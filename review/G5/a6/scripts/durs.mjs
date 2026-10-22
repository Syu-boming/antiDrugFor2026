// 第六幕代理：印出各 cue 長度（私人建置，引擎時間軸）
//   node review/G5/a6/scripts/durs.mjs [a6,a7,a8]
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const SCR = '/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad/a678';
const segs = (process.argv[2] ?? 'a6,a7,a8').split(',');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 480, height: 270 } });
await page.goto(`${pathToFileURL(join(SCR, 'dist/index.html')).href}?capture=1&cues=show&q=B`);
await page.waitForFunction(() => window.__engine && window.__engine.ready(), null, { timeout: 120000 });
const cues = await page.evaluate(() => window.__engine.getCues().map((c) => ({ id: c.id, d: c.duration })));
for (const s of segs) {
  const cs = cues.filter((c) => c.id.startsWith(s + '_'));
  console.log(s, cs.reduce((a, c) => a + c.d, 0).toFixed(2), cs.map((c) => `${c.id.slice(3)} ${c.d.toFixed(2)}`).join('  '));
}
await browser.close();
