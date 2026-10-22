"""fc2.mjs 的分析：連續片段的 fine 32×18、16×9 每秒幾次（門檻同 tools/capture_analyze.py），
加上全畫面平均亮度一格內相對變化 > 20%（且絕對 ≥ 0.03）的位置。"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import capture_analyze as ca  # noqa: E402


def main():
    out = Path(sys.argv[1])
    meta = json.loads((out / "list.json").read_text())
    fps = meta["fps"]
    frames = meta["frames"]
    Ls, Rs, M = {32: [], 16: []}, {32: [], 16: []}, []
    for fr in frames:
        im = Image.open(out / f"{fr['k']:06d}.jpg").convert("RGB").resize((640, 360), Image.BOX)
        a = ca.to_linear(np.asarray(im, dtype=np.float32) / 255.0)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        s = r + g + b
        sat = (r / np.maximum(s, 1e-6) >= 0.8) & (r > 0.05)
        redv = np.where(sat, np.maximum(0.0, r - g - b) * 320.0, 0.0)
        M.append(float(lum.mean()))
        for gw, gh in ((32, 18), (16, 9)):
            bh, bw = 360 // gh, 640 // gw
            reg = lambda x: x[: bh * gh, : bw * gw].reshape(gh, bh, gw, bw).mean(axis=(1, 3))
            Ls[gw].append(reg(lum)); Rs[gw].append(reg(redv))
    times = [i / fps for i in range(len(frames))]
    where = lambda t: (frames[min(len(frames) - 1, int(round(t * fps)))]["cue"], round(frames[min(len(frames) - 1, int(round(t * fps)))]["t"], 2))
    ok = True
    for gw, gh, name in ((32, 18, "fine_32x18"), (16, 9, "16x9")):
        L = np.array(Ls[gw]); R = np.array(Rs[gw])
        worst = {"luma": (0, None), "red": (0, None)}
        bad = []
        for gy in range(gh):
            for gx in range(gw):
                for kind, arr, th, dark in (("luma", L, ca.LUMA_TH, ca.LUMA_DARK), ("red", R, ca.RED_TH, None)):
                    ev = ca.transitions(times, list(arr[:, gy, gx]), th, dark)
                    c, at = ca.max_per_second(ev)
                    if c > worst[kind][0]:
                        worst[kind] = (c, at)
                    if c > 3:
                        bad.append((kind, gx, gy, c, at))
        if bad:
            ok = False
        wl = worst["luma"]; wr = worst["red"]
        print(f"{name}: 明暗 {wl[0]}（{where(wl[1]) if wl[1] is not None else '-'}）紅 {wr[0]}（{where(wr[1]) if wr[1] is not None else '-'}）超標 {len(bad)} 格")
        for kind, gx, gy, c, at in sorted(bad, key=lambda b: b[4])[:30]:
            px = 1920 // gw
            print(f"    {kind}{c} 格 x{gx}_y{gy}（px {gx * px}–{(gx + 1) * px}, {gy * px}–{(gy + 1) * px}）{where(at)}")
    jumps = []
    for i in range(1, len(M)):
        a, b = M[i - 1], M[i]
        if abs(b - a) >= 0.05 and abs(b - a) / max(1e-6, min(a, b)) > 0.2:
            jumps.append((i, a, b))
    print(f"全畫面亮度一格內相對變化 > 20%：{len(jumps)} 處" + ("" if not jumps else "；" + "；".join(f"{frames[i]['cue']} t={frames[i]['t']:.2f} {a:.3f}→{b:.3f}" for i, a, b in jumps[:20])))
    mx = 0.0
    for i in range(1, len(M)):
        a, b = M[i - 1], M[i]
        mx = max(mx, abs(b - a) / max(1e-6, min(a, b)))
    print(f"全畫面亮度一格內最大相對變化 {mx * 100:.1f}%")
    np.save(out / "mean_luma.npy", np.array(M))


if __name__ == "__main__":
    main()
