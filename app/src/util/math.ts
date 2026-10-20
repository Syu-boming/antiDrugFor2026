// 數學小工具：插值、緩動、可重現的亂數。全部是純函式，供動畫與模擬共用。

export const clamp = (v: number, a = 0, b = 1): number => Math.min(b, Math.max(a, v));
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export function smoothstep(e0: number, e1: number, x: number): number {
  const t = clamp((x - e0) / (e1 - e0));
  return t * t * (3 - 2 * t);
}

/** 緩動函式表：cue 的 animation.ease 以名稱指定 */
export const EASE: Record<string, (t: number) => number> = {
  linear: (t) => clamp(t),
  in: (t) => { t = clamp(t); return t * t * t; },
  out: (t) => { t = clamp(t); return 1 - Math.pow(1 - t, 3); },
  inOut: (t) => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; },
  // 正弦：最高速度只有平均速度的 1.57 倍（三次方是 3 倍），鏡頭移動用它，避免高對比景物快速掃過造成明暗頻繁變化
  sine: (t) => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t)),
  // 布幕：起步慢、收尾更慢，像有重量的紙布
  heavy: (t) => { t = clamp(t); return t < 0.5 ? 8 * t ** 4 : 1 - Math.pow(-2 * t + 2, 4) / 2; },
};

export const ease = (name: string | undefined, t: number): number => (EASE[name ?? 'inOut'] ?? EASE.inOut)(t);

/** 可重現的亂數（mulberry32）：同一個種子永遠得到同一串數字，擷取與重播才會一致 */
export function seeded(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 字串雜湊成整數（給種子用） */
export function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
