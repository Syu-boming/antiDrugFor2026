// 第六幕代理的快速預覽擷取（私人建置；不是驗收包）
//   node review/G5/a6/scripts/shots.mjs --spec "a6_c001:0,3,end;a6_c002:every2" [--out dir] [--dist dir] [--w 960] [--level 2]
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
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
const out = resolve(opt('--out', join(SCR, 'shots')));
const W = Number(opt('--w', '1920')), H = Math.round(W * 9 / 16);
const level = Number(opt('--level', '0'));
mkdirSync(out, { recursive: true });
const spec = opt('--spec', '').split(';').filter(Boolean).map((s) => { const [id, ts] = s.split(':'); return { id, ts: (ts ?? 'mid').split(',') }; });
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errs = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.text()); });
page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
await page.goto(`${pathToFileURL(join(dist, 'index.html')).href}?capture=1&cues=show&q=A&step=30`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
if (level) await page.evaluate((l) => window.__engineShow.setCompression(l), level);
const cues = await page.evaluate(() => window.__engine.getCues().map((c) => ({ id: c.id, duration: c.duration, lines: c.lines })));
const files = [];
for (const s of spec) {
  const c = cues.find((x) => x.id === s.id);
  if (!c) { console.log('no cue', s.id); continue; }
  await page.evaluate((id) => window.__engine.capture.playCue(id), s.id);
  let ts = [];
  for (const t of s.ts) {
    if (t === 'end') ts.push(c.duration + 0.001);
    else if (t === 'mid') ts.push(c.duration / 2);
    else if (t.startsWith('every')) { const st = Number(t.slice(5)); for (let x = 0; x <= c.duration + 1e-6; x += st) ts.push(x); }
    else ts.push(Number(t));
  }
  for (const t of ts) {
    await page.evaluate((tt) => window.__engine.capture.seek(tt), t);
    const f = join(out, `${s.id}_${t.toFixed(2).padStart(6, '0')}.png`);
    await page.screenshot({ path: f });
    files.push({ f, label: `${s.id} t=${t.toFixed(2)} / ${c.duration.toFixed(1)}` });
  }
  console.log(`${s.id} dur ${c.duration.toFixed(2)}`);
}
await browser.close();
writeFileSync(join(out, '_list.json'), JSON.stringify(files));
if (errs.length) console.log('console:', errs.slice(0, 12).join('\n'));
const py = `
import json,sys
from PIL import Image, ImageDraw, ImageFont
L=json.load(open(sys.argv[1]))
if not L: sys.exit()
cols=int(sys.argv[3]); tw=int(sys.argv[4])
ims=[Image.open(x['f']).convert('RGB') for x in L]
th=int(tw*ims[0].height/ims[0].width)
rows=(len(ims)+cols-1)//cols
sheet=Image.new('RGB',(cols*tw,rows*(th+26)),(30,26,24))
try: font=ImageFont.truetype('/System/Library/Fonts/PingFang.ttc',18)
except Exception: font=None
d=ImageDraw.Draw(sheet)
for i,(im,x) in enumerate(zip(ims,L)):
  r,c=divmod(i,cols); sheet.paste(im.resize((tw,th)),(c*tw,r*(th+26)+26)); d.text((c*tw+6,r*(th+26)+3),x['label'],fill=(240,230,210),font=font)
sheet.save(sys.argv[2])
`;
const sheet = join(out, opt('--sheet', 'sheet.jpg'));
spawnSync('/opt/anaconda3/bin/python3', ['-c', py, join(out, '_list.json'), sheet, opt('--cols', '4'), opt('--tw', '480')], { stdio: 'inherit' });
console.log('sheet', sheet);
