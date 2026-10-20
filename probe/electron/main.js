// 探針的 Electron 外殼：開啟單檔探針、回報顯示器與版本，並優先使用高效能 GPU。
const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');

app.commandLine.appendSwitch('force_high_performance_gpu');

ipcMain.handle('probe-info', () => ({
  versions: { electron: process.versions.electron, chrome: process.versions.chrome },
  displays: screen.getAllDisplays().map((d) => ({ id: d.id, size: d.size, bounds: d.bounds, scaleFactor: d.scaleFactor, internal: d.internal })),
  gpuFeatures: app.getGPUFeatureStatus(),
}));

app.whenReady().then(() => {
  const win = new BrowserWindow({
    width: 1280, height: 800, autoHideMenuBar: true, backgroundColor: '#14111c',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, autoplayPolicy: 'no-user-gesture-required' },
  });
  win.removeMenu();
  win.loadFile(path.join(__dirname, 'probe.html'));
});
app.on('window-all-closed', () => app.quit());
