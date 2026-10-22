import re,base64,hashlib,sys,io,wave,os,json
root=sys.argv[1]
def pcm(b):
    w=wave.open(io.BytesIO(b));return w.readframes(w.getnframes()),w.getframerate(),w.getnframes()
res={}
for dist in [root+'/app/dist/data', root+'/交付/browser/data']:
  if not os.path.isdir(dist): continue
  for cue,lines in [('a0_c002',['a0_c002_03']),('a6_c001',['a6_c001_02']),('a6_c009',['a6_c009_03'])]:
    s=open(f'{dist}/vo_{cue}.js',encoding='utf8').read()
    for ln in lines:
        m=re.search(r'"audio:vo_%s","data:audio/wav;base64,([^"]+)"'%ln,s)
        b=base64.b64decode(m.group(1)); p,sr,n=pcm(b)
        h=hashlib.md5(p).hexdigest()
        out={'pack_frames':n,'sr':sr,'pack_pcm_md5':h}
        for v in ['v04','v05']:
            f=f'{root}/audio/vo/vo_{ln}_{v}.wav'
            pp,sr2,n2=pcm(open(f,'rb').read())
            out[v]={'frames':n2,'sr':sr2,'md5':hashlib.md5(pp).hexdigest(),'match':hashlib.md5(pp).hexdigest()==h}
        res[f'{os.path.relpath(dist,root)}:{ln}']=out
print(json.dumps(res,ensure_ascii=False,indent=1))
