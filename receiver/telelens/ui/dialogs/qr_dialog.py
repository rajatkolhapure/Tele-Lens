"""
TeleLens QR Code Pairing Dialog.
Displays connection QR code for mobile scanning.
"""

from typing import Optional

try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
    from PyQt6.QtGui import QPixmap, QImage
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object

from telelens.discovery.qr_code import generate_qr_png_bytes


class QRCodeDialog(QDialog if PYQT6_AVAILABLE else object):
    """Pairing QR code presentation modal."""

    def __init__(self, payload_str: str, host: str, port: int, parent=None):
        if not PYQT6_AVAILABLE:
            return
        super().__init__(parent)
        self.setWindowTitle("Pair Mobile Device - TeleLens")
        self.setFixedSize(380, 480)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Scan to Connect")
        title.setObjectName("HeaderTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Open the TeleLens mobile app on your phone and scan this code:")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # QR Code Image
        png_bytes = generate_qr_png_bytes(payload_str)
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if png_bytes:
            q_img = QImage()
            q_img.loadFromData(png_bytes)
            pixmap = QPixmap.fromImage(q_img).scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            qr_label.setPixmap(pixmap)
        else:
            qr_label.setText("[QR Code Generation Unavailable]")

        layout.addWidget(qr_label)

        endpoint_lbl = QLabel(f"Endpoint: <code>ws://{host}:{port}/ws</code>")
        endpoint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(endpoint_lbl)

        close_btn = QPushButton("Done")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
