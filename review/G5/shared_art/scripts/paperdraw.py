"""G5 共用美術：程式繪製的厚卡紙景片／道具小工具（image_gen 額度用完時的退路）。

- 平塗色塊＋紙纖維紋理：紋理取自 G2 正式景片 bg-square-sky_v03 的高頻亮度（同一種紙紋），乘在色塊上。
- 線條：暖深灰細線（#4E3E33），和角色、G2 景片同色系；不畫陰影、不畫方向光。
- 道具（角色會碰到的獨立紙片）外加一圈白色紙芯邊（同角色立牌）；景片不加白邊。
- 圖裡不放任何文字、數字、標誌。
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
INK = (78, 62, 51, 255)
_TEX = None


def paper_tex(w, h):
    """紙紋乘數（約 0.94–1.06）；以 G2 天空景片的高頻亮度鏡射鋪滿。"""
    global _TEX
    if _TEX is None:
        sky = np.array(Image.open(ROOT / "assets/generated/bg-square-sky_v03.png").convert("L")).astype(np.float32)
        sky = sky[720:1010]                       # 地平線附近沒有雲的那一段（只要紙纖維）
        hp = sky - ndimage.gaussian_filter(sky, 2.5)
        _TEX = np.clip(hp / 255.0 * 1.8, -0.06, 0.06)
    t = _TEX
    th, tw = t.shape
    reps_y, reps_x = h // th + 2, w // tw + 2
    row = np.concatenate([t if i % 2 == 0 else t[:, ::-1] for i in range(reps_x)], 1)
    full = np.concatenate([row if j % 2 == 0 else row[::-1] for j in range(reps_y)], 0)
    return 1.0 + full[:h, :w]


class Sheet:
    def __init__(self, w, h, ss=2):
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def S(self, pts):
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def rect(self, x0, y0, x1, y1, fill, line=2.0, r=0):
        box = [x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss]
        if r:
            self.d.rounded_rectangle(box, r * self.ss, fill=fill, outline=INK if line else None, width=int(line * self.ss) if line else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=INK if line else None, width=int(line * self.ss) if line else 0)

    def poly(self, pts, fill, line=2.0):
        self.d.polygon(self.S(pts), fill=fill, outline=None)
        if line:
            p = self.S(pts)
            self.d.line(p + [p[0]], fill=INK, width=int(line * self.ss), joint="curve")

    def ellipse(self, x0, y0, x1, y1, fill, line=2.0):
        self.d.ellipse([x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss], fill=fill, outline=INK if line else None,
                       width=int(line * self.ss) if line else 0)

    def line(self, pts, w=2.0, color=INK):
        self.d.line(self.S(pts), fill=color, width=max(1, int(w * self.ss)), joint="curve")

    def hole(self, x0, y0, x1, y1, r=0):
        """挖成透明（例如警衛室玻璃）。"""
        m = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss], r * self.ss, fill=255)
        a = np.array(self.img)
        a[np.array(m) > 0, 3] = 0
        self.img = Image.fromarray(a, "RGBA")
        self.d = ImageDraw.Draw(self.img)

    def finish(self, white_border=0, edge_dark=0.0, seed=0):
        im = self.img.resize((self.w, self.h), Image.LANCZOS)
        a = np.array(im).astype(np.float32)
        tex = paper_tex(self.w, self.h)
        a[..., :3] *= tex[..., None]
        if edge_dark:
            m = a[..., 3] > 128
            din = ndimage.distance_transform_edt(m)
            k = np.clip(1 - din / 5.0, 0, 1) * edge_dark
            a[..., :3] *= (1 - k[..., None])
        a = np.clip(a, 0, 255).astype(np.uint8)
        if white_border:
            m = a[..., 3] >= 128
            pad = white_border + 6
            big = np.zeros((self.h + 2 * pad, self.w + 2 * pad, 4), np.uint8)
            big[pad:pad + self.h, pad:pad + self.w] = a
            m2 = big[..., 3] >= 128
            dist = ndimage.distance_transform_edt(~m2)
            core = (dist > 0) & (dist <= white_border)
            ring = (dist > 0) & (dist <= white_border + 1.2)
            out = big.copy().astype(np.float32)
            wc = np.array([250, 246, 238], np.float32) * paper_tex(big.shape[1], big.shape[0])[..., None]
            out[ring, :3] = wc[ring]
            aa = np.clip(white_border + 1.2 - dist, 0, 1)
            out[..., 3] = np.where(m2, out[..., 3], aa * 255 * ring)
            # 白邊內側一圈深色細線（同角色立牌）
            dl = ndimage.distance_transform_edt(m2)
            line = m2 & (dl <= 2.2)
            out[line, :3] = out[line, :3] * 0.25 + np.array([70, 56, 46]) * 0.75
            a = np.clip(out, 0, 255).astype(np.uint8)
        return a


def save(a, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    m = a[..., 3] > 0
    if m.any() and not m.all():
        _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
        a = a.copy()
        a[~m, :3] = a[iy[~m], ix[~m], :3]
    Image.fromarray(a, "RGBA").save(path, optimize=True)
    return path
