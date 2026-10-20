"""G4 美術：臉部換片（嘴 5 種、眼 3 種）＋ face.json ＋ review/G4/art/face_sheet.png。

做法（不重新生成臉，避免變臉）：
- 以原圖為底，只在嘴、眼的局部做「蓋片」：原特徵用調和填補（Laplace）＋同一張臉的紙紋高頻補成皮膚，
  再用程式畫剪紙風的新嘴型／眼皮線（4 倍超取樣抗鋸齒，顏色取自原圖的線色、口腔色、舌色）。
- 每片都是同一個框（同錨點、同尺寸），alpha 只蓋住「原特徵＋新特徵」範圍並羽化 1–2 px；
  框內的眉毛、鬍子、眼鏡框、髮絲等深色線一律不蓋（alpha＝0），所以換片時臉型、膚色、髮型、眼鏡都不會變。
- 原圖本來就有的表情直接當作其中一片（小晴、小宇的「圓唇」＝原圖驚訝嘴；阿樂的「擔心抿嘴」＝原圖困惑嘴；三人的「睜眼」＝原圖眼睛）。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_faces.py
"""
import json
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
FACE_DIR = ROOT / "assets/final/face"
FONT = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
SS = 4  # 超取樣倍數

CHARS = {
    "xiaoqing": dict(
        zh="小晴", head=ROOT / "assets/final/chr-xiaoqing_pose-reach-worried_v04.png",
        head_note="頭部圖＝整張姿勢圖 chr-xiaoqing_pose-reach-worried（裁切後；座標以裁切後的圖為準）",
        tilt=19.5, mouth_c=(494, 364), mouth_box=(456, 330, 534, 404),
        eyes=[(474, 290), (569, 318)], eyes_box=(440, 238, 612, 362),
        eye_boxes=[(452, 266, 497, 315), (543, 286, 599, 349)],
        eye_ellipses=[(474, 284, 22, 30, 10), (570, 316, 28, 31, 10)],
        original_mouth="mouth_round", stage_scale=0.32,
        mouth_scale=1.0, lw=3.5, lid_lw=5.0),
    "xiaoyu": dict(
        zh="小宇", head=ROOT / "assets/final/chr-xiaoyu_pose-stepback-surprised_v04.png",
        head_note="頭部圖＝整張姿勢圖 chr-xiaoyu_pose-stepback-surprised（裁切後；座標以裁切後的圖為準）",
        tilt=22.0, mouth_c=(485, 380), mouth_box=(450, 346, 524, 416),
        eyes=[(466, 282), (552, 318)], eyes_box=(444, 248, 586, 356),
        eye_boxes=[(450, 256, 489, 313), (533, 292, 581, 351)],
        eye_ellipses=[(470, 285, 17.5, 27, 15), (558, 321, 22, 30, 15)],
        original_mouth="mouth_round", stage_scale=0.30,
        mouth_scale=0.92, lw=3.3, lid_lw=4.6),
    "ale": dict(
        zh="阿樂叔叔", head=ROOT / "assets/final/rig/chr-ale_head-worried_v04.png",
        head_note="頭部圖＝分件困惑頭 chr-ale_head-worried_v04（rig 部件，與 head 同樞紐）",
        tilt=7.5, mouth_c=(161, 230), mouth_box=(128, 219, 198, 252),
        eyes=[(142, 171), (203, 179)], eyes_box=(124, 150, 222, 200),
        eye_boxes=[(128, 152, 157, 191), (190, 161, 216, 198)], eye_dark_only=True,
        original_mouth="mouth_worried", stage_scale=0.39,
        mouth_scale=1.0, lw=3.0, lid_lw=3.4,
        mouth_search=(140, 223, 182, 238)),
}


# ---------------------------------------------------------------- 工具
def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def rot(tilt):
    t = math.radians(tilt)
    return np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])


def to_img(c, tilt, u, v):
    """特徵座標（u 沿臉的水平線、v 往下）→ 影像座標"""
    R_ = rot(tilt)
    p = R_ @ np.stack([np.asarray(u, float), np.asarray(v, float)])
    return p[0] + c[0], p[1] + c[1]


def skin_stats(a, box, exclude):
    x0, y0, x1, y1 = box
    sub = a[y0:y1, x0:x1, :3].astype(np.float32)
    ex = exclude[y0:y1, x0:x1]
    L = lum(sub)
    m = (~ex) & (L > np.percentile(L[~ex], 30)) & (a[y0:y1, x0:x1, 3] > 200)
    med = np.median(sub[m], 0)
    d = np.abs(sub - med).sum(-1)
    m &= d < 40
    return np.median(sub[m], 0), m


