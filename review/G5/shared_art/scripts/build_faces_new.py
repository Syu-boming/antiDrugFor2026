"""G5 共用美術：新角色（品安、林老師、陳伯伯、葉護理師）的正式臉部換片＋原生 face.json。

為什麼不只用退路換片：退路換片（face.ts drawFallback）的皮膚補片是一個橢圓、兩眼共用一個倍數，
遠側眼貼著髮際或臉緣時，補片會蓋到頭髮、臉緣線或白邊（spill），縮小倍數又蓋不滿眼睛。
這裡改用和 G4 build_faces_r2 相同的想法：補片只畫在「可以畫的範圍」（膚色＋這隻眼自己的像素），
頭髮、臉緣線、白邊、透明背景一律保護不畫；兩眼在同一張換片，所以一定同時閉、同時開。

每個姿勢輸出（assets/final/face/<角色>/）：
  chr-<角色>_<姿勢>-eyes_half_v01.png、-eyes_closed_v01.png（睜眼＝原圖，不另做）
  chr-<角色>_<姿勢>-mouth_<形狀>_v01.png（closed／half／open／round／worried／smile，原圖本來的嘴型不做＝顯示原圖）
  face_v01.json（原生 FaceConfig：最上層空槽＋perPose；引擎 id face/<角色>/face）
閉眼線＝近乎平直、略往下彎的中性線（與 face.ts 退路、G4 v02／v03 換片同款）；嘴型畫法與 face.ts 退路相同。
檢查：review/G5/shared_art/blink_check_pieces.json、faces_pieces/<key>.png
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/build_faces_new.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
OUT = ROOT / "review/G5/shared_art"
FIN = ROOT / "assets/final"
NEW = ("pinan", "lin", "chen", "ye")
MOUTHS = ["closed", "half", "open", "round", "worried", "smile"]
INK = np.array([52, 34, 26], np.float32)
VER = "v01"
SS = 4  # 超取樣倍數（線條抗鋸齒）


def prot_mask(a):
    lab = L.lab_of(a[..., :3])
    Lc, C = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    din = ndimage.distance_transform_edt(a[..., 3] >= 128)
    return Lc, C, din


def eye_pixels(Lc, C, a, box):
    """這隻眼自己的像素：大部分在眼框內的深色連通區＋跨框連通區在框內的部分＋框內的眼白／高光。"""
    H, W = Lc.shape
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    inbox = np.zeros((H, W), bool)
    inbox[y0:y1, x0:x1] = True
    grow = np.zeros((H, W), bool)
    grow[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = True
    dark = (Lc < 55) & (a[..., 3] >= 128)
    lb, n = ndimage.label(dark & ndimage.binary_dilation(grow, iterations=40))
    eye = np.zeros((H, W), bool)
    for j in range(1, n + 1):
        cmp_ = lb == j
        if not (cmp_ & inbox).any():
            continue
        if (cmp_ & grow).sum() >= 0.6 * cmp_.sum():
            eye |= cmp_ & grow
        else:
            # 連到頭髮或臉緣線的連通區：框內「粗」的部分（眼珠，開運算半徑 3 還在）一定算這隻眼；
            # 「細」的部分（睫毛、臉緣線）只有沒碰到框外那段（頭髮／臉緣）的才算，碰到的＝臉緣線或頭髮，保護不畫
            part = cmp_ & inbox
            core = ndimage.binary_opening(part, structure=np.ones((3, 3)), iterations=2)
            thin = part & ~ndimage.binary_dilation(core, iterations=1)
            # 細的部分：離框外那段（頭髮／臉緣線）8 px 以內的保護不畫，其餘（睫毛、眼眶線）算這隻眼
            near_out = ndimage.binary_dilation(cmp_ & ~inbox, iterations=8)
            keep = core | (thin & ~near_out)
            eye |= keep
    din = ndimage.distance_transform_edt(a[..., 3] >= 128)
    whites = inbox & (Lc > 78) & (C < 22) & (a[..., 3] >= 128) & (din >= 18)   # 眼白／高光（離輪廓 <18 px 的白是紙芯白邊，不算）
    return ndimage.binary_dilation(eye, iterations=1) | whites


def paintable(a, Lc, C, din, own_eyes):
    hair_or_line = (Lc < 55) & ~own_eyes
    border = (Lc > 86) & (C < 14) & (din < 18) & ~own_eyes
    return (a[..., 3] >= 128) & ~hair_or_line & ~border


def local_skin(a, Lc, C, pm, box, own):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    H, W = Lc.shape
    yy, xx = np.mgrid[:H, :W]
    d = np.hypot((xx - cx) / rx, (yy - cy) / ry)
    h, s, v = L.hsv(a[..., :3])
    ring = (d > 1.25) & (d < 2.2) & pm & ~own & (Lc > 60) & (h > 5) & (h < 45) & (s > 0.12)
    px = a[..., :3][ring].astype(np.float32)
    if len(px) < 30:
        return np.array([246, 190, 145], np.float32), 2.0
    med = np.median(px, 0)
    sd = float(np.std(Lc[ring]))
    return med, min(4.0, max(1.0, sd * 0.6))


def ellipse_alpha(shape, cx, cy, rx, ry, k, ss=1):
    H, W = shape
    yy, xx = np.mgrid[:H, :W]
    R = max(rx, ry) * k
    d = np.hypot((xx / ss - cx) / (rx * k / R), (yy / ss - cy) / (ry * k / R)) / R
    return np.clip((1 - d) / 0.18, 0, 1)


def slot_box(boxes, pad, W, H):
    b = L.fallback_slot_box(boxes, pad)
    return [max(0, b[0]), max(0, b[1]), min(W, b[2]), min(H, b[3])]


def up(m):
    return np.array(Image.fromarray((m * 255).astype(np.uint8)).resize((m.shape[1] * SS, m.shape[0] * SS), Image.BILINEAR)).astype(np.float32) / 255


def build_eyes(a, fb, shape, rng):
    H, W = a.shape[:2]
    Lc, C, din = prot_mask(a)
    owns = [eye_pixels(Lc, C, a, e) for e in fb["eyes"]]
    own_all = owns[0] | owns[1]
    pm = paintable(a, Lc, C, din, own_all)
    sb = slot_box(fb["eyes"], 0.45, W, H)
    X0, Y0, X1, Y1 = sb
    w, h = X1 - X0, Y1 - Y0
    # 透明處也先填膚色（縮圖時不會混進黑色，換片邊緣不會出現深色圈）
    sk0, _ = local_skin(a, Lc, C, pm, fb["eyes"][0], own_all)
    rgb = np.broadcast_to(sk0, (h * SS, w * SS, 3)).astype(np.float32).copy()
    alpha = np.zeros((h * SS, w * SS), np.float32)
    line = Image.new("L", (w * SS, h * SS), 0)
    dl = ImageDraw.Draw(line)
    k = 1.3  # 正式換片固定 1.3（遮罩已保護頭髮與臉緣；fb 的 patchK 是給退路用的）
    for e, own in zip(fb["eyes"], owns):
        ex0, ey0, ex1, ey1 = e
        cx, cy, rx, ry = (ex0 + ex1) / 2, (ey0 + ey1) / 2, (ex1 - ex0) / 2, (ey1 - ey0) / 2
        skin, sd = local_skin(a, Lc, C, pm, e, own_all)
        ell = ellipse_alpha((h * SS, w * SS), cx - X0, cy - Y0, rx, ry, k, SS)
        ownc = up(ndimage.binary_dilation(own, iterations=1)[Y0:Y1, X0:X1].astype(np.float32))
        p = np.maximum(ell, ownc) * up(ndimage.gaussian_filter(pm[Y0:Y1, X0:X1].astype(np.float32), 0.5))
        if shape == "half":
            cut = (np.arange(h * SS)[:, None] / SS + Y0) <= cy + ry * 0.02
            p = p * cut
        noise = ndimage.gaussian_filter(rng.normal(0, 1, (h * SS, w * SS)), SS * 0.8)
        noise = noise / (noise.std() + 1e-6) * sd
        col = skin[None, None, :] + noise[..., None]
        rgb = rgb * (1 - p[..., None]) + col * p[..., None]
        alpha = np.maximum(alpha, p)
        lw = max(2, ry * (0.22 if shape == "closed" else 0.2)) * SS
        Xp = lambda v: (v - X0) * SS  # noqa: E731
        Yp = lambda v: (v - Y0) * SS  # noqa: E731
        if shape == "closed":
            pts = L.quad((Xp(cx - rx * 1.05), Yp(cy + ry * 0.05)), (Xp(cx), Yp(cy + ry * 0.16)), (Xp(cx + rx * 1.05), Yp(cy + ry * 0.05)))
        else:
            pts = L.quad((Xp(cx - rx * 1.05), Yp(cy)), (Xp(cx), Yp(cy - ry * 0.18)), (Xp(cx + rx * 1.05), Yp(cy)))
        dl.line(pts, fill=255, width=int(round(lw)), joint="curve")
    # 眼皮線只畫在臉上（不畫到頭髮、白邊外）
    lm = np.array(line).astype(np.float32) / 255 * 0.95
    lm *= up(ndimage.binary_dilation(pm | own_all, iterations=1)[Y0:Y1, X0:X1].astype(np.float32))
    rgb = rgb * (1 - lm[..., None]) + INK * lm[..., None]
    alpha = np.maximum(alpha, lm)
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8)
    img = Image.fromarray(out, "RGBA").resize((w, h), Image.LANCZOS)
    return img, sb


def build_mouth(a, fb, shape, rng):
    H, W = a.shape[:2]
    Lc, C, din = prot_mask(a)
    mx0, my0, mx1, my1 = fb["mouth"]
    own = np.zeros((H, W), bool)
    own[my0:my1, mx0:mx1] = (Lc[my0:my1, mx0:mx1] < 70)
    pm = paintable(a, Lc, C, din, ndimage.binary_dilation(own, iterations=1))
    sb = slot_box([fb["mouth"]], 0.9, W, H)
    X0, Y0, X1, Y1 = sb
    w, h = X1 - X0, Y1 - Y0
    cx, cy = (mx0 + mx1) / 2, (my0 + my1) / 2
    mw, mh = max(mx1 - mx0, 24), max(my1 - my0, 10)
    skin, sd = local_skin(a, Lc, C, pm, fb["mouth"], own)
    p = ellipse_alpha((h * SS, w * SS), cx - X0, cy - Y0, mw * 0.68, mh * 0.95 + 4, 1.0, SS)
    p = np.maximum(p, up(ndimage.binary_dilation(own, iterations=2)[Y0:Y1, X0:X1].astype(np.float32)))
    p *= up(ndimage.gaussian_filter(pm[Y0:Y1, X0:X1].astype(np.float32), 0.5))
    noise = ndimage.gaussian_filter(rng.normal(0, 1, (h * SS, w * SS)), SS * 0.8)
    noise = noise / (noise.std() + 1e-6) * sd
    base = Image.fromarray(np.dstack([np.clip(skin[None, None, :] + noise[..., None], 0, 255), p * 255]).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(base)
    Xp = lambda v: (v - X0) * SS  # noqa: E731
    Yp = lambda v: (v - Y0) * SS  # noqa: E731
    lw = int(round(max(2, mw * 0.06) * SS))
    ink = (52, 34, 26, 242)

    def ell(ew, eh, dy=0):
        bb = [Xp(cx - ew), Yp(cy + dy - eh), Xp(cx + ew), Yp(cy + dy + eh)]
        d.ellipse(bb, fill=(122, 46, 40, 247), outline=ink, width=lw)
        if bb[3] - bb[1] <= 2 * lw + 2 or bb[2] - bb[0] <= 2 * lw + 2:
            return
        # 舌頭（下半淡紅），限制在嘴裡
        tongue = Image.new("L", base.size, 0)
        ImageDraw.Draw(tongue).ellipse([Xp(cx - ew * 0.8), Yp(cy + dy + eh * 0.75 - eh * 0.55), Xp(cx + ew * 0.8), Yp(cy + dy + eh * 0.75 + eh * 0.55)], fill=255)
        inside = Image.new("L", base.size, 0)
        ImageDraw.Draw(inside).ellipse([bb[0] + lw, bb[1] + lw, bb[2] - lw, bb[3] - lw], fill=255)
        t = np.minimum(np.array(tongue), np.array(inside))
        arr = np.array(base).astype(np.float32)
        tm = t[..., None].astype(np.float32) / 255 * 0.9
        arr[..., :3] = arr[..., :3] * (1 - tm) + np.array([214, 112, 104], np.float32) * tm
        base.paste(Image.fromarray(arr.astype(np.uint8), "RGBA"))

    if shape == "closed":
        d.line(L.quad((Xp(cx - mw * 0.32), Yp(cy)), (Xp(cx), Yp(cy + mh * 0.12)), (Xp(cx + mw * 0.32), Yp(cy))), fill=ink, width=lw, joint="curve")
    elif shape == "smile":
        d.line(L.quad((Xp(cx - mw * 0.4), Yp(cy - mh * 0.15)), (Xp(cx), Yp(cy + mh * 0.6)), (Xp(cx + mw * 0.4), Yp(cy - mh * 0.15))), fill=ink, width=lw, joint="curve")
    elif shape == "worried":
        pts = []
        p0, c1, c2, p3 = (cx - mw * 0.3, cy + mh * 0.12), (cx - mw * 0.12, cy - mh * 0.22), (cx + mw * 0.1, cy + mh * 0.25), (cx + mw * 0.3, cy - mh * 0.05)
        for i in range(25):
            t = i / 24
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t ** 2 * c2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t ** 2 * c2[1] + t ** 3 * p3[1]
            pts.append((Xp(x), Yp(y)))
        d.line(pts, fill=ink, width=lw, joint="curve")
    elif shape == "half":
        ell(mw * 0.2, mh * 0.28)
    elif shape == "open":
        ell(mw * 0.24, mh * 0.55, mh * 0.1)
    elif shape == "round":
        ell(mw * 0.13, mh * 0.42, mh * 0.05)
    return base.resize((w, h), Image.LANCZOS), sb


def composite(a, piece, sb):
    out = a.copy()
    X0, Y0, X1, Y1 = sb
    p = np.array(piece).astype(np.float32)
    al = p[..., 3:4] / 255
    out[Y0:Y1, X0:X1, :3] = (out[Y0:Y1, X0:X1, :3].astype(np.float32) * (1 - al) + p[..., :3] * al).astype(np.uint8)
    return out, al[..., 0]


def check_piece(a, fb, closed, half, sb):
    Lc, C, din = prot_mask(a)
    res = {}
    for name, piece in (("closed", closed), ("half", half)):
        comp, al = composite(a, piece, sb)
        L1 = L.lab_of(comp[..., :3])[..., 0]
        X0, Y0, X1, Y1 = sb
        alfull = np.zeros(Lc.shape, np.float32)
        alfull[Y0:Y1, X0:X1] = al
        owns = [eye_pixels(Lc, C, a, e) for e in fb["eyes"]]
        own_all = owns[0] | owns[1]
        eyes = []
        for e, own in zip(fb["eyes"], owns):
            ex0, ey0, ex1, ey1 = [int(round(v)) for v in e]
            reg = np.zeros_like(own)
            reg[ey0:ey1, ex0:ex1] = True
            if name == "half":
                reg[int((ey0 + ey1) / 2):, :] = False
            od = own & reg & (Lc < 45)
            # 新眼皮線的位置不算殘留：只看換片 alpha ≥0.9 的皮膚色區沒蓋到的深色
            new_dark = (L1 < 60) & (alfull > 0.5)
            line_px = int((new_dark & ndimage.binary_dilation(reg, iterations=3)).sum())
            still = od & (alfull < 0.5) & (L1 < 60)
            light = own & reg & (Lc > 88) & (L1 > 88) & (alfull < 0.5)
            eyes.append({"orig_dark_px": int(od.sum()), "residual_dark_px": int(still.sum()),
                         "residual_ratio": round(float(still.sum() / max(1, od.sum())), 4), "highlight_left_px": int(light.sum()),
                         "lid_line_px": line_px})
        prot = (a[..., 3] < 128) | ((Lc < 55) & ~own_all) | ((Lc > 86) & (C < 14) & (din < 18) & ~own_all)
        spill = int(((alfull >= 0.5) & prot).sum())
        ok = all(x["residual_ratio"] <= 0.03 and x["highlight_left_px"] <= 2 and x["lid_line_px"] >= 15 for x in eyes) and spill <= 25
        res[name] = {"eyes": eyes, "spill_px": spill, "ok": bool(ok)}
    res["both_closed_ok"] = res["closed"]["ok"]
    return res


def sheet(a, fb, pieces, sbe, sbm, label, scale=3):
    allb = fb["eyes"] + [fb["mouth"]]
    H, W = a.shape[:2]
    x0 = max(0, int(min(b[0] for b in allb) - 40)); y0 = max(0, int(min(b[1] for b in allb) - 40))
    x1 = min(W, int(max(b[2] for b in allb) + 40)); y1 = min(H, int(max(b[3] for b in allb) + 30))
    bg = np.array([232, 226, 214], np.float32)

    def flat(arr):
        al = a[..., 3:4].astype(np.float32) / 255
        return Image.fromarray((arr[..., :3].astype(np.float32) * al + bg * (1 - al)).astype(np.uint8)[y0:y1, x0:x1])

    tiles = [("原圖", flat(a))]
    for name in ("eyes_half", "eyes_closed") + tuple(f"mouth_{m}" for m in MOUTHS if f"mouth_{m}" in pieces):
        comp, _ = composite(a, pieces[name], sbe if name.startswith("eyes") else sbm)
        tiles.append((name, flat(comp)))
    w, h = (x1 - x0) * scale, (y1 - y0) * scale
    cols = 4
    rows = math.ceil(len(tiles) / cols)
    sh = Image.new("RGB", (cols * (w + 10) + 10, rows * (h + 36) + 10), (40, 40, 40))
    d = ImageDraw.Draw(sh)
    f = L.font(18)
    for i, (n, t) in enumerate(tiles):
        cx, cy = 10 + (i % cols) * (w + 10), 10 + (i // cols) * (h + 36)
        sh.paste(t.resize((w, h), Image.NEAREST), (cx, cy + 26))
        d.text((cx, cy), f"{label} {n}", fill=(255, 255, 255), font=f)
    return sh


def main():
    boxes = json.loads((OUT / "face_boxes.json").read_text())
    imp = json.loads((OUT / "import.json").read_text())
    (OUT / "faces_pieces").mkdir(exist_ok=True)
    checks = {}
    per_char = {}
    for rid, rec in imp.items():
        if rid.startswith("_") or rec.get("character") not in NEW:
            continue
        cid = rec["character"]
        from measure_faces import POSE_NAME
        pose = POSE_NAME[rec["part"]]
        key = f"{cid}:{pose}"
        fb = boxes[key]
        a = np.array(Image.open(ROOT / rec["final"]).convert("RGBA"))
        rng = np.random.default_rng(abs(hash(key)) % (2 ** 32))
        tag = pose.replace("_", "-")
        d = FIN / "face" / cid
        d.mkdir(parents=True, exist_ok=True)
        pieces, ids = {}, {"eyes": {}, "mouth": {}}
        closed, sbe = build_eyes(a, fb, "closed", rng)
        half, _ = build_eyes(a, fb, "half", rng)
        pieces["eyes_closed"], pieces["eyes_half"] = closed, half
        for nm, im in (("eyes_closed", closed), ("eyes_half", half)):
            fn = f"chr-{cid}_{tag}-{nm}_{VER}.png"
            im.save(d / fn, optimize=True)
            ids["eyes"][nm.split("_")[1]] = f"face/{cid}/chr-{cid}_{tag}-{nm}"
        sbm = None
        for m in MOUTHS:
            if m == fb["paintedMouth"]:
                continue
            im, sbm = build_mouth(a, fb, m, rng)
            pieces[f"mouth_{m}"] = im
            fn = f"chr-{cid}_{tag}-mouth_{m}_{VER}.png"
            im.save(d / fn, optimize=True)
            ids["mouth"][m] = f"face/{cid}/chr-{cid}_{tag}-mouth_{m}"
        res = check_piece(a, fb, closed, half, sbe)
        checks[key] = {"image": rec["final"], **res}
        sheet(a, fb, pieces, sbe, sbm, key).save(OUT / "faces_pieces" / f"{key.replace(':', '_')}.png")
        cfgp = per_char.setdefault(cid, {})
        cfgp[pose] = {
            "eyes": {"anchor": [(sbe[0] + sbe[2]) / 2, (sbe[1] + sbe[3]) / 2], "size": [sbe[2] - sbe[0], sbe[3] - sbe[1]], "z": 1, "shapes": ids["eyes"]},
            "mouth": {"anchor": [(sbm[0] + sbm[2]) / 2, (sbm[1] + sbm[3]) / 2], "size": [sbm[2] - sbm[0], sbm[3] - sbm[1]], "z": 2, "shapes": ids["mouth"]},
            "_image": f"chr-{cid}_{rec['part']}", "_paintedMouth": fb["paintedMouth"],
        }
        e = res["closed"]["eyes"]
        print(key, "閉眼殘留", [x["residual_ratio"] for x in e], "線", [x["lid_line_px"] for x in e], "溢出", res["closed"]["spill_px"],
              "通過" if res["both_closed_ok"] and res["half"]["ok"] else "不通過")
    for cid, poses in per_char.items():
        painted = {p: v.pop("_paintedMouth") for p, v in poses.items()}
        cfg = {
            "character": cid, "version": VER,
            "format_note": "引擎原生 FaceConfig（app/src/stage/face.ts）。perPose 依立牌姿勢名稱（assets/final/rig/show_characters.json 的 poses）；"
                           "最上層 mouth／eyes 是空槽（沒列在 perPose 的姿勢改用 fallbackFaces 退路換片）。anchor＝換片中心、size＝換片在姿勢圖上的像素尺寸，"
                           "座標都是 assets/final 姿勢圖的像素。睜眼與原圖本來的嘴型沒有換片＝顯示原圖。",
            "paintedMouth": "smile",
            "paintedMouth_per_pose": painted,
            "paintedMouth_note": "FaceConfig 只有一個 paintedMouth（整個角色共用）。各姿勢原圖的嘴型在 paintedMouth_per_pose；每個姿勢都做了除了它自己原圖嘴型以外的全部嘴型換片，所以引擎要哪個嘴型都對得上（要原圖嘴型時顯示原圖）。",
            "mouth": {"anchor": [0, 0], "size": [1, 1], "z": 2, "shapes": {m: f"none/{cid}-{m}" for m in MOUTHS}},
            "eyes": {"anchor": [0, 0], "size": [1, 1], "z": 1, "shapes": {s: f"none/{cid}-{s}" for s in ("open", "half", "closed")}},
            "perPose": poses,
            "swap_rule": "硬切換（不做透明度交叉淡化）；兩眼在同一張換片，一定同時閉、同時開。",
            "made_by": "review/G5/shared_art/scripts/build_faces_new.py",
        }
        (FIN / "face" / cid / f"face_{VER}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
    (OUT / "blink_check_pieces.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
