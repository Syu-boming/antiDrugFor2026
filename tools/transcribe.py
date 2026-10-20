"""逐檔轉寫配音（faster-whisper small），用 ffmpeg 解碼以避開 PyAV 版本問題。

用法：tools/.venv/bin/python tools/transcribe.py 音檔... ；輸出每檔一行 JSON（檔名、秒數、逐字稿）。
"""
import json
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


model = WhisperModel("small", device="cpu", compute_type="int8")
for p in sys.argv[1:]:
    audio = load(p)
    segs, _ = model.transcribe(audio, language="zh", initial_prompt="以下是繁體中文的台灣華語。")
    print(json.dumps({"file": p, "seconds": round(len(audio) / 16000, 2), "text": "".join(s.text for s in segs).strip()}, ensure_ascii=False))
