"""配音導演驗收：獨立重轉寫（small＋large-v3-turbo），不用 vo_lib。輸出 JSONL。"""
import json, subprocess, sys, re, os
import numpy as np
from faster_whisper import WhisperModel
ROOT = "/Users/boming/Documents/AI tool/反毒小劇場"
OUT = sys.argv[1]
lines = []
for l in open(os.path.join(ROOT, "review/G3/el/full/transcripts.md"), encoding="utf-8"):
    m = re.match(r"^## (a\d_c\d{3}_\d{2})｜([^｜]+)｜(.*)$", l.strip())
    if m: lines.append(m.groups())
def load(p):
    raw = subprocess.run(["ffmpeg","-v","error","-i",p,"-ac","1","-ar","16000","-f","f32le","-"],check=True,capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)
done=set()
if os.path.exists(OUT):
    for l in open(OUT): d=json.loads(l); done.add((d['id'],d['engine'],d['model']))
fo=open(OUT,"a")
for model_name in ["small","large-v3-turbo"]:
    mdl = WhisperModel(model_name if model_name=="small" else "mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8", cpu_threads=8)
    for lid, role, text in lines:
        for eng, path in [("el", f"{ROOT}/audio/vo_el/vo_{lid}_el01.wav"), ("edge", f"{ROOT}/review/G3/el/full/edge/vo_{lid}_edge.wav")]:
            if (lid,eng,model_name) in done or not os.path.exists(path): continue
            a = load(path)
            segs,_ = mdl.transcribe(a, language="zh", beam_size=5, initial_prompt="以下是繁體中文的台灣華語。")
            fo.write(json.dumps({"id":lid,"role":role,"ref":text,"engine":eng,"model":model_name,"hyp":"".join(s.text for s in segs).strip()},ensure_ascii=False)+"\n"); fo.flush()
