@echo off
echo ========================================
echo   XKG Mobile Build Script
echo ========================================
echo.

REM Check if Flutter is available
where flutter >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Flutter not found in PATH
    echo.
    echo Please ensure Flutter is installed and in your PATH
    echo Or edit this script to use: C:\flutter\bin\flutter.exe
    echo.
    pause
    exit /b 1
)

echo [1/4] Getting dependencies...
flutter pub get
if %errorlevel% neq 0 (
    echo ERROR: Failed to get dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Building debug APK...
flutter build apk --debug
if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [3/4] APK built successfully!
echo.
echo ========================================
echo APK LOCATION:
echo   %CD%\build\app\outputs\flutter-apk\app-debug.apk
echo ========================================
echo.
echo To install:
echo   1. Connect phone via USB with Developer Mode + USB Debugging enabled
echo   2. Run: flutter install
echo.
echo   OR transfer this file to your phone manually:
echo   %CD%\build\app\outputs\flutter-apk\app-debug.apk
echo.

echo [4/4] Done!
echo.
pause
