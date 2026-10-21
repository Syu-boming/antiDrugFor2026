// 資料驅動的通用景（imageSet）：讀 assets/final/sets/<景名>/layout.json，各幕代理多半只要放圖＋寫 layout.json 就能新增景。
// 圖像 id 寫相對於景資料夾的檔名（去副檔名與版本號），例如 "back" → sets/<景名>/back（assets/final/sets/<景名>/back_v01.png）；
// 也可以寫完整 id（含 "/"，例如 bg-workshop-back）。
//
// layout.json（format "antidrug-set/1"）：
// {
//   "format": "antidrug-set/1", "title": "小鎮廣場（放學後）",
//   "wall":  { "image": "back", "width": 21, "y": 0, "z": -3.6, "emissive": 0.32 },          背牆（不立起；底邊在 y）
//   "floor": { "image": "floor", "repeat": [10, 4], "color": "#d8c09a", "z": 2.4, "depth": 12 }, 地板（沒有圖就用 color）
//   "layers": [                                                                                  景片（依序；後面的在前）
//     { "id": "arcade", "image": "arcade", "x": -4.2, "y": 0, "z": -2.4, "width": 6.0,           寬或高擇一（另一邊依圖比例）
//       "layer": "far", "order": 0, "popup": [0.1, 0.3], "thick": 5, "parallax": 0,
//       "shadow": true, "emissive": 0, "flipX": false, "rotationY": 0, "opacity": 1 }
//   ],
//   "grade":  { "preset": "day_warm", "tint": "#fff6e8", "saturation": 1 },                    FX8 色彩分級（tint 乘在景片顏色上）
//   "light":  { "key": [-7, 13, 16], "keyColor": "#ffe9c8", "keyIntensity": 1, "hemiSky": "#fff3dc", "hemiGround": "#6b5846" },
//   "marks":  { "xiaoqing": { "x": 1.8, "z": 0.4 } },                                            角色站位（名冊沒寫 x、z 時用）
//   "landmarks": { "bench": { "x0": -1, "x1": 1, "y": 0.8, "z": -0.5 } },                       量測用地標
//   "cameras":   { "plaza_wide": { "pos": [0, 3.6, 27], "target": [0, 3.2, 0], "fov": 20 } }    這個景的鏡位
// }
// - popup [from, to]：在 set.popup／set.fold 的進度（0–1）中，這張景片從平躺到立好的區間（立起順序與時間）；省略＝一直站著。
// - layer：backdrop／far／mid／fore（層序 src/stage/layers.ts LAYER；同層內再加 order）。
// - parallax：鏡頭橫移時這張景片額外跟著移動的比例（0＝不動，0.5＝跟一半；遠景用，讓背景不必做得很大）。
// - thick：往右下烘進的卡紙厚度（像素，預設 5，0＝不加）；shadow：投影與受影（預設 true）。
// - opacity < 1：半透明（不寫深度，只靠層序；霧、光、和紙用）。
import {
  CanvasTexture, Color, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshStandardMaterial, PlaneGeometry, RepeatWrapping, type Material,
} from 'three';
import { fibers, finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import type { BuiltSet, PopPiece, SetContext, SetEntry, SetLandmark, SetLight } from './types';

export const SET_LAYOUT_FORMAT = 'antidrug-set/1';

export interface LayoutLayer {
  id: string;
  image?: string;
  /** 沒有圖時的紙色（平塗紙片＋纖維） */
  color?: string;
  x: number;
  y?: number;
  z: number;
  width?: number;
  height?: number;
  scale?: number;
  layer?: 'backdrop' | 'far' | 'mid' | 'fore';
  order?: number;
  popup?: [number, number] | null;
  thick?: number;
  parallax?: number;
  shadow?: boolean;
  emissive?: number;
  flipX?: boolean;
  rotationY?: number;
  opacity?: number;
}

export interface SetLayout {
  format: string;
  title?: string;
  wall?: { image?: string; color?: string; width?: number; height?: number; y?: number; z?: number; emissive?: number };
  floor?: { image?: string; color?: string; repeat?: [number, number]; z?: number; depth?: number; width?: number };
  layers?: LayoutLayer[];
  grade?: { preset?: string; tint?: string; saturation?: number };
  light?: SetLight;
  marks?: Record<string, { x: number; z: number }>;
  landmarks?: Record<string, SetLandmark>;
  cameras?: Record<string, CameraPreset>;
}

/** FX8 色彩分級預設（tint 乘在景片顏色上；角色、操偶線、字幕、題卡不受影響）。節拍表 0.4 色彩腳本 */
export const GRADE_PRESETS: Record<string, { tint: string; saturation: number }> = {
  neutral: { tint: '#ffffff', saturation: 1 },
  morning_gold: { tint: '#fff0d4', saturation: 1.02 },
  day_warm: { tint: '#fff6e6', saturation: 1 },
  cool_shadow: { tint: '#eef0f4', saturation: 0.9 },
  dusk_purple: { tint: '#ebdff0', saturation: 0.92 },
  classroom_afternoon: { tint: '#fbf3e4', saturation: 0.98 },
  kraft_map: { tint: '#f6ead6', saturation: 0.95 },
  silhouette: { tint: '#d9cfc4', saturation: 0.7 },
  muted: { tint: '#f2eee8', saturation: 0.8 },
  hospital_evening: { tint: '#ece6ee', saturation: 0.9 },
  night_warm: { tint: '#f4dfc4', saturation: 1 },
  memory_faded: { tint: '#f1ebe2', saturation: 0.6 },
};

const KRAFT = '#7a5a3c';

function layoutId(name: string): string { return `sets/${name}/layout`; }

/** 依景名讀 layout.json（沒有就回傳 undefined） */
export function readLayout(ctx: Pick<SetContext, 'json'>, name: string): SetLayout | undefined {
  const raw = ctx.json<SetLayout>(layoutId(name));
  return raw && typeof raw === 'object' ? raw : undefined;
}

function img(ctx: SetContext, name: string, id?: string): HTMLImageElement | undefined {
  if (!id) return undefined;
  return (id.includes('/') ? ctx.image(id) : undefined) ?? ctx.image(`sets/${name}/${id}`) ?? ctx.image(id);
}

/** 圖像景片：原圖（可降彩）＋往右下烘進卡紙厚度 */
function imageTexture(image: HTMLImageElement, thick: number, saturation: number, flipX: boolean): CanvasTexture {
  const W = image.naturalWidth, H = image.naturalHeight;
  const pad = thick > 0 ? thick + 2 : 0;
  const [c, g] = makeCanvas(W + pad, H + pad);
  const [art, ag] = makeCanvas(W, H);
  if (saturation !== 1) ag.filter = `saturate(${saturation})`;
  if (flipX) { ag.translate(W, 0); ag.scale(-1, 1); }
  ag.drawImage(image, 0, 0);
  if (thick > 0) {
    const [sil, sg] = makeCanvas(W, H);
    sg.drawImage(art, 0, 0);
    sg.globalCompositeOperation = 'source-in';
    sg.fillStyle = KRAFT;
    sg.fillRect(0, 0, W, H);
    for (let k = thick; k >= 1; k--) g.drawImage(sil, k * 0.75, k);
  }
  g.drawImage(art, 0, 0);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

function colorTexture(color: string, w: number, h: number, seed: number): CanvasTexture {
  const W = Math.max(16, Math.min(1024, Math.round(w * 100))), H = Math.max(16, Math.min(1024, Math.round(h * 100)));
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = color;
  g.fillRect(0, 0, W, H);
  fibers(g, W, H, seed, 1.2);
  return finishTexture(new CanvasTexture(c));
}

export function buildImageSet(ctx: SetContext, layout: SetLayout): BuiltSet {
  const name = ctx.name;
  const group = new Group();
  group.name = `set:${name}`;
  const mats: Material[] = [];
  const pieces: PopPiece[] = [];
  const report: string[] = [];
  const grade = { ...(GRADE_PRESETS[layout.grade?.preset ?? 'neutral'] ?? GRADE_PRESETS.neutral), ...(layout.grade?.tint ? { tint: layout.grade.tint } : {}), ...(layout.grade?.saturation !== undefined ? { saturation: layout.grade.saturation } : {}) };
  const tint = new Color(grade.tint);
  const parallax: { obj: Group; x0: number; k: number }[] = [];

  // ---- 背牆
  const WALL_Z = layout.wall?.z ?? -3.6;
  {
    const w0 = layout.wall ?? {};
    const im = img(ctx, name, w0.image);
    if (w0.image && !im) report.push(`景 ${name}：缺背牆圖 ${w0.image}`);
    const wallW = w0.width ?? 21;
    const wallH = w0.height ?? (im ? wallW * im.naturalHeight / im.naturalWidth : 13);
    const tex = im ? imageTexture(im, 0, grade.saturation, false) : colorTexture(w0.color ?? '#e6d3b3', 18, 8, 201);
    const mat = new MeshStandardMaterial({ map: tex, roughness: 0.96, metalness: 0 });
    // 背牆自發光：舞台燈調暗或降彩時，兒童身後仍夠亮（D-G2-06，同 workshop_g4）
    mat.emissiveMap = tex;
    mat.emissive.copy(tint);
    mat.emissiveIntensity = w0.emissive ?? 0.32;
    mat.color.copy(tint).multiplyScalar(0.86);
    mats.push(mat);
    const wall = new Mesh(new PlaneGeometry(wallW, wallH), mat);
    wall.position.set(0, (w0.y ?? -0.02) + wallH / 2, WALL_Z);
    wall.receiveShadow = true;
    wall.renderOrder = LAYER.backdrop.order;
    group.add(wall);
  }
  // ---- 地板
  {
    const f0 = layout.floor ?? {};
    const im = img(ctx, name, f0.image);
    if (f0.image && !im) report.push(`景 ${name}：缺地板圖 ${f0.image}`);
    const tex = im ? finishTexture(new CanvasTexture(im)) : colorTexture(f0.color ?? '#c9aa7e', 10, 4, 203);
    tex.wrapS = tex.wrapT = RepeatWrapping;
    const rep = f0.repeat ?? (im ? [10, 4] : [3, 1.5]);
    tex.repeat.set(rep[0], rep[1]);
    const mat = new MeshStandardMaterial({ map: tex, roughness: 0.95, metalness: 0, color: tint.clone() });
    mats.push(mat);
    const depth = f0.depth ?? 12;
    const front = f0.z ?? WALL_Z + 12;
    const floor = new Mesh(new PlaneGeometry(f0.width ?? 32, depth), mat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(0, 0, front - depth / 2);
    floor.receiveShadow = true;
    floor.renderOrder = LAYER.backdrop.order + 1;
    group.add(floor);
  }
  // ---- 景片
  (layout.layers ?? []).forEach((L, i) => {
    const im = img(ctx, name, L.image);
    if (L.image && !im) report.push(`景 ${name}：缺景片圖 ${L.image}（${L.id}）`);
    if (!im && !L.color) return;
    const aspect = im ? im.naturalWidth / im.naturalHeight : (L.width && L.height ? L.width / L.height : 1);
    const sc = L.scale ?? 1;
    let w = L.width ?? (L.height ? L.height * aspect : 2);
    let h = L.height ?? w / aspect;
    w *= sc; h *= sc;
    const thick = L.thick ?? 5;
    const tex = im ? imageTexture(im, thick, grade.saturation, !!L.flipX) : colorTexture(L.color!, w, h, 300 + i);
    // 卡紙厚度往右下多了 pad 像素：幾何同比例放大，讓原圖部分的尺寸不變
    const padK = im && thick > 0 ? [(im.naturalWidth + thick + 2) / im.naturalWidth, (im.naturalHeight + thick + 2) / im.naturalHeight] : [1, 1];
    const translucent = L.opacity !== undefined && L.opacity < 1;
    const mat = new MeshStandardMaterial({
      map: tex, side: DoubleSide, roughness: 0.92, metalness: 0, color: tint.clone(),
      ...(translucent ? { transparent: true, opacity: L.opacity, depthWrite: false } : { alphaTest: 0.5, alphaToCoverage: ctx.alphaToCoverage }),
    });
    if (L.emissive) { mat.emissiveMap = tex; mat.emissive.copy(tint); mat.emissiveIntensity = L.emissive; }
    mats.push(mat);
    const geo = new PlaneGeometry(w * padK[0], h * padK[1]);
    // 底邊中央是鉸鏈（原圖部分的底邊對齊 y；卡紙厚度多出來的往右下）
    geo.translate((w * padK[0] - w) / 2, h - (h * padK[1]) / 2, 0);
    const m = new Mesh(geo, mat);
    const base = LAYER[L.layer ?? 'mid'].order;
    m.renderOrder = base + (L.order ?? i);
    m.castShadow = L.shadow !== false && !translucent;
    m.receiveShadow = L.shadow !== false;
    const hinge = new Group();
    hinge.name = `pop:${L.id}`;
    hinge.position.set(L.x, L.y ?? 0, L.z);
    hinge.rotation.y = L.rotationY ?? 0;
    hinge.add(m);
    if (L.parallax) {
      const holder = new Group();
      holder.add(hinge);
      group.add(holder);
      parallax.push({ obj: holder, x0: 0, k: L.parallax });
    } else group.add(hinge);
    if (L.popup) pieces.push({ hinge, from: L.popup[0], to: L.popup[1], name: L.id });
  });

  return {
    group, pieces, materials: mats, marks: layout.marks, landmarks: layout.landmarks, light: layout.light, cameras: layout.cameras, report,
    update: parallax.length ? ({ world }) => { for (const p of parallax) p.obj.position.x = p.x0 + world.camera.target[0] * p.k; } : undefined,
  };
}

/** 由 layout.json 建景（registry 找不到景名、但素材裡有 sets/<景名>/layout 時用） */
export function imageSetEntry(layout: SetLayout): SetEntry {
  return { title: layout.title ?? '資料驅動景', cameras: layout.cameras, build: (ctx) => buildImageSet(ctx, layout) };
}
