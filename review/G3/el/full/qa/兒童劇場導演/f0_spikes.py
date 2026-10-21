# 阿樂叔叔等角色：F0 高於角色中位 2 倍的框（疑似八度誤判或尖聲）位置
import sys, numpy as np, parselmouth
ROOT="/Users/boming/Documents/AI tool/反毒小劇場"
for lid in sys.argv[1:]:
    for eng,p in (("EL",f"{ROOT}/audio/vo_el/vo_{lid}_el01.wav"),("edge",f"{ROOT}/review/G3/el/full/edge/vo_{lid}_edge.wav")):
        s=parselmouth.Sound(p); pt=s.to_pitch_ac(time_step=0.01,pitch_floor=75,pitch_ceiling=700)
        f=pt.selected_array['frequency']; t=pt.xs(); v=f>0; med=np.median(f[v])
        hi=np.where(f>2*med)[0]
        runs=[];
        for i in hi:
            if runs and i-runs[-1][1]<=2: runs[-1][1]=i
            else: runs.append([i,i])
        # 強度：高框處的相對 dB
        it=s.to_intensity(time_step=0.01)
        desc=[(round(t[a],2),round(t[b],2),int(f[a:b+1].max()),round(it.get_value(t[a]),1) if it.get_value(t[a])==it.get_value(t[a]) else None) for a,b in runs]
        print(lid,eng,"med",int(med),"voiced",int(v.sum()),"frames>2x",len(hi),"runs(t0,t1,maxHz,dB)",desc, "maxdB",round(it.values.max(),1))
