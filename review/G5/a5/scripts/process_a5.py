"""第五幕：Codex 原檔 → assets/generated（加版本號；兒童主色同色相調回 v04 色票）→ assets/final（去雜點、裁透明邊＋16 px、顏色外擴）。
做法同 review/G5/shared_art/scripts/process_chars.py（共用 g5lib 的檢查：霧邊、白邊、裁腳、主色 ΔE、平光）。

用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/process_a5.py
輸出紀錄：review/G5/a5/import.json
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
sys.path.insert(0, str(ROOT / "tools"))
import g5lib as L  # noqa: E402

RAW = ROOT / "review/G5/a5/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
OUT = ROOT / "review/G5/a5"

XQ_SPEC = [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, (0.0, 1.0), 37.0)]
XY_SPEC = [("橘紅外套", (345, 22), 0.55, 0.25, (0.15, 0.78), 39.0)]
GARMENTS = {
    "xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, 1.0, (0.3, 1.0)), ("芥末黃上衣", (35, 55), 0.5, 0.5, 1.0, (0.2, 0.5))],
    "xiaoyu": [("橘紅外套", (345, 22), 0.55, 0.25, 0.95, (0.15, 0.6)), ("卡其短褲", (25, 45), 0.2, 0.4, 0.85, (0.5, 0.75))],
    "chen": [("黃綠背心", (55, 95), 0.4, 0.4, 1.0, (0.15, 0.6)), ("淺灰制服", (0, 360), 0.0, 0.55, 0.9, (0.12, 0.45))],
}
REF_MASTER = {"xiaoqing": "chr-xiaoqing_master_v04.png", "xiaoyu": "chr-xiaoyu_master_v04.png", "chen": "chr-chen_master_v01.png"}

# raw_id → (角色, 檔名部件, 調色規格)
JOBS = {
    "a5_chen_shout_v01": ("chen", "pose-shoutr", None),
    "a5_xq_sitb_v01": ("xiaoqing", "pose-sitb", XQ_SPEC),
    "a5_xy_sitb_v01": ("xiaoyu", "pose-sitb", XY_SPEC),
}


def ref_lab():
    ref = {}
    for cid, f in REF_MASTER.items():
        a = np.array(Image.open(FIN / f).convert("RGBA"))
        ref[cid] = {g[0]: L.garment_stats(a, g[1], g[2], g[3], g[4], g[5]) for g in GARMENTS[cid]}
    return ref


def defog(a, keep=3.0):
    """離不透明範圍（alpha≥128）超過 keep px 的半透明殘留（Codex 的淡霧）清成 0。"""
    a = a.copy()
    m = a[..., 3] >= 128
    d = ndimage.distance_transform_edt(~m)
    a[(d > keep), 3] = 0
    return a


def finish(a_gen, rawa, cid, part, ver, ref):
    a, removed = L.clean_alpha(a_gen)
    a = defog(a)
    crop, off = L.crop_pad(a, 16)
    fin = FIN / f"chr-{cid}_{part}_{ver}.png"
    Image.fromarray(crop, "RGBA").save(fin, optimize=True)
    al = crop[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]
    bottom = int(rows.max())
    low = al[bottom - 6:bottom + 1].any(0)
    lx = np.nonzero(low)[0]
    rec = {"final": str(fin.relative_to(ROOT)), "offset_from_source": list(off), "size": [int(crop.shape[1]), int(crop.shape[0])],
           "stray_px_removed": removed, "feet_bottom_px": [round(float((lx.min() + lx.max()) / 2), 1), bottom],
           "height_px": int(bottom - rows.min() + 1), "checks": L.checks(crop, rawa)}
    gs = {}
    for g in GARMENTS.get(cid, []):
        st = L.garment_stats(crop, g[1], g[2], g[3], g[4], g[5])
        if st and cid in ref and ref[cid].get(g[0]):
            st["dE_vs_master"] = L.delta_e(st["lab"], ref[cid][g[0]]["lab"])
        gs[g[0]] = st
    rec["garments"] = gs
    return rec


def process(raw_id, ref):
    cid, part, spec = JOBS[raw_id]
    raw = RAW / f"{raw_id}.png"
    ver = raw_id.rsplit("_", 1)[1]
    gen = GEN / f"chr-{cid}_{part}_{ver}.png"
    rec = {"raw": str(raw.relative_to(ROOT)), "character": cid, "part": part}
    if spec:
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
    else:
        shutil.copyfile(raw, gen)
    rec["generated"] = str(gen.relative_to(ROOT))
    rawa = np.array(Image.open(raw).convert("RGBA"))
    a = np.array(Image.open(gen).convert("RGBA"))
    rec.update(finish(a, rawa, cid, part, ver, ref))
    return rec


def medics(ref):
    """一張兩人 → 兩個立牌（中間透明縫切開）。"""
    raw = RAW / "a5_medics_v01.png"
    shutil.copyfile(raw, GEN / "chr-medic_pair_v01.png")
    a = np.array(Image.open(raw).convert("RGBA"))
    a, _ = L.clean_alpha(a)
    a = defog(a)
    colany = (a[..., 3] >= 128).any(0)
    xs = np.nonzero(colany)[0]
    gap = np.nonzero(~colany[xs.min():xs.max()])[0] + xs.min()
    cut = int((gap.min() + gap.max()) / 2)
    out = {"raw": str(raw.relative_to(ROOT)), "generated": "assets/generated/chr-medic_pair_v01.png", "cut_x": cut}
    for k, sl in (("a", slice(0, cut)), ("b", slice(cut, a.shape[1]))):
        part = np.zeros_like(a)
        part[:, sl] = a[:, sl]
        rec = finish(part, part, f"medic-{k}", "stand", "v01", ref)
        out[k] = rec
    return out


def wall():
    raw = RAW / "a5_hosp_wall_v01.png"
    gen = GEN / "bg-hospital-wall_v01.png"
    shutil.copyfile(raw, gen)
    dst = FIN / "sets/a5_hospital/wall_v01.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(raw).convert("RGB")
    im.save(dst, optimize=True)
    return {"raw": str(raw.relative_to(ROOT)), "generated": str(gen.relative_to(ROOT)), "final": str(dst.relative_to(ROOT)), "size": list(im.size)}


def main():
    ref = ref_lab()
    info = {"_reference": ref}
    for k in JOBS:
        info[k] = process(k, ref)
        c = info[k]["checks"]
        print(k, info[k]["final"], "白邊", c.get("white_border_px"), c.get("white_border_ok"), "霧", c.get("fog_px"),
              "裁切", c.get("raw_touches_edge"), "左右L差", c.get("lr_L_median_diff"),
              {n: (g and (g["L*"], g.get("dE_vs_master"))) for n, g in info[k].get("garments", {}).items()})
    info["a5_medics_v01"] = medics(ref)
    for k in ("a", "b"):
        c = info["a5_medics_v01"][k]["checks"]
        print("medic", k, info["a5_medics_v01"][k]["final"], "白邊", c.get("white_border_px"), c.get("white_border_ok"), "霧", c.get("fog_px"))
    info["a5_hosp_wall_v01"] = wall()
    (OUT / "import.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
