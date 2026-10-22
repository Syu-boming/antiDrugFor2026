// 教師資料的資料層：讀 cue（app/cues/show）、用 app 自己的時間軸程式算每個 cue 的播放長度、
// 解析八題定稿（script/八題_v03.md）與劇本的教師插話，算授課時鐘。
// 只讀，不改任何 app／script 檔。由 tools/teacher_docs.mjs 呼叫。
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

export async function loadAppModules(ROOT) {
  const require = createRequire(join(ROOT, 'app/package.json'));
  const esbuild = require('esbuild');
  // 直接打包 app 的原始碼（mergeShow、buildTimelines、控制台的壓縮規則與按鍵映射），教師資料和演出用同一套算法
  const entry = `
export { mergeShow } from './cues/show';
export { buildTimelines, TIMING } from './cues/timeline';
export { COMPRESSION_TEACHER, COMPRESSION_LABEL, COMPRESSION_RULES, CLOCK_START_OFFSET, zoneFor } from './ui/console-protocol';
export { DEFAULT_KEYMAP, ACTION_LABEL, FIXED_BLOCK } from './engine/input';
`;
  const r = await esbuild.build({ stdin: { contents: entry, resolveDir: join(ROOT, 'app/src'), loader: 'ts', sourcefile: 'teacher_entry.ts' }, bundle: true, format: 'esm', platform: 'node', write: false, logLevel: 'warning' });
  const text = r.outputFiles[0].text;
  const mod = { ...(await import('data:text/javascript;base64,' + Buffer.from(text).toString('base64'))) };
  // 換景漸暗預捲秒數：engine.ts 牽動 three 與 DOM，不打包，直接讀常數
  const m = /export const PREROLL_SEC = ([\d.]+)/.exec(readFileSync(join(ROOT, 'app/src/engine/engine.ts'), 'utf8'));
  mod.PREROLL_SEC = m ? Number(m[1]) : 0.6;
  return mod;
}

/** 最新版配音檔的長度（同 tools/pack.mjs：取最高版本號、ffprobe 量長度） */
export function voDurations(ROOT) {
  const dir = join(ROOT, 'audio/vo');
  const best = {};
  for (const f of readdirSync(dir)) {
    const m = /^(vo_a\d_c\d{3}_\d{2})_v(\d+)\.(wav|mp3)$/i.exec(f);
    if (!m) continue;
    const v = Number(m[2]);
    if (!best[m[1]] || best[m[1]].v < v) best[m[1]] = { v, f };
  }
  const out = {};
  for (const [id, b] of Object.entries(best)) {
    try {
      out[id] = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', join(dir, b.f)], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }));
    } catch { /* 讀不到就用 timings.json */ }
  }
  // 備援：timings.json 的 seconds
  const tj = join(dir, 'timings.json');
  if (existsSync(tj)) {
    const t = JSON.parse(readFileSync(tj, 'utf8'));
    for (const [k, v] of Object.entries(t)) if (out[`vo_${k}`] === undefined && v?.seconds) out[`vo_${k}`] = v.seconds;
  }
  return out;
}

export function loadShow(ROOT, mod) {
  const idx = JSON.parse(readFileSync(join(ROOT, 'app/cues/show/index.json'), 'utf8'));
  const files = {};
  const hash = createHash('sha1');
  for (const f of idx.segments) {
    const raw = readFileSync(join(ROOT, 'app/cues/show', f), 'utf8');
    hash.update(raw);
    files[f] = JSON.parse(raw);
  }
  const merged = mod.mergeShow(idx, files);
  return { idx, files, merged, cueHash: hash.digest('hex').slice(0, 10) };
}

// ───────────────────────────── 八題定稿（script/八題_v03.md 第 4 節） ─────────────────────────────

