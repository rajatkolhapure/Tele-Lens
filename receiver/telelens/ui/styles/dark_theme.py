"""
TeleLens Modern Minimalist Grey & Black QSS Stylesheet.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #09090B;
    color: #F4F4F5;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QWidget {
    background-color: transparent;
    color: #F4F4F5;
    font-size: 13px;
}

QGroupBox {
    background-color: #121214;
    border: 1px solid #27272A;
    border-radius: 8px;
    margin-top: 18px;
    font-weight: 600;
    padding-top: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #D4D4D8;
    font-size: 12px;
    letter-spacing: 0.5px;
}

QPushButton {
    background-color: #18181B;
    color: #F4F4F5;
    border: 1px solid #27272A;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #27272A;
    border-color: #3F3F46;
}

QPushButton:pressed {
    background-color: #3F3F46;
    color: #FFFFFF;
}

QPushButton:checked {
    background-color: #27272A;
    border-color: #A1A1AA;
    color: #FAFAFA;
}

QPushButton#StepperButton {
    padding: 5px 10px;
    font-size: 11px;
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 5px;
    font-weight: bold;
}

QPushButton#StepperButton:hover {
    background-color: #27272A;
    border-color: #52525B;
}

QPushButton#StepperButton:checked {
    background-color: #E4E4E7;
    color: #09090B;
    border-color: #E4E4E7;
}

QPushButton#PrimaryButton {
    background-color: #E4E4E7;
    color: #09090B;
    border: 1px solid #E4E4E7;
    font-size: 13px;
    font-weight: bold;
}

QPushButton#PrimaryButton:hover {
    background-color: #FFFFFF;
    border-color: #FFFFFF;
}

QPushButton#PrimaryButton:pressed {
    background-color: #D4D4D8;
}

QPushButton#DangerButton {
    background-color: #18181B;
    color: #EF4444;
    border: 1px solid #3F3F46;
}

QPushButton#DangerButton:hover {
    background-color: #27272A;
    color: #F87171;
    border-color: #EF4444;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #27272A;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #71717A;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #F4F4F5;
    border: 1px solid #71717A;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #FFFFFF;
    border-color: #A1A1AA;
}

QComboBox {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 6px;
    padding: 6px 12px;
    color: #F4F4F5;
}

QComboBox:hover {
    border-color: #3F3F46;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #18181B;
    selection-background-color: #27272A;
    selection-color: #FFFFFF;
    border: 1px solid #3F3F46;
}

QCheckBox {
    color: #D4D4D8;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #3F3F46;
    background-color: #18181B;
}

QCheckBox::indicator:checked {
    background-color: #E4E4E7;
    border-color: #E4E4E7;
}

QLabel#HeaderTitle {
    font-size: 18px;
    font-weight: 700;
    color: #FAFAFA;
    letter-spacing: -0.3px;
}

QLabel#StatusBadge {
    background-color: #18181B;
    color: #71717A;
    border: 1px solid #27272A;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

QLabel#StatusBadgeActive {
    background-color: #18181B;
    color: #F4F4F5;
    border: 1px solid #71717A;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
"""
