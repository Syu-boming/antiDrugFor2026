"""列出 flashcheck 擷取資料夾裡每秒 >3 次的格子（fine 32×18 與 16×9）：python flashcells.py <資料夾> [fps]"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import capture_analyze as ca  # noqa: E402
from flashcheck import stats  # noqa: E402

d = Path(sys.argv[1]); fps = float(sys.argv[2]) if len(sys.argv) > 2 else 30
files = sorted(d.glob("*.jpg"))
times = [int(f.stem) / fps for f in files]
for name, (gw, gh) in (("fine", (32, 18)), ("16x9", (16, 9))):
    S = [stats(f, gw, gh) for f in files]
    L = np.array([s["L"] for s in S]); R = np.array([s["R"] for s in S])
    for gy in range(gh):
        for gx in range(gw):
            for kind, arr, th, dark in (("luma", L, ca.LUMA_TH, ca.LUMA_DARK), ("red", R, ca.RED_TH, None)):
                ev = ca.transitions(times, list(arr[:, gy, gx]), th, dark)
                c, at = ca.max_per_second(ev)
                if c > 3:
                    print(name, kind, f"cell x{gx} y{gy} (px {gx * 1920 // gw}-{(gx + 1) * 1920 // gw}, {gy * 1080 // gh}-{(gy + 1) * 1080 // gh})", c, "t", round(at, 2), "events", [round(e, 2) for e in ev if at - 0.1 <= e <= at + 1.1])
