// 組 Electron 可攜版（v1.3 第 6 節；正式打包與操作說明由 G6 主線完成）：
//   1. out/app/                  ＝ resources/app 的內容：main.js、preload.js、layout.js、package.json、dist/（劇場程式＋控制台）
//   2. out/AntidrugTheater/      ＝ Windows 可攜版資料夾（有 Electron Windows zip 時）：解開 zip → 放進 resources/app → electron.exe 改名
// 用法（先在 app/ 執行 npm run build；build.mjs 會一併產生控制台，否則先跑 node console.build.mjs）：
//   node electron/pack.mjs [--win=<electron-vX-win32-x64.zip>] [--out=<輸出資料夾>]
//   預設 zip：probe/dl/electron-v44.9.1-win32-x64.zip（探針用的同一版）
// 檔名一律英數（隨身碟複製、解壓縮時不會遇到中文檔名編碼問題）；例外是給老師看的「啟動說明.txt」
// （G7 修正第 1 輪：可攜版資料夾根目錄附啟動說明，UTF-8 BOM＋CRLF，Windows 記事本可讀；交付資料夾本來就有中文檔名的說明與 PDF）。
import { cpSync, existsSync, mkdirSync, readdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
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

/** 可攜版資料夾根目錄的啟動說明（內容與 交付/使用說明.md 第三、四節、teacher_pdf 的一頁操作卡一致；署名固定） */
const STARTUP_NOTE_NAME = '啟動說明.txt';
const STARTUP_NOTE_LINES = [
  '反毒剪紙劇場《紙燈節》｜啟動說明（Windows 可攜版）',
  '許博明老師製作',
  '',
  '這個資料夾（AntidrugTheater）是正式演出用的 Windows 可攜版，不用安裝、不用網路。',
  '完整說明在上一層（交付資料夾）的「使用說明.md」；講稿、操作卡、故障卡在交付資料夾的 teacher_pdf 資料夾。',
  '',
  '一、先複製到本機硬碟',
  '1. 把隨身碟上「整個交付資料夾」複製到筆電的本機硬碟（例如桌面或 D 槽），',
  '   裡面要有 AntidrugTheater、browser、backup_video、teacher_pdf 四個資料夾。',
  '2. 不要只複製 AntidrugTheater：出狀況時要用的瀏覽器版、備援影片、紙本題卡在其他資料夾。',
  '3. 不要直接在隨身碟上執行，也不要從網路下載後直接開。',
  '',
  '二、開演前（請在彩排時先做一次）',
  '1. 筆電插電、設成高效能模式，關掉通知與自動更新。',
  '2. 接投影機與場地音響，按 Win＋P 選「延伸」。確認 Windows 的播放裝置是場地音響。',
  '3. 雙擊 AntidrugTheater.exe。',
  '   投影上出現舞台；筆電上出現深色大字的「教師控制台」。',
  '4. 在控制台按一次「下一步」＝「準備播放」（同時啟用聲音）。',
  '5. 畫面停在「許博明老師製作」署名卡。之後不再動滑鼠，改用簡報筆。',
  '',
  '三、只有一個畫面時',
  '- 同步顯示或只有一個螢幕時，程式只開舞台（沒有控制台）。',
  '  在舞台上按「準備播放」，之後用簡報筆照常演；M 鍵是教師選單（跳段、畫質）。',
  '- 想要舞台＋控制台兩個畫面：按 Win＋P 選「延伸」，等 2～3 秒控制台會自己出現；',
  '  沒有出現就關掉程式，確認是「延伸」後再雙擊 AntidrugTheater.exe。',
  '',
  '四、簡報筆與鍵盤',
  '  下一頁（PageDown，鍵盤 → 也可以）　下一步。播放中多按會被忽略，不會跳段',
  '  上一頁（PageUp）　　　　　　　　　　回上一個停格點',
  '  黑屏鍵（句點）／空白鍵　　　　　　　暫停／繼續',
  '  放映鍵（F5／Esc）　　　　　　　　　已攔截，不會跳出',
  '  R　　　　　　　　　　　　　　　　　重播這一段',
  '  M　　　　　　　　　　　　　　　　　教師選單（會出現在投影上）',
  '  簡報筆實際送出的鍵碼，可在控制台的「按鍵測試」確認。',
  '',
  '五、出問題時',
  '- 看交付資料夾的 teacher_pdf\\故障一頁卡.pdf（建議印出來放在講桌）。',
  '- 出現「Windows 已保護您的電腦」：學校允許時按「其他資訊」→「仍要執行」；',
  '  學校不允許時請資訊組協助，或改用交付資料夾的 browser\\index.html（瀏覽器版）。',
  '- 準備畫面出現「缺 N 句配音」或「無法開始：缺少……資料檔」：表示複製時漏了檔，',
  '  請把整個交付資料夾重新複製到本機硬碟再開。',
  '- 退路順序：Windows 可攜版 → 瀏覽器版（browser\\index.html）→ 備援影片（backup_video）→ 紙本題卡＋講稿。',
  '',
  '許博明老師製作',
];
/** UTF-8 BOM＋CRLF（Windows 記事本一定認得是 UTF-8） */
function startupNoteText() { return `\uFEFF${STARTUP_NOTE_LINES.join('\r\n')}\r\n`; }

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
writeFileSync(join(winDir, STARTUP_NOTE_NAME), startupNoteText(), 'utf8');
console.log(`[pack] ${join(winDir, STARTUP_NOTE_NAME)}（UTF-8 BOM、CRLF）`);
console.log(`[pack] ${winDir}（${readdirSync(winDir).length} 個項目；執行 AntidrugTheater.exe）`);
