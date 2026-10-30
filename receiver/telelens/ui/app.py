"""
TeleLens Desktop Studio Dashboard.
Modern glassmorphism UI matching the Studio Pro mobile client with real-time digital magnification,
bidirectional remote controls, dual-channel command redundancy, USB Turbo frame transport,
and virtual camera publisher.
"""

import sys
import json
import logging
import threading
import asyncio
from typing import Optional, Dict, Any
import numpy as np

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSlider, QComboBox, QCheckBox, QFrame,
        QMessageBox
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
from telelens.stream.turbo_server import TurboStreamServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("telelens.app")


class AppBridge(QObject if PYQT6_AVAILABLE else object):
    """Qt signal bridge for thread-safe cross-talk between asyncio and Qt event loop."""
    if PYQT6_AVAILABLE:
        frame_received = pyqtSignal(object)
        approval_requested = pyqtSignal(dict, object)
        telemetry_updated = pyqtSignal(dict)
        remote_control_received = pyqtSignal(str, dict)
        client_disconnected = pyqtSignal()
        protocol_detected = pyqtSignal(str)


class TeleLensMainWindow(QMainWindow if PYQT6_AVAILABLE else object):
    """TeleLens Studio Master Window with Android Studio Pro Design."""

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
        self.stepper_buttons = []
        self.active_protocol = "None"

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
        self.adb_bridge = ADBBridge(
            port=self.config.server.signaling_port,
            stream_port=self.config.server.direct_stream_port,
        )
        self.peer_manager = WebRTCPeerManager(
            on_frame=self._on_webrtc_frame,
            on_telemetry=self._on_telemetry,
            on_remote_disconnect=self._on_client_disconnect,
            on_remote_control=self._on_remote_control
        )
        self.turbo_server = TurboStreamServer(
            host=self.config.server.host,
            port=self.config.server.direct_stream_port,
            on_frame=self._on_turbo_frame,
            on_connect=self._on_turbo_connect,
            on_disconnect=self._on_turbo_disconnect,
        )

        self.signaling_server: Optional[SignalingServer] = None
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_thread: Optional[threading.Thread] = None

        self._init_ui()
        self._connect_signals()
        self._start_services()

    def _init_ui(self):
        self.setWindowTitle("TeleLens Studio — Pro Phone-to-PC Webcam")
        self.resize(1280, 800)
        self.setStyleSheet(DARK_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(20)

        # ── Left / Center Area: Video Canvas & Top Header Bar ───────────
        left_area = QVBoxLayout()
        left_area.setSpacing(16)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        title_lbl = QLabel("TeleLens Studio")
        title_lbl.setObjectName("HeaderTitle")

        self.status_badge = QLabel("WAITING FOR DEVICE")
        self.status_badge.setObjectName("StatusBadge")

        self.protocol_badge = QLabel("BUS: USB/WI-FI AUTO")
        self.protocol_badge.setStyleSheet(
            "background-color: #27272A; color: #A1A1AA; font-size: 11px; "
            "font-weight: 700; padding: 4px 8px; border-radius: 6px;"
        )

        self.battery_badge = QLabel("🔋 --%")
        self.battery_badge.setObjectName("BatteryBadge")
        self.battery_badge.setVisible(False)

        top_bar.addWidget(title_lbl)
        top_bar.addWidget(self.status_badge)
        top_bar.addWidget(self.protocol_badge)
        top_bar.addWidget(self.battery_badge)
        top_bar.addStretch()

        self.disconnect_btn = QPushButton("⏹ Disconnect")
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

        # Video Canvas Container
        self.video_widget = VideoPreviewWidget()
        left_area.addWidget(self.video_widget, stretch=1)

        # Bottom Bar: Viewfinder Options & Virtual Cam Quick Toggle
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(12)

        self.vcam_btn = QPushButton("🎥 Start Virtual Webcam")
        self.vcam_btn.setObjectName("PrimaryButton")
        self.vcam_btn.clicked.connect(self._toggle_virtual_cam)

        self.vcam_status_lbl = QLabel("Virtual Cam: Inactive (OBS / DirectShow)")
        self.vcam_status_lbl.setStyleSheet("color: #8E8E9E; font-size: 12px; margin-left: 6px;")

        bottom_bar.addWidget(self.vcam_btn)
        bottom_bar.addWidget(self.vcam_status_lbl)
        bottom_bar.addStretch()

        self.mirror_check = QCheckBox("Mirror Viewfinder")
        self.mirror_check.setChecked(False)
        self.mirror_check.toggled.connect(self._on_mirror_toggled)
        bottom_bar.addWidget(self.mirror_check)

        left_area.addLayout(bottom_bar)
        root_layout.addLayout(left_area, stretch=3)

        # ── Right Area: Modern Floating Sidebar Cards ───────────────────
        sidebar = QVBoxLayout()
        sidebar.setSpacing(14)
        sidebar.setContentsMargins(0, 0, 0, 0)

        # Card 1: Stream Output Profile
        profile_card = QFrame()
        profile_card.setObjectName("SidebarCard")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setSpacing(10)
        profile_layout.setContentsMargins(14, 14, 14, 14)

        profile_title = QLabel("⚡ Stream Output Profile")
        profile_title.setObjectName("CardTitle")
        profile_layout.addWidget(profile_title)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("1088x1088 Square HD (1:1 Creator Studio) @ 30 FPS • 25 Mbps", (1088, 1088, 30))
        self.quality_combo.addItem("1088x1088 Square HD (1:1 Creator Studio) @ 60 FPS • 35 Mbps", (1088, 1088, 60))
        self.quality_combo.addItem("1080p FHD (1920x1080) @ 60 FPS • 18 Mbps", (1920, 1080, 60))
        self.quality_combo.addItem("1080p FHD (1920x1080) @ 30 FPS • 14 Mbps", (1920, 1080, 30))
        self.quality_combo.addItem("4K UHD (3840x2160) @ 30 FPS • 35 Mbps", (3840, 2160, 30))
        self.quality_combo.addItem("1440p QHD (2560x1440) @ 60 FPS • 24 Mbps", (2560, 1440, 60))
        self.quality_combo.addItem("720p HD (1280x720) @ 60 FPS • 8 Mbps", (1280, 720, 60))
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        profile_layout.addWidget(self.quality_combo)
        sidebar.addWidget(profile_card)

        # Card 2: Camera Sensor & Flashlight
        sensor_card = QFrame()
        sensor_card.setObjectName("SidebarCard")
        sensor_layout = QVBoxLayout(sensor_card)
        sensor_layout.setSpacing(10)
        sensor_layout.setContentsMargins(14, 14, 14, 14)

        sensor_title = QLabel("📷 Camera Sensor & Lens")
        sensor_title.setObjectName("CardTitle")
        sensor_layout.addWidget(sensor_title)

        self.lens_combo = QComboBox()
        self.lens_combo.addItem("Rear Primary Camera (Wide 1x)", "rear_main")
        self.lens_combo.addItem("Front Selfie Camera", "front")
        self.lens_combo.addItem("Rear Ultra-Wide Lens (0.5x)", "rear_ultrawide")
        self.lens_combo.addItem("Rear Telephoto Lens (3x)", "rear_telephoto")
        self.lens_combo.currentIndexChanged.connect(self._on_lens_changed)
        sensor_layout.addWidget(self.lens_combo)

        self.torch_btn = QPushButton("🔦 Flashlight: OFF")
        self.torch_btn.setObjectName("TorchButton")
        self.torch_btn.setCheckable(True)
        self.torch_btn.toggled.connect(self._on_torch_toggled)
        sensor_layout.addWidget(self.torch_btn)
        sidebar.addWidget(sensor_card)

        # Card 3: Digital Magnification & Zoom
        zoom_card = QFrame()
        zoom_card.setObjectName("SidebarCard")
        zoom_layout = QVBoxLayout(zoom_card)
        zoom_layout.setSpacing(10)
        zoom_layout.setContentsMargins(14, 14, 14, 14)

        zoom_header = QHBoxLayout()
        zoom_title = QLabel("🔍 Digital Magnification")
        zoom_title.setObjectName("CardTitle")
        self.zoom_val_lbl = QLabel("1.0x")
        self.zoom_val_lbl.setStyleSheet("font-weight: 800; color: #FFFFFF; font-size: 13px;")
        zoom_header.addWidget(zoom_title)
        zoom_header.addStretch()
        zoom_header.addWidget(self.zoom_val_lbl)
        zoom_layout.addLayout(zoom_header)

        # Stepper Chips matching Android UI
        stepper_layout = QHBoxLayout()
        stepper_layout.setSpacing(6)
        self.stepper_buttons = []
        for mult in [1.0, 1.5, 2.0, 3.0, 5.0]:
            btn = QPushButton(f"{mult}x")
            btn.setObjectName("StepperButton")
            btn.setProperty("active", "true" if mult == 1.0 else "false")
            btn.clicked.connect(lambda _, m=mult: self._set_zoom_val(m))
            stepper_layout.addWidget(btn)
            self.stepper_buttons.append((mult, btn))
        zoom_layout.addLayout(stepper_layout)

        # Zoom Slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 50)  # 1.0x to 5.0x
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        sidebar.addWidget(zoom_card)

        # Card 4: Precision Focus Tuning
        focus_card = QFrame()
        focus_card.setObjectName("SidebarCard")
        focus_layout = QVBoxLayout(focus_card)
        focus_layout.setSpacing(10)
        focus_layout.setContentsMargins(14, 14, 14, 14)

        focus_title = QLabel("🎯 Precision Focus")
        focus_title.setObjectName("CardTitle")
        focus_layout.addWidget(focus_title)

        self.af_check = QCheckBox("Continuous Auto Focus (AF)")
        self.af_check.setChecked(True)
        self.af_check.toggled.connect(self._on_af_toggled)
        focus_layout.addWidget(self.af_check)

        focus_slider_layout = QHBoxLayout()
        focus_near_lbl = QLabel("Near")
        focus_near_lbl.setStyleSheet("color: #71717A; font-size: 11px;")
        focus_far_lbl = QLabel("Far")
        focus_far_lbl.setStyleSheet("color: #71717A; font-size: 11px;")

        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setRange(0, 100)
        self.focus_slider.setValue(50)
        self.focus_slider.setEnabled(False)
        self.focus_slider.valueChanged.connect(self._on_focus_changed)

        focus_slider_layout.addWidget(focus_near_lbl)
        focus_slider_layout.addWidget(self.focus_slider, stretch=1)
        focus_slider_layout.addWidget(focus_far_lbl)
        focus_layout.addLayout(focus_slider_layout)
        sidebar.addWidget(focus_card)

        # Card 5: Power & Screen Dimmer
        power_card = QFrame()
        power_card.setObjectName("SidebarCard")
        power_layout = QVBoxLayout(power_card)
        power_layout.setSpacing(10)
        power_layout.setContentsMargins(14, 14, 14, 14)

        power_title = QLabel("🔋 Power & Thermal Saver")
        power_title.setObjectName("CardTitle")
        power_layout.addWidget(power_title)

        self.saver_check = QCheckBox("Phone OLED Screen Dimmer (Saves Battery)")
        self.saver_check.setChecked(True)
        self.saver_check.toggled.connect(self._on_thermal_saver_toggled)
        power_layout.addWidget(self.saver_check)
        sidebar.addWidget(power_card)

        sidebar.addStretch()
        root_layout.addLayout(sidebar, stretch=1)

    def _connect_signals(self):
        self.bridge.frame_received.connect(self._handle_frame_received)
        self.bridge.approval_requested.connect(self._handle_approval_dialog)
        self.bridge.telemetry_updated.connect(self._handle_telemetry_ui)
        self.bridge.remote_control_received.connect(self._handle_remote_control_ui)
        self.bridge.client_disconnected.connect(self._handle_client_disconnected)
        self.bridge.protocol_detected.connect(self._handle_protocol_detected)

    def _start_services(self):
        self.mdns_service.start()
        self.adb_bridge.start_auto_reverse()

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
        self.signaling_server.set_control_handler(self._on_remote_control)
        self.signaling_server.set_disconnect_handler(self._on_client_disconnect)

        def run_loop():
            asyncio.set_event_loop(self._async_loop)
            self._async_loop.run_until_complete(self.signaling_server.start())
            self._async_loop.run_until_complete(self.turbo_server.start())
            self._async_loop.run_forever()

        self._async_thread = threading.Thread(target=run_loop, daemon=True)
        self._async_thread.start()

    def send_command_dual(self, method: str, params: Dict[str, Any]):
        """Dispatches control command with dual-channel redundancy over both DataChannel and WebSocket."""
        # 1. Send via WebRTC DataChannel
        cmd_str = json.dumps({"method": method, "params": params})
        self.peer_manager.send_control(cmd_str)

        # 2. Send via WebSocket Signaling Server
        if self._async_loop and self._async_loop.is_running() and self.signaling_server:
            asyncio.run_coroutine_threadsafe(
                self.signaling_server.send_control(method, params),
                self._async_loop
            )

    def _on_turbo_connect(self, client_info: str):
        self.bridge.protocol_detected.emit("USB Turbo Pipe")

    def _on_turbo_disconnect(self):
        if self.active_protocol == "USB Turbo Pipe":
            self.bridge.client_disconnected.emit()

    def _on_turbo_frame(self, frame_rgb: np.ndarray):
        if self.active_protocol != "USB Turbo Pipe":
            self.bridge.protocol_detected.emit("USB Turbo Pipe")
        self._on_video_frame(frame_rgb)

    def _on_webrtc_frame(self, frame_rgb: np.ndarray):
        if self.active_protocol != "USB Turbo Pipe":
            if self.active_protocol != "WebRTC Studio":
                self.bridge.protocol_detected.emit("WebRTC Studio")
            self._on_video_frame(frame_rgb)

    def _on_video_frame(self, frame_rgb: np.ndarray):
        # Apply Digital Magnification
        if self.current_zoom > 1.01:
            try:
                h, w, c = frame_rgb.shape
                crop_h = max(2, int(h / self.current_zoom))
                crop_w = max(2, int(w / self.current_zoom))
                y1 = (h - crop_h) // 2
                x1 = (w - crop_w) // 2
                cropped = frame_rgb[y1:y1 + crop_h, x1:x1 + crop_w]
                try:
                    import cv2
                    resized_img = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
                    frame_rgb = np.ascontiguousarray(resized_img)
                except ImportError:
                    from PIL import Image
                    pil_img = Image.fromarray(cropped)
                    resized_img = pil_img.resize((w, h), Image.Resampling.BILINEAR)
                    frame_rgb = np.ascontiguousarray(np.array(resized_img))
            except Exception as e:
                logger.debug("Digital magnification error: %s", e)

        if self.mirror_preview:
            frame_rgb = np.ascontiguousarray(np.fliplr(frame_rgb))

        self.bridge.frame_received.emit(frame_rgb)
        if self.vcam_engine.is_running:
            self.vcam_engine.send_frame(frame_rgb)

    def _on_telemetry(self, data):
        self.bridge.telemetry_updated.emit(data)

    def _on_remote_control(self, method: str, params: Dict[str, Any]):
        self.bridge.remote_control_received.emit(method, params)

    def _on_client_disconnect(self):
        self.bridge.client_disconnected.emit()

    def _handle_protocol_detected(self, protocol_name: str):
        self.active_protocol = protocol_name
        if protocol_name == "USB Turbo Pipe":
            self.protocol_badge.setText("⚡ USB TURBO (ZERO-THROTTLE)")
            self.protocol_badge.setStyleSheet(
                "background-color: #064E3B; color: #34D399; font-size: 11px; "
                "font-weight: 800; padding: 4px 10px; border-radius: 6px; border: 1px solid #059669;"
            )
        else:
            self.protocol_badge.setText("📶 WEBRTC STUDIO")
            self.protocol_badge.setStyleSheet(
                "background-color: #1E3A8A; color: #93C5FD; font-size: 11px; "
                "font-weight: 800; padding: 4px 10px; border-radius: 6px; border: 1px solid #2563EB;"
            )

    def _handle_frame_received(self, frame_rgb):
        h, w = frame_rgb.shape[:2]
        self.video_widget.update_frame(frame_rgb, fps=float(self.config.stream.fps))
        if self.status_badge.objectName() != "StatusBadgeActive":
            self.status_badge.setText(f"STUDIO LIVE ({w}x{h})")
            self.status_badge.setObjectName("StatusBadgeActive")
            self.status_badge.style().unpolish(self.status_badge)
            self.status_badge.style().polish(self.status_badge)
            self.disconnect_btn.setEnabled(True)

        # Dynamic auto-adaptation: if received resolution changed, adapt virtual camera device
        if self.vcam_engine.is_running:
            if (self.vcam_engine.width, self.vcam_engine.height) != (w, h):
                logger.info("Auto-adapting Virtual Camera buffer to input stream: %dx%d -> %dx%d",
                            self.vcam_engine.width, self.vcam_engine.height, w, h)
                self.config.stream.width = w
                self.config.stream.height = h
                self.vcam_engine.resize(w, h, self.config.stream.fps)

            if self.vcam_engine.frame_count % 30 == 0:
                self.vcam_status_lbl.setText(
                    f"Virtual Cam: Active ({self.vcam_engine.backend}) — {w}x{h} ({self.vcam_engine.frame_count} frames)"
                )

    def _handle_approval_dialog(self, device_info, future):
        dialog = ApprovalDialog(device_info, self)
        accepted = (dialog.exec() == 1)
        self._async_loop.call_soon_threadsafe(future.set_result, accepted)

    def _handle_telemetry_ui(self, data):
        pct = data.get("batteryLevel", data.get("battery"))
        if pct is not None:
            self.battery_badge.setText(f"🔋 {pct}%")
            self.battery_badge.setVisible(True)
            self.video_widget.set_battery(pct)

    def _handle_remote_control_ui(self, method: str, params: Dict[str, Any]):
        """Handles incoming commands from the phone (e.g. phone user zoomed or toggled torch)."""
        if method == "camera.onZoomChanged":
            zoom = float(params.get("zoom", 1.0))
            self.current_zoom = zoom
            self.zoom_val_lbl.setText(f"{zoom:.1f}x")
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(int(zoom * 10))
            self.zoom_slider.blockSignals(False)
            self._update_stepper_visuals(zoom)

    def _update_stepper_visuals(self, active_zoom: float):
        for mult, btn in self.stepper_buttons:
            is_active = abs(active_zoom - mult) < 0.2
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _handle_user_disconnect(self):
        self.peer_manager.disconnect_peer()
        if self._async_loop and self._async_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.peer_manager.close(), self._async_loop)
            asyncio.run_coroutine_threadsafe(self.turbo_server.stop(), self._async_loop)
        self._handle_client_disconnected()

    def _handle_client_disconnected(self):
        self.active_protocol = "None"
        self.video_widget.set_disconnected()
        self.status_badge.setText("WAITING FOR DEVICE")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.protocol_badge.setText("BUS: USB/WI-FI AUTO")
        self.protocol_badge.setStyleSheet(
            "background-color: #27272A; color: #A1A1AA; font-size: 11px; "
            "font-weight: 700; padding: 4px 8px; border-radius: 6px;"
        )
        self.battery_badge.setVisible(False)
        self.disconnect_btn.setEnabled(False)
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
                self.vcam_btn.setText("⏹ Stop Virtual Webcam")
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

    # ── Camera & Remote Hardware Controls ──────────────────────────────
    def _on_quality_changed(self, index):
        data = self.quality_combo.currentData()
        if data:
            width, height, fps = data
            self.send_command_dual("camera.setQuality", {"width": width, "height": height, "fps": fps})
            self.config.stream.width = width
            self.config.stream.height = height
            self.config.stream.fps = fps
            if self.vcam_engine.is_running:
                self.vcam_engine.resize(width, height, fps)

    def _on_lens_changed(self, index):
        lens = self.lens_combo.currentData()
        if lens:
            self.send_command_dual("camera.setLens", {"lens": lens})
            if "front" in lens.lower():
                self.mirror_check.setChecked(True)

    def _on_torch_toggled(self, checked):
        self.torch_btn.setText("🔦 Flashlight: ON" if checked else "🔦 Flashlight: OFF")
        self.send_command_dual("camera.setTorch", {"enabled": checked})

    def _set_zoom_val(self, multiplier: float):
        self.zoom_slider.setValue(int(multiplier * 10))

    def _on_zoom_changed(self, val):
        factor = val / 10.0
        self.current_zoom = factor
        self.zoom_val_lbl.setText(f"{factor:.1f}x")
        self._update_stepper_visuals(factor)
        self.send_command_dual("camera.setZoom", {"zoom": factor})

    def _on_mirror_toggled(self, checked):
        self.mirror_preview = checked

    def _on_af_toggled(self, checked):
        self.focus_slider.setEnabled(not checked)
        self.send_command_dual("camera.setFocus", {
            "auto": checked,
            "distance": self.focus_slider.value() / 100.0
        })

    def _on_focus_changed(self, val):
        if not self.af_check.isChecked():
            self.send_command_dual("camera.setFocus", {
                "auto": False,
                "distance": val / 100.0
            })

    def _on_thermal_saver_toggled(self, checked):
        self.send_command_dual("camera.setThermalSaver", {"enabled": checked})

    def closeEvent(self, event):
        self.peer_manager.disconnect_peer()
        self.adb_bridge.stop()
        self.vcam_engine.stop()
        self.mdns_service.stop()
        if self._async_loop and self._async_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.turbo_server.stop(), self._async_loop)
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
