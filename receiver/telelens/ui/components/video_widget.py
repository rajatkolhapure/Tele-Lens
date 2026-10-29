"""
TeleLens Video Preview Widget.
Renders real-time video frames using QPainter with dynamic studio telemetry badges.
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
            self.setStyleSheet("background-color: #09090B; border: 1px solid #27272A; border-radius: 8px;")

        self._image: Optional[QImage] = None
        self._fps: float = 0.0
        self._resolution_str: str = "No Signal"
        self._battery_pct: Optional[int] = None
        self._is_active: bool = False

    def update_frame(self, frame_rgb: np.ndarray, fps: float = 30.0) -> None:
        """Receives RGB numpy array and updates view."""
        if not PYQT6_AVAILABLE:
            return

        if not frame_rgb.flags['C_CONTIGUOUS']:
            frame_rgb = np.ascontiguousarray(frame_rgb)

        h, w, c = frame_rgb.shape
        bytes_per_line = c * w
        # QImage format Format_RGB888 cloned into Qt-owned buffer
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        self._image = q_img
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
            img_w = self._image.width()
            img_h = self._image.height()
            if img_w > 0 and img_h > 0:
                widget_w = rect.width()
                widget_h = rect.height()
                scale = min(widget_w / img_w, widget_h / img_h)
                draw_w = max(1, int(img_w * scale))
                draw_h = max(1, int(img_h * scale))
                draw_x = (widget_w - draw_w) // 2
                draw_y = (widget_h - draw_h) // 2
                target_rect = QRect(draw_x, draw_y, draw_w, draw_h)
                painter.drawImage(target_rect, self._image)
        else:
            # Standby screen in sleek grey & black
            painter.fillRect(rect, QColor("#09090B"))
            painter.setPen(QColor("#71717A"))
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Waiting for phone connection...")

            painter.setFont(QFont("Segoe UI", 11))
            sub_rect = QRect(rect.x(), rect.y() + 45, rect.width(), rect.height())
            painter.setPen(QColor("#52525B"))
            painter.drawText(
                sub_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Scan the QR code or plug in USB cable to stream in studio quality",
            )

        # Draw Telemetry Badges in upper-left corner
        if self._is_active:
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(font)
            metrics = painter.fontMetrics()

            badge_text = f"STUDIO LIVE | {self._resolution_str} @ {self._fps:.1f} FPS"
            if self._battery_pct is not None:
                badge_text += f" | 🔋 {self._battery_pct}%"

            text_width = metrics.horizontalAdvance(badge_text)
            badge_width = text_width + 24

            painter.setPen(QPen(QColor("#3F3F46"), 1))
            painter.setBrush(QColor(18, 18, 20, 220))
            painter.drawRoundedRect(16, 16, badge_width, 32, 6, 6)

            # Draw green live dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#22C55E"))
            painter.drawEllipse(26, 28, 8, 8)

            painter.setPen(QColor("#E4E4E7"))
            painter.drawText(40, 37, badge_text)
