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
        scaffoldBackgroundColor: const Color(0xFF09090B),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFE4E4E7),
          secondary: Color(0xFFA1A1AA),
          surface: Color(0xFF121214),
        ),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
