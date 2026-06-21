@echo off
echo ========================================
echo   XKG Mobile - Full Setup & Build
echo ========================================
echo.

echo This script will:
echo   1. Clone the XKG Mobile repo
echo   2. Install dependencies
echo   3. Build the APK
echo.

echo Cloning repository...
git clone https://github.com/griptoad26/xkg-mobile.git
if %errorlevel% neq 0 (
    echo ERROR: Failed to clone repository
    pause
    exit /b 1
)

cd xkg-mobile

echo.
echo Running build...
call build.bat
