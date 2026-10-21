import subprocess,numpy as np,sys,json
V=sys.argv[1]; W,H=384,216
raw=subprocess.run(['ffmpeg','-v','error','-i',V,'-vf',f'scale={W}:{H}:flags=area','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,H,W,3).astype(np.float32)/255
n=len(fr); fps=30
lin=np.where(fr<=0.04045,fr/12.92,((fr+0.055)/1.055)**2.4)
L=0.2126*lin[...,0]+0.7152*lin[...,1]+0.0722*lin[...,2]
# red saturation per pixel: R/(R+G+B)>=0.8 -> red value; WCAG red: (R-G-B)*320 >20
redv=np.clip((lin[...,0]-lin[...,1]-lin[...,2])*320,0,None)*( (fr[...,0]/(fr.sum(-1)+1e-6))>=0.8)
def regions(A):
    gh,gw=36,64; bh,bw=H//gh,W//gw
    R=A[:, :gh*bh,:gw*bw].reshape(n,gh,bh,gw,bw).mean((2,4)).reshape(n,-1)
    return np.concatenate([R,A.reshape(n,-1).mean(1,keepdims=True)],1)
RL=regions(L); RR=regions(redv)
def count_transitions(s,thr,darkcap=None):
    # find alternating extrema with amplitude>=thr
    ev=[] # (frame, dir)
    ref=s[0]; lo=hi=s[0]; lo_i=hi_i=0; direction=0
    lastext=s[0]; trend=0; trans=[]
    for i in range(1,len(s)):
        v=s[i]
        if trend>=0:
            if v>lastext: lastext=v; ext_i=i
            if trend==0:
                if v-s0 if False else 0: pass
        # simpler: hysteresis tracker
    return trans
def trans_times(s,thr,lumi=True):
    out=[]; trend=0; mx=mn=s[0]; ext=s[0]
    for i in range(1,len(s)):
        v=s[i]
        if trend==0:
            mx=max(mx,v); mn=min(mn,v)
            if mx-v>=thr and (not lumi or min(mx,v)<0.8): out.append(i); trend=-1; ext=v
            elif v-mn>=thr and (not lumi or min(mn,v)<0.8): out.append(i); trend=1; ext=v
            continue
        if trend>0 and v>ext: ext=v
        if trend<0 and v<ext: ext=v
        if trend>0 and ext-v>=thr and (not lumi or min(ext,v)<0.8):
            out.append(i); trend=-1; ext=v
        elif trend<0 and v-ext>=thr and (not lumi or min(ext,v)<0.8):
            out.append(i); trend=1; ext=v
    return out
res={'luma':[], 'red':[]}
maxL=0;maxR=0;worst=[]
for k in range(RL.shape[1]):
    for kind,S,thr,lu in (('luma',RL[:,k],0.1,True),('red',RR[:,k],20.0,False)):
        t=trans_times(S,thr,lu)
        t=np.array(t)
        m=0;at=None
        for i,x in enumerate(t):
            c=((t>=x)&(t<x+fps)).sum()
            if c>m: m=c;at=x/fps
        flashes=m//2
        worst.append((m,kind,k,at))
worst.sort(reverse=True)
print('frames',n)
print('top transitions per 1s window (flash = 2 transitions):',worst[:12])
print('max transitions luma',max(w[0] for w in worst if w[1]=='luma'),'red',max(w[0] for w in worst if w[1]=='red'))
print('global mean L range',RL[:,-1].min(),RL[:,-1].max(),'max frame-to-frame global dL',np.abs(np.diff(RL[:,-1])).max())
print('max frame-to-frame regional dL',np.abs(np.diff(RL[:,:-1],axis=0)).max(), 'at frame', np.unravel_index(np.abs(np.diff(RL[:,:-1],axis=0)).argmax(),(n-1,2304)))
