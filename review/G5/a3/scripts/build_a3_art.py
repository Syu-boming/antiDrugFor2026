"""G5 第三幕（a3）景片與小道具 —— 程式繪製的厚卡紙景片（Codex 額度只留給角色新姿勢）。

畫法沿用 G5 共用美術 review/G5/shared_art/scripts/paperdraw.py：平塗色塊＋G2 景片同款紙紋、暖深灰細線、無陰影、無方向光；
圖裡不放任何生成的文字、數字、標誌（練習卡上的字由本程式用 Noto Sans TC 粗體排版，見 practice_card()）。

輸出（assets/final/…）：
  sets/a3_classroom/  outside_v01.png（窗外：午後天空＋對面廣場騎樓屋頂）、backwall_v01.png（教室後牆，三扇窗挖空）、
                      board_v01.png（黑板＋粉筆畫的燈籠與星星，沒有字）、desk_v01.png（課桌椅一組）、
                      students_v01.png（遠景同學剪影，中性、沒有五官）、teacherdesk_v01.png（講桌）、door_v01.png（教室後門，門外走廊）、
                      floor_v01.png（木地板）、garland_v01.png（窗外燈籠串，沿用 square_a1 的燈籠串顏色、較短）
  sets/a3_arcade/     memory_v01.png（回想小圓窗：a2_c002 被操偶線拉偏的手，取自第二幕驗收包關鍵影格，褪色、手撕圓框）
  sets/a3_gate/       card_v01.png（台口前緣的練習卡：拒絕句＋口訣四格、動作小圖取自角色姿勢圖）
  chr-xiaoqing_pose-forehead-l_v01.png（小晴 forehead 左右翻轉：髮夾回到原朝向那側，朝畫面左張望）
用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/build_a3_art.py [classroom] [memory] [card] [poses]
"""
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

FINAL = ROOT / "assets/final"
INK = P.INK
FONT = ROOT / "review/G5/a3/fonts/NotoSansTC-wght.ttf"
META = {}


def out(setname, name, ver="v01"):
    return FINAL / "sets" / setname / f"{name}_{ver}.png"


def tex_mul(a):
    a = a.astype(np.float32)
    a[..., :3] *= P.paper_tex(a.shape[1], a.shape[0])[..., None]
    return np.clip(a, 0, 255).astype(np.uint8)


def font(px, weight=800):
    f = ImageFont.truetype(str(FONT), px)
    f.set_variation_by_axes([weight])
    return f


# ═══════════════════════════════════════════ 教室（a3_c008） ═══════════════════════════════════════════
PPU = 100   # 每世界單位像素

CREAM = (240, 228, 204, 255)
SAGE = (205, 214, 190, 255)
WOOD = (176, 128, 86, 255)
WOOD_L = (206, 160, 112, 255)
FRAME = (236, 226, 206, 255)


def outside():
    """窗外：午後天空（淡藍到暖米）＋對面廣場騎樓屋頂剪紙（無字無招牌）。寬 26、高 9（世界單位）。"""
    w, h = 26 * 40, 9 * 40
    s = P.Sheet(w, h)
    for y in range(h):
        u = y / h
        c = (int(214 + 30 * u), int(228 + 14 * u), int(232 - 6 * u), 255)
        s.rect(0, y, w, y + 1, c, line=0)
    rng = random.Random(3)
    # 遠處雲（紙片）
    for cx, cy, r in [(150, 60, 34), (420, 40, 28), (700, 70, 38), (930, 50, 26)]:
        for k in range(4):
            s.ellipse(cx - r + k * r * 0.55, cy - r * 0.55, cx + r * 0.3 + k * r * 0.55, cy + r * 0.45, (250, 248, 240, 255), line=0)
    # 對面騎樓屋頂（地平線在 h*0.72）
    base = int(h * 0.80)
    x = 0
    while x < w:
        bw = rng.randint(90, 150)
        bh = rng.randint(70, 120)
        col = rng.choice([(226, 186, 150, 255), (232, 204, 168, 255), (214, 170, 140, 255), (236, 214, 184, 255)])
        s.rect(x, base - bh, x + bw, h, col, line=1.6)
        # 窗格（淺色小方塊）
        for wy in range(base - bh + 16, base - 10, 30):
            for wx in range(x + 14, x + bw - 20, 32):
                s.rect(wx, wy, wx + 16, wy + 14, (247, 238, 220, 255), line=1.2)
        x += bw + rng.randint(0, 8)
    # 遠山一線
    pts = [(0, base - 130)]
    for i in range(14):
        pts.append((i * w / 13, base - 130 - 24 * math.sin(i * 1.3) - 10))
    pts += [(w, base - 120), (w, base - 60), (0, base - 60)]
    a = s.finish()
    return a


