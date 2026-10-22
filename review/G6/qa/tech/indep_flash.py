# 技術 QA 自抽：從九段 playback.mp4 獨立量測（1）一格全畫面平均亮度相對跳變（>20% 不得硬切）
# （2）32×18 細格明暗變化每秒次數（簡化法：區域線性亮度相鄰極值差 ≥0.1 且較暗端 <0.8 記一次變化）。
import subprocess, sys, json, numpy as np
W,H=128,72
def frames(path):
    p=subprocess.Popen(['ffmpeg','-v','error','-i',path,'-vf',f'scale={W}:{H}:flags=area','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    n=W*H*3
    while True:
        b=p.stdout.read(n)
        if len(b)<n: break
        yield np.frombuffer(b,np.uint8).reshape(H,W,3)
def lin(img):
    x=img.astype(np.float32)/255.0
    x=np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
    return 0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]
out={}
for seg in sys.argv[1:]:
    path=f'review/G5/{seg}/pack/{seg}_playback.mp4'
    means=[];grid=[]
    for f in frames(path):
        L=lin(f); means.append(float(L.mean()))
        grid.append(L.reshape(18,4,32,4).mean(axis=(1,3)))
    m=np.array(means); g=np.array(grid)
    rel=np.abs(np.diff(m))/np.maximum(np.minimum(m[:-1],m[1:]),1e-3)
    big=[(int(i+1),round((i+1)/30,2),round(float(m[i]),3),round(float(m[i+1]),3),round(float(rel[i]),3)) for i in np.where((rel>0.2)&(np.maximum(m[:-1],m[1:])>0.03))[0]]
    # transitions per region: track extrema; count a change when swing>=0.1 and darker<0.8
    T,R,C=g.shape; counts=np.zeros((T,R,C),bool)
    for r in range(R):
        for c in range(C):
            s=g[:,r,c]; ref=s[0]; direction=0
            lo=hi=s[0]
            for t in range(1,T):
                v=s[t]
                if v-lo>=0.1 and min(lo,v)<0.8 and direction!=1:
                    counts[t,r,c]=True; direction=1; hi=v; lo=v
                elif hi-v>=0.1 and min(hi,v)<0.8 and direction!=-1:
                    counts[t,r,c]=True; direction=-1; lo=v; hi=v
                lo=min(lo,v); hi=max(hi,v)
    cs=np.cumsum(counts,axis=0)
    win=30
    per=cs[win:]-cs[:-win] if T>win else cs[-1:]
    mx=int(per.max()) if per.size else 0
    over=int((per>3).any(axis=(1,2)).sum()) if per.size else 0
    out[seg]={'frames':int(T),'mean_luma_range':[round(float(m.min()),3),round(float(m.max()),3)],'one_frame_jumps_gt20pct':big[:20],'n_jumps':len(big),'fine32x18_max_changes_per_sec_simplified':mx,'windows_over3':over}
    print(seg, json.dumps(out[seg],ensure_ascii=False))
json.dump(out,open('review/G6/qa/tech/indep_flash.json','w'),ensure_ascii=False,indent=1)
