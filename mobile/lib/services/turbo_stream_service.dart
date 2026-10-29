import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import '../core/constants.dart';
import 'webrtc_service.dart';

/// TurboStreamService streams frames directly over a raw TCP socket via ADB USB reverse tunnel.
///
/// Bypasses WebRTC, SDP negotiation, and Google Congestion Control to deliver
/// instantaneous 1088x1088 full-bitrate frames without warm-up time or bitrate drops.
class TurboStreamService {
  final WebRTCService webrtcService;
  final ValueChanged<bool>? onConnectionChanged;

  Socket? _socket;
  Timer? _frameTimer;
  bool _isStreaming = false;
  int _framesSent = 0;

  bool get isStreaming => _isStreaming;
  int get framesSent => _framesSent;

  TurboStreamService({
    required this.webrtcService,
    this.onConnectionChanged,
  });

  Future<bool> start({
    String host = "127.0.0.1",
    int port = TeleLensConstants.defaultTurboStreamPort,
    int fps = 30,
  }) async {
    await stop();

    try {
      debugPrint("Connecting Turbo Frame Pipe to $host:$port...");
      _socket = await Socket.connect(host, port, timeout: const Duration(seconds: 4));
      _isStreaming = true;
      _framesSent = 0;
      onConnectionChanged?.call(true);

      _socket!.done.then((_) {
        _handleDisconnect();
      }).catchError((err) {
        debugPrint("Turbo socket error: $err");
        _handleDisconnect();
      });

      final intervalMs = (1000 / fps).round();
      _frameTimer = Timer.periodic(Duration(milliseconds: intervalMs), (_) => _captureAndSendFrame());
      debugPrint("Turbo Frame Pipe started at $fps FPS");
      return true;
    } catch (e) {
      debugPrint("Failed to connect Turbo Stream Pipe: $e");
      _handleDisconnect();
      return false;
    }
  }

  Future<void> _captureAndSendFrame() async {
    if (!_isStreaming || _socket == null) return;

    try {
      final byteBuffer = await webrtcService.captureFrame();
      if (byteBuffer == null) return;

      final payload = byteBuffer.asUint8List();
      if (payload.isEmpty) return;

      final width = webrtcService.currentWidth;
      final height = webrtcService.currentHeight;
      final timestampUs = DateTime.now().microsecondsSinceEpoch;

      // Header layout (22 bytes, big endian):
      // 0..3:   Magic 'TELE' (0x54454C45)
      // 4..7:   Payload length (uint32)
      // 8..9:   Width (uint16)
      // 10..11: Height (uint16)
      // 12:     Format: 1 = JPEG (uint8)
      // 13:     Flags: 0 (uint8)
      // 14..21: Timestamp us (uint64)
      final header = ByteData(22);
      header.setUint8(0, 0x54); // 'T'
      header.setUint8(1, 0x45); // 'E'
      header.setUint8(2, 0x4C); // 'L'
      header.setUint8(3, 0x45); // 'E'
      header.setUint32(4, payload.length, Endian.big);
      header.setUint16(8, width, Endian.big);
      header.setUint16(10, height, Endian.big);
      header.setUint8(12, 1); // 1 = JPEG
      header.setUint8(13, 0); // flags
      header.setUint64(14, timestampUs, Endian.big);

      _socket!.add(header.buffer.asUint8List());
      _socket!.add(payload);
      _framesSent++;
    } catch (e) {
      debugPrint("Error sending turbo frame: $e");
    }
  }

  void _handleDisconnect() {
    _isStreaming = false;
    _frameTimer?.cancel();
    _frameTimer = null;
    _socket?.destroy();
    _socket = null;
    onConnectionChanged?.call(false);
  }

  Future<void> stop() async {
    _handleDisconnect();
  }
}
