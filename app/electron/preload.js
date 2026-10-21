// 舞台視窗與控制台共用的 preload：只開放「兩個視窗互傳訊息」與「查詢版面」，沒有檔案、網路、攝影機或麥克風。
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('theaterHost', {
  kind: 'electron',
  send: (m) => ipcRenderer.send('theater-msg', m),
  on: (cb) => {
    const h = (_e, m) => cb(m);
    ipcRenderer.on('theater-msg', h);
    return () => ipcRenderer.removeListener('theater-msg', h);
  },
  info: () => ipcRenderer.invoke('theater-info'),
});
