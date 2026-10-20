"""兒童主角主色「同色相加深」（G2 退路，主線決定 D-G2-06）。

用法：/opt/anaconda3/bin/python3 tools/recolor_garment.py
輸出：assets/generated/ 下的 *_v04.png（不覆寫 v02／v03），並印出加深前後的中位色。

做法：服裝區用 HSV 範圍選取（與 compose_stage 的 COSTUMES 相同），在 CIELAB 把 L* 等比縮放到目標中位值
（保留紙紋與皺褶的相對明暗），a*、b* 不動（色相角與彩度不變，只有明度變深，避免第 1 輪「變成磚紅」的灰濁感）。
選取邊緣用色相距離做羽化，避免硬邊。
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color as skc

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "assets/generated"

# (來源, 輸出, [(名稱, 色相範圍, 飽和度下限, 明度下限, 身高帶, 目標 L*)])
JOBS = [
    ("chr-xiaoyu_master_v02.png", "chr-xiaoyu_master_v04.png", [("橘紅外套", (345, 22), 0.55, 0.25, (0.15, 0.78), 39.0)]),
    ("chr-xiaoyu_pose-stepback-surprised_v03.png", "chr-xiaoyu_pose-stepback-surprised_v04.png",
     [("橘紅外套", (345, 22), 0.55, 0.25, (0.15, 0.78), 39.0)]),
    ("chr-xiaoqing_master_v02.png", "chr-xiaoqing_master_v04.png", [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, (0.0, 1.0), 37.0)]),
    ("chr-xiaoqing_pose-reach-worried_v03.png", "chr-xiaoqing_pose-reach-worried_v04.png",
     [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, (0.0, 1.0), 37.0)]),
]


def hsv(rgb):
    r, g, b = [rgb[..., i] / 255.0 for i in range(3)]
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0)
    return h, s, mx


def hue_weight(h, h0, h1, soft=8.0):
    """在範圍內＝1，範圍外依色相距離在 soft 度內線性降到 0。"""
    if h0 > h1:
        inside = (h >= h0) | (h <= h1)
        dist = np.minimum(np.minimum(np.abs(h - h0), 360 - np.abs(h - h0)), np.minimum(np.abs(h - h1), 360 - np.abs(h - h1)))
    else:
        inside = (h >= h0) & (h <= h1)
        dist = np.minimum(np.abs(h - h0), np.abs(h - h1))
    return np.where(inside, 1.0, np.clip(1 - dist / soft, 0, 1))


def recolor(src, dst, specs):
    im = np.array(Image.open(GEN / src).convert("RGBA")).astype(np.float32)
    rgb, a = im[..., :3], im[..., 3]
    h, s, v = hsv(rgb)
    lab = skc.rgb2lab(rgb / 255.0)
    ys = np.nonzero(a.max(1) > 0)[0]
    top, bot = ys.min(), ys.max()
    yy = np.arange(im.shape[0])[:, None]
    report = []
    for name, (h0, h1), s0, v0, band, target in specs:
        w = hue_weight(h, h0, h1) * np.clip((s - s0) / 0.08 + 1, 0, 1) * np.clip((v - v0) / 0.06 + 1, 0, 1)
        w *= (a > 200) & (yy >= top + band[0] * (bot - top)) & (yy <= top + band[1] * (bot - top))
        core = ndimage.binary_opening(w > 0.5, iterations=1)
        # 只保留大的連通區（服裝本體），去掉零星同色像素（例如腮紅、髮夾）
        lb, n = ndimage.label(core)
        if n:
            sizes = ndimage.sum(core, lb, range(1, n + 1))
            keep = np.isin(lb, 1 + np.nonzero(sizes >= 0.02 * sizes.max())[0])
        else:
            keep = core
        region = ndimage.binary_dilation(keep, iterations=2)
        w = np.where(region, w, 0)
        w = ndimage.gaussian_filter(w, 0.6) * region
        L0 = float(np.median(lab[..., 0][keep]))
        k = target / L0
        new = lab.copy()
        new[..., 0] = lab[..., 0] * k
        out_rgb = skc.lab2rgb(new) * 255.0
        rgb = rgb * (1 - w[..., None]) + out_rgb * w[..., None]
        before = np.median(im[..., :3][keep], 0)
        after = np.median(rgb[keep], 0)
        report.append((name, int(keep.sum()), round(L0, 1), target, "#%02X%02X%02X" % tuple(int(round(c)) for c in before),
                       "#%02X%02X%02X" % tuple(int(round(c)) for c in after)))
        lab = skc.rgb2lab(np.clip(rgb, 0, 255) / 255.0)
    out = np.dstack([np.clip(rgb, 0, 255), a]).round().astype(np.uint8)
    Image.fromarray(out, "RGBA").save(GEN / dst)
    return report


def main():
    for src, dst, specs in JOBS:
        for name, px, L0, tgt, b, a_ in recolor(src, dst, specs):
            print(f"{dst}: {name} 像素 {px}，L* {L0} → {tgt}，中位色 {b} → {a_}")


if __name__ == "__main__":
    main()
