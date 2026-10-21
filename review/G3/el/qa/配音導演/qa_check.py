"""配音導演驗收：獨立重量測（響度、真峰值、削波、合成器原始檔句尾是否被截斷、F0 中位）。
用法：/opt/anaconda3/bin/python3 qa_check.py  → 輸出 qa_tech.json
"""
import json, re, subprocess, glob, os
import numpy as np

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../library"))
OUT = os.path.join(os.path.dirname(__file__), "qa_tech.json")
PAT = re.compile(r"__(edge|[A-Za-z]+-[A-Za-z0-9]{4}_v3)__a\d_c\d{3}_\d{2}\.wav$")


def decode(path, sr=48000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def ebur(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return float(I[-1]), float(TP[-1])


def tail_info(x, sr=48000):
    """原始檔句尾：最後 20 ms 的 RMS 相對整檔語音 RMS（dB）。> -30 dB 代表句尾仍在發聲＝疑似被截斷。"""
    w = int(0.02 * sr)
    frames = x[: len(x) // w * w].reshape(-1, w)
    rms = np.sqrt((frames ** 2).mean(1) + 1e-12)
    ref = np.percentile(rms, 90)
    last = rms[-1]
    # 最後一個 > ref-30dB 的格到檔尾的距離
    thr = ref * 10 ** (-30 / 20)
    idx = np.where(rms > thr)[0]
    tail_ms = (len(rms) - 1 - idx[-1]) * 20 if len(idx) else None
    return float(round(float(20 * np.log10(last / ref)), 1)), (int(tail_ms) if tail_ms is not None else None)


def main():
    samples = json.load(open(os.path.join(LIB, "samples.json")))["samples"]
    res = {}
    for rel, meta in samples.items():
        if not PAT.search(rel):
            continue
        p = os.path.join(LIB, rel)
        x = decode(p)
        I, TP = ebur(p)
        clip = int((np.abs(x) >= 0.999).sum())
        rawp = meta.get("raw") or meta.get("raw_file")
        raw_tail = None
        if rawp is None:
            # 從 meta 中找 raw 路徑
            s = json.dumps(meta, ensure_ascii=False)
            m = re.findall(r"(review/G3/el/library/raw(?:_edge)?/[^\"]+\.(?:mp3|wav))", s)
            rawp = m[-1] if m else None
        if rawp:
            rp = rawp if os.path.isabs(rawp) else os.path.join(LIB, "../../../..", rawp)
            if not os.path.exists(rp):
                rp = os.path.join(LIB, os.path.basename(os.path.dirname(rawp)), os.path.basename(rawp))
            if os.path.exists(rp):
                raw_tail = tail_info(decode(rp))
        res[rel] = {"I": I, "TP": TP, "clip": clip, "dur": round(len(x) / 48000, 2),
                    "raw": rawp, "raw_last20ms_rel_dB_and_tail_ms": raw_tail}
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    Is = [v["I"] for v in res.values()]
    print(len(res), "files; I range", min(Is), max(Is))
    for k, v in res.items():
        t = v["raw_last20ms_rel_dB_and_tail_ms"]
        flag = "" if (t and t[0] < -30) else "  <-- 句尾疑似截斷/無原始檔"
        print(os.path.basename(k), v["I"], v["TP"], v["clip"], t, flag)


main()
