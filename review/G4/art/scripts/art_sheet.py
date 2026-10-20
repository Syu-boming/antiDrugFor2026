"""G4 美術：所有採用圖的接觸表 review/G4/art/art_sheet.png（只供製作檢視，不是舞台圖）。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "assets/final"
FONT = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
f = ImageFont.truetype(FONT, 22, index=10)
fs = ImageFont.truetype(FONT, 15, index=10)
groups = [
    ("景片（遠／中／前景）", ["bg-workshop-back_v02.jpg", "bg-workshop-lanterns_v01.png", "bg-workshop-table_v02.png", "bg-workshop-wing_v01.png", "bg-workshop-floor_v01.jpg"]),
    ("無字貼圖（布幕、署名卡底紙；署名由程式排字）", ["tex-curtain-paper_v01.png", "tex-titlecard-paper_v01.png"]),
    ("孩子（v04 姿勢圖與母版，已裁邊＋顏色外擴；姿勢圖另拆頭層＋身體層，可轉頭 ±2.5°）", ["chr-xiaoqing_pose-reach-worried_v04.png", "chr-xiaoyu_pose-stepback-surprised_v04.png", "chr-xiaoqing_master_v04.png", "chr-xiaoyu_master_v04.png",
     "chr-xiaoqing_pose-reach-worried-body_v04.png", "chr-xiaoqing_pose-reach-worried-head_v04.png", "chr-xiaoyu_pose-stepback-surprised-body_v04.png", "chr-xiaoyu_pose-stepback-surprised-head_v04.png"]),
    ("阿樂叔叔分件 v04（rig/；接縫修正＋乾淨困惑頭；描邊底圖另附 -outline）", sorted(p.name for p in (FIN / "rig").glob("chr-ale_*_v04.png") if "outline" not in p.name)),
    ("臉部換片（face/；每角色 8 片，見 face_sheet.png）", sorted(str(p.relative_to(FIN)) for p in (FIN / "face").glob("*/chr-*_v01.png"))),
]
TH = {0: 220, 1: 200, 2: 300, 3: 200, 4: 70}
blocks = []
for gi, (title, files) in enumerate(groups):
    tiles = []
    for fn in files:
        p = FIN / fn if (FIN / fn).exists() else FIN / "rig" / fn
        im = Image.open(p).convert("RGBA")
        h = TH[gi]
        w = max(1, int(im.width * h / im.height))
        if w > 640:
            w = 640; h = int(im.height * 640 / im.width)
        im = im.resize((w, h), Image.LANCZOS)
        bg = Image.new("RGBA", im.size, (150, 150, 146, 255))
        bg.alpha_composite(im)
        tiles.append((Path(fn).name.replace("_v0", " v0"), bg.convert("RGB")))
    blocks.append((title, tiles))
W = 2000
rows = []
for title, tiles in blocks:
    x, y, line_h, placed = 20, 0, 0, []
    for name, t in tiles:
        tw = max(t.width, int(fs.getlength(name)) + 10)
        if x + tw > W - 20:
            x = 20; y += line_h + 34; line_h = 0
        placed.append((name, t, x, y))
        x += tw + 18; line_h = max(line_h, t.height)
    rows.append((title, placed, y + line_h + 34))
H = 70 + sum(h + 50 for _, _, h in rows)
S = Image.new("RGB", (W, H), (44, 42, 40))
d = ImageDraw.Draw(S)
d.text((20, 16), "G4 美術採用圖接觸表（assets/final/）— 製作檢視用；灰底＝透明區；圖中沒有任何生成文字", font=f, fill=(240, 240, 240))
y0 = 64
for title, placed, h in rows:
    d.text((20, y0), title, font=f, fill=(240, 210, 120))
    for name, t, x, y in placed:
        S.paste(t, (x, y0 + 36 + y))
        d.text((x, y0 + 36 + y + t.height + 2), name, font=fs, fill=(210, 210, 210))
    y0 += h + 50
S.save(ROOT / "review/G4/art/art_sheet.png")
print(S.size)
