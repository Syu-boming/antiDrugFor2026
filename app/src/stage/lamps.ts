// 台口八盞燈（G5 修正第 1 輪，主線裁定 3）：全劇模式（?cues=show）才有；?cues=g4 不建立、畫面不變。
// - 位置：台口外框上方（開口上緣之上、外框前面一點），一條窄木條上並排坐著 8 盞剪紙紙燈（不從上方垂繩，避免和操偶線的意象混淆）；
//   跟換景無關，所有景都在。
//   quiz 鏡位（題卡模式後拉）看得到、而且在題卡上緣之上（1080p 約 y 14–92 px）；台口寬度約畫面 60%。
//   故事鏡位（show_mid、show_wide、g4_mid…）與 wide／g4_stage 都在畫面上緣之外（wide 剛好在外，光暈也不進畫面）。
// - 亮度綁定 world.lamps（0–1；引擎的 lampsBefore＋本 cue 的 lamp.light 進度）：未亮＝灰白紙色＋深棕細邊；
//   亮＝暖黃紙色（交叉淡入）＋柔和泛光（FX14：加法混色的暖色光暈，只隨亮度單向漸變）。
//   不閃、不晃：亮度只跟 world.lamps 走（點燈約 1.5 秒單向漸亮），亮了一直亮到劇終；上一步、章節跳轉由 lampsBefore 還原。
// - 不受舞台光照影響（MeshBasicMaterial）：未亮的紙色只跟舞台燈總量略變（題卡模式 0.55 時約 0.8 倍），不同景看起來一樣。
// - 不投影、不套 FX8 降彩（燈是全班的回報，不屬於景片）。
import { AdditiveBlending, CanvasTexture, Group, Mesh, MeshBasicMaterial, PlaneGeometry, Vector3 } from 'three';
import { LAYER, STAGE_OPENING } from './layers';
import { finishTexture, makeCanvas } from './paper';
import { seeded } from '../util/math';

/** 台口燈的版面（世界單位）：燈中心 x、燈下緣 y、燈寬高、紙繩高度、前後位置 */
export const LAMP_ROW = {
  count: 8,
  /** 第一盞與相鄰間距：中心 −5.6 … +5.6（含燈寬約 11.9 單位＝quiz 鏡位畫面寬約 60%） */
  x0: -5.6, dx: 1.6,
  w: 0.62, h: 0.8,
  /** 燈下緣：比 wide 鏡位在這個深度的畫面上緣（約 9.01）高一點，wide 看不到 */
  bottom: 9.06,
  /** 放燈的木條（燈下緣＝木條上緣）：wide 鏡位這個深度的畫面上緣約 9.01，木條在 9.02 以上，wide 看不到 */
  ledge: 0.04,
  z: LAYER.proscenium.z + 0.12,
  order: LAYER.proscenium.order + 10,
} as const;

const COLORS = {
  outline: '#5a4332', cap: '#5a4332',
  paper: '#dcd6cb', rib: 'rgba(107,84,64,0.45)',
  litIn: '#ffe9ad', litOut: '#f3b041', litRib: 'rgba(150,92,32,0.55)',
};

