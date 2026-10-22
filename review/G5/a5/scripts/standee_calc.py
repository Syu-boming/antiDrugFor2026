"""第五幕新姿勢的立牌參數：仿 app/src/stage/standee.ts 的腳底／頭頂自動偵測，算坐姿的 feet／headTop（座面 0.92）與手的位置；
並畫一張舞台比例預覽（review/G5/a5/checks/scale_preview.png）。"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "assets/final"
OUT = ROOT / "review/G5/a5/checks"


def auto(img):
    a = np.array(Image.open(FIN / f"{img}.png").convert("RGBA"))[..., 3] >= 128
    ys, xs = np.nonzero(a)
    bb = [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]
    low = a[max(0, bb[3] - 40):bb[3]]
    lx = np.nonzero(low.any(0))[0]
    feet = [(lx.min() + lx.max()) / 2, bb[3] - 4]
    H = bb[3] - bb[1]
    r0, r1 = int(bb[1] + 0.12 * H), int(bb[1] + 0.22 * H)
    yy, xx = np.nonzero(a[r0:r1])
    hx = xx.mean() if len(xx) else a.shape[1] / 2
    half = int(a.shape[1] * 0.06)
    top = min(np.nonzero(a[:, c])[0].min() for c in range(max(0, int(hx - half)), min(a.shape[1], int(hx + half))) if a[:, c].any())
    return a, bb, feet, top


def main():
    res = {}
    # 站姿：自動偵測（和引擎一樣）
    for key, img, h in (("xq_stand", "chr-xiaoqing_master_v04", 2.5), ("xy_stand", "chr-xiaoyu_master_v04", 2.42), ("chen_shoutr", "chr-chen_pose-shoutr_v01", 3.45),
                        ("chen_stand", "chr-chen_master_v01", 3.45), ("medic_a", "chr-medic-a_stand_v01", 3.4), ("medic_b", "chr-medic-b_stand_v01", 3.22)):
        a, bb, feet, top = auto(img)
        s = h / (feet[1] - top)
        res[key] = {"img": img, "feet": [round(float(feet[0]), 1), int(feet[1])], "top": int(top), "s": s}
    # 陳伯伯 shoutr 垂下那隻手（握拳）的位置：圖上約（92, 905）→ 身體座標
    c = res["chen_shoutr"]
    fist = (92, 905)
    res["chen_shoutr"]["fist_body"] = [round((fist[0] - c["feet"][0]) * c["s"], 3), round((c["feet"][1] - fist[1]) * c["s"], 3)]
    # 坐姿：頭部大小比（預覽目測和站姿母版頭部同大；頸部最窄列量法 1.12–1.16 會讓頭太小，不用）換算比例；座面列 → feet.y；虛擬 headTop
    sit = {"xq_sitb": ("chr-xiaoqing_pose-sitb_v01", 2.5, res["xq_stand"]["s"], 0.97, 880, 200),
           "xy_sitb": ("chr-xiaoyu_pose-sitb_v01", 2.42, res["xy_stand"]["s"], 0.99, 925, 235)}
    for key, (img, h, s_master, ratio, seat_row, hip_x) in sit.items():
        s = s_master / ratio
        fy = seat_row + 0.92 / s
        top = fy - h / s
        res[key] = {"img": img, "feet": [hip_x, round(fy, 1)], "headTop": round(top, 1), "s": s, "seat_row": seat_row}
    (OUT / "standee_calc.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))
    # 預覽：同一條地面線，世界 1 單位＝200 px
    PPU = 200
    items = [("chr-lin_master_v01", None, 3.42, 0.0), ("chr-lin_pose-sit_v01", ([195.0, 1512.8], -345.3), 3.42, 1.8),
             ("chr-xiaoqing_master_v04", None, 2.5, 3.6), (res["xq_sitb"]["img"], (res["xq_sitb"]["feet"], res["xq_sitb"]["headTop"]), 2.5, 5.0),
             ("chr-xiaoyu_master_v04", None, 2.42, 6.3), (res["xy_sitb"]["img"], (res["xy_sitb"]["feet"], res["xy_sitb"]["headTop"]), 2.42, 7.7),
             ("chr-chen_master_v01", None, 3.45, 9.4), ("chr-chen_pose-shoutr_v01", None, 3.45, 11.0),
             ("chr-medic-a_stand_v01", None, 3.4, 12.8), ("chr-medic-b_stand_v01", None, 3.22, 14.3)]
    W, Hh = int(15.5 * PPU), int(4.2 * PPU)
    can = Image.new("RGB", (W, Hh), (226, 220, 208))
    d = ImageDraw.Draw(can)
    g = Hh - 20
    d.line([(0, g), (W, g)], fill=(200, 0, 0), width=2)
    d.line([(0, g - 0.92 * PPU), (W, g - 0.92 * PPU)], fill=(0, 0, 200), width=1)
    for img, cfg, h, x in items:
        im = Image.open(FIN / f"{img}.png").convert("RGBA")
        if cfg is None:
            _, bb, feet, top = auto(img)
        else:
            feet, top = cfg
        s = h / (feet[1] - top)
        k = s * PPU
        im2 = im.resize((max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k))), Image.LANCZOS)
        px = int(x * PPU + 100 - feet[0] * k)
        py = int(g - feet[1] * k)
        can.paste(im2, (px, py), im2)
    can.save(OUT / "scale_preview.png")
    print(json.dumps(res, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
