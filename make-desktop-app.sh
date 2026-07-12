#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo ""
echo "============================================"
echo "  DevOrbit Desktop Application Builder"
echo "============================================"
echo ""

# Check Python venv
if [ ! -d .venv ]; then
  echo "Missing .venv. Run ./install.sh first."
  exit 1
fi
source .venv/bin/activate

echo "[1/4] Ensuring PyInstaller is installed..."
python -m pip install pyinstaller -q 2>/dev/null || true

echo "[2/4] Building Python executable + portable ZIP..."
python packaging/build.py

echo ""
echo "[3/4] Building Electron app (if Node.js available)..."
if command -v npm &>/dev/null; then
  cd electron
  npm install
  npm run build
  cd ..
  echo "  Electron app built: electron/release/"
else
  echo "  Node.js not found — skipping Electron build"
  echo "  Install Node.js to build the native desktop app"
fi

echo ""
echo "[4/4] Build complete!"
echo "  Executable: dist/DevOrbit"
echo "  Portable:  DevOrbit-portable-*.zip"
echo ""
echo "To run: ./desktop.sh --mock"
echo ""
