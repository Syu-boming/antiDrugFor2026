// PDF 題卡（備援：投影故障時用紙本完成八題）。
// 學生版：橫式 A4，一題一張，題目與三個選項大字；每個選項有大號數字＋手指圖示＋形狀標記（1 圓形、2 三角形、3 方形），不靠顏色。
// 教師版：同一張題卡蓋「正解」印章（勾號＋粗外框），下方附指定區與教師回饋。
// 文字一律取自 cue 的 quiz 資料，腳本另外和 script/八題_v03.md 比對（teacher/data/quiz_check.json）。
import { BYLINE, SHOW_TITLE, htmlPage, esc, inline, shapeSvg, handSvg, lampSvg } from './common.mjs';
import { quizTable } from './docs.mjs';

const CARD_CSS = `
@page { size: A4 landscape; margin: 0; }
body { font-size: 12pt; }
.card { width: 297mm; height: 210mm; padding: 11mm 15mm 9mm; display: flex; flex-direction: column; break-after: page; position: relative; overflow: hidden; }
.card:last-child { break-after: auto; }
.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5mm; }
.qno { font-size: 22pt; font-weight: 900; display: flex; align-items: center; gap: 4mm; }
.qno .badge { border: 2pt solid var(--ink); border-radius: 4mm; padding: 0 4mm; }
.lamps { display: flex; gap: 1.6mm; }
.lamps svg { width: 7mm; height: 9mm; }
.q { font-size: 33pt; font-weight: 800; line-height: 1.32; margin: 0 0 7mm; }
.opts { display: flex; flex-direction: column; gap: 5mm; flex: 1; max-height: 128mm; }
.opts .opt { flex: 1; }
.opt { display: flex; align-items: center; gap: 5mm; border: 1.6pt solid var(--ink2); border-radius: 5mm; padding: 3.5mm 6mm; position: relative; background: #fff; }
.num { font-size: 50pt; font-weight: 900; width: 14mm; text-align: center; line-height: 1; }
.ico-hand { width: 15mm; height: 16mm; color: #3c2f25; flex: none; }
.ico-shape { width: 11mm; height: 11mm; color: #3c2f25; flex: none; }
.otext { font-size: 32pt; font-weight: 700; line-height: 1.25; flex: 1; }
.ph { display: inline-block; white-space: nowrap; }
.foot { display: flex; justify-content: space-between; font-size: 10pt; color: var(--muted); margin-top: 4mm; }
/* 教師版 */
.t .q { font-size: 21pt; margin-bottom: 3mm; }
.t .opts { gap: 2.4mm; flex: none; max-height: none; }
.t .opts .opt { flex: none; }
.t .opt { padding: 1.6mm 5mm; }
.t .num { font-size: 26pt; width: 9mm; }
.t .ico-hand { width: 9mm; height: 10mm; }
.t .ico-shape { width: 7mm; height: 7mm; }
.t .otext { font-size: 17pt; }
.t .opt.correct { border: 3.2pt solid var(--ink); }
.t .opt.dim .otext, .t .opt.dim .num { color: #8a8076; }
.stamp { display: inline-flex; align-items: center; gap: 1.5mm; border: 2.4pt solid var(--indigo); color: var(--indigo); border-radius: 2.5mm; padding: 0.5mm 3mm; font-size: 16pt; font-weight: 900; transform: rotate(-6deg); flex: none; }
.stamp svg { width: 6mm; height: 6mm; }
.meta { display: flex; gap: 6mm; font-size: 13pt; margin: 0 0 2.5mm; }
.meta b { font-size: 15pt; }
.fb { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm 7mm; margin-top: 3.5mm; font-size: 11.5pt; line-height: 1.45; flex: 1; }
.fb h3 { font-size: 12pt; margin: 0 0 1mm; }
.fb .say { border-left: 2.4pt solid var(--accent); padding: 1mm 3mm; background: var(--paper); }
.fb ul { margin: 0; padding-left: 5mm; }
.fb .bg { color: var(--ink2); font-size: 10pt; }
.cover { width: 297mm; height: 210mm; padding: 18mm 22mm; break-after: page; display: flex; flex-direction: column; gap: 5mm; }
.cover h1 { font-size: 30pt; margin: 0; }
.cover p, .cover li { font-size: 14pt; }
.cover table { font-size: 14pt; width: auto; }
.cover th, .cover td { padding: 2mm 5mm; text-align: center; }
`;

/** 教師背景濃縮：每條只留完整的句子，總長約 230 字以內，其餘見教師講稿 */
function briefBackground(list, limit = 230) {
  const out = []; let used = 0; let cut = false;
  for (const b of list) {
    const sents = b.split(/(?<=。)/).filter((x) => x.trim());
    let keep = '';
    for (const x of sents) { if (used + keep.length + x.length > limit && (keep || out.length)) { cut = true; break; } keep += x; }
    if (keep) { out.push(keep); used += keep.length; }
    if (keep.length < b.length) cut = true;
    if (used >= limit) { cut = cut || out.length < list.length; break; }
  }
  if (cut || out.length < list.length) out.push('（完整內容見教師講稿第六節）');
  return out;
}

/** 只在標點後換行：每個片語包成不可斷行的小段（避免「怎／麼辦？」這種斷法） */
function phrases(text) {
  return String(text).split(/(?<=[，。、？！；：])/).filter(Boolean).map((p) => `<span class="ph">${esc(p)}</span>`).join('');
}

