// 臉部換片（v1.2 第 15.3 節）：嘴型（閉、半開、大開、圓唇＋擔心、微笑）與眼睛（開、半閉、閉）。
// - 正式素材：assets/final/face/<角色>/mouth_*.png、eyes_*.png＋face.json（錨點像素座標、尺寸、層序），見 app/G4_INTERFACE.md。
// - 退路：正式素材還沒到時，用「量好的眼睛／嘴巴範圍」在載入時程式畫出換片（膚色補片＋線條），只在需要時蓋在原圖上；
//   平常顯示原圖畫好的眼睛和嘴巴。
// - 換片一律硬切（不交叉淡化），所以不會有殘影；換片區域很小，不構成明暗閃爍。
import { DoubleSide, Group, Mesh, MeshStandardMaterial, PlaneGeometry, type Object3D, type Texture, CanvasTexture } from 'three';
import { finishTexture } from './paper';
import { makeCanvas2 } from './imageproc';

export type MouthShape = 'closed' | 'half' | 'open' | 'round' | 'worried' | 'smile';
export type EyeShape = 'open' | 'half' | 'closed';
export const MOUTH_SHAPES: MouthShape[] = ['closed', 'half', 'open', 'round', 'worried', 'smile'];
export const EYE_SHAPES: EyeShape[] = ['open', 'half', 'closed'];

/** face.json 的一個換片槽（mouth 或 eyes）。座標是「基準圖」的像素座標（左上原點，y 向下） */
export interface FaceSlotConfig {
  /** 換片圖中心在基準圖上的像素位置 */
  anchor: [number, number];
  /** 換片圖在基準圖上佔的像素尺寸 */
  size: [number, number];
  /** 層序：數字越大越前面（眼睛預設 2、嘴巴 1） */
  z?: number;
  /** 形狀 → 圖像 id（省略時依慣例 face/<角色>/<槽>_<形狀>） */
  shapes?: Partial<Record<string, string>>;
}

export interface FaceConfig {
  character?: string;
  /** 錨點座標所依據的圖像 id（例如 chr-ale_head-worried、chr-xiaoqing_pose-reach-worried）；只有掛在這張圖上時才用正式換片 */
  baseImage?: string;
  /** 不說話時的嘴型（例如 worried） */
  restMouth?: string;
  /** 立牌的頭層（素材代理把姿勢圖拆成頭＋身體時）：頭層圖 id、頭層左上角在姿勢圖上的位置、轉動支點（頭層像素） */
  headLayer?: { image: string; offset: [number, number]; pivot: [number, number]; size?: [number, number] };
  /** 頭層所屬的整張姿勢圖 id */
  poseImage?: string;
  /** 錨點座標所依據的基準圖：分件紙偶填部件 id（例如 head），立牌填姿勢 id 或省略 */
  base?: string;
  mouth?: FaceSlotConfig;
  eyes?: FaceSlotConfig;
  /** 立牌每個姿勢的錨點不同時，依姿勢覆寫 */
  perPose?: Record<string, { mouth?: FaceSlotConfig; eyes?: FaceSlotConfig }>;
  /** 原圖本來畫的嘴型（不說話、情緒相符時直接顯示原圖） */
  paintedMouth?: MouthShape;
}

/**
 * 素材代理的 face.json（groups＋pieces 格式，anchor_px＝換片左上角）→ FaceConfig。
 * 也接受本檔的原生格式（mouth／eyes＋anchor＝中心）。
 */
export function parseFaceJson(raw: unknown): FaceConfig | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const j = raw as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  if (j.mouth || j.eyes) return j as FaceConfig;
  if (!j.groups || !j.pieces) return undefined;
  const cfg: FaceConfig = { character: j.character, baseImage: j.head_image?.image_id, restMouth: String(j.rest_mouth ?? '').replace(/^mouth_/, '') || undefined };
  const hi = j.head_image;
  if (hi?.offset_in_pose_image_px && hi?.pivot_px) {
    cfg.headLayer = { image: hi.image_id, offset: hi.offset_in_pose_image_px, pivot: hi.pivot_px, size: hi.size };
    cfg.poseImage = j.pose_image?.image_id;
  }
  for (const kind of ['mouth', 'eyes'] as const) {
    const g = j.groups[kind];
    if (!g) continue;
    const shapes: Record<string, string> = {};
    for (const [k, v] of Object.entries(j.pieces as Record<string, any>)) { // eslint-disable-line @typescript-eslint/no-explicit-any
      if ((v.group ?? k.split('_')[0]) !== kind) continue;
      shapes[k.replace(new RegExp(`^${kind}_`), '')] = v.image_id ?? k;
    }
    cfg[kind] = { anchor: [g.anchor_px[0] + g.size[0] / 2, g.anchor_px[1] + g.size[1] / 2], size: g.size, z: kind === 'mouth' ? 2 : 1, shapes };
  }
  return cfg;
}

