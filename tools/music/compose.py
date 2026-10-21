# -*- coding: utf-8 -*-
"""反毒剪紙劇場｜配樂作曲（全部原創，程式寫譜）。

每首一個函式，回傳 dict：
  song        Song 物件（已排好音符）
  kind        'oneshot'（一次播完，檔尾自然收到靜音）或 'loop'（逐樣本無縫循環）
  length      成品秒數；loop 時為一圈的秒數
  target      整合響度目標（LUFS）
  fade_out    (開始秒, 長度秒)，只用在 oneshot
  render      fluidsynth 殘響設定
  sync        同步點說明（寫進 review/G3/music.md 與 metrics）

主調：D 大調五聲音階（D E F# A B）為骨幹，和弦 D、Bm7、Gmaj7、Asus4、Em7。
M1 小燈鎮主題（原創）：A4–B4–D5–E5–D5–B4 | A4–F#4–E4 ……
"""
from __future__ import annotations

import random

from common import Song, n

# ---------------------------------------------------------------- 共用素材
# 和弦配置：(低音, [琴的分解和弦四音], [墊音])
CH = {
    'D':     ('D2',  ['D3', 'A3', 'D4', 'F#4'], ['D3', 'A3', 'F#4']),
    'Bm7':   ('B1',  ['B2', 'F#3', 'A3', 'D4'], ['B2', 'F#3', 'D4']),
    'Gmaj7': ('G1',  ['G2', 'D3', 'F#3', 'B3'], ['G2', 'D3', 'B3']),
    'Asus4': ('A1',  ['A2', 'E3', 'A3', 'D4'], ['A2', 'E3', 'D4']),
    'Em7':   ('E2',  ['E3', 'B3', 'D4', 'G4'], ['E3', 'G3', 'D4']),
    'D/F#':  ('F#2', ['F#2', 'A3', 'D4', 'F#4'], ['F#3', 'A3', 'D4']),
    'G':     ('G1',  ['G2', 'D3', 'G3', 'B3'], ['G2', 'D3', 'B3']),
}

# M1 主題（拍數）：前 8 小節
M1_MELODY = [
    [('A4', 1.5), ('B4', .5), ('D5', .5), ('E5', .5), ('D5', .5), ('B4', .5)],
    [('A4', 2), ('F#4', 1), ('E4', 1)],
    [('F#4', 1), ('A4', .5), ('B4', .5), ('A4', 1.5), ('F#4', .5)],
    [('E4', 3), (None, 1)],
    [('A4', 1.5), ('B4', .5), ('D5', .5), ('E5', .5), ('F#5', 1)],
    [('E5', 1.5), ('D5', .5), ('B4', 1), ('D5', 1)],
    [('E5', 1), ('D5', .5), ('B4', .5), ('A4', 1), ('F#4', .5), ('E4', .5)],
    [('D4', 3), (None, 1)],
]

ARP = [0, 1, 2, 3, 1, 2, 3, 2]   # 八分音符分解型


def _hum(rng: random.Random, t: float, ms: float = 8.0) -> float:
    return t + rng.uniform(-ms, ms) / 1000.0


def _vel(rng: random.Random, v: float, spread: float = 4) -> int:
    return int(round(v + rng.uniform(-spread, spread)))


def play_phrase(s: Song, key: str, phrase, t0: float, beat: float, vel: float, rng, octave: int = 0):
    t = t0
    for note, b in phrase:
        if note is not None:
            p = n(note) + 12 * octave
            s.note(key, p, _hum(rng, t, 5), b * beat * 0.95, _vel(rng, vel, 3))
        t += b * beat
    return t


def koto_bar(s: Song, key: str, chord: str, t0: float, beat: float, vel: float, rng, pattern=ARP, beats: int = 4):
    notes = CH[chord][1]
    step = beat / 2
    for i in range(beats * 2):
        idx = pattern[i % len(pattern)]
        accent = 6 if i % 2 == 0 else 0
        s.note(key, notes[idx], _hum(rng, t0 + i * step, 6), step * 1.8, _vel(rng, vel + accent))


def harp_gliss(s: Song, key: str, notes, t0: float, t1: float, v0: float, v1: float, ring: float = 2.0):
    k = len(notes)
    for i, p in enumerate(notes):
        t = t0 + (t1 - t0) * i / max(1, k - 1)
        v = v0 + (v1 - v0) * i / max(1, k - 1)
        s.note(key, p, t, ring, v)


PENTA_UP = ['D3', 'E3', 'F#3', 'A3', 'B3', 'D4', 'E4', 'F#4', 'A4', 'B4', 'D5', 'E5', 'F#5', 'A5']


