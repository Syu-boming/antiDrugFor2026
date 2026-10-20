// 操偶線（v1.2 第 15.2 節、G2 一般問題第 2 項）：
// - 平面紙繩：中灰紙帶＋紙纖維、兩側深灰邊線、左側一道受光邊；不做扭絞鋼索紋。
//   明度：紙帶 L*≈48，對阿樂的皮膚（L*≈76）與袖口（L*≈88）ΔL* ≥ 25；深灰邊 L*≈22。
//   用不受光照影響的材質（亮度只跟舞台燈總量走），擷取量得到的 ΔL* 才穩定。
// - 寬度：中景約 9 px、近景 ≥ 8 px（1080p）。
// - 從畫面上方外面垂下，下端以紙環扣在錨點（紙環是包住肢體的一圈紙帶）；不畫操控者的手或人影。
// - 受力順序：線先繃緊（弧度消失），肢體才被拉動；擺盪用固定步長的彈簧阻尼模擬，每個 cue 開始時重設，
//   所以重播與上一步會得到一模一樣的畫面。
// - 復原 API：鬆（tension→0、弧度變大）、淡（opacity）、脫落（紙環打開、線往上飄出畫面）；沒有「剪斷」。
import {
  BufferAttribute, BufferGeometry, CanvasTexture, DoubleSide, Mesh, MeshBasicMaterial, PlaneGeometry, RepeatWrapping, Vector3,
} from 'three';
import { finishTexture, makeCanvas } from './paper';
import { seeded } from '../util/math';

export const ROPE_COLORS = { body: '#77746f', edge: '#3a3835', lit: '#c9c5bc', fiberDark: 'rgba(40,38,34,0.16)', fiberLight: 'rgba(235,232,224,0.18)' };

/** 平面紙繩貼圖（u＝橫跨寬度，v＝沿長度重複） */
export function ropeTexture(): CanvasTexture {
  const W = 64, H = 256;
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = ROPE_COLORS.body;
  g.fillRect(0, 0, W, H);
  // 紙纖維：沿長度方向的細短線與斑點（不成螺旋）
  const r = seeded(913);
  for (let i = 0; i < 260; i++) {
    const x = 9 + r() * (W - 18), y = r() * H, len = 4 + r() * 14;
    g.strokeStyle = r() < 0.5 ? ROPE_COLORS.fiberDark : ROPE_COLORS.fiberLight;
    g.lineWidth = 0.7 + r() * 0.8;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 3, y + len); g.stroke();
  }
  // 兩側深灰邊線（各約 15%）＋左側受光邊
  g.fillStyle = ROPE_COLORS.edge;
  g.fillRect(0, 0, 9, H);
  g.fillRect(W - 10, 0, 10, H);
  g.fillStyle = ROPE_COLORS.lit;
  g.fillRect(9, 0, 4, H);
  g.fillStyle = 'rgba(0,0,0,0.10)';
  g.fillRect(W - 16, 0, 6, H); // 右側背光
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = RepeatWrapping;
  t.wrapT = RepeatWrapping;
  return t;
}

/** 紙環貼圖：米白紙帶、上下深色紙邊、中間一道摺痕、上緣中央綁線的小結 */
export function ringTexture(): CanvasTexture {
  const W = 128, H = 48;
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = '#efe6d3';
  g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(120,96,70,0.18)';
  g.fillRect(0, H * 0.48, W, 3);
  g.fillStyle = '#4d4034';
  g.fillRect(0, 0, W, 5);
  g.fillRect(0, H - 5, W, 5);
  g.fillRect(0, 0, 4, H);
  g.fillRect(W - 4, 0, 4, H);
  // 兩端略暗（紙帶繞到肢體後面）
  const grd = g.createLinearGradient(0, 0, W, 0);
  grd.addColorStop(0, 'rgba(60,45,30,0.35)'); grd.addColorStop(0.18, 'rgba(60,45,30,0)');
  grd.addColorStop(0.82, 'rgba(60,45,30,0)'); grd.addColorStop(1, 'rgba(60,45,30,0.35)');
  g.fillStyle = grd;
  g.fillRect(0, 0, W, H);
  // 綁線的小結（灰色）
  g.fillStyle = ROPE_COLORS.edge;
  g.beginPath(); g.ellipse(W / 2, 9, 9, 7, 0, 0, Math.PI * 2); g.fill();
  g.fillStyle = ROPE_COLORS.body;
  g.beginPath(); g.ellipse(W / 2, 9, 5.5, 4, 0, 0, Math.PI * 2); g.fill();
  return finishTexture(new CanvasTexture(c));
}

