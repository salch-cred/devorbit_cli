"""Build a portable console application and optional native installer on the current OS."""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP_NAME = "DevOrbit"
SUPPORT_FILES = [
    "models.json", ".env.example", "providers.example.json", "settings.example.json",
    "README.md", "FEATURES.md", "SECURITY.md", "PRODUCTION.md",
]

def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)

def main():
    shutil.rmtree(DIST, ignore_errors=True)
    run(
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
        "--name", APP_NAME, "--collect-all", "keyring", "--collect-all", "playwright", "acli/main.py",
    )
    for name in SUPPORT_FILES:
        source = ROOT / name
        if source.exists(): shutil.copy2(source, DIST / source.name)
    (DIST / "workspace").mkdir(exist_ok=True)

    system = platform.system()
    architecture = platform.machine().lower() or "unknown"
    portable = ROOT / (APP_NAME + "-portable-" + system.lower() + "-" + architecture)
    shutil.make_archive(str(portable), "zip", DIST)

    if system == "Windows" and shutil.which("makensis"):
        run("makensis", "packaging/windows.nsi")
    elif system == "Darwin" and shutil.which("pkgbuild"):
        run("pkgbuild", "--root", "dist", "--identifier", "com.devorbit.cli", "--version", "2.1.0", "dist/DevOrbit.pkg")
    elif system == "Linux":
        shutil.make_archive(str(ROOT / (APP_NAME + "-linux-" + architecture)), "gztar", DIST)

    print("Application:", DIST / (APP_NAME + (".exe" if system == "Windows" else "")))
    print("Portable archive:", str(portable) + ".zip")
    if system == "Windows" and not shutil.which("makensis"):
        print("NSIS was not found; portable EXE/ZIP created without Setup.exe.")

if __name__ == "__main__":
    main()
