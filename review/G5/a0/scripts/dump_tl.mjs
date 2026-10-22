// 列出指定段落每個 cue 的長度與台詞起訖（私人建置 review/G5/a0/dist）。用法：node dump_tl.mjs a0,a1
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const segs = (process.argv[2] || 'a0,a1').split(',');
const dist = process.argv[3] || join(ROOT, 'review/G5/a0/dist');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 640, height: 360 } });
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A`);
await page.waitForFunction(() => window.__engine && window.__engine.ready(), null, { timeout: 90000 });
const cues = await page.evaluate(() => window.__engine.getCues());
for (const s of segs) {
  let tot = 0;
  for (const c of cues.filter((x) => x.segment === s)) {
    const tl = await page.evaluate((id) => window.__engine.debug.timeline(id), c.id);
    tot += c.duration;
    const ls = (tl?.lines ?? []).map((l) => `${(l.id ?? l.line?.id ?? '').slice(-2)}:${l.start.toFixed(2)}-${l.end.toFixed(2)}`).join(' ');
    console.log(`${c.id} ${c.duration.toFixed(2)}  ${ls}`);
  }
  console.log(`${s} total ${tot.toFixed(2)}`);
}
await browser.close();
