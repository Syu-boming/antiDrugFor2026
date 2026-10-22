"""逐字聲調量測（「燈」讀音檢查，2026-10-22）：large-v3-turbo 字級時間戳＋parselmouth F0。

用法（專案根目錄）：
  tools/.venv/bin/python tools/vo_tone_check.py --file audio/vo/vo_a0_c002_03_v04.wav --id a0_c002_03 [--dump]
  （主要給 review/G3/el/deng/ 的量測腳本 import：measure_file()、classify()）

做法：
  1. faster-whisper large-v3-turbo（word_timestamps）→ 字詞時間；多字詞平均攤成逐字；用 difflib 和劇本原文（去標點）逐字對齊
     （等長 replace 一對一，容許同音字）。
  2. parselmouth 自相關 F0（5 ms；地板／天花板依該檔中位數 ×0.5／×2 第二次估算，避免八度跳）。
  3. 每個字的音節核心：whisper 字窗前後放寬 40 ms 內，取和字窗重疊最多的有聲段，再裁到字窗 ±30 ms，頭尾各去掉 10%
     （避開聲母過渡與連音）；至少 40 ms 有聲。
  4. 特徵（半音，相對該檔 F0 中位數）：起點（前 25% 平均）、終點（後 25% 平均）、變化量、斜率（線性迴歸，半音／秒）、
     平均高低、在該檔音域（p10–p90）中的位置（0＝p10、1＝p90）。
判定（classify）：以同一檔中參考字（劇本中依 pypinyin 為第一聲、第四聲的字，排除一、不與句末字）的特徵當基準。
聽感一律未驗證（Claude 聽不到聲音）；這是聲學量測，不等於聽感。
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402

SR = V.SR
_MODEL = None


def word_times(x: np.ndarray) -> list[tuple[str, float, float]]:
    global _MODEL
    from faster_whisper import WhisperModel
    if _MODEL is None:
        _MODEL = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    a16 = V.resample(x.astype(np.float32), SR, 16000)
    segs, _ = _MODEL.transcribe(a16, language="zh", beam_size=5, word_timestamps=True,
                                initial_prompt="以下是繁體中文的台灣華語。")
    return [(w.word, float(w.start), float(w.end)) for s in segs for w in (s.words or [])]


def char_times(x: np.ndarray):
    hc, hs, he = [], [], []
    for w, s, e in word_times(x):
        t = V.PUNCT_RE.sub("", V._to_trad(w)).replace("119", "一一九").translate(V.DIGITS)
        if not t:
            continue
        d = (e - s) / len(t)
        for i, ch in enumerate(t):
            hc.append(ch)
            hs.append(s + i * d)
            he.append(s + (i + 1) * d)
    return hc, hs, he


def char_map(ref: str, hyp: str) -> dict[int, int]:
    mp = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if op in ("equal", "replace"):
            for d in range(min(i2 - i1, j2 - j1)):
                mp[i1 + d] = j1 + d
    return mp


def pitch_track(x: np.ndarray):
    import parselmouth
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=SR)
    p0 = snd.to_pitch_ac(time_step=0.01, pitch_floor=60, pitch_ceiling=700)
    f = p0.selected_array["frequency"]
    med = float(np.median(f[f > 0])) if np.any(f > 0) else 150.0
    p = snd.to_pitch_ac(time_step=0.005, pitch_floor=max(50.0, med * 0.5), pitch_ceiling=min(900.0, med * 2.0))
    return p.xs(), p.selected_array["frequency"]


def nucleus(t: np.ndarray, f: np.ndarray, s: float, e: float):
    """回傳 (時間, F0) 的音節核心；找不到回傳 None。"""
    win = (t >= s - 0.04) & (t <= e + 0.04)
    idx = np.nonzero(win)[0]
    if not len(idx):
        return None
    runs, cur = [], []
    for i in idx:
        if f[i] > 0:
            cur.append(i)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if not runs:
        return None

    def ov(r):
        a, b = t[r[0]], t[r[-1]]
        return max(0.0, min(b, e) - max(a, s))
    r = max(runs, key=ov)
    r = [i for i in r if s - 0.03 <= t[i] <= e + 0.03]
    if len(r) < 4:
        return None
    n = len(r)
    r = r[int(n * 0.10): n - int(n * 0.10)]
    if len(r) < 8:     # < 40 ms
        return None
    return t[r], f[r]


def features(tt: np.ndarray, ff: np.ndarray, med: float, p10: float, p90: float) -> dict:
    st = 12 * np.log2(ff / med)
    q = max(2, len(st) // 4)
    a, b = float(st[:q].mean()), float(st[-q:].mean())
    slope = float(np.polyfit(tt - tt[0], st, 1)[0])
    lo, hi = 12 * np.log2(p10 / med), 12 * np.log2(p90 / med)
    mean = float(st.mean())
    k = max(3, int(len(st) * 0.4))
    tail_slope = float(np.polyfit(tt[-k:] - tt[-k], st[-k:], 1)[0])
    imax = int(np.argmax(st))
    fall = float(st[imax] - st[imax:].min())          # 最高點之後的最大下降
    imin = int(np.argmin(st))
    rise = float(st[imin:].max() - st[imin])          # 最低點之後的最大上升
    return {"t0": round(float(tt[0]), 3), "t1": round(float(tt[-1]), 3), "dur_ms": round(float(tt[-1] - tt[0]) * 1000),
            "f0_start_hz": round(float(np.mean(ff[:q])), 1), "f0_end_hz": round(float(np.mean(ff[-q:])), 1),
            "start_st": round(a, 2), "end_st": round(b, 2), "delta_st": round(b - a, 2), "slope_st_s": round(slope, 1),
            "mean_st": round(mean, 2), "fall_st": round(fall, 2), "rise_st": round(rise, 2),
            "tail_slope_st_s": round(tail_slope, 1), "min_st": round(float(st.min()), 2), "max_st": round(float(st.max()), 2),
            "range_pos": round((mean - lo) / max(0.5, hi - lo), 2),
            "start_pos": round((a - lo) / max(0.5, hi - lo), 2), "end_pos": round((b - lo) / max(0.5, hi - lo), 2)}


def tones_of(text: str) -> list[int]:
    from pypinyin import Style, lazy_pinyin
    out = []
    for ch in text:
        p = lazy_pinyin(ch, style=Style.TONE3, neutral_tone_with_five=True, errors=lambda x: list(x))[0]
        out.append(int(p[-1]) if p and p[-1].isdigit() else 0)
    return out


def measure_file(wav: Path, text: str, target: str = "燈", windows=None) -> dict:
    """回傳每個字的特徵與 target 字的索引。windows＝之前存下的 (asr, [(s, e) or None]…) 可省掉轉寫。"""
    x = V.read_wav(wav)
    ref = V.PUNCT_RE.sub("", text)
    if windows is None:
        hc, hs, he = char_times(x)
        hyp = "".join(hc)
        mp = char_map(ref, hyp)
    else:
        hyp, wins = windows
        hc, hs, he, mp = [], [], [], {}
        for i, w in enumerate(wins):
            if w:
                mp[i] = len(hc)
                hc.append(w[2] if len(w) > 2 else ref[i])
                hs.append(w[0])
                he.append(w[1])
    t, f = pitch_track(x)
    v = f[f > 0]
    med, p10, p90 = float(np.median(v)), float(np.percentile(v, 10)), float(np.percentile(v, 90))
    tones = tones_of(ref)
    chars = []
    for i, ch in enumerate(ref):
        e = {"i": i, "ch": ch, "tone": tones[i], "last": i == len(ref) - 1}
        if i in mp:
            j = mp[i]
            e.update(asr=hc[j], s=round(hs[j], 3), e=round(he[j], 3))
            nu = nucleus(t, f, hs[j], he[j])
            if nu is not None:
                e.update(features(nu[0], nu[1], med, p10, p90))
        chars.append(e)
    tgt = [i for i, ch in enumerate(ref) if ch == target]
    return {"file": str(wav), "text": text, "asr": hyp, "f0_median": round(med, 1), "f0_p10": round(p10, 1),
            "f0_p90": round(p90, 1), "chars": chars, "targets": tgt}


def vs_tone1(chars: list[dict], i: int) -> dict:
    """目標字平均高低 − 同句其他一聲字（非句末、排除一、不與目標字）平均高低（半音）。"""
    v = [c["mean_st"] for c in chars if c["tone"] == 1 and "mean_st" in c and not c["last"] and c["ch"] not in "一不燈"
         and c["i"] != i]
    c = chars[i]
    if not v or "mean_st" not in c:
        return {"n": len(v), "diff_st": None}
    return {"n": len(v), "diff_st": round(c["mean_st"] - float(np.mean(v)), 1)}


def ref_stats(chars: list[dict], exclude: set[int]) -> dict:
    """同一檔參考字（第一聲／第四聲；排除一、不、句末字與目標字）的特徵中位數。"""
    out = {}
    for tone in (1, 4):
        sel = [c for c in chars if c["tone"] == tone and "delta_st" in c and c["ch"] not in "一不"
               and not c["last"] and c["i"] not in exclude]
        if sel:
            out[tone] = {"n": len(sel), "delta_st": round(float(np.median([c["delta_st"] for c in sel])), 2),
                         "start_pos": round(float(np.median([c["start_pos"] for c in sel])), 2),
                         "range_pos": round(float(np.median([c["range_pos"] for c in sel])), 2),
                         "chars": "".join(c["ch"] for c in sel)}
    return out


def classify(c: dict, refs: dict | None = None) -> tuple[str, str]:
    """規則（台灣華語：一聲高平 55、四聲高降 51、三聲低降 21）。基準：a0_c002_03（使用者聽到念成「鄧」）的「燈」最高點後下降
    約 5 半音、起點在音域上段；使用者認可的「紙登結」（a0_c001_01、a0_c003_01）與其他送「登」的參考句，接在三聲字後面時是
    平或小幅上升（變化 −1～＋2.7 半音，平均位置 0.2–0.9）。
       最高點後下降 ≥ 2.5 半音、整體變化 ≤ −2.0、起點在音域中上（start_pos ≥ 0.5）→ 疑似第四聲；
       平均位置 < 0.10，或位置 < 0.35 且下降 ≥ 1.5 半音（低降）→ 疑似第三聲；
       最低點後上升 ≥ 4.0 半音而且尾段仍在上升（尾段斜率 > 15 半音／秒，沒有平段）→ 無法判定（可能聽成第二聲）；
       |整體變化| < 2.8 半音、最高點後下降 < 2.5 → 第一聲；其餘或量不到 → 無法判定。
    低平（平均位置 0.1–0.3）不單獨判成三聲：使用者認可的 a0_c001_01「紙登結」的「登」平均位置 0.27、比同句一聲字平均低 6.1 半音，
    a0_c003_01 低 4.5 半音——接在三聲字後面的一聲在這些聲線裡本來就落在低處。"""
    if "delta_st" not in c:
        return "無法判定", "量不到有聲音節核心（時間戳對不上或太短）"
    d, sp, rp, fa, ri, ts = c["delta_st"], c["start_pos"], c["range_pos"], c["fall_st"], c["rise_st"], c["tail_slope_st_s"]
    why = (f"變化 {d:+.1f} 半音（最高點後降 {fa:.1f}、最低點後升 {ri:.1f}；尾段斜率 {ts:+.0f} 半音／秒）、"
           f"起點位置 {sp:.2f}、平均位置 {rp:.2f}（0＝該句 p10、1＝p90）")
    if fa >= 2.5 and d <= -2.0 and sp >= 0.5:
        return "疑似第四聲", why
    if rp < 0.10 or (rp < 0.35 and d <= -1.5):
        return "疑似第三聲", why
    if ri >= 4.0 and ts > 15:
        return "無法判定", why + "；一路上升沒有平段，可能聽成第二聲"
    if abs(d) < 2.8 and fa < 2.5:
        return "第一聲", why
    return "無法判定", why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--target", default="燈")
    ap.add_argument("--dump", action="store_true")
    a = ap.parse_args()
    text = V.load_lines()[a.id]["text"]
    r = measure_file(Path(a.file), text, a.target)
    print("ASR:", r["asr"], "F0 median", r["f0_median"], "p10", r["f0_p10"], "p90", r["f0_p90"])
    for c in r["chars"]:
        if a.dump or c["i"] in r["targets"]:
            print(c["i"], c["ch"], c["tone"], c.get("s"), c.get("e"),
                  {k: c.get(k) for k in ("start_st", "end_st", "delta_st", "slope_st_s", "range_pos", "start_pos", "dur_ms")},
                  classify(c)[0] if c["i"] in r["targets"] else "")
    print("參考字：", ref_stats(r["chars"], set(r["targets"])))


if __name__ == "__main__":
    main()
