// 舞台版面（v1.2 第 16.1、21 節）：
// - 一律 16:9 舞台；視窗較寬時左右留黑邊。
// - 視窗較窄（4:3 投影 1024×768）時舞台靠上對齊，黑邊集中在下方放字幕，不縮小字級。
// - 16:10 這類下方黑邊不夠放兩行字幕的，字幕維持在舞台內下方安全區（下方約 20%）。
// - 字級與介面尺寸一律以舞台高度的比例計算（CSS 變數 --H），不寫死 1080p 像素。

export interface Rect { x: number; y: number; w: number; h: number }
export interface StageLayout { stage: Rect; subtitle: Rect; subtitleInside: boolean; H: number }

/** 兩行字幕＋底板約需舞台高度的 21% */
const SUB_NEED = 0.21;

export function computeLayout(vw: number, vh: number): StageLayout {
  const aspect = 16 / 9;
  if (vw / vh >= aspect) {
    const h = vh, w = h * aspect;
    const stage = { x: (vw - w) / 2, y: 0, w, h };
    return { stage, subtitle: insideSub(stage), subtitleInside: true, H: h };
  }
  const w = vw, h = w / aspect;
  const spare = vh - h;
  if (spare >= h * SUB_NEED) {
    const stage = { x: 0, y: 0, w, h };
    return { stage, subtitle: { x: 0, y: h, w, h: spare }, subtitleInside: false, H: h };
  }
  const stage = { x: 0, y: spare / 2, w, h };
  return { stage, subtitle: insideSub(stage), subtitleInside: true, H: h };
}

function insideSub(s: Rect): Rect {
  return { x: s.x, y: s.y + s.h * 0.77, w: s.w, h: s.h * 0.2 };
}

export function applyRect(el: HTMLElement, r: Rect): void {
  el.style.left = `${r.x}px`;
  el.style.top = `${r.y}px`;
  el.style.width = `${r.w}px`;
  el.style.height = `${r.h}px`;
}
