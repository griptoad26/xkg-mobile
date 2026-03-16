import 'package:hive/hive.dart';

class StorageService {
  static const String _llmBox = 'llm_apps';
  static const String _settingsBox = 'settings';
  
  /// Get saved custom LLM apps
  static List<Map<String, dynamic>> getCustomApps() {
    try {
      final box = Hive.box(_llmBox);
      final apps = box.get('custom_apps', defaultValue: []);
      return List<Map<String, dynamic>>.from(apps);
    } catch (e) {
      return [];
    }
  }
  
  /// Save a custom LLM app
  static Future<void> saveCustomApp(Map<String, dynamic> app) async {
    try {
      final box = Hive.box(_llmBox);
      final apps = getCustomApps();
      apps.add(app);
      await box.put('custom_apps', apps);
    } catch (e) {
      print('Error saving custom app: $e');
    }
  }
  
  /// Delete a custom LLM app
  static Future<void> deleteCustomApp(String name) async {
    try {
      final box = Hive.box(_llmBox);
      final apps = getCustomApps();
      apps.removeWhere((app) => app['name'] == name);
      await box.put('custom_apps', apps);
    } catch (e) {
      print('Error deleting custom app: $e');
    }
  }
  
  /// Get XKG endpoint
  static String getXKGEndpoint() {
    try {
      final box = Hive.box(_settingsBox);
      return box.get('xkg_endpoint', defaultValue: '');
    } catch (e) {
      return '';
    }
  }
  
  /// Save XKG endpoint
  static Future<void> setXKGEndpoint(String endpoint) async {
    try {
      final box = Hive.box(_settingsBox);
      await box.put('xkg_endpoint', endpoint);
    } catch (e) {
      print('Error saving endpoint: $e');
    }
  }
  
  /// Get auto-sync setting
  static bool getAutoSync() {
    try {
      final box = Hive.box(_settingsBox);
      return box.get('auto_sync', defaultValue: false);
    } catch (e) {
      return false;
    }
  }
  
  /// Save auto-sync setting
  static Future<void> setAutoSync(bool value) async {
    try {
      final box = Hive.box(_settingsBox);
      await box.put('auto_sync', value);
    } catch (e) {
      print('Error saving auto-sync: $e');
    }
  }
}
