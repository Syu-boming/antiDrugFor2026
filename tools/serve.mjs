// 本機 http 伺服器（只綁 127.0.0.1，不需要任何套件）：開發測試與「方案 B 本機伺服器＋Edge」用。
// 用法：node tools/serve.mjs [根目錄，預設 app/dist] [埠號，預設 8787]
import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { extname, join, normalize, resolve, sep } from 'node:path';

const root = resolve(process.cwd(), process.argv[2] ?? 'app/dist');
const port = Number(process.argv[3] ?? 8787);
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml', '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.woff2': 'font/woff2', '.map': 'application/json',
};

if (!existsSync(join(root, 'index.html'))) {
  console.error(`[serve] ${root} 沒有 index.html，請先在 app/ 執行 npm run build`);
  process.exit(1);
}

createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://127.0.0.1');
  let path = normalize(join(root, decodeURIComponent(url.pathname)));
  if (!path.startsWith(root + sep) && path !== root) { res.writeHead(403).end(); return; } // 防止跳出根目錄
  if (existsSync(path) && statSync(path).isDirectory()) path = join(path, 'index.html');
  if (!existsSync(path)) { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('找不到檔案'); return; }
  res.writeHead(200, { 'Content-Type': MIME[extname(path).toLowerCase()] ?? 'application/octet-stream', 'Cache-Control': 'no-store' });
  createReadStream(path).pipe(res);
}).listen(port, '127.0.0.1', () => {
  console.log(`[serve] http://127.0.0.1:${port}/  （根目錄 ${root}；Ctrl+C 結束）`);
});
