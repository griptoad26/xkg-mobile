#!/usr/bin/env bash
# bundle-server.sh — build and smoke-test the XKG server binary on Linux/macOS.
# This is the cross-platform subset of bundle-windows.ps1. It is used to
# verify the PyInstaller packaging works on any host before running the
# Windows-only Flutter build on a Windows runner.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="$REPO_ROOT/xkg-server"
BUILD_DIR="$REPO_ROOT/build"
DIST_DIR="$BUILD_DIR/dist"
SERVER_DIST="$DIST_DIR/xkg-server"
PORT="${XKG_PORT:-18050}"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
SMOKE_TIMEOUT="${SMOKE_TIMEOUT:-60}"
PYTHON="${PYTHON:-python3}"

cd "$SERVER_DIR"

echo "=== XKG Server Bundle (Linux/macOS) ==="
echo "Server dir:  $SERVER_DIR"
echo "Dist dir:    $DIST_DIR"
echo "Port:        $PORT"
echo "Python:      $($PYTHON --version 2>&1)"
echo

# Step 1: install deps
echo "[1/4] Installing server dependencies..."
$PYTHON -m pip install -q -r requirements.txt

# Step 2: PyInstaller
echo "[2/4] Building server binary with PyInstaller..."
mkdir -p "$DIST_DIR"
rm -rf "$SERVER_DIST"
$PYTHON -m pip install -q pyinstaller
$PYTHON -m PyInstaller --noconfirm --clean --onefile --name xkg-server \
    --distpath "$SERVER_DIST" \
    --workpath "$DIST_DIR/pyinstaller-work" \
    --specpath "$DIST_DIR/pyinstaller-spec" \
    --add-data "frontend:frontend" \
    --add-data "core:core" \
    --hidden-import flask \
    --hidden-import flask_cors \
    --hidden-import flask_compress \
    --hidden-import networkx \
    --hidden-import pandas \
    --hidden-import numpy \
    --hidden-import waitress \
    --paths "$SERVER_DIR" \
    start_waitress.py

SERVER_BIN="$SERVER_DIST/xkg-server"
if [[ ! -x "$SERVER_BIN" ]]; then
    echo "✗ PyInstaller did not produce $SERVER_BIN" >&2
    exit 1
fi
SIZE=$(du -h "$SERVER_BIN" | cut -f1)
echo "  ✓ Built: $SERVER_BIN ($SIZE)"

# Step 3: smoke test
echo "[3/4] Smoke-testing the server binary..."
LOG="$DIST_DIR/smoke-test.log"
rm -f "$LOG"
"$SERVER_BIN" > "$LOG" 2>&1 &
PID=$!

cleanup() {
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

healthy=0
for i in $(seq 1 "$SMOKE_TIMEOUT"); do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "  ✗ Server exited prematurely (see $LOG)" >&2
        cat "$LOG" >&2
        exit 1
    fi
    if curl -sf -o /dev/null -m 2 "$HEALTH_URL"; then
        healthy=1
        break
    fi
    sleep 1
done

if [[ "$healthy" -ne 1 ]]; then
    echo "  ✗ Server did not respond to $HEALTH_URL within ${SMOKE_TIMEOUT}s" >&2
    cat "$LOG" >&2
    exit 1
fi
echo "  ✓ Health check OK: $HEALTH_URL"

# Step 4: report
echo "[4/4] Done."
echo
echo "=== BUILD COMPLETE ==="
echo "Binary: $SERVER_BIN ($SIZE)"
echo "Smoke:  PASS (port $PORT, /api/health returned 200)"
echo
echo "To run:"
echo "  $SERVER_BIN"
echo
echo "Note: this script only builds the server half. The Windows-only"
echo "Flutter Desktop app is built by bundle-windows.ps1 on Windows."
