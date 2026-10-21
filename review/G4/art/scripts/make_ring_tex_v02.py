"""G4 修正第 2 輪（美術，問題 8）：米白紙環貼圖 tex-string-ring_v02（取代灰色、像金屬墊圈的 v01）。

v01 的問題：淡灰環身＋白色「紙芯邊」＋外深內深兩圈灰線，在畫面上讀成金屬環／墊圈（中性灰、像高光）。
v02 畫法（128×128 透明，引擎 strings.ts 用 alphaTest 0.5、正對鏡頭、不旋轉，所以陰影方向固定）：
  - 環身：米白紙色 sRGB≈(251,242,222)（色相約 41°、彩度約 12%，是紙色不是中性灰），整片同色，不做放射漸層、不畫高光。
  - 紙紋：細纖維（±5）＋低頻斑駁（±3）；左下方一道紙帶接口（稍深的細線），讀得出是「紙條繞成的環」。
  - 描邊：外緣、內緣各一圈暖深棕細線（同紙偶整體描邊的顏色），中景約 0.8 px。
  - 單側陰影：整個環往右下偏移（5, 6）px 的暖棕色厚紙側邊／投影，只出現在環的右下外緣與孔內左上緣
    （alphaTest 不允許半透明陰影，所以用不透明的厚紙側邊色）。
  - 外半徑 0.88、孔半徑 0.42（以貼圖半寬 64 px 為 1），陰影延伸到約 1.0；中景直徑仍約 19 px。
輸出：
  assets/final/tex-string-ring_v02.png（打包 id tex-string-ring 不變，tools/pack.mjs 自動取 v02）
  review/G4/art/ring_crops_v02_preview.png：把 G4 擷取影格裡的舊紙環清掉、換上 v02（同中心、同直徑）的示意接觸表，
      上排＝擷取原圖（v01），下排＝換成 v02；×3 放大，排法同 review/G4/pack/capture/ring_crops.png
  review/G4/art/ring_tex_v02.json：v02 貼圖與示意圖的環身亮度、色相量測，以及舊擷取（v01）的同一量測
用法：
  /opt/anaconda3/bin/python3 review/G4/art/scripts/make_ring_tex_v02.py
  /opt/anaconda3/bin/python3 review/G4/art/scripts/make_ring_tex_v02.py --measure <擷取資料夾>
      （引擎重擷取後量實際畫面的環身：讀 <資料夾>/probe.json 與影格，輸出 <資料夾>/ring_body_stats.json）
"""
import argparse
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G4/art/scripts"))
import build_faces as BF  # noqa: E402

FIN = ROOT / "assets/final"
ART = ROOT / "review/G4/art"
CAP = ROOT / "review/G4/pack/capture"

PAPER = np.array([251, 242, 222], np.float32)    # 米白紙
OUTLINE = np.array([74, 52, 38], np.float32)     # 暖深棕描邊（同紙偶描邊色系）
SIDE = np.array([132, 106, 78], np.float32)      # 厚紙側邊／投影（暖棕）
SEAM = PAPER * 0.86
R_OUT, R_HOLE = 0.88, 0.42
W_OUT, W_IN = 0.065, 0.055
SHADOW = (5.0, 6.0)                              # 往右下（貼圖 px）
S = 128
SS = 4


