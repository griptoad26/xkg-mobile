import 'package:flutter/material.dart';
import 'package:hive/hive.dart';
import '../models/llm_app.dart';
import '../widgets/llm_card.dart';
import '../widgets/search_bar.dart';
import 'webview_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

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
            icon: const Icon(Icons.settings_outlined),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
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
              onSearch: (query) {
                // TODO: Implement XKG search
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Search: $query')),
                );
              },
            ),
          ),
          
          // Quick Actions
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
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
                TextButton.icon(
                  onPressed: () {
                    // Add custom app
                  },
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Add'),
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
              itemCount: LLMApp.defaultApps.length,
              itemBuilder: (context, index) {
                final app = LLMApp.defaultApps[index];
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
