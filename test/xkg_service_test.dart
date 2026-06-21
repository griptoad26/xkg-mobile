import 'package:flutter_test/flutter_test.dart';
import 'package:xkg_mobile/services/xkg_service.dart';

void main() {
  group('XKGService', () {
    test('isConfigured returns false when no endpoint', () {
      final service = XKGService();
      expect(service.isConfigured, false);
    });

    test('isConfigured returns true when endpoint set', () {
      final service = XKGService();
      service.setEndpoint('http://localhost:5000');
      expect(service.isConfigured, true);
    });

    test('setEndpoint updates endpoint', () {
      final service = XKGService();
      service.setEndpoint('http://test:3000');
      expect(service.endpoint, 'http://test:3000');
    });

    test('search returns empty when not configured', () async {
      final service = XKGService();
      final results = await service.search('test');
      expect(results, isEmpty);
    });

    test('getTabs returns empty when not configured', () async {
      final service = XKGService();
      final tabs = await service.getTabs();
      expect(tabs, isEmpty);
    });

    test('importTab returns false when not configured', () async {
      final service = XKGService();
      final result = await service.importTab(
        title: 'Test',
        url: 'https://test.com',
        content: 'Test content',
      );
      expect(result, false);
    });

    test('getStats returns null when not configured', () async {
      final service = XKGService();
      final stats = await service.getStats();
      expect(stats, null);
    });
  });

  group('SearchResult', () {
    test('creates SearchResult correctly', () {
      final result = SearchResult(
        title: 'Test Title',
        content: 'Test Content',
        type: 'tweet',
        url: 'https://x.com/test',
      );
      expect(result.title, 'Test Title');
      expect(result.content, 'Test Content');
      expect(result.type, 'tweet');
      expect(result.url, 'https://x.com/test');
    });
  });

  group('TabItem', () {
    test('creates TabItem correctly', () {
      final tab = TabItem(
        title: 'Test Tab',
        url: 'https://test.com',
        timestamp: 1234567890,
      );
      expect(tab.title, 'Test Tab');
      expect(tab.url, 'https://test.com');
      expect(tab.timestamp, 1234567890);
    });
  });

  group('XKGStats', () {
    test('creates XKGStats correctly', () {
      final stats = XKGStats(
        tweets: 100,
        likes: 50,
        bookmarks: 25,
        conversations: 10,
      );
      expect(stats.tweets, 100);
      expect(stats.likes, 50);
      expect(stats.bookmarks, 25);
      expect(stats.conversations, 10);
    });
  });
}
