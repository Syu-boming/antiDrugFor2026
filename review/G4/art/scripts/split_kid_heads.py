"""G4 美術：孩子姿勢圖拆成「頭」＋「身體」兩層（G2 問題 4：孩子要能轉頭、呼吸、眨眼，不是正面立牌）。

- 頭層：頭髮、臉、耳朵、髮夾＋頭部外圍的白色紙芯邊；樞紐在下巴下方的頸部中央。
- 身體層：原圖，頭部範圍改成「模糊過的底色」（看不到五官，避免轉頭時出現重影），
  並把頭部朝外（貼著透明背景）的 12 px 邊緣挖空，頭轉動時不會露出兩層白邊；頭與頸、肩的接縫保持不透明，不會露縫。
- 建議轉頭範圍 ±2.5°（髮尾位移 ≤10 px@原圖），超過請改用整張姿勢圖切換。
輸出 assets/final/chr-<角色>_pose-<姿勢>-head_v04.png、-body_v04.png、review/G4/art/kid_heads.json、review/G4/art/kid_heads_check.png
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "assets/final"
PAD = 6
KIDS = {
    "xiaoqing": dict(file="chr-xiaoqing_pose-reach-worried_v04.png",
                     chin=[(250, 286), (300, 296), (330, 306), (360, 326), (415, 343), (470, 346), (505, 337), (530, 332), (560, 420), (720, 430)],
                     pivot=(445, 352), hair_below_ok=lambda x, y: (x > 500) | (x < 300),
                     not_head=lambda x, y, skin, white: ((skin | white) & (x < 318)) | ((x < 262))),
    "xiaoyu": dict(file="chr-xiaoyu_pose-stepback-surprised_v04.png",
                   chin=[(150, 300), (185, 306), (230, 345), (270, 366), (330, 373), (380, 360), (405, 378), (445, 372), (475, 356), (560, 352)],
                   pivot=(330, 378), hair_below_ok=lambda x, y: (x > 400),
                   not_head=lambda x, y, skin, white: np.zeros_like(skin)),
}


def hsv(a):
    rgb = a[..., :3].astype(np.float32) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-6), mx


def split(name, k):
    a = np.array(Image.open(FIN / k["file"]).convert("RGBA"))
    H, W = a.shape[:2]
    fig = a[..., 3] > 128
    h, s, v = hsv(a)
    yy, xx = np.mgrid[:H, :W]
    ch = np.array(k["chin"], float)
    chin_y = np.interp(xx, ch[:, 0], ch[:, 1])
    above = yy < chin_y
    # 衣服、書包等顏色（不屬於頭）
    yellow = (h > 30) & (h < 58) & (s > 0.55) & (v > 0.55)
    teal = (h > 160) & (h < 210) & (s > 0.3)
    red = ((h < 22) | (h > 340)) & (s > 0.6) & (v > 0.3) & (v < 0.85)
    blue = (h > 200) & (h < 250) & (s > 0.25) & (v < 0.6)
    clothing = yellow | teal | red | blue
    star = (h > 30) & (h < 58) & (s > 0.55) & (yy < chin_y)   # 小晴的星星髮夾在頭上（黃色但屬於頭）
    hairish = (v < 0.48) & (s < 0.75) & ~teal & ~blue
    skin = (h > 8) & (h < 42) & (s > 0.15) & (s < 0.65) & (v > 0.68)
    white = (s < 0.12) & (v > 0.85)
    core = fig & above & (~clothing | star) & ~k["not_head"](xx, yy, skin, white)
    # 頭以下、兩側垂下的頭髮
    below_hair = fig & ~above & hairish & k["hair_below_ok"](xx, yy)
    cand = core | below_hair
    lab, n = ndimage.label(cand)
    py, px = int(k["pivot"][1]) - 30, int(k["pivot"][0])
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    keep = lab == (1 + int(np.argmax(sizes)))
    head = ndimage.binary_closing(keep, iterations=2)
    head = ndimage.binary_fill_holes(head) & fig
    # 頭部外圍的白色紙芯邊（貼著透明背景、離頭 ≤16 px）
    bg = ~fig
    d_bg = ndimage.distance_transform_edt(~bg)
    d_head = ndimage.distance_transform_edt(~head)
    border = fig & ~head & (d_head <= 16) & (d_bg <= 16)
    # 不把肩膀、身體的白邊算進來：只取頭部下巴線以上、或頭髮旁邊的白邊
    border &= above | (d_head <= 6)
    border &= ~k["not_head"](xx, yy, np.zeros_like(fig), np.zeros_like(fig)) if name == "xiaoqing" else border
    if name == "xiaoqing":
        border &= xx >= 262
    head_full = head | border
    # ---- 頭層
    ys, xs = np.nonzero(head_full)
    x0, y0 = max(xs.min() - PAD, 0), max(ys.min() - PAD, 0)
    x1, y1 = min(xs.max() + 1 + PAD, W), min(ys.max() + 1 + PAD, H)
    hl = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    sub = a[y0:y1, x0:x1].copy()
    m = head_full[y0:y1, x0:x1]
    hl[m] = sub[m]
    # 顏色外擴
    mm = hl[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~mm, return_indices=True)
    hl[~mm, :3] = hl[iy[~mm], ix[~mm], :3]
    # ---- 身體層
    body = a.copy()
    blur = np.stack([ndimage.gaussian_filter(a[..., c].astype(np.float32), 7) for c in range(3)], -1)
    under = head_full & (d_bg > 12)
    body[head_full & ~under, 3] = 0
    body[under, :3] = np.clip(blur[under], 0, 255).astype(np.uint8)
    # 頭與身體的接縫（頭內、離身體像素 ≤8 px）保持原色，避免轉頭時看到糊色
    d_bodypx = ndimage.distance_transform_edt(~(fig & ~head_full))
    seam = head_full & (d_bodypx <= 8)
    body[seam] = a[seam]
    mm = body[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~mm, return_indices=True)
    body[~mm, :3] = body[iy[~mm], ix[~mm], :3]
    stem = k["file"].replace("_v04.png", "")
    Image.fromarray(hl, "RGBA").save(FIN / f"{stem}-head_v04.png", optimize=True)
    Image.fromarray(body, "RGBA").save(FIN / f"{stem}-body_v04.png", optimize=True)
    # 轉頭檢查：±2.5° 合成與原圖差異
    def compose(deg):
        out = Image.fromarray(body, "RGBA")
        hd = Image.fromarray(hl, "RGBA")
        piv = (k["pivot"][0] - x0, k["pivot"][1] - y0)
        big = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        big.paste(hd, (x0, y0))
        big = big.rotate(deg, resample=Image.BICUBIC, center=k["pivot"])
        out.alpha_composite(big)
        return out
    # 0° 直接疊回（不經旋轉重取樣），以預乘色比較
    rest = Image.fromarray(body, "RGBA")
    rest.alpha_composite(Image.fromarray(hl, "RGBA"), (int(x0), int(y0)))
    c0 = np.array(rest).astype(np.float32)
    ao = a.astype(np.float32)
    diff0 = int((np.abs(c0[..., :3] * c0[..., 3:] / 255 - ao[..., :3] * ao[..., 3:] / 255).max(-1) > 8).sum())
    info = {"head_file": f"assets/final/{stem}-head_v04.png", "body_file": f"assets/final/{stem}-body_v04.png",
            "head_offset_px": [int(x0), int(y0)], "head_size": [int(x1 - x0), int(y1 - y0)],
            "pivot_px_full": list(k["pivot"]), "pivot_px_head": [k["pivot"][0] - int(x0), k["pivot"][1] - int(y0)],
            "turn_range_deg": [-2.5, 2.5], "rest_diff_px_vs_original": diff0,
            "note": "身體層與原圖同尺寸、同座標；頭層貼在 head_offset_px，繞 pivot 旋轉。0° 時兩層疊起來與原圖相同。"}
    return info, compose


def main():
    res = {}
    tiles = []
    for name, k in KIDS.items():
        info, compose = split(name, k)
        res[name] = info
        for deg in (-2.5, 0, 2.5):
            im = compose(deg)
            hx, hy = info["head_offset_px"]
            hw, hh = info["head_size"]
            box = (max(hx - 60, 0), max(hy - 20, 0), hx + hw + 60, hy + hh + 140)
            bgc = Image.new("RGBA", im.size, (150, 150, 146, 255))
            bgc.alpha_composite(im)
            t = bgc.crop(box)
            t = t.resize((int(t.width * 0.6), int(t.height * 0.6)), Image.LANCZOS)
            tiles.append((f"{name} {deg:+.1f}°", t))
    W = sum(t.width + 12 for _, t in tiles) + 12
    Hh = max(t.height for _, t in tiles) + 40
    S = Image.new("RGB", (W, Hh), (44, 42, 40))
    d = ImageDraw.Draw(S)
    x = 12
    for lab, t in tiles:
        S.paste(t.convert("RGB"), (x, 32))
        d.text((x, 8), lab, fill=(240, 220, 120))
        x += t.width + 12
    S.save(ROOT / "review/G4/art/kid_heads_check.png")
    (ROOT / "review/G4/art/kid_heads.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
