"""G4 美術：後牆延伸（生成圖 1536×1024＝11.4×7.6 舞台單位 → 22×10.5 單位，蓋滿中景與大全景的後牆）。
延伸部分只用同一張圖的素材（灰泥、柱、樑、踢腳板）以鏡射拼貼補齊，不新增物件；原圖整張保留在右下。
輸出 assets/final/bg-workshop-back_v02.jpg（2964×1415，134.7 px／單位）。
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = Path(__file__).resolve().parents[4]
src = np.array(Image.open(ROOT / "review/G4/art/raw/wk_back_v02.png").convert("RGB")).astype(np.float32)
PXU = 1024 / 7.6
W, H = int(round(22 * PXU)), int(round(10.5 * PXU))
OX, OY = 1024, H - 1024


def mirror_tile(patch, w, h):
    p = np.concatenate([patch, patch[:, ::-1]], 1)
    p = np.concatenate([p, p[::-1]], 0)
    reps = (h // p.shape[0] + 1, w // p.shape[1] + 1, 1)
    return np.tile(p, reps)[:h, :w]


plaster = src[430:950, 545:955]
canvas = mirror_tile(plaster, W, H)
post = src[430:950, 486:529]           # 柱（含兩側描線）
beam = src[0:50, 545:955]              # 頂樑
skirt = src[972:1024, 545:955]         # 踢腳板
frame = src[230:950, 1360:1398]        # 門框直條
# 延伸的頂樑、踢腳板（全寬，同高度）
canvas[OY:OY + 50] = mirror_tile(beam, W, 50)
canvas[H - 52:H] = mirror_tile(skirt, W, 52)
# 柱：原圖柱位＋往左延伸（間距 ~465 px），全高
orig_posts = [34, 488, 966, 1298]
posts = [OX + x for x in orig_posts] + [OX + 34 - 465, OX + 34 - 930] + [OX + 1536 + 210]
for x in posts:
    canvas[:, x:x + post.shape[1]] = mirror_tile(post, post.shape[1], H)
    canvas[H - 52:H, x:x + post.shape[1]] = mirror_tile(skirt, post.shape[1], 52)  # 踢腳板蓋過柱腳
# 貼回原圖（四邊 24 px 羽化接縫，底邊不羽化）
alpha = np.ones((1024, 1536), np.float32)
f = 24
ramp = np.linspace(0, 1, f)
alpha[:, :f] *= ramp[None, :]
alpha[:f, :] *= ramp[:, None]
reg = canvas[OY:OY + 1024, OX:OX + 1536]
canvas[OY:OY + 1024, OX:OX + 1536] = reg * (1 - alpha[..., None]) + src * alpha[..., None]
# 原圖右側門洞外：補右門框（直條）＋門楣延伸
fx = OX + 1536
lintel = src[166:212, 1364:1536]
ly0 = OY + 166
canvas[ly0:H - 52, fx:fx + frame.shape[1]] = mirror_tile(frame[:, ::-1], frame.shape[1], H - 52 - ly0)
canvas[ly0:ly0 + 46, fx - 8:fx + frame.shape[1] + 6] = mirror_tile(lintel[:, 40:120], frame.shape[1] + 14, 46)
# 原圖上方：柱子往上接
for x in [OX + v for v in orig_posts]:
    canvas[:OY + 4, x:x + post.shape[1]] = mirror_tile(post, post.shape[1], OY + 4)
# 頂樑在柱子前面（重貼頂樑那一條，柱子穿過頂樑會很怪）
canvas[OY + 3:OY + 46, :OX + 4] = mirror_tile(src[3:46, 545:955], OX + 4, 43)
canvas[OY + 3:OY + 46, OX + 1536 - 4:] = mirror_tile(src[3:46, 545:955], W - (OX + 1536 - 4), 43)
# 柱子整體提亮 40%（往灰泥色靠）：孩子身後若剛好有柱子，投影 v2 下背景仍夠亮（G2 問題 1）
plaster_rgb = np.median(plaster.reshape(-1, 3), 0)
pm = np.zeros((H, W), bool)
for x in posts:
    pm[:, x:x + post.shape[1]] = True
pm[H - 52:] = False
pm[OY + 3:OY + 46] = False            # 頂樑不動
pm[OY + 40:OY + 400, OX:OX + 1300] = False   # 層架區（含層板、托架、燈籠）不動
k = 0.40
canvas[pm] = canvas[pm] * (1 - k) + plaster_rgb * k
img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
out = ROOT / "assets/final/bg-workshop-back_v02.jpg"
img.save(out, quality=92, subsampling=0)
info = {"file": str(out.relative_to(ROOT)), "size": [W, H], "px_per_unit": round(PXU, 2), "world_size_units": [22, 10.5],
        "original_placed_at_px": [OX, OY], "doorway_px": [OX + 1395, OX + 1536], "floor_line_px": H,
        "posts_lightened": 0.40, "note": "下緣＝地板線（世界 y=0）；水平中心＝世界 x=0；層架在世界 y 4.8–7.3（中景畫面上方）"}
(ROOT / "review/G4/art/wall_extend.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
print(info)
