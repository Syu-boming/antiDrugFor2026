import sys, json, numpy as np
S = sys.argv[1]
act = sys.argv[2]
tl = sys.argv[3] if len(sys.argv) > 3 else None
d = np.load(f'{S}/{act}.npz')
full, cells, red = d['full'], d['cells'], d['red']
fps = 30.0
sched = json.load(open(tl))['schedule'] if tl else []

def cue_at(t):
    best = None
    for c in sched:
        if t >= c['start'] - c.get('preroll', 0) - 0.001:
            best = c
    if not best:
        return '-', 0
    return best['id'], t - best['start']

# 1. full-frame one-frame jumps
print(f'== {act} frames {len(full)}  full-frame one-frame jumps (rel>20%, abs>=0.02) ==')
for i in range(1, len(full)):
    a, b = full[i - 1], full[i]
    lo, hi = min(a, b), max(a, b)
    if hi - lo >= 0.02 and hi / max(lo, 1e-4) > 1.2:
        t = i / fps
        cid, ct = cue_at(t)
        # context: 0.3s before/after mean
        print(f'  t={t:7.3f} {cid} cue_t={ct:6.2f}  {a:.3f}->{b:.3f}  ratio={hi/max(lo,1e-4):.2f}')
# also largest relative one-frame jumps overall
rel = np.array([max(full[i], full[i-1]) / max(min(full[i], full[i-1]), 1e-4) for i in range(1, len(full))])
absd = np.abs(np.diff(full))
idx = np.argsort(-absd)[:6]
print('  top abs one-frame deltas:', [(round((i+1)/fps, 3), round(float(full[i]), 3), round(float(full[i+1]), 3)) for i in idx])

# 2. fine 32x18 transitions per 1s window
def transitions(series, thr=0.1, dark=0.8):
    ev = []
    ext = series[0]; direction = 0
    lastext = series[0]
    for i in range(1, len(series)):
        v = series[i]
        if direction >= 0 and v > ext:
            ext = v
        if direction <= 0 and v < ext:
            ext = v
        # check reversal relative to running extreme
        if direction == 0:
            if abs(v - series[0]) >= thr and min(v, series[0]) < dark:
                direction = 1 if v > series[0] else -1
                ev.append(i); ext = v
        elif direction == 1:
            if ext - v >= thr and min(ext, v) < dark:
                ev.append(i); direction = -1; ext = v
            elif v > ext:
                ext = v
        else:
            if v - ext >= thr and min(ext, v) < dark:
                ev.append(i); direction = 1; ext = v
            elif v < ext:
                ext = v
    return ev

W = int(fps)
maxc = 0; worst = []
counts = {}
for y in range(18):
    for x in range(32):
        ev = transitions(cells[:, y, x])
        ev = np.array(ev)
        m = 0; ws = None
        for k in range(len(ev)):
            n = np.sum((ev >= ev[k]) & (ev < ev[k] + W))
            if n > m:
                m = n; ws = ev[k]
        counts[(x, y)] = (m, ws)
        if m > maxc:
            maxc = m
hist = {}
for k, (m, ws) in counts.items():
    hist[m] = hist.get(m, 0) + 1
print(f'  fine32x18 luma transitions/sec max={maxc}; histogram={dict(sorted(hist.items()))}')
for k, (m, ws) in sorted(counts.items(), key=lambda kv: -kv[1][0])[:8]:
    if m >= 3:
        t = ws / fps; cid, ct = cue_at(t)
        print(f'    cell x{k[0]}_y{k[1]} n={m} window_start={t:.3f} {cid} cue_t={ct:.2f}')
