// 題卡樣張（G2 第 3 輪，依兒童劇場導演意見 13、投影可讀性意見 20）：
// 直接用劇場程式的題卡樣式（app/src/ui/theater.css＋app/src/ui/quizcard.ts 的結構與圖示）排 Q1，
// 以 headless Chrome 擷取 1920×1080 三種狀態：出題（思考時靜止、無倒數）、揭答（正解紙印章＋勾號＋外框，其他選項變淡）、點燈。
// 背景＝舞台合成畫面調暗（v1.2 §16.3：出題時舞台燈轉暗、台口前緣亮起）。
// 用法：node tools/quizcard_sample.mjs [--bg review/G2/stage_composite_nosub_v03.png] [--out review/G2]
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const bg = resolve(ROOT, opt('--bg', 'review/G2/stage_composite_nosub_v03.png'));
const out = resolve(ROOT, opt('--out', 'review/G2'));
mkdirSync(out, { recursive: true });

// Q1（script/八題_v03.md 題卡文字，一字不差）
const Q = {
  qid: 'Q1',
  question: '有人拿出包裝漂亮的電子煙，說「這個很安全」。可以相信嗎？',
  options: ['可以，包裝漂亮就很安全。', '不行，外觀不能證明安全。', '可以，聞起來香就沒問題。'],
  answer: 2,
};

// 與 app/src/ui/quizcard.ts 相同的圖示
function handSvg(n) {
  const fingers = [];
  for (let i = 0; i < 4; i++) {
    const up = i < n;
    const x = 9 + i * 8;
    fingers.push(up ? `<rect x="${x}" y="3" width="6.6" height="25" rx="3.3"/>` : `<rect x="${x}" y="19" width="6.6" height="10" rx="3.3"/>`);
  }
  return `<svg class="ico-hand" viewBox="0 0 48 52" aria-hidden="true"><g fill="currentColor">${fingers.join('')}
    <rect x="7" y="22" width="34" height="26" rx="10"/><rect x="0" y="27" width="13" height="7" rx="3.5" transform="rotate(-25 6 30)"/></g></svg>`;
}
function shapeSvg(n) {
  const shape = n === 1 ? '<circle cx="20" cy="20" r="15"/>' : n === 2 ? '<polygon points="20,4 37,35 3,35"/>' : '<rect x="5" y="5" width="30" height="30" rx="3"/>';
  return `<svg class="ico-shape" viewBox="0 0 40 40" aria-hidden="true"><g fill="currentColor">${shape}</g></svg>`;
}
function lampSvg() {
  return `<svg viewBox="0 0 40 52" aria-hidden="true">
    <rect class="lamp-cap" x="13" y="2" width="14" height="6" rx="2"/>
    <ellipse class="lamp-body" cx="20" cy="27" rx="16" ry="18"/>
    <ellipse class="lamp-lit" cx="20" cy="27" rx="16" ry="18"/>
    <path class="lamp-rib" d="M20 9 V45 M11 11 Q4 27 11 43 M29 11 Q36 27 29 43" fill="none"/>
    <rect class="lamp-cap" x="13" y="44" width="14" height="6" rx="2"/></svg>`;
}

function page(state) {
  const reveal = state !== 'question' ? 1 : 0;
  const rows = Q.options.map((text, i) => {
    const n = i + 1;
    const correct = n === Q.answer;
    const opacity = correct ? 1 : (reveal ? 0.36 : 1);
    const frame = correct && reveal ? 1 : 0;
    const stamp = correct && reveal ? 'opacity:1;transform:translateY(-62%) rotate(-7deg) scale(1)' : 'opacity:0';
    return `<div class="quiz-opt opt-${n}${correct && reveal ? ' correct' : ''}" style="opacity:${opacity};--frame:${frame}">
      <span class="opt-num">${n}</span>${handSvg(n)}${shapeSvg(n)}<span class="opt-text">${text}</span>
      <span class="opt-stamp" style="${stamp}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12.5 L9.5 18 L20 6" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>正解</span></div>`;
  }).join('');
  const lamps = Array.from({ length: 8 }, (_, i) => `<div class="lamp" style="--lit:${state === 'lamp' && i === 0 ? 1 : 0}">${lampSvg()}</div>`).join('');
  const css = readFileSync(join(ROOT, 'app/src/ui/theater.css'), 'utf8');
  return `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>${css}
    body { cursor: default; }
    #bgimg { position:absolute; inset:0; width:1920px; height:1080px; filter: brightness(0.42) saturate(0.7); }
  </style></head><body class="capture"><div id="viewport" style="--H:1080px">
    <div id="stage-box" style="left:0;top:0;width:1920px;height:1080px"><img id="bgimg" src="${pathToFileURL(bg).href}"></div>
    <div class="layer" id="quiz-card"><div class="quiz"><div class="quiz-q">${Q.question.replace('。', '。<br>')}</div><div class="quiz-opts">${rows}</div><div class="quiz-lamps">${lamps}</div></div></div>
  </div></body></html>`;
}

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
const pg = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const report = {
  question: Q,
  line_break_note: '題目在句號後換行（「……很安全」。／可以相信嗎？」）。劇場程式目前以 textContent 自動斷行，會斷在「可以／相信」之間；建議主線讓 QuizData.question 支援 \\n 換行（共用元件，G4 前由主線處理）。',
  states: {},
};
for (const state of ['question', 'reveal', 'lamp']) {
  const html = join(out, `_quizcard_${state}.html`);
  writeFileSync(html, page(state));
  await pg.goto(pathToFileURL(html).href);
  await pg.waitForTimeout(300);
  const file = join(out, `quizcard_q1_${state}_v03.png`);
  await pg.screenshot({ path: file });
  // 量測：選項字身、題目字身、每列元素的位置
  report.states[state] = await pg.evaluate(() => {
    const r = (el) => { const b = el.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; };
    const opt = document.querySelector('.quiz-opt .opt-text');
    const q = document.querySelector('.quiz-q');
    return {
      option_font_px: parseFloat(getComputedStyle(opt).fontSize),
      question_font_px: parseFloat(getComputedStyle(q).fontSize),
      font_family_resolved: getComputedStyle(opt).fontFamily,
      card: r(document.querySelector('.quiz')),
      rows: [...document.querySelectorAll('.quiz-opt')].map((row) => ({
        num: r(row.querySelector('.opt-num')), hand: r(row.querySelector('.ico-hand')), shape: r(row.querySelector('.ico-shape')),
        text: r(row.querySelector('.opt-text')), opacity: getComputedStyle(row).opacity,
      })),
    };
  });
  report.states[state].file = file.replace(ROOT + '/', '');
}
await browser.close();
writeFileSync(join(out, 'quizcard_q1_v03.json'), JSON.stringify(report, null, 1));
console.log(JSON.stringify(report.states.question, null, 0).slice(0, 400));
