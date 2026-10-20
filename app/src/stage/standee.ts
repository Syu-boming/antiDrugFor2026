// 整張圖立牌紙偶（兒童角色的 G4 做法：v04 母版＋姿勢圖）：
// - 每個姿勢一張圖（例如 stand、reach、stepback），以腳底中心對齊；換姿勢用「紙片翻面」（約 0.24 秒，水平壓扁→換圖→展開），
//   不用透明度交叉淡化（v1.2 第 15.4 節）。
// - 原圖已經有白色紙芯邊；程式在後面加 2–4 px 深色卡紙側邊（依外形膨脹）。
// - 呼吸（以腳底為支點的極輕微伸縮）、重心擺動、聆聽時微微傾向說話者；眨眼與嘴型由 FaceRig 換片。
import { CanvasTexture, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshStandardMaterial, PlaneGeometry } from 'three';
import { alphaBBox, alphaMask, bleedEdges, cropPixels, outlineBacking, pixelsToCanvas, type Pixels } from './imageproc';
import { finishTexture } from './paper';
import { FaceRig, shiftFallback, type FaceConfig, type FallbackFace } from './face';
import { backingMaterial } from './rig';

export interface StandeePoseConfig {
  /** 圖像 id（manifest images） */
  image: string;
  /** 腳底中心（像素）；省略時自動找最低 40 px 的不透明範圍中心 */
  feet?: [number, number];
  /** 頭頂 y（像素）；用來讓不同姿勢圖的角色高度一致 */
  headTop?: number;
  /** 退路臉部範圍 key（FALLBACK_FACES） */
  face?: string;
}

export interface StandeeConfig {
  id: string;
  /** 腳底到頭頂的高度（世界單位） */
  height: number;
  poses: Record<string, StandeePoseConfig>;
  defaultPose: string;
  /** 深色卡紙側邊寬度（貼圖像素） */
  edge?: number;
}

interface PoseView { name: string; group: Group; mesh: Mesh; face: FaceRig | null; scale: number; heightUnits: number; head: Group | null }

const PAD = 18;

export class StandeeActor {
  readonly root = new Group();
  /** 翻面、呼吸用的中間層（支點在腳底） */
  readonly body = new Group();
  readonly poses = new Map<string, PoseView>();
  current = '';
  readonly missing: string[] = [];

