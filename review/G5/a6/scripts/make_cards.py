"""第六幕代理：a7_c001 三張大紙卡、a7_c002 口訣卡的卡片圖（程式排版；標題與口訣文字由 app/src/sets/a6_shop.ts 在執行時排版）。

用法：
  /opt/anaconda3/bin/python3 review/G5/a6/scripts/make_cards.py [--c1 圖 --c2 圖 --c3 圖]
  預設來源：review/G5/a6/cards_src/a3_c002_9.0.png、a4_c012_6.0.png、a5_c006_6.0.png
  （capture_cards.mjs 從目前的 a3／a4／a5 畫面擷取、不含字幕；驗收包產生後可改用
   review/G5/a3/pack/capture/keyframes、a4、a5 的關鍵影格重跑，卡片位置與尺寸不變）
輸出：assets/final/sets/a6_shop/card-{1,2,3}_v01.png（1050×810）、card-mnemonic_v01.png（1400×620）
卡片＝米色厚紙卡（圓角、牛皮紙邊、深色細邊）＋上方空白標題列＋插畫窗（來源影格裁切、略降彩、加紙紋）；圖裡沒有任何文字。
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as PD  # noqa: E402

OUT = ROOT / "assets/final/sets/a6_shop"
SRC = ROOT / "review/G5/a6/cards_src"
FIN = ROOT / "assets/final"
INK = (78, 62, 51, 255)
PAPER = (247, 239, 222, 255)
KRAFT = (190, 150, 104, 255)


def rounded_mask(w, h, r, ss=3):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def card_base(W, H, r=40):
    sh = PD.Sheet(W, H, ss=2)
    sh.rect(2, 2, W - 2, H - 2, KRAFT, line=0, r=r)
    sh.rect(12, 12, W - 12, H - 12, PAPER, line=0, r=r - 8)
    a = sh.finish()
    im = Image.fromarray(a, "RGBA")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([1, 1, W - 2, H - 2], r, outline=INK, width=4)
    return im


def illustration(src, box_w, box_h, cx_frac=0.5, cy_frac=0.5):
    im = Image.open(src).convert("RGB")
    W, H = im.size
    asp = box_w / box_h
    cw = min(W, int(H * asp))
    ch = int(cw / asp)
    x0 = int(np.clip(cx_frac * W - cw / 2, 0, W - cw))
    y0 = int(np.clip(cy_frac * H - ch / 2, 0, H - ch))
    im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((box_w, box_h), Image.LANCZOS)
    # 印在紙卡上的插畫：略降彩、略提亮、輕微柔化，乘上紙紋
    im = ImageEnhance.Color(im).enhance(0.9)
    im = ImageEnhance.Brightness(im).enhance(1.04)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    a = np.array(im).astype(np.float32)
    a *= PD.paper_tex(box_w, box_h)[..., None]
    a = a * 0.94 + np.array([250, 240, 222]) * 0.06
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def make_card(n, src, cx):
    W, H = 1050, 810
    im = card_base(W, H)
    d = ImageDraw.Draw(im)
    # 標題列下緣細線（標題文字執行時排版，位置 y≈0.098H）
    d.line([(70, 152), (W - 70, 152)], fill=(150, 118, 88, 255), width=3)
    bw, bh = W - 96, H - 168 - 48
    ill = illustration(src, bw, bh, cx)
    mask = rounded_mask(bw, bh, 22)
    im.paste(ill, (48, 168), mask)
    d.rounded_rectangle([48, 168, 48 + bw - 1, 168 + bh - 1], 22, outline=INK, width=4)
    p = OUT / f"card-{n}_v01.png"
    PD.save(np.array(im), p)
    return {"file": str(p.relative_to(ROOT)), "src": str(Path(src).relative_to(ROOT)) if str(src).startswith(str(ROOT)) else str(src), "crop_cx": cx}


def pose_crop(path, top_frac=0.0, bot_frac=0.6):
    im = Image.open(path).convert("RGBA")
    a = np.array(im)[..., 3] > 128
    ys, xs = np.nonzero(a)
    y0, y1 = ys.min(), ys.max()
    hgt = y1 - y0
    c = im.crop((0, int(y0 + top_frac * hgt), im.width, int(y0 + bot_frac * hgt)))
    bb = c.getbbox()
    return c.crop(bb) if bb else c


def make_mnemonic():
    W, H = 1400, 620
    im = card_base(W, H, r=44)
    tiles = [("chr-xiaoqing_pose-cross_v06.png", (238, 220, 196, 255)), ("chr-xiaoyu_pose-palmno_v06.png", (226, 230, 214, 255)),
             ("chr-xiaoqing_pose-pointr_v07.png", (232, 222, 236, 255)), ("chr-xiaoyu_pose-forehead_v06.png", (222, 230, 236, 255))]
    d = ImageDraw.Draw(im)
    for i, (f, bg) in enumerate(tiles):
        cx = int(W * (0.125 + i * 0.25))
        x0, x1, y0, y1 = cx - 150, cx + 150, 46, 440
        d.rounded_rectangle([x0, y0, x1, y1], 26, fill=bg, outline=INK, width=3)
        pc = pose_crop(FIN / f, 0.0, 0.62)
        s = min((x1 - x0 - 20) / pc.width, (y1 - y0 - 16) / pc.height)
        pc = pc.resize((max(1, int(pc.width * s)), max(1, int(pc.height * s))), Image.LANCZOS)
        mask = rounded_mask(x1 - x0 - 6, y1 - y0 - 6, 22)
        tile = Image.new("RGBA", (x1 - x0 - 6, y1 - y0 - 6), (0, 0, 0, 0))
        tile.paste(pc, ((tile.width - pc.width) // 2, tile.height - pc.height), pc)
        tile.putalpha(Image.fromarray(np.minimum(np.array(tile)[..., 3], np.array(mask))))
        im.paste(tile, (x0 + 3, y0 + 3), tile)
        d.rounded_rectangle([x0, y0, x1, y1], 26, outline=INK, width=3)
    p = OUT / "card-mnemonic_v01.png"
    PD.save(np.array(im), p)
    return {"file": str(p.relative_to(ROOT)), "poses": [t[0] for t in tiles]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c1", default=str(SRC / "a3_c002_9.0.png"))
    ap.add_argument("--c2", default=str(SRC / "a4_c012_6.0.png"))
    ap.add_argument("--c3", default=str(SRC / "a5_c006_6.0.png"))
    ap.add_argument("--cx", default="0.45,0.52,0.52")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cx = [float(v) for v in a.cx.split(",")]
    rec = {"cards": [make_card(1, a.c1, cx[0]), make_card(2, a.c2, cx[1]), make_card(3, a.c3, cx[2])], "mnemonic": make_mnemonic()}
    (ROOT / "review/G5/a6/cards.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps(rec, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
