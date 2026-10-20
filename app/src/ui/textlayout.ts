// 字幕斷行（v1.2 第 16.2 節）：每行不超過 16 字、最多兩行，在詞語邊界斷行；太長的句子拆成數頁依字數分配時間。
// 斷點優先序：
//   1. cue 文字裡的手動換行 "\n"（強制換行；"\n\n" 強制換頁）。手動換行只影響排版，不算字、不影響配音比對。
//   2. 標點之後（句號、問號 > 逗號、頓號 > 刪節號、破折號）。
//   3. 詞語邊界：用內建詞表（WORDS，取自劇本 v03 常用詞）做最長匹配，不把詞拆開；疊字（叔叔、慢慢）不拆。
//   4. 虛詞前後的自然停頓（「的、了」之後；「和、可是、因為、就、也」之前）。
//   5. 兩行長度接近。
// 標點與「的、了、嗎」這類虛詞不放行首；開引號不放行尾；英數不拆開（例如 119）。
// 這個檔只能用 `import type`（tools 腳本會用 Node 直接執行它做測試）。

export const MAX_PER_ROW = 16;
export const MAX_ROWS = 2;

const BREAK_AFTER_STRONG = '。！？!?；;';
const BREAK_AFTER = '，、：:,…—」』）)';
const NO_ROW_START = '，、。！？；：…」』）,.!?;:)—';
const NO_ROW_END = '「『（(';
const SOFT_NO_ROW_START = '的了嗎呢吧啊喔呀囉啦哦嘛著過得地';
const PARTICLE_END = '的了著過嗎呢吧啊喔呀囉啦';
const SENTENCE_END = '。！？!?';
const CLOSERS = '」』）)';
const PUNCT = BREAK_AFTER_STRONG + BREAK_AFTER + '「『（( ';

/**
 * 常用詞表（兩字以上）：只需要涵蓋劇本裡會被斷行碰到的詞，不是完整斷詞字典。
 * 最長匹配時較長的詞優先，所以「操偶線」不會被拆成「操偶／線」。
 */
export const WORDS: string[] = (`
小燈鎮 小燈國小 紙燈節 燈籠紙 燈籠 主燈 骨架 竹子 竹篾 折折 阿樂 叔叔 阿樂叔叔 小晴 小宇 品安 葉護理師 護理師 林老師 老師
陳伯伯 伯伯 警衛 警察 醫生 家人 家長 同學 朋友 小朋友 大人 小孩 孩子 大家 我們 你們 他們 自己 別人 每個人 有人 一個人
操偶線 紙偶戲 紙偶 比喻 故事 毒品 喪屍 喪屍煙彈 煙彈 電子煙 頭腦 身體 不聽使喚 使喚 影響 受到 可能 一定 真的 變成
盒子 小盒子 包裝 外表 外觀 安全 危險 證明 閃亮 亮晶晶 漂亮 聞起來 看起來 香香 沒問題 沒關係 一下下 一次 而已
揮手 旁邊 跑到 怎麼 什麼 哪裡 為什麼 不見 昨天 今天 明天 晚上 早上 放學 上學 每年 秋天 前幾天 這幾天 一點 一下 一起
找大人 幫忙 需要 知道 不知道 告訴 拜託 答應 記得 記下來 想起來 想不起來 想一想 試試看 試一次 不要 不用 不能 不行 不會
可以 可是 因為 所以 如果 不過 還有 但是 或是 而且 就是 已經 還沒 馬上 先去 先找 先待 繼續 剛好 明明 到底 原來 其實
開車 上車 坐車 接送 駕駛 乘客 路人 路上 車子 轉彎 停下來 反應 判斷 變差 變慢 昏昏沉沉 受傷 危害 救護車 擔架 鑰匙 安全帶 後座
電話 打電話 手機 手錶 辦公室 警衛室 校門 校門口 正門口 門口 門裡 轉角 馬路 過馬路 廣場 騎樓 學校 椅子 工作台 桌子
站不穩 站穩 叫不醒 不舒服 休息 看醫生 吸毒 狀況 其他 身體狀況 舉手 線索 題目 正解 一題 這一題 完成 點亮 亮了 八盞
離開 拒絕 口訣 動作 保管 保密 秘密 做法 比較 指示 發生 請問 您好 好不好 好嗎 謝謝 對不起 沒事 小心 奇怪 慢慢 慢慢的
這裡 那裡 這個 那個 這些 那些 一條 一條一條 一盞 一團 細細 細細的 一頂 帽子 放大鏡 青蛙 風向 迷路 測試 布置 編的 準備
漂亮的 包裝裡面 裡面 外面 上面 下面 後面 前面 中間 樣子 時候 地方 東西 問題 事情 方法 機會 感覺 心情
`).trim().split(/\s+/).filter((w) => w.length >= 2);

