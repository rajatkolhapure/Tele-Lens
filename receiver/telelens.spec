# -*- mode: python ; coding: utf-8 -*-
# TeleLens PyInstaller Build Specification
# Build with:  pyinstaller telelens.spec
# Output:      dist/TeleLens/TeleLens.exe  (one-folder)

import sys
from pathlib import Path

block_cipher = None

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    ['telelens/ui/app.py'],
    pathex=['receiver'],
    binaries=[],
    datas=[
        # Include the shared protocol schema files for runtime use
        ('../shared/protocol', 'protocol'),
    ],
    hiddenimports=[
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
    icon='installer/assets/telelens.ico',
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
