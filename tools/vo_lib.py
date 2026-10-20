"""配音管線共用函式庫（vo_build.py、vo_g3.py、vo_design.py 共用）。

內容：讀劇本台詞、讀音替身字、合成（ElevenLabs／edge-tts，含快取）、後製（去頭尾靜音、
補 120 ms／250 ms、響度 −18 LUFS、真峰值 ≤ −1.5 dBTP、16-bit）、量測（響度、真峰值、削波、
F0、語速、停頓、句頭句尾）、對嘴 JSON（v1.2 第 15.3 節）、轉寫比對（faster-whisper＋拼音）。

金鑰：只從環境變數 ELEVENLABS_API_KEY 讀（沒有就讀專案根目錄 .env 進環境變數）；
本模組絕不印出、記錄或寫出金鑰。
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "script" / "劇本_v03.md"
VO_DIR = ROOT / "audio" / "vo"
LIP_DIR = ROOT / "audio" / "lipsync"
RAW_DIR = VO_DIR / "_raw"            # 合成原始檔快取（同參數不重複呼叫雲端，省額度）
USAGE_LOG = VO_DIR / "elevenlabs_usage.jsonl"
SR = 48000

ROLE_CODES = {
    "旁白": "narrator", "折折": "zhezhe", "小晴": "xiaoqing", "小宇": "xiaoyu", "阿樂叔叔": "ale",
    "品安": "pinan", "葉護理師": "ye", "林老師": "lin", "陳伯伯": "chen", "邀請者": "inviter",
    "執勤人員": "dispatcher",
}

HAN_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff0-9A-Za-z]")
LINE_RE = re.compile(r"^\[(a\d_c\d{3}_\d{2})\]\s*([^：]+)：(.+?)\s*$")


# ---------------------------------------------------------------- 劇本與替身字
def load_lines(path: Path = SCRIPT) -> dict[str, dict]:
    """回傳 {台詞編號: {id, cue, role, text}}，依劇本順序。"""
    out: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = LINE_RE.match(raw.strip())
        if m:
            lid, role, text = m.groups()
            out[lid] = {"id": lid, "cue": lid[:7], "role": role.strip(), "text": text.strip()}
    return out


def han_count(text: str) -> int:
    return len(HAN_RE.findall(text))


def load_pronounce(path: Path = VO_DIR / "pronounce.json") -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_pronounce(text: str, pron: dict, service: str, line_id: str | None = None) -> str:
    """字幕原文 → 合成用文字。順序：全域表 → 服務專用表 → 單句覆寫；長詞優先。"""
    table: dict[str, str] = {}
    table.update(pron.get("global", {}))
    table.update(pron.get(service, {}))
    if line_id and line_id in pron.get("lines", {}):
        table.update(pron["lines"][line_id].get(service, pron["lines"][line_id].get("global", {})))
    for k in sorted(table, key=len, reverse=True):
        text = text.replace(k, table[k])
    return text


# ---------------------------------------------------------------- 金鑰
def _ensure_env() -> None:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return
    envp = ROOT / ".env"
    if envp.exists():
        for line in envp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def el_key() -> str:
    _ensure_env()
    k = os.environ.get("ELEVENLABS_API_KEY", "")
    if not k:
        raise RuntimeError("沒有 ELEVENLABS_API_KEY 環境變數")
    return k


def el_request(method: str, path: str, body: dict | None = None, timeout: int = 120):
    """呼叫 ElevenLabs；回傳 (狀態碼, 回應位元組, 標頭 dict)。錯誤訊息不含金鑰。"""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("https://api.elevenlabs.io" + path, data=data, method=method,
                                 headers={"xi-api-key": el_key(), "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as e:
            payload = e.read()
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            return e.code, payload, {k.lower(): v for k, v in e.headers.items()}
        except urllib.error.URLError:
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    raise RuntimeError("ElevenLabs 連線失敗")


def log_usage(entry: dict) -> None:
    VO_DIR.mkdir(parents=True, exist_ok=True)
    entry = dict(entry, time=time.strftime("%Y-%m-%d %H:%M:%S"))
    with USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 合成
def _cache_path(spec: dict, text: str, ext: str) -> Path:
    key = json.dumps({"spec": {k: spec.get(k) for k in sorted(spec) if k not in ("post", "notes", "label")},
                      "text": text}, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    tag = f"_{spec.get('output_format', 'pcm_44100')}" if ext == "pcm" else ""
    return RAW_DIR / f"{spec['service']}_{h}{tag}.{ext}"


def synth_raw(spec: dict, text: str, purpose: str = "", force: bool = False) -> tuple[Path, dict]:
    """依聲線規格合成原始檔（有快取）。回傳 (原始檔路徑, 資訊)。

    spec 例：{"service": "elevenlabs", "voice_id": "...", "model": "eleven_multilingual_v2",
              "settings": {...}, "seed": 1234, "language_code": null, "output_format": "pcm_44100"}
             {"service": "edge", "voice": "zh-TW-HsiaoChenNeural", "rate": "-5%", "pitch": "+0Hz"}
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    svc = spec["service"]
    if svc == "elevenlabs":
        fmt = spec.get("output_format", "pcm_44100")
        ext = "pcm" if fmt.startswith("pcm") else "mp3"
        out = _cache_path(spec, text, ext)
        if out.exists() and not force:
            return out, {"cached": True, "chars": 0, "format": fmt}
        body = {"text": text, "model_id": spec["model"]}
        if spec.get("settings"):
            body["voice_settings"] = spec["settings"]
        if spec.get("seed") is not None:
            body["seed"] = spec["seed"]
        if spec.get("language_code"):
            body["language_code"] = spec["language_code"]
        code, payload, hdr = el_request("POST", f"/v1/text-to-speech/{spec['voice_id']}?output_format={fmt}", body)
        if code != 200 and fmt.startswith("pcm") and b"output_format" in payload:
            # 方案不支援 PCM 時退回 mp3 44.1k 128k
            spec = dict(spec, output_format="mp3_44100_128")
            return synth_raw(spec, text, purpose, force)
        if code != 200:
            try:
                detail = json.loads(payload).get("detail")
            except Exception:
                detail = payload[:300].decode(errors="replace")
            log_usage({"purpose": purpose, "voice_id": spec.get("voice_id"), "model": spec.get("model"),
                       "ok": False, "http": code, "detail": detail, "text_chars": len(text)})
            raise RuntimeError(f"ElevenLabs HTTP {code}: {detail}")
        out.write_bytes(payload)
        cost = hdr.get("character-cost") or hdr.get("x-character-count")
        info = {"cached": False, "chars": len(text), "billed": int(cost) if cost and str(cost).isdigit() else None,
                "format": fmt, "request_id": hdr.get("request-id")}
        log_usage({"purpose": purpose, "voice_id": spec.get("voice_id"), "model": spec.get("model"), "ok": True,
                   "text_chars": len(text), "billed": info["billed"], "request_id": info["request_id"],
                   "raw": out.name})
        return out, info
    if svc == "edge":
        out = _cache_path(spec, text, "mp3")
        if out.exists() and not force:
            return out, {"cached": True, "chars": 0, "format": "mp3_24000"}
        cmd = ["uvx", "--from", "edge-tts==7.3.1", "edge-tts", "--voice", spec["voice"],
               f"--rate={spec.get('rate', '+0%')}", f"--pitch={spec.get('pitch', '+0Hz')}",
               "--text", text, "--write-media", str(out)]
        for attempt in range(3):
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0 and out.exists() and out.stat().st_size > 1000:
                return out, {"cached": False, "chars": len(text), "format": "mp3_24000"}
            time.sleep(2)
        raise RuntimeError(f"edge-tts 失敗：{r.stderr[-300:]}")
    if svc == "azure":
        # Azure AI Speech（正式授權；與 edge-tts 同名聲線、同樣的 rate／pitch 語意）。金鑰：AZURE_SPEECH_KEY、AZURE_SPEECH_REGION。
        # 尚未實測（目前沒有金鑰）；有金鑰後執行 vo_build.py --service azure 即可重建。
        out = _cache_path(spec, text, "wav")
        if out.exists() and not force:
            return out, {"cached": True, "chars": 0, "format": "riff_48k"}
        _ensure_env()
        key, region = os.environ.get("AZURE_SPEECH_KEY"), os.environ.get("AZURE_SPEECH_REGION", "eastasia")
        if not key:
            raise RuntimeError("沒有 AZURE_SPEECH_KEY 環境變數")
        from xml.sax.saxutils import escape
        ssml = (f"<speak version='1.0' xml:lang='zh-TW'><voice name='{spec['voice']}'>"
                f"<prosody rate='{spec.get('rate', '+0%')}' pitch='{spec.get('pitch', '+0Hz')}'>{escape(text)}</prosody>"
                f"</voice></speak>")
        req = urllib.request.Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                                     data=ssml.encode("utf-8"), method="POST",
                                     headers={"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                                              "X-Microsoft-OutputFormat": "riff-48khz-16bit-mono-pcm",
                                              "User-Agent": "antidrug-theater-vo"})
        with urllib.request.urlopen(req, timeout=120) as r:
            out.write_bytes(r.read())
        return out, {"cached": False, "chars": len(text), "format": "riff_48k"}
    raise ValueError(f"未知服務 {svc}")