def harmonic_fill(a, F, skin, protect, iters=700):
    """F 內用 Laplace 調和填補；邊界若是深色線（protect）就當作皮膚色，避免把線色抹進來。"""
    ys, xs = np.nonzero(F)
    if len(ys) == 0:
        return a
    y0, y1 = max(ys.min() - 3, 0), ys.max() + 4
    x0, x1 = max(xs.min() - 3, 0), xs.max() + 4
    sub = a[y0:y1, x0:x1, :3].astype(np.float32).copy()
    f = F[y0:y1, x0:x1]
    pr = protect[y0:y1, x0:x1] & ~f
    sub[pr] = skin
    sub[f] = skin
    for _ in range(iters):
        nb = (np.roll(sub, 1, 0) + np.roll(sub, -1, 0) + np.roll(sub, 1, 1) + np.roll(sub, -1, 1)) / 4
        sub[f] = nb[f]
    out = a.copy()
    out[y0:y1, x0:x1, :3][f] = np.clip(sub[f], 0, 255).astype(np.uint8)
    return out


def paper_grain(a, F, skin_mask_full, seed=1):
    """填補區補紙紋：量同一張臉皮膚區的高頻強度（原圖－模糊），用同強度的細顆粒雜訊補回（不搬別處的線條）。"""
    fy, fx = np.nonzero(F)
    ys, xs = np.nonzero(skin_mask_full)
    if len(fy) == 0 or len(ys) < 50:
        return a
    L = a[..., :3].astype(np.float32)
    hp = L - ndimage.gaussian_filter(L, (1.6, 1.6, 0))
    hv = hp[ys, xs]
    std = 1.4826 * np.median(np.abs(hv - np.median(hv, 0)), 0)   # 穩健估計，不被線條、腮紅邊拉高
    rng = np.random.default_rng(seed)
    y0, y1, x0, x1 = fy.min(), fy.max() + 1, fx.min(), fx.max() + 1
    n = ndimage.gaussian_filter(rng.standard_normal((y1 - y0, x1 - x0)), 0.7)
    n /= n.std() + 1e-6
    out = a.copy()
    v = L[fy, fx] + n[fy - y0, fx - x0][:, None] * std[None, :] * 0.8
    out[fy, fx, :3] = np.clip(v, 0, 255).astype(np.uint8)
    return out


def feature_mask_dark(a, c, box, thr):
    """以中心點所在的深色連通區為特徵（眼珠、嘴線）"""
    x0, y0, x1, y1 = box
    L = lum(a[..., :3].astype(np.float32))
    dark = np.zeros(L.shape, bool)
    dark[y0:y1, x0:x1] = (L[y0:y1, x0:x1] < thr) & (a[y0:y1, x0:x1, 3] > 128)
    lab, n = ndimage.label(dark)
    if n == 0:
        return dark
    cx, cy = int(round(c[0])), int(round(c[1]))
    k = lab[cy, cx]
    if k == 0:
        # 找離中心最近的連通區
        d = ndimage.distance_transform_edt(lab == 0, return_indices=True)[1]
        k = lab[d[0][cy, cx], d[1][cy, cx]]
    return lab == k


# ---------------------------------------------------------------- 畫圖（4 倍超取樣）
class Canvas:
    def __init__(self, box):
        self.box = box
        w, h = box[2] - box[0], box[3] - box[1]
        self.im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def P(self, x, y):
        return [((xx - self.box[0]) * SS, (yy - self.box[1]) * SS) for xx, yy in zip(np.atleast_1d(x), np.atleast_1d(y))]

    def stroke(self, xs, ys, width, color, taper=False):
        pts = self.P(xs, ys)
        n = len(pts)
        for i in range(n):
            t = i / max(n - 1, 1)
            w = width * (0.35 + 0.65 * math.sin(math.pi * t) ** 0.6) if taper else width
            r = w * SS / 2
            x, y = pts[i]
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=color)
            if i:
                self.d.line([pts[i - 1], pts[i]], fill=color, width=max(1, int(round(w * SS))))

    def poly(self, xs, ys, color):
        self.d.polygon(self.P(xs, ys), fill=color)

    def result(self):
        w, h = self.box[2] - self.box[0], self.box[3] - self.box[1]
        return np.array(self.im.resize((w, h), Image.LANCZOS))


