"""G5 修正第 1 輪（開場＋第一幕）：驗收指出的美術問題，程式繪製（不用 Codex 生圖）。

輸出：
  assets/final/sets/workshop_a0/stand_v02.png      空著的主燈底座（a0_c003「骨架不見了」看得出空位）：
                                                    圓木座＋淺色紙墊上一圈虛線印痕（骨架原本立在這裡）＋八個空插孔；比 v01 大、俯角更大
  assets/final/sets/square_a1/silbody_v02.png       窗內阿樂叔叔剪影（a1_c008）：同 v01 外形與裁切（尺寸不變），改成兩階深色剪影——
                                                    頭髮與圍裙最深、襯衫與皮膚次深（看得出圍裙與髮型；沒有五官、沒有操偶線）
  assets/final/sets/square_a1/silarm_v02.png        右臂（襯衫袖＋拳頭，次深色；轉軸同 v01）
  assets/final/sets/square_a1/silbamboo_v02.png     短竹條（v01 的一半長，不像長竿）
規則：圖裡沒有任何文字、數字、標誌。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

OUT0 = ROOT / "assets/final/sets/workshop_a0"
OUT1 = ROOT / "assets/final/sets/square_a1"
DARK = np.array([38, 28, 26], np.float32)     # 頭髮、圍裙（窗光前最深）
MID = np.array([86, 66, 58], np.float32)      # 襯衫、皮膚、手臂


def stand():
    """空著的主燈底座 v02：圓木座（正面木紋帶）＋座面上的淺色紙墊；紙墊上一圈深色虛線印痕＝骨架原本立的位置，
    印痕上八個空插孔（深色），中間空空的。寬 1.2 世界單位。"""
    PP = 300
    W, H = int(1.2 * PP), int(0.5 * PP)
    s = P.Sheet(W, H)
    top = (222, 182, 128, 255)
    side = (176, 128, 82, 255)
    mat = (246, 236, 214, 255)
    s.rect(16, H * 0.40, W - 16, H - 6, side, line=2.2, r=12)
    for x0 in range(46, W - 46, 52):                       # 正面木紋短線
        s.line([(x0, H * 0.72), (x0 + 24, H * 0.72)], 1.4, (138, 98, 62, 255))
    s.ellipse(10, 4, W - 10, H * 0.66, top, line=2.2)      # 座面
    s.ellipse(W * 0.14, H * 0.12, W * 0.86, H * 0.56, mat, line=1.6)   # 紙墊
    # 虛線印痕（骨架底圈原本壓在這裡）
    cx, cy, rx, ry = W / 2, H * 0.34, W * 0.27, H * 0.14
    n = 28
    for k in range(n):
        if k % 2:
            continue
        a0, a1 = 2 * np.pi * k / n, 2 * np.pi * (k + 0.75) / n
        pts = [(cx + rx * np.cos(a), cy + ry * np.sin(a)) for a in np.linspace(a0, a1, 6)]
        s.line(pts, 3.0, (120, 84, 56, 255))
    # 八個空插孔（骨架的竹篾原本插在這裡）
    for k in range(8):
        a = 2 * np.pi * (k + 0.5) / 8
        x, y = cx + rx * np.cos(a), cy + ry * np.sin(a)
        s.ellipse(x - 10, y - 5.5, x + 10, y + 5.5, (70, 48, 34, 255), line=1.0)
    # 兩小撮竹屑（剛被拿走的樣子）
    s.line([(W * 0.2, H * 0.47), (W * 0.25, H * 0.44)], 1.8, (200, 164, 100, 255))
    s.line([(W * 0.78, H * 0.45), (W * 0.83, H * 0.48)], 1.8, (200, 164, 100, 255))
    return s.finish(white_border=6), {"px_per_unit": PP, "note": "底邊中央為原點；座面中心約在高度 0.66（由下往上）"}


def silhouettes():
    """同 build_a01_art.silhouettes 的外形與裁切（尺寸、轉軸不變），顏色改成兩階：頭髮＋圍裙＝DARK，其他＝MID。"""
    src = np.array(Image.open(ROOT / "assets/generated/chr-ale_master_v02.png").convert("RGBA")).astype(np.float32)
    al = src[..., 3] > 128
    ys, xs = np.nonzero(al)
    top = ys.min()
    cut = int(top + 0.52 * (ys.max() - top))
    body = al[:cut].copy()
    xc = (xs.min() + xs.max()) / 2
    shoulder = int(top + 0.2 * (ys.max() - top))
    body[shoulder:, : int(xc - 0.21 * (xs.max() - xs.min()))] = False
    m = ndimage.binary_closing(body, iterations=3)
    r, g, b = src[:cut, :, 0], src[:cut, :, 1], src[:cut, :, 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    inner = ndimage.binary_erosion(m, iterations=14)          # 去掉貼紙白邊
    apron = inner & (b > r + 18) & (b > 60)
    apron = ndimage.binary_fill_holes(ndimage.binary_closing(apron, iterations=14)) & inner   # 口袋、工具、腰帶的空隙補滿
    hair = inner & (lum < 95) & (np.arange(cut)[:, None] < top + 0.16 * (ys.max() - top))
    dark = apron | hair
    dark = ndimage.binary_opening(dark, iterations=2)
    lab, nl = ndimage.label(dark)
    sizes = ndimage.sum(dark, lab, range(1, nl + 1))
    keep = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz > 2500])   # 眉毛、眼睛等小塊不要（沒有五官）
    dark = ndimage.binary_closing(keep, iterations=4) & m
    darkf = ndimage.gaussian_filter(dark.astype(np.float32), 1.6)
    yb, xb = np.nonzero(m)
    sl = (slice(yb.min(), yb.max() + 1), slice(xb.min(), xb.max() + 1))
    def pad(x):
        return np.pad(x[sl], 12)
    a = ndimage.gaussian_filter(pad(m).astype(np.float32), 2.2)
    d = pad(darkf)
    out = np.zeros(a.shape + (4,), np.float32)
    out[..., :3] = MID[None, None] * (1 - d[..., None]) + DARK[None, None] * d[..., None]
    out[..., 3] = np.clip(a * 1.15, 0, 1) * 255
    body_img = out.astype(np.uint8)

    def soft(mask, col, blur=2.2):
        aa = ndimage.gaussian_filter(mask.astype(np.float32), blur)
        o = np.zeros(mask.shape + (4,), np.float32)
        o[..., :3] = col
        o[..., 3] = np.clip(aa * 1.15, 0, 1) * 255
        return o.astype(np.uint8)
    S = 3
    arm = Image.new("L", (300 * S, 300 * S), 0)
    dr = ImageDraw.Draw(arm)
    sx, sy = 240 * S, 250 * S
    ex, ey = 150 * S, 160 * S
    hx, hy = 110 * S, 60 * S
    dr.line([(sx, sy), (ex, ey)], fill=255, width=46 * S)
    dr.line([(ex, ey), (hx, hy)], fill=255, width=38 * S)
    dr.ellipse([hx - 26 * S, hy - 26 * S, hx + 26 * S, hy + 26 * S], fill=255)
    dr.ellipse([sx - 24 * S, sy - 24 * S, sx + 24 * S, sy + 24 * S], fill=255)
    arm = arm.resize((300, 300), Image.LANCZOS)
    arm_img = soft(np.array(arm) > 128, MID)
    # 短竹條：v01 長 520 px → 260 px（約 0.5 世界單位），兩端圓
    bam = Image.new("L", (60 * S, 260 * S), 0)
    ImageDraw.Draw(bam).rounded_rectangle([20 * S, 4 * S, 40 * S, 256 * S], 9 * S, fill=255)
    bam = bam.resize((60, 260), Image.LANCZOS)
    bam_img = soft(np.array(bam) > 128, DARK, 1.4)
    return body_img, arm_img, bam_img, {"body_size_px": list(body_img.shape[1::-1]), "bamboo_size_px": [60, 260],
                                        "dark_ratio": round(float(dark.sum() / max(1, m.sum())), 3)}


def main():
    meta = {}
    a, m = stand()
    P.save(a, OUT0 / "stand_v02.png")
    meta["assets/final/sets/workshop_a0/stand_v02.png"] = {**m, "size": list(a.shape[1::-1])}
    b, ar, bm, m2 = silhouettes()
    for name, img in (("silbody", b), ("silarm", ar), ("silbamboo", bm)):
        P.save(img, OUT1 / f"{name}_v02.png")
    meta["assets/final/sets/square_a1/sil*_v02.png"] = m2
    for k, v in meta.items():
        print(k, v)
    mp = ROOT / "review/G5/a0/scripts/build_a01_art_meta.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    old.update(meta)
    mp.write_text(json.dumps(old, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