  constructor(readonly cfg: StandeeConfig, image: (id: string) => CanvasImageSource | undefined, opts: {
    renderOrderBase: number; alphaToCoverage: boolean; faceConfig?: FaceConfig; fallbackFaces: Record<string, FallbackFace>;
    faceImage: (id: string) => CanvasImageSource | undefined;
  }) {
    this.root.name = `standee:${cfg.id}`;
    this.root.add(this.body);
    let refScale = 0;
    for (const [name, pc] of Object.entries(cfg.poses)) {
      const img = image(pc.image);
      if (!img) { this.missing.push(pc.image); continue; }
      const w = (img as HTMLImageElement).naturalWidth ?? (img as HTMLCanvasElement).width;
      const h = (img as HTMLImageElement).naturalHeight ?? (img as HTMLCanvasElement).height;
      const full = cropPixels(img, 0, 0, w, h);
      const bb = alphaBBox(full) ?? [0, 0, w, h];
      const x0 = bb[0] - PAD, y0 = bb[1] - PAD, x1 = bb[2] + PAD, y1 = bb[3] + PAD;
      const px: Pixels = cropPixels(img, x0, y0, x1, y1);
      const mask = alphaMask(px);
      // 腳底中心：最低 40 px 的不透明範圍中心
      let feet = pc.feet;
      if (!feet) {
        let minx = Infinity, maxx = -Infinity;
        for (let y = Math.max(0, bb[3] - 40 - y0); y < bb[3] - y0; y++) {
          for (let x = 0; x < px.width; x++) if (mask[y * px.width + x]) { if (x < minx) minx = x; if (x > maxx) maxx = x; }
        }
        feet = [x0 + (minx + maxx) / 2, bb[3] - 4];
      }
      // 頭頂：頭部所在欄位（高度 12–22% 的不透明欄位加權中心 ±6% 寬）的最高點；舉起的手不算
      let top = pc.headTop ?? bb[1];
      if (pc.headTop === undefined) {
        const H = bb[3] - bb[1];
        const r0 = Math.round(bb[1] + 0.12 * H - y0), r1 = Math.round(bb[1] + 0.22 * H - y0);
        let sw = 0, sx = 0;
        for (let y = r0; y < r1; y++) for (let x = 0; x < px.width; x++) if (mask[y * px.width + x]) { sw++; sx += x; }
        const hx = sw ? sx / sw : px.width / 2;
        const half = Math.round(px.width * 0.06);
        let best = Infinity;
        for (let x = Math.max(0, Math.round(hx - half)); x < Math.min(px.width, Math.round(hx + half)); x++) {
          for (let y = 0; y < px.height; y++) if (mask[y * px.width + x]) { if (y < best) best = y; break; }
        }
        if (best < Infinity) top = best + y0;
      }
      const s = cfg.height / (feet[1] - top);
      if (!refScale) refScale = s;
      bleedEdges(px, 3);
      const edge = cfg.edge ?? 9;
      const back = outlineBacking(mask, px.width, px.height, { core: 0, edge, offset: [3, 4], coreColor: [247, 242, 230], edgeColor: [58, 44, 34] });
      const mk = (p: Pixels): CanvasTexture => { const t = finishTexture(new CanvasTexture(pixelsToCanvas(p))); t.minFilter = LinearMipmapLinearFilter; return t; };
      const map = mk(px), bmap = mk(back);
      const px2local = (x: number, y: number): [number, number] => [(x - feet![0]) * s, (feet![1] - y) * s];
      const [lx0, ly0] = px2local(x0, y1);
      const [lx1, ly1] = px2local(x1, y0);
      const geo = new PlaneGeometry(lx1 - lx0, ly1 - ly0);
      geo.translate((lx0 + lx1) / 2, (ly0 + ly1) / 2, 0);
      const mat = new MeshStandardMaterial({ map, alphaTest: 0.5, side: DoubleSide, roughness: 0.92, metalness: 0, alphaToCoverage: opts.alphaToCoverage });
      const mesh = new Mesh(geo, mat);
      mesh.castShadow = true; mesh.receiveShadow = true;
      mesh.renderOrder = opts.renderOrderBase + 2;
      const bm = new Mesh(geo, backingMaterial(bmap, opts.alphaToCoverage));
      bm.position.z = -0.006;
      bm.castShadow = true; bm.receiveShadow = true;
      bm.renderOrder = opts.renderOrderBase + 1;
      const group = new Group();
      group.add(bm, mesh);
      group.visible = false;
      this.body.add(group);
      // 頭層：face.json 指出這張姿勢圖有拆好的頭＋身體時，身體用 -body 圖、頭另成一層（可微微轉頭、點頭）
      const hl = opts.faceConfig?.headLayer && opts.faceConfig.poseImage === pc.image ? opts.faceConfig.headLayer : undefined;
      const headImg = hl ? image(hl.image) : undefined;
      const bodyImg = hl ? image(`${pc.image}-body`) : undefined;
      let headGroup: Group | null = null;
      let faceParent: Group = group;
      let facePx = px2local;
      if (hl && headImg && bodyImg) {
        // 身體層與整張姿勢圖同座標：換掉主圖貼圖
        const bpx = cropPixels(bodyImg, x0, y0, x1, y1);
        bleedEdges(bpx, 3);
        (mesh.material as MeshStandardMaterial).map = mk(bpx);
        const hw = (headImg as HTMLImageElement).naturalWidth, hh = (headImg as HTMLImageElement).naturalHeight;
        const hpx = cropPixels(headImg, 0, 0, hw, hh);
        bleedEdges(hpx, 3);
        const hmask = alphaMask(hpx);
        const hback = outlineBacking(hmask, hw, hh, { core: 0, edge, offset: [3, 4], coreColor: [247, 242, 230], edgeColor: [58, 44, 34] });
        const [px0, py0] = [hl.offset[0] + hl.pivot[0], hl.offset[1] + hl.pivot[1]];
        const [gx, gy] = px2local(px0, py0);
        headGroup = new Group();
        headGroup.position.set(gx, gy, 0.003);
        const toHead = (x: number, y: number): [number, number] => { const [lx, ly] = px2local(x + hl.offset[0], y + hl.offset[1]); return [lx - gx, ly - gy]; };
        const [hx0, hy0] = toHead(0, hh), [hx1, hy1] = toHead(hw, 0);
        const hgeo = new PlaneGeometry(hx1 - hx0, hy1 - hy0);
        hgeo.translate((hx0 + hx1) / 2, (hy0 + hy1) / 2, 0);
        const hmesh = new Mesh(hgeo, new MeshStandardMaterial({ map: mk(hpx), alphaTest: 0.5, side: DoubleSide, roughness: 0.92, metalness: 0, alphaToCoverage: opts.alphaToCoverage }));
        hmesh.castShadow = true; hmesh.receiveShadow = true;
        hmesh.renderOrder = opts.renderOrderBase + 2.5;
        const hb = new Mesh(hgeo, backingMaterial(mk(hback), opts.alphaToCoverage));
        hb.position.z = -0.0095;
        hb.renderOrder = opts.renderOrderBase + 1;
        headGroup.add(hb, hmesh);
        group.add(headGroup);
        faceParent = headGroup;
        facePx = toHead;
      }
      const fbKey = pc.face ?? `${cfg.id}:${name}`;
      const fb0 = opts.fallbackFaces[fbKey];
      const fb = fb0 ? shiftFallback(fb0, [bb[0], bb[1]]) : undefined;
      const face = (opts.faceConfig || fb)
        ? new FaceRig(cfg.id, faceParent, facePx, s, { config: opts.faceConfig, fallback: headGroup ? undefined : fb, baseImage: img, baseId: headGroup ? hl!.image : pc.image, source: { image: opts.faceImage }, renderOrder: opts.renderOrderBase + 3, zBase: 0.004, pose: name })
        : null;
      this.poses.set(name, { name, group, mesh, face, scale: s, heightUnits: cfg.height, head: headGroup });
    }
    this.setPose(cfg.defaultPose in cfg.poses ? cfg.defaultPose : [...this.poses.keys()][0] ?? '');
  }

  get ready(): boolean { return this.poses.size > 0; }

  setPose(name: string): void {
    if (!this.poses.has(name)) name = this.poses.has(this.cfg.defaultPose) ? this.cfg.defaultPose : [...this.poses.keys()][0];
    if (name === this.current) return;
    this.current = name;
    this.poses.forEach((p, k) => { p.group.visible = k === name; });
  }

  get face(): FaceRig | null { return this.poses.get(this.current)?.face ?? null; }
  /** 目前姿勢的頭層（沒有拆頭的姿勢回傳 null） */
  get head(): Group | null { return this.poses.get(this.current)?.head ?? null; }

  forEachMesh(fn: (m: Mesh) => void): void { this.poses.forEach((p) => p.group.traverse((o) => { if ((o as Mesh).isMesh) fn(o as Mesh); })); }
}
