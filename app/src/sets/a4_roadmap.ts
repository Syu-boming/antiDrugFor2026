// a4_roadmap：第四幕「紙上的路」（a4_c002 後半～a4_c008 前半）。G5 第四幕代理。
// 牛皮紙地圖（俯視）＋立體書小屋（隨 set.popup／set.fold 從地圖上長出來／收回）＋紙剪小車（沿路線前進、偏離、凍結）
// ＋虛線預定路線＋鉛筆偏移線＋背光剪影幕（FX10：駕駛、乘客、路人三個剪影；聚光依序照過，每次漸變 ≥1 秒）。
// 和故事場景明顯區隔：整個畫面是一張攤在桌上的紙地圖，小車是通用小車（不是阿樂叔叔的小貨車），沒有碰撞、沒有數字。
//
// 景自己的動作寫在 cue 的 `setTrack`（引擎不讀，本景與 gate 景的 update 讀；時間參照同 animation.start：
// 數字、"a4_c003_01.end+0.3"、"end-1"）：
//   { "do": "plan",   "to": 1, "start": …, "duration": 1.5 }        虛線預定路線畫出來的比例（0–1）
//   { "do": "car",    "keys": [[時間, 路線點序號], …] }              小車沿實際路線前進（序號＝ACTUAL 的點，可有小數；單調三次插值，不會倒退）
//   { "do": "screen", "to": 1, "start": …, "duration": 2.2 }        剪影幕立起（1）／收回（0）
//   { "do": "glow",   "to": 1, "start": …, "duration": 1.6 }        剪影幕背光（0＝沒開燈的紙，1＝背光）
//   { "do": "spot",   "target": "driver|passenger|walker", "to": 1, "start": …, "duration": 1.2 }   聚光（≥1 秒漸變）
//   { "do": "street", "to": 1, "start": …, "duration": 1.0 }        地圖淡成校門口地面（回到街景前；gate 景同一張地面圖）
// 所有量都是時間的純函式（同一秒同一格）。
import {
  AdditiveBlending, BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide, Group, LinearMipmapLinearFilter, Mesh,
  MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, RepeatWrapping, type Material, type Texture,
} from 'three';
import { fibers, finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import { clamp, ease, lerp, seeded } from '../util/math';
import type { CueTimeline } from '../cues/timeline';
import type { BuiltSet, SetContext, SetEntry } from './types';

// ------------------------------------------------------------------ 共用：setTrack（gate 景也用）

export interface TrackEvent { do: string; start: number; duration: number; p: Record<string, unknown> }

const REF_RE = /^([a-z0-9_]+?)(\.end|\.start)?([+-]\d+(?:\.\d+)?)?$/;
const trackCache = new WeakMap<CueTimeline, TrackEvent[]>();

/** cue 時間參照 → 秒（同 timeline.ts 的規則；找不到台詞時用偏移量） */
export function refTime(tl: CueTimeline, ref: unknown): number {
  if (typeof ref === 'number') return ref;
  if (typeof ref !== 'string') return 0;
  const m = REF_RE.exec(ref.trim());
  if (!m) return 0;
  const off = m[3] ? Number(m[3]) : 0;
  if (m[1] === 'end') return tl.duration + off;
  const l = tl.lines.find((x) => x.line.id === m[1]);
  if (!l) return off;
  return (m[2] === '.end' ? l.end : l.start) + off;
}

/** 這個 cue 的 setTrack（解析好時間、依開始時間排序） */
export function trackOf(tl: CueTimeline): TrackEvent[] {
  let ev = trackCache.get(tl);
  if (ev) return ev;
  const raw = (tl.cue as unknown as { setTrack?: Record<string, unknown>[] }).setTrack;
  ev = (Array.isArray(raw) ? raw : []).map((r) => ({ do: String(r.do ?? ''), start: refTime(tl, r.start ?? 0), duration: Math.max(0, Number(r.duration ?? 0)), p: r }));
  ev.sort((a, b) => a.start - b.start);
  trackCache.set(tl, ev);
  return ev;
}

/** 數值軌：從 v0 開始，依序套用同名事件（lerp 到 to，正弦緩動） */
export function trackValue(tl: CueTimeline, name: string, t: number, v0: number, easeName = 'sine'): number {
  let v = v0;
  for (const e of trackOf(tl)) {
    if (e.do !== name || t < e.start) continue;
    const u = e.duration > 0 ? clamp((t - e.start) / e.duration) : 1;
    v = lerp(v, Number(e.p.to ?? 1), ease(String(e.p.ease ?? easeName), u));
  }
  return v;
}

/** 圖像紙片（可選白邊已在圖裡）：底邊中央為原點的平面 */
export function imagePlane(img: HTMLImageElement | undefined, width: number, o: { basic?: boolean; color?: string; alphaTest?: number; transparent?: boolean; a2c?: boolean } = {}): Mesh | null {
  if (!img) return null;
  const tex = finishTexture(new CanvasTexture(img as unknown as HTMLCanvasElement));
  tex.minFilter = LinearMipmapLinearFilter;
  const h = width * img.naturalHeight / img.naturalWidth;
  const geo = new PlaneGeometry(width, h);
  geo.translate(0, h / 2, 0);
  const common = { map: tex, side: DoubleSide, ...(o.transparent ? { transparent: true, depthWrite: false } : { alphaTest: o.alphaTest ?? 0.5, alphaToCoverage: !!o.a2c }) };
  const mat: Material = o.basic ? new MeshBasicMaterial({ ...common, color: new Color(o.color ?? '#ffffff') })
    : new MeshStandardMaterial({ ...common, roughness: 0.92, metalness: 0, color: new Color(o.color ?? '#ffffff') });
  const m = new Mesh(geo, mat);
  m.userData.h = h;
  return m;
}

// ------------------------------------------------------------------ 地圖幾何（和 review/G5/a4/scripts/build_a4_art.py 一致）

/** 地圖中心（世界 x）；u＝x−MAP_X、v＝z */
export const MAP_X = -5.0;
export const MAP_W = 18, MAP_H = 9;
const MAP_Y = 0.012;

/** 預定路線（虛線）：支路北上 → 右轉進近車道 → 停在停止線前 */
function planPoints(): [number, number][] {
  const pts: [number, number][] = [];
  for (let v = 2.7; v > 1.95; v -= 0.1) pts.push([-3.25, v]);   // G6 精修：起點從 v 2.95 往上移到 2.7（a4_map 鏡頭往上收，避開台口左側布幕）
  const c: [number, number] = [-2.3, 1.95], R = 0.95;
  for (let k = 0; k <= 16; k++) { const th = Math.PI + (Math.PI / 2) * (k / 16); pts.push([c[0] + R * Math.cos(th), c[1] + R * Math.sin(th)]); }
  for (let u = -2.2; u <= 2.17; u += 0.1) pts.push([u, 1.0]);
  return pts;
}

/** 實際路線（小車中心）：上坡慢慢晃 → 晚轉、轉太大跨到對向車道 → 拉回 → 過了停止線，偏向斑馬線 → 在碰到任何東西前凍結 */
export const ACTUAL: [number, number][] = [
  [-3.25, 2.7], [-3.17, 2.42], [-3.33, 2.16], [-3.18, 1.92], [-3.02, 1.6], [-2.62, 0.82], [-1.75, 0.4], [-0.55, 0.52], [0.7, 0.9], [1.7, 1.0], [2.4, 0.93], [2.92, 0.84],
];
/** 路人（斑馬線上，往學校方向走） */
export const WALKER_UV: [number, number] = [4.4, 0.1];

/** Catmull-Rom 取樣＋弧長表 */
function spline(ctrl: [number, number][], per = 24): { pts: [number, number][]; len: number[]; ctrlS: number[] } {
  const pts: [number, number][] = [];
  const ctrlS: number[] = [];
  const P = (i: number): [number, number] => ctrl[Math.max(0, Math.min(ctrl.length - 1, i))];
  for (let i = 0; i < ctrl.length - 1; i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    for (let k = 0; k < per; k++) {
      const t = k / per, t2 = t * t, t3 = t2 * t;
      const f = (a: number, b: number, c: number, d: number): number => 0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      pts.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
    }
  }
  pts.push(ctrl[ctrl.length - 1]);
  const len = [0];
  for (let i = 1; i < pts.length; i++) len.push(len[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  for (let i = 0; i < ctrl.length; i++) ctrlS.push(len[Math.min(pts.length - 1, i * per)]);
  return { pts, len, ctrlS };
}

function polyLen(pts: [number, number][]): number[] {
  const len = [0];
  for (let i = 1; i < pts.length; i++) len.push(len[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  return len;
}

function sampleAt(pts: [number, number][], len: number[], s: number): { p: [number, number]; dir: [number, number] } {
  s = clamp(s, 0, len[len.length - 1]);
  let i = 1;
  while (i < len.length - 1 && len[i] < s) i++;
  const u = (s - len[i - 1]) / Math.max(1e-6, len[i] - len[i - 1]);
  const a = pts[i - 1], b = pts[i];
  const d = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
  return { p: [lerp(a[0], b[0], u), lerp(a[1], b[1], u)], dir: [(b[0] - a[0]) / d, (b[1] - a[1]) / d] };
}

/** 單調三次插值（Fritsch–Carlson）：keys [t, s]（t 遞增、s 不遞減） */
function monotone(keys: [number, number][], t: number): number {
  if (!keys.length) return 0;
  if (t <= keys[0][0]) return keys[0][1];
  const n = keys.length;
  if (t >= keys[n - 1][0]) return keys[n - 1][1];
  const d: number[] = [], m: number[] = [];
  for (let i = 0; i < n - 1; i++) d.push((keys[i + 1][1] - keys[i][1]) / Math.max(1e-6, keys[i + 1][0] - keys[i][0]));
  m.push(d[0]);
  for (let i = 1; i < n - 1; i++) m.push(d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2);
  m.push(d[n - 2]);
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
    const a = m[i] / d[i], b = m[i + 1] / d[i];
    const h = a * a + b * b;
    if (h > 9) { const k = 3 / Math.sqrt(h); m[i] = k * a * d[i]; m[i + 1] = k * b * d[i]; }
  }
  let i = 0;
  while (i < n - 2 && t > keys[i + 1][0]) i++;
  const h = keys[i + 1][0] - keys[i][0], u = (t - keys[i][0]) / h;
  const h00 = 2 * u ** 3 - 3 * u ** 2 + 1, h10 = u ** 3 - 2 * u ** 2 + u, h01 = -2 * u ** 3 + 3 * u ** 2, h11 = u ** 3 - u ** 2;
  return h00 * keys[i][1] + h10 * h * m[i] + h01 * keys[i + 1][1] + h11 * h * m[i + 1];
}

/** 沿路線的帶狀幾何（貼在地圖上）：u 座標＝弧長／週期（虛線貼圖用） */
function ribbon(pts: [number, number][], len: number[], width: number, period: number, wobble = 0, seed = 1): BufferGeometry {
  const n = pts.length;
  const pos = new Float32Array(n * 2 * 3), uv = new Float32Array(n * 2 * 2);
  const r = seeded(seed);
  let wv = 0;
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
    const dx = b[0] - a[0], dz = b[1] - a[1];
    const d = Math.hypot(dx, dz) || 1;
    const nx = -dz / d, nz = dx / d;
    wv = lerp(wv, (r() - 0.5) * 2, 0.25);
    const w = width * (1 + wobble * wv) / 2;
    const x = pts[i][0] + MAP_X, z = pts[i][1];
    pos.set([x + nx * w, 0, z + nz * w, x - nx * w, 0, z - nz * w], i * 6);
    uv.set([len[i] / period, 1, len[i] / period, 0], i * 4);
  }
  const idx: number[] = [];
  for (let i = 0; i < n - 1; i++) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(pos, 3));
  g.setAttribute('uv', new BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

function dashTexture(color: string): CanvasTexture {
  const [c, g] = makeCanvas(128, 16);
  g.fillStyle = color;
  g.beginPath(); g.roundRect(4, 2, 76, 12, 6); g.fill();
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = RepeatWrapping;
  return t;
}

function pencilTexture(): CanvasTexture {
  const [c, g] = makeCanvas(256, 16);
  const r = seeded(77);
  g.fillStyle = 'rgba(78,70,64,0.92)';
  g.fillRect(0, 3, 256, 10);
  for (let i = 0; i < 700; i++) { g.fillStyle = `rgba(${r() < 0.5 ? '150,140,130' : '50,44,40'},${0.25 + r() * 0.3})`; g.fillRect(r() * 256, 3 + r() * 10, 1 + r() * 3, 1); }
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = RepeatWrapping;
  return t;
}

/** 聚光：柔和放射漸層（加色） */
export function haloTexture(): CanvasTexture {
  const [c, g] = makeCanvas(256, 256);
  const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, 'rgba(255,246,222,0.95)');
  gr.addColorStop(0.45, 'rgba(255,236,196,0.55)');
  gr.addColorStop(1, 'rgba(255,230,180,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 256, 256);
  return finishTexture(new CanvasTexture(c));
}

// ------------------------------------------------------------------ 鏡位

/** 第四幕紙上的路的鏡位（gate 景也登記同名的 a4_map_top，換景那一刻畫面完全相同） */
export const A4_MAP_CAMERAS: Record<string, CameraPreset> = {
  // 俯視鏡位都在台口裡面（z < 4）：台口外的高鏡位會看到台口上緣與摺幕
  /** 俯視（a4_c002 街道摺平後；a4_c008 回街景前） */
  a4_map_top: { pos: [-5.2, 20.5, 2.4], target: [-5.2, 0, -0.4], fov: 20 },
  /** 俯視整張地圖（a4_c003 起點；小車在左下支路）。G6 精修：畫面下緣往上收（下緣在地面 z≈3.32），
   *  台口左側收攏的布幕摺頁（z 3.43–4.0、x −8.35～−7.35）不再從左下角露出來；小車起點跟著往上移（ACTUAL[0]） */
  a4_map: { pos: [-4.3, 14.6, 3.25], target: [-4.3, 0, 0.75], fov: 20 },
  /** 小車偏離、凍結（看路口、停止線與斑馬線） */
  a4_map_cross: { pos: [-1.7, 10.6, 3.3], target: [-1.7, 0, 1.25], fov: 20 },
  /** 剪影幕從地圖上立起來（台口裡面、斜看；之後切到正面 a4_sil） */
  a4_map_rise: { pos: [-1.6, 7.2, 3.85], target: [-1.6, 1.5, -1.1], fov: 20 },
  /** 低一點的斜看（a4_c008 剪影幕收回地圖、地圖變回街道；鏡頭在台口外但低於台口上緣） */
  a4_map_low: { pos: [-1.8, 6.2, 13.8], target: [-1.8, 0.3, 0], fov: 20 },
  /** 剪影幕正面（a4_c004）：G5 修正第 1 輪拉近、放平，整個畫面都是背光的幕（下緣不再露出地圖；剪影在字幕區之上） */
  a4_sil: { pos: [-2.1, 2.55, 13.25], target: [-2.1, 2.55, -0.75], fov: 20 },
};

// ------------------------------------------------------------------ 景

/** 立體書小屋（u, 鉸鏈 v, 圖, 寬, 在 set 進度中的立起區間） */
const POPS: [number, number, string, number, number, number][] = [
  [-7.3, -1.35, 'house-a', 1.8, 0.05, 0.4], [-5.95, -1.2, 'tree', 0.95, 0.12, 0.45], [-4.6, -1.35, 'house-b', 1.8, 0.15, 0.5],
  [-3.15, -1.2, 'tree', 0.95, 0.2, 0.55], [-1.6, -1.35, 'house-c', 2.0, 0.25, 0.6], [1.1, -1.35, 'house-d', 1.6, 0.3, 0.65],
  [2.35, -1.15, 'tree', 0.95, 0.35, 0.7], [3.55, -0.95, 'gatepost', 0.3, 0.42, 0.72], [5.25, -0.95, 'gatepost', 0.3, 0.45, 0.75],
  [3.7, -2.5, 'tree', 0.95, 0.4, 0.74], [6.2, -3.05, 'school', 4.6, 0.45, 0.85], [8.4, -2.0, 'tree', 0.95, 0.55, 0.9],
  [WALKER_UV[0], WALKER_UV[1], 'walker', 0.42, 0.6, 0.95],
];

/** 剪影幕：鉸鏈（世界）與尺寸；剪影在幕上的位置（幕的左下角為原點） */
export const SCREEN = { x: -1.5, z: -0.75, w: 11.0, h: 5.2 };
const SIL = {
  ground: { x: 0.17, y: 1.3, w: 10.66 },
  car: { x: 1.3, y: 1.73, w: 3.4 },
  walker: { x: 7.6, y: 1.77, w: 0.95 },
};
/** 聚光中心（幕上座標）與半徑 */
const SPOTS: Record<string, [number, number, number]> = { driver: [3.48, 2.9, 1.0], passenger: [2.7, 2.85, 0.92], walker: [8.08, 2.75, 1.35] };

/** 立體書小屋立好時往後仰的角度（弧度；俯視鏡頭下才看得到正面） */
const POP_TILT = 0.68;

function popEase(u: number): number {
  return u <= 0 ? 0 : u >= 1 ? 1 : u < 0.78 ? 1.06 * (1 - Math.pow(1 - u / 0.78, 3)) : 1.06 - 0.06 * ((u - 0.78) / 0.22);
}

export function buildA4Roadmap(ctx: SetContext): BuiltSet {
  const group = new Group();
  group.name = 'set:a4_roadmap';
  const mats: Material[] = [];
  const report: string[] = [];
  const img = (n: string): HTMLImageElement | undefined => {
    const im = ctx.image(`sets/a4_roadmap/set-a4map_${n}`);
    if (!im) report.push(`景 a4_roadmap：缺圖 set-a4map_${n}`);
    return im;
  };
  const keep = (m: Mesh | null): Mesh | null => { if (m) mats.push(m.material as Material); return m; };

  // 桌面（深牛皮紙）與後牆（暗，剪影幕亮起時四周是暗的劇場）
  {
    const [c, g] = makeCanvas(1024, 512);
    g.fillStyle = '#7d5e40'; g.fillRect(0, 0, 1024, 512);
    fibers(g, 1024, 512, 401, 1.5);
    const t = finishTexture(new CanvasTexture(c));
    t.wrapS = t.wrapT = RepeatWrapping; t.repeat.set(4, 3);
    const mat = new MeshStandardMaterial({ map: t, roughness: 0.95, metalness: 0 });
    mats.push(mat);
    const floor = new Mesh(new PlaneGeometry(60, 40), mat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(MAP_X, 0, -4);
    floor.receiveShadow = true;
    floor.renderOrder = LAYER.backdrop.order + 1;
    group.add(floor);
    const [c2, g2] = makeCanvas(1024, 512);
    g2.fillStyle = '#4a3a2c'; g2.fillRect(0, 0, 1024, 512);
    fibers(g2, 1024, 512, 403, 1.2);
    const t2 = finishTexture(new CanvasTexture(c2));
    const wm = new MeshStandardMaterial({ map: t2, roughness: 0.96, metalness: 0 });
    mats.push(wm);
    const wall = new Mesh(new PlaneGeometry(60, 26), wm);
    wall.position.set(MAP_X, 12, -9);
    wall.renderOrder = LAYER.backdrop.order;
    group.add(wall);
  }
  // 地圖
  const mapImg = img('map');
  let mapMat: MeshStandardMaterial | null = null;
  if (mapImg) {
    const t = finishTexture(new CanvasTexture(mapImg as unknown as HTMLCanvasElement));
    t.minFilter = LinearMipmapLinearFilter;
    mapMat = new MeshStandardMaterial({ map: t, roughness: 0.94, metalness: 0 });
    mats.push(mapMat);
    const m = new Mesh(new PlaneGeometry(MAP_W, MAP_H), mapMat);
    m.rotation.x = -Math.PI / 2;
    m.position.set(MAP_X, MAP_Y, 0);
    m.receiveShadow = true;
    m.renderOrder = LAYER.backdrop.order + 2;
    group.add(m);
  }
  // 原點的地圖補片（G6 精修）：引擎 stage.ts 給程式角色（折折）的接觸陰影放在 root 位置＝永遠在 (0, 0.012, 0.05)，
  // 和地圖同高、z-fighting 成斑馬線旁一條灰色殘影（a4_c002 換景後折折還在名冊上）。用同一張地圖貼圖、同樣的 UV、
  // 不透明、高一點點（寫深度）蓋住它；和 gate 景的 zzpatch 同一個做法，本景一直開著（補片和底下的地圖一模一樣）
  if (mapMat) {
    const P = { x0: -0.45, x1: 0.45, z0: -0.32, z1: 0.42 };
    const pg = new PlaneGeometry(P.x1 - P.x0, P.z1 - P.z0);
    const pos = pg.attributes.position, uv = pg.attributes.uv;
    const cx = (P.x0 + P.x1) / 2, cz = (P.z0 + P.z1) / 2;
    for (let k = 0; k < pos.count; k++) {
      const wx = cx + pos.getX(k), wz = cz - pos.getY(k);          // 平面轉 −90°：本地 y → 世界 −z
      uv.setXY(k, (wx - MAP_X + MAP_W / 2) / MAP_W, (0 - wz + MAP_H / 2) / MAP_H);
    }
    uv.needsUpdate = true;
    const pm = mapMat.clone();
    mats.push(pm);
    const patch = new Mesh(pg, pm);
    patch.name = 'a4:zzPatch';
    patch.rotation.x = -Math.PI / 2;
    patch.position.set(cx, MAP_Y + 0.004, cz);
    patch.receiveShadow = true;
    patch.renderOrder = LAYER.backdrop.order + 3;
    group.add(patch);
  }
  // 地圖淡成校門口地面（a4_c008 回街景前；gate 景同一張地面圖、同一位置）
  const streetImg = ctx.image('sets/gate/set-gate_floor');
  let streetMat: MeshStandardMaterial | null = null;
  if (streetImg) {
    const t = finishTexture(new CanvasTexture(streetImg as unknown as HTMLCanvasElement));
    streetMat = new MeshStandardMaterial({ map: t, transparent: true, opacity: 0, depthWrite: false, roughness: 0.95, metalness: 0, color: new Color('#fff6e6') });
    mats.push(streetMat);
    const m = new Mesh(new PlaneGeometry(24, 10), streetMat);
    m.rotation.x = -Math.PI / 2;
    m.position.set(0, MAP_Y + 0.03, 0);
    m.renderOrder = LAYER.backdrop.order + 8;
    m.name = 'a4:street';
    group.add(m);
  }
  // 預定路線（虛線，深青綠）與終點小圈；鉛筆偏移線
  const plan = planPoints();
  const planLen = polyLen(plan);
  const planGeo = ribbon(plan, planLen, 0.085, 0.3);
  const planMat = new MeshBasicMaterial({ map: dashTexture('#2f7a80'), alphaTest: 0.5, side: DoubleSide });
  const planMesh = new Mesh(planGeo, planMat);
  planMesh.position.y = MAP_Y + 0.006;
  planMesh.renderOrder = LAYER.backdrop.order + 4;
  group.add(planMesh);
  const ring = new Mesh(new PlaneGeometry(0.26, 0.26), new MeshBasicMaterial({ map: (() => { const [c, g] = makeCanvas(64, 64); g.strokeStyle = '#2f7a80'; g.lineWidth = 9; g.beginPath(); g.arc(32, 32, 24, 0, Math.PI * 2); g.stroke(); return finishTexture(new CanvasTexture(c)); })(), alphaTest: 0.5 }));
  ring.rotation.x = -Math.PI / 2;
  const endP = plan[plan.length - 1];
  ring.position.set(endP[0] + MAP_X + 0.1, MAP_Y + 0.007, endP[1]);
  ring.renderOrder = LAYER.backdrop.order + 4;
  group.add(ring);
  const act = spline(ACTUAL);
  const trailGeo = ribbon(act.pts, act.len, 0.06, 1.3, 0.25, 9);
  const trailMat = new MeshBasicMaterial({ map: pencilTexture(), alphaTest: 0.35, side: DoubleSide });
  const trail = new Mesh(trailGeo, trailMat);
  trail.position.y = MAP_Y + 0.009;
  trail.renderOrder = LAYER.backdrop.order + 5;
  group.add(trail);
  // 紙剪小車（俯視，平躺在地圖上）＋影子：車身剪影的 alpha 羽化（G5 修正第 1 輪：原本是一張長方形半透明卡片）
  // 影子跟著車子轉向，偏移量固定在畫面右下（世界 +x、+z 約 0.022＝俯視鏡位 6–8 px），不透明度 0.25
  const carHolder = new Group();
  const carImg = img('car');
  const car = keep(imagePlane(carImg, 1.0));
  const shadowHolder = new Group();
  if (car && carImg) {
    car.geometry.translate(0, -(car.userData.h as number) / 2, 0);
    car.rotation.x = -Math.PI / 2;
    car.position.y = 0.05;
    car.castShadow = true;
    car.renderOrder = LAYER.mid.order + 50;
    carHolder.add(car);
    const pad = 16;
    const [c, g] = makeCanvas(carImg.naturalWidth + pad * 2, carImg.naturalHeight + pad * 2);
    g.filter = 'blur(6px)';
    g.drawImage(carImg, pad, pad);
    g.filter = 'none';
    g.globalCompositeOperation = 'source-in';
    g.fillStyle = '#2a1b10';
    g.fillRect(0, 0, c.width, c.height);
    const sm = new MeshBasicMaterial({ map: finishTexture(new CanvasTexture(c)), transparent: true, opacity: 0.25, depthWrite: false });
    mats.push(sm);
    const k = 1.0 / carImg.naturalWidth;
    const sh = new Mesh(new PlaneGeometry(c.width * k, c.height * k), sm);
    sh.rotation.x = -Math.PI / 2;
    sh.position.y = 0.012;
    sh.renderOrder = LAYER.backdrop.order + 6;
    shadowHolder.add(sh);
  }
  group.add(shadowHolder, carHolder);
  // 立體書小屋
  const pops: { g: Group; from: number; to: number; walker: boolean }[] = [];
  for (const [u, v, name, w, from, to] of POPS) {
    const m = keep(imagePlane(img(name), w));
    if (!m) continue;
    m.castShadow = false;
    m.receiveShadow = true;
    m.renderOrder = LAYER.mid.order + 10 + Math.round(v * 2 + 10);
    const g = new Group();
    g.position.set(u + MAP_X, MAP_Y, v);
    g.add(m);
    group.add(g);
    pops.push({ g, from, to, walker: name === 'walker' });
  }
  // 剪影幕（鉸鏈在幕底邊；立起前是一條線）
  const scr = new Group();
  scr.position.set(SCREEN.x, MAP_Y, SCREEN.z);
  group.add(scr);
  const scrInner = new Group();
  scrInner.position.x = -SCREEN.w / 2;
  scr.add(scrInner);
  const screenMesh = imagePlane(img('screen'), SCREEN.w, { basic: true });
  if (screenMesh) { screenMesh.position.x = SCREEN.w / 2; screenMesh.renderOrder = LAYER.mid.order + 60; scrInner.add(screenMesh); }
  const halo = haloTexture();
  const spotMeshes: Record<string, Mesh> = {};
  for (const [k, [x, y, r]] of Object.entries(SPOTS)) {
    const m = new Mesh(new PlaneGeometry(r * 2, r * 2), new MeshBasicMaterial({ map: halo, transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
    m.position.set(x, y, 0.02);
    m.renderOrder = LAYER.mid.order + 61;
    scrInner.add(m);
    spotMeshes[k] = m;
  }
  // 剪影：背光亮起才看得到（影子戲：燈從後面照才有影子）；幕立起時是一張空白的紙，亮度不會一帶一帶掃過畫面
  const silMats: MeshBasicMaterial[] = [];
  for (const [k, s] of Object.entries(SIL)) {
    const m = imagePlane(img(`sil-${k}`), s.w, { basic: true, transparent: true });
    if (!m) continue;
    m.position.set(s.x + s.w / 2, s.y, 0.045);
    m.renderOrder = LAYER.mid.order + 62;
    scrInner.add(m);
    silMats.push(m.material as MeshBasicMaterial);
  }

  return {
    group, materials: mats, report, cameras: A4_MAP_CAMERAS,
    landmarks: { a4Car: { x0: -1, x1: -1, y: 0, z: 0 } },
    update({ world, tl, t }) {
      // 立體書小屋：從地圖上長出來（高度由 0 長到 1，帶一點點往後仰再回正）
      const screenUp = trackValue(tl, 'screen', t, 0);
      for (const p of pops) {
        const u = clamp((world.set - p.from) / Math.max(1e-6, p.to - p.from));
        let e = popEase(u);
        if (p.walker) e *= 1 - clamp(screenUp * 3);
        p.g.visible = e > 0.002;
        p.g.scale.set(1, Math.max(0.001, e), 1);
        // 俯視鏡頭下看得到：立好時往後仰 POP_TILT（像立體書的紙片斜斜立著），立起時從更後仰轉回來
        p.g.rotation.x = -POP_TILT - (1 - Math.min(1, e)) * 0.4;
      }
      // 路線
      const planK = trackValue(tl, 'plan', t, 0, 'linear');
      planGeo.setDrawRange(0, Math.floor(clamp(planK) * (plan.length - 1)) * 6);
      ring.visible = planK > 0.98;
      // 小車：沿實際路線（keys＝[時間, 路線點序號]）
      let s = 0;
      for (const e of trackOf(tl)) {
        if (e.do !== 'car') continue;
        const keys = (Array.isArray(e.p.keys) ? e.p.keys : []) as [unknown, number][];
        const ks: [number, number][] = keys.map(([tr, k]) => {
          const i = Math.floor(clamp(k, 0, ACTUAL.length - 1)), f = k - i;
          const s0 = act.ctrlS[i], s1 = act.ctrlS[Math.min(ACTUAL.length - 1, i + 1)];
          return [refTime(tl, tr), lerp(s0, s1, f)];
        });
        s = monotone(ks, t);
      }
      const carPop = clamp((world.set - 0.5) / 0.35);
      const smp = sampleAt(act.pts, act.len, s);
      carHolder.position.set(smp.p[0] + MAP_X, MAP_Y, smp.p[1]);
      carHolder.rotation.y = -Math.atan2(smp.dir[1], smp.dir[0]);
      carHolder.scale.setScalar(Math.max(0.001, popEase(carPop)));
      carHolder.visible = carPop > 0.002;
      shadowHolder.position.set(carHolder.position.x + 0.022, MAP_Y, carHolder.position.z + 0.022);
      shadowHolder.rotation.y = carHolder.rotation.y;
      shadowHolder.scale.copy(carHolder.scale);
      shadowHolder.visible = carHolder.visible;
      // 鉛筆線：畫到車尾
      const tail = Math.max(0, s - 0.42);
      let n = 0;
      while (n < act.len.length - 1 && act.len[n + 1] <= tail) n++;
      trailGeo.setDrawRange(0, tail > 0.02 ? n * 6 : 0);
      // 剪影幕：高度從 0 長出、同時從往後仰轉正
      const e = popEase(screenUp);
      scr.visible = screenUp > 0.002;
      scr.scale.set(1, Math.max(0.001, e), 1);
      scr.rotation.x = -(1 - Math.min(1, e)) * 0.9;
      const glow = trackValue(tl, 'glow', t, 0);
      if (screenMesh) (screenMesh.material as MeshBasicMaterial).color.setScalar(lerp(0.58, 1.0, glow));
      const silK = clamp((glow - 0.05) / 0.9);
      for (const m of silMats) { m.opacity = silK; m.visible = silK > 0.002; }
      for (const k of Object.keys(spotMeshes)) {
        let v = 0;
        for (const ev of trackOf(tl)) {
          if (ev.do !== 'spot' || (ev.p.target !== k && ev.p.target !== 'all') || t < ev.start) continue;
          const uu = ev.duration > 0 ? clamp((t - ev.start) / ev.duration) : 1;
          v = lerp(v, Number(ev.p.to ?? 1), ease('sine', uu));
        }
        (spotMeshes[k].material as MeshBasicMaterial).opacity = 0.5 * v * glow;
      }
      // 地圖淡成校門口地面
      if (streetMat) streetMat.opacity = trackValue(tl, 'street', t, 0);
    },
  };
}

export const A4_ROADMAP: SetEntry = { title: '紙上的路（第四幕）', cameras: A4_MAP_CAMERAS, build: (ctx) => buildA4Roadmap(ctx) };

/** gate 景用：同一張地圖貼圖（a4_c002 街道摺平後淡入） */
export function mapOverlay(ctx: SetContext): { mesh: Mesh; mat: MeshStandardMaterial } | null {
  const im = ctx.image('sets/a4_roadmap/set-a4map_map');
  if (!im) return null;
  const t: Texture = finishTexture(new CanvasTexture(im as unknown as HTMLCanvasElement));
  t.minFilter = LinearMipmapLinearFilter;
  const mat = new MeshStandardMaterial({ map: t, transparent: true, opacity: 0, depthWrite: false, roughness: 0.94, metalness: 0 });
  const mesh = new Mesh(new PlaneGeometry(MAP_W, MAP_H), mat);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(MAP_X, MAP_Y + 0.02, 0);
  mesh.renderOrder = LAYER.backdrop.order + 8;
  return { mesh, mat };
}