def backwall():
    """教室後牆：上段奶油色、下段淺鼠尾草綠護牆板＋木條；左邊三扇窗（玻璃挖空）、右邊一扇開著的後門（門外走廊亮一點）。
    寬 24、高 8（世界單位）。窗：x −6.6～−0.6（三扇各 1.8 寬、間隔 0.3）、y 1.35～3.55。門：x 8.4～9.8、y 0～3.3。"""
    W, H = 24, 8
    w, h = W * PPU, H * PPU
    s = P.Sheet(w, h)
    X = lambda wx: (wx + W / 2) * PPU   # noqa: E731
    Y = lambda wy: (H - wy) * PPU      # noqa: E731
    s.rect(0, 0, w, h, CREAM, line=0)
    s.rect(0, Y(1.0), w, h, SAGE, line=0)
    s.rect(0, Y(1.06), w, Y(0.98), WOOD_L, line=1.5)
    s.rect(0, Y(0.08), w, h, WOOD, line=1.5)
    # 天花板邊的木條
    s.rect(0, Y(7.6), w, Y(7.5), WOOD_L, line=1.5)
    wins = []
    for i in range(3):
        x0 = -6.6 + i * 2.1
        wins.append((x0, x0 + 1.8))
        s.rect(X(x0) - 14, Y(3.55) - 14, X(x0 + 1.8) + 14, Y(1.35) + 22, FRAME, line=2)
        s.rect(X(x0) - 20, Y(1.35) + 8, X(x0 + 1.8) + 20, Y(1.35) + 26, WOOD_L, line=2)   # 窗台
    # 後門（開著）：門框＋門外走廊（淺暖光、一盞燈）
    s.rect(X(8.25), Y(3.45), X(9.95), Y(0.0), WOOD_L, line=2)
    s.rect(X(8.4), Y(3.3), X(9.8), Y(0.0), (250, 240, 218, 255), line=2)
    s.rect(X(8.4), Y(0.5), X(9.8), Y(0.0), (226, 214, 190, 255), line=1.5)
    s.rect(X(8.4) + 6, Y(3.3) + 6, X(8.4) + 30, Y(0.0), (198, 150, 104, 255), line=1.5)   # 門板（推開貼牆）
    # 布告欄（牆上的畫，沒有字：一張燈籠、一張貓、一張房子）
    bx0, bx1, by0, by1 = 5.2, 7.7, 2.1, 3.6
    s.rect(X(bx0), Y(by1), X(bx1), Y(by0), (204, 168, 128, 255), line=2)
    s.rect(X(bx0) + 10, Y(by1) + 10, X(bx1) - 10, Y(by0) - 10, (222, 190, 150, 255), line=1.2)
    papers = [(5.35, 2.35, 6.05, 3.35, (250, 244, 230, 255)), (6.15, 2.45, 6.85, 3.4, (246, 236, 214, 255)), (6.95, 2.3, 7.55, 3.3, (250, 246, 236, 255))]
    for k, (x0, y0, x1, y1, c) in enumerate(papers):
        s.rect(X(x0), Y(y1), X(x1), Y(y0), c, line=1.4)
        cx, cy = (X(x0) + X(x1)) / 2, (Y(y0) + Y(y1)) / 2
        if k == 0:   # 燈籠
            s.ellipse(cx - 22, cy - 26, cx + 22, cy + 26, (240, 168, 120, 255), line=1.4)
            s.line([(cx, cy - 26), (cx, cy - 40)], 1.4)
        elif k == 1:  # 貓臉
            s.ellipse(cx - 24, cy - 18, cx + 24, cy + 22, (238, 200, 150, 255), line=1.4)
            s.poly([(cx - 22, cy - 8), (cx - 16, cy - 32), (cx - 4, cy - 16)], (238, 200, 150, 255), 1.4)
            s.poly([(cx + 22, cy - 8), (cx + 16, cy - 32), (cx + 4, cy - 16)], (238, 200, 150, 255), 1.4)
        else:         # 房子
            s.rect(cx - 20, cy - 4, cx + 20, cy + 26, (176, 206, 196, 255), line=1.4)
            s.poly([(cx - 26, cy - 4), (cx, cy - 28), (cx + 26, cy - 4)], (214, 140, 120, 255), 1.4)
        for px, py in [(X(x0) + 6, Y(y1) + 6), (X(x1) - 6, Y(y1) + 6)]:
            s.ellipse(px - 4, py - 4, px + 4, py + 4, (200, 90, 80, 255), line=0)
    # 時鐘（沒有數字：只有刻點）
    cx, cy, r = X(3.0), Y(5.0), 34
    s.ellipse(cx - r, cy - r, cx + r, cy + r, (250, 246, 236, 255), line=2.5)
    for k in range(12):
        a = k * math.pi / 6
        s.ellipse(cx + 26 * math.sin(a) - 2.5, cy - 26 * math.cos(a) - 2.5, cx + 26 * math.sin(a) + 2.5, cy - 26 * math.cos(a) + 2.5, INK, line=0)
    s.line([(cx, cy), (cx + 14, cy + 8)], 2.5)     # 時針（約四點）
    s.line([(cx, cy), (cx, cy - 22)], 2.0)
    # 窗玻璃挖空
    for x0, x1 in wins:
        s.hole(X(x0), Y(3.55), X(x1), Y(1.35))
    a = s.finish()
    # 窗格（十字窗櫺）畫在挖空之後，留在透明洞上
    im = Image.fromarray(a, "RGBA")
    d = ImageDraw.Draw(im)
    for x0, x1 in wins:
        xm = (X(x0) + X(x1)) / 2
        d.rectangle([xm - 6, Y(3.55), xm + 6, Y(1.35)], fill=FRAME, outline=INK, width=2)
        ym = Y(2.45)
        d.rectangle([X(x0), ym - 5, X(x1), ym + 5], fill=FRAME, outline=INK, width=2)
        d.rectangle([X(x0), Y(3.55), X(x1), Y(1.35)], outline=INK, width=3)
    a = tex_mul(np.array(im))
    META["backwall"] = {"width": W, "windows_x": wins, "window_y": [1.35, 3.55], "door_x": [8.4, 9.8]}
    return a


