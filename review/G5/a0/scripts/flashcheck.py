"""flashcheck.mjs 的分析：fine 32×18 與 16×9（門檻同 tools/capture_analyze.py），列出每秒 >3 次的區域與時間。"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import capture_analyze as ca  # noqa: E402


def stats(path, gw, gh):
    im = Image.open(path).convert("RGB").resize((640, 360), Image.BOX)
    a = ca.to_linear(np.asarray(im, dtype=np.float32) / 255.0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    s = r + g + b
    sat = (r / np.maximum(s, 1e-6) >= 0.8) & (r > 0.05)
    redv = np.where(sat, np.maximum(0.0, r - g - b) * 320.0, 0.0)
    bh, bw = 360 // gh, 640 // gw
    reg = lambda x: x[: bh * gh, : bw * gw].reshape(gh, bh, gw, bw).mean(axis=(1, 3))
    return {"L": reg(lum), "R": reg(redv)}


def main():
    items = json.loads(Path(sys.argv[1]).read_text())
    for it in items:
        files = sorted(Path(it["dir"]).glob("*.jpg"))
        times = [int(f.stem) / it["fps"] for f in files]
        for name, (gw, gh) in (("fine_32x18", (32, 18)), ("16x9", (16, 9))):
            S = [stats(f, gw, gh) for f in files]
            L = np.array([s["L"] for s in S]); R = np.array([s["R"] for s in S])
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
                            bad.append((kind, gx, gy, c, round(at, 2)))
            ts = sorted({b[4] for b in bad})
            print(f"{it['id']} {name}: luma {worst['luma'][0]}（t={worst['luma'][1]}）red {worst['red'][0]}（t={worst['red'][1]}）超標 {len(bad)} 格；時間 {ts[:12]}")
            if bad and name == "fine_32x18":
                print("   ", " ".join(f"{k[0]}{c}@({gx * 60},{gy * 60})t{at}" for k, gx, gy, c, at in sorted(bad, key=lambda b: b[4])[:40]))


if __name__ == "__main__":
    main()
