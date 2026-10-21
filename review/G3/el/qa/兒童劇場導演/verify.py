# 兒童劇場導演視角：重跑量測（F0、共振峰、響度、原始檔句尾能量、edge 底聲）
import json, subprocess, sys, re, os
import numpy as np, parselmouth
from parselmouth.praat import call
LIB = "/Users/boming/Documents/AI tool/反毒小劇場/review/G3/el/library"
OUT = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(f"{LIB}/samples.json"))["samples"]

def f0_form(path):
    snd = parselmouth.Sound(path)
    p = snd.to_pitch_ac(time_step=0.01, pitch_floor=70, pitch_ceiling=600)
    f = p.selected_array["frequency"]; v = f[f > 0]
    fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5, maximum_formant=5500, window_length=0.025)
    ts = p.xs()[f > 0]
    f1 = [fm.get_value_at_time(1, t) for t in ts]; f2 = [fm.get_value_at_time(2, t) for t in ts]
    f1 = np.array([x for x in f1 if x == x]); f2 = np.array([x for x in f2 if x == x])
    return dict(f0_med=round(float(np.median(v)),1), f0_p10=round(float(np.percentile(v,10)),1), f0_p90=round(float(np.percentile(v,90)),1),
                f1=round(float(np.median(f1))), f2=round(float(np.median(f2))), dur=round(snd.duration,2))

def ebur(path):
    r = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",path,"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]; TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1]
    return float(I), float(TP)

def tail_energy(raw):
    # 原始合成檔最後 30 ms 的 RMS 相對全檔 RMS 最大 50 ms 窗（dB）；> -30 dB 表示句尾可能被截斷
    snd = parselmouth.Sound(raw); x = snd.values[0]; sr = int(snd.sampling_frequency)
    w = int(0.05*sr); rms = [np.sqrt(np.mean(x[i:i+w]**2)) for i in range(0, len(x)-w, w//2)]
    mx = max(rms); t = x[-int(0.03*sr):]; tr = np.sqrt(np.mean(t**2))
    return round(20*np.log10(tr/mx+1e-12),1)

res = {}
for path, m in S.items():
    if m.get("kind") != "line": continue
    full = f"{LIB}/{path}"
    if not os.path.exists(full): continue
    d = dict(role=m["role"], cand=m["cand"], model=m["model"], line=m.get("line_id"))
    if m["cand"] == "edge":
        d["edge_voice"] = sorted({s["voice"] for s in m["edge"]["specs"]})
        d["edge_rate_pitch"] = [(s["rate"], s["pitch"]) for s in m["edge"]["specs"]]
    else:
        raws = m.get("raw") or m.get("raw_files") or m.get("segments_raw")
        cand_raw = []
        for k in ("raw","raw_path","raw_file"):
            if isinstance(m.get(k), str): cand_raw.append(m[k])
        for sg in (m.get("el") or {}).get("segments", []):
            if True:
                if isinstance(sg, dict):
                    for k in ("raw","raw_path"):
                        if isinstance(sg.get(k), str): cand_raw.append(sg[k])
        tails = []
        for r in cand_raw:
            rp = r if os.path.isabs(r) else (f"{LIB}/{r}" if os.path.exists(f"{LIB}/{r}") else f"/Users/boming/Documents/AI tool/反毒小劇場/{r}")
            if os.path.exists(rp): tails.append(tail_energy(rp))
        d["raw_tail30ms_db"] = tails
    d.update(f0_form(full)); d["I"], d["TP"] = ebur(full)
    res[path] = d
json.dump(res, open(f"{OUT}/verify_metrics.json","w"), ensure_ascii=False, indent=1)
print(len(res))
