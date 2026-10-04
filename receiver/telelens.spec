# -*- mode: python ; coding: utf-8 -*-
# TeleLens PyInstaller Build Specification
# Build with:  pyinstaller telelens.spec
# Output:      dist/TeleLens/TeleLens.exe  (one-folder)

import sys
from pathlib import Path

# Resolve repository root and receiver directory from spec location
RECEIVER_DIR = Path(SPECPATH).resolve()
ROOT_DIR = RECEIVER_DIR.parent
ICON_PATH = ROOT_DIR / 'installer' / 'assets' / 'telelens.ico'

block_cipher = None

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[str(RECEIVER_DIR)],
    binaries=[],
    datas=[
        # Include telelens package source tree directly in the bundle
        (str(RECEIVER_DIR / 'telelens'), 'telelens'),
        # Include the shared protocol schema files for runtime use
        (str(ROOT_DIR / 'shared' / 'protocol'), 'protocol'),
    ],
    hiddenimports=[
        # TeleLens core modules
        'telelens',
        'telelens.config',
        'telelens.ui',
        'telelens.ui.app',
        'telelens.ui.styles',
        'telelens.ui.styles.dark_theme',
        'telelens.ui.components',
        'telelens.ui.components.video_widget',
        'telelens.ui.dialogs',
        'telelens.ui.dialogs.approval_dialog',
        'telelens.ui.dialogs.qr_dialog',
        'telelens.ui.dialogs.diagnostic_dialog',
        'telelens.discovery',
        'telelens.discovery.mdns',
        'telelens.discovery.qr_code',
        'telelens.driver',
        'telelens.driver.diagnostics',
        'telelens.driver.virtual_cam',
        'telelens.webrtc',
        'telelens.webrtc.signaling',
        'telelens.webrtc.peer',
        'telelens.webrtc.controls',
        # aiortc / PyAV codec plugins
        'av.codec.codec',
        'av.filter',
        'av.stream',
        # aiohttp internals
        'aiohttp',
        'aiohttp.web_ws',
        # zeroconf
        'zeroconf',
        'zeroconf._dns',
        'zeroconf._services',
        'zeroconf._utils',
        # qrcode renderer
        'qrcode',
        'qrcode.image.pil',
        # pyvirtualcam
        'pyvirtualcam',
        # PIL
        'PIL',
        'PIL.Image',
        # PyQt6 extras that may not be auto-detected
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.QtCore',
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ ────────────────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ────────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TeleLens',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # No console window — pure GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)

# ── COLLECT ────────────────────────────────────────────────────────────────────
# One-folder mode: all DLLs and data files next to TeleLens.exe
# Inno Setup will then compress and package this folder into Setup.exe
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TeleLens',
)
