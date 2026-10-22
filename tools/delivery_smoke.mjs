// 交付包冒煙測試（G6 修正第 1 輪，技術 QA S2）：主線把 app/dist 複製進交付資料夾後跑，證明老師拿到的就是驗收過的建置。
//
// 用法（專案根目錄）：
//   node tools/delivery_smoke.mjs                      → 測 交付/browser 與 交付/AntidrugTheater/resources/app/dist，報告寫 review/G6/pack/delivery/
// 選項：
//   --targets <資料夾,資料夾>   要測的交付資料夾（預設上面兩個）
//   --ref <資料夾>              對照的建置（預設 app/dist）
//   --out <資料夾>              報告位置（預設 review/G6/pack/delivery；delivery_smoke.json、delivery_smoke.md、截圖）
//   --expect-cues 71            不加參數開 index.html 應載入的全劇 cue 數
//   --headed                    有視窗的 Chrome
//
// 每個交付資料夾檢查：
//   1. 與 app/dist 逐檔相同（路徑、大小、sha1；列出不同、缺少、多出的檔）
//   2. file:// 開 index.html 不加任何網址參數 → 載入全劇 show（71 個 cue、9 段）、配音與配樂音效齊全
//   3. 整個過程零外部請求（只允許 file:、data:、blob:、about:、chrome*）、沒有頁面錯誤
//   4. 署名卡兩端：按「準備播放」後片頭待機、演完最後一個 cue 後片尾，DOM 都是「許博明老師製作」且看得到
//   5. 八題：題目 cue 依序 Q1–Q8，cue 資料的正解與揭答畫面印章（.quiz-opt.correct）都是 2、3、1、1、3、2、3、2；出題畫面不自動揭答
//   Electron 版另查外殼（main.js、preload.js、layout.js、package.json）與 app/electron 原始碼相同。
// 全部通過結束碼 0，否則 1。
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const TARGETS = opt('--targets', '交付/browser,交付/AntidrugTheater/resources/app/dist').split(',').map((s) => resolve(ROOT, s.trim())).filter(Boolean);
const REF = resolve(ROOT, opt('--ref', 'app/dist'));
const OUT = resolve(ROOT, opt('--out', 'review/G6/pack/delivery'));
const EXPECT_CUES = Number(opt('--expect-cues', '71'));
const ANSWERS = [2, 3, 1, 1, 3, 2, 3, 2];
const SIGNATURE = '許博明老師製作';
const ELECTRON_SHELL = ['main.js', 'preload.js', 'layout.js', 'package.json'];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const relRoot = (p) => { const r = relative(ROOT, p).split('\\').join('/'); return r.startsWith('..') ? p : r || '.'; };
const isExternal = (u) => !/^(file|data|blob|about|chrome|chrome-extension|devtools):/.test(u);
mkdirSync(OUT, { recursive: true });

// ---------------------------------------------------------------- 1. 逐檔比對
function walk(dir, base = dir, out = new Map()) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, base, out);
    else if (e.isFile()) out.set(relative(base, p).split('\\').join('/'), p);
  }
  return out;
}
const hashCache = new Map();
const sha1File = (p) => { if (!hashCache.has(p)) hashCache.set(p, createHash('sha1').update(readFileSync(p)).digest('hex')); return hashCache.get(p); };
function diffTrees(target, ref) {
  const a = walk(target), b = walk(ref);
  const missing = [...b.keys()].filter((k) => !a.has(k)).sort();
  const extra = [...a.keys()].filter((k) => !b.has(k)).sort();
  const different = [];
  for (const [k, pb] of b) {
    const pa = a.get(k);
    if (!pa) continue;
    if (statSync(pa).size !== statSync(pb).size || sha1File(pa) !== sha1File(pb)) different.push(k);
  }
  different.sort();
  return { files_ref: b.size, files_target: a.size, different, missing, extra, identical: !different.length && !missing.length && !extra.length };
}

