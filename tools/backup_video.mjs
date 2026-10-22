// 備援影片（v1.2 第 17.2 節 C 級、第 21 節方案 D；v1.3 第 8 節「分幕影片（逐格離線輸出）」）。
// 以同一套引擎（?capture=1 虛擬時鐘、固定步長 30 格／秒）逐格離線輸出，每段一檔 backup_a0.mp4 … backup_a8.mp4；不即時錄螢幕。
//
//   畫面：逐格規則與 tools/act_review_pack.mjs 相同（gotoCue(第一個 cue, before) 停在流程上前一個 cue 的停格 → capture.playCue →
//         換景漸暗預捲 seek(負秒) → 逐格 seek(k/30) → 停住格 seek(長度＋0.001)）。差別只有三點：
//         (1) 截圖直接用管線送進 ffmpeg（不落地，省磁碟）；(2) 每個 cue 的第 0 秒對齊 1/30 秒格線（聲音與畫面同一個時間原點，誤差 0）；
//         (3) 停格長度改成備援用（見下）。
//   編碼：H.264 High@L4.1、CRF 16（≤18）、preset slow、yuv420p、BT.709（RGB→YUV 用 BT.709 矩陣並標註）、1920×1080、30 格／秒；
//         章節起點強制關鍵格（拖曳、跳章節準確）；AAC-LC 256 kbps 48 kHz 立體聲；+faststart。
//   聲音：與驗收包同一套離線混音（tools/g4_review_pack.py mix()，act_review_pack.py 也用它）；另照引擎規則
//         （engine.ts scheduleAudio：同一首配樂已經在播就不重新淡入）修正 mix() 對「連續兩段同一首配樂」的重新起播，見 backup_video.py。
//   停格：每個 cue 播完停 2 秒（--hold）；出題（quiz）停 3 秒（--quiz-hold，老師在這裡按暫停）；片頭署名卡 3 秒（--title-hold）；
//         片尾署名卡 12 秒（--end-hold，閉幕曲約 10 秒自然淡出）；自動接續的 cue（autoAdvance，例如 a8_c002 布幕合攏）不停，照現場直接接下一段。
//   章節：每個 cue 一章（ffmpeg metadata chapters），起點＝老師按下一步的那一格（含換景漸暗預捲），標題＝「cue 標題（cue 編號）」。
//   每段影片從靜音開始：上一段的配樂不延續（現場會從上一段的配樂交叉淡入，影片是從無聲淡入）。
//
// 用法（專案根目錄；先 cd app && npm run build）：
//   caffeinate -i node tools/backup_video.mjs --acts a8 --out review/G6/_test/backup     → 試跑最短一段
//   caffeinate -i node tools/backup_video.mjs --acts all                                → 全劇九段（預設輸出 交付/backup_video/）
//   node tools/backup_video.mjs --acts all --plan                                       → 只列每段格數與預估時間，不擷取
//   node tools/backup_video.mjs --readme-only --out 交付/backup_video                   → 只依現有檢查報告重寫 README.txt
// 選項：
//   --out <資料夾>        影片與 README.txt 的位置（預設 交付/backup_video）；檢查報告在 <out>/_check/（--check 改位置）
//   --img png|jpeg        截圖格式：png（預設，無損，約 0.1 秒／格）或 jpeg（品質 98，約 0.05 秒／格）
//   --crf 16 --preset slow --abr 256k
//   --hold 2 --quiz-hold 3 --title-hold 3 --end-hold 12
//   --keep-work           保留 <check>/_work_<段>/（時間軸、混音 WAV、無聲影片、取樣格）
//   --no-verify           不做輸出後的檢查（不建議）
// 產出：<out>/backup_<段>.mp4、<out>/README.txt（Windows 記事本可讀，UTF-8 BOM）；<check>/backup_<段>.json（ffprobe、章節、
//       聲畫對齊（每句配音與成品音軌的互相關時間差）、取樣格與成品逐格比對 PSNR、響度）；<check>/plan.json（--plan）。
import { createRequire } from 'node:module';
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const esbuild = require('esbuild');
const PYTHON = process.env.PYTHON ?? '/opt/anaconda3/bin/python3';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const OUT = resolve(ROOT, opt('--out', '交付/backup_video'));
const CHECK = resolve(ROOT, opt('--check', join(OUT, '_check')));
const IMG = opt('--img', 'png') === 'jpeg' ? 'jpeg' : 'png';
const CRF = Math.min(18, Number(opt('--crf', '16')));
const PRESET = opt('--preset', 'slow');
const ABR = opt('--abr', '256k');
const HOLD = Number(opt('--hold', '2'));
const QUIZ_HOLD = Number(opt('--quiz-hold', '3'));
const TITLE_HOLD = Number(opt('--title-hold', '3'));
const END_HOLD = Number(opt('--end-hold', '12'));
const FPS = 30;
const W = 1920, H = 1080;
const SAMPLES_PER_SEG = 16;