let ropeTex: CanvasTexture | null = null;
let ringTex: CanvasTexture | null = null;

export function ropeMaterial(): MeshBasicMaterial {
  ropeTex ??= ropeTexture();
  return new MeshBasicMaterial({ map: ropeTex, side: DoubleSide });
}

export function ringMaterial(): MeshBasicMaterial {
  ringTex ??= ringTexture();
  return new MeshBasicMaterial({ map: ringTex, side: DoubleSide });
}

const SEGMENTS = 36;
const tmpA = new Vector3();

export interface StringPose {
  top: Vector3;
  bottom: Vector3;
  /** 鬆垂弧度（世界單位，0＝繃直；正負決定往哪邊彎） */
  bow: number;
  /** 線寬（世界單位） */
  width: number;
  /** 0–1 不透明度（變淡） */
  opacity: number;
  /** 紙環：0＝沒扣上、1＝扣好；脫落時從 1 往 0 */
  ring: number;
  /** 紙環方向（世界角度，弧度：肢體方向）與寬度（包住的肢體寬度） */
  ringAngle: number;
  ringWidth: number;
  /** 舞台燈總量（紙繩不受光照，亮度跟著舞台燈走） */
  light: number;
}

/** 一條紙繩：二次貝茲曲線的帶狀網格＋下端紙環 */
export class PaperString {
  readonly mesh: Mesh;
  readonly ring: Mesh;
  readonly ropeMat: MeshBasicMaterial;
  readonly ringMat: MeshBasicMaterial;
  private pos: Float32Array;
  private uv: Float32Array;
  /** 最近一次的螢幕取樣資訊（測試與擷取量測用） */
  last: { top: Vector3; bottom: Vector3; width: number; visible: boolean; bow: number } = { top: new Vector3(), bottom: new Vector3(), width: 0, visible: false, bow: 0 };

  constructor(renderOrder: number) {
    this.ropeMat = ropeMaterial();
    this.ringMat = ringMaterial();
    const geo = new BufferGeometry();
    this.pos = new Float32Array((SEGMENTS + 1) * 2 * 3);
    this.uv = new Float32Array((SEGMENTS + 1) * 2 * 2);
    const idx: number[] = [];
    for (let i = 0; i < SEGMENTS; i++) {
      const a = i * 2, b = a + 1, c = a + 2, d = a + 3;
      idx.push(a, c, b, b, c, d);
    }
    geo.setAttribute('position', new BufferAttribute(this.pos, 3));
    geo.setAttribute('uv', new BufferAttribute(this.uv, 2));
    geo.setIndex(idx);
    this.mesh = new Mesh(geo, this.ropeMat);
    this.mesh.renderOrder = renderOrder;
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = true;
    this.ring = new Mesh(new PlaneGeometry(1, 1), this.ringMat);
    this.ring.renderOrder = renderOrder + 1;
    this.ring.castShadow = true;
    this.ring.frustumCulled = false;
  }

  hide(): void { this.mesh.visible = false; this.ring.visible = false; this.last.visible = false; }

