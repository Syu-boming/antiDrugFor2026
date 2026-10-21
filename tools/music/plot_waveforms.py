# -*- coding: utf-8 -*-
"""畫 review/G5/audio/waveforms_music.png、waveforms_sfx.png：每檔一列（左：波形；右：頻譜圖）。
用 /opt/anaconda3/bin/python3 執行（需要 matplotlib）。由 build_all.py 自動呼叫。
（G3 版的 review/G3/music_waveforms.png 保留不覆寫；草稿不畫。）"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.io import wavfile  # noqa: E402
from scipy.signal import spectrogram  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
METRICS = ROOT / 'review' / 'G5' / 'audio' / 'metrics.json'
OUTDIR = ROOT / 'review' / 'G5' / 'audio'

# 主要同步點（秒），畫成垂直虛線
MARKS = {
    'music_opening': [(1.0, 'curtain'), (3.0, 'M1 in'), (7.5, 'sets up'), (11.0, 'final chord')],
    'music_closing': [(2.0, 'card'), (5.0, 'final chord')],
    'music_m4_strings': [(11.0, 'sparse'), (40.0, 'tail')],
    'sfx_string_drop': [(0.5, 'clasp')],
    'music_zhezhe': [(4.0, 'bed'), (16.0, 'seam')],
    'music_shiny': [(3.75, 'D+'), (7.5, 'E+'), (11.25, 'C+')],
    'music_road': [(10.0, 'celesta'), (17.5, 'F#')],
    'music_courage': [(10.0, 'phrase 2'), (20.0, 'bed')],
    'music_recovery': [(6.0, 'winter'), (12.0, 'spring'), (18.0, 'summer')],
    'music_bows': [(1.0, 'bow1'), (3.0, '2'), (5.0, '3'), (7.0, '4'), (9.0, '5'), (11.0, '6'), (13.0, '7'), (15.0, 'final')],
    'music_town_night': [(12.0, 'phrase 2'), (24.0, 'bed')],
    'sfx_wind': [(3.0, 'gust')],
    'sfx_ambulance_engine': [(8.0, 'stop'), (9.0, 'idle'), (14.5, 'fade')],
    'sfx_plane_whoosh': [(0.6, 'nearest')],
    'sfx_school_bell': [(3.05, 'phrase 2')],
    'sfx_watch_dial': [(0.10, '1'), (0.42, '1'), (0.74, '9')],
}


def main():
    d = json.loads(METRICS.read_text(encoding='utf-8'))
    allf = [r for r in d['files'] if not r.get('draft')]
    plot([r for r in allf if r['kind'].startswith('music')], OUTDIR / 'waveforms_music.png', 'music')
    plot([r for r in allf if r['kind'].startswith('sfx')], OUTDIR / 'waveforms_sfx.png', 'sfx')


def plot(files, OUT, label):
    n = len(files)
    fig, axes = plt.subplots(n, 2, figsize=(16, 1.55 * n), gridspec_kw={'width_ratios': [1.25, 1]})
    for row, rec in enumerate(files):
        sr, y = wavfile.read(ROOT / rec['file'])
        y = y.astype(np.float64) / 32768
        mono = y.mean(axis=1) if y.ndim == 2 else y
        t = np.arange(len(mono)) / sr
        ax = axes[row, 0]
        hop = max(1, int(0.005 * sr))
        k = len(mono) // hop
        seg = mono[:k * hop].reshape(k, hop)
        tt = np.arange(k) * hop / sr
        ax.fill_between(tt, seg.min(axis=1), seg.max(axis=1), color='#3b6ea5', lw=0)
        lim = max(0.05, 1.25 * float(np.max(np.abs(mono))))
        ax.set_ylim(-lim, lim)
        ax.set_xlim(0, t[-1])
        for sgn in (1, -1):   # −6 dBFS 參考線
            ax.axhline(sgn * 10 ** (-6 / 20), color='#bbbbbb', lw=0.5, ls=':')
        name = re.sub(r'_v\d+$', '', Path(rec['file']).stem)
        stat = f"I {rec['integrated_lufs']} LUFS  TP {rec['true_peak_dbtp']} dBTP  {rec['duration_s']} s"
        if rec['kind'] in ('music_loop', 'sfx_loop'):
            stat += f"  loop seam {rec['seam_sample_diff_lsb']} LSB"
        if rec.get('draft'):
            stat += '  [DRAFT]'
        ax.set_title(f'{name}   {stat}', fontsize=8, loc='left')
        ax.tick_params(labelsize=6)
        for x, lab in MARKS.get(name, []):
            ax.axvline(x, color='#d0703c', lw=0.8, ls='--')
            ax.text(x, 0.75 * lim, lab, fontsize=6, color='#d0703c')
        ax2 = axes[row, 1]
        f, ts, S = spectrogram(mono, fs=sr, nperseg=2048, noverlap=1536)
        Sdb = 10 * np.log10(S + 1e-12)
        ax2.pcolormesh(ts, f, Sdb, shading='auto', vmin=Sdb.max() - 80, vmax=Sdb.max(), cmap='magma')
        ax2.set_ylim(30, 10000)
        ax2.set_yscale('log')
        ax2.tick_params(labelsize=6)
    fig.suptitle(f'G5 {label} — waveform (left, 5 ms min/max) / spectrogram 30 Hz–10 kHz (right). Listening: NOT VERIFIED',
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.995))
    fig.savefig(OUT, dpi=80)
    print('[plot]', OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
