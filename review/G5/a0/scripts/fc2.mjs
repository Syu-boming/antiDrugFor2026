// 修正第 2 輪（開場、第一幕、第二幕）：連續片段光敏檢查（跨 cue 接縫）。私人建置，不碰 app/dist。
// 用法：
//   node review/G5/a0/scripts/fc2.mjs --dist <私人建置> --out <暫存資料夾> --seq "a1_c004:27:end,hold:1,a1_c005:0:6" [--fps 30] [--size 960x540]
//   --acts a1          整段（每個 cue 從頭到尾，cue 之間停 hold 秒，預設 1 秒）
// 每段 <cue>:<起>:<訖|end>；hold:<秒> 重複上一格（教師停格）。分析：fine 32×18、16×9 每秒幾次（同 tools/capture_analyze.py 門檻），
// 以及全畫面平均亮度一格內相對變化 > 20% 的位置（主線更正裁定：切場亮度漸變）。
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] !== undefined ? args[i + 1] : d; };
const dist = resolve(opt('--dist', ''));
const out = resolve(opt('--out', ''));
const fps = Number(opt('--fps', '30'));
const [W, H] = opt('--size', '960x540').split('x').map(Number);
const holdDefault = Number(opt('--hold', '1'));
if (!existsSync(join(dist, 'index.html'))) { console.error('找不到私人建置'); process.exit(1); }
rmSync(out, { recursive: true, force: true }); mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=${fps}`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
const all = await page.evaluate(() => window.__engine.getCues());
let seq = [];
const acts = opt('--acts', '');
if (acts) {
  for (const a of acts.split(',')) {
    const ids = all.filter((c) => c.id.startsWith(`${a}_`) && c.duration > 0).map((c) => c.id);
    ids.forEach((id, i) => { seq.push([id, 0, 'end']); if (i < ids.length - 1) seq.push(['hold', holdDefault]); });
  }
} else {
  seq = opt('--seq', '').split(',').filter(Boolean).map((s) => s.split(':'));
}
let k = 0, last = null;
const list = [];
for (const s of seq) {
  if (s[0] === 'hold') {
    const n = Math.round(Number(s[1]) * fps);
    for (let i = 0; i < n && last; i++) { const f = join(out, `${String(k).padStart(6, '0')}.jpg`); copyFileSync(last, f); list.push({ k, cue: 'hold', t: 0 }); k++; }
    continue;
  }
  const c = all.find((x) => x.id === s[0]);
  if (!c) { console.log('沒有', s[0]); continue; }
  await page.evaluate((cid) => window.__engine.capture.playCue(cid), c.id);
  const t0 = Number(s[1] ?? 0), t1 = s[2] === undefined || s[2] === 'end' ? c.duration : Math.min(c.duration, Number(s[2]));
  const n0 = Math.ceil(t0 * fps - 1e-6), n1 = Math.floor(t1 * fps + 1e-6);
  for (let n = n0; n <= n1; n++) {
    await page.evaluate((t) => window.__engine.capture.seek(t), n / fps);
    const f = join(out, `${String(k).padStart(6, '0')}.jpg`);
    await page.screenshot({ path: f, type: 'jpeg', quality: 85 });
    list.push({ k, cue: c.id, t: n / fps }); last = f; k++;
  }
  // 停格：cue 結束後的畫面
  await page.evaluate((t) => window.__engine.capture.seek(t), c.duration + 0.001);
  console.log(`${c.id} ${c.duration.toFixed(2)} 秒（${t0}–${t1.toFixed(2)}）`);
}
await browser.close();
writeFileSync(join(out, 'list.json'), JSON.stringify({ fps, frames: list }));
const py = spawnSync('/opt/anaconda3/bin/python3', [join(ROOT, 'review/G5/a0/scripts/fc2.py'), out], { stdio: 'inherit' });
if (py.status !== 0) console.log('分析失敗');
