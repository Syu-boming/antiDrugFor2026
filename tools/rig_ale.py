"""阿樂叔叔分件紙偶 rig（G2 第 2 輪；v1.2 第 15.1、15.5、22.1 節）。

做三件事：
1. 組裝檢查：把 kit_ale_v02 的 13 個部件以「關節點對齊」組回站姿，和正式母版 chr-ale_master_v02.png 半透明疊圖，
   逐件標出長度誤差與輪廓誤差（review/G2/kit_ale_v02_assembly.png、review/G2/kit_ale_v02_assembly.json）。
   A 欄＝生成部件原樣（全部同一個縮放）；B 欄＝逐件校正長寬後的 rig 部件（實際用在舞台的版本）。
2. 產出 rig 部件：逐件依母版關節距離校正長／寬（沿部件主軸的縮放，不重畫內容），
   重做固定寬度白色紙芯邊（母版尺度 11 px），把腕部空白舌片補成膚色；存到 assets/parts/ale_v02/rig/ 與 rig.json。
3. 擺姿勢：render(pose) 依關節樹旋轉部件，回傳 RGBA 與操偶線附著點（腕背、肘外、膝前）在畫面上的位置。

母版關節點（MJ）是在 50 px 格線圖上人工點選（review/G2/kit_ale_v02_assembly.png 左欄可對照），座標為母版像素。
用法：/opt/anaconda3/bin/python3 tools/rig_ale.py build   # 產出 rig 部件與組裝檢查圖
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
KIT_DIR = ROOT / "assets/parts/ale_v02"
RIG_DIR = KIT_DIR / "rig"
MASTER = ROOT / "assets/generated/chr-ale_master_v02.png"
WORRIED = ROOT / "assets/generated/chr-ale_head-worried_v02.png"
H = 258.0            # 母版頭高（頭頂 33 → 下巴 291）
BORDER = 11          # 母版尺度的白色紙芯邊寬
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)

MJ = dict(neck=(505, 330), shoulder_r=(330, 415), elbow_r=(305, 640), wrist_r=(320, 845), fingertip_r=(318, 955),
          shoulder_l=(655, 415), elbow_l=(678, 642), wrist_l=(720, 852), fingertip_l=(728, 940),
          hip_r=(420, 1005), knee_r=(415, 1255), ankle_r=(397, 1490),
          hip_l=(595, 1005), knee_l=(597, 1255), ankle_l=(602, 1490),
          waist=(515, 690), apron_top=(515, 706), apron_hem=(515, 1120))
HIP_MID = ((MJ["hip_r"][0] + MJ["hip_l"][0]) / 2, MJ["hip_r"][1])
APRON_HEM_WIDTH = 380   # 圍裙下襬（含白邊）目標寬：母版下襬 370 px，加長到大腿中段後略外擴

# 部件：父件、近端關節、遠端關節（母版）、kit 端點偵測方式
PARTS = {
    "torso": dict(parent=None, prox="neck", dist="waist"),
    "head": dict(parent="torso", prox="neck", dist=None),
    "apron_skirt": dict(parent="torso", prox="apron_top", dist="apron_hem"),
    "upper_arm_r": dict(parent="torso", prox="shoulder_r", dist="elbow_r"),
    "forearm_r": dict(parent="upper_arm_r", prox="elbow_r", dist="wrist_r"),
    "hand_r": dict(parent="forearm_r", prox="wrist_r", dist="fingertip_r"),
    "upper_arm_l": dict(parent="torso", prox="shoulder_l", dist="elbow_l"),
    "forearm_l": dict(parent="upper_arm_l", prox="elbow_l", dist="wrist_l"),
    "hand_l": dict(parent="forearm_l", prox="wrist_l", dist="fingertip_l"),
    "thigh_r": dict(parent="torso", prox="hip_r", dist="knee_r"),
    "shin_r": dict(parent="thigh_r", prox="knee_r", dist="ankle_r"),
    "thigh_l": dict(parent="torso", prox="hip_l", dist="knee_l"),
    "shin_l": dict(parent="thigh_l", prox="knee_l", dist="ankle_l"),
}
# 由後往前的層序（遠側＝角色左手、左腳；近側＝右手、右腳；大腿壓住小腿的膝舌片；圍裙下襬壓住大腿；
# 軀幹只到腰帶，所以壓在圍裙下襬上面＝圍裙上緣舌片塞在腰帶下、蝴蝶結垂帶在圍裙前）
LAYERS = ["upper_arm_l", "forearm_l", "hand_l", "shin_l", "thigh_l", "shin_r", "thigh_r",
          "apron_skirt", "torso", "head", "upper_arm_r", "forearm_r", "hand_r"]
ZH = {"head": "頭", "torso": "軀幹", "apron_skirt": "圍裙下襬", "upper_arm_r": "右上臂", "upper_arm_l": "左上臂",
      "forearm_r": "右前臂", "forearm_l": "左前臂", "hand_r": "右手", "hand_l": "左手",
      "thigh_r": "右大腿", "thigh_l": "左大腿", "shin_r": "右小腿含鞋", "shin_l": "左小腿含鞋"}


def mj(name):
    if name == "hip_mid":
        return np.array(HIP_MID, float)
    return np.array(MJ[name], float)


def font(px):
    try:
        return ImageFont.truetype(FONT[0], px, index=FONT[1])
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- 幾何工具
def affine(M, t):
    """3x3 齊次矩陣：p' = M p + t"""
    A = np.eye(3)
    A[:2, :2] = M
    A[:2, 2] = t
    return A


def rot(theta_deg):
    th = math.radians(theta_deg)
    return np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])


def rot_about(p, theta_deg):
    """畫面座標（y 向下）中繞 p 旋轉；theta>0＝畫面上順時針。"""
    R = rot(theta_deg)
    p = np.asarray(p, float)
    return affine(R, p - R @ p)


