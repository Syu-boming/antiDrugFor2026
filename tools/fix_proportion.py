"""母版頭身校正：只把指定的「身體水平帶」縱向拉長，讓頭身落在目標值；頭部、手、鞋不動，不重畫任何內容。

為什麼：Codex 生成兩次後頭身仍不足（模型傾向畫大頭）。v1.2 第 22.1 節允許以程式做局部修正並用差異圖確認沒有漂移；
這裡只做縱向重取樣（LANCZOS），臉、手、鞋所在的列完全不變。

用法：
  /opt/anaconda3/bin/python3 tools/fix_proportion.py 輸入.png 輸出.png --chin 291 --zones 380:650,1000:1330 --target 6.2 \
      [--compare review/G2/ale_proportion_fix.png]
  --zones：要拉長的列範圍（原圖座標），只選輪廓近乎垂直、沒有手和臉的列（例如胸口到腰、褲管中段）。
  頭頂／腳底：紙芯白邊內側第一個／最後一個非白色不透明列（同 tools/proportion_grid.py）。
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage


def inner_extent(im):
    """紙芯白邊內側的頭頂與腳底列。白邊外緣有 1 px 灰色抗鋸齒線，所以先把不透明區內縮 5 px 再找非白色像素。"""
    a = np.array(im.convert("RGBA"))
    rgb = a[..., :3].astype(np.float32)
    v = rgb.max(-1)
    s = (rgb.max(-1) - rgb.min(-1)) / (v + 1e-6)
    core = ndimage.binary_erosion(a[..., 3] > 200, iterations=5)
    nonwhite = core & ~((v > 215) & (s < 0.15))
    rows = np.nonzero(nonwhite.sum(1) > 0)[0]
    return int(rows.min()), int(rows.max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--chin", type=int, required=True)
    ap.add_argument("--zones", required=True)
    ap.add_argument("--target", type=float, required=True)
    ap.add_argument("--compare", default=None)
    args = ap.parse_args()
    im = Image.open(args.src).convert("RGBA")
    top, bot = inner_extent(im)
    head = args.chin - top
    height = bot - top
    zones = [tuple(int(v) for v in z.split(":")) for z in args.zones.split(",")]
    zlen = sum(b - a for a, b in zones)
    need = args.target * head - height
    f = 1 + need / zlen
    bands, cur = [], 0
    for a, b in zones:
        bands.append(im.crop((0, cur, im.width, a)))
        z = im.crop((0, a, im.width, b))
        bands.append(z.resize((im.width, round((b - a) * f)), Image.LANCZOS))
        cur = b
    bands.append(im.crop((0, cur, im.width, im.height)))
    out = Image.new("RGBA", (im.width, sum(b.height for b in bands)), (0, 0, 0, 0))
    y = 0
    for b in bands:
        out.paste(b, (0, y))
        y += b.height
    out.save(args.dst)
    t2, b2 = inner_extent(out)
    info = dict(src=args.src, dst=args.dst, zones=zones, stretch_factor=round(f, 4),
                before=dict(top=top, bottom=bot, chin=args.chin, heads=round(height / head, 3)),
                after=dict(top=t2, bottom=b2, chin=args.chin, heads=round((b2 - t2) / head, 3), size=list(out.size)))
    print(json.dumps(info, ensure_ascii=False, indent=1))
    if args.compare:
        H = max(im.height, out.height) + 80
        sheet = Image.new("RGB", (im.width * 2 + 60, H), (206, 202, 194))
        sheet.paste(im, (20, 60), im)
        sheet.paste(out, (im.width + 40, 60), out)
        d = ImageDraw.Draw(sheet)
        try:
            fnt = ImageFont.truetype("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 30, index=10)
        except OSError:
            fnt = ImageFont.load_default()
        d.text((20, 14), f"校正前 {info['before']['heads']:.2f} 頭身", font=fnt, fill=(20, 20, 20))
        d.text((im.width + 40, 14), f"校正後 {info['after']['heads']:.2f} 頭身（縱向拉長帶 ×{f:.3f}）", font=fnt, fill=(20, 20, 20))
        off = 0
        for a, b in zones:
            for x0, y0, y1 in ((20, a, b), (im.width + 40, a + off, a + off + round((b - a) * f))):
                d.rectangle([x0, 60 + y0, x0 + 14, 60 + y1], fill=(60, 90, 200))
            off += round((b - a) * f) - (b - a)
        for x0, yy in ((20, top), (20, args.chin), (im.width + 40, t2), (im.width + 40, args.chin)):
            d.line([x0, 60 + yy, x0 + im.width, 60 + yy], fill=(200, 40, 40), width=2)
        sheet.save(args.compare)


if __name__ == "__main__":
    main()
