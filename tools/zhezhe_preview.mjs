// 折折（摺紙貓，FX13）獨立預覽頁＋驗收資料產生器。
// 用 app 的 three 與 app/src/stage 的模組（zhezhe.ts、G4 燈籠店景 workshop.ts、台口 sets.ts、鏡位 layers.ts）打包成一頁，
// 以 headless Chrome 逐格擷取：狀態接觸表、每種摺紙變形的逐格接觸表、旋轉掃描、和剪紙人物並排、光敏數據、投影模擬明度差、
// 效能、確定性（同一秒重建同一格），以及 a0_c002 開場自我介紹預覽影片（配 vo_a0_c002_01／02 對嘴）。
//
// 用法（專案根目錄）：
//   node tools/zhezhe_preview.mjs                    全部
//   node tools/zhezhe_preview.mjs --only look,states  只跑指定項目：build look states folds actions spin compare flash contrast perf determinism video
//   node tools/zhezhe_preview.mjs --out review/G5/zhezhe
// 輸出：review/G5/zhezhe/（preview/index.html 可直接 file:// 開啟互動預覽；INDEX.md 列出所有檔案與量測摘要）
// 製作代理不挑畫面：每張接觸表的取樣時間由節拍固定（見各段程式），量測全部由程式計算。
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const APP = join(ROOT, 'app');
const require = createRequire(join(APP, 'package.json'));
const { chromium } = require('playwright-core');
const esbuild = require('esbuild');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const OUT = resolve(ROOT, opt('--out', 'review/G5/zhezhe'));
const ALL = ['build', 'look', 'states', 'folds', 'actions', 'spin', 'compare', 'flash', 'contrast', 'perf', 'determinism', 'video'];
const only = new Set((opt('--only', ALL.join(','))).split(','));
only.add('build'); // 頁面程式在打包時注入，每次都重新打包（約 0.1 秒）
mkdirSync(OUT, { recursive: true });
const t0 = Date.now();
const log = (...a) => console.log(`[zhezhe ${((Date.now() - t0) / 1000).toFixed(1)}s]`, ...a);

// ─────────────────────────────────────────── 1. 打包預覽頁 ───────────────────────────────────────────
function latestAsset(id) {
  const dir = join(ROOT, 'assets/final');
  const re = new RegExp(`^${id.replace(/[-/]/g, (c) => `\\${c}`)}_v(\\d+)\\.(png|jpg|jpeg)$`, 'i');
  const hits = readdirSync(dir).map((f) => [f, re.exec(f)]).filter(([, m]) => m).sort((a, b) => Number(b[1][1]) - Number(a[1][1]));
  return hits.length ? join(dir, hits[0][0]) : null;
}

async function buildPreview() {
  const dir = join(OUT, 'preview');
  mkdirSync(dir, { recursive: true });
  const entry = `
import * as THREE from 'three';
import { Zhezhe, FOLD_BEATS, HUSH_BEATS, ZHEZHE_EMOTIONS, zhezheTrackFromTimeline, zhezheSeed } from './zhezhe';
import { buildWorkshopG4, applyPopup, G4_SET_IMAGES } from './workshop';
import { buildProscenium } from './sets';
import { CAMERA_PRESETS, LAYER } from './layers';
(${pageMain.toString()})({ THREE, Zhezhe, FOLD_BEATS, HUSH_BEATS, ZHEZHE_EMOTIONS, zhezheTrackFromTimeline, zhezheSeed, buildWorkshopG4, applyPopup, G4_SET_IMAGES, buildProscenium, CAMERA_PRESETS, LAYER });
`;
  await esbuild.build({
    stdin: { contents: entry, resolveDir: join(APP, 'src/stage'), sourcefile: 'zhezhe_preview_entry.js', loader: 'js' },
    bundle: true, format: 'iife', target: ['chrome100'], outfile: join(dir, 'preview.js'), minify: false, legalComments: 'none', logLevel: 'warning',
    define: { 'process.env.NODE_ENV': '"production"' },
  });
  // 素材（嵌成 data URL，file:// 開啟不會被跨來源擋住）
  const ids = ['bg-workshop-back', 'bg-workshop-floor', 'bg-workshop-table', 'bg-workshop-lanterns', 'bg-workshop-wing', 'chr-xiaoqing_master', 'chr-xiaoyu_master'];
  const data = { images: {}, lips: {} };
  for (const id of ids) {
    const f = latestAsset(id);
    if (!f) continue;
    const mime = f.endsWith('.png') ? 'image/png' : 'image/jpeg';
    data.images[id] = `data:${mime};base64,${readFileSync(f).toString('base64')}`;
  }
  for (const k of ['a0_c002_01', 'a0_c002_02']) {
    const f = join(ROOT, `audio/lipsync/${k}_v04.json`);
    if (existsSync(f)) data.lips[k] = JSON.parse(readFileSync(f, 'utf8'));
  }
  writeFileSync(join(dir, 'data.js'), `window.ZZ_DATA = ${JSON.stringify(data)};\n`);
  writeFileSync(join(dir, 'index.html'), `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>折折預覽</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;background:#1d1712;color:#f3e9d8;font:14px/1.5 "PingFang TC","Heiti TC","Microsoft JhengHei",sans-serif;overflow:hidden}
#ui{position:fixed;left:8px;top:8px;max-width:420px;background:rgba(20,14,10,.82);padding:8px 10px;border-radius:6px}
#ui button{margin:2px;padding:3px 8px;background:#5b3d2a;color:#fbf3e4;border:1px solid #8a6248;border-radius:4px;cursor:pointer}
#ui .row{margin:4px 0}#ui label{margin-right:6px}canvas{display:block}</style></head>
<body><script src="data.js"></script><script src="preview.js"></script></body></html>\n`);
  log('預覽頁', join(dir, 'index.html'));
}

