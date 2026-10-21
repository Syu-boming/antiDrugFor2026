// 全劇 cue 集（app/cues/show/）：index.json 依序列出段落檔（a0.json 開場、a1–a6 六幕、a7 複習與收束、a8 閉幕），
// 打包時（tools/pack.mjs）驗證每個段落檔、合併成一個 cue 檔（cues:show），引擎用 ?cues=show 載入。
// - 每個 cue 的景：cue.set ＞ 段落檔的 set ＞ 'kraft_stage'（合併時填進 cue.set）。
// - 每個 cue 記下所屬段落（cue.segment）；段落的名冊（characters）保留在 segments[]，時間軸用它找說話者、舞台用它擺紙偶。
// - 跨段落的 next／prevStable：可以直接寫別的段落的 cue 編號；段落最後一個 cue 寫 next: null、第一個 cue 寫 prevStable: null
//   時，合併會自動接到下一段的第一個 cue／上一段最後一個穩定節點（全劇最後一段的 next: null 保留＝演出結束）。
// tools/pack.mjs、tools/engine-test.mjs、tools/act_review_pack.mjs 用 esbuild 打包這個檔再執行（它 import 了 validate.ts）。
import type { CharacterRoster, Cue, CueFile, SegmentInfo, ShowIndex } from '../types/cue';
import { validateCueFile, type ValidationResult } from './validate';

export const SHOW_FORMAT = 'antidrug-show/1';
/** 沒有指定景時的全劇預設景（中性的牛皮紙舞台佔位景） */
export const DEFAULT_SHOW_SET = 'kraft_stage';

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);

/** 驗證 index.json 與每個段落檔，再驗證合併後的整齣 */
export function validateShow(index: unknown, files: Record<string, unknown>): ValidationResult & { merged: CueFile | null } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const fail = (): ValidationResult & { merged: CueFile | null } => ({ ok: false, errors, warnings, merged: null });
  if (!isObj(index)) { errors.push('show/index.json 不是 JSON 物件'); return fail(); }
  if (index.format !== SHOW_FORMAT) errors.push(`show/index.json 的 format 應為 "${SHOW_FORMAT}"`);
  if (!Array.isArray(index.segments) || !index.segments.length) { errors.push('show/index.json 的 segments 必須是非空陣列（段落檔名）'); return fail(); }
  // 所有段落的 cue 編號（段落檔單獨驗證時，跨段落的 next／prevStable 指向這裡面就算合法）
  const all = new Set<string>();
  for (const f of index.segments as string[]) {
    const d = files[f];
    if (!isObj(d)) { errors.push(`找不到段落檔 show/${f}`); continue; }
    for (const c of Array.isArray(d.cues) ? d.cues : []) if (isObj(c) && typeof c.id === 'string') all.add(c.id);
  }
  const segIds = new Set<string>();
  for (const f of index.segments as string[]) {
    const d = files[f];
    if (!isObj(d)) continue;
    const v = validateCueFile(d, { externalIds: all });
    errors.push(...v.errors.map((e) => `show/${f}：${e}`));
    warnings.push(...v.warnings.map((w) => `show/${f}：${w}`));
    const id = String(d.id ?? '');
    if (segIds.has(id)) errors.push(`show/${f}：段落 id ${id} 重複`);
    segIds.add(id);
  }
  if (errors.length) return fail();
  const merged = mergeShow(index as unknown as ShowIndex, files as Record<string, CueFile>);
  const v = validateCueFile(merged);
  errors.push(...v.errors.map((e) => `合併後：${e}`));
  warnings.push(...v.warnings.map((w) => `合併後：${w}`));
  // 跨檔流程：從第一個 cue 沿 next 走得到每一個 cue（壓縮略過的節點也要走得到）
  const byId = new Map(merged.cues.map((c, i) => [c.id, i]));
  const seen = new Set<string>();
  for (let i: number | undefined = 0, n = 0; i !== undefined && n <= merged.cues.length; n++) {
    const c: Cue = merged.cues[i];
    if (seen.has(c.id)) { errors.push(`合併後：沿 next 走到 ${c.id} 形成循環`); break; }
    seen.add(c.id);
    i = c.next === null ? undefined : byId.get(c.next ?? '') ?? (c.next === undefined ? i + 1 : undefined);
    if (i !== undefined && i >= merged.cues.length) i = undefined;
  }
  const unreached = merged.cues.filter((c) => !seen.has(c.id)).map((c) => c.id);
  if (unreached.length) warnings.push(`合併後：從片頭沿 next 走不到 ${unreached.slice(0, 8).join('、')}${unreached.length > 8 ? ` 等 ${unreached.length} 個` : ''}`);
  return { ok: errors.length === 0, errors, warnings, merged: errors.length ? null : merged };
}

/** 合併段落檔成一個 cue 檔（不驗證；validateShow 會先驗證再呼叫） */
export function mergeShow(index: ShowIndex, files: Record<string, CueFile>): CueFile {
  const segs: SegmentInfo[] = [];
  const cues: Cue[] = [];
  const roster: CharacterRoster = {};
  for (const f of index.segments) {
    const d = files[f];
    if (!d) continue;
    const set = d.set ?? DEFAULT_SHOW_SET;
    const seg: SegmentInfo = { id: d.id, title: d.title, file: f, set, characters: d.characters ?? {}, cueIds: [] };
    for (const c0 of d.cues) {
      const c: Cue = { ...c0, set: c0.set ?? set, segment: d.id };
      cues.push(c);
      seg.cueIds.push(c.id);
    }
    // 全劇名冊：同一個 id 第一次出現的設定（舞台另依段落名冊擺位置、選紙偶）
    for (const [id, e] of Object.entries(d.characters ?? {})) if (!roster[id]) roster[id] = { ...e };
    segs.push(seg);
  }
  // 段落接縫：段落最後一個 cue 的 next: null → 下一段第一個 cue；段落第一個 cue 的 prevStable: null → 上一段最後一個穩定節點
  for (let k = 0; k < segs.length; k++) {
    const s = segs[k];
    const first = cues.find((c) => c.id === s.cueIds[0]);
    const last = cues.find((c) => c.id === s.cueIds[s.cueIds.length - 1]);
    const nextSeg = segs[k + 1];
    if (last && last.next === null && nextSeg) last.next = nextSeg.cueIds[0];
    const prevSeg = segs[k - 1];
    if (first && first.prevStable === null && prevSeg) {
      const pc = [...prevSeg.cueIds].reverse().map((id) => cues.find((c) => c.id === id)!).find((c) => !c.autoAdvance);
      if (pc) first.prevStable = pc.id;
    }
  }
  return { format: 'antidrug-cues/1', id: index.id, title: index.title, set: segs[0]?.set ?? DEFAULT_SHOW_SET, characters: roster, cues, segments: segs };
}

/** cue 所屬段落的名冊（全劇）；一般 cue 檔回傳檔案層級名冊 */
export function rosterFor(file: CueFile, cue: Cue): CharacterRoster {
  if (file.segments && cue.segment) {
    const s = file.segments.find((x) => x.id === cue.segment);
    if (s?.characters) return s.characters;
  }
  return file.characters ?? {};
}
