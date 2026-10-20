// 把 cue 資料展開成時間軸：每句台詞的開始／結束、字幕分頁、動畫起訖、cue 總長。
// 有正式音檔就用音檔長度；沒有就進「暫代模式」，依字數估計長度。
import type { Cue, CueAnimation, CueFile, CueLine, QuizData, TimeRef } from '../types/cue';
import { layoutSubtitle, spokenChars, charLen } from '../ui/textlayout';

export interface SubtitlePage { start: number; end: number; rows: string[] }

export interface ResolvedLine {
  line: CueLine;
  audioId: string;
  /** 說話者在舞台上的角色 id（旁白等沒有紙偶的為 null） */
  actorId: string | null;
  start: number;
  end: number;
  duration: number;
  placeholder: boolean;
  pages: SubtitlePage[];
}

export interface ResolvedAnim {
  name: string;
  target?: string;
  start: number;
  duration: number;
  end: number;
  ease?: string;
  params: Record<string, unknown>;
}

export interface ResolvedSfx { id: string; at: number; gain: number }

export interface CueTimeline {
  cue: Cue;
  index: number;
  duration: number;
  lines: ResolvedLine[];
  anims: ResolvedAnim[];
  sfx: ResolvedSfx[];
  /** 這段有任何一句找不到音檔 */
  placeholder: boolean;
  quiz: QuizData | null;
  /** 上一穩定節點的索引（-1＝沒有） */
  prevStableIndex: number;
  /** 下一節點的索引（-1＝最後） */
  nextIndex: number;
}

/** 時間參數預設值（暫代模式的估計依劇本「字數 ÷ 4 字／秒＋每句 0.5 秒」） */
export const TIMING = { voStart: 0.5, gap: 0.45, tail: 0.9, charsPerSec: 4, minLine: 1.2, lampTail: 1.8 };

/** 各動畫的預設長度（秒） */
const ANIM_DEFAULT_DURATION: Record<string, number> = {
  'title.fadeOut': 1.0, 'title.fadeIn': 0.9, 'curtain.open': 2.0, 'curtain.close': 2.0,
  'quiz.show': 0.6, 'quiz.hide': 0.5, 'quiz.reveal': 0.45, 'lamp.light': 1.2,
  'light.dim': 1.0, 'light.restore': 1.0, 'camera.move': 2.5, 'camera.cut': 0,
};

export function estimateLineDuration(text: string): number {
  return Math.max(TIMING.minLine, spokenChars(text) / TIMING.charsPerSec);
}

export const audioIdOf = (line: CueLine): string => line.audioId ?? `vo_${line.id}`;

/** 依字數比例分配字幕頁的時間 */
function paginate(text: string, start: number, end: number): SubtitlePage[] {
  const pages = layoutSubtitle(text);
  const weights = pages.map((p) => Math.max(1, charLen(p.join(''))));
  const total = weights.reduce((a, b) => a + b, 0);
  let t = start;
  return pages.map((rows, i) => {
    const d = ((end - start) * weights[i]) / total;
    const page = { start: t, end: t + d, rows };
    t += d;
    return page;
  });
}

const REF_RE = /^([a-z0-9_]+?)(\.end|\.start)?([+-]\d+(?:\.\d+)?)?$/;

/** 解析時間參照；回傳 null 表示要等 cue 總長算出來（"end" 參照） */
function resolveRef(ref: TimeRef | undefined, lines: Map<string, ResolvedLine>, duration: number | null, where: string): number | null {
  if (ref === undefined) return 0;
  if (typeof ref === 'number') return ref;
  const m = REF_RE.exec(ref.trim());
  if (!m) { console.warn(`[timeline] ${where} 無法解析時間參照 ${ref}`); return 0; }
  const off = m[3] ? Number(m[3]) : 0;
  if (m[1] === 'end') return duration === null ? null : duration + off;
  const l = lines.get(m[1]);
  if (!l) { console.warn(`[timeline] ${where} 參照了不存在的台詞 ${m[1]}`); return off; }
  return (m[2] === '.end' ? l.end : l.start) + off;
}

/**
 * 建立整份 cue 檔的時間軸。
 * @param durationOf 依音檔 id 查實際長度（秒）；找不到回傳 undefined → 暫代模式
 */
