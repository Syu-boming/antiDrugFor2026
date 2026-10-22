// G5 各幕驗收包產生器（v1.3 第 4 節：驗收包由 tools/ 腳本產生，製作代理不挑畫面、不附自評）。
// 沿用 G4 驗收包（tools/g4_review_pack.mjs／.py）的方法與函式；G4 的指令照樣能跑（本工具不改它們）。
//
// 用法（專案根目錄；先 cd app && npm run build）：
//   caffeinate -i node tools/act_review_pack.mjs --acts a1            → review/G5/a1/pack/
//   caffeinate -i node tools/act_review_pack.mjs --acts a0,a1,a2      → 每段各一包
// 選項：
//   --out <資料夾>     輸出根目錄（預設 review/G5；每段在 <out>/<段>/pack）
//   --skip-capture     沿用 <pack>/capture（不重跑 tools/capture.mjs）
//   --skip-frames      沿用 <pack>/_work 的播放逐格（不重新截圖）
//   --skip-asr         不跑 faster-whisper 逐字稿（沿用 <pack>/transcripts.json）
//   --keep-work        保留 <pack>/_work（播放逐格、混音分軌、逐句切段）
//
// 產出（固定規則取樣；INDEX.md 只列數字與檔案）：
//   capture/          tools/capture.mjs：每個 cue 前／中／後關鍵影格、每秒 1 格接觸表、30 格／秒光敏分析、操偶線量測（probe）
//   proj/             關鍵影格的投影模擬 v2（tools/projsim.py）與接觸表
//   compare_g4/       與 G4 代表鏡頭同尺寸並排的對照格（本段每個 cue 的中、後格｜G4 基準格）
//   audio/            依 cue 時間照引擎規則離線混音：整段響度、各 cue 響度、各句對白響度、瞬間響度、教師停格配樂
//   <段>_playback.mp4 固定步長 30 格／秒逐格（含換景漸暗預捲與教師停格假設）＋混音（1920×1080）
//   flash_playback.json、flash_variants.json   播放錄製 30 格／秒光敏分析（16×9、32×18、投影 v2）
//   subtitle_sync.json  字幕頁與語音起點的時間差
//   transcripts.*     配音（v04）逐句 faster-whisper 逐字稿與劇本差異（配音檔、混音中該句）
//   durations.json    各 cue 長度與 時長估算_v03.md 預算對照
//   safety_data.json  操偶線扣點、線到頭部框距離、線是否經過兒童、必要旁白一字不差、字幕排版、隱私
//   timeline.json     解析後的時間軸與播放排程（教師按鍵間隔假設）
//   segment_hash.json 段落指紋（G6 修正）：段落檔 sha1（去掉 checkpoint 欄）、app/dist 合併後這一段的 sha1、建置是否用目前段落檔（tools/seg_fingerprint.mjs）
//   isolated_cuts.json 孤立單格全畫面亮度比（G6 修正：前後格不動、只有一格跳變，比值 > 1.2 判光敏不通過）
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { packTimelineCues, segmentFingerprints } from './seg_fingerprint.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const esbuild = require('esbuild');
const PYTHON = process.env.PYTHON ?? '/opt/anaconda3/bin/python3';
const VENV_PY = join(ROOT, 'tools/.venv/bin/python');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : d; };
const has = (k) => args.includes(k);
const ACTS = (opt('--acts', '') || '').split(',').map((s) => s.trim()).filter(Boolean);
if (!ACTS.length) { console.error('用法：node tools/act_review_pack.mjs --acts a1[,a2…]'); process.exit(1); }
const OUT_ROOT = resolve(ROOT, opt('--out', 'review/G5'));
const FPS = 30;
const W = 1920, H = 1080;
/** 播放錄製的教師按鍵間隔假設（秒）：該 cue 播完後停住多久才按下一步（劇情停 3.5 秒＝量教師停格配樂 3 秒內是否降到 ≤ −35 LUFS） */
const HOLD = { title: 2.0, curtain: 2.0, scene: 3.5, wait: 3.5, quiz: 3.0, reveal: 2.5, lamp: 2.5 };

const dist = join(ROOT, 'app/dist/index.html');
if (!existsSync(dist)) { console.error('[actpack] 找不到 app/dist/index.html，請先在 app/ 執行 npm run build'); process.exit(1); }
const t0 = Date.now();
const log = (s) => console.log(`[actpack ${((Date.now() - t0) / 1000).toFixed(0).padStart(4)}s] ${s}`);
const r3 = (x) => Math.round(x * 1000) / 1000;
const run = (cmd, argv, o = {}) => {
  const r = spawnSync(cmd, argv, { stdio: 'inherit', cwd: ROOT, ...o });
  if (r.status !== 0) { console.error(`[actpack] 失敗：${cmd} ${argv.join(' ')}`); process.exit(r.status ?? 1); }
};
const readPack = (file, id) => JSON.parse(readFileSync(join(ROOT, 'app/dist/data', file), 'utf8').replace(new RegExp(`^[\\s\\S]*?window\\.__pack\\(${JSON.stringify(id).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')},`), '').replace(/\);\s*$/, ''));

