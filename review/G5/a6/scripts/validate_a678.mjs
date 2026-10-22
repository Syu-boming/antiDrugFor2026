// 驗證第六幕代理的段落檔（暫存檔）：validate.ts＋外部 cue 編號（其他段落）；錯誤或提醒都算失敗
//   node review/G5/a6/scripts/validate_a678.mjs <段名 a6|a7|a8> <暫存檔>
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const { validateCueFile } = await import(pathToFileURL(join(ROOT, 'app/src/cues/validate.ts')).href);
const [seg, file] = process.argv.slice(2);
const data = JSON.parse(readFileSync(file, 'utf8'));
const ext = new Set();
for (const f of readdirSync(join(ROOT, 'app/cues/show')).filter((x) => /^a\d\.json$/.test(x) && x !== `${seg}.json`)) {
  try { for (const c of JSON.parse(readFileSync(join(ROOT, 'app/cues/show', f), 'utf8')).cues) ext.add(c.id); } catch { /* 別人的檔案寫到一半 */ }
}
const v = validateCueFile(data, { externalIds: ext });
console.log(`${seg} 驗證：${v.ok ? '通過' : '失敗'}，錯誤 ${v.errors.length}、提醒 ${v.warnings.length}`);
for (const e of [...v.errors, ...v.warnings]) console.log('  ' + e);
process.exit(v.ok && v.warnings.length === 0 ? 0 : 1);
