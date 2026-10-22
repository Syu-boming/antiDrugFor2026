# G6 r2 抽查改壞：從九段 playback.mp4 獨立量測
# (1) 相鄰兩格全畫面平均亮度（gamma Rec.709 luma 與線性亮度）相對跳變 >20%（不論前後格是否靜止）
# (2) 16x9 與 32x18 區域明暗變化每秒次數（區域線性亮度相鄰極值差 >=0.1 且較暗端 <0.8 記一次變化）
# (3) 飽和紅（R/(R+G+B)>=0.8 的區域比例變化 >=0.25 記一次）每秒次數
import subprocess, sys, json, numpy as np
W,H=128,72
def frames(path):
    p=subprocess.Popen(['ffmpeg','-v','error','-i',path,'-vf',f'scale={W}:{H}:flags=area','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    n=W*H*3
    while True:
        b=p.stdout.read(n)
        if len(b)<n: break
        yield np.frombuffer(b,np.uint8).reshape(H,W,3)
def lin(x):
    return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
def count_changes(g):
    T,R,C=g.shape; counts=np.zeros((T,R,C),bool)
    for r in range(R):
        for c in range(C):
            s=g[:,r,c]; direction=0; lo=hi=s[0]
            for t in range(1,T):
                v=s[t]
                if v-lo>=0.1 and min(lo,v)<0.8 and direction!=1:
                    counts[t,r,c]=True; direction=1; hi=v; lo=v
                elif hi-v>=0.1 and min(hi,v)<0.8 and direction!=-1:
                    counts[t,r,c]=True; direction=-1; lo=v; hi=v
                lo=min(lo,v); hi=max(hi,v)
    return counts
def per_sec(counts,win=30):
    cs=np.concatenate([np.zeros((1,)+counts.shape[1:],int),np.cumsum(counts,axis=0)])
    T=counts.shape[0]
    if T<=win: per=cs[-1:]-cs[:1]
    else: per=cs[win:]-cs[:-win]
    mx=int(per.max()); over=int((per>3).any(axis=(1,2)).sum())
    t_at=int(np.unravel_index(per.argmax(),per.shape)[0])
    return mx,over,round(t_at/30,2)
seg=sys.argv[1]; out_path=sys.argv[2]
path=f'review/G5/{seg}/pack/{seg}_playback.mp4'
gm=[];lm=[];g16=[];g32=[];r16=[]
for f in frames(path):
    x=f.astype(np.float32)/255.0
    Y=0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]
    L=0.2126*lin(x[...,0])+0.7152*lin(x[...,1])+0.0722*lin(x[...,2])
    gm.append(float(Y.mean())); lm.append(float(L.mean()))
    g32.append(L.reshape(18,4,32,4).mean(axis=(1,3)))
    g16.append(L.reshape(9,8,16,8).mean(axis=(1,3)))
    s=x.sum(axis=2)+1e-6; red=((x[...,0]/s)>=0.8)&(x[...,0]>0.2)
    r16.append(red.reshape(9,8,16,8).mean(axis=(1,3)))
gm=np.array(gm); lm=np.array(lm)
def jumps(m,thr=0.2):
    rel=np.maximum(m[1:],m[:-1])/np.maximum(np.minimum(m[1:],m[:-1]),1e-4)-1
    idx=np.where((rel>thr)&(np.maximum(m[:-1],m[1:])>0.03))[0]
    return [(int(i+1),round((i+1)/30,3),round(float(m[i]),4),round(float(m[i+1]),4),round(float(rel[i])+1,3)) for i in idx], float(rel[np.maximum(m[:-1],m[1:])>0.03].max()+1) if len(m)>1 else 1
jg,maxg=jumps(gm); jl,maxl=jumps(lm)
c16=count_changes(np.array(g16)); c32=count_changes(np.array(g32))
R=np.array(r16); rc=np.zeros(R.shape,bool)
for t in range(1,R.shape[0]): pass
# red: count transitions of red-area fraction with hysteresis 0.25
T,a,b=R.shape
for i in range(a):
    for j in range(b):
        s=R[:,i,j]; d=0; lo=hi=s[0]
        for t in range(1,T):
            v=s[t]
            if v-lo>=0.25 and d!=1: rc[t,i,j]=True; d=1; lo=hi=v
            elif hi-v>=0.25 and d!=-1: rc[t,i,j]=True; d=-1; lo=hi=v
            lo=min(lo,v); hi=max(hi,v)
res={'seg':seg,'frames':int(len(gm)),
 'gamma_luma_one_frame_ratio_max':round(maxg,3),'gamma_jumps_gt1.2':jg,
 'linear_one_frame_ratio_max':round(maxl,3),'linear_jumps_gt1.2_count':len(jl),'linear_jumps_gt1.2_first':jl[:15],
 'luma16x9_max_per_sec_at':per_sec(c16),'luma32x18_max_per_sec_at':per_sec(c32),'red16x9_max_per_sec_at':per_sec(rc)}
json.dump(res,open(out_path,'w'),ensure_ascii=False,indent=1)
print(json.dumps(res,ensure_ascii=False))
