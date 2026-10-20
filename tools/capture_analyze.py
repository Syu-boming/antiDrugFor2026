"""擷取結果分析：接觸表＋亮度／飽和紅色時間序列＋光敏檢查（v1.2 第 17.3 節、CLAUDE.md 安全界線第 9 條）。

用法：/opt/anaconda3/bin/python3 tools/capture_analyze.py <擷取資料夾>
（通常由 tools/capture.mjs 自動呼叫；資料夾內要有 capture.json）

光敏檢查方法：
- 每格縮成 320×180，切成 16×9 個區域（每區約占畫面 0.7%，不採面積豁免），另加整個畫面。
- 明暗：線性相對亮度；從上一個極值變化 ≥ 0.10 且較暗的一端 < 0.80 時記一次「變化」（WCAG 2.3.1 的轉折定義）。
- 紅色：飽和紅色 R/(R+G+B) ≥ 0.8 的像素，以 (R−G−B)×320 的區域平均值計，變化 ≥ 20 記一次。
- 任一區域在任一 1 秒窗內的變化次數 > 3 即標示（專案規則：每秒變化 ≤ 3 次）。
- 取樣率見 capture.json 的 analysisFps；取樣 10 格／秒最多能分辨每秒 5 次變化，要更嚴謹可用 --analysis-fps 30 重跑。
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

GRID_W, GRID_H = 16, 9
SMALL = (320, 180)
LUMA_TH = 0.10
LUMA_DARK = 0.80
RED_TH = 20.0
LIMIT_PER_SEC = 3
KEY_LABEL = {"before": "前", "mid": "中", "after": "後"}


def font(size):
    for p in ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
              "C:/Windows/Fonts/msjh.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def to_linear(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def frame_stats(path):
    """回傳（區域亮度 9×16、區域紅色值 9×16、整體亮度、飽和紅色比例）"""
    im = Image.open(path).convert("RGB").resize(SMALL, Image.BOX)
    a = to_linear(np.asarray(im, dtype=np.float32) / 255.0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    s = r + g + b
    sat = (r / np.maximum(s, 1e-6) >= 0.8) & (r > 0.05)
    redv = np.where(sat, np.maximum(0.0, r - g - b) * 320.0, 0.0)
    bh, bw = SMALL[1] // GRID_H, SMALL[0] // GRID_W
    reg = lambda x: x[: bh * GRID_H, : bw * GRID_W].reshape(GRID_H, bh, GRID_W, bw).mean(axis=(1, 3))
    return reg(lum), reg(redv), float(lum.mean()), float(sat.mean())


def transitions(times, series, th, dark_limit=None):
    """依 WCAG 轉折定義找出「變化」發生的時間點"""
    events = []
    if len(series) < 2:
        return events
    lo = hi = series[0]
    pk = series[0]
    trend = 0
    ok = (lambda a, b: min(a, b) < dark_limit) if dark_limit is not None else (lambda a, b: True)
    for t, v in zip(times[1:], series[1:]):
        if trend == 0:
            if v - lo >= th and ok(lo, v):
                events.append(t); trend, pk = 1, v
            elif hi - v >= th and ok(v, hi):
                events.append(t); trend, pk = -1, v
            lo, hi = min(lo, v), max(hi, v)
        elif trend == 1:
            if v > pk:
                pk = v
            elif pk - v >= th and ok(v, pk):
                events.append(t); trend, pk = -1, v
        else:
            if v < pk:
                pk = v
            elif v - pk >= th and ok(pk, v):
                events.append(t); trend, pk = 1, v
    return events


def max_per_second(events):
    """任一 1 秒窗內最多幾次變化，以及那個窗的起點"""
    best, at = 0, None
    j = 0
    for i, t in enumerate(events):
        while events[j] < t - 1.0 + 1e-9:
            j += 1
        if i - j + 1 > best:
            best, at = i - j + 1, events[j]
    return best, at


def contact_keyframes(out, meta):
    rows = []
    for c in meta["cueList"]:
        ks = {}
        for f in meta["frames"]:
            if f["cueId"] == c["id"] and f.get("key"):
                for k in f["key"].split("+"):
                    ks[k] = f
        if ks:
            rows.append((c, ks))
    tw, th, lw, pad = 480, 270, 300, 10
    W = lw + 3 * (tw + pad) + pad
    H = len(rows) * (th + pad + 28) + pad + 50
    sheet = Image.new("RGB", (W, H), (24, 20, 17))
    d = ImageDraw.Draw(sheet)
    f_big, f_small = font(22), font(18)
    d.text((pad, 12), f"關鍵影格（前／中／後）  {meta['cues']}  {meta['width']}×{meta['height']}  畫質 {meta['quality']}", fill=(240, 228, 210), font=f_big)
    y = 50
    for c, ks in rows:
        d.text((pad, y + 6), c["id"], fill=(255, 220, 160), font=f_big)
        d.text((pad, y + 40), f"{c['kind']}  {c['duration']:.1f} 秒", fill=(220, 210, 195), font=f_small)
        d.text((pad, y + 68), c.get("title", "")[:14], fill=(200, 190, 175), font=f_small)
        if c.get("placeholder"):
            d.text((pad, y + 96), "暫代音訊", fill=(230, 170, 120), font=f_small)
        for j, k in enumerate(("before", "mid", "after")):
            f = ks.get(k)
            if not f:
                continue
            im = Image.open(out / f["file"]).convert("RGB").resize((tw, th), Image.LANCZOS)
            x = lw + pad + j * (tw + pad)
            sheet.paste(im, (x, y))
            d.text((x, y + th + 3), f"{KEY_LABEL[k]}  t={f['t']:.2f}s  {f.get('phase', '')}", fill=(200, 190, 175), font=f_small)
        y += th + pad + 28
    p = out / "contact_keyframes.png"
    sheet.save(p)
    return p


def contact_timeline(out, meta, cols=6, per_page=48):
    fr = sorted([f for f in meta["frames"] if f.get("save")], key=lambda f: f["globalT"])
    tw, th, pad = 320, 180, 8
    pages = []
    for pi in range(0, len(fr), per_page):
        chunk = fr[pi: pi + per_page]
        rows = (len(chunk) + cols - 1) // cols
        W = cols * (tw + pad) + pad
        H = rows * (th + pad + 24) + pad + 40
        sheet = Image.new("RGB", (W, H), (24, 20, 17))
        d = ImageDraw.Draw(sheet)
        d.text((pad, 10), f"每秒 {meta['fps']} 格  {meta['cues']}  第 {pi // per_page + 1} 頁", fill=(240, 228, 210), font=font(20))
        for i, f in enumerate(chunk):
            x, y = pad + (i % cols) * (tw + pad), 40 + (i // cols) * (th + pad + 24)
            sheet.paste(Image.open(out / f["file"]).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x, y + th + 2), f"{f['cueId']}  t={f['t']:.1f}s  ({f['globalT']:.1f})", fill=(200, 190, 175), font=font(15))
        p = out / f"contact_timeline_{pi // per_page + 1:02d}.png"
        sheet.save(p)
        pages.append(p)
    return pages


def plot(out, meta, times, luma, red, boundaries, flagged_times):
    W, H, ml, mb = 1600, 420, 60, 40
    im = Image.new("RGB", (W, H), (250, 247, 240))
    d = ImageDraw.Draw(im)
    T = max(times[-1], 1e-6) if times else 1
    X = lambda t: ml + (W - ml - 20) * t / T
    Y = lambda v: H - mb - (H - mb - 30) * v
    for t, label in boundaries:
        d.line([(X(t), 30), (X(t), H - mb)], fill=(200, 190, 175))
        d.text((X(t) + 3, 32), label, fill=(120, 100, 80), font=font(13))
    for t in flagged_times:
        d.line([(X(t), 30), (X(t), H - mb)], fill=(230, 120, 60), width=3)
    if len(times) > 1:
        d.line([(X(t), Y(v)) for t, v in zip(times, luma)], fill=(40, 60, 120), width=2)
        d.line([(X(t), Y(v)) for t, v in zip(times, red)], fill=(200, 60, 60), width=2)
    d.line([(ml, H - mb), (W - 20, H - mb)], fill=(80, 70, 60))
    d.text((ml, 6), "藍：平均相對亮度（線性 0–1）　紅：飽和紅色像素比例　橘線：超過每秒 3 次變化的位置", fill=(60, 50, 40), font=font(16))
    d.text((ml, H - mb + 8), f"0 秒", fill=(60, 50, 40), font=font(14))
    d.text((W - 120, H - mb + 8), f"{T:.1f} 秒", fill=(60, 50, 40), font=font(14))
    p = out / "luma_plot.png"
    im.save(p)
    return p


def main():
    out = Path(sys.argv[1]).resolve()
    meta = json.loads((out / "capture.json").read_text(encoding="utf-8"))
    fr = sorted([f for f in meta["frames"] if f.get("analysis")], key=lambda f: f["globalT"])
    times, luma, red = [], [], []
    regL, regR = [], []
    rows = []
    for f in fr:
        rl, rr, ml, rratio = frame_stats(out / f["file"])
        times.append(f["globalT"]); luma.append(ml); red.append(rratio)
        regL.append(rl); regR.append(rr)
        rows.append([f"{f['globalT']:.3f}", f["cueId"], f"{f['t']:.3f}", f"{ml:.5f}", f"{rratio:.5f}", f"{rl.max():.5f}", f"{rr.max():.3f}"])
    with open(out / "luma_series.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["global_t", "cue_id", "cue_t", "mean_luma_linear", "sat_red_ratio", "max_region_luma", "max_region_red_value"])
        w.writerows(rows)

    regL, regR = np.array(regL), np.array(regR)
    flagged, worst = [], {"luma": 0, "red": 0}
    whole = transitions(times, luma, LUMA_TH, LUMA_DARK)
    wc, wat = max_per_second(whole)
    worst["luma"] = wc
    if wc > LIMIT_PER_SEC:
        flagged.append({"type": "luma", "region": "全畫面", "count_per_sec": wc, "window_start": wat})
    for gy in range(GRID_H):
        for gx in range(GRID_W):
            for kind, arr, th, dark in (("luma", regL, LUMA_TH, LUMA_DARK), ("red", regR, RED_TH, None)):
                ev = transitions(times, list(arr[:, gy, gx]), th, dark)
                c, at = max_per_second(ev)
                worst[kind] = max(worst[kind], c)
                if c > LIMIT_PER_SEC:
                    flagged.append({"type": kind, "region": f"x{gx}_y{gy}", "count_per_sec": c, "window_start": at})
    boundaries, acc = [], 0.0
    for c in meta["cueList"]:
        boundaries.append((acc, c["id"]))
        acc += c["duration"]
    report = {
        "ok": len(flagged) == 0,
        "rule": "任一區域明暗或飽和紅色每秒變化 ≤ 3 次（不採面積豁免）",
        "method": f"{GRID_W}×{GRID_H} 區域＋全畫面；亮度門檻 {LUMA_TH}（較暗端 < {LUMA_DARK}）；紅色門檻 {RED_TH}；取樣 {meta['analysisFps']} 格／秒",
        "frames_analyzed": len(fr),
        "duration_sec": round(acc, 3),
        "max_changes_per_sec": worst,
        "flagged": sorted(flagged, key=lambda x: -x["count_per_sec"])[:200],
        "flagged_total": len(flagged),
        "mean_luma_range": [round(min(luma), 4), round(max(luma), 4)] if luma else None,
        "max_sat_red_ratio": round(max(red), 5) if red else None,
        "limits": "取樣率決定可偵測的最高變化頻率；字幕換頁也算區域變化。聽感與實際投影的光感無法由此驗證。",
    }
    (out / "flash_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    kp = contact_keyframes(out, meta)
    tp = contact_timeline(out, meta)
    pp = plot(out, meta, times, luma, red, boundaries, sorted({f["window_start"] for f in flagged if f["window_start"] is not None}))
    status = "通過" if report["ok"] else f"有 {len(flagged)} 個區域超標"
    print(f"[analyze] 光敏檢查：{status}（每秒最多變化：明暗 {worst['luma']}、紅色 {worst['red']}；分析 {len(fr)} 格）")
    print(f"[analyze] 接觸表：{kp.name}、{', '.join(p.name for p in tp)}；時間序列：luma_series.csv、{pp.name}；報告：flash_report.json")


if __name__ == "__main__":
    main()
