# 高 F0 片段交叉檢查：三種音高演算法＋頻譜最低強峰
import sys, numpy as np, parselmouth
from parselmouth.praat import call
p, *ts = sys.argv[1:]
s=parselmouth.Sound(p)
algs={"ac":s.to_pitch_ac(time_step=0.01,pitch_floor=75,pitch_ceiling=700),
      "cc":s.to_pitch_cc(time_step=0.01,pitch_floor=75,pitch_ceiling=700),
      "shs":s.to_pitch_shs(time_step=0.01,minimum_pitch=75,maximum_frequency_component=1250,ceiling=700)}
x=s.values[0]; sr=int(s.sampling_frequency)
for t in map(float,ts):
    vals={k:(lambda z: None if z!=z else round(z))(v.get_value_at_time(t)) for k,v in algs.items()}
    i0=int((t-0.02)*sr); seg=x[i0:i0+int(0.04*sr)]*np.hanning(int(0.04*sr))
    sp=np.abs(np.fft.rfft(seg,8192)); fr=np.fft.rfftfreq(8192,1/sr)
    band=(fr>70)&(fr<1500); spb=sp[band]; frb=fr[band]
    thr=spb.max()*0.25
    peaks=[round(frb[i]) for i in range(1,len(spb)-1) if spb[i]>thr and spb[i]>=spb[i-1] and spb[i]>=spb[i+1]]
    print(p.split('/')[-1],t,vals,"spectral peaks<1500Hz(>25% max):",peaks[:8])
