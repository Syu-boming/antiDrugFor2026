// G4 代表鏡頭驗收包產生器（v1.3 第 4 節：驗收包由 tools/ 腳本產生，製作代理不挑畫面、不附自評）。
//
// 用法（專案根目錄）：
//   cd app && npm run build && cd ..
//   caffeinate -i node tools/g4_review_pack.mjs                 → review/G4/pack/
// 選項：
//   --out <資料夾>     輸出位置（預設 review/G4/pack）
//   --skip-capture     沿用 <out>/capture（不重跑 tools/capture.mjs）
//   --skip-frames      沿用 <out>/_work 的播放逐格（不重新截圖）
//   --skip-perf        不跑即時播放效能量測（沿用 <out>/perf.json）
//   --skip-asr         不跑 faster-whisper 逐字稿（沿用 <out>/transcripts.json）
//   --keep-work        保留 <out>/_work（播放逐格、混音分軌、逐句切段）
//
// 產出（全部固定規則取樣，見 INDEX.md）：
//   capture/          tools/capture.mjs：每個 cue 前／中／後關鍵影格、每秒 2 格接觸表、30 格／秒光敏分析、操偶線量測
//   keyframes_4x3/    同一套關鍵影格在 1440×1080、1024×768 視窗重新渲染
//   proj/             關鍵影格的投影模擬 v2（tools/projsim.py 的函式）與接觸表
//   strip_a2_c002/    a2_c002 從「strings.drop」開始到停格，每秒 8 格的逐格條帶（標出揮手與扯膝的節拍時間點）；
//                     換姿勢（紙片翻面）前後每秒 30 格的放大條帶
//   audio/            依 cue 時間混成的最終混音與分軌響度、逐句響度
//   g4_playback.mp4   固定步長 30 格／秒逐格輸出＋混音（1920×1080）
//   perf.json         開發機即時播放的影格時間（畫質 A、B 各 3 次，AudioContext 時鐘；列出每格 > 50 ms 的時間點）
//   timeline.json     解析後的 cue 時間軸、播放排程（含教師按鍵間隔假設）
//   transcripts.*     配音逐句 faster-whisper 逐字稿與劇本差異
//   INDEX.md          檔案與量測數字
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { cpus, release, totalmem } from 'node:os';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const esbuild = require('esbuild');
const PYTHON = process.env.PYTHON ?? '/opt/anaconda3/bin/python3';
const VENV_PY = join(ROOT, 'tools/.venv/bin/python');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const OUT = resolve(ROOT, opt('--out', 'review/G4/pack'));
const WORK = join(OUT, '_work');
const CUES = 'g4';
const FPS = 30;           // 播放錄製與光敏分析
const STRIP_FPS = 8;      // a2_c002 逐格條帶
const W = 1920, H = 1080;
const SIZES_4X3 = [[1440, 1080], [1024, 768]];
/** 播放錄製的教師按鍵間隔假設（秒）：該 cue 播完後停住多久才按下一步。a8_c002 自動接 a8_c003。 */
// a2_c002、a2_c004 停 4 秒：量教師停格時配樂 3 秒內是否降到 ≤ −35 LUFS（G3 修正第 11 項）
const HOLDS = { a0_c000: 3.0, a0_c001: 2.0, a2_c002: 4.0, a2_c004: 4.0, a8_c002: 0, a8_c003: 6.5 };
const PERF_HOLD = 1.0;    // 效能量測時每個停住點等 1 秒再按下一步
const PERF_RUNS = 3;      // 每種畫質跑幾次

const dist = join(ROOT, 'app/dist/index.html');
if (!existsSync(dist)) { console.error('[g4pack] 找不到 app/dist/index.html，請先在 app/ 執行 npm run build'); process.exit(1); }
mkdirSync(OUT, { recursive: true });
mkdirSync(WORK, { recursive: true });
const t0 = Date.now();
const log = (s) => console.log(`[g4pack ${((Date.now() - t0) / 1000).toFixed(0).padStart(4)}s] ${s}`);
const r3 = (x) => Math.round(x * 1000) / 1000;
const run = (cmd, argv, o = {}) => {
  const r = spawnSync(cmd, argv, { stdio: 'inherit', cwd: ROOT, ...o });
  if (r.status !== 0) { console.error(`[g4pack] 失敗：${cmd} ${argv.join(' ')}`); process.exit(r.status ?? 1); }
};

