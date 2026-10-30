import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
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
  int _currentWidth = 1088;
  int _currentHeight = 1088;
  int _currentFps = 30;
  bool _isPortraitSensor = true;

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
        "stream_profile": "1088x1088 Studio Turbo"
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
    } else if (type == 'control') {
      final method = payload['method'] as String?;
      final params = payload['params'] as Map<String, dynamic>? ?? {};
      if (method != null) {
        onRemoteControl?.call(method, params);
      }
    } else if (type == 'reject') {
      debugPrint("Laptop user rejected incoming stream request.");
      _handleDisconnected();
    }
  }

  int _calculateBitrate(int width, int height, int fps) {
    if (width == 1088 && height == 1088) {
      return (fps >= 60) ? 35000000 : 25000000;
    }
    final maxDim = max(width, height);
    if (maxDim >= 3840) {
      return 35000000; // 35 Mbps for 4K UHD
    } else if (maxDim >= 2560) {
      return 24000000; // 24 Mbps for 1440p QHD
    } else if (fps >= 60) {
      return 18000000; // 18 Mbps for 1080p 60FPS
    } else if (maxDim >= 1920) {
      return 14000000; // 14 Mbps for 1080p 30FPS
    }
    return 12000000; // 12 Mbps baseline
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
            enc.minBitrate = 20000000; // 20 Mbps floor prevents WebRTC GCC downscaling
            enc.maxFramerate = _currentFps;
            enc.scaleResolutionDownBy = 1.0;
            enc.networkPriority = 1;
          }
          params.degradationPreference = RTCDegradationPreference.MAINTAIN_RESOLUTION;
          await sender.setParameters(params);
          debugPrint("Sender encodings optimized: $targetBitrate bps @ $_currentFps FPS (floor 20Mbps)");
        }
      }
    } catch (e) {
      debugPrint("optimizeSenderEncodings error: $e");
    }
  }

  String _mungeSdpForStudioQuality(String sdp) {
    final lines = sdp.split("\r\n");
    final output = <String>[];
    bool inVideoSection = false;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("m=video")) {
        inVideoSection = true;
        output.add(lines[i]);
        output.add("b=AS:50000");
        output.add("b=TIAS:50000000");
        continue;
      } else if (lines[i].startsWith("m=audio") || lines[i].startsWith("m=application")) {
        inVideoSection = false;
      }

      if (inVideoSection && lines[i].startsWith("a=fmtp:")) {
        String fmtpLine = lines[i];
        if (fmtpLine.contains("profile-level-id=")) {
          fmtpLine = fmtpLine.replaceAll(RegExp(r'profile-level-id=[0-9a-fA-F]+'), 'profile-level-id=42e033');
          if (!fmtpLine.contains("level-asymmetry-allowed")) {
            fmtpLine += ";level-asymmetry-allowed=1";
          }
          if (!fmtpLine.contains("packetization-mode")) {
            fmtpLine += ";packetization-mode=1";
          }
        }
        output.add("$fmtpLine;x-google-min-bitrate=25000;x-google-start-bitrate=35000;x-google-max-bitrate=50000");
      } else {
        output.add(lines[i]);
      }
    }
    return output.join("\r\n");
  }

  Map<String, dynamic> _buildMediaConstraints(int width, int height, int fps, String facingMode) {
    if (width == height) {
      // 1:1 Square Creator resolution (e.g. 1088x1088)
      return <String, dynamic>{
        'audio': true,
        'video': {
          'mandatory': {
            'minWidth': '$width',
            'maxWidth': '$width',
            'minHeight': '$height',
            'maxHeight': '$height',
            'minFrameRate': '$fps',
            'maxFrameRate': '$fps',
          },
          'facingMode': facingMode,
          'optional': [],
        }
      };
    }

    // Android camera sensors are physically mounted in landscape (sensorWidth >= sensorHeight).
    // WebRTC Camera2 enumerator matches sizes against sensor landscape orientation.
    final sensorWidth = max(width, height);
    final sensorHeight = min(width, height);

    return <String, dynamic>{
      'audio': true,
      'video': {
        'mandatory': {
          'minWidth': '$sensorWidth',
          'maxWidth': '$sensorWidth',
          'minHeight': '$sensorHeight',
          'maxHeight': '$sensorHeight',
          'minFrameRate': '$fps',
          'maxFrameRate': '$fps',
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
        final method = parsed['method'] as String?;
        final params = parsed['params'] as Map<String, dynamic>? ?? {};
        if (method != null) {
          onRemoteControl?.call(method, params);
        }
      } catch (e) {
        debugPrint("Error parsing remote control message: $e");
      }
    };

    // Attempt preferred studio resolution with fallback
    try {
      final constraints = _buildMediaConstraints(_currentWidth, _currentHeight, _currentFps, _currentFacingMode);
      _localStream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      debugPrint("Strict getUserMedia constraints failed ($e), falling back to high-res mandatory bounds");
      final sensorWidth = max(_currentWidth, _currentHeight);
      final sensorHeight = min(_currentWidth, _currentHeight);

      final fallbackConstraints = <String, dynamic>{
        'audio': true,
        'video': {
          'mandatory': {
            'minWidth': '${min(1280, sensorWidth)}',
            'minHeight': '${min(720, sensorHeight)}',
            'minFrameRate': '24',
          },
          'facingMode': _currentFacingMode,
          'optional': [],
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
  /// Safely releases old Camera2 hardware first to eliminate CAMERA_IN_USE conflicts.
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

      // 1. IMPORTANT: Safely release previous camera hardware FIRST
      final oldVideoTracks = _localStream?.getVideoTracks() ?? [];
      for (final oldTrack in oldVideoTracks) {
        _localStream?.removeTrack(oldTrack);
        try {
          await oldTrack.stop();
          await oldTrack.dispose();
        } catch (_) {}
      }

      // Small yield to let OS Camera HAL release hardware cleanly
      await Future.delayed(const Duration(milliseconds: 120));

      // 2. Acquire new camera stream with specified parameters
      MediaStream newStream;
      try {
        final constraints = _buildMediaConstraints(newWidth, newHeight, newFps, newFacing);
        newStream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (e) {
        debugPrint("Strict constraints failed, using high-res mandatory bounds: $e");
        final sensorWidth = max(newWidth, newHeight);
        final sensorHeight = min(newWidth, newHeight);

        final fallback = <String, dynamic>{
          'audio': false,
          'video': {
            'mandatory': {
              'minWidth': '${min(1280, sensorWidth)}',
              'minHeight': '${min(720, sensorHeight)}',
              'minFrameRate': '24',
            },
            'facingMode': newFacing,
            'optional': [],
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

      _localStream ??= await createLocalMediaStream('telelens-stream');
      _localStream!.addTrack(newTrack);

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

  Future<ByteBuffer?> captureFrame() async {
    final track = videoTrack;
    if (track == null) return null;
    try {
      return await track.captureFrame();
    } catch (e) {
      debugPrint("Frame capture error: $e");
      return null;
    }
  }

  Future<bool> setTorch(bool enabled) async {
    final track = videoTrack;
    if (track == null) return false;
    try {
      await track.setTorch(enabled);
      return true;
    } catch (e) {
      debugPrint("setTorch error: $e");
    }
    return false;
  }

  /// Switch between front selfie camera and rear primary camera.
  Future<bool> switchCamera({String? targetLens}) async {
    final track = videoTrack;
    if (track != null) {
      // First attempt fast in-place switch
      try {
        await Helper.switchCamera(track);
        _currentFacingMode = (_currentFacingMode == 'user') ? 'environment' : 'user';
        onStreamReady?.call(_localStream!);
        return true;
      } catch (e) {
        debugPrint("Helper.switchCamera failed ($e), falling back to track reacquire");
      }
    }

    String newFacing = (_currentFacingMode == 'user') ? 'environment' : 'user';
    if (targetLens != null) {
      newFacing = (targetLens.toLowerCase().contains("front") || targetLens.toLowerCase().contains("selfie"))
          ? 'user'
          : 'environment';
    }

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
      debugPrint("setZoom constraint notice: $e");
    }
    return true;
  }

  Future<bool> setFocus(double distance, bool auto) async {
    final track = videoTrack;
    if (track == null) return false;
    try {
      await track.applyConstraints({
        'advanced': [
          {
            'focusMode': auto ? 'continuous' : 'manual',
            'focusDistance': distance,
          }
        ]
      });
      return true;
    } catch (e) {
      debugPrint("setFocus error: $e");
    }
    return false;
  }

  Future<bool> setQuality(int width, int height, int fps) async {
    return await reacquireVideoTrack(
      width: width,
      height: height,
      fps: fps,
    );
  }

  void sendZoom(double zoom) {
    sendControl('camera.onZoomChanged', {'zoom': zoom});
  }

  void sendControl(String method, Map<String, dynamic> params) {
    final data = jsonEncode({'method': method, 'params': params});

    // 1. Send over DataChannel
    if (_dataChannel != null && _dataChannel!.state == RTCDataChannelState.RTCDataChannelOpen) {
      try {
        _dataChannel!.send(RTCDataChannelMessage(data));
      } catch (_) {}
    }

    // 2. Send over WebSocket for dual-channel redundancy
    if (_wsChannel != null) {
      try {
        _wsChannel!.sink.add(jsonEncode({
          'type': 'control',
          'payload': {'method': method, 'params': params}
        }));
      } catch (_) {}
    }
  }

  void sendDisconnect() {
    sendControl('session.disconnect', {});
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