def mouth_shapes(cfg, cols):
    """回傳 {變體: 畫圖函式(canvas)}；u/v 單位為頭部圖像素"""
    c, tilt, s, lw = cfg["mouth_c"], cfg["tilt"], cfg["mouth_scale"], cfg["lw"]
    line, inside, tongue = cols
    ale = cfg.get("mouth_search") is not None

    def curve(u, v):
        return to_img(c, tilt, u, v)

    def open_shape(cv, half_w, top, bot, t_ry, t_cy, flat_top=False):
        u = np.linspace(-half_w, half_w, 60)
        k = np.clip(1 - (u / half_w) ** 2, 0, 1)
        vt = -top * (k ** (1.2 if flat_top else 0.85))
        vb = bot * (k ** 0.7)
        xs, ys = curve(np.concatenate([u, u[::-1]]), np.concatenate([vt, vb[::-1]]))
        # 口腔
        cv.poly(xs, ys, tuple(int(x) for x in inside) + (255,))
        # 舌頭（只留在嘴裡）
        tmp = Canvas(cv.box)
        tu = np.linspace(-half_w * 0.62, half_w * 0.62, 40)
        tk = np.clip(1 - (tu / (half_w * 0.62)) ** 2, 0, 1)
        txs, tys = curve(np.concatenate([tu, tu[::-1]]), np.concatenate([t_cy - t_ry * tk ** 0.5, (t_cy + t_ry * 2.0 * tk ** 0.5)[::-1]]))
        tmp.poly(txs, tys, tuple(int(x) for x in tongue) + (255,))
        mouth_m = Image.new("L", cv.im.size, 0)
        ImageDraw.Draw(mouth_m).polygon(cv.P(xs, ys), fill=255)
        tl = tmp.im.copy()
        tl.putalpha(Image.fromarray(np.minimum(np.array(tl)[..., 3], np.array(mouth_m))))
        cv.im.alpha_composite(tl)
        # 外框
        cv.stroke(np.append(xs, xs[0]), np.append(ys, ys[0]), lw * 0.85, tuple(int(x) for x in line) + (255,))

    shapes = {}

    def closed(cv):
        u = np.linspace(-11 * s, 11 * s, 40) * (1.25 if ale else 1)
        v = (0.5 if ale else -0.45) * (u / u.max()) ** 2 + (0.0 if ale else 0.2)
        xs, ys = curve(u, v)
        cv.stroke(xs, ys, lw, tuple(int(x) for x in line) + (255,), taper=True)

    def half(cv):
        if ale:
            open_shape(cv, 12, 1.2, 7.5, 2.2, 5.0, flat_top=True)
        else:
            open_shape(cv, 11 * s, 1.6, 9.5 * s, 2.8 * s, 6.2 * s, flat_top=True)

    def opened(cv):
        if ale:
            open_shape(cv, 13.5, 2.0, 12.5, 3.2, 8.5)
        else:
            open_shape(cv, 15.5 * s, 6.5 * s, 17.5 * s, 4.8 * s, 11 * s)

    def rounded(cv):
        # 圓唇：小圓口（阿樂用；孩子的圓唇用原圖）
        t = np.linspace(0, 2 * np.pi, 80)
        u, v = 7.5 * np.cos(t), 2.5 + 6.5 * np.sin(t)
        xs, ys = curve(u, v)
        cv.poly(xs, ys, tuple(int(x) for x in inside) + (255,))
        tu, tv = 4.6 * np.cos(t), 5.6 + 2.6 * np.sin(t)
        txs, tys = curve(tu, tv)
        cv.poly(txs, tys, tuple(int(x) for x in tongue) + (255,))
        cv.stroke(np.append(xs, xs[0]), np.append(ys, ys[0]), lw * 0.85, tuple(int(x) for x in line) + (255,))

    def worried(cv):
        u = np.linspace(-8.5 * s, 8.5 * s, 50)
        v = 1.6 * s * (np.abs(u) / (8.5 * s)) ** 1.7 + 0.75 * s * np.sin(u / (8.5 * s) * 2.4 * np.pi) - 0.3
        xs, ys = curve(u, v)
        cv.stroke(xs, ys, lw * 0.95, tuple(int(x) for x in line) + (255,), taper=True)

    shapes["mouth_closed"] = closed
    shapes["mouth_half"] = half
    shapes["mouth_open"] = opened
    if cfg["original_mouth"] != "mouth_round":
        shapes["mouth_round"] = rounded
    if cfg["original_mouth"] != "mouth_worried":
        shapes["mouth_worried"] = worried
    return shapes


