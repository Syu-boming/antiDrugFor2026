"""把一個資料夾的 PNG／JPG 依檔名排成接觸表：tile.py <dir> <out.jpg> [cols=4] [w=480]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
d, out = Path(sys.argv[1]), sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
w = int(sys.argv[4]) if len(sys.argv) > 4 else 480
fs = sorted([f for f in d.iterdir() if f.suffix.lower() in ('.png', '.jpg')])
h = w * 9 // 16
rows = (len(fs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * (h + 22)), (20, 18, 16))
try:
    font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 16)
except OSError:
    font = ImageFont.load_default()
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB').resize((w, h), Image.LANCZOS)
    x, y = (i % cols) * w, (i // cols) * (h + 22)
    sheet.paste(im, (x, y + 22))
    dr.text((x + 4, y + 2), f.stem, fill=(230, 220, 200), font=font)
sheet.save(out, quality=88)
print(out, len(fs))