/** 退路：量好的眼睛、嘴巴範圍（基準圖像素 [x0,y0,x1,y1]） */
export interface FallbackFace {
  /** 量測時那張圖的不透明範圍（alpha ≥ 128）左上角；圖被重新裁切時用它換算座標 */
  ref?: [number, number];
  eyes: [number, number, number, number][];
  mouth: [number, number, number, number];
  paintedMouth: MouthShape;
  /** 眼睛有眼鏡框時，補片只蓋鏡片內 */
  glasses?: boolean;
  /** 眼睛補片半徑倍數（相對眼框半徑；預設 眼鏡 1.08／無眼鏡 1.3）。補片邊緣 18% 是羽化，眼眶要落在實色區內才不會留下淡淡的眼框 */
  patchK?: number;
}

/** 基準圖像素 → 掛載物件本地座標（世界單位） */
export type PxToLocal = (x: number, y: number) => [number, number];

interface SlotView { group: Group; meshes: Map<string, Mesh>; current: string }

/** 讀圖片指定範圍的平均膚色（排除深色線條） */
function sampleSkin(img: CanvasImageSource, box: [number, number, number, number]): [number, number, number] {
  const [x0, y0, x1, y1] = box;
  const pad = Math.max(6, (x1 - x0) * 0.35);
  const [c, g] = makeCanvas2(x1 - x0 + pad * 2, y1 - y0 + pad * 2);
  g.drawImage(img, -(x0 - pad), -(y0 - pad));
  const d = g.getImageData(0, 0, c.width, c.height).data;
  let r = 0, gg = 0, b = 0, n = 0;
  for (let y = 0; y < c.height; y++) {
    for (let x = 0; x < c.width; x++) {
      const inside = x >= pad && x < c.width - pad && y >= pad && y < c.height - pad;
      if (inside) continue; // 只取外圈
      const k = (y * c.width + x) * 4;
      if (d[k + 3] < 200) continue;
      const lum = d[k] * 0.3 + d[k + 1] * 0.59 + d[k + 2] * 0.11;
      if (lum < 150 || d[k] < d[k + 2] + 40) continue; // 排除頭髮、線條、非膚色
      r += d[k]; gg += d[k + 1]; b += d[k + 2]; n++;
    }
  }
  return n ? [r / n, gg / n, b / n] : [246, 190, 145];
}

const css = (c: [number, number, number], a = 1): string => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;

