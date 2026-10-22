// 教師與學校資料一鍵重建（G7 交付清單：教師資料、學校資料、列印檔、PDF 題卡）。
//
// 依演出資料（app/cues/show/*.json、audio/vo 的配音長度、script/八題_v03.md、script/劇本_v03.md）產生：
//   teacher/教師講稿.md                 教師講稿（每個 cue 一列：授課時鐘、畫面、老師說／做、按鍵；八題回饋；查核點與壓縮）
//   teacher/html/*.html                 每份資料的列印原始檔（同時是 PDF 的來源）
//   teacher/pdf/*.pdf                   本機 Chrome（Playwright）由 HTML 列印
//   teacher/img/*.png                   貼紙、小卡用的角色裁切圖與折折渲染圖（--art 重做）
//   teacher/data/*.json                 時間計算、題目比對、用語檢查、PDF 檢查的報告
//
// 用法（專案根目錄）：
//   node tools/teacher_docs.mjs              全部重建（圖已存在就沿用）
//   node tools/teacher_docs.mjs --art        連圖一起重做
//   node tools/teacher_docs.mjs --no-pdf     只產生 Markdown／HTML（不開 Chrome）
//   node tools/teacher_docs.mjs --only 教師講稿,題卡_學生版   只重印指定的 PDF
//
// 只讀 app／script／assets，不改任何演出檔。字型：teacher/fonts/NotoSansTC-wght.ttf（SIL OFL 1.1）。
import { existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const TEACHER = join(ROOT, 'teacher');
const SRC = join(TEACHER, 'src');
const args = process.argv.slice(2);
const has = (k) => args.includes(k);
const optVal = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const only = optVal('--only') ? new Set(optVal('--only').split(',')) : null;

const imp = (f) => import(pathToFileURL(join(SRC, f)).href);
const D = await imp('data.mjs');
const { buildTeacherScript } = await imp('script_doc.mjs');
const C = await imp('common.mjs');

for (const d of ['html', 'pdf', 'img', 'data']) mkdirSync(join(TEACHER, d), { recursive: true });
const log = (...a) => console.log('[teacher]', ...a);
const warnings = [];

// ───────────────────────────── 1. 資料 ─────────────────────────────
const mod = await D.loadAppModules(ROOT);
const show = D.loadShow(ROOT, mod);
const merged = show.merged;
const dur = D.voDurations(ROOT);
const tl = { 0: mod.buildTimelines(merged, (id) => dur[id], { compression: 0 }), 1: mod.buildTimelines(merged, (id) => dur[id], { compression: 1 }), 2: mod.buildTimelines(merged, (id) => dur[id], { compression: 2 }) };
const placeholders = tl[0].filter((t) => t.placeholder).map((t) => t.cue.id);
if (placeholders.length) warnings.push(`這些 cue 有台詞找不到配音檔，用字數估計長度：${placeholders.join('、')}`);
const indexOf = Object.fromEntries(merged.cues.map((c, i) => [c.id, i]));
const eight = D.parseEightQuestions(readFileSync(join(ROOT, 'script/八題_v03.md'), 'utf8'));
const scriptTeacher = D.parseScriptTeacherLines(readFileSync(join(ROOT, 'script/劇本_v03.md'), 'utf8'));
const pre = mod.PREROLL_SEC;
const sched = D.scheduleClock(merged, tl, { preroll: pre });
const variants = {
  l1: D.scheduleClock(merged, tl, { preroll: pre, level: 1 }),
  l2: D.scheduleClock(merged, tl, { preroll: pre, level: 2 }),
  stress: D.scheduleClock(merged, tl, { preroll: pre, stress: true }),
  stressDyn: D.scheduleClock(merged, tl, { preroll: pre, stress: true, dynamic: true }),
  optional: D.scheduleClock(merged, tl, { preroll: pre, optional: true }),
};

// 壓縮的實際內容（從時間軸差異算）
const comp = { l1Anim: [], l1Saved: 0, l2Anim: [], l2Saved: 0 };
for (let i = 0; i < merged.cues.length; i++) {
  const c = merged.cues[i];
  const d0 = tl[0][i].duration, d1 = tl[1][i].skipped ? 0 : tl[1][i].duration, d2 = tl[2][i].skipped ? 0 : tl[2][i].duration;
  if (tl[1][i].skipped) { comp.l1Anim.push(`${c.id}〈${c.title}〉整段略過（約 ${Math.round(d0)} 秒）`); comp.l1Saved += d0; }
  else if (tl[1][i].droppedLines.length) {
    const ids = tl[1][i].droppedLines;
    const texts = ids.map((id) => c.lines.find((l) => l.id === id)?.text.replace(/\s+/g, '')).filter(Boolean);
    comp.l1Anim.push(`${c.id}〈${c.title}〉略過第 ${ids.map((x) => x.slice(-2)).join('、')} 句「${texts.join('」「')}」（約 ${(d0 - d1).toFixed(1)} 秒）`);
    comp.l1Saved += d0 - d1;
  } else if (d0 - d1 > 0.05) { comp.l1Anim.push(`${c.id}〈${c.title}〉縮短（約 ${(d0 - d1).toFixed(1)} 秒）`); comp.l1Saved += d0 - d1; }
  if (c.compression === 2 && d1 - d2 > 0.05) {
    const kept = c.level2?.lines;
    comp.l2Anim.push(`${c.id}〈${c.title}〉改短版${kept ? `（只留第 ${kept.map((x) => x.slice(-2)).join('、')} 句）` : ''}，約省 ${(d1 - d2).toFixed(1)} 秒`);
    comp.l2Saved += d1 - d2;
  }
}
const checkpointRules = merged.cues.filter((c) => c.checkpoint?.escalate).map((c) => `${c.checkpoint.label.replace(/收聲後$/, '')}（目標 ${D.fmtClock(c.checkpoint.atMinute * 60)}）落後 ≥ ${D.fmtMinSec(c.checkpoint.escalate.behindSec)} → ${c.checkpoint.escalate.level} 級`);

const generatedAt = new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });
const ctx = { ROOT, merged, tl0: tl[0], tl, indexOf, sched, variants, eight, scriptTeacher, warnings, cueHash: show.cueHash, generatedAt, comp, checkpointRules, mod };

