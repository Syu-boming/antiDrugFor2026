// three.js 舞台管理：渲染器（WebGLRenderer）、相機、燈光、景、布幕、紙偶與特效，
// 以及 GPU 中斷（webglcontextlost／restored）、預先編譯（compileAsync）與畫質等級 A／B。
// 景與演員在 cue 檔載入後才建立（setScene）：
// - 景（G5）：每個 cue 的景＝時間軸的 set（cue.set ＞ 檔案層級 set），景名查 src/sets/registry.ts（找不到再找 layout.json、最後用佔位景）。
//   換景時先釋放舊景（幾何、材質、貼圖），再建新景；換景發生在畫面全暗的時候（時間軸的 enterFade／引擎的漸暗預捲），dimmer 蓋住台口內。
// - 演員（G5）：全劇所有段落名冊的聯集一次建好（演員池），每個 cue 只顯示它所屬段落名冊上的角色（位置、站位、層序依段落）；
//   程式角色（例如折折）不經過 PuppetDirector，舞台每格直接呼叫它的 apply。
import {
  CanvasTexture, Color, DirectionalLight, DoubleSide, Group, HemisphereLight, Mesh, MeshBasicMaterial, NoToneMapping, PCFShadowMap,
  PerspectiveCamera, PlaneGeometry, Scene, SRGBColorSpace, Vector3, WebGLRenderer, type Material, type MeshStandardMaterial,
  type Object3D, type Texture,
} from 'three';
import { Curtain } from './curtain';
import { applyPopup, type PopPiece } from './workshop';
import { ANCHOR_CAMERA, CAMERA_PRESETS, LAYER, STAGE_OPENING, type CameraPreset } from './layers';
import { MIN_STRING_PX, PuppetDirector, type LipsyncData, type Performer } from './perform';
import { buildCastPool, castKey, retargetOrder, type AnyPerformer, type CastEntry, type ProgramPerformer } from './cast';
import { configureStringTextures } from './strings';
import { setTextureDensity, makeCanvas } from './paper';
import { desatUniform, enableDesat, FollowSpot } from './fx';
import type { AnchorName } from './rig';
import { setAt, type WorldState, type CameraResolver } from '../engine/world';
import type { CueTimeline } from '../cues/timeline';
import type { CharacterRoster, CueFile } from '../types/cue';
import type { AssetStore } from '../data/assets';
import { rosterFor } from '../cues/show';
import { buildProscenium, buildSet, setCameras } from '../sets/registry';
import type { BuiltSet, SetContext, SetLight } from '../sets/types';
import { lerp } from '../util/math';

export type Quality = 'A' | 'B';

export interface StageOptions {
  host: HTMLElement;
  quality: Quality;
  /** 擷取模式：保留繪圖緩衝，截圖才會拿到最新一格 */
  capture: boolean;
  lipsync?: (id: string) => LipsyncData | undefined;
}

const BASE = { hemi: 1.35, key: 2.2, fill: 0.5 };
/** 燈光預設（景可以覆寫，見 src/sets/types.ts SetLight） */
const LIGHT_DEFAULT = { key: [-7, 13, 16] as [number, number, number], keyColor: '#ffe9c8', hemiSky: '#fff3dc', hemiGround: '#6b5846' };
/** 換景調暗：貼在相機前面的全畫面深色片（不測深度、最後畫），不透明度＝world.dim；字幕與題卡是 HTML，不受影響 */
const DIMMER = { z: -0.6, order: 10000, color: '#0b0806' };

