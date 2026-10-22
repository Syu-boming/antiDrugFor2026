// 列印檔：參與小卡、角色貼紙、成果紀錄範本、導師匿名回饋單。
// 參與小卡與貼紙用 teacher/img 的角色裁切圖（tools/teacher_docs.mjs --art 從 assets/final 母版重做）。
import { BYLINE, SHOW_TITLE, htmlPage, esc, lampSvg } from './common.mjs';
import { fmtClock } from './data.mjs';
import { quizTable } from './docs.mjs';
import { GOALS } from './lesson.mjs';

const SLOGAN = '不碰、不試；先離開，找大人。';
const ACTS = [['act-cross', '不碰'], ['act-palmno', '不試'], ['act-pointr', '先離開'], ['act-forehead', '找大人']];

export function buildPrints(ctx, segs) {
  return [buildSmallCards(), buildStickers(), buildRecord(ctx, segs), buildFeedback()];
}

// ───────────────────────────── 參與小卡（名片大小 90×54 mm，A4 一頁 10 張） ─────────────────────────────

const SMALL_CSS = `
@page { size: A4 portrait; margin: 0; }
.sheet { width: 210mm; height: 297mm; padding: 13.5mm 15mm; display: grid; grid-template-columns: 90mm 90mm; grid-template-rows: repeat(5, 54mm); justify-content: center; break-after: page; }
.sheet:last-child { break-after: auto; }
.c { width: 90mm; height: 54mm; border: 0.5pt dashed #9c8f82; padding: 3.2mm 4mm 2.6mm; display: flex; flex-direction: column; background: #fffaf2; position: relative; overflow: hidden; }
.c .t { display: flex; align-items: center; gap: 1.6mm; font-size: 8.4pt; font-weight: 700; color: var(--accent); }
.c .t svg { width: 3.4mm; height: 4.4mm; }
.c .s { font-size: 17pt; font-weight: 900; line-height: 1.22; margin: 1.2mm 0 1.4mm; letter-spacing: 0.02em; }
.c .acts { display: flex; justify-content: space-between; gap: 1mm; flex: 1; align-items: flex-end; }
.c .a { flex: 1; display: flex; flex-direction: column; align-items: center; }
.c .a img { height: 21mm; width: auto; max-width: 20mm; object-fit: contain; }
.c .a span { font-size: 8.6pt; font-weight: 800; margin-top: 0.4mm; }
.c .by { position: absolute; right: 3.5mm; top: 3.3mm; font-size: 6.8pt; color: var(--muted); }
`;

function buildSmallCards() {
  const card = `<div class="c"><div class="t">${lampSvg(true)}${SHOW_TITLE}｜參與小卡</div><div class="by">${BYLINE}</div>
<div class="s">不碰、不試；<br>先離開，找大人。</div>
<div class="acts">${ACTS.map(([img, l]) => `<div class="a"><img src="../img/${img}.png" alt=""><span>${l}</span></div>`).join('')}</div></div>`;
  const sheet = `<section class="sheet">${Array.from({ length: 10 }, () => card).join('')}</section>`;
  return { name: '參與小卡', html: htmlPage({ title: `${SHOW_TITLE}｜參與小卡`, css: SMALL_CSS, body: sheet }), expectPages: 1 };
}

// ───────────────────────────── 角色貼紙 ─────────────────────────────

const STICKERS = [
  ['st-xiaoqing', '小晴'], ['st-xiaoyu', '小宇'], ['st-zhezhe', '折折'],
  ['st-ale', '阿樂叔叔'], ['st-pinan', '品安'], ['st-lin', '林老師'],
  ['st-ye', '葉護理師'], ['st-chen', '陳伯伯'], [['st-xiaoqing-bow', 'st-xiaoyu-bow'], '謝謝你！'],
];
const ROUND = [['bust-xiaoqing', '小晴'], ['bust-xiaoyu', '小宇'], ['bust-zhezhe', '折折'], ['bust-ale', '阿樂叔叔'], ['bust-pinan', '品安']];

