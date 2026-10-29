"""
TeleLens Desktop Studio Dashboard.
Main PyQt6 window with live preview, real-time digital magnification pipeline,
remote camera controls, virtual camera publisher, and pairing modals.
"""

import sys
import logging
import threading
import asyncio
from typing import Optional
import numpy as np

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QComboBox, QCheckBox, QGroupBox,
        QStatusBar, QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QObject
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QMainWindow = object
    QObject = object

# Defensive path insertion for PyInstaller frozen execution or direct execution
import os
_base = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
if _base not in sys.path:
    sys.path.insert(0, _base)

from telelens.config import TeleLensConfig
from telelens.ui.styles.dark_theme import DARK_STYLESHEET
from telelens.ui.components.video_widget import VideoPreviewWidget
from telelens.ui.dialogs.approval_dialog import ApprovalDialog
from telelens.ui.dialogs.qr_dialog import QRCodeDialog
from telelens.ui.dialogs.diagnostic_dialog import DiagnosticDialog
from telelens.discovery.mdns import TeleLensMDNSService, get_local_ip_addresses
from telelens.discovery.qr_code import generate_pairing_payload
from telelens.discovery.adb_bridge import ADBBridge
from telelens.driver.virtual_cam import VirtualCameraEngine
from telelens.webrtc.signaling import SignalingServer
from telelens.webrtc.peer import WebRTCPeerManager
from telelens.webrtc.controls import CameraControls, CameraLens

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("telelens.app")


class AppBridge(QObject if PYQT6_AVAILABLE else object):
    """Qt signal bridge for thread-safe cross-talk between asyncio and Qt event loop."""
    if PYQT6_AVAILABLE:
        frame_received = pyqtSignal(object)
        approval_requested = pyqtSignal(dict, object)  # device_info, future
        telemetry_updated = pyqtSignal(dict)
        client_disconnected = pyqtSignal()


