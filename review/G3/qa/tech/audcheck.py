import sys,glob,json,numpy as np
from scipy.io import wavfile
files=sys.argv[1:]
for f in files:
    sr,x=wavfile.read(f)
    if x.dtype==np.int16: y=x.astype(np.float64)/32768
    elif x.dtype==np.int32: y=x.astype(np.float64)/2**31
    else: y=x.astype(np.float64)
    if y.ndim>1: m=np.abs(y).max(axis=1); mono=y.mean(axis=1)
    else: m=np.abs(y); mono=y
    clip=int((m>=0.9999).sum())
    pk=20*np.log10(m.max()+1e-12)
    win=int(sr*0.01)
    n=len(mono)//win
    rms=np.sqrt((mono[:n*win].reshape(n,win)**2).mean(1)+1e-20)
    db=20*np.log10(rms)
    thr=db.max()-40
    act=np.where(db>thr)[0]
    st=act[0]*0.01 if len(act) else None; en=(act[-1]+1)*0.01 if len(act) else None
    last=db[-3:].max(); first=db[:3].max()
    # dc offset, final sample abs
    print(f"{f.split('/')[-1]:40s} sr={sr} dur={len(mono)/sr:.3f} pk={pk:.2f}dBFS clip={clip} act={st}-{en} head10ms_dB={first:.1f} tail30ms_dB={last:.1f} lastsample={abs(mono[-1]):.4f} dc={mono.mean():.5f}")
