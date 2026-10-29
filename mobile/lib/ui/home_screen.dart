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
  Future<bool> _connectWithPayload(String rawPayload,
      {String displayName = 'TeleLens Studio', bool suppressError = false}) async {
    if (_isConnecting) return false;
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
              isUsb: config.host == '127.0.0.1' || config.host == 'localhost',
              host: config.host,
            ),
          ),
        );
      }
      return true;
    } catch (e) {
      if (mounted && !suppressError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connection failed: $e')),
        );
      }
      return false;
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

  Future<void> _connectUSB() async {
    final success = await _connectWithPayload(
      jsonEncode({
        'app': 'telelens',
        'name': 'TeleLens via USB',
        'host': '127.0.0.1',
        'port': 8990,
        'ws_url': 'ws://127.0.0.1:8990/ws',
        'token': 'open',
      }),
      suppressError: true,
    );

    if (!success && mounted) {
      _showUsbGuidanceDialog();
    }
  }

  void _showUsbGuidanceDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF121214),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: Color(0xFF27272A)),
        ),
        title: const Row(
          children: [
            Icon(Icons.usb, color: Color(0xFFE4E4E7), size: 22),
            SizedBox(width: 10),
            Text(
              'USB Cable Setup',
              style: TextStyle(
                color: Color(0xFFF4F4F5),
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'To stream with lowest latency over USB:',
              style: TextStyle(color: Color(0xFFA1A1AA), fontSize: 13),
            ),
            SizedBox(height: 12),
            Text(
              '1. Enable Developer Options on your phone.\n'
              '2. Turn ON "USB Debugging".\n'
              '3. Connect phone to laptop with a USB cable.\n'
              '4. Tap "Allow USB Debugging" when prompted.\n\n'
              'TeleLens on Windows will automatically detect your phone and route video directly.',
              style: TextStyle(
                color: Color(0xFFE4E4E7),
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Got it', style: TextStyle(color: Color(0xFFE4E4E7), fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

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
      backgroundColor: const Color(0xFF09090B),
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
          CircularProgressIndicator(color: Color(0xFFE4E4E7), strokeWidth: 3),
          SizedBox(height: 20),
          Text(
            'Connecting…',
            style: TextStyle(
                color: Color(0xFFF4F4F5),
                fontSize: 18,
                fontWeight: FontWeight.w600),
          ),
          SizedBox(height: 8),
          Text(
            'Waiting for laptop approval',
            style: TextStyle(color: Color(0xFFA1A1AA), fontSize: 13),
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
              border: Border.all(color: const Color(0xFFE4E4E7), width: 2.5),
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
                color: const Color(0xFF18181B).withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(30),
                border: Border.all(color: const Color(0xFF27272A)),
              ),
              child: const Icon(Icons.arrow_back, color: Color(0xFFF4F4F5)),
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
            style: TextStyle(color: Color(0xFFA1A1AA), fontSize: 14),
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
                    // Circle Logo with Grey Aura Glow
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: const Color(0xFF18181B),
                        border: Border.all(color: const Color(0xFF52525B), width: 1.5),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.white.withValues(alpha: 0.18),
                            blurRadius: 16,
                            spreadRadius: 2,
                          ),
                          BoxShadow(
                            color: const Color(0xFF71717A).withValues(alpha: 0.25),
                            blurRadius: 28,
                            spreadRadius: 4,
                          ),
                        ],
                      ),
                      child: Center(
                        child: Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: Color(0xFFF4F4F5),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    const Text(
                      'TeleLens',
                      style: TextStyle(
                        color: Color(0xFFF4F4F5),
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                const Text(
                  'Turn your phone into a studio webcam',
                  style: TextStyle(color: Color(0xFF71717A), fontSize: 13),
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
        const SliverToBoxAdapter(
          child: Padding(
            padding: EdgeInsets.fromLTRB(24, 24, 24, 10),
            child: Text(
              'OTHER WAYS TO CONNECT',
              style: TextStyle(
                color: Color(0xFF71717A),
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
                color: Color(0xFF71717A),
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
                  color: Color(0xFFE4E4E7),
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
        color: const Color(0xFF121214),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF27272A)),
      ),
      child: const Column(
        children: [
          Icon(Icons.wifi_find,
              color: Color(0xFF52525B), size: 32),
          SizedBox(height: 12),
          Text(
            'Scanning local network…',
            style: TextStyle(color: Color(0xFFA1A1AA), fontSize: 14),
          ),
          SizedBox(height: 4),
          Text(
            'Make sure TeleLens is open on your laptop\nand both devices are on the same Wi-Fi.',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: Color(0xFF71717A), fontSize: 12),
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
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: const Color(0xFF121214),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: const Color(0xFF3F3F46),
                width: 1.2,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.white.withValues(alpha: 0.08),
                  blurRadius: _glowAnim.value,
                  spreadRadius: _glowAnim.value * 0.15,
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF18181B),
                    border: Border.all(color: const Color(0xFF27272A)),
                  ),
                  child: const Icon(
                    Icons.laptop_mac,
                    color: Color(0xFFF4F4F5),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                // Device details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        device.name,
                        style: const TextStyle(
                          color: Color(0xFFF4F4F5),
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        device.host,
                        style: const TextStyle(
                            color: Color(0xFFA1A1AA),
                            fontSize: 12,
                            fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ),
                // CTA Button
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE4E4E7),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Connect',
                        style: TextStyle(
                            color: Color(0xFF09090B),
                            fontWeight: FontWeight.bold,
                            fontSize: 13),
                      ),
                      SizedBox(width: 4),
                      Icon(Icons.arrow_forward, color: Color(0xFF09090B), size: 15),
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
          title: 'USB Cable (Zero Latency)',
          subtitle: 'Plug in via USB. Uses automatic ADB channel.',
          onTap: _connectUSB,
        ),
        const SizedBox(height: 10),
        // QR Scan
        _buildFallbackTile(
          icon: Icons.qr_code_scanner,
          title: 'Scan QR Code',
          subtitle: 'Pair using camera and QR on your laptop.',
          onTap: () => setState(() => _showQrScanner = true),
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
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          color: const Color(0xFF121214),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF27272A)),
        ),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: const Color(0xFF18181B),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF27272A)),
              ),
              child: Icon(icon, color: const Color(0xFFE4E4E7), size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: const TextStyle(
                          color: Color(0xFFF4F4F5),
                          fontWeight: FontWeight.w600,
                          fontSize: 14)),
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: const TextStyle(
                          color: Color(0xFFA1A1AA), fontSize: 12)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Color(0xFF52525B)),
          ],
        ),
      ),
    );
  }

  Widget _buildManualEntry() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF121214),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF27272A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Manual IP Address',
            style: TextStyle(
                color: Color(0xFFF4F4F5), fontWeight: FontWeight.w600, fontSize: 14),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _ipController,
                  keyboardType: TextInputType.number,
                  style: const TextStyle(color: Color(0xFFF4F4F5), fontSize: 14),
                  decoration: InputDecoration(
                    hintText: '192.168.1.50',
                    hintStyle: const TextStyle(
                        color: Color(0xFF52525B), fontSize: 14),
                    filled: true,
                    fillColor: const Color(0xFF18181B),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFF27272A)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFF27272A)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFF52525B)),
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFE4E4E7),
                  foregroundColor: const Color(0xFF09090B),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 18, vertical: 14),
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
