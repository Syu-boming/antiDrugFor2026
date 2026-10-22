"""第五幕修正第 1 輪：程式繪製素材 v02（G5 第二批驗收 b2_art／b2_director／b2_safety 指出的問題）。

- 救護車 v02（a5-ambulance_v02）：車頭朝畫面左、後車門在右端（倒車停到長椅旁、從後門把擔架送上車）。
  車廂比救護人員高（站在車後面頭不會冒出車頂）；白色紙芯邊＋深色細線（同角色立牌）、紙纖維、上亮下暗的淡淡明暗、
  底部投影；車身腰線與輪胎的明度差約為 v01 的一半（細格光敏：車子移動時掃過的高對比邊）；車廂側面不開窗、
  手捧愛心圖示用淡色（不用紅十字、沒有任何文字或真實單位配色）；頂燈畫在圖裡（暖米黃、恆亮，不閃）。
- 後車門 a5-ambulance-door_v01：打開時以車尾為樞紐轉向鏡頭、關上時轉回車尾平面（側看變成一條線）。
- 擔架 v02（a5-gurney_v02）：床墊上緣 0.93（同長椅座面 0.92），阿樂叔叔坐上去不用改高度；灰色金屬架、摺好的毯子。
- 轉角的低年級小朋友 v02（a5-student_v02／a5-student-arm_v02）：主線裁定「沒有五官的灰色幾何人影一律改成不透明、
  有紙纖維的淺紙色小紙人放遠景」：淺紙色分件小紙人（同第四幕遠景家長牽孩子的畫法 review/G5/a4/scripts/build_a4_art_fix1.py），
  側面朝畫面右、小黃帽、書包，只有一點眼睛；白色紙芯邊。

輸出：assets/final/sets/a5_gate/a5-{ambulance_v02,ambulance-door_v01,gurney_v02,student_v02,student-arm_v02}.png；
review/G5/a5/art_meta.json 的 fix1 鍵。
用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/build_a5_art_fix1.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

GATE = ROOT / "assets/final/sets/a5_gate"
META = ROOT / "review/G5/a5/art_meta.json"
INK = P.INK

CREAM = (246, 240, 226, 255)
CREAM_D = (234, 227, 211, 255)      # 下半部／裙邊
SAGE_L = (194, 212, 198, 255)       # 腰線（v01 SAGE 150,182,160 的明度差減半）
SAGE_LINE = (170, 190, 176, 255)
TIRE = (158, 151, 143, 255)         # 輪胎（v01 92,84,78 的明度差減半）
HUB = (174, 168, 160, 255)         # 輪轂（和輪胎明度接近：車子移動時輪子掃過細格只算一次明暗）
ARCH = (184, 176, 166, 255)
FROST = (228, 232, 228, 255)        # 霧面窗（和車身明度相近）
CAB_GLASS = (214, 224, 224, 255)
CORAL_L = (236, 184, 168, 255)      # 淡色愛心
SKIN_L = (240, 214, 188, 255)
AMBER = (250, 222, 160, 255)
AMBER_D = (228, 196, 128, 255)
DGRAY = (150, 146, 140, 255)


def lab_L(rgb):
    c = np.asarray(rgb, np.float64)[..., :3] / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(y > 0.008856, 116 * np.cbrt(y) - 16, 903.3 * y)


def heart_hand_soft(s, cx, cy, k):
    """手捧愛心（淡色、細線；同第二幕求助站造形）"""
    s.poly([(cx - 70 * k, cy + 10 * k), (cx + 70 * k, cy + 10 * k), (cx + 60 * k, cy + 36 * k), (cx + 20 * k, cy + 52 * k),
            (cx - 30 * k, cy + 50 * k), (cx - 64 * k, cy + 34 * k)], SKIN_L, line=1.6)
    hx, hy, r = cx, cy - 28 * k, 26 * k
    s.ellipse(hx - 2 * r + 4 * k, hy - r, hx + 4 * k, hy + r * 0.9, CORAL_L, line=0)
    s.ellipse(hx - 4 * k, hy - r, hx + 2 * r - 4 * k, hy + r * 0.9, CORAL_L, line=0)
    s.poly([(hx - 2 * r + 6 * k, hy + 6 * k), (hx + 2 * r - 6 * k, hy + 6 * k), (hx, hy + 2.1 * r)], CORAL_L, line=0)


def shade_and_shadow(a, top_gain=0.03, bot_gain=-0.06):
    """上亮下暗的淡淡明暗（紙片受光），只乘在不透明的地方"""
    h = a.shape[0]
    g = np.linspace(1 + top_gain, 1 + bot_gain, h)[:, None, None]
    out = a.astype(np.float32)
    out[..., :3] *= g
    return np.clip(out, 0, 255).astype(np.uint8)


def add_ground_shadow(a, y_ground, x0, x1, height=18, alpha=0.32):
    """底部投影：圖下緣加一條柔和的暖灰陰影（在紙芯邊外）"""
    H, W = a.shape[:2]
    pad = height + 8
    big = np.zeros((H + pad, W, 4), np.uint8)
    big[:H] = a
    sh = np.zeros((H + pad, W), np.float32)
    yy = int(y_ground)
    sh[yy - 4:yy + height // 2, int(x0):int(x1)] = 1.0
    sh = ndimage.gaussian_filter(sh, (height / 2.5, height / 1.5)) * alpha
    base = big.astype(np.float32)
    al = base[..., 3] / 255.0
    sc = np.array([92, 78, 66], np.float32)
    out_a = al + sh * (1 - al)
    rgb = (base[..., :3] * al[..., None] + sc * (sh * (1 - al))[..., None]) / np.maximum(out_a, 1e-6)[..., None]
    out = np.zeros_like(base)
    out[..., :3] = rgb
    out[..., 3] = out_a * 255
    return np.clip(out, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ 救護車 v02（車頭朝畫面左）
AMB_PPU = 140
AMB_L, AMB_H = 8.4, 4.05            # 世界單位（含頂燈、不含白邊）


def ambulance_v02():
    u = AMB_PPU
    W, H = int(AMB_L * u), int(AMB_H * u)
    s = P.Sheet(W, H)
    ground = H - 3
    wheel_r = 0.5 * u
    wy = ground - wheel_r
    cab_x1 = int(2.55 * u)                    # 駕駛艙右緣（車廂從這裡開始）
    box_top = int(0.30 * u)                   # 車廂頂（頂燈在上面）
    body_bot = ground - int(0.36 * u)
    # 車廂（圓角方箱）
    s.rect(cab_x1 - 6, box_top, W - 6, body_bot, CREAM, line=2.6, r=int(0.12 * u))
    # 駕駛艙（斜擋風玻璃朝左）
    cab = [(cab_x1, int(1.2 * u)), (int(1.35 * u), int(1.2 * u)), (int(0.55 * u), int(2.05 * u)), (6, int(2.2 * u)),
           (6, body_bot), (cab_x1, body_bot)]
    s.poly(cab, CREAM, line=2.6)
    s.poly([(int(1.42 * u), int(1.34 * u)), (cab_x1 - int(0.16 * u), int(1.34 * u)), (cab_x1 - int(0.16 * u), int(2.02 * u)),
            (int(0.78 * u), int(2.02 * u))], CAB_GLASS, line=2.0)
    s.line([(int(1.75 * u), int(1.34 * u)), (int(1.75 * u), int(2.02 * u))], w=1.6)
    s.rect(int(1.55 * u), int(2.12 * u), int(1.72 * u), int(2.19 * u), DGRAY, line=1.2, r=3)
    s.rect(8, int(2.4 * u), int(0.28 * u), int(2.62 * u), (246, 234, 200, 255), line=1.4, r=4)   # 車頭燈（不亮）
    # 裙邊與保險桿
    s.rect(2, body_bot - 4, W - 2, body_bot + int(0.14 * u), CREAM_D, line=2.0, r=6)
    # 腰線（淡鼠尾草綠，明度差小）
    by0, by1 = int(2.38 * u), int(2.62 * u)
    s.rect(8, by0, W - 8, by1, SAGE_L, line=0)
    s.line([(8, by0), (W - 8, by0)], w=1.2, color=SAGE_LINE)
    s.line([(8, by1), (W - 8, by1)], w=1.2, color=SAGE_LINE)
    # 車廂側面：側門（細線）、手捧愛心圓牌（淡色）、後車門線＋霧面小窗＋把手
    s.line([(cab_x1 + int(0.55 * u), box_top + int(0.25 * u)), (cab_x1 + int(0.55 * u), body_bot - 6)], w=1.4)
    s.line([(cab_x1 + int(1.75 * u), box_top + int(0.25 * u)), (cab_x1 + int(1.75 * u), body_bot - 6)], w=1.4)
    s.rect(cab_x1 + int(1.55 * u), int(2.0 * u), cab_x1 + int(1.68 * u), int(2.06 * u), DGRAY, line=1.0, r=3)
    cx, cy, rr = W - int(2.05 * u), int(1.45 * u), int(0.56 * u)
    s.ellipse(cx - rr, cy - rr, cx + rr, cy + rr, (250, 247, 240, 255), line=2.0)
    heart_hand_soft(s, cx, cy + int(0.04 * u), 0.9)
    rd = W - int(0.62 * u)                    # 後車門（車尾一段）
    s.line([(rd, box_top + int(0.1 * u)), (rd, body_bot - 4)], w=1.6)
    s.rect(rd + int(0.12 * u), box_top + int(0.45 * u), W - int(0.14 * u), box_top + int(1.15 * u), FROST, line=1.6, r=6)
    s.rect(rd + int(0.14 * u), int(2.0 * u), rd + int(0.3 * u), int(2.07 * u), DGRAY, line=1.0, r=3)
    # 車尾燈（米黃、不亮）
    s.rect(W - int(0.16 * u), int(2.75 * u), W - 6, int(3.0 * u), (240, 214, 176, 255), line=1.2, r=3)
    # 頂燈（暖米黃、恆亮）：車廂後角一盞、駕駛艙頂一條
    for x0, x1, y0 in ((W - int(0.95 * u), W - int(0.25 * u), box_top - int(0.24 * u)), (cab_x1 + int(0.15 * u), cab_x1 + int(1.15 * u), box_top - int(0.24 * u))):
        s.rect(x0 - 4, y0 + int(0.15 * u), x1 + 4, box_top + 2, DGRAY, line=1.4, r=3)
        s.rect(x0, y0, x1, y0 + int(0.2 * u), AMBER, line=1.8, r=int(0.08 * u))
        s.line([(x0 + (x1 - x0) * 0.5, y0 + 4), (x0 + (x1 - x0) * 0.5, y0 + int(0.17 * u))], w=1.2, color=AMBER_D)
    # 車底裙板（到地面：車後面的人腳不會從車底露出來；和輪拱同一個中明度）
    s.rect(int(0.4 * u), body_bot + int(0.12 * u), W - int(0.4 * u), ground - 2, ARCH, line=1.6, r=4)
    # 輪拱與輪子（明度差減半）
    wheels = []
    for wx in (int(1.35 * u), W - int(1.6 * u)):
        s.d.pieslice([(wx - wheel_r - 10) * 2, (wy - wheel_r - 10) * 2, (wx + wheel_r + 10) * 2, (wy + wheel_r + 10) * 2], 180, 360, fill=ARCH)
        s.d.rectangle([(wx - wheel_r - 10) * 2, wy * 2, (wx + wheel_r + 10) * 2, (body_bot + int(0.14 * u)) * 2], fill=ARCH)
        s.ellipse(wx - wheel_r, wy - wheel_r, wx + wheel_r, wy + wheel_r, TIRE, line=2.2)
        s.ellipse(wx - wheel_r * 0.5, wy - wheel_r * 0.5, wx + wheel_r * 0.5, wy + wheel_r * 0.5, HUB, line=1.6)
        wheels.append(wx)
    a = s.finish(white_border=5, edge_dark=0.06)
    pad = 5 + 6
    a = shade_and_shadow(a)
    a = add_ground_shadow(a, H + pad - 2, pad + 10, W + pad - 10)
    meta = {
        "size_world_core": [AMB_L, AMB_H], "pad_px": pad, "ppu": u,
        "image_px": [int(a.shape[1]), int(a.shape[0])],
        "image_world": [a.shape[1] / u, a.shape[0] / u],
        "bottom_core_from_image_bottom_world": (a.shape[0] - (H + pad)) / u,
        "rear_end_from_center_world": (W / 2) / u,
        "roof_world": (H - box_top) / u,
        "L_body": float(lab_L(CREAM)), "L_stripe": float(lab_L(SAGE_L)), "L_tire": float(lab_L(TIRE)),
        "L_stripe_v01": float(lab_L((150, 182, 160))), "L_tire_v01": float(lab_L((92, 84, 78))),
    }
    return a, meta


def ambulance_door():
    """後車門（打開時看到的門板：米白、霧面窗、腰線；樞紐在左緣）"""
    u = AMB_PPU
    w, h = 1.05, 3.0
    W, H = int(w * u), int(h * u)
    s = P.Sheet(W, H)
    s.rect(4, 4, W - 4, H - 4, CREAM, line=2.4, r=10)
    s.rect(int(0.14 * u), int(0.3 * u), W - int(0.14 * u), int(1.0 * u), FROST, line=1.6, r=6)
    y0 = int((2.38 - 0.30) * u)
    s.rect(6, y0, W - 6, y0 + int(0.24 * u), SAGE_L, line=0)
    s.line([(6, y0), (W - 6, y0)], w=1.2, color=SAGE_LINE)
    s.line([(6, y0 + int(0.24 * u)), (W - 6, y0 + int(0.24 * u))], w=1.2, color=SAGE_LINE)
    s.rect(W - int(0.3 * u), int(1.7 * u), W - int(0.14 * u), int(1.77 * u), DGRAY, line=1.0, r=3)
    a = s.finish(white_border=4, edge_dark=0.06)
    a = shade_and_shadow(a)
    return a, {"size_world_core": [w, h], "pad_px": 4 + 6, "ppu": u, "image_world": [a.shape[1] / u, a.shape[0] / u],
               "top_from_box_top_world": 0.02}


# ------------------------------------------------------------------ 擔架 v02（床墊上緣 0.93）
def gurney_v02():
    w, h = 2.5, 1.12
    PPW = 200
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    mat_top = int(H - 0.93 * PPW)           # 床墊上緣
    frame_y = mat_top + int(0.2 * PPW)
    metal = (196, 200, 202, 255)
    for x in (int(W * 0.18), int(W * 0.82)):
        s.line([(x, frame_y + 10), (x - 26, H - 28)], w=7, color=metal)
        s.line([(x, frame_y + 10), (x + 26, H - 28)], w=7, color=metal)
        for dx in (-26, 26):
            s.ellipse(x + dx - 14, H - 32, x + dx + 14, H - 4, (176, 172, 168, 255), line=1.6)
    s.rect(10, frame_y - 4, W - 10, frame_y + 16, metal, line=2.0, r=6)
    s.rect(16, mat_top, W - 16, frame_y, (246, 242, 232, 255), line=2.2, r=14)
    s.rect(int(W * 0.66), mat_top - 26, int(W * 0.92), mat_top + 4, (200, 218, 204, 255), line=1.8, r=8)   # 摺好的毯子
    s.line([(int(W * 0.66) + 8, mat_top - 12), (int(W * 0.92) - 8, mat_top - 12)], w=1.2, color=SAGE_LINE)
    a = s.finish(white_border=4)
    return a, {"size_world_core": [w, h], "pad_px": 10, "ppw": PPW, "image_world": [a.shape[1] / PPW, a.shape[0] / PPW],
               "mattress_top_world_core": 0.93}


# ------------------------------------------------------------------ 轉角的低年級小朋友 v02（淺紙色分件小紙人）
def student_v02():
    w, h = 0.9, 1.75
    PPW = 220
    W, H = int(w * PPW), int(h * PPW)
    s = P.Sheet(W, H)
    cx = W * 0.5
    g = H - 6
    hair = (128, 104, 84, 255)
    top = (206, 214, 222, 255)
    shorts = (196, 188, 170, 255)
    pack = (214, 196, 160, 255)
    cap = (238, 214, 150, 255)
    skin = (238, 210, 182, 255)
    shoe = (156, 138, 122, 255)
    # 書包（背後、畫面左）
    s.rect(cx - 62, H * 0.33, cx - 14, H * 0.6, pack, line=1.6, r=10)
    s.line([(cx - 58, H * 0.44), (cx - 18, H * 0.44)], 1.4, (168, 140, 106, 255))
    # 腿、鞋（側面朝右，一前一後）
    s.rect(cx - 22, H * 0.7, cx - 4, g - 16, skin, line=1.4, r=5)
    s.rect(cx + 2, H * 0.7, cx + 20, g - 16, skin, line=1.4, r=5)
    s.ellipse(cx - 26, g - 20, cx + 4, g - 2, shoe, line=1.2)
    s.ellipse(cx - 2, g - 20, cx + 30, g - 2, shoe, line=1.2)
    s.rect(cx - 30, H * 0.6, cx + 28, H * 0.74, shorts, line=1.6, r=6)
    # 上衣
    s.poly([(cx - 30, H * 0.33), (cx + 26, H * 0.33), (cx + 32, H * 0.64), (cx - 34, H * 0.64)], top, line=1.6)
    s.line([(cx - 12, H * 0.34), (cx - 4, H * 0.58)], 5, (192, 172, 136, 255))       # 書包背帶
    # 垂下的手臂（近側）
    s.rect(cx + 2, H * 0.36, cx + 18, H * 0.57, top, line=1.4, r=7)
    s.ellipse(cx + 1, H * 0.555, cx + 19, H * 0.62, skin, line=1.2)
    # 頭（側面）、頭髮、小黃帽與帽簷（朝右）、耳朵、一點眼睛
    s.ellipse(cx - 30, H * 0.11, cx + 28, H * 0.33, skin, line=1.6)
    s.ellipse(cx - 32, H * 0.13, cx + 6, H * 0.3, hair, line=1.4)
    s.ellipse(cx - 34, H * 0.07, cx + 30, H * 0.2, cap, line=1.6)
    s.rect(cx + 14, H * 0.155, cx + 50, H * 0.19, cap, line=1.4, r=6)
    s.ellipse(cx - 8, H * 0.2, cx + 4, H * 0.25, skin, line=1.0)
    s.ellipse(cx + 15, H * 0.215, cx + 21, H * 0.235, (110, 92, 78, 255), line=0)
    body = s.finish(white_border=4)
    # 揮手的手臂（肩膀在圖下緣附近）
    aw, ah = 0.24, 0.5
    AP = 220
    AW, AH = int(aw * AP), int(ah * AP)
    t = P.Sheet(AW, AH)
    t.rect(AW * 0.5 - 9, AH * 0.3, AW * 0.5 + 9, AH - 4, top, line=1.4, r=7)
    t.ellipse(AW * 0.5 - 12, AH * 0.08, AW * 0.5 + 12, AH * 0.34, skin, line=1.2)
    arm = t.finish(white_border=3)
    meta = {"size_world_core": [w, h], "arm_size_world_core": [aw, ah],
            "shoulder_world_from_bottom_center": [(10) / PPW, H * (1 - 0.36) / PPW],
            "image_world": [body.shape[1] / PPW, body.shape[0] / PPW], "arm_image_world": [arm.shape[1] / AP, arm.shape[0] / AP]}
    return body, arm, meta


def main():
    meta = json.loads(META.read_text()) if META.exists() else {}
    fx = {}
    a, m = ambulance_v02()
    P.save(a, GATE / "a5-ambulance_v02.png")
    fx["ambulance"] = m
    a, m = ambulance_door()
    P.save(a, GATE / "a5-ambulance-door_v01.png")
    fx["ambulance_door"] = m
    a, m = gurney_v02()
    P.save(a, GATE / "a5-gurney_v02.png")
    fx["gurney"] = m
    b, arm, m = student_v02()
    P.save(b, GATE / "a5-student_v02.png")
    P.save(arm, GATE / "a5-student-arm_v02.png")
    fx["student"] = m
    meta["fix1"] = {"made_by": "review/G5/a5/scripts/build_a5_art_fix1.py", **fx}
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(fx, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
