// 列印檔用的圖：從 assets/final 的角色母版裁切（貼紙、參與小卡的動作小圖），折折用 app 的摺紙貓程式渲染。
// 規則：不用阿樂叔叔受影響的畫面、不放操偶線（母版本身沒有線）、沒有食物；圖上不放任何文字。
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';

/** 取 assets 某資料夾裡最新版本的檔案：chr-xiaoqing_master → chr-xiaoqing_master_v04.png */
function latest(dir, id) {
  if (!existsSync(dir)) return null;
  const re = new RegExp(`^${id.replace(/[-]/g, '\\-')}_v(\\d+)\\.png$`);
  const hits = readdirSync(dir).map((f) => [f, re.exec(f)]).filter(([, m]) => m).sort((a, b) => Number(b[1][1]) - Number(a[1][1]));
  return hits.length ? join(dir, hits[0][0]) : null;
}

/**
 * 輸出清單：name → { src: [資料夾, id], crop: 上方保留比例（1＝全身）, maxH }
 * 阿樂叔叔：assets/final 只有從正式母版切出的分件（assets/final/rig，README 說明疊回去和母版逐像素相同），
 * 母版本身在 assets/generated/chr-ale_master_v02.png（G2 正式母版），所以從那裡裁。
 */
export const ART = {
  // 貼紙（全身）
  'st-xiaoqing': { src: ['final', 'chr-xiaoqing_master'], crop: 1, maxH: 1100, label: '小晴' },
  'st-xiaoyu': { src: ['final', 'chr-xiaoyu_master'], crop: 1, maxH: 1100, label: '小宇' },
  'st-ale': { src: ['generated', 'chr-ale_master'], crop: 1, maxH: 1100, label: '阿樂叔叔' },
  'st-pinan': { src: ['final', 'chr-pinan_master'], crop: 1, maxH: 1100, label: '品安' },
  'st-lin': { src: ['final', 'chr-lin_master'], crop: 1, maxH: 1100, label: '林老師' },
  'st-ye': { src: ['final', 'chr-ye_master'], crop: 1, maxH: 1100, label: '葉護理師' },
  'st-chen': { src: ['final', 'chr-chen_master'], crop: 1, maxH: 1100, label: '陳伯伯' },
  'st-xiaoqing-bow': { src: ['final', 'chr-xiaoqing_pose-bow'], crop: 1, maxH: 900, label: '小晴（鞠躬）' },
  'st-xiaoyu-bow': { src: ['final', 'chr-xiaoyu_pose-bow'], crop: 1, maxH: 900, label: '小宇（鞠躬）' },
  // 圓形貼紙（半身）
  'bust-xiaoqing': { src: ['final', 'chr-xiaoqing_master'], crop: 0.36, maxH: 700 },
  'bust-xiaoyu': { src: ['final', 'chr-xiaoyu_master'], crop: 0.37, maxH: 700 },
  'bust-ale': { src: ['generated', 'chr-ale_master'], crop: 0.3, maxH: 700 },
  'bust-pinan': { src: ['final', 'chr-pinan_master'], crop: 0.36, maxH: 700 },
  // 參與小卡的四個動作（同第三幕練習卡：小晴 cross、小宇 palmno、小晴 pointr、小宇 forehead，膝蓋以上）
  'act-cross': { src: ['final', 'chr-xiaoqing_pose-cross'], crop: 0.62, maxH: 600, label: '不碰' },
  'act-palmno': { src: ['final', 'chr-xiaoyu_pose-palmno'], crop: 0.62, maxH: 600, label: '不試' },
  'act-pointr': { src: ['final', 'chr-xiaoqing_pose-pointr'], crop: 0.62, maxH: 600, label: '先離開' },
  'act-forehead': { src: ['final', 'chr-xiaoyu_pose-forehead'], crop: 0.62, maxH: 600, label: '找大人' },
};
export const ZZ_ART = ['st-zhezhe', 'bust-zhezhe'];

