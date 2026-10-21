// 開場（a0_c002–a0_c005）的燈籠店：沿用 G4 燈籠店景（buildWorkshopG4，不改它），再疊上開場需要的程式景片。G5 開場＋第一幕代理。
//   - 主燈設計圖（牆上，摺紙貓燈，沒有任何文字）、工作台上空著的主燈底座、門口風鈴、台口上方一串八盞還沒亮的燈
//   - 回憶小窗（a0_c002）：暖杏色手撕邊紙框從畫面外緣收進來＋景片轉暖色（角色不變色）
//   - 小晴的筆記本特寫（a0_c004）：小窗裡的筆記本，竹骨架與問號一筆一筆畫上（程式畫線）
//   - 風鈴（a0_c004 開頭 S6）：輕輕擺幾下停住
// 每格 update 只依（cue、cue 內秒數、鏡頭）決定畫面＝時間的純函式。動作時間錨在台詞上（配音長度改了會跟著移）。
// 素材：assets/final/sets/workshop_a0/*（review/G5/a0/scripts/build_a01_art.py 程式繪製）。
import {
  CanvasTexture, Color, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, Vector3,
  type Material, type PerspectiveCamera,
} from 'three';
import { buildWorkshopG4 } from '../stage/workshop';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER } from '../stage/layers';
import type { CameraPreset } from '../stage/layers';
import type { CueTimeline } from '../cues/timeline';
import { clamp, lerp } from '../util/math';
import type { BuiltSet, SetContext, SetEntry } from './types';

