# TeleLens Architecture Specification

## 1. Executive Summary
TeleLens is a high-performance, open-source, watermark-free Phone-to-Laptop webcam system engineered for 4K / 1440p 60 FPS studio broadcasting and video conferencing. It decouples the mobile camera capture engine from the desktop virtual device pipeline using standard WebRTC with hardware acceleration.

---

## 2. Component Architecture

### 2.1 Mobile Application (`mobile/`)
- **Framework**: Flutter (Dart) with direct platform channels to Camera2 (Android) and AVFoundation (iOS).
- **Video Pipeline**: Captures raw camera frames in 4K/1440p/1080p, feeding into the platform's hardware H.264/H.265/VP8 encoder.
- **Audio Pipeline**: Real-time microphone capture with Opus encoding (48 kHz stereo/mono).
- **Signaling & Discovery**:
  - Broadcasts presence via mDNS (`_telelens._tcp`).
  - Scans desktop QR code containing the signaling server endpoints and one-time session challenge.
  - Automatically listens on loopback TCP port when USB ADB tethering is activated.
- **Hardware Sensor Controller**:
  - Lens switching (Ultra-wide <0.6x>, Wide <1.0x>, Telephoto <3x/5x>, Front selfie).
  - Manual exposure (ISO range, shutter speed, EV compensation).
  - Manual focus (macro, distance slider, auto-focus lock).
  - White balance presets & manual Kelvin temperature.
  - Flashlight / Torch toggle.
  - Thermal saver: Dims screen to 5% brightness and draws minimal OLED black UI during active stream to prevent overheating.

---

### 2.2 Desktop Receiver (`receiver/`)
- **Engine**: Python 3.10+ async core (`asyncio`) leveraging `aiortc` for real-time peer connection and media demuxing.
- **UI Framework**: PyQt6 desktop application with custom dark theme, hardware-accelerated video rendering, and live stream telemetry (FPS, bitrate, packet loss, phone battery).
- **Virtual Camera Engine**:
  - `pyvirtualcam` backend supporting OBS Virtual Camera DirectShow filter on Windows and `v4l2loopback` on Linux.
  - Automatically provisions virtual camera frame buffers matching the phone stream resolution (e.g., 3840x2160, 2560x1440, or 1920x1080).
- **Audio Engine**: Passthrough to virtual audio loopback devices (e.g. VB-Audio Cable or DirectShow audio loopback).
- **Approval Gatekeeper**:
  - When an incoming connection request is signaled from the phone, the laptop UI raises an interactive approval modal displaying:
    - Phone Model (e.g., "Google Pixel 8 Pro")
    - IP Address / USB connection indicator
    - Requested stream profile
  - User must click **Accept** before SDP answer is generated and media transmission starts.

---

### 2.3 Shared Control Protocol (`shared/protocol/`)
- **Transport**: WebRTC DataChannel (reliable, ordered mode).
- **Format**: JSON-RPC 2.0 messages for low-latency bidirectional command and telemetry exchange.
  - Laptop -> Phone: `camera.setTorch`, `camera.setLens`, `camera.setZoom`, `camera.setExposure`, `camera.setFocus`.
  - Phone -> Laptop: `telemetry.battery`, `telemetry.thermalState`, `telemetry.sensorCaps`.

---

## 3. Connectivity & Pairing Flow

1. **Discovery Phase**:
   - Laptop starts local signaling server on a randomized/configured port (default: 8990) and advertises service via mDNS (`_telelens._tcp.local.`).
   - Laptop displays pairing QR code on the desktop dashboard.
   - If USB cable is plugged in, `start_adb_tunnel.ps1` or the built-in ADB manager binds `adb reverse tcp:8990 tcp:8990`.
2. **Handshake & Gatekeeper**:
   - Phone establishes WebSocket connection to the laptop signaling server.
   - Phone transmits `DeviceHello` (device name, OS, camera capabilities).
   - Laptop displays: **"Device 'Google Pixel 8 Pro' requests to stream. Accept / Reject?"**.
   - Upon user approval, WebRTC SDP Offer/Answer and ICE candidates are exchanged.
3. **Active Streaming**:
   - WebRTC media tracks (video & audio) begin transmission.
   - Laptop demuxes video frames and writes to `pyvirtualcam`.
   - DataChannel exchanges real-time telemetry and camera controls.