export function allPresent(TEACHER) {
  return [...Object.keys(ART), ...ZZ_ART].every((n) => existsSync(join(TEACHER, 'img', `${n}.png`)));
}

export function sources(ROOT) {
  const out = {};
  for (const [name, a] of Object.entries(ART)) {
    const dir = join(ROOT, 'assets', a.src[0]);
    out[name] = latest(dir, a.src[1]);
  }
  return out;
}

export async function renderArt(ROOT, TEACHER, browser, log) {
  const srcs = sources(ROOT);
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><body style="margin:0;background:transparent"></body></html>');
  const manifest = {};
  for (const [name, a] of Object.entries(ART)) {
    const f = srcs[name];
    if (!f) { log(`找不到 ${a.src.join('/')}，略過 ${name}`); continue; }
    const dataUrl = `data:image/png;base64,${readFileSync(f).toString('base64')}`;
    const out = await page.evaluate(async ({ dataUrl, crop, maxH }) => {
      const im = new Image(); im.src = dataUrl; await im.decode();
      const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
      const g = c.getContext('2d'); g.drawImage(im, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height).data;
      let x0 = c.width, y0 = c.height, x1 = 0, y1 = 0;
      for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) if (d[(y * c.width + x) * 4 + 3] > 8) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      const h = Math.round((y1 - y0 + 1) * crop);
      // 裁上半部時，重新算這一段的左右邊界
      let cx0 = c.width, cx1 = 0;
      for (let y = y0; y < y0 + h; y++) for (let x = 0; x < c.width; x++) if (d[(y * c.width + x) * 4 + 3] > 8) { if (x < cx0) cx0 = x; if (x > cx1) cx1 = x; }
      const w = cx1 - cx0 + 1;
      const s = Math.min(1, maxH / h);
      const o = document.createElement('canvas'); o.width = Math.round(w * s); o.height = Math.round(h * s);
      const og = o.getContext('2d'); og.imageSmoothingQuality = 'high';
      og.drawImage(c, cx0, y0, w, h, 0, 0, o.width, o.height);
      // 裁切的下緣做 6% 漸淡，避免半身圖切口生硬
      if (crop < 1) {
        og.globalCompositeOperation = 'destination-out';
        const grd = og.createLinearGradient(0, o.height * 0.9, 0, o.height);
        grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(1, 'rgba(0,0,0,1)');
        og.fillStyle = grd; og.fillRect(0, o.height * 0.9, o.width, o.height * 0.1);
      }
      return { url: o.toDataURL('image/png'), w: o.width, h: o.height };
    }, { dataUrl, crop: a.crop, maxH: a.maxH });
    writeFileSync(join(TEACHER, 'img', `${name}.png`), Buffer.from(out.url.split(',')[1], 'base64'));
    manifest[name] = { source: f.slice(ROOT.length + 1), crop: a.crop, size: [out.w, out.h] };
  }
  await page.close();
  // 折折：用 app 的程式（app/src/stage/zhezhe.ts）在透明背景上渲染
  try {
    const zz = await renderZhezhe(ROOT, browser);
    for (const [name, url] of Object.entries(zz)) {
      writeFileSync(join(TEACHER, 'img', `${name}.png`), Buffer.from(url.split(',')[1], 'base64'));
      manifest[name] = { source: 'app/src/stage/zhezhe.ts（程式渲染，透明背景）' };
    }
  } catch (e) {
    log(`折折渲染失敗：${e.message}；改用 assets/final/ui/ui-speaker_zhezhe_v01.png`);
    const f = join(ROOT, 'assets/final/ui/ui-speaker_zhezhe_v01.png');
    for (const n of ZZ_ART) { writeFileSync(join(TEACHER, 'img', `${n}.png`), readFileSync(f)); manifest[n] = { source: 'assets/final/ui/ui-speaker_zhezhe_v01.png（退路）' }; }
  }
  writeFileSync(join(TEACHER, 'img', 'manifest.json'), JSON.stringify(manifest, null, 1));
  log(`圖 ${Object.keys(manifest).length} 張 → teacher/img/`);
}

