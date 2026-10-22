// 第四幕修正用的私人建置（不碰共用的 app/dist）：esbuild → <out>/app.js＋index.html＋data/（tools/pack.mjs runPack）。
// 用法：node review/G5/a4/scripts/build_private.mjs [--out <資料夾>] [--cues-dir <cue 資料夾>]
//   --out       預設 review/G5/a4/dist（已在 .gitignore；用完要刪）；修正第 2 輪放 scratchpad
//   --cues-dir  預設 app/cues；給一份私人副本（只換 show/a4.json）就能試排戲，不動共用的段落檔
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const APP = join(ROOT, 'app');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] !== undefined ? args[i + 1] : d; };
const OUT = resolve(opt('--out', join(ROOT, 'review/G5/a4/dist')));
const CUES = opt('--cues-dir', null);
const require = createRequire(join(APP, 'package.json'));
const { build } = require('esbuild');
mkdirSync(OUT, { recursive: true });
const t0 = Date.now();
if (!args.includes('--data-only')) {
  await build({
    entryPoints: [join(APP, 'src/main.ts')], outfile: join(OUT, 'app.js'), bundle: true, format: 'iife', target: ['es2020', 'chrome100'],
    minify: true, legalComments: 'none', charset: 'utf8', logLevel: 'warning', define: { 'process.env.NODE_ENV': '"production"' },
  });
  const css = readFileSync(join(APP, 'src/ui/theater.css'), 'utf8');
  writeFileSync(join(OUT, 'index.html'), readFileSync(join(APP, 'index.html'), 'utf8').replace('/*CSS*/', () => css));
}
const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
await runPack({ outDir: join(OUT, 'data'), ...(CUES ? { cuesDir: resolve(CUES) } : {}) });
console.log(`[a4 private build] ${OUT}（${Date.now() - t0} ms）`);
