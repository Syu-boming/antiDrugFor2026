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
//   --dense a2_c002,a2_c004      指定 cue 的高密度逐格（每格都存 JPEG，frames_dense/<cue>/；可做影片或逐格檢查）
//   --dense-fps 30        高密度逐格的每秒格數（預設 30）
//   --probe               量測：每個關鍵影格與每秒一格記錄操偶線螢幕位置與線寬（probe.json），
//                         並在關鍵影格隱藏角色重畫一次，量兒童站位背景的亮度（投影 v2 模擬）與線的 ΔL*
//   --probe-times "a0_c001:4.6,4.8;a2_c002:11.5"   另外在這些 cue 內秒數做量測（隱藏角色量背景、紙環位置；不進接觸表與光敏分析）
//   --video               把高密度逐格組成 H.264 預覽影片（無聲，需要 ffmpeg）
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
const dense = opt('--dense', '') ? new Set(opt('--dense', '').split(',')) : new Set();
const denseFps = Number(opt('--dense-fps', '30'));
const probe = has('--probe');
const probeTimes = new Map((opt('--probe-times', '') || '').split(';').filter(Boolean).map((x) => { const [id, ts] = x.split(':'); return [id, ts.split(',').map(Number).filter((v) => Number.isFinite(v))]; }));
const video = has('--video');

// --dist <資料夾>：用另一份建置（例如私人建置）代替 app/dist（預設 app/dist）
const dist = opt('--dist', '') ? join(resolve(process.cwd(), opt('--dist', '')), 'index.html') : join(ROOT, 'app/dist/index.html');
if (!existsSync(dist)) { console.error(`[capture] 找不到 ${dist}，請先在 app/ 執行 npm run build`); process.exit(1); }

for (const d of ['keyframes', 'frames', 'frames/analysis', 'frames_dense', 'probe_bg', 'probe_frames']) {
  rmSync(join(out, d), { recursive: true, force: true });
  mkdirSync(join(out, d), { recursive: true });
}

const url = `${pathToFileURL(dist).href}?capture=1&cues=${encodeURIComponent(cues)}&q=${quality}&step=${Math.max(afps, dense.size ? denseFps : 0)}`;
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
const probes = [];
let denseCount = 0;
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
  // 額外量測時間（只量測，不存進接觸表、不進光敏分析）
  if (probe) for (const t of probeTimes.get(c.id) ?? []) { const k = r3(Math.min(D, t)); const e = times.get(k); if (e) e.probeBg = true; else times.set(k, { t: k, key: null, save: false, probeBg: true, probeOnly: true }); }
  // 高密度逐格：每格都存（另一個資料夾，不進接觸表）
  const denseTimes = new Set();
  if (dense.has(c.id)) {
    mkdirSync(join(out, 'frames_dense', c.id), { recursive: true });
    for (let k = 0; k <= Math.floor(D * denseFps + 1e-6); k++) { const k3 = r3(k / denseFps); denseTimes.add(k3); if (!times.has(k3)) times.set(k3, { t: k3, key: null, save: false, denseOnly: true }); }
  }
  for (const e of [...times.values()].sort((a, b) => a.t - b.t)) {
    // 「後」一律取到 cue 結束之後一點點，確保已進入停住（等待）狀態
    const seekT = e.key && e.key.includes('after') ? D + 0.001 : e.t;
    const r = await page.evaluate((t) => window.__engine.capture.seek(t), seekT);
    const tag = `${c.id}_${e.t.toFixed(2).padStart(6, '0')}`;
    if (denseTimes.has(e.t)) {
      const df = `frames_dense/${c.id}/${String(Math.round(e.t * denseFps)).padStart(5, '0')}.jpg`;
      await page.screenshot({ path: join(out, df), type: 'jpeg', quality: 88 });
      denseCount++;
      if (e.denseOnly) continue;
    }
    // 量測：關鍵影格＋每秒一格記錄操偶線位置；關鍵影格另外隱藏角色量背景
    if (probe && (e.key || e.probeBg || Math.abs(e.t - Math.round(e.t)) < 1e-6)) {
      const pr = await page.evaluate(() => window.__engine.debug.probe());
      // dim＝換景漸暗（world.dim）、quiz＝題卡不透明度（DOM 題卡蓋住舞台）：capture_probe 量兒童身後亮度與線的 ΔL* 時排除 dim > 0.05、quiz > 0.5 的格子
      const wNow = await page.evaluate(() => { const w = window.__engine.getState().world; return { dim: w?.dim ?? 0, quiz: w?.quizVisible ?? 0 }; });
      const rec = { cueId: c.id, t: e.t, key: e.key ?? (e.probeBg ? 'probe' : null), dim: wNow.dim, quiz: wNow.quiz, ...pr };
      if (e.key || e.probeBg) {
        const label = e.key ? e.key.replace(/\+/g, '-') : 'probe';
        let shot = `keyframes/${tag}_${label}.png`;
        if (!e.key) { shot = `probe_frames/${tag}_${label}.png`; await page.screenshot({ path: join(out, shot), type: 'png' }); }
        rec.frame = shot;
        await page.evaluate(() => window.__engine.debug.hideActors(true));
        rec.bgFrame = `probe_bg/${tag}_${label}.png`;
        await page.screenshot({ path: join(out, rec.bgFrame), type: 'png' });
        await page.evaluate(() => window.__engine.debug.hideActors(false));
        await page.evaluate((t) => window.__engine.capture.seek(t), seekT);
      }
      probes.push(rec);
      if (e.probeOnly) continue;
    }
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
if (probe) writeFileSync(join(out, 'probe.json'), JSON.stringify({ note: '座標為繪圖緩衝像素（與截圖相同）；bgFrame＝同一格隱藏角色後的背景', probes }, null, 1));
if (dense.size) console.log(`[capture] 高密度逐格 ${denseCount} 格（${denseFps} 格／秒）→ frames_dense/`);
if (video && dense.size) {
  for (const id of dense) {
    const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(denseFps), '-i', join(out, 'frames_dense', id, '%05d.jpg'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', join(out, `preview_${id}.mp4`)], { stdio: 'inherit' });
    console.log(`[capture] 預覽影片 preview_${id}.mp4 ${r.status === 0 ? '完成' : '失敗'}`);
  }
}
console.log(`[capture] 擷取 ${n} 格，${((Date.now() - t0) / 1000).toFixed(0)} 秒；外部網路請求 ${requests.length} 個；主控台錯誤／警告 ${consoleErrors.length} 則`);
for (const e of consoleErrors.slice(0, 10)) console.log(`  ${e}`);

// 交給 Python（Pillow）組接觸表與光敏分析
const py = spawnSync(PYTHON, [join(ROOT, 'tools/capture_analyze.py'), out], { stdio: 'inherit' });
if (probe && py.status === 0) {
  const pp = spawnSync(PYTHON, [join(ROOT, 'tools/capture_probe.py'), out], { stdio: 'inherit' });
  if (pp.status !== 0) console.error('[capture] 量測分析失敗');
}
if (py.status !== 0) { console.error('[capture] 分析失敗'); process.exit(py.status ?? 1); }
if (!has('--keep-analysis')) rmSync(join(out, 'frames/analysis'), { recursive: true, force: true });
if (!probe) { rmSync(join(out, 'probe_bg'), { recursive: true, force: true }); rmSync(join(out, 'probe_frames'), { recursive: true, force: true }); }
if (!dense.size) rmSync(join(out, 'frames_dense'), { recursive: true, force: true });
console.log(`[capture] 完成 → ${out}`);