  update(p: StringPose): void {
    if (p.opacity <= 0.002) { this.hide(); return; }
    this.mesh.visible = true;
    const { top, bottom } = p;
    const dx = bottom.x - top.x, dy = bottom.y - top.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    const cx = (top.x + bottom.x) / 2 + nx * p.bow, cy = (top.y + bottom.y) / 2 + ny * p.bow;
    const cz = (top.z + bottom.z) / 2;
    const vRepeat = len / (p.width * 4);
    for (let i = 0; i <= SEGMENTS; i++) {
      const t = i / SEGMENTS, it = 1 - t;
      const px = it * it * top.x + 2 * it * t * cx + t * t * bottom.x;
      const py = it * it * top.y + 2 * it * t * cy + t * t * bottom.y;
      const pz = it * it * top.z + 2 * it * t * cz + t * t * bottom.z;
      const tx = 2 * it * (cx - top.x) + 2 * t * (bottom.x - cx);
      const ty = 2 * it * (cy - top.y) + 2 * t * (bottom.y - cy);
      const tl = Math.hypot(tx, ty) || 1;
      // 紙帶寬度：u=0 在畫面左側（受光邊在左）
      let ox = (-ty / tl) * p.width / 2, oy = (tx / tl) * p.width / 2;
      if (ox > 0) { ox = -ox; oy = -oy; }
      const k = i * 6;
      this.pos[k] = px + ox; this.pos[k + 1] = py + oy; this.pos[k + 2] = pz;
      this.pos[k + 3] = px - ox; this.pos[k + 4] = py - oy; this.pos[k + 5] = pz;
      const u = i * 4;
      this.uv[u] = 0; this.uv[u + 1] = t * vRepeat;
      this.uv[u + 2] = 1; this.uv[u + 3] = t * vRepeat;
    }
    const geo = this.mesh.geometry;
    geo.attributes.position.needsUpdate = true;
    geo.attributes.uv.needsUpdate = true;
    const L = Math.max(0.2, Math.min(1.2, p.light));
    this.ropeMat.color.setScalar(L);
    this.ringMat.color.setScalar(L);
    const fade = p.opacity < 0.999;
    if (this.ropeMat.transparent !== fade) { this.ropeMat.transparent = fade; this.ringMat.transparent = fade; this.ropeMat.needsUpdate = true; this.ringMat.needsUpdate = true; }
    this.ropeMat.opacity = p.opacity;
    this.ringMat.opacity = p.opacity;
    this.ropeMat.depthWrite = !fade;
    this.ringMat.depthWrite = !fade;
    this.last = { top: top.clone(), bottom: bottom.clone(), width: p.width, visible: true, bow: p.bow };

    // 紙環：包住肢體的紙帶（長邊垂直於肢體方向），扣上時由 0.6 倍彈到原尺寸
    this.ring.visible = p.ring > 0.01;
    if (this.ring.visible) {
      tmpA.copy(bottom);
      const pop = p.ring < 1 ? 0.6 + 0.4 * p.ring : 1;
      this.ring.position.set(tmpA.x, tmpA.y, tmpA.z + 0.02);
      this.ring.rotation.set(0, 0, p.ringAngle + Math.PI / 2);
      this.ring.scale.set((p.ringWidth + 0.04) * pop, Math.max(0.06, p.width * 1.05) * pop, 1);
    }
  }
}

/** 固定步長的彈簧阻尼模擬（每個通道是一個 2D 位移） */
export interface SimChannel { ox: number; oy: number; vx: number; vy: number }

export type SimDrive = (t: number) => Map<string, { px: number; py: number; k?: number; c?: number }>;

export class StringSim {
  /** 固定步長 1/120 秒 */
  readonly dt = 1 / 120;
  time = 0;
  readonly ch = new Map<string, SimChannel>();
  /** 預設勁度與阻尼：約 1.2 Hz、阻尼比 0.37，會擺盪幾下後停住 */
  stiffness = 55;
  damping = 5.5;

  reset(initial?: Map<string, { px: number; py: number }>): void {
    this.time = 0;
    this.ch.clear();
    initial?.forEach((v, key) => this.ch.set(key, { ox: v.px, oy: v.py, vx: 0, vy: 0 }));
  }

  /** 推進到時間 t；t 比目前早時，從 0 重新模擬（確保結果只跟 t 有關） */
  advanceTo(t: number, drive: SimDrive, initial?: Map<string, { px: number; py: number }>): void {
    if (t < this.time - 1e-9) this.reset(initial);
    let guard = 0;
    while (this.time + this.dt <= t + 1e-9 && guard++ < 200000) {
      const targets = drive(this.time);
      targets.forEach((tg, key) => {
        let c = this.ch.get(key);
        if (!c) { c = { ox: tg.px, oy: tg.py, vx: 0, vy: 0 }; this.ch.set(key, c); }
        const k = tg.k ?? this.stiffness, d = tg.c ?? this.damping;
        const ax = k * (tg.px - c.ox) - d * c.vx;
        const ay = k * (tg.py - c.oy) - d * c.vy;
        c.vx += ax * this.dt; c.vy += ay * this.dt;
        c.ox += c.vx * this.dt; c.oy += c.vy * this.dt;
      });
      this.time += this.dt;
    }
  }

  get(key: string): SimChannel { return this.ch.get(key) ?? { ox: 0, oy: 0, vx: 0, vy: 0 }; }
}

