# 獨立抽查：「燈」字（逗號後第一個音節）前 0.28 秒的 F0 走勢，比較 v04 與 v05。
# 簡易自相關法，只看走勢（起點/終點/降幅），不代表聽感。
import numpy as np, wave, json, sys
root=sys.argv[1]
t=json.load(open(root+'/audio/vo/timings.json'))
def load(f):
    w=wave.open(f); sr=w.getframerate(); x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(float)
    if w.getnchannels()>1: x=x.reshape(-1,w.getnchannels()).mean(1)
    return x/32768,sr
def f0(x,sr,lo=70,hi=450):
    x=x-x.mean()
    if np.sqrt((x**2).mean())<0.01: return None
    c=np.correlate(x,x,'full')[len(x)-1:]; c/=c[0]+1e-9
    a,b=int(sr/hi),int(sr/lo); i=a+np.argmax(c[a:b])
    return sr/i if c[i]>0.45 else None
# 依 v04 的 timings 從 git 取不到，改用能量偵測找逗號後的段落起點
def segs(x,sr):
    hop=int(sr*0.01); e=np.array([np.sqrt((x[i:i+hop]**2).mean()) for i in range(0,len(x)-hop,hop)])
    on=e>0.02; out=[];s=None
    for i,v in enumerate(on):
        if v and s is None: s=i
        if not v and s is not None:
            if i-s>5: out.append((s/100,i/100))
            s=None
    if s is not None: out.append((s/100,len(on)/100))
    # 合併間隔 <0.12 秒
    m=[]
    for a,b in out:
        if m and a-m[-1][1]<0.12: m[-1]=(m[-1][0],b)
        else: m.append((a,b))
    return m
target={'a0_c002_03':-1,'a6_c001_02':-1,'a6_c009_03':-1}  # 最後一段＝「燈才會亮」
res={}
for k in target:
    for v in ['v04','v05']:
        x,sr=load(f'{root}/audio/vo/vo_{k}_{v}.wav')
        sg=segs(x,sr); a=sg[-1][0]
        tr=[]
        for i in range(0,28):
            s=int((a+i*0.01)*sr); fr=x[s:s+int(0.04*sr)]
            tr.append(f0(fr,sr))
        vals=[p for p in tr if p]
        if len(vals)>=6:
            st=np.median(vals[:4]); en=np.median(vals[-4:])
            semis=12*np.log2(en/st)
        else: st=en=semis=None
        res[f'{k}_{v}']={'segments':[(round(p,2),round(q,2)) for p,q in sg],'deng_onset_s':a,'f0_start_hz':None if st is None else round(float(st),1),'f0_end_hz':None if en is None else round(float(en),1),'change_semitones':None if semis is None else round(float(semis),2),'voiced_frames':len(vals)}
print(json.dumps(res,ensure_ascii=False,indent=1))