# ---------------------------------------------------------------- 主流程
def build(name, cfg):
    a = np.array(Image.open(cfg["head"]).convert("RGBA"))
    H, W = a.shape[:2]
    tilt = cfg["tilt"]
    L = lum(a[..., :3].astype(np.float32))
    out_dir = FACE_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {"pieces": {}}

    # ---- 嘴
    mb = cfg["mouth_box"]
    if cfg.get("mouth_search"):
        sx0, sy0, sx1, sy1 = cfg["mouth_search"]
        m0 = np.zeros((H, W), bool)
        m0[sy0:sy1, sx0:sx1] = (L[sy0:sy1, sx0:sx1] < 120)
        mouth_m = m0
    else:
        # 孩子的嘴：深色外框＋口腔＋舌頭（非膚色的連通區，填洞）
        skin0, _ = skin_stats(a, mb, np.zeros((H, W), bool))
        dist = np.abs(a[..., :3].astype(np.float32) - skin0).sum(-1)
        cand = np.zeros((H, W), bool)
        x0, y0, x1, y1 = mb
        cand[y0:y1, x0:x1] = dist[y0:y1, x0:x1] > 60
        lab, _ = ndimage.label(cand)
        k = lab[cfg["mouth_c"][1], cfg["mouth_c"][0]]
        mouth_m = ndimage.binary_fill_holes(lab == k) if k else cand
    mouth_m = ndimage.binary_dilation(mouth_m, iterations=2)
    # 深色保護線（鬍子、髮絲、眼鏡框…）：框內深色但不是特徵本身
    protect_all = (L < 125) & (a[..., 3] > 128)
    skin, skin_m_box = skin_stats(a, mb, mouth_m | protect_all)
    skin_full = np.zeros((H, W), bool)
    skin_full[mb[1]:mb[3], mb[0]:mb[2]] = skin_m_box
    clean = harmonic_fill(a, mouth_m, skin, protect_all & ~mouth_m)
    clean = paper_grain(clean, mouth_m, skin_full & ~mouth_m, seed=zlib.crc32(name.encode()) % 1000)
    # 取色
    if cfg.get("mouth_search"):
        line = np.median(a[mouth_m & (L < 100)][:, :3], 0)
        inside, tongue = np.array([118, 48, 44]), np.array([214, 116, 100])
    else:
        mm = mouth_m & (a[..., 3] > 128)
        px = a[mm][:, :3].astype(np.float32)
        Lp = lum(px)
        line = np.minimum(np.median(px[Lp < np.percentile(Lp, 18)], 0), np.array([78, 40, 34]))
        redish = px[(Lp > np.percentile(Lp, 25)) & (Lp < np.percentile(Lp, 55))]
        inside = np.median(redish, 0)
        tongue = np.median(px[Lp > np.percentile(Lp, 80)], 0)
    cols = (line, inside, tongue)
    rec["colors"] = {"line": [int(x) for x in line], "inside": [int(x) for x in inside], "tongue": [int(x) for x in tongue]}
    protect_m = protect_all & ~ndimage.binary_dilation(mouth_m, iterations=1)
    pieces_m = {}
    for var, fn in mouth_shapes(cfg, cols).items():
        cv = Canvas(mb)
        fn(cv)
        draw = cv.result()
        pieces_m[var] = draw
    pieces_m[cfg["original_mouth"]] = None
    write_group(name, "mouth", mb, a, clean, mouth_m, protect_m, pieces_m, out_dir, rec)

    # ---- 眼
    eb = cfg["eyes_box"]
    eye_masks, eye_core = [], []
    skin_e0, _ = skin_stats(a, eb, protect_all)
    dist_e = np.abs(a[..., :3].astype(np.float32) - skin_e0).sum(-1)
    yy_, xx_ = np.mgrid[:H, :W]
    for i, (c, ebx) in enumerate(zip(cfg["eyes"], cfg["eye_boxes"])):
        x0, y0, x1, y1 = ebx
        box = np.zeros((H, W), bool)
        box[y0:y1, x0:x1] = True
        if cfg.get("eye_ellipses"):
            # 孩子：手量的眼睛橢圓（含上睫毛、眼珠、眼白月牙）；橢圓內整個重填，
            # 但「伸出橢圓外的深色連通區」（髮絲、眼鏡框、鼻樑線）是保護線，不填不蓋
            ex, ey, ea, eb_, th = cfg["eye_ellipses"][i]
            t = math.radians(th)
            dx, dy = xx_ - ex, yy_ - ey
            u = dx * math.cos(t) + dy * math.sin(t)
            v = -dx * math.sin(t) + dy * math.cos(t)
            ell = (u / ea) ** 2 + (v / eb_) ** 2 <= 1
            ell_big = (u / (ea + 4)) ** 2 + (v / (eb_ + 4)) ** 2 <= 1
            darkish = ((L < 135) | (dist_e > 110)) & (a[..., 3] > 128) & ell_big
            lab, n = ndimage.label(darkish)
            prot = np.zeros((H, W), bool)
            for k in range(1, n + 1):
                comp = lab == k
                outside = comp & ~ndimage.binary_dilation(ell, iterations=3)
                if outside.sum() > 3:
                    prot |= comp
            core = ell & (dist_e > 40) & (a[..., 3] > 128) & ~prot
            core = ndimage.binary_fill_holes(core)
            em = ell & ~prot
        else:
            cand = box & (L < 100) & (a[..., 3] > 128)
            lab, n = ndimage.label(cand)
            cx, cy = int(round(c[0])), int(round(c[1]))
            k = lab[cy, cx]
            if k == 0:
                idx = ndimage.distance_transform_edt(lab == 0, return_indices=True)[1]
                k = lab[idx[0][cy, cx], idx[1][cy, cx]]
            core = ndimage.binary_fill_holes(lab == k)
            em = ndimage.binary_dilation(core, iterations=1) & ndimage.binary_dilation(box, iterations=1)
        eye_core.append(core)
        eye_masks.append(em)
    eyes_m = eye_masks[0] | eye_masks[1]
    core_all = eye_core[0] | eye_core[1]
    # 保護線：框內所有不屬於眼睛本身的深色線（眼鏡框、眉毛、髮絲、鼻樑線）
    protect_e = ((L < 135) | (dist_e > 110)) & (a[..., 3] > 128) & ~eyes_m
    fill_e = eyes_m & ~protect_e
    skin_e, skin_m_e = skin_stats(a, eb, eyes_m | protect_all)
    skin_full_e = np.zeros((H, W), bool)
    skin_full_e[eb[1]:eb[3], eb[0]:eb[2]] = skin_m_e
    clean_e = harmonic_fill(a, fill_e, skin_e, protect_all & ~fill_e)
    clean_e = paper_grain(clean_e, fill_e, skin_full_e & ~fill_e, seed=7 + zlib.crc32(name.encode()) % 100)
    lash = np.median(a[eyes_m & (L < 60)][:, :3], 0) if (eyes_m & (L < 60)).any() else np.array([30, 22, 20])
    rec["colors"]["lash"] = [int(x) for x in lash]
    pieces_e = {"eyes_open": None}
    # 半閉：上半部改成皮膚＋眼皮線；閉眼：整個眼改成皮膚＋向上的弧線
    for var in ("eyes_half", "eyes_closed"):
        base = a.copy()
        cv = Canvas(eb)
        keep_lower = np.zeros((H, W), bool)
        for c, em in zip(cfg["eyes"], eye_core):
            ys, xs = np.nonzero(em)
            Rinv = rot(-tilt)
            uv = Rinv @ np.stack([xs - c[0], ys - c[1]]).astype(float)
            u0, u1 = np.percentile(uv[0], 2), np.percentile(uv[0], 98)
            v0, v1 = np.percentile(uv[1], 2), np.percentile(uv[1], 98)
            uc, hw_, hh = (u0 + u1) / 2, (u1 - u0) / 2, (v1 - v0)
            if var == "eyes_half":
                vm = v0 + 0.50 * hh
                vlid = vm + 0.10 * hh * np.clip(1 - ((uv[0] - uc) / hw_) ** 2, 0, 1)
                lower = uv[1] > vlid + 0.6
                kl = np.zeros((H, W), bool)
                kl[ys[lower], xs[lower]] = True
                keep_lower |= kl
                u = np.linspace(uc - hw_ * 1.02, uc + hw_ * 1.06, 40)
                v = vm + 0.10 * hh * np.clip(1 - ((u - uc) / hw_) ** 2, 0, 1)
                X, Y = to_img(c, tilt, u, v)
                cv.stroke(X, Y, cfg["lid_lw"], tuple(int(x) for x in lash) + (255,), taper=False)
            else:
                vm = v0 + 0.62 * hh
                u = np.linspace(uc - hw_ * 0.95, uc + hw_ * 0.95, 40)
                v = vm - 0.16 * hh * np.clip(1 - ((u - uc) / (hw_ * 0.95)) ** 2, 0, 1) ** 0.8
                X, Y = to_img(c, tilt, u, v)
                cv.stroke(X, Y, cfg["lid_lw"], tuple(int(x) for x in lash) + (255,), taper=True)
        img = clean_e.copy()
        if var == "eyes_half":
            img[keep_lower] = a[keep_lower]
        pieces_e[var] = (img, cv.result())
    write_group(name, "eyes", eb, a, clean_e, eyes_m, protect_e, pieces_e, out_dir, rec)

    face = {
        "character": name, "zh": cfg["zh"], "version": "v01",
        "head_image": {"file": str(cfg["head"].relative_to(ROOT)), "image_id": pack_id(cfg["head"]), "size": [W, H], "note": cfg["head_note"]},
        "pack_ids": "圖像 id＝相對 assets/final 的路徑去掉 _vNN（tools/pack.mjs）；本檔的 JSON id＝face/<角色>/face。",
        "coords": "anchor_px＝換片左上角在頭部圖上的像素座標（y 向下）；同一組（嘴、眼）所有換片同錨點、同尺寸，直接疊在頭部圖上即可。",
        "z_order": "頭部圖 < 眼睛換片 < 嘴巴換片（兩組不重疊）；換片永遠畫在頭部圖正上方、同一變換。",
        "swap_rule": "硬切換（不做透明度交叉淡化，角色表 0.6）；眨眼：eyes_closed 停 2–3 格（12 fps），每 3–6 秒一次；轉頭／情緒轉折時加眨一次。",
        "lipsync_map": {"0": "mouth_closed", "1": "mouth_half", "2": "mouth_open", "3": "mouth_round"},
        "rest_mouth": "mouth_worried", "rest_eyes": "eyes_open",
        "groups": rec["groups"], "pieces": rec["pieces"], "colors": rec["colors"],
        "stage_scale_hint": cfg["stage_scale"],
    }
    if name == "ale":
        face["expression_hint"] = "X10 困惑＝eyes_half＋（眉在頭部圖上已是擔心眉）＋mouth_worried（說話時 lipsync）；X11 疲倦＝eyes_half＋mouth_closed；X12 閉眼靠著＝eyes_closed＋mouth_closed。"
    else:
        face["expression_hint"] = "姿勢圖本身是擔心眉；X4 驚訝＝eyes_open＋mouth_round（原圖）；X5 擔心＝eyes_open＋mouth_worried；說話時 lipsync。"
    (out_dir / "face.json").write_text(json.dumps(face, ensure_ascii=False, indent=1))
    return face, a