/** 程式畫的換片：每個形狀一張畫布，範圍＝slotBox（基準圖像素） */
function drawFallback(kind: 'eyes' | 'mouth', shape: string, fb: FallbackFace, skin: [number, number, number], slotBox: [number, number, number, number], scale: number): HTMLCanvasElement | null {
  const [sx0, sy0, sx1, sy1] = slotBox;
  const W = Math.ceil((sx1 - sx0) * scale), H = Math.ceil((sy1 - sy0) * scale);
  const [c, g] = makeCanvas2(W, H);
  const X = (x: number): number => (x - sx0) * scale, Y = (y: number): number => (y - sy0) * scale;
  const ink = 'rgba(52,34,26,0.95)';
  g.lineCap = 'round';
  g.lineJoin = 'round';
  const patch = (cx: number, cy: number, rx: number, ry: number): void => {
    // 膚色補片：中心實色、邊緣 2 px 羽化，貼上去看不出接縫
    const grd = g.createRadialGradient(X(cx), Y(cy), 0, X(cx), Y(cy), Math.max(rx, ry) * scale);
    grd.addColorStop(0, css(skin));
    grd.addColorStop(0.82, css(skin));
    grd.addColorStop(1, css(skin, 0));
    g.save();
    g.translate(X(cx), Y(cy));
    g.scale(rx / Math.max(rx, ry), ry / Math.max(rx, ry));
    g.translate(-X(cx), -Y(cy));
    g.fillStyle = grd;
    g.beginPath(); g.arc(X(cx), Y(cy), Math.max(rx, ry) * scale, 0, Math.PI * 2); g.fill();
    g.restore();
  };
  if (kind === 'eyes') {
    if (shape === 'open') return null; // 原圖
    for (const [x0, y0, x1, y1] of fb.eyes) {
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rx = (x1 - x0) / 2, ry = (y1 - y0) / 2;
      const k = fb.patchK ?? (fb.glasses ? 1.08 : 1.3);
      if (shape === 'closed') {
        // 中性閉眼：近乎平直、略往下彎的眼皮線（與素材 eyes_closed v02／v03 同款，不是往上拱的笑眼）；兩眼畫在同一張換片，一定同時閉
        patch(cx, cy, rx * k, ry * k);
        g.strokeStyle = ink;
        g.lineWidth = Math.max(2, ry * 0.22 * scale);
        g.beginPath();
        g.moveTo(X(cx - rx * 1.05), Y(cy + ry * 0.05));
        g.quadraticCurveTo(X(cx), Y(cy + ry * 0.16), X(cx + rx * 1.05), Y(cy + ry * 0.05));
        g.stroke();
      } else {
        // 半閉：上半部蓋上眼皮，留下半個眼珠
        g.save();
        g.beginPath(); g.rect(0, 0, W, Y(cy + ry * 0.02)); g.clip();
        patch(cx, cy, rx * k, ry * k);
        g.restore();
        g.strokeStyle = ink;
        g.lineWidth = Math.max(2, ry * 0.2 * scale);
        g.beginPath();
        g.moveTo(X(cx - rx * 1.05), Y(cy));
        g.quadraticCurveTo(X(cx), Y(cy - ry * 0.18), X(cx + rx * 1.05), Y(cy));
        g.stroke();
      }
    }
    return c;
  }
  // 嘴型
  if (shape === fb.paintedMouth) return null;
  const [x0, y0, x1, y1] = fb.mouth;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const mw = Math.max(x1 - x0, 24), mh = Math.max(y1 - y0, 10);
  patch(cx, cy, mw * 0.68, mh * 0.95 + 4);
  g.strokeStyle = ink;
  g.fillStyle = 'rgba(122,46,40,0.97)';
  const lw = Math.max(2, mw * 0.06 * scale);
  g.lineWidth = lw;
  const ell = (w: number, h: number, dy = 0): void => {
    g.beginPath(); g.ellipse(X(cx), Y(cy + dy), w * scale, h * scale, 0, 0, Math.PI * 2); g.fill(); g.stroke();
    // 舌頭：下半淡紅
    g.save(); g.clip(); g.fillStyle = 'rgba(214,112,104,0.9)';
    g.beginPath(); g.ellipse(X(cx), Y(cy + dy + h * 0.75), w * 0.8 * scale, h * 0.55 * scale, 0, 0, Math.PI * 2); g.fill(); g.restore();
  };
  switch (shape) {
    case 'closed': g.beginPath(); g.moveTo(X(cx - mw * 0.32), Y(cy)); g.quadraticCurveTo(X(cx), Y(cy + mh * 0.12), X(cx + mw * 0.32), Y(cy)); g.stroke(); break;
    case 'smile': g.beginPath(); g.moveTo(X(cx - mw * 0.4), Y(cy - mh * 0.15)); g.quadraticCurveTo(X(cx), Y(cy + mh * 0.6), X(cx + mw * 0.4), Y(cy - mh * 0.15)); g.stroke(); break;
    case 'worried':
      g.beginPath(); g.moveTo(X(cx - mw * 0.3), Y(cy + mh * 0.12));
      g.bezierCurveTo(X(cx - mw * 0.12), Y(cy - mh * 0.22), X(cx + mw * 0.1), Y(cy + mh * 0.25), X(cx + mw * 0.3), Y(cy - mh * 0.05));
      g.stroke(); break;
    case 'half': ell(mw * 0.2, mh * 0.28); break;
    case 'open': ell(mw * 0.24, mh * 0.55, mh * 0.1); break;
    case 'round': ell(mw * 0.13, mh * 0.42, mh * 0.05); break;
    default: return null;
  }
  return c;
}

