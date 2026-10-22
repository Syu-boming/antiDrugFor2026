// cue 檔驗證。執行期（準備畫面顯示錯誤）與打包期（tools/pack.mjs 直接 import 這個 .ts）共用。
// 注意：這個檔只能用 `import type`，Node 才能直接剝除型別執行。
import type { CueKind } from '../types/cue';

export const CUE_ID_RE = /^a\d_c\d{3}$/;
export const LINE_ID_RE = /^a\d_c\d{3}_\d{2}$/;
export const CUE_KINDS: readonly CueKind[] = ['title', 'curtain', 'scene', 'quiz', 'reveal', 'wait', 'lamp'];
const REQUIRED_KEYS = ['id', 'sceneId', 'kind', 'initialState', 'animation', 'audioId', 'lines', 'next', 'prevStable',
  'skippable', 'compression', 'fx', 'teacherNote', 'checkpoint'];
/** 已知動畫名稱（與 engine/world.ts 的 STAGE_ANIMS、ACTOR_ANIMS 相同；這裡不能 import 值，所以另列一份） */
export const KNOWN_ANIMS = ['title.fadeOut', 'title.fadeIn', 'curtain.open', 'curtain.close', 'set.popup', 'set.fold', 'light.dim', 'light.restore',
  'fx.desat', 'fx.spot', 'camera.move', 'camera.cut', 'quiz.show', 'quiz.hide', 'quiz.reveal', 'lamp.light',
  'strings.drop', 'strings.tension', 'strings.loosen', 'strings.fade', 'strings.detach',
  'puppet.popup', 'puppet.enter', 'puppet.exit', 'puppet.sit', 'puppet.waveTry', 'puppet.kneeTug', 'puppet.reach', 'puppet.wave',
  'puppet.chest', 'puppet.grab', 'puppet.lean', 'puppet.move', 'puppet.tilt', 'puppet.pose', 'puppet.face', 'puppet.blink',
  // G5 全劇：換景、亮度漸變
  'set.swap', 'fade.out', 'fade.in',
  // G5 修正第 1 輪：點頭
  'puppet.nod'];
/** 程式角色的動畫前綴（<程式名>.<動作>，例如 zhezhe.fold）：由程式角色自己解讀，驗證時不當未知動畫 */
export const PROGRAM_ANIM_PREFIXES = ['zhezhe.'];
/** 換景亮度漸變的下限（秒；v1.2 第 17.3 節） */
export const MIN_SET_FADE = 0.6;
const knownAnim = (name: string): boolean => KNOWN_ANIMS.includes(name) || PROGRAM_ANIM_PREFIXES.some((p) => name.startsWith(p));

export interface ValidationResult { ok: boolean; errors: string[]; warnings: string[] }

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);
const isTimeRef = (v: unknown): boolean => typeof v === 'number' || typeof v === 'string';

export interface ValidateOptions {
  /** 其他段落檔裡的 cue 編號（全劇段落檔單獨驗證時，next／prevStable 可以指向別的段落） */
  externalIds?: Set<string>;
}

