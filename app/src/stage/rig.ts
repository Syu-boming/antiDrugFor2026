// 分件紙偶 Rig（G4 後凍結介面）：
// - 部件樹：每個部件是一個樞紐群組（pivot），掛在父部件的樞紐座標上，只繞 z 軸旋轉（紙偶在平面內動）。
// - 部件外觀有兩種：程式產生的佔位紙片（rigspecs.ts），或圖片分件（imagerig.ts 從 parts.json 建立）。
//   沒有 rect 的部件是「虛擬部件」（例如骨盆中心、腳踝），只當樞紐與 IK 末端用。
// - 樞紐點：部件貼圖以 rect 指定相對樞紐的範圍（世界單位，y 向上）。
// - 層序：spec.z 決定同一紙偶內的前後（z 間距 Z_STEP，renderOrder＝角色基準＋z）。
// - 整體外輪廓描邊：每個部件可帶一張「背板」貼圖（白色紙芯邊＋深色卡紙側邊，由部件外形膨脹而成），
//   所有背板都畫在所有部件後面，所以只有整個紙偶的外輪廓露出描邊，部件之間不會各自描邊。
// - 兩節 IK：上段＋下段，以解析解求角度（solveTwoBone）；骨頭的靜止方向由子樞紐位置推得，圖片分件也適用。
// - 錨點：操偶線只能扣在手腕背側、手肘外側、膝蓋正面（兒童安全界線第 2 條）。
import { DoubleSide, Group, Mesh, MeshStandardMaterial, PlaneGeometry, Vector2, Vector3, type Material, type Texture } from 'three';
import { cutPaperMaterial, cutPaperTexture, type ShapeKind } from './paper';
import { Z_STEP } from './layers';
import { clamp } from '../util/math';

export interface PartSpec {
  id: string;
  parent: string | null;
  /** 樞紐點在父部件本地座標的位置 */
  at: [number, number];
  /** 貼圖範圍 [x, y, w, h]，相對自己的樞紐點（y 向上，x,y 為左下角）；null＝虛擬部件 */
  rect: [number, number, number, number] | null;
  /** 同一紙偶內的前後序（整數，越大越前面） */
  z: number;
  color?: string;
  shape?: ShapeKind;
  /** 現成貼圖（圖片分件）；沒有就用 color＋shape 產生佔位紙片 */
  map?: Texture;
  /** 外輪廓背板貼圖（範圍同 rect） */
  backing?: Texture;
  /** 靜止姿勢的旋轉（弧度，逆時針為正） */
  rest?: number;
  /** 旋轉範圍限制 */
  limits?: [number, number];
  decorate?: (g: CanvasRenderingContext2D, W: number, H: number) => void;
}

/** 操偶線錨點只允許這三種 */
export type AnchorName = 'wrist' | 'elbow' | 'knee';

export interface AnchorSpec {
  part: string;
  local: [number, number];
  /** 紙環要包住的肢體寬度（世界單位）與肢體方向（部件本地角度，弧度）；省略時用預設小紙環 */
  width?: number;
  axis?: number;
}

export interface RigSpec {
  id: string;
  parts: PartSpec[];
  anchors: Partial<Record<AnchorName, AnchorSpec>>;
  /** 四肢：IK 用（上段、下段、末端部件） */
  limbs: Record<string, { upper: string; lower: string; end: string; bend: 1 | -1 }>;
  /** 站立高度（世界單位，腳底到頭頂） */
  height?: number;
  /** 語意部件對照（給表演用；沒有的就跳過） */
  roles?: Partial<Record<'pelvis' | 'torso' | 'head' | 'handA' | 'handB' | 'footA' | 'footB', string>>;
}

