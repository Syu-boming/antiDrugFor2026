"""小晴 pointr（Codex 原檔把星星髮夾畫在她的右側＝畫面左）：程式搬到她的左側（3/4 側臉時在頭頂右後方、比較小），
和母版 v04 的髮夾同一側（畫面右），同場和 cross、palmno、forehead-l 不會左右跳。
輸入 review/G5/a3/raw/pose_xq_pointr_v07.png（不改）→ 輸出 review/G5/a3/raw/pose_xq_pointr_v07_fix.png（之後走 process_a3_chars.py）。
做法：星星＝金黃色像素（色相 35–55、飽和 ≥0.45、亮度 ≥0.55）外擴 7 px；原位置用旁邊的頭髮貼片（同形狀、平移）補上、邊緣柔化；
星星縮成 0.62 倍、轉 −12°，貼在頭頂右後方的頭髮上（整顆在頭髮剪影內，不改外輪廓與白邊）。
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
src = ROOT / "review/G5/a3/raw/pose_xq_pointr_v07.png"
dst = ROOT / "review/G5/a3/raw/pose_xq_pointr_v07_fix.png"
shift = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (-55, 25)
target = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (545, 128)

im = Image.open(src).convert("RGBA")
a = np.array(im).astype(np.float32)
rgb = a[..., :3] / 255
mx, mn = rgb.max(2), rgb.min(2)
s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
h = np.zeros_like(mx)
d = np.maximum(mx - mn, 1e-6)
h = np.where(mx == r, (60 * ((g - b) / d)) % 360, h)
h = np.where(mx == g, 60 * ((b - r) / d) + 120, h)
h = np.where(mx == b, 60 * ((r - g) / d) + 240, h)
yellow = (h > 35) & (h < 58) & (s > 0.45) & (mx > 0.55) & (a[..., 3] > 200)
yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
yellow &= (yy < 420)            # 只在頭部（上衣也是黃色）
lab, n = ndimage.label(yellow)
sizes = ndimage.sum(yellow, lab, range(1, n + 1))
k = int(np.argmax(sizes)) + 1
star = lab == k
ys, xs = np.nonzero(star)
print("star bbox", xs.min(), ys.min(), xs.max(), ys.max(), "px", star.sum())
# 星星的暗面、摺痕（色相偏橘、飽和較低）也算進去：只在星星外框附近
near = ndimage.binary_dilation(star, iterations=10)
warm = (h > 20) & (h < 65) & (s > 0.28) & (mx > 0.35)
star = star | (near & warm)
mask = ndimage.binary_dilation(star, iterations=12)
# 星星（含外框）切出來
y0, y1, x0, x1 = ys.min() - 8, ys.max() + 9, xs.min() - 8, xs.max() + 9
star_rgba = a[y0:y1, x0:x1].copy()
star_rgba[..., 3] = np.where(mask[y0:y1, x0:x1], star_rgba[..., 3], 0)
# 1) 補頭髮：雙調和內插（skimage）補顏色＋旁邊頭髮的高頻紋理（毛氈紙紋），邊緣 6 px 柔化
from skimage.restoration import inpaint_biharmonic
by0, by1, bx0, bx1 = ys.min() - 30, ys.max() + 30, xs.min() - 30, xs.max() + 30
sub = a[by0:by1, bx0:bx1, :3] / 255.0
m = mask[by0:by1, bx0:bx1]
fill = inpaint_biharmonic(sub, m, channel_axis=-1)
# 紋理：左側頭髮一塊乾淨的毛氈區（raw x 185–245、y 235–315）鏡射鋪滿
blk = a[235:315, 185:245, :3] / 255.0
blk = blk - ndimage.gaussian_filter(blk, (3, 3, 0))
th, tw = by1 - by0, bx1 - bx0
row = np.concatenate([blk if i % 2 == 0 else blk[:, ::-1] for i in range(tw // blk.shape[1] + 2)], 1)
til = np.concatenate([row if j % 2 == 0 else row[::-1] for j in range(th // blk.shape[0] + 2)], 0)[:th, :tw]
med = np.median(a[235:315, 185:245, :3].reshape(-1, 3), 0) / 255.0   # 乾淨頭髮的中位色：內插色往它拉一半（去掉亮斑、暗斑）
fill = fill * 0.4 + med * 0.6
fill = np.clip(fill + til * 0.9, 0, 1)
dist = ndimage.distance_transform_edt(m)
w = np.clip(dist / 9.0, 0, 1)[..., None]
out = a.copy()
out[by0:by1, bx0:bx1, :3] = a[by0:by1, bx0:bx1, :3] * (1 - w) + fill * 255 * w
# 2) 星星縮小、轉一點，貼到頭頂右後方
st = Image.fromarray(star_rgba.astype(np.uint8), "RGBA")
st = st.resize((int(st.width * 0.62), int(st.height * 0.62)), Image.LANCZOS).rotate(-12, resample=Image.BICUBIC, expand=True)
o = Image.fromarray(out.astype(np.uint8), "RGBA")
tx, ty = target[0] - st.width // 2, target[1] - st.height // 2
hair_alpha = np.array(o)[..., 3]
layer = Image.new("RGBA", o.size, (0, 0, 0, 0))
layer.alpha_composite(st, (tx, ty))
la = np.array(layer)
la[..., 3] = np.minimum(la[..., 3], hair_alpha)   # 不超出原剪影
o.alpha_composite(Image.fromarray(la, "RGBA"))
o.save(dst)
print("wrote", dst, "shift", shift, "target", target)
