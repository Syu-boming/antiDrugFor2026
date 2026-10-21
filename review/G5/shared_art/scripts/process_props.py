"""G5 共用美術：道具與邀請者（Codex 原檔）→ assets/generated → assets/final。

用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/process_props.py [raw_id ...]
- prop_inviter_v01：兩個連通區 → 左＝邀請者的手＋盒子（袖口被畫布左緣切掉，左側不留透明邊）
  → assets/final/chr-inviter_hand-box_v01.png；右＝盒子特寫 → assets/final/props/prop-sticker-box_v01.png
- prop_truck_v01（19:50 額度恢復後的生成圖）→ assets/final/props/prop-truck_v02.png（v01 是程式繪製退路版，保留）
- prop_bench_v01 → assets/final/props/prop-bench_v02.png（換圖要重量座面高 0.92、更新 layout.json 與 show_characters.json 坐姿 feet）
紀錄：review/G5/shared_art/import_props.json
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
RAW = ROOT / "review/G5/shared_art/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
PROPS = FIN / "props"
OUT = ROOT / "review/G5/shared_art"


def comps(a):
    lab, n = ndimage.label(a[..., 3] > 0)
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    return lab, objs, sizes


def save(a, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a, "RGBA").save(path, optimize=True)
    return str(path.relative_to(ROOT))


def inviter():
    raw = RAW / "prop_inviter_v01.png"
    gen = GEN / "chr-inviter_kit_v01.png"
    shutil.copyfile(raw, gen)
    rawa = np.array(Image.open(raw).convert("RGBA"))
    a, removed = L.clean_alpha(rawa, keep_largest=2)
    lab, objs, sizes = comps(a)
    order = sorted(range(len(objs)), key=lambda i: objs[i][1].start)
    recs = {"raw": str(raw.relative_to(ROOT)), "generated": str(gen.relative_to(ROOT)), "stray_px_removed": removed}
    for name, idx in (("hand", order[0]), ("box", order[1])):
        piece = a.copy()
        piece[lab != idx + 1, 3] = 0
        if name == "hand":
            crop, off = L.crop_pad(piece, 16, pad_left=0)
            path = FIN / "chr-inviter_hand-box_v01.png"
            exp = ("left",)
        else:
            crop, off = L.crop_pad(piece, 16)
            path = PROPS / "prop-sticker-box_v01.png"
            exp = ()
        rec = {"final": save(crop, path), "offset_from_source": list(off), "size": [int(crop.shape[1]), int(crop.shape[0])],
               "alpha_ref": L.alpha_ref(crop)}
        raw_piece = rawa.copy()
        raw_piece[lab != idx + 1, 3] = 0
        rec["checks"] = L.checks(crop, raw_piece, expect_touch=exp)
        if name == "hand":
            # 手掌上盒子的位置（給引擎：盒子中心、手掌托點），圖片像素
            al = crop[..., 3] >= 128
            h, s, v = L.hsv(crop[..., :3])
            gaudy = al & (s > 0.55) & (v > 0.6)
            ys, xs = np.nonzero(gaudy)
            rec["box_bbox_px"] = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
            rec["note"] = "左緣是袖口切口（畫布外延伸），引擎請把左緣放在畫面外或柱子後；左側沒有白邊是刻意的"
        recs[name] = rec
    return recs


def simple(raw_id, out_name, gen_name):
    raw = RAW / f"{raw_id}.png"
    gen = GEN / gen_name
    shutil.copyfile(raw, gen)
    rawa = np.array(Image.open(raw).convert("RGBA"))
    a, removed = L.clean_alpha(rawa, keep_largest=1)
    crop, off = L.crop_pad(a, 16)
    rec = {"raw": str(raw.relative_to(ROOT)), "generated": str(gen.relative_to(ROOT)), "stray_px_removed": removed,
           "final": save(crop, PROPS / out_name), "offset_from_source": list(off), "size": [int(crop.shape[1]), int(crop.shape[0])],
           "alpha_ref": L.alpha_ref(crop)}
    rec["checks"] = L.checks(crop, rawa)
    return rec, crop


def main():
    ids = sys.argv[1:] or ["prop_inviter_v01", "prop_truck_v01", "prop_bench_v01"]
    path = OUT / "import_props.json"
    info = json.loads(path.read_text()) if path.exists() else {}
    for k in ids:
        if not (RAW / f"{k}.png").exists():
            print(k, "原檔不存在")
            continue
        if k == "prop_inviter_v01":
            info[k] = inviter()
        elif k == "prop_truck_v01":
            info[k], _ = simple(k, "prop-truck_v02.png", "prop-truck_v02.png")   # v01＝程式繪製退路版，不覆寫
        elif k == "prop_bench_v01":
            info[k], _ = simple(k, "prop-bench_v02.png", "prop-bench_v02.png")   # 換圖後要重量座面高、更新 layout 與坐姿 feet
        print(k, json.dumps(info[k], ensure_ascii=False)[:600])
    path.write_text(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