def pack_id(p):
    """tools/pack.mjs 的圖像 id：相對 assets/final 的路徑，去掉副檔名與 _vNN"""
    import re
    p = Path(p)
    if not p.is_absolute():
        p = ROOT / p
    rel = p.relative_to(ROOT / "assets/final").as_posix()
    d = rel.rsplit("/", 1)[0] + "/" if "/" in rel else ""
    m = re.match(r"^(.*)_v(\d+)$", p.stem)
    return d + (m.group(1) if m else p.stem)


def write_group(name, group, box, orig, clean, feat_m, protect_m, pieces, out_dir, rec):
    x0, y0, x1, y1 = box
    rec.setdefault("groups", {})[group] = {"anchor_px": [x0, y0], "size": [x1 - x0, y1 - y0]}
    for var, data in pieces.items():
        if data is None:
            img = orig.copy()
            drawn = None
        elif isinstance(data, tuple):
            img, drawn = data
        else:
            img, drawn = clean.copy(), data
        crop = img[y0:y1, x0:x1].copy()
        cover = feat_m[y0:y1, x0:x1].copy()
        if drawn is not None:
            da = drawn[..., 3:4].astype(np.float32) / 255
            crop[..., :3] = (crop[..., :3] * (1 - da) + drawn[..., :3] * da).astype(np.uint8)
            cover |= ndimage.binary_dilation(drawn[..., 3] > 20, iterations=2)
        cover = ndimage.binary_dilation(cover, iterations=1)
        cover &= ~protect_m[y0:y1, x0:x1]
        cover &= orig[y0:y1, x0:x1, 3] > 128
        alpha = ndimage.gaussian_filter(cover.astype(np.float32), 0.9)
        alpha = np.where(ndimage.binary_erosion(cover, iterations=1), 1.0, np.clip(alpha * 1.4, 0, 1))
        alpha *= (orig[y0:y1, x0:x1, 3] > 128)
        crop[..., 3] = (alpha * 255).astype(np.uint8)
        fn = f"chr-{name}_{var}_v01.png"
        Image.fromarray(crop, "RGBA").save(out_dir / fn, optimize=True)
        # 換片後與原圖的差異範圍（只應在特徵框內）
        comp = orig[y0:y1, x0:x1, :3].astype(np.float32) * (1 - alpha[..., None]) + crop[..., :3] * alpha[..., None]
        diff = np.abs(comp - orig[y0:y1, x0:x1, :3]).max(-1) > 12
        rec["pieces"][var] = {"file": f"assets/final/face/{name}/{fn}", "image_id": f"face/{name}/chr-{name}_{var}", "group": group,
                              "anchor_px": [x0, y0], "size": [x1 - x0, y1 - y0],
                              "source": "原圖（未改）" if data is None else "原圖局部填補＋程式畫剪紙風線條",
                              "changed_px": int(diff.sum())}