# ---------------------------------------------------------------- M1 小燈鎮主題（底樂循環）
def town(name='music_town', reps: int = 1, length_bars: int = 12):
    """96 BPM、12 小節 = 30.0 秒一圈；對白下的底樂。reps=3 用來算無縫循環。"""
    beat = 60 / 96
    bar = 4 * beat
    loop = length_bars * bar
    s = Song(name, loop * reps, tail=4.0)
    rng = random.Random(11)
    s.inst('koto', 'koto', volume=92, pan=48, reverb=55)
    s.inst('pizz', 'pizz', volume=88, pan=64, reverb=40)
    s.inst('flute', 'flute', volume=84, pan=80, reverb=70)
    s.inst('glock', 'glock', volume=70, pan=84, reverb=70)
    s.inst('pad', 'warmpad', volume=62, pan=64, reverb=60)
    s.inst('marimba', 'marimba', volume=80, pan=40, reverb=55)
    prog = ['D', 'Bm7', 'Gmaj7', 'Asus4', 'D', 'Bm7', ('Em7', 'Asus4'), 'D', 'Gmaj7', 'D/F#', 'Em7', 'Asus4']
    for r in range(reps):
        base = r * loop
        for b, ch in enumerate(prog):
            t0 = base + b * bar
            halves = ch if isinstance(ch, tuple) else (ch, ch)
            for h, c in enumerate(halves):
                th = t0 + h * 2 * beat
                bass, arp, padv = CH[c]
                # 撥弦低音：第 1、3 拍
                s.note('pizz', bass, _hum(rng, th, 4), beat * 0.6, _vel(rng, 62))
                s.note('pizz', n(bass) + 12 if b % 2 else n(bass) + 7, _hum(rng, th + beat, 4), beat * 0.5, _vel(rng, 50))
                # 琴：八分分解
                for i in range(4):
                    idx = ARP[(i + h * 4) % 8]
                    s.note('koto', arp[idx], _hum(rng, th + i * beat / 2, 6), beat * 0.9,
                           _vel(rng, 54 + (6 if i % 2 == 0 else 0)))
            # 墊音：每小節一個和弦
            c0 = halves[0]
            s.chord('pad', CH[c0][2], t0, bar * 0.98, vel=34)
            # 竹笛旋律：前 8 小節；後 4 小節留白給對白
            if b < 8:
                play_phrase(s, 'flute', M1_MELODY[b], t0, beat, 56 if b < 4 else 60, rng)
        # 鐵琴點綴
        for bb, p, v in ((0, 'D6', 40), (4, 'A5', 36), (8, 'D6', 38)):
            s.note('glock', p, base + bb * bar, 1.5, v)
        s.note('glock', 'A5', base + 11 * bar + 2 * beat, 0.6, 32)
        s.note('glock', 'B5', base + 11 * bar + 3 * beat, 0.6, 34)
        # 木琴回聲（第 9–11 小節，句頭動機上移）
        echo = [('A5', .5), ('B5', .5), ('D6', 1), (None, 2)]
        for bb in (8, 10):
            play_phrase(s, 'marimba', echo, base + bb * bar, beat, 46, rng)
    return {
        'song': s, 'kind': 'loop', 'length': loop, 'target': -24.0,
        'render': dict(reverb_room=0.6, reverb_level=0.5),
        'tempo': '96 BPM（4/4）', 'key': 'D 大調五聲音階',
        'mood': '溫暖、木質、平穩；紙燈節前一天的小鎮',
        'instruments': '箏（Koto）分解和弦、撥奏弦樂低音、長笛（代竹笛）主旋律、鐵琴點綴、木琴回聲、溫暖墊音',
        'sync': '一圈 30.0 秒（12 小節 × 2.5 秒）；第 1–8 小節（0–20 s）有笛聲旋律，第 9–12 小節（20–30 s）只剩伴奏與木琴回聲，留白給對白；循環接縫在 30.0 s。',
    }


