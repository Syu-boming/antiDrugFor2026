"""G4 修正第 1 輪（美術，問題 27）：阿樂前臂件 v05——補線稿與紙紋、修掉肘部袖口的零碎紙邊。

輸入：assets/final/rig/chr-ale_forearm-{l,r}_v04.png（不改原檔）
輸出：assets/final/rig/chr-ale_forearm-{l,r}_v05.png、chr-ale_forearm-{l,r}-outline_v05.png（尺寸、樞紐與 v04 相同，
      ale_rig.json 只換檔名，座標不變）；檢查圖 review/G4/art/forearm_fix_v05.png；紀錄 review/G4/art/forearm_fix_v05.json
做法：
1. 零碎紙邊：外形做半徑 6 px 的開運算（去掉寬度 < 12 px 的突出碎片），只保留最大連通塊，再以 1 px 膨脹還原正常邊緣；
   被移除的像素記數。
2. 線稿：沿新外形內側畫 3 px 深棕線（顏色取自原圖袖口線 ≈#70422A），手腕圓舌片（被手蓋住的範圍）不畫，
   免得手轉動時露出一圈圓紙。
3. 紙紋：膚色區加同強度紙纖維（±4%）＋外側 10 px 的輕微暗邊（2–5%），和手、袖子的紙感一致。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/fix_forearms_v05.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_ale_rig as B  # noqa: E402  （outline_of、bleed 與 v04 相同）

RIG = ROOT / "assets/final/rig"
ART = ROOT / "review/G4/art"
LINE = np.array([112, 66, 42], np.float32)


def disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return xx * xx + yy * yy <= r * r


def fibers(shape, seed, n=260):
    h, w = shape
    r = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    for _ in range(n):
        x, y = r.uniform(0, w), r.uniform(0, h)
        ang = r.uniform(0, np.pi)
        L = r.uniform(8, 30)
        s = 1 if r.random() < 0.5 else -1
        for t in np.linspace(0, L, int(L)):
            xi, yi = int(x + np.cos(ang) * t), int(y + np.sin(ang) * t)
            if 0 <= xi < w and 0 <= yi < h:
                out[yi, xi] += s
    out = ndimage.gaussian_filter(out, 0.7)
    grain = ndimage.gaussian_filter(np.random.default_rng(seed + 1).standard_normal(shape), 1.2)
    out = out / (np.abs(out).max() + 1e-6) + 0.5 * grain / (grain.std() + 1e-6)
    return out / (np.abs(out).max() + 1e-6)


def fix(side):
    rig = json.loads((RIG / "ale_rig.json").read_text())
    part = rig["parts"][f"forearm_{side}"]
    hand = rig["parts"][f"hand_{side}"]
    src = RIG / part["file"]
    a = np.array(Image.open(src).convert("RGBA")).astype(np.float32)
    m = a[..., 3] > 127
    # 1) 零碎紙邊：保留「膚色主體＋最大一塊袖口紙＋貼著它們的深色線」，其餘（切件時帶進來的襯衫碎片）移除
    R_, B_ = a[..., 0], a[..., 2]
    L_ = a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    skin0 = m & (R_ > 190) & (B_ < 150) & (R_ - B_ > 90)
    dark0 = m & (L_ < 150) & ~skin0
    pale0 = m & ~skin0 & ~dark0
    sk = ndimage.binary_opening(skin0, structure=disk(2))
    lab, n = ndimage.label(sk)
    sk = lab == (1 + int(np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)))))
    sk = ndimage.binary_fill_holes(sk)
    lab, n = ndimage.label(pale0)
    cuff = lab == (1 + int(np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)))))
    core = ndimage.binary_fill_holes(sk | cuff | (dark0 & ndimage.binary_dilation(sk | cuff, structure=disk(3))))
    keep = ndimage.binary_fill_holes(ndimage.binary_closing(core, structure=disk(2))) & m
    removed = m & ~keep
    new = a.copy()
    new[~keep, 3] = 0
    m2 = keep
    # 2) 線稿：新外形內側 3 px（手腕圓舌片內不畫）
    inner = ndimage.distance_transform_edt(m2)
    wj = np.array(hand["pivot_master"]) - np.array(part["origin_master"])   # 手腕樞紐在前臂圖上的位置
    yy, xx = np.mgrid[:m2.shape[0], :m2.shape[1]]
    tab = (xx - wj[0]) ** 2 + (yy - wj[1]) ** 2 <= (hand.get("tab_radius") or 40) ** 2
    tab_r = 46
    tab = (xx - wj[0]) ** 2 + (yy - wj[1]) ** 2 <= tab_r ** 2
    line_a = np.clip(3.5 - inner, 0, 1) * m2 * ~tab
    # 原本就有深色線的地方不重畫（避免變粗）
    L0 = a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    already = ndimage.binary_dilation(L0 < 125, iterations=1) & m2
    line_a = line_a * ~already
    # 3) 紙紋：膚色區（R 高、B 低）
    skin = m2 & (a[..., 0] > 200) & (a[..., 2] < 150) & (a[..., 1] > 120)
    f = fibers(m2.shape, 401 if side == "l" else 402)
    rgb = new[..., :3]
    mult = 1 + 0.04 * f
    edge_dark = 1 - 0.05 * np.clip(1 - (inner - 3) / 10, 0, 1)
    k = np.where(skin, mult * edge_dark, 1.0)
    rgb = rgb * k[..., None]
    # 線
    rgb = rgb * (1 - line_a[..., None]) + LINE * line_a[..., None]
    new[..., :3] = np.clip(rgb, 0, 255)
    new[..., 3] = np.where(m2, 255, 0)
    out = B.bleed(new.astype(np.uint8))
    stem = part["file"].replace("_v04.png", "")
    Image.fromarray(out, "RGBA").save(RIG / f"{stem}_v05.png", optimize=True)
    Image.fromarray(B.bleed(B.outline_of(out[..., 3])), "RGBA").save(RIG / f"{stem}-outline_v05.png", optimize=True)
    return {"part": f"forearm_{side}", "file_v05": f"{stem}_v05.png", "outline_v05": f"{stem}-outline_v05.png",
            "stray_px_removed": int(removed.sum()), "line_px_added": int((line_a > 0.5).sum()),
            "skin_px_textured": int(skin.sum()), "size": list(out.shape[1::-1])}, a.astype(np.uint8), out, removed


def main():
    log = []
    tiles = []
    for side in ("l", "r"):
        rec, before, after, removed = fix(side)
        log.append(rec)
        tiles.append((side, before, after, removed))
    # 檢查圖：前／後（3× 放大，深藍底）＋被移除的碎片（紅）
    sc = 3
    cols = []
    for side, b, a, rm in tiles:
        h, w = b.shape[:2]
        for arr, lab in ((b, "v04"), (a, "v05")):
            bg = Image.new("RGBA", (w, h), (60, 90, 120, 255))
            bg.alpha_composite(Image.fromarray(arr))
            if lab == "v04":
                ov = np.zeros((h, w, 4), np.uint8); ov[rm] = (255, 40, 40, 255)
                bg.alpha_composite(Image.fromarray(ov))
            cols.append((f"forearm_{side} {lab}", bg.resize((w * sc, h * sc), Image.NEAREST)))
    W = sum(c.width for _, c in cols) + 20 * (len(cols) + 1)
    H = max(c.height for _, c in cols) + 50
    S = Image.new("RGB", (W, H), (44, 42, 40))
    d = ImageDraw.Draw(S)
    x = 20
    for lab, c in cols:
        d.text((x, 10), lab + ("（紅＝移除的碎片）" if "v04" in lab else ""), fill=(240, 240, 240))
        S.paste(c.convert("RGB"), (x, 40))
        x += c.width + 20
    S.save(ART / "forearm_fix_v05.png")
    (ART / "forearm_fix_v05.json").write_text(json.dumps(log, ensure_ascii=False, indent=1))
    print(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
