// G6 全劇驗收包產生器（v1.3 第 8 節「自動驗收」、v1.2 第 24 節門檻；驗收包由 tools/ 腳本產生，製作代理不挑畫面）。
//
// 用法（專案根目錄；先 cd app && npm run build，九段驗收包在 review/G5/<段>/pack）：
//   caffeinate -i node tools/show_review_pack.mjs                       → review/G6/pack/（全部，約 40 分鐘）
// 選項：
//   --out <資料夾>        輸出位置（預設 review/G6/pack）
//   --packs <資料夾>      九段驗收包的根目錄（預設 review/G5；每段在 <packs>/<段>/pack）
//   --skip-live           不跑即時播放（沿用 <out>/live/live_raw.json；INDEX 會比對那次記下的建置，不同就標「沿用舊建置的數據」）
//   --skip-seams          不重新擷取段落接縫（沿用 <out>/seams/seams_raw.json）
//   --skip-ops            不跑全劇操作補測（沿用 <out>/ops/ops_show.json）
//   --engine-test-log <檔> 引用已存在的 engine-test 輸出（不重跑）；預設重跑 node tools/engine-test.mjs 並存 <out>/ops/engine_test.log
//   --skip-engine-test    不跑也不引用 engine-test（操作節只列全劇補測）
//   --gap 0.8             即時播放時，每段播完停住後隔幾秒按下一步（教師停格用短間隔）
//   --quiz-wait 1.6       出題畫面停住後等幾秒才按（同時確認不會自動揭答）
//   --headed              用有視窗的 Chrome 跑即時播放（預設無頭；兩者都用 Apple M4 GPU）
//   --perf-only           只跑即時播放效能（＋卡頓那幾格的擷取），其他各節沿用上次的結果，再重產 INDEX.md
//   --index-only          只重跑段落指紋比對、Python 彙整與 INDEX.md
//
// 產出（INDEX.md 只列數字與檔案）：
//   show_timeline.json         目前建置的全劇時間軸（buildTimelines，與引擎相同）
//   (a) packs/                 九段驗收包彙整：與建置一致（段落 sha1，去掉 checkpoint 欄：packs/segment_hashes.json）、長度、響度（段落響度差 ±1 LU）、
//                              光敏通過判定（含孤立單格亮度比 ≤ 1.2）、字幕時間差、安全量測；全劇時長＋教師時間 ≤ 38 分
//   (b) live/                  即時播放效能：影格時間第 95 百分位、>100 ms 卡頓（發生的 cue、是否在對白或揭答中、是否在 fade 黑格內〔全畫面亮度 < 0.05，
//                              live/stall_frames/ 用擷取模式重畫卡頓前後那一格〕）、播放中／停格（逐格記錄 cueTime ≥ cue 長度＝停格）、JS heap／程序記憶體走勢、
//                              開頁到片頭待機的載入時間、字幕與語音時間差（voiceSync）、嘴型、網路紀錄
//   (c) seams/                 段落接縫（a0→a1 … a7→a8）：前段最後一格｜後段第一格｜後段第一個全亮格並排、亮度差、接縫 30 格／秒光敏
//   (d) live/network.json      離線：所有請求，外部請求數
//   (e) ops/                   操作：engine-test 引用結果＋全劇模式補測（連按、長按、上一步、暫停、重播、頁面隱藏、凍結、休眠）
//   (f) attribution/           署名卡：片頭與片尾的 DOM 文字與截圖
//   (g) quiz/                  八題：逐題出題→揭答→等待→續演、答案與題卡核對
//   (h) delivery/              交付包冒煙測試結果（tools/delivery_smoke.mjs 另外跑、寫在這裡；INDEX.md 有結果才列）
//   build_check.json           建置指紋（G7 修正第 1 輪，技術 QA G2）：每節新跑時在 <節>/build.json 記下 app/dist 的 app.js 與 cues_show.js sha1；
//                              沿用舊資料（--skip-live、--skip-seams、--skip-ops、--engine-test-log、--perf-only、--index-only）時與目前 app/dist 比對，
//                              INDEX.md 在該節開頭寫明「本次量測」「沿用、同一建置」或「沿用舊建置的數據」（列出兩邊 sha1）
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { loadavg } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { packTimelineCues, segmentFingerprints, timelineSha1 } from './seg_fingerprint.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const esbuild = require('esbuild');
const PYTHON = process.env.PYTHON ?? '/opt/anaconda3/bin/python3';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const OUT = resolve(ROOT, opt('--out', 'review/G6/pack'));
const PACKS = resolve(ROOT, opt('--packs', 'review/G5'));
const GAP = Number(opt('--gap', '0.8'));
const QUIZ_WAIT = Number(opt('--quiz-wait', '1.6'));
const W = 1920, H = 1080, FPS = 30;
const ANSWERS = [2, 3, 1, 1, 3, 2, 3, 2];
const SIGNATURE = '許博明老師製作';
const dist = join(ROOT, 'app/dist/index.html');
const distUrl = pathToFileURL(dist).href;
if (!existsSync(dist)) { console.error('[g6pack] 找不到 app/dist/index.html，請先在 app/ 執行 npm run build'); process.exit(1); }
for (const d of ['', 'packs', 'live', 'seams', 'ops', 'attribution', 'quiz']) mkdirSync(join(OUT, d), { recursive: true });

