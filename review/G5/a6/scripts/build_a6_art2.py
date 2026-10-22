"""第六幕代理（第二次執行）：程式繪製的景片第二批（Pillow＋G2 同款紙紋；圖裡沒有任何文字、數字、標誌）。

用法：/opt/anaconda3/bin/python3 review/G5/a6/scripts/build_a6_art2.py
輸出：
- assets/final/sets/a6_window/tree-winter_v02.png、tree-spring_v02.png   冬（枝條從樹幹分岔長出）、春（同枝條＋新芽與小花）
- assets/final/sets/a6_window/room_v01.png        室內牆（暖米色紙）＋木窗框（窗洞透明、十字窗櫺）＋窗台＋踢腳板
- assets/final/sets/a6_window/sky-{autumn,winter,spring,summer}_v01.png   窗外天空（平塗漸層＋剪紙雲）
- assets/final/sets/a6_window/shelf_v01.png、plant_v01.png      室內小物（矮櫃上一盞沒點的紙燈籠、盆栽）
- assets/final/sets/a6_window/leaf_v01.png        秋天飄落的葉子（一片）
- assets/final/sets/a6_square_night/rack_v02.png  燈籠架（加高：燈籠掛在孩子頭頂上方，孩子站在架子後面的角落）
- assets/final/sets/a6_square_night/folk-{a,b,c,d}_v01.png   一起糊燈籠紙的鎮民（背影、不透明紙片小人，沒有五官；中性設計）
- assets/final/sets/a6_square_night/table_v01.png 糊紙用的長桌（漿糊碗、紙捲）
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as PD  # noqa: E402

FIN = ROOT / "assets/final/sets"
INK = PD.INK


# ───────────────────────────── 樹（冬、春） ─────────────────────────────
def hsv_arr(rgb):
    r, g, b = [rgb[..., i] / 255.0 for i in range(3)]
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0)
    return h, s, mx


def bare_tree():
    """去葉的樹幹＋從各分岔頂端長出的枝條；回傳 (RGBA float 陣列, 枝梢座標表)。"""
    src = np.array(Image.open(FIN / "square/set-square_tree-a_v01.png").convert("RGBA")).astype(np.float32)
    rgb, al = src[..., :3], src[..., 3]
    h, s, v = hsv_arr(rgb)
    leaf = (al > 0) & (h > 48) & (h < 170) & (s > 0.18)
    leaf = ndimage.binary_closing(leaf, iterations=2) & (al > 0)
    trunk = (al > 128) & ~leaf
    H, W = al.shape
    # 只留和地面相連的最大樹幹塊（去掉被葉子切斷的小碎片）
    lab, n = ndimage.label(trunk)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    main = lab == (1 + int(np.argmax(sizes)))
    a = src.copy()
    a[..., 3] = np.where(main, al, 0)
    tcol = tuple(int(c) for c in np.median(rgb[main & (np.arange(H)[:, None] > H * 0.7)], 0)) + (255,)
    ys, xs = np.nonzero(main)
    ytop = ys.min()
    yfork = int(ytop + 0.25 * (ys.max() - ytop))
    # 分岔：樹幹上段（ytop～yfork）的各個連通塊，各取最高點與方向
    upper = main.copy()
    upper[yfork:] = False
    lab2, n2 = ndimage.label(upper)
    tips = []
    for k in range(1, n2 + 1):
        yy, xx = np.nonzero(lab2 == k)
        if len(yy) < 60:
            continue
        i = int(np.argmin(yy))
        tx, ty = float(xx[i]), float(yy[i])
        cx, cy = float(xx.mean()), float(yy.max())
        ang = math.atan2(cy - ty, tx - cx) if (cy - ty) > 1 else math.pi / 2
        w = max(6.0, float((lab2 == k)[int(ty) + 12].sum()) if int(ty) + 12 < H else 8.0)
        tips.append((tx, ty + 6, ang, w))
    sh = PD.Sheet(W, H, ss=2)
    rng = np.random.default_rng(11)
    ends = []

    def branch(x, y, ang, length, width, depth):
        if depth == 0 or length < 16:
            ends.append((x, y, ang))
            return
        x2, y2 = x + length * math.cos(ang), y - length * math.sin(ang)
        sh.d.line([(x * 2, y * 2), (x2 * 2, y2 * 2)], fill=tcol, width=max(2, int(width * 2)), joint="curve")
        sh.d.ellipse([(x2 - width / 2) * 2, (y2 - width / 2) * 2, (x2 + width / 2) * 2, (y2 + width / 2) * 2], fill=tcol)
        for da in (-0.40 - 0.22 * rng.random(), 0.36 + 0.22 * rng.random()):
            branch(x2, y2, ang + da, length * (0.68 + 0.1 * rng.random()), width * 0.68, depth - 1)

    if not tips:
        tips = [(W / 2, ytop + 10, math.pi / 2, 16)]
    for tx, ty, ang, w in tips:
        branch(tx, ty, ang, 120 + 30 * rng.random(), min(18, w * 0.8), 5)
    br = np.array(sh.img.resize((W, H), Image.LANCZOS)).astype(np.float32)
    m = br[..., 3] > 0
    put = m & (a[..., 3] < br[..., 3])
    a[put] = br[put]
    edge = ndimage.binary_dilation(br[..., 3] > 128, iterations=2) & ~(br[..., 3] > 128) & (a[..., 3] < 10)
    a[edge, :3] = np.array(INK[:3]); a[edge, 3] = 255
    tex = PD.paper_tex(W, H)
    a[..., :3] = np.clip(a[..., :3] * np.where(m[..., None], tex[..., None], 1.0), 0, 255)
    return a, ends


def season_trees_v2():
    winter, ends = bare_tree()
    PD.save(np.clip(winter, 0, 255).astype(np.uint8), FIN / "a6_window/tree-winter_v02.png")
    # 春：同樣的枝條＋枝梢的新芽（淺綠小葉團）與幾朵淡粉小花
    H, W = winter.shape[:2]
    sh = PD.Sheet(W, H, ss=2)
    rng = np.random.default_rng(23)
    for (x, y, ang) in ends:
        if rng.random() < 0.9:
            r = 15 + 9 * rng.random()
            for k in range(3):
                ox, oy = (k - 1) * r * 0.7, -abs(k - 1) * r * 0.25
                col = (168, 204, 120, 255) if (k + int(x)) % 3 else (142, 186, 104, 255)
                sh.ellipse(x + ox - r * 0.6, y + oy - r * 0.45, x + ox + r * 0.6, y + oy + r * 0.45, col, line=1.2)
        if rng.random() < 0.35:
            r = 11
            sh.ellipse(x - r + 6, y - r - 4, x + r + 6, y + r - 4, (246, 206, 214, 255), line=1.2)
            sh.ellipse(x + 3, y - 7, x + 9, y - 1, (238, 190, 120, 255), line=0)
    buds = sh.finish()
    a = winter.copy()
    bm = buds[..., 3].astype(np.float32) / 255.0
    a[..., :3] = a[..., :3] * (1 - bm[..., None]) + buds[..., :3] * bm[..., None]
    a[..., 3] = np.maximum(a[..., 3], buds[..., 3])
    PD.save(np.clip(a, 0, 255).astype(np.uint8), FIN / "a6_window/tree-spring_v02.png")


# ───────────────────────────── 室內牆與窗 ─────────────────────────────
PPU = 160          # 室內牆：每世界單位幾像素
ROOM = {"w": 13.0, "h": 6.8, "x0": -6.2}   # 牆左緣世界 x、寬、高（地面 y=0 起）
WIN = {"x0": -1.75, "x1": 3.05, "y0": 1.3, "y1": 4.25}   # 窗洞（世界座標）


def room():
    W, H = int(ROOM["w"] * PPU), int(ROOM["h"] * PPU)
    sh = PD.Sheet(W, H, ss=1)
    X = lambda x: (x - ROOM["x0"]) * PPU   # noqa: E731
    Y = lambda y: H - y * PPU               # noqa: E731
    wall = (238, 224, 198, 255)
    sh.rect(0, 0, W, H, wall, line=0)
    # 腰板（木色）＋踢腳板
    sh.rect(0, Y(1.05), W, H, (206, 176, 136, 255), line=0)
    sh.line([(0, Y(1.05)), (W, Y(1.05))], w=3)
    for x in np.arange(ROOM["x0"] + 0.55, ROOM["x0"] + ROOM["w"], 0.62):
        sh.line([(X(x), Y(1.0)), (X(x), Y(0.14))], w=1.4, color=(170, 136, 98, 255))
    sh.rect(0, Y(0.14), W, H, (150, 112, 78, 255), line=0)
    sh.line([(0, Y(0.14)), (W, Y(0.14))], w=2.5)
    # 牆上淡淡的紙紋直條（壁紙接縫）
    for x in np.arange(ROOM["x0"] + 1.3, ROOM["x0"] + ROOM["w"], 1.3):
        sh.line([(X(x), 0), (X(x), Y(1.06))], w=1.0, color=(226, 210, 182, 255))
    # 窗框（外框＋窗台）
    fx0, fx1, fy0, fy1 = WIN["x0"], WIN["x1"], WIN["y0"], WIN["y1"]
    fw = 0.16
    wood, wood2 = (150, 106, 70, 255), (128, 88, 58, 255)
    sh.rect(X(fx0 - fw), Y(fy1 + fw), X(fx1 + fw), Y(fy0 - fw * 0.5), wood, line=2.5)
    sh.rect(X(fx0 - fw - 0.18), Y(fy0 + 0.02), X(fx1 + fw + 0.18), Y(fy0 - 0.2), wood2, line=2.5)
    sh.rect(X(fx0 - fw - 0.1), Y(fy0 - 0.2), X(fx1 + fw + 0.1), Y(fy0 - 0.3), (110, 76, 50, 255), line=1.5)
    # 窗櫺（十字）先畫，窗洞再挖
    cx = (fx0 + fx1) / 2
    cy = fy0 + (fy1 - fy0) * 0.55
    sh.hole(X(fx0), Y(fy1), X(fx1), Y(fy0))
    sh.rect(X(cx - 0.055), Y(fy1), X(cx + 0.055), Y(fy0), wood, line=1.8)
    sh.rect(X(fx0), Y(cy + 0.05), X(fx1), Y(cy - 0.05), wood, line=1.8)
    # 窗框內緣細邊
    sh.line([(X(fx0), Y(fy1)), (X(fx1), Y(fy1)), (X(fx1), Y(fy0)), (X(fx0), Y(fy0)), (X(fx0), Y(fy1))], w=2.0)
    # 布簾（兩側，束起）
    cur = (214, 168, 120, 255)
    for side in (-1, 1):
        x_out = fx0 - fw - 0.05 if side < 0 else fx1 + fw + 0.05
        x_in = x_out + side * -0.55
        pts = [(X(x_out - side * 0.05), Y(fy1 + 0.35)), (X(x_in), Y(fy1 + 0.35)), (X(x_in + side * 0.22), Y(cy - 0.1)),
               (X(x_in - side * 0.05), Y(fy0 - 0.15)), (X(x_out - side * 0.05), Y(fy0 - 0.15))]
        sh.poly(pts, cur, line=2.0)
        sh.line([(X((x_out + x_in) / 2), Y(fy1 + 0.3)), (X((x_out + x_in) / 2 + side * 0.08), Y(fy0 - 0.1))], w=1.2, color=(186, 140, 98, 255))
        sh.rect(X(x_in + side * 0.1) - 10, Y(cy - 0.05) - 6, X(x_in + side * 0.1) + 10, Y(cy - 0.05) + 6, (170, 120, 80, 255), line=1.2, r=4)
    # 布簾桿
    sh.rect(X(fx0 - 0.9), Y(fy1 + 0.42), X(fx1 + 0.9), Y(fy1 + 0.34), (120, 84, 56, 255), line=1.5, r=3)
    a = sh.finish()
    PD.save(a, FIN / "a6_window/room_v01.png")
    return {"ppu": PPU, "room": ROOM, "win": WIN}


def sky(name, stops, clouds, sun=None):
    W, H = 1024, 640
    y = np.linspace(0, 1, H)[:, None]
    col = np.zeros((H, 1, 3), np.float32)
    for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
        m = (y >= y0) & (y <= y1)
        u = np.clip((y - y0) / (y1 - y0), 0, 1)
        col = np.where(m[..., None], np.array(c0) + (np.array(c1) - np.array(c0)) * u[..., None], col)
    img = np.repeat(col, W, 1)
    sh = PD.Sheet(W, H, ss=1)
    sh.img = Image.fromarray(np.dstack([img.astype(np.uint8), np.full((H, W), 255, np.uint8)]), "RGBA")
    sh.d = ImageDraw.Draw(sh.img)
    if sun:
        sh.ellipse(sun[0] - sun[2], sun[1] - sun[2], sun[0] + sun[2], sun[1] + sun[2], sun[3], line=2)
    for cx, cy, s, c in clouds:
        for k in range(5):
            r = (48 + 10 * ((k * 7) % 3)) * s
            ox = (k - 2) * 52 * s
            oy = -(14 * s if k in (1, 3) else 0) - (24 * s if k == 2 else 0)
            sh.d.ellipse([cx + ox - r, cy + oy - r * 0.6, cx + ox + r, cy + oy + r * 0.6], fill=c)
    PD.save(sh.finish(), FIN / f"a6_window/sky-{name}_v01.png")


def skies():
    sky("autumn", [(0, (150, 178, 206)), (0.6, (214, 210, 196)), (1, (238, 214, 172))],
        [(260, 170, 1.0, (244, 236, 222, 255)), (760, 120, 0.8, (246, 238, 224, 255))])
    sky("winter", [(0, (168, 180, 196)), (0.7, (206, 210, 214)), (1, (224, 222, 216))],
        [(300, 150, 1.2, (228, 230, 232, 255)), (800, 220, 1.0, (230, 232, 234, 255)), (540, 380, 0.7, (222, 224, 228, 255))])
    sky("spring", [(0, (150, 196, 226)), (0.65, (204, 226, 236)), (1, (238, 232, 222))],
        [(220, 140, 0.9, (250, 248, 244, 255)), (720, 210, 0.75, (250, 248, 244, 255))])
    sky("summer", [(0, (96, 160, 214)), (0.6, (160, 204, 232)), (1, (214, 232, 238))],
        [(320, 160, 1.15, (252, 252, 250, 255)), (820, 110, 0.9, (252, 252, 250, 255))], sun=(860, 300, 46, (252, 236, 170, 255)))


def shelf():
    W, H = 520, 560
    sh = PD.Sheet(W, H, ss=2)
    wood = (168, 124, 84, 255)
    sh.rect(20, 250, 500, 540, wood, line=2.5, r=6)
    sh.rect(46, 280, 254, 520, (186, 142, 100, 255), line=2)
    sh.rect(266, 280, 474, 520, (186, 142, 100, 255), line=2)
    sh.ellipse(140, 392, 160, 412, (120, 84, 56, 255), line=1)
    sh.ellipse(360, 392, 380, 412, (120, 84, 56, 255), line=1)
    # 櫃上一盞沒點的小紙燈籠＋一疊摺紙
    cx, cy, r = 170, 126, 78
    sh.rect(cx - 26, cy - r - 22, cx + 26, cy - r + 2, (130, 92, 60, 255), line=1.5)
    sh.ellipse(cx - r, cy - r * 0.95, cx + r, cy + r * 0.95, (246, 214, 168, 255), line=2.2)
    for k in (-0.55, 0.0, 0.55):
        w = r * math.sqrt(max(0, 1 - k * k))
        sh.d.arc([(cx - w) * 2, (cy - r * 0.95) * 2, (cx + w) * 2, (cy + r * 0.95) * 2], 0, 360, fill=(170, 116, 70, 255), width=3)
    sh.rect(cx - 26, cy + r - 2, cx + 26, cy + r + 22, (130, 92, 60, 255), line=1.5)
    sh.rect(cx - 50, cy + r + 22, cx + 50, 250, (150, 108, 72, 255), line=1.5)
    for i, c in enumerate([(232, 160, 110, 255), (150, 190, 170, 255), (240, 214, 140, 255)]):
        sh.poly([(320 + i * 8, 236 - i * 14), (440 + i * 6, 230 - i * 14), (450 + i * 6, 246 - i * 14), (316 + i * 8, 250 - i * 14)], c, line=1.5)
    PD.save(sh.finish(), FIN / "a6_window/shelf_v01.png")


def plant():
    W, H = 420, 700
    sh = PD.Sheet(W, H, ss=2)
    rng = np.random.default_rng(5)
    for k in range(9):
        a = math.pi / 2 + (k - 4) * 0.27 + rng.uniform(-0.06, 0.06)
        L = 300 + rng.uniform(-40, 60)
        x0, y0 = 210, 470
        x1, y1 = x0 + L * math.cos(a), y0 - L * math.sin(a)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        nx, ny = -math.sin(a) * 34, -math.cos(a) * 34
        col = (96, 146, 98, 255) if k % 2 else (120, 168, 112, 255)
        sh.poly([(x0, y0), (mx + nx, my + ny), (x1, y1), (mx - nx, my - ny)], col, line=1.8)
        sh.line([(x0, y0), (x1, y1)], w=1.2, color=(70, 110, 74, 255))
    sh.poly([(110, 460), (310, 460), (288, 690), (132, 690)], (196, 120, 86, 255), line=2.5)
    sh.rect(98, 446, 322, 478, (176, 104, 74, 255), line=2.2, r=4)
    PD.save(sh.finish(), FIN / "a6_window/plant_v01.png")


def leaf():
    W, H = 120, 90
    sh = PD.Sheet(W, H, ss=3)
    sh.poly([(10, 45), (40, 14), (82, 10), (110, 40), (84, 74), (40, 78)], (226, 160, 64, 255), line=2)
    sh.line([(14, 46), (106, 40)], w=1.4, color=(170, 104, 40, 255))
    PD.save(sh.finish(), FIN / "a6_window/leaf_v01.png")


# ───────────────────────────── 夜晚廣場：燈籠架、鎮民、長桌 ─────────────────────────────
def lantern(sh, cx, cy, r, color, rib=(150, 96, 60, 255)):
    sh.line([(cx, cy - r * 1.6), (cx, cy - r * 0.95)], w=2.2)
    sh.rect(cx - r * 0.32, cy - r * 1.02, cx + r * 0.32, cy - r * 0.86, (120, 82, 50, 255), line=1.5)
    sh.ellipse(cx - r, cy - r * 0.9, cx + r, cy + r * 0.9, color, line=2.2)
    for k in (-0.55, 0.0, 0.55):
        w = r * math.sqrt(max(0, 1 - k * k))
        sh.d.arc([(cx - w) * sh.ss, (cy - r * 0.9) * sh.ss, (cx + w) * sh.ss, (cy + r * 0.9) * sh.ss], 0, 360, fill=rib, width=int(1.6 * sh.ss))
    sh.rect(cx - r * 0.32, cy + r * 0.86, cx + r * 0.32, cy + r * 1.02, (120, 82, 50, 255), line=1.5)
    sh.line([(cx, cy + r * 1.02), (cx, cy + r * 1.35)], w=2.0, color=(196, 92, 70, 255))


def rack2():
    """寬 1100、高 1100（世界寬 4.6 → 高 4.6）：橫樑在上緣，燈籠中心約 3.9 世界單位高（孩子頭頂 2.45、大人 3.4 之上）。"""
    W, H = 1100, 1100
    sh = PD.Sheet(W, H, ss=2)
    bam, node = (176, 132, 78, 255), (138, 98, 56, 255)
    for x0 in (30, W - 30 - 22):
        sh.rect(x0, 50, x0 + 22, H - 4, bam, line=2)
        for y in range(150, H - 20, 170):
            sh.rect(x0 - 3, y, x0 + 25, y + 8, node, line=1.2)
        # 斜撐腳
        sh.poly([(x0 - 26, H - 4), (x0 + 48, H - 4), (x0 + 22, H - 60), (x0, H - 60)], node, line=1.6)
    sh.rect(6, 42, W - 6, 68, bam, line=2)
    for cx, r, c in [(200, 54, (246, 196, 140, 255)), (395, 48, (244, 216, 160, 255)), (575, 56, (238, 170, 120, 255)),
                     (760, 50, (246, 206, 150, 255)), (925, 46, (240, 186, 132, 255))]:
        lantern(sh, cx, 68 + r * 1.6 + 26, r, c)
    # 橫樑上晾著幾張燈籠紙（糊燈籠用）
    for x, c in [(300, (248, 236, 214, 255)), (680, (246, 226, 196, 255)), (850, (250, 240, 222, 255))]:
        sh.poly([(x, 68), (x + 52, 68), (x + 56, 148), (x + 2, 152)], c, line=1.6)
    PD.save(sh.finish(), FIN / "a6_square_night/rack_v02.png")


def person_back(sh, cx, foot, h, hair, top, pants, shoe, arms="up", child=False, sheet=None, skin=(232, 196, 166, 255)):
    """背影紙片小人（沒有五官）：頭（後腦頭髮）、脖子、上衣、褲子、鞋；arms＝up（舉手糊紙）／side。"""
    head_r = h * (0.095 if not child else 0.12)
    y_head = foot - h + head_r
    sh_w = h * (0.24 if not child else 0.26)
    y_sh = y_head + head_r * 1.35
    y_hip = foot - h * 0.47
    # 腿
    lw = sh_w * 0.42
    sh.poly([(cx - sh_w * 0.48, y_hip), (cx - 2, y_hip), (cx - 4, foot - h * 0.04), (cx - sh_w * 0.46, foot - h * 0.04)], pants, line=2)
    sh.poly([(cx + 2, y_hip), (cx + sh_w * 0.48, y_hip), (cx + sh_w * 0.46, foot - h * 0.04), (cx + 4, foot - h * 0.04)], pants, line=2)
    sh.ellipse(cx - sh_w * 0.5 - 4, foot - h * 0.055, cx - 2, foot + 2, shoe, line=1.8)
    sh.ellipse(cx + 2, foot - h * 0.055, cx + sh_w * 0.5 + 4, foot + 2, shoe, line=1.8)
    # 手臂（先畫，在上衣後）
    if arms == "up":
        for s in (-1, 1):
            x0 = cx + s * sh_w * 0.42
            x1 = cx + s * sh_w * 0.62
            y1 = y_head - head_r * 0.9
            sh.poly([(x0 - 9, y_sh + 6), (x0 + 9, y_sh + 2), (x1 + 8, y1), (x1 - 8, y1 + 4)], top, line=2)
            sh.ellipse(x1 - 10, y1 - 16, x1 + 10, y1 + 4, skin, line=1.6)
        if sheet:
            sx0, sx1 = cx - sh_w * 0.85, cx + sh_w * 0.85
            sy1 = y_head - head_r * 1.0
            sh.poly([(sx0, sy1 - h * 0.17), (sx1, sy1 - h * 0.19), (sx1 + 4, sy1 + 2), (sx0 - 2, sy1 + 6)], sheet, line=1.8)
    elif arms == "reach":
        # 兩手往右上方伸（把燈籠紙貼到骨架上）；站在主燈右邊的鎮民用 flipX 翻成往左上
        hx, hy = cx + sh_w * 1.05, y_head - head_r * 0.2
        aw = sh_w * 0.13
        for s, dy in ((-1, 0.0), (1, head_r * 0.7)):
            x0, y0 = cx + s * sh_w * 0.36, y_sh + aw
            x1, y1 = hx, hy + dy
            L = math.hypot(x1 - x0, y1 - y0)
            nx, ny = -(y1 - y0) / L * aw, (x1 - x0) / L * aw
            sh.poly([(x0 + nx, y0 + ny), (x1 + nx * 0.8, y1 + ny * 0.8), (x1 - nx * 0.8, y1 - ny * 0.8), (x0 - nx, y0 - ny)], top, line=2)
            sh.ellipse(x1 - aw, y1 - aw, x1 + aw, y1 + aw, skin, line=1.6)
        if sheet:
            sh.poly([(hx + 4, hy - h * 0.2), (hx + h * 0.16, hy - h * 0.17), (hx + h * 0.15, hy + h * 0.08), (hx + 2, hy + h * 0.06)], sheet, line=1.8)
    else:
        for s in (-1, 1):
            x0 = cx + s * sh_w * 0.5
            sh.poly([(x0 - 9, y_sh + 4), (x0 + 9, y_sh + 4), (x0 + s * 6 + 8, y_hip + h * 0.06), (x0 + s * 6 - 8, y_hip + h * 0.06)], top, line=2)
            sh.ellipse(x0 + s * 6 - 9, y_hip + h * 0.04, x0 + s * 6 + 9, y_hip + h * 0.09, skin, line=1.6)
    # 上衣
    sh.poly([(cx - sh_w * 0.5, y_sh), (cx + sh_w * 0.5, y_sh), (cx + sh_w * 0.46, y_hip + 6), (cx - sh_w * 0.46, y_hip + 6)], top, line=2.2)
    # 脖子＋頭（後腦，頭髮蓋住）
    sh.rect(cx - head_r * 0.35, y_head + head_r * 0.7, cx + head_r * 0.35, y_sh + 4, skin, line=1.6)
    sh.ellipse(cx - head_r * 1.08, y_head - head_r * 0.2, cx - head_r * 0.82, y_head + head_r * 0.3, skin, line=1.4)
    sh.ellipse(cx + head_r * 0.82, y_head - head_r * 0.2, cx + head_r * 1.08, y_head + head_r * 0.3, skin, line=1.4)
    sh.ellipse(cx - head_r, y_head - head_r, cx + head_r, y_head + head_r * 0.95, hair, line=2.2)


def folks():
    # (檔名, 像素寬高, 人物表)
    specs = {
        "folk-a": (560, 980, [dict(cx=210, foot=960, h=900, hair=(58, 46, 40, 255), top=(78, 120, 128, 255), pants=(70, 66, 72, 255),
                                     shoe=(60, 50, 44, 255), arms="reach", sheet=(250, 240, 220, 255))]),
        "folk-b": (560, 980, [dict(cx=210, foot=960, h=880, hair=(150, 146, 140, 255), top=(176, 120, 70, 255), pants=(92, 84, 76, 255),
                                     shoe=(70, 56, 46, 255), arms="reach", sheet=(246, 226, 190, 255))]),
        "folk-c": (360, 760, [dict(cx=180, foot=740, h=640, hair=(40, 32, 30, 255), top=(128, 84, 120, 255), pants=(64, 72, 98, 255),
                                     shoe=(220, 214, 204, 255), arms="up", child=True, sheet=(250, 236, 214, 255))]),
        "folk-d": (420, 980, [dict(cx=210, foot=960, h=900, hair=(86, 60, 44, 255), top=(96, 104, 136, 255), pants=(76, 66, 60, 255),
                                     shoe=(56, 46, 40, 255), arms="side")]),
    }
    for name, (W, H, people) in specs.items():
        sh = PD.Sheet(W, H, ss=2)
        for p in people:
            person_back(sh, **p)
        PD.save(sh.finish(white_border=6), FIN / f"a6_square_night/{name}_v01.png")


def table():
    W, H = 900, 380
    sh = PD.Sheet(W, H, ss=2)
    wood, leg = (178, 134, 90, 255), (140, 100, 66, 255)
    for x in (70, W - 70 - 26):
        sh.rect(x, 150, x + 26, H - 6, leg, line=2)
    sh.rect(20, 120, W - 20, 160, wood, line=2.5)
    # 桌上：漿糊碗、紙捲、一疊剪好的燈籠紙
    sh.ellipse(140, 84, 250, 126, (236, 230, 216, 255), line=2)
    sh.ellipse(152, 86, 238, 104, (250, 248, 240, 255), line=1.2)
    sh.rect(330, 76, 520, 120, (248, 236, 212, 255), line=2, r=18)
    sh.ellipse(500, 76, 540, 120, (232, 216, 186, 255), line=2)
    for i, c in enumerate([(246, 210, 160, 255), (250, 232, 200, 255), (244, 196, 150, 255)]):
        sh.poly([(600 + i * 6, 118 - i * 9), (780 + i * 4, 114 - i * 9), (786 + i * 4, 122 - i * 9), (596 + i * 6, 126 - i * 9)], c, line=1.5)
    PD.save(sh.finish(), FIN / "a6_square_night/table_v01.png")


def main():
    season_trees_v2()
    meta = room()
    skies()
    shelf()
    plant()
    leaf()
    rack2()
    folks()
    table()
    print("ok", meta)


if __name__ == "__main__":
    main()
