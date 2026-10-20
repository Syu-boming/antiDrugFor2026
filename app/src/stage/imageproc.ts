// 圖片前處理（載入時做一次，結果固定）：裁切、接縫清除、顏色外擴、整體外輪廓背板。
// 全部是確定性的像素運算，同一張圖每次得到同一個結果（擷取與重播一致）。

export interface Pixels { width: number; height: number; data: Uint8ClampedArray }

export function makeCanvas2(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w));
  c.height = Math.max(1, Math.round(h));
  return [c, c.getContext('2d', { willReadFrequently: true })!];
}

/** 從圖片裁出 [x0,y0,x1,y1)（可超出邊界，超出部分透明） */
export function cropPixels(img: CanvasImageSource, x0: number, y0: number, x1: number, y1: number): Pixels {
  const [c, g] = makeCanvas2(x1 - x0, y1 - y0);
  g.drawImage(img, -x0, -y0);
  const d = g.getImageData(0, 0, c.width, c.height);
  return { width: c.width, height: c.height, data: d.data };
}

export function pixelsToCanvas(p: Pixels): HTMLCanvasElement {
  const [c, g] = makeCanvas2(p.width, p.height);
  const id = g.createImageData(p.width, p.height);
  id.data.set(p.data);
  g.putImageData(id, 0, 0);
  return c;
}

/** 不透明範圍（alpha ≥ th）的外框；沒有不透明像素回傳 null */
export function alphaBBox(p: Pixels, th = 128): [number, number, number, number] | null {
  let x0 = p.width, y0 = p.height, x1 = -1, y1 = -1;
  for (let y = 0; y < p.height; y++) {
    for (let x = 0; x < p.width; x++) {
      if (p.data[(y * p.width + x) * 4 + 3] >= th) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
  }
  return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
}

/** 一維平方距離轉換（Felzenszwalb） */
function edt1d(f: Float32Array, n: number, d: Float32Array, v: Int32Array, z: Float32Array): void {
  let k = 0;
  v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
  for (let q = 1; q < n; q++) {
    let s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
    while (s <= z[k]) { k--; s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
    k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
  }
  k = 0;
  for (let q = 0; q < n; q++) { while (z[k + 1] < q) k++; d[q] = (q - v[k]) * (q - v[k]) + f[v[k]]; }
}

/** 精確歐氏距離轉換：回傳每個像素到最近「內部」像素的距離（內部像素為 0） */
export function distanceField(inside: Uint8Array, w: number, h: number): Float32Array {
  const INF = 1e20;
  const n = Math.max(w, h);
  const f = new Float32Array(n), d = new Float32Array(n), z = new Float32Array(n + 1);
  const v = new Int32Array(n);
  const grid = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) grid[i] = inside[i] ? 0 : INF;
  for (let x = 0; x < w; x++) {
    for (let y = 0; y < h; y++) f[y] = grid[y * w + x];
    edt1d(f, h, d, v, z);
    for (let y = 0; y < h; y++) grid[y * w + x] = d[y];
  }
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) f[x] = grid[y * w + x];
    edt1d(f, w, d, v, z);
    for (let x = 0; x < w; x++) grid[y * w + x] = Math.sqrt(d[x]);
  }
  return grid;
}

export function alphaMask(p: Pixels, th = 128): Uint8Array {
  const m = new Uint8Array(p.width * p.height);
  for (let i = 0; i < m.length; i++) m[i] = p.data[i * 4 + 3] >= th ? 1 : 0;
  return m;
}

/**
 * 以「已知像素」逐圈往外填色：unknown＝1 的像素取周圍已知像素的平均色（RGB），重複 passes 圈。
 * 用在接縫清除（把切件時留下的深色接縫線換成內側的布料色）與顏色外擴（透明邊的 RGB 換成鄰近色，避免取樣出黑邊）。
 */
export function inpaint(p: Pixels, unknown: Uint8Array, passes: number, keepAlpha = true): void {
  const { width: w, height: h, data } = p;
  const known = new Uint8Array(w * h);
  for (let i = 0; i < known.length; i++) known[i] = unknown[i] ? 0 : (data[i * 4 + 3] > 0 ? 1 : 0);
  const next = new Uint8Array(w * h);
  for (let pass = 0; pass < passes; pass++) {
    let changed = 0;
    next.set(known);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (known[i] || !unknown[i]) continue;
        let r = 0, g = 0, b = 0, n = 0;
        for (let dy = -1; dy <= 1; dy++) {
          const yy = y + dy;
          if (yy < 0 || yy >= h) continue;
          for (let dx = -1; dx <= 1; dx++) {
            const xx = x + dx;
            if (xx < 0 || xx >= w || (dx === 0 && dy === 0)) continue;
            const j = yy * w + xx;
            if (!known[j]) continue;
            r += data[j * 4]; g += data[j * 4 + 1]; b += data[j * 4 + 2]; n++;
          }
        }
        if (!n) continue;
        data[i * 4] = r / n; data[i * 4 + 1] = g / n; data[i * 4 + 2] = b / n;
        if (!keepAlpha) data[i * 4 + 3] = 255;
        next[i] = 1;
        changed++;
      }
    }
    known.set(next);
    if (!changed) break;
  }
}