// ─────────────────────────────────────────── 2. 頁面程式（在瀏覽器執行） ───────────────────────────────────────────
// 注意：這個函式會被 toString() 注入打包入口，不在 node 裡執行。
function pageMain(L) {
  const { THREE, Zhezhe, CAMERA_PRESETS } = L;
  const D = window.ZZ_DATA || { images: {}, lips: {} };
  const auto = /[?&]auto=1/.test(location.search);
  const S = { w: auto ? 1920 : innerWidth, h: auto ? 1080 : innerHeight };
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, alpha: false, stencil: false });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.setPixelRatio(1);
  renderer.setSize(S.w, S.h, true);
  document.body.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0b0806');
  const camera = new THREE.PerspectiveCamera(20, S.w / S.h, 0.5, 200);
  // 舞台燈（同 app/src/stage/stage.ts 的預設與 light 公式）
  const hemi = new THREE.HemisphereLight('#fff3dc', '#6b5846', 1.35);
  const key = new THREE.DirectionalLight('#ffe9c8', 2.2);
  const fill = new THREE.DirectionalLight('#d6e4ff', 0.5);
  key.position.set(-7, 13, 16); key.target.position.set(0, 2.5, -2); key.castShadow = true;
  const sc = key.shadow.camera; sc.left = -14; sc.right = 14; sc.top = 14; sc.bottom = -3; sc.near = 1; sc.far = 60;
  key.shadow.bias = -0.0004; key.shadow.normalBias = 0.03; key.shadow.radius = 4; key.shadow.intensity = 0.45; key.shadow.mapSize.set(2048, 2048);
  fill.position.set(9, 6, 12);
  scene.add(hemi, key, key.target, fill);
  const imgs = {};
  const setGroup = new THREE.Group(); scene.add(setGroup);
  const kidGroup = new THREE.Group(); scene.add(kidGroup);
  let pros = null;
  let cat = null;
  let catOpts = null;
  let lightLevel = 1;
  const lerp = (a, b, t) => a + (b - a) * t;
  function setLight(v) {
    lightLevel = v;
    hemi.intensity = 1.35 * lerp(0.45, 1, v); key.intensity = 2.2 * v; fill.intensity = 0.5 * lerp(0.6, 1, v);
    if (pros) pros.lip.material.emissiveIntensity = Math.max(0, (1 - v) * 2.2);
  }
  function loadImages() {
    return Promise.all(Object.entries(D.images).map(([id, src]) => new Promise((res) => { const im = new Image(); im.onload = () => { imgs[id] = im; res(); }; im.onerror = () => res(); im.src = src; })));
  }
  function opaqueBox(im) {
    const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
    const g = c.getContext('2d'); g.drawImage(im, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    let x0 = c.width, y0 = c.height, x1 = 0, y1 = 0;
    for (let y = 0; y < c.height; y += 2) for (let x = 0; x < c.width; x += 2) if (d[(y * c.width + x) * 4 + 3] > 128) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    return [x0, y0, x1 + 2, y1 + 2];
  }
  function standee(id, h, x, z, facing) {
    const im = imgs[id]; if (!im) return;
    const [x0, y0, x1, y1] = opaqueBox(im);
    const t = new THREE.Texture(im); t.colorSpace = THREE.SRGBColorSpace; t.needsUpdate = true; t.anisotropy = 4;
    t.repeat.set((x1 - x0) / im.naturalWidth, (y1 - y0) / im.naturalHeight);
    t.offset.set(x0 / im.naturalWidth, 1 - y1 / im.naturalHeight);
    const w = h * (x1 - x0) / (y1 - y0);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: t, alphaTest: 0.5, roughness: 0.92, side: THREE.DoubleSide }));
    m.position.set(x, h / 2, z); m.scale.x = facing; m.castShadow = true;
    kidGroup.add(m);
  }
  function buildScene() {
    const ws = L.buildWorkshopG4({ alphaToCoverage: false, image: (id) => imgs[id] });
    L.applyPopup(ws.pieces, 1);
    setGroup.add(ws.group);
    pros = L.buildProscenium();
    scene.add(pros.group);
    standee('chr-xiaoqing_master', 2.5, 1.85, 0.45, 1);
    standee('chr-xiaoyu_master', 2.42, 3.35, 0.3, -1);
    kidGroup.visible = false;
  }
  function makeCat(o) {
    if (cat) { scene.remove(cat.group); cat.dispose(); }
    catOpts = Object.assign({ position: [0.55, 1.4, -0.6], height: 1.0, facing: 'front', seed: 11 }, o || {});
    cat = new Zhezhe(catOpts);
    scene.add(cat.group);
    return cat;
  }
  function setSize(w, h) { S.w = w; S.h = h; renderer.setSize(w, h, true); camera.aspect = w / h; camera.updateProjectionMatrix(); }
  function view(v) {
    let pos, target, fov = 20;
    if (typeof v === 'string') { const p = CAMERA_PRESETS[v]; pos = p.pos; target = p.target; fov = p.fov; }
    else if (v && v.close) {
      const c = catOpts.position, h = catOpts.height * (v.zoom || 1);
      const tgt = [c[0] + (v.dx || 0) * catOpts.height, c[1] + (v.dy !== undefined ? v.dy : 0.5) * catOpts.height, c[2]];
      const dist = (h * (v.k || 1.9) / 2) / Math.tan((fov / 2) * Math.PI / 180);
      const a = v.orbit || 0, e = v.elev || 0.06;
      pos = [tgt[0] + Math.sin(a) * Math.cos(e) * dist, tgt[1] + Math.sin(e) * dist, tgt[2] + Math.cos(a) * Math.cos(e) * dist];
      target = tgt;
    } else { pos = v.pos; target = v.target; fov = v.fov || 20; }
    camera.position.set(pos[0], pos[1], pos[2]); camera.fov = fov; camera.aspect = S.w / S.h; camera.updateProjectionMatrix();
    camera.lookAt(target[0], target[1], target[2]);
  }
  let bgMode = 'set';
  function background(mode) {
    bgMode = mode;
    setGroup.visible = mode === 'set';
    if (pros) pros.group.visible = mode === 'set';
    scene.background = new THREE.Color(mode === 'set' ? '#0b0806' : mode === 'gray' ? '#8c857c' : mode);
  }
  function frame(t, state) { if (cat) cat.update(t, state || {}); renderer.render(scene, camera); }
  function grab(type, q) { return renderer.domElement.toDataURL(type === 'jpeg' ? 'image/jpeg' : 'image/png', q || 0.92); }
  function pixels() {
    const gl = renderer.getContext();
    const buf = new Uint8Array(S.w * S.h * 4);
    gl.readPixels(0, 0, S.w, S.h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    return buf;
  }
  function hash() { const b = pixels(); let h = 2166136261; for (let i = 0; i < b.length; i++) { h ^= b[i]; h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); }
  // 光敏統計：縮成 320×180，16×9 與 64×36 區域的線性相對亮度、飽和紅色值（同 tools/capture_analyze.py 的定義）
  const small = document.createElement('canvas'); small.width = 320; small.height = 180;
  const sg = small.getContext('2d', { willReadFrequently: true });
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const LUT = new Float32Array(256); for (let i = 0; i < 256; i++) LUT[i] = lin(i);
  function regionStats() {
    sg.imageSmoothingEnabled = true; sg.imageSmoothingQuality = 'high';
    sg.drawImage(renderer.domElement, 0, 0, 320, 180);
    const d = sg.getImageData(0, 0, 320, 180).data;
    const g16 = new Float64Array(144), r16 = new Float64Array(144), g64 = new Float64Array(64 * 36);
    let all = 0;
    for (let y = 0; y < 180; y++) for (let x = 0; x < 320; x++) {
      const i = (y * 320 + x) * 4, r = LUT[d[i]], g = LUT[d[i + 1]], b = LUT[d[i + 2]];
      const l = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const s = r + g + b, red = (s > 0 && r / s >= 0.8 && r > 0.05) ? Math.max(0, r - g - b) * 320 : 0;
      const a = Math.floor(y / 20) * 16 + Math.floor(x / 20);
      g16[a] += l / 400; r16[a] += red / 400; g64[Math.floor(y / 5) * 64 + Math.floor(x / 5)] += l / 25; all += l;
    }
    return { g16: Array.from(g16), r16: Array.from(r16), g64: Array.from(g64), all: all / (320 * 180) };
  }
  // 投影模擬 v2（同 tools/projsim.py）與 L*
  const LSTAR = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const Y = LUT[i]; LSTAR[i] = Y > 0.008856 ? 116 * Math.cbrt(Y) - 16 : 903.3 * Y; }
  function lstarOf(r, g, b, proj) {
    if (proj) {
      const R = r / 255, G = g / 255, B = b / 255, m = (R + G + B) / 3;
      const f = (v) => Math.round(Math.min(1, Math.max(0, 0.18 + (m + (v - m) * 0.65) * (0.87 - 0.18))) * 255);
      r = f(R); g = f(G); b = f(B);
    }
    const Y = 0.2126 * LUT[r] + 0.7152 * LUT[g] + 0.0722 * LUT[b];
    return Y > 0.008856 ? 116 * Math.cbrt(Y) - 16 : 903.3 * Y;
  }
  function contrast() {
    // 只量折折本身：關掉地面柔影與投到景片上的影子（影子另外看接觸表）
    const casters = [];
    cat.group.traverse((o) => { if (o.isMesh && o.castShadow) { casters.push(o); o.castShadow = false; } });
    cat.shadowEnabled = false; frame(cat.lastPoseT);
    const A = pixels();
    cat.group.visible = false; renderer.render(scene, camera);
    const B = pixels();
    // 精確剪影：只畫折折（純白覆寫材質、黑底），燈籠柔光精靈不算
    cat.group.visible = true;
    const hidden = [];
    for (const o of [setGroup, kidGroup, pros && pros.group]) if (o && o.visible) { hidden.push(o); o.visible = false; }
    const sprites = []; cat.group.traverse((o) => { if (o.isSprite && o.visible) { sprites.push(o); o.visible = false; } });
    const bg0 = scene.background; scene.background = new THREE.Color('#000000');
    scene.overrideMaterial = new THREE.MeshBasicMaterial({ color: '#ffffff', side: THREE.DoubleSide });
    renderer.render(scene, camera);
    const M = pixels();
    scene.overrideMaterial = null; scene.background = bg0; hidden.forEach((o) => { o.visible = true; }); sprites.forEach((o) => { o.visible = true; });
    cat.shadowEnabled = true; casters.forEach((o) => { o.castShadow = true; }); frame(cat.lastPoseT);
    const W = S.w, H = S.h, mask = new Uint8Array(W * H);
    let n = 0;
    for (let i = 0; i < W * H; i++) if (M[i * 4] > 127) { mask[i] = 1; n++; }
    const res = {};
    for (const proj of [false, true]) {
      const LA = new Float32Array(W * H), LB = new Float32Array(W * H);
      for (let i = 0; i < W * H; i++) { const o = i * 4; LA[i] = lstarOf(A[o], A[o + 1], A[o + 2], proj); LB[i] = lstarOf(B[o], B[o + 1], B[o + 2], proj); }
      const dl = []; let sa = 0, sb = 0;
      for (let i = 0; i < W * H; i++) if (mask[i]) { dl.push(Math.abs(LA[i] - LB[i])); sa += LA[i]; sb += LB[i]; }
      // 輪廓：剪影最外圈像素（暖褐外輪廓）／往內 4 px（紙面）對上往外 2 px（背景）
      const edgeO = [], edgeF = [];
      for (let y = 6; y < H - 6; y++) for (let x = 6; x < W - 6; x++) {
        const i = y * W + x; if (!mask[i]) continue;
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          if (mask[(y + dy) * W + (x + dx)]) continue;
          const out = (y + dy * 2) * W + (x + dx * 2), inn = (y - dy * 4) * W + (x - dx * 4);
          if (mask[out]) continue;
          edgeO.push(Math.abs(LA[i] - LA[out]));
          if (mask[inn]) edgeF.push(Math.abs(LA[inn] - LA[out]));
          break;
        }
      }
      dl.sort((a, b) => a - b); edgeO.sort((a, b) => a - b); edgeF.sort((a, b) => a - b);
      const q = (arr, p) => (arr.length ? arr[Math.min(arr.length - 1, Math.floor(arr.length * p))] : 0);
      const fr = (arr, v) => +(arr.filter((x) => x >= v).length / Math.max(1, arr.length)).toFixed(3);
      res[proj ? 'proj_v2' : 'original'] = {
        pixels: n, mean_abs_dL: +(dl.reduce((s, v) => s + v, 0) / Math.max(1, dl.length)).toFixed(2), median_abs_dL: +q(dl, 0.5).toFixed(2),
        frac_dL_ge10: fr(dl, 10), frac_dL_ge20: fr(dl, 20),
        mean_L_cat: +(sa / Math.max(1, n)).toFixed(1), mean_L_bg: +(sb / Math.max(1, n)).toFixed(1),
        edge_px: edgeO.length, edge_outline_median_dL: +q(edgeO, 0.5).toFixed(2), edge_outline_p25_dL: +q(edgeO, 0.25).toFixed(2), edge_outline_frac_ge15: fr(edgeO, 15),
        edge_paper_median_dL: +q(edgeF, 0.5).toFixed(2), edge_paper_p25_dL: +q(edgeF, 0.25).toFixed(2), edge_paper_frac_ge10: fr(edgeF, 10),
      };
    }
    return res;
  }
  // 接觸表：每格套事件表、時間、鏡位後畫一格，貼到 2D 畫布上加標籤
  function sheet(spec) {
    const cols = spec.cols, tw = spec.tile[0], th = spec.tile[1], pad = 6, top = spec.title ? 44 : 0;
    const items = spec.items;
    const rows = Math.ceil(items.length / cols);
    const c = document.createElement('canvas'); c.width = cols * (tw + pad) + pad; c.height = top + rows * (th + pad) + pad;
    const g = c.getContext('2d');
    g.fillStyle = '#211913'; g.fillRect(0, 0, c.width, c.height);
    if (spec.title) { g.fillStyle = '#f6ead6'; g.font = '22px "PingFang TC","Heiti TC",sans-serif'; g.fillText(spec.title, pad + 4, 30); }
    const prevSize = [S.w, S.h];
    setSize(tw, th);
    let lastKey = '';
    items.forEach((it, i) => {
      const o = Object.assign({}, spec.defaults || {}, it);
      const ck = JSON.stringify(o.cat || null);
      if (ck !== lastKey) { makeCat(o.cat || {}); lastKey = ck; }
      cat.setTrack(o.track || { start: {}, events: [] });
      background(o.bg || 'set');
      setLight(o.light !== undefined ? o.light : 1);
      kidGroup.visible = !!o.kids;
      cat.update(o.t || 0);
      view(o.view || { close: true });
      frame(o.t || 0);
      const x = pad + (i % cols) * (tw + pad), y = top + pad + Math.floor(i / cols) * (th + pad);
      g.drawImage(renderer.domElement, x, y);
      if (o.label) {
        g.font = '15px "PingFang TC","Heiti TC",sans-serif';
        const lines = String(o.label).split('\n');
        const wmax = Math.max(...lines.map((s) => g.measureText(s).width));
        g.fillStyle = 'rgba(20,14,10,0.72)'; g.fillRect(x + 4, y + th - 8 - lines.length * 19, wmax + 10, lines.length * 19 + 4);
        g.fillStyle = '#fbf3e4'; lines.forEach((s, k) => g.fillText(s, x + 9, y + th - 10 - (lines.length - 1 - k) * 19));
      }
    });
    setSize(prevSize[0], prevSize[1]);
    return c.toDataURL('image/png');
  }
  function perf(n) {
    const out = {};
    const gl = renderer.getContext();
    const px = new Uint8Array(4);
    const run = (label, fn) => {
      for (let i = 0; i < 20; i++) fn(i);
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      const ts = [];
      for (let i = 0; i < n; i++) { const a = performance.now(); fn(i); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); ts.push(performance.now() - a); }
      ts.sort((a, b) => a - b);
      out[label] = { mean_ms: +(ts.reduce((s, v) => s + v, 0) / n).toFixed(2), p95_ms: +ts[Math.floor(n * 0.95)].toFixed(2), max_ms: +ts[n - 1].toFixed(2) };
    };
    renderer.info.autoReset = false;
    cat.group.visible = false; renderer.info.reset(); renderer.render(scene, camera);
    out.scene_without = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
    cat.group.visible = true; renderer.info.reset(); frame(1.0);
    out.scene_with = { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles };
    renderer.info.autoReset = true;
    run('frame_without_cat', () => { cat.group.visible = false; renderer.render(scene, camera); });
    run('frame_with_cat', (i) => { cat.group.visible = true; frame(1 + i / 30); });
    // update 很快（headless 計時器解析度 0.1 ms），每 100 次一批計時再平均
    const batches = [];
    for (let b = 0; b < 30; b++) { const a = performance.now(); for (let i = 0; i < 100; i++) cat.update(0.5 + (b * 100 + i) / 30); batches.push((performance.now() - a) / 100); }
    batches.sort((a, b) => a - b);
    out.cat_update = { mean_ms: +(batches.reduce((s, v) => s + v, 0) / batches.length).toFixed(4), worst_batch_mean_ms: +batches[batches.length - 1].toFixed(4), note: '每批 100 次 update（含尾巴、燈籠頂點重算）的平均' };
    out.cat_triangles = cat.triangles;
    out.gpu = (() => { const e = gl.getExtension('WEBGL_debug_renderer_info'); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'unknown'; })();
    return out;
  }

  // ─── 互動預覽（直接開啟 index.html） ───
  function interactive() {
    makeCat({ position: [0.55, 1.4, -0.6], height: 1.0 });
    view({ close: true, k: 2.6 });
    const ui = document.createElement('div'); ui.id = 'ui';
    const forms = ['idle', 'card', 'plane', 'megaphone', 'magnifier', 'lantern', 'hat', 'sheet'];
    const emos = L.ZHEZHE_EMOTIONS;
    ui.innerHTML = '<div><b>折折預覽</b>（許博明老師製作《紙燈節》）</div>'
      + '<div class="row">摺紙：' + forms.map((f) => '<button data-f="' + f + '">' + f + '</button>').join('') + '</div>'
      + '<div class="row">情緒：' + emos.map((f) => '<button data-e="' + f + '">' + f + '</button>').join('') + '</div>'
      + '<div class="row">動作：<button data-a="hush">收摺訊號</button><button data-a="twitch">耳朵動</button><button data-a="walk">走路</button><button data-a="hop">跳上台口</button><button data-a="glow">燈籠亮</button><button data-a="intro">a0_c002 開場</button><button data-a="reset">重設</button></div>'
      + '<div class="row"><label><input type="checkbox" id="kids"> 兒童立牌</label><label>鏡頭 <select id="cam"><option value="close">近景</option><option value="g4_mid">g4_mid</option><option value="g4_wide">g4_wide</option><option value="spin">旋轉</option></select></label></div>'
      + '<div class="row">時間 <input type="range" id="scrub" min="0" max="20" step="0.01" value="0" style="width:200px"> <span id="tv">0.00</span> 秒 <button id="play">播放／暫停</button></div>';
    document.body.appendChild(ui);
    let t = 0, playing = true, last = performance.now(), camMode = 'close';
    const pos0 = [0.55, 1.4, -0.6];
    ui.addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.f) cat.fold(b.dataset.f, b.dataset.f === 'idle' && cat.poseAt(t).form === 'sheet' ? 3.0 : 1.3, t);
      if (b.dataset.e) cat.emote(b.dataset.e, t);
      const a = b.dataset.a;
      if (a === 'hush') cat.hush(t);
      if (a === 'twitch') cat.twitch('both', t);
      if (a === 'glow') cat.glow(cat.poseAt(t).glow > 0.5 ? 0 : 1, 1.5, t);
      if (a === 'walk') { const p = cat.poseAt(t).pos; cat.walkTo([p[0] > 0.6 ? 0.1 : 1.0, p[1], p[2]], 1.6, t); }
      if (a === 'hop') { const p = cat.poseAt(t).pos; cat.hopTo(p[1] > 0.5 ? [1.2, 0, 0.8] : pos0, 0.9, 0.8, t); }
      if (a === 'reset') { cat.reset(); t = 0; }
      if (a === 'intro') { introTrack(cat); t = 0; playing = true; }
    });
    ui.querySelector('#play').onclick = () => { playing = !playing; };
    ui.querySelector('#scrub').oninput = (e) => { t = Number(e.target.value); playing = false; };
    ui.querySelector('#kids').onchange = (e) => { kidGroup.visible = e.target.checked; };
    ui.querySelector('#cam').onchange = (e) => { camMode = e.target.value; };
    addEventListener('resize', () => setSize(innerWidth, innerHeight));
    const loop = (now) => {
      if (playing) t += (now - last) / 1000;
      last = now;
      ui.querySelector('#tv').textContent = t.toFixed(2);
      if (playing) ui.querySelector('#scrub').value = String(Math.min(20, t));
      if (camMode === 'spin') view({ close: true, k: 2.2, orbit: t * 0.6, elev: 0.15 });
      else if (camMode === 'close') view({ close: true, k: 2.6 });
      else view(camMode);
      frame(t);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  /** a0_c002 開場：紙平躺 → 立起 → 摺、摺、摺 → 耳朵啪地立起 → 「喵！大家好，我是折折。」→「我是燈籠紙摺成的貓……」 */
  function introTrack(c, o) {
    o = o || {};
    const L1 = o.l1 !== undefined ? o.l1 : 4.7, L2 = o.l2 !== undefined ? o.l2 : 7.75;
    c.reset({ form: 'sheet', rise: 0, emotion: 'neutral' });
    c.rise(1.0, 0.3);
    c.fold('idle', 3.0, 1.4);
    c.twitch('both', 1.4 + 3.0 * 0.97);
    c.emote('happy', L1 - 0.1);
    if (D.lips.a0_c002_01) c.say(D.lips.a0_c002_01, L1);
    c.emote('neutral', L1 + 0.95);
    c.emote('proud', L1 + 1.75);
    c.emote('neutral', L2 - 0.15);
    if (D.lips.a0_c002_02) c.say(D.lips.a0_c002_02, L2);
    c.look(-0.4, 0.5, L2 + 2.1);
    c.twitch('l', L2 + 2.2);
    c.look(0, 0.6, L2 + 3.7);
    c.emote('happy', L2 + 3.8);
    return { l1: L1, l2: L2, end: L2 + 5.6 };
  }

  window.__zz = {
    ready: false, THREE, renderer, scene, camera, setSize, view, setLight, background, makeCat, frame, grab, hash, regionStats, contrast, sheet, perf,
    introTrack, trackFromTimeline: L.zhezheTrackFromTimeline, seedFor: L.zhezheSeed, get cat() { return cat; }, showKids: (on) => { kidGroup.visible = on; }, beats: { fold: L.FOLD_BEATS, hush: L.HUSH_BEATS },
  };
  loadImages().then(() => {
    buildScene();
    setLight(1);
    if (auto) { makeCat({}); view({ close: true }); frame(0); window.__zz.ready = true; }
    else interactive();
  });
}

