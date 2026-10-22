// 段落指紋（G6 修正第 1 輪）：驗收包記下量的是哪一版段落，全劇驗收包（show_review_pack）用雜湊比對「與建置一致」，不再只比 cue 長度。
//
// 兩種 sha1（都先拿掉所有 checkpoint 欄位，再把 JSON 的鍵排序後序列化）：
//   source：app/cues/show/<段>.json 段落檔本身（技術 QA G4 指定：「段落檔的 sha1（去掉 checkpoint 欄）」）
//   built ：app/dist/data/cues_show.js 合併後這一段的內容（段落資訊＋這一段的 cue；合併時會補 cue.set、cue.segment、段落接縫的 next／prevStable）
// 另外用 tools/pack.mjs 的 loadShow 把目前的段落檔照建置的方式合併一次，算出 sourceMerged，和 built 相同＝app/dist 是用目前段落檔建的。
//
// 用法（給其他工具 import）：
//   import { segmentFingerprints } from './seg_fingerprint.mjs';
//   const fp = await segmentFingerprints();   // { a0: { file, source, built, sourceMerged, builtFromSource }, … }
// 指令列：node tools/seg_fingerprint.mjs [--dist <資料夾>]   → 印出 JSON
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

export const FINGERPRINT_METHOD = 'sha1（拿掉所有 checkpoint 欄位、JSON 鍵排序後序列化）；source＝app/cues/show/<段>.json；built＝app/dist/data/cues_show.js 合併後的這一段（段落資訊＋cue）；sourceMerged＝目前段落檔照建置方式合併後的這一段';

/** 拿掉 checkpoint 欄位、鍵排序 */
export function canonical(v) {
  if (Array.isArray(v)) return v.map(canonical);
  if (v && typeof v === 'object') {
    const o = {};
    for (const k of Object.keys(v).sort()) if (k !== 'checkpoint' && v[k] !== undefined) o[k] = canonical(v[k]);
    return o;
  }
  return v;
}
export const sha1 = (v) => createHash('sha1').update(JSON.stringify(canonical(v))).digest('hex');

/** 讀資料包（window.__pack(id, 資料)） */
export function readPack(distDir, file, id) {
  const src = readFileSync(join(distDir, 'data', file), 'utf8');
  const head = `window.__pack(${JSON.stringify(id)},`;
  const i = src.indexOf(head);
  if (i < 0) throw new Error(`${file} 裡沒有 ${id}`);
  return JSON.parse(src.slice(i + head.length).replace(/\);\s*$/, ''));
}

/** 合併後全劇（cues_show.js 的內容或 loadShow 的 merged）裡某一段的指紋 */
export function mergedSegmentSha1(show, segId) {
  const seg = show.segments.find((s) => s.id === segId);
  if (!seg) return null;
  return sha1({ segment: seg, cues: show.cues.filter((c) => c.segment === segId) });
}

const r3 = (x) => Math.round(x * 1000) / 1000;
/**
 * act_review_pack 寫進 timeline.json 的 cues（buildTimelines 解析後的時間軸；act_review_pack.mjs 與 show_review_pack.mjs 共用，兩邊格式一定相同）。
 * show_review_pack 拿它當後備比對：舊包沒有段落指紋時，比「包裡的解析後時間軸」與「目前建置解析後的時間軸」（不含 initialState 的站位與鏡位，只供參考）。
 */
export function packTimelineCues(tls, MUSIC_LEVEL) {
  return tls.map((t) => ({
    id: t.cue.id, kind: t.cue.kind, title: t.cue.title, duration: r3(t.duration), autoAdvance: !!t.cue.autoAdvance, set: t.set, enterFade: t.enterFade,
    audioId: t.cue.audioId ?? null, musicLoop: t.cue.musicLoop ?? true, musicLevel: t.cue.musicLevel ?? MUSIC_LEVEL[t.cue.kind] ?? 0.6,
    // musicDuck（台詞時的配樂避讓增益，G6 修正第 2 輪）只在 cue 有寫時才列：沒寫的 cue 時間軸與舊包逐字相同，離線混音照 DUCK_LEVEL
    ...(t.cue.musicDuck !== undefined ? { musicDuck: t.cue.musicDuck } : {}),
    compression: t.cue.compression, lamp: t.cue.lamp ?? null, quiz: t.quiz ?? null,
    lines: t.lines.map((l) => ({ id: l.line.id, speaker: l.line.speaker, text: l.line.text, audioId: l.audioId, start: r3(l.start), end: r3(l.end), duration: r3(l.duration), placeholder: l.placeholder, pages: l.pages.map((p) => ({ start: r3(p.start), end: r3(p.end), rows: p.rows })) })),
    sfx: t.sfx.map((s) => ({ ...s, at: r3(s.at) })),
    music: t.music.map((m) => ({ ...m, at: r3(m.at) })),
    anims: t.anims.map((a) => ({ name: a.name, target: a.target ?? null, start: r3(a.start), end: r3(a.end), params: a.params })),
    strings: Object.fromEntries(Object.entries(t.cue.initialState.characters ?? {}).filter(([, c]) => c.strings?.length).map(([id, c]) => [id, c.strings])),
    stringAnims: t.anims.filter((a) => a.name.startsWith('strings.')).map((a) => ({ target: a.target ?? null, name: a.name, anchors: a.params.anchors ?? null })),
  }));
}
/** 解析後時間軸的 sha1（先經過 JSON 來回，和讀回 timeline.json 的值一致） */
export const timelineSha1 = (cues) => sha1(JSON.parse(JSON.stringify(cues)));

/** 每一段的 source／built／sourceMerged 指紋（distDir 預設 app/dist） */
export async function segmentFingerprints({ distDir = join(ROOT, 'app/dist'), cuesDir = join(ROOT, 'app/cues') } = {}) {
  const manifest = readPack(distDir, 'manifest.js', 'manifest');
  const built = manifest.cueSets?.show ? readPack(distDir, manifest.cueSets.show, 'cues:show') : null;
  const { loadShow } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
  // 別的代理正在改段落檔時可能讀到寫一半的 JSON：段落檔這邊算不出來就記下原因，建置那邊照算
  let src = null;
  let sourceError = null;
  try { src = await loadShow(cuesDir); } catch (err) { sourceError = err instanceof Error ? err.message : String(err); }
  const srcSha1 = (p) => { try { return existsSync(p) ? sha1(JSON.parse(readFileSync(p, 'utf8'))) : null; } catch { return null; } };
  const out = {};
  const segs = built?.segments ?? (src?.index?.segments ?? []).map((f) => ({ id: f.replace(/\.json$/, ''), file: f }));
  for (const s of segs) {
    const p = join(cuesDir, 'show', s.file);
    const source = srcSha1(p);
    const b = built ? mergedSegmentSha1(built, s.id) : null;
    const sm = src?.merged ? mergedSegmentSha1(src.merged, s.id) : null;
    out[s.id] = { file: `app/cues/show/${s.file}`, source, built: b, sourceMerged: sm, builtFromSource: b !== null && b === sm };
  }
  return { method: FINGERPRINT_METHOD, distBuiltAt: manifest.builtAt ?? null, sourceValid: src ? !!src.ok : null, sourceError, segments: out };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const i = process.argv.indexOf('--dist');
  const distDir = i > 0 ? resolve(process.argv[i + 1]) : join(ROOT, 'app/dist');
  console.log(JSON.stringify(await segmentFingerprints({ distDir }), null, 1));
}
