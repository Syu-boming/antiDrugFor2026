// 指定 cue 與時間截圖（1920×1080，?capture=1）：node shots.mjs <dist> <輸出資料夾> <cues> "a1_c007:0,1,2;a2_c001:5" [--js "<每格後執行的程式，回傳值存 json>"]
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const [distArg, outArg, cues, spec] = process.argv.slice(2);
const jsI = process.argv.indexOf('--js');
const js = jsI > 0 ? process.argv[jsI + 1] : null;
const out = resolve(process.cwd(), outArg);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`${pathToFileURL(join(resolve(process.cwd(), distArg), 'index.html')).href}?capture=1&cues=${cues}&q=A&step=10`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 120000 });
const res = {};
for (const part of spec.split(';').filter(Boolean)) {
  const [id, ts] = part.split(':');
  await page.evaluate((x) => window.__engine.capture.playCue(x), id);
  for (const tt of ts.split(',')) {
    const t = tt === 'after' ? (await page.evaluate(() => window.__engine.getState().cueDuration)) + 0.001 : Number(tt);
    await page.evaluate((x) => window.__engine.capture.seek(x), t);
    const name = `${id}_${tt}`;
    await page.screenshot({ path: join(out, `${name}.png`) });
    if (js) res[name] = await page.evaluate(js);
  }
}
if (js) writeFileSync(join(out, 'shots.json'), JSON.stringify(res, null, 1));
await browser.close();
console.log(`[shots] ${out}${errs.length ? `；錯誤 ${errs.slice(0, 3).join(' | ')}` : ''}`);
