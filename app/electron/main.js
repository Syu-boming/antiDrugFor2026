// 反毒剪紙劇場 Electron 外殼（v1.3 第 6 節打包首選；v1.2 第 19.4、21 節）。
//
// - 延伸顯示：舞台視窗全螢幕放投影螢幕（只顯示乾淨的舞台），教師控制台放筆電螢幕。
// - 同步顯示或只有一個畫面：只開單一舞台視窗（簡報筆照常操作，M 鍵是教師選單）。
// - 兩個視窗用 IPC 互傳訊息（主程序只轉送，不保存演出狀態；狀態來源唯一＝舞台視窗的引擎）。
// - 允許自動播放（老師不必在投影畫面上點滑鼠才能出聲）；舞台視窗不因失焦或被遮住而降速。
// - 完全離線：擋掉所有 http／https／ws 請求；拒絕攝影機、麥克風等權限；不開新視窗、不跳網頁。
// - 演出中防止螢幕關閉或休眠。
//
// 參數：--cues=show｜g4｜demo（預設依序找 show、g4、demo）  --single 強制單一視窗  --windowed 不全螢幕
//       --stage-display=<id> 指定舞台螢幕  --query=q=B&lead=200 傳給舞台頁的網址參數  --dev 允許開發者工具
//       --dual-test 在同一個螢幕並排開兩個小視窗（只給測試用）
const { app, BrowserWindow, ipcMain, screen, session, powerSaveBlocker } = require('electron');
const path = require('path');
const fs = require('fs');
const vm = require('vm');
const { chooseLayout } = require('./layout');

const argv = process.argv.slice(1);
const flag = (n) => argv.includes(`--${n}`);
const opt = (n) => { const a = argv.find((x) => x.startsWith(`--${n}=`)); return a ? a.slice(n.length + 3) : null; };
const OPTS = {
  single: flag('single'), dualTest: flag('dual-test'), dev: flag('dev'), windowed: flag('windowed'),
  stageDisplay: opt('stage-display') != null ? Number(opt('stage-display')) : null,
  cues: opt('cues'), query: opt('query') || '',
};

app.commandLine.appendSwitch('force_high_performance_gpu');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

/** 劇場程式（app/dist）：打包後在 resources/app/dist，開發時在 app/dist */
function findDist() {
  for (const d of [path.join(__dirname, 'dist'), path.join(__dirname, '..', 'dist')]) if (fs.existsSync(path.join(d, 'stage.html'))) return d;
  return path.join(__dirname, 'dist');
}
const DIST = findDist();

function cueSets() {
  try {
    const box = {};
    vm.runInNewContext(fs.readFileSync(path.join(DIST, 'data', 'manifest.js'), 'utf8'), { window: { __pack: (id, data) => { box[id] = data; } } }, { timeout: 1000 });
    return Object.keys((box.manifest && box.manifest.cueSets) || {});
  } catch { return []; }
}
const SETS = cueSets();
const CUES = OPTS.cues || ['show', 'g4', 'demo'].find((s) => SETS.includes(s)) || SETS[0] || 'demo';

let stageWin = null;
let consoleWin = null;
let layout = null;

const alive = (w) => !!w && !w.isDestroyed();
const publicLayout = () => (layout ? { mode: layout.mode, reason: layout.reason, stageDisplay: layout.stage, consoleDisplay: layout.console, displays: layout.displays } : null);

function send(w, msg) { if (alive(w)) w.webContents.send('theater-msg', msg); }
function broadcast(msg) { send(stageWin, msg); send(consoleWin, msg); }

function webPrefs(extra) {
  return { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false, devTools: OPTS.dev, ...extra };
}

function stageQuery() {
  const q = Object.fromEntries(new URLSearchParams(OPTS.query));
  return { ...q, cues: CUES, nofs: '1' };
}

const testMode = () => layout && layout.mode === 'dual-test';

function placeStage(w, display) {
  const b = display.bounds;
  if (testMode() || OPTS.windowed) {
    if (w.isFullScreen()) w.setFullScreen(false);
    w.setBounds(testMode() ? { x: b.x + 20, y: b.y + 40, width: 800, height: 450 } : { x: b.x + 40, y: b.y + 40, width: Math.min(1280, b.width - 80), height: Math.min(720, b.height - 80) });
    return;
  }
  if (w.isFullScreen()) w.setFullScreen(false);
  w.setBounds(b);
  w.setFullScreen(true);
}

