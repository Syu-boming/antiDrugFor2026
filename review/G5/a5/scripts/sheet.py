"""把 snaps 裡某個 cue 的試拍排成一張（依時間排序）：python sheet.py a5_c001 [cols]"""
import glob, re, sys
from PIL import Image, ImageDraw
cue = sys.argv[1]; cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3
fs = glob.glob(f"/Users/boming/Documents/AI tool/反毒小劇場/review/G5/a5/checks/snaps/{cue}_*.png")
key = lambda f: 1e9 if f.endswith('_end.png') else float(re.search(r'_([0-9.]+)\.png$', f).group(1))
fs = sorted(fs, key=key)
ims = [Image.open(f).convert('RGB') for f in fs]
w, h = ims[0].size
s = 0.5
W, H = int(w * s), int(h * s)
rows = (len(ims) + cols - 1) // cols
c = Image.new('RGB', (W * cols, H * rows), (0, 0, 0))
d = ImageDraw.Draw(c)
for i, (f, im) in enumerate(zip(fs, ims)):
    x, y = (i % cols) * W, (i // cols) * H
    c.paste(im.resize((W, H)), (x, y))
    d.rectangle([x, y, x + 70, y + 16], fill=(0, 0, 0)); d.text((x + 3, y + 2), f.split('_')[-1][:-4], fill=(255, 255, 0))
out = f"/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad/a5/{cue}_sheet.png"
c.save(out); print(out)
