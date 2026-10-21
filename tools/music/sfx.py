# -*- coding: utf-8 -*-
"""反毒剪紙劇場｜音效程式合成（全部原創，numpy／scipy）。

原則（CLAUDE.md 第 9 條、v1.2 §20.3）：起音 ≥ 5 ms、不刺耳（高頻都做低通）、沒有突發巨響；
紙繩繃緊不可陰森（不用低頻長音、不用不協和持續音）。
每個函式回傳單聲道 float64（48 kHz），尚未正規化；音量統一在 build_all.py 處理。
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

from common import SR

RNG_SEED = 2026


def _rng(k: int) -> np.random.Generator:
    return np.random.default_rng(RNG_SEED + k)


def secs(t: float) -> int:
    return int(round(t * SR))


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype='bandpass', fs=SR, output='sos')
    return sosfiltfilt(sos, x)


def lp(x, f, order=2):
    return sosfiltfilt(butter(order, f, btype='lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfiltfilt(butter(order, f, btype='highpass', fs=SR, output='sos'), x)


def pink(n, rng):
    """近似粉紅雜訊（Voss 濾波法）。"""
    w = rng.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    from scipy.signal import lfilter
    y = lfilter(b, a, w)
    return y / (np.std(y) + 1e-12)


def env_points(n, pts):
    """分段升餘弦包絡；pts = [(秒, 振幅), ...]。"""
    e = np.zeros(n)
    t = np.arange(n) / SR
    for (t0, a0), (t1, a1) in zip(pts[:-1], pts[1:]):
        m = (t >= t0) & (t < t1)
        if t1 > t0:
            u = (t[m] - t0) / (t1 - t0)
            e[m] = a0 + (a1 - a0) * (0.5 - 0.5 * np.cos(np.pi * u))
    e[t >= pts[-1][0]] = pts[-1][1]
    return e


def grain(rng, dur_ms, lo, hi, rise_ms=2.0):
    """一顆紙張「沙」粒：帶通雜訊＋升餘弦起音＋指數衰減。"""
    n = max(8, int(dur_ms * SR / 1000))
    g = rng.standard_normal(n)
    g = bp(np.concatenate([np.zeros(64), g, np.zeros(64)]), lo, hi)[64:-64]
    nr = max(2, int(rise_ms * SR / 1000))
    e = np.exp(-np.arange(n) / (n / 3.5))
    e[:nr] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return g * e


def scatter(n, rng, rate_env, lo, hi, dur_ms=(4, 14), amp=(0.3, 1.0), rise_ms=2.0):
    """依密度包絡（每秒顆數）撒紙張顆粒。"""
    out = np.zeros(n)
    dt = 0.002
    for i in range(int(n / (dt * SR))):
        idx = int(i * dt * SR)
        if rng.random() < rate_env[idx] * dt:
            g = grain(rng, rng.uniform(*dur_ms), lo * rng.uniform(0.85, 1.15), hi * rng.uniform(0.85, 1.1), rise_ms)
            g *= rng.uniform(*amp)
            e = min(n, idx + len(g))
            out[idx:e] += g[:e - idx]
    return out


def onset(x, ms=8.0, tail_ms=10.0):
    """整體起音：升餘弦淡入（保證 ≥ 5 ms）＋ 尾端淡出到零。"""
    y = x.copy()
    k = int(ms * SR / 1000)
    y[:k] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k))
    j = int(tail_ms / 1000 * SR)
    y[-j:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, j))
    return y


def soft_thud(n, t0, f0=150, f1=90, decay=0.09, rise_ms=8, amp=1.0):
    """柔和的低頻「咚」：下滑正弦、慢起音，不是重擊。"""
    out = np.zeros(n)
    i0 = secs(t0)
    m = min(n - i0, secs(decay * 6))
    t = np.arange(m) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = np.exp(-t / decay)
    r = int(rise_ms * SR / 1000)
    e[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
    out[i0:i0 + m] += amp * np.sin(ph) * e
    return out


# ---------------------------------------------------------------- 布幕
def _curtain(direction: int, k: int):
    rng = _rng(k)
    dur = 2.3
    n = secs(dur)
    t = np.arange(n) / SR
    # 布面摩擦：粉紅雜訊、移動的帶通（開：中心往上；合：往下）
    base = pink(n, rng)
    motion = env_points(n, [(0, 0), (0.30, 0.85), (0.9, 1.0), (1.5, 0.8), (2.0, 0.25), (2.3, 0.0)])
    # 時變帶通：切成 20 ms 小段近似
    out = np.zeros(n)
    hop = secs(0.02)
    win = np.hanning(2 * hop)
    for s0 in range(0, n - 2 * hop, hop):
        u = s0 / n
        fc = (500 + 900 * u) if direction > 0 else (1400 - 900 * u)
        seg = base[s0:s0 + 2 * hop]
        out[s0:s0 + 2 * hop] += bp(np.pad(seg, 256), fc * 0.55, fc * 1.6)[256:-256] * win
    body = out * motion * (1 + 0.12 * np.sin(2 * np.pi * 3.1 * t))
    # 摺層紙布幕的細碎紙聲
    rate = 18 + 40 * motion
    crk = scatter(n, rng, rate, 1500, 5200, amp=(0.15, 0.5))
    crk = lp(crk, 6500) * motion
    # 布幕停住：很輕的布面落定（無重擊）
    settle = soft_thud(n, 2.02 if direction > 0 else 1.98, f0=180, f1=110, decay=0.07, rise_ms=10, amp=0.25)
    x = 1.0 * body + 0.55 * crk + settle
    x = lp(hp(x, 90), 7000)
    return onset(x, 12)


def sfx_curtain_open():
    return _curtain(+1, 1)


def sfx_curtain_close():
    return _curtain(-1, 2)


# ---------------------------------------------------------------- 紙張
def sfx_paper_rustle():
    rng = _rng(3)
    n = secs(1.3)
    dens = env_points(n, [(0, 0), (0.08, 70), (0.35, 120), (0.55, 40), (0.7, 110), (1.0, 60), (1.3, 0)])
    crk = scatter(n, rng, dens, 1200, 5500, dur_ms=(5, 18), amp=(0.2, 0.9))
    body = bp(pink(n, rng), 400, 2500) * env_points(n, [(0, 0), (0.1, 0.3), (0.4, 0.4), (0.6, 0.15), (0.8, 0.35), (1.3, 0)])
    x = lp(0.8 * crk + body, 6500)
    return onset(x, 10)


def sfx_fold():
    """折折摺紙：三下乾淨的摺痕聲。"""
    rng = _rng(4)
    n = secs(0.95)
    x = np.zeros(n)
    for i, (t0, fc) in enumerate(((0.02, 2400), (0.28, 2800), (0.54, 3200))):
        i0 = secs(t0)
        m = secs(0.11)
        dens = env_points(m, [(0, 0), (0.006, 700), (0.03, 500), (0.11, 0)])
        c = scatter(m, rng, dens, fc * 0.5, fc * 1.9, dur_ms=(3, 9), amp=(0.4, 1.0), rise_ms=1.5)
        crease = bp(rng.standard_normal(m), 700, 2200) * env_points(m, [(0, 0), (0.007, 0.5), (0.04, 0.2), (0.11, 0)])
        cl = (c + crease) * env_points(m, [(0, 0), (0.007, 1), (0.11, 1)])
        x[i0:i0 + m] += cl * (1.0 - 0.1 * i)
    x = lp(x, 6800)
    return onset(x, 7)


def sfx_card_in():
    """題卡摺開送上：兩下展開摺痕 → 輕輕滑入 → 落定。"""
    rng = _rng(5)
    n = secs(1.35)
    x = np.zeros(n)
    for t0 in (0.02, 0.2):
        i0 = secs(t0)
        m = secs(0.12)
        dens = env_points(m, [(0, 0), (0.008, 500), (0.12, 0)])
        c = scatter(m, rng, dens, 1300, 4800, dur_ms=(4, 12), amp=(0.3, 0.9))
        x[i0:i0 + m] += c * env_points(m, [(0, 0), (0.008, 1), (0.12, 1)])
    # 滑入：帶通雜訊由低往高掃（輕）
    i0 = secs(0.42)
    m = secs(0.62)
    w = pink(m, rng)
    sl = np.zeros(m)
    hop = secs(0.02)
    win = np.hanning(2 * hop)
    for s0 in range(0, m - 2 * hop, hop):
        fc = 450 + 900 * s0 / m
        sl[s0:s0 + 2 * hop] += bp(np.pad(w[s0:s0 + 2 * hop], 256), fc * 0.6, fc * 1.7)[256:-256] * win
    sl *= env_points(m, [(0, 0), (0.2, 0.55), (0.45, 0.4), (0.62, 0)])
    x[i0:i0 + m] += sl
    x += soft_thud(n, 1.02, f0=220, f1=140, decay=0.05, rise_ms=8, amp=0.22)
    x = lp(hp(x, 100), 6800)
    return onset(x, 8)


# ---------------------------------------------------------------- 操偶線（紙繩）
def sfx_string_drop():
    """一根紙繩落下的輕沙沙＋紙環輕扣（扣上點在 0.50 s）。每根線觸發一次。"""
    rng = _rng(6)
    n = secs(1.0)
    t = np.arange(n) / SR
    # 落下：細紙繩擦過空氣與紙面，0.05–0.48 s 漸強的細沙聲
    fall_env = env_points(n, [(0, 0), (0.05, 0.05), (0.40, 0.55), (0.48, 0.6), (0.52, 0.05), (0.7, 0)])
    hiss = bp(pink(n, rng), 1800, 5200) * fall_env * 0.35
    dens = env_points(n, [(0, 0), (0.1, 15), (0.45, 60), (0.5, 0)])
    crk = scatter(n, rng, dens, 1600, 4800, dur_ms=(3, 8), amp=(0.1, 0.35))
    # 紙環輕扣：中頻紙聲短促一下＋很輕的紙板共鳴（起音 6 ms）
    i0 = secs(0.50)
    m = secs(0.12)
    tick = bp(rng.standard_normal(m), 900, 3200) * env_points(m, [(0, 0), (0.006, 1.0), (0.025, 0.35), (0.12, 0)])
    tt = np.arange(m) / SR
    res = np.sin(2 * np.pi * 520 * tt) * np.exp(-tt / 0.03)
    res[:secs(0.006)] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, secs(0.006)))
    clasp = np.zeros(n)
    clasp[i0:i0 + m] = 0.6 * tick + 0.25 * res
    x = lp(hiss + crk + clasp, 6500)
    return onset(x, 10)


def sfx_string_taut():
    """紙繩繃緊：短短一下輕微的紙張拉緊聲（中頻窄帶雜訊往上滑），不陰森、不留長音。"""
    rng = _rng(7)
    n = secs(0.75)
    w = pink(n, rng)
    out = np.zeros(n)
    hop = secs(0.015)
    win = np.hanning(2 * hop)
    for s0 in range(0, n - 2 * hop, hop):
        u = s0 / n
        fc = 900 + 700 * min(1, u * 1.6)
        out[s0:s0 + 2 * hop] += bp(np.pad(w[s0:s0 + 2 * hop], 256), fc * 0.6, fc * 1.7)[256:-256] * win
    e = env_points(n, [(0, 0), (0.12, 0.6), (0.30, 1.0), (0.40, 0.5), (0.75, 0)])
    dens = env_points(n, [(0, 0), (0.15, 30), (0.32, 70), (0.45, 8), (0.75, 0)])
    crk = scatter(n, rng, dens, 1500, 4200, dur_ms=(3, 7), amp=(0.1, 0.3))
    x = lp(hp(0.7 * out * e + crk, 300), 6000)
    return onset(x, 15)


# ---------------------------------------------------------------- 燈、印章、收聲
def _bell(n, t0, f, amp=1.0, tau=0.9, rise_ms=14):
    """溫暖小鈴：諧和泛音為主，少量非諧和泛音，高泛音衰減快。"""
    out = np.zeros(n)
    i0 = secs(t0)
    m = n - i0
    t = np.arange(m) / SR
    partials = [(1.0, 1.0, tau), (2.0, 0.28, tau * 0.55), (3.0, 0.10, tau * 0.35), (2.76, 0.06, tau * 0.3), (4.1, 0.03, tau * 0.2)]
    y = np.zeros(m)
    for ratio, a, tt in partials:
        y += a * np.sin(2 * np.pi * f * ratio * t + ratio) * np.exp(-t / tt)
    r = int(rise_ms * SR / 1000)
    y[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
    out[i0:] += amp * y
    return out


def sfx_lamp_on():
    """點燈：溫暖輕鈴兩聲（A5 → D6，上行四度），加一點紙燈籠的暖光「呼」。"""
    rng = _rng(8)
    n = secs(3.4)
    x = _bell(n, 0.0, 880.0, 1.0, tau=0.7) + _bell(n, 0.16, 1174.66, 0.7, tau=0.62)
    glow = bp(pink(n, rng), 300, 1400) * env_points(n, [(0, 0), (0.25, 0.05), (0.8, 0.04), (1.6, 0)])
    x = lp(x + glow, 7000)
    return onset(x, 14, tail_ms=400)


def sfx_stamp():
    """「正解」紙印章：柔和的一聲（低中頻「噗」＋紙面接觸），之後輕輕抬起。"""
    rng = _rng(9)
    n = secs(0.75)
    x = soft_thud(n, 0.0, f0=170, f1=95, decay=0.07, rise_ms=14, amp=0.9)
    m = secs(0.12)
    contact = bp(rng.standard_normal(m), 300, 2200) * env_points(m, [(0, 0), (0.014, 0.6), (0.04, 0.2), (0.12, 0)])
    x[:m] += contact
    lift_i = secs(0.32)
    lm = secs(0.2)
    lift = bp(pink(lm, rng), 1200, 4000) * env_points(lm, [(0, 0), (0.05, 0.12), (0.2, 0)])
    x[lift_i:lift_i + lm] += lift
    x = lp(hp(x, 60), 5000)
    return onset(x, 14)


def sfx_quiet_fold():
    """S3 折折收摺音效（收聲訊號）：兩下摺紙＋輕柔下行兩音（D6 → A5）。"""
    n = secs(2.8)
    f = sfx_fold()[:secs(0.5)]
    x = np.zeros(n)
    x[:len(f)] += f * 0.9
    x += _bell(n, 0.55, 1174.66, 0.55, tau=0.5) + _bell(n, 0.80, 880.0, 0.6, tau=0.55)
    x = lp(x, 7000)
    return onset(x, 7, tail_ms=400)


# ================================================================ G5 新增（S6–S16）
# 可循環的環境聲（風、校門口、廣場人聲、電話底音）全部「週期性合成」：
#   雜訊在頻域直接生成長度 L 的週期訊號（irfft），事件（鳥叫、人聲音節、車經過）超過檔尾就繞回檔頭，
#   殘響用循環摺積，包絡也是週期函數 → 檔尾接回檔頭逐樣本連續（不靠交叉淡化）。
#   接縫處刻意放在「低谷」：檔頭從約 −12～−20 dB 慢慢起來（1–2 秒），所以從靜音直接開始播也不會突然冒出來。
# 人聲遠景只用母音共振峰合成（沒有子音），多人重疊、低通、加殘響 → 聽不出任何字。

def periodic_noise(L, rng, lo=20.0, hi=20000.0, tilt_db_oct=-3.0, order=4):
    """長度 L 樣本的週期雜訊：頻域給幅度（每八度 tilt dB，lo–hi 外 order 階滾降，4 階 ≈ 24 dB／八度）與隨機相位。"""
    f = np.fft.rfftfreq(L, 1 / SR)
    ff = np.maximum(f, 1.0)
    mag = (ff / 1000.0) ** (tilt_db_oct / 6.0206)
    mag *= 1 / np.sqrt(1 + (lo / ff) ** (2 * order)) / np.sqrt(1 + (ff / hi) ** (2 * order))
    mag[0] = 0
    ph = rng.uniform(0, 2 * np.pi, len(f))
    x = np.fft.irfft(mag * np.exp(1j * ph), n=L)
    return x / (np.std(x) + 1e-12)


def periodic_lfo(L, rng, max_hz=0.3, depth=1.0):
    """週期性的慢變化（只含 ≤ max_hz 的頻率分量），回傳均值 0、標準差 depth。"""
    k = max(1, int(max_hz * L / SR))
    spec = np.zeros(L // 2 + 1, complex)
    spec[1:k + 1] = rng.standard_normal(k) + 1j * rng.standard_normal(k)
    spec[1:k + 1] /= np.arange(1, k + 1) ** 0.5
    x = np.fft.irfft(spec, n=L)
    return x / (np.std(x) + 1e-12) * depth


def seam_lull(L, depth_db=-14.0, rise=1.5):
    """週期包絡：接縫（t=0 = t=L）處低到 depth_db，前後 rise 秒升餘弦回到 1。"""
    t = np.arange(L) / SR
    T = L / SR
    d = np.minimum(t, T - t)                     # 到接縫的距離（秒）
    g = 10 ** (depth_db / 20)
    u = np.clip(d / rise, 0, 1)
    return g + (1 - g) * (0.5 - 0.5 * np.cos(np.pi * u))


def circ_reverb(x, rng, rt=1.2, wet=0.5, pre_ms=12.0, lp_hz=3500.0):
    """循環摺積殘響（週期訊號用；長度不變）。"""
    L = len(x)
    n = min(L, secs(rt * 1.6))
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / rt)
    ir = lp(ir, lp_hz)
    ir[:secs(pre_ms / 1000)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-12
    h = np.zeros(L)
    h[:n] = ir
    y = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(h), n=L)
    return (1 - wet) * x + wet * y * (np.std(x) / (np.std(y) + 1e-12))


def add_wrap(out, seg, i0):
    """把 seg 加到週期緩衝 out 的 i0 位置，超過檔尾的部分繞回檔頭。"""
    L = len(out)
    i0 %= L
    m = len(seg)
    e = min(L, i0 + m)
    out[i0:e] += seg[:e - i0]
    if i0 + m > L:
        rest = seg[e - i0:]
        out[:len(rest)] += rest[:L]


# 母音共振峰（成人，Hz）：a、i、u、e、o 的近似值
_VOWELS = [(750, 1200, 2500), (330, 2100, 2800), (350, 850, 2300), (480, 1800, 2550), (480, 900, 2450)]


def _syllable(rng, dur, f0, fshift):
    m = secs(dur)
    t = np.arange(m) / SR
    f = f0 * (1 + 0.06 * np.sin(np.pi * t / dur + rng.uniform(-1, 1)) + rng.uniform(-0.04, 0.04))
    ph = 2 * np.pi * np.cumsum(f) / SR
    src = np.zeros(m)
    for h in range(1, 14):                       # 有限諧波的鋸齒波（聲門脈衝近似）
        src += np.sin(h * ph) / h
    src += 0.15 * rng.standard_normal(m)
    v0 = _VOWELS[rng.integers(len(_VOWELS))]
    y = np.zeros(m)
    for k, (fc, a) in enumerate(zip(v0, (1.0, 0.6, 0.25))):
        fc *= fshift
        bw = 90 + 40 * k
        sos = butter(2, [max(80, fc - bw), min(SR / 2 - 100, fc + bw)], btype='bandpass', fs=SR, output='sos')
        y += a * sosfilt(sos, src)
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return y * e


def babble(L, rng, voices=10, f0=(100, 240), fshift=(1.0, 1.25), talk=0.55, level_jitter=6.0):
    """L 樣本長的週期「人聲遠景」：多人各自說話（母音音節串、句間停頓），沒有子音、聽不出字。"""
    out = np.zeros(L)
    T = L / SR
    for v in range(voices):
        vb = np.zeros(L)
        base_f0 = rng.uniform(*f0)
        fs_ = rng.uniform(*fshift)
        amp = 10 ** (-rng.uniform(0, level_jitter) / 20)
        t = rng.uniform(0, T)
        t_end = t + T                             # 每個聲音繞一整圈
        while t < t_end:
            if rng.random() > talk:
                t += rng.uniform(0.8, 2.5)
                continue
            for _ in range(int(rng.integers(3, 10))):
                d = rng.uniform(0.11, 0.24)
                syl = _syllable(rng, d, base_f0 * rng.uniform(0.9, 1.15), fs_) * rng.uniform(0.5, 1.0)
                add_wrap(vb, syl, secs(t))
                t += d + rng.uniform(0.0, 0.06)
            t += rng.uniform(0.3, 1.0)
        out += amp * vb / (np.std(vb) + 1e-12)
    return out / (np.std(out) + 1e-12)


def _chirp(rng, f_start, f_end, dur, rise_ms=6):
    m = secs(dur)
    t = np.arange(m) / SR
    f = f_start + (f_end - f_start) * (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    r = int(rise_ms * SR / 1000)
    e[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
    return (np.sin(ph) + 0.15 * np.sin(2 * ph)) * e


# ---------------------------------------------------------------- S6 風鈴
def sfx_windchime():
    """店門風鈴：五支金屬管（A5 B5 D6 E6 F#6，D 大調五聲）被門輕碰，8 下逐漸變輕；
    管樂器泛音比 1：2.756：5.404，高泛音衰減快、整體低通 6.5 kHz，不刺耳。第一下在 0.02 s。"""
    rng = _rng(16)
    n = secs(4.2)
    t = np.arange(n) / SR
    tubes = [880.0, 987.77, 1174.66, 1318.51, 1479.98]
    hits = [(0.02, 1.0), (0.11, 0.8), (0.21, 0.75), (0.35, 0.6), (0.52, 0.5), (0.76, 0.38), (1.08, 0.28), (1.52, 0.18)]
    x = np.zeros(n)
    last = -1
    for t0, a in hits:
        k = int(rng.integers(len(tubes)))
        if k == last:
            k = (k + 2) % len(tubes)
        last = k
        f = tubes[k] * rng.uniform(0.997, 1.003)
        i0 = secs(t0)
        tt = t[:n - i0]
        y = (np.sin(2 * np.pi * f * tt) * np.exp(-tt / 1.3)
             + 0.35 * np.sin(2 * np.pi * f * 2.756 * tt + 0.7) * np.exp(-tt / 0.45)
             + 0.08 * np.sin(2 * np.pi * f * 5.404 * tt + 1.3) * np.exp(-tt / 0.18))
        r = secs(0.012)
        y[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
        x[i0:] += a * y
    x = lp(hp(x, 300), 6500)
    return onset(x, 6, tail_ms=600)


# ---------------------------------------------------------------- S7 竹篾輕落地
def sfx_bamboo_drop():
    """細竹篾落到工作台／地板：一下輕脆的「答」＋三次越來越小的彈跳（0.00／0.13／0.22／0.28 s），
    木質模態（約 520／1350／2400 Hz）短衰減，最後很輕的滾動。起音 14 ms（量測 ≥ 5 ms），不是重擊。"""
    rng = _rng(17)
    n = secs(1.0)
    x = np.zeros(n)
    modes = [(520, 0.055, 1.0), (1350, 0.03, 0.55), (2400, 0.018, 0.3), (3300, 0.012, 0.12)]
    for t0, a in ((0.0, 1.0), (0.13, 0.45), (0.22, 0.24), (0.28, 0.12)):
        i0 = secs(t0 + 0.01)
        m = secs(0.35)
        tt = np.arange(m) / SR
        y = np.zeros(m)
        for f, tau, g in modes:
            y += g * np.sin(2 * np.pi * f * rng.uniform(0.98, 1.02) * tt + rng.uniform(0, 6)) * np.exp(-tt / tau)
        burst = bp(rng.standard_normal(m), 600, 3500) * np.exp(-tt / 0.008)
        y = y + 0.4 * burst
        r = secs(0.014)
        y[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
        e = min(n, i0 + m)
        x[i0:e] += a * y[:e - i0]
    x += soft_thud(n, 0.01, f0=190, f1=130, decay=0.03, rise_ms=14, amp=0.25)
    dens = env_points(n, [(0, 0), (0.30, 0), (0.33, 60), (0.5, 20), (0.6, 0)])
    x += scatter(n, rng, dens, 900, 3000, dur_ms=(3, 8), amp=(0.03, 0.08), rise_ms=2.0)
    x = lp(hp(x, 120), 6000)
    return onset(x, 6, tail_ms=80)


# ---------------------------------------------------------------- S8 風聲（可循環）
WIND_LOOP = 30.0


def sfx_wind():
    """柔和的風（30.0 s 可循環）：低中頻氣流聲＋一點高頻沙沙，慢慢起伏；不呼嘯、沒有口哨聲。
    檔頭從低谷起來（約 1.5 s），3.0 s 前後一陣較明顯的風（可對「包裝紙被吹來」），之後平穩起伏。"""
    rng = _rng(18)
    L = secs(WIND_LOOP)
    body = periodic_noise(L, rng, lo=90, hi=1300, tilt_db_oct=-4.5)
    air = periodic_noise(L, rng, lo=700, hi=3200, tilt_db_oct=-3.0)
    lfo = periodic_lfo(L, rng, max_hz=0.25, depth=0.22)
    t = np.arange(L) / SR
    gust = np.exp(-0.5 * ((t - 3.0) / 0.8) ** 2)            # 3.0 s 一陣風
    e_body = np.clip(0.7 + lfo + 0.8 * gust, 0.25, 1.8)
    e_air = np.clip(0.5 + 0.8 * lfo + 1.0 * gust, 0.1, 1.8)
    x = body * e_body + 0.32 * air * e_air
    # 落葉／紙屑的細沙（週期擺放），很輕
    leaves = np.zeros(L)
    for _ in range(26):
        g = grain(rng, rng.uniform(4, 10), 1800, 4200) * rng.uniform(0.05, 0.14)
        add_wrap(leaves, g, int(rng.integers(L)))
    x = x + leaves * 6
    return x * seam_lull(L, -14.0, 1.5)


# ---------------------------------------------------------------- S9 下課鐘（柔）
def sfx_school_bell():
    """柔和的下課鐘：西敏寺鐘聲前兩句（1793 年旋律，公有領域；台灣校園常用），D 大調：
    F#5 D5 E5 A4｜A4 E5 F#5 D5，每音 0.6 s（第一句尾音 1.2 s），溫暖鐘聲音色、起音 12 ms、高泛音快衰減。
    第一音 0.05 s，第二句從 3.05 s，最後一音 4.85 s，約 6.5 s 餘響收完。"""
    n = secs(7.0)
    notes = [('F#5', 0.05), ('D5', 0.65), ('E5', 1.25), ('A4', 1.85), ('A4', 3.05), ('E5', 3.65), ('F#5', 4.25), ('D5', 4.85)]
    from common import n as midi
    x = np.zeros(n)
    for name, t0 in notes:
        f = 440.0 * 2 ** ((midi(name) - 69) / 12)
        x += _bell(n, t0, f, amp=0.8, tau=1.1, rise_ms=12)
    x = lp(hp(x, 200), 5500)
    return onset(x, 12, tail_ms=500)


# ---------------------------------------------------------------- S10 校門口環境聲（可循環）
GATE_LOOP = 40.0


def sfx_gate_ambience():
    """放學後的校門口遠景（40.0 s 可循環，低音量）：遠處車流的柔和底噪、偶爾一台車慢慢經過（不按喇叭、
    不煞車）、遠遠零星的小朋友說話聲（只有母音、聽不出字）、幾聲麻雀。檔頭從低谷約 1.5 s 起來。"""
    rng = _rng(19)
    L = secs(GATE_LOOP)
    t = np.arange(L) / SR
    traffic = periodic_noise(L, rng, lo=70, hi=900, tilt_db_oct=-4.0) * (0.8 + periodic_lfo(L, rng, 0.15, 0.12))
    # 車慢慢經過：寬頻雜訊、5–7 秒的鐘形包絡（週期擺放）
    cars = np.zeros(L)
    for c0 in (6.0, 21.0, 33.0):
        m = secs(7.0)
        tt = np.arange(m) / SR
        env = np.exp(-0.5 * ((tt - 3.5) / 1.3) ** 2)
        nz = bp(pink(m, rng), 120, 1600) * env
        add_wrap(cars, nz * 0.9, secs(c0))
    kids = babble(L, rng, voices=4, f0=(200, 320), fshift=(1.15, 1.3), talk=0.35)
    kids = lp(kids, 1500)
    kids = circ_reverb(kids, rng, rt=1.4, wet=0.6)
    birds = np.zeros(L)
    for b0 in (3.2, 3.5, 3.75, 15.4, 15.6, 27.9, 28.2, 28.4, 36.1):
        f1 = rng.uniform(2600, 3200)
        ch = _chirp(rng, f1, f1 * rng.uniform(0.75, 0.9), rng.uniform(0.05, 0.09))
        add_wrap(birds, ch * rng.uniform(0.5, 1.0), secs(b0))
    birds = circ_reverb(birds, rng, rt=0.8, wet=0.4, lp_hz=5000)
    x = traffic + 0.7 * cars + 0.45 * kids + 0.12 * birds
    x = x - np.mean(x)
    return x * seam_lull(L, -12.0, 1.5)


# ---------------------------------------------------------------- S11 兒童手錶撥號音（輕）
def sfx_watch_dial():
    """兒童手錶撥 119：三下輕按鍵嗶聲（0.10／0.42／0.74 s；「1」「1」用 A5，「9」用 C#6），
    1.25 s 一聲更輕的確認音（E6→A5 下行兩音）。純正弦＋少量二次諧波、起音 14 ms；不是電信撥號音（DTMF）。"""
    n = secs(2.2)
    x = np.zeros(n)

    def bip(t0, f, a, dur=0.12):
        i0 = secs(t0)
        m = secs(dur + 0.25)
        tt = np.arange(m) / SR
        y = (np.sin(2 * np.pi * f * tt) + 0.12 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt / (dur * 0.8))
        r = secs(0.014)
        y[:r] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
        x[i0:i0 + m] += a * y[:n - i0]

    for t0, f in ((0.10, 880.0), (0.42, 880.0), (0.74, 1108.73)):
        bip(t0, f, 1.0)
    bip(1.25, 1318.51, 0.45, 0.09)
    bip(1.40, 880.0, 0.45, 0.14)
    rng = _rng(20)
    for t0 in (0.10, 0.42, 0.74):                 # 很輕的按鍵觸感
        x[secs(t0):secs(t0) + secs(0.02)] += grain(rng, 20, 1500, 4000) * 0.12
    x = lp(x, 6000)
    return onset(x, 8, tail_ms=200)


# ---------------------------------------------------------------- S12 電話音色底音（可循環）
PHONE_LOOP = 40.0


def sfx_phone_bed():
    """119 通話時的「電話線」底音（40.0 s 可循環，很輕）：300–3400 Hz 窄頻的柔和線路雜音，慢慢起伏；
    不放任何電信業者的撥號音、回鈴音或忙線音。檔頭 0.8 s 從低谷起來（通話接通的感覺）。"""
    rng = _rng(21)
    L = secs(PHONE_LOOP)
    line = periodic_noise(L, rng, lo=300, hi=3400, tilt_db_oct=-2.0, order=12)
    warm = periodic_noise(L, rng, lo=300, hi=700, tilt_db_oct=-3.0, order=12)
    drift = 1.0 + periodic_lfo(L, rng, max_hz=0.2, depth=0.1)
    x = (line + 0.5 * warm) * drift
    return x * seam_lull(L, -20.0, 0.8)


# ---------------------------------------------------------------- S13 救護車引擎聲（無警笛）
def sfx_ambulance_engine():
    """救護車從遠處慢慢開近、停下、怠速（16.0 s；沒有警笛、喇叭、煞車尖響）。
    0–8.0 s 由約 120 m 開到 10 m（漸近、越近越慢，1 秒內響度上升 ≤ 約 6 dB）、8.0–9.0 s 停下（轉速下降）、
    9.0–14.5 s 怠速、14.5–16.0 s 淡出。引擎＝點火頻率諧波（約 42 → 28 Hz）＋路噪；遠時高頻少（空氣吸收）。"""
    rng = _rng(22)
    n = secs(16.0)
    t = np.arange(n) / SR
    # 距離：0–8 s ease-out（前段快、後段慢）
    u = np.clip(t / 8.0, 0, 1)
    s = 1 - (1 - u) ** 2.2
    dist = 120 - 110 * s
    speed = np.gradient(dist, 1 / SR) * -1          # m/s（正＝接近）
    doppler = 1 / (1 - np.clip(speed, 0, 30) / 343.0)
    rpm = 28 + 14 * np.clip(1 - (t - 7.0) / 2.0, 0, 1)   # 7–9 s 轉速降到怠速
    f = rpm * doppler
    ph = 2 * np.pi * np.cumsum(f) / SR
    jit = 1 + 0.08 * lp(rng.standard_normal(n), 40)
    eng = np.zeros(n)
    for h in range(1, 28):
        fc = 180.0
        a = 1 / (1 + ((h * 30 - fc) / 160.0) ** 2) * (1.0 if h % 2 else 0.7)
        eng += a * np.sin(h * ph + rng.uniform(0, 6))
    eng *= jit
    road = bp(pink(n, rng), 150, 1600) * np.clip(speed / 12.0, 0, 1) * 0.6
    near = eng + road
    far = lp(near, 700)
    w = np.clip((120 - dist) / 110, 0, 1)            # 越近越亮
    x = far * (1 - w) + near * w
    g = 10.0 / dist                                  # 1/r
    x = x * g
    x = hp(x, 45)
    x = lp(x, 4000)
    e = env_points(n, [(0, 0), (0.6, 1), (14.5, 1), (16.0, 0)])
    return onset(x * e, 30, tail_ms=50)


# ---------------------------------------------------------------- S14 紙飛機咻聲（輕）
def sfx_plane_whoosh():
    """紙飛機飛過（1.6 s，輕）：帶通氣流聲中心頻率 600 → 1900（0.6 s 最近）→ 900 Hz，鐘形包絡；
    加一點紙翼的細沙聲。沒有尖銳高頻（低通 6 kHz）。"""
    rng = _rng(23)
    n = secs(1.6)
    w = pink(n, rng)
    out = np.zeros(n)
    hop = secs(0.015)
    win = np.hanning(2 * hop)
    for s0 in range(0, n - 2 * hop, hop):
        u = s0 / SR
        fc = 600 + 1300 * np.exp(-0.5 * ((u - 0.6) / 0.28) ** 2) + 300 * (u > 0.6) * (u - 0.6)
        out[s0:s0 + 2 * hop] += bp(np.pad(w[s0:s0 + 2 * hop], 256), fc * 0.6, fc * 1.6)[256:-256] * win
    e = env_points(n, [(0, 0), (0.25, 0.35), (0.6, 1.0), (0.95, 0.35), (1.55, 0)])
    dens = env_points(n, [(0, 0), (0.3, 20), (0.6, 50), (0.9, 15), (1.3, 0)])
    crk = scatter(n, rng, dens, 1500, 4500, dur_ms=(3, 7), amp=(0.05, 0.15))
    x = lp(hp(out * e + crk * e, 250), 6000)
    return onset(x, 20)


# ---------------------------------------------------------------- S15 廣場人聲遠景（可循環）
CROWD_LOOP = 40.0


def sfx_crowd_far():
    """廣場上大家準備燈節的遠景人聲（40.0 s 可循環）：約 14 個聲音（大人與小孩）各自說話、重疊，
    只有母音共振峰（沒有子音）、低通 2.2 kHz、加殘響推遠 → 聽不出任何字；偶爾遠處紙張與竹子的輕響。
    檔頭從低谷約 1.5 s 起來。"""
    rng = _rng(24)
    L = secs(CROWD_LOOP)
    adults = babble(L, rng, voices=8, f0=(95, 210), fshift=(0.95, 1.1), talk=0.6)
    kids = babble(L, rng, voices=6, f0=(220, 330), fshift=(1.15, 1.3), talk=0.5)
    x = adults + 0.7 * kids
    x = lp(x, 2200)
    x = circ_reverb(x, rng, rt=1.6, wet=0.55)
    floor_ = periodic_noise(L, rng, lo=150, hi=1800, tilt_db_oct=-3.5) * 0.25
    paper = np.zeros(L)
    for _ in range(14):
        g = grain(rng, rng.uniform(6, 16), 1200, 3500) * rng.uniform(0.2, 0.5)
        add_wrap(paper, g, int(rng.integers(L)))
    x = x + floor_ + 0.6 * circ_reverb(paper, rng, rt=1.0, wet=0.5)
    x = x - np.mean(x)
    return x * seam_lull(L, -12.0, 1.5)


# ---------------------------------------------------------------- S16 腳步聲
FOOT_STEP = 0.5


def sfx_footsteps():
    """紙偶劇場的腳步（4.0 s）：8 步，每步 0.50 s（＝120 BPM，對得上 120 BPM 的配樂拍點），
    第 k 步在 0.02 + 0.5k 秒（k = 0…7）。每步是硬紙板輕輕點地：柔和低頻「咚」＋紙面短促沙聲，左右腳音高略不同。"""
    rng = _rng(25)
    n = secs(4.0)
    x = np.zeros(n)
    for k in range(8):
        t0 = 0.02 + FOOT_STEP * k
        sh = 1.0 if k % 2 == 0 else 0.9
        x += soft_thud(n, t0, f0=230 * sh, f1=140 * sh, decay=0.035, rise_ms=14, amp=0.7)
        i0 = secs(t0)
        m = secs(0.06)
        tap = bp(rng.standard_normal(m), 600 * sh, 2600 * sh) * env_points(m, [(0, 0), (0.014, 1.0), (0.03, 0.3), (0.06, 0)])
        x[i0:i0 + m] += 0.45 * tap
        sm = secs(0.09)
        scuff = bp(pink(sm, rng), 1500, 4000) * env_points(sm, [(0, 0), (0.03, 0.12), (0.09, 0)])
        j0 = i0 + secs(0.05)
        x[j0:j0 + sm] += scuff
    x = lp(hp(x, 80), 6000)
    return onset(x, 6, tail_ms=60)


# ---------------------------------------------------------------- S17–S20（G5 修正第 1 輪：audio/sfx/_placeholders.txt 的四個佔位檔）
def sfx_gust():
    """一陣風（2.6 s）：低中頻氣流聲中心頻率 350 → 900（1.0 s 最強）→ 450 Hz，鐘形包絡，一點落葉紙屑細沙；
    不呼嘯、沒有口哨聲（低通 4.5 kHz）。起音 ≥ 0.25 s（慢慢起風），最後 0.6 s 退去。"""
    rng = _rng(31)
    n = secs(2.6)
    w = pink(n, rng)
    out = np.zeros(n)
    hop = secs(0.02)
    win = np.hanning(2 * hop)
    for s0 in range(0, n - 2 * hop, hop):
        u = s0 / SR
        fc = 350 + 550 * np.exp(-0.5 * ((u - 1.0) / 0.45) ** 2) + 100 * (u > 1.0) * (u - 1.0)
        out[s0:s0 + 2 * hop] += bp(np.pad(w[s0:s0 + 2 * hop], 256), fc * 0.5, fc * 1.8)[256:-256] * win
    e = env_points(n, [(0, 0), (0.35, 0.35), (1.0, 1.0), (1.6, 0.55), (2.0, 0.25), (2.6, 0)])
    dens = env_points(n, [(0, 0), (0.6, 8), (1.0, 22), (1.6, 6), (2.2, 0)])
    leaves = scatter(n, rng, dens, 1600, 4000, dur_ms=(4, 10), amp=(0.04, 0.12))
    x = lp(hp(out * e + leaves * e, 80), 4500)
    return onset(x, 30, tail_ms=80)


def sfx_phone_noanswer():
    """手機撥號、沒人接（2.6 s）：兩聲柔和的「嘟嚕」鈴（0.05–0.85 s、1.35–2.15 s；520／650 Hz 正弦＋每秒 14 次的柔和顫音），
    經過 300–3400 Hz 的電話線音色，底下一層很輕的線路聲。刻意不用任何電信業者的回鈴音、撥號音或忙線音
    （臺灣回鈴音是 440＋480 Hz、響 1 秒停 2 秒；這裡音高、節奏都不同）。每聲起音 40 ms、收尾 120 ms，沒有突發巨響。"""
    rng = _rng(32)
    n = secs(2.6)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0 in (0.05, 1.35):
        m = secs(0.8)
        i0 = secs(t0)
        tt = np.arange(m) / SR
        trem = 0.6 + 0.4 * (0.5 - 0.5 * np.cos(2 * np.pi * 14 * tt))
        tone = (np.sin(2 * np.pi * 520 * tt) + 0.8 * np.sin(2 * np.pi * 650 * tt + 0.7)) * trem
        e = env_points(m, [(0, 0), (0.04, 1.0), (0.68, 0.9), (0.8, 0)])
        x[i0:i0 + m] += tone * e
    line = bp(rng.standard_normal(n), 300, 3400, order=4) * 0.012
    x = bp(x, 300, 3400, order=4) + line * env_points(n, [(0, 0), (0.05, 1), (2.45, 1), (2.6, 0)])
    return onset(x, 10, tail_ms=60)


def sfx_truck_arrive():
    """小貨車輕聲開近、停下、怠速（5.0 s；不按喇叭、沒有煞車尖響）：0–3.0 s 由約 40 m 開到 8 m（越近越慢）、
    3.0–3.6 s 轉速降下停住、3.6–5.0 s 怠速（檔尾 0.4 s 淡出）。小引擎＝點火頻率諧波（約 50 → 33 Hz）＋輕路噪，
    遠時高頻少；1/r 但最大值受控（build_all 依峰值與瞬間響度上限正規化）。"""
    rng = _rng(33)
    n = secs(5.0)
    t = np.arange(n) / SR
    u = np.clip(t / 3.0, 0, 1)
    s = 1 - (1 - u) ** 2.0
    dist = 40 - 32 * s
    speed = -np.gradient(dist, 1 / SR)
    doppler = 1 / (1 - np.clip(speed, 0, 20) / 343.0)
    rpm = 33 + 17 * np.clip(1 - (t - 2.8) / 0.8, 0, 1)
    ph = 2 * np.pi * np.cumsum(rpm * doppler) / SR
    jit = 1 + 0.06 * lp(rng.standard_normal(n), 30)
    eng = np.zeros(n)
    for h in range(1, 24):
        a = 1 / (1 + ((h * 40 - 220) / 180.0) ** 2) * (1.0 if h % 2 else 0.6)
        eng += a * np.sin(h * ph + rng.uniform(0, 6))
    eng *= jit
    road = bp(pink(n, rng), 160, 1500) * np.clip(speed / 8.0, 0, 1) * 0.5
    near = eng + road
    w = np.clip((40 - dist) / 32, 0, 1)
    x = lp(near, 650) * (1 - w) + near * w
    x = x * np.minimum(8.0 / dist, 1.0)
    x = lp(hp(x, 50), 3500)
    e = env_points(n, [(0, 0), (0.5, 1), (4.6, 1), (5.0, 0)])
    return onset(x * e, 40, tail_ms=60)


def sfx_crowd_short():
    """廣場人聲短版（4.0 s）：約 10 個聲音（大人與小孩）重疊說話，只有母音共振峰、低通 2.2 kHz、加殘響推遠 → 聽不出任何字；
    0.6 s 淡入、最後 0.8 s 淡出（一次播完，不循環）。"""
    rng = _rng(34)
    L = secs(4.0)
    adults = babble(L, rng, voices=6, f0=(95, 210), fshift=(0.95, 1.1), talk=0.75)
    kids = babble(L, rng, voices=4, f0=(220, 330), fshift=(1.15, 1.3), talk=0.65)
    x = lp(adults + 0.7 * kids, 2200)
    x = circ_reverb(x, rng, rt=1.4, wet=0.5)
    x = x - np.mean(x)
    e = env_points(L, [(0, 0), (0.6, 1), (3.2, 1), (4.0, 0)])
    return onset(x * e, 20, tail_ms=40)


# 個別音量規格（沒列的照 G3：樣本峰值 −8 dBFS、最大瞬間響度 ≤ −20 LUFS）
#   peak：正規化的樣本峰值；mmax：最大瞬間響度上限；lufs：環境聲改用整合響度目標（循環檔只做線性增益）
SFX_LEVEL = {
    'sfx_windchime': {'peak': -10.0, 'mmax': -24.0},
    'sfx_bamboo_drop': {'peak': -12.0, 'mmax': -26.0},
    'sfx_wind': {'lufs': -30.0},
    'sfx_school_bell': {'peak': -10.0, 'mmax': -24.0},
    'sfx_gate_ambience': {'lufs': -36.0},
    'sfx_watch_dial': {'peak': -14.0, 'mmax': -28.0},
    'sfx_phone_bed': {'lufs': -38.0},
    'sfx_ambulance_engine': {'peak': -10.0, 'mmax': -24.0},
    'sfx_plane_whoosh': {'peak': -12.0, 'mmax': -26.0},
    'sfx_crowd_far': {'lufs': -34.0},
    'sfx_footsteps': {'peak': -12.0, 'mmax': -26.0},
    # G5 修正第 1 輪（佔位檔換正式）
    'sfx_gust': {'peak': -14.0, 'mmax': -28.0},
    'sfx_phone_noanswer': {'peak': -14.0, 'mmax': -28.0},
    'sfx_truck_arrive': {'peak': -12.0, 'mmax': -27.0},
    'sfx_crowd_short': {'peak': -14.0, 'mmax': -30.0},
}
# 可循環的音效（一圈秒數）；不做淡入淡出、不經過限制器，接縫量測見 build_all.py
SFX_LOOPS = {'sfx_wind': WIND_LOOP, 'sfx_gate_ambience': GATE_LOOP, 'sfx_phone_bed': PHONE_LOOP, 'sfx_crowd_far': CROWD_LOOP}


SFX = {
    'sfx_curtain_open': (sfx_curtain_open, '布幕打開：紙／布摩擦約 2 秒，1.9–2.1 s 輕輕落定'),
    'sfx_curtain_close': (sfx_curtain_close, '布幕合攏：紙／布摩擦約 2 秒，約 2.0 s 輕輕落定'),
    'sfx_paper_rustle': (sfx_paper_rustle, '紙張摩擦（S1 一般用）'),
    'sfx_string_drop': (sfx_string_drop, '紙繩落下輕沙沙＋紙環輕扣（扣上點 0.50 s；每根線觸發一次）'),
    'sfx_string_taut': (sfx_string_taut, '紙繩繃緊：短促輕微紙張拉緊聲（峰在約 0.30 s），不陰森'),
    'sfx_lamp_on': (sfx_lamp_on, '點燈（S5）：溫暖輕鈴 A5→D6，0.00／0.16 s'),
    'sfx_stamp': (sfx_stamp, '「正解」紙印章（S4）：柔和一聲，0.32 s 輕抬'),
    'sfx_fold': (sfx_fold, '折折摺紙（S2）：三下摺痕 0.02／0.28／0.54 s'),
    'sfx_card_in': (sfx_card_in, '題卡摺開送上：兩下展開 → 0.42 s 滑入 → 1.02 s 落定'),
    'sfx_quiet_fold': (sfx_quiet_fold, '折折收摺音效（S3 收聲訊號，加做）：兩下摺紙＋D6→A5 輕鈴 0.55／0.80 s'),
    # G5 新增（S6–S16）
    'sfx_windchime': (sfx_windchime, 'S6 店門風鈴：8 下逐漸變輕，第一下 0.02 s，約 1.5 s 後只剩餘響（4.2 s）'),
    'sfx_bamboo_drop': (sfx_bamboo_drop, 'S7 竹篾輕落地：落地 0.01 s，彈跳 0.14／0.23／0.29 s，輕滾到 0.5 s'),
    'sfx_wind': (sfx_wind, 'S8 柔和風聲：30.0 s 可循環，檔頭 1.5 s 從低谷起來，3.0 s 一陣較明顯的風'),
    'sfx_school_bell': (sfx_school_bell, 'S9 柔和下課鐘：西敏寺鐘聲前兩句（公有領域），第一音 0.05 s、第二句 3.05 s、最後一音 4.85 s'),
    'sfx_gate_ambience': (sfx_gate_ambience, 'S10 校門口環境聲：40.0 s 可循環、低音量；遠處車流、慢車經過 6／21／33 s 前後、零星童聲（聽不出字）、麻雀'),
    'sfx_watch_dial': (sfx_watch_dial, 'S11 兒童手錶撥號：嗶 0.10／0.42／0.74 s（1、1、9），確認音 1.25 s'),
    'sfx_phone_bed': (sfx_phone_bed, 'S12 電話音色底音：40.0 s 可循環、很輕；300–3400 Hz 線路雜音，沒有電信撥號／回鈴音'),
    'sfx_ambulance_engine': (sfx_ambulance_engine, 'S13 救護車引擎（無警笛）：0–8 s 開近、8–9 s 停下、9–14.5 s 怠速、14.5–16 s 淡出'),
    'sfx_plane_whoosh': (sfx_plane_whoosh, 'S14 紙飛機咻聲：1.6 s，最近點 0.6 s'),
    'sfx_crowd_far': (sfx_crowd_far, 'S15 廣場人聲遠景：40.0 s 可循環；只有母音、聽不出字；檔頭 1.5 s 從低谷起來'),
    'sfx_footsteps': (sfx_footsteps, 'S16 紙偶腳步：8 步、每步 0.50 s（120 BPM），第 k 步 0.02＋0.5k 秒'),
    # G5 修正第 1 輪：audio/sfx/_placeholders.txt 的佔位檔原檔名換成正式音效
    'sfx_gust': (sfx_gust, 'S17 一陣風：2.6 s，1.0 s 最強，最後 0.6 s 退去；不呼嘯'),
    'sfx_phone_noanswer': (sfx_phone_noanswer, 'S18 撥號沒人接：兩聲柔和鈴 0.05／1.35 s（各 0.8 s），電話線音色；不用真實電信音調'),
    'sfx_truck_arrive': (sfx_truck_arrive, 'S19 小貨車輕聲開近：0–3.0 s 開近、3.0–3.6 s 停下、3.6–5.0 s 怠速；不按喇叭、沒有煞車尖響'),
    'sfx_crowd_short': (sfx_crowd_short, 'S20 廣場人聲短版：4.0 s，0.6 s 淡入、最後 0.8 s 淡出；只有母音、聽不出字'),
}
