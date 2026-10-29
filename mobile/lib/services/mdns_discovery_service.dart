import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';

/// Represents a discovered TeleLens laptop on the local network.
class DiscoveredDevice {
  final String name;
  final String host;
  final int port;
  final String wsUrl;

  const DiscoveredDevice({
    required this.name,
    required this.host,
    required this.port,
    required this.wsUrl,
  });

  String get connectionPayload => jsonEncode({
        'app': 'telelens',
        'name': name,
        'host': host,
        'port': port,
        'ws_url': wsUrl,
        'token': 'open',
      });

  @override
  bool operator ==(Object other) =>
      other is DiscoveredDevice && other.host == host && other.port == port;

  @override
  int get hashCode => Object.hash(host, port);
}

/// Discovers TeleLens laptop receivers on the local Wi-Fi LAN.
///
/// Strategy:
///   1. Probe common LAN subnets (192.168.x.x, 10.0.x.x) by attempting a
///      WebSocket HTTP upgrade check on port 8990 in parallel.
///   2. Emit discovered devices as a stream so the UI can react in real time.
///
/// A proper multicast-DNS library is ideal for production, but requires a
/// native plugin. This subnet-scan approach works without any extra
/// dependencies beyond dart:io and gives instant beginner-friendly discovery
/// on any home router without needing mDNS support.
class MdnsDiscoveryService {
  static const int _signalingPort = 8990;

  final StreamController<List<DiscoveredDevice>> _devicesController =
      StreamController<List<DiscoveredDevice>>.broadcast();

  Stream<List<DiscoveredDevice>> get devicesStream => _devicesController.stream;

  final List<DiscoveredDevice> _discovered = [];
  bool _isScanning = false;
  Timer? _scanTimer;

  bool get isScanning => _isScanning;

  /// Starts a periodic full scan every 5 seconds.
  void startContinuousDiscovery() {
    _isScanning = true;
    _runScan(); // Immediate first scan
    _scanTimer = Timer.periodic(const Duration(seconds: 5), (_) => _runScan());
  }

  Future<void> _runScan() async {
    final subnets = await _detectLocalSubnets();
    if (subnets.isEmpty) return;

    final List<Future<void>> probes = [];
    for (final subnet in subnets) {
      for (int host = 1; host <= 254; host++) {
        final ip = '$subnet.$host';
        probes.add(_probeHost(ip));
      }
    }

    await Future.wait(probes, eagerError: false);
  }

  Future<void> _probeHost(String ip) async {
    try {
      final socket = await Socket.connect(
        ip,
        _signalingPort,
        timeout: const Duration(milliseconds: 350),
      );
      // Port is open — try an HTTP GET to validate it is a TeleLens server
      socket.write(
          'GET /ws HTTP/1.1\r\nHost: $ip:$_signalingPort\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n');
      await socket.flush();

      String response = '';
      final completer = Completer<void>();
      late StreamSubscription<Uint8List> sub;
      sub = socket.listen((data) {
        response += String.fromCharCodes(data);
        if (response.contains('101') || response.contains('HTTP/1.1')) {
          sub.cancel();
          if (!completer.isCompleted) completer.complete();
        }
      }, onError: (_) {
        if (!completer.isCompleted) completer.complete();
      }, onDone: () {
        if (!completer.isCompleted) completer.complete();
      });

      await completer.future
          .timeout(const Duration(milliseconds: 400), onTimeout: () {});
      await socket.close();

      // Accept any server that responds with an HTTP 101 Switching Protocols
      if (response.contains('101') || response.contains('TeleLens')) {
        final device = DiscoveredDevice(
          name: 'TeleLens Studio @ $ip',
          host: ip,
          port: _signalingPort,
          wsUrl: 'ws://$ip:$_signalingPort/ws',
        );
        if (!_discovered.contains(device)) {
          _discovered.add(device);
          if (!_devicesController.isClosed) {
            _devicesController.add(List.unmodifiable(_discovered));
          }
        }
      }
    } catch (_) {
      // Host not reachable — silently skip
    }
  }

  /// Detects local subnets by inspecting NetworkInterface addresses.
  Future<List<String>> _detectLocalSubnets() async {
    final subnets = <String>{};
    try {
      final interfaces = await NetworkInterface.list(
        type: InternetAddressType.IPv4,
        includeLoopback: false,
      );
      for (final iface in interfaces) {
        for (final addr in iface.addresses) {
          final parts = addr.address.split('.');
          if (parts.length == 4 &&
              (parts[0] == '192' || parts[0] == '10' || parts[0] == '172')) {
            subnets.add('${parts[0]}.${parts[1]}.${parts[2]}');
          }
        }
      }
    } catch (e) {
      debugPrint('Error detecting local subnets: $e');
    }
    return subnets.toList();
  }

  void clearDiscovered() {
    _discovered.clear();
    if (!_devicesController.isClosed) {
      _devicesController.add([]);
    }
  }

  void dispose() {
    _scanTimer?.cancel();
    _isScanning = false;
    _devicesController.close();
  }
}