// 時間報告
const timing = {
  generatedAt, cueHash: show.cueHash, prerollSec: pre, teacherTime: D.TEACHER_TIME,
  playback: { level0: +tl[0].reduce((n, t) => n + t.duration, 0).toFixed(1), level1: +tl[1].filter((t) => !t.skipped).reduce((n, t) => n + t.duration, 0).toFixed(1), level2: +tl[2].filter((t) => !t.skipped).reduce((n, t) => n + t.duration, 0).toFixed(1) },
  totalSec: Math.round(sched.total), total: D.fmtClock(sched.total), limit: '38:00', withinLimit: sched.total <= 38 * 60, bufferSec: Math.round(38 * 60 - sched.total),
  variants: Object.fromEntries(Object.entries(variants).map(([k, v]) => [k, { total: D.fmtClock(v.total), totalSec: Math.round(v.total), events: v.events.map((e) => ({ ...e, planned: D.fmtClock(e.planned), actual: D.fmtClock(e.actual), behind: Math.round(e.behind) })) }])),
  checkpoints: sched.events.map((e) => ({ cueId: e.cueId, label: e.label, planned: D.fmtClock(e.planned), estimated: D.fmtClock(e.actual), behindSec: Math.round(e.behind) })),
  compression: { level1SavedSec: +comp.l1Saved.toFixed(1), level2SavedSec: +comp.l2Saved.toFixed(1), level1: comp.l1Anim, level2: comp.l2Anim },
  cues: sched.rows.map((r) => ({ id: r.id, kind: r.kind, start: D.fmtClock(r.start), startSec: +r.start.toFixed(1), playSec: +r.dur.toFixed(2), teacherSec: r.after, teacher: r.afterParts })),
};
writeFileSync(join(TEACHER, 'data/timing.json'), JSON.stringify(timing, null, 1));
log(`播放 0 級 ${timing.playback.level0} 秒；預估總長 ${timing.total}（上限 38:00，緩衝 ${timing.bufferSec} 秒）；壓力測試 ${variants.stress.events.length ? D.fmtClock(variants.stress.total) : ''} → 照查核點壓縮 ${D.fmtClock(variants.stressDyn.total)}`);