class TeleLensMainWindow(QMainWindow if PYQT6_AVAILABLE else object):
    """TeleLens Studio Master Window."""

    def __init__(self, config: Optional[TeleLensConfig] = None):
        if not PYQT6_AVAILABLE:
            print("PyQt6 is required to run the desktop UI. Install via 'pip install PyQt6'.")
            return
        super().__init__()

        self.config = config or TeleLensConfig()
        self.bridge = AppBridge()

        # Digital Magnification & Preview State
        self.current_zoom = 1.0
        self.mirror_preview = False

        # Engines
        self.vcam_engine = VirtualCameraEngine(
            width=self.config.stream.width,
            height=self.config.stream.height,
            fps=self.config.stream.fps,
            backend=self.config.stream.backend,
        )
        self.mdns_service = TeleLensMDNSService(
            port=self.config.server.signaling_port,
            service_name=self.config.server.mdns_service_name,
        )
        self.adb_bridge = ADBBridge(port=self.config.server.signaling_port)
        self.peer_manager = WebRTCPeerManager(
            on_frame=self._on_video_frame,
            on_telemetry=self._on_telemetry,
            on_remote_disconnect=self._on_client_disconnect
        )

        self.signaling_server: Optional[SignalingServer] = None
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_thread: Optional[threading.Thread] = None

        self._init_ui()
        self._connect_signals()
        self._start_services()

    def _init_ui(self):
        self.setWindowTitle("TeleLens Studio — Pro Phone-to-PC Webcam")
        self.resize(1260, 780)
        self.setStyleSheet(DARK_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(18)

        # Left / Center Area: Video Canvas & Top Bar
        left_area = QVBoxLayout()
        left_area.setSpacing(14)

        # Top Bar
        top_bar = QHBoxLayout()
        title_lbl = QLabel("TeleLens Studio")
        title_lbl.setObjectName("HeaderTitle")

        self.status_badge = QLabel("READY - WAITING FOR PHONE")
        self.status_badge.setObjectName("StatusBadge")

        top_bar.addWidget(title_lbl)
        top_bar.addWidget(self.status_badge)
        top_bar.addStretch()

        # Disconnect Button
        self.disconnect_btn = QPushButton("⏹️ Disconnect Device")
        self.disconnect_btn.setObjectName("DangerButton")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self._handle_user_disconnect)
        top_bar.addWidget(self.disconnect_btn)

        self.qr_btn = QPushButton("📱 Pair Device (QR)")
        self.qr_btn.clicked.connect(self._show_qr_dialog)
        top_bar.addWidget(self.qr_btn)

        self.diag_btn = QPushButton("🛠️ Driver Diagnostics")
        self.diag_btn.clicked.connect(self._show_diagnostics)
        top_bar.addWidget(self.diag_btn)

        left_area.addLayout(top_bar)

        # Video Canvas
        self.video_widget = VideoPreviewWidget()
        left_area.addWidget(self.video_widget, stretch=1)

        # Bottom Bar: Virtual Camera Controls & Frame Delivery
        bottom_bar = QHBoxLayout()
        self.vcam_btn = QPushButton("🎥 Start Virtual Webcam")
        self.vcam_btn.setObjectName("PrimaryButton")
        self.vcam_btn.clicked.connect(self._toggle_virtual_cam)

        self.vcam_status_lbl = QLabel("Virtual Cam: Inactive (Click Diagnostics to verify driver)")
        self.vcam_status_lbl.setStyleSheet("color: #A1A1AA; font-size: 12px; margin-left: 8px;")
        bottom_bar.addWidget(self.vcam_btn)
        bottom_bar.addWidget(self.vcam_status_lbl)
        bottom_bar.addStretch()

        # Mirror Preview Button
        self.mirror_check = QCheckBox("Mirror Viewfinder")
        self.mirror_check.setChecked(False)
        self.mirror_check.toggled.connect(self._on_mirror_toggled)
        bottom_bar.addWidget(self.mirror_check)

        left_area.addLayout(bottom_bar)
        root_layout.addLayout(left_area, stretch=3)

        # Right Area: Remote Hardware Controls Sidebar
        sidebar = QVBoxLayout()
        sidebar.setSpacing(14)
        sidebar.setContentsMargins(0, 0, 0, 0)

        # Group 1: Stream Output Quality & FPS
        quality_group = QGroupBox("Stream Output Profile")
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.setSpacing(8)

        quality_lbl = QLabel("Resolution & Target Framerate:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("1080p FHD (1920x1080) @ 60 FPS", (1920, 1080, 60))
        self.quality_combo.addItem("1080p FHD (1920x1080) @ 30 FPS", (1920, 1080, 30))
        self.quality_combo.addItem("4K UHD (3840x2160) @ 30 FPS", (3840, 2160, 30))
        self.quality_combo.addItem("1440p QHD (2560x1440) @ 60 FPS", (2560, 1440, 60))
        self.quality_combo.addItem("720p HD (1280x720) @ 60 FPS", (1280, 720, 60))
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(quality_lbl)
        quality_layout.addWidget(self.quality_combo)
        sidebar.addWidget(quality_group)

        # Group 2: Camera Sensor & Lens
        cam_group = QGroupBox("Camera Sensor & Lens")
        cam_layout = QVBoxLayout(cam_group)
        cam_layout.setSpacing(10)

        lens_lbl = QLabel("Active Camera:")
        self.lens_combo = QComboBox()
        self.lens_combo.addItem("Rear Primary Camera (Main)", "rear_main")
        self.lens_combo.addItem("Front Selfie Camera", "front")
        self.lens_combo.addItem("Rear Ultra-Wide Lens", "rear_ultrawide")
        self.lens_combo.addItem("Rear Telephoto Lens", "rear_telephoto")
        self.lens_combo.currentIndexChanged.connect(self._on_lens_changed)
        cam_layout.addWidget(lens_lbl)
        cam_layout.addWidget(self.lens_combo)

        # Torch Button
        self.torch_btn = QPushButton("🔦 Flashlight: OFF")
        self.torch_btn.setCheckable(True)
        self.torch_btn.toggled.connect(self._on_torch_toggled)
        cam_layout.addWidget(self.torch_btn)

        sidebar.addWidget(cam_group)

        # Group 3: Digital Magnification & Zoom
        zoom_group = QGroupBox("Digital Magnification & Zoom")
        zoom_layout = QVBoxLayout(zoom_group)
        zoom_layout.setSpacing(10)

        zoom_header = QHBoxLayout()
        zoom_lbl = QLabel("Magnification:")
        self.zoom_val_lbl = QLabel("1.0x")
        self.zoom_val_lbl.setStyleSheet("font-weight: bold; color: #FAFAFA;")
        zoom_header.addWidget(zoom_lbl)
        zoom_header.addStretch()
        zoom_header.addWidget(self.zoom_val_lbl)
        zoom_layout.addLayout(zoom_header)

        # Stepper buttons
        stepper_layout = QHBoxLayout()
        stepper_layout.setSpacing(6)
        for mult in [1.0, 1.5, 2.0, 3.0, 5.0]:
            btn = QPushButton(f"{mult}x")
            btn.setObjectName("StepperButton")
            btn.clicked.connect(lambda _, m=mult: self._set_zoom_val(m))
            stepper_layout.addWidget(btn)
        zoom_layout.addLayout(stepper_layout)

        # Zoom Slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 50)  # 1.0x to 5.0x
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)

        sidebar.addWidget(zoom_group)

        # Group 4: Focus Tuning
        focus_group = QGroupBox("Focus Tuning")
        focus_layout = QVBoxLayout(focus_group)
        focus_layout.setSpacing(10)

        self.af_check = QCheckBox("Continuous Auto Focus")
        self.af_check.setChecked(True)
        self.af_check.toggled.connect(self._on_af_toggled)
        focus_layout.addWidget(self.af_check)

        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setRange(0, 100)
        self.focus_slider.setValue(50)
        self.focus_slider.setEnabled(False)
        self.focus_slider.valueChanged.connect(self._on_focus_changed)
        focus_layout.addWidget(self.focus_slider)

        sidebar.addWidget(focus_group)

        # Group 5: Telemetry & Saver
        power_group = QGroupBox("Phone Telemetry & Power")
        power_layout = QVBoxLayout(power_group)
        power_layout.setSpacing(10)

        self.battery_lbl = QLabel("🔋 Phone Battery: --%")
        power_layout.addWidget(self.battery_lbl)

        self.saver_check = QCheckBox("Phone Screen Dimmer (Thermal Saver)")
        self.saver_check.setChecked(True)
        self.saver_check.toggled.connect(self._on_thermal_saver_toggled)
        power_layout.addWidget(self.saver_check)

        sidebar.addWidget(power_group)
        sidebar.addStretch()

        root_layout.addLayout(sidebar, stretch=1)

    def _connect_signals(self):
        self.bridge.frame_received.connect(self._handle_frame_received)
        self.bridge.approval_requested.connect(self._handle_approval_dialog)
        self.bridge.telemetry_updated.connect(self._handle_telemetry_ui)
        self.bridge.client_disconnected.connect(self._handle_client_disconnected)

    def _start_services(self):
        # 1. Start mDNS
        self.mdns_service.start()

        # 2. Start ADB Cable Auto-Reversal
        self.adb_bridge.start_auto_reverse()

        # 3. Start Asyncio Background Thread for Signaling & WebRTC
        self._async_loop = asyncio.new_event_loop()

        async def async_approval(device_info: dict) -> bool:
            future = self._async_loop.create_future()
            self.bridge.approval_requested.emit(device_info, future)
            return await future

        self.signaling_server = SignalingServer(
            host=self.config.server.host,
            port=self.config.server.signaling_port,
            approval_callback=async_approval,
            require_approval=self.config.server.require_approval
        )
        self.signaling_server.set_offer_handler(self.peer_manager.handle_offer)
        self.signaling_server.set_disconnect_handler(self._on_client_disconnect)

        def run_loop():
            asyncio.set_event_loop(self._async_loop)
            self._async_loop.run_until_complete(self.signaling_server.start())
            self._async_loop.run_forever()

        self._async_thread = threading.Thread(target=run_loop, daemon=True)
        self._async_thread.start()

    def _on_video_frame(self, frame_rgb: np.ndarray):
        # 1. Apply Real-Time Digital Magnification & Center-Crop
        if self.current_zoom > 1.01:
            try:
                h, w, c = frame_rgb.shape
                crop_h = max(2, int(h / self.current_zoom))
                crop_w = max(2, int(w / self.current_zoom))
                y1 = (h - crop_h) // 2
                x1 = (w - crop_w) // 2
                cropped = frame_rgb[y1:y1 + crop_h, x1:x1 + crop_w]
                from PIL import Image
                pil_img = Image.fromarray(cropped)
                resized_img = pil_img.resize((w, h), Image.Resampling.BILINEAR)
                frame_rgb = np.ascontiguousarray(np.array(resized_img))
            except Exception as e:
                logger.debug("Digital magnification processing error: %s", e)

        # 2. Apply Mirror Viewport if enabled
        if self.mirror_preview:
            frame_rgb = np.ascontiguousarray(np.fliplr(frame_rgb))

        self.bridge.frame_received.emit(frame_rgb)
        if self.vcam_engine.is_running:
            self.vcam_engine.send_frame(frame_rgb)

    def _on_telemetry(self, data):
        self.bridge.telemetry_updated.emit(data)

    def _on_client_disconnect(self):
        self.bridge.client_disconnected.emit()

    def _handle_frame_received(self, frame_rgb):
        self.video_widget.update_frame(frame_rgb, fps=float(self.config.stream.fps))
        if self.status_badge.objectName() != "StatusBadgeActive":
            self.status_badge.setText("STUDIO LIVE")
            self.status_badge.setObjectName("StatusBadgeActive")
            self.status_badge.style().unpolish(self.status_badge)
            self.status_badge.style().polish(self.status_badge)
            self.disconnect_btn.setEnabled(True)

        if self.vcam_engine.is_running and self.vcam_engine.frame_count % 30 == 0:
            self.vcam_status_lbl.setText(
                f"Virtual Cam: Active ({self.vcam_engine.backend}) — {self.vcam_engine.frame_count} frames delivered"
            )

    def _handle_approval_dialog(self, device_info, future):
        dialog = ApprovalDialog(device_info, self)
        accepted = (dialog.exec() == 1)
        self._async_loop.call_soon_threadsafe(future.set_result, accepted)

    def _handle_telemetry_ui(self, data):
        pct = data.get("batteryLevel", data.get("battery"))
        if pct is not None:
            self.battery_lbl.setText(f"🔋 Phone Battery: {pct}%")
            self.video_widget.set_battery(pct)

    def _handle_user_disconnect(self):
        """User clicked Disconnect button on Windows."""
        self.peer_manager.disconnect_peer()
        if self._async_loop and self._async_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.peer_manager.close(), self._async_loop)
        self._handle_client_disconnected()

    def _handle_client_disconnected(self):
        self.video_widget.set_disconnected()
        self.status_badge.setText("READY - WAITING FOR PHONE")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.disconnect_btn.setEnabled(False)
        self.battery_lbl.setText("🔋 Phone Battery: --%")
        self.torch_btn.setChecked(False)
        self.torch_btn.setText("🔦 Flashlight: OFF")

    def _toggle_virtual_cam(self):
        if self.vcam_engine.is_running:
            self.vcam_engine.stop()
            self.vcam_btn.setText("🎥 Start Virtual Webcam")
            self.vcam_status_lbl.setText("Virtual Cam: Inactive")
        else:
            success = self.vcam_engine.start()
            if success:
                self.vcam_btn.setText("⏹️ Stop Virtual Webcam")
                self.vcam_status_lbl.setText(f"Virtual Cam: Active ({self.vcam_engine.backend or 'OBS'})")
            else:
                QMessageBox.warning(
                    self,
                    "Virtual Camera Driver",
                    "Could not initialize Virtual Camera driver.\n\n"
                    "Click 'Driver Diagnostics' in the top bar to inspect and install the driver with 1 click."
                )

    def _show_qr_dialog(self):
        local_ips = get_local_ip_addresses()
        ip = local_ips[0]
        payload = generate_pairing_payload(host_ip=ip, port=self.config.server.signaling_port)
        dlg = QRCodeDialog(payload, ip, self.config.server.signaling_port, self)
        dlg.exec()

    def _show_diagnostics(self):
        dlg = DiagnosticDialog(self)
        dlg.exec()

    # Camera & Video Pipeline Controls
    def _on_quality_changed(self, index):
        data = self.quality_combo.currentData()
        if data:
            width, height, fps = data
            cmd = CameraControls.set_quality(width, height, fps)
            self.peer_manager.send_control(cmd)
            self.config.stream.width = width
            self.config.stream.height = height
            self.config.stream.fps = fps
            if self.vcam_engine.is_running:
                self.vcam_engine.resize(width, height, fps)

    def _on_lens_changed(self, index):
        lens = self.lens_combo.currentData()
        if lens:
            cmd = CameraControls.set_lens(lens)
            self.peer_manager.send_control(cmd)
            if "front" in lens.lower():
                self.mirror_check.setChecked(True)

    def _on_torch_toggled(self, checked):
        self.torch_btn.setText("🔦 Flashlight: ON" if checked else "🔦 Flashlight: OFF")
        cmd = CameraControls.set_torch(checked)
        self.peer_manager.send_control(cmd)

    def _set_zoom_val(self, multiplier: float):
        self.zoom_slider.setValue(int(multiplier * 10))

    def _on_zoom_changed(self, val):
        factor = val / 10.0
        self.current_zoom = factor
        self.zoom_val_lbl.setText(f"{factor:.1f}x")
        cmd = CameraControls.set_zoom(factor)
        self.peer_manager.send_control(cmd)

    def _on_mirror_toggled(self, checked):
        self.mirror_preview = checked

    def _on_af_toggled(self, checked):
        self.focus_slider.setEnabled(not checked)
        cmd = CameraControls.set_focus(distance=self.focus_slider.value() / 100.0, auto=checked)
        self.peer_manager.send_control(cmd)

    def _on_focus_changed(self, val):
        if not self.af_check.isChecked():
            cmd = CameraControls.set_focus(distance=val / 100.0, auto=False)
            self.peer_manager.send_control(cmd)

    def _on_thermal_saver_toggled(self, checked):
        cmd = CameraControls.set_thermal_saver(checked)
        self.peer_manager.send_control(cmd)

    def closeEvent(self, event):
        self.peer_manager.disconnect_peer()
        self.adb_bridge.stop()
        self.vcam_engine.stop()
        self.mdns_service.stop()
        event.accept()


def main():
    if not PYQT6_AVAILABLE:
        raise RuntimeError("PyQt6 is required to launch the desktop UI. Please install it using: pip install PyQt6")
    app = QApplication(sys.argv)
    window = TeleLensMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
