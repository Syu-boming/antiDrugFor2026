// 把 cue 資料展開成時間軸：每句台詞的開始／結束、字幕分頁、動畫起訖、cue 總長。
// 有正式音檔就用音檔長度；沒有就進「暫代模式」，依字數估計長度。
// G5 全劇：每個 cue 的景（set）與換景亮度漸變（enterFade）、段落名冊（說話者 → 角色）、壓縮級別（略過的 cue 與台詞、短版）。
import type { Cue, CueAnimation, CueFile, CueLine, QuizData, TimeRef } from '../types/cue';
import { layoutSubtitle, spokenChars, charLen, plainText } from '../ui/textlayout';
import { rosterFor } from './show';

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
export interface ResolvedMusic { id: string; at: number; loop: boolean; fade: number; gain: number; offset: number }

export interface CueTimeline {
  cue: Cue;
  index: number;
  duration: number;
  lines: ResolvedLine[];
  anims: ResolvedAnim[];
  sfx: ResolvedSfx[];
  /** 段落內的配樂切換 */
  music: ResolvedMusic[];
  /** 這段有任何一句找不到音檔 */
  placeholder: boolean;
  quiz: QuizData | null;
  /** 上一穩定節點的索引（-1＝沒有） */
  prevStableIndex: number;
  /** 下一節點的索引（-1＝最後）；壓縮略過的 cue 會被跳過 */
  nextIndex: number;
  /** 這個 cue 開始時的景（cue.set ＞ 檔案層級 set ＞ workshop） */
  set: string;
  /** 這個 cue 結束時的景（最後一個 set.swap 動畫；沒有就同 set） */
  endSet: string;
  /** 開始時從暗漸亮的秒數（換景或 setFade；0＝不漸變） */
  enterFade: number;
  /** 目前壓縮級別下這個 cue 被略過（只能從章節選單直接跳進來） */
  skipped: boolean;
  /** 目前壓縮級別下沒播的台詞編號 */
  droppedLines: string[];
}

export interface TimelineOptions {
  /** 壓縮級別 0／1／2（時長估算_v03.md 第 5 節）：1＝略過 compression 1 的 cue 與 skippableWhenBehind 的台詞、套 level1；2＝再套 level2 短版 */
  compression?: 0 | 1 | 2;
}

/** 換景亮度漸變：預設與下限（秒；v1.2 第 17.3 節「切場亮度漸變」） */
export const SET_FADE = { default: 0.8, min: 0.6 };

/** 時間參數預設值（暫代模式的估計依劇本「字數 ÷ 4 字／秒＋每句 0.5 秒」） */
export const TIMING = { voStart: 0.5, gap: 0.45, tail: 0.9, charsPerSec: 4, minLine: 1.2, lampTail: 1.8 };

/** 各動畫的預設長度（秒） */
const ANIM_DEFAULT_DURATION: Record<string, number> = {
  'title.fadeOut': 1.0, 'title.fadeIn': 0.9, 'curtain.open': 2.2, 'curtain.close': 2.2,
  'quiz.show': 0.6, 'quiz.hide': 0.5, 'quiz.reveal': 0.45, 'lamp.light': 1.2,
  'light.dim': 1.0, 'light.restore': 1.0, 'camera.move': 2.5, 'camera.cut': 0,
  'set.popup': 3.0, 'set.fold': 2.4, 'fx.desat': 3.0, 'fx.spot': 2.0,
  'strings.drop': 3.0, 'strings.tension': 0.5, 'strings.loosen': 3.0, 'strings.fade': 3.0, 'strings.detach': 2.0,
  'puppet.popup': 1.1, 'puppet.enter': 2.0, 'puppet.exit': 2.0, 'puppet.sit': 1.0, 'puppet.waveTry': 3.4, 'puppet.kneeTug': 3.2,
  'puppet.reach': 0.8, 'puppet.wave': 2.0, 'puppet.chest': 0.8, 'puppet.grab': 0.8, 'puppet.lean': 0.8, 'puppet.move': 1.5,
  'puppet.tilt': 0.8, 'puppet.pose': 0.24, 'puppet.face': 0, 'puppet.blink': 0,
  'set.swap': 0, 'fade.out': 0.8, 'fade.in': 0.8,
};

export function estimateLineDuration(text: string): number {
  return Math.max(TIMING.minLine, spokenChars(text) / TIMING.charsPerSec);
}

export const audioIdOf = (line: CueLine): string => line.audioId ?? `vo_${line.id}`;