def _probe_rate(path: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return int(r.stdout.strip().split()[0])


def resample(x: np.ndarray, sr_in: int, sr_out: int = SR) -> np.ndarray:
    """多相濾波重取樣（scipy resample_poly；本機 ffmpeg 沒有 soxr）。"""
    if sr_in == sr_out:
        return x.astype(np.float32)
    from math import gcd
    from scipy.signal import resample_poly
    g = gcd(sr_in, sr_out)
    return resample_poly(x, sr_out // g, sr_in // g, window=("kaiser", 8.0)).astype(np.float32)


def decode(raw: Path) -> np.ndarray:
    """原始檔 → 48 kHz 單聲道 float32。PCM 的取樣率寫在檔名（..._pcm_44100.pcm）。"""
    if raw.suffix == ".pcm":
        m = re.search(r"_pcm_(\d+)\.pcm$", raw.name)
        rate = int(m.group(1)) if m else 44100
        args = ["-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", str(raw)]
    else:
        rate = _probe_rate(raw)
        args = ["-i", str(raw)]
    pcm = subprocess.run(["ffmpeg", "-v", "error", *args, "-ac", "1", "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return resample(np.frombuffer(pcm, dtype=np.float32).copy(), rate)


# ---------------------------------------------------------------- 訊號工具
def frame_db(x: np.ndarray, hop: int = 480, win: int = 960) -> np.ndarray:
    """10 ms 一格的 RMS（dBFS）。"""
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    n = 1 + (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    rms = np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def speech_bounds(x: np.ndarray, rel_db: float = -45.0) -> tuple[int, int]:
    """語音起訖（樣本索引）：RMS 高於最大值 rel_db 的第一格與最後一格。"""
    db = frame_db(x)
    thr = db.max() + rel_db
    on = np.nonzero(db > thr)[0]
    if len(on) == 0:
        return 0, len(x)
    start = int(on[0] * 480)
    end = int(min(len(x), on[-1] * 480 + 960))
    return start, end


def cap_pauses(x: np.ndarray, max_ms: int, rel_db: float = -40.0) -> tuple[np.ndarray, list]:
    """句中停頓上限：語音區間內低於最大值 rel_db、長於 max_ms 的靜音段，從中間剪到 max_ms（10 ms 交叉淡化）。

    只剪靜音、不變速（v1.2 第 20.4 節「不後製變速」）。edge-tts 的句號／問號停頓約 0.8–1.2 秒，對兒童角色的對話偏長。
    回傳 (新訊號, [(原毫秒, 新毫秒), ...])。
    """
    db = frame_db(x)
    thr = db.max() + rel_db
    s, e = speech_bounds(x)
    sf, ef = s // 480 + 1, e // 480 - 1
    runs, i = [], sf
    while i < ef:
        if db[i] < thr:
            j = i
            while j < ef and db[j] < thr:
                j += 1
            if (j - i) * 10 > max_ms:
                runs.append((i, j))
            i = j
        else:
            i += 1
    if not runs:
        return x, []
    out, last, log = [], 0, []
    xf = int(0.010 * SR)
    for a, b in runs:
        a_s, b_s = a * 480 + 480, b * 480     # 靜音段樣本範圍（保守內縮一格）
        keep = int(max_ms / 1000 * SR)
        cut_len = (b_s - a_s) - keep
        if cut_len <= xf:
            continue
        mid = a_s + keep // 2
        seg1 = x[last:mid].copy()
        nxt = mid + cut_len
        ramp = np.linspace(1, 0, xf, dtype=np.float32)
        seg1[-xf:] = seg1[-xf:] * ramp + x[nxt - xf:nxt] * (1 - ramp)
        out.append(seg1)
        last = nxt
        log.append((round((b - a) * 10), round((b - a) * 10 - cut_len / SR * 1000)))
    out.append(x[last:])
    return np.concatenate(out).astype(np.float32), log


def trim_pad(x: np.ndarray, head_ms: int = 120, tail_ms: int = 250) -> tuple[np.ndarray, dict]:
    """去掉合成器頭尾靜音，再補成「頭 120 ms、尾 250 ms」。

    句尾保守：語音最後一格（−45 dB 門檻）之後再保留 80 ms 自然衰減（含在 250 ms 內），只在最後 30 ms 淡出，
    不切到尾音。原始檔頭尾靜音長度另外回報，用來判斷合成器是否把句子截斷。
    """
    s, e = speech_bounds(x)
    info = {"raw_head_silence_ms": round(s / SR * 1000), "raw_tail_silence_ms": round((len(x) - e) / SR * 1000)}
    keep_tail = int(0.080 * SR)
    lead = int(0.010 * SR)
    a = max(0, s - lead)
    b = min(len(x), e + keep_tail)
    seg = x[a:b].copy()
    fi = min(len(seg), int(0.005 * SR))
    seg[:fi] *= np.linspace(0, 1, fi)
    fo = min(len(seg), int(0.030 * SR))
    seg[-fo:] *= np.linspace(1, 0, fo)
    head = np.zeros(int(head_ms / 1000 * SR) - (s - a), dtype=np.float32)
    tail = np.zeros(int(tail_ms / 1000 * SR) - (b - e), dtype=np.float32)
    y = np.concatenate([head, seg, tail]).astype(np.float32)
    info["speech_start"] = round(len(head) / SR + (s - a) / SR, 3)
    info["speech_end"] = round((len(head) + (e - a)) / SR, 3)
    return y, info


def write_wav(path: Path, x: np.ndarray, sr: int = SR, bits: int = 16) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if bits == 16:
        rng = np.random.default_rng(1234)
        d = (rng.random(len(x)) - rng.random(len(x))) / 32768.0  # TPDF 抖動
        y = np.clip(np.round((x + d) * 32767.0), -32768, 32767).astype("<i2")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
                        "-c:a", "pcm_f32le", str(path)], input=x.astype(np.float32).tobytes(), check=True)


def read_wav_native(path: Path) -> np.ndarray:
    """讀任一音檔並以 resample_poly 轉成 48 kHz。"""
    rate = _probe_rate(path)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return resample(np.frombuffer(pcm, dtype=np.float32).copy(), rate)


read_wav = read_wav_native


def ebur128(path_or_x) -> dict:
    """ffmpeg ebur128：整合響度 I（LUFS）、LRA、真峰值（dBTP）。"""
    tmp = None
    if isinstance(path_or_x, np.ndarray):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        write_wav(Path(tmp.name), path_or_x, bits=32)
        p = tmp.name
    else:
        p = str(path_or_x)
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", p, "-filter_complex", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    if tmp:
        os.unlink(tmp.name)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    def grab(pat):
        m = re.search(pat, txt)
        return float(m.group(1)) if m else None
    return {"I": grab(r"I:\s+(-?[\d.]+|-inf) LUFS"), "LRA": grab(r"LRA:\s+(-?[\d.]+) LU"),
            "TP": grab(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS")}


def loudnorm_two_pass(x: np.ndarray, target: float, tp: float) -> tuple[np.ndarray, dict]:
    """ffmpeg loudnorm 兩段式（linear=true）；回傳 48 kHz 結果與第二段報告。"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "in.wav"
        write_wav(src, x, bits=32)
        r1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                             f"loudnorm=I={target}:TP={tp}:LRA=20:print_format=json", "-f", "null", "-"],
                            capture_output=True, text=True)
        m1 = json.loads(r1.stderr[r1.stderr.rfind("{"):r1.stderr.rfind("}") + 1])
        af = (f"loudnorm=I={target}:TP={tp}:LRA=20:measured_I={m1['input_i']}:measured_TP={m1['input_tp']}:"
              f"measured_LRA={m1['input_lra']}:measured_thresh={m1['input_thresh']}:offset={m1['target_offset']}:"
              f"linear=true:print_format=json")
        dst = Path(td) / "out.wav"
        r2 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(src), "-af", af,
                             "-c:a", "pcm_f32le", str(dst)], capture_output=True, text=True)
        m2 = json.loads(r2.stderr[r2.stderr.rfind("{"):r2.stderr.rfind("}") + 1])
        y = read_wav_native(dst)
    n = min(len(y), len(x))
    y = y[:n] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))
    return y.astype(np.float32), {"method": "loudnorm_two_pass", "normalization_type": m2.get("normalization_type"),
                                  "pass1_input_i": float(m1["input_i"])}


def true_peak_limit(x: np.ndarray, ceiling_db: float) -> np.ndarray:
    """4 倍超取樣下的峰值限制（只在超過時才動作）。"""
    from scipy.signal import resample_poly
    up = resample_poly(x, 4, 1)
    lim = 10 ** (ceiling_db / 20)
    peak = np.abs(up).max()
    if peak <= lim:
        return x
    env = np.maximum(np.abs(up) / lim, 1.0)
    # 平滑的增益包絡：攻擊 1 ms、釋放 60 ms
    g = 1.0 / env
    a_rel = np.exp(-1.0 / (0.060 * SR * 4))
    out = np.empty_like(g)
    cur = 1.0
    for i, gi in enumerate(g):
        cur = gi if gi < cur else a_rel * cur + (1 - a_rel) * gi
        out[i] = cur
    # 預看：往前移 1 ms，避免峰值先過
    look = int(0.001 * SR * 4)
    out = np.minimum(out, np.concatenate([out[look:], np.ones(look)]))
    y = resample_poly(up * out, 1, 4)
    return y[:len(x)].astype(np.float32)


def master(x: np.ndarray, target: float = -18.0, tp_max: float = -1.5, head_ms: int = 120,
           tail_ms: int = 250, short_s: float = 3.0) -> tuple[np.ndarray, dict]:
    """去頭尾靜音並補齊 → 響度 → 真峰值；回傳最終 float 與處理紀錄。"""
    y, info = trim_pad(x, head_ms, tail_ms)
    dur = info["speech_end"] - info["speech_start"]
    if dur >= short_s:
        y0 = y
        y, rep = loudnorm_two_pass(y0, target, tp_max)
        if rep.get("normalization_type") != "linear":
            # loudnorm 預估真峰值會超標時會改成動態模式（會改變句頭動態）；改用第一段量測值做線性增益，真峰值交給限制器
            gain = target - rep["pass1_input_i"]
            y = (y0 * 10 ** (gain / 20)).astype(np.float32)
            rep = {"method": "loudnorm_pass1_gain", "gain_db": round(gain, 2), "pass1_input_i": rep["pass1_input_i"],
                   "note": "loudnorm 第二段轉動態模式，改用第一段量測值做線性增益＋真峰值限制"}
        info.update(rep)
    else:
        m = ebur128(y)
        gain = target - m["I"]
        y = (y * 10 ** (gain / 20)).astype(np.float32)
        info.update({"method": "measured_gain", "gain_db": round(gain, 2), "pre_I": m["I"]})
    m = ebur128(y)
    if m["TP"] is not None and m["TP"] > tp_max - 0.1:
        y = true_peak_limit(y, tp_max - 0.4)
        info["limited"] = True
        m = ebur128(y)
        # 限制後響度若掉了，小幅補回（仍守住真峰值）
        if m["I"] is not None and m["I"] < target - 0.3:
            y2 = true_peak_limit((y * 10 ** ((target - m["I"]) / 20)).astype(np.float32), tp_max - 0.4)
            m2 = ebur128(y2)
            if m2["TP"] <= tp_max:
                y, m = y2, m2
    # 收斂：量測值與目標差 > 0.2 LU 就再補一次增益（真峰值仍由限制器守住）
    for _ in range(3):
        if m["I"] is None or abs(m["I"] - target) <= 0.2:
            break
        y2 = (y * 10 ** ((target - m["I"]) / 20)).astype(np.float32)
        m2 = ebur128(y2)
        if m2["TP"] is not None and m2["TP"] > tp_max - 0.1:
            y2 = true_peak_limit(y2, tp_max - 0.4)
            m2 = ebur128(y2)
            info["limited"] = True
        y, m = y2, m2
        info["trim_passes"] = info.get("trim_passes", 0) + 1
    info["I"] = m["I"]
    info["TP"] = m["TP"]
    return y, info


# ---------------------------------------------------------------- 量測
def measure(path: Path, text: str) -> dict:
    """單檔量測：響度、真峰值、削波、長度、語音起訖、語速、停頓、F0。"""
    import parselmouth
    x = read_wav(path)
    with wave.open(str(path)) as w:
        sr, bits, ch = w.getframerate(), w.getsampwidth() * 8, w.getnchannels()
        ints = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2") if bits == 16 else None
    m = ebur128(path)
    s, e = speech_bounds(x)
    db = frame_db(x)
    # 停頓：語音區間內，低於最大值 −35 dB、長度 ≥ 150 ms 的段
    thr = db.max() - 35
    s_f, e_f = s // 480, e // 480
    pauses, run = [], 0
    for v in db[s_f:e_f]:
        if v < thr:
            run += 1
        else:
            if run >= 15:
                pauses.append(run * 10)
            run = 0
    speech_s = (e - s) / SR
    n = han_count(text)
    long_pause = sum(p for p in pauses if p >= 250) / 1000
    snd = parselmouth.Sound(str(path))
    pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
    f0 = pitch.selected_array["frequency"]
    f0 = f0[f0 > 0]
    clip = int(np.sum((ints >= 32767) | (ints <= -32768))) if ints is not None else None
    head_sil = s / SR * 1000
    tail_sil = (len(x) - e) / SR * 1000
    return {
        "file": str(path.relative_to(ROOT)), "sample_rate": sr, "bits": bits, "channels": ch,
        "seconds": round(len(x) / SR, 3), "speech_seconds": round(speech_s, 3),
        "integrated_lufs": m["I"], "true_peak_dbtp": m["TP"], "lra": m["LRA"], "clipped_samples": clip,
        "head_silence_ms": round(head_sil), "tail_silence_ms": round(tail_sil),
        "han_chars": n, "rate_cps": round(n / speech_s, 2) if speech_s else None,
        "rate_cps_net": round(n / max(0.1, speech_s - long_pause), 2) if speech_s else None,
        "pauses_ms": pauses, "pause_count_ge250": sum(1 for p in pauses if p >= 250),
        "f0_median": round(float(np.median(f0)), 1) if len(f0) else None,
        "f0_p10": round(float(np.percentile(f0, 10)), 1) if len(f0) else None,
        "f0_p90": round(float(np.percentile(f0, 90)), 1) if len(f0) else None,
        "voiced_ratio": round(len(f0) / max(1, len(pitch.selected_array["frequency"])), 2),
    }


# ---------------------------------------------------------------- 對嘴
def lipsync(x: np.ndarray, fps: int = 12, min_hold_ms: int = 90) -> dict:
    """音量包絡＋遲滯門檻＋最短停留 → 每秒 12 格。

    整數含義依 app/src/stage/perform.ts 的 mouthOpen()：0 閉、1 半開、2 大開、3 圓唇（開口 0.75）。
    做法：200–4000 Hz 帶通後取 10 ms RMS（dB，相對本檔語音 95 百分位）；
    遲滯門檻：閉→半開 > −24 dB、半開→閉 < −30 dB；半開→大開 > −9 dB、大開→半開 < −14 dB；
    每個狀態至少停留 90 ms；再以每 1/12 秒取眾數（同票取較大）量化。
    圓唇：大開格中，頻譜重心低於本檔有聲段中位數 0.72 倍者改為 3（u、o 類低 F2 母音的近似）。
    """
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [200, 4000], btype="band", fs=SR, output="sos")
    xb = sosfiltfilt(sos, x).astype(np.float32)
    db = frame_db(xb)
    voiced = db[db > db.max() - 40]
    ref = np.percentile(voiced, 95) if len(voiced) else db.max()
    rel = db - ref
    # 頻譜重心（每 10 ms）
    hop, win = 480, 960
    n = len(db)
    cent = np.zeros(n)
    w = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    band = (freqs >= 200) & (freqs <= 4000)
    xp = np.pad(xb, (0, max(0, (n - 1) * hop + win - len(xb))))
    for i in range(n):
        spec = np.abs(np.fft.rfft(xp[i * hop:i * hop + win] * w))[band]
        cent[i] = (spec * freqs[band]).sum() / (spec.sum() + 1e-9)
    min_hold = max(1, int(round(min_hold_ms / 10)))
    state, held = 0, min_hold
    states = np.zeros(n, dtype=int)
    for i, v in enumerate(rel):
        target = state
        if state == 0 and v > -24:
            target = 2 if v > -9 else 1
        elif state == 1:
            if v < -30:
                target = 0
            elif v > -9:
                target = 2
        elif state == 2:
            if v < -30:
                target = 0
            elif v < -14:
                target = 1
        if target != state and held >= min_hold:
            state, held = target, 0
        held += 1
        states[i] = state
    on = states > 0
    med_c = np.median(cent[on]) if on.any() else 0
    dur = len(x) / SR
    nf = int(np.ceil(dur * fps))
    frames = []
    for k in range(nf):
        a, b = int(k / fps * 100), int((k + 1) / fps * 100)
        seg = states[a:min(b, n)]
        if len(seg) == 0:
            frames.append(0)
            continue
        counts = np.bincount(seg, minlength=3)
        v = int(max(range(3), key=lambda s: (counts[s], s)))
        if v == 2 and med_c > 0 and np.median(cent[a:min(b, n)]) < 0.72 * med_c:
            v = 3
        frames.append(v)
    return {"fps": fps, "frames": frames}


# ---------------------------------------------------------------- 轉寫比對
_WHISPER = None
PUNCT_RE = re.compile(r"[\s，。、！？；：「」『』（）()…—\-.,!?;:\"'《》〈〉～~·]")
SANDHI_WORDS = ["一起", "不碰", "不試", "不用", "不要", "不能", "不會", "不是", "不聽", "一下", "一條", "一想", "一次",
                "不舒服", "不對", "一直", "一樣"]
CHECK_WORDS = ["紙燈節", "燈籠", "折折", "阿樂", "喪屍煙彈", "毒駕", "和", "垃圾", "竹篾", "載", "擔架", "糊", "鑰匙",
               "119", "操偶線", "喪屍", "使喚"]


ASR_MODELS = ("small", "large-v3-turbo")   # 兩個轉寫模型交叉比對：兩個都出現的差異才當成「疑似讀音問題」
_WHISPERS: dict = {}


def transcribe(paths: list[Path], model: str = "small") -> dict[str, str]:
    from faster_whisper import WhisperModel
    if model not in _WHISPERS:
        _WHISPERS[model] = WhisperModel(model, device="cpu", compute_type="int8")
    w = _WHISPERS[model]
    out = {}
    for p in paths:
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             check=True, capture_output=True).stdout
        audio = np.frombuffer(pcm, dtype=np.float32)
        segs, _ = w.transcribe(audio, language="zh", beam_size=5, initial_prompt="以下是繁體中文的台灣華語。")
        out[str(p)] = "".join(s.text for s in segs).strip()
    return out


def transcribe_compare(items: list[tuple[Path, str, str]]) -> dict[str, dict]:
    """items：(音檔, 劇本原文, 合成用文字)。兩個模型各轉寫一次並比對，回傳 {音檔: {models: {...}, verdict}}。"""
    paths = [p for p, _, _ in items]
    res = {str(p): {"models": {}} for p in paths}
    for mname in ASR_MODELS:
        tx = transcribe(paths, mname)
        for p, ref, syn in items:
            res[str(p)]["models"][mname] = compare(ref, syn, tx[str(p)])
    for p, ref, syn in items:
        ms = res[str(p)]["models"]
        sets = [{(d["ref"], d["kind"]) for d in m["diffs"] if d["kind"] != "同音字（讀音一致）"} for m in ms.values()]
        refs = [{d["ref"] for d in m["diffs"] if d["kind"] != "同音字（讀音一致）" and d["ref"]} for m in ms.values()]
        both = sorted(set.intersection(*refs)) if refs else []
        res[str(p)]["per_min"] = min(m["per"] for m in ms.values())
        res[str(p)]["cer_min"] = min(m["cer"] for m in ms.values())
        res[str(p)]["both_models_diff"] = both
        res[str(p)]["verdict"] = ("兩個模型都轉寫一致或只有同音字" if not any(sets) else
                                  ("需複查：兩個模型都在「" + "、".join(both) + "」出現非同音差異") if both else
                                  "只有單一模型出現差異（多半是轉寫誤差）")
    return res


def _to_trad(s: str) -> str:
    try:
        from opencc import OpenCC
        return OpenCC("s2tw").convert(s)
    except Exception:
        return s


def _pinyin(s: str, tone: bool = True) -> list[str]:
    from pypinyin import Style, lazy_pinyin
    s = re.sub(r"119", "一一九", s)
    return lazy_pinyin(s, style=Style.TONE3 if tone else Style.NORMAL, neutral_tone_with_five=True,
                       errors=lambda x: list(x))


DIGITS = str.maketrans("0123456789", "〇一二三四五六七八九")


def compare(ref_text: str, synth_text: str, hyp: str) -> dict:
    """劇本原文 vs 轉寫：字錯率（CER）、拼音錯率（含聲調，PER）、差異清單、讀音檢查詞。

    先逐字對齊；字相同的位置不算讀音錯（轉寫選了同一個字）。字不同的段落再比拼音：
    參考讀音取「合成用文字」（已套替身字，例如 阿勒、紙登結，代表要的讀音）；
    拼音（含聲調）相同 → 同音字，讀音一致；只差聲調 → 疑似讀錯聲調（也可能是轉寫模型的語言模型偏好，需複查）。
    """
    import difflib
    ref = PUNCT_RE.sub("", ref_text)
    ref_cmp = ref.replace("119", "一一九")
    hyp_t = PUNCT_RE.sub("", _to_trad(hyp))
    hyp_cmp = hyp_t.replace("119", "一一九").translate(DIGITS)
    ref_syn = PUNCT_RE.sub("", synth_text).replace("119", "一一九")
    if len(ref_syn) != len(ref_cmp):
        ref_syn = ref_cmp
    sm = difflib.SequenceMatcher(None, ref_cmp, hyp_cmp, autojunk=False)
    edits, pedits, diffs = 0, 0, []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        edits += max(i2 - i1, j2 - j1)
        r_seg, h_seg, syn_seg = ref_cmp[i1:i2], hyp_cmp[j1:j2], ref_syn[i1:i2]
        if r_seg and h_seg:
            pr, ph = _pinyin(syn_seg), _pinyin(h_seg)
            sm2 = difflib.SequenceMatcher(None, pr, ph, autojunk=False)
            pedits += sum(max(a2 - a1, b2 - b1) for o, a1, a2, b1, b2 in sm2.get_opcodes() if o != "equal")
            if pr == ph:
                kind = "同音字（讀音一致）"
            elif _pinyin(syn_seg, False) == _pinyin(h_seg, False):
                kind = "聲調不同（疑讀錯，或轉寫偏好）"
            else:
                kind = "字不同"
        elif r_seg:
            kind = "漏字"
            pedits += len(r_seg)
        else:
            kind = "多字"
            pedits += len(h_seg)
        diffs.append({"ref": r_seg, "hyp": h_seg, "kind": kind})
    cer = edits / max(1, len(ref_cmp))
    per = pedits / max(1, len(ref_cmp))
    ph_all = " ".join(_pinyin(hyp_cmp))
    pron = load_pronounce() if (VO_DIR / "pronounce.json").exists() else {}
    checks = []
    for w in CHECK_WORDS:
        if w in ref_text:
            if w.replace("119", "一一九") in hyp_cmp:
                st = "轉寫一致"
            else:
                syn_w = apply_pronounce(w, pron, "global") if pron else w
                st = "同音轉寫（讀音一致）" if " ".join(_pinyin(syn_w)) in ph_all else "不一致（需複查）"
            checks.append({"word": w, "status": st})
    for w in SANDHI_WORDS:
        if w in ref_text:
            checks.append({"word": w, "status": "未驗證（變調轉寫看不出）"})
    return {"ref": ref_text, "hyp": hyp, "hyp_trad": hyp_t, "cer": round(cer, 3), "per": round(per, 3),
            "diffs": diffs, "checks": checks}
