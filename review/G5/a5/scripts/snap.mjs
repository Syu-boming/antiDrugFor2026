// 第五幕製作用的快速試拍（私人建置 review/G5/a5/dist；不是驗收包，驗收包照 tools/act_review_pack.mjs）。
// 用法：node review/G5/a5/scripts/snap.mjs "a5_c001:1,5,9.5;a5_c005:2" [--out review/G5/a5/checks/snaps] [--w 960]
//        時間寫 "end" 表示 cue 結束停格；另外印出每個 cue 的長度。
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const spec = args[0] ?? 'a5_c001:1';
const out = resolve(ROOT, opt('--out', 'review/G5/a5/checks/snaps'));
const W = Number(opt('--w', '960'));
const dist = resolve(ROOT, opt('--dist', 'review/G5/a5/dist'));
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: W, height: Math.round(W * 9 / 16) }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=10`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 120000 });
const cues = await page.evaluate(() => window.__engine.getCues().filter((c) => c.segment === 'a5').map((c) => ({ id: c.id, d: c.duration, set: c.set })));
console.log(cues.map((c) => `${c.id} ${c.d.toFixed(2)}s ${c.set}`).join('\n'), `\n合計 ${cues.reduce((n, c) => n + c.d, 0).toFixed(1)} s`);
for (const part of spec.split(';').filter(Boolean)) {
  const [id, ts] = part.split(':');
  await page.evaluate((cid) => window.__engine.capture.playCue(cid), id);
  const D = cues.find((c) => c.id === id)?.d ?? 0;
  for (const tt of ts.split(',')) {
    const t = tt === 'end' ? D + 0.001 : Number(tt);
    await page.evaluate((x) => window.__engine.capture.seek(x), t);
    const f = join(out, `${id}_${tt === 'end' ? 'end' : Number(tt).toFixed(1).padStart(5, '0')}.png`);
    await page.screenshot({ path: f });
  }
}
if (errs.length) console.log('錯誤：', errs.slice(0, 8).join('\n'));
const rep = await page.evaluate(() => (window.__engine.getState().report ?? []).filter((r) => /a5|救護|medic|第五/.test(String(r))));
if (rep.length) console.log('準備畫面：', rep.join('\n'));
await browser.close();
