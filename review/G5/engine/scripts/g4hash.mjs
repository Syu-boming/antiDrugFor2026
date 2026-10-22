// G4 逐像素比對：?cues=g4&capture=1 每個 cue 每 0.5 秒截圖（1920×1080），存每格 PNG 的 SHA-1；
// 第二個參數給上一次的結果 JSON 時，列出不同的格。
// 用法：node review/G5/engine/scripts/g4hash.mjs <dist 資料夾> <輸出 json> [基準 json] [cues=g4] [step=0.5]
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const [distArg, outArg, baseArg, cuesArg, stepArg, onlyArg] = process.argv.slice(2);
const cues = cuesArg && cuesArg !== '-' ? cuesArg : 'g4';
const step = Number(stepArg && stepArg !== '-' ? stepArg : 0.5);
const only = onlyArg ? new Set(onlyArg.split(',')) : null;
const dist = join(resolve(process.cwd(), distArg), 'index.html');
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
await page.goto(`${pathToFileURL(dist).href}?capture=1&cues=${cues}&q=A&step=10`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 120000 });
const list = await page.evaluate(() => window.__engine.getCues());
const out = {};
for (const c of list) {
  if (only && !only.has(c.id)) continue;
  await page.evaluate((id) => window.__engine.capture.playCue(id), c.id);
  for (let t = 0; t <= c.duration + 1e-6; t += step) {
    await page.evaluate((x) => window.__engine.capture.seek(x), t);
    const buf = await page.screenshot({ type: 'png' });
    out[`${c.id}@${t.toFixed(2)}`] = createHash('sha1').update(buf).digest('hex');
  }
  await page.evaluate((x) => window.__engine.capture.seek(x), c.duration + 0.001);
  out[`${c.id}@after`] = createHash('sha1').update(await page.screenshot({ type: 'png' })).digest('hex');
}
await browser.close();
writeFileSync(resolve(process.cwd(), outArg), JSON.stringify(out, null, 0));
let msg = `${Object.keys(out).length} 格`;
if (baseArg && existsSync(resolve(process.cwd(), baseArg))) {
  const base = JSON.parse(readFileSync(resolve(process.cwd(), baseArg), 'utf8'));
  const diff = Object.keys(out).filter((k) => base[k] !== out[k]);
  msg += `；和基準不同 ${diff.length} 格${diff.length ? '：' + diff.slice(0, 20).join('、') : ''}`;
}
console.log(`[g4hash] ${cues} ${msg}${errs.length ? `；頁面錯誤 ${errs.slice(0, 2).join(' | ')}` : ''}`);
