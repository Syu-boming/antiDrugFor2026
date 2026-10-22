// 第六幕代理的私人建置（不碰共用的 app/dist）：esbuild → <out>/app.js、index.html，資料包 → <out>/data
//   node review/G5/a6/scripts/mybuild.mjs [--out <dir>] [--no-pack]
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { build } = require('esbuild');
const args = process.argv.slice(2);
const oi = args.indexOf('--out');
const out = oi >= 0 ? resolve(args[oi + 1]) : '/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad/a678/dist';
mkdirSync(out, { recursive: true });
const t0 = Date.now();
await build({
  entryPoints: [join(ROOT, 'app/src/main.ts')], outfile: join(out, 'app.js'), bundle: true, format: 'iife',
  target: ['es2020', 'chrome100'], minify: true, legalComments: 'none', charset: 'utf8', logLevel: 'warning',
  define: { 'process.env.NODE_ENV': '"production"' },
});
const css = readFileSync(join(ROOT, 'app/src/ui/theater.css'), 'utf8');
writeFileSync(join(out, 'index.html'), readFileSync(join(ROOT, 'app/index.html'), 'utf8').replace('/*CSS*/', () => css));
console.log(`[mybuild] app.js ${Date.now() - t0} ms → ${out}`);
if (!args.includes('--no-pack')) {
  const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
  await runPack({ outDir: join(out, 'data') });
  console.log(`[mybuild] pack done ${Date.now() - t0} ms`);
}