# ---------------------------------------------------------------- 開幕
def opening(name='music_opening'):
    """120 BPM（1 拍 0.5 秒）。署名卡淡出 0–1 s → 布幕 1–3 s → 主題落點 3.0 s → 景片立起 3–7 s → 收在 D 和弦。"""
    beat = 0.5
    s = Song(name, 15.0, tail=3.0)
    rng = random.Random(21)
    s.inst('celesta', 'celesta', volume=80, pan=70, reverb=75)
    s.inst('harp', 'harp', volume=96, pan=56, reverb=70)
    s.inst('pad', 'warmpad', volume=70, pan=64, reverb=60)
    s.inst('koto', 'koto', volume=90, pan=46, reverb=55)
    s.inst('pizz', 'pizz', volume=92, pan=64, reverb=45)
    s.inst('flute', 'flute', volume=92, pan=78, reverb=70)
    s.inst('marimba', 'marimba', volume=90, pan=36, reverb=55)
    s.inst('glock', 'glock', volume=78, pan=86, reverb=70)
    # 0–1 s：署名卡淡出，鋼片琴兩聲
    s.note('celesta', 'A5', 0.12, 1.2, 40)
    s.note('celesta', 'D6', 0.60, 1.4, 44)
    # 墊音 0–3 s 漸強
    s.chord('pad', ['D3', 'A3', 'E4'], 0.0, 3.0, vel=50)
    s.expr('pad', 0.0, 3.0, 35, 100)
    # 1–3 s：布幕打開，豎琴五聲上行滑奏
    harp_gliss(s, 'harp', PENTA_UP, 1.0, 2.85, 38, 78, ring=2.4)
    # 3.0 s：主題落點
    prog = ['D', 'Bm7', 'Gmaj7', 'Asus4']
    for b, c in enumerate(prog):
        t0 = 3.0 + b * 4 * beat
        bass, arp, padv = CH[c]
        s.chord('pad', padv, t0, 4 * beat * 0.98, vel=40 if b else 48)
        s.note('pizz', bass, t0, beat * 0.7, 72)
        s.note('pizz', n(bass) + 7, t0 + 2 * beat, beat * 0.6, 58)
        koto_bar(s, 'koto', c, t0, beat, 56, rng)
        play_phrase(s, 'flute', [M1_MELODY[0], M1_MELODY[1],
                                 [('A4', 1.5), ('B4', .5), ('D5', .5), ('E5', .5), ('F#5', 1)],
                                 [('E5', 1.5), ('D5', .5), ('B4', 1), ('E5', 1)]][b],
                    t0, beat, 66, rng)
    s.expr('pad', 3.0, 3.1, 100, 80)
    # 3–7 s：景片立起，每 1.0 秒一個木琴＋鐵琴「立起」點
    pops = [(3.0, 'D5'), (4.0, 'E5'), (5.0, 'F#5'), (6.0, 'A5'), (7.0, 'B5')]
    for t, p in pops:
        s.note('marimba', p, t, 0.8, 70)
        s.note('glock', n(p) + 12, t + 0.004, 1.0, 38)
    # 11.0 s：收在 D（加九）和弦，延長後自然收尾
    t = 11.0
    s.note('flute', 'D5', t, 2.8, 62)
    s.expr('flute', 11.6, 13.8, 127, 40)
    s.chord('harp', ['D3', 'A3', 'D4', 'E4', 'F#4', 'A4'], t, 4.0, vel=58, roll=0.06)
    s.chord('koto', ['D4', 'F#4', 'A4', 'D5'], t + 0.02, 3.0, vel=48, roll=0.08)
    s.note('pizz', 'D2', t, 0.9, 70)
    s.note('glock', 'D6', t, 2.5, 44)
    s.chord('pad', ['D3', 'A3', 'F#4', 'E4'], t, 4.2, vel=46)
    s.expr('pad', 12.0, 14.6, 80, 20)
    return {
        'song': s, 'kind': 'oneshot', 'length': 15.0, 'target': -20.0, 'fade_out': (13.4, 1.6),
        'render': dict(reverb_room=0.62, reverb_level=0.55),
        'tempo': '120 BPM（1 拍 = 0.5 s）', 'key': 'D 大調五聲音階',
        'mood': '溫暖、節慶感（紙燈節開幕），明亮但不吵',
        'instruments': '鋼片琴、豎琴滑奏、溫暖墊音、箏分解和弦、撥奏弦樂、長笛主旋律、木琴＋鐵琴（景片立起點）',
        'sync': ('0.00–1.00 s 署名卡淡出（鋼片琴 0.12、0.60 s 兩聲）；1.00–2.85 s 布幕打開（豎琴五聲上行滑奏、墊音漸強）；'
                 '3.00 s 主題落點＝布幕全開（對上 S1）；景片立起點 3.0／4.0／5.0／6.0／7.0 s（木琴＋鐵琴各一聲，可對齊 5 片景片，'
                 '立起區間 3.0–7.5 s）；7.0–11.0 s 主題第二句；11.00 s 收在 D（加九）和弦；13.4–15.0 s 自然淡出，15.0 s 靜音結束。'),
    }


# ---------------------------------------------------------------- 閉幕
def closing(name='music_closing'):
    """布幕合攏 0–2 s → 2.0 s 署名卡出現，主題句頭慢慢回來 → 5.0 s 最後和弦 → 自然收尾。"""
    beat = 0.5
    s = Song(name, 10.0, tail=3.0)
    rng = random.Random(31)
    s.inst('harp', 'harp', volume=96, pan=56, reverb=70)
    s.inst('pad', 'warmpad', volume=70, pan=64, reverb=60)
    s.inst('flute', 'flute', volume=90, pan=76, reverb=72)
    s.inst('mbox', 'musicbox', volume=82, pan=84, reverb=72)
    s.inst('pizz', 'pizz', volume=90, pan=64, reverb=45)
    s.inst('glock', 'glock', volume=74, pan=86, reverb=70)
    s.inst('koto', 'koto', volume=86, pan=44, reverb=60)
    # 0–2 s：布幕合攏，豎琴下行滑奏
    down = ['A5', 'F#5', 'E5', 'D5', 'B4', 'A4', 'F#4', 'E4', 'D4', 'A3']
    harp_gliss(s, 'harp', down, 0.0, 1.7, 66, 42, ring=2.2)
    s.chord('pad', ['D3', 'A3', 'F#4'], 0.0, 2.0, vel=46)
    s.expr('pad', 0.0, 2.0, 70, 95)
    s.note('pizz', 'D2', 1.9, 0.6, 52)
    # 2.0 s：署名卡出現，主題句頭（長笛＋音樂盒高八度）
    phrase = [('A4', 1.5), ('B4', .5), ('D5', 1), ('B4', 1), ('A4', 1), ('F#4', .5), ('E4', .5)]
    play_phrase(s, 'flute', phrase, 2.0, beat, 60, rng)
    play_phrase(s, 'mbox', phrase, 2.0, beat, 52, rng, octave=1)
    for t0, c in ((2.0, 'D'), (3.0, 'Bm7'), (4.0, 'Gmaj7'), (4.5, 'Asus4')):
        dur = 1.0 if c != 'Asus4' else 0.5
        s.chord('pad', CH[c][2], t0, dur * 0.98, vel=40)
        s.note('pizz', CH[c][0], t0, 0.5, 56)
    # 5.0 s：最後和弦
    t = 5.0
    s.note('flute', 'D5', t, 2.6, 56)
    s.expr('flute', 5.6, 7.8, 127, 36)
    s.chord('harp', ['D3', 'A3', 'D4', 'F#4', 'A4', 'D5'], t, 4.0, vel=56, roll=0.07)
    s.chord('koto', ['D4', 'A4', 'E5'], t + 0.03, 3.0, vel=40, roll=0.1)
    s.note('mbox', 'D6', t, 2.5, 48)
    s.note('glock', 'A6', t + 0.4, 2.0, 30)
    s.note('pizz', 'D2', t, 0.9, 62)
    s.chord('pad', ['D3', 'A3', 'F#4'], t, 4.5, vel=44)
    s.expr('pad', 6.0, 9.4, 95, 15)
    return {
        'song': s, 'kind': 'oneshot', 'length': 10.0, 'target': -20.0, 'fade_out': (8.4, 1.6),
        'render': dict(reverb_room=0.66, reverb_level=0.58),
        'tempo': '120 BPM（1 拍 = 0.5 s）', 'key': 'D 大調五聲音階',
        'mood': '溫暖收束、安心；呼應開幕動機',
        'instruments': '豎琴下行滑奏、溫暖墊音、長笛＋音樂盒（高八度）主題句頭、撥奏弦樂、箏、鐵琴',
        'sync': ('0.00–1.70 s 布幕合攏（豎琴下行滑奏，布幕約 2 秒）；2.00 s 署名卡「許博明老師製作」出現＝主題句頭進入；'
                 '5.00 s 最後 D 和弦；8.4–10.0 s 自然淡出，10.0 s 靜音結束。'),
    }


