"""鞠躬圖和站姿母版的比例對照（引擎縮放規則：腳底到 headTop 拉成角色身高）。輸出 review/G5/a6/bow_scale_check.png 與 headTop 建議值。"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/a6/scripts"))
from process_a6_chars import feet_and_top, auto_top, MASTER, CFG  # noqa
FIN = ROOT / "assets/final"
PPU = 160  # 每世界單位像素
mode = sys.argv[1] if len(sys.argv) > 1 else "feet"
def shoe_w(a):
    al = a[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]; b = rows.max(); H = b - rows.min()
    ws = []
    for y in range(int(b - 0.045 * H), b - 2):
        xs = np.nonzero(al[y])[0]
        if len(xs): ws.append(xs.max() - xs.min())
    return float(np.median(ws))
def headw(a, f):
    al = a[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]; t = rows.min(); H = rows.max() - t
    ws = [np.ptp(np.nonzero(al[y])[0]) for y in range(int(t), int(t + f * H)) if al[y].any()]
    return float(np.percentile(ws, 90))
out = {}
tiles = []
for cid in ["xiaoqing", "xiaoyu", "pinan", "chen", "lin", "ye"]:
    m = np.array(Image.open(FIN / MASTER[cid]).convert("RGBA")); b = np.array(Image.open(FIN / f"chr-{cid}_pose-bow_v01.png").convert("RGBA"))
    h = CFG["characters"][cid]["height"]
    fm, _ = feet_and_top(m); tm = auto_top(m); sm = h / (fm[1] - tm)
    fb, tb = feet_and_top(b)
    k_feet = shoe_w(m) / shoe_w(b); k_head = headw(m, 0.17) / headw(b, 0.2)
    if mode == "ratio":   # 鞠躬可見高度＝站姿身高 × 0.86（彎腰約 30°）
        sb = h * 0.86 / (fb[1] - tb)
    else:
        k = {"feet": k_feet, "head": k_head, "mix": (k_feet * k_head) ** 0.5}[mode]
        sb = sm * k
    head_top = round(fb[1] - h / sb, 1)
    out[cid] = {"k_feet": round(k_feet, 3), "k_head": round(k_head, 3), "mode": mode, "headTop": head_top, "visible_ratio": round((fb[1] - tb) * sb / h, 3)}
    # 對照圖：同一地平線
    def place(a, s, f):
        im = Image.fromarray(a); W, H = im.size
        im = im.resize((max(1, int(W * s * PPU)), max(1, int(H * s * PPU))), Image.LANCZOS)
        return im, (f[0] * s * PPU, f[1] * s * PPU)
    im1, f1 = place(m, sm, fm); im2, f2 = place(b, sb, fb)
    tile = Image.new("RGBA", (int(PPU * 3.2), int(PPU * (h + 0.6))), (200, 196, 188, 255))
    base = tile.height - 20
    tile.alpha_composite(im1, (int(PPU * 0.8 - f1[0]), int(base - f1[1])))
    tile.alpha_composite(im2, (int(PPU * 2.3 - f2[0]), int(base - f2[1])))
    d = ImageDraw.Draw(tile); d.line([(0, base), (tile.width, base)], fill=(200, 0, 0), width=2)
    tiles.append(tile)
W = sum(t.width for t in tiles); H = max(t.height for t in tiles)
sheet = Image.new("RGBA", (W, H), (60, 60, 60, 255)); x = 0
for t in tiles: sheet.alpha_composite(t, (x, H - t.height)); x += t.width
sheet.convert("RGB").save(ROOT / "review/G5/a6" / f"bow_scale_check_{mode}.png")
print(json.dumps(out, indent=1))