def ring_texture_v02():
    s = S * SS
    yy, xx = np.mgrid[:s, :s].astype(np.float32)
    c = (s - 1) / 2
    half = s / 2

    def rad(dx=0.0, dy=0.0):
        return np.hypot(xx - c - dx * SS, yy - c - dy * SS) / half

    r = rad()
    rs = rad(*SHADOW)
    rgba = np.zeros((s, s, 4), np.float32)
    # 1) 厚紙側邊／投影（最底層）
    sh = (rs <= R_OUT) & (rs >= R_HOLE)
    rgba[sh, :3] = SIDE
    rgba[sh, 3] = 255
    # 2) 環（描邊＋紙面）
    ring = (r <= R_OUT) & (r >= R_HOLE)
    rgba[ring, :3] = OUTLINE
    rgba[ring, 3] = 255
    face = (r <= R_OUT - W_OUT) & (r >= R_HOLE + W_IN)
    rng = np.random.default_rng(42)
    fib = np.zeros((s, s), np.float32)
    ang = np.arctan2(yy - c, xx - c)
    for _ in range(260):                                      # 細纖維：短、方向大致沿圓周
        a0 = rng.uniform(-np.pi, np.pi)
        r0 = rng.uniform(R_HOLE, R_OUT) * half
        L = rng.uniform(6, 22) * SS / 2
        sgn = 1 if rng.random() < 0.5 else -1
        t_dir = a0 + np.pi / 2 + rng.normal(0, 0.45)
        x0, y0 = c + r0 * np.cos(a0), c + r0 * np.sin(a0)
        for t in np.linspace(-L / 2, L / 2, int(L)):
            xi, yi = int(x0 + np.cos(t_dir) * t), int(y0 + np.sin(t_dir) * t)
            if 0 <= xi < s and 0 <= yi < s:
                fib[yi, xi] += sgn
    fib = ndimage.gaussian_filter(fib, 1.1 * SS / 2)
    fib /= np.abs(fib).max() + 1e-6
    mott = ndimage.gaussian_filter(np.random.default_rng(7).standard_normal((s, s)), 5 * SS)
    mott /= mott.std() + 1e-6
    paper = PAPER[None, None, :] + fib[..., None] * 5 + mott[..., None] * 3
    rgba[face, :3] = paper[face]
    # 3) 紙帶接口：左下方一道細線（稍深），跨整個紙面寬
    seam_ang = np.deg2rad(140)          # 影像座標（y 向下）：140° ＝ 左下
    dang = np.abs((ang - seam_ang + np.pi) % (2 * np.pi) - np.pi)
    seam = face & (dang * r * half < 0.9 * SS)
    rgba[seam, :3] = SEAM
    out = rgba.reshape(S, SS, S, SS, 4).mean(axis=(1, 3))
    al = out[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~al, return_indices=True)
    out[~al, :3] = out[iy[~al], ix[~al], :3]
    return np.clip(out, 0, 255).astype(np.uint8)


def body_stats(rgb):
    """rgb: (N,3) 0–255 → 平均 sRGB、亮度（Rec.601 luma）、色相／彩度（HSV）"""
    m = rgb.reshape(-1, 3).astype(np.float32)
    mean = m.mean(0)
    h, s_, v = colorsys.rgb_to_hsv(*(mean / 255))
    return {"mean_srgb": [round(float(x), 1) for x in mean], "luma": round(float(BF.lum(mean[None])[0]), 1),
            "min_channel_mean": round(float(mean.min()), 1),
            "hue_deg": round(float(h) * 360, 1), "saturation": round(float(s_), 3), "n_px": int(len(m))}


def render_ring(tex, d, light=1.0):
    """模擬引擎：貼圖縮到直徑 d px（4× 超取樣、alpha 0.5 硬切），顏色 × light"""
    D4 = max(4, int(round(d * 4)))
    t = Image.fromarray(tex).resize((D4, D4), Image.BILINEAR)
    a = np.array(t, np.float32)
    hard = (a[..., 3] >= 128).astype(np.float32)
    col = np.clip(a[..., :3] * light, 0, 255)
    di = max(2, int(round(d)))
    k = D4 / di
    col_s = np.array(Image.fromarray(col.astype(np.uint8)).resize((di, di), Image.BOX), np.float32)
    al_s = np.array(Image.fromarray((hard * 255).astype(np.uint8)).resize((di, di), Image.BOX), np.float32) / 255
    return col_s, al_s


def swap_ring(frame, ring_px, R, rope_dir, width, tex):
    """擷取影格裡的舊紙環清掉（調和填補），把紙繩延到環內，再疊 v02。回傳整張影格（float）"""
    img = frame.astype(np.float32).copy()
    H, W = img.shape[:2]
    cx, cy = ring_px
    yy, xx = np.mgrid[:H, :W]
    disc = np.hypot(xx - cx, yy - cy) <= R * 1.08 + 0.8
    a = np.dstack([img.astype(np.uint8), np.full((H, W), 255, np.uint8)])
    filled = BF.harmonic_fill(a, disc, np.median(img[ndimage.binary_dilation(disc, iterations=3) & ~disc], 0), np.zeros((H, W), bool), iters=500)
    img = filled[..., :3].astype(np.float32)
    # 紙繩延長：在環外 1.25R 處取一條橫跨線寬的剖面，沿方向往環心複製到 0.78R
    dx, dy = rope_dir
    nx, ny = -dy, dx
    prof_pts = np.arange(-(width / 2 + 1.5), width / 2 + 1.6, 0.5)
    d0 = R * 1.25
    prof = []
    for sft in prof_pts:
        px, py = cx + dx * d0 + nx * sft, cy + dy * d0 + ny * sft
        prof.append(frame[int(round(py)) % H, int(round(px)) % W].astype(np.float32))
    prof = np.array(prof)
    for dd in np.arange(R * 0.78, R * 1.25, 0.5):
        for sft, col in zip(prof_pts, prof):
            px, py = int(round(cx + dx * dd + nx * sft)), int(round(cy + dy * dd + ny * sft))
            if 0 <= px < W and 0 <= py < H:
                img[py, px] = col
    col, al = render_ring(tex, 2 * R)
    di = col.shape[0]
    x0, y0 = int(round(cx - di / 2)), int(round(cy - di / 2))
    sub = img[y0:y0 + di, x0:x0 + di]
    img[y0:y0 + di, x0:x0 + di] = sub * (1 - al[..., None]) + col * al[..., None]
    return img


