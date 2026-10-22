"""第三幕（a3）修正第 2 輪美術：兩張 Codex 原檔 → assets/generated（原樣、加版本號）→ assets/final（去雜點、裁透明邊＋16 px）。

  raw/pose_lin_phone_v01.png      → assets/final/chr-lin_pose-phone_v01.png（林老師朝右、手機貼耳；a3_c008 走出教室前）
  raw/set_a3_classmates_v01.png   → assets/final/sets/a3_classroom/classmate-a_v01.png、classmate-b_v01.png
                                    （教室後排兩個同學的背影，同畫風、不透明、有紙纖維；取代 students_v02 的幾何背影）
並把林老師的新姿勢登記到 assets/final/rig/show_characters.json 的 lin.poses.phone（只加這一筆；讀、改、寫暫存檔再搬回）。
自動檢查（g5lib.checks：霧邊、白邊、裁切、左右 L*）＋酒紅毛衣 ΔE（對母版）寫到 review/G5/a3/import.json。

用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/build_a3_fix2_art.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import g5lib as L  # noqa: E402
from process_chars import GARMENTS  # noqa: E402  （只讀共用設定）

RAW = ROOT / "review/G5/a3/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
OUT = ROOT / "review/G5/a3"


def rel(p):
    return str(Path(p).relative_to(ROOT))


def finish(a, dst, raw=None):
    a, removed = L.clean_alpha(a)
    crop, off = L.crop_pad(a, 16)
    Image.fromarray(crop, "RGBA").save(dst, optimize=True)
    al = crop[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]
    return crop, {"final": rel(dst), "size": [int(crop.shape[1]), int(crop.shape[0])], "offset_from_source": list(off),
                  "stray_px_removed": removed, "height_px": int(rows.max() - rows.min() + 1),
                  "checks": L.checks(crop, raw)}


def lin_phone():
    raw = RAW / "pose_lin_phone_v01.png"
    gen = GEN / "chr-lin_pose-phone_v01.png"
    shutil.copyfile(raw, gen)
    a = np.array(Image.open(raw).convert("RGBA"))
    crop, rec = finish(a, FIN / "chr-lin_pose-phone_v01.png", a)
    rec.update({"raw": rel(raw), "generated": rel(gen), "character": "lin", "part": "pose-phone"})
    master = np.array(Image.open(FIN / "chr-lin_master_v01.png").convert("RGBA"))
    gs = {}
    for g in GARMENTS["lin"]:
        st = L.garment_stats(crop, g[1], g[2], g[3], g[4], g[5])
        ref = L.garment_stats(master, g[1], g[2], g[3], g[4], g[5])
        if st and ref:
            st["dE_vs_master"] = L.delta_e(st["lab"], ref["lab"])
        gs[g[0]] = st
    rec["garments"] = gs
    return rec


def classmates():
    raw = RAW / "set_a3_classmates_v01.png"
    gen = GEN / "set-a3-classroom_classmates_v01.png"
    shutil.copyfile(raw, gen)
    a = np.array(Image.open(raw).convert("RGBA"))
    a, removed = L.clean_alpha(a)
    lab, n = ndimage.label(a[..., 3] > 0)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    big = [1 + i for i in np.argsort(sizes)[::-1][:2]]
    xs = {k: float(np.nonzero(lab == k)[1].mean()) for k in big}
    recs = {"raw": rel(raw), "generated": rel(gen), "stray_px_removed": removed, "pieces": {}}
    for name, k in zip(("a", "b"), sorted(big, key=lambda k: xs[k])):
        piece = a.copy()
        piece[lab != k, 3] = 0
        _, rec = finish(piece, FIN / f"sets/a3_classroom/classmate-{name}_v01.png", None)
        recs["pieces"][name] = rec
    return recs


def register_pose():
    """show_characters.json：lin.poses.phone（只加這一筆，其他欄位原樣；寫暫存檔、驗證 JSON 再搬回）"""
    path = FIN / "rig/show_characters.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    poses = d["characters"]["lin"].setdefault("poses", {})
    if poses.get("phone", {}).get("image") == "chr-lin_pose-phone":
        return "已登記"
    poses["phone"] = {"image": "chr-lin_pose-phone"}
    note = d["characters"]["lin"].get("_note", "")
    if "phone＝" not in note:
        d["characters"]["lin"]["_note"] = note + " phone＝朝右、手機貼耳講電話（a3_c008 走出教室前；第三幕修正第 2 輪 Codex）。"
    txt = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    json.loads(txt)
    fd, tmp = tempfile.mkstemp(prefix="show_characters_", suffix=".json", dir=str(OUT))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(txt)
    json.loads(Path(tmp).read_text(encoding="utf-8"))
    os.replace(tmp, path)
    return "新增 lin.poses.phone"


def main():
    path = OUT / "import.json"
    info = json.loads(path.read_text()) if path.exists() else {}
    info["pose_lin_phone_v01"] = lin_phone()
    info["set_a3_classmates_v01"] = classmates()
    path.write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str))
    c = info["pose_lin_phone_v01"]["checks"]
    print("lin phone", info["pose_lin_phone_v01"]["size"], "白邊", c.get("white_border_px"), c.get("white_border_ok"), "霧", c.get("fog_px"),
          "裁切", c.get("raw_touches_edge"), "左右L差", c.get("lr_L_median_diff"),
          {k: (v and (v.get("L*"), v.get("dE_vs_master"))) for k, v in info["pose_lin_phone_v01"]["garments"].items()})
    for k, r in info["set_a3_classmates_v01"]["pieces"].items():
        c = r["checks"]
        print("classmate", k, r["size"], "白邊", c.get("white_border_px"), c.get("white_border_ok"), "霧", c.get("fog_px"), "左右L差", c.get("lr_L_median_diff"))
    print(register_pose())


if __name__ == "__main__":
    main()
