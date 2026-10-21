# 句尾完整性：母帶檔中語音終點（最後一個高於峰值 -40 dB 的 10 ms 窗）前 30 ms 的最大 RMS（相對峰值 dB）
# 自然收尾逐漸衰減（低）；被截斷則終點前仍很響（高）。edge 與 v2 作對照。
import json, os, numpy as np, soundfile as sf
LIB="/Users/boming/Documents/AI tool/反毒小劇場/review/G3/el/library"
r=json.load(open("verify_metrics.json")); out={}
for p,d in r.items():
    x,sr=sf.read(f"{LIB}/{p}"); w=int(0.01*sr)
    rms=np.array([np.sqrt(np.mean(x[i:i+w]**2)) for i in range(0,len(x)-w,w)])+1e-9
    db=20*np.log10(rms/rms.max()); idx=np.where(db>-40)[0][-1]
    pre=db[max(0,idx-3):idx+1].max()
    out[p]=dict(role=d['role'],cand=d['cand'],model=d['model'],line=d['line'],pre_end30ms_db=round(float(pre),1),raw_tail30ms_db=d.get('raw_tail30ms_db'))
json.dump(out,open("tailcheck.json","w"),ensure_ascii=False,indent=1)
import collections
g=collections.defaultdict(list)
for v in out.values(): g['edge' if v['cand']=='edge' else v['model']].append(v['pre_end30ms_db'])
for k,v in g.items(): print(k,len(v),'median',np.median(v),'max',max(v),'n>-20',sum(1 for a in v if a>-20))
for p,v in sorted(out.items(), key=lambda t:-t[1]['pre_end30ms_db'])[:25]: print(v['pre_end30ms_db'],v['cand'],v['model'][-3:],v['line'])