const t0 = Date.now();
const log = (s) => console.log(`[backup ${((Date.now() - t0) / 1000).toFixed(0).padStart(5)}s] ${s}`);
const run = (cmd, argv) => {
  const r = spawnSync(cmd, argv, { stdio: 'inherit', cwd: ROOT });
  if (r.status !== 0) { console.error(`[backup] 失敗：${cmd} ${argv.join(' ')}`); process.exit(r.status ?? 1); }
};
mkdirSync(CHECK, { recursive: true });

if (has('--readme-only')) {
  run(PYTHON, [join(ROOT, 'tools/backup_video.py'), 'readme', OUT, CHECK]);
  process.exit(0);
}

const dist = join(ROOT, 'app/dist/index.html');
if (!existsSync(dist)) { console.error('[backup] 找不到 app/dist/index.html，請先在 app/ 執行 npm run build'); process.exit(1); }
const readPack = (file, id) => JSON.parse(readFileSync(join(ROOT, 'app/dist/data', file), 'utf8').replace(new RegExp(`^[\\s\\S]*?window\\.__pack\\(${JSON.stringify(id).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')},`), '').replace(/\);\s*$/, ''));
const manifest = readPack('manifest.js', 'manifest');
if (!manifest.cueSets.show) { console.error('[backup] 資料包裡沒有全劇 cue 集（app/cues/show/）'); process.exit(1); }
const show = readPack(manifest.cueSets.show, 'cues:show');

// 時間軸：與引擎、act_review_pack.mjs 同一個 buildTimelines（app/src/cues/timeline.ts）
const bundle = async (rel) => {
  const r = await esbuild.build({ entryPoints: [join(ROOT, rel)], bundle: true, format: 'esm', platform: 'node', write: false, logLevel: 'silent' });
  return import(`data:text/javascript;base64,${Buffer.from(r.outputFiles[0].text).toString('base64')}`);
};
const { buildTimelines } = await bundle('app/src/cues/timeline.ts');
const engineSrc = readFileSync(join(ROOT, 'app/src/engine/engine.ts'), 'utf8');
const MUSIC_LEVEL = Function(`return (${/const MUSIC_LEVEL[^=]*=\s*(\{[^}]*\})/.exec(engineSrc)[1]})`)();
const PREROLL = Number(/export const PREROLL_SEC = ([\d.]+)/.exec(engineSrc)[1]);
const timelines = buildTimelines(show, (id) => manifest.audio[id]?.duration ?? undefined);
const byId = new Map(timelines.map((t) => [t.cue.id, t]));
const firstCueId = timelines[0].cue.id;
const lastCueId = timelines[timelines.length - 1].cue.id;

