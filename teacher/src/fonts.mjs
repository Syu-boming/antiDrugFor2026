// 字型：把 Noto Sans TC 可變字型（teacher/fonts/NotoSansTC-wght.ttf，SIL OFL 1.1）依實際用到的字縮小，
// 再切成 400／700／800／900 四個固定字重（teacher/fonts/subset/）。
// 原因：Chrome 列印 PDF 時，可變字型會被轉成 Type 3 字型（檔案大、部分印表機處理慢）；固定字重會以 CID TrueType 內嵌，
// 一頁操作卡從約 1.4 MB 降到幾十 KB。用 fontTools（/opt/anaconda3/bin/python3）；沒有的話 CSS 會退回可變字型。
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';

export const WEIGHTS = [400, 700, 800, 900];

const PY = `
import sys, json
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
src, outdir, textfile = sys.argv[1], sys.argv[2], sys.argv[3]
weights = json.loads(sys.argv[4])
text = open(textfile, encoding='utf-8').read()
f = TTFont(src)
opts = subset.Options()
opts.layout_features = ['*']
opts.name_IDs = ['*']
opts.notdef_outline = True
opts.hinting = False
sub = subset.Subsetter(opts)
sub.populate(text=text)
sub.subset(f)
for w in weights:
    inst = instancer.instantiateVariableFont(f, {'wght': w}, inplace=False)
    inst['OS/2'].usWeightClass = w
    inst.save(f"{outdir}/NotoSansTC-{w}.ttf")
print('ok')
`;

/** 依所有文件用到的字產生子集字型；字集沒變就不重做 */
export function buildSubsetFonts(TEACHER, texts, log) {
  const src = join(TEACHER, 'fonts/NotoSansTC-wght.ttf');
  const out = join(TEACHER, 'fonts/subset');
  mkdirSync(out, { recursive: true });
  // 用到的字＋ASCII＋常用全形標點與符號（保險）
  const base = Array.from({ length: 95 }, (_, i) => String.fromCharCode(32 + i)).join('') + '　，。、；：？！「」『』（）《》〈〉…—–－＋＝／＼｜→←↑↓▶★☆●▲■□✓≥≤×÷％＃＆＠〔〕【】・·０１２３４５６７８９';
  const chars = [...new Set([...base, ...texts.join('')])].filter((c) => c.codePointAt(0) >= 32).sort().join('');
  const sig = createHash('sha1').update(chars).update(String(WEIGHTS)).digest('hex').slice(0, 12);
  const sigFile = join(out, 'charset.sha1');
  const have = WEIGHTS.every((w) => existsSync(join(out, `NotoSansTC-${w}.ttf`)));
  if (have && existsSync(sigFile) && readFileSync(sigFile, 'utf8').trim() === sig) return { ok: true, cached: true, chars: chars.length };
  const textFile = join(out, 'charset.txt');
  writeFileSync(textFile, chars);
  for (const py of ['/opt/anaconda3/bin/python3', 'python3']) {
    const r = spawnSync(py, ['-c', PY, src, out, textFile, JSON.stringify(WEIGHTS)], { encoding: 'utf8' });
    if (r.status === 0 && /ok/.test(r.stdout)) {
      writeFileSync(sigFile, sig);
      log(`子集字型 ${WEIGHTS.join('／')}（${chars.length} 字）→ teacher/fonts/subset/`);
      return { ok: true, cached: false, chars: chars.length };
    }
  }
  log('fontTools 無法使用：PDF 改用可變字型（會變成 Type 3 字型，檔案較大）');
  return { ok: false };
}
