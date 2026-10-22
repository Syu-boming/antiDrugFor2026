"""第三幕（a3）角色新姿勢：Codex 原檔 → assets/generated（加版本號；兒童主色調回 v04 色票）→ assets/final（去雜點、裁透明邊＋16 px）。
照 G5 共用美術 process_chars.py 的流程與自動檢查（霧邊、白邊、裁腳、左右 L*、主色 ΔE），只是 JOBS 與紀錄檔換成第三幕自己的。
用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/process_a3_chars.py
紀錄：review/G5/a3/import.json
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
sys.path.insert(0, str(ROOT / "tools"))
import g5lib as L  # noqa: E402
from process_chars import GARMENTS, XQ_SPEC, XY_SPEC, master_ref_lab  # noqa: E402  （只讀共用設定，不改共用檔）

RAW = ROOT / "review/G5/a3/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
OUT = ROOT / "review/G5/a3"

# raw 檔 → (角色, 檔名部件, 版本, 調色規格)
JOBS = {
    "pose_xq_pointr_v07_fix": ("xiaoqing", "pose-pointr", "v07", XQ_SPEC),
    "pose_xy_pointr_v07": ("xiaoyu", "pose-pointr", "v07", XY_SPEC),
    "pose_xy_glasses_v07": ("xiaoyu", "pose-glasses", "v07", XY_SPEC),
}


def process(raw_id, ref):
    cid, part, ver, spec = JOBS[raw_id]
    raw = RAW / f"{raw_id}.png"
    gen = GEN / f"chr-{cid}_{part}_{ver}.png"
    rec = {"raw": str(raw.relative_to(ROOT)), "character": cid, "part": part}
    import recolor_garment as RG
    a0 = np.array(Image.open(raw).convert("RGBA"))
    g0 = L.garment_stats(a0, spec[0][1], spec[0][2], spec[0][3], 1.0, spec[0][4])
    rec["raw_main_L*"] = g0 and g0["L*"]
    if g0 and abs(g0["L*"] - spec[0][5]) > 1.0:
        tmp = GEN / f"_tmp_{raw_id}.png"
        shutil.copyfile(raw, tmp)
        rep = RG.recolor(tmp.name, gen.name, spec)
        tmp.unlink()
        rec["recolor"] = [list(r) for r in rep]
    else:
        shutil.copyfile(raw, gen)
        rec["recolor"] = "未調整（L* 與 v04 差 ≤ 1）"
    rec["generated"] = str(gen.relative_to(ROOT))
    rawa = np.array(Image.open(raw).convert("RGBA"))
    a = np.array(Image.open(gen).convert("RGBA"))
    a, removed = L.clean_alpha(a)
    rec["stray_px_removed"] = removed
    crop, off = L.crop_pad(a, 16)
    fin = FIN / f"chr-{cid}_{part}_{ver}.png"
    Image.fromarray(crop, "RGBA").save(fin, optimize=True)
    al = crop[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]
    bottom = int(rows.max())
    low = al[bottom - 6:bottom + 1].any(0)
    lx = np.nonzero(low)[0]
    rec.update({"final": str(fin.relative_to(ROOT)), "offset_from_source": list(off), "size": [int(crop.shape[1]), int(crop.shape[0])],
                "alpha_ref": L.alpha_ref(crop), "feet_bottom_px": [round(float((lx.min() + lx.max()) / 2), 1), bottom],
                "height_px": int(bottom - rows.min() + 1)})
    rec["checks"] = L.checks(crop, rawa)
    gs = {}
    for g in GARMENTS.get(cid, []):
        st = L.garment_stats(crop, g[1], g[2], g[3], g[4], g[5])
        if st and cid in ref and ref[cid].get(g[0]):
            st["dE_vs_v04"] = L.delta_e(st["lab"], ref[cid][g[0]]["lab"])
        gs[g[0]] = st
    rec["garments"] = gs
    return rec


def main():
    path = OUT / "import.json"
    info = json.loads(path.read_text()) if path.exists() else {}
    ref = master_ref_lab()
    for k in JOBS:
        if not (RAW / f"{k}.png").exists():
            continue
        info[k] = process(k, ref)
        c = info[k]["checks"]
        print(k, info[k]["final"], "白邊", c.get("white_border_px"), c.get("white_border_ok"), "霧", c.get("fog_px"),
              "裁切", c.get("raw_touches_edge"), "左右L差", c.get("lr_L_median_diff"),
              {n: (g and (g["median"], g["L*"], g.get("dE_vs_v04"))) for n, g in info[k]["garments"].items()})
    path.write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
