// 資料包載入：素材一律包成傳統 script（dist/data/*.js），內容呼叫 window.__pack(id, 資料)。
// file:// 不能用 fetch 與 ES module，但可以插入 <script src>，所以 file://、http、Electron 三種環境都能用同一套。
// window.__pack 由 index.html 開頭的內嵌 script 先定義好。

declare global {
  interface Window {
    __packs: Record<string, unknown>;
    __pack: (id: string, data: unknown) => void;
  }
}

/** 打包時產生的總表（tools/pack.mjs 寫成 data/manifest.js） */
export interface PackManifest {
  format: 'antidrug-packs/1';
  builtAt: string;
  /** cue 檔名 → 資料包檔名 */
  cueSets: Record<string, string>;
  /** 音檔 id（例如 vo_a2_c002_01）→ 所在資料包與長度 */
  audio: Record<string, { file: string; duration: number | null; source: string; bus: 'vo' | 'music' | 'sfx' }>;
  /** 圖片 id → 所在資料包 */
  images: Record<string, { file: string; source: string }>;
  /** 對嘴資料 id → 所在資料包 */
  lipsync: Record<string, { file: string }>;
}

export function getPack<T>(id: string): T | undefined {
  return (window.__packs ?? {})[id] as T | undefined;
}

const loading = new Map<string, Promise<void>>();

/** 以 <script src> 載入一個資料包檔（相對 index.html 的 data/ 資料夾）；同一檔只載一次 */
export function loadPackFile(file: string): Promise<void> {
  const cached = loading.get(file);
  if (cached) return cached;
  const p = new Promise<void>((resolve, reject) => {
    const s = document.createElement('script');
    s.src = `data/${file}`;
    s.async = false;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`資料包載入失敗：data/${file}`));
    document.head.appendChild(s);
  });
  loading.set(file, p);
  return p;
}

export async function loadPackFiles(files: Iterable<string>, onProgress?: (done: number, total: number) => void): Promise<void> {
  const list = [...new Set(files)];
  let done = 0;
  await Promise.all(list.map(async (f) => { await loadPackFile(f); onProgress?.(++done, list.length); }));
}

/** data URL（base64）→ ArrayBuffer，不經過 fetch，file:// 也能用 */
export function dataUrlToArrayBuffer(dataUrl: string): ArrayBuffer {
  const comma = dataUrl.indexOf(',');
  const bin = atob(dataUrl.slice(comma + 1));
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return buf.buffer;
}

/** data URL → HTMLImageElement（data URL 不會污染 WebGL 貼圖） */
export function dataUrlToImage(dataUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('圖片解碼失敗'));
    img.src = dataUrl;
  });
}
