import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../models/device_payload.dart';
import '../services/webrtc_service.dart';
import '../services/mdns_discovery_service.dart';
import 'camera_stream_view.dart';

/// The home screen of TeleLens Mobile.
///
/// Priority UX hierarchy:
///   1. [PRIMARY]  Auto-discovered laptop card — one tap to connect.
///   2. [FALLBACK] USB ADB fast connect (wired, zero-latency).
///   3. [FALLBACK] QR code scanner.
///   4. [POWER-USER] Manual IP entry.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  // ── Discovery ─────────────────────────────────────────────────────────────
  final MdnsDiscoveryService _discovery = MdnsDiscoveryService();
  List<DiscoveredDevice> _devices = [];
  StreamSubscription<List<DiscoveredDevice>>? _sub;

  // ── UI State ──────────────────────────────────────────────────────────────
  bool _isConnecting = false;
  bool _showQrScanner = false;
  final TextEditingController _ipController =
      TextEditingController(text: '192.168.1.');

  // ── Glow animation for the discovery card ─────────────────────────────────
  late final AnimationController _glowController;
  late final Animation<double> _glowAnim;

  @override
  void initState() {
    super.initState();

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _glowAnim = Tween<double>(begin: 4.0, end: 18.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    _sub = _discovery.devicesStream.listen((devices) {
      if (mounted) setState(() => _devices = devices);
    });
    _discovery.startContinuousDiscovery();
  }

  @override
  void dispose() {
    _glowController.dispose();
    _sub?.cancel();
    _discovery.dispose();
    _ipController.dispose();
    super.dispose();
  }

  // ── Connection Logic ──────────────────────────────────────────────────────
  Future<void> _connectWithPayload(String rawPayload,
      {String displayName = 'TeleLens Studio'}) async {
    if (_isConnecting) return;
    setState(() => _isConnecting = true);

    try {
      final jsonMap = jsonDecode(rawPayload) as Map<String, dynamic>;
      final config = PairingConfig.fromJson(jsonMap);

      final service = WebRTCService(
        onConnectionStateChanged: (connected) {
          if (!connected && mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                  content: Text('Disconnected from TeleLens Studio.')),
            );
          }
        },
      );

      await service.connect(config.wsUrl, deviceName: _deviceName());

      if (mounted) {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => CameraStreamView(
              webrtcService: service,
              serverName: config.name,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connection failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isConnecting = false);
    }
  }

  String _deviceName() {
    // Returns a friendly device name; could use device_info_plus in production.
    return 'Android Phone';
  }

  void _connectToDevice(DiscoveredDevice device) =>
      _connectWithPayload(device.connectionPayload, displayName: device.name);

  void _connectUSB() => _connectWithPayload(jsonEncode({
        'app': 'telelens',
        'name': 'TeleLens via USB',
        'host': '127.0.0.1',
        'port': 8990,
        'ws_url': 'ws://127.0.0.1:8990/ws',
        'token': 'open',
      }));

  void _connectManual() {
    final ip = _ipController.text.trim();
    if (ip.isEmpty) return;
    _connectWithPayload(jsonEncode({
      'app': 'telelens',
      'name': 'TeleLens @ $ip',
      'host': ip,
      'port': 8990,
      'ws_url': 'ws://$ip:8990/ws',
      'token': 'open',
    }));
  }

  void _onQrDetect(BarcodeCapture capture) {
    if (_isConnecting) return;
    for (final barcode in capture.barcodes) {
      if (barcode.rawValue != null) {
        setState(() => _showQrScanner = false);
        _connectWithPayload(barcode.rawValue!);
        return;
      }
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D1A),
      body: SafeArea(
        child: _isConnecting
            ? _buildConnectingOverlay()
            : _showQrScanner
                ? _buildQrScanner()
                : _buildMainContent(),
      ),
    );
  }

  Widget _buildConnectingOverlay() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(color: Color(0xFF00ADB5), strokeWidth: 3),
          SizedBox(height: 20),
          Text(
            'Connecting…',
            style: TextStyle(
                color: Color(0xFF00ADB5),
                fontSize: 18,
                fontWeight: FontWeight.w600),
          ),
          SizedBox(height: 8),
          Text(
            'Waiting for laptop approval',
            style: TextStyle(color: Colors.white54, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildQrScanner() {
    return Stack(
      children: [
        MobileScanner(onDetect: _onQrDetect),
        // Viewfinder overlay
        Center(
          child: Container(
            width: 260,
            height: 260,
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFF00ADB5), width: 3),
              borderRadius: BorderRadius.circular(18),
            ),
          ),
        ),
        // Back button
        Positioned(
          top: 16,
          left: 16,
          child: GestureDetector(
            onTap: () => setState(() => _showQrScanner = false),
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(30),
              ),
              child: const Icon(Icons.arrow_back, color: Colors.white),
            ),
          ),
        ),
        const Positioned(
          bottom: 48,
          left: 0,
          right: 0,
          child: Text(
            'Point camera at the QR code\ndisplayed on your laptop',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
        ),
      ],
    );
  }

  Widget _buildMainContent() {
    return CustomScrollView(
      slivers: [
        // ── App Bar ─────────────────────────────────────────────────────────
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 28, 24, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: const Color(0xFF00ADB5),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.videocam, color: Colors.black, size: 22),
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      'TeleLens',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        letterSpacing: -0.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                const Text(
                  'Turn your phone into a 4K studio webcam',
                  style: TextStyle(color: Colors.white38, fontSize: 13),
                ),
                const SizedBox(height: 28),
              ],
            ),
          ),
        ),

        // ── Section: Auto-Discovered Laptops ────────────────────────────────
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: _buildDiscoverySection(),
          ),
        ),

        // ── Section: Other Ways to Connect ──────────────────────────────────
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
            child: Text(
              'OTHER WAYS TO CONNECT',
              style: TextStyle(
                color: Colors.white.withOpacity(0.3),
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
              ),
            ),
          ),
        ),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: _buildFallbackOptions(),
          ),
        ),

        const SliverToBoxAdapter(child: SizedBox(height: 32)),
      ],
    );
  }

  // ── Discovery Section ─────────────────────────────────────────────────────

  Widget _buildDiscoverySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'NEARBY LAPTOPS',
              style: TextStyle(
                color: Colors.white38,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(width: 10),
            if (_discovery.isScanning)
              const SizedBox(
                width: 12,
                height: 12,
                child: CircularProgressIndicator(
                  color: Color(0xFF00ADB5),
                  strokeWidth: 1.8,
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        if (_devices.isEmpty)
          _buildScanningPlaceholder()
        else
          ...List.generate(
            _devices.length,
            (i) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _buildDeviceCard(_devices[i]),
            ),
          ),
      ],
    );
  }

  Widget _buildScanningPlaceholder() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 20),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        children: [
          Icon(Icons.wifi_find,
              color: Colors.white.withOpacity(0.2), size: 36),
          const SizedBox(height: 12),
          const Text(
            'Scanning local network…',
            style: TextStyle(color: Colors.white54, fontSize: 14),
          ),
          const SizedBox(height: 4),
          Text(
            'Make sure TeleLens is running on\nyour laptop and both are on the same Wi-Fi.',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: Colors.white.withOpacity(0.25), fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildDeviceCard(DiscoveredDevice device) {
    return AnimatedBuilder(
      animation: _glowAnim,
      builder: (context, child) {
        return GestureDetector(
          onTap: () => _connectToDevice(device),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF0A2E2F), Color(0xFF0D1F2D)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                  color: const Color(0xFF00ADB5).withOpacity(0.7), width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00ADB5).withOpacity(0.22),
                  blurRadius: _glowAnim.value,
                  spreadRadius: _glowAnim.value * 0.25,
                ),
              ],
            ),
            child: Row(
              children: [
                // Icon & pulse
                Stack(
                  alignment: Alignment.center,
                  children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: const Color(0xFF00ADB5).withOpacity(0.12),
                      ),
                    ),
                    const Icon(Icons.laptop_mac,
                        color: Color(0xFF00ADB5), size: 28),
                  ],
                ),
                const SizedBox(width: 16),
                // Device details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        device.name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        device.host,
                        style: const TextStyle(
                            color: Color(0xFF00ADB5),
                            fontSize: 12,
                            fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ),
                // CTA Arrow
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 9),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00ADB5),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Connect',
                        style: TextStyle(
                            color: Colors.black,
                            fontWeight: FontWeight.bold,
                            fontSize: 13),
                      ),
                      SizedBox(width: 4),
                      Icon(Icons.arrow_forward, color: Colors.black, size: 16),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ── Fallback Options ──────────────────────────────────────────────────────

  Widget _buildFallbackOptions() {
    return Column(
      children: [
        // USB Connect
        _buildFallbackTile(
          icon: Icons.usb_rounded,
          title: '⚡  USB Cable (Lowest Latency)',
          subtitle: 'Plug in your phone & tap. Zero Wi-Fi jitter.',
          onTap: _connectUSB,
          accentColor: const Color(0xFF9B59B6),
        ),
        const SizedBox(height: 10),
        // QR Scan
        _buildFallbackTile(
          icon: Icons.qr_code_scanner,
          title: 'Scan QR Code',
          subtitle: 'Tap "Pair Device" on the laptop dashboard.',
          onTap: () => setState(() => _showQrScanner = true),
          accentColor: const Color(0xFF2980B9),
        ),
        const SizedBox(height: 10),
        // Manual IP
        _buildManualEntry(),
      ],
    );
  }

  Widget _buildFallbackTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    required Color accentColor,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          color: const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.07)),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: accentColor.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: accentColor, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14)),
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.4), fontSize: 12)),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: Colors.white.withOpacity(0.25)),
          ],
        ),
      ),
    );
  }

  Widget _buildManualEntry() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Manual IP Address',
            style: TextStyle(
                color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _ipController,
                  keyboardType: TextInputType.number,
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: '192.168.1.50',
                    hintStyle: TextStyle(
                        color: Colors.white.withOpacity(0.25), fontSize: 14),
                    filled: true,
                    fillColor: const Color(0xFF0D0D1A),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2D3748),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                  elevation: 0,
                ),
                onPressed: _connectManual,
                child: const Text('Go',
                    style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
