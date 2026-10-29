"""
TeleLens Studio Modern Minimalist Obsidian & Charcoal Stylesheet.
Styled to match the modern Studio Pro mobile interface with glassmorphism cards,
sleek pill buttons, glowing status badges, and refined typography.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #09090B;
    color: #F4F4F8;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QWidget {
    background-color: transparent;
    color: #F4F4F8;
    font-size: 13px;
}

/* Card Container Panels matching mobile design */
QFrame#SidebarCard {
    background-color: #121214;
    border: 1px solid #22222E;
    border-radius: 12px;
    padding: 14px;
}

QFrame#SidebarCard:hover {
    border-color: #2F2F40;
}

QLabel#CardTitle {
    font-size: 12px;
    font-weight: 700;
    color: #D4D4E0;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}

/* Standard Buttons */
QPushButton {
    background-color: #1A1A24;
    color: #F4F4F8;
    border: 1px solid #2A2A3A;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #242434;
    border-color: #3E3E54;
}

QPushButton:pressed {
    background-color: #161620;
}

/* Stepper Pill Buttons matching Android Zoom Chips */
QPushButton#StepperButton {
    padding: 6px 12px;
    font-size: 11px;
    background-color: #181822;
    border: 1px solid #282838;
    border-radius: 6px;
    font-weight: 700;
    color: #A1A1B2;
}

QPushButton#StepperButton:hover {
    background-color: #262638;
    color: #FFFFFF;
    border-color: #4A4A62;
}

QPushButton#StepperButton[active="true"] {
    background-color: #E4E4E7;
    color: #09090D;
    border-color: #FFFFFF;
}

/* Primary Action Button (White Pill) */
QPushButton#PrimaryButton {
    background-color: #E4E4E7;
    color: #09090D;
    border: 1px solid #FFFFFF;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover {
    background-color: #FFFFFF;
    border-color: #FFFFFF;
}

QPushButton#PrimaryButton:pressed {
    background-color: #CCCCCC;
}

/* Destructive / Danger Button */
QPushButton#DangerButton {
    background-color: #1C1215;
    color: #F87171;
    border: 1px solid #451A1D;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton#DangerButton:hover {
    background-color: #2A151A;
    border-color: #EF4444;
    color: #FFA4A4;
}

/* Torch Flashlight Toggle Button */
QPushButton#TorchButton {
    background-color: #181822;
    color: #A1A1B2;
    border: 1px solid #282838;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#TorchButton:hover {
    background-color: #222232;
    border-color: #3A3A50;
}

QPushButton#TorchButton:checked {
    background-color: #2D200E;
    color: #FBBF24;
    border: 1px solid #F59E0B;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #1C1C26;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #E4E4EC;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 1px solid #A1A1B2;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #F4F4F8;
    border-color: #FFFFFF;
}

/* Dropdowns / ComboBoxes */
QComboBox {
    background-color: #161620;
    border: 1px solid #262636;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F4F4F8;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #3C3C52;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #161620;
    selection-background-color: #262638;
    selection-color: #FFFFFF;
    border: 1px solid #323246;
    border-radius: 6px;
    padding: 4px;
}

/* Checkboxes */
QCheckBox {
    color: #D4D4E0;
    font-size: 12px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #36364A;
    background-color: #161620;
}

QCheckBox::indicator:checked {
    background-color: #E4E4EC;
    border-color: #FFFFFF;
}

/* Header & Badges */
QLabel#HeaderTitle {
    font-size: 20px;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.4px;
}

QLabel#StatusBadge {
    background-color: #14141C;
    color: #8E8E9E;
    border: 1px solid #242432;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#StatusBadgeActive {
    background-color: #0E1C14;
    color: #4ADE80;
    border: 1px solid #1E4628;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#BatteryBadge {
    background-color: #14141C;
    color: #F4F4F8;
    border: 1px solid #242432;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
}
"""
