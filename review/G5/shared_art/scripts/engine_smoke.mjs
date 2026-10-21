// G5 共用美術：在真的引擎裡確認新角色立牌（show_characters.json）建得起來、臉部換片模式正確（煙霧測試，不是驗收包）。
// 用法：node review/G5/shared_art/scripts/engine_smoke.mjs   （先在 app/ 跑 npm run build）
// 對每個指定 cue：playCue → seek 1.2 秒 → 讀 getState().castReport、debug.faces()，存一張 1280×720 截圖到 review/G5/shared_art/engine_smoke/。
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const out = join(ROOT, 'review/G5/shared_art/engine_smoke');
mkdirSync(out, { recursive: true });
const cues = (process.argv[2] ?? 'a1_c001,a2_c012,a3_c003,a4_c001,a5_c001').split(',');
const url = `${pathToFileURL(join(ROOT, 'app/dist/index.html')).href}?capture=1&cues=show&q=A&step=10&nofs=1`;
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`));
await page.goto(url);
await page.waitForFunction(() => window.__engine && window.__engine.ready(), null, { timeout: 90000 });
const report = { url, cues: {}, errors };
for (const id of cues) {
  try {
    await page.evaluate((cid) => window.__engine.capture.playCue(cid), id);
    await page.evaluate(() => window.__engine.capture.seek(1.2));
    const st = await page.evaluate(() => { const s = window.__engine.getState(); return { set: s.set, actors: s.actors, castReport: s.castReport }; });
    const faces = await page.evaluate(() => window.__engine.debug.faces());
    await page.screenshot({ path: join(out, `${id}.png`) });
    report.cues[id] = { ...st, faces };
    console.log(id, st.set, JSON.stringify(st.castReport));
  } catch (e) {
    report.cues[id] = { error: String(e) };
    console.log(id, 'ERROR', String(e));
  }
}
await browser.close();
writeFileSync(join(out, 'smoke.json'), JSON.stringify(report, null, 1));
console.log('console errors', errors.length, errors.slice(0, 5));
