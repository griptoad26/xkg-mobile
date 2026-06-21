@echo off
cd /d "%~dp0"

echo ========================================
echo   XKG Mobile Build Script
echo ========================================
echo.

echo [1/4] Getting dependencies...
flutter pub get
if errorlevel 1 goto error

echo.
echo [2/4] Building debug APK...
flutter build apk --debug
if errorlevel 1 goto error

echo.
echo ========================================
echo SUCCESS! APK built at:
echo   %CD%\build\app\outputs\flutter-apk\app-debug.apk
echo ========================================

pause
exit /b 0

:error
echo.
echo BUILD FAILED - check errors above
pause
