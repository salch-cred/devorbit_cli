const { contextBridge, ipcRenderer } = require('electron');

// Expose minimal API to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  // Allow renderer to check if running in Electron
  isElectron: true,
});