const STICKER_CSS = `
@page { size: A4 portrait; margin: 0; }
.sheet { width: 210mm; height: 297mm; padding: 12mm 12mm 10mm; break-after: page; display: flex; flex-direction: column; }
.sheet:last-child { break-after: auto; }
.hd { font-size: 8.5pt; color: var(--muted); display: flex; justify-content: space-between; margin-bottom: 3mm; }
.g9 { display: grid; grid-template-columns: repeat(3, 60mm); grid-template-rows: repeat(3, 84mm); gap: 4mm 3mm; justify-content: center; }
.st { border: 0.5pt dashed #9c8f82; border-radius: 6mm; background: #fbf3e6; display: flex; flex-direction: column; align-items: center; padding: 3mm 2.5mm 2.5mm; overflow: hidden; }
.st .pic { flex: 1; display: flex; align-items: flex-end; justify-content: center; gap: 1mm; min-height: 0; width: 100%; }
.st .pic img { max-height: 60mm; max-width: 52mm; object-fit: contain; }
.st .pic.two img { max-width: 26mm; max-height: 56mm; }
.st .pic img.zz { max-height: 52mm; }
.st .nm { font-size: 14pt; font-weight: 900; margin-top: 1.5mm; }
.st .sl { font-size: 7.6pt; font-weight: 700; color: var(--ink2); white-space: nowrap; }
.g20 { display: grid; grid-template-columns: repeat(4, 44mm); grid-template-rows: repeat(5, 50mm); gap: 3mm 4mm; justify-content: center; }
.rd { display: flex; flex-direction: column; align-items: center; }
.rd .ci { width: 44mm; height: 44mm; border-radius: 50%; border: 0.5pt dashed #9c8f82; background: #fbf3e6; overflow: hidden; display: flex; align-items: flex-end; justify-content: center; position: relative; }
.rd .ci img { width: 36mm; height: 38mm; object-fit: contain; object-position: bottom; }
.rd .ci .lb { position: absolute; bottom: 3mm; left: 50%; transform: translateX(-50%); background: #fffaf2; border: 0.6pt solid #5a4636; border-radius: 3mm; padding: 0 2.2mm; font-size: 8.6pt; font-weight: 900; white-space: nowrap; }
`;

function buildStickers() {
  const one = ([img, name]) => {
    const imgs = Array.isArray(img) ? img : [img];
    return `<div class="st"><div class="pic${imgs.length > 1 ? ' two' : ''}">${imgs.map((i) => `<img src="../img/${i}.png" alt=""${i.includes('zhezhe') ? ' class="zz"' : ''}>`).join('')}</div><div class="nm">${esc(name)}</div><div class="sl">${SLOGAN}</div></div>`;
  };
  const page1 = `<section class="sheet"><div class="hd"><span>${SHOW_TITLE}｜角色貼紙（獎品，非食物）　建議用 A4 貼紙紙列印，沿虛線剪下</span><span>${BYLINE}</span></div><div class="g9">${STICKERS.map(one).join('')}</div></section>`;
  const rounds = [];
  for (let r = 0; r < 5; r++) for (let c = 0; c < 4; c++) rounds.push(ROUND[(r * 4 + c) % ROUND.length]);
  const page2 = `<section class="sheet"><div class="hd"><span>${SHOW_TITLE}｜圓形角色貼紙（直徑 44 mm）　沿虛線剪下</span><span>${BYLINE}</span></div><div class="g20">${rounds.map(([img, name]) => `<div class="rd"><div class="ci"><img src="../img/${img}.png" alt=""><span class="lb">${esc(name)}</span></div></div>`).join('')}</div></section>`;
  return { name: '角色貼紙', html: htmlPage({ title: `${SHOW_TITLE}｜角色貼紙`, css: STICKER_CSS, body: page1 + page2 }), expectPages: 2 };
}

// ───────────────────────────── 成果紀錄範本 ─────────────────────────────

const FORM_CSS = `
@page { size: A4 portrait; margin: 13mm 14mm 12mm; }
body { font-size: 10.4pt; }
h1 { font-size: 17pt; text-align: center; margin: 0 0 1pt; }
.sub { text-align: center; color: var(--muted); font-size: 9.5pt; margin-bottom: 5pt; }
h2 { font-size: 12pt; margin: 9pt 0 3pt; border-left: 4pt solid var(--accent); padding-left: 6pt; break-after: avoid; }
table { font-size: 9.8pt; }
th, td { padding: 3pt 5pt; }
td.blank { height: 15pt; }
.box { border: 0.8pt solid var(--line); border-radius: 3pt; min-height: 22mm; padding: 3pt 6pt; color: var(--muted); font-size: 9pt; }
.box.tall { min-height: 26mm; }
.ck { white-space: nowrap; }
.photos { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
.photos .box { min-height: 40mm; }
.pb { break-after: page; }
.hint { font-size: 8.8pt; color: var(--muted); }
`;
const CK = (opts) => opts.map((o) => `<span class="ck">□ ${o}</span>`).join('　');