export function parseEightQuestions(md) {
  const out = {};
  const sec4 = md.split(/^## 4\./m)[1]?.split(/^## 5\./m)[0] ?? '';
  const blocks = sec4.split(/^### /m).slice(1);
  for (const b of blocks) {
    const lines = b.split('\n');
    const head = /^(Q\d)｜(.+)$/.exec(lines[0].trim());
    if (!head) continue;
    const q = { qid: head[1], topic: head[2].trim(), options: [], answer: null, ifMany: [], background: [], cues: {}, zone: null };
    let mode = '';
    for (const raw of lines.slice(1)) {
      const line = raw.replace(/\s+$/, '');
      let m;
      if ((m = /^- cue：出題 (a\d_c\d{3})｜揭答 (a\d_c\d{3})｜點燈 (a\d_c\d{3})｜本題看 \*\*([A-D]) 區\*\*/.exec(line))) {
        q.cues = { quiz: m[1], reveal: m[2], lamp: m[3] }; q.zone = m[4]; continue;
      }
      if ((m = /^- 折折引言：(.+)$/.exec(line))) { q.intro = m[1].trim(); continue; }
      if (/^\*\*題卡文字\*\*/.test(line)) { mode = 'card'; continue; }
      if (mode === 'card') {
        if ((m = /^- 題幹：(.+)$/.exec(line))) { q.question = m[1].trim(); continue; }
        if ((m = /^- ([123])　(.+?)(?:　\*\*〔正解〕\*\*)?$/.exec(line))) {
          q.options[Number(m[1]) - 1] = m[2].trim();
          if (/〔正解〕/.test(line)) q.answer = Number(m[1]);
          continue;
        }
        if (line.trim() === '') continue;
        mode = '';
      }
      if ((m = /^\*\*揭答旁白\*\*：(.+)$/.exec(line))) { q.revealLine = m[1].trim(); mode = ''; continue; }
      if ((m = /^\*\*對全班說\*\*：(.+)$/.exec(line))) { q.say = stripQuotes(m[1].trim()); mode = ''; continue; }
      if ((m = /^\*\*若不少人選了 ([^*]+)\*\*：(.+)$/.exec(line))) { q.ifMany.push({ choice: m[1].trim(), text: stripQuotes(m[2].trim()) }); mode = ''; continue; }
      if ((m = /^\*\*教師背景\*\*：(.*)$/.exec(line))) {
        mode = 'bg';
        if (m[1].trim()) q.background.push(m[1].trim());
        continue;
      }
      if (mode === 'bg') {
        if ((m = /^- (.+)$/.exec(line))) q.background.push(m[1].trim());
        else if (line.trim() && !line.startsWith('#')) q.background.push(line.trim());
      }
    }
    out[q.qid] = q;
  }
  return out;
}

function stripQuotes(s) {
  // 「……」整段包起來的話，去掉最外層的引號
  if (s.startsWith('「') && s.endsWith('」')) {
    const inner = s.slice(1, -1);
    // 只有內部引號成對時才去掉（避免把「不用，我不試」這種內層引號拆壞）
    const opens = (inner.match(/「/g) ?? []).length, closes = (inner.match(/」/g) ?? []).length;
    if (opens === closes) return inner;
  }
  return s;
}

/** 劇本 v03 的〔教師〕行（可選補充等 cue 檔沒有的內容） */
export function parseScriptTeacherLines(md) {
  const out = {};
  let cur = null;
  for (const line of md.split('\n')) {
    const m = /^### (a\d_c\d{3})/.exec(line);
    if (m) { cur = m[1]; continue; }
    if (cur && line.startsWith('〔教師〕')) (out[cur] ??= []).push(line.slice(4).trim());
  }
  return out;
}

// ───────────────────────────── 授課時鐘 ─────────────────────────────

/** 教師現場時間的假設（時長估算_v03.md 第 4 節；v02 起、v03 不變） */
export const TEACHER_TIME = {
  greeting: 30, // 00:00–00:30 課前問候（署名卡待機）
  press: 1, // 老師每按一次下一步的反應時間
  lead: 0.1, // 每段開頭的音訊延遲（引擎 clock.lead 約 0.06 秒＋輸出延遲）
  quiz: { think: 15, reason: 15, feedback: 12, lampCall: 2, quiet: 3 },
  // cue 播完後的教師時間
  after: {
    a0_c005: { sec: 75, label: '規則說明＋捧燈手試做' },
    a1_c003: { sec: 30, label: '找找看 1', l1: 15 },
    a2_c001: { sec: 30, label: '找找看 2', l1: 15 },
    a3_c004: { sec: 90, label: '拒絕句與口訣練習' },
    a4_c013: { sec: 30, label: '找找看 3', l1: 15 },
    a7_c002: { sec: 30, label: '全場一起做口訣' },
    a8_c003: { sec: 45, label: '教師結語', l2: 30 },
  },
  optional: { a2_c004: { sec: 20, label: '可選補充（預設不講，超前時才講）' } },
  reasonL1: 8, // 1 級：學生說理由縮成一句（15 → 8 秒，每題約省 7 秒）
};

/** 壓力測試（時長估算_v03.md 第 4.4 節）：每題拉長到 100 秒、找找看各 45 秒、練習 120 秒、規則 90 秒 */
export const STRESS = { quizTotal: 100, findSec: 45, practice: 120, rules: 90 };

function teacherAfter(cue, level, opts) {
  const T = TEACHER_TIME;
  const a = T.after[cue.id];
  let sec = 0; const parts = [];
  if (a) {
    let s = a.sec;
    if (opts.stress) {
      if (/找找看/.test(a.label)) s = STRESS.findSec;
      if (cue.id === 'a3_c004') s = STRESS.practice;
      if (cue.id === 'a0_c005') s = STRESS.rules;
    }
    if (level >= 1 && a.l1 !== undefined) s = Math.min(s, a.l1);
    if (level >= 2 && a.l2 !== undefined) s = a.l2;
    sec += s; parts.push(`${a.label} ${s} 秒`);
  }
  if (opts.optional && T.optional[cue.id]) { sec += T.optional[cue.id].sec; parts.push(T.optional[cue.id].label); }
  if (cue.kind === 'quiz') { sec += T.quiz.think; parts.push(`想＋全班比 ${T.quiz.think} 秒`); }
  if (cue.kind === 'reveal') {
    const reason = level >= 1 ? T.reasonL1 : T.quiz.reason;
    const s = reason + T.quiz.feedback + T.quiz.lampCall;
    sec += s; parts.push(`點人說理由 ${reason}＋回饋 ${T.quiz.feedback}＋「捧燈手」${T.quiz.lampCall} 秒`);
  }
  if (cue.kind === 'lamp' || cue.lamp) { sec += T.quiz.quiet; parts.push(`燈亮後收聲 ${T.quiz.quiet} 秒`); }
  return { sec, parts };
}

/**
 * 依時間軸排出授課時鐘。
 * @param tlByLevel  {0: timelines, 1: …, 2: …}
 * @param opts { level: 起始級別, dynamic: 依查核點自動升級, stress: 壓力測試, optional: 講可選補充, preroll }
 */
export function scheduleClock(merged, tlByLevel, opts = {}) {
  const T = TEACHER_TIME;
  const preroll = opts.preroll ?? 0.6;
  let level = opts.level ?? 0;
  const ids = merged.cues.map((c) => c.id);
  const rows = [];
  let t = T.greeting; // 00:30 按下署名卡（開演）
  const events = [];
  // 依 next 走（壓縮略過的 cue 依該級的 nextIndex）
  let i = 0; // a0_c000
  let guard = 0;
  while (i >= 0 && guard++ < 500) {
    const tl = tlByLevel[level][i];
    const cue = merged.cues[i];
    const pre = tl.enterFade > 0 ? preroll : 0;
    const isTitleIdle = cue.kind === 'title' && i === 0;
    let start, end;
    if (isTitleIdle) { start = 0; end = T.greeting; }
    else { start = t + pre + T.lead; end = start + tl.duration; }
    const after = isTitleIdle ? { sec: 0, parts: ['課前問候 30 秒（署名卡待機）'] } : teacherAfter(cue, level, opts);
    // 壓力測試：每題拉長到 100 秒（多出的時間算在揭答後）
    if (opts.stress && cue.kind === 'reveal') {
      const qi = rows.length - 1;
      const quizRow = rows[qi];
      const lampTl = tlByLevel[level][tl.nextIndex];
      const base = (quizRow ? quizRow.dur + quizRow.after : 0) + tl.duration + after.sec + (lampTl ? lampTl.duration : 0) + T.quiz.quiet + 3 * T.press;
      const extra = Math.max(0, STRESS.quizTotal - base);
      after.sec += extra; after.parts.push(`壓力測試多 ${Math.round(extra)} 秒`);
    }
    const leave = isTitleIdle ? T.greeting : end + after.sec;
    const next = tl.nextIndex;
    const autoNext = next >= 0 && cue.autoAdvance;
    rows.push({ id: cue.id, index: i, level, kind: cue.kind, start, end, dur: isTitleIdle ? 0 : tl.duration, pre, after: after.sec, afterParts: after.parts, leave, skipped: false });
    // 查核點：離開這個 cue 時記錄，和 cue 檔的 atMinute 比
    if (cue.checkpoint && cue.checkpoint.atMinute > 0) {
      // 控制台在「離開這個 cue（按下一步那一刻）」記錄；最後一個 cue 沒有離開，用播完的時間
      const planned = cue.checkpoint.atMinute * 60;
      const actual = next < 0 ? end : leave + (autoNext ? 0 : T.press);
      const behind = actual - planned;
      events.push({ cueId: cue.id, label: cue.checkpoint.label, planned, actual, behind, level });
      const esc = cue.checkpoint.escalate;
      if (opts.dynamic && esc && behind >= esc.behindSec && esc.level > level) {
        events.push({ cueId: cue.id, label: `觸發 ${esc.level} 級`, planned, actual, behind, level: esc.level, trigger: true });
        level = esc.level;
      }
    }
    if (next < 0) { t = leave; break; }
    t = leave + (autoNext ? 0 : T.press);
    i = next;
  }
  return { rows, events, total: t, finalLevel: level };
}

export function fmtClock(sec) {
  const s = Math.max(0, Math.round(sec));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}
export function fmtMinSec(sec) {
  const s = Math.round(Math.abs(sec));
  const m = Math.floor(s / 60), r = s % 60;
  return m ? `${m} 分 ${String(r).padStart(2, '0')} 秒` : `${r} 秒`;
}
