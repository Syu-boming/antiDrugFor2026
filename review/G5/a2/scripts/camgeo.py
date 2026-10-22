"""第二幕修正自查：鏡頭幾何（像素 ↔ 世界）。three.js PerspectiveCamera（fov＝垂直視角，16:9，1920×1080）。"""
import numpy as np, sys, json

def basis(pos, target):
    pos = np.array(pos, float); target = np.array(target, float)
    f = target - pos; f /= np.linalg.norm(f)
    up = np.array([0, 1.0, 0])
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return pos, f, r, u

def project(cam, p, W=1920, H=1080):
    pos, f, r, u = basis(cam['pos'], cam['target'])
    d = np.array(p, float) - pos
    z = d @ f; x = d @ r; y = d @ u
    th = np.tan(np.radians(cam['fov']) / 2)
    return (W / 2 + x / (z * th) * (H / 2), H / 2 - y / (z * th) * (H / 2))

def unproject(cam, px, py, zplane=0.0, W=1920, H=1080):
    pos, f, r, u = basis(cam['pos'], cam['target'])
    th = np.tan(np.radians(cam['fov']) / 2)
    nx = (px - W / 2) / (H / 2) * th; ny = -(py - H / 2) / (H / 2) * th
    d = f + nx * r + ny * u
    s = (zplane - pos[2]) / d[2]
    return pos + s * d

def ppu(cam, p):
    """p 附近每世界單位幾 px"""
    a = np.array(project(cam, p)); b = np.array(project(cam, np.array(p) + [0.01, 0, 0]))
    return np.linalg.norm(b - a) / 0.01

if __name__ == '__main__':
    cam = json.loads(sys.argv[1])
    if sys.argv[2] == 'u':
        print(unproject(cam, float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]) if len(sys.argv) > 5 else 0.0))
    else:
        p = json.loads(sys.argv[3]); print(project(cam, p), ppu(cam, p))