# ---------------------------------------------------------------- M4 操偶線動機
def _ritard_beats(nbeats: int, d0: float, d1: float):
    ts, t = [], 0.0
    for k in range(nbeats + 1):
        ts.append(t)
        t += d0 + (d1 - d0) * k / max(1, nbeats - 1)
    return ts


def m4_strings(name='music_m4_strings'):
    """前段承接小鎮主題、配器變薄、漸慢（0–11 s）；中段稀疏留白（11–40 s）；乾淨長尾（40–46 s）。"""
    s = Song(name, 46.0, tail=4.0)
    rng = random.Random(41)
    s.inst('koto', 'koto', volume=63, pan=48, reverb=60)
    s.inst('flute', 'flute', volume=60, pan=78, reverb=72)
    s.inst('harp', 'harp', volume=80, pan=56, reverb=72)
    s.inst('pad', 'warmpad', volume=50, pan=64, reverb=62)
    s.inst('glock', 'glock', volume=48, pan=84, reverb=70)
    s.inst('pizzb', 'pizz', volume=65, pan=64, reverb=45)     # 小鎮低音（前段）
    s.inst('cellopz', 'pizz', volume=72, pan=58, reverb=55)   # 大提琴撥弦動機
    s.inst('bass', 'contrabass', volume=80, pan=64, reverb=55)
    s.inst('str', 'slowstrings', volume=88, pan=64, reverb=65)
    s.inst('cel', 'celesta', volume=58, pan=76, reverb=80)

    # ---- 前段：漸慢 0.62 → 0.95 秒／拍，共 14 拍 ≈ 11 秒
    T = _ritard_beats(14, 0.62, 0.95)

    def bt(x):  # 拍 → 秒（線性內插）
        i = int(x)
        if i >= len(T) - 1:
            return T[-1]
        return T[i] + (T[i + 1] - T[i]) * (x - i)

    # 箏：第 1 小節八分分解，第 2 小節只剩四分，之後停
    arp = CH['D'][1]
    for i in range(8):
        s.note('koto', arp[ARP[i]], bt(i * 0.5), 0.6, _vel(rng, 46 - i))
    for i, p in enumerate(CH['Bm7'][1]):
        s.note('koto', p, bt(4 + i), 0.9, _vel(rng, 36 - 2 * i))
    # 長笛：主題第 1、2 小節，逐漸變弱，第 8 拍後停
    x = 0.0
    for (p, b), v in zip(M1_MELODY[0] + M1_MELODY[1], (50, 48, 46, 46, 44, 44, 42, 38, 34)):
        s.note('flute', p, bt(x), bt(x + b) - bt(x) - 0.04, v)
        x += b
    # 豎琴：同一句尾慢慢重複一次（第 9–13 拍），停在 E（懸而未決但柔和）
    for xb, p, v in ((9, 'A4', 46), (10.5, 'F#4', 43), (12, 'E4', 41)):
        s.note('harp', p, bt(xb), 3.0, v)
    # 鐵琴只在開頭一聲
    s.note('glock', 'D6', 0.0, 1.5, 32)
    # 前段低音
    for xb, p, v in ((0, 'D2', 56), (2, 'A2', 46), (4, 'B1', 50), (6, 'F#2', 42), (8, 'G1', 44), (10, 'D2', 36)):
        s.note('pizzb', p, bt(xb), 0.5, v)
    # 墊音：D → Bm7 → Gmaj7 → Em7，表情慢慢收
    for xb0, xb1, c in ((0, 4, 'D'), (4, 8, 'Bm7'), (8, 12, 'Gmaj7'), (12, 14, 'Em7')):
        s.chord('pad', CH[c][2], bt(xb0), bt(xb1) - bt(xb0) + (1.2 if c == 'Em7' else 0.3), vel=36)
    s.expr('pad', 0.0, 13.0, 100, 70)
    a_end = bt(14)   # ≈ 11 s

    # ---- 中段：稀疏、留白（和弦都是三和弦或開放五度，沒有低音不協和團塊）
    plan = [(11.0, 19.0, 'B1', ['B2', 'F#3', 'D4']),
            (19.0, 27.0, 'G1', ['G2', 'D3', 'B3']),
            (27.0, 34.0, 'E2', ['E3', 'G3', 'B3']),
            (34.0, 40.0, 'A1', ['A2', 'E3', 'D4'])]
    s.chord('str', ['B2', 'F#3', 'D4'], bt(6), bt(8) - bt(6) + 0.2, vel=50)   # 弦樂在前段後半悄悄進來
    s.chord('str', ['G2', 'D3', 'B3'], bt(8), 11.0 - bt(8) + 0.3, vel=50)
    s.expr('str', bt(6), 11.0, 40, 66)
    for t0, t1, b, chord in plan:
        s.note('bass', b, t0, t1 - t0 + 0.4, 38)
        s.expr('bass', t0, t0 + 1.6, 45 if t0 == 11.0 else 75, 110, steps=12)
        s.chord('str', chord, t0, t1 - t0 + 0.4, vel=40)
    # 弦樂呼吸：每個和弦中間微微起伏（±8，不突增）
    for t0, t1, _, _ in plan:
        mid = (t0 + t1) / 2
        s.expr('str', t0, mid, 60, 70, steps=12)
        s.expr('str', mid, t1, 70, 60, steps=12)
    # 大提琴撥弦「拉線」動機：低→上四度；一段時間後輕輕下行三音
    tug = [(11.5, 'F#2'), (11.95, 'B2'), (15.0, 'D3'), (15.45, 'B2'), (16.0, 'F#2'),
           (19.5, 'D2'), (19.95, 'G2'), (23.0, 'B2'), (23.45, 'A2'), (24.0, 'G2'),
           (27.5, 'B1'), (27.95, 'E2'), (30.5, 'G2'), (30.95, 'F#2'), (31.5, 'E2'),
           (34.5, 'E2'), (34.95, 'A2'), (37.5, 'D3'), (37.95, 'B2'), (38.5, 'A2')]
    for t, p in tug:
        s.note('cellopz', p, t, 0.7, _vel(rng, 40, 3))
    # 線上的微光：鋼片琴很輕的單音
    for t, p in ((14.0, 'F#5'), (22.0, 'B5'), (30.0, 'G5'), (38.0, 'E5')):
        s.note('cel', p, t, 2.0, 30)

    # ---- 尾段：停在 G（加九），乾淨長尾
    t = 40.0
    s.note('bass', 'G1', t, 4.6, 34)
    s.chord('str', ['G2', 'D3', 'B3'], t, 4.8, vel=36)
    s.expr('str', 40.0, 45.0, 60, 0)
    s.chord('harp', ['G2', 'D3', 'B3', 'A4'], t, 4.0, vel=28, roll=0.12)
    s.note('cellopz', 'G2', t, 0.7, 34)
    return {
        'song': s, 'kind': 'oneshot', 'length': 46.0, 'target': -24.0, 'fade_out': (43.5, 2.5),
        'render': dict(reverb_room=0.7, reverb_level=0.55, reverb_damp=0.45),
        'tempo': '前段 97 → 63 BPM 漸慢；中段自由速度（約每 3.5–4 秒一個撥弦短句）',
        'key': 'D 大調 → B 小調（關係小調）→ 停在 G（加九）',
        'mood': '收束、懸念但不恐怖；把空間留給對白',
        'instruments': '前段：箏、長笛、豎琴、撥奏低音、墊音、鐵琴一聲；中段：低音提琴長音、慢速弦樂墊、大提琴撥弦（GM 撥奏弦樂低音域）、鋼片琴微光',
        'sync': (f'0.0–{a_end:.1f} s 承接小鎮主題、配器逐層退出、漸慢（箏 0–3 s 退場、長笛約 6 s 退場、鐵琴只在 0.0 s）；'
                 '約 4.2 s 起弦樂悄悄進來；11.0 s 起中段稀疏（和弦 11.0 Bm／19.0 G／27.0 Em／34.0 Asus4，'
                 '撥弦短句 11.5、15.0、19.5、23.0、27.5、30.5、34.5、37.5 s）；40.0 s 停在 G（加九）；43.5–46.0 s 淡到靜音。'
                 '紙繩落下若在中段，可對齊任一撥弦短句；沒有驚嚇點，沒有重擊。'),
    }


