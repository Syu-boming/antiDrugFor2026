import subprocess, sys, numpy as np
src, out = sys.argv[1], sys.argv[2]
W, H = 640, 360
cmd = ['ffmpeg', '-v', 'error', '-i', src, '-vf', f'scale={W}:{H}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
lut = np.arange(256) / 255.0
lut = np.where(lut <= 0.04045, lut / 12.92, ((lut + 0.055) / 1.055) ** 2.4)
full, cells, red = [], [], []
fs = W * H * 3
while True:
    b = p.stdout.read(fs)
    if len(b) < fs:
        break
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
    lin = lut[f]
    Y = lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722
    full.append(Y.mean())
    cells.append(Y.reshape(18, 20, 32, 20).mean(axis=(1, 3)))
    s = f.astype(np.int32).sum(-1)
    rr = np.where(s > 0, f[..., 0] / np.maximum(s, 1), 0)
    redmask = (rr >= 0.8) & (f[..., 0] > 60)
    red.append(redmask.reshape(18, 20, 32, 20).mean(axis=(1, 3)))
np.savez_compressed(out, full=np.array(full), cells=np.array(cells), red=np.array(red))
print(out, len(full))
