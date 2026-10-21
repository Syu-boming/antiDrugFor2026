// 操偶線（v1.2 第 15.2 節；G4 修正第 1 輪第 22、23、34 項）：
// - 紙繩：素材貼圖 tex-string-rope（64×256；v02 起為平面紙繩：淡灰繩身 sRGB≈184＋不規則短纖維點紋（無扭紋）、兩側深灰邊、左側淡色受光邊；G4 關卡決定，主線更新）；
//   沒有素材時用程式畫的退路貼圖。線寬 0.043 世界單位＝g4 中景約 8 px（規格 6–10 px），兩側深灰邊各約 1.5 px。
//   用不受光照影響的材質（亮度只跟舞台燈總量走），擷取量得到的 ΔL* 才穩定。
// - 紙環：素材貼圖 tex-string-ring v02（128×128 米白紙環 sRGB≈(251,242,222)＋紙紋、暖棕細描邊、右下單側厚紙陰影，中間透明；
//   G4 修正第 2 輪第 8 項）。貼圖取樣 LOD 偏移 −1（環身不被描邊糊灰）；last.ring＝紙環實際畫的位置（含前移 RING_Z）。
//   正方形、直徑 0.103 世界單位（約 2.4 倍線寬），正對鏡頭、不隨肢體旋轉、不拉長；不用矩形帶、鉚釘或扁板。
//   紙環中心＝扣點（扣點在肢體剪影內，見 assets/final/rig/ale_attach_v05.json）；線的下端停在紙環上緣（往線的方向退 0.4×直徑），
//   紙環畫在部件與線的上面。
// - 從畫面上方外面垂下；不畫操控者的手或人影。
// - 受力順序：線先繃緊（弧度消失），肢體才被拉動；擺盪用固定步長的彈簧阻尼模擬，每個 cue 開始時重設，
//   所以重播與上一步會得到一模一樣的畫面。
// - 鬆垂弧（G4 修正第 2 輪第 6 項）：線還鬆時，彎曲集中在「紙環往上 sagLength()」這一段（畫面裡看得到的下段），
//   形狀 sagShape(u)＝6.75·u·(1−u)²：最大偏移在下段 1/3 處，往上以斜率 0 平順接回直線（沒有折角）；
//   g4 中景線鬆（張力 0.2）時，畫面中段偏離直線約 20–30 px；張力 1 時 bow＝0，整條線是直線。
//   網格在下段細分 30 段、上段（直線）6 段；中心線世界座標存在 last.path，擷取量測（Stage.probe）直接投影這條線。
// - 復原 API：鬆（tension→0、弧度變大）、淡（opacity）、脫落（紙環打開、線往上飄出畫面）；沒有「剪斷」。
import {
  BufferAttribute, BufferGeometry, CanvasTexture, DoubleSide, LinearFilter, LinearMipmapLinearFilter, Mesh, MeshBasicMaterial, PlaneGeometry,
  RepeatWrapping, SRGBColorSpace, Texture, Vector3,
} from 'three';
import { finishTexture, makeCanvas } from './paper';
import { seeded } from '../util/math';

export const ROPE_COLORS = { body: '#b3b0aa', edge: '#403d3a', lit: '#d7d4cc', fiberDark: 'rgba(40,38,34,0.16)', fiberLight: 'rgba(245,242,234,0.2)' };

/** 退路紙繩貼圖（素材 tex-string-rope 缺圖時）：淡灰紙繩身、斜向扭紋、兩側深灰邊、左側受光邊（u＝橫跨寬度，v＝沿長度重複） */
export function ropeTexture(): CanvasTexture {
  const W = 64, H = 256;
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = ROPE_COLORS.body;
  g.fillRect(0, 0, W, H);
  // 斜向扭紋（每個週期 3 道）＋紙纖維
  g.strokeStyle = 'rgba(70,64,58,0.22)';
  g.lineWidth = 5;
  for (let k = -1; k < 4; k++) { const y = k * (H / 3); g.beginPath(); g.moveTo(10, y + 30); g.lineTo(W - 10, y); g.stroke(); }
  const r = seeded(913);
  for (let i = 0; i < 220; i++) {
    const x = 12 + r() * (W - 24), y = r() * H, len = 4 + r() * 12;
    g.strokeStyle = r() < 0.5 ? ROPE_COLORS.fiberDark : ROPE_COLORS.fiberLight;
    g.lineWidth = 0.7 + r() * 0.8;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 3, y + len); g.stroke();
  }
  g.fillStyle = ROPE_COLORS.edge;
  g.fillRect(0, 0, 12, H);
  g.fillRect(W - 12, 0, 12, H);
  g.fillStyle = ROPE_COLORS.lit;
  g.fillRect(12, 0, 6, H);
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = RepeatWrapping;
  t.wrapT = RepeatWrapping;
  return t;
}

