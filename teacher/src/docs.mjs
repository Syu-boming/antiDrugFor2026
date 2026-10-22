// 講稿以外的教師與學校資料：一頁操作卡、故障一頁卡，並彙整題卡、教案、導覽單、列印檔。
import { BYLINE, SHOW_TITLE, htmlPage, esc, inline, lampSvg } from './common.mjs';
import { TEACHER_TIME, fmtClock, fmtMinSec } from './data.mjs';
import { buildQuizCards } from './quizcards.mjs';
import { buildLesson, buildGuide } from './lesson.mjs';
import { buildPrints } from './print.mjs';
import { backupVideoText } from './teacher_text.mjs';

const md2html = (s) => String(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

/** 各段的授課時鐘（和講稿同一套算法） */
export function segTimes(ctx) {
  const rowsById = Object.fromEntries(ctx.sched.rows.map((r) => [r.id, r]));
  const lastRow = ctx.sched.rows[ctx.sched.rows.length - 1];
  return ctx.merged.segments.map((sg) => {
    const rs = sg.cueIds.map((id) => rowsById[id]).filter(Boolean);
    const start = rs[0].index === 0 ? 0 : rs[0].start - rs[0].pre - TEACHER_TIME.lead;
    const last = rs[rs.length - 1];
    const end = last.leave + (last === lastRow ? 0 : TEACHER_TIME.press);
    const qs = sg.cueIds.map((id) => ctx.merged.cues[ctx.indexOf[id]]).filter((c) => c.kind === 'quiz').map((c) => c.quiz.qid);
    return { id: sg.id, title: sg.title, start, end, qs, firstCue: sg.cueIds[0], lastCue: sg.cueIds[sg.cueIds.length - 1], closingStart: last === lastRow ? last.end : null };
  });
}

/** 八題摘要：題號、指定區、正解 */
export function quizTable(ctx) {
  return Object.keys(ctx.eight).sort().map((qid) => {
    const e = ctx.eight[qid];
    const c = ctx.merged.cues[ctx.indexOf[e.cues.quiz]];
    const zone = /本題看 ([A-D]) 區/.exec(c?.teacherNote ?? '')?.[1] ?? e.zone;
    return { qid, zone, answer: c?.quiz?.answer ?? e.answer, quiz: c?.quiz ?? e, e, cues: e.cues };
  });
}

export function buildAll(ctx) {
  return [
    buildOpCard(ctx),
    buildFaultCard(ctx),
    ...buildQuizCards(ctx),
    buildLesson(ctx, segTimes(ctx)),
    buildGuide(ctx, segTimes(ctx)),
    ...buildPrints(ctx, segTimes(ctx)),
  ];
}

// ───────────────────────────── 一頁操作卡 ─────────────────────────────

const CARD_CSS = `
@page { size: A4 portrait; margin: 9mm 10mm 8mm; }
body { font-size: 11.3pt; line-height: 1.38; }
.top { display: flex; align-items: baseline; justify-content: space-between; border-bottom: 2pt solid var(--accent); padding-bottom: 2pt; margin-bottom: 5pt; }
.top h1 { font-size: 20pt; margin: 0; }
.top .by { font-size: 10pt; color: var(--muted); }
h2 { font-size: 13.5pt; margin: 6pt 0 3pt; display: flex; align-items: center; gap: 5pt; }
h2 .n { display: inline-flex; width: 17pt; height: 17pt; border-radius: 50%; background: var(--ink); color: #fff; font-size: 10.5pt; align-items: center; justify-content: center; }
ol, ul { margin: 0 0 2pt; padding-left: 16pt; }
li { margin: 0.5pt 0; }
table { font-size: 11pt; }
th, td { padding: 2.2pt 5pt; }
.keys td:first-child { font-weight: 800; white-space: nowrap; width: 1%; }
.grid2 { display: grid; grid-template-columns: 1.08fr 1fr; gap: 0 9pt; }
.flow { display: flex; flex-wrap: wrap; align-items: stretch; gap: 3pt; margin: 2pt 0 4pt; }
.flow .st { border: 1.2pt solid var(--ink2); border-radius: 5pt; padding: 3pt 5pt; flex: 1 1 0; min-width: 0; background: #fff; font-size: 10.6pt; line-height: 1.3; }
.flow .st b { display: block; font-size: 11.5pt; }
.flow .ar { align-self: center; font-weight: 800; color: var(--accent); }
.zones { font-size: 11pt; text-align: center; }
.zones th, .zones td { text-align: center; padding: 1.8pt 3pt; }
.zones td.big { font-size: 13pt; font-weight: 800; }
.warn { border: 1.4pt solid var(--ink); border-radius: 5pt; padding: 3pt 7pt; margin-top: 5pt; font-size: 11pt; }
.small { font-size: 9.6pt; color: var(--muted); }
`;

function buildOpCard(ctx) {
  const qs = quizTable(ctx);
  const cps = ctx.merged.cues.filter((c) => c.checkpoint?.escalate);
  const body = `
<div class="top"><h1>${SHOW_TITLE}｜一頁操作卡</h1><span class="by">反毒剪紙劇場｜${BYLINE}</span></div>

<h2><span class="n">1</span>開演前準備（T−60 到 T−15）</h2>
<ol>
<li><b>整個交付資料夾</b>（AntidrugTheater、browser、backup_video、teacher_pdf）用隨身碟<b>複製到筆電本機硬碟</b>（不要從網路下載）。筆電插電、高效能模式，關掉通知與自動更新。</li>
<li>接投影機與場地音響，按 <b>Win＋P</b> 選「<b>延伸</b>」。確認 Windows 的播放裝置是場地音響。</li>
<li>雙擊 <b>AntidrugTheater.exe</b>：投影上出現舞台，筆電上出現深色大字的<b>教師控制台</b>。</li>
<li>控制台按一次「<b>下一步</b>」＝<b>準備播放</b>（同時啟用聲音），畫面停在「${BYLINE}」署名卡。之後不再動滑鼠。</li>
<li>控制台「按鍵測試」逐顆試簡報筆；到最後一排看字、聽聲音。</li>
</ol>
<p class="small">只有一個畫面（同步顯示）時會自動只開舞台，用簡報筆照常演；M 鍵是教師選單。Windows 擋執行檔、當機等狀況看「故障一頁卡」。</p>

<div class="grid2">
<div>
<h2><span class="n">2</span>簡報筆與鍵盤</h2>
<table class="keys"><tbody>
<tr><td>下一頁（PageDown）</td><td><b>下一步</b>（播放中按會被忽略，不跳段）</td></tr>
<tr><td>上一頁（PageUp）</td><td>回上一個停格點</td></tr>
<tr><td>黑屏鍵（句點）</td><td>暫停／繼續</td></tr>
<tr><td>空白鍵</td><td>暫停／繼續（鍵盤備用）</td></tr>
<tr><td>放映鍵（F5／Esc）</td><td>已攔截，不會跳出</td></tr>
<tr><td>R</td><td>重播這一段</td></tr>
<tr><td>M</td><td>教師選單（跳段、畫質、聲畫偏移），<b>會出現在投影上</b>；雙畫面改用控制台「跳到」</td></tr>
</tbody></table>
</div>
<div>
<h2><span class="n">3</span>八題：看哪區、正解</h2>
<table class="zones"><thead><tr><th>題</th>${qs.map((q) => `<th>${q.qid}</th>`).join('')}</tr></thead><tbody>
<tr><td>看哪區</td>${qs.map((q) => `<td class="big">${q.zone}</td>`).join('')}</tr>
<tr><td>正解</td>${qs.map((q) => `<td class="big">${q.answer}</td>`).join('')}</tr>
</tbody></table>
<p class="small">A→B→C→D 各輪兩次。得獎只記區、排、座位，不記姓名；獎品是角色貼紙（非食物）。</p>
<h2><span class="n">4</span>時間落後時</h2>
<ul>
<li>控制台查核點：${cps.map((c) => `${esc(c.checkpoint.label.replace(/ ?點燈收聲後/, ''))}（${fmtClock(c.checkpoint.atMinute * 60)}）落後 ≥ ${fmtMinSec(c.checkpoint.escalate.behindSec).replace(/ 分 /, ':').replace(/ 秒/, '')} → <b>${c.checkpoint.escalate.level} 級</b>`).join('；')}</li>
<li><b>1 級</b>：${esc(ctx.mod.COMPRESSION_TEACHER[1])}</li>
<li><b>2 級</b>：${esc(ctx.mod.COMPRESSION_TEACHER[2])}</li>
<li>超前時：只讓更多學生說理由，不加題。</li>
</ul>
</div>
</div>

<h2><span class="n">5</span>每一題的流程（三個 cue：出題 → 揭答 → 點燈）</h2>
<div class="flow">
<div class="st"><b>① 出題</b>題卡出現，旁白念題目和三個選項（沒有倒數）</div><div class="ar">▶</div>
<div class="st"><b>② 3、2、1 比手指</b>「想一想……3、2、1，一起比！」手舉過頭、不喊、不離座 → 按</div><div class="ar">▶</div>
<div class="st"><b>③ 揭答</b>「正解」印章蓋下 → 回饋、點指定區一位說理由</div><div class="ar">▶</div>
<div class="st"><b>④ 點燈</b>「大家一起，捧燈手——」<b>說完就按</b>，燈亮</div><div class="ar">▶</div>
<div class="st"><b>⑤ 續演</b>做安靜手勢，全場安靜再按</div>
</div>
<p class="small">答錯不羞辱：比例對全班統一說，不點名追問；劇情照常前進。每題都點燈，不看答對率。</p>

<div class="grid2">
<div>
<h2><span class="n">6</span>老師要說話的停格</h2>
<ul>
<li><b>a0_c005</b> 規則＋捧燈手試做（約 75 秒）</li>
<li><b>a1_c003、a2_c001、a4_c013</b> 找找看（各約 30 秒）</li>
<li><b>a3_c004</b> 拒絕句＋口訣動作（約 90 秒）；<b>a7_c002</b> 全場口訣（約 30 秒）</li>
<li>其他停格：畫面停住就按下一步。</li>
</ul>
</div>
<div>
<h2><span class="n">7</span>${ctx.mainLamp ? '主燈與結束' : '結束'}</h2>
<ul>
${ctx.mainLamp ? `<li><b>${ctx.mainLamp.id}</b> 八盞燈全亮、鏡頭後拉時：「最後的主燈，全場一起，捧燈手——」</li>` : ''}
<li>謝幕後按一次：布幕合攏，自動停在「${BYLINE}」署名卡。</li>
<li>教師結語約 45 秒（落後時 30 秒），說明退場發參與小卡。預估總長 <b>${fmtClock(ctx.sched.total)}</b>（上限 38:00）。</li>
</ul>
</div>
</div>
<div class="warn"><b>口訣</b>「不碰、不試；先離開，找大人。」　<b>用語</b>：稱「受到毒品影響的人」；對孩子只說「操偶線」；不念藥名；不問家庭經驗。</div>
`;
  return { name: '一頁操作卡', html: htmlPage({ title: `${SHOW_TITLE}｜一頁操作卡`, css: CARD_CSS, body }), expectPages: 1 };
}

// ───────────────────────────── 故障一頁卡 ─────────────────────────────

const FAULT_CSS = `
@page { size: A4 portrait; margin: 9mm 9mm 8mm; }
body { font-size: 10.8pt; line-height: 1.35; }
.top { display: flex; align-items: baseline; justify-content: space-between; border-bottom: 2pt solid var(--accent); padding-bottom: 2pt; margin-bottom: 5pt; }
.top h1 { font-size: 20pt; margin: 0; }
.top .by { font-size: 10pt; color: var(--muted); }
p { margin: 3pt 0; }
table.fault th { font-size: 11pt; }
table.fault td { padding: 3pt 5pt; }
table.fault td:first-child { font-weight: 800; width: 22%; }
table.fault td:nth-child(2) { width: 40%; }
.path { display: flex; gap: 4pt; align-items: center; margin: 6pt 0 4pt; }
.path .st { border: 1.4pt solid var(--ink); border-radius: 5pt; padding: 3pt 6pt; text-align: center; flex: 1; font-weight: 700; font-size: 10.6pt; line-height: 1.25; }
.path .st small { display: block; font-weight: 400; font-size: 9pt; color: var(--ink2); }
.path .ar { font-weight: 800; color: var(--accent); }
.calm { border: 1.4pt solid var(--ink); border-radius: 5pt; padding: 3pt 7pt; font-size: 10.8pt; margin: 4pt 0; }
.small { font-size: 9.3pt; color: var(--muted); }
`;

function buildFaultCard(ctx) {
  const bv = backupVideoText(ctx.backup);
  const rows = [
    ['簡報筆按了沒反應', '看控制台上方「焦點」：點一下控制台（或舞台）任何地方取回焦點。檢查 USB 接收器與電池。', '用筆電鍵盤：PageDown 或 →＝下一步、空白鍵＝暫停；或按控制台的「下一步」。換備用簡報筆。鍵碼不同時用控制台「按鍵測試」設定。'],
    ['沒有聲音', '看控制台「聲音」狀態。檢查 Windows 播放裝置（接投影機後常被改成 HDMI）、音量、場地擴音與音源線。', '按黑屏鍵暫停再繼續。第一個字被吃掉：教師選單（M）「開頭靜音」改 200 或 400。仍沒聲音：<b>老師照字幕與講稿講述，劇情照常進行</b>。'],
    ['畫面卡頓、不順', '等這一段播完停住。在停格時按 M → 畫質「B 級」或「鎖 30 fps」，再按 M 關掉選單。', `關掉其他程式、插電、高效能模式。仍卡：改用${bv.label}${bv.ready ? '（下方）' : ''}或紙本題卡。`],
    ['出現「畫面暫停」或「顯示卡連線中斷」', '按一次「下一步」，重新建立畫面，回到目前的停格點。', '重建失敗：關掉程式重開，用控制台「跳到」選講稿上的 cue 編號、按「前往」。授課時鐘會保留。'],
    ['畫面黑掉、被重新整理或程式關掉', '不用慌：舞台回到「準備播放」畫面，不會自己出聲。按「準備播放」，再用控制台「跳到」回到剛才的 cue。', '程式關掉了：重新雙擊 AntidrugTheater.exe，同上跳回。'],
    ['螢幕被關掉或系統休眠', '喚醒後畫面停在原處，按黑屏鍵（或下一步）繼續，不會跳段。', '—'],
    ['只有一個畫面、控制台被投影出去', '按 Win＋P 選「延伸」。', '控制台會提示改用單一舞台視窗：只用舞台和簡報筆演出，看紙本講稿。'],
    ['控制台顯示「舞台：未連線」', '點一下舞台視窗，等 2–3 秒。', '只用舞台視窗演出（M 鍵選單可跳段），看紙本講稿與 cue 編號。'],
    ['投影機沒畫面或故障', '檢查訊號線與投影機的輸入來源；Win＋P 重選「延伸」。', '<b>改用紙本題卡完成八題</b>（題卡_學生版.pdf，可放大印成 A3），老師照講稿說故事。'],
    ['畫面寫「無法開始」或「缺 N 句配音」', '<b>不要再按</b>。關掉程式，把<b>整個交付資料夾</b>重新複製到本機再開。', '改開<b>瀏覽器版</b>或備援影片。'],
    ['Windows 擋執行檔（「Windows 已保護您的電腦」）', '按「其他資訊」→「仍要執行」（學校允許時）。', '學校電腦禁止執行時，請資訊組協助，或改用<b>瀏覽器版</b>（下方）。'],
  ];
  const body = `
<div class="top"><h1>${SHOW_TITLE}｜故障一頁卡</h1><span class="by">反毒剪紙劇場｜${BYLINE}</span></div>
<div class="calm">先深呼吸：畫面一定停在某個停格點等老師，<b>不會自己亂跳</b>；播放中多按的鍵會被忽略。學生照常坐著，老師可以先帶大家說一次口訣「不碰、不試；先離開，找大人。」</div>
<table class="fault"><thead><tr><th>症狀</th><th>第一個動作</th><th>還不行（退路）</th></tr></thead><tbody>
${rows.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('\n')}
</tbody></table>
<h2 style="font-size:13pt;margin:7pt 0 2pt">退路順序（一層不行就換下一層）</h2>
<div class="path">
<div class="st">Windows 可攜版<small>AntidrugTheater.exe</small></div><div class="ar">▶</div>
<div class="st">瀏覽器版<small>Chrome／Edge 開 browser 資料夾</small></div><div class="ar">▶</div>
<div class="st">${bv.label}<small>${bv.step}</small></div><div class="ar">▶</div>
<div class="st">紙本題卡＋講稿<small>老師講故事，八題照常</small></div>
</div>
<p><b>瀏覽器版怎麼開</b>：用 Chrome 或 Edge 開啟 <code>browser\\index.html</code>（不用加參數，預設就是全劇），按「準備播放」，用簡報筆操作。要雙畫面：開 <code>browser\\console.html</code>，按「開啟舞台視窗」，把舞台拖到投影畫面，在舞台上按一次「準備播放」。不需要網路、不用安裝。</p>
<p><b>${bv.ready ? '備援影片怎麼播' : bv.label}</b>：${md2html(bv.short)}</p>
<p class="small">代理老師照「一頁操作卡」與本卡就能演出。正解依序 ${quizTable(ctx).map((q) => q.answer).join('、')}；看 ${quizTable(ctx).map((q) => q.zone).join('')} 區。完全離線。</p>
`;
  return { name: '故障一頁卡', html: htmlPage({ title: `${SHOW_TITLE}｜故障一頁卡`, css: FAULT_CSS, body }), expectPages: 1 };
}
