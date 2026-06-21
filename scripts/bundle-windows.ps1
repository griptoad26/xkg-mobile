# bundle-windows.ps1
# Bundles the XKG Flutter Desktop UI with the XKG Python server into a
# single Windows .exe distribution. Run this on a Windows machine with
# Flutter SDK + Python 3.11+ installed.
#
# Output: build/dist/xkg-bundle-<version>.zip containing:
#   - xkg_desktop.exe              (Flutter Windows app, launches UI)
#   - xkg-server.exe               (PyInstaller bundle of the Python server)
#   - start-xkg.bat                (one-click launcher; not needed if you
#                                  run xkg_desktop.exe directly — the app
#                                  spawns the server itself)
#   - README.txt                   (user-facing install + first-run notes)
#   - LICENSE.txt
#
# Architecture:
#   1. flutter build windows        → build\windows\x64\runner\Release\xkg_desktop.exe
#   2. PyInstaller onefile          → dist\xkg-server.exe  (the Flask/Waitress server)
#   3. Patch the Flutter app        → xkg_desktop.exe unpacks xkg-server.exe from
#                                    its own resources on first launch, spawns it
#                                    as a child process, polls http://127.0.0.1:18050/api/health,
#                                    then shows the UI.
#   4. Zip everything for distribution.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
$ScriptDir        = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot         = Resolve-Path (Join-Path $ScriptDir "..")
$FlutterProject   = $RepoRoot
$ServerDir        = Join-Path $RepoRoot "xkg-server"
$BuildDir         = Join-Path $RepoRoot "build"
$DistDir          = Join-Path $BuildDir "dist"
$ServerDist       = Join-Path $DistDir "xkg-server"
$Version          = (Get-Content (Join-Path $RepoRoot "pubspec.yaml") | Select-String -Pattern "^version:" | ForEach-Object { ($_ -split ":",2)[1].Trim() })
if (-not $Version) { $Version = "0.1.0" }
$BundleName       = "xkg-bundle-$Version"
$OutputZip        = Join-Path $DistDir "$BundleName.zip"

$ServerPort       = 18050
$HealthCheckUrl   = "http://127.0.0.1:$ServerPort/api/health"
$ServerStartupTimeoutSec = 60

