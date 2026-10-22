# 備援影片 a0、a6 的聲軌裡，三句「燈」台詞是 v05 還是 v04：
# 以 16 kHz 單聲道做正規化互相關，找各版本在聲軌中的最佳匹配值。
import numpy as np, wave, sys, subprocess, json
root, S = sys.argv[1], sys.argv[2]
def rd(f, sr=16000):
    raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar',str(sr),'-f','s16le','-'],capture_output=True).stdout
    return np.frombuffer(raw,dtype=np.int16).astype(float)/32768
def best(track, tpl):
    n=len(track)+len(tpl); N=1<<int(np.ceil(np.log2(n)))
    c=np.fft.irfft(np.fft.rfft(track,N)*np.conj(np.fft.rfft(tpl,N)),N)[:len(track)-len(tpl)]
    # 局部能量正規化
    cs=np.concatenate([[0],np.cumsum(track**2)]); L=len(tpl)
    en=np.sqrt(cs[L:L+len(c)]-cs[:len(c)])+1e-9
    r=c/(en*np.linalg.norm(tpl)); i=int(np.argmax(r)); return float(r[i]), i/16000
res={}
for a,lines in [('a0',['a0_c002_03']),('a6',['a6_c001_02','a6_c009_03'])]:
    tr=rd(f'{S}/bk_{a}.wav')
    for ln in lines:
        for v in ['v04','v05']:
            r,t=best(tr, rd(f'{root}/audio/vo/vo_{ln}_{v}.wav'))
            res[f'backup_{a}:{ln}:{v}']={'peak_ncc':round(r,3),'at_s':round(t,2)}
print(json.dumps(res,indent=1))