def m4_light(name='music_m4_light', reps: int = 1):
    """a2_c004 用的很輕版本：只有長音與偶爾的撥弦，32 秒無縫循環。"""
    loop = 32.0
    s = Song(name, loop * reps, tail=5.0)
    rng = random.Random(42)
    s.inst('bass', 'contrabass', volume=78, pan=64, reverb=55)
    s.inst('str', 'slowstrings', volume=66, pan=64, reverb=65)
    s.inst('cellopz', 'pizz', volume=72, pan=58, reverb=55)
    s.inst('cel', 'celesta', volume=52, pan=76, reverb=80)
    for r in range(reps):
        base = r * loop
        for t0, b, chord in ((0.0, 'B1', ['B2', 'F#3', 'D4']), (16.0, 'G1', ['G2', 'D3', 'B3'])):
            s.note('bass', b, base + t0, 16.0, 38)
            s.chord('str', chord, base + t0, 16.0, vel=32)
            s.expr('str', base + t0, base + t0 + 8, 54, 64, steps=12)
            s.expr('str', base + t0 + 8, base + t0 + 16, 64, 54, steps=12)
        for t, p in ((2.0, 'F#2'), (2.45, 'B2'), (9.0, 'D3'), (9.45, 'B2'), (10.0, 'F#2'),
                     (18.0, 'D2'), (18.45, 'G2'), (25.0, 'B2'), (25.45, 'A2'), (26.0, 'G2')):
            s.note('cellopz', p, base + t, 0.7, _vel(rng, 44, 2))
        s.note('cel', 'F#5', base + 6.0, 2.0, 24)
        s.note('cel', 'D5', base + 22.0, 2.0, 24)
    return {
        'song': s, 'kind': 'loop', 'length': loop, 'target': -24.0,
        'render': dict(reverb_room=0.7, reverb_level=0.55, reverb_damp=0.45),
        'tempo': '自由速度（長音 16 秒換一次和弦）', 'key': 'B 小調 → G 大調',
        'mood': '很輕的靜止張力；停格等老師時也不打擾',
        'instruments': '低音提琴長音、慢速弦樂墊、大提琴撥弦（極輕）、鋼片琴微光',
        'sync': '一圈 32.0 秒；0.0 s Bm、16.0 s G；撥弦短句 2.0、9.0、18.0、25.0 s；循環接縫在 32.0 s。v01 整合響度刻意比底樂低 3 LU（−27 LUFS）；v02（G3 修正第 1 輪）改回底樂同級 −24 LUFS：'
                '避讓 0.56 下必要旁白比背景高約 17 LU、句間停頓背景約 −32 LUFS（v01 是 20 LU、−35～−37），停格時改由引擎淡到 0.10×。',
    }


