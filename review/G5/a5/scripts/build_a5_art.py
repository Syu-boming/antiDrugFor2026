"""第五幕（a5）程式繪製素材：校門口加的街角、轉角的低年級學生、救護車（自訂愛心手掌圖示、無紅十字、頂燈恆亮）、
擔架、119 電話聲波圖示；醫院走廊的地板與候診長椅；陳伯伯轉身朝右（站姿鏡射）。

為什麼是程式繪製：這些都是道具或背景小件，Pillow＋G2 同款紙紋（review/G5/shared_art/scripts/paperdraw.py：平塗色塊、
暖深灰細線、無方向光）做得到，和校門口景片、小貨車同一套畫法；Codex 額度只用在角色新姿勢與醫院主景（review/G5/a5/codex_log.md）。
圖裡不放任何文字、數字、品牌、標誌；救護車只用自訂的「手捧愛心」圖示（同求助站與葉護理師識別證），不用紅十字、不用真實救護單位的配色。

輸出：
  assets/final/sets/a5_gate/a5-*_v01.png
  assets/final/sets/a5_hospital/{floor,bench}_v01.png
  assets/final/chr-chen_pose-standr_v01.png（站姿鏡射：朝畫面右）
  review/G5/a5/art_meta.json（尺寸、錨點，給 app/src/sets/a5_gate.ts 對照）
用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/build_a5_art.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

GATE = ROOT / "assets/final/sets/a5_gate"
HOSP = ROOT / "assets/final/sets/a5_hospital"
INK = P.INK

CREAM = (246, 240, 226, 255)
CREAM2 = (232, 224, 206, 255)
SAGE = (150, 182, 160, 255)
SAGE2 = (128, 162, 140, 255)
CORAL = (226, 128, 110, 255)
GLASS = (206, 223, 226, 255)
GLASS2 = (186, 205, 210, 255)
GRAY = (172, 172, 168, 255)
DGRAY = (110, 108, 104, 255)
SKIN = (236, 196, 160, 255)
AMBER = (250, 218, 150, 255)


def heart_hand(s, cx, cy, k):
    """手捧愛心圖示（同第二幕求助站 review/G5/a2/scripts/build_a2_art.py；不用紅十字）。"""
    s.poly([(cx - 70 * k, cy + 10 * k), (cx + 70 * k, cy + 10 * k), (cx + 60 * k, cy + 36 * k), (cx + 20 * k, cy + 52 * k),
            (cx - 30 * k, cy + 50 * k), (cx - 64 * k, cy + 34 * k)], SKIN, line=2.2)
    for i in range(4):
        x = cx - 50 * k + i * 26 * k
        s.line([(x, cy + 12 * k), (x + 8 * k, cy + 30 * k)], w=1.4)
    hx, hy, r = cx, cy - 28 * k, 26 * k
    s.ellipse(hx - 2 * r + 4 * k, hy - r, hx + 4 * k, hy + r * 0.9, CORAL, line=0)
    s.ellipse(hx - 4 * k, hy - r, hx + 2 * r - 4 * k, hy + r * 0.9, CORAL, line=0)
    s.poly([(hx - 2 * r + 6 * k, hy + 6 * k), (hx + 2 * r - 6 * k, hy + 6 * k), (hx, hy + 2.1 * r)], CORAL, line=0)


# ------------------------------------------------------------------ 救護車（側面，車頭朝右）
AMB_PPU = 150
AMB_L, AMB_H = 5.6, 2.5          # 世界單位（不含頂燈）


def ambulance():
    W, H = int(AMB_L * AMB_PPU), int(AMB_H * AMB_PPU)
    s = P.Sheet(W, H)
    u = AMB_PPU
    ground = H - 4
    wheel_r = 0.42 * u
    wy = ground - wheel_r                    # 輪心
    box_x1 = int(3.75 * u)                   # 後車廂右緣（駕駛艙從這裡開始）
    body_bot = ground - int(0.30 * u)
    # 後車廂（圓角方箱）
    s.rect(6, int(0.08 * u), box_x1, body_bot, CREAM, line=2.4, r=int(0.12 * u))
    # 駕駛艙（斜擋風玻璃）
    cab = [(box_x1 - 4, int(0.42 * u)), (int(4.75 * u), int(0.42 * u)), (int(5.35 * u), int(1.18 * u)), (W - 8, int(1.32 * u)),
           (W - 8, body_bot), (box_x1 - 4, body_bot)]
    s.poly(cab, CREAM, line=2.4)
    # 下緣保險桿與裙邊
    s.rect(2, body_bot - 4, W - 4, body_bot + int(0.12 * u), CREAM2, line=2.0, r=6)
    # 側面鼠尾草綠寬帶（車廂＋駕駛艙）
    by0, by1 = int(1.34 * u), int(1.62 * u)
    s.rect(8, by0, box_x1 - 2, by1, SAGE, line=0)
    s.poly([(box_x1 - 2, by0), (W - 10, by0), (W - 10, by1), (box_x1 - 2, by1)], SAGE, line=0)
    s.line([(8, by0), (W - 10, by0)], w=1.4)
    s.line([(8, by1), (W - 10, by1)], w=1.4)
    # 駕駛艙側窗＋擋風玻璃
    s.poly([(box_x1 + int(0.12 * u), int(0.56 * u)), (int(4.68 * u), int(0.56 * u)), (int(5.16 * u), int(1.16 * u)),
            (box_x1 + int(0.12 * u), int(1.16 * u))], GLASS, line=2.0)
    s.line([(int(4.45 * u), int(0.56 * u)), (int(4.45 * u), int(1.16 * u))], w=1.6)
    # 車門線、門把
    s.line([(box_x1 + int(0.06 * u), int(0.5 * u)), (box_x1 + int(0.06 * u), body_bot - 6)], w=1.4)
    s.line([(int(4.92 * u), int(1.2 * u)), (int(4.92 * u), body_bot - 6)], w=1.4)
    s.rect(int(4.62 * u), int(1.24 * u), int(4.78 * u), int(1.3 * u), DGRAY, line=1.2, r=3)
    # 車廂側窗（霧面）與側滑門
    s.rect(int(0.35 * u), int(0.42 * u), int(1.25 * u), int(1.06 * u), GLASS2, line=2.0, r=8)
    s.line([(int(2.6 * u), int(0.22 * u)), (int(2.6 * u), body_bot - 6)], w=1.4)
    s.rect(int(2.68 * u), int(1.0 * u), int(2.82 * u), int(1.06 * u), DGRAY, line=1.2, r=3)
    # 後車門（左端）
    s.line([(int(0.18 * u), int(0.16 * u)), (int(0.18 * u), body_bot - 6)], w=1.4)
    # 手捧愛心圖示（白底圓牌）在車廂側面中央
    cx, cy = int(1.95 * u), int(0.82 * u)
    rr = int(0.40 * u)
    s.ellipse(cx - rr, cy - rr, cx + rr, cy + rr, (252, 249, 242, 255), line=2.2)
    heart_hand(s, cx, cy + int(0.02 * u), 0.62)
    # 車頭燈（米黃、不亮）、方向燈
    s.rect(W - 26, int(1.42 * u), W - 8, int(1.6 * u), (244, 230, 190, 255), line=1.4, r=4)
    # 輪拱（深色，輪子另外疊）
    for wx in (int(1.0 * u), int(4.55 * u)):
        s.d.pieslice([(wx - wheel_r - 10) * 2, (wy - wheel_r - 10) * 2, (wx + wheel_r + 10) * 2, (wy + wheel_r + 10) * 2], 180, 360,
                     fill=(92, 84, 78, 255))
        s.d.rectangle([(wx - wheel_r - 10) * 2, wy * 2, (wx + wheel_r + 10) * 2, (ground - 2) * 2], fill=(92, 84, 78, 255))
    a = s.finish(white_border=0)
    meta = {"size_world": [AMB_L, AMB_H], "wheels_world_from_bottom_center": [[1.0 - AMB_L / 2, (H - wy) / u], [4.55 - AMB_L / 2, (H - wy) / u]],
            "wheel_diameter_world": 0.84, "light_world_from_bottom_center": [4.25 - AMB_L / 2, (H - 0.42 * u) / u]}
    return a, meta


def ambulance_light():
    """駕駛艙頂的燈條（暖米黃、恆亮；不是紅藍警示燈）"""
    w, h = 1.1, 0.28
    PPW = 300
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    s.rect(6, int(H * 0.62), W - 6, H - 4, DGRAY, line=1.6, r=4)
    s.rect(14, 6, W - 14, int(H * 0.68), AMBER, line=2.0, r=int(H * 0.3))
    s.line([(W * 0.35, 10), (W * 0.35, H * 0.64)], w=1.2, color=(222, 186, 118, 255))
    s.line([(W * 0.65, 10), (W * 0.65, H * 0.64)], w=1.2, color=(222, 186, 118, 255))
    return s.finish(white_border=0), (w, h)


def gurney():
    """摺好的擔架床（側面）：淺灰金屬架、米白床墊、鼠尾草綠摺好的毯子、小輪子"""
    w, h = 2.2, 1.05
    PPW = 200
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    top = int(H * 0.36)
    for x in (int(W * 0.16), int(W * 0.84)):
        s.line([(x, top + 20), (x - 22, H - 26)], w=6, color=(176, 182, 186, 255))
        s.line([(x, top + 20), (x + 22, H - 26)], w=6, color=(176, 182, 186, 255))
        for dx in (-22, 22):
            s.ellipse(x + dx - 13, H - 30, x + dx + 13, H - 4, (90, 90, 92, 255), line=1.6)
    s.rect(10, top + 8, W - 10, top + 26, (188, 194, 198, 255), line=2.0, r=6)
    s.rect(18, top - 34, W - 18, top + 10, (244, 240, 230, 255), line=2.2, r=14)
    s.rect(int(W * 0.5), top - 52, int(W * 0.82), top - 26, SAGE, line=2.0, r=8)
    s.line([(int(W * 0.5) + 8, top - 39), (int(W * 0.82) - 8, top - 39)], w=1.2, color=SAGE2)
    s.rect(30, top - 50, int(W * 0.24), top - 30, (250, 248, 242, 255), line=1.8, r=10)   # 枕頭
    return s.finish(white_border=0), (w, h)


# ------------------------------------------------------------------ 街角、轉角的低年級學生
def corner():
    """街角的兩層小店（左邊建築物的轉角）：右緣是轉角柱；樓下拉下的鐵捲門、小雨遮；沒有招牌字"""
    w, h = 2.6, 5.4
    PPW = 110
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    wall = (232, 204, 170, 255)
    trim = (246, 230, 204, 255)
    s.rect(4, int(0.25 * PPW), W - 4, H - 4, wall, line=2.2)
    s.rect(0, int(0.18 * PPW), W, int(0.36 * PPW), trim, line=2.0)                 # 女兒牆
    s.rect(W - int(0.42 * PPW), int(0.3 * PPW), W - 4, H - 4, trim, line=2.0)      # 轉角柱
    for i in range(1, 9):
        y = int(0.3 * PPW) + i * int(0.55 * PPW)
        s.line([(W - int(0.42 * PPW) + 4, y), (W - 8, y)], w=1.0, color=(214, 196, 168, 255))
    # 二樓窗
    s.rect(int(0.35 * PPW), int(0.9 * PPW), int(1.75 * PPW), int(2.2 * PPW), (196, 214, 214, 255), line=2.0)
    s.line([(int(1.05 * PPW), int(0.9 * PPW)), (int(1.05 * PPW), int(2.2 * PPW))], w=1.6)
    s.rect(int(0.25 * PPW), int(2.2 * PPW), int(1.85 * PPW), int(2.32 * PPW), trim, line=1.6)
    # 雨遮
    s.poly([(0, int(2.9 * PPW)), (W - int(0.42 * PPW), int(2.9 * PPW)), (W - int(0.42 * PPW) - 10, int(3.25 * PPW)),
            (10, int(3.25 * PPW))], (128, 160, 156, 255), line=2.0)
    # 鐵捲門
    s.rect(int(0.2 * PPW), int(3.3 * PPW), W - int(0.55 * PPW), H - 6, (206, 206, 200, 255), line=2.0)
    for i in range(1, 16):
        y = int(3.3 * PPW) + i * int(0.135 * PPW)
        if y < H - 10:
            s.line([(int(0.2 * PPW) + 4, y), (W - int(0.55 * PPW) - 4, y)], w=1.0, color=(178, 178, 172, 255))
    return s.finish(white_border=0), (w, h)


def student():
    """轉角的低年級學生（遠景小尺寸、中性：黃色小帽、深藍上衣、灰短褲、綠書包；沒有五官細節）。舉起揮手的手臂另一張。"""
    w, h = 0.95, 2.05
    PPW = 220
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    cx = W * 0.5
    g = H - 6
    navy = (92, 110, 148, 255)
    shorts = (150, 148, 140, 255)
    pack = (122, 160, 112, 255)
    cap = (240, 198, 86, 255)
    # 書包（身體後面，畫面左）
    s.rect(cx - 70, H * 0.33, cx - 18, H * 0.62, pack, line=2.0, r=12)
    # 腿、鞋
    s.rect(cx - 30, H * 0.7, cx - 8, g - 20, SKIN, line=1.8)
    s.rect(cx + 6, H * 0.7, cx + 28, g - 20, SKIN, line=1.8)
    s.rect(cx - 32, g - 30, cx - 6, g - 18, (250, 248, 240, 255), line=1.4)
    s.rect(cx + 4, g - 30, cx + 30, g - 18, (250, 248, 240, 255), line=1.4)
    s.ellipse(cx - 40, g - 22, cx - 2, g, (80, 76, 74, 255), line=1.6)
    s.ellipse(cx + 2, g - 22, cx + 40, g, (80, 76, 74, 255), line=1.6)
    s.rect(cx - 38, H * 0.6, cx + 38, H * 0.74, shorts, line=2.0, r=6)
    # 身體（上衣）
    s.rect(cx - 40, H * 0.32, cx + 40, H * 0.63, navy, line=2.0, r=14)
    # 垂下的手臂（畫面左）
    s.rect(cx - 52, H * 0.35, cx - 32, H * 0.58, navy, line=1.8, r=8)
    s.ellipse(cx - 54, H * 0.56, cx - 32, H * 0.63, SKIN, line=1.6)
    # 書包背帶
    s.line([(cx - 22, H * 0.33), (cx - 14, H * 0.58)], w=5, color=(98, 134, 92, 255))
    # 頭、小帽
    s.ellipse(cx - 40, H * 0.1, cx + 40, H * 0.32, SKIN, line=2.0)
    s.ellipse(cx - 44, H * 0.06, cx + 44, H * 0.2, cap, line=2.0)
    s.rect(cx + 20, H * 0.15, cx + 62, H * 0.19, cap, line=1.8, r=6)               # 帽簷（朝畫面右）
    s.ellipse(cx + 8, H * 0.21, cx + 18, H * 0.235, (78, 62, 51, 255), line=0)     # 一點眼睛（遠景）
    body = s.finish(white_border=0)
    # 揮手的手臂（肩膀在圖的下緣中央）
    aw, ah = 0.3, 0.62
    AP = 220
    AW, AH = int(aw * AP), int(ah * AP)
    t = P.Sheet(AW, AH)
    t.rect(AW * 0.5 - 11, AH * 0.3, AW * 0.5 + 11, AH - 4, navy, line=1.8, r=8)
    t.ellipse(AW * 0.5 - 16, AH * 0.08, AW * 0.5 + 16, AH * 0.36, SKIN, line=1.8)
    arm = t.finish(white_border=0)
    meta = {"size_world": [w, h], "arm_size_world": [aw, ah], "shoulder_world_from_bottom_center": [0.40 / PPW * 0 + (52 - 42) / PPW, H * (1 - 0.36) / PPW]}
    return body, arm, meta


# ------------------------------------------------------------------ 119 電話聲波圖示
def phone_icon():
    """紙剪的電話聽筒（米白圓牌、深青綠聽筒）；聲波弧線另三張（只在執勤人員說話時慢慢起伏）"""
    D = 260
    s = P.Sheet(D, D)
    s.ellipse(6, 6, D - 6, D - 6, (250, 244, 230, 255), line=3.0)
    s.ellipse(20, 20, D - 20, D - 20, (238, 226, 204, 255), line=1.4)
    teal = (74, 128, 128, 255)
    # 聽筒（經典話筒剪影：中間弧形握把＋兩端耳承與話筒，整支斜放 −40°）：先在大畫布畫水平的，再旋轉貼上
    from PIL import ImageDraw
    B = 4 * D
    hs = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hs)
    k = 4
    cxh, cyh = B / 2, B / 2
    # 握把：上凸的粗弧（PIL 角度順時針、0°＝三點鐘）
    rx, ry = 92 * k, 75 * k
    ecx, ecy = cxh, cyh + 35 * k
    hd.arc([ecx - rx, ecy - ry, ecx + rx, ecy + ry], 205, 335, fill=teal, width=30 * k)
    # 兩端：耳承／話筒＝往弧內側（徑向朝圓心）伸出的寬塊，寬邊沿切線
    for ang in (205, 335):
        th = math.radians(ang)
        ex, ey = ecx + rx * math.cos(th), ecy + ry * math.sin(th)
        inx, iny = ecx - ex, ecy - ey
        n = math.hypot(inx, iny)
        inx, iny = inx / n, iny / n
        tx, ty = -iny, inx
        L0, L1, Wd = -10 * k, 40 * k, 34 * k
        pts = [(ex + inx * L0 + tx * Wd, ey + iny * L0 + ty * Wd), (ex + inx * L1 + tx * Wd * 0.8, ey + iny * L1 + ty * Wd * 0.8),
               (ex + inx * L1 - tx * Wd * 0.8, ey + iny * L1 - ty * Wd * 0.8), (ex + inx * L0 - tx * Wd, ey + iny * L0 - ty * Wd)]
        hd.polygon(pts, fill=teal)
        for (qx, qy) in pts:
            hd.ellipse([qx - 3 * k, qy - 3 * k, qx + 3 * k, qy + 3 * k], fill=teal)
    hs = hs.rotate(40, resample=Image.BICUBIC, center=(cxh, cyh + 10 * k))
    hs = hs.resize((D, D), Image.LANCZOS)
    big = s.img
    big.alpha_composite(hs.resize(big.size, Image.LANCZOS), (0, 0))
    s.d = ImageDraw.Draw(big)
    icon = s.finish(white_border=0)
    arcs = []
    for i in range(3):
        R = 34 + i * 26
        A = R * 2 + 20
        t = P.Sheet(A, A)
        a0 = A / 2
        pts = [(a0 + R * math.cos(math.radians(th)), a0 + R * math.sin(math.radians(th))) for th in range(-45, 46, 5)]
        t.line(pts, w=11, color=(250, 244, 230, 255))
        t.line(pts, w=6, color=(98, 150, 146, 255))
        arcs.append(t.finish(white_border=0))
    return icon, arcs


# ------------------------------------------------------------------ 醫院走廊：地板、候診長椅
def hosp_floor():
    W, H = 1024, 512
    a = np.zeros((H, W, 4), np.float32)
    base = np.array([214, 186, 146], np.float32)
    a[..., :3] = base
    a[..., 3] = 255
    rng = np.random.default_rng(5)
    # 長條木紋地板（橫向長條、接縫）
    ph = 64
    for r in range(H // ph):
        off = rng.integers(0, 256)
        shade = rng.uniform(-6, 6)
        a[r * ph:(r + 1) * ph, :, :3] += shade
        a[r * ph:r * ph + 2, :, :3] -= 26
        for x in range(off, W, 256):
            a[r * ph:(r + 1) * ph, x:x + 2, :3] -= 22
    a[..., :3] *= P.paper_tex(W, H)[..., None]
    return np.clip(a, 0, 255).astype(np.uint8)


def hosp_bench():
    """候診長椅（四個連在一起的座位：淺木色座面與椅背、鐵灰色橫樑與椅腳）。座面上緣＝世界 0.92。"""
    w, h = 4.6, 1.9
    PPW = 200
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    seat_y = H - int(0.92 * PPW)
    wood = (214, 170, 120, 255)
    wood2 = (196, 152, 104, 255)
    steel = (128, 132, 136, 255)
    # 椅腳與橫樑
    for x in (int(0.35 * PPW), W // 2, W - int(0.35 * PPW)):
        s.rect(x - 10, seat_y + 30, x + 10, H - 6, steel, line=1.8)
        s.rect(x - 40, H - 16, x + 40, H - 4, steel, line=1.6, r=4)
    s.rect(14, seat_y + 30, W - 14, seat_y + 48, steel, line=1.8, r=4)
    n = 4
    sw = (W - 40) / n
    for i in range(n):
        x0 = 20 + i * sw + 8
        x1 = 20 + (i + 1) * sw - 8
        # 椅背
        s.rect(x0 + 10, 10, x1 - 10, seat_y - 26, wood, line=2.2, r=26)
        s.line([(x0 + 26, seat_y - 60), (x1 - 26, seat_y - 60)], w=1.2, color=wood2)
        s.rect((x0 + x1) / 2 - 8, seat_y - 30, (x0 + x1) / 2 + 8, seat_y + 2, steel, line=1.4)
        # 座面（前緣）
        s.rect(x0, seat_y - 4, x1, seat_y + 32, wood, line=2.2, r=12)
        s.line([(x0 + 12, seat_y + 10), (x1 - 12, seat_y + 10)], w=1.0, color=wood2)
    return s.finish(white_border=0), (w, h), {"seat_top_world": 0.92 + 4 / PPW}


def chen_standr():
    src = Image.open(ROOT / "assets/final/chr-chen_master_v01.png").convert("RGBA")
    return np.array(src.transpose(Image.FLIP_LEFT_RIGHT))


def main():
    meta = {"made_by": "review/G5/a5/scripts/build_a5_art.py"}
    a, m = ambulance()
    P.save(a, GATE / "a5-ambulance_v01.png")
    meta["ambulance"] = m
    a, wh = ambulance_light()
    P.save(a, GATE / "a5-ambulance-light_v01.png")
    meta["ambulance_light"] = {"size_world": wh}
    a, wh = gurney()
    P.save(a, GATE / "a5-gurney_v01.png")
    meta["gurney"] = {"size_world": wh}
    a, wh = corner()
    P.save(a, GATE / "a5-corner_v01.png")
    meta["corner"] = {"size_world": wh}
    body, arm, m = student()
    P.save(body, GATE / "a5-student_v01.png")
    P.save(arm, GATE / "a5-student-arm_v01.png")
    meta["student"] = m
    icon, arcs = phone_icon()
    # 電話圖示本體改由 phone_icon_v2.py 畫 a5-phone_v02.png（v01 的話筒兩端像彎箭頭，已刪）；這裡只輸出聲波弧線
    del icon
    for i, ar in enumerate(arcs):
        P.save(ar, GATE / f"a5-phone-arc{i + 1}_v01.png")
    HOSP.mkdir(parents=True, exist_ok=True)
    Image.fromarray(hosp_floor(), "RGBA").convert("RGB").save(HOSP / "floor_v01.png", optimize=True)
    a, wh, m = hosp_bench()
    P.save(a, HOSP / "bench_v01.png")
    meta["hosp_bench"] = {"size_world": wh, **m}
    dst = ROOT / "assets/final/chr-chen_pose-standr_v01.png"
    if not dst.exists():
        Image.fromarray(chen_standr(), "RGBA").save(dst, optimize=True)
    (ROOT / "review/G5/a5/art_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
