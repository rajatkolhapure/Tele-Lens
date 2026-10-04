"""
TeleLens Gatekeeper Approval Dialog.
Prompts laptop user when an incoming device requests to stream.
"""

from typing import Dict, Any

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
    )
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object


class ApprovalDialog(QDialog if PYQT6_AVAILABLE else object):
    """Approval gatekeeper modal."""

    def __init__(self, device_info: Dict[str, Any], parent=None):
        if not PYQT6_AVAILABLE:
            return
        super().__init__(parent)
        self.setWindowTitle("Incoming Stream Request - TeleLens")
        self.setFixedSize(420, 240)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Device Connection Request")
        title.setObjectName("HeaderTitle")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ADB5;")
        layout.addWidget(title)

        desc = QLabel(
            f"The following device is requesting to stream video & audio to this laptop:"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Card container for device details
        card = QFrame()
        card.setStyleSheet("background-color: #1E1E2E; border-radius: 6px; padding: 12px;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)

        device_name = device_info.get("device_name", "Unknown Phone")
        device_os = device_info.get("os", "Android / iOS")
        stream_profile = device_info.get("stream_profile", "4K / 1440p")

        name_lbl = QLabel(f"<b>Device:</b> {device_name}")
        os_lbl = QLabel(f"<b>Operating System:</b> {device_os}")
        profile_lbl = QLabel(f"<b>Stream Profile:</b> {stream_profile}")

        card_layout.addWidget(name_lbl)
        card_layout.addWidget(os_lbl)
        card_layout.addWidget(profile_lbl)
        layout.addWidget(card)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        reject_btn = QPushButton("Reject")
        reject_btn.setObjectName("DangerButton")
        reject_btn.clicked.connect(self.reject)

        accept_btn = QPushButton("Accept Stream")
        accept_btn.setObjectName("PrimaryButton")
        accept_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(reject_btn)
        btn_layout.addWidget(accept_btn)
        layout.addLayout(btn_layout)
