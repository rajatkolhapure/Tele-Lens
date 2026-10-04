"""
TeleLens Virtual Camera Driver Diagnostic Dialog.
Provides real-time inspection and setup guidance for the virtual webcam driver.
"""

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
    )
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object

from telelens.driver.diagnostics import DriverDiagnostics


class DiagnosticDialog(QDialog if PYQT6_AVAILABLE else object):
    """Driver diagnostic modal."""

    def __init__(self, parent=None):
        if not PYQT6_AVAILABLE:
            return
        super().__init__(parent)
        self.setWindowTitle("Virtual Camera Diagnostics - TeleLens")
        self.setFixedSize(500, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Virtual Camera Driver Status")
        title.setObjectName("HeaderTitle")
        layout.addWidget(title)

        result = DriverDiagnostics.run_all()

        status_card = QFrame()
        status_card.setStyleSheet("background-color: #1E1E2E; border-radius: 6px; padding: 10px;")
        card_layout = QVBoxLayout(status_card)

        if result.driver_found:
            status_text = f"<b style='color:#68D391;'>[READY] {result.driver_name} Detected</b><br/>" \
                          f"Backend: <code>{result.backend}</code><br/>" \
                          f"{result.details}"
        else:
            status_text = f"<b style='color:#FC8181;'>[MISSING] Virtual Camera Driver Not Found</b><br/>" \
                          f"{result.details}"

        status_lbl = QLabel(status_text)
        status_lbl.setWordWrap(True)
        card_layout.addWidget(status_lbl)
        layout.addWidget(status_card)

        if not result.driver_found:
            help_lbl = QLabel("<b>Setup Instructions:</b>")
            layout.addWidget(help_lbl)

            steps_box = QTextEdit()
            steps_box.setReadOnly(True)
            steps_content = "\n".join(f"{i}. {s}" for i, s in enumerate(result.troubleshooting_steps, 1))
            steps_box.setText(steps_content)
            layout.addWidget(steps_box)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