def face_sheet(faces):
    """每個角色一區：上排原寸（以臉為中心的裁切）、下排縮到舞台尺寸（×stage_scale，再放大 2 倍方便看，標示）"""
    f = ImageFont.truetype(FONT, 22, index=10)
    fs = ImageFont.truetype(FONT, 16, index=10)
    order = ["mouth_closed", "mouth_half", "mouth_open", "mouth_round", "mouth_worried", "eyes_open", "eyes_half", "eyes_closed"]
    blocks = []
    for name, (face, head) in faces.items():
        cfg = CHARS[name]
        g = {k: dict(v, anchor_px=v.get("anchor_px_pose_image", v["anchor_px"])) for k, v in face["groups"].items()}
        bx0 = min(g["mouth"]["anchor_px"][0], g["eyes"]["anchor_px"][0]) - 30
        by0 = g["eyes"]["anchor_px"][1] - 40
        bx1 = max(g["mouth"]["anchor_px"][0] + g["mouth"]["size"][0], g["eyes"]["anchor_px"][0] + g["eyes"]["size"][0]) + 30
        by1 = g["mouth"]["anchor_px"][1] + g["mouth"]["size"][1] + 24
        tiles, small = [], []
        for var in order:
            p = face["pieces"][var]
            im = Image.fromarray(head.copy(), "RGBA")
            # 預設搭配：換嘴時眼睛用 eyes_open（原圖），換眼時嘴用 rest 原圖
            pc = Image.open(ROOT / p["file"]).convert("RGBA")
            im.alpha_composite(pc, tuple(p.get("anchor_px_pose_image", p["anchor_px"])))
            bg = Image.new("RGBA", im.size, (214, 206, 190, 255))
            bg.alpha_composite(im)
            crop = bg.crop((bx0, by0, bx1, by1))
            k = 2 if name == "ale" else 1
            tiles.append((var, crop.resize((crop.width * k, crop.height * k), Image.LANCZOS)))
            # 舞台尺寸：整個頭縮到舞台比例
            hb = Image.fromarray(head[..., 3]).getbbox()
            hx0, hy0, hx1, hy1 = hb
            if name != "ale":
                hx0, hy0, hx1, hy1 = bx0 - 120, by0 - 140, bx1 + 120, by1 + 160
            hcrop = bg.crop((hx0, hy0, hx1, hy1))
            s = cfg["stage_scale"]
            st = hcrop.resize((max(1, int(hcrop.width * s)), max(1, int(hcrop.height * s))), Image.LANCZOS)
            small.append((var, st))
        blocks.append((name, face, tiles, small))
    Wt = 30 + max(sum(t.width + 16 for _, t in tiles) for _, _, tiles, _ in blocks)
    Ht = 60 + sum(60 + max(t.height for _, t in tiles) + 50 + max(s.height for _, s in small) + 40 for _, _, tiles, small in blocks)
    S = Image.new("RGB", (Wt, Ht), (46, 44, 42))
    d = ImageDraw.Draw(S)
    d.text((20, 14), "臉部換片 face_sheet（G4）：每個角色上排＝原寸（阿樂 ×2 放大），下排＝縮到舞台尺寸（1080p 中景）。換片只改眼、嘴；臉型、膚色、髮型、眼鏡不變。", font=f, fill=(240, 240, 240))
    y = 60
    for name, face, tiles, small in blocks:
        d.text((20, y), f"{face['zh']}（{name}）  頭部圖：{face['head_image']['image_id']}", font=f, fill=(240, 210, 120))
        y += 36
        x = 20
        for var, t in tiles:
            S.paste(t.convert("RGB"), (x, y + 22))
            d.text((x, y), var + ("（原圖）" if face["pieces"][var]["source"].startswith("原圖（") else ""), font=fs, fill=(220, 220, 220))
            x += t.width + 16
        y += 22 + max(t.height for _, t in tiles) + 16
        d.text((20, y), f"舞台尺寸 ×{CHARS[name]['stage_scale']}", font=fs, fill=(200, 200, 200))
        x = 20
        y += 24
        for var, s in small:
            S.paste(s.convert("RGB"), (x, y))
            x += max(s.width, 60) + 16
        y += max(s.height for _, s in small) + 40
    S.save(ROOT / "review/G4/art/face_sheet.png")