// ───────────────────────────── 2. 題目比對（cue quiz ↔ 八題定稿 ↔ 旁白台詞） ─────────────────────────────
const quizCheck = { ok: true, items: [] };
const norm = (s) => String(s ?? '').replace(/\s+/g, '');
const ANSWERS = [2, 3, 1, 1, 3, 2, 3, 2];
for (const c of merged.cues.filter((x) => x.kind === 'quiz')) {
  const q = c.quiz, e = eight[q.qid];
  const item = { qid: q.qid, cue: c.id, checks: [] };
  const chk = (name, a, b) => { const ok = norm(a) === norm(b); item.checks.push({ name, ok, cue: a, ref: b }); if (!ok) quizCheck.ok = false; };
  chk('題幹（cue quiz ↔ 八題定稿）', q.question, e?.question);
  q.options.forEach((o, i) => chk(`選項 ${i + 1}（cue quiz ↔ 八題定稿）`, o, e?.options[i]));
  chk('正解（cue quiz ↔ 八題定稿）', String(q.answer), String(e?.answer));
  chk('正解（cue quiz ↔ 固定答案順序 2、3、1、1、3、2、3、2）', String(q.answer), String(ANSWERS[q.number - 1]));
  chk('出題 cue 編號', c.id, e?.cues.quiz);
  const lines = c.lines.map((l) => l.text);
  chk('旁白念的題幹', lines[1], q.question);
  q.options.forEach((o, i) => chk(`旁白念的選項 ${i + 1}`, lines[2 + i], `${C.zh(i + 1)}，${o}`));
  const rev = merged.cues[indexOf[e?.cues.reveal]];
  chk('揭答旁白（cue ↔ 八題定稿）', rev?.lines[0]?.text, e?.revealLine);
  chk('揭答旁白內容', rev?.lines[0]?.text, `正解是${C.zh(q.answer)}：${q.options[q.answer - 1]}`);
  const z = /本題看 ([A-D]) 區/.exec(c.teacherNote ?? '')?.[1];
  chk('指定區（cue 教師欄 ↔ 八題定稿 ↔ A→B→C→D 各輪兩次）', `${z}${e?.zone}`, `${mod.zoneFor(q.number)}${mod.zoneFor(q.number)}`);
  quizCheck.items.push(item);
}
writeFileSync(join(TEACHER, 'data/quiz_check.json'), JSON.stringify(quizCheck, null, 1));
log(`題目比對：${quizCheck.ok ? '全部一致' : '有不一致，見 teacher/data/quiz_check.json'}（${quizCheck.items.reduce((n, it) => n + it.checks.length, 0)} 項）`);

// ───────────────────────────── 3. 文件 ─────────────────────────────
const outputs = []; // { name, html, pageCheck }
const ts = buildTeacherScript(ctx);
writeFileSync(join(TEACHER, '教師講稿.md'), ts.md);
outputs.push({ name: '教師講稿', html: ts.html });

const extra = await imp('docs.mjs');
for (const o of extra.buildAll(ctx)) outputs.push(o);

for (const o of outputs) writeFileSync(join(TEACHER, 'html', `${o.name}.html`), o.html);
log(`HTML ${outputs.length} 份 → teacher/html/`);

// 子集字型（依所有文件實際用到的字；PDF 以 CID TrueType 內嵌）
const { buildSubsetFonts } = await imp('fonts.mjs');
const fontRes = buildSubsetFonts(TEACHER, [...outputs.map((o) => o.html.replace(/<style[\s\S]*?<\/style>/g, '').replace(/<[^>]+>/g, '')), ts.md], log);
if (!fontRes.ok) warnings.push('子集字型沒有產生（fontTools 無法使用），PDF 用可變字型（Type 3，檔案較大）');

// ───────────────────────────── 4. 圖（角色裁切、折折渲染） ─────────────────────────────
const art = await imp('art.mjs');
const needArt = has('--art') || !art.allPresent(TEACHER);
const require = createRequire(join(ROOT, 'app/package.json'));
let browser = null;
const getBrowser = async () => {
  if (browser) return browser;
  const { chromium } = require('playwright-core');
  browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--allow-file-access-from-files'] });
  return browser;
};
if (needArt && !has('--no-pdf')) {
  await art.renderArt(ROOT, TEACHER, await getBrowser(), log);
} else if (needArt) warnings.push('teacher/img 缺圖，但指定了 --no-pdf：沒有開 Chrome 產生圖');

// ───────────────────────────── 5. PDF ─────────────────────────────
const pdfReport = [];
if (!has('--no-pdf')) {
  const b = await getBrowser();
  const page = await b.newPage();
  for (const o of outputs) {
    if (only && !only.has(o.name)) continue;
    const htmlPath = join(TEACHER, 'html', `${o.name}.html`);
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
    await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map((im) => (im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; })))); });
    const missingImg = await page.evaluate(() => [...document.images].filter((im) => !im.naturalWidth).map((im) => im.getAttribute('src')));
    const fontOk = await page.evaluate(() => document.fonts.check('16px "Noto Sans TC Local"'));
    const pdfPath = join(TEACHER, 'pdf', `${o.name}.pdf`);
    await page.pdf({ path: pdfPath, preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false });
    const info = execFileSync('pdfinfo', [pdfPath], { encoding: 'utf8' });
    const pages = Number(/Pages:\s+(\d+)/.exec(info)?.[1] ?? 0);
    const size = /Page size:\s+([^\n]+)/.exec(info)?.[1]?.trim();
    const rep = { name: o.name, pages, size, fontOk, missingImg };
    if (o.expectPages !== undefined && pages !== o.expectPages) { rep.problem = `應為 ${o.expectPages} 頁，實際 ${pages} 頁`; warnings.push(`${o.name}.pdf ${rep.problem}`); }
    if (missingImg.length) warnings.push(`${o.name} 有圖載入失敗：${missingImg.join('、')}`);
    if (!fontOk) warnings.push(`${o.name} 沒有載入 Noto Sans TC`);
    pdfReport.push(rep);
    log(`PDF ${o.name}.pdf：${pages} 頁 ${size}`);
  }
  await page.close();
}
if (browser) await browser.close();