/** 退路紙環貼圖（素材 tex-string-ring 缺圖時）：透明底上的圓環（外深灰細線、白紙芯邊、淡灰環身、內深灰細線） */
export function ringTexture(): CanvasTexture {
  // 與素材 tex-string-ring v02 一致：米白紙環（#FBF2DE）、暖棕細描邊（#4A3426）、右下單側厚紙陰影，沒有金屬漸層或高光
  const S = 128;
  const [c, g] = makeCanvas(S, S);
  const ring = (cx: number, cy: number, r: number, w: number, col: string): void => { g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke(); };
  ring(S / 2 + 3, S / 2 + 4, 42, 22, 'rgba(132,106,78,0.9)');
  ring(S / 2, S / 2, 42, 24, '#4a3426');
  ring(S / 2, S / 2, 42, 19, '#fbf2de');
  return finishTexture(new CanvasTexture(c));
}

let ropeTex: Texture | null = null;
let ringTex: Texture | null = null;

/**
 * 換用素材貼圖（Stage.setScene 在建立紙偶前呼叫）：rope＝tex-string-rope、ring＝tex-string-ring；缺圖時用程式畫的退路。
 * anisotropy：細長的紙繩斜著貼時保留扭紋（渲染器支援的上限內）。
 */
export function configureStringTextures(rope: CanvasImageSource | undefined, ring: CanvasImageSource | undefined, anisotropy = 4): { rope: 'image' | 'fallback'; ring: 'image' | 'fallback' } {
  const mk = (img: CanvasImageSource, repeat: boolean): Texture => {
    const t = new Texture(img as HTMLImageElement);
    t.colorSpace = SRGBColorSpace;
    t.generateMipmaps = true;
    t.minFilter = LinearMipmapLinearFilter;
    t.magFilter = LinearFilter;
    t.anisotropy = anisotropy;
    if (repeat) { t.wrapS = RepeatWrapping; t.wrapT = RepeatWrapping; }
    t.needsUpdate = true;
    return t;
  };
  ropeTex = rope ? mk(rope, true) : null;
  ringTex = ring ? mk(ring, false) : null;
  return { rope: rope ? 'image' : 'fallback', ring: ring ? 'image' : 'fallback' };
}

export function ropeMaterial(): MeshBasicMaterial {
  ropeTex ??= ropeTexture();
  return new MeshBasicMaterial({ map: ropeTex, side: DoubleSide });
}

/**
 * 紙環貼圖取樣往細一級 mip（LOD 偏移 −1）：紙環在畫面上只有約 15–27 px，預設三線性取樣會用到 16–32 px 的 mip，
 * 深棕描邊與厚紙陰影被糊進米白環身，看起來變灰（G4 修正第 2 輪第 8 項）；偏移後環身保持紙色，描邊仍有反鋸齒。
 */
const RING_LOD_BIAS = -1.0;

export function ringMaterial(): MeshBasicMaterial {
  ringTex ??= ringTexture();
  // 紙環素材是透明圓環：刀切邊（alphaTest），中間看得到肢體
  const m = new MeshBasicMaterial({ map: ringTex, side: DoubleSide, alphaTest: 0.5, transparent: false });
  m.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>',
      `#ifdef USE_MAP\n\tvec4 sampledDiffuseColor = texture2D( map, vMapUv, ${RING_LOD_BIAS.toFixed(2)} );\n\tdiffuseColor *= sampledDiffuseColor;\n#endif`);
  };
  m.customProgramCacheKey = () => 'paper-ring-lodbias';
  return m;
}

/** 紙環在線前面多少（世界單位）；last.ring 記的是紙環實際畫的位置（含這個前移），量測的紙環中心才和畫面一致 */
const RING_Z = 0.02;

/** 紙環直徑（世界單位）：約 2.4 倍線寬，中景約 19 px（assets/final/g4_manifest.json string_render） */
export const RING_DIAMETER = 0.103;

/** 網格分段：下段（鬆垂弧所在）30 段＋上段（直線）6 段 */
const SEG_LOW = 30;
const SEG_HIGH = 6;
const SEGMENTS = SEG_LOW + SEG_HIGH;
const tmpB = new Vector3();