/** 顏色外擴：透明像素（alpha < 8）的 RGB 換成最近的不透明色（只做 radius 圈） */
export function bleedEdges(p: Pixels, radius = 4): void {
  const unknown = new Uint8Array(p.width * p.height);
  for (let i = 0; i < unknown.length; i++) unknown[i] = p.data[i * 4 + 3] < 8 ? 1 : 0;
  // inpaint 會把 alpha>0 的當已知；這裡讓低 alpha 的也算未知
  const saved = new Uint8ClampedArray(unknown.length);
  for (let i = 0; i < unknown.length; i++) { saved[i] = p.data[i * 4 + 3]; if (unknown[i]) p.data[i * 4 + 3] = 0; }
  inpaint(p, unknown, radius, true);
  for (let i = 0; i < unknown.length; i++) p.data[i * 4 + 3] = saved[i];
}

export interface OutlineStyle {
  /** 白色紙芯邊寬度（貼圖像素）；0＝不畫（圖片本身已經有白邊，例如兒童立牌） */
  core: number;
  /** 深色卡紙側邊寬度（貼圖像素，在紙芯邊外側） */
  edge: number;
  /** 卡紙側邊往右下偏移（貼圖像素），像紙張的厚度 */
  offset: [number, number];
  coreColor: [number, number, number];
  edgeColor: [number, number, number];
}

export const DEFAULT_OUTLINE: OutlineStyle = { core: 12, edge: 6, offset: [3, 4], coreColor: [247, 242, 230], edgeColor: [58, 44, 34] };

/** 由外形產生背板：內部與紙芯邊＝白、外圈＝深色卡紙側邊；邊緣 1 px 抗鋸齒 */
export function outlineBacking(mask: Uint8Array, w: number, h: number, st: OutlineStyle): Pixels {
  const d0 = distanceField(mask, w, h);
  // 偏移後的距離場（卡紙厚度往右下）
  const [ox, oy] = st.offset;
  const shifted = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    const sy = y - oy;
    if (sy < 0 || sy >= h) continue;
    for (let x = 0; x < w; x++) {
      const sx = x - ox;
      if (sx >= 0 && sx < w && mask[sy * w + sx]) shifted[y * w + x] = 1;
    }
  }
  const d1 = distanceField(shifted, w, h);
  const out = new Uint8ClampedArray(w * h * 4);
  const R0 = st.core, R1 = st.core + st.edge;
  for (let i = 0; i < w * h; i++) {
    const a = d0[i], b = d1[i];
    const k = i * 4;
    const coreA = st.core > 0 ? Math.max(0, Math.min(1, R0 + 0.5 - a)) : (a <= 0.5 ? 1 : 0);
    const edgeA = Math.max(0, Math.min(1, Math.max(R1 + 0.5 - a, R1 + 0.5 - b)));
    const alpha = Math.max(coreA, edgeA);
    if (alpha <= 0) { out[k] = st.edgeColor[0]; out[k + 1] = st.edgeColor[1]; out[k + 2] = st.edgeColor[2]; continue; }
    const t = st.core > 0 ? coreA : 0; // 紙芯在上
    out[k] = st.coreColor[0] * t + st.edgeColor[0] * (1 - t);
    out[k + 1] = st.coreColor[1] * t + st.edgeColor[1] * (1 - t);
    out[k + 2] = st.coreColor[2] * t + st.edgeColor[2] * (1 - t);
    out[k + 3] = Math.round(alpha * 255);
  }
  return { width: w, height: h, data: out };
}

/** 相對亮度（sRGB 0–255 → 0–1 線性加權） */
export function luma255(r: number, g: number, b: number): number {
  const L = (c: number): number => { const v = c / 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * L(r) + 0.7152 * L(g) + 0.0722 * L(b);
}

/** CIELAB L*（D65） */
export function lstar(r: number, g: number, b: number): number {
  const Y = luma255(r, g, b);
  return Y > 216 / 24389 ? 116 * Math.cbrt(Y) - 16 : (24389 / 27) * Y;
}