// ─────────────────────────────────────────── 3. 擷取與量測 ───────────────────────────────────────────
const TABLE = [0.55, 1.4, -0.6];   // G4 工作台右段桌面（燈籠骨架右邊的空位）
const FLOOR = [0.8, 0, 0.75];      // 工作台前的地板
const APRON = [-4.7, 0, 3.4];      // 台口前緣（題卡模式），高 1.5
const FORMS = ['card', 'plane', 'megaphone', 'magnifier', 'lantern', 'hat'];
const EMOS = ['neutral', 'happy', 'curious', 'worried', 'proud', 'sad'];
const EMO_ZH = { neutral: '平靜', happy: '開心', curious: '好奇', worried: '擔心', proud: '得意', sad: '失落' };
const FORM_ZH = { idle: '貓', card: '題卡', plane: '紙飛機', megaphone: '傳聲筒', magnifier: '放大鏡', lantern: '燈籠', hat: '帽子', sheet: '燈籠紙' };
const lips01 = existsSync(join(ROOT, 'audio/lipsync/a0_c002_01_v04.json')) ? JSON.parse(readFileSync(join(ROOT, 'audio/lipsync/a0_c002_01_v04.json'), 'utf8')) : null;
const summary = {};
const files = [];

function saveDataUrl(rel, dataUrl) {
  const f = join(OUT, rel);
  mkdirSync(dirname(f), { recursive: true });
  writeFileSync(f, Buffer.from(dataUrl.replace(/^data:[^,]+,/, ''), 'base64'));
  files.push(rel);
  return f;
}

