// 教師控制台建置（在 build.mjs 之後執行；也可單獨跑 node console.build.mjs [--dev]）：
//   dist/console.html ＋ console.js      教師控制台（筆電端）
//   dist/keytest.html ＋ keytest.js      簡報筆按鍵測試頁
//   dist/console-link.js                 舞台端連結（讀 window.__engine，跟控制台同步）
//   dist/stage.html                      舞台視窗＝dist/index.html 多載入 console-link.js（投影端，畫面與 index.html 完全相同）
// 全部是傳統 script（IIFE），file:// 與 Electron 都能直接開；不載入任何外部資源。
import { build } from 'esbuild';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

export async function buildConsole({ dev = false, dist = join(here, 'dist') } = {}) {
  const t0 = Date.now();
  if (!existsSync(join(dist, 'index.html'))) throw new Error('[console] 找不到 dist/index.html，請先執行 npm run build');
  const common = {
    bundle: true, format: 'iife', target: ['es2020', 'chrome100'], minify: !dev, sourcemap: dev ? 'inline' : false,
    legalComments: 'none', charset: 'utf8', logLevel: 'warning',
  };
  await Promise.all([
    build({ ...common, entryPoints: [join(here, 'src/ui/console.ts')], outfile: join(dist, 'console.js') }),
    build({ ...common, entryPoints: [join(here, 'src/ui/console-keytest.ts')], outfile: join(dist, 'keytest.js') }),
    build({ ...common, entryPoints: [join(here, 'src/ui/console-link.ts')], outfile: join(dist, 'console-link.js') }),
  ]);
  const css = readFileSync(join(here, 'src/ui/console.css'), 'utf8');
  for (const page of ['console.html', 'keytest.html']) {
    const html = readFileSync(join(here, page), 'utf8').replace('/*CSS*/', () => css);
    writeFileSync(join(dist, page), html);
  }
  // 舞台視窗：index.html 加上 console-link.js（若主線已經把它加進 index.html，就原樣複製）
  let stage = readFileSync(join(dist, 'index.html'), 'utf8');
  if (!stage.includes('console-link.js')) {
    const tag = '<script src="app.js"></script>';
    if (!stage.includes(tag)) throw new Error('[console] dist/index.html 找不到 <script src="app.js"></script>，無法產生 stage.html');
    stage = stage.replace(tag, `${tag}\n<script src="console-link.js"></script>`);
  }
  writeFileSync(join(dist, 'stage.html'), stage);
  console.log(`[console] dist/console.html、keytest.html、stage.html、console-link.js（${dev ? '開發' : '正式'}，${Date.now() - t0} ms）`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  await buildConsole({ dev: process.argv.includes('--dev') });
}
