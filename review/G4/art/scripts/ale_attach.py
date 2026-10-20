"""操偶線扣點 assets/final/rig/ale_attach.json（腕背、肘外、膝前；部件局部像素座標）。"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[4]
RIG = ROOT / "assets/final/rig"
meta = json.loads((RIG / "ale_rig.json").read_text())


def alpha(part):
    p = meta["parts"][part]
    return np.array(Image.open(RIG / p["file"]))[..., 3] > 128, p


def edge_point(part, y_master, side, inset):
    """在母版高度 y_master 找部件外側（side=-1 畫面左緣、+1 畫面右緣）邊緣，往內 inset px"""
    a, p = alpha(part)
    ox, oy = p["origin_master"]
    row = a[int(round(y_master - oy))]
    xs = np.nonzero(row)[0]
    x = (xs.min() + inset) if side < 0 else (xs.max() - inset)
    return [float(x), float(y_master - oy)], [float(x + ox), float(y_master)]


def center_point(part, y_master):
    a, p = alpha(part)
    ox, oy = p["origin_master"]
    row = a[int(round(y_master - oy))]
    xs = np.nonzero(row)[0]
    x = (xs.min() + xs.max()) / 2
    return [float(x), float(y_master - oy)], [float(x + ox), float(y_master)]


def rec(name, part, local, master, zh, primary):
    p = meta["parts"][part]
    pv = p["pivot_local"]
    return {"part": part, "image_id": p["image_id"], "local_px": [round(local[0], 1), round(local[1], 1)],
            "master_px": [round(master[0], 1), round(master[1], 1)],
            "from_pivot_px": [round(local[0] - pv[0], 1), round(local[1] - pv[1], 1)],
            "zh": zh, "primary": primary}


pts = {}
# 右臂（畫面左側；a2_c001 的 L1 細線就在右手腕背）：外側＝畫面左緣
l, m = edge_point("forearm_r", 812, -1, 9); pts["wrist_back"] = rec("wrist_back", "forearm_r", l, m, "右手腕背側（前臂靠手腕、外側緣往內 9 px）", True)
l, m = edge_point("upper_arm_r", 628, -1, 10); pts["elbow_out"] = rec("elbow_out", "upper_arm_r", l, m, "右手肘外側（上臂靠手肘、外側緣往內 10 px；不扣手肘內側）", True)
l, m = center_point("thigh_l", 1236); pts["knee_front"] = rec("knee_front", "thigh_l", l, m, "左膝蓋正面（大腿下端膝頭中央；坐姿時從桌子右端露出）", True)
# 另一側（a2 代表鏡頭不用；後段 6 條線全上時用）
l, m = edge_point("forearm_l", 822, +1, 9); pts["wrist_back_l"] = rec("wrist_back_l", "forearm_l", l, m, "左手腕背側（外側＝畫面右緣）", False)
l, m = edge_point("upper_arm_l", 628, +1, 9); pts["elbow_out_l"] = rec("elbow_out_l", "upper_arm_l", l, m, "左手肘外側", False)
l, m = center_point("thigh_r", 1236); pts["knee_front_r"] = rec("knee_front_r", "thigh_r", l, m, "右膝蓋正面（a2 坐姿被桌子擋住）", False)
out = {
    "version": "v04", "rig": "assets/final/rig/ale_rig.json",
    "coords": "local_px＝部件圖（assets/final/rig/chr-ale_<部件>_v04.png）左上角起算的像素，y 向下；from_pivot_px＝相對該部件樞紐；master_px＝母版座標。",
    "safety": "只扣手腕背側、手肘外側、膝蓋正面（兒童安全界線第 2 條）；線往上延伸出畫面；不繞脖子、不接頭胸腰；不畫操控者。",
    "ring": "紙環由劇場程式畫（淡灰紙繩＋深灰邊），環的直徑約為前臂寬的 0.55；扣點在部件邊緣往內，環不會懸空。",
    "a2_primary": ["wrist_back", "elbow_out", "knee_front"],
    "string_direction_hint": {"wrist_back": "往上偏畫面左（危險方位）", "elbow_out": "往上偏畫面左", "knee_front": "近乎垂直往上，走身體外側（畫面右），不經過頭頸"},
    "points": pts,
}
(RIG / "ale_attach.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({k: (v["part"], v["local_px"], v["master_px"]) for k, v in pts.items()}, ensure_ascii=False))
