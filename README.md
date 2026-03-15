# XKG Mobile

Unified LLM launcher + XKG knowledge base on mobile.

## Features

- 🚀 **Quick Launch** - One tap to open Grok, ChatGPT, Claude, Gemini, Perplexity
- 🔍 **XKG Search** - Search your knowledge base from mobile
- 🌙 **Dark Mode** - Beautiful dark theme
- 📱 **PWA Ready** - Can be wrapped as PWA

## Install

### Prerequisites
- Flutter SDK 3.x
- Android Studio or Xcode

### Build

```bash
# Clone and enter directory
cd xkg-mobile

# Get dependencies
flutter pub get

# Build debug APK
flutter build apk --debug

# Or build for iOS
flutter build ios
```

## Usage

1. Launch app
2. Tap any LLM to open in WebView
3. Configure XKG endpoint in Settings
4. Search your knowledge base

## Supported LLM Apps

| App | URL |
|-----|-----|
| Grok | x.com/grok |
| ChatGPT | chatgpt.com |
| Claude | claude.ai |
| Gemini | gemini.google.com |
| Perplexity | perplexity.ai |

## XKG Integration

Connect to your XKG instance:
1. Open Settings
2. Enter XKG endpoint (e.g., `http://192.168.1.100:5000`)
3. Test connection
4. Save

## Future Features

- [ ] TabMind sync
- [ ] Offline cache
- [ ] Widget support
- [ ] Share to XKG

## License

MIT
