"""快速並排預覽（只給製作時看，不是驗收包）。用法：view.py out.png 檔案...（相對專案根目錄）"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[4]
out = sys.argv[1]; fs = sys.argv[2:]
H = int(dict(a.split('=') for a in [x for x in fs if x.startswith('H=')] or ['H=900'])['H'])
fs = [f for f in fs if not f.startswith('H=')]
ims = [Image.open(ROOT / f).convert('RGBA') for f in fs]
row = [im.resize((max(1, int(im.width * H / im.height)), H)) for im in ims]
W = sum(r.width for r in row) + 20 * len(row) + 20
c = Image.new('RGB', (W, H + 20), (150, 150, 160))
x = 10
for r in row:
    c.paste(r, (x, 10), r); x += r.width + 20
c.save(ROOT / out)
