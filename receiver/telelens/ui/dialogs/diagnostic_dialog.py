"""
TeleLens Virtual Camera Driver Diagnostic Dialog.
Provides real-time inspection, setup guidance, and 1-click elevated driver registration for the virtual webcam driver.
"""

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame, QMessageBox
    )
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object

from telelens.driver.diagnostics import DriverDiagnostics


class DiagnosticDialog(QDialog if PYQT6_AVAILABLE else object):
    """Driver diagnostic modal with automated administrative installer."""

    def __init__(self, parent=None):
        if not PYQT6_AVAILABLE:
            return
        super().__init__(parent)
        self.setWindowTitle("Virtual Camera Diagnostics — TeleLens")
        self.setFixedSize(540, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #09090B;
                color: #F4F4F5;
            }
            QLabel {
                color: #D4D4D8;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #121214;
                border: 1px solid #27272A;
                border-radius: 6px;
                color: #D4D4D8;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton {
                background-color: #18181B;
                color: #FAFAFA;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
            QPushButton#ActionBtn {
                background-color: #E4E4E7;
                color: #09090B;
                border: 1px solid #E4E4E7;
                font-weight: bold;
            }
            QPushButton#ActionBtn:hover {
                background-color: #FFFFFF;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(14)
        self.layout.setContentsMargins(22, 22, 22, 22)

        title = QLabel("System & Virtual Camera Diagnostics")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        self.layout.addWidget(title)

        self.status_card = QFrame()
        self.status_card.setStyleSheet("background-color: #121214; border: 1px solid #27272A; border-radius: 8px; padding: 12px;")
        self.card_layout = QVBoxLayout(self.status_card)
        self.status_lbl = QLabel()
        self.status_lbl.setWordWrap(True)
        self.card_layout.addWidget(self.status_lbl)
        self.layout.addWidget(self.status_card)

        self.help_lbl = QLabel("<b>Details & Compatibility Notes:</b>")
        self.layout.addWidget(self.help_lbl)

        self.steps_box = QTextEdit()
        self.steps_box.setReadOnly(True)
        self.layout.addWidget(self.steps_box)

        # Action Buttons
        self.btn_layout = QHBoxLayout()
        self.register_btn = QPushButton("🛡️ Register Driver (Administrator)")
        self.register_btn.setObjectName("ActionBtn")
        self.register_btn.clicked.connect(self._run_driver_install)
        self.btn_layout.addWidget(self.register_btn)

        self.refresh_btn = QPushButton("🔄 Re-Check")
        self.refresh_btn.clicked.connect(self._refresh_diagnostics)
        self.btn_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.btn_layout.addWidget(self.close_btn)

        self.layout.addLayout(self.btn_layout)

        self._refresh_diagnostics()

    def _refresh_diagnostics(self):
        result = DriverDiagnostics.run_all()

        if result.driver_found:
            status_text = (
                f"<b style='color:#22C55E; font-size:14px;'>✓ {result.driver_name} Ready</b><br/>"
                f"<span style='color:#A1A1AA;'>Target Backend: <code>{result.backend}</code></span><br/>"
                f"<span style='color:#D4D4D8;'>{result.details}</span>"
            )
            self.register_btn.setEnabled(False)
            self.register_btn.setText("✓ Driver Registered")
        else:
            status_text = (
                f"<b style='color:#F87171; font-size:14px;'>✗ Virtual Camera Driver Not Registered</b><br/>"
                f"<span style='color:#D4D4D8;'>{result.details}</span>"
            )
            self.register_btn.setEnabled(result.can_auto_register)
            if not result.can_auto_register:
                self.register_btn.setText("Driver DLL Not Found")

        self.status_lbl.setText(status_text)

        steps_content = "\n".join(f"{i}. {s}" for i, s in enumerate(result.troubleshooting_steps, 1))
        self.steps_box.setText(steps_content)

    def _run_driver_install(self):
        QMessageBox.information(
            self,
            "Driver Registration",
            "Windows will now display an Administrator (UAC) prompt to register the virtual camera driver DLL. Please click 'Yes'."
        )
        success = DriverDiagnostics.register_driver_elevated()
        self._refresh_diagnostics()
        if success:
            QMessageBox.information(
                self,
                "Success",
                "Virtual camera registration executed! Re-checking status..."
            )
        else:
            QMessageBox.warning(
                self,
                "Notice",
                "Registration command finished. If not registered, ensure you approved the Windows administrator prompt."
            )
