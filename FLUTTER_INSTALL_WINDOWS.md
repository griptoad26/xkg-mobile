# Flutter Windows Installation Guide

This guide walks you through installing Flutter on Windows to build XKG Mobile.

---

## Prerequisites

### 1. Check Your System
- **OS:** Windows 10 or later (64-bit)
- **Disk Space:** 2.8 GB (plus extra for tools)
- **RAM:** 8 GB recommended
- **Screen:** 1280x720 minimum

### 2. Install Git (if not already)
- Download: https://git-scm.com/download/win
- Run installer
- Use default options

---

## Option 1: Manual Install (Recommended)

### Step 1: Download Flutter SDK

**Option A: Direct Download (Faster)**
1. Go to: https://docs.flutter.dev/get-started/install/windows
2. Click **Download Flutter SDK** (flutter_windows_3.x-stable.zip)
3. Or use direct link:
   ```
   https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.24.5-stable.zip
   ```
4. Extract to: `C:\flutter`
5. **Important:** Do NOT install in Program Files (permissions issues)

**Option B: Git Clone**
```cmd
cd C:\
git clone https://github.com/flutter/flutter.git -b stable
```

### Step 2: Add Flutter to PATH

1. Press **Windows key** + **S**
2. Type: `environment`
3. Click: **Edit the system environment variables**
4. Click: **Environment Variables**
5. Under **User variables**, find **Path**
6. Click **Edit** → **New**
7. Add: `C:\flutter\bin`
8. Click **OK** all the way out

### Step 3: Verify Installation

Open **Command Prompt** (cmd.exe):
```cmd
flutter --version
```

You should see something like:
```
Flutter 3.24.5 • Dart 3.5.4 • etc.
```

### Step 4: Run Flutter Doctor

```cmd
flutter doctor
```

This will show any issues. Common fixes:

**"Flutter SDK not found"** — Run:
```cmd
flutter precache
```

**"Android toolchain not found"** — Continue to Step 5

---

## Option 2: Install Android Studio (Includes SDK)

### Step 1: Download Android Studio

1. Go to: https://developer.android.com/studio
2. Download **android-studio-2024.1.1.12-windows.exe**
3. Run installer
4. Use default options

### Step 2: Configure Android Studio

1. Open Android Studio
2. Click **More Actions** → **SDK Manager**
3. In **SDK Platforms**, check:
   - Android API 34 (latest)
   - Android API 21 (minimum)
4. In **SDK Tools**, check:
   - Android SDK Build-Tools
   - Android SDK Command-line Tools
5. Click **Apply** → **OK**

### Step 3: Accept Licenses

```cmd
flutter doctor --android-licenses
```

Press **y** to accept each license.

### Step 4: Set ANDROID_HOME

1. Go back to Environment Variables (see Step 2 above)
2. Under **User variables**, click **New**
3. Variable name: `ANDROID_HOME`
4. Variable value: `C:\Users\YOUR_USERNAME\AppData\Local\Android\Sdk`
5. Click **OK**

Also add to Path:
- `C:\Users\YOUR_USERNAME\AppData\Local\Android\Sdk\platform-tools`
- `C:\Users\YOUR_USERNAME\AppData\Local\Android\Sdk\tools`

---

## Quick Fix: Standalone SDK (No Android Studio)

If you don't want Android Studio:

### Step 1: Download Command-Line Tools

1. Go to: https://developer.android.com/studio#command-tools
2. Download **commandlinetools-win-11076708_latest.zip**
3. Create folder: `C:\Android\cmdline-tools`
4. Extract the zip inside so you have: `C:\Android\cmdline-tools\latest\bin\`

### Step 2: Install SDK Packages

```cmd
C:\Android\cmdline-tools\latest\bin\sdkmanager.bat "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

### Step 3: Set Environment Variables

Add to Path:
- `C:\Android\cmdline-tools\latest\bin`
- `C:\Android\platform-tools`
- `C:\Android\build-tools\34.0.0`

Set variable `ANDROID_HOME` = `C:\Android`

---

## Building XKG Mobile

### Step 1: Get the Code

```cmd
cd C:\Users\YOUR_USERNAME\projects
git clone https://github.com/griptoad26/xkg-mobile.git
cd xkg-mobile
```

### Step 2: Get Dependencies

```cmd
flutter pub get
```

### Step 3: Build Debug APK

```cmd
flutter build apk --debug
```

**Success!** APK will be at:
```
C:\Users\YOUR_USERNAME\projects\xkg-mobile\build\app\outputs\flutter-apk\app-debug.apk
```

### Step 4: Install on Phone

1. Enable Developer Mode on your Android phone:
   - Settings → About Phone → Tap **Build Number** 7 times
2. Enable USB Debugging:
   - Settings → Developer Options → USB Debugging
3. Connect phone via USB
4. Run:
   ```cmd
   flutter install
   ```

Or transfer the APK file to your phone and install it.

---

## Troubleshooting

### "Flutter SDK not found in PATH"
- Make sure you added `C:\flutter\bin` to PATH
- Restart Command Prompt after editing PATH

### "Java not found"
- Download JDK 17: https://adoptium.net/
- Install and set JAVA_HOME

### "cmdline-tools not found"
- You need Android SDK command-line tools installed
- See "Quick Fix" section above

### Build fails with memory errors
- Close other programs
- Run: `flutter clean` then try again

### "Gradle failed to download"
- May need VPN or different network
- Or set up Gradle proxy

---

## Summary: Minimum Commands

```cmd
# 1. Download & extract Flutter to C:\flutter

# 2. Add to PATH

# 3. Verify
flutter --version

# 4. Install Android SDK (Android Studio or command-line tools)

# 5. Accept licenses
flutter doctor --android-licenses

# 6. Build!
cd xkg-mobile
flutter pub get
flutter build apk --debug
```

---

## Need Help?

- Flutter docs: https://docs.flutter.dev/
- Stack Overflow: Search "Flutter install Windows"
- XKG Mobile GitHub: https://github.com/griptoad26/xkg-mobile
