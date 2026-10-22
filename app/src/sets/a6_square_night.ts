// 第六幕（a6_c001–a6_c007）紙燈節晚上的廣場。G5 第六幕代理。
// 底景照 assets/final/sets/a6_square_night/layout.json（夜空、遠山、騎樓、行道樹、求助站帳篷、燈籠架、一起糊紙的鎮民背影），
// 本檔加上需要程式的東西（全部是時間的純函式：只依 cue、cue 內秒數、world 決定畫面）：
//   - 主燈：大摺紙貓燈籠（和折折同一家族的多面摺紙造型：多邊形貓臉＋兩隻三角耳；竹骨架＋一片一片糊上的燈籠紙）
//       a6_c001 鎮民一起糊紙（紙片一片一片貼上，每片 0.6 秒淡入）；a6_c007 全部糊好，八盞燈的光流過來後柔和亮起（2.6 秒漸亮）
//   - 騎樓燈籠串：a6_c007 主燈亮了以後一盞接一盞亮（單盞 1.2 秒漸亮、相鄰間隔 0.45 秒）
//   - 台口上方八盞燈：主線的 src/stage/lamps.ts（全劇共用）；本檔的備用燈列 OWN_LAMP_ROW＝false 不建立
//   - 八盞燈流進廣場的光：一串小紙燈珠從台口上方八盞燈的中央沿弧線往主燈一顆一顆亮起（亮度固定，不閃）
//   - 修正第 2 輪：Q8 題卡題目在「，」處換行（只調排版，文字不變；見 q8Layout）；鏡位 a6_glow（光流進廣場的畫面）
// 光敏：每一區只有一次單向漸亮；沒有忽明忽暗；燈的泛光（加法混色）透明度只隨亮度慢慢變。
import {
  AdditiveBlending, BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide, Group, Mesh, MeshBasicMaterial, MeshStandardMaterial,
  PlaneGeometry, Sprite, SpriteMaterial, Vector3, type Material,
} from 'three';
import { buildImageSet, readLayout } from './imageSet';
import { fibers, finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import type { CueTimeline } from '../cues/timeline';
import { clamp, lerp, seeded } from '../util/math';
import type { BuiltSet, SetContext, SetEntry } from './types';

/** 主線在台口做了全劇共用的八盞實景紙燈之後改成 false（REVIEW.md G5 第一批裁定 3） */
export const OWN_LAMP_ROW = false;   // 主線已在 src/stage/lamps.ts 做了台口八盞燈（全劇共用），景不再自己做

// ───────────────────────────── 共用小工具（a6_window、a6_shop 也用） ─────────────────────────────
export const sine01 = (t: number): number => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t));
export function lineT(tl: CueTimeline, id: string, which: 'start' | 'end' = 'start', fallback = 0): number {
  const l = tl.lines.find((x) => x.line.id === id);
  return l ? (which === 'start' ? l.start : l.end) : fallback;
}
/** 這句在目前的壓縮級別被略過了嗎（略過的句子收成 0 秒） */
export const dropped = (tl: CueTimeline, id: string): boolean => tl.droppedLines.includes(id);

