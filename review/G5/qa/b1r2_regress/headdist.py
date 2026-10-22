import json,sys,math
def segdist(p,a,b):
    (px,py),(ax,ay),(bx,by)=p,a,b
    dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
    t=0 if L==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L))
    return math.hypot(px-ax-t*dx,py-ay-t*dy)
def boxdist(a,b,box):
    x0,y0,x1,y1=box
    # check intersection by sampling
    best=1e9
    for i in range(21):
        t=i/20; x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t
        dx=max(x0-x,0,x-x1); dy=max(y0-y,0,y-y1); best=min(best,math.hypot(dx,dy))
    return best
act=sys.argv[1]
d=json.load(open(f'{act}/pack/probe_dense.json'))['probes']
res={}
for p in d:
    heads={a['id']:a.get('headBox') for a in p.get('actors',[]) if a.get('visible')}
    for s in p.get('strings',[]):
        if not s.get('visible') or 'path' not in s: continue
        hb=heads.get(s['actor']); 
        if not hb: continue
        onscreen = hb[2]>0 and hb[0]<1920 and hb[3]>0 and hb[1]<1080
        path=[q for q in s['path']]
        m=min(boxdist(path[i],path[i+1],hb) for i in range(len(path)-1))
        k=(s['anchor'],onscreen)
        if k not in res or m<res[k][0]: res[k]=(round(m,1),p['cueId'],p['t'])
for k,v in sorted(res.items()): print(act,k,v)
