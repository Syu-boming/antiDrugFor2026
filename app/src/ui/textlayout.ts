// 字幕斷行（v1.2 第 16.2 節）：每行不超過 16 字、最多兩行；太長的句子拆成數頁依字數分配時間。
// 沒有斷詞字典，以標點為優先斷點，其次取最接近中間的位置，並避免標點出現在行首。

export const MAX_PER_ROW = 16;
export const MAX_ROWS = 2;

const BREAK_AFTER = '，、。！？；：…—」』）,.!?;:';
const NO_ROW_START = '，、。！？；：…」』）,.!?;:';
const SENTENCE_END = '。！？!?';
const CLOSERS = '」』）';

export const chars = (s: string): string[] => Array.from(s);
export const charLen = (s: string): number => chars(s).length;

/** 把一段（≤ 2 行容量）的文字拆成最多兩行 */
export function splitRows(text: string, max = MAX_PER_ROW): string[] {
  const ch = chars(text);
  const n = ch.length;
  if (n <= max) return [text];
  let best = -1;
  let bestScore = Infinity;
  for (let i = Math.max(1, n - max); i <= Math.min(max, n - 1); i++) {
    if (NO_ROW_START.includes(ch[i])) continue; // 標點不放行首
    let score = Math.abs(i - n / 2);
    if (BREAK_AFTER.includes(ch[i - 1])) score -= 8; // 在標點後斷行最自然
    if (/[A-Za-z0-9]/.test(ch[i - 1]) && /[A-Za-z0-9]/.test(ch[i])) score += 30; // 不拆開英數
    if (score < bestScore) { bestScore = score; best = i; }
  }
  if (best < 0) best = Math.min(max, n - 1);
  return [ch.slice(0, best).join(''), ch.slice(best).join('')];
}

/** 依句號等切句（保留標點與後面的引號） */
function sentences(text: string): string[] {
  const ch = chars(text.trim());
  const out: string[] = [];
  let cur = '';
  for (let i = 0; i < ch.length; i++) {
    cur += ch[i];
    const next = ch[i + 1];
    if (SENTENCE_END.includes(ch[i]) && !(next && (SENTENCE_END.includes(next) || CLOSERS.includes(next)))) { out.push(cur); cur = ''; }
    else if (CLOSERS.includes(ch[i]) && i > 0 && SENTENCE_END.includes(ch[i - 1])) { out.push(cur); cur = ''; }
  }
  if (cur) out.push(cur);
  return out;
}

/** 超過一頁容量的句子，先在逗號處切，再不行就硬切 */
function splitLong(s: string, cap: number): string[] {
  const ch = chars(s);
  const out: string[] = [];
  let start = 0;
  while (ch.length - start > cap) {
    let cut = -1;
    for (let i = start + cap; i > start + cap / 2; i--) if (BREAK_AFTER.includes(ch[i - 1])) { cut = i; break; }
    if (cut < 0) cut = start + cap;
    out.push(ch.slice(start, cut).join(''));
    start = cut;
  }
  out.push(ch.slice(start).join(''));
  return out;
}

/** 把一句台詞排成字幕頁：回傳「頁 → 行」 */
export function layoutSubtitle(text: string, max = MAX_PER_ROW, rows = MAX_ROWS): string[][] {
  const clean = text.trim();
  if (charLen(clean) <= max) return [[clean]];
  const cap = max * rows;
  const pieces: string[] = [];
  for (const s of sentences(clean)) pieces.push(...(charLen(s) <= cap ? [s] : splitLong(s, cap)));
  const pages: string[][] = [];
  let page = '';
  const fits = (s: string): boolean => splitRows(s, max).every((r) => charLen(r) <= max) && charLen(s) <= cap;
  for (const p of pieces) {
    const cand = page + p;
    if (page && !fits(cand)) { pages.push(splitRows(page, max)); page = p; }
    else page = cand;
  }
  if (page) pages.push(splitRows(page, max));
  return pages;
}

/** 估計朗讀字數（不算標點與空白） */
export function spokenChars(text: string): number {
  return chars(text).filter((c) => !/[\s，、。！？；：…—「」『』（）,.!?;:"'()\-]/.test(c)).length;
}
