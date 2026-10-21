import json,subprocess,sys,os
from PIL import Image,ImageDraw
P='pack/'; OUT='qa/regress_r2/'
d=json.load(open(P+'faces_playback.json'));fr=d['frames']
b=json.load(open(P+'blink/blink_check.json'))['blinks']
tiles=[]
for i,bl in enumerate(b):
    kid=bl['kid']
    # find frames in this blink with closed
    cand=[f for f in fr if f['cueId']==bl['cue'] and bl['t0']-0.01<=f['t']<=bl['t1']+0.01 and f['faces'][kid]['eyes']=='closed']
    if not cand: cand=[f for f in fr if f['cueId']==bl['cue'] and bl['t0']-0.01<=f['t']<=bl['t1']+0.01]
    f=cand[len(cand)//2]
    eb=f['eyes'].get(kid)
    if not eb: print('no eyebox',i);continue
    pt=f['playT']; idx=round(pt*30)
    fn=OUT+f'mp4_{i:02d}.png'
    if not os.path.exists(fn):
        subprocess.run(['ffmpeg','-v','error','-y','-i',P+'g4_playback.mp4','-vf',f'select=eq(n\\,{idx})','-frames:v','1',fn],check=True)
    im=Image.open(fn)
    x0,y0,x1,y1=eb; w=x1-x0; cx=(x0+x1)/2; cy=(y0+y1)/2; h=max(w*0.9,40)
    W=max(w*1.8,60)
    c=im.crop((int(cx-W/2),int(cy-h/2),int(cx+W/2),int(cy+h/2))).resize((360,int(360*h/W)),Image.LANCZOS)
    t=Image.new('RGB',(360,c.height+22),'white');t.paste(c,(0,22));ImageDraw.Draw(t).text((3,3),f'{i} {kid} {bl["cue"]} t={f["t"]:.3f} play={pt:.3f} {f["faces"][kid]["eyes"]} pose?',fill='black')
    tiles.append(t)
cols=4;rows=(len(tiles)+cols-1)//cols;th=max(t.height for t in tiles)
S=Image.new('RGB',(cols*362,rows*(th+2)),'gray')
for k,t in enumerate(tiles):S.paste(t,((k%cols)*362,(k//cols)*(th+2)))
S.save(OUT+'blink_mp4_all.png');print(S.size)
