"""阿樂叔叔分件紙偶 v03：直接以正式母版 chr-ale_master_v02.png 切件（G2 第 2 輪重驗意見 3、26、29）。

做法（不重新生成、不做任何非等比縮放）：
1. 母版每個像素只分給一個部件（多邊形＋顏色分類；頭部用色彩分割沿衣領切開），所以站姿組回來和母版逐像素相同。
2. 去掉母版的外輪廓白邊與外側深色細線（距外輪廓 ≤12 px；以及手臂與身體之間的內側白邊缺口），
   只保留每件自己的深色內描線。白色紙芯邊改在擺好姿勢後，沿「整體外輪廓」重畫（rig_ale_v03.py）。
3. 關節舌片：只補在「站姿時被前一層蓋住」的地方（不改站姿外觀）：
   - 上臂在軀幹後層：肩部圓形舌片（以肩關節為圓心）藏在軀幹後面；遠側（左）上臂在軀幹後面補足到完整臂寬。
   - 肘：前臂（含袖口反摺）在上臂前面，上臂下端補一個以肘關節為圓心的圓形舌片，藏在袖口後。
   - 腕：手在前臂前面，前臂下端補圓形舌片藏在手後。
   - 髖：大腿在圍裙（軀幹）後面，上端補到髖關節圓心的圓形舌片；膝：大腿在小腿前面，大腿下端是以膝關節為圓心的半圓，
     小腿上端補圓形舌片藏在大腿後。
   - 頭在軀幹後面，頸部舌片藏在衣領裡。
   補出的像素以同一部件最近的布面顏色延伸＋紙纖維雜訊。
4. 部件之間的切邊（站姿時看得到的那一側）畫 2.5 px 深色細接縫；母版原有的外輪廓深色線不重複加粗。

輸出：assets/parts/ale_v03/<部件>.png（母版畫布座標、同尺寸 1024×1656，可直接疊回）、parts.json（關節、半徑、層序、
來源像素數與補出像素數）、review/G2/kit_ale_v03_parts_sheet.png（部件表）、review/G2/kit_ale_v03_cutmap.png（切件分配圖）。
由 tools/split_parts.py --layout master_v03 呼叫。
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets/generated/chr-ale_master_v02.png"
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)
LINE = (84, 75, 67)          # 母版深色內描線顏色（中位數）
BORDER_STRIP = 12.5          # 母版外輪廓：外側深色細線 1–2 px＋白色紙芯邊約 10 px

# 關節（母版像素；人工在 10 px 格線放大圖上點選，對照 review/G2/kit_ale_v03_cutmap.png）
PIV = dict(neck=(530, 330), shoulder_r=(335, 425), elbow_r=(305, 655), wrist_r=(306, 840),
           shoulder_l=(664, 425), elbow_l=(694, 652), wrist_l=(718, 850),
           hip_r=(425, 1000), knee_r=(420, 1255), hip_l=(595, 1000), knee_l=(597, 1255))
RAD = dict(shoulder_r=60, elbow_r=68, wrist_r=40, shoulder_l=50, elbow_l=56, wrist_l=36,
           hip_r=78, hip_l=78, knee_r=64, knee_l=64)

BALL = dict(r=50, l=28)       # 軀幹肩球半徑（到母版布面外緣為止，站姿外觀不變）
# 層序（由後往前）：上臂、大腿、頭在軀幹後；前臂與手在軀幹前；大腿壓小腿
LAYERS = ["shin_l", "thigh_l", "shin_r", "thigh_r", "upper_arm_l", "head", "upper_arm_r", "torso",
          "forearm_l", "hand_l", "forearm_r", "hand_r"]
PARENT = {"torso": None, "head": "torso", "upper_arm_r": "torso", "forearm_r": "upper_arm_r", "hand_r": "forearm_r",
          "upper_arm_l": "torso", "forearm_l": "upper_arm_l", "hand_l": "forearm_l",
          "thigh_r": "torso", "shin_r": "thigh_r", "thigh_l": "torso", "shin_l": "thigh_l"}
JOINT = {"head": "neck", "upper_arm_r": "shoulder_r", "forearm_r": "elbow_r", "hand_r": "wrist_r",
         "upper_arm_l": "shoulder_l", "forearm_l": "elbow_l", "hand_l": "wrist_l",
         "thigh_r": "hip_r", "shin_r": "knee_r", "thigh_l": "hip_l", "shin_l": "knee_l"}
ZH = {"head": "頭（含頸部舌片）", "torso": "軀幹＋圍裙", "upper_arm_r": "右上臂", "upper_arm_l": "左上臂",
      "forearm_r": "右前臂（含袖口）", "forearm_l": "左前臂（含袖口）", "hand_r": "右手", "hand_l": "左手",
      "thigh_r": "右大腿", "thigh_l": "左大腿", "shin_r": "右小腿含鞋", "shin_l": "左小腿含鞋"}

# 可見區分配多邊形（母版像素；外側刻意畫寬，最後與母版 alpha 取交集）
POLY = {
    "upper_arm_r": [(170, 330), (282, 384), (300, 372), (315, 367), (330, 366), (345, 370), (360, 379), (373, 394),
                    (385, 417), (392, 440), (396, 470), (398, 520), (394, 570), (387, 608), (382, 630), (345, 624),
                    (300, 619), (240, 617), (170, 617)],
    "forearm_r": [(170, 617), (240, 617), (300, 619), (345, 624), (382, 630), (386, 700), (353, 708), (351, 838),
                  (170, 838)],
    "hand_r": [(170, 838), (351, 838), (368, 880), (372, 990), (170, 990)],
    "upper_arm_l": [(627, 330), (637, 363), (647, 390), (655, 417), (663, 440), (667, 470), (668, 520), (670, 570),
                    (675, 622), (700, 615), (745, 612), (830, 612), (830, 330)],
    "forearm_l": [(675, 622), (700, 615), (745, 612), (830, 612), (830, 848), (686, 848), (676, 780), (665, 700),
                  (640, 692), (638, 640)],
    "hand_l": [(686, 848), (830, 848), (830, 990), (680, 990), (680, 900)],
}
# 只在「站姿被前一層蓋住」的地方補出的區域（再與允許遮罩取交集）
TORSO_SIDE = {
    "r": [(378, 618), (450, 618), (450, 1040), (348, 1040), (351, 830), (358, 700)],
    "l": [(560, 612), (677, 612), (670, 700), (667, 850), (668, 1040), (560, 1040)],
}
NECK_TAB = [(470, 285), (600, 285), (610, 425), (465, 425)]
# 補色用布紋貼片（母版上平整、沒有摺線的區塊；鏡射平鋪）
PATCH = {"sleeve": (282, 440, 340, 560), "skin": (285, 715, 335, 800), "navy": (450, 955, 560, 1005), "olive": (385, 1080, 450, 1200)}
# 各部件補出區要用哪一種布紋；軀幹依高度分區：腰帶以上＝襯衫、腰帶＝深藍、腰帶以下（圍裙兩側的褲腰）＝橄欖褐
SYN_TEX = {"head": "skin", "upper_arm_r": "sleeve", "upper_arm_l": "sleeve", "forearm_r": "skin", "forearm_l": "skin",
           "hand_r": "skin", "hand_l": "skin", "thigh_r": "olive", "thigh_l": "olive", "shin_r": "olive", "shin_l": "olive"}
TIE_ROWS = (668, 708)


def tiled(patch, shape):
    """鏡射平鋪布紋（接縫不跳色）。"""
    ph, pw = patch.shape[:2]
    big = np.concatenate([patch, patch[::-1]], 0)
    big = np.concatenate([big, big[:, ::-1]], 1)
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    return big[yy % (2 * ph), xx % (2 * pw)]


def font(px):
    try:
        return ImageFont.truetype(FONT[0], px, index=FONT[1])
    except OSError:
        return ImageFont.load_default()


def poly_mask(pts, shape):
    im = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=255)
    return np.array(im) > 0


def disk(c, r, shape):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r


def hsv(rgb):
    a = rgb.astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, (mx - mn) / (mx + 1e-6), mx


def shaft(p, q, half_w, shape):
    p, q = np.array(p, float), np.array(q, float)
    t = (q - p) / np.linalg.norm(q - p)
    n = np.array([-t[1], t[0]])
    pts = [p + n * half_w, q + n * half_w, q - n * half_w, p - n * half_w]
    return poly_mask(pts, shape)


def cut(master=MASTER, out_dir=ROOT / "assets/parts/ale_v03", sheet=ROOT / "review/G2/kit_ale_v03_parts_sheet.png",
        cutmap=ROOT / "review/G2/kit_ale_v03_cutmap.png"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    arr = np.array(Image.open(master).convert("RGBA"))
    H, W = arr.shape[:2]
    shape = (H, W)
    rgb = arr[..., :3]
    alpha = np.where(arr[..., 3] < 24, 0, arr[..., 3])
    core = alpha > 128
    core = ndimage.binary_fill_holes(core) & (alpha > 0) | core
    d_out = ndimage.distance_transform_edt(core)
    h, s, v = hsv(rgb)
    mn = rgb.min(-1).astype(int)
    outer_strip = core & (d_out <= BORDER_STRIP)
    # 內側白邊（手臂與身體之間的缺口）：和外輪廓白邊「相連」的淺色低彩度像素；不相連的內部亮點（袖子受光條紋）不動
    wcand = core & (mn >= 196) & ((rgb.max(-1).astype(int) - mn) <= 50) & (d_out <= 90)
    lbw, _ = ndimage.label(wcand | outer_strip)
    touch = np.unique(lbw[outer_strip & (d_out >= 2)])
    inner_white = np.isin(lbw, touch[touch > 0]) & wcand & ~outer_strip
    strip = outer_strip | inner_white
    # 內側白邊兩側各有一條外側深色細線：一併去掉 1 px
    strip |= ndimage.binary_dilation(inner_white, iterations=1) & core & (v < 0.45)
    body = core & ~strip
    navy = (h >= 200) & (h <= 250) & (s > 0.25) & (v > 0.12)
    shirt = (h >= 18) & (h <= 50) & (s >= 0.06) & (s <= 0.34) & (v > 0.70)

    owner = np.full(shape, "", dtype=object)
    lab = np.full(shape, -1, np.int16)
    names = LAYERS
    idx = {n: i for i, n in enumerate(names)}

    def assign(name, m):
        m = m & body & (lab < 0)
        lab[m] = idx[name]

    skin = (h >= 8) & (h <= 38) & (s > 0.33) & (v > 0.45)
    # 手 → 前臂 → 上臂（避開深藍圍裙像素；多邊形外 14 px 內的膚色也歸手臂，避免軀幹殘留皮膚）
    for side in ("r", "l"):
        for part in (f"hand_{side}", f"forearm_{side}"):
            pm = poly_mask(POLY[part], shape)
            near = ndimage.binary_dilation(pm, iterations=14) & skin
            if part.startswith("forearm"):
                near &= poly_mask([(0, 690), (W, 690), (W, 850), (0, 850)], shape)
            assign(part, (pm & ~navy) | near)
        # 肩：袖山（關節以上）與以肩關節為圓心的「肩球」歸軀幹（軀幹在前層），上臂從肩球下面轉出來，舉臂時肩線不缺角
        px_, py_ = PIV[f"shoulder_{side}"]
        cap = poly_mask([(0, 0), (W, 0), (W, py_), (0, py_)], shape) | disk((px_, py_), BALL[side], shape)
        assign(f"upper_arm_{side}", poly_mask(POLY[f"upper_arm_{side}"], shape) & ~navy & ~cap)
    # 頭：y<400 內「非襯衫、非深藍」且與臉部相連的區域
    yy, xx = np.mgrid[:H, :W]
    cand = body & (yy < 398) & ~shirt & ~navy & (lab < 0)
    lb, n = ndimage.label(cand)
    k = lb[200, 540]
    headm = lb == k
    headm = ndimage.binary_fill_holes(headm) & body & (lab < 0)
    headm = ndimage.binary_opening(headm, iterations=1)
    headm |= ndimage.binary_dilation(headm, iterations=3) & cand & (d_out <= 18)   # 補回外緣深色內描線
    assign("head", headm)
    # 腿：圍裙下襬以下（逐欄找最後一個深藍像素）
    hem = np.full(W, 1032)
    for x in range(320, 730):
        col = np.nonzero(navy[930:1080, x])[0]
        if len(col):
            hem[x] = 930 + col.max() + 3
    below = yy > hem[None, :]
    leg_r = below & (xx < 510)
    leg_l = below & (xx >= 510)
    for side, legm in (("r", leg_r), ("l", leg_l)):
        kx, ky = PIV[f"knee_{side}"]
        thigh = legm & ((yy < ky) | disk((kx, ky), RAD[f"knee_{side}"], shape))
        assign(f"thigh_{side}", thigh)
        assign(f"shin_{side}", legm)
    assign("torso", body)

    # ---------------- 全形（含舌片）與補色
    def front_of(name):
        return set(names[idx[name] + 1:])

    tabs = {
        "upper_arm_r": [(disk(PIV["shoulder_r"], RAD["shoulder_r"], shape), {"torso"}),
                        (disk(PIV["elbow_r"], RAD["elbow_r"], shape), {"forearm_r", "hand_r"})],
        "upper_arm_l": [(disk(PIV["shoulder_l"], RAD["shoulder_l"], shape) | shaft(PIV["shoulder_l"], PIV["elbow_l"], 50, shape),
                         {"torso"}),
                        (disk(PIV["elbow_l"], RAD["elbow_l"], shape), {"forearm_l", "hand_l", "torso"})],
        "forearm_r": [(disk(PIV["wrist_r"], RAD["wrist_r"], shape), {"hand_r"})],
        "forearm_l": [(disk(PIV["wrist_l"], RAD["wrist_l"], shape), {"hand_l"})],
        # 頸部舌片離整體外輪廓 ≥16 px（頭轉 ±6° 也不會從肩線露出）
        "head": [(poly_mask(NECK_TAB, shape) & (d_out > 16 + BORDER_STRIP), {"torso"})],
        "torso": [(poly_mask(TORSO_SIDE["r"], shape), {"forearm_r", "hand_r", "_notch"}),
                  (poly_mask(TORSO_SIDE["l"], shape), {"forearm_l", "hand_l", "_notch"})],
    }
    for side in ("r", "l"):
        hx, hy = PIV[f"hip_{side}"]
        rr = RAD[f"hip_{side}"]
        top = disk((hx, hy), rr, shape) | (poly_mask([(hx - 75, hy), (hx + 75, hy), (hx + 75, 1045), (hx - 75, 1045)], shape))
        tabs[f"thigh_{side}"] = [(top, {"torso"})]
        tabs[f"shin_{side}"] = [(disk(PIV[f"knee_{side}"], RAD[f"knee_{side}"], shape), {f"thigh_{side}"})]

    parts, report = {}, {}
    final_lab = np.full(shape, 255, np.uint8)
    rng = np.random.default_rng(11)
    grain = ndimage.gaussian_filter(rng.normal(0, 1, shape), 0.8) * 3.0
    for name in names:
        own = lab == idx[name]
        full = own.copy()
        for region, allowed in tabs.get(name, []):
            # 補出的區域只允許落在「站姿時被前層蓋住」的像素（allowed 必須都在本件前面）
            front = [idx[a] for a in allowed if a in front_of(name)]
            okm = np.isin(lab, front)
            if "_notch" in allowed:          # 手臂與軀幹之間的內側白邊缺口：手臂移開後由軀幹側邊補滿
                okm |= inner_white | (strip & ~outer_strip)
            full |= region & okm
        own = ndimage.binary_opening(own, iterations=1)               # 去掉白邊缺口旁殘留的細線
        full = ndimage.binary_opening(full, iterations=1) | own
        yy0, xx0 = np.ogrid[-3:4, -3:4]
        full |= ndimage.binary_closing(full, structure=(xx0 ** 2 + yy0 ** 2 <= 9)) & core   # 修平切口的小缺角
        lbf, nf = ndimage.label(full)                                  # 去掉小碎片（<60 px）
        if nf > 1:
            sizes = ndimage.sum(full, lbf, range(1, nf + 1))
            full = np.isin(lbf, [i + 1 for i, s_ in enumerate(sizes) if s_ >= 60])
            own &= full
        syn = full & ~own
        final_lab[own] = idx[name]
        out = np.zeros((H, W, 4), np.uint8)
        out[own, :3] = rgb[own]
        if syn.any() and name in SYN_TEX or (syn.any() and name == "torso"):
            texs = {k: tiled(rgb[b[1]:b[3], b[0]:b[2]].astype(np.float32), shape) for k, b in PATCH.items()}
            if name == "torso":
                fill = np.where((yy < TIE_ROWS[0])[..., None], texs["sleeve"],
                                np.where((yy < TIE_ROWS[1])[..., None], texs["navy"], texs["olive"]))
            else:
                fill = texs[SYN_TEX[name]]
            fill = fill + grain[..., None] * 0.5
            out[syn, :3] = np.clip(fill[syn], 0, 255).astype(np.uint8)
        elif syn.any():
            lum = rgb.astype(np.float32).mean(-1)
            med = np.median(lum[own])
            src = own & (lum > med * 0.72) & (lum < 250)
            for it in (5, 3, 1):
                e = ndimage.binary_erosion(src, iterations=it)
                if e.sum() > 400:
                    src = e
                    break
            _, (iy, ix) = ndimage.distance_transform_edt(~src, return_indices=True)
            # 鏡射延伸：補出點 p 以最近的布面像素 q 為鏡心取 2q−p（保留布紋，不拉出條紋）；鏡射點不在布面上時才用 q
            ry, rx = 2 * iy - yy, 2 * ix - xx
            okr = (ry >= 0) & (ry < H) & (rx >= 0) & (rx < W)
            ry, rx = np.clip(ry, 0, H - 1), np.clip(rx, 0, W - 1)
            okr &= src[ry, rx]
            fill = np.where(okr[..., None], rgb[ry, rx], rgb[iy, ix]).astype(np.float32)
            m = syn.astype(np.float32)
            for c in range(3):
                num = ndimage.gaussian_filter(fill[..., c] * m, 1.0)
                den = ndimage.gaussian_filter(m, 1.0) + 1e-6
                fill[..., c] = np.where(syn, num / den, fill[..., c])
            fill += grain[..., None] * 0.6
            out[syn, :3] = np.clip(fill[syn], 0, 255).astype(np.uint8)
        out[full, 3] = 255
        # 接縫：全形邊界內側 2.5 px，跳過母版外輪廓（已有深色線）與內側白邊處
        er = ndimage.distance_transform_edt(full)
        band = full & (er <= 2.5)
        d_edge = ndimage.distance_transform_edt(body)          # 到「母版外輪廓或內側白邊」的距離
        seam = band & (d_edge > 3.5)
        out[seam, :3] = (np.array(LINE) * 0.85 + out[seam, :3] * 0.15).astype(np.uint8)
        Image.fromarray(out, "RGBA").save(out_dir / f"{name}.png")
        parts[name] = out
        ys, xs = np.nonzero(full)
        report[name] = dict(zh=ZH[name], file=f"{name}.png", bbox=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                            source_px=int(own.sum()), synth_px=int(syn.sum()), seam_px=int(seam.sum()),
                            parent=PARENT[name], joint=JOINT.get(name), pivot=list(PIV[JOINT[name]]) if name in JOINT else None,
                            tab_radius=RAD.get(JOINT.get(name, ""), None))
    manifest = dict(source=str(Path(master).relative_to(ROOT)), canvas=[W, H], method="以正式母版直接切件（逐像素分配＋關節舌片補色），無縮放",
                    border_strip_px=BORDER_STRIP, line_rgb=list(LINE), pivots=PIV, tab_radius=RAD, layers=LAYERS,
                    convention="左／右＝角色自身的左右（右側在畫面左邊）", parts=report,
                    master_core_px=int(core.sum()), stripped_border_px=int(strip.sum()),
                    unassigned_body_px=int((body & (lab < 0)).sum()))
    (out_dir / "parts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    Image.fromarray(final_lab, "L").save(out_dir / "_labels.png")   # 母版像素分配（量測用）
    _cutmap(arr, lab, strip, cutmap)
    _sheet(parts, report, sheet)
    return manifest


PAL = [(230, 60, 60), (40, 150, 230), (240, 170, 20), (60, 180, 90), (170, 80, 220), (20, 190, 190),
       (250, 110, 180), (120, 120, 250), (200, 200, 60), (255, 140, 60), (90, 220, 140), (180, 120, 80)]


def _cutmap(arr, lab, strip, path):
    H, W = lab.shape
    base = Image.new("RGBA", (W, H), (60, 60, 60, 255))
    base.alpha_composite(Image.fromarray(arr))
    ov = np.zeros((H, W, 4), np.uint8)
    for i, n in enumerate(LAYERS):
        ov[lab == i] = PAL[i] + (110,)
    ov[strip] = (255, 255, 255, 160)
    base.alpha_composite(Image.fromarray(ov, "RGBA"))
    d = ImageDraw.Draw(base)
    f = font(22)
    for n, (x, y) in PIV.items():
        d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 255, 0, 255), width=3)
        r = RAD.get(n)
        if r:
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 0, 200), width=1)
    for i, n in enumerate(LAYERS):
        ys, xs = np.nonzero(lab == i)
        if len(xs):
            d.text((int(xs.mean()) - 30, int(ys.mean())), ZH[n].split("（")[0], font=f, fill=(255, 255, 255, 255),
                   stroke_width=2, stroke_fill=(0, 0, 0, 255))
    W2 = W + 40
    sheet = Image.new("RGB", (W2, H + 70), (40, 40, 40))
    sheet.paste(base.convert("RGB"), (20, 60))
    ImageDraw.Draw(sheet).text((20, 14), "kit_ale_v03 切件分配圖：母版每個像素只屬於一個部件；白色＝去掉的外輪廓白邊；黃圈＝關節與舌片半徑",
                               font=font(22), fill=(240, 240, 240))
    sheet.save(path)


def _sheet(parts, report, path):
    order = [["head", "torso", "upper_arm_r", "upper_arm_l"], ["forearm_r", "forearm_l", "hand_r", "hand_l"],
             ["thigh_r", "thigh_l", "shin_r", "shin_l"]]
    crops = {}
    for n, a in parts.items():
        x0, y0, x1, y1 = report[n]["bbox"]
        crops[n] = Image.fromarray(a[max(y0 - 6, 0):y1 + 6, max(x0 - 6, 0):x1 + 6], "RGBA")
    pad = 30
    rows = []
    for r in order:
        w = sum(crops[n].width for n in r) + pad * (len(r) + 1)
        hgt = max(crops[n].height for n in r) + 70
        rows.append((r, w, hgt))
    Wt = max(w for _, w, _ in rows)
    Ht = sum(hh for _, _, hh in rows) + 80
    sheet = Image.new("RGB", (Wt, Ht), (150, 150, 146))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 12), "阿樂叔叔 kit_ale_v03：以正式母版 chr-ale_master_v02 直接切件（12 件，母版原尺度、無任何縮放）", font=font(24), fill=(20, 20, 20))
    d.text((pad, 44), "部件本身不帶白邊；部件間為深色細接縫，白色紙芯邊在組裝後沿整體外輪廓重畫。「補」＝只在站姿被前層蓋住處補出的舌片像素。",
           font=font(18), fill=(40, 40, 40))
    y = 80
    for r, w, hgt in rows:
        x = pad
        for n in r:
            c = crops[n]
            sheet.paste(c, (x, y + 40), c)
            rep = report[n]
            d.text((x, y + 4), f"{ZH[n]}", font=font(22), fill=(20, 20, 20))
            d.text((x, y + 40 + c.height + 2), f"補 {rep['synth_px']} px", font=font(16), fill=(50, 50, 50))
            x += c.width + pad
        y += hgt
    sheet.save(path)


if __name__ == "__main__":
    m = cut()
    print(json.dumps({k: (v["source_px"], v["synth_px"]) for k, v in m["parts"].items()}, ensure_ascii=False))
    print("unassigned", m["unassigned_body_px"])
