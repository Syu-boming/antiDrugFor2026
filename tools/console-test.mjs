// 簡報筆映射與教師控制台測試（G5 共用元件；v1.2 第 19.2、19.4、21 節，v1.3 第 6 節）。
// 以 playwright-core＋系統 Google Chrome（瀏覽器雙視窗，BroadcastChannel）與 Electron（雙視窗，IPC）驗證：
//   零、建置：console.html／keytest.html／stage.html／console-link.js 產出、無外部請求、不用攝影機麥克風
//   一、純函式：按鍵解析與映射覆寫、輪區、下一步預告、查核點與壓縮建議、Electron 顯示器版面（延伸／同步／只投影）
//   二、瀏覽器雙視窗：按鍵路由（控制台 → 舞台）、連按／長按不跳段、暫停、上一步、F5／Esc 攔截、
//       控制台內容隨 cue 更新（講稿重點、下一步、正解與指定區、查核點、授課時鐘）、舞台按鍵回報、
//       焦點切換提示、暫停規則（控制台隱藏不暫停、舞台隱藏才暫停且不自行恢復）、舞台乾淨、斷線與重連（時鐘接回）
//   三、單一舞台視窗退路（同步顯示）
//   四、舞台視窗換到不同縮放的螢幕：依新的 devicePixelRatio 重設解析度
//   五、按鍵測試頁與控制台的按鍵測試面板（加設映射後舞台立即生效、恢復預設、測試中不送到劇場）
//   六、Electron 版（有本機 Electron 執行檔時）：雙視窗 IPC、遠端「準備播放」能出聲、離線、拒絕攝影機麥克風、單一視窗模式
// 截圖與結果：review/G5/console/（console_test.json）。
//
// 用法：node tools/console-test.mjs [--headed] [--no-electron] [--electron=/path/to/Electron]
// 需要先在 app/ 執行 npm run build（本測試會自己跑 console.build.mjs）。約 2–3 分鐘。
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const APP = join(ROOT, 'app');
const DIST = join(APP, 'dist');
const OUT = join(ROOT, 'review/G5/console');
const require = createRequire(join(APP, 'package.json'));
const { chromium, _electron } = require('playwright-core');
const esbuild = require('esbuild');
mkdirSync(OUT, { recursive: true });
if (!existsSync(join(DIST, 'index.html'))) { console.error('[console-test] 請先在 app/ 執行 npm run build'); process.exit(1); }

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok: !!ok, detail: String(detail) });
  console.log(`${ok ? '  通過' : '✗ 失敗'}  ${name}${detail ? `  （${detail}）` : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const shots = [];
const shot = async (page, name) => { await page.screenshot({ path: join(OUT, name) }); shots.push(name); };
const url = (file, q = '') => `${pathToFileURL(join(DIST, file)).href}${q ? `?${q}` : ''}`;

// ======================================================================= 零、建置
console.log('\n零、建置');
{
  const { buildConsole } = await import(pathToFileURL(join(APP, 'console.build.mjs')).href);
  await buildConsole({});
  const files = ['console.html', 'console.js', 'keytest.html', 'keytest.js', 'console-link.js', 'stage.html'];
  check('產出 console.html、keytest.html、stage.html、console-link.js', files.every((f) => existsSync(join(DIST, f))), files.filter((f) => !existsSync(join(DIST, f))).join('、'));
  const idx = readFileSync(join(DIST, 'index.html'), 'utf8');
  const stage = readFileSync(join(DIST, 'stage.html'), 'utf8');
  check('stage.html＝index.html 多載入 console-link.js（舞台畫面相同）', stage.replace('\n<script src="console-link.js"></script>', '') === idx || stage === idx);
  const txt = files.map((f) => readFileSync(join(DIST, f), 'utf8')).join('\n');
  const ext = [...txt.matchAll(/(?:src|href)\s*=\s*["'](https?:)?\/\/[^"']+/gi)].map((m) => m[0]);
  check('控制台檔案沒有外部資源', ext.length === 0, ext.slice(0, 3).join(' '));
  check('不用攝影機、麥克風、地理位置', !/getUserMedia|mediaDevices|geolocation|getDisplayMedia/.test(txt));
}

// ======================================================================= 一、純函式
console.log('\n一、純函式');
{
  const tmp = mkdtempSync(join(tmpdir(), 'console-test-'));
  await esbuild.build({
    stdin: { contents: "export * from './src/engine/input.ts'; export * from './src/ui/console-protocol.ts';", resolveDir: APP, loader: 'ts' },
    bundle: true, format: 'esm', platform: 'neutral', outfile: join(tmp, 'units.mjs'), logLevel: 'warning',
  });
  const U = await import(pathToFileURL(join(tmp, 'units.mjs')).href);
  const km = U.effectiveKeymap({});
  const k = (code, key = '', mods = {}) => U.resolveAction({ code, key, ctrlKey: false, metaKey: false, altKey: false, ...mods }, km);
  check('預設映射：PageDown 下一步、PageUp 上一步、句點暫停、F5／Esc 攔截', k('PageDown') === 'next' && k('PageUp') === 'prev' && k('Period') === 'pause' && k('F5') === 'block' && k('Escape') === 'block');
  check('code 缺漏時用 key 對回（PageDown、句點、Esc）', k('', 'PageDown') === 'next' && k('', '.') === 'pause' && k('', 'Esc') === 'block');
  check('修飾鍵：Ctrl＋PageDown 交還瀏覽器，Ctrl＋F5 仍攔截', k('PageDown', '', { ctrlKey: true }) === null && k('F5', '', { ctrlKey: true }) === 'block');
  const km2 = U.effectiveKeymap({ KeyB: 'pause', F5: 'next', Escape: null, ArrowRight: null });
  check('本機加設：B＝暫停；F5／Esc 不能改（仍攔截）；可取消 → 鍵', km2.KeyB === 'pause' && km2.F5 === 'block' && km2.Escape === 'block' && !('ArrowRight' in km2));
  check('輪區 Q1–Q8＝A B C D A B C D', [1, 2, 3, 4, 5, 6, 7, 8].map(U.zoneFor).join('') === 'ABCDABCD');
  check('時間文字', U.clockText(783) === '13:03' && U.driftText(95) === '落後 1:35' && U.driftText(-61) === '超前 1:01' && U.driftText(12).startsWith('準時'));

  const q2 = { qid: 'Q2', number: 2, question: '題目', options: ['甲', '乙', '丙'], answer: 3, zone: 'B' };
  const cues = [
    { id: 'a0_c000', index: 0, kind: 'title', title: '署名卡待機', teacherNote: '待機', checkpoint: null, compression: 0, quiz: null, lamp: null, next: 'a0_c001', prevStable: null, duration: 0, shortVersion: null, skippableLines: [], autoAdvance: false },
    { id: 'a0_c001', index: 1, kind: 'curtain', title: '開幕', teacherNote: '開幕提示。', checkpoint: null, compression: 0, quiz: null, lamp: null, next: 'a2_c005', prevStable: 'a0_c000', duration: 4, shortVersion: null, skippableLines: [], autoAdvance: false },
    { id: 'a2_c005', index: 2, kind: 'quiz', title: '〔題卡 Q2〕出題', teacherNote: '3、2、1', checkpoint: null, compression: 0, quiz: q2, lamp: null, next: 'a2_c006', prevStable: 'a0_c001', duration: 20, shortVersion: null, skippableLines: [], autoAdvance: false },
    { id: 'a2_c006', index: 3, kind: 'reveal', title: '揭答', teacherNote: '', checkpoint: null, compression: 0, quiz: q2, lamp: null, next: 'a2_c007', prevStable: 'a2_c005', duration: 8, shortVersion: null, skippableLines: [], autoAdvance: false },
    { id: 'a2_c007', index: 4, kind: 'lamp', title: '點燈', teacherNote: '', checkpoint: null, compression: 0, quiz: q2, lamp: 2, next: null, prevStable: 'a2_c006', duration: 6, shortVersion: null, skippableLines: [], autoAdvance: false },
  ];
  const byId = new Map(cues.map((c) => [c.id, c]));
  const snap = (e) => ({ sessionId: 's', at: 0, host: 'browser', canRemoteStart: false, cueSet: 'x', engine: { mode: 'waiting', phase: 'story_waiting', phaseLabel: '', paused: false, pauseReason: null, cueId: 'a0_c001', cueIndex: 1, kind: 'curtain', title: '', cueTime: 0, cueDuration: 0, revealed: false, quizVisible: false, lampsLit: [], placeholderAudio: false, missingAudio: [], subtitle: '', clock: 'audio', audioState: 'running', avOffsetMs: 0, leadInMs: 0, quality: 'A', lock30: false, playId: 1, ignoredInputs: 0, ignoredRepeats: 0, blockedKeys: 0, fps: 60, contextLost: false, errors: [], gpu: '', ...e }, win: { focused: true, visible: true, dpr: 1, w: 1, h: 1, extended: null }, clock: { startedAt: null, offsetSec: 30, reached: {} }, compressionLevel: 0, engineCompression: false, lastKey: null });
  const ns = (e, extra = {}) => U.nextStep({ ...snap(e), ...extra }, byId, true).main;
  check('下一步預告：題目出現 → 揭曉答案；劇情等待 → 出題 Q2；正解等待 → 點燈第 2 盞', ns({ phase: 'quiz_shown', cueId: 'a2_c005' }) === '下一步：揭曉答案' && ns({}).startsWith('下一步：出題 Q2') && ns({ phase: 'reveal_waiting', cueId: 'a2_c006' }) === '下一步：點燈（第 2 盞）');
  check('下一步預告：準備畫面（瀏覽器要在舞台按；Electron 可遠端）、暫停中、播放中', ns({ mode: 'preparing', phase: 'preparing' }).includes('投影畫面') && ns({ mode: 'preparing', phase: 'preparing' }, { canRemoteStart: true }) === '下一步：準備播放' && ns({ paused: true, mode: 'playing', phase: 'playing' }) === '暫停中' && ns({ mode: 'playing', phase: 'playing' }).startsWith('播放中'));
  const qc = U.quizContext(snap({}), byId);
  check('劇情等待時預告下一題正解與指定區', qc && qc.upcoming && qc.quiz.answer === 3 && qc.quiz.zone === 'B');
  const show = [
    { id: 'a2_c011', checkpoint: { label: 'Q3 點燈收聲後', atMinute: 13 } },
    { id: 'a4_c011', checkpoint: { label: 'Q6 點燈收聲後', atMinute: 23.45 } },
    { id: 'a6_c005', checkpoint: { label: 'Q8 點燈收聲後', atMinute: 30.8167 } },
  ];
  const adv = (rec) => U.compressionAdvice(show, rec).level;
  check('壓縮建議（時長估算 v03 第 5 節）：Q3 落後 1:29 不觸發、1:30 → 1 級；Q6 2:00 → 1 級；Q8 2:30 → 2 級',
    adv({ a2_c011: { driftSec: 89 } }) === 0 && adv({ a2_c011: { driftSec: 90 } }) === 1 && adv({ a4_c011: { driftSec: 120 } }) === 1
    && adv({ a2_c011: { driftSec: 100 }, a6_c005: { driftSec: 150 } }) === 2 && adv({ a6_c005: { driftSec: 149 } }) === 0);
  const esc = [{ id: 'a2_c011', checkpoint: { label: 'Q3', atMinute: 13, escalate: { behindSec: 60, level: 2 } } }];
  check('壓縮建議以 cue 檔的 checkpoint.escalate 為準（有寫就用它的門檻與級別）', U.compressionAdvice(esc, { a2_c011: { driftSec: 61 } }).level === 2 && U.compressionAdvice(esc, { a2_c011: { driftSec: 59 } }).level === 0);

  const { chooseLayout } = require(join(APP, 'electron/layout.js'));
  const D = (id, x, internal, w = 1920, h = 1080) => ({ id, bounds: { x, y: 0, width: w, height: h }, internal });
  const L1 = chooseLayout([D(1, 0, true)], 1);
  const L2 = chooseLayout([D(1, 0, true), D(2, 0, false)], 1);
  const L3 = chooseLayout([D(1, 0, true, 1366, 768), D(2, 1366, false)], 1);
  const L4 = chooseLayout([D(2, 0, false), D(1, -1366, true, 1366, 768)], 2);
  const L5 = chooseLayout([D(7, 0, false), D(8, 1920, false)], 7);
  const L6 = chooseLayout([D(1, 0, true), D(2, 1920, false)], 1, { single: true });
  check('版面：只有一個畫面 → 單一舞台視窗', L1.mode === 'single' && L1.reason === 'one-display');
  check('版面：同步顯示（兩個畫面範圍相同）→ 單一舞台視窗', L2.mode === 'single' && L2.reason === 'mirror');
  check('版面：延伸顯示 → 舞台在外接螢幕、控制台在筆電螢幕', L3.mode === 'dual' && L3.stage === 2 && L3.console === 1);
  check('版面：投影機被設成主螢幕時，控制台仍放筆電內建螢幕', L4.mode === 'dual' && L4.stage === 2 && L4.console === 1);
  check('版面：不知道哪個是內建螢幕時，控制台放主螢幕、舞台放另一個', L5.mode === 'dual' && L5.console === 7 && L5.stage === 8);
  check('版面：--single 強制單一視窗', L6.mode === 'single');
}

// ======================================================================= 二、瀏覽器雙視窗
const browser = await chromium.launch({ channel: 'chrome', headless: !process.argv.includes('--headed'), args: ['--autoplay-policy=no-user-gesture-required'] });

async function openPair(ctx, cues = 'demo') {
  const con = await ctx.newPage();
  const errors = [];
  con.on('pageerror', (e) => errors.push(`控制台：${e.message}`));
  con.on('console', (m) => { if (m.type() === 'error') errors.push(`控制台：${m.text()}`); });
  await con.goto(url('console.html', `cues=${cues}&dual=force`));
  const stage = await ctx.newPage();
  stage.on('pageerror', (e) => errors.push(`舞台：${e.message}`));
  stage.on('console', (m) => { if (m.type() === 'error') errors.push(`舞台：${m.text()}`); });
  await stage.goto(url('stage.html', `cues=${cues}&nofs=1`));
  await stage.waitForFunction(() => window.__engine && ['preparing', 'waiting'].includes(window.__engine.getState().mode), null, { timeout: 60000 });
  await con.waitForFunction(() => window.__console.connected() && window.__console.cues().length > 0, null, { timeout: 10000 });
  return { con, stage, errors };
}
const sst = (stage) => stage.evaluate(() => window.__engine.getState());
const ctext = (con, sel) => con.locator(sel).first().innerText();
// 等待條件成立；逾時不中斷測試（由後面的 check 判定失敗）
const waitStage = (stage, fn, arg, timeout = 15000) => stage.waitForFunction(fn, arg, { timeout, polling: 50 }).then(() => true, () => false);
const waitCon = (con, fn, arg, timeout = 5000) => con.waitForFunction(fn, arg, { timeout, polling: 50 }).then(() => true, () => false);

console.log('\n二、瀏覽器雙視窗（BroadcastChannel）');
{
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const { con, stage, errors } = await openPair(ctx);
  check('控制台自動連上舞台並取得 cue 資料', await con.evaluate(() => window.__console.transport === 'broadcast' && window.__console.cues().length === 8));
  await shot(con, 'browser_01_preparing.png');

  // 準備畫面：瀏覽器版不能遠端啟用聲音
  await con.keyboard.press('PageDown');
  await sleep(400);
  let s = await sst(stage);
  const lc = await con.evaluate(() => window.__console.lastCmd());
  check('準備畫面：控制台按下一步不會在舞台沒有使用者操作時啟動（瀏覽器規定）', s.mode === 'preparing' && lc?.effect === 'need-gesture' && (await ctext(con, '[data-el="nextMain"]')).includes('準備播放'));
  await stage.click('.ready-btn');
  await waitStage(stage, () => window.__engine.getState().phase === 'title_idle');
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent.startsWith('下一步：開幕'));
  check('片頭待機：控制台顯示「下一步：開幕」與講稿重點', (await ctext(con, '[data-el="note"]')).includes('課前待機'));
  check('授課時鐘開演前顯示「未開始」', (await ctext(con, '[data-el="clock"]')) === '未開始');
  await shot(con, 'browser_02_title_idle.png');

  // 按鍵路由（停住後 350 ms 內的下一步視為連按誤觸，先等一下）
  await sleep(450);
  await con.keyboard.press('PageDown');
  await waitStage(stage, () => window.__engine.getState().phase === 'playing', null, 3000).catch(() => undefined);
  s = await sst(stage);
  check('按鍵路由：控制台 PageDown → 舞台開幕（唯一狀態來源執行）', s.cueId === 'a0_c001' && s.phase === 'playing');
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent.startsWith('播放中'));
  check('授課時鐘在開幕時從 00:30 起跳', /^00:3\d$/.test(await ctext(con, '[data-el="clock"]')), await ctext(con, '[data-el="clock"]'));
  await shot(con, 'browser_03_playing.png');

  await waitStage(stage, () => window.__engine.getState().phase === 'story_waiting', null, 10000);
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent.includes('線落下來'));
  check('劇情等待：下一步預告下一段標題、講稿重點換成本段', (await ctext(con, '[data-el="note"]')).includes('署名卡約 1 秒淡出'));
  await shot(con, 'browser_04_story_waiting.png');
  await sleep(450);
  // 停住後連按兩下：只推進一段
  await con.keyboard.press('PageDown');
  await sleep(60);
  await con.keyboard.press('PageDown');
  await sleep(400);
  s = await sst(stage);
  check('停住後連按兩下：只推進一段（a2_c002）', s.cueId === 'a2_c002' && s.phase === 'playing');
  // 播放中連按
  const ign0 = s.ignoredInputs;
  for (let i = 0; i < 5; i++) { await con.keyboard.press('PageDown'); await sleep(40); }
  await sleep(300);
  s = await sst(stage);
  check('播放中從控制台連按 5 下：全部忽略、不跳段', s.cueId === 'a2_c002' && s.phase === 'playing' && s.ignoredInputs - ign0 >= 5, `忽略 ${s.ignoredInputs - ign0} 次`);
  // 長按
  const rep0 = await con.evaluate(() => window.__console.input.ignoredRepeats);
  await con.keyboard.down('PageDown');
  for (let i = 0; i < 8; i++) { await con.keyboard.down('PageDown'); await sleep(20); }
  await con.keyboard.up('PageDown');
  await sleep(300);
  s = await sst(stage);
  const rep1 = await con.evaluate(() => window.__console.input.ignoredRepeats);
  check('長按（key repeat）：控制台全部忽略、舞台不跳段', rep1 - rep0 >= 8 && s.cueId === 'a2_c002', `repeat ${rep1 - rep0} 次`);
  // 暫停／繼續
  await con.keyboard.press('Period');
  await sleep(300);
  const p1 = await sst(stage);
  await sleep(500);
  const p2 = await sst(stage);
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent === '暫停中');
  check('黑屏鍵（句點）從控制台暫停：畫面時間停住、控制台顯示暫停中', p1.paused && Math.abs(p2.cueTime - p1.cueTime) < 0.01);
  await shot(con, 'browser_07_paused.png');
  await con.keyboard.press('Period');
  await sleep(300);
  check('再按一次繼續', !(await sst(stage)).paused);
  // 上一步
  await con.keyboard.press('PageUp');
  await sleep(300);
  s = await sst(stage);
  const back = await con.evaluate(() => window.__console.lastCmd());
  check('上一步：回到上一個穩定節點（a0_c001 停住）', s.cueId === 'a0_c001' && s.phase === 'story_waiting' && back?.effect === 'back');
  // F5／Esc
  await con.evaluate(() => { window.__marker = 7; });
  await con.keyboard.press('F5');
  await con.keyboard.press('Escape');
  await sleep(200);
  check('控制台的 F5／Esc 一律攔截、不重新整理、不送到舞台', (await con.evaluate(() => window.__marker)) === 7 && (await con.evaluate(() => window.__console.input.blocked)) >= 2 && (await sst(stage)).cueId === 'a0_c001');

  // 舞台視窗收到的按鍵回報到控制台
  await stage.keyboard.press('KeyX');
  await waitCon(con, () => document.querySelector('[data-el="keys"]').textContent.includes('舞台視窗'), null, 3000).catch(() => undefined);
  check('舞台視窗收到的按鍵也顯示在控制台（標明是哪個視窗）', /x（舞台視窗）/i.test(await ctext(con, '[data-el="keys"]')));

  // 跳到 a2_c005（停在它之前）→ 預告下一題
  await con.selectOption('[data-el="jump"]', 'a2_c005');
  await con.click('button[data-act="jump"]');
  await waitStage(stage, () => window.__engine.getState().cueId === 'a2_c004' && window.__engine.getState().mode === 'waiting', null, 3000);
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent.includes('出題 Q2'));
  check('跳到選單：停在 a2_c005 之前；控制台預告下一題 Q2（正解 3、B 區）', (await ctext(con, '[data-el="quizLbl"]')).includes('下一題 Q2') && (await ctext(con, '[data-el="ans"]')) === '3' && (await ctext(con, '[data-el="zone"]')) === 'B 區');
  await sleep(400);
  await con.keyboard.press('PageDown');
  await waitStage(stage, () => window.__engine.getState().phase === 'quiz_shown', null, 40000);
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent === '下一步：揭曉答案');
  const note = await ctext(con, '[data-el="note"]');
  const opts = await con.locator('[data-el="opts"] li.correct').innerText();
  check('題目出現：下一步＝揭曉答案；本題正解 3、指定區 B；講稿重點是本題提示', note.includes('本題看 B 區') && opts.startsWith('3') && (await ctext(con, '[data-el="quizLbl"]')) === '本題 Q2');
  check('投影端（舞台）沒有正解標示（題目出現時未揭答）', (await stage.locator('.quiz-opt.correct').count()) === 0);
  await shot(con, 'browser_05_quiz_shown.png');
  await shot(stage, 'stage_quiz_shown_clean.png');
  await sleep(400);
  await con.keyboard.press('PageDown');
  await waitStage(stage, () => window.__engine.getState().phase === 'reveal_waiting', null, 20000);
  await waitCon(con, () => document.querySelector('[data-el="nextMain"]').textContent.includes('收起題卡'));
  check('正解等待：控制台標示已揭曉、下一步＝收起題卡進入閉幕', (await ctext(con, '[data-el="quizLbl"]')).includes('已揭曉') && (await ctext(con, '[data-el="nextMain"]')).includes('收起題卡'));
  await shot(con, 'browser_06_reveal_waiting.png');

  // 查核點：完整播一次 a2_c004（查核點「第二幕必要旁白一」13:00）
  await stage.evaluate(() => window.__engine.gotoCue('a2_c004', { mode: 'play' }));
  await waitStage(stage, () => window.__engine.getState().cueId === 'a2_c004' && window.__engine.getState().mode === 'waiting', null, 40000);
  await waitCon(con, () => /第二幕必要旁白一[^\n]*實際/.test(document.querySelector('[data-el="cpList"]').innerText), null, 3000);
  const cp = await ctext(con, '[data-el="cpList"]');
  check('查核點：段落播完時記下實際時間與落差（超前／落後）', /第二幕必要旁白一\s+目標 13:00\s+實際 \d\d:\d\d，超前 1[12]:\d\d/.test(cp), cp.split('\n').find((l) => l.includes('第二幕')));
  const clk0 = await ctext(con, '[data-el="clock"]');
  await con.click('button[data-clock="adjust:30"]');
  await sleep(400);
  const clk1 = await ctext(con, '[data-el="clock"]');
  const toS = (t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3));
  check('授課時鐘 ＋30 秒（狀態存在舞台端）', toS(clk1) - toS(clk0) >= 29 && toS(clk1) - toS(clk0) <= 32, `${clk0} → ${clk1}`);
  await shot(con, 'browser_10_checkpoint.png');

  // 焦點切換
  const setFocus = (page, on) => page.evaluate((v) => { document.hasFocus = () => v; window.dispatchEvent(new Event(v ? 'focus' : 'blur')); }, on);
  await setFocus(con, false);
  await setFocus(stage, false);
  await waitCon(con, () => !document.querySelector('[data-el="focusWarn"]').hidden, null, 4000).catch(() => undefined);
  check('兩個視窗都沒有焦點：大字提示「請點一下控制台」', !(await con.locator('[data-el="focusWarn"]').isHidden()) && (await ctext(con, '[data-el="focusWarn"]')).includes('請點一下控制台'));
  await shot(con, 'browser_08_focus_warn.png');
  await setFocus(stage, true);
  await waitCon(con, () => document.querySelector('[data-el="focus"]').textContent.startsWith('焦點：舞台視窗'), null, 4000).catch(() => undefined);
  check('焦點在舞台視窗：控制台標示焦點位置、不擋畫面', (await ctext(con, '[data-el="focus"]')).startsWith('焦點：舞台視窗') && (await con.locator('[data-el="focusWarn"]').isHidden()));
  await setFocus(con, true);
  await waitCon(con, () => document.querySelector('[data-el="focus"]').textContent.startsWith('焦點：控制台'), null, 2000).catch(() => undefined);
  check('點回控制台：標示「焦點：控制台」', (await ctext(con, '[data-el="focus"]')).startsWith('焦點：控制台'));

  // 暫停規則
  await stage.evaluate(() => window.__engine.gotoCue('a2_c002', { mode: 'play' }));
  await sleep(600);
  await setFocus(stage, false);
  await con.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await sleep(500);
  s = await sst(stage);
  check('舞台失去焦點、控制台被隱藏：演出不暫停（只在控制台提示）', s.phase === 'playing' && !s.paused);
  await con.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await stage.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await sleep(300);
  await stage.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await sleep(700);
  s = await sst(stage);
  await waitCon(con, () => document.querySelector('[data-el="nextSub"]').textContent.includes('被隱藏'), null, 3000).catch(() => undefined);
  check('舞台頁面被隱藏才暫停；恢復顯示後仍停住，控制台說明原因', s.paused && s.pauseReason === 'hidden' && (await ctext(con, '[data-el="nextSub"]')).includes('舞台視窗被隱藏或縮小'));
  await con.keyboard.press('PageDown');
  await sleep(300);
  s = await sst(stage);
  check('暫停中從控制台按下一步：只繼續、不跳段', !s.paused && s.cueId === 'a2_c002' && s.phase === 'playing');
  await setFocus(stage, true);

  // 舞台乾淨
  check('投影端只有舞台：舞台頁沒有任何控制台元素', (await stage.evaluate(() => document.querySelectorAll('#console-root, [class^="c-"], .kt').length)) === 0);
  await shot(stage, 'stage_playing_clean.png');

  // 斷線與重連
  const clockBefore = await con.evaluate(() => window.__console.snapshot().clock.startedAt);
  await stage.close();
  await waitCon(con, () => document.querySelector('[data-el="link"]').textContent.includes('中斷'), null, 6000).catch(() => undefined);
  check('舞台視窗關掉：控制台 3 秒內顯示連線中斷', (await ctext(con, '[data-el="link"]')).includes('連線中斷'));
  await con.keyboard.press('PageDown');
  await sleep(200);
  check('斷線時按下一步：控制台說明沒有送出', (await ctext(con, '[data-el="keys"]')).includes('舞台未連線'));
  await shot(con, 'browser_09_disconnected.png');
  const stage2 = await ctx.newPage();
  await stage2.goto(url('stage.html', 'cues=demo&nofs=1'));
  await stage2.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
  await waitCon(con, () => window.__console.connected(), null, 8000).catch(() => undefined);
  await sleep(1500);
  const clockAfter = await stage2.evaluate(() => window.__consoleLink.snapshot()?.clock.startedAt);
  check('舞台重新開啟：自動重連，授課時鐘接回原本的起點', (await con.evaluate(() => window.__console.connected())) && clockAfter === clockBefore);

  check('過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));

  // 其他筆電解析度（1920×1080 縮放 150%＝1280×720；125%＝1536×864）
  for (const [w, h] of [[1280, 720], [1536, 864]]) {
    await con.setViewportSize({ width: w, height: h });
    await sleep(300);
    const fit = await con.evaluate(() => {
      const r = document.querySelector('.c-controls').getBoundingClientRect();
      return r.bottom <= window.innerHeight + 1 && document.documentElement.scrollWidth <= window.innerWidth + 1;
    });
    check(`控制台在 ${w}×${h} 一個畫面放得下（按鈕列不被擠出畫面、沒有橫向捲動）`, fit);
    await shot(con, `browser_layout_${w}x${h}.png`);
  }
  await ctx.close();
}

// ======================================================================= 二之二、全劇 cue 集
const hasShow = existsSync(join(DIST, 'data/cues_show.js'));
console.log('\n二之二、全劇 cue 集（show）');
if (!hasShow) check('全劇 cue 集（dist 沒有 cues_show.js，略過）', true);
else {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const { con, stage, errors } = await openPair(ctx, 'show');
  const cues = await con.evaluate(() => window.__console.cues());
  const groups = await con.locator('[data-el="jump"] optgroup').count();
  check('全劇：控制台取得全部 cue，跳到選單依章節分組', cues.length >= 69 && groups >= 9, `${cues.length} 個 cue、${groups} 章`);
  await stage.click('.ready-btn');
  await waitStage(stage, () => window.__engine.getState().phase === 'title_idle', null, 20000);
  await sleep(450);
  await con.keyboard.press('PageDown'); // 開演（引擎與控制台的授課時鐘從這裡起算）
  await waitStage(stage, () => window.__engine.getState().cueId === 'a0_c001', null, 5000);
  // 八題：跳到每題出題之前，控制台預告的正解與指定區
  const quizzes = cues.filter((c) => c.kind === 'quiz');
  const seen = [];
  for (const q of quizzes) {
    await con.selectOption('[data-el="jump"]', q.id);
    await con.click('button[data-act="jump"]');
    await waitCon(con, (qid) => document.querySelector('[data-el="quizLbl"]').textContent.includes(`下一題 ${qid}`), q.quiz.qid, 5000);
    seen.push(`${(await ctext(con, '[data-el="quizLbl"]')).match(/Q\d/)?.[0]}:${await ctext(con, '[data-el="ans"]')}${(await ctext(con, '[data-el="zone"]'))[0]}`);
  }
  check('全劇八題：控制台的正解 2、3、1、1、3、2、3、2，指定區 A B C D A B C D', seen.join(' ') === 'Q1:2A Q2:3B Q3:1C Q4:1D Q5:3A Q6:2B Q7:3C Q8:2D', seen.join(' '));
  await shot(con, 'show_01_q8_upcoming.png');
  // 壓縮級別：由控制台設定，引擎是唯一來源
  if (await stage.evaluate(() => !!window.__engineShow?.setCompression)) {
    await con.click('button[data-comp="1"]');
    await waitCon(con, () => document.querySelector('[data-el="compTeacher"]').textContent.startsWith('目前 1 級'), null, 3000);
    const lv = await stage.evaluate(() => window.__engineShow.compression());
    check('壓縮級別：控制台按「1 級」→ 引擎套用 1 級（控制台顯示引擎的值）', lv === 1 && (await con.locator('button[data-comp="1"].on').count()) === 1);
    await shot(con, 'show_02_compression1.png');
    await con.click('button[data-comp="0"]');
    await waitCon(con, () => document.querySelector('[data-el="compTeacher"]').textContent.startsWith('目前 0 級'), null, 3000);
    check('壓縮級別：回到 0 級', (await stage.evaluate(() => window.__engineShow.compression())) === 0);
    // 查核點：播完 Q3 點燈（a2_c011）
    await stage.evaluate(() => window.__engine.gotoCue('a2_c011', { mode: 'play' }));
    await waitStage(stage, () => window.__engine.getState().cueId === 'a2_c011' && window.__engine.getState().mode === 'waiting', null, 30000);
    await waitCon(con, () => /Q3[^\n]*實際/.test(document.querySelector('[data-el="cpList"]').innerText), null, 4000);
    const cpTxt = await ctext(con, '[data-el="cpList"]');
    const src = await con.evaluate(() => window.__console.snapshot()?.checkpointSource);
    check('查核點用引擎的到達紀錄，換算成授課時鐘（開幕 00:30 起跳）顯示落差', src === 'engine' && /Q3 點燈收聲後\s+目標 13:00\s+實際 \d\d:\d\d，超前 1[12]:\d\d/.test(cpTxt), `${src}｜${cpTxt.split('\n').find((l) => l.includes('Q3'))}`);
    await shot(con, 'show_03_checkpoint_q3.png');
  } else check('引擎沒有 __engineShow（舊版），壓縮與查核點由連結自己處理', true);
  check('全劇：過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
  await ctx.close();
}

// ======================================================================= 三、單一舞台視窗退路
console.log('\n三、單一舞台視窗退路（同步顯示）');
{
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const con = await ctx.newPage();
  await con.goto(url('console.html', 'cues=demo&fallbackDelay=1500'));
  const ext = await con.evaluate(() => screen.isExtended);
  await con.waitForSelector('[data-el="single"]:not([hidden])', { timeout: 4000 }).catch(() => undefined);
  await shot(con, 'single_01_notice.png');
  await con.waitForURL(/stage\.html/, { timeout: 8000 }).catch(() => undefined);
  const onStage = con.url().includes('stage.html');
  if (onStage) await con.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
  check('只有一個畫面（screen.isExtended=false）：先提示，再自動改走單一舞台視窗', ext === false && onStage && con.url().includes('cues=demo'), con.url().split('/').pop());
  await con.click('.ready-btn');
  await con.waitForFunction(() => window.__engine.getState().phase === 'title_idle');
  await sleep(450);
  await con.keyboard.press('PageDown');
  await sleep(300);
  check('單一舞台視窗：簡報筆直接操作舞台', (await sst(con)).cueId === 'a0_c001');
  await ctx.close();

  // 舞台已經開著時，不再開第二個舞台
  const ctx2 = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const st = await ctx2.newPage();
  await st.goto(url('stage.html', 'cues=demo&nofs=1'));
  await st.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
  const con2 = await ctx2.newPage();
  await con2.goto(url('console.html', 'cues=demo&fallbackDelay=800'));
  await sleep(3000);
  check('同一個畫面上舞台已經開著：控制台只提醒「會被投影出去」，不再開第二個舞台', con2.url().includes('console.html') && (await ctext(con2, '[data-el="singleTitle"]')).includes('會被投影出去'));
  await shot(con2, 'single_02_stage_already_open.png');
  await ctx2.close();
}

// ======================================================================= 四、縮放比例改變
console.log('\n四、舞台視窗換到不同縮放的螢幕');
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const st = await ctx.newPage();
  await st.goto(url('stage.html', 'cues=demo&nofs=1'));
  await st.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
  const size = () => st.evaluate(() => { const c = document.querySelector('#stage-box canvas'); return { w: c.width, h: c.height, dpr: devicePixelRatio, css: c.getBoundingClientRect().width }; });
  const a = await size();
  const cdp = await ctx.newCDPSession(st);
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 720, deviceScaleFactor: 1.5, mobile: false });
  await sleep(800);
  const b = await size();
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 720, deviceScaleFactor: 1.25, mobile: false });
  await sleep(800);
  const c = await size();
  check('devicePixelRatio 1 → 1.5 → 1.25：舞台繪圖解析度跟著重設', b.dpr === 1.5 && Math.abs(b.w / a.w - 1.5) < 0.02 && Math.abs(c.w / a.w - 1.25) < 0.02, `${a.w}→${b.w}→${c.w} px`);
  await ctx.close();
}

// ======================================================================= 五、按鍵測試
console.log('\n五、按鍵測試頁與控制台的按鍵測試面板');
{
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const kt = await ctx.newPage();
  await kt.goto(url('keytest.html'));
  await kt.evaluate(() => { window.__marker = 9; });
  for (const key of ['PageDown', 'PageUp', 'Period', 'F5', 'Escape']) { await kt.keyboard.press(key); await sleep(60); }
  await kt.keyboard.down('PageDown');
  for (let i = 0; i < 4; i++) { await kt.keyboard.down('PageDown'); await sleep(20); }
  await kt.keyboard.up('PageDown');
  await sleep(200);
  check('按鍵測試頁：六項核對全部打勾（下一步、上一步、黑屏鍵、F5、Esc、長按）', (await kt.locator('.kt-checks li.ok').count()) === 6);
  check('按鍵測試頁：F5 被攔截、沒有重新整理；顯示 key／code', (await kt.evaluate(() => window.__marker)) === 9 && (await kt.locator('[data-el="lastMeta"]').innerText()).includes('code=PageDown'));
  await kt.keyboard.press('F5');
  await sleep(100);
  check('F5／Esc 不能改映射（不顯示改設按鈕）', await kt.locator('[data-el="remap"]').isHidden());
  await kt.keyboard.press('KeyB');
  await sleep(100);
  const remapShown = !(await kt.locator('[data-el="remap"]').isHidden());
  await kt.click('[data-remap="next"]');
  await sleep(100);
  const saved = await kt.evaluate(() => localStorage.getItem('antidrug-theater-keymap'));
  check('沒有作用的鍵（b）可以加設成「下一步」並存在本機設定', remapShown && saved === '{"KeyB":"next"}' && (await kt.locator('[data-el="lastAct"]').innerText()).includes('下一步'), saved);
  await shot(kt, 'keytest_page.png');
  // 舞台頁（同一個瀏覽器設定檔）立即生效
  const st = await ctx.newPage();
  await st.goto(url('stage.html', 'cues=demo&nofs=1'));
  await st.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
  await st.click('.ready-btn');
  await st.waitForFunction(() => window.__engine.getState().phase === 'title_idle');
  await sleep(450);
  await st.keyboard.press('KeyB');
  await sleep(300);
  check('加設的映射在舞台視窗生效（按 b＝下一步，開幕）', (await sst(st)).cueId === 'a0_c001');
  await kt.click('[data-kt="reset"]');
  await sleep(150);
  check('恢復預設映射：清除本機加設', (await kt.evaluate(() => localStorage.getItem('antidrug-theater-keymap'))) === null);
  // 控制台的按鍵測試面板：測試中按鍵不送到劇場
  const con = await ctx.newPage();
  await con.goto(url('console.html', 'cues=demo&dual=force'));
  await con.waitForFunction(() => window.__console.connected(), null, { timeout: 8000 });
  await st.waitForFunction(() => window.__engine.getState().phase === 'story_waiting', null, { timeout: 10000 });
  await sleep(400);
  await con.click('button[data-act="keytest"]');
  await con.keyboard.press('PageDown');
  await sleep(400);
  check('控制台的按鍵測試面板：測試中按 PageDown 不會送到劇場', (await sst(st)).cueId === 'a0_c001' && (await con.locator('.kt-checks li.ok').count()) >= 1);
  await shot(con, 'console_keytest_overlay.png');
  await con.click('[data-kt="close"]');
  await con.keyboard.press('PageDown');
  await sleep(400);
  check('關閉面板後恢復轉送', (await sst(st)).cueId === 'a2_c002');
  await ctx.close();
}
await browser.close();

// ======================================================================= 六、Electron
console.log('\n六、Electron 版（雙視窗 IPC）');
function findElectron() {
  const arg = process.argv.find((a) => a.startsWith('--electron='));
  if (arg) return arg.slice(11);
  if (process.env.ELECTRON_PATH) return process.env.ELECTRON_PATH;
  if (process.platform !== 'darwin') return null;
  const cache = join(homedir(), 'Library/Caches/electron');
  if (!existsSync(cache)) return null;
  const zips = [];
  const walk = (d) => { for (const f of readdirSync(d, { withFileTypes: true })) { const p = join(d, f.name); if (f.isDirectory()) walk(p); else if (/^electron-v[\d.]+-darwin-(arm64|x64)\.zip$/.test(f.name)) zips.push(p); } };
  walk(cache);
  if (!zips.length) return null;
  const zip = zips.sort().pop();
  const ver = /electron-v([\d.]+)-/.exec(zip)[1];
  const dir = join(tmpdir(), `antidrug-electron-${ver}`);
  const exe = join(dir, 'Electron.app/Contents/MacOS/Electron');
  if (!existsSync(exe)) { mkdirSync(dir, { recursive: true }); execFileSync('ditto', ['-x', '-k', zip, dir]); }
  return existsSync(exe) ? exe : null;
}
const electronExe = process.argv.includes('--no-electron') ? null : findElectron();
if (!electronExe) {
  check('Electron 測試（找不到本機 Electron 執行檔，略過）', true, '用 --electron=路徑 或 ELECTRON_PATH 指定');
} else {
  const launch = (args) => _electron.launch({ executablePath: electronExe, args: [join(APP, 'electron'), ...args], timeout: 30000 });
  const eapp = await launch(['--dual-test', '--cues=demo']);
  const errors = [];
  const t0 = Date.now();
  while (eapp.windows().length < 2 && Date.now() - t0 < 15000) await sleep(200);
  const wins = eapp.windows();
  for (const w of wins) w.on('pageerror', (e) => errors.push(e.message));
  const stage = wins.find((w) => w.url().includes('stage.html'));
  const con = wins.find((w) => w.url().includes('console.html'));
  check('Electron：開兩個視窗（舞台 stage.html、控制台 console.html）', !!stage && !!con, wins.map((w) => w.url().split('/').pop()).join('、'));
  await stage.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
  await con.waitForFunction(() => window.__console.connected() && window.__console.cues().length > 0, null, { timeout: 10000 });
  check('Electron：兩個視窗用 IPC 同步', (await con.evaluate(() => window.__console.transport)) === 'ipc' && (await stage.evaluate(() => window.__consoleLink.transport)) === 'ipc');
  await con.keyboard.press('PageDown');
  await stage.waitForFunction(() => window.__engine.getState().phase === 'title_idle', null, { timeout: 20000 }).catch(() => undefined);
  let s = await sst(stage);
  check('Electron：控制台按下一步＝遠端「準備播放」，音訊時鐘正常（允許自動播放）', s.phase === 'title_idle' && s.clock === 'audio' && s.audioState === 'running', `${s.clock}／${s.audioState}`);
  await sleep(500);
  await con.keyboard.press('PageDown');
  await sleep(500);
  s = await sst(stage);
  check('Electron：按鍵路由（控制台 PageDown → 舞台開幕）', s.cueId === 'a0_c001' && s.phase === 'playing');
  const layout = await con.evaluate(() => window.theaterHost.info());
  check('Electron：主程序回報版面（測試用並排雙視窗）', layout.layout?.mode === 'dual-test' && layout.role === 'console', JSON.stringify(layout.layout));
  const offline = await stage.evaluate(async () => { try { await fetch('https://example.com/'); return 'reached'; } catch { return 'blocked'; } });
  check('Electron：完全離線（外部請求一律擋掉）', offline === 'blocked');
  const media = await stage.evaluate(async () => { try { await navigator.mediaDevices.getUserMedia({ audio: true }); return 'granted'; } catch (e) { return `denied:${e.name}`; } });
  check('Electron：拒絕麥克風／攝影機權限', media.startsWith('denied'), media);
  const opened = await con.evaluate(() => { const w = window.open('https://example.com'); return !!w; });
  check('Electron：不開新視窗', !opened);
  await stage.waitForFunction(() => window.__engine.getState().phase === 'story_waiting', null, { timeout: 10000 });
  await sleep(500);
  await shot(con, 'electron_console.png');
  await shot(stage, 'electron_stage.png');
  // 舞台視窗失焦不暫停（backgroundThrottling 關閉）
  await con.evaluate(() => window.focus());
  await sleep(400);
  await con.keyboard.press('PageDown');
  await sleep(2500);
  s = await sst(stage);
  check('Electron：焦點在控制台時舞台照常播放（不因失焦降速或暫停）', s.cueId === 'a2_c002' && s.phase === 'playing' && !s.paused && s.cueTime > 1.5, `t=${s.cueTime}`);
  check('Electron：過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
  await eapp.close();

  const single = await launch(['--single', '--windowed', '--cues=demo']);
  await sleep(4000);
  const sw = single.windows();
  check('Electron：單一視窗模式只開舞台（同步顯示時的版面）', sw.length === 1 && sw[0].url().includes('stage.html'), sw.map((w) => w.url().split('/').pop()).join('、'));
  if (sw[0]) {
    await sw[0].waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 60000 });
    await sw[0].keyboard.press('PageDown');
    await sw[0].waitForFunction(() => window.__engine.getState().phase === 'title_idle', null, { timeout: 20000 }).catch(() => undefined);
    check('Electron 單一視窗：簡報筆在舞台上直接「準備播放」（不必點滑鼠）', (await sst(sw[0])).phase === 'title_idle');
  }
  await single.close();
}

// ======================================================================= 結果
const failed = results.filter((r) => !r.ok);
writeFileSync(join(OUT, 'console_test.json'), JSON.stringify({ at: new Date().toISOString(), passed: results.length - failed.length, total: results.length, electron: electronExe ? electronExe.replace(homedir(), '~') : null, screenshots: shots, results }, null, 2));
console.log(`\n共 ${results.length} 項，通過 ${results.length - failed.length}，失敗 ${failed.length}。截圖 ${shots.length} 張 → review/G5/console/`);
process.exit(failed.length ? 1 : 0);
