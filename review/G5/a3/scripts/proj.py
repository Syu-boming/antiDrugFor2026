"""鏡位投影小工具（規劃構圖用）：proj(cam, [(x,y,z),...]) → 1920×1080 畫面座標。three.js PerspectiveCamera（fov 垂直、16:9）。"""
import math, sys, json
import numpy as np

def proj(cam, pts, W=1920, H=1080):
    pos = np.array(cam['pos'], float); tgt = np.array(cam['target'], float)
    f = tgt - pos; f /= np.linalg.norm(f)
    up = np.array([0, 1, 0.0]); r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
    th = math.tan(math.radians(cam['fov']) / 2); asp = W / H
    out = []
    for p in pts:
        d = np.array(p, float) - pos
        z = d @ f
        x = (d @ r) / (z * th * asp); y = (d @ u) / (z * th)
        out.append((round((x + 1) / 2 * W), round((1 - y) / 2 * H)))
    return out

def frame_at(cam, zplane, W=1920, H=1080):
    """畫面四角在 z=zplane 平面（垂直於鏡頭近似）上的寬高（世界單位）"""
    pos = np.array(cam['pos'], float)
    dist = pos[2] - zplane
    h = 2 * dist * math.tan(math.radians(cam['fov']) / 2)
    return h * W / H, h

if __name__ == '__main__':
    cam = json.loads(sys.argv[1]); pts = json.loads(sys.argv[2])
    print(proj(cam, pts), frame_at(cam, pts[0][2]))