export function validateCueFile(data: unknown, opts: ValidateOptions = {}): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const done = (): ValidationResult => ({ ok: errors.length === 0, errors, warnings });
  if (!isObj(data)) { errors.push('cue 檔不是 JSON 物件'); return done(); }
  if (data.format !== 'antidrug-cues/1') errors.push(`format 應為 "antidrug-cues/1"（目前是 ${JSON.stringify(data.format)}）`);
  if (typeof data.id !== 'string' || !data.id) errors.push('缺少 cue 檔 id');
  const cues = data.cues;
  if (!Array.isArray(cues) || cues.length === 0) { errors.push('cues 必須是非空陣列'); return done(); }

  const ids = new Map<string, number>();
  const lineIds = new Set<string>();
  cues.forEach((c, i) => {
    const where = `第 ${i + 1} 個 cue`;
    if (!isObj(c)) { errors.push(`${where} 不是物件`); return; }
    const id = String(c.id ?? '');
    const at = `${where}（${id || '無 id'}）`;
    for (const k of REQUIRED_KEYS) if (!(k in c)) errors.push(`${at} 缺少欄位 ${k}`);
    if (!CUE_ID_RE.test(id)) errors.push(`${at} 編號格式應為 a{幕}_c{三位數}`);
    if (ids.has(id)) errors.push(`${at} 編號重複`);
    ids.set(id, i);
    if (typeof c.sceneId !== 'string' || !c.sceneId) errors.push(`${at} sceneId 必須是非空字串`);
    if (!CUE_KINDS.includes(c.kind as CueKind)) errors.push(`${at} 種類 ${JSON.stringify(c.kind)} 不在 ${CUE_KINDS.join('／')}`);
    if (!isObj(c.initialState)) errors.push(`${at} initialState 必須是物件`);
    if (!Array.isArray(c.animation)) errors.push(`${at} animation 必須是陣列`);
    else c.animation.forEach((a, j) => {
      if (!isObj(a) || typeof a.name !== 'string' || !isTimeRef(a.start)) errors.push(`${at} animation[${j}] 需要 name 與 start`);
      else if (a.duration !== undefined && (typeof a.duration !== 'number' || a.duration < 0)) errors.push(`${at} animation[${j}] duration 必須是非負數`);
      else if (!knownAnim(a.name)) warnings.push(`${at} animation[${j}] 未知的動畫名稱 ${a.name}（會被忽略）`);
      else if ((a.name === 'fade.out' || a.name === 'fade.in') && typeof a.duration === 'number' && a.duration < MIN_SET_FADE) warnings.push(`${at} animation[${j}] ${a.name} 短於 ${MIN_SET_FADE} 秒（光敏：亮度漸變至少 ${MIN_SET_FADE} 秒）`);
      else if (a.name === 'set.swap' && (!isObj(a.params) || typeof a.params.set !== 'string')) errors.push(`${at} animation[${j}] set.swap 需要 params.set（景名）`);
      else if (a.target !== undefined && typeof a.target === 'string' && isObj(data.characters) && !(a.target in (data.characters as Obj))) warnings.push(`${at} animation[${j}] 的對象 ${a.target} 不在角色名冊`);
    });
    if (c.music !== undefined) {
      if (!Array.isArray(c.music)) errors.push(`${at} music 必須是陣列`);
      else c.music.forEach((m, j) => { if (!isObj(m) || typeof m.id !== 'string' || !isTimeRef(m.at)) errors.push(`${at} music[${j}] 需要 id 與 at`); });
    }
    if (c.audioId !== null && typeof c.audioId !== 'string') errors.push(`${at} audioId 必須是字串或 null`);
    if (c.musicDuck !== undefined && (typeof c.musicDuck !== 'number' || !Number.isFinite(c.musicDuck) || c.musicDuck < 0 || c.musicDuck > 1)) errors.push(`${at} musicDuck 必須是 0–1 的數字（台詞時的配樂避讓增益）`);
    if (!Array.isArray(c.lines)) errors.push(`${at} lines 必須是陣列`);
    else c.lines.forEach((l, j) => {
      if (!isObj(l)) { errors.push(`${at} lines[${j}] 不是物件`); return; }
      const lid = String(l.id ?? '');
      if (!LINE_ID_RE.test(lid)) errors.push(`${at} 台詞 ${lid || j} 編號格式應為 a{幕}_c{三位數}_{兩位數}`);
      else if (!lid.startsWith(id + '_')) errors.push(`${at} 台詞 ${lid} 不屬於這個 cue`);
      if (lineIds.has(lid)) errors.push(`${at} 台詞 ${lid} 編號重複`);
      lineIds.add(lid);
      if (typeof l.speaker !== 'string' || !l.speaker) errors.push(`${at} 台詞 ${lid} 缺少說話者`);
      if (typeof l.text !== 'string' || !l.text) errors.push(`${at} 台詞 ${lid} 缺少字幕文字`);
      if (l.start !== undefined && !isTimeRef(l.start)) errors.push(`${at} 台詞 ${lid} start 格式錯誤`);
    });
    if (c.next !== null && typeof c.next !== 'string') errors.push(`${at} next 必須是字串或 null`);
    if (c.prevStable !== null && typeof c.prevStable !== 'string') errors.push(`${at} prevStable 必須是字串或 null`);
    if (typeof c.skippable !== 'boolean') errors.push(`${at} skippable 必須是 true／false`);
    if (![0, 1, 2].includes(c.compression as number)) errors.push(`${at} compression 必須是 0／1／2`);
    if (!Array.isArray(c.fx) || c.fx.some((f) => typeof f !== 'string' || !/^FX\d+$/.test(f))) errors.push(`${at} fx 必須是 "FX數字" 陣列`);
    if (typeof c.teacherNote !== 'string') errors.push(`${at} teacherNote 必須是字串`);
    if (c.checkpoint !== null && !(isObj(c.checkpoint) && typeof c.checkpoint.label === 'string' && typeof c.checkpoint.atMinute === 'number')) {
      errors.push(`${at} checkpoint 必須是 null 或 { label, atMinute }`);
    }
    if (c.kind === 'quiz') {
      const q = c.quiz;
      if (!isObj(q)) errors.push(`${at} 出題 cue 需要 quiz 資料`);
      else {
        if (!Array.isArray(q.options) || q.options.length !== 3) errors.push(`${at} quiz.options 必須剛好 3 個選項`);
        if (![1, 2, 3].includes(q.answer as number)) errors.push(`${at} quiz.answer 必須是 1／2／3`);
        if (typeof q.question !== 'string' || !q.question) errors.push(`${at} quiz.question 缺少題目`);
        if (typeof q.number !== 'number' || q.number < 1 || q.number > 8) errors.push(`${at} quiz.number 必須是 1–8`);
      }
    }
    if (c.lamp !== undefined && !(Number.isInteger(c.lamp) && (c.lamp as number) >= 1 && (c.lamp as number) <= 8)) errors.push(`${at} lamp 必須是 1–8`);
    // G5 全劇欄位
    if (c.set !== undefined && (typeof c.set !== 'string' || !c.set)) errors.push(`${at} set 必須是景名字串`);
    if (c.setFade !== undefined && (typeof c.setFade !== 'number' || c.setFade < MIN_SET_FADE)) errors.push(`${at} setFade 必須是 ≥ ${MIN_SET_FADE} 的秒數（光敏：亮度漸變）`);
    if (isObj(c.checkpoint) && c.checkpoint.escalate !== undefined) {
      const e = c.checkpoint.escalate;
      if (!isObj(e) || typeof e.behindSec !== 'number' || ![1, 2].includes(e.level as number)) errors.push(`${at} checkpoint.escalate 必須是 { behindSec, level: 1|2 }`);
    }
    for (const k of ['level1', 'level2'] as const) {
      const v = c[k];
      if (v === undefined) continue;
      if (!isObj(v)) { errors.push(`${at} ${k} 必須是物件`); continue; }
      const own = new Set(Array.isArray(c.lines) ? (c.lines as Obj[]).map((l) => String(l.id)) : []);
      if (v.lines !== undefined && (!Array.isArray(v.lines) || v.lines.some((x) => typeof x !== 'string' || !own.has(x)))) errors.push(`${at} ${k}.lines 必須是這個 cue 的台詞編號陣列`);
      if (v.animation !== undefined && !Array.isArray(v.animation)) errors.push(`${at} ${k}.animation 必須是陣列`);
      else if (Array.isArray(v.animation)) v.animation.forEach((a, j) => { if (!isObj(a) || typeof a.name !== 'string' || !isTimeRef(a.start)) errors.push(`${at} ${k}.animation[${j}] 需要 name 與 start`); else if (!knownAnim(a.name)) warnings.push(`${at} ${k}.animation[${j}] 未知的動畫名稱 ${a.name}`); });
      for (const n of ['minDuration', 'voStart', 'tail']) if (v[n] !== undefined && (typeof v[n] !== 'number' || (v[n] as number) < 0)) errors.push(`${at} ${k}.${n} 必須是非負數`);
    }
  });

  // 參照檢查（下一節點、上一穩定節點、揭答前要有出題）
  let lastQuiz = -1;
  cues.forEach((c, i) => {
    if (!isObj(c)) return;
    const at = `cue ${String(c.id)}`;
    const ext = (x: string): boolean => !!opts.externalIds?.has(x);
    if (typeof c.next === 'string' && !ids.has(c.next) && !ext(c.next)) errors.push(`${at} 的 next 指向不存在的 ${c.next}`);
    if (typeof c.prevStable === 'string') {
      const j = ids.get(c.prevStable);
      if (j === undefined) { if (!ext(c.prevStable)) errors.push(`${at} 的 prevStable 指向不存在的 ${c.prevStable}`); }
      else if (j >= i) warnings.push(`${at} 的 prevStable（${c.prevStable}）不在它之前`);
      else if (isObj(cues[j]) && (cues[j] as Obj).autoAdvance === true) warnings.push(`${at} 的 prevStable 是會自動接續的節點，不是穩定節點`);
    }
    if (c.kind === 'quiz') lastQuiz = i;
    if (c.kind === 'reveal' && !isObj(c.quiz) && lastQuiz < 0) errors.push(`${at} 是揭答，但前面沒有出題`);
    if (c.autoAdvance === true && c.next === null) warnings.push(`${at} 設了 autoAdvance 但沒有下一節點`);
  });
  if (!opts.externalIds && isObj(cues[0]) && (cues[0] as Obj).kind !== 'title') warnings.push('第一個 cue 通常應是 title（署名卡待機）');
  return done();
}