/** 摺紙變形的事件表：idle →（0.4 s）form →（停 0.9 s）→ idle */
const foldTrack = (form, dur = 1.3) => ({ start: { form: 'idle', emotion: 'neutral' }, events: [
  { type: 'fold', t: 0.4, form, dur }, { type: 'fold', t: 0.4 + dur + 0.9, form: 'idle', dur },
  ...(form === 'lantern' ? [{ type: 'glow', t: 0.4 + dur, to: 1, dur: 0.9 }] : []),
] });

async function main() {
  if (only.has('build')) await buildPreview();
  const need = [...only].some((k) => k !== 'build');
  if (!need) return;
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars', '--use-angle=metal'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`[console] ${m.text()}`); });
  await page.goto(`${pathToFileURL(join(OUT, 'preview/index.html')).href}?auto=1`);
  await page.waitForFunction(() => window.__zz && window.__zz.ready, null, { timeout: 60000 });
  const sheet = async (rel, spec) => { const url = await page.evaluate((s) => window.__zz.sheet(s), spec); saveDataUrl(rel, url); log(rel); };

  // ── 快速看圖（製作時自查用；同時放進驗收包）
  if (only.has('look')) {
    await sheet('look.png', { cols: 3, tile: [640, 640], title: '折折：桌上近景、地板、題卡台口（投影前原圖）', items: [
      { cat: { position: TABLE }, t: 1.0, view: { close: true, k: 1.9 }, label: '工作台上（平靜）' },
      { cat: { position: TABLE }, t: 1.0, track: { start: { emotion: 'happy' }, events: [] }, view: { close: true, k: 1.9, orbit: 0.6 }, label: '開心、四分之三側' },
      { cat: { position: FLOOR }, t: 1.0, track: { start: { emotion: 'curious' }, events: [] }, view: { close: true, k: 1.9 }, label: '地板（好奇）' },
      { cat: { position: TABLE }, t: 2.0, track: foldTrack('card'), view: { close: true, k: 2.6 }, label: '題卡' },
      { cat: { position: TABLE }, t: 2.0, track: foldTrack('lantern'), view: { close: true, k: 1.9 }, label: '燈籠（亮）' },
      { cat: { position: APRON, height: 1.5 }, t: 1.0, light: 0.55, view: 'quiz', label: '題卡模式全景（quiz 鏡位、燈 0.55）' },
    ] });
  }

  // ── 狀態接觸表：情緒 × 嘴型／眨眼
  if (only.has('states')) {
    const items = [];
    for (const e of EMOS) {
      const st = { start: { emotion: e }, events: [] };
      items.push({ track: st, t: 0.5, label: `${EMO_ZH[e]}｜不說話` });
      for (const m of [1, 2, 3]) items.push({ track: { start: { emotion: e }, events: [{ type: 'say', t: 0, lips: { fps: 12, frames: Array(40).fill(m) } }] }, t: 0.5, label: `${EMO_ZH[e]}｜嘴 ${m}` });
      items.push({ track: { start: { emotion: e }, events: [{ type: 'blink', t: 0.45 }] }, t: 0.5, label: `${EMO_ZH[e]}｜眨眼` });
      items.push({ track: st, t: 0.5, view: { close: true, orbit: 0.75 }, label: `${EMO_ZH[e]}｜側 0.75 rad` });
    }
    await sheet('contact_states.png', { cols: 6, tile: [300, 300], title: '折折狀態：情緒（耳朵、尾巴、眼睛）× 嘴型 0–3（12 fps 對嘴值）× 眨眼', defaults: { cat: { position: TABLE } }, items });
  }

  // ── 摺紙變形逐格（固定取樣：每個變形 dur 內等距 12 格＋落定後 1 格）
  if (only.has('folds')) {
    for (const f of FORMS) {
      const dur = 1.3, items = [];
      const k = f === 'card' ? 2.7 : f === 'megaphone' || f === 'plane' ? 2.3 : 2.0;
      for (let i = 0; i <= 12; i++) { const t = 0.4 + (dur * i) / 12; items.push({ track: foldTrack(f), t, view: { close: true, k, dy: 0.55 }, label: `貓→${FORM_ZH[f]} ${(t - 0.4).toFixed(2)}s` }); }
      for (let i = 0; i <= 12; i++) { const t = 0.4 + dur + 0.9 + (dur * i) / 12; items.push({ track: foldTrack(f), t, view: { close: true, k, dy: 0.55 }, label: `${FORM_ZH[f]}→貓 ${(t - 2.6).toFixed(2)}s` }); }
      await sheet(`folds/fold_${f}.png`, { cols: 13, tile: [220, 220], title: `摺紙變形：貓 ↔ ${FORM_ZH[f]}（dur 1.3 s；第 0.45×dur 紙包縮到最小時硬切換造型）`, defaults: { cat: { position: TABLE } }, items });
    }
    // 開場：燈籠紙 → 貓（摺、摺、摺）
    const items = [];
    for (let i = 0; i <= 25; i++) { const t = 0.2 + i * 0.18; items.push({ track: { start: { form: 'sheet', rise: 0 }, events: [{ type: 'rise', t: 0.3, dur: 1.0 }, { type: 'fold', t: 1.4, form: 'idle', dur: 3.0 }, { type: 'twitch', t: 1.4 + 2.91 }] }, t, view: { close: true, k: 2.2, dy: 0.5, elev: 0.12 }, label: `${t.toFixed(2)}s` }); }
    await sheet('folds/fold_sheet_intro.png', { cols: 13, tile: [220, 220], title: 'a0_c002 登場：燈籠紙立起（0.3–1.3 s）→ 摺、摺、摺（落點 1.90／2.52／3.13 s）→ 紙包最小時換成貓（3.44 s）→ 耳朵立起（4.31 s）', defaults: { cat: { position: TABLE } }, items });
  }

  // ── 動作：收摺訊號、耳朵動一下、走路、跳上台口、摺錯
  if (only.has('actions')) {
    const row = (label, track, times, view, cat) => times.map((t) => ({ track, t, view, cat, label: `${label} ${t.toFixed(2)}s` }));
    const hush = { start: { emotion: 'neutral' }, events: [{ type: 'hush', t: 0.3 }] };
    const tw = { start: { emotion: 'neutral' }, events: [{ type: 'twitch', t: 0.3, ear: 'l' }] };
    const walk = { start: { emotion: 'happy', pos: [-0.2, 1.4, -0.6] }, events: [{ type: 'move', t: 0.2, dur: 1.6, to: [0.9, 1.4, -0.6], style: 'walk' }] };
    const hop = { start: { emotion: 'happy', pos: [0.55, 1.4, -0.6] }, events: [{ type: 'move', t: 0.2, dur: 0.9, to: [1.2, 0, 0.8], style: 'hop', height: 0.7 }] };
    const fumble = { start: { emotion: 'curious' }, events: [{ type: 'fold', t: 0.2, form: 'hat', dur: 1.3, fumble: true }, { type: 'emotion', t: 1.6, emotion: 'happy' }] };
    const emo = { start: { emotion: 'neutral' }, events: [{ type: 'emotion', t: 0.3, emotion: 'worried' }, { type: 'emotion', t: 1.5, emotion: 'sad' }, { type: 'emotion', t: 2.7, emotion: 'proud' }] };
    const items = [
      ...row('收摺訊號', hush, [0.3, 0.45, 0.6, 0.75, 0.85, 1.0, 1.2, 1.5, 1.8, 2.1], { close: true, k: 2.0 }),
      ...row('耳朵動一下', tw, [0.3, 0.36, 0.42, 0.48, 0.56, 0.66, 0.8, 1.0, 1.2, 1.5], { close: true, k: 1.6, dy: 0.65 }),
      ...row('走路', walk, [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0], { pos: [0.35, 2.1, 8.5], target: [0.35, 1.85, -0.6], fov: 20 }),
      ...row('跳下工作台', hop, [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.3], { pos: [0.85, 1.5, 11], target: [0.85, 1.1, 0], fov: 20 }),
      ...row('摺錯（想摺放大鏡→帽子）', fumble, [0.3, 0.5, 0.75, 0.95, 1.15, 1.5, 1.6, 1.75, 1.9, 2.3], { close: true, k: 2.0 }),
      ...row('情緒轉換', emo, [0.3, 0.5, 0.8, 1.5, 1.7, 2.0, 2.7, 2.9, 3.2, 3.8], { close: true, k: 2.0 }),
    ];
    await sheet('contact_actions.png', { cols: 10, tile: [240, 240], title: '動作：收摺收聲訊號（S3 落點 0.55 s）、耳朵動一下、小跳步走路、跳下工作台、摺錯、情緒彈簧過渡', defaults: { cat: { position: TABLE } }, items });
  }

  // ── 旋轉掃描（破面、穿模）：每種造型完全攤開，12 個方位 × 兩個仰角，中性灰底
  if (only.has('spin')) {
    for (const f of ['idle', ...FORMS, 'sheet']) {
      const items = [];
      const track = f === 'idle' ? { start: { form: 'idle', emotion: 'neutral' }, events: [] } : { start: { form: f, emotion: 'neutral' }, events: [] };
      const k = f === 'card' ? 2.6 : f === 'megaphone' || f === 'plane' ? 2.2 : 1.8;
      for (const elev of [0.06, 0.5]) for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2;
        items.push({ track, t: 0.6, bg: 'gray', view: { close: true, k, orbit: a, elev, dy: 0.5 }, label: `${Math.round((a * 180) / Math.PI)}°／仰 ${Math.round((elev * 180) / Math.PI)}°` });
      }
      await sheet(`spin/spin_${f}.png`, { cols: 12, tile: [200, 200], title: `旋轉掃描：${FORM_ZH[f]}（檢查破面、穿模；外輪廓、紙厚、正反兩色）`, defaults: { cat: { position: [0, 0, 0] } }, items });
    }
  }

  // ── 和剪紙人物並排（摺 vs 剪）＋ G4 中景整格
  if (only.has('compare')) {
    await page.evaluate(() => { const z = window.__zz; z.setSize(1920, 1080); z.makeCat({ position: [0.55, 1.4, -0.6], height: 1.0 }); z.background('set'); z.setLight(1); z.showKids(true); z.cat.setTrack({ start: { emotion: 'happy' }, events: [] }); z.view('g4_mid'); z.frame(1.0); });
    saveDataUrl('compare_g4_mid_with_kids.png', await page.evaluate(() => window.__zz.grab('png')));
    await page.evaluate(() => { const z = window.__zz; z.view({ pos: [1.25, 2.0, 7.2], target: [1.25, 1.55, 0], fov: 20 }); z.frame(1.0); });
    saveDataUrl('compare_fold_vs_cut_close.png', await page.evaluate(() => window.__zz.grab('png')));
    await page.evaluate(() => { const z = window.__zz; z.makeCat({ position: [-4.7, 0, 3.4], height: 1.5 }); z.showKids(true); z.setLight(0.55); z.cat.setTrack({ start: { form: 'card' }, events: [] }); z.view('quiz'); z.frame(1.0); });
    saveDataUrl('compare_quiz_card.png', await page.evaluate(() => window.__zz.grab('png')));
    await page.evaluate(() => { window.__zz.showKids(false); window.__zz.setLight(1); });
    log('compare');
  }

  // ── 光敏：每種變形與動作 30 格／秒，16×9（專案標準）與 64×36（細格）區域、整個畫面；兩種鏡位
  if (only.has('flash')) {
    const seqs = {
      ...Object.fromEntries(FORMS.map((f) => [`fold_${f}`, { track: foldTrack(f), end: 4.4 }])),
      fold_sheet_intro: { track: { start: { form: 'sheet', rise: 0 }, events: [{ type: 'rise', t: 0.3, dur: 1.0 }, { type: 'fold', t: 1.4, form: 'idle', dur: 3.0 }] }, end: 5.0 },
      fumble_hat: { track: { start: { emotion: 'curious' }, events: [{ type: 'fold', t: 0.2, form: 'hat', dur: 1.3, fumble: true }] }, end: 3.0 },
      hush: { track: { start: {}, events: [{ type: 'hush', t: 0.3 }] }, end: 2.5 },
      lantern_glow: { track: { start: { form: 'lantern' }, events: [{ type: 'glow', t: 0.3, to: 1, dur: 1.5 }, { type: 'glow', t: 2.5, to: 0, dur: 1.5 }] }, end: 4.5 },
      walk: { track: { start: { emotion: 'happy', pos: [-0.2, 1.4, -0.6] }, events: [{ type: 'move', t: 0.2, dur: 2.4, to: [1.0, 1.4, -0.6], style: 'walk' }] }, end: 3.0 },
      hop: { track: { start: { emotion: 'happy' }, events: [{ type: 'move', t: 0.2, dur: 0.9, to: [1.2, 0, 0.8], style: 'hop', height: 0.7 }] }, end: 2.0 },
      ...Object.fromEntries(['card', 'plane', 'megaphone', 'magnifier'].map((f) => [`fold_${f}_dur1.8`, { track: foldTrack(f, 1.8), end: 5.6 }])),
      'hop_dur1.3': { track: { start: { emotion: 'happy' }, events: [{ type: 'move', t: 0.2, dur: 1.3, to: [1.2, 0, 0.8], style: 'hop', height: 0.7 }] }, end: 2.4 },
      talk_wag_happy: { track: { start: { emotion: 'happy' }, events: [...(lips01 ? [{ type: 'say', t: 0.2, lips: lips01 }] : [])] }, end: 3.0 },
    };
    const seqRe = opt('--seq', '') ? new RegExp(opt('--seq', '')) : null;
    if (seqRe) for (const k of Object.keys(seqs)) if (!seqRe.test(k)) delete seqs[k];
    const views = { g4_mid: 'g4_mid', medium: { close: true, k: 3.3, dy: 0.55 }, close: { close: true, k: 1.6, dy: 0.55 } };
    const report = {};
    for (const [name, sq] of Object.entries(seqs)) {
      report[name] = {};
      for (const [vn, v] of Object.entries(views)) {
        const series = await page.evaluate(({ sq, v }) => {
          const z = window.__zz; z.setSize(1920, 1080); z.makeCat({ position: sq.track.start.pos || [0.55, 1.4, -0.6], height: 1.0 }); z.background('set'); z.setLight(1); z.showKids(false);
          z.cat.setTrack(sq.track);
          if (v.close) z.cat.update(0);
          z.view(v);
          const out = [];
          for (let i = 0; i <= Math.round(sq.end * 30); i++) { const t = i / 30; z.frame(t); out.push(z.regionStats()); }
          return out;
        }, { sq, v });
        report[name][vn] = analyzeFlash(series, 30);
      }
    }
    const worst = Object.values(report).flatMap((r) => Object.values(r)).reduce((m, r) => Math.max(m, r.max_per_sec_16x9, r.max_per_sec_64x36, r.red_max_per_sec, r.global_max_per_sec), 0);
    const maxOf = (views, key) => Object.entries(report).filter(([k]) => !k.includes('_dur')).reduce((m, [, r]) => Math.max(m, ...views.map((v) => r[v][key])), 0);
    const verdict = {
      standard_16x9_stage_framings: maxOf(['g4_mid', 'medium'], 'max_per_sec_16x9'),
      red_all: maxOf(['g4_mid', 'medium', 'close'], 'red_max_per_sec'),
      global_all: maxOf(['g4_mid', 'medium', 'close'], 'global_max_per_sec'),
      stress_close_16x9: maxOf(['close'], 'max_per_sec_16x9'),
      fine_64x36_stage_framings: maxOf(['g4_mid', 'medium'], 'max_per_sec_64x36'),
      framings: 'g4_mid＝G4 代表鏡頭中景（折折高約 180 px）；medium＝a0_c002 慢推的工作台中景（約 330 px）；close＝壓力測試特寫（約 675 px，折折超過畫面一半高）',
    };
    if (seqRe) { writeFileSync(join(tmpdir(), 'zhezhe_flash_diag.json'), JSON.stringify(report)); for (const [k, r] of Object.entries(report)) console.log(k.padEnd(22), Object.entries(r).map(([vn, x]) => `${vn}: ${x.max_per_sec_16x9}/${x.max_per_sec_64x36}`).join('  ')); return void (await browser.close()); }
    writeFileSync(join(OUT, 'flash.json'), JSON.stringify({ method: '每格縮成 320×180；16×9 區域（專案標準，同 tools/capture_analyze.py）＋64×36 細格（約 30×30 px@1080p）＋整個畫面；線性相對亮度從上一個極值變化 ≥0.10 且暗端 <0.80 記一次；飽和紅 R/(R+G+B)≥0.8 以 (R−G−B)×320 變化 ≥20 記一次；30 格／秒', limit_per_sec: 3, verdict, worst_any_grid_any_framing: worst, sequences: report }, null, 1));
    files.push('flash.json');
    summary.flash = { verdict, per_sequence: Object.fromEntries(Object.entries(report).map(([k, r]) => [k, Object.fromEntries(Object.entries(r).map(([vn, x]) => [vn, `${x.max_per_sec_16x9}/${x.max_per_sec_64x36}/${x.red_max_per_sec}`]))])) };
    log('flash worst', worst);
  }

  // ── 投影模擬後與背景的明度差
  if (only.has('contrast')) {
    const cases = [
      { name: 'table_g4_mid', cat: { position: TABLE }, view: 'g4_mid', track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'table_g4_mid_no_outline', cat: { position: TABLE, outline: false }, view: 'g4_mid', track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'floor_g4_mid', cat: { position: FLOOR }, view: 'g4_mid', track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'table_g4_wide', cat: { position: TABLE }, view: 'g4_wide', track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'table_close', cat: { position: TABLE }, view: { close: true, k: 1.9 }, track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'apron_quiz_light055', cat: { position: APRON, height: 1.5 }, view: 'quiz', light: 0.55, track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'apron_quiz_light055_presence020', cat: { position: APRON, height: 1.5, presence: 0.2 }, view: 'quiz', light: 0.55, track: { start: { emotion: 'neutral' }, events: [] } },
      { name: 'apron_quiz_card', cat: { position: APRON, height: 1.5 }, view: 'quiz', light: 0.55, track: { start: { form: 'card' }, events: [] } },
      { name: 'apron_quiz_card_presence020', cat: { position: APRON, height: 1.5, presence: 0.2 }, view: 'quiz', light: 0.55, track: { start: { form: 'card' }, events: [] } },
      { name: 'table_lantern_lit', cat: { position: TABLE }, view: 'g4_mid', track: { start: { form: 'lantern', glow: 1 }, events: [] } },
    ];
    const out = {};
    const crops = [];
    for (const c of cases) {
      out[c.name] = await page.evaluate((c) => {
        const z = window.__zz; z.setSize(1920, 1080); z.makeCat(c.cat); z.background('set'); z.setLight(c.light ?? 1); z.showKids(false);
        z.cat.setTrack(c.track); z.cat.update(1.0); z.view(c.view); z.frame(1.0);
        return z.contrast();
      }, c);
      crops.push(c);
    }
    writeFileSync(join(OUT, 'contrast.json'), JSON.stringify({ method: '同一格畫兩次（有／沒有折折；地面柔影與投到景片的影子都關掉，只量折折本身）；折折剪影用純白覆寫材質單獨畫出（精確遮罩）；mean_abs_dL＝剪影內每個像素和同位置背景的 L* 差平均；edge_outline＝剪影最外圈（暖褐外輪廓）與外側 2 px 背景的 L* 差；edge_paper＝往內 4 px 的紙面與外側 2 px 背景的 L* 差；proj_v2＝tools/projsim.py 的投影模擬 v2（彩度×0.65、黑位 0.18、白位 0.87）', cases: out }, null, 1));
    files.push('contrast.json');
    summary.contrast = Object.fromEntries(Object.entries(out).map(([k, v]) => [k, { mean_abs_dL_proj: v.proj_v2.mean_abs_dL, edge_outline_median_proj: v.proj_v2.edge_outline_median_dL, edge_paper_median_proj: v.proj_v2.edge_paper_median_dL, frac_ge10_proj: v.proj_v2.frac_dL_ge10, L_cat: v.proj_v2.mean_L_cat, L_bg: v.proj_v2.mean_L_bg }]));
    // 原圖／投影模擬並排（在頁面內套 v2）
    const url = await page.evaluate((cases) => {
      const z = window.__zz, T = 360, cols = cases.length;
      const c = document.createElement('canvas'); c.width = cols * (T + 6) + 6; c.height = 2 * (T + 6) + 50;
      const g = c.getContext('2d'); g.fillStyle = '#211913'; g.fillRect(0, 0, c.width, c.height);
      g.fillStyle = '#f6ead6'; g.font = '20px "PingFang TC",sans-serif'; g.fillText('上：原圖　下：投影模擬 v2（以折折為中心裁切 360×360）', 10, 30);
      cases.forEach((cs, i) => {
        z.setSize(1920, 1080); z.makeCat(cs.cat); z.background('set'); z.setLight(cs.light ?? 1);
        z.cat.setTrack(cs.track); z.cat.update(1.0); z.view(cs.view); z.frame(1.0);
        const p = cs.cat.position, h = cs.cat.height || 1;
        const v = new z.THREE.Vector3(p[0], p[1] + 0.5 * h, p[2]).project(z.camera);
        const cx = (v.x + 1) / 2 * 1920, cy = (1 - v.y) / 2 * 1080;
        const tmp = document.createElement('canvas'); tmp.width = T; tmp.height = T;
        const tg = tmp.getContext('2d'); tg.drawImage(z.renderer.domElement, cx - T / 2, cy - T / 2, T, T, 0, 0, T, T);
        g.drawImage(tmp, 6 + i * (T + 6), 44);
        const d = tg.getImageData(0, 0, T, T);
        for (let k = 0; k < d.data.length; k += 4) {
          const R = d.data[k] / 255, G = d.data[k + 1] / 255, B = d.data[k + 2] / 255, m = (R + G + B) / 3;
          for (const [o, v0] of [[0, R], [1, G], [2, B]]) d.data[k + o] = Math.round(Math.min(1, Math.max(0, 0.18 + (m + (v0 - m) * 0.65) * 0.69)) * 255);
        }
        tg.putImageData(d, 0, 0);
        g.drawImage(tmp, 6 + i * (T + 6), 50 + T + 6);
        g.fillStyle = 'rgba(20,14,10,.75)'; g.fillRect(6 + i * (T + 6), 44, 230, 24); g.fillStyle = '#fbf3e4'; g.font = '14px sans-serif'; g.fillText(cs.name, 12 + i * (T + 6), 61);
      });
      return c.toDataURL('image/png');
    }, crops);
    saveDataUrl('contrast_proj_sheet.png', url);
    log('contrast');
  }

  // ── 效能
  if (only.has('perf')) {
    const p = await page.evaluate(() => { const z = window.__zz; z.setSize(1920, 1080); z.makeCat({ position: [0.55, 1.4, -0.6], height: 1.0 }); z.background('set'); z.setLight(1); z.showKids(true); z.cat.setTrack({ start: { emotion: 'happy' }, events: [] }); z.view('g4_mid'); return z.perf(240); });
    const forms = await page.evaluate(() => { const z = window.__zz; const r = {}; for (const f of ['idle', 'card', 'plane', 'megaphone', 'magnifier', 'lantern', 'hat', 'sheet']) { z.cat.setTrack({ start: { form: f }, events: [] }); z.renderer.info.autoReset = false; z.renderer.info.reset(); z.frame(1); const a = z.renderer.info.render.triangles; z.cat.group.visible = false; z.renderer.info.reset(); z.renderer.render(z.scene, z.camera); const b = z.renderer.info.render.triangles; z.cat.group.visible = true; z.renderer.info.autoReset = true; r[f] = a - b; } return r; });
    p.visible_triangles_by_form = forms;
    p.note = '本機（Apple M4、Chrome headless、1920×1080、MSAA）量測；學校 Windows 內顯筆電需實機確認';
    writeFileSync(join(OUT, 'perf.json'), JSON.stringify(p, null, 1));
    files.push('perf.json');
    summary.perf = p;
    log('perf', JSON.stringify(p));
  }

  // ── 確定性：同一秒以不同順序重建（逐格前進、跳回、上一步、新建實例）要得到一樣的像素
  if (only.has('determinism')) {
    const res = await page.evaluate((lips) => {
      const z = window.__zz; z.setSize(960, 540); z.background('set'); z.setLight(1); z.showKids(false);
      const mk = () => { z.makeCat({ position: [0.55, 1.4, -0.6], height: 1.0, seed: 3 }); const c = z.cat;
        c.reset({ form: 'sheet', rise: 0 }); c.rise(1, 0.2); c.fold('idle', 3.0, 1.2); c.emote('curious', 4.4); if (lips) c.say(lips, 4.6); c.hush(7.6); c.fold('lantern', 1.3, 9.4); c.glow(1, 1.5, 10.8); c.fold('idle', 1.3, 12.5);
        c.walkTo([1.0, 1.4, -0.6], 1.5, 14.0); c.hopTo([1.3, 0, 0.8], 0.9, 0.7, 15.8); return c; };
      mk(); z.view({ close: true, k: 3.0 });
      const T = [2.05, 3.5, 5.3, 8.1, 10.0, 11.7, 13.1, 14.6, 16.2];
      const direct = T.map((t) => { z.frame(t); return z.hash(); });
      const stepped = []; let k = 0;
      for (let i = 0; i <= 17 * 30; i++) { const t = i / 30; z.frame(t); if (k < T.length && Math.abs(t - T[k]) < 1 / 60) { z.frame(T[k]); stepped.push(z.hash()); k++; } }
      const back = [...T].reverse().map((t) => { z.frame(t + 0.7); z.frame(t); return z.hash(); }).reverse();
      mk(); z.view({ close: true, k: 3.0 });
      const fresh = T.map((t) => { z.frame(t); return z.hash(); });
      const q = T.map((t) => { z.frame(t + 0.003); return z.hash(); });
      return { times: T, direct, stepped, back, fresh, quantized: q, pass: T.every((_, i) => direct[i] === stepped[i] && direct[i] === back[i] && direct[i] === fresh[i] && direct[i] === q[i]) };
    }, lips01);
    // cue 時間軸轉事件表（主線接線用的 zhezheTrackFromTimeline）
    res.converter = await page.evaluate((lips) => {
      const z = window.__zz;
      const tl = { anims: [
        { name: 'zhezhe.fold', target: 'zhezhe', start: 1.0, duration: 1.3, params: { form: 'card' } },
        { name: 'zhezhe.emote', target: 'zhezhe', start: 0.2, duration: 0, params: { emotion: 'happy' } },
        { name: 'zhezhe.walk', target: 'zhezhe', start: 3.0, duration: 1.5, params: { dx: 0.5 } },
        { name: 'zhezhe.hop', target: 'zhezhe', start: 5.0, duration: 0.9, params: { to: [1.2, 0, 0.8], height: 0.7 } },
        { name: 'zhezhe.hush', target: 'zhezhe', start: 6.5, duration: 0, params: {} },
        { name: 'zhezhe.fold', target: 'zhezhe', start: 2.4, duration: 0, params: { form: 'not-a-form' } },
        { name: 'puppet.wave', target: 'ale', start: 1.0, duration: 1, params: {} },
      ], lines: [{ line: { id: 'a0_c002_01' }, actorId: 'zhezhe', start: 0.5 }, { line: { id: 'x' }, actorId: 'ale', start: 1 }] };
      const tr = z.trackFromTimeline(tl, { pos: [0.55, 1.4, -0.6], seed: z.seedFor('a1_c005') }, (id) => (id === 'a0_c002_01' ? lips : undefined));
      const types = tr.events.map((e) => e.type).sort().join(',');
      const walk = tr.events.find((e) => e.type === 'move' && e.style === 'walk');
      return { types, walkTo: walk ? walk.to : null, pass: types === 'emotion,fold,hush,move,move,say' && !!walk && Math.abs(walk.to[0] - 1.05) < 1e-9 };
    }, lips01);
    res.pass = res.pass && res.converter.pass;
    writeFileSync(join(OUT, 'determinism.json'), JSON.stringify({ method: '同一組事件表，在 9 個時間點比較整格像素雜湊：直接跳到、從 0 每 1/30 秒逐格前進、從 t+0.7 退回（上一步）、重新建立實例、t+0.003 秒（量化到 1/120 秒的同一步）', ...res }, null, 1));
    files.push('determinism.json');
    summary.determinism = res.pass;
    log('determinism', res.pass);
  }

  // ── a0_c002 開場自我介紹預覽影片（30 fps，配 vo_a0_c002_01／02）
  if (only.has('video')) {
    const fdir = join(tmpdir(), `zhezhe_frames_${process.pid}`);
    rmSync(fdir, { recursive: true, force: true }); mkdirSync(fdir, { recursive: true });
    const info = await page.evaluate(() => { const z = window.__zz; z.setSize(1920, 1080); z.makeCat({ position: [0.55, 1.4, -0.6], height: 1.0, seed: 21 }); z.background('set'); z.setLight(1); z.showKids(false); return z.introTrack(z.cat); });
    const N = Math.round(info.end * 30);
    const vstats = [];
    for (let i = 0; i < N; i += 15) {
      const res = await page.evaluate(({ i0, n, end }) => {
        const z = window.__zz, out = [], st = [];
        for (let i = i0; i < i0 + n; i++) {
          const t = i / 30, u = Math.min(1, t / end), e = 0.5 - 0.5 * Math.cos(Math.PI * u);
          // 慢推：工作台中景（折折約占畫面 34%）→ 稍近（約 42%），正弦緩動、不晃
          const d = 8.8 - 1.7 * e;
          z.view({ pos: [0.55, 1.42 + 0.065 * d, -0.6 + d], target: [0.55, 1.9, -0.6], fov: 20 });
          z.frame(t); out.push(z.grab('jpeg', 0.93)); st.push(z.regionStats());
        }
        return { out, st };
      }, { i0: i, n: Math.min(15, N - i), end: info.end });
      res.out.forEach((u, k) => writeFileSync(join(fdir, `${String(i + k).padStart(5, '0')}.jpg`), Buffer.from(u.replace(/^data:[^,]+,/, ''), 'base64')));
      vstats.push(...res.st);
    }
    const vflash = analyzeFlash(vstats, 30);
    delete vflash.worst_64x36;
    log('video flash', JSON.stringify({ s16: vflash.max_per_sec_16x9, s64: vflash.max_per_sec_64x36, red: vflash.red_max_per_sec }));
    const vo1 = join(ROOT, 'audio/vo/vo_a0_c002_01_v04.wav'), vo2 = join(ROOT, 'audio/vo/vo_a0_c002_02_v04.wav');
    const out = join(OUT, 'a0_c002_intro_preview.mp4');
    const d1 = Math.round(info.l1 * 1000), d2 = Math.round(info.l2 * 1000);
    const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', '30', '-i', join(fdir, '%05d.jpg'), '-i', vo1, '-i', vo2,
      '-filter_complex', `[1:a]adelay=${d1}|${d1}[a1];[2:a]adelay=${d2}|${d2}[a2];[a1][a2]amix=inputs=2:normalize=0,apad[a]`,
      '-map', '0:v', '-map', '[a]', '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '160k', out], { encoding: 'utf8' });
    if (r.status !== 0) log('ffmpeg 失敗', r.stderr);
    else { files.push('a0_c002_intro_preview.mp4'); log('video', out); }
    // 影片逐格接觸表（每 0.5 秒一格）
    const pick = [];
    for (let i = 0; i < N; i += 15) pick.push(join(fdir, `${String(i).padStart(5, '0')}.jpg`));
    const tiles = pick.map((f) => `data:image/jpeg;base64,${readFileSync(f).toString('base64')}`);
    const url = await page.evaluate(async ({ tiles, l1, l2 }) => {
      const cols = 6, tw = 384, th = 216, pad = 6;
      const c = document.createElement('canvas'); c.width = cols * (tw + pad) + pad; c.height = 50 + Math.ceil(tiles.length / cols) * (th + pad) + pad;
      const g = c.getContext('2d'); g.fillStyle = '#211913'; g.fillRect(0, 0, c.width, c.height);
      g.fillStyle = '#f6ead6'; g.font = '20px "PingFang TC",sans-serif'; g.fillText(`a0_c002 開場預覽：每 0.5 秒一格（_01 句從 ${l1.toFixed(2)} s、_02 句從 ${l2.toFixed(2)} s）`, 10, 32);
      for (let i = 0; i < tiles.length; i++) {
        const im = new Image(); im.src = tiles[i]; await im.decode();
        const x = pad + (i % cols) * (tw + pad), y = 44 + Math.floor(i / cols) * (th + pad);
        g.drawImage(im, x, y, tw, th);
        g.fillStyle = 'rgba(20,14,10,.75)'; g.fillRect(x + 4, y + th - 26, 64, 22); g.fillStyle = '#fbf3e4'; g.font = '14px sans-serif'; g.fillText(`${(i * 0.5).toFixed(1)}s`, x + 10, y + th - 10);
      }
      return c.toDataURL('image/jpeg', 0.9);
    }, { tiles, l1: info.l1, l2: info.l2 });
    saveDataUrl('a0_c002_intro_contact.jpg', url);
    rmSync(fdir, { recursive: true, force: true });
    summary.video = { seconds: +(N / 30).toFixed(2), lines: { a0_c002_01: info.l1, a0_c002_02: info.l2 }, flash_on_video_frames: vflash };
  }

  summary.errors = errors;
  await browser.close();
  writeIndex();
  log('完成', errors.length ? `頁面錯誤 ${errors.length} 則` : '');
  if (errors.length) console.log(errors.join('\n'));
}

