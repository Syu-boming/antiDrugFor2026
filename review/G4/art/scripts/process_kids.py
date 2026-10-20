"""G4 美術：孩子 v04 姿勢圖與母版 → assets/final/（裁透明邊＋16 px、顏色外擴、alpha 清雜點），並記錄裁切位移與腳底錨點。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/process_kids.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
GEN = ROOT / "assets/generated"
OUT = ROOT / "assets/final"
PAD = 16
SRC = ["chr-xiaoqing_pose-reach-worried_v04.png", "chr-xiaoyu_pose-stepback-surprised_v04.png",
       "chr-xiaoqing_master_v04.png", "chr-xiaoyu_master_v04.png"]


def bleed(a):
    m = a[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
    out = a.copy()
    out[~m, :3] = a[iy[~m], ix[~m], :3]
    return out


def main():
    info = {}
    for f in SRC:
        a = np.array(Image.open(GEN / f).convert("RGBA"))
        before_white_fringe = int(((a[..., 3] > 0) & (a[..., 3] < 128) & (a[..., :3].min(-1) > 235)).sum())
        a[..., 3] = np.where(a[..., 3] < 24, 0, a[..., 3])
        lab, n = ndimage.label(a[..., 3] > 0)
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= 200)[0])
        stray = int(((a[..., 3] > 0) & ~keep).sum())
        a[~keep, 3] = 0
        ys, xs = np.nonzero(a[..., 3] > 0)
        x0, y0, x1, y1 = xs.min() - PAD, ys.min() - PAD, xs.max() + 1 + PAD, ys.max() + 1 + PAD
        crop = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x1, a.shape[1]), min(y1, a.shape[0])
        crop[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
        crop = bleed(crop)
        Image.fromarray(crop, "RGBA").save(OUT / f, optimize=True)
        al = crop[..., 3] > 128
        rows = np.nonzero(al.any(1))[0]
        bottom = rows.max()
        low = al[bottom - 6:bottom + 1].any(0)
        lx = np.nonzero(low)[0]
        info[f] = {"source": f"assets/generated/{f}", "offset_from_source": [int(x0), int(y0)], "size": [int(crop.shape[1]), int(crop.shape[0])],
                   "feet_bottom_px": [round(float((lx.min() + lx.max()) / 2), 1), int(bottom)],
                   "height_px": int(bottom - rows.min() + 1), "stray_px_removed": stray, "semi_white_fringe_px_before": before_white_fringe}
    (ROOT / "review/G4/art/kids_crop.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