def board():
    """黑板（淺一點的墨綠，孩子不站在它前面）＋木框＋粉筆槽；粉筆畫：一盞燈籠、三顆星星、一條燈籠串（沒有字）。寬 4.2、高 2.0。"""
    W, H = 4.2, 2.0
    w, h = int(W * PPU), int(H * PPU) + 24
    s = P.Sheet(w, h)
    s.rect(0, 0, w, h - 24, WOOD_L, line=2)
    s.rect(12, 12, w - 12, h - 36, (78, 108, 92, 255), line=2)
    s.rect(-4, h - 30, w + 4, h - 16, WOOD, line=2)
    s.rect(60, h - 38, 90, h - 30, (250, 248, 240, 255), line=1)
    chalk = (236, 240, 228, 255)
    # 燈籠（粉筆線）
    cx, cy = w * 0.32, h * 0.47
    s.ellipse(cx - 46, cy - 54, cx + 46, cy + 54, None, line=0)
    s.d.ellipse([(cx - 46) * 2, (cy - 54) * 2, (cx + 46) * 2, (cy + 54) * 2], outline=chalk, width=6)
    for k in (-0.55, 0, 0.55):
        s.d.arc([(cx - 46 * abs(k) - 2) * 2, (cy - 54) * 2, (cx + 46 * abs(k) + 2) * 2, (cy + 54) * 2], 0, 360, fill=chalk, width=3) if k else None
    s.line([(cx - 24, cy - 56), (cx + 24, cy - 56)], 3, chalk)
    s.line([(cx - 24, cy + 56), (cx + 24, cy + 56)], 3, chalk)
    s.line([(cx, cy - 56), (cx, cy - 76)], 3, chalk)
    # 星星
    for sx, sy, r in [(w * 0.62, h * 0.30, 18), (w * 0.74, h * 0.52, 14), (w * 0.86, h * 0.33, 16)]:
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((sx + rr * math.cos(a), sy + rr * math.sin(a)))
        s.line(pts + [pts[0]], 3, chalk)
    # 燈籠串（弧線＋小圓）
    pts = [(w * 0.52 + i * 8, h * 0.70 + 14 * math.sin(i / 22 * math.pi)) for i in range(23)]
    s.line(pts, 2.5, chalk)
    for i in range(1, 23, 5):
        x, y = pts[i]
        s.d.ellipse([(x - 9) * 2, (y + 4) * 2, (x + 9) * 2, (y + 24) * 2], outline=chalk, width=4)
    return s.finish()