const t0 = Date.now();
const log = (s) => console.log(`[g6pack ${((Date.now() - t0) / 1000).toFixed(0).padStart(5)}s] ${s}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const r3 = (x) => Math.round(x * 1000) / 1000;
const isExternal = (u) => !/^(file|data|blob|about|chrome|chrome-extension|devtools):/.test(u);
const runPy = (...a) => { const r = spawnSync(PYTHON, [join(ROOT, 'tools/show_review_pack.py'), ...a], { stdio: 'inherit', cwd: ROOT }); if (r.status !== 0) { console.error('[g6pack] Python 彙整失敗'); process.exit(r.status ?? 1); } };


// ---------------------------------------------------------------- 0. 目前建置的全劇時間軸（與引擎、act_review_pack.mjs 同一個 buildTimelines）
const readPack = (file, id) => JSON.parse(readFileSync(join(ROOT, 'app/dist/data', file), 'utf8').replace(new RegExp(`^[\\s\\S]*?window\\.__pack\\(${JSON.stringify(id).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')},`), '').replace(/\);\s*$/, ''));
const manifest = readPack('manifest.js', 'manifest');
const show = readPack(manifest.cueSets.show, 'cues:show');
const bundle = async (rel) => {
  const r = await esbuild.build({ entryPoints: [join(ROOT, rel)], bundle: true, format: 'esm', platform: 'node', write: false, logLevel: 'silent' });
  return import(`data:text/javascript;base64,${Buffer.from(r.outputFiles[0].text).toString('base64')}`);
};
const { buildTimelines } = await bundle('app/src/cues/timeline.ts');
const engineSrc = readFileSync(join(ROOT, 'app/src/engine/engine.ts'), 'utf8');

// ---------------------------------------------------------------- 建置指紋（G7 修正第 1 輪，技術 QA G2）
// 每節新跑時把目前 app/dist 的 app.js、cues_show.js sha1 記進 <節>/build.json（也寫進原始資料檔）；沿用舊資料時拿來和目前建置比
const sha1Of = (p) => (existsSync(p) ? createHash('sha1').update(readFileSync(p)).digest('hex') : null);
const BUILD = {
  appJsSha1: sha1Of(join(ROOT, 'app/dist/app.js')), cuesShowFile: manifest.cueSets.show ?? null,
  cuesShowSha1: manifest.cueSets.show ? sha1Of(join(ROOT, 'app/dist/data', manifest.cueSets.show)) : null,
  distBuiltAt: manifest.builtAt ?? null, appJsMtime: existsSync(join(ROOT, 'app/dist/app.js')) ? statSync(join(ROOT, 'app/dist/app.js')).mtime.toISOString() : null,
};
/** 各節的資料檔與建置紀錄：live＝(b)(d)(f)(g)、seams＝(c)、ops＝(e) 全劇補測、engine_test＝(e) engine-test */
const SECTIONS = {
  live: { data: 'live/live_raw.json', build: 'live/build.json', option: '--skip-live', rerun: '不加 --skip-live 重跑（或只用 --perf-only 重跑這一節）', rerunMin: 27 },
  seams: { data: 'seams/seams_raw.json', build: 'seams/build.json', option: '--skip-seams', rerun: '不加 --skip-seams 重跑', rerunMin: 5 },
  ops: { data: 'ops/ops_show.json', build: 'ops/build.json', option: '--skip-ops', rerun: '不加 --skip-ops 重跑', rerunMin: 3 },
  engine_test: { data: 'ops/engine_test.log', build: 'ops/engine_test.build.json', option: '--engine-test-log／--skip-engine-test', rerun: '不加 --engine-test-log／--skip-engine-test 重跑', rerunMin: 6 },
};
const fresh = new Set();
function recordBuild(section, extra = {}) {
  fresh.add(section);
  writeFileSync(join(OUT, SECTIONS[section].build), JSON.stringify({ ...BUILD, measuredAt: new Date().toISOString(), ...extra }, null, 1));
}
function writeBuildCheck() {
  const sections = {};
  for (const [k, v] of Object.entries(SECTIONS)) {
    const dataP = join(OUT, v.data), buildP = join(OUT, v.build);
    const row = { data: v.data, option: v.option, rerun: v.rerun, rerunMin: v.rerunMin, exists: existsSync(dataP), fresh: fresh.has(k), recorded: null };
    if (row.exists) row.dataMtime = statSync(dataP).mtime.toISOString();
    if (existsSync(buildP)) { try { row.recorded = JSON.parse(readFileSync(buildP, 'utf8')); } catch { row.recorded = null; } }
    if (!row.exists) row.status = 'missing';
    else if (row.fresh) row.status = 'fresh';
    else if (row.recorded?.appJsSha1) {
      row.appJsMatch = row.recorded.appJsSha1 === BUILD.appJsSha1;
      row.cuesShowMatch = row.recorded.cuesShowSha1 === BUILD.cuesShowSha1;
      row.status = row.appJsMatch && row.cuesShowMatch ? 'reused_same_build' : 'reused_other_build';
    } else {
      // 舊版工具產生的資料、或引用的 engine-test log，沒有記錄建置：退而比較檔案時間（資料比目前 app.js 舊＝一定不是用目前建置量的）
      row.comparedTime = row.recorded?.citedMtime ?? row.dataMtime;
      row.olderThanBuild = !!BUILD.appJsMtime && row.comparedTime < BUILD.appJsMtime;
      row.status = row.olderThanBuild ? 'reused_other_build' : 'reused_unknown_build';
    }
    sections[k] = row;
  }
  writeFileSync(join(OUT, 'build_check.json'), JSON.stringify({ note: '建置指紋：current＝目前 app/dist；sections.<節>.recorded＝那一節資料量測時記下的建置（<節>/build.json）。status：fresh＝本次量測；reused_same_build＝沿用、sha1 相同；reused_other_build＝沿用舊建置的數據（sha1 不同，或舊資料沒有記錄 sha1 且檔案時間早於目前 app.js）；reused_unknown_build＝沿用、沒有記錄 sha1 且無法判斷；missing＝沒有資料。',
    generated: new Date().toISOString(), current: BUILD, sections }, null, 1));
  const stale = Object.entries(sections).filter(([, r]) => r.status === 'reused_other_build').map(([k]) => k);
  log(`建置指紋：app.js ${BUILD.appJsSha1?.slice(0, 12)}、${BUILD.cuesShowFile} ${BUILD.cuesShowSha1?.slice(0, 12)}；${stale.length ? `沿用舊建置的數據：${stale.join('、')}` : '沒有沿用舊建置的數據'}`);
}
const PREROLL = Number(/export const PREROLL_SEC = ([\d.]+)/.exec(engineSrc)[1]);
const MUSIC_LEVEL = Function(`return (${/const MUSIC_LEVEL[^=]*=\s*(\{[^}]*\})/.exec(engineSrc)[1]})`)();
const WAIT_GUARD_MS = Number(/WAIT_GUARD_MS\s*=\s*(\d+)/.exec(engineSrc)?.[1] ?? 350);
const timelines = buildTimelines(show, (id) => manifest.audio[id]?.duration ?? undefined);
const segOf = new Map(show.segments.flatMap((s) => s.cueIds.map((id) => [id, s.id])));
const showTl = {
  note: 'buildTimelines（app/src/cues/timeline.ts）解析目前 app/dist 的全劇 cue 集；preroll＝enterFade > 0 時的換景漸暗預捲（engine PREROLL_SEC）。',
  built: manifest.built ?? null, prerollSec: PREROLL, waitGuardMs: WAIT_GUARD_MS, answersExpected: ANSWERS,
  segments: show.segments.map((s) => ({ id: s.id, title: s.title, file: s.file, cueIds: s.cueIds })),
  cues: timelines.map((t) => ({
    id: t.cue.id, segment: segOf.get(t.cue.id) ?? null, kind: t.cue.kind, title: t.cue.title, duration: r3(t.duration), autoAdvance: !!t.cue.autoAdvance,
    set: t.set, enterFade: t.enterFade, preroll: t.enterFade > 0 ? PREROLL : 0, quiz: t.quiz ? { qid: t.quiz.qid, number: t.quiz.number, answer: t.quiz.answer, question: t.quiz.question, options: t.quiz.options } : null,
    lamp: t.cue.lamp ?? null,
    lines: t.lines.map((l) => ({ id: l.line.id, speaker: l.line.speaker, text: l.line.text, actorIds: l.actorIds ?? (l.actorId ? [l.actorId] : []), start: r3(l.start), end: r3(l.end) })),
  })),
};
// ---------------------------------------------------------------- (a) 段落指紋：驗收包記下的 sha1 與目前段落檔、app/dist 比對（G6 修正：不再只比 cue 長度）
async function writeSegmentHashes() {
  const fp = await segmentFingerprints();
  const rows = {};
  for (const [seg, cur] of Object.entries(fp.segments)) {
    const p = join(PACKS, seg, 'pack', 'segment_hash.json');
    const pk = existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')) : null;
    // 後備（舊包沒有指紋時參考）：包裡 timeline.json 的解析後時間軸＝目前建置解析後的時間軸（不含 initialState 的站位與鏡位）
    const ptl = join(PACKS, seg, 'pack', 'timeline.json');
    const segInfo = show.segments.find((x) => x.id === seg);
    let timelineMatch = null;
    if (existsSync(ptl) && segInfo) {
      const packCues = JSON.parse(readFileSync(ptl, 'utf8')).cues ?? [];
      const curCues = packTimelineCues(segInfo.cueIds.map((id) => timelines.find((t) => t.cue.id === id)).filter(Boolean), MUSIC_LEVEL);
      timelineMatch = timelineSha1(packCues) === timelineSha1(curCues);
    }
    rows[seg] = {
      file: cur.file, current: { source: cur.source, built: cur.built, sourceMerged: cur.sourceMerged, builtFromSource: cur.builtFromSource },
      pack: pk ? { source: pk.source ?? null, built: pk.built ?? null, generatedAt: pk.generatedAt ?? null } : null,
      // 產生期間 app/dist 被重建過（distChangedDuringRun）的包不算一致
      builtMatch: pk && pk.built ? pk.built === cur.built && !pk.distChangedDuringRun : null, sourceMatch: pk && pk.source ? pk.source === cur.source : null,
      distChangedDuringRun: pk ? !!pk.distChangedDuringRun : null,
      timelineMatch,
    };
  }
  writeFileSync(join(OUT, 'packs', 'segment_hashes.json'), JSON.stringify({
    note: '與建置一致＝驗收包記下的 built（量的那一版 app/dist 合併後的段落）＝目前 app/dist 的 built；sourceMatch＝段落檔 sha1 相同；builtFromSource＝目前 app/dist 是用目前段落檔建的。pack＝null：舊版工具產生的包沒有記錄（要重產）；timelineMatch＝後備參考：包裡解析後的時間軸（timeline.json cues）與目前建置相同（不含 initialState 的站位與鏡位）。',
    method: fp.method, distBuiltAt: fp.distBuiltAt, sourceValid: fp.sourceValid, segments: rows,
  }, null, 1));
  const ok = Object.values(rows).filter((r) => r.builtMatch).length;
  log(`段落指紋：驗收包與目前建置一致 ${ok}／${Object.keys(rows).length} 段${Object.values(rows).some((r) => !r.current.builtFromSource) ? '；注意：app/dist 有段落不是用目前段落檔建的' : ''}`);
}
await writeSegmentHashes();
// --index-only：沿用上次的 show_timeline.json（即時播放量測的 cue 序號對的是那一版），只重比段落指紋與重產 INDEX.md
if (has('--index-only')) { writeBuildCheck(); runPy(OUT, PACKS); process.exit(0); }
writeFileSync(join(OUT, 'show_timeline.json'), JSON.stringify(showTl, null, 1));
log(`全劇時間軸：${timelines.length} 個 cue、${show.segments.length} 段`);

const LAUNCH_ARGS = ['--autoplay-policy=no-user-gesture-required', '--enable-precise-memory-info', '--mute-audio', '--force-device-scale-factor=1', '--hide-scrollbars', `--window-size=${W},${H}`];

async function newPage(browser, query, net) {
  const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`[console] ${m.text()}`); });
  if (net) {
    page.on('request', (r) => net.requests.push({ url: r.url().startsWith('file:') ? r.url().replace(pathToFileURL(ROOT).href, '<ROOT>') : r.url(), type: r.resourceType(), external: isExternal(r.url()) }));
    page.on('requestfailed', (r) => net.failed.push({ url: r.url().replace(pathToFileURL(ROOT).href, '<ROOT>'), error: r.failure()?.errorText ?? '' }));
  }
  await page.goto(`${distUrl}?${query}`);
  return { context, page, errors };
}
const st = (page) => page.evaluate(() => window.__engine.getState());
const waitFor = (page, fn, arg, timeout = 15000) => page.waitForFunction(fn, arg, { timeout, polling: 50 });