const WORD_SET = new Set(WORDS);
const MAX_WORD = Math.max(...WORDS.map((w) => Array.from(w).length));
const CONJ_BEFORE = ['和', '跟', '或', '但', '可是', '因為', '所以', '如果', '不過', '還有', '就', '也', '都', '還', '才', '卻', '被', '把', '讓', '要', '會', '能', '在', '再', '先', '不'];

export const chars = (s: string): string[] => Array.from(s);
export const charLen = (s: string): number => chars(s).length;

const isAlnum = (c: string | undefined): boolean => !!c && /[A-Za-z0-9]/.test(c);
const isCJK = (c: string | undefined): boolean => !!c && /[㐀-鿿]/.test(c);

/** 最長匹配標出詞的範圍：inside[i]＝true 表示第 i 個字和第 i−1 個字屬於同一個詞（不能在 i 前面斷行） */
export function wordJoins(ch: string[]): boolean[] {
  const inside = new Array<boolean>(ch.length + 1).fill(false);
  let i = 0;
  while (i < ch.length) {
    let len = 1;
    for (let L = Math.min(MAX_WORD, ch.length - i); L >= 2; L--) {
      if (WORD_SET.has(ch.slice(i, i + L).join(''))) { len = L; break; }
    }
    for (let k = i + 1; k < i + len; k++) inside[k] = true;
    i += len;
  }
  // 疊字（叔叔、慢慢、香香）不拆
  for (let k = 1; k < ch.length; k++) if (isCJK(ch[k]) && ch[k] === ch[k - 1]) inside[k] = true;
  return inside;
}

/** 在第 i 個字前面斷行的代價（≥0，越小越好）；Infinity＝不可以在這裡斷 */
function breakCost(ch: string[], i: number, joins: boolean[]): number {
  const prev = ch[i - 1], cur = ch[i];
  if (NO_ROW_START.includes(cur) || NO_ROW_END.includes(prev)) return Infinity;
  if (isAlnum(prev) && isAlnum(cur)) return Infinity;
  if (BREAK_AFTER_STRONG.includes(prev) || (CLOSERS.includes(prev) && SENTENCE_END.includes(ch[i - 2] ?? ''))) return 0;
  if (BREAK_AFTER.includes(prev)) return 3;
  let cost = 12;
  if (joins[i]) cost += 45; // 拆開詞語
  if (SOFT_NO_ROW_START.includes(cur)) cost += 25;
  if (PARTICLE_END.includes(prev)) cost -= 3;
  const rest = ch.slice(i, i + 2).join('');
  if (CONJ_BEFORE.includes(cur) || CONJ_BEFORE.includes(rest)) cost -= 2.5;
  return Math.max(1, cost);
}

const ROW_PENALTY = 30;
const PAGE_PENALTY = 8;

/** 一行內部的代價：太短的行、行中夾著句尾又接下一句（混句） */
function rowCost(ch: string[], i: number, j: number, total: number): number {
  const L = j - i;
  let c = ROW_PENALTY;
  if (L < 4 && total > 4) c += (4 - L) * 4;
  for (let k = i; k < j - 1; k++) if (SENTENCE_END.includes(ch[k]) && !SENTENCE_END.includes(ch[k + 1]) && !CLOSERS.includes(ch[k + 1])) c += 20;
  return c;
}

/** 動態規劃排行：每行 ≤ max，總代價最小（行數、斷點品質、混句） */
function layoutRows(ch: string[], max: number): number[] {
  const n = ch.length;
  const joins = wordJoins(ch);
  const f = new Array<number>(n + 1).fill(Infinity);
  const from = new Array<number>(n + 1).fill(-1);
  f[0] = 0;
  for (let j = 1; j <= n; j++) {
    const bc = j < n ? breakCost(ch, j, joins) : 0;
    if (bc === Infinity) continue;
    for (let i = Math.max(0, j - max); i < j; i++) {
      if (f[i] === Infinity) continue;
      const c = f[i] + rowCost(ch, i, j, n) + bc;
      if (c < f[j]) { f[j] = c; from[j] = i; }
    }
  }
  if (f[n] === Infinity) { // 沒有合法斷點（極少見）：硬切
    const cuts: number[] = [];
    for (let k = max; k < n; k += max) cuts.push(k);
    return [...cuts, n];
  }
  const ends: number[] = [];
  for (let j = n; j > 0; j = from[j]) ends.unshift(j);
  return ends;
}