/** 鬆垂弧形狀（u＝從紙環往上的距離 ÷ 下段長度）：u＝0 與 1 時為 0，最大值 1 在 u＝1/3，u＝1 處斜率 0 */
export function sagShape(u: number): number { return u <= 0 || u >= 1 ? 0 : 6.75 * u * (1 - u) * (1 - u); }
function sagSlope(u: number): number { return u <= 0 || u >= 1 ? 0 : 6.75 * (1 - u) * (1 - 3 * u); }
/** 鬆垂弧所在的下段長度（世界單位）：線長的 20%，限制在 1.0–3.0（g4 中景約等於畫面裡看得到的線段） */
export function sagLength(len: number): number { return Math.max(1.0, Math.min(3.0, len * 0.2)); }

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
  /** 紙環直徑（世界單位；省略＝RING_DIAMETER） */
  ringDiameter?: number;
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
  /** 中心線世界座標（x,y,z × 37 點，上端 → 下端） */
  private center = new Float32Array((SEGMENTS + 1) * 3);
  /** 最近一次的螢幕取樣資訊（測試與擷取量測用）；path＝中心線世界座標（上端 → 線的下端，37 點） */
  last: { top: Vector3; bottom: Vector3; width: number; visible: boolean; bow: number; ring: Vector3 | null; ringD: number; path: Float32Array } = { top: new Vector3(), bottom: new Vector3(), width: 0, visible: false, bow: 0, ring: null, ringD: 0, path: new Float32Array(0) };

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
    const { top } = p;
    // 中心線：從扣點（紙環中心 p.bottom）沿直線往上到 top，再加上側向的鬆垂弧 bow·sagShape(s／Ls)
    //（s＝沿直線從扣點往上的距離）。紙環扣上時，線的下端停在紙環上緣：從 s0＝0.4×直徑開始畫。
    const D = p.ringDiameter ?? RING_DIAMETER;
    const ringOn = p.ring > 0.01;
    const pop = p.ring < 1 ? 0.6 + 0.4 * p.ring : 1;
    const ax = p.bottom.x, ay = p.bottom.y, az = p.bottom.z;
    const ux0 = top.x - ax, uy0 = top.y - ay;
    const len = Math.hypot(ux0, uy0) || 1;
    const ux = ux0 / len, uy = uy0 / len;
    // 法線（與舊版二次貝茲相同的方向慣例：bow > 0 往 (uy, −ux)）
    const nx = uy, ny = -ux;
    const Ls = Math.min(sagLength(len), len);
    const s0 = ringOn ? Math.min(0.4 * D * pop, len * 0.5) : 0;
    const bow = p.bow;
    for (let i = 0; i <= SEGMENTS; i++) {
      // i＝0 在上端；下段（i ≥ SEG_HIGH）細分
      const sd = i <= SEG_HIGH ? len - (len - Ls) * (i / SEG_HIGH) : Ls - (Ls - s0) * ((i - SEG_HIGH) / SEG_LOW);
      const s = Math.max(s0, sd);
      const u = s / Ls;
      const off = bow * sagShape(u);
      const px = ax + ux * s + nx * off;
      const py = ay + uy * s + ny * off;
      const pz = az + (top.z - az) * (s / len);
      // 切線（往上）：up＋法線×bow·g'(u)／Ls
      const sl = s < Ls ? (bow * sagSlope(u)) / Ls : 0;
      const tx = ux + nx * sl, ty = uy + ny * sl;
      const tl = Math.hypot(tx, ty) || 1;
      // 紙帶寬度：u=0 在畫面左側（受光邊在左）
      let ox = (-ty / tl) * p.width / 2, oy = (tx / tl) * p.width / 2;
      if (ox > 0) { ox = -ox; oy = -oy; }
      const k = i * 6;
      this.pos[k] = px + ox; this.pos[k + 1] = py + oy; this.pos[k + 2] = pz;
      this.pos[k + 3] = px - ox; this.pos[k + 4] = py - oy; this.pos[k + 5] = pz;
      const c3 = i * 3;
      this.center[c3] = px; this.center[c3 + 1] = py; this.center[c3 + 2] = pz;
      const v = (len - s) / (p.width * 4);
      const uvk = i * 4;
      this.uv[uvk] = 0; this.uv[uvk + 1] = v;
      this.uv[uvk + 2] = 1; this.uv[uvk + 3] = v;
    }
    const bottom = tmpB.set(this.center[SEGMENTS * 3], this.center[SEGMENTS * 3 + 1], this.center[SEGMENTS * 3 + 2]);
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
    this.last = { top: top.clone(), bottom: bottom.clone(), width: p.width, visible: true, bow: p.bow, ring: ringOn ? new Vector3(p.bottom.x, p.bottom.y, p.bottom.z + RING_Z) : null, ringD: ringOn ? D * pop : 0, path: this.center };

    // 紙環：正方形圓環貼圖，正對鏡頭、不隨肢體旋轉；扣上時由 0.6 倍彈到原尺寸
    this.ring.visible = ringOn;
    if (ringOn) {
      this.ring.position.set(p.bottom.x, p.bottom.y, p.bottom.z + RING_Z);
      this.ring.rotation.set(0, 0, 0);
      this.ring.scale.set(D * pop, D * pop, 1);
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