# ---------------------------------------------------------------- 草稿（10–20 秒，標明草稿）
def draft_m2_zhezhe(name='music_m2_zhezhe'):
    """M2 折折動機草稿：撥弦跳音＋木魚，短句。"""
    beat = 60 / 132
    s = Song(name, 9.5, tail=2.5)
    rng = random.Random(52)
    s.inst('pizz', 'pizz', volume=96, pan=60, reverb=40)
    s.inst('wood', 'woodblock', volume=70, pan=72, reverb=35)
    s.inst('marimba', 'marimba', volume=86, pan=40, reverb=45)
    s.inst('kalimba', 'kalimba', volume=80, pan=84, reverb=55)
    motif = [('D4', .5), ('F#4', .5), ('A4', .5), (None, .5), ('B4', .25), ('A4', .25), ('F#4', .5), ('E4', .5), (None, .5)]
    motif2 = [('E4', .5), ('A4', .5), ('B4', .5), (None, .5), ('D5', .25), ('B4', .25), ('A4', .5), ('D4', .5), (None, .5)]
    t = 0.2
    for m in (motif, motif2, motif, motif2):
        play_phrase(s, 'pizz', m, t, beat, 70, rng)
        play_phrase(s, 'kalimba', m, t, beat, 42, rng, octave=1)
        t += 4 * beat
    for i in range(int((t - 0.2) / beat)):
        tt = 0.2 + i * beat
        if i % 4 in (0, 3):
            s.note('wood', 'E5' if i % 4 == 0 else 'A5', tt, 0.1, 40)
    for i, c in enumerate(['D', 'Asus4', 'D', 'Asus4']):
        s.note('marimba', CH[c][0], 0.2 + i * 4 * beat, beat, 55)
    s.note('marimba', 'D4', t, 1.0, 50)
    s.note('kalimba', 'D6', t, 1.5, 40)
    return {
        'song': s, 'kind': 'oneshot', 'length': 9.5, 'target': -24.0, 'fade_out': (8.3, 1.2), 'draft': True,
        'render': dict(reverb_room=0.5, reverb_level=0.45),
        'tempo': '132 BPM', 'key': 'D 大調五聲音階', 'mood': '俏皮、輕巧（草稿）',
        'instruments': '撥奏弦樂跳音、卡林巴、木魚（GM Woodblock）、木琴低音',
        'sync': '草稿：4 個短句各約 1.8 s，第 7.5 s 收在 D；尚未對任何 cue。',
    }


def draft_m3_shiny(name='music_m3_shiny'):
    """M3 閃亮動機草稿：音樂盒、和聲略不穩，不恐怖、無低頻轟鳴。"""
    s = Song(name, 14.0, tail=3.0)
    rng = random.Random(53)
    s.inst('mbox', 'musicbox', volume=86, pan=70, reverb=70)
    s.inst('vibes', 'vibes', volume=70, pan=50, reverb=70)
    s.inst('pad', 'warmpad', volume=52, pan=64, reverb=60)
    beat = 0.55
    # 全音階味道的閃亮小句（不穩但不陰森），都在中高音域
    ph = [('E5', .5), ('F#5', .5), ('G#5', .5), ('B5', 1), (None, .5), ('A#5', .5), ('G#5', .5), ('F#5', 1.5), (None, .5)]
    t = 0.3
    for k in range(3):
        play_phrase(s, 'mbox', ph, t, beat, 52 - 4 * k, rng)
        t += 6 * beat
    s.chord('vibes', ['E4', 'G#4', 'C5'], 0.3, 6 * beat + 0.6, vel=26)
    s.chord('vibes', ['D4', 'F#4', 'A#4'], 0.3 + 6 * beat, 6 * beat + 0.6, vel=26)
    s.chord('vibes', ['E4', 'G#4', 'C5'], 0.3 + 12 * beat, 6 * beat, vel=24)
    s.chord('pad', ['E4', 'B4'], 0.3, 12.0, vel=44)
    return {
        'song': s, 'kind': 'oneshot', 'length': 14.0, 'target': -24.0, 'fade_out': (11.5, 2.5), 'draft': True,
        'render': dict(reverb_room=0.65, reverb_level=0.6),
        'tempo': '約 109 BPM', 'key': 'E 全音階色彩（增三和弦）', 'mood': '亮晶晶、有點不穩、讓人想靠近但不安心（草稿；不恐怖、無低頻）',
        'instruments': '音樂盒、顫音琴增三和弦、極輕墊音',
        'sync': '草稿：三次同一小句，約每 3.3 秒一次；尚未對 cue。',
    }


