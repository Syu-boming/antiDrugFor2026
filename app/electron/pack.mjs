// 組 Electron 可攜版（v1.3 第 6 節；正式打包與操作說明由 G6 主線完成）：
//   1. out/app/                  ＝ resources/app 的內容：main.js、preload.js、layout.js、package.json、dist/（劇場程式＋控制台）
//   2. out/AntidrugTheater/      ＝ Windows 可攜版資料夾（有 Electron Windows zip 時）：解開 zip → 放進 resources/app → electron.exe 改名
// 用法（先在 app/ 執行 npm run build；build.mjs 會一併產生控制台，否則先跑 node console.build.mjs）：
//   node electron/pack.mjs [--win=<electron-vX-win32-x64.zip>] [--out=<輸出資料夾>]
//   預設 zip：probe/dl/electron-v44.9.1-win32-x64.zip（探針用的同一版）
// 檔名一律英數（隨身碟複製、解壓縮時不會遇到中文檔名編碼問題）。
import { cpSync, existsSync, mkdirSync, readdirSync, renameSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const APP = resolve(here, '..');
const ROOT = resolve(APP, '..');
const arg = (n) => { const a = process.argv.find((x) => x.startsWith(`--${n}=`)); return a ? a.slice(n.length + 3) : null; };
const OUT = resolve(arg('out') ?? join(here, 'out'));
const DIST = join(APP, 'dist');

for (const f of ['index.html', 'stage.html', 'console.html', 'console-link.js', 'data/manifest.js']) {
  if (!existsSync(join(DIST, f))) { console.error(`[pack] 缺 dist/${f}：請先在 app/ 執行 npm run build（以及 node console.build.mjs）`); process.exit(1); }
}

const appDir = join(OUT, 'app');
rmSync(appDir, { recursive: true, force: true });
mkdirSync(appDir, { recursive: true });
for (const f of ['main.js', 'preload.js', 'layout.js', 'package.json']) cpSync(join(here, f), join(appDir, f));
cpSync(DIST, join(appDir, 'dist'), { recursive: true, filter: (src) => !src.endsWith('.map') });
console.log(`[pack] ${appDir}`);

const zip = arg('win') ?? join(ROOT, 'probe/dl/electron-v44.9.1-win32-x64.zip');
if (!existsSync(zip)) {
  console.log(`[pack] 沒有 Electron Windows zip（${zip}），只組 resources/app。`);
  process.exit(0);
}
const winDir = join(OUT, 'AntidrugTheater');
rmSync(winDir, { recursive: true, force: true });
mkdirSync(winDir, { recursive: true });
execFileSync('unzip', ['-q', zip, '-d', winDir]);
const res = join(winDir, 'resources');
rmSync(join(res, 'default_app.asar'), { force: true });
cpSync(appDir, join(res, 'app'), { recursive: true });
if (existsSync(join(winDir, 'electron.exe'))) renameSync(join(winDir, 'electron.exe'), join(winDir, 'AntidrugTheater.exe'));
console.log(`[pack] ${winDir}（${readdirSync(winDir).length} 個項目；執行 AntidrugTheater.exe）`);
