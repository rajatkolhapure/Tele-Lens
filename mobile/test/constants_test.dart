import 'package:flutter_test/flutter_test.dart';
import 'package:telelens_mobile/core/constants.dart';

void main() {
  test('constants define correct 4K and 1440p studio presets', () {
    expect(TeleLensConstants.defaultSignalingPort, equals(8990));
    expect(TeleLensConstants.target4KWidth, equals(3840));
    expect(TeleLensConstants.target4KHeight, equals(2160));
    expect(TeleLensConstants.target1440pWidth, equals(2560));
    expect(TeleLensConstants.target1440pHeight, equals(1440));
  });
}
