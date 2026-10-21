"""G5 共用美術：校門口分層景（第三、四、五幕共用）＋長椅、小貨車道具 —— 程式繪製的厚卡紙景片（退路版）。

為什麼是程式繪製：2026-10-21 15:01 啟動的 image_gen（Codex，ChatGPT 額度）全部回「usage limit，19:50 後再試」。
提示已寫好（review/G5/shared_art/raw/set_gate_*_v01.prompt.txt、prop_truck_v01、prop_bench_v01），額度恢復後可用 _run.sh 重抽，
抽到的圖替換同 id 的檔案即可（版本號 v02，tools/pack.mjs 取最新版）。
畫法：平塗色塊＋G2 景片同款紙紋（paperdraw.py）、暖深灰細線、無陰影無方向光、無任何文字／校徽／品牌。
在地元素（v1.2 §14.3）：校門柱、伸縮門、警衛室、三層樓走廊式校舍、對街騎樓（沿用 G2 廣場的後排騎樓）、行道樹、斑馬線、接送線。
輸出：assets/final/sets/gate/set-gate_<件名>_v01.png、layout.draft.json；assets/final/props/prop-bench_v01.png、prop-truck_v01.png、prop-truck-wheel_v01.png
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/build_gate.py
"""
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paperdraw as P  # noqa: E402

ROOT = P.ROOT
GATE = ROOT / "assets/final/sets/gate"
PROPS = ROOT / "assets/final/props"
PPU = 150

CREAM = (239, 227, 198, 255)
CREAM2 = (244, 234, 211, 255)
CORRIDOR = (240, 231, 210, 255)
TERRA = (230, 186, 158, 255)
TILE = (196, 132, 98, 255)
GLASS = (206, 223, 226, 255)
LEAF = (126, 158, 98, 255)
LEAF2 = (104, 138, 84, 255)
STONE = (216, 209, 194, 255)
STONE2 = (205, 196, 178, 255)


def school_building():
    W, H = 12 * PPU, int(5.4 * PPU)
    s = P.Sheet(W, H)
    # 屋頂女兒牆
    s.rect(0, 30, W, 70, CREAM2)
    s.rect(0, 22, W, 34, TILE, line=1.5)
    floor_h = (H - 70) // 3
    bays = 8
    bw = W / bays
    for f in range(3):
        y0 = 70 + f * floor_h
        y1 = y0 + floor_h
        s.rect(0, y0, W, y1, CORRIDOR, line=1.5)
        for b in range(bays):
            bx = b * bw
            # 每格兩扇窗（上半部）
            for k in (0.22, 0.58):
                wx0, wx1 = bx + bw * k, bx + bw * (k + 0.24)
                wy0, wy1 = y0 + 28, y0 + 28 + floor_h * 0.42
                s.rect(wx0 - 6, wy0 - 6, wx1 + 6, wy1 + 6, CREAM2, line=1.5)
                s.rect(wx0, wy0, wx1, wy1, GLASS, line=1.5)
                s.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], 2)
                s.line([(wx0, (wy0 + wy1) / 2), (wx1, (wy0 + wy1) / 2)], 2)
            if f == 2 and b in (2, 5):
                # 一樓兩扇門（淺木色）
                s.rect(bx + bw * 0.3, y1 - floor_h * 0.62, bx + bw * 0.7, y1, (206, 182, 142, 255), line=1.5)
                s.line([(bx + bw * 0.5, y1 - floor_h * 0.62), (bx + bw * 0.5, y1)], 1.5)
        # 柱
        for b in range(bays + 1):
            px = min(max(b * bw, 14), W - 14)
            s.rect(px - 14, y0, px + 14, y1, CREAM2, line=1.5)
        if f < 2:
            # 二、三樓走廊欄杆（矮牆＋米色壓頂）與盆栽
            ry0 = y1 - 62
            s.rect(0, ry0, W, y1, TERRA, line=1.5)
            s.rect(0, ry0 - 10, W, ry0 + 2, CREAM2, line=1.5)
            rnd = random.Random(7 + f)
            for b in range(bays):
                if rnd.random() < 0.55:
                    cx = b * bw + bw * rnd.uniform(0.3, 0.7)
                    s.rect(cx - 13, ry0 - 26, cx + 13, ry0 - 8, (190, 120, 88, 255), line=1.2)
                    s.ellipse(cx - 20, ry0 - 52, cx + 20, ry0 - 20, LEAF, line=1.2)
        # 樓板
        s.rect(0, y1 - 8, W, y1 + 6 if f < 2 else y1, CREAM2, line=1.5)
    return s.finish(edge_dark=0.05)


