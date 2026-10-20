// 程式產生的紙片佔位貼圖（之後換成 assets/final 的正式素材）。
// 刀切邊：外形完全不透明＋alphaTest 0.5，寫入深度；邊緣畫一圈較深的切口線與一條淺色紙芯，帶出剪紙感。
import { CanvasTexture, DoubleSide, MeshStandardMaterial, SRGBColorSpace, type Texture } from 'three';
import { seeded } from '../util/math';

export type ShapeKind = 'rect' | 'round' | 'ellipse' | 'trapezoid' | 'capsule' | 'hand' | 'foot' | 'cap';

/** 貼圖解析度：每單位幾個像素（A 級 220，B 級 150） */
export let PX_PER_UNIT = 220;
export function setTextureDensity(ppu: number): void { PX_PER_UNIT = ppu; }

export function makeCanvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = Math.max(4, Math.round(w));
  c.height = Math.max(4, Math.round(h));
  return [c, c.getContext('2d')!];
}

/** 外形路徑（畫在 pad 內縮的範圍） */
export function shapePath(g: CanvasRenderingContext2D, shape: ShapeKind, W: number, H: number, pad: number): void {
  const x = pad, y = pad, w = W - pad * 2, h = H - pad * 2;
  g.beginPath();
  switch (shape) {
    case 'ellipse': g.ellipse(W / 2, H / 2, w / 2, h / 2, 0, 0, Math.PI * 2); break;
    case 'round': g.roundRect(x, y, w, h, Math.min(w, h) * 0.28); break;
    case 'capsule': g.roundRect(x, y, w, h, Math.min(w, h) / 2); break;
    case 'trapezoid': {
      // 上窄下寬的軀幹（y 向下）
      const inset = w * 0.12;
      g.moveTo(x + inset, y); g.lineTo(x + w - inset, y);
      g.quadraticCurveTo(x + w, y + h * 0.1, x + w, y + h * 0.35);
      g.lineTo(x + w * 0.96, y + h); g.lineTo(x + w * 0.04, y + h); g.lineTo(x, y + h * 0.35);
      g.quadraticCurveTo(x, y + h * 0.1, x + inset, y);
      break;
    }
    case 'hand': {
      // 手掌＋拇指凸起（指尖朝下）
      g.roundRect(x + w * 0.08, y, w * 0.84, h * 0.92, w * 0.38);
      g.ellipse(x + w * 0.86, y + h * 0.38, w * 0.16, h * 0.2, -0.4, 0, Math.PI * 2);
      break;
    }
    case 'foot': g.roundRect(x, y + h * 0.1, w, h * 0.9, [h * 0.3, h * 0.5, h * 0.45, h * 0.2]); break;
    case 'cap': {
      // 頭髮／帽子：上半圓
      g.ellipse(W / 2, y + h * 0.95, w / 2, h * 0.95, 0, Math.PI, 0);
      g.closePath();
      break;
    }
    default: g.rect(x, y, w, h);
  }
}

/** 紙纖維：短線條與斑點，低透明度疊在底色上 */
export function fibers(g: CanvasRenderingContext2D, W: number, H: number, seed: number, strength = 1): void {
  const r = seeded(seed);
  const n = Math.round((W * H) / 900 * strength);
  for (let i = 0; i < n; i++) {
    const x = r() * W, y = r() * H, len = 3 + r() * 12, a = r() * Math.PI;
    g.strokeStyle = r() < 0.5 ? `rgba(255,255,255,${0.05 + r() * 0.08})` : `rgba(60,40,20,${0.03 + r() * 0.06})`;
    g.lineWidth = 0.6 + r() * 0.9;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len); g.stroke();
  }
}

export interface CutPaperOptions {
  /** 世界單位尺寸 */
  w: number;
  h: number;
  color: string;
  shape: ShapeKind;
  seed: number;
  /** 切口線顏色（預設比底色深） */
  edge?: string;
  /** 額外圖樣（臉、花紋）；座標為像素，y 向下 */
  decorate?: (g: CanvasRenderingContext2D, W: number, H: number) => void;
  ppu?: number;
}

/** 單一刀切紙片貼圖 */
export function cutPaperTexture(o: CutPaperOptions): CanvasTexture {
  const ppu = o.ppu ?? PX_PER_UNIT;
  const W = Math.min(1024, Math.max(16, o.w * ppu));
  const H = Math.min(1024, Math.max(16, o.h * ppu));
  const [c, g] = makeCanvas(W, H);
  const pad = Math.max(2, Math.min(W, H) * 0.03);
  const lw = Math.max(1.5, Math.min(W, H) * 0.035);
  shapePath(g, o.shape, c.width, c.height, pad);
  g.fillStyle = o.color;
  g.fill();
  g.save();
  g.clip();
  fibers(g, c.width, c.height, o.seed);
  o.decorate?.(g, c.width, c.height);
  g.restore();
  // 切口：外圈深色線＋內圈淺色紙芯
  shapePath(g, o.shape, c.width, c.height, pad);
  g.lineWidth = lw;
  g.strokeStyle = o.edge ?? 'rgba(40,25,15,0.55)';
  g.stroke();
  shapePath(g, o.shape, c.width, c.height, pad + lw * 0.9);
  g.lineWidth = Math.max(1, lw * 0.35);
  g.strokeStyle = 'rgba(255,248,235,0.35)';
  g.stroke();
  return finishTexture(new CanvasTexture(c));
}

export function finishTexture<T extends Texture>(t: T): T {
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  t.needsUpdate = true;
  return t;
}

/** 刀切紙片材質（alphaTest＋寫深度＋雙面） */
export function cutPaperMaterial(map: Texture, extra: Partial<{ roughness: number; color: string }> = {}): MeshStandardMaterial {
  return new MeshStandardMaterial({
    map, alphaTest: 0.5, transparent: false, depthWrite: true, side: DoubleSide,
    roughness: extra.roughness ?? 0.92, metalness: 0, ...(extra.color ? { color: extra.color } : {}),
  });
}

/** 整張紙底（背景、地板）：底色＋纖維＋可選圖樣 */
export function paperSheetTexture(wPx: number, hPx: number, color: string, seed: number,
  decorate?: (g: CanvasRenderingContext2D, W: number, H: number) => void): CanvasTexture {
  const [c, g] = makeCanvas(wPx, hPx);
  g.fillStyle = color;
  g.fillRect(0, 0, c.width, c.height);
  fibers(g, c.width, c.height, seed, 1.4);
  decorate?.(g, c.width, c.height);
  return finishTexture(new CanvasTexture(c));
}