/** 依字數比例分配字幕頁的時間 */
function paginate(text: string, start: number, end: number): SubtitlePage[] {
  const pages = layoutSubtitle(text);
  const weights = pages.map((p) => Math.max(1, charLen(plainText(p.join('')))));
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
export function buildTimelines(file: CueFile, durationOf: (audioId: string) => number | undefined, opts: TimelineOptions = {}): CueTimeline[] {
  const cues = file.cues;
  const level = opts.compression ?? 0;
  const index = new Map(cues.map((c, i) => [c.id, i]));
  const rosterCache = new Map<string, Map<string, string>>();
  const speakerMap = (cue: Cue): Map<string, string> => {
    const key = cue.segment ?? '';
    let m = rosterCache.get(key);
    if (!m) { m = new Map(Object.entries(rosterFor(file, cue)).map(([id, c]) => [c.name, id])); rosterCache.set(key, m); }
    return m;
  };
  let lastQuiz: QuizData | null = null;
  // 壓縮：1 級略過 compression 1 的 cue（2 級的 cue 改短版，不略過）
  const skippedCue = (c: Cue): boolean => level >= 1 && c.compression === 1;

  const out0 = cues.map((cue0, i) => {
    // 0. 壓縮的替代版本（1 級：略過可略台詞＋level1；2 級：再套 level2）
    let cue = cue0;
    const keep = new Set<string>(cue.lines.map((l) => l.id));
    if (level >= 1) {
      for (const l of cue.lines) if (l.skippableWhenBehind) keep.delete(l.id);
      if (cue.level1) { cue = applyVariant(cue, cue.level1); if (cue.level1?.lines) for (const id of [...keep]) if (!cue0.level1!.lines!.includes(id)) keep.delete(id); }
    }
    if (level >= 2 && cue0.compression === 2 && cue0.level2) {
      cue = applyVariant(cue, cue0.level2);
      if (cue0.level2.lines) for (const id of [...keep]) if (!cue0.level2.lines.includes(id)) keep.delete(id);
    }
    const roster = speakerMap(cue0);
    // 1. 台詞依序排上時間軸（壓縮略過的台詞收成 0 秒：不播、不上字幕，錨在它上面的動作照樣解析）
    const lines = new Map<string, ResolvedLine>();
    const resolved: ResolvedLine[] = [];
    const dropped: string[] = [];
    let cursor = cue.voStart ?? TIMING.voStart;
    for (const line of cue.lines) {
      const audioId = audioIdOf(line);
      const real = durationOf(audioId);
      const on = keep.has(line.id);
      const duration = on ? real ?? estimateLineDuration(line.text) : 0;
      const s = line.start !== undefined ? (resolveRef(line.start, lines, null, line.id) ?? cursor) : cursor;
      const r: ResolvedLine = {
        line, audioId, actorId: roster.get(line.speaker) ?? null,
        start: s, end: s + duration, duration, placeholder: on && real === undefined, pages: [],
      };
      lines.set(line.id, r);
      if (!on) { dropped.push(line.id); continue; }
      r.pages = paginate(line.text, r.start, r.end);
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
    const music: ResolvedMusic[] = (cue.music ?? []).map((e) => ({
      id: e.id, at: Math.max(0, resolveRef(e.at, lines, duration, `${cue.id}/music`) ?? 0), loop: e.loop ?? true, fade: e.fade ?? 1.5, gain: e.gain ?? 1, offset: e.offset ?? 0,
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

    // 6. 景：cue.set ＞ 檔案層級 ＞ workshop；結束時的景＝最後一個 set.swap
    const set = cue0.set ?? file.set ?? 'workshop';
    const swaps = out.filter((a) => a.name === 'set.swap' && typeof a.params.set === 'string');
    const endSet = swaps.length ? String(swaps[swaps.length - 1].params.set) : set;

    return {
      cue, index: i, duration, lines: resolved, anims: out, sfx, music,
      placeholder: resolved.some((l) => l.placeholder), quiz, prevStableIndex, nextIndex,
      set, endSet, enterFade: 0, skipped: skippedCue(cue0), droppedLines: dropped,
    };
  });

  // 7. 壓縮略過的 cue：下一節點與上一穩定節點都跳過它們（直接從章節選單跳進去仍可播）
  const live = (j: number, dir: 'next' | 'prev'): number => {
    const seen = new Set<number>();
    while (j >= 0 && out0[j].skipped && !seen.has(j)) { seen.add(j); j = dir === 'next' ? out0[j].nextIndex : out0[j].prevStableIndex; }
    return j;
  };
  if (level >= 1) for (const t of out0) { t.nextIndex = live(t.nextIndex, 'next'); t.prevStableIndex = live(t.prevStableIndex, 'prev'); }

  // 8. 換景亮度漸變：跟流程上前一個 cue（next 指向自己的那個）結束時的景不同、而且開始時布幕是開的 → 從暗漸亮
  for (const t of out0) {
    const c = t.cue;
    const pred = out0.find((p) => p.nextIndex === t.index && !p.skipped) ?? out0[t.index - 1];
    const curtainOpen = (c.initialState.stage?.curtain ?? (c.kind === 'title' ? 'closed' : 'open')) === 'open';
    const changed = !!pred && pred.endSet !== t.set;
    if (curtainOpen && (changed || c.setFade !== undefined)) t.enterFade = Math.max(SET_FADE.min, c.setFade ?? SET_FADE.default);
  }
  return out0;
}

/** 套用壓縮替代版本（只換有寫的欄位） */
function applyVariant(cue: Cue, v: NonNullable<Cue['level1']>): Cue {
  return {
    ...cue,
    animation: v.animation ?? cue.animation,
    minDuration: v.minDuration ?? cue.minDuration,
    voStart: v.voStart ?? cue.voStart,
    tail: v.tail ?? cue.tail,
  };
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
