"""G5 第二幕（a2）景片與小道具 —— 程式繪製的厚卡紙景片（Codex image_gen 額度用完時的退路版）。

畫法沿用 G5 共用美術 review/G5/shared_art/scripts/paperdraw.py：平塗色塊＋G2 景片同款紙紋、暖深灰細線、無陰影、無方向光；
圖裡不放任何文字、數字、標誌；求助站不用紅十字（愛心＋手掌圖示，同葉護理師識別證）。
回憶小窗重用既有素材：props/prop-sticker-box（a1_c003 的盒子）、chr-inviter_hand-box（邀請者的手，只取剪影）、阿樂叔叔分件手臂（只取剪影）。

輸出（assets/final/sets/<景>/）：
  a2_memory/  mem-box_v01.png、mem-wrapper_v01.png（褪色回想小窗兩張，含紙框）
  a2_helpdesk/ tent_v01.png（求助站帳篷＋桌子）、crate_v01.png（紙箱）
  a2_window/  sky_v01.png、facade_v01.png（店面，窗與門挖空）、interior_v01.png（店內暖牆）、stool_v01.png、
              sil-frame_v01.png（剪影小窗：背光紙框）、sil-hand-box_v01.png、sil-ale-hand_v01.png、notebook_v01.png、
              glass_v01.png（窗玻璃淡暖色，半透明用）
用法：/opt/anaconda3/bin/python3 review/G5/a2/scripts/build_a2_art.py
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

FINAL = ROOT / "assets/final"
INK = P.INK


def out(setname, name):
    return FINAL / "sets" / setname / f"{name}_v01.png"


def tex_mul(a):
    a = a.astype(np.float32)
    a[..., :3] *= P.paper_tex(a.shape[1], a.shape[0])[..., None]
    return np.clip(a, 0, 255).astype(np.uint8)


def deckle_mask(w, h, margin, seed, amp=5.0):
    """撕紙毛邊的不透明遮罩（四邊不規則）。"""
    rng = np.random.default_rng(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    pts = []
    n = 90
    for side in range(4):
        for i in range(n):
            u = i / n
            jitter = (rng.random() - 0.5) * amp * 2 + math.sin(u * 23 + seed) * amp * 0.4
            if side == 0:
                pts.append((margin + u * (w - 2 * margin), margin + jitter))
            elif side == 1:
                pts.append((w - margin + jitter, margin + u * (h - 2 * margin)))
            elif side == 2:
                pts.append((w - margin - u * (w - 2 * margin), h - margin + jitter))
            else:
                pts.append((margin + jitter, h - margin - u * (h - 2 * margin)))
    d.polygon(pts, fill=255)
    return np.array(m.filter(ImageFilter.GaussianBlur(0.8)))


def fade_photo(rgb, amount=0.55, warm=(244, 226, 196)):
    """褪色：降彩、抬亮、偏暖（回憶）。rgb：float32 HxWx3。"""
    g = rgb.mean(axis=2, keepdims=True)
    rgb = rgb * (1 - amount) + g * amount
    w = np.array(warm, np.float32)
    rgb = rgb * 0.72 + w * 0.28
    return rgb


# ------------------------------------------------------------------ 回憶小窗（a2_c003）
def ground(w, h, seed):
    """廣場地磚（暖米色，簡單磚縫）。"""
    s = P.Sheet(w, h)
    s.rect(0, 0, w, h, (222, 200, 164, 255), line=0)
    rng = random.Random(seed)
    for row in range(0, h, 70):
        off = 0 if (row // 70) % 2 == 0 else 60
        s.line([(0, row), (w, row)], w=1.4, color=(170, 146, 112, 255))
        for x in range(-off, w, 120):
            s.line([(x, row), (x, row + 70)], w=1.4, color=(170, 146, 112, 255))
    for _ in range(40):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        s.ellipse(x, y, x + rng.uniform(2, 5), y + rng.uniform(2, 4), (190, 168, 132, 255), line=0)
    return s.finish().astype(np.float32)


def framed_card(photo_rgba, W, H, seed, inner_pad=46):
    """把照片放進米白紙框（毛邊、內框細線）。"""
    card = np.zeros((H, W, 4), np.float32)
    paper = np.array([246, 238, 222], np.float32) * P.paper_tex(W, H)[..., None]
    card[..., :3] = paper
    card[..., 3] = deckle_mask(W, H, 8, seed, amp=4.0)
    ph, pw = H - inner_pad * 2, W - inner_pad * 2
    im = Image.fromarray(photo_rgba.astype(np.uint8), "RGBA").resize((pw, ph), Image.LANCZOS)
    pa = np.array(im).astype(np.float32)
    al = pa[..., 3:4] / 255
    reg = card[inner_pad:inner_pad + ph, inner_pad:inner_pad + pw, :3]
    card[inner_pad:inner_pad + ph, inner_pad:inner_pad + pw, :3] = reg * (1 - al) + pa[..., :3] * al
    # 內框細線（暖灰）
    d = Image.fromarray(card.astype(np.uint8), "RGBA")
    dd = ImageDraw.Draw(d)
    dd.rectangle([inner_pad - 3, inner_pad - 3, inner_pad + pw + 2, inner_pad + ph + 2], outline=(150, 128, 104, 255), width=3)
    a = np.array(d)
    a[..., 3] = card[..., 3].astype(np.uint8)
    return a


def mem_box():
    W, H = 1040, 800
    pw, ph = W - 92, H - 92
    bg = ground(pw, ph, 3)
    box = Image.open(FINAL / "props/prop-sticker-box_v01.png").convert("RGBA")
    bw = int(pw * 0.62)
    box = box.resize((bw, int(box.height * bw / box.width)), Image.LANCZOS)
    ba = np.array(box).astype(np.float32)
    x0, y0 = (pw - bw) // 2, int(ph * 0.5 - ba.shape[0] * 0.48)
    # 盒底柔影（紙片接觸陰影）
    sh = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(sh).ellipse([x0 + 20, y0 + ba.shape[0] - 40, x0 + bw - 10, y0 + ba.shape[0] + 26], fill=120)
    sh = np.array(sh.filter(ImageFilter.GaussianBlur(14))).astype(np.float32)[..., None] / 255
    bg[..., :3] *= 1 - 0.28 * sh
    al = ba[..., 3:4] / 255
    reg = bg[y0:y0 + ba.shape[0], x0:x0 + bw, :3]
    bg[y0:y0 + ba.shape[0], x0:x0 + bw, :3] = reg * (1 - al) + ba[..., :3] * al
    bg[..., :3] = fade_photo(bg[..., :3], 0.5)
    bg[..., 3] = 255
    return framed_card(bg, W, H, 11)


def thread_tangle(d, cx, cy, r, seed, ss=1.0):
    """一團灰色紙線（同操偶線的淡灰紙繩＋深灰邊）。"""
    rng = random.Random(seed)
    pts = []
    a = rng.uniform(0, 6.28)
    x, y = cx, cy
    for i in range(70):
        a += rng.uniform(-1.1, 1.1)
        step = r * rng.uniform(0.12, 0.3)
        x += math.cos(a) * step
        y += math.sin(a) * step
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        if dist > r:
            x, y = cx + dx / dist * r * 0.9, cy + dy / dist * r * 0.9
            a += 2.4
        pts.append((x, y))
    # 尾巴：一小截線頭伸出
    tail = [pts[-1], (pts[-1][0] + r * 0.9, pts[-1][1] + r * 0.35), (pts[-1][0] + r * 1.6, pts[-1][1] + r * 0.2)]
    for seg in (pts, tail):
        d.line(seg, fill=(82, 74, 70, 255), width=int(13 * ss), joint="curve")
    for seg in (pts, tail):
        d.line(seg, fill=(178, 176, 172, 255), width=int(8 * ss), joint="curve")
    for seg in (pts, tail):
        d.line([(p[0] - 1.5 * ss, p[1] - 1.5 * ss) for p in seg], fill=(214, 212, 206, 255), width=max(1, int(2 * ss)), joint="curve")


def mem_wrapper():
    W, H = 1040, 800
    pw, ph = W - 92, H - 92
    bg = ground(pw, ph, 5)
    # 撕破的包裝紙：取盒子正面的貼紙紋路，裁成不規則撕邊
    box = Image.open(FINAL / "props/prop-sticker-box_v01.png").convert("RGBA")
    face = box.crop((40, 130, 420, 500)).resize((560, 540), Image.LANCZOS)
    fa = np.array(face).astype(np.float32)
    m = Image.new("L", face.size, 0)
    rng = random.Random(7)
    poly = []
    for i in range(40):
        ang = i / 40 * 6.283
        rr = 230 + rng.uniform(-30, 30) + (60 if 0.3 < ang < 1.4 else 0)
        poly.append((280 + math.cos(ang) * rr * 1.05, 270 + math.sin(ang) * rr * 0.86))
    ImageDraw.Draw(m).polygon(poly, fill=255)
    mm = np.array(m).astype(np.float32) / 255
    # 撕開的白色紙芯邊
    core = ndimage.binary_dilation(mm > 0.5, iterations=7) & ~(mm > 0.5)
    sx, sy = int(pw * 0.14), int(ph * 0.12)
    reg = bg[sy:sy + 540, sx:sx + 560, :3]
    al = (mm * (fa[..., 3] / 255))[..., None]
    reg[:] = reg * (1 - al) + fa[..., :3] * al
    reg[core] = reg[core] * 0.15 + np.array([248, 244, 236]) * 0.85
    # 撕口裡糾結的一團灰線
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    thread_tangle(d, sx + 400, sy + 330, 120, 21)
    bg = np.array(img).astype(np.float32)
    bg[..., :3] = fade_photo(bg[..., :3], 0.5)
    bg[..., 3] = 255
    return framed_card(bg, W, H, 13)


# ------------------------------------------------------------------ 求助站（a2_c012）
SAGE = (156, 186, 158, 255)
SAGE2 = (132, 166, 138, 255)
CREAM = (244, 236, 216, 255)
WOOD = (176, 132, 92, 255)


def heart_hand(s, cx, cy, k):
    """手捧愛心圖示（同葉護理師識別證；不用紅十字）。"""
    # 手掌（張開朝上的弧形）
    s.poly([(cx - 70 * k, cy + 10 * k), (cx + 70 * k, cy + 10 * k), (cx + 60 * k, cy + 36 * k), (cx + 20 * k, cy + 52 * k),
            (cx - 30 * k, cy + 50 * k), (cx - 64 * k, cy + 34 * k)], (236, 196, 160, 255), line=2.5)
    for i in range(4):
        x = cx - 50 * k + i * 26 * k
        s.line([(x, cy + 12 * k), (x + 8 * k, cy + 30 * k)], w=1.6)
    # 愛心（暖珊瑚色，不是飽和紅）
    hx, hy, r = cx, cy - 28 * k, 26 * k
    s.ellipse(hx - 2 * r + 4 * k, hy - r, hx + 4 * k, hy + r * 0.9, (226, 128, 110, 255), line=0)
    s.ellipse(hx - 4 * k, hy - r, hx + 2 * r - 4 * k, hy + r * 0.9, (226, 128, 110, 255), line=0)
    s.poly([(hx - 2 * r + 6 * k, hy + 6 * k), (hx + 2 * r - 6 * k, hy + 6 * k), (hx, hy + 2.1 * r)], (226, 128, 110, 255), line=0)


def tent():
    PPU = 220
    W, H = int(4.6 * PPU), int(3.9 * PPU)
    s = P.Sheet(W, H)
    top, val = int(0.25 * PPU), int(0.95 * PPU)
    # 柱子
    for x in (int(0.35 * PPU), W - int(0.35 * PPU)):
        s.rect(x - 10, val, x + 10, H - 6, (200, 196, 186, 255), line=2)
    # 桌子（白色桌布）
    tx0, tx1, ty = int(0.7 * PPU), W - int(0.7 * PPU), int(2.55 * PPU)
    s.rect(tx0, ty, tx1, H - 10, CREAM, line=2.2)
    s.rect(tx0, ty, tx1, ty + 26, (232, 222, 200, 255), line=2)
    for i in range(1, 6):
        x = tx0 + (tx1 - tx0) * i / 6
        s.line([(x, ty + 30), (x + 6, H - 14)], w=1.2, color=(200, 188, 166, 255))
    # 桌上：水杯一排、籃子（毛巾）、紙箱
    for i in range(5):
        x = tx0 + 60 + i * 46
        s.poly([(x, ty), (x + 30, ty), (x + 26, ty - 46), (x + 4, ty - 46)], (236, 240, 238, 255), line=1.8)
    bx = tx1 - 300
    s.poly([(bx, ty), (bx + 170, ty), (bx + 186, ty - 80), (bx - 16, ty - 80)], (214, 176, 120, 255), line=2)
    for i in range(1, 5):
        s.line([(bx - 12 + i * 40, ty - 76), (bx + i * 38, ty - 4)], w=1.2, color=(170, 132, 88, 255))
    s.ellipse(bx + 10, ty - 108, bx + 90, ty - 70, (196, 216, 224, 255), line=1.8)
    s.ellipse(bx + 70, ty - 112, bx + 160, ty - 72, (240, 226, 196, 255), line=1.8)
    # 篷頂（三角屋頂＋扇形垂邊）
    s.poly([(0, val), (W // 2, top), (W, val)], SAGE, line=2.5)
    s.poly([(W * 0.18, val), (W // 2, top), (W * 0.36, val)], SAGE2, line=0)
    s.poly([(W * 0.64, val), (W // 2, top), (W * 0.82, val)], SAGE2, line=0)
    s.line([(W * 0.18, val), (W // 2, top), (W * 0.82, val)], w=1.6)
    s.line([(W * 0.36, val), (W // 2, top), (W * 0.64, val)], w=1.6)
    vh = int(0.36 * PPU)
    s.rect(0, val, W, val + vh, CREAM, line=2.2)
    n = 9
    for i in range(n):
        x0, x1 = W * i / n, W * (i + 1) / n
        s.d.pieslice([x0 * 2, (val + vh - 30) * 2, x1 * 2, (val + vh + 30) * 2], 0, 180, fill=CREAM)
        s.d.arc([x0 * 2, (val + vh - 30) * 2, x1 * 2, (val + vh + 30) * 2], 0, 180, fill=INK, width=4)
    # 垂邊中央：手捧愛心圖示（白底圓牌）
    cx, cy = W // 2, val + vh // 2 + 6
    s.ellipse(cx - 74, cy - 70, cx + 74, cy + 70, (252, 248, 240, 255), line=2.2)
    heart_hand(s, cx, cy + 10, 0.78)
    return s.finish(white_border=0)


def crate():
    PPU = 220
    W, H = int(1.0 * PPU), int(0.8 * PPU)
    s = P.Sheet(W, H)
    s.rect(4, 20, W - 4, H - 4, (204, 168, 118, 255), line=2.2)
    s.poly([(4, 20), (W - 4, 20), (W - 24, 4), (24, 4)], (220, 186, 136, 255), line=2)
    s.line([(W / 2, 22), (W / 2, H - 6)], w=1.4, color=(160, 124, 84, 255))
    return s.finish(white_border=0)


# ------------------------------------------------------------------ 店外傍晚（a2_c013）
def sky():
    W, H = 1600, 760
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([150, 136, 178], np.float32)      # 淡紫
    mid = np.array([214, 172, 186], np.float32)      # 粉紫
    low = np.array([244, 200, 160], np.float32)      # 暖杏
    c = np.where(y < 0.55, top + (mid - top) * (y / 0.55), mid + (low - mid) * ((y - 0.55) / 0.45))
    a = np.zeros((H, W, 4), np.float32)
    a[..., :3] = c[:, None, :] if c.ndim == 2 else c
    a[..., :3] = np.broadcast_to(c[:, None, :] if c.ndim == 2 else c, (H, W, 3))
    # 幾片剪紙雲（淡）
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    rng = random.Random(4)
    for _ in range(6):
        cx, cy, r = rng.uniform(0, W), rng.uniform(80, 360), rng.uniform(50, 90)
        col = (232, 206, 214, 255)
        for k in range(4):
            d.ellipse([cx + k * r * 0.8 - r, cy - r * (0.6 + 0.2 * (k % 2)), cx + k * r * 0.8 + r, cy + r * 0.5], fill=col)
    a = np.array(img).astype(np.float32)
    a[..., 3] = 255
    return tex_mul(a)


FWOOD = (150, 104, 72, 255)
FWOOD2 = (128, 88, 62, 255)
FPLASTER = (226, 206, 176, 255)
TILE = (120, 96, 92, 255)


def facade():
    """燈籠店店面（夜色前）：左邊大窗（挖空）、右邊木門、上方屋簷與一排紙燈籠。座標以 PPU 200 計，寬 12、 高 6.2。"""
    PPU = 200
    W, H = 12 * PPU, int(6.2 * PPU)
    s = P.Sheet(W, H)
    # 牆面（灰泥）＋木柱
    s.rect(0, int(1.0 * PPU), W, H, FPLASTER, line=0)
    for x in (0.0, 5.55, 11.4):
        s.rect(int(x * PPU), int(1.0 * PPU), int((x + 0.6) * PPU), H, FWOOD, line=2)
    # 屋簷（瓦）
    s.poly([(0, int(1.05 * PPU)), (W, int(1.05 * PPU)), (W, int(0.55 * PPU)), (0, int(0.55 * PPU))], TILE, line=2.5)
    for i in range(0, W, 46):
        s.line([(i, int(0.58 * PPU)), (i + 10, int(1.02 * PPU))], w=1.4, color=(92, 72, 70, 255))
    s.rect(0, int(1.0 * PPU), W, int(1.18 * PPU), FWOOD2, line=2)
    # 窗（左）：x 1.0–5.0、y 2.2–4.9（從上量；地面在 H）
    wx0, wx1 = int(1.0 * PPU), int(5.0 * PPU)
    wy0, wy1 = H - int(4.0 * PPU), H - int(1.05 * PPU)
    s.rect(wx0 - 34, wy0 - 34, wx1 + 34, wy1 + 50, FWOOD, line=2.5)
    s.rect(wx0 - 60, wy1 + 34, wx1 + 60, wy1 + 70, FWOOD2, line=2.2)   # 窗台
    # 門（右）：x 7.0–9.2
    dx0, dx1 = int(7.0 * PPU), int(9.2 * PPU)
    dy0 = H - int(3.6 * PPU)
    s.rect(dx0 - 30, dy0 - 30, dx1 + 30, H, FWOOD, line=2.5)
    s.rect(dx0, dy0, dx1, H, (176, 128, 88, 255), line=2)
    s.rect((dx0 + dx1) // 2 - 3, dy0, (dx0 + dx1) // 2 + 3, H, FWOOD2, line=0)
    for k in (0.18, 0.55):
        s.rect(dx0 + 26, dy0 + int(k * 3.6 * PPU), (dx0 + dx1) // 2 - 26, dy0 + int((k + 0.3) * 3.6 * PPU), (160, 114, 78, 255), line=1.6)
        s.rect((dx0 + dx1) // 2 + 26, dy0 + int(k * 3.6 * PPU), dx1 - 26, dy0 + int((k + 0.3) * 3.6 * PPU), (160, 114, 78, 255), line=1.6)
    s.ellipse((dx0 + dx1) // 2 - 40, dy0 + int(1.8 * PPU), (dx0 + dx1) // 2 - 20, dy0 + int(1.8 * PPU) + 20, (210, 180, 110, 255), line=1.5)
    # 門口石階
    s.rect(dx0 - 80, H - 34, dx1 + 80, H, (190, 180, 168, 255), line=2)
    # 屋簷下一排紙燈籠（沒點亮，暖米白；不發光）
    for i, x in enumerate(np.linspace(0.7, 11.3, 9)):
        cx, cy = x * PPU, int(1.55 * PPU)
        s.line([(cx, int(1.18 * PPU)), (cx, cy - 46)], w=2)
        col = (246, 226, 190, 255) if i % 2 == 0 else (240, 206, 170, 255)
        s.ellipse(cx - 40, cy - 48, cx + 40, cy + 48, col, line=2.2)
        for k in (-20, 0, 20):
            s.d.arc([(cx - abs(k) - 6) * 2, (cy - 48) * 2, (cx + abs(k) + 6) * 2, (cy + 48) * 2], 90, 270, fill=(200, 170, 130, 255), width=2)
        s.rect(cx - 16, cy - 56, cx + 16, cy - 46, FWOOD2, line=1.5)
        s.rect(cx - 16, cy + 46, cx + 16, cy + 56, FWOOD2, line=1.5)
    # 牆角盆栽（右）
    s.poly([(10.0 * PPU, H - 6), (10.8 * PPU, H - 6), (10.9 * PPU, H - 0.6 * PPU), (9.9 * PPU, H - 0.6 * PPU)], (190, 120, 90, 255), line=2)
    for k in range(7):
        a0 = -2.6 + k * 0.32
        cx, cy = 10.4 * PPU, H - 0.6 * PPU
        s.poly([(cx, cy), (cx + math.cos(a0 - 0.15) * 160, cy + math.sin(a0 - 0.15) * 160), (cx + math.cos(a0) * 240, cy + math.sin(a0) * 240),
                (cx + math.cos(a0 + 0.15) * 160, cy + math.sin(a0 + 0.15) * 160)], (112, 146, 98, 255), line=1.6)
    s.hole(wx0, wy0, wx1, wy1)
    return s.finish()


def interior():
    """店內暖牆（窗裡看到的背景）：暖黃牆、木架上幾盞燈籠。"""
    PPU = 160
    W, H = int(7.5 * PPU), int(5.0 * PPU)
    s = P.Sheet(W, H)
    s.rect(0, 0, W, H, (244, 214, 160, 255), line=0)
    for x in (0.4, 3.6, 6.8):
        s.rect(int(x * PPU), 0, int((x + 0.22) * PPU), H, (214, 170, 112, 255), line=1.5)
    sy = int(1.3 * PPU)
    s.rect(0, sy, W, sy + 18, (186, 136, 90, 255), line=1.8)
    for i, x in enumerate(np.linspace(0.8, 6.8, 6)):
        cx = x * PPU
        col = [(240, 200, 150, 255), (220, 232, 210, 255), (244, 222, 190, 255)][i % 3]
        s.ellipse(cx - 46, sy - 96, cx + 46, sy - 4, col, line=2)
    s.rect(0, H - int(0.25 * PPU), W, H, (200, 160, 112, 255), line=1.5)
    return s.finish()


def stool():
    PPU = 220
    W, H = int(0.9 * PPU), int(0.98 * PPU)
    s = P.Sheet(W, H)
    s.ellipse(W * 0.04, 2, W * 0.96, H * 0.13, (160, 116, 80, 255), line=2)
    for x in (0.12, 0.79):
        s.rect(W * x, H * 0.08, W * (x + 0.09), H - 2, (138, 97, 64, 255), line=1.6)
    s.rect(W * 0.45, H * 0.1, W * 0.55, H - 2, (138, 97, 64, 255), line=1.6)
    s.rect(W * 0.12, H * 0.62, W * 0.88, H * 0.67, (138, 97, 64, 255), line=1.4)
    return s.finish()


def glass():
    W, H = 64, 64
    a = np.zeros((H, W, 4), np.uint8)
    a[..., :3] = (255, 236, 200)
    a[..., 3] = 255
    return a


# 剪影小窗（a2_c013）：背光的米杏色紙框（中間亮、四周暗），剪影另外兩張
SIL = (58, 44, 40)


def sil_frame():
    W, H = 1000, 720
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W * 0.5) / (W * 0.5), (yy - H * 0.45) / (H * 0.55))
    inner = np.array([252, 238, 214], np.float32)
    outer = np.array([226, 190, 160], np.float32)
    k = np.clip(r, 0, 1)[..., None] ** 1.6
    a = np.zeros((H, W, 4), np.float32)
    a[..., :3] = inner * (1 - k) + outer * k
    # 褪色紙框
    pad = 40
    frame = np.ones((H, W), bool)
    frame[pad:H - pad, pad:W - pad] = False
    a[frame, :3] = np.array([232, 220, 200], np.float32)
    a[..., 3] = deckle_mask(W, H, 6, 31, amp=4.0)
    img = Image.fromarray(np.clip(tex_mul(a), 0, 255).astype(np.uint8), "RGBA")
    ImageDraw.Draw(img).rectangle([pad - 3, pad - 3, W - pad + 2, H - pad + 2], outline=(150, 128, 104, 255), width=3)
    return np.array(img)


def silhouette_of(rgba, color=SIL):
    a = np.array(rgba).astype(np.float32)
    out = np.zeros_like(a)
    out[..., :3] = color
    out[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    return out.astype(np.uint8)


def sil_hand_box():
    im = Image.open(FINAL / "chr-inviter_hand-box_v01.png").convert("RGBA")
    return silhouette_of(im)


def sil_ale_hand():
    """阿樂叔叔的前臂＋手（分件圖合成），往左上伸出，剪影。"""
    fa = Image.open(FINAL / "rig/chr-ale_forearm-l_v05.png").convert("RGBA")
    hd = Image.open(FINAL / "rig/chr-ale_hand-l_v04.png").convert("RGBA")
    W, H = 420, 520
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.alpha_composite(fa, (140, 160))
    c.alpha_composite(hd, (150, 160 + fa.height - 60))
    c = c.rotate(215, resample=Image.BICUBIC, expand=True)   # 先倒過來（手在上、袖口在下），再往左上斜
    c = c.crop(c.getbbox())
    return silhouette_of(c)


def notebook():
    """小晴的筆記本（a2_c013 特寫）：兩頁米白紙、左頁竹骨架速寫、右頁一個大問號（第二個問號由程式畫上）。無文字。"""
    W, H = 1500, 960
    s = P.Sheet(W, H)
    s.rect(10, 10, W - 10, H - 10, (190, 120, 92, 255), line=2.5, r=24)            # 封面邊
    s.rect(40, 30, W // 2 - 4, H - 40, (250, 246, 236, 255), line=1.8)
    s.rect(W // 2 + 4, 30, W - 40, H - 40, (250, 246, 236, 255), line=1.8)
    s.rect(W // 2 - 6, 24, W // 2 + 6, H - 34, (170, 104, 80, 255), line=1.4)
    for y in range(120, H - 60, 64):                                                 # 淡格線（無字）
        s.line([(80, y), (W // 2 - 40, y)], w=1.2, color=(214, 222, 230, 255))
        s.line([(W // 2 + 40, y), (W - 80, y)], w=1.2, color=(214, 222, 230, 255))
    pencil = (92, 86, 96, 255)
    # 左頁：燈籠竹骨架速寫
    cx, cy, rx, ry = W * 0.25, H * 0.48, 170, 230
    for k in (-1, -0.5, 0, 0.5, 1):
        s.d.arc([(cx - rx * abs(k) - 8) * 2, (cy - ry) * 2, (cx + rx * abs(k) + 8) * 2, (cy + ry) * 2],
                90 if k <= 0 else 270, 270 if k <= 0 else 90, fill=pencil, width=7)
    s.d.ellipse([(cx - rx) * 2, (cy - 34) * 2, (cx + rx) * 2, (cy + 34) * 2], outline=pencil, width=6)
    s.line([(cx - 60, cy - ry), (cx + 60, cy - ry)], w=4, color=pencil)
    s.line([(cx - 60, cy + ry), (cx + 60, cy + ry)], w=4, color=pencil)
    # 右頁：第一個問號（鉛筆線）
    qmark(s, W * 0.64, H * 0.46, 1.0, pencil)
    return s.finish()


def qmark_path(cx, cy, k):
    pts = []
    for i in range(0, 41):
        a = math.pi * 1.05 - i / 40 * math.pi * 1.45
        pts.append((cx + math.cos(a) * 95 * k, cy - 120 * k - math.sin(a) * 95 * k))
    last = pts[-1]
    pts += [(last[0] - 10 * k, last[1] + 40 * k), (cx, cy + 40 * k), (cx, cy + 70 * k)]
    return pts


def qmark(s, cx, cy, k, col):
    s.line(qmark_path(cx, cy, k), w=13 * k, color=col)
    s.ellipse(cx - 13 * k, cy + 120 * k, cx + 13 * k, cy + 146 * k, col, line=0)


def main():
    jobs = [
        ("a2_memory", "mem-box", mem_box), ("a2_memory", "mem-wrapper", mem_wrapper),
        ("a2_helpdesk", "tent", tent), ("a2_helpdesk", "crate", crate),
        ("a2_window", "sky", sky), ("a2_window", "facade", facade), ("a2_window", "interior", interior),
        ("a2_window", "stool", stool), ("a2_window", "glass", glass), ("a2_window", "sil-frame", sil_frame),
        ("a2_window", "sil-hand-box", sil_hand_box), ("a2_window", "sil-ale-hand", sil_ale_hand), ("a2_window", "notebook", notebook),
    ]
    only = set(sys.argv[1:])
    for setname, name, fn in jobs:
        if only and name not in only:
            continue
        a = fn()
        p = P.save(np.asarray(a).astype(np.uint8), out(setname, name))
        print(p.relative_to(ROOT), a.shape[1], a.shape[0])


if __name__ == "__main__":
    main()