function lampsRow(n) {
  return `<div class="lamps">${Array.from({ length: 8 }, (_, i) => lampSvg(i < n - 1)).join('')}</div>`;
}

function optRows(q, teacher) {
  return q.options.map((o, i) => {
    const n = i + 1;
    const correct = teacher && n === q.answer;
    const cls = teacher ? (correct ? ' correct' : ' dim') : '';
    const stamp = correct ? `<span class="stamp"><svg viewBox="0 0 24 24"><path d="M4 12.5 L9.5 18 L20 6" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>正解</span>` : '';
    return `<div class="opt opt-${n}${cls}"><span class="num">${n}</span>${handSvg(n)}${shapeSvg(n)}<span class="otext">${phrases(o)}</span>${stamp}</div>`;
  }).join('\n');
}

export function buildQuizCards(ctx) {
  const qs = quizTable(ctx);
  const student = qs.map((x) => {
    const q = x.quiz;
    return `<section class="card">
<div class="head"><div class="qno"><span class="badge">第 ${q.number} 題</span></div>${lampsRow(q.number)}</div>
<div class="q">${phrases(q.question)}</div>
<div class="opts">${optRows(q, false)}</div>
<div class="foot"><span>想一想……3、2、1，一起比！用手指比 1、2、3，手舉過頭，不用喊。</span><span>${SHOW_TITLE}｜${BYLINE}</span></div>
</section>`;
  });
  const teacher = qs.map((x) => {
    const q = x.quiz, e = x.e;
    return `<section class="card t">
<div class="head"><div class="qno"><span class="badge">第 ${q.number} 題（教師版）</span><span style="font-size:14pt;font-weight:700">${esc(x.qid)}｜${esc(e.topic)}</span></div>${lampsRow(q.number)}</div>
<div class="meta"><span>看 <b>${x.zone} 區</b></span><span>正解 <b>${q.answer}</b></span><span>出題 ${x.cues.quiz}｜揭答 ${x.cues.reveal}｜點燈 ${x.cues.lamp}</span></div>
<div class="q">${phrases(q.question)}</div>
<div class="opts">${optRows(q, true)}</div>
<div class="fb">
<div><h3>揭答後對全班說</h3><div class="say">${inline(e.say)}</div>
<h3 style="margin-top:2mm">接著</h3><ul><li>從 ${x.zone} 區比 ${q.answer} 的同學中點一位說一句理由；說不出來也沒關係，老師幫他接完。</li><li>記錄區、排、座位 →「${q.number === 8 ? '最後一盞，' : '大家一起，'}捧燈手——」說完就按（紙本時老師一起做捧燈手）。</li></ul></div>
<div>${e.ifMany.length ? `<h3>若不少人選了……（對全班統一說，不點名）</h3><ul>${e.ifMany.map((m) => `<li><b>選 ${esc(m.choice)}</b>：${inline(m.text)}</li>`).join('')}</ul>` : ''}
${e.background.length ? `<h3 style="margin-top:2mm">教師背景（不念給學生聽）</h3><ul class="bg">${briefBackground(e.background).map((b) => `<li>${inline(b)}</li>`).join('')}</ul>` : ''}</div>
</div>
<div class="foot"><span>答錯不羞辱：比例對全班統一說，劇情照常前進。每題都點燈，不看答對率。</span><span>${SHOW_TITLE}｜${BYLINE}</span></div>
</section>`;
  });
  const cover = `<section class="cover">
<h1>${SHOW_TITLE}｜紙本題卡（教師版）</h1>
<p>投影故障時的退路：老師舉起學生版題卡（可放大印成 A3），照念題目與三個選項，全班照常用手指比 1、2、3。這一份給老師看正解與回饋。</p>
<table><thead><tr><th>題</th>${qs.map((q) => `<th>${q.qid}</th>`).join('')}</tr></thead><tbody>
<tr><th>看哪區</th>${qs.map((q) => `<td><b>${q.zone}</b></td>`).join('')}</tr>
<tr><th>正解</th>${qs.map((q) => `<td><b>${q.answer}</b></td>`).join('')}</tr></tbody></table>
<ul><li>念法：「第 N 題。」→ 題目 →「一，……二，……三，……」→「想一想……3、2、1，一起比！」</li>
<li>揭答：「正解是 N：……」→ 對全班說 → 點指定區一位說理由 → 捧燈手。</li>
<li>紙本時沒有燈：老師說「第 N 盞燈，亮了！」，全班一起做捧燈手，再做安靜手勢。</li></ul>
<p style="font-size:11pt;color:var(--muted)">題目與選項文字和演出題卡、八題定稿（script/八題_v03.md）一字不差，由 tools/teacher_docs.mjs 比對。${BYLINE}</p>
</section>`;
  return [
    { name: '題卡_學生版', html: htmlPage({ title: `${SHOW_TITLE}｜紙本題卡（學生版）`, css: CARD_CSS, body: student.join('\n') }), expectPages: qs.length, quizPdf: 'student' },
    { name: '題卡_教師版', html: htmlPage({ title: `${SHOW_TITLE}｜紙本題卡（教師版）`, css: CARD_CSS, body: cover + teacher.join('\n') }), expectPages: qs.length + 1, quizPdf: 'teacher' },
  ];
}
