import 'package:http/http.dart' as http;
import 'dart:convert';

class XKGService {
  String? endpoint;
  
  XKGService({this.endpoint});
  
  void setEndpoint(String ep) {
    endpoint = ep;
  }
  
  bool get isConfigured => endpoint != null && endpoint!.isNotEmpty;
  
  /// Test connection to XKG
  Future<bool> testConnection() async {
    if (!isConfigured) return false;
    
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/health'),
      ).timeout(const Duration(seconds: 5));
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Search the knowledge base
  Future<List<SearchResult>> search(String query) async {
    if (!isConfigured) return [];
    
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/search?q=${Uri.encodeComponent(query)}'),
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Handle unified search response
        final results = <SearchResult>[];
        
        if (data['tweets'] != null) {
          for (var item in data['tweets']) {
            results.add(SearchResult(
              title: item['text']?.toString().substring(0, 50) ?? 'Tweet',
              content: item['text'] ?? '',
              type: 'tweet',
              url: 'https://x.com/user/status/${item['id']}',
            ));
          }
        }
        
        if (data['conversations'] != null) {
          for (var item in data['conversations']) {
            results.add(SearchResult(
              title: item['title'] ?? 'Grok Conversation',
              content: item['content'] ?? '',
              type: 'grok',
              url: item['url'] ?? '',
            ));
          }
        }
        
        return results;
      }
    } catch (e) {
      print('Search error: $e');
    }
    
    return [];
  }
  
  /// Get list of imported tabs
  Future<List<TabItem>> getTabs() async {
    if (!isConfigured) return [];
    
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/tabs'),
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final tabs = data['tabs'] as List? ?? [];
        
        return tabs.map((t) => TabItem(
          title: t['title'] ?? 'Untitled',
          url: t['url'] ?? '',
          timestamp: t['timestamp'] ?? 0,
        )).toList();
      }
    } catch (e) {
      print('Get tabs error: $e');
    }
    
    return [];
  }
  
  /// Import a tab to XKG
  Future<bool> importTab({
    required String title,
    required String url,
    required String content,
  }) async {
    if (!isConfigured) return false;
    
    try {
      final response = await http.post(
        Uri.parse('$endpoint/api/tab-import'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'title': title,
          'url': url,
          'content': content,
          'timestamp': DateTime.now().millisecondsSinceEpoch,
        }),
      ).timeout(const Duration(seconds: 10));
      
      return response.statusCode == 200;
    } catch (e) {
      print('Import error: $e');
      return false;
    }
  }
  
  /// Get statistics
  Future<XKGStats?> getStats() async {
    if (!isConfigured) return null;
    
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/stats'),
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return XKGStats(
          tweets: data['tweets'] ?? 0,
          likes: data['likes'] ?? 0,
          bookmarks: data['bookmarks'] ?? 0,
          conversations: data['conversations'] ?? 0,
        );
      }
    } catch (e) {
      print('Stats error: $e');
    }
    
    return null;
  }
}

class SearchResult {
  final String title;
  final String content;
  final String type;
  final String url;
  
  SearchResult({
    required this.title,
    required this.content,
    required this.type,
    required this.url,
  });
}

class TabItem {
  final String title;
  final String url;
  final int timestamp;
  
  TabItem({
    required this.title,
    required this.url,
    required this.timestamp,
  });
}

class XKGStats {
  final int tweets;
  final int likes;
  final int bookmarks;
  final int conversations;
  
  XKGStats({
    required this.tweets,
    required this.likes,
    required this.bookmarks,
    required this.conversations,
  });
}

class AIConversation {
  final String id;
  final String title;
  final String provider;
  final int messageCount;
  final String createdAt;
  final List<AIMessage> messages;

  AIConversation({
    required this.id,
    required this.title,
    required this.provider,
    required this.messageCount,
    required this.createdAt,
    required this.messages,
  });
}

class AIMessage {
  final String id;
  final String role;
  final String content;
  final String timestamp;

  AIMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.timestamp,
  });
}

extension XKGServiceAI on XKGService {
  /// Get AI conversations by provider
  Future<List<AIConversation>> getAIConversations(String provider) async {
    if (!isConfigured) return [];
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/data/conversations?provider=$provider'),
      ).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List<AIConversation> convos = [];
        for (var item in data['data'] ?? []) {
          convos.add(AIConversation(
            id: item['id'] ?? '',
            title: item['title'] ?? 'Untitled',
            provider: item['provider'] ?? provider,
            messageCount: item['message_count'] ?? 0,
            createdAt: item['created_at'] ?? '',
            messages: (item['messages'] as List? ?? []).map((m) => AIMessage(
              id: m['id'] ?? '',
              role: m['role'] ?? 'user',
              content: m['content'] ?? '',
              timestamp: m['timestamp'] ?? '',
            )).toList(),
          ));
        }
        return convos;
      }
    } catch (e) {
      print('getAIConversations error: $e');
    }
    return [];
  }

  /// Get all AI conversations across all providers
  Future<List<AIConversation>> getAllAIConversations() async {
    if (!isConfigured) return [];
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/data/conversations?provider=all_ai'),
      ).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List<AIConversation> convos = [];
        for (var item in data['data'] ?? []) {
          convos.add(AIConversation(
            id: item['id'] ?? '',
            title: item['title'] ?? 'Untitled',
            provider: item['provider'] ?? 'unknown',
            messageCount: item['message_count'] ?? 0,
            createdAt: item['created_at'] ?? '',
            messages: (item['messages'] as List? ?? []).map((m) => AIMessage(
              id: m['id'] ?? '',
              role: m['role'] ?? 'user',
              content: m['content'] ?? '',
              timestamp: m['timestamp'] ?? '',
            )).toList(),
          ));
        }
        return convos;
      }
    } catch (e) {
      print('getAllAIConversations error: $e');
    }
    return [];
  }

  /// Get AI export sources status
  Future<Map<String, dynamic>> getAISources() async {
    if (!isConfigured) return {};
    try {
      final response = await http.get(
        Uri.parse('$endpoint/api/ai-sources'),
      ).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print('getAISources error: $e');
    }
    return {};
  }
}