function buildRecord(ctx, segs) {
  const qs = quizTable(ctx);
  const goalOf = (qid) => GOALS.find((g) => g.where.includes(qid));
  // 查核點一律用 cue 的 checkpoint.atMinute（控制台畫面上的目標時間）
  const cps = ctx.merged.cues.filter((c) => c.checkpoint && c.checkpoint.atMinute > 0);
  const body = `
<h1>反毒剪紙劇場《${SHOW_TITLE}》成果紀錄</h1>
<div class="sub">範本｜${BYLINE}｜交學務處（1–2 頁）。不記錄學生姓名，不放可辨識正臉的照片，不寫家庭狀況。</div>

<h2>一、活動資料</h2>
<table><tbody>
<tr><th style="width:17%">活動名稱</th><td colspan="3">反毒剪紙劇場《${SHOW_TITLE}》：不碰、不試；先離開，找大人</td></tr>
<tr><th>日期／節次</th><td class="blank" style="width:33%"></td><th style="width:17%">地點</th><td class="blank"></td></tr>
<tr><th>對象</th><td>三、四年級　　　班，共　　　人</td><th>主講</th><td>許博明老師</td></tr>
<tr><th>協助人員</th><td colspan="3" class="blank"></td></tr>
<tr><th>教育定位</th><td colspan="3">學校防制學生藥物濫用三級預防之一級預防（宣導教育）；以操偶線比喻與全班互動練習拒絕、離開、求助與用路安全，不恐嚇、不探詢家庭。</td></tr>
</tbody></table>

<h2>二、學習目標對照與課中作答概況</h2>
<p class="hint">協助教師揭答時逐題勾選全班作答概況（看全場手勢的大約比例，不記錄個人）。</p>
<table><thead><tr><th style="width:7%">題</th><th style="width:30%">主題（學習目標）</th><th style="width:7%">正解</th><th>比出正解的大約比例</th></tr></thead><tbody>
${qs.map((q) => `<tr><td>${q.qid}</td><td>${esc(q.e.topic)}（${goalOf(q.qid)?.n ?? ''}）</td><td>${q.answer}</td><td>${CK(['幾乎全班', '約一半', '少數'])}</td></tr>`).join('\n')}
<tr><td colspan="2">拒絕句與口訣動作（a3_c004）</td><td>—</td><td>${CK(['幾乎全班參與', '約一半', '少數'])}</td></tr>
</tbody></table>

<h2>三、時間紀錄（教師控制台的查核點）</h2>
<table><thead><tr><th>查核點</th><th style="width:22%">控制台目標</th><th style="width:16%">實際</th><th style="width:28%">備註</th></tr></thead><tbody>
${cps.map((c) => `<tr><td>${esc(c.checkpoint.label)}（${c.id}）</td><td>${fmtClock(c.checkpoint.atMinute * 60)}</td><td></td><td></td></tr>`).join('\n')}
<tr><td>下課（教師結語結束）</td><td>預估 ${fmtClock(ctx.sched.total)}</td><td></td><td></td></tr>
</tbody></table>
<p>壓縮級別使用：${CK(['沒有使用', '1 級（從　　　起）', '2 級（從　　　起）'])}</p>

<div class="pb"></div>
<h2>四、導師匿名回饋摘要（共　　份）</h2>
<table><thead><tr><th style="width:24%">項目</th><th>摘要</th></tr></thead><tbody>
${['學生理解', '投入程度', '內容疑慮', '視聽清晰度', '建議'].map((x) => `<tr><td>${x}</td><td class="blank" style="height:20pt"></td></tr>`).join('\n')}
</tbody></table>

<h2>五、一週後全班複習（導師口頭進行，不記名、不打分、不問家庭）</h2>
<table><thead><tr><th style="width:42%">情境</th><th>全班回應概況</th></tr></thead><tbody>
<tr><td>遇到有人邀請你試試看，怎麼辦？</td><td>${CK(['多數說得出', '部分說得出', '需要提醒'])}</td></tr>
<tr><td>接送的人怪怪的，怎麼辦？</td><td>${CK(['多數說得出', '部分說得出', '需要提醒'])}</td></tr>
<tr><td>朋友要你保密，怎麼辦？</td><td>${CK(['多數說得出', '部分說得出', '需要提醒'])}</td></tr>
<tr><td>口訣「${SLOGAN}」</td><td>${CK(['多數記得', '部分記得', '需要提醒'])}</td></tr>
</tbody></table>

<h2>六、技術事件</h2>
<p>${CK(['無', '有（簡述狀況與處理方式）'])}</p>
<div class="box">例：簡報筆失靈改用鍵盤、聲音延遲調整「開頭靜音」……</div>

<h2>七、教學省思</h2>
<div class="box tall">有效之處：</div>
<div class="box tall" style="margin-top:3mm">待調整處：</div>

<h2>八、活動照片（背影、舞台與教師為主，避開可辨識的臉，不用閃光燈）</h2>
<div class="photos"><div class="box">照片 1　說明：</div><div class="box">照片 2　說明：</div></div>
`;
  return { name: '成果紀錄範本', html: htmlPage({ title: `${SHOW_TITLE}｜成果紀錄範本`, css: FORM_CSS, body }), expectPages: 2 };
}

