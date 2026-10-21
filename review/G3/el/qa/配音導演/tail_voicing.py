"""eleven_v3 與 v2 原始檔句尾檢查：最後 60 ms 的 RMS（相對 p90）與有聲比例（parselmouth 自相關）。
用法：tools/.venv/bin/python review/G3/el/qa/配音導演/tail_voicing.py → tail_voicing.json"""
import json, re, subprocess, os, sys
import numpy as np, parselmouth
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
d = json.load(open(os.path.join(ROOT, "review/G3/el/library/samples.json")))["samples"]
def dec(p):
    raw = subprocess.run(["ffmpeg","-v","error","-i",p,"-ac","1","-ar","48000","-f","f32le","-"],capture_output=True,check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)
out = {}
for k, m in d.items():
    if "edge" in m.get("cand","edge") or m.get("kind") != "line":
        continue
    raws = re.findall(r'(review/G3/el/library/raw/[^"]+\.mp3)', json.dumps(m))
    if not raws: continue
    x = dec(os.path.join(ROOT, raws[-1]))
    w = 960
    fr = x[:len(x)//w*w].reshape(-1, w); r = 20*np.log10(np.sqrt((fr**2).mean(1))+1e-9); ref = np.percentile(r, 90)
    snd = parselmouth.Sound(x, 48000)
    p = snd.to_pitch_ac(time_step=0.01, pitch_floor=60, pitch_ceiling=600)
    f = p.selected_array["frequency"]; t = p.xs()
    dur = len(x)/48000
    tailv = float(np.mean(f[t > dur-0.06] > 0)) if np.any(t > dur-0.06) else None
    out[k] = {"model": m["model"], "last60ms_rel_dB": round(float(np.mean(r[-3:]-ref)),1), "last60ms_voiced": tailv}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "tail_voicing.json"), "w"), ensure_ascii=False, indent=1)
for model in ["eleven_multilingual_v2", "eleven_v3"]:
    v = [o for o in out.values() if o["model"] == model]
    cut = [o for o in v if o["last60ms_rel_dB"] > -25]
    cutv = [o for o in v if o["last60ms_rel_dB"] > -25 and (o["last60ms_voiced"] or 0) > 0.3]
    print(model, "lines", len(v), "末 60ms > -25 dB:", len(cut), "其中仍有聲(>30%):", len(cutv))
for k, o in out.items():
    if o["model"] == "eleven_v3": print(os.path.basename(k), o["last60ms_rel_dB"], o["last60ms_voiced"])