const manifest = readPack('manifest.js', 'manifest');
if (!manifest.cueSets.show) { console.error('[actpack] 資料包裡沒有全劇 cue 集（app/cues/show/）'); process.exit(1); }
const show = readPack(manifest.cueSets.show, 'cues:show');
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
// G6 修正：段落指紋（本包量的是 app/dist 合併後的這一版；sha1 都去掉 checkpoint 欄）
const fingerprints = await segmentFingerprints();

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`${pathToFileURL(dist).href}?capture=1&cues=show&q=A&step=${FPS}`);
  await page.waitForFunction(() => window.__engine && window.__engine.ready() && window.__engine.getState().mode === 'waiting', null, { timeout: 180000 });
  return { page, errors };
}

for (const act of ACTS) {
  const seg = show.segments.find((s) => s.id === act);
  if (!seg) { console.error(`[actpack] 沒有段落 ${act}（可用：${show.segments.map((s) => s.id).join('、')}）`); process.exit(1); }
  const OUT = join(OUT_ROOT, act, 'pack');
  const WORK = join(OUT, '_work');
  mkdirSync(WORK, { recursive: true });
  log(`${act}「${seg.title}」：${seg.cueIds.length} 個 cue → ${OUT}`);

  // ---------------------------------------------------------------- 1. 擷取（關鍵影格、接觸表、光敏、操偶線量測）
  if (!has('--skip-capture')) {
    run('node', ['tools/capture.mjs', '--cues', 'show', '--only', seg.cueIds.join(','), '--probe', '--analysis-fps', String(FPS), '--fps', '1', '--out', join(OUT, 'capture')]);
  }

  // ---------------------------------------------------------------- 2. 時間軸與播放排程（與引擎同一個 buildTimelines；預捲在逐格時由引擎回報）
  const order = seg.cueIds.map((id) => byId.get(id)).filter(Boolean);
  const framesMetaPath = join(WORK, 'frames_meta.json');
  let framesMeta = { fps: FPS, cues: {}, preroll: {}, errors: [] };
  if (!has('--skip-frames')) {
    const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--force-device-scale-factor=1', '--hide-scrollbars'] });
    const { page, errors } = await openPage(browser);
    framesMeta.engineDurations = Object.fromEntries((await page.evaluate(() => window.__engine.getCues())).map((c) => [c.id, r3(c.duration)]));
    rmSync(join(WORK, 'video'), { recursive: true, force: true });
    const dense = [];
    // 第一段之前：停在流程上前一個 cue 的停格（換景預捲從這一格漸暗）
    await page.evaluate((id) => window.__engine.gotoCue(id, { mode: 'before' }), order[0].cue.id);
    for (const tl of order) {
      const id = tl.cue.id;
      const dir = join(WORK, 'video', id);
      mkdirSync(dir, { recursive: true });
      await page.evaluate((x) => window.__engine.capture.playCue(x), id);
      const st = await page.evaluate(() => window.__engine.getState());
      const pre = st.prerollSec || 0;
      framesMeta.preroll[id] = pre;
      const np = Math.round(pre * FPS);
      for (let k = 0; k < np; k++) {
        await page.evaluate((t) => window.__engine.capture.seek(t), -pre + k / FPS);
        await page.screenshot({ path: join(dir, `pre_${String(k).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92 });
      }
      const n = Math.round(st.cueDuration * FPS);
      for (let k = 0; k < n; k++) {
        await page.evaluate((t) => window.__engine.capture.seek(t), k / FPS);
        await page.screenshot({ path: join(dir, `${String(k).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92 });
        if (k % 3 === 0) {
          const pr = await page.evaluate(() => window.__engine.debug.probe());
          if (pr.strings.some((x) => x.visible)) dense.push({ cueId: id, t: r3(k / FPS), ...pr });
        }
      }
      await page.evaluate((t) => window.__engine.capture.seek(t), st.cueDuration + 0.001);
      await page.screenshot({ path: join(dir, 'after.jpg'), type: 'jpeg', quality: 92 });
      framesMeta.cues[id] = { frames: n, preFrames: np, duration: st.cueDuration };
      log(`播放逐格 ${id}：預捲 ${np} 格＋${n} 格＋停住格`);
    }
    writeFileSync(join(OUT, 'probe_dense.json'), JSON.stringify({ note: '播放錄製每 3 格（每秒 10 次）取一次 window.__engine.debug.probe()，只留有操偶線顯示的格；座標為 1920×1080 繪圖緩衝像素。', probes: dense }));
    framesMeta.errors.push(...errors);
    framesMeta.sets = await page.evaluate(() => window.__engineShow.sets());
    await page.close();
    await browser.close();
    writeFileSync(framesMetaPath, JSON.stringify(framesMeta, null, 1));
  } else if (existsSync(framesMetaPath)) framesMeta = JSON.parse(readFileSync(framesMetaPath, 'utf8'));
  else { console.error(`[actpack] --skip-frames 但 ${WORK} 沒有播放逐格（上次沒有加 --keep-work）；請拿掉 --skip-frames 重跑`); process.exit(1); }

  let gt = 0;
  const schedule = order.map((tl) => {
    const pre = framesMeta.preroll[tl.cue.id] ?? (tl.enterFade > 0 ? PREROLL : 0);
    gt += pre;
    const hold = tl.cue.autoAdvance ? 0 : (HOLD[tl.cue.kind] ?? 2.0);
    const item = { id: tl.cue.id, kind: tl.cue.kind, preroll: pre, start: r3(gt), duration: r3(tl.duration), hold, autoAdvance: !!tl.cue.autoAdvance, set: tl.set, enterFade: tl.enterFade };
    gt += tl.duration + hold;
    return item;
  });
  const audioSrc = Object.fromEntries(Object.entries(manifest.audio).map(([id, a]) => [id, { source: a.source, duration: a.duration, bus: a.bus }]));
  const tlOut = {
    note: '由 app/src/cues/timeline.ts 的 buildTimelines 解析（與引擎相同），全劇 cue 集取自 app/dist/data/cues_show.js，音檔長度取自 manifest.js。schedule：start＝該 cue 第 0 秒在播放錄製中的秒數（前面是換景漸暗預捲 preroll）；hold＝教師按鍵間隔假設（秒）。',
    act, title: seg.title, segmentFile: `app/cues/show/${seg.file}`,
    musicLevelDefaults: MUSIC_LEVEL, prerollSec: PREROLL,
    cues: packTimelineCues(order, MUSIC_LEVEL),
    schedule,
    totalPlaybackSec: r3(gt),
    audio: audioSrc,
    fps: FPS,
  };
  // G6 精修：audio 只列本段 cue 實際用到的音檔（配樂、音效、配音；含時間軸自動加的題卡音效）。
  // 以前列整個資料包，第一批重驗看到第四幕的 timeline.json 有 sfx_ambulance_engine（第五幕的音效），誤以為第四幕還在用。
  {
    const used = new Set();
    for (const c of tlOut.cues) {
      if (c.audioId) used.add(c.audioId);
      for (const m of c.music) used.add(m.id);
      for (const x of c.sfx) used.add(x.id);
      for (const l of c.lines) if (l.audioId) used.add(l.audioId);
    }
    tlOut.audio = Object.fromEntries(Object.entries(audioSrc).filter(([id]) => used.has(id)));
    tlOut.audioNote = 'audio 只列本段 cue 用到的音檔（G6 精修起；以前是整個資料包的音檔表）';
  }
  const fp = fingerprints.segments[act] ?? null;
  tlOut.segmentHash = fp ? { source: fp.source, built: fp.built, sourceMerged: fp.sourceMerged, builtFromSource: fp.builtFromSource } : null;
  writeFileSync(join(OUT, 'segment_hash.json'), JSON.stringify({ note: '本包量的段落版本（G6 修正第 1 輪起）。show_review_pack 以 built 比對目前 app/dist（與建置一致）、以 source 比對目前段落檔。',
    act, method: fingerprints.method, distBuiltAt: fingerprints.distBuiltAt, generatedAt: new Date().toISOString(), ...fp }, null, 1));
  if (fp && !fp.builtFromSource) log(`注意：app/dist 不是用目前的 ${fp.file} 建的（built ${fp.built?.slice(0, 10)} ≠ 段落檔合併 ${fp.sourceMerged?.slice(0, 10)}）；本包量的是 app/dist 那一版，請先 npm run build 再重產`);
  writeFileSync(join(OUT, 'timeline.json'), JSON.stringify(tlOut, null, 1));

  // ---------------------------------------------------------------- 3. Python：投影模擬、G4 並排、混音與響度、播放光敏、影片、長度、安全
  run(PYTHON, [join(ROOT, 'tools/act_review_pack.py'), 'analyze', OUT]);
  if (!has('--skip-asr')) {
    log('配音逐字稿（faster-whisper small＋large-v3-turbo）');
    run(VENV_PY, [join(ROOT, 'tools/act_review_pack.py'), 'transcripts', OUT]);
  }
  // 擷取期間 app/dist 若被重建（多個代理同時 build），包裡的畫面可能混到新版：結束時再算一次，不同就記下來（INDEX 會列出）
  {
    const end = (await segmentFingerprints()).segments[act] ?? null;
    const shPath = join(OUT, 'segment_hash.json');
    const sh = JSON.parse(readFileSync(shPath, 'utf8'));
    sh.builtAtEnd = end?.built ?? null;
    sh.distChangedDuringRun = !!end && end.built !== sh.built;
    writeFileSync(shPath, JSON.stringify(sh, null, 1));
    if (sh.distChangedDuringRun) log(`注意：產生這個包的期間 app/dist 的 ${act} 被重建過（${sh.built?.slice(0, 10)} → ${end.built?.slice(0, 10)}），請重產`);
  }
  run(PYTHON, [join(ROOT, 'tools/act_review_pack.py'), 'index', OUT]);
  if (!has('--keep-work')) rmSync(WORK, { recursive: true, force: true });
  log(`完成 ${act} → ${OUT}`);
}
