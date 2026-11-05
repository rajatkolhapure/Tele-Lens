import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Direct hardware access service for physical camera hardware features
/// (LED flash torch, camera sensors) bypassing WebRTC software limitations.
class HardwareService {
  static const MethodChannel _channel = MethodChannel('com.telelens.mobile/hardware');

  /// Directly turns on/off the device's physical camera LED torch using CameraManager.
  static Future<bool> setTorch(bool enabled) async {
    try {
      final result = await _channel.invokeMethod<bool>('setTorch', {'enabled': enabled});
      return result ?? false;
    } on PlatformException catch (e) {
      debugPrint("HardwareService.setTorch PlatformException: ${e.message}");
      return false;
    } on MissingPluginException {
      debugPrint("HardwareService.setTorch: channel not available on this platform");
      return false;
    } catch (e) {
      debugPrint("HardwareService.setTorch error: $e");
      return false;
    }
  }

  /// Checks if hardware flash LED is available on the device.
  static Future<bool> isTorchAvailable() async {
    try {
      final result = await _channel.invokeMethod<bool>('isTorchAvailable');
      return result ?? false;
    } catch (_) {
      return false;
    }
  }
}
