// 圖片分件紙偶：從 parts.json（tools/master_cut.py 的輸出格式，例如 assets/parts/ale_v03/parts.json）
// 與各部件 PNG 建立 RigSpec。正面視角（front）：坐姿以大腿透視縮短表現，腿不做側面 IK。
//
// 載入時的前處理（imageproc.ts，確定性）：
// 1. 依 bbox 裁切（每邊留描邊空間）。
// 2. 接縫清除：肩、膝的圓形舌片在前層部件上留下的深色弧線（G2 一般問題第 3 項），
//    只在「舌片圓內、而且下面有後層部件」的邊緣帶，把深色線換成內側布料色；外輪廓的線保留。
// 3. 顏色外擴（避免透明邊取樣出黑邊）。
// 4. 外輪廓背板：白色紙芯邊＋深色卡紙側邊（Rig 把所有背板畫在所有部件後面＝只描整體外輪廓）。
// 5. 操偶線扣點：有 ale_attach.json 就照它；沒有就由部件外形自動找（手腕背側、手肘外側、膝蓋正面），並量出紙環要包住的肢體寬度。
import { CanvasTexture, LinearMipmapLinearFilter } from 'three';
import type { AnchorName, AnchorSpec, PartSpec, RigSpec } from './rig';
import {
  alphaMask, bleedEdges, cropPixels, distanceField, inpaint, outlineBacking, pixelsToCanvas, DEFAULT_OUTLINE, type OutlineStyle, type Pixels,
} from './imageproc';
import { finishTexture } from './paper';

export interface PartsJson {
  canvas: [number, number];
  pivots: Record<string, [number, number]>;
  tab_radius?: Record<string, number>;
  layers: string[];
  parts: Record<string, { file: string; bbox: [number, number, number, number]; parent: string | null; joint: string | null; pivot: [number, number] | null; tab_radius?: number | null }>;
}

/** ale_attach.json：扣點（部件圖的像素座標；部件圖是整張畫布時＝母版座標） */
export type AttachJson = Partial<Record<'wrist_back' | 'elbow_out' | 'knee_front', { part: string; px?: [number, number]; local?: [number, number]; width?: number }>>;

/** 素材代理 v04 分件格式（assets/final/rig/ale_rig.json）：部件圖已裁切，origin_master＝圖左上角在母版上的位置 */
export interface RigJsonV04 {
  master_canvas: [number, number];
  layers_back_to_front: string[];
  parts: Record<string, { file: string; image_id: string; size: [number, number]; origin_master: [number, number]; parent: string | null; joint: string | null; pivot_master: [number, number] | null; tab_radius?: number | null }>;
  fix_log?: unknown;
}

/** v04 格式 → PartsJson（母版座標）＋各部件圖的原點 */
export function partsFromRigJson(j: RigJsonV04): { parts: PartsJson; origins: Record<string, [number, number]>; imageIds: Record<string, string>; variants: Record<string, string> } {
  const parts: PartsJson['parts'] = {};
  const pivots: Record<string, [number, number]> = {};
  const origins: Record<string, [number, number]> = {};
  const imageIds: Record<string, string> = {};
  const variants: Record<string, string> = {};
  const tab: Record<string, number> = {};
  for (const [id, p] of Object.entries(j.parts)) {
    origins[id] = p.origin_master;
    imageIds[id] = p.image_id;
    const m = /^(.+?)_([a-z]+)$/.exec(id);
    if (m && j.parts[m[1]] && !j.layers_back_to_front.includes(id)) { variants[id] = m[1]; continue; } // 例如 head_worried
    const [ox, oy] = p.origin_master;
    parts[id] = { file: p.image_id, bbox: [ox, oy, ox + p.size[0], oy + p.size[1]], parent: p.parent, joint: p.joint, pivot: p.pivot_master, tab_radius: p.tab_radius };
    if (p.joint && p.pivot_master) pivots[p.joint] = p.pivot_master;
    if (p.joint && p.tab_radius) tab[p.joint] = p.tab_radius;
  }
  return { parts: { canvas: j.master_canvas, pivots, tab_radius: tab, layers: j.layers_back_to_front, parts }, origins, imageIds, variants };
}