// ---------------------------------------------------------------- (b)(d)(f)(g) 即時播放：從片頭按到片尾
async function liveRun() {
  const browser = await chromium.launch({ channel: 'chrome', headless: !has('--headed'), args: LAUNCH_ARGS });
  const bcdp = await browser.newBrowserCDPSession();
  const net = { requests: [], failed: [] };
  const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  // 影格時間：獨立的 requestAnimationFrame 迴圈記下每一格的時間戳（引擎那一格做太久，下一格就會晚到）；長動畫格（long-animation-frame）；
  // 每 200 ms 記一次引擎狀態（cue、階段、cue 內秒數、發聲中的對白、暫停、字幕、題卡、fps），說話時另記嘴型
  await context.addInitScript(() => {
    const R = (window.__perfRec = { ts: [], samples: [], loaf: [], faces: [], fs: [] });
    // 逐格狀態（G6 修正）：每一格開頭記下引擎上一格做完後的狀態 [時間戳, cue 序號, cue 內秒數, 模式(1 播放／2 停住／0 其他), 調暗, 預捲秒數, 暫停]；
    // 卡頓（第 k−1 格到第 k 格的間隔）前後的畫面＝第 k−1 格與第 k 格記下的狀態；cueTime ≥ cue 長度＝停格（不再用每 200 ms 取樣推測）
    const f = (t) => {
      R.ts.push(t);
      const e = window.__engine;
      if (e && e.ready()) {
        try { const s = e.getState(); R.fs.push([Math.round(t * 100) / 100, s.cueIndex, s.cueTime, s.mode === 'playing' ? 1 : s.mode === 'waiting' ? 2 : 0, s.dim, s.prerollSec, s.paused ? 1 : 0]); } catch { /* 載入中 */ }
      }
      requestAnimationFrame(f);
    };
    requestAnimationFrame(f);
    try {
      new PerformanceObserver((l) => { for (const e of l.getEntries()) R.loaf.push([e.startTime, e.duration, e.blockingDuration ?? 0]); }).observe({ type: 'long-animation-frame', buffered: true });
    } catch { /* 舊版 Chrome 沒有 LoAF */ }
    let k = 0;
    setInterval(() => {
      const e = window.__engine;
      if (!e || !e.ready()) return;
      try {
        const s = e.getState();
        R.samples.push([performance.now(), s.cueId, s.phase, s.cueTime, s.voSounding, s.paused ? 1 : 0, s.subtitle, s.quizVisible ? 1 : 0, s.fps, s.mode]);
        if (s.voSounding > 0 && (k++ % 1 === 0)) R.faces.push([performance.now(), s.cueId, s.cueTime, e.debug.faces()]);
      } catch { /* 載入中 */ }
    }, 200);
  });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Performance.enable');
  const errors = [];
  page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`[console] ${m.text()}`); });
  page.on('request', (r) => net.requests.push({ url: r.url().startsWith('file:') ? r.url().replace(pathToFileURL(ROOT).href, '<ROOT>') : r.url(), type: r.resourceType(), external: isExternal(r.url()) }));
  page.on('requestfailed', (r) => net.failed.push({ url: r.url().replace(pathToFileURL(ROOT).href, '<ROOT>'), error: r.failure()?.errorText ?? '' }));

  const raw = { ts: [], fs: [], samples: [], loaf: [], faces: [], memory: [], voiceSync: [], visits: [], quiz: [], attribution: {}, load: {}, system: {}, presses: [] };
  const drain = async () => {
    const d = await page.evaluate(() => { const r = window.__perfRec; return r ? { ts: r.ts.splice(0), fs: r.fs.splice(0), samples: r.samples.splice(0), loaf: r.loaf.splice(0), faces: r.faces.splice(0) } : null; });
    if (d) { raw.ts.push(...d.ts.map((x) => Math.round(x * 100) / 100)); for (const x of d.fs) raw.fs.push(x); raw.samples.push(...d.samples); raw.loaf.push(...d.loaf); raw.faces.push(...d.faces); }
  };
  const procMem = async () => {
    try {
      const { processInfo } = await bcdp.send('SystemInfo.getProcessInfo');
      const pids = processInfo.map((p) => p.id).filter(Boolean);
      const out = execFileSync('ps', ['-o', 'pid=,rss=', '-p', pids.join(',')], { encoding: 'utf8' });
      const rss = Object.fromEntries(out.trim().split('\n').map((l) => l.trim().split(/\s+/).map(Number)));
      const byType = {};
      for (const p of processInfo) byType[p.type] = (byType[p.type] ?? 0) + (rss[p.id] ?? 0) / 1024;
      return byType;
    } catch { return null; }
  };
  const memSample = async (label) => {
    const m = await cdp.send('Performance.getMetrics');
    const g = Object.fromEntries(m.metrics.map((x) => [x.name, x.value]));
    const pm = await page.evaluate(() => (performance.memory ? { used: performance.memory.usedJSHeapSize, total: performance.memory.totalJSHeapSize, limit: performance.memory.jsHeapSizeLimit } : null));
    const s = await page.evaluate(() => { try { const x = window.__engine?.getState(); return x ? [x.cueId, x.phase] : [null, null]; } catch { return [null, null]; } });
    raw.memory.push({ t: Date.now() - tStart, label, cue: s[0], phase: s[1], jsHeapUsedMB: r3((g.JSHeapUsedSize ?? 0) / 1048576), jsHeapTotalMB: r3((g.JSHeapTotalSize ?? 0) / 1048576),
      perfMemoryUsedMB: pm ? r3(pm.used / 1048576) : null, nodes: g.Nodes, listeners: g.JSEventListeners, processRssMB: await procMem(), loadavg1: loadavg()[0] });
  };

  // 載入：開頁 → 準備畫面可按 → 按「準備播放」→ 片頭待機
  const tStart = Date.now();
  raw.load.loadavg_before = loadavg();
  await page.goto(`${distUrl}?cues=show`);
  raw.load.goto_ms = Date.now() - tStart;
  await page.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing' && !document.querySelector('.ready-btn')?.disabled, null, { timeout: 300000, polling: 100 });
  raw.load.ready_button_ms = Date.now() - tStart;
  await memSample('準備畫面');
  const nav = await page.evaluate(() => { const n = performance.getEntriesByType('navigation')[0]; return n ? { domContentLoaded: n.domContentLoadedEventEnd, load: n.loadEventEnd } : null; });
  raw.load.navigation = nav;
  const tClick = Date.now();
  await page.click('.ready-btn');
  await waitFor(page, () => window.__engine.getState().phase === 'title_idle', null, 300000);
  raw.load.ready_click_to_title_ms = Date.now() - tClick;
  raw.load.open_to_title_idle_ms = Date.now() - tStart;
  raw.load.warm_ms = await page.evaluate(() => window.__engine.debug.warmMs());
  const s0 = await st(page);
  raw.system = { gpu: s0.gpu, clock: s0.clock, audioState: s0.audioState, quality: s0.quality, lock30: s0.lock30, headless: !has('--headed'),
    userAgent: await page.evaluate(() => navigator.userAgent), fullscreen: await page.evaluate(() => !!document.fullscreenElement), viewport: [W, H], gapSec: GAP, quizWaitSec: QUIZ_WAIT };
  log(`即時播放：載入 ${raw.load.ready_button_ms} ms、按「準備播放」到片頭待機 ${raw.load.ready_click_to_title_ms} ms；GPU ${s0.gpu}；時鐘 ${s0.clock}`);
  // (f) 片頭署名卡
  const sig = async () => page.evaluate(() => ({ text: document.querySelector('#title-card .sig-text')?.textContent ?? null, hidden: document.getElementById('title-card')?.hidden ?? null,
    opacity: (() => { const e = document.getElementById('title-card'); return e ? getComputedStyle(e).opacity : null; })() }));
  await sleep(1500);
  raw.attribution.start = { ...(await sig()), cueId: s0.cueId, phase: s0.phase, titleCard: s0.world?.titleCard ?? null };
  await page.screenshot({ path: join(OUT, 'attribution', 'title_start.png') });
  await memSample('片頭待機');
  await drain();

  // 從片頭按到片尾
  const press = async (why) => { raw.presses.push({ t: await page.evaluate(() => performance.now()), why }); await page.keyboard.press('PageDown'); };
  const quizDom = () => page.evaluate(() => ({
    visible: !document.getElementById('quiz-card')?.hidden, question: document.querySelector('#quiz-card .quiz-q')?.textContent ?? null,
    options: [...document.querySelectorAll('#quiz-card .quiz-opt')].map((e) => ({ cls: e.className, text: e.querySelector('.opt-text')?.textContent ?? e.textContent })),
    correct: [...document.querySelectorAll('#quiz-card .quiz-opt.correct')].map((e) => e.className),
  }));
  let lastCue = s0.cueId;
  let lastMem = Date.now();
  let lastSync = 0;
  const deadline = Date.now() + 70 * 60 * 1000;
  await press('開演');
  let s = await st(page);
  let q = null;
  while (Date.now() < deadline) {
    s = await st(page);
    if (s.cueId !== lastCue) { raw.visits.push({ id: s.cueId, kind: s.kind, phase: s.phase, at: await page.evaluate(() => performance.now()), wall: Date.now() - tStart }); lastCue = s.cueId; }
    if (s.mode === 'playing') {
      if (s.voSounding > 0 && Date.now() - lastSync > 1000) { lastSync = Date.now(); const sy = await page.evaluate(() => window.__engine.debug.voiceSync()); raw.voiceSync.push({ cue: s.cueId, t: s.cueTime, rows: sy }); }
      if (Date.now() - lastMem > 5000) { lastMem = Date.now(); await memSample('播放'); await drain(); }
      await sleep(80);
      continue;
    }
    if (s.mode !== 'waiting') { await sleep(100); continue; }
    if (s.phase === 'ended') break;
    // 停住等老師
    if (s.phase === 'quiz_shown') {
      const cue = showTl.cues.find((c) => c.id === s.cueId);
      const shown = await quizDom();
      await sleep(QUIZ_WAIT * 1000);
      const s2 = await st(page);
      q = { cue: s.cueId, qid: cue.quiz?.qid, number: cue.quiz?.number, answerData: cue.quiz?.answer, answerExpected: ANSWERS[(cue.quiz?.number ?? 0) - 1],
        shown, noAutoReveal: !s2.revealed && s2.phase === 'quiz_shown' && (await quizDom()).correct.length === 0, waitedSec: QUIZ_WAIT };
      await press('揭答');
      await waitFor(page, () => window.__engine.getState().phase === 'reveal_playing', null, 5000).catch(() => undefined);
      q.revealPhase = (await st(page)).phase;
      raw.quiz.push(q);
      continue;
    }
    if (s.phase === 'reveal_waiting' && q && !q.revealed) {
      const dom = await quizDom();
      q.revealed = { cue: s.cueId, correct: dom.correct, lampsLit: s.lampsLit, revealedFlag: s.revealed };
    }
    if (s.kind === 'lamp' && q && !q.lamp) q.lamp = { cue: s.cueId, lampsLit: s.lampsLit, phase: s.phase };
    await sleep(GAP * 1000);
    const before = s.cueId;
    await press('下一步');
    await waitFor(page, (id) => { const x = window.__engine.getState(); return x.mode === 'playing' || x.cueId !== id; }, before, 5000).catch(() => undefined);
    if (q && q.lamp && !q.next) { const x = await st(page); if (x.cueId !== q.lamp.cue) q.next = { cue: x.cueId, kind: x.kind, phase: x.phase }; }
  }
  const sEnd = await st(page);
  raw.end = { cueId: sEnd.cueId, phase: sEnd.phase, lampsLit: sEnd.lampsLit, wall_ms: Date.now() - tStart, timedOut: Date.now() >= deadline };
  await sleep(1500);
  raw.attribution.end = { ...(await sig()), cueId: sEnd.cueId, phase: sEnd.phase, titleCard: (await st(page)).world?.titleCard ?? null };
  await page.screenshot({ path: join(OUT, 'attribution', 'title_end.png') });
  await memSample('片尾署名卡');
  await drain();
  raw.errors = errors;
  raw.net = net;
  raw.fsNote = 'fs：逐格狀態 [rAF 時間戳 ms, cue 序號（show_timeline.json cues 的索引）, cue 內秒數, 模式 1 播放／2 停住／0 其他, 調暗, 預捲秒數, 暫停]，每一格開頭記下引擎上一格做完後的狀態。';
  raw.cdpNote = 'jsHeapUsedMB＝CDP Performance.getMetrics JSHeapUsedSize；perfMemoryUsedMB＝performance.memory（--enable-precise-memory-info）；processRssMB＝SystemInfo.getProcessInfo 的各程序 ps RSS（macOS，依程序類型加總，MB）。';
  await browser.close();
  raw.build = BUILD;
  writeFileSync(join(OUT, 'live', 'live_raw.json'), JSON.stringify(raw));
  recordBuild('live');
  writeFileSync(join(OUT, 'live', 'network.json'), JSON.stringify({ requests: net.requests.length, external: net.requests.filter((r) => r.external), failed: net.failed,
    byType: net.requests.reduce((m, r) => ((m[r.type] = (m[r.type] ?? 0) + 1), m), {}), list: net.requests }, null, 1));
  log(`即時播放完成：${raw.visits.length} 段、${raw.ts.length} 格、最後 ${raw.end.cueId} ${raw.end.phase}、${(raw.end.wall_ms / 60000).toFixed(1)} 分`);
}

