import 'package:flutter/material.dart';
import '../services/xkg_service.dart';

class SearchResultsScreen extends StatelessWidget {
  final List<SearchResult> results;
  final String query;

  const SearchResultsScreen({
    super.key,
    required this.results,
    required this.query,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Results for "$query"'),
      ),
      body: results.isEmpty
          ? const Center(
              child: Text('No results found'),
            )
          : ListView.builder(
              itemCount: results.length,
              itemBuilder: (context, index) {
                final result = results[index];
                return ListTile(
                  leading: Icon(
                    result.type == 'grok' ? Icons.psychology : Icons.chat_bubble,
                    color: result.type == 'grok'
                        ? const Color(0xFF6366F1)
                        : Colors.blue,
                  ),
                  title: Text(
                    result.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(
                    result.type.toUpperCase(),
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                  ),
                  trailing: const Icon(Icons.open_in_new),
                  onTap: () {
                    // Could open in webview or external browser
                  },
                );
              },
            ),
    );
  }
}
