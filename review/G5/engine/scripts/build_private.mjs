// 共用元件代理（G5 修正第 1 輪）的私人建置：不碰共用的 app/dist。
// 用法：node review/G5/engine/scripts/build_private.mjs [輸出資料夾，預設 review/G5/engine/dist] [--nopack 只重建 app.js]
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const APP = join(ROOT, 'app');
const argOut = process.argv.slice(2).find((a) => !a.startsWith('--'));
const OUT = argOut ? resolve(process.cwd(), argOut) : join(ROOT, 'review/G5/engine/dist');
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
if (!process.argv.includes('--nopack') || !existsSync(join(OUT, 'data/manifest.js'))) {
  const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
  await runPack({ outDir: join(OUT, 'data') });
}
console.log(`[engine private build] ${OUT}（${Date.now() - t0} ms）`);
