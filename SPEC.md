# XKG Mobile - Specification

## Project Overview

**Name:** XKG Mobile
**Type:** Flutter Mobile App (Android & iOS)
**Purpose:** Unified launcher for all LLM chatbots + XKG knowledge base access
**Target:** Power users who use multiple AI chatbots

---

## Build Status

| Feature | Status |
|---------|--------|
| Home screen with LLM grid | ✅ Done |
| WebView for each LLM | ✅ Done |
| Settings (XKG endpoint) | ✅ Done |
| Dark theme | ✅ Done |
| XKG search | ✅ Done |
| Custom LLM apps | ✅ Done |
| XKG API integration | ✅ Done |
| Build APK | 🔧 Needs Flutter |

---

## Quick Start (Building the App)

### Option 1: Windows

1. **Install Flutter SDK:**
   - Download from: https://docs.flutter.dev/get-started/install/windows
   - Extract to: `C:\flutter`
   - Add to PATH: `C:\flutter\bin`

2. **Install Android Studio:**
   - Download from: https://developer.android.com/studio
   - Run installer
   - Open Android Studio → SDK Manager → Install tools

3. **Clone and build:**
   ```cmd
   cd C:\path\to\xkg-mobile
   flutter pub get
   flutter build apk --debug
   ```

4. **Find APK at:**
   ```
   build\app\outputs\flutter-apk\app-debug.apk
   ```

### Option 2: macOS

1. **Install Flutter:**
   ```bash
   brew install flutter
   ```

2. **Build:**
   ```bash
   cd ~/projects/xkg-mobile
   flutter pub get
   flutter build ipa  # For iOS
   flutter build apk  # For Android
   ```

### Option 3: Linux (WSL)

1. **Install Flutter in WSL:**
   ```bash
   sudo apt update
   sudo apt install curl git unzip xz-utils zip libglu1-mesa
   git clone https://github.com/flutter/flutter.git -b stable ~/flutter
   export PATH="$PATH:$HOME/flutter/bin"
   flutter precache
   ```

2. **Install Android SDK:**
   - Download command-line tools from Android developer site
   - Set ANDROID_HOME and ANDROID_SDK_ROOT

3. **Build:**
   ```bash
   cd ~/projects/xkg-mobile
   flutter pub get
   flutter build apk --debug
   ```

---

## Core Features

### 1. LLM Launcher
Quick access to launch all major LLM chatbots:
- Grok (x.com/grok)
- ChatGPT (chatgpt.com)
- Claude (claude.ai)
- Gemini (gemini.google.com)
- Perplexity (perplexity.ai)
- Custom (user-added URLs)

### 2. XKG Integration
- Connect to local XKG instance
- Search knowledge base from mobile
- View imported conversations

### 3. Tab Sync (Future)
- Sync with TabMind extension
- Access indexed tabs on mobile

---

## Tech Stack

- **Framework:** Flutter 3.x
- **State Management:** Riverpod
- **WebView:** flutter_inappwebview
- **Local Storage:** Hive
- **HTTP:** dio

---

## App Structure

```
lib/
├── main.dart
├── app.dart
├── screens/
│   ├── home_screen.dart      # Main launcher
│   ├── settings_screen.dart   # Configuration
│   └── webview_screen.dart    # LLM WebView
├── widgets/
│   ├── llm_card.dart         # LLM app tiles
│   └── search_bar.dart       # XKG search
├── services/
│   ├── xkg_service.dart      # XKG API
│   └── storage_service.dart  # Local storage
├── models/
│   ├── llm_app.dart          # LLM app model
│   └── config.dart           # App config
└── utils/
    ├── urls.dart             # LLM URLs
    └── theme.dart            # App theme
```

---

## Screens

### 1. Home Screen
- Grid of LLM app tiles
- Search bar for XKG
- Quick settings access

### 2. WebView Screen
- Full-screen WebView
- Navigation controls
- Share to XKG button

### 3. Settings Screen
- XKG endpoint configuration
- Add custom LLM apps
- Theme toggle

---

## LLM Apps List

| App | URL | Color |
|-----|-----|-------|
| Grok | x.com/grok | #000000 |
| ChatGPT | chatgpt.com | #10A37F |
| Claude | claude.ai | #D4A574 |
| Gemini | gemini.google.com | #8AB4F8 |
| Perplexity | perplexity.ai | #B649FF |

---

## Build Instructions

### Prerequisites
- Flutter SDK 3.x
- Android Studio / Xcode

### Build Commands
```bash
# Get dependencies
flutter pub get

# Build debug APK
flutter build apk --debug

# Build release APK
flutter build apk --release
```

---

## XKG API Integration

### Connect to XKG
1. Enter XKG endpoint (e.g., `http://192.168.1.x:5000`)
2. Test connection
3. Save configuration

### Search Knowledge Base
```dart
GET /api/search?q=query
```

### Import from Mobile
```dart
POST /api/tab-import
{
  "title": "...",
  "url": "...",
  "content": "..."
}
```

---

## Monetization

- **Free:** Basic LLM launcher
- **XKG Pro:** Full search, sync, unlimited imports

---

## Future Features

- [ ] TabMind sync
- [ ] Offline XKG cache
- [ ] Widget support
- [ ] Share extension
- [ ] Push notifications for LLM responses
