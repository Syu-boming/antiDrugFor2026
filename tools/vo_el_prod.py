"""ElevenLabs 全劇版配音製作工具：逐句合成 → 自動檢查 (a)–(f) → 不過就換 seed 重算 → 點數保護 → edge 基準 → 驗收報告。

用法（專案根目錄；用 tools/.venv 的 Python，裡面有 faster-whisper、parselmouth、pypinyin、opencc）：
  tools/.venv/bin/python tools/vo_el_prod.py --dry-run                         # 列出句子、分段、預估點數（不呼叫、不寫檔）
  tools/.venv/bin/python tools/vo_el_prod.py --role ye --max-credits 300       # 某角色的全劇台詞（可多個 --role）
  tools/.venv/bin/python tools/vo_el_prod.py --line a2_c012_01 --line a5_c008_03 --max-attempts 6 --max-credits 300
  tools/.venv/bin/python tools/vo_el_prod.py                                   # 所有有 EL 角色設定（status=active）的台詞
  tools/.venv/bin/python tools/vo_el_prod.py --baseline-edge [--role …|--line …]   # edge 基準（免費、不重算；不指定＝全劇）
  tools/.venv/bin/python tools/vo_el_prod.py --report                          # 彙整寫出 review/G3/el/full/
  --reuse-edge-baseline：沿用既有 edge 基準（人名豁免用），不因簽章變動重算、不呼叫 edge-tts。
  角色設定 lines.<id>.seed_base：逐句 seed 起點（重做時第 1 次沿用原採用的 seed）。
  其他選項：--force（不沿用既有輸出，從第 1 次嘗試重新判定；同 seed、同文字的 EL 原始檔快取會沿用，不重複計費——
            要拿到新的合成結果請改角色設定的 seed_base）、--include-draft（連 status=draft 的角色一起做）。
  續跑：--max-credits 到了會停在下一個呼叫之前（exit 3），已完成的句子沿用、未完成的句子從下一次嘗試接著做。

角色設定：audio/vo_el/casting/<角色代碼>.json（代碼沿用 audio/vo/casting.json 的 code）。欄位見該資料夾任一檔的 _說明。

每次嘗試的自動檢查（全部通過才採用；都沒通過就保留問題最少的一次，標 fail）：
  (a) 轉寫：faster-whisper small 與 large-v3-turbo 各轉寫一次，用 vo_lib.compare（逐字對齊；參考讀音取 pronounce.json
      全域替身字；台灣讀音表）和劇本比對，兩個模型都只能有「同音字」。人名差異若在 edge 基準同一句、同一模型也出現
      同音的轉寫（拼音含聲調相同），視為轉寫器詞彙問題，不算失敗（必要旁白不適用此例外）。
  (b) 讀音檢查詞（script/讀音檢查表.md＋任務指定）：句中有的詞，兩個模型都要「轉寫一致」或「同音轉寫」。
  (c) 句尾完整：每一段 ElevenLabs 原始檔最後 60 ms 不可仍有聲。方法同 review/G3/el/qa/配音導演/tail_voicing.py：
      ffmpeg 解成 48 kHz、20 ms 窗 RMS 相對 p90、最後三窗平均 > −25 dB 而且 parselmouth 自相關有聲比例 > 30% ＝截斷。
      用句尾保護（tail_guard）時改在切點前 60 ms 用同一門檻判定（原始檔結尾的數值另存 tail_raw_end）。
  (d) 淨語速：vo_lib.measure 的驗收者算法（−40 dB、扣掉 ≥200 ms 停頓），字數改成「漢字＋數字逐字」（119＝3 音節）；
      在角色 targets.rate_cps_net 範圍內。少於 6 音節的句子不適用。
  (e) 句間停頓：多句台詞每個句界的靜音（10 ms RMS 低於最大值 −35 dB）≥150 ms；必要旁白 ≥1300 ms。
  (f) 母帶：整合響度 −18±0.5 LUFS（有 loudness_offset_db 時目標跟著移）、真峰值 ≤ −1.5 dBTP、削波 0。
重算：換 seed（seed_base＋嘗試序號）。adaptive_speed 開啟時，上一次語速超出範圍就把 speed 調 ±step（eleven_v3 實測不理會 speed）。
減輕方法（角色設定可選；報告逐句寫明）：
  tail_guard：句尾加「……嗯。」讓合成器的截斷落在填充字，再用轉寫時間戳＋能量在正文後的停頓切掉（guard_cut）；
  segment_mode=post：整句一次合成（v3 分段合成時語速變快），再依轉寫時間戳在句界插入停頓（insert_boundaries）；
  tail_guard 關閉時的舊法：同一段句尾截斷 2 次以上，下一次句尾補「……」。

金鑰：只經 vo_lib.el_request 讀取，本工具不讀、不印、不寫金鑰。每次呼叫都用 vo_lib.log_usage 記到
audio/vo/elevenlabs_usage.jsonl（purpose 以「EL 全劇」開頭；失敗記錄錯誤原文）。計費以回應標頭 character-cost 為準。
只寫：audio/vo_el/、audio/lipsync_el/、review/G3/el/full/（以及上述 usage 紀錄的追加）。
edge 基準的原始檔：audio/vo/_raw 已有的快取只讀取沿用，新合成的放 review/G3/el/full/edge/_raw/（不寫 audio/vo/）。
聽感（台灣口音、自然度、像不像孩子）一律未驗證：Claude 聽不到聲音。
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import difflib
import fcntl
import os
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402
import vo_build as B  # noqa: E402

ROOT = V.ROOT
SR = V.SR
OUT = ROOT / "audio" / "vo_el"
CAST_DIR = OUT / "casting"
RAW = OUT / "_raw"
ATT = OUT / "_attempts"
LIP = ROOT / "audio" / "lipsync_el"
REPORT = OUT / "build_report_el.json"
TIMINGS = OUT / "timings_el.json"
LEDGER = OUT / "ledger.json"
FULL = ROOT / "review" / "G3" / "el" / "full"
EDGE = FULL / "edge"
EDGE_RAW = EDGE / "_raw"
EDGE_METRICS = EDGE / "metrics.json"
LISTEN = FULL / "listen"

VER = "el01"
TOOL_VERSION = "vo_el_prod/1"
FMT = "mp3_44100_128"            # Starter 只能用這個格式
PURPOSE = "EL 全劇"
EST_PER_CHAR = 0.5               # 呼叫前的保守預估（中文實際約 0.4 點／字元，以 character-cost 為準）
MAX_ATTEMPTS_CAP = 6             # license_evidence.md 第 4 節：每句最多 6 次

REQUIRED = {  # CLAUDE.md 兒童安全界線第 4 條，一字不改
    "a2_c004_02": "這些線是故事的比喻。毒品可能讓人的頭腦和身體受到影響，不聽使喚。人不會真的變成喪屍。",
    "a2_c008_05": "不過，看見一個人站不穩，不能就說他吸毒，也可能有其他身體狀況。我們要先找大人幫忙。",
}
REQUIRED_GAP_MS = 1300
REQUIRED_INSERT_MS = 1650   # 實際插入的靜音：v3 句首常帶 0.3 s 吸氣聲，插 1300 時真正無聲（−50 dBFS）只剩約 1.0 s（G3 EL 驗收 2026-10-21）；檢查門檻仍是 1300
MIN_GAP_MS = 150
REQUIRED_RATE = [3.0, 4.0]       # 角色表「必要旁白放慢到約 3.5」±0.5（淨語速）
RATE_TOL = 0.5                   # 一般台詞：角色表語速 ±0.5 字／秒（逐句自然變動）
MIN_SYLL_FOR_RATE = 6
CHECK_WORDS = ["紙燈節", "燈籠", "折折", "阿樂叔叔", "喪屍煙彈", "電子煙", "垃圾", "口訣", "竹篾", "119"]
NAMES = ["小晴", "小宇", "阿樂", "折折", "品安", "周品安", "阿琴", "葉護理師", "林老師", "陳伯伯", "立恆", "雅雯", "正雄"]
HOMO = "同音字（讀音一致）"
W_OK = {"轉寫一致", "同音轉寫（讀音一致）"}
TAIL_SUFFIX = "……"

# 角色表第 3 節（語速，字／秒）與 audio/vo/casting.json 各角色 note（F0 Hz）。F0 只列入報告，不當成逐句的通過條件。
DEFAULT_TARGETS = {
    "narrator": {"rate_nominal": [3.8, 4.0], "f0_nominal": 185.0},
    "zhezhe": {"rate_nominal": [4.3, 4.6], "f0_nominal": 293.5, "f0_hz": [280.0, 360.0]},
    "xiaoqing": {"rate_nominal": [3.9, 4.1], "f0_nominal": 276.9},
    "xiaoyu": {"rate_nominal": [4.2, 4.4], "f0_nominal": 228.0},
    "pinan": {"rate_nominal": [3.6, 3.8], "f0_nominal": 181.0},
    "ale": {"rate_nominal": [3.6, 3.8], "f0_nominal": 113.0},
    "ye": {"rate_nominal": [3.8, 4.0], "f0_nominal": 148.0},
    "lin": {"rate_nominal": [3.9, 4.1], "f0_nominal": 161.0},
    "chen": {"rate_nominal": [3.5, 3.7], "f0_nominal": 91.7},
    "inviter": {"rate_nominal": [4.0, 4.4], "f0_nominal": 167.0, "f0_hz": [145.0, 175.0]},
    "dispatcher": {"rate_nominal": [4.0, 4.4], "f0_nominal": 203.0},
}
ALE_AFFECTED = re.compile(r"a2_c0(0[1-9]|1[0-2])_\d{2}|a4_c001_\d{2}|a4_c008_\d{2}")   # casting.json 阿樂受影響段

LINES = V.load_lines()
CAST = json.loads((V.VO_DIR / "casting.json").read_text("utf-8"))
PRON = V.load_pronounce()
ROLE2CODE = {r: c.get("code", V.ROLE_CODES.get(r)) for r, c in CAST["roles"].items()}
CODE2ROLE = {c: r for r, c in ROLE2CODE.items()}
D = CAST["defaults"]


class BudgetStop(Exception):
    pass


class ApiStop(Exception):
    pass


# ---------------------------------------------------------------- 小工具
def rel(p: Path) -> str:
    p = Path(p)
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def jload(p: Path, default):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except Exception:
        return copy.deepcopy(default)


def _jdefault(o):
    if isinstance(o, (np.generic,)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return rel(o)
    raise TypeError(f"無法寫成 JSON：{type(o)}")


def jsave(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=_jdefault), "utf-8")
    tmp.replace(p)


@contextlib.contextmanager
def locked(p: Path):
    """共用 JSON（build_report_el／timings_el／ledger／edge metrics）的檔案鎖：成人組、兒童組可能同時執行本工具，
    寫入一律「鎖住 → 重新讀檔 → 只改自己的鍵 → 寫回」，不用執行開始時讀進記憶體的舊副本整份覆寫。"""
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p.with_suffix(p.suffix + ".lock"), "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def merge_save(p: Path, key: str, value) -> None:
    """鎖住後重新讀檔，只寫入（value＝None 時刪除）一個鍵。"""
    with locked(p):
        cur = jload(p, {})
        if value is None:
            cur.pop(key, None)
        else:
            cur[key] = value
        jsave(p, dict(sorted(cur.items())))


def sha(obj) -> str:
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def deep_merge(a: dict, b: dict) -> dict:
    return B.deep_merge(a or {}, b or {})


def roles_of(line: dict) -> list[str]:
    return [r.strip() for r in line["role"].split("、")]


def verify_required() -> None:
    for lid, t in REQUIRED.items():
        if LINES.get(lid, {}).get("text") != t:
            raise SystemExit(f"必要旁白 {lid} 和 CLAUDE.md 不一致：{LINES.get(lid, {}).get('text')!r}")


def semitones(a: float, b: float) -> float:
    return round(12 * math.log2(b / a), 2)


# ---------------------------------------------------------------- 角色設定與目標
def load_cast(code: str) -> dict | None:
    p = CAST_DIR / f"{code}.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def active_codes(include_draft: bool = False) -> list[str]:
    out = []
    for p in sorted(CAST_DIR.glob("*.json")):
        c = json.loads(p.read_text("utf-8"))
        if c.get("status", "active") == "active" or (include_draft and c.get("status") == "draft"):
            out.append(c["code"])
    return out


def rate_range(t: dict) -> list[float]:
    if t.get("rate_cps_net"):
        return list(t["rate_cps_net"])
    lo, hi = t["rate_nominal"]
    return [round(lo - RATE_TOL, 2), round(hi + RATE_TOL, 2)]


def f0_range(t: dict) -> list[float]:
    if t.get("f0_hz"):
        return list(t["f0_hz"])
    f = t["f0_nominal"]
    return [round(f * 2 ** (-2 / 12), 1), round(f * 2 ** (2 / 12), 1)]


def line_targets(code: str, lid: str, cfg: dict | None = None) -> dict:
    """角色目標＋逐句覆寫（必要旁白、阿樂受影響段、角色設定 lines.<id>.targets）。"""
    t = copy.deepcopy((cfg or {}).get("targets") or DEFAULT_TARGETS.get(code, {"rate_nominal": [3.6, 4.4], "f0_nominal": 180.0}))
    t["source"] = t.get("source", "角色表第 3 節／casting.json note")
    if code == "ale" and ALE_AFFECTED.fullmatch(lid):
        t.pop("rate_cps_net", None)
        t["rate_nominal"] = [3.3, 3.5]
        t["f0_nominal"] = 103.0
        t["note"] = "阿樂受影響段（角色表 3.3–3.5）"
    if lid in REQUIRED:
        t["rate_cps_net"] = list(REQUIRED_RATE)
        t["note"] = "必要旁白：語速要慢（角色表約 3.5，±0.5）"
    if cfg and cfg.get("lines", {}).get(lid, {}).get("targets"):
        t.update(cfg["lines"][lid]["targets"])
    t["rate_range"] = rate_range(t)
    t["f0_range"] = f0_range(t)
    return t


# ---------------------------------------------------------------- 分段與文字
SENT_FIND = re.compile(r"[^。！？]+(?:[。！？]+[」』）]*)?|[。！？]+[」』）]*")


def sentences(text: str) -> list[str]:
    """依句號、問號、驚嘆號分句；句末的引號跟著前一句；沒有字的片段併入前一句。"""
    out: list[str] = []
    for p in SENT_FIND.findall(text):
        if out and not V.HAN_RE.search(p):
            out[-1] += p
        elif p.strip():
            out.append(p)
    return out


def plan_segments(synth_text: str, gap_ms: int) -> list[tuple[str, int | None]]:
    """[(段落文字, 之後停頓毫秒)]：先依 [[break:N]]（vo_lib.split_breaks），再依句號／問號／驚嘆號分句。"""
    out: list[tuple[str, int | None]] = []
    for text, brk in V.split_breaks(synth_text):
        parts = sentences(text) or [text]
        for i, p in enumerate(parts):
            out.append((p, gap_ms if i < len(parts) - 1 else brk))
    return out


def synth_text_for(cfg: dict, lid: str, text: str) -> str:
    lc = cfg.get("lines", {}).get(lid, {})
    base = lc.get("synth_text") or text
    mode = lc.get("text_mode", cfg.get("text_mode", "pronounce"))
    t = V.apply_pronounce(base, PRON, "elevenlabs", lid) if mode == "pronounce" else base
    subs = dict(cfg.get("text_subs", {}), **lc.get("text_subs", {}))
    for k in sorted(subs, key=len, reverse=True):
        t = t.replace(k, subs[k])
    return t


def reading_of(text: str, lid: str) -> str:
    """轉寫比對的參考讀音：pronounce.json 全域替身字（代表要的讀音），與實際送出的文字無關。"""
    return V.strip_breaks(V.apply_pronounce(text, PRON, "global", lid))


def syllables(text: str) -> int:
    return len(re.findall(r"[一-鿿]", text)) + len(re.findall(r"[0-9]", text))


def n_sentences(text: str) -> int:
    return len(sentences(V.strip_breaks(text)))


# ---------------------------------------------------------------- 點數帳
LEDGER_DEFAULT = {"_說明": "ElevenLabs 全劇版點數帳（tools/vo_el_prod.py）。每筆成功呼叫依回應標頭 character-cost 累加；"
                           "失敗呼叫記 0（ElevenLabs 不計費）。runs＝每次執行的上限、實際用量與停止原因（可續跑）。",
                  "total_billed": 0, "calls": 0, "failed_calls": 0, "by_role": {}, "by_line": {}, "runs": [], "entries": []}


def ledger_add(entry: dict) -> None:
    with locked(LEDGER):
        L = jload(LEDGER, LEDGER_DEFAULT)
        b = int(entry.get("billed") or 0)
        L["calls"] += 1
        if not entry.get("ok"):
            L["failed_calls"] += 1
        L["total_billed"] += b
        L["by_role"][entry["role"]] = L["by_role"].get(entry["role"], 0) + b
        L["by_line"][entry["line"]] = L["by_line"].get(entry["line"], 0) + b
        L["entries"].append(entry)
        jsave(LEDGER, L)


RUN_KEY = f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"   # 同時有兩個行程時，各自只更新自己的 runs 紀錄


def ledger_run(update: dict, start: bool = False) -> None:
    with locked(LEDGER):
        L = jload(LEDGER, LEDGER_DEFAULT)
        mine = [r for r in L["runs"] if r.get("run_key") == RUN_KEY]
        if start or not mine:
            L["runs"].append(dict(update, run_key=RUN_KEY))
        else:
            mine[-1].update(update)
        jsave(LEDGER, L)


# ---------------------------------------------------------------- ElevenLabs 呼叫（原始檔快取在 audio/vo_el/_raw/）
def _detail(payload: bytes):
    try:
        return json.loads(payload).get("detail", json.loads(payload))
    except Exception:
        return payload[:400].decode(errors="replace")


def el_call(cfg: dict, text: str, seed: int, settings: dict, lid: str, k: int, i: int, run: dict) -> tuple[Path, dict]:
    body = {"text": text, "model_id": cfg["model"], "seed": int(seed)}
    vs = {kk: vv for kk, vv in settings.items() if vv is not None}
    if vs:
        body["voice_settings"] = vs
    if cfg.get("language_code"):
        body["language_code"] = cfg["language_code"]
    h = sha({"voice_id": cfg["voice_id"], "body": body, "fmt": FMT})[:12]
    out = RAW / lid / f"{cfg['code']}_a{k}_s{i}_{h}.mp3"
    meta = out.with_suffix(".json")
    if out.exists() and out.stat().st_size > 500 and meta.exists():
        return out, dict(json.loads(meta.read_text("utf-8")), cached=True)
    est = math.ceil(len(text) * EST_PER_CHAR) + 1
    if run["spent"] + est > run["max_credits"]:
        raise BudgetStop(f"點數上限 {run['max_credits']}：本次已用 {run['spent']}，下一段預估 {est}")
    tag = f"{PURPOSE} {cfg['role']} {lid} 嘗試{k + 1} 段{i + 1}"
    code, payload, hdr = V.el_request("POST", f"/v1/text-to-speech/{cfg['voice_id']}?output_format={FMT}", body)
    if code != 200:
        det = _detail(payload)
        V.log_usage({"purpose": tag, "voice_id": cfg["voice_id"], "model": cfg["model"], "ok": False, "http": code,
                     "detail": det, "text_chars": len(text), "seed": seed})
        ledger_add({"time": now(), "line": lid, "role": cfg["code"], "attempt": k + 1, "segment": i + 1, "ok": False,
                    "http": code, "detail": det, "billed": 0, "text_chars": len(text)})
        run["failed"] += 1
        raise ApiStop(f"ElevenLabs HTTP {code}：{det}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    cost = hdr.get("character-cost")
    billed = int(cost) if cost and str(cost).strip().isdigit() else math.ceil(len(text) * 0.4)
    src = "character-cost" if cost and str(cost).strip().isdigit() else "估計（無標頭，0.4 點／字元）"
    info = {"request_id": hdr.get("request-id"), "billed": billed, "billed_source": src, "http": 200,
            "text_chars": len(text), "seed": seed, "time": now(), "raw": rel(out)}
    meta.write_text(json.dumps(info, ensure_ascii=False), "utf-8")
    V.log_usage({"purpose": tag, "voice_id": cfg["voice_id"], "model": cfg["model"], "ok": True, "http": 200,
                 "text_chars": len(text), "billed": billed, "billed_source": src, "request_id": info["request_id"],
                 "seed": seed, "raw": rel(out)})
    ledger_add({"time": now(), "line": lid, "role": cfg["code"], "attempt": k + 1, "segment": i + 1, "ok": True,
                "http": 200, "billed": billed, "billed_source": src, "request_id": info["request_id"],
                "text_chars": len(text), "voice_id": cfg["voice_id"], "model": cfg["model"], "seed": seed, "raw": rel(out)})
    run["spent"] += billed
    run["calls"] += 1
    return out, dict(info, cached=False)


# ---------------------------------------------------------------- 訊號處理
def telephone(x: np.ndarray) -> np.ndarray:
    """與 vo_build.render_line 相同：300–3400 Hz 4 階帶通（零相位）。"""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [300, 3400], btype="band", fs=SR, output="sos")
    return sosfiltfilt(sos, x).astype(np.float32)


def psola_shift(x: np.ndarray, st: float) -> np.ndarray:
    """整段 F0 乘 2^(st/12)（Praat Manipulation，overlap-add；不改長度、不變速）。"""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=SR)
    man = call(snd, "To Manipulation", 0.01, 60, 600)
    tier = call(man, "Extract pitch tier")
    call(tier, "Multiply frequencies", snd.xmin, snd.xmax, 2 ** (st / 12))
    call([tier, man], "Replace pitch tier")
    y = call(man, "Get resynthesis (overlap-add)").values[0].astype(np.float32)
    return y[:len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))


def psola_mod(x: np.ndarray, st: float = 0.0, stretch: float = 1.0) -> np.ndarray:
    """PSOLA（Praat Manipulation，overlap-add）一次完成：F0 乘 2^(st/12)、長度乘 stretch（>1＝變慢，音高不變）。
    兒童組加（2026-10-21）：eleven_v3 不理會 speed，淨語速常比角色表快 1 字／秒以上，只能後處理放慢。"""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=SR)
    man = call(snd, "To Manipulation", 0.01, 60, 600)
    if st:
        tier = call(man, "Extract pitch tier")
        call(tier, "Multiply frequencies", snd.xmin, snd.xmax, 2 ** (st / 12))
        call([tier, man], "Replace pitch tier")
    if stretch != 1.0:
        dt = call("Create DurationTier", "stretch", snd.xmin, snd.xmax)
        call(dt, "Add point", snd.xmin, float(stretch))
        call([man, dt], "Replace duration tier")
    y = call(man, "Get resynthesis (overlap-add)").values[0].astype(np.float32)
    if stretch == 1.0:
        y = y[:len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))
    return y


def net_rate_arr(x: np.ndarray, text: str) -> float | None:
    """(d) 的淨語速算法用在母帶前的陣列：−40 dB 有聲區間扣掉 ≥200 ms 停頓（同 vo_lib.measure 的 rate_cps_net_r），
    字數＝漢字＋數字逐字（同 syllables）。"""
    db = V.frame_db(x)
    thr = db.max() - 40
    act = np.nonzero(db > thr)[0]
    if not len(act):
        return None
    pz, run = 0, 0
    for v in db[act[0]:act[-1] + 1]:
        if v <= thr:
            run += 1
        else:
            if run >= 20:
                pz += run
            run = 0
    span = (act[-1] + 1 - act[0] - pz) * 0.01
    return round(syllables(V.strip_breaks(text)) / max(0.1, span), 3)


def tail_check(raw: Path) -> dict:
    """同 review/G3/el/qa/配音導演/tail_voicing.py：ffmpeg 解成 48 kHz，最後 60 ms 的 RMS（相對 p90）與有聲比例。"""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(raw), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return tail_metrics(np.frombuffer(pcm, dtype=np.float32).astype(np.float64))


def _voiced_frames(x: np.ndarray, n: int) -> np.ndarray:
    """每個 frame_db 窗（10 ms 一格、中心 0.01·(i+1) 秒）是否有聲（parselmouth 自相關 60–600 Hz）。"""
    import parselmouth
    p = parselmouth.Sound(x.astype(np.float64), sampling_frequency=SR).to_pitch_ac(time_step=0.01, pitch_floor=60,
                                                                                    pitch_ceiling=600)
    f, tt = p.selected_array["frequency"], p.xs()
    if not len(tt):
        return np.zeros(n, dtype=bool)
    idx = np.clip(np.searchsorted(tt, 0.01 * (np.arange(n) + 1)), 0, len(tt) - 1)
    return f[idx] > 0


def char_times(x: np.ndarray) -> tuple[list[str], list[float], list[float]]:
    """large-v3-turbo 字詞時間戳攤成逐字（字詞內平均分配）；數字轉成國字（119→一一九）。"""
    hc, hs, he = [], [], []
    for w, s, e in word_times(x):
        t = V.PUNCT_RE.sub("", V._to_trad(w)).replace("119", "一一九").translate(V.DIGITS)
        if not t:
            continue
        d = (e - s) / len(t)
        for i, ch in enumerate(t):
            hc.append(ch)
            hs.append(s + i * d)
            he.append(s + (i + 1) * d)
    return hc, hs, he


def char_map(ref: str, hc: list[str]) -> dict[int, int]:
    """逐字對齊（difflib；等長的 replace 段一對一，容許同音字）：參考字索引 → 轉寫字索引。"""
    mp = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, "".join(hc), autojunk=False).get_opcodes():
        if op == "equal" or op == "replace":
            # 不等長的 replace（例如句尾「登結」對到「燈節嗯」）：前 min 個字一對一（2026-10-21 成人組修正：
            # 原本整段不對應，guard_cut 退回「最後一個對上的字」，把句尾「燈節」當成填充字切掉）
            for d in range(min(i2 - i1, j2 - j1)):
                mp[i1 + d] = j1 + d
    return mp


def guard_cut(x: np.ndarray, min_pause_ms: int = 300, main_text: str | None = None) -> tuple[np.ndarray | None, dict]:
    """句尾保護：送出文字在句尾加「……嗯。」，合成器的截斷就落在後面的填充字。切點：
    ① 用 large-v3-turbo 字詞時間戳找正文最後一字的結束 t_end 與填充字的開始 t_fill；在 [t_end − 150 ms, t_fill + 100 ms]
       （沒轉寫出填充字就到檔尾）裡取最早一段 ≥60 ms 的無聲低能量段（10 ms RMS 平滑後低於 p90 −12 dB、沒有 F0）；
    ② 對不上時，改取最後一段 ≥min_pause_ms 的無聲低能量段。
    在正文衰減到該段底噪（中位數 +3 dB）後再留最多 100 ms（離段尾至少 30 ms）處切掉，20 ms 淡出。
    找不到合適的段＝回傳 None（這次嘗試的 (c) 判不通過）；切得不對時 (a) 轉寫會看到殘留的「嗯」或漏字。"""
    db = V.frame_db(x)
    rel = db - np.percentile(db, 90)
    sm = np.convolve(rel, np.ones(5) / 5, mode="same")
    low = (sm < -12) & ~_voiced_frames(x, len(db))
    voiced_idx = np.nonzero(~low)[0]
    if not len(voiced_idx):
        return None, {"guard": "找不到語音"}
    runs, i = [], int(voiced_idx[0])
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if j - i >= 6 and i > len(low) * 0.15:
                runs.append((i, j))
            i = j
        else:
            i += 1
    info: dict = {}
    pick = None
    if main_text:
        ref = V.PUNCT_RE.sub("", main_text).replace("119", "一一九")
        hc, hs, he = char_times(x)
        mp = char_map(ref, hc)
        if mp:
            if len(ref) - 1 in mp:
                jl = mp[len(ref) - 1]
            else:   # 最後一字沒對上：從最後一個對上的字往後補足剩下的字數（不可退回最後對上的字，會切掉句尾）
                il = max(mp)
                jl = min(len(hc) - 1, mp[il] + (len(ref) - 1 - il))
            t_end = he[jl]
            t_fill = hs[jl + 1] if jl + 1 < len(hc) else None
            lo, hi = t_end - 0.15, (t_fill + 0.10) if t_fill is not None else len(x) / SR + 1
            # 2026-10-21 成人組修正：原本取「和 [t_end−150 ms, …] 重疊的第一段 ≥60 ms 低能量」，會選到句尾字裡的
            # 塞音／塞擦音閉塞段（「節」的 j、「蛋」的 d，80–150 ms），把最後一個字的韻母切掉。改成：段的起點要在
            # t_end−150 ms 之後（或本身 ≥300 ms 的長停頓），優先取第一段 ≥200 ms；沒有時才取起點在 t_end−50 ms 之後、
            # ≥100 ms、底噪低於 −25 dB 的段；都沒有＝句尾保護失敗（(c) 不通過、重算）。
            cand = [r for r in runs if r[0] / 100 < hi
                    and (r[0] / 100 >= lo or (r[1] - r[0] >= 30 and r[1] / 100 > lo + 0.15))]
            info.update({"how": "轉寫時間戳", "t_end_s": round(t_end, 3),
                         "t_fill_s": None if t_fill is None else round(t_fill, 3), "asr_tail": "".join(hc[jl + 1:])})
            long_ = [r for r in cand if r[1] - r[0] >= 20]
            short = [r for r in cand if r[1] - r[0] >= 10 and r[0] / 100 >= t_end - 0.05
                     and float(np.median(rel[r[0]:r[1]])) < -25]
            if long_:
                pick = long_[0]
            elif short:
                pick = short[0]
                info["pick_rule"] = "短停頓（100–200 ms、底噪 < −25 dB）"
            else:
                return None, dict(info, guard="正文和填充字之間沒有 ≥200 ms 的停頓（填充字黏在句尾）")
    if pick is None:
        need = max(1, min_pause_ms // 10)
        full = [r for r in runs if r[1] - r[0] >= need]
        endrun = [r for r in runs if r[1] >= len(low) and r[1] - r[0] >= need // 2]
        cands = full or endrun
        if not cands:
            return None, dict(info, guard=f"找不到 ≥{min_pause_ms} ms 的停頓（填充字沒有和正文分開）")
        pick = cands[-1]
        info.setdefault("how", "最後一段長停頓")
    a, b = pick
    floor = float(np.median(rel[a:b]))
    k = a
    while k < b and rel[k] > floor + 3:
        k += 1
    cf = max(k + 1, min(b - 3 if b < len(low) else b, k + 10))
    cut = min(len(x), cf * 480 + 480)
    y = V.fade_edges(x[:cut], fin_ms=0, fout_ms=20)
    return y, dict(info, guard="ok", pause_s=[round(a / 100, 2), round(b / 100, 2)], decay_end_s=round(k / 100 + 0.01, 2),
                   cut_s=round(cut / SR, 3), floor_rel_db=round(floor, 1), removed_s=round((len(x) - cut) / SR, 2))


def head_cut(x: np.ndarray, prefix: str, main_text: str) -> tuple[np.ndarray | None, dict]:
    """句首保護（兒童組加，2026-10-21）：eleven_v3 常把句首一兩個字念糊（「電子煙」→電視煙、「陳伯伯」→伯伯），送出文字前加
    prefix（預設「嗯。」）讓含糊落在填充字，再切掉。切點：large-v3-turbo 字詞時間戳找正文第一字的開始 t0；取第一個有聲段之後、
    結束時間不晚於 t0＋150 ms 的最後一段 ≥120 ms 無聲低能量段（同 guard_cut 的門檻）；t0 對不上時取第一段。在段尾前 30 ms 切開、
    10 ms 淡入。找不到＝None；切錯時 (a) 轉寫會看到殘留的「嗯」或漏字。"""
    db = V.frame_db(x)
    rel = db - np.percentile(db, 90)
    sm = np.convolve(rel, np.ones(5) / 5, mode="same")
    low = (sm < -12) & ~_voiced_frames(x, len(db))
    vi = np.nonzero(~low)[0]
    if not len(vi):
        return None, {"guard": "找不到語音"}
    runs, i = [], int(vi[0])
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            if j - i >= 12 and j < len(low):
                runs.append((i, j))
            i = j
        else:
            i += 1
    pre = V.PUNCT_RE.sub("", prefix)
    ref = pre + V.PUNCT_RE.sub("", main_text).replace("119", "一一九")
    hc, hs, he = char_times(x)
    mp = char_map(ref, hc)
    t0 = None
    for d in range(3):
        if len(pre) + d in mp:
            t0 = hs[mp[len(pre) + d]] - 0.15 * d
            break
    info = {"t0_s": None if t0 is None else round(t0, 3), "asr_head": "".join(hc[:4])}
    cand = [r for r in runs if t0 is None or r[1] / 100 <= t0 + 0.15]
    if cand and t0 is not None:
        a, b = cand[-1]
        info["how"] = "轉寫時間戳"
    else:   # 時間戳對不上或太早（轉寫器常把第一字的開始標在填充字上）：取 1.5 秒內的第一段停頓
        cand = [r for r in runs if r[0] / 100 < 1.5]
        if not cand:
            return None, dict(info, guard="填充字和正文之間沒有 ≥120 ms 的停頓")
        a, b = cand[0]
        info["how"] = "第一段停頓"
    cut = max(0, b * 480 - int(0.03 * SR))
    y = x[cut:].astype(np.float32).copy()
    y = V.fade_edges(y, fin_ms=10, fout_ms=0)
    return y, dict(info, guard="ok", pause_s=[round(a / 100, 2), round(b / 100, 2)], cut_s=round(cut / SR, 3))


def word_times(x: np.ndarray) -> list[tuple[str, float, float]]:
    """large-v3-turbo 字詞時間戳（faster-whisper word_timestamps）。"""
    from faster_whisper import WhisperModel
    name = "large-v3-turbo"
    if name not in V._WHISPERS:
        V._WHISPERS[name] = WhisperModel(name, device="cpu", compute_type="int8")
    a16 = V.resample(x.astype(np.float32), SR, 16000)
    segs, _ = V._WHISPERS[name].transcribe(a16, language="zh", beam_size=5, word_timestamps=True,
                                           initial_prompt="以下是繁體中文的台灣華語。")
    return [(w.word, float(w.start), float(w.end)) for s in segs for w in (s.words or [])]


def insert_boundaries(x: np.ndarray, parts: list[str], gaps_ms: list[int]) -> tuple[np.ndarray, list, list]:
    """post 模式：整句一次合成後，在句界插入靜音。句界時間＝轉寫時間戳裡「前一句最後一字的結束」到「下一句第一字的開始」
    （對不上時改用字數比例），前後各放寬 120 ms，取 30 ms 平滑能量最低點切開（10 ms 淡出／淡入），
    原有停頓（−35 dB）不足 gap 的部分補靜音。最低點高於 p90 −20 dB＝句界不乾淨，(e) 判不通過。"""
    hc, hs, he = char_times(x)
    seq = [V.PUNCT_RE.sub("", p).replace("119", "一一九") for p in parts]
    ref = "".join(seq)
    mp = char_map(ref, hc)
    db = V.frame_db(x)
    rel = db - np.percentile(db, 90)
    sm = np.convolve(rel, np.ones(3) / 3, mode="same")
    thr = db.max() - 35
    s0, e0 = V.speech_bounds(x)
    dur = (e0 - s0) / SR
    chunks, gaps, info = [], [], []
    last, pos, K = 0, 0, 0
    ramp = int(0.010 * SR)
    for k in range(len(seq) - 1):
        K += len(seq[k])
        a, b = mp.get(K - 1), mp.get(K)
        if a is not None and b is not None:
            t0, t1, how = he[a], hs[b], "轉寫時間戳"
        else:
            t0 = t1 = s0 / SR + K / max(1, len(ref)) * dur
            how = "字數比例（時間戳對不上）"
        lo, hi = min(t0, t1) - 0.12, max(t0, t1) + 0.12
        f0, f1 = max(int(lo * 100), last // 480 + 2), min(len(sm) - 2, int(hi * 100))
        if f1 <= f0:
            f0, f1 = last // 480 + 2, min(len(sm) - 2, last // 480 + 40)
        fm = f0 + int(np.argmin(sm[f0:f1 + 1]))
        c = fm * 480 + 480
        exist = 0
        if db[fm] < thr:
            i = j = fm
            while i > 0 and db[i - 1] < thr:
                i -= 1
            while j + 1 < len(db) and db[j + 1] < thr:
                j += 1
            exist = (j - i + 1) * 10
        ins = max(0, int(gaps_ms[k]) - exist)
        seg = x[last:c].astype(np.float32).copy()
        if last > 0:
            seg[:ramp] *= V._cos_ramp(min(ramp, len(seg)), True)[:len(seg[:ramp])]
        seg[-ramp:] *= V._cos_ramp(min(ramp, len(seg)), False)[-len(seg[-ramp:]):]
        chunks.append(seg)
        pos += len(seg)
        z = int(ins / 1000 * SR)
        gaps.append((pos, pos + z, int(gaps_ms[k])))
        chunks.append(np.zeros(z, dtype=np.float32))
        pos += z
        last = c
        info.append({"boundary": k + 1, "how": how, "t_est_s": [round(t0, 3), round(t1, 3)], "cut_s": round(c / SR, 3),
                     "depth_rel_db": round(float(sm[fm]), 1), "existing_pause_ms": exist, "inserted_ms": ins,
                     "clean": bool(sm[fm] < -20)})
    seg = x[last:].astype(np.float32).copy()
    if last > 0:
        seg[:ramp] *= V._cos_ramp(min(ramp, len(seg)), True)[:len(seg[:ramp])]
    chunks.append(seg)
    return np.concatenate(chunks).astype(np.float32), gaps, info


def tail_metrics(x: np.ndarray) -> dict:
    """tail_check 的計算本體（48 kHz 陣列）。"""
    import parselmouth
    x = x.astype(np.float64)
    w = 960
    fr = x[:len(x) // w * w].reshape(-1, w)
    r = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    ref = np.percentile(r, 90)
    p = parselmouth.Sound(x, 48000).to_pitch_ac(time_step=0.01, pitch_floor=60, pitch_ceiling=600)
    f, t = p.selected_array["frequency"], p.xs()
    dur = len(x) / 48000
    tv = float(np.mean(f[t > dur - 0.06] > 0)) if np.any(t > dur - 0.06) else None
    rd = round(float(np.mean(r[-3:] - ref)), 1)
    return {"last60ms_rel_dB": rd, "last60ms_voiced": None if tv is None else round(tv, 2),
            "truncated": bool(rd > -25 and (tv or 0) > 0.3)}


def boundary_pauses(y: np.ndarray, x_pre: np.ndarray, gaps: list[tuple[int, int, int]]) -> list[int]:
    """每個插入停頓在母帶檔中的實際靜音長度（ms）：10 ms RMS 低於最大值 −35 dB 的連續段（同 vo_lib.measure 的停頓門檻）。
    時間對應依 vo_lib.trim_pad：輸出索引＝頭段長度＋（原索引 − 語音起點前 10 ms）。"""
    s, _ = V.speech_bounds(x_pre)
    a = max(0, s - 480)
    head = int(D["head_ms"] / 1000 * SR) - (s - a)
    db = V.frame_db(y)
    thr = db.max() - 35
    out = []
    for g0, g1, _ in gaps:
        c = (g0 + g1) // 2 - a + head
        fc = min(len(db) - 1, max(0, (c - 480) // 480))
        if db[fc] >= thr:
            out.append(0)
            continue
        i = j = fc
        while i > 0 and db[i - 1] < thr:
            i -= 1
        while j + 1 < len(db) and db[j + 1] < thr:
            j += 1
        out.append((j - i + 1) * 10)
    return out


# ---------------------------------------------------------------- 轉寫比對
def align(ref_text: str, hyp: str) -> tuple[str, str, list[tuple[int, int, int, int]]]:
    """與 vo_lib.compare 相同的前處理與逐字對齊，回傳非 equal 段的位置（順序與 compare 的 diffs 一一對應）。"""
    ref_cmp = V.PUNCT_RE.sub("", ref_text).replace("119", "一一九")
    hyp_cmp = V.PUNCT_RE.sub("", V._to_trad(hyp)).replace("119", "一一九").translate(V.DIGITS)
    sm = difflib.SequenceMatcher(None, ref_cmp, hyp_cmp, autojunk=False)
    return ref_cmp, hyp_cmp, [(i1, i2, j1, j2) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]


def check_words(text: str, ref_cmp: str, hyp_cmp: str, diffs: list[dict]) -> list[dict]:
    """讀音檢查詞狀態，判定邏輯同 vo_lib.compare（轉寫一致 → 檢查詞範圍內差異都是同音字 → 拼音比對）。"""
    out = []
    ph_all = " ".join(V._pinyin(hyp_cmp))
    for w in CHECK_WORDS:
        if w not in text:
            continue
        wc = w.replace("119", "一一九")
        if wc in hyp_cmp:
            st = "轉寫一致"
        else:
            spans = [(k, k + len(wc)) for k in range(len(ref_cmp)) if ref_cmp.startswith(wc, k)]
            over = [d for d in diffs if "span" in d for a, b in spans if d["span"][0] < b and d["span"][1] > a]
            if spans and over and all(d["kind"] == HOMO for d in over):
                st = "同音轉寫（讀音一致）"
            else:
                syn_w = V.apply_pronounce(w, PRON, "global")
                st = "同音轉寫（讀音一致）" if " ".join(V._pinyin(syn_w)) in ph_all else "不一致（需複查）"
        out.append({"word": w, "status": st})
    return out


def asr_eval(wav: Path, text: str, reading: str) -> dict:
    res = {}
    for mname in V.ASR_MODELS:
        hyp = V.transcribe([wav], mname)[str(wav)]
        c = V.compare(text, reading, hyp)
        ref_cmp, hyp_cmp, spans = align(text, hyp)
        diffs = c["diffs"]
        if len(spans) == len(diffs):
            for d, sp in zip(diffs, spans):
                d["span"] = [sp[0], sp[1]]
        res[mname] = {"hyp": hyp, "hyp_trad": c["hyp_trad"], "cer": c["cer"], "per": c["per"], "diffs": diffs,
                      "words": check_words(text, ref_cmp, hyp_cmp, diffs)}
    return res


def same_sound(h1: str, h2: str) -> bool:
    return h1 == h2 or (bool(h1) and bool(h2) and V._pinyin(h1) == V._pinyin(h2))


def check_a(asr: dict, text: str, base_asr: dict | None, allow_names: bool) -> dict:
    ref_cmp = V.PUNCT_RE.sub("", text).replace("119", "一一九")
    nspans = [(k, k + len(n), n) for n in NAMES for k in range(len(ref_cmp)) if ref_cmp.startswith(n, k)]
    models, ok, nbad = {}, True, 0
    for mname, r in asr.items():
        bad, exc = [], []
        for d in r["diffs"]:
            if d["kind"] == HOMO:
                continue
            ex = None
            if allow_names and base_asr and "span" in d and d["span"][1] > d["span"][0]:
                for a, b, n in nspans:
                    if a <= d["span"][0] and d["span"][1] <= b:
                        for e in base_asr.get(mname, {}).get("diffs", []):
                            if (e["kind"] != HOMO and "span" in e and e["span"][0] < b and e["span"][1] > a
                                    and same_sound(e["hyp"], d["hyp"])):
                                ex = {"name": n, "edge_hyp": e["hyp"]}
                                break
                    if ex:
                        break
            (exc if ex else bad).append({k: v for k, v in d.items()} | ({"excuse": ex} if ex else {}))
        models[mname] = {"bad": bad, "excused_names": exc}
        ok = ok and not bad
        nbad += len(bad)
    return {"pass": ok, "n_bad": nbad, "models": models,
            "rule": "兩個模型都只能有同音字" + ("；人名在 edge 基準同句同模型有同音轉寫差異者豁免" if allow_names else "")}


def check_b(asr: dict) -> dict:
    words: dict[str, dict] = {}
    for mname, r in asr.items():
        for w in r["words"]:
            words.setdefault(w["word"], {})[mname] = w["status"]
    bad = [w for w, s in words.items() if any(v not in W_OK for v in s.values())]
    return {"pass": not bad, "words": words, "inconsistent": bad, "applicable": bool(words)}


def evaluate(wav: Path, ln: dict, targets: dict, tails: list[dict], pauses_b: list[int] | None, n_sent: int,
             asr: dict, base_asr: dict | None, allow_names: bool, loud_offset: float,
             boundaries: list | None = None) -> tuple[dict, dict]:
    """(a)–(f) 全部檢查；回傳 (checks, 量測摘要)。pauses_b＝已知句界的停頓（EL 分段）；None＝用最長的 n−1 個停頓（edge 基準）。"""
    m = V.measure(wav, ln["text"])
    required = ln["id"] in REQUIRED
    ch = {"a": check_a(asr, ln["text"], base_asr, allow_names and not required), "b": check_b(asr)}
    trunc = [t for t in tails if t["truncated"]]
    ch["c"] = {"pass": not trunc, "segments": tails, "truncated": len(trunc), "rule": "最後 60 ms > −25 dB 且有聲 > 30% ＝截斷"}
    n_syl = syllables(ln["text"])
    n_cjk = len(re.findall(r"[一-鿿]", ln["text"]))
    rng = targets["rate_range"]
    if n_syl >= MIN_SYLL_FOR_RATE and m.get("rate_cps_net_r") and n_cjk:
        net = round(n_syl / (n_cjk / m["rate_cps_net_r"]), 2)
        ch["d"] = {"pass": rng[0] <= net <= rng[1], "value": net, "range": rng, "syllables": n_syl, "applicable": True}
    else:
        ch["d"] = {"pass": True, "value": None, "range": rng, "syllables": n_syl, "applicable": False,
                   "note": f"少於 {MIN_SYLL_FOR_RATE} 音節，不判定"}
    thr = REQUIRED_GAP_MS if required else MIN_GAP_MS
    if n_sent > 1:
        if pauses_b is None:
            ps = sorted(m["pauses_ms"], reverse=True)[:n_sent - 1]
            ps = ps + [0] * (n_sent - 1 - len(ps))
            how = "最長的 n−1 個停頓（edge 基準沒有句界位置）"
        else:
            ps, how = pauses_b, "已知句界（分段合成插入的停頓）"
        unclean = [b["boundary"] for b in (boundaries or []) if not b["clean"]]
        ch["e"] = {"pass": all(p >= thr for p in ps) and not unclean, "pauses_ms": ps, "threshold_ms": thr, "method": how,
                   "applicable": True}
        if boundaries:
            ch["e"]["method"] = "整句合成後依轉寫時間戳插入（insert_boundaries）"
            ch["e"]["boundaries"] = boundaries
            ch["e"]["unclean"] = unclean
    else:
        ch["e"] = {"pass": True, "pauses_ms": [], "threshold_ms": thr, "applicable": False, "note": "單句"}
    tgt = D["target_lufs"] + loud_offset
    lu, tp, cl = m["integrated_lufs"], m["true_peak_dbtp"], m["clipped_samples"]
    ch["f"] = {"pass": lu is not None and abs(lu - tgt) <= 0.5 and tp is not None and tp <= D["true_peak_max"] and cl == 0,
               "lufs": lu, "target_lufs": tgt, "true_peak_dbtp": tp, "clipped": cl}
    f0 = m.get("f0_median")
    summ = {k: m.get(k) for k in ("file", "seconds", "speech_seconds", "integrated_lufs", "true_peak_dbtp", "clipped_samples",
                                  "rate_cps", "rate_cps_net", "rate_cps_net_r", "pauses_ms", "pauses_ms_r", "f0_median",
                                  "f0_p10", "f0_p90", "pause_spikes", "head_silence_ms", "tail_silence_ms")}
    summ["rate_net_syll"] = ch["d"]["value"]
    summ["f0_in_range"] = None if f0 is None else bool(targets["f0_range"][0] <= f0 <= targets["f0_range"][1])
    return ch, summ


def score(ch: dict) -> tuple[list[str], int, float]:
    failed = [k for k in "abcdef" if not ch[k]["pass"]]
    d = ch["d"]
    dev = 0.0
    if d.get("applicable") and not d["pass"]:
        dev = min(abs(d["value"] - d["range"][0]), abs(d["value"] - d["range"][1]))
    detail = (ch["a"]["n_bad"] + len(ch["b"]["inconsistent"]) + ch["c"]["truncated"] + dev
              + sum(1 for p in ch["e"]["pauses_ms"] if p < ch["e"]["threshold_ms"]) + (0 if ch["f"]["pass"] else 1))
    return failed, len(failed), round(detail, 3)


# ---------------------------------------------------------------- edge 基準
_orig_cache_path = V._cache_path
_orig_synth_raw = V.synth_raw
_EDGE_REC: list = []


def _cache_path_ro(spec: dict, text: str, ext: str) -> Path:
    p = _orig_cache_path(spec, text, ext)        # audio/vo/_raw 已有的快取：只讀沿用
    return p if p.exists() else EDGE_RAW / p.name  # 新合成的放 review/G3/el/full/edge/_raw/


def _synth_rec(spec: dict, text: str, purpose: str = "", force: bool = False):
    if spec.get("service") != "edge":
        raise RuntimeError("edge 基準只允許 edge-tts（不呼叫 ElevenLabs）")
    p, info = _orig_synth_raw(spec, text, purpose, force)
    _EDGE_REC.append({"raw": p, "text": text})
    return p, info


def edge_signature(lid: str) -> str:
    ln = LINES[lid]
    rs = {r: {k: CAST["roles"][r].get(k) for k in ("spec", "overrides", "post", "loudness_offset_db")} for r in roles_of(ln)}
    return sha({"tool": TOOL_VERSION, "text": ln["text"], "roles": rs, "pron": PRON, "defaults": D})


def loud_offset_edge(lid: str) -> float:
    off = 0.0
    for r in roles_of(LINES[lid]):
        off = CAST["roles"][r].get("loudness_offset_db", {}).get(lid, off)
    return off


def baseline_line(lid: str, force: bool = False) -> dict:
    ln = LINES[lid]
    sig = edge_signature(lid)
    allm = jload(EDGE_METRICS, {})
    old = allm.get(lid)
    wav = EDGE / f"vo_{lid}_edge.wav"
    if old and old.get("signature") == sig and wav.exists() and not force:
        return old
    EDGE_RAW.mkdir(parents=True, exist_ok=True)
    _EDGE_REC.clear()
    V._cache_path, V.synth_raw = _cache_path_ro, _synth_rec
    try:
        x, notes = B.render_line(ln, CAST, PRON, None, False, f"{PURPOSE} edge 基準")
    finally:
        V._cache_path, V.synth_raw = _orig_cache_path, _orig_synth_raw
    raws = [dict(r) for r in _EDGE_REC]
    y, minfo = V.master(x, target=D["target_lufs"], tp_max=D["true_peak_max"], head_ms=D["head_ms"], tail_ms=D["tail_ms"],
                        short_s=D.get("short_line_s", 3.0))
    off = loud_offset_edge(lid)
    if off:
        y = (y * 10 ** (off / 20)).astype(np.float32)
    V.write_wav(wav, y)
    tails = []
    for r in raws:
        t = tail_check(r["raw"])
        tails.append(dict(t, raw=rel(r["raw"]), text=r["text"]))
    code = ROLE2CODE.get(roles_of(ln)[0])
    targets = line_targets(code, lid, None)
    asr = asr_eval(wav, ln["text"], V.strip_breaks(notes["specs"][0]["synth_text"]))
    ch, summ = evaluate(wav, ln, targets, tails, None, n_sentences(ln["text"]), asr, None, False, off)
    failed, n, det = score(ch)
    ent = {"id": lid, "role": ln["role"], "codes": [ROLE2CODE.get(r) for r in roles_of(ln)], "text": ln["text"],
           "signature": sig, "file": rel(wav), "time": now(), "engine": "edge",
           "spec": notes["specs"], "targets": targets, "metrics": summ, "asr": asr, "checks": ch, "failed": failed,
           "problems": n, "detail_score": det, "loudness_offset_db": off,
           "master": {k: minfo.get(k) for k in ("speech_start", "speech_end", "method", "I", "TP", "limited")}}
    merge_save(EDGE_METRICS, lid, ent)
    return ent


def run_baseline(ids: list[str], args) -> None:
    print(f"edge 基準：{len(ids)} 句（免費、不重算）→ {rel(EDGE)}")
    if args.dry_run:
        for lid in ids:
            print(" ", lid, LINES[lid]["role"], LINES[lid]["text"])
        return
    for n, lid in enumerate(ids, 1):
        try:
            e = baseline_line(lid, args.force)
            print(f"[{n}/{len(ids)}] {lid} {e['role']} 未通過：{','.join(e['failed']) or '無'}  "
                  f"淨語速 {e['checks']['d']['value']}  F0 {e['metrics']['f0_median']}  "
                  + "｜".join(f"{k}：{v['hyp_trad']}" for k, v in e["asr"].items()))
        except Exception as ex:  # noqa: BLE001
            print(f"[{n}/{len(ids)}] {lid} edge 基準失敗：{ex}")


# ---------------------------------------------------------------- EL 逐句
def el_signature(lid: str, cfgs: list[dict]) -> str:
    cs = []
    for c in cfgs:
        d = {k: v for k, v in c.items()       # 只算會影響合成或判定的欄位（說明、備註、來源不算）
             if not k.startswith("_") and k not in ("lines", "source", "status") and not k.endswith("note")}
        d["adaptive_speed"] = {kk: vv for kk, vv in (c.get("adaptive_speed") or {}).items() if kk != "note"}
        d["line"] = {kk: vv for kk, vv in (c.get("lines", {}).get(lid) or {}).items() if kk != "note"} or None
        cs.append(d)
    return sha({"tool": TOOL_VERSION, "text": LINES[lid]["text"], "required": lid in REQUIRED, "pron": PRON, "cast": cs,
                "defaults": D})


def adapt_speed(cfg: dict, base, prev: list[dict]):
    ad = cfg.get("adaptive_speed") or {}
    if base is None or not prev:
        return base
    sp = prev[-1]["settings"].get(cfg["code"], {}).get("speed", base)
    if ad.get("enabled"):
        d = prev[-1]["checks"]["d"]
        if d.get("applicable") and not d["pass"]:
            sp = sp - ad.get("step", 0.03) if d["value"] > d["range"][1] else sp + ad.get("step", 0.03)
        sp = min(ad.get("max", 1.1), max(ad.get("min", 0.85), sp))
    return round(sp, 3)


def prev_truncations(prev: list[dict], code: str, i: int) -> int:
    return sum(1 for a in prev for s in a["segments"] if s["role"] == code and s["i"] == i and s["tail"]["truncated"])


def render_attempt(lid: str, ln: dict, cfgs: list[dict], k: int, prev: list[dict], run: dict):
    """合成一次嘗試（含合唱、分段或整句、句尾保護、插入停頓、後處理），回傳母帶前的 48 kHz 訊號與紀錄。

    segment_mode＝synth（預設，依任務規格）：依句號／問號／驚嘆號與 [[break:N]] 分段各自合成，段間插入停頓。
    segment_mode＝post：整句一次合成（eleven_v3 分段合成時語速明顯變快），再依轉寫時間戳在句界插入停頓（insert_boundaries）。
    tail_guard.mode＝always／on_fail（該段截斷過一次後才用）／off：句尾加 suffix，合成後在長停頓處切掉（guard_cut）；
    off 時沿用舊法：同一段截斷 2 次以上，下一次句尾補「……」。"""
    required = lid in REQUIRED
    mixes, segrecs, settings_by, seeds, gaps0, bnd0 = [], [], {}, {}, [], None
    for ri, cfg in enumerate(cfgs):
        lc = cfg.get("lines", {}).get(lid, {})
        st = dict(cfg["settings"], **lc.get("settings", {}))
        st["speed"] = adapt_speed(cfg, st.get("speed"), prev)
        settings_by[cfg["code"]] = st
        seed = int(lc.get("seed_base", cfg["seed_base"])) + k   # 逐句 seed_base（2026-10-22 加：重做時第 1 次沿用原採用的 seed）
        seeds[cfg["code"]] = seed
        gap = REQUIRED_INSERT_MS if required else int(lc.get("sentence_gap_ms", cfg.get("sentence_gap_ms", 450)))
        segs = plan_segments(synth_text_for(cfg, lid, ln["text"]), gap)
        post = deep_merge(cfg.get("post", {}), lc.get("post", {}))
        smode = lc.get("segment_mode", cfg.get("segment_mode", "synth"))
        tg = deep_merge(cfg.get("tail_guard", {"mode": "off"}), lc.get("tail_guard", {}))
        hg = deep_merge(cfg.get("head_guard", {"mode": "off"}), lc.get("head_guard", {}))   # 句首保護（兒童組加）
        if smode == "post" and len(segs) > 1:
            units = [("".join(p for p, _ in segs), None)]
            b_parts = [p for p, _ in segs]
            b_gaps = [max(MIN_GAP_MS, int(g or 0)) if not required else REQUIRED_INSERT_MS for _, g in segs[:-1]]
        else:
            units, b_parts, b_gaps = segs, None, None
        chunks, gaps, pos = [], [], 0
        for i, (part, g) in enumerate(units):
            ntr = prev_truncations(prev, cfg["code"], i)
            use_guard = tg.get("mode") == "always" or (tg.get("mode") == "on_fail" and ntr >= 1)
            legacy = tg.get("mode", "off") == "off" and ntr >= 2
            suffix = tg.get("suffix", "……嗯。") if use_guard else (TAIL_SUFFIX if legacy else "")
            prefix = hg.get("prefix", "嗯。") if hg.get("mode") == "always" and i == 0 else ""
            sent = prefix + part + suffix
            raw, info = el_call(cfg, sent, seed, st, lid, k, i, run)
            tail_raw = tail_check(raw)
            x = V.decode(raw)
            ginfo, hinfo = None, None
            if use_guard:
                y, ginfo = guard_cut(x, int(tg.get("min_pause_ms", 300)), V.strip_breaks(part))
                if y is None:
                    tail = dict(tail_raw, truncated=True, note="句尾保護失敗：" + ginfo["guard"])
                else:
                    x = y
                    tail = dict(tail_metrics(x), where="切點前 60 ms（句尾保護）")
            else:
                tail = dict(tail_raw, where="原始檔最後 60 ms")
            if prefix:
                y, hinfo = head_cut(x, prefix, V.strip_breaks(part))
                if y is None:   # 句首填充字切不掉＝這次嘗試判 (c) 不通過、重算
                    tail = dict(tail, truncated=True, note=(tail.get("note", "") + "；句首保護失敗：" + hinfo["guard"]).lstrip("；"))
                else:
                    x = y
            x, clicks = V.declick(x)
            if len(units) > 1:
                a, b = V.speech_bounds(x)
                x = V.fade_edges(x[max(0, a - 480):min(len(x), b + int(0.08 * SR))], fin_ms=10, fout_ms=20)
            rec = {"role": cfg["code"], "i": i, "text": part, "sent": sent, "segment_mode": smode,
                   "tail_guard": suffix if use_guard else None, "tail_fix": TAIL_SUFFIX if legacy else None,
                   "gap_after_ms": g if i < len(units) - 1 else None, "raw": rel(raw), "request_id": info.get("request_id"),
                   "billed": info.get("billed"), "billed_source": info.get("billed_source"), "cached": info.get("cached"),
                   "seed": seed, "tail": tail, "tail_raw_end": tail_raw, "guard": ginfo, "declicked": len(clicks),
                   "head_guard": prefix or None, "head": hinfo}
            if post.get("max_pause_ms"):
                x, cut = V.cap_pauses(x, int(post["max_pause_ms"]))
                rec["pause_caps"] = cut
            if post.get("contour") and post["contour"].get("segment") == i:
                x, rec["contour"] = V.apply_contour(x, post["contour"]["points"])
            chunks.append(x)
            pos += len(x)
            if g and i < len(units) - 1:
                z = int(g / 1000 * SR)
                gaps.append((pos, pos + z, g))
                chunks.append(np.zeros(z, dtype=np.float32))
                pos += z
            segrecs.append(rec)
        x = np.concatenate(chunks).astype(np.float32)
        bnd = None
        if b_parts:
            x, gaps, bnd = insert_boundaries(x, b_parts, b_gaps)
            segrecs[-1]["boundaries"] = bnd
        if post.get("telephone"):
            x = telephone(x)
        # PSOLA 改調／放慢（兒童組加）：post.pitch_shift_st＝整段改調半音；post.stretch＝固定長度倍數；
        # post.auto_stretch＝{target（省略＝該句角色表語速中點）, tolerance（預設 0.2）, min, max, default（少於 6 音節的句子用）}：
        # 母帶前淨語速落在角色表語速 ±tolerance 內就不處理；超出才把倍數設成 淨語速÷target，夾在 min–max；差不到 2% 不處理。
        st_shift = float(post.get("pitch_shift_st") or 0.0)
        stretch, r0, tgt = float(post.get("stretch") or 1.0), None, None
        auto = post.get("auto_stretch")
        if auto and auto.get("enabled", True):
            tt = line_targets(cfg["code"], lid, cfg)
            lo, hi = tt["rate_nominal"]
            tol = float(auto.get("tolerance", 0.2))
            tgt = float(auto.get("target") or round((lo + hi) / 2, 3))
            r0 = net_rate_arr(x, ln["text"]) if syllables(ln["text"]) >= MIN_SYLL_FOR_RATE else None
            if r0:
                stretch = 1.0 if lo - tol <= r0 <= hi + tol else r0 / tgt
            else:
                stretch = float(auto.get("default", 1.0))
            stretch = min(float(auto.get("max", 1.3)), max(float(auto.get("min", 1.0)), stretch))
            stretch = 1.0 if abs(stretch - 1.0) < 0.02 else round(stretch, 3)
        if st_shift or stretch != 1.0:
            x_in = x
            x = psola_mod(x_in, st_shift, stretch)
            if r0 and stretch != 1.0:
                # 放慢會把 150–199 ms 的短停頓拉到 ≥200 ms（(d) 會扣掉），實際淨語速比 r0÷倍數 快：再量一次修正（最多 3 次）
                for _ in range(3):
                    r1 = net_rate_arr(x, ln["text"])
                    if not r1 or abs(r1 / tgt - 1) < 0.015:
                        break
                    s2 = min(float(auto.get("max", 1.3)), max(float(auto.get("min", 1.0)), round(stretch * r1 / tgt, 3)))
                    if abs(s2 - stretch) < 0.01:
                        break
                    stretch = s2
                    x = psola_mod(x_in, st_shift, stretch)
            if gaps and stretch != 1.0:
                gaps = [(int(a * stretch), int(b * stretch), g) for a, b, g in gaps]
            segrecs[-1]["psola"] = {"pitch_shift_st": st_shift, "stretch": stretch, "rate_before": r0, "target": tgt}
        mixes.append(x)
        if ri == 0:
            gaps0, bnd0 = gaps, bnd
    if len(mixes) > 1:   # 合唱：同 vo_build.render_line（各自合成與後處理 → 補齊長度相加 × √(1/n)）
        n = max(len(m) for m in mixes)
        x = (sum(np.pad(m, (0, n - len(m))) for m in mixes) * (1 / len(mixes)) ** 0.5).astype(np.float32)
        gaps0, bnd0 = None, None
    else:
        x = mixes[0]
    return x, segrecs, settings_by, seeds, gaps0, bnd0


def drop_outputs(lid: str, timings: dict) -> None:
    for f in (OUT / f"vo_{lid}_{VER}.wav", LIP / f"{lid}_{VER}.json"):
        if f.exists():
            f.unlink()
    timings.pop(lid, None)
    merge_save(TIMINGS, lid, None)


def run_line(lid: str, args, run: dict, report: dict, timings: dict) -> str:
    ln = LINES[lid]
    codes = [ROLE2CODE.get(r) for r in roles_of(ln)]
    cfgs = [load_cast(c) for c in codes]
    if any(c is None for c in cfgs):
        miss = [c for c, g in zip(codes, cfgs) if g is None]
        print(f"{lid} 略過：{'、'.join(miss)} 沒有 EL 角色設定")
        return "skipped"
    required = lid in REQUIRED
    sig = el_signature(lid, cfgs)
    max_att = max(1, min(args.max_attempts, MAX_ATTEMPTS_CAP))
    old = report.get(lid)
    final = OUT / f"vo_{lid}_{VER}.wav"
    attempts: list[dict] = []
    if old and old.get("signature") == sig and not args.force:
        if old["status"] == "pass" and final.exists():
            print(f"{lid} 沿用（已通過，設定未變）")
            return "reused"
        if old["status"] == "fail" and final.exists() and len(old["attempts"]) >= max_att:
            print(f"{lid} 沿用（已用滿 {len(old['attempts'])} 次仍未通過，設定未變）")
            return "reused"
        attempts = old.get("attempts", [])
    # 兒童組加：未通過的句子調參數重算時（逐句設定改變＝簽章不同），前一輪的嘗試保留在 previous_rounds，嘗試檔改名 r<n>_a<k>.wav
    prev_rounds = list((old or {}).get("previous_rounds", []))
    if old and old.get("signature") != sig and old.get("attempts") and not args.force:
        prev_rounds.append({k: old.get(k) for k in ("signature", "status", "chosen", "failed", "cast", "attempts",
                                                    "billed_total", "targets")})
    att_prefix = f"r{len(prev_rounds) + 1}_" if prev_rounds else ""
    base = jload(EDGE_METRICS, {}).get(lid)
    if not base or (base.get("signature") != edge_signature(lid) and not getattr(args, "reuse_edge_baseline", False)):
        try:
            base = baseline_line(lid)
        except Exception as ex:  # noqa: BLE001
            print(f"  edge 基準失敗（人名豁免停用）：{ex}")
            base = None
    base_asr = base.get("asr") if base else None
    targets = line_targets(codes[0], lid, cfgs[0])
    loud_off = float(cfgs[0].get("lines", {}).get(lid, {}).get("loudness_offset_db", 0.0))
    reading = reading_of(ln["text"], lid)
    entry = {"id": lid, "role": ln["role"], "codes": codes, "text": ln["text"], "required": required, "signature": sig,
             "status": "incomplete", "max_attempts": max_att, "targets": targets, "attempts": attempts,
             "cast": [{k: c.get(k) for k in ("voice_id", "voice_name", "model", "language_code", "settings", "seed_base",
                                             "sentence_gap_ms", "text_mode", "text_subs", "post")} for c in cfgs]}
    if prev_rounds:
        entry["previous_rounds"] = prev_rounds
    stop = None
    for k in range(len(attempts), max_att):
        try:
            x, segrecs, settings_by, seeds, gaps, bnd = render_attempt(lid, ln, cfgs, k, attempts, run)
        except (BudgetStop, ApiStop) as ex:
            stop = ex
            break
        y, minfo = V.master(x, target=D["target_lufs"], tp_max=D["true_peak_max"], head_ms=D["head_ms"],
                            tail_ms=D["tail_ms"], short_s=D.get("short_line_s", 3.0))
        if loud_off:
            y = (y * 10 ** (loud_off / 20)).astype(np.float32)
        wav = ATT / lid / f"{att_prefix}a{k + 1}.wav"
        V.write_wav(wav, y)
        pb = boundary_pauses(y, x, gaps) if gaps is not None else None
        n_sent = (len(gaps) + 1) if gaps is not None else n_sentences(ln["text"])
        asr = asr_eval(wav, ln["text"], reading)
        ch, summ = evaluate(wav, ln, targets, [s["tail"] for s in segrecs], pb, n_sent, asr, base_asr, True, loud_off, bnd)
        failed, n, det = score(ch)
        att = {"k": k + 1, "time": now(), "seeds": seeds, "settings": settings_by, "segments": segrecs, "wav": rel(wav),
               "master": {kk: minfo.get(kk) for kk in ("speech_start", "speech_end", "method", "I", "TP", "limited",
                                                       "raw_head_silence_ms", "raw_tail_silence_ms")},
               "metrics": summ, "asr": {m: {kk: v[kk] for kk in ("hyp_trad", "cer", "per", "diffs", "words")} for m, v in asr.items()},
               "checks": ch, "failed": failed, "problems": n, "detail_score": det,
               "billed": sum(s["billed"] or 0 for s in segrecs),            # 原始檔的實際計費（快取沿用時是當初的計費）
               "billed_new": sum(s["billed"] or 0 for s in segrecs if not s["cached"]),   # 本次執行新呼叫的計費
               "mitigations": [f"段{s['i'] + 1}句尾補「{s['tail_fix']}」" for s in segrecs if s["tail_fix"]]
               + [f"段{s['i'] + 1}句尾保護（送出加「{s['tail_guard']}」，在 {s['guard'].get('cut_s')} 秒處切掉 {s['guard'].get('removed_s')} 秒）"
                  if s["guard"] and s["guard"].get("guard") == "ok" else f"段{s['i'] + 1}句尾保護失敗"
                  for s in segrecs if s["tail_guard"]]
               + [f"句首保護（送出加「{s['head_guard']}」，在 {s['head'].get('cut_s')} 秒處切掉）"
                  for s in segrecs if s.get("head_guard") and s.get("head") and s["head"].get("guard") == "ok"]
               + [f"PSOLA 改調 {s['psola']['pitch_shift_st']} 半音、長度 ×{s['psola']['stretch']}"
                  + (f"（母帶前淨語速 {s['psola']['rate_before']} → 目標 {s['psola']['target']}）" if s['psola'].get('rate_before') else "")
                  for s in segrecs if s.get("psola")]
               + ["整句合成＋依轉寫時間戳插入句間停頓" for s in segrecs[:1] if s.get("segment_mode") == "post" and s.get("boundaries")]
               + [f"speed {settings_by[c].get('speed')}（基準 {g['settings'].get('speed')}）" for c, g in
                  ((cf["code"], cf) for cf in cfgs) if settings_by[c].get("speed") != g["settings"].get("speed")]}
        attempts.append(att)
        print(f"  {lid} 嘗試 {k + 1}：未通過 {','.join(failed) or '無'}  淨語速 {ch['d']['value']}  "
              f"句尾 {[s['tail']['last60ms_rel_dB'] for s in segrecs]}  停頓 {ch['e']['pauses_ms']}  "
              f"I={summ['integrated_lufs']} TP={summ['true_peak_dbtp']}  計費 {att['billed']}（本次新呼叫 {att['billed_new']}）  "
              + "｜".join(f"{m}：{v['hyp_trad']}" for m, v in asr.items()))
        entry["attempts"] = attempts
        report[lid] = entry
        merge_save(REPORT, lid, entry)
        if not failed:
            break
    entry["attempts"] = attempts
    entry["billed_total"] = sum(a["billed"] for a in attempts)
    passed = [a for a in attempts if not a["failed"]]
    if not attempts or not (passed or len(attempts) >= max_att):
        entry["status"] = "incomplete"
        entry["stopped"] = str(stop)
        report[lid] = entry
        merge_save(REPORT, lid, entry)
        drop_outputs(lid, timings)      # 沒有目前版本的採用檔：移除舊版輸出，避免新舊混用
        raise stop
    best = passed[0] if passed else min(attempts, key=lambda a: (a["problems"], a["detail_score"], a["k"]))
    entry["status"] = "pass" if passed else "fail"
    entry["chosen"] = best["k"]
    entry.pop("stopped", None)
    shutil.copyfile(ROOT / best["wav"], final)
    y = V.read_wav(final)
    lip = V.lipsync(y, fps=D.get("lipsync_fps", 12))
    LIP.mkdir(parents=True, exist_ok=True)
    lp = LIP / f"{lid}_{VER}.json"
    lp.write_text(json.dumps(lip, separators=(",", ":")), "utf-8")
    entry.update({"file": rel(final), "lipsync": rel(lp), "seconds": round(len(y) / SR, 3),
                  "speech_start": best["master"]["speech_start"], "speech_end": best["master"]["speech_end"],
                  "speech_segments": V.speech_segments(y), "checks": best["checks"], "failed": best["failed"],
                  "metrics": best["metrics"], "request_ids": [s["request_id"] for s in best["segments"]],
                  "mitigations": best["mitigations"]})
    report[lid] = entry
    timings[lid] = {k: entry[k] for k in ("seconds", "speech_start", "speech_end", "speech_segments", "file", "lipsync",
                                          "role", "text")}
    merge_save(REPORT, lid, entry)
    merge_save(TIMINGS, lid, timings[lid])
    print(f"{lid} {ln['role']} → {entry['status']}（採用第 {best['k']} 次，共 {len(attempts)} 次；"
          f"未通過 {','.join(best['failed']) or '無'}；本句計費 {entry['billed_total']}）")
    return entry["status"]


def dry_run(ids: list[str], args) -> None:
    report = jload(REPORT, {})
    tot = 0
    print(f"共 {len(ids)} 句；每次嘗試預估點數＝送出字元 × 0.4（實際以 character-cost 為準）；上限 --max-credits {args.max_credits}")
    for lid in ids:
        ln = LINES[lid]
        codes = [ROLE2CODE.get(r) for r in roles_of(ln)]
        cfgs = [load_cast(c) for c in codes]
        if any(c is None for c in cfgs):
            print(f"  {lid} {ln['role']} 略過（沒有 EL 角色設定）")
            continue
        chars, segtxt = 0, []
        for c in cfgs:
            gap = REQUIRED_INSERT_MS if lid in REQUIRED else c.get("lines", {}).get(lid, {}).get("sentence_gap_ms", c.get("sentence_gap_ms", 450))
            segs = plan_segments(synth_text_for(c, lid, ln["text"]), gap)
            lc = c.get("lines", {}).get(lid, {})
            smode = lc.get("segment_mode", c.get("segment_mode", "synth"))
            tg = deep_merge(c.get("tail_guard", {"mode": "off"}), lc.get("tail_guard", {}))
            n_units = 1 if (smode == "post" or len(segs) == 1) else len(segs)
            suf = len(tg.get("suffix", "……嗯。")) if tg.get("mode") == "always" else 0
            chars += sum(len(s) for s, _ in segs) + suf * n_units
            segtxt.append(f"{smode}{'＋句尾保護' if suf else ''}：" + " / ".join(f"{s}" + (f" [{g}ms]" if g else "") for s, g in segs))
        est = math.ceil(chars * 0.4)
        old = report.get(lid)
        st = "未做" if not old else ("可沿用" if old.get("signature") == el_signature(lid, cfgs) and old["status"] in ("pass", "fail")
                                    else f"{old['status']}（設定已變或未完成）")
        tot += est if st != "可沿用" else 0
        print(f"  {lid} {ln['role']}｜{st}｜每次約 {est} 點（最多 {min(args.max_attempts, MAX_ATTEMPTS_CAP)} 次＝{est * min(args.max_attempts, MAX_ATTEMPTS_CAP)}）"
              f"｜{'｜'.join(segtxt)}")
    print(f"一次全過預估 {tot} 點；全部用滿嘗試次數最多 {tot * min(args.max_attempts, MAX_ATTEMPTS_CAP)} 點")


def run_el(ids: list[str], args) -> None:
    if args.dry_run:
        dry_run(ids, args)
        return
    report = jload(REPORT, {})
    timings = jload(TIMINGS, {})
    run = {"spent": 0, "calls": 0, "failed": 0, "max_credits": args.max_credits}
    ledger_run({"start": now(), "lines": ids, "max_credits": args.max_credits,
                "max_attempts": min(args.max_attempts, MAX_ATTEMPTS_CAP)}, start=True)
    stats: dict[str, int] = {}
    stopped = None
    try:
        for lid in ids:
            st = run_line(lid, args, run, report, timings)
            stats[st] = stats.get(st, 0) + 1
    except (BudgetStop, ApiStop) as ex:
        stopped = str(ex)
    ledger_run({"end": now(), "spent": run["spent"], "calls": run["calls"], "failed_calls": run["failed"],
                "stopped": stopped, "result": stats})
    print(f"本次 ElevenLabs 計費 {run['spent']} 點（呼叫 {run['calls']} 次、失敗 {run['failed']} 次）；結果 {stats}")
    if stopped:
        print(f"已停止：{stopped}\n續跑：用同樣的指令再執行一次（已完成的句子沿用，未完成句子從下一次嘗試接著做，已付費的原始檔不重算）。")
        sys.exit(3)


# ---------------------------------------------------------------- 報告
def f0_pooled(paths: list[Path]) -> float | None:
    import parselmouth
    fr = []
    for p in paths:
        pt = parselmouth.Sound(str(p)).to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
        f = pt.selected_array["frequency"]
        fr.append(f[f > 0])
    allf = np.concatenate(fr) if fr else np.array([])
    return round(float(np.median(allf)), 1) if len(allf) else None


def mp3(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:a", "libmp3lame", "-b:a", "96k", str(dst)], check=True)


def mark(ok) -> str:
    return "—" if ok is None else ("✓" if ok else "✗")


def chk_cell(ch: dict) -> str:
    out = []
    for k in "abcdef":
        c = ch.get(k, {})
        na = c.get("applicable") is False
        out.append(f"{k}{'·' if na else mark(c.get('pass'))}")
    return " ".join(out)


def fail_detail(ch: dict) -> str:
    out = []
    if not ch["a"]["pass"]:
        out.append("(a) " + "；".join(f"{m}：" + "、".join(f"{d['ref']}→{d['hyp'] or '∅'}（{d['kind']}）" for d in v["bad"])
                                      for m, v in ch["a"]["models"].items() if v["bad"]))
    if not ch["b"]["pass"]:
        out.append("(b) " + "、".join(f"{w}（{'／'.join(ch['b']['words'][w].values())}）" for w in ch["b"]["inconsistent"]))
    if not ch["c"]["pass"]:
        out.append("(c) " + "、".join(f"段{n + 1} {s['last60ms_rel_dB']} dB／有聲 {s['last60ms_voiced']}"
                                      for n, s in enumerate(ch["c"]["segments"]) if s["truncated"]))
    if not ch["d"]["pass"]:
        out.append(f"(d) {ch['d']['value']} 字／秒（範圍 {ch['d']['range'][0]}–{ch['d']['range'][1]}）")
    if not ch["e"]["pass"]:
        out.append(f"(e) {ch['e']['pauses_ms']} ms（門檻 {ch['e']['threshold_ms']}）"
                   + (f"；句界不乾淨 {ch['e']['unclean']}" if ch["e"].get("unclean") else ""))
    if not ch["f"]["pass"]:
        out.append(f"(f) {ch['f']['lufs']} LUFS／{ch['f']['true_peak_dbtp']} dBTP／削波 {ch['f']['clipped']}")
    return "；".join(out)


def med(v: list) -> float | None:
    v = [x for x in v if x is not None]
    return round(float(np.median(v)), 2) if v else None


def write_report() -> None:
    report = jload(REPORT, {})
    edge = jload(EDGE_METRICS, {})
    L = jload(LEDGER, LEDGER_DEFAULT)
    FULL.mkdir(parents=True, exist_ok=True)
    for lid, e in report.items():     # 角色設定改過、還沒重跑的句子：標成 stale，不算進比較
        cf = [load_cast(c) for c in e.get("codes", [])]
        e["stale"] = any(c is None for c in cf) or e.get("signature") != el_signature(lid, cf)
    stale = [e for e in report.values() if e["stale"]]
    report = {k: v for k, v in report.items() if not v["stale"]}
    casts = {c: load_cast(c) for c in [p.stem for p in sorted(CAST_DIR.glob("*.json"))]}
    by_role_el: dict[str, list[dict]] = {}
    for e in report.values():
        if e.get("status") in ("pass", "fail") and len(e["codes"]) == 1:
            by_role_el.setdefault(e["codes"][0], []).append(e)
    by_role_edge: dict[str, list[dict]] = {}
    for e in edge.values():
        if len(e["codes"]) == 1:
            by_role_edge.setdefault(e["codes"][0], []).append(e)

    # ---- separation.json（F0 中位：有 EL 採用檔的角色用 EL，否則用 edge 基準）
    roles = {}
    for code, role in CODE2ROLE.items():
        el_files = [ROOT / e["file"] for e in by_role_el.get(code, [])]
        ed_files = [ROOT / e["file"] for e in by_role_edge.get(code, [])]
        roles[code] = {"role": role, "engine": "elevenlabs" if el_files else ("edge" if ed_files else None),
                       "f0_median_el": f0_pooled(el_files) if el_files else None,
                       "f0_median_edge": f0_pooled(ed_files) if ed_files else None,
                       "n_el": len(el_files), "n_edge": len(ed_files),
                       "f0_target": DEFAULT_TARGETS.get(code, {}).get("f0_nominal")}
        roles[code]["f0_median"] = roles[code]["f0_median_el"] or roles[code]["f0_median_edge"]
    cues: dict[str, set] = {}
    for ln in LINES.values():
        for r in roles_of(ln):
            cues.setdefault(ROLE2CODE.get(r), set()).add(ln["cue"])
    pairs = []
    codes = list(CODE2ROLE)
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            fa, fb = roles[a]["f0_median"], roles[b]["f0_median"]
            shared = sorted(cues.get(a, set()) & cues.get(b, set()))
            pairs.append({"a": CODE2ROLE[a], "b": CODE2ROLE[b], "engines": [roles[a]["engine"], roles[b]["engine"]],
                          "f0": [fa, fb], "semitones": abs(semitones(fa, fb)) if fa and fb else None,
                          "same_scene": bool(shared), "shared_cues": shared})
    pairs.sort(key=lambda p: (not p["same_scene"], p["semitones"] if p["semitones"] is not None else 99))
    sep = {"_說明": "全部角色兩兩的 F0 中位數半音差。F0＝該角色所有檔案有聲格合併的中位數（parselmouth 自相關，75–700 Hz）；"
                    "有 ElevenLabs 採用檔的角色用 EL，否則用 edge 基準。same_scene＝兩個角色在同一個 cue（同場戲）都有台詞。"
                    "排序：同場戲在前、半音差小的在前。聽感未驗證。",
           "generated": now(), "roles": roles, "pairs": pairs,
           "same_scene_under_3st": [p for p in pairs if p["same_scene"] and p["semitones"] is not None and p["semitones"] < 3]}
    jsave(FULL / "separation.json", sep)

    # ---- metrics.json
    role_rows = {}
    for code, role in CODE2ROLE.items():
        el = by_role_el.get(code, [])
        ed = by_role_edge.get(code, [])
        all_el = [e for e in report.values() if code in e.get("codes", [])]
        role_rows[code] = {
            "role": role, "cast": {k: (casts.get(code) or {}).get(k) for k in ("voice_name", "voice_id", "model", "status")} if casts.get(code) else None,
            "el_lines": len(el), "el_pass": sum(1 for e in el if e["status"] == "pass"),
            "el_fail": sum(1 for e in el if e["status"] == "fail"),
            "el_incomplete": sum(1 for e in all_el if e.get("status") == "incomplete"),
            "el_attempts_mean": round(float(np.mean([len(e["attempts"]) for e in el])), 2) if el else None,
            "el_billed": sum(e.get("billed_total", 0) for e in all_el),
            "edge_lines": len(ed), "edge_pass": sum(1 for e in ed if not e["failed"]),
            "f0_el": roles[code]["f0_median_el"], "f0_edge": roles[code]["f0_median_edge"],
            "f0_target": DEFAULT_TARGETS.get(code, {}).get("f0_nominal"),
            "rate_el_median": med([e["checks"]["d"]["value"] for e in el]),
            "rate_edge_median": med([e["checks"]["d"]["value"] for e in ed]),
            "rate_nominal": ((casts.get(code) or {}).get("targets") or DEFAULT_TARGETS.get(code, {})).get("rate_nominal"),
            "fail_counts_el": {k: sum(1 for e in el if k in e["failed"]) for k in "abcdef"},
            "fail_counts_edge": {k: sum(1 for e in ed if k in e["failed"]) for k in "abcdef"},
        }
    metrics = {"_說明": "EL 採用版與 edge 基準的逐句檢查與量測（tools/vo_el_prod.py --report）。el＝audio/vo_el/build_report_el.json "
                        "的採用嘗試摘要；edge＝review/G3/el/full/edge/metrics.json。",
               "generated": now(), "ledger": {k: L.get(k) for k in ("total_billed", "calls", "failed_calls", "by_role")},
               "roles": role_rows,
               "el": {lid: {k: e.get(k) for k in ("role", "status", "chosen", "file", "failed", "checks", "metrics", "billed_total",
                                                    "request_ids", "mitigations")} | {"attempts": len(e.get("attempts", []))}
                      for lid, e in report.items()},
               "edge": {lid: {k: e.get(k) for k in ("role", "file", "failed", "checks", "metrics")} for lid, e in edge.items()}}
    jsave(FULL / "metrics.json", metrics)

    # ---- transcripts.md
    tl = ["# 逐字稿（EL 全劇版對 edge 基準）", "",
          "兩個轉寫模型：faster-whisper small、large-v3-turbo。比對＝vo_lib.compare（逐字對齊；參考讀音取 pronounce.json 全域替身字；"
          "台灣讀音表）。✓＝兩個模型都只有同音字。聽感未驗證。", ""]
    for lid in [l for l in LINES if l in report or l in edge]:
        ln = LINES[lid]
        tl.append(f"## {lid}｜{ln['role']}｜{ln['text']}")
        tl.append("")
        e = report.get(lid)
        if e and e.get("attempts"):
            for a in e["attempts"]:
                tag = "（採用）" if a["k"] == e.get("chosen") else ""
                tl.append(f"- EL 嘗試 {a['k']}{tag}：未通過 {','.join(a['failed']) or '無'}")
                for m, v in a["asr"].items():
                    bad = [d for d in v["diffs"] if d["kind"] != HOMO]
                    tl.append(f"  - {m}：{v['hyp_trad']}（CER {v['cer']}／PER {v['per']}）"
                              + ("；差異 " + "、".join(f"{d['ref']}→{d['hyp'] or '∅'}（{d['kind']}）" for d in bad) if bad else ""))
        b = edge.get(lid)
        if b:
            tl.append(f"- edge 基準：未通過 {','.join(b['failed']) or '無'}")
            for m, v in b["asr"].items():
                bad = [d for d in v["diffs"] if d["kind"] != HOMO]
                tl.append(f"  - {m}：{v['hyp_trad']}（CER {v['cer']}／PER {v['per']}）"
                          + ("；差異 " + "、".join(f"{d['ref']}→{d['hyp'] or '∅'}（{d['kind']}）" for d in bad) if bad else ""))
        tl.append("")
    (FULL / "transcripts.md").write_text("\n".join(tl), "utf-8")

    # ---- listen.html（音檔轉 96 kbps mp3，相對路徑）
    rows = []
    for lid in [l for l in LINES if l in report and report[l].get("file")]:
        e = report[lid]
        el_mp3 = LISTEN / f"{lid}_{VER}.mp3"
        mp3(ROOT / e["file"], el_mp3)
        b = edge.get(lid)
        ed_cell = "—"
        if b:
            ed_mp3 = LISTEN / f"{lid}_edge.mp3"
            mp3(ROOT / b["file"], ed_mp3)
            ed_cell = f'<audio controls preload="none" src="listen/{ed_mp3.name}"></audio><div class="c">{chk_cell(b["checks"])}</div>'
        st = "通過" if e["status"] == "pass" else "未通過"
        rows.append(f"<tr><td class='id'>{lid}</td><td>{html.escape(e['role'])}</td><td>{html.escape(e['text'])}</td>"
                    f"<td>{ed_cell}</td><td><audio controls preload='none' src='listen/{el_mp3.name}'></audio>"
                    f"<div class='c'>{chk_cell(e['checks'])}</div></td><td class='{'ok' if e['status'] == 'pass' else 'ng'}'>{st}"
                    f"<div class='c'>第 {e['chosen']}／{len(e['attempts'])} 次</div></td></tr>")
    page = f"""<!doctype html>
