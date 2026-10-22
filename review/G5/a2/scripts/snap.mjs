// 第二幕修正用的快速擷取（a2 代理自查用，不是驗收包）：私人建置 review/G5/a2/dist 上，指定 cue 內秒數存 PNG＋probe。
// 用法：node review/G5/a2/scripts/snap.mjs <輸出資料夾> a2_c001:0,12,23.7 a2_c008:3,5 [--w 960] [--probe]
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const out = resolve(args[0]);
const W = Number(opt('--w', '1920')), H = Math.round(W * 9 / 16);
const dist = resolve(opt('--dist', join(ROOT, 'review/G5/a2/dist')), 'index.html');
const specs = args.slice(1).filter((a) => a.includes(':') && !a.startsWith('--'));
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`${pathToFileURL(dist).href}?capture=1&cues=show&q=A`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
const list = await page.evaluate(() => window.__engine.getCues().map((c) => ({ id: c.id, duration: c.duration })));
const probes = [];
for (const s of specs) {
  const [id, ts] = s.split(':');
  const c = list.find((x) => x.id === id);
  if (!c) { console.log('沒有', id); continue; }
  await page.evaluate((cid) => window.__engine.capture.playCue(cid), id);
  const times = ts === 'all' ? Array.from({ length: Math.floor(c.duration) + 1 }, (_, i) => i) : ts.split(',').map((x) => (x === 'end' ? c.duration + 0.001 : Number(x)));
  for (const t of times) {
    await page.evaluate((tt) => window.__engine.capture.seek(tt), t);
    const f = `${id}_${t.toFixed(2).padStart(6, '0')}.png`;
    await page.screenshot({ path: join(out, f) });
    if (args.includes('--probe')) probes.push({ id, t, ...(await page.evaluate(() => window.__engine.debug.probe())) });
  }
  console.log(id, '長度', c.duration.toFixed(2), '格', times.length);
}
if (probes.length) writeFileSync(join(out, 'probe.json'), JSON.stringify(probes));
if (errs.length) console.log('錯誤：', errs.slice(0, 10).join('\n'));
await browser.close();
