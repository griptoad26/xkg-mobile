import 'package:flutter/material.dart';
import '../models/llm_app.dart';
import '../widgets/llm_card.dart';
import '../widgets/search_bar.dart';
import '../services/xkg_service.dart';
import '../services/storage_service.dart';
import 'webview_screen.dart';
import 'settings_screen.dart';
import 'add_app_screen.dart';
import 'search_results_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final XKGService _xkgService = XKGService();
  List<Map<String, dynamic>> _customApps = [];

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  void _loadSettings() {
    final endpoint = StorageService.getXKGEndpoint();
    if (endpoint.isNotEmpty) {
      _xkgService.setEndpoint(endpoint);
    }
    _customApps = StorageService.getCustomApps();
  }

  List<LLMApp> get _allApps {
    final defaultApps = List<LLMApp>.from(LLMApp.defaultApps);
    
    // Add custom apps
    for (final app in _customApps) {
      defaultApps.add(LLMApp(
        name: app['name'] ?? 'Custom',
        url: app['url'] ?? '',
        color: Color(app['color'] ?? 0xFF6366F1),
        icon: Icons.launch,
      ));
    }
    
    return defaultApps;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.psychology, color: Color(0xFF6366F1)),
            SizedBox(width: 8),
            Text(
              'XKG Mobile',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () async {
              final result = await Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AddAppScreen()),
              );
              if (result == true) {
                setState(() {
                  _customApps = StorageService.getCustomApps();
                });
              }
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () async {
              await Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
              _loadSettings();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // XKG Search Bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: XKGSearchBar(
              onSearch: (query) async {
                if (!_xkgService.isConfigured) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Configure XKG endpoint in Settings first'),
                    ),
                  );
                  return;
                }
                
                final results = await _xkgService.search(query);
                if (mounted && results.isNotEmpty) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => SearchResultsScreen(
                        results: results,
                        query: query,
                      ),
                    ),
                  );
                }
              },
            ),
          ),
          
          // Quick Stats
          if (_xkgService.isConfigured)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Icon(
                    Icons.check_circle,
                    size: 16,
                    color: Colors.green[400],
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'XKG Connected',
                    style: TextStyle(
                      color: Colors.green[400],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          
          // AI Apps Section
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Row(
              children: [
                const Text(
                  'AI Chatbots',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                Text(
                  '${_allApps.length} apps',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          
          // LLM Grid
          Expanded(
            child: GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                childAspectRatio: 1.3,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: _allApps.length,
              itemBuilder: (context, index) {
                final app = _allApps[index];
                return LLMCard(
                  app: app,
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => WebViewScreen(app: app),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
