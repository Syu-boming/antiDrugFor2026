// 第六幕代理的私人光敏檢查（不是驗收包）：照驗收包的播放錄製方式（預捲＋逐格＋教師停格）逐格截圖，
// 再用和驗收包相同的門檻算 16×9 與 fine_32x18 的每秒變化次數。
//   node review/G5/a6/scripts/flashcheck.mjs --cues a6_c002,a6_c003 [--dist dir] [--w 960] [--fps 30] [--keep]
// 輸出：<scratchpad>/a678/flash/report.json（flagged 依 cue 與 cue 秒列出）；影格用完即刪（--keep 保留）。
import { createRequire } from 'node:module';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const SCR = '/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad/a678';
const dist = resolve(opt('--dist', join(SCR, 'dist')));
const out = resolve(opt('--out', join(SCR, 'flash')));
const W = Number(opt('--w', '960')), H = Math.round(W * 9 / 16);
const FPS = Number(opt('--fps', '30'));
const level = Number(opt('--level', '0'));
const HOLD = { title: 2.0, curtain: 2.0, scene: 3.5, wait: 3.5, quiz: 3.0, reveal: 2.5, lamp: 2.5 };
const ids = opt('--cues', '').split(',').filter(Boolean);
rmSync(join(out, 'frames'), { recursive: true, force: true });
mkdirSync(join(out, 'frames'), { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=${FPS}`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 120000 });
if (level) await page.evaluate((l) => window.__engineShow.setCompression(l), level);
const cues = await page.evaluate(() => window.__engine.getCues().map((c) => ({ id: c.id, kind: c.kind, duration: c.duration, autoAdvance: !!c.autoAdvance })));
const seq = [];   // [file, cueId, cueT]
let n = 0;
const shot = async (cue, ct) => {
  const f = join(out, 'frames', `${String(n++).padStart(6, '0')}.jpg`);
  await page.screenshot({ path: f, type: 'jpeg', quality: 90 });
  seq.push([f, cue, Math.round(ct * 1000) / 1000]);
};
await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'before' }), ids[0]);
await shot('before', 0);
for (const id of ids) {
  const c = cues.find((x) => x.id === id);
  await page.evaluate((x) => window.__engine.capture.playCue(x), id);
  const st = await page.evaluate(() => window.__engine.getState());
  const pre = st.prerollSec || 0;
  for (let k = 0; k < Math.round(pre * FPS); k++) { await page.evaluate((t) => window.__engine.capture.seek(t), -pre + k / FPS); await shot(id, -pre + k / FPS); }
  const nn = Math.round(st.cueDuration * FPS);
  for (let k = 0; k < nn; k++) { await page.evaluate((t) => window.__engine.capture.seek(t), k / FPS); await shot(id, k / FPS); }
  await page.evaluate((t) => window.__engine.capture.seek(t), st.cueDuration + 0.001);
  const hold = c.autoAdvance ? 0 : (HOLD[c.kind] ?? 2);
  const f = join(out, 'frames', `${String(n++).padStart(6, '0')}.jpg`);
  await page.screenshot({ path: f, type: 'jpeg', quality: 90 });
  for (let k = 0; k < Math.round(hold * FPS); k++) seq.push([f, id, Math.round((st.cueDuration + k / FPS) * 1000) / 1000]);
  console.log(`${id} ${st.cueDuration.toFixed(2)} s（預捲 ${pre}）`);
}
await browser.close();
writeFileSync(join(out, 'seq.json'), JSON.stringify({ fps: FPS, seq }));
if (errs.length) console.log('console:', errs.slice(0, 10).join('\n'));
const r = spawnSync('/opt/anaconda3/bin/python3', [join(dirname(fileURLToPath(import.meta.url)), 'flashcheck.py'), join(out, 'seq.json'), join(out, 'report.json')], { stdio: 'inherit' });
if (!args.includes('--keep')) rmSync(join(out, 'frames'), { recursive: true, force: true });
process.exit(r.status ?? 0);