// ------------------------------------------------------------------ 1. 擷取（關鍵影格、接觸表、光敏、量測）
// 額外量測時間：開幕兒童立起過程（每 0.2 秒，量站位背景亮度，G4 修正第 21 項）、
// 驗收意見指定的紙環檢查時間（a2_c002 11.41／22.83 秒、a2_c004 9.75 秒，G4 修正第 23 項）
const probeTimes = (() => {
  const cf = JSON.parse(readFileSync(join(ROOT, `app/cues/${CUES}.json`), 'utf8'));
  const c1 = cf.cues.find((c) => c.id === 'a0_c001');
  const pops = (c1?.animation ?? []).filter((a) => a.name === 'puppet.popup' && a.target !== 'ale');
  const t0 = Math.min(...pops.map((a) => a.start)), t1 = Math.max(...pops.map((a) => a.start + (a.duration ?? 1.1)));
  const open = [];
  for (let t = Math.floor(t0 * 5) / 5; t <= t1 + 0.6; t += 0.2) open.push(r3(t));
  return `a0_c001:${open.join(',')};a2_c002:11.41,22.83;a2_c004:9.75`;
})();
if (!has('--skip-capture')) {
  log('tools/capture.mjs（30 格／秒光敏分析＋操偶線量測）');
  run('node', ['tools/capture.mjs', '--cues', CUES, '--probe', '--probe-times', probeTimes, '--analysis-fps', String(FPS), '--fps', '2', '--out', join(OUT, 'capture')]);
}

// ------------------------------------------------------------------ 2. 時間軸（與引擎同一個 buildTimelines）
log('解析 cue 時間軸');
const manifest = JSON.parse(readFileSync(join(ROOT, 'app/dist/data/manifest.js'), 'utf8').replace(/^[\s\S]*?window\.__pack\("manifest",/, '').replace(/\);\s*$/, ''));
const tlBundle = await esbuild.build({ entryPoints: [join(ROOT, 'app/src/cues/timeline.ts')], bundle: true, format: 'esm', platform: 'node', write: false, logLevel: 'silent' });
const { buildTimelines } = await import(`data:text/javascript;base64,${Buffer.from(tlBundle.outputFiles[0].text).toString('base64')}`);
const cueFile = JSON.parse(readFileSync(join(ROOT, `app/cues/${CUES}.json`), 'utf8'));
const engineSrc = readFileSync(join(ROOT, 'app/src/engine/engine.ts'), 'utf8');
const MUSIC_LEVEL = Function(`return (${/const MUSIC_LEVEL[^=]*=\s*(\{[^}]*\})/.exec(engineSrc)[1]})`)();
const timelines = buildTimelines(cueFile, (id) => manifest.audio[id]?.duration);
const beatBundle = await esbuild.build({ entryPoints: [join(ROOT, 'app/src/stage/beats.ts')], bundle: true, format: 'esm', platform: 'node', write: false, logLevel: 'silent' });
const { beatMarks, WAVE_TRY, KNEE_TUG } = await import(`data:text/javascript;base64,${Buffer.from(beatBundle.outputFiles[0].text).toString('base64')}`);
const byId = new Map(timelines.map((t) => [t.cue.id, t]));
// 播放順序：從第一個 cue 沿 next 走到底
const order = [];
for (let c = timelines[0]; c; c = c.nextIndex >= 0 ? timelines[c.nextIndex] : null) { order.push(c); if (order.length > 100) break; }
let gt = 0;
const schedule = order.map((t) => {
  const hold = HOLDS[t.cue.id] ?? 2.0;
  const item = { id: t.cue.id, kind: t.cue.kind, start: r3(gt), duration: r3(t.duration), hold, autoAdvance: !!t.cue.autoAdvance };
  gt += t.duration + hold;
  return item;
});
const audioSrc = Object.fromEntries(Object.entries(manifest.audio).map(([id, a]) => [id, { source: a.source, duration: a.duration, bus: a.bus }]));
const tlOut = {
  note: '由 app/src/cues/timeline.ts 的 buildTimelines 解析（與引擎相同），音檔長度取自 app/dist/data/manifest.js。schedule＝播放錄製用的排程；hold＝教師按鍵間隔假設（秒）。',
  cueFile: `app/cues/${CUES}.json`,
  musicLevelDefaults: MUSIC_LEVEL,
  cues: order.map((t) => ({
    id: t.cue.id, kind: t.cue.kind, title: t.cue.title, duration: r3(t.duration), autoAdvance: !!t.cue.autoAdvance,
    audioId: t.cue.audioId ?? null, musicLoop: t.cue.musicLoop ?? true,
    musicLevel: t.cue.musicLevel ?? MUSIC_LEVEL[t.cue.kind] ?? 0.6,
    lines: t.lines.map((l) => ({ id: l.line.id, speaker: l.line.speaker, text: l.line.text, audioId: l.audioId, start: r3(l.start), end: r3(l.end), duration: r3(l.duration), placeholder: l.placeholder, pages: l.pages.map((p) => ({ start: r3(p.start), end: r3(p.end), rows: p.rows })) })),
    sfx: t.sfx.map((s) => ({ ...s, at: r3(s.at) })),
    music: t.music.map((m) => ({ ...m, at: r3(m.at) })),
    anims: t.anims.map((a) => ({ name: a.name, target: a.target ?? null, start: r3(a.start), end: r3(a.end), params: a.params })),
    beats: t.anims.flatMap((a) => beatMarks(a.name, a.start).map((m) => ({ anim: a.name, target: a.target ?? null, label: m.label, t: r3(m.t) }))),
  })),
  beatTables: { waveTry: WAVE_TRY, kneeTug: KNEE_TUG, source: 'app/src/stage/beats.ts' },
  schedule,
  totalPlaybackSec: r3(gt),
  audio: audioSrc,
  fps: FPS,
};
writeFileSync(join(OUT, 'timeline.json'), JSON.stringify(tlOut, null, 1));

