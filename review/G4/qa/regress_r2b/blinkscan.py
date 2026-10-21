import json,subprocess,numpy as np
from PIL import Image,ImageDraw
f=json.load(open('pack/faces_playback.json'))
fr=f['frames']
want={}
for x in fr:
    for k in ('xiaoqing','xiaoyu'):
        e=x['faces'].get(k,{}).get('eyes','open')
        if e!='open' and k in x.get('eyes',{}):
            want.setdefault(round(x['playT']*30),[]).append((k,e,x['eyes'][k],x['cueId'],x['t']))
print('nonopen frames',len(want))
print(json.dumps(fr[1000]['eyes']), fr[1000]['boxes'])
W,H=1920,1080
p=subprocess.Popen(['ffmpeg','-loglevel','error','-i','pack/g4_playback.mp4','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
crops=[];i=0
while True:
    b=p.stdout.read(W*H*3)
    if len(b)<W*H*3: break
    if i in want:
        im=np.frombuffer(b,np.uint8).reshape(H,W,3)
        for k,e,box,cid,t in want[i]:
            if isinstance(box,dict): x0,y0,x1,y1=box['x0'],box['y0'],box['x1'],box['y1']
            else: x0,y0,x1,y1=box
            pad=10
            c=Image.fromarray(im[max(0,int(y0)-pad):int(y1)+pad, max(0,int(x0)-pad):int(x1)+pad]).resize((240,120))
            crops.append((c,f'{i/30:.2f} {cid} {t:.2f} {k[:4]} {e}'))
    i+=1
print('frames read',i,'crops',len(crops))
cols=8;rows=(len(crops)+cols-1)//cols
sheet=Image.new('RGB',(cols*244,rows*140),'black');d=ImageDraw.Draw(sheet)
for n,(c,l) in enumerate(crops):
    x=(n%cols)*244;y=(n//cols)*140;sheet.paste(c,(x,y));d.text((x+2,y+122),l,fill='white')
sheet.save('qa/regress_r2b/blink_all.png');print(sheet.size)
