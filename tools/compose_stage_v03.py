"""舞台合成試作 v03（G2 第 3 輪，依第 2 輪重驗意見修正；v02 版本保留在 tools/compose_stage_v02.py）。

用法：
  /opt/anaconda3/bin/python3 tools/compose_stage.py [--out-dir review/G2]
輸出（全部帶 _v03，不覆寫前兩輪）：
  stage_composite_v03.png            1920×1080（16:9，含字幕）
  stage_composite_nosub_v03.png      無字幕版（量測用）
  stage_composite_43_v03.png         1440×1080（4:3；舞台靠上、下方 25% 黑邊放兩行字幕）
  stage_composite_1024x768_v03.png   4:3 投影機原生解析度
  stage_layers_v03.png               分層卡紙景片拆解圖（遠山、後排建築、前排騎樓、樹、花台各自獨立＋側邊厚度）
  stage_grade_compare_v03.png        舞台調色前後對照（只在遠山與天空降彩；不洗白表演區）
  stage_feet_closeup_v03.png         腳部接觸影局部放大（三人）
  contrast_v03.json / contrast_table_v03.png   逐色對比（原圖／投影 v1／v2／低對比／灰階；中位數＋p10＋10×10 取樣座標）
  intent_force_demo_v03.png          「意圖與受力」三格（膝繩固定扣右膝、近乎垂直出畫面）

規則：
- 主光左上前方 45°：所有景片的投影與角色落影都往右下；景片離後層越遠，影子偏移越大、越柔。
- 景片＝獨立卡紙層：每層都有右下側的卡紙厚度（深牛皮色）與左上切口受光細線，並在後一層投下柔影。
- 對比解法＝局部背板（不整面提亮）：騎樓陰影內牆（深暖灰）在角色上半身後方；小宇身後是更暗的門洞；
  阿樂與小晴的下半身前方站在淺色洗石子花台前；地面維持暖黃橘與紙紋，前緣略壓暗。
- 降彩只做在天空與遠山。角色固有色不調（只做縮放與擺放）。
- 角色：白色紙芯邊外再加 3 px 深色卡紙側邊（偏右下）；落影強度 0.22–0.28＋腳底接地影。
- 操偶線：淡灰平面紙繩（紙纖維、兩側深灰邊線、左側受光邊；不做扭絞紋），只扣右腕背、右肘外、左膝前（a2_c001 細線在右腕），
  腕／肘兩條垂直往上；膝線從膝前紙環近乎垂直往上、走身體外側，和手、臉、腕 ≥30 px、和前臂與圍裙 ≥24 px。
- 字幕：字身 70 px@1080、每行 ≤16 字、兩行；紙條整條在 90% 安全框內（下緣 ≤1026 列），底色壓暗到投影 v2 下約 7:1。
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
from projsim import projector, low_contrast, grayscale  # noqa: E402
import rig_ale_v03 as rig  # noqa: E402

W, H = 1920, 1080
GEN = ROOT / "assets/generated"
LAYER_FILES = {
    "sky": GEN / "bg-square-sky_v03.png",
    "mountains": GEN / "bg-square-mountains_v03.png",
    "backrow": GEN / "bg-square-backrow_v03.png",
    "arcade": GEN / "bg-square-arcade_v03.png",
    "trees": GEN / "bg-square-trees_v03.png",
    "planters": GEN / "bg-square-planters_v03.png",
}
KID_FILES = {
    "xiaoqing": GEN / "chr-xiaoqing_pose-reach-worried_v03.png",
    "xiaoyu": GEN / "chr-xiaoyu_pose-stepback-surprised_v03.png",
}
RAW_XIAOYU = ROOT / "review/G2/raw/master_xiaoyu.png"
MASTER_XIAOYU = GEN / "chr-xiaoyu_master_v02.png"

ADULT_H = 640                 # 阿樂叔叔站姿身高 px@1080（含白邊）
CHILD_RATIO = 0.65
Y_BASE = 742                  # 騎樓與地面的交界
SUB_LINES = ["咦？我想揮手……", "手怎麼跑到旁邊去了？"]   # 劇本 a2_c002_01（阿樂叔叔），在詞語邊界斷行
SUB_PX = 70
SAFE = (96, 54, 1824, 1026)   # 90% 安全框
FONT_CANDIDATES = [
    ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
]
LABEL_FONT = FONT_CANDIDATES[0]

# 站位（a2_c002）：阿樂在左（危險固定從左側來），孩子在右（安全側）、面向阿樂；三人腳底在不同景深
# depth＝離背板的距離（影子偏移、柔度用）
LAYOUT = {
    "ale": dict(cx=610, feet=788, height=ADULT_H, depth=1.0, shadow=0.26),
    "xiaoqing": dict(cx=925, feet=806, height=ADULT_H * CHILD_RATIO * 1.06, depth=2.3, shadow=0.20),   # 最前面、離背板最遠 → 影子偏移最大、最柔
    "xiaoyu": dict(cx=1170, feet=760, height=ADULT_H * CHILD_RATIO * 0.96, depth=0.8, shadow=0.28),
}
ALE_POSE = dict(rig.POSES["pulled"])
SHADOW = dict(offset=(60, 45), sigma=11.0, contact=0.72)
FAR_DESAT = 0.78
WARM = np.array([1.0, 0.985, 0.94], np.float32)     # 暖色日光（近景景片）
WALL = (30, 26, 23)          # 騎樓陰影內牆
DOORWAY = (6, 5, 5)          # 小宇身後門洞
GROUND = ((206, 160, 104), (178, 133, 84))   # 地面：後緣 → 前緣（暖黃橘，前緣略壓暗）
SHADOW_RGB = np.array([58, 44, 36], np.float32) / 255.0
KRAFT = (118, 94, 70)        # 卡紙側邊（背光側）
BACK = dict(base_gap=24, xq_top=0.40, lim_gap=40, ale_above_waist=30)   # 局部背板：花台底離腳 base_gap px；小晴花台上緣＝身高比例 xq_top；A 花台右界離黃上衣 lim_gap px
LAYOUT_CACHE = {}
PLANTER_LIFT = 0.18          # 局部亮背板花台：石材往紙白提亮（255−(255−c)×0.18），紋理保留
CUT_HI = (244, 232, 208)     # 切口受光細線

COSTUMES = {
    # 色相範圍（度）、飽和度、明度（HSV 0–1）、是否主色、身高帶（由頭頂算起的比例範圍）
    "ale": [("深藍圍裙", (195, 255), 0.18, 1.0, 0.10, 0.62, True, (0.0, 1.0)),
            ("米色襯衫", (14, 50), 0.04, 0.46, 0.55, 1.0, False, (0.0, 1.0)),
            ("橄欖褐長褲", (25, 62), 0.28, 1.0, 0.10, 0.58, False, (0.55, 1.0))],
    "xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.28, 1.0, 0.12, 0.90, True, (0.0, 1.0)),
                 ("芥末黃上衣", (32, 56), 0.55, 1.0, 0.55, 1.0, False, (0.18, 0.60)),
                 ("深棕頭髮", (0, 45), 0.20, 0.75, 0.10, 0.42, False, (0.0, 0.30))],
    "xiaoyu": [("橘紅外套", (345, 22), 0.62, 1.0, 0.28, 1.0, True, (0.15, 0.75)),
               ("卡其短褲", (22, 46), 0.28, 0.75, 0.40, 0.88, False, (0.50, 0.85)),
               ("深棕頭髮", (0, 45), 0.20, 0.80, 0.08, 0.40, False, (0.0, 0.30))],
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


def hexs(c):
    c = np.asarray(c).round().astype(int)
    return "#%02X%02X%02X" % tuple(c[:3])


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


def grain(shape, seed, amp=5.0, sigma=0.9):
    rng = np.random.default_rng(seed)
    g = ndimage.gaussian_filter(rng.normal(0, 1, shape), sigma)
    g2 = ndimage.gaussian_filter(rng.normal(0, 1, shape), 18)
    return (g / (g.std() + 1e-6) * amp + g2 / (g2.std() + 1e-6) * amp * 0.5).astype(np.float32)


# ---------------------------------------------------------------- 景片
def load_rgba(path):
    a = np.array(Image.open(path).convert("RGBA")).astype(np.float32)
    a[..., 3] = np.where(a[..., 3] < 24, 0, a[..., 3])
    return a


def components(alpha, min_frac=0.01):
    m = alpha > 128
    lb, n = ndimage.label(m)
    out = []
    for i in range(1, n + 1):
        mm = lb == i
        if mm.sum() < m.size * min_frac:
            continue
        ys, xs = np.nonzero(mm)
        out.append(dict(mask=mm, box=(xs.min(), ys.min(), xs.max() + 1, ys.max() + 1), area=int(mm.sum())))
    return sorted(out, key=lambda c: c["box"][0])


def place(src, scale, x, y, crop_box=None, mask=None):
    """把 RGBA（float）等比縮放 scale 後，左上角放到 (x, y)，回傳全畫面 RGBA float。"""
    a = src.copy()
    if mask is not None:
        a[..., 3] = a[..., 3] * mask
    if crop_box is not None:
        x0, y0, x1, y1 = crop_box
        a = a[y0:y1, x0:x1]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    nw, nh = max(int(round(im.width * scale)), 1), max(int(round(im.height * scale)), 1)
    im = im.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(im, (max(int(round(x)), 0), max(int(round(y)), 0)),
                        (max(-int(round(x)), 0), max(-int(round(y)), 0)))
    return np.array(out).astype(np.float32)


def shift(a, dy, dx):
    return ndimage.shift(a, (dy, dx), order=1, mode="constant")


def cast_shadow(base, alpha, gap, strength):
    """景片投在後層的柔影：主光左上 → 往右下；gap 越大偏移越大、越柔。"""
    a = alpha / 255.0
    off = (gap * 0.75, gap)
    sh = ndimage.gaussian_filter(shift(a, *off), 1.2 + gap * 0.45) * strength
    sh = np.clip(sh - a * strength, 0, 1) + np.minimum(sh, a * strength) * 0  # 只在本層外側
    m = sh[..., None]
    return base * (1 - m + m * SHADOW_RGB)


def composite_flat(base, layer, gap=0.0, strength=0.0, thick=0.0, shadow=True):
    """景片：先投影到後層，再畫右下側卡紙厚度與左上切口受光細線，最後貼上本層。"""
    a = layer[..., 3]
    if shadow and strength > 0:
        base = cast_shadow(base, a, gap, strength)
    an = a / 255.0
    if thick > 0:
        side = np.clip(np.maximum(shift(an, thick * 0.8, thick), shift(an, thick * 0.4, thick * 0.5)) - an, 0, 1)
        col = np.array(KRAFT, np.float32)
        base = base * (1 - side[..., None]) + col * side[..., None]
    out = base * (1 - an[..., None]) + layer[..., :3] * an[..., None]
    if thick > 0:
        hi = np.clip(an - shift(an, -1.2, -1.2), 0, 1) * 0.55
        out = out * (1 - hi[..., None]) + np.array(CUT_HI, np.float32) * hi[..., None]
    return out


def desat(rgb, k):
    g = rgb.mean(-1, keepdims=True)
    return g + (rgb - g) * k


def ground_layer():
    """地面：暖黃橘紙，後緣到前緣漸暗（前景地面保留暗部），紙纖維＋大尺度斑駁；後緣是手撕毛邊。"""
    yy = np.arange(H, dtype=np.float32)[:, None]
    t = np.clip((yy - Y_BASE) / (H - Y_BASE), 0, 1)
    c0, c1 = np.array(GROUND[0], np.float32), np.array(GROUND[1], np.float32)
    rgb = c0 * (1 - t[..., None]) + c1 * t[..., None]
    rgb = np.broadcast_to(rgb, (H, W, 3)).copy()
    rgb += grain((H, W), 21, 4.0)[..., None]
    rng = np.random.default_rng(5)
    edge = Y_BASE - 2 + ndimage.gaussian_filter1d(rng.normal(0, 1, W), 3) * 1.6
    a = np.clip(yy - edge[None, :] + 0.5, 0, 1) * 255
    return np.dstack([rgb, a]).astype(np.float32)


def wall_layer(box, doorway_box):
    """騎樓陰影內牆（深暖灰紙）＋店門門板（略有深淺），小宇身後一扇開著的門洞（更暗）。"""
    x0, y0, x1, y1 = box
    rgb = np.zeros((H, W, 3), np.float32) + np.array(WALL, np.float32)
    rgb += grain((H, W), 31, 1.6)[..., None]
    a = np.zeros((H, W), np.float32)
    a[y0:y1, x0:x1] = 255
    # 店門門板（低對比：比牆暗 6、門框亮 8），避開門洞
    d = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(d)
    fr = Image.new("L", (W, H), 0)
    dfr = ImageDraw.Draw(fr)
    span = x1 - x0
    for k in range(4):
        dx0 = x0 + 40 + k * span // 4
        dx1 = dx0 + span // 4 - 80
        if doorway_box and not (dx1 < doorway_box[0] - 30 or dx0 > doorway_box[2] + 30):
            continue
        dr.rectangle([dx0, y0 + 90, dx1, y1], fill=255)
        dfr.rectangle([dx0, y0 + 90, dx1, y1], outline=255, width=3)
        for j in range(1, 3):
            xx = dx0 + j * (dx1 - dx0) // 3
            dfr.line([xx, y0 + 96, xx, y1], fill=255, width=2)
    dm = np.array(d, np.float32) / 255
    fm = np.array(fr, np.float32) / 255
    rgb -= dm[..., None] * 6
    rgb += fm[..., None] * 8
    if doorway_box:
        bx0, by0, bx1, by1 = doorway_box
        door = Image.new("L", (W, H), 0)
        ImageDraw.Draw(door).rounded_rectangle([bx0, by0, bx1, by1 + 60], radius=(bx1 - bx0) // 2, fill=255)
        door = np.array(door, np.float32) / 255
        door = ndimage.gaussian_filter(door, 0.8)
        rgb = rgb * (1 - door[..., None]) + (np.array(DOORWAY, np.float32) + grain((H, W), 33, 0.6)[..., None]) * door[..., None]
        # 門框（略亮的細框，在門洞外 4–10 px；門洞外 34 px 內不放亮線）
    return np.dstack([np.clip(rgb, 0, 255), a]).astype(np.float32)


# ---------------------------------------------------------------- 角色
def trim(im):
    arr = np.array(im)
    arr[..., 3] = np.where(arr[..., 3] < 24, 0, arr[..., 3])
    im = Image.fromarray(arr, "RGBA")
    ys, xs = np.nonzero(arr[..., 3] > 16)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def place_kid(key, lay):
    im = trim(Image.open(KID_FILES[key]).convert("RGBA"))
    s = lay["height"] / im.height
    im2 = im.resize((round(im.width * s), round(lay["height"])), Image.LANCZOS)
    a = np.array(im2)[..., 3] > 128
    # 腳底中心：最低 3% 列的不透明像素水平中心
    ys, xs = np.nonzero(a)
    low = ys >= ys.max() - max(int(0.03 * im2.height), 3)
    fx = xs[low].mean()
    x = round(lay["cx"] - fx)
    y = round(lay["feet"] - im2.height)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(im2, (x, y))
    return layer, dict(scale=s, origin=(x, y), size=im2.size, src_size=im.size)


def place_ale(pose, head="worried", lay=None, cache={}):
    lay = lay or LAYOUT["ale"]
    key = (json.dumps(pose, sort_keys=True), head)
    if key not in cache:
        r = rig.Rig(head=head)
        img, pt, Mw, pm = r.render(pose, outline=True, masks=True)
        rest_img, _, _, _ = rig.Rig().render({}, outline=True)
        cache[key] = (r, img, pt, pm, rest_img)
    r, img, pt, pm, rest_img = cache[key]
    ra = np.array(rest_img)[..., 3] > 128
    ys, xs = np.nonzero(ra)
    top, bot = ys.min(), ys.max()
    s = lay["height"] / (bot - top)
    cx_rig = (xs.min() + xs.max()) / 2
    big = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    ix = int(round(lay["cx"] - cx_rig * s))
    iy = int(round(lay["feet"] - bot * s))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(big, (max(ix, 0), max(iy, 0)), (max(-ix, 0), max(-iy, 0)))
    masks = {}
    for n, m in pm.items():
        mi = Image.fromarray((m * 255).astype(np.uint8)).resize(big.size, Image.BILINEAR)
        full = Image.new("L", (W, H), 0)
        full.paste(mi, (ix, iy))
        masks[n] = np.array(full) > 127

    def to_stage(part, p):
        q = pt(part, p)
        return np.array([q[0] * s + ix, q[1] * s + iy])
    return layer, to_stage, dict(scale=s, rig=r, masks=masks, head=r.head_info)


def card_side(alpha):
    """角色白色紙芯邊外的深色卡紙側邊：外擴 2 px 一圈＋往右下再多 2 px（主光左上）。"""
    a = alpha.astype(np.float32) / 255
    d = ndimage.distance_transform_edt(a < 0.5)
    ring = np.clip(2.6 - d, 0, 1)
    sh = np.clip(shift(a, 2.2, 2.2) - a, 0, 1)
    side = np.clip(np.maximum(ring, sh) - a, 0, 1)
    out = np.zeros((H, W, 4), np.float32)
    out[..., :3] = (74, 62, 52)
    out[..., 3] = side * 235
    return out


def char_shadows(alpha, lay):
    """主光左上前方 45°：(1) 投在背板上的柔影往右下（強度 0.22–0.28，depth 越大越柔、偏移越大）；
    (2) 腳底接地影：腳底一小段輪廓往右拖成斜片後模糊，靠腳最深。"""
    a = alpha.astype(np.float32) / 255.0
    d = lay["depth"]
    off = (SHADOW["offset"][1] * d, SHADOW["offset"][0] * d)
    sig = SHADOW["sigma"] * d ** 1.4
    drop = ndimage.gaussian_filter(shift(a, *off), sig) * lay["shadow"]
    feet = lay["feet"]
    drop[int(feet + 6):, :] = 0
    ys = np.nonzero(a.max(1) > 0.5)[0]
    hgt = ys.max() - ys.min()
    # 鞋底附近（最低 5% 身高）往右拖成斜片：主光左上前方 → 地面上的影子往右（略往後）延伸；
    # 離地越高（例如被提起的腳）權重越低
    yy = np.arange(H, dtype=np.float32)[:, None]
    wgt = np.clip(1 - (feet - yy) / (hgt * 0.07), 0, 1) * (yy <= feet + 4)
    foot = a * wgt
    sl = np.zeros_like(a)
    for k in range(0, 28):
        sl = np.maximum(sl, shift(foot, -k * 0.28 + 3.0, k * 5.0) * (1 - k / 32))
    sl = np.maximum(sl, ndimage.grey_dilation(sl, size=(5, 1)) * 0.8)      # 影子略厚一點（地面透視下的薄片）
    contact = ndimage.gaussian_filter(sl, (2.6 + 1.0 * d, 4.0 + 2.0 * d)) * SHADOW["contact"]
    core = ndimage.gaussian_filter(shift(foot * (wgt > 0.75), 2.5, 3.0), 2.0) * 0.45   # 最靠腳底的深色接觸線
    return np.clip(np.maximum(drop, contact) + core, 0, 0.8)


def multiply_shadow(base, mask):
    m = mask[..., None]
    return base * (1 - m + m * SHADOW_RGB)


# ---------------------------------------------------------------- 操偶線與紙環
def draw_rope(canvas, pts, width=7.0, ss=4, seed=3):
    """淡灰平面紙繩：淡灰本體＋細紙纖維（不做扭絞紋）、兩側各 2 px 深灰邊線、左上受光邊、右側背光細線。"""
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
    ImageDraw.Draw(layer).line(seq, fill=(62, 60, 58, 255), width=int((width + 4) * ss), joint="curve")
    core = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(core).line(seq, fill=255, width=int(width * ss), joint="curve")
    rng = np.random.default_rng(seed)
    fib = ndimage.gaussian_filter(rng.normal(0, 1, (bh, bw)), (6, 1.2)) * 5 + 190
    body = np.dstack([fib - 2, fib - 4, fib - 9, np.full_like(fib, 255)])
    body = Image.fromarray(np.clip(body, 0, 255).astype(np.uint8), "RGBA")
    dd = ImageDraw.Draw(body)
    tang = np.gradient(p, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
    nor = np.stack([-tang[:, 1], tang[:, 0]], 1)
    up_left = np.array([-1.0, -1.0]) / math.sqrt(2)
    if (nor @ up_left).mean() < 0:
        nor = -nor
    hl = p + nor * width * 0.30 * ss
    dd.line([tuple(v) for v in hl], fill=(234, 232, 226, 255), width=max(int(width * 0.22 * ss), 1), joint="curve")
    sh = p - nor * width * 0.32 * ss
    dd.line([tuple(v) for v in sh], fill=(156, 154, 148, 255), width=max(int(width * 0.18 * ss), 1), joint="curve")
    body.putalpha(core)
    layer = Image.alpha_composite(layer, body)
    layer = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    canvas.alpha_composite(layer, (x0, y0))


def ring_points(center, axis, half_w):
    axis = np.asarray(axis, float) / (np.linalg.norm(axis) + 1e-9)
    n = np.array([-axis[1], axis[0]])
    R = half_w + 3.0
    r = max(R * 0.32, 3.5)
    t = np.linspace(0, 2 * np.pi, 240)
    ring = np.stack([np.cos(t) * R, np.sin(t) * r], 1)
    pts = np.array(center) + ring[:, :1] * n + ring[:, 1:] * axis
    return pts, t, R, r, n, axis


def draw_loop(canvas, center, axis, half_w, occluder, ss=4):
    """紙環：白色紙帶繞肢體一圈；後半圈被肢體擋住，前半圈壓在肢體上。"""
    pts, t, R, r, n, axis = ring_points(center, axis, half_w)
    pad = 14
    size = int(2 * (R + pad))
    big = size * ss
    back = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    front = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    c = np.array([big / 2, big / 2])
    ring = np.stack([np.cos(t) * R, np.sin(t) * r], 1)
    lp = c + (ring[:, :1] * n + ring[:, 1:] * axis) * ss
    fpts, bpts = lp[t <= np.pi], lp[t >= np.pi]
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
    return pts[t <= np.pi]


def seg_clear(p0, p1, dist_maps, skip):
    n = int(np.linalg.norm(p1 - p0) / 2) + 2
    pts = p0 + (p1 - p0) * np.linspace(0, 1, n)[:, None]
    xs = np.clip(np.round(pts[:, 0]).astype(int), 0, W - 1)
    ys = np.round(pts[:, 1]).astype(int)
    ok = (ys >= 0) & (ys < H)
    out = {}
    for k, dm in dist_maps.items():
        d = np.full(n, 1e6)
        d[ok] = dm[ys[ok], xs[ok]]
        out[k] = float(d[skip:].min()) if n > skip else 1e6
    return out, pts


def add_strings(sc, mode="taut", knee_side="l"):
    """三條操偶線：右腕背、右肘外（垂直往上），左膝前（近乎垂直、走身體外側），紙環扣住，往上出畫面。"""
    canvas = sc["canvas"]
    to_stage = sc["to_stage"]
    masks = sc["ale_masks"]
    s = sc["ale_scale"]
    Hs = rig.H * s
    occ = sc["alphas"]["ale"]
    MJ = rig.MJ
    hands = masks["hand_l"] | masks["hand_r"]
    face = masks["head"]
    wrists = np.zeros_like(hands)
    for side in ("l", "r"):
        c = to_stage(f"hand_{side}", MJ[f"wrist_{side}"])
        yy, xx = np.ogrid[:H, :W]
        wrists |= (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= (0.16 * Hs) ** 2
    forearms = masks["forearm_l"] | masks["forearm_r"]
    uppers = masks["upper_arm_l"] | masks["upper_arm_r"]
    body = occ > 60
    torso = masks["torso"]
    kids = np.zeros((H, W), bool)
    for k in ("xiaoqing", "xiaoyu"):
        if k in sc["alphas"]:
            kids |= sc["alphas"][k] > 60
    big = np.full((H, W), 1e6)
    dmap = {
        "手、臉、手腕": ndimage.distance_transform_edt(~(hands | face | wrists)),
        "前臂、上臂、圍裙與軀幹": ndimage.distance_transform_edt(~(forearms | uppers | torso)),
        "孩子": ndimage.distance_transform_edt(~kids) if kids.any() else big,
    }
    d_face_kids = {"臉": ndimage.distance_transform_edt(~face), "孩子": dmap["孩子"]}

    def along(part, p, q, frac):
        P = to_stage(part, np.array(MJ[p], float))
        Q = to_stage(part, np.array(MJ[q], float))
        return P + (Q - P) * frac, (Q - P)
    geo = {
        "wrist": along("forearm_r", "elbow_r", "wrist_r", 0.84) + (0.15 * Hs, "腕背（右）"),
        "elbow": along("upper_arm_r", "shoulder_r", "elbow_r", 0.84) + (0.24 * Hs, "肘外（右）"),
        "knee": along("thigh_" + knee_side, "hip_" + knee_side, "knee_" + knee_side, 0.97) + (0.27 * Hs, f"膝前（{'右' if knee_side == 'r' else '左'}）"),
    }

    def body_over_after_exit(line):
        xs = np.clip(np.round(line[:, 0]).astype(int), 0, W - 1)
        ys = np.round(line[:, 1]).astype(int)
        ok = (ys >= 0) & (ys < H)
        inside = np.zeros(len(line), bool)
        inside[ok] = body[ys[ok], xs[ok]]
        out_idx = np.nonzero(~inside)[0]
        if len(out_idx) == 0:
            return len(line)
        first = out_idx[0] + 3
        return int(inside[first:].sum())
    results = {}
    for name, (c, ax, hw, label) in geo.items():
        pts, t, R, r, n, axn = ring_points(c, ax, hw)
        front = pts[t <= np.pi]
        if name in ("wrist", "elbow"):
            st = front[np.argmin(front[:, 1])]                # 前緣最高點 → 垂直往上
            end = np.array([st[0], -60.0])
            cl, line = seg_clear(st, end, d_face_kids, int(0.25 * Hs / 2))
            tilt = 0.0
            over = body_over_after_exit(line)
        else:
            # 膝前：從紙環前緣「外側半圈」挑扣點，錨點往外側找，取「最接近垂直、又滿足淨距」的一條
            outer = front[front[:, 0] <= np.median(front[:, 0])] if knee_side == "r" else front[front[:, 0] >= np.median(front[:, 0])]
            best = None
            sgn = -1 if knee_side == "r" else 1
            amps = [0.0] if mode != "slack" else [16.0, 24.0, 32.0, 40.0, 50.0, 60.0, 72.0]
            for st in outer[:: max(len(outer) // 16, 1)]:
                for tilt in np.arange(0, 12.1, 0.25):
                    dx = math.tan(math.radians(tilt)) * (st[1] + 60) * sgn
                    end = np.array([st[0] + dx, -60.0])
                    found = False
                    for amp in amps:
                        line = st + (end - st) * np.linspace(0, 1, 700)[:, None]
                        if amp:
                            tt = np.linspace(0, 1, 700)[:, None]
                            line = line + np.array([sgn, 0.0]) * (np.sin(np.pi * tt) * (1 - 0.6 * tt)) * amp
                        cl = {}
                        xs_ = np.clip(np.round(line[:, 0]).astype(int), 0, W - 1)
                        ys_ = np.round(line[:, 1]).astype(int)
                        okk = (ys_ >= 0) & (ys_ < H)
                        for kk, dm in dmap.items():
                            dd_ = np.full(len(line), 1e6)
                            dd_[okk] = dm[ys_[okk], xs_[okk]]
                            cl[kk] = float(dd_[2:].min())
                        over = body_over_after_exit(line)
                        ok = cl["手、臉、手腕"] >= 30 and cl["前臂、上臂、圍裙與軀幹"] >= 24 and cl["孩子"] >= 30 and over == 0
                        if ok:
                            cand = (tilt, amp, -cl["前臂、上臂、圍裙與軀幹"], st, end, cl, over)
                            if best is None or cand[:3] < best[:3]:
                                best = cand
                            found = True
                            break
                    if found:
                        break
            if best is None:
                st = outer[0]
                tilt = 12.0
                end = np.array([st[0] + math.tan(math.radians(tilt)) * (st[1] + 60) * (-1 if knee_side == "r" else 1), -60.0])
                cl, line = seg_clear(st, end, dmap, 2)
                over = body_over_after_exit(line)
                label += "（未找到符合淨距的路徑）"
                amp = 0.0
            else:
                tilt, amp, _, st, end, cl, over = best
        if name != "knee":
            amp = 0.0
        results[name] = dict(st=st, end=end, cl=cl, tilt=float(tilt), label=label, geo=(c, ax, hw), over=over, amp=amp)
    for name, rres in results.items():
        c, ax, hw = rres["geo"]
        draw_loop(canvas, c, ax, hw, occ)
    out = {}
    for i, (name, rres) in enumerate(results.items()):
        st, end = rres["st"], rres["end"]
        pts = st + (end - st) * np.linspace(0, 1, 900)[:, None]
        if mode == "slack":
            tt = np.linspace(0, 1, 900)[:, None]
            outward = np.sign(st[0] - to_stage("torso", rig.MJ["neck"])[0]) or 1.0   # 鬆線往身體外側彎
            amp = rres["amp"] if name == "knee" else 22.0 + 6 * i
            pts = pts + np.array([outward, 0.0]) * (np.sin(np.pi * tt) * (1 - 0.6 * tt)) * amp
        draw_rope(canvas, pts, width=7.0, seed=i + 3)
        hand_px = face_px = 0
        skip = int(len(pts) * (0.25 * Hs) / max(np.linalg.norm(end - st), 1))
        q = pts[skip:]
        xs = np.clip(np.round(q[:, 0]).astype(int), 0, W - 1)
        ys = np.clip(np.round(q[:, 1]).astype(int), 0, H - 1)
        okk = q[:, 1] >= 0
        hand_px = int(hands[ys[okk], xs[okk]].sum())
        face_px = int(face[ys[okk], xs[okk]].sum())
        out[name] = dict(attach_point=rres["label"], attach=[round(float(st[0]), 1), round(float(st[1]), 1)],
                         anchor_offscreen=[round(float(end[0]), 1), -60], tilt_deg_from_vertical=round(rres["tilt"], 1),
                         min_clearance_px={k: round(v, 1) for k, v in rres["cl"].items()},
                         samples_over_hand=hand_px, samples_over_face=face_px,
                         samples_over_body_after_leaving_limb=int(rres["over"]), mode=mode,
                         slack_bow_px=round(float(rres["amp"] if name == "knee" else (22.0 + 6 * i if mode == "slack" else 0)), 1), pts=pts)
    sc["ropes"] = out
    return out


# ---------------------------------------------------------------- 字幕
def subtitle_block(canvas, lines, px, cx, bottom, strip=True, alpha=0.95):
    """兩行字幕＋深色紙條（手撕左右邊）。cx、bottom＝紙條中心 x 與下緣 y。"""
    font, fname = find_font(px)
    d0 = ImageDraw.Draw(canvas)
    bbs = [d0.textbbox((0, 0), t, font=font) for t in lines]
    lh = int(round(px * 1.28))
    tw = max(b[2] - b[0] for b in bbs)
    pad_x, pad_y = int(px * 0.6), int(px * 0.24)
    sw = tw + 2 * pad_x
    sh = lh * len(lines) + 2 * pad_y
    sx, sy = int(round(cx - sw / 2)), int(round(bottom - sh))
    if strip:
        rng = np.random.default_rng(7)
        m = np.ones((sh, sw), np.float32)
        edge = max(int(px * 0.13), 5)
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
        g = ndimage.gaussian_filter(rng.normal(0, 1, (sh, sw)), 1.2) * 3
        col = np.empty((sh, sw, 4), np.float32)
        col[..., 0], col[..., 1], col[..., 2] = 20 + g, 18 + g, 21 + g
        col[..., 3] = m * alpha * 255
        canvas.alpha_composite(Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGBA"), (sx, sy))
    d = ImageDraw.Draw(canvas)
    boxes = []
    for i, (t, bb) in enumerate(zip(lines, bbs)):
        w_ = bb[2] - bb[0]
        tx = int(cx - w_ / 2 - bb[0])
        ty = int(sy + pad_y + i * lh + (lh - (bb[3] - bb[1])) / 2 - bb[1])
        d.text((tx, ty), t, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(16, 14, 16, 255))
        boxes.append([tx + bb[0], ty + bb[1], w_, bb[3] - bb[1]])
    return dict(font=fname, px=px, strip=[sx, sy, sw, sh], strip_bottom_row=sy + sh, line_boxes=boxes,
                chars_per_line=[len(t) for t in lines], strip_alpha=alpha)


def text_contrast(img, strip_box, line_boxes):
    a = np.array(img.convert("RGB"))
    x, y, w, h = strip_box
    region = a[y:y + h, x:x + w]
    m = np.ones(region.shape[:2], bool)
    for bx, by, bw, bh in line_boxes:
        m[max(by - y - 6, 0):by - y + bh + 6, max(bx - x - 6, 0):bx - x + bw + 6] = False
    # 紙條內部（避開手撕邊）
    m[:, :12] = False
    m[:, -12:] = False
    vals = region[m]
    bg_med = np.median(vals, 0)
    bg_p90 = np.percentile(vals, 90, axis=0)
    txt = np.array([255, 255, 255], float)
    out = {}
    for tag, f in (("original", lambda c: np.asarray(c, float)),
                   ("proj_v2", lambda c: projector(np.asarray(c, np.uint8)[None, None, :], "v2")[0, 0].astype(float))):
        lt = float(rel_lum(f(txt)))
        lb, lb90 = float(rel_lum(f(bg_med.round()))), float(rel_lum(f(bg_p90.round())))
        out[tag] = dict(bg_hex=hexs(f(bg_med.round())), contrast=round(contrast(lt, lb), 2),
                        contrast_vs_bg_p90=round(contrast(lt, lb90), 2))
    return out


def ink_height(img, box):
    x, y, w, h = box
    a = np.array(img.convert("RGB"))[y:y + h, x:x + w].astype(int)
    white = (a.min(-1) > 225)
    rows = np.nonzero(white.sum(1) > 2)[0]
    return int(rows.max() - rows.min() + 1) if len(rows) else 0


# ---------------------------------------------------------------- 景板組裝
def build_set(char_boxes, info=None):
    """分層卡紙景片：天空 → 遠山 → 後排建築 → 騎樓陰影內牆（含門洞）→ 前排騎樓立面 → 樹 → 地面 → 花台。
    char_boxes：各角色的版面資訊（決定門洞與花台位置）。回傳 (景板 RGB float, 各層資訊, 各層 RGBA 供拆解圖)。"""
    L = {k: load_rgba(v) for k, v in LAYER_FILES.items()}
    rec = {}
    flats = []
    # 天空：鋪滿（等比放大到蓋住畫面），降彩
    sky = L["sky"]
    s = max(W / sky.shape[1], H / sky.shape[0])
    sky_l = place(sky, s, (W - sky.shape[1] * s) / 2, 0)
    sky_l[..., :3] = desat(sky_l[..., :3], FAR_DESAT)
    sky_l[..., 3] = 255
    base = sky_l[..., :3].copy()
    flats.append(("天空（和紙）", sky_l))
    # 遠山：寬度貼齊畫面，底緣放在 y=640，降彩
    mt = L["mountains"]
    cm = components(mt[..., 3], 0.02)
    box = (min(c["box"][0] for c in cm), min(c["box"][1] for c in cm), max(c["box"][2] for c in cm), max(c["box"][3] for c in cm))
    s = (W + 80) / (box[2] - box[0])
    mt_l = place(mt, s, -40 - box[0] * s, 582 - box[3] * s)
    mt_l[..., :3] = desat(mt_l[..., :3], FAR_DESAT)
    base = composite_flat(base, mt_l, gap=5, strength=0.16, thick=2.0)
    flats.append(("遠山（兩層撕紙）", mt_l))
    rec["mountains"] = dict(scale=round(s, 4), bottom_y=582)
    # 後排建築：放在右側（騎樓立面以外露出），底緣 y=720
    br = L["backrow"]
    cb = components(br[..., 3], 0.02)
    bx = (min(c["box"][0] for c in cb), min(c["box"][1] for c in cb), max(c["box"][2] for c in cb), max(c["box"][3] for c in cb))
    s = 1250 / (bx[2] - bx[0])
    br_l = place(br, s, 1080 - bx[0] * s, 668 - bx[3] * s)
    br_l[..., :3] *= WARM
    base = composite_flat(base, br_l, gap=8, strength=0.20, thick=3.0)
    flats.append(("後排建築", br_l))
    rec["backrow"] = dict(scale=round(s, 4), x=1080, bottom_y=668)
    # 前排騎樓立面：找出中間的拱廊開口（透明區），讓開口涵蓋 x 220–1300、上緣 ≤ 227
    ar = L["arcade"]
    fa = ar[..., 3] > 128
    ys, xs = np.nonzero(fa)
    fbox = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    hole = ~fa
    hole[: fbox[1]] = False
    lbh, nh = ndimage.label(hole)
    # 開口＝和畫面底邊相連、位於立面範圍內最大的透明區
    best = None
    for i in range(1, nh + 1):
        m = lbh == i
        yy, xx = np.nonzero(m)
        if yy.max() < ar.shape[0] - 3 or xx.min() <= fbox[0] + 2 and xx.max() >= fbox[2] - 2:
            continue
        if best is None or m.sum() > best[1].sum():
            best = (i, m)
    if best is None:
        # 沒有切空：把開口區（立面寬 10%–90%、高 42% 以下）當開口
        ow = fbox[2] - fbox[0]
        oh = fbox[3] - fbox[1]
        opening = (int(fbox[0] + 0.10 * ow), int(fbox[1] + 0.42 * oh), int(fbox[0] + 0.90 * ow), fbox[3])
        already = float((ar[opening[1]:opening[3], opening[0]:opening[2], 3] < 24).mean())
        ar[opening[1]:opening[3], opening[0]:opening[2], 3] = 0
        rec["arcade_note"] = (f"開口取立面寬 10%–90%、高 42% 以下；生成圖在此範圍已有 {already * 100:.0f}% 透明"
                              "（開口和柱腳下方的透明區相連，所以改用固定比例框定開口）")
    else:
        yy, xx = np.nonzero(best[1])
        opening = (xx.min(), yy.min(), xx.max() + 1, yy.max() + 1)
    ow, oh = opening[2] - opening[0], opening[3] - opening[1]
    s = max(1080 / ow, (Y_BASE + 4 - 227) / oh)
    ox = 220 - opening[0] * s
    oy = (Y_BASE + 6) - fbox[3] * s
    ar_l = place(ar, s, ox, oy)
    ar_l[..., :3] *= WARM
    op_stage = (int(opening[0] * s + ox), int(opening[1] * s + oy), int(opening[2] * s + ox), int(min(opening[3] * s + oy, Y_BASE + 6)))
    rec["arcade"] = dict(scale=round(s, 4), opening_stage=list(op_stage), facade_stage=[int(fbox[0] * s + ox), int(fbox[1] * s + oy),
                                                                                      int(fbox[2] * s + ox), int(fbox[3] * s + oy)])
    # 騎樓陰影內牆（含小宇身後的門洞），在立面後面
    door = char_boxes.get("doorway")
    wall_box = (op_stage[0] - 20, op_stage[1] - 20, op_stage[2] + 20, Y_BASE + 8)
    wall = wall_layer(wall_box, door)
    base = composite_flat(base, wall, gap=0, strength=0, thick=0, shadow=False)
    flats.append(("騎樓陰影內牆＋門洞（局部背板）", wall))
    base = composite_flat(base, ar_l, gap=16, strength=0.30, thick=4.0)
    flats.append(("前排騎樓立面", ar_l))
    # 樹：左右兩棵
    tr = L["trees"]
    ct = components(tr[..., 3], 0.01)
    trees_l = []
    if len(ct) >= 2:
        for c, (cx, hgt) in zip((ct[0], ct[-1]), ((40, 740), (1730, 820))):
            x0, y0, x1, y1 = c["box"]
            s = hgt / (y1 - y0)
            tl = place(tr, s, cx - (x0 + x1) / 2 * s, (Y_BASE + 26) - y1 * s, mask=c["mask"].astype(np.float32))
            tl[..., :3] *= WARM
            base = composite_flat(base, tl, gap=12, strength=0.26, thick=3.5)
            trees_l.append(tl)
        flats.append(("行道樹（左、右各一棵）", np.maximum(trees_l[0], trees_l[1])))
    # 地面
    gl = ground_layer()
    base = composite_flat(base, gl, gap=0, strength=0, thick=0, shadow=False)
    flats.append(("地面（暖黃橘紙）", gl))
    # 花台：A（高）在阿樂下半身後；B（中）在小晴下半身後；C（長矮）在右側前景
    pl = L["planters"]
    cp = components(pl[..., 3], 0.01)
    rec["planters"] = []
    planter_l = []
    if len(cp) >= 3:
        used = set()
        # 角色身後的 A、B 是「局部亮背板」：去掉頂上的小植物（植物在角色腰側會拉低對比），石材提亮到接近紙白；C 是右側裝飾花台，保留原樣
        specs = [(char_boxes["planter_ale"], char_boxes.get("lim_ale", (-1e9, 1e9)), True),
                 (char_boxes["planter_xq"], char_boxes.get("lim_xq", (-1e9, 1e9)), True),
                 (char_boxes["planter_c"], (-1e9, 1e9), False)]
        for (tx0, ttop, tx1, tbase), (lim0, lim1), backing in specs:
            asp_t = (tbase - ttop) / max(tx1 - tx0, 1)
            cands = [i for i in range(len(cp)) if i not in used] or list(range(len(cp)))
            i = min(cands, key=lambda j: abs(math.log(((cp[j]["box"][3] - cp[j]["box"][1]) / (cp[j]["box"][2] - cp[j]["box"][0])) / asp_t)))
            used.add(i)
            c = cp[i]
            x0, y0, x1, y1 = c["box"]
            # 石材本體上緣（不含頂上的小植物）：寬度達最大寬 92% 的第一列
            widths = c["mask"].sum(1)
            stone_top = int(np.nonzero(widths >= 0.92 * widths.max())[0][0])
            cols = np.nonzero(c["mask"][stone_top + 4:y1].any(0))[0]
            sx0, sx1 = cols.min(), cols.max() + 1
            # 只等比縮放：石材上緣貼齊腰線、下緣在角色腳後；寬度不夠才並排兩個（一排花台），不拉伸
            s = (tbase - ttop) / (y1 - stone_top)
            wbox = (sx1 - sx0) * s
            n_copy = 1 if wbox >= 0.85 * (tx1 - tx0) else max(1, int(math.ceil((tx1 - tx0) / wbox - 0.08)))
            while n_copy > 1 and wbox * n_copy > (lim1 - lim0):
                n_copy -= 1
            total = wbox * n_copy
            left = (tx0 + tx1) / 2 - total / 2
            left = min(max(left, lim0), lim1 - total)     # 不伸到相鄰角色需要暗背板的位置
            src = pl
            msk = c["mask"].astype(np.float32)
            if backing:
                src = pl.copy()
                msk = msk.copy()
                msk[: stone_top + 2] = 0                       # 去掉植物
                src[..., :3] = 255 - (255 - src[..., :3]) * PLANTER_LIFT
            for kk in range(n_copy):
                plx = place(src, s, left + kk * wbox - sx0 * s, tbase - y1 * s, mask=msk)
                base = composite_flat(base, plx, gap=10, strength=0.30, thick=4.0)
                planter_l.append(plx)
            rec["planters"].append(dict(target=[tx0, ttop, tx1, tbase], component=i, scale=round(s, 4), copies=n_copy,
                                        local_backing=backing, plants_removed=backing, lift=PLANTER_LIFT if backing else None,
                                        stage_box=[int(left), int(ttop), int(left + total), int(tbase)]))
        allp = planter_l[0].copy()
        for p_ in planter_l[1:]:
            allp = np.where(p_[..., 3:4] > allp[..., 3:4], p_, allp)
        flats.append(("洗石子花台（三個，局部亮背板）", allp))
    return base, rec, flats


def scene_boxes(layers_alpha, ale_masks, to_stage):
    """依角色實際輪廓決定局部背板位置：門洞包住小宇上半身＋短褲外 46 px；花台上緣＝阿樂、小晴腰線。"""
    out = {}
    a_xy = layers_alpha["xiaoyu"] > 60
    ys, xs = np.nonzero(a_xy)
    top, bot = ys.min(), ys.max()
    hgt = bot - top
    sel = a_xy.copy()
    sel[int(top + 0.86 * hgt):] = False
    ys2, xs2 = np.nonzero(sel)
    out["doorway"] = (int(xs2.min() - 52), int(top - 40), int(xs2.max() + 52), Y_BASE + 8)
    # 阿樂：腰線（圍裙腰帶）＝軀幹上 waist 點
    wy = to_stage("torso", rig.MJ["waist"])[1]
    low = ale_masks["torso"] | ale_masks["thigh_r"] | ale_masks["thigh_l"] | ale_masks["shin_r"] | ale_masks["shin_l"]
    low[: int(wy + 8)] = False
    ys3, xs3 = np.nonzero(low)
    feet = LAYOUT["ale"]["feet"]
    out["planter_ale"] = (int(xs3.min() - 60), int(wy - BACK["ale_above_waist"]), int(xs3.max() + 60), int(feet - BACK["base_gap"]))   # 花台底在腳後，露出一條地面放接地影
    a_q = layers_alpha["xiaoqing"] > 60
    ys4, xs4 = np.nonzero(a_q)
    tq, bq = ys4.min(), ys4.max()
    hq = bq - tq
    waist_q = tq + BACK["xq_top"] * hq
    lowq = a_q.copy()
    lowq[: int(waist_q)] = False
    ys5, xs5 = np.nonzero(lowq)
    out["planter_xq"] = (int(xs5.min() - 50), int(waist_q + 4), int(xs5.max() + 50), int(LAYOUT["xiaoqing"]["feet"] - BACK["base_gap"]))
    out["planter_c"] = (1500, 712, 1900, 856)
    # 花台不可伸到鄰近角色「需要暗背板」的位置：A 不超過小晴黃上衣左緣 −40（伸出的手臂是膚色，可以在花台前）；B 不超過門洞左緣 −10
    lay_q = np.array(LAYOUT_CACHE["xiaoqing"])
    hq_, sq_, vq_ = hsv_np(lay_q[..., :3])
    yellow = (lay_q[..., 3] > 200) & (hq_ >= 32) & (hq_ <= 56) & (sq_ >= 0.55) & (vq_ >= 0.55)
    yx = np.nonzero(yellow.any(0))[0]
    out["lim_ale"] = (-1e9, float((yx.min() if len(yx) else xs4.min()) - BACK["lim_gap"]))
    out["lim_xq"] = (float(xs3.max() - 200), float(out["doorway"][0] - 10))
    return out


def build_scene(pose=None, head="worried", with_kids=True):
    pose = pose or ALE_POSE
    layers, info = {}, {}
    if with_kids:
        for key in ("xiaoyu", "xiaoqing"):
            layers[key], info[key] = place_kid(key, LAYOUT[key])
            LAYOUT_CACHE[key] = layers[key]
    layers["ale"], to_stage, info["ale"] = place_ale(pose, head)
    alphas = {k: np.array(v)[..., 3] for k, v in layers.items()}
    boxes = scene_boxes(alphas, info["ale"]["masks"], to_stage) if with_kids else {}
    stage, rec, flats = build_set(boxes)
    shaded = stage.copy()
    for k in [k for k in ("xiaoyu", "ale", "xiaoqing") if k in layers]:
        shaded = multiply_shadow(shaded, char_shadows(alphas[k], LAYOUT[k]))
    canvas = Image.fromarray(np.clip(shaded, 0, 255).astype(np.uint8)).convert("RGBA")
    for k in [k for k in ("xiaoyu", "ale", "xiaoqing") if k in layers]:   # 由後往前
        canvas.alpha_composite(Image.fromarray(np.clip(card_side(alphas[k]), 0, 255).astype(np.uint8), "RGBA"))
        canvas.alpha_composite(layers[k])
    return dict(stage=stage, shaded=shaded, layers=layers, alphas=alphas, to_stage=to_stage, info=info, boxes=boxes, set_info=rec,
                flats=flats, chars_only=canvas.copy(), canvas=canvas, ale_masks=info["ale"]["masks"], ale_scale=info["ale"]["scale"],
                pose=pose)


# ---------------------------------------------------------------- 量測
def costume_masks(sc):
    out = {}
    for key, specs in COSTUMES.items():
        if key not in sc["layers"]:
            continue
        layer = np.array(sc["layers"][key])
        rgb, a = layer[..., :3], layer[..., 3]
        h, s, v = hsv_np(rgb)
        base = ndimage.binary_erosion(a > 220, iterations=4)
        ys = np.nonzero(a.max(1) > 0)[0]
        top, bot = ys.min(), ys.max()
        yy = np.arange(H)[:, None]
        res = {}
        for name, (h0, h1), s0, s1, v0, v1, main, band in specs:
            hue_ok = ((h >= h0) | (h <= h1)) if h0 > h1 else ((h >= h0) & (h <= h1))
            m = base & hue_ok & (s >= s0) & (s <= s1) & (v >= v0) & (v <= v1)
            m &= (yy >= top + band[0] * (bot - top)) & (yy <= top + band[1] * (bot - top))
            m = ndimage.binary_opening(m, iterations=1)
            res[name] = dict(mask=m, main=main)
        out[key] = res
    return out


def measure(sc):
    """逐色對比：每個服裝色 × 實際相鄰背景（輪廓外 6–34 px、只算靠近該色的那一段）。
    中位數＝服裝中位亮度對環帶中位亮度；p10＝環帶逐像素對比的第 10 百分位；worst＝min(對 p10 亮度, 對 p90 亮度)。"""
    any_char = np.zeros((H, W), bool)
    for k, a in sc["alphas"].items():
        any_char |= a > 60
    bg_img = np.clip(sc["shaded"], 0, 255).astype(np.uint8)
    chars = np.array(sc["chars_only"].convert("RGB"))
    views = {"original": (bg_img, chars), "proj_v1": (projector(bg_img, "v1"), projector(chars, "v1")),
             "proj_v2": (projector(bg_img, "v2"), projector(chars, "v2")),
             "lowc": (low_contrast(bg_img), low_contrast(chars)), "gray": (grayscale(bg_img), grayscale(chars))}
    cms = costume_masks(sc)
    near_ring = ndimage.binary_dilation(any_char, iterations=34) & ~ndimage.binary_dilation(any_char, iterations=6)
    outside = ~ndimage.binary_dilation(any_char, iterations=8)
    _, (iy, ix) = ndimage.distance_transform_edt(~outside, return_indices=True)
    rows, samples = [], []
    for key, res in cms.items():
        a = sc["alphas"][key] > 60
        dist_in = ndimage.distance_transform_edt(a)
        for cname, cinfo in res.items():
            m = cinfo["mask"]
            if m.sum() < 30:
                continue
            edge_part = m & (dist_in <= 18)
            if edge_part.sum() < 15:
                rows.append(dict(character=NAMES[key], color=cname, main=cinfo["main"], touches_background=False))
                continue
            ring = ndimage.binary_dilation(edge_part, iterations=34) & near_ring
            dm = ndimage.distance_transform_edt(m)
            cand = np.where(edge_part, dm, 0)
            yc, xc = np.unravel_index(np.argmax(cand), cand.shape)
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
                med, p10l, p90l = float(np.median(rl)), float(np.percentile(rl, 10)), float(np.percentile(rl, 90))
                per = (np.maximum(cl, rl) + 0.05) / (np.minimum(cl, rl) + 0.05)
                cs = np.median(chv[max(yc - 5, 0):yc + 5, max(xc - 5, 0):xc + 5].reshape(-1, 3), 0)
                bs = np.median(bgv[by2 - 5:by2 + 5, bx2 - 5:bx2 + 5].reshape(-1, 3), 0)
                row[vk] = dict(costume_hex=hexs(cmed), costume_lum=round(cl, 4), ring_median_lum=round(med, 4),
                               ring_p10_lum=round(p10l, 4), ring_p90_lum=round(p90l, 4),
                               contrast_median=round(contrast(cl, med), 2), contrast_p10=round(float(np.percentile(per, 10)), 2),
                               contrast_worst=round(min(contrast(cl, p10l), contrast(cl, p90l)), 2),
                               sample_contrast_10x10=round(contrast(float(rel_lum(cs)), float(rel_lum(bs))), 2),
                               sample_costume_lum=round(float(rel_lum(cs)), 4), sample_bg_lum=round(float(rel_lum(bs)), 4))
            rows.append(row)
            samples.append((len(rows), (xc, yc), (bx2, by2)))
    outline = {}
    pv2c = projector(np.array(sc["canvas"].convert("RGB")), "v2")
    pv2b = views["proj_v2"][0]
    for key in sc["alphas"]:
        a = sc["alphas"][key] > 60
        band = ndimage.binary_dilation(a, iterations=3) & ~ndimage.binary_erosion(a, iterations=8)
        lum = rel_lum(pv2c[band])
        dark = float(np.percentile(lum, 20))
        light = float(np.percentile(lum, 80))
        ring = ndimage.binary_dilation(a, iterations=34) & ~ndimage.binary_dilation(a, iterations=6) & ~any_char
        bl = float(np.median(rel_lum(pv2b[ring])))
        outline[NAMES[key]] = dict(edge_dark_p20_lum=round(dark, 4), edge_light_p80_lum=round(light, 4), ring_median_lum=round(bl, 4),
                                   contrast_dark_edge=round(contrast(dark, bl), 2), contrast_white_core=round(contrast(light, bl), 2),
                                   best=round(max(contrast(dark, bl), contrast(light, bl)), 2))
    return rows, samples, outline


def ring_sheet(sc, path, keys=(("小宇", "橘紅外套"), ("小晴", "湖水綠吊帶褲"), ("小晴", "芥末黃上衣"), ("阿樂叔叔", "深藍圍裙"), ("阿樂叔叔", "米色襯衫"), ("小宇", "卡其短褲"))):
    """逐色環帶診斷圖（投影 v2）：環帶像素依逐像素對比上色（綠 ≥3:1、紅 <3:1），讓驗收方看見是哪一段背景拉低 p10。"""
    any_char = np.zeros((H, W), bool)
    for a in sc["alphas"].values():
        any_char |= a > 60
    bg = projector(np.clip(sc["shaded"], 0, 255).astype(np.uint8), "v2")
    chars = projector(np.array(sc["chars_only"].convert("RGB")), "v2")
    cms = costume_masks(sc)
    near_ring = ndimage.binary_dilation(any_char, iterations=34) & ~ndimage.binary_dilation(any_char, iterations=6)
    inv = {v: k for k, v in NAMES.items()}
    tiles = []
    for who, cname in keys:
        key = inv[who]
        if key not in cms or cname not in cms[key]:
            continue
        m = cms[key][cname]["mask"]
        a = sc["alphas"][key] > 60
        edge = m & (ndimage.distance_transform_edt(a) <= 18)
        ring = ndimage.binary_dilation(edge, iterations=34) & near_ring
        cl = float(rel_lum(np.median(chars[m], 0)))
        rl = rel_lum(bg)
        per = (np.maximum(cl, rl) + 0.05) / (np.minimum(cl, rl) + 0.05)
        img = (np.array(sc["chars_only"].convert("RGB")).astype(np.float32) * 0.55).astype(np.uint8)
        img[m] = (255, 255, 255)
        img[ring & (per >= 3)] = (60, 220, 90)
        img[ring & (per < 3)] = (255, 60, 60)
        ys, xs = np.nonzero(ring | m)
        box = (max(xs.min() - 20, 0), max(ys.min() - 20, 0), min(xs.max() + 20, W), min(ys.max() + 20, H))
        tile = Image.fromarray(img).crop(box)
        sc_ = 420 / tile.height
        tile = tile.resize((max(int(tile.width * sc_), 1), 420), Image.LANCZOS)
        frac = float((per[ring] >= 3).mean())
        tiles.append((f"{who}｜{cname}：環帶 ≥3:1 佔 {frac * 100:.0f}%", tile))
    Wt = sum(tl.width + 20 for _, tl in tiles) + 20
    sheet = Image.new("RGB", (max(Wt, 900), 520), (36, 36, 38))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), "逐色環帶診斷（投影 v2）：白＝服裝色、綠＝該處背景對比 ≥3:1、紅＝<3:1", font=lfont(22), fill=(240, 240, 240))
    x = 20
    for title, tl in tiles:
        sheet.paste(tl, (x, 84))
        d.text((x, 52), title, font=lfont(17), fill=(255, 220, 120))
        x += tl.width + 20
    sheet.save(path)


def rope_checks(sc, final_rgb):
    pv2 = projector(final_rgb, "v2")
    out = {}
    for name, r in sc["ropes"].items():
        pts = r["pts"]
        checks = []
        for frac in (0.06, 0.2, 0.35, 0.5, 0.7, 0.9):
            i = int(frac * (len(pts) - 1))
            cx, cy = pts[i]
            if cy < 6 or cy > H - 6:
                continue
            t = pts[min(i + 5, len(pts) - 1)] - pts[max(i - 5, 0)]
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])

            def lum_at(x, y):
                return float(rel_lum(pv2[int(np.clip(round(y), 0, H - 1)), int(np.clip(round(x), 0, W - 1))]))
            prof = [lum_at(cx + n[0] * d, cy + n[1] * d) for d in np.arange(-6, 6.5, 0.5)]
            sides = []
            for d in (-16, 16):
                x, y = int(round(cx + n[0] * d)), int(round(cy + n[1] * d))
                patch = pv2[max(y - 3, 0):y + 4, max(x - 3, 0):x + 4].reshape(-1, 3)
                sides.append(float(np.median(rel_lum(patch))))
            checks.append(dict(at=[round(float(cx)), round(float(cy))], cross_section_min_max=[round(min(prof), 4), round(max(prof), 4)],
                               side_lum=[round(v, 4) for v in sides],
                               best_contrast_vs_each_side=[round(max(contrast(min(prof), sl), contrast(max(prof), sl)), 2) for sl in sides]))
        out[name] = dict({k: v for k, v in r.items() if k != "pts"}, samples_proj_v2=checks)
    return out


# ---------------------------------------------------------------- 輸出圖
def table_sheet(rows, samples, final, path, outline):
    f1, f3 = lfont(28), lfont(16)
    thumb_w = 1100
    th = final.resize((thumb_w, int(thumb_w * H / W)), Image.LANCZOS).convert("RGB")
    dd = ImageDraw.Draw(th)
    k = thumb_w / W
    for idx, (cx, cy), (bx, by) in samples:
        for (x, y), col in (((cx, cy), (255, 40, 40)), ((bx, by), (40, 160, 255))):
            dd.rectangle([x * k - 4, y * k - 4, x * k + 4, y * k + 4], outline=col, width=2)
        dd.line([cx * k, cy * k, bx * k, by * k], fill=(255, 255, 0), width=1)
        dd.text((cx * k + 5, cy * k - 16), str(idx), font=lfont(15), fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))
    hrow = 30
    img = Image.new("RGB", (2080, 140 + th.height + 40 + hrow * (len(rows) + 4)), (36, 36, 38))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "逐色對比量測表 v03（角色服裝色 × 實際站位背景；WCAG 相對亮度比；局部背板解法，未改任何服色）", font=f1, fill=(240, 240, 240))
    d.text((20, 56), "紅框＝服裝取樣點（10×10），藍框＝背景取樣點（10×10）；數字＝表格列號。環帶＝該色靠外緣部分往外 6–34 px 的景板（含影子，不含角色、繩、字幕）。"
           "p10＝環帶逐像素對比的第 10 百分位。", font=f3, fill=(200, 200, 200))
    img.paste(th, (20, 90))
    y = 90 + th.height + 20
    hdr = ["#", "角色", "服裝色", "主色", "HEX", "取樣 服裝→背景", "原圖 中位", "投影v2 中位", "投影v2 p10", "投影v2 10×10", "灰階 中位", "灰階 10×10", "低對比 中位", "低對比 p10", "低對比 10×10"]
    xs = [20, 56, 140, 270, 320, 420, 640, 750, 870, 985, 1110, 1220, 1340, 1460, 1580]
    for x, h_ in zip(xs, hdr):
        d.text((x, y), h_, font=f3, fill=(255, 220, 120))
    y += hrow
    for i, r in enumerate(rows, 1):
        if not r.get("touches_background"):
            vals = [str(i), r["character"], r["color"], "●" if r["main"] else "", "—", "不接觸背景"]
        else:
            o, p2, g, lc = r["original"], r["proj_v2"], r["gray"], r["lowc"]
            f = lambda v: f"{v:.2f}"  # noqa: E731
            vals = [str(i), r["character"], r["color"], "●" if r["main"] else "", o["costume_hex"],
                    f"({r['sample_costume_xy'][0]},{r['sample_costume_xy'][1]})→({r['sample_bg_xy'][0]},{r['sample_bg_xy'][1]})",
                    f(o["contrast_median"]), f(p2["contrast_median"]), f(p2["contrast_p10"]), f(p2["sample_contrast_10x10"]),
                    f(g["contrast_median"]), f(g["sample_contrast_10x10"]), f(lc["contrast_median"]), f(lc["contrast_p10"]),
                    f(lc["sample_contrast_10x10"])]
        for j, (x, v) in enumerate(zip(xs, vals)):
            col = (235, 235, 235)
            if j >= 6 and r.get("touches_background"):
                try:
                    col = (120, 230, 120) if float(v) >= 3 else (255, 120, 110)
                except ValueError:
                    pass
            d.text((x, y), v, font=f3, fill=col)
        y += hrow
    y += 10
    d.text((20, y), "外輪廓對相鄰景板（投影 v2；取深色內線／白色紙芯邊兩者較高者）：" +
           "；".join(f"{k} {v['best']:.2f}:1" for k, v in outline.items()), font=f3, fill=(200, 200, 200))
    y += 26
    d.text((20, y), "綠＝≥3:1；紅＝<3:1。低對比模擬（CSS contrast 50%）把全畫面壓到 sRGB 0.25–0.75，橘紅外套對任何背景的理論上限是 2.42:1"
           "（見 contrast_v03.json 的 lowc_ceiling 與 DECISIONS.md 待決事項）。", font=f3, fill=(200, 200, 200))
    img.save(path)


def letterbox_43(final_nosub, lines, px_1080, out_w, out_h):
    stage_h = round(out_w * 9 / 16)
    img = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
    img.alpha_composite(final_nosub.resize((out_w, stage_h), Image.LANCZOS).convert("RGBA"), (0, 0))
    px = round(px_1080 * out_h / 1080)
    band = out_h - stage_h
    blk_h = px * 1.28 * len(lines) + 2 * int(px * 0.24)
    sub = subtitle_block(img, lines, px, out_w / 2, stage_h + band / 2 + blk_h / 2, strip=False)
    return img.convert("RGB"), dict(sub, stage_rows=[0, stage_h], black_band_rows=[stage_h, out_h], band_fraction=round(band / out_h, 3),
                                    px_equiv_1080=round(px * 1080 / out_h, 1))


def layers_sheet(sc, path):
    """分層拆解圖：每一層單獨畫在灰底上（看得到切口與側邊厚度），最後一格是組合結果。"""
    flats = sc["flats"]
    tw = 600
    th_ = int(tw * H / W)
    n = len(flats) + 1
    cols = 3
    rows_ = math.ceil(n / cols)
    img = Image.new("RGB", (cols * (tw + 20) + 20, rows_ * (th_ + 56) + 70), (36, 36, 38))
    d = ImageDraw.Draw(img)
    d.text((20, 16), "分層卡紙景片 v03：每層獨立（右下側卡紙厚度＋左上切口受光細線＋往右下的柔影）；表演區不整面提亮，只在角色身後放局部背板",
           font=lfont(22), fill=(240, 240, 240))
    for i, (name, lay) in enumerate(flats + [("組合結果（含角色影子）", None)]):
        r, c = divmod(i, cols)
        x, y = 20 + c * (tw + 20), 64 + r * (th_ + 56)
        if lay is None:
            tile = Image.fromarray(np.clip(sc["shaded"], 0, 255).astype(np.uint8)).resize((tw, th_), Image.LANCZOS)
        else:
            bg = np.zeros((H, W, 3), np.float32) + np.array([120, 124, 128], np.float32)
            tile_a = composite_flat(bg, lay, gap=10, strength=0.30, thick=4.0)
            tile = Image.fromarray(np.clip(tile_a, 0, 255).astype(np.uint8)).resize((tw, th_), Image.LANCZOS)
        img.paste(tile, (x, y + 30))
        d.text((x, y + 4), f"{i + 1}. {name}", font=lfont(20), fill=(255, 220, 120))
    img.save(path)


def feet_closeup(sc, final, path):
    f = lfont(22)
    crops = []
    for key in ("ale", "xiaoqing", "xiaoyu"):
        a = sc["alphas"][key] > 60
        ys, xs = np.nonzero(a)
        feet = LAYOUT[key]["feet"]
        low = a.copy()
        low[: feet - 60] = False
        ys2, xs2 = np.nonzero(low)
        cx = int((xs2.min() + xs2.max()) / 2)
        box = (cx - 150, feet - 110, cx + 210, feet + 70)
        crops.append((NAMES[key], final.crop(box).resize((720, 360), Image.LANCZOS), box))
    img = Image.new("RGB", (720 * 3 + 80, 470), (36, 36, 38))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "腳部局部放大（×2）：主光左上前方 45° → 背板柔影往右下（強度 0.22–0.28），腳底接地影往右拖、靠腳最深；離背板越遠影子越柔、偏移越大",
           font=lfont(20), fill=(240, 240, 240))
    for i, (name, c, box) in enumerate(crops):
        x = 20 + i * 740
        img.paste(c.convert("RGB"), (x, 90))
        d.text((x, 56), f"{name}（畫面 {box[0]}–{box[2]}, {box[1]}–{box[3]}）深度 {LAYOUT[list(NAMES)[i]]['depth']}", font=f, fill=(255, 220, 120))
    img.save(path)


def grade_compare(sc, path):
    """舞台調色對照：左＝不降彩（生成景片原色）、右＝v03（只在天空與遠山降彩 ×0.78；表演區不提亮）。"""
    raw = Image.fromarray(np.clip(sc["stage"], 0, 255).astype(np.uint8))
    img = Image.new("RGB", (1940, 640), (36, 36, 38))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "舞台調色 v03：撤回表演區提亮（v02 lift 0.62）；降彩只做在天空與遠山（×0.78）；地面維持暖黃橘並往前緣壓暗；局部背板在角色身後",
           font=lfont(22), fill=(240, 240, 240))
    v02 = ROOT / "review/G2/stage_wash_compare_v02.png"
    if v02.exists():
        old = Image.open(v02).convert("RGB")
        old = old.resize((940, int(940 * old.height / old.width)))
        img.paste(old.crop((0, 0, 940, min(old.height, 560))), (20, 60))
        d.text((20, 600), "參考：v02 對照圖（表演區洗白）", font=lfont(20), fill=(200, 200, 200))
    img.paste(raw.resize((940, 529), Image.LANCZOS), (980, 60))
    d.text((980, 600), "v03 景板（分層卡紙＋局部背板，含景片投影；未含角色）", font=lfont(20), fill=(200, 200, 200))
    img.save(path)


def jacket_info(sc, final_rgb):
    """小宇外套色票：raw 基準、v02 母版、v03 姿勢圖、舞台合成；並附「同色相加深」兩個試算（未套用，待決）。"""
    def med_jacket(rgba):
        a = np.asarray(rgba)
        h, s_, v = hsv_np(a[..., :3])
        m = ((h >= 345) | (h <= 22)) & (s_ >= 0.62) & (v >= 0.28) & (a[..., 3] > 220)
        ys = np.nonzero(a[..., 3].max(1) > 0)[0]
        m[: int(ys.min() + 0.15 * (ys.max() - ys.min()))] = False
        m[int(ys.min() + 0.75 * (ys.max() - ys.min())):] = False
        return np.median(a[..., :3][m], 0)
    sw = {}
    for tag, path in (("基準（原始生成 raw）", RAW_XIAOYU), ("v02 母版", MASTER_XIAOYU), ("v03 姿勢圖", KID_FILES["xiaoyu"])):
        c = med_jacket(np.array(Image.open(path).convert("RGBA")))
        sw[tag] = c
    cm = costume_masks(sc)["xiaoyu"]["橘紅外套"]["mask"]
    sw["舞台合成 v03"] = np.median(final_rgb[cm], 0)
    base_lab = srgb_to_lab(sw["v02 母版"])
    out = {}
    for tag, c in sw.items():
        lab = srgb_to_lab(c)
        out[tag] = dict(hex=hexs(c), L_star=round(float(lab[0]), 1), rel_lum=round(float(rel_lum(c)), 4),
                        proj_v2_lum=round(float(rel_lum(projector(np.asarray(c).round().astype(np.uint8)[None, None, :], "v2")[0, 0])), 4),
                        lowc_lum=round(float(rel_lum(low_contrast(np.asarray(c).round().astype(np.uint8)[None, None, :])[0, 0])), 4),
                        dE00_vs_v02=round(delta_e2000(base_lab.tolist(), lab.tolist()), 2))
    trials = {}
    for Lt in (42.0, 38.0):
        lab = base_lab.copy()
        k = Lt / base_lab[0]
        lab = np.array([Lt, base_lab[1] * (0.6 + 0.4 * k), base_lab[2] * (0.6 + 0.4 * k)])   # 色相角不變，彩度隨明度略降
        c = lab_to_srgb(lab[None, :])[0]
        lab2 = srgb_to_lab(c)
        pc = projector(c.round().astype(np.uint8)[None, None, :], "v2")[0, 0]
        lc = low_contrast(c.round().astype(np.uint8)[None, None, :])[0, 0]
        lp, ll = float(rel_lum(pc)), float(rel_lum(lc))
        trials[f"L*{int(Lt)}"] = dict(hex=hexs(c), L_star=round(float(lab2[0]), 1),
                                     hue_deg=round(float(math.degrees(math.atan2(lab2[2], lab2[1]))), 1),
                                     base_hue_deg=round(float(math.degrees(math.atan2(base_lab[2], base_lab[1]))), 1),
                                     dE00_vs_v02=round(delta_e2000(base_lab.tolist(), lab2.tolist()), 2),
                                     proj_v2_lum=round(lp, 4), lowc_lum=round(ll, 4),
                                     needs_bg_proj_v2_at_least=round(3 * (lp + 0.05) - 0.05, 3),
                                     best_vs_white_proj_v2=round(contrast(lp, 0.729), 2),
                                     best_vs_white_lowc=round(contrast(ll, float(rel_lum(np.array([191, 191, 191])))), 2),
                                     best_vs_black_lowc=round(contrast(ll, float(rel_lum(np.array([64, 64, 64])))), 2))
    return out, trials


def intent_force_demo(path):
    """「意圖與受力」三格：① 想揮手（線鬆）② 線繃緊、手停住、臉換困惑 ③ 手腕被拉到旁邊、膝蓋真的被提起（膝線繃緊）。
    三格的線都扣同樣三點：右腕背、右肘外、左膝前；腕／肘垂直、膝線近乎垂直走身體外側。"""
    panels = [
        ("① 想揮手（笑著）：右手往上抬，線還鬆", "wave", "smile", "slack"),
        ("② 線繃緊：手停在半空，臉換成困惑", "stopped", "worried", "taut"),
        ("③ 手腕被拉到旁邊、左膝被提起（大腿外抬 18°）", "pulled", "worried", "taut"),
    ]
    cw, chh = 620, 820
    sheet = Image.new("RGB", (cw * 3 + 40, chh + 130), (36, 36, 38))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), "意圖與受力（a2_c002）：同一位阿樂叔叔分件 rig 的三個瞬間；線只扣腕背、肘外、膝前，往上出畫面，不畫操控者", font=lfont(24), fill=(240, 240, 240))
    rep = []
    for i, (title, pname, head, mode) in enumerate(panels):
        lay = dict(LAYOUT["ale"], cx=960, feet=1000, height=800)
        pose = dict(rig.POSES[pname])
        layer, to_stage, inf = place_ale(pose, head, lay=lay)
        alphas = {"ale": np.array(layer)[..., 3]}
        boxes = {"doorway": None, "planter_ale": None}
        # 背景：同一套分層景板（不放孩子；花台放在阿樂下半身後）
        wy = to_stage("torso", rig.MJ["waist"])[1]
        low = inf["masks"]["torso"] | inf["masks"]["thigh_r"] | inf["masks"]["thigh_l"]
        low[: int(wy + 8)] = False
        ys3, xs3 = np.nonzero(low)
        boxes = {"doorway": None, "planter_ale": (int(xs3.min() - 60), int(wy + 14), int(xs3.max() + 60), 988),
                 "planter_xq": (1500, 860, 1700, 1000), "planter_c": (40, 860, 420, 1000)}
        stage, _, _ = build_set(boxes)
        shaded = multiply_shadow(stage, char_shadows(alphas["ale"], lay))
        canvas = Image.fromarray(np.clip(shaded, 0, 255).astype(np.uint8)).convert("RGBA")
        canvas.alpha_composite(Image.fromarray(np.clip(card_side(alphas["ale"]), 0, 255).astype(np.uint8), "RGBA"))
        canvas.alpha_composite(layer)
        sc = dict(canvas=canvas, alphas=alphas, to_stage=to_stage, ale_masks=inf["masks"], ale_scale=inf["scale"])
        ropes = add_strings(sc, mode=mode)
        cwid = int(1040 * (cw - 20) / chh)
        crop = canvas.crop((960 - cwid // 2, 40, 960 + cwid // 2, 1080)).resize((cw - 20, chh), Image.LANCZOS)
        sheet.paste(crop.convert("RGB"), (20 + i * cw, 60))
        d.text((20 + i * cw, chh + 72), title, font=lfont(21), fill=(240, 240, 240))
        rep.append({k: dict(attach=v["attach_point"], tilt=v["tilt_deg_from_vertical"], clearance=v["min_clearance_px"],
                            over_hand=v["samples_over_hand"], over_face=v["samples_over_face"]) for k, v in ropes.items()})
    sheet.save(path)
    return rep


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "review/G2"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sc = build_scene()
    ropes = add_strings(sc, mode="taut")
    final_nosub = sc["canvas"].copy()
    final_nosub.convert("RGB").save(out / "stage_composite_nosub_v03.png")
    # 16:9 字幕：紙條中心 x＝960，下緣＝1018（≤1026，安全框內）
    final = final_nosub.copy()
    sub = subtitle_block(final, SUB_LINES, SUB_PX, W / 2, 1018)
    final.convert("RGB").save(out / "stage_composite_v03.png")
    sub["inside_safe_frame"] = bool(sub["strip"][0] >= SAFE[0] and sub["strip"][1] >= SAFE[1]
                                    and sub["strip"][0] + sub["strip"][2] <= SAFE[2] and sub["strip_bottom_row"] <= SAFE[3])
    sub["text_vs_strip"] = text_contrast(final, sub["strip"], sub["line_boxes"])
    sub["ink_height_px_measured"] = [ink_height(final, b) for b in sub["line_boxes"]]
    img43, s43 = letterbox_43(final_nosub, SUB_LINES, SUB_PX, 1440, 1080)
    img43.save(out / "stage_composite_43_v03.png")
    s43["text_vs_band"] = text_contrast(img43, [s43["strip"][0], s43["strip"][1], s43["strip"][2], s43["strip"][3]], s43["line_boxes"])
    img1024, s1024 = letterbox_43(final_nosub, SUB_LINES, SUB_PX, 1024, 768)
    img1024.save(out / "stage_composite_1024x768_v03.png")
    rows, samples, outline = measure(sc)
    final_rgb = np.array(final_nosub.convert("RGB"))
    jk, trials = jacket_info(sc, final_rgb)
    table_sheet(rows, samples, final_nosub, out / "contrast_table_v03.png", outline)
    layers_sheet(sc, out / "stage_layers_v03.png")
    ring_sheet(sc, out / "contrast_rings_v03.png")
    feet_closeup(sc, final_nosub, out / "stage_feet_closeup_v03.png")
    grade_compare(sc, out / "stage_grade_compare_v03.png")
    demo = intent_force_demo(out / "intent_force_demo_v03.png")
    # 低對比模擬的理論上限：CSS contrast(50%) 把 sRGB 壓到 0.25–0.75
    jl = [r for r in rows if r.get("color") == "橘紅外套"][0]["lowc"]["costume_lum"] if any(r.get("color") == "橘紅外套" for r in rows) else None
    lowc_black, lowc_white = float(rel_lum(np.array([64, 64, 64]))), float(rel_lum(np.array([191, 191, 191])))
    data = dict(
        version="v03", scene="a2_c002「線落下來」：阿樂叔叔右手想揮手、手腕被拉到旁邊、左膝被提起；小晴轉身伸手指向手腕的線（擔心）、小宇側身退半步雙手縮到胸前（驚訝）",
        note="WCAG 相對亮度比。投影 v1＝第 1 輪參數；投影 v2＝第 2 輪加強版（彩度×0.65、黑位 0.18、白位 0.87：黑位相對亮度 0.027、最亮 0.729）。"
             "低對比＝CSS contrast(50%)。灰階＝WCAG 相對亮度灰階。環帶＝該服裝色靠外緣部分往外 6–34 px 的景板（含影子，不含角色、繩、字幕）。"
             "contrast_p10＝環帶逐像素對比的第 10 百分位；contrast_worst＝min(對環帶 p10 亮度, 對 p90 亮度)（沿用 v02 定義）。",
        method="局部背板（不改任何服色、不整面提亮）：騎樓陰影內牆 " + hexs(WALL) + " 在角色上半身後；小宇身後門洞 " + hexs(DOORWAY) +
               "；阿樂與小晴下半身後是淺色洗石子花台；地面暖黃橘 " + hexs(GROUND[0]) + "→" + hexs(GROUND[1]) + "。",
        stage_grade=dict(wash="撤回（v02 lift 0.62 不再使用）", far_desat=FAR_DESAT, far_desat_layers=["天空", "遠山"], warm=WARM.tolist(),
                         shadow=dict(SHADOW, strengths={k: v["shadow"] for k, v in LAYOUT.items()}), light="主光左上前方 45°，所有影子往右下"),
        layout={k: {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in LAYOUT.items()},
        local_backings=sc["boxes"], set_layers=sc["set_info"], ale_pose=ALE_POSE, worried_head=sc["info"]["ale"]["head"],
        per_color=rows, outline_vs_background_proj_v2=outline,
        ropes=rope_checks(sc, final_rgb), subtitle={"16x9_1920x1080": sub, "4x3_1440x1080": s43, "4x3_1024x768": s1024,
                                                    "text": SUB_LINES, "safe_frame_90pct": list(SAFE)},
        jacket=dict(swatches=jk, deeper_trials_NOT_APPLIED=trials,
                    lowc_ceiling=dict(note="CSS contrast(50%) 下最暗 #404040、最亮 #BFBFBF；外套對任何背景的對比上限",
                                      jacket_lowc_lum=jl, vs_black=round(contrast(jl, lowc_black), 2) if jl else None,
                                      vs_white=round(contrast(jl, lowc_white), 2) if jl else None)),
        intent_force_demo=dict(file="intent_force_demo_v03.png", ropes_per_panel=demo),
        unverified="場地投影機實拍（v1.2 §14.2）：代理無法執行，標「未驗證」，第 3 天彩排時從最後一排拍題卡、字幕與本合成畫面回傳對照。",
    )
    (out / "contrast_v03.json").write_text(json.dumps(data, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    for r in rows:
        if r.get("touches_background"):
            p = r["proj_v2"]
            print(f"{r['character']} {r['color']}{'（主色）' if r['main'] else ''}: v2 中位 {p['contrast_median']} p10 {p['contrast_p10']} "
                  f"10×10 {p['sample_contrast_10x10']} | lowc 中位 {r['lowc']['contrast_median']}")
    print("ropes", {k: (v["tilt_deg_from_vertical"], v["min_clearance_px"]) for k, v in sc["ropes"].items()})
    print("subtitle", sub["strip"], sub["strip_bottom_row"], sub["text_vs_strip"])


if __name__ == "__main__":
    main()