/** 光敏分析（同 tools/capture_analyze.py 的轉折定義） */
function transitions(series, th, dark) {
  const ev = [];
  if (series.length < 2) return ev;
  let lo = series[0], hi = series[0], pk = series[0], trend = 0;
  const ok = (a, b) => (dark === undefined ? true : Math.min(a, b) < dark);
  for (let i = 1; i < series.length; i++) {
    const v = series[i];
    if (trend === 0) {
      if (v - lo >= th && ok(lo, v)) { ev.push(i); trend = 1; pk = v; }
      else if (hi - v >= th && ok(v, hi)) { ev.push(i); trend = -1; pk = v; }
      lo = Math.min(lo, v); hi = Math.max(hi, v);
    } else if (trend === 1) { if (v > pk) pk = v; else if (pk - v >= th && ok(v, pk)) { ev.push(i); trend = -1; pk = v; } }
    else { if (v < pk) pk = v; else if (v - pk >= th && ok(pk, v)) { ev.push(i); trend = 1; pk = v; } }
  }
  return ev;
}
function maxPerSecond(evIdx, fps) {
  let best = 0, j = 0;
  for (let i = 0; i < evIdx.length; i++) { while (evIdx[j] < evIdx[i] - fps + 1e-9) j++; best = Math.max(best, i - j + 1); }
  return best;
}
function analyzeFlash(frames, fps) {
  const n16 = frames[0].g16.length, n64 = frames[0].g64.length;
  let m16 = 0, m64 = 0, mr = 0, near = 0, maxStep16 = 0;
  let worst16 = null;
  for (let r = 0; r < n16; r++) {
    const s = frames.map((f) => f.g16[r]);
    const ev16 = transitions(s, 0.1, 0.8), c16 = maxPerSecond(ev16, fps);
    if (c16 > m16) worst16 = { cell: [r % 16, Math.floor(r / 16)], per_sec: c16, events_s: ev16.map((i) => +(i / fps).toFixed(3)), series: s.map((v) => +v.toFixed(3)) };
    m16 = Math.max(m16, c16);
    mr = Math.max(mr, maxPerSecond(transitions(frames.map((f) => f.r16[r]), 20), fps));
    for (let i = 1; i < s.length; i++) maxStep16 = Math.max(maxStep16, Math.abs(s[i] - s[i - 1]));
  }
  let worst = null;
  for (let r = 0; r < n64; r++) {
    const ser = frames.map((f) => f.g64[r]);
    const ev = transitions(ser, 0.1, 0.8);
    const c = maxPerSecond(ev, fps);
    if (c > m64) worst = { cell: [r % 64, Math.floor(r / 64)], per_sec: c, events_s: ev.map((i) => +(i / fps).toFixed(3)), series: ser.map((v) => +v.toFixed(3)) };
    m64 = Math.max(m64, c);
    if (c >= 2) near++;
  }
  const g = maxPerSecond(transitions(frames.map((f) => f.all), 0.1, 0.8), fps);
  return { frames: frames.length, max_per_sec_16x9: m16, max_per_sec_64x36: m64, red_max_per_sec: mr, global_max_per_sec: g, cells_64x36_with_2plus: near, max_frame_step_16x9: +maxStep16.toFixed(4), worst_16x9: worst16, worst_64x36: worst };
}