def gate_pillar():
    W, H = int(0.82 * PPU), int(3.0 * PPU)
    s = P.Sheet(W, H)
    s.rect(8, 34, W - 8, H - 26, STONE)
    s.rect(0, 0, W, 40, STONE2)          # 柱頭
    s.rect(4, 40, W - 4, 52, STONE)
    s.rect(2, H - 30, W - 2, H, STONE2)  # 柱腳
    a = s.finish(edge_dark=0.06)
    # 洗石子斑點
    rnd = np.random.default_rng(3)
    m = a[..., 3] > 128
    ys, xs = np.nonzero(m)
    pick = rnd.choice(len(xs), size=len(xs) // 40, replace=False)
    for i in pick:
        y, x = ys[i], xs[i]
        k = rnd.uniform(0.82, 1.08)
        a[y, x, :3] = np.clip(a[y, x, :3] * k, 0, 255)
    return a


def folding_gate():
    W, H = int(1.0 * PPU), int(2.0 * PPU)
    s = P.Sheet(W, H)
    grey, grey2 = (206, 210, 212, 255), (186, 191, 194, 255)
    s.rect(0, 0, W, 16, grey2, line=1.5)
    s.rect(0, H - 34, W, H - 20, grey2, line=1.5)
    n = 9
    for i in range(n):
        x = 8 + i * (W - 16) / (n - 1)
        s.rect(x - 3, 16, x + 3, H - 34, grey, line=1.2)
    for i in range(n - 1):
        x0 = 8 + i * (W - 16) / (n - 1)
        x1 = 8 + (i + 1) * (W - 16) / (n - 1)
        for y in range(30, H - 40, 46):
            s.line([(x0, y), (x1, y + 23), (x0, y + 46)], 1.8, (150, 156, 160, 255))
    for x in (20, W - 20):
        s.ellipse(x - 12, H - 24, x + 12, H, (96, 100, 104, 255), line=1.2)
    return s.finish(edge_dark=0.04)


def school_wall():
    W, H = int(7.0 * PPU), int(1.45 * PPU)
    s = P.Sheet(W, H)
    s.rect(0, 22, W, H, (236, 226, 203, 255))
    s.rect(0, 0, W, 26, TILE)
    for x in range(0, W, 30):
        s.line([(x, 2), (x, 24)], 1.2, (160, 104, 78, 255))
    # 矮樹籬（下緣）
    hy = H - int(0.55 * PPU)
    pts = [(0, H)]
    x = 0
    rnd = random.Random(11)
    while x < W:
        r = rnd.uniform(18, 30)
        for t in range(0, 181, 30):
            pts.append((x + r - r * math.cos(math.radians(t)), hy + 10 - r * 0.8 * math.sin(math.radians(t))))
        x += 2 * r
    pts.append((W, H))
    s.poly(pts, LEAF, line=1.5)
    for i in range(40):
        cx, cy = rnd.uniform(10, W - 10), rnd.uniform(hy + 22, H - 10)
        s.ellipse(cx - 9, cy - 6, cx + 9, cy + 6, LEAF2, line=0)
    return s.finish(edge_dark=0.04)


def guard_house():
    W, H = int(2.7 * PPU), int(3.0 * PPU)
    s = P.Sheet(W, H)
    wall = (207, 216, 198, 255)
    s.rect(14, 34, W - 14, H, wall)
    s.rect(0, 0, W, 40, (160, 176, 152, 255))        # 平屋頂外伸
    s.rect(14, H - 26, W - 14, H, (184, 194, 174, 255))
    # 大窗（玻璃挖空：林老師的背影放在後面）
    wx0, wy0, wx1, wy1 = 40, 108, 238, 292
    s.rect(wx0, wy0, wx1, wy1, (240, 232, 214, 255), line=2)
    s.rect(28, wy1, 250, wy1 + 16, (230, 220, 200, 255), line=1.5)   # 窗台
    # 門
    s.rect(272, 150, 372, H - 26, (169, 187, 178, 255), line=2)
    s.rect(292, 170, 352, 240, GLASS, line=1.5)
    s.rect(282, 300, 296, 330, (111, 123, 116, 255), line=1)
    a_sheet = s
    a_sheet.hole(wx0 + 13, wy0 + 13, wx1 - 13, wy1 - 13)
    s.line([((wx0 + wx1) / 2, wy0 + 12), ((wx0 + wx1) / 2, wy1 - 12)], 0.1, (0, 0, 0, 0))
    a = a_sheet.finish(edge_dark=0.05)
    hole = {"x0": wx0 + 13, "y0": wy0 + 13, "x1": wx1 - 13, "y1": wy1 - 13}
    return a, hole


def floor():
    W, H = 24 * 100, 10 * 100
    s = P.Sheet(W, H, ss=1)
    x_road1 = int((-2.6 + 12) * 100)    # 路面右緣（世界 x −2.6）
    x_curb = x_road1 + 18
    x_gate = int((0.1 + 12) * 100)
    x_line = int((1.6 + 12) * 100)      # 接送線（世界 x +1.6，與校門平行）
    s.rect(0, 0, x_road1, H, (163, 161, 156, 255), line=0)
    s.rect(x_road1, 0, x_curb, H, (205, 199, 186, 255), line=0)
    s.rect(x_curb, 0, x_gate, H, (221, 211, 192, 255), line=0)
    s.rect(x_gate, 0, W, H, (228, 221, 207, 255), line=0)
    # 人行道地磚縫
    for y in range(0, H, 50):
        s.line([(x_curb, y), (x_gate, y)], 1, (196, 186, 166, 255))
    # 斑馬線：路面上一排與 x 軸平行的白色長條（往景深方向排列）
    zx0, zx1 = int((-7.4 + 12) * 100), int((-3.4 + 12) * 100)
    for y in range(40, H - 20, 90):
        s.rect(zx0, y, zx1, y + 48, (236, 233, 224, 255), line=0)
    # 接送線
    s.rect(x_line - 8, 0, x_line + 8, H, (226, 195, 90, 255), line=0)
    a = s.finish()
    return a, {"road_right_x": -2.6, "gate_x": 0.1, "pickup_line_x": 1.6, "zebra_x": [-7.4, -3.4]}


def bench():
    PP = 300
    W, H = int(3.2 * PP), int(1.6 * PP)
    s = P.Sheet(W, H)
    metal = (96, 113, 102, 255)
    wood, wood2, wood3 = (201, 154, 94, 255), (190, 141, 83, 255), (216, 173, 116, 255)
    seat = H - int(0.92 * PP)               # 座面上緣（像素）
    for x in (70, W // 2 - 12, W - 94):
        s.rect(x, 20, x + 24, H - 8, metal, line=1.5)
        s.rect(x - 14, H - 14, x + 38, H, metal, line=1.5)
    for i, y in enumerate((28, 76, 124)):
        s.rect(36, y, W - 36, y + 34, wood if i % 2 == 0 else wood2, line=1.8)
    s.rect(30, seat - 14, W - 30, seat, wood3, line=1.6)       # 座面上側（略俯視）
    s.rect(30, seat, W - 30, seat + 40, wood2, line=1.8)       # 座板正面
    s.rect(46, seat + 40, W - 46, seat + 54, metal, line=1.5)
    for x0 in range(60, W - 60, 140):
        s.line([(x0, seat + 6), (x0 + 30, seat + 6)], 1.2, (150, 108, 64, 255))
    a = s.finish(white_border=10)
    pad = 16
    return a, {"seat_top_px_in_final": seat + pad, "px_per_unit": PP, "seat_world_y": 0.92, "white_border_px": 10}


def truck():
    PP = 250
    W, H = int(6.0 * PP), int(3.3 * PP)
    s = P.Sheet(W, H)
    body = (241, 230, 204, 255)
    body2 = (230, 217, 188, 255)
    tarp, tarp2 = (154, 147, 99, 255), (136, 129, 86, 255)
    wy = H - 96
    wheels = [(360, wy), (1180, wy)]
    for cx, cy in wheels:          # 輪拱（深色，輪子後面）
        s.ellipse(cx - 116, cy - 116, cx + 116, cy + 116, (92, 86, 80, 255), line=1.5)
    s.rect(60, 560, 1470, 690, body2)                       # 底盤裙板
    s.rect(70, 470, 1000, 640, body)                        # 車斗側板
    for x in (300, 530, 760):
        s.line([(x, 480), (x, 630)], 2)
    s.rect(64, 458, 1006, 476, body2, line=1.8)             # 車斗上緣
    # 帆布
    pts = [(78, 462), (84, 360)]
    for i in range(13):
        t = i / 12
        pts.append((90 + t * 890, 330 - math.sin(t * math.pi) * 40 + 10 * math.sin(t * 9)))
    pts += [(994, 340), (1000, 462)]
    s.poly(pts, tarp, line=2)
    for i in range(4):
        x = 150 + i * 220
        s.line([(x, 340), (x + 160, 462)], 2.5, (104, 90, 68, 255))
        s.line([(x + 160, 340), (x, 462)], 2.5, (104, 90, 68, 255))
    for x in range(110, 990, 110):
        s.rect(x - 6, 462, x + 6, 476, tarp2, line=1)
    # 竹篾貓耳尖（從帆布下露出一小角，靠近駕駛座後窗）
    ear = [(930, 335), (978, 238), (1004, 330)]
    s.poly(ear, (208, 171, 114, 255), line=2)
    for k in range(1, 4):
        t = k / 4
        s.line([(930 + (978 - 930) * t, 335 + (238 - 335) * t), (1004 - (1004 - 978) * t, 330 + (238 - 330) * t)], 1.8, (156, 122, 76, 255))
    s.line([(954, 287), (966, 333)], 1.8, (156, 122, 76, 255))
    # 駕駛座
    cab = [(1012, 690), (1012, 270)]
    for t in range(0, 91, 15):
        cab.append((1060 - 48 * math.cos(math.radians(t)), 270 - 30 * math.sin(math.radians(t))))
    cab += [(1360, 240), (1392, 252), (1452, 420), (1466, 560), (1466, 690)]
    s.poly(cab, body, line=2.4)
    s.poly([(1150, 285), (1370, 280), (1418, 430), (1150, 438)], GLASS, line=2)     # 側窗
    s.rect(1032, 292, 1112, 402, GLASS, line=2, r=8)                                  # 後窗
    s.line([(1132, 286), (1132, 660)], 2)
    s.line([(1132, 660), (1440, 660)], 2)
    s.rect(1150, 470, 1196, 482, (140, 133, 121, 255), line=1.2)                      # 門把
    s.rect(1426, 518, 1462, 560, (242, 229, 181, 255), line=1.6)                      # 頭燈（不亮）
    s.rect(1430, 640, 1488, 694, (164, 157, 146, 255), line=1.6)                      # 前保險桿
    s.rect(40, 620, 84, 684, (164, 157, 146, 255), line=1.6)                          # 後保險桿
    s.rect(60, 520, 78, 562, (196, 128, 100, 255), line=1.2)                          # 尾燈（不亮、低彩度）
    s.rect(1388, 318, 1418, 352, (150, 156, 160, 255), line=1.2)                      # 後照鏡
    for cx, cy in wheels:
        s.ellipse(cx - 95, cy - 95, cx + 95, cy + 95, (74, 70, 68, 255), line=2)
        s.ellipse(cx - 46, cy - 46, cx + 46, cy + 46, (238, 230, 210, 255), line=1.6)
        for k in range(5):
            ang = math.radians(k * 72 - 90)
            bx, by = cx + 26 * math.cos(ang), cy + 26 * math.sin(ang)
            s.ellipse(bx - 5, by - 5, bx + 5, by + 5, (150, 142, 128, 255), line=0)
    a = s.finish(white_border=10)
    # 單獨的輪子（可轉動；和車圖上畫的輪子同位置同大小，疊在上面轉）
    ws = P.Sheet(212, 212)
    c = 106
    ws.ellipse(c - 95, c - 95, c + 95, c + 95, (74, 70, 68, 255), line=2)
    ws.ellipse(c - 46, c - 46, c + 46, c + 46, (238, 230, 210, 255), line=1.6)
    for k in range(5):
        ang = math.radians(k * 72 - 90)
        bx, by = c + 26 * math.cos(ang), c + 26 * math.sin(ang)
        ws.ellipse(bx - 5, by - 5, bx + 5, by + 5, (150, 142, 128, 255), line=0)
    wheel = ws.finish()
    pad = 16
    meta = {"px_per_unit": PP, "wheel_centers_px_in_final": [[cx + pad, cy + pad] for cx, cy in wheels], "wheel_radius_px": 95,
            "ground_px_in_final": H + pad, "cat_ear_tip_px_in_final": [978 + pad, 238 + pad], "rear_window_px_in_final": [1032 + pad, 292 + pad, 1112 + pad, 402 + pad],
            "driver_door_px_in_final": [1132 + pad, 286 + pad, 1440 + pad, 660 + pad], "faces": "車頭朝畫面右（從左邊開進來）"}
    return a, wheel, meta


def main():
    GATE.mkdir(parents=True, exist_ok=True)
    recs = {}

    def put(a, path, name, **meta):
        P.save(a, path)
        recs[name] = {"file": str(path.relative_to(ROOT)), "size": [int(a.shape[1]), int(a.shape[0])], **meta}

    put(school_building(), GATE / "set-gate_school-building_v01.png", "school-building")
    put(gate_pillar(), GATE / "set-gate_pillar_v01.png", "pillar")
    put(folding_gate(), GATE / "set-gate_folding-gate_v01.png", "folding-gate")
    put(school_wall(), GATE / "set-gate_school-wall_v01.png", "school-wall")
    gh, hole = guard_house()
    put(gh, GATE / "set-gate_guard-house_v01.png", "guard-house", window_hole_px=hole)
    fl, fmeta = floor()
    put(fl, GATE / "set-gate_floor_v01.png", "floor", **fmeta)
    b, bmeta = bench()
    put(b, PROPS / "prop-bench_v01.png", "bench", **bmeta)
    t, wheel, tmeta = truck()
    put(t, PROPS / "prop-truck_v01.png", "truck", **tmeta)
    put(wheel, PROPS / "prop-truck-wheel_v01.png", "truck-wheel")

    def wh(name, w):
        W, H = recs[name]["size"]
        return round(w * H / W, 3)

    sq = json.loads((ROOT / "review/G5/shared_art/sets/square_import.json").read_text())

    def sqp(name, layer, x, y, w, z, note=""):
        W, H = sq[name]["size"]
        return {"id": f"sets/square/set-square_{name}", "file": sq[name]["file"], "layer": layer, "x": x, "y": y, "z": z, "width": w,
                "height": round(w * H / W, 3), "anchor": "bottom-center", "note": note}

    def gp(name, layer, x, y, w, z, note="", **extra):
        return {"id": f"sets/gate/set-gate_{name}", "file": recs[name]["file"], "layer": layer, "x": x, "y": y, "z": z, "width": w,
                "height": wh(name, w), "anchor": "bottom-center", "note": note, **extra}

    gh_w = 2.7
    hx = 4.7
    hole_world = None
    W, H = recs["guard-house"]["size"]
    upp = gh_w / W
    hole_world = {"x0": round(hx - gh_w / 2 + hole["x0"] * upp, 3), "x1": round(hx - gh_w / 2 + hole["x1"] * upp, 3),
                  "y0": round((H - hole["y1"]) * upp, 3), "y1": round((H - hole["y0"]) * upp, 3)}
    truck_w = 6.0
    tW, tH = recs["truck"]["size"]
    tup = truck_w / tW
    layout = {
        "format": "antidrug-g5-set-layout-draft/1",
        "status": "草稿：引擎代理定 layout.json 正式格式後改寫（app/SHOW_INTERFACE.md）。景片是程式繪製的退路版（image_gen 額度 19:50 才恢復）；之後若重抽，同 id 換圖即可。",
        "set": "gate",
        "used_in": "第三幕 a3_c003（校門口迎接、品安走過）；第四幕 a4_c001、a4_c002、a4_c008、a4_c012、a4_c013；第五幕 a5_c001、a5_c005–a5_c007",
        "coords": "世界座標同 app/src/stage/layers.ts：x 向右、y 向上（地面 0）、z 朝觀眾；x,y＝圖片底邊中點；width／height 世界單位。",
        "staging": {
            "outside_left": "校門外（街道、對街騎樓、停在對面的小貨車、校門外長椅）＝畫面左＝危險方位（和 G4 一致）",
            "inside_right": "校門內（警衛室、校舍、接送區）＝畫面右＝安全方位",
            "kids_mark": "孩子站在接送線（世界 x +1.6）右側：建議 x +2.5～+3.7，z 0～0.4；不往左越過接送線（兒童安全界線第 6 條）",
            "bench_mark": "長椅在校門外：x −3.2、z 0.1（坐的人 z 0.3）（阿樂叔叔 a4_c013 坐下、a5_c001 P-AL1 靠著椅背）",
            "truck_mark": "小貨車停在對面：x −7.6、z −2.4（車頭朝右；從畫面左外開進來，只開到這裡就停，不靠近孩子）",
            "guard_window": {"world": hole_world, "note": "警衛室大窗的玻璃是挖空的（透明）；a4_c001 林老師的背影可以放在 z −1.2（警衛室後面一點）從窗裡看到。林老師背面圖還沒有（handoff）"},
        },
        "lighting": "兒童站位身後是警衛室淺灰綠牆（約 sRGB 207,216,198）與米色校牆，投影 v2 下要 ≥0.50（D-G2-06）；本預覽量測見 review/G5/shared_art/sets/gate_preview_*.json。",
        "floor": {"id": "sets/gate/set-gate_floor", "file": recs["floor"]["file"], "world_width": 24, "world_depth": 10, "center": [0, 0, 0.0],
                  "note": "地面平面（y=0，圖上方＝遠處）：左邊柏油路＋斑馬線、路緣、人行道、校門（x 0.1）、校內水泥地與黃色接送線（x +1.6）", **fmeta},
        "pieces": [
            sqp("sky", "backdrop", 0, -0.5, 26, -5.0, "沿用廣場天空（同一天、同一個小鎮）"),
            sqp("mountains", "far", 0, -2.2, 24, -4.4, "沿用廣場遠山（底邊在地面下，只露出山脊）"),
            sqp("backrow", "far", -7.2, 0, 11.5, -3.4, "對街騎樓（沿用廣場後排建築）"),
            gp("school-building", "far", 5.6, 0, 11.5, -3.2, "三層樓走廊式校舍（無校徽、無字）"),
            gp("school-wall", "mid", 5.2, 0, 7.0, -1.25, "校內側圍牆＋矮樹籬（在警衛室後面）"),
            gp("pillar", "mid", -1.25, 0, 0.82, -0.9, "左門柱"),
            gp("pillar", "mid", 1.25, 0, 0.82, -0.9, "右門柱（同一張圖）"),
            gp("folding-gate", "mid", 2.1, 0, 0.9, -1.0, "伸縮門收在右門柱內側（淺灰，避免孩子身後變暗）"),
            gp("guard-house", "mid", hx, 0, gh_w, -0.95, "警衛室（窗戶玻璃挖空）", window_hole_world=hole_world),
            sqp("tree-a", "mid", -4.9, 0, 3.6, -1.6, "校門外行道樹"),
            sqp("planter-mid", "fore", 7.6, 0, 1.5, 2.4, "右前景花台（框景）"),
            sqp("tree-b", "fore", -8.6, 0, 3.4, 2.2, "左前景行道樹（框景，大全景才看得到）"),
        ],
        "props": [
            {"id": "props/prop-bench", "file": recs["bench"]["file"], "x": -3.2, "y": 0, "z": 0.1, "width": round(recs["bench"]["size"][0] / 300, 3),
             "height": round(recs["bench"]["size"][1] / 300, 3), "anchor": "bottom-center", "seat_world_y": 0.92,
             "note": "座面世界高 0.92（圖上座面 y＝seat_top_px_in_final；白邊 10 px 在外）。品安 P-PA1、林老師 P-LIN2 的 feet 已算好坐在 0.92。"},
            {"id": "props/prop-truck", "file": recs["truck"]["file"], "x": -7.6, "y": 0, "z": -2.4, "width": truck_w, "height": round(tH * tup, 3),
             "anchor": "bottom-center", "wheels": {"id": "props/prop-truck-wheel", "centers_world_from_bottom_center": [[round((c[0] - tW / 2) * tup, 3), round((tH - c[1]) * tup, 3)] for c in tmeta["wheel_centers_px_in_final"]],
                                                   "diameter_world": round(212 * tup, 3)},
             "note": "淡米色無標誌小貨車（a4_c001、a4_c008、a4_c013 共用同一張）。貓耳竹篾尖在後窗旁；a4_c013 鏡頭帶到後車窗時用 cat_ear_tip_px_in_final 找位置。"},
        ],
        "made_by": "review/G5/shared_art/scripts/build_gate.py",
    }
    (ROOT / "review/G5/shared_art/sets/gate_layout_source.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1))
    (ROOT / "review/G5/shared_art/sets/gate_import.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    for k, v in recs.items():
        print(k, v["size"])


if __name__ == "__main__":
    main()