const actArg = opt('--acts', '');
const ACTS = actArg === 'all' ? show.segments.map((s) => s.id) : actArg.split(',').map((s) => s.trim()).filter(Boolean);
if (!ACTS.length) { console.error('用法：node tools/backup_video.mjs --acts a8[,a0…]|all [--out 資料夾]'); process.exit(1); }
for (const a of ACTS) if (!show.segments.some((s) => s.id === a)) { console.error(`[backup] 沒有段落 ${a}（可用：${show.segments.map((s) => s.id).join('、')}）`); process.exit(1); }

/** 這個 cue 播完停幾秒（備援影片規則） */
function holdFor(tl) {
  const c = tl.cue;
  if (c.id === lastCueId) return END_HOLD;
  if (c.autoAdvance) return 0;
  if (c.id === firstCueId) return TITLE_HOLD;
  if (c.kind === 'quiz') return QUIZ_HOLD;
  return HOLD;
}

/**
 * 逐格計畫：每個 cue 的格線（全部是整數格）。fPre0＝老師按下一步的那一格（章節起點），f0＝cue 第 0 秒，fEnd＝播完，fHold＝停格結束。
 * cue 第 0 秒對齊格線：G＝f0／30，配音、音效、配樂都從 G 起算，所以第 k 格畫面＝cue 內 k／30 秒＝混音裡的同一時間。
 */
function framePlan(order, prerolls) {
  let f = 0;
  return order.map((tl) => {
    const id = tl.cue.id;
    const pre = prerolls[id] ?? 0;
    const fPre0 = f;
    const f0 = fPre0 + Math.round(pre * FPS);
    const G = f0 / FPS;
    const hold = holdFor(tl);
    const fEnd = Math.round((G + tl.duration) * FPS);
    const fHold = Math.round((G + tl.duration + hold) * FPS);
    f = fHold;
    return { id, kind: tl.cue.kind, title: tl.cue.title, preroll: pre, start: G, chapterStart: fPre0 / FPS, duration: tl.duration, hold, autoAdvance: !!tl.cue.autoAdvance,
      set: tl.set, enterFade: tl.enterFade, fPre0, f0, fEnd, fHold };
  });
}

function segOrder(act) {
  const seg = show.segments.find((s) => s.id === act);
  return { seg, order: seg.cueIds.map((id) => byId.get(id)).filter(Boolean) };
}

// ------------------------------------------------------------------ --plan：只列格數與預估時間
if (has('--plan')) {
  let rate = null;
  for (const a of show.segments.map((s) => s.id)) {
    const p = join(CHECK, `backup_${a}.json`);
    if (existsSync(p)) { const r = JSON.parse(readFileSync(p, 'utf8')); if (r.timing?.capture_ms_per_frame) rate = { ms: r.timing.capture_ms_per_frame, mux: r.timing.post_sec_per_video_sec ?? r.timing.mux_sec_per_video_sec, load: r.timing.load_sec, img: r.timing.img, from: a }; }
  }
  const msPerFrame = rate?.img === IMG ? rate.ms : (IMG === 'png' ? 110 : 65);
  const muxPerSec = rate?.mux ?? 0.4;
  const rows = ACTS.map((a) => {
    const { seg, order } = segOrder(a);
    const pl = framePlan(order, Object.fromEntries(order.map((t) => [t.cue.id, t.enterFade > 0 ? PREROLL : 0])));
    const frames = pl[pl.length - 1].fHold;
    // 每段：開頁載入（約 60 秒）＋第一遍讀預捲＋逐格擷取＋混音封裝檢查
    const est = (rate?.load ?? 60) + order.length * 0.3 + frames * msPerFrame / 1000 + frames / FPS * muxPerSec;
    return { act: a, title: seg.title, cues: order.length, frames, video_sec: Math.round(frames / FPS * 10) / 10, est_min: Math.round(est / 6) / 10 };
  });
  const tot = rows.reduce((n, r) => n + r.est_min, 0);
  const plan = { img: IMG, ms_per_frame: msPerFrame, mux_sec_per_video_sec: muxPerSec, rate_source: rate ? `_check/backup_${rate.from}.json` : '預設值（還沒有試跑紀錄）', rows,
    total_frames: rows.reduce((n, r) => n + r.frames, 0), total_video_min: Math.round(rows.reduce((n, r) => n + r.video_sec, 0) / 6) / 10, total_est_min: Math.round(tot * 10) / 10,
    disk_note: '截圖用管線送進 ffmpeg，不落地；每段工作檔（混音 WAV＋無聲影片）約 0.2–1 GB，做完即刪；成品約每分鐘 100–200 MB。' };
  writeFileSync(join(CHECK, 'plan.json'), JSON.stringify(plan, null, 1));
  console.table(rows);
  console.log(`[backup] 合計 ${plan.total_frames} 格、影片約 ${plan.total_video_min} 分；預估 ${plan.total_est_min} 分鐘（${IMG}，${msPerFrame} ms／格，來源：${plan.rate_source}）→ ${join(CHECK, 'plan.json')}`);
  process.exit(0);
}