function writeIndex() {
  const prev = existsSync(join(OUT, 'summary.json')) ? JSON.parse(readFileSync(join(OUT, 'summary.json'), 'utf8')) : {};
  const all = { ...prev, ...summary, generated: new Date().toISOString() };
  writeFileSync(join(OUT, 'summary.json'), JSON.stringify(all, null, 1));
  const list = [...new Set([...(prev.files || []), ...files])].sort();
  all.files = list;
  writeFileSync(join(OUT, 'summary.json'), JSON.stringify(all, null, 1));
  const L = [];
  L.push('# 折折（FX13）預覽與量測', '', `產生：${all.generated}（\`node tools/zhezhe_preview.mjs\`；製作代理不挑畫面，取樣時間由節拍固定）`, '');
  L.push('## 檔案', '', '| 檔案 | 內容 |', '|---|---|');
  const desc = (f) => f.startsWith('folds/fold_sheet') ? 'a0_c002 登場：燈籠紙立起 → 摺、摺、摺 → 貓'
    : f.startsWith('folds/') ? '貓 ↔ 造型的逐格（dur 等距 12 格＋落定）'
      : f.startsWith('spin/') ? '旋轉掃描 12 方位 × 2 仰角（中性灰底）'
        : ({ 'look.png': '總覽', 'contact_states.png': '情緒 × 嘴型 × 眨眼', 'contact_actions.png': '收摺訊號、耳朵動、走路、跳、摺錯、情緒轉換',
          'compare_g4_mid_with_kids.png': 'G4 中景（g4_mid）整格：折折在工作台上、兩個孩子立牌', 'compare_fold_vs_cut_close.png': '摺紙 vs 剪紙近景並排', 'compare_quiz_card.png': '題卡模式（quiz 鏡位、燈 0.55）折折攤開題卡',
          'flash.json': '光敏（每秒變化次數）', 'contrast.json': '投影模擬明度差', 'contrast_proj_sheet.png': '原圖／投影模擬 v2 對照', 'perf.json': '三角面數、繪製呼叫、每格時間',
          'determinism.json': '確定性（同一秒同一格）', 'a0_c002_intro_preview.mp4': 'a0_c002 開場自我介紹預覽（配 vo_a0_c002_01／02）', 'a0_c002_intro_contact.jpg': '開場影片每 0.5 秒一格' })[f] || '';
  for (const f of list) L.push(`| \`${f}\` | ${desc(f)} |`);
  L.push('', '`preview/index.html`：直接用瀏覽器開啟的互動預覽（按鈕切換摺紙造型、情緒、動作；「a0_c002 開場」播放登場）。', '');
  if (all.flash) {
    const v = all.flash.verdict || {};
    L.push('## 光敏', '', `專案標準（16×9 區域，同 tools/capture_analyze.py）在舞台鏡位（g4_mid、medium）：每秒最多 ${v.standard_16x9_stage_framings} 次（上限 3）；飽和紅 ${v.red_all} 次；整個畫面 ${v.global_all} 次。`,
      `壓力測試特寫（close，折折超過畫面一半高）16×9：${v.stress_close_16x9} 次——變形、跳躍不要在這種特寫裡做。細格 64×36（約 30 px）舞台鏡位：${v.fine_64x36_stage_framings} 次（移動的紙片邊緣掃過小區域；專案標準不採這個尺度，列出供驗收參考）。`,
      '', '各序列「16×9／64×36／飽和紅」：', '', '```', JSON.stringify(all.flash.per_sequence, null, 1), '```', '');
  }
  if (all.contrast) L.push('## 投影模擬 v2 後與背景的明度差', '', '```', JSON.stringify(all.contrast, null, 1), '```', '');
  if (all.perf) L.push('## 效能', '', `折折三角面（含外輪廓、所有造型）${all.perf.cat_triangles}；畫面上可見（依造型）${JSON.stringify(all.perf.visible_triangles_by_form)}；`, `每格 update ${all.perf.cat_update?.mean_ms} ms（最慢一批平均 ${all.perf.cat_update?.worst_batch_mean_ms}）；整格 有折折 ${all.perf.frame_with_cat?.mean_ms} ms／沒有 ${all.perf.frame_without_cat?.mean_ms} ms（${all.perf.gpu}）`, '');
  if (all.video) L.push('## a0_c002 預覽影片', '', `${all.video.seconds} 秒；_01 句從 ${all.video.lines.a0_c002_01} s、_02 句從 ${all.video.lines.a0_c002_02} s。影片本身逐格光敏（16×9／64×36／飽和紅）：${all.video.flash_on_video_frames?.max_per_sec_16x9}／${all.video.flash_on_video_frames?.max_per_sec_64x36}／${all.video.flash_on_video_frames?.red_max_per_sec} 次每秒。`, '');
  if (all.determinism !== undefined) L.push('## 確定性', '', all.determinism ? '通過：9 個時間點以五種順序重建，整格像素雜湊完全相同；cue 時間軸轉事件表（zhezheTrackFromTimeline）檢查通過。' : '未通過，見 determinism.json。', '');
  if (all.errors?.length) L.push('## 頁面錯誤', '', ...all.errors.map((e) => `- ${e}`), '');
  writeFileSync(join(OUT, 'INDEX.md'), L.join('\n'));
}

await main();
