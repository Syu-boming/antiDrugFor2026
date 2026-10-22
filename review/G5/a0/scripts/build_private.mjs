// 開場＋第一幕修正用的私人建置（不碰共用的 app/dist）：esbuild → review/G5/a0/dist/app.js＋index.html＋data/（tools/pack.mjs runPack）。
// 用法：node review/G5/a0/scripts/build_private.mjs        （dist/ 已在 .gitignore）
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const APP = join(ROOT, 'app');
const OUT = join(ROOT, 'review/G5/a0/dist');
const require = createRequire(join(APP, 'package.json'));
const { build } = require('esbuild');
mkdirSync(OUT, { recursive: true });
const t0 = Date.now();
await build({
  entryPoints: [join(APP, 'src/main.ts')], outfile: join(OUT, 'app.js'), bundle: true, format: 'iife', target: ['es2020', 'chrome100'],
  minify: true, legalComments: 'none', charset: 'utf8', logLevel: 'warning', define: { 'process.env.NODE_ENV': '"production"' },
});
const css = readFileSync(join(APP, 'src/ui/theater.css'), 'utf8');
writeFileSync(join(OUT, 'index.html'), readFileSync(join(APP, 'index.html'), 'utf8').replace('/*CSS*/', () => css));
const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
await runPack({ outDir: join(OUT, 'data') });
console.log(`[a0/a1 private build] ${OUT}（${Date.now() - t0} ms）`);
