"""
TeleLens QR Code Pairing Dialog.
Displays high-contrast connection QR code for instant mobile camera scanning with dynamic network adapter selection.
"""

from typing import List, Optional

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QFrame
    )
    from PyQt6.QtGui import QPixmap, QImage
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object

from telelens.discovery.qr_code import generate_pairing_payload, generate_qr_png_bytes
from telelens.discovery.mdns import get_local_ip_addresses


class QRCodeDialog(QDialog if PYQT6_AVAILABLE else object):
    """Pairing QR code presentation modal with multi-interface adapter switching."""

    def __init__(self, initial_payload: str, current_ip: str, port: int, parent=None):
        if not PYQT6_AVAILABLE:
            return
        super().__init__(parent)
        self.setWindowTitle("Pair Mobile Device — TeleLens")
        self.setFixedSize(420, 540)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #09090B;
                color: #F4F4F5;
            }
            QLabel {
                color: #D4D4D8;
                font-size: 13px;
            }
            QComboBox {
                background-color: #18181B;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 12px;
                color: #FAFAFA;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #27272A;
                color: #FAFAFA;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
        """)

        self.port = port
        self.all_ips = get_local_ip_addresses()
        if "127.0.0.1" not in self.all_ips:
            self.all_ips.append("127.0.0.1")
        self.selected_ip = current_ip if current_ip in self.all_ips else self.all_ips[0]

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header Title
        title = QLabel("Scan with TeleLens App")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Point your phone's camera or in-app scanner at the QR code below:")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # High-contrast white card container for optical barcode readability
        qr_card = QFrame()
        qr_card.setStyleSheet("background-color: #FFFFFF; border-radius: 12px; padding: 12px;")
        qr_card_layout = QVBoxLayout(qr_card)
        qr_card_layout.setContentsMargins(8, 8, 8, 8)
        qr_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_card_layout.addWidget(self.qr_label)
        layout.addWidget(qr_card)

        # IP Network Adapter Selector
        adapter_layout = QHBoxLayout()
        adapter_lbl = QLabel("Host Adapter:")
        adapter_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.ip_combo = QComboBox()
        for ip in self.all_ips:
            label = f"{ip} (USB Cable / Loopback)" if ip.startswith("127.") else f"{ip} (Wi-Fi / LAN)"
            self.ip_combo.addItem(label, ip)

        idx = self.ip_combo.findData(self.selected_ip)
        if idx >= 0:
            self.ip_combo.setCurrentIndex(idx)
        self.ip_combo.currentIndexChanged.connect(self._on_ip_selection_changed)

        adapter_layout.addWidget(adapter_lbl)
        adapter_layout.addWidget(self.ip_combo, stretch=1)
        layout.addLayout(adapter_layout)

        # Endpoint display
        self.endpoint_lbl = QLabel()
        self.endpoint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.endpoint_lbl.setStyleSheet("font-family: monospace; font-size: 11px; color: #71717A;")
        layout.addWidget(self.endpoint_lbl)

        # Render initial QR
        self._update_qr_display()

        # Close Button
        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _on_ip_selection_changed(self, index: int):
        ip = self.ip_combo.currentData()
        if ip:
            self.selected_ip = ip
            self._update_qr_display()

    def _update_qr_display(self):
        payload = generate_pairing_payload(host_ip=self.selected_ip, port=self.port)
        png_bytes = generate_qr_png_bytes(payload)

        if png_bytes:
            q_img = QImage()
            q_img.loadFromData(png_bytes)
            pixmap = QPixmap.fromImage(q_img).scaled(
                220, 220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.qr_label.setPixmap(pixmap)
        else:
            self.qr_label.setText("[QR Generation Unavailable]")

        self.endpoint_lbl.setText(f"ws://{self.selected_ip}:{self.port}/ws")
