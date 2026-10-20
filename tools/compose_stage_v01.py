"""【凍結：G2 第 1 輪版本，只用來重現 review/G2/stage_composite.png 等 v01 輸出；第 2 輪起改用 tools/compose_stage.py】
舞台合成測試（G2）：三位母版＋景板＋接觸陰影＋灰色扭紋紙繩＋字幕紙條。

用法：
  /opt/anaconda3/bin/python3 tools/compose_stage.py [--stage 景板.png] [--out-dir review/G2]
預設讀 assets/generated/ 的 v01 母版與景板。輸出：
  review/G2/stage_composite.png      1920×1080
  review/G2/stage_composite_43.png   1440×1080（16:9 畫面縮放置中、上下黑邊，模擬 4:3 投影機）
  review/G2/contrast.json            投影模擬下的明度對比量測（角色主色對相鄰背景、白邊腳底對地面、紙繩對背景）

規則（v1.2 第 14.1、15.2 節；G2a 改進清單）：
- 兒童身高＝成人身高 × CHILD_RATIO（0.62–0.68，預設 0.65）。
- 主光在左上前方，接觸陰影與柔和投影落在右下；陰影由程式產生，素材本身不帶影子。
- 紙繩粗 8 px@1080p，深灰邊線＋左上受光邊＋扭紋；只連膝蓋正面並以紙環扣住，不經過頭頸。
- 字幕 64 px@1080p、白字、半透明深色紙條，系統繁中字型（PingFang TC Semibold，退路 Heiti TC）。
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from projsim import projector_v1 as projector  # noqa: E402

W, H = 1920, 1080
CHILD_RATIO = 0.65
ADULT_H = 660            # 成人（阿樂叔叔）在 1080p 中景的身高 px
FEET_Y = 900             # 站立基線（字幕紙條上緣之上）
HORIZON_Y = 760         # 景板地面與騎樓交界（1080p）
BG_LIFT = 0.50          # 舞台背景提亮層：地平線以上往暖白靠攏的比例（G2 掃描 0.38／0.5／0.6 後選定）
BG_DESAT = 0.75         # 地平線以上保留的彩度
GROUND_GAIN = 0.90      # 地面略壓暗，讓白邊腳底更清楚
LIFT_COLOR = (246, 240, 228)
DROP_SHADOW = 0.22      # 右下柔和投影濃度
SUB_TEXT = "不碰、不試；先離開，找大人。"
SUB_PX = 64
FONT_CANDIDATES = [
    ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10),  # PingFang TC Semibold
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),  # Heiti TC Medium
]

CHARS = [
    # (key, 檔案, 中心 x 比例, 是否兒童)
    ("ale", "assets/generated/chr-ale_master_v01.png", 0.30, False),
    ("xiaoqing", "assets/generated/chr-xiaoqing_master_v01.png", 0.53, True),
    ("xiaoyu", "assets/generated/chr-xiaoyu_master_v01.png", 0.70, True),
]


def find_font(px):
    for path, idx in FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(path, px, index=idx)
            return f, f"{f.getname()[0]} {f.getname()[1]}"
        except OSError:
            continue
    raise SystemExit("找不到繁中字型")


def trim(im):
    """去掉生成圖外圍的淡霧（alpha < 24 的半透明光暈）後裁到輪廓。"""
    arr = np.array(im)
    arr[..., 3] = np.where(arr[..., 3] < 24, 0, arr[..., 3])
    im = Image.fromarray(arr, "RGBA")
    ys, xs = np.nonzero(arr[..., 3] > 16)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def rel_lum(rgb):
    a = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def contrast(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def stage_grade(rgb):
    """舞台背景提亮層（大氣透視）：地平線以上的景片降彩、往暖白提亮（背景＝低彩度、中高明度）；
    地面維持中明度並略壓暗。這是舞台燈光的工作，不改原始景板檔。"""
    yy = np.arange(H, dtype=np.float32)[:, None, None]
    w = np.clip((HORIZON_Y + 40 - yy) / 80.0, 0, 1)        # 1＝地平線以上，0＝地面
    gray = rgb.mean(-1, keepdims=True)
    up = gray + (rgb - gray) * BG_DESAT
    up = up + (np.array(LIFT_COLOR, np.float32) - up) * BG_LIFT
    down = rgb * GROUND_GAIN
    return w * up + (1 - w) * down


def multiply_shadow(base, mask, strength, color=(58, 44, 36)):
    """在 base（RGB float 0–255）上以 mask（0–1）乘上暖深色影子。"""
    m = (mask * strength)[..., None]
    col = np.array(color, dtype=np.float32) / 255.0
    return base * (1 - m + m * col)


def char_shadow(alpha_full, feet_y, x0, x1):
    """接觸陰影＋柔和右下投影（主光左上前方）。回傳 0–1 遮罩。"""
    a = alpha_full.astype(np.float32) / 255.0
    # 1) 柔和投影：輪廓往右下偏移、模糊，模擬人物離景片有一段距離
    drop = ndimage.shift(a, (10, 14), order=1)
    drop = ndimage.gaussian_filter(drop, 9) * DROP_SHADOW
    drop[feet_y + 14:, :] = 0  # 不超出腳底太多
    # 2) 接觸陰影：腳底的扁橢圓，略往右偏
    yy, xx = np.mgrid[0:H, 0:W]
    cx = (x0 + x1) / 2 + 10
    rx = (x1 - x0) * 0.62
    ry = 13
    ell = np.clip(1 - (((xx - cx) / rx) ** 2 + ((yy - (feet_y + 3)) / ry) ** 2), 0, 1)
    ell = ndimage.gaussian_filter(ell, 5) * 0.75
    return np.clip(np.maximum(drop, ell), 0, 1)


def bezier(p0, p1, p2, n):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


def draw_rope(canvas, pts, width=8.0, ss=4):
    """灰色扭紋紙繩：深灰邊線、中灰本體、左上受光邊、斜向扭紋。pts 為 1x 座標。"""
    x0, y0 = np.floor(pts.min(0) - 20).astype(int)
    x1, y1 = np.ceil(pts.max(0) + 20).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W), min(y1, H)
    bw, bh = (x1 - x0) * ss, (y1 - y0) * ss
    p = (pts - [x0, y0]) * ss
    seq = [tuple(v) for v in p]
    layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.line(seq, fill=(46, 46, 50, 255), width=int((width + 3) * ss), joint="curve")
    core = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(core).line(seq, fill=255, width=int(width * ss), joint="curve")
    body = Image.new("RGBA", (bw, bh), (122, 122, 120, 255))
    dd = ImageDraw.Draw(body)
    # 切線與法線
    tang = np.gradient(p, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
    nor = np.stack([-tang[:, 1], tang[:, 0]], 1)
    if nor[len(nor) // 2, 0] > 0:  # 讓法線朝左（光從左上來）
        nor = -nor
    # 受光邊：沿左上側的細亮線
    hl = p + nor * width * 0.28 * ss
    dd.line([tuple(v) for v in hl], fill=(214, 214, 208, 255), width=int(width * 0.26 * ss), joint="curve")
    # 背光側：沿右下側的暗帶
    sh = p - nor * width * 0.30 * ss
    dd.line([tuple(v) for v in sh], fill=(92, 92, 92, 255), width=int(width * 0.30 * ss), joint="curve")
    # 扭紋：每 7 px 一道斜紋
    seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    step = 7 * ss
    for s in np.arange(step / 2, seglen[-1], step):
        i = int(np.searchsorted(seglen, s))
        i = min(i, len(p) - 1)
        c, t, n = p[i], tang[i], nor[i]
        a = c + n * width * 0.55 * ss - t * width * 0.45 * ss
        b = c - n * width * 0.55 * ss + t * width * 0.45 * ss
        dd.line([tuple(a), tuple(b)], fill=(78, 78, 78, 255), width=int(1.3 * ss))
    body.putalpha(core)
    layer = Image.alpha_composite(layer, body)
    layer = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    canvas.alpha_composite(layer, (x0, y0))


def draw_paper_loop(canvas, cx, cy, half_w, occluder, ss=4):
    """膝蓋正面的紙環：白色紙帶繞腿一圈。後緣被腿擋住（只畫在腿外的部分），前緣較粗壓在腿上。
    回傳前緣正中央的座標（紙繩接在這裡）。occluder＝角色 alpha（全畫面，0–255）。"""
    pad, ry = 16, 11
    bw, bh = int((half_w * 2 + pad * 2) * ss), int((ry * 2 + pad * 2) * ss)
    box = [pad * ss, pad * ss, bw - pad * ss, bh - pad * ss]
    back = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    db = ImageDraw.Draw(back)
    db.arc(box, 180, 360, fill=(70, 66, 62, 255), width=int(5 * ss))
    db.arc(box, 180, 360, fill=(214, 208, 198, 255), width=int(3 * ss))
    front = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    df = ImageDraw.Draw(front)
    df.arc(box, 0, 180, fill=(46, 46, 50, 255), width=int(8 * ss))
    df.arc(box, 0, 180, fill=(250, 248, 242, 255), width=int(5 * ss))
    back = back.resize((bw // ss, bh // ss), Image.LANCZOS)
    front = front.resize((bw // ss, bh // ss), Image.LANCZOS)
    x0, y0 = int(round(cx - back.width / 2)), int(round(cy - back.height / 2))
    occ = occluder[y0:y0 + back.height, x0:x0 + back.width].astype(np.float32) / 255.0
    ba = np.array(back)
    ba[..., 3] = (ba[..., 3] * (1 - occ)).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(ba, "RGBA"), (x0, y0))
    canvas.alpha_composite(front, (x0, y0))
    return float(cx), float(cy + ry)


def subtitle_strip(canvas, text, px):
    font, fname = find_font(px)
    d0 = ImageDraw.Draw(canvas)
    l, t, r, b = d0.textbbox((0, 0), text, font=font)
    tw, th = r - l, b - t
    pad_x, strip_h = 56, int(px * 1.72)
    sw = tw + pad_x * 2
    sx, sy = (W - sw) // 2, H - 30 - strip_h
    rng = np.random.default_rng(7)
    # 半透明深色紙條：左右手撕毛邊＋輕微紙紋
    m = np.zeros((strip_h, sw), np.float32)
    m[:, :] = 1
    edge = 10
    for side in (0, 1):
        prof = ndimage.gaussian_filter1d(rng.normal(0, 1, strip_h), 3)
        prof = (prof - prof.min()) / (np.ptp(prof) + 1e-9) * edge
        for y in range(strip_h):
            k = int(prof[y])
            if side == 0:
                m[y, :k] = 0
            else:
                m[y, sw - k:] = 0
    m = ndimage.gaussian_filter(m, 0.8)
    grain = ndimage.gaussian_filter(rng.normal(0, 1, (strip_h, sw)), 1.2) * 6
    col = np.empty((strip_h, sw, 4), np.float32)
    col[..., 0] = 30 + grain
    col[..., 1] = 27 + grain
    col[..., 2] = 31 + grain
    col[..., 3] = m * 0.74 * 255
    strip = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), "RGBA")
    canvas.alpha_composite(strip, (sx, sy))
    d = ImageDraw.Draw(canvas)
    tx = (W - tw) // 2 - l
    ty = sy + (strip_h - th) // 2 - t
    d.text((tx, ty), text, font=font, fill=(255, 255, 255, 255),
           stroke_width=2, stroke_fill=(20, 18, 20, 255))
    return dict(font=fname, px=px, strip=[sx, sy, sw, strip_h], text_bbox=[tx + l, ty + t, tw, th])


MAIN_COSTUME = {
    # 角色主色＝面積最大、最能代表角色的服裝色（色相範圍°、HSV 飽和度下限、明度上下限）
    "ale": ("深藍工作圍裙", (200, 250), 0.22, (0.0, 0.60)),
    "xiaoqing": ("湖水綠吊帶褲", (160, 200), 0.30, (0.0, 1.0)),
    "xiaoyu": ("橘紅連帽外套", (345, 25), 0.55, (0.25, 1.0)),
}


def costume_mask(rgb, base_mask, spec):
    """以色相／飽和度找出主色服裝像素（在原始顏色上判斷，再拿投影模擬後的顏色量測）。"""
    _, (h0, h1), smin, (vmin, vmax) = spec
    a = rgb.astype(np.float32) / 255.0
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-6
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = (mx - mn) / (mx + 1e-6)
    hue_ok = (h >= h0) | (h <= h1) if h0 > h1 else (h >= h0) & (h <= h1)
    m = base_mask & hue_ok & (sat >= smin) & (mx >= vmin) & (mx <= vmax)
    return ndimage.binary_opening(m, iterations=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=str(ROOT / "assets/generated/bg-square_v01.png"))
    ap.add_argument("--out-dir", default=str(ROOT / "review/G2"))
    ap.add_argument("--child-ratio", type=float, default=CHILD_RATIO)
    ap.add_argument("--lift", type=float, default=BG_LIFT)
    ap.add_argument("--drop", type=float, default=DROP_SHADOW)
    args = ap.parse_args()
    globals()["BG_LIFT"] = args.lift
    globals()["DROP_SHADOW"] = args.drop
    assert 0.62 <= args.child_ratio <= 0.68
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    stage = Image.open(args.stage).convert("RGB").resize((W, H), Image.LANCZOS)
    stage_raw = np.array(stage).astype(np.float32)
    stage_np = stage_grade(stage_raw)

    placed = []
    for key, rel, cxr, child in CHARS:
        im = trim(Image.open(ROOT / rel).convert("RGBA"))
        target_h = ADULT_H * (args.child_ratio if child else 1.0)
        s = target_h / im.height
        im = im.resize((round(im.width * s), round(target_h)), Image.LANCZOS)
        x = round(W * cxr - im.width / 2)
        y = FEET_Y - im.height
        full = np.zeros((H, W), np.uint8)
        full[y:y + im.height, x:x + im.width] = np.array(im.getchannel("A"))
        placed.append(dict(key=key, im=im, x=x, y=y, alpha=full, child=child, scale=s))

    # 陰影（先畫在景板上）
    shaded = stage_np.copy()
    for p in placed:
        sh = char_shadow(p["alpha"], FEET_Y, p["x"], p["x"] + p["im"].width)
        shaded = multiply_shadow(shaded, sh, 1.0)
    canvas = Image.fromarray(np.clip(shaded, 0, 255).astype(np.uint8)).convert("RGBA")
    for p in placed:
        canvas.alpha_composite(p["im"], (p["x"], p["y"]))
    chars_only = canvas.copy()

    # 紙繩測試：從畫面上緣經過淺色背景（避開頭頸），再經過阿樂叔叔的圍裙與褲子，止於右膝正面的紙環
    ale = placed[0]
    a = ale["alpha"]
    top, bot = ale["y"], FEET_Y
    hgt = bot - top
    head_rows = slice(top, top + int(hgt * 0.20))           # 頭＋頸（約 1.25 頭高）
    head_cols = np.nonzero(a[head_rows].max(0) > 16)[0]
    head_right = head_cols.max()
    knee_y = top + int(hgt * 0.735)
    cols = np.nonzero(a[knee_y] > 128)[0]
    runs = np.split(cols, np.nonzero(np.diff(cols) > 1)[0] + 1)
    leg = max(runs, key=lambda r: r.mean())                  # 畫面右側那條腿
    knee_x = float(leg.mean())
    half_leg = (leg.max() - leg.min()) / 2
    loop_cy = knee_y + 2
    p0 = np.array([head_right + 70.0, -12.0])
    p2 = np.array([knee_x, loop_cy + 11.0 - 1.5])   # 接在紙環前緣正中央
    p1 = np.array([p0[0] + 6, (p0[1] + p2[1]) * 0.5])
    pts = bezier(p0, p1, p2, 1400)
    # 檢查：紙繩在頭頸列的位置都在頭部右緣 40 px 以外
    in_head = (pts[:, 1] >= head_rows.start) & (pts[:, 1] < head_rows.stop)
    head_clear = float((pts[in_head, 0] - head_right).min()) if in_head.any() else None
    draw_rope(canvas, pts)
    draw_paper_loop(canvas, knee_x, loop_cy, half_leg + 6, ale["alpha"])

    sub = subtitle_strip(canvas, SUB_TEXT, SUB_PX)
    final = canvas.convert("RGB")
    final.save(out / "stage_composite.png")

    # 4:3 黑邊版：16:9 畫面縮到 1440 寬、上下黑邊
    k43 = Image.new("RGB", (1440, 1080), (0, 0, 0))
    k43.paste(final.resize((1440, 810), Image.LANCZOS), (0, 135))
    k43.save(out / "stage_composite_43.png")

    # ---- 量測（投影模擬後）----
    proj_stage = projector(np.array(Image.fromarray(np.clip(shaded, 0, 255).astype(np.uint8))))
    proj_chars = projector(np.array(chars_only.convert("RGB")))
    proj_final = projector(np.array(final))
    any_char = np.zeros((H, W), bool)
    for p in placed:
        any_char |= p["alpha"] > 128
    report = dict(note="明度對比為 WCAG 相對亮度比，量測在 tools/projsim.py 的投影模擬（壓縮對比、抬高黑位、降彩度）之後；"
                       "主色＝各角色指定服裝色（MAIN_COSTUME）；相鄰背景＝輪廓外 6–34 px 環帶（不含其他角色），"
                       "分成景片（地平線以上）與地面兩部分。",
                  stage_grade=dict(horizon_y=HORIZON_Y, lift=BG_LIFT, desat=BG_DESAT, ground_gain=GROUND_GAIN,
                                   drop_shadow=DROP_SHADOW),
                  child_ratio=args.child_ratio, adult_height_px=ADULT_H, feet_y=FEET_Y, characters={})
    chars_rgb = np.array(chars_only.convert("RGB"))
    for p in placed:
        m = p["alpha"] > 200
        ring = ndimage.binary_dilation(m, iterations=34) & ~ndimage.binary_dilation(m, iterations=6) & ~any_char
        ring[FEET_Y - 6:, :] = False                           # 腳底以下另外量（白邊對地面）
        above = ring.copy(); above[HORIZON_Y:, :] = False      # 景片（地平線以上）
        below = ring & ~above                                   # 地面
        spec = MAIN_COSTUME[p["key"]]
        cm = costume_mask(chars_rgb, ndimage.binary_erosion(m, iterations=3), spec)
        main_rgb = np.median(proj_chars[cm], 0)
        ml = float(rel_lum(main_rgb))

        def stats(sel):
            if sel.sum() < 50:
                return None
            l = rel_lum(proj_stage[sel])
            med, p10 = float(np.median(l)), float(np.percentile(l, 10))
            return dict(pixels=int(sel.sum()), median_lum=round(med, 4), p10_lum=round(p10, 4),
                        contrast_median=round(contrast(ml, med), 2), contrast_p10=round(contrast(ml, p10), 2))
        foot = m.copy()
        foot[:FEET_Y - int(p["im"].height * 0.06), :] = False
        edge = foot & ~ndimage.binary_erosion(m, iterations=4)
        edge_px = proj_chars[edge]
        edge_l = float(np.median(rel_lum(edge_px))) if len(edge_px) else None
        gx0, gx1 = p["x"], p["x"] + p["im"].width
        ground = proj_stage[FEET_Y + 25:FEET_Y + 45, gx0:gx1].reshape(-1, 3)
        ground_l = float(np.median(rel_lum(ground)))
        report["characters"][p["key"]] = dict(
            placed_box=[p["x"], p["y"], p["im"].width, p["im"].height],
            main_costume=spec[0], main_pixels=int(cm.sum()),
            main_color_proj=main_rgb.round().astype(int).tolist(), main_lum=round(ml, 4),
            ring_backdrop=stats(above), ring_ground=stats(below), ring_all=stats(ring),
            white_edge_at_feet_lum=round(edge_l, 4) if edge_l is not None else None,
            ground_under_feet_lum=round(ground_l, 4),
            contrast_white_edge_vs_ground=round(contrast(edge_l, ground_l), 2) if edge_l is not None else None,
        )
    # 紙繩：比較繩心與兩側背景
    rope_checks = []
    for frac in (0.12, 0.25, 0.70, 0.85):
        i = int(frac * (len(pts) - 1))
        cx, cy = pts[i]
        t = pts[min(i + 5, len(pts) - 1)] - pts[max(i - 5, 0)]
        t /= np.linalg.norm(t)
        n = np.array([-t[1], t[0]])
        def patch(x, y, r):
            x, y = int(round(x)), int(round(y))
            return np.median(proj_final[max(y - r, 0):y + r + 1, max(x - r, 0):x + r + 1].reshape(-1, 3), 0)
        core = patch(cx, cy, 1)
        side = [patch(cx + n[0] * d, cy + n[1] * d, 3) for d in (-18, 18)]
        over_char = bool(any_char[int(round(cy)), int(round(cx))])
        prof = [float(rel_lum(proj_final[int(round(cy + n[1] * d)), int(round(cx + n[0] * d))])) for d in np.arange(-5, 5.5, 0.5)]
        side_l = [float(rel_lum(s_)) for s_ in side]
        rope_checks.append(dict(at=[round(float(cx)), round(float(cy))], over_character=over_char,
                                core_lum=round(float(rel_lum(core)), 4),
                                side_lum=[round(float(rel_lum(s_)), 4) for s_ in side],
                                contrast=[round(contrast(float(rel_lum(core)), float(rel_lum(s_))), 2) for s_ in side],
                                cross_section_lum=[round(min(prof), 4), round(max(prof), 4)],
                                best_contrast_vs_sides=[round(max(contrast(min(prof), sl), contrast(max(prof), sl)), 2) for sl in side_l]))
    report["rope"] = dict(width_px=8, note="繩心為中灰；在淺色背景靠深灰邊線、在深色衣服靠左上受光邊拉開明度，cross_section 為橫切面最暗／最亮。", head_clearance_px=round(head_clear, 1) if head_clear is not None else None,
                          attach="右膝正面（紙環）", samples=rope_checks)
    report["subtitle"] = sub
    (out / "contrast.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
