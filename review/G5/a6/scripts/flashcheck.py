"""第六幕代理的私人光敏檢查：和驗收包相同的算法（tools/capture_analyze.py transitions／max_per_second、g4_review_pack._region_stats）。
用法：python3 flashcheck.py seq.json report.json"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import capture_analyze as ca  # noqa: E402


def region_stats(rgb, gw, gh):
    a = ca.to_linear(rgb.astype(np.float32) / 255.0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    ssum = r + g + b
    sat = (r / np.maximum(ssum, 1e-6) >= 0.8) & (r > 0.05)
    redv = np.where(sat, np.maximum(0.0, r - g - b) * 320.0, 0.0)
    H, W = lum.shape
    bh, bw = H // gh, W // gw
    reg = lambda x: x[: bh * gh, : bw * gw].reshape(gh, bh, gw, bw).mean(axis=(1, 3))  # noqa: E731
    return reg(lum), reg(redv), float(lum.mean())


def main():
    d = json.loads(Path(sys.argv[1]).read_text())
    fps = d["fps"]
    seq = d["seq"]
    grids = {"16x9": (16, 9), "fine_32x18": (32, 18)}
    data = {k: ([], []) for k in grids}
    means = []
    cache = {}
    for f, cue, ct in seq:
        if f not in cache:
            im = np.asarray(Image.open(f).convert("RGB").resize((640, 360), Image.BOX))
            cache.clear()
            cache[f] = {k: region_stats(im, *g) for k, g in grids.items()}
        for k in grids:
            L, R, M = cache[f][k]
            data[k][0].append(L)
            data[k][1].append(R)
        means.append(cache[f]["16x9"][2])
    times = [i / fps for i in range(len(seq))]
    rep = {"frames": len(seq), "grids": {}}
    for k, (gw, gh) in grids.items():
        L, R = np.array(data[k][0]), np.array(data[k][1])
        worst = {"luma": 0, "red": 0}
        flagged = []
        for gy in range(gh):
            for gx in range(gw):
                for kind, arr, th, dark in (("luma", L, ca.LUMA_TH, ca.LUMA_DARK), ("red", R, ca.RED_TH, None)):
                    ev = ca.transitions(times, list(arr[:, gy, gx]), th, dark)
                    c, at = ca.max_per_second(ev)
                    worst[kind] = max(worst[kind], c)
                    if c > 3:
                        i = int(round(at * fps))
                        flagged.append({"type": kind, "region": f"x{gx}_y{gy}", "n": c, "cue": seq[i][1], "cue_t": seq[i][2]})
        rep["grids"][k] = {"max": worst, "flagged_total": len(flagged), "flagged": flagged[:600]}
    # 全畫面平均亮度：一格之內相對變化最大的地方（切場亮度漸變：> 約 20% 不能一格硬切）
    # 只抓「一格硬切」：這一格的相對變化 > 12%，而前後兩格的變化都 < 這一格的 1/4（漸變不算）
    jumps = []
    rel = [0.0] + [abs(means[i] - means[i - 1]) / max(2e-3, min(means[i], means[i - 1])) for i in range(1, len(means))]
    for i in range(1, len(means)):
        r = rel[i]
        nb = max(rel[i - 1], rel[i + 1] if i + 1 < len(rel) else 0)
        if r > 0.12 and nb < r / 4:
            jumps.append({"cue": seq[i][1], "cue_t": seq[i][2], "rel": round(r, 3), "from": round(means[i - 1], 4), "to": round(means[i], 4)})
    rep["frame_jumps_over_12pct"] = jumps[:60]
    Path(sys.argv[2]).write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    for k in grids:
        g = rep["grids"][k]
        print(f"{k}: 明暗 {g['max']['luma']}、紅色 {g['max']['red']}，超標 {g['flagged_total']}")
        by = {}
        for x in g["flagged"]:
            by.setdefault((x["cue"], round(x["cue_t"], 1)), []).append(f"{x['type'][0]}{x['n']}:{x['region']}")
        for (cue, t), v in sorted(by.items()):
            print(f"   {cue} {t}: {' '.join(v[:8])}{' …' if len(v) > 8 else ''}")
    print("一格硬切、全畫面亮度變化 >12%：", ", ".join(f"{j['cue']}@{j['cue_t']}({j['rel']})" for j in jumps[:20]) or "無")


if __name__ == "__main__":
    main()
