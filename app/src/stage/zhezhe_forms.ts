// 折折的摺紙變形造型（FX13）：每種造型都是「一張紙用鉸鏈摺起來」——setOpen(0) 是摺好的扁紙包（厚度都在本地 z 很薄），
// setOpen(1) 是攤開的完成形。中間每片紙都繞摺線轉動（剛體旋轉、不拉伸、不交叉淡化），所以看起來是真的在摺／攤開。
//   card       題卡：田字四格，先攤開右半、再攤開上半（正面白色、背面淺橙；摺痕留在卡上）
//   plane      紙飛機：機身兩片龍骨＋兩片機翼，從扁平的鏢形攤開機翼
//   megaphone  傳聲筒：8 片扇面像摺扇一樣一片片打開，再合成圓錐（外淺橙、內白）
//   magnifier  放大鏡：8 片扇面攤成八角紙框（上緣一對貓耳）＋兩節摺紙柄＋半透明描圖紙鏡片
//   lantern    燈籠：手風琴摺的貓耳小燈籠，由扁平圓盤往上拉開；glow 0–1 柔和亮起（只做慢漸變，不閃）
//   hat        紙帽子：前後兩片從併攏張開（a0_c004 摺錯的笑點）
//   sheet      一張方形燈籠紙（a0_c002 登場前）：收摺時「摺、摺、摺」三下（對摺、再對摺、斜摺）成小三角紙包
//   frog       紙青蛙（a1_c001 摺燈籠摺錯）：後腿、前腳、眼睛翻片依序攤開（G5 開場＋第一幕代理新增）
// 單位：折折身高＝1（由 zhezhe.ts 的外層縮放成世界單位）。
import {
  AdditiveBlending, BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide, Group, Matrix4, Mesh,
  MeshStandardMaterial, Quaternion, SRGBColorSpace, Sprite, SpriteMaterial, Vector3, type Material,
} from 'three';
import { clamp, smoothstep } from '../util/math';
import { PAPER_T, PaperBuilder, ZZ_COLORS, outlineGeometry, paperMaterial, triNormal, v3 } from './zhezhe_paper';

export type FoldForm = 'idle' | 'card' | 'plane' | 'megaphone' | 'magnifier' | 'lantern' | 'hat' | 'sheet' | 'frog';
export const FOLD_FORMS: FoldForm[] = ['idle', 'card', 'plane', 'megaphone', 'magnifier', 'lantern', 'hat', 'sheet', 'frog'];

/** 建立部件時共用的設定 */
export interface PartCtx {
  mat: MeshStandardMaterial;
  outlineMat: Material | null;
  /** 外輪廓寬（折折身高單位） */
  outlineW: number;
  castShadow: boolean;
  renderOrder: number;
  /** 三角面計數（含外輪廓） */
  tris: { n: number };
  /** 存在感 uniform（紙面常數自發光，見 zhezhe_paper.ts） */
  presence: { value: number };
  /** 直射光反應倍率（見 paperMaterial 的 direct） */
  direct: number;
}

/** 由 PaperBuilder 建立一個部件（紙＋外輪廓） */
export function partMesh(b: PaperBuilder, ctx: PartCtx, o: { outline?: boolean; mat?: Material; name?: string } = {}): Group {
  const g = new Group();
  const geo = b.build();
  const m = new Mesh(geo, o.mat ?? ctx.mat);
  m.castShadow = ctx.castShadow;
  m.renderOrder = ctx.renderOrder;
  if (o.name) m.name = o.name;
  g.add(m);
  ctx.tris.n += b.count;
  if (ctx.outlineMat && o.outline !== false && ctx.outlineW > 0) {
    const ol = new Mesh(outlineGeometry(geo, ctx.outlineW), ctx.outlineMat);
    ol.renderOrder = ctx.renderOrder;
    g.add(ol);
    ctx.tris.n += b.count;
  }
  return g;
}

export interface FormObject {
  readonly group: Group;
  /** 0＝摺好的扁紙包，1＝完成形；t＝目前秒數（燈籠微動用） */
  setOpen(open: number, t: number): void;
  /** 燈籠亮度 0–1（其他造型忽略） */
  setGlow?(g: number): void;
}

const quatAxis = (x: number, y: number, z: number, a: number): Quaternion => new Quaternion().setFromAxisAngle(new Vector3(x, y, z).normalize(), a);
const easeIO = (t: number): number => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const sub = (open: number, a: number, b: number): number => easeIO((open - a) / (b - a));

/** 小三角耳朵（紙片，正面淺橙、背面白、中間一道谷摺） */
function earSlab(b: PaperBuilder, base0: Vector3, base1: Vector3, tip: Vector3, front = ZZ_COLORS.front, back = ZZ_COLORS.back): void {
  const mid = base0.clone().lerp(base1, 0.5);
  const n = triNormal(base0, base1, tip);
  mid.addScaledVector(n, -0.012);
  b.slab([base0, mid, tip], front, back);
  b.slab([mid, base1, tip], front, back);
}