// ---------------------------------------------------------------- (b) 卡頓那幾格：用擷取模式重畫卡頓前、後的畫面（量全畫面亮度，分「在 fade 黑格內／不在」）
// 第 k−1 格到第 k 格的間隔 > 100 ms：卡住時畫面上是第 k−1 格記下的狀態（before），卡完換成第 k 格的狀態（after）。
// 預捲（cueTime 0、prerollSec > 0、離按鍵 < 預捲秒數）重畫成上一個 cue 漸暗中的那一格（seek 負秒數）；停格重畫成 cue 最後一格。
const STALL_MS = 100;
const MAX_STALL_SHOTS = 60;
async function stallFrames() {
  const rawPath = join(OUT, 'live', 'live_raw.json');
  if (!existsSync(rawPath)) return;
  const raw = JSON.parse(readFileSync(rawPath, 'utf8'));
  const fsr = raw.fs ?? [];
  const pressT = (raw.presses ?? []).map((p) => p.t).sort((a, b) => a - b);
  const dir = join(OUT, 'live', 'stall_frames');
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const target = (r) => {
    const c = showTl.cues[r[1]];
    if (!c) return null;
    const [t, , cueTime, mode, dim, pre] = r;
    let seekT = cueTime;
    let kind = 'play';
    if (mode !== 1 || cueTime >= c.duration - 1e-3) { seekT = c.duration + 0.001; kind = 'hold'; }
    else if (cueTime <= 1e-6 && pre > 0) {
      const p = [...pressT].reverse().find((x) => x <= t);
      const el = p === undefined ? pre : (t - p) / 1000;
      if (el < pre) { seekT = -pre + el; kind = 'preroll'; }
    }
    return { cue: c.id, cueTime, mode, dim, seekT: r3(seekT), kind };
  };
  const list = [];
  const tFirst = pressT[0] ?? -Infinity; // 開演（第一次按下一步）之後才算，和 show_review_pack.py 相同
  for (let k = 1; k < fsr.length; k++) {
    const iv = fsr[k][0] - fsr[k - 1][0];
    if (iv > STALL_MS && fsr[k][0] >= tFirst) list.push({ k, t: fsr[k][0], interval_ms: r3(iv), before: target(fsr[k - 1]), after: target(fsr[k]) });
  }
  const shots = list.slice(0, MAX_STALL_SHOTS);
  if (shots.length) {
    const browser = await chromium.launch({ channel: 'chrome', headless: true, args: LAUNCH_ARGS });
    const { page } = await newPage(browser, `capture=1&cues=show&q=${raw.system?.quality ?? 'A'}&step=${FPS}`, null);
    await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 300000 });
    for (const s of shots) {
      for (const side of ['before', 'after']) {
        const x = s[side];
        if (!x) continue;
        await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'before' }), x.cue);
        await page.evaluate((id) => window.__engine.capture.playCue(id), x.cue);
        await page.evaluate((t) => window.__engine.capture.seek(t), x.seekT);
        x.file = `stall_frames/k${s.k}_${side}.jpg`;
        await page.screenshot({ path: join(OUT, 'live', x.file), type: 'jpeg', quality: 92 });
      }
    }
    await browser.close();
  }
  writeFileSync(join(OUT, 'live', 'stall_frames.json'), JSON.stringify({
    note: `逐格狀態（live_raw.json fs）裡間隔 > ${STALL_MS} ms 的卡頓；before／after＝卡住時與卡完的畫面，用擷取模式（?capture=1，同畫質）重畫，最多 ${MAX_STALL_SHOTS} 個。kind：play＝播放中、preroll＝換景漸暗預捲、hold＝停格（cueTime ≥ cue 長度或停住等老師）。`,
    stalls: list.length, shots: shots.length, list,
  }, null, 1));
  log(`卡頓擷取：> ${STALL_MS} ms ${list.length} 次，重畫 ${shots.length} 組前後畫面`);
}