export interface ImageRigOptions {
  id: string;
  parts: PartsJson;
  /** 部件圖與它在母版上的原點（整張畫布的圖原點是 [0,0]） */
  image: (partId: string, file: string) => { img: CanvasImageSource; origin: [number, number] } | undefined;
  /** 同樞紐的替換部件（例如 head_worried → head），預設隱藏，由表演切換 */
  variants?: Record<string, { of: string; bbox: [number, number, number, number] }>;
  /** 站立高度（世界單位，腳底到頭頂） */
  height: number;
  /** 扣操偶線的手臂（A 側）與腿：預設右手、左膝（DECISIONS.md D-G2-04） */
  stringArm?: 'r' | 'l';
  kneeLeg?: 'r' | 'l';
  attach?: AttachJson;
  outline?: OutlineStyle;
  /** 腳踝相對膝蓋的像素位移（parts.json 沒有腳踝） */
  ankleOffset?: Record<'r' | 'l', [number, number]>;
  /** 要清除舌片弧線的關節 */
  seamJoints?: string[];
  /** 鞋底到地面的像素（腳底）；省略時用小腿最低點 */
  floorY?: number;
}

export interface ImageRigResult {
  spec: RigSpec;
  /** 像素 → 紙偶根本地座標 */
  px2root: (x: number, y: number) => [number, number];
  scale: number;
  /** 頭部原圖（臉部換片取膚色用）與頭部樞紐 */
  headImage?: CanvasImageSource;
  headPivotPx: [number, number];
  /** 各關節的像素座標（坐姿、腳踝等計算用） */
  joints: Record<string, [number, number]>;
  timings: Record<string, number>;
}

const PAD = 26;

function limbWidthAt(mask: Uint8Array, w: number, h: number, ox: number, oy: number, px: number, py: number, nx: number, ny: number): { width: number; c0: number; c1: number } {
  // 沿法線方向（nx, ny）兩側找外形邊界
  let c0 = 0, c1 = 0;
  const at = (s: number): boolean => {
    const x = Math.round(px + nx * s - ox), y = Math.round(py + ny * s - oy);
    return x >= 0 && y >= 0 && x < w && y < h && mask[y * w + x] === 1;
  };
  if (!at(0)) return { width: 0, c0: 0, c1: 0 };
  while (c0 > -200 && at(c0 - 1)) c0--;
  while (c1 < 200 && at(c1 + 1)) c1++;
  return { width: c1 - c0, c0, c1 };
}

