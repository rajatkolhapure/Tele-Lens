import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:battery_plus/battery_plus.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import '../services/webrtc_service.dart';
import '../models/device_payload.dart';

class CameraStreamView extends StatefulWidget {
  final WebRTCService webrtcService;
  final String serverName;

  const CameraStreamView({
    super.key,
    required this.webrtcService,
    required this.serverName,
  });

  @override
  State<CameraStreamView> createState() => _CameraStreamViewState();
}

class _CameraStreamViewState extends State<CameraStreamView> {
  final Battery _battery = Battery();
  final RTCVideoRenderer _localRenderer = RTCVideoRenderer();
  Timer? _telemetryTimer;

  // Stream & Hardware States
  bool _thermalSaverActive = false;
  String _activeLens = "Rear Main";
  bool _torchActive = false;
  double _currentZoom = 1.0;
  String _activeQuality = "1080p @ 30 FPS";
  int _batteryLevel = 100;
  bool _rendererInitialized = false;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable();
    _hookWebRTC();
    _initRenderer();
    _startTelemetryLoop();
  }

  void _hookWebRTC() {
    widget.webrtcService.onRemoteControl = _handleRemoteCommand;
    widget.webrtcService.onConnectionStateChanged = (connected) {
      if (!connected && mounted) {
        _handleDisconnectCleanup();
      }
    };
  }

  Future<void> _initRenderer() async {
    try {
      await _localRenderer.initialize();
      if (widget.webrtcService.localStream != null) {
        _localRenderer.srcObject = widget.webrtcService.localStream;
      }
      if (mounted) {
        setState(() {
          _rendererInitialized = true;
        });
      }
    } catch (e) {
      debugPrint("Error initializing RTCVideoRenderer: $e");
    }
  }

  void _startTelemetryLoop() {
    _telemetryTimer = Timer.periodic(const Duration(seconds: 4), (timer) async {
      try {
        final level = await _battery.batteryLevel;
        final state = await _battery.batteryState;
        if (mounted) {
          setState(() => _batteryLevel = level);
        }
        final data = TelemetryData(
          batteryLevel: level,
          isCharging: state == BatteryState.charging,
          thermalState: "normal",
        );
        widget.webrtcService.sendTelemetry(data);
      } catch (e) {
        debugPrint("Error collecting battery telemetry: $e");
      }
    });
  }

  // Handle incoming remote commands from Windows Studio Dashboard
  void _handleRemoteCommand(String method, Map<String, dynamic> params) async {
    debugPrint("Mobile received command: $method $params");
    if (method == "camera.setTorch") {
      final enabled = params['enabled'] as bool? ?? false;
      final ok = await widget.webrtcService.setTorch(enabled);
      if (ok && mounted) {
        setState(() => _torchActive = enabled);
      }
    } else if (method == "camera.setLens") {
      final ok = await widget.webrtcService.switchCamera();
      if (ok && mounted) {
        setState(() {
          _activeLens = (_activeLens == "Rear Main") ? "Front Selfie" : "Rear Main";
        });
      }
    } else if (method == "camera.setZoom") {
      final zoom = (params['zoom'] is num) ? (params['zoom'] as num).toDouble() : 1.0;
      final ok = await widget.webrtcService.setZoom(zoom);
      if (ok && mounted) {
        setState(() => _currentZoom = zoom);
      }
    } else if (method == "camera.setQuality") {
      final width = params['width'] as int? ?? 1920;
      final height = params['height'] as int? ?? 1080;
      final fps = params['fps'] as int? ?? 30;
      final ok = await widget.webrtcService.setQuality(width, height, fps);
      if (ok && mounted) {
        setState(() {
          _activeQuality = "${height}p @ ${fps}FPS";
        });
      }
    } else if (method == "camera.setThermalSaver") {
      final enabled = params['enabled'] as bool? ?? false;
      if (mounted) setState(() => _thermalSaverActive = enabled);
    } else if (method == "session.disconnect") {
      _handleDisconnectCleanup();
    }
  }

  // Local user interactions from phone on-screen toolbar
  Future<void> _toggleTorch() async {
    final target = !_torchActive;
    final ok = await widget.webrtcService.setTorch(target);
    if (ok && mounted) {
      setState(() => _torchActive = target);
    }
  }

  Future<void> _switchLens() async {
    final ok = await widget.webrtcService.switchCamera();
    if (ok && mounted) {
      setState(() {
        _activeLens = (_activeLens == "Rear Main") ? "Front Selfie" : "Rear Main";
      });
    }
  }

  Future<void> _applyZoom(double factor) async {
    final ok = await widget.webrtcService.setZoom(factor);
    if (ok && mounted) {
      setState(() => _currentZoom = factor);
    }
  }

  void _userDisconnect() {
    widget.webrtcService.sendDisconnect();
    _handleDisconnectCleanup();
  }

  void _handleDisconnectCleanup() {
    if (mounted) {
      widget.webrtcService.dispose();
      Navigator.of(context).pop();
    }
  }

  @override
  void dispose() {
    _telemetryTimer?.cancel();
    _localRenderer.srcObject = null;
    _localRenderer.dispose();
    WakelockPlus.disable();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_rendererInitialized &&
        _localRenderer.srcObject == null &&
        widget.webrtcService.localStream != null) {
      _localRenderer.srcObject = widget.webrtcService.localStream;
    }

    return Scaffold(
      backgroundColor: const Color(0xFF09090B),
      body: Stack(
        children: [
          // 1. Live Camera Viewfinder Feed
          Positioned.fill(
            child: (_rendererInitialized && _localRenderer.srcObject != null)
                ? RTCVideoView(
                    _localRenderer,
                    mirror: _activeLens.contains("Front"),
                    objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover,
                  )
                : Container(
                    color: const Color(0xFF09090B),
                    child: const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircularProgressIndicator(
                            color: Color(0xFFE4E4E7),
                            strokeWidth: 2.5,
                          ),
                          SizedBox(height: 16),
                          Text(
                            "Starting Camera Stream…",
                            style: TextStyle(
                              color: Color(0xFFA1A1AA),
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
          ),

          // 2. Thermal Saver Dimming Layer
          if (_thermalSaverActive)
            GestureDetector(
              onTap: () => setState(() => _thermalSaverActive = false),
              child: Container(
                color: Colors.black.withValues(alpha: 0.95),
                child: const Center(
                  child: Text(
                    "Thermal Saver Mode Active\nTap screen to brighten",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Color(0xFF71717A), fontSize: 13),
                  ),
                ),
              ),
            ),

          // 3. Top HUD: Connection Info, Quality Pill, Battery, Disconnect
          Positioned(
            top: 48,
            left: 16,
            right: 16,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Laptop host & status
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF18181B).withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF27272A)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: Color(0xFF22C55E),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        widget.serverName,
                        style: const TextStyle(
                          color: Color(0xFFF4F4F5),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),

                // Quality Badge & Battery
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF18181B).withValues(alpha: 0.85),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF27272A)),
                      ),
                      child: Text(
                        _activeQuality,
                        style: const TextStyle(
                          color: Color(0xFFE4E4E7),
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF18181B).withValues(alpha: 0.85),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF27272A)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.battery_charging_full_rounded, color: Color(0xFF22C55E), size: 14),
                          const SizedBox(width: 4),
                          Text(
                            "$_batteryLevel%",
                            style: const TextStyle(
                              color: Color(0xFFF4F4F5),
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    // Quick Disconnect
                    GestureDetector(
                      onTap: _userDisconnect,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF18181B).withValues(alpha: 0.85),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFEF4444).withValues(alpha: 0.5)),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.power_settings_new, color: Color(0xFFEF4444), size: 14),
                            SizedBox(width: 4),
                            Text(
                              "Stop",
                              style: TextStyle(
                                color: Color(0xFFEF4444),
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // 4. Floating On-Screen Controls Toolbar (Bottom Center)
          Positioned(
            bottom: 32,
            left: 16,
            right: 16,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Floating Toolbar Card
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF18181B).withValues(alpha: 0.90),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF27272A)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.5),
                        blurRadius: 16,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      // Torch Toggle
                      IconButton(
                        onPressed: _toggleTorch,
                        tooltip: "Torch",
                        icon: Icon(
                          _torchActive ? Icons.flashlight_on_rounded : Icons.flashlight_off_rounded,
                          color: _torchActive ? const Color(0xFFFBBF24) : const Color(0xFFA1A1AA),
                          size: 22,
                        ),
                      ),

                      // Lens Switcher (Front/Rear)
                      IconButton(
                        onPressed: _switchLens,
                        tooltip: "Switch Camera",
                        icon: const Icon(
                          Icons.flip_camera_ios_rounded,
                          color: Color(0xFFE4E4E7),
                          size: 22,
                        ),
                      ),

                      // Zoom Steppers (1x, 2x, 3x, 5x)
                      _buildZoomChip(1.0, "1x"),
                      _buildZoomChip(2.0, "2x"),
                      _buildZoomChip(3.0, "3x"),
                      _buildZoomChip(5.0, "5x"),

                      // Thermal Saver
                      IconButton(
                        onPressed: () => setState(() => _thermalSaverActive = !_thermalSaverActive),
                        tooltip: "Dim Screen (Thermal Saver)",
                        icon: Icon(
                          _thermalSaverActive ? Icons.brightness_high_rounded : Icons.brightness_2_rounded,
                          color: const Color(0xFFA1A1AA),
                          size: 20,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildZoomChip(double factor, String label) {
    final bool isSelected = (_currentZoom - factor).abs() < 0.2;
    return GestureDetector(
      onTap: () => _applyZoom(factor),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFE4E4E7) : const Color(0xFF27272A),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? const Color(0xFF09090B) : const Color(0xFFF4F4F5),
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}