// ---------------------------------------------------------------- (c) 段落接縫（擷取模式，固定步長）
async function seams() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: LAUNCH_ARGS });
  const net = { requests: [], failed: [] };
  const { page, errors } = await newPage(browser, `capture=1&cues=show&q=A&step=${FPS}`, net);
  await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 300000 });
  const work = join(OUT, 'seams', '_work');
  rmSync(work, { recursive: true, force: true });
  const ev = (fn, a) => page.evaluate(fn, a);
  const seek = (t) => ev((x) => window.__engine.capture.seek(x), t);
  const shot = (p) => page.screenshot({ path: p, type: 'jpeg', quality: 92 });
  const out = [];
  for (let i = 0; i + 1 < show.segments.length; i++) {
    const A = show.segments[i], B = show.segments[i + 1];
    const prev = A.cueIds[A.cueIds.length - 1], next = B.cueIds[0];
    const dir = join(work, `${A.id}_${B.id}`);
    mkdirSync(dir, { recursive: true });
    const seq = [];
    let g = 0;
    // 前段最後一個 cue 的最後 1 秒＋停住 1 秒（停住格重複）
    await ev((id) => window.__engine.gotoCue(id, { mode: 'before' }), prev);
    await ev((x) => window.__engine.capture.playCue(x), prev);
    const sa = await st(page);
    const D = sa.cueDuration;
    const nTail = Math.min(FPS, Math.round(D * FPS));
    for (let k = nTail; k > 0; k--) { const t = D - k / FPS; await seek(t); const p = join(dir, `a_${String(nTail - k).padStart(3, '0')}.jpg`); await shot(p); seq.push([r3(g / FPS), p, prev, r3(t)]); g++; }
    await seek(D + 0.001);
    const pAfter = join(dir, 'a_after.jpg');
    await shot(pAfter);
    for (let k = 0; k < FPS; k++) { seq.push([r3(g / FPS), pAfter, prev, r3(D)]); g++; }
    // 後段第一個 cue：換景漸暗預捲（如果有）＋前 3 秒
    await ev((x) => window.__engine.capture.playCue(x), next);
    const sb = await st(page);
    const pre = sb.prerollSec || 0;
    const np = Math.round(pre * FPS);
    let firstShown = null;
    for (let k = 0; k < np; k++) { await seek(-pre + k / FPS); const p = join(dir, `b_pre_${String(k).padStart(3, '0')}.jpg`); await shot(p); seq.push([r3(g / FPS), p, next, r3(-pre + k / FPS)]); firstShown ??= p; g++; }
    const nHead = Math.min(3 * FPS, Math.round(sb.cueDuration * FPS));
    let firstLit = null;
    const lit = Math.max(sb.enterFade || 0, 0);
    for (let k = 0; k < nHead; k++) {
      await seek(k / FPS);
      const p = join(dir, `b_${String(k).padStart(3, '0')}.jpg`);
      await shot(p);
      seq.push([r3(g / FPS), p, next, r3(k / FPS)]);
      firstShown ??= p;
      if (!firstLit && k / FPS >= lit - 1e-6) firstLit = p;
      g++;
    }
    const tlA = timelines.find((t) => t.cue.id === prev), tlB = timelines.find((t) => t.cue.id === next);
    out.push({ from: A.id, to: B.id, prevCue: prev, nextCue: next, prevDuration: D, preroll: pre, enterFade: sb.enterFade, setFrom: tlA.endSet ?? tlA.set, setTo: tlB.set,
      prevLast: pAfter, nextFirstShown: firstShown, nextFirstLit: firstLit ?? firstShown, seq });
    log(`接縫 ${A.id}→${B.id}：${prev} → ${next}（預捲 ${pre} 秒、漸亮 ${sb.enterFade} 秒）${seq.length} 格`);
  }
  await browser.close();
  writeFileSync(join(OUT, 'seams', 'seams_raw.json'), JSON.stringify({ fps: FPS, seams: out, errors, externalRequests: net.requests.filter((r) => r.external), requests: net.requests.length, build: BUILD }, null, 1));
  recordBuild('seams');
}

