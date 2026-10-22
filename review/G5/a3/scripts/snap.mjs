// 第三幕製作用的快照（私人建置 review/G5/a3/dist）：指定 cue 內秒數截圖，拼成一張接觸表（製作時自己看構圖用，不是驗收包）。
// 用法：node review/G5/a3/scripts/snap.mjs "a3_c001:0,2,4.5;a3_c002:1,3" <輸出 jpg> [--dist review/G5/a3/dist] [--w 960]
import { createRequire } from 'node:module';
import { mkdirSync, existsSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const spec = args[0];
const outJpg = resolve(args[1] ?? join(ROOT, 'review/G5/a3/_snap.jpg'));
const dist = join(resolve(ROOT, opt('--dist', 'review/G5/a3/dist')), 'index.html');
const W = Number(opt('--w', '960'));
const tmp = join(dirname(outJpg), '_snap_tmp');
rmSync(tmp, { recursive: true, force: true });
mkdirSync(tmp, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
await page.goto(`${pathToFileURL(dist).href}?capture=1&cues=show&q=A&step=10`);
await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
const list = await page.evaluate(() => window.__engine.getCues().map((c) => ({ id: c.id, duration: c.duration, set: c.set })));
const files = [];
for (const part of spec.split(';').filter(Boolean)) {
  const [id, ts] = part.split(':');
  const c = list.find((x) => x.id === id);
  if (!c) { console.log('沒有 cue', id); continue; }
  console.log(`${id} ${c.set} ${c.duration.toFixed(2)} s`);
  await page.evaluate((cid) => window.__engine.capture.playCue(cid), id);
  for (const tsx of ts.split(',')) {
    const t = tsx === 'end' ? c.duration + 0.001 : Number(tsx);
    await page.evaluate((x) => window.__engine.capture.seek(x), t);
    const f = join(tmp, `${id}_${String(files.length).padStart(3, '0')}.jpg`);
    await page.screenshot({ path: f, type: 'jpeg', quality: 85 });
    files.push({ f, label: `${id} ${t.toFixed(2)}` });
  }
}
await browser.close();
if (errs.length) console.log('頁面錯誤：', errs.slice(0, 8));
// 拼圖（ffmpeg tile 不加字；用 python 拼）
const py = `
import sys,json
from PIL import Image,ImageDraw
fs=json.loads(sys.argv[1]); W=int(sys.argv[3]); H=W*9//16; cols=2 if len(fs)>1 else 1; rows=(len(fs)+cols-1)//cols
cv=Image.new('RGB',(cols*W,rows*H),(30,30,30)); d=ImageDraw.Draw(cv)
for i,e in enumerate(fs):
    im=Image.open(e['f']).convert('RGB').resize((W,H)); x=(i%cols)*W; y=(i//cols)*H; cv.paste(im,(x,y))
    d.rectangle([x,y,x+150,y+16],fill=(0,0,0)); d.text((x+3,y+2),e['label'],fill=(255,255,0))
    d.line([x,y+int(H*0.8),x+W,y+int(H*0.8)],fill=(255,0,0))
cv.save(sys.argv[2],quality=85)
`;
execFileSync('/opt/anaconda3/bin/python3', ['-c', py, JSON.stringify(files), outJpg, String(W)]);
console.log('wrote', outJpg);