// ───────────────────────────── 導師匿名回饋單（5 題） ─────────────────────────────

const FB_CSS = `
@page { size: A4 portrait; margin: 14mm 16mm 12mm; }
body { font-size: 11.4pt; }
h1 { font-size: 18pt; text-align: center; margin: 0 0 2pt; }
.sub { text-align: center; color: var(--muted); font-size: 10pt; margin-bottom: 4pt; }
.notice { border: 1.2pt solid var(--ink); border-radius: 4pt; padding: 4pt 8pt; font-size: 10.4pt; margin: 4pt 0 8pt; }
.q { margin: 0 0 7pt; break-inside: avoid; }
.q h2 { font-size: 12.6pt; margin: 0 0 3pt; }
.q .ops { display: flex; flex-wrap: wrap; gap: 3pt 14pt; margin: 2pt 0 3pt; }
.line { border-bottom: 0.8pt solid var(--line); height: 19pt; }
.thanks { text-align: center; color: var(--muted); font-size: 10pt; margin-top: 8pt; }
`;

function buildFeedback() {
  const Q = [
    ['1. 學生理解', '學生大致聽得懂故事、題目與操偶線的比喻嗎？', ['很清楚', '大致清楚', '部分不清楚', '不清楚'], '哪一段或哪一題比較不清楚？'],
    ['2. 投入程度', '學生投入的程度（作答、說口訣、做動作）？', ['非常投入', '大致投入', '部分分心', '多數分心'], '學生特別有反應的地方：'],
    ['3. 內容疑慮', '有沒有讓您擔心的畫面、用語或節奏？', ['沒有', '有（請寫下是哪裡）'], '說明：'],
    ['4. 視聽清晰度', '坐在後排也看得清字幕與題卡、聽得清楚配音嗎？', ['清楚', '字太小', '聲音太小', '聲音太大', '其他'], '說明：'],
    ['5. 建議', '對這堂課的其他建議（內容、時間、互動方式）：', null, ''],
  ];
  const body = `
<h1>反毒剪紙劇場《${SHOW_TITLE}》導師回饋單</h1>
<div class="sub">${BYLINE}｜當天填寫，交給學務處或主講老師</div>
<div class="notice"><b>不記名。</b>請不要寫學生姓名、座號或家庭狀況。若有學生需要個別關心（例如情緒反應或主動透露的事情），請直接聯繫輔導室，不寫在這張單子上。</div>
${Q.map(([h, ask, ops, more]) => `<div class="q"><h2>${h}</h2><div>${ask}</div>${ops ? `<div class="ops">${ops.map((o) => `<span>□ ${o}</span>`).join('')}</div>` : ''}${more ? `<div style="font-size:10pt;color:var(--muted)">${more}</div>` : ''}<div class="line"></div><div class="line"></div>${h.startsWith('5') ? '<div class="line"></div><div class="line"></div>' : ''}</div>`).join('\n')}
<div class="thanks">謝謝您的協助！一週後也請以三個情境帶全班口頭複習：遇到邀請怎麼辦、接送的人怪怪的怎麼辦、朋友要你保密怎麼辦（不記名、不打分）。</div>
`;
  return { name: '導師匿名回饋單', html: htmlPage({ title: `${SHOW_TITLE}｜導師匿名回饋單`, css: FB_CSS, body }), expectPages: 1 };
}