def band_pixels(img, ring_px, R, r0=0.57, r1=0.73, exclude_dir=None):
    """環身取樣：半徑 r0–r1（以 R＝貼圖半寬為 1），避開紙繩方向 ±25°"""
    H, W = img.shape[:2]
    cx, cy = ring_px
    yy, xx = np.mgrid[:H, :W]
    rr = np.hypot(xx - cx, yy - cy) / R
    m = (rr >= r0) & (rr <= r1)
    if exclude_dir is not None:
        ang = np.arctan2(yy - cy, xx - cx)
        a0 = np.arctan2(exclude_dir[1], exclude_dir[0])
        m &= np.abs((ang - a0 + np.pi) % (2 * np.pi) - np.pi) > np.deg2rad(25)
    return img[m]


def probe_rings(cap):
    data = json.loads((cap / "probe.json").read_text(encoding="utf-8"))
    for rec in data["probes"]:
        if not rec.get("frame") or rec.get("curtain", 1) < 0.95:
            continue
        key = rec.get("key") or ""
        if not (key in ("mid", "after", "probe", "before") or "after" in key):
            continue
        fp = cap / rec["frame"]
        if not fp.exists():
            continue
        for s in rec["strings"]:
            if s.get("visible") and s.get("ringPx") and s.get("ringRadiusPx"):
                yield rec, s, fp