/** 紙燈貼圖（和題卡上的小燈同一個造型：上下深棕木蓋、橢圓紙身、竹骨） */
function lampTexture(lit: boolean, seed: number): CanvasTexture {
  const W = 128, H = 166;
  const [c, g] = makeCanvas(W, H);
  const cx = W / 2, cy = 86, rx = 50, ry = 56;
  g.clearRect(0, 0, W, H);
  // 紙身
  if (lit) {
    const grd = g.createRadialGradient(cx, cy - 6, 6, cx, cy, ry);
    grd.addColorStop(0, COLORS.litIn);
    grd.addColorStop(1, COLORS.litOut);
    g.fillStyle = grd;
  } else g.fillStyle = COLORS.paper;
  g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.fill();
  // 紙纖維（未亮才明顯）
  const r = seeded(seed);
  g.save();
  g.beginPath(); g.ellipse(cx, cy, rx - 2, ry - 2, 0, 0, Math.PI * 2); g.clip();
  for (let i = 0; i < 70; i++) {
    const x = cx - rx + r() * rx * 2, y = cy - ry + r() * ry * 2, len = 4 + r() * 9;
    g.strokeStyle = lit ? 'rgba(255,250,230,0.18)' : (r() < 0.5 ? 'rgba(90,70,50,0.10)' : 'rgba(255,255,250,0.22)');
    g.lineWidth = 0.8 + r() * 0.6;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 4, y + len); g.stroke();
  }
  g.restore();
  // 竹骨：中央直線＋左右兩道弧
  g.strokeStyle = lit ? COLORS.litRib : COLORS.rib;
  g.lineWidth = 3;
  g.beginPath(); g.moveTo(cx, cy - ry + 4); g.lineTo(cx, cy + ry - 4); g.stroke();
  for (const s of [-1, 1]) {
    g.beginPath();
    g.moveTo(cx + s * 29, cy - ry + 8);
    g.quadraticCurveTo(cx + s * (rx + 12), cy, cx + s * 29, cy + ry - 8);
    g.stroke();
  }
  // 深棕細邊
  g.strokeStyle = COLORS.outline;
  g.lineWidth = 5;
  g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.stroke();
  // 上下木蓋
  g.fillStyle = COLORS.cap;
  const cap = (y: number): void => { g.beginPath(); g.roundRect(cx - 23, y, 46, 20, 6); g.fill(); };
  cap(6); cap(140);
  return finishTexture(new CanvasTexture(c));
}