export class RigPart {
  readonly pivot = new Group();
  readonly mesh: Mesh | null;
  readonly backing: Mesh | null = null;
  /** 長度比例（模擬朝鏡頭的透視縮短，例如坐姿的大腿） */
  lengthScale = 1;
  constructor(readonly spec: PartSpec, material: Material | null, backingMat: Material | null) {
    this.pivot.position.set(spec.at[0], spec.at[1], 0);
    this.pivot.name = spec.id;
    if (!spec.rect || !material) { this.mesh = null; return; }
    const [x, y, w, h] = spec.rect;
    const geo = new PlaneGeometry(w, h);
    geo.translate(x + w / 2, y + h / 2, 0); // 讓樞紐點落在原點
    this.mesh = new Mesh(geo, material);
    this.mesh.position.z = spec.z * Z_STEP;
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.pivot.add(this.mesh);
    if (backingMat) {
      const b = new Mesh(geo, backingMat);
      // 背板放在整個紙偶所有部件的後面（紙偶本地 z＝−0.6 Z_STEP），跟著部件一起轉動、縮放
      b.position.z = -spec.z * Z_STEP - Z_STEP * 0.6;
      b.castShadow = true;
      b.receiveShadow = true;
      this.mesh.add(b);
      this.backing = b;
    }
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

/** 背板材質（白色紙芯＋深色卡紙側邊）：不受燈光明暗影響太多，避免描邊在暗處消失 */
export function backingMaterial(map: Texture, alphaToCoverage: boolean): MeshStandardMaterial {
  return new MeshStandardMaterial({
    map, alphaTest: 0.5, transparent: false, depthWrite: true, side: DoubleSide, roughness: 0.95, metalness: 0, alphaToCoverage,
  });
}

export class Rig {
  /** 紙偶根節點（放在角色腳底的位置） */
  readonly root = new Group();
  readonly parts = new Map<string, RigPart>();
  private order: RigPart[] = [];

  constructor(readonly spec: RigSpec, opts: { renderOrderBase: number; seed: number; alphaToCoverage?: boolean }) {
    this.root.name = `rig:${spec.id}`;
    spec.parts.forEach((p, i) => {
      let mat: Material | null = null;
      let bmat: Material | null = null;
      if (p.rect) {
        const map = p.map ?? cutPaperTexture({ w: p.rect[2], h: p.rect[3], color: p.color ?? '#cccccc', shape: p.shape ?? 'rect', seed: opts.seed + i * 17, decorate: p.decorate });
        const m = cutPaperMaterial(map);
        if (p.map && opts.alphaToCoverage) m.alphaToCoverage = true;
        mat = m;
        if (p.backing) bmat = backingMaterial(p.backing, !!opts.alphaToCoverage);
      }
      const part = new RigPart(p, mat, bmat);
      if (part.mesh) part.mesh.renderOrder = opts.renderOrderBase + 1 + p.z;
      if (part.backing) part.backing.renderOrder = opts.renderOrderBase;
      this.parts.set(p.id, part);
      this.order.push(part);
    });
    for (const part of this.order) {
      const parent = part.spec.parent ? this.parts.get(part.spec.parent) : null;
      (parent ? parent.pivot : this.root).add(part.pivot);
    }
    this.resetPose();
  }

  has(id: string | undefined): id is string { return !!id && this.parts.has(id); }

  part(id: string): RigPart {
    const p = this.parts.get(id);
    if (!p) throw new Error(`Rig ${this.spec.id} 沒有部件 ${id}`);
    return p;
  }

  role(name: keyof NonNullable<RigSpec['roles']>): string | undefined {
    const id = this.spec.roles?.[name] ?? name;
    return this.parts.has(id) ? id : undefined;
  }

  resetPose(): void {
    for (const p of this.order) {
      p.pivot.rotation.set(0, 0, p.rest);
      if (p.mesh) p.mesh.scale.set(1, 1, 1);
      if (p.lengthScale !== 1) this.setLength(p.spec.id, 1);
    }
  }

  setRot(id: string, r: number): void {
    const p = this.part(id);
    const lim = p.spec.limits;
    p.pivot.rotation.z = lim ? clamp(r, lim[0], lim[1]) : r;
  }

  addRot(id: string, r: number): void { this.setRot(id, this.part(id).pivot.rotation.z + r); }

  /** 沿部件本地 y 方向縮短（模擬朝向鏡頭的透視縮短）；子部件的樞紐跟著移動，子部件本身不縮 */
  setLength(id: string, s: number): void {
    const p = this.part(id);
    p.lengthScale = s;
    if (p.mesh) p.mesh.scale.set(1, s, 1);
    for (const child of this.order) {
      if (child.spec.parent !== id) continue;
      child.pivot.position.set(child.spec.at[0], child.spec.at[1] * s, 0);
    }
  }

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
    const p = this.part(a.part);
    return this.worldPoint(a.part, [a.local[0], a.local[1] * p.lengthScale], out);
  }

  /** 錨點所在肢體的世界角度（紙環方向用） */
  anchorAngle(name: AnchorName): number {
    const a = this.spec.anchors[name];
    if (!a) return 0;
    const p = this.part(a.part);
    let r = p.pivot.rotation.z + this.chainRot(a.part);
    // 紙偶根的旋轉與左右翻面
    r = r * Math.sign(this.root.scale.x || 1) + this.root.rotation.z;
    return r + (a.axis ?? 0);
  }

  /** 兩節 IK：讓四肢末端（手腕或腳踝樞紐）到達紙偶根本地座標的 target */
  solveLimb(limb: string, target: Vector2, bendOverride?: 1 | -1): void {
    const L = this.spec.limbs[limb];
    if (!L) return;
    const upper = this.part(L.upper), lower = this.part(L.lower), end = this.part(L.end);
    const l1 = Math.hypot(lower.spec.at[0], lower.spec.at[1] * upper.lengthScale);
    const l2 = Math.hypot(end.spec.at[0], end.spec.at[1] * lower.lengthScale);
    const s = this.localPoint(L.upper);
    const { a1, a2 } = solveTwoBone(s.x, s.y, l1, l2, target.x, target.y, bendOverride ?? L.bend);
    const phi1 = Math.atan2(lower.spec.at[1] * upper.lengthScale, lower.spec.at[0]);
    const phi2 = Math.atan2(end.spec.at[1] * lower.lengthScale, end.spec.at[0]);
    this.setRot(L.upper, a1 - phi1 - this.chainRot(L.upper));
    this.setRot(L.lower, a2 + phi1 - phi2);
  }

  /**
   * 兩種彎向之間連續過渡：w=0 用 L.bend、w=1 用相反彎向。上段角度依 w 內插（走較短的一邊），
   * 下段指向目標；兩端都等於一般的 solveLimb。用在抬手：抬起後手肘改朝外，不會貼到頭頸。
   */
  solveLimbBlend(limb: string, target: Vector2, w: number): void {
    const L = this.spec.limbs[limb];
    if (!L) return;
    if (w <= 1e-4) { this.solveLimb(limb, target); return; }
    if (w >= 1 - 1e-4) { this.solveLimb(limb, target, L.bend === 1 ? -1 : 1); return; }
    const upper = this.part(L.upper), lower = this.part(L.lower), end = this.part(L.end);
    const l1 = Math.hypot(lower.spec.at[0], lower.spec.at[1] * upper.lengthScale);
    const l2 = Math.hypot(end.spec.at[0], end.spec.at[1] * lower.lengthScale);
    const s = this.localPoint(L.upper);
    const A = solveTwoBone(s.x, s.y, l1, l2, target.x, target.y, L.bend);
    const B = solveTwoBone(s.x, s.y, l1, l2, target.x, target.y, L.bend === 1 ? -1 : 1);
    const d = Math.atan2(Math.sin(B.a1 - A.a1), Math.cos(B.a1 - A.a1));
    const a1 = A.a1 + d * w;
    const ex = s.x + l1 * Math.cos(a1), ey = s.y + l1 * Math.sin(a1);
    const a2w = Math.atan2(target.y - ey, target.x - ex);
    const a2 = Math.atan2(Math.sin(a2w - a1), Math.cos(a2w - a1));
    const phi1 = Math.atan2(lower.spec.at[1] * upper.lengthScale, lower.spec.at[0]);
    const phi2 = Math.atan2(end.spec.at[1] * lower.lengthScale, end.spec.at[0]);
    this.setRot(L.upper, a1 - phi1 - this.chainRot(L.upper));
    this.setRot(L.lower, a2 + phi1 - phi2);
  }

  /** 四肢目前的兩段角度：a1＝肩→肘向量的角度（紙偶根座標）、a2＝前臂相對上臂的角度（同 solveTwoBone 的定義） */
  limbAngles(limb: string): { a1: number; a2: number } {
    const L = this.spec.limbs[limb];
    if (!L) return { a1: 0, a2: 0 };
    const s = this.localPoint(L.upper), e = this.localPoint(L.lower), w = this.localPoint(L.end);
    const a1 = Math.atan2(e.y - s.y, e.x - s.x);
    const aw = Math.atan2(w.y - e.y, w.x - e.x);
    return { a1, a2: Math.atan2(Math.sin(aw - a1), Math.cos(aw - a1)) };
  }

  /** 依兩段角度擺四肢（a1、a2 同 limbAngles） */
  setLimbAngles(limb: string, a1: number, a2: number): void {
    const L = this.spec.limbs[limb];
    if (!L) return;
    const upper = this.part(L.upper), lower = this.part(L.lower), end = this.part(L.end);
    const phi1 = Math.atan2(lower.spec.at[1] * upper.lengthScale, lower.spec.at[0]);
    const phi2 = Math.atan2(end.spec.at[1] * lower.lengthScale, end.spec.at[0]);
    this.setRot(L.upper, a1 - phi1 - this.chainRot(L.upper));
    this.setRot(L.lower, a2 + phi1 - phi2);
  }

  /** 兩種彎向中，上臂角度最接近 refA1 的那一個（參考姿勢連續，解就連續；不會在兩種彎向間跳） */
  solveLimbNear(limb: string, target: Vector2, refA1: number): void {
    const L = this.spec.limbs[limb];
    if (!L) return;
    const [l1, l2] = this.limbLengths(limb);
    const s = this.localPoint(L.upper);
    const A = solveTwoBone(s.x, s.y, l1, l2, target.x, target.y, 1);
    const B = solveTwoBone(s.x, s.y, l1, l2, target.x, target.y, -1);
    const dist = (a: number): number => Math.abs(Math.atan2(Math.sin(a - refA1), Math.cos(a - refA1)));
    const pick = dist(A.a1) <= dist(B.a1) ? A : B;
    this.setLimbAngles(limb, pick.a1, pick.a2);
  }

  /** 四肢兩段長度（世界單位，含縮短比例） */
  limbLengths(limb: string): [number, number] {
    const L = this.spec.limbs[limb];
    if (!L) return [0, 0];
    const upper = this.part(L.upper), lower = this.part(L.lower), end = this.part(L.end);
    return [Math.hypot(lower.spec.at[0], lower.spec.at[1] * upper.lengthScale), Math.hypot(end.spec.at[0], end.spec.at[1] * lower.lengthScale)];
  }

  forEachMesh(fn: (m: Mesh) => void): void {
    for (const p of this.order) { if (p.mesh) fn(p.mesh); if (p.backing) fn(p.backing); }
  }
}
