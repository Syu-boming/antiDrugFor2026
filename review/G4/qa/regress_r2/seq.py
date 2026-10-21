import json,subprocess,os,sys
from PIL import Image,ImageDraw
P='pack/';OUT='qa/regress_r2/'
d=json.load(open(P+'faces_playback.json'));fr=d['frames']
byk={round(f['playT']*30):f for f in fr}
kid=sys.argv[1]; play0=float(sys.argv[2]); n=int(sys.argv[3]); tag=sys.argv[4]
i0=round(play0*30)
subprocess.run(['ffmpeg','-v','error','-y','-ss',f'{(i0-2)/30:.4f}','-i',P+'g4_playback.mp4','-frames:v',str(n+4),OUT+f'{tag}_%03d.png'],check=True)
tiles=[]
for j in range(n+4):
    fn=OUT+f'{tag}_{j+1:03d}.png'
    im=Image.open(fn)
    # find frame meta: approximate via index
    k=i0-2+j; f=byk.get(k)
    eb=None
    for kk in [k,k-1,k+1]:
        if kk in byk and byk[kk]['eyes'].get(kid): eb=byk[kk]['eyes'][kid];break
    x0,y0,x1,y1=eb;cx=(x0+x1)/2;cy=(y0+y1)/2;W=max((x1-x0)*2.2,70);H=W*0.6
    c=im.crop((int(cx-W/2),int(cy-H/2),int(cx+W/2),int(cy+H/2))).resize((400,240),Image.LANCZOS)
    t=Image.new('RGB',(400,262),'white');t.paste(c,(0,22))
    st=f['faces'][kid]['eyes'] if f else '?'
    ImageDraw.Draw(t).text((3,3),f'k={k} play={k/30:.3f} {f["cueId"] if f else ""} t={f["t"] if f else ""} eyes={st}',fill='black')
    tiles.append(t)
cols=4;rows=(len(tiles)+3)//4
S=Image.new('RGB',(cols*402,rows*264),'gray')
for q,t in enumerate(tiles):S.paste(t,((q%4)*402,(q//4)*264))
S.save(OUT+f'{tag}_seq.png')
for j in range(n+4): os.remove(OUT+f'{tag}_{j+1:03d}.png')
