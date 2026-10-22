// 建置：esbuild 把 TypeScript 打包成傳統 script（IIFE）dist/app.js，樣式內嵌進 dist/index.html，
// 最後呼叫 tools/pack.mjs 產生 dist/data/*.js 資料包。產出物可直接用 file:// 開啟。
//   node build.mjs          正式建置（壓縮）
//   node build.mjs --dev    開發建置（不壓縮、附 sourcemap）
import { build } from 'esbuild';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dev = process.argv.includes('--dev');
const dist = join(here, 'dist');
mkdirSync(dist, { recursive: true });

const t0 = Date.now();
const result = await build({
  entryPoints: [join(here, 'src/main.ts')],
  outfile: join(dist, 'app.js'),
  bundle: true,
  format: 'iife',
  target: ['es2020', 'chrome100'],
  minify: !dev,
  sourcemap: dev ? 'inline' : false,
  legalComments: 'none',
  charset: 'utf8',
  logLevel: 'warning',
  metafile: true,
  define: { 'process.env.NODE_ENV': dev ? '"development"' : '"production"' },
});
const css = readFileSync(join(here, 'src/ui/theater.css'), 'utf8');
const html = readFileSync(join(here, 'index.html'), 'utf8').replace('/*CSS*/', () => css);
writeFileSync(join(dist, 'index.html'), html);
const bytes = Object.values(result.metafile.outputs).reduce((n, o) => n + o.bytes, 0);
console.log(`[build] dist/app.js ${(bytes / 1024).toFixed(0)} KB、dist/index.html（${dev ? '開發' : '正式'}，${Date.now() - t0} ms）`);

// 產生資料包
const { runPack } = await import(pathToFileURL(join(here, '../tools/pack.mjs')).href);
await runPack({});

// 教師控制台、按鍵測試頁、舞台端連結（dist/console.html、keytest.html、stage.html、console-link.js）
const { buildConsole } = await import('./console.build.mjs');
await buildConsole({ dev });

// 第三方授權聲明（legalComments 關掉了，改成隨包附一個檔）：three.js（MIT）、配樂用的 FluidR3_GM 音色庫（MIT）
const notice = (title, file) => `==== ${title} ====\n${readFileSync(file, 'utf8').trim()}\n`;
writeFileSync(join(dist, 'THIRD_PARTY_LICENSES.txt'), [
  '反毒剪紙劇場《紙燈節》第三方授權聲明（許博明老師製作）\n'
    + '配音：ElevenLabs 語音合成（付費方案、聲線庫聲線）。配樂與音效：自製；配樂以 FluidR3_GM 音色庫算成音檔。\n',
  notice('three.js 0.186.1（MIT License）', join(here, 'node_modules/three/LICENSE')),
  notice('FluidR3_GM SoundFont（MIT License）', join(here, '../audio/LICENSES/FluidR3_GM_copyright.txt')),
].join('\n'));
