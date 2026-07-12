const { app, BrowserWindow, Menu, Tray, nativeImage } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let tray = null;
let serverProcess = null;
const SERVER_PORT = 8765;
const SERVER_HOST = '127.0.0.1';

// ─── Server Management ────────────────────────────────────────────────

function getPythonPath() {
  // Check for venv first
  const venvPython = process.platform === 'win32'
    ? path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe')
    : path.join(__dirname, '..', '.venv', 'bin', 'python');
  try {
    const fs = require('fs');
    if (fs.existsSync(venvPython)) return venvPython;
  } catch (e) {}
  return process.platform === 'win32' ? 'python' : 'python3';
}

function startServer(args = []) {
  const pythonPath = getPythonPath();
  const modulePath = path.join(__dirname, '..');

  const allArgs = ['-m', 'acli.desktop.launch',
    '--host', SERVER_HOST,
    '--port', String(SERVER_PORT),
    '--no-browser',
    ...args
  ];

  serverProcess = spawn(pythonPath, allArgs, {
    cwd: modulePath,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  serverProcess.stdout.on('data', (data) => {
    console.log(`[server] ${data.toString().trim()}`);
  });

  serverProcess.stderr.on('data', (data) => {
    console.error(`[server] ${data.toString().trim()}`);
  });

  serverProcess.on('exit', (code) => {
    console.log(`[server] exited with code ${code}`);
    serverProcess = null;
  });
}

function stopServer() {
  if (serverProcess) {
    try {
      process.platform === 'win32'
        ? spawn('taskkill', ['/pid', serverProcess.pid, '/f', '/t'])
        : serverProcess.kill('SIGTERM');
    } catch (e) {
      console.error('[server] failed to stop:', e);
    }
    serverProcess = null;
  }
}

function waitForServer(callback, retries = 30) {
  const options = {
    hostname: SERVER_HOST,
    port: SERVER_PORT,
    path: '/api/status',
    method: 'GET',
    timeout: 2000
  };

  const check = (remaining) => {
    if (remaining <= 0) {
      console.error('[server] failed to start within timeout');
      callback(false);
      return;
    }

    const req = http.request(options, (res) => {
      if (res.statusCode === 200) {
        callback(true);
      } else {
        setTimeout(() => check(remaining - 1), 1000);
      }
    });

    req.on('error', () => {
      setTimeout(() => check(remaining - 1), 1000);
    });

    req.on('timeout', () => {
      req.destroy();
      setTimeout(() => check(remaining - 1), 1000);
    });

    req.end();
  };

  check(retries);
}

// ─── Window Management ────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'DevOrbit',
    backgroundColor: '#0d1117',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'renderer', 'assets', 'icon.png'),
  });

  // Load the desktop app
  mainWindow.loadURL(`http://${SERVER_HOST}:${SERVER_PORT}`);

  // Handle external links — open in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost')) {
      return { action: 'allow' };
    }
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('close', (e) => {
    if (tray && !app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
      return;
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  // Create a simple tray icon
  const icon = nativeImage.createEmpty();
  try {
    const iconPath = path.join(__dirname, 'renderer', 'assets', 'tray-icon.png');
    const fs = require('fs');
    if (fs.existsSync(iconPath)) {
      tray = new Tray(iconPath);
    } else {
      tray = new Tray(nativeImage.createFromBuffer(Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        'base64'
      )));
    }
  } catch (e) {
    return; // Tray not available
  }

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show DevOrbit', click: () => { if (mainWindow) mainWindow.show(); } },
    { type: 'separator' },
    { label: 'Quit', click: () => { app.isQuitting = true; app.quit(); } }
  ]);

  tray.setToolTip('DevOrbit');
  tray.setContextMenu(contextMenu);
  tray.on('click', () => {
    if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
    }
  });
}

// ─── App Lifecycle ────────────────────────────────────────────────────

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    // Parse command line args
    const args = process.argv.slice(2);
    const isMock = args.includes('--mock');
    const serverArgs = isMock ? ['--mock'] : [];

    // Start Python backend
    startServer(serverArgs);

    // Wait for server then create window
    waitForServer((success) => {
      if (success) {
        createWindow();
        createTray();
      else {
        // Show error window
        const { dialog } = require('electron');
        dialog.showErrorBox(
          'DevOrbit — Server Error',
          'Failed to start the DevOrbit backend server.\n\nMake sure Python and dependencies are installed:\n  pip install -r requirements.txt\n\nThen try again.'
        );
        app.quit();
      }
    });
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      if (!tray) {
        app.quit();
      }
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });

  app.on('before-quit', () => {
    app.isQuitting = true;
    stopServer();
  });

  process.on('exit', () => stopServer());
  process.on('SIGINT', () => { stopServer(); process.exit(0); });
  process.on('SIGTERM', () => { stopServer(); process.exit(0); });
}
