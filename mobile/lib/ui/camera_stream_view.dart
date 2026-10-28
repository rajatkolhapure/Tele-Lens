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
  bool _thermalSaverActive = false;
  String _activeLens = "Rear Main";
  bool _torchActive = false;
  bool _rendererInitialized = false;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable();
    _initRenderer();
    _startTelemetryLoop();
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

  void handleRemoteCommand(String method, Map<String, dynamic> params) {
    setState(() {
      if (method == "camera.setTorch") {
        _torchActive = params['enabled'] ?? false;
      } else if (method == "camera.setThermalSaver") {
        _thermalSaverActive = params['enabled'] ?? false;
      } else if (method == "camera.setLens") {
        _activeLens = params['lens'] ?? _activeLens;
      }
    });
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
    // If localStream became available after renderer init
    if (_rendererInitialized &&
        _localRenderer.srcObject == null &&
        widget.webrtcService.localStream != null) {
      _localRenderer.srcObject = widget.webrtcService.localStream;
    }

    return Scaffold(
      backgroundColor: const Color(0xFF09090B),
      body: Stack(
        children: [
          // Live Camera Viewfinder Feed
          Positioned.fill(
            child: (_rendererInitialized && _localRenderer.srcObject != null)
                ? RTCVideoView(
                    _localRenderer,
                    mirror: false,
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

          // Thermal Saver Dimming Layer
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

          // On-screen Minimalist Badges
          Positioned(
            top: 48,
            left: 20,
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                  decoration: BoxDecoration(
                    color: const Color(0xFF18181B).withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF27272A)),
                  ),
                  child: Row(
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
                        "Streaming to ${widget.serverName}",
                        style: const TextStyle(
                          color: Color(0xFFF4F4F5),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF18181B).withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF27272A)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        "LIVE",
                        style: TextStyle(
                          color: Color(0xFFEF4444),
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.5,
                        ),
                      ),
                      SizedBox(width: 4),
                      Text(
                        "HD",
                        style: TextStyle(
                          color: Color(0xFFA1A1AA),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Bottom Bar: Lens info & Disconnect Button
          Positioned(
            bottom: 30,
            left: 20,
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF18181B).withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF27272A)),
                  ),
                  child: Text(
                    "$_activeLens | ${_torchActive ? 'Torch ON' : 'Torch OFF'}",
                    style: const TextStyle(
                      color: Color(0xFFA1A1AA),
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF18181B),
                    foregroundColor: const Color(0xFFEF4444),
                    side: const BorderSide(color: Color(0xFF27272A)),
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  ),
                  onPressed: () {
                    widget.webrtcService.dispose();
                    Navigator.of(context).pop();
                  },
                  icon: const Icon(Icons.close, size: 16),
                  label: const Text(
                    "Disconnect",
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