/** 柔和泛光：暖色放射漸層（加法混色） */
function glowTexture(): CanvasTexture {
  const S = 128;
  const [c, g] = makeCanvas(S, S);
  const grd = g.createRadialGradient(S / 2, S / 2, 4, S / 2, S / 2, S / 2);
  grd.addColorStop(0, 'rgba(255,196,96,0.85)');
  grd.addColorStop(0.45, 'rgba(255,178,80,0.35)');
  grd.addColorStop(1, 'rgba(255,170,70,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, S, S);
  return finishTexture(new CanvasTexture(c));
}

/** 放燈的窄木條（紙板）：燈坐在上面，不用從上方垂下的繩子（避免和操偶線的意象混淆） */
function ledgeTexture(): { tex: CanvasTexture; width: number } {
  const width = 2 * (Math.abs(LAMP_ROW.x0) + 0.62);
  const W = 1024, H = 16;
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = '#a9825a'; g.fillRect(0, 0, W, H);
  const r = seeded(711);
  for (let i = 0; i < 260; i++) { g.fillStyle = r() < 0.5 ? 'rgba(80,56,36,0.18)' : 'rgba(240,220,190,0.18)'; g.fillRect(r() * W, r() * H, 3 + r() * 10, 1); }
  g.fillStyle = '#d9b98a'; g.fillRect(0, 0, W, 3);
  g.fillStyle = '#4a3426'; g.fillRect(0, H - 3, W, 3);
  return { tex: finishTexture(new CanvasTexture(c)), width };
}

export class ProsceniumLamps {
  readonly group = new Group();
  private base: Mesh[] = [];
  private lit: Mesh[] = [];
  private glow: Mesh[] = [];
  private level: number[] = Array(LAMP_ROW.count).fill(0);
  private ledge: Mesh | null = null;
  private built = false;
  private on = false;

  constructor() {
    this.group.name = 'proscenium-lamps';
    this.group.visible = false;
  }

  /** 全劇模式才建立（第一次啟用時才畫貼圖；G4 模式完全不建立） */
  setEnabled(on: boolean): void {
    if (on && !this.built) this.build();
    this.on = on;
    this.group.visible = on;
  }

  /** 是否啟用（不看 group.visible：預先編譯時會暫時把所有隱藏物件設成可見） */
  get enabled(): boolean { return this.on; }

  private build(): void {
    this.built = true;
    const geo = new PlaneGeometry(LAMP_ROW.w, LAMP_ROW.h);
    const glowTex = glowTexture();
    const glowGeo = new PlaneGeometry(LAMP_ROW.w * 1.75, (LAMP_ROW.h / 2 - 0.02) * 2 + 0.1);
    const cy = LAMP_ROW.bottom + LAMP_ROW.h / 2;
    for (let k = 0; k < LAMP_ROW.count; k++) {
      const x = LAMP_ROW.x0 + k * LAMP_ROW.dx;
      const g = new Mesh(glowGeo, new MeshBasicMaterial({ map: glowTex, transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
      g.position.set(x, cy + 0.05, LAMP_ROW.z - 0.02);
      g.renderOrder = LAMP_ROW.order;
      g.visible = false;
      const b = new Mesh(geo, new MeshBasicMaterial({ map: lampTexture(false, 700 + k), alphaTest: 0.5 }));
      b.position.set(x, cy, LAMP_ROW.z);
      b.renderOrder = LAMP_ROW.order + 1;
      const l = new Mesh(geo, new MeshBasicMaterial({ map: lampTexture(true, 800 + k), transparent: true, opacity: 0, depthWrite: false }));
      l.position.set(x, cy, LAMP_ROW.z + 0.004);
      l.renderOrder = LAMP_ROW.order + 2;
      l.visible = false;
      for (const m of [g, b, l]) { m.castShadow = false; m.receiveShadow = false; m.frustumCulled = false; }
      this.group.add(g, b, l);
      this.glow.push(g); this.base.push(b); this.lit.push(l);
    }
    const ledge = ledgeTexture();
    const lm = new Mesh(new PlaneGeometry(ledge.width, LAMP_ROW.ledge), new MeshBasicMaterial({ map: ledge.tex }));
    lm.position.set(0, LAMP_ROW.bottom - LAMP_ROW.ledge / 2, LAMP_ROW.z + 0.006);
    lm.renderOrder = LAMP_ROW.order + 3;
    lm.castShadow = false; lm.receiveShadow = false;
    this.ledge = lm;
    this.group.add(lm);
  }

  /** 每格：lamps＝world.lamps（0–1），light＝舞台燈總量（未亮的紙色跟著略變） */
  update(lamps: number[], light: number): void {
    if (!this.on || !this.built) return;
    const paper = 0.55 + 0.45 * Math.max(0, Math.min(1, light));
    if (this.ledge) (this.ledge.material as MeshBasicMaterial).color.setScalar(paper);
    for (let k = 0; k < LAMP_ROW.count; k++) {
      const v = Math.max(0, Math.min(1, lamps[k] ?? 0));
      this.level[k] = v;
      (this.base[k].material as MeshBasicMaterial).color.setScalar(paper);
      const lm = this.lit[k].material as MeshBasicMaterial;
      lm.opacity = v;
      this.lit[k].visible = v > 0.001;
      const gm = this.glow[k].material as MeshBasicMaterial;
      gm.opacity = 0.7 * v;
      this.glow[k].visible = v > 0.001;
    }
  }

  /** 測試與量測：每盞燈的亮度與畫面外框（像素，用舞台的投影函式） */
  state(project: (p: Vector3) => [number, number]): { enabled: boolean; lit: number[]; boxes: [number, number, number, number][] } {
    const boxes: [number, number, number, number][] = [];
    if (this.built) {
      for (let k = 0; k < LAMP_ROW.count; k++) {
        const x = LAMP_ROW.x0 + k * LAMP_ROW.dx;
        const a = project(new Vector3(x - LAMP_ROW.w / 2, LAMP_ROW.bottom + LAMP_ROW.h, LAMP_ROW.z));
        const b = project(new Vector3(x + LAMP_ROW.w / 2, LAMP_ROW.bottom, LAMP_ROW.z));
        boxes.push([a[0], a[1], b[0], b[1]].map((v) => Math.round(v * 10) / 10) as [number, number, number, number]);
      }
    }
    return { enabled: this.enabled, lit: [...this.level], boxes };
  }
}

/** 給文件與測試：台口開口上緣（世界 y） */
export const OPENING_TOP = STAGE_OPENING.centerY + STAGE_OPENING.height / 2;
