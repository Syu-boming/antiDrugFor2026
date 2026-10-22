"""第六幕代理：程式繪製的景片（Pillow＋G2 同款紙紋；圖裡沒有任何文字、數字、標誌）。

用法：/opt/anaconda3/bin/python3 review/G5/a6/scripts/build_a6_art.py
輸出：
- assets/final/sets/a6_square_night/sky_v01.png     紙燈節夜空（靛藍→暖紫→地平線燈光暖色；剪紙月亮、紙星星，全部固定不發光）
- assets/final/sets/a6_square_night/rack_v01.png    燈籠架（竹竿、橫樑、四盞圓燈籠）
- assets/final/sets/a6_window/tree-{autumn,winter,spring,summer}_v01.png   窗外的樹四季（取 sets/square/set-square_tree-a 重新上色；冬天＝去葉＋程式枝條）
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as PD  # noqa: E402

FIN = ROOT / "assets/final/sets"
INK = PD.INK


def hsv_arr(rgb):
    r, g, b = [rgb[..., i] / 255.0 for i in range(3)]
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0)
    return h, s, mx


def hsv_to_rgb(h, s, v):
    h = (h % 360) / 60.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1) * 255


def star(cx, cy, r, rot=0.0):
    pts = []
    for k in range(10):
        a = rot - math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def night_sky():
    W, H = 2048, 1024
    y = np.linspace(0, 1, H)[:, None]
    stops = [(0.0, (40, 46, 92)), (0.45, (66, 64, 118)), (0.72, (120, 96, 140)), (0.88, (176, 126, 128)), (1.0, (214, 160, 128))]
    col = np.zeros((H, 1, 3), np.float32)
    for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
        m = (y >= y0) & (y <= y1)
        u = np.clip((y - y0) / (y1 - y0), 0, 1)
        col = np.where(m[..., None], np.array(c0) + (np.array(c1) - np.array(c0)) * u[..., None], col)
    img = np.repeat(col, W, 1)
    sh = PD.Sheet(W, H, ss=1)
    sh.img = Image.fromarray(np.dstack([img.astype(np.uint8), np.full((H, W), 255, np.uint8)]), "RGBA")
    sh.d = ImageDraw.Draw(sh.img)
    # 幾片剪紙雲（比天空略亮的暗紫，平塗＋細線）
    rng = np.random.default_rng(61)
    for cx, cy, s in [(330, 300, 1.0), (1180, 210, 1.2), (1700, 420, 0.9), (760, 520, 0.8)]:
        for k in range(5):
            r = (55 + 30 * rng.random()) * s
            ox = (k - 2) * 62 * s
            oy = -abs(k - 2) * -10 * s - (18 * s if k in (1, 3) else 0)
            sh.d.ellipse([cx + ox - r, cy + oy - r * 0.62, cx + ox + r, cy + oy + r * 0.62], fill=(92, 88, 140, 255))
    # 剪紙月亮（固定，不發光）
    sh.ellipse(1530, 120, 1690, 280, (246, 232, 196, 255), line=3)
    sh.ellipse(1585, 170, 1612, 196, (232, 214, 176, 255), line=0)
    sh.ellipse(1630, 214, 1648, 232, (232, 214, 176, 255), line=0)
    # 紙星星
    for i in range(26):
        x, yy = rng.uniform(40, W - 40), rng.uniform(30, H * 0.55)
        if 1490 < x < 1730 and yy < 320:
            continue
        r = rng.uniform(9, 17)
        sh.poly(star(x, yy, r, rng.uniform(0, 1)), (243, 226, 168, 255), line=1.2)
    return sh.finish()


def lantern(sh, cx, cy, r, color, rib=(150, 96, 60, 255)):
    sh.line([(cx, cy - r * 1.6), (cx, cy - r * 0.95)], w=2.2)
    sh.rect(cx - r * 0.32, cy - r * 1.02, cx + r * 0.32, cy - r * 0.86, (120, 82, 50, 255), line=1.5)
    sh.ellipse(cx - r, cy - r * 0.9, cx + r, cy + r * 0.9, color, line=2.2)
    for k in (-0.55, 0.0, 0.55):
        w = r * (1 - abs(k)) * 0.0 + r * math.sqrt(max(0, 1 - k * k))
        sh.d.arc([(cx - w) * sh.ss, (cy - r * 0.9) * sh.ss, (cx + w) * sh.ss, (cy + r * 0.9) * sh.ss], 0, 360, fill=rib, width=int(1.6 * sh.ss))
    sh.rect(cx - r * 0.32, cy + r * 0.86, cx + r * 0.32, cy + r * 1.02, (120, 82, 50, 255), line=1.5)
    sh.line([(cx, cy + r * 1.02), (cx, cy + r * 1.35)], w=2.0, color=(196, 92, 70, 255))


def rack():
    W, H = 1100, 860
    sh = PD.Sheet(W, H, ss=2)
    bam, node = (176, 132, 78, 255), (138, 98, 56, 255)
    for x0 in (40, W - 40 - 26):
        sh.rect(x0, 60, x0 + 26, H - 4, bam, line=2)
        for y in range(140, H - 20, 150):
            sh.rect(x0 - 3, y, x0 + 29, y + 8, node, line=1.2)
    sh.rect(10, 52, W - 10, 80, bam, line=2)
    for x in range(120, W - 60, 150):
        sh.rect(x, 52, x + 8, 80, node, line=0)
    for cx, r, c in [(240, 62, (246, 196, 140, 255)), (440, 54, (244, 216, 160, 255)), (640, 64, (238, 170, 120, 255)), (850, 56, (246, 206, 150, 255))]:
        lantern(sh, cx, 80 + r * 1.6 + 30, r, c)
    return sh.finish()


def season_trees():
    src = np.array(Image.open(FIN / "square/set-square_tree-a_v01.png").convert("RGBA")).astype(np.float32)
    rgb, al = src[..., :3], src[..., 3]
    h, s, v = hsv_arr(rgb)
    leaf = (al > 0) & (h > 48) & (h < 170) & (s > 0.18)
    leaf = ndimage.binary_closing(leaf, iterations=2) & (al > 0)
    trunk = (al > 0) & ~leaf
    H, W = al.shape
    out = {}
    # 夏：原圖、綠色略加深加飽和
    a = src.copy()
    hs = h.copy(); ss = np.clip(s * 1.08, 0, 1); vs = v * 0.95
    a[leaf, :3] = hsv_to_rgb(hs, ss, vs)[leaf]
    out["summer"] = a
    # 秋：葉子轉成橘黃（亮葉→金黃、暗葉→橘），保留明暗紋理
    a = src.copy()
    hn = np.where(v > 0.62, 42.0, 26.0) + (h - 95) * 0.12
    a[leaf, :3] = hsv_to_rgb(hn, np.clip(s * 1.25 + 0.15, 0, 0.85), np.clip(v * 1.05, 0, 1))[leaf]
    out["autumn"] = a
    # 春：新芽淺綠、葉量減少（隨機拿掉約一半的葉團）
    a = src.copy()
    lab, n = ndimage.label(ndimage.binary_erosion(leaf, iterations=3))
    rng = np.random.default_rng(7)
    keep_ids = [i for i in range(1, n + 1) if rng.random() < 0.55]
    keep = ndimage.binary_dilation(np.isin(lab, keep_ids), iterations=3) & leaf
    a[leaf & ~keep, 3] = 0
    a[keep, :3] = hsv_to_rgb(np.full_like(h, 88.0) + (h - 95) * 0.1, np.clip(s * 0.75, 0, 0.6), np.clip(v * 1.12 + 0.05, 0, 1))[keep]
    out["spring"] = a
    # 冬：去掉葉子＋程式畫的光禿枝條（暖褐，和樹幹同色）
    a = src.copy()
    a[leaf, 3] = 0
    tr = trunk & (al > 128)
    ys, xs = np.nonzero(tr)
    sh = PD.Sheet(W, H, ss=2)
    tcol = tuple(int(c) for c in np.median(rgb[tr & (np.arange(H)[:, None] > H * 0.7)], 0)) + (255,)
    rng = np.random.default_rng(11)

    def branch(x, y, ang, length, width, depth):
        if depth == 0 or length < 18:
            return
        x2, y2 = x + length * math.cos(ang), y - length * math.sin(ang)
        sh.d.line([(x * 2, y * 2), (x2 * 2, y2 * 2)], fill=tcol, width=max(2, int(width * 2)), joint="curve")
        for da in (-0.42 - 0.2 * rng.random(), 0.38 + 0.2 * rng.random()):
            branch(x2, y2, ang + da, length * (0.66 + 0.1 * rng.random()), width * 0.66, depth - 1)
    # 樹幹頂端（不透明樹幹的最上方幾個點）往上分枝
    top_rows = sorted(set(ys))[:1]
    ytop = int(np.percentile(ys, 2))
    cx = float(np.median(xs[ys < ytop + 40])) if (ys < ytop + 40).any() else W / 2
    for ang, L0, w0 in [(1.57, 150, 16), (2.25, 170, 14), (0.85, 165, 14), (2.7, 120, 10), (0.4, 120, 10)]:
        branch(cx, ytop + 30, ang, L0, w0, 5)
    br = np.array(sh.img.resize((W, H), Image.LANCZOS)).astype(np.float32)
    m = br[..., 3] > 0
    a[m & (a[..., 3] < br[..., 3]), :] = br[m & (a[..., 3] < br[..., 3]), :]
    # 枝條暖深灰細邊
    edge = ndimage.binary_dilation(br[..., 3] > 128, iterations=2) & ~(br[..., 3] > 128) & (a[..., 3] < 10)
    a[edge, :3] = np.array(INK[:3]); a[edge, 3] = 255
    tex = PD.paper_tex(W, H)
    a[..., :3] = np.clip(a[..., :3] * np.where(m[..., None], tex[..., None], 1.0), 0, 255)
    out["winter"] = a
    for k, arr in out.items():
        PD.save(np.clip(arr, 0, 255).astype(np.uint8), FIN / f"a6_window/tree-{k}_v01.png")


def main():
    PD.save(night_sky(), FIN / "a6_square_night/sky_v01.png")
    PD.save(rack(), FIN / "a6_square_night/rack_v01.png")
    season_trees()
    print("ok")


if __name__ == "__main__":
    main()
