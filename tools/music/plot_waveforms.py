# -*- coding: utf-8 -*-
"""畫 review/G3/music_waveforms.png：每檔一列（左：波形＋瞬間響度；右：頻譜圖）。
用 /opt/anaconda3/bin/python3 執行（需要 matplotlib）。由 build_all.py 自動呼叫。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.io import wavfile  # noqa: E402
from scipy.signal import spectrogram  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
METRICS = ROOT / 'review' / 'G3' / 'music_metrics.json'
OUT = ROOT / 'review' / 'G3' / 'music_waveforms.png'

# 主要同步點（秒），畫成垂直虛線
MARKS = {
    'music_opening': [(1.0, 'curtain'), (3.0, 'M1 in'), (7.5, 'sets up'), (11.0, 'final chord')],
    'music_closing': [(2.0, 'card'), (5.0, 'final chord')],
    'music_m4_strings': [(11.0, 'sparse'), (40.0, 'tail')],
    'sfx_string_drop': [(0.5, 'clasp')],
}


def main():
    d = json.loads(METRICS.read_text(encoding='utf-8'))
    files = d['files']
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
        ax.set_ylim(-0.6, 0.6)
        ax.set_xlim(0, t[-1])
        for sgn in (1, -1):   # −6 dBFS 參考線
            ax.axhline(sgn * 10 ** (-6 / 20), color='#bbbbbb', lw=0.5, ls=':')
        name = Path(rec['file']).stem.replace('_v01', '')
        stat = f"I {rec['integrated_lufs']} LUFS  TP {rec['true_peak_dbtp']} dBTP  {rec['duration_s']} s"
        if rec['kind'] == 'music_loop':
            stat += f"  loop seam {rec['seam_sample_diff_lsb']} LSB"
        if rec.get('draft'):
            stat += '  [DRAFT]'
        ax.set_title(f'{name}   {stat}', fontsize=8, loc='left')
        ax.tick_params(labelsize=6)
        for x, lab in MARKS.get(name, []):
            ax.axvline(x, color='#d0703c', lw=0.8, ls='--')
            ax.text(x, 0.45, lab, fontsize=6, color='#d0703c')
        ax2 = axes[row, 1]
        f, ts, S = spectrogram(mono, fs=sr, nperseg=2048, noverlap=1536)
        Sdb = 10 * np.log10(S + 1e-12)
        ax2.pcolormesh(ts, f, Sdb, shading='auto', vmin=Sdb.max() - 80, vmax=Sdb.max(), cmap='magma')
        ax2.set_ylim(30, 10000)
        ax2.set_yscale('log')
        ax2.tick_params(labelsize=6)
    fig.suptitle('G3 music & sfx — waveform (left, 5 ms min/max) / spectrogram 30 Hz–10 kHz (right). Listening: NOT VERIFIED',
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.995))
    fig.savefig(OUT, dpi=80)
    print('[plot]', OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
