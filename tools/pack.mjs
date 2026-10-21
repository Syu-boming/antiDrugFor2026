// 資料包產生器：把 app/cues、audio/（vo、music、sfx、lipsync）與 assets/final 轉成 app/dist/data/*.js。
// 每個資料包是傳統 script，內容呼叫 window.__pack(id, 資料)；data/manifest.js 是總表。
// G5 全劇：app/cues/show/index.json＋各段落檔 → 驗證每個段落檔與合併後的整齣（app/src/cues/show.ts）→ cues_show.js（?cues=show）。
// 這樣 file://、http、Electron 三種環境都能用 <script src> 載入素材（file:// 擋 fetch 與 ES module）。
//
// 用法（在專案根目錄或 app/ 皆可）：
//   node tools/pack.mjs
//   node tools/pack.mjs --audio-dir <資料夾> --assets-dir <資料夾> --out <資料夾> [--sources <json>]   （測試用，覆寫來源）
// 只讀取素材，不會改動 assets/ 與 audio/。
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

/** 用 esbuild 把 app/src 的 TypeScript 模組打包成可在 Node 執行的 ESM（show.ts 會 import validate.ts） */
export async function importTs(rel) {
  const require = createRequire(join(ROOT, 'app/package.json'));
  const esbuild = require('esbuild');
  const r = await esbuild.build({ entryPoints: [join(ROOT, rel)], bundle: true, format: 'esm', platform: 'node', write: false, logLevel: 'silent' });
  return import(`data:text/javascript;base64,${Buffer.from(r.outputFiles[0].text).toString('base64')}`);
}

/** 讀 app/cues/show（index.json＋段落檔），驗證並合併；沒有 show 資料夾回傳 null */
export async function loadShow(cuesDir = join(ROOT, 'app/cues')) {
  const dir = join(cuesDir, 'show');
  if (!existsSync(join(dir, 'index.json'))) return null;
  const { validateShow } = await importTs('app/src/cues/show.ts');
  const index = JSON.parse(readFileSync(join(dir, 'index.json'), 'utf8'));
  const files = {};
  for (const f of index.segments ?? []) {
    const p = join(dir, f);
    if (existsSync(p)) files[f] = JSON.parse(readFileSync(p, 'utf8'));
  }
  return { index, files, ...validateShow(index, files) };
}
const MIME = {
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.m4a': 'audio/mp4',
  '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
};
const AUDIO_EXT = new Set(['.wav', '.mp3', '.ogg', '.m4a']);
const IMAGE_EXT = new Set(['.png', '.webp', '.jpg', '.jpeg']);

const listFiles = (dir) => (existsSync(dir) ? readdirSync(dir).filter((f) => !f.startsWith('.') && statSync(join(dir, f)).isFile()) : []);
function walk(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const f of readdirSync(dir)) {
    if (f.startsWith('.') || f.startsWith('_')) continue;
    const p = join(dir, f);
    if (statSync(p).isDirectory()) out.push(...walk(p)); else out.push(p);
  }
  return out;
}

const dataUrl = (path) => `data:${MIME[extname(path).toLowerCase()] ?? 'application/octet-stream'};base64,${readFileSync(path).toString('base64')}`;

/** 去掉版本號：vo_a2_c014_01_v02 → { id: vo_a2_c014_01, version: 2 } */
function splitVersion(name) {
  const m = /^(.*)_v(\d+)$/i.exec(name);
  return m ? { id: m[1], version: Number(m[2]) } : { id: name, version: 0 };
}

