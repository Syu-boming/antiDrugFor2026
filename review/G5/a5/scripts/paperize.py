"""第五幕修正第 2 輪：把平塗景片／道具處理成「厚卡紙剪貼」的質感（b2r2 美術 G5：校門口景片平灰；救護車、導護旗沒有紙紋）。

做法（全部是確定性的影像處理，不加文字、不改造形、不改平均亮度）：
1. 放大（LANCZOS）：原圖每世界單位只有 110–170 px，近景會糊；放大後線條與紙紋才撐得住。
2. 紙片浮雕：以色塊為「一層一層貼上去的紙」，在每條色塊邊界上沿左上亮、右下暗（光從左上來），
   深色細線在右下方落一道 2–4 px 的淡投影（像上層紙片壓在下層上）；整體是零平均的明暗，不改平均亮度。
3. 紙纖維：G2 天空景片的高頻紙紋（paperdraw.paper_tex）＋隨機短纖維（淺／深）＋很淡的大塊斑駁。
4. 紙邊：外輪廓內側 3–5 px 一圈淺色紙芯（卡紙切口），右下輪廓再暗一點；道具可再加白色紙芯邊（同角色立牌）。
用法：from paperize import paperize；a = paperize(Image.open(...), scale=2, seed=1)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402


def _lum(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def fibers_layer(w, h, seed, density=1.0, k=1.0):
    """隨機短纖維：回傳加法層（−1..1 的亮度位移，單位＝0–255）"""
    rng = np.random.default_rng(seed)
    n = int(w * h / 700 * density)
    im = Image.new("L", (w, h), 128)
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y = rng.random() * w, rng.random() * h
        ln = (4 + rng.random() * 16) * k
        ang = rng.random() * np.pi
        dx, dy = np.cos(ang) * ln / 2, np.sin(ang) * ln / 2
        v = 128 + (rng.integers(10, 26) if rng.random() < 0.55 else -rng.integers(8, 20))
        d.line([(x - dx, y - dy), (x + dx, y + dy)], fill=int(v), width=1 if rng.random() < 0.7 else 2)
    a = (np.asarray(im, np.float32) - 128.0)
    return ndimage.gaussian_filter(a, 0.6)


def mottle(w, h, seed, amp=0.025, sigma=40):
    rng = np.random.default_rng(seed + 7)
    n = rng.standard_normal((h // 8 + 2, w // 8 + 2)).astype(np.float32)
    n = ndimage.zoom(n, 8, order=1)[:h, :w]
    n = ndimage.gaussian_filter(n, sigma / 8)
    n /= max(1e-6, np.abs(n).max())
    return 1.0 + amp * n


def paperize(img, scale=2.0, seed=1, relief=1.6, shadow=1.8, fiber=1.0, rim=1.0, white_border=0, max_side=3200, shadow_off=3.0):
    im = img.convert("RGBA")
    W0, H0 = im.size
    s = min(scale, max_side / max(W0, H0))
    W, H = int(round(W0 * s)), int(round(H0 * s))
    if (W, H) != (W0, H0):
        # 預乘 alpha 再縮放，避免透明邊出現黑邊
        a0 = np.asarray(im, np.float32)
        pm = a0.copy(); pm[..., :3] *= a0[..., 3:4] / 255.0
        big = np.asarray(Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), "RGBA").resize((W, H), Image.LANCZOS), np.float32)
        al = np.maximum(big[..., 3:4], 1e-3)
        big[..., :3] = np.where(big[..., 3:4] > 0.5, big[..., :3] * 255.0 / al, 0)
        a = big
    else:
        a = np.asarray(im, np.float32).copy()
    rgb = a[..., :3]
    alpha = a[..., 3]
    inside = alpha > 127
    px = s  # 每原圖像素放大的倍數（線寬、投影距離跟著放大）

    # ---- 紙片浮雕：色塊邊界的左上亮、右下暗（以平滑後的亮度當高度）
    L = _lum(rgb)
    Lm = np.where(inside, L, ndimage.grey_dilation(np.where(inside, L, 0), size=3))
    h1 = ndimage.gaussian_filter(Lm, 1.2 * px)
    gx = ndimage.sobel(h1, axis=1) / 8.0
    gy = ndimage.sobel(h1, axis=0) / 8.0
    emb = -(gx + gy) / np.sqrt(2)                      # 光從左上：高度往右下降＝亮
    emb = np.clip(emb / (3.0 + 0.0 * px), -1.0, 1.0)
    shade = 1.0 + 0.10 * relief * emb

    # ---- 深色細線的投影（右下 2–4 px）：上層紙片壓在下層上
    ink = np.clip((np.median(L[inside]) * 0.62 - L) / 50.0, 0, 1) if inside.any() else np.zeros_like(L)
    ink = ink * inside
    off = shadow_off * px
    sh = ndimage.shift(ndimage.gaussian_filter(ink, 1.6 * px), (off, off * 0.8), order=1, mode="constant")
    shade *= 1.0 - 0.14 * shadow * np.clip(sh - ink, 0, 1)

    # ---- 紙邊：外輪廓內側一圈淺色紙芯、右下輪廓暗一點
    din = ndimage.distance_transform_edt(inside)
    rimw = 2.6 * px
    rim_m = np.clip(1.0 - din / rimw, 0, 1) * inside
    a_s = ndimage.gaussian_filter(inside.astype(np.float32), 1.5 * px)
    agx = ndimage.sobel(a_s, axis=1); agy = ndimage.sobel(a_s, axis=0)
    dirv = np.clip((agx + agy) / (np.abs(agx) + np.abs(agy) + 1e-6), -1, 1)    # >0＝左上邊、<0＝右下邊
    shade *= 1.0 + rim * rim_m * (0.07 * np.clip(dirv, 0, 1) - 0.10 * np.clip(-dirv, 0, 1))

    # ---- 紙纖維、斑駁
    tex = P.paper_tex(W, H)
    tex = 1.0 + (tex - 1.0) * (0.9 * fiber)
    fl = fibers_layer(W, H, seed, density=1.0, k=max(1.0, px * 0.8)) * 0.55 * fiber
    mt = mottle(W, H, seed)

    out = rgb * (shade * tex * mt)[..., None] + fl[..., None]
    # 平均亮度不變（只在不透明區）
    if inside.any():
        k = _lum(rgb)[inside].mean() / max(1e-3, _lum(out)[inside].mean())
        out *= k
    a[..., :3] = np.clip(out, 0, 255)
    res = np.clip(a, 0, 255).astype(np.uint8)
    if white_border:
        res = add_white_border(res, int(round(white_border * px)))
    return res


def add_white_border(a, wb):
    """道具外圍白色紙芯邊＋內側深色細線（同 paperdraw.Sheet.finish）"""
    h, w = a.shape[:2]
    pad = wb + 6
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8)
    big[pad:pad + h, pad:pad + w] = a
    m2 = big[..., 3] >= 128
    dist = ndimage.distance_transform_edt(~m2)
    ring = (dist > 0) & (dist <= wb + 1.2)
    out = big.astype(np.float32)
    wc = np.array([250, 246, 238], np.float32) * P.paper_tex(big.shape[1], big.shape[0])[..., None]
    out[ring, :3] = wc[ring]
    aa = np.clip(wb + 1.2 - dist, 0, 1)
    out[..., 3] = np.where(m2, out[..., 3], aa * 255 * ring)
    dl = ndimage.distance_transform_edt(m2)
    line = m2 & (dl <= 2.2)
    out[line, :3] = out[line, :3] * 0.25 + np.array([70, 56, 46]) * 0.75
    return np.clip(out, 0, 255).astype(np.uint8)
