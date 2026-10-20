const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('probeHost', { info: () => ipcRenderer.invoke('probe-info') });