def rebase_to_head_layer(name, face):
    """孩子：換片錨點改成相對「頭層」（split_kid_heads.py 拆出的 -head 圖）；另保留相對整張姿勢圖的錨點。"""
    kh = json.loads((ROOT / "review/G4/art/kid_heads.json").read_text())[name]
    ox, oy = kh["head_offset_px"]
    full = dict(face["head_image"])
    face["pose_image"] = full
    face["head_image"] = {"file": kh["head_file"], "image_id": pack_id(kh["head_file"]), "size": kh["head_size"],
                          "pivot_px": kh["pivot_px_head"], "offset_in_pose_image_px": [ox, oy],
                          "note": "頭層（可繞 pivot 轉 ±2.5°）；身體層 " + kh["body_file"] + " 與整張姿勢圖同座標"}
    for g in face["groups"].values():
        g["anchor_px_pose_image"] = list(g["anchor_px"])
        g["anchor_px"] = [g["anchor_px"][0] - ox, g["anchor_px"][1] - oy]
    for pc in face["pieces"].values():
        pc["anchor_px_pose_image"] = list(pc["anchor_px"])
        pc["anchor_px"] = [pc["anchor_px"][0] - ox, pc["anchor_px"][1] - oy]
    face["coords"] = ("anchor_px＝換片左上角在『頭層』上的像素座標（y 向下）；anchor_px_pose_image＝在整張姿勢圖上的座標（不拆頭時用）。"
                      "同一組（嘴、眼）所有換片同錨點、同尺寸。")
    (FACE_DIR / name / "face.json").write_text(json.dumps(face, ensure_ascii=False, indent=1))


