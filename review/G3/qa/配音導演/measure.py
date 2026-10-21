import json,subprocess,sys,re,numpy as np
def load(p,sr=16000):
    raw=subprocess.run(["ffmpeg","-v","error","-i",p,"-ac","1","-ar",str(sr),"-f","f32le","-"],check=True,capture_output=True).stdout
    return np.frombuffer(raw,dtype=np.float32)
def f0track(x,sr=16000,fmin=70,fmax=450,hop=160,win=640):
    out=[]
    for i in range(0,len(x)-win,hop):
        f=x[i:i+win]; 
        if np.sqrt(np.mean(f**2))<0.01: out.append(0);continue
        f=f-f.mean()
        # YIN difference
        tmax=int(sr/fmin); tmin=int(sr/fmax)
        d=np.array([np.sum((f[:win-tmax]-f[t:t+win-tmax])**2) for t in range(tmax+1)])
        cm=np.ones_like(d); cs=np.cumsum(d[1:]); cm[1:]=d[1:]*np.arange(1,len(d))/np.maximum(cs,1e-12)
        idx=np.where(cm[tmin:]<0.15)[0]
        if len(idx)==0: out.append(0);continue
        t=idx[0]+tmin
        while t+1<len(cm) and cm[t+1]<cm[t]: t+=1
        out.append(sr/t)
    return np.array(out)
def segs(x,sr=16000,hop=160,thr_db=-40):
    fr=len(x)//hop; e=np.array([20*np.log10(np.sqrt(np.mean(x[i*hop:(i+1)*hop]**2))+1e-9) for i in range(fr)])
    act=e>(e.max()+thr_db)
    idx=np.where(act)[0]; s,en=idx[0]*hop/sr,(idx[-1]+1)*hop/sr
    pauses=[];run=0
    for a in act[idx[0]:idx[-1]+1]:
        if not a: run+=1
        else:
            if run*hop/sr>=0.2: pauses.append(round(run*hop/sr*1000))
            run=0
    return s,en,pauses
tim=json.load(open(sys.argv[1]))
res={}
for k,v in tim.items():
    x=load(v["file"]); n=len(re.findall(r'[一-鿿]',v["text"]))
    s,e,p=segs(x); f=f0track(x); fv=f[f>0]
    res[k]=dict(role=v["role"],chars=n,speech_s=round(e-s,2),cps=round(n/(e-s),2),cps_net=round(n/(e-s-sum(p)/1000),2),pauses_ms=p,
      f0_med=round(float(np.median(fv)),1),f0_p10=round(float(np.percentile(fv,10)),1),f0_p90=round(float(np.percentile(fv,90)),1),
      head_ms=round(s*1000),tail_ms=round((len(x)/16000-e)*1000))
    print(k,json.dumps(res[k],ensure_ascii=False))
json.dump(res,open(sys.argv[2],"w"),ensure_ascii=False,indent=1)