export interface FaceSource {
  /** 正式換片圖（id → 圖） */
  image: (id: string) => CanvasImageSource | undefined;
}

/** 一組臉部換片（掛在頭部部件或立牌姿勢上） */
export class FaceRig {
  readonly group = new Group();
  private slots: Partial<Record<'mouth' | 'eyes', SlotView>> = {};
  readonly mode: 'images' | 'fallback' | 'none';
  readonly painted: MouthShape;

  constructor(
    readonly charId: string,
    parent: Object3D,
    px2local: PxToLocal,
    pxScale: number,
    opts: { config?: FaceConfig; fallback?: FallbackFace; baseImage?: CanvasImageSource; baseId?: string; source: FaceSource; renderOrder: number; zBase: number; pose?: string },
  ) {
    parent.add(this.group);
    this.group.position.z = opts.zBase;
    const cfg = opts.config && (!opts.config.baseImage || !opts.baseId || opts.config.baseImage === opts.baseId) ? opts.config : undefined;
    this.painted = (cfg?.restMouth as MouthShape | undefined) ?? cfg?.paintedMouth ?? opts.fallback?.paintedMouth ?? 'smile';
    const slotCfg = (k: 'mouth' | 'eyes'): FaceSlotConfig | undefined => (opts.pose && cfg?.perPose?.[opts.pose]?.[k]) || cfg?.[k];
    const hasImages = !!cfg && (['mouth', 'eyes'] as const).some((k) => {
      const s = slotCfg(k);
      if (!s) return false;
      return (k === 'mouth' ? MOUTH_SHAPES : EYE_SHAPES).some((sh) => opts.source.image(s.shapes?.[sh] ?? `face/${charId}/${k}_${sh}`));
    });
    this.mode = hasImages ? 'images' : opts.fallback && opts.baseImage ? 'fallback' : 'none';
    if (this.mode === 'none') return;

    for (const kind of ['eyes', 'mouth'] as const) {
      const view: SlotView = { group: new Group(), meshes: new Map(), current: '' };
      this.group.add(view.group);
      const shapes = kind === 'mouth' ? MOUTH_SHAPES : EYE_SHAPES;
      const z = kind === 'eyes' ? 2 : 1;
      if (this.mode === 'images') {
        const s = slotCfg(kind);
        if (!s) continue;
        const [cx, cy] = s.anchor, [w, h] = s.size;
        for (const sh of shapes) {
          const img = opts.source.image(s.shapes?.[sh] ?? `face/${charId}/${kind}_${sh}`);
          if (!img) continue;
          const tex = finishTexture(new CanvasTexture(img as HTMLCanvasElement));
          view.meshes.set(sh, this.makeMesh(tex, px2local, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, opts.renderOrder + (s.z ?? z), (s.z ?? z) * 0.0015));
        }
      } else {
        const fb = opts.fallback!;
        const boxes = kind === 'eyes' ? fb.eyes : [fb.mouth];
        const pad = kind === 'eyes' ? 0.45 : 0.9;
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        for (const b of boxes) {
          const bw = b[2] - b[0], bh = b[3] - b[1];
          x0 = Math.min(x0, b[0] - bw * pad); y0 = Math.min(y0, b[1] - bh * pad);
          x1 = Math.max(x1, b[2] + bw * pad); y1 = Math.max(y1, b[3] + bh * pad);
        }
        const box: [number, number, number, number] = [Math.floor(x0), Math.floor(y0), Math.ceil(x1), Math.ceil(y1)];
        const skin = sampleSkin(opts.baseImage!, kind === 'eyes' ? [box[0], fb.eyes[0][3], box[2], fb.eyes[0][3] + 20] : fb.mouth);
        const scale = Math.max(1, Math.min(3, 1.5 / Math.max(pxScale * 400, 0.5)));
        for (const sh of shapes) {
          const cv = drawFallback(kind, sh, fb, skin, box, scale);
          if (!cv) continue;
          const tex = finishTexture(new CanvasTexture(cv));
          view.meshes.set(sh, this.makeMesh(tex, px2local, box[0], box[1], box[2], box[3], opts.renderOrder + z, z * 0.0015));
        }
      }
      this.slots[kind] = view;
    }
    this.set('open', this.painted);
  }

