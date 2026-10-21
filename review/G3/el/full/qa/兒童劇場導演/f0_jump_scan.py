# 全劇掃描：響度在最大值 10 dB 內、持續 ≥50 ms、F0 > 2 倍角色中位的片段（疑似假聲尖叫）
import json, re, numpy as np, parselmouth, os
ROOT="/Users/boming/Documents/AI tool/反毒小劇場"; PKG=f"{ROOT}/review/G3/el/full"
meas=json.load(open(f"{PKG}/qa/兒童劇場導演/measure.json"))
out={}
for eng in ("el","edge"):
    for lid,r in meas["lines"][eng].items():
        role=r["role"]; med=meas["summary"][role][eng]["f0_med"]
        p=f"{ROOT}/audio/vo_el/vo_{lid}_el01.wav" if eng=="el" else f"{PKG}/edge/vo_{lid}_edge.wav"
        s=parselmouth.Sound(p); pt=s.to_pitch_ac(time_step=0.01,pitch_floor=75,pitch_ceiling=700)
        f=pt.selected_array['frequency']; t=pt.xs(); it=s.to_intensity(time_step=0.01); mx=it.values.max()
        flag=[]
        run=[]
        for i in range(len(f)):
            db=it.get_value(t[i])
            ok = f[i]>2*med and db==db and db>mx-10
            if ok: run.append(i)
            if (not ok or i==len(f)-1) and run:
                if len(run)>=5: flag.append((round(t[run[0]],2),round(t[run[-1]],2),int(f[run].max())))
                run=[]
        if flag: out.setdefault(eng,{})[lid]=dict(role=role,role_med=med,runs=flag)
json.dump(out,open(f"{PKG}/qa/兒童劇場導演/f0_jump_scan.json","w"),ensure_ascii=False,indent=1)
for eng in out:
    for lid,v in out[eng].items(): print(eng,lid,v["role"],v["role_med"],v["runs"])
