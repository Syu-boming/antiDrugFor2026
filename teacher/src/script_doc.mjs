// 教師講稿（teacher/教師講稿.md＋html/教師講稿.html）：全部依 cue 資料、時間軸與八題定稿產生。
import { BYLINE, SHOW_TITLE, toMarkdown, toHtml, htmlPage, zh } from './common.mjs';
import { ONE_LINERS, quizLine } from './oneliners.mjs';
import { TEACHER_TIME, fmtClock, fmtMinSec } from './data.mjs';
import { STAFF_LINE, backupVideoText } from './teacher_text.mjs';

const KEY_NEXT = '下一步';

/** 依題號找八題定稿與 cue 的題目資料 */
function quizFor(ctx, cue) {
  const q = cue.quiz ?? null;
  if (q) return { ...q, ...(ctx.eight[q.qid] ?? {}), cueQuiz: q };
  // 揭答、點燈沿用前一題
  const tl = ctx.tl0[ctx.indexOf[cue.id]];
  if (tl?.quiz) return { ...tl.quiz, ...(ctx.eight[tl.quiz.qid] ?? {}), cueQuiz: tl.quiz };
  return null;
}

function zoneOf(cue, q) {
  const m = /本題看 ([A-D]) 區/.exec(cue.teacherNote ?? '');
  return m ? m[1] : q?.zone ?? null;
}

function lastLine(cue) {
  const ls = cue.lines ?? [];
  if (!ls.length) return '';
  const t = ls[ls.length - 1].text.replace(/\s+/g, '');
  return t.length > 26 ? `${t.slice(0, 26)}…` : t;
}

const GENERIC = '播完停格，等老師按下一步。';
/** 教師欄寫的是畫面說明（給製作與驗收看），老師不用說話的 cue */
const DESCRIPTIVE = new Set(['a2_c002', 'a2_c004', 'a2_c008', 'a2_c012', 'a2_c013']);

/** 老師說／做（精簡版，表格用）＋按鍵 */
function teacherCell(ctx, cue, row) {
  const n = cue.teacherNote ?? '';
  const q = ['quiz', 'reveal', 'lamp'].includes(cue.kind) ? quizFor(ctx, cue) : null;
  let say = '', key = KEY_NEXT;
  const extra = [];
  switch (cue.kind) {
    case 'title':
      if (row.index === 0) { say = '學生坐定，問候一句（約 30 秒）。署名卡待機，沒有音樂。'; key = '下一步＝開演'; }
      else { say = '**教師結語**（約 45 秒，講法見第五節）。停在署名卡，不再按。'; key = '不按'; }
      break;
    case 'curtain':
      if (cue.autoAdvance) { say = '（不用說話）布幕合攏後會自動出現署名卡。'; key = '自動接下一格'; }
      else { say = '（不用說話）布幕打開、劇名出現後畫面停住，再按。'; }
      break;
    case 'quiz': {
      const z = zoneOf(cue, q);
      say = `等旁白念完三個選項，說〔照念〕「想一想……3、2、1，一起比！」看 **${z} 區**。全班比完再按。`;
      key = '下一步＝揭答';
      break;
    }
    case 'reveal': {
      const z = zoneOf(cue, q);
      say = `**正解 ${q?.answer}**。回饋（第六節 ${q?.qid}）→ 從 ${z} 區比 ${q?.answer} 的同學中點一位說一句理由 → 協助教師記錄區、排、座位 → 說「${/最後一盞/.test(n) ? '最後一盞，' : '大家一起，'}捧燈手——」**說完就按**，不等全班做好。`;
      key = '下一步＝點燈';
      break;
    }
    case 'lamp':
      say = '燈亮後做安靜手勢，等全場安靜再按。';
      break;
    default:
      if (ctx.mainLamp && cue.id === ctx.mainLamp.id) say = mainLampSay(ctx.mainLamp);
      else if (n.trim() === GENERIC || !n.trim() || /^播完停格[^。]*等老師按下一步。?$/.test(n.trim())) say = '（不用說話）畫面停住後按。';
      else if (/^找找看 (\d)/.test(n)) say = `**${/^找找看 \d（[^）]*）/.exec(n)?.[0] ?? '找找看'}**：點一位安靜舉手的同學（講法見第五節）。`;
      else if (cue.id === 'a0_c005' || /今天有八題/.test(n)) say = '**規則說明＋捧燈手試做**（約 75 秒，講法見第五節）。全班安靜後再按。';
      else if (/練習/.test(n) && /口訣/.test(n) && /約 90 秒/.test(n)) say = '**全班練習**：拒絕句一次、口訣加動作一次（約 90 秒，講法見第五節）。安靜手勢後再按。';
      else if (/口訣/.test(n) && /約 30 秒/.test(n)) say = '**帶全場說口訣、做動作一次**（約 30 秒）。做安靜手勢後再按。';
      else if (DESCRIPTIVE.has(cue.id)) say = '（不用說話）畫面停住後按。';
      else {
        // 認不得的教師欄：照原文放進來（不讓新的教師指示被當成「不用說話」），並在報告提醒
        say = n.length > 120 ? `${n.slice(0, 120)}…（全文見 cue 教師欄）` : n;
        ctx.warnings.push(`${cue.id} 的教師欄沒有對應的講稿樣式，已照原文放入講稿：「${n.slice(0, 40)}…」`);
      }
  }
  // 可選補充（劇本的〔教師〕行，cue 檔沒有）
  for (const l of ctx.scriptTeacher[cue.id] ?? []) if (/可選/.test(l)) extra.push('（可選，預設不講）進度超前時講補充（約 20 秒，見第五節）。');
  if (cue.checkpoint && cue.checkpoint.atMinute > 0 && cue.checkpoint.escalate) {
    const e = cue.checkpoint.escalate;
    extra.push(`**查核點**：看控制台落差；目標 ${fmtClock(cue.checkpoint.atMinute * 60)}，落後 ≥ ${fmtMinSec(e.behindSec)} → 按「${e.level} 級」。`);
  }
  // 壓縮會略過的句子
  const sk = (cue.lines ?? []).filter((l) => l.skippableWhenBehind).map((l) => l.id.slice(-2));
  if (sk.length) extra.push(`〔1 級〕略過第 ${sk.join('、')} 句。`);
  if (cue.compression === 2 && cue.level2) extra.push('〔2 級〕改短版。');
  if (cue.compression === 1) extra.push('〔1 級〕整段略過。');
  return { say: [say, ...extra].join('\n'), key };
}

