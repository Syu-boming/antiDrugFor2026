# 必要旁白與安全句的句界停頓：多個門檻重算（10 ms 框）
import sys, numpy as np, soundfile as sf
ROOT="/Users/boming/Documents/AI tool/反毒小劇場"
def pauses(p, thr_abs=None, thr_rel=None, minms=150):
    x,sr=sf.read(p); hop=int(0.01*sr)
    fr=np.array([np.sqrt(np.mean(x[i:i+hop]**2)+1e-12) for i in range(0,len(x)-hop,hop)])
    db=20*np.log10(fr)
    thr = thr_abs if thr_abs is not None else db.max()+thr_rel
    act=db>thr; idx=np.where(act)[0]; seg=act[idx[0]:idx[-1]+1]
    out=[];run=0
    for v in seg:
        if not v: run+=1
        else:
            if run*10>=minms: out.append(run*10)
            run=0
    return out
for lid in sys.argv[1:]:
    for eng,p in (("EL",f"{ROOT}/audio/vo_el/vo_{lid}_el01.wav"),("edge",f"{ROOT}/review/G3/el/full/edge/vo_{lid}_edge.wav")):
        try:
            print(lid,eng,"-35dBFS:",pauses(p,thr_abs=-35),"| -40dBFS:",pauses(p,thr_abs=-40),"| peak-40:",pauses(p,thr_rel=-40))
        except FileNotFoundError: print(lid,eng,"缺檔")
