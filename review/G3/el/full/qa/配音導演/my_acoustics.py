"""配音導演驗收：獨立量測（不用 vo_lib）。每檔：LUFS、真峰值、削波、F0、共振峰、MFCC、淨語速、停頓、句尾。"""
import json, subprocess, re, os, sys
import numpy as np, parselmouth
from parselmouth.praat import call
ROOT="/Users/boming/Documents/AI tool/反毒小劇場"
lines=[]
for l in open(f"{ROOT}/review/G3/el/full/transcripts.md",encoding="utf-8"):
    m=re.match(r"^## (a\d_c\d{3}_\d{2})｜([^｜]+)｜(.*)$",l.strip())
    if m: lines.append(m.groups())
def ebur(p):
    r=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",p,"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True).stderr
    I=re.findall(r"I:\s+(-?[\d.]+) LUFS",r); tp=re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS",r)
    return float(I[-1]) if I else None, float(tp[-1]) if tp else None
def nchar(t): return len(re.findall(r"[\u4e00-\u9fff0-9]",t))
out=[]
for lid,role,text in lines:
    for eng,p in [("el",f"{ROOT}/audio/vo_el/vo_{lid}_el01.wav"),("edge",f"{ROOT}/review/G3/el/full/edge/vo_{lid}_edge.wav")]:
        if not os.path.exists(p): continue
        snd=parselmouth.Sound(p); x=snd.values[0]; sr=snd.sampling_frequency
        raw=subprocess.run(["ffmpeg","-v","error","-i",p,"-f","s16le","-"],capture_output=True).stdout
        s16=np.frombuffer(raw,dtype=np.int16)
        clipped=int(np.sum(np.abs(s16.astype(int))>=32767))
        I,tp=ebur(p)
        # energy frames 10ms
        hop=int(sr*0.01); n=len(x)//hop
        fr=x[:n*hop].reshape(n,hop); rms=20*np.log10(np.sqrt((fr**2).mean(1))+1e-10)
        ref=np.percentile(rms,95)
        act=rms>ref-40  # -40 dB rel
        idx=np.where(act)[0]
        speech_s=0; pauses=[]
        if len(idx):
            a0,a1=idx[0],idx[-1]
            seg=act[a0:a1+1]
            # pauses = runs of False
            run=0; tot=len(seg)
            for v in list(seg)+[True]:
                if not v: run+=1
                else:
                    if run>=20: pauses.append(run*10)
                    run=0
            speech_s=(tot*10-sum(pauses))/1000
            head=a0*10; tail=(n-1-a1)*10
        else: head=tail=None
        # sentence-boundary pauses at -35 dB (rel to peak frame) >=150 ms
        act35=rms>ref-35; idx35=np.where(act35)[0]; p35=[]
        if len(idx35):
            seg=act35[idx35[0]:idx35[-1]+1]; run=0
            for v in list(seg)+[True]:
                if not v: run+=1
                else:
                    if run>=15: p35.append(run*10)
                    run=0
        # last voiced 60ms before tail silence
        if len(idx):
            last=x[max(0,(a1+1)*hop-int(0.06*sr)):(a1+1)*hop]
            last_db=20*np.log10(np.sqrt((last**2).mean())+1e-10)-ref
        else: last_db=None
        pitch=snd.to_pitch_ac(time_step=0.01,pitch_floor=75,pitch_ceiling=700)
        f0=pitch.selected_array['frequency']; f0=f0[f0>0]
        fm=snd.to_formant_burg(time_step=0.01,max_number_of_formants=5,maximum_formant=5500 if np.median(f0 if len(f0) else [150])<170 else 6500)
        ts=[pitch.get_time_from_frame_number(i+1) for i in range(pitch.get_number_of_frames())]
        fv=pitch.selected_array['frequency']
        F=[[],[],[]]
        for t,v in zip(ts,fv):
            if v>0:
                for k in range(3):
                    val=fm.get_value_at_time(k+1,t)
                    if val==val: F[k].append(val)
        mf=snd.to_mfcc(number_of_coefficients=12).to_array()  # (13, frames)
        e=mf[0]; keep=e>np.percentile(e,40)
        mfcc=mf[1:,keep].mean(1).tolist() if keep.sum() else None
        nc=nchar(text)
        out.append(dict(id=lid,role=role,engine=eng,lufs=I,tp=tp,clipped=clipped,dur=len(x)/sr,
            head_ms=head,tail_ms=tail,last60_db=None if last_db is None else round(float(last_db),1),
            pauses200=pauses,pauses35=p35,speech_s=round(speech_s,3),nchar=nc,rate=round(nc/speech_s,2) if speech_s else None,
            f0_med=float(np.median(f0)) if len(f0) else None,f0_p10=float(np.percentile(f0,10)) if len(f0) else None,f0_p90=float(np.percentile(f0,90)) if len(f0) else None,
            F1=float(np.median(F[0])) if F[0] else None,F2=float(np.median(F[1])) if F[1] else None,F3=float(np.median(F[2])) if F[2] else None,mfcc=mfcc))
json.dump(out,open(sys.argv[1],"w"),ensure_ascii=False,default=lambda o: o.item() if hasattr(o,"item") else str(o))
print(len(out))
