// 自動檢查：PDF 題卡文字與八題定稿一字不差、兒童安全用語、繁體與台灣用語、署名、頁數。
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { existsSync } from 'node:fs';
import { PRODUCTION_NOTE_PATTERNS, SPOILERS, SPOILER_RE, STAFF_LINE, speechSeconds, AI_NOTE_LONG, AI_NOTE_SHORT, AI_NOTE_BANNED, PRINT_LIST, PRINT_COUNTS } from './teacher_text.mjs';
import { GOALS } from './lesson.mjs';

const fmtClock = (sec) => { const s = Math.max(0, Math.round(sec)); return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`; };
/** 「對全班說」的長度上限：每題回饋預算約 12 秒（每秒 4 字），容許到 13 秒 */
const SAY_LIMIT_SEC = 13;

const norm = (s) => String(s ?? '').replace(/\s+/g, '');
const plain = (html) => html.replace(/<style[\s\S]*?<\/style>/g, '').replace(/<[^>]+>/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');

// 給孩子看的列印檔（題卡學生版、參與小卡、貼紙）：更嚴格
const CHILD_DOCS = new Set(['題卡_學生版', '參與小卡', '角色貼紙']);

const DRUG_NAMES = ['依托咪酯', '安非他命', 'K他命', '愷他命', '海洛因', '古柯鹼', '搖頭丸', 'MDMA', '笑氣', '喵喵', 'FM2', '一粒眠', '卡西酮', '大麻', '咖啡包', '甲基', '芬太尼', '嗎啡'];
const NAME_CALLING = ['毒蟲', '廢人', '毒鬼'];
const SENTENCE_TERMS = ['有期徒刑', '罰鍰', '級毒品', '刑度', '徒刑'];
// 簡體字（常見、在繁體中不會出現的字）
const SIMPLIFIED = '们这说吗个时会对学医车线画灯请问点题样还没让给东边过见长门头发号机关开听语读写网页书种动无欢乐爱应该儿业专产亲认识贴纸卡师护'.split('').filter((c) => !'卡'.includes(c));
// 非台灣用語（繁體字形寫出的中國大陸用語）
const NON_TW = ['視頻', '軟件', '信息', '屏幕', '鼠標', '打印', '默認', '網絡', '質量', 'U盤', '用戶', '創建', '點擊', '菜單', '優化', '激活', '服務器', '數據'];

export function runChecks({ ROOT, TEACHER, merged, eight, outputs, md, pdfReport, quizCheck, skipPdf, backup, mainLamp, fingerprint }) {
  const results = [];
  const add = (name, ok, detail) => results.push({ name, ok, detail });

  // 1. PDF 題卡的文字（實際印出來的 PDF 抽文字比對）
  if (!skipPdf) {
    for (const [file, offset] of [['題卡_學生版', 0], ['題卡_教師版', 1]]) {
      const pdf = join(TEACHER, 'pdf', `${file}.pdf`);
      if (!existsSync(pdf)) { add(`${file}.pdf 存在`, false, '找不到 PDF'); continue; }
      const qids = Object.keys(eight).sort();
      const detail = [];
      let allOk = true;
      qids.forEach((qid, i) => {
        const e = eight[qid];
        const cueQ = merged.cues.find((c) => c.id === e.cues.quiz)?.quiz;
        const txt = norm(execFileSync('pdftotext', ['-f', String(i + 1 + offset), '-l', String(i + 1 + offset), '-enc', 'UTF-8', pdf, '-'], { encoding: 'utf8' }));
        const want = [e.question, ...e.options];
        const missing = want.filter((w) => !txt.includes(norm(w)));
        const cueSame = cueQ && norm(cueQ.question) === norm(e.question) && cueQ.options.every((o, k) => norm(o) === norm(e.options[k]));
        const ok = missing.length === 0 && cueSame;
        if (!ok) allOk = false;
        detail.push({ qid, page: i + 1 + offset, ok, missing, cueMatchesEight: cueSame });
      });
      add(`${file}.pdf：題目與三個選項和八題定稿、cue quiz 一字不差（pdftotext 抽字）`, allOk, detail);
    }
  }
  add('cue quiz ↔ 八題定稿 ↔ 旁白台詞（題幹、選項、正解、揭答句、指定區）', quizCheck.ok, `${quizCheck.items.reduce((n, it) => n + it.checks.length, 0)} 項`);

  // 2. 用語檢查（所有輸出的文字＋講稿 Markdown）
  const docs = outputs.map((o) => ({ name: o.name, text: plain(o.html) }));
  docs.push({ name: '教師講稿.md', text: md });
  const hits = { drug: [], name: [], sentence: [], zombie: [], grayline: [], simplified: [], nonTW: [], byline: [] };
  const ctxOf = (t, i, n = 14) => t.slice(Math.max(0, i - n), i + n).replace(/\s+/g, ' ');
  for (const d of docs) {
    const child = CHILD_DOCS.has(d.name);
    for (const w of DRUG_NAMES) { let i = d.text.indexOf(w); while (i >= 0) { hits.drug.push({ doc: d.name, word: w, at: ctxOf(d.text, i) }); i = d.text.indexOf(w, i + 1); } }
    for (const w of NAME_CALLING) { let i = d.text.indexOf(w); while (i >= 0) { const c = ctxOf(d.text, i, 10); if (!/不(說|用|稱)|不用「|不稱/.test(c)) hits.name.push({ doc: d.name, word: w, at: c }); i = d.text.indexOf(w, i + 1); } }
    for (const w of SENTENCE_TERMS) { let i = d.text.indexOf(w); while (i >= 0) { const c = ctxOf(d.text, i, 12); if (child || !/不(進|寫|講|談|對)|不把|刑度不/.test(c)) hits.sentence.push({ doc: d.name, word: w, at: c }); i = d.text.indexOf(w, i + 1); } }
    // 「喪屍」只能指物品（喪屍煙彈）或出現在「人不會真的變成喪屍」這類說明裡
    const re = /喪屍(?!煙彈)/g; let m;
    while ((m = re.exec(d.text))) {
      const c = ctxOf(d.text, m.index, 12);
      if (!/(不會真的變成喪屍|真的會變成喪屍|不會變成喪屍|不畫成喪屍|叫成「喪屍」|稱為「喪屍」|稱「喪屍」)/.test(c)) hits.zombie.push({ doc: d.name, at: c });
    }
    let gi = d.text.indexOf('灰線');
    while (gi >= 0) { const c = ctxOf(d.text, gi, 12); if (child || !/叫成「灰線|不用「灰線|「灰線」只/.test(c)) hits.grayline.push({ doc: d.name, at: c }); gi = d.text.indexOf('灰線', gi + 1); }
    for (const ch of SIMPLIFIED) { const i = d.text.indexOf(ch); if (i >= 0) hits.simplified.push({ doc: d.name, char: ch, at: ctxOf(d.text, i, 6) }); }
    for (const w of NON_TW) { const i = d.text.indexOf(w); if (i >= 0) hits.nonTW.push({ doc: d.name, word: w, at: ctxOf(d.text, i, 8) }); }
    if (!d.text.includes('許博明老師製作')) hits.byline.push(d.name);
  }
  add('不念、不寫藥名', hits.drug.length === 0, hits.drug);
  add('不用貶稱（毒蟲、廢人）', hits.name.length === 0, hits.name);
  add('法規分級與刑度不進內容（兒童列印檔一律不出現；教師資料只出現在「不談」的說明）', hits.sentence.length === 0, hits.sentence);
  add('「喪屍」只指物品或用在「人不會變成喪屍」的說明', hits.zombie.length === 0, hits.zombie);
  add('不把操偶線叫成「灰線」', hits.grayline.length === 0, hits.grayline);
  add('全部繁體字（常見簡體字掃描）', hits.simplified.length === 0, hits.simplified);
  add('台灣用語（常見大陸用語掃描）', hits.nonTW.length === 0, hits.nonTW);
  add('每份資料都有署名「許博明老師製作」', hits.byline.length === 0, hits.byline);

  // 3. 必要旁白：講稿裡提到時一字不差（若有完整引用）
  const N1 = '這些線是故事的比喻。毒品可能讓人的頭腦和身體受到影響，不聽使喚。人不會真的變成喪屍。';
  const n1cue = merged.cues.find((c) => c.id === 'a2_c004')?.lines.find((l) => l.id === 'a2_c004_02')?.text;
  add('必要旁白一在 cue 檔一字不差（講稿依 cue 產生）', norm(n1cue) === norm(N1), n1cue);
  const N2 = '不過，看見一個人站不穩，不能就說他吸毒，也可能有其他身體狀況。我們要先找大人幫忙。';
  const n2cue = merged.cues.find((c) => c.id === 'a2_c008')?.lines.find((l) => l.id === 'a2_c008_05')?.text;
  add('必要旁白二在 cue 檔一字不差（講稿依 cue 產生）', norm(n2cue) === norm(N2), n2cue);

  // 3b. G6 修正：製作備註、八題回饋、查核點、人力、備援影片、主燈捧燈手
  const docText = Object.fromEntries(docs.map((d) => [d.name, d.text]));
  docText['教師講稿'] = md; // 講稿用 Markdown 原文比對（和 HTML 同一份內容）
  {
    const found = [];
    for (const d of docs) for (const p of PRODUCTION_NOTE_PATTERNS) {
      const m = p.re.exec(d.text);
      if (m) found.push({ doc: d.name, kind: p.name, at: ctxOf(d.text, m.index, 16) });
    }
    add('沒有製作備註（版本沿革、檔名、程式路徑、規劃書章節號、台詞編號）', found.length === 0, found);
  }
  {
    const bad = []; const lens = [];
    const tCard = norm(docText['題卡_教師版'] ?? '');
    for (const [qid, e] of Object.entries(eight).sort()) {
      const texts = [e.say, ...e.ifMany.map((x) => x.text)];
      for (const t of texts) {
        if (SPOILER_RE.test(t)) bad.push({ qid, problem: '用「像小晴／小宇……」引用劇情', text: t });
        for (const w of SPOILERS[qid] ?? []) if (t.includes(w)) bad.push({ qid, problem: `提前講還沒演的劇情「${w}」`, text: t });
      }
      const sp = speechSeconds(e.say);
      lens.push(`${qid} ${sp.chars} 字約 ${sp.sec.toFixed(1)} 秒`);
      if (sp.sec > SAY_LIMIT_SEC) bad.push({ qid, problem: `「對全班說」${sp.chars} 字約 ${sp.sec.toFixed(1)} 秒，超過每題回饋預算約 12 秒`, text: e.say });
      if (!norm(md).includes(norm(e.say))) bad.push({ qid, problem: '講稿的「對全班說」和產生用的文字不同' });
      if (docText['題卡_教師版'] !== undefined && !tCard.includes(norm(e.say))) bad.push({ qid, problem: '教師版題卡的「對全班說」和講稿不同' });
    }
    add('八題「對全班說」不提前講劇情、約 12 秒內（每秒 4 字），講稿與教師版題卡同一句', bad.length === 0, bad.length ? bad : lens);
  }
  {
    const cps = merged.cues.filter((c) => c.checkpoint && c.checkpoint.atMinute > 0);
    const miss = [];
    const need = { 教師講稿: cps, 一頁操作卡: cps.filter((c) => c.checkpoint.escalate), 成果紀錄範本: cps };
    for (const [doc, list] of Object.entries(need)) {
      const t = docText[doc];
      if (t === undefined) { miss.push({ doc, problem: '沒有這份文件' }); continue; }
      for (const c of list) { const want = fmtClock(c.checkpoint.atMinute * 60); if (!t.includes(want)) miss.push({ doc, cue: c.id, want }); }
    }
    for (const d of docs) if (/比實際配音長度算出的估計早|顯示「落後」約|落後約 ?\d+ ?秒，這是正常的/.test(d.text)) miss.push({ doc: d.name, problem: '還留著「控制台目標比估計早、落後是正常的」說明' });
    add(`查核點時間一律用 cue 的 atMinute（${cps.map((c) => `${c.id} ${c.checkpoint.atMinute}＝${fmtClock(c.checkpoint.atMinute * 60)}`).join('、')}）：講稿、一頁操作卡、成果紀錄範本`, miss.length === 0, miss.length ? miss : '全部寫的是 cue 的目標時間');
  }
  {
    const bad = [];
    for (const doc of ['教師講稿', '教案_教學活動設計', '觀課導覽單']) if (!(docText[doc] ?? '').includes(STAFF_LINE)) bad.push({ doc, problem: '沒有統一的人力配置句' });
    for (const d of docs) if (/協助教師 ?2 ?名/.test(d.text)) bad.push({ doc: d.name, problem: '還寫協助教師 2 名' });
    const n = (md.match(/協助教師記錄區、排、座位/g) ?? []).length;
    const reveals = merged.cues.filter((c) => c.kind === 'reveal').length;
    if (n < reveals) bad.push({ doc: '教師講稿', problem: `揭答欄只有 ${n}／${reveals} 列寫「協助教師記錄區、排、座位」` });
    add(`人力配置三份一致（講稿、教案、觀課導覽單：「${STAFF_LINE}」），講稿揭答欄由協助教師記錄`, bad.length === 0, bad);
  }
  if (backup) {
    const bad = [];
    const docsBV = ['故障一頁卡', '觀課導覽單', '教案_教學活動設計', '教師講稿'];
    for (const doc of docsBV) {
      const t = docText[doc] ?? '';
      if (backup.ready) {
        if (!t.includes(backup.first)) bad.push({ doc, problem: `沒寫備援影片檔名 ${backup.first}` });
        if (/影片（暫定）/.test(t)) bad.push({ doc, problem: '備援影片已產生，還寫「暫定」' });
      } else if (!/影片（暫定）/.test(t)) bad.push({ doc, problem: '備援影片還沒產生，卻沒有標「暫定」' });
    }
    add(`備援影片的說法和交付資料夾一致（${backup.ready ? `已產生：${backup.first}–${backup.last}` : `還沒產生：保留「暫定」，見注意`}）`, bad.length === 0, bad);
  }
  {
    const ok = !!mainLamp && md.includes('最後的主燈，全場一起，捧燈手') && md.includes(`| ${mainLamp.id} |`);
    add(`高潮主燈亮起時帶全場捧燈手（${mainLamp ? `${mainLamp.id}，主燈約第 ${mainLamp.at0.toFixed(1)} 秒亮起` : '找不到主燈的點燈時間'}）`, ok, mainLamp ?? null);
  }
  if (fingerprint) {
    const { atGen, inScript, now } = fingerprint;
    const ok = atGen === now && inScript === now;
    add(`講稿產生時的 cue 指紋＝目前 app/cues/show 的指紋（產生用 ${atGen}、講稿上 ${inScript ?? '找不到'}、目前 ${now}；不排除任何欄位）`, ok, ok ? null : '產生途中或產生之後 cue 有變動：重跑 node tools/teacher_docs.mjs');
  }

  // 3c. G7 修正第 1 輪：AI 使用說明照實寫、列印清單、學習目標④、時間表
  {
    const bad = [];
    if (!norm(docText['教案_教學活動設計']).includes(norm(AI_NOTE_LONG))) bad.push({ doc: '教案_教學活動設計', problem: '沒有完整的 AI 使用說明' });
    if (!norm(docText['觀課導覽單']).includes(norm(AI_NOTE_SHORT))) bad.push({ doc: '觀課導覽單', problem: '沒有精簡的 AI 使用說明' });
    for (const d of docs) for (const re of AI_NOTE_BANNED) { const m = re.exec(d.text); if (m) bad.push({ doc: d.name, problem: `還有舊說法「${m[0]}」`, at: ctxOf(d.text, m.index, 16) }); }
    add('AI 使用說明照實寫（劇本、八題、口訣、教師資料由 AI 起草；不寫「自行設計」「輔助」）：教案、觀課導覽單', bad.length === 0, bad);
  }
  {
    const bad = [];
    const lesson = docText['教案_教學活動設計'] ?? '';
    if (!lesson.includes('列印清單')) bad.push({ doc: '教案_教學活動設計', problem: '教學資源沒有列印清單' });
    for (const r of PRINT_LIST) {
      if (!lesson.includes(`${r.file} ${r.qty}`)) bad.push({ doc: '教案_教學活動設計', problem: `列印清單少了「${r.file} ${r.qty}」` });
      if (!skipPdf) for (const [name, want] of Object.entries(r.pages)) {
        const got = pdfReport.find((x) => x.name === name)?.pages;
        if (got !== undefined && got !== want) bad.push({ doc: name, problem: `列印清單寫 ${want} 頁，PDF 實際 ${got} 頁（改 teacher_text.mjs 的 PRINT_LIST）` });
      }
    }
    const html = Object.fromEntries(outputs.map((o) => [o.name, o.html]));
    const sheets = (html['參與小卡'] ?? '').split('<section class="sheet">').slice(1);
    for (const sh of sheets) { const n = (sh.match(/<div class="c">/g) ?? []).length; if (n !== PRINT_COUNTS.cardsPerSheet) bad.push({ doc: '參與小卡', problem: `一張 A4 實際 ${n} 張卡，列印清單用 ${PRINT_COUNTS.cardsPerSheet}` }); }
    const big = ((html['角色貼紙'] ?? '').match(/<div class="st">/g) ?? []).length, round = ((html['角色貼紙'] ?? '').match(/<div class="rd">/g) ?? []).length;
    if (big !== PRINT_COUNTS.bigStickers || round !== PRINT_COUNTS.roundStickers) bad.push({ doc: '角色貼紙', problem: `實際大貼紙 ${big}、圓貼紙 ${round}，列印清單用 ${PRINT_COUNTS.bigStickers}、${PRINT_COUNTS.roundStickers}` });
    add(`列印清單的數量依實際排版（參與小卡每張 ${PRINT_COUNTS.cardsPerSheet} 張、${PRINT_COUNTS.students} 人；貼紙 ${PRINT_COUNTS.bigStickers}＋${PRINT_COUNTS.roundStickers} 張）與 PDF 頁數`, bad.length === 0, bad);
  }
  {
    const bad = [];
    const g4 = GOALS.find((g) => g.n === '④');
    for (const doc of ['教案_教學活動設計', '觀課導覽單', '成果紀錄範本']) if (!(docText[doc] ?? '').includes(g4.goal)) bad.push({ doc, problem: `沒有學習目標④「${g4.goal}」` });
    if (!/比喻/.test(g4.goal) || !/比喻/.test(g4.show) || !g4.where.includes('Q2')) bad.push({ problem: '目標④ 要涵蓋 Q2 的「操偶線是比喻」' });
    for (const d of docs) if (/求助、不貼標籤（|④ ?求助、不貼標籤/.test(d.text)) bad.push({ doc: d.name, problem: '還有舊的目標④ 名稱' });
    add(`學習目標④「${g4.goal}」三份一致（教案、觀課導覽單、成果紀錄範本）並涵蓋 Q2`, bad.length === 0, bad);
  }
  {
    const bad = [];
    const lesson = docText['教案_教學活動設計'] ?? '';
    if (!/00:00–00:30\s*課前/.test(lesson)) bad.push({ doc: '教案_教學活動設計', problem: '沒有「00:00–00:30 課前」' });
    if (!/\| 課前[^|]*\| 00:00–00:30 \|/.test(md)) bad.push({ doc: '教師講稿', problem: '時間總表沒有獨立的「課前 00:00–00:30」列' });
    const nTalk = (lesson.match(/教師結語/g) ?? []).length;
    const flow = lesson.slice(lesson.indexOf('三、教學流程與時間'), lesson.indexOf('四、評量方式'));
    if ((flow.match(/說明退場/g) ?? []).length > 1) bad.push({ doc: '教案_教學活動設計', problem: '教學流程裡閉幕與教師結語兩列重複寫「說明退場」' });
    if (/日期與場地：暫定/.test(docText['觀課導覽單'] ?? '')) bad.push({ doc: '觀課導覽單', problem: '還印「日期與場地：暫定」' });
    if (!/預錄播放有兩種數字/.test(md)) bad.push({ doc: '教師講稿', problem: '沒有說明預錄播放兩種數字的關係' });
    add('時間表：講稿與教案都把課前 00:00–00:30 獨立一列、閉幕與教師結語不重複；導覽單日期與場地留空格；講稿說明預錄播放兩種數字', bad.length === 0, bad.length ? bad : `教案「教師結語」出現 ${nTalk} 次`);
  }

  // 4. PDF 頁數
  if (!skipPdf) {
    const bad = pdfReport.filter((p) => p.problem || p.missingImg?.length || !p.fontOk);
    add('PDF 頁數符合（操作卡、故障卡、導覽單、回饋單各 1 頁；題卡 8＋教師版封面）、圖與字型都載入', bad.length === 0, bad.length ? bad : pdfReport.map((p) => `${p.name} ${p.pages} 頁`));
  }

  const failed = results.filter((r) => !r.ok).length;
  return { failed, summary: `${results.length - failed}／${results.length} 項通過`, results };
}
