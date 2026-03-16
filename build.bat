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

REM Find the APK
for /r %%i in (build\app\outputs\flutter-apk\*.apk) do (
    echo APK Location: %%i
    echo.
    echo To install on phone:
    echo   1. Connect phone via USB
    echo   2. Enable Developer Mode + USB Debugging on phone
    echo   3. Run: flutter install
    echo.
    echo   OR transfer the APK file to your phone manually
)

echo [4/4] Done!
echo.
pause
