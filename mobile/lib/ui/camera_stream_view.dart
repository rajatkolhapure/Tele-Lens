import 'dart:async';
import 'package:flutter/material.dart';
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
  Timer? _telemetryTimer;
  bool _thermalSaverActive = false;
  double _screenOpacity = 1.0;
  String _activeLens = "Rear Main";
  bool _torchActive = false;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable();
    _startTelemetryLoop();
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
        _screenOpacity = _thermalSaverActive ? 0.05 : 1.0;
      } else if (method == "camera.setLens") {
        _activeLens = params['lens'] ?? _activeLens;
      }
    });
  }

  @override
  void dispose() {
    _telemetryTimer?.cancel();
    WakelockPlus.disable();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // Viewfinder simulation / camera preview placeholder
          Center(
            child: Container(
              color: Colors.black87,
              child: const Center(
                child: Text(
                  "4K STUDIO STREAM ACTIVE",
                  style: TextStyle(
                    color: Color(0xFF00ADB5),
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2.0,
                  ),
                ),
              ),
            ),
          ),

          // Thermal Saver Dimming Layer
          if (_thermalSaverActive)
            Container(
              color: Colors.black.withOpacity(0.95),
              child: const Center(
                child: Text(
                  "Thermal Saver Mode Active\nTap screen to brighten",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white30, fontSize: 13),
                ),
              ),
            ),

          // On-screen Live Badges
          Positioned(
            top: 48,
            left: 20,
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E1E2E),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFF00ADB5)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.videocam, color: Color(0xFF00ADB5), size: 16),
                      const SizedBox(width: 6),
                      Text(
                        "Streaming to: ${widget.serverName}",
                        style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.redAccent.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Text(
                    "LIVE 4K",
                    style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
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
                Text(
                  "Lens: $_activeLens | Flash: ${_torchActive ? 'ON' : 'OFF'}",
                  style: const TextStyle(color: Colors.white70, fontSize: 13),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red.shade700,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: () {
                    widget.webrtcService.dispose();
                    Navigator.of(context).pop();
                  },
                  icon: const Icon(Icons.call_end, size: 18),
                  label: const Text("Disconnect"),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
