// 紙青蛙（a1_c001）確定性：同一秒用不同路徑（直接跳、逐格前進、退回、重播）擷取，比較整格像素雜湊
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const ROOT = '/Users/boming/Documents/AI tool/反毒小劇場';
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const dist = process.argv[2] ?? join(ROOT, 'app/dist');
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1'] });
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=30`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 240000 });
const h = async () => createHash('sha1').update(await page.screenshot()).digest('hex').slice(0, 12);
const out = {};
for (const [id, times] of [['a1_c001', [21.6, 22.3, 23.0, 24.5, 27.9]], ['a0_c004', [19.0, 20.5]], ['a0_c005', [1.2, 2.4]]]) {
  for (const t of times) {
    const r = {};
    await page.evaluate((x) => window.__engine.gotoCue(x, { mode: 'before' }), id);
    await page.evaluate((x) => window.__engine.capture.playCue(x), id);
    await page.evaluate((s) => window.__engine.capture.seek(s), t); r.direct = await h();
    await page.evaluate((s) => window.__engine.capture.seek(s), t - 1.0);
    await page.evaluate(() => window.__engine.capture.step(30)); r.stepped = await h();
    await page.evaluate((s) => window.__engine.capture.seek(s), t + 0.7);
    await page.evaluate((s) => window.__engine.capture.seek(s), t); r.back = await h();
    await page.evaluate((x) => window.__engine.capture.playCue(x), id);
    await page.evaluate((s) => window.__engine.capture.seek(s), t); r.replay = await h();
    r.same = new Set([r.direct, r.stepped, r.back, r.replay]).size === 1;
    out[`${id}@${t}`] = r;
  }
}
console.log(JSON.stringify(out, null, 1));
await browser.close();
