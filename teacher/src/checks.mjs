// 自動檢查：PDF 題卡文字與八題定稿一字不差、兒童安全用語、繁體與台灣用語、署名、頁數。
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { existsSync } from 'node:fs';

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

export function runChecks({ ROOT, TEACHER, merged, eight, outputs, md, pdfReport, quizCheck, skipPdf }) {
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

  // 4. PDF 頁數
  if (!skipPdf) {
    const bad = pdfReport.filter((p) => p.problem || p.missingImg?.length || !p.fontOk);
    add('PDF 頁數符合（操作卡、故障卡、導覽單、回饋單各 1 頁；題卡 8＋教師版封面）、圖與字型都載入', bad.length === 0, bad.length ? bad : pdfReport.map((p) => `${p.name} ${p.pages} 頁`));
  }

  const failed = results.filter((r) => !r.ok).length;
  return { failed, summary: `${results.length - failed}／${results.length} 項通過`, results };
}
