"""G4 修正第 1 輪（美術，問題 16、25）：小晴三張新姿勢圖（Codex image_gen）→ assets/generated → assets/final。

姿勢（全部 3/4 側身朝畫面左、看著阿樂，沒有指人的動作）：
  watch   ：a2_c002 開場「注視阿樂」（取代正面立正母版）；放鬆、微笑
  palm    ：「叔叔，小心！」伸出手掌示意（掌心向外、手指併攏、手在胸口高度）；擔心、叫喚的圓嘴
  worried ：擔心站姿（雙手輕握在胸前）；a2_c004 全段用
步驟：
  1. review/G4/art/raw/pose_xq_<k>_v05.png（Codex 原檔，不改）→ 量吊帶褲 L*；若和母版 v04 的 37 差 > 1，
     用 tools/recolor_garment.recolor 同色相調到 L* 37（和 G2 退路 D-G2-06 同法）→ assets/generated/chr-xiaoqing_pose-<k>_v05.png
  2. 去 alpha 雜點、裁透明邊＋16 px、顏色外擴 → assets/final/chr-xiaoqing_pose-<k>_v05.png（同 process_kids.py）
  3. 記錄 review/G4/art/xq_v05_import.json（裁切位移、腳底、身高、頭身比、吊帶褲色、雜點數）
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/process_xq_v05.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
import recolor_garment as RG  # noqa: E402
from skimage import color as skc  # noqa: E402

RAW = ROOT / "review/G4/art/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
PAD = 16
POSES = ["watch", "palm", "worried"]
SPEC = [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, (0.0, 1.0), 37.0)]


def overalls_L(path):
    im = np.array(Image.open(path).convert("RGBA")).astype(np.float32)
    h, s, v = RG.hsv(im[..., :3])
    w = RG.hue_weight(h, 160, 205) * (s > 0.25) * (v > 0.10) * (im[..., 3] > 200)
    core = ndimage.binary_opening(w > 0.5, iterations=1)
    lab = skc.rgb2lab(im[..., :3] / 255.0)
    if core.sum() < 500:
        return None, 0, None
    med = np.median(im[..., :3][core], 0)
    return float(np.median(lab[..., 0][core])), int(core.sum()), "#%02X%02X%02X" % tuple(int(round(c)) for c in med)


def bleed(a):
    m = a[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
    out = a.copy()
    out[~m, :3] = a[iy[~m], ix[~m], :3]
    return out


def main():
    info = {"master_v04_overalls": dict(zip(("L*", "px", "median"), overalls_L(GEN / "chr-xiaoqing_master_v04.png")))}
    for k in POSES:
        raw = RAW / f"pose_xq_{k}_v05.png"
        if not raw.exists():
            info[k] = {"error": "原檔不存在"}
            continue
        gen = GEN / f"chr-xiaoqing_pose-{k}_v05.png"
        L0, px, med0 = overalls_L(raw)
        rec = {"raw": str(raw.relative_to(ROOT)), "raw_overalls_L*": None if L0 is None else round(L0, 1), "raw_overalls_median": med0}
        if L0 is not None and abs(L0 - 37.0) > 1.0:
            rep = RG.recolor(raw, gen, SPEC)
            rec["recolor"] = [list(r) for r in rep]
        else:
            Image.open(raw).save(gen)
            rec["recolor"] = "未調整（L* 與母版差 ≤ 1）"
        L1, _, med1 = overalls_L(gen)
        rec["generated"] = str(gen.relative_to(ROOT))
        rec["overalls_L*_after"] = None if L1 is None else round(L1, 1)
        rec["overalls_median_after"] = med1
        a = np.array(Image.open(gen).convert("RGBA"))
        a[..., 3] = np.where(a[..., 3] < 24, 0, a[..., 3])
        a[..., 3] = np.where(a[..., 3] >= 250, 255, a[..., 3])   # Codex 圖內部 alpha＝254 → 255
        lab, n = ndimage.label(a[..., 3] > 0)
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= 200)[0])
        rec["stray_px_removed"] = int(((a[..., 3] > 0) & ~keep).sum())
        a[~keep, 3] = 0
        ys, xs = np.nonzero(a[..., 3] > 0)
        x0, y0, x1, y1 = xs.min() - PAD, ys.min() - PAD, xs.max() + 1 + PAD, ys.max() + 1 + PAD
        crop = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x1, a.shape[1]), min(y1, a.shape[0])
        crop[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
        crop = bleed(crop)
        fin = FIN / f"chr-xiaoqing_pose-{k}_v05.png"
        Image.fromarray(crop, "RGBA").save(fin, optimize=True)
        al = crop[..., 3] > 128
        rows = np.nonzero(al.any(1))[0]
        bottom = rows.max()
        low = al[bottom - 6:bottom + 1].any(0)
        lx = np.nonzero(low)[0]
        rec.update({"final": str(fin.relative_to(ROOT)), "offset_from_source": [int(x0), int(y0)], "size": [int(crop.shape[1]), int(crop.shape[0])],
                    "feet_bottom_px": [round(float((lx.min() + lx.max()) / 2), 1), int(bottom)], "height_px": int(bottom - rows.min() + 1),
                    "has_alpha": bool((a[..., 3] == 0).any()),
                    "semi_alpha_px": int(((crop[..., 3] > 0) & (crop[..., 3] < 255)).sum())})
        info[k] = rec
    (ROOT / "review/G4/art/xq_v05_import.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
