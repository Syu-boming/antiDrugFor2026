"""EL 選角：ElevenLabs 聲線設計（小晴、小宇、品安、折折），和 edge-tts 升調基準並排量測。

用法（專案根目錄；長時間指令加 caffeinate -i）：
  tools/.venv/bin/python tools/vo_el_design.py design [--model eleven_ttv_v3] [--roles xiaoqing,xiaoyu,pinan,zhezhe] [--dry-run]
  tools/.venv/bin/python tools/vo_el_design.py previews          # 母帶處理＋量測全部預覽與 edge 基準（免費）
  tools/.venv/bin/python tools/vo_el_design.py select [--save]   # 依客觀條件篩選；--save 才真的存成正式聲線
  tools/.venv/bin/python tools/vo_el_design.py samples           # 存好的聲線 × eleven_multilingual_v2／eleven_v3 念代表句
  tools/.venv/bin/python tools/vo_el_design.py report            # 量測樣本、角色區分矩陣、讀音提案、INDEX／transcripts／listen.html

規則：
- 金鑰只經 vo_lib.el_request 讀取，不印出、不寫檔。每次呼叫都以 vo_lib.log_usage 記到 audio/vo/elevenlabs_usage.jsonl，
  purpose 一律以「EL 選角｜聲線設計」開頭；本腳本點數上限 3,000（依回應標頭 character-cost 累加，含設計預覽）。
- Starter 方案：一律 mp3_44100_128。合成快取放在本資料夾 _raw/（不寫 audio/vo/_raw），重跑不重複計費。
- 母帶處理與量測同 G3（vo_lib.master、vo_lib.measure、vo_lib.transcribe_compare：small＋large-v3-turbo）；
  另加 Praat Burg 法 LPC 共振峰（有聲段 F1／F2 中位數）。聽感與台灣口音自然度一律未驗證（Claude 聽不到聲音）。
- 只寫 review/G3/el/design/ 與本腳本；不改 casting.json、pronounce.json、正式配音檔。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402
import vo_build as B  # noqa: E402
import vo_g3_r1 as R  # noqa: E402  （只借用 islands、f0_frames、st；import 時只讀檔）

OUT = V.ROOT / "review" / "G3" / "el" / "design"
PREV = OUT / "previews"
SAMP = OUT / "samples"
TONE = OUT / "tone_checks"
STATE = OUT / "state.json"
ASR_CACHE = OUT / "asr_cache.json"
V.RAW_DIR = OUT / "_raw"            # 合成快取改放本資料夾（vo_lib 的函式在執行時讀模組全域變數）

PREFIX = "EL 選角｜聲線設計"
CAP = 3000
SEED = 20261021
FMT = "mp3_44100_128"
CAST, PRON, LINES = R.CAST, R.PRON, R.LINES
D = CAST["defaults"]
EL_MV2 = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True, "speed": 1.0}  # 同 G3
EL_V3 = {"stability": 0.5, "similarity_boost": 0.75}                                                      # 同 G3
TTS_MODELS = {"mv2": "eleven_multilingual_v2", "v3": "eleven_v3"}
TTV_SHORT = {"eleven_ttv_v3": "ttv3", "eleven_multilingual_ttv_v2": "ttv2"}
FORMANT_CEIL = 6500.0               # 主要共振峰上限（所有聲線同一設定）；5500 Hz 另列供參考
ZDJ = "紙燈節"

PINAN_DESC = ("A nine-year-old girl from Taiwan speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, soft retroflex, "
              "not a Beijing accent). Quiet, shy and gentle, a little afraid of being scolded; she speaks softly and slowly "
              "with small pauses, but every word stays clear. The lowest and softest voice among the four children: a warm, "
              "mellow child voice in the lower-middle range, not whispering, not squeaky, not baby talk, not sad or dramatic. "
              "Clean close-microphone studio recording with no background noise, no music and no reverb.")
# 描述寫兒童年齡被拒絕時的改寫（任務指定：「為兒童角色配音的年輕成人配音員，明亮、輕快、帶童聲質感的台灣華語」；描述沿用英文）
FALLBACK = {
    "xiaoqing": ("A young adult voice actor who voices children's characters, here a calm and sensible schoolgirl: bright, "
                 "light and lively, with a childlike vocal quality, speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, "
                 "soft retroflex, not a Beijing accent). Short, confident sentences at a medium pace; clear mid-high voice, "
                 "warm and friendly, not squeaky, not baby talk, not whispering, not exaggerated. Clean close-microphone "
                 "studio recording with no background noise, no music and no reverb."),
    "xiaoyu": ("A young adult voice actor who voices children's characters, here a curious and lively schoolboy: bright, light "
               "and quick, with a childlike vocal quality, speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, not a "
               "Beijing accent). Friendly, energetic tone in a clear middle range, a little lower and rounder than a girl's. "
               "Not squeaky, not cartoonish, not baby talk. Clean close-microphone studio recording with no background "
               "noise, no music and no reverb."),
    "pinan": ("A young adult voice actor who voices children's characters, here a quiet and shy schoolgirl: soft and gentle, "
              "with a childlike vocal quality, speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, soft retroflex, not a "
              "Beijing accent). The lowest and softest of the child voices: warm, mellow lower-middle range, speaking slowly "
              "and quietly with small pauses but every word clear. Not whispering, not squeaky, not baby talk, not dramatic. "
              "Clean close-microphone studio recording with no background noise, no music and no reverb."),
    "zhezhe": ("A young adult voice actor who voices children's characters, here a playful origami paper cat who hosts a "
               "children's paper puppet theater: bright, light and lively, with a childlike vocal quality, speaking natural "
               "Taiwan Mandarin (Taiwanese Guoyu accent, not a Beijing accent). Gender-neutral, the highest-pitched voice in "
               "the cast, with a slight upward lilt at the end of sentences, friendly and warm but never shrill, squeaky or "
               "babyish. Clean close-microphone studio recording with no background noise, no music and no reverb."),
}

# 實測（2026-10-21）：原描述與上面的改寫描述都回 403 blocked_generation（"this prompt potentially doesn't follow our safety
# guidelines"）；第三層改寫拿掉所有兒童字眼（child、children's、schoolgirl、childlike、nine-year-old），只描述音色。
FALLBACK2 = {
    "xiaoqing": ("A young adult woman in her early twenties from Taiwan, speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, "
                 "soft retroflex, not a Beijing accent). Bright, light, clear and high-pitched voice; calm and sensible, short "
                 "confident sentences at a medium pace, warm and friendly, not squeaky, not whispering, not exaggerated. Clean "
                 "close-microphone studio recording with no background noise, no music and no reverb."),
    "xiaoyu": ("A young adult woman in her early twenties from Taiwan, speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, "
               "not a Beijing accent). Light, clear and energetic voice in the middle range, a little lower and rounder than a "
               "typical young woman's, with a playful, boyish tone; curious, lively and quick, friendly. Not squeaky, not "
               "cartoonish. Clean close-microphone studio recording with no background noise, no music and no reverb."),
    "pinan": ("A young adult woman in her early twenties from Taiwan, speaking natural Taiwan Mandarin (Taiwanese Guoyu accent, "
              "soft retroflex, not a Beijing accent). Quiet, shy and gentle; she speaks softly and slowly with small pauses, but "
              "every word stays clear. Warm, mellow voice in the lower-middle range, soft and light, not whispering, not "
              "breathy, not sad or dramatic. Clean close-microphone studio recording with no background noise, no music and no "
              "reverb."),
    "zhezhe": ("A playful origami paper cat, the cheerful cartoon host of a paper puppet theater in Taiwan, speaking natural "
               "Taiwan Mandarin (Taiwanese Guoyu accent, not a Beijing accent). Bright, light, high-pitched and gender-neutral "
               "voice, the highest in the cast, lively with a slight upward lilt at the end of sentences, friendly and warm but "
               "never shrill or squeaky. Clean close-microphone studio recording with no background noise, no music and no "
               "reverb."),
}
DESIGN_EST_FACTOR = 3   # 設計端點沒有回 character-cost 標頭（實測）；保守以「3 個預覽 × 預覽文字字元數」估計點數

# 角色設定：F0 目標（Hz，含端點）；預覽句（≥100 字元，涵蓋該角色台詞裡出現的檢查詞）；代表句；原字對照句
ROLES = {
    "xiaoqing": {"zh": "小晴", "f0": [245.0, 275.0], "f0_note": "約 260 Hz（±1 半音＝245–275 Hz）",
                 "preview": ["a2_c002_02", "a1_c004_03", "a1_c001_01", "a1_c008_02", "a3_c003_01", "a2_c008_04",
                             "a4_c012_01", "a0_c004_02"],
                 "samples": ["a2_c002_02", "a1_c004_03", "a1_c008_02"], "orig": ["a1_c008_02"], "frame": False},
    "xiaoyu": {"zh": "小宇", "f0": [230.0, 250.0], "f0_note": "230–250 Hz",
               "preview": ["a3_c002_02", "a2_c001_01", "a0_c004_01", "a2_c013_04", "a1_c003_01", "a1_c004_04", "a4_c012_03",
                           "a1_c001_03"],
               "samples": ["a3_c002_02", "a2_c013_04", "a0_c004_01"], "orig": ["a2_c013_04", "a0_c004_01"], "frame": True},
    "pinan": {"zh": "品安", "f0": [180.0, 200.0], "f0_note": "180–200 Hz",
              "preview": ["a1_c004_06", "a6_c002_01", "a6_c002_03", "a6_c006_03", "a7_c003_01", "a6_c002_02"],
              "samples": ["a1_c004_06", "a6_c002_03", "a6_c006_03"], "orig": ["a1_c004_06"], "frame": False},
    "zhezhe": {"zh": "折折", "f0": [280.0, None], "f0_note": "≥280 Hz",
               "preview": ["a0_c003_01", "a0_c002_01", "a0_c002_02", "a2_c001_03", "a1_c005_01", "a0_c005_02"],
               "samples": ["a2_c001_03", "a0_c003_01", "a0_c002_01"], "orig": ["a0_c003_01", "a0_c002_01"], "frame": True},
}
ROLE_ORDER = ["xiaoqing", "xiaoyu", "pinan", "zhezhe"]
FRAME_ID, FRAME_TEXT = "frame_zdj", "紙燈節。"
# 讀音探測：存好的聲線若自己的代表句沒有念到某個替身字詞，就借用這幾句（原字＋替身字各一次）只做讀音提案，不算選角樣本、不進角色區分矩陣
PROBE_LINES = [FRAME_ID, "a0_c003_01", "a0_c002_01", "a1_c004_06"]
CHECKLIST_WORDS = ["紙燈節", "燈籠", "折折", "阿樂", "喪屍煙彈", "垃圾"]   # script/讀音檢查表.md（「一」「不」變調另列）

CRITERIA = {
    "per0": "轉寫：兩個轉寫模型（small、large-v3-turbo）中至少一個 PER＝0（per_min＝0；同 G3「兩個模型都出現的差異才算疑似讀音問題」）。"
            "小晴的預覽含人名「品安」，兩個模型在 G3 就把它寫成常用詞「平安」（review/G3/tone_check_pinan.json），"
            "所以 PER 另算「排除人名」版：轉寫裡的「平安」視為「品安」後重算；原始 PER 也列出。",
    "check_words": "讀音檢查詞：兩個轉寫模型對每個檢查詞（vo_lib.CHECK_WORDS，含紙燈節、燈籠、折折、阿樂）都是「轉寫一致」或「同音轉寫」，"
                   "沒有「不一致」。「一」「不」變調轉寫看不出，一律未驗證。",
    "zdj_tone": "紙燈節聲調（折折必測；含「紙燈節」的檔都量）：有聲段與起訖量法同 review/G3/tone_check_ting.json；"
                "定位：large-v3-turbo 逐字時間與原文逐字對齊找出「燈」的時間，和它重疊最多的有聲段＝燈，前一段＝紙，後一段＝節"
                "（後面緊接、間隔 <80 ms 的段一併合併）；對齊失敗才退回「最後三個有聲段」並註明（第一版只用最後三個有聲段，"
                "複查時發現 zhezhe_ttv3_p2 的「節」被嘎裂聲切成兩段而錯位，故改法）。"
                "燈＝高平：終點／起點 0.93–1.07，且平均 F0 ≥ 1.08 × 紙的平均 F0；節＝上揚：終點／起點 ≥ 1.10。三項都成立才通過。",
    "f0_target": "F0 中位數落在角色目標：小晴 245–275 Hz（約 260）、小宇 230–250 Hz、品安 180–200 Hz、折折 ≥280 Hz。",
    "formants_higher": f"共振峰：有聲段 F1 與 F2 中位數（Praat Burg 法 LPC，5 個共振峰、上限 {FORMANT_CEIL:.0f} Hz、25 ms 窗，"
                       "只取 F0>0 且強度在最大值 25 dB 內的格）都高於同一段文字的 edge 升調基準。",
    "accent": "台灣口音、自然度、像不像孩子的聽感：無法量測，一律「未驗證」。",
}
TIERS = {
    1: "全部條件成立（per0、check_words、zdj_tone〔折折〕、f0_target、formants_higher）",
    2: "除 f0_target 外全部成立（F0 不在目標內，依與目標的半音距離排序）",
    3: "check_words、zdj_tone〔折折〕、formants_higher 成立，但 PER≠0（依 PER、F0 距離排序）",
}
SELECT_RULE = ("每個角色依（級別、F0 與目標的半音距離、F1×F2 相對 edge 的幾何平均倍率由高到低）排序。第 1 輪：每個角色取排序第一、"
               "級別 1–3 的候選；第 2 輪：各角色排序第二、級別 1–2 的候選依（級別、F0 距離）排序補到合計 6 個為止；每角色最多 2 個。"
               "沒有級別的候選不存。")


# ---------------------------------------------------------------- 共用
def relroot(p) -> str:
    return str(Path(p).relative_to(V.ROOT))


def relout(p) -> str:
    return str(Path(p).relative_to(OUT))


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text("utf-8"))
    return {"designs": [], "saved": [], "problems": []}


def save_state(st: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), "utf-8")


def add_problem(st: dict, msg: str) -> None:
    if msg not in st["problems"]:
        st["problems"].append(msg)
    print("問題：", msg)


def spent() -> int:
    """本腳本（purpose 以 PREFIX 開頭）已計費點數：依標頭 character-cost；成功但沒有標頭時保守以送出字元數計。"""
    tot = 0
    if not V.USAGE_LOG.exists():
        return 0
    for line in V.USAGE_LOG.read_text("utf-8").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not str(e.get("purpose", "")).startswith(PREFIX):
            continue
        b = e.get("billed")
        if b is not None and str(b).isdigit():
            tot += int(b)
        elif e.get("ok") and e.get("endpoint") == "text-to-voice/design":
            tot += DESIGN_EST_FACTOR * int(e.get("text_chars") or 0)
        elif e.get("ok") and e.get("endpoint") != "text-to-voice":
            tot += int(e.get("text_chars") or 0)
    return tot


def usage_rows() -> list[dict]:
    rows = []
    if V.USAGE_LOG.exists():
        for line in V.USAGE_LOG.read_text("utf-8").splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if str(e.get("purpose", "")).startswith(PREFIX):
                rows.append(e)
    return rows


def err_detail(payload: bytes):
    try:
        return json.loads(payload).get("detail")
    except Exception:
        return payload[:400].decode(errors="replace")


def role_text(role: str, ids: list[str], service: str = "elevenlabs") -> tuple[str, str]:
    ref = "".join(LINES[i]["text"] for i in ids)
    syn = "".join(V.apply_pronounce(LINES[i]["text"], PRON, service, i) for i in ids)
    return ref, syn


def descriptions() -> dict:
    specs = json.loads((V.VO_DIR / "design_specs.json").read_text("utf-8"))
    out = {r: specs[r]["description"] for r in ("xiaoqing", "xiaoyu", "zhezhe")}
    out["pinan"] = PINAN_DESC
    return out


def coverage(role: str) -> dict:
    """該角色全部台詞裡出現的檢查詞，以及預覽／代表句是否念到。"""
    all_text = "".join(v["text"] for v in LINES.values() if v["role"] == ROLES[role]["zh"])
    pv = "".join(LINES[i]["text"] for i in ROLES[role]["preview"])
    sm = "".join(LINES[i]["text"] for i in ROLES[role]["samples"]) + (FRAME_TEXT if ROLES[role]["frame"] else "")
    words = [w for w in CHECKLIST_WORDS + ["竹篾", "119"] if w in all_text]
    rows = {w: {"in_preview": w in pv, "in_samples": w in sm} for w in words}
    for ch in ("一", "不"):
        if ch in all_text:
            rows[f"「{ch}」變調"] = {"in_preview": ch in pv, "in_samples": ch in sm, "note": "轉寫看不出變調，未驗證"}
    return rows


# ---------------------------------------------------------------- 音訊處理與量測
def master_to(x: np.ndarray, out: Path) -> dict:
    x, clicks = V.declick(x)
    y, minfo = V.master(x, target=D["target_lufs"], tp_max=D["true_peak_max"], head_ms=D["head_ms"], tail_ms=D["tail_ms"],
                        short_s=D.get("short_line_s", 3.0))
    V.write_wav(out, y)
    minfo["declick_raw"] = clicks
    return minfo


def formants(path: Path, ceiling: float = FORMANT_CEIL) -> dict:
    import parselmouth
    snd = parselmouth.Sound(str(path))
    pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
    fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5.0, maximum_formant=ceiling, window_length=0.025,
                             pre_emphasis_from=50.0)
    inten = snd.to_intensity(minimum_pitch=100.0, time_step=0.01)
    imax = float(np.nanmax(inten.values))
    f1s, f2s, f3s = [], [], []
    for t, f in zip(pitch.xs(), pitch.selected_array["frequency"]):
        if f <= 0:
            continue
        iv = inten.get_value(t)
        if iv != iv or iv < imax - 25:
            continue
        a, b, c = (fm.get_value_at_time(k, t) for k in (1, 2, 3))
        if a == a and b == b and 150 < a < 1500 and 500 < b < 4000:
            f1s.append(a)
            f2s.append(b)
            if c == c:
                f3s.append(c)

    def med(v):
        return round(float(np.median(v)), 1) if v else None
    return {"F1_median": med(f1s), "F2_median": med(f2s), "F3_median": med(f3s), "frames": len(f1s), "ceiling_hz": ceiling}


def measure_file(path: Path, ref: str) -> dict:
    m = V.measure(path, ref)
    m["formants"] = formants(path, FORMANT_CEIL)
    m["formants_5500"] = formants(path, 5500.0)
    return m


def f0_median_arr(x: np.ndarray) -> float | None:
    import parselmouth
    p = parselmouth.Sound(x.astype(np.float64), sampling_frequency=V.SR).to_pitch_ac(time_step=0.01, pitch_floor=75,
                                                                                       pitch_ceiling=700)
    f = p.selected_array["frequency"]
    f = f[f > 0]
    return round(float(np.median(f)), 1) if len(f) else None


def _voiced_runs(y: np.ndarray, min_ms: int = 40) -> list[dict]:
    """全檔有聲段（parselmouth 自相關 75–700 Hz、10 ms），保留每格時間與 F0。"""
    import parselmouth
    p = parselmouth.Sound(y.astype(np.float64), sampling_frequency=V.SR).to_pitch_ac(time_step=0.01, pitch_floor=75,
                                                                                       pitch_ceiling=700)
    f, ts = p.selected_array["frequency"], p.xs()
    runs, i = [], 0
    while i < len(f):
        if f[i] > 0:
            j = i
            while j + 1 < len(f) and f[j + 1] > 0:
                j += 1
            if (j - i + 1) * 10 >= min_ms:
                runs.append({"t0": float(ts[i]), "t1": float(ts[j]), "f": f[i:j + 1].copy()})
            i = j + 1
        else:
            i += 1
    return runs


def _stats(f: np.ndarray) -> dict:
    n = max(1, len(f) // 5)
    a, b = float(np.median(f[:n])), float(np.median(f[-n:]))
    return {"mean_hz": round(float(f.mean()), 1), "start_hz": round(a, 1), "end_hz": round(b, 1),
            "end_over_start": round(b / a, 3), "contour_hz_20ms": [round(float(q)) for q in f[::2]]}


def word_char_times(path: Path) -> list[tuple[str, float, float]]:
    """large-v3-turbo 逐字時間（word_timestamps；多字詞平均分配時間），字已轉繁體、去標點。"""
    import subprocess
    from faster_whisper import WhisperModel
    if "large-v3-turbo" not in V._WHISPERS:
        V._WHISPERS["large-v3-turbo"] = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32)
    segs, _ = V._WHISPERS["large-v3-turbo"].transcribe(audio, language="zh", beam_size=5, word_timestamps=True,
                                                       initial_prompt="以下是繁體中文的台灣華語。")
    out = []
    for s in segs:
        for w in s.words:
            chars = V.PUNCT_RE.sub("", V._to_trad(w.word))
            if not chars:
                continue
            step = (w.end - w.start) / len(chars)
            for k, ch in enumerate(chars):
                out.append((ch, w.start + k * step, w.start + (k + 1) * step))
    return out


def tone_zdj(path: Path, mode: str, ref: str | None = None) -> dict:
    """「紙燈節」聲調。定位：large-v3-turbo 逐字時間與原文逐字對齊，找出紙、燈、節三字的時間，再把中點落在該字時間內
    （±40 ms）的有聲段歸給該字（一字可有多段，合併計算）。對齊失敗才退回舊法（mode＝frame：全句最後三個有聲段；
    first_segment：第一個語音段落的最後三個有聲段），並註明定位方法。"""
    import difflib
    y = V.read_wav(path)
    if ref:
        try:
            chars = word_char_times(path)
            r = V.PUNCT_RE.sub("", ref)
            h = "".join(c for c, _, _ in chars)
            k = r.find(ZDJ)
            m: dict[int, int] = {}
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, r, h, autojunk=False).get_opcodes():
                if op in ("equal", "replace") and i2 > i1 and j2 > j1:
                    for q in range(i2 - i1):
                        m[i1 + q] = j1 + min(j2 - j1 - 1, int(q * (j2 - j1) / (i2 - i1)))
            if k >= 0 and all(k + q in m for q in range(3)):
                spans = [chars[m[k + q]] for q in range(3)]
                runs = _voiced_runs(y)
                assigned: dict[int, list] = {0: [], 1: [], 2: []}
                _, da, db = spans[1]
                ov = [max(0.0, min(db, r_["t1"]) - max(da, r_["t0"])) for r_ in runs]
                d = int(np.argmax(ov)) if runs and max(ov) > 0 else (
                    int(np.argmin([abs((r_["t0"] + r_["t1"]) / 2 - (da + db) / 2) for r_ in runs])) if runs else -1)
                if d >= 1 and d + 1 < len(runs):
                    assigned[0] = [runs[d - 1]]
                    assigned[1] = [runs[d]]
                    j = d + 1
                    assigned[2] = [runs[j]]
                    while j + 1 < len(runs) and runs[j + 1]["t0"] - runs[j]["t1"] < 0.08 and runs[j + 1]["t0"] < spans[2][2] + 0.15:
                        j += 1
                        assigned[2].append(runs[j])
                res = {"file": relroot(path), "mode": mode,
                       "locate_method": "large-v3-turbo 逐字時間定位「燈」＝與其時間重疊最多的有聲段；紙＝前一段；"
                                        "節＝後一段（後面緊接、間隔 <80 ms 的段一併合併，處理嘎裂聲切段）",
                       "asr_chars": [{"ref": ZDJ[q], "hyp": spans[q][0], "t0": round(spans[q][1], 3), "t1": round(spans[q][2], 3),
                                      "islands": [[round(x["t0"], 3), round(x["t1"], 3)] for x in assigned[q]]}
                                     for q in range(3)]}
                if all(assigned[q] for q in range(3)):
                    zhi, deng, jie = (_stats(np.concatenate([x["f"] for x in assigned[q]])) for q in range(3))
                    return _tone_verdict(res, zhi, deng, jie)
        except Exception as ex:  # 轉寫對齊失敗 → 舊法
            print("  逐字時間定位失敗：", ex)
    return _tone_legacy(path, y, mode)


def _tone_verdict(res: dict, zhi: dict, deng: dict, jie: dict) -> dict:
    deng_level = 0.93 <= deng["end_over_start"] <= 1.07
    deng_high = deng["mean_hz"] >= 1.08 * zhi["mean_hz"]
    jie_rise = jie["end_over_start"] >= 1.10
    res.update({"located": True, "紙": {k: zhi[k] for k in ("mean_hz", "start_hz", "end_hz", "end_over_start")},
                "燈": deng, "節": jie, "燈_over_紙_mean": round(deng["mean_hz"] / zhi["mean_hz"], 3),
                "燈_level_0.93_1.07": deng_level, "燈_high_ge1.08x紙": deng_high, "節_rise_ge1.10": jie_rise,
                "pass": bool(deng_level and deng_high and jie_rise)})
    return res


def _tone_legacy(path: Path, y: np.ndarray, mode: str) -> dict:
    """舊法（tone_check_ting 同法）：最後三個有聲段＝紙、燈、節。句中（mode＝sentence）沒有退路，標未能定位。"""
    if mode == "sentence":
        return {"file": relroot(path), "mode": mode, "located": False, "pass": False, "reason": "逐字時間對齊失敗，句中無退路"}
    if mode == "frame":
        a, b = V.speech_bounds(y)
    else:
        segs = V.speech_segments(y)
        a, b = int(segs[0][0] * V.SR), int(segs[0][1] * V.SR)
    a = max(0, a - 480)
    b = min(len(y), b + int(0.06 * V.SR))
    seg = y[a:b]
    isl = R.islands(seg, floor=75, ceil=700)
    dur = (b - a) / V.SR
    res = {"file": relroot(path), "mode": mode, "locate_method": "最後三個有聲段（逐字時間對齊失敗時的退路）",
           "segment_s": [round(a / V.SR, 3), round(b / V.SR, 3)],
           "segment_f0_median": f0_median_arr(seg), "n_islands": len(isl), "islands": isl}
    located = len(isl) >= 3 and (mode == "frame" or (dur <= 3.5 and 4 <= len(isl) <= 9))
    if not located:
        res.update({"located": False, "pass": False, "reason": f"未能定位（段長 {dur:.2f} 秒、有聲段 {len(isl)} 個）"})
        return res
    zhi, deng, jie = isl[-3], isl[-2], isl[-1]
    return _tone_verdict(res, zhi, {k: deng[k] for k in ("mean_hz", "start_hz", "end_hz", "end_over_start", "contour_hz_20ms")},
                         {k: jie[k] for k in ("mean_hz", "start_hz", "end_hz", "end_over_start", "contour_hz_20ms")})


def _asr_key(p: Path, ref: str, syn: str) -> str:
    h = hashlib.sha1(Path(p).read_bytes()).hexdigest()[:16]
    return h + "_" + hashlib.sha1((ref + "|" + syn).encode()).hexdigest()[:10]


def asr_batch(items: list[tuple[Path, str, str]]) -> dict[str, dict]:
    cache = json.loads(ASR_CACHE.read_text("utf-8")) if ASR_CACHE.exists() else {}
    keys = {str(p): _asr_key(p, r, s) for p, r, s in items}
    todo = [it for it in items if keys[str(it[0])] not in cache]
    if todo:
        print(f"轉寫 {len(todo)} 檔（small＋large-v3-turbo）…", flush=True)
        res = V.transcribe_compare(todo)
        for p, r, s in todo:
            cache[keys[str(p)]] = summarize_asr(res[str(p)], r, s)
        ASR_CACHE.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    return {str(p): cache[keys[str(p)]] for p, _, _ in items}


def summarize_asr(tc: dict, ref: str, syn: str) -> dict:
    out = {"models": {}, "verdict": tc["verdict"], "both_models_diff": tc["both_models_diff"]}
    for name, m in tc["models"].items():
        row = {"hyp": m["hyp"], "hyp_trad": m["hyp_trad"], "cer": m["cer"], "per": m["per"], "diffs": m["diffs"],
               "checks": m["checks"]}
        if "品安" in ref and "平安" in m["hyp_trad"]:
            mx = V.compare(ref, syn, m["hyp_trad"].replace("平安", "品安"))
            row["per_excl_name"] = mx["per"]
            row["cer_excl_name"] = mx["cer"]
        else:
            row["per_excl_name"] = m["per"]
            row["cer_excl_name"] = m["cer"]
        out["models"][name] = row
    ms = out["models"].values()
    out["per_min"] = min(m["per"] for m in ms)
    out["per_min_excl_name"] = min(m["per_excl_name"] for m in ms)
    out["check_words_ok_both"] = all(not c["status"].startswith("不一致") for m in ms for c in m["checks"])
    zd = [c["status"] for m in ms for c in m["checks"] if c["word"] == ZDJ]
    out["zdj_asr_ok_both"] = (all(not s.startswith("不一致") for s in zd)) if zd else None
    out["check_status"] = {}
    for name, m in out["models"].items():
        for c in m["checks"]:
            out["check_status"].setdefault(c["word"], {})[name] = c["status"]
    return out


# ---------------------------------------------------------------- 1. 聲線設計
def design_call(role: str, model: str, desc: str, text: str, tag: str) -> dict:
    body = {"voice_description": desc, "model_id": model, "text": text, "auto_generate_text": False, "loudness": 0.5,
            "guidance_scale": 5, "seed": SEED, "should_enhance": False}
    code, payload, hdr = V.el_request("POST", f"/v1/text-to-voice/design?output_format={FMT}", body, timeout=300)
    entry = {"purpose": f"{PREFIX} 預覽 {role} {model} {tag}", "endpoint": "text-to-voice/design", "model": model,
             "text_chars": len(text), "description_chars": len(desc), "ok": code == 200, "http": code,
             "billed": hdr.get("character-cost"), "request_id": hdr.get("request-id"),
             "header_names": sorted(k for k in hdr if "cost" in k or "character" in k or "request" in k)}
    res = {"role": role, "model": model, "tag": tag, "description": desc, "text": text, "http": code, "ok": code == 200,
           "billed": entry["billed"], "request_id": entry["request_id"], "previews": []}
    if code != 200:
        entry["detail"] = err_detail(payload)
        res["error"] = entry["detail"]
        V.log_usage(entry)
        print(f"  {role} {model} {tag}：HTTP {code} {json.dumps(entry['detail'], ensure_ascii=False)[:300]}")
        return res
    V.log_usage(entry)
    d = json.loads(payload)
    PREV.mkdir(parents=True, exist_ok=True)
    short = TTV_SHORT.get(model, model)
    for i, p in enumerate(d.get("previews", []), 1):
        cid = f"{role}_{short}_p{i}"
        mp3 = PREV / f"{cid}.mp3"
        mp3.write_bytes(base64.b64decode(p["audio_base_64"]))
        res["previews"].append({"cid": cid, "n": i, "generated_voice_id": p["generated_voice_id"], "mp3": relroot(mp3),
                                "duration_secs": p.get("duration_secs"), "language": p.get("language"),
                                "media_type": p.get("media_type")})
    res["returned_text"] = d.get("text")
    print(f"  {role} {model} {tag}：{len(res['previews'])} 個預覽，計費 {entry['billed']}（文字 {len(text)} 字元）")
    return res


def is_content_rejection(res: dict) -> bool:
    msg = json.dumps(res.get("error"), ensure_ascii=False).lower()
    if "blocked_generation" in msg or "safety" in msg:      # 實測：兒童年齡描述回 403 blocked_generation
        return True
    if res["http"] not in (400, 422):
        return False
    return not any(k in msg for k in ("tier", "plan", "subscription", "output_format", "quota", "credit", "payment",
                                      "voice_limit", "too short", "too long", "at least", "characters"))


def cmd_design(args) -> None:
    st = load_state()
    descs = descriptions()
    roles = args.roles.split(",") if args.roles else ROLE_ORDER
    for role in roles:
        _, syn = role_text(role, ROLES[role]["preview"])
        if len(syn) < 100:
            raise SystemExit(f"{role} 預覽文字 {len(syn)} 字元，少於 100")
        done = [d for d in st["designs"] if d["role"] == role and d["model"] == args.model and d["ok"]]
        if done and not args.force:
            print(f"  {role} {args.model}：已有預覽（{len(done[0]['previews'])} 個），沿用")
            continue
        if args.dry_run:
            print(f"  {role} {args.model}：文字 {len(syn)} 字元：{syn}")
            continue
        est = DESIGN_EST_FACTOR * len(syn)
        if spent() + est > CAP:
            add_problem(st, f"點數上限：{role} {args.model} 設計預估 {est} 點，已用 {spent()}，超過 {CAP}，停止")
            break
        res = None
        for tag, desc in (("原描述", descs[role]), ("改寫描述（年輕成人配音員）", FALLBACK[role]),
                          ("改寫描述2（無兒童字眼）", FALLBACK2[role])):
            prev = [d for d in st["designs"] if d["role"] == role and d["model"] == args.model and d["tag"] == tag]
            if prev and is_content_rejection(prev[-1]) and not args.force:
                res = prev[-1]
                print(f"  {role} {args.model} {tag}：先前已被拒（HTTP {res['http']}），改下一層描述")
                continue
            res = design_call(role, args.model, desc, syn, tag)
            st["designs"].append(res)
            save_state(st)
            if res["ok"] or not is_content_rejection(res):
                break
            print(f"  {role}：{tag} 被拒（{res['http']}），改下一層描述重試")
        if not res["ok"]:
            add_problem(st, f"{role} {args.model} 設計失敗：HTTP {res['http']} {json.dumps(res.get('error'), ensure_ascii=False)[:300]}")
            if res["http"] in (401, 402, 403) and not is_content_rejection(res):
                save_state(st)
                break
        save_state(st)
    print(f"本腳本已用點數：{spent()} / {CAP}")


# ---------------------------------------------------------------- 2. 預覽量測
def edge_render(role: str, lid: str, text: str, out: Path) -> dict:
    ln = {"id": lid, "cue": lid[:7], "role": ROLES[role]["zh"], "text": text}
    x, notes = B.render_line(ln, CAST, PRON, None, False, f"{PREFIX} edge 基準")
    minfo = master_to(x, out)
    sp = notes["specs"][0]
    return {"spec": {k: sp.get(k) for k in ("service", "voice", "rate", "pitch", "post")}, "synth_text": sp["synth_text"],
            "master": minfo}


def cmd_previews(args) -> None:
    st = load_state()
    metrics = load_metrics()
    items, recs = [], {}
    # edge 基準：同一段預覽文字，照 casting.json 目前參數（含 post）
    for role in ROLE_ORDER:
        if not any(d["role"] == role and d["ok"] for d in st["designs"]):
            continue
        ref, _ = role_text(role, ROLES[role]["preview"])
        out = PREV / f"edge_{role}_preview.wav"
        info = edge_render(role, f"pv_{role}", ref, out)
        rec = {"kind": "edge_preview", "role": role, "file": relroot(out), "ref": ref, "synth_text": info["synth_text"],
               "edge_spec": info["spec"], "master": info["master"]}
        recs[f"edge_{role}"] = rec
        items.append((out, ref, info["synth_text"]))
    for d in st["designs"]:
        if not d["ok"]:
            continue
        ref, syn = role_text(d["role"], ROLES[d["role"]]["preview"])
        for p in d["previews"]:
            wav = PREV / f"{p['cid']}.wav"
            minfo = master_to(V.decode(V.ROOT / p["mp3"]), wav)
            recs[p["cid"]] = {"kind": "el_preview", "role": d["role"], "ttv_model": d["model"], "desc_tag": d["tag"],
                              "generated_voice_id": p["generated_voice_id"], "file": relroot(wav), "mp3": p["mp3"],
                              "ref": ref, "synth_text": syn, "master": minfo, "duration_secs": p.get("duration_secs")}
            items.append((wav, ref, syn))
    asr = asr_batch(items)
    for key, rec in recs.items():
        p = V.ROOT / rec["file"]
        rec["measure"] = measure_file(p, rec["ref"])
        rec["asr"] = asr[str(p)]
        if rec["role"] == "zhezhe":
            rec["tone_zdj"] = tone_zdj(p, "first_segment", rec["ref"])
            TONE.mkdir(parents=True, exist_ok=True)
            (TONE / f"{key}_preview.json").write_text(json.dumps(tone_doc(rec["tone_zdj"], "預覽第一句「明天就是紙登結。」"),
                                                                 ensure_ascii=False, indent=1), "utf-8")
        m = rec["measure"]
        print(f"  {key:22s} F0 {m['f0_median']}  F1/F2 {m['formants']['F1_median']}/{m['formants']['F2_median']}  "
              f"PER min {rec['asr']['per_min_excl_name']}  檢查詞 {rec['asr']['check_words_ok_both']}"
              + (f"  紙燈節聲調 {rec['tone_zdj']['pass']}" if 'tone_zdj' in rec else ""), flush=True)
    metrics["previews"] = recs
    save_metrics(metrics)
    print("預覽量測完成")


def tone_doc(t: dict, what: str) -> dict:
    return {"_說明": "「紙燈節」聲調檢查。" + CRITERIA["zdj_tone"] + f" 對象：{what}。"
                     "有聲段＝parselmouth 自相關音高（75–700 Hz、10 ms）連續 ≥40 ms 的有聲格；起點／終點＝前後 20% 中位數。"
                     "聽感未驗證。", **t}


def load_metrics() -> dict:
    p = OUT / "metrics.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else {}


def save_metrics(m: dict) -> None:
    m["_說明"] = ("EL 選角（聲線設計）全部量測。每筆：measure＝vo_lib.measure（響度 I、真峰值、削波、頭尾靜音、毛語速 rate_cps、"
                 "淨語速 rate_cps_net〔扣 ≥250 ms 停頓〕與 rate_cps_net_r〔驗收者算法：−40 dB、≥200 ms〕、句中停頓 pauses_ms、"
                 "F0 中位數與 p10／p90）＋ formants（Praat Burg LPC，上限 6500 Hz；formants_5500 為 5500 Hz 參考）；"
                 "asr＝small 與 large-v3-turbo 轉寫比對（CER、PER〔含聲調拼音〕、差異、檢查詞）；tone_zdj＝紙燈節聲調。"
                 "聽感與台灣口音一律未驗證。")
    (OUT / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), "utf-8")


# ---------------------------------------------------------------- 3. 篩選與儲存
def st_dist(f0: float, lo: float, hi: float | None) -> float:
    if f0 is None:
        return 99.0
    if f0 < lo:
        return round(12 * math.log2(lo / f0), 2)
    if hi is not None and f0 > hi:
        return round(12 * math.log2(f0 / hi), 2)
    return 0.0


def evaluate(metrics: dict) -> dict:
    recs = metrics.get("previews", {})
    out = {}
    for cid, rec in recs.items():
        if rec["kind"] != "el_preview":
            continue
        role = rec["role"]
        edge = recs.get(f"edge_{role}")
        m, a = rec["measure"], rec["asr"]
        lo, hi = ROLES[role]["f0"]
        fe = edge["measure"]["formants"] if edge else {}
        f1, f2 = m["formants"]["F1_median"], m["formants"]["F2_median"]
        f1r = round(f1 / fe["F1_median"], 3) if fe.get("F1_median") and f1 else None
        f2r = round(f2 / fe["F2_median"], 3) if fe.get("F2_median") and f2 else None
        c = {"per0": a["per_min_excl_name"] == 0,
             "check_words": bool(a["check_words_ok_both"]),
             "zdj_tone": (bool(rec["tone_zdj"]["pass"]) and a.get("zdj_asr_ok_both") is not False) if role == "zhezhe" else None,
             "f0_target": st_dist(m["f0_median"], lo, hi) == 0.0,
             "formants_higher": bool(f1r and f2r and f1r > 1.0 and f2r > 1.0)}
        hard = [c["check_words"], c["formants_higher"]] + ([c["zdj_tone"]] if c["zdj_tone"] is not None else [])
        tier = None
        if all(hard) and c["per0"] and c["f0_target"]:
            tier = 1
        elif all(hard) and c["per0"]:
            tier = 2
        elif all(hard):
            tier = 3
        out[cid] = {"cid": cid, "role": role, "role_zh": ROLES[role]["zh"], "ttv_model": rec["ttv_model"],
                    "desc_tag": rec["desc_tag"], "generated_voice_id": rec["generated_voice_id"], "file": rec["file"],
                    "f0_median": m["f0_median"], "f0_p10": m["f0_p10"], "f0_p90": m["f0_p90"],
                    "f0_target": ROLES[role]["f0_note"], "f0_dist_semitones": st_dist(m["f0_median"], lo, hi),
                    "F1": f1, "F2": f2, "F1_edge": fe.get("F1_median"), "F2_edge": fe.get("F2_median"),
                    "F1_ratio_vs_edge": f1r, "F2_ratio_vs_edge": f2r,
                    "formant_geo_ratio": round(math.sqrt(f1r * f2r), 3) if f1r and f2r else None,
                    "per_small": a["models"]["small"]["per"], "per_turbo": a["models"]["large-v3-turbo"]["per"],
                    "per_min": a["per_min"], "per_min_excl_name": a["per_min_excl_name"],
                    "cer_small": a["models"]["small"]["cer"], "cer_turbo": a["models"]["large-v3-turbo"]["cer"],
                    "check_status": a["check_status"], "criteria": c, "tier": tier, "accent": "未驗證"}
    return out


def choose(ev: dict) -> list[str]:
    by_role: dict[str, list] = {}
    for cid, e in ev.items():
        if e["tier"] is None:
            continue
        by_role.setdefault(e["role"], []).append(e)
    for r in by_role:
        by_role[r].sort(key=lambda e: (e["tier"], e["f0_dist_semitones"], -(e["formant_geo_ratio"] or 0)))
    picks = [by_role[r][0]["cid"] for r in ROLE_ORDER if r in by_role]
    second = [by_role[r][1] for r in ROLE_ORDER if r in by_role and len(by_role[r]) > 1 and by_role[r][1]["tier"] <= 2]
    second.sort(key=lambda e: (e["tier"], e["f0_dist_semitones"]))
    for e in second:
        if len(picks) >= 6:
            break
        picks.append(e["cid"])
    return picks[:6]


def save_voice(st: dict, e: dict, desc: str) -> dict:
    prev = [s for s in st["saved"] if s["generated_voice_id"] == e["generated_voice_id"] and s.get("voice_id")]
    if prev:
        return prev[0]
    name = f"AD-{e['cid']}"
    body = {"voice_name": name, "voice_description": desc[:1000], "generated_voice_id": e["generated_voice_id"],
            "labels": {"project": "antidrug-theater", "role": e["role"]}}
    code, payload, hdr = V.el_request("POST", "/v1/text-to-voice", body)
    tried = ["text-to-voice"]
    if code in (400, 422) and b"label" in payload.lower():
        body.pop("labels")
        code, payload, hdr = V.el_request("POST", "/v1/text-to-voice", body)
        tried.append("text-to-voice（不帶 labels）")
    if code in (404, 405):
        code, payload, hdr = V.el_request("POST", "/v1/text-to-voice/create-voice-from-preview", body)
        tried.append("text-to-voice/create-voice-from-preview")
    d = {}
    try:
        d = json.loads(payload)
    except Exception:
        pass
    rec = {"cid": e["cid"], "role": e["role"], "generated_voice_id": e["generated_voice_id"], "voice_name": name,
           "http": code, "voice_id": d.get("voice_id") if code == 200 else None, "endpoints_tried": tried,
           "detail": None if code == 200 else err_detail(payload), "tier": e["tier"]}
    V.log_usage({"purpose": f"{PREFIX} 儲存聲線 {e['cid']}", "endpoint": "text-to-voice", "ok": code == 200, "http": code,
                 "text_chars": 0, "billed": hdr.get("character-cost"), "request_id": hdr.get("request-id"),
                 "detail": rec["detail"], "voice_name": name})
    st["saved"].append(rec)
    save_state(st)
    print(f"  儲存 {e['cid']}：HTTP {code} voice_id={rec['voice_id']} {json.dumps(rec['detail'], ensure_ascii=False)[:200] if rec['detail'] else ''}")
    return rec


def cmd_select(args) -> None:
    st = load_state()
    metrics = load_metrics()
    ev = evaluate(metrics)
    picks = choose(ev)
    for cid, e in ev.items():
        e["selected"] = cid in picks
    print("篩選結果：")
    for cid in sorted(ev, key=lambda k: (ROLE_ORDER.index(ev[k]["role"]), k)):
        e = ev[cid]
        print(f"  {cid:20s} 級別 {e['tier']}  F0 {e['f0_median']}（距目標 {e['f0_dist_semitones']} 半音）  F1/F2 倍率 "
              f"{e['F1_ratio_vs_edge']}/{e['F2_ratio_vs_edge']}  PER {e['per_small']}/{e['per_turbo']}（排除人名 min "
              f"{e['per_min_excl_name']}）  {e['criteria']}  {'選' if e['selected'] else ''}")
    missing = [r for r in ROLE_ORDER if not any(ev[c]["role"] == r for c in picks)]
    if missing:
        print("沒有可存候選的角色：", missing)
    if args.save:
        descs = {(d["role"], d["model"], d["tag"]): d["description"] for d in st["designs"] if d["ok"]}
        for cid in picks:
            e = ev[cid]
            rec = save_voice(st, e, descs[(e["role"], e["ttv_model"], e["desc_tag"])])
            if not rec.get("voice_id"):
                add_problem(st, f"儲存 {cid} 失敗：HTTP {rec['http']} {json.dumps(rec['detail'], ensure_ascii=False)[:300]}")
        save_state(st)
    metrics["selection"] = {"criteria": CRITERIA, "tiers": TIERS, "rule": SELECT_RULE, "picks": picks,
                            "roles_without_pick": missing, "evaluation": ev}
    save_metrics(metrics)


# ---------------------------------------------------------------- 4. 代表句
def el_spec(voice_id: str, name: str, mshort: str) -> dict:
    model = TTS_MODELS[mshort]
    s = {"service": "elevenlabs", "voice_id": voice_id, "voice_name": name, "model": model,
         "settings": dict(EL_V3 if mshort == "v3" else EL_MV2), "seed": SEED, "output_format": FMT}
    if mshort == "v3":
        s["language_code"] = "zh"
    return s


def sample_jobs(st: dict) -> list[dict]:
    jobs = []
    for sv in st["saved"]:
        if not sv.get("voice_id"):
            continue
        role = sv["role"]
        cfg = ROLES[role]
        lines = [(lid, LINES[lid]["text"], "sub") for lid in cfg["samples"]]
        lines += [(lid, LINES[lid]["text"], "orig") for lid in cfg["orig"]]
        if cfg["frame"]:
            lines += [(FRAME_ID, FRAME_TEXT, "sub"), (FRAME_ID, FRAME_TEXT, "orig")]
        own = {lid for lid, _, _ in lines}
        probes = [(lid, FRAME_TEXT if lid == FRAME_ID else LINES[lid]["text"], var) for lid in PROBE_LINES if lid not in own
                  for var in ("sub", "orig")]
        for mshort in TTS_MODELS:
            for lid, text, var in lines + probes:
                syn = V.apply_pronounce(text, PRON, "elevenlabs", lid if lid in LINES else None) if var == "sub" else text
                if var == "orig" and syn == V.apply_pronounce(text, PRON, "elevenlabs", lid if lid in LINES else None):
                    continue
                probe = lid not in own
                key = f"{sv['cid']}__{mshort}__{'probe_' if probe else ''}{lid}" + ("__orig" if var == "orig" else "")
                jobs.append({"key": key, "probe": probe, "cid": sv["cid"], "role": role, "voice_id": sv["voice_id"], "voice_name": sv["voice_name"],
                             "mshort": mshort, "line": lid, "ref": text, "synth_text": syn, "variant": var})
    return jobs


def cmd_samples(args) -> None:
    st = load_state()
    jobs = sample_jobs(st)
    SAMP.mkdir(parents=True, exist_ok=True)
    est_new = 0
    for j in jobs:
        spec = el_spec(j["voice_id"], j["voice_name"], j["mshort"])
        if not V._cache_path(spec, j["synth_text"], "mp3").exists():
            est_new += len(j["synth_text"])
    print(f"代表句 {len(jobs)} 檔，預估新計費 {est_new} 點；已用 {spent()} / {CAP}")
    done = []
    for j in jobs:
        spec = el_spec(j["voice_id"], j["voice_name"], j["mshort"])
        cached = V._cache_path(spec, j["synth_text"], "mp3").exists()
        if not cached and spent() + len(j["synth_text"]) > CAP:
            add_problem(st, f"點數上限：{j['key']} 未合成（已用 {spent()}，上限 {CAP}）")
            break
        try:
            raw, info = V.synth_raw(spec, j["synth_text"], purpose=f"{PREFIX} 代表句 {j['key']}")
        except RuntimeError as ex:
            add_problem(st, f"{j['key']} 合成失敗：{ex}")
            if "401" in str(ex) or "quota" in str(ex):
                break
            continue
        wav = SAMP / f"{j['key']}.wav"
        j["master"] = master_to(V.decode(raw), wav)
        j["file"] = relroot(wav)
        j["billed"] = info.get("billed")
        done.append(j)
    # edge 基準：同一批代表句（含短框句），照 casting.json 目前參數
    for role in ROLE_ORDER:   # 四個角色都做 edge 基準（角色區分矩陣與混搭需要；edge 免費）
        ids = ROLES[role]["samples"] + ([FRAME_ID] if ROLES[role]["frame"] else [])
        for lid in ids:
            text = LINES[lid]["text"] if lid in LINES else FRAME_TEXT
            out = SAMP / f"edge_{role}__{lid}.wav"
            info = edge_render(role, lid, text, out)
            done.append({"key": f"edge_{role}__{lid}", "cid": f"edge_{role}", "role": role, "mshort": "edge", "line": lid,
                         "ref": text, "synth_text": info["synth_text"], "variant": "sub", "file": relroot(out),
                         "edge_spec": info["spec"], "master": info["master"]})
    st["sample_jobs"] = done
    save_state(st)
    print(f"代表句完成 {len(done)} 檔；本腳本已用點數 {spent()} / {CAP}")


# ---------------------------------------------------------------- 5. 量測、矩陣、提案、報告
def measure_samples(st: dict, metrics: dict) -> dict:
    jobs = st.get("sample_jobs", [])
    items = [(V.ROOT / j["file"], j["ref"], V.strip_breaks(j["synth_text"])) for j in jobs]
    asr = asr_batch(items) if items else {}
    out = {}
    for j in jobs:
        p = V.ROOT / j["file"]
        rec = {k: j[k] for k in ("cid", "role", "mshort", "line", "ref", "synth_text", "variant", "file", "master")}
        rec["probe"] = bool(j.get("probe"))
        if "edge_spec" in j:
            rec["edge_spec"] = j["edge_spec"]
        rec["model"] = TTS_MODELS.get(j["mshort"], "edge-tts")
        rec["measure"] = measure_file(p, j["ref"])
        rec["asr"] = asr[str(p)]
        if ZDJ in j["ref"]:
            mode = "frame" if j["line"] == FRAME_ID else ("first_segment" if j["line"] == "a0_c003_01" else "sentence")
            if mode:
                rec["tone_zdj"] = tone_zdj(p, mode, j["ref"])
                TONE.mkdir(parents=True, exist_ok=True)
                (TONE / f"{j['key']}.json").write_text(json.dumps(tone_doc(rec["tone_zdj"], f"{j['key']}（{j['synth_text']}）"),
                                                                  ensure_ascii=False, indent=1), "utf-8")
        out[j["key"]] = rec
    return out


def option_f0(samples: dict) -> dict:
    """每個角色選項（edge 或 設計聲線@模型）：代表句（替身字版，不含短框句與原字對照）有聲格合併 F0 中位數。"""
    opts: dict[str, dict] = {}
    for key, r in samples.items():
        if r["variant"] != "sub" or r["line"] == FRAME_ID or r.get("probe"):
            continue
        opt = r["cid"] if r["mshort"] == "edge" else f"{r['cid']}@{r['mshort']}"
        o = opts.setdefault(opt, {"role": r["role"], "files": [], "frames": []})
        o["files"].append(r["file"])
        o["frames"].append(R.f0_frames(V.ROOT / r["file"]))
    res = {}
    for opt, o in opts.items():
        allf = np.concatenate(o["frames"]) if o["frames"] else np.array([])
        base = None
        if opt.startswith("edge_"):
            base = CAST["roles"][ROLES[o["role"]]["zh"]]["spec"]["voice"]
        res[opt] = {"role": o["role"], "role_zh": ROLES[o["role"]]["zh"], "n_files": len(o["files"]), "files": o["files"],
                    "f0_median_pooled": round(float(np.median(allf)), 1) if len(allf) else None,
                    "base_voice": base or opt.split("@")[0], "service": "edge" if opt.startswith("edge_") else "elevenlabs"}
    return res


def preview_options(metrics: dict) -> dict:
    """參考用：預覽文字（各角色文字不同）的 F0 中位數；未存檔的候選也列入。"""
    res = {}
    for k, r in metrics.get("previews", {}).items():
        base = CAST["roles"][ROLES[r["role"]]["zh"]]["spec"]["voice"] if r["kind"] == "edge_preview" else k
        res[k] = {"role": r["role"], "role_zh": ROLES[r["role"]]["zh"], "n_files": 1, "files": [r["file"]],
                  "f0_median_pooled": r["measure"]["f0_median"], "base_voice": base,
                  "service": "edge" if r["kind"] == "edge_preview" else "elevenlabs"}
    return res


def separation(opts: dict) -> dict:
    roles = [r for r in ROLE_ORDER if any(o["role"] == r for o in opts.values())]
    choices = {r: [k for k, o in opts.items() if o["role"] == r and o["f0_median_pooled"]] for r in roles}

    def pair(a, b):
        fa, fb = opts[a]["f0_median_pooled"], opts[b]["f0_median_pooled"]
        same = opts[a]["base_voice"] == opts[b]["base_voice"]
        stv = abs(R.st(fa, fb))
        pct = round(abs(fa - fb) / min(fa, fb) * 100, 1)
        return {"a": a, "b": b, "f0": [fa, fb], "semitones": stv, "diff_pct": pct, "same_base_voice": same,
                "pass": stv >= 3 and (pct >= 10 if same else True)}
    full = []
    keys = [k for r in roles for k in choices[r]]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if opts[a]["role"] != opts[b]["role"]:
                full.append(pair(a, b))
    combos = []
    for combo in itertools.product(*[choices[r] for r in roles]):
        prs = [pair(a, b) for a, b in itertools.combinations(combo, 2)]
        combos.append({"combo": dict(zip([ROLES[r]["zh"] for r in roles], combo)),
                       "n_design": sum(1 for c in combo if not c.startswith("edge_")),
                       "min_semitones": min(p["semitones"] for p in prs) if prs else None,
                       "failing_pairs": [f"{p['a']}↔{p['b']}（{p['semitones']}）" for p in prs if not p["pass"]],
                       "all_pass": all(p["pass"] for p in prs)})
    combos.sort(key=lambda c: (not c["all_pass"], -(c["min_semitones"] or 0)))
    named = {}
    edge_all = {r: f"edge_{r}" for r in roles}
    for r in roles:
        for k in choices[r]:
            if k.startswith("edge_"):
                continue
            combo = dict(edge_all, **{r: k})
            prs = [pair(a, b) for a, b in itertools.combinations([combo[x] for x in roles], 2)]
            named[f"只有{ROLES[r]['zh']}用 {k}，其他 edge"] = {
                "combo": {ROLES[x]["zh"]: combo[x] for x in roles},
                "pairs": [{"pair": f"{p['a']}↔{p['b']}", "semitones": p["semitones"], "pass": p["pass"]} for p in prs],
                "all_pass": all(p["pass"] for p in prs)}
    return {"_說明": "角色區分：四個角色（小晴、小宇、品安、折折）的每個選項（edge 目前參數，或設計聲線@eleven_multilingual_v2／eleven_v3）"
                     "取代表句（替身字版 3 句，不含短框句與原字對照）全部有聲格合併的 F0 中位數；兩兩差 ≥3 半音（12·log2 比值）才通過，"
                     "同一個底聲（edge 同一個 Neural 聲線）另須差 ≥10%。matrix_pairs 列出所有跨角色選項兩兩比較；combos 列出所有組合"
                     "（依是否全部通過、最小半音差排序，非推薦）；named_mixes 是「只換一個角色、其他維持 edge」的混搭。聽感未驗證。",
            "options": opts, "matrix_pairs": full, "named_mixes": named,
            "combos_total": len(combos), "combos_all_pass": sum(1 for c in combos if c["all_pass"]), "combos": combos}


def pronounce_proposal(samples: dict) -> dict:
    words = {"紙燈節": "紙登結", "折折": "哲哲", "阿樂": "阿勒", "燈籠": "登籠"}
    res = {"_說明": "ElevenLabs 讀音提案（不改 audio/vo/pronounce.json）。同一聲線、同一模型、同一句，原字與替身字各合成一次："
                    "兩個轉寫模型對該詞都是「轉寫一致」或「同音轉寫」才算通過；「紙燈節」另須聲調檢查通過（可定位時）。"
                    "規則：某模型下原字在所有測過的聲線與句子都通過 → 提案該模型 elevenlabs 表把該詞對應回原字（取消全域替身字）；"
                    "否則若替身字全部通過 → 維持全域替身字；兩者都有未通過 → 列出，不提案。聽感未驗證。",
           "evidence": {}, "proposal": {}}
    for w, sub in words.items():
        ev = []
        for key, r in samples.items():
            if r["mshort"] == "edge" or w not in r["ref"]:
                continue
            st_ = r["asr"]["check_status"].get(w, {})
            ok_asr = bool(st_) and all(not s.startswith("不一致") for s in st_.values())
            tone = r.get("tone_zdj") if w == ZDJ else None
            ok = ok_asr and (tone["pass"] if tone else True)
            ev.append({"key": key, "voice": r["cid"], "model": r["model"], "line": r["line"], "variant": r["variant"],
                       "sent_text": r["synth_text"], "asr_status": st_, "tone_pass": tone["pass"] if tone else None, "pass": ok})
        res["evidence"][w] = ev
        prop = {}
        for mshort, model in TTS_MODELS.items():
            o = [e for e in ev if e["model"] == model and e["variant"] == "orig"]
            s = [e for e in ev if e["model"] == model and e["variant"] == "sub"]
            pairs = {(e["voice"], e["line"]) for e in o}
            s = [e for e in s if (e["voice"], e["line"]) in pairs]
            if not o:
                prop[model] = {"decision": "沒有原字對照資料", "orig_pass": None, "sub_pass": None}
            elif all(e["pass"] for e in o):
                prop[model] = {"decision": "原字", "elevenlabs_entry": {w: w}, "orig_pass": f"{len(o)}/{len(o)}",
                               "sub_pass": f"{sum(e['pass'] for e in s)}/{len(s)}"}
            elif s and all(e["pass"] for e in s):
                prop[model] = {"decision": "替身字（維持全域）", "elevenlabs_entry": {w: sub},
                               "orig_pass": f"{sum(e['pass'] for e in o)}/{len(o)}", "sub_pass": f"{len(s)}/{len(s)}"}
            else:
                prop[model] = {"decision": "兩者都有未通過（不提案）", "orig_pass": f"{sum(e['pass'] for e in o)}/{len(o)}",
                               "sub_pass": f"{sum(e['pass'] for e in s)}/{len(s)}"}
        res["proposal"][w] = prop
    for model in TTS_MODELS.values():
        res.setdefault("proposed_elevenlabs_table", {})[model] = {
            w: p[model]["elevenlabs_entry"][w] for w, p in res["proposal"].items() if "elevenlabs_entry" in p[model]}
    return res


def cmd_report(args) -> None:
    st = load_state()
    metrics = load_metrics()
    if st.get("sample_jobs"):
        metrics["samples"] = measure_samples(st, metrics)
        opts = option_f0(metrics["samples"])
        sep = separation(opts)
        (OUT / "separation_matrix.json").write_text(json.dumps(sep, ensure_ascii=False, indent=1), "utf-8")
        sep["preview_reference"] = separation(preview_options(metrics))
        sep["preview_reference"]["_說明"] = ("參考：用預覽文字（各角色文字不同、長約 100–115 字元）的 F0 中位數做同樣的兩兩比較，"
                                            "未存檔的設計候選也列入；選項名 edge_<角色> 是 edge 基準念預覽文字。正式比較以上層（代表句）為準。")
        (OUT / "separation_matrix.json").write_text(json.dumps(sep, ensure_ascii=False, indent=1), "utf-8")
        prop = pronounce_proposal(metrics["samples"])
        (OUT / "proposed_pronounce_el.json").write_text(json.dumps(prop, ensure_ascii=False, indent=1), "utf-8")
    else:
        sep, prop = None, None
    metrics["budget"] = {"cap": CAP, "spent": spent(), "calls": usage_rows()}
    save_metrics(metrics)
    write_candidates(st, metrics)
    write_transcripts(metrics)
    write_listen(st, metrics)
    write_index(st, metrics, sep, prop)
    print(f"報告完成；本腳本已用點數 {spent()} / {CAP}")


def write_candidates(st: dict, metrics: dict) -> None:
    descs = descriptions()
    sel = metrics.get("selection", {})
    doc = {"_說明": "EL 選角聲線設計：全部候選（每次設計回傳 3 個預覽，全部量測）。只列客觀條件與結果，不含評分或推薦。",
           "criteria": CRITERIA, "tiers": TIERS, "select_rule": SELECT_RULE,
           "design_specs": {r: {"role_zh": ROLES[r]["zh"], "description": descs[r], "fallback_description": FALLBACK[r], "fallback2_description": FALLBACK2[r],
                                "description_source": "audio/vo/design_specs.json" if r != "pinan" else
                                "本腳本（script/角色表_v03.md：四個孩子中聲音最低、輕聲、慢）",
                                "preview_lines": ROLES[r]["preview"], "preview_text_sent": role_text(r, ROLES[r]["preview"])[1],
                                "preview_text_chars": len(role_text(r, ROLES[r]["preview"])[1]),
                                "f0_target": ROLES[r]["f0_note"], "sample_lines": ROLES[r]["samples"],
                                "orig_variant_lines": ROLES[r]["orig"], "tone_frame": FRAME_TEXT if ROLES[r]["frame"] else None,
                                "check_word_coverage": coverage(r)} for r in ROLE_ORDER},
           "design_calls": [{k: d.get(k) for k in ("role", "model", "tag", "http", "ok", "billed", "request_id", "error")} |
                            {"n_previews": len(d.get("previews", []))} for d in st["designs"]],
           "candidates": sel.get("evaluation", {}), "picks": sel.get("picks", []),
           "saved_voices": st.get("saved", []), "problems": st.get("problems", [])}
    (OUT / "candidates.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")


def _fmt(v, nd=1):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def write_transcripts(metrics: dict) -> None:
    L = ["# EL 選角（聲線設計）逐字稿比對", "",
         "轉寫：faster-whisper small 與 large-v3-turbo（vo_lib.transcribe_compare，提示詞「以下是繁體中文的台灣華語。」）。"
         "原文＝劇本台詞（字幕用）；送出文字＝實際送進合成器的文字（替身字版或原字版）。PER＝含聲調拼音錯率，"
         "參考讀音取送出文字。「排除人名」＝轉寫裡的「平安」視為「品安」後重算（已知轉寫混淆）。聽感未驗證。", ""]

    def block(key, r):
        a = r["asr"]
        L.append(f"## {key}")
        L.append("")
        L.append(f"- 檔案：`{r['file']}`")
        L.append(f"- 原文：{r['ref']}")
        L.append(f"- 送出文字：{r['synth_text']}")
        for name, m in a["models"].items():
            L.append(f"- {name}：{m['hyp_trad']}（CER {m['cer']}、PER {m['per']}、排除人名 PER {m['per_excl_name']}）")
            bad = [d for d in m["diffs"] if d["kind"] != "同音字（讀音一致）"]
            if m["diffs"]:
                L.append("  - 差異：" + "；".join(f"{d['ref'] or '∅'}→{d['hyp'] or '∅'}（{d['kind']}）" for d in m["diffs"]))
            if not bad:
                L.append("  - 沒有非同音差異")
        if a["check_status"]:
            L.append("- 檢查詞：" + "；".join(f"{w}：" + "／".join(f"{k} {v}" for k, v in s.items())
                                          for w, s in a["check_status"].items()))
        L.append(f"- 判定：{a['verdict']}")
        L.append("")
    L.append("# 一、設計預覽與 edge 基準（預覽文字）")
    L.append("")
    for key, r in metrics.get("previews", {}).items():
        block(key, r)
    if metrics.get("samples"):
        L.append("# 二、代表句（存好的聲線 × eleven_multilingual_v2／eleven_v3，及 edge 基準）")
        L.append("")
        for key, r in metrics["samples"].items():
            block(key, r)
    (OUT / "transcripts.md").write_text("\n".join(L), "utf-8")


def write_listen(st: dict, metrics: dict) -> None:
    pv = metrics.get("previews", {})
    sm = metrics.get("samples", {})
    ev = metrics.get("selection", {}).get("evaluation", {})
    saved = {s["cid"]: s for s in st.get("saved", []) if s.get("voice_id")}
    parts = []
    for role in ROLE_ORDER:
        zh = ROLES[role]["zh"]
        rows = []
        e = pv.get(f"edge_{role}")
        if e:
            rows.append(("edge 基準（預覽文字）", f"{e['edge_spec']['voice']} {e['edge_spec']['rate']} {e['edge_spec']['pitch']}",
                         e["file"], e["measure"]["f0_median"]))
        for cid, r in pv.items():
            if r["kind"] == "el_preview" and r["role"] == role:
                tag = "已存" if cid in saved else ""
                rows.append((f"設計預覽 {cid} {tag}", f"{r['ttv_model']}｜{r['desc_tag']}", r["file"], r["measure"]["f0_median"]))
        srows = []
        for key, r in sm.items():
            if r["role"] != role:
                continue
            label = "edge 基準" if r["mshort"] == "edge" else f"{r['cid']}｜{r['model']}"
            var = "原字" if r["variant"] == "orig" else ("替身字" if r["synth_text"] != r["ref"] else "")
            srows.append((f"{label}｜{r['line']} {var}", r["synth_text"], r["file"], r["measure"]["f0_median"]))
        if not rows and not srows:
            continue
        sec = [f'<section><h2>{html.escape(zh)}</h2><p class="note">F0 目標：{html.escape(ROLES[role]["f0_note"])}</p>']
        sec.append(f'<p class="text">預覽文字：{html.escape(role_text(role, ROLES[role]["preview"])[0])}</p>')
        sec.append('<h3>預覽</h3><ul>')
        for label, sub, f, f0 in rows:
            sec.append(f'<li><div class="lab"><b>{html.escape(label)}</b><span>{html.escape(sub)}｜F0 中位 {_fmt(f0)} Hz</span></div>'
                       f'<audio controls preload="none" src="{html.escape(relout(V.ROOT / f))}"></audio></li>')
        sec.append('</ul>')
        if srows:
            sec.append('<h3>代表句</h3><ul>')
            for label, sub, f, f0 in sorted(srows):
                sec.append(f'<li><div class="lab"><b>{html.escape(label)}</b><span>{html.escape(sub)}｜F0 中位 {_fmt(f0)} Hz</span></div>'
                           f'<audio controls preload="none" src="{html.escape(relout(V.ROOT / f))}"></audio></li>')
            sec.append('</ul>')
        sec.append('</section>')
        parts.append("\n".join(sec))
    page = f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>選角試聽</title>
<style>
:root {{ --bg:#faf8f4; --fg:#2b2622; --muted:#6d655d; --card:#ffffff; --line:#e4ddd3; --accent:#9a4b2f; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#1d1a17; --fg:#ece6de; --muted:#a89e93; --card:#272320; --line:#3a342f; --accent:#e09a78; }} }}
:root[data-theme="dark"] {{ --bg:#1d1a17; --fg:#ece6de; --muted:#a89e93; --card:#272320; --line:#3a342f; --accent:#e09a78; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 "PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif; }}
main {{ max-width:880px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:1.5rem; margin:0 0 4px; }}
h2 {{ font-size:1.25rem; color:var(--accent); margin:32px 0 4px; }}
h3 {{ font-size:1rem; margin:16px 0 8px; }}
.note, .text {{ color:var(--muted); font-size:.9rem; margin:4px 0; }}
ul {{ list-style:none; padding:0; margin:0; }}
li {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:8px 12px; margin:6px 0; }}
.lab {{ display:flex; flex-wrap:wrap; gap:4px 12px; align-items:baseline; }}
.lab span {{ color:var(--muted); font-size:.85rem; }}
audio {{ width:100%; margin-top:6px; }}
</style>
</head>
<body>
<main>
<h1>選角試聽</h1>
<p class="note">ElevenLabs 聲線設計候選與 edge-tts 基準（全部經同一母帶處理：−18 LUFS、真峰值 ≤ −1.5 dBTP）。數據與篩選條件見 INDEX.md；
本頁只供選擇性試聽，不含推薦。聽感與台灣口音由使用者判斷（代理聽不到聲音，一律未驗證）。</p>
{"".join(parts)}
</main>
</body>
</html>
"""
    (OUT / "listen.html").write_text(page, "utf-8")


