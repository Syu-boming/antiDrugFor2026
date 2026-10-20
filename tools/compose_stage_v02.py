"""（第 2 輪版本保留：tools/compose_stage_v02.py；第 3 輪改用 compose_stage.py）舞台合成試作 v02（G2 第 2 輪）：景板 bg-square_v02＋三位 v02 母版（阿樂叔叔用分件 rig）＋操偶線三點＋字幕紙條。

用法：
  /opt/anaconda3/bin/python3 tools/compose_stage.py [--out-dir review/G2]
輸出（全部帶 _v02，不覆寫第 1 輪）：
  stage_composite_v02.png        1920×1080（16:9）
  stage_composite_43_v02.png     1440×1080（4:3；v1.2 §16.1：舞台靠上、下方 25% 黑邊放兩行字幕）
  stage_composite_1024x768_v02.png  直接以 1024×768 輸出（4:3 投影機原生解析度）
  stage_composite_nosub_v02.png  無字幕版（量測用）
  stage_wash_compare_v02.png     景板原圖／舞台調色後（表演區洗光、遠景降彩）對照
  contrast_v02.json              逐色對比量測（原圖、投影 v1、投影 v2、低對比）＋操偶線＋字幕＋色差
  contrast_table_v02.png         逐色對比量測表（含取樣座標標記圖）
  jacket_deltaE_v02.png          小宇外套色票與 stage／raw 母版同位置色差
  intent_force_demo_v02.png      「意圖與受力」靜態演示（三格）

規則（v1.2 §14.1、§14.2、§15.2、§16.1、§16.2；CLAUDE.md 第 2 條）：
- 主光左上前方 45°：角色影子落在右下；離景板越遠的角色，影子越淡、越柔、偏移越大；腳底接觸影往右下拖成斜片，不用正圓橢圓。
- 角色固有色不調：母版直接貼上（只做縮放、鏡像、整體微傾），舞台調色只動景板。
- 操偶線：灰色扭紋紙繩 8 px@1080p＋兩側各 2 px 深灰邊線（淡灰本體、左上受光邊、低對比不規則扭紋），只扣腕背、肘外、膝前三點（紙環），往上延伸出畫面；
  路徑自動避開手、臉、圍裙綁帶（量測最小距離寫進 contrast_v02.json）。
- 字幕：字身 70 px@1080（§16.2 64–72 px 取上段），每行 ≤16 字、最多兩行，白字＋2 px 描邊，半透明深色紙條。
  4:3 版字級以「輸出畫面高 1080」換算，不隨舞台縮小。
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from projsim import projector, low_contrast  # noqa: E402
import rig_ale  # noqa: E402

W, H = 1920, 1080
CHILD_RATIO = 0.65
ADULT_H = 640              # 阿樂叔叔（站姿）身高 px@1080
STAGE_BG = ROOT / "assets/generated/bg-square_v02.png"
MASTERS = {
    "xiaoqing": ROOT / "assets/generated/chr-xiaoqing_master_v02.png",
    "xiaoyu": ROOT / "assets/generated/chr-xiaoyu_master_v02.png",
    "ale": ROOT / "assets/generated/chr-ale_master_v02.png",
}
RAW_XIAOYU = ROOT / "review/G2/raw/master_xiaoyu.png"          # 原始生成（外套基準色）
V01_XIAOYU = ROOT / "assets/generated/chr-xiaoyu_master_v01.png"  # 第 1 輪壓暗版（對照用）

# 站位（a2_c002「線落下來」的瞬間）：阿樂在左（危險固定從左側來），孩子在右（安全側）、面向阿樂（鏡像）
# depth：離景板的相對距離（1＝中景）；越大＝越靠觀眾 → 影子越淡越柔、偏移越大
LAYOUT = {
    "ale": dict(cx=0.318, feet=828, scale=1.00, mirror=False, lean=0.0, depth=1.0),
    "xiaoqing": dict(cx=0.540, feet=840, scale=1.03, mirror=True, lean=-4.0, depth=1.35),   # 往前傾、靠近阿樂：「叔叔，小心！」
    "xiaoyu": dict(cx=0.722, feet=808, scale=0.95, mirror=True, lean=3.0, depth=0.75),      # 往後退半步、身體後仰
}
ALE_POSE = {  # 被線拉偏的瞬間：右手本來想揮手，肘外線把手肘往外上提、腕背線把手腕往外上拉，手掌無力垂下；右膝被往前提
    "upper_arm_r": 84, "forearm_r": 62, "hand_r": -112, "upper_arm_l": -21, "forearm_l": -6,
    "thigh_r": -10, "shin_r": 12, "head": -4, "root": (0, 0, -1.5, "hip_mid"),
}
SUB_LINES = ["咦？我想揮手……", "手怎麼跑到旁邊去了？"]   # 劇本 a2_c002_01（阿樂叔叔），在詞語邊界斷行
SUB_PX = 70
FONT_CANDIDATES = [
    ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
]
LABEL_FONT = (FONT_CANDIDATES[0][0], 10)

# 舞台調色（只動景板）
WASH = dict(top=330, feather=110, lift=0.62, desat=0.60, warm=(246, 238, 222), mix=0.20,
            v_lo=0.42, v_hi=0.70, s_lo=0.22, s_span=0.30)
FAR_DESAT = 0.80          # 遠景（天空與遠山：藍、藍綠色相）保留的彩度
SHADOW = dict(base_strength=0.07, base_offset=(60, 45), base_sigma=13.0, contact_strength=0.30)

COSTUMES = {
    # 色相範圍（度）、飽和度下限/上限、明度下限/上限（HSV，0–1）；在原始顏色上判斷
    "ale": [("深藍圍裙", (195, 255), 0.18, 1.0, 0.10, 0.62, True), ("米色襯衫", (14, 50), 0.04, 0.46, 0.55, 1.0, False),
            ("橄欖褐長褲", (25, 62), 0.28, 1.0, 0.10, 0.58, False)],
    "xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.28, 1.0, 0.12, 0.90, True), ("芥末黃上衣", (32, 56), 0.55, 1.0, 0.55, 1.0, False),
                 ("深棕頭髮", (0, 45), 0.20, 0.75, 0.10, 0.42, False)],
    "xiaoyu": [("橘紅外套", (345, 22), 0.62, 1.0, 0.28, 1.0, True), ("卡其短褲", (22, 46), 0.28, 0.75, 0.40, 0.88, False),
               ("深棕頭髮", (0, 45), 0.20, 0.80, 0.08, 0.40, False)],
}
NAMES = {"ale": "阿樂叔叔", "xiaoqing": "小晴", "xiaoyu": "小宇"}


# ---------------------------------------------------------------- 色彩工具
def rel_lum(rgb):
    a = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def contrast(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def srgb_to_lab(rgb):
    a = np.asarray(rgb, float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_srgb(lab):
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116
    fx, fz = fy + A / 500, fy - B / 200
    finv = lambda t: np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))  # noqa: E731
    xyz = np.stack([finv(fx), finv(fy), finv(fz)], -1) * np.array([0.95047, 1.0, 1.08883])
    m = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])
    lin = np.clip(xyz @ m.T, 0, 1)
    return np.clip(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055) * 255, 0, 255)


def delta_e2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    else:
        hbp = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dtheta = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def hsv_np(rgb):
    a = rgb.astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = (mx - mn) / (mx + 1e-6)
    return h, s, mx


def find_font(px):
    for path, idx in FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(path, px, index=idx)
            return f, f"{f.getname()[0]} {f.getname()[1]}"
        except OSError:
            continue
    raise SystemExit("找不到繁中字型")


def lfont(px):
    try:
        return ImageFont.truetype(LABEL_FONT[0], px, index=LABEL_FONT[1])
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- 景板調色
def stage_grade(rgb):
    """舞台燈光（只動景板）：
    1) 遠景降彩：天空與遠山（藍、藍綠色相、位於畫面上半）彩度 ×FAR_DESAT；不整體抬黑、不加霧。
    2) 表演區洗光：角色站位帶（約 y≥330 到地面）只把「淺色、低彩度的面」（騎樓牆面、鐵捲門、地面）往暖白提亮，
       樹、燈籠、花台等有色物件不動（避免整片起霧），讓中明度的服裝主色（湖水綠、深藍）在投影後對相鄰背景拉開。
       上方的紅磚、樹、遠山保留原本的暖色日光與明暗層次。"""
    out = rgb.astype(np.float32).copy()
    h, s, v = hsv_np(rgb)
    yy = np.arange(H, dtype=np.float32)[:, None]
    far = ((h > 150) & (h < 235) & (s > 0.12)).astype(np.float32) * np.clip((560 - yy) / 120, 0, 1)
    far = ndimage.gaussian_filter(far, 2)[..., None]
    gray = out.mean(-1, keepdims=True)
    out = out * (1 - far) + (gray + (out - gray) * FAR_DESAT) * far
    # 表演區洗光：只提亮「淺色、低彩度的面」（騎樓牆面、鐵捲門、地面），樹、燈籠、花台等有色物件不動，避免整片起霧
    m = np.clip((yy - WASH["top"]) / WASH["feather"], 0, 1) * np.ones((1, W), np.float32)
    a = out / 255.0
    hh, ss_, vv = hsv_np(np.clip(out, 0, 255).astype(np.uint8))
    lum = a.mean(-1)
    sel = np.clip((lum - WASH["v_lo"]) / (WASH["v_hi"] - WASH["v_lo"]), 0, 1) * np.clip(1 - (ss_ - WASH["s_lo"]) / WASH["s_span"], 0, 1)
    sel = ndimage.gaussian_filter(sel, 1.2)
    k = (m * sel)[..., None]
    lifted = 1 - (1 - a) * (1 - WASH["lift"])          # 往紙白靠（亮部保留細節比例）
    g2 = lifted.mean(-1, keepdims=True)
    lifted = g2 + (lifted - g2) * WASH["desat"]
    lifted = lifted * (1 - WASH["mix"]) + np.array(WASH["warm"], np.float32) / 255 * WASH["mix"]
    out = out * (1 - k) + lifted * 255 * k
    m = m * np.ones((H, W), np.float32)
    m = m[..., None]
    return np.clip(out, 0, 255), m[..., 0]


# ---------------------------------------------------------------- 角色擺放
def trim(im):
    arr = np.array(im)
    arr[..., 3] = np.where(arr[..., 3] < 24, 0, arr[..., 3])
    im = Image.fromarray(arr, "RGBA")
    ys, xs = np.nonzero(arr[..., 3] > 16)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def place_master(key, im, lay, height):
    """縮放到身高 height、必要時鏡像、繞腳底中心傾斜 lean 度；回傳 (全畫面 RGBA, 變換資訊)。"""
    im = trim(im)
    s = height / im.height
    im2 = im.resize((round(im.width * s), round(height)), Image.LANCZOS)
    if lay["mirror"]:
        im2 = im2.transpose(Image.FLIP_LEFT_RIGHT)
    if lay["lean"]:
        pad = 60
        big = Image.new("RGBA", (im2.width + 2 * pad, im2.height + 2 * pad), (0, 0, 0, 0))
        big.paste(im2, (pad, pad))
        piv = (pad + im2.width / 2, pad + im2.height)
        big = big.rotate(-lay["lean"], resample=Image.BICUBIC, center=piv)
        x = round(lay["cx"] * W - piv[0])
        y = round(lay["feet"] - piv[1])
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.alpha_composite(big, (max(x, 0), max(y, 0)), (max(-x, 0), max(-y, 0)))
    else:
        x = round(lay["cx"] * W - im2.width / 2)
        y = round(lay["feet"] - im2.height)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.alpha_composite(im2, (x, y))
    return layer, dict(scale=s, mirror=lay["mirror"], lean=lay["lean"], height=height, src_size=im.size)


def place_ale(pose, head="worried", lay=None, height=ADULT_H):
    """阿樂叔叔：rig 擺姿勢 → 縮放貼到畫面。回傳 (全畫面 RGBA, 點位換算函式, rig 資訊)。"""
    lay = lay or LAYOUT["ale"]
    if head == "worried":
        wim, A, info = rig_ale.make_worried_head()
        rig = rig_ale.Rig(head_override=(wim, A))
    else:
        rig = rig_ale.Rig()
        info = None
    img, pt, Mw = rig.render(pose)
    rest, _, _ = rig_ale.Rig().render({})
    ra = np.array(rest)[..., 3] > 16
    ys, xs = np.nonzero(ra)
    top, bot = ys.min(), ys.max()
    s = height / (bot - top)
    cx_rig = (xs.min() + xs.max()) / 2
    big = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    ox = lay["cx"] * W - cx_rig * s
    oy = lay["feet"] - bot * s
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ix, iy = int(round(ox)), int(round(oy))
    layer.alpha_composite(big, (max(ix, 0), max(iy, 0)), (max(-ix, 0), max(-iy, 0)))

    def to_stage(part, p):
        q = pt(part, p)
        return np.array([q[0] * s + ix, q[1] * s + iy])
    return layer, to_stage, dict(scale=s, head=info, rig=rig, Mw=Mw)


def char_shadow(alpha, lay, feet_y):
    """主光左上前方 45°：(1) 落在景板上的柔和投影，往右下偏移；depth 越大（離景板越遠）→ 越淡、越柔、偏移越大；
    (2) 腳底接觸影：取腳底一小段輪廓，往右下拖成斜片後模糊（不是置中的正圓橢圓）。"""
    a = alpha.astype(np.float32) / 255.0
    d = lay["depth"]
    off = (SHADOW["base_offset"][1] * d, SHADOW["base_offset"][0] * d)
    sig = SHADOW["base_sigma"] * d ** 1.6
    stg = SHADOW["base_strength"] / d ** 1.3
    drop = ndimage.gaussian_filter(ndimage.shift(a, off, order=1), sig) * stg
    drop[int(feet_y + 10):, :] = 0
    foot = a.copy()
    ys = np.nonzero(a.max(1) > 0.5)[0]
    hgt = ys.max() - ys.min()
    foot[: int(feet_y - hgt * 0.035), :] = 0
    foot[int(feet_y + 4):, :] = 0
    # 往右下斜拖：x 方向 shear，y 方向壓扁
    sl = np.zeros_like(a)
    for k in range(0, 9):
        sl = np.maximum(sl, ndimage.shift(foot, (k * 1.2, k * 5.0 * d), order=1) * (1 - k / 11))
    contact = ndimage.gaussian_filter(sl, 3.0 + 2 * d) * SHADOW["contact_strength"] / d ** 0.5
    return np.clip(np.maximum(drop, contact), 0, 1)


def multiply_shadow(base, mask, color=(58, 44, 36)):
    m = mask[..., None]
    col = np.array(color, dtype=np.float32) / 255.0
    return base * (1 - m + m * col)


def card_edge(layer):
    """厚卡紙側邊：主光左上 → 輪廓右下側露出 2 px 深色卡紙厚度（畫在角色後面）。"""
    a = np.array(layer)[..., 3].astype(np.float32) / 255
    sh = ndimage.shift(a, (2.0, 1.6), order=1)
    edge = np.clip(sh - a, 0, 1)
    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = 96, 84, 72
    out[..., 3] = (edge * 235).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------- 操偶線與紙環
def draw_rope(canvas, pts, width=8.0, ss=4, seed=3):
    """灰色扭紋紙繩：淡灰本體、深灰邊線、左上受光邊、右下背光帶、低對比不規則扭紋（紙繩，不是金屬纜線）。"""
    x0, y0 = np.floor(pts.min(0) - 24).astype(int)
    x1, y1 = np.ceil(pts.max(0) + 24).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, canvas.width), min(y1, canvas.height)
    if x1 <= x0 or y1 <= y0:
        return
    bw, bh = (x1 - x0) * ss, (y1 - y0) * ss
    p = (pts - [x0, y0]) * ss
    seq = [tuple(v) for v in p]
    layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(layer).line(seq, fill=(50, 48, 46, 255), width=int((width + 4) * ss), joint="curve")   # 深灰邊線（兩側各 2 px）
    core = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(core).line(seq, fill=255, width=int(width * ss), joint="curve")
    body = Image.new("RGBA", (bw, bh), (178, 176, 170, 255))
    dd = ImageDraw.Draw(body)
    tang = np.gradient(p, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
    nor = np.stack([-tang[:, 1], tang[:, 0]], 1)
    up_left = np.array([-1.0, -1.0]) / math.sqrt(2)
    if (nor @ up_left).mean() < 0:
        nor = -nor
    hl = p + nor * width * 0.27 * ss
    dd.line([tuple(v) for v in hl], fill=(226, 224, 218, 255), width=max(int(width * 0.26 * ss), 1), joint="curve")
    sh = p - nor * width * 0.30 * ss
    dd.line([tuple(v) for v in sh], fill=(142, 140, 134, 255), width=max(int(width * 0.26 * ss), 1), joint="curve")
    seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    rng = np.random.default_rng(seed)
    s_ = 4.0 * ss
    while s_ < seglen[-1]:
        i = min(int(np.searchsorted(seglen, s_)), len(p) - 1)
        c, t, n = p[i], tang[i], nor[i]
        a = c + n * width * 0.5 * ss - t * width * 0.35 * ss
        b = c - n * width * 0.5 * ss + t * width * 0.35 * ss
        dd.line([tuple(a), tuple(b)], fill=(158, 156, 150, 255), width=max(int(1.0 * ss), 1))
        s_ += (8.0 + rng.uniform(-1.5, 1.5)) * ss
    body.putalpha(core)
    layer = Image.alpha_composite(layer, body)
    layer = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    canvas.alpha_composite(layer, (x0, y0))


def draw_loop(canvas, center, axis, half_w, occluder, ss=4, draw=True):
    """紙環：白色紙帶繞肢體一圈（環面垂直於肢體主軸）。後半圈被肢體擋住，前半圈壓在肢體上。
    draw=False 時只回傳前緣點（用來先挑繩路）。"""
    axis = np.asarray(axis, float) / (np.linalg.norm(axis) + 1e-9)
    n = np.array([-axis[1], axis[0]])
    R = half_w + 3.0
    r = max(R * 0.32, 3.5)
    t = np.linspace(0, 2 * np.pi, 200)
    ring = np.stack([np.cos(t) * R, np.sin(t) * r], 1)
    if not draw:
        return np.array(center) + ring[t <= np.pi][:, :1] * n + ring[t <= np.pi][:, 1:] * axis
    pad = 14
    size = int(2 * (R + pad))
    big = size * ss
    back = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    front = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    c = np.array([big / 2, big / 2])
    t = np.linspace(0, 2 * np.pi, 200)
    ring = np.stack([np.cos(t) * R, np.sin(t) * r], 1)            # 局部：x＝沿 n（橫過肢體），y＝沿 axis
    pts = c + (ring[:, :1] * n + ring[:, 1:] * axis) * ss
    fpts, bpts = pts[t <= np.pi], pts[t >= np.pi]                  # sin>0（沿 axis 正向）當前緣
    for img, seq, wo, wi in ((back, bpts, 5, 3), (front, fpts, 8, 5)):
        dr = ImageDraw.Draw(img)
        dr.line([tuple(v) for v in seq], fill=(52, 50, 48, 255), width=wo * ss, joint="curve")
        dr.line([tuple(v) for v in seq], fill=(250, 248, 242, 255), width=wi * ss, joint="curve")
    back = back.resize((size, size), Image.LANCZOS)
    front = front.resize((size, size), Image.LANCZOS)
    x0, y0 = int(round(center[0] - size / 2)), int(round(center[1] - size / 2))
    occ = np.zeros((size, size), np.float32)
    ys0, xs0 = max(y0, 0), max(x0, 0)
    ys1, xs1 = min(y0 + size, H), min(x0 + size, W)
    occ[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0] = occluder[ys0:ys1, xs0:xs1] / 255.0
    ba = np.array(back)
    ba[..., 3] = (ba[..., 3] * (1 - occ)).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(ba, "RGBA"), (x0, y0))
    canvas.alpha_composite(front, (x0, y0))
    # 前緣上「朝上」的那一點（線從這裡往上）
    cand = np.array(center) + ring[t <= np.pi][:, :1] * n + ring[t <= np.pi][:, 1:] * axis
    return cand


def seg_dist(pts, mask_dist):
    """折線上每一點到遮罩的距離（用距離場查表）。"""
    xs = np.clip(np.round(pts[:, 0]).astype(int), 0, W - 1)
    ys = np.clip(np.round(pts[:, 1]).astype(int), 0, H - 1)
    inside = (pts[:, 1] >= 0) & (pts[:, 1] < H) & (pts[:, 0] >= 0) & (pts[:, 0] < W)
    d = np.where(inside, mask_dist[ys, xs], 1e6)
    return d


def choose_anchor(start, forbid_dist, xs_try, others, skip=26, prefer_x=None, body=None):
    """在畫面上方外（y=−60）挑錨點，讓直線繩路離「禁止區」（手、臉、圍裙綁帶、其他角色）最遠、
    盡量走在身體外側（body：經過身體前方的比例會扣分）、接近垂直，且不和其他繩交叉。"""
    best = None
    for ax in xs_try:
        end = np.array([ax, -60.0])
        L = np.linalg.norm(end - start)
        n = int(L / 2)
        pts = start + (end - start) * np.linspace(0, 1, n)[:, None]
        cl = seg_dist(pts[skip:], forbid_dist).min() if n > skip else 0
        cross = any(segments_intersect(start, end, o0, o1) for o0, o1 in others)
        tilt = abs(ax - start[0]) / (start[1] + 60)
        over = 0.0
        if body is not None and n > skip:
            q = pts[skip:]
            ok = (q[:, 1] >= 0) & (q[:, 1] < H) & (q[:, 0] >= 0) & (q[:, 0] < W)
            q = q[ok].astype(int)
            over = float(body[q[:, 1], q[:, 0]].mean()) if len(q) else 0.0
        score = min(cl, 32) - 35 * tilt - 30 * over - (1000 if cross else 0) - (500 if cl < 6 else 0)
        if prefer_x is not None:
            score -= abs(ax - prefer_x) * 0.01
        if best is None or score > best[0]:
            best = (score, end, cl, cross)
    return best


def segments_intersect(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))


# ---------------------------------------------------------------- 字幕
def subtitle_block(canvas, lines, px, box_w, box_h, cx, bottom, strip=True):
    """兩行字幕＋半透明深色紙條。cx、bottom＝紙條中心 x 與下緣 y（畫布座標）。"""
    font, fname = find_font(px)
    d0 = ImageDraw.Draw(canvas)
    bbs = [d0.textbbox((0, 0), t, font=font) for t in lines]
    lh = int(round(px * 1.28))
    tw = max(b[2] - b[0] for b in bbs)
    pad_x, pad_y = int(px * 0.7), int(px * 0.26)
    sw = min(tw + 2 * pad_x, box_w)
    sh = lh * len(lines) + 2 * pad_y
    sx, sy = int(cx - sw / 2), int(bottom - sh)
    if strip:
        rng = np.random.default_rng(7)
        m = np.ones((sh, sw), np.float32)
        edge = max(int(px * 0.15), 6)
        for side in (0, 1):
            prof = ndimage.gaussian_filter1d(rng.normal(0, 1, sh), 3)
            prof = (prof - prof.min()) / (np.ptp(prof) + 1e-9) * edge
            for y in range(sh):
                k = int(prof[y])
                if side == 0:
                    m[y, :k] = 0
                else:
                    m[y, sw - k:] = 0
        m = ndimage.gaussian_filter(m, 0.8)
        grain = ndimage.gaussian_filter(rng.normal(0, 1, (sh, sw)), 1.2) * 6
        col = np.empty((sh, sw, 4), np.float32)
        col[..., 0], col[..., 1], col[..., 2] = 30 + grain, 27 + grain, 31 + grain
        col[..., 3] = m * 0.78 * 255
        canvas.alpha_composite(Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGBA"), (sx, sy))
    d = ImageDraw.Draw(canvas)
    boxes = []
    for i, (t, bb) in enumerate(zip(lines, bbs)):
        w_ = bb[2] - bb[0]
        tx = int(cx - w_ / 2 - bb[0])
        ty = int(sy + pad_y + i * lh + (lh - (bb[3] - bb[1])) / 2 - bb[1])
        d.text((tx, ty), t, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(20, 18, 20, 255))
        boxes.append([tx + bb[0], ty + bb[1], w_, bb[3] - bb[1]])
    return dict(font=fname, px=px, strip=[sx, sy, sw, sh], line_boxes=boxes, chars_per_line=[len(t) for t in lines])


def text_contrast(img, strip_box, line_boxes):
    """字幕白字對紙條底板（或 4:3 黑邊）的對比：原圖與投影 v2。底板取紙條內、字框外的像素中位數。"""
    a = np.array(img.convert("RGB"))
    x, y, w, h = strip_box
    region = a[y:y + h, x:x + w]
    m = np.ones(region.shape[:2], bool)
    for bx, by, bw, bh in line_boxes:
        m[max(by - y - 6, 0):by - y + bh + 6, max(bx - x - 6, 0):bx - x + bw + 6] = False
    bg = np.median(region[m], 0)
    txt = np.array([255, 255, 255], float)
    out = {}
    for tag, f in (("original", lambda c: c), ("proj_v2", lambda c: projector(np.asarray(c, np.uint8)[None, None, :], "v2")[0, 0])):
        lb, lt = float(rel_lum(f(bg.round()))), float(rel_lum(f(txt)))
        out[tag] = dict(bg_hex="#%02X%02X%02X" % tuple(np.asarray(f(bg.round())).astype(int)), contrast=round(contrast(lt, lb), 2))
    return out


def ink_height(img, box):
    """實測字形墨高：紙條範圍內接近白色的像素列。"""
    x, y, w, h = box
    a = np.array(img.convert("RGB"))[y:y + h, x:x + w].astype(int)
    white = (a.min(-1) > 225)
    rows = np.nonzero(white.sum(1) > 2)[0]
    return int(rows.max() - rows.min() + 1) if len(rows) else 0


# ---------------------------------------------------------------- 主流程
def build_scene(pose=ALE_POSE, head="worried"):
    stage_raw = np.array(Image.open(STAGE_BG).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    graded, wash_mask = stage_grade(stage_raw)
    layers, info = {}, {}
    adult_h = ADULT_H
    for key in ("xiaoyu", "xiaoqing"):
        lay = LAYOUT[key]
        layers[key], info[key] = place_master(key, Image.open(MASTERS[key]).convert("RGBA"), lay,
                                              adult_h * CHILD_RATIO * lay["scale"])
    layers["ale"], to_stage, info["ale"] = place_ale(pose, head)
    alphas = {k: np.array(v)[..., 3] for k, v in layers.items()}
    shaded = graded.copy()
    for k in ("xiaoyu", "ale", "xiaoqing"):
        shaded = multiply_shadow(shaded, char_shadow(alphas[k], LAYOUT[k], LAYOUT[k]["feet"]))
    canvas = Image.fromarray(np.clip(shaded, 0, 255).astype(np.uint8)).convert("RGBA")
    for k in ("xiaoyu", "ale", "xiaoqing"):          # 由後往前：小宇（後）→ 阿樂 → 小晴（前）
        canvas.alpha_composite(card_edge(layers[k]))
        canvas.alpha_composite(layers[k])
    return dict(stage_raw=stage_raw, graded=graded, shaded=shaded, wash_mask=wash_mask, layers=layers, alphas=alphas,
                to_stage=to_stage, info=info, chars_only=canvas.copy(), canvas=canvas)


def add_strings(sc, mode="taut"):
    """三條操偶線：右腕背、右肘外、膝前（自動挑左或右膝），紙環扣住，往上出畫面。
    mode="slack"：線還沒繃緊（中段下垂的弧線）；"taut"：繃直。"""
    canvas = sc["canvas"]
    to_stage = sc["to_stage"]
    rig = sc["info"]["ale"]["rig"]
    s = sc["info"]["ale"]["scale"]
    MJ = rig_ale.MJ
    a_ale = sc["alphas"]["ale"]
    # 禁止區：臉／頭、雙手、圍裙綁帶（蝴蝶結）——以「只畫某些部件」的方式取得各部件遮罩（畫面座標）
    def mask_of(parts):
        r = sc["info"]["ale"]["rig"]
        keep = {n: r.parts[n] for n in r.parts}
        blank = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        for n in r.parts:
            if n not in parts:
                r.parts[n] = blank
        lay, _, _ = place_ale_cached(sc, r)
        for n in keep:
            r.parts[n] = keep[n]
        return np.array(lay)[..., 3] > 60
    hands = mask_of({"hand_r", "hand_l"})
    headm = mask_of({"head"})
    forearm_r = mask_of({"forearm_r"})
    upper_r = mask_of({"upper_arm_r"})
    torso = mask_of({"torso"})
    # 蝴蝶結區（軀幹的右下角，腰帶以下保留的部分）
    bow = torso.copy()
    wy = to_stage("torso", MJ["waist"])[1]
    bow[: int(wy - 6), :] = False
    forbid = hands | headm | bow
    sc["masks"] = dict(hands=hands, head=headm, bow=bow, forearm_r=forearm_r, upper_r=upper_r)
    pose = sc.get("pose") or ALE_POSE
    H_s = rig_ale.H * s
    # 1) 右腕背：前臂遠端往近端 0.12 頭高處
    def along(part, p, q, frac):
        P = to_stage(part, np.array(MJ[p], float))
        Q = to_stage(part, np.array(MJ[q], float))
        return P + (Q - P) * frac, (Q - P)
    occ = sc["alphas"]["ale"]
    # 其他角色也不能被繩穿過（外擴 12 px）
    kids = np.zeros((H, W), bool)
    for k in ("xiaoqing", "xiaoyu"):
        if k in sc["alphas"]:
            kids |= sc["alphas"][k] > 60
    forbid2 = forbid | ndimage.binary_dilation(kids, iterations=12)
    fd = ndimage.distance_transform_edt(~forbid2)
    geo = {
        "wrist": along("forearm_r", "elbow_r", "wrist_r", 0.86) + (0.15 * H_s, "腕背（右）"),
        "elbow": along("upper_arm_r", "shoulder_r", "elbow_r", 0.86) + (0.22 * H_s, "肘外（右）"),
        "knee_r": along("shin_r", "knee_r", "ankle_r", 0.06) + (0.30 * H_s, "膝前（右）"),
        "knee_l": along("shin_l", "knee_l", "ankle_l", 0.06) + (0.30 * H_s, "膝前（左）"),
    }
    att, fronts = {}, {}
    for k, (c, ax, hw, _) in geo.items():
        fr = draw_loop(canvas, c, ax, hw, occ, draw=False)
        fronts[k] = fr
        att[k] = fr[np.argmin(fr[:, 1])] if k in ("wrist", "elbow") else fr[len(fr) // 2]
    body = occ > 60
    others, results = [], {}
    skip = int(0.12 * H_s)
    for name in ("wrist", "elbow"):
        # 腕背／肘外：在紙環前緣上取 7 個候選扣點（外側到上側），和錨點一起挑最乾淨的繩路
        fr = fronts[name]
        cands = fr[np.linspace(0, len(fr) - 1, 7).astype(int)]
        best = None
        for st in cands:
            xs_try = np.arange(st[0] - 300, st[0] + 120, 6)
            r = choose_anchor(st, fd, xs_try, others, skip=skip, prefer_x=st[0] - 40, body=body)
            if best is None or r[0] > best[1][0]:
                best = (st, r)
        st, (sc_, end, cl, cross) = best
        att[name] = st
        others.append((st, end))
        results[name] = dict(st=st, end=end, cl=cl, cross=cross, label=geo[name][3])
    # 膝前：左右兩腳都試，挑「離手、臉、綁帶、孩子最遠、又最接近垂直、不和其他線交叉」的那一條
    best_k = None
    for kn, xs_try in (("knee_r", np.arange(att["knee_r"][0] - 700, att["knee_r"][0] + 200, 5)),
                       ("knee_l", np.arange(att["knee_l"][0] - 200, att["knee_l"][0] + 700, 5))):
        st = att[kn]
        cand = choose_anchor(st, fd, xs_try, others, skip=int(0.20 * H_s), body=body)
        if best_k is None or cand[0] > best_k[1][0]:
            best_k = (kn, cand)
    kn, (sc_, end, cl, cross) = best_k
    results["knee"] = dict(st=att[kn], end=end, cl=cl, cross=cross, label=geo[kn][3])
    used = {"wrist": "wrist", "elbow": "elbow", "knee": kn}
    for name, gk in used.items():
        c, ax, hw, _ = geo[gk]
        draw_loop(canvas, c, ax, hw, occ)
    for i, (name, r) in enumerate(results.items()):
        st, end = r["st"], r["end"]
        pts = st + (end - st) * np.linspace(0, 1, 800)[:, None]
        if mode == "slack":
            # 鬆的線：沿垂直於繩的方向彎出一個弧（下段比上段彎得多，像沒拉緊的紙繩）
            t = np.linspace(0, 1, 800)[:, None]
            dvec = (end - st) / np.linalg.norm(end - st)
            nvec = np.array([dvec[1], -dvec[0]])
            if nvec[0] > 0:
                nvec = -nvec
            pts = pts + nvec * (np.sin(np.pi * t) * (1 - 0.5 * t)) * (34.0 + 10 * i)
        draw_rope(canvas, pts, width=8.0, seed=i + 3)
        results[name] = dict(attach_point=r["label"], attach=[round(float(st[0]), 1), round(float(st[1]), 1)],
                             anchor_offscreen=[round(float(end[0]), 1), -60],
                             min_clearance_px_to_hands_face_bow_kids=round(float(r["cl"]), 1), crosses_other_rope=bool(r["cross"]),
                             tilt_deg_from_vertical=round(math.degrees(math.atan2(st[0] - end[0], st[1] - end[1])), 1), pts=pts)
    # 繩不經過手掌前方：檢查所有繩與手部遮罩的交集像素數
    for name, r in results.items():
        p = r["pts"][int(0.12 * H_s):]
        xs = np.clip(np.round(p[:, 0]).astype(int), 0, W - 1)
        ys = np.clip(np.round(p[:, 1]).astype(int), 0, H - 1)
        ok = (p[:, 1] >= 0)
        r["samples_over_hand"] = int((hands[ys[ok], xs[ok]]).sum())
        r["samples_over_face"] = int((headm[ys[ok], xs[ok]]).sum())
    sc["ropes"] = results
    return results


def place_ale_cached(sc, rig):
    """用指定 rig（可能暫時清掉某些部件）重畫阿樂叔叔到畫面座標。"""
    pose = sc.get("pose") or ALE_POSE
    lay = sc.get("lay_ale") or LAYOUT["ale"]
    img, pt, _ = rig.render(pose)
    s = sc["info"]["ale"]["scale"]
    rest, _, _ = rig_ale.Rig().render({})
    ra = np.array(rest)[..., 3] > 16
    ys, xs = np.nonzero(ra)
    bot = ys.max()
    cx_rig = (xs.min() + xs.max()) / 2
    big = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    ix, iy = int(round(lay["cx"] * W - cx_rig * s)), int(round(lay["feet"] - bot * s))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(big, (max(ix, 0), max(iy, 0)), (max(-ix, 0), max(-iy, 0)))
    return layer, None, None


def costume_masks(sc):
    """各角色各服裝色的遮罩（畫面座標；在原始顏色上判斷，內縮 2 px 避開線條）。"""
    out = {}
    for key, specs in COSTUMES.items():
        layer = np.array(sc["layers"][key])
        rgb, a = layer[..., :3], layer[..., 3]
        h, s, v = hsv_np(rgb)
        base = ndimage.binary_erosion(a > 220, iterations=4)
        res = {}
        for name, (h0, h1), s0, s1, v0, v1, main in specs:
            hue_ok = ((h >= h0) | (h <= h1)) if h0 > h1 else ((h >= h0) & (h <= h1))
            m = base & hue_ok & (s >= s0) & (s <= s1) & (v >= v0) & (v <= v1)
            m = ndimage.binary_opening(m, iterations=1)
            if name == "深棕頭髮":
                ys = np.nonzero(a.max(1) > 0)[0]
                top = ys.min()
                m[int(top + 0.30 * (ys.max() - top)):, :] = False   # 頭髮只在頭部
            if key == "ale" and name == "米色襯衫":
                pass
            res[name] = dict(mask=m, main=main)
        out[key] = res
    return out


def measure(sc, final_rgb):
    """逐色對比：每個服裝色 × 實際相鄰背景（輪廓外 6–34 px、只算靠近該色的那一段），原圖／投影 v1／v2／低對比。"""
    any_char = np.zeros((H, W), bool)
    for k, a in sc["alphas"].items():
        any_char |= a > 60
    bg_img = np.clip(sc["shaded"], 0, 255).astype(np.uint8)        # 景板（含影子），不含角色、繩、字幕
    chars = np.array(sc["chars_only"].convert("RGB"))
    views = {"original": (bg_img, chars), "proj_v1": (projector(bg_img, "v1"), projector(chars, "v1")),
             "proj_v2": (projector(bg_img, "v2"), projector(chars, "v2")),
             "lowc": (low_contrast(bg_img), low_contrast(chars))}
    cms = costume_masks(sc)
    near_ring = ndimage.binary_dilation(any_char, iterations=34) & ~ndimage.binary_dilation(any_char, iterations=6)
    rows = []
    samples = []
    for key, res in cms.items():
        a = sc["alphas"][key] > 60
        dist_in = ndimage.distance_transform_edt(a)
        for cname, cinfo in res.items():
            m = cinfo["mask"]
            if m.sum() < 30:
                continue
            edge_part = m & (dist_in <= 16)
            if edge_part.sum() < 15:
                rows.append(dict(character=NAMES[key], color=cname, main=cinfo["main"], touches_background=False))
                continue
            ring = ndimage.binary_dilation(edge_part, iterations=34) & near_ring
            # 取樣點（10×10）：服裝取「靠外緣、且離其他顏色最遠」的一點；背景取它往外 20 px 處
            dm = ndimage.distance_transform_edt(m)
            cand = np.where(edge_part, dm, 0)
            yc, xc = np.unravel_index(np.argmax(cand), cand.shape)
            # 往外方向：離角色輪廓最近的外部點
            outside = ~ndimage.binary_dilation(any_char, iterations=8)
            dd, (iy, ix) = ndimage.distance_transform_edt(~outside, return_indices=True)
            by, bx = iy[yc, xc], ix[yc, xc]
            vec = np.array([bx - xc, by - yc], float)
            vec /= np.linalg.norm(vec) + 1e-9
            bpt = np.array([bx, by]) + vec * 8
            bx2, by2 = int(np.clip(bpt[0], 5, W - 6)), int(np.clip(bpt[1], 5, H - 6))
            row = dict(character=NAMES[key], color=cname, main=cinfo["main"], touches_background=True,
                       costume_pixels=int(m.sum()), ring_pixels=int(ring.sum()),
                       sample_costume_xy=[int(xc), int(yc)], sample_bg_xy=[bx2, by2])
            for vk, (bgv, chv) in views.items():
                cmed = np.median(chv[m], 0)
                cl = float(rel_lum(cmed))
                rl = rel_lum(bgv[ring])
                med, p10, p90 = float(np.median(rl)), float(np.percentile(rl, 10)), float(np.percentile(rl, 90))
                cs = np.median(chv[max(yc - 5, 0):yc + 5, max(xc - 5, 0):xc + 5].reshape(-1, 3), 0)
                bs = np.median(bgv[by2 - 5:by2 + 5, bx2 - 5:bx2 + 5].reshape(-1, 3), 0)
                row[vk] = dict(costume_hex="#%02X%02X%02X" % tuple(cmed.round().astype(int)), costume_lum=round(cl, 4),
                               ring_median_lum=round(med, 4), ring_p10_lum=round(p10, 4), ring_p90_lum=round(p90, 4),
                               contrast_median=round(contrast(cl, med), 2),
                               contrast_worst=round(min(contrast(cl, p10), contrast(cl, p90)), 2),
                               sample_contrast_10x10=round(contrast(float(rel_lum(cs)), float(rel_lum(bs))), 2))
            rows.append(row)
            samples.append((len(rows), (xc, yc), (bx2, by2)))
    # 外輪廓（深色內描線＋卡紙側邊）對背景：每位角色外緣 2–6 px 的最暗 25% 對相鄰背景
    outline = {}
    pv2c = projector(np.array(sc["canvas"].convert("RGB")), "v2")
    pv2b = views["proj_v2"][0]
    for key in sc["alphas"]:
        a = sc["alphas"][key] > 60
        band = ndimage.binary_dilation(a, iterations=3) & ~ndimage.binary_erosion(a, iterations=8)
        lum = rel_lum(pv2c[band])
        dark = float(np.percentile(lum, 20))
        ring = ndimage.binary_dilation(a, iterations=34) & ~ndimage.binary_dilation(a, iterations=6) & ~any_char
        bl = float(np.median(rel_lum(pv2b[ring])))
        outline[NAMES[key]] = dict(edge_dark_p20_lum=round(dark, 4), ring_median_lum=round(bl, 4), contrast=round(contrast(dark, bl), 2))
    return rows, samples, outline


def rope_checks(sc, final_rgb):
    pv2 = projector(final_rgb, "v2")
    any_char = np.zeros((H, W), bool)
    for a in sc["alphas"].values():
        any_char |= a > 60
    out = {}
    for name, r in sc["ropes"].items():
        pts = r["pts"]
        checks = []
        for frac in (0.08, 0.2, 0.35, 0.5, 0.7, 0.9):
            i = int(frac * (len(pts) - 1))
            cx, cy = pts[i]
            if cy < 6 or cy > H - 6:
                continue
            t = pts[min(i + 5, len(pts) - 1)] - pts[max(i - 5, 0)]
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])

            def lum_at(x, y):
                x, y = int(round(x)), int(round(y))
                return float(rel_lum(pv2[np.clip(y, 0, H - 1), np.clip(x, 0, W - 1)]))
            prof = [lum_at(cx + n[0] * d, cy + n[1] * d) for d in np.arange(-6, 6.5, 0.5)]
            sides = []
            for d in (-16, 16):
                x, y = int(round(cx + n[0] * d)), int(round(cy + n[1] * d))
                patch = pv2[max(y - 3, 0):y + 4, max(x - 3, 0):x + 4].reshape(-1, 3)
                sides.append(float(np.median(rel_lum(patch))))
            core = lum_at(cx, cy)
            checks.append(dict(at=[round(float(cx)), round(float(cy))], over_character=bool(any_char[int(cy), int(cx)]),
                               core_lum=round(core, 4), side_lum=[round(v, 4) for v in sides],
                               cross_section_min_max=[round(min(prof), 4), round(max(prof), 4)],
                               best_contrast_vs_each_side=[round(max(contrast(min(prof), sl), contrast(max(prof), sl)), 2) for sl in sides]))
        out[name] = dict({k: v for k, v in r.items() if k != "pts"}, samples_proj_v2=checks)
    return out


def jacket_delta(sc, final_rgb):
    """小宇外套：stage 合成與 raw 母版（原始生成）同位置的色差（CIEDE2000）＋色票。"""
    lay = LAYOUT["xiaoyu"]
    inf = sc["info"]["xiaoyu"]
    raw = trim(Image.open(RAW_XIAOYU).convert("RGBA"))
    v02 = trim(Image.open(MASTERS["xiaoyu"]).convert("RGBA"))
    v01 = trim(Image.open(V01_XIAOYU).convert("RGBA"))
    # 取樣點：v02 母版外套遮罩內、離邊緣最遠的 5 點（分 5 個水平區段各取一點），而且只在 propfix 沒動到的列
    # （原圖 y<580 → 去白邊裁切後約 y<530），所以 raw、v01、v02 是同一個像素位置
    va = np.array(v02)
    hh_, ss_, vv_ = hsv_np(va[..., :3])
    jm = ((hh_ >= 345) | (hh_ <= 22)) & (ss_ >= 0.62) & (vv_ >= 0.28) & (va[..., 3] > 220)
    jm[525:] = False
    jm = ndimage.binary_opening(jm, iterations=2)
    dtj = ndimage.distance_transform_edt(jm)
    xs_j = np.nonzero(jm.any(0))[0]
    bins = np.linspace(xs_j.min(), xs_j.max(), 6).astype(int)
    pts_master = []
    for b0, b1 in zip(bins[:-1], bins[1:]):
        sub = np.zeros_like(dtj)
        sub[:, b0:b1] = dtj[:, b0:b1]
        yy_, xx_ = np.unravel_index(np.argmax(sub), sub.shape)
        if sub[yy_, xx_] >= 14:   # 離線條與邊緣 ≥14 px（舞台 5×5 取樣約等於母版 17×17）
            pts_master.append((int(xx_), int(yy_)))
    layer = np.array(sc["layers"]["xiaoyu"])
    s = inf["scale"]
    hgt = inf["height"]
    w2 = round(v02.width * s)
    out = []
    # 由母版座標換到畫面座標：縮放 → 鏡像 → 繞腳底傾斜
    piv_local = np.array([w2 / 2, hgt])
    th = math.radians(lay["lean"])
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    for (u, v) in pts_master:
        q = np.array([u * s, v * s])
        if lay["mirror"]:
            q[0] = w2 - q[0]
        q = R @ (q - piv_local) + np.array([lay["cx"] * W, lay["feet"]])
        x, y = int(round(q[0])), int(round(q[1]))
        stage_px = np.median(final_rgb[y - 2:y + 3, x - 2:x + 3].reshape(-1, 3), 0)
        r = int(round(2 / s))

        def mpatch(im):
            a = np.array(im.convert("RGB"))
            return np.median(a[v - r:v + r + 1, u - r:u + r + 1].reshape(-1, 3), 0)
        raw_px, v02_px, v01_px = mpatch(raw), mpatch(v02), mpatch(v01)
        L = lambda c: srgb_to_lab(np.array(c, float)).tolist()  # noqa: E731
        out.append(dict(master_uv=[u, v], stage_xy=[x, y],
                        stage_hex="#%02X%02X%02X" % tuple(stage_px.round().astype(int)),
                        raw_hex="#%02X%02X%02X" % tuple(raw_px.round().astype(int)),
                        v02_hex="#%02X%02X%02X" % tuple(v02_px.round().astype(int)),
                        v01_hex="#%02X%02X%02X" % tuple(v01_px.round().astype(int)),
                        dE00_stage_vs_raw=round(delta_e2000(L(stage_px), L(raw_px)), 2),
                        dE00_stage_vs_v02=round(delta_e2000(L(stage_px), L(v02_px)), 2),
                        dE00_v01_vs_raw=round(delta_e2000(L(v01_px), L(raw_px)), 2)))
    # 外套整體中位數（色票）
    def jacket_median(im):
        a = np.array(im.convert("RGBA"))
        h, s_, v = hsv_np(a[..., :3])
        m = ((h >= 345) | (h <= 22)) & (s_ >= 0.62) & (v >= 0.28) & (a[..., 3] > 220)
        m[: int(0.25 * a.shape[0])] = False
        m[int(0.52 * a.shape[0]):] = False
        return np.median(a[..., :3][m], 0)
    sw = {}
    for tag, im in (("基準（原始生成 raw）", raw), ("第 1 輪壓暗版 v01", v01), ("第 2 輪 v02（還原基準＋去烘焙光影）", v02)):
        c = jacket_median(im)
        lab = srgb_to_lab(c)
        sw[tag] = dict(hex="#%02X%02X%02X" % tuple(c.round().astype(int)), L_star=round(float(lab[0]), 1),
                       rel_lum=round(float(rel_lum(c)), 4), proj_v2_lum=round(float(rel_lum(projector(c[None, None, :], "v2")[0, 0])), 4))
    cm = costume_masks(sc)["xiaoyu"]["橘紅外套"]["mask"]
    c = np.median(final_rgb[cm], 0)
    lab = srgb_to_lab(c)
    sw["舞台合成 stage_composite_v02（同一件外套）"] = dict(hex="#%02X%02X%02X" % tuple(c.round().astype(int)), L_star=round(float(lab[0]), 1),
                                                   rel_lum=round(float(rel_lum(c)), 4))
    return out, sw


def swatch_sheet(points, sw, path):
    f1, f2, f3 = lfont(30), lfont(22), lfont(18)
    img = Image.new("RGB", (1500, 760), (238, 234, 226))
    d = ImageDraw.Draw(img)
    d.text((24, 18), "小宇外套：恢復基準橘紅（色票＋明度）與 stage／raw 母版同位置色差", font=f1, fill=(30, 30, 30))
    x = 24
    for tag, v in sw.items():
        hexv = v["hex"]
        col = tuple(int(hexv[i:i + 2], 16) for i in (1, 3, 5))
        d.rectangle([x, 80, x + 330, 250], fill=col, outline=(40, 40, 40), width=2)
        d.text((x, 262), tag, font=f3, fill=(30, 30, 30))
        d.text((x, 290), f"{hexv}  L* {v['L_star']}", font=f2, fill=(30, 30, 30))
        d.text((x, 320), f"相對亮度 {v['rel_lum']}" + (f"｜投影 v2 {v['proj_v2_lum']}" if "proj_v2_lum" in v else ""), font=f3, fill=(30, 30, 30))
        x += 365
    y = 380
    d.text((24, y), "同位置色差（CIEDE2000；母版胸口一帶 5 點，stage 取 5×5、母版取對應面積中位數）", font=f2, fill=(30, 30, 30))
    y += 40
    hdr = ["母版座標", "stage 座標", "stage", "raw 基準", "v02", "ΔE00 stage↔raw", "ΔE00 stage↔v02", "ΔE00 v01↔raw（第 1 輪）"]
    xs = [24, 170, 320, 450, 580, 710, 930, 1150]
    for xx, h in zip(xs, hdr):
        d.text((xx, y), h, font=f3, fill=(120, 60, 20))
    y += 30
    for p in points:
        vals = [str(tuple(p["master_uv"])), str(tuple(p["stage_xy"])), p["stage_hex"], p["raw_hex"], p["v02_hex"],
                f"{p['dE00_stage_vs_raw']:.2f}", f"{p['dE00_stage_vs_v02']:.2f}", f"{p['dE00_v01_vs_raw']:.2f}"]
        for xx, v in zip(xs, vals):
            d.text((xx, y), v, font=f3, fill=(30, 30, 30))
        for xx, hx in ((300, p["stage_hex"]), (430, p["raw_hex"]), (560, p["v02_hex"])):
            col = tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))
            d.rectangle([xx, y + 2, xx + 16, y + 18], fill=col)
        y += 30
    d.text((24, y + 16), "說明：stage 與 raw 的差異只來自「去除烘焙光影」（該點原本若在暗面會被拉回固有色）與縮放取樣；舞台調色不動角色。", font=f3, fill=(60, 60, 60))
    img.save(path)


def table_sheet(rows, samples, final, path, outline):
    f1, f2, f3 = lfont(28), lfont(19), lfont(16)
    thumb_w = 960
    th = final.resize((thumb_w, int(thumb_w * H / W)), Image.LANCZOS).convert("RGB")
    dd = ImageDraw.Draw(th)
    k = thumb_w / W
    for idx, (cx, cy), (bx, by) in samples:
        for (x, y), col in (((cx, cy), (255, 40, 40)), ((bx, by), (40, 120, 255))):
            dd.rectangle([x * k - 4, y * k - 4, x * k + 4, y * k + 4], outline=col, width=2)
        dd.line([cx * k, cy * k, bx * k, by * k], fill=(255, 255, 0), width=1)
        dd.text((cx * k + 5, cy * k - 16), str(idx), font=lfont(15), fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
    hrow = 30
    img = Image.new("RGB", (1900, 120 + th.height + 40 + hrow * (len(rows) + 8)), (36, 36, 38))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "逐色對比量測表 v02（角色主色 × 實際站位背景；WCAG 相對亮度比）", font=f1, fill=(240, 240, 240))
    d.text((20, 54), "紅框＝服裝取樣點（10×10），藍框＝背景取樣點（10×10），黃線連結；數字＝表格列號。「環帶」＝該色靠外緣部分往外 6–34 px 的景板（含影子，不含其他角色、繩、字幕）。", font=f3, fill=(200, 200, 200))
    img.paste(th, (20, 84))
    y = 84 + th.height + 20
    hdr = ["#", "角色", "服裝色", "主色", "服裝 HEX（原圖）", "取樣座標 服裝→背景", "原圖 環帶中位", "投影v1 環帶中位", "投影v2 環帶中位", "投影v2 最差(p10/p90)", "投影v2 10×10", "低對比 環帶中位"]
    xs = [20, 60, 150, 290, 350, 520, 760, 900, 1050, 1200, 1390, 1530]
    for x, h in zip(xs, hdr):
        d.text((x, y), h, font=f3, fill=(255, 220, 120))
    y += hrow
    for i, r in enumerate(rows, 1):
        if not r.get("touches_background"):
            vals = [str(i), r["character"], r["color"], "●" if r["main"] else "", "—", "不接觸背景"]
        else:
            o, p1, p2, lc = r["original"], r["proj_v1"], r["proj_v2"], r["lowc"]

            def fmt(v):
                return f"{v:.2f}"
            vals = [str(i), r["character"], r["color"], "●" if r["main"] else "", o["costume_hex"],
                    f"({r['sample_costume_xy'][0]},{r['sample_costume_xy'][1]})→({r['sample_bg_xy'][0]},{r['sample_bg_xy'][1]})",
                    fmt(o["contrast_median"]), fmt(p1["contrast_median"]), fmt(p2["contrast_median"]), fmt(p2["contrast_worst"]),
                    fmt(p2["sample_contrast_10x10"]), fmt(lc["contrast_median"])]
        for j, (x, v) in enumerate(zip(xs, vals)):
            col = (235, 235, 235)
            if j in (8, 9, 10) and r.get("touches_background"):
                try:
                    col = (120, 230, 120) if float(v) >= 3 else (255, 120, 110)
                except ValueError:
                    pass
            d.text((x, y), v, font=f3, fill=col)
        y += hrow
    y += 10
    d.text((20, y), "外輪廓（深色內描線＋卡紙側邊，外緣 2–6 px 最暗 20%）對相鄰景板，投影 v2：" +
           "；".join(f"{k} {v['contrast']:.2f}:1" for k, v in outline.items()), font=f3, fill=(200, 200, 200))
    y += 26
    d.text((20, y), "綠＝≥3:1；紅＝<3:1。淺色服裝（黃上衣、米色襯衫、卡其短褲）與深色主色無法同時對同一面景板 ≥3:1（見 contrast_v02.json 的 conflict_note）。", font=f3, fill=(200, 200, 200))
    img.save(path)


def letterbox_43(final_nosub, lines, px_1080, out_w, out_h):
    """4:3：舞台靠上對齊（寬度貼齊），下方黑邊放兩行字幕；字級以輸出畫面高換算（px_1080 × out_h / 1080）。"""
    stage_h = round(out_w * 9 / 16)
    img = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
    img.alpha_composite(final_nosub.resize((out_w, stage_h), Image.LANCZOS).convert("RGBA"), (0, 0))
    px = round(px_1080 * out_h / 1080)
    band = out_h - stage_h
    sub = subtitle_block(img, lines, px, out_w - 40, band, out_w / 2, stage_h + band / 2 + (px * 1.28 * len(lines) + 2 * px * 0.26) / 2,
                         strip=False)
    return img.convert("RGB"), dict(sub, stage_rows=[0, stage_h], black_band_rows=[stage_h, out_h], band_fraction=round(band / out_h, 3),
                                    px_equiv_1080=round(px * 1080 / out_h, 1))


def scene_single(pose, head, height=820, feet=980, cx=0.5):
    """只有阿樂叔叔的小場景（意圖與受力演示用）。"""
    stage_raw = np.array(Image.open(STAGE_BG).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    graded, _ = stage_grade(stage_raw)
    lay = dict(LAYOUT["ale"], cx=cx, feet=feet)
    layer, to_stage, inf = place_ale(pose, head, lay=lay, height=height)
    a = np.array(layer)[..., 3]
    shaded = multiply_shadow(graded.copy(), char_shadow(a, lay, feet))
    canvas = Image.fromarray(np.clip(shaded, 0, 255).astype(np.uint8)).convert("RGBA")
    canvas.alpha_composite(card_edge(layer))
    canvas.alpha_composite(layer)
    return dict(canvas=canvas, alphas={"ale": a}, info={"ale": inf}, to_stage=to_stage, pose=pose, head=head, lay_ale=lay)


def intent_force_demo(path):
    """「意圖與受力」三格：① 想揮手（線鬆）② 線繃緊、手停住 ③ 手腕被拉偏、膝蓋被提、表情困惑。
    只畫阿樂叔叔與線（繩路用和主合成同一套自動避開手、臉、綁帶的規則），不靠字幕也看得懂。"""
    poses = [
        ("① 想揮手（劇本：笑著想揮手）：手往上抬，線還鬆", {"upper_arm_r": 150, "forearm_r": 18, "hand_r": 8, "upper_arm_l": -21, "forearm_l": -6}, "smile", "slack"),
        ("② 線繃緊：手停在半空，臉換成困惑", {"upper_arm_r": 118, "forearm_r": 38, "hand_r": -40, "upper_arm_l": -21, "forearm_l": -6, "head": -2}, "worried", "taut"),
        ("③ 手腕被拉到旁邊、膝蓋被提：需要幫忙", dict(ALE_POSE), "worried", "taut"),
    ]
    cw, chh = 600, 760
    sheet = Image.new("RGB", (cw * 3 + 40, chh + 120), (36, 36, 38))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), "意圖與受力（a2_c002）：同一位阿樂叔叔分件 rig 的三個瞬間；線只扣腕背、肘外、膝前，往上出畫面，不畫操控者", font=lfont(24), fill=(240, 240, 240))
    info = []
    for i, (title, pose, head, mode) in enumerate(poses):
        sc = scene_single(pose, head)
        ropes = add_strings(sc, mode=mode)
        info.append({k: (v["attach_point"], v["min_clearance_px_to_hands_face_bow_kids"]) for k, v in ropes.items()})
        cwid = int(H * cw / chh)
        x0 = int(W / 2 - cwid / 2)
        crop = sc["canvas"].crop((x0, 0, x0 + cwid, H)).convert("RGB").resize((cw, chh), Image.LANCZOS)
        sheet.paste(crop, (10 + i * (cw + 10), 56))
        d.text((16 + i * (cw + 10), 56 + chh + 14), title, font=lfont(21), fill=(240, 240, 240))
    sheet.save(path)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "review/G2"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sc = build_scene()
    add_strings(sc)
    nosub = sc["canvas"].copy()
    nosub.convert("RGB").save(out / "stage_composite_nosub_v02.png")
    final = sc["canvas"].copy()
    strip_bottom = H - 22
    sub = subtitle_block(final, SUB_LINES, SUB_PX, W - 200, 400, W / 2, strip_bottom)
    sub["ink_height_px_measured"] = [ink_height(final, b) for b in sub["line_boxes"]]
    sub["text_vs_strip"] = text_contrast(final, sub["strip"], sub["line_boxes"])
    final_rgb_img = final.convert("RGB")
    final_rgb_img.save(out / "stage_composite_v02.png")
    final_rgb = np.array(final_rgb_img)
    k43, sub43 = letterbox_43(nosub, SUB_LINES, SUB_PX, 1440, 1080)
    k43.save(out / "stage_composite_43_v02.png")
    sub43["ink_height_px_measured"] = [ink_height(k43, b) for b in sub43["line_boxes"]]
    sub43["text_vs_band"] = text_contrast(k43, sub43["strip"], sub43["line_boxes"])
    k768, sub768 = letterbox_43(nosub, SUB_LINES, SUB_PX, 1024, 768)
    k768.save(out / "stage_composite_1024x768_v02.png")
    sub768["ink_height_px_measured"] = [ink_height(k768, b) for b in sub768["line_boxes"]]
    # 景板調色對照
    cmp_ = Image.new("RGB", (W, H // 2 + 40), (36, 36, 38))
    cmp_.paste(Image.fromarray(sc["stage_raw"].astype(np.uint8)).resize((W // 2 - 10, H // 2 - 5)), (0, 40))
    cmp_.paste(Image.fromarray(np.clip(sc["graded"], 0, 255).astype(np.uint8)).resize((W // 2 - 10, H // 2 - 5)), (W // 2 + 10, 40))
    dc = ImageDraw.Draw(cmp_)
    dc.text((10, 8), "景板原圖 bg-square_v02（生成，未修改）", font=lfont(22), fill=(240, 240, 240))
    dc.text((W // 2 + 20, 8), "舞台調色後：遠景降彩 ×%.2f；表演區洗光只提亮淺色低彩度的牆面與地面（y≥%d，提亮 %.0f%%）；不整體抬黑" %
            (FAR_DESAT, WASH["top"], WASH["lift"] * 100), font=lfont(18), fill=(240, 240, 240))
    cmp_.save(out / "stage_wash_compare_v02.png")
    rows, samples, outline = measure(sc, final_rgb)
    ropes = rope_checks(sc, np.array(nosub.convert("RGB")))
    jpts, jsw = jacket_delta(sc, np.array(nosub.convert("RGB")))
    swatch_sheet(jpts, jsw, out / "jacket_deltaE_v02.png")
    table_sheet(rows, samples, final, out / "contrast_table_v02.png", outline)
    demo_info = intent_force_demo(out / "intent_force_demo_v02.png")
    # 外套若加深（同色相、保留彩度）時的投影對比：只做試算，不改母版
    base = np.array([int(jsw["第 2 輪 v02（還原基準＋去烘焙光影）"]["hex"][i:i + 2], 16) for i in (1, 3, 5)], float)
    lab = srgb_to_lab(base)
    xy_row = [r for r in rows if r["character"] == "小宇" and r["color"] == "橘紅外套"][0]
    ring_l = xy_row["proj_v2"]["ring_median_lum"]
    trial = []
    for dL in (-6, -10, -14):
        l2 = lab.copy()
        l2[0] += dL
        c2 = lab_to_srgb(l2[None, None, :])[0, 0]
        pl = float(rel_lum(projector(c2[None, None, :], "v2")[0, 0]))
        trial.append(dict(dL=dL, hex="#%02X%02X%02X" % tuple(c2.round().astype(int)), proj_v2_lum=round(pl, 4),
                          contrast_vs_same_ring=round(contrast(pl, ring_l), 2)))
    report = dict(
        version="v02", scene="a2_c002「線落下來」：阿樂叔叔想揮手、手被拉偏；小晴往前「叔叔，小心！」、小宇退半步",
        note="WCAG 相對亮度比。投影 v1＝第 1 輪參數；投影 v2＝第 2 輪加強版（彩度×0.65、黑位 0.18、白位 0.87：黑位相對亮度 0.027、最亮 0.729）。"
             "低對比＝CSS contrast(50%)（近似 Chrome DevTools Reduced contrast）。環帶＝該服裝色靠外緣部分往外 6–34 px 的景板（含影子，不含角色、繩、字幕）。",
        stage_grade=dict(far_desat=FAR_DESAT, wash=WASH, shadow=SHADOW, note="舞台調色只動景板；角色像素直接取自 v02 母版／rig。"),
        layout=LAYOUT, ale_pose={k: (list(v) if isinstance(v, tuple) else v) for k, v in ALE_POSE.items()},
        worried_head_alignment=sc["info"]["ale"]["head"],
        per_color=rows, outline_vs_background_proj_v2=outline, ropes=ropes,
        subtitle=dict(**{"16x9_1920x1080": sub, "4x3_1440x1080": sub43, "4x3_1024x768": sub768}, text=SUB_LINES,
                      rule="v1.2 §16.2：字身 64–72 px@1080（取 70）；每行 ≤16 字、最多兩行；4:3 依 §16.1 舞台靠上、下方黑邊放字幕，不縮字"),
        jacket=dict(swatches=jsw, same_position_dE00=jpts, deeper_trial_not_applied=trial),
        intent_force_demo=dict(file="intent_force_demo_v02.png", ropes_per_panel=demo_info),
        conflict_note=("數學限制：在投影 v2 下，景板最亮約 0.729、最暗約 0.027。服裝色亮度 L 要對同一面景板 ≥3:1，景板須 ≥3L+0.1 或 ≤(L+0.05)/3−0.05。"
                       "湖水綠（L≈0.16）與深藍（≈0.10）只能靠很亮的景板達標；芥末黃（≈0.37）、米色襯衫（≈0.55）、卡其（≈0.25）只能靠很暗的景板達標，"
                       "兩類顏色不可能同時對同一塊相鄰背景 ≥3:1。基準橘紅外套（L≈0.21）需要景板 ≥0.72，超過投影 v2 的白位上限，"
                       "所以在不改母版服色的前提下無法達到 3:1；加深外套的試算見 jacket.deeper_trial_not_applied（未套用，待驗收決定）。"),
    )
    (out / "contrast_v02.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    print(json.dumps(dict(sub=sub["ink_height_px_measured"], sub43=sub43, ropes={k: (v["attach_point"], v["min_clearance_px_to_hands_face_bow_kids"], v["tilt_deg_from_vertical"], v["samples_over_hand"], v["samples_over_face"], v["crosses_other_rope"]) for k, v in ropes.items()},
                          per_color=[(r["character"], r["color"], r.get("proj_v2", {}).get("contrast_median"), r.get("proj_v2", {}).get("contrast_worst")) for r in rows]),
                     ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