/** 主燈亮起那一段的「老師說／做」 */
function mainLampSay(L) {
  return `**主燈亮起，全場捧燈手**（見 5.6）：${L.cueText}，說〔照念〕「最後的主燈，全場一起，捧燈手——」，主燈在大家捧手時亮起（約第 ${Math.round(L.at0)} 秒）。主燈亮後做安靜手勢；畫面停住後按。`;
}

/**
 * 主燈亮起的時間（高潮 cue）：用該 cue 的點燈音效 sfx_lamp_on 在時間軸上的位置；
 * 老師提前約 2 秒開口，讓「捧燈手——」說完時主燈剛好亮起。
 */
export function mainLampInfo(ctx) {
  const cue = ctx.merged.cues.find((c) => c.id === 'a6_c007') ?? ctx.merged.cues.find((c) => c.kind === 'scene' && /主燈/.test(c.title ?? ''));
  if (!cue) return null;
  const i = ctx.indexOf[cue.id];
  const lampAt = (lv) => {
    const t = ctx.tl[lv]?.[i];
    if (!t || t.skipped) return null;
    const s = t.sfx.find((x) => x.id === 'sfx_lamp_on');
    return s ? s.at : null;
  };
  const at0 = lampAt(0);
  if (at0 === null) { ctx.warnings.push(`${cue.id} 找不到主燈的點燈音效（sfx_lamp_on），講稿的主燈捧燈手沒有時間`); return null; }
  const at1 = lampAt(1);
  const t0 = ctx.tl[0][i];
  const clean = (x) => x.replace(/\s+/g, '');
  const before = [...t0.lines].reverse().find((l) => l.end <= at0 + 0.05);
  const after = t0.lines.find((l) => l.start >= at0 - 0.05);
  const callAt0 = Math.max(0, at0 - 2);
  const cueText = `${before ? `${before.line.speaker ?? ''}說完「${clean(before.line.text)}」${before.line.skippableWhenBehind ? '（1 級時這句略過）' : ''}、` : ''}鏡頭往後拉、看到台口八盞燈都亮著時（約播放第 ${Math.round(callAt0)} 秒）`;
  return { id: cue.id, at0, at1, callAt0, cueText, afterText: after ? clean(after.line.text) : '' };
}

function screenCell(ctx, cue) {
  if (['quiz', 'reveal', 'lamp'].includes(cue.kind)) {
    const q = quizFor(ctx, cue);
    return q ? quizLine(cue.kind, q) : cue.title;
  }
  let s = ONE_LINERS[cue.id];
  if (!s) {
    const beat = (cue.storyboard?.beat ?? cue.title ?? '').replace(/\*\*/g, '').split(/[；;]/)[0];
    s = `${beat}`;
    ctx.warnings.push(`${cue.id} 沒有一句話說明，改用劇本節拍：「${s}」`);
  }
  const last = lastLine(cue);
  return last && !['title', 'curtain'].includes(cue.kind) ? `${s}\n停在：「${last}」` : s;
}

