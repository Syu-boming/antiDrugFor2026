// 分件紙偶 Rig（介面與佔位版，G4 後凍結介面）：
// - 部件樹：每個部件是一個樞紐群組（pivot），掛在父部件的樞紐座標上，只繞 z 軸旋轉（紙偶在平面內動）。
// - 樞紐點：部件貼圖以 rect 指定相對樞紐的範圍（世界單位，y 向上）。
// - 層序：spec.z 決定同一紙偶內的前後（z 間距 Z_STEP，renderOrder＝角色基準＋z）。
// - 兩節 IK：上臂＋前臂、大腿＋小腿，以解析解求角度（solveTwoBone）。
// - 錨點：操偶線只能扣在手腕背側、手肘外側、膝蓋正面（兒童安全界線第 2 條）。
import { Group, Mesh, PlaneGeometry, Vector2, Vector3, type Material } from 'three';
import { cutPaperMaterial, cutPaperTexture, type ShapeKind } from './paper';
import { Z_STEP } from './layers';
import { clamp } from '../util/math';

export interface PartSpec {
  id: string;
  parent: string | null;
  /** 樞紐點在父部件本地座標的位置 */
  at: [number, number];
  /** 貼圖範圍 [x, y, w, h]，相對自己的樞紐點（y 向上，x,y 為左下角） */
  rect: [number, number, number, number];
  /** 同一紙偶內的前後序（整數，越大越前面） */
  z: number;
  color: string;
  shape: ShapeKind;
  /** 靜止姿勢的旋轉（弧度，逆時針為正） */
  rest?: number;
  /** 旋轉範圍限制 */
  limits?: [number, number];
  decorate?: (g: CanvasRenderingContext2D, W: number, H: number) => void;
}

/** 操偶線錨點只允許這三種 */
export type AnchorName = 'wrist' | 'elbow' | 'knee';

export interface AnchorSpec { part: string; local: [number, number] }

export interface RigSpec {
  id: string;
  parts: PartSpec[];
  anchors: Partial<Record<AnchorName, AnchorSpec>>;
  /** 四肢：IK 用（上段、下段、末端部件） */
  limbs: Record<string, { upper: string; lower: string; end: string; bend: 1 | -1 }>;
}

export class RigPart {
  readonly pivot = new Group();
  readonly mesh: Mesh;
  constructor(readonly spec: PartSpec, material: Material) {
    const [x, y, w, h] = spec.rect;
    const geo = new PlaneGeometry(w, h);
    geo.translate(x + w / 2, y + h / 2, 0); // 讓樞紐點落在原點
    this.mesh = new Mesh(geo, material);
    this.mesh.position.z = spec.z * Z_STEP;
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.pivot.add(this.mesh);
    this.pivot.position.set(spec.at[0], spec.at[1], 0);
    this.pivot.name = spec.id;
  }
  get rest(): number { return this.spec.rest ?? 0; }
}

/** 兩節 IK 的解析解（2D）。回傳上段的世界角度與下段相對上段的角度 */
export function solveTwoBone(sx: number, sy: number, l1: number, l2: number, tx: number, ty: number, bend: 1 | -1): { a1: number; a2: number; reached: boolean } {
  const dx = tx - sx, dy = ty - sy;
  const d = Math.hypot(dx, dy);
  const dd = clamp(d, Math.abs(l1 - l2) + 1e-4, l1 + l2 - 1e-4);
  const base = Math.atan2(dy, dx);
  const A = Math.acos(clamp((l1 * l1 + dd * dd - l2 * l2) / (2 * l1 * dd), -1, 1));
  const B = Math.acos(clamp((l1 * l1 + l2 * l2 - dd * dd) / (2 * l1 * l2), -1, 1));
  return { a1: base + bend * A, a2: bend * (B - Math.PI), reached: d <= l1 + l2 };
}

const tmp3 = new Vector3();