// ---------------------------------------------------------------- (e) 全劇模式操作補測（即時、AudioContext 時鐘、正式配音）
async function opsShow() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: LAUNCH_ARGS });
  const net = { requests: [], failed: [] };
  const { page, context, errors } = await newPage(browser, 'cues=show&nofs=1', net);
  const cdp = await context.newCDPSession(page);
  await page.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing' && !document.querySelector('.ready-btn')?.disabled, null, { timeout: 300000 });
  await page.click('.ready-btn');
  await waitFor(page, () => window.__engine.getState().phase === 'title_idle', null, 300000);
  const results = [];
  const check = (name, ok, detail = '', group = '') => { results.push({ group, name, ok: !!ok, detail }); console.log(`${ok ? '  通過' : '✗ 失敗'}  ${name}${detail ? `  （${detail}）` : ''}`); };
  const S = () => st(page);
  const sync = () => page.evaluate(() => window.__engine.debug.voiceSync());
  const maxDiff = (xs) => (xs.length ? Math.max(...xs.map((x) => Math.abs(x.diffMs))) : NaN);
  const plain = (t) => (t ?? '').replace(/\s+/g, '');
  const cueOf = (id) => showTl.cues.find((c) => c.id === id);
  const activeLine = (id, t) => cueOf(id)?.lines.find((l) => t >= l.start + 0.15 && t <= l.end - 0.15) ?? null;
  const subOk = (x) => { const l = activeLine(x.cueId, x.cueTime); return !l || x.quizVisible || (x.subtitle && plain(l.text).includes(plain(x.subtitle))); };
  const mouths = async (ms) => { const seen = new Map(); const tEnd = Date.now() + ms; while (Date.now() < tEnd) { const f = await page.evaluate(() => window.__engine.debug.faces()); for (const [k, v] of Object.entries(f)) { if (v) { if (!seen.has(k)) seen.set(k, new Set()); seen.get(k).add(v.mouth); } } await sleep(60); } return seen; };
  const speakerMouth = async (x) => { const l = activeLine(x.cueId, x.cueTime); if (!l || !l.actorIds.length) return null; const m = await mouths(900); return { line: l.id, actors: l.actorIds, states: Object.fromEntries(l.actorIds.map((a) => [a, [...(m.get(a) ?? [])]])) }; };
  const playUntilLine = async (id, minIntoLine = 1.0) => {
    const c = cueOf(id);
    // 選一句夠長、而且後面還有 ≥ 8 秒的台詞（休眠模擬會讓時間往前跳 4.5 秒，不能跳出這一段）
    const l = c.lines.find((x) => x.end - x.start >= minIntoLine + 0.8 && c.duration - x.start > 8) ?? c.lines.find((x) => x.end - x.start >= minIntoLine + 0.8) ?? c.lines[0];
    await page.evaluate((x) => window.__engine.gotoCue(x, { mode: 'play' }), id);
    await waitFor(page, (t) => window.__engine.getState().cueTime > t, l.start + minIntoLine, (l.start + minIntoLine + 15) * 1000);
    return l;
  };
  await sleep(WAIT_GUARD_MS + 200); // 剛停住時的誤觸保護（WAIT_GUARD）之後才連按
  let s = await S();
  const G1 = '連按與長按';
  const ign0 = s.ignoredInputs;
  for (let i = 0; i < 5; i++) { await page.keyboard.press('PageDown'); await sleep(40); }
  s = await S();
  check('片頭待機連按 5 下：只開幕一次（其餘忽略）', s.cueId === timelines[1].cue.id && s.mode === 'playing' && s.ignoredInputs - ign0 >= 4, `${s.cueId}、忽略 ${s.ignoredInputs - ign0} 次`, G1);
  const rep0 = s.ignoredRepeats;
  await page.keyboard.down('PageDown');
  for (let i = 0; i < 8; i++) { await page.keyboard.down('PageDown'); await sleep(20); }
  await page.keyboard.up('PageDown');
  s = await S();
  check('開幕播放中長按（key repeat）：全部忽略、不跳段', s.ignoredRepeats - rep0 >= 8 && s.cueId === timelines[1].cue.id, `repeat ${s.ignoredRepeats - rep0} 次`, G1);
  // 題目：出題畫面連按 3 下只揭答一次；揭答播放中再按忽略；上一步回到未揭答
  const quizCue = showTl.cues.find((c) => c.kind === 'quiz' && c.segment !== 'a0');
  await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'after' }), quizCue.id);
  await sleep(WAIT_GUARD_MS + 150);
  const ig1 = (await S()).ignoredInputs;
  for (let i = 0; i < 3; i++) { await page.keyboard.press('PageDown'); await sleep(50); }
  s = await S();
  check(`出題畫面連按 3 下（${quizCue.id}）：只進入揭答、不會跳到點燈`, s.kind === 'reveal' && s.phase === 'reveal_playing' && s.ignoredInputs - ig1 >= 2, `${s.cueId} ${s.phase}、忽略 ${s.ignoredInputs - ig1} 次`, G1);
  await page.keyboard.press('PageUp');
  await sleep(150);
  s = await S();
  check('揭答播放中按上一步：回到出題、恢復未揭答（沒有印章、這一題的燈未亮）', s.phase === 'quiz_shown' && !s.revealed && !s.lampsLit.includes(quizCue.quiz.number)
    && (await page.locator('#quiz-card .quiz-opt.correct').count()) === 0, `${s.cueId} ${s.phase}`, G1);

  // 對白段落：暫停、重播、上一步、頁面隱藏、凍結、休眠（字幕與語音時間差 ≤ 50 ms、發聲中的對白 ≤ 1、字幕對、嘴型在動）
  const G2 = '對白中的操作（全劇正式配音）';
  const dlg = showTl.cues.filter((c) => c.kind === 'scene' && c.lines.some((l) => l.end - l.start >= 2.6 && l.actorIds.length)).map((c) => c.id);
  const pick = [dlg.find((id) => id.startsWith('a1')), dlg.find((id) => id.startsWith('a4')), dlg.find((id) => id.startsWith('a6'))].filter(Boolean);
  for (const id of pick) {
    await playUntilLine(id);
    s = await S();
    let sy = await sync();
    const mo = await speakerMouth(s);
    check(`${id} 播放中：字幕與語音時間差 ≤ 50 ms、發聲中的對白 ≤ 1、字幕是這一句`, sy.length >= 1 && maxDiff(sy) <= 50 && s.voSounding <= 1 && subOk(s), `差 ${maxDiff(sy)} ms、對白 ${s.voSounding}、字幕「${s.subtitle}」`, G2);
    if (mo) check(`${id} 說話時嘴型換片（${mo.line}，0.9 秒內 ≥ 2 種）`, Object.values(mo.states).some((v) => v.length >= 2), JSON.stringify(mo.states), G2);
    // 暫停 0.6 秒後繼續
    await page.keyboard.press('Period');
    await sleep(80);
    const p1 = await S();
    await sleep(600);
    const p2 = await S();
    await page.keyboard.press('Period');
    await sleep(450);
    sy = await sync();
    s = await S();
    check(`${id} 暫停 0.6 秒：時間停住、音訊一起停；繼續後時間差 ≤ 50 ms、對白 ≤ 1`, p1.paused && p2.paused && Math.abs(p2.cueTime - p1.cueTime) < 0.03 && p2.audioState === 'suspended' && !s.paused && maxDiff(sy.length ? sy : [{ diffMs: 0 }]) <= 50 && s.voSounding <= 1,
      `${p1.cueTime}→${p2.cueTime}、${p2.audioState}；差 ${maxDiff(sy)} ms`, G2);
    // R 重播
    const r0 = await S();
    await page.keyboard.press('r');
    await sleep(120);
    const r1 = await S();
    const l0 = cueOf(id).lines[0];
    await waitFor(page, (t) => window.__engine.getState().cueTime > t, l0.start + 0.8, (l0.start + 12) * 1000).catch(() => undefined);
    sy = await sync();
    s = await S();
    check(`${id} 按 R：同一段從頭播、舊台詞停掉；重播後時間差 ≤ 50 ms、對白 ≤ 1`, r1.cueId === id && r1.cueTime < 1 && r1.playId > r0.playId && r1.voSounding <= 1 && (sy.length === 0 || maxDiff(sy) <= 50) && s.voSounding <= 1,
      `t ${r0.cueTime}→${r1.cueTime}、差 ${maxDiff(sy)} ms`, G2);
  }
  // 頁面隱藏 → 恢復 → 老師按一下才繼續
  const idH = pick[0];
  await playUntilLine(idH);
  await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await sleep(150);
  const h1 = await S();
  await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
  await sleep(700);
  const h2 = await S();
  await page.keyboard.press('PageDown');
  await sleep(450);
  let sy = await sync();
  let h3 = await S();
  check(`${idH} 頁面隱藏：自動暫停；恢復後仍停住不發聲；按下一步只繼續同一段、時間差 ≤ 50 ms`, h1.paused && h1.pauseReason === 'hidden' && h2.paused && Math.abs(h2.cueTime - h1.cueTime) < 0.05 && h2.audioState !== 'running'
    && !h3.paused && h3.cueId === idH && h3.mode === 'playing' && (sy.length === 0 || maxDiff(sy) <= 50), `${h1.pauseReason}；${h1.cueTime}→${h2.cueTime}（${h2.audioState}）→ ${h3.cueId} ${h3.phase}；差 ${maxDiff(sy)} ms`, G2);
  // 凍結（Page Lifecycle 的 freeze／resume 事件：分頁被系統凍結、筆電闔上前常見）。無頭 Chrome 的 CDP Page.setWebLifecycleState 不會真的凍結頁面、
  // 也不送事件（實測），所以和 engine-test 的頁面隱藏一樣用合成事件測引擎的處理
  await playUntilLine(idH);
  await page.evaluate(() => document.dispatchEvent(new Event('freeze')));
  await sleep(150);
  const f1 = await S();
  await page.evaluate(() => document.dispatchEvent(new Event('resume')));
  await sleep(600);
  const f2 = await S();
  await page.keyboard.press('Period');
  await sleep(450);
  sy = await sync();
  h3 = await S();
  check(`${idH} 分頁凍結（合成 freeze／resume 事件）：自動暫停、恢復後仍停住不發聲；老師按繼續後時間差 ≤ 50 ms`, f1.paused && f1.pauseReason === 'freeze' && f2.paused && Math.abs(f2.cueTime - f1.cueTime) < 0.05 && f2.audioState !== 'running'
    && !h3.paused && h3.cueId === idH && (sy.length === 0 || maxDiff(sy) <= 50), `${f1.pauseReason}；${f1.cueTime}→${f2.cueTime}（${f2.audioState}）→ ${h3.phase}；差 ${maxDiff(sy)} ms`, G2);
  // 休眠偵測：畫面更新中斷 > 4 秒（主執行緒卡 4.5 秒模擬系統睡眠喚醒）
  await playUntilLine(idH);
  await page.evaluate(() => { const t = performance.now(); while (performance.now() - t < 4500) { /* 模擬休眠：畫面更新中斷 */ } });
  await sleep(500);
  const z1 = await S();
  await sleep(600);
  const z2 = await S();
  await page.keyboard.press('Period');
  await sleep(450);
  sy = await sync();
  h3 = await S();
  check(`${idH} 畫面更新中斷 4.5 秒（模擬休眠喚醒）：自動暫停、之後不自行播放；老師按繼續後時間差 ≤ 50 ms`, z1.paused && z1.pauseReason === 'sleep' && z2.paused && Math.abs(z2.cueTime - z1.cueTime) < 0.05 && !h3.paused && (sy.length === 0 || maxDiff(sy) <= 50),
    `${z1.pauseReason}、${z1.cueTime}→${z2.cueTime} → ${h3.phase}；差 ${maxDiff(sy)} ms`, G2);
  // 上一步：對白中按上一步 → 回到上一個穩定節點、聲音全停
  await playUntilLine(idH);
  await page.keyboard.press('PageUp');
  await sleep(200);
  s = await S();
  const prevStable = timelines.find((t) => t.cue.id === idH).prevStableIndex;
  check(`${idH} 對白中按上一步：回到上一個穩定節點（${timelines[prevStable]?.cue.id}）、發聲中的對白 0、字幕收起`, s.cueId === timelines[prevStable]?.cue.id && s.mode === 'waiting' && s.voSounding === 0 && !s.subtitle,
    `${s.cueId} ${s.phase}、對白 ${s.voSounding}、字幕「${s.subtitle}」`, G2);
  // 跨段上一步：每段第一個 cue 播放中按上一步 → 回到前一段最後的停格
  const G3 = '跨段上一步與重播';
  const cross = [];
  for (let i = 1; i < show.segments.length; i++) {
    const first = show.segments[i].cueIds[0];
    const tl = timelines.find((t) => t.cue.id === first);
    await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'play' }), first);
    await sleep(900);
    await page.keyboard.press('PageUp');
    await sleep(250);
    const x = await S();
    const want = timelines[tl.prevStableIndex]?.cue.id ?? null;
    cross.push(`${first}→${x.cueId}`);
    if (x.cueId !== want || x.mode !== 'waiting' || x.voSounding !== 0) check(`跨段上一步 ${first}`, false, `${x.cueId}（應為 ${want}）${x.phase}`, G3);
  }
  check('每段第一個 cue 播放中按上一步：回到前一段最後的穩定節點、聲音停', !results.some((r) => r.group === G3 && !r.ok), cross.join('、'), G3);
  check('全劇操作補測沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '), '');
  await browser.close();
  writeFileSync(join(OUT, 'ops', 'ops_show.json'), JSON.stringify({ note: '全劇模式（?cues=show&nofs=1）、即時 AudioContext 時鐘、正式配音（v04）；無頭 Chrome（Apple M4 GPU，--mute-audio）。', results,
    externalRequests: net.requests.filter((r) => r.external), requests: net.requests.length, build: BUILD }, null, 1));
  recordBuild('ops');
  log(`全劇操作補測：${results.filter((r) => r.ok).length}／${results.length} 通過`);
}