def write_index(st: dict, metrics: dict, sep: dict | None, prop: dict | None) -> None:
    pv = metrics.get("previews", {})
    sel = metrics.get("selection", {})
    ev = sel.get("evaluation", {})
    sm = metrics.get("samples", {})
    L = ["# EL 選角：聲線設計驗收包（入口）", "",
         "製作代理：配音製作（ElevenLabs 聲線設計）。腳本：`tools/vo_el_design.py`。本包只列候選與全部數據，**不含評分或推薦**；"
         "篩選只用下列客觀條件。聽感、台灣口音自然度、「像不像孩子」的聽覺判斷一律 **未驗證**（Claude 聽不到聲音）。", "",
         "## 0. 檔案", "",
         "| 檔案 | 內容 |", "|---|---|",
         "| `candidates.json` | 設計規格（描述、預覽文字、檢查詞涵蓋）、每次設計呼叫、全部預覽候選與條件判定、存檔聲線 |",
         "| `metrics.json` | 全部量測（預覽、edge 基準、代表句）、篩選、點數紀錄 |",
         "| `transcripts.md` | 每個檔兩個轉寫模型的逐字稿、CER／PER、差異與檢查詞 |",
         "| `tone_checks/*.json` | 「紙燈節」聲調（燈高平、節上揚）F0 走勢 |",
         "| `separation_matrix.json` | 角色區分：F0 兩兩半音差、全部組合與混搭 |",
         "| `proposed_pronounce_el.json` | ElevenLabs 原字對替身字的讀音提案（不改 pronounce.json） |",
         "| `previews/`、`samples/` | 原始 mp3（預覽）與母帶處理後 wav（48 kHz／16-bit／單聲道） |",
         "| `listen.html` | 選擇性試聽頁（相對路徑） |", "",
         "## 1. 方法", "",
         "- 聲線設計：`POST /v1/text-to-voice/design`（`output_format=mp3_44100_128`、`seed=20261021`、`guidance_scale=5`、"
         "`loudness=0.5`、`should_enhance=false`）。描述：小晴、小宇、折折取 `audio/vo/design_specs.json`；品安依 `script/角色表_v03.md` 補寫"
         "（四個孩子中聲音最低、輕聲、慢）。預覽文字＝該角色劇本台詞串接（≥100 字元，套 `pronounce.json` 全域替身字，和正式管線相同），"
         "每次回傳 3 個預覽，全部量測。",
         "- 描述被拒的處理（三層，全部記錄原文）：①原描述（寫兒童年齡）→ ②任務指定改寫「為兒童角色配音的年輕成人配音員，明亮、輕快、帶童聲質感的台灣華語」"
         "（英文版）→ ③代理新增：①②在 eleven_ttv_v3 與 eleven_multilingual_ttv_v2 都回 403 blocked_generation，第三層拿掉所有兒童字眼"
         "（child、children's、schoolgirl、childlike、nine-year-old），只描述音色（年輕成人女性、明亮／偏低、輕聲等）。三層全文見 candidates.json → design_specs。"
         "折折的原描述（摺紙貓主持人）沒有被擋。",
         "- 模型：四個角色先用 eleven_ttv_v3；eleven_multilingual_ttv_v2 加試小晴（原意只是確認安全過濾是否同樣擋兒童描述，結果第三層通過而產生預覽）"
         "與折折（ttv_v3 三個預覽 F0 都低於 280 Hz、且原描述可用）。小宇、品安未加試 ttv_v2，以保留點數。",
         "- edge-tts 基準：同一段文字，照 `audio/vo/casting.json` 目前參數（含 post 設定）以 `vo_build.render_line` 合成。",
         "- 母帶處理同 G3：`vo_lib.master`（頭 120 ms、尾 250 ms、−18 LUFS、真峰值 ≤ −1.5 dBTP、48 kHz／16-bit／單聲道）。",
         "- 量測同 G3：`vo_lib.measure`（響度、真峰值、削波、頭尾靜音、毛語速／淨語速、句中停頓、F0 中位數與 p10–p90），"
         "轉寫 `vo_lib.transcribe_compare`（small＋large-v3-turbo，逐字對齊＋台灣讀音表）。共振峰："
         f"Praat Burg 法 LPC，上限 {FORMANT_CEIL:.0f} Hz（5500 Hz 版另列於 metrics.json）。",
         "- 代表句：存好的聲線 × `eleven_multilingual_v2`（stability 0.5、similarity 0.75、style 0、speaker boost、speed 1.0）與 "
         "`eleven_v3`（stability 0.5、similarity 0.75、language_code zh），seed 20261021、mp3_44100_128；替身字版為主，另做原字對照句與短框句「紙燈節。」。",
         "", "## 2. 客觀條件與篩選規則", ""]
    for k, v in CRITERIA.items():
        L.append(f"- **{k}**：{v}")
    L.append("")
    for k, v in TIERS.items():
        L.append(f"- 級別 {k}：{v}")
    L.append(f"- 選取：{SELECT_RULE}")
    L.append("")
    # 設計呼叫
    L += ["## 3. 設計呼叫", "", "| 角色 | 模型 | 描述 | HTTP | 計費（character-cost） | 預覽數 | 錯誤原文 |", "|---|---|---|---|---|---|---|"]
    for d in st["designs"]:
        bill = _fmt(d.get("billed")) if d.get("billed") else (f"無標頭（估計 {DESIGN_EST_FACTOR * len(d['text'])}）" if d["ok"] else "—")
        L.append(f"| {ROLES[d['role']]['zh']} | {d['model']} | {d['tag']} | {d['http']} | {bill} | "
                 f"{len(d.get('previews', []))} | {json.dumps(d.get('error'), ensure_ascii=False) if d.get('error') else ''} |")
    L.append("")
    # 預覽表
    L += ["## 4. 全部預覽候選與 edge 基準（預覽文字）", "",
          "F0／F1／F2 單位 Hz；倍率＝相對同角色 edge 基準；PER＝small／large-v3-turbo（括號為排除人名後的最小值）；"
          "語速＝毛／淨（字／秒）；停頓＝句中 ≥150 ms 停頓數與最長（ms）。", "",
          "| 候選 | F0 中位（p10–p90） | 距目標（半音） | F1／F2（倍率） | PER | 檢查詞 | 紙燈節聲調 | LUFS／dBTP／削波 | 語速 毛／淨 | 停頓 數／最長 | 頭／尾靜音 ms | 級別 | 存檔 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    saved_ids = {s["cid"]: s for s in st.get("saved", [])}
    for role in ROLE_ORDER:
        keys = [f"edge_{role}"] + sorted(k for k, r in pv.items() if r["kind"] == "el_preview" and r["role"] == role)
        for k in keys:
            r = pv.get(k)
            if not r:
                continue
            m, a = r["measure"], r["asr"]
            e = ev.get(k, {})
            fm = m["formants"]
            ratio = f"（{_fmt(e.get('F1_ratio_vs_edge'), 3)}／{_fmt(e.get('F2_ratio_vs_edge'), 3)}）" if e else "（基準）"
            tone = r.get("tone_zdj")
            tone_s = ("—" if not tone else ("通過" if tone["pass"] else ("未定位" if not tone["located"] else "未通過"))
                      + (f"（燈 {tone['燈']['end_over_start']}、燈/紙 {tone['燈_over_紙_mean']}、節 {tone['節']['end_over_start']}）"
                         if tone and tone.get("located") else ""))
            sv = saved_ids.get(k)
            L.append(f"| {('**' + k + '**') if k.startswith('edge') else k} | {_fmt(m['f0_median'])}（{_fmt(m['f0_p10'])}–{_fmt(m['f0_p90'])}） | "
                     f"{_fmt(e.get('f0_dist_semitones'), 2) if e else '—'} | {_fmt(fm['F1_median'], 0)}／{_fmt(fm['F2_median'], 0)}{ratio} | "
                     f"{a['models']['small']['per']}／{a['models']['large-v3-turbo']['per']}（{a['per_min_excl_name']}） | "
                     f"{'一致' if a['check_words_ok_both'] else '有不一致'} | {tone_s} | "
                     f"{_fmt(m['integrated_lufs'])}／{_fmt(m['true_peak_dbtp'])}／{m['clipped_samples']} | "
                     f"{_fmt(m['rate_cps'], 2)}／{_fmt(m['rate_cps_net'], 2)} | {len(m['pauses_ms'])}／{max(m['pauses_ms']) if m['pauses_ms'] else 0} | "
                     f"{m['head_silence_ms']}／{m['tail_silence_ms']} | {_fmt(e.get('tier')) if e else '—'} | "
                     f"{('已存 ' + str(sv.get('voice_id'))) if sv and sv.get('voice_id') else ('失敗 HTTP ' + str(sv['http']) if sv else '')} |")
    L.append("")
    L.append("各候選每個條件的真假值見 `candidates.json` → candidates[*].criteria；檢查詞逐詞狀態見 check_status。台灣口音：全部未驗證。")
    L.append("")
    # 存檔
    L += ["## 5. 存成正式聲線", "", f"選取：{', '.join(sel.get('picks', [])) or '（無）'}；沒有候選的角色：{', '.join(ROLES[r]['zh'] for r in sel.get('roles_without_pick', [])) or '無'}", "",
          "| 候選 | 角色 | 級別 | voice_name | voice_id | HTTP | 錯誤原文 |", "|---|---|---|---|---|---|---|"]
    for s in st.get("saved", []):
        L.append(f"| {s['cid']} | {ROLES[s['role']]['zh']} | {s.get('tier')} | {s['voice_name']} | {s.get('voice_id') or '—'} | {s['http']} | "
                 f"{json.dumps(s['detail'], ensure_ascii=False) if s.get('detail') else ''} |")
    L.append("")
    # 代表句
    if sm:
        L += ["## 6. 代表句（存好的聲線 × 兩個 TTS 模型，及 edge 基準）", "",
              "| 檔 | 送出文字 | F0 中位（p10–p90） | F1／F2 | PER small／turbo | 檢查詞 | 紙燈節聲調 | LUFS／dBTP／削波 | 語速 毛／淨 | 停頓 | 頭／尾 ms |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for role in ROLE_ORDER:
            for k in sorted(k for k, r in sm.items() if r["role"] == role):
                r = sm[k]
                m, a = r["measure"], r["asr"]
                tone = r.get("tone_zdj")
                tone_s = ("—" if not tone else ("通過" if tone["pass"] else ("未定位" if not tone["located"] else "未通過"))
                          + (f"（燈 {tone['燈']['end_over_start']}、燈/紙 {tone['燈_over_紙_mean']}、節 {tone['節']['end_over_start']}）"
                             if tone and tone.get("located") else ""))
                L.append(f"| {k} | {r['synth_text']} | {_fmt(m['f0_median'])}（{_fmt(m['f0_p10'])}–{_fmt(m['f0_p90'])}） | "
                         f"{_fmt(m['formants']['F1_median'], 0)}／{_fmt(m['formants']['F2_median'], 0)} | "
                         f"{a['models']['small']['per']}／{a['models']['large-v3-turbo']['per']} | "
                         f"{'一致' if a['check_words_ok_both'] else '有不一致'} | {tone_s} | "
                         f"{_fmt(m['integrated_lufs'])}／{_fmt(m['true_peak_dbtp'])}／{m['clipped_samples']} | "
                         f"{_fmt(m['rate_cps'], 2)}／{_fmt(m['rate_cps_net'], 2)} | {m['pauses_ms']} | {m['head_silence_ms']}／{m['tail_silence_ms']} |")
        L.append("")
    if sep:
        L += ["## 7. 角色區分（F0 中位數兩兩 ≥3 半音；同底聲另須 ≥10%）", "",
              "| 選項 | 角色 | F0 中位（代表句合併） | 底聲 |", "|---|---|---|---|"]
        for k, o in sep["options"].items():
            L.append(f"| {k} | {o['role_zh']} | {_fmt(o['f0_median_pooled'])} | {o['base_voice']} |")
        L += ["", f"全部組合 {sep['combos_total']} 種，兩兩都通過 {sep['combos_all_pass']} 種（清單見 separation_matrix.json → combos）。", "",
              "混搭（只換一個角色、其他維持 edge）：", ""]
        for name, v in sep["named_mixes"].items():
            fails = [p["pair"] + f"（{p['semitones']}）" for p in v["pairs"] if not p["pass"]]
            L.append(f"- {name}：{'全部通過' if v['all_pass'] else '未通過：' + '、'.join(fails)}")
        pr = sep.get("preview_reference")
        if pr:
            L += ["", f"參考（預覽文字的 F0，未存檔候選也列入）：組合 {pr['combos_total']} 種，兩兩都通過 {pr['combos_all_pass']} 種；"
                      "只換一個角色、其他維持 edge 的混搭中，全部通過的有："
                      + ("、".join(k for k, v in pr["named_mixes"].items() if v["all_pass"]) or "無") + "。",
                  "", "| 預覽選項 | 角色 | F0 中位 |", "|---|---|---|"]
            for k, o in pr["options"].items():
                L.append(f"| {k} | {o['role_zh']} | {_fmt(o['f0_median_pooled'])} |")
            ptop = [c for c in pr["combos"] if c["all_pass"]][:10]
            if ptop:
                L += ["", "預覽參考中兩兩都通過的組合（依最小半音差排序前 10 個，非推薦；是否符合其他條件見第 4 節）：", ""]
                for c in ptop:
                    L.append(f"- {json.dumps(c['combo'], ensure_ascii=False)}：最小 {c['min_semitones']} 半音")
        top = [c for c in sep["combos"] if c["all_pass"]][:10]
        if top:
            L += ["", "兩兩都通過的組合（依最小半音差排序的前 10 個，非推薦）：", ""]
            for c in top:
                L.append(f"- {json.dumps(c['combo'], ensure_ascii=False)}：最小 {c['min_semitones']} 半音")
        L.append("")
    if prop:
        L += ["## 8. 讀音提案（proposed_pronounce_el.json）", ""]
        for w, p in prop["proposal"].items():
            L.append(f"- {w}：" + "；".join(f"{m}：{v['decision']}（原字通過 {v.get('orig_pass')}、替身字通過 {v.get('sub_pass')}）"
                                            for m, v in p.items()))
        L.append("")
    b = metrics.get("budget", {})
    calls = b.get("calls", [])
    by = {}
    for c in calls:
        kind = c.get("endpoint") or "text-to-speech"
        x = by.setdefault(kind, {"calls": 0, "ok": 0, "billed": 0, "est": 0})
        x["calls"] += 1
        x["ok"] += 1 if c.get("ok") else 0
        if c.get("billed") is not None and str(c["billed"]).isdigit():
            x["billed"] += int(c["billed"])
        elif c.get("ok") and kind == "text-to-voice/design":
            x["est"] += DESIGN_EST_FACTOR * int(c.get("text_chars") or 0)
    hdr = sum(v["billed"] for v in by.values())
    est = sum(v["est"] for v in by.values())
    L += ["## 9. 點數", "",
          f"本腳本上限 {CAP} 點（含設計預覽），計入值 **{b.get('spent')}** 點＝回應標頭 character-cost 合計 {hdr} 點＋設計預覽估計 {est} 點。"
          f"設計端點（text-to-voice/design）的回應沒有 character-cost 標頭（實測），所以每次成功的設計保守以「3 個預覽 × 預覽文字字元數」估計；"
          "被安全過濾擋下（403 blocked_generation）的呼叫沒有產生預覽，不計。金鑰沒有 user_read 權限，查不到帳號剩餘點數，"
          f"實際扣點請以帳號後台為準（升級後 39,701 點；同時段另一個選角工作流也在用）。紀錄：audio/vo/elevenlabs_usage.jsonl，purpose 以「{PREFIX}」開頭。", ""]
    for k, v in by.items():
        L.append(f"- {k}：{v['calls']} 次（成功 {v['ok']}），標頭計費 {v['billed']} 點" + (f"、估計 {v['est']} 點" if v["est"] else ""))
    L.append("")
    L += ["## 10. 未驗證與已知限制", "",
          "- 聽感、台灣口音自然度、是否像孩子：未驗證（共振峰只是客觀代理指標）。",
          "- 「一」「不」變調：轉寫看不出，未驗證。",
          "- 人名「品安」：兩個轉寫模型都可能寫成「平安」（G3 已知），PER 另列排除人名版。",
          "- 預覽是設計模型（eleven_ttv_*）的輸出；存檔後用 TTS 模型念出的音高、語速可能不同，以第 6 節代表句為準。",
          "- 紙燈節聲調條件（節終點／起點 ≥1.10）：edge 基準（目前正式參數）在句末與短框句也沒有達到（見第 4、6 節），條件照原定值判定，未放寬。",
          "- 短框句「紙燈節。」只有三個字，轉寫模型缺上下文，常轉成其他詞（例如 edge 折折的「子彈結」）；以 F0 走勢與句中版本對照。",
          "- 讀音探測列（檔名含 probe_）是借用小晴設計聲線念其他角色的句子，只供讀音提案，不是選角樣本，也不進角色區分矩陣。",
          "- 實際投影場地音響：未驗證。", ""]
    if st.get("problems"):
        L += ["## 11. 問題紀錄", ""] + [f"- {p}" for p in st["problems"]] + [""]
    (OUT / "INDEX.md").write_text("\n".join(L), "utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["design", "previews", "select", "samples", "report"])
    ap.add_argument("--model", default="eleven_ttv_v3")
    ap.add_argument("--roles", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"design": cmd_design, "previews": cmd_previews, "select": cmd_select, "samples": cmd_samples, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
