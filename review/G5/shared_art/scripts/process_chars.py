"""G5 共用美術：角色立牌（Codex 原檔）→ assets/generated（加版本號；兒童主色同色相調回 v04 色票）→ assets/final（去雜點、裁透明邊＋16 px、顏色外擴）。

用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/process_chars.py [raw_id ...]
- 原檔：review/G5/shared_art/raw/<raw_id>.png（不改）
- 兒童（小晴、小宇）：主色 L* 和 v04 母版差 > 1 時用 tools/recolor_garment.recolor 調回（D-G2-06：吊帶褲 L* 37、外套 L* 39，a*、b* 不動）
- 輸出紀錄：review/G5/shared_art/import.json（裁切位移、尺寸、腳底、主色、雜點數、自動檢查）
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
sys.path.insert(0, str(ROOT / "tools"))
RAW = ROOT / "review/G5/shared_art/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
OUT = ROOT / "review/G5/shared_art"

XQ_SPEC = [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, (0.0, 1.0), 37.0)]
XY_SPEC = [("橘紅外套", (345, 22), 0.55, 0.25, (0.15, 0.78), 39.0)]

# raw_id → (角色, 檔名部件, 種類, 主色量測 [(名稱, 色相範圍, s_min, v_min, v_max, 身高帶)], 調色規格)
JOBS = {
    "pose_xq_cross_v06": ("xiaoqing", "pose-cross", "kid", XQ_SPEC),
    "pose_xq_palmno_v06": ("xiaoqing", "pose-palmno", "kid", XQ_SPEC),
    "pose_xq_forehead_v06": ("xiaoqing", "pose-forehead", "kid", XQ_SPEC),
    "pose_xq_walk_v06": ("xiaoqing", "pose-walk", "kid", XQ_SPEC),
    "pose_xy_cross_v06": ("xiaoyu", "pose-cross", "kid", XY_SPEC),
    "pose_xy_palmno_v06": ("xiaoyu", "pose-palmno", "kid", XY_SPEC),
    "pose_xy_forehead_v06": ("xiaoyu", "pose-forehead", "kid", XY_SPEC),
    "pose_xy_walk_v06": ("xiaoyu", "pose-walk", "kid", XY_SPEC),
    "pose_xy_watch_v06": ("xiaoyu", "pose-watch-dial", "kid", XY_SPEC),
    "chr_pinan_stand_v01": ("pinan", "master", "new", None),
    "chr_pinan_sit_v01": ("pinan", "pose-sit-lantern", "new", None),
    "chr_pinan_walk_v01": ("pinan", "pose-walk-straps", "new", None),
    "chr_lin_stand_v01": ("lin", "master", "new", None),
    "chr_lin_crouch_v01": ("lin", "pose-crouch", "new", None),
    "chr_lin_sit_v01": ("lin", "pose-sit", "new", None),
    "chr_chen_stand_v01": ("chen", "master", "new", None),
    "chr_ye_stand_v01": ("ye", "master", "new", None),
    "chr_ye_crouch_v01": ("ye", "pose-crouch", "new", None),
}

# 主色量測（色相範圍、s 下限、v 下限、v 上限、身高帶）與參考色（Lab；兒童＝v04 母版實量）
GARMENTS = {
    "xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, 1.0, (0.3, 1.0)), ("芥末黃上衣", (35, 55), 0.5, 0.5, 1.0, (0.2, 0.5))],
    "xiaoyu": [("橘紅外套", (345, 22), 0.55, 0.25, 0.95, (0.15, 0.6)), ("卡其短褲", (25, 45), 0.2, 0.4, 0.85, (0.5, 0.75))],
    "pinan": [("茄紫上衣", (280, 345), 0.15, 0.12, 0.7, (0.15, 0.6)), ("橄欖綠書包", (55, 95), 0.2, 0.15, 0.7, (0.1, 0.6))],
    "lin": [("酒紅毛衣", (330, 15), 0.3, 0.15, 0.8, (0.12, 0.6))],
    "chen": [("黃綠背心", (55, 95), 0.4, 0.4, 1.0, (0.15, 0.6)), ("淺灰制服", (0, 360), 0.0, 0.55, 0.9, (0.12, 0.45))],
    "ye": [("鼠尾草綠護理服", (70, 160), 0.08, 0.35, 0.85, (0.15, 0.55))],
}


def master_ref_lab():
    ref = {}
    for cid, f in (("xiaoqing", "chr-xiaoqing_master_v04.png"), ("xiaoyu", "chr-xiaoyu_master_v04.png")):
        a = np.array(Image.open(FIN / f).convert("RGBA"))
        ref[cid] = {g[0]: L.garment_stats(a, g[1], g[2], g[3], g[4], g[5]) for g in GARMENTS[cid]}
    return ref


def process(raw_id, ref):
    cid, part, kind, spec = JOBS[raw_id]
    raw = RAW / f"{raw_id}.png"
    if not raw.exists():
        return {"error": "原檔不存在"}
    ver = raw_id.rsplit("_", 1)[1]
    gen = GEN / f"chr-{cid}_{part}_{ver}.png"
    rec = {"raw": str(raw.relative_to(ROOT)), "character": cid, "part": part}
    if spec:
        import recolor_garment as RG
        a0 = np.array(Image.open(raw).convert("RGBA"))
        g0 = L.garment_stats(a0, spec[0][1], spec[0][2], spec[0][3], 1.0, spec[0][4])
        rec["raw_main_L*"] = g0 and g0["L*"]
        if g0 and abs(g0["L*"] - spec[0][5]) > 1.0:
            # recolor() 讀 GEN 下的檔名：先把原檔複製成暫存名
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
    ids = sys.argv[1:] or [k for k in JOBS if (RAW / f"{k}.png").exists()]
    path = OUT / "import.json"
    info = json.loads(path.read_text()) if path.exists() else {}
    ref = master_ref_lab()
    info["_v04_reference"] = ref
    for k in ids:
        info[k] = process(k, ref)
        c = info[k].get("checks", {})
        print(k, info[k].get("final"), "白邊", c.get("white_border_px"), c.get("white_border_ok"), "霧", c.get("fog_px"),
              "裁切", c.get("raw_touches_edge"), "左右L差", c.get("lr_L_median_diff"),
              {n: (g and (g["median"], g["L*"], g.get("dE_vs_v04"))) for n, g in info[k].get("garments", {}).items()})
    path.write_text(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
