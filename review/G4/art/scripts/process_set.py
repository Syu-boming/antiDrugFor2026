"""G4 美術：燈籠工作室景片 → assets/generated（原圖加版本號）＋ assets/final（清 alpha 雜點、裁邊、顏色外擴；後牆放大 1.5 倍存 JPG）。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/process_set.py
"""
import json, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "review/G4/art/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
sys.path.insert(0, str(ROOT / "tools"))
from projsim import projector  # noqa: E402

PAD = 8
SETS = {  # 最終 id: (raw, 版本, 透明?)
    "bg-workshop-back": ("wk_back_v02", 2, False),
    "bg-workshop-lanterns": ("wk_lanterns_v01", 1, True),
    "bg-workshop-table": ("wk_table_v02", 2, True),
    "bg-workshop-wing": ("wk_wing_v01", 1, True),
}


def rel_lum(rgb):
    a = rgb.astype(np.float32) / 255
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def bleed(a):
    m = a[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
    out = a.copy()
    out[~m, :3] = a[iy[~m], ix[~m], :3]
    return out


def clean_alpha(a, min_px=400):
    a = a.copy()
    a[..., 3] = np.where(a[..., 3] < 20, 0, a[..., 3])
    lab, n = ndimage.label(a[..., 3] > 0)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.nonzero(sizes >= min_px)[0])
    removed = int(((a[..., 3] > 0) & ~keep).sum())
    a[~keep, 3] = 0
    # 白邊檢查：半透明且接近白色的邊緣像素
    semi = (a[..., 3] > 0) & (a[..., 3] < 200)
    white_semi = int((semi & (a[..., :3].min(-1) > 235)).sum())
    return a, removed, white_semi


def main():
    info = {}
    for fid, (raw, ver, transparent) in SETS.items():
        src = RAW / f"{raw}.png"
        gen = GEN / f"{fid}_v{ver:02d}.png"
        shutil.copyfile(src, gen)
        im = Image.open(src)
        rec = {"raw": str(src.relative_to(ROOT)), "generated": str(gen.relative_to(ROOT)), "raw_size": list(im.size)}
        if not transparent:
            rgb = im.convert("RGB")
            big = rgb.resize((rgb.width * 3 // 2, rgb.height * 3 // 2), Image.LANCZOS)
            out = FIN / f"{fid}_v{ver:02d}.jpg"
            big.save(out, quality=92, subsampling=0)
            a = np.array(big)
            pv = projector(a, "v2")
            L = rel_lum(pv)
            H, W = L.shape
            # 量測帶：畫面下 2/3 中央（角色軀幹後方）
            bands = {"lower_two_thirds": L[int(H * 0.40):int(H * 0.92), int(W * 0.04):int(W * 0.88)],
                     "kids_torso_band_right_half": L[int(H * 0.55):int(H * 0.85), int(W * 0.45):int(W * 0.88)],
                     "upper_shelves": L[:int(H * 0.36)]}
            rec["proj_v2_rel_lum"] = {k: {"median": round(float(np.median(v)), 3), "p10": round(float(np.percentile(v, 10)), 3)} for k, v in bands.items()}
            rec["final"] = str(out.relative_to(ROOT)); rec["final_size"] = list(big.size)
        else:
            a = np.array(im.convert("RGBA"))
            a, removed, white_semi = clean_alpha(a)
            ys, xs = np.nonzero(a[..., 3] > 0)
            x0, y0 = max(xs.min() - PAD, 0), max(ys.min() - PAD, 0)
            x1, y1 = min(xs.max() + 1 + PAD, a.shape[1]), min(ys.max() + 1 + PAD, a.shape[0])
            crop = bleed(a[y0:y1, x0:x1])
            out = FIN / f"{fid}_v{ver:02d}.png"
            Image.fromarray(crop, "RGBA").save(out, optimize=True)
            rec.update(final=str(out.relative_to(ROOT)), final_size=[int(x1 - x0), int(y1 - y0)], crop_from_raw=[int(x0), int(y0)],
                       stray_px_removed=removed, semi_white_edge_px=white_semi)
            al = crop[..., 3] > 128
            if fid == "bg-workshop-table":
                # 桌面上緣：右側三分之一（空的桌面）最上面的不透明列
                w = al.shape[1]
                cols = al[:, int(w * 0.70):int(w * 0.95)]
                top_rows = [int(np.nonzero(cols[:, j])[0].min()) for j in range(cols.shape[1]) if cols[:, j].any()]
                rec["table_top_y_px"] = int(np.median(top_rows))
                xs_ = np.nonzero(al[rec["table_top_y_px"] + 10])[0]
                rec["table_body_x_px"] = [int(xs_.min()), int(xs_.max())]
                rec["table_body_h_px"] = int(al.shape[0] - rec["table_top_y_px"])
            if fid == "bg-workshop-lanterns":
                rows = np.nonzero(al.any(1))[0]
                rec["lowest_lantern_px"] = int(rows.max())
        info[fid] = rec
        print(fid, json.dumps(rec, ensure_ascii=False))
    (ROOT / "review/G4/art/set_process.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