/** 釋放一個物件樹裡的幾何、材質與貼圖（換景時舊景用） */
function disposeTree(root: Object3D): void {
  const texKeys = ['map', 'emissiveMap', 'alphaMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'bumpMap', 'aoMap', 'lightMap'];
  root.traverse((o) => {
    const m = o as Mesh;
    if (!m.isMesh) return;
    m.geometry?.dispose();
    const mats = Array.isArray(m.material) ? m.material : [m.material];
    for (const mat of mats) {
      if (!mat) continue;
      for (const k of texKeys) { const t = (mat as unknown as Record<string, Texture | null>)[k]; if (t && typeof t.dispose === 'function') t.dispose(); }
      mat.dispose();
    }
  });
}

function contactShadowTexture(): CanvasTexture {
  const [c, g] = makeCanvas(128, 64);
  const grd = g.createRadialGradient(64, 32, 2, 64, 32, 62);
  grd.addColorStop(0, 'rgba(40,25,15,0.55)');
  grd.addColorStop(0.6, 'rgba(40,25,15,0.22)');
  grd.addColorStop(1, 'rgba(40,25,15,0)');
  g.save(); g.scale(1, 0.5); g.translate(0, 32); g.fillStyle = grd; g.fillRect(0, -32, 128, 128); g.restore();
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

export class Stage {
  renderer!: WebGLRenderer;
  readonly scene = new Scene();
  /** 長焦透視相機：垂直視角約 20° */
  readonly camera = new PerspectiveCamera(20, 16 / 9, 0.5, 200);
  readonly curtain: Curtain;
  /** 目前段落在台上的紙偶（角色 id → 紙偶；PuppetDirector 只管這些） */
  actors = new Map<string, Performer>();
  /** 目前段落的程式角色（例如折折） */
  programs = new Map<string, ProgramPerformer>();
  readonly director: PuppetDirector;
  private hemi = new HemisphereLight('#fff3dc', '#6b5846', BASE.hemi);
  private key = new DirectionalLight('#ffe9c8', BASE.key);
  private fill = new DirectionalLight('#d6e4ff', BASE.fill);
  readonly spot = new FollowSpot();
  private lip: Mesh;
  private setGroup = new Group();
  private castGroup = new Group();
  private pieces: PopPiece[] = [];
  /** 接觸陰影（演員池鍵 → 陰影） */
  private shadows = new Map<string, Mesh>();
  /** 全劇演員池（castKey(id, rig) → 紙偶）與池內 renderOrder 基準 */
  private pool = new Map<string, AnyPerformer>();
  private poolBase = new Map<string, number>();
  /** 目前在台上的演員池鍵（角色 id → 鍵） */
  private activeKeys = new Map<string, string>();
  private castSync = '';
  private file: CueFile | null = null;
  private assets: AssetStore | null = null;
  private activeSet: { name: string; built: BuiltSet } | null = null;
  private setMarks: Record<string, { x: number; z: number }> | undefined;
  private lightMul = { key: 1, hemi: 1, fill: 1 };
  private dimmer: Mesh;
  private setReports = new Set<string>();
  private castPoolReport: string[] = [];
  /** 景的建立與釋放次數（測試「舊景釋放資源」用） */
  readonly setStats = { built: 0, disposed: 0, buildMs: 0, lastBuildMs: 0 };
  private loseExt: WEBGL_lose_context | null = null;
  private size = { w: 1280, h: 720 };
  setName = '';
  get castReport(): string[] { return [...this.castPoolReport, ...this.setReports]; }
  castTimings: Record<string, number> = {};
  tableEdge: [number, number] | null = null;
  /** 量測用地標（世界座標；只有 workshop_g4 景有） */
  landmarks: Record<string, { x0: number; x1: number; y: number; z: number }> = {};
  contextLost = false;
  onContextLost?: () => void;
  onContextRestored?: () => void;
  quality: Quality;
  compiledMs = 0;
  private anchorCams = new Map<string, Map<string, CameraPreset>>();
  private shadowTex = contactShadowTexture();
  hideActorsForProbe = false;

  constructor(private opts: StageOptions) {
    this.quality = opts.quality;
    setTextureDensity(opts.quality === 'A' ? 220 : 150);
    this.scene.background = new Color('#0b0806');

    // 燈光預設（G4 後凍結）：暖色主光從左上前方打下紙影，冷色補光從右側，半球光當環境
    this.key.position.set(-7, 13, 16);
    this.key.target.position.set(0, 2.5, -2);
    this.key.castShadow = true;
    const sc = this.key.shadow.camera;
    sc.left = -14; sc.right = 14; sc.top = 14; sc.bottom = -3; sc.near = 1; sc.far = 60;
    this.key.shadow.bias = -0.0004;
    this.key.shadow.normalBias = 0.03;
    this.key.shadow.radius = opts.quality === 'A' ? 4 : 2.5;
    this.key.shadow.intensity = 0.45;
    this.fill.position.set(9, 6, 12);
    this.scene.add(this.hemi, this.key, this.key.target, this.fill, this.spot.light, this.spot.target);

    this.scene.add(this.setGroup, this.castGroup);
    const pros = buildProscenium();
    this.lip = pros.lip;
    this.scene.add(pros.group);
    this.curtain = new Curtain({
      width: STAGE_OPENING.width + 0.6, height: STAGE_OPENING.height + 0.4,
      bottom: STAGE_OPENING.centerY - STAGE_OPENING.height / 2 - 0.05, z: LAYER.curtain.z, pleats: 16, color: '#8c4632',
      renderOrder: LAYER.curtain.order,
    });
    this.scene.add(this.curtain.group);
    for (const o of [pros.group, this.curtain.group]) o.traverse((m) => { const mat = (m as Mesh).material as Material | undefined; if (mat) enableDesat(mat); });
    // 換景亮度漸變：相機前面一張全畫面深色片（整個畫面一起漸暗、漸亮）；dim 0 時不畫（畫面與 G4 相同）
    this.dimmer = new Mesh(new PlaneGeometry(4, 4), new MeshBasicMaterial({ color: DIMMER.color, transparent: true, opacity: 0, depthWrite: false, depthTest: false }));
    this.dimmer.position.set(0, 0, DIMMER.z);
    this.dimmer.renderOrder = DIMMER.order;
    this.dimmer.visible = false;
    this.dimmer.frustumCulled = false;
    this.dimmer.name = 'dimmer';
    this.camera.add(this.dimmer);
    this.scene.add(this.camera);
    this.director = new PuppetDirector(this.actors, opts.lipsync);
    this.createRenderer();
  }

  /** 依 cue 檔建立景與演員（載入後呼叫一次）：先建第一個 cue 的景，再建全劇演員池 */
  setScene(file: CueFile, assets: AssetStore | null): void {
    this.disposeActiveSet();
    this.castGroup.clear();
    this.shadows.clear();
    this.anchorCams.clear();
    this.pool.clear();
    this.poolBase.clear();
    this.activeKeys.clear();
    this.castSync = '';
    this.setReports.clear();
    this.file = file;
    this.assets = assets;
    const first = file.cues[0];
    this.ensureSet(first?.set ?? file.set ?? 'workshop');
    // 操偶線紙繩與紙環貼圖（素材優先，缺圖用程式畫的退路）：要在建立紙偶之前設定
    const maxAniso = this.renderer?.capabilities.getMaxAnisotropy?.() ?? 4;
    const st = configureStringTextures(assets?.image('tex-string-rope'), assets?.image('tex-string-ring'), Math.min(8, maxAniso || 4));
    // 演員池：檔案名冊＋各段落名冊的聯集（依第一次出現的順序；單一 cue 檔＝名冊順序，與 G4 相同）
    const entries: CastEntry[] = [];
    const seen = new Set<string>();
    const addRoster = (r: CharacterRoster | undefined): void => {
      for (const [id, entry] of Object.entries(r ?? {})) { const key = castKey(id, entry.rig); if (!seen.has(key)) { seen.add(key); entries.push({ key, id, entry }); } }
    };
    if (file.segments?.length) for (const sg of file.segments) addRoster(sg.characters); else addRoster(file.characters);
    const cast = buildCastPool(entries, assets, { alphaToCoverage: this.quality === 'A', marks: this.setMarks });
    if (st.rope === 'fallback' || st.ring === 'fallback') cast.report.push(`操偶線貼圖：紙繩 ${st.rope === 'image' ? '素材' : '程式退路'}、紙環 ${st.ring === 'image' ? '素材' : '程式退路'}`);
    this.castPoolReport = cast.report;
    this.castTimings = cast.timings;
    this.pool = cast.pool;
    let k = 0;
    for (const e of entries) {
      const a = this.pool.get(e.key);
      if (!a || this.poolBase.has(e.key)) continue;
      this.poolBase.set(e.key, LAYER.actors.order + k * LAYER.actorStride);
      k++;
      a.addTo(this.castGroup);
      a.root.visible = false;
      const sh = new Mesh(new PlaneGeometry(1, 1), new MeshBasicMaterial({ map: this.shadowTex, transparent: true, depthWrite: false, side: DoubleSide }));
      sh.rotation.x = -Math.PI / 2;
      sh.renderOrder = LAYER.backdrop.order + 5;
      sh.visible = false;
      this.castGroup.add(sh);
      this.shadows.set(e.key, sh);
    }
    if (first) this.syncCast(first, first.set ?? file.set ?? 'workshop');
  }

  /** 時間軸重建（例如換壓縮級別）後清掉依 cue 快取的錨點鏡位 */
  resetCaches(): void { this.anchorCams.clear(); }

  /** 場景裡還掛著的景（換景後應該一直是 1：舊景已釋放） */
  get liveSetGroups(): number { return this.setGroup.children.length; }

  private setContext(): SetContext {
    const assets = this.assets;
    return {
      name: '', alphaToCoverage: this.quality === 'A', quality: this.quality,
      image: (id) => assets?.image(id), json: <T>(id: string) => assets?.getJson<T>(id),
    };
  }

  /** 換景：同名不動；不同就釋放舊景、建新景（舞台全暗時呼叫，避免看到換景） */
  private ensureSet(name: string): void {
    if (this.activeSet?.name === name) return;
    this.disposeActiveSet();
    const t0 = performance.now();
    const { built, report } = buildSet(name, { ...this.setContext(), name });
    this.setGroup.add(built.group);
    if (built.materials) built.materials.forEach(enableDesat);
    else built.group.traverse((m) => { const mat = (m as Mesh).material as Material | Material[] | undefined; if (mat) (Array.isArray(mat) ? mat : [mat]).forEach(enableDesat); });
    this.pieces = built.pieces ?? [];
    this.tableEdge = built.tableEdge ?? null;
    this.landmarks = built.landmarks ?? {};
    this.setMarks = built.marks;
    this.applySetLight(built.light);
    this.activeSet = { name, built };
    this.setName = name;
    for (const r of report) this.setReports.add(r);
    this.setStats.built++;
    this.setStats.lastBuildMs = performance.now() - t0;
    this.setStats.buildMs += this.setStats.lastBuildMs;
  }

  private disposeActiveSet(): void {
    const a = this.activeSet;
    if (!a) { this.setGroup.clear(); return; }
    this.setGroup.remove(a.built.group);
    disposeTree(a.built.group);
    try { a.built.dispose?.(); } catch { /* 景自己的釋放失敗不影響演出 */ }
    this.activeSet = null;
    this.pieces = [];
    this.setStats.disposed++;
  }

  private applySetLight(l: SetLight | undefined): void {
    const k = l?.key ?? LIGHT_DEFAULT.key;
    this.key.position.set(k[0], k[1], k[2]);
    this.key.color.set(l?.keyColor ?? LIGHT_DEFAULT.keyColor);
    this.hemi.color.set(l?.hemiSky ?? LIGHT_DEFAULT.hemiSky);
    this.hemi.groundColor.set(l?.hemiGround ?? LIGHT_DEFAULT.hemiGround);
    this.lightMul = { key: l?.keyIntensity ?? 1, hemi: l?.hemiIntensity ?? 1, fill: l?.fillIntensity ?? 1 };
  }

  /**
   * 換段落（或換景）時：段落名冊上的角色上台（位置＝名冊 x、z ＞ 景的站位 marks ＞ 0；層序依段落名冊順序），其他角色下台。
   * 單一 cue 檔（G4、demo）只同步一次。
   */
  private syncCast(cue: { segment?: string } & Parameters<typeof rosterFor>[1], setName: string): void {
    const key = `${cue.segment ?? ''}|${setName}`;
    if (key === this.castSync || !this.file) return;
    this.castSync = key;
    const roster = rosterFor(this.file, cue);
    const actors = new Map<string, Performer>();
    const programs = new Map<string, ProgramPerformer>();
    this.activeKeys.clear();
    let j = 0;
    for (const [id, entry] of Object.entries(roster)) {
      const pk = castKey(id, entry.rig);
      const p = this.pool.get(pk);
      if (!p) continue;
      const mark = this.setMarks?.[id];
      p.place.x = entry.x ?? mark?.x ?? 0;
      p.place.z = entry.z ?? mark?.z ?? 0;
      p.place.facing = (entry.facing ?? 1) as 1 | -1;
      retargetOrder(p, this.poolBase.get(pk) ?? LAYER.actors.order, LAYER.actors.order + j * LAYER.actorStride);
      j++;
      this.activeKeys.set(id, pk);
      if (p.kind === 'program') programs.set(id, p); else actors.set(id, p);
    }
    // 下台：池裡其他紙偶與它們的線、陰影都藏起來
    this.pool.forEach((p, pk) => {
      if ([...this.activeKeys.values()].includes(pk)) return;
      p.root.visible = false;
      if (p.kind === 'rig') p.strings.forEach((s) => s.hide());
      const sh = this.shadows.get(pk);
      if (sh) sh.visible = false;
    });
    const same = actors.size === this.actors.size && [...actors].every(([id, a]) => this.actors.get(id) === a);
    this.actors = actors;
    this.programs = programs;
    if (!same) this.director.setActors(this.actors);
  }

  private createRenderer(): void {
    const r = new WebGLRenderer({
      antialias: this.quality === 'A', powerPreference: 'high-performance',
      preserveDrawingBuffer: this.opts.capture, alpha: false, stencil: false,
    });
    r.outputColorSpace = SRGBColorSpace;
    r.toneMapping = NoToneMapping;
    r.shadowMap.enabled = true;
    r.shadowMap.type = PCFShadowMap;
    this.key.shadow.mapSize.set(this.quality === 'A' ? 2048 : 1024, this.quality === 'A' ? 2048 : 1024);
    const canvas = r.domElement;
    canvas.id = 'stage-canvas';
    canvas.addEventListener('webglcontextlost', this.handleLost, false);
    canvas.addEventListener('webglcontextrestored', this.handleRestored, false);
    this.opts.host.prepend(canvas);
    this.renderer = r;
    this.loseExt = r.getContext().getExtension('WEBGL_lose_context');
    this.contextLost = false;
    this.resize(this.size.w, this.size.h);
  }

  private handleLost = (e: Event): void => {
    e.preventDefault(); // 允許之後恢復
    this.contextLost = true;
    this.onContextLost?.();
  };

  private handleRestored = (): void => {
    this.contextLost = false;
    this.onContextRestored?.();
  };

  /** 設定舞台大小（CSS 像素，16:9） */
  resize(w: number, h: number): void {
    this.size = { w: Math.max(16, Math.round(w)), h: Math.max(9, Math.round(h)) };
    const dpr = window.devicePixelRatio || 1;
    this.renderer.setPixelRatio(this.quality === 'A' ? Math.min(dpr, 2) : Math.min(dpr, 1));
    this.renderer.setSize(this.size.w, this.size.h, true);
    this.camera.aspect = 16 / 9;
    this.camera.updateProjectionMatrix();
  }

  /** 錨點鏡位："anchor:<角色>.<錨點>"，以該 cue 開始時（t=0）的姿勢計算，整段固定（純函式） */
  cameraResolver(tl: CueTimeline): CameraResolver {
    return (name, params) => {
      // 景的鏡位（layout.json 的 cameras 或程式景的 cameras）
      for (const sn of [tl.set, ...tl.anims.filter((a) => a.name === 'set.swap').map((a) => String(a.params.set))]) {
        const cams = (this.activeSet?.name === sn ? this.activeSet.built.cameras : undefined) ?? setCameras(sn, this.setContext());
        if (cams?.[name]) return cams[name];
      }
      const m = /^anchor:([a-z0-9_]+)\.(wrist|elbow|knee|up)$/i.exec(name);
      if (!m) return null;
      let cams = this.anchorCams.get(tl.cue.id);
      if (!cams) { cams = this.computeAnchorCams(tl); this.anchorCams.set(tl.cue.id, cams); }
      const base = cams.get(`${m[1]}.${m[2]}`);
      if (!base) return CAMERA_PRESETS.medium;
      const dist = Number(params.dist ?? ANCHOR_CAMERA.dist);
      const dy = Number(params.dy ?? ANCHOR_CAMERA.dy);
      const dx = Number(params.dx ?? 0);
      const [x, y, z] = base.target;
      return { pos: [x + dx, y + dy + 0.15, z + dist], target: [x + dx, y + dy, z], fov: Number(params.fov ?? ANCHOR_CAMERA.fov) };
    };
  }

  private computeAnchorCams(tl: CueTimeline): Map<string, CameraPreset> {
    const out = new Map<string, CameraPreset>();
    this.syncCast(tl.cue, this.activeSet?.name ?? tl.set);
    this.director.reset();
    this.director.apply(tl, 0, '__anchor_probe__');
    const v = new Vector3();
    this.actors.forEach((a, id) => {
      if (a.kind !== 'rig') return;
      for (const n of ['wrist', 'elbow', 'knee'] as AnchorName[]) {
        const p = a.rig.anchorWorld(n, v);
        if (p) out.set(`${id}.${n}`, { pos: [p.x, p.y, p.z + 10], target: [p.x, p.y, p.z], fov: 20 });
      }
      // 沿線往上：順著膝前線往上到頭頂上方（y≈3.4），畫面上緣之外看得到線繼續往上、沒有操控者
      const s = a.strings.get('knee') ?? a.strings.get('wrist');
      if (s?.last.visible) {
        const b = s.last.bottom, tp = s.last.top;
        const y = 3.4;
        const u = (y - b.y) / Math.max(1e-3, tp.y - b.y);
        const x = lerp(b.x, tp.x, u);
        out.set(`${id}.up`, { pos: [x, y, b.z + 10], target: [x, y, b.z], fov: 20 });
      }
    });
    this.director.reset();
    return out;
  }

  /**
   * 把舞台層狀態與紙偶表演套到場景上。
   * @param opts.keepSet 預熱用：不換景（只擺紙偶），避免開演前把每個景都建一次
   */
  apply(world: WorldState, tl: CueTimeline, t: number, playKey: string, opts: { keepSet?: boolean } = {}): void {
    if (!opts.keepSet) this.ensureSet(setAt(tl, t));
    this.syncCast(tl.cue, this.activeSet?.name ?? tl.set);
    this.curtain.setOpen(world.curtain);
    applyPopup(this.pieces, world.set);
    const dim = Math.min(1, Math.max(0, world.dim ?? 0));
    this.dimmer.visible = dim > 0.001;
    (this.dimmer.material as MeshBasicMaterial).opacity = dim;
    const c = world.camera;
    this.camera.position.set(...c.pos);
    this.camera.fov = c.fov;
    this.camera.lookAt(...c.target);
    this.camera.updateProjectionMatrix();
    const L = world.light;
    this.hemi.intensity = BASE.hemi * lerp(0.45, 1, L) * this.lightMul.hemi;
    this.key.intensity = BASE.key * L * this.lightMul.key;
    this.fill.intensity = BASE.fill * lerp(0.6, 1, L) * this.lightMul.fill;
    (this.lip.material as MeshStandardMaterial).emissiveIntensity = Math.max(0, (1 - L) * 2.2);
    desatUniform.value = world.desat;
    this.director.light = lerp(0.55, 1, L) + world.spot * 0.08;
    // 線寬下限：相機到注視點的距離 → 1080p 每世界單位幾 px（純函式，重播一致）
    const camDist = Math.hypot(c.pos[0] - c.target[0], c.pos[1] - c.target[1], c.pos[2] - c.target[2]);
    this.director.minStringWidth = MIN_STRING_PX * (2 * camDist * Math.tan((c.fov * Math.PI) / 360)) / 1080;
    this.director.apply(tl, t, playKey);
    // 程式角色（折折等）：不經過 PuppetDirector
    const chars = tl.cue.initialState.characters ?? {};
    this.programs.forEach((p, id) => p.apply(tl, t, chars[id], { light: this.director.light, playKey: `${tl.cue.id}#${playKey}`, lipsync: this.opts.lipsync ?? (() => undefined) }));
    // 景自己的每格更新（視差、程式景片）
    this.activeSet?.built.update?.({ world, tl, t, camera: this.camera });
    // 追光跟著角色（胸口高度）
    const target = world.spotTarget ? (this.actors.get(world.spotTarget) ?? this.programs.get(world.spotTarget)) : undefined;
    if (target && world.spot > 0.001) {
      const r = target.root;
      this.spot.set(world.spot, [r.position.x, r.position.y + 1.9, r.position.z], 1.1);
    } else if (world.spotAt && world.spot > 0.001) this.spot.set(world.spot, world.spotAt, 1.1);
    else this.spot.set(0, null);
    // 接觸陰影
    const onStage: [string, AnyPerformer][] = [...this.actors, ...this.programs];
    onStage.forEach(([id, a]) => {
      const sh = this.shadows.get(this.activeKeys.get(id) ?? '');
      if (!sh) return;
      const r = a.root;
      sh.visible = r.visible;
      if (!sh.visible) return;
      const wide = a.kind === 'rig' ? 1.35 : a.kind === 'program' ? 0.6 : 1.0;
      const up = Math.max(0, Math.cos(r.rotation.x));
      sh.position.set(r.position.x, 0.012, r.position.z + 0.05);
      sh.scale.set(wide * up + 0.001, 0.5 * up + 0.001, 1);
      (sh.material as MeshBasicMaterial).opacity = 0.75 * up * lerp(0.6, 1, L);
    });
    // 擷取量測用：隱藏所有角色，量背景亮度
    if (this.hideActorsForProbe) {
      onStage.forEach(([id, a]) => {
        a.root.visible = false;
        const sh = this.shadows.get(this.activeKeys.get(id) ?? '');
        if (sh) sh.visible = false;
        if (a.kind === 'rig') a.strings.forEach((st) => st.hide());
      });
    }
  }

  render(): void {
    if (this.contextLost) return;
    this.renderer.render(this.scene, this.camera);
  }

  /** 開演前預先編譯所有材質與著色器、預先上傳貼圖（Edge kiosk 每次啟動都要重做） */
  async precompile(): Promise<number> {
    if (this.contextLost) return 0;
    const t0 = performance.now();
    const hidden: Object3D[] = [];
    this.scene.traverse((o) => { if (!o.visible) { hidden.push(o); o.visible = true; } });
    try {
      await this.renderer.compileAsync(this.scene, this.camera);
    } catch (err) {
      console.warn('[stage] compileAsync 失敗，改用同步編譯', err);
      try { this.renderer.compile(this.scene, this.camera); } catch { /* 交給第一次渲染 */ }
    }
    const textures = new Set<Texture>();
    this.scene.traverse((o) => {
      const mats = (o as Mesh).material as Material | Material[] | undefined;
      if (!mats) return;
      for (const m of Array.isArray(mats) ? mats : [mats]) {
        const map = (m as MeshStandardMaterial).map;
        if (map) textures.add(map);
      }
    });
    textures.forEach((tex) => this.renderer.initTexture(tex));
    hidden.forEach((o) => { o.visible = false; });
    this.render();
    this.compiledMs = performance.now() - t0;
    return this.compiledMs;
  }

  /** GPU 中斷後重建：還沒恢復就換一個新的渲染器（新 canvas），再重新預編譯 */
  async rebuild(): Promise<void> {
    if (this.contextLost) this.recreateRenderer();
    await this.precompile();
  }

  recreateRenderer(): void {
    const old = this.renderer;
    old.domElement.removeEventListener('webglcontextlost', this.handleLost);
    old.domElement.removeEventListener('webglcontextrestored', this.handleRestored);
    try { old.dispose(); } catch { /* 已失效 */ }
    old.domElement.remove();
    // 陰影貼圖屬於舊的 GL context，丟掉讓新渲染器重建
    this.key.shadow.map?.dispose();
    (this.key.shadow as unknown as { map: unknown }).map = null;
    this.createRenderer();
  }

  setQuality(q: Quality): void {
    if (q === this.quality) return;
    this.quality = q;
    this.key.shadow.radius = q === 'A' ? 4 : 2.5;
    this.recreateRenderer();
    void this.precompile();
  }

  /** 測試用：模擬 GPU 中斷與恢復 */
  loseContextForTest(): boolean { if (!this.loseExt) return false; this.loseExt.loseContext(); return true; }
  restoreContextForTest(): boolean { if (!this.loseExt) return false; try { this.loseExt.restoreContext(); return true; } catch { return false; } }

  get gpuInfo(): string {
    try {
      const gl = this.renderer.getContext();
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      return String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    } catch { return 'unknown'; }
  }

  /** 世界座標 → 舞台畫面像素（以目前的渲染尺寸） */
  project(p: Vector3): [number, number] {
    const v = p.clone().project(this.camera);
    const W = this.renderer.domElement.width, H = this.renderer.domElement.height;
    return [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H];
  }

  private alphaBounds = new WeakMap<object, [number, number, number, number] | null>();

  /** 部件貼圖不透明範圍（alpha ≥ 128）投影到螢幕的外框；量測用，結果依貼圖快取 */
  private opaqueBox(m: Mesh): [number, number, number, number] | null {
    const map = (m.material as MeshStandardMaterial).map;
    const img = map?.image as HTMLCanvasElement | undefined;
    if (!img || typeof img.getContext !== 'function') return null;
    let ab = this.alphaBounds.get(img);
    if (ab === undefined) {
      ab = null;
      try {
        const g = img.getContext('2d');
        if (g) {
          const { width: W, height: H } = img;
          const d = g.getImageData(0, 0, W, H).data;
          let x0 = W, y0 = H, x1 = -1, y1 = -1;
          for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (d[(y * W + x) * 4 + 3] >= 128) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
          if (x1 >= 0) ab = [x0 / W, y0 / H, (x1 + 1) / W, (y1 + 1) / H];
        }
      } catch { ab = null; }
      this.alphaBounds.set(img, ab);
    }
    if (!ab) return null;
    m.geometry.computeBoundingBox();
    const bb = m.geometry.boundingBox!;
    const gx = (u: number): number => bb.min.x + (bb.max.x - bb.min.x) * u;
    const gy = (v: number): number => bb.max.y - (bb.max.y - bb.min.y) * v; // 圖像 y 向下
    const box: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
    for (const [u, v] of [[ab[0], ab[1]], [ab[2], ab[1]], [ab[0], ab[3]], [ab[2], ab[3]]]) {
      const [px, py] = this.project(new Vector3(gx(u), gy(v), 0).applyMatrix4(m.matrixWorld));
      box[0] = Math.min(box[0], px); box[1] = Math.min(box[1], py); box[2] = Math.max(box[2], px); box[3] = Math.max(box[3], py);
    }
    return box.map((v) => Math.round(v * 10) / 10) as [number, number, number, number];
  }

  /** 擷取量測：操偶線（錨點、螢幕線寬）與角色外框（像素，繪圖緩衝座標） */
  probe(): { curtain: number; strings: { actor: string; anchor: string; anchorPx: [number, number]; widthPx: number; visible: boolean; dir: [number, number]; path?: [number, number][]; ringPx?: [number, number]; ringRadiusPx?: number }[]; actors: { id: string; box: [number, number, number, number]; visible: boolean; headBox?: [number, number, number, number]; parts?: Record<string, [number, number, number, number]>; opaque?: Record<string, [number, number, number, number]>; joints?: Record<string, [number, number]>; eyesBox?: [number, number, number, number] }[]; landmarks: Record<string, [[number, number], [number, number]]> } {
    const strings: { actor: string; anchor: string; anchorPx: [number, number]; widthPx: number; visible: boolean; dir: [number, number]; path?: [number, number][]; ringPx?: [number, number]; ringRadiusPx?: number }[] = [];
    const actors: { id: string; box: [number, number, number, number]; visible: boolean; headBox?: [number, number, number, number]; parts?: Record<string, [number, number, number, number]>; opaque?: Record<string, [number, number, number, number]>; joints?: Record<string, [number, number]>; eyesBox?: [number, number, number, number] }[] = [];
    // 驗收量測用：物件與所有上層都可見才算顯示中
    const shown = (o: Object3D | null): boolean => { for (let q = o; q; q = q.parent) if (!q.visible) return false; return true; };
    const meshBox = (m: Mesh, box: [number, number, number, number]): void => {
      m.geometry.computeBoundingBox();
      const bb = m.geometry.boundingBox!;
      for (const [x, y] of [[bb.min.x, bb.min.y], [bb.max.x, bb.min.y], [bb.min.x, bb.max.y], [bb.max.x, bb.max.y]]) {
        const [px, py] = this.project(new Vector3(x, y, 0).applyMatrix4(m.matrixWorld));
        box[0] = Math.min(box[0], px); box[1] = Math.min(box[1], py); box[2] = Math.max(box[2], px); box[3] = Math.max(box[3], py);
      }
    };
    this.actors.forEach((a, id) => {
      const box: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
      a.root.updateMatrixWorld(true);
      a.root.traverse((o) => {
        const m = o as Mesh;
        if (!m.isMesh || !m.visible || !m.geometry) return;
        m.geometry.computeBoundingBox();
        const bb = m.geometry.boundingBox!;
        for (const [x, y] of [[bb.min.x, bb.min.y], [bb.max.x, bb.min.y], [bb.min.x, bb.max.y], [bb.max.x, bb.max.y]]) {
          const [px, py] = this.project(new Vector3(x, y, 0).applyMatrix4(m.matrixWorld));
          box[0] = Math.min(box[0], px); box[1] = Math.min(box[1], py); box[2] = Math.max(box[2], px); box[3] = Math.max(box[3], py);
        }
      });
      let headBox: [number, number, number, number] | undefined;
      let parts: Record<string, [number, number, number, number]> | undefined;
      let joints: Record<string, [number, number]> | undefined;
      let opaque: Record<string, [number, number, number, number]> | undefined;
      if (a.kind === 'rig') {
        // 關節（螢幕像素）：hip＝骨盆樞紐（臀部離凳的量測點）
        const pel = a.rig.role('pelvis');
        if (pel && a.rig.has(pel)) {
          const hp = a.rig.part(pel).pivot.getWorldPosition(new Vector3());
          joints = { hip: this.project(hp).map((v) => Math.round(v * 10) / 10) as [number, number] };
        }
        const hb: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
        a.rig.parts.forEach((p, name) => { if (name.startsWith('head') && p.mesh && shown(p.mesh)) meshBox(p.mesh, hb); });
        if (Number.isFinite(hb[0])) headBox = hb;
        // 各部件外框（含透明邊；驗收包量腳、膝與字幕底板是否重疊用）
        parts = {};
        a.rig.parts.forEach((p, name) => {
          if (!p.mesh || !shown(p.mesh)) return;
          const b: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
          meshBox(p.mesh, b);
          if (Number.isFinite(b[0])) parts![name] = b.map((v) => Math.round(v * 10) / 10) as [number, number, number, number];
          // 不透明範圍（貼圖 alpha ≥ 128 的外框；不含透明邊與白色紙芯描邊）
          const ob = this.opaqueBox(p.mesh);
          if (ob) { opaque ??= {}; opaque[name] = ob; }
        });
      }
      // 眼睛換片在畫面上的範圍（驗收包放大眨眼格用）
      let eyesBox: [number, number, number, number] | undefined;
      const fr = a.kind === 'rig' ? (a.activeFace ?? a.face) : a.face;
      const em = fr?.eyesMesh();
      if (em && shown(fr!.group)) {
        const eb: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
        meshBox(em, eb);
        if (Number.isFinite(eb[0])) eyesBox = eb.map((v) => Math.round(v * 10) / 10) as [number, number, number, number];
      }
      actors.push({ id, box, visible: a.root.visible, headBox, parts, opaque, joints, eyesBox });
      if (a.kind !== 'rig') return;
      a.strings.forEach((s, n) => {
        const L = s.last;
        if (!L.visible) { strings.push({ actor: id, anchor: n, anchorPx: [0, 0], widthPx: 0, visible: false, dir: [0, 0] }); return; }
        const b = this.project(L.bottom);
        // 整條線的螢幕路徑：strings.ts 實際畫的中心線（37 點，上端 → 線的下端；下段細分，看得到的彎曲都在裡面）
        const path: [number, number][] = [];
        for (let i = 0; i + 2 < L.path.length; i += 3) path.push(this.project(new Vector3(L.path[i], L.path[i + 1], L.path[i + 2])));
        // 線在下端的方向（往上）：沿路徑往上第一個離下端 ≥ 10 px 的點
        let u = path.length > 1 ? path[path.length - 2] : this.project(L.bottom.clone().lerp(L.top, 0.02));
        for (let i = path.length - 2; i >= 0; i--) { u = path[i]; if (Math.hypot(u[0] - b[0], u[1] - b[1]) >= 10) break; }
        const side = L.bottom.clone().add(new Vector3(L.width, 0, 0));
        const sp = this.project(side);
        const dx = u[0] - b[0], dy = u[1] - b[1], dl = Math.hypot(dx, dy) || 1;
        // 線寬（垂直於線的方向）＝水平投影寬度 × |cos|
        const widthPx = Math.abs(sp[0] - b[0]) * Math.abs(dy / dl);
        // 紙環中心與半徑（螢幕像素）：驗收包檢查扣點是否落在肢體剪影內
        let ringPx: [number, number] | undefined, ringRadiusPx: number | undefined;
        if (L.ring) {
          ringPx = this.project(L.ring);
          const e = this.project(L.ring.clone().add(new Vector3(L.ringD / 2, 0, 0)));
          ringRadiusPx = Math.abs(e[0] - ringPx[0]);
        }
        strings.push({ actor: id, anchor: n, anchorPx: b, widthPx, visible: true, dir: [dx / dl, dy / dl], path, ringPx, ringRadiusPx });
      });
    });
    // 程式角色（折折等）：只量外框
    this.programs.forEach((a, id) => {
      const box: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
      a.root.updateMatrixWorld(true);
      a.root.traverse((o) => { const m = o as Mesh; if (m.isMesh && m.visible && m.geometry) meshBox(m, box); });
      actors.push({ id, box, visible: a.root.visible });
    });
    // 地標（桌面上緣、凳面上緣）：左右兩端投影到螢幕
    const landmarks: Record<string, [[number, number], [number, number]]> = {};
    for (const [k, v] of Object.entries(this.landmarks)) {
      const r = (q: [number, number]): [number, number] => q.map((x) => Math.round(x * 10) / 10) as [number, number];
      landmarks[k] = [r(this.project(new Vector3(v.x0, v.y, v.z))), r(this.project(new Vector3(v.x1, v.y, v.z)))];
    }
    return { curtain: this.curtain.openAmount, strings, actors, landmarks };
  }
}
