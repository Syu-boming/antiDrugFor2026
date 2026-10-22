"""flashcheck 影格的單一細格亮度序列與轉折：cellseries.py <影格資料夾> <fps> <x1080> <y1080> <t0> <t1> [red]
（座標＝1920×1080 的像素，取該點所在的 fine 32×18 格）"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import capture_analyze as ca  # noqa: E402

d = Path(sys.argv[1]); fps = float(sys.argv[2]); X, Y = int(sys.argv[3]), int(sys.argv[4]); t0, t1 = float(sys.argv[5]), float(sys.argv[6])
RED = len(sys.argv) > 7 and sys.argv[7] == "red"
gx, gy = X // 60, Y // 60
times, vals = [], []
for f in sorted(d.glob("*.jpg")):
    t = int(f.stem) / fps
    if t < t0 - 1 or t > t1 + 1:
        continue
    im = Image.open(f).convert("RGB").resize((640, 360), Image.BOX)
    a = ca.to_linear(np.asarray(im, dtype=np.float32) / 255.0)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    if RED:
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        sat = (r / np.maximum(r + g + b, 1e-6) >= 0.8) & (r > 0.05)
        lum = np.where(sat, np.maximum(0.0, r - g - b) * 320.0, 0.0)
    times.append(t); vals.append(float(lum[gy * 20:(gy + 1) * 20, gx * 20:(gx + 1) * 20].mean()))
ev = ca.transitions(times, vals, ca.RED_TH, None) if RED else ca.transitions(times, vals, ca.LUMA_TH, ca.LUMA_DARK)
print(f"cell x{gx}_y{gy}：", "轉折", [round(e, 2) for e in ev])
for t, v in zip(times, vals):
    if t0 <= t <= t1:
        print(f"{t:6.2f} {v:.3f}", "*" if any(abs(t - e) < 1e-6 for e in ev) else "")