// ───────────────────────────── 共用小工具（square_a1.ts 也用） ─────────────────────────────
export const sine01 = (t: number): number => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t));
/** 台詞時間（秒）：ids 依序找第一句在時間軸上的；which＝'start'｜'end'。都找不到回傳 fallback */
export function lineTime(tl: CueTimeline, ids: string[], which: 'start' | 'end' = 'start', fallback = 0): number {
  for (const id of ids) {
    const l = tl.lines.find((x) => x.line.id === id);
    if (l) return which === 'start' ? l.start : l.end;
  }
  return fallback;
}
/** 圖像景片：底邊中央（或 pivot）為原點；w 或 h 擇一（世界單位） */
export function imagePiece(img: HTMLImageElement | undefined, o: { w?: number; h?: number; pivot?: [number, number]; order: number; emissive?: number; basic?: boolean; transparent?: boolean; shadow?: boolean }, mats: Material[]): Mesh | null {
  if (!img) return null;
  const aspect = img.naturalWidth / img.naturalHeight;
  const w = o.w ?? (o.h ?? 1) * aspect, h = o.h ?? w / aspect;
  const tex = finishTexture(new CanvasTexture(img));
  tex.minFilter = LinearMipmapLinearFilter;
  const mat = o.basic
    ? new MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, side: DoubleSide })
    : new MeshStandardMaterial({ map: tex, side: DoubleSide, roughness: 0.92, metalness: 0, ...(o.transparent ? { transparent: true, depthWrite: false } : { alphaTest: 0.5 }) });
  if (o.emissive && mat instanceof MeshStandardMaterial) { mat.emissiveMap = tex; mat.emissive.setRGB(1, 1, 1); mat.emissiveIntensity = o.emissive; }
  mats.push(mat);
  const geo = new PlaneGeometry(w, h);
  const [px, py] = o.pivot ?? [0.5, 0];
  geo.translate((0.5 - px) * w, (0.5 - py) * h, 0);
  const m = new Mesh(geo, mat);
  m.renderOrder = o.order;
  m.castShadow = o.shadow ?? false;
  m.receiveShadow = !o.basic && (o.shadow ?? false);
  return m;
}
/** 畫面疊層（貼在鏡頭前，不受燈光、不寫深度；換景暗片 order 10000 仍蓋在上面） */
export function screenLayer(map: CanvasTexture<HTMLCanvasElement | HTMLImageElement>, order: number): Mesh {
  const mat = new MeshBasicMaterial({ map, transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
  const m = new Mesh(new PlaneGeometry(1, 1), mat);
  m.renderOrder = order;
  m.frustumCulled = false;
  m.visible = false;
  return m;
}
const _f = new Vector3(), _r = new Vector3(), _u = new Vector3();
/** 把疊層放在鏡頭前 dist 處：cx、cy＝畫面中心起算（−0.5～0.5，cy 往上為正），hFrac＝佔畫面高的比例，aspect＝寬高比 */
export function placeOnCamera(m: Mesh, cam: PerspectiveCamera, cx: number, cy: number, hFrac: number, aspect: number, dist = 0.8): void {
  const H = 2 * dist * Math.tan((cam.fov * Math.PI) / 360);
  const W = H * cam.aspect;
  cam.getWorldDirection(_f);
  _r.set(1, 0, 0).applyQuaternion(cam.quaternion);
  _u.set(0, 1, 0).applyQuaternion(cam.quaternion);
  m.position.copy(cam.position).addScaledVector(_f, dist).addScaledVector(_r, cx * W).addScaledVector(_u, cy * H);
  m.quaternion.copy(cam.quaternion);
  m.scale.set(hFrac * H * aspect, hFrac * H, 1);
}

// ───────────────────────────── 鏡位 ─────────────────────────────
const C = (pos: [number, number, number], target: [number, number, number], fov = 20): CameraPreset => ({ pos, target, fov });
export const WORKSHOP_A0_CAMERAS: Record<string, CameraPreset> = {
  /** 工作台右段（燈籠紙在桌上摺成折折）：阿樂叔叔的位置在畫面外 */
  a0_table: C([1.55, 2.12, 9.4], [1.55, 1.95, -0.6]),
  /** 主燈設計圖近景（牆上的設計圖＋桌上的折折在右下回頭看） */
  a0_design: C([-1.05, 2.38, 9.3], [-1.2, 2.36, -3.5]),
  /** 空著的主燈底座與折折（「骨架不見了！」） */
  a0_base: C([1.15, 2.05, 8.6], [1.15, 1.8, -0.7]),
  /** 回憶小窗：阿樂叔叔坐在工作台前＋桌上的折折 */
  a0_memory: C([-0.95, 1.95, 12.4], [-0.95, 1.72, -0.5]),
  /** 阿樂叔叔（工作台後面）與折折的雙人中景 */
  a0_ale: C([0.05, 1.95, 11.4], [0.05, 1.72, -0.6]),
  /** 店內全景：孩子從右側進門 */
  a0_shop: C([1.8, 1.62, 14.6], [1.8, 1.42, 0]),
  /** 孩子與筆記本特寫小窗（右側留白給小窗） */
  a0_kids: C([2.3, 1.66, 13.6], [2.3, 1.46, 0]),
  /** 台口前緣：折折對全場說話，上方看得到八盞燈 */
  a0_apron: C([0.35, 2.15, 25.0], [0.35, 1.87, 0]),
};

// ───────────────────────────── 位置（世界座標） ─────────────────────────────
const WALL_Z = -3.6;
const DESIGN = { x: -1.6, y: 2.45, w: 1.3 };
const STAND = { x: -0.08, y: 1.36, z: -0.78, w: 1.05 };
const CHIME = { x: 5.35, y: 4.75, z: -1.3, h: 1.12 };
const LAMPS = { x: 0.0, top: 5.4, z: 3.55, w: 12.4 };

const WARM = new Color('#ffd9ae');

/** 筆記本特寫上逐筆畫的筆畫（右頁：竹骨架燈籠；左頁：大問號）。座標＝notebook 圖的像素（900×600） */
function notebookStrokes(): [number, number][][] {
  const S: [number, number][][] = [];
  const cx = 676, cy = 300, rx = 120, ry = 150;
  const ell = (k: number, n = 40): [number, number][] => Array.from({ length: n + 1 }, (_, i) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + rx * k * Math.cos(a), cy + ry * Math.sin(a)]; });
  S.push(ell(1));
  S.push(ell(0.5));
  S.push(Array.from({ length: 21 }, (_, i) => { const a = Math.PI * (i / 20); return [cx - rx * Math.cos(a), cy + 0.32 * ry * Math.sin(a)] as [number, number]; }));
  S.push([[cx - 34, cy - ry - 4], [cx + 34, cy - ry - 4]]);
  S.push([[cx - 34, cy + ry + 4], [cx + 34, cy + ry + 4]]);
  // 問號（左頁）
  const q: [number, number][] = [];
  for (let i = 0; i <= 24; i++) { const a = Math.PI * 1.15 - (Math.PI * 1.45 * i) / 24; q.push([225 + 78 * Math.cos(a), 200 - 78 * Math.sin(a)]); }
  q.push([258, 300], [226, 340], [226, 382]);
  S.push(q);
  S.push([[222, 446], [230, 446]]);
  return S;
}

