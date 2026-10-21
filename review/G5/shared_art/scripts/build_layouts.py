"""G5 共用美術：把景的擺位（review/G5/shared_art/sets/<景>_layout_source.json）寫成引擎正式格式
assets/final/sets/<景>/layout.json（format "antidrug-set/1"，見 app/SHOW_INTERFACE.md 第 5.3 節、app/src/sets/imageSet.ts）。

- y：圖片底邊的透明留白會讓景片浮起來，所以 y 一律減去「最低不透明列以下的留白」換算成的世界長度（景片的實際底邊落在地面）。
- popup：由遠到近依序立起（set.popup 進度 0–1）。
- 以 "_" 開頭的欄位是給人看的說明（引擎不讀）。
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/build_layouts.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "review/G5/shared_art/sets"


def bottom_pad(path):
    a = np.array(Image.open(ROOT / path).convert("RGBA"))
    rows = np.nonzero((a[..., 3] >= 128).any(1))[0]
    return a.shape[0] - 1 - rows.max(), a.shape[0]


def short(pid, setname):
    pre = f"sets/{setname}/"
    return pid[len(pre):] if pid.startswith(pre) else pid


def convert(setname, title, cams, marks, landmarks, grade, extra_emissive=None):
    src = json.loads((SRC / f"{setname}_layout_source.json").read_text())
    pieces = [p for p in src["pieces"]]
    wall_p = next(p for p in pieces if p["layer"] == "backdrop")
    layers = []
    rest = [p for p in pieces if p is not wall_p] + [dict(p, layer=p.get("layer", "mid")) for p in src.get("props", [])]
    rest.sort(key=lambda p: p["z"])
    n = len(rest)
    for i, p in enumerate(rest):
        pad, H = bottom_pad(p["file"])
        h = p["height"]
        y = round(p["y"] - pad / H * h, 3)
        L = {"id": p["id"].split("/")[-1].replace("set-" + setname + "_", "").replace("set-square_", "sq-"), "image": short(p["id"], setname),
             "x": p["x"], "y": y, "z": p["z"], "width": p["width"], "layer": "mid" if p["layer"] == "actors" else p["layer"]}
        a0 = round(0.05 + 0.8 * i / max(1, n), 2)
        L["popup"] = [a0, round(min(1.0, a0 + 0.22), 2)]
        if extra_emissive and L["id"] in extra_emissive:
            L["emissive"] = extra_emissive[L["id"]]
        if p.get("note"):
            L["_note"] = p["note"]
        for k in ("window_hole_world", "wheels", "seat_world_y"):
            if k in p:
                L["_" + k] = p[k]
        layers.append(L)
    # 同一張圖用兩次（門柱）時 id 要分開
    seen = {}
    for L in layers:
        if L["id"] in seen:
            seen[L["id"]] += 1
            L["id"] = f"{L['id']}-{seen[L['id']]}"
        else:
            seen[L["id"]] = 1
    pad, H = bottom_pad(wall_p["file"])
    out = {
        "format": "antidrug-set/1",
        "title": title,
        "wall": {"image": short(wall_p["id"], setname), "width": wall_p["width"], "y": wall_p["y"], "z": wall_p["z"], "emissive": 0.32},
        "floor": ({"image": short(src["floor"]["id"], setname), "repeat": [1, 1], "width": src["floor"]["world_width"], "depth": src["floor"]["world_depth"],
                   "z": src["floor"]["center"][2] + src["floor"]["world_depth"] / 2, "color": "#ddd3c0"}
                  if src["floor"].get("id") else {"color": src["floor"]["color"], "z": 7.0, "depth": 12}),
        "layers": layers,
        "grade": grade,
        "marks": marks,
        "landmarks": landmarks,
        "cameras": cams,
        "_made_by": "review/G5/shared_art/scripts/build_layouts.py（G5 共用美術代理）；擺位來源 review/G5/shared_art/sets/" + setname + "_layout_source.json",
        "_coords": src["coords"],
        "_staging": src.get("staging") or src.get("lighting"),
        "_lighting": src.get("lighting"),
        "_floor_note": src["floor"].get("note"),
        "_preview": f"review/G5/shared_art/sets/{setname}_preview_*.png（Python 近似預覽，不是引擎擷取）",
    }
    (ROOT / f"assets/final/sets/{setname}/layout.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main():
    gate_src = json.loads((SRC / "gate_layout_source.json").read_text())
    hole = gate_src["staging"]["guard_window"]["world"]
    truck = next(p for p in gate_src["props"] if p["id"] == "props/prop-truck")
    gi = json.loads((SRC / "gate_import.json").read_text())
    tW, tH = gi["truck"]["size"]
    tup = truck["width"] / tW
    ear = gi["truck"]["cat_ear_tip_px_in_final"]
    pad, _ = bottom_pad(truck["file"])
    ear_w = [round(truck["x"] + (ear[0] - tW / 2) * tup, 3), round((tH - ear[1]) * tup - pad * tup, 3), truck["z"]]
    bench = next(p for p in gate_src["props"] if p["id"] == "props/prop-bench")
    convert(
        "gate", "校門口（放學接送區）",
        cams={
            "gate_wide": {"pos": [0, 3.6, 27], "target": [0, 3.2, 0], "fov": 20},
            "gate_mid": {"pos": [-0.2, 1.7, 17.5], "target": [-0.2, 1.5, 0], "fov": 20},
            "gate_inside": {"pos": [3.3, 1.5, 13.5], "target": [3.3, 1.35, 0], "fov": 20},
            "gate_bench": {"pos": [-3.3, 1.45, 13.5], "target": [-3.3, 1.25, 0], "fov": 20},
            "gate_truck_window": {"pos": [ear_w[0] + 0.25, ear_w[1] + 0.1, ear_w[2] + 10.5], "target": [ear_w[0], ear_w[1] - 0.15, ear_w[2]], "fov": 20},
        },
        marks={"xiaoqing": {"x": 2.7, "z": 0.35}, "xiaoyu": {"x": 3.6, "z": 0.1}, "lin": {"x": 4.6, "z": 0.3}, "chen": {"x": -1.9, "z": 0.25},
               "ale": {"x": bench["x"], "z": bench["z"] + 0.2}, "pinan": {"x": 1.0, "z": -0.2}},
        landmarks={"benchSeat": {"x0": round(bench["x"] - 1.45, 3), "x1": round(bench["x"] + 1.45, 3), "y": 0.92, "z": bench["z"]},
                   "pickupLine": {"x0": 1.6, "x1": 1.6, "y": 0, "z": 0},
                   "guardWindow": {"x0": hole["x0"], "x1": hole["x1"], "y": round((hole["y0"] + hole["y1"]) / 2, 3), "z": -0.95},
                   "truckCatEar": {"x0": ear_w[0], "x1": ear_w[0], "y": ear_w[1], "z": ear_w[2]}},
        grade={"preset": "day_warm"},
    )
    sq_src = json.loads((SRC / "square_layout_source.json").read_text())
    sq_src["props"] = [q for q in sq_src.get("props", []) if q["id"] != "props/prop-bench"]
    sq_src["props"].append({"id": "props/prop-bench", "file": bench["file"], "layer": "mid", "x": -2.4, "y": 0, "z": 0.0,
                                           "width": bench["width"], "height": bench["height"], "seat_world_y": 0.92,
                                           "note": "品安 P-PA1 坐的長椅（座面 0.92；品安站位 z 要大於 0.0）"})
    (SRC / "square_layout_source.json").write_text(json.dumps(sq_src, ensure_ascii=False, indent=1))
    convert(
        "square", "小鎮廣場（紙燈節）",
        cams={
            "square_wide": {"pos": [0, 3.6, 27], "target": [0, 3.2, 0], "fov": 20},
            "square_mid": {"pos": [0.3, 1.7, 17.5], "target": [0.3, 1.5, 0], "fov": 20},
            "square_bench": {"pos": [-2.2, 1.4, 13], "target": [-2.2, 1.2, 0], "fov": 20},
        },
        marks={"pinan": {"x": -2.4, "z": 0.2}, "xiaoqing": {"x": 0.4, "z": 0.35}, "xiaoyu": {"x": 1.5, "z": 0.1}, "ye": {"x": 4.6, "z": 0.2}},
        landmarks={"benchSeat": {"x0": -3.85, "x1": -0.95, "y": 0.92, "z": 0.0}},
        grade={"preset": "day_warm"},
        extra_emissive={"sq-arcade": 0.3, "sq-backrow": 0.2},
    )
    for s in ("gate", "square"):
        j = json.loads((ROOT / f"assets/final/sets/{s}/layout.json").read_text())
        print(s, len(j["layers"]), "layers;", [L["id"] for L in j["layers"]])


if __name__ == "__main__":
    main()
