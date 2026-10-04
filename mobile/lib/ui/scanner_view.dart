import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../models/device_payload.dart';
import '../services/webrtc_service.dart';
import 'camera_stream_view.dart';

class ScannerView extends StatefulWidget {
  const ScannerView({super.key});

  @override
  State<ScannerView> createState() => _ScannerViewState();
}

class _ScannerViewState extends State<ScannerView> {
  final TextEditingController _ipController = TextEditingController(text: "192.168.1.");
  bool _isConnecting = false;

  void _onDetect(BarcodeCapture capture) {
    if (_isConnecting) return;
    final List<Barcode> barcodes = capture.barcodes;
    for (final barcode in barcodes) {
      if (barcode.rawValue != null) {
        _connectWithPayload(barcode.rawValue!);
        break;
      }
    }
  }

  Future<void> _connectWithPayload(String rawPayload) async {
    setState(() => _isConnecting = true);

    try {
      final jsonMap = jsonDecode(rawPayload) as Map<String, dynamic>;
      final config = PairingConfig.fromJson(jsonMap);

      final webrtcService = WebRTCService(
        onConnectionStateChanged: (connected) {
          if (!connected && mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text("Disconnected from TeleLens Studio.")),
            );
          }
        },
      );

      await webrtcService.connect(config.wsUrl, deviceName: "Mobile Device");

      if (mounted) {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => CameraStreamView(
              webrtcService: webrtcService,
              serverName: config.name,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Connection failed: $e")),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isConnecting = false);
      }
    }
  }

  void _connectManual() {
    final ip = _ipController.text.trim();
    if (ip.isEmpty) return;
    final url = "ws://$ip:8990/ws";
    final manualPayload = jsonEncode({
      "app": "telelens",
      "name": "Manual TeleLens Server",
      "host": ip,
      "port": 8990,
      "ws_url": url,
      "token": "open"
    });
    _connectWithPayload(manualPayload);
  }

  void _connectUSB() {
    // USB ADB reverse maps tcp:8990 to phone loopback 127.0.0.1:8990
    final usbPayload = jsonEncode({
      "app": "telelens",
      "name": "TeleLens via USB ADB",
      "host": "127.0.0.1",
      "port": 8990,
      "ws_url": "ws://127.0.0.1:8990/ws",
      "token": "open"
    });
    _connectWithPayload(usbPayload);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF12121E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E1E2E),
        title: const Text("Connect to TeleLens Studio", style: TextStyle(fontWeight: FontWeight.bold)),
        elevation: 0,
      ),
      body: Column(
        children: [
          // QR Scanner Viewport
          Expanded(
            flex: 3,
            child: Stack(
              alignment: Alignment.center,
              children: [
                MobileScanner(onDetect: _onDetect),
                Container(
                  width: 250,
                  height: 250,
                  decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xFF00ADB5), width: 3),
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                if (_isConnecting)
                  Container(
                    color: Colors.black54,
                    child: const Center(
                      child: CircularProgressIndicator(color: Color(0xFF00ADB5)),
                    ),
                  ),
              ],
            ),
          ),

          // Manual Entry & USB ADB Fast Connect
          Expanded(
            flex: 2,
            child: Container(
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(
                color: Color(0xFF1E1E2E),
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00ADB5),
                      foregroundColor: const Color(0xFF12121E),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: _connectUSB,
                    icon: const Icon(Icons.usb, size: 22),
                    label: const Text("⚡ One-Click USB ADB Connect", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _ipController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: "Enter Laptop IP (e.g. 192.168.1.50)",
                            hintStyle: const TextStyle(color: Colors.white38),
                            filled: true,
                            fillColor: const Color(0xFF12121E),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2D3748),
                          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: _connectManual,
                        child: const Text("Connect", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
