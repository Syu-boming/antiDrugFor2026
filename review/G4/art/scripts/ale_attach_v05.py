"""G4 修正第 1 輪（美術，問題 23、27）：阿樂分件 rig／扣點 v05。

1. assets/final/rig/ale_rig_v05.json：內容同 ale_rig.json（v04），只把前臂兩件換成 v05 檔（fix_forearms_v05.py；
   尺寸、樞紐、座標都不變），並在 fix_log 記錄。打包 id 仍是 rig/ale_rig（tools/pack.mjs 取最新版本）。
2. assets/final/rig/ale_attach_v05.json：扣點改成「整個紙環都落在肢體剪影內」。
   紙環直徑建議 0.103 世界單位（≈ 2.4 × 線寬 0.043），換算阿樂母版約 46 px（半徑 23 px）；
   每個扣點都放在距外形邊緣 ≥ 26 px（半徑＋3 px）的位置，並盡量靠語意上的那一側（腕背＝外側、肘外＝外側、膝前＝膝頭中央）。
   手腕扣點的紙環下緣留在手腕圓舌片（被手蓋住）上方 ≥ 12 px。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/ale_attach_v05.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
RIG = ROOT / "assets/final/rig"
ART = ROOT / "review/G4/art"

STRING_WIDTH_WORLD = 0.043
RING_D_WORLD = 0.103
ALE_HEIGHT_WORLD = 3.55          # app/src/stage/cast.ts BUILTIN_RIGS.ale_v03.height
MARGIN = 3


def main():
    rig = json.loads((RIG / "ale_rig.json").read_text())
    fx = json.loads((ART / "forearm_fix_v05.json").read_text())
    rig5 = json.loads(json.dumps(rig))
    rig5["source"] = rig["source"] + " → G4 修正第 1 輪 v05（前臂補線稿與紙紋、移除袖口零碎紙邊）"
    for r in fx:
        p = rig5["parts"][r["part"]]
        p["file"] = r["file_v05"]
        p["outline_file"] = r["outline_v05"]
    rig5.setdefault("fix_log", {})["forearms_v05"] = fx
    rig5["version"] = "v05"
    # 世界尺度：o.height / (floorY - topY)（app/src/stage/imagerig.ts）
    tops, floors = [], []
    for n, p in rig["parts"].items():
        if n == "head_worried":
            continue
        tops.append(p["origin_master"][1])                      # 引擎用含透明邊的 bbox
        if n.startswith("shin"):
            floors.append(p["origin_master"][1] + p["size"][1])
    s = ALE_HEIGHT_WORLD / (max(floors) - min(tops))
    R = RING_D_WORLD / s / 2
    need = R + MARGIN

    def mask(part, rigj):
        p = rigj["parts"][part]
        return np.array(Image.open(RIG / p["file"]).convert("RGBA"))[..., 3] > 127, p

    def place(part, y_local, side, rigj, y_max=None):
        """在 y_local（可上下微調 ±60 px，越近越好）找最靠 side（-1 左、+1 右、0 中央）且 dt ≥ need 的點"""
        m, p = mask(part, rigj)
        dt = ndimage.distance_transform_edt(m)
        best = None
        for dy in range(0, 61):
            for y in ((y_local - dy, y_local + dy) if dy else (y_local,)):
                y = int(round(y))
                if y_max is not None and y > y_max:
                    continue
                row = np.nonzero(dt[y] >= need)[0]
                if not len(row):
                    continue
                x = row.min() if side < 0 else row.max() if side > 0 else int(round((row.min() + row.max()) / 2))
                best = (float(x), float(y), float(dt[y, x]))
                break
            if best:
                break
        return best, p

    old = json.loads((RIG / "ale_attach.json").read_text())
    pts = {}
    hand = {"forearm_r": "hand_r", "forearm_l": "hand_l"}
    spec = {
        "wrist_back": ("forearm_r", -1, "右手腕背側（前臂靠手腕，外側；整個紙環在前臂剪影內、在手的上方）"),
        "elbow_out": ("upper_arm_r", -1, "右手肘外側（上臂靠手肘的袖子上，外側；不扣手肘內側）"),
        "knee_front": ("thigh_l", 0, "左膝蓋正面（膝頭中央，整個紙環在膝蓋輪廓內；坐姿時從桌子右端露出）"),
        "wrist_back_l": ("forearm_l", 1, "左手腕背側（外側＝畫面右緣）"),
        "elbow_out_l": ("upper_arm_l", 1, "左手肘外側"),
        "knee_front_r": ("thigh_r", 0, "右膝蓋正面（a2 坐姿被桌子擋住）"),
    }
    for k, (part, side, zh) in spec.items():
        o = old["points"][k]
        y0 = o["local_px"][1]
        y_max = None
        if part in hand:
            hp = rig["parts"][hand[part]]
            wj_y = hp["pivot_master"][1] - rig["parts"][part]["origin_master"][1]
            y_max = wj_y - 30 - R            # 紙環下緣在手腕圓舌片（半徑約 30）上方
            y0 = min(y0, y_max)
        if part.startswith("upper_arm"):
            y0 = y0 - 14                     # 往上移到捲袖口上方的袖子
        (x, y, d), p = place(part, y0, side, rig5, y_max)
        pv = p["pivot_local"]
        ox, oy = p["origin_master"]
        pts[k] = {"part": part, "image_id": p["image_id"], "local_px": [x, y], "master_px": [x + ox, y + oy],
                  "from_pivot_px": [round(x - pv[0], 1), round(y - pv[1], 1)], "zh": zh, "primary": o["primary"],
                  "edge_distance_px": round(d, 1), "v04_local_px": o["local_px"]}
    out = {
        "version": "v05",
        "rig": "assets/final/rig/ale_rig_v05.json",
        "coords": old["coords"].replace("_v04.png", "_v05.png（前臂）／_v04.png（其他）"),
        "safety": old["safety"],
        "ring": {
            "texture_image_id": "tex-string-ring",
            "rope_texture_image_id": "tex-string-rope",
            "shape": "紙環＝圓環（外深灰細線＋白紙芯邊＋淡灰紙環身＋內深灰細線，中間透明），正對鏡頭、不隨肢體旋轉；不用矩形帶、鉚釘或扁板",
            "diameter_world": RING_D_WORLD,
            "diameter_master_px": round(2 * R, 1),
            "string_width_world": STRING_WIDTH_WORLD,
            "px_at_1080p": {"g4_mid（16.4 單位，186.8 px/單位）": {"線寬": round(STRING_WIDTH_WORLD * 186.8, 1), "紙環直徑": round(RING_D_WORLD * 186.8, 1)},
                            "錨點近景（12.5 單位，245 px/單位）": {"線寬": round(STRING_WIDTH_WORLD * 245, 1), "紙環直徑": round(RING_D_WORLD * 245, 1)}},
            "rope_end": "線的下端停在紙環上緣（扣點往線的方向退 0.4×直徑），看起來是繩子綁在紙環上；紙環畫在部件與線的上面",
            "inside_rule": f"每個扣點離部件外形邊緣 ≥ {need:.1f} 母版 px（紙環半徑 {R:.1f}＋{MARGIN}），所以整個紙環都在肢體剪影內",
        },
        "a2_primary": old["a2_primary"],
        "string_direction_hint": old["string_direction_hint"],
        "points": pts,
    }
    (RIG / "ale_rig_v05.json").write_text(json.dumps(rig5, ensure_ascii=False, indent=1))
    (RIG / "ale_attach_v05.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("scale world/px", round(s, 6), "ring R px", round(R, 1))
    print(json.dumps({k: (v["part"], v["v04_local_px"], "→", v["local_px"], v["edge_distance_px"]) for k, v in pts.items()}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
