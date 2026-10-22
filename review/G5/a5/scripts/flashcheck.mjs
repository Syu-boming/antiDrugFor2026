// 第五幕修正：快速光敏檢查與定格（私人建置 review/G5/a5/dist，不碰 app/dist）。
// 用法：
//   node review/G5/a5/scripts/flashcheck.mjs --cues a5_c001,a5_c007 [--fps 30] [--size 960x540] [--out <dir>]
//   node review/G5/a5/scripts/flashcheck.mjs --shots "a5_c007:4,20,after" [--out <dir>]   （1920×1080 PNG）
// 光敏：每格縮成 640×360（BOX），同 tools/capture_analyze.py 的門檻，算 fine 32×18 與 16×9 每秒最多幾次（亮度、紅色）。
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] !== undefined ? args[i + 1] : d; };
const dist = resolve(opt('--dist', process.env.A5_DIST ?? join(ROOT, 'review/G5/a5/dist')));
const out = resolve(opt('--out', join(process.env.A5_DIST ?? join(ROOT, 'review/G5/a5/dist'), '_check')));
const cues = (opt('--cues', '') || '').split(',').filter(Boolean);
const shots = (opt('--shots', '') || '').split(';').filter(Boolean).map((s) => { const [id, ts] = s.split(':'); return [id, ts.split(',')]; });
const fps = Number(opt('--fps', '30'));
const [W, H] = opt('--size', '960x540').split('x').map(Number);
const from = Number(opt('--from', '0')), to = Number(opt('--to', '1e9'));
if (!existsSync(join(dist, 'index.html'))) { console.error('先跑 build_private.mjs'); process.exit(1); }
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
async function open(w, h) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=${fps}`);
  await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
  return page;
}
const list = [];
if (args.includes('--list')) {
  const page = await open(640, 360);
  const all = await page.evaluate(() => window.__engine.getCues());
  let tot = 0;
  for (const c of all.filter((x) => x.id.startsWith(opt('--list', 'a5') === '--list' ? 'a5' : opt('--list', 'a5')))) { tot += c.duration; console.log(c.id, c.duration.toFixed(2)); }
  console.log('合計', tot.toFixed(2));
  await page.close();
}
if (cues.length) {
  const page = await open(W, H);
  const all = await page.evaluate(() => window.__engine.getCues());
  for (const id of cues) {
    const c = all.find((x) => x.id === id);
    if (!c) { console.log('沒有', id); continue; }
    const dir = join(out, id);
    rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
    await page.evaluate((cid) => window.__engine.capture.playCue(cid), id);
    const n = Math.floor(c.duration * fps + 1e-6);
    let k0 = Math.max(0, Math.ceil(from * fps)), k1 = Math.min(n, Math.floor(to * fps));
    for (let k = k0; k <= k1; k++) {
      await page.evaluate((t) => window.__engine.capture.seek(t), k / fps);
      await page.screenshot({ path: join(dir, `${String(k).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 85 });
    }
    list.push({ id, dir, fps, duration: c.duration });
    console.log(`${id} ${c.duration.toFixed(2)} 秒，${k1 - k0 + 1} 格`);
  }
  await page.close();
  writeFileSync(join(out, 'list.json'), JSON.stringify(list));
  const py = spawnSync('/opt/anaconda3/bin/python3', [join(ROOT, 'review/G5/a5/scripts/flashcheck.py'), join(out, 'list.json')], { stdio: 'inherit' });
  if (py.status !== 0) console.log('分析失敗');
}
if (shots.length) {
  const page = await open(1920, 1080);
  const all = await page.evaluate(() => window.__engine.getCues());
  for (const [id, ts] of shots) {
    const c = all.find((x) => x.id === id);
    if (!c) { console.log('沒有', id); continue; }
    await page.evaluate((cid) => window.__engine.capture.playCue(cid), id);
    for (const s of ts) {
      const t = s === 'after' ? c.duration + 0.001 : Number(s);
      await page.evaluate((tt) => window.__engine.capture.seek(tt), t);
      const f = join(out, `${id}_${s === 'after' ? 'after' : Number(s).toFixed(2)}.png`);
      await page.screenshot({ path: f, type: 'png' });
      console.log(f);
    }
  }
  await page.close();
}
await browser.close();