def desk():
    """課桌椅一組（側面剪影的正面視角：桌面＋桌板＋兩支腳；椅背在桌後）。桌寬 1.5、桌高 0.95（兒童約 2.45 高）。"""
    W, H = 1.7, 1.25
    w, h = int(W * PPU), int(H * PPU)
    s = P.Sheet(w, h)
    # 椅背（桌後、偏左）
    s.rect(18, 18, 74, 60, (150, 176, 160, 255), line=2)
    s.rect(24, 60, 30, h - 4, (120, 128, 118, 255), line=1.5)
    s.rect(62, 60, 68, h - 4, (120, 128, 118, 255), line=1.5)
    # 桌面＋桌板
    s.rect(6, h - 95, w - 6, h - 83, WOOD_L, line=2)
    s.rect(14, h - 83, w - 14, h - 50, (196, 150, 104, 255), line=2)
    s.rect(30, h - 78, w - 30, h - 58, (222, 196, 160, 255), line=1.2)   # 抽屜口
    s.rect(18, h - 50, 26, h - 2, (112, 120, 112, 255), line=1.5)
    s.rect(w - 26, h - 50, w - 18, h - 2, (112, 120, 112, 255), line=1.5)
    return s.finish()


def teacherdesk():
    """講桌（右前方，林老師旁邊）：木色講桌、桌上一疊作業簿（封面空白）與一個小燈籠。寬 1.6、高 1.4。"""
    W, H = 1.6, 1.55
    w, h = int(W * PPU), int(H * PPU)
    s = P.Sheet(w, h)
    s.rect(4, 30, w - 4, 44, WOOD_L, line=2)
    s.rect(12, 44, w - 12, h - 2, (190, 142, 98, 255), line=2)
    s.rect(28, 60, w - 28, h - 24, (206, 160, 116, 255), line=1.4)
    for k in range(3):
        s.rect(20 + k * 3, 22 - k * 6, 70 + k * 3, 30 - k * 6, [(246, 236, 214, 255), (226, 236, 222, 255), (240, 222, 206, 255)][k], line=1.2)
    s.ellipse(102, 2, 134, 30, (244, 196, 140, 255), line=1.5)
    s.line([(118, 2), (118, -4)], 1.5)
    return s.finish()