// ───────────────────────────── 主程式 ─────────────────────────────

export function buildTeacherScript(ctx) {
  const { merged, sched, eight } = ctx;
  const B = [];
  const segs = merged.segments;
  const rowsById = Object.fromEntries(sched.rows.map((r) => [r.id, r]));
  const total = sched.total;
  const playSum = sched.rows.reduce((n, r) => n + r.dur, 0);
  const teacherSum = sched.rows.reduce((n, r) => n + r.after, 0) + TEACHER_TIME.greeting;
  const overhead = total - playSum - teacherSum;
  const LIMIT = 38 * 60;

  B.push({ h: 1, text: `${SHOW_TITLE}｜教師講稿` });
  B.push({ p: `反毒剪紙劇場《${SHOW_TITLE}》｜${BYLINE}`, cls: 'byline' });

  // 一、怎麼用
  B.push({ h: 2, text: '一、這份講稿怎麼用' });
  B.push({ ul: [
    '每一列是一個 cue（一段畫面）。**按鍵**欄的「下一步」＝簡報筆的「下一頁」鍵（PageDown）。',
    `**授課時鐘**：00:00＝老師站上台（署名卡待機，問候約 30 秒）；00:30 按第一下開演。教師控制台的「授課時鐘」也是從開演那一下的 00:30 起跳。`,
    '每段播完都會**停格等老師**，不會自己往下播。**播放中按下一步會被忽略**，不會跳段；不小心多按也沒關係。',
    '〔照念〕的句子可以照念，也可以換成自己的話。「教師背景」只給老師看，不念給學生聽。',
    '時間落後時看第七節：控制台會在查核點提示要不要啟用 1 級或 2 級。',
  ] });

  // 二、時間總表
  B.push({ h: 2, text: '二、時間總表' });
  const segRows = [];
  for (const sg of segs) {
    const rs = sg.cueIds.map((id) => rowsById[id]).filter(Boolean);
    if (!rs.length) continue;
    const start = rs[0].index === 0 ? 0 : rs[0].start - rs[0].pre - TEACHER_TIME.lead;
    const last = rs[rs.length - 1];
    const end = last.leave + (last === sched.rows[sched.rows.length - 1] ? 0 : TEACHER_TIME.press);
    const play = rs.reduce((n, r) => n + r.dur, 0);
    const teach = rs.reduce((n, r) => n + r.after, 0) + (rs[0].index === 0 ? TEACHER_TIME.greeting : 0);
    const qs = sg.cueIds.map((id) => merged.cues[ctx.indexOf[id]]).filter((c) => c.kind === 'quiz').map((c) => c.quiz.qid);
    segRows.push([sg.title, `${fmtClock(start)}–${fmtClock(end)}`, fmtMinSec(play), fmtMinSec(teach), qs.join('、') || '—']);
  }
  B.push({ table: { head: ['段落', '授課時鐘', '預錄播放', '教師時間', '題目'], rows: segRows, cls: 'tbl-time', widths: ['34%', '18%', '16%', '16%', '16%'] } });
  const ok = total <= LIMIT;
  B.push({ p: `**預估總長 ${fmtClock(total)}**（${ok ? '在' : '超過'} 38 分鐘上限${ok ? `內，緩衝 ${fmtMinSec(LIMIT - total)}` : ` ${fmtMinSec(total - LIMIT)}`}）＝預錄播放 ${fmtMinSec(playSum)}＋教師時間 ${fmtMinSec(teacherSum)}＋按鍵與換景 ${fmtMinSec(overhead)}。38–40 分不排內容，留給下課前的餘裕。` });
  // 查核點一律用 cue 的 checkpoint.atMinute（控制台顯示的就是 atMinute×60）
  const cpRows = merged.cues.filter((c) => c.checkpoint && c.checkpoint.atMinute > 0).map((c) => {
    const esc = c.checkpoint.escalate;
    return [c.checkpoint.label, c.id, fmtClock(c.checkpoint.atMinute * 60), esc ? `落後 ≥ ${fmtMinSec(esc.behindSec)} → ${esc.level} 級` : '—'];
  });
  B.push({ h: 3, text: '查核點（控制台會顯示落差）' });
  B.push({ table: { head: ['查核點', 'cue', '控制台目標', '落後多少要壓縮'], rows: cpRows, cls: 'tbl-cp', widths: ['34%', '14%', '18%', '34%'] } });
  B.push({ note: '控制台目標和控制台畫面上顯示的時間相同。照本講稿的節奏走，到查核點時落差應該在幾十秒內；只要沒達到右欄門檻就不用壓縮。' });
  const v = ctx.variants;
  B.push({ h: 3, text: '其他情境' });
  B.push({ table: { head: ['情境', '預估總長', '說明'], rows: [
    ['預設（0 級）', fmtClock(total), '本講稿的時間'],
    ['從頭啟用 1 級', fmtClock(v.l1.total), '略過標示的句子；學生說理由縮成一句、找找看 15 秒'],
    ['從頭啟用 2 級', fmtClock(v.l2.total), '再加上四季、三張大圖、謝幕短版；教師結語 30 秒'],
    ['現場拉長，不壓縮', fmtClock(v.stress.total), `每題 ${100} 秒、找找看各 45 秒、練習 120 秒、規則 90 秒`],
    ['現場拉長，照查核點壓縮', fmtClock(v.stressDyn.total), v.stressDyn.events.filter((e) => e.trigger).map((e) => `${e.cueId.replace(/_c\d+$/, '')} 查核點落後 ${fmtMinSec(e.behind)} → ${e.level} 級`).join('；') || '沒有觸發'],
  ], cls: 'tbl-var', widths: ['26%', '14%', '60%'] } });

  // 三、開演前
  B.push({ h: 2, text: '三、開演前（T−15 到開演）' });
  B.push({ ul: [
    '控制台按一次「下一步」（或「準備播放」）＝啟用聲音，畫面停在署名卡。之後不再動滑鼠。',
    '確認：投影畫面是舞台、筆電是控制台；控制台上方「舞台：已連線」「焦點」正常；聲音從場地喇叭出來。',
    `**人力**：${STAFF_LINE}（此時獎品改在課後發）。四區導師維持秩序、照看特殊需求學生。`,
    '學生入場、依區就座（四區 A、B、C、D）。協助教師拿好得獎座位記錄單與獎品（貼紙，不用食物）。',
    '「故障一頁卡」放在手邊；演出出問題時照第十節的退路順序處理。',
    '鐘響、學生坐定：問候一句，接著按下一步開演（授課時鐘從 00:30 起跳）。',
  ] });
  B.push({ quote: '〔照念・可選〕各位小朋友好！今天我們要看一齣剪紙劇場，名字叫《紙燈節》。等一下會有八個問題，要請大家一起幫忙。準備好了嗎？我們開始！' });

  // 四、逐 cue 講稿
  B.push({ h: 2, text: '四、逐 cue 講稿', cls: 'newpage' });
  B.push({ note: '時鐘＝這段開始播放的授課時鐘（預估）；秒數＝預錄長度。「停在」＝這段最後一句字幕，看到它播完就可以準備按。' });
  for (const sg of segs) {
    const rs = sg.cueIds.map((id) => rowsById[id]).filter(Boolean);
    if (!rs.length) continue;
    B.push({ h: 3, text: `${sg.title}（${sg.cueIds[0]}–${sg.cueIds[sg.cueIds.length - 1]}）` });
    const rows = [];
    const rowCls = [];
    for (const r of rs) {
      const cue = merged.cues[r.index];
      const t = teacherCell(ctx, cue, r);
      const clock = r.index === 0 ? '00:00' : `${fmtClock(r.start)}\n${Math.round(r.dur)} 秒`;
      rows.push([cue.id, clock, screenCell(ctx, cue), t.say, t.key]);
      rowCls.push(['quiz', 'reveal', 'lamp'].includes(cue.kind) ? 'row-quiz' : (t.say.startsWith('（不用說話）') ? 'row-plain' : 'row-talk'));
    }
    B.push({ table: { head: ['cue', '時鐘', '畫面', '老師說／做', '按鍵'], rows, rowCls, cls: 'tbl-cues', widths: ['10%', '8%', '38%', '34%', '10%'] } });
  }

  // 五、互動講法全文
  B.push({ h: 2, text: '五、互動講法全文' });
  const note = (id) => merged.cues[ctx.indexOf[id]]?.teacherNote ?? '';
  const at = (id) => (rowsById[id] ? `授課時鐘約 ${fmtClock(rowsById[id].end)}` : '');
  B.push({ h: 3, text: `5.1 規則說明與捧燈手試做（a0_c005 播完後，約 75 秒；${at('a0_c005')}）` });
  const rules = note('a0_c005').replace(/^（約 1 分鐘）/, '');
  const [rSay, rDo] = splitDo(rules);
  B.push({ quote: `〔照念〕${rSay}` });
  if (rDo.length) B.push({ ul: rDo });
  B.push({ ul: [
    '**安靜手勢**：老師自己固定一個手勢（例如舉起一隻手、另一手食指放在嘴前），整節課都用同一個。題卡出現時折折的「收摺」音效也是收聲訊號。',
    '**捧燈手**：雙手在胸前捧成一盞燈。正式作答時，老師說完「捧燈手——」就按下一步，燈在大家捧手的同時亮起；燈亮後做安靜手勢。',
    '**作答**：手指比 1、2、3，手舉過頭；不用喊、不離開座位。系統不辨識手勢，由老師口頭判定。',
  ] });
  for (const [id, n] of [['a1_c003', 1], ['a2_c001', 2], ['a4_c013', 3]]) {
    B.push({ h: 3, text: `5.${n + 1} 找找看 ${n}（${id} 播完後，約 30 秒，不計獎；${at(id)}）` });
    B.push(...findBlocks(note(id)));
  }
  B.push({ h: 3, text: `5.5 拒絕句與口訣練習（a3_c004 播完後，約 90 秒，全場只練這一次；${at('a3_c004')}）` });
  const prac = note('a3_c004').split('\n').filter((l) => l.trim() && !/^練習（/.test(l));
  B.push({ ol: prac.map((l) => l.replace(/^[①②③④⑤]/, '').trim()) });
  B.push({ table: { head: ['口訣', '動作（坐著做，不離座）'], rows: [
    ['不碰', '雙手在胸前交叉。'], ['不試', '手掌左右搖。'], ['先離開', '手指向門口方向。'], ['找大人', '手掌放在額前，左右張望（和作答時的舉手不一樣）。'],
  ], cls: 'tbl-moves', widths: ['20%', '80%'] } });
  if (ctx.mainLamp) {
    const L = ctx.mainLamp;
    B.push({ h: 3, text: `5.6 主燈亮起：全場一起捧燈手（${L.id} 播放中，不另花時間；${at(L.id) ? `授課時鐘約 ${fmtClock(rowsById[L.id].start + L.callAt0)}` : ''}）` });
    B.push({ p: `八盞燈點完後，${L.id} 是全劇的高潮：八盞燈的光流進廣場，主燈亮起。這是全場最後一次捧燈手，讓大家的動作和主燈亮起同步。` });
    B.push({ quote: '〔照念〕最後的主燈，全場一起，捧燈手——' });
    B.push({ ul: [
      `**什麼時候說**：${L.cueText}。說完不用按鍵，主燈會在大家捧手時亮起（播放約第 ${Math.round(L.at0)} 秒${L.at1 !== null && Math.abs(L.at1 - L.at0) >= 1 ? `；1 級約第 ${Math.round(L.at1)} 秒` : ''}）${L.afterText ? `，接著旁白說「${L.afterText}」` : '。'}`,
      '主燈亮後放下手、做安靜手勢，讓大家聽完旁白；這一段播完停格再按下一步。',
      '備援影片時也一樣：看到八盞燈都亮、鏡頭往後拉，就帶全場捧燈手。紙本時，說完第八盞燈後接著說這一句，全場一起捧燈手。',
    ] });
  }
  const opt = (ctx.scriptTeacher.a2_c004 ?? []).find((l) => /可選/.test(l));
  if (opt) {
    B.push({ h: 3, text: '5.7 可選補充（a2_c004 播完後，約 20 秒；預設不講，進度超前時才講）' });
    const said = /「(.+)」/.exec(opt)?.[1] ?? opt;
    B.push({ quote: `〔照念〕${said}` });
    B.push({ note: '只講這一次，不延伸說明成分、用法或新聞細節；不念任何藥名。' });
  }
  B.push({ h: 3, text: `5.8 全場一起做口訣（a7_c002 播完後，約 30 秒；${at('a7_c002')}）` });
  B.push({ quote: '〔照念〕我們一起說，一起做：不碰——不試——先離開——找大人！' });
  B.push({ p: '帶全場說一次、做動作一次。做完做安靜手勢，再按下一步。' });
  B.push({ h: 3, text: `5.9 教師結語（停在片尾署名卡後，約 45 秒；2 級時縮成 30 秒）` });
  B.push({ quote: '〔照念〕謝謝大家，今天一起幫小燈鎮點亮了八盞燈。我們記住今天的口訣：不碰、不試；先離開，找大人。遇到不明的東西、覺得不對勁的時候，先保護自己，去找可以信任的大人。等一下退場的時候，導師會發給每個人一張參與小卡，上面有今天的口訣。' });
  B.push({ ul: [
    '2 級（縮成 30 秒）：只說第一、二句和發小卡。落後很多時只說一句「謝謝大家」，小卡由導師在門口發。',
    '如有長官致詞，建議放在署名卡之後，不要壓縮學生作答時間。',
    '停在署名卡，不再按鍵（再按也不會動作）。',
  ] });

  // 六、八題
  B.push({ h: 2, text: '六、八題（正解、指定區與回饋）', cls: 'newpage' });
  B.push({ note: '題目文字和演出的題卡、紙本題卡一字不差（產生時已自動比對）。「對全班說」約 12 秒，只講這一題的重點，不先講後面的劇情。「若不少人選了」只在揭答後對全班統一說，不點名、不追問是誰選的。答錯不羞辱，劇情照常前進。' });
  for (const qid of Object.keys(eight).sort()) {
    const e = eight[qid];
    const quizCue = merged.cues[ctx.indexOf[e.cues.quiz]];
    const cq = quizCue?.quiz ?? e;
    B.push({ h: 3, text: `${qid}｜${e.topic.replace(/[？?]$/, '')}？　正解 ${cq.answer}｜看 ${zoneOf(quizCue, e) ?? e.zone} 區`, cls: 'qh' });
    B.push({ p: `cue：出題 ${e.cues.quiz}｜揭答 ${e.cues.reveal}｜點燈 ${e.cues.lamp}${rowsById[e.cues.quiz] ? `｜授課時鐘約 ${fmtClock(rowsById[e.cues.quiz].start)}` : ''}`, cls: 'qmeta' });
    B.push({ p: `**題目**：${cq.question}` });
    B.push({ ol: cq.options.map((o, i) => (i + 1 === cq.answer ? `**${o}　〔正解〕**` : o)), cls: 'qopts' });
    B.push({ p: `**揭答旁白**：${e.revealLine}` });
    B.push({ quote: `〔照念〕${e.say}` });
    if (e.ifMany.length) B.push({ ul: e.ifMany.map((x) => `**若不少人選了 ${x.choice}**：「${x.text}」`) });
    if (e.background.length) { B.push({ p: '**教師背景**（不念給學生聽）', cls: 'bg-h' }); B.push({ ul: e.background, cls: 'bg' }); }
  }

  // 七、查核點與壓縮
  B.push({ h: 2, text: '七、時間落後時：查核點與壓縮' });
  B.push({ ul: [
    '**看哪裡**：控制台右邊「查核點與時間」。每個查核點顯示目標時間、實際時間與落差；達到門檻時，控制台會提示建議級別。',
    '**怎麼啟用**：按控制台的「1 級」或「2 級」。播放中按下去，會等這一段播完才套用；之後一直維持。',
    '**門檻**：' + ctx.checkpointRules.join('；') + '。',
    '**超前時**：只讓更多學生說理由，不加題；可以講 a2_c004 後的可選補充。',
  ] });
  B.push({ h: 3, text: '1 級：落後一點時' });
  B.push({ p: `**畫面**（自動）：${ctx.comp.l1Anim.length ? ctx.comp.l1Anim.join('；') : '沒有可略過的句子'}。從頭套用約省 ${fmtMinSec(ctx.comp.l1Saved)}。` });
  B.push({ p: `**老師**：${ctx.mod.COMPRESSION_TEACHER[1]}` });
  B.push({ h: 3, text: '2 級：落後較多時' });
  B.push({ p: `**畫面**（自動，1 級也一併套用）：${ctx.comp.l2Anim.join('；')}。比 1 級再省約 ${fmtMinSec(ctx.comp.l2Saved)}。` });
  B.push({ p: `**老師**：${ctx.mod.COMPRESSION_TEACHER[2]}` });
  B.push({ h: 3, text: '絕對不刪' });
  B.push({ p: '八題完整流程（出題 → 揭答 → 點燈）、兩句必要旁白（a2_c004、a2_c008）、操偶線段（a2_c002–a2_c004）、道路段（a4_c002–a4_c004）、求助與復原轉場（a5_c005–a5_c008、a6_c008 至少短版）、結尾的 119 求助訊息、片頭片尾與署名卡。' });
  B.push({ p: '若到 Q8 查核點已落後超過約 3 分 30 秒（1、2 級都用上仍會超過 38 分鐘）：教師結語只說一句，參與小卡改由導師在門口發。' });

  // 八、輪區表
  B.push({ h: 2, text: '八、輪區表與得獎記錄' });
  B.push({ table: { head: ['題', '看哪一區', '正解', '揭答 cue', '得獎座位（區／排／號）'], rows: Object.keys(eight).sort().map((qid) => {
    const e = eight[qid];
    const qc = merged.cues[ctx.indexOf[e.cues.quiz]];
    return [qid, `${zoneOf(qc, e) ?? e.zone} 區`, `${qc?.quiz?.answer ?? e.answer}`, e.cues.reveal, ''];
  }), cls: 'tbl-zone', widths: ['10%', '16%', '10%', '18%', '46%'] } });
  B.push({ note: '只記區、排、座位，不記姓名，避免同一人重複得獎。獎品是角色貼紙（非食物）；退場時每人一張參與小卡。' });

  // 九、安全提醒
  B.push({ h: 2, text: '九、給老師的安全提醒' });
  B.push({ ul: [
    '**用語**：稱「受到毒品影響的人」「需要幫助的人」，不說「毒蟲」，也不把人叫成「喪屍」。對孩子只說「操偶線」；物品說「喪屍煙彈」「電子煙」。不念藥名，不講法規分級與刑度。',
    '**操偶線命名前**（a2_c004 之前），只說「細細的線」「一條線」。',
    '**不嘲笑症狀**：不模仿站不穩或叫不醒的樣子，也不拿叔叔的動作開玩笑。',
    '**答錯不羞辱**：比例對全班統一說，不針對個人，不說「答錯會害人出事」。',
    '**不探詢家庭**：不問「誰家有人……」。學生主動透露時，簡短回應「謝謝你願意說，下課老師再跟你聊」，不公開追問；課後由導師帶到安靜處個別關心，**當天**告知輔導室與學務處，依《兒童及少年福利與權益保障法》第 53、54 條與學校流程完成責任通報（是否通報不由個人判斷後擱置）。',
    '**毒駕段**：只要求孩子「先不上車、回到安全的地方找大人」，不要求靠近車輛、查證或勸阻駕駛。若學生問「已經在車上怎麼辦」：「這個問題很好，下課可以和家人、老師一起討論；今天先記住：還沒上車，就先不上車、找大人。」',
    '**光敏與聲音**：課前私下向導師或校護確認是否有學生有光敏性癲癇病史或對聲音敏感，不在班上詢問。畫面不閃爍、沒有突發巨響。',
    '**拍照**：以背影、舞台與老師為主，避開可辨識的臉，不用閃光燈；未經同意不上網。',
  ] });

  // 十、故障時
  const bv = backupVideoText(ctx.backup);
  B.push({ h: 2, text: '十、故障時的退路' });
  B.push({ p: '先照「故障一頁卡」依症狀處理；一層不行再換下一層。畫面一定停在某個停格點等老師，不會自己亂跳。' });
  B.push({ ol: [
    '**Windows 可攜版**（AntidrugTheater.exe）：關掉重開，用控制台「跳到」回到講稿上的 cue 編號。',
    '**瀏覽器版**（browser 資料夾，用 Chrome 或 Edge 開）：開法見故障一頁卡。',
    `**${bv.label}**：${bv.how}`,
    '**紙本題卡＋講稿**：老師照本講稿說故事，舉起學生版題卡（可放大印成 A3）完成八題，全班照常比 1、2、3、一起做捧燈手。',
  ] });

  // 附錄
  B.push({ h: 2, text: '附錄：時間怎麼算' });
  const T = TEACHER_TIME;
  B.push({ ul: [
    `**預錄播放**：用演出程式自己的時間計算方式與實際配音長度算出，每段＝最後一句＋停留、所有動畫結束、最短長度三者取大。全劇 0 級 ${fmtMinSec(playSum)}。`,
    `**每題教師時間**：想＋全班比 ${T.quiz.think} 秒、點一位說理由 ${T.quiz.reason} 秒、回饋 ${T.quiz.feedback} 秒、說「捧燈手——」並按 ${T.quiz.lampCall} 秒、燈亮後收聲 ${T.quiz.quiet} 秒。`,
    `**其他教師時間**：課前問候 ${T.greeting} 秒、規則與捧燈手試做 ${T.after.a0_c005.sec} 秒、找找看 3 次各 ${T.after.a1_c003.sec} 秒、練習 ${T.after.a3_c004.sec} 秒、全場口訣 ${T.after.a7_c002.sec} 秒、教師結語 ${T.after.a8_c003.sec} 秒；a2_c004 可選補充預設不講。`,
    `**按鍵與換景**：老師每按一次約 ${T.press} 秒；換景時先漸暗 ${ctx.mod.PREROLL_SEC} 秒；每段開頭的音訊延遲約 ${T.lead} 秒。`,
    '發獎與記錄座位由協助教師在下一段劇情播放時進行，不另計時間。',
    `**主燈捧燈手**（${ctx.mainLamp?.id ?? 'a6_c007'}）在播放中進行，不另計時間。`,
  ] });
  const qRows = Object.keys(eight).sort().map((qid) => {
    const e = eight[qid];
    const a = rowsById[e.cues.quiz], b = rowsById[e.cues.reveal], c = rowsById[e.cues.lamp];
    if (!a || !b || !c) return [qid, '', '', '', '', ''];
    const teach = a.after + b.after + c.after;
    const tot = c.leave + T.press - (a.start - a.pre - T.lead);
    return [qid, `${a.dur.toFixed(1)}`, `${b.dur.toFixed(1)}`, `${c.dur.toFixed(1)}`, `${teach}`, `${Math.round(tot)}`];
  });
  B.push({ table: { head: ['題', '出題 cue（秒）', '揭答 cue（秒）', '點燈 cue（秒）', '教師（秒）', '每題合計（秒）'], rows: qRows, cls: 'tbl-q' } });

  B.push({ note: `印製版本：${ctx.generatedAt}（版本碼 ${ctx.cueHash}）。版本碼和演出資料對應；演出內容改過之後講稿會重新產生，版本碼也會跟著變。${BYLINE}。` });

  const md = toMarkdown(B);
  const html = htmlPage({ title: `${SHOW_TITLE}｜教師講稿`, css: SCRIPT_CSS, body: toHtml(B) });
  return { md, html, blocks: B };
}

