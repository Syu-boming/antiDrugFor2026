"""G4 美術：阿樂叔叔 a2 姿勢規劃與舌片檢查（沿用 tools/rig_ale_v03.py 的部件與合成，不改原檔）。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/ale_a2_poses.py [--fixed]
--fixed：改用 assets/final/rig/ 的修正部件（接縫修正＋乾淨困惑頭）。
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import rig_ale_v03 as R

# 工作台（舞台世界的物件，母版座標）：桌面上緣 y=TABLE_TOP，右端 x=TABLE_R
TABLE_TOP = 830
TABLE_R = 705
FLOOR = 1631

# a2 關鍵姿勢（度；正值＝畫面上順時針；root＝(dx, dy, 角度, 樞紐)）
POSES = {
    # a2_c001 結尾／a2_c002 開頭：坐在高凳上，右手靠在身體左外側的桌面上（腕、肘的線往上走都在身體外側，不橫過胸前與頭頸），左腿從桌子右端露出（膝蓋正面可見）
    "sit": {"root": (0, 80, 0, "hip_mid"), "upper_arm_r": 25, "forearm_r": 37, "hand_r": 18,
            "upper_arm_l": 10, "forearm_l": -14, "hand_l": 6,
            "thigh_l": -45, "shin_l": 45, "thigh_r": 40, "shin_r": -40, "head": 0},
    # 想揮手：右手舉起（手先抬起）
    "wave": {"root": (0, 80, 0, "hip_mid"), "upper_arm_r": 150, "forearm_r": 12, "hand_r": 6,
             "upper_arm_l": 10, "forearm_l": -14, "hand_l": 6,
             "thigh_l": -45, "shin_l": 45, "thigh_r": 40, "shin_r": -40, "head": 3},
    # 線繃緊、手被拉向旁邊（畫面左＝危險方位）
    "pulled": {"root": (0, 80, -2, "hip_mid"), "upper_arm_r": 92, "forearm_r": 18, "hand_r": -70,
               "upper_arm_l": 10, "forearm_l": -14, "hand_l": 6,
               "thigh_l": -45, "shin_l": 45, "thigh_r": 40, "shin_r": -40, "head": 2},
    # 想站起來（半站）：臀部抬高、身體前傾
    "halfstand": {"root": (8, 50, 4, "hip_mid"), "upper_arm_r": 92, "forearm_r": 18, "hand_r": -70,
                  "upper_arm_l": 4, "forearm_l": -10, "hand_l": 4,
                  "thigh_l": -38, "shin_l": 40, "thigh_r": 22, "shin_r": -24, "head": 2},
    # 膝蓋被線一扯：左膝被提起、腳離地、身體往後晃
    "kneetug": {"root": (0, 40, -5, "hip_mid"), "upper_arm_r": 96, "forearm_r": 16, "hand_r": -72,
                "upper_arm_l": -14, "forearm_l": -30, "hand_l": -10,
                "thigh_l": -68, "shin_l": 74, "thigh_r": 22, "shin_r": -24, "head": -3},
    # 扶住桌邊（停格）：左手掌心向下壓在桌子右端
    "hold": {"root": (4, 100, 2, "hip_mid"), "upper_arm_r": 94, "forearm_r": 18, "hand_r": -72,
             "upper_arm_l": -24, "forearm_l": -22, "hand_l": -58,
             "thigh_l": -52, "shin_l": 52, "thigh_r": 30, "shin_r": -30, "head": 4},
}


def table_layer(size, scale, offset):
    """佔位工作台（只做檢查用；正式圖由 manifest 定位）"""
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def P(x, y):
        return ((offset[0] + x) * scale, (offset[1] + y) * scale)
    d.rectangle([P(-900, TABLE_TOP), P(TABLE_R, FLOOR)], fill=(196, 150, 96, 255))
    d.rectangle([P(-900, TABLE_TOP), P(TABLE_R, TABLE_TOP + 48)], fill=(222, 190, 140, 255))
    return im


def load_rig(fixed):
    rig = R.Rig(head="worried")
    if fixed:
        meta = json.loads((ROOT / "assets/final/rig/ale_rig.json").read_text())
        for n, p in meta["parts"].items():
            im = Image.open(ROOT / "assets/final/rig" / p["file"]).convert("RGBA")
            ox, oy = p["origin_master"]
            key = "head" if n == "head_worried" else n
            if n == "head":
                continue
            rig.parts[key] = (im, (ox, oy))
    return rig


CHILD = {"shoulder_l": "upper_arm_l", "elbow_l": "forearm_l", "wrist_l": "hand_l", "shoulder_r": "upper_arm_r",
         "elbow_r": "forearm_r", "wrist_r": "hand_r", "knee_r": "shin_r", "knee_l": "shin_l", "hip_l": "thigh_l"}
ZH = {"shoulder_l": "左肩", "elbow_l": "左肘", "wrist_l": "左腕", "shoulder_r": "右肩", "elbow_r": "右肘", "wrist_r": "右腕",
      "knee_l": "左膝", "hip_l": "左髖"}


def render_pose(rig, name, with_table=True, scale=1.0):
    img, pt, Mw, pm = rig.render(POSES[name], outline=True, scale=scale, masks=False)
    if with_table:
        img.alpha_composite(table_layer(img.size, scale, R.OFFSET))
    return img, pt


def sheet(out, fixed):
    rig = load_rig(fixed)
    font = R.font
    names = list(POSES)
    cols = []
    att = json.loads((ROOT / "assets/final/rig/ale_attach.json").read_text())["points"] if fixed else {}
    for n in names:
        img, pt = render_pose(rig, n)
        bg = Image.new("RGBA", img.size, (236, 226, 206, 255))
        bg.alpha_composite(img)
        # 地板線
        d = ImageDraw.Draw(bg)
        # 操偶線扣點（腕背、肘外、膝前）＋往上的示意線
        for key, lean in (("wrist_back", -0.02), ("elbow_out", -0.02), ("knee_front", 0.19)):
            if key not in att:
                continue
            q = pt(att[key]["part"], att[key]["master_px"])
            d.line([tuple(q), (q[0] + lean * q[1], 0)], fill=(90, 86, 80, 255), width=9)
            d.line([tuple(q), (q[0] + lean * q[1], 0)], fill=(214, 210, 202, 255), width=5)
            d.ellipse([q[0] - 13, q[1] - 13, q[0] + 13, q[1] + 13], outline=(70, 66, 62, 255), width=6)
        fy = (R.OFFSET[1] + FLOOR)
        d.line([(0, fy), (bg.width, fy)], fill=(120, 100, 80, 255), width=3)
        body = bg.crop((R.OFFSET[0] - 380, 60, R.OFFSET[0] + 1100, R.OFFSET[1] + FLOOR + 20))
        sc = 640 / body.height
        body = body.resize((int(body.width * sc), 640), Image.LANCZOS)
        crops = []
        for j in ["shoulder_r", "elbow_r", "knee_l", "shoulder_l"]:
            c = pt(CHILD[j], R.PIV[j])
            box = (int(c[0] - 110), int(c[1] - 110), int(c[0] + 110), int(c[1] + 110))
            crops.append((j, bg.crop(box).resize((220, 220), Image.LANCZOS)))
        cols.append((n, body, crops))
    W = sum(max(b.width, 460) + 24 for _, b, _ in cols) + 24
    S = Image.new("RGB", (W, 1240), (44, 42, 40))
    d = ImageDraw.Draw(S)
    d.text((24, 10), f"阿樂叔叔 a2 姿勢規劃（{'修正部件 v04' if fixed else '原 ale_v03 部件'}）：坐高凳→想揮手→被拉偏→半站→膝被扯→扶桌；桌子為佔位色塊（右端 x={TABLE_R}、桌面 y={TABLE_TOP}）",
           font=font(22), fill=(240, 240, 240))
    x = 24
    for n, body, crops in cols:
        d.text((x, 44), n, font=font(24), fill=(240, 210, 120))
        S.paste(body.convert("RGB"), (x, 80))
        for i, (j, cr) in enumerate(crops):
            cx, cy = x + (i % 2) * 232, 740 + (i // 2) * 245
            S.paste(cr.convert("RGB"), (cx, cy))
            d.text((cx + 4, cy + 2), ZH[j], font=font(18), fill=(20, 20, 20))
        x += max(body.width, 460) + 24
    S.save(out)
    print("saved", out)


def solve_left_hand(pose, target, hand_total=-78, elbow="out"):
    """左手扶桌：在 pose 的軀幹位置下，找上臂、前臂角度讓左手腕落在 target。
    elbow="in"：手肘收在身體側（不往外撐，讓膝前線的走向淨空）；"out"：手肘往外。"""
    rig = R.Rig()
    best = None
    r1 = range(-10, 71, 1) if elbow == "in" else range(-70, 11, 1)
    r2 = range(-140, 21, 2) if elbow == "in" else range(-20, 141, 2)
    for a1 in r1:
        for a2 in r2:
            q = dict(pose); q["upper_arm_l"] = a1; q["forearm_l"] = a2
            M = rig.world(q)
            w = R.apply(M["forearm_l"], R.PIV["wrist_l"])
            e = R.apply(M["upper_arm_l"], R.PIV["elbow_l"])
            err = float(np.hypot(*(w - np.array(target))))
            score = err + (0.02 if elbow == "in" else -0.02) * e[0]
            if best is None or score < best[0]:
                best = (score, a1, a2, err)
    _, a1, a2, err = best
    pose["upper_arm_l"], pose["forearm_l"] = a1, a2
    pose["hand_l"] = hand_total - a1 - a2
    return err


IK_TARGETS = {"kneetug": ((640, 776), -62), "hold": ((598, 806), -84)}


def fit_right_leg(pose, floor=FLOOR - 4):
    """右腿被桌子擋住：只要腳底不穿過地板（小腿保持垂直），角度取最小的那個"""
    rig = R.Rig()
    ankle_to_sole = 1620 - 1490
    for th in range(10, 86, 1):
        q = dict(pose); q["thigh_r"] = th; q["shin_r"] = -th
        M = rig.world(q)
        a = R.apply(M["shin_r"], R.MJ["ankle_r"])
        if a[1] + ankle_to_sole <= floor:
            pose["thigh_r"], pose["shin_r"] = th, -th
            return th
    return None


def apply_ik():
    errs = {}
    for n, (tgt, tot) in IK_TARGETS.items():
        errs[n] = round(solve_left_hand(POSES[n], tgt, tot), 1)
    for n in POSES:
        fit_right_leg(POSES[n])
    return errs


if __name__ == "__main__":
    print("IK", apply_ik(), {n: {k: POSES[n][k] for k in ("upper_arm_l", "forearm_l", "hand_l")} for n in IK_TARGETS})
    fixed = "--fixed" in sys.argv
    out = ROOT / "review/G4/art" / ("ale_a2_poses_fixed.png" if fixed else "ale_a2_poses_before.png")
    sheet(out, fixed)