export function buildImageRig(o: ImageRigOptions): ImageRigResult {
  const t0 = performance.now();
  const P = o.parts;
  const A = o.stringArm ?? 'r', B = A === 'r' ? 'l' : 'r';
  const K = o.kneeLeg ?? 'l', KO = K === 'r' ? 'l' : 'r';
  const st = o.outline ?? DEFAULT_OUTLINE;
  const piv = P.pivots;
  const floorY = o.floorY ?? Math.max(...['shin_r', 'shin_l'].map((k) => P.parts[k]?.bbox[3] ?? 0));
  const topY = Math.min(...Object.values(P.parts).map((p) => p.bbox[1]));
  const s = o.height / (floorY - topY);
  const hip: [number, number] = [(piv.hip_r[0] + piv.hip_l[0]) / 2, (piv.hip_r[1] + piv.hip_l[1]) / 2];
  const ankleOff = o.ankleOffset ?? { r: [-13, 235], l: [5, 235] };
  const joints: Record<string, [number, number]> = { ...piv, hip_c: hip };
  for (const side of ['r', 'l'] as const) joints[`ankle_${side}`] = [piv[`knee_${side}`][0] + ankleOff[side][0], piv[`knee_${side}`][1] + ankleOff[side][1]];
  const px2root = (x: number, y: number): [number, number] => [(x - hip[0]) * s, (floorY - y) * s];

  // ---- 1. 裁切與遮罩（全部換算成母版座標）
  const crops = new Map<string, { px: Pixels; x0: number; y0: number; mask: Uint8Array }>();
  const cropOne = (id: string, file: string, bbox: [number, number, number, number]): void => {
    const got = o.image(id, file);
    if (!got) return;
    const [bx0, by0, bx1, by1] = bbox;
    const x0 = bx0 - PAD, y0 = by0 - PAD;
    const [ox, oy] = got.origin;
    const px = cropPixels(got.img, x0 - ox, y0 - oy, bx1 + PAD - ox, by1 + PAD - oy);
    crops.set(id, { px, x0, y0, mask: alphaMask(px) });
  };
  for (const [id, p] of Object.entries(P.parts)) cropOne(id, p.file, p.bbox);
  for (const [id, v] of Object.entries(o.variants ?? {})) cropOne(id, id, v.bbox);
  const t1 = performance.now();
  const alphaAt = (id: string, x: number, y: number): boolean => {
    const c = crops.get(id);
    if (!c) return false;
    const lx = x - c.x0, ly = y - c.y0;
    return lx >= 0 && ly >= 0 && lx < c.px.width && ly < c.px.height && c.mask[ly * c.px.width + lx] === 1;
  };

  // ---- 2. 接縫清除（肩、膝的舌片弧線）
  const layerIdx = (id: string): number => P.layers.indexOf(id);
  const seamJoints = o.seamJoints ?? ['shoulder_r', 'shoulder_l', 'knee_r', 'knee_l'];
  let seamPx = 0;
  for (const j of seamJoints) {
    const child = Object.entries(P.parts).find(([, p]) => p.joint === j)?.[0];
    if (!child) continue;
    const parent = P.parts[child].parent!;
    const front = layerIdx(parent) > layerIdx(child) ? parent : child;
    const back = front === parent ? child : parent;
    const c = crops.get(front);
    if (!c) continue;
    const [jx, jy] = piv[j];
    const R = (P.tab_radius?.[j] ?? P.parts[child].tab_radius ?? 60) + 10;
    const { px, x0, y0, mask } = c;
    const w = px.width, h = px.height;
    const outside = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) outside[i] = mask[i] ? 0 : 1;
    const dIn = distanceField(outside, w, h); // 內部像素到外形邊界的距離
    const unknown = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (!mask[i] || dIn[i] > 5.5) continue;
        const X = x + x0, Y = y + y0;
        if ((X - jx) ** 2 + (Y - jy) ** 2 > R * R) continue;
        // 下面有後層部件（往外 3 px 也算，涵蓋線條本身）
        if (alphaAt(back, X, Y) || alphaAt(back, X + 3, Y) || alphaAt(back, X - 3, Y) || alphaAt(back, X, Y + 3) || alphaAt(back, X, Y - 3)) { unknown[i] = 1; seamPx++; }
      }
    }
    inpaint(px, unknown, 8, true);
  }
  const t2 = performance.now();

  // ---- 3–4. 外擴、背板、貼圖
  const textures = new Map<string, { map: CanvasTexture; backing: CanvasTexture }>();
  for (const [id, c] of crops) {
    bleedEdges(c.px, 3);
    const back = outlineBacking(c.mask, c.px.width, c.px.height, st);
    const mk = (p: Pixels): CanvasTexture => {
      const t = finishTexture(new CanvasTexture(pixelsToCanvas(p)));
      t.minFilter = LinearMipmapLinearFilter;
      return t;
    };
    textures.set(id, { map: mk(c.px), backing: mk(back) });
  }
  const t3 = performance.now();

  // ---- 5. 部件樹（骨盆中心是虛擬部件；大腿掛在骨盆，不跟著軀幹轉）
  const parts: PartSpec[] = [];
  const pivotPx = (id: string): [number, number] => (id === 'pelvis' ? hip : id.startsWith('ankle_') ? joints[id] : (P.parts[id]?.pivot ?? hip));
  const parentOf = (id: string): string | null => {
    if (id === 'torso') return 'pelvis';
    if (id.startsWith('thigh_')) return 'pelvis';
    return P.parts[id]?.parent ?? null;
  };
  const add = (id: string, parent: string | null, z: number): void => {
    const pp = pivotPx(id);
    const at: [number, number] = parent ? [(pp[0] - pivotPx(parent)[0]) * s, (pivotPx(parent)[1] - pp[1]) * s] : px2root(pp[0], pp[1]);
    const c = crops.get(id), tx = textures.get(id);
    const rect: PartSpec['rect'] = c ? [(c.x0 - pp[0]) * s, (pp[1] - (c.y0 + c.px.height)) * s, c.px.width * s, c.px.height * s] : null;
    parts.push({ id, parent, at, rect, z, map: tx?.map, backing: tx?.backing });
  };
  add('pelvis', null, 0);
  // 依 layers 順序（後 → 前）加入；父部件要先加入，所以先排出拓撲順序
  const order = [...P.layers];
  const added = new Set<string>(['pelvis']);
  let guard = 0;
  while (order.length && guard++ < 100) {
    const id = order.shift()!;
    const par = parentOf(id);
    if (par && !added.has(par)) { order.push(id); continue; }
    add(id, par, layerIdx(id) + 1);
    added.add(id);
  }
  for (const side of ['r', 'l'] as const) add(`ankle_${side}`, `shin_${side}`, 0);
  // 替換部件：掛在原部件的樞紐上（at＝0），層序在原部件前一點點
  for (const [id, v] of Object.entries(o.variants ?? {})) {
    if (!crops.has(id) || !P.parts[v.of]) continue;
    const pp = pivotPx(v.of);
    const c = crops.get(id)!, tx = textures.get(id);
    parts.push({ id, parent: v.of, at: [0, 0], rect: [(c.x0 - pp[0]) * s, (pp[1] - (c.y0 + c.px.height)) * s, c.px.width * s, c.px.height * s], z: layerIdx(v.of) + 1.5, map: tx?.map, backing: tx?.backing });
  }

  // ---- 6. 操偶線扣點
  const anchors: Partial<Record<AnchorName, AnchorSpec>> = {};
  const mkAnchor = (name: AnchorName, part: string, from: string, to: string, t: number, side: 'outer' | 'center', given?: { px?: [number, number]; local?: [number, number]; width?: number }): void => {
    const c = crops.get(part);
    const p0 = joints[from], p1 = joints[to];
    if (!c || !p0 || !p1) return;
    const ax = p1[0] - p0[0], ay = p1[1] - p0[1];
    const len = Math.hypot(ax, ay) || 1;
    const nx = -ay / len, ny = ax / len; // 肢體法線（像素座標）
    let px = p0[0] + ax * t, py = p0[1] + ay * t;
    if (given?.px) { px = given.px[0]; py = given.px[1]; }
    const lw = limbWidthAt(c.mask, c.px.width, c.px.height, c.x0, c.y0, px, py, nx, ny);
    let cx = px + nx * (lw.c0 + lw.c1) / 2, cy = py + ny * (lw.c0 + lw.c1) / 2; // 肢體中心
    if (given?.px) { cx = px; cy = py; }
    void side;
    const pp = pivotPx(part);
    const local: [number, number] = given?.local ?? [(cx - pp[0]) * s, (pp[1] - cy) * s];
    const width = (given?.width ?? (lw.width || 40)) * s;
    // 紙環方向：肢體方向在部件本地座標的角度（像素 y 向下 → 世界 y 向上）
    const axis = Math.atan2(-ay, ax);
    anchors[name] = { part, local, width, axis };
  };
  const at = o.attach ?? {};
  mkAnchor('wrist', `forearm_${A}`, `elbow_${A}`, `wrist_${A}`, 0.84, 'outer', at.wrist_back);
  mkAnchor('elbow', `upper_arm_${A}`, `shoulder_${A}`, `elbow_${A}`, 0.86, 'outer', at.elbow_out);
  mkAnchor('knee', `thigh_${K}`, `hip_${K}`, `knee_${K}`, 0.93, 'center', at.knee_front);

  const spec: RigSpec = {
    id: o.id,
    parts,
    anchors,
    limbs: {
      armA: { upper: `upper_arm_${A}`, lower: `forearm_${A}`, end: `hand_${A}`, bend: A === 'r' ? -1 : 1 },
      armB: { upper: `upper_arm_${B}`, lower: `forearm_${B}`, end: `hand_${B}`, bend: B === 'r' ? -1 : 1 },
      legA: { upper: `thigh_${K}`, lower: `shin_${K}`, end: `ankle_${K}`, bend: 1 },
      legB: { upper: `thigh_${KO}`, lower: `shin_${KO}`, end: `ankle_${KO}`, bend: 1 },
    },
    height: o.height,
    roles: { pelvis: 'pelvis', torso: 'torso', head: 'head', handA: `hand_${A}`, handB: `hand_${B}` },
  };
  return {
    spec, px2root, scale: s, headImage: o.image('head', P.parts.head?.file ?? 'head.png')?.img, headPivotPx: P.parts.head?.pivot ?? piv.neck, joints,
    timings: { crop: t1 - t0, seams: t2 - t1, textures: t3 - t2, seamPx },
  };
}