export const WORKSHOP_A0: SetEntry = {
  title: '燈籠店（開場：G4 燈籠店＋主燈設計圖、空底座、風鈴、八盞燈、回憶小窗、筆記本）',
  cameras: WORKSHOP_A0_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const ws = buildWorkshopG4({ alphaToCoverage: ctx.alphaToCoverage, image: (id) => ctx.image(id) });
    const group = ws.group;
    group.name = 'set:workshop_a0';
    const mats: Material[] = [...ws.materials];
    const report: string[] = [];
    const im = (n: string): HTMLImageElement | undefined => { const i = ctx.image(`sets/workshop_a0/${n}`); if (!i) report.push(`景 workshop_a0：缺圖 ${n}`); return i; };
    const baseColors = ws.materials.map((m) => (m as MeshStandardMaterial).color?.clone());
    // 圓凳：回憶（a0_c002）阿樂叔叔坐在上面；回到現在（a0_c003 起）他站在工作台後面，凳子收到工作台後方（鏡頭橫移時不會掃過細凳腳）
    const stool = ws.pieces.find((p) => p.name === 'stool')?.hinge;
    const stool0 = stool ? stool.position.clone() : null;

    // 主燈設計圖（貼在牆上，和牆一樣有自發光，兒童身後仍夠亮）
    const design = imagePiece(im('design'), { w: DESIGN.w, order: LAYER.far.order - 30, emissive: 0.3 }, mats);
    if (design) { design.position.set(DESIGN.x, DESIGN.y, WALL_Z + 0.06); design.receiveShadow = true; group.add(design); }
    // 空著的主燈底座（在工作台面上）
    const stand = imagePiece(im('stand'), { w: STAND.w, order: LAYER.mid.order + 8, shadow: true }, mats);
    if (stand) { stand.position.set(STAND.x, STAND.y, STAND.z); group.add(stand); }
    // 門口風鈴（懸掛點在上緣中央）
    const chimeHinge = new Group();
    chimeHinge.position.set(CHIME.x, CHIME.y, CHIME.z);
    const chime = imagePiece(im('chime'), { h: CHIME.h, pivot: [0.5, 1], order: LAYER.mid.order + 20, shadow: true }, mats);
    if (chime) chimeHinge.add(chime);
    group.add(chimeHinge);
    // 台口上方一串八盞還沒亮的燈
    const lamps = imagePiece(im('lamps'), { w: LAMPS.w, pivot: [0.5, 1], order: LAYER.fore.order + 30, emissive: 0.12 }, mats);
    if (lamps) { lamps.position.set(LAMPS.x, LAMPS.top, LAMPS.z); group.add(lamps); }

    // 回憶小窗（畫面疊層）
    const memImg = im('memoryframe');
    const memTex = memImg ? finishTexture(new CanvasTexture(memImg)) : null;
    const memory = memTex ? screenLayer(memTex, 9000) : null;
    if (memory) group.add(memory);

    // 筆記本特寫（畫面疊層；筆畫由程式逐筆畫）
    const nbImg = im('notebook');
    const [nbCanvas, nbG] = makeCanvas(900, 600);
    const nbTex = finishTexture(new CanvasTexture(nbCanvas));
    const notebook = nbImg ? screenLayer(nbTex, 9001) : null;
    if (notebook) group.add(notebook);
    const strokes = notebookStrokes();
    const strokeLen = strokes.map((s) => s.slice(1).reduce((a, p, i) => a + Math.hypot(p[0] - s[i][0], p[1] - s[i][1]), 0));
    const total = strokeLen.reduce((a, b) => a + b, 0);
    let nbDrawn = -1;
    const drawNotebook = (p: number): void => {
      const q = Math.round(clamp(p) * 240) / 240;     // 量化（每 1/240 才重畫一次貼圖）
      if (q === nbDrawn || !nbImg) return;
      nbDrawn = q;
      nbG.clearRect(0, 0, 900, 600);
      nbG.drawImage(nbImg, 0, 0, 900, 600);
      nbG.strokeStyle = '#4a3c34'; nbG.lineWidth = 7; nbG.lineCap = 'round'; nbG.lineJoin = 'round';
      let left = q * total;
      strokes.forEach((s, k) => {
        if (left <= 0) return;
        nbG.beginPath();
        nbG.moveTo(s[0][0], s[0][1]);
        let acc = 0;
        for (let i = 1; i < s.length; i++) {
          const seg = Math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]);
          if (acc + seg <= left) { nbG.lineTo(s[i][0], s[i][1]); acc += seg; continue; }
          const u = (left - acc) / seg;
          nbG.lineTo(lerp(s[i - 1][0], s[i][0], u), lerp(s[i - 1][1], s[i][1], u));
          acc = left;
          break;
        }
        nbG.stroke();
        left -= strokeLen[k];
      });
      nbTex.needsUpdate = true;
    };

    return {
      group, pieces: ws.pieces, materials: mats, marks: ws.marks, tableEdge: ws.tableEdge,
      landmarks: { ...ws.landmarks, emptyStand: { x0: STAND.x - STAND.w / 2, x1: STAND.x + STAND.w / 2, y: STAND.y + 0.3, z: STAND.z } },
      cameras: WORKSHOP_A0_CAMERAS, report,
      update({ tl, t, camera }) {
        const id = tl.cue.id;
        if (stool && stool0) {
          if (id === 'a0_c003' || id === 'a0_c004' || id === 'a0_c005') stool.position.set(-1.85, stool0.y, -1.4);
          else stool.position.copy(stool0);
        }
        // ---- 回憶小窗（a0_c002）：「是阿樂叔叔把我摺出來的喔」說完前 0.5 秒，紙框從外緣收進來（1.4 秒），景片轉暖
        let mem = 0;
        if (id === 'a0_c002') mem = sine01((t - (lineTime(tl, ['a0_c002_02'], 'end', 9) - 0.5)) / 1.4);
        if (memory) {
          memory.visible = mem > 0.001;
          if (memory.visible) {
            placeOnCamera(memory, camera, 0, 0, 1.0 * (1 + 0.32 * (1 - mem)), 16 / 9, 0.75);
            (memory.material as MeshBasicMaterial).opacity = clamp(mem * 1.6);
          }
        }
        ws.materials.forEach((m, i) => { const c = (m as MeshStandardMaterial).color; const b = baseColors[i]; if (c && b) c.copy(b).lerp(b.clone().multiply(WARM), 0.75 * mem); });
        // ---- 風鈴（a0_c004 開頭 S6）：輕擺，阻尼漸停（擺幅小、慢，不閃）
        let ang = 0;
        if (id === 'a0_c004') { const s = t - 0.15; if (s > 0) ang = 0.13 * Math.exp(-s / 1.6) * Math.sin(2 * Math.PI * 0.85 * s); }
        chimeHinge.rotation.z = ang;
        // ---- 筆記本特寫（a0_c004）：小晴「我記下來」→ 小窗打開、竹骨架與問號逐筆畫上 → 折折開口前收起
        let nb = 0, draw = 0;
        if (id === 'a0_c004') {
          const t0 = lineTime(tl, ['a0_c004_02'], 'start', 3) + 0.55;
          const t1 = lineTime(tl, ['a0_c004_03', 'a0_c004_05'], 'start', t0 + 4) - 0.1;
          nb = sine01((t - t0) / 0.45) * (1 - sine01((t - t1) / 0.45));
          draw = clamp((t - t0 - 0.35) / Math.max(1.2, Math.min(2.8, t1 - t0 - 0.8)));
        }
        if (notebook) {
          notebook.visible = nb > 0.001;
          if (notebook.visible) {
            drawNotebook(draw);
            placeOnCamera(notebook, camera, 0.285, 0.16, 0.4 * (0.94 + 0.06 * nb), 1.5, 0.78);
            (notebook.material as MeshBasicMaterial).opacity = nb;
          }
        }
      },
    };
  },
};
