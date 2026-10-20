"""G4 美術：程式產生的無字紙材貼圖（地板、布幕、署名卡底紙）。圖裡沒有任何文字；署名「許博明老師製作」由劇場程式用字型排在底紙上。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/make_textures.py
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "assets/final"
rng = np.random.default_rng(20261021)


def wrap_noise(h, w, sigma, seed):
    r = np.random.default_rng(seed).standard_normal((h, w))
    n = ndimage.gaussian_filter(r, sigma, mode="wrap")
    return n / (n.std() + 1e-6)


def fibers(h, w, n, seed, length=(20, 70), alpha=0.06, vertical_bias=0.0):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for _ in range(n):
        x, y = r.uniform(0, w), r.uniform(0, h)
        ang = r.uniform(0, np.pi) if vertical_bias == 0 else np.pi / 2 + r.normal(0, 0.25)
        L = r.uniform(*length)
        for t in np.linspace(0, L, int(L)):
            xx, yy = int(x + np.cos(ang) * t) % w, int(y + np.sin(ang) * t) % h
            out[yy, xx] += 1
    return ndimage.gaussian_filter(out, 0.6, mode="wrap") * alpha * 8


# 1) 地板：淺暖木板（沿 x 方向的長木板，接縫是淡棕細線），四方連續
H, W = 512, 1024
base = np.array([226, 206, 172], np.float32)
img = np.ones((H, W, 3), np.float32) * base
plank_h = 64
for i in range(H // plank_h):
    shade = rng.uniform(-7, 7)
    img[i * plank_h:(i + 1) * plank_h] += shade
    # 每塊板的接頭位置
    for k in range(2):
        x = int(rng.uniform(0, W))
        img[i * plank_h + 2:(i + 1) * plank_h - 1, x:x + 2] = base - 34
grain = wrap_noise(H, W, (0.8, 12), 3) * 3.2 + wrap_noise(H, W, 1.0, 4) * 2.0
img += grain[..., None]
img -= fibers(H, W, 900, 5)[..., None] * 40
for i in range(H // plank_h):
    img[i * plank_h:i * plank_h + 2] = base - 36
img = np.clip(img, 0, 255).astype(np.uint8)
Image.fromarray(img).save(FIN / "bg-workshop-floor_v01.jpg", quality=92)

# 2) 布幕紙材：酒紅和紙（直向纖維、淡淡橫向摺痕、下緣深色滾邊＋芥末黃紙條）；左右四方連續；不烘焙光影（摺層由幾何產生）
H, W = 1024, 512
red = np.array([132, 44, 42], np.float32)
img = np.ones((H, W, 3), np.float32) * red
img += (wrap_noise(H, W, (14, 0.7), 11) * 3.5)[..., None]
img += (wrap_noise(H, W, 1.0, 12) * 2.5)[..., None]
img += (fibers(H, W, 700, 13, (30, 90), vertical_bias=1) * 60)[..., None] * np.array([1.0, 0.7, 0.6])
for y in range(90, H - 120, 180):
    img[y:y + 2] += 9
img[H - 96:H - 30] = img[H - 96:H - 30] * 0.72
img[H - 104:H - 96] = np.array([201, 160, 72], np.float32) + wrap_noise(8, W, 1.0, 14)[..., None] * 4
img[H - 30:] = img[H - 30:] * 0.62
img = np.clip(img, 0, 255).astype(np.uint8)
Image.fromarray(img).save(FIN / "tex-curtain-paper_v01.png", optimize=True)

# 3) 署名卡底紙：奶油色厚卡紙＋白色紙芯邊＋簡單剪紙角花（純幾何，無字）
H, W = 900, 1600
card = np.ones((H, W, 3), np.float32) * np.array([244, 234, 214], np.float32)
card += (wrap_noise(H, W, 1.2, 21) * 2.2)[..., None]
card -= (fibers(H, W, 2600, 22) * 30)[..., None]
yy, xx = np.mgrid[:H, :W]
# 內框細線（暖棕）
m = 54
frame = ((np.abs(xx - m) < 2) | (np.abs(xx - (W - m)) < 2)) & (yy > m) & (yy < H - m)
frame |= ((np.abs(yy - m) < 2) | (np.abs(yy - (H - m)) < 2)) & (xx > m) & (xx < W - m)
card[frame] = np.array([170, 122, 84], np.float32)
# 四角剪紙菱形花（芥末黃＋湖水綠，角色色票的淺版）
for cx, cy in ((m, m), (W - m, m), (m, H - m), (W - m, H - m)):
    d = np.abs(xx - cx) + np.abs(yy - cy)
    card[(d < 30) & (d > 18)] = np.array([214, 172, 74], np.float32)
    card[d <= 12] = np.array([86, 150, 140], np.float32)
alpha = np.ones((H, W), np.float32) * 255
img = np.dstack([np.clip(card, 0, 255), alpha]).astype(np.uint8)
Image.fromarray(img, "RGBA").save(FIN / "tex-titlecard-paper_v01.png", optimize=True)
print("ok")
