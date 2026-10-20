"""角色主色加深一階（只動指定色相、高彩度的區域；膚色、腮紅、白邊、其他衣物不動）。

為什麼：G2a 改進清單要求「角色主色比 S4 深一階、彩度略高」，讓投影模擬下主色對相鄰背景的明度對比 ≥3:1。
生成的小宇橘紅外套與 S4 幾乎同明度（量測見 review/G2/contrast.json 的備註），所以以程式只把外套的明度降一階。

用法：
  /opt/anaconda3/bin/python3 tools/deepen_color.py 輸入.png 輸出.png --hue 345:22 --min-sat 0.60 --value 0.82 --sat 1.06 \
      [--compare review/G2/xiaoyu_color_fix.png]
  --hue：色相範圍（度，可跨 0°），--min-sat：HSV 飽和度下限（膚色約 0.3–0.5，所以 0.6 以上才算外套），
  --value：明度倍率，--sat：飽和度倍率。遮罩邊緣做 2 px 羽化，避免色塊硬邊。
"""
import argparse
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rr = m & (mx == r)
    gg = m & (mx == g) & ~rr
    bb = m & ~rr & ~gg
    h[rr] = ((g - b)[rr] / d[rr]) % 6
    h[gg] = (b - r)[gg] / d[gg] + 2
    h[bb] = (r - g)[bb] / d[bb] + 4
    h = h * 60
    s = np.where(mx > 1e-6, d / (mx + 1e-9), 0)
    return h, s, mx


def hsv_to_rgb(h, s, v):
    c = v * s
    x = c * (1 - np.abs((h / 60) % 2 - 1))
    m = v - c
    z = np.zeros_like(h)
    k = (h // 60).astype(int) % 6
    r = np.choose(k, [c, x, z, z, x, c])
    g = np.choose(k, [x, c, c, x, z, z])
    b = np.choose(k, [z, z, x, c, c, x])
    return np.stack([r + m, g + m, b + m], -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--hue", default="345:22")
    ap.add_argument("--min-sat", type=float, default=0.60)
    ap.add_argument("--min-val", type=float, default=0.30)
    ap.add_argument("--value", type=float, default=0.82)
    ap.add_argument("--sat", type=float, default=1.06)
    ap.add_argument("--compare", default=None)
    args = ap.parse_args()
    im = Image.open(args.src).convert("RGBA")
    a = np.array(im).astype(np.float64)
    rgb = a[..., :3] / 255.0
    h, s, v = rgb_to_hsv(rgb)
    h0, h1 = (float(x) for x in args.hue.split(":"))
    in_hue = (h >= h0) | (h <= h1) if h0 > h1 else (h >= h0) & (h <= h1)
    mask = in_hue & (s >= args.min_sat) & (v >= args.min_val) & (a[..., 3] > 0)
    mask = ndimage.binary_opening(mask, iterations=1)
    soft = ndimage.gaussian_filter(mask.astype(np.float64), 2.0)
    v2 = v * (1 - soft * (1 - args.value))
    s2 = np.clip(s * (1 + soft * (args.sat - 1)), 0, 1)
    out = a.copy()
    out[..., :3] = np.clip(hsv_to_rgb(h, s2, v2) * 255, 0, 255)
    Image.fromarray(out.round().astype(np.uint8), "RGBA").save(args.dst)
    sel = mask
    before = np.median(a[..., :3][sel], 0)
    after = np.median(out[..., :3][sel], 0)
    print(json.dumps(dict(src=args.src, dst=args.dst, pixels=int(sel.sum()),
                          median_before=before.round().tolist(), median_after=after.round().tolist()), ensure_ascii=False))
    if args.compare:
        w, hh = im.size
        sheet = Image.new("RGB", (w * 3 + 40, hh + 20), (206, 202, 194))
        sheet.paste(im, (10, 10), im)
        res = Image.fromarray(out.round().astype(np.uint8), "RGBA")
        sheet.paste(res, (w + 20, 10), res)
        diff = (np.abs(out[..., :3] - a[..., :3]).max(-1) * 4).clip(0, 255).astype(np.uint8)
        sheet.paste(Image.fromarray(diff).convert("RGB"), (2 * w + 30, 10))
        ImageDraw.Draw(sheet).text((20, 14), "before / after / diff x4", fill=(20, 20, 20))
        sheet.save(args.compare)


if __name__ == "__main__":
    main()