def students():
    """遠景同學剪影（教室後排，收書包準備放學）：中性、沒有五官，低對比暖灰；6 個人。寬 7.0、高 2.4。"""
    W, H = 7.0, 2.4
    w, h = int(W * PPU), int(H * PPU)
    s = P.Sheet(w, h)
    rng = random.Random(11)
    cols = [(196, 178, 156, 255), (186, 170, 152, 255), (204, 186, 162, 255)]
    xs = [40, 150, 270, 400, 520, 620]
    for k, x in enumerate(xs):
        hh = rng.uniform(1.95, 2.25) * PPU
        c = cols[k % 3]
        top = h - hh
        hr = hh * 0.11
        cx = x + 30
        # 頭、身體（圓角）、手臂；有的背著書包
        s.ellipse(cx - hr, top, cx + hr, top + hr * 2.1, c, line=1.2)
        s.rect(cx - hr * 1.25, top + hr * 2.0, cx + hr * 1.25, h - hh * 0.36, c, line=1.2, r=10)
        s.rect(cx - hr * 0.95, h - hh * 0.38, cx - hr * 0.15, h - 2, c, line=1.2, r=4)
        s.rect(cx + hr * 0.15, h - hh * 0.38, cx + hr * 0.95, h - 2, c, line=1.2, r=4)
        if k % 2 == 0:
            side = -1 if k % 4 == 0 else 1
            s.rect(cx + side * hr * 1.1 - (hr * 0.9 if side < 0 else 0), top + hr * 2.3, cx + side * hr * 1.1 + (hr * 0.9 if side > 0 else 0), top + hr * 4.6,
                   (172, 156, 140, 255), line=1.2, r=8)
        else:
            s.rect(cx + hr * 1.1, top + hr * 2.4, cx + hr * 1.6, top + hr * 4.4, c, line=1.2, r=5)    # 舉手拿書包
    return s.finish()


def floor():
    """木地板（橫向木條；地板平面的 u＝x、v＝z）。2048×512，鋪在 32×12 上。"""
    w, h = 2048, 512
    s = P.Sheet(w, h, ss=1)
    s.rect(0, 0, w, h, (204, 170, 128, 255), line=0)
    rng = random.Random(5)
    for y in range(0, h, 32):
        s.rect(0, y, w, y + 1, (176, 140, 100, 255), line=0)
        x = rng.randint(0, 200)
        while x < w:
            s.rect(x, y, x + 1, y + 32, (180, 146, 106, 255), line=0)
            x += rng.randint(240, 420)
    return s.finish()


def garland():
    """窗外的燈籠串（沿用 square_a1 garland 的配色；7 盞，寬 6.0）。吊繩兩端在圖的左上、右上。"""
    W, H = 6.0, 0.7
    w, h = int(W * PPU), int(H * PPU)
    s = P.Sheet(w, h)
    cols = [(244, 206, 120, 255), (184, 216, 196, 255), (240, 176, 150, 255), (246, 236, 214, 255), (244, 206, 120, 255), (190, 200, 226, 255), (240, 176, 150, 255)]
    pts = [(4 + i * (w - 8) / 40, 6 + 16 * math.sin(math.pi * i / 40)) for i in range(41)]
    s.line(pts, 1.6)
    for k, c in enumerate(cols):
        i = 3 + k * 5.6
        x, y = pts[int(i)]
        s.line([(x, y), (x, y + 8)], 1.4)
        s.rect(x - 7, y + 8, x + 7, y + 12, (120, 92, 70, 255), line=1)
        s.ellipse(x - 14, y + 11, x + 14, y + 47, c, line=1.6)
        s.rect(x - 7, y + 45, x + 7, y + 50, (120, 92, 70, 255), line=1)
    return s.finish()


def build_classroom():
    d = "a3_classroom"
    for name, fn in [("outside", outside), ("backwall", backwall), ("board", board), ("desk", desk), ("teacherdesk", teacherdesk),
                     ("students", students), ("floor", floor), ("garland", garland)]:
        a = fn()
        P.save(a, out(d, name))
        print("wrote", out(d, name).relative_to(ROOT), a.shape[1], a.shape[0])


