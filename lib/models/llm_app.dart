import 'package:flutter/material.dart';

class LLMApp {
  final String name;
  final String url;
  final Color color;
  final IconData icon;

  const LLMApp({
    required this.name,
    required this.url,
    required this.color,
    required this.icon,
  });

  static const List<LLMApp> defaultApps = [
    LLMApp(
      name: 'Grok',
      url: 'https://x.com/grok',
      color: Color(0xFF000000),
      icon: Icons.smart_toy_outlined,
    ),
    LLMApp(
      name: 'ChatGPT',
      url: 'https://chatgpt.com',
      color: Color(0xFF10A37F),
      icon: Icons.psychology_outlined,
    ),
    LLMApp(
      name: 'Claude',
      url: 'https://claude.ai',
      color: Color(0xFFD4A574),
      icon: Icons.auto_awesome_outlined,
    ),
    LLMApp(
      name: 'Gemini',
      url: 'https://gemini.google.com',
      color: Color(0xFF8AB4F8),
      icon: Icons.auto_fix_high_outlined,
    ),
    LLMApp(
      name: 'Perplexity',
      url: 'https://perplexity.ai',
      color: Color(0xFFB649FF),
      icon: Icons.search_outlined,
    ),
  ];
}
