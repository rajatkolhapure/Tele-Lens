"""
TeleLens Video Preview Widget.
Renders real-time video frames using QPainter with live telemetry badges.
"""

from typing import Optional
import numpy as np

try:
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtGui import QPainter, QImage, QColor, QFont, QPen
    from PyQt6.QtCore import Qt, QRect
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object


class VideoPreviewWidget(QWidget if PYQT6_AVAILABLE else object):
    """Studio video preview canvas."""

    def __init__(self, parent=None):
        if PYQT6_AVAILABLE:
            super().__init__(parent)
            self.setMinimumSize(640, 360)
            self.setStyleSheet("background-color: #0A0A12; border-radius: 8px;")

        self._image: Optional[QImage] = None
        self._fps: float = 0.0
        self._resolution_str: str = "No Signal"
        self._battery_pct: Optional[int] = None
        self._is_active: bool = False

    def update_frame(self, frame_rgb: np.ndarray, fps: float = 30.0) -> None:
        """Receives RGB numpy array and updates view."""
        if not PYQT6_AVAILABLE:
            return

        h, w, c = frame_rgb.shape
        bytes_per_line = c * w
        # QImage format Format_RGB888
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self._image = q_img.copy()  # detached copy for rendering
        self._fps = fps
        self._resolution_str = f"{w}x{h}"
        self._is_active = True
        self.update()

    def set_disconnected(self) -> None:
        self._image = None
        self._is_active = False
        self._resolution_str = "No Signal"
        self._fps = 0.0
        if PYQT6_AVAILABLE:
            self.update()

    def set_battery(self, pct: int) -> None:
        self._battery_pct = pct
        if PYQT6_AVAILABLE:
            self.update()

    def paintEvent(self, event) -> None:
        if not PYQT6_AVAILABLE:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        if self._image is not None and not self._image.isNull():
            # Draw video scaled preserving aspect ratio
            scaled_img = self._image.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (rect.width() - scaled_img.width()) // 2
            y = (rect.height() - scaled_img.height()) // 2
            painter.drawImage(x, y, scaled_img)
        else:
            # Placeholder standby screen
            painter.fillRect(rect, QColor("#0E0E18"))
            painter.setPen(QColor("#4A5568"))
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Waiting for phone connection...")

            painter.setFont(QFont("Segoe UI", 11))
            sub_rect = QRect(rect.x(), rect.y() + 45, rect.width(), rect.height())
            painter.drawText(
                sub_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Scan the QR code or enable USB ADB to stream in 4K/1440p",
            )

        # Draw Telemetry Badges in upper-left corner
        if self._is_active:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(16, 16, 220, 34, 6, 6)

            painter.setPen(QColor("#00ADB5"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            badge_text = f"LIVE | {self._resolution_str} @ {self._fps:.1f} FPS"
            if self._battery_pct is not None:
                badge_text += f" | 🔋 {self._battery_pct}%"
            painter.drawText(26, 38, badge_text)
