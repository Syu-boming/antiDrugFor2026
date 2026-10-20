"""阿樂叔叔分件紙偶 rig v03（G2 第 2 輪重驗意見 3、26、29）：部件直接由正式母版切出（tools/master_cut.py）。

和 v02 的差別：
- 部件與母版同尺度、同座標，沒有任何非等比拉伸（v02 曾用 ×1.43、×2.60 補長度）。站姿組回去與母版逐像素相同。
- 白色紙芯邊只畫在「擺好姿勢後的整體外輪廓」：部件本身沒有白邊，部件之間是深色細接縫（master_cut 已畫好）。
- 上臂在軀幹後層，肩部圓形舌片永遠藏在軀幹後面；肘、腕、膝的後層部件下端是以關節為圓心的圓形舌片，任何角度都蓋得住。

用法：
  /opt/anaconda3/bin/python3 tools/rig_ale_v03.py check   # 組裝檢查（站姿 vs 母版）＋舉臂、受拉兩種姿勢的關節特寫
輸出：review/G2/kit_ale_v03_assembly.png、kit_ale_v03_assembly.json、kit_ale_v03_poses.png
姿勢角度單位為度，正值＝畫面上順時針；"root"＝(dx, dy, 角度, 樞紐) 作用在軀幹。
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
PARTS_DIR = ROOT / "assets/parts/ale_v03"
MASTER = ROOT / "assets/generated/chr-ale_master_v02.png"
WORRIED = ROOT / "assets/generated/chr-ale_head-worried_v02.png"
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)
H = 258.0             # 母版頭高（頭頂 33 → 下巴 291）
BORDER = 11.0         # 白色紙芯邊（母版尺度）
RIM = 1.6             # 白邊外側深色細線
LINE = (84, 75, 67)
CANVAS = (1800, 1900)
OFFSET = (388, 150)   # 母版座標 → 輸出畫布

CFG = json.loads((PARTS_DIR / "parts.json").read_text())
PIV = {k: np.array(v, float) for k, v in CFG["pivots"].items()}
LAYERS = CFG["layers"]
PARENT = {n: CFG["parts"][n]["parent"] for n in LAYERS}
JOINT = {n: CFG["parts"][n]["joint"] for n in LAYERS}
HIP_MID = (PIV["hip_r"] + PIV["hip_l"]) / 2
MJ = dict(PIV)
MJ.update(hip_mid=HIP_MID, fingertip_r=np.array([316.0, 960.0]), fingertip_l=np.array([735.0, 955.0]),
          ankle_r=np.array([400.0, 1490.0]), ankle_l=np.array([602.0, 1490.0]), waist=np.array([515.0, 690.0]))
ZH = {n: CFG["parts"][n]["zh"] for n in LAYERS}


def font(px):
    try:
        return ImageFont.truetype(FONT[0], px, index=FONT[1])
    except OSError:
        return ImageFont.load_default()


def rot(theta_deg):
    """畫面上順時針為正（y 向下的座標系）。"""
    t = math.radians(theta_deg)
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def trans(dx, dy):
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1.0]])


def about(p, theta):
    return trans(p[0], p[1]) @ rot(theta) @ trans(-p[0], -p[1])


def apply(M, p):
    p = np.asarray(p, float)
    return (M @ np.array([p[0], p[1], 1.0]))[:2]


def load_parts():
    parts = {}
    for n in LAYERS:
        im = Image.open(PARTS_DIR / CFG["parts"][n]["file"]).convert("RGBA")
        x0, y0, x1, y1 = CFG["parts"][n]["bbox"]
        parts[n] = (im.crop((x0, y0, x1, y1)), (x0, y0))
    return parts


def strip_border(arr, width=None):
    """去掉換片圖的外輪廓白邊與外側細線（與 master_cut 同法：距外輪廓 ≤ 白邊寬＋外線）。"""
    a = arr.copy()
    a[..., 3] = np.where(a[..., 3] < 24, 0, a[..., 3])
    core = a[..., 3] > 128
    d = ndimage.distance_transform_edt(core)
    if width is None:
        # 由外往內找第一條深色內描線
        prof = []
        for k in range(1, 40):
            ring = (d >= k) & (d < k + 1)
            prof.append(np.median(a[ring][:, :3].min(1)) if ring.any() else 0)
        prof = np.array(prof)
        white_end = int(np.nonzero(prof > 200)[0].max()) + 1 if (prof > 200).any() else 10
        width = white_end + 0.5
    keep = core & (d > width)
    a[..., 3] = np.where(keep, 255, 0).astype(np.uint8)
    return a, width


def make_worried_head(parts):
    """困惑換片頭：生成圖去白邊 → 以「頭頂到下巴 70%」的輪廓 IoU 對齊母版頭（等比＋旋轉＋平移）→
    疊在母版頭的頸部舌片上（V 領與衣領內的頸部沿用母版膚色）。回傳 (RGBA 裁切圖, 左上角, 資訊)。"""
    w = np.array(Image.open(WORRIED).convert("RGBA"))
    w, bw = strip_border(w)
    head_im, (hx0, hy0) = parts["head"]
    hm = np.array(head_im)
    full = np.zeros((CFG["canvas"][1], CFG["canvas"][0], 4), np.uint8)
    full[hy0:hy0 + hm.shape[0], hx0:hx0 + hm.shape[1]] = hm
    mmask = full[..., 3] > 128
    # 母版頭的頭頂到下巴（頭高 H）只取上 70%
    ys = np.nonzero(mmask.any(1))[0]
    top = ys.min()
    m_top = mmask.copy()
    m_top[int(top + 0.70 * H):] = False
    wmask = w[..., 3] > 128
    wys = np.nonzero(wmask.any(1))[0]
    # 生成頭的下巴：輪廓寬度在下半部最窄處之前的位置，近似用「上 70% 頭高」＝面積比例換算
    best = None
    s0 = math.sqrt(m_top.sum() / max(wmask[: int(wys.min() + 0.55 * (wys.max() - wys.min()))].sum(), 1))
    yy, xx = np.nonzero(m_top)
    cm = np.array([xx.mean(), yy.mean()])
    for s in np.linspace(s0 * 0.85, s0 * 1.15, 13):
        for th in range(-24, 25, 3):
            # 生成頭縮放後，同樣取上 70% 頭高
            M = trans(*cm) @ rot(th) @ np.diag([s, s, 1])
            wy, wx = np.nonzero(wmask)
            pts = np.stack([wx, wy, np.ones_like(wx)], 0).astype(float)
            q = (M @ pts)[:2]
            qtop = q[1].min()
            sel = q[1] < qtop + 0.70 * H
            if sel.sum() < 100:
                continue
            c = q[:, sel].mean(1)
            dx, dy = cm - c
            xs_, ys_ = np.round(q[0, sel] + dx).astype(int), np.round(q[1, sel] + dy).astype(int)
            ok = (xs_ >= 0) & (xs_ < mmask.shape[1]) & (ys_ >= 0) & (ys_ < mmask.shape[0])
            canvas = np.zeros_like(mmask)
            canvas[ys_[ok], xs_[ok]] = True
            canvas = ndimage.binary_closing(canvas, iterations=1)
            inter = (canvas & m_top).sum()
            uni = (canvas | m_top).sum()
            iou = inter / uni
            if best is None or iou > best[0]:
                best = (iou, s, th, dx, dy)
    iou, s, th, dx, dy = best
    M = trans(dx, dy) @ trans(*cm) @ rot(th) @ np.diag([s, s, 1])
    Minv = np.linalg.inv(M)
    wim = Image.fromarray(w, "RGBA")
    warped = wim.transform((mmask.shape[1], mmask.shape[0]), Image.AFFINE, data=tuple(Minv[:2].ravel()), resample=Image.BICUBIC)
    wa = np.array(warped)
    # 頸部舌片（母版頭在下巴以下的部分）墊在後面
    base = full.copy()
    chin_y = int(top + H)
    base[: chin_y - 30, :, 3] = 0
    out = Image.fromarray(base, "RGBA")
    out.alpha_composite(Image.fromarray(wa, "RGBA"))
    o = np.array(out)
    o[..., 3] = np.where(o[..., 3] > 127, 255, 0)
    ys2, xs2 = np.nonzero(o[..., 3])
    x0, y0, x1, y1 = xs2.min(), ys2.min(), xs2.max() + 1, ys2.max() + 1
    return Image.fromarray(o[y0:y1, x0:x1], "RGBA"), (int(x0), int(y0)), dict(iou_top70=round(float(iou), 3), scale=round(float(s), 3),
                                                                          rot_deg=int(th), border_px=float(bw))


class Rig:
    def __init__(self, head="smile"):
        self.parts = load_parts()
        self.head_info = None
        if head == "worried":
            im, xy, info = make_worried_head(self.parts)
            self.parts["head"] = (im, xy)
            self.head_info = info

    def world(self, pose):
        dx, dy, th, pv = pose.get("root", (0, 0, 0, "hip_mid"))
        M = {"torso": trans(dx, dy) @ about(MJ[pv], th)}
        for n in LAYERS:
            if n == "torso":
                continue
        order = ["torso", "head", "upper_arm_r", "forearm_r", "hand_r", "upper_arm_l", "forearm_l", "hand_l",
                 "thigh_r", "shin_r", "thigh_l", "shin_l"]
        for n in order[1:]:
            M[n] = M[PARENT[n]] @ about(PIV[JOINT[n]], pose.get(n, 0.0))
        return M

    def render(self, pose, outline=True, scale=1.0, masks=False):
        """回傳 (RGBA 畫布, pt(part, 母版點)→畫布點, 世界矩陣, [各部件遮罩])。畫布為 CANVAS×scale，母版點 (0,0) 在 OFFSET×scale。"""
        Mw = self.world(pose)
        S = trans(OFFSET[0] * scale, OFFSET[1] * scale) @ np.diag([scale, scale, 1])
        size = (int(CANVAS[0] * scale), int(CANVAS[1] * scale))
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        pm = {}
        for n in LAYERS:
            im, (x0, y0) = self.parts[n]
            M = S @ Mw[n] @ trans(x0, y0)
            Minv = np.linalg.inv(M)
            warped = im.transform(size, Image.AFFINE, data=tuple(Minv[:2].ravel()), resample=Image.BICUBIC)
            canvas.alpha_composite(warped)
            if masks:
                pm[n] = np.array(warped)[..., 3] > 100
        if outline:
            canvas = add_outline(canvas, BORDER * scale, RIM * scale)

        def pt(part, p):
            return apply(S @ Mw[part], p)
        return canvas, pt, Mw, pm


def add_outline(canvas, border, rim):
    """沿整體外輪廓畫白色紙芯邊＋外側深色細線（部件之間不畫白邊）。"""
    a = np.array(canvas)
    m = a[..., 3] > 127
    d = ndimage.distance_transform_edt(~m)
    white_a = np.clip(border + 0.5 - d, 0, 1)
    rim_a = np.clip(border + rim + 0.5 - d, 0, 1)
    out = np.zeros_like(a, dtype=np.float32)
    out[..., :3] = np.array(LINE, np.float32)
    out[..., 3] = rim_a * 255
    w = white_a[..., None]
    out[..., :3] = out[..., :3] * (1 - w) + np.array([252, 243, 230], np.float32) * w
    base = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    base.alpha_composite(canvas)
    return base


# 姿勢（G2 第 3 輪）：右手（畫面左側；a2_c001 的細線就在右手腕背）想揮手 → 線繃緊 → 手腕被拉到旁邊；
# 左手收在胸前（讓左側身體外緣淨空）；膝前線扣左膝（畫面右側），近乎垂直往上、走身體外側
POSES = {
    "rest": {},
    "wave": {"upper_arm_r": 150, "forearm_r": 12, "hand_r": 6, "upper_arm_l": 16, "forearm_l": 128, "hand_l": 22, "head": 3,
             "thigh_l": -4, "shin_l": 6},
    "stopped": {"upper_arm_r": 112, "forearm_r": 38, "hand_r": -62, "upper_arm_l": 16, "forearm_l": 128, "hand_l": 22, "head": 2,
                "thigh_l": -10, "shin_l": 16},
    "pulled": {"upper_arm_r": 84, "forearm_r": 10, "hand_r": -92, "upper_arm_l": 16, "forearm_l": 128, "hand_l": 22,
               "thigh_l": -18, "shin_l": 38, "head": 2, "root": (0, 0, 1.0, "hip_mid")},
}


def assembly_check(out_png, out_json):
    rig = Rig()
    img, pt, _, _ = rig.render({}, outline=True)
    a = np.array(img)
    master = np.array(Image.open(MASTER).convert("RGBA"))
    ma = np.where(master[..., 3] < 24, 0, master[..., 3]) > 128
    H_, W_ = ma.shape
    sub = a[OFFSET[1]:OFFSET[1] + H_, OFFSET[0]:OFFSET[0] + W_]
    ra = sub[..., 3] > 128
    iou = (ra & ma).sum() / (ra | ma).sum()
    # 逐件：站姿下看得到的區域 vs 母版分配區（輪廓距離）
    rig2 = Rig()
    _, _, _, pm = rig2.render({}, outline=False, masks=True)
    vis = {}
    covered = np.zeros(CANVAS[::-1], bool)
    for n in reversed(LAYERS):
        vis[n] = pm[n] & ~covered
        covered |= pm[n]
    rows = {}
    labels = np.array(Image.open(PARTS_DIR / "_labels.png"))
    for i, n in enumerate(LAYERS):
        own = np.zeros(CANVAS[::-1], bool)
        own[OFFSET[1]:OFFSET[1] + H_, OFFSET[0]:OFFSET[0] + W_] = labels == i
        v = vis[n]
        bv = v & ~ndimage.binary_erosion(v)
        bo = own & ~ndimage.binary_erosion(own)
        if bv.sum() == 0 or bo.sum() == 0:
            continue
        dist_o = ndimage.distance_transform_edt(~bo)
        dist_v = ndimage.distance_transform_edt(~bv)
        dd = np.concatenate([dist_o[bv], dist_v[bo]])
        rows[n] = dict(zh=ZH[n], mean_px=round(float(dd.mean()), 1), p95_px=round(float(np.percentile(dd, 95)), 1),
                       synth_px=CFG["parts"][n]["synth_px"], scale="1.000（等比，無縮放）")
    # 站姿與母版的色差（不含接縫線）：平均 RGB 差
    mrgb = master[..., :3].astype(int)
    rrgb = sub[..., :3].astype(int)
    inside = ndimage.binary_erosion(ma, iterations=14)
    diff = np.abs(mrgb - rrgb).max(-1)[inside]
    res = dict(iou_rest_vs_master=round(float(iou), 4), target=dict(iou=">=0.93", contour_p95="<=30 px"),
               rgb_maxdiff_le2_fraction=round(float((diff <= 2).mean()), 4),
               note="站姿與母版只差在部件之間的深色細接縫（2.5 px）與重畫的外輪廓白邊；所有部件縮放＝1.000。",
               parts=rows, scale_all_parts=1.0, pivots={k: [float(v[0]), float(v[1])] for k, v in PIV.items()},
               layers=LAYERS)
    # 疊圖
    cmp = Image.new("RGB", (W_ * 3 + 80, H_ + 170), (40, 40, 40))
    d = ImageDraw.Draw(cmp)
    f = font(26)
    bg = (150, 150, 146)

    def onbg(arr):
        b = Image.new("RGBA", (arr.shape[1], arr.shape[0]), bg + (255,))
        b.alpha_composite(Image.fromarray(arr, "RGBA"))
        return b.convert("RGB")
    mclean = master.copy()
    mclean[..., 3] = np.where(mclean[..., 3] < 24, 0, mclean[..., 3])
    cmp.paste(onbg(mclean), (20, 110))
    cmp.paste(onbg(sub), (W_ + 40, 110))
    ov = onbg(sub).convert("RGBA")
    edge_m = ma & ~ndimage.binary_erosion(ma, iterations=2)
    edge_r = ra & ~ndimage.binary_erosion(ra, iterations=2)
    o = np.array(ov)
    o[edge_m] = (255, 255, 255, 255)
    o[edge_r & ~edge_m] = (230, 60, 60, 255)
    cmp.paste(Image.fromarray(o).convert("RGB"), (2 * W_ + 60, 110))
    d.text((20, 14), "阿樂叔叔 kit_ale_v03：以母版直接切件的 12 個部件組回站姿 vs 正式母版 chr-ale_master_v02（6.15 頭身）", font=f, fill=(240, 240, 240))
    d.text((20, 60), "① 母版", font=f, fill=(240, 240, 240))
    d.text((W_ + 40, 60), "② rig 站姿（部件間深色細接縫；白邊只在外輪廓）", font=font(22), fill=(240, 240, 240))
    d.text((2 * W_ + 60, 60), f"③ 輪廓疊圖：白＝母版、紅＝rig｜IoU {iou:.4f}", font=font(22), fill=(240, 240, 240))
    worst = max(r["p95_px"] for r in rows.values())
    d.text((20, H_ + 125), f"全部部件等比 ×1.000（無非等比拉伸）；逐件輪廓誤差 95 百分位最大 {worst} px（目標 ≤30 px）；IoU 目標 ≥0.93",
           font=font(24), fill=(240, 220, 120))
    cmp.save(out_png)
    Path(out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def joint_gaps(pm, pt, pose_name):
    """關節處的白縫檢查：每個關節半徑＋12 px 範圍內，兩個相鄰部件聯集的「被包住的空洞」像素數。"""
    out = {}
    pairs = {"shoulder_r": ("torso", "upper_arm_r"), "elbow_r": ("upper_arm_r", "forearm_r"), "wrist_r": ("forearm_r", "hand_r"),
             "shoulder_l": ("torso", "upper_arm_l"), "elbow_l": ("upper_arm_l", "forearm_l"), "wrist_l": ("forearm_l", "hand_l"),
             "hip_r": ("torso", "thigh_r"), "knee_r": ("thigh_r", "shin_r"), "hip_l": ("torso", "thigh_l"), "knee_l": ("thigh_l", "shin_l")}
    for j, (a, b) in pairs.items():
        child = b
        c = pt(child, PIV[j])
        r = CFG["tab_radius"][j] + 12
        x0, y0 = int(c[0] - r), int(c[1] - r)
        win = (pm[a] | pm[b])[max(y0, 0):int(c[1] + r), max(x0, 0):int(c[0] + r)]
        yy, xx = np.mgrid[:win.shape[0], :win.shape[1]]
        circ = (xx + max(x0, 0) - c[0]) ** 2 + (yy + max(y0, 0) - c[1]) ** 2 <= (r - 12) ** 2
        holes = circ & ~win & ndimage.binary_fill_holes(win)
        # 關節圓內「兩件之間」的缺口：圓內不屬於任何一件、但被兩件夾住的像素
        out[j] = int(holes.sum())
    return out


def poses_sheet(out_png, out_json_update):
    rig = Rig(head="worried")
    shots = []
    info = {}
    for name, title in (("wave", "舉臂（想揮手）"), ("pulled", "受拉（腕被拉到旁邊、膝被提起）")):
        img, pt, _, pm = rig.render(POSES[name], outline=True, masks=True)
        info[name] = dict(pose=POSES[name], joint_hole_px=joint_gaps(pm, pt, name))
        shots.append((name, title, img, pt))
    # 版面：每個姿勢一欄全身（縮 0.42）＋ 4 個關節特寫（×1.0，原尺度）
    cells = []
    for name, title, img, pt in shots:
        bb = img.getbbox()
        body = img.crop(bb)
        sc = 760 / body.height
        body = body.resize((int(body.width * sc), 760), Image.LANCZOS)
        crops = []
        joints = ["shoulder_r", "elbow_r", "shoulder_l", "elbow_l"] if name == "wave" else ["shoulder_r", "elbow_r", "wrist_r", "knee_l"]
        for j in joints:
            child = {"shoulder_l": "upper_arm_l", "elbow_l": "forearm_l", "wrist_l": "hand_l", "shoulder_r": "upper_arm_r",
                     "elbow_r": "forearm_r", "wrist_r": "hand_r", "knee_r": "shin_r", "knee_l": "shin_l", "hip_r": "thigh_r"}[j]
            c = pt(child, PIV[j])
            box = (int(c[0] - 120), int(c[1] - 120), int(c[0] + 120), int(c[1] + 120))
            cr = Image.new("RGBA", (240, 240), (150, 150, 146, 255))
            cr.alpha_composite(img.crop(box))
            crops.append((j, cr.resize((300, 300), Image.LANCZOS)))
        cells.append((title, body, crops, info[name]["joint_hole_px"]))
    Wt = 40 + sum(max(b.width, 620) + 40 for _, b, _, _ in cells)
    sheet = Image.new("RGB", (Wt, 1580), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    d.text((20, 10), "kit_ale_v03 組裝特寫：上臂在軀幹後層，肩部舌片藏在軀幹的肩球後面不外露；肘、腕、膝以圓形舌片重疊", font=font(24), fill=(240, 240, 240))
    d.text((20, 42), "白色紙芯邊只在整體外輪廓，部件之間是深色細接縫；特寫為母版原尺度 ×1.25；「關節空洞」＝關節圓內兩件之間露出的空隙像素", font=font(18), fill=(210, 210, 210))
    x = 20
    zh = {"shoulder_l": "左肩", "elbow_l": "左肘", "wrist_l": "左腕", "shoulder_r": "右肩", "elbow_r": "右肘", "wrist_r": "右腕", "knee_r": "右膝", "knee_l": "左膝"}
    for title, body, crops, holes in cells:
        d.text((x, 70), title, font=font(26), fill=(240, 220, 120))
        bgc = Image.new("RGB", body.size, (150, 150, 146))
        bgc.paste(body, (0, 0), body)
        sheet.paste(bgc, (x, 108))
        cy = 890
        for i, (j, cr) in enumerate(crops):
            cx = x + (i % 2) * 320
            yy = cy + (i // 2) * 335
            sheet.paste(cr.convert("RGB"), (cx, yy))
            d.text((cx + 6, yy + 4), f"{zh[j]}｜關節空洞 {holes.get(j, 0)} px", font=font(18), fill=(20, 20, 20))
        x += max(body.width, 620) + 40
    sheet.save(out_png)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check"])
    ap.parse_args()
    res = assembly_check(ROOT / "review/G2/kit_ale_v03_assembly.png", ROOT / "review/G2/kit_ale_v03_assembly.json")
    info = poses_sheet(ROOT / "review/G2/kit_ale_v03_poses.png", None)
    res["poses"] = info
    res["worried_head"] = Rig(head="worried").head_info
    (ROOT / "review/G2/kit_ale_v03_assembly.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in ("iou_rest_vs_master", "rgb_maxdiff_le2_fraction")}, ensure_ascii=False))
    print(json.dumps({n: r["p95_px"] for n, r in res["parts"].items()}, ensure_ascii=False))
    print(json.dumps(info, ensure_ascii=False)[:800])
    print(res["worried_head"])


if __name__ == "__main__":
    main()
