import 'package:flutter_test/flutter_test.dart';
import 'package:telelens_mobile/core/constants.dart';

void main() {
  test('constants define correct 4K, 1440p, and 1088x1088 presets', () {
    expect(TeleLensConstants.defaultSignalingPort, equals(8990));
    expect(TeleLensConstants.defaultTurboStreamPort, equals(8991));
    expect(TeleLensConstants.targetSquareWidth, equals(1088));
    expect(TeleLensConstants.targetSquareHeight, equals(1088));
    expect(TeleLensConstants.target4KWidth, equals(3840));
    expect(TeleLensConstants.target4KHeight, equals(2160));
    expect(TeleLensConstants.target1440pWidth, equals(2560));
    expect(TeleLensConstants.target1440pHeight, equals(1440));
  });
}
