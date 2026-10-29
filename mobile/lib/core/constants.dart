class TeleLensConstants {
  static const int defaultSignalingPort = 8990;
  static const int defaultTurboStreamPort = 8991;
  static const String mdnsServiceType = "_telelens._tcp";

  // Square Creator Preset (1088x1088 @ 30/60fps)
  static const int targetSquareWidth = 1088;
  static const int targetSquareHeight = 1088;
  static const int targetSquareFPS = 30;

  // 4K Studio Preset (3840x2160 @ 30/60fps)
  static const int target4KWidth = 3840;
  static const int target4KHeight = 2160;
  static const int target4KFPS = 30;

  // 1440p Preset (2560x1440 @ 60fps)
  static const int target1440pWidth = 2560;
  static const int target1440pHeight = 1440;
  static const int target1440pFPS = 60;

  // 1080p Preset (1920x1080 @ 30/60fps)
  static const int target1080pWidth = 1920;
  static const int target1080pHeight = 1080;
  static const int target1080pFPS = 30;
}
