// 操偶線（v1.2 第 15.2 節，介面與佔位版）：
// - 灰色扭紋紙繩，1080p 中景約 6–10 px，深灰邊線＋淡色受光邊，明度與背景拉開。
// - 從畫面上方外面垂下，下端以紙環扣在錨點；不畫操控者的手或人影。
// - 受力順序：線先繃緊（弧度消失），肢體才被拉動；擺盪用固定步長的彈簧阻尼模擬，每個 cue 開始時重設，
//   所以重播與上一步會得到一模一樣的畫面。
import {
  BufferAttribute, BufferGeometry, CanvasTexture, DoubleSide, Mesh, MeshStandardMaterial, RepeatWrapping, RingGeometry,
  Vector3, type Material,
} from 'three';
import { finishTexture, makeCanvas, fibers } from './paper';

/** 扭紋紙繩貼圖（沿 v 方向重複） */
export function ropeTexture(): CanvasTexture {
  const [c, g] = makeCanvas(32, 128);
  g.fillStyle = '#9d9b95';
  g.fillRect(0, 0, 32, 128);
  // 扭紋：斜向的深淺條
  for (let y = -32; y < 160; y += 16) {
    g.fillStyle = 'rgba(70,68,64,0.55)';
    g.beginPath(); g.moveTo(0, y); g.lineTo(32, y + 12); g.lineTo(32, y + 17); g.lineTo(0, y + 5); g.closePath(); g.fill();
    g.fillStyle = 'rgba(235,232,224,0.35)';
    g.beginPath(); g.moveTo(0, y + 7); g.lineTo(32, y + 19); g.lineTo(32, y + 21); g.lineTo(0, y + 9); g.closePath(); g.fill();
  }
  fibers(g, 32, 128, 77, 2);
  // 邊線：左深灰、右淡色受光邊
  g.fillStyle = '#3f3e3b'; g.fillRect(0, 0, 4, 128); g.fillRect(29, 0, 3, 128);
  g.fillStyle = 'rgba(240,238,230,0.75)'; g.fillRect(4, 0, 2, 128);
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = RepeatWrapping;
  t.wrapT = RepeatWrapping;
  return t;
}

export function ropeMaterial(): MeshStandardMaterial {
  return new MeshStandardMaterial({ map: ropeTexture(), side: DoubleSide, roughness: 0.95, metalness: 0 });
}

export function ringMaterial(): MeshStandardMaterial {
  return new MeshStandardMaterial({ color: '#ece4d2', side: DoubleSide, roughness: 0.9, metalness: 0 });
}

const SEGMENTS = 28;
const tmpA = new Vector3();

/** 一條紙繩：二次貝茲曲線的帶狀網格＋下端紙環 */
export class PaperString {
  readonly mesh: Mesh;
  readonly ring: Mesh;
  private pos: Float32Array;
  private uv: Float32Array;

  constructor(material: Material, ringMat: Material, renderOrder: number) {
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
    this.mesh = new Mesh(geo, material);
    this.mesh.renderOrder = renderOrder;
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = true;
    this.ring = new Mesh(new RingGeometry(0.04, 0.072, 24), ringMat);
    this.ring.renderOrder = renderOrder + 1;
    this.ring.castShadow = true;
  }

  /**
   * @param top 上端（畫面外）
   * @param bottom 下端（錨點或正在落下的位置）
   * @param bow 鬆垂弧度（世界單位，0＝繃直）
   * @param width 紙繩寬度
   */
  update(top: Vector3, bottom: Vector3, bow: number, width: number, showRing: boolean, visible: boolean): void {
    this.mesh.visible = visible;
    this.ring.visible = visible && showRing;
    if (!visible) return;
    const dx = bottom.x - top.x, dy = bottom.y - top.y;
    const len = Math.hypot(dx, dy) || 1;
    // 垂直於線的方向（在 xy 平面）
    const nx = -dy / len, ny = dx / len;
    const cx = (top.x + bottom.x) / 2 + nx * bow, cy = (top.y + bottom.y) / 2 + ny * bow;
    const cz = (top.z + bottom.z) / 2;
    const vRepeat = len / (width * 5);
    for (let i = 0; i <= SEGMENTS; i++) {
      const t = i / SEGMENTS, it = 1 - t;
      const px = it * it * top.x + 2 * it * t * cx + t * t * bottom.x;
      const py = it * it * top.y + 2 * it * t * cy + t * t * bottom.y;
      const pz = it * it * top.z + 2 * it * t * cz + t * t * bottom.z;
      // 切線
      const tx = 2 * it * (cx - top.x) + 2 * t * (bottom.x - cx);
      const ty = 2 * it * (cy - top.y) + 2 * t * (bottom.y - cy);
      const tl = Math.hypot(tx, ty) || 1;
      const ox = (-ty / tl) * width / 2, oy = (tx / tl) * width / 2;
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
    geo.computeVertexNormals();
    geo.computeBoundingSphere();
    tmpA.copy(bottom);
    this.ring.position.set(tmpA.x, tmpA.y, tmpA.z + 0.012);
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
