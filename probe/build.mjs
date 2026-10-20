// 把探針打包成單一 HTML（傳統 script 內嵌，file:// 可直接開），並組出 Electron 版的 app 資料夾。
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';

const out = await build({
  entryPoints: ['src/probe.js'], bundle: true, format: 'iife', minify: true,
  target: 'es2020', write: false, legalComments: 'none',
});
const js = out.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const html = readFileSync('template.html', 'utf8').replace("<!--SCRIPT-->", () => `<script>${js}</script>`);
mkdirSync('build/app', { recursive: true });
writeFileSync('build/探針_瀏覽器版.html', html);
writeFileSync('build/app/probe.html', html);
for (const f of ['main.js', 'preload.js', 'package.json']) copyFileSync(`electron/${f}`, `build/app/${f}`);
console.log(`probe.html ${(html.length / 1024 / 1024).toFixed(2)} MB`);
