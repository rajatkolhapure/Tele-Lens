class PairingConfig {
  final String app;
  final String name;
  final String host;
  final int port;
  final String wsUrl;
  final String token;

  PairingConfig({
    required this.app,
    required this.name,
    required this.host,
    required this.port,
    required this.wsUrl,
    required this.token,
  });

  factory PairingConfig.fromJson(Map<String, dynamic> json) {
    return PairingConfig(
      app: json['app'] ?? '',
      name: json['name'] ?? '',
      host: json['host'] ?? '',
      port: json['port'] ?? 8990,
      wsUrl: json['ws_url'] ?? '',
      token: json['token'] ?? '',
    );
  }
}

class TelemetryData {
  final int batteryLevel;
  final bool isCharging;
  final String thermalState;

  TelemetryData({
    required this.batteryLevel,
    required this.isCharging,
    required this.thermalState,
  });

  Map<String, dynamic> toJson() => {
    'battery': batteryLevel,
    'charging': isCharging,
    'thermal': thermalState,
  };
}
