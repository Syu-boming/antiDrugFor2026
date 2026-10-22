"""第五幕 119 電話圖示 v02：v01 的聽筒兩端畫成楔形，看起來像彎箭頭；改成經典話筒剪影（弧形握把＋兩端圓角耳承、話筒）。
輸出 assets/final/sets/a5_gate/a5-phone_v02.png（v01 刪除）。用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/phone_icon_v2.py
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

D = 260
TEAL = (74, 128, 128, 255)


def handset(B):
    """經典話筒剪影（自己畫的幾何，不取自任何字型或圖示庫）：圓心在右上角的四分之一粗圓弧當握把，
    兩端各接一塊往弧內側伸出的圓角方塊（耳承、話筒）。"""
    im = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = B / 1000
    cx, cy = 880 * k, 120 * k          # 弧心（右上）
    R, w = 640 * k, 150 * k           # 握把中線半徑、粗細
    d.arc([cx - R - w / 2, cy - R - w / 2, cx + R + w / 2, cy + R + w / 2], 95, 175, fill=TEAL, width=int(w))
    pad_w, pad_l, rr = 250 * k, 230 * k, 70 * k
    # 左上端（9 點鐘方向附近）：往右（弧內側）伸出的耳承
    ex, ey = cx - R, cy + 40 * k
    d.rounded_rectangle([ex - pad_w / 2 - 10 * k, ey - 40 * k, ex - pad_w / 2 - 10 * k + pad_l + 40 * k, ey - 40 * k + pad_w], int(rr), fill=TEAL)
    # 下端（6 點鐘方向附近）：往上（弧內側）伸出的話筒
    fx, fy = cx - 40 * k, cy + R
    d.rounded_rectangle([fx - pad_w + 40 * k, fy - pad_l - 30 * k + pad_w / 2, fx + 40 * k, fy + pad_w / 2 + 10 * k], int(rr), fill=TEAL)
    return im


def main():
    s = P.Sheet(D, D)
    s.ellipse(6, 6, D - 6, D - 6, (250, 244, 230, 255), line=3.0)
    s.ellipse(20, 20, D - 20, D - 20, (238, 226, 204, 255), line=1.4)
    B = D * s.ss
    hs = handset(B * 2)
    hs = hs.crop(hs.getbbox())
    side = int(B * 0.56)
    kk = side / max(hs.size)
    hs = hs.resize((int(hs.size[0] * kk), int(hs.size[1] * kk)), Image.LANCZOS)
    s.img.alpha_composite(hs, ((B - hs.size[0]) // 2, (B - hs.size[1]) // 2))
    s.d = ImageDraw.Draw(s.img)
    out = ROOT / "assets/final/sets/a5_gate/a5-phone_v02.png"
    P.save(s.finish(white_border=0), out)
    old = ROOT / "assets/final/sets/a5_gate/a5-phone_v01.png"
    if old.exists():
        old.unlink()
    print(out)


if __name__ == "__main__":
    main()