def apply(A, pts):
    pts = np.atleast_2d(np.asarray(pts, float))
    return pts @ A[:2, :2].T + A[:2, 2]


def warp_rgba(im, A, out_size):
    """把 im（部件區域座標）以 A（部件→輸出）貼到 out_size 畫布；回傳 RGBA。"""
    inv = np.linalg.inv(A)
    data = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])
    # 預乘 alpha 避免邊緣出現黑邊
    arr = np.array(im).astype(np.float32)
    a = arr[..., 3:4] / 255.0
    pre = np.concatenate([arr[..., :3] * a, arr[..., 3:4]], -1).astype(np.uint8)
    w = Image.fromarray(pre, "RGBA").transform(out_size, Image.AFFINE, data, resample=Image.BICUBIC)
    o = np.array(w).astype(np.float32)
    al = o[..., 3:4] / 255.0
    rgb = np.where(al > 1e-3, o[..., :3] / np.maximum(al, 1e-3), 0)
    return Image.fromarray(np.concatenate([np.clip(rgb, 0, 255), o[..., 3:4]], -1).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- kit 端點偵測
def principal_axis(mask):
    ys, xs = np.nonzero(mask)
    pts = np.stack([xs, ys], 1).astype(float)
    c = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    a = vt[0]
    if a[1] < 0:
        a = -a
    return c, a, pts


def tab_center(mask, end):
    """端點圓弧舌片的圓心：沿主軸從端點往內找 d，使該處寬度 ≈ 2d（半圓）。end='top' 或 'bottom'。"""
    c, a, pts = principal_axis(mask)
    n = np.array([-a[1], a[0]])
    t = (pts - c) @ a
    w = (pts - c) @ n
    if end == "top":
        t0, sgn = t.min(), 1
    else:
        t0, sgn = t.max(), -1
    best = None
    for d in np.arange(4, 0.45 * (t.max() - t.min()), 1.0):
        sel = np.abs(t - (t0 + sgn * d)) < 1.0
        if sel.sum() < 2:
            continue
        width = w[sel].max() - w[sel].min()
        if width <= 2 * d:
            mid = (w[sel].max() + w[sel].min()) / 2
            best = c + a * (t0 + sgn * d) + n * mid
            break
    if best is None:
        best = c + a * t0
    return best


def extreme(mask, end):
    c, a, pts = principal_axis(mask)
    t = (pts - c) @ a
    n = np.array([-a[1], a[0]])
    w = (pts - c) @ n
    tt = t.min() if end == "top" else t.max()
    sel = np.abs(t - tt) < 3
    return c + a * tt + n * np.median(w[sel])


def boot_top(rgb, mask):
    """小腿含鞋：棕色皮鞋開始的那一列（中心線上的點）＝腳踝。"""
    a = rgb.astype(float) / 255
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = mx - mn + 1e-6
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    brown = mask & (hue < 33) & (sat > 0.40) & (mx < 0.62)   # 皮鞋（紅棕，色相 <33°）；褲管橄欖褐約 40–45°
    rows = np.nonzero(mask.sum(1))[0]
    for y in rows:
        if mask[y].sum() > 10 and brown[y].sum() > 0.45 * mask[y].sum():
            xs = np.nonzero(mask[y])[0]
            return np.array([(xs.min() + xs.max()) / 2, y], float)
    return extreme(mask, "bottom")


def border_width(arr):
    """白色紙芯邊寬：不透明區內、深色像素（內描線）離外緣的最小距離（取 5 百分位）。"""
    m = arr[..., 3] > 128
    dist = ndimage.distance_transform_edt(m)
    v = arr[..., :3].max(-1) / 255.0
    dark = m & (v < 0.42) & (dist > 3) & (dist < 30)   # 外緣 1–2 px 的灰色抗鋸齒線不算
    if dark.sum() < 20:
        return 10.0
    return float(np.percentile(dist[dark], 5))


def torso_points(mask):
    """軀幹：頸部舌片圓心（上方中間）、左右臀部舌片中點（下方兩個圓舌）、左右肩舌片。"""
    ys, xs = np.nonzero(mask)
    y0, y1 = ys.min(), ys.max()
    hgt = y1 - y0
    # 頸部：上方 12% 列的中段
    top = mask.copy()
    top[int(y0 + 0.12 * hgt):] = False
    lab, n = ndimage.label(top)
    comps = [np.nonzero(lab == k) for k in range(1, n + 1)]
    cx_all = (xs.min() + xs.max()) / 2
    neck = None
    for cy_, cx_ in comps:
        if abs(cx_.mean() - cx_all) < 0.15 * (xs.max() - xs.min()):
            neck = np.array([cx_.mean(), cy_.min() + (cx_.max() - cx_.min()) / 2])
    if neck is None:
        neck = np.array([cx_all, y0 + 30.0])
    # 臀部：下方 9% 列的兩個圓舌
    bot = mask.copy()
    bot[:int(y1 - 0.09 * hgt)] = False
    lab, n = ndimage.label(bot)
    lobes = []
    for k in range(1, n + 1):
        yy, xx = np.nonzero(lab == k)
        if len(xx) > 30:
            r = (xx.max() - xx.min()) / 2
            lobes.append(np.array([xx.mean(), yy.max() - r]))
    hip_mid = np.mean(lobes, 0) if len(lobes) >= 2 else np.array([cx_all, y1 - 30.0])
    # 肩舌片：上方 30% 列最左、最右點往內 r
    band = mask.copy()
    band[int(y0 + 0.30 * hgt):] = False
    by, bx = np.nonzero(band)
    li, ri = bx.argmin(), bx.argmax()
    r = 0.06 * (xs.max() - xs.min())
    sh_r = np.array([bx[li] + r, by[li]])   # 畫面左＝角色右肩
    sh_l = np.array([bx[ri] - r, by[ri]])
    return neck, hip_mid, sh_r, sh_l


TORSO_TIE_ROWS = (360, 398)
TORSO_NECK = (176, 80)    # 對應母版 neck=(505,330)：下巴下方、衣領高度
TORSO_BOW_POLYS = [  # 軀幹裁切圖（assets/parts/ale_v02/torso.png）上腰帶以下要保留的蝴蝶結垂帶與右側繩圈（目視描點）
    [(246, 395), (272, 395), (272, 440), (270, 492), (228, 492), (236, 440)],
    [(272, 395), (305, 400), (322, 425), (322, 447), (300, 452), (282, 430)],
]
APRON_PLAIN_BAND = (0.775, 0.885)
APRON_WAISTBAND_FRAC = 0.17
APRON_POCKET_BAND = (0.47, 0.775)   # 口袋本體（不含剪刀與竹篾）
APRON_POCKET_STRETCH = 1.2   # 圍裙下襬裁切圖上腰頭的高度（佔高比例，目視量測）  # 圍裙下襬裁切圖上「口袋下緣到下襬縫線」的素色帶（佔高比例，目視量測）


def top_tab_center_run(mask):
    """上方舌片圓心：逐列取「含中心欄的那一段」寬度，找第一個寬度 ≤ 2d 的 d（避免肩舌片干擾）。"""
    ys, xs = np.nonzero(mask)
    y0 = ys.min()
    cx = int(round(xs[ys < y0 + 4].mean()))
    prev = None
    widths = []
    for d in range(1, 200):
        row = mask[y0 + d]
        if not row[cx]:
            continue
        l = cx
        while l > 0 and row[l - 1]:
            l -= 1
        r = cx
        while r < len(row) - 1 and row[r + 1]:
            r += 1
        w = r - l + 1
        if r - l + 1 <= 2 * d:
            return np.array([(l + r) / 2, y0 + d], float)
        if prev is not None and w > prev * 1.35 + 6:   # 舌片和衣身相連處寬度突增：以突增前的寬度當直徑
            dia = max(widths)
            return np.array([cx, y0 + dia / 2], float)
        widths.append(w)
        prev = w
    return np.array([cx, y0 + 30.0])


def navy_mask(arr):
    rgb = arr[..., :3].astype(int)
    return (arr[..., 3] > 128) & (rgb[..., 2] > rgb[..., 0] + 15) & (rgb[..., 2] >= rgb[..., 1])


def tie_band(arr):
    """軀幹的圍裙腰帶：由上往下第一段「深藍佔該列不透明寬度 ≥85%」的連續列（圍兜比襯衫窄，腰帶橫跨全寬）。"""
    m = arr[..., 3] > 128
    nv = navy_mask(arr)
    inner = ndimage.binary_erosion(m, iterations=14)
    frac = nv.sum(1) / np.maximum(inner.sum(1), 1)
    rows = np.nonzero((frac > 0.85) & (inner.sum(1) > 40))[0]
    top = int(rows.min())
    bot = top
    while bot + 1 < len(frac) and frac[bot + 1] > 0.85:
        bot += 1
    bot = min(bot, top + 45)
    return top, bot


def kit_points(name, arr):
    m = arr[..., 3] > 128
    m = ndimage.binary_fill_holes(m)
    if name == "torso":
        _, _, sh_r, sh_l = torso_points(m)
        neck = np.array(TORSO_NECK, float)   # 頸舌片是外擴形、和衣領相連，圓心自動偵測不穩；取衣領高度的頸部中點（目視量測）
        tie_top, tie_bot = TORSO_TIE_ROWS   # 腰帶列：kit 軀幹裁切圖上目視量測（圍兜下緣外擴處會誤判，所以不用自動偵測）
        xs = np.nonzero(m[(tie_top + tie_bot) // 2])[0]
        waist = np.array([(xs.min() + xs.max()) / 2, (tie_top + tie_bot) / 2])
        return dict(prox=neck, dist=waist, sh_r=sh_r, sh_l=sh_l, tie_top=tie_top, tie_bot=tie_bot)
    if name == "apron_skirt":
        # 近端＝下襬上緣的腰頭中點（舌片塞在軀幹腰帶下），遠端＝下襬底邊中點（白邊內側）
        ys, xs = np.nonzero(m)
        hh = arr.shape[0]
        yb = ys.max() - 12
        xb = xs[ys > ys.max() - 30]
        cx = (xb.min() + xb.max()) / 2
        return dict(prox=np.array([cx, APRON_WAISTBAND_FRAC * hh]), dist=np.array([cx, float(yb)]))
    if name.startswith("hand"):
        return dict(prox=tab_center(m, "top"), dist=extreme(m, "bottom"))
    if name.startswith("shin"):
        return dict(prox=tab_center(m, "top"), dist=boot_top(arr[..., :3], m))
    if name == "head":
        return dict(prox=tab_center(m, "bottom"), top=extreme(m, "top"))
    return dict(prox=tab_center(m, "top"), dist=tab_center(m, "bottom"))


def axis_frame(p, q):
    a = (q - p) / (np.linalg.norm(q - p) + 1e-9)
    n = np.array([-a[1], a[0]])
    return a, n


def seg_map(kp, kq, mp, mq, sx_over=None):
    """部件座標→母版：近端對近端、沿主軸縮放到母版長度（sy），橫向縮放 sx。回傳 (A, sy)。"""
    ak, nk = axis_frame(kp, kq)
    am, nm = axis_frame(mp, mq)
    sy = np.linalg.norm(mq - mp) / np.linalg.norm(kq - kp)
    sx = sy if sx_over is None else sx_over
    M = np.stack([am, nm], 1) @ np.diag([sy, sx]) @ np.stack([ak, nk], 1).T
    return affine(M, mp - M @ kp), sy, sx


# ---------------------------------------------------------------- 頭部：以輪廓 IoU 對齊母版（相似變換）
def register_similarity(src_mask, dst_mask, s_range, th_range, center_src, center_dst):
    best = (-1, None)
    hs, ws = dst_mask.shape
    dst = dst_mask.astype(np.float32)
    for s in s_range:
        for th in th_range:
            M = rot(th) * s
            A = affine(M, center_dst - M @ center_src)
            inv = np.linalg.inv(A)
            w = Image.fromarray((src_mask * 255).astype(np.uint8)).transform(
                (ws, hs), Image.AFFINE, (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2]),
                resample=Image.BILINEAR)
            wm = np.array(w) > 127
            # 允許小範圍平移：用質心差補正一次
            if wm.sum() == 0:
                continue
            ys, xs = np.nonzero(wm)
            dy, dx = np.nonzero(dst_mask)
            shift = np.array([dx.mean() - xs.mean(), dy.mean() - ys.mean()])
            A2 = affine(M, center_dst - M @ center_src + shift)
            inv = np.linalg.inv(A2)
            w = Image.fromarray((src_mask * 255).astype(np.uint8)).transform(
                (ws, hs), Image.AFFINE, (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2]),
                resample=Image.BILINEAR)
            wm = np.array(w) > 127
            iou = (wm & dst_mask).sum() / ((wm | dst_mask).sum() + 1e-9)
            if iou > best[0]:
                best = (iou, A2, s, th)
    return best


def head_region(mask, frac):
    m = mask.copy()
    ys = np.nonzero(m.any(1))[0]
    m[int(ys.min() + frac * (ys.max() - ys.min())):] = False
    return m


# ---------------------------------------------------------------- 部件正規化（rig 部件）
def recolor_tab(arr, center, radius):
    """把舌片上的空白紙色（低彩度、高明度）補成該部件的膚色，保留紙紋明暗。"""
    rgb = arr[..., :3].astype(float)
    a = rgb / 255
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    m = arr[..., 3] > 200
    dist_edge = ndimage.distance_transform_edt(m)
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    near = np.hypot(xx - center[0], yy - center[1]) < radius
    skin = m & (sat > 0.33) & (mx > 0.75) & (dist_edge > 14)
    cream = m & near & (sat < 0.30) & (mx > 0.66) & (dist_edge > 12)
    if skin.sum() < 50 or cream.sum() < 20:
        return arr, 0
    skin_med = np.median(rgb[skin], 0)
    lum = rgb.mean(-1)
    ref = np.median(lum[cream])
    out = arr.copy().astype(float)
    k = (lum / (ref + 1e-6))[..., None]
    soft = ndimage.gaussian_filter(cream.astype(float), 1.0)[..., None]
    out[..., :3] = rgb * (1 - soft) + np.clip(skin_med * k, 0, 255) * soft
    return out.clip(0, 255).astype(np.uint8), int(cream.sum())


def normalize_part(arr, scale, b_kit, pts, tab=None, zones=None, keep=None):
    """部件重取樣成 rig 部件：
    - scale：等比縮放（不做橫向／縱向不等比，避免紙紋與白邊變形）；
    - zones：[(y0, y1, f)] kit 列範圍再縱向拉長 f 倍（只選素色帶，例如圍兜中段、圍裙下襬口袋以下），同 tools/fix_proportion.py；
    - keep：kit 座標的保留遮罩（例如軀幹只留到腰帶＋蝴蝶結）；新切口沿內緣補 2 px 深色內描線；
    - 舊白邊去掉後重做固定寬度 BORDER 的白色紙芯邊。回傳 (陣列, 換算後的點)。"""
    if tab is not None:
        arr, _ = recolor_tab(arr, tab[0], tab[1])
    m = ndimage.binary_fill_holes(arr[..., 3] > 128)
    content = ndimage.binary_erosion(m, iterations=max(int(round(b_kit - 2)), 1))
    cut_edge = np.zeros_like(content)
    if keep is not None:
        kept = content & keep
        cut_edge = kept & ~ndimage.binary_erosion(kept, iterations=2) & ndimage.binary_dilation(content & ~keep, iterations=2)
        content = kept
    src = arr.copy()
    if cut_edge.any():
        src[..., :3] = np.where(cut_edge[..., None], (src[..., :3] * 0.32 + np.array([40, 34, 30]) * 0.4).astype(np.uint8), src[..., :3])
    src[..., 3] = (ndimage.gaussian_filter(content.astype(float), 0.6) * 255).astype(np.uint8)
    h, w = m.shape
    pad = BORDER + 6
    size = (int(np.ceil(w * scale + 2 * pad)), int(np.ceil(h * scale + 2 * pad)))
    A = affine(np.eye(2) * scale, np.array([pad, pad], float))
    warped = np.array(warp_rgba(Image.fromarray(src, "RGBA"), A, size))
    ymap = lambda y: y  # noqa: E731
    if zones:
        # 依序拉長素色帶（座標已是縮放後）
        bands, cur, segs = [], 0, []
        zs = sorted([(pad + z0 * scale, pad + z1 * scale, f) for z0, z1, f in zones])
        img = Image.fromarray(warped, "RGBA")
        out_y = 0
        for z0, z1, f in zs:
            z0, z1 = int(round(z0)), int(round(z1))
            bands.append(img.crop((0, cur, img.width, z0)))
            segs.append((cur, z0, out_y, 1.0))
            out_y += z0 - cur
            band = img.crop((0, z0, img.width, z1))
            nh = int(round((z1 - z0) * f))
            bands.append(band.resize((img.width, nh), Image.LANCZOS))
            segs.append((z0, z1, out_y, nh / (z1 - z0)))
            out_y += nh
            cur = z1
        bands.append(img.crop((0, cur, img.width, img.height)))
        segs.append((cur, img.height, out_y, 1.0))
        tot = sum(bb.height for bb in bands)
        canvas = Image.new("RGBA", (img.width, tot), (0, 0, 0, 0))
        yy = 0
        for bb in bands:
            canvas.paste(bb, (0, yy))
            yy += bb.height
        warped = np.array(canvas)

        def ymap(y):
            for s0, s1, o0, k in segs:
                if s0 <= y <= s1:
                    return o0 + (y - s0) * k
            return y
    cm = warped[..., 3] > 127
    dist = ndimage.distance_transform_edt(~cm)
    ring_soft = np.clip(BORDER + 0.5 - dist, 0, 1)
    rng = np.random.default_rng(11)
    noise = ndimage.gaussian_filter(rng.normal(0, 1, cm.shape), 0.8) * 3.0
    paper = np.stack([248 + noise, 244 + noise, 234 + noise], -1)
    outa = np.maximum(warped[..., 3].astype(float) / 255, ring_soft)
    wa = warped[..., 3:4].astype(float) / 255
    rgb = warped[..., :3] * wa + paper * (1 - wa)
    out = np.concatenate([rgb, outa[..., None] * 255], -1).clip(0, 255).astype(np.uint8)
    new_pts = {}
    for k, v in pts.items():
        q = apply(A, v)[0]
        new_pts[k] = np.array([q[0], ymap(q[1])])
    return out, new_pts


# ---------------------------------------------------------------- 主要流程
def load_kit():
    info = json.loads((KIT_DIR / "parts.json").read_text())
    parts = {}
    for name in PARTS:
        arr = np.array(Image.open(KIT_DIR / info["parts"][name]["file"]).convert("RGBA"))
        parts[name] = arr
    return parts


def master_mask():
    im = Image.open(MASTER).convert("RGBA")
    return im, np.array(im)[..., 3] > 128


def build():
    parts = load_kit()
    mim, mmask = master_mask()
    kp = {n: kit_points(n, a) for n, a in parts.items()}
    bw = {n: border_width(a) for n, a in parts.items()}
    fits = {}
    # 1) 每件需要的縮放：關節距離（母版）÷ 關節距離（kit）
    for name, spec in PARTS.items():
        if name == "head":
            continue
        p, q = kp[name]["prox"], kp[name]["dist"]
        mp, mq = mj(spec["prox"]), mj(spec["dist"])
        fits[name] = dict(sy=float(np.linalg.norm(mq - mp) / np.linalg.norm(q - p)),
                          kit_len=float(np.linalg.norm(q - p)), master_len=float(np.linalg.norm(mq - mp)))
    limb = [n for n in fits if n not in ("torso", "apron_skirt")]
    g = float(np.median([fits[n]["sy"] for n in limb]))
    # 2) 縮放策略：四肢與手腳等比（sx＝sy）；軀幹等比（頸→腰帶）；圍裙下襬以下襬寬定比例，口袋以下素色帶拉長到大腿中段
    for name in fits:
        fits[name]["sx"] = fits[name]["sy"]
        fits[name]["zones"] = None
    m_ap = parts["apron_skirt"][..., 3] > 128
    ys_, xs_ = np.nonzero(m_ap)
    hem_w = float(np.ptp(xs_[ys_ > ys_.max() - 25]))
    s_ap = APRON_HEM_WIDTH / hem_w
    hgt = parts["apron_skirt"].shape[0]
    z0, z1 = APRON_PLAIN_BAND[0] * hgt, APRON_PLAIN_BAND[1] * hgt
    k0, k1 = APRON_POCKET_BAND[0] * hgt, APRON_POCKET_BAND[1] * hgt
    p, q = kp["apron_skirt"]["prox"], kp["apron_skirt"]["dist"]
    need = fits["apron_skirt"]["master_len"] / s_ap - (q[1] - p[1])   # 要補的長度（kit 像素）
    need -= (APRON_POCKET_STRETCH - 1) * (k1 - k0)                    # 口袋帶先分擔一點（×1.2）
    f_ap = 1 + need / (z1 - z0)
    fits["apron_skirt"].update(sx=float(s_ap), sy=float(s_ap),
                               zones=[(float(k0), float(k1), APRON_POCKET_STRETCH), (float(z0), float(z1), float(f_ap))])
    # 3) 頭：輪廓 IoU 對齊（只比頭與頸，不含衣領）
    hk = ndimage.binary_fill_holes(parts["head"][..., 3] > 128)
    hk_top = head_region(hk, 0.72)
    hm_top = mmask.copy()
    hm_top[300:] = False
    ys, xs = np.nonzero(hk_top)
    ck = np.array([xs.mean(), ys.mean()])
    ys2, xs2 = np.nonzero(hm_top)
    cm_ = np.array([xs2.mean(), ys2.mean()])
    best = register_similarity(hk_top, hm_top, np.linspace(0.70, 1.05, 15), np.arange(-10, 10.5, 2), ck, cm_)
    iou_head, A_head, s_head, th_head = best
    fits["head"] = dict(sy=float(s_head), sx=float(s_head), rot=float(th_head), iou_with_master_head=round(float(iou_head), 3),
                        kit_len=None, master_len=None, zones=None)

    # 4) A：同一縮放 g（不校正）；B：逐件校正後的 rig 部件
    canvas = (mim.width, mim.height)
    placedA, placedB, rig = {}, {}, {}
    RIG_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in PARTS.items():
        arr = parts[name]
        if name == "head":
            AA = affine(rot(th_head) * g, apply(A_head, ck)[0] - (rot(th_head) * g) @ ck)
            placedA[name] = warp_rgba(Image.fromarray(arr, "RGBA"), AA, canvas)
            pts = dict(prox=kp[name]["prox"], top=kp[name]["top"])
            out, npts = normalize_part(arr, s_head, bw[name], pts)
            A_rest = affine(rot(th_head), apply(A_head, kp[name]["prox"])[0] - rot(th_head) @ npts["prox"])
        else:
            p, q = kp[name]["prox"], kp[name]["dist"]
            mp, mq = mj(spec["prox"]), mj(spec["dist"])
            AA, _, _ = seg_map(p, q, mp, mp + (mq - mp) / np.linalg.norm(mq - mp) * np.linalg.norm(q - p) * g, sx_over=g)
            placedA[name] = warp_rgba(Image.fromarray(arr, "RGBA"), AA, canvas)
            pts = dict(prox=p, dist=q)
            tab, keep = None, None
            if name.startswith("hand"):
                tab = (p, 0.50 * np.linalg.norm(q - p))
            elif name.startswith("forearm"):
                tab = (q, 0.30 * np.linalg.norm(q - p))
            if name == "torso":
                # 腰帶以下由圍裙下襬蓋住：只留到腰帶下緣，加上垂下的蝴蝶結與綁帶
                hh, ww = arr.shape[:2]
                keep = np.zeros((hh, ww), bool)
                keep[:kp["torso"]["tie_bot"] + 3] = True
                poly = Image.new("L", (ww, hh), 0)
                for pg in TORSO_BOW_POLYS:
                    ImageDraw.Draw(poly).polygon(pg, fill=255)
                keep |= np.array(poly) > 0
            out, npts = normalize_part(arr, fits[name]["sy"], bw[name], pts, tab=tab, zones=fits[name]["zones"], keep=keep)
            a_now, _ = axis_frame(npts["prox"], npts["dist"])
            am, _ = axis_frame(mp, mq)
            ang = math.degrees(math.atan2(am[1], am[0]) - math.atan2(a_now[1], a_now[0]))
            R = rot(ang)
            A_rest = affine(R, mp - R @ npts["prox"])
            fits[name]["rest_rot_deg"] = round(ang, 2)
        Image.fromarray(out, "RGBA").save(RIG_DIR / f"{name}.png")
        rig[name] = dict(file=f"rig/{name}.png", parent=spec["parent"], joint=spec["prox"],
                         pivot_local=[round(float(v), 2) for v in npts["prox"]],
                         A_rest=[[round(float(v), 5) for v in row] for row in A_rest[:2]])
        placedB[name] = warp_rgba(Image.fromarray(out, "RGBA"), A_rest, canvas)

    # 5) 誤差量測
    def union_mask(placed):
        u = np.zeros(mmask.shape, bool)
        for n in placed:
            u |= np.array(placed[n])[..., 3] > 128
        return u
    edge_m = mmask & ~ndimage.binary_erosion(mmask)
    dist_out = ndimage.distance_transform_edt(~mmask)    # 母版外的距離
    dist_in = ndimage.distance_transform_edt(mmask)      # 母版內的距離
    report = {}
    for tag, placed in (("A", placedA), ("B", placedB)):
        u = union_mask(placed)
        u_edge = u & ~ndimage.binary_erosion(u)
        per = {}
        for n in PARTS:
            pm = np.array(placed[n])[..., 3] > 128
            pe = pm & ~ndimage.binary_erosion(pm) & u_edge
            if pe.sum() < 10:
                per[n] = None
                continue
            d = np.where(mmask[pe], -dist_in[pe], dist_out[pe])
            outside = pm & ~mmask
            per[n] = dict(outline_px=int(pe.sum()), mean_abs_px=round(float(np.abs(d).mean()), 1),
                          p95_abs_px=round(float(np.percentile(np.abs(d), 95)), 1),
                          mean_abs_H=round(float(np.abs(d).mean() / H), 3),
                          outside_area_px=int(outside.sum()))
        iou = float((u & mmask).sum() / ((u | mmask).sum()))
        missing = mmask & ~u
        report[tag] = dict(iou=round(iou, 3), missing_px=int(missing.sum()), extra_px=int((u & ~mmask).sum()), parts=per)
    for n in fits:
        f = fits[n]
        f["border_kit_px"] = round(bw[n], 1)
        f["scale_vs_g"] = round(f["sy"] / g, 3)
        if f.get("kit_len"):
            f["len_error_at_g_H"] = round((f["kit_len"] * g - f["master_len"]) / H, 3)
    rig_json = dict(source_kit="review/G2/raw/kit_ale_v02.png", master="assets/generated/chr-ale_master_v02.png",
                    master_head_px=H, border_px=BORDER, global_scale_g=round(g, 4), joints_master=MJ,
                    hip_mid=HIP_MID, layers=LAYERS, parts=rig,
                    note="A_rest：rig 部件像素→母版像素（站姿）。pose 角度單位為度，正值＝畫面上順時針，繞該件近端關節。")
    (KIT_DIR / "rig.json").write_text(json.dumps(rig_json, ensure_ascii=False, indent=1))
    out = dict(global_scale_g=round(g, 4), head_registration=fits["head"], fits={n: {k: (round(v, 4) if isinstance(v, float) else v)
                                                                                         for k, v in f.items()} for n, f in fits.items()},
               assembly=report,
               notes=["A＝生成部件原樣、全部同一縮放 g（看生成比例誤差）；B＝逐件依母版關節距離校正長寬、重做白邊後的 rig 部件（舞台實際使用）。",
                      "輪廓誤差＝組裝外輪廓上、屬於該部件的邊緣像素到母版輪廓的距離（母版像素；母版頭高 258 px）。",
                      "圍裙下襬依第 1 輪美術總監意見刻意加長到大腿中段（母版下襬 y≈1030 → 1120），所以 B 欄圍裙下襬超出母版輪廓屬於刻意差異。"])
    (ROOT / "review/G2/kit_ale_v02_assembly.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    assembly_sheet(mim, mmask, placedA, placedB, fits, report, g)
    print(json.dumps(dict(g=g, head=fits["head"], A=report["A"]["iou"], B=report["B"]["iou"],
                          sy={n: round(fits[n]["sy"], 3) for n in fits}), ensure_ascii=False, indent=1))


PALETTE = [(230, 60, 60), (40, 150, 230), (240, 170, 20), (60, 180, 90), (170, 80, 220), (20, 190, 190),
           (230, 110, 170), (120, 120, 240), (200, 140, 60), (90, 200, 40), (240, 90, 30), (60, 90, 160), (160, 60, 100)]


def assembly_sheet(mim, mmask, placedA, placedB, fits, report, g):
    sc = 0.5
    W0, H0 = mim.size
    pw, ph = int(W0 * sc), int(H0 * sc)
    head_h = 70
    table_h = 560
    sheet = Image.new("RGB", (pw * 3 + 80, head_h + ph + table_h), (46, 46, 48))
    d = ImageDraw.Draw(sheet)
    f1, f2, f3 = font(28), font(20), font(17)
    d.text((20, 14), "阿樂叔叔 kit_ale_v02：部件組裝回站姿 vs 正式母版 chr-ale_master_v02（6.15 頭身）", font=f1, fill=(240, 240, 240))
    gray_bg = (150, 150, 146)
    # 欄 1：母版＋關節
    c1 = Image.new("RGBA", (W0, H0), gray_bg + (255,))
    c1.alpha_composite(mim)
    dd = ImageDraw.Draw(c1)
    for k, (x, y) in MJ.items():
        dd.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(255, 30, 30), width=4)
    for a, b in [("neck", "shoulder_r"), ("neck", "shoulder_l"), ("shoulder_r", "elbow_r"), ("elbow_r", "wrist_r"),
                 ("shoulder_l", "elbow_l"), ("elbow_l", "wrist_l"), ("hip_r", "knee_r"), ("knee_r", "ankle_r"),
                 ("hip_l", "knee_l"), ("knee_l", "ankle_l"), ("hip_r", "hip_l"), ("waist", "apron_hem")]:
        dd.line([MJ[a], MJ[b]], fill=(255, 230, 0), width=3)
    sheet.paste(c1.convert("RGB").resize((pw, ph), Image.LANCZOS), (20, head_h))
    d.text((24, head_h + 6), "① 母版＋關節點（人工點選）", font=f2, fill=(20, 20, 20))

    def overlay(placed, rep, x0, title):
        base = np.zeros((H0, W0, 3), np.float32) + np.array(gray_bg, np.float32)
        mrgb = np.array(mim.convert("RGB")).astype(np.float32)
        base = np.where(mmask[..., None], base * 0.45 + mrgb * 0.55 * 0.6 + 40, base)
        img = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")
        for n in LAYERS:
            p = np.array(placed[n]).copy()
            p[..., 3] = (p[..., 3] * 0.62).astype(np.uint8)
            img.alpha_composite(Image.fromarray(p, "RGBA"))
        dd = ImageDraw.Draw(img)
        medge = mmask & ~ndimage.binary_erosion(mmask, iterations=2)
        arr = np.array(img)
        arr[medge] = (255, 255, 255, 255)
        img = Image.fromarray(arr, "RGBA")
        dd = ImageDraw.Draw(img)
        for i, n in enumerate(LAYERS):
            pm = np.array(placed[n])[..., 3] > 128
            e = pm & ~ndimage.binary_erosion(pm, iterations=2)
            arr = np.array(img)
            arr[e] = PALETTE[i % len(PALETTE)] + (255,)
            img = Image.fromarray(arr, "RGBA")
        dd = ImageDraw.Draw(img)
        fl = font(30)
        for i, n in enumerate(LAYERS):
            pm = np.array(placed[n])[..., 3] > 128
            ys, xs = np.nonzero(pm)
            r = rep["parts"].get(n)
            lab = f"{ZH[n]} {r['mean_abs_px']:.0f}px" if r else f"{ZH[n]} —"
            tx = int(np.clip(xs.mean() - 60, 0, W0 - 200))
            dd.text((tx, int(ys.mean())), lab, font=fl, fill=PALETTE[i % len(PALETTE)], stroke_width=3, stroke_fill=(0, 0, 0))
        sheet.paste(img.convert("RGB").resize((pw, ph), Image.LANCZOS), (x0, head_h))
        d.text((x0 + 4, head_h + 6), title, font=f2, fill=(20, 20, 20))
        d.text((x0 + 4, head_h + 32), f"IoU {rep['iou']:.3f}｜缺 {rep['missing_px']} px｜多 {rep['extra_px']} px", font=f3, fill=(20, 20, 20))

    overlay(placedA, report["A"], 40 + pw, f"② 生成部件原樣（同一縮放 g={g:.3f}）")
    overlay(placedB, report["B"], 60 + 2 * pw, "③ 逐件校正長寬後的 rig 部件（舞台用）")
    y = head_h + ph + 16
    d.text((20, y), "白線＝母版輪廓；彩色線＝各部件輪廓；標籤數字＝該件外輪廓到母版輪廓的平均距離（母版像素，頭高 258 px）。", font=f3, fill=(220, 220, 220))
    y += 30
    cols = ["部件", "kit 關節距 px", "母版關節距 px", "② 長度誤差（頭高）", "rig 縮放", "相對 g", "② 輪廓 平均/95% px", "③ 輪廓 平均/95% px", "備註"]
    xs_ = [20, 150, 300, 450, 640, 780, 900, 1110, 1320]
    for x, c in zip(xs_, cols):
        d.text((x, y), c, font=f3, fill=(255, 220, 120))
    y += 26
    for n in ["head", "torso", "apron_skirt", "upper_arm_r", "upper_arm_l", "forearm_r", "forearm_l", "hand_r", "hand_l",
              "thigh_r", "thigh_l", "shin_r", "shin_l"]:
        f = fits[n]
        rA, rB = report["A"]["parts"].get(n), report["B"]["parts"].get(n)
        note = ""
        if n == "head":
            note = f"輪廓 IoU 對齊（{f['iou_with_master_head']:.2f}）、等比 {f['sy']:.3f}"
        if n == "apron_skirt":
            note = "口袋帶 ×%.2f、口袋以下素色帶 ×%.2f；刻意加長到大腿中段" % (f["zones"][0][2], f["zones"][1][2])
        if n == "torso":
            note = "頸→腰帶；腰帶以下改由圍裙下襬蓋住"
        vals = [ZH[n], f"{f['kit_len']:.0f}" if f.get("kit_len") else "—", f"{f['master_len']:.0f}" if f.get("master_len") else "—",
                f"{f.get('len_error_at_g_H', 0):+.2f}" if f.get("kit_len") else "—", f"{f['sy']:.3f}", f"×{f['sy'] / g:.2f}",
                f"{rA['mean_abs_px']:.0f} / {rA['p95_abs_px']:.0f}" if rA else "（被遮住）",
                f"{rB['mean_abs_px']:.0f} / {rB['p95_abs_px']:.0f}" if rB else "（被遮住）", note]
        for x, v in zip(xs_, vals):
            d.text((x, y), v, font=f3, fill=(235, 235, 235))
        y += 25
    sheet.save(ROOT / "review/G2/kit_ale_v02_assembly.png")


# ---------------------------------------------------------------- 擺姿勢
class Rig:
    def __init__(self, head_override=None):
        self.cfg = json.loads((KIT_DIR / "rig.json").read_text())
        self.parts = {}
        for n, p in self.cfg["parts"].items():
            self.parts[n] = Image.open(KIT_DIR / p["file"]).convert("RGBA")
        self.A_rest = {n: np.vstack([np.array(p["A_rest"]), [0, 0, 1]]) for n, p in self.cfg["parts"].items()}
        if head_override is not None:
            im, A = head_override
            self.parts["head"] = im
            self.A_rest["head"] = A

    def joint_pos(self, name):
        if name == "hip_mid":
            return np.array(self.cfg["hip_mid"], float)
        return np.array(self.cfg["joints_master"][name], float)

    def world(self, pose):
        """回傳每件的姿勢矩陣（母版站姿座標 → 母版座標的姿勢）。pose: {部件: 角度}，另可給 'root': (dx, dy, 角度, 樞紐)。"""
        Mw = {}
        order = ["torso", "head", "apron_skirt", "upper_arm_r", "forearm_r", "hand_r", "upper_arm_l", "forearm_l",
                 "hand_l", "thigh_r", "shin_r", "thigh_l", "shin_l"]
        root = pose.get("root", (0, 0, 0, "hip_mid"))
        base = affine(np.eye(2), np.array(root[:2], float)) @ rot_about(self.joint_pos(root[3]), root[2])
        for n in order:
            spec = PARTS[n]
            par = Mw[spec["parent"]] if spec["parent"] else base
            Mw[n] = par @ rot_about(self.joint_pos(spec["prox"]), pose.get(n, 0.0))
        return Mw

    def render(self, pose, canvas=(1700, 1900), offset=(338, 120)):
        Mw = self.world(pose)
        T = affine(np.eye(2), np.array(offset, float))
        img = Image.new("RGBA", canvas, (0, 0, 0, 0))
        for n in LAYERS:
            A = T @ Mw[n] @ self.A_rest[n]
            img.alpha_composite(warp_rgba(self.parts[n], A, canvas))
        return img, (lambda part, p: apply(T @ Mw[part], p)[0]), Mw


def make_worried_head():
    """換片頭：生成的困惑表情頭以輪廓 IoU 對齊 rig 的微笑頭（等比＋旋轉），回傳 (影像, A_rest)。"""
    cfg = json.loads((KIT_DIR / "rig.json").read_text())
    smile = np.array(Image.open(KIT_DIR / cfg["parts"]["head"]["file"]).convert("RGBA"))
    A_s = np.vstack([np.array(cfg["parts"]["head"]["A_rest"]), [0, 0, 1]])
    wim = Image.open(WORRIED).convert("RGBA")
    w = np.array(wim)
    w[..., 3] = np.where(w[..., 3] < 24, 0, w[..., 3])
    wm = ndimage.binary_fill_holes(w[..., 3] > 128)
    sm = ndimage.binary_fill_holes(smile[..., 3] > 128)
    s_top, w_top = head_region(sm, 0.72), head_region(wm, 0.72)
    ys, xs = np.nonzero(w_top)
    cw = np.array([xs.mean(), ys.mean()])
    ys2, xs2 = np.nonzero(s_top)
    cs = np.array([xs2.mean(), ys2.mean()])
    ratio = math.sqrt(s_top.sum() / w_top.sum())
    iou, A_ws, s, th = register_similarity(w_top, s_top, np.linspace(ratio * 0.9, ratio * 1.1, 9), np.arange(-30, 31, 3), cw, cs)
    # 重取樣到 smile 頭的尺度（等比 s），並重做白邊
    bwk = border_width(w)
    out, npts = normalize_part(w, float(s), bwk, dict(c=cw))
    # A：worried rig 像素 → smile 局部 → 母版
    R = rot(th)
    A_local = affine(R, apply(A_ws, cw)[0] - R @ npts["c"])
    return Image.fromarray(out, "RGBA"), A_s @ A_local, dict(iou=round(float(iou), 3), scale=round(float(s), 3), rot=float(th))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "worried"])
    args = ap.parse_args()
    if args.cmd == "build":
        build()
        args.cmd = "worried"
    if args.cmd == "worried":
        # 換片頭（困惑、需要幫忙）：對齊到微笑頭後存成 rig 部件，A_rest 寫進 rig.json 的 alt_heads
        im, A, info = make_worried_head()
        im.save(RIG_DIR / "head_worried.png")
        cfg = json.loads((KIT_DIR / "rig.json").read_text())
        cfg["alt_heads"] = {"worried": dict(file="rig/head_worried.png", source="assets/generated/chr-ale_head-worried_v02.png",
                                            A_rest=[[round(float(v), 5) for v in row] for row in A[:2]], alignment=info)}
        (KIT_DIR / "rig.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
        print("worried head", info)


if __name__ == "__main__":
    main()