// ---------------------------------------------------------------- 2–5. 瀏覽器
async function runtime(target, tag) {
  const res = { url: null, errors: [], requests: 0, external: [], checks: {} };
  const browser = await chromium.launch({ channel: 'chrome', headless: !has('--headed'), args: ['--autoplay-policy=no-user-gesture-required', '--mute-audio', '--force-device-scale-factor=1', '--hide-scrollbars'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    page.on('pageerror', (e) => res.errors.push(`[pageerror] ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error') res.errors.push(`[console] ${m.text()}`); });
    page.on('request', (r) => { res.requests++; if (isExternal(r.url())) res.external.push(r.url()); });
    res.url = pathToFileURL(join(target, 'index.html')).href;
    await page.goto(res.url); // 不加任何網址參數（老師在 Windows 上雙擊 index.html 就是這樣）
    await page.waitForFunction(() => window.__engine && (window.__engine.getState().mode === 'error'
      || (window.__engine.getState().mode === 'preparing' && !document.querySelector('.ready-btn')?.disabled)), null, { timeout: 300000, polling: 100 });
    const st = () => page.evaluate(() => window.__engine.getState());
    let s = await st();
    const cues = await page.evaluate(() => window.__engine.getCues());
    const chapters = await page.evaluate(() => window.__engineShow?.chapters?.().length ?? null);
    const query = await page.evaluate(() => location.search);
    res.load = { query, mode: s.mode, cues: cues.length, firstCue: cues[0]?.id ?? null, firstSegment: cues[0]?.segment ?? null, chapters, missingVo: s.missingVo ?? null, missingAudio: s.missingAudio, errors: s.errors };
    res.checks.loads_show_without_params = { ok: query === '' && s.mode === 'preparing' && cues.length === EXPECT_CUES && cues[0]?.id === 'a0_c000' && cues[0]?.segment === 'a0',
      detail: `網址參數「${query}」、${s.mode}、${cues.length} 個 cue（應為 ${EXPECT_CUES}）、第一個 ${cues[0]?.id}（段落 ${cues[0]?.segment}）、${chapters ?? '—'} 段` };
    res.checks.audio_complete = { ok: Array.isArray(s.missingVo) && s.missingVo.length === 0 && s.missingAudio.length === 0,
      detail: `缺配音 ${s.missingVo ? s.missingVo.length : '（這版引擎沒有回報）'}、缺配樂音效 ${s.missingAudio.length}${s.missingAudio.length ? `：${s.missingAudio.join('、')}` : ''}` };
    if (s.mode !== 'preparing') throw new Error(`載入失敗：${(s.errors || []).join('；')}`);

    // 片頭署名卡
    await page.click('.ready-btn');
    await sleep(300);
    if ((await st()).voConfirmPending) { await sleep(900); await page.click('.ready-btn'); } // 缺配音時要按第二次（上面已判不通過）
    await page.waitForFunction(() => window.__engine.getState().phase === 'title_idle', null, { timeout: 120000, polling: 100 });
    await sleep(1500);
    const sig = () => page.evaluate(() => {
      const el = document.getElementById('title-card');
      return { text: el?.querySelector('.sig-text')?.textContent ?? null, hidden: el?.hidden ?? null, opacity: el ? Number(getComputedStyle(el).opacity) : null };
    });
    const sigStart = { ...(await sig()), cue: (await st()).cueId, phase: (await st()).phase };
    const shotStart = `${tag}_title_start.png`;
    await page.screenshot({ path: join(OUT, shotStart) });

    // 八題：出題畫面不自動揭答；揭答畫面印章在正解
    const quizzes = cues.filter((c) => c.kind === 'quiz' && c.quiz);
    const rows = [];
    for (const q of quizzes) {
      const reveal = cues.find((c, i) => i > cues.indexOf(q) && c.kind === 'reveal' && c.quiz?.number === q.quiz.number);
      // 跳到出題畫面（即時播放跳到別的景會先漸暗再漸亮，等漸亮完、題卡出現）
      await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'after' }), q.id);
      await sleep(300); // 漸暗要一兩格才開始（剛跳過去時 dim 還是 0）
      await page.waitForFunction((id) => { const x = window.__engine.getState(); return x.cueId === id && x.mode === 'waiting' && x.quizVisible && x.dim === 0; }, q.id, { timeout: 6000, polling: 50 }).catch(() => undefined);
      await sleep(200);
      const shown = await page.evaluate(() => ({ visible: !document.getElementById('quiz-card')?.hidden, correct: document.querySelectorAll('#quiz-card .quiz-opt.correct').length }));
      const sq = await st();
      let stamp = null;
      if (reveal) {
        await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'after' }), reveal.id);
        await sleep(300);
        await page.waitForFunction((id) => { const x = window.__engine.getState(); return x.cueId === id && x.mode === 'waiting' && x.revealed && x.dim === 0; }, reveal.id, { timeout: 6000, polling: 50 }).catch(() => undefined);
        await sleep(200);
        stamp = await page.evaluate(() => {
          const opts = [...document.querySelectorAll('#quiz-card .quiz-opt')];
          const idx = opts.map((e, i) => (e.classList.contains('correct') ? i + 1 : 0)).filter(Boolean);
          return { options: opts.length, correct: idx };
        });
      }
      rows.push({ number: q.quiz.number, qid: q.quiz.qid, cue: q.id, reveal: reveal?.id ?? null, answerData: q.quiz.answer, stamp: stamp?.correct ?? null, options: stamp?.options ?? null,
        shownVisible: shown.visible, noAutoReveal: shown.correct === 0 && !sq.revealed && sq.phase === 'quiz_shown' });
    }
    const order = rows.map((r) => r.number);
    const dataAns = rows.map((r) => r.answerData);
    const stampAns = rows.map((r) => (r.stamp && r.stamp.length === 1 ? r.stamp[0] : null));
    res.quiz = { rows, order, answers_data: dataAns, answers_stamp: stampAns, expected: ANSWERS };
    res.checks.quiz_order_answers = { ok: rows.length === 8 && JSON.stringify(order) === '[1,2,3,4,5,6,7,8]' && JSON.stringify(dataAns) === JSON.stringify(ANSWERS)
      && JSON.stringify(stampAns) === JSON.stringify(ANSWERS) && rows.every((r) => r.noAutoReveal && r.options === 3),
      detail: `${rows.length} 題、順序 ${order.join('、')}；cue 正解 ${dataAns.join('、')}；印章 ${stampAns.join('、')}（應為 ${ANSWERS.join('、')}）；出題不自動揭答 ${rows.filter((r) => r.noAutoReveal).length}／${rows.length}` };

    // 片尾：演最後一個 cue 到結束，停在署名卡
    const last = cues[cues.length - 1];
    await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'play' }), last.id);
    await page.waitForFunction(() => window.__engine.getState().phase === 'ended', null, { timeout: (last.duration + 30) * 1000, polling: 200 });
    await sleep(1500);
    const sigEnd = { ...(await sig()), cue: (await st()).cueId, phase: (await st()).phase };
    const shotEnd = `${tag}_title_end.png`;
    await page.screenshot({ path: join(OUT, shotEnd) });
    const same = readFileSync(join(OUT, shotStart)).equals(readFileSync(join(OUT, shotEnd)));
    const vis = (x) => x.text === SIGNATURE && x.hidden === false && (x.opacity ?? 0) > 0.9;
    res.attribution = { start: sigStart, end: sigEnd, screenshots: [shotStart, shotEnd], screenshotsIdentical: same };
    res.checks.attribution_both_ends = { ok: vis(sigStart) && vis(sigEnd) && sigStart.phase === 'title_idle' && sigEnd.phase === 'ended',
      detail: `片頭「${sigStart.text}」${sigStart.hidden === false ? '顯示' : '隱藏'}（${sigStart.cue} ${sigStart.phase}）；片尾「${sigEnd.text}」${sigEnd.hidden === false ? '顯示' : '隱藏'}（${sigEnd.cue} ${sigEnd.phase}）；兩張截圖逐位元組相同 ${same ? '是' : '否'}` };
  } catch (err) {
    res.fatal = err instanceof Error ? err.message : String(err);
  } finally {
    await browser.close();
  }
  res.checks.zero_external_requests = { ok: res.external.length === 0, detail: `請求 ${res.requests} 個、外部 ${res.external.length} 個${res.external.length ? `：${res.external.slice(0, 5).join('、')}` : ''}` };
  res.checks.no_page_errors = { ok: res.errors.length === 0 && !res.fatal, detail: res.fatal ? `中止：${res.fatal}` : `${res.errors.length} 則${res.errors.length ? `：${res.errors.slice(0, 3).join(' | ')}` : ''}` };
  for (const k of ['loads_show_without_params', 'audio_complete', 'attribution_both_ends', 'quiz_order_answers']) res.checks[k] ??= { ok: false, detail: res.fatal ? `沒有跑到（${res.fatal}）` : '沒有跑到' };
  return res;
}

// ---------------------------------------------------------------- 執行
const t0 = Date.now();
const report = { generated: new Date().toISOString(), ref: relRoot(REF), expectCues: EXPECT_CUES, expectedAnswers: ANSWERS, signature: SIGNATURE, targets: [] };
if (!existsSync(join(REF, 'index.html'))) { console.error(`[delivery] 找不到 ${relRoot(REF)}/index.html，請先 cd app && npm run build`); process.exit(1); }
for (const target of TARGETS) {
  const tag = relRoot(target).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '') || basename(target);
  const row = { target: relRoot(target), exists: existsSync(join(target, 'index.html')), checks: {} };
  console.log(`\n[delivery] ${row.target}`);
  if (!row.exists) {
    row.checks.exists = { ok: false, detail: '找不到 index.html' };
  } else {
    row.diff = diffTrees(target, REF);
    row.checks.identical_to_build = { ok: row.diff.identical, detail: `與 ${relRoot(REF)} 不同 ${row.diff.different.length}、缺少 ${row.diff.missing.length}、多出 ${row.diff.extra.length}（${row.diff.files_ref} 個檔）` };
    if (basename(target) === 'dist' && existsSync(join(dirname(target), 'main.js'))) {
      const shell = ELECTRON_SHELL.map((f) => ({ file: f, same: existsSync(join(dirname(target), f)) && existsSync(join(ROOT, 'app/electron', f)) && sha1File(join(dirname(target), f)) === sha1File(join(ROOT, 'app/electron', f)) }));
      row.electronShell = shell;
      row.checks.electron_shell_matches_source = { ok: shell.every((x) => x.same), detail: shell.map((x) => `${x.file} ${x.same ? '相同' : '不同'}`).join('、') };
    }
    const rt = await runtime(target, tag);
    Object.assign(row, { runtime: { url: rt.url, load: rt.load, requests: rt.requests, external: rt.external, errors: rt.errors, fatal: rt.fatal ?? null }, quiz: rt.quiz, attribution: rt.attribution });
    Object.assign(row.checks, rt.checks);
  }
  row.pass = Object.values(row.checks).every((c) => c.ok);
  for (const [k, c] of Object.entries(row.checks)) console.log(`${c.ok ? '  通過' : '✗ 失敗'}  ${k}  （${c.detail}）`);
  report.targets.push(row);
}
report.pass = report.targets.length > 0 && report.targets.every((t) => t.pass);
report.seconds = Math.round((Date.now() - t0) / 1000);
writeFileSync(join(OUT, 'delivery_smoke.json'), JSON.stringify(report, null, 1));
const NAMES = {
  exists: '交付資料夾存在', identical_to_build: '與建置逐檔相同（diff 0）', electron_shell_matches_source: 'Electron 外殼與 app/electron 相同',
  loads_show_without_params: `不加參數開 index.html 載入全劇（${EXPECT_CUES} 個 cue）`, audio_complete: '配音、配樂音效齊全',
  attribution_both_ends: `署名卡兩端「${SIGNATURE}」`, quiz_order_answers: `八題順序與正解 ${ANSWERS.join('、')}`, zero_external_requests: '零外部請求', no_page_errors: '沒有頁面錯誤',
};
const md = [`# 交付包冒煙測試`, '', `- 產生：tools/delivery_smoke.mjs（${report.generated}，${report.seconds} 秒）；對照建置 \`${report.ref}\`。本檔只列結果。`,
  `- 整體：${report.pass ? '通過' : '不通過'}。`, ''];
for (const t of report.targets) {
  md.push(`## ${t.target}：${t.pass ? '通過' : '不通過'}`, '', '| 檢查 | 結果 | 說明 |', '|---|---|---|');
  for (const [k, c] of Object.entries(t.checks)) md.push(`| ${NAMES[k] ?? k} | ${c.ok ? '通過' : '不通過'} | ${String(c.detail).replace(/\|/g, '／')} |`);
  if (t.diff && !t.diff.identical) {
    md.push('', `- 不同的檔：${t.diff.different.slice(0, 40).join('、') || '無'}${t.diff.different.length > 40 ? '…' : ''}`,
      `- 交付資料夾缺少：${t.diff.missing.slice(0, 40).join('、') || '無'}${t.diff.missing.length > 40 ? '…' : ''}`,
      `- 交付資料夾多出：${t.diff.extra.slice(0, 40).join('、') || '無'}${t.diff.extra.length > 40 ? '…' : ''}`);
  }
  if (t.attribution) md.push('', `- 署名卡截圖：${t.attribution.screenshots.join('、')}`);
  md.push('');
}
writeFileSync(join(OUT, 'delivery_smoke.md'), md.join('\n') + '\n');
console.log(`\n[delivery] ${report.pass ? '全部通過' : '有項目不通過'} → ${relRoot(join(OUT, 'delivery_smoke.md'))}（${report.seconds} 秒）`);
process.exit(report.pass ? 0 : 1);
