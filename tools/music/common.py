# -*- coding: utf-8 -*-
"""反毒剪紙劇場｜配樂與音效共用工具（作曲、算譜、後製、量測）。

用 tools/.venv/bin/python 執行（需要 pretty_midi、numpy、scipy）。
外部程式：fluidsynth、ffmpeg。音色庫：tools/sf/FluidR3_GM.sf2（MIT）。
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pretty_midi as pm
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
SF2 = ROOT / 'tools' / 'sf' / 'FluidR3_GM.sf2'
BUILD = ROOT / 'tools' / 'music' / 'build'
MUSIC_OUT = ROOT / 'audio' / 'music'
SFX_OUT = ROOT / 'audio' / 'sfx'
SR = 48000

# GM 音色（0 起算）
GM = {
    'piano': 0, 'celesta': 8, 'glock': 9, 'musicbox': 10, 'vibes': 11, 'marimba': 12,
    'nylon': 24, 'cello': 42, 'contrabass': 43, 'pizz': 45, 'harp': 46,
    'strings': 48, 'slowstrings': 49, 'flute': 73, 'recorder': 74, 'panflute': 75,
    'warmpad': 89, 'koto': 107, 'kalimba': 108, 'woodblock': 115,
}

_NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def n(name: str) -> int:
    """'F#4' → MIDI 音高。"""
    m = re.fullmatch(r'([A-G])([#b]?)(-?\d)', name)
    if not m:
        raise ValueError(name)
    p = _NOTE[m.group(1)] + {'#': 1, 'b': -1, '': 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + p


class Song:
    """以「秒」為單位排音符（漸慢、自由速度都直接算秒數）。"""

    def __init__(self, name: str, length: float, tail: float = 3.0):
        self.name = name
        self.length = length          # 成品長度（秒）
        self.tail = tail              # 算譜時多留的餘響（秒）
        self.midi = pm.PrettyMIDI(initial_tempo=120)
        self.insts: dict[str, pm.Instrument] = {}
        self._ch = 0

    def inst(self, key: str, program: str, volume: int = 100, pan: int = 64,
             reverb: int = 50, chorus: int = 0) -> pm.Instrument:
        if key in self.insts:
            return self.insts[key]
        ins = pm.Instrument(program=GM[program], name=key)
        for cc, v in ((7, volume), (10, pan), (91, reverb), (93, chorus), (11, 127)):
            ins.control_changes.append(pm.ControlChange(cc, v, 0.0))
        self.insts[key] = ins
        self.midi.instruments.append(ins)
        return ins

    def note(self, key: str, pitch, start: float, dur: float, vel: int = 70):
        if isinstance(pitch, str):
            pitch = n(pitch)
        vel = int(max(1, min(127, round(vel))))
        self.insts[key].notes.append(pm.Note(vel, int(pitch), float(start), float(start + dur)))

    def chord(self, key: str, pitches, start: float, dur: float, vel: int = 60, roll: float = 0.0):
        for i, p in enumerate(pitches):
            self.note(key, p, start + i * roll, dur - i * roll, vel)

    def expr(self, key: str, t0: float, t1: float, v0: int, v1: int, steps: int = 24):
        """CC11（表情）線性漸變，用來做漸強漸弱。"""
        ins = self.insts[key]
        for i in range(steps + 1):
            t = max(0.002, t0 + (t1 - t0) * i / steps)
            v = int(round(v0 + (v1 - v0) * i / steps))
            ins.control_changes.append(pm.ControlChange(11, max(0, min(127, v)), t))

    def write(self) -> Path:
        BUILD.mkdir(parents=True, exist_ok=True)
        # 在尾端放一個無作用的控制訊息，讓算譜延伸到餘響結束
        first = next(iter(self.insts.values()))
        first.control_changes.append(pm.ControlChange(110, 0, self.length + self.tail))
        path = BUILD / f'{self.name}.mid'
        self.midi.write(str(path))
        return path


def render(mid: Path, reverb_room: float = 0.62, reverb_level: float = 0.55,
           reverb_damp: float = 0.35, reverb_width: float = 0.9, gain: float = 0.5) -> np.ndarray:
    """fluidsynth 算成 48 kHz 浮點立體聲，回傳 (N, 2) float64。"""
    out = mid.with_suffix('.render.wav')
    cmd = ['fluidsynth', '-ni', '-q', '-F', str(out), '-T', 'wav', '-O', 'float', '-r', str(SR),
           '-g', str(gain),
           '-o', 'synth.chorus.active=0',
           '-o', 'synth.reverb.active=1',
           '-o', f'synth.reverb.room-size={reverb_room}',
           '-o', f'synth.reverb.level={reverb_level}',
           '-o', f'synth.reverb.damp={reverb_damp}',
           '-o', f'synth.reverb.width={reverb_width}',
           str(SF2), str(mid)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sr, x = wavfile.read(out)
    assert sr == SR, sr
    x = x.astype(np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    return x


def fit_length(x: np.ndarray, seconds: float) -> np.ndarray:
    n_ = int(round(seconds * SR))
    if len(x) >= n_:
        return x[:n_].copy()
    pad = np.zeros((n_ - len(x),) + x.shape[1:])
    return np.concatenate([x, pad])


def raised_cos(n_: int) -> np.ndarray:
    return 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n_))


def fade(x: np.ndarray, fin: float = 0.005, fout: float = 0.0, fout_start: float | None = None) -> np.ndarray:
    """淡入（升餘弦）；淡出可指定開始秒數，淡出後補零到檔尾。"""
    y = x.copy()
    ni = max(1, int(fin * SR))
    env_in = raised_cos(ni)
    y[:ni] *= env_in[:, None] if y.ndim == 2 else env_in
    if fout > 0:
        s = int(fout_start * SR) if fout_start is not None else len(y) - int(fout * SR)
        no = int(fout * SR)
        env = raised_cos(no)[::-1]
        e = min(len(y), s + no)
        seg = env[:e - s]
        y[s:e] *= seg[:, None] if y.ndim == 2 else seg
        y[e:] = 0
    return y


def loop_bake(render3: np.ndarray, loop_sec: float, xfade: float = 0.03) -> np.ndarray:
    """輸入「同一段落連續算三遍＋餘響」的音訊，取中間那一遍；
    開頭極短交叉淡化成第三遍的開頭，讓檔尾接回檔頭時逐樣本連續。"""
    L = int(round(loop_sec * SR))
    mid = render3[L:2 * L].copy()
    nx = int(xfade * SR)
    w = raised_cos(nx)[:, None]
    nxt = render3[2 * L:2 * L + nx]
    mid[:nx] = nxt * (1 - w) + mid[:nx] * w
    return mid


# ---------------------------------------------------------------- 量測
_FR = re.compile(r't:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.inf]+)\s+S:\s*(-?[\d.inf]+)')


def ffmpeg_measure(path: Path) -> dict:
    """ffmpeg ebur128：整合響度、真峰值、逐 100 ms 瞬間響度。"""
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-v', 'verbose', '-i', str(path), '-af',
           'ebur128=peak=true:framelog=verbose', '-f', 'null', '-']
    r = subprocess.run(cmd, capture_output=True, text=True)
    err = r.stderr
    summary = err[err.rfind('Summary:'):]
    I = float(re.search(r'I:\s*(-?[\d.]+|-inf)\s*LUFS', summary).group(1))
    tp_m = re.search(r'True peak:\s*Peak:\s*(-?[\d.]+|-inf)', summary, re.S)
    TP = float(tp_m.group(1)) if tp_m else float('nan')
    lra_m = re.search(r'LRA:\s*(-?[\d.]+)\s*LU', summary)
    M = []
    for line in err.splitlines():
        mm = _FR.search(line)
        if mm:
            try:
                M.append((float(mm.group(1)), float(mm.group(2))))
            except ValueError:
                pass
    return {'I': I, 'TP': TP, 'LRA': float(lra_m.group(1)) if lra_m else None, 'M': M}


def true_peak_db(x: np.ndarray) -> float:
    xx = x if x.ndim == 2 else x[:, None]
    up = resample_poly(xx, 4, 1, axis=0)
    pk = np.max(np.abs(up))
    return 20 * np.log10(max(pk, 1e-12))


def sample_peak_db(x: np.ndarray) -> float:
    return 20 * np.log10(max(np.max(np.abs(x)), 1e-12))


def limiter(x: np.ndarray, ceiling_db: float = -2.5, look: float = 0.004, release: float = 0.12) -> np.ndarray:
    """簡單的前視峰值限制器（以 4 倍超取樣的峰值估計），避免真峰值超標。"""
    thr = 10 ** (ceiling_db / 20)
    xx = x if x.ndim == 2 else x[:, None]
    up = np.abs(resample_poly(xx, 4, 1, axis=0)).max(axis=1)
    pk = up[:4 * len(xx)].reshape(-1, 4).max(axis=1)
    g = np.minimum(1.0, thr / np.maximum(pk, 1e-12))
    la = max(1, int(look * SR))
    # 前視：往前取最小值
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(g, size=2 * la + 1, mode='nearest')
    # 釋放平滑（單極）
    a = np.exp(-1.0 / (release * SR))
    out = np.empty_like(g)
    cur = 1.0
    for i in range(len(g)):  # noqa: 迴圈長度 = 樣本數，檔案都很短
        cur = g[i] if g[i] < cur else a * cur + (1 - a) * g[i]
        out[i] = cur
    y = xx * out[:, None]
    return y if x.ndim == 2 else y[:, 0]


def write_pcm16(path: Path, x: np.ndarray, seed: int = 7):
    """TPDF 抖動後寫成 16-bit PCM。"""
    rng = np.random.default_rng(seed)
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0
    y = np.clip(np.round((x + d) * 32767.0), -32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, SR, y)


def write_float(path: Path, x: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, SR, x.astype(np.float32))


def normalize_loudness(x: np.ndarray, target_lufs: float, tp_ceiling: float = -2.3,
                       name: str = 'tmp') -> tuple[np.ndarray, dict]:
    """量整合響度 → 調增益 → 必要時限制真峰值 → 再量一次微調。"""
    tmp = BUILD / f'{name}.norm.wav'
    y = x.copy()
    for _ in range(4):
        write_float(tmp, y)
        m = ffmpeg_measure(tmp)
        diff = target_lufs - m['I']
        if abs(diff) < 0.15 and true_peak_db(y) <= tp_ceiling + 0.05:
            break
        y = y * 10 ** (diff / 20)
        if true_peak_db(y) > tp_ceiling:
            y = limiter(y, ceiling_db=tp_ceiling - 0.2)
    return y, m


def json_dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
