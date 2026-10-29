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

  String _currentFacingMode = 'environment';
  int _currentWidth = 1920;
  int _currentHeight = 1080;
  int _currentFps = 30;

  String get currentFacingMode => _currentFacingMode;
  int get currentWidth => _currentWidth;
  int get currentHeight => _currentHeight;
  int get currentFps => _currentFps;

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
        "stream_profile": "1080p 30fps"
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
      await _optimizeSenderEncodings();
    } else if (type == 'reject') {
      debugPrint("Laptop user rejected incoming stream request.");
      _handleDisconnected();
    }
  }

  int _calculateBitrate(int width, int height, int fps) {
    if (width >= 3840 || height >= 2160) {
      return 35000000; // 35 Mbps for 4K
    } else if (width >= 2560 || height >= 1440) {
      return 24000000; // 24 Mbps for 1440p
    } else if (fps >= 60) {
      return 18000000; // 18 Mbps for 1080p60
    } else if (width >= 1920 || height >= 1080) {
      return 12000000; // 12 Mbps for 1080p30
    }
    return 6000000; // 6 Mbps for 720p
  }

  Future<void> _optimizeSenderEncodings() async {
    if (_peerConnection == null) return;
    try {
      final senders = await _peerConnection!.getSenders();
      for (final sender in senders) {
        if (sender.track?.kind == 'video') {
          final params = sender.parameters;
          final targetBitrate = _calculateBitrate(_currentWidth, _currentHeight, _currentFps);
          for (var enc in params.encodings ?? []) {
            enc.maxBitrate = targetBitrate;
            enc.minBitrate = 4000000; // 4 Mbps floor prevents 360p downscaling
            enc.maxFramerate = _currentFps;
            enc.networkPriority = 1;
          }
          params.degradationPreference = RTCDegradationPreference.MAINTAIN_RESOLUTION;
          await sender.setParameters(params);
          debugPrint("Sender encodings optimized: $targetBitrate bps @ $_currentFps FPS");
        }
      }
    } catch (e) {
      debugPrint("optimizeSenderEncodings error: $e");
    }
  }

  String _mungeSdpForStudioQuality(String sdp) {
    final lines = sdp.split("\r\n");
    final output = <String>[];
    for (int i = 0; i < lines.length; i++) {
      output.add(lines[i]);
      if (lines[i].startsWith("m=video")) {
        // Enforce 45 Mbps bandwidth ceiling directly in SDP
        output.add("b=AS:45000");
        output.add("b=TIAS:45000000");
      } else if (lines[i].startsWith("a=fmtp:")) {
        // Force Google WebRTC engine high start/min/max bitrates
        output.add("${lines[i]};x-google-min-bitrate=6000;x-google-start-bitrate=20000;x-google-max-bitrate=50000");
      }
    }
    return output.join("\r\n");
  }

  Map<String, dynamic> _buildMediaConstraints(int width, int height, int fps, String facingMode) {
    return <String, dynamic>{
      'audio': true,
      'video': {
        'mandatory': {
          'minWidth': '$width',
          'minHeight': '$height',
          'minFrameRate': '$fps',
        },
        'facingMode': facingMode,
        'optional': [],
      }
    };
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

    // Attempt preferred studio resolution with fallback
    try {
      final constraints = _buildMediaConstraints(_currentWidth, _currentHeight, _currentFps, _currentFacingMode);
      _localStream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      debugPrint("High resolution getUserMedia failed, trying fallback: $e");
      final fallbackConstraints = <String, dynamic>{
        'audio': true,
        'video': {
          'width': {'ideal': _currentWidth},
          'height': {'ideal': _currentHeight},
          'frameRate': {'ideal': _currentFps},
          'facingMode': _currentFacingMode,
        }
      };
      _localStream = await navigator.mediaDevices.getUserMedia(fallbackConstraints);
    }

    onStreamReady?.call(_localStream!);

    for (var track in _localStream!.getTracks()) {
      await _peerConnection!.addTrack(track, _localStream!);
    }

    final offer = await _peerConnection!.createOffer();
    final mungedOfferSdp = _mungeSdpForStudioQuality(offer.sdp ?? '');
    final customOffer = RTCSessionDescription(mungedOfferSdp, 'offer');
    await _peerConnection!.setLocalDescription(customOffer);

    final offerMsg = jsonEncode({
      "type": "offer",
      "payload": {
        "type": "offer",
        "sdp": customOffer.sdp,
      }
    });
    _wsChannel?.sink.add(offerMsg);
  }

  /// Dynamically re-acquires camera hardware stream with target lens, resolution, and framerate.
  /// Seamlessly swaps the track on the active WebRTC sender without dropping the session.
  Future<bool> reacquireVideoTrack({
    String? facingMode,
    int? width,
    int? height,
    int? fps,
  }) async {
    final newFacing = facingMode ?? _currentFacingMode;
    final newWidth = width ?? _currentWidth;
    final newHeight = height ?? _currentHeight;
    final newFps = fps ?? _currentFps;

    try {
      debugPrint("Reacquiring video track: ${newWidth}x$newHeight @ $newFps FPS, facing: $newFacing");

      MediaStream newStream;
      try {
        final constraints = _buildMediaConstraints(newWidth, newHeight, newFps, newFacing);
        newStream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (e) {
        debugPrint("Strict constraints failed, using ideal constraints: $e");
        final fallback = <String, dynamic>{
          'audio': false,
          'video': {
            'width': {'ideal': newWidth},
            'height': {'ideal': newHeight},
            'frameRate': {'ideal': newFps},
            'facingMode': newFacing,
          }
        };
        newStream = await navigator.mediaDevices.getUserMedia(fallback);
      }

      final newVideoTracks = newStream.getVideoTracks();
      if (newVideoTracks.isEmpty) {
        newStream.dispose();
        return false;
      }
      final newTrack = newVideoTracks.first;

      // Swap track on WebRTC RTCRtpSender
      if (_peerConnection != null) {
        final senders = await _peerConnection!.getSenders();
        for (final sender in senders) {
          if (sender.track?.kind == 'video') {
            await sender.replaceTrack(newTrack);
            break;
          }
        }
      }

      // Dispose old video track and update local stream
      final oldVideoTracks = _localStream?.getVideoTracks() ?? [];
      for (final oldTrack in oldVideoTracks) {
        _localStream?.removeTrack(oldTrack);
        await oldTrack.stop();
        await oldTrack.dispose();
      }

      _localStream?.addTrack(newTrack);

      _currentFacingMode = newFacing;
      _currentWidth = newWidth;
      _currentHeight = newHeight;
      _currentFps = newFps;

      await _optimizeSenderEncodings();
      onStreamReady?.call(_localStream!);

      debugPrint("Track successfully replaced: ${newWidth}x$newHeight @ $newFps FPS ($newFacing)");
      return true;
    } catch (e) {
      debugPrint("Failed to reacquire video track: $e");
      return false;
    }
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

  /// Switch between front selfie camera and rear primary camera.
  Future<bool> switchCamera({String? targetLens}) async {
    String newFacing;
    if (targetLens != null) {
      if (targetLens.toLowerCase().contains("front") || targetLens.toLowerCase().contains("selfie")) {
        newFacing = 'user';
      } else {
        newFacing = 'environment';
      }
    } else {
      newFacing = (_currentFacingMode == 'user') ? 'environment' : 'user';
    }

    if (newFacing == _currentFacingMode && _localStream != null) {
      return true;
    }

    // For front camera, adjust target resolution if exceeding standard front sensor limits
    int targetW = _currentWidth;
    int targetH = _currentHeight;
    if (newFacing == 'user' && targetW > 1920) {
      targetW = 1920;
      targetH = 1080;
    }

    return await reacquireVideoTrack(
      facingMode: newFacing,
      width: targetW,
      height: targetH,
      fps: _currentFps,
    );
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
      debugPrint("setZoom constraint warning (handled in video pipeline): $e");
    }
    return true;
  }

  Future<bool> setQuality(int width, int height, int fps) async {
    return await reacquireVideoTrack(
      width: width,
      height: height,
      fps: fps,
    );
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
