"""
TeleLens Desktop Studio Dashboard.
Main PyQt6 window with live preview, remote camera controls, virtual camera publisher, and pairing modals.
"""

import sys
import logging
import threading
import asyncio
from typing import Optional

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

from telelens.config import TeleLensConfig
from telelens.ui.styles.dark_theme import DARK_STYLESHEET
from telelens.ui.components.video_widget import VideoPreviewWidget
from telelens.ui.dialogs.approval_dialog import ApprovalDialog
from telelens.ui.dialogs.qr_dialog import QRCodeDialog
from telelens.ui.dialogs.diagnostic_dialog import DiagnosticDialog
from telelens.discovery.mdns import TeleLensMDNSService, get_local_ip_addresses
from telelens.discovery.qr_code import generate_pairing_payload
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
        self.peer_manager = WebRTCPeerManager(
            on_frame=self._on_video_frame,
            on_telemetry=self._on_telemetry
        )

        self.signaling_server: Optional[SignalingServer] = None
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_thread: Optional[threading.Thread] = None

        self._init_ui()
        self._connect_signals()
        self._start_services()

    def _init_ui(self):
        self.setWindowTitle("TeleLens Studio — 4K Phone-to-Laptop Webcam")
        self.resize(1180, 720)
        self.setStyleSheet(DARK_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # Left / Center Area: Video Canvas & Top Bar
        left_area = QVBoxLayout()
        left_area.setSpacing(12)

        # Top Bar
        top_bar = QHBoxLayout()
        title_lbl = QLabel("TeleLens Studio")
        title_lbl.setObjectName("HeaderTitle")

        self.status_badge = QLabel("READY - WAITING FOR PHONE")
        self.status_badge.setObjectName("StatusBadge")

        top_bar.addWidget(title_lbl)
        top_bar.addWidget(self.status_badge)
        top_bar.addStretch()

        self.qr_btn = QPushButton("📱 Pair Device (QR)")
        self.qr_btn.clicked.connect(self._show_qr_dialog)
        top_bar.addWidget(self.qr_btn)

        self.diag_btn = QPushButton("🛠️ Diagnostics")
        self.diag_btn.clicked.connect(self._show_diagnostics)
        top_bar.addWidget(self.diag_btn)

        left_area.addLayout(top_bar)

        # Video Canvas
        self.video_widget = VideoPreviewWidget()
        left_area.addWidget(self.video_widget, stretch=1)

        # Bottom Bar: Virtual Camera Controls
        bottom_bar = QHBoxLayout()
        self.vcam_btn = QPushButton("🎥 Start Virtual Webcam")
        self.vcam_btn.setObjectName("PrimaryButton")
        self.vcam_btn.clicked.connect(self._toggle_virtual_cam)

        self.vcam_status_lbl = QLabel("Virtual Cam: Inactive")
        bottom_bar.addWidget(self.vcam_btn)
        bottom_bar.addWidget(self.vcam_status_lbl)
        bottom_bar.addStretch()

        left_area.addLayout(bottom_bar)
        root_layout.addLayout(left_area, stretch=3)

        # Right Area: Remote Hardware Controls Sidebar
        sidebar = QVBoxLayout()
        sidebar.setSpacing(16)
        sidebar.setContentsMargins(0, 0, 0, 0)

        # Group 1: Camera Sensor & Lenses
        cam_group = QGroupBox("Camera Sensor & Lens")
        cam_layout = QVBoxLayout(cam_group)
        cam_layout.setSpacing(10)

        lens_lbl = QLabel("Active Lens:")
        self.lens_combo = QComboBox()
        self.lens_combo.addItem("Rear Primary (Wide 1x)", CameraLens.REAR_MAIN)
        self.lens_combo.addItem("Rear Ultra-Wide (0.6x)", CameraLens.REAR_ULTRAWIDE)
        self.lens_combo.addItem("Rear Telephoto (3x/5x)", CameraLens.REAR_TELEPHOTO)
        self.lens_combo.addItem("Front Facing (Selfie)", CameraLens.FRONT)
        self.lens_combo.currentIndexChanged.connect(self._on_lens_changed)
        cam_layout.addWidget(lens_lbl)
        cam_layout.addWidget(self.lens_combo)

        self.torch_check = QCheckBox("Flashlight / Torch")
        self.torch_check.toggled.connect(self._on_torch_toggled)
        cam_layout.addWidget(self.torch_check)

        sidebar.addWidget(cam_group)

        # Group 2: Manual Tuning (Zoom, Exposure, Focus)
        tuning_group = QGroupBox("Manual Tuning")
        tune_layout = QVBoxLayout(tuning_group)
        tune_layout.setSpacing(10)

        # Zoom Slider
        zoom_lbl = QLabel("Zoom Factor:")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 50)  # 1.0x to 5.0x
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        tune_layout.addWidget(zoom_lbl)
        tune_layout.addWidget(self.zoom_slider)

        # Focus Slider & Auto-focus
        focus_lbl = QLabel("Manual Focus:")
        self.af_check = QCheckBox("Auto Focus (Continuous)")
        self.af_check.setChecked(True)
        self.af_check.toggled.connect(self._on_af_toggled)
        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setRange(0, 100)
        self.focus_slider.setValue(50)
        self.focus_slider.setEnabled(False)
        self.focus_slider.valueChanged.connect(self._on_focus_changed)
        tune_layout.addWidget(focus_lbl)
        tune_layout.addWidget(self.af_check)
        tune_layout.addWidget(self.focus_slider)

        sidebar.addWidget(tuning_group)

        # Group 3: Thermal & Battery Management
        power_group = QGroupBox("Thermal & Battery Saver")
        power_layout = QVBoxLayout(power_group)
        power_layout.setSpacing(10)

        self.saver_check = QCheckBox("Phone OLED Screen Off / Dim")
        self.saver_check.setChecked(True)
        self.saver_check.toggled.connect(self._on_thermal_saver_toggled)
        power_layout.addWidget(self.saver_check)

        self.battery_lbl = QLabel("Phone Battery: --%")
        power_layout.addWidget(self.battery_lbl)

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

        # 2. Start Asyncio Background Thread for Signaling & WebRTC
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

    def _on_video_frame(self, frame_rgb):
        # Called from WebRTC track reader thread
        self.bridge.frame_received.emit(frame_rgb)
        if self.vcam_engine.is_running:
            self.vcam_engine.send_frame(frame_rgb)

    def _on_telemetry(self, data):
        self.bridge.telemetry_updated.emit(data)

    def _on_client_disconnect(self):
        self.bridge.client_disconnected.emit()

    def _handle_frame_received(self, frame_rgb):
        self.video_widget.update_frame(frame_rgb, fps=float(self.config.stream.fps))
        self.status_badge.setText("STREAMING (LIVE)")
        self.status_badge.setObjectName("StatusBadgeActive")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def _handle_approval_dialog(self, device_info, future):
        dialog = ApprovalDialog(device_info, self)
        accepted = (dialog.exec() == 1)
        self._async_loop.call_soon_threadsafe(future.set_result, accepted)

    def _handle_telemetry_ui(self, data):
        if "battery" in data:
            pct = data["battery"]
            self.battery_lbl.setText(f"Phone Battery: {pct}%")
            self.video_widget.set_battery(pct)

    def _handle_client_disconnected(self):
        self.video_widget.set_disconnected()
        self.status_badge.setText("STANDBY")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def _toggle_virtual_cam(self):
        if self.vcam_engine.is_running:
            self.vcam_engine.stop()
            self.vcam_btn.setText("🎥 Start Virtual Webcam")
            self.vcam_status_lbl.setText("Virtual Cam: Inactive")
        else:
            success = self.vcam_engine.start()
            if success:
                self.vcam_btn.setText("⏹️ Stop Virtual Webcam")
                self.vcam_status_lbl.setText("Virtual Cam: Active (OBS DirectShow)")
            else:
                QMessageBox.warning(
                    self,
                    "Virtual Camera Error",
                    "Could not initialize Virtual Camera driver. Click 'Diagnostics' to verify driver registration."
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

    # Camera Controls
    def _on_lens_changed(self, index):
        lens = self.lens_combo.currentData()
        if lens:
            cmd = CameraControls.set_lens(lens)
            self.peer_manager.send_control(cmd)

    def _on_torch_toggled(self, checked):
        cmd = CameraControls.set_torch(checked)
        self.peer_manager.send_control(cmd)

    def _on_zoom_changed(self, val):
        factor = val / 10.0
        cmd = CameraControls.set_zoom(factor)
        self.peer_manager.send_control(cmd)

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
        self.vcam_engine.stop()
        self.mdns_service.stop()
        event.accept()


def main():
    if not PYQT6_AVAILABLE:
        print("PyQt6 is required. Install with: pip install PyQt6")
        sys.exit(1)
    app = QApplication(sys.argv)
    window = TeleLensMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
