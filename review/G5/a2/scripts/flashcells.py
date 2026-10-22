"""第二幕修正自查：細格光敏超標的格子位置（同 tools/capture_analyze.py 門檻；影格來自 review/G5/a4/scripts/flashcheck.mjs）。
用法：python3 flashcells.py <影格資料夾> [fps=30] [格網 32x18]"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import capture_analyze as ca  # noqa: E402

d = Path(sys.argv[1]); fps = float(sys.argv[2]) if len(sys.argv) > 2 else 30
gw, gh = map(int, (sys.argv[3] if len(sys.argv) > 3 else "32x18").split("x"))
files = sorted(d.glob("*.jpg"))
times = [int(f.stem) / fps for f in files]
L = []
for f in files:
    im = Image.open(f).convert("RGB").resize((640, 360), Image.BOX)
    a = ca.to_linear(np.asarray(im, dtype=np.float32) / 255.0)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    bh, bw = 360 // gh, 640 // gw
    L.append(lum[: bh * gh, : bw * gw].reshape(gh, bh, gw, bw).mean(axis=(1, 3)))
L = np.array(L)
bad = []
for gy in range(gh):
    for gx in range(gw):
        ev = ca.transitions(times, list(L[:, gy, gx]), ca.LUMA_TH, ca.LUMA_DARK)
        c, at = ca.max_per_second(ev)
        if c > 3:
            bad.append((round(at, 2), gx, gy, c, [round(e, 2) for e in ev][:12] if isinstance(ev[0], float) else ev[:8]))
for b in sorted(bad):
    print(b)