async function renderZhezhe(ROOT, browser) {
  const require = createRequire(join(ROOT, 'app/package.json'));
  const esbuild = require('esbuild');
  const dir = join(tmpdir(), `teacher_zz_${process.pid}`);
  mkdirSync(dir, { recursive: true });
  const entry = `
import * as THREE from 'three';
import { Zhezhe } from './zhezhe';
window.__render = (o) => {
  const S = o.size;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
  renderer.setPixelRatio(1); renderer.setSize(S, S, false); renderer.setClearColor(0x000000, 0);
  document.body.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const hemi = new THREE.HemisphereLight('#fff3dc', '#6b5846', 1.35);
  const key = new THREE.DirectionalLight('#ffe9c8', 2.2); key.position.set(-7, 13, 16);
  const fill = new THREE.DirectionalLight('#d6e4ff', 0.5); fill.position.set(9, 6, 12);
  scene.add(hemi, key, fill);
  const cat = new Zhezhe({ position: [0, 0, 0], height: 1, facing: o.facing, seed: 11, contactShadow: false, castShadow: false, presence: 0.1 });
  scene.add(cat.group);
  cat.setTrack({ start: { emotion: o.emotion, form: 'idle' }, events: [] });
  cat.update(1.0, {});
  const camera = new THREE.PerspectiveCamera(20, 1, 0.1, 100);
  const tgt = [0, o.ty, 0];
  const dist = (o.k / 2) / Math.tan(10 * Math.PI / 180);
  const a = o.orbit, e = 0.08;
  camera.position.set(tgt[0] + Math.sin(a) * Math.cos(e) * dist, tgt[1] + Math.sin(e) * dist, tgt[2] + Math.cos(a) * Math.cos(e) * dist);
  camera.lookAt(tgt[0], tgt[1], tgt[2]);
  cat.update(1.0, {});
  renderer.render(scene, camera);
  // 裁到不透明範圍
  const src = renderer.domElement;
  const c = document.createElement('canvas'); c.width = S; c.height = S;
  const g = c.getContext('2d'); g.drawImage(src, 0, 0);
  const d = g.getImageData(0, 0, S, S).data;
  let x0 = S, y0 = S, x1 = 0, y1 = 0;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) if (d[(y * S + x) * 4 + 3] > 8) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  const pad = 6, w = x1 - x0 + 1 + pad * 2, h = y1 - y0 + 1 + pad * 2;
  const out = document.createElement('canvas'); out.width = w; out.height = h;
  out.getContext('2d').drawImage(c, x0 - pad, y0 - pad, w, h, 0, 0, w, h);
  renderer.dispose(); renderer.domElement.remove();
  return out.toDataURL('image/png');
};
window.__ready = true;
`;
  await esbuild.build({ stdin: { contents: entry, resolveDir: join(ROOT, 'app/src/stage'), sourcefile: 'teacher_zz_entry.js', loader: 'js' }, bundle: true, format: 'iife', target: ['chrome100'], outfile: join(dir, 'zz.js'), logLevel: 'warning', define: { 'process.env.NODE_ENV': '"production"' } });
  writeFileSync(join(dir, 'index.html'), '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:transparent"><script src="zz.js"></script></body></html>');
  const page = await browser.newPage();
  await page.goto(pathToFileURL(join(dir, 'index.html')).href);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 15000 });
  const st = await page.evaluate(() => window.__render({ size: 1400, facing: 0.32, emotion: 'happy', orbit: 0, ty: 0.5, k: 1.25 }));
  const bust = await page.evaluate(() => window.__render({ size: 1400, facing: 0.2, emotion: 'happy', orbit: 0, ty: 0.62, k: 0.85 }));
  await page.close();
  return { 'st-zhezhe': st, 'bust-zhezhe': bust };
}
