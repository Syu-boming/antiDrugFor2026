"""鏡位檢查：把指定世界座標投影到畫面（NDC，−1～1；下方 20% 字幕區＝y < −0.6），檢查台口邊緣是否入鏡。
用法：python camcheck.py  （鏡位與檢查點寫在下面）"""
import json, math, sys
import numpy as np

def proj(cam, P, aspect=16 / 9):
    pos, tgt, fov = np.array(cam["pos"], float), np.array(cam["target"], float), cam["fov"]
    f = tgt - pos; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    d = np.array(P, float) - pos
    zc = d @ f
    th = math.tan(math.radians(fov) / 2)
    return (d @ r) / (zc * th * aspect), (d @ u) / (zc * th)

if __name__ == "__main__":
    cams = json.loads(sys.argv[1])
    pts = json.loads(sys.argv[2])
    for cn, cam in cams.items():
        print(f"== {cn}")
        for name, P in pts.items():
            x, y = proj(cam, P)
            flag = "  OUT" if abs(x) > 1 or abs(y) > 1 else ""
            sub = "  (字幕區)" if y < -0.6 else ""
            print(f"  {name:18s} x={x:+.2f} y={y:+.2f}{flag}{sub}")