# ═══════════════════════════════════════════ 回想小圓窗（a3_c002） ═══════════════════════════════════════════
def build_memory():
    """a2_c002 結尾（被操偶線拉偏的手）：第二幕驗收包的關鍵影格（引擎擷取 1920×1080），只取手臂與兩個紙環、往上延伸的線（不含臉）。
    褪色（降彩 0.55、偏暖）＋手撕圓框（奶油色紙邊）＋淡投影。輸出 640×640。"""
    src = ROOT / "review/G5/a2/pack/capture/keyframes/a2_c002_025.18_after.png"
    im = Image.open(src).convert("RGB")
    box = (20, 0, 395, 375)            # 手（x 130–200）、腕環、肘環、往上的線；頭在 x>400 之外
    crop = im.crop(box).resize((560, 560), Image.LANCZOS)
    rgb = np.array(crop).astype(np.float32)
    g = rgb.mean(axis=2, keepdims=True)
    rgb = rgb * 0.45 + g * 0.55
    rgb = rgb * 0.74 + np.array([246, 228, 198], np.float32) * 0.26
    S = 640
    canvas = np.zeros((S, S, 4), np.float32)
    yy, xx = np.mgrid[:S, :S]
    ang = np.arctan2(yy - S / 2, xx - S / 2)
    rng = np.random.default_rng(7)
    harm = sum(rng.uniform(1.5, 4.0) * np.sin(k * ang + rng.uniform(0, 6.28)) for k in (5, 9, 13, 21, 37))
    rad = np.hypot(xx - S / 2, yy - S / 2)
    r_out = 300 + harm * 0.9
    r_in = 268 + harm * 0.5
    paper = rad <= r_out
    photo = rad <= r_in
    canvas[paper, :3] = np.array([250, 242, 226], np.float32)
    canvas[paper, 3] = 255
    off = (S - 560) // 2
    ph = np.zeros((S, S, 3), np.float32)
    ph[off:off + 560, off:off + 560] = rgb
    canvas[photo, :3] = ph[photo]
    # 內緣一圈淡褐細線
    ring = (rad > r_in - 1.6) & (rad <= r_in + 1.2)
    canvas[ring, :3] = canvas[ring, :3] * 0.4 + np.array([150, 120, 92]) * 0.6
    # 外緣暖深灰細線
    ring2 = (rad > r_out - 2.0) & paper
    canvas[ring2, :3] = canvas[ring2, :3] * 0.35 + np.array([110, 90, 72]) * 0.65
    a = np.clip(canvas, 0, 255).astype(np.uint8)
    a = tex_mul(a)
    P.save(a, out("a3_arcade", "memory"))
    META["memory"] = {"source": str(src.relative_to(ROOT)), "crop_box": box, "note": "不含阿樂叔叔的臉；褪色"}
    print("wrote", out("a3_arcade", "memory").relative_to(ROOT))


# ═══════════════════════════════════════════ 練習卡（a3_c004） ═══════════════════════════════════════════
CARD_W, CARD_H = 2400, 1360     # 世界寬 6.0 → 400 px／單位
CARD_CELLS = [
    ("不碰", "chr-xiaoqing_pose-cross", False),
    ("不試", "chr-xiaoyu_pose-palmno", False),
    ("先離開", "chr-xiaoqing_pose-pointr", False),
    ("找大人", "chr-xiaoyu_pose-forehead", False),
]


def latest(stem):
    c = sorted(FINAL.glob(f"{stem}_v*.png"))
    return c[-1] if c else None


def thumb(stem, box_w, box_h, mirror=False):
    p = latest(stem)
    if p is None:
        return None, None
    im = Image.open(p).convert("RGBA")
    if mirror:
        im = ImageOps.mirror(im)
    a = np.array(im)
    al = a[..., 3] > 128
    rows = np.nonzero(al.any(1))[0]
    cols = np.nonzero(al.any(0))[0]
    im = im.crop((cols.min(), rows.min(), cols.max() + 1, rows.min() + int((rows.max() - rows.min()) * 0.66)))   # 上 2/3（膝蓋以上）
    k = min(box_w / im.width, box_h / im.height)
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS), p.name


