# DevOrbit Electron Desktop Wrapper

This wraps the DevOrbit web UI in a native Electron desktop window.

## Prerequisites

1. Python backend installed:
```bash
cd .. && ./install.sh    # or install.bat
```

2. Node.js installed (for Electron)

## Install & Run

```bash
npm install
npm start              # launches desktop app with real API
npm run start:mock     # launches in demo mode (no API key needed)
```

## Build Native Installers

```bash
npm run build:win      # Windows: creates NSIS installer + portable exe
npm run build:mac      # macOS: creates DMG
npm run build:linux    # Linux: creates AppImage + deb
```

Output goes to `electron/release/`.

## How It Works

```
Electron main.js
  ├── starts Python FastAPI server (acli.desktop.launch)
  ├── waits for server to be ready
  └── loads http://127.0.0.1:8765 in a native BrowserWindow
```

The Electron window loads the same web UI served by the Python backend.
All features (chat, dashboard, files, models, tools, settings) work identically.

## Features

- Native desktop window (no browser chrome)
- System tray icon (minimize to tray)
- Single instance lock (prevents multiple copies)
- Auto-starts and manages the Python backend
- Graceful shutdown (stops server on quit)
- Cross-platform: Windows, macOS, Linux
