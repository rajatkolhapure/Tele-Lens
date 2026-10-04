import 'package:flutter/material.dart';
import 'ui/home_screen.dart';

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
        scaffoldBackgroundColor: const Color(0xFF0D0D1A),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00ADB5),
          secondary: Color(0xFF00ADB5),
          surface: Color(0xFF1A1A2E),
        ),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
