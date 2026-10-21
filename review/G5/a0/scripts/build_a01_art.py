"""G5 開場＋第一幕：程式繪製的景片、道具與兩張補姿勢圖（Codex 圖像額度用完時的退路；同 G5 共用美術的 paperdraw 做法）。

輸出：
  assets/final/sets/workshop_a0/  design（主燈設計圖）、stand（工作台上空著的主燈底座）、chime（風鈴）、lamps（台口上方八盞未亮的燈）、
                                  memoryframe（回憶小窗的紙框，1920×1080）、notebook（小晴的筆記本，筆畫由程式逐筆畫）
  assets/final/sets/square_a1/    pillar（紅磚柱子）、garland（騎樓下的小燈籠串）、townsfolk（遠景布置的鎮民剪影）、
                                  wrapper（撕破的包裝紙＋一團灰色紙線）、shopfront（燈籠店門面，窗挖空）、windowpaper（窗紙）、
                                  silbody／silarm／silbamboo（窗內阿樂叔叔的剪影：身體、手臂、竹篾）、boxclose（盒子特寫，去掉透明邊的雜色）
  assets/final/chr-xiaoyu_pose-standwatch_v01.png   小宇站姿＋左腕兒童手錶（a0_c004 起的伏筆；錶面只有圓點，沒有字）
  assets/final/chr-pinan_pose-sit-lantern-back_v01.png  品安坐長椅綁燈籠的左右鏡像（a1_c004「偷偷回頭看柱子」翻面用）
  assets/final/chr-xiaoqing_pose-walkl_v01.png  小晴走路姿勢的左右鏡像（往畫面左走；小宇往右走用 a2 代理做的 walk_r）
規則：圖裡沒有任何文字、數字、標誌；不畫陰影與方向光；求助、危險方位依劇本。
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

INK = P.INK
OUT0 = ROOT / "assets/final/sets/workshop_a0"
OUT1 = ROOT / "assets/final/sets/square_a1"
rng = np.random.default_rng(20261021)
meta = {}


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


# ───────────────────────────── 燈籠店（workshop_a0） ─────────────────────────────
def design():
    """主燈設計圖：一張微黃的圖紙，鉛筆線畫一隻大大的摺紙貓燈（和折折同色系），旁邊是竹骨架草圖。沒有任何文字、數字。"""
    PP = 300
    W, H = int(1.5 * PP), int(1.85 * PP)
    s = P.Sheet(W, H)
    s.rect(6, 6, W - 6, H - 6, (247, 239, 222, 255), line=2.0)
    pencil = (112, 92, 76, 255)
    wash = (246, 199, 156, 255)
    cx, cy = W * 0.46, H * 0.5
    # 貓燈：圓燈身（摺面）＋三角耳＋臉
    body = [(cx + 120 * math.cos(a), cy + 40 + 128 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]]
    s.poly(body, wash, line=0)
    for i in range(len(body)):
        s.line([body[i], body[(i + 1) % len(body)]], 2.4, pencil)
    # 摺面線（從中心放射＋兩圈）
    for i in range(0, len(body), 2):
        s.line([(cx, cy + 40), body[i]], 1.2, (150, 122, 98, 255))
    for k in (0.55, 0.8):
        ring = [(cx + 120 * k * math.cos(a), cy + 40 + 128 * k * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)]
        s.line(ring, 1.0, (160, 132, 108, 255))
    # 耳朵
    for sgn in (-1, 1):
        ear = [(cx + sgn * 40, cy - 70), (cx + sgn * 112, cy - 56), (cx + sgn * 96, cy - 150)]
        s.poly(ear, wash, line=2.4)
        s.line([(cx + sgn * 58, cy - 70), (cx + sgn * 94, cy - 128)], 1.2, (150, 122, 98, 255))
    # 臉：兩眼、鼻、嘴、鬍鬚
    for sgn in (-1, 1):
        s.ellipse(cx + sgn * 44 - 8, cy + 6 - 10, cx + sgn * 44 + 8, cy + 6 + 10, (90, 70, 58, 255), line=0)
        for k in (-1, 1):
            s.line([(cx + sgn * 70, cy + 44 + k * 8), (cx + sgn * 132, cy + 36 + k * 18)], 1.4, pencil)
    s.poly([(cx - 9, cy + 30), (cx + 9, cy + 30), (cx, cy + 40)], (196, 120, 100, 255), line=0)
    s.line([(cx - 18, cy + 50), (cx - 8, cy + 56), (cx, cy + 48), (cx + 8, cy + 56), (cx + 18, cy + 50)], 1.8, pencil)
    # 底座與提把（燈籠上下木蓋）
    s.rect(cx - 46, cy + 168, cx + 46, cy + 184, (196, 160, 112, 255), line=1.8)
    s.line([(cx, cy - 150), (cx, cy - 190)], 1.6, pencil)
    s.ellipse(cx - 10, cy - 206, cx + 10, cy - 186, None, line=1.6)
    # 量尺寸的虛線箭頭（沒有數字）
    for y in range(int(cy - 140), int(cy + 180), 14):
        s.line([(W * 0.86, y), (W * 0.86, y + 7)], 1.2, (150, 130, 110, 255))
    for yy, d in ((cy - 140, 1), (cy + 180, -1)):
        s.line([(W * 0.86 - 7, yy + d * 9), (W * 0.86, yy), (W * 0.86 + 7, yy + d * 9)], 1.4, (150, 130, 110, 255))
    # 右下角：竹骨架小草圖（只有線）
    bx, by = W * 0.2, H * 0.86
    for k in range(-2, 3):
        s.d.ellipse([(bx - abs(k) * 9 - 3) * s.ss, (by - 34) * s.ss, (bx + abs(k) * 9 + 3) * s.ss, (by + 34) * s.ss], outline=(170, 130, 80, 255), width=3)
    s.d.ellipse([(bx - 24) * s.ss, (by - 9) * s.ss, (bx + 24) * s.ss, (by + 9) * s.ss], outline=(170, 130, 80, 255), width=3)
    # 圖釘（黃銅色）
    for x, y in ((22, 22), (W - 22, 22), (22, H - 22), (W - 22, H - 22)):
        s.ellipse(x - 9, y - 9, x + 9, y + 9, (200, 164, 96, 255), line=1.4)
    return s.finish(edge_dark=0.12), {"px_per_unit": PP, "size_units": [1.5, 1.85]}


def stand():
    """空著的主燈底座：圓木座＋四個空插孔（骨架原本插在這裡）。"""
    PP = 300
    W, H = int(1.05 * PP), int(0.36 * PP)
    s = P.Sheet(W, H)
    top = (214, 172, 120, 255)
    side = (178, 132, 86, 255)
    s.rect(14, H * 0.42, W - 14, H - 6, side, line=2.0, r=10)
    s.ellipse(10, 4, W - 10, H * 0.62, top, line=2.0)
    # 四個空插孔（深色小橢圓）＋插孔邊的竹屑
    for k in range(4):
        x = W * (0.22 + 0.19 * k)
        s.ellipse(x - 13, H * 0.26, x + 13, H * 0.39, (92, 64, 44, 255), line=1.2)
    s.line([(W * 0.12, H * 0.33), (W * 0.18, H * 0.3)], 1.6, (196, 160, 96, 255))
    s.line([(W * 0.84, H * 0.28), (W * 0.9, H * 0.33)], 1.6, (196, 160, 96, 255))
    for x0 in range(40, W - 40, 60):
        s.line([(x0, H * 0.7), (x0 + 22, H * 0.7)], 1.2, (140, 100, 64, 255))
    return s.finish(white_border=6), {"px_per_unit": PP}


def chime():
    """風鈴：淺色玻璃鈴＋繩＋舌＋淺橙紙籤（沒有字）。懸掛點在圖上緣中央。"""
    PP = 420
    W, H = int(0.46 * PP), int(1.12 * PP)
    s = P.Sheet(W, H)
    c = W / 2
    s.line([(c, 0), (c, 40)], 2.0, (110, 90, 74, 255))
    s.poly([(c - 52, 120), (c - 46, 66), (c - 24, 42), (c + 24, 42), (c + 46, 66), (c + 52, 120)], (226, 238, 240, 255), line=2.0)
    s.line([(c - 40, 92), (c - 14, 80), (c + 10, 92), (c + 38, 80)], 2.2, (232, 150, 108, 255))
    s.ellipse(c - 8, 36, c + 8, 48, (150, 120, 96, 255), line=1.2)
    s.line([(c, 118), (c, 250)], 1.8, (110, 90, 74, 255))
    s.ellipse(c - 7, 126, c + 7, 140, (196, 160, 104, 255), line=1.2)
    s.poly([(c - 28, 250), (c + 28, 250), (c + 26, H - 10), (c - 26, H - 10)], (246, 205, 164, 255), line=1.8)
    s.line([(c - 16, 270), (c + 16, 270)], 1.0, (226, 180, 140, 255))
    return s.finish(), {"px_per_unit": PP, "hang_px": [W / 2, 0]}


def lamps():
    """台口上方一串八盞還沒亮的紙燈（和題卡上的燈同造型：圓燈身、竹骨線、上下木蓋），掛在下垂的細繩上。"""
    PP = 160
    W, H = int(12.4 * PP), int(1.55 * PP)
    s = P.Sheet(W, H)
    sag = 0.42 * PP
    xs = np.linspace(0, W, 200)
    ys = 10 + sag * (1 - ((xs - W / 2) / (W / 2)) ** 2)
    s.line(list(zip(xs, ys)), 3.0, (108, 88, 70, 255))
    meta_l = []
    for i in range(8):
        x = W * (0.5 + (i - 3.5) * 0.112)
        y0 = 10 + sag * (1 - ((x - W / 2) / (W / 2)) ** 2)
        r = 0.25 * PP
        cy = y0 + 0.18 * PP + r * 1.12
        s.line([(x, y0), (x, cy - r * 1.12 - 6)], 2.2, (108, 88, 70, 255))
        s.ellipse(x - r, cy - r * 1.12, x + r, cy + r * 1.12, (238, 228, 208, 255), line=2.2)
        for k in (-2, -1, 1, 2):
            rx = r * abs(k) / 2.6
            s.d.arc([(x - rx) * s.ss, (cy - r * 1.12) * s.ss, (x + rx) * s.ss, (cy + r * 1.12) * s.ss], 90 if k < 0 else 270, 270 if k < 0 else 90,
                    fill=(186, 158, 120, 255), width=3)
        s.line([(x, cy - r * 1.12), (x, cy + r * 1.12)], 1.4, (186, 158, 120, 255))
        s.rect(x - r * 0.42, cy - r * 1.22, x + r * 0.42, cy - r * 1.02, (124, 88, 58, 255), line=1.2)
        s.rect(x - r * 0.42, cy + r * 1.02, x + r * 0.42, cy + r * 1.22, (124, 88, 58, 255), line=1.2)
        meta_l.append([round(x / PP, 3), round(cy / PP, 3)])
    return s.finish(), {"px_per_unit": PP, "lamp_centers_units_from_topleft": meta_l}


def memoryframe():
    """回憶小窗：暖杏色厚紙框（1920×1080），中間挖一個手撕邊的圓角窗；窗緣一圈淺色紙芯，往內一點淡淡的暖色暈。"""
    W, H = 1920, 1080
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy, rx, ry = W * 0.5, H * 0.43, W * 0.39, H * 0.4
    # 超橢圓（圓角窗）＋手撕邊的低頻起伏
    ang = np.arctan2((yy - cy) / ry, (xx - cx) / rx)
    wob = np.zeros_like(ang)
    for k, a in ((5, 0.012), (9, 0.008), (17, 0.005), (31, 0.003), (57, 0.002)):
        wob += a * np.sin(k * ang + rng.uniform(0, 6.28))
    n = 3.2
    d = (np.abs((xx - cx) / rx) ** n + np.abs((yy - cy) / ry) ** n) ** (1 / n) - 1 - wob
    px = d * min(rx, ry)  # 約略的像素距離（窗外為正）
    frame = np.zeros((H, W, 4), np.float32)
    base = np.array([226, 196, 152], np.float32)
    tex = P.paper_tex(W, H)
    frame[..., :3] = base * tex[..., None]
    # 框外緣淡淡變深（像紙張邊緣）
    edge = np.clip(1 - np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy]) / 90, 0, 1)
    frame[..., :3] *= (1 - 0.18 * edge[..., None])
    # 窗緣的紙芯白邊（2–7 px）與內側暖暈
    core = np.clip(1 - np.abs(px - 4.5) / 3.5, 0, 1)
    frame[..., :3] = frame[..., :3] * (1 - core[..., None]) + np.array([252, 244, 228], np.float32) * core[..., None]
    alpha = np.clip(px / 1.5 + 0.5, 0, 1)
    glow = np.clip(1 + px / 70, 0, 1) * (px < 0)
    out = frame.copy()
    out[..., 3] = 255 * np.maximum(alpha, 0.0)
    # 窗內的暖暈：半透明暖色（回憶的暖光），越靠窗緣越濃
    inner = (px < 0)
    out[inner, :3] = np.array([255, 214, 160], np.float32)
    out[inner, 3] = 255 * 0.32 * glow[inner] ** 2
    return np.clip(out, 0, 255).astype(np.uint8), {"window": {"cx": cx / W, "cy": cy / H, "rx": rx / W, "ry": ry / H, "n": n}}


def notebook():
    """小晴的小筆記本（攤開、格線、沒有字）。竹骨架與問號由程式逐筆畫上（app/src/sets/workshop_a0.ts）。"""
    W, H = 900, 600
    s = P.Sheet(W, H)
    s.rect(14, 18, W - 14, H - 12, (120, 160, 150, 255), line=2.2, r=18)          # 封面（綠，和小晴吊帶褲同色系）
    s.rect(34, 34, W / 2 - 4, H - 30, (250, 246, 236, 255), line=1.8, r=6)
    s.rect(W / 2 + 4, 34, W - 34, H - 30, (250, 246, 236, 255), line=1.8, r=6)
    for y in range(90, H - 40, 46):
        s.line([(56, y), (W / 2 - 24, y)], 1.2, (186, 200, 210, 255))
        s.line([(W / 2 + 24, y), (W - 56, y)], 1.2, (186, 200, 210, 255))
    for y in range(60, H - 40, 52):
        s.ellipse(W / 2 - 9, y - 9, W / 2 + 9, y + 9, (150, 150, 156, 255), line=1.2)
    return s.finish(edge_dark=0.1), {"page_right_px": [W / 2 + 4, 34, W - 34, H - 30], "size": [W, H]}


# ───────────────────────────── 廣場（square_a1） ─────────────────────────────
def pillar():
    """紅磚柱子（畫面左側；邀請者的手從後面伸出來）：米色柱頭柱腳＋紅磚柱身。"""
    PP = 150
    W, H = int(1.15 * PP), int(5.8 * PP)
    s = P.Sheet(W, H)
    brick, brick2, mortar = (176, 96, 70, 255), (164, 86, 62, 255), (226, 204, 178, 255)
    s.rect(12, 70, W - 12, H - 70, mortar, line=2.0)
    bh = 26
    for r, y in enumerate(range(72, H - 72, bh)):
        off = 0 if r % 2 == 0 else 34
        for x in range(12 - off, W - 12, 68):
            x0, x1 = max(14, x + 2), min(W - 14, x + 66)
            if x1 - x0 > 6:
                s.rect(x0, y + 2, x1, min(y + bh - 2, H - 72), brick if (r + x // 68) % 2 else brick2, line=0)
    s.rect(4, 20, W - 4, 74, (236, 218, 188, 255), line=2.0)
    s.rect(0, 0, W, 26, (226, 206, 172, 255), line=2.0)
    s.rect(4, H - 74, W - 4, H - 22, (236, 218, 188, 255), line=2.0)
    s.rect(0, H - 26, W, H, (226, 206, 172, 255), line=2.0)
    return s.finish(edge_dark=0.1), {"px_per_unit": PP}


def garland():
    """騎樓下的小燈籠串（白天、未點亮，粉彩色）。"""
    PP = 150
    W, H = int(10.0 * PP), int(1.0 * PP)
    s = P.Sheet(W, H)
    sag = 0.22 * PP
    xs = np.linspace(0, W, 200)
    ys = 6 + sag * (1 - ((xs - W / 2) / (W / 2)) ** 2)
    s.line(list(zip(xs, ys)), 2.0, (110, 90, 72, 255))
    cols = [(246, 200, 160), (244, 232, 206), (246, 222, 140), (190, 220, 196), (242, 180, 150)]
    for i in range(14):
        x = W * (0.04 + i * 0.0708)
        y0 = 6 + sag * (1 - ((x - W / 2) / (W / 2)) ** 2)
        r = 0.13 * PP
        cy = y0 + 0.08 * PP + r * 1.1
        s.line([(x, y0), (x, cy - r)], 1.6, (110, 90, 72, 255))
        s.ellipse(x - r, cy - r * 1.1, x + r, cy + r * 1.1, rgba(cols[i % 5]), line=1.6)
        s.line([(x, cy - r * 1.1), (x, cy + r * 1.1)], 1.0, (170, 140, 110, 255))
        s.rect(x - r * 0.4, cy - r * 1.22, x + r * 0.4, cy - r * 1.02, (130, 96, 64, 255), line=0)
        s.rect(x - r * 0.4, cy + r * 1.02, x + r * 0.4, cy + r * 1.22, (130, 96, 64, 255), line=0)
    return s.finish(), {"px_per_unit": PP}


def townsfolk():
    """遠景布置燈節的鎮民剪影（中性：沒有五官、沒有年齡或族群標記；暖灰褐平塗，不是黑影）。"""
    PP = 150
    W, H = int(5.2 * PP), int(2.6 * PP)
    s = P.Sheet(W, H)
    col = (204, 184, 162, 255)     # 遠景：淡暖灰（像隔著一層空氣），不是黑影
    col2 = (196, 176, 155, 255)
    gy = H - 4
    # 人 1：站在小梯子上掛燈籠
    lx = W * 0.22
    s.poly([(lx - 50, gy), (lx - 22, gy - 150), (lx - 12, gy - 150), (lx - 34, gy)], col2, line=0)
    s.poly([(lx + 30, gy), (lx + 8, gy - 150), (lx + 18, gy - 150), (lx + 46, gy)], col2, line=0)
    for k in range(4):
        y = gy - 30 - k * 34
        s.line([(lx - 40 + k * 6, y), (lx + 36 - k * 6, y)], 4, (186, 164, 142, 255))
    s.rect(lx - 26, gy - 290, lx + 26, gy - 152, col, line=0, r=14)
    s.ellipse(lx - 22, gy - 336, lx + 22, gy - 292, col, line=0)
    s.line([(lx + 20, gy - 270), (lx + 52, gy - 330)], 12, col)  # 舉起燈籠的手臂
    s.line([(lx + 52, gy - 330), (lx + 52, gy - 352)], 2, (120, 100, 84, 255))
    s.ellipse(lx + 36, gy - 352, lx + 70, gy - 312, (232, 196, 150, 255), line=0)
    # 人 2：舉著掛燈籠的竹竿
    x2 = W * 0.6
    s.rect(x2 - 28, gy - 230, x2 + 28, gy - 70, col, line=0, r=14)
    s.rect(x2 - 24, gy - 74, x2 - 4, gy, col, line=0)
    s.rect(x2 + 4, gy - 74, x2 + 24, gy, col, line=0)
    s.ellipse(x2 - 23, gy - 278, x2 + 23, gy - 232, col, line=0)
    s.line([(x2 + 22, gy - 200), (x2 + 120, gy - 360)], 5, (186, 164, 142, 255))
    s.line([(x2 + 120, gy - 360), (x2 + 120, gy - 330)], 2, (120, 100, 84, 255))
    s.ellipse(x2 + 102, gy - 332, x2 + 138, gy - 290, (238, 214, 168, 255), line=0)
    # 人 3：抱著一箱燈籠
    x3 = W * 0.86
    s.rect(x3 - 26, gy - 210, x3 + 26, gy - 66, col2, line=0, r=14)
    s.rect(x3 - 22, gy - 70, x3 - 4, gy, col2, line=0)
    s.rect(x3 + 4, gy - 70, x3 + 22, gy, col2, line=0)
    s.ellipse(x3 - 22, gy - 254, x3 + 22, gy - 212, col2, line=0)
    s.rect(x3 - 40, gy - 160, x3 + 40, gy - 110, (196, 162, 120, 255), line=0)
    return s.finish(), {"px_per_unit": PP}


STICKER = [(244, 70, 140), (250, 216, 60), (40, 190, 200), (150, 210, 60), (250, 140, 60)]


def sticker_pattern(W, H, seed):
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (W, H), rgba(STICKER[1]))
    d = ImageDraw.Draw(im)
    for _ in range(int(W * H / 26000)):
        c = rgba(STICKER[r.integers(0, 5)])
        x, y, sz = r.uniform(0, W), r.uniform(0, H), r.uniform(90, 230)
        kind = r.integers(0, 4)
        if kind == 0:
            pts = [(x + sz * (1 if i % 2 == 0 else 0.45) * math.cos(math.pi / 2 + i * math.pi / 5), y - sz * (1 if i % 2 == 0 else 0.45) * math.sin(math.pi / 2 + i * math.pi / 5)) for i in range(10)]
            d.polygon(pts, fill=c)
        elif kind == 1:
            d.ellipse([x - sz / 2, y - sz / 2, x + sz / 2, y + sz / 2], fill=c)
        elif kind == 2:
            d.polygon([(x, y - sz / 2), (x + sz / 2, y), (x, y + sz / 2), (x - sz / 2, y)], fill=c)
        else:
            for k in range(3):
                rr = sz * (1 - k * 0.3) / 2
                d.arc([x - rr, y - rr, x + rr, y + rr], 0, 300, fill=rgba(STICKER[(r.integers(0, 5))]), width=18)
    return im


def wrapper():
    """撕破的包裝紙（貼紙花紋，和盒子同色系）：撕口露出白色紙背，一團灰色紙線（同操偶線的紙繩：淺灰繩身＋深灰邊）從撕口糾結出來。
    單位：0.8×0.55 世界單位，1000 px／單位（推近特寫用）。"""
    PP = 1000
    W, H = int(0.8 * PP), int(0.55 * PP)
    ss = 2
    WW, HH = W * ss, H * ss
    pat = sticker_pattern(WW, HH, 7)
    # 手撕的外形：略呈四邊形的紙片，邊緣鋸齒
    corners = [(0.06, 0.30), (0.62, 0.14), (0.95, 0.36), (0.88, 0.86), (0.30, 0.95), (0.03, 0.70)]
    pts = []
    for k in range(len(corners)):
        (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % len(corners)]
        n = 14
        for i in range(n):
            u = i / n
            jx, jy = rng.uniform(-0.012, 0.012), rng.uniform(-0.016, 0.016)
            pts.append(((x0 + (x1 - x0) * u + jx) * WW, (y0 + (y1 - y0) * u + jy) * HH))
    mask = Image.new("L", (WW, HH), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    out = Image.new("RGBA", (WW, HH), (0, 0, 0, 0))
    out.paste(pat, (0, 0), mask)
    d = ImageDraw.Draw(out)
    d.line(pts + [pts[0]], fill=INK, width=5)
    # 撕口：不規則的破洞，裡面是白色紙背
    hx, hy, hrx, hry = 0.56 * WW, 0.5 * HH, 0.2 * WW, 0.2 * HH
    hole = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        rr = 1 + 0.18 * math.sin(3 * a + 0.7) + 0.08 * rng.uniform(-1, 1)
        hole.append((hx + hrx * rr * math.cos(a), hy + hry * rr * math.sin(a)))
    d.polygon(hole, fill=(238, 232, 220, 255))
    d.line(hole + [hole[0]], fill=(120, 96, 80, 255), width=5)
    # 撕口邊翻起的一小片白紙
    flap = [hole[31], hole[35], (hx + hrx * 1.05, hy - hry * 1.25)]
    d.polygon(flap, fill=(246, 241, 230, 255))
    d.line(flap + [flap[0]], fill=INK, width=5)
    # 一團灰色紙線：平滑的線圈（深灰邊＋淺灰繩身），從破洞糾結出來
    loops = []
    for k in range(10):
        cx0 = hx + rng.uniform(-0.6, 0.6) * hrx
        cy0 = hy + rng.uniform(-0.55, 0.45) * hry
        rx0, ry0 = rng.uniform(0.25, 0.6) * hrx, rng.uniform(0.2, 0.5) * hry
        rot = rng.uniform(0, math.pi)
        seg = []
        for j in range(72):
            a = 2 * math.pi * j / 64
            x = rx0 * math.cos(a) * (1 + 0.15 * math.sin(2 * a + k))
            y = ry0 * math.sin(a)
            seg.append((cx0 + x * math.cos(rot) - y * math.sin(rot), cy0 + x * math.sin(rot) + y * math.cos(rot)))
        loops.append(seg)
    tails = [[(hx + 0.3 * hrx, hy - 0.5 * hry), (hx + 0.9 * hrx, hy - 1.2 * hry), (hx + 1.6 * hrx, hy - 1.45 * hry), (hx + 2.0 * hrx, hy - 1.3 * hry)],
             [(hx - 0.5 * hrx, hy + 0.4 * hry), (hx - 1.1 * hrx, hy + 0.9 * hry), (hx - 1.7 * hrx, hy + 1.05 * hry)]]
    for seg in loops + tails:
        d.line(seg, fill=(86, 84, 82, 255), width=17, joint="curve")
    for seg in loops + tails:
        d.line(seg, fill=(176, 174, 170, 255), width=9, joint="curve")
    im = out.resize((W, H), Image.LANCZOS)
    a = np.array(im).astype(np.float32)
    a[..., :3] *= P.paper_tex(W, H)[..., None]
    return np.clip(a, 0, 255).astype(np.uint8), {"px_per_unit": PP, "hole_center_px": [hx / ss, hy / ss]}


def shopfront():
    """燈籠店門面（街角）：米色牆、木框、只有燈籠圖示的招牌、格子窗（窗格中間挖空，後面另放窗紙與剪影）、門口布簾。"""
    PP = 150
    W, H = int(4.4 * PP), int(5.2 * PP)
    s = P.Sheet(W, H)
    wall, wood = (238, 222, 196, 255), (150, 108, 72, 255)
    s.rect(10, 60, W - 10, H - 4, wall, line=2.0)
    s.rect(0, 30, W, 74, (178, 96, 72, 255), line=2.0)                # 屋簷（紅磚色）
    # 招牌：只有燈籠圖示
    s.rect(W * 0.28, 96, W * 0.72, 186, (120, 84, 56, 255), line=2.0, r=10)
    lx, ly = W * 0.5, 141
    s.ellipse(lx - 26, ly - 30, lx + 26, ly + 30, (246, 200, 150, 255), line=1.6)
    s.rect(lx - 12, ly - 36, lx + 12, ly - 28, (90, 64, 44, 255), line=0)
    s.rect(lx - 12, ly + 28, lx + 12, ly + 36, (90, 64, 44, 255), line=0)
    # 窗：木框＋格子，窗格挖空
    wx0, wy0, wx1, wy1 = int(W * 0.08), int(H * 0.36), int(W * 0.58), int(H * 0.74)
    s.rect(wx0 - 14, wy0 - 14, wx1 + 14, wy1 + 14, wood, line=2.0)
    s.rect(wx0 - 22, wy1 + 10, wx1 + 22, wy1 + 30, (170, 126, 86, 255), line=2.0)   # 窗台
    cols, rows = 3, 3
    holes = []
    gw, gh = (wx1 - wx0), (wy1 - wy0)
    for i in range(cols):
        for j in range(rows):
            x0 = wx0 + i * gw / cols + 4
            y0 = wy0 + j * gh / rows + 4
            holes.append((x0, y0, x0 + gw / cols - 8, y0 + gh / rows - 8))
    # 門：布簾（淺杏色，沒有字）
    dx0, dx1 = int(W * 0.66), int(W * 0.92)
    s.rect(dx0, int(H * 0.34), dx1, H - 4, (120, 92, 70, 255), line=2.0)
    s.rect(dx0 + 6, int(H * 0.34) + 6, dx1 - 6, int(H * 0.56), (240, 196, 150, 255), line=1.6)
    s.line([((dx0 + dx1) / 2, int(H * 0.34) + 6), ((dx0 + dx1) / 2, int(H * 0.56))], 1.6, INK)
    # 牆角掛一串小燈籠
    for k in range(3):
        x = W * 0.12 + k * 46
        s.ellipse(x - 14, 220, x + 14, 252, (246, 214, 160, 255), line=1.4)
    for h in holes:
        s.hole(*h)
    a = s.finish(edge_dark=0.08)
    win = [wx0 / PP, wy0 / PP, wx1 / PP, wy1 / PP]
    return a, {"px_per_unit": PP, "window_units_from_topleft": [round(v, 3) for v in win], "size_units": [W / PP, H / PP]}


def shopwindow():
    """騎樓下燈籠店的窗（掛在廣場騎樓最右邊那一間）：木窗框＋格子（窗格挖空，後面另放窗紙與剪影）、窗台、只有燈籠圖示的小招牌。"""
    PP = 150
    W, H = int(2.5 * PP), int(2.55 * PP)
    s = P.Sheet(W, H)
    wood, wood2 = (150, 108, 72, 255), (170, 126, 86, 255)
    # 小招牌（燈籠圖示，沒有字）
    s.rect(W * 0.3, 4, W * 0.7, 62, (120, 84, 56, 255), line=2.0, r=8)
    lx, ly = W * 0.5, 33
    s.ellipse(lx - 17, ly - 20, lx + 17, ly + 20, (246, 200, 150, 255), line=1.4)
    s.rect(lx - 8, ly - 24, lx + 8, ly - 18, (90, 64, 44, 255), line=0)
    s.rect(lx - 8, ly + 18, lx + 8, ly + 24, (90, 64, 44, 255), line=0)
    # 窗框
    wx0, wy0, wx1, wy1 = 22, 84, W - 22, H - 46
    s.rect(wx0 - 14, wy0 - 14, wx1 + 14, wy1 + 14, wood, line=2.0)
    s.rect(wx0 - 22, wy1 + 10, wx1 + 22, wy1 + 32, wood2, line=2.0)     # 窗台
    holes = []
    cols, rows = 3, 3
    gw, gh = (wx1 - wx0), (wy1 - wy0)
    for i in range(cols):
        for j in range(rows):
            x0 = wx0 + i * gw / cols + 4
            y0 = wy0 + j * gh / rows + 4
            holes.append((x0, y0, x0 + gw / cols - 8, y0 + gh / rows - 8))
    for h in holes:
        s.hole(*h)
    a = s.finish(edge_dark=0.08)
    return a, {"px_per_unit": PP, "window_units_from_topleft": [round(v / PP, 3) for v in (wx0, wy0, wx1, wy1)], "size_units": [W / PP, H / PP]}


def windowpaper():
    """窗紙（暖色，屋裡點著燈）：放在剪影後面，自發光由程式設定。"""
    PP = 150
    W, H = int(2.4 * PP), int(2.2 * PP)
    a = np.zeros((H, W, 4), np.float32)
    a[..., :3] = np.array([252, 226, 178], np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.exp(-(((xx - W * 0.45) / (W * 0.6)) ** 2 + ((yy - H * 0.4) / (H * 0.7)) ** 2))
    a[..., :3] *= (0.86 + 0.14 * g)[..., None]
    a[..., :3] *= P.paper_tex(W, H)[..., None]
    a[..., 3] = 255
    return np.clip(a, 0, 255).astype(np.uint8), {"px_per_unit": PP}


def silhouettes():
    """窗內阿樂叔叔的剪影（FX10）：以阿樂叔叔母版的外形取上半身，填暖深褐並柔化；右臂另外一片（可轉動）；竹篾一根。沒有操偶線。"""
    src = Image.open(ROOT / "assets/generated/chr-ale_master_v02.png").convert("RGBA")
    al = np.array(src)[..., 3] > 128
    H0, W0 = al.shape
    ys, xs = np.nonzero(al)
    top = ys.min()
    cut = int(top + 0.52 * (ys.max() - top))           # 腰（窗台以上）
    body = al[:cut].copy()
    # 去掉畫面左側（阿樂叔叔的右臂）：肩膀以下、身體中線左側 33% 以外
    xc = (xs.min() + xs.max()) / 2
    shoulder = int(top + 0.2 * (ys.max() - top))
    body[shoulder:, : int(xc - 0.21 * (xs.max() - xs.min()))] = False
    m = ndimage.binary_closing(body, iterations=3)
    col = np.array([88, 66, 54], np.float32)
    def soft(mask, blur=2.2):
        a = ndimage.gaussian_filter(mask.astype(np.float32), blur)
        out = np.zeros(mask.shape + (4,), np.float32)
        out[..., :3] = col
        out[..., 3] = np.clip(a * 1.15, 0, 1) * 255
        return out.astype(np.uint8)
    yb, xb = np.nonzero(m)
    crop = m[yb.min():yb.max() + 1, xb.min():xb.max() + 1]
    body_img = soft(np.pad(crop, 12))
    # 右臂：上臂＋前臂＋拳頭（肩膀為轉軸，舉起約 45°）
    S = 3
    arm = Image.new("L", (300 * S, 300 * S), 0)
    d = ImageDraw.Draw(arm)
    sx, sy = 240 * S, 250 * S
    ex, ey = 150 * S, 160 * S
    hx, hy = 110 * S, 60 * S
    d.line([(sx, sy), (ex, ey)], fill=255, width=46 * S)
    d.line([(ex, ey), (hx, hy)], fill=255, width=38 * S)
    d.ellipse([hx - 26 * S, hy - 26 * S, hx + 26 * S, hy + 26 * S], fill=255)
    d.ellipse([sx - 24 * S, sy - 24 * S, sx + 24 * S, sy + 24 * S], fill=255)
    arm = arm.resize((300, 300), Image.LANCZOS)
    arm_img = soft(np.array(arm) > 128)
    bam = Image.new("L", (60 * S, 520 * S), 0)
    ImageDraw.Draw(bam).rounded_rectangle([22 * S, 4 * S, 38 * S, 516 * S], 8 * S, fill=255)
    bam = bam.resize((60, 520), Image.LANCZOS)
    bam_img = soft(np.array(bam) > 128, 1.6)
    scale_px = (ys.max() - top) / 3.55                # 母版：腳底到頭頂＝3.55 世界單位
    return body_img, arm_img, bam_img, {
        "body_px_per_unit": round(scale_px, 2), "body_size_px": list(body_img.shape[1::-1]),
        "arm_pivot_px": [240, 250], "arm_px_per_unit": round(scale_px, 2), "bamboo_px_per_unit": round(scale_px, 2),
        "shoulder_in_body_px": [int(xc - 0.21 * (xs.max() - xs.min())) - xb.min() + 12, shoulder - yb.min() + 12],
    }


def boxclose():
    """盒子特寫：沿用共用美術的 prop-sticker-box，只把透明處的雜色清掉（避免縮放時邊緣滲色）。"""
    im = np.array(Image.open(ROOT / "assets/final/props/prop-sticker-box_v01.png").convert("RGBA"))
    m = im[..., 3] >= 128
    im[..., 3] = np.where(m, 255, 0)
    return im, {"source": "assets/final/props/prop-sticker-box_v01.png"}


# ───────────────────────────── 角色補姿勢 ─────────────────────────────
def xiaoyu_watch():
    """小宇站姿（v04 母版）＋左腕兒童手錶：深藍錶帶、淺色錶面、只有圓點刻度。位置在畫面右側那隻手的手腕（袖口下緣）。"""
    src = Image.open(ROOT / "assets/final/chr-xiaoyu_master_v04.png").convert("RGBA")
    S = 4
    big = src.resize((src.width * S, src.height * S), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    # 手腕（袖口下緣）：量自母版
    band = [(433, 792), (487, 800)]
    bx0, by0 = band[0]
    bx1, by1 = band[1]
    poly = [(bx0 * S, by0 * S), (bx1 * S, by1 * S), (bx1 * S - 2 * S, (by1 + 15) * S), (bx0 * S + 1 * S, (by0 + 15) * S)]
    d.polygon(poly, fill=(46, 58, 92, 255), outline=(30, 36, 56, 255), width=2 * S)
    fx, fy = (bx0 + bx1) / 2 + 2, (by0 + by1) / 2 + 7
    d.rounded_rectangle([(fx - 15) * S, (fy - 12) * S, (fx + 15) * S, (fy + 12) * S], 6 * S, fill=(214, 232, 236, 255), outline=(30, 36, 56, 255), width=2 * S)
    for k in range(4):
        a = k * math.pi / 2
        d.ellipse([(fx + 8 * math.cos(a) - 1.4) * S, (fy + 7 * math.sin(a) - 1.4) * S, (fx + 8 * math.cos(a) + 1.4) * S, (fy + 7 * math.sin(a) + 1.4) * S], fill=(60, 70, 96, 255))
    out = big.resize(src.size, Image.LANCZOS)
    a = np.array(out)
    a0 = np.array(src)
    # 透明度維持原圖（不改外形與臉部範圍）
    a[..., 3] = a0[..., 3]
    return a, {"source": "chr-xiaoyu_master_v04.png", "watch_center_px": [fx, fy]}


def pinan_back():
    src = np.array(Image.open(ROOT / "assets/final/chr-pinan_pose-sit-lantern_v01.png").convert("RGBA"))
    return src[:, ::-1].copy(), {"source": "chr-pinan_pose-sit-lantern_v01.png（左右鏡像）"}


def mirror(src_name, note):
    def f():
        src = np.array(Image.open(ROOT / "assets/final" / src_name).convert("RGBA"))
        return src[:, ::-1].copy(), {"source": f"{src_name}（左右鏡像，{note}）"}
    return f


def main():
    jobs = [
        (OUT0 / "design_v01.png", design), (OUT0 / "stand_v01.png", stand), (OUT0 / "chime_v01.png", chime),
        (OUT0 / "lamps_v01.png", lamps), (OUT0 / "memoryframe_v01.png", memoryframe), (OUT0 / "notebook_v01.png", notebook),
        (OUT1 / "pillar_v01.png", pillar), (OUT1 / "garland_v01.png", garland), (OUT1 / "townsfolk_v01.png", townsfolk),
        (OUT1 / "wrapper_v01.png", wrapper), (OUT1 / "shopwindow_v01.png", shopwindow), (OUT1 / "windowpaper_v01.png", windowpaper),
        (OUT1 / "boxclose_v01.png", boxclose),
        (ROOT / "assets/final/chr-xiaoyu_pose-standwatch_v01.png", xiaoyu_watch),
        (ROOT / "assets/final/chr-pinan_pose-sit-lantern-back_v01.png", pinan_back),
        (ROOT / "assets/final/chr-xiaoqing_pose-walkl_v01.png", mirror("chr-xiaoqing_pose-walk_v06.png", "往畫面左走")),
    ]
    only = set(sys.argv[1:])
    for path, fn in jobs:
        if only and path.stem.rsplit("_v", 1)[0] not in only and fn.__name__ not in only:
            continue
        a, m = fn()
        if path.name == "memoryframe_v01.png":
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(a, "RGBA").save(path, optimize=True)
        else:
            P.save(a, path)
        meta[str(path.relative_to(ROOT))] = {**m, "size": list(a.shape[1::-1])}
        print("wrote", path.relative_to(ROOT), a.shape[1::-1])
    if not only or "silhouettes" in only:
        b, ar, bm, m = silhouettes()
        for name, a in (("silbody", b), ("silarm", ar), ("silbamboo", bm)):
            p = OUT1 / f"{name}_v01.png"
            P.save(a, p)
            print("wrote", p.relative_to(ROOT), a.shape[1::-1])
        meta["assets/final/sets/square_a1/sil*_v01.png"] = m
    mp = ROOT / "review/G5/a0/scripts/build_a01_art_meta.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    old.update(meta)
    mp.write_text(json.dumps(old, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
