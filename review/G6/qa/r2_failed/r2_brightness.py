# G6 第 2 輪重驗（驗不通過項）自抽：九段播放錄製逐格全畫面亮度。
# (1) 孤立單格全畫面亮度比：相鄰兩格全畫面平均線性亮度（sRGB→線性、Rec.709）比 >1.2，
#     且前一格與後一格的變化都 <該跳變的 25% → 孤立硬切（主線裁定 >20% 不得一格硬切）。
# (2) 非孤立的單格大跳變（不管前後格，相鄰兩格比 >1.2、兩格都 >0.05）也列出，人工判讀是不是漸變中的切換。
# (3) 黑場：gamma 亮度（Rec.601，0–255）YAVG <25 的連續格算一次黑場（同導演視角 black_dips 的門檻）；
#     列出每次黑場的位置，以及 3 秒內連續兩次黑場。
# 解碼解析度 320×180（area），和驗收包 128×72 不同，作為獨立方法。不使用任何舊快取。
import subprocess, sys, json, numpy as np
ROOT = '/Users/boming/Documents/AI tool/反毒小劇場'
W, H = 320, 180
OUT = ROOT + '/review/G6/qa/r2_failed/'

def decode(path):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={W}:{H}:flags=area',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = W * H * 3; lin = []; yg = []
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        x = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        yg.append(float((0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]).mean() * 255))
        l = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
        lin.append(float((0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]).mean()))
    p.wait()
    return np.array(lin), np.array(yg)

def cue_at(sched, t):
    cur = None
    for c in sched:
        if t + 1e-6 >= c['start'] - c.get('preroll', 0): cur = c
    return (cur['id'], round(t - cur['start'], 2)) if cur else ('?', t)

res = {}
for seg in sys.argv[1:]:
    tl = json.load(open(f'{ROOT}/review/G5/{seg}/pack/timeline.json'))
    sched = tl['schedule']
    m, yg = decode(f'{ROOT}/review/G5/{seg}/pack/{seg}_playback.mp4')
    np.save(f'{OUT}{seg}_lin.npy', m); np.save(f'{OUT}{seg}_yavg.npy', yg)
    d = np.diff(m)
    iso, big = [], []
    for i in range(len(d)):
        a, b = m[i], m[i + 1]
        if max(a, b) <= 0.05: continue
        r = max(a, b) / max(min(a, b), 1e-4)
        if r < 1.06: continue
        pd = d[i - 1] if i > 0 else 0.0
        nd = d[i + 1] if i + 1 < len(d) else 0.0
        isolated = abs(pd) < 0.25 * abs(d[i]) and abs(nd) < 0.25 * abs(d[i])
        t = (i + 1) / 30
        cid, ct = cue_at(sched, t)
        row = {'frame': i + 1, 't': round(t, 3), 'cue': cid, 'cue_t': ct, 'before': round(float(a), 4),
               'after': round(float(b), 4), 'ratio': round(float(r), 3), 'isolated': bool(isolated),
               'prev_d': round(float(pd), 4), 'next_d': round(float(nd), 4)}
        if isolated: iso.append(row)
        if r > 1.2: big.append(row)
    # 黑場
    black = yg < 25
    runs = []; i = 0
    while i < len(black):
        if black[i]:
            j = i
            while j + 1 < len(black) and black[j + 1]: j += 1
            t0 = i / 30; cid, ct = cue_at(sched, t0)
            runs.append({'start_t': round(t0, 2), 'end_t': round((j + 1) / 30, 2), 'frames': j - i + 1,
                         'cue': cid, 'cue_t': ct, 'min_yavg': round(float(yg[i:j + 1].min()), 1)})
            i = j + 1
        else: i += 1
    double = [[a['cue'], a['start_t'], b['start_t']] for a, b in zip(runs, runs[1:])
              if b['start_t'] - a['end_t'] < 3.0]
    res[seg] = {'frames': len(m), 'max_isolated_ratio': max([r['ratio'] for r in iso], default=1.0),
                'max_isolated': max(iso, key=lambda r: r['ratio']) if iso else None,
                'isolated_over_1.2': [r for r in iso if r['ratio'] > 1.2],
                'isolated_ge_1.10': [r for r in iso if r['ratio'] >= 1.10],
                'nonisolated_single_frame_over_1.2': [r for r in big if not r['isolated']],
                'black_dips': len(runs), 'black_runs': runs, 'double_black_within_3s': double}
    print(seg, len(m), 'maxiso', res[seg]['max_isolated_ratio'], 'iso>1.2', len(res[seg]['isolated_over_1.2']),
          'big-noniso', len(res[seg]['nonisolated_single_frame_over_1.2']), 'black', len(runs), 'double', double, flush=True)
json.dump(res, open(OUT + 'r2_brightness.json', 'w'), ensure_ascii=False, indent=1)
