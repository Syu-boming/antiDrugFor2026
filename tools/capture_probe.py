"""擷取量測（tools/capture.mjs --probe 會自動呼叫）：操偶線線寬與明度差、兒童站位背景亮度。

用法：/opt/anaconda3/bin/python3 tools/capture_probe.py <擷取資料夾>

量什麼：
1. 操偶線線寬（px，1080p 繪圖緩衝）：劇場程式回報的螢幕線寬（垂直於線的方向）。規格：近景 ≥ 8 px。
2. 操偶線與相鄰處的明度差 ΔL*（CIELAB）：沿線在紙環上方 14–60 px 取樣，線中心 vs 線兩側緊鄰（線寬一半＋3 px 外）的像素；
   取兩側中較小的那個，再取沿線中位數。原圖與投影 v2 模擬（彩度 ×0.65、黑位 0.18、白位 0.87）各算一次。
   規格（劇本 L1 投影可讀性）：ΔL* ≥ 25，投影模擬後 ≥ 15。
3. 兒童站位背景亮度：同一格隱藏角色後重畫（probe_bg/），在每個兒童外框的軀幹帶（寬 50%、高 30–75%）量 WCAG 相對亮度，
   套投影 v2 模擬後取中位數與第 10 百分位。規格（D-G2-06）：≥ 0.50。
輸出：probe_report.json，並在終端機印摘要。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJ = (0.65, 0.18, 0.87)


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


def string_contrast(img, s):
    ax, ay = s["anchorPx"]
    dx, dy = s["dir"]
    w = max(2.0, s["widthPx"])
    nx, ny = -dy, dx
    out, outp = [], []
    proj = projector(img)
    for d in range(14, 61, 3):
        cx, cy = ax + dx * d, ay + dy * d
        c = sample(img, cx, cy)
        if c is None:
            continue
        sides, sidesp = [], []
        for sgn in (-1, 1):
            off = w / 2 + 3
            p = sample(img, cx + nx * off * sgn, cy + ny * off * sgn)
            if p is not None:
                sides.append(abs(float(lstar(c[None, :3])[0] - lstar(p[None, :3])[0])))
                pc = sample(proj, cx, cy)
                pp = sample(proj, cx + nx * off * sgn, cy + ny * off * sgn)
                sidesp.append(abs(float(lstar(pc[None, :3])[0] - lstar(pp[None, :3])[0])))
        if sides:
            out.append(min(sides))
            outp.append(min(sidesp))
    if not out:
        return None, None
    return float(np.median(out)), float(np.median(outp))


def main():
    out = Path(sys.argv[1]).resolve()
    data = json.loads((out / "probe.json").read_text(encoding="utf-8"))
    rows, bg_rows = [], []
    for rec in data["probes"]:
        if not rec.get("frame"):
            continue
        fp = out / rec["frame"]
        if not fp.exists():
            continue
        img = np.asarray(Image.open(fp).convert("RGB"))
        for s in rec["strings"]:
            if not s["visible"] or rec.get("curtain", 1) < 0.95:  # 布幕沒全開（線在布幕後面）不量
                continue
            dl, dlp = string_contrast(img, s)
            rows.append({"cue": rec["cueId"], "t": rec["t"], "key": rec["key"], "actor": s["actor"], "anchor": s["anchor"],
                         "widthPx": round(s["widthPx"], 2), "deltaL": None if dl is None else round(dl, 1),
                         "deltaL_proj": None if dlp is None else round(dlp, 1)})
        bgp = out / rec.get("bgFrame", "")
        if rec.get("bgFrame") and bgp.exists() and rec.get("curtain", 1) >= 0.95:  # 布幕沒全開時不量背景
            bg = np.asarray(Image.open(bgp).convert("RGB"))
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
                                "region": [rx0, ry0, rx1, ry1], "proj_lum_median": round(float(np.median(lum)), 3),
                                "proj_lum_p10": round(float(np.percentile(lum, 10)), 3)})
    close = [r for r in rows if r["deltaL"] is not None]
    report = {
        "rule": {"string_width_px_closeup": ">= 8", "deltaL": ">= 25（投影模擬後 >= 15）", "child_bg_proj_lum": ">= 0.50"},
        "strings": rows,
        "child_background": bg_rows,
        "summary": {
            "min_string_width_px": min((r["widthPx"] for r in rows), default=None),
            "min_deltaL": min((r["deltaL"] for r in close), default=None),
            "min_deltaL_proj": min((r["deltaL_proj"] for r in close), default=None),
            "min_child_bg_median": min((r["proj_lum_median"] for r in bg_rows), default=None),
            "min_child_bg_p10": min((r["proj_lum_p10"] for r in bg_rows), default=None),
        },
        "limits": "ΔL* 以線兩側緊鄰像素計（可能是皮膚、袖口或背景）；實際投影無法由此驗證。",
    }
    (out / "probe_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    s = report["summary"]
    print(f"[probe] 線寬最小 {s['min_string_width_px']} px；ΔL* 最小 {s['min_deltaL']}（投影 {s['min_deltaL_proj']}）；"
          f"兒童背景投影亮度 中位數最低 {s['min_child_bg_median']}、p10 最低 {s['min_child_bg_p10']} → probe_report.json")


if __name__ == "__main__":
    main()
