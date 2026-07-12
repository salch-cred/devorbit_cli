"""Enhanced build script for DevOrbit desktop application.

Creates:
1. A PyInstaller executable of the Python backend
2. An Electron wrapper (if Node.js is available)
3. A portable ZIP distribution
4. A native installer (NSIS on Windows, DMG on macOS, AppImage on Linux)
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
ELECTRON_DIR = ROOT / "electron"
APP_NAME = "DevOrbit"

SUPPORT_FILES = [
    "models.json", ".env.example", "providers.example.json", "settings.example.json",
    "README.md", "FEATURES.md", "SECURITY.md", "PRODUCTION.md",
    "desktop.sh", "desktop.bat",
]

DESKTOP_FILES = [
    "acli/desktop/__init__.py",
    "acli/desktop/server.py",
    "acli/desktop/launch.py",
    "acli/desktop/static/index.html",
    "acli/desktop/static/styles.css",
    "acli/desktop/static/app.js",
    "acli/desktop/static/editor.css",
]


def run(*args, cwd=None):
    print(f"  Running: {' '.join(str(a) for a in args)}")
    subprocess.run(args, cwd=cwd or ROOT, check=True)


def build_python_executable():
    """Build a standalone Python executable with PyInstaller."""
    print("\n📦 Building Python executable with PyInstaller...")
    run(
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
        "--name", APP_NAME,
        "--collect-all", "keyring",
        "--collect-all", "playwright",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "acli/main.py",
    )

    # Copy support files
    for name in SUPPORT_FILES + DESKTOP_FILES:
        src = ROOT / name
        if src.exists():
            dest = DIST / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    (DIST / "workspace").mkdir(exist_ok=True)
    print(f"  ✅ Python executable: {DIST / (APP_NAME + ('.exe' if platform.system() == 'Windows' else ''))}")


def build_electron_app():
    """Build Electron desktop wrapper if Node.js is available."""
    if not shutil.which("npm"):
        print("\n⚠️  Node.js/npm not found — skipping Electron build")
        print("   Install Node.js to build the native desktop app")
        return False

    print("\n🖥️  Building Electron desktop application...")
    electron_dist = ELECTRON_DIR / "release"

    # Install dependencies
    run("npm", "install", cwd=ELECTRON_DIR)

    # Build for current platform
    system = platform.system()
    if system == "Windows":
        run("npm", "run", "build:win", cwd=ELECTRON_DIR)
    elif system == "Darwin":
        run("npm", "run", "build:mac", cwd=ELECTRON_DIR)
    else:
        run("npm", "run", "build:linux", cwd=ELECTRON_DIR)

    print(f"  ✅ Electron app: {electron_dist}")
    return True


def build_portable_zip():
    """Create a portable ZIP distribution."""
    print("\n🗜️  Creating portable ZIP distribution...")
    system = platform.system().lower()
    architecture = platform.machine().lower() or "unknown"
    portable = ROOT / f"{APP_NAME}-portable-{system}-{architecture}"
    shutil.make_archive(str(portable), "zip", DIST)
    print(f"  ✅ Portable ZIP: {portable}.zip")


def build_native_installer():
    """Build a native installer for the current platform."""
    system = platform.system()
    print(f"\n🔧 Building native installer for {system}...")

    if system == "Windows" and shutil.which("makensis"):
        run("makensis", "packaging/windows.nsi")
        print(f"  ✅ NSIS installer: {DIST / (APP_NAME + '-Setup.exe')}")
    elif system == "Windows":
        print("  ⚠️  NSIS not found — skipping installer (portable exe created)")
    elif system == "Darwin" and shutil.which("pkgbuild"):
        run("pkgbuild", "--root", "dist", "--identifier", "com.devorbit.cli",
            "--version", "2.1.0", f"dist/{APP_NAME}.pkg")
        print(f"  ✅ macOS installer: {DIST / (APP_NAME + '.pkg')}")
    elif system == "Linux":
        arch = platform.machine().lower()
        archive = ROOT / f"{APP_NAME}-linux-{arch}"
        shutil.make_archive(str(archive), "gztar", DIST)
        print(f"  ✅ Linux package: {archive}.tar.gz")
    else:
        print(f"  ⚠️  No native installer available for {system}")


def main():
    print("=" * 60)
    print(f"  DevOrbit Desktop Application Builder v2.1.0")
    print("=" * 60)

    # Check PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("\n❌ PyInstaller not found. Installing...")
        run(sys.executable, "-m", "pip", "install", "pyinstaller")

    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir(parents=True)

    # Step 1: Python executable
    build_python_executable()

    # Step 2: Portable ZIP
    build_portable_zip()

    # Step 3: Native installer
    build_native_installer()

    # Step 4: Electron app (optional)
    electron_built = build_electron_app()

    print("\n" + "=" * 60)
    print("  Build Summary")
    print("=" * 60)
    system = platform.system()
    exe_name = APP_NAME + (".exe" if system == "Windows" else "")
    print(f"  📦 Executable:     dist/{exe_name}")
    print(f"  🗜️  Portable ZIP:  {APP_NAME}-portable-{system.lower()}-*.zip")
    if electron_built:
        print(f"  🖥️  Electron App:  electron/release/")
    print(f"\n  To run the desktop app:")
    print(f"    ./desktop.sh --mock    (demo mode, no API key)")
    print(f"    ./desktop.sh           (with NVIDIA API key)")
    if electron_built:
        print(f"\n  Or use the Electron desktop app:")
        print(f"    cd electron && npm start")
    print("=" * 60)


if __name__ == "__main__":
    main()
