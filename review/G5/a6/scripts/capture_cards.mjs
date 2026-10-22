// 第六幕代理：擷取 a7_c001 三張大紙卡的來源畫面（不含字幕；私人建置，不是驗收包）
//   node review/G5/a6/scripts/capture_cards.mjs [--dist dir] [--spec "a3_c002:9.0;a4_c012:6.3;a5_c006:6.0"]
// 輸出 review/G5/a6/cards_src/<cue>_<秒>.png（1920×1080）；之後 make_cards.py 用這三張做紙卡插畫。
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const dist = resolve(opt('--dist', '/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad/a678/dist'));
const out = join(ROOT, 'review/G5/a6/cards_src');
mkdirSync(out, { recursive: true });
const spec = opt('--spec', 'a3_c002:9.0;a4_c012:6.3;a5_c006:6.0').split(';').map((s) => s.split(':'));
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=30`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
await page.addStyleTag({ content: '#subtitle-box, .badge { display: none !important; }' });
for (const [id, t] of spec) {
  await page.evaluate((c) => window.__engine.capture.playCue(c), id);
  await page.evaluate((tt) => window.__engine.capture.seek(tt), Number(t));
  const f = join(out, `${id}_${Number(t).toFixed(1)}.png`);
  await page.screenshot({ path: f });
  console.log(f);
}
await browser.close();
