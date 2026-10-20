// cue 檔驗證。執行期（準備畫面顯示錯誤）與打包期（tools/pack.mjs 直接 import 這個 .ts）共用。
// 注意：這個檔只能用 `import type`，Node 才能直接剝除型別執行。
import type { CueKind } from '../types/cue';

export const CUE_ID_RE = /^a\d_c\d{3}$/;
export const LINE_ID_RE = /^a\d_c\d{3}_\d{2}$/;
export const CUE_KINDS: readonly CueKind[] = ['title', 'curtain', 'scene', 'quiz', 'reveal', 'wait', 'lamp'];
const REQUIRED_KEYS = ['id', 'sceneId', 'kind', 'initialState', 'animation', 'audioId', 'lines', 'next', 'prevStable',
  'skippable', 'compression', 'fx', 'teacherNote', 'checkpoint'];

export interface ValidationResult { ok: boolean; errors: string[]; warnings: string[] }

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);
const isTimeRef = (v: unknown): boolean => typeof v === 'number' || typeof v === 'string';

export function validateCueFile(data: unknown): ValidationResult {
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
    });
    if (c.audioId !== null && typeof c.audioId !== 'string') errors.push(`${at} audioId 必須是字串或 null`);
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
  });

  // 參照檢查（下一節點、上一穩定節點、揭答前要有出題）
  let lastQuiz = -1;
  cues.forEach((c, i) => {
    if (!isObj(c)) return;
    const at = `cue ${String(c.id)}`;
    if (typeof c.next === 'string' && !ids.has(c.next)) errors.push(`${at} 的 next 指向不存在的 ${c.next}`);
    if (typeof c.prevStable === 'string') {
      const j = ids.get(c.prevStable);
      if (j === undefined) errors.push(`${at} 的 prevStable 指向不存在的 ${c.prevStable}`);
      else if (j >= i) warnings.push(`${at} 的 prevStable（${c.prevStable}）不在它之前`);
      else if (isObj(cues[j]) && (cues[j] as Obj).autoAdvance === true) warnings.push(`${at} 的 prevStable 是會自動接續的節點，不是穩定節點`);
    }
    if (c.kind === 'quiz') lastQuiz = i;
    if (c.kind === 'reveal' && !isObj(c.quiz) && lastQuiz < 0) errors.push(`${at} 是揭答，但前面沒有出題`);
    if (c.autoAdvance === true && c.next === null) warnings.push(`${at} 設了 autoAdvance 但沒有下一節點`);
  });
  if (isObj(cues[0]) && (cues[0] as Obj).kind !== 'title') warnings.push('第一個 cue 通常應是 title（署名卡待機）');
  return done();
}
