// three.js 舞台管理：渲染器（WebGLRenderer）、相機、燈光、層次、布幕、紙偶，
// 以及 GPU 中斷（webglcontextlost／restored）、預先編譯（compileAsync）與畫質等級 A／B。
import {
  Color, DirectionalLight, HemisphereLight, Mesh, NoToneMapping, PCFShadowMap, PerspectiveCamera, Scene, SRGBColorSpace,
  WebGLRenderer, type Material, type MeshStandardMaterial, type Object3D, type Texture,
} from 'three';
import { Curtain } from './curtain';
import { buildProscenium, buildWorkshop } from './sets';
import { LAYER, STAGE_OPENING } from './layers';
import { PuppetActor, PuppetDirector, type ActorConfig, type LipsyncData } from './perform';
import { RIG_ALE, RIG_XIAOQING } from './rigspecs';
import { ringMaterial, ropeMaterial } from './strings';
import { setTextureDensity } from './paper';
import type { WorldState } from '../engine/world';
import type { CueTimeline } from '../cues/timeline';
import { lerp } from '../util/math';

export type Quality = 'A' | 'B';

export interface StageOptions {
  host: HTMLElement;
  quality: Quality;
  /** 擷取模式：保留繪圖緩衝，截圖才會拿到最新一格 */
  capture: boolean;
  lipsync?: (id: string) => LipsyncData | undefined;
}

const BASE = { hemi: 1.25, key: 2.4, fill: 0.45 };

export class Stage {
  renderer!: WebGLRenderer;
  readonly scene = new Scene();
  /** 長焦透視相機：垂直視角約 20° */
  readonly camera = new PerspectiveCamera(20, 16 / 9, 0.5, 200);
  readonly curtain: Curtain;
  readonly actors = new Map<string, PuppetActor>();
  readonly director: PuppetDirector;
  private hemi = new HemisphereLight('#fff3dc', '#5b4a3c', BASE.hemi);
  private key = new DirectionalLight('#ffe7c4', BASE.key);
  private fill = new DirectionalLight('#cfe0ff', BASE.fill);
  private lip: Mesh;
  private loseExt: WEBGL_lose_context | null = null;
  private size = { w: 1280, h: 720 };
  contextLost = false;
  onContextLost?: () => void;
  onContextRestored?: () => void;
  quality: Quality;
  compiledMs = 0;

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
    this.fill.position.set(9, 6, 12);
    this.scene.add(this.hemi, this.key, this.key.target, this.fill);

    const workshop = buildWorkshop();
    this.scene.add(workshop.group);
    const pros = buildProscenium();
    this.lip = pros.lip;
    this.scene.add(pros.group);
    this.curtain = new Curtain({
      width: STAGE_OPENING.width + 0.6, height: STAGE_OPENING.height + 0.4,
      bottom: STAGE_OPENING.centerY - STAGE_OPENING.height / 2 - 0.05, z: LAYER.curtain.z, pleats: 13, color: '#7c2a2a',
      renderOrder: LAYER.curtain.order,
    });
    this.scene.add(this.curtain.group);

    // 佔位紙偶：阿樂叔叔（左，操偶線那一側）與小晴（右，安全的一側）
    const rope = ropeMaterial(), ring = ringMaterial();
    const cast: ActorConfig[] = [
      { id: 'ale', spec: RIG_ALE, x: -2.2, z: 0, facing: 1 },
      { id: 'xiaoqing', spec: RIG_XIAOQING, x: 3.1, z: 0.3, facing: -1 },
    ];
    cast.forEach((cfg, i) => {
      const actor = new PuppetActor(cfg, LAYER.actors.order + i * LAYER.actorStride, rope, ring);
      actor.addTo(this.scene);
      this.actors.set(cfg.id, actor);
    });
    this.director = new PuppetDirector(this.actors, opts.lipsync);
    this.createRenderer();
  }

  private createRenderer(): void {
    const r = new WebGLRenderer({
      antialias: this.quality === 'A', powerPreference: 'high-performance',
      preserveDrawingBuffer: this.opts.capture, alpha: false, stencil: false,
    });
    r.outputColorSpace = SRGBColorSpace;
    r.toneMapping = NoToneMapping;
    r.shadowMap.enabled = true;
    r.shadowMap.type = PCFShadowMap; // r186 已移除 PCFSoftShadowMap
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

  /** 把舞台層狀態與紙偶表演套到場景上 */
  apply(world: WorldState, tl: CueTimeline, t: number, playKey: string): void {
    this.curtain.setOpen(world.curtain);
    const c = world.camera;
    this.camera.position.set(...c.pos);
    this.camera.fov = c.fov;
    this.camera.lookAt(...c.target);
    this.camera.updateProjectionMatrix();
    const L = world.light;
    this.hemi.intensity = BASE.hemi * lerp(0.45, 1, L);
    this.key.intensity = BASE.key * L;
    this.fill.intensity = BASE.fill * lerp(0.6, 1, L);
    (this.lip.material as MeshStandardMaterial).emissiveIntensity = Math.max(0, (1 - L) * 2.2);
    this.director.apply(tl, t, playKey);
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
}
