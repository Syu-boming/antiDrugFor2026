"""移除母版裡烘焙的方向性光影（G2 第 1 輪意見第 4 條；v1.2 第 14.1 節「生成素材一律不畫方向性打光」）。

做法：每個服裝區塊（依色相／飽和度／明度與列範圍選取）在 CIELAB 空間估計明暗場
（排除深色線條與淺色縫線後做中位數濾波，能保留卡通式硬邊暗面的邊界），再減去「明暗場 − 區塊中位數」。
結果：大片暗面、斜向陰影、褶痕暗帶被拉平；紙纖維（1–4 px）、縫線、輪廓線、口袋等細節原樣保留；
區塊中位數（固有色）不變，所以「主色」的 HEX 與明度值不因此改變。臉、手、頭髮、鞋不處理。

用法：
  /opt/anaconda3/bin/python3 tools/flatten_shading.py 輸入.png 輸出.png --preset ale \
      [--compare review/G2/ale_flatten_v02.png] [--report review/G2/flatten_ale_v02.json]
preset 定義在下方 PRESETS（座標為該母版的像素列）。
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)

# 區塊：名稱, 色相範圍(度), 飽和度範圍, 明度範圍(HSV V), 列範圍, 明暗場半徑 r（中位數濾波 2r+1 px）
PRESETS = {
    "ale": [  # chr-ale_master_v01.png（1024×1656，6.15 頭身）
        ("深藍圍裙", (195, 255), (0.18, 1.0), (0.10, 0.62), (330, 1040), 9),
        ("橄欖褐褲管", (25, 62), (0.28, 1.0), (0.10, 0.58), (1040, 1442), 9),
        ("褲管反摺", (25, 62), (0.20, 1.0), (0.18, 0.75), (1442, 1515), 6),
        ("米色襯衫", (14, 50), (0.04, 0.46), (0.55, 1.0), (300, 1000), 9),
    ],
    "xiaoqing": [  # master_xiaoqing.png（1024×1536，4.45 頭身）
        ("湖水綠吊帶褲", (160, 205), (0.28, 1.0), (0.12, 0.49), (420, 1262), 6),
        ("吊帶褲反摺", (160, 205), (0.15, 1.0), (0.49, 0.90), (1160, 1262), 6),
        ("芥末黃上衣", (32, 56), (0.55, 1.0), (0.55, 1.0), (420, 720), 9),
    ],
    "xiaoyu": [  # master_xiaoyu_propfix.png（1024×1496，4.45 頭身，外套為原生成色）；下巴 y=368，臉與脖子不處理
        ("橘紅外套", (345, 22), (0.62, 1.0), (0.28, 1.0), (372, 760), 9),
        ("卡其短褲", (22, 46), (0.28, 0.75), (0.40, 0.88), (760, 935), 9),
        ("短褲反摺", (18, 46), (0.25, 0.80), (0.35, 0.90), (935, 995), 6),
        ("腿部（膚色）", (8, 40), (0.15, 0.55), (0.62, 1.0), (995, 1190), 9),
    ],
}


def srgb_to_lab(rgb):
    a = rgb / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    A = 500 * (f[..., 0] - f[..., 1])
    B = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, A, B], -1)


def lab_to_srgb(lab):
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116
    fx = fy + A / 500
    fz = fy - B / 200
    def finv(t):
        return np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))
    xyz = np.stack([finv(fx), finv(fy), finv(fz)], -1) * np.array([0.95047, 1.0, 1.08883])
    m = np.array([[3.2404542, -1.5371385, -0.4985314],
                  [-0.9692660, 1.8760108, 0.0415560],
                  [0.0556434, -0.2040259, 1.0572252]])
    lin = np.clip(xyz @ m.T, 0, 1)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return np.clip(srgb * 255, 0, 255)


def hsv(rgb):
    a = rgb / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 1e-6, (mx - mn) / (mx + 1e-9), 0)
    return h, s, mx


BORDER_PX = 11.5  # 白色紙芯邊寬（proportion_grid 量到 9–11 px）：這一圈永遠不處理


def edge_dist(alpha):
    return ndimage.distance_transform_edt(alpha > 128)


def region_mask(rgb, alpha, spec, dist):
    name, (h0, h1), (s0, s1), (v0, v1), (y0, y1), _ = spec
    h, s, v = hsv(rgb)
    hue_ok = ((h >= h0) | (h <= h1)) if h0 > h1 else ((h >= h0) & (h <= h1))
    m = hue_ok & (s >= s0) & (s <= s1) & (v >= v0) & (v <= v1) & (alpha > 200) & (dist > BORDER_PX + 3)
    rows = np.zeros_like(m)
    rows[y0:y1] = True
    m &= rows
    m = ndimage.binary_opening(m, iterations=1)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= 400)[0])
        m = keep
    return m


def flatten(rgba, specs):
    arr = rgba.astype(np.float64)
    rgb, alpha = arr[..., :3], arr[..., 3]
    lab = srgb_to_lab(rgb)
    out = lab.copy()
    report, masks = [], []
    owner = np.full(alpha.shape, -1)
    best = np.full(alpha.shape, np.inf)
    deltas = []
    dist_edge = edge_dist(alpha)
    for k, spec in enumerate(specs):
        m = region_mask(rgb, alpha, spec, dist_edge)
        sigma = spec[5]
        # 估計用的像素：排除深色線條與淺色縫線（相對局部中位數 ±9 L*）
        ys, xs = np.nonzero(m)
        y0, y1 = max(ys.min() - 20, 0), min(ys.max() + 21, m.shape[0])
        x0, x1 = max(xs.min() - 20, 0), min(xs.max() + 21, m.shape[1])
        mc = m[y0:y1, x0:x1]
        labc = lab[y0:y1, x0:x1]
        # 區塊外的像素以最近的區塊像素填滿，避免中位數被鄰色拉走
        _, (iy, ix) = ndimage.distance_transform_edt(~mc, return_indices=True)
        filled = labc[iy, ix]
        med_local = ndimage.median_filter(filled[..., 0], size=9)
        est = mc & (labc[..., 0] > med_local - 9) & (labc[..., 0] < med_local + 9)
        _, (iy2, ix2) = ndimage.distance_transform_edt(~est, return_indices=True)
        filled2 = labc[iy2, ix2]
        # 明暗場：中位數濾波（size＝2·sigma+1）保留色塊邊界（卡通式硬邊暗面也能整塊拉平），
        # 小於約 sigma 的細節（紙纖維、縫線、輪廓線）不進入明暗場，所以會原樣保留
        size = 2 * sigma + 1
        lowc = np.stack([ndimage.gaussian_filter(ndimage.median_filter(filled2[..., c], size=size), 1.2)
                         for c in range(3)], -1)
        low = np.zeros_like(lab)
        low[y0:y1, x0:x1] = lowc
        estf = np.zeros_like(m)
        estf[y0:y1, x0:x1] = est
        est = estf
        w = ndimage.gaussian_filter(m.astype(np.float64), 2.0)
        ref = np.median(lab[est], 0)
        delta = low - ref
        # 套用範圍：區塊本身＋往外 3 px（區塊內的縫線、折線一起平移，保留相對明暗）
        apply = ndimage.binary_closing(m, iterations=3)
        apply = ndimage.binary_dilation(apply, iterations=3) & (alpha > 200) & (dist_edge > BORDER_PX)
        dist = ndimage.distance_transform_edt(~m)
        take = apply & (dist < best)
        best = np.where(take, dist, best)
        owner = np.where(take, k, owner)
        deltas.append(np.where(apply[..., None] & (w[..., None] > 0.05), delta, 0))
        masks.append(m)
        before = np.median(lab[m], 0)
        _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
        low_b = ndimage.median_filter(lab[..., 0][iy, ix], size=2 * sigma + 1)
        Lspread_before = float(np.percentile(low_b[m], 95) - np.percentile(low_b[m], 5))
        report.append(dict(region=spec[0], pixels=int(m.sum()), sigma=sigma,
                           lab_median_before=[round(float(x), 2) for x in before],
                           lowfreq_L_spread_p5_p95_before=round(Lspread_before, 2)))
    for k in range(len(specs)):
        sel = owner == k
        out[sel] = lab[sel] - deltas[k][sel]
    # 羽化：在套用範圍邊界 2 px 內和原圖混合，避免硬邊
    any_apply = owner >= 0
    soft = ndimage.gaussian_filter(any_apply.astype(np.float64), 1.0)
    soft = np.where(any_apply, np.maximum(soft, 0.5), 0) * any_apply
    res = lab * (1 - soft[..., None]) + out * soft[..., None]
    rgb2 = lab_to_srgb(res)
    new = arr.copy()
    new[..., :3] = rgb2
    lab2 = srgb_to_lab(rgb2)
    for k, (spec, m) in enumerate(zip(specs, masks)):
        _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
        low2 = ndimage.median_filter(lab2[..., 0][iy, ix], size=2 * spec[5] + 1)
        after = np.median(lab2[m], 0)
        b = np.array(report[k]["lab_median_before"])
        report[k].update(lab_median_after=[round(float(x), 2) for x in after],
                         median_deltaE76=round(float(np.linalg.norm(after - b)), 2),
                         lowfreq_L_spread_p5_p95_after=round(float(np.percentile(low2[m], 95) - np.percentile(low2[m], 5)), 2),
                         hex_median_before="#%02X%02X%02X" % tuple(np.median(rgb[m], 0).round().astype(int)),
                         hex_median_after="#%02X%02X%02X" % tuple(np.median(rgb2[m], 0).round().astype(int)))
    return np.clip(new.round(), 0, 255).astype(np.uint8), report, masks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--preset", required=True, choices=sorted(PRESETS))
    ap.add_argument("--compare", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--alpha-floor", type=int, default=0,
                    help="把 alpha 低於此值的外圍淡霧清成全透明（生成圖常見的 alpha<24 光暈）")
    args = ap.parse_args()
    im = Image.open(args.src).convert("RGBA")
    arr = np.array(im)
    if args.alpha_floor:
        arr[..., 3] = np.where(arr[..., 3] < args.alpha_floor, 0, arr[..., 3])
        im = Image.fromarray(arr, "RGBA")
    new, report, masks = flatten(arr, PRESETS[args.preset])
    Image.fromarray(new, "RGBA").save(args.dst)
    info = dict(src=args.src, dst=args.dst, preset=args.preset, alpha_floor=args.alpha_floor, method="CIELAB 明暗場（排除線條後中位數濾波）減去區塊中位數", regions=report)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    if args.report:
        Path(args.report).write_text(json.dumps(info, ensure_ascii=False, indent=2))
    if args.compare:
        w, h = im.size
        bg = (206, 202, 194)
        sheet = Image.new("RGB", (w * 3 + 40, h + 70), bg)
        sheet.paste(im, (10, 60), im)
        res = Image.fromarray(new, "RGBA")
        sheet.paste(res, (w + 20, 60), res)
        diff = np.abs(new[..., :3].astype(int) - arr[..., :3].astype(int)).max(-1)
        dv = np.clip(diff * 4, 0, 255).astype(np.uint8)
        dimg = Image.fromarray(dv).convert("RGB")
        ov = np.array(dimg)
        palette = [(255, 80, 80), (80, 200, 255), (255, 220, 60), (120, 255, 120)]
        for k, m in enumerate(masks):
            edge = m & ~ndimage.binary_erosion(m, iterations=2)
            ov[edge] = palette[k % 4]
        sheet.paste(Image.fromarray(ov), (2 * w + 30, 60))
        d = ImageDraw.Draw(sheet)
        try:
            f = ImageFont.truetype(FONT[0], 28, index=FONT[1])
        except OSError:
            f = ImageFont.load_default()
        d.text((14, 14), "原圖", font=f, fill=(20, 20, 20))
        d.text((w + 24, 14), "移除烘焙光影後（區塊中位數不變）", font=f, fill=(20, 20, 20))
        d.text((2 * w + 34, 14), "差異 ×4（彩色框＝處理區塊）", font=f, fill=(20, 20, 20))
        sheet.save(args.compare)


if __name__ == "__main__":
    main()