def measure(cap):
    rows = []
    for rec, s, fp in probe_rings(cap):
        img = np.asarray(Image.open(fp).convert("RGB")).astype(np.float32)
        px = band_pixels(img, s["ringPx"], s["ringRadiusPx"], exclude_dir=s.get("dir"))
        rows.append(dict(cue=rec["cueId"], t=rec["t"], anchor=s["anchor"], **body_stats(px)))
    if not rows:
        return {"rows": []}
    lum = [r["luma"] for r in rows]
    sat = [r["saturation"] for r in rows]
    hue = [r["hue_deg"] for r in rows]
    return {"rule": "環身＝半徑 0.57–0.73（貼圖半寬為 1；v02 紙面在 0.475–0.815）、避開紙繩方向 ±25°；luma＝Rec.601；"
                    "通過條件（問題 8）：環身平均 sRGB ≥ 220（取 luma 與最小通道平均都看）、色相接近紙色（約 30–50°、彩度 ≥ 0.05），不是中性灰",
            "summary": {"n": len(rows), "luma_min": min(lum), "luma_median": float(np.median(lum)),
                        "hue_median": float(np.median(hue)), "sat_median": float(np.median(sat)), "sat_min": min(sat)},
            "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", type=Path)
    args = ap.parse_args()
    if args.measure:
        rep = measure(args.measure.resolve())
        (args.measure / "ring_body_stats.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
        print(json.dumps(rep.get("summary"), ensure_ascii=False))
        return
    tex = ring_texture_v02()
    Image.fromarray(tex, "RGBA").save(FIN / "tex-string-ring_v02.png", optimize=True)
    # 貼圖本身的量測
    yy, xx = np.mgrid[:S, :S]
    r = np.hypot(xx - (S - 1) / 2, yy - (S - 1) / 2) / (S / 2)
    facem = (r >= R_HOLE + W_IN + 0.02) & (r <= R_OUT - W_OUT - 0.02) & (tex[..., 3] > 250)
    stats = {"texture_face": body_stats(tex[facem][:, :3]),
             "texture_layout": {"外半徑": R_OUT, "孔半徑": R_HOLE, "外描邊寬": W_OUT, "內描邊寬": W_IN,
                                "陰影偏移_px": SHADOW, "紙色": PAPER.tolist(), "描邊色": OUTLINE.tolist(), "側邊陰影色": SIDE.tolist()}}
    # 舊擷取（v01）與換成 v02 的示意
    old_rows, new_rows, tiles = [], [], []
    for rec, s, fp in probe_rings(CAP):
        frame = np.asarray(Image.open(fp).convert("RGB"))
        R = s["ringRadiusPx"]
        cx, cy = s["ringPx"]
        old_rows.append(dict(cue=rec["cueId"], t=rec["t"], anchor=s["anchor"], **body_stats(band_pixels(frame.astype(np.float32), (cx, cy), R, exclude_dir=s.get("dir")))))
        new = swap_ring(frame, (cx, cy), R, s.get("dir", (0, -1)), s.get("widthPx", 8), tex)
        new_rows.append(dict(cue=rec["cueId"], t=rec["t"], anchor=s["anchor"], **body_stats(band_pixels(new, (cx, cy), R, exclude_dir=s.get("dir")))))
        box = (int(cx) - 48, int(cy) - 48, int(cx) + 48, int(cy) + 48)
        o = Image.fromarray(frame).crop(box).resize((288, 288), Image.NEAREST)
        n = Image.fromarray(np.clip(new, 0, 255).astype(np.uint8)).crop(box).resize((288, 288), Image.NEAREST)
        tiles.append((o, n, f"{rec['cueId']} {rec['t']:.2f}s {s['anchor']}"))
    stats["capture_v01_band"] = {"luma_median": float(np.median([r["luma"] for r in old_rows])),
                                 "sat_median": float(np.median([r["saturation"] for r in old_rows])),
                                 "hue_median": float(np.median([r["hue_deg"] for r in old_rows])), "rows": old_rows}
    stats["preview_v02_band"] = {"luma_median": float(np.median([r["luma"] for r in new_rows])), "luma_min": min(r["luma"] for r in new_rows),
                                 "sat_median": float(np.median([r["saturation"] for r in new_rows])),
                                 "hue_median": float(np.median([r["hue_deg"] for r in new_rows])), "rows": new_rows,
                                 "note": "示意：舊影格清掉舊環後以 light＝1.0 疊上 v02（引擎 strings.ts 會把顏色乘上 director.light，G4 全亮時約 1.0）。"
                                         "正式驗證要等引擎用 v02 重擷取 ring_crops.png，再跑本腳本 --measure。"}
    stats["light_note"] = "環身 luma 在 light 0.92 時仍 ≥ 220（貼圖 luma×0.92）" if stats["texture_face"]["luma"] * 0.92 >= 220 else "注意：light < 1 時環身可能低於 220"
    (ART / "ring_tex_v02.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    # 接觸表：每格上＝v01 擷取原圖、下＝換成 v02（示意）
    font = ImageFont.truetype(BF.FONT, 15, index=10)
    fbig = ImageFont.truetype(BF.FONT, 20, index=10)
    cols = 6
    cell = 288
    rows_n = (len(tiles) + cols - 1) // cols
    head = 330
    Wt = cols * cell
    Ht = head + rows_n * (2 * cell + 50)
    sheet = Image.new("RGB", (Wt, Ht), (24, 22, 20))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), "紙環 v02（米白紙環、紙紋、右下單側厚紙陰影；沒有金屬漸層或高光）——每格上＝G4 擷取原圖（v01 灰環）、下＝同中心同直徑換成 v02（示意）",
           font=fbig, fill=(240, 236, 226))
    pv = stats["preview_v02_band"]
    d.text((10, 36), f"環身量測（半徑 0.57–0.73、避開紙繩）：v01 擷取 luma 中位數 {stats['capture_v01_band']['luma_median']:.0f}、彩度 {stats['capture_v01_band']['sat_median']:.3f}（中性灰）"
                     f"｜v02 示意 luma 中位數 {pv['luma_median']:.0f}（最低 {pv['luma_min']:.0f}）、色相 {pv['hue_median']:.0f}°、彩度 {pv['sat_median']:.3f}",
           font=font, fill=(240, 210, 120))
    # 貼圖放大（米色底、工作褲底、皮膚底）
    x = 10
    for bgc in ((236, 226, 213), (119, 89, 53), (252, 167, 95)):
        b = Image.new("RGBA", (256, 256), bgc + (255,))
        b.alpha_composite(Image.fromarray(tex).resize((256, 256), Image.NEAREST))
        sheet.paste(b.convert("RGB"), (x, 64))
        x += 266
    d.text((x + 10, 80), "貼圖 128 px ×2\n（左起：後牆色、工作褲色、皮膚色底）", font=font, fill=(220, 220, 220))
    for i, (o, n, lab) in enumerate(tiles):
        cx_, cy_ = (i % cols) * cell, head + (i // cols) * (2 * cell + 50)
        sheet.paste(o, (cx_, cy_))
        sheet.paste(n, (cx_, cy_ + cell + 4))
        d.text((cx_ + 4, cy_ + 2 * cell + 8), lab + "（上 v01／下 v02）", font=font, fill=(230, 226, 218))
    sheet.save(ART / "ring_crops_v02_preview.png")
    print(json.dumps({k: v for k, v in stats.items() if k in ("texture_face", "light_note")}, ensure_ascii=False))
    print("v01 band", {k: v for k, v in stats["capture_v01_band"].items() if k != "rows"})
    print("v02 band", {k: v for k, v in stats["preview_v02_band"].items() if k not in ("rows", "note")})


if __name__ == "__main__":
    main()
