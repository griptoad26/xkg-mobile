import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/llm_app.dart';

class WebViewScreen extends StatelessWidget {
  final LLMApp app;

  const WebViewScreen({
    super.key,
    required this.app,
  });

  Future<void> _launchUrl(BuildContext context) async {
    final uri = Uri.parse(app.url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not launch ${app.url}')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Launch immediately
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _launchUrl(context);
    });

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: app.color.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                app.icon,
                color: app.color,
                size: 18,
              ),
            ),
            const SizedBox(width: 8),
            Text(app.name),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _launchUrl(context),
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: app.color),
            const SizedBox(height: 16),
            Text(
              'Opening ${app.name}...',
              style: TextStyle(color: app.color),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _launchUrl(context),
              icon: const Icon(Icons.open_in_new),
              label: const Text('Click to Open'),
              style: ElevatedButton.styleFrom(
                backgroundColor: app.color,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
