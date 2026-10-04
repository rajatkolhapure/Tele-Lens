# TeleLens Mobile Client (Flutter) 📱

The mobile capture client for **TeleLens**, streaming 4K/1440p camera frames and audio to your laptop over WebRTC.

## Features
- **4K & High-FPS Camera Pipeline**: Native hardware encoder feeding low-latency WebRTC streams.
- **Bi-directional Remote Hardware Controls**: Torch toggle, camera switching, manual focus, exposure, and zoom via WebRTC DataChannel.
- **Thermal Saver Mode**: Dims the OLED display to 5% brightness while streaming to conserve battery and avoid thermal throttling.
- **Hybrid Pairing**:
  - Instant pairing via QR code scan.
  - Automatic Wi-Fi local network discovery (mDNS).
  - One-click USB ADB wired tethering connection (`ws://127.0.0.1:8990/ws`).

## Quickstart

### Prerequisites
- [Flutter SDK](https://flutter.dev) (version 3.0.0+)
- Connected Android device with USB Debugging enabled, or iOS device with Developer Mode.

### Running on Device
```bash
# Navigate to mobile project directory
cd mobile

# Install Flutter dependencies
flutter pub get

# Run on your connected phone in release mode for best 4K performance
flutter run --release
```

### Wired USB ADB Connection
For the lowest latency with zero Wi-Fi packet jitter:
1. Plug your phone into your laptop via USB.
2. Run the helper script on your laptop:
   ```powershell
   ..\scripts\start_adb_tunnel.ps1
   ```
3. In the mobile app, tap **⚡ One-Click USB ADB Connect**.