/** 頁斷點代價：句尾 0、逗號 6、句子中間 20 */
function pageBreakCost(ch: string[], end: number): number {
  const prev = ch[end - 1];
  if (SENTENCE_END.includes(prev) || (CLOSERS.includes(prev) && SENTENCE_END.includes(ch[end - 2] ?? ''))) return 0;
  if (BREAK_AFTER.includes(prev) || BREAK_AFTER_STRONG.includes(prev)) return 6;
  return 20;
}

/** 把一段（≤ 2 行容量）的文字拆成最多兩行 */
export function splitRows(text: string, max = MAX_PER_ROW): string[] {
  const ch = chars(text);
  if (ch.length <= max) return [text];
  const joins = wordJoins(ch);
  let best = -1, bestCost = Infinity;
  for (let i = Math.max(1, ch.length - max); i <= Math.min(max, ch.length - 1); i++) {
    const c = breakCost(ch, i, joins) + rowCost(ch, 0, i, ch.length) + rowCost(ch, i, ch.length, ch.length) + Math.abs(i - ch.length / 2) * 0.8;
    if (c < bestCost) { bestCost = c; best = i; }
  }
  if (best < 0) best = Math.min(max, ch.length - 1);
  return [ch.slice(0, best).join(''), ch.slice(best).join('')];
}

/** 自動排版（沒有手動換行的一段文字）→ 頁 → 行 */
function autoLayout(clean: string, max: number, rows: number): string[][] {
  const ch = chars(clean);
  if (ch.length <= max) return [[clean]];
  const ends = layoutRows(ch, max);
  const starts = [0, ...ends.slice(0, -1)];
  const R = ends.length;
  // 行分頁：每頁 1～rows 行，頁斷點盡量在句尾
  const g = new Array<number>(R + 1).fill(Infinity);
  const gp = new Array<number>(R + 1).fill(-1);
  g[0] = 0;
  for (let k = 1; k <= R; k++) {
    for (let m = 1; m <= rows && k - m >= 0; m++) {
      const c = g[k - m] + PAGE_PENALTY + (k < R ? pageBreakCost(ch, ends[k - 1]) : 0);
      if (c < g[k]) { g[k] = c; gp[k] = k - m; }
    }
  }
  const pages: string[][] = [];
  for (let k = R; k > 0; k = gp[k]) {
    const a = gp[k];
    const page: string[] = [];
    for (let r = a; r < k; r++) page.push(ch.slice(starts[r], ends[r]).join(''));
    pages.unshift(page);
  }
  // 兩行一頁時重新平衡這兩行（同一段文字，斷點可能有更均勻的選擇）
  return pages.map((p) => (p.length === 2 ? splitRows(p.join(''), max) : p));
}

/** 把一句台詞排成字幕頁：回傳「頁 → 行」。支援手動換行 "\n"（換行）與 "\n\n"（換頁）。 */
export function layoutSubtitle(text: string, max = MAX_PER_ROW, rows = MAX_ROWS): string[][] {
  const src = text.replace(/\r/g, '').trim();
  if (!src.includes('\n')) return autoLayout(src, max, rows);
  const pages: string[][] = [];
  for (const block of src.split(/\n{2,}/)) {
    // 每個手動行如果超過一行容量，再自動拆開
    const rowList: string[] = [];
    for (const line of block.split('\n').map((l) => l.trim()).filter(Boolean)) {
      if (charLen(line) <= max) rowList.push(line);
      else for (const pg of autoLayout(line, max, rows)) rowList.push(...pg);
    }
    for (let i = 0; i < rowList.length; i += rows) pages.push(rowList.slice(i, i + rows));
  }
  return pages;
}

/** 去掉排版用的手動換行（配音比對、字數統計用） */
export const plainText = (text: string): string => text.replace(/\s*\n\s*/g, '');

/** 估計朗讀字數（不算標點與空白） */
export function spokenChars(text: string): number {
  return chars(text).filter((c) => !/[\s，、。！？；：…—「」『』（）,.!?;:"'()\-]/.test(c)).length;
}

/** 檢查用：回傳一句台詞排版後拆開的詞（給測試與驗收報告） */
export function brokenWords(text: string, max = MAX_PER_ROW, rows = MAX_ROWS): string[] {
  const out: string[] = [];
  for (const page of layoutSubtitle(text, max, rows)) {
    for (let r = 0; r + 1 < page.length; r++) {
      const a = chars(page[r]), b = chars(page[r + 1]);
      const joined = [...a, ...b];
      const joins = wordJoins(joined);
      if (joins[a.length]) out.push(`${a.slice(-2).join('')}／${b.slice(0, 2).join('')}`);
    }
  }
  return out;
}

export const PUNCTUATION = PUNCT;