// ───────────────────────────── 6. 檢查：PDF 題卡文字、用語 ─────────────────────────────
const checkMod = await imp('checks.mjs');
const checks = checkMod.runChecks({ ROOT, TEACHER, merged, eight, outputs, md: ts.md, pdfReport, quizCheck, skipPdf: has('--no-pdf') });
const report = { generatedAt, cueHash: show.cueHash, timing: { total: timing.total, bufferSec: timing.bufferSec, withinLimit: timing.withinLimit }, quizCheckOk: quizCheck.ok, pdf: pdfReport, checks, warnings };
writeFileSync(join(TEACHER, 'data/check_report.json'), JSON.stringify(report, null, 1));
writeFileSync(join(TEACHER, 'data/檢查報告.md'), checkReportMd(report, quizCheck, timing));
for (const w of warnings) log('注意：', w);
log(`檢查：${checks.summary}`);
if (!quizCheck.ok || checks.failed) process.exitCode = 1;

/** 給人看的檢查報告（teacher/data/檢查報告.md，每次重建都覆寫） */
function checkReportMd(report, quizCheck, timing) {
  const L = [];
  L.push('# 教師資料自動檢查報告', '', `由 \`tools/teacher_docs.mjs\` 產生（${report.generatedAt}，cue 資料指紋 ${report.cueHash}）。${C.BYLINE}。`, '');
  L.push('## 時長', '', `- 預估總長 **${timing.total}**（上限 38:00，${timing.withinLimit ? `緩衝 ${D.fmtMinSec(timing.bufferSec)}` : '超過上限'}）；預錄播放 0 級 ${timing.playback.level0} 秒、1 級 ${timing.playback.level1} 秒、2 級 ${timing.playback.level2} 秒。`);
  const VN = { l1: '從頭啟用 1 級', l2: '從頭啟用 2 級', stress: '現場拉長、不壓縮', stressDyn: '現場拉長、照查核點壓縮', optional: '加講 a2_c004 可選補充' };
  for (const [k, v] of Object.entries(timing.variants)) L.push(`- ${VN[k] ?? k}：${v.total}`);
  L.push('', '| 查核點 | cue | 控制台目標 | 講稿估計 | 差（秒） |', '|---|---|---|---|---|');
  for (const c of timing.checkpoints) L.push(`| ${c.label} | ${c.cueId} | ${c.planned} | ${c.estimated} | ${c.behindSec >= 0 ? '+' : ''}${c.behindSec} |`);
  L.push('', '## 檢查項目', '', `結果：${report.checks.summary}`, '', '| 項目 | 結果 |', '|---|---|');
  for (const r of report.checks.results) L.push(`| ${r.name} | ${r.ok ? '通過' : '**不通過**'} |`);
  L.push('', '## 八題文字比對（cue quiz ↔ script/八題_v03.md ↔ 旁白台詞 ↔ PDF 題卡）', '');
  L.push('| 題 | 比對項目數 | 不一致 |', '|---|---|---|');
  for (const it of quizCheck.items) { const bad = it.checks.filter((c) => !c.ok); L.push(`| ${it.qid} | ${it.checks.length} | ${bad.length ? bad.map((b) => b.name).join('；') : '無'} |`); }
  const pdfRows = report.checks.results.filter((r) => /pdftotext/.test(r.name));
  for (const r of pdfRows) {
    L.push('', `**${r.name}**：${r.ok ? '通過' : '不通過'}`, '');
    if (Array.isArray(r.detail)) for (const d of r.detail) L.push(`- ${d.qid}（第 ${d.page} 頁）：${d.ok ? '題目與三個選項都在 PDF 文字裡，cue 與定稿相同' : `缺少 ${d.missing.join('、') || '—'}；cue 與定稿相同：${d.cueMatchesEight}`}`);
  }
  L.push('', '## PDF', '', '| 檔案 | 頁數 | 尺寸 | 字型 | 備註 |', '|---|---|---|---|---|');
  for (const p of report.pdf) L.push(`| ${p.name}.pdf | ${p.pages} | ${p.size} | ${p.fontOk ? 'Noto Sans TC' : '**未載入**'} | ${p.problem ?? ''} |`);
  if (report.warnings.length) { L.push('', '## 注意', ''); for (const w of report.warnings) L.push(`- ${w}`); }
  return L.join('\n') + '\n';
}
