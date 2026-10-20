// 驗收擷取腳本：以 ?capture=1 虛擬時鐘逐 cue 擷取畫面，產生驗收包需要的關鍵影格、接觸表與光敏數據。
// 製作代理不挑畫面：每個 cue 一律擷取「前、中、後」三格關鍵影格＋每秒 2 格，另以每秒 10 格做亮度／紅色分析。
//
// 用法：node tools/capture.mjs --cues demo --out review/_capture_test
// 選項：
//   --cues <名稱>         cue 檔（app/cues/<名稱>.json，需先 npm run build）
//   --out <資料夾>        輸出位置（相對目前目錄）
//   --fps 2               每秒存幾格（接觸表用）
//   --analysis-fps 10     光敏分析每秒幾格（建議 ≥10；要更嚴謹可用 30）
//   --width 1920 --height 1080   擷取解析度
//   --q A|B               畫質等級
//   --only a2_c002,a2_c004       只擷取指定 cue
//   --keep-analysis       保留分析用的中間影格（預設分析完刪除，節省空間）
// 輸出：keyframes/（PNG）、frames/（每秒 2 格 JPEG）、contact_keyframes.png、contact_timeline_NN.png、
//       luma_series.csv、flash_report.json、luma_plot.png、capture.json
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const PYTHON = process.env.PYTHON ?? '/opt/anaconda3/bin/python3';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const cues = opt('--cues', 'demo');
const out = resolve(process.cwd(), opt('--out', `review/_capture_${cues}`));
const fps = Number(opt('--fps', '2'));
const afps = Number(opt('--analysis-fps', '10'));
const width = Number(opt('--width', '1920'));
const height = Number(opt('--height', '1080'));
const quality = opt('--q', 'A');
const only = opt('--only', '') ? new Set(opt('--only', '').split(',')) : null;

const dist = join(ROOT, 'app/dist/index.html');
if (!existsSync(dist)) { console.error('[capture] 找不到 app/dist/index.html，請先在 app/ 執行 npm run build'); process.exit(1); }

for (const d of ['keyframes', 'frames', 'frames/analysis']) {
  rmSync(join(out, d), { recursive: true, force: true });
  mkdirSync(join(out, d), { recursive: true });
}

const url = `${pathToFileURL(dist).href}?capture=1&cues=${encodeURIComponent(cues)}&q=${quality}&step=${afps}`;
const t0 = Date.now();
const browser = await chromium.launch({
  channel: 'chrome', headless: true,
  args: ['--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1', '--hide-scrollbars'],
});
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
const consoleErrors = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') consoleErrors.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', (e) => consoleErrors.push(`[pageerror] ${e.message}`));
const requests = [];
page.on('request', (r) => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:')) requests.push(r.url()); });

await page.goto(url);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 60000 });
const state0 = await page.evaluate(() => window.__engine.getState());
const list = await page.evaluate(() => window.__engine.getCues());
console.log(`[capture] ${cues}：${list.length} 個 cue，總長 ${list.reduce((n, c) => n + c.duration, 0).toFixed(1)} 秒；GPU ${state0.gpu}`);

const r3 = (x) => Math.round(x * 1000) / 1000;
const frames = [];
let globalT = 0;
let n = 0;
for (const c of list) {
  if (only && !only.has(c.id)) continue;
  await page.evaluate((id) => window.__engine.capture.playCue(id), c.id);
  const D = c.duration;
  // 取樣時間：分析格（每秒 afps）、存檔格（每秒 fps）、關鍵影格（前、中、後）
  const times = new Map();
  const add = (t, flag) => {
    const k = r3(Math.min(D, t));
    const e = times.get(k) ?? { t: k, key: null, save: false };
    if (flag === 'save') e.save = true; else if (flag) e.key = e.key ? `${e.key}+${flag}` : flag;
    times.set(k, e);
  };
  for (let k = 0; k <= Math.floor(D * afps + 1e-6); k++) add(k / afps, null);
  for (let k = 0; k <= Math.floor(D * fps + 1e-6); k++) add(k / fps, 'save');
  add(0, 'before'); add(D / 2, 'mid'); add(D, 'after');
  for (const e of [...times.values()].sort((a, b) => a.t - b.t)) {
    // 「後」一律取到 cue 結束之後一點點，確保已進入停住（等待）狀態
    const seekT = e.key && e.key.includes('after') ? D + 0.001 : e.t;
    const r = await page.evaluate((t) => window.__engine.capture.seek(t), seekT);
    const tag = `${c.id}_${e.t.toFixed(2).padStart(6, '0')}`;
    let file;
    if (e.key) {
      file = `keyframes/${tag}_${e.key.replace(/\+/g, '-')}.png`;
      await page.screenshot({ path: join(out, file), type: 'png' });
      if (e.save) { const f2 = `frames/${tag}.jpg`; await page.screenshot({ path: join(out, f2), type: 'jpeg', quality: 90 }); frames.push({ file: f2, cueId: c.id, kind: c.kind, t: e.t, globalT: r3(globalT + e.t), key: null, save: true, analysis: false, phase: r.phase }); }
    } else if (e.save) {
      file = `frames/${tag}.jpg`;
      await page.screenshot({ path: join(out, file), type: 'jpeg', quality: 90 });
    } else {
      file = `frames/analysis/${tag}.jpg`;
      await page.screenshot({ path: join(out, file), type: 'jpeg', quality: 85 });
    }
    frames.push({ file, cueId: c.id, kind: c.kind, t: e.t, globalT: r3(globalT + e.t), key: e.key, save: !e.key && e.save, analysis: true, phase: r.phase });
    n++;
  }
  globalT += D;
  process.stdout.write(`  ${c.id} ${c.kind.padEnd(7)} ${D.toFixed(1).padStart(5)} 秒 → ${times.size} 格\n`);
}
const finalState = await page.evaluate(() => window.__engine.getState());
await browser.close();

const meta = {
  tool: 'tools/capture.mjs', createdAt: new Date().toISOString(), url, cues, width, height, quality, fps, analysisFps: afps,
  gpu: state0.gpu, cueList: list, frames, consoleErrors, externalRequests: requests, finalState,
  note: '虛擬時鐘逐格擷取（固定步長），與即時播放共用同一套 cue 與動畫函式；製作代理不挑畫面。',
};
writeFileSync(join(out, 'capture.json'), JSON.stringify(meta, null, 2));
console.log(`[capture] 擷取 ${n} 格，${((Date.now() - t0) / 1000).toFixed(0)} 秒；外部網路請求 ${requests.length} 個；主控台錯誤／警告 ${consoleErrors.length} 則`);
for (const e of consoleErrors.slice(0, 10)) console.log(`  ${e}`);

// 交給 Python（Pillow）組接觸表與光敏分析
const py = spawnSync(PYTHON, [join(ROOT, 'tools/capture_analyze.py'), out], { stdio: 'inherit' });
if (py.status !== 0) { console.error('[capture] 分析失敗'); process.exit(py.status ?? 1); }
if (!has('--keep-analysis')) rmSync(join(out, 'frames/analysis'), { recursive: true, force: true });
console.log(`[capture] 完成 → ${out}`);