// ------------------------------------------------------------------ 擷取
async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const errors = [];
  const external = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('request', (r) => { if (!/^(file|data|blob):/.test(r.url())) external.push(r.url()); });
  await page.goto(`${pathToFileURL(dist).href}?capture=1&cues=show&q=A&step=${FPS}`);
  await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 180000 });
  return { page, errors, external };
}

function startEncoder(file, keyTimes) {
  const vf = 'scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p';
  const argv = ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', IMG === 'png' ? 'png' : 'mjpeg', '-i', '-',
    '-vf', vf, '-c:v', 'libx264', '-preset', PRESET, '-crf', String(CRF), '-profile:v', 'high', '-level:v', '4.1', '-maxrate', '50M', '-bufsize', '75M',
    '-g', String(FPS * 2), '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709', '-force_key_frames', keyTimes.map((t) => t.toFixed(4)).join(','),
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-r', String(FPS), '-an', file];
  const ff = spawn('ffmpeg', argv, { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', (code) => (code === 0 ? res() : rej(new Error(`ffmpeg 結束碼 ${code}`)))));
  let n = 0;
  const write = (buf) => new Promise((res, rej) => {
    n++;
    ff.stdin.write(buf, (e) => (e ? rej(e) : undefined));
    if (ff.stdin.writableNeedDrain) ff.stdin.once('drain', res); else res();
  });
  return { write, end: async () => { ff.stdin.end(); await done; return n; } };
}

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
for (const act of ACTS) {
  const { seg, order } = segOrder(act);
  const WORK = join(CHECK, `_work_${act}`);
  rmSync(WORK, { recursive: true, force: true });
  mkdirSync(join(WORK, 'samples'), { recursive: true });
  mkdirSync(OUT, { recursive: true });
  log(`${act}「${seg.title}」：${order.length} 個 cue`);
  const tLoad0 = Date.now();
  const { page, errors, external } = await openPage(browser);
  const loadSec = (Date.now() - tLoad0) / 1000;
  const cdp = await page.context().newCDPSession(page);
  const shot = async () => {
    const r = await cdp.send('Page.captureScreenshot', IMG === 'png' ? { format: 'png', optimizeForSpeed: true } : { format: 'jpeg', quality: 98, optimizeForSpeed: true });
    return Buffer.from(r.data, 'base64');
  };
  const ev = (fn, a) => page.evaluate(fn, a);
  const seek = (t) => ev((x) => window.__engine.capture.seek(x), t);

  // 第一遍：讀引擎回報的換景漸暗預捲（與 act_review_pack.mjs 相同來源），排出逐格計畫與章節關鍵格
  const prerolls = {};
  const engineDur = {};
  await ev((id) => window.__engine.gotoCue(id, { mode: 'before' }), order[0].cue.id);
  for (const tl of order) {
    await ev((x) => window.__engine.capture.playCue(x), tl.cue.id);
    const st = await ev(() => window.__engine.getState());
    prerolls[tl.cue.id] = st.prerollSec || 0;
    engineDur[tl.cue.id] = st.cueDuration;
    await seek(st.cueDuration + 0.001);
  }
  const plan = framePlan(order, prerolls);
  const durMismatch = order.filter((tl) => Math.abs(engineDur[tl.cue.id] - tl.duration) > 0.002).map((tl) => `${tl.cue.id} 引擎 ${engineDur[tl.cue.id]} ≠ 時間軸 ${tl.duration}`);
  if (durMismatch.length) { console.error(`[backup] 引擎與 buildTimelines 的 cue 長度不同（建置與原始檔不一致？請重新 npm run build）：${durMismatch.join('；')}`); process.exit(1); }
  const totalFrames = plan[plan.length - 1].fHold;
  // 取樣格（輸出後與成品逐格比對，確認沒有掉格、重複格或錯位）：每個 cue 中段一格、預捲第 2 格（第 1 格和上一格停格相同），最多 16 格
  const cand = plan.flatMap((p) => [p.f0 + Math.floor((p.fEnd - p.f0) / 2), ...(p.f0 > p.fPre0 ? [p.fPre0 + 1] : [])]).filter((f) => f < totalFrames);
  const step = Math.max(1, Math.ceil(cand.length / SAMPLES_PER_SEG));
  const sampleSet = new Set(cand.filter((_, i) => i % step === 0));

  // 第二遍：逐格擷取 → ffmpeg
  const silent = join(WORK, 'video_silent.mp4');
  const enc = startEncoder(silent, plan.map((p) => p.chapterStart).filter((t) => t > 0));
  const tCap0 = Date.now();
  let f = 0;
  let shots = 0;
  const emit = async (buf, n = 1) => {
    for (let i = 0; i < n; i++) {
      if (sampleSet.has(f)) writeFileSync(join(WORK, 'samples', `${String(f).padStart(6, '0')}.${IMG === 'png' ? 'png' : 'jpg'}`), buf);
      await enc.write(buf);
      f++;
    }
  };
  await ev((id) => window.__engine.gotoCue(id, { mode: 'before' }), order[0].cue.id);
  for (const p of plan) {
    await ev((x) => window.__engine.capture.playCue(x), p.id);
    const st = await ev(() => window.__engine.getState());
    if (Math.abs((st.prerollSec || 0) - p.preroll) > 1e-6) { console.error(`[backup] ${p.id} 預捲 ${st.prerollSec} 與第一遍 ${p.preroll} 不同`); process.exit(1); }
    if (f !== p.fPre0) { console.error(`[backup] 格數錯位：${p.id} 應從第 ${p.fPre0} 格開始，實際 ${f}`); process.exit(1); }
    for (let k = 0; k < p.f0 - p.fPre0; k++) { await seek(-p.preroll + k / FPS); await emit(await shot()); shots++; }
    for (let k = 0; k < p.fEnd - p.f0; k++) {
      if (k / FPS > p.duration) break;
      await seek(k / FPS); await emit(await shot()); shots++;
    }
    await seek(p.duration + 0.001);
    const after = await shot(); shots++;
    await emit(after, p.fHold - f);
    log(`  ${p.id}：預捲 ${p.f0 - p.fPre0} 格＋${p.fEnd - p.f0} 格＋停格 ${(p.hold).toFixed(1)} 秒（累計 ${f}／${totalFrames} 格）`);
  }
  const written = await enc.end();
  const capSec = (Date.now() - tCap0) / 1000;
  await page.close();
  log(`${act} 擷取完成：${written} 格（實拍 ${shots} 張）、${capSec.toFixed(0)} 秒（${(capSec * 1000 / shots).toFixed(0)} ms／張）`);

  // 混音與封裝用的時間軸（欄位同 act_review_pack.mjs 的 timeline.json，mix() 直接吃）
  const prevIdx = timelines.findIndex((t) => t.cue.id === order[0].cue.id) - 1;
  const tlOut = {
    note: 'tools/backup_video.mjs：buildTimelines（app/src/cues/timeline.ts）＋引擎回報的預捲；schedule.start＝cue 第 0 秒（對齊 1/30 秒格線）；chapterStart＝老師按下一步的那一格；hold＝備援影片停格秒數。',
    act, title: seg.title, segmentFile: `app/cues/show/${seg.file}`, musicLevelDefaults: MUSIC_LEVEL, prerollSec: PREROLL, fps: FPS,
    holds: { hold: HOLD, quiz: QUIZ_HOLD, title: TITLE_HOLD, end: END_HOLD, autoAdvance: 0 },
    previousCue: prevIdx >= 0 ? timelines[prevIdx].cue.id : null,
    cues: order.map((t) => ({
      id: t.cue.id, kind: t.cue.kind, title: t.cue.title, duration: t.duration, autoAdvance: !!t.cue.autoAdvance, set: t.set, enterFade: t.enterFade,
      audioId: t.cue.audioId ?? null, musicLoop: t.cue.musicLoop ?? true, musicLevel: t.cue.musicLevel ?? MUSIC_LEVEL[t.cue.kind] ?? 0.6,
      ...(t.cue.musicDuck !== undefined ? { musicDuck: t.cue.musicDuck } : {}),   // 台詞時的配樂避讓增益（g4.mix 的 duck_plan 讀它；沒寫＝DUCK_LEVEL）
      teacherNote: t.cue.teacherNote ?? '', quiz: t.quiz ? { qid: t.quiz.qid, number: t.quiz.number, answer: t.quiz.answer } : null, lamp: t.cue.lamp ?? null,
      lines: t.lines.map((l) => ({ id: l.line.id, speaker: l.line.speaker, text: l.line.text, audioId: l.audioId, start: l.start, end: l.end, duration: l.duration, placeholder: l.placeholder })),
      sfx: t.sfx.map((s) => ({ ...s })),
      music: t.music.map((m) => ({ ...m })),
    })),
    schedule: plan,
    totalFrames,
    totalPlaybackSec: totalFrames / FPS,
    audio: Object.fromEntries(Object.entries(manifest.audio).map(([id, a]) => [id, { source: a.source, duration: a.duration, bus: a.bus }])),
    capture: { img: IMG, load_sec: Math.round(loadSec * 10) / 10, shots, written, capture_sec: Math.round(capSec * 10) / 10, capture_ms_per_frame: Math.round(capSec * 1000 / Math.max(1, shots)), page_errors: errors, external_requests: external,
      encoder: { crf: CRF, preset: PRESET, profile: 'high', level: '4.1', pix_fmt: 'yuv420p', colorspace: 'bt709', gop: FPS * 2, abr: ABR } },
    samples: [...sampleSet].sort((a, b) => a - b),
  };
  writeFileSync(join(WORK, 'timeline.json'), JSON.stringify(tlOut, null, 1));

  // 混音、章節、封裝、檢查（Python）
  const mp4 = join(OUT, `backup_${act}.mp4`);
  const tMux0 = Date.now();
  run(PYTHON, [join(ROOT, 'tools/backup_video.py'), 'mux', WORK, mp4, join(CHECK, `backup_${act}.json`), ...(has('--no-verify') ? ['--no-verify'] : [])]);
  log(`${act} 封裝＋檢查 ${((Date.now() - tMux0) / 1000).toFixed(0)} 秒 → ${mp4}`);
  if (!has('--keep-work')) rmSync(WORK, { recursive: true, force: true });
}
await browser.close();
run(PYTHON, [join(ROOT, 'tools/backup_video.py'), 'readme', OUT, CHECK]);
log(`完成：${ACTS.map((a) => `backup_${a}.mp4`).join('、')}＋README.txt → ${OUT}`);