export class Rig {
  /** 紙偶根節點（放在角色腳底的位置） */
  readonly root = new Group();
  readonly parts = new Map<string, RigPart>();
  private order: RigPart[] = [];

  constructor(readonly spec: RigSpec, opts: { renderOrderBase: number; seed: number }) {
    this.root.name = `rig:${spec.id}`;
    spec.parts.forEach((p, i) => {
      const tex = cutPaperTexture({ w: p.rect[2], h: p.rect[3], color: p.color, shape: p.shape, seed: opts.seed + i * 17, decorate: p.decorate });
      const part = new RigPart(p, cutPaperMaterial(tex));
      part.mesh.renderOrder = opts.renderOrderBase + p.z;
      this.parts.set(p.id, part);
      this.order.push(part);
    });
    for (const part of this.order) {
      const parent = part.spec.parent ? this.parts.get(part.spec.parent) : null;
      (parent ? parent.pivot : this.root).add(part.pivot);
    }
    this.resetPose();
  }

  part(id: string): RigPart {
    const p = this.parts.get(id);
    if (!p) throw new Error(`Rig ${this.spec.id} 沒有部件 ${id}`);
    return p;
  }

  resetPose(): void {
    for (const p of this.order) { p.pivot.rotation.set(0, 0, p.rest); p.mesh.scale.set(1, 1, 1); }
  }

  setRot(id: string, r: number): void {
    const p = this.part(id);
    const lim = p.spec.limits;
    p.pivot.rotation.z = lim ? clamp(r, lim[0], lim[1]) : r;
  }

  addRot(id: string, r: number): void { this.setRot(id, this.part(id).pivot.rotation.z + r); }

  /** 祖先部件的旋轉總和（紙偶根本地座標系） */
  chainRot(id: string): number {
    let r = 0;
    let p = this.part(id).spec.parent;
    while (p) { const pp = this.part(p); r += pp.pivot.rotation.z; p = pp.spec.parent; }
    return r;
  }

  /** 部件上某個本地點在「紙偶根本地座標」的位置 */
  localPoint(id: string, local: [number, number] = [0, 0], out = new Vector2()): Vector2 {
    this.root.updateMatrixWorld(true);
    tmp3.set(local[0], local[1], 0);
    this.part(id).pivot.localToWorld(tmp3);
    this.root.worldToLocal(tmp3);
    return out.set(tmp3.x, tmp3.y);
  }

  /** 部件上某個本地點的世界座標 */
  worldPoint(id: string, local: [number, number] = [0, 0], out = new Vector3()): Vector3 {
    this.root.updateMatrixWorld(true);
    out.set(local[0], local[1], 0);
    return this.part(id).pivot.localToWorld(out);
  }

  /** 錨點世界座標（操偶線下端） */
  anchorWorld(name: AnchorName, out = new Vector3()): Vector3 | null {
    const a = this.spec.anchors[name];
    if (!a) return null;
    return this.worldPoint(a.part, a.local, out);
  }

  /** 兩節 IK：讓四肢末端（手腕或腳踝樞紐）到達紙偶根本地座標的 target */
  solveLimb(limb: string, target: Vector2, bendOverride?: 1 | -1): void {
    const L = this.spec.limbs[limb];
    if (!L) return;
    const lower = this.part(L.lower), end = this.part(L.end);
    const l1 = Math.hypot(lower.spec.at[0], lower.spec.at[1]);
    const l2 = Math.hypot(end.spec.at[0], end.spec.at[1]);
    const s = this.localPoint(L.upper);
    const { a1, a2 } = solveTwoBone(s.x, s.y, l1, l2, target.x, target.y, bendOverride ?? L.bend);
    // 骨頭靜止方向朝下（-90°）
    this.setRot(L.upper, a1 + Math.PI / 2 - this.chainRot(L.upper));
    this.setRot(L.lower, a2);
  }

  forEachMesh(fn: (m: Mesh) => void): void { for (const p of this.order) fn(p.mesh); }
}