<html lang="zh-Hant-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EL 全劇試聽</title>
<style>
:root{{--bg:#faf8f4;--fg:#222;--mut:#666;--line:#ddd6cc;--ok:#1d6b3a;--ng:#a3322a;--head:#efe9df}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1c1b19;--fg:#eee;--mut:#aaa;--line:#3a3833;--ok:#6fcf8f;--ng:#ff8a80;--head:#2a2825}}}}
:root[data-theme="dark"]{{--bg:#1c1b19;--fg:#eee;--mut:#aaa;--line:#3a3833;--ok:#6fcf8f;--ng:#ff8a80;--head:#2a2825}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.6 "PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} p{{color:var(--mut);margin:4px 0 12px}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;min-width:760px}}
th,td{{border-bottom:1px solid var(--line);padding:8px 6px;text-align:left;vertical-align:top}}
th{{background:var(--head);position:sticky;top:0}} td.id{{font-family:ui-monospace,Menlo,monospace;white-space:nowrap}}
audio{{width:220px;height:32px}} .c{{font-size:12px;color:var(--mut);font-family:ui-monospace,Menlo,monospace}}
.ok{{color:var(--ok)}} .ng{{color:var(--ng)}}
</style></head><body>
<h1>EL 全劇版試聽（edge 基準對 ElevenLabs）</h1>
<p>逐句比較。檢查欄：a 轉寫只有同音字、b 讀音檢查詞、c 句尾完整、d 淨語速、e 句間停頓、f 響度／真峰值／削波；✓ 通過、✗ 未通過、· 不適用。
音檔為 96 kbps mp3 試聽版（正式檔是 48 kHz／16-bit wav）。聽感（台灣口音、自然度）未驗證：Claude 聽不到聲音。產生時間 {now()}。</p>
<div class="wrap"><table><thead><tr><th>台詞</th><th>角色</th><th>劇本</th><th>edge 基準</th><th>ElevenLabs（採用）</th><th>結果</th></tr></thead>
<tbody>
{chr(10).join(rows) if rows else '<tr><td colspan="6">尚無 EL 輸出</td></tr>'}
</tbody></table></div></body></html>
"""
    (FULL / "listen.html").write_text(page, "utf-8")

    # ---- INDEX.md
    el_entries = [report[l] for l in LINES if l in report]
    fails = [e for e in el_entries if e.get("status") == "fail"]
    inc = [e for e in el_entries if e.get("status") == "incomplete"]
    idx = ["# ElevenLabs 全劇版配音｜驗收入口", "",
           f"- 產生：{now()}｜工具：`tools/vo_el_prod.py --report`｜製作：配音工程代理",
           f"- EL 角色設定（`audio/vo_el/casting/`）：" + ("、".join(f"{c['role']}＝{c['voice_name']}（{c['model']}，{c.get('status', 'active')}）"
                                                          for c in casts.values() if c) or "無"),
           f"- EL 句數：{len(el_entries)}（通過 {sum(1 for e in el_entries if e.get('status') == 'pass')}、未通過 {len(fails)}、"
           f"未完成 {len(inc)}）｜edge 基準句數：{len(edge)}"
           + (f"｜角色設定改過、尚未重跑（不列入本報告）：{'、'.join(e['id'] for e in stale)}" if stale else ""),
           f"- 點數：累計 **{L.get('total_billed', 0)}** 點（`audio/vo_el/ledger.json`，依回應標頭 character-cost），"
           f"呼叫 {L.get('calls', 0)} 次、失敗 {L.get('failed_calls', 0)} 次。",
           "- **聽感一律未驗證**：台灣口音、自然度、情緒、像不像孩子，Claude 聽不到聲音。",
           "- 授權不在本工具範圍（見 `review/G3/el/license_evidence.md`）。", "",
           "## 1. 每次嘗試的自動檢查（全部通過才採用）", "",
           "| 項目 | 規則 |", "|---|---|",
           "| (a) 轉寫 | small＋large-v3-turbo 各轉寫一次，vo_lib.compare 逐字對齊（參考讀音＝pronounce.json 全域替身字；台灣讀音表），兩個模型都只能有同音字。人名在 edge 基準同句、同模型也有同音的轉寫差異時豁免（必要旁白不豁免）。 |",
           f"| (b) 讀音檢查詞 | {'、'.join(CHECK_WORDS)}：句中有的詞，兩個模型都要「轉寫一致」或「同音轉寫」。 |",
           "| (c) 句尾完整 | 每段原始 mp3 的最後 60 ms：RMS 相對 p90 > −25 dB 且有聲比例 > 30% ＝截斷（方法同 review/G3/el/qa/配音導演/tail_voicing.py）。用句尾保護時改在切點前 60 ms 用同一門檻判定（原始檔結尾數值另存 tail_raw_end）。 |",
           f"| (d) 淨語速 | −40 dB、扣掉 ≥200 ms 停頓（vo_lib.measure 驗收者算法），漢字＋數字逐字計；角色表語速 ±{RATE_TOL}；必要旁白 {REQUIRED_RATE[0]}–{REQUIRED_RATE[1]}；少於 {MIN_SYLL_FOR_RATE} 音節不判定。 |",
           f"| (e) 句間停頓 | 多句台詞依句號／問號／驚嘆號分段合成並插入停頓；母帶檔每個句界靜音（−35 dB）≥{MIN_GAP_MS} ms，必要旁白 ≥{REQUIRED_GAP_MS} ms。edge 基準沒有句界位置，取最長的 n−1 個停頓。 |",
           "| (f) 母帶 | vo_lib.master：頭 120 ms、尾 250 ms、−18±0.5 LUFS（loudness_offset_db 另計）、真峰值 ≤ −1.5 dBTP、削波 0、48 kHz／16-bit／單聲道。 |",
           "", "重算：換 seed（seed_base＋嘗試序號），最多 6 次；都沒通過就保留問題最少的一次並標 fail。adaptive_speed（角色設定開啟時）依上一次語速調 speed ±step（eleven_v3 實測不理會 speed，所以 v3 角色關閉）。", "",
           "減輕方法（角色設定可選，用到的句子列在第 4 節「處理」欄）：",
           "- **句尾保護**（tail_guard）：送出文字句尾加「……嗯。」，合成器的截斷落在填充字上。切點：用 large-v3-turbo 字詞時間戳找正文最後一字的結束與填充字的開始，取其間最早一段 ≥60 ms 的無聲低能量段（p90 −12 dB 以下、沒有 F0；對不上時改取最後一段 ≥300 ms 的），正文衰減到底噪後再留最多 100 ms 處切掉（20 ms 淡出）。填充字黏在句尾、找不到停頓＝(c) 不通過；切錯時 (a) 轉寫會看到殘留的「嗯」或漏字。",
           "- **整句合成**（segment_mode=post）：整句一次合成（eleven_v3 分段合成時語速明顯變快），句界用 large-v3-turbo 字詞時間戳定位（前後放寬 120 ms 取能量最低點），原有停頓不足的部分補靜音；最低點高於 p90 −20 dB＝句界不乾淨，(e) 不通過。",
           "- 舊法（tail_guard 關閉時）：同一段句尾截斷 2 次以上，下一次句尾補「……」（第 1 輪試跑無效）。", "",
           "## 2. 逐角色比較（EL 採用版 對 edge 基準）", "",
           "| 角色 | EL 聲線／模型 | EL 句數 | 通過／未通過／未完成 | 平均嘗試 | F0 中位 EL／edge（目標 Hz） | 淨語速中位 EL／edge（角色表） | EL 未通過項 | edge 未通過項 | 本版嘗試計費 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for code, r in role_rows.items():
        cast = r["cast"]
        fc = lambda d: "、".join(f"{k}×{v}" for k, v in d.items() if v) or "—"  # noqa: E731
        idx.append(f"| {r['role']} | {(cast['voice_name'] + '／' + cast['model']) if cast else '（無 EL 設定）'} | {r['el_lines']} | "
                   f"{r['el_pass']}／{r['el_fail']}／{r['el_incomplete']} | {r['el_attempts_mean'] or '—'} | "
                   f"{r['f0_el'] or '—'}／{r['f0_edge'] or '—'}（{r['f0_target']}） | {r['rate_el_median'] or '—'}／{r['rate_edge_median'] or '—'}"
                   f"（{'–'.join(str(x) for x in r['rate_nominal']) if r['rate_nominal'] else '—'}） | {fc(r['fail_counts_el'])} | "
                   f"{fc(r['fail_counts_edge'])}（{r['edge_lines']} 句） | {r['el_billed']} |")
    idx += ["", "## 3. 未通過句清單（EL）", ""]
    if fails or inc:
        idx += ["| 台詞 | 角色 | 狀態 | 嘗試 | 採用 | 未通過項與細節 |", "|---|---|---|---|---|---|"]
        for e in fails + inc:
            idx.append(f"| {e['id']} | {e['role']} | {e['status']} | {len(e['attempts'])} | {e.get('chosen', '—')} | "
                       f"{fail_detail(e['checks']) if e.get('checks') else html.escape(str(e.get('stopped')))} |")
    else:
        idx.append("（無）")
    idx += ["", "## 4. 逐句明細", "",
            "檢查欄：✓ 通過、✗ 未通過、· 不適用。request_id 與每次嘗試的完整紀錄見 `audio/vo_el/build_report_el.json`。", "",
            "| 台詞 | 角色 | EL 結果 | 採用／嘗試 | EL 檢查 | EL 淨語速 | EL F0 | 句尾 dB（各段） | 停頓 ms | 處理 | edge 檢查 | edge 淨語速 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in el_entries:
        if not e.get("checks"):
            idx.append(f"| {e['id']} | {e['role']} | {e['status']} | —／{len(e['attempts'])} | — | — | — | — | — | — | — | — |")
            continue
        b = edge.get(e["id"])
        ch = e["checks"]
        idx.append(f"| {e['id']} | {e['role']} | {e['status']} | {e['chosen']}／{len(e['attempts'])} | {chk_cell(ch)} | "
                   f"{ch['d']['value']} | {e['metrics']['f0_median']} | {'、'.join(str(s['last60ms_rel_dB']) for s in ch['c']['segments'])} | "
                   f"{ch['e']['pauses_ms'] or '—'} | {'；'.join(e.get('mitigations') or []) or '—'} | "
                   f"{chk_cell(b['checks']) if b else '—'} | {b['checks']['d']['value'] if b else '—'} |")
    sp = sep["same_scene_under_3st"]
    idx += ["", "## 5. 角色區分（separation.json）", "",
            f"同場戲（同一 cue 都有台詞）且 F0 中位差 <3 半音的組合：{len(sp)} 組。"
            + ("".join(f"\n- {p['a']}（{p['engines'][0]}）↔ {p['b']}（{p['engines'][1]}）：{p['semitones']} 半音；同場 {', '.join(p['shared_cues'][:6])}"
                       + ("…" if len(p['shared_cues']) > 6 else "") for p in sp) if sp else ""), "",
            "## 6. 點數", "",
            f"- 累計 {L.get('total_billed', 0)} 點；依角色：" + ("、".join(f"{CODE2ROLE.get(k, k)} {v}" for k, v in L.get("by_role", {}).items()) or "—"),
            "- 每次執行（上限、實際用量、停止原因）："]
    for r in L.get("runs", []):
        idx.append(f"  - {r.get('start')}–{r.get('end', '（執行中或中斷）')}：上限 {r.get('max_credits')}、用 {r.get('spent')}、"
                   f"呼叫 {r.get('calls')}、失敗 {r.get('failed_calls')}、停止 {r.get('stopped') or '無'}、結果 {r.get('result')}")
    tr = FULL / "trial" / "r1_synth_build_report.json"
    if tr.exists():
        r1 = jload(tr, {})
        segs = [sg for e in r1.values() for a in e.get("attempts", []) for sg in a["segments"]]
        ntr = sum(1 for sg in segs if sg["tail"]["truncated"])
        atts = [a for e in r1.values() for a in e.get("attempts", [])]
        fc = {k: sum(1 for a in atts if k in a["failed"]) for k in "abcdef"}
        idx += ["", "## 6.1 試跑紀錄（`review/G3/el/full/trial/`）", "",
                f"- 第 1 輪（segment_mode=synth、無句尾保護；{'、'.join(r1)}）：{len(atts)} 次嘗試全部未通過；各項未通過次數 "
                + "、".join(f"{k}×{v}" for k, v in fc.items() if v) + f"；分段句尾截斷 {ntr}/{len(segs)} 段。"
                "句尾補「……」無效。完整紀錄：`trial/r1_synth_build_report.json`（第 1 輪的 a5_c008_03 輸出移到 `trial/r1/`）。",
                "- 實驗：句尾加「……嗯。」後正文能自然衰減進長停頓（`audio/vo_el/_raw/x_tailtest/`）；eleven_v3 speed 0.7 對 1.2 正文長度相同（`x_speedtest/`）。",
                "- 第 2 輪（segment_mode=post＋句尾保護）：見第 2–4 節；a5_c008_03 因試跑點數上限（300）未重跑。"]
    idx += ["", "## 7. 檔案", "",
            "- `audio/vo_el/vo_<台詞編號>_el01.wav`：採用檔（48 kHz／16-bit／單聲道）；`audio/lipsync_el/<台詞編號>_el01.json`：對嘴（12 fps）",
            "- `audio/vo_el/timings_el.json`、`audio/vo_el/build_report_el.json`（每句所有嘗試、seed、speed、request_id、計費、檢查結果）、`audio/vo_el/ledger.json`",
            "- `audio/vo_el/casting/<代碼>.json`：角色設定；`audio/vo_el/_raw/`：EL 原始 mp3（含 request_id 中繼檔）；`audio/vo_el/_attempts/`：每次嘗試的母帶檔",
            "- `review/G3/el/full/edge/`：edge 基準（vo_<台詞編號>_edge.wav、metrics.json）",
            "- 本資料夾：`metrics.json`、`transcripts.md`、`separation.json`、`listen.html`（試聽，mp3 在 `listen/`）", "",
            "## 8. 已知限制與未驗證", "",
            "- 聽感、台灣口音、自然度、情緒、像不像孩子：未驗證。實際投影場地的聽感：未驗證（第 3 天彩排）。",
            "- 轉寫看不出「一」「不」變調與「垃圾」lè sè／lā jī 的差別；「119」轉寫成數字時也看不出 yāo／yī，所以 EL 送出文字用「一一九」（角色設定 text_subs）。",
            "- eleven_v3 每次輸出不同：同一 seed 重跑不會得到同一檔；已付費的原始檔存在 `audio/vo_el/_raw/`，續跑時沿用。",
            "- 句尾保護與整句合成是為了 eleven_v3 加的處理：切掉填充字的位置、插入停頓的句界都只用能量＋轉寫時間戳判定，句尾語氣與停頓自然度未驗證（聽感）；有用到的句子列在第 4 節「處理」欄。",
            "- eleven_v3 不理會 voice_settings.speed（同文字 0.7 與 1.2 正文長度 1.64／1.63 秒），語速只能靠換 seed 重抽；Devon 的淨語速逐次在約 4.5–5.3 之間（整句合成時），(d) 常在上限附近。",
            "- F0：Door（林老師）約 202 Hz、Angel（執勤人員）約 285–295 Hz（電話音色後），都高於 edge 版目標（161／203 Hz）；同場戲的區分見第 5 節。",
            "- F0 目標只列入報告，不是逐句通過條件。"]
    (FULL / "INDEX.md").write_text("\n".join(idx) + "\n", "utf-8")
    print(f"報告：{rel(FULL / 'INDEX.md')}、metrics.json、transcripts.md、separation.json、listen.html（{len(rows)} 句試聽）")


# ---------------------------------------------------------------- 選句與主程式
def select_lines(args, el: bool) -> list[str]:
    for lid in args.line:
        if lid not in LINES:
            raise SystemExit(f"沒有這句台詞：{lid}")
    for c in args.role:
        if c not in CODE2ROLE:
            raise SystemExit(f"沒有這個角色代碼：{c}（可用：{'、'.join(CODE2ROLE)}）")
    if args.line:
        ids = [l for l in LINES if l in args.line]
    elif args.role:
        ids = [l for l, ln in LINES.items() if any(ROLE2CODE.get(r) in args.role for r in roles_of(ln))]
    elif el:
        act = set(active_codes(args.include_draft))
        ids = [l for l, ln in LINES.items() if all(ROLE2CODE.get(r) in act for r in roles_of(ln))]
    else:
        ids = list(LINES)
    if el and not args.include_draft:
        act = set(active_codes(False))
        keep = []
        for l in ids:
            cs = [ROLE2CODE.get(r) for r in roles_of(LINES[l])]
            if all(c in act for c in cs):
                keep.append(l)
            else:
                print(f"{l} 略過：{'、'.join(c for c in cs if c not in act)} 沒有 active 的 EL 角色設定")
        ids = keep
    return ids


def main() -> None:
    ap = argparse.ArgumentParser(description="ElevenLabs 全劇版配音製作（逐句合成＋自動檢查＋重算＋點數保護）")
    ap.add_argument("--role", action="append", default=[], help="角色代碼（casting.json 的 code），可多個")
    ap.add_argument("--line", action="append", default=[], help="台詞編號，可多個")
    ap.add_argument("--max-attempts", type=int, default=6, help="每句最多嘗試次數（上限 6）")
    ap.add_argument("--max-credits", type=int, default=300, help="本次執行的 ElevenLabs 點數上限（到了就停，可續跑）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--baseline-edge", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--include-draft", action="store_true")
    ap.add_argument("--reuse-edge-baseline", action="store_true",
                    help="沿用既有 edge 基準（只用於人名豁免），簽章不同也不重算、不呼叫 edge-tts（2026-10-22 加）")
    args = ap.parse_args()
    verify_required()
    if args.max_attempts > MAX_ATTEMPTS_CAP:
        print(f"--max-attempts {args.max_attempts} 超過上限，改用 {MAX_ATTEMPTS_CAP}")
    if args.report:
        write_report()
        return
    if args.baseline_edge:
        run_baseline(select_lines(args, el=False), args)
        return
    run_el(select_lines(args, el=True), args)


if __name__ == "__main__":
    main()