  private makeMesh(tex: Texture, px2local: PxToLocal, x0: number, y0: number, x1: number, y1: number, order: number, dz: number): Mesh {
    const [ax, ay] = px2local(x0, y1);
    const [bx, by] = px2local(x1, y0);
    const geo = new PlaneGeometry(Math.abs(bx - ax), Math.abs(by - ay));
    geo.translate((ax + bx) / 2, (ay + by) / 2, 0);
    const mat = new MeshStandardMaterial({ map: tex, transparent: true, depthWrite: false, side: DoubleSide, roughness: 0.95, metalness: 0 });
    const m = new Mesh(geo, mat);
    m.position.z = dz;
    m.renderOrder = order;
    m.visible = false;
    this.group.add(m);
    return m;
  }

  /** 設定目前的眼睛與嘴型（沒有對應換片的形狀＝顯示原圖） */
  set(eyes: EyeShape, mouth: MouthShape): void {
    this.apply('eyes', eyes);
    this.apply('mouth', mouth);
  }

  private apply(kind: 'eyes' | 'mouth', shape: string): void {
    const v = this.slots[kind];
    if (!v || v.current === shape) return;
    v.current = shape;
    v.meshes.forEach((m, k) => { m.visible = k === shape; });
  }

  setVisible(on: boolean): void { this.group.visible = on; }
  /** 眼睛換片的任一張網格（同一組換片同錨點、同尺寸；量測眼睛在畫面上的位置用） */
  eyesMesh(): Mesh | null { const v = this.slots.eyes; if (!v) return null; for (const m of v.meshes.values()) return m; return null; }
  get current(): { eyes: string; mouth: string } { return { eyes: this.slots.eyes?.current ?? '', mouth: this.slots.mouth?.current ?? '' }; }
}

/** 退路臉部範圍（2026-10-21 從 v04 母版與 ale_v03 頭部量測；正式 face.json 到了就不用） */
export const FALLBACK_FACES: Record<string, FallbackFace> = {
  'ale:head': { eyes: [[507, 174, 522, 201], [568, 180, 582, 206]], mouth: [505, 231, 566, 249], paintedMouth: 'smile' },
  'xiaoqing:stand': { ref: [262, 48], eyes: [[393, 240, 427, 289], [494, 251, 538, 301]], mouth: [433, 328, 481, 339], paintedMouth: 'smile' },
  'xiaoqing:reach': { ref: [119, 97], eyes: [[457, 264, 479, 303], [545, 289, 593, 335]], mouth: [479, 350, 510, 377], paintedMouth: 'open' },
  // 2026-10-21 主線：G4 重驗（第 2 輪後）發現站姿近側眼框比實際眼睛高 6 px、窄 3 px → 眨眼像單眼眨。改用 chr-xiaoyu_master_v04 實量的眼珠範圍（深色連通區外擴 1–2 px；ref＝alpha≥128 左上角 17,16），補片放大到 1.32 倍（眼眶落在實色區，閉眼不留淡框；仍在鏡片內）
  'xiaoyu:stand': { ref: [17, 16], eyes: [[177, 212, 199, 249], [270, 225, 295, 263]], mouth: [196, 285, 250, 299], paintedMouth: 'smile', glasses: true, patchK: 1.32 },
  'xiaoyu:stepback': { ref: [256, 81], eyes: [[463, 254, 481, 286], [546, 289, 564, 321]], mouth: [472, 365, 498, 395], paintedMouth: 'round', glasses: true },
};

/** 圖被重新裁切時（不透明範圍左上角從 ref 移到 at），把退路臉部範圍平移過去 */
export function shiftFallback(fb: FallbackFace, at: [number, number]): FallbackFace {
  if (!fb.ref) return fb;
  const dx = at[0] - fb.ref[0], dy = at[1] - fb.ref[1];
  const sh = (b: [number, number, number, number]): [number, number, number, number] => [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy];
  return { ...fb, ref: at, eyes: fb.eyes.map(sh), mouth: sh(fb.mouth) };
}