// ---------------------------------------------------------------- 執行
const PERF_ONLY = has('--perf-only');
if (!has('--skip-ops') && !PERF_ONLY) await opsShow();
if (!has('--skip-engine-test') && !PERF_ONLY) {
  const given = opt('--engine-test-log', '');
  if (given) {
    // 引用別人跑的 log：不知道是哪個建置（沒有 sha1），只記引用的檔與它的時間，INDEX 依時間判斷是否早於目前建置
    writeFileSync(join(OUT, 'ops', 'engine_test.log'), `# 引用：${given}\n` + readFileSync(resolve(ROOT, given), 'utf8'));
    writeFileSync(join(OUT, SECTIONS.engine_test.build), JSON.stringify({ cited: given, citedMtime: statSync(resolve(ROOT, given)).mtime.toISOString() }, null, 1));
  } else {
    log('engine-test（約 6 分鐘）');
    const r = spawnSync('node', [join(ROOT, 'tools/engine-test.mjs')], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
    writeFileSync(join(OUT, 'ops', 'engine_test.log'), `# node tools/engine-test.mjs（${new Date().toISOString()}，結束碼 ${r.status}；建置 app.js ${BUILD.appJsSha1}、${BUILD.cuesShowFile} ${BUILD.cuesShowSha1}）\n${r.stdout}\n${r.stderr}`);
    recordBuild('engine_test', { exitCode: r.status });
  }
}
if (!has('--skip-seams') && !PERF_ONLY) await seams();
if (!has('--skip-live') || PERF_ONLY) { await liveRun(); await stallFrames(); }
else if (!existsSync(join(OUT, 'live', 'stall_frames.json'))) await stallFrames();
writeBuildCheck();
runPy(OUT, PACKS);
rmSync(join(OUT, 'seams', '_work'), { recursive: true, force: true });
log(`完成 → ${join(OUT, 'INDEX.md')}`);
