"""列出某個 cue 逐格（flashcheck 的 _check/<cue>/*.jpg）fine 32×18 每秒 >3 次的區域與那 1 秒內的變化時間（找是什麼在動）。
用法：python flashcells.py <dir> <fps> [t0 t1]"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import capture_analyze as ca  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "review/G5/a3/scripts"))
from flashcheck import stats  # noqa: E402

d = Path(sys.argv[1]); fps = float(sys.argv[2])
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0; t1 = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
files = [f for f in sorted(d.glob("*.jpg")) if t0 <= int(f.stem) / fps <= t1]
times = [int(f.stem) / fps for f in files]
S = [stats(f, 32, 18) for f in files]
L = np.array([s["L"] for s in S]); R = np.array([s["R"] for s in S])
for kind, arr, th, dark in (("luma", L, ca.LUMA_TH, ca.LUMA_DARK), ("red", R, ca.RED_TH, None)):
    for gy in range(18):
        for gx in range(32):
            ev = ca.transitions(times, list(arr[:, gy, gx]), th, dark)
            c, at = ca.max_per_second(ev)
            if c > 3:
                evs = [round(e if isinstance(e, float) else e[0], 2) for e in ev]
                print(kind, f"x{gx}_y{gy}", f"px({gx*60},{gy*60})", c, "at", round(at, 2), "events", [e for e in evs if at - 0.05 <= e <= at + 1.05])
