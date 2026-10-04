# TeleLens 📸⚡
> **Professional, Watermark-Free, Studio-Grade Phone-to-Laptop Webcam**

TeleLens transforms your smartphone into a high-fidelity 4K/1440p webcam and studio camera for your laptop or desktop. Built from the ground up to be 100% open-source, subscription-free, and watermark-free.

---

## 🌟 Key Highlights

- 💎 **Studio-Grade 4K & 1440p Streaming**: Native 30/60 FPS high-bitrate video stream over low-latency WebRTC.
- 🚫 **Zero Watermarks, Zero Ads**: Pure open-source engineering. No artificial resolution caps or paywalls.
- 🎛️ **Full Remote Hardware Controls**:
  - Front / Rear / Ultra-Wide / Telephoto lens switching.
  - Manual sensor tuning: Torch/flashlight toggle, manual focus, exposure & ISO locking, white balance, and smooth digital/optical zoom.
- 🎙️ **Synchronized Audio Passthrough**: High-fidelity mobile microphone passthrough directly to a virtual microphone device.
- 🛡️ **Laptop Gatekeeper Approval**: Incoming phone connections request permission on your laptop dashboard (`"Accept / Reject"`) before any video feed is initialized.
- 🔌 **Seamless Hybrid Connectivity**:
  - **Wi-Fi LAN**: Zero-configuration auto-discovery via mDNS/Bonjour + QR code pairing fallback.
  - **USB ADB Tethering**: Automatic port-forwarding detection for zero-jitter, wired low-latency streaming.
- ❄️ **Thermal & Battery Management**: Integrated screen dimming, idle throttling, and phone battery telemetry monitoring.
- 🎥 **Virtual Camera Backend**: Direct integration with OBS Virtual Camera and DirectShow via `pyvirtualcam` for seamless compatibility with Zoom, Microsoft Teams, Google Meet, Discord, and OBS Studio.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│       Phone (Flutter App)       │                 │     Laptop (Python + PyQt6)     │
│                                 │                 │                                 │
│  • Camera2 / AVFoundation       │   mDNS / QR     │  • Zero-Config Discovery        │
│  • flutter_webrtc Pipeline      ├────────────────►│  • Approval Gatekeeper          │
│  • Multi-Lens & Manual Sensor   │                 │  • PyQt6 Studio Dashboard       │
│  • Thermal Saver Mode           │   WebRTC A/V    │  • pyvirtualcam (OBS Driver)    │
│  • High-Fidelity Audio Stream   │◄═══════════════►│  • Virtual Mic Audio Loopback   │
│  • Bidirectional DataChannel    │  (Wi-Fi / USB)  │  • Remote Camera Control Sliders│
└─────────────────────────────────┘                 └─────────────────────────────────┘
```

---

## 📁 Repository Structure

```
rajats-take-on-webcams/
├── mobile/                   # Flutter mobile client (iOS / Android)
│   ├── lib/                  # WebRTC client, sensor controller, UI overlay
│   └── pubspec.yaml
├── receiver/                 # Python PyQt6 laptop receiver application
│   ├── telelens/             # Core receiver engine, WebRTC, pyvirtualcam driver
│   ├── pyproject.toml        # Dependencies and packaging
│   └── requirements.txt
├── shared/                   # Protocol definitions (WebRTC signaling & JSON-RPC)
│   └── protocol/
├── docs/                     # Technical architecture & setup guides
├── scripts/                  # Development & ADB tethering automation scripts
├── LICENSE                   # MIT License
└── README.md
```

---

## 🚀 Quick Start

### 1. Laptop Receiver Setup
Requirements: Python 3.10+ (tested on Python 3.14).

```powershell
# Navigate to the receiver directory
cd receiver

# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install receiver dependencies
pip install -r requirements.txt

# Run the TeleLens desktop application
python -m telelens.ui.app
```

### 2. Virtual Camera Driver Setup
TeleLens outputs directly to the OBS Virtual Camera driver.
- If OBS Studio is installed, the virtual camera is available automatically.
- Alternatively, run the built-in TeleLens Diagnostic Wizard in the desktop app for one-click setup assistance.

### 3. Phone App Setup
Open `mobile/` in Flutter or Android Studio, or connect your Android/iOS device and run:
```bash
cd mobile
flutter run --release
```

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).