/** 音檔長度（秒）：優先 ffprobe，退而解析 WAV 檔頭 */
function audioDuration(path) {
  try {
    const out = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
    const d = Number(out.trim());
    if (Number.isFinite(d) && d > 0) return Math.round(d * 1000) / 1000;
  } catch { /* 沒有 ffprobe */ }
  if (extname(path).toLowerCase() === '.wav') {
    const b = readFileSync(path);
    let off = 12, byteRate = 0, dataLen = 0;
    while (off + 8 <= b.length) {
      const id = b.toString('ascii', off, off + 4), size = b.readUInt32LE(off + 4);
      if (id === 'fmt ') byteRate = b.readUInt32LE(off + 16);
      if (id === 'data') { dataLen = size; break; }
      off += 8 + size + (size % 2);
    }
    if (byteRate) return Math.round((dataLen / byteRate) * 1000) / 1000;
  }
  return null;
}

function writePack(path, entries) {
  const body = entries.map(([id, data]) => `window.__pack(${JSON.stringify(id)},${JSON.stringify(data)});`).join('\n');
  writeFileSync(path, `/* 反毒剪紙劇場資料包（tools/pack.mjs 自動產生，請勿手改） */\n${body}\n`);
  return statSync(path).size;
}

/** 選出每個 id 的最新版本 */
function latest(files, dir, pattern) {
  const best = new Map();
  for (const f of files) {
    const ext = extname(f).toLowerCase();
    const { id, version } = splitVersion(basename(f, extname(f)));
    if (pattern && !pattern.test(id)) continue;
    const cur = best.get(id);
    if (!cur || version > cur.version) best.set(id, { id, version, path: join(dir, f), ext });
  }
  return [...best.values()].sort((a, b) => a.id.localeCompare(b.id));
}

export async function runPack(opts = {}) {
  const tmp = `${opts.outDir ?? join(ROOT, 'app/dist/data')}.tmp-${process.pid}`;
  try { return await runPackInner(opts); } catch (err) { rmSync(tmp, { recursive: true, force: true }); throw err; }
}