def shift_cfg(cfg, off):
    """孩子的設定座標是 assets/generated 原圖座標 → 換成 assets/final 裁切後座標"""
    dx, dy = off
    cfg = dict(cfg)
    cfg["mouth_c"] = (cfg["mouth_c"][0] - dx, cfg["mouth_c"][1] - dy)
    for k in ("mouth_box", "eyes_box", "mouth_search"):
        if cfg.get(k):
            b = cfg[k]
            cfg[k] = (b[0] - dx, b[1] - dy, b[2] - dx, b[3] - dy)
    cfg["eyes"] = [(x - dx, y - dy) for x, y in cfg["eyes"]]
    cfg["eye_boxes"] = [(b[0] - dx, b[1] - dy, b[2] - dx, b[3] - dy) for b in cfg["eye_boxes"]]
    if cfg.get("eye_ellipses"):
        cfg["eye_ellipses"] = [(e[0] - dx, e[1] - dy, e[2], e[3], e[4]) for e in cfg["eye_ellipses"]]
    return cfg


def main():
    crop = json.loads((ROOT / "review/G4/art/kids_crop.json").read_text())
    for name in ("xiaoqing", "xiaoyu"):
        CHARS[name] = shift_cfg(CHARS[name], crop[CHARS[name]["head"].name]["offset_from_source"])
    faces = {}
    for name, cfg in CHARS.items():
        face, head = build(name, cfg)
        faces[name] = (face, head)
        if name in ("xiaoqing", "xiaoyu"):
            rebase_to_head_layer(name, face)
        print(name, {k: v["changed_px"] for k, v in face["pieces"].items()})
    face_sheet(faces)


if __name__ == "__main__":
    main()
