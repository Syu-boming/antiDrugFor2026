# 兒童劇場導演視角：獨立重算 F0、共振峰、淨語速（EL 對 edge 全劇基準）
# 用法：tools/.venv/bin/python measure.py  （在 repo 根目錄外也可，路徑寫死）
import json, re, os, statistics as st
import numpy as np
import parselmouth

ROOT = "/Users/boming/Documents/AI tool/反毒小劇場"
PKG = f"{ROOT}/review/G3/el/full"
OUT = f"{PKG}/qa/兒童劇場導演"

# 句子文字與角色：從 transcripts.md 標題取
lines = {}
for ln in open(f"{PKG}/transcripts.md", encoding="utf-8"):
    m = re.match(r"^## (a\d_c\d{3}_\d{2})｜([^｜]+)｜(.*)$", ln.strip())
    if m:
        lines[m.group(1)] = (m.group(2), m.group(3))

def n_syll(t):
    return len(re.findall(r"[一-鿿0-9]", t))

def analyse(path, text):
    snd = parselmouth.Sound(path)
    x = snd.values[0]; sr = snd.sampling_frequency
    pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
    f0 = pitch.selected_array["frequency"]; voiced = f0 > 0
    fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5, maximum_formant=5500)
    F = {1: [], 2: [], 3: []}
    for i, t in enumerate(pitch.xs()):
        if f0[i] <= 0:
            continue
        for k in (1, 2, 3):
            v = fm.get_value_at_time(k, t)
            if v == v:
                F[k].append(v)
    # 淨語速：20 ms 框 RMS，−40 dB（相對最大框）以上為有聲，扣掉 ≥200 ms 的無聲段
    hop = int(0.02 * sr)
    fr = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2) + 1e-12) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(fr / fr.max())
    act = db > -40
    idx = np.where(act)[0]
    if len(idx) == 0:
        return None
    a, b = idx[0], idx[-1]
    seg = act[a:b + 1]
    pause_frames = 0; run = 0; pauses = []
    for v in list(seg) + [True]:
        if not v:
            run += 1
        else:
            if run * 0.02 >= 0.2:
                pause_frames += run; pauses.append(run * 20)
            run = 0
    speech_s = (len(seg) - pause_frames) * 0.02
    ns = n_syll(text)
    return dict(
        f0_med=float(np.median(f0[voiced])) if voiced.any() else None,
        f0_p10=float(np.percentile(f0[voiced], 10)) if voiced.any() else None,
        f0_p90=float(np.percentile(f0[voiced], 90)) if voiced.any() else None,
        F1=float(np.median(F[1])) if F[1] else None,
        F2=float(np.median(F[2])) if F[2] else None,
        F3=float(np.median(F[3])) if F[3] else None,
        syll=ns, speech_s=round(speech_s, 2),
        rate_net=round(ns / speech_s, 2) if speech_s > 0 else None,
        pauses_ms=pauses,
        f0_all=f0[voiced].tolist(),
    )

res = {"el": {}, "edge": {}}
for lid, (role, text) in lines.items():
    p_el = f"{ROOT}/audio/vo_el/vo_{lid}_el01.wav"
    p_ed = f"{PKG}/edge/vo_{lid}_edge.wav"
    if os.path.exists(p_el):
        res["el"][lid] = dict(role=role, **analyse(p_el, text))
    if os.path.exists(p_ed):
        res["edge"][lid] = dict(role=role, **analyse(p_ed, text))

summary = {}
for eng in ("el", "edge"):
    byrole = {}
    for lid, r in res[eng].items():
        byrole.setdefault(r["role"], []).append(r)
    for role, rs in byrole.items():
        allf0 = [v for r in rs for v in r["f0_all"]]
        summary.setdefault(role, {})[eng] = dict(
            n=len(rs),
            f0_med=round(float(np.median(allf0)), 1) if allf0 else None,
            f0_p10=round(float(np.percentile(allf0, 10)), 1) if allf0 else None,
            f0_p90=round(float(np.percentile(allf0, 90)), 1) if allf0 else None,
            F1=round(st.median([r["F1"] for r in rs if r["F1"]]), 0),
            F2=round(st.median([r["F2"] for r in rs if r["F2"]]), 0),
            F3=round(st.median([r["F3"] for r in rs if r["F3"]]), 0),
            rate_med=round(st.median([r["rate_net"] for r in rs if r["rate_net"] and r["syll"] >= 6]), 2)
            if any(r["syll"] >= 6 for r in rs) else None,
        )

for eng in res:
    for r in res[eng].values():
        r.pop("f0_all")

def st_diff(a, b):
    return round(abs(12 * np.log2(a / b)), 2)

pairs = [("折折", "小晴"), ("阿樂叔叔", "葉護理師"), ("葉護理師", "林老師"), ("品安", "林老師"),
         ("旁白", "小宇"), ("小晴", "小宇"), ("小宇", "品安"), ("小宇", "執勤人員"), ("旁白", "折折")]
pair_out = []
for a, b in pairs:
    row = {"pair": f"{a}↔{b}"}
    for eng in ("el", "edge"):
        A = summary[a][eng]; B = summary[b][eng]
        row[eng] = dict(f0_semitones=st_diff(A["f0_med"], B["f0_med"]),
                        F2_diff_pct=round(abs(A["F2"] - B["F2"]) / min(A["F2"], B["F2"]) * 100, 1),
                        F3_diff_pct=round(abs(A["F3"] - B["F3"]) / min(A["F3"], B["F3"]) * 100, 1),
                        rate_diff=round(abs((A["rate_med"] or 0) - (B["rate_med"] or 0)), 2))
    pair_out.append(row)

json.dump(dict(summary=summary, pairs=pair_out, lines=res), open(f"{OUT}/measure.json", "w"),
          ensure_ascii=False, indent=1)
for role, d in summary.items():
    print(role, "EL", d.get("el"), "| edge", d.get("edge"))
for p in pair_out:
    print(p)