// ---------------------------------------------------------------------------------------------------------------------
// 題卡：田字四格，鉸鏈在卡片中心的十字摺線
// ---------------------------------------------------------------------------------------------------------------------
export class CardForm implements FormObject {
  readonly group = new Group();
  private card = new Group();
  private hingeV = new Group();
  private hingeH = new Group();
  private hingeH2 = new Group();
  constructor(ctx: PartCtx, readonly w = 1.6, readonly h = 1.1, readonly cy = 0.78) {
    const qw = w / 2, qh = h / 2, t = PAPER_T;
    // 正面（朝觀眾）白、背面淺橙：摺好時看到淺橙紙包，攤開後是白色卡面
    const quad = (x0: number, y0: number, x1: number, y1: number): PaperBuilder => new PaperBuilder().slab(
      [v3(x0, y0, 0), v3(x1, y0, 0), v3(x1, y1, 0), v3(x0, y1, 0)], ZZ_COLORS.back, ZZ_COLORS.front);
    const p0 = partMesh(quad(-qw, -qh, 0, 0), ctx);
    const p1 = partMesh(quad(0, -qh, qw, 0), ctx);
    const p2 = partMesh(quad(-qw, 0, 0, qh), ctx);
    const p3 = partMesh(quad(0, 0, qw, qh), ctx);
    // 鉸鏈軸在紙面前方 o 處、紙片放在 −o：轉 180° 時紙片疊在前一層上面（間隔一張紙厚），不會共平面閃爍。
    // 摺好時由後往前：p0（0）、p2（t）、p3（2t）、p1（3t）；攤開時 hingeH2 的軸和 hingeH 重合（世界 z＝t/2）。
    this.hingeH.position.z = t / 2; p2.position.z = -t / 2;
    this.hingeV.position.z = 1.5 * t; p1.position.z = -1.5 * t;
    this.hingeH2.position.z = -t; p3.position.z = -t / 2;
    this.hingeH.add(p2);
    this.hingeH2.add(p3);
    this.hingeV.add(p1, this.hingeH2);
    this.card.add(p0, this.hingeH, this.hingeV);
    this.card.position.y = cy;
    this.group.add(this.card);
  }
  setOpen(open: number): void {
    const e = 0.03;
    const a1 = sub(open, 0, 0.5), a2 = sub(open, 0.42, 1);
    // 先攤開右半（垂直摺線），再攤開上半（水平摺線）
    this.hingeV.rotation.y = -(Math.PI - e) * (1 - a1);
    const h = (Math.PI - e) * (1 - a2);
    this.hingeH.rotation.x = h;
    this.hingeH2.rotation.x = h;
    // 紙包置中：攤開時往右上長，整張卡的中心最後回到原點
    this.card.position.x = (this.w / 4) * (1 - a1);
    this.card.position.y = this.cy + (this.h / 4) * (1 - a2);
  }
  /** 卡片四角（form 本地座標，左下、右下、右上、左上；完全攤開時） */
  corners(): Vector3[] {
    const qw = this.w / 2, qh = this.h / 2;
    return [v3(-qw, this.cy - qh, 0), v3(qw, this.cy - qh, 0), v3(qw, this.cy + qh, 0), v3(-qw, this.cy + qh, 0)];
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// 紙飛機：機頭朝本地 +x；四片紙都以機身頂線（x 軸）為鉸鏈
// ---------------------------------------------------------------------------------------------------------------------
export class PlaneForm implements FormObject {
  readonly group = new Group();
  private body = new Group();
  private wingL = new Group();
  private wingR = new Group();
  private keelL = new Group();
  private keelR = new Group();
  constructor(ctx: PartCtx, inkMat: Material) {
    const L0 = 0.62, L1 = -0.55;
    const wing = new PaperBuilder().slab([v3(L0, 0, 0), v3(L1, 0, 0), v3(L1 + 0.06, 0.52, 0)], ZZ_COLORS.back, ZZ_COLORS.front);
    const wingR = new PaperBuilder().slab([v3(L1, 0, 0), v3(L0, 0, 0), v3(L1 + 0.06, 0.52, 0)], ZZ_COLORS.front, ZZ_COLORS.back);
    const keel = new PaperBuilder().slab([v3(L1, 0, 0), v3(L0, 0, 0), v3(L1 + 0.08, -0.16, 0)], ZZ_COLORS.front, ZZ_COLORS.back);
    const keelR = new PaperBuilder().slab([v3(L0, 0, 0), v3(L1, 0, 0), v3(L1 + 0.08, -0.16, 0)], ZZ_COLORS.back, ZZ_COLORS.front);
    const t = PAPER_T;
    this.wingL.add(partMesh(wing, ctx)); this.wingL.position.z = 1.5 * t;
    this.wingR.add(partMesh(wingR, ctx)); this.wingR.position.z = -1.5 * t;
    this.keelL.add(partMesh(keel, ctx)); this.keelL.position.z = 0.5 * t;
    this.keelR.add(partMesh(keelR, ctx)); this.keelR.position.z = -0.5 * t;
    // 機頭的小眼睛（每片龍骨外側一顆）：讓孩子看得出「是折折變的」
    const eye = (z: number): Mesh => {
      const m = new Mesh(discGeometry(0.022, 12), inkMat);
      m.position.set(0.36, -0.035, z);
      return m;
    };
    this.keelL.add(eye(PAPER_T * 0.5 + 0.002));
    const er = eye(-PAPER_T * 0.5 - 0.002); er.rotation.y = Math.PI; this.keelR.add(er);
    ctx.tris.n += 24;
    this.body.add(this.wingL, this.wingR, this.keelL, this.keelR);
    this.body.position.y = 0.55;
    this.group.add(this.body);
  }
  setOpen(open: number): void {
    const w = sub(open, 0.25, 1), k = sub(open, 0, 0.6);
    this.wingL.rotation.x = (Math.PI / 2 - 0.16) * w;
    this.wingR.rotation.x = -(Math.PI / 2 - 0.16) * w;
    this.keelL.rotation.x = 0.2 * k;
    this.keelR.rotation.x = -0.2 * k;
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// 扇面鏈：N 片楔形紙片，相鄰兩片以共用的母線為鉸鏈。摺好＝手風琴（交替 ±180°）疊成一片楔形；打開＝圓錐或平面圓環
// ---------------------------------------------------------------------------------------------------------------------
interface FanOptions { n: number; alpha: number; r0: number; r1: number; front: string; back: string; stagger?: number }

export class FanChain {
  readonly root = new Group();
  readonly panels: Group[] = [];
  private hinges: Group[] = [];
  private openAngle = 0;
  private stagger: number;
  readonly beta: number;
  constructor(ctx: PartCtx, readonly o: FanOptions) {
    const { n, alpha, r0, r1 } = o;
    const d = (k: number): Vector3 => new Vector3(Math.cos(alpha), Math.sin(alpha) * Math.cos((2 * Math.PI * k) / n), Math.sin(alpha) * Math.sin((2 * Math.PI * k) / n));
    const d0 = d(0), d1 = d(1), d2 = d(2);
    this.beta = Math.acos(clamp(d0.dot(d1), -1, 1));
    const n0 = new Vector3().crossVectors(d0, d1).normalize(), n1 = new Vector3().crossVectors(d1, d2).normalize();
    const phi = Math.acos(clamp(n0.dot(n1), -1, 1));
    // 第 0 片的座標系：X＝母線 d0，Y＝面內朝 d1，Z＝法線
    const X = d0.clone(), Y = d1.clone().addScaledVector(d0, -d1.dot(d0)).normalize(), Z = new Vector3().crossVectors(X, Y);
    this.root.quaternion.setFromRotationMatrix(new Matrix4().makeBasis(X, Y, Z));
    // 選摺角正負：讓鏈的最後一條母線回到 d0（圓錐閉合）
    this.openAngle = phi < 1e-4 ? 0 : (this.closure(phi) < this.closure(-phi) ? phi : -phi);
    this.stagger = o.stagger ?? 0.55;
    const b = this.beta, c = Math.cos(b), s = Math.sin(b);
    const geo = (): PaperBuilder => new PaperBuilder().slab([v3(r0, 0, 0), v3(r1, 0, 0), v3(r1 * c, r1 * s, 0), v3(r0 * c, r0 * s, 0)], o.front, o.back);
    let parent: Group = this.root;
    for (let i = 0; i < n; i++) {
      const panel = partMesh(geo(), ctx);
      if (i === 0) {
        this.root.add(panel);
      } else {
        const hinge = new Group();
        const off = (i % 2 === 1 ? 1 : -1) * PAPER_T * 0.5;
        hinge.position.z = off;
        panel.position.z = -off;
        hinge.userData.off = off;
        parent.add(hinge);
        hinge.add(panel);
        this.hinges.push(hinge);
      }
      this.panels.push(panel);
      parent = panel;
    }
  }
  /** 只用旋轉計算鏈末端母線和 d0 的夾角（選摺角正負用） */
  private closure(phi: number): number {
    const q = new Quaternion();
    const qb = quatAxis(0, 0, 1, this.beta);
    for (let i = 1; i < this.o.n; i++) q.multiply(qb).multiply(quatAxis(1, 0, 0, phi));
    const end = new Vector3(Math.cos(this.beta), Math.sin(this.beta), 0).applyQuaternion(q);
    return end.angleTo(new Vector3(1, 0, 0));
  }
  set(open: number): void {
    const n = this.o.n, st = this.stagger;
    const qb = quatAxis(0, 0, 1, this.beta);
    this.hinges.forEach((h, idx) => {
      const i = idx + 1;
      const packed = (i % 2 === 1 ? 1 : -1) * (Math.PI - 0.035);
      const oi = easeIO(open * (1 + st) - (st * (i - 1)) / Math.max(1, n - 2));
      const a = packed + (this.openAngle - packed) * oi;
      h.quaternion.copy(qb).multiply(quatAxis(1, 0, 0, a));
    });
  }
}

export class MegaphoneForm implements FormObject {
  readonly group = new Group();
  private fan: FanChain;
  constructor(ctx: PartCtx) {
    // 外淺橙、內白：第 0 片的法線朝圓錐內側，所以正面（+Z）給白色
    this.fan = new FanChain(ctx, { n: 8, alpha: 0.4, r0: 0.12, r1: 0.78, front: ZZ_COLORS.back, back: ZZ_COLORS.front, stagger: 0.6 });
    const holder = new Group();
    holder.add(this.fan.root);
    // 軸（本地 +x）朝觀眾右前方、微微上揚；整體置中在折折原本的位置
    holder.position.set(-0.3, 0.52, 0);
    holder.quaternion.copy(quatAxis(0, 1, 0, -0.62)).multiply(quatAxis(0, 0, 1, 0.12));
    this.group.add(holder);
  }
  setOpen(open: number): void { this.fan.set(open); }
}

export class MagnifierForm implements FormObject {
  readonly group = new Group();
  private fan: FanChain;
  private handleA = new Group();
  private handleB = new Group();
  private lens: Mesh;
  private ears: Group[] = [];
  constructor(ctx: PartCtx) {
    const R = 0.3, W = 0.075;
    this.fan = new FanChain(ctx, { n: 8, alpha: Math.PI / 2, r0: R - W, r1: R, front: ZZ_COLORS.front, back: ZZ_COLORS.back, stagger: 0.5 });
    const ring = new Group();
    ring.add(this.fan.root);
    ring.rotation.y = -Math.PI / 2; // 環面朝觀眾（本地 +x → 世界 +z）
    ring.position.set(0, 0.62, 0);
    // 柄：掛在第 5 片的起始母線外端（畫面右下 315°），兩節手風琴摺
    const seg = 0.19, hw = 0.036;
    const hb = (): PaperBuilder => new PaperBuilder().slab([v3(0, -hw, 0), v3(seg, -hw, 0), v3(seg, hw, 0), v3(0, hw, 0)], ZZ_COLORS.front, ZZ_COLORS.back);
    const a = partMesh(hb(), ctx), b = partMesh(hb(), ctx);
    this.handleA.position.set(R, 0, PAPER_T);
    this.handleA.add(a);
    this.handleB.position.set(seg, 0, 0);
    this.handleB.add(b);
    a.add(this.handleB);
    this.fan.panels[5].add(this.handleA);
    // 上緣一對貓耳：掛在第 0、7 片外緣
    const earAt = (panel: number, ang: number): void => {
      const eb = new PaperBuilder();
      const c = Math.cos(ang), s = Math.sin(ang);
      const radial = v3(c, s, 0), tang = v3(-s, c, 0);
      const base = radial.clone().multiplyScalar(R - 0.01);
      earSlab(eb, base.clone().addScaledVector(tang, -0.065), base.clone().addScaledVector(tang, 0.065), base.clone().addScaledVector(radial, 0.13).addScaledVector(tang, 0.01));
      const ear = partMesh(eb, ctx);
      ear.position.z = PAPER_T * 0.6;
      this.fan.panels[panel].add(ear);
      this.ears.push(ear);
    };
    earAt(0, 0.42);
    earAt(7, 0.36);
    // 鏡片：半透明描圖紙（不反光、不發光）
    this.lens = new Mesh(discGeometry(R - W + 0.01, 32), new MeshStandardMaterial({
      color: '#fdf8ee', roughness: 1, metalness: 0, transparent: true, opacity: 0.42, depthWrite: false, side: DoubleSide,
    }));
    this.lens.position.set(0, 0.62, -0.002);
    this.lens.renderOrder = ctx.renderOrder + 1;
    ctx.tris.n += 32;
    this.group.add(ring, this.lens);
  }
  setOpen(open: number): void {
    this.fan.set(open);
    const h = sub(open, 0.45, 0.95);
    this.handleA.rotation.y = -(Math.PI - 0.04) * (1 - h);
    this.handleB.rotation.y = (Math.PI - 0.04) * (1 - h);
    const s = smoothstep(0.82, 1, open);
    this.lens.scale.setScalar(Math.max(1e-3, s));
    this.lens.visible = s > 0.002;
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// 燈籠：手風琴摺的圓燈籠（橫向摺 7 道、周圍 12 面），上緣竹圈一對貓耳；摺好時是扁平的圓盤
// ---------------------------------------------------------------------------------------------------------------------
export class LanternForm implements FormObject {
  readonly group = new Group();
  private geo: BufferGeometry;
  private mesh: Mesh;
  private mat: MeshStandardMaterial;
  private top = new Group();
  private bottom: Group;
  private halo: Sprite;
  private readonly M = 7;
  private readonly NA = 12;
  private glow = 0;
  constructor(ctx: PartCtx) {
    const { M, NA } = this;
    const rings = 2 * M + 1;
    const triCount = (rings - 1) * NA * 2;
    const pos = new Float32Array(triCount * 9);
    const col = new Float32Array(triCount * 9), bak = new Float32Array(triCount * 9), edg = new Float32Array(triCount * 9), uv = new Float32Array(triCount * 6);
    const cf = new Color(ZZ_COLORS.front), cb = new Color(ZZ_COLORS.back);
    // 每個四邊形 (a,b,c,d) 兩個三角形 (a,b,d)、(b,c,d)：橫線與直線是摺痕，對角線 b–d 不畫
    // (a,b,d)：對角線是頂點 0 的對邊；(b,c,d)：對角線是頂點 1 的對邊
    let t = 0;
    for (let k = 0; k < rings - 1; k++) for (let j = 0; j < NA; j++) for (let s = 0; s < 2; s++) {
      const hidden = s === 0 ? [true, false, false] : [false, true, false];
      for (let v = 0; v < 3; v++) {
        const o = t * 9 + v * 3;
        col[o] = cf.r; col[o + 1] = cf.g; col[o + 2] = cf.b;
        bak[o] = cb.r; bak[o + 1] = cb.g; bak[o + 2] = cb.b;
        for (let c = 0; c < 3; c++) edg[o + c] = c === v ? 1 : (hidden[c] ? 1 : 0);
        uv[t * 6 + v * 2] = (j + (v === 0 ? 1 : 0)) * 0.12; uv[t * 6 + v * 2 + 1] = (k + (v === 2 ? 1 : 0)) * 0.05;
      }
      t++;
    }
    this.geo = new BufferGeometry();
    this.geo.setAttribute('position', new BufferAttribute(pos, 3));
    this.geo.setAttribute('normal', new BufferAttribute(new Float32Array(triCount * 9), 3));
    this.geo.setAttribute('color', new BufferAttribute(col, 3));
    this.geo.setAttribute('aBack', new BufferAttribute(bak, 3));
    this.geo.setAttribute('aEdge', new BufferAttribute(edg, 3));
    this.geo.setAttribute('uv', new BufferAttribute(uv, 2));
    this.mat = paperMaterial({ presence: ctx.presence, direct: ctx.direct });
    this.mat.emissive = new Color('#ffae5e');
    this.mat.emissiveIntensity = 0;
    this.mesh = new Mesh(this.geo, this.mat);
    this.mesh.castShadow = ctx.castShadow;
    this.mesh.renderOrder = ctx.renderOrder;
    this.mesh.frustumCulled = false;
    ctx.tris.n += triCount;
    // 底座竹圈（實心扁八角）與上緣竹圈（帶貓耳）
    const rimPts = (r: number, y0: number, y1: number): Vector3[] => {
      const p: Vector3[] = [];
      for (let j = 0; j < NA; j++) { const a = (j / NA) * Math.PI * 2; p.push(v3(Math.cos(a) * r, y0, Math.sin(a) * r), v3(Math.cos(a) * r, y1, Math.sin(a) * r)); }
      return p;
    };
    this.bottom = partMesh(new PaperBuilder().hull(rimPts(0.17, -0.03, 0), () => ZZ_COLORS.bamboo), ctx);
    const tb = new PaperBuilder().hull(rimPts(0.15, 0, 0.03), () => ZZ_COLORS.bamboo);
    earSlab(tb, v3(-0.15, 0.02, 0.06), v3(-0.03, 0.02, 0.13), v3(-0.11, 0.17, 0.1));
    earSlab(tb, v3(0.03, 0.02, 0.13), v3(0.15, 0.02, 0.06), v3(0.11, 0.17, 0.1));
    this.top.add(partMesh(tb, ctx));
    // 柔和泛光（FX14）：暖色徑向漸層，透明度只隨 glow 慢慢變
    this.halo = new Sprite(new SpriteMaterial({ map: haloTexture(), color: '#ffcf96', transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
    this.halo.scale.set(1.25, 1.25, 1);
    this.halo.renderOrder = ctx.renderOrder + 2;
    this.group.add(this.mesh, this.bottom, this.top, this.halo);
  }
  setGlow(g: number): void {
    this.glow = clamp(g);
    this.mat.emissiveIntensity = 0.6 * this.glow;
    (this.halo.material as SpriteMaterial).opacity = 0.3 * this.glow;
    this.halo.visible = this.glow > 0.003;
  }
  setOpen(open: number): void {
    const { M, NA } = this;
    const rings = 2 * M + 1;
    const o = easeIO(open);
    const yb = 0.12, H = 0.04 + 0.58 * o, depth = 0.06 + (0.03 - 0.06) * o, Rmax = 0.27;
    const ring = (k: number, j: number): Vector3 => {
      const u = k / (rings - 1);
      const r = Rmax * (0.6 + 0.4 * Math.sin(Math.PI * u)) - (k % 2 === 1 ? depth : 0);
      const a = ((j % NA) / NA) * Math.PI * 2 + Math.PI / NA;
      return v3(Math.cos(a) * r, yb + H * u, Math.sin(a) * r);
    };
    const pos = this.geo.getAttribute('position') as BufferAttribute;
    const nor = this.geo.getAttribute('normal') as BufferAttribute;
    let t = 0;
    for (let k = 0; k < rings - 1; k++) for (let j = 0; j < NA; j++) {
      // 從外面看逆時針＝法線朝外（正面淺橙在外、背面白在內）
      const a = ring(k, j + 1), b = ring(k, j), c = ring(k + 1, j), d = ring(k + 1, j + 1);
      for (const tri of [[a, b, d], [b, c, d]]) {
        const n = triNormal(tri[0], tri[1], tri[2]);
        for (let v = 0; v < 3; v++) { pos.setXYZ(t * 3 + v, tri[v].x, tri[v].y, tri[v].z); nor.setXYZ(t * 3 + v, n.x, n.y, n.z); }
        t++;
      }
    }
    pos.needsUpdate = true;
    nor.needsUpdate = true;
    this.geo.computeBoundingSphere();
    this.bottom.position.y = yb;
    this.top.position.y = yb + H;
    this.halo.position.set(0, yb + H * 0.5, -0.05);
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// 紙帽子：前後兩片，以頂點橫軸為鉸鏈張開；帽簷是往上摺的白色紙條；頂端一對小貓耳
// ---------------------------------------------------------------------------------------------------------------------
export class HatForm implements FormObject {
  readonly group = new Group();
  private front = new Group();
  private back = new Group();
  constructor(ctx: PartCtx) {
    const apex = 0.42;
    const panel = (sign: 1 | -1): PaperBuilder => {
      const b = new PaperBuilder();
      const f = sign === 1 ? ZZ_COLORS.front : ZZ_COLORS.back, k = sign === 1 ? ZZ_COLORS.back : ZZ_COLORS.front;
      const pts = [v3(-0.34, 0, 0), v3(0.34, 0, 0), v3(0.3, 0.1, 0), v3(0, apex, 0), v3(-0.3, 0.1, 0)].map((p) => p.add(v3(0, -apex, 0)));
      b.slab(sign === 1 ? pts : [...pts].reverse(), f, k);
      // 帽簷：往上摺的紙條（露出另一面的顏色）
      const brim = [v3(-0.36, -apex - 0.005, 0), v3(0.36, -apex - 0.005, 0), v3(0.355, -apex + 0.085, 0), v3(-0.355, -apex + 0.085, 0)];
      b.slab(sign === 1 ? brim : [...brim].reverse(), k, f, PAPER_T, PAPER_T * 1.1 * sign);
      return b;
    };
    this.front.add(partMesh(panel(1), ctx));
    this.back.add(partMesh(panel(-1), ctx));
    const ears = new PaperBuilder();
    earSlab(ears, v3(-0.17, -0.2, 0), v3(-0.05, -0.08, 0), v3(-0.17, -0.02, 0));
    earSlab(ears, v3(0.05, -0.08, 0), v3(0.17, -0.2, 0), v3(0.17, -0.02, 0));
    const earM = partMesh(ears, ctx);
    earM.position.z = PAPER_T * 0.5;
    this.front.add(earM);
    const pivot = new Group();
    pivot.position.y = 0.2 + apex;
    pivot.add(this.front, this.back);
    this.group.add(pivot);
  }
  setOpen(open: number): void {
    const a = 0.015 + 0.3 * sub(open, 0.1, 1);
    this.front.rotation.x = a;
    this.back.rotation.x = -a;
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// 依序摺：每一步是「繞世界中一條固定摺線轉 θ」，受影響的紙片矩陣＝最後一步⋯第一步的旋轉相乘（攤開時反過來，最後一步先打開）
// ---------------------------------------------------------------------------------------------------------------------
export interface FoldStep {
  /** 摺線上一點、方向（攤平時的座標） */
  point: Vector3;
  dir: Vector3;
  /** 摺好時的角度（右手定則，繞 dir） */
  angle: number;
  /** 在「收摺進度」0–1 中的時段 */
  window: [number, number];
  /** 被這一步帶動的紙片編號 */
  panels: number[];
}

export class FoldSequence implements FormObject {
  readonly group = new Group();
  private meshes: Group[] = [];
  private tmp = new Matrix4();
  constructor(ctx: PartCtx, panels: Vector3[][], private steps: FoldStep[], front: string, back: string) {
    for (const pts of panels) {
      const m = partMesh(new PaperBuilder().slab(pts, front, back), ctx);
      m.matrixAutoUpdate = false;
      this.meshes.push(m);
      this.group.add(m);
    }
  }
  setOpen(open: number): void {
    const closed = 1 - clamp(open);
    const rots = this.steps.map((s) => {
      const th = s.angle * easeIO((closed - s.window[0]) / (s.window[1] - s.window[0]));
      const p = s.point;
      return new Matrix4().makeTranslation(p.x, p.y, p.z).multiply(new Matrix4().makeRotationAxis(s.dir.clone().normalize(), th)).multiply(new Matrix4().makeTranslation(-p.x, -p.y, -p.z));
    });
    this.meshes.forEach((m, i) => {
      this.tmp.identity();
      this.steps.forEach((s, k) => { if (s.panels.includes(i)) this.tmp.premultiply(rots[k]); });
      m.matrix.copy(this.tmp);
      m.matrixWorldNeedsUpdate = true;
    });
  }
}

/**
 * 一張方形燈籠紙（站立、正面淺橙朝觀眾）。收摺三步：右半往前對摺 → 上半往下對摺 → 沿對角線斜摺，成小三角紙包。
 * rise：0＝平躺在桌上（以底邊為鉸鏈），1＝立起來（a0_c002 開頭「紙自己立起來」）。
 */
export class SheetForm implements FormObject {
  readonly group = new Group();
  private seq: FoldSequence;
  private riser = new Group();
  static readonly SIZE = 0.72;
  static readonly CY = 0.42;
  /** 三下摺各自的時段（收摺進度）；落點＝時段終點 */
  static readonly WINDOWS: [number, number][] = [[0, 0.28], [0.34, 0.62], [0.68, 0.96]];
  constructor(ctx: PartCtx) {
    const h = SheetForm.SIZE / 2, cy = SheetForm.CY, t = PAPER_T;
    const P = (x: number, y: number): Vector3 => v3(x, cy + y, 0);
    // 四個象限各沿「中心→外角」對角線切成兩個三角形；A＝貼著水平中線的一半（第三步斜摺會帶動）
    const tris: Vector3[][] = [
      [P(0, 0), P(-h, 0), P(-h, -h)], [P(0, 0), P(-h, -h), P(0, -h)], // 0、1：左下（A、B）
      [P(0, 0), P(h, -h), P(h, 0)], [P(0, 0), P(0, -h), P(h, -h)], // 2、3：右下（A、B）
      [P(0, 0), P(-h, h), P(-h, 0)], [P(0, 0), P(0, h), P(-h, h)], // 4、5：左上（A、B）
      [P(0, 0), P(h, 0), P(h, h)], [P(0, 0), P(h, h), P(0, h)], // 6、7：右上（A、B）
    ];
    const W = SheetForm.WINDOWS;
    const steps: FoldStep[] = [
      // 1. 右半往前（朝觀眾）對摺到左半上：繞 +y 轉 −π
      { point: v3(0, cy, 0.5 * t), dir: v3(0, 1, 0), angle: -(Math.PI - 0.03), window: W[0], panels: [2, 3, 6, 7] },
      // 2. 上半往下（朝觀眾）對摺：繞 +x 轉 +π
      { point: v3(0, cy, 1.5 * t), dir: v3(1, 0, 0), angle: Math.PI - 0.03, window: W[1], panels: [4, 5, 6, 7] },
      // 3. 沿左下象限對角線斜摺（朝觀眾）
      { point: v3(0, cy, 3.5 * t), dir: v3(-1, -1, 0), angle: -(Math.PI - 0.05), window: W[2], panels: [0, 2, 4, 6] },
    ];
    this.seq = new FoldSequence(ctx, tris, steps, ZZ_COLORS.front, ZZ_COLORS.back);
    // 紙包往中間靠：最後的三角形在左下，收摺時整體往右上移回中心
    this.riser.add(this.seq.group);
    this.riser.position.y = cy - h;
    this.seq.group.position.y = -(cy - h);
    this.group.add(this.riser);
  }
  setOpen(open: number): void {
    this.seq.setOpen(open);
    const c = 1 - clamp(open), h = SheetForm.SIZE / 2;
    const k1 = easeIO(c / 0.62), k3 = easeIO((c - 0.68) / 0.28);
    this.seq.group.position.x = (h / 2) * k1 + (h / 6) * k3;
  }
  /** 0＝平躺（往舞台後方倒下），1＝立起 */
  setRise(r: number): void { this.riser.rotation.x = -(Math.PI / 2) * (1 - easeIO(r)); }
}

// ---------------------------------------------------------------------------------------------------------------------
// 小工具
// ---------------------------------------------------------------------------------------------------------------------
export function discGeometry(r: number, seg: number, sy = 1): BufferGeometry {
  const pos: number[] = [];
  for (let i = 0; i < seg; i++) {
    const a0 = (i / seg) * Math.PI * 2, a1 = ((i + 1) / seg) * Math.PI * 2;
    pos.push(0, 0, 0, Math.cos(a0) * r, Math.sin(a0) * r * sy, 0, Math.cos(a1) * r, Math.sin(a1) * r * sy, 0);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(new Float32Array(pos), 3));
  g.computeVertexNormals();
  return g;
}

let haloTex: CanvasTexture | null = null;
function haloTexture(): CanvasTexture {
  if (haloTex) return haloTex;
  const S = 128;
  const c = document.createElement('canvas');
  c.width = S; c.height = S;
  const g = c.getContext('2d')!;
  const grd = g.createRadialGradient(S / 2, S / 2, 2, S / 2, S / 2, S / 2);
  grd.addColorStop(0, 'rgba(255,220,170,0.9)');
  grd.addColorStop(0.35, 'rgba(255,200,140,0.45)');
  grd.addColorStop(1, 'rgba(255,190,120,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, S, S);
  haloTex = new CanvasTexture(c);
  haloTex.colorSpace = SRGBColorSpace;
  return haloTex;
}

// ---------------------------------------------------------------------------------------------------------------------
// 紙青蛙（a1_c001 摺燈籠摺錯的笑點；G5 開場＋第一幕代理新增，主線授權只新增造型）。
// 正面看的摺紙青蛙：六角身體（淺橙正面朝觀眾）＋頭頂兩片圓眼翻片（墨點眼珠）＋身體兩側摺出的後腿＋底下兩隻小前腳＋一道寬嘴。
// 收摺：後腿、前腳往前摺回身體正面，眼睛翻片往前翻下蓋住臉，整個疊成一片扁紙包；攤開時依序打開（先後腿、再前腳、最後眼睛立起）。
// 單位同其他造型（折折身高＝1），腳底在 y＝0；全寬約 0.9、高約 0.52。
// ---------------------------------------------------------------------------------------------------------------------
export class FrogForm implements FormObject {
  readonly group = new Group();
  private flaps: { g: Group; axis: Vector3; folded: number; rest: number; win: [number, number] }[] = [];
  private eyesUp: Group[] = [];
  constructor(ctx: PartCtx, inkMat: Material) {
    const F: string = ZZ_COLORS.front, B: string = ZZ_COLORS.back, t = PAPER_T;
    const root = new Group();
    this.group.add(root);
    // 身體：正面淺橙（逆時針＝法線朝 +z）
    const body = [v3(-0.27, 0.05, 0), v3(0.27, 0.05, 0), v3(0.25, 0.27, 0), v3(0.12, 0.37, 0), v3(-0.12, 0.37, 0), v3(-0.25, 0.27, 0)];
    root.add(partMesh(new PaperBuilder().slab(body, F, B), ctx));
    // 寬嘴（墨色細彎條，貼在身體正面）
    const mouth: Vector3[] = [];
    const N = 7;
    for (let i = 0; i <= N; i++) { const u = i / N, x = -0.11 + 0.22 * u, y = 0.2 - 0.035 * Math.sin(Math.PI * u); mouth.push(v3(x, y, 0)); }
    for (let i = N; i >= 0; i--) { const u = i / N, x = -0.11 + 0.22 * u, y = 0.2 - 0.035 * Math.sin(Math.PI * u) - 0.016 * Math.sin(Math.PI * u) - 0.004; mouth.push(v3(x, y, 0)); }
    const mouthB = new PaperBuilder().slab(mouth.reverse(), ZZ_COLORS.ink, ZZ_COLORS.ink, t * 0.4);
    const mouthM = partMesh(mouthB, ctx, { outline: false, mat: inkMat });
    mouthM.position.z = t * 0.75;
    root.add(mouthM);
    // 翻片：pts 是攤開時的座標，a→b 是摺線；folded＝收摺時繞摺線轉的角度（轉到身體正面），rest＝完成形的微角度（立體感）
    const flap = (pts: Vector3[], a: Vector3, b: Vector3, folded: number, rest: number, win: [number, number], z: number, front = F, back = B): Group => {
      const g = new Group();
      g.position.set(a.x, a.y, z);
      g.add(partMesh(new PaperBuilder().slab(pts.map((p) => p.clone().sub(v3(a.x, a.y, 0))), front, back), ctx));
      root.add(g);
      this.flaps.push({ g, axis: b.clone().sub(a).normalize(), folded, rest, win });
      return g;
    };
    // 後腿（左右）：鉸鏈在身體側邊，往前摺回身體正面；完成形略朝觀眾翹起
    const lA = v3(-0.27, 0.05, 0), lB = v3(-0.25, 0.27, 0);
    flap([v3(-0.27, 0.05, 0), v3(-0.25, 0.27, 0), v3(-0.36, 0.2, 0), v3(-0.45, 0.07, 0), v3(-0.4, 0.0, 0), v3(-0.3, 0.0, 0)], lA, lB, Math.PI - 0.06, 0.35, [0, 0.55], 1.5 * t);
    const rA = v3(0.25, 0.27, 0), rB = v3(0.27, 0.05, 0);
    flap([v3(0.27, 0.05, 0), v3(0.3, 0.0, 0), v3(0.4, 0.0, 0), v3(0.45, 0.07, 0), v3(0.36, 0.2, 0), v3(0.25, 0.27, 0)], rA, rB, Math.PI - 0.06, 0.35, [0.05, 0.6], 2.5 * t);
    // 前腳（左右）：鉸鏈在身體底邊，往上摺回正面
    const fl = v3(-0.2, 0.05, 0), fl2 = v3(-0.08, 0.05, 0);
    flap([v3(-0.2, 0.05, 0), v3(-0.08, 0.05, 0), v3(-0.17, -0.0, 0), v3(-0.25, 0.0, 0)].reverse(), fl, fl2, -(Math.PI - 0.06), -0.25, [0.3, 0.8], 3.5 * t);
    const fr = v3(0.08, 0.05, 0), fr2 = v3(0.2, 0.05, 0);
    flap([v3(0.08, 0.05, 0), v3(0.2, 0.05, 0), v3(0.25, 0.0, 0), v3(0.17, 0.0, 0)].reverse(), fr, fr2, -(Math.PI - 0.06), -0.25, [0.32, 0.82], 4.5 * t);
    // 眼睛翻片（左右）：鉸鏈在身體上緣，往前翻下蓋住臉；完成形微微前傾。墨點眼珠＋白色眼白（背面色）
    const eye = (cx: number, z: number, win: [number, number]): void => {
      const hy = 0.335, a = v3(cx - 0.075, hy, 0), b = v3(cx + 0.075, hy, 0);
      const pts: Vector3[] = [];
      for (let i = 0; i <= 8; i++) { const ang = Math.PI * (i / 8); pts.push(v3(cx + 0.075 * Math.cos(ang), hy + 0.145 * Math.sin(ang) * (0.82 + 0.18 * Math.sin(ang)), 0)); }
      // 逆時針（角度 0→π：從右下沿上緣走到左下）；正面＝白色眼白
      const g = flap(pts, b, a, -(Math.PI - 0.08), -0.25, win, 5.5 * t + z, B, F);
      const pupil = new Mesh(discGeometry(0.03, 14), inkMat);
      pupil.position.set(cx - b.x + (cx < 0 ? 0.008 : -0.008), 0.075, t * 0.75);
      g.add(pupil);
      ctx.tris.n += 14;
      this.eyesUp.push(g);
    };
    eye(-0.085, 0, [0.55, 1]);
    eye(0.085, t, [0.6, 1]);
  }
  setOpen(open: number): void {
    for (const f of this.flaps) {
      const k = sub(open, f.win[0], f.win[1]);
      const ang = f.folded * (1 - k) + f.rest * k;
      f.g.quaternion.setFromAxisAngle(f.axis, ang);
    }
  }
}
