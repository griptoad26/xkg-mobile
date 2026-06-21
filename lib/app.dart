import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'utils/theme.dart';

class XKGMobileApp extends StatelessWidget {
  const XKGMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'XKG Mobile',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.dark,
      home: const HomeScreen(),
    );
  }
}
