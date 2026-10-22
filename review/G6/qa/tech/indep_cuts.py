# 技術 QA 自抽（第 2 步）：(1) 孤立硬切：一格內全畫面平均線性亮度相對變化 >20%，且前後一格的變化都 <該跳變的 25%（排除漸暗漸亮）；
# (2) 簡化細格計數 >3 的窗位置（cue、秒數、區域），供人工對照官方 flash_variants。
import subprocess, sys, json, os, numpy as np
W,H=128,72
def decode(path):
    p=subprocess.Popen(['ffmpeg','-v','error','-i',path,'-vf',f'scale={W}:{H}:flags=area','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    n=W*H*3; out=[]
    while True:
        b=p.stdout.read(n)
        if len(b)<n: break
        x=np.frombuffer(b,np.uint8).reshape(H,W,3).astype(np.float32)/255
        x=np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
        out.append((0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]).reshape(18,4,32,4).mean(axis=(1,3)))
    return np.array(out)
res={}
for seg in sys.argv[1:]:
    cache=f'/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad/{seg}.npy'
    g=np.load(cache) if os.path.exists(cache) else decode(f'review/G5/{seg}/pack/{seg}_playback.mp4')
    np.save(cache,g)
    m=g.mean(axis=(1,2)); d=np.diff(m)
    cuts=[]
    for i in range(1,len(d)-1):
        lo=min(m[i],m[i+1]); rel=abs(d[i])/max(lo,1e-3)
        if rel>0.2 and max(m[i],m[i+1])>0.05 and abs(d[i-1])<0.25*abs(d[i]) and abs(d[i+1])<0.25*abs(d[i]):
            cuts.append({'frame':i+1,'t':round((i+1)/30,2),'before':round(float(m[i]),3),'after':round(float(m[i+1]),3),'rel':round(float(rel),3)})
    # 細格（官方相同 32×18 區格）每格最大單格區域差
    res[seg]={'isolated_hard_cuts_gt20pct':cuts,'max_rel_isolated':max([c['rel'] for c in cuts],default=0)}
    print(seg, json.dumps(res[seg],ensure_ascii=False))
json.dump(res,open('review/G6/qa/tech/indep_cuts.json','w'),ensure_ascii=False,indent=1)
