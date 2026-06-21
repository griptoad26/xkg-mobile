// XKG Mobile - Message Relay Service
// Pulls LLM conversations and sends to OpenClaw

import 'dart:convert';
import 'package:http/http.dart' as http;

class MessageRelayService {
  String? openclawEndpoint;
  String? apiKey;
  
  void configure({required String endpoint, String? key}) {
    openclawEndpoint = endpoint;
    apiKey = key;
  }
  
  /// Send conversation to OpenClaw via message relay
  Future<bool> sendToOpenClaw({
    required String title,
    required String platform, // grok, chatgpt, claude, etc.
    required List<Map<String, String>> messages,
  }) async {
    if (openclawEndpoint == null) {
      return false;
    }
    
    try {
      // Try OpenClaw message relay endpoint
      final response = await http.post(
        Uri.parse('$openclawEndpoint/api/relay/message'),
        headers: {
          'Content-Type': 'application/json',
          if (apiKey != null) 'Authorization': 'Bearer $apiKey',
        },
        body: jsonEncode({
          'source': 'xkg-mobile',
          'platform': platform,
          'title': title,
          'messages': messages,
          'timestamp': DateTime.now().toIso8601String(),
        }),
      );
      
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      // Fallback: try session send
      return await _sendViaSession(title, platform, messages);
    }
  }
  
  /// Alternative: send via OpenClaw agent session
  Future<bool> _sendViaSession(
    String title,
    String platform,
    List<Map<String, String>> messages,
  ) async {
    if (openclawEndpoint == null) return false;
    
    try {
      // Format messages as text
      final content = _formatMessages(platform, messages);
      
      // Send to main agent session
      final response = await http.post(
        Uri.parse('$openclawEndpoint/api/sessions/main/send'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': '[XKG Mobile Import]\n\n$content',
          'source': 'message-relay',
        }),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  String _formatMessages(String platform, List<Map<String, String>> messages) {
    final buffer = StringBuffer();
    buffer.writeln('📱 Imported from: $platform');
    buffer.writeln('🕐 Time: ${DateTime.now().toIso8601String()}');
    buffer.writeln('');
    
    for (final msg in messages) {
      final role = msg['role'] ?? 'unknown';
      final content = msg['content'] ?? '';
      final prefix = role == 'user' ? '👤 User' : '🤖 Assistant';
      buffer.writeln('$prefix:');
      buffer.writeln(content);
      buffer.writeln('');
    }
    
    return buffer.toString();
  }
  
  /// Test connection to OpenClaw
  Future<bool> testConnection() async {
    if (openclawEndpoint == null) return false;
    
    try {
      final response = await http.get(
        Uri.parse('$openclawEndpoint/api/health'),
      ).timeout(const Duration(seconds: 5));
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Get list of available platforms for import
  static List<Map<String, String>> get platforms => [
    {'id': 'grok', 'name': 'Grok', 'icon': '🤖', 'url': 'https://x.com/i/grok'},
    {'id': 'chatgpt', 'name': 'ChatGPT', 'icon': '💬', 'url': 'https://chat.openai.com'},
    {'id': 'claude', 'name': 'Claude', 'icon': '🧠', 'url': 'https://claude.ai'},
    {'id': 'gemini', 'name': 'Gemini', 'icon': '✨', 'url': 'https://gemini.google.com'},
    {'id': 'perplexity', 'name': 'Perplexity', 'icon': '🔍', 'url': 'https://perplexity.ai'},
  ];
}