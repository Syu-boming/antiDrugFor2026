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
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
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
    cues: order.map((t) => ({
      id: t.cue.id, kind: t.cue.kind, title: t.cue.title, duration: r3(t.duration), autoAdvance: !!t.cue.autoAdvance, set: t.set, enterFade: t.enterFade,
      audioId: t.cue.audioId ?? null, musicLoop: t.cue.musicLoop ?? true, musicLevel: t.cue.musicLevel ?? MUSIC_LEVEL[t.cue.kind] ?? 0.6,
      compression: t.cue.compression, lamp: t.cue.lamp ?? null, quiz: t.quiz ?? null,
      lines: t.lines.map((l) => ({ id: l.line.id, speaker: l.line.speaker, text: l.line.text, audioId: l.audioId, start: r3(l.start), end: r3(l.end), duration: r3(l.duration), placeholder: l.placeholder, pages: l.pages.map((p) => ({ start: r3(p.start), end: r3(p.end), rows: p.rows })) })),
      sfx: t.sfx.map((s) => ({ ...s, at: r3(s.at) })),
      music: t.music.map((m) => ({ ...m, at: r3(m.at) })),
      anims: t.anims.map((a) => ({ name: a.name, target: a.target ?? null, start: r3(a.start), end: r3(a.end), params: a.params })),
      strings: Object.fromEntries(Object.entries(t.cue.initialState.characters ?? {}).filter(([, c]) => c.strings?.length).map(([id, c]) => [id, c.strings])),
      stringAnims: t.anims.filter((a) => a.name.startsWith('strings.')).map((a) => ({ target: a.target ?? null, name: a.name, anchors: a.params.anchors ?? null })),
    })),
    schedule,
    totalPlaybackSec: r3(gt),
    audio: audioSrc,
    fps: FPS,
  };
  writeFileSync(join(OUT, 'timeline.json'), JSON.stringify(tlOut, null, 1));

  // ---------------------------------------------------------------- 3. Python：投影模擬、G4 並排、混音與響度、播放光敏、影片、長度、安全
  run(PYTHON, [join(ROOT, 'tools/act_review_pack.py'), 'analyze', OUT]);
  if (!has('--skip-asr')) {
    log('配音逐字稿（faster-whisper small＋large-v3-turbo）');
    run(VENV_PY, [join(ROOT, 'tools/act_review_pack.py'), 'transcripts', OUT]);
  }
  run(PYTHON, [join(ROOT, 'tools/act_review_pack.py'), 'index', OUT]);
  if (!has('--keep-work')) rmSync(WORK, { recursive: true, force: true });
  log(`完成 ${act} → ${OUT}`);
}