async function runPackInner(opts) {
  const cuesDir = opts.cuesDir ?? join(ROOT, 'app/cues');
  const audioDir = opts.audioDir ?? join(ROOT, 'audio');
  const assetsDir = opts.assetsDir ?? join(ROOT, 'assets/final');
  const finalDir = opts.outDir ?? join(ROOT, 'app/dist/data');
  const rel = (p) => relative(ROOT, p).split('\\').join('/');
  // 先寫到暫存資料夾、最後才換上（多個代理同時 build 時，別人的測試不會讀到寫一半或被刪掉的資料包）
  const outDir = `${finalDir}.tmp-${process.pid}`;
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });
  const manifest = { format: 'antidrug-packs/1', builtAt: new Date().toISOString(), cueSets: {}, audio: {}, images: {}, lipsync: {}, json: {} };
  let total = 0;
  const warnings = [];

  // 1. cue 檔（打包前先驗證；有錯誤就停止）
  const { validateCueFile } = await import(pathToFileURL(join(ROOT, 'app/src/cues/validate.ts')).href);
  for (const f of listFiles(cuesDir).filter((f) => f.endsWith('.json') && !f.endsWith('.schema.json'))) {
    const name = basename(f, '.json');
    const data = JSON.parse(readFileSync(join(cuesDir, f), 'utf8'));
    const v = validateCueFile(data);
    if (!v.ok) throw new Error(`cue 檔 ${f} 驗證失敗：\n  ${v.errors.join('\n  ')}`);
    for (const w of v.warnings) warnings.push(`${f}：${w}`);
    const file = `cues_${name}.js`;
    total += writePack(join(outDir, file), [[`cues:${name}`, data]]);
    manifest.cueSets[name] = file;
  }
  // 1b. 全劇（app/cues/show/）：每個段落檔與合併後的整齣都要驗證通過
  const show = await loadShow(cuesDir);
  if (show) {
    if (!show.ok) throw new Error(`全劇 cue 集驗證失敗：\n  ${show.errors.join('\n  ')}`);
    for (const w of show.warnings) warnings.push(`show：${w}`);
    total += writePack(join(outDir, 'cues_show.js'), [['cues:show', show.merged]]);
    manifest.cueSets.show = 'cues_show.js';
  }

  // 2. 配音：逐句一檔 audio/vo/vo_<台詞編號>_vNN.(wav|mp3)，取最新版本；依 cue 分包
  const vo = latest(listFiles(join(audioDir, 'vo')).filter((f) => AUDIO_EXT.has(extname(f).toLowerCase())), join(audioDir, 'vo'), /^vo_a\d_c\d{3}_\d{2}$/);
  const byCue = new Map();
  for (const a of vo) {
    const cue = a.id.slice(3, 10); // vo_a2_c014_01 → a2_c014
    if (!byCue.has(cue)) byCue.set(cue, []);
    byCue.get(cue).push(a);
  }
  for (const [cue, list] of byCue) {
    const file = `vo_${cue}.js`;
    total += writePack(join(outDir, file), list.map((a) => [`audio:${a.id}`, dataUrl(a.path)]));
    for (const a of list) manifest.audio[a.id] = { file, duration: audioDuration(a.path), source: rel(a.path), bus: 'vo' };
  }

  // 3. 音樂（每首一包）與音效（合成一包）
  for (const a of latest(listFiles(join(audioDir, 'music')).filter((f) => AUDIO_EXT.has(extname(f).toLowerCase())), join(audioDir, 'music'))) {
    const file = `music_${a.id}.js`;
    total += writePack(join(outDir, file), [[`audio:${a.id}`, dataUrl(a.path)]]);
    manifest.audio[a.id] = { file, duration: audioDuration(a.path), source: rel(a.path), bus: 'music' };
  }
  const sfx = latest(listFiles(join(audioDir, 'sfx')).filter((f) => AUDIO_EXT.has(extname(f).toLowerCase())), join(audioDir, 'sfx'));
  if (sfx.length) {
    total += writePack(join(outDir, 'sfx.js'), sfx.map((a) => [`audio:${a.id}`, dataUrl(a.path)]));
    for (const a of sfx) manifest.audio[a.id] = { file: 'sfx.js', duration: audioDuration(a.path), source: rel(a.path), bus: 'sfx' };
  }

  // 4. 對嘴資料：audio/lipsync/<台詞編號>_vNN.json（{ fps, frames }）
  const lips = latest(listFiles(join(audioDir, 'lipsync')).filter((f) => f.endsWith('.json')), join(audioDir, 'lipsync'));
  if (lips.length) {
    total += writePack(join(outDir, 'lipsync.js'), lips.map((l) => [`lip:${l.id}`, JSON.parse(readFileSync(l.path, 'utf8'))]));
    for (const l of lips) manifest.lipsync[l.id] = { file: 'lipsync.js' };
  }

  // 5. 圖像：assets/final/**。圖像 id＝相對 assets/final 的路徑（去掉副檔名與 _vNN 版本號），
  //    例如 chr-ale_head_v03.png → chr-ale_head；face/ale/mouth_closed.png → face/ale/mouth_closed。
  //    依路徑第一段（子資料夾）或檔名第一段分包：img_chr-ale.js、img_face_ale.js。
  //    另外 app/asset-sources.json 列出「正式素材還沒到時」的退路來源（例如 assets/parts/ale_v03），
  //    只有 assets/final 沒有同一個 id 時才打包退路來源（manifest 標示 fallback: true）。
  const relId = (p) => {
    const r = relative(assetsDir, p).split('\\').join('/');
    const dir = r.includes('/') ? r.slice(0, r.lastIndexOf('/') + 1) : '';
    const { id, version } = splitVersion(basename(p, extname(p)));
    return { id: dir + id, version, group: dir ? dir.slice(0, -1).split('/').slice(0, 2).join('_') : (id.split('_')[0] || 'misc') };
  };
  const imgs = walk(assetsDir).filter((p) => IMAGE_EXT.has(extname(p).toLowerCase()));
  const groups = new Map();
  const addImage = (id, version, group, path, fallback) => {
    if (!groups.has(group)) groups.set(group, new Map());
    const g = groups.get(group);
    if (!g.has(id) || g.get(id).version < version) g.set(id, { id, version, path, fallback });
  };
  for (const p of imgs) { const r = relId(p); addImage(r.id, r.version, r.group, p, false); }
  manifest.json = {};
  const jsonEntries = [];
  const jsons = walk(assetsDir).filter((p) => extname(p).toLowerCase() === '.json');
  const bestJson = new Map();
  for (const p of jsons) {
    const r = relId(p);
    const cur = bestJson.get(r.id);
    if (!cur || cur.version < r.version) bestJson.set(r.id, { ...r, path: p });
  }
  for (const j of bestJson.values()) {
    try { jsonEntries.push([`json:${j.id}`, JSON.parse(readFileSync(j.path, 'utf8'))]); manifest.json[j.id] = { file: 'assets_json.js', source: rel(j.path) }; }
    catch (err) { warnings.push(`素材 JSON 解析失敗 ${rel(j.path)}：${err.message}`); }
  }
  const srcFile = opts.sourcesFile ?? join(ROOT, 'app/asset-sources.json');
  if (existsSync(srcFile)) {
    const src = JSON.parse(readFileSync(srcFile, 'utf8'));
    const have = new Set([...groups.values()].flatMap((g) => [...g.keys()]));
    for (const [id, path] of Object.entries(src.images ?? {})) {
      if (have.has(id)) continue;
      const abs = join(ROOT, path);
      if (!existsSync(abs)) { warnings.push(`退路圖像不存在：${path}`); continue; }
      addImage(id, -1, `fallback_${id.split('/')[0].split('_')[0]}`, abs, true);
    }
    for (const [id, path] of Object.entries(src.json ?? {})) {
      if (manifest.json[id]) continue;
      const abs = join(ROOT, path);
      if (!existsSync(abs)) { warnings.push(`退路 JSON 不存在：${path}`); continue; }
      jsonEntries.push([`json:${id}`, JSON.parse(readFileSync(abs, 'utf8'))]);
      manifest.json[id] = { file: 'assets_json.js', source: rel(abs), fallback: true };
    }
  }
  if (jsonEntries.length) total += writePack(join(outDir, 'assets_json.js'), jsonEntries);
  for (const [group, m] of groups) {
    const file = `img_${group.replace(/[^A-Za-z0-9_-]/g, '_')}.js`;
    total += writePack(join(outDir, file), [...m.values()].map((i) => [`img:${i.id}`, dataUrl(i.path)]));
    for (const i of m.values()) manifest.images[i.id] = { file, source: rel(i.path), ...(i.fallback ? { fallback: true } : {}) };
  }

  total += writePack(join(outDir, 'manifest.js'), [['manifest', manifest]]);
  rmSync(finalDir, { recursive: true, force: true });
  renameSync(outDir, finalDir);
  const nAudio = Object.keys(manifest.audio).length;
  const nFallback = Object.values(manifest.images).filter((i) => i.fallback).length;
  console.log(`[pack] cue 檔 ${Object.keys(manifest.cueSets).length}、音檔 ${nAudio}（配音 ${vo.length}）、對嘴 ${lips.length}、圖像 ${Object.keys(manifest.images).length}（退路 ${nFallback}）、素材 JSON ${Object.keys(manifest.json).length}；資料包共 ${(total / 1024 / 1024).toFixed(2)} MB → ${rel(finalDir)}`);
  for (const w of warnings) console.warn(`[pack] 提醒：${w}`);
  return manifest;
}

// 直接執行時才跑（被 build.mjs import 時由它呼叫）
if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const args = process.argv.slice(2);
  const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
  const abs = (p) => (p ? resolve(process.cwd(), p) : undefined);
  runPack({ audioDir: abs(opt('--audio-dir')), assetsDir: abs(opt('--assets-dir')), outDir: abs(opt('--out')), cuesDir: abs(opt('--cues-dir')), sourcesFile: abs(opt('--sources')) })
    .catch((err) => { console.error(`[pack] ${err.message}`); process.exit(1); });
}