/** teacherNote 裡的「要說的話」與括號裡的「要做的事」分開 */
function splitDo(text) {
  const paras = text.split('\n').map((s) => s.trim()).filter(Boolean);
  const say = [], todo = [];
  for (const p of paras) {
    const m = /^(.*?)（([^（）]*(?:全班|等安靜|正式作答)[^（）]*)）\s*$/.exec(p);
    if (m) { if (m[1].trim()) say.push(m[1].trim()); todo.push(...m[2].split(/[。；]/).map((s) => s.trim()).filter(Boolean).map((s) => `${s}。`)); }
    else say.push(p);
  }
  return [say.join('\n'), todo];
}

/** 句子切分：不切在「」、『』、（）裡面的句號 */
function sentences(text) {
  const out = []; let cur = '', depth = 0;
  for (const ch of text) {
    cur += ch;
    if ('「『（'.includes(ch)) depth++;
    else if ('」』）'.includes(ch)) depth = Math.max(0, depth - 1);
    else if (ch === '。' && depth === 0) { out.push(cur.trim()); cur = ''; }
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

/** 開頭的一組「……」（可巢狀） */
function firstQuote(t) {
  const s = t.trimStart();
  if (!s.startsWith('「')) return null;
  let depth = 0;
  for (let i = 0; i < s.length; i++) {
    if (s[i] === '「') depth++;
    else if (s[i] === '」') { depth--; if (depth === 0) return { inner: s.slice(1, i), rest: s.slice(i + 1) }; }
  }
  return null;
}

function findBlocks(n) {
  const out = [];
  const body = n.replace(/^找找看 \d（[^）]*）：/, '');
  const setup = [], notes = [];
  let answer = '';
  const replies = [];
  const chunks = body.split(/(?=回應：)/);
  for (const chunk of chunks) {
    if (chunk.startsWith('回應：')) {
      const q = firstQuote(chunk.slice(3));
      if (q) { replies.push(q.inner); const rest = q.rest.trim(); if (rest) notes.push(...sentences(rest).map((x) => x.replace(/^（(.+)）$/, '$1'))); }
      else replies.push(chunk.slice(3));
      continue;
    }
    for (const s of sentences(chunk)) {
      if (/^(可能的)?答案：/.test(s)) answer = s.replace(/^(可能的)?答案：/, '');
      else if (/^（.+）$/.test(s)) notes.push(s.slice(1, -1));
      else if (replies.length) notes.push(s);
      else setup.push(s);
    }
  }
  if (setup.length) out.push({ p: setup.join('') });
  if (answer) out.push({ p: `**可能的答案**：${answer}` });
  for (const r of replies) out.push({ quote: `〔照念〕${r}` });
  if (notes.length) out.push({ ul: notes });
  return out;
}

const SCRIPT_CSS = `
@page { size: A4 portrait; margin: 13mm 12mm 14mm; }
body { font-size: 10pt; }
h1 { font-size: 22pt; margin-top: 0; }
h2 { font-size: 15pt; border-bottom: 1.2pt solid var(--accent); padding-bottom: 2pt; margin-top: 14pt; break-after: avoid; }
h3 { font-size: 12pt; margin-top: 10pt; break-after: avoid; }
h2.newpage { break-before: page; }
h3.qh { background: var(--soft); padding: 3pt 6pt; border-radius: 3pt; }
.qmeta { color: var(--muted); font-size: 9pt; }
table { font-size: 9pt; margin: 4pt 0 8pt; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
.tbl-cues td:nth-child(1) { font-weight: 700; white-space: nowrap; }
.tbl-cues td:nth-child(2) { white-space: nowrap; color: var(--ink2); }
.tbl-cues td:nth-child(5) { font-weight: 700; }
.tbl-cues tr.row-quiz td { background: #f6efe4; }
.tbl-cues tr.row-plain td:nth-child(4) { color: var(--muted); }
ol.qopts li { margin: 1pt 0; }
ul.bg { color: var(--ink2); font-size: 9pt; }
.bg-h { margin-bottom: 0; }
blockquote { font-size: 10.5pt; }
`;
