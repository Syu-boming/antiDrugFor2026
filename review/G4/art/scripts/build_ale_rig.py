"""G4 美術：阿樂叔叔分件 v04（由 assets/parts/ale_v03 衍生，不改原檔）。

做的事：
1. 接縫修正（G2 帶進 G4 的問題 3「肩、膝圓舌片弧線外露」）：
   - 軀幹右肩球、左肩球：球內的深色弧線（母版原本的手臂輪廓線、舌片邊線）改成鄰近袖子顏色 → 手臂舉起或被拉開時不再露出一圈圓弧。
   - 左右大腿下端圓舌片：舌片邊緣的深色接縫改成鄰近褲子顏色 → 膝蓋彎曲時看起來是膝頭，不是一片圓紙。
2. 乾淨的困惑頭（head_worried）：沿用 tools/rig_ale_v03.make_worried_head 的對位（IoU 0.97），再
   去掉生成圖頸部殘留的圓弧線、白色殘點、身體外的頸部突出與零碎小塊。
3. 輸出 assets/final/rig/：每個部件裁到外框＋16 px 透明邊（chr-ale_<部件>_v04.png），各附一張整體外輪廓用的描邊底圖
   （chr-ale_<部件>-outline_v04.png，同尺寸；白色紙芯邊 11 px＋外側深色細線 1.6 px），ale_rig.json，ale_attach.json。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_ale_rig.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import rig_ale_v03 as R  # noqa: E402

OUT = ROOT / "assets/final/rig"
PAD = 16
BORDER, RIM = R.BORDER, R.RIM
CFG = R.CFG
CANVAS_W, CANVAS_H = CFG["canvas"]
PIV = R.PIV


def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def dark_lines(a, drop=28, size=15):
    """深色棕灰線（不含深藍圍裙）：亮度比局部中位數低 drop 以上，且 R ≥ B。"""
    L = lum(a.astype(np.float32))
    med = ndimage.median_filter(L, size=size)
    return (L < med - drop) & (a[..., 0].astype(int) >= a[..., 2].astype(int) - 4) & (a[..., 3] > 0)


def recolor(a, fix, avoid=None):
    """把 fix 遮罩內的像素換成最近的「好」像素顏色（不動 alpha）。"""
    good = (a[..., 3] > 200) & ~fix
    if avoid is not None:
        good &= ~avoid
    if not good.any() or not fix.any():
        return a
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
    out = a.copy()
    ys, xs = np.nonzero(fix)
    out[ys, xs, :3] = a[iy[ys, xs], ix[ys, xs], :3]
    return out


def disc(shape, c, r):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    return (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r


def load_full(n):
    return np.array(Image.open(R.PARTS_DIR / CFG["parts"][n]["file"]).convert("RGBA"))


def fix_torso(a):
    log = {}
    dl = dark_lines(a)
    inner = ndimage.distance_transform_edt(a[..., 3] > 128)
    for j, r, xlim in (("shoulder_r", 68, lambda xx: xx < 400), ("shoulder_l", 58, lambda xx: xx > 618)):
        c = PIV[j]
        reg = disc(a.shape, c, r)
        yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
        reg &= xlim(xx)
        reg &= yy > c[1] - 72
        # 球內深色線＋球邊接縫（距透明 ≤4 px 且在球的下半圈）
        rim = (inner <= 4) & (inner > 0) & (yy > c[1] - 10)
        fix = reg & (dl | rim)
        fix = ndimage.binary_dilation(fix, iterations=1) & reg & (a[..., 3] > 0)
        a = recolor(a, fix, avoid=dl)
        log[j] = int(fix.sum())
    return a, log


def fix_thigh(a, knee):
    c = PIV[knee]
    r = CFG["tab_radius"][knee] + 8
    inner = ndimage.distance_transform_edt(a[..., 3] > 128)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    reg = disc(a.shape, c, r) & (yy > c[1] - 6)
    rim = (inner <= 4.5) & (inner > 0)
    dl = dark_lines(a)
    fix = reg & (rim | (dl & (inner <= 9)))
    return recolor(a, fix, avoid=dl), int(fix.sum())


def worried_head(parts_full):
    """回傳乾淨困惑頭（全畫布 RGBA）與記錄。"""
    parts = R.load_parts()
    im, (x0, y0), info = R.make_worried_head(parts)
    full = np.zeros((CANVAS_H, CANVAS_W, 4), np.uint8)
    arr = np.array(im)
    full[y0:y0 + arr.shape[0], x0:x0 + arr.shape[1]] = arr
    # 原母版頭（含頸部舌片）與軀幹的聯集＝可以有頸部的範圍
    allow = (parts_full["head"][..., 3] > 128) | (parts_full["torso"][..., 3] > 128)
    top = 34
    chin_local = 258           # 母版頭頂 34 → 下巴 292（頭高 258）
    # 下巴線（困惑頭在部件畫布上的鬍渣下緣），在它以下是生成圖殘留的頸部
    jaw = np.array([(380, 245), (430, 262), (470, 282), (505, 292), (540, 293), (575, 284), (600, 268), (625, 245), (660, 230)], float)
    yy, xx = np.mgrid[:CANVAS_H, :CANVAS_W]
    jaw_y = np.interp(xx, jaw[:, 0], jaw[:, 1])
    below = yy > jaw_y + 3
    log = {}
    # 生成頭覆蓋到的像素（和母版頭底圖不同的地方）
    base = parts_full["head"].copy()
    base[: top + chin_local - 30, :, 3] = 0
    gen = (np.abs(full[..., :3].astype(int) - base[..., :3].astype(int)).max(-1) > 6) | ((base[..., 3] < 128) & (full[..., 3] > 0))
    gen = ndimage.binary_dilation(gen, iterations=1) & (full[..., 3] > 0)
    # (a) 身體外的頸部突出 → 透明
    out_of_body = below & (full[..., 3] > 0) & ~allow
    full[out_of_body, 3] = 0
    log["neck_outside_body_px"] = int(out_of_body.sum())
    # (b) 頸部的深色圓弧線、白色殘點 → 鄰近膚色（只在下巴以下、領口 V 線以上）
    a = full
    dl = dark_lines(a, drop=24)
    white = (a[..., :3].min(-1) > 226) & (a[..., 3] > 0)
    neck_zone = below & gen & (yy < top + chin_local + 50)
    fix = neck_zone & (dl | white)
    fix = ndimage.binary_dilation(fix, iterations=1) & neck_zone & (a[..., 3] > 0)
    a = recolor(a, fix, avoid=dl | white)
    log["neck_lines_recolored_px"] = int(fix.sum())
    # (c) 頭內的白色殘點（距外輪廓 >3 px）→ 鄰近色；外緣的白點交給整體白邊
    inner = ndimage.distance_transform_edt(a[..., 3] > 128)
    w2 = (a[..., :3].min(-1) > 226) & (inner > 3)
    a = recolor(a, w2, avoid=w2)
    log["inner_white_specks_px"] = int(w2.sum())
    # (d) 零碎小塊
    lab, n = ndimage.label(a[..., 3] > 0)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= 400)[0])
        log["stray_px_removed"] = int(((a[..., 3] > 0) & ~keep).sum())
        a[~keep, 3] = 0
    a[..., 3] = np.where(a[..., 3] > 127, 255, 0).astype(np.uint8)
    log.update(align=info)
    return a, log


def outline_of(alpha):
    m = alpha > 127
    d = ndimage.distance_transform_edt(~m)
    white_a = np.clip(BORDER + 0.5 - d, 0, 1)
    rim_a = np.clip(BORDER + RIM + 0.5 - d, 0, 1)
    out = np.zeros(alpha.shape + (4,), np.float32)
    out[..., :3] = np.array(R.LINE, np.float32)
    w = white_a[..., None]
    out[..., :3] = out[..., :3] * (1 - w) + np.array([252, 243, 230], np.float32) * w
    out[..., 3] = rim_a * 255
    return np.clip(out, 0, 255).astype(np.uint8)


def bleed(a):
    """透明像素的 RGB 填最近的不透明色（顏色外擴，避免縮圖時出現白邊／黑邊）。"""
    m = a[..., 3] > 0
    if not m.any():
        return a
    _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
    out = a.copy()
    out[~m, :3] = a[iy[~m], ix[~m], :3]
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = list(CFG["layers"])
    full = {n: load_full(n) for n in names}
    log = {}
    full["torso"], log["torso"] = fix_torso(full["torso"])
    full["thigh_l"], log["thigh_l"] = fix_thigh(full["thigh_l"], "knee_l")
    full["thigh_r"], log["thigh_r"] = fix_thigh(full["thigh_r"], "knee_r")
    hw, log["head_worried"] = worried_head(full)
    full["head_worried"] = hw
    meta = {"source": "assets/parts/ale_v03（母版 chr-ale_master_v02 直接切件）→ G4 v04 接縫修正",
            "master_canvas": [CANVAS_W, CANVAS_H], "pad_px": PAD,
            "units": "像素＝母版像素（站姿總高約 1610 px，含白邊 1632 px）",
            "angle_convention": "姿勢角度：度，正值＝畫面上順時針（影像 y 向下）。three.js（y 向上、逆時針為正）請用 rad = -deg·π/180。",
            "outline": "白色紙芯邊只畫在擺好姿勢後的整體外輪廓：每個部件的 -outline 圖與部件同尺寸、同變換，"
                       "全部描邊放在該角色所有部件的最後面（renderOrder 最小），部件之間就不會出現白邊。",
            "pack_ids": "圖像 id＝相對 assets/final 的路徑去掉 _vNN（tools/pack.mjs），例如 rig/chr-ale_torso；本檔的 JSON id＝rig/ale_rig。",
            "layers_back_to_front": names, "parts": {}, "fix_log": log}
    for n in names + ["head_worried"]:
        a = full[n]
        ys, xs = np.nonzero(a[..., 3] > 0)
        x0, y0 = int(xs.min()) - PAD, int(ys.min()) - PAD
        x1, y1 = int(xs.max()) + 1 + PAD, int(ys.max()) + 1 + PAD
        crop = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        sx0, sy0 = max(x0, 0), max(y0, 0)
        sx1, sy1 = min(x1, CANVAS_W), min(y1, CANVAS_H)
        crop[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
        fid = "chr-ale_" + n.replace("_", "-")
        Image.fromarray(bleed(crop), "RGBA").save(OUT / f"{fid}_v04.png", optimize=True)
        Image.fromarray(bleed(outline_of(crop[..., 3])), "RGBA").save(OUT / f"{fid}-outline_v04.png", optimize=True)
        base = "head" if n == "head_worried" else n
        pc = CFG["parts"][base]
        piv = PIV[pc["joint"]] if pc["joint"] else None
        par = pc["parent"]
        rec = {"zh": pc["zh"] if n != "head_worried" else "困惑頭（含頸部舌片；換頭用，與 head 同樞紐）",
               "file": f"{fid}_v04.png", "image_id": f"rig/{fid}", "outline_file": f"{fid}-outline_v04.png", "outline_image_id": f"rig/{fid}-outline",
               "size": [int(x1 - x0), int(y1 - y0)], "origin_master": [x0, y0],
               "parent": par, "joint": pc["joint"],
               "pivot_local": None if piv is None else [round(float(piv[0] - x0), 1), round(float(piv[1] - y0), 1)],
               "pivot_master": None if piv is None else [float(piv[0]), float(piv[1])],
               "tab_radius": pc["tab_radius"],
               "layer_index": names.index(base)}
        meta["parts"][n] = rec
    # 子部件樞紐在父部件本地座標的位置
    for n, rec in meta["parts"].items():
        if rec["parent"]:
            po = meta["parts"][rec["parent"]]["origin_master"]
            rec["joint_in_parent_local"] = [round(rec["pivot_master"][0] - po[0], 1), round(rec["pivot_master"][1] - po[1], 1)]
    (OUT / "ale_rig.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
