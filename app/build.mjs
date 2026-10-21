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
