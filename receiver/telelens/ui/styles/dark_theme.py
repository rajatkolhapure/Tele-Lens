"""
TeleLens Modern Dark Theme QSS Stylesheet.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #12121E;
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QWidget {
    background-color: transparent;
    color: #E2E8F0;
    font-size: 13px;
}

QGroupBox {
    background-color: #1E1E2E;
    border: 1px solid #2E2E3E;
    border-radius: 8px;
    margin-top: 18px;
    font-weight: bold;
    padding-top: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #00ADB5;
}

QPushButton {
    background-color: #2D3748;
    color: #F7FAFC;
    border: 1px solid #4A5568;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #4A5568;
    border-color: #00ADB5;
}

QPushButton:pressed {
    background-color: #00ADB5;
    color: #12121E;
}

QPushButton#PrimaryButton {
    background-color: #00ADB5;
    color: #12121E;
    border: none;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#PrimaryButton:hover {
    background-color: #00D2DC;
}

QPushButton#DangerButton {
    background-color: #E53E3E;
    color: #FFFFFF;
    border: none;
}

QPushButton#DangerButton:hover {
    background-color: #FC8181;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #2D3748;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #00ADB5;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #00ADB5;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}

QComboBox {
    background-color: #1E1E2E;
    border: 1px solid #4A5568;
    border-radius: 6px;
    padding: 6px 12px;
    color: #E2E8F0;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1E1E2E;
    selection-background-color: #00ADB5;
    selection-color: #12121E;
    border: 1px solid #4A5568;
}

QLabel#HeaderTitle {
    font-size: 20px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#StatusBadge {
    background-color: #2D3748;
    color: #A0AEC0;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel#StatusBadgeActive {
    background-color: #22543D;
    color: #68D391;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: bold;
}
"""