/** 柔和泛光貼圖（徑向漸層） */
export function haloTexture(): CanvasTexture {
  const S = 256;
  const [c, g] = makeCanvas(S, S);
  const grd = g.createRadialGradient(S / 2, S / 2, 2, S / 2, S / 2, S / 2);
  grd.addColorStop(0, 'rgba(255,255,255,0.9)');
  grd.addColorStop(0.35, 'rgba(255,255,255,0.45)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, S, S);
  return finishTexture(new CanvasTexture(c));
}

/** 圓紙燈籠貼圖（暖色紙＋竹骨線＋上下木蓋）；透明背景 */
export function lanternTexture(paper: string, seed: number): CanvasTexture {
  const W = 128, H = 160;
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = '#7a5434';
  g.fillRect(W * 0.34, 4, W * 0.32, 14);
  g.fillRect(W * 0.34, H - 18, W * 0.32, 14);
  g.beginPath();
  g.ellipse(W / 2, H / 2, W * 0.46, H * 0.4, 0, 0, Math.PI * 2);
  g.fillStyle = paper;
  g.fill();
  g.save();
  g.clip();
  fibers(g, W, H, seed, 2.0);
  g.strokeStyle = 'rgba(150,96,60,0.75)';
  g.lineWidth = 2.2;
  for (const k of [-0.55, 0, 0.55]) {
    const w = W * 0.46 * Math.sqrt(1 - k * k);
    g.beginPath(); g.ellipse(W / 2, H / 2, w, H * 0.4, 0, 0, Math.PI * 2); g.stroke();
  }
  g.restore();
  g.strokeStyle = '#4e3e33';
  g.lineWidth = 3;
  g.beginPath(); g.ellipse(W / 2, H / 2, W * 0.46, H * 0.4, 0, 0, Math.PI * 2); g.stroke();
  return finishTexture(new CanvasTexture(c));
}

export interface LanternLamp { group: Group; mat: MeshStandardMaterial; halo: Sprite; set(b: number): void }
/** 一盞會亮的小紙燈籠（平面卡紙＋泛光）。b＝亮度 0–1 */
export function makeLamp(tex: CanvasTexture, w: number, order: number, mats: Material[], haloTex: CanvasTexture, haloScale = 3.2, base = 0.1): LanternLamp {
  const group = new Group();
  const h = w * 160 / 128;
  const mat = new MeshStandardMaterial({ map: tex, side: DoubleSide, roughness: 0.9, metalness: 0, alphaTest: 0.5 });
  mat.emissiveMap = tex;
  mat.emissive = new Color('#ffcf96');
  mat.emissiveIntensity = base;
  mats.push(mat);
  const m = new Mesh(new PlaneGeometry(w, h), mat);
  m.renderOrder = order;
  group.add(m);
  const halo = new Sprite(new SpriteMaterial({ map: haloTex, color: '#ffc884', transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
  halo.scale.set(w * haloScale, w * haloScale, 1);
  halo.position.z = -0.02;
  halo.renderOrder = order - 1;
  group.add(halo);
  return {
    group, mat, halo,
    set(b: number) {
      mat.emissiveIntensity = base + (1.05 - base) * b;
      (halo.material as SpriteMaterial).opacity = 0.42 * b;
      halo.visible = b > 0.002;
    },
  };
}

// ───────────────────────────── 主燈：大摺紙貓燈籠 ─────────────────────────────
const N_RING = 10;
const PAPER = '#f4c494';
const INK = '#4e3e33';

interface CatLantern {
  group: Group;
  /** p＝糊好的比例 0–1（逐片淡入）、glow＝亮度 0–1 */
  set(p: number, glow: number): void;
  headTop: Vector3;
}

/** 貓臉與摺痕的貼圖（平面投影到多面體上）：u＝(x+RX)/(2RX)、v＝(y−(cy−RY))/(2RY) */
function catFaceTexture(): CanvasTexture {
  const S = 1024;
  const [c, g] = makeCanvas(S, S);
  g.fillStyle = PAPER;
  g.fillRect(0, 0, S, S);
  fibers(g, S, S, 77, 2.4);
  // 臉：瞇瞇笑眼、小鼻子、ω 嘴、鬍鬚（簡單線條，和折折同一套臉）
  g.strokeStyle = INK; g.lineCap = 'round'; g.lineJoin = 'round';
  g.lineWidth = 15;
  for (const sx of [-1, 1]) {
    g.beginPath(); g.arc(S / 2 + sx * 170, S * 0.47, 46, Math.PI * 1.12, Math.PI * 1.88); g.stroke();
  }
  g.fillStyle = '#c8705a';
  g.beginPath(); g.moveTo(S / 2 - 26, S * 0.555); g.lineTo(S / 2 + 26, S * 0.555); g.lineTo(S / 2, S * 0.59); g.closePath(); g.fill();
  g.lineWidth = 10;
  g.beginPath(); g.arc(S / 2 - 26, S * 0.6, 26, 0.1 * Math.PI, 0.95 * Math.PI); g.stroke();
  g.beginPath(); g.arc(S / 2 + 26, S * 0.6, 26, 0.05 * Math.PI, 0.9 * Math.PI); g.stroke();
  g.lineWidth = 7;
  for (const sx of [-1, 1]) for (const k of [-1, 0, 1]) {
    g.beginPath(); g.moveTo(S / 2 + sx * 120, S * 0.58 + k * 26); g.lineTo(S / 2 + sx * 300, S * 0.56 + k * 52); g.stroke();
  }
  // 腮紅
  g.fillStyle = 'rgba(232,140,120,0.35)';
  for (const sx of [-1, 1]) { g.beginPath(); g.ellipse(S / 2 + sx * 250, S * 0.6, 60, 34, 0, 0, Math.PI * 2); g.fill(); }
  return finishTexture(new CanvasTexture(c));
}

function earTexture(): CanvasTexture {
  const [c, g] = makeCanvas(256, 256);
  g.fillStyle = PAPER; g.fillRect(0, 0, 256, 256);
  fibers(g, 256, 256, 79, 2.0);
  g.fillStyle = 'rgba(236,150,136,0.55)';
  g.beginPath(); g.moveTo(128, 40); g.lineTo(200, 220); g.lineTo(56, 220); g.closePath(); g.fill();
  return finishTexture(new CanvasTexture(c));
}

function buildCatLantern(mats: Material[], haloTex: CanvasTexture): CatLantern {
  const group = new Group();
  group.name = 'a6:main-lantern';
  const RX = 1.5, RY = 1.28, BASE_H = 0.78;
  const cy = BASE_H + RY;
  // 底座（木箱）
  const [bc, bg] = makeCanvas(256, 128);
  bg.fillStyle = '#9a6a44'; bg.fillRect(0, 0, 256, 128); fibers(bg, 256, 128, 81, 2);
  bg.strokeStyle = '#5e3e28'; bg.lineWidth = 4; bg.strokeRect(2, 2, 252, 124);
  bg.beginPath(); bg.moveTo(0, 30); bg.lineTo(256, 30); bg.stroke();
  const baseMat = new MeshStandardMaterial({ map: finishTexture(new CanvasTexture(bc)), roughness: 0.92, metalness: 0 });
  mats.push(baseMat);
  const base = new Mesh(new PlaneGeometry(1.7, BASE_H), baseMat);
  base.position.set(0, BASE_H / 2, 0.15);
  base.renderOrder = LAYER.mid.order + 40;
  base.castShadow = true;
  group.add(base);

  // 頂點：中心（往前凸）、內圈、外圈
  const C = new Vector3(0, cy - 0.05, 0.62);
  const inner: Vector3[] = [], outer: Vector3[] = [];
  for (let i = 0; i < N_RING; i++) {
    const a = Math.PI / 2 + (i / N_RING) * Math.PI * 2 + Math.PI / N_RING;
    outer.push(new Vector3(RX * Math.cos(a), cy + RY * Math.sin(a), 0));
    inner.push(new Vector3(0.56 * RX * Math.cos(a), cy - 0.03 + 0.56 * RY * Math.sin(a), 0.44));
  }
  const faceTex = catFaceTexture();
  const uvOf = (p: Vector3): [number, number] => [(p.x + RX) / (2 * RX), (p.y - (cy - RY)) / (2 * RY)];
  const panels: { mesh: Mesh; mat: MeshStandardMaterial }[] = [];
  const panelMat = (map: CanvasTexture): MeshStandardMaterial => {
    const m = new MeshStandardMaterial({ map, side: DoubleSide, roughness: 0.9, metalness: 0, flatShading: true, transparent: true, opacity: 1, depthWrite: true });
    m.emissiveMap = map;
    m.emissive = new Color('#ffbe7c');
    m.emissiveIntensity = 0.1;
    mats.push(m);
    return m;
  };
  const addPanel = (tris: Vector3[][], map: CanvasTexture, uv: (p: Vector3) => [number, number]): void => {
    const pos: number[] = [], uvs: number[] = [];
    for (const t of tris) for (const p of t) { pos.push(p.x, p.y, p.z); uvs.push(...uv(p)); }
    const geo = new BufferGeometry();
    geo.setAttribute('position', new BufferAttribute(new Float32Array(pos), 3));
    geo.setAttribute('uv', new BufferAttribute(new Float32Array(uvs), 2));
    geo.computeVertexNormals();
    const mat = panelMat(map);
    const mesh = new Mesh(geo, mat);
    mesh.renderOrder = LAYER.mid.order + 42;
    mesh.castShadow = true;
    group.add(mesh);
    panels.push({ mesh, mat });
  };
  for (let i = 0; i < N_RING; i++) {
    const j = (i + 1) % N_RING;
    addPanel([[C, inner[i], inner[j]]], faceTex, uvOf);
    addPanel([[inner[i], outer[i], outer[j]], [inner[i], outer[j], inner[j]]], faceTex, uvOf);
  }
  // 兩隻三角耳（各兩片，中間有一條往前的稜）
  const earTex = earTexture();
  const ears: Vector3[][] = [];
  for (const sx of [-1, 1]) {
    // 外圈頂端附近的兩點：取 x 符號相同、y 最高的兩個（外圈 10 點、左右各 5 點）
    const [p0, p1] = outer.filter((p) => Math.sign(p.x) === sx).sort((p, q) => q.y - p.y);
    const tip = new Vector3(sx * 0.95, cy + RY + 0.78, 0.1);
    const mid = new Vector3((p0.x + p1.x) / 2, (p0.y + p1.y) / 2 + 0.18, 0.3);
    ears.push([p0, mid, tip], [mid, p1, tip]);
    const ex0 = Math.min(p0.x, p1.x, tip.x), ex1 = Math.max(p0.x, p1.x, tip.x), ey0 = Math.min(p0.y, p1.y), ey1 = tip.y;
    const euv = (p: Vector3): [number, number] => [(p.x - ex0) / (ex1 - ex0), (p.y - ey0) / (ey1 - ey0)];
    addPanel([[p0, mid, tip]], earTex, euv);
    addPanel([[mid, p1, tip]], earTex, euv);
  }
  // 竹骨架（細長方條，沿摺痕）
  const bamboo = new MeshStandardMaterial({ color: '#cf9f62', roughness: 0.9, metalness: 0 });
  bamboo.emissive = new Color('#cf9f62'); bamboo.emissiveIntensity = 0.12;
  mats.push(bamboo);
  const strip = (a: Vector3, b: Vector3, w = 0.045): void => {
    const len = a.distanceTo(b);
    const m = new Mesh(new PlaneGeometry(len, w), bamboo);
    m.position.copy(a).add(b).multiplyScalar(0.5);
    m.position.z += 0.012;
    const dir = b.clone().sub(a);
    m.rotation.z = Math.atan2(dir.y, dir.x);
    m.renderOrder = LAYER.mid.order + 44;
    group.add(m);
  };
  for (let i = 0; i < N_RING; i++) {
    const j = (i + 1) % N_RING;
    strip(outer[i], outer[j], 0.05);
    strip(inner[i], inner[j], 0.032);
    strip(inner[i], outer[i], 0.03);
    strip(C, inner[i], 0.024);
  }
  for (const e of ears) { strip(e[0], e[2], 0.04); strip(e[1], e[2], 0.04); }
  // 泛光（主燈後方，加法混色；透明度只隨 glow 慢慢變）
  const halo = new Sprite(new SpriteMaterial({ map: haloTex, color: '#ffbf7a', transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
  halo.scale.set(7.2, 6.8, 1);
  halo.position.set(0, cy + 0.2, -0.3);
  halo.renderOrder = LAYER.mid.order + 38;
  group.add(halo);
  // 糊紙順序（固定種子）
  const order = panels.map((_, i) => i);
  const r = seeded(613);
  for (let i = order.length - 1; i > 0; i--) { const k = Math.floor(r() * (i + 1)); [order[i], order[k]] = [order[k], order[i]]; }
  const rank = new Array(panels.length);
  order.forEach((pi, k) => { rank[pi] = k; });
  return {
    group,
    headTop: new Vector3(0, cy + RY + 0.6, 0.1),
    set(p: number, glow: number) {
      const n = panels.length;
      panels.forEach((pn, i) => {
        // 第 k 片在 p 走到 k/n 時開始淡入（每片佔 1/n 的一段，淡入用其中 70%）
        const u = clamp((p * n - rank[i]) / 0.7);
        pn.mesh.visible = u > 0.002;
        pn.mat.opacity = u;
        pn.mat.transparent = u < 0.999;
        pn.mat.depthWrite = u > 0.5;
        pn.mat.emissiveIntensity = 0.1 + 0.95 * glow;
      });
      (halo.material as SpriteMaterial).opacity = 0.38 * glow;
      halo.visible = glow > 0.002;
    },
  };
}

// ───────────────────────────── Q8 題目斷行（修正第 2 輪） ─────────────────────────────
// 題卡（src/ui/quizcard.ts，共用元件）用 textContent 自動斷行，Q8 會斷成「……怎麼／辦？」。
// 題目文字不能改（engine-test 逐字比對八題_v03.md），所以只調排版：題卡寫入 Q8 題目後，把同一段文字拆成兩個 inline-block
//（在「，」後面），textContent 完全不變；放得下一行就一行，放不下就在「，」處換行。字級不動（題卡樣式 0.063H ≈ 68 px）。
const Q8_TEXT = '朋友可能碰到危險物品，卻說「不要告訴老師」。怎麼辦？';
const Q8_BREAK = Q8_TEXT.indexOf('，') + 1;
function q8Layout(el: Element | null): void {
  if (!el || el.textContent !== Q8_TEXT || el.childNodes.length !== 1 || el.firstChild?.nodeType !== 3) return;
  const doc = el.ownerDocument;
  const part = (s: string): HTMLElement => { const sp = doc.createElement('span'); sp.style.display = 'inline-block'; sp.textContent = s; return sp; };
  el.replaceChildren(part(Q8_TEXT.slice(0, Q8_BREAK)), part(Q8_TEXT.slice(Q8_BREAK)));
}
let q8Observer: MutationObserver | null = null;
/** 裝一次（整頁共用；題卡換題時 quizcard.ts 重寫 textContent → 觀察到變化當下就重排，畫面上不會有斷錯的一格） */
function installQ8Layout(): void {
  if (q8Observer || typeof document === 'undefined' || typeof MutationObserver === 'undefined') return;
  const el = document.querySelector('#quiz-card .quiz-q');
  if (!el) return;
  q8Observer = new MutationObserver(() => q8Layout(el));
  q8Observer.observe(el, { childList: true, characterData: true, subtree: true });
  q8Layout(el);
}

// ───────────────────────────── 位置與鏡位 ─────────────────────────────
const MAIN = { x: -3.9, z: -0.8 };
const LAMP_ROW = { y: 7.05, z: 4.05, x0: -5.6, dx: 1.6, w: 0.5 };
const C = (pos: [number, number, number], target: [number, number, number], fov = 20): CameraPreset => ({ pos, target, fov });
export const A6_SQUARE_CAMERAS: Record<string, CameraPreset> = {
  /** 廣場大全景：主燈在左、鎮民一起糊紙，孩子在主燈右邊（台口外緣不入鏡） */
  a6_wide: C([-1.0, 2.55, 23.0], [-1.0, 2.25, 0]),
  /** 孩子與主燈（小晴、小宇說話） */
  a6_kids: C([-1.55, 1.95, 14.8], [-1.55, 1.76, 0]),
  /** 品安近景（抓著書包背帶，一直沒說話；小晴、小宇在左） */
  a6_pinan: C([1.3, 1.55, 6.9], [1.3, 1.42, 0]),       // 修正第 2 輪：品安往右站 0.5（燈籠架左柱不壓在她身上）
  /** 燈籠架後的角落：三人近景（架子的竹竿與燈籠在前景框住三人） */
  a6_secret: C([1.65, 1.8, 12.4], [1.65, 1.66, 0]),
  /** a6_c005 回故事＝a6_c006 起點：同 a6_secret 往左 0.5（帳篷前的林老師在畫面右緣外） */
  a6_secret_c6: C([1.15, 1.8, 12.4], [1.15, 1.66, 0]),
  /** 三人近景再靠近一點（品安說秘密） */
  a6_secret_close: C([1.95, 1.68, 10.2], [1.95, 1.56, 0]),
  /** 品安說「藏在書包裡」「不要告訴老師」（品安近景，小宇在畫面左側） */
  a6_secret_pinan: C([2.4, 1.62, 7.6], [2.4, 1.52, 0]),
  /** 跟拍往右的中途 */
  a6_follow: C([3.95, 1.8, 13.6], [3.95, 1.62, 0]),
  /** 求助站帳篷中景：林老師、葉護理師與三個孩子（台口右緣不入鏡） */
  a6_tent: C([3.95, 1.78, 13.6], [3.95, 1.6, 0]),
  /** 品安與林老師（說出來） */
  a6_tent_close: C([4.75, 1.72, 11.4], [4.75, 1.58, 0]),
  /** 廣場中景（a6_c007 開頭：主燈與底座上的折折、廣場群像） */
  a6_plaza: C([-2.4, 2.4, 17.5], [-2.4, 2.2, 0]),
  /** 後拉：台口＋廣場大全景（台口上方八盞燈都亮著） */
  a6_full: C([0, 4.6, 36], [0, 4.4, 0]),
  /** 修正第 2 輪：光流進廣場、主燈亮起、騎樓燈籠一盞接一盞的畫面（比台口近一級；主燈、廣場群像、上方留夜空給光流進來） */
  a6_glow: C([-1.5, 2.8, 20.2], [-1.5, 2.55, 0]),
};

export const A6_SQUARE_NIGHT: SetEntry = {
  title: '紙燈節晚上的廣場（第六幕：主燈、騎樓燈籠串、台口八盞燈、求助站）',
  cameras: A6_SQUARE_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const layout = readLayout(ctx, 'a6_square_night') ?? { format: 'antidrug-set/1' };
    const base = buildImageSet({ ...ctx, name: 'a6_square_night' }, layout);
    const group = base.group;
    group.name = 'set:a6_square_night';
    const mats: Material[] = [...(base.materials ?? [])];
    const glowMats: Material[] = [];      // 燈籠（不受 FX8 降彩：燈光本身就是暖色）
    const haloTex = haloTexture();

    // ---- 夜色：前排騎樓前面一層上暗下透明的深藍紗（樓上與天空變暗，孩子身後的騎樓下層仍亮）
    {
      const [vc, vg] = makeCanvas(8, 256);
      const grd = vg.createLinearGradient(0, 0, 0, 256);
      grd.addColorStop(0, 'rgba(26,28,62,0.66)');
      grd.addColorStop(0.42, 'rgba(26,28,62,0.46)');
      grd.addColorStop(0.68, 'rgba(26,28,62,0.14)');
      grd.addColorStop(0.82, 'rgba(26,28,62,0)');
      grd.addColorStop(1, 'rgba(26,28,62,0)');
      vg.fillStyle = grd; vg.fillRect(0, 0, 8, 256);
      const veilMat = new MeshBasicMaterial({ map: finishTexture(new CanvasTexture(vc)), transparent: true, depthWrite: false });
      const veil = new Mesh(new PlaneGeometry(44, 9.0), veilMat);
      veil.position.set(0, 4.5, -1.84);
      veil.renderOrder = LAYER.mid.order - 50;
      group.add(veil);
    }
    // ---- 主燈
    const cat = buildCatLantern(glowMats, haloTex);
    cat.group.position.set(MAIN.x, 0, MAIN.z);
    group.add(cat.group);

    // ---- 騎樓燈籠串（前排騎樓屋簷下＋後排騎樓），一條細繩串起來
    const lampColors = ['#f6d2a0', '#f2b88a', '#f7dcae', '#eeb08c', '#f4c99a'];
    const town: { lamp: LanternLamp; order: number }[] = [];
    const townPos: [number, number, number][] = [];
    for (let i = 0; i < 8; i++) { const x = -6.9 + i * 1.62; townPos.push([x, 4.28 - 0.12 * (i % 2), -1.72]); }
    for (let i = 0; i < 5; i++) { const x = -0.9 + i * 2.0; townPos.push([x, 3.75, -3.05]); }
    const ropeMat = new MeshBasicMaterial({ color: '#5a4434' });
    for (const [z, idx0, idx1] of [[-1.7, 0, 8], [-3.03, 8, 13]] as const) {
      for (let i = idx0; i < idx1 - 1; i++) {
        const a = townPos[i], b = townPos[i + 1];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const rope = new Mesh(new PlaneGeometry(len, 0.025), ropeMat);
        rope.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.22, z + 0.01);
        rope.rotation.z = Math.atan2(b[1] - a[1], b[0] - a[0]);
        rope.renderOrder = LAYER.mid.order - 6;
        group.add(rope);
      }
    }
    // 亮起順序：從主燈附近往兩邊（前排先、後排後）
    const dist = townPos.map((p, i) => ({ i, d: Math.abs(p[0] - MAIN.x) + (p[2] < -2.5 ? 6 : 0) })).sort((a, b) => a.d - b.d);
    const rankOf = new Map(dist.map((e, k) => [e.i, k]));
    townPos.forEach((p, i) => {
      const lamp = makeLamp(lanternTexture(lampColors[i % lampColors.length], 400 + i), p[2] < -2.5 ? 0.36 : 0.44, LAYER.mid.order - 5, glowMats, haloTex, 3.0, 0.14);
      lamp.group.position.set(p[0], p[1], p[2] + 0.02);
      group.add(lamp.group);
      town.push({ lamp, order: rankOf.get(i) ?? i });
    });

    // ---- 台口上方八盞燈
    const row: LanternLamp[] = [];
    if (OWN_LAMP_ROW) {
      const rope = new Mesh(new PlaneGeometry(LAMP_ROW.dx * 8 + 1.2, 0.03), ropeMat);
      rope.position.set(0, LAMP_ROW.y + 0.42, LAMP_ROW.z - 0.01);
      rope.renderOrder = LAYER.curtain.order + 8;
      group.add(rope);
      for (let i = 0; i < 8; i++) {
        const lamp = makeLamp(lanternTexture('#f3e2c2', 500 + i), LAMP_ROW.w, LAYER.curtain.order + 10, glowMats, haloTex, 3.0, 0.1);
        lamp.group.position.set(LAMP_ROW.x0 + i * LAMP_ROW.dx, LAMP_ROW.y, LAMP_ROW.z);
        const string = new Mesh(new PlaneGeometry(0.02, 0.2), ropeMat);
        string.position.set(0, LAMP_ROW.w * 0.62 + 0.08, 0);
        lamp.group.add(string);
        group.add(lamp.group);
        row.push(lamp);
      }
    }

    // ---- 八盞燈流進廣場的光（小紙燈珠沿弧線）
    const beadTex = haloTexture();
    const beads: Sprite[] = [];
    const p0 = OWN_LAMP_ROW ? new Vector3(0, LAMP_ROW.y - 0.35, LAMP_ROW.z - 0.1) : new Vector3(0, 8.85, 4.6);
    const top = cat.headTop.clone().add(new Vector3(MAIN.x, 0, MAIN.z));
    const p2 = new Vector3(top.x + 0.2, top.y + 0.1, top.z + 0.2);
    const p1 = OWN_LAMP_ROW ? new Vector3(-1.6, LAMP_ROW.y + 1.1, 1.6) : new Vector3(-1.4, 8.3, 3.4);
    const NB = 34;
    for (let i = 0; i < NB; i++) {
      const u = (i + 0.5) / NB;
      const p = p0.clone().multiplyScalar((1 - u) * (1 - u)).add(p1.clone().multiplyScalar(2 * u * (1 - u))).add(p2.clone().multiplyScalar(u * u));
      const s = new Sprite(new SpriteMaterial({ map: beadTex, color: '#f0b46c', transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
      s.position.copy(p);
      s.scale.set(0.3, 0.3, 1);
      s.renderOrder = LAYER.fore.order + 20;
      s.visible = false;
      group.add(s);
      beads.push(s);
    }

    const baseUpdate = base.update;
    return {
      ...base, group, materials: mats, report: base.report,
      cameras: { ...(base.cameras ?? {}), ...A6_SQUARE_CAMERAS },
      landmarks: { ...(base.landmarks ?? {}), mainLantern: { x0: MAIN.x - 1.5, x1: MAIN.x + 1.5, y: 0.78, z: MAIN.z } },
      update(o) {
        baseUpdate?.(o);
        const { tl, t, world } = o;
        const id = tl.cue.id;
        if (id === 'a6_c003' || id === 'a6_c004' || id === 'a6_c005') {
          installQ8Layout();
          if (typeof document !== 'undefined') q8Layout(document.querySelector('#quiz-card .quiz-q'));
        }
        // 主燈：a6_c001 糊紙 0.55 → 0.8（小晴說「幫他把主燈完成」之後加快），a6_c002–c006 停在 0.8，a6_c007 全部糊好
        let paper = 0.8, glow = 0, stream = 0, townT = -1;
        if (id === 'a6_c001') {
          const s = lineT(tl, 'a6_c001_01', 'start', 2.5);
          paper = lerp(0.5, 0.8, clamp((t - 0.6) / Math.max(4, s + 9 - 0.6)));
        } else if (id === 'a6_c007') {
          paper = 1;
          const s2 = lineT(tl, 'a6_c007_02', 'start', 12);
          // 光流（2.6 秒）→ 主燈漸亮（2.6 秒）→ 騎樓燈籠一盞接一盞。修正第 2 輪：鏡頭先後拉到台口（看得到八盞燈），
          // 光從燈下流出時鏡頭跟著推回廣場（a6.json），所以光流晚 1.8 秒起：主燈在推回後的畫面裡亮、騎樓燈籠在旁白「都亮了」時亮
          const t0 = s2 - 3.2;
          stream = clamp((t - t0) / 2.6);
          glow = sine01((t - t0 - 2.2) / 2.6);
          townT = t - (t0 + 3.6);
        } else if (!id.startsWith('a6_')) paper = 1;
        cat.set(paper, glow);
        // 光流：燈珠一顆一顆亮起（每顆 0.6 秒漸亮，之後固定）
        beads.forEach((b, i) => {
          const v = sine01((stream * (NB + 6) - i) / 6);
          b.visible = v > 0.002;
          (b.material as SpriteMaterial).opacity = 0.55 * v * (1 - 0.3 * glow);
        });
        // 騎樓燈籠：單盞 1.2 秒漸亮、間隔 0.45 秒
        town.forEach(({ lamp, order }) => lamp.set(townT < 0 ? 0 : sine01((townT - order * 0.45) / 1.2)));
        // 台口八盞燈：照 world.lamps
        row.forEach((lamp, i) => lamp.set(clamp(world.lamps[i] ?? 0)));
      },
    };
  },
};
