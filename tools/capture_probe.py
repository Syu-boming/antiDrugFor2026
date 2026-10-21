"""擷取量測（tools/capture.mjs --probe 會自動呼叫）：操偶線線寬與明度差、紙環位置、兒童站位背景亮度。

用法：/opt/anaconda3/bin/python3 tools/capture_probe.py <擷取資料夾>

量什麼：
1. 操偶線線寬（px，1080p 繪圖緩衝）：劇場程式回報的螢幕線寬（垂直於線的方向）。規格（G4 修正第 22 項）：中景 6–10 px。
   G5 修正第 1 輪起 widthPx＝實際畫出的紙帶寬（紙環上方那段紙帶兩側頂點的螢幕距離、垂直於線的分量，程式的 widthTruePx）；
   舊量法（水平投影寬 × |cos|，線斜時偏小）另列 widthPxLegacy。G5 規格（主線裁定 5）：中景 ≥ 8 px、遠景 ≥ 6–7 px。
2. 操偶線與相鄰處的明度差 ΔL*（CIELAB）：沿線在紙環上方 14–60 px 取樣，線兩側緊鄰（線寬一半＋3 px 外）的像素當背景；
   - 繩身 ΔL*：線中心像素 vs 背景；深灰邊 ΔL*：線內側距邊 1 px 的像素 vs 同一側的背景；兩側取較小者，再取沿線中位數。
   - 判定用 ΔL*：每一側取「繩身或該側深灰邊對該側背景」的較大者（看得出那一側的界線），再取兩側較小者
     （G4 修正第 22 項後繩身改淡灰 sRGB≈178，對淺牆的可讀性由兩側深灰邊提供；判定方式的改變要主線確認，繩身與深灰邊也分開列出）。原圖與投影 v2 模擬（彩度 ×0.65、黑位 0.18、白位 0.87）各算一次。
   規格（劇本 L1 投影可讀性）：ΔL* ≥ 25，投影模擬後 ≥ 15。
3. 紙環中心是否落在角色剪影內（G4 修正第 23 項）與環身顏色（G4 修正第 2 輪第 8 項：米白紙環，亮度 ≥ 220、色相接近紙色）：紙環中間是透明的，紙環中心看到的是肢體（在剪影內）或背景（在剪影外）；
   用同一格隱藏角色後的背景（probe_bg/）比對紙環中心 5×5 的像素差（最大通道差的中位數 > 18 算在剪影內）。
   另外輸出紙環 1:1 放大裁切（ring_crops/、ring_crops.png）與一段紙繩 1:1 放大（看得到扭紋與纖維）。
4. 兒童站位背景亮度：同一格隱藏角色後重畫（probe_bg/），在每個兒童外框的軀幹帶（寬 50%、高 30–75%）量 WCAG 相對亮度，
   套投影 v2 模擬後取中位數與第 10 百分位。規格（D-G2-06）：≥ 0.50。開幕立起過程另外以 --probe-times 加密量測；
   upright＝外框高度 ÷ 該角色在整個擷取中的最大外框高度（立起程度）。
5. 換景漸暗中、題卡蓋住舞台的格（G5 修正第 1 輪）：capture.mjs 在每筆量測記下 world.dim（換景漸暗 0＝正常、1＝全暗）與
   world.quizVisible（DOM 題卡）；dim > 0.05 或題卡 > 0.5 的格不量兒童身後亮度、也不量操偶線 ΔL*（畫面是暗的或被題卡蓋住，
   數字沒有意義；列 dim、quiz 值與 excluded_dim）。
輸出：probe_report.json，並在終端機印摘要。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJ = (0.65, 0.18, 0.87)
# 換景漸暗（world.dim）超過這個值的格不量兒童背景與線的 ΔL*
DIM_MAX = 0.05


def to_linear(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def projector(rgb):
    sat, lo, hi = PROJ
    a = rgb.astype(np.float32) / 255.0
    g = a.mean(axis=-1, keepdims=True)
    a = g + (a - g) * sat
    a = lo + a * (hi - lo)
    return np.clip(a, 0, 1) * 255


def luminance(rgb):
    a = to_linear(np.asarray(rgb, dtype=np.float32) / 255.0)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def lstar(rgb):
    y = luminance(rgb)
    return np.where(y > 216 / 24389, 116 * np.cbrt(y) - 16, (24389 / 27) * y)


def sample(img, x, y):
    h, w = img.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < w and 0 <= yi < h:
        return img[yi, xi].astype(np.float32)
    return None


def _l(px):
    return float(lstar(px[None, :3])[0])


def along_path(s, d):
    """沿線（從線的下端往上）走 d px 的位置與方向：有 path（引擎實際畫的中心線）就沿折線走，否則沿 dir 直線"""
    ax, ay = s["anchorPx"]
    path = s.get("path")
    if path and len(path) >= 3:
        pts = [tuple(p) for p in reversed(path)]  # 下端 → 上端
        acc = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = float(np.hypot(x1 - x0, y1 - y0))
            if seg < 1e-6:
                continue
            if acc + seg >= d:
                u = (d - acc) / seg
                return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, (x1 - x0) / seg, (y1 - y0) / seg
            acc += seg
    dx, dy = s["dir"]
    return ax + dx * d, ay + dy * d, dx, dy


def string_contrast(img, proj, s):
    """回傳沿線中位數：繩身 ΔL*、深灰邊 ΔL*、best（每一側取繩身或深灰邊較大者，再取兩側較小者）；各含投影 v2。
    取樣點沿引擎回報的中心線（path，線鬆時是彎的）走，不沿直線。"""
    w = max(2.0, s.get("widthTruePx") or s["widthPx"])
    acc = {"body": [], "edge": [], "body_p": [], "edge_p": [], "best": [], "best_p": []}
    for d in range(14, 61, 3):
        cx, cy, dx, dy = along_path(s, d)
        nx, ny = -dy, dx
        vals = {"body": [], "edge": [], "body_p": [], "edge_p": [], "best": [], "best_p": []}
        ok = True
        for src, suf in ((img, ""), (proj, "_p")):
            c = sample(src, cx, cy)
            if c is None:
                ok = False
                break
            for sgn in (-1, 1):
                bgp = sample(src, cx + nx * (w / 2 + 3) * sgn, cy + ny * (w / 2 + 3) * sgn)
                ed = sample(src, cx + nx * max(0.5, w / 2 - 1.0) * sgn, cy + ny * max(0.5, w / 2 - 1.0) * sgn)
                if bgp is None or ed is None:
                    ok = False
                    break
                b_, e_ = abs(_l(c) - _l(bgp)), abs(_l(ed) - _l(bgp))
                vals["body" + suf].append(b_)
                vals["edge" + suf].append(e_)
                # 這一側看得出線的界線＝繩身或該側深灰邊對該側背景的較大者
                vals[("best" + suf) if suf else "best"].append(max(b_, e_))
        if not ok:
            continue
        for k in acc:
            acc[k].append(min(vals[k]))
    if not acc["body"]:
        return None
    return {k: float(np.median(v)) for k, v in acc.items()}


def ring_inside(img, bg, ring):
    """紙環中心 5×5 與背景的最大通道差中位數；> 18 算在角色剪影內"""
    x, y = int(round(ring[0])), int(round(ring[1]))
    h, w = img.shape[:2]
    if not (2 <= x < w - 2 and 2 <= y < h - 2):
        return None, False
    a = img[y - 2:y + 3, x - 2:x + 3].astype(np.int16)
    b = bg[y - 2:y + 3, x - 2:x + 3].astype(np.int16)
    dv = float(np.median(np.abs(a - b).max(axis=-1)))
    return round(dv, 1), dv > 18


def ring_body(img, ring, R, rope_dir=None, r0=0.57, r1=0.73):
    """紙環環身取樣（G4 修正第 2 輪第 8 項）：半徑 r0–r1（R＝紙環貼圖半寬；v02 紙面在 0.475–0.815）、避開紙繩方向 ±25°。
    回傳平均 sRGB、亮度（Rec.601 luma）、最小通道平均、HSV 色相（度）與彩度"""
    import colorsys
    h, w = img.shape[:2]
    cx, cy = ring
    x0, x1 = int(max(0, cx - R - 2)), int(min(w, cx + R + 3))
    y0, y1 = int(max(0, cy - R - 2)), int(min(h, cy + R + 3))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx - cx, yy - cy) / max(1e-6, R)
    m = (rr >= r0) & (rr <= r1)
    if rope_dir is not None:
        ang = np.arctan2(yy - cy, xx - cx)
        a0 = np.arctan2(rope_dir[1], rope_dir[0])
        m &= np.abs((ang - a0 + np.pi) % (2 * np.pi) - np.pi) > np.deg2rad(25)
    px = img[y0:y1, x0:x1][m].reshape(-1, 3).astype(np.float32)
    if len(px) < 5:
        return None
    mean = px.mean(0)
    hh, ss, _ = colorsys.rgb_to_hsv(*(mean / 255))
    return {"mean_srgb": [round(float(v), 1) for v in mean], "luma": round(float(0.299 * mean[0] + 0.587 * mean[1] + 0.114 * mean[2]), 1),
            "min_channel_mean": round(float(mean.min()), 1), "hue_deg": round(float(hh) * 360, 1), "saturation": round(float(ss), 3), "n_px": int(len(px))}


def ring_sheet(out, crops):
    """紙環放大裁切接觸表"""
    from PIL import ImageDraw, ImageFont
    if not crops:
        return None
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 16)
    except OSError:
        font = ImageFont.load_default()
    cell = 288
    cols = 6
    rows = (len(crops) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 40)), (24, 22, 20))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(crops):
        x, y = (i % cols) * cell, (i // cols) * (cell + 40)
        sheet.paste(im.resize((cell, cell), Image.NEAREST), (x, y))
        d.text((x + 4, y + cell + 2), lab, font=font, fill=(230, 226, 218))
    path = out / "ring_crops.png"
    sheet.save(path)
    return path.name


def main():
    out = Path(sys.argv[1]).resolve()
    data = json.loads((out / "probe.json").read_text(encoding="utf-8"))
    rows, bg_rows, ring_rows, crops = [], [], [], []
    cdir = out / "ring_crops"
    cdir.mkdir(exist_ok=True)
    for f in cdir.glob("*.png"):
        f.unlink()
    max_h = {}
    for rec in data["probes"]:
        for a in rec["actors"]:
            if a.get("visible"):
                max_h[a["id"]] = max(max_h.get(a["id"], 0), a["box"][3] - a["box"][1])
    rope_crop_done = False
    for rec in data["probes"]:
        if not rec.get("frame"):
            continue
        fp = out / rec["frame"]
        if not fp.exists():
            continue
        img = np.asarray(Image.open(fp).convert("RGB"))
        proj = projector(img)
        bgp = out / rec.get("bgFrame", "")
        bg = np.asarray(Image.open(bgp).convert("RGB")) if rec.get("bgFrame") and bgp.exists() else None
        dimmed = (rec.get("dim") or 0) > DIM_MAX or (rec.get("quiz") or 0) > 0.5
        for s in rec["strings"]:
            if not s["visible"] or rec.get("curtain", 1) < 0.95:  # 布幕沒全開（線在布幕後面）不量
                continue
            c = None if dimmed else string_contrast(img, proj, s)
            row = {"cue": rec["cueId"], "t": rec["t"], "key": rec["key"], "actor": s["actor"], "anchor": s["anchor"],
                   "widthPx": round(s.get("widthTruePx") or s["widthPx"], 2), "widthPxLegacy": round(s["widthPx"], 2)}
            if c:
                row.update({"deltaL_body": round(c["body"], 1), "deltaL_edge": round(c["edge"], 1), "deltaL": round(c["best"], 1),
                            "deltaL_proj_body": round(c["body_p"], 1), "deltaL_proj_edge": round(c["edge_p"], 1), "deltaL_proj": round(c["best_p"], 1)})
            else:
                row.update({"deltaL": None, "deltaL_proj": None})
            if dimmed:
                row.update({"dim": rec.get("dim"), "quiz": rec.get("quiz"), "excluded_dim": True})
            rows.append(row)
            if s.get("ringPx") and bg is not None:
                dv, inside = ring_inside(img, bg, s["ringPx"])
                rx, ry = s["ringPx"]
                body = ring_body(img, s["ringPx"], s.get("ringRadiusPx") or 0, s.get("dir")) if s.get("ringRadiusPx") else None
                ring_rows.append({"cue": rec["cueId"], "t": rec["t"], "key": rec["key"], "anchor": s["anchor"], "ring_px": [round(rx, 1), round(ry, 1)],
                                  "ring_radius_px": round(s.get("ringRadiusPx") or 0, 1), "center_diff_vs_bg": dv, "center_inside_silhouette": inside,
                                  "body": body})
                if rec["key"] in ("mid", "after", "probe", "before") or rec["key"] and "after" in rec["key"]:
                    half = 48
                    box = (int(rx) - half, int(ry) - half, int(rx) + half, int(ry) + half)
                    crop = Image.open(fp).convert("RGB").crop(box)
                    name = f"{rec['cueId']}_{rec['t']:06.2f}_{s['anchor']}.png"
                    crop.resize((288, 288), Image.NEAREST).save(cdir / name)
                    lab = f"{rec['cueId']} {rec['t']:.2f}s {s['anchor']} {'剪影內' if inside else '剪影外'}"
                    if body:
                        lab += f" 環身{body['luma']:.0f} 色相{body['hue_deg']:.0f}°"
                    crops.append((crop, lab))
                    # 一段紙繩 1:1 放大（腕背紙環上方，看扭紋與纖維）
                    if not rope_crop_done and s["anchor"] == "wrist" and rec["key"] and "after" in rec["key"]:
                        dx, dy = s["dir"]
                        cx, cy = rx + dx * 70, ry + dy * 70
                        rb = (int(cx) - 24, int(cy) - 48, int(cx) + 24, int(cy) + 48)
                        Image.open(fp).convert("RGB").crop(rb).resize((192, 384), Image.NEAREST).save(out / "rope_crop_4x.png")
                        rope_crop_done = True
        if bg is not None and rec.get("curtain", 1) >= 0.95 and not dimmed:  # 布幕沒全開、換景漸暗中（dim > 0.05）不量背景
            H, W = bg.shape[:2]
            for a in rec["actors"]:
                if a["id"] not in ("xiaoqing", "xiaoyu") or not a["visible"]:
                    continue
                x0, y0, x1, y1 = a["box"]
                bw, bh = x1 - x0, y1 - y0
                rx0, rx1 = int(max(0, x0 + bw * 0.25)), int(min(W, x1 - bw * 0.25))
                ry0, ry1 = int(max(0, y0 + bh * 0.30)), int(min(H, y0 + bh * 0.75))
                if rx1 - rx0 < 4 or ry1 - ry0 < 4:
                    continue
                reg = bg[ry0:ry1, rx0:rx1]
                lum = luminance(projector(reg))
                bg_rows.append({"cue": rec["cueId"], "t": rec["t"], "key": rec["key"], "actor": a["id"],
                                "upright": round(bh / max(1, max_h.get(a["id"], bh)), 2),
                                "region": [rx0, ry0, rx1, ry1], "proj_lum_median": round(float(np.median(lum)), 3),
                                "proj_lum_p10": round(float(np.percentile(lum, 10)), 3)})
    sheet = ring_sheet(out, crops)
    close = [r for r in rows if r.get("deltaL") is not None]
    up = [r for r in bg_rows if r["upright"] >= 0.6]
    report = {
        "rule": {"string_width_px": "6–10（中景，G4 修正第 22 項）；G5 修正第 1 輪：全劇非 G4 cue 中景 ≥ 8、遠景 ≥ 6–7（widthPx＝實際紙帶寬）", "deltaL": ">= 25（投影模擬後 >= 15）；ΔL*＝每一側取繩身或該側深灰邊對背景的較大者、再取兩側較小者（判定方式待主線確認）",
                 "ring_center_inside_silhouette": "全部 true（G4 修正第 23 項）", "child_bg_proj_lum": ">= 0.50",
                 "dim_excluded": f"換景漸暗中 world.dim > {DIM_MAX}、或題卡 quizVisible > 0.5（DOM 題卡蓋住舞台）的格不量兒童背景與線的 ΔL*"},
        "strings": rows,
        "rings": ring_rows,
        "ring_crops": {"sheet": sheet, "dir": "ring_crops/", "rope_crop_4x": "rope_crop_4x.png" if rope_crop_done else None},
        "ring_body_rule": "環身＝紙環半徑 0.57–0.73（以紙環貼圖半寬為 1；v02 紙面在 0.475–0.815）、避開紙繩方向 ±25° 的像素平均；luma＝Rec.601；"
                          "G4 修正第 2 輪第 8 項：環身平均 sRGB ≥ 220（luma 與最小通道平均都列）、色相接近紙色（約 30–50°、彩度 ≥ 0.05），不是中性灰",
        "child_background": bg_rows,
        "summary": {
            "min_string_width_px": min((r["widthPx"] for r in rows), default=None),
            "max_string_width_px": max((r["widthPx"] for r in rows), default=None),
            "min_deltaL": min((r["deltaL"] for r in close), default=None),
            "min_deltaL_proj": min((r["deltaL_proj"] for r in close), default=None),
            "min_deltaL_body": min((r["deltaL_body"] for r in close), default=None),
            "min_deltaL_proj_body": min((r["deltaL_proj_body"] for r in close), default=None),
            "min_deltaL_edge": min((r["deltaL_edge"] for r in close), default=None),
            "min_deltaL_proj_edge": min((r["deltaL_proj_edge"] for r in close), default=None),
            "rings_measured": len(ring_rows),
            "rings_center_inside": sum(1 for r in ring_rows if r["center_inside_silhouette"]),
            "ring_body_luma_min": min((r["body"]["luma"] for r in ring_rows if r.get("body")), default=None),
            "ring_body_luma_median": float(np.median([r["body"]["luma"] for r in ring_rows if r.get("body")])) if any(r.get("body") for r in ring_rows) else None,
            "ring_body_min_channel_min": min((r["body"]["min_channel_mean"] for r in ring_rows if r.get("body")), default=None),
            "ring_body_hue_median": float(np.median([r["body"]["hue_deg"] for r in ring_rows if r.get("body")])) if any(r.get("body") for r in ring_rows) else None,
            "ring_body_hue_range": [min((r["body"]["hue_deg"] for r in ring_rows if r.get("body")), default=None), max((r["body"]["hue_deg"] for r in ring_rows if r.get("body")), default=None)],
            "ring_body_sat_median": float(np.median([r["body"]["saturation"] for r in ring_rows if r.get("body")])) if any(r.get("body") for r in ring_rows) else None,
            "ring_body_sat_min": min((r["body"]["saturation"] for r in ring_rows if r.get("body")), default=None),
            "min_child_bg_median": min((r["proj_lum_median"] for r in bg_rows), default=None),
            "min_child_bg_p10": min((r["proj_lum_p10"] for r in bg_rows), default=None),
            "min_child_bg_median_upright": min((r["proj_lum_median"] for r in up), default=None),
            "child_bg_frames": len(bg_rows),
            "frames_excluded_dim": sum(1 for r in data["probes"] if ((r.get("dim") or 0) > DIM_MAX or (r.get("quiz") or 0) > 0.5) and r.get("frame")),
        },
        "limits": "ΔL* 以線兩側緊鄰像素計（可能是皮膚、袖口或背景）；紙環剪影判定只看紙環中心；實際投影無法由此驗證。",
    }
    (out / "probe_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    s = report["summary"]
    print(f"[probe] 線寬 {s['min_string_width_px']}–{s['max_string_width_px']} px；ΔL* 最小 {s['min_deltaL']}（投影 {s['min_deltaL_proj']}；繩身 {s['min_deltaL_body']}、深灰邊 {s['min_deltaL_edge']}）；"
          f"紙環中心在剪影內 {s['rings_center_inside']}／{s['rings_measured']}；環身亮度最低 {s['ring_body_luma_min']}、色相中位 {s['ring_body_hue_median']}；兒童背景投影亮度 中位數最低 {s['min_child_bg_median']}、p10 最低 {s['min_child_bg_p10']} → probe_report.json")


if __name__ == "__main__":
    main()
