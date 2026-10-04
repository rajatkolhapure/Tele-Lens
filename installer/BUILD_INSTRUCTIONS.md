# TeleLens Windows Build & Packaging Guide

This document explains how to locally build the Windows installer for development
and testing before the CI pipeline takes over for production releases.

## Prerequisites

| Tool | Version | Download |
|:--|:--|:--|
| Python | 3.10+ | [python.org](https://python.org) |
| PyInstaller | 6.x | `pip install pyinstaller` |
| Inno Setup | 6.x | [jrsoftware.org](https://jrsoftware.org/isdl.php) |
| UPX (optional) | 4.x | [upx.github.io](https://upx.github.io) — makes the exe ~30% smaller |

---

## Step 1: Install Dependencies

```powershell
cd receiver
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
```

---

## Step 2: Build the PyInstaller One-Folder Bundle

```powershell
# From the /receiver directory
pyinstaller telelens.spec --clean
```

This produces `receiver/dist/TeleLens/TeleLens.exe` alongside all required DLLs.

> **Note:** On first build, PyInstaller will warn about missing hidden imports.
> All known hidden imports are already declared in `telelens.spec`.

---

## Step 3: Add the App Icon

Place a 256×256 `.ico` file at `installer/assets/telelens.ico` before running
Inno Setup. A placeholder path is already referenced in the `.iss` script.

---

## Step 4: Add Virtual Camera Driver DLLs

Copy the open-source OBS DirectShow DLLs into `installer/drivers/obs-virtualcam/`:

```
installer/
└── drivers/
    └── obs-virtualcam/
        ├── obs-virtualcam-startup.dll       (64-bit)
        └── obs-virtualcam-startup-32bit.dll (32-bit, for 32-bit processes)
```

These DLLs ship with **OBS Studio** (GPL-compatible). Alternatively, download the
standalone [obs-virtual-cam](https://github.com/Avasam/obs-virtual-cam) project
and build the DLLs, or extract them from an existing OBS installation.

---

## Step 5: Compile the Installer

Open **Inno Setup Compiler**, load `installer/telelens_installer.iss`, and click
**Build > Compile**. The output `TeleLens-Setup.exe` will be placed in
`dist-installer/`.

Or from the command line:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\telelens_installer.iss
```

---

## CI / Automated Builds

The GitHub Actions workflow (`.github/workflows/release.yml`) automates all steps
above on every version tag push, and attaches the resulting
`TeleLens-Setup.exe` as a release asset automatically.
