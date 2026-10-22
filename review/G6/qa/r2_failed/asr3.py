import sys, json
from faster_whisper import WhisperModel
D='/Users/boming/Documents/AI tool/反毒小劇場/review/G6/qa/r2_failed/'
out={}
for name in ['small','large-v3-turbo']:
    try: m=WhisperModel(name, device='cpu', compute_type='int8')
    except Exception as e: out[name]=str(e); continue
    for lid in ['a0_c004_01','a1_c001_05','a6_c009_01']:
        import soundfile as sf; a,_sr=sf.read(D+f'mix_{lid}.wav',dtype='float32'); segs,_=m.transcribe(a, language='zh', beam_size=5)
        out.setdefault(lid,{})[name]=''.join(s.text for s in segs)
json.dump(out,open(D+'asr3.json','w'),ensure_ascii=False,indent=1); print(json.dumps(out,ensure_ascii=False,indent=1))
