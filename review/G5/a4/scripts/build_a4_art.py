"""第四幕（a4）素材：紙上的路（牛皮紙地圖、立體書小屋、小紙車、斑馬線上的路人）、背光剪影幕、
校門口的程式道具（車鑰匙、導護旗、警衛室窗內的小背影、遠景家長剪影、騎樓小燈籠）、陳伯伯接鑰匙姿勢。

為什麼是程式繪製：Codex image_gen 額度用完（約 19:50 恢復），G5 第四幕代理改用 Pillow＋G2 同款紙紋
（review/G5/shared_art/scripts/paperdraw.py，平塗色塊、暖深灰細線、無方向光），和校門口退路版景片同一套畫法。
圖裡不放任何文字、數字、品牌、標誌；車子是通用小車（不是阿樂叔叔的小貨車），路人與剪影是通用人形（不是主角）。

輸出：
  assets/final/sets/a4_roadmap/set-a4map_*_v01.png      紙上的路（a4_c002 後半～a4_c008 前半）
  assets/final/sets/gate/set-gate_a4-*_v01.png         校門口第四幕程式道具（只在第四幕 cue 的 setTrack 打開）
  assets/final/chr-chen_pose-receive_v01.png           陳伯伯伸手接鑰匙（由 chr-chen_master_v01 改畫前臂，頭臉不動）
  review/G5/a4/art_meta.json                           尺寸、地標（世界座標）給 app/src/sets/a4_roadmap.ts、gate.ts 對照
用法：/opt/anaconda3/bin/python3 review/G5/a4/scripts/build_a4_art.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

MAP_DIR = ROOT / "assets/final/sets/a4_roadmap"
GATE = ROOT / "assets/final/sets/gate"
INK = P.INK

# ---- 色票（和校門口退路版、G2 景片同一系：暖、低彩度）
KRAFT = (205, 175, 132, 255)
KRAFT_D = (176, 143, 101, 255)
ROAD = (236, 229, 212, 255)
ROAD_EDGE = (214, 204, 182, 255)
WALK = (218, 204, 176, 255)
ZEBRA = (251, 247, 236, 255)
GRASS = (186, 196, 152, 255)
GRASS2 = (168, 182, 136, 255)
YARD = (230, 216, 186, 255)
LEAF = (126, 158, 98, 255)
LEAF2 = (104, 138, 84, 255)
TRUNK = (150, 112, 78, 255)
CREAM = (241, 230, 204, 255)
WALL2 = (232, 219, 190, 255)
TERRA = (196, 134, 102, 255)
SAGE = (140, 164, 150, 255)
SLATE = (122, 138, 150, 255)
GLASS = (206, 223, 226, 255)
LINEY = (214, 184, 92, 255)      # 道路中線（淡黃、實線，不和預定路線的虛線混淆）

MAP_W, MAP_H = 18.0, 9.0          # 世界單位（地圖中心＝世界 x −5、z 0；u＝x+5、v＝z）
MAP_PPU = 180


def u2px(u):
    return (u + MAP_W / 2) * MAP_PPU


def v2px(v):
    return (v + MAP_H / 2) * MAP_PPU


# ============================================================ 1. 牛皮紙地圖（俯視）
ROAD_V = (-0.5, 1.5)            # 主路（v 範圍）：遠車道 −0.5–0.5（往左）、近車道 0.5–1.5（往右）
SIDE_U = (-4.6, -2.8)           # 由下方接上主路的支路（u 範圍）
WALK_W = 0.4                    # 人行道寬
ZEBRA_U = (3.7, 5.1)            # 斑馬線（u 範圍）
STOP_U = 2.45                   # 停止線（近車道）


def draw_map():
    W, H = int(MAP_W * MAP_PPU), int(MAP_H * MAP_PPU)
    s = P.Sheet(W, H, ss=1)
    d = s.d
    X, Y = u2px, v2px
    # 牛皮紙底＋邊緣稍深（紙放久的邊）
    s.rect(0, 0, W, H, KRAFT, line=0)
    # 公園（左下）、校園（右上）、街廓（左上、右下）
    s.rect(X(-9), Y(1.5 + WALK_W), X(SIDE_U[0]), Y(4.5), GRASS, line=0)
    s.rect(X(2.6), Y(-4.5), X(9), Y(-0.5 - WALK_W), YARD, line=0)
    # 人行道
    s.rect(X(-9), Y(-0.5 - WALK_W), X(9), Y(-0.5), WALK, line=0)
    s.rect(X(-9), Y(1.5), X(SIDE_U[0] - WALK_W), Y(1.5 + WALK_W), WALK, line=0)
    s.rect(X(SIDE_U[1] + WALK_W), Y(1.5), X(9), Y(1.5 + WALK_W), WALK, line=0)
    s.rect(X(SIDE_U[0] - WALK_W), Y(1.5), X(SIDE_U[0]), Y(4.5), WALK, line=0)
    s.rect(X(SIDE_U[1]), Y(1.5), X(SIDE_U[1] + WALK_W), Y(4.5), WALK, line=0)
    # 路面（主路＋支路），路緣鉛筆線
    s.rect(X(-9), Y(ROAD_V[0]), X(9), Y(ROAD_V[1]), ROAD, line=0)
    s.rect(X(SIDE_U[0]), Y(ROAD_V[1]) - 2, X(SIDE_U[1]), Y(4.5), ROAD, line=0)
    lw = 3.0
    s.line([(0, Y(ROAD_V[0])), (W, Y(ROAD_V[0]))], lw)
    s.line([(0, Y(ROAD_V[1])), (X(SIDE_U[0]), Y(ROAD_V[1]))], lw)
    s.line([(X(SIDE_U[1]), Y(ROAD_V[1])), (W, Y(ROAD_V[1]))], lw)
    s.line([(X(SIDE_U[0]), Y(ROAD_V[1])), (X(SIDE_U[0]), H)], lw)
    s.line([(X(SIDE_U[1]), Y(ROAD_V[1])), (X(SIDE_U[1]), H)], lw)
    # 人行道外緣（細）
    for pts in ([(0, Y(-0.9)), (W, Y(-0.9))], [(0, Y(1.9)), (X(SIDE_U[0] - WALK_W), Y(1.9))], [(X(SIDE_U[1] + WALK_W), Y(1.9)), (W, Y(1.9))],
                [(X(SIDE_U[0] - WALK_W), Y(1.9)), (X(SIDE_U[0] - WALK_W), H)], [(X(SIDE_U[1] + WALK_W), Y(1.9)), (X(SIDE_U[1] + WALK_W), H)]):
        s.line(pts, 1.6, (120, 98, 78, 255))
    # 人行道地磚縫
    for u in np.arange(-9, 9, 0.5):
        s.line([(X(u), Y(-0.9)), (X(u), Y(-0.5))], 1, (196, 182, 154, 255))
        if not (SIDE_U[0] - WALK_W - 0.01 < u < SIDE_U[1] + WALK_W + 0.01):
            s.line([(X(u), Y(1.5)), (X(u), Y(1.9))], 1, (196, 182, 154, 255))
    # 道路中線（淡黃雙實線）
    for dv in (-0.035, 0.035):
        s.line([(0, Y(0.5 + dv)), (X(ZEBRA_U[0] - 0.15), Y(0.5 + dv))], 2.2, LINEY)
        s.line([(X(ZEBRA_U[1] + 0.15), Y(0.5 + dv)), (W, Y(0.5 + dv))], 2.2, LINEY)
    # 斑馬線（長條和車流平行，沿 v 方向排列）
    v = ROAD_V[0] + 0.06
    while v < ROAD_V[1] - 0.12:
        s.rect(X(ZEBRA_U[0]), Y(v), X(ZEBRA_U[1]), Y(v + 0.15), ZEBRA, line=1.2)
        v += 0.27
    # 停止線（近車道）
    s.rect(X(STOP_U - 0.09), Y(0.55), X(STOP_U + 0.09), Y(1.45), ZEBRA, line=1.6)
    # 校園：跑道一角（淡線）、花圃
    d.arc([X(5.2), Y(-3.0), X(10.5), Y(0.4)], 180, 270, fill=(206, 186, 150, 255), width=6)
    # 右下街廓：俯視屋頂（平面，不立起）
    roofs = [(-2.2, 2.25, 0.2, 3.7, TERRA), (0.6, 2.3, 2.6, 3.5, SAGE), (3.0, 2.25, 5.3, 3.8, (206, 160, 112, 255)), (5.7, 2.3, 8.4, 3.6, SLATE)]
    for u0, v0, u1, v1, col in roofs:
        s.rect(X(u0), Y(v0), X(u1), Y(v1), col, line=2.2)
        s.line([(X(u0), Y((v0 + v1) / 2)), (X(u1), Y((v0 + v1) / 2))], 1.8)
        for k in range(1, 6):
            uu = u0 + (u1 - u0) * k / 6
            s.line([(X(uu), Y(v0) + 4), (X(uu), Y(v1) - 4)], 1, tuple(int(c * 0.9) for c in col[:3]) + (255,))
    # 公園：小路與草叢（平面）
    d.line([(X(-9), Y(3.6)), (X(-7.0), Y(3.1)), (X(-5.6), Y(3.4)), (X(SIDE_U[0] - WALK_W), Y(2.9))], fill=(214, 198, 166, 255), width=26, joint="curve")
    for (u, vv, r) in [(-8.2, 2.5, 0.42), (-6.6, 2.4, 0.36), (-7.6, 4.1, 0.4), (-5.6, 4.0, 0.34), (-5.3, 2.4, 0.3)]:
        s.ellipse(X(u - r), Y(vv - r), X(u + r), Y(vv + r), LEAF, line=2)
        s.ellipse(X(u - r * 0.55), Y(vv - r * 0.6), X(u + r * 0.25), Y(vv + r * 0.1), (150, 180, 118, 255), line=0)
    # 左上街廓：房子的地基（立體書小屋立起的位置，淡淡的平面輪廓）
    for u0, u1 in [(-8.2, -6.4), (-5.5, -3.7), (-2.6, -0.6), (0.3, 1.9)]:
        s.rect(X(u0), Y(-1.65), X(u1), Y(-1.05), (192, 160, 118, 255), line=1.4)
    # 指北的紙星（沒有字母）
    cu, cv, R = -8.0, -3.75, 0.42
    pts = []
    for k in range(16):
        ang = -math.pi / 2 + k * math.pi / 8
        rr = R if k % 4 == 0 else (R * 0.55 if k % 2 == 0 else R * 0.22)
        pts.append((X(cu) + rr * MAP_PPU * math.cos(ang), Y(cv) + rr * MAP_PPU * math.sin(ang)))
    s.poly(pts, (232, 214, 180, 255), line=2)
    s.poly([(X(cu), Y(cv) - R * MAP_PPU), (X(cu) + 0.09 * MAP_PPU, Y(cv)), (X(cu) - 0.09 * MAP_PPU, Y(cv))], (171, 92, 72, 255), line=1.5)
    s.ellipse(X(cu) - 6, Y(cv) - 6, X(cu) + 6, Y(cv) + 6, INK, line=0)
    # ---- 細節（手繪地圖感）：左上街廓的鉛筆斜線、樹穴與行道樹（平面）、人孔蓋、公園水池與長椅、校園花圃與球場線
    hatch = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(hatch)
    for k in range(-H, W, 22):
        hd.line([(k, H), (k + H, 0)], fill=255, width=2)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle([X(-9), Y(-4.5), X(2.6), Y(-0.9 - 0.02)], fill=255)
    for u0, u1 in [(-8.2, -6.4), (-5.5, -3.7), (-2.6, -0.6), (0.3, 1.9)]:
        ImageDraw.Draw(m).rectangle([X(u0) - 14, Y(-1.65) - 14, X(u1) + 14, Y(-1.05) + 14], fill=0)
    hm = (np.array(hatch) > 0) & (np.array(m) > 0)
    arr = np.array(s.img)
    arr[hm, :3] = (arr[hm, :3].astype(np.int32) * 0.93).astype(np.uint8)
    s.img = Image.fromarray(arr, "RGBA")
    s.d = d = ImageDraw.Draw(s.img)
    for u in np.arange(-8.4, 2.4, 1.3):           # 上方人行道的行道樹（平面圓）
        s.ellipse(X(u - 0.22), Y(-0.92), X(u + 0.22), Y(-0.48), (150, 172, 118, 255), line=1.6)
        s.ellipse(X(u - 0.1), Y(-0.86), X(u + 0.06), Y(-0.7), (176, 196, 140, 255), line=0)
    for u in list(np.arange(-1.9, 9, 1.5)):        # 下方人行道
        s.ellipse(X(u - 0.2), Y(1.5), X(u + 0.2), Y(1.9), (150, 172, 118, 255), line=1.6)
    for (u, vv) in [(-6.3, 0.0), (0.6, 1.05), (6.4, 0.0), (-3.7, 2.9)]:   # 人孔蓋
        s.ellipse(X(u - 0.13), Y(vv - 0.13), X(u + 0.13), Y(vv + 0.13), (206, 198, 180, 255), line=1.4)
        s.line([(X(u - 0.08), Y(vv)), (X(u + 0.08), Y(vv))], 1, (150, 140, 120, 255))
    s.ellipse(X(-7.9), Y(2.9), X(-6.2), Y(3.9), (170, 196, 204, 255), line=2)          # 公園水池
    s.ellipse(X(-7.6), Y(3.05), X(-6.9), Y(3.45), (196, 214, 218, 255), line=0)
    for (u, vv) in [(-5.6, 3.3), (-8.6, 2.1)]:                                          # 長椅（俯視）
        s.rect(X(u - 0.3), Y(vv - 0.08), X(u + 0.3), Y(vv + 0.08), (176, 136, 90, 255), line=1.4)
    for (u0, v0, u1, v1) in [(2.9, -1.5, 4.1, -1.15), (6.2, -1.5, 8.4, -1.15)]:          # 校園花圃
        s.rect(X(u0), Y(v0), X(u1), Y(v1), (196, 170, 130, 255), line=1.6)
        for k in range(6):
            uu = u0 + (u1 - u0) * (k + 0.5) / 6
            s.ellipse(X(uu) - 9, Y((v0 + v1) / 2) - 9, X(uu) + 9, Y((v0 + v1) / 2) + 9, (214, 150, 120, 255) if k % 2 else (226, 196, 110, 255), line=1)
    d.rectangle([X(2.95), Y(-4.1), X(4.9), Y(-2.6)], outline=(206, 186, 150, 255), width=5)   # 球場線
    d.line([(X(3.925), Y(-4.1)), (X(3.925), Y(-2.6))], fill=(206, 186, 150, 255), width=4)
    # 摺痕（3×2 摺）：一條淡亮線＋一條淡暗線
    for u in (-3.0, 3.0):
        s.line([(X(u) - 2, 0), (X(u) - 2, H)], 3, (226, 202, 162, 160))
        s.line([(X(u) + 2, 0), (X(u) + 2, H)], 2, (150, 118, 82, 120))
    s.line([(0, Y(0.0) - 2), (W, Y(0.0) - 2)], 3, (226, 202, 162, 140))
    s.line([(0, Y(0.0) + 2), (W, Y(0.0) + 2)], 2, (150, 118, 82, 110))
    # 內框（地圖邊框）
    m = 0.22 * MAP_PPU
    d.rectangle([m, m, W - m, H - m], outline=INK, width=4)
    d.rectangle([m + 10, m + 10, W - m - 10, H - m - 10], outline=(120, 98, 78, 255), width=2)
    a = s.finish()
    # 邊緣變深（紙邊）
    yy, xx = np.mgrid[0:H, 0:W]
    edge = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy]).astype(np.float32)
    k = np.clip(1 - edge / 70.0, 0, 1) ** 1.6 * 0.22
    a = a.astype(np.float32)
    a[..., :3] *= (1 - k[..., None])
    return np.clip(a, 0, 255).astype(np.uint8)


# ============================================================ 2. 立體書小屋與樹（正面立面，立在地圖上）
PP_POP = 220


def house(kind):
    if kind == "a":
        w, h = 1.8, 1.45
    elif kind == "b":
        w, h = 1.8, 1.75
    elif kind == "c":
        w, h = 2.0, 1.35
    else:
        w, h = 1.6, 1.5
    W, H = int(w * PP_POP), int(h * PP_POP)
    s = P.Sheet(W, H)
    g = H - 4
    if kind == "a":      # 平房：赤陶屋頂
        s.rect(40, int(H * 0.42), W - 40, g, CREAM, line=2.2)
        s.poly([(14, int(H * 0.45)), (W // 2, 14), (W - 14, int(H * 0.45))], TERRA, line=2.4)
        s.rect(int(W * 0.18), int(H * 0.58), int(W * 0.38), int(H * 0.78), GLASS, line=2)
        s.rect(int(W * 0.56), int(H * 0.56), int(W * 0.74), g, (176, 128, 92, 255), line=2)
    elif kind == "b":    # 二樓透天：灰綠屋頂
        s.rect(46, int(H * 0.26), W - 46, g, WALL2, line=2.2)
        s.poly([(22, int(H * 0.28)), (W // 2, 12), (W - 22, int(H * 0.28))], SAGE, line=2.4)
        for yy in (0.36, 0.62):
            for xx in (0.24, 0.6):
                s.rect(int(W * xx), int(H * yy), int(W * (xx + 0.16)), int(H * (yy + 0.14)), GLASS, line=2)
        s.rect(int(W * 0.08), int(H * 0.53), W - int(W * 0.08), int(H * 0.56), (196, 180, 150, 255), line=1.5)
    elif kind == "c":    # 小店：素色遮雨棚（不放招牌字）
        s.rect(30, int(H * 0.3), W - 30, g, CREAM, line=2.2)
        s.rect(18, int(H * 0.18), W - 18, int(H * 0.32), (196, 170, 120, 255), line=2)
        n = 7
        for i in range(n):
            x0 = 24 + (W - 48) * i / n
            x1 = 24 + (W - 48) * (i + 1) / n
            col = (226, 214, 190, 255) if i % 2 else (176, 150, 112, 255)
            s.poly([(x0, int(H * 0.32)), (x1, int(H * 0.32)), (x1 - 6, int(H * 0.43)), (x0 + 6, int(H * 0.43))], col, line=1.6)
        s.rect(int(W * 0.12), int(H * 0.52), int(W * 0.5), int(H * 0.8), GLASS, line=2)
        s.rect(int(W * 0.6), int(H * 0.5), int(W * 0.84), g, (160, 120, 88, 255), line=2)
    else:                # 兩層小屋：石板灰屋頂
        s.rect(40, int(H * 0.34), W - 40, g, (236, 222, 196, 255), line=2.2)
        s.rect(26, int(H * 0.2), W - 26, int(H * 0.36), SLATE, line=2.2)
        s.rect(int(W * 0.2), int(H * 0.48), int(W * 0.44), int(H * 0.66), GLASS, line=2)
        s.rect(int(W * 0.56), int(H * 0.58), int(W * 0.78), g, (170, 126, 90, 255), line=2)
    return s.finish(white_border=6), (w, h)


def school():
    w, h = 4.6, 1.95
    W, H = int(w * PP_POP), int(h * PP_POP)
    s = P.Sheet(W, H)
    g = H - 4
    s.rect(20, 40, W - 20, g, (239, 227, 198, 255), line=2.4)
    s.rect(12, 26, W - 12, 52, (226, 196, 172, 255), line=2)
    for fl in range(3):
        y0 = 70 + fl * (H - 90) / 3
        s.rect(26, int(y0 + (H - 90) / 3 - 16), W - 26, int(y0 + (H - 90) / 3 - 4), (228, 190, 160, 255), line=1.4)
        for i in range(9):
            x0 = 48 + i * (W - 96) / 9
            s.rect(int(x0 + 10), int(y0 + 10), int(x0 + (W - 96) / 9 - 10), int(y0 + (H - 90) / 3 - 26), GLASS, line=1.6)
    return s.finish(white_border=6), (w, h)


def gatepost():
    w, h = 0.3, 0.85
    W, H = int(w * PP_POP), int(h * PP_POP)
    s = P.Sheet(W, H)
    s.rect(8, 20, W - 8, H - 4, (216, 209, 194, 255), line=2)
    s.rect(2, 6, W - 2, 26, (205, 196, 178, 255), line=2)
    return s.finish(white_border=5), (w, h)


def tree(seed):
    w, h = 0.95, 1.25
    W, H = int(w * PP_POP), int(h * PP_POP)
    s = P.Sheet(W, H)
    s.rect(W // 2 - 10, int(H * 0.55), W // 2 + 10, H - 4, TRUNK, line=1.8)
    rnd = np.random.default_rng(seed)
    blobs = [(0.5, 0.36, 0.34), (0.3, 0.46, 0.22), (0.7, 0.46, 0.22), (0.5, 0.2, 0.22)]
    for (cx, cy, r) in blobs:
        s.ellipse(W * (cx - r), H * (cy - r * 0.8), W * (cx + r), H * (cy + r * 0.8), LEAF, line=2)
    for (cx, cy, r) in blobs[:3]:
        jx = rnd.uniform(-0.04, 0.04)
        s.ellipse(W * (cx - r * 0.5 + jx), H * (cy - r * 0.55), W * (cx + r * 0.2 + jx), H * (cy - r * 0.05), (150, 182, 116, 255), line=0)
    return s.finish(white_border=5), (w, h)


def walker_map():
    """斑馬線上背書包的路人（往學校方向走、背影；通用人形）"""
    w, h = 0.42, 0.86
    PPW = 400
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    cx = W / 2
    skin = (238, 196, 160, 255)
    s.rect(cx - 30, H * 0.62, cx - 6, H - 22, (94, 104, 120, 255), line=2)            # 腿
    s.rect(cx + 6, H * 0.6, cx + 30, H - 30, (94, 104, 120, 255), line=2)
    s.ellipse(cx - 40, H - 34, cx - 2, H - 12, (80, 72, 66, 255), line=1.6)
    s.ellipse(cx + 2, H - 42, cx + 40, H - 20, (80, 72, 66, 255), line=1.6)
    s.rect(cx - 48, H * 0.3, cx + 48, H * 0.66, (132, 160, 184, 255), line=2, r=18)  # 上衣
    s.rect(cx - 66, H * 0.34, cx - 44, H * 0.58, skin, line=1.8, r=10)               # 手
    s.rect(cx + 44, H * 0.34, cx + 66, H * 0.56, skin, line=1.8, r=10)
    s.ellipse(cx - 40, H * 0.06, cx + 40, H * 0.3, (92, 70, 54, 255), line=2)        # 頭（背面：頭髮）
    s.rect(cx - 42, H * 0.3, cx + 42, H * 0.6, (226, 186, 96, 255), line=2.2, r=16)  # 書包
    s.rect(cx - 30, H * 0.44, cx + 30, H * 0.54, (210, 166, 80, 255), line=1.6, r=8)
    return s.finish(white_border=6), (w, h)


def car_top():
    """紙剪的小車（俯視，車頭朝 +u；通用小車，無標誌）"""
    w, h = 1.0, 0.56
    PPW = 320
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    body = (141, 179, 168, 255)
    body2 = (124, 160, 150, 255)
    for (x, y) in [(0.2, 0.0), (0.72, 0.0), (0.2, 0.86), (0.72, 0.86)]:       # 輪子（露出一點）
        s.rect(W * x, H * y, W * (x + 0.14), H * (y + 0.14), (70, 66, 62, 255), line=1.4, r=6)
    s.rect(8, H * 0.08, W - 8, H * 0.92, body, line=2.4, r=46)
    s.rect(W * 0.3, H * 0.18, W * 0.72, H * 0.82, body2, line=2, r=20)       # 車頂
    s.poly([(W * 0.72, H * 0.2), (W * 0.84, H * 0.26), (W * 0.84, H * 0.74), (W * 0.72, H * 0.8)], GLASS, line=2)   # 前擋
    s.poly([(W * 0.3, H * 0.22), (W * 0.22, H * 0.28), (W * 0.22, H * 0.72), (W * 0.3, H * 0.78)], GLASS, line=2)   # 後擋
    s.ellipse(W - 30, H * 0.16, W - 12, H * 0.3, (244, 234, 200, 255), line=1.2)     # 車燈（不亮）
    s.ellipse(W - 30, H * 0.7, W - 12, H * 0.84, (244, 234, 200, 255), line=1.2)
    return s.finish(white_border=6), (w, h)


# ============================================================ 3. 背光剪影幕（a4_c004）
SCR_W, SCR_H, SCR_PPU = 11.0, 5.2, 200
SIL = (58, 44, 34, 255)


def screen():
    W, H = int(SCR_W * SCR_PPU), int(SCR_H * SCR_PPU)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx / W - 0.5) * 2, (yy / H - 0.55) * 2
    r = np.sqrt((nx * 0.8) ** 2 + (ny * 1.0) ** 2)
    c0 = np.array([255, 238, 206], np.float32)
    c1 = np.array([226, 182, 128], np.float32)
    k = np.clip(r, 0, 1) ** 1.7
    rgb = c0[None, None] * (1 - k[..., None]) + c1[None, None] * k[..., None]
    tex = P.paper_tex(W, H)
    # 背光的紙：纖維看起來比較暗、比較明顯
    tex2 = 1 + (tex - 1) * 2.2
    rgb *= tex2[..., None]
    a = np.zeros((H, W, 4), np.float32)
    a[..., :3] = rgb
    a[..., 3] = 255
    # 外框：牛皮紙摺邊
    fr = int(0.16 * SCR_PPU)
    fm = (xx < fr) | (xx > W - fr) | (yy < fr) | (yy > H - fr)
    frame = np.array([150, 112, 74], np.float32) * tex[..., None]
    a[fm, :3] = frame[fm]
    inner = (np.abs(xx - fr) < 3) | (np.abs(xx - (W - fr)) < 3) | (np.abs(yy - fr) < 3) | (np.abs(yy - (H - fr)) < 3)
    a[inner & ~fm, :3] = np.array([110, 80, 54])
    return np.clip(a, 0, 255).astype(np.uint8)


def sil_ground():
    """地面剪影（路面＋路緣；右邊一段斑馬線用亮縫表示）"""
    w, h = SCR_W - 0.34, 0.62
    W, H = int(w * SCR_PPU), int(h * SCR_PPU)
    s = P.Sheet(W, H, ss=1)
    s.rect(0, int(H * 0.22), W, H, SIL, line=0)
    s.rect(0, int(H * 0.08), W, int(H * 0.24), (74, 58, 44, 255), line=0)
    zx0, zx1 = int(W * 0.66), int(W * 0.86)
    n = 7
    for i in range(n):
        x0 = zx0 + (zx1 - zx0) * i / n + 6
        s.rect(x0, int(H * 0.3), x0 + (zx1 - zx0) / n * 0.5, int(H * 0.5), (0, 0, 0, 0), line=0)
    return s.finish(), (w, h)


def sil_car():
    """車子剪影（側面、車頭朝右）：前窗裡是駕駛、後窗裡是乘客（都是通用人形）"""
    w, h = 3.4, 1.62
    PPW = SCR_PPU
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    body = [(20, H - 70), (16, H * 0.5), (40, H * 0.44), (W * 0.2, H * 0.4), (W * 0.32, H * 0.12), (W * 0.66, H * 0.1), (W * 0.8, H * 0.38),
            (W - 30, H * 0.46), (W - 10, H * 0.56), (W - 12, H - 70)]
    s.poly(body, SIL, line=0)
    s.rect(20, H - 90, W - 14, H - 44, SIL, line=0)
    for cx in (W * 0.22, W * 0.78):
        s.ellipse(cx - 66, H - 132, cx + 66, H, SIL, line=0)
    # 窗（挖空，透出背光）
    win_r = [(W * 0.52, H * 0.17), (W * 0.64, H * 0.16), (W * 0.76, H * 0.38), (W * 0.52, H * 0.4)]
    win_f = [(W * 0.34, H * 0.18), (W * 0.49, H * 0.17), (W * 0.49, H * 0.4), (W * 0.24, H * 0.41)]
    for poly in (win_r, win_f):
        s.poly(poly, (0, 0, 0, 0), line=0)
    # 駕駛（前窗，頭肩＋雙手握方向盤）；乘客（後窗，個子小一點）
    def person(cx, top, scale):
        r = 26 * scale
        s.ellipse(cx - r, top, cx + r, top + 2 * r, SIL, line=0)
        s.poly([(cx - 46 * scale, top + 2 * r + 60 * scale), (cx - 34 * scale, top + 2 * r + 8 * scale), (cx + 34 * scale, top + 2 * r + 8 * scale),
                (cx + 46 * scale, top + 2 * r + 60 * scale)], SIL, line=0)
    person(W * 0.64, H * 0.2, 1.0)
    s.line([(W * 0.69, H * 0.36), (W * 0.74, H * 0.3)], 9, SIL)        # 手與方向盤
    s.ellipse(W * 0.725, H * 0.26, W * 0.765, H * 0.36, SIL, line=0)
    person(W * 0.41, H * 0.25, 0.8)
    a = s.finish()
    return a, (w, h)


def sil_walker():
    """斑馬線上背書包的路人剪影（側面、往右走）"""
    w, h = 0.95, 1.95
    PPW = SCR_PPU
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    cx = W * 0.48
    s.ellipse(cx - 30, 8, cx + 30, 72, SIL, line=0)                                     # 頭
    s.poly([(cx - 34, 84), (cx + 30, 84), (cx + 38, 220), (cx - 30, 228)], SIL, line=0)   # 身體
    s.rect(cx - 80, 92, cx - 22, 210, SIL, line=0, r=18)                               # 書包
    s.line([(cx - 8, 220), (cx - 52, H - 22)], 26, SIL)                                # 後腳
    s.line([(cx + 10, 220), (cx + 56, H - 26)], 26, SIL)                               # 前腳
    s.ellipse(cx - 74, H - 34, cx - 28, H - 8, SIL, line=0)
    s.ellipse(cx + 40, H - 38, cx + 86, H - 12, SIL, line=0)
    s.line([(cx + 18, 100), (cx + 50, 170)], 18, SIL)                                  # 手
    return s.finish(), (w, h)


# ============================================================ 4. 校門口第四幕道具
def key_prop():
    """車鑰匙：圓環鑰匙頭＋鑰匙齒＋小紙牌（無字）"""
    w, h = 0.40, 0.22
    PPW = 1000
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    brass, brass2 = (214, 176, 84, 255), (186, 148, 66, 255)
    cy = H * 0.5
    s.ellipse(14, cy - 18, 50, cy + 18, (150, 150, 150, 255), line=2)          # 鑰匙圈
    s.ellipse(22, cy - 10, 42, cy + 10, (0, 0, 0, 0), line=0)
    s.ellipse(40, cy - 44, 128, cy + 44, brass, line=2.4)                        # 鑰匙頭
    s.ellipse(58, cy - 12, 82, cy + 12, (0, 0, 0, 0), line=2)
    s.rect(122, cy - 13, W - 40, cy + 13, brass2, line=2.2)                      # 鑰匙身
    teeth = [(W - 160, cy + 13), (W - 148, cy + 34), (W - 132, cy + 13), (W - 112, cy + 13), (W - 100, cy + 30), (W - 84, cy + 13), (W - 60, cy + 13), (W - 50, cy + 26), (W - 40, cy + 13)]
    s.poly(teeth + [(W - 40, cy + 12), (W - 160, cy + 12)], brass2, line=2)
    s.rect(4, cy + 20, 50, H - 6, (126, 170, 172, 255), line=2, r=8)             # 小紙牌（無字）
    return s.finish(white_border=6), (w, h)


def flag_prop():
    """導護旗：黃綠色小旗（無字、無圖案）＋短竹柄；握點在柄的下段"""
    w, h = 0.78, 1.3
    PPW = 400
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    s.rect(W * 0.12, 10, W * 0.12 + 16, H - 6, (176, 138, 92, 255), line=1.8)
    s.poly([(W * 0.12 + 16, 18), (W - 12, 40), (W - 30, H * 0.33), (W * 0.12 + 16, H * 0.42)], (214, 224, 84, 255), line=2.4)
    s.line([(W * 0.12 + 22, H * 0.2), (W - 40, H * 0.22)], 7, (242, 238, 214, 255))
    return s.finish(white_border=6), (w, h)


def phone_prop():
    """林老師的手機（深灰圓角、螢幕淡灰沒有內容）"""
    w, h = 0.13, 0.24
    PPW = 1000
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    s.rect(4, 4, W - 4, H - 4, (70, 74, 82, 255), line=2.4, r=16)
    s.rect(14, 22, W - 14, H - 30, (176, 190, 196, 255), line=1.6, r=6)
    return s.finish(white_border=5), (w, h)


def lin_back():
    """警衛室窗內的林老師小背影（低髮髻、深紅開襟衫、右手拿手機貼耳；看不到臉）"""
    w, h = 0.95, 1.1
    PPW = 300
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    hair, cardi, cardi2, skin = (58, 44, 38, 255), (128, 42, 48, 255), (110, 34, 40, 255), (232, 190, 156, 255)
    cx = W * 0.5
    s.poly([(cx - 120, H), (cx - 112, H * 0.62), (cx - 70, H * 0.5), (cx + 70, H * 0.5), (cx + 112, H * 0.62), (cx + 120, H)], cardi, line=2)
    s.line([(cx - 4, H * 0.56), (cx - 4, H)], 2, cardi2)
    s.rect(cx - 22, H * 0.42, cx + 22, H * 0.54, skin, line=1.8)                       # 脖子
    s.ellipse(cx - 56, H * 0.1, cx + 56, H * 0.48, hair, line=2)                         # 後腦（頭髮）
    s.ellipse(cx - 26, H * 0.36, cx + 26, H * 0.5, (70, 54, 46, 255), line=2)            # 低髮髻
    s.poly([(cx + 70, H * 0.58), (cx + 108, H * 0.4), (cx + 82, H * 0.28), (cx + 54, H * 0.3), (cx + 60, H * 0.5)], cardi2, line=2)   # 抬起的手臂
    s.rect(cx + 44, H * 0.2, cx + 70, H * 0.34, (80, 84, 90, 255), line=1.6, r=4)       # 手機
    s.ellipse(cx + 48, H * 0.26, cx + 80, H * 0.36, skin, line=1.6)                       # 手
    return s.finish(white_border=5), (w, h)


def walkers(kind):
    """遠景家長牽孩子離開（平塗灰藍剪影紙片，沒有五官）"""
    w, h = 1.7, 3.1
    PPW = 130
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    col = (132, 146, 160, 255) if kind == "a" else (146, 150, 132, 255)
    col2 = tuple(int(c * 0.88) for c in col[:3]) + (255,)
    g = H - 4
    # 大人（左）
    ax = W * 0.36
    s.ellipse(ax - 22, 10, ax + 22, 58, col, line=1.6)
    s.poly([(ax - 34, 64), (ax + 34, 64), (ax + 40, H * 0.58), (ax - 40, H * 0.58)], col, line=1.6)
    s.line([(ax - 14, H * 0.56), (ax - 24, g - 6)], 18, col2)
    s.line([(ax + 14, H * 0.56), (ax + 26, g - 6)], 18, col2)
    if kind == "a":
        s.rect(ax - 62, H * 0.36, ax - 36, H * 0.5, col2, line=1.4, r=5)    # 提袋
    s.line([(ax + 34, 80), (ax + 58, H * 0.44)], 13, col)                   # 牽手的手臂
    # 小孩（右）
    cxk = W * 0.72
    top = H * 0.36
    s.ellipse(cxk - 17, top, cxk + 17, top + 36, col, line=1.6)
    s.poly([(cxk - 24, top + 40), (cxk + 24, top + 40), (cxk + 28, H * 0.78), (cxk - 28, H * 0.78)], col, line=1.6)
    s.rect(cxk + 14, top + 46, cxk + 36, top + 96, col2, line=1.4, r=6)     # 小書包
    s.line([(cxk - 24, top + 50), (ax + 58, H * 0.46)], 11, col)
    s.line([(cxk - 9, H * 0.77), (cxk - 16, g - 4)], 13, col2)
    s.line([(cxk + 9, H * 0.77), (cxk + 17, g - 4)], 13, col2)
    return s.finish(), (w, h)


def lantern():
    """騎樓下的小紙燈籠（暖米橘、低彩度；不發光）＋吊繩；鉸點在繩的上端"""
    w, h = 0.46, 1.0
    PPW = 300
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    cx = W / 2
    s.line([(cx, 0), (cx, H * 0.36)], 3, (110, 90, 70, 255))
    s.rect(cx - 26, H * 0.34, cx + 26, H * 0.4, (150, 108, 70, 255), line=1.6)
    s.ellipse(cx - 62, H * 0.38, cx + 62, H * 0.88, (232, 174, 118, 255), line=2)
    for k in (-0.5, 0, 0.5):
        s.line([(cx + k * 60, H * 0.4), (cx + k * 66, H * 0.86)], 1.5, (196, 136, 86, 255))
    s.rect(cx - 26, H * 0.86, cx + 26, H * 0.92, (150, 108, 70, 255), line=1.6)
    s.line([(cx, H * 0.92), (cx, H - 4)], 3, (190, 140, 90, 255))
    return s.finish(), (w, h)


# ============================================================ 5. 陳伯伯伸手接鑰匙（改畫前臂）
def chen_receive():
    """陳伯伯伸手接鑰匙：畫面左側（他的右手）整段手臂以袖口下為軸往外轉 38°，手伸向左前方；
    轉軸藏在袖子下面（手臂畫在袖子後面），頭臉、身體不動。"""
    src = Image.open(ROOT / "assets/final/chr-chen_master_v01.png").convert("RGBA")
    a = np.array(src)
    H, W = a.shape[:2]
    pad = 170                          # 往左加寬（伸出去的手）
    big = np.zeros((H, W + pad, 4), np.uint8)
    big[:, pad:] = a
    alpha = big[..., 3]
    yy, xx = np.mgrid[0:H, 0:W + pad]
    ox = xx - pad                      # 原圖座標
    rgb = big[..., :3].astype(np.int32)
    skin = (rgb[..., 0] > 200) & (rgb[..., 1] > 130) & (rgb[..., 1] < 205) & (rgb[..., 2] < 175) & (rgb[..., 0] - rgb[..., 2] > 45)
    y0 = 588
    piece_m = (alpha > 0) & (yy >= y0) & (yy < 985) & ((ox < 104) | ((ox < 124) & skin) | ((ox < 126) & (yy >= 834)))
    piece_m = ndimage.binary_opening(piece_m, iterations=1)
    piece = np.zeros_like(big)
    piece[piece_m] = big[piece_m]
    rest = big.copy()
    rest[piece_m] = 0
    pivot = (pad + 86, 600)
    ang = 38
    rot = np.array(Image.fromarray(piece, "RGBA").rotate(-ang, center=pivot, resample=Image.BICUBIC))
    # 手臂在袖子後面；袖口外那圈白邊若蓋到轉出來的手臂，就讓手臂露出來
    r3 = rest[..., :3].astype(np.int32)
    whiteish = (r3.min(axis=2) > 228) & (rest[..., 3] > 0)
    show_arm = whiteish & (rot[..., 3] > 0) & (yy > 560) & (yy < 660)
    out = Image.fromarray(rot, "RGBA")
    rest2 = rest.copy()
    rest2[show_arm] = 0
    out.alpha_composite(Image.fromarray(rest2, "RGBA"))
    o = np.array(out).astype(np.float32)
    # 新露出的身體側邊與轉過去的手臂：補一圈白色紙芯邊（只在改過的範圍內）
    m = o[..., 3] >= 128
    box = (yy >= 560) & (yy <= 1040) & (xx <= pad + 132)
    dist = ndimage.distance_transform_edt(~m)
    ring = (dist > 0) & (dist <= 11) & box
    o[ring, :3] = np.array([250, 246, 238]) * P.paper_tex(W + pad, H)[ring][:, None]
    o[ring, 3] = 255
    dl = ndimage.distance_transform_edt(m)
    line = m & (dl <= 2.0) & box & ndimage.binary_dilation(ring, iterations=2)
    o[line, :3] = o[line, :3] * 0.3 + np.array([70, 56, 46]) * 0.7
    # 手掌中心（旋轉後）：原圖手心約（70, 900）
    hx, hy = pad + 70, 900
    th = math.radians(ang)
    dx, dy = hx - pivot[0], hy - pivot[1]
    nx = pivot[0] + dx * math.cos(th) - dy * math.sin(th)
    ny = pivot[1] + dx * math.sin(th) + dy * math.cos(th)
    return np.clip(o, 0, 255).astype(np.uint8), {"pad_left_px": pad, "palm_px": [round(nx, 1), round(ny, 1)], "pivot_px": list(pivot), "angle_deg": ang}


def lin_standr():
    """林老師轉身朝右（a4_c013 走進辦公室前紙片翻面）：林老師站姿原圖左右鏡射（原圖臉朝畫面左）"""
    src = Image.open(ROOT / "assets/final/chr-lin_master_v01.png").convert("RGBA")
    return np.array(src.transpose(Image.FLIP_LEFT_RIGHT))


def main():
    meta = {"made_by": "review/G5/a4/scripts/build_a4_art.py", "map": {"size_world": [MAP_W, MAP_H], "center_world": [-5.0, 0.0], "ppu": MAP_PPU,
            "road_v": ROAD_V, "side_u": SIDE_U, "zebra_u": ZEBRA_U, "stop_u": STOP_U}}
    P.save(draw_map(), MAP_DIR / "set-a4map_map_v01.png")
    pops = {}
    for k in ("a", "b", "c", "d"):
        a, wh = house(k)
        P.save(a, MAP_DIR / f"set-a4map_house-{k}_v01.png")
        pops[f"house-{k}"] = wh
    for name, fn in (("school", school), ("gatepost", gatepost), ("walker", walker_map), ("car", car_top)):
        a, wh = fn()
        P.save(a, MAP_DIR / f"set-a4map_{name}_v01.png")
        pops[name] = wh
    a, wh = tree(3)
    P.save(a, MAP_DIR / "set-a4map_tree_v01.png")
    pops["tree"] = wh
    P.save(screen(), MAP_DIR / "set-a4map_screen_v01.png")
    pops["screen"] = (SCR_W, SCR_H)
    for name, fn in (("sil-ground", sil_ground), ("sil-car", sil_car), ("sil-walker", sil_walker)):
        a, wh = fn()
        P.save(a, MAP_DIR / f"set-a4map_{name}_v01.png")
        pops[name] = wh
    for name, fn in (("a4-phone", phone_prop), ("a4-key", key_prop), ("a4-flag", flag_prop), ("a4-lin-back", lin_back), ("a4-lantern", lantern)):
        a, wh = fn()
        P.save(a, GATE / f"set-gate_{name}_v01.png")
        pops[name] = wh
    for k in ("a", "b"):
        a, wh = walkers(k)
        P.save(a, GATE / f"set-gate_a4-walkers-{k}_v01.png")
        pops[f"a4-walkers-{k}"] = wh
    P.save(lin_standr(), ROOT / "assets/final/chr-lin_pose-standr_v01.png")
    a, m = chen_receive()
    P.save(a, ROOT / "assets/final/chr-chen_pose-receive_v01.png")
    meta["chen_receive"] = m
    meta["sizes_world"] = {k: [round(v[0], 3), round(v[1], 3)] for k, v in pops.items()}
    (ROOT / "review/G5/a4/art_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