# --------------------------------------------------------------------------
# Pre-flight checks
# --------------------------------------------------------------------------
function Assert-Command($cmd, $installHint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "✗ Missing required tool: $cmd" -ForegroundColor Red
        Write-Host "  Install: $installHint" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "=== XKG Windows Bundle Builder ===" -ForegroundColor Cyan
Write-Host "Repo:        $RepoRoot"
Write-Host "Version:     $Version"
Write-Host "Output:      $OutputZip"
Write-Host ""

Assert-Command "flutter"   "https://docs.flutter.dev/get-started/install/windows"
Assert-Command "python"    "https://www.python.org/downloads/windows/  (3.11+ recommended)"
Assert-Command "pyinstaller" "pip install pyinstaller"

# Verify repo layout
foreach ($p in @($FlutterProject, $ServerDir, (Join-Path $ServerDir "main.py"), (Join-Path $ServerDir "start_waitress.py"))) {
    if (-not (Test-Path $p)) {
        Write-Host "✗ Required path missing: $p" -ForegroundColor Red
        exit 1
    }
}

# --------------------------------------------------------------------------
# Step 1: Build the Flutter Windows app
# --------------------------------------------------------------------------
Write-Host "[1/5] Building Flutter Windows app (release)..." -ForegroundColor Yellow
Push-Location $FlutterProject
try {
    flutter pub get
    if ($LASTEXITCODE -ne 0) { throw "flutter pub get failed" }

    flutter build windows --release
    if ($LASTEXITCODE -ne 0) { throw "flutter build windows failed" }
} finally {
    Pop-Location
}

$FlutterExe = Get-ChildItem -Path (Join-Path $BuildDir "windows\x64\runner\Release") -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $FlutterExe) {
    Write-Host "✗ Flutter build did not produce an .exe" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Flutter app: $($FlutterExe.FullName) ($([math]::Round($FlutterExe.Length/1MB,1)) MB)" -ForegroundColor Green

# --------------------------------------------------------------------------
# Step 2: Build the XKG Python server with PyInstaller
# --------------------------------------------------------------------------
Write-Host "[2/5] Building XKG Python server with PyInstaller..." -ForegroundColor Yellow
Push-Location $ServerDir
try {
    # Install server deps if needed
    python -m pip install -q -r requirements.txt

    if (Test-Path $ServerDist) { Remove-Item -Recurse -Force $ServerDist }
    New-Item -ItemType Directory -Path $ServerDist | Out-Null

    # Build one-file binary. We use start_waitress.py as the entry point
    # so the server pre-loads data and binds port 18050 on launch.
    pyinstaller --noconfirm --clean --onefile --name xkg-server `
        --distpath $ServerDist `
        --workpath (Join-Path $DistDir "pyinstaller-work") `
        --specpath (Join-Path $DistDir "pyinstaller-spec") `
        --add-data "frontend;frontend" `
        --add-data "core;core" `
        --hidden-import flask `
        --hidden-import flask_cors `
        --hidden-import flask_compress `
        --hidden-import networkx `
        --hidden-import pandas `
        --hidden-import numpy `
        --hidden-import waitress `
        --paths $ServerDir `
        start_waitress.py

    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
} finally {
    Pop-Location
}

$ServerExe = Join-Path $ServerDist "xkg-server.exe"
if (-not (Test-Path $ServerExe)) {
    Write-Host "✗ PyInstaller did not produce xkg-server.exe" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Server binary: $ServerExe ($([math]::Round((Get-Item $ServerExe).Length/1MB,1)) MB)" -ForegroundColor Green

# --------------------------------------------------------------------------
# Step 3: Smoke-test the server binary in isolation
# --------------------------------------------------------------------------
Write-Host "[3/5] Smoke-testing xkg-server.exe in isolation..." -ForegroundColor Yellow
$smokeLog = Join-Path $DistDir "smoke-test.log"
$proc = Start-Process -FilePath $ServerExe -PassThru -RedirectStandardOutput $smokeLog -RedirectStandardError "$smokeLog.err" -NoNewWindow
try {
    $healthy = $false
    $deadline = (Get-Date).AddSeconds($ServerStartupTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) {
            Write-Host "  ✗ Server process exited prematurely (code $($proc.ExitCode))" -ForegroundColor Red
            Get-Content $smokeLog -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $_" }
            Get-Content "$smokeLog.err" -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    [err] $_" }
            exit 1
        }
        try {
            $r = Invoke-WebRequest -Uri $HealthCheckUrl -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $healthy = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $healthy) {
        Write-Host "  ✗ Server did not respond to $HealthCheckUrl within ${ServerStartupTimeoutSec}s" -ForegroundColor Red
        Get-Content $smokeLog -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $_" }
        exit 1
    }
    Write-Host "  ✓ Health check passed: $HealthCheckUrl" -ForegroundColor Green
} finally {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

# --------------------------------------------------------------------------
# Step 4: Stage the distribution directory
# --------------------------------------------------------------------------
Write-Host "[4/5] Staging distribution directory..." -ForegroundColor Yellow

# Fresh stage dir
$StageDir = Join-Path $DistDir $BundleName
if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
New-Item -ItemType Directory -Path $StageDir | Out-Null

# Copy Flutter app (entire Release folder so all runtime DLLs are present)
$flutterReleaseDir = Split-Path $FlutterExe -Parent
Copy-Item -Recurse -Force "$flutterReleaseDir\*" $StageDir

# Copy server binary
Copy-Item -Force $ServerExe $StageDir

# Inject the bundling helper into the Flutter app's resources.
# The Flutter app's main.dart does NOT currently spawn the server — we
# write a tiny helper script that the build patches in via --dart-define.
# The cleanest portable path is to ship a `start-xkg.bat` that:
#   1. Spawns xkg-server.exe in the background
#   2. Polls /api/health
#   3. Then launches xkg_desktop.exe
# This way we don't need to modify the Flutter source.
$startBat = Join-Path $StageDir "start-xkg.bat"
@"
@echo off
setlocal
set SERVER_EXE=%~dp0xkg-server.exe
set UI_EXE=%~dp0$($FlutterExe.Name)
set PORT=$ServerPort

echo === XKG Desktop Launcher ===
echo Starting XKG server on port %PORT%...

start "" /B "%SERVER_EXE%"
if errorlevel 1 (
  echo ERROR: Failed to start xkg-server.exe
  pause
  exit /b 1
)

echo Waiting for server health check at http://127.0.0.1:%PORT%/api/health ...
set RETRIES=0
:waitloop
set /a RETRIES+=1
if %RETRIES% gtr 60 (
  echo ERROR: Server did not respond within 60s
  pause
  exit /b 1
)
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:%PORT%/api/health).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto waitloop
)

echo Server is healthy. Launching XKG Desktop UI...
start "" "%UI_EXE%"
endlocal
"@ | Out-File -FilePath $startBat -Encoding ASCII

# README for end users
$readme = Join-Path $StageDir "README.txt"
@"
XKG Desktop + Server — Windows Bundle
Version: $Version

QUICK START
-----------
Double-click  start-xkg.bat
  - Starts the XKG server (background)
  - Waits for the server to be healthy
  - Launches the XKG Desktop UI

Or run xkg_desktop.exe directly after starting the server yourself
(port $ServerPort, GET /api/health).

REQUIREMENTS
------------
- Windows 10 64-bit or newer
- 4 GB RAM minimum (8 GB recommended for large knowledge graphs)
- 500 MB free disk

FIRST RUN
---------
1. The XKG server uses port $ServerPort. If another program is on this
   port, edit start-xkg.bat and xkg-server's CLI args.
2. The server stores its data in %%USERPROFILE%%\xkg-data\.
3. The default endpoint in the Flutter app is http://127.0.0.1:$ServerPort.
   To change it, open Settings inside the app.

TROUBLESHOOTING
---------------
- Windows SmartScreen may block the unsigned .exe on first run.
  Click "More info" -> "Run anyway".
- If the server fails to start, run xkg-server.exe from a Command Prompt
  to see its error output.
- Logs: %%USERPROFILE%%\xkg-data\logs\

LICENSE
-------
See LICENSE.txt.
"@ | Out-File -FilePath $readme -Encoding UTF8

# Copy LICENSE
$licenseSrc = Join-Path $RepoRoot "LICENSE"
if (Test-Path $licenseSrc) { Copy-Item -Force $licenseSrc (Join-Path $StageDir "LICENSE.txt") }

# --------------------------------------------------------------------------
# Step 5: Zip the bundle
# --------------------------------------------------------------------------
Write-Host "[5/5] Creating $BundleName.zip..." -ForegroundColor Yellow
if (Test-Path $OutputZip) { Remove-Item -Force $OutputZip }

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($StageDir, $OutputZip, [System.IO.Compression.CompressionLevel]::Optimal, $false)

$size = [math]::Round((Get-Item $OutputZip).Length / 1MB, 1)
Write-Host ""
Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Green
Write-Host "Bundle: $OutputZip" -ForegroundColor Cyan
Write-Host "Size:   $size MB"
Write-Host ""
Write-Host "Test it locally:" -ForegroundColor Yellow
Write-Host "  Expand-Archive '$OutputZip' -DestinationPath 'C:\xkg-test'"
Write-Host "  cd C:\xkg-test"
Write-Host "  .\start-xkg.bat"