function createStage(display) {
  const w = new BrowserWindow({
    x: display.bounds.x, y: display.bounds.y, width: Math.min(1280, display.bounds.width), height: Math.min(720, display.bounds.height),
    show: false, frame: !!(testMode() || OPTS.windowed), backgroundColor: '#000000', autoHideMenuBar: true, title: '反毒剪紙劇場｜舞台',
    webPreferences: webPrefs({ autoplayPolicy: 'no-user-gesture-required', backgroundThrottling: false }),
  });
  w.removeMenu();
  w.once('ready-to-show', () => {
    placeStage(w, display);
    w.show();
    if (layout.mode === 'single') w.focus();
    else if (alive(consoleWin)) consoleWin.focus();
  });
  w.on('closed', () => { stageWin = null; app.quit(); });
  w.loadFile(path.join(DIST, 'stage.html'), { query: stageQuery() });
  return w;
}

function placeConsole(w, display) {
  const wa = display.workArea;
  if (testMode()) { w.setBounds({ x: wa.x + 840, y: wa.y + 40, width: 1000, height: 640 }); return; }
  w.setBounds(wa);
  if (!OPTS.windowed) w.maximize();
}

function createConsole(display) {
  const w = new BrowserWindow({
    x: display.workArea.x, y: display.workArea.y, width: Math.min(1366, display.workArea.width), height: Math.min(768, display.workArea.height),
    show: false, backgroundColor: '#0f1216', autoHideMenuBar: true, title: '教師控制台｜反毒剪紙劇場',
    webPreferences: webPrefs({ backgroundThrottling: false }),
  });
  w.removeMenu();
  w.once('ready-to-show', () => { placeConsole(w, display); w.show(); w.focus(); });
  w.on('closed', () => { consoleWin = null; });
  w.loadFile(path.join(DIST, 'console.html'), { query: { cues: CUES, host: 'electron' } });
  return w;
}

/** 依目前的顯示器配置開窗或搬窗；演出中拔掉投影機時改成單一視窗，接回來時恢復雙視窗 */
function applyLayout() {
  const displays = screen.getAllDisplays();
  const primary = screen.getPrimaryDisplay();
  layout = chooseLayout(displays.map((d) => ({ id: d.id, bounds: d.bounds, internal: !!d.internal })), primary.id, OPTS);
  layout.displays = displays.length;
  const byId = (id) => displays.find((d) => d.id === id) || primary;
  if (!alive(stageWin)) stageWin = createStage(byId(layout.stage));
  else placeStage(stageWin, byId(layout.stage));
  if (layout.mode === 'single') {
    if (alive(consoleWin)) consoleWin.close();
    if (alive(stageWin)) stageWin.focus();
  } else if (!alive(consoleWin)) consoleWin = createConsole(byId(layout.console));
  else placeConsole(consoleWin, byId(layout.console));
  broadcast({ t: 'host', event: 'layout', layout: publicLayout() });
}

let relayoutTimer = null;
function scheduleRelayout() {
  if (OPTS.single || OPTS.dualTest) return;
  clearTimeout(relayoutTimer);
  relayoutTimer = setTimeout(applyLayout, 800); // 等 Windows 切換顯示模式穩定
}

// 兩個視窗互傳訊息：主程序只轉送給另一個視窗
ipcMain.on('theater-msg', (e, msg) => {
  for (const w of [stageWin, consoleWin]) if (alive(w) && w.webContents !== e.sender) w.webContents.send('theater-msg', msg);
});
ipcMain.handle('theater-info', (e) => ({
  layout: publicLayout(),
  role: alive(stageWin) && e.sender === stageWin.webContents ? 'stage' : 'console',
  versions: { electron: process.versions.electron, chrome: process.versions.chrome },
  cues: CUES,
}));

app.on('web-contents-created', (_e, wc) => {
  wc.setWindowOpenHandler(() => ({ action: 'deny' }));
  wc.on('will-navigate', (ev, url) => { if (!url.startsWith('file:')) ev.preventDefault(); });
});

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => { const w = alive(consoleWin) ? consoleWin : stageWin; if (alive(w)) w.focus(); });
  app.whenReady().then(() => {
    const ses = session.defaultSession;
    ses.setPermissionRequestHandler((_wc, perm, cb) => cb(perm === 'fullscreen'));
    ses.setPermissionCheckHandler((_wc, perm) => perm === 'fullscreen');
    ses.webRequest.onBeforeRequest({ urls: ['http://*/*', 'https://*/*', 'ws://*/*', 'wss://*/*'] }, (_d, cb) => cb({ cancel: true }));
    powerSaveBlocker.start('prevent-display-sleep');
    applyLayout();
    screen.on('display-added', scheduleRelayout);
    screen.on('display-removed', scheduleRelayout);
    screen.on('display-metrics-changed', (_e, _d, changed) => {
      // 縮放比例改了：通知舞台依新的 devicePixelRatio 重設解析度
      broadcast({ t: 'host', event: 'display-metrics' });
      if (changed.includes('bounds')) scheduleRelayout();
    });
  });
  app.on('window-all-closed', () => app.quit());
}