export function buildTimelines(file: CueFile, durationOf: (audioId: string) => number | undefined): CueTimeline[] {
  const cues = file.cues;
  const index = new Map(cues.map((c, i) => [c.id, i]));
  const roster = new Map(Object.entries(file.characters ?? {}).map(([id, c]) => [c.name, id]));
  let lastQuiz: QuizData | null = null;

  return cues.map((cue, i) => {
    // 1. 台詞依序排上時間軸
    const lines = new Map<string, ResolvedLine>();
    const resolved: ResolvedLine[] = [];
    let cursor = cue.voStart ?? TIMING.voStart;
    for (const line of cue.lines) {
      const audioId = audioIdOf(line);
      const real = durationOf(audioId);
      const duration = real ?? estimateLineDuration(line.text);
      const s = line.start !== undefined ? (resolveRef(line.start, lines, null, line.id) ?? cursor) : cursor;
      const r: ResolvedLine = {
        line, audioId, actorId: roster.get(line.speaker) ?? null,
        start: s, end: s + duration, duration, placeholder: real === undefined, pages: [],
      };
      r.pages = paginate(line.text, r.start, r.end);
      lines.set(line.id, r);
      resolved.push(r);
      cursor = r.end + TIMING.gap;
    }

    // 2. 動畫（含依種類自動補上的預設動畫）
    const anims: CueAnimation[] = [...cue.animation];
    const has = (name: string): boolean => anims.some((a) => a.name === name);
    if (cue.kind === 'quiz' && !has('quiz.show')) anims.unshift({ name: 'quiz.show', start: 0.2 });
    if (cue.kind === 'reveal' && !has('quiz.reveal')) anims.unshift({ name: 'quiz.reveal', start: 0.3 });
    if (cue.lamp && !has('lamp.light')) anims.push({ name: 'lamp.light', start: 'end-1.5', params: { index: cue.lamp } });

    const pending: { a: CueAnimation; dur: number }[] = [];
    const out: ResolvedAnim[] = [];
    for (const a of anims) {
      const dur = a.duration ?? ANIM_DEFAULT_DURATION[a.name] ?? 1;
      const s = resolveRef(a.start, lines, null, `${cue.id}/${a.name}`);
      if (s === null) { pending.push({ a, dur }); continue; }
      out.push({ name: a.name, target: a.target, start: s, duration: dur, end: s + dur, ease: a.ease, params: a.params ?? {} });
    }

    // 3. cue 總長＝最後一句＋停留、所有動畫結束、最短長度三者取大
    const lastLineEnd = resolved.length ? Math.max(...resolved.map((l) => l.end)) : 0;
    let duration = Math.max(
      cue.minDuration ?? 0,
      resolved.length ? lastLineEnd + (cue.tail ?? TIMING.tail) : 0,
      ...out.map((a) => a.end),
    );
    if (cue.lamp) duration = Math.max(duration, lastLineEnd + TIMING.lampTail);
    for (const { a, dur } of pending) {
      const s = Math.max(0, resolveRef(a.start, lines, duration, `${cue.id}/${a.name}`) ?? 0);
      out.push({ name: a.name, target: a.target, start: s, duration: dur, end: s + dur, ease: a.ease, params: a.params ?? {} });
      duration = Math.max(duration, s + dur);
    }
    out.sort((x, y) => x.start - y.start);

    const sfx: ResolvedSfx[] = (cue.sfx ?? []).map((e) => ({
      id: e.id, at: Math.max(0, resolveRef(e.at, lines, duration, `${cue.id}/sfx`) ?? 0), gain: e.gain ?? 1,
    }));

    // 4. 題目資料：reveal 沒寫就沿用前一個 quiz
    let quiz: QuizData | null = cue.quiz ?? null;
    if (cue.kind === 'quiz' && quiz) lastQuiz = quiz;
    // 題卡還在畫面上的 cue（例如揭答後的閉幕要讓題卡淡出）也沿用前一題
    if (!quiz && (cue.kind === 'reveal' || cue.initialState.stage?.quiz)) quiz = lastQuiz;

    // 5. 上一穩定節點與下一節點：沒寫時自動推算（跳過會自動接續的節點）
    let prevStableIndex = -1;
    if (typeof cue.prevStable === 'string') prevStableIndex = index.get(cue.prevStable) ?? -1;
    else if (cue.prevStable === undefined) {
      for (let j = i - 1; j >= 0; j--) if (!cues[j].autoAdvance) { prevStableIndex = j; break; }
    }
    let nextIndex = -1;
    if (typeof cue.next === 'string') nextIndex = index.get(cue.next) ?? -1;
    else if (cue.next === undefined && i + 1 < cues.length) nextIndex = i + 1;

    return {
      cue, index: i, duration, lines: resolved, anims: out, sfx,
      placeholder: resolved.some((l) => l.placeholder), quiz, prevStableIndex, nextIndex,
    };
  });
}

/** 某時間點正在顯示的字幕頁 */
export function subtitleAt(tl: CueTimeline, t: number): { line: ResolvedLine; page: SubtitlePage } | null {
  for (const l of tl.lines) {
    if (t < l.start || t >= l.end) continue;
    for (const p of l.pages) if (t >= p.start && t < p.end) return { line: l, page: p };
  }
  return null;
}

/** 某時間點是否有人在說話（給配樂避讓與嘴型用） */
export function speakingAt(tl: CueTimeline, t: number): ResolvedLine | null {
  for (const l of tl.lines) if (t >= l.start && t < l.end) return l;
  return null;
}
