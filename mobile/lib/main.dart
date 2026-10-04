import 'package:flutter/material.dart';
import 'ui/scanner_view.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const TeleLensMobileApp());
}

class TeleLensMobileApp extends StatelessWidget {
  const TeleLensMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TeleLens Studio Camera',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF12121E),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00ADB5),
          secondary: Color(0xFF00ADB5),
          surface: Color(0xFF1E1E2E),
        ),
        useMaterial3: true,
      ),
      home: const ScannerView(),
    );
  }
}