// ------------------------------------------------------------------ 3. 逐格：播放錄製（30 格／秒）、a2_c002 條帶（8 格／秒）、4:3 關鍵影格
async function openCapturePage(browser, w, h, step) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`${pathToFileURL(dist).href}?capture=1&cues=${CUES}&q=A&step=${step}`);
  await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 90000 });
  return { page, errors };
}

const framesMeta = { fps: FPS, cues: {}, strip: null, sizes4x3: {}, errors: [] };
if (!has('--skip-frames')) {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
  {
    const { page, errors } = await openCapturePage(browser, W, H, FPS);
    const engineCues = await page.evaluate(() => window.__engine.getCues());
    framesMeta.engineDurations = Object.fromEntries(engineCues.map((c) => [c.id, r3(c.duration)]));
    rmSync(join(WORK, 'video'), { recursive: true, force: true });
    const dense = [];   // 操偶線量測：播放錄製每 3 格（10 次／秒）取一次 probe()
    const facesPlay = [];   // 每一格的臉部換片狀態＋兒童外框（G4 修正第 2 輪第 9、10 項：眨眼與翻面、兩眼同閉）
    for (const s of schedule) {
      const dir = join(WORK, 'video', s.id);
      mkdirSync(dir, { recursive: true });
      await page.evaluate((id) => window.__engine.capture.playCue(id), s.id);
      const n = Math.round(s.duration * FPS);
      for (let k = 0; k < n; k++) {
        await page.evaluate((t) => window.__engine.capture.seek(t), k / FPS);
        await page.screenshot({ path: join(dir, `${String(k).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92 });
        const pr = await page.evaluate(() => window.__engine.debug.probe());
        const fc = await page.evaluate(() => window.__engine.debug.faces());
        facesPlay.push({ cueId: s.id, k, t: r3(k / FPS), playT: r3(s.start + k / FPS), faces: fc,
          boxes: Object.fromEntries(pr.actors.filter((a) => a.visible && a.id !== 'ale').map((a) => [a.id, a.box.map((v) => Math.round(v))])),
          eyes: Object.fromEntries(pr.actors.filter((a) => a.visible && a.eyesBox).map((a) => [a.id, a.eyesBox])) });
        if (k % 3 === 0 && pr.strings.some((x) => x.visible)) dense.push({ cueId: s.id, t: r3(k / FPS), ...pr });
      }
      await page.evaluate((t) => window.__engine.capture.seek(t), s.duration + 0.001);
      await page.screenshot({ path: join(dir, 'after.jpg'), type: 'jpeg', quality: 92 });
      framesMeta.cues[s.id] = { frames: n, after: 'after.jpg' };
      log(`播放逐格 ${s.id}：${n} 格＋停住格`);
    }
    writeFileSync(join(OUT, 'probe_dense.json'), JSON.stringify({ note: '播放錄製逐格時每 3 格（每秒 10 次）取一次 window.__engine.debug.probe()，只留有操偶線顯示的格；座標為 1920×1080 繪圖緩衝像素。', probes: dense }));
    writeFileSync(join(OUT, 'faces_playback.json'), JSON.stringify({ note: '播放錄製每一格（30 格／秒）的臉部換片狀態 window.__engine.debug.faces()（eyes：open／half／closed；一張眼睛換片同時蓋兩眼）、兩個孩子的立牌外框 boxes 與眼睛換片範圍 eyes（1920×1080 像素）；playT＝g4_playback.mp4 的秒數。', fps: FPS, frames: facesPlay }));
    log(`操偶線量測 ${dense.length} 格（每秒 10 次）`);
    // a2_c002：從線開始落下（strings.drop 起點）到停格，每秒 8 格
    const tl = tlOut.cues.find((c) => c.id === 'a2_c002');
    const drop = tl.anims.find((a) => a.name === 'strings.drop');
    const s0 = drop ? drop.start : 0;
    const sdir = join(OUT, 'strip_a2_c002', 'frames');
    rmSync(join(OUT, 'strip_a2_c002'), { recursive: true, force: true });
    mkdirSync(sdir, { recursive: true });
    await page.evaluate(() => window.__engine.capture.playCue('a2_c002'));
    const stripTimes = [];
    for (let k = 0; ; k++) { const t = s0 + k / STRIP_FPS; if (t > tl.duration + 1e-6) break; stripTimes.push(r3(t)); }
    stripTimes.push(r3(tl.duration + 0.001));
    const subRect = () => page.evaluate(() => { const e = document.querySelector('.sub-strip'); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; });
    const stripProbe = [];
    for (const t of stripTimes) {
      await page.evaluate((x) => window.__engine.capture.seek(x), t);
      await page.screenshot({ path: join(sdir, `a2_c002_${t.toFixed(3).padStart(7, '0')}.jpg`), type: 'jpeg', quality: 90 });
      const pr = await page.evaluate(() => window.__engine.debug.probe());
      stripProbe.push({ t, sub: await subRect(), faces: await page.evaluate(() => window.__engine.debug.faces()), actors: pr.actors, strings: pr.strings, landmarks: pr.landmarks });
    }
    writeFileSync(join(OUT, 'strip_a2_c002', 'strip_probe.json'), JSON.stringify({ note: '條帶每一格的 probe()（角色外框、部件外框與不透明範圍 opaque、關節 joints.hip、操偶線中心線 path 與紙環螢幕位置、景片地標 landmarks：桌面上緣 tableTop、凳面上緣 stoolTop）、字幕底板外框（DOM，1920×1080 像素）、臉部換片狀態', frames: stripProbe }));
    framesMeta.strip = { cue: 'a2_c002', from: s0, to: tl.duration, fps: STRIP_FPS, count: stripTimes.length, fromAnim: 'strings.drop.start' };
    // 換姿勢（紙片翻面）前後每秒 30 格（G4 修正第 19、27 項：檢查有沒有只剩細縫的格）；
    // 第 2 輪第 10 項：翻面前 0.2 秒到翻面結束後 0.4 秒，逐格記錄臉部換片狀態（翻面結束後 0.3 秒內必須是 open）
    const fdir = join(OUT, 'strip_a2_c002', 'flip');
    mkdirSync(fdir, { recursive: true });
    const flips = [];
    for (const a of tl.anims.filter((x) => x.name === 'puppet.pose')) {
      const list = [];
      for (let k = -6; k <= Math.round((a.end - a.start) * FPS) + 12; k++) {
        const t = r3(a.start + k / FPS);
        await page.evaluate((x) => window.__engine.capture.seek(x), t);
        const f = `${a.target}_${t.toFixed(3).padStart(7, '0')}.jpg`;
        await page.screenshot({ path: join(fdir, f), type: 'jpeg', quality: 92 });
        const pr = await page.evaluate(() => window.__engine.debug.probe());
        const fc = await page.evaluate(() => window.__engine.debug.faces());
        list.push({ t, file: f, box: pr.actors.find((x) => x.id === a.target)?.box, eyes: fc[a.target]?.eyes ?? null });
      }
      flips.push({ target: a.target, pose: a.params.pose, start: a.start, end: a.end, frames: list });
    }
    writeFileSync(join(fdir, 'flips.json'), JSON.stringify(flips, null, 1));
    log(`換姿勢放大條帶 ${flips.length} 段（每秒 ${FPS} 格）`);
    log(`a2_c002 條帶 ${stripTimes.length} 格（${s0}–${tl.duration} 秒，${STRIP_FPS} 格／秒）`);
    framesMeta.errors.push(...errors);
    await page.close();
  }
  for (const [w, h] of SIZES_4X3) {
    const { page, errors } = await openCapturePage(browser, w, h, FPS);
    const dir = join(OUT, 'keyframes_4x3', `${w}x${h}`);
    rmSync(dir, { recursive: true, force: true });
    mkdirSync(dir, { recursive: true });
    const list = [];
    for (const s of schedule) {
      await page.evaluate((id) => window.__engine.capture.playCue(id), s.id);
      const keys = [['before', 0], ['mid', r3(s.duration / 2)], ['after', s.duration]];
      for (const [key, t] of keys) {
        await page.evaluate((x) => window.__engine.capture.seek(x), key === 'after' ? t + 0.001 : t);
        const f = `${s.id}_${t.toFixed(2).padStart(6, '0')}_${key}.png`;
        await page.screenshot({ path: join(dir, f), type: 'png' });
        list.push({ file: f, cue: s.id, t, key });
      }
    }
    framesMeta.sizes4x3[`${w}x${h}`] = list;
    framesMeta.errors.push(...errors);
    log(`4:3 關鍵影格 ${w}×${h}：${list.length} 張`);
    await page.close();
  }
  await browser.close();
  writeFileSync(join(WORK, 'frames_meta.json'), JSON.stringify(framesMeta, null, 1));
} else if (existsSync(join(WORK, 'frames_meta.json'))) {
  Object.assign(framesMeta, JSON.parse(readFileSync(join(WORK, 'frames_meta.json'), 'utf8')));
}

// ------------------------------------------------------------------ 4. 效能：即時播放（開發機）
async function perfRun(quality) {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1', '--hide-scrollbars'] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  // 每個 rAF 回呼記錄時間戳與回呼耗時（同一格多個回呼合併）；同時記錄當下的 cue 與 cue 內秒數
  await page.addInitScript(() => {
    const rec = { ts: [], cpu: [] };
    window.__perfRec = rec;
    const raf = window.requestAnimationFrame.bind(window);
    rec.cue = []; rec.ct = [];
    window.requestAnimationFrame = (cb) => raf((ts) => {
      const s = performance.now();
      try { cb(ts); } finally {
        rec.ts.push(ts); rec.cpu.push(performance.now() - s);
        let c = null, t = null;
        try { const st = window.__engine?.getState(); if (st && st.mode === 'playing') { c = st.cueId; t = st.cueTime; } } catch { /* 還沒載入 */ }
        rec.cue.push(c); rec.ct.push(t);
      }
    });
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${pathToFileURL(dist).href}?cues=${CUES}&autostart=1&nofs=1&q=${quality}`);
  await page.waitForFunction(() => window.__engine && window.__engine.getState().phase === 'title_idle', null, { timeout: 90000, polling: 100 });
  const st = await page.evaluate(() => window.__engine.getState());
  const marks = [];
  const mark = async (label) => marks.push({ label, ...(await page.evaluate(() => { const s = window.__engine.getState(); return { t: performance.now(), cueId: s.cueId, mode: s.mode }; })) });
  await page.waitForTimeout(PERF_HOLD * 1000);
  for (const s of schedule.slice(1)) {
    const prev = await page.evaluate(() => window.__engine.getState().cueId);
    if (prev === s.id && (await page.evaluate(() => window.__engine.getState().mode)) === 'playing') { /* 自動接續 */ } else if (!schedule.find((x) => x.id === prev)?.autoAdvance) {
      await page.keyboard.press('ArrowRight');
    }
    await page.waitForFunction((id) => window.__engine.getState().cueId === id && window.__engine.getState().mode === 'playing', s.id, { timeout: 20000, polling: 20 });
    await mark(`start:${s.id}`);
    await page.waitForFunction((id) => { const x = window.__engine.getState(); return x.cueId !== id || x.mode === 'waiting'; }, s.id, { timeout: 120000, polling: 20 });
    await mark(`end:${s.id}`);
    if (!s.autoAdvance) await page.waitForTimeout(PERF_HOLD * 1000);
  }
  const rec = await page.evaluate(() => window.__perfRec);
  const warm = await page.evaluate(() => window.__engine.debug.warmMs());
  await browser.close();
  // 合併同一時間戳
  const frames = [];
  for (let i = 0; i < rec.ts.length; i++) {
    const last = frames[frames.length - 1];
    if (last && Math.abs(last.ts - rec.ts[i]) < 0.01) { last.cpu += rec.cpu[i]; last.cue = last.cue ?? rec.cue[i]; last.ct = last.ct ?? rec.ct[i]; } else frames.push({ ts: rec.ts[i], cpu: rec.cpu[i], cue: rec.cue[i], ct: rec.ct[i] });
  }
  const windows = [];
  for (const s of schedule.slice(1)) {
    const a = marks.find((m) => m.label === `start:${s.id}`), b = marks.find((m) => m.label === `end:${s.id}`);
    if (a && b) windows.push({ id: s.id, from: a.t, to: b.t });
  }
  const stats = (xs) => {
    if (!xs.length) return null;
    const v = [...xs].sort((p, q) => p - q);
    const q = (p) => v[Math.min(v.length - 1, Math.floor(p * (v.length - 1) + 0.5))];
    return { n: v.length, median: r3(q(0.5)), p95: r3(q(0.95)), p99: r3(q(0.99)), max: r3(v[v.length - 1]), mean: r3(v.reduce((s, x) => s + x, 0) / v.length) };
  };
  const per = {};
  const allInt = [], allCpu = [];
  const slow = [];   // 每格 > 50 ms：時間戳、cue、cue 內秒數、是否在台詞時段內
  const lineSpans = Object.fromEntries(tlOut.cues.map((c) => [c.id, c.lines.map((l) => [l.start, l.end, l.id])]));
  for (const w of windows) {
    const fr = frames.filter((f) => f.ts >= w.from && f.ts <= w.to);
    const ints = [];
    for (let i = 1; i < fr.length; i++) {
      const dt = fr[i].ts - fr[i - 1].ts;
      ints.push(dt);
      if (dt > 50) {
        const ct = fr[i].ct ?? fr[i - 1].ct;
        const inLine = (lineSpans[w.id] ?? []).find(([a, b]) => ct !== null && ct >= a - 0.1 && ct <= b + 0.1);
        slow.push({ cue: w.id, msSinceCueStart: r3(fr[i].ts - w.from), cueTime: ct === null ? null : r3(ct), frameMs: r3(dt), duringLine: inLine ? inLine[2] : null });
      }
    }
    allInt.push(...ints); allCpu.push(...fr.map((f) => f.cpu));
    per[w.id] = { playMs: r3(w.to - w.from), frameIntervalMs: stats(ints), rafCallbackMs: stats(fr.map((f) => f.cpu)), over33ms: ints.filter((x) => x > 33.4).length, over50ms: ints.filter((x) => x > 50).length };
  }
  return {
    quality, gpu: st.gpu, clock: st.clock, audioState: st.audioState, warmUpMs: r3(warm),
    frameIntervalMs: stats(allInt), rafCallbackMs: stats(allCpu),
    over33ms: allInt.filter((x) => x > 33.4).length, over50ms: allInt.filter((x) => x > 50).length, over100ms: allInt.filter((x) => x > 100).length,
    over100msDuringLines: slow.filter((x) => x.frameMs > 100 && x.duringLine).length,
    slowFrames: slow,
    playingFrames: allInt.length + windows.length, perCue: per, pageErrors: errors,
  };
}
if (!has('--skip-perf')) {
  log('效能量測（即時播放，畫質 A 與 B）');
  const runs = [];
  for (const q of ['A', 'B']) for (let i = 1; i <= PERF_RUNS; i++) { const r = await perfRun(q); r.run = i; runs.push(r); log(`效能 ${q} 第 ${i} 次：時鐘 ${r.clock}、p95 ${r.frameIntervalMs?.p95} ms、最長 ${r.frameIntervalMs?.max} ms、>50 ms ${r.over50ms} 格、>100 ms ${r.over100ms} 格`); }
  const perf = {
    note: 'Mac 開發機（Apple M4）上 headless Chrome（ANGLE Metal）即時播放 g4 的數據，不代表學校 Windows 筆電；學校筆電要用探針與第 3 天彩排實測（school 欄，未驗證）。',
    method: `只統計 cue 播放中（mode=playing）的影格；影格時間＝相鄰 requestAnimationFrame 時間戳的間隔；rAF 回呼耗時＝引擎每格 JS 工作（不含 GPU）。視窗 ${W}×${H}、deviceScaleFactor 1；停住點等 ${PERF_HOLD} 秒按 →（下一步）；畫質 A、B 各 ${PERF_RUNS} 次，每次重開瀏覽器，用 AudioContext 時鐘（clock 欄）。slowFrames＝每格 > 50 ms 的 cue、cue 內秒數、是否在台詞時段內（前後各 0.1 秒）。`,
    machine: { cpu: cpus()[0]?.model, cores: cpus().length, memGB: Math.round(totalmem() / 2 ** 30), os: `darwin ${release()}` },
    acceptance: { rule: '台詞時段內 0 格超過 100 ms（G4 修正第 28 項）', over100msDuringLines: runs.reduce((n, r) => n + r.over100msDuringLines, 0), over100ms: runs.reduce((n, r) => n + r.over100ms, 0), allClocksAudio: runs.every((r) => r.clock === 'audio') },
    school: { status: '未驗證', todo: '請使用者在學校 Windows 筆電用探針跑 g4：p95 影格時間、> 100 ms 次數、30＋40 分鐘耐熱測試，結果填在這裡（G4 修正第 31、35 項）。', p95Ms: null, over100ms: null, thermal30plus40min: null },
    runs,
  };
  writeFileSync(join(OUT, 'perf.json'), JSON.stringify(perf, null, 1));
  const a = perf.runs[0];
  log(`效能 A：影格時間中位 ${a.frameIntervalMs?.median} ms、p95 ${a.frameIntervalMs?.p95} ms、最長 ${a.frameIntervalMs?.max} ms`);
}

// ------------------------------------------------------------------ 5. Python：投影模擬、條帶、混音與響度、播放光敏、影片
log('分析（投影模擬、條帶、混音、響度、光敏、影片）');
run(PYTHON, [join(ROOT, 'tools/g4_review_pack.py'), 'analyze', OUT]);

// ------------------------------------------------------------------ 6. 逐字稿（faster-whisper，兩個模型）
if (!has('--skip-asr')) {
  log('配音逐字稿（faster-whisper small＋large-v3-turbo）');
  run(VENV_PY, [join(ROOT, 'tools/g4_transcripts.py'), OUT]);
}

// ------------------------------------------------------------------ 7. INDEX.md
run(PYTHON, [join(ROOT, 'tools/g4_review_pack.py'), 'index', OUT]);
if (!has('--keep-work')) rmSync(WORK, { recursive: true, force: true });
log(`完成 → ${OUT}`);