def practice_card():
    """台口前緣的練習卡：上排＝拒絕句「不用，我不試。我先離開。」；下排＝口訣四格（動作小圖＋口訣），從左到右依口訣順序。
    字：Noto Sans TC 粗體（程式排版，不是生成圖）；版面座標存在 META["card"]（引擎畫逐格標示用）。"""
    W, H = CARD_W, CARD_H
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 紙卡（圓角、暖白，外框暖深灰）＋中間一道摺痕（攤開的大紙卡）
    d.rounded_rectangle([8, 8, W - 8, H - 8], 46, fill=(252, 247, 236, 255), outline=(92, 72, 58, 255), width=10)
    d.rounded_rectangle([34, 34, W - 34, H - 34], 30, outline=(214, 190, 160, 255), width=4)
    d.line([(W / 2, 40), (W / 2, H - 40)], fill=(232, 220, 200, 255), width=5)
    # 上排：拒絕句
    f1 = font(168, 850)
    txt = "不用，我不試。我先離開。"
    tb = d.textbbox((0, 0), txt, font=f1)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    sx, sy = (W - tw) / 2 - tb[0], 92 - tb[1]
    band = [70, 64, W - 70, 64 + th + 64]
    d.text((sx, sy), txt, font=f1, fill=(64, 46, 36, 255))
    # 下排：四格
    gx0, gx1, gy0, gy1 = 70, W - 70, band[3] + 40, H - 66
    gap = 34
    # 「先離開」手臂往旁伸，格子寬 1.4 倍，四格小圖的人物大小才一致
    wk = [1.0, 1.0, 1.4, 1.0]
    unit = (gx1 - gx0 - gap * 3) / sum(wk)
    cells = []
    f2 = font(132, 850)
    tints = [(250, 226, 214, 255), (226, 238, 228, 255), (250, 238, 206, 255), (222, 232, 244, 255)]
    for i, (label, stem, mir) in enumerate(CARD_CELLS):
        x0 = gx0 + sum(wk[:i]) * unit + i * gap
        cw = wk[i] * unit
        x1 = x0 + cw
        d.rounded_rectangle([x0, gy0, x1, gy1], 28, fill=tints[i], outline=(150, 120, 96, 255), width=5)
        lb = d.textbbox((0, 0), label, font=f2)
        lw, lh = lb[2] - lb[0], lb[3] - lb[1]
        ly = gy1 - 40 - lh
        th_img, used = thumb(stem, cw - 60, ly - gy0 - 50, mir)
        if th_img is not None:
            img.alpha_composite(th_img, (int(x0 + (cw - th_img.width) / 2), int(ly - 30 - th_img.height)))
        d.text((x0 + (cw - lw) / 2 - lb[0], ly - lb[1]), label, font=f2, fill=(64, 46, 36, 255))
        cells.append({"label": label, "box_px": [round(x0), round(gy0), round(x1), round(gy1)], "thumb": used})
    a = tex_mul(np.array(img))
    P.save(a, out("a3_gate", "card"))
    META["card"] = {"size_px": [W, H], "world_width": 6.0, "sentence_box_px": [round(v) for v in band], "cells": cells, "font": "Noto Sans TC（OFL，review/G5/a3/fonts）weight 850"}
    print("wrote", out("a3_gate", "card").relative_to(ROOT), cells)


# ═══════════════════════════════════════════ 姿勢圖（翻轉） ═══════════════════════════════════════════
def build_poses():
    src = FINAL / "chr-xiaoqing_pose-forehead_v06.png"
    dst = FINAL / "chr-xiaoqing_pose-forehead-l_v01.png"
    ImageOps.mirror(Image.open(src).convert("RGBA")).save(dst, optimize=True)
    META["forehead_l"] = {"source": src.name, "op": "左右翻轉", "size": Image.open(dst).size}
    print("wrote", dst.relative_to(ROOT))


def main():
    what = set(sys.argv[1:]) or {"classroom", "memory", "card", "poses"}
    if "classroom" in what:
        build_classroom()
    if "memory" in what:
        build_memory()
    if "poses" in what:
        build_poses()
    if "card" in what:
        practice_card()
    mp = HERE / "build_a3_art_meta.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    old.update(META)
    mp.write_text(json.dumps(old, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
