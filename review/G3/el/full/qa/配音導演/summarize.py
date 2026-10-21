import json, numpy as np, itertools, math
A=json.load(open('acoustics.json'))
roles=['旁白','折折','小晴','小宇','阿樂叔叔','葉護理師','林老師','品安','陳伯伯','邀請者','執勤人員']
def sel(role,eng): return [a for a in A if a['role']==role and a['engine']==eng]
print('role eng n LUFSmin/max TPmax clip | rate med min max | F0 med p10 p90 | F1 F2 F3 | last60max tail_min head_min')
S={}
for r in roles:
  for e in ['el','edge']:
    L=sel(r,e)
    if not L: continue
    lu=[a['lufs'] for a in L]; tp=[a['tp'] for a in L]; cl=sum(a['clipped'] for a in L)
    rt=[a['rate'] for a in L if a['rate'] and a['nchar']>=6]
    f0=[a['f0_med'] for a in L if a['f0_med']]
    S[(r,e)]=dict(f0=np.median(f0),rate=np.median(rt),F1=np.median([a['F1'] for a in L if a['F1']]),F2=np.median([a['F2'] for a in L if a['F2']]),F3=np.median([a['F3'] for a in L if a['F3']]),mfcc=np.mean([a['mfcc'] for a in L if a['mfcc']],0),p10=np.median([a['f0_p10'] for a in L if a['f0_p10']]),p90=np.median([a['f0_p90'] for a in L if a['f0_p90']]))
    print(r,e,len(L),f"{min(lu):.1f}/{max(lu):.1f}",max(tp),cl,'|',f"{np.median(rt):.2f} {min(rt):.2f} {max(rt):.2f}",'|',f"{np.median(f0):.0f} {S[(r,e)]['p10']:.0f} {S[(r,e)]['p90']:.0f}",'|',f"{S[(r,e)]['F1']:.0f} {S[(r,e)]['F2']:.0f} {S[(r,e)]['F3']:.0f}",'|',max(a['last60_db'] for a in L),min(a['tail_ms'] for a in L),min(a['head_ms'] for a in L))
import pickle; pickle.dump(S,open('S.pkl','wb'))
