# -*- coding: utf-8 -*-
"""反毒剪紙劇場｜配樂與音效一鍵重建。

用法（在專案根目錄）：
  caffeinate -i tools/.venv/bin/python tools/music/build_all.py            # 全部重建
  tools/.venv/bin/python tools/music/build_all.py --only music_town,sfx_stamp
  tools/.venv/bin/python tools/music/build_all.py --metrics-only          # 只重新量測與畫圖

流程：compose.py 寫譜 → MIDI → fluidsynth（FluidR3_GM.sf2，MIT）算成 48 kHz 浮點 →
      numpy 後製（循環接縫、淡入淡出、響度、真峰值）→ 16-bit PCM 寫進 audio/music/、audio/sfx/；
      sfx.py 程式合成音效；最後量測寫 review/G3/music_metrics.json、畫 review/G3/music_waveforms.png。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BUILD, MUSIC_OUT, ROOT, SFX_OUT, SR, ffmpeg_measure, fade, fit_length,  # noqa: E402
                    json_dump, limiter, loop_bake, render, sample_peak_db, true_peak_db,
                    write_float, write_pcm16)
import compose  # noqa: E402
import sfx as sfxmod  # noqa: E402

VER = 'v01'
# 個別改版（不覆寫已採用的 v01；tools/pack.mjs 自動取最新版本）
VERSIONS = {'music_m4_light': 'v02'}   # G3 修正第 1 輪：−27 → −24 LUFS（review/G3/mix_r1.json）
REVIEW = ROOT / 'review' / 'G3'
TP_CEIL = -2.3        # 真峰值上限（規格 ≤ −2 dBTP，留 0.3 dB 餘裕）
SFX_PEAK = -8.0       # 音效樣本峰值（規格 ≤ −6 dBFS）
SFX_M_MAX = -20.0     # 音效最大瞬間響度上限（配音 −18 LUFS，音效不搶過對白）


def log(*a):
    print('[build]', *a, flush=True)


# ---------------------------------------------------------------- 配樂
def music_path(pid: str, draft: bool) -> Path:
    """草稿放 audio/music/drafts/（tools/pack.mjs 只讀 audio/music/ 第一層，草稿不會被打包進演出）。"""
    return (MUSIC_OUT / 'drafts' if draft else MUSIC_OUT) / f'{pid}_{VERSIONS.get(pid, VER)}.wav'


def build_music(pid: str, fn) -> dict:
    t0 = time.time()
    if pid in compose.LOOPS:
        spec = fn(reps=3)
        x = render(spec['song'].write(), **spec['render'])
        L = spec['length']
        need = int(round(3 * L * SR)) + int(0.05 * SR)
        if len(x) < need:
            x = np.concatenate([x, np.zeros((need - len(x), 2))])
        y = loop_bake(x, L)
    else:
        spec = fn()
        x = render(spec['song'].write(), **spec['render'])
        y = fit_length(x, spec['length'])
        fs, fl = spec['fade_out']
        y = fade(y, fin=0.005, fout=fl, fout_start=fs)
    # 響度：先線性增益到目標；循環檔不經過限制器（避免接縫兩側增益不同）
    tmp = BUILD / f'{pid}.pre.wav'
    write_float(tmp, y)
    m = ffmpeg_measure(tmp)
    g = 10 ** ((spec['target'] - m['I']) / 20)
    y = y * g
    tp = true_peak_db(y)
    limited = False
    if tp > TP_CEIL:
        if pid in compose.LOOPS:
            y = y * 10 ** ((TP_CEIL - tp) / 20)
        else:
            y = limiter(y, ceiling_db=TP_CEIL - 0.2)
            limited = True
            write_float(tmp, y)
            m2 = ffmpeg_measure(tmp)
            y = y * 10 ** ((spec['target'] - m2['I']) / 20)
            if true_peak_db(y) > TP_CEIL:
                y = y * 10 ** ((TP_CEIL - true_peak_db(y)) / 20)
    out = music_path(pid, bool(spec.get('draft')))
    write_pcm16(out, y)
    log(f'{pid}: {len(y) / SR:.2f}s → {out.relative_to(ROOT)}（{time.time() - t0:.1f}s）')
    return {k: v for k, v in spec.items() if k not in ('song', 'render')} | {'limited': limited}


# ---------------------------------------------------------------- 音效
def build_sfx(pid: str, fn) -> None:
    x = fn()
    x = x / (np.max(np.abs(x)) + 1e-12) * 10 ** (SFX_PEAK / 20)
    tmp = BUILD / f'{pid}.pre.wav'
    write_float(tmp, x)
    m = ffmpeg_measure(tmp)
    mmax = max([v for _, v in m['M']] or [-99])
    if mmax > SFX_M_MAX:
        x = x * 10 ** ((SFX_M_MAX - mmax) / 20)
    tp = true_peak_db(x)
    if tp > TP_CEIL:
        x = x * 10 ** ((TP_CEIL - tp) / 20)
    out = SFX_OUT / f'{pid}_{VER}.wav'
    write_pcm16(out, x)
    log(f'{pid}: {len(x) / SR:.2f}s → {out.relative_to(ROOT)}')


# ---------------------------------------------------------------- 量測
def momentary_stats(M, skip: float = 0.0):
    """M：[(t, LUFS)]，每 100 ms 一點（400 ms 視窗）。低於 −50 LUFS 當成 −50（避免從靜音起算的假跳升）。
    skip：略過檔頭幾秒（配樂用 0.4 s，避開 400 ms 視窗還沒填滿、從檔案外的靜音算起的假跳升）。"""
    M = [(t, v) for t, v in M if t >= skip - 1e-6]
    if not M:
        return {}
    v = np.array([max(-50.0, x) for _, x in M])
    t = np.array([a for a, _ in M])
    j100 = np.diff(v) if len(v) > 1 else np.array([0.0])
    rise1 = [v[k] - v[max(0, k - 10):k + 1].min() for k in range(len(v))]
    k1 = int(np.argmax(rise1))
    k0 = int(np.argmax(j100)) + 1 if len(j100) else 0
    return {
        'momentary_max_lufs': round(float(v.max()), 1),
        'max_jump_100ms_db': round(float(j100.max()), 1), 'max_jump_100ms_at_s': round(float(t[k0]), 1),
        'max_rise_1s_db': round(float(max(rise1)), 1), 'max_rise_1s_at_s': round(float(t[k1]), 1),
    }


def rise_time_ms(x):
    """起音時間：1 ms 絕對值包絡從首次超過峰值 −40 dB 到首次達到峰值 −6 dB 的時間。"""
    a = np.abs(x)
    k = int(0.001 * SR)
    env = np.convolve(a, np.ones(k) / k, mode='same')
    pk = env.max()
    i0 = int(np.argmax(env > pk * 0.01))
    i1 = int(np.argmax(env >= pk * 0.5))
    return round((i1 - i0) / SR * 1000, 1)


def seam_check(path: Path, y: np.ndarray, pid: str) -> dict:
    """循環接縫：首尾樣本差（LSB）與一般相鄰樣本差比較；首尾 50 ms 能量；兩圈接起來的瞬間響度跳升。"""
    yi = y.astype(np.int32)
    d_seam = np.abs(yi[0] - yi[-1]).max()
    d_all = np.abs(np.diff(yi, axis=0)).max(axis=1)
    p999 = float(np.percentile(d_all, 99.9))
    w = int(0.05 * SR)
    yf = y.astype(np.float64) / 32768

    def rms_db(s):
        return 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)
    e_head, e_tail = rms_db(yf[:w]), rms_db(yf[-w:])
    tmp = BUILD / f'{pid}.twice.wav'
    wavfile.write(tmp, SR, np.concatenate([y, y]))
    m = ffmpeg_measure(tmp)
    L = len(y) / SR
    near = [(t, v) for t, v in m['M'] if L - 1.0 <= t <= L + 1.5]
    vs = [max(-50, v) for _, v in near]
    jump = max(np.diff(vs)) if len(vs) > 1 else 0.0
    return {
        'seam_sample_diff_lsb': int(d_seam), 'adjacent_diff_p99_9_lsb': round(p999, 1),
        'seam_ok': bool(d_seam <= max(p999, 64)),
        'head_50ms_rms_dbfs': round(e_head, 1), 'tail_50ms_rms_dbfs': round(e_tail, 1),
        'head_tail_rms_diff_db': round(abs(e_head - e_tail), 1),
        'seam_momentary_max_jump_100ms_db': round(float(jump), 1),
    }


def measure_file(path: Path, kind: str, extra: dict | None = None) -> dict:
    sr, y = wavfile.read(path)
    yf = y.astype(np.float64) / 32768
    m = ffmpeg_measure(path)
    rec = {
        'file': str(path.relative_to(ROOT)), 'kind': kind,
        'sample_rate': sr, 'channels': 1 if y.ndim == 1 else y.shape[1], 'bit_depth': 16,
        'duration_s': round(len(y) / sr, 3),
        'integrated_lufs': m['I'], 'true_peak_dbtp': m['TP'], 'lra_lu': m['LRA'],
        'sample_peak_dbfs': round(sample_peak_db(yf), 2),
        'true_peak_dbtp_numpy_4x': round(true_peak_db(yf), 2),
        'size_bytes': path.stat().st_size,
    }
    rec |= momentary_stats(m['M'], 0.0 if kind.startswith('sfx') else 0.4)
    if kind.startswith('sfx'):
        rec['rise_time_ms'] = rise_time_ms(yf if yf.ndim == 1 else yf.mean(axis=1))
        rec['first_5ms_peak_rel_db'] = round(20 * np.log10(np.max(np.abs(yf[:int(0.005 * SR)])) / np.max(np.abs(yf)) + 1e-12), 1)
    if kind == 'music_loop':
        rec |= seam_check(path, y, path.stem)
    else:
        n10 = int(0.01 * sr)
        rec['last_10ms_peak_dbfs'] = round(sample_peak_db(yf[-n10:]), 1)
        rec['first_sample_abs_lsb'] = int(np.abs(y[0]).max())
    if extra:
        rec |= extra
    return rec


def check_spec(rec: dict) -> list[str]:
    bad = []
    if rec['true_peak_dbtp'] > -2.0:
        bad.append(f"真峰值 {rec['true_peak_dbtp']} > −2 dBTP")
    if rec['kind'].startswith('sfx') and rec['sample_peak_dbfs'] > -6.0:
        bad.append(f"音效峰值 {rec['sample_peak_dbfs']} > −6 dBFS")
    if rec['kind'].startswith('sfx') and rec.get('rise_time_ms', 99) < 5.0:
        bad.append(f"起音 {rec['rise_time_ms']} ms < 5 ms")
    tgt = rec.get('target_lufs')
    if tgt is not None and abs(rec['integrated_lufs'] - tgt) > 1.0:
        bad.append(f"整合響度 {rec['integrated_lufs']} 偏離目標 {tgt}")
    if rec['kind'] == 'music_loop' and not rec.get('seam_ok', True):
        bad.append('循環接縫樣本差過大')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--metrics-only', action='store_true')
    ap.add_argument('--no-plot', action='store_true')
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    BUILD.mkdir(parents=True, exist_ok=True)
    specs_path = BUILD / 'specs.json'
    import json
    specs = json.loads(specs_path.read_text(encoding='utf-8')) if specs_path.exists() else {}

    if not a.metrics_only:
        for pid, fn in compose.PIECES.items():
            if only and pid not in only:
                continue
            specs[pid] = build_music(pid, fn)
        for pid, (fn, desc) in sfxmod.SFX.items():
            if only and pid not in only:
                continue
            build_sfx(pid, fn)
            specs[pid] = {'desc': desc}
        json_dump(specs_path, specs)

    # 量測全部輸出
    records, problems = [], {}
    for pid in compose.PIECES:
        sp = specs.get(pid, {})
        p = music_path(pid, bool(sp.get('draft')))
        if not p.exists():
            continue
        kind = 'music_loop' if pid in compose.LOOPS else 'music_oneshot'
        extra = {'target_lufs': sp.get('target'), 'draft': bool(sp.get('draft')),
                 'tempo': sp.get('tempo'), 'key': sp.get('key'), 'sync': sp.get('sync'),
                 'limiter_used': sp.get('limited')}
        r = measure_file(p, kind, extra)
        records.append(r)
    for pid in sfxmod.SFX:
        p = SFX_OUT / f'{pid}_{VER}.wav'
        if p.exists():
            records.append(measure_file(p, 'sfx', {'desc': specs.get(pid, {}).get('desc', sfxmod.SFX[pid][1])}))
    for r in records:
        b = check_spec(r)
        r['spec_pass'] = not b
        if b:
            problems[r['file']] = b
    out = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'tool': 'tools/music/build_all.py（ffmpeg ebur128 量測；真峰值 = ffmpeg true peak）',
        'spec': {'music_bed_lufs': -24, 'opening_closing_lufs': -20, 'sfx_sample_peak_max_dbfs': -6,
                 'true_peak_max_dbtp': -2, 'sample_rate': 48000, 'bit_depth': 16},
        'definitions': {
            'max_jump_100ms_db': '瞬間響度（400 ms 視窗、每 100 ms）相鄰兩點的最大上升；低於 −50 LUFS 視為 −50；配樂從 0.4 s 起算（視窗填滿後），音效從 0 s 起算（含從靜音起音）',
            'max_rise_1s_db': '任一點的瞬間響度減去它前 1 秒內最低值的最大值（同上下限）',
            'rise_time_ms': '1 ms 包絡從峰值 −40 dB 升到峰值 −6 dB 的時間（音效起音）',
            'seam_sample_diff_lsb': '循環檔最後一個樣本與第一個樣本的差（16-bit LSB），與全檔相鄰樣本差的 99.9 百分位比較',
        },
        'listening': '未驗證（Claude 聽不到音訊；聽感待許老師確認）',
        'problems': problems,
        'files': records,
    }
    json_dump(REVIEW / 'music_metrics.json', out)
    log(f'量測完成：{len(records)} 檔；不合規格 {len(problems)} 檔 → review/G3/music_metrics.json')
    for f, b in problems.items():
        log('  [不合格]', f, '；'.join(b))
    # 清掉中間浮點檔（保留 .mid 與 specs.json），避免 build/ 佔數百 MB
    for pat in ('*.render.wav', '*.pre.wav', '*.norm.wav', '*.twice.wav'):
        for f in BUILD.glob(pat):
            f.unlink()
    if not a.no_plot:
        py = '/opt/anaconda3/bin/python3'
        subprocess.run([py, str(Path(__file__).with_name('plot_waveforms.py'))], check=False)


if __name__ == '__main__':
    main()
