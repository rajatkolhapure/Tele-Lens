import 'package:flutter_test/flutter_test.dart';
import 'package:telelens_mobile/models/device_payload.dart';

void main() {
  group('PairingConfig Tests', () {
    test('parses from valid JSON', () {
      final json = {
        'app': 'telelens',
        'name': 'Laptop-Studio',
        'host': '192.168.1.100',
        'port': 8990,
        'ws_url': 'ws://192.168.1.100:8990/ws',
        'token': 'tok_xyz',
      };

      final config = PairingConfig.fromJson(json);
      expect(config.app, equals('telelens'));
      expect(config.name, equals('Laptop-Studio'));
      expect(config.host, equals('192.168.1.100'));
      expect(config.port, equals(8990));
      expect(config.wsUrl, equals('ws://192.168.1.100:8990/ws'));
      expect(config.token, equals('tok_xyz'));
    });

    test('handles default fallbacks for missing fields', () {
      final config = PairingConfig.fromJson({});
      expect(config.app, isEmpty);
      expect(config.port, equals(8990));
      expect(config.token, isEmpty);
    });
  });

  group('TelemetryData Tests', () {
    test('serializes to JSON correctly', () {
      final telemetry = TelemetryData(
        batteryLevel: 85,
        isCharging: true,
        thermalState: 'normal',
      );

      final json = telemetry.toJson();
      expect(json['battery'], equals(85));
      expect(json['charging'], isTrue);
      expect(json['thermal'], equals('normal'));
    });
  });
}