def draft_m6_courage(name='music_m6_courage'):
    """M6 勇氣動機草稿：M1 的上行變奏，穩定。"""
    beat = 60 / 100
    s = Song(name, 16.0, tail=3.0)
    rng = random.Random(56)
    s.inst('koto', 'koto', volume=88, pan=46, reverb=55)
    s.inst('flute', 'flute', volume=88, pan=78, reverb=68)
    s.inst('pizz', 'pizz', volume=90, pan=64, reverb=42)
    s.inst('strings', 'strings', volume=66, pan=64, reverb=60)
    s.inst('glock', 'glock', volume=70, pan=86, reverb=70)
    mel = [[('D4', 1), ('E4', 1), ('F#4', 1), ('A4', 1)],
           [('B4', 1.5), ('A4', .5), ('D5', 2)],
           [('E5', 1), ('D5', .5), ('B4', .5), ('A4', 1), ('B4', 1)],
           [('D5', 3), (None, 1)],
           [('E5', 1), ('F#5', 1), ('E5', .5), ('D5', .5), ('B4', 1)],
           [('D5', 4)]]
    prog = ['D', 'Gmaj7', 'Em7', 'Asus4', 'Gmaj7', 'D']
    for b, c in enumerate(prog):
        t0 = 0.2 + b * 4 * beat
        koto_bar(s, 'koto', c, t0, beat, 52, rng)
        s.note('pizz', CH[c][0], t0, beat * 0.7, 64)
        s.note('pizz', n(CH[c][0]) + 7, t0 + 2 * beat, beat * 0.6, 52)
        s.chord('strings', CH[c][2], t0, 4 * beat * 0.98, vel=40)
        play_phrase(s, 'flute', mel[b], t0, beat, 62, rng)
    s.note('glock', 'D6', 0.2 + 3 * 4 * beat, 1.5, 36)
    s.note('glock', 'A6', 0.2 + 5 * 4 * beat, 2.0, 34)
    return {
        'song': s, 'kind': 'oneshot', 'length': 16.0, 'target': -24.0, 'fade_out': (14.4, 1.6), 'draft': True,
        'render': dict(reverb_room=0.6, reverb_level=0.5),
        'tempo': '100 BPM', 'key': 'D 大調五聲音階', 'mood': '穩定、有勇氣、往前走（草稿）',
        'instruments': '箏、長笛、撥奏弦樂、弦樂合奏墊、鐵琴',
        'sync': '草稿：6 小節，每小節 2.4 s；尚未對 cue。',
    }


def draft_m7_recovery(name='music_m7_recovery'):
    """M7 復原動機草稿：M1 慢版鋼琴＋弦。"""
    beat = 60 / 66
    s = Song(name, 20.0, tail=4.0)
    rng = random.Random(57)
    s.inst('piano', 'piano', volume=80, pan=58, reverb=70)
    s.inst('strings', 'slowstrings', volume=70, pan=64, reverb=65)
    s.inst('cello', 'cello', volume=66, pan=50, reverb=62)
    prog = ['D', 'Bm7', 'Gmaj7', 'Asus4', 'D']
    for b, c in enumerate(prog[:4]):
        t0 = 0.3 + b * 4 * beat
        s.chord('strings', CH[c][2], t0, 4 * beat, vel=34)
        s.note('cello', n(CH[c][0]) + 12, t0, 4 * beat * 0.95, 40)
        play_phrase(s, 'piano', M1_MELODY[b], t0, beat, 48, rng)
        for i, idx in enumerate([0, 2, 3, 2]):
            s.note('piano', CH[c][1][idx], t0 + i * beat, beat * 1.5, 30)
    t = 0.3 + 16 * beat
    s.chord('piano', ['D3', 'A3', 'D4', 'F#4', 'D5'], t, 3.0, vel=40, roll=0.08)
    s.chord('strings', ['D3', 'A3', 'F#4'], t, 2.5, vel=32)
    return {
        'song': s, 'kind': 'oneshot', 'length': 20.0, 'target': -24.0, 'fade_out': (18.0, 2.0), 'draft': True,
        'render': dict(reverb_room=0.7, reverb_level=0.6),
        'tempo': '66 BPM', 'key': 'D 大調', 'mood': '安靜、慢慢好起來（草稿）',
        'instruments': '鋼琴（M1 慢版）、慢速弦樂、大提琴',
        'sync': '草稿：4 小節 M1 慢版，約 14.8 s 收在 D；尚未對 cue。',
    }


