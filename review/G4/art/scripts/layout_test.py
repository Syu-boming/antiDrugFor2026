"""G4 美術：a2 中景粗合成試排（Python，不是劇場截圖）＋投影 v2 對比量測。

相機照 app/src/stage/layers.ts 的 CAMERA_PRESETS.medium（pos 0.3,3.3,22 → target 0.3,2.75,0；垂直視角 20°；1920×1080）。
景片照 assets/final/g4_manifest.json 的建議座標與縮放擺放（本腳本同時輸出 manifest 的 placement 段）。
輸出：
  review/G4/art/a2_layout_test.png        試排（含字幕安全區、90% 安全框、操偶線示意）
  review/G4/art/a2_layout_test_nosub.png  無疊加的試排（量測用）
  review/G4/art/a2_layout_sit.png         坐姿起始畫面（a2_c002 開頭）
  review/G4/art/contrast_g4.json          兒童主色 vs 身後背景（投影 v2）的對比
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/layout_test.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).parent))
from projsim import projector  # noqa: E402
import ale_a2_poses as A  # noqa: E402

FIN = ROOT / "assets/final"
OUTD = ROOT / "review/G4/art"
FONT = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
SW, SH = 1920, 1080
CAM = np.array([0.3, 3.3, 22.0])
TGT = np.array([0.3, 2.75, 0.0])
FOV = 20.0
F = (SH / 2) / math.tan(math.radians(FOV / 2))
fwd = (TGT - CAM) / np.linalg.norm(TGT - CAM)
right = np.array([1.0, 0, 0])
up = np.cross(right, fwd)
up /= np.linalg.norm(up)

# ---- 世界尺度（建議值，寫進 manifest）
ALE_H_UNITS = 4.6                  # 阿樂站姿身高（含白邊）＝中景 1080p 約 640 px，與 G2 v04 合成一致
ALE_UPX = ALE_H_UNITS / 1610.0     # 母版 1 px → 世界單位
ALE_X = -2.2                       # 阿樂身體中線（母版 x=510）的世界 x
KID = {  # 孩子：整張圖外框高度（世界單位）、腳底世界位置、z
    "xiaoqing": dict(file="chr-xiaoqing_pose-reach-worried_v04.png", h=640 * 0.65 * 1.06 / 139.2, x=0.95, z=0.4),
    "xiaoyu": dict(file="chr-xiaoyu_pose-stepback-surprised_v04.png", h=640 * 0.65 * 0.96 / 139.2, x=2.75, z=-0.35),
}


def project(p):
    r = np.asarray(p, float) - CAM
    zc = r @ fwd
    x = r @ right
    y = r @ up
    return np.array([SW / 2 + F * x / zc, SH / 2 - F * y / zc]), zc


def place_sprite(canvas, img, world_left_top, world_w, z, flip=False):
    """把圖貼在 z 平面上：左上角世界座標、世界寬度（等比）"""
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    x0, y0 = world_left_top
    world_h = world_w * img.height / img.width
    p0, _ = project((x0, y0, z))
    p1, _ = project((x0 + world_w, y0 - world_h, z))
    w, h = int(round(p1[0] - p0[0])), int(round(p1[1] - p0[1]))
    if w < 1 or h < 1:
        return None
    im = img.resize((w, h), Image.LANCZOS)
    layer = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    layer.paste(im, (int(round(p0[0])), int(round(p0[1]))), im)
    canvas.alpha_composite(layer)
    return layer


def floor_and_wall(canvas):
    wall = Image.open(FIN / "bg-workshop-back_v02.jpg").convert("RGB")
    floor_tex = np.array(Image.open(FIN / "bg-workshop-floor_v01.jpg").convert("RGB"))
    WALL_Z, WALL_W = -5.0, 22.0
    # 地板：逐列找射線與 y=0 平面的交點，取地板貼圖（1 單位＝貼圖 128 px）
    arr = np.zeros((SH, SW, 3), np.uint8)
    ys = np.arange(SH)
    xs = np.arange(SW)
    for y in ys:
        v = -(y - SH / 2) / F
        dirs = fwd[None, :] + right[None, :] * ((xs - SW / 2) / F)[:, None] + up[None, :] * v
        t = -CAM[1] / dirs[:, 1]
        valid = (dirs[:, 1] < 0)
        P = CAM[None, :] + dirs * t[:, None]
        u = (P[:, 0] * 128).astype(int) % floor_tex.shape[1]
        w = (P[:, 2] * 128).astype(int) % floor_tex.shape[0]
        row = floor_tex[w, u]
        row[~valid] = 0
        arr[y] = row
    canvas.alpha_composite(Image.fromarray(arr).convert("RGBA"))
    place_sprite(canvas, wall.convert("RGBA"), (-WALL_W / 2, WALL_W * wall.height / wall.width), WALL_W, WALL_Z)
    return dict(id="bg-workshop-back", z=WALL_Z, world_w=WALL_W, world_h=round(WALL_W * wall.height / wall.width, 3),
                left_top=[-WALL_W / 2, round(WALL_W * wall.height / wall.width, 3)])


def visible_top_y(z):
    # 畫面上緣（y=0）在 z 平面上的世界 y（x 取中央）
    lo, hi = -5, 30
    for _ in range(60):
        m = (lo + hi) / 2
        if project((0.3, m, z))[0][1] < 0:
            hi = m
        else:
            lo = m
    return lo


def render(pose_name, with_kids=True, strings=True):
    canvas = Image.new("RGBA", (SW, SH), (0, 0, 0, 255))
    place = {}
    place["back"] = floor_and_wall(canvas)
    # 中景懸掛燈籠：只放在畫面右半（孩子上方），讓阿樂上方留白給落下的操偶線；竹竿在畫面上緣下方約 0.3 單位，寬 6.6 單位
    lan = Image.open(FIN / "bg-workshop-lanterns_v01.png").convert("RGBA")
    LZ, LW = -0.9, 6.6
    pole_y = visible_top_y(LZ) - 0.30
    # 竹竿在裁切圖的 y≈ 13 px（中心）
    lt_y = pole_y + 13 * LW / lan.width
    place_sprite(canvas, lan, (0.7, lt_y), LW, LZ)
    place["lanterns"] = dict(id="bg-workshop-lanterns", z=LZ, world_w=LW, left_top=[0.7, round(lt_y, 3)], pole_y=round(pole_y, 3))
    chars_layer = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    masks = {}
    # 阿樂（rig 姿勢）
    A.apply_ik()
    rig = A.load_rig(True)
    img, pt = A.render_pose(rig, pose_name, with_table=False)
    # rig 畫布：母版點 (0,0) 在 OFFSET；母版 (510, 1631) → 世界 (ALE_X, 0)
    ox, oy = A.R.OFFSET
    wl = ALE_X - (510 + ox) * ALE_UPX
    wt = (1631 + oy) * ALE_UPX
    lay = place_sprite(chars_layer, img, (wl, wt), img.width * ALE_UPX, 0.0)
    masks["ale"] = np.array(lay)[..., 3] > 128
    place["ale"] = dict(id="ale_rig", z=0.0, master_px_to_units=round(ALE_UPX, 6), body_center_x=ALE_X, floor_master_y=1631,
                        standing_height_units=ALE_H_UNITS)
    # 孩子
    kid_layers = {}
    crop = json.loads((OUTD / "kids_crop.json").read_text())
    for name, k in KID.items():
        if not with_kids:
            break
        im = Image.open(FIN / k["file"]).convert("RGBA")
        c = crop[k["file"]]
        hpx = c["height_px"]
        upx = k["h"] / hpx
        al = np.array(im)[..., 3] > 128
        rows = np.nonzero(al.any(1))[0]
        bottom = rows.max()
        low = np.nonzero(al[bottom - 40:bottom + 1].any(0))[0]
        feet_cx = (low.min() + low.max()) / 2
        top_px = rows.min()
        wl_k = k["x"] - feet_cx * upx
        wt_k = (bottom) * upx
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        place_sprite(lay, im, (wl_k, wt_k), im.width * upx, k["z"])
        kid_layers[name] = lay
        masks[name] = np.array(lay)[..., 3] > 128
        place[name] = dict(id=k["file"].replace("_v04.png", ""), z=k["z"], units_per_px=round(upx, 6), feet_anchor_px=[round(float(feet_cx), 1), int(bottom)],
                           feet_world_x=k["x"], height_units=round(k["h"], 3))
    # 層序：小宇（後）→ 阿樂 → 工作台 → 小晴（前）
    if with_kids:
        canvas.alpha_composite(kid_layers["xiaoyu"])
    canvas.alpha_composite(chars_layer)
    # 工作台（z=0.3，桌面上緣＝阿樂母版 y=830、右端＝母版 x=705）
    sp = json.loads((OUTD / "set_process.json").read_text())["bg-workshop-table"]
    tab = Image.open(FIN / "bg-workshop-table_v02.png").convert("RGBA")
    top_px, (bx0, bx1), body_h = sp["table_top_y_px"], sp["table_body_x_px"], sp["table_body_h_px"]
    TZ = 0.3
    top_world = (1631 - A.TABLE_TOP) * ALE_UPX
    tupx = top_world / body_h
    right_world = ALE_X + (A.TABLE_R - 510) * ALE_UPX
    t_left = right_world - bx1 * tupx
    t_top = top_world + top_px * tupx
    tl = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    place_sprite(tl, tab, (t_left, t_top), tab.width * tupx, TZ)
    canvas.alpha_composite(tl)
    masks["table"] = np.array(tl)[..., 3] > 128
    place["table"] = dict(id="bg-workshop-table", z=TZ, units_per_px=round(tupx, 6), left_top=[round(t_left, 3), round(t_top, 3)],
                          world_w=round(tab.width * tupx, 3), top_surface_y=round(top_world, 3), right_end_x=round(right_world, 3))
    if with_kids:
        canvas.alpha_composite(kid_layers["xiaoqing"])
    # 側翼前景（z=2.4，左原圖、右鏡射）
    wing = Image.open(FIN / "bg-workshop-wing_v01.png").convert("RGBA")
    WZ, WH = 2.4, 7.2
    ww = WH * wing.width / wing.height
    place_sprite(canvas, wing, (-6.55, WH), ww, WZ)
    place_sprite(canvas, wing, (7.15 - ww, WH), ww, WZ, flip=True)
    place["wings"] = dict(id="bg-workshop-wing", z=WZ, world_h=WH, world_w=round(ww, 3), left=[-6.55, WH], right_mirrored=[round(7.15 - ww, 3), WH])
    # 操偶線示意（劇場程式會畫正式的紙繩；這裡只檢查走向不碰到孩子與頭頸）
    string_hits = {}
    if strings:
        att = json.loads((FIN / "rig/ale_attach.json").read_text())["points"]
        d = ImageDraw.Draw(canvas)
        Mw = rig.world(A.POSES[pose_name])
        for key, lean in (("wrist_back", -0.25), ("elbow_out", -0.25), ("knee_front", 2.6)):
            p = att[key]
            mp = A.R.apply(Mw[p["part"]], p["master_px"])
            wx = ALE_X + (mp[0] - 510) * ALE_UPX
            wy = (1631 - mp[1]) * ALE_UPX
            a0, _ = project((wx, wy, 0.0))
            a1, _ = project((wx + lean, wy + 14, 0.0))
            for wdt, col in ((11, (70, 66, 62, 255)), (7, (214, 210, 202, 255))):
                d.line([tuple(a0), tuple(a1)], fill=col, width=wdt)
            d.ellipse([a0[0] - 9, a0[1] - 9, a0[0] + 9, a0[1] + 9], outline=(70, 66, 62, 255), width=4)
            # 碰撞檢查：線段經過的像素是否落在孩子身上、阿樂頭部
            n = int(np.hypot(*(a1 - a0)))
            ts = np.linspace(0, 1, max(n, 2))
            pts = a0[None, :] + (a1 - a0)[None, :] * ts[:, None]
            ok = (pts[:, 0] >= 0) & (pts[:, 0] < SW) & (pts[:, 1] >= 0) & (pts[:, 1] < SH)
            pp = pts[ok].astype(int)
            string_hits[key] = {nm: int(masks[nm][pp[:, 1], pp[:, 0]].sum()) for nm in ("xiaoqing", "xiaoyu") if nm in masks}
    return canvas, masks, place, string_hits


def rel_lum(rgb):
    a = rgb.astype(np.float32) / 255
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def hue_sat_val(rgb):
    a = rgb.astype(np.float32) / 255
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-6
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-6), mx


def measure(full, bg_only, masks, place):
    pv_full = projector(np.array(full.convert("RGB")), "v2")
    pv_bg = projector(np.array(bg_only.convert("RGB")), "v2")
    out = {}
    specs = {"xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.28, (0.12, 0.90)), ("芥末黃上衣", (32, 56), 0.55, (0.55, 1.0))],
             "xiaoyu": [("橘紅外套", (345, 22), 0.55, (0.28, 1.0)), ("卡其短褲", (22, 46), 0.25, (0.40, 0.88))],
             "ale": [("深藍圍裙", (195, 255), 0.18, (0.10, 0.62))]}
    for name, rows in specs.items():
        m = masks[name]
        core = ndimage.binary_erosion(m, iterations=3)
        ring = ndimage.binary_dilation(m, iterations=26) & ~ndimage.binary_dilation(m, iterations=6)
        for nm in masks:
            if nm != name:
                ring &= ~masks[nm]
        ys = np.nonzero(m.any(1))[0]
        top, bot = ys.min(), ys.max()
        # 軀幹高度帶（身高 25%–65%）
        band = np.zeros_like(m)
        band[int(top + 0.25 * (bot - top)):int(top + 0.65 * (bot - top))] = True
        rb = ring & band
        bgL = rel_lum(pv_bg[rb])
        rec = {"bg_torso_band_median_lum": round(float(np.median(bgL)), 3), "bg_torso_band_p10_lum": round(float(np.percentile(bgL, 10)), 3),
               "requirement_bg_lum": ">=0.50（兒童）", "costumes": {}}
        orig = np.array(full.convert("RGB"))
        h, s, v = hue_sat_val(orig)
        for label, (h0, h1), smin, (vmin, vmax) in rows:
            hm = ((h >= h0) & (h <= h1)) if h0 < h1 else ((h >= h0) | (h <= h1))
            cm = core & hm & (s >= smin) & (v >= vmin) & (v <= vmax)
            if cm.sum() < 50:
                rec["costumes"][label] = {"pixels": int(cm.sum())}
                continue
            cl = rel_lum(pv_full[cm])
            lc = float(np.median(cl))
            ratio_med = (max(np.median(bgL), lc) + 0.05) / (min(np.median(bgL), lc) + 0.05)
            ratio_p10 = (max(np.percentile(bgL, 10), lc) + 0.05) / (min(np.percentile(bgL, 10), lc) + 0.05)
            rec["costumes"][label] = {"pixels": int(cm.sum()), "proj_v2_lum": round(lc, 3), "contrast_vs_bg_median": round(float(ratio_med), 2),
                                      "contrast_vs_bg_p10": round(float(ratio_p10), 2)}
        out[name] = rec
    return out


def overlay(canvas):
    o = canvas.copy()
    d = ImageDraw.Draw(o)
    f = ImageFont.truetype(FONT, 26, index=10)
    fs = ImageFont.truetype(FONT, 20, index=10)
    # 90% 安全框
    d.rectangle([96, 54, 1824, 1026], outline=(0, 200, 255, 255), width=3)
    # 字幕安全區（下 20%）
    band = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([0, int(SH * 0.8), SW, SH], fill=(0, 120, 255, 34))
    o.alpha_composite(band)
    d.line([(0, int(SH * 0.8)), (SW, int(SH * 0.8))], fill=(0, 140, 255, 255), width=3)
    # 字幕底板示意（字由程式排；這裡只放佔位條，不放生成字）
    d.rounded_rectangle([560, 888, 1360, 1010], radius=10, fill=(20, 20, 20, 200))
    d.text((590, 930), "（字幕安全區：兩行字幕底板位置示意）", font=f, fill=(255, 255, 255, 255))
    d.text((104, 60), "a2 中景試排（Python 粗合成，非劇場截圖）｜藍框＝90% 安全框｜藍色帶＝字幕安全區（下 20%，說話者的臉不進入）｜灰線＝操偶線走向示意",
           font=fs, fill=(20, 60, 120, 255))
    return o


def main():
    full, masks, place, hits = render("hold")
    bg_only, _, _, _ = render("hold", with_kids=False, strings=False)
    # 背景量測用：沒有角色的畫面（阿樂也拿掉）
    bg_canvas = Image.new("RGBA", (SW, SH), (0, 0, 0, 255))
    floor_and_wall(bg_canvas)
    lan = Image.open(FIN / "bg-workshop-lanterns_v01.png").convert("RGBA")
    p = place["lanterns"]
    place_sprite(bg_canvas, lan, tuple(p["left_top"]), p["world_w"], p["z"])
    full.convert("RGB").save(OUTD / "a2_layout_test_nosub.png")
    overlay(full).convert("RGB").save(OUTD / "a2_layout_test.png")
    sit, _, _, _ = render("sit")
    overlay(sit).convert("RGB").save(OUTD / "a2_layout_sit.png")
    res = measure(full, bg_canvas, masks, place)
    # 臉不進字幕區
    faces = {}
    for nm in ("xiaoqing", "xiaoyu", "ale"):
        ys = np.nonzero(masks[nm].any(1))[0]
        faces[nm] = {"top_px": int(ys.min()), "bottom_px": int(ys.max())}
    out = {"camera": "medium（layers.ts CAMERA_PRESETS.medium）", "projector": "tools/projsim.py v2", "pose": "hold（a2_c002 停格）",
           "contrast": res, "string_pixels_on_kids": hits, "figure_extent_px": faces, "placement": place}
    (OUTD / "contrast_g4.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"contrast": res, "hits": hits}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
