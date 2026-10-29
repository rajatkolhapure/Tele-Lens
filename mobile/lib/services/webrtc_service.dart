import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/device_payload.dart';

typedef ControlCallback = void Function(String method, Map<String, dynamic> params);

class WebRTCService {
  RTCPeerConnection? _peerConnection;
  MediaStream? _localStream;
  RTCDataChannel? _dataChannel;
  WebSocketChannel? _wsChannel;

  ControlCallback? onRemoteControl;
  ValueChanged<bool>? onConnectionStateChanged;
  ValueChanged<MediaStream>? onStreamReady;

  bool _isConnected = false;
  bool get isConnected => _isConnected;
  MediaStream? get localStream => _localStream;

  MediaStreamTrack? get videoTrack {
    final tracks = _localStream?.getVideoTracks();
    return (tracks != null && tracks.isNotEmpty) ? tracks.first : null;
  }

  WebRTCService({
    this.onRemoteControl,
    this.onConnectionStateChanged,
    this.onStreamReady,
  });

  Future<void> connect(String wsUrl, {String deviceName = "Smartphone"}) async {
    final uri = Uri.parse(wsUrl);
    _wsChannel = WebSocketChannel.connect(uri);

    _wsChannel!.stream.listen(
      (message) => _handleSignalingMessage(message),
      onDone: () => _handleDisconnected(),
      onError: (err) => debugPrint("Signaling error: $err"),
    );

    // Send Hello Handshake to Laptop Gatekeeper
    final helloMsg = jsonEncode({
      "type": "hello",
      "payload": {
        "device_name": deviceName,
        "os": defaultTargetPlatform.name,
        "stream_profile": "4K 30fps"
      }
    });
    _wsChannel!.sink.add(helloMsg);
  }

  Future<void> _handleSignalingMessage(dynamic rawMsg) async {
    final msg = jsonDecode(rawMsg as String) as Map<String, dynamic>;
    final type = msg['type'];
    final payload = msg['payload'] ?? {};

    if (type == 'hello_ack') {
      debugPrint("Laptop approved connection! Initializing WebRTC media stream...");
      await _initializeMediaAndOffer();
    } else if (type == 'answer') {
      final sdp = payload['sdp'] as String;
      final answerDesc = RTCSessionDescription(sdp, 'answer');
      await _peerConnection?.setRemoteDescription(answerDesc);
      _isConnected = true;
      onConnectionStateChanged?.call(true);
    } else if (type == 'reject') {
      debugPrint("Laptop user rejected incoming stream request.");
      _handleDisconnected();
    }
  }

  Future<void> _initializeMediaAndOffer() async {
    final configuration = <String, dynamic>{
      'iceServers': [
        {'urls': 'stun:stun.l.google.com:19302'}
      ],
      'sdpSemantics': 'unified-plan'
    };

    _peerConnection = await createPeerConnection(configuration);

    // Create DataChannel for camera control commands
    final dcInit = RTCDataChannelInit()..ordered = true;
    _dataChannel = await _peerConnection!.createDataChannel("telelens-control", dcInit);
    _dataChannel!.onMessage = (data) {
      if (data.isBinary) return;
      try {
        final parsed = jsonDecode(data.text) as Map<String, dynamic>;
        final method = parsed['method'] as String;
        final params = parsed['params'] as Map<String, dynamic>? ?? {};
        onRemoteControl?.call(method, params);
      } catch (e) {
        debugPrint("Error parsing remote control message: $e");
      }
    };

    // Capture 4K / High-FPS video & high-fidelity audio
    final mediaConstraints = <String, dynamic>{
      'audio': true,
      'video': {
        'mandatory': {
          'minWidth': '1920',
          'minHeight': '1080',
          'minFrameRate': '30',
        },
        'facingMode': 'environment',
        'optional': [],
      }
    };

    _localStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
    onStreamReady?.call(_localStream!);

    for (var track in _localStream!.getTracks()) {
      await _peerConnection!.addTrack(track, _localStream!);
    }

    final offer = await _peerConnection!.createOffer();
    await _peerConnection!.setLocalDescription(offer);

    final offerMsg = jsonEncode({
      "type": "offer",
      "payload": {
        "type": "offer",
        "sdp": offer.sdp,
      }
    });
    _wsChannel?.sink.add(offerMsg);
  }

  Future<bool> setTorch(bool enabled) async {
    final track = videoTrack;
    if (track == null) return false;
    try {
      final hasTorch = await track.hasTorch();
      if (hasTorch) {
        await track.setTorch(enabled);
        return true;
      }
    } catch (e) {
      debugPrint("setTorch error: $e");
    }
    return false;
  }

  Future<bool> switchCamera() async {
    final track = videoTrack;
    if (track == null) return false;
    try {
      await Helper.switchCamera(track);
      return true;
    } catch (e) {
      debugPrint("switchCamera error: $e");
    }
    return false;
  }

  Future<bool> setZoom(double zoom) async {
    final track = videoTrack;
    if (track == null) return false;
    try {
      await track.applyConstraints({
        'advanced': [{'zoom': zoom}]
      });
      return true;
    } catch (e) {
      debugPrint("setZoom error: $e");
    }
    return false;
  }

  Future<bool> setQuality(int width, int height, int fps) async {
    final track = videoTrack;
    if (track == null) return false;
    try {
      await track.applyConstraints({
        'width': {'ideal': width},
        'height': {'ideal': height},
        'frameRate': {'ideal': fps},
      });
      return true;
    } catch (e) {
      debugPrint("setQuality error: $e");
    }
    return false;
  }

  void sendDisconnect() {
    if (_dataChannel != null && _dataChannel!.state == RTCDataChannelState.RTCDataChannelOpen) {
      try {
        _dataChannel!.send(RTCDataChannelMessage(
          jsonEncode({'method': 'session.disconnect', 'params': {}}),
        ));
      } catch (_) {}
    }
  }

  void sendTelemetry(TelemetryData telemetry) {
    if (_dataChannel != null && _dataChannel!.state == RTCDataChannelState.RTCDataChannelOpen) {
      _dataChannel!.send(RTCDataChannelMessage(jsonEncode(telemetry.toJson())));
    }
  }

  void _handleDisconnected() {
    _isConnected = false;
    onConnectionStateChanged?.call(false);
    dispose();
  }

  Future<void> dispose() async {
    await _localStream?.dispose();
    await _dataChannel?.close();
    await _peerConnection?.close();
    await _wsChannel?.sink.close();
    _localStream = null;
    _dataChannel = null;
    _peerConnection = null;
    _wsChannel = null;
  }
}
