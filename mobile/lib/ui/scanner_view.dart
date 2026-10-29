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
  final MobileScannerController _scannerController = MobileScannerController(
    formats: [BarcodeFormat.qrCode],
    detectionSpeed: DetectionSpeed.noDuplicates,
    facing: CameraFacing.back,
    torchEnabled: false,
  );
  bool _isConnecting = false;
  bool _isTorchOn = false;

  @override
  void dispose() {
    _scannerController.dispose();
    _ipController.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_isConnecting) return;
    final List<Barcode> barcodes = capture.barcodes;
    for (final barcode in barcodes) {
      final val = barcode.rawValue;
      if (val != null && val.trim().isNotEmpty) {
        _connectWithPayload(val.trim());
        break;
      }
    }
  }

  Future<void> _connectWithPayload(String rawPayload) async {
    if (_isConnecting) return;
    setState(() => _isConnecting = true);

    try {
      String wsUrl = "";
      String serverName = "TeleLens Studio";

      if (rawPayload.startsWith("{") && rawPayload.endsWith("}")) {
        // Standard JSON payload
        final jsonMap = jsonDecode(rawPayload) as Map<String, dynamic>;
        final config = PairingConfig.fromJson(jsonMap);
        wsUrl = config.wsUrl;
        serverName = config.name.isNotEmpty ? config.name : serverName;
      } else if (rawPayload.startsWith("ws://") || rawPayload.startsWith("wss://")) {
        // Direct WebSocket URL
        wsUrl = rawPayload;
      } else if (rawPayload.contains(":")) {
        // Host:Port format
        wsUrl = "ws://$rawPayload/ws";
      } else if (RegExp(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$').hasMatch(rawPayload)) {
        // Plain IP
        wsUrl = "ws://$rawPayload:8990/ws";
      } else {
        throw FormatException("Unrecognized connection format: $rawPayload");
      }

      final webrtcService = WebRTCService(
        onConnectionStateChanged: (connected) {
          if (!connected && mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text("Disconnected from TeleLens Studio.")),
            );
          }
        },
      );

      await webrtcService.connect(wsUrl, deviceName: "Mobile Device");

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => CameraStreamView(
              webrtcService: webrtcService,
              serverName: serverName,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Connection failed: $e"),
            backgroundColor: const Color(0xFFEF4444),
          ),
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
    _connectWithPayload(url);
  }

  void _connectUSB() {
    // USB ADB reverse maps tcp:8990 to phone loopback 127.0.0.1:8990
    _connectWithPayload("ws://127.0.0.1:8990/ws");
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF09090B),
      appBar: AppBar(
        backgroundColor: const Color(0xFF121214),
        title: const Text(
          "Connect to TeleLens Studio",
          style: TextStyle(color: Color(0xFFF4F4F5), fontWeight: FontWeight.bold),
        ),
        elevation: 0,
        iconTheme: const IconThemeData(color: Color(0xFFF4F4F5)),
        actions: [
          IconButton(
            icon: Icon(
              _isTorchOn ? Icons.flash_on : Icons.flash_off,
              color: _isTorchOn ? Colors.amber : const Color(0xFFF4F4F5),
            ),
            onPressed: () async {
              await _scannerController.toggleTorch();
              setState(() => _isTorchOn = !_isTorchOn);
            },
          ),
          IconButton(
            icon: const Icon(Icons.flip_camera_ios, color: Color(0xFFF4F4F5)),
            onPressed: () => _scannerController.switchCamera(),
          ),
        ],
      ),
      body: Column(
        children: [
          // QR Scanner Viewport with Scan Reticle
          Expanded(
            flex: 3,
            child: Stack(
              alignment: Alignment.center,
              children: [
                MobileScanner(
                  controller: _scannerController,
                  onDetect: _onDetect,
                ),
                // Crisp target framing
                Container(
                  width: 260,
                  height: 260,
                  decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xFFE4E4E7), width: 2.5),
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                Positioned(
                  bottom: 24,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.black.withAlpha(180),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Text(
                      "Align QR code inside box",
                      style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                  ),
                ),
                if (_isConnecting)
                  Container(
                    color: Colors.black54,
                    child: const Center(
                      child: CircularProgressIndicator(color: Color(0xFFE4E4E7)),
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
                color: Color(0xFF121214),
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFE4E4E7),
                      foregroundColor: const Color(0xFF09090B),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      elevation: 0,
                    ),
                    onPressed: _connectUSB,
                    icon: const Icon(Icons.usb, size: 22),
                    label: const Text(
                      "USB Cable Connect (Zero Latency)",
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _ipController,
                          style: const TextStyle(color: Color(0xFFF4F4F5)),
                          decoration: InputDecoration(
                            hintText: "Laptop IP (e.g. 192.168.1.50)",
                            hintStyle: const TextStyle(color: Color(0xFF52525B)),
                            filled: true,
                            fillColor: const Color(0xFF18181B),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF27272A)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF27272A)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                              borderSide: const BorderSide(color: Color(0xFF52525B)),
                            ),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF18181B),
                          foregroundColor: const Color(0xFFF4F4F5),
                          side: const BorderSide(color: Color(0xFF27272A)),
                          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          elevation: 0,
                        ),
                        onPressed: _connectManual,
                        child: const Text("Connect", style: TextStyle(fontWeight: FontWeight.bold)),
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
