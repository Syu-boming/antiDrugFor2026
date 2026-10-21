"""G5 共用美術的共用函式：去背整理、自動檢查、退路臉部範圍量測與兩眼同閉模擬。"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from skimage import color as skc

ROOT = Path(__file__).resolve().parents[4]
FONT_PATH = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"


def font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size, index=10)
    except Exception:  # noqa: BLE001
        return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", size)


def hsv(rgb):
    rgb = rgb.astype(np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, (mx - mn) / (mx + 1e-6), mx


def lab_of(rgb):
    return skc.rgb2lab(rgb.astype(np.float32) / 255.0)


def bleed(a):
    m = a[..., 3] > 0
    if m.all() or not m.any():
        return a
    _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
    out = a.copy()
    out[~m, :3] = a[iy[~m], ix[~m], :3]
    return out


def clean_alpha(a, min_comp=200, keep_largest=None):
    """Codex 圖：alpha<24→0、≥250→255，移除小雜點。回傳 (清理後, 移除像素數)。"""
    a = a.copy()
    a[..., 3] = np.where(a[..., 3] < 24, 0, a[..., 3])
    a[..., 3] = np.where(a[..., 3] >= 250, 255, a[..., 3])
    lab, n = ndimage.label(a[..., 3] > 0)
    if n == 0:
        return a, 0
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    if keep_largest:
        order = np.argsort(sizes)[::-1][:keep_largest]
        keep = np.isin(lab, 1 + order)
    else:
        keep = np.isin(lab, 1 + np.nonzero(sizes >= min_comp)[0])
    removed = int(((a[..., 3] > 0) & ~keep).sum())
    a[~keep, 3] = 0
    return a, removed


def crop_pad(a, pad=16, pad_left=None):
    ys, xs = np.nonzero(a[..., 3] > 0)
    pl = pad if pad_left is None else pad_left
    x0, y0, x1, y1 = xs.min() - pl, ys.min() - pad, xs.max() + 1 + pad, ys.max() + 1 + pad
    crop = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x1, a.shape[1]), min(y1, a.shape[0])
    crop[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
    return bleed(crop), (int(x0), int(y0))


def edge_margins(a, th=128):
    m = a[..., 3] >= th
    ys, xs = np.nonzero(m)
    H, W = m.shape
    return {"left": int(xs.min()), "top": int(ys.min()), "right": int(W - 1 - xs.max()), "bottom": int(H - 1 - ys.max())}


def checks(a, raw=None, expect_touch=()):
    """自動檢查：霧邊、白邊、深色細線、裁切、平光。a＝最終 RGBA（uint8）。"""
    alpha = a[..., 3]
    m = alpha >= 128
    out = {}
    # 霧邊：離不透明範圍 > 3 px 還有 alpha>0 的像素
    dist_out = ndimage.distance_transform_edt(~m)
    fog = (alpha > 0) & (dist_out > 3)
    out["fog_px"] = int(fog.sum())
    out["semi_alpha_px"] = int(((alpha > 0) & (alpha < 255)).sum())
    out["semi_alpha_ratio_of_edge"] = round(out["semi_alpha_px"] / max(1, int((m ^ ndimage.binary_erosion(m)).sum())), 3)
    if raw is not None:
        ra = raw[..., 3]
        rm = ra >= 128
        rd = ndimage.distance_transform_edt(~rm)
        out["raw_fog_px"] = int(((ra > 0) & (ra < 24) & (rd > 3)).sum())
        out["raw_margins"] = edge_margins(raw)
        touch = [k for k, v in out["raw_margins"].items() if v <= 2]
        out["raw_touches_edge"] = touch
        out["crop_ok"] = all(t in expect_touch for t in touch)
    # 白邊：沿外輪廓往內 d px 的像素有多少是紙芯白
    din = ndimage.distance_transform_edt(m)
    lab = lab_of(a[..., :3])
    L, C = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    white = (L > 86) & (C < 14)
    dark = L < 50
    prof = []
    for d in range(1, 25):
        ring = m & (din > d - 1) & (din <= d)
        prof.append(round(float(white[ring].mean()), 3) if ring.any() else 0.0)
    out["white_profile_1_24"] = prof
    # 白邊起點：前 4 px 內第一個白色比例 ≥0.5 的環（有些圖白邊外還有 1–2 px 深色細線）
    start = next((i for i in range(4) if prof[i] >= 0.5), None)
    width = 0
    if start is not None:
        for f in prof[start:]:
            if f < 0.5:
                break
            width += 1
    out["white_border_start_px"] = start
    out["outer_dark_line"] = bool(start is not None and start >= 2)
    out["white_border_px"] = width
    end = (start or 0) + width
    ring_in = m & (din > end + 0.5) & (din <= end + 4.5)
    out["dark_line_inside_border"] = round(float(dark[ring_in].mean()), 3) if ring_in.any() else 0.0
    # 白邊連續性：白邊範圍內（去掉頭尾 1 px）的白色比例平均
    seg = prof[(start or 0) + 1:max((start or 0) + 2, end - 1)]
    out["white_border_coverage"] = round(float(np.mean(seg)), 3) if width >= 3 else 0.0
    out["white_border_ok"] = bool(width >= 6 and out["white_border_coverage"] >= 0.8)
    # 平光：角色內部（離邊 ≥ 20 px）左右半邊 L* 中位差
    core = m & (din > 20)
    ys, xs = np.nonzero(core)
    if len(xs):
        cx = np.median(xs)
        lft, rgt = core & (np.arange(a.shape[1])[None, :] < cx), core & (np.arange(a.shape[1])[None, :] >= cx)
        out["lr_L_median_diff"] = round(float(abs(np.median(L[lft]) - np.median(L[rgt]))), 1)
    # 暖色偏：全圖非膚色不透明處的平均 b*
    out["mean_b"] = round(float(lab[..., 2][core].mean()), 1) if core.any() else None
    return out


def garment_stats(a, hue, s_min=0.25, v_min=0.1, v_max=1.0, band=(0, 1)):
    rgb = a[..., :3]
    h, s, v = hsv(rgb)
    h0, h1 = hue
    inside = ((h >= h0) | (h <= h1)) if h0 > h1 else ((h >= h0) & (h <= h1))
    ys = np.nonzero(a[..., 3].max(1) > 0)[0]
    top, bot = ys.min(), ys.max()
    yy = np.arange(a.shape[0])[:, None]
    w = inside & (s > s_min) & (v > v_min) & (v <= v_max) & (a[..., 3] > 200) & (yy >= top + band[0] * (bot - top)) & (yy <= top + band[1] * (bot - top))
    w = ndimage.binary_opening(w, iterations=1)
    if w.sum() < 300:
        return None
    lab = lab_of(rgb)
    med = np.median(rgb[w], 0)
    return {"px": int(w.sum()), "L*": round(float(np.median(lab[..., 0][w])), 1),
            "median": "#%02X%02X%02X" % tuple(int(round(c)) for c in med),
            "lab": [round(float(np.median(lab[..., i][w])), 1) for i in range(3)]}


def delta_e(l1, l2):
    return round(float(np.sqrt(sum((x - y) ** 2 for x, y in zip(l1, l2)))), 1)


# ---------- 退路臉部：模擬 app/src/stage/face.ts 的 drawFallback（眼睛 closed／half） ----------

def sample_skin(a, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    pad = max(6, int((x1 - x0) * 0.35))
    H, W = a.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    sub = a[Y0:Y1, X0:X1].astype(np.float32)
    yy, xx = np.mgrid[Y0:Y1, X0:X1]
    inside = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    r, g, b, al = sub[..., 0], sub[..., 1], sub[..., 2], sub[..., 3]
    lum = r * 0.3 + g * 0.59 + b * 0.11
    ok = ~inside & (al >= 200) & (lum >= 150) & (r >= b + 40)
    if ok.sum() == 0:
        return np.array([246, 190, 145], np.float32)
    return np.array([r[ok].mean(), g[ok].mean(), b[ok].mean()], np.float32)


def fallback_slot_box(boxes, pad):
    x0 = min(b[0] - (b[2] - b[0]) * pad for b in boxes)
    y0 = min(b[1] - (b[3] - b[1]) * pad for b in boxes)
    x1 = max(b[2] + (b[2] - b[0]) * pad for b in boxes)
    y1 = max(b[3] + (b[3] - b[1]) * pad for b in boxes)
    return [math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)]


def render_eyes(a, fb, shape, ss=4):
    """在原圖上疊出退路眼睛換片（closed／half），回傳 RGB 陣列（全圖大小）與畫線遮罩。"""
    H, W = a.shape[:2]
    box = fallback_slot_box(fb["eyes"], 0.45)
    skin = sample_skin(a, [box[0], fb["eyes"][0][3], box[2], fb["eyes"][0][3] + 20])
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    layer = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    line = Image.new("L", (w * ss, h * ss), 0)
    dr = ImageDraw.Draw(layer)
    dl = ImageDraw.Draw(line)
    glasses = fb.get("glasses", False)
    k = fb.get("patchK", 1.08 if glasses else 1.3)
    patch = np.zeros((h * ss, w * ss), np.float32)
    yy, xx = np.mgrid[:h * ss, :w * ss]
    X = lambda v: (v - x0) * ss  # noqa: E731
    Y = lambda v: (v - y0) * ss  # noqa: E731
    for (ex0, ey0, ex1, ey1) in fb["eyes"]:
        cx, cy, rx, ry = (ex0 + ex1) / 2, (ey0 + ey1) / 2, (ex1 - ex0) / 2, (ey1 - ey0) / 2
        R = max(rx, ry) * k
        sx, sy = rx * k / R, ry * k / R
        d = np.hypot((xx - X(cx)) / sx, (yy - Y(cy)) / sy) / (R * ss)
        p = np.clip((1 - d) / 0.18, 0, 1)   # 0.82 以內實色、外 18% 羽化
        if shape == "half":
            p = p * (yy <= Y(cy + ry * 0.02))
        patch = np.maximum(patch, p)
        lw = max(2, ry * (0.22 if shape == "closed" else 0.2)) * ss
        if shape == "closed":
            pts = quad((X(cx - rx * 1.05), Y(cy + ry * 0.05)), (X(cx), Y(cy + ry * 0.16)), (X(cx + rx * 1.05), Y(cy + ry * 0.05)))
        else:
            pts = quad((X(cx - rx * 1.05), Y(cy)), (X(cx), Y(cy - ry * 0.18)), (X(cx + rx * 1.05), Y(cy)))
        dl.line(pts, fill=255, width=int(round(lw)), joint="curve")
    sub = a[y0:y1, x0:x1, :3].astype(np.float32)
    big = np.array(Image.fromarray(sub.astype(np.uint8)).resize((w * ss, h * ss), Image.NEAREST)).astype(np.float32)
    comp = big * (1 - patch[..., None]) + skin[None, None, :] * patch[..., None]
    ink = np.array([52, 34, 26], np.float32)
    lm = np.array(line).astype(np.float32) / 255 * 0.95
    comp = comp * (1 - lm[..., None]) + ink * lm[..., None]
    small = np.array(Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS))
    lsmall = np.array(Image.fromarray((lm * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)) > 60
    out = a[..., :3].copy()
    out[y0:y1, x0:x1] = small
    lmask = np.zeros((H, W), bool)
    lmask[y0:y1, x0:x1] = lsmall
    pfull = np.zeros((H, W), np.float32)
    pfull[y0:y1, x0:x1] = np.array(Image.fromarray((patch * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)).astype(np.float32) / 255
    render_eyes.last_patch = pfull
    return out, lmask, box


def quad(p0, p1, p2, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def blink_check(a, fb):
    """兩眼同閉檢查：每隻眼原本的深色眼珠＋淺色眼白／高光，在 closed 換片上還看得到多少（排除新畫的眼皮線）。"""
    lab0 = lab_of(a[..., :3])
    L0 = lab0[..., 0]
    Cc = np.hypot(lab0[..., 1], lab0[..., 2])
    din0 = ndimage.distance_transform_edt(a[..., 3] >= 128)
    res = {}
    for shape in ("closed", "half"):
        rgb, lmask, _ = render_eyes(a, fb, shape)
        L1 = lab_of(rgb)[..., 0]
        eyes = []
        for i, (ex0, ey0, ex1, ey1) in enumerate(fb["eyes"]):
            x0, y0, x1, y1 = int(math.floor(ex0)), int(math.floor(ey0)), int(math.ceil(ex1)), int(math.ceil(ey1))
            reg = np.zeros_like(L0, bool)
            reg[y0:y1, x0:x1] = True
            orig_dark = reg & (L0 < 45)
            orig_light = reg & (L0 > 88)   # 眼睛高光／眼白
            if fb.get("glasses"):
                # 戴眼鏡：鏡片反光不是眼睛，只檢查眼珠周圍 3 px 內的亮點
                orig_light &= ndimage.binary_dilation(orig_dark, iterations=3)
            still_dark = orig_dark & (L1 < 60) & ~ndimage.binary_dilation(lmask, iterations=1)
            # 半閉只看上半眼
            if shape == "half":
                cy = (ey0 + ey1) / 2
                top = np.zeros_like(reg)
                top[y0:int(cy), x0:x1] = True
                orig_dark &= top
                orig_light &= top
                still_dark &= top
            still_light = orig_light & (L1 > 88)
            # 溢出：補片（≥0.5）蓋到不屬於這隻眼的東西＝頭髮或臉緣線（不屬於眼睛的深色連通區）、白邊（離輪廓 <18 px 的白）、透明背景
            pf = render_eyes.last_patch
            cxe, cye = (ex0 + ex1) / 2, (ey0 + ey1) / 2
            own = np.zeros_like(reg)
            hx, hy = (ex1 - ex0) * 0.95, (ey1 - ey0) * 0.95
            own[max(0, int(cye - hy)):int(cye + hy), max(0, int(cxe - hx)):int(cxe + hx)] = True
            boxg = np.zeros_like(reg)
            boxg[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = True
            dk = (L0 < 55) & own
            lbd, nd = ndimage.label(dk)
            eye_mask = np.zeros_like(reg)
            for j in range(1, nd + 1):
                cmp_ = lbd == j
                if (cmp_ & boxg).sum() >= 0.6 * cmp_.sum():
                    eye_mask |= cmp_
            eye_mask = ndimage.binary_dilation(eye_mask, iterations=1)
            prot = (a[..., 3] < 128) | ((L0 > 88) & (Cc < 12) & (din0 < 18)) | ((L0 < 55) & ~eye_mask)
            spill = int((own & (pf >= 0.5) & prot).sum())
            line_px = int((lmask & reg).sum()) if shape == "closed" else int(lmask[y0 - 3:y1 + 3, x0 - 3:x1 + 3].sum())
            eyes.append({"eye": i, "orig_dark_px": int(orig_dark.sum()), "residual_dark_px": int(still_dark.sum()),
                         "residual_ratio": round(float(still_dark.sum() / max(1, orig_dark.sum())), 4),
                         "highlight_left_px": int(still_light.sum()), "lid_line_px": line_px, "spill_px": spill})
        ok = all(e["residual_ratio"] <= 0.03 and e["highlight_left_px"] <= 2 and e["lid_line_px"] >= 15 and e["spill_px"] <= 25 for e in eyes)
        res[shape] = {"eyes": eyes, "ok": bool(ok)}
    res["both_closed_ok"] = res["closed"]["ok"]
    return res


# ---------- 退路臉部範圍自動量測（深色連通區；結果要人工看放大圖確認） ----------

def detect_face(a, head_frac=0.32, region=None):
    """在頭部範圍找膚色區裡的深色連通區：回傳候選框 [(x0,y0,x1,y1,area,mean_y)]。region＝手動指定的頭部框。"""
    H, W = a.shape[:2]
    m = a[..., 3] >= 128
    ys, xs = np.nonzero(m)
    top, bot = ys.min(), ys.max()
    if region is None:
        region = (xs.min(), top, xs.max() + 1, int(top + head_frac * (bot - top)))
    x0, y0, x1, y1 = region
    sub = a[y0:y1, x0:x1]
    h, s, v = hsv(sub[..., :3])
    skin = (h > 5) & (h < 45) & (s > 0.12) & (s < 0.7) & (v > 0.62) & (sub[..., 3] > 200)
    skin = ndimage.binary_opening(skin, iterations=1)
    lb, n = ndimage.label(skin)
    if n == 0:
        return [], region
    sizes = ndimage.sum(skin, lb, range(1, n + 1))
    # 所有夠大的膚色區（眼鏡鏡片裡的膚色另成一區，眼珠是它的洞）
    face = np.isin(lb, 1 + np.nonzero(sizes >= max(200, 0.02 * sizes.max()))[0])
    holes = np.zeros_like(face)
    for i in 1 + np.nonzero(sizes >= max(200, 0.02 * sizes.max()))[0]:
        comp = lb == i
        holes |= ndimage.binary_fill_holes(comp) & ~comp
    L = lab_of(sub[..., :3])[..., 0]
    dark = holes & (L < 55)
    dl, dn = ndimage.label(dark)
    cands = []
    for i, sl in enumerate(ndimage.find_objects(dl), 1):
        comp = dl[sl] == i
        area = int(comp.sum())
        if area < 12:
            continue
        cy, cx = ndimage.center_of_mass(comp)
        cands.append([int(sl[1].start + x0), int(sl[0].start + y0), int(sl[1].stop + x0), int(sl[0].stop + y0), area,
                      round(float(cy + sl[0].start + y0), 1)])
    cands.sort(key=lambda c: -c[4])
    return cands, [int(v) for v in region]


def alpha_ref(a):
    m = a[..., 3] >= 128
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min())]


def zoom_face(a, fb, scale=4, label=""):
    """臉部放大：原圖／眼框＋嘴框／半閉／閉眼（四格）。"""
    eyes = fb["eyes"]
    allb = eyes + [fb["mouth"]]
    x0 = int(min(b[0] for b in allb) - 40)
    y0 = int(min(b[1] for b in allb) - 40)
    x1 = int(max(b[2] for b in allb) + 40)
    y1 = int(max(b[3] for b in allb) + 30)
    H, W = a.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    bg = np.array([232, 226, 214], np.float32)

    def flat(rgb):
        al = a[..., 3:4].astype(np.float32) / 255
        return (rgb.astype(np.float32) * al + bg * (1 - al)).astype(np.uint8)

    tiles = []
    base = flat(a[..., :3])
    t0 = Image.fromarray(base[y0:y1, x0:x1])
    t1 = t0.copy()
    tiles.append(("原圖", t0))
    d = ImageDraw.Draw(t1)
    for b in eyes:
        d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(0, 160, 255))
    b = fb["mouth"]
    d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 60, 160))
    tiles.append(("眼框／嘴框", t1))
    for shape in ("half", "closed"):
        rgb, _, _ = render_eyes(a, fb, shape)
        tiles.append((shape, Image.fromarray(flat(rgb)[y0:y1, x0:x1])))
    w, h = (x1 - x0) * scale, (y1 - y0) * scale
    sheet = Image.new("RGB", (w * len(tiles) + 10 * (len(tiles) + 1), h + 46), (40, 40, 40))
    dd = ImageDraw.Draw(sheet)
    f = font(20)
    for i, (name, t) in enumerate(tiles):
        sheet.paste(t.resize((w, h), Image.NEAREST), (10 + i * (w + 10), 36))
        dd.text((10 + i * (w + 10), 6), f"{label} {name}", fill=(255, 255, 255), font=f)
    return sheet
