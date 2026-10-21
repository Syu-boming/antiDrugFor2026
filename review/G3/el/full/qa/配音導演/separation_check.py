import json, numpy as np, itertools, collections, math
A=json.load(open('acoustics.json'))
cue_roles=collections.defaultdict(set)
for a in A:
    for r in a['role'].split('、'): cue_roles[a['id'][:7]].add(r)
pairs=collections.defaultdict(list)
for c,rs in cue_roles.items():
    for x,y in itertools.combinations(sorted(rs),2): pairs[(x,y)].append(c)
def feats(a):
    return [12*math.log2(a['f0_med']), 12*math.log2(a['f0_p90']/a['f0_p10']), math.log(a['F1']),math.log(a['F2']),math.log(a['F3'])]+a['mfcc']
def lines(role,eng): return [a for a in A if a['role']==role and a['engine']==eng and a['f0_med'] and a['mfcc'] and a['F1']]
def loo(r1,e1,r2,e2):
    X=[feats(a) for a in lines(r1,e1)]+[feats(a) for a in lines(r2,e2)]
    y=[0]*len(lines(r1,e1))+[1]*len(lines(r2,e2))
    X=np.array(X); y=np.array(y); mu=X.mean(0); sd=X.std(0)+1e-9; Z=(X-mu)/sd
    ok=0
    for i in range(len(y)):
        m=np.ones(len(y),bool); m[i]=False
        c0=Z[m&(y==0)].mean(0); c1=Z[m&(y==1)].mean(0)
        p=0 if np.linalg.norm(Z[i]-c0)<np.linalg.norm(Z[i]-c1) else 1
        ok+=p==y[i]
    return ok/len(y)
def f0(role,eng): return np.median([a['f0_med'] for a in lines(role,eng)])
combos={'全edge':{},'全EL':None,'建議組合':{'折折':'edge','小宇':'edge'}}
out=[]
for (x,y),cs in sorted(pairs.items(),key=lambda kv:-len(kv[1])):
    if '小晴、小宇' in (x,y): continue
    row={'pair':f'{x}↔{y}','shared_cues':cs}
    for name,cmb in combos.items():
        ex = 'edge' if cmb=={} else ('el' if cmb is None else cmb.get(x,'el'))
        ey = 'edge' if cmb=={} else ('el' if cmb is None else cmb.get(y,'el'))
        if not lines(x,ex) or not lines(y,ey): continue
        st=abs(12*math.log2(f0(x,ex)/f0(y,ey)))
        row[name]={'engines':[ex,ey],'f0_st':round(st,2),'loo_acc':round(loo(x,ex,y,ey),3)}
    out.append(row)
json.dump(out,open('separation_check.json','w'),ensure_ascii=False,indent=1)
for r in out:
    print(r['pair'],len(r['shared_cues']),' | '.join(f"{k}:{v['f0_st']}st/{v['loo_acc']}" for k,v in r.items() if isinstance(v,dict)))
