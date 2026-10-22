"""第四幕修正第 1 輪的素材（G5 第一批驗收第 1 輪：review/G5/qa/b1_*.md 第四幕一般問題）。

只產生這一輪要換的圖，v01 一律不動（build_a4_art.py 不重跑）：
  assets/final/sets/gate/set-gate_a4-truck_v01.png        小貨車第四幕版：舊的單一米色三角形拿掉，改成帆布下露出的竹編貓頭骨架
                                                         （兩隻尖耳＋一小段頭框，輪廓同 a0 主燈設計圖：十二邊形貓頭、兩耳往外斜）。
                                                         和 props/prop-truck_v01.png 同尺寸、同位置，gate.ts 的 setTrack {do:"catEar"} 打開時換貼圖。
  assets/final/sets/gate/set-gate_a4-walkers-{a,b}_v02.png 遠景家長牽孩子離開：改成淺紙色、不透明的分件小紙人（背影，看不到臉；有髮型與衣色）
  assets/final/sets/a4_roadmap/set-a4map_sil-car_v02.png    背光剪影：手剪紙輪廓（剪刀直線折角＋紙纖維毛邊；駕駛、乘客有頭髮剪邊）
  assets/final/sets/a4_roadmap/set-a4map_sil-walker_v02.png 背光剪影：背書包的路人（書包帶剪縫、衣服皺褶缺口、頭髮鋸齒）
圖裡沒有文字、數字、品牌、標誌。
用法：/opt/anaconda3/bin/python3 review/G5/a4/scripts/build_a4_art_fix1.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

GATE = ROOT / "assets/final/sets/gate"
MAP_DIR = ROOT / "assets/final/sets/a4_roadmap"
BORDER_RGB = np.array([250, 246, 238], np.float32)
LINE_DARK = np.array([70, 56, 46], np.float32)

# 竹色（比車身 L*≈90 深 ΔL* ≥ 25：底 L*≈42、亮篾 L*≈55、篾邊 L*≈27）
BAMBOO = (132, 92, 50, 255)
BAMBOO_L = (170, 124, 70, 255)
BAMBOO_D = (84, 56, 32, 255)


# ============================================================ 共用
def lab_L(rgb):
    c = np.asarray(rgb, np.float64)[..., :3] / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    y = c @ np.array([0.2126, 0.7152, 0.0722])
    f = np.where(y > 216 / 24389, np.cbrt(y), (24389 / 27 * y + 16) / 116)
    return 116 * f - 16


def add_border(rgba, width, inner_line=True):
    """同 paperdraw.finish 的白邊（不改尺寸）：外圍 width px 米白紙邊、內側一圈深色細線。"""
    a = rgba.astype(np.float32)
    m = a[..., 3] >= 128
    dist = ndimage.distance_transform_edt(~m)
    ring = (dist > 0) & (dist <= width + 1.2)
    tex = P.paper_tex(a.shape[1], a.shape[0])
    wc = BORDER_RGB[None, None] * tex[..., None]
    a[ring, :3] = wc[ring]
    aa = np.clip(width + 1.2 - dist, 0, 1)
    a[..., 3] = np.where(m, a[..., 3], np.maximum(a[..., 3] * 0, aa * 255 * ring))
    if inner_line:
        dl = ndimage.distance_transform_edt(m)
        line = m & (dl <= 2.0)
        a[line, :3] = a[line, :3] * 0.3 + LINE_DARK * 0.7
    return np.clip(a, 0, 255).astype(np.uint8)


def jitter_poly(pts, seg, amp, rng, closed=True):
    """把多邊形重新取樣成約 seg px 一段、每個頂點垂直方向亂移 ±amp：剪刀剪出的直線折角。"""
    out = []
    n = len(pts)
    rng_n = n if closed else n - 1
    for i in range(rng_n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        k = max(1, int(L / seg))
        nx, ny = (-(y1 - y0) / (L or 1), (x1 - x0) / (L or 1))
        for j in range(k):
            u = j / k
            off = (rng.random() - 0.5) * 2 * amp if j > 0 else 0
            out.append((x0 + (x1 - x0) * u + nx * off, y0 + (y1 - y0) * u + ny * off))
    if not closed:
        out.append(pts[-1])
    return out


def ellipse_pts(cx, cy, rx, ry, n=28, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * k / n), cy + ry * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


# ============================================================ 1. 小貨車第四幕版（竹編貓頭骨架）
TRUCK_SRC = ROOT / "assets/final/props/prop-truck_v01.png"
TARP = np.array([153, 146, 98])
HEAD_C = (812.0, 410.0)      # 貓頭中心（車圖 px；在帆布下面）
HEAD_R = 132.0
# 耳朵（以頭半徑為單位、相對頭中心；量自 assets/final/sets/workshop_a0/design_v01.png：尖端 ±0.76R、−1.5R，外底 ±0.9R、−0.78R，內底 ±0.33R、−0.86R）
EAR = [(0.76, -1.50), (0.90, -0.78), (0.33, -0.86)]


def tarp_top(im):
    """每一欄帆布上緣（第一個帆布色像素）；三角形底下看不到的那段用左邊的斜率延伸。"""
    H, W = im.shape[:2]
    top = np.full(W, -1, int)
    d = np.abs(im[..., :3].astype(int) - TARP).sum(2)
    ok = (d < 45) & (im[..., 3] > 200)
    for x in range(W):
        ys = np.where(ok[250:420, x])[0]
        if len(ys):
            top[x] = 250 + ys[0]
    # 560–940 量得幾乎是直線：y ≈ 298 + 0.132 (x − 560)
    for x in range(940, 1016):
        top[x] = int(round(298 + 0.132 * (x - 560)))
    return top


def truck_catear(tip_only=False):
    src = np.array(Image.open(TRUCK_SRC).convert("RGBA"))
    H, W = src.shape[:2]
    out = src.copy()
    top = tarp_top(src)
    # ---- (a) 拿掉舊的單一三角形（含它和車頭之間的白邊）：x 925–1026、帆布上緣以上全部清成透明，再從剩下的形狀重做白邊
    yy, xx = np.mgrid[0:H, 0:W]
    topx = top.copy()
    for x in range(1013, W):
        topx[x] = int(round(298 + 0.132 * (x - 560)))
    above = yy < topx[None, :].clip(0)
    kill = above & (xx >= 925) & (xx < 1027) & (yy > 150)
    out[kill, 3] = 0
    # 帆布上緣那段補回深色輪廓線（3 px）
    for x in range(925, 1016):
        y = topx[x]
        out[y - 3:y, x, :3] = (70, 56, 46)
        out[y - 3:y, x, 3] = 255
    core = out[..., 3] >= 128
    dist = ndimage.distance_transform_edt(~core)
    ring = (dist > 0) & (dist <= 13.2) & (xx >= 915) & (xx < 1040) & (yy < topx[None, :] + 3) & (yy > 150)
    tex = P.paper_tex(W, H)
    wc = BORDER_RGB[None, None] * tex[..., None]
    o = out.astype(np.float32)
    o[ring, :3] = wc[ring]
    o[ring, 3] = np.clip(13.2 - dist[ring], 0, 1) * 255
    out = np.clip(o, 0, 255).astype(np.uint8)

    # ---- (b) 竹編貓頭骨架（畫在一張同尺寸的圖層上，再只留帆布上緣以上的部分）
    ss = 3
    lay = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy, R = HEAD_C[0], HEAD_C[1], HEAD_R

    def S(p):
        return [(x * ss, y * ss) for x, y in p]

    # 十二邊形頭框（平頂）
    def gon(r):
        return [(cx + r * math.cos(math.radians(-90 + 15 + 30 * k)), cy + r * math.sin(math.radians(-90 + 15 + 30 * k))) for k in range(12)]

    ears = []
    for side in (-1, 1):
        ears.append([(cx + side * ex * R, cy + ey * R) for ex, ey in EAR])
    # 耳朵：竹編（底色＋兩個方向交錯的亮篾），外框深色竹篾
    ear_mask = Image.new("L", lay.size, 0)
    dm = ImageDraw.Draw(ear_mask)
    for e in ears:
        dm.polygon(S(e), fill=255)
    weave = Image.new("RGBA", lay.size, BAMBOO)
    dw = ImageDraw.Draw(weave)
    step = 15 * ss
    wid = 7 * ss
    x0, x1 = int((cx - 1.2 * R) * ss), int((cx + 1.2 * R) * ss)
    y0, y1 = int((cy - 1.7 * R) * ss), int((cy - 0.5 * R) * ss)
    for k, x in enumerate(range(x0 - (y1 - y0), x1, step)):          # 斜篾（／）
        for j, y in enumerate(range(y0, y1, step)):
            if (k + j) % 2 == 0:
                dw.polygon([(x + (y - y0), y), (x + (y - y0) + wid, y), (x + (y - y0) + wid + step, y + step), (x + (y - y0) + step, y + step)], fill=BAMBOO_L)
    for k, x in enumerate(range(x0, x1 + (y1 - y0), step)):          # 斜篾（＼）的縫
        dw.line([(x, y0), (x - (y1 - y0), y1)], fill=BAMBOO_D, width=int(1.6 * ss))
    lay.paste(weave, (0, 0), ear_mask)
    for e in ears:                                                    # 耳框：粗竹篾（深）
        p = S(e)
        d.line(p + [p[0]], fill=BAMBOO_D, width=int(7 * ss), joint="curve")
        d.line(p + [p[0]], fill=BAMBOO, width=int(3 * ss), joint="curve")
        # 耳朵中線一根篾（和設計圖一樣）
        tip, ob, ib = e
        mid = ((ob[0] + ib[0]) / 2, (ob[1] + ib[1]) / 2)
        d.line(S([tip, mid]), fill=BAMBOO_D, width=int(3 * ss))
    # 頭框：外圈、內圈、輻條（竹篾條，內部透空＝骨架）
    for r, w_out, w_in in ((R, 14, 7), (0.74 * R, 9, 4)):
        p = S(gon(r))
        d.line(p + [p[0]], fill=BAMBOO_D, width=int(w_out * ss), joint="curve")
        d.line(p + [p[0]], fill=BAMBOO_L, width=int(w_in * ss), joint="curve")
    for k in range(12):
        a = math.radians(-90 + 15 + 30 * k)
        p = S([(cx + 0.74 * R * math.cos(a), cy + 0.74 * R * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a))])
        d.line(p, fill=BAMBOO_D, width=int(6 * ss))
        d.line(p, fill=BAMBOO_L, width=int(2.4 * ss))
    lay = np.array(lay.resize((W, H), Image.LANCZOS)).astype(np.float32)
    lay[..., :3] *= P.paper_tex(W, H)[..., None]
    lay = np.clip(lay, 0, 255).astype(np.uint8)
    lay = add_border(lay, 7, inner_line=False)
    # 只留帆布上緣以上（骨架在帆布下面，露出來的是兩耳＋一小段頭框）；x > 1010 是帆布右端外，不畫
    vis = (yy < (top[None, :] + 1)) & (xx < 1010) & (top[None, :] > 0)
    lay[~vis, 3] = 0
    # 疊在車圖上
    a_l = lay[..., 3:4].astype(np.float32) / 255
    res = out.astype(np.float32)
    res[..., :3] = res[..., :3] * (1 - a_l) + lay[..., :3] * a_l
    res[..., 3] = np.maximum(res[..., 3], lay[..., 3])
    res = np.clip(res, 0, 255).astype(np.uint8)
    if tip_only:
        # a4_c001、a4_c008（風吹之前）：帆布蓋在骨架上鼓成一團，只有左耳尖從帆布邊露出一小角（劇本：只露一小角、不推近、不打光）
        hump = [(684, int(top[684]) + 4), (700, 268), (722, 258), (752, 250), (800, 232), (860, 210), (915, 196), (958, 198), (990, 226),
                (1008, 286), (1011, int(topx[1011]) + 4)]
        hm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(hm).polygon(hump, fill=255)
        hm = np.array(hm) > 0
        o = res.astype(np.float32)
        tarp_rgb = np.array([153, 146, 98], np.float32)[None, None] * P.paper_tex(W, H)[..., None]
        o[hm, :3] = tarp_rgb[hm]
        o[hm, 3] = 255
        din = ndimage.distance_transform_edt(hm)
        edge = hm & (din <= 3.0) & (yy < topx[None, :] - 8)
        o[edge, :3] = (70, 56, 46)
        # 帆布繩（同原圖的深色斜線）
        res = np.clip(o, 0, 255).astype(np.uint8)
        im2 = Image.fromarray(res, "RGBA")
        dd = ImageDraw.Draw(im2)
        dd.line([(760, 250), (930, 330)], fill=(92, 80, 62, 255), width=3)
        dd.line([(930, 205), (800, 330)], fill=(92, 80, 62, 255), width=3)
        res = np.array(im2)
        # 鼓起的帆布外圍補白邊（13 px，同車圖）
        o = res.astype(np.float32)
        core = res[..., 3] >= 128
        dist = ndimage.distance_transform_edt(~core)
        ring = (dist > 0) & (dist <= 13.2) & (xx >= 670) & (xx < 1030) & (yy < topx[None, :] + 3)
        wc = BORDER_RGB[None, None] * P.paper_tex(W, H)[..., None]
        o[ring, :3] = wc[ring]
        o[ring, 3] = np.clip(13.2 - dist[ring], 0, 1) * 255
        res = np.clip(o, 0, 255).astype(np.uint8)
        # 鼓起的帆布底邊和原本帆布上緣之間零星的亮點（白邊殘留）改成帆布色
        band = ndimage.binary_dilation(hm, iterations=2) & (yy >= topx[None, :] - 10) & (yy <= topx[None, :] + 8) & (xx < 1012)
        light = band & (res[..., :3].astype(int).sum(2) > 480)
        res[light, :3] = (153, 146, 98)
        res[light, 3] = 255
        vis = vis & ~hm
    # 量測：露出的骨架外框（車圖 px）、竹色與車身的 L*
    vm = (lay[..., 3] > 128) & vis & (res[..., 3] > 128) & (np.abs(res[..., :3].astype(int) - np.array([153, 146, 98])).sum(2) > 40)
    ys, xs = np.where(vm)
    body = src[600:640, 200:300, :3].reshape(-1, 3).mean(0)
    earpx = res[vm & (np.abs(res[..., :3].astype(int) - np.array(BORDER_RGB, int)).sum(2) > 60)][:, :3].reshape(-1, 3)
    meta = {
        "visible_box_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        "visible_center_world_from_bottom_center": [round(((xs.min() + xs.max()) / 2 - W / 2) * 6.0 / W, 3), round((H - (ys.min() + ys.max()) / 2) * 6.0 / W, 3)],
        "visible_height_world": round((ys.max() - ys.min()) * 6.0 / W, 3),
        "body_L": round(float(lab_L(body)), 1), "bamboo_L_mean": round(float(lab_L(earpx).mean()), 1),
    }
    meta["dL"] = round(meta["body_L"] - meta["bamboo_L_mean"], 1)
    return res, meta


# ============================================================ 2. 遠景家長牽孩子（淺紙色分件小紙人，背影）
def walkers(kind):
    w, h = 1.5, 2.8
    PPW = 150
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    if kind == "a":
        hairA, topA, pantA, bag = (128, 102, 82, 255), (200, 210, 214, 255), (184, 176, 158, 255), (222, 204, 168, 255)
        hairK, topK, pantK, pack = (116, 90, 70, 255), (232, 208, 160, 255), (188, 194, 176, 255), (206, 182, 144, 255)
    else:
        hairA, topA, pantA, bag = (110, 92, 78, 255), (214, 200, 176, 255), (170, 176, 170, 255), None
        hairK, topK, pantK, pack = (124, 98, 74, 255), (196, 214, 196, 255), (200, 188, 166, 255), (226, 196, 150, 255)
    skin = (236, 206, 178, 255)
    shoe = (150, 132, 116, 255)
    g = H - 6
    # 大人（左；背影）
    ax = W * 0.36
    hip = H * 0.6
    s.rect(ax - 16, hip - 6, ax - 1, g - 12, pantA, line=1.4, r=5)          # 腿
    s.rect(ax + 1, hip - 6, ax + 16, g - 12, pantA, line=1.4, r=5)
    s.ellipse(ax - 19, g - 18, ax - 1, g - 4, shoe, line=1.2)
    s.ellipse(ax + 1, g - 18, ax + 19, g - 4, shoe, line=1.2)
    s.poly([(ax - 30, 80), (ax + 30, 80), (ax + 37, hip + 6), (ax - 37, hip + 6)], topA, line=1.6)   # 外套（下襬微張）
    s.line([(ax, 92), (ax, hip + 2)], 1.4, tuple(int(c * 0.85) for c in topA[:3]) + (255,))
    s.poly([(ax - 30, 82), (ax - 44, 96), (ax - 48, H * 0.47), (ax - 36, H * 0.48), (ax - 32, 110)], topA, line=1.4)   # 左袖
    if bag:
        s.rect(ax - 60, H * 0.42, ax - 36, H * 0.55, bag, line=1.4, r=4)   # 提袋
        s.line([(ax - 54, H * 0.42), (ax - 44, H * 0.47)], 1.6, (150, 122, 92, 255))
    s.line([(ax + 28, 88), (ax + 54, H * 0.45)], 13, topA)                  # 牽手的手臂
    s.rect(ax - 8, 58, ax + 8, 82, skin, line=1.2)                          # 脖子
    s.poly([(ax - 25, 66), (ax - 27, 34), (ax - 16, 14), (ax, 9), (ax + 16, 14), (ax + 27, 34), (ax + 25, 66), (ax + 8, 70), (ax - 8, 70)], hairA, line=1.6)   # 後腦（短鮑伯頭）
    # 小孩（右；背影、背小書包）
    cxk = W * 0.72
    top = H * 0.42
    khip = H * 0.8
    s.rect(cxk - 12, khip - 4, cxk - 1, g - 9, pantK, line=1.2, r=4)
    s.rect(cxk + 1, khip - 4, cxk + 12, g - 9, pantK, line=1.2, r=4)
    s.ellipse(cxk - 14, g - 14, cxk - 1, g - 3, shoe, line=1.0)
    s.ellipse(cxk + 1, g - 14, cxk + 14, g - 3, shoe, line=1.0)
    s.poly([(cxk - 21, top + 40), (cxk + 21, top + 40), (cxk + 25, khip + 2), (cxk - 25, khip + 2)], topK, line=1.4)
    s.rect(cxk - 19, top + 48, cxk + 19, top + 98, pack, line=1.4, r=8)     # 書包（背面）
    s.line([(cxk - 19, top + 64), (cxk + 19, top + 64)], 1.6, (150, 122, 92, 255))
    s.line([(cxk - 21, top + 50), (ax + 56, H * 0.47)], 10, topK)            # 牽手
    s.rect(cxk - 6, top + 28, cxk + 6, top + 42, skin, line=1.0)
    s.ellipse(cxk - 17, top, cxk + 17, top + 36, hairK, line=1.4)            # 後腦
    if kind == "a":
        s.ellipse(cxk + 10, top + 4, cxk + 24, top + 18, hairK, line=1.2)    # 小馬尾
    return s.finish(white_border=5), (w, h)


# ============================================================ 3. 背光剪影（手剪紙）
SIL = (58, 44, 34, 255)
SCR_PPU = 300


def handcut_finish(mask, seed):
    """mask（L, 超取樣）→ 縮小 → 紙纖維毛邊（邊外 1–2 px 稀疏纖維）＋ 剪影色 RGBA"""
    ss = 3
    m = np.array(mask.resize((mask.width // ss, mask.height // ss), Image.LANCZOS)).astype(np.float32) / 255
    rng = np.random.default_rng(seed)
    out_band = (ndimage.distance_transform_edt(m < 0.5) <= 2.2) & (m < 0.5)
    fib = ndimage.gaussian_filter(rng.random(m.shape), 0.6)
    fib = (fib > 0.56).astype(np.float32) * 0.55
    alpha = np.maximum(m, out_band * fib)
    H, W = m.shape
    a = np.zeros((H, W, 4), np.float32)
    a[..., :3] = np.array(SIL[:3], np.float32)
    # 剪影紙本身也有一點纖維明暗（背光透出的紙紋）
    a[..., :3] *= (1 + (P.paper_tex(W, H) - 1) * 1.5)[..., None]
    a[..., 3] = alpha * 255
    return np.clip(a, 0, 255).astype(np.uint8)


def sil_car():
    """車子剪影（側面、車頭朝右）：前窗裡是駕駛（雙手握方向盤）、後窗裡是乘客；剪刀直線折角＋紙纖維毛邊"""
    w, h = 3.4, 1.62
    W, H = int(w * SCR_PPU), int(h * SCR_PPU)
    ss = 3
    rng = np.random.default_rng(41)
    mask = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(mask)

    def S(p):
        return [(x * ss, y * ss) for x, y in p]

    def cut(p, seg=26, amp=2.2, fill=255):
        d.polygon(S(jitter_poly(p, seg, amp, rng)), fill=fill)

    body = [(26, H - 104), (22, H * 0.5), (60, H * 0.44), (W * 0.2, H * 0.41), (W * 0.31, H * 0.13), (W * 0.665, H * 0.11), (W * 0.795, H * 0.38),
            (W - 44, H * 0.455), (W - 14, H * 0.55), (W - 16, H - 104)]
    cut(body)
    cut([(26, H - 134), (W - 18, H - 134), (W - 18, H - 66), (26, H - 66)])
    for cxw in (W * 0.22, W * 0.78):                                       # 輪子＋輪拱
        cut(ellipse_pts(cxw, H - 100, 98, 98, 30), seg=20, amp=1.8)
    # 窗（挖空，透出背光）
    win_r = [(W * 0.525, H * 0.18), (W * 0.645, H * 0.165), (W * 0.765, H * 0.385), (W * 0.525, H * 0.405)]
    win_f = [(W * 0.345, H * 0.19), (W * 0.495, H * 0.18), (W * 0.495, H * 0.405), (W * 0.245, H * 0.415)]
    cut(win_r, seg=22, amp=1.8, fill=0)
    cut(win_f, seg=22, amp=1.8, fill=0)
    # 駕駛（前窗、靠右；頭髮鋸齒剪邊）、乘客（後窗、小一點；綁馬尾）
    def person(cx, top, sc, pony=False):
        r = 40 * sc
        cut(ellipse_pts(cx, top + r, r * 0.92, r, 22), seg=14, amp=1.6)
        # 頭髮：頂上一排鋸齒
        tips = []
        for k in range(5):
            ang = math.pi + math.pi * (k + 0.5) / 5
            tips += [(cx + r * 1.0 * math.cos(ang - 0.25), top + r + r * 1.0 * math.sin(ang - 0.25)),
                     (cx + r * 1.1 * math.cos(ang), top + r + r * 1.1 * math.sin(ang))]
        cut([(cx - r, top + r)] + tips + [(cx + r, top + r)], seg=40, amp=0.8)
        if pony:
            cut([(cx - r * 0.7, top + r * 0.6), (cx - r * 1.6, top + r * 1.1), (cx - r * 1.35, top + r * 1.9), (cx - r * 0.8, top + r * 1.3)], seg=20, amp=1.2)
        # 脖子、肩膀（衣領缺口）
        sh = top + 2 * r + 4 * sc
        cut([(cx - 12 * sc, top + 1.7 * r), (cx + 12 * sc, top + 1.7 * r), (cx + 14 * sc, sh + 6), (cx - 14 * sc, sh + 6)], seg=20, amp=1)
        cut([(cx - 70 * sc, sh + 96 * sc), (cx - 56 * sc, sh + 10 * sc), (cx - 12 * sc, sh), (cx, sh + 14 * sc), (cx + 12 * sc, sh),
             (cx + 56 * sc, sh + 10 * sc), (cx + 70 * sc, sh + 96 * sc)], seg=22, amp=1.6)
    person(W * 0.645, H * 0.215, 1.0)
    person(W * 0.415, H * 0.27, 0.8, pony=True)
    # 駕駛的手臂伸向方向盤（方向盤＝小圓環，中間剪空；整個在前窗裡）
    cut([(W * 0.655, H * 0.375), (W * 0.683, H * 0.335), (W * 0.693, H * 0.35), (W * 0.668, H * 0.39)], seg=14, amp=0.8)
    cut(ellipse_pts(W * 0.69, H * 0.335, 13, 19, 18), seg=10, amp=0.7)
    cut(ellipse_pts(W * 0.69, H * 0.335, 6, 11, 14), seg=8, amp=0.5, fill=0)
    # 車門縫、門把（剪縫透光）、車燈缺口、輪框細環
    d.line(S([(W * 0.5, H * 0.43), (W * 0.505, H - 140)]), fill=0, width=int(3 * ss))
    d.line(S([(W * 0.285, H * 0.44), (W * 0.27, H - 140)]), fill=0, width=int(3 * ss))
    d.line(S([(W * 0.42, H * 0.5), (W * 0.46, H * 0.5)]), fill=0, width=int(5 * ss))
    d.line(S([(W * 0.6, H * 0.5), (W * 0.64, H * 0.5)]), fill=0, width=int(5 * ss))
    cut([(W - 16, H * 0.55), (W - 52, H * 0.53), (W - 46, H * 0.6), (W - 16, H * 0.61)], seg=12, amp=0.8, fill=0)
    for cxw in (W * 0.22, W * 0.78):
        d.ellipse([(cxw - 52) * ss, (H - 152) * ss, (cxw + 52) * ss, (H - 48) * ss], outline=0, width=int(4 * ss))
    return handcut_finish(mask, 7), (w, h)


def sil_walker():
    """斑馬線上背書包的路人剪影（側面、往右走；書包帶剪縫、衣服皺褶缺口、頭髮剪邊）"""
    w, h = 0.95, 1.95
    W, H = int(w * SCR_PPU), int(h * SCR_PPU)
    ss = 3
    rng = np.random.default_rng(43)
    mask = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(mask)

    def S(p):
        return [(x * ss, y * ss) for x, y in p]

    def cut(p, seg=16, amp=1.6, fill=255):
        d.polygon(S(jitter_poly(p, seg, amp, rng)), fill=fill)

    cx = W * 0.52
    hc, hr = 66, 50
    # 頭（側面，臉朝右）＋鼻尖、下巴
    cut(ellipse_pts(cx, hc, hr * 0.94, hr, 24), seg=14, amp=1.2)
    cut([(cx + hr * 0.86, hc + 4), (cx + hr * 1.04, hc + 16), (cx + hr * 0.84, hc + 22)], seg=8, amp=0.5)
    # 頭髮：後腦蓋一層、額前一撮瀏海（剪刀剪出的三個小尖）
    cut([(cx - hr * 1.02, hc + 18), (cx - hr * 1.06, hc - 18), (cx - hr * 0.7, hc - hr * 0.92), (cx - hr * 0.2, hc - hr * 1.12), (cx + hr * 0.35, hc - hr * 1.1),
         (cx + hr * 0.78, hc - hr * 0.8), (cx + hr * 0.96, hc - hr * 0.42), (cx + hr * 0.74, hc - hr * 0.5), (cx + hr * 0.66, hc - hr * 0.3),
         (cx + hr * 0.5, hc - hr * 0.52), (cx + hr * 0.36, hc - hr * 0.36), (cx + hr * 0.2, hc - hr * 0.6), (cx - hr * 0.4, hc - hr * 0.5), (cx - hr * 0.7, hc + 22)], seg=22, amp=0.8)
    # 脖子
    cut([(cx - 12, hc + hr - 8), (cx + 12, hc + hr - 8), (cx + 14, hc + hr + 18), (cx - 12, hc + hr + 18)], seg=10, amp=0.6)
    # 上衣（短袖；下襬兩個皺褶缺口）
    t0, t1 = hc + hr + 12, 318
    cut([(cx - 42, t0 + 4), (cx + 30, t0), (cx + 40, t0 + 26), (cx + 44, t1 - 6), (cx + 26, t1), (cx + 18, t1 - 14), (cx + 8, t1 + 2), (cx - 8, t1 - 12),
         (cx - 20, t1 + 4), (cx - 44, t1)], seg=18, amp=1.4)
    # 書包（背在後面，左側）
    cut([(cx - 104, t0 + 14), (cx - 38, t0 + 8), (cx - 34, t0 + 150), (cx - 98, t0 + 158)], seg=18, amp=1.8)
    cut([(cx - 106, t0 + 60), (cx - 118, t0 + 64), (cx - 116, t0 + 118), (cx - 102, t0 + 116)], seg=10, amp=1)   # 側袋
    d.line(S([(cx - 38, t0 + 12), (cx + 18, t0 + 6), (cx + 30, t0 + 96)]), fill=0, width=int(3.5 * ss))   # 肩帶剪縫
    d.line(S([(cx - 96, t0 + 112), (cx - 38, t0 + 106)]), fill=0, width=int(3 * ss))                       # 書包蓋縫
    # 手臂（往前擺，手肘微彎；拳頭）
    cut([(cx + 14, t0 + 10), (cx + 38, t0 + 8), (cx + 64, t0 + 96), (cx + 84, t0 + 150), (cx + 66, t0 + 158), (cx + 44, t0 + 104), (cx + 22, t0 + 50)], seg=16, amp=1.2)
    cut(ellipse_pts(cx + 78, t0 + 160, 14, 15, 14), seg=8, amp=0.6)
    # 短褲
    s0 = t1 - 10
    cut([(cx - 42, s0), (cx + 42, s0 - 4), (cx + 52, s0 + 84), (cx + 8, s0 + 92), (cx, s0 + 64), (cx - 12, s0 + 94), (cx - 52, s0 + 86)], seg=16, amp=1.4)
    # 腳（跨步：後腳往左後、前腳往右前；小腿有粗細）
    k0 = s0 + 80
    cut([(cx - 46, k0), (cx - 14, k0 + 4), (cx - 40, H - 60), (cx - 58, H - 52), (cx - 70, H - 62)], seg=18, amp=1.2)
    cut([(cx + 4, k0), (cx + 44, k0 - 2), (cx + 66, H - 66), (cx + 54, H - 50), (cx + 40, H - 58)], seg=18, amp=1.2)
    # 鞋
    cut([(cx - 92, H - 64), (cx - 38, H - 58), (cx - 40, H - 26), (cx - 100, H - 30)], seg=12, amp=1)
    cut([(cx + 34, H - 64), (cx + 72, H - 70), (cx + 104, H - 38), (cx + 46, H - 26)], seg=12, amp=1)
    return handcut_finish(mask, 9), (w, h)


def main():
    meta = {"made_by": "review/G5/a4/scripts/build_a4_art_fix1.py"}
    a, m = truck_catear()
    P.save(a, GATE / "set-gate_a4-truck_v01.png")
    meta["truck_catear"] = m
    a, m = truck_catear(tip_only=True)
    P.save(a, GATE / "set-gate_a4-truck-tip_v01.png")
    meta["truck_catear_tip"] = m
    for k in ("a", "b"):
        a, wh = walkers(k)
        P.save(a, GATE / f"set-gate_a4-walkers-{k}_v02.png")
        meta[f"walkers-{k}"] = wh
    for name, fn in (("sil-car", sil_car), ("sil-walker", sil_walker)):
        a, wh = fn()
        P.save(a, MAP_DIR / f"set-a4map_{name}_v02.png")
        meta[name] = wh
    p = ROOT / "review/G5/a4/art_meta.json"
    old = json.loads(p.read_text(encoding="utf-8"))
    old["fix1"] = meta
    p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