def draft_m5_road(name='music_m5_road'):
    """M5 紙上的路動機草稿：木塊輕打擊的規律節奏，緊張但不像警報；不用時鐘滴答。"""
    beat = 60 / 104
    s = Song(name, 14.0, tail=2.5)
    rng = random.Random(55)
    s.inst('wood', 'woodblock', volume=62, pan=60, reverb=35)
    s.inst('marimba', 'marimba', volume=80, pan=44, reverb=45)
    s.inst('pizz', 'pizz', volume=86, pan=64, reverb=40)
    s.inst('str', 'strings', volume=58, pan=64, reverb=55)
    # 不規則重音（3+3+2），避免時鐘滴答感
    acc = [1, 0, 0, 1, 0, 0, 1, 0]
    nbars = 6
    for b in range(nbars):
        t0 = 0.2 + b * 4 * beat
        for i in range(8):
            if acc[i] or i == 7:
                s.note('wood', 'E5' if acc[i] else 'G5', _hum(rng, t0 + i * beat / 2, 3), 0.08, 40 if acc[i] else 26)
        root = ['B1', 'B1', 'G1', 'A1', 'B1', 'F#2'][b]
        s.note('pizz', root, t0, beat * 0.6, 58)
        s.note('pizz', n(root) + 7, t0 + 1.5 * beat, beat * 0.5, 46)
        s.note('pizz', n(root) + 12, t0 + 3 * beat, beat * 0.5, 46)
        for i, p in enumerate((['B3', 'D4', 'F#4'] if b % 2 == 0 else ['A3', 'D4', 'E4'])):
            s.note('marimba', p, t0 + (i * 1.5) * beat / 2 * 2, beat * 0.4, 40)
    s.chord('str', ['B2', 'F#3'], 0.2, nbars * 4 * beat, vel=30)
    return {
        'song': s, 'kind': 'oneshot', 'length': 14.0, 'target': -24.0, 'fade_out': (12.0, 2.0), 'draft': True,
        'render': dict(reverb_room=0.45, reverb_level=0.4),
        'tempo': '104 BPM（3+3+2 重音）', 'key': 'B 小調', 'mood': '專注、有點緊張但不像警報（草稿）',
        'instruments': '木魚／木塊（3+3+2 不規則重音，不用時鐘滴答）、木琴、撥奏弦樂、弦樂長音',
        'sync': '草稿：6 小節，每小節約 2.3 s；凍結時由引擎停止配樂；尚未對 cue。',
    }


def draft_m1_bows(name='music_m1_bows'):
    """M1 謝幕版草稿：全編制、溫暖，最後和弦。"""
    beat = 60 / 104
    s = Song(name, 20.0, tail=3.0)
    rng = random.Random(58)
    s.inst('koto', 'koto', volume=88, pan=44, reverb=55)
    s.inst('harp', 'harp', volume=84, pan=56, reverb=65)
    s.inst('flute', 'flute', volume=90, pan=78, reverb=68)
    s.inst('pizz', 'pizz', volume=90, pan=64, reverb=42)
    s.inst('strings', 'strings', volume=66, pan=64, reverb=60)
    s.inst('glock', 'glock', volume=72, pan=86, reverb=70)
    s.inst('marimba', 'marimba', volume=78, pan=36, reverb=50)
    prog = ['D', 'Bm7', 'Gmaj7', 'Asus4', 'D', 'Bm7', ('Em7', 'Asus4')]
    for b, ch in enumerate(prog):
        t0 = 0.2 + b * 4 * beat
        halves = ch if isinstance(ch, tuple) else (ch, ch)
        for h, c in enumerate(halves):
            th = t0 + h * 2 * beat
            s.note('pizz', CH[c][0], th, beat * 0.6, 66)
            for i in range(4):
                s.note('koto', CH[c][1][ARP[(i + 4 * h) % 8]], _hum(rng, th + i * beat / 2), beat * 0.9, _vel(rng, 54))
        s.chord('strings', CH[halves[0]][2], t0, 4 * beat * 0.98, vel=44)
        play_phrase(s, 'flute', M1_MELODY[b], t0, beat, 66, rng)
        play_phrase(s, 'marimba', M1_MELODY[b], t0, beat, 40, rng, octave=1) if b >= 4 else None
    t = 0.2 + 7 * 4 * beat
    s.note('flute', 'D5', t, 3.0, 64)
    s.chord('harp', ['D3', 'A3', 'D4', 'E4', 'F#4', 'A4', 'D5'], t, 4.0, vel=60, roll=0.06)
    s.note('glock', 'D6', t, 2.5, 44)
    s.note('pizz', 'D2', t, 1.0, 70)
    s.chord('strings', ['D3', 'A3', 'F#4'], t, 3.5, vel=42)
    return {
        'song': s, 'kind': 'oneshot', 'length': 20.0, 'target': -20.0, 'fade_out': (18.2, 1.8), 'draft': True,
        'render': dict(reverb_room=0.62, reverb_level=0.55),
        'tempo': '104 BPM', 'key': 'D 大調五聲音階', 'mood': '溫暖、全員謝幕（草稿）',
        'instruments': '箏、豎琴、長笛＋木琴（主題）、撥奏弦樂、弦樂合奏、鐵琴',
        'sync': '草稿：7 小節主題後約 16.4 s 收在 D 和弦；尚未對 cue。',
    }


PIECES = {
    'music_opening': opening,
    'music_town': town,
    'music_m4_strings': m4_strings,
    'music_m4_light': m4_light,
    'music_closing': closing,
    # 草稿
    'music_m2_zhezhe': draft_m2_zhezhe,
    'music_m3_shiny': draft_m3_shiny,
    'music_m5_road': draft_m5_road,
    'music_m6_courage': draft_m6_courage,
    'music_m7_recovery': draft_m7_recovery,
    'music_m1_bows': draft_m1_bows,
}
LOOPS = {'music_town': town, 'music_m4_light': m4_light}
