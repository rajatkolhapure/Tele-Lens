# TeleLens Architecture Specification

## 1. Executive Summary
TeleLens is a high-performance, open-source, watermark-free Phone-to-Laptop webcam system engineered for 4K / 1440p / 1088x1088 Square HD studio broadcasting and video conferencing. It features a **Dual-Protocol Hybrid Architecture** that combines:
1. **Direct USB Turbo Frame Pipe**: Dedicated zero-latency, zero-congestion-control TCP media transport over the physical USB bus (Port 8991).
2. **WebRTC Studio Engine**: High-bitrate wireless streaming over local Wi-Fi with pinned SDP bitrates and anti-throttling resolution locks (Port 8990).

---

## 2. Dual-Protocol Transport Matrix

| Feature | Direct USB Turbo Pipe (Port 8991) | WebRTC Studio (Port 8990) |
| :--- | :--- | :--- |
| **Primary Medium** | Physical USB cable via ADB | Wi-Fi / Local Area Network |
| **Warmup Delay** | **0 ms (Instant 1088x1088 from Frame 1)** | 15–30s unless SDP bitrate is pinned |
| **Congestion Control** | None (100% fixed bitrate, zero drop) | Google Congestion Control (GCC) |
| **Latency** | **< 20 ms end-to-end** | 50–120 ms |
| **Transport Overhead** | Raw 22-byte header + binary payload | ICE, DTLS, SRTP, RTCP compound packets |
| **Resolution Stability** | **Locked (1088x1088 / 1080p / 4K)** | Dynamic downscale unless locked |

---

## 3. Component Architecture

### 3.1 Mobile Application (`mobile/`)
- **Framework**: Flutter (Dart) with direct platform channels to Camera2 (Android) and AVFoundation (iOS).
- **Transport Subsystems**:
  - `TurboStreamService`: Streams JPEG/RGB frames over TCP port 8991 directly via ADB USB reverse tunnel.
  - `WebRTCService`: Manages WebRTC peer connection, SDP munging, and DataChannel control commands.
- **Hardware Sensor Controller**:
  - Dedicated **1088x1088 Square HD** profile for 1:1 streaming, portrait-mode cropping, and content creation.
  - Lens switching (Ultra-wide <0.6x>, Wide <1.0x>, Telephoto <3x/5x>, Front selfie).
  - Manual focus, zoom steppers (1x, 2x, 3x, 5x), torch/flashlight toggle.
  - OLED Thermal Saver dimming layer.

### 3.2 Desktop Receiver (`receiver/`)
- **Async Streaming Core**:
  - `TurboStreamServer`: Listens on TCP port 8991, reading binary-framed payloads and decoding via OpenCV SIMD C++ routines in <2 ms.
  - `WebRTCPeerManager`: Manages WebRTC session with pinned 25–35 Mbps floor to prevent GCC quality degradation.
  - `ADBBridge`: Automatically maintains dual-channel port reversal:
    - Port 8990: Signaling, Gatekeeper Approval, JSON-RPC Hardware Controls
    - Port 8991: Direct Turbo Frame Pipe
- **Desktop UI (`PyQt6`)**:
  - Master Studio Dashboard with dark glassmorphism theme.
  - Live Connection Protocol Badge (`⚡ USB TURBO` vs `📶 WEBRTC STUDIO`).
  - Native 1088x1088 Square HD preset option in Stream Output Profile.
  - Real-time digital magnification (1.0x - 5.0x) and preview canvas.
- **Virtual Camera Engine**:
  - `pyvirtualcam` backend supporting OBS Virtual Camera DirectShow filter on Windows and `v4l2loopback` on Linux.
  - Accelerated OpenCV resizing and non-blocking frame ingestion pipeline.

---

## 4. Binary Wire Framing Protocol (Turbo Pipe)

Each frame transmitted over TCP port 8991 follows a compact 22-byte big-endian binary frame header:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Magic: 'TELE' (0x54454C45)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Payload Length (Bytes)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Width (uint16)        |        Height (uint16)        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Format (u8)  |   Flags (u8)  |                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
|                    Timestamp (uint64, Microseconds)           |
|                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Binary Frame Payload (JPEG / RGB)            |
|                              ...                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Format IDs: `1` = JPEG, `2` = Raw RGB24, `3` = H.264 NALU stream.
