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
}
