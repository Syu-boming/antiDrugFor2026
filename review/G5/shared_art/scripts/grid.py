"""製作用：放大裁切＋10 px 格線與座標（量臉部範圍、座面高度用）。用法：grid.py 圖 x0 y0 x1 y1 [倍數] [輸出]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import g5lib as L
f, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:6])
k = int(sys.argv[6]) if len(sys.argv) > 6 else 4
out = sys.argv[7] if len(sys.argv) > 7 else str(L.ROOT / 'review/G5/shared_art/_tmp/grid.png')
im = Image.open(L.ROOT / f).convert('RGBA')
bg = Image.new('RGBA', im.size, (232, 226, 214, 255)); bg.alpha_composite(im)
c = bg.crop((x0, y0, x1, y1)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST).convert('RGB')
d = ImageDraw.Draw(c); fn = L.font(12)
step = 10 if (x1 - x0) <= 200 else 20 if (x1 - x0) <= 400 else 50
for x in range((x0 // step + 1) * step, x1, step):
    d.line([((x - x0) * k, 0), ((x - x0) * k, c.height)], fill=(0, 200, 255) if x % (step * 5) else (255, 0, 0), width=1)
    d.text(((x - x0) * k + 2, 2), str(x), fill=(0, 0, 255), font=fn)
for y in range((y0 // step + 1) * step, y1, step):
    d.line([(0, (y - y0) * k), (c.width, (y - y0) * k)], fill=(0, 200, 255) if y % (step * 5) else (255, 0, 0), width=1)
    d.text((2, (y - y0) * k + 2), str(y), fill=(0, 0, 255), font=fn)
c.save(out)
