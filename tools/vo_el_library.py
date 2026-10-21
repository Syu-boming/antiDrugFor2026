"""ElevenLabs「台灣華語聲線庫」選角（成人角色為主；庫裡若有年輕聲線也試兒童角色與折折）。

用法（專案根目錄）：
  tools/.venv/bin/python tools/vo_el_library.py discover     # 1. GET /v1/shared-voices 找台灣華語聲線（不計點）
  tools/.venv/bin/python tools/vo_el_library.py probe        # 2. 每個聲線用「你好」實測 Starter 能不能用（約 1 點／個）
  tools/.venv/bin/python tools/vo_el_library.py shortlist    # 3. 依客觀條件替每個角色挑 ≤3 個候選（不計點）
  tools/.venv/bin/python tools/vo_el_library.py render       # 4. edge 基準＋候選 multilingual_v2 試音（計點）
  tools/.venv/bin/python tools/vo_el_library.py v3           # 5. 每個角色依客觀條件排前兩名，另跑 eleven_v3（計點）
  tools/.venv/bin/python tools/vo_el_library.py tone         # 6. 「紙燈節」F0 走勢（旁白、折折候選；原字與替身字）
  tools/.venv/bin/python tools/vo_el_library.py measure      # 7. 母帶後量測＋兩個轉寫模型＋共振峰（不計點）
  tools/.venv/bin/python tools/vo_el_library.py report       # 8. candidates.json、metrics.json、transcripts.md、INDEX.md、listen.html
  選項：--budget N（本代理 ElevenLabs 點數上限，預設 3000；接近上限就停止）

規則：金鑰只經 vo_lib.el_request 讀取，不印出、不寫檔。每次呼叫 ElevenLabs 都用 vo_lib.log_usage 記到
audio/vo/elevenlabs_usage.jsonl（purpose 以「EL 選角」開頭；失敗記錄錯誤原文）。計費依回應標頭 character-cost 累加。
輸出格式一律 mp3_44100_128（Starter 不能用 192k 與 PCM）；固定 seed。
母帶與量測同 G3：vo_lib.master（頭 120 ms、尾 250 ms、−18 LUFS、真峰值 ≤ −1.5 dBTP、48 kHz／16-bit／單聲道）、
vo_lib.measure、vo_lib.transcribe_compare（small＋large-v3-turbo；台灣讀音表與逐字對齊判斷檢查詞）。
只寫 review/G3/el/library/ 與本腳本；不改 casting.json、pronounce.json 與任何正式檔。聽感一律未驗證（Claude 聽不到聲音）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.parse
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402

OUT = V.ROOT / "review" / "G3" / "el" / "library"
RAW = OUT / "raw"                 # ElevenLabs 原始 mp3（快取：同參數不重複呼叫）
EDGE_RAW = OUT / "raw_edge"       # edge-tts 原始檔（基準；免費）
SAMPLES = OUT / "samples"
TONE = OUT / "tone_checks"
LEDGER = OUT / "ledger.json"      # 本代理點數帳本（依回應標頭 character-cost 累加）
VOICES = OUT / "voices.json"      # 聲線庫查詢結果
PROBE = OUT / "probe.json"        # 「你好」實測
FMT = "mp3_44100_128"
SEED = 20261021
PURPOSE = "EL 選角"


# ---------------------------------------------------------------- 帳本
def ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text("utf-8"))
    return {"_說明": "本代理 ElevenLabs 點數帳本：每筆成功呼叫依回應標頭 character-cost 累加；失敗的呼叫記 0（ElevenLabs 不計費）。",
            "budget": 3000, "spent": 0, "calls": 0, "failed": 0, "entries": []}


def save_ledger(L: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(L, ensure_ascii=False, indent=1), "utf-8")


class BudgetStop(Exception):
    pass


def _detail(payload: bytes):
    try:
        return json.loads(payload).get("detail", json.loads(payload))
    except Exception:
        return payload[:400].decode(errors="replace")


def el_tts(voice_id: str, text: str, model: str = "eleven_multilingual_v2", settings: dict | None = None,
           seed: int = SEED, language_code: str | None = None, purpose: str = PURPOSE, budget: int = 3000,
           tag: str = "") -> tuple[Path | None, dict]:
    """ElevenLabs TTS（有快取）。回傳 (原始 mp3 路徑或 None, 資訊)。接近上限（剩餘 < 本次字數＋20）就停止。"""
    RAW.mkdir(parents=True, exist_ok=True)
    body = {"text": text, "model_id": model, "seed": seed}
    if settings:
        body["voice_settings"] = settings
    if language_code:
        body["language_code"] = language_code
    key = json.dumps({"voice_id": voice_id, "body": body, "fmt": FMT}, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    out = RAW / f"el_{h}.mp3"
    if out.exists() and out.stat().st_size > 500:
        return out, {"cached": True, "billed": 0, "raw": out.name}
    L = ledger()
    L["budget"] = budget
    if L["spent"] + len(text) + 20 > budget:
        raise BudgetStop(f"點數上限 {budget}：已用 {L['spent']}，本次 {len(text)} 字元會超過")
    code, payload, hdr = V.el_request("POST", f"/v1/text-to-speech/{voice_id}?output_format={FMT}", body)
    full_purpose = f"{purpose} {tag}".strip()
    if code != 200:
        det = _detail(payload)
        V.log_usage({"purpose": full_purpose, "voice_id": voice_id, "model": model, "ok": False, "http": code,
                     "detail": det, "text_chars": len(text)})
        L["calls"] += 1
        L["failed"] += 1
        L["entries"].append({"purpose": full_purpose, "voice_id": voice_id, "model": model, "http": code, "billed": 0,
                             "text_chars": len(text), "detail": det, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        save_ledger(L)
        return None, {"cached": False, "ok": False, "http": code, "detail": det, "billed": 0}
    out.write_bytes(payload)
    cost = hdr.get("character-cost")
    billed = int(cost) if cost and str(cost).strip().isdigit() else len(text)
    V.log_usage({"purpose": full_purpose, "voice_id": voice_id, "model": model, "ok": True, "http": 200,
                 "text_chars": len(text), "billed": billed, "billed_source": "character-cost" if cost else "估計（無標頭）",
                 "request_id": hdr.get("request-id"), "raw": f"review/G3/el/library/raw/{out.name}"})
    L["spent"] += billed
    L["calls"] += 1
    L["entries"].append({"purpose": full_purpose, "voice_id": voice_id, "model": model, "http": 200, "billed": billed,
                         "text_chars": len(text), "request_id": hdr.get("request-id"), "raw": out.name,
                         "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    save_ledger(L)
    return out, {"cached": False, "ok": True, "billed": billed, "request_id": hdr.get("request-id"), "raw": out.name}


# ---------------------------------------------------------------- 1. 找聲線
FIELDS = ("name", "voice_id", "public_owner_id", "gender", "age", "accent", "use_case", "descriptive", "description",
          "free_users_allowed", "category", "language", "locale", "verified_languages", "preview_url", "cloned_by_count",
          "usage_character_count_1y", "date_unix", "featured", "notice_period", "rate")
QUERIES = [
    {"locale": "cmn-TW", "language": "zh"},
    {"accent": "taiwanese"},
    {"accent": "taiwan mandarin", "language": "zh"},   # 任務指定的 accent=taiwanese 查到 0 筆；聲線庫實際的口音值是「taiwan mandarin」
    {"search": "Taiwan"},
    {"search": "Taiwanese"},
]


def fetch_query(q: dict) -> tuple[list[dict], list[dict]]:
    voices, pages = [], []
    page = 0
    while True:
        params = dict(q, page_size=100, page=page)
        path = "/v1/shared-voices?" + urllib.parse.urlencode(params)
        code, payload, _ = V.el_request("GET", path)
        if code != 200:
            pages.append({"page": page, "http": code, "detail": _detail(payload)})
            break
        d = json.loads(payload)
        vs = d.get("voices", [])
        pages.append({"page": page, "http": 200, "n": len(vs), "has_more": d.get("has_more")})
        voices.extend(vs)
        if not d.get("has_more") or not vs or page > 50:
            break
        page += 1
    return voices, pages


def is_tw_mandarin(v: dict) -> dict:
    """台灣華語判定（客觀欄位）：locale＝cmn-TW，或 verified_languages 有 zh＋cmn-TW／taiwanese 口音，或 language=zh 且 accent 含 taiwan。"""
    reasons = []
    if (v.get("locale") or "").lower() == "cmn-tw":
        reasons.append("locale=cmn-TW")
    for vl in v.get("verified_languages") or []:
        if (vl.get("locale") or "").lower() == "cmn-tw" or ("taiwan" in (vl.get("accent") or "").lower() and vl.get("language") == "zh"):
            reasons.append(f"verified:{vl.get('language')}/{vl.get('accent')}/{vl.get('locale')}/{vl.get('model_id')}")
    if v.get("language") == "zh" and "taiwan" in (v.get("accent") or "").lower():
        reasons.append("language=zh＋accent=taiwanese")
    return {"tw_mandarin": bool(reasons), "reasons": sorted(set(reasons))}


def cmd_discover(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    allv: dict[str, dict] = {}
    qlog = []
    for q in QUERIES:
        vs, pages = fetch_query(q)
        qlog.append({"query": q, "pages": pages, "count": len(vs)})
        for v in vs:
            rec = allv.setdefault(v["voice_id"], {k: v.get(k) for k in FIELDS} | {"found_by": []})
            rec["found_by"].append(urllib.parse.urlencode(q))
        print(q, len(vs), pages)
    for rec in allv.values():
        rec.update(is_tw_mandarin(rec))
    res = {"_說明": "GET /v1/shared-voices（page_size=100，翻完所有分頁）四次查詢的聯集；tw_mandarin＝依客觀欄位判定為台灣華語"
                    "（locale=cmn-TW，或 verified_languages 有 cmn-TW／taiwanese 口音的 zh）。查詢不計點。",
           "time": time.strftime("%Y-%m-%d %H:%M:%S"), "queries": qlog, "total_unique": len(allv),
           "tw_mandarin_count": sum(1 for r in allv.values() if r["tw_mandarin"]), "voices": list(allv.values())}
    VOICES.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    print("聯集", len(allv), "台灣華語", res["tw_mandarin_count"])


# ---------------------------------------------------------------- 聲學量測（F0、共振峰）
FORMANT_CEILING = 5500   # 所有聲線（含 edge 基準）用同一個上限，數值才可互相比較


def f0_stats(x: np.ndarray) -> dict:
    import parselmouth
    p = parselmouth.Sound(x.astype(np.float64), sampling_frequency=V.SR).to_pitch_ac(time_step=0.01, pitch_floor=75,
                                                                                      pitch_ceiling=700)
    f = p.selected_array["frequency"]
    f = f[f > 0]
    if not len(f):
        return {"f0_median": None, "f0_p10": None, "f0_p90": None, "voiced_frames": 0}
    return {"f0_median": round(float(np.median(f)), 1), "f0_p10": round(float(np.percentile(f, 10)), 1),
            "f0_p90": round(float(np.percentile(f, 90)), 1), "voiced_frames": int(len(f))}


def formants(x: np.ndarray, ceiling: int = FORMANT_CEILING) -> dict:
    """有聲段 LPC（Praat Burg，5 個共振峰、上限 5500 Hz、25 ms 窗、10 ms 步進）的 F1／F2／F3 中位數。
    只取有聲格（自相關 F0 > 0）且強度在最大值 25 dB 以內的格。兒童聲道短，F1／F2 普遍比成人高（「像不像孩子」的客觀代理指標）。"""
    import parselmouth
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=V.SR)
    pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
    fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5, maximum_formant=ceiling, window_length=0.025,
                             pre_emphasis_from=50)
    inten = snd.to_intensity(minimum_pitch=75, time_step=0.01)
    imax = float(np.nanmax(inten.values))
    F = {1: [], 2: [], 3: []}
    for t, f in zip(pitch.xs(), pitch.selected_array["frequency"]):
        if f <= 0:
            continue
        iv = inten.get_value(t)
        if iv is None or math.isnan(iv) or iv < imax - 25:
            continue
        vals = [fm.get_value_at_time(k, t) for k in (1, 2, 3)]
        if any(v is None or math.isnan(v) for v in vals):
            continue
        for k, v in zip((1, 2, 3), vals):
            F[k].append(v)
    if not F[1]:
        return {"F1_median": None, "F2_median": None, "F3_median": None, "formant_frames": 0}
    return {"F1_median": round(float(np.median(F[1]))), "F2_median": round(float(np.median(F[2]))),
            "F3_median": round(float(np.median(F[3]))), "formant_frames": len(F[1]), "formant_ceiling_hz": ceiling}


# ---------------------------------------------------------------- 1b. 聲線主人的預覽檔（免費下載，只作篩選）
PREVIEWS = OUT / "previews"


def preview_url_of(v: dict) -> tuple[str | None, str]:
    for vl in v.get("verified_languages") or []:
        if (vl.get("locale") or "").lower() == "cmn-tw" and vl.get("model_id") == "eleven_multilingual_v2" and vl.get("preview_url"):
            return vl["preview_url"], "verified cmn-TW multilingual_v2"
    for vl in v.get("verified_languages") or []:
        if vl.get("language") == "zh" and vl.get("preview_url"):
            return vl["preview_url"], f"verified {vl.get('locale')} {vl.get('model_id')}"
    return v.get("preview_url"), "preview_url"


def cmd_previews(args) -> None:
    import urllib.request
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    d = json.loads(VOICES.read_text("utf-8"))
    rows = {}
    for v in d["voices"]:
        url, src = preview_url_of(v)
        rec = {"name": v["name"], "url_source": src}
        if not url:
            rows[v["voice_id"]] = rec | {"error": "沒有預覽網址"}
            continue
        p = PREVIEWS / f"{v['voice_id']}.mp3"
        if not p.exists():
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    p.write_bytes(r.read())
            except Exception as e:  # noqa: BLE001
                rows[v["voice_id"]] = rec | {"error": f"下載失敗：{e}"}
                continue
        try:
            x = V.read_wav_native(p)
            rec |= {"seconds": round(len(x) / V.SR, 2)} | f0_stats(x) | formants(x)
        except Exception as e:  # noqa: BLE001
            rec |= {"error": f"解碼失敗：{e}"}
        rows[v["voice_id"]] = rec
        print(f"{v['name'][:34]:34s} {rec.get('f0_median')}  F1 {rec.get('F1_median')} F2 {rec.get('F2_median')}")
    (OUT / "previews.json").write_text(json.dumps({
        "_說明": "聲線主人在聲線庫提供的預覽檔（Google Cloud Storage 公開網址，免費、不經 API、不計點）。內容與語言由聲線主人決定，"
                 "每個聲線不同，所以只用來做初步篩選（F0、共振峰），不作為候選比較的依據。量測方法同試音：F0＝parselmouth 自相關 75–700 Hz；"
                 f"共振峰＝有聲格 LPC（Burg）上限 {FORMANT_CEILING} Hz 的中位數。", "voices": rows}, ensure_ascii=False, indent=1), "utf-8")


# ---------------------------------------------------------------- 2. 「你好」實測
MAX_ADDS = 3


def add_voice(v: dict) -> dict:
    """把共享聲線加入「我的聲線」（只在直接用 voice_id 合成失敗、且錯誤指出要先加入時才用；最多 3 個）。"""
    code, payload, _ = V.el_request("POST", f"/v1/voices/add/{v['public_owner_id']}/{v['voice_id']}",
                                    {"new_name": f"EL選角 {v['name'][:30]}"})
    det = None if code == 200 else _detail(payload)
    V.log_usage({"purpose": f"{PURPOSE} 加入我的聲線 {v['name']}", "endpoint": "voices/add", "voice_id": v["voice_id"],
                 "ok": code == 200, "http": code, "detail": det, "text_chars": 0, "billed": 0})
    return {"http": code, "detail": det, "response": json.loads(payload) if code == 200 else None}


def cmd_probe(args) -> None:
    d = json.loads(VOICES.read_text("utf-8"))
    prev = json.loads(PROBE.read_text("utf-8")) if PROBE.exists() else {"voices": {}, "adds": []}
    adds = prev.get("adds", [])
    for v in d["voices"]:
        vid = v["voice_id"]
        old = prev["voices"].get(vid)
        if old and (old.get("ok") or old.get("http") in (400, 401, 402, 403)):
            continue        # 已測過（成功或方案限制），沿用
        try:
            raw, info = el_tts(vid, "你好", purpose=PURPOSE, budget=args.budget, tag=f"探測 你好 {v['name'][:30]}")
        except BudgetStop as e:
            print("停止：", e)
            break
        rec = {"name": v["name"], "ok": bool(raw), "http": 200 if raw else info.get("http"), "detail": info.get("detail"),
               "billed": info.get("billed"), "cached": info.get("cached"), "added_to_my_voices": False}
        det_s = json.dumps(info.get("detail") or "", ensure_ascii=False).lower()
        if not raw and ("not found" in det_s or "voice_not_found" in det_s or "add" in det_s and "library" in det_s) \
                and len(adds) < MAX_ADDS:
            a = add_voice(v)
            adds.append({"voice_id": vid, "name": v["name"], **a})
            rec["add_attempt"] = a
            if a["http"] == 200:
                rec["added_to_my_voices"] = True
                raw, info = el_tts(vid, "你好", purpose=PURPOSE, budget=args.budget, tag=f"探測（加入後）你好 {v['name'][:30]}")
                rec.update({"ok": bool(raw), "http": 200 if raw else info.get("http"), "detail": info.get("detail"),
                            "billed": (rec.get("billed") or 0) + (info.get("billed") or 0)})
        if raw:
            x = V.decode(raw)
            rec |= {"raw": f"review/G3/el/library/raw/{raw.name}", "seconds": round(len(x) / V.SR, 2)} | f0_stats(x)
        prev["voices"][vid] = rec
        print(f"{v['name'][:36]:36s} ok={rec['ok']} http={rec['http']} 計費={rec.get('billed')} F0={rec.get('f0_median')} "
              f"{'' if rec['ok'] else json.dumps(rec['detail'], ensure_ascii=False)[:120]}")
    prev["adds"] = adds
    prev["_說明"] = ("每個聲線用「你好」（2 字元）以 eleven_multilingual_v2、mp3_44100_128、seed 20261021 實測 Starter 能不能用；"
                    "失敗記錄 HTTP 狀態與錯誤原文（ElevenLabs 失敗不計費）。F0 只有兩個音節，僅供參考。")
    ok = [r for r in prev["voices"].values() if r["ok"]]
    prev["summary"] = {"tested": len(prev["voices"]), "usable": len(ok),
                       "failed_by_http": {str(k): sum(1 for r in prev["voices"].values() if not r["ok"] and r["http"] == k)
                                          for k in sorted({r["http"] for r in prev["voices"].values() if not r["ok"]}, key=str)},
                       "billed": sum((r.get("billed") or 0) for r in prev["voices"].values())}
    PROBE.write_text(json.dumps(prev, ensure_ascii=False, indent=1), "utf-8")
    print(prev["summary"], "帳本已用", ledger()["spent"])


# ---------------------------------------------------------------- 3. 角色計畫與客觀篩選
# F0 目標＝audio/vo/casting.json 各角色 note 記錄的 edge 正式參數量測值；語速目標＝script/角色表_v03.md 第 3 節。
# lines＝劇本台詞（vo_lib.load_lines，一字不改）；frames＝補念該角色台詞裡出現、但所選台詞沒涵蓋的檢查詞（取自該角色台詞的片段）。
ROLE_PLAN = {
    "narrator": dict(zh="旁白", cast="旁白", group="adult", lines=["a0_c001_01", "a2_c004_02", "a2_c003_02"],
                     frames=[("f_ale", "阿樂叔叔。", "阿樂叔叔（a2_c004_01 等句）")],
                     f0_target=185.0, f0_src="casting.json 旁白 note：F0 中位 185 Hz",
                     filt=dict(gender=None, age=["young", "middle_aged"], use_case=["narrative_story", "informative_educational"]),
                     speed=0.92, speed_line={"a2_c004_02": 0.85}, gap_line={"a2_c004_02": 1300},
                     rate=(3.8, 4.0), rate_line={"a2_c004_02": (3.3, 3.7)}, tone="a0_c001_01"),
    "ale": dict(zh="阿樂叔叔（一般段＋受影響段）", cast="阿樂叔叔", group="adult", lines=["a0_c002_03", "a2_c002_01", "a2_c012_02"],
                frames=[], f0_target=113.0, f0_src="casting.json 葉護理師 note：阿樂一般段 113 Hz（受影響段 103 Hz）",
                filt=dict(gender="male", age=["middle_aged"], use_case=None),
                speed=0.92, speed_line={"a2_c002_01": 0.85, "a2_c012_02": 0.85},
                rate=(3.6, 3.8), rate_line={"a2_c002_01": (3.3, 3.5), "a2_c012_02": (3.3, 3.5)}),
    "ye": dict(zh="葉護理師", cast="葉護理師", group="adult", lines=["a2_c012_01", "a5_c008_03"], frames=[],
               f0_target=148.0, f0_src="casting.json 葉護理師 note：F0 148 Hz",
               filt=dict(gender="male", age=["young", "middle_aged"], use_case=None), speed=0.92, rate=(3.8, 4.0)),
    "lin": dict(zh="林老師", cast="林老師", group="adult", lines=["a3_c008_01", "a3_c003_02", "a3_c008_02"],
                frames=[("f_buyao", "盒子不要碰。", "「不要」變調（a6_c006_04 片段）")],
                f0_target=161.0, f0_src="casting.json 林老師 note：F0 161 Hz",
                filt=dict(gender="female", age=["young", "middle_aged"], use_case=None), speed=0.95, rate=(3.9, 4.1)),
    "chen": dict(zh="陳伯伯", cast="陳伯伯", group="adult", lines=["a4_c012_05", "a5_c001_02"], frames=[],
                 f0_target=91.7, f0_src="casting.json 陳伯伯 note：91.7 Hz（全劇最低）",
                 filt=dict(gender="male", age=["middle_aged"], use_case=None), speed=0.88, rate=(3.5, 3.7)),
    "inviter": dict(zh="邀請者", cast="邀請者", group="adult", lines=["a1_c002_02", "a3_c001_03"], frames=[],
                    f0_target=167.0, f0_src="casting.json 邀請者 note：約 167 Hz（中性區 145–175 Hz）", f0_window=(145, 175),
                    filt=dict(gender=None, age=["young", "middle_aged"], use_case=None), speed=1.0, rate=(4.0, 4.4)),
    "dispatcher": dict(zh="執勤人員", cast="執勤人員", group="adult", lines=["a5_c006_01", "a5_c006_05"], frames=[],
                       f0_target=203.0, f0_src="casting.json 執勤人員 note：F0 203 Hz（電話音色後量）",
                       filt=dict(gender=None, age=["young", "middle_aged"], use_case=["informative_educational", "narrative_story"]),
                       speed=1.0, rate=(4.0, 4.4), telephone=True),
    # ---- 庫裡的年輕聲線試兒童角色與折折（聲線設計由另一位代理負責）
    "zhezhe": dict(zh="折折", cast="折折", group="kids", lines=["a0_c003_01", "a0_c002_02", "a3_c004_02"],
                   frames=[("f_zhezhe", "我是折折。", "折折（a0_c002_01 片段）")],
                   f0_target=293.5, f0_src="casting.json 折折 note：293.5 Hz（全劇最高）", f0_min=220,
                   filt=dict(gender="female", age=["young"], use_case=None), speed=1.05, rate=(4.3, 4.6), tone="a0_c003_01"),
    "xiaoqing": dict(zh="小晴", cast="小晴", group="kids", lines=["a1_c001_01", "a1_c008_02"], frames=[],
                     f0_target=276.9, f0_src="casting.json 小晴 note：276.9 Hz", f0_min=220,
                     filt=dict(gender="female", age=["young"], use_case=None), speed=0.97, rate=(3.9, 4.1)),
    "xiaoyu": dict(zh="小宇", cast="小宇", group="kids", lines=["a3_c002_02", "a2_c013_04", "a0_c004_01"], frames=[],
                   f0_target=228.0, f0_src="casting.json 小宇 note：228 Hz", f0_min=220,
                   filt=dict(gender=None, age=["young"], use_case=None), speed=1.0, rate=(4.2, 4.4)),
    "pinan": dict(zh="品安", cast="品安", group="kids", lines=["a1_c004_06", "a6_c002_03"], frames=[],
                  f0_target=181.0, f0_src="casting.json 品安 note：181 Hz", f0_min=220,
                  filt=dict(gender="female", age=["young"], use_case=None), speed=0.9, rate=(3.6, 3.8)),
}
ADULT_EXCLUDE_USE = {"characters_animation"}     # 成人寫實角色排除「卡通角色」用途的聲線
MAX_CANDS = 3
CANDS = OUT / "candidates.json"


def semis(a: float, b: float) -> float:
    return abs(12 * math.log2(a / b))


def screen(role: str, plan: dict, voices: list[dict], previews: dict, probe: dict) -> dict:
    f = plan["filt"]
    rows = []
    for v in voices:
        vid = v["voice_id"]
        pv, pb = previews.get(vid, {}), probe.get(vid, {})
        f0 = pv.get("f0_median") or pb.get("f0_median")
        why = []
        if not v.get("tw_mandarin"):
            why.append("不是台灣華語（locale／verified_languages）")
        if not pb.get("ok"):
            why.append(f"Starter 實測不能用（HTTP {pb.get('http')}）")
        if str(v.get("rate") or 1.0) not in ("1", "1.0"):
            why.append(f"計費倍率 {v.get('rate')}（點數加倍）")
        if f["gender"] and v.get("gender") != f["gender"]:
            why.append(f"性別 {v.get('gender') or '未標'} ≠ {f['gender']}")
        if f["age"] and v.get("age") not in f["age"]:
            why.append(f"年齡 {v.get('age')} 不在 {f['age']}")
        if f["use_case"] and v.get("use_case") not in f["use_case"]:
            why.append(f"用途 {v.get('use_case')} 不在 {f['use_case']}")
        if plan["group"] == "adult" and v.get("use_case") in ADULT_EXCLUDE_USE:
            why.append("用途 characters_animation（成人寫實角色排除）")
        if f0 is None:
            why.append("沒有 F0")
        else:
            if plan.get("f0_window") and not (plan["f0_window"][0] <= f0 <= plan["f0_window"][1]):
                why.append(f"預覽 F0 {f0} 不在中性區 {plan['f0_window']}")
            if plan.get("f0_min") and f0 < plan["f0_min"]:
                why.append(f"預覽 F0 {f0} < 兒童下限 {plan['f0_min']} Hz")
        rows.append({"voice_id": vid, "name": v["name"], "gender": v.get("gender"), "age": v.get("age"),
                     "use_case": v.get("use_case"), "preview_f0": pv.get("f0_median"), "probe_f0": pb.get("f0_median"),
                     "preview_F1": pv.get("F1_median"), "preview_F2": pv.get("F2_median"),
                     "f0_dist_semitones": round(semis(f0, plan["f0_target"]), 2) if f0 else None,
                     "excluded": why})
    passing = sorted([r for r in rows if not r["excluded"]], key=lambda r: (r["f0_dist_semitones"], r["name"]))
    return {"passing": passing, "chosen": [r["voice_id"] for r in passing[:MAX_CANDS]],
            "excluded_count": sum(1 for r in rows if r["excluded"]),
            "excluded": [{"name": r["name"], "why": r["excluded"]} for r in rows if r["excluded"]]}


def cmd_shortlist(args) -> None:
    voices = json.loads(VOICES.read_text("utf-8"))["voices"]
    previews = json.loads((OUT / "previews.json").read_text("utf-8"))["voices"]
    probe = json.loads(PROBE.read_text("utf-8"))["voices"]
    byid = {v["voice_id"]: v for v in voices}
    old = json.loads(CANDS.read_text("utf-8")) if CANDS.exists() else {}
    res = {"_說明": "候選篩選（只用客觀條件，不含聽感）：硬條件＝台灣華語（locale／verified_languages）、Starter「你好」實測可用、計費倍率 1、"
                    "性別與年齡符合角色表、用途條件（旁白與執勤人員限 narrative_story／informative_educational）、成人寫實角色排除 "
                    "characters_animation、邀請者預覽 F0 在中性區 145–175 Hz、兒童角色預覽 F0 ≥ 220 Hz；"
                    "排序＝聲線主人預覽檔的 F0 中位與 casting.json 的 F0 目標相差的半音數（小者優先），取前 3。"
                    "同一個聲線可以同時是不同角色的候選（各角色獨立篩選）。", "roles": {}}
    for role, plan in ROLE_PLAN.items():
        s = screen(role, plan, voices, previews, probe)
        cands = []
        for i, vid in enumerate(s["chosen"]):
            v = byid[vid]
            short = v["name"].split(" - ")[0].split()[0].replace("/", "")
            cands.append({"cand_id": f"{role}_{short}-{vid[:4]}", "rank_screen": i + 1, "voice_id": vid, "name": v["name"],
                          "public_owner_id": v["public_owner_id"], "gender": v.get("gender"), "age": v.get("age"),
                          "accent": v.get("accent"), "use_case": v.get("use_case"), "description": v.get("description"),
                          "free_users_allowed": v.get("free_users_allowed"), "category": v.get("category"),
                          "preview_f0": previews.get(vid, {}).get("f0_median"),
                          "f0_dist_semitones": next(r["f0_dist_semitones"] for r in s["passing"] if r["voice_id"] == vid)})
        res["roles"][role] = {"zh": plan["zh"], "group": plan["group"], "lines": plan["lines"],
                              "frames": [list(f) for f in plan.get("frames", [])], "f0_target": plan["f0_target"],
                              "f0_src": plan["f0_src"], "filter": plan["filt"] | {k: plan[k] for k in ("f0_window", "f0_min") if k in plan},
                              "speed": plan["speed"], "speed_line": plan.get("speed_line", {}), "rate_target": plan["rate"],
                              "rate_target_line": plan.get("rate_line", {}), "candidates": cands,
                              "screen_passing": s["passing"], "screen_excluded_count": s["excluded_count"],
                              "v3": old.get("roles", {}).get(role, {}).get("v3")}
        print(f"{plan['zh']:16s} 通過 {len(s['passing']):2d}：" + "、".join(f"{c['name'].split(' - ')[0]}({c['preview_f0']})" for c in cands))
    CANDS.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")


# ---------------------------------------------------------------- 4. 合成（edge 基準＋ElevenLabs）
_R = None


def R():
    """延後載入 vo_g3_r1（它會載入 vo_build、casting.json、pronounce.json、劇本；只讀）。"""
    global _R
    if _R is None:
        import vo_g3_r1 as r1
        _R = r1
    return _R


def edge_render(role_cast: str, item_id: str, text: str, line_id: str | None) -> tuple[np.ndarray, dict]:
    """edge 基準：照 casting.json 目前的參數（含 post）走 vo_build.render_line；原始檔快取放本代理資料夾。"""
    r = R()
    V.RAW_DIR = EDGE_RAW
    ln = {"id": line_id or item_id, "cue": (line_id or item_id)[:7], "role": role_cast, "text": text}
    x, notes = r.B.render_line(ln, r.CAST, r.PRON, None, False, f"{PURPOSE} edge 基準")
    return x, {"service": "edge", "specs": notes["specs"], "segments": notes.get("segments"), "pause_caps": notes.get("pause_caps", []),
               "synth_text": notes["specs"][0]["synth_text"]}


def el_render(vid: str, text_syn: str, model: str, speed: float, gap_ms: int | None, budget: int, tag: str,
              telephone: bool = False) -> tuple[np.ndarray | None, dict]:
    segs = R().B.plan_segments(text_syn, gap_ms)
    chunks, log, billed = [], [], 0
    for i, (part, gap) in enumerate(segs):
        if model == "eleven_v3":
            st = {"stability": 0.5, "similarity_boost": 0.75, "speed": speed}
            raw, info = el_tts(vid, part, model, st, language_code="zh", budget=budget, tag=tag)
            if raw is None and info.get("http") in (400, 422) and "speed" in json.dumps(info.get("detail"), ensure_ascii=False).lower():
                st = {"stability": 0.5, "similarity_boost": 0.75}
                raw, info = el_tts(vid, part, model, st, language_code="zh", budget=budget, tag=tag + "（不帶 speed 重試）")
        else:
            st = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True, "speed": speed}
            raw, info = el_tts(vid, part, model, st, budget=budget, tag=tag)
        billed += info.get("billed") or 0
        if raw is None:
            return None, {"error": {"http": info.get("http"), "detail": info.get("detail")}, "billed": billed, "segments": log}
        x = V.decode(raw)
        s0, e0 = V.speech_bounds(x)
        rec = {"text": part, "gap_after_ms": gap, "raw": f"review/G3/el/library/raw/{raw.name}", "settings": st,
               "raw_head_silence_ms": round(s0 / V.SR * 1000), "raw_tail_silence_ms": round((len(x) - e0) / V.SR * 1000),
               "cached": info.get("cached"), "billed": info.get("billed")}
        x, clicks = V.declick(x)
        rec["declicked"] = clicks
        if len(segs) > 1:
            a, b = V.speech_bounds(x)
            x = V.fade_edges(x[max(0, a - 480):min(len(x), b + int(0.08 * V.SR))], fin_ms=10, fout_ms=20)
        if gap and i < len(segs) - 1:
            x = np.concatenate([x, np.zeros(int(gap / 1000 * V.SR), dtype=np.float32)])
        chunks.append(x)
        log.append(rec)
    x = np.concatenate(chunks)
    if telephone:
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, [300, 3400], btype="band", fs=V.SR, output="sos")
        x = sosfiltfilt(sos, x).astype(np.float32)
    return x.astype(np.float32), {"billed": billed, "segments": log}


def master_write(x: np.ndarray, path: Path) -> dict:
    y, minfo = V.master(x, target=-18.0, tp_max=-1.5, head_ms=120, tail_ms=250, short_s=3.0)
    V.write_wav(path, y)
    return minfo


SAMPLE_LOG = OUT / "samples.json"


def load_samples() -> dict:
    return json.loads(SAMPLE_LOG.read_text("utf-8")) if SAMPLE_LOG.exists() else {"samples": {}}


def save_samples(S: dict) -> None:
    SAMPLE_LOG.write_text(json.dumps(S, ensure_ascii=False, indent=1), "utf-8")


def items_of(role: str, plan: dict, with_tone: bool = False) -> list[dict]:
    """這個角色要念的項目：劇本台詞（替身字照 pronounce.json）＋補念檢查詞的片段；with_tone＝加「紙燈節」聲調對照。"""
    r = R()
    out = []
    for lid in plan["lines"]:
        t = r.LINES[lid]["text"]
        out.append({"item": lid, "kind": "line", "line_id": lid, "text": t,
                    "syn_el": V.apply_pronounce(t, r.PRON, "elevenlabs", lid),
                    "speed": plan.get("speed_line", {}).get(lid, plan["speed"]), "gap": plan.get("gap_line", {}).get(lid)})
    for fid, t, why in plan.get("frames", []):
        out.append({"item": fid, "kind": "frame", "line_id": None, "text": t, "why": why,
                    "syn_el": V.apply_pronounce(t, r.PRON, "elevenlabs"), "speed": plan["speed"], "gap": None})
    if with_tone and plan.get("tone"):
        lid = plan["tone"]
        t = r.LINES[lid]["text"]
        out.append({"item": f"tone_{lid}_orig", "kind": "tone_line", "line_id": lid, "text": t, "syn_el": t,
                    "speed": plan["speed"], "gap": None, "why": "原字（不套替身字）念整句"})
        for k, syn in (("orig", "紙燈節。"), ("sub", "紙登結。"), ("wrong", "紙等街。")):
            out.append({"item": f"tone_frame_{k}", "kind": "tone_frame", "line_id": None,
                        "text": "紙等街。" if k == "wrong" else "紙燈節。", "syn_el": syn, "speed": plan["speed"], "gap": None,
                        "why": {"orig": "原字", "sub": "替身字（pronounce.json 全域表）", "wrong": "錯誤讀音對照（燈三聲、節一聲＝使用者聽到的「只等街」）"}[k]})
    return out


def sample_path(role: str, tag: str, item: str) -> Path:
    return SAMPLES / role / f"{role}__{tag}__{item}.wav"


def render_edge(role: str, plan: dict, S: dict, with_tone: bool) -> None:
    for it in items_of(role, plan, with_tone):
        p = sample_path(role, "edge", it["item"])
        key = str(p.relative_to(OUT))
        if key in S["samples"] and p.exists():
            continue
        if it["kind"] in ("tone_line",):
            continue      # edge 基準整句已含原字（edge 的替身字另計）；聲調對照只做短框句
        text_for_edge = it["syn_el"] if it["kind"] == "tone_frame" else it["text"]
        if it["kind"] == "tone_frame":
            # 短框句：edge 用同一角色的一般參數，直接念指定寫法（不再套替身字）
            r = R()
            spec = r.B.resolve_spec(r.CAST, plan["cast"], "tone_frame", None)
            s = {k: spec[k] for k in ("service", "voice", "rate", "pitch")}
            V.RAW_DIR = EDGE_RAW
            raw, _ = V.synth_raw(s, text_for_edge, purpose=f"{PURPOSE} edge 聲調對照")
            x, _ = V.declick(V.decode(raw))
            meta = {"service": "edge", "specs": [s], "synth_text": text_for_edge}
        else:
            x, meta = edge_render(plan["cast"], it["item"], it["text"], it["line_id"])
        minfo = master_write(x, p)
        S["samples"][key] = {"role": role, "cand": "edge", "voice": "edge 基準（casting.json）", "model": "edge-tts 7.3.1",
                             "item": it["item"], "kind": it["kind"], "line_id": it["line_id"], "text": it["text"],
                             "synth_text": meta["synth_text"], "edge": meta, "master": minfo}
        save_samples(S)
        print("edge", key)


def render_el(role: str, plan: dict, cand: dict, model: str, S: dict, budget: int, with_tone: bool, lines_only: bool = False) -> None:
    mtag = "v2" if model == "eleven_multilingual_v2" else "v3"
    for it in items_of(role, plan, with_tone):
        if lines_only and it["kind"] != "line":
            continue
        p = sample_path(role, f"{cand['cand_id'].split('_', 1)[1]}_{mtag}", it["item"])
        key = str(p.relative_to(OUT))
        if key in S["samples"] and (p.exists() or S["samples"][key].get("error")):
            continue
        tag = f"{plan['zh']} {cand['name'].split(' - ')[0]} {mtag} {it['item']}"
        x, info = el_render(cand["voice_id"], it["syn_el"], model, it["speed"], it["gap"], budget, tag,
                            telephone=plan.get("telephone", False))
        rec = {"role": role, "cand": cand["cand_id"], "voice": cand["name"], "voice_id": cand["voice_id"], "model": model,
               "item": it["item"], "kind": it["kind"], "line_id": it["line_id"], "text": it["text"], "synth_text": it["syn_el"],
               "speed": it["speed"], "gap_ms": it["gap"], "seed": SEED, "output_format": FMT,
               "telephone": plan.get("telephone", False), "el": info}
        if x is None:
            rec["error"] = info["error"]
            S["samples"][key] = rec
            save_samples(S)
            print("失敗", key, info["error"])
            continue
        rec["master"] = master_write(x, p)
        S["samples"][key] = rec
        save_samples(S)
        print(f"{key}  計費 {info['billed']}  累計 {ledger()['spent']}")


def cmd_render(args) -> None:
    C = json.loads(CANDS.read_text("utf-8"))
    S = load_samples()
    groups = set(args.group.split(","))
    roles = [r for r in ROLE_PLAN if ROLE_PLAN[r]["group"] in groups and (not args.roles or r in args.roles.split(","))]
    try:
        for role in roles:
            plan = ROLE_PLAN[role]
            render_edge(role, plan, S, with_tone=True)
            for cand in C["roles"][role]["candidates"]:
                render_el(role, plan, cand, "eleven_multilingual_v2", S, args.budget, with_tone=True)
    except BudgetStop as e:
        print("停止：", e)
        S.setdefault("stops", []).append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "why": str(e)})
        save_samples(S)
    print("帳本已用", ledger()["spent"])


# ---------------------------------------------------------------- 5. 量測
METRICS = OUT / "metrics.json"


def load_metrics() -> dict:
    return json.loads(METRICS.read_text("utf-8")) if METRICS.exists() else {"samples": {}}


def cmd_measure(args) -> None:
    S = load_samples()["samples"]
    M = load_metrics()
    todo = []
    for key, s in S.items():
        if s.get("error"):
            continue
        p = OUT / key
        if not p.exists():
            continue
        mt = p.stat().st_mtime
        old = M["samples"].get(key)
        if old and old.get("_mtime") == mt and (old.get("transcript") or args.no_transcribe):
            continue
        x = V.read_wav(p)
        m = V.measure(p, s["text"]) | formants(x)
        m["_mtime"] = mt
        m["raw_head_silence_ms"] = s.get("master", {}).get("raw_head_silence_ms")
        m["raw_tail_silence_ms"] = s.get("master", {}).get("raw_tail_silence_ms")
        if s.get("el", {}).get("segments"):
            m["raw_segments_silence_ms"] = [[g["raw_head_silence_ms"], g["raw_tail_silence_ms"]] for g in s["el"]["segments"]]
        M["samples"][key] = m
        todo.append((p, s["text"], V.strip_breaks(s["synth_text"])))
        print("量測", key, m["f0_median"], m["rate_cps"], m["F1_median"], m["F2_median"])
    if todo and not args.no_transcribe:
        tc = V.transcribe_compare(todo)
        for p, _, _ in todo:
            M["samples"][str(p.relative_to(OUT))]["transcript"] = tc[str(p)]
    M["_說明"] = ("每個樣本（母帶後 48 kHz／16-bit）的量測：vo_lib.measure（整合響度、真峰值、削波、頭尾靜音、毛語速＝字數÷語音區間、"
                 "淨語速＝扣掉 ≥250 ms 停頓、rate_cps_net_r＝驗收者算法（−40 dB、≥200 ms）、句中停頓 pauses_ms（−35 dB、≥150 ms）、"
                 "F0 中位與 p10–p90）＋共振峰（有聲格 LPC Burg，上限 5500 Hz）＋兩個轉寫模型（faster-whisper small、large-v3-turbo）"
                 "的 CER／PER 與檢查詞（vo_lib.compare：逐字對齊；參考讀音取合成用文字；台灣讀音表）。raw_*_silence_ms＝合成器原始檔頭尾靜音。")
    METRICS.write_text(json.dumps(M, ensure_ascii=False, indent=1), "utf-8")
    print("量測完成", len(todo))


# ---------------------------------------------------------------- 6. 依客觀條件排名 → eleven_v3
def cand_stats(role: str, cand_id: str, model: str, S: dict, M: dict) -> dict:
    plan = ROLE_PLAN[role]
    keys = [k for k, s in S.items() if s["role"] == role and s["cand"] == cand_id and s.get("model") == model
            and s["kind"] == "line" and not s.get("error")]
    flagged, cw_fail, pers, frames, rates = 0, 0, [], [], []
    lines = {}
    for k in keys:
        m = M["samples"].get(k)
        if not m or not m.get("transcript"):
            continue
        t = m["transcript"]
        if t["both_models_diff"]:
            flagged += 1
        cw_fail += sum(1 for mm in t["models"].values() for c in mm["checks"] if c["status"].startswith("不一致"))
        pers.append(t["per_min"])
        lid = S[k]["line_id"]
        lo, hi = plan.get("rate_line", {}).get(lid, plan["rate"])
        rates.append(0 if lo <= m["rate_cps"] <= hi else min(abs(m["rate_cps"] - lo), abs(m["rate_cps"] - hi)))
        frames.append(V.read_wav(OUT / k))
        lines[lid] = k
    f0 = None
    if frames:
        f0 = f0_stats(np.concatenate(frames))["f0_median"]
    return {"lines_measured": len(pers), "lines_flagged_both_models": flagged, "checkword_fail_count": cw_fail,
            "mean_per_min": round(float(np.mean(pers)), 3) if pers else None,
            "f0_pooled": f0, "f0_dist_semitones": round(semis(f0, plan["f0_target"]), 2) if f0 else None,
            "rate_outside_target_cps_mean": round(float(np.mean(rates)), 2) if rates else None, "files": lines}


RANK_RULE = ("排名（客觀、依序比較）：① 兩個轉寫模型都在同一處出現非同音差異的台詞數（少者優先）→ ② 檢查詞「不一致」次數（兩個模型合計）"
             "→ ③ 各句 PER（兩個模型取小）的平均 → ④ 合併 F0 中位與 F0 目標相差的半音數。")


def cmd_v3(args) -> None:
    C = json.loads(CANDS.read_text("utf-8"))
    S = load_samples()
    M = load_metrics()
    groups = set(args.group.split(","))
    try:
        for role, plan in ROLE_PLAN.items():
            if plan["group"] not in groups or (args.roles and role not in args.roles.split(",")):
                continue
            rc = C["roles"][role]
            stats = []
            for cand in rc["candidates"]:
                st = cand_stats(role, cand["cand_id"], "eleven_multilingual_v2", S["samples"], M)
                cand["v2_stats"] = st
                if st["lines_measured"]:
                    stats.append((st["lines_flagged_both_models"], st["checkword_fail_count"], st["mean_per_min"],
                                  st["f0_dist_semitones"] or 99, cand["cand_id"]))
            stats.sort()
            top = [s[-1] for s in stats[:2]]
            rc["v3"] = {"rule": RANK_RULE, "ranking": [list(s) for s in stats], "top2": top}
            CANDS.write_text(json.dumps(C, ensure_ascii=False, indent=1), "utf-8")
            print(plan["zh"], "v3 前兩名", top)
            for cand in rc["candidates"]:
                if cand["cand_id"] in top:
                    render_el(role, plan, cand, "eleven_v3", S, args.budget, with_tone=False, lines_only=True)
    except BudgetStop as e:
        print("停止：", e)
        S.setdefault("stops", []).append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "why": str(e)})
        save_samples(S)
    CANDS.write_text(json.dumps(C, ensure_ascii=False, indent=1), "utf-8")
    print("帳本已用", ledger()["spent"])


# ---------------------------------------------------------------- 7. 「紙燈節」聲調（F0 走勢）
TONE_RULE = ("定位：large-v3-turbo 轉寫加字級時間戳（faster-whisper word_timestamps），把轉寫逐字對齊到合成用文字，取「紙燈節」三個字的時間；"
             "再在這個時間窗（前後各放寬 80 ms）裡找 ≥50 ms 的有聲段（parselmouth 自相關，10 ms；音高範圍依該檔 F0 中位自動設定：下限 0.6 倍、上限 2 倍；高於中位 1.7 倍的格減半、低於 0.55 倍的格加倍，修正八度錯誤）："
             "紙（zh）、燈（d）、節（j）的聲母都是清音，正好三段時直接用；多於三段時，每個字取與時間戳重疊最多的一段；少於三段（或某段有聲格不足 50 ms）時改用時間戳範圍內的有聲格。"
             "每個字：起點＝前 20% 有聲格中位數、終點＝後 20% 中位數、最低點＝三點移動中位數的最小值。"
             "判定：燈＝一聲（終點／起點 ≥ 0.90，沒有三聲、四聲那種明顯下降；且平均 F0 ≥ 紙的 1.05 倍，紙是三聲、接一聲時讀低的半三聲）；"
             "節＝二聲（終點／最低點 ≥ 1.08，且最低點落在前 70%；台灣華語二聲常是先略降再上揚）。"
             "另以同一聲線念「紙等街。」（燈三聲、節一聲＝使用者聽到的「只等街」）作對照。"
             "G3 tone_check_ting.json 的 0.95–1.05 高平門檻是單音節框句用的；本句「燈」夾在低的「紙」與「節」之間，edge 基準的「燈」也會上揚到 1.19，所以只要求「不下降且比紙高」。")
_WT: dict = {}


def word_chars(path: Path) -> list[tuple[str, float, float]]:
    """large-v3-turbo 轉寫＋字級時間戳 → [(字, 起, 訖)]（詞的時間平均分給每個字）。"""
    import subprocess
    from faster_whisper import WhisperModel
    if "m" not in _WT:
        _WT["m"] = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    segs, _ = _WT["m"].transcribe(np.frombuffer(pcm, dtype=np.float32), language="zh", beam_size=5,
                                  initial_prompt="以下是繁體中文的台灣華語。", word_timestamps=True)
    out = []
    for sg in segs:
        for w in sg.words or []:
            t = V.PUNCT_RE.sub("", V._to_trad(w.word))
            for i, c in enumerate(t):
                out.append((c, w.start + (w.end - w.start) * i / len(t), w.start + (w.end - w.start) * (i + 1) / len(t)))
    return out


def syl_stats(f: np.ndarray, ts: np.ndarray, a: float, b: float) -> dict | None:
    sel = (ts >= a) & (ts <= b) & (f > 0)
    seg = f[sel]
    if len(seg) < 5:          # 少於 50 ms 有聲格不量
        return None
    n = max(1, len(seg) // 5)
    st, en = float(np.median(seg[:n])), float(np.median(seg[-n:]))
    sm = np.array([np.median(seg[max(0, i - 1):i + 2]) for i in range(len(seg))])
    mi = int(np.argmin(sm))
    return {"t0": round(float(ts[sel][0]), 3), "t1": round(float(ts[sel][-1]), 3), "mean_hz": round(float(seg.mean()), 1),
            "start_hz": round(st, 1), "end_hz": round(en, 1), "min_hz": round(float(sm[mi]), 1),
            "min_pos": round(mi / max(1, len(seg) - 1), 2), "end_over_start": round(en / st, 3),
            "end_over_min": round(en / float(sm[mi]), 3), "contour_hz_20ms": [round(float(q)) for q in seg[::2]]}


def zdj(path: Path, synth_text: str) -> dict:
    import difflib
    import parselmouth
    ref = V.PUNCT_RE.sub("", V.strip_breaks(synth_text))
    k = next((ref.find(t) for t in ("紙燈節", "紙登結", "紙等街") if t in ref), -1)
    if k < 0:
        return {"error": "合成用文字沒有紙燈節"}
    chars = word_chars(path)
    hyp = "".join(c for c, _, _ in chars)
    mp = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for d in range(i2 - i1):
                mp[i1 + d] = j1 + d
    res = {"whisper_turbo_words": hyp}
    if not all(k + d in mp for d in range(3)):
        return res | {"error": f"轉寫無法逐字對齊到「{ref[k:k + 3]}」"}
    spans = [chars[mp[k + d]][1:] for d in range(3)]
    res["whisper_spans"] = [[round(a, 3), round(b, 3)] for a, b in spans]
    snd = parselmouth.Sound(str(path))
    f_all = snd.to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700).selected_array["frequency"]
    med = float(np.median(f_all[f_all > 0])) if (f_all > 0).any() else 200.0
    floor, ceil = max(60.0, 0.6 * med), min(800.0, 2.0 * med)
    p = snd.to_pitch_ac(time_step=0.01, pitch_floor=floor, pitch_ceiling=ceil)
    f, ts = p.selected_array["frequency"].copy(), p.xs()
    # 八度錯誤修正：高於檔案中位數 1.7 倍的格減半、低於 0.55 倍的格加倍
    hi, lo = (f > 1.7 * med), (f > 0) & (f < 0.55 * med)
    f[hi] /= 2
    f[lo] *= 2
    res["octave_fixed_frames"] = int(hi.sum() + lo.sum())
    res["pitch_range_hz"] = [round(floor), round(ceil)]
    w0, w1 = spans[0][0] - 0.08, spans[2][1] + 0.08
    isl, i = [], 0
    while i < len(f):
        if f[i] > 0 and w0 <= ts[i] <= w1:
            j = i
            while j + 1 < len(f) and f[j + 1] > 0 and ts[j + 1] <= w1:
                j += 1
            if (j - i + 1) * 10 >= 50:
                isl.append((float(ts[i]) - 0.005, float(ts[j]) + 0.005))
            i = j + 1
        else:
            i += 1
    res["islands_in_window"] = len(isl)
    if len(isl) == 3:
        use, how = isl, "有聲段正好 3 段"
    elif len(isl) > 3:
        use, taken = [], set()
        for a, b in spans:
            ov = [(max(0, min(b, y) - max(a, x)), n) for n, (x, y) in enumerate(isl) if n not in taken]
            best = max(ov)[1] if ov else None
            if best is None:
                break
            taken.add(best)
            use.append(isl[best])
        how = "有聲段多於 3 段：取與字時間戳重疊最多者"
    else:
        use, how = spans, "有聲段少於 3 段：用字時間戳範圍"
    res["method"] = how
    st = [syl_stats(f, ts, a, b) for a, b in use]
    if (any(x is None for x in st) or len(st) < 3) and use is not spans:
        st = [syl_stats(f, ts, a, b) for a, b in spans]
        res["method"] += "（有聲段太短，改用字時間戳範圍）"
    if any(x is None for x in st) or len(st) < 3:
        return res | {"error": "有聲格不足，無法量測"}
    zhi, deng, jie = st
    res |= {"紙": zhi, "燈": deng, "節": jie, "燈_end_over_start": deng["end_over_start"],
            "燈_over_紙_mean": round(deng["mean_hz"] / zhi["mean_hz"], 3), "節_end_over_min": jie["end_over_min"],
            "節_min_pos": jie["min_pos"]}
    res["燈_一聲"] = bool(deng["end_over_start"] >= 0.90 and res["燈_over_紙_mean"] >= 1.05)
    res["節_二聲"] = bool(jie["end_over_min"] >= 1.08 and jie["min_pos"] <= 0.7)
    res["pass"] = res["燈_一聲"] and res["節_二聲"]
    return res


def wave_sim(a: np.ndarray, b: np.ndarray) -> dict:
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    return {"corr": round(float(np.corrcoef(a, b)[0, 1]), 4),
            "residual_db": round(float(20 * np.log10(np.sqrt(np.mean((a - b) ** 2)) / np.sqrt(np.mean(a ** 2)) + 1e-9)), 1),
            "samples": [int(len(a)), int(len(b))]}


def asr_word(m: dict | None, word: str = "紙燈節") -> dict:
    if not m or not m.get("transcript"):
        return {"status": "未轉寫"}
    st = {k: next((c["status"] for c in v["checks"] if c["word"] == word), "（句中無此詞）") for k, v in m["transcript"]["models"].items()}
    hyp = {k: v["hyp_trad"] for k, v in m["transcript"]["models"].items()}
    ok = all(s in ("轉寫一致", "同音轉寫（讀音一致）") for s in st.values())
    return {"status_by_model": st, "hyp_by_model": hyp, "both_models_ok": ok}


def cmd_tone(args) -> None:
    S = load_samples()["samples"]
    M = load_metrics()["samples"]
    TONE.mkdir(parents=True, exist_ok=True)
    summary = {"_說明": TONE_RULE, "rows": []}
    for role, plan in ROLE_PLAN.items():
        lid = plan.get("tone") or ("a3_c008_01" if role == "lin" else None)
        if not lid:
            continue
        cands = sorted({(s["cand"], s.get("model")) for s in S.values() if s["role"] == role and not s.get("error")})
        for cand, model in cands:
            mtag = "edge" if cand == "edge" else ("v2" if model == "eleven_multilingual_v2" else "v3")
            def k_of(item):
                return next((k for k, s in S.items() if s["role"] == role and s["cand"] == cand and s.get("model") == model
                             and s["item"] == item and not s.get("error")), None)
            out = {"role": role, "role_zh": plan["zh"], "cand": cand, "model": model, "line": lid,
                   "voice": next(s["voice"] for s in S.values() if s["role"] == role and s["cand"] == cand)}
            for label, item in (("整句（替身字，正式管線）", lid), ("整句（原字）", f"tone_{lid}_orig"),
                                ("短框句 紙燈節（原字）", "tone_frame_orig"), ("短框句 紙登結（替身字）", "tone_frame_sub"),
                                ("短框句 紙等街（錯誤讀音對照）", "tone_frame_wrong")):
                k = k_of(item)
                if not k:
                    continue
                f = zdj(OUT / k, S[k]["synth_text"])
                out[label] = {"file": k, "synth_text": S[k]["synth_text"], "f0": f,
                              "asr": asr_word(M.get(k), "紙燈節") if not item.endswith("wrong") else
                              {"hyp_by_model": {kk: vv["hyp_trad"] for kk, vv in (M.get(k) or {}).get("transcript", {}).get("models", {}).items()}}}
            w = out.get("短框句 紙等街（錯誤讀音對照）", {}).get("f0", {})
            for label in ("短框句 紙燈節（原字）", "短框句 紙登結（替身字）"):
                f = out.get(label, {}).get("f0", {})
                if f.get("燈") and w.get("燈"):
                    f["燈_over_錯誤對照等_mean"] = round(f["燈"]["mean_hz"] / w["燈"]["mean_hz"], 3)
            (TONE / f"{role}__{cand.split('_', 1)[-1]}_{mtag}.json").write_text(
                json.dumps({"_說明": TONE_RULE} | out, ensure_ascii=False, indent=1), "utf-8")
            row = {"role": role, "role_zh": plan["zh"], "cand": cand, "voice": out["voice"], "model": mtag,
                   "file": f"tone_checks/{role}__{cand.split('_', 1)[-1]}_{mtag}.json"}
            for label in ("整句（替身字，正式管線）", "整句（原字）", "短框句 紙燈節（原字）", "短框句 紙登結（替身字）"):
                if label in out:
                    f, a = out[label]["f0"], out[label]["asr"]
                    row[label] = {"燈_end_over_start": f.get("燈_end_over_start"), "燈_over_紙_mean": f.get("燈_over_紙_mean"),
                                  "節_end_over_min": f.get("節_end_over_min"), "節_min_pos": f.get("節_min_pos"),
                                  "f0_pass": f.get("pass"), "error": f.get("error"), "method": f.get("method"),
                                  "islands": f.get("islands_in_window"), "asr_both_ok": a.get("both_models_ok"),
                                  "hyp": a.get("hyp_by_model"), "燈_over_錯誤對照等_mean": f.get("燈_over_錯誤對照等_mean")}
            summary["rows"].append(row)
            print(role, cand, mtag, {k: (v.get("f0_pass"), v.get("asr_both_ok")) for k, v in row.items() if isinstance(v, dict) and "f0_pass" in v})
    # 原字／替身字／錯誤寫法的波形相似度（同聲線、同參數、同 seed）＋同一句重複呼叫的決定性對照
    ident = {}
    for role in ("narrator", "zhezhe"):
        for cand, model in sorted({(s["cand"], s.get("model")) for s in S.values() if s["role"] == role and s["cand"] != "edge"}):
            ks = {s["item"]: k for k, s in S.items() if s["role"] == role and s["cand"] == cand and s.get("model") == model and not s.get("error")}
            def rawx(item):
                return V.decode(RAW / S[ks[item]]["el"]["segments"][0]["raw"].split("/")[-1])
            if not all(i in ks for i in ("tone_frame_orig", "tone_frame_sub", "tone_frame_wrong")):
                continue
            o = rawx("tone_frame_orig")
            lid = ROLE_PLAN[role]["tone"]
            ident[f"{cand}｜{'v2' if model.endswith('v2') else 'v3'}"] = {
                "紙燈節 vs 紙登結": wave_sim(o, rawx("tone_frame_sub")), "紙燈節 vs 紙等街": wave_sim(o, rawx("tone_frame_wrong")),
                f"{lid} 原字 vs 替身字": wave_sim(rawx(f"tone_{lid}_orig"), rawx(lid)) if f"tone_{lid}_orig" in ks and lid in ks else None}
    det = json.loads((TONE / "determinism_door.json").read_text("utf-8")) if (TONE / "determinism_door.json").exists() else None
    summary["waveform_identity"] = {"_說明": "合成器原始檔（解碼後）兩兩比較：corr＝相關係數、residual_db＝差值能量相對原訊號（dB）。"
                                            "determinism＝Door Chow「紙燈節。」同文字、同參數、同 seed 重複呼叫一次的對照（量合成器本身的變動）。",
                                    "pairs": ident, "determinism_same_text": det}
    (TONE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), "utf-8")
    # 讀音提案（不改 pronounce.json）
    prop = {"_說明": "ElevenLabs 專用讀音提案（只寫在本資料夾，不改 audio/vo/pronounce.json）。格式同 pronounce.json 的 elevenlabs 服務表："
                     "鍵＝字幕原字、值＝送進 ElevenLabs 的文字。全域表已有 紙燈節→紙登結；若要讓 ElevenLabs 念原字，服務表寫 紙燈節→紙燈節。"
                     "判定規則（客觀）：某寫法在某候選「整句」兩個轉寫模型都沒有非同音差異（ASR 通過），且整句與短框句的 F0 走勢都通過（燈高平、節上揚）"
                     "＝該候選通過。聽感未驗證。", "rule": TONE_RULE, "elevenlabs": {}, "evidence": {}}
    ev = {}
    for row in summary["rows"]:
        if row["model"] == "edge":
            continue
        full_sub, full_orig = row.get("整句（替身字，正式管線）", {}), row.get("整句（原字）", {})
        fr_sub, fr_orig = row.get("短框句 紙登結（替身字）", {}), row.get("短框句 紙燈節（原字）", {})
        ev[f"{row['role_zh']}｜{row['voice']}｜{row['model']}"] = {
            "替身字 紙登結": {"整句 ASR": full_sub.get("asr_both_ok"), "整句 F0": full_sub.get("f0_pass"), "短框句 F0": fr_sub.get("f0_pass"),
                         "pass": bool(full_sub.get("asr_both_ok") and full_sub.get("f0_pass") and fr_sub.get("f0_pass"))},
            "原字 紙燈節": {"整句 ASR": full_orig.get("asr_both_ok"), "整句 F0": full_orig.get("f0_pass"), "短框句 F0": fr_orig.get("f0_pass"),
                        "pass": bool(full_orig.get("asr_both_ok") and full_orig.get("f0_pass") and fr_orig.get("f0_pass")),
                        "tested": bool(full_orig) or bool(fr_orig)}}
    prop["evidence"]["紙燈節"] = ev
    # 依模型分開計數
    cnt = {}
    for key, e in ev.items():
        mt = key.rsplit("｜", 1)[-1]
        c = cnt.setdefault(mt, {"tested_candidates": 0, "原字通過": 0, "替身字通過": 0})
        if e["原字 紙燈節"]["tested"]:
            c["tested_candidates"] += 1
            c["原字通過"] += int(e["原字 紙燈節"]["pass"])
            c["替身字通過"] += int(e["替身字 紙登結"]["pass"])
    prop["counts"] = {"紙燈節": cnt}
    v2pairs = {k: v for k, v in ident.items() if k.endswith("v2")}
    det_v2 = (det or {}).get("v2", {}).get("corr")
    min_pair = min((p["corr"] for v in v2pairs.values() for p in v.values() if p), default=None)
    prop["multilingual_v2_waveform_identity"] = {"pairs": v2pairs, "same_text_repeat_corr": det_v2, "min_pair_corr": min_pair}
    txt = []
    if min_pair is not None and det_v2 is not None:
        txt.append(f"eleven_multilingual_v2：同聲線、同 seed 念「紙燈節。」「紙登結。」「紙等街。」與整句原字／替身字，解碼後波形兩兩相關 ≥ {min_pair}"
                   f"（同一句重複呼叫的相關 {det_v2}），長度逐樣本相同 → 換寫法（包括聲調不同的「等」「街」）對 v2 的讀音沒有可量測的作用；"
                   "v2 的「紙燈節」讀得對不對，取決於聲線與 seed，不取決於替身字。")
    for mt, c in cnt.items():
        txt.append(f"{mt}：整句 ASR＋整句與短框句 F0 全部通過的候選，原字 {c['原字通過']}／{c['tested_candidates']}、替身字 {c['替身字通過']}／{c['tested_candidates']}。")
    v3c = cnt.get("v3", {})
    if v3c.get("tested_candidates") and v3c["原字通過"] > v3c["替身字通過"]:
        prop["elevenlabs"] = {"紙燈節": "紙燈節"}
        txt.append("依規則（原字通過數 > 替身字通過數才改）：elevenlabs 服務表加 紙燈節→紙燈節。注意 v3 同文字重複呼叫結果不同（決定性對照 corr "
                   f"{(det or {}).get('v3', {}).get('corr')}），通過與否可能是單次抽樣。")
    else:
        prop["elevenlabs"] = {}
        txt.append("依規則（原字通過數 > 替身字通過數才改）：維持全域替身字「紙登結」，elevenlabs 服務表不新增；"
                   "v3 同文字重複呼叫結果不同（決定性對照 corr " f"{(det or {}).get('v3', {}).get('corr')}），單次結果只代表一次抽樣。")
    prop["proposal_text"] = "".join(txt)
    prop["other_words"] = ("燈籠→登籠、折折→哲哲、阿樂→阿勒、喪屍煙彈→桑師煙蛋：本輪只用全域替身字合成（正式管線的做法），"
                           "沒有另測原字；各候選的轉寫檢查結果見 metrics.json 與 transcripts.md。119：劇本原字直接送 ElevenLabs，結果見執勤人員 a5_c006_01。")
    (OUT / "proposed_pronounce_el.json").write_text(json.dumps(prop, ensure_ascii=False, indent=1), "utf-8")
    print(prop.get("proposal_text"))


# ---------------------------------------------------------------- 8. 報告
def _fmt(v, nd=1):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def model_tag(s: dict) -> str:
    return "edge" if s["cand"] == "edge" else ("v2" if s.get("model") == "eleven_multilingual_v2" else "v3")


def pooled(keys: list[str]) -> dict:
    if not keys:
        return {}
    x = np.concatenate([V.read_wav(OUT / k) for k in keys])
    return f0_stats(x) | formants(x)


def role_rows(role: str, S: dict, M: dict, tone_rows: list) -> list[dict]:
    plan = ROLE_PLAN[role]
    combos = []
    for k, s in S.items():
        if s["role"] != role:
            continue
        c = (s["cand"], model_tag(s))
        if c not in combos:
            combos.append(c)
    order = {"edge": 0, "v2": 1, "v3": 2}
    combos.sort(key=lambda c: (order[c[1]], c[0]))
    rows = []
    for cand, mt in combos:
        ks = [k for k, s in S.items() if s["role"] == role and s["cand"] == cand and model_tag(s) == mt and s["kind"] == "line"]
        ok = [k for k in ks if not S[k].get("error") and k in M]
        errs = [S[k]["error"] for k in ks if S[k].get("error")]
        p = pooled(ok)
        per_line = []
        flagged, cwf = 0, 0
        for k in ok:
            m, s = M[k], S[k]
            t = m.get("transcript") or {}
            ms = t.get("models", {})
            if t.get("both_models_diff"):
                flagged += 1
            cwf += sum(1 for mm in ms.values() for c in mm["checks"] if c["status"].startswith("不一致"))
            per_line.append({"line": s["line_id"], "file": f"review/G3/el/library/{k}", "seconds": m["seconds"],
                             "rate_cps": m["rate_cps"], "rate_cps_net": m["rate_cps_net"], "rate_cps_net_r": m["rate_cps_net_r"],
                             "pauses_ms": m["pauses_ms"], "f0_median": m["f0_median"], "f0_p10": m["f0_p10"], "f0_p90": m["f0_p90"],
                             "F1": m.get("F1_median"), "F2": m.get("F2_median"), "lufs": m["integrated_lufs"],
                             "dbtp": m["true_peak_dbtp"], "clip": m["clipped_samples"],
                             "raw_head": m.get("raw_head_silence_ms"), "raw_tail": m.get("raw_tail_silence_ms"),
                             "raw_segments": m.get("raw_segments_silence_ms"),
                             "cer": {kk: vv["cer"] for kk, vv in ms.items()}, "per": {kk: vv["per"] for kk, vv in ms.items()},
                             "hyp": {kk: vv["hyp_trad"] for kk, vv in ms.items()}, "verdict": t.get("verdict"),
                             "checks": {kk: [f"{c['word']}：{c['status']}" for c in vv["checks"]] for kk, vv in ms.items()},
                             "pause_spikes": m.get("pause_spikes"), "speed": s.get("speed"), "head_ms": m["head_silence_ms"],
                             "tail_ms": m["tail_silence_ms"]})
            if s["line_id"] == "a2_c002_01":
                per_line[-1]["yi_first_syllable"] = V.first_syllable_rise(V.read_wav(OUT / k))
        tone = next((t for t in tone_rows if t["cand"] == cand and t["model"] == mt), None)
        s0 = S[ks[0]] if ks else {}
        rows.append({"cand": cand, "model": mt, "voice": s0.get("voice"), "voice_id": s0.get("voice_id"),
                     "model_id": s0.get("model"), "pooled": p, "lines": per_line, "errors": errs,
                     "lines_flagged_both_models": flagged, "checkword_fail_count": cwf,
                     "mean_per_min": round(float(np.mean([M[k]["transcript"]["per_min"] for k in ok if M[k].get("transcript")])), 3)
                     if ok and all(M[k].get("transcript") for k in ok) else None,
                     "f0_dist_semitones": round(semis(p["f0_median"], plan["f0_target"]), 2) if p.get("f0_median") else None,
                     "tone": tone})
    return rows


def write_transcripts(S: dict, M: dict) -> None:
    L = ["# ElevenLabs 台灣聲線庫選角｜逐字稿（兩個轉寫模型）", "",
         "- 轉寫：faster-whisper `small` 與 `large-v3-turbo`（int8、CPU、beam 5、提示詞「以下是繁體中文的台灣華語。」），轉成台灣正體後與劇本原文逐字對齊（`vo_lib.compare`）。",
         "- CER＝字錯率；PER＝拼音（含聲調）錯率：字相同不算錯、同音字不算錯；參考讀音取合成用文字（已套替身字）。",
         "- 「需複查」＝兩個模型在同一處都出現非同音差異。一／不 變調轉寫看不出，一律未驗證。聽感未驗證。", ""]
    for role, plan in ROLE_PLAN.items():
        ks = [k for k, s in S.items() if s["role"] == role and not s.get("error") and k in M]
        if not ks:
            continue
        L += [f"## {plan['zh']}（{role}）", ""]
        for k in sorted(ks, key=lambda k: (S[k]["item"], {"edge": 0, "v2": 1, "v3": 2}[model_tag(S[k])], S[k]["cand"])):
            s, m = S[k], M[k]
            t = m.get("transcript")
            L.append(f"### `{k}`")
            L.append(f"- 聲線：{s['voice']}｜模型：{s.get('model')}｜項目：{s['item']}（{s['kind']}）")
            L.append(f"- 劇本原文：{s['text']}")
            L.append(f"- 合成用文字：{V.strip_breaks(s['synth_text'])}")
            if not t:
                L += ["- （未轉寫）", ""]
                continue
            for mn, mm in t["models"].items():
                diffs = "；".join(f"{d['ref'] or '∅'}→{d['hyp'] or '∅'}（{d['kind']}）" for d in mm["diffs"]) or "無"
                checks = "、".join(f"{c['word']}：{c['status']}" for c in mm["checks"]) or "—"
                L.append(f"- **{mn}**：{mm['hyp_trad']}｜CER {mm['cer']}｜PER {mm['per']}｜差異：{diffs}｜檢查詞：{checks}")
            L += [f"- 判讀：{t['verdict']}", ""]
    (OUT / "transcripts.md").write_text("\n".join(L), "utf-8")


def write_listen(S: dict, C: dict) -> None:
    import html
    css = """
:root{--bg:#f7f5f0;--fg:#1f1d1a;--muted:#6b665d;--card:#ffffff;--line:#e2ddd2;--accent:#8a4b2a}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#171614;--fg:#ece8e1;--muted:#a39d92;--card:#22201d;--line:#3a3631;--accent:#e0a37e}}
:root[data-theme="dark"]{--bg:#171614;--fg:#ece8e1;--muted:#a39d92;--card:#22201d;--line:#3a3631;--accent:#e0a37e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 "PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.6rem;margin:.2em 0}h2{font-size:1.25rem;margin:2em 0 .4em;border-bottom:2px solid var(--accent);padding-bottom:.2em}
h3{font-size:1rem;margin:1.4em 0 .4em;color:var(--muted);font-weight:600}.note{color:var(--muted);font-size:.9rem}
nav a{color:var(--accent);margin-right:.8em;white-space:nowrap}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line)}
td,th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}th{font-weight:600;font-size:.85rem;color:var(--muted)}
td.v{width:38%;font-size:.9rem}audio{width:100%;min-width:180px;height:34px}.tag{display:inline-block;font-size:.75rem;padding:0 6px;border-radius:4px;border:1px solid var(--line);color:var(--muted);margin-left:4px}
.scroll{overflow-x:auto}
"""
    roles = [r for r in ROLE_PLAN if any(s["role"] == r for s in S.values())]
    out = ["<!doctype html><html lang='zh-Hant-TW'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>選角試聽</title><style>" + css + "</style></head><body><main>",
           "<h1>選角試聽</h1>",
           "<p class='note'>ElevenLabs 台灣華語聲線庫候選與 edge-tts 基準（casting.json 目前參數）。全部是同一套母帶處理（−18 LUFS、真峰值 ≤ −1.5 dBTP、48 kHz）。"
           "列出順序依篩選規則，不代表推薦；數據與方法見 INDEX.md。選擇性試聽用，Claude 聽不到聲音，聽感與台灣口音自然度未驗證。</p>",
           "<nav>" + "".join(f"<a href='#{r}'>{html.escape(ROLE_PLAN[r]['zh'])}</a>" for r in roles) + "</nav>"]
    order = {"edge": 0, "v2": 1, "v3": 2}
    for role in roles:
        plan = ROLE_PLAN[role]
        out.append(f"<h2 id='{role}'>{html.escape(plan['zh'])}</h2>")
        items = []
        for s in S.values():
            if s["role"] == role and s["item"] not in items:
                items.append(s["item"])
        for it in items:
            ss = sorted([(k, s) for k, s in S.items() if s["role"] == role and s["item"] == it],
                        key=lambda ks: (order[model_tag(ks[1])], ks[1]["cand"]))
            s0 = ss[0][1]
            label = {"line": s0.get("line_id"), "frame": "檢查詞片段", "tone_line": "原字整句（聲調對照）",
                     "tone_frame": "短框句（聲調對照）"}.get(s0["kind"], s0["kind"])
            text = s0["text"] if s0["kind"] != "tone_frame" else V.strip_breaks(s0["synth_text"])
            out.append(f"<h3>{html.escape(str(label))}｜{html.escape(text)}</h3><div class='scroll'><table>")
            out.append("<tr><th>聲線</th><th>播放</th></tr>")
            for k, s in ss:
                if s.get("error"):
                    out.append(f"<tr><td class='v'>{html.escape(s['voice'])}<span class='tag'>{model_tag(s)}</span></td>"
                               f"<td>合成失敗：HTTP {s['error'].get('http')}</td></tr>")
                    continue
                if s0["kind"] == "tone_frame" and model_tag(s) != "edge":
                    pass
                syn = V.strip_breaks(s["synth_text"])
                extra = f"<span class='tag'>念：{html.escape(syn)}</span>" if s["kind"] == "tone_frame" else ""
                out.append(f"<tr><td class='v'>{html.escape(s['voice'])}<span class='tag'>{model_tag(s)}</span>{extra}</td>"
                           f"<td><audio controls preload='none' src='{html.escape(k)}'></audio></td></tr>")
            out.append("</table></div>")
    out.append("</main></body></html>")
    (OUT / "listen.html").write_text("\n".join(out), "utf-8")


def cmd_report(args) -> None:
    C = json.loads(CANDS.read_text("utf-8"))
    S = load_samples()["samples"]
    M = load_metrics()["samples"]
    T = json.loads((TONE / "summary.json").read_text("utf-8"))["rows"] if (TONE / "summary.json").exists() else []
    Lg = ledger()
    P = json.loads(PROBE.read_text("utf-8"))
    VV = json.loads(VOICES.read_text("utf-8"))
    PV = json.loads((OUT / "previews.json").read_text("utf-8"))["voices"]
    prop = json.loads((OUT / "proposed_pronounce_el.json").read_text("utf-8")) if (OUT / "proposed_pronounce_el.json").exists() else {}
    table = {}
    for role in ROLE_PLAN:
        if any(s["role"] == role for s in S.values()):
            table[role] = role_rows(role, S, M, [t for t in T if t["role"] == role])
    for role, rc in C["roles"].items():
        rc["comparison"] = table.get(role, [])
    C["rank_rule_v3"] = RANK_RULE
    CANDS.write_text(json.dumps(C, ensure_ascii=False, indent=1), "utf-8")
    write_transcripts(S, M)
    write_listen(S, C)
    # 計費分類
    def stage(e):
        p = e["purpose"]
        return "探測（你好）" if "探測" in p else ("eleven_v3 試音" if e.get("model") == "eleven_v3" else "multilingual_v2 試音")
    by_stage = {}
    for e in Lg["entries"]:
        st = stage(e)
        by_stage.setdefault(st, {"calls": 0, "billed": 0, "text_chars": 0, "failed": 0})
        by_stage[st]["calls"] += 1
        by_stage[st]["billed"] += e["billed"] or 0
        by_stage[st]["text_chars"] += e["text_chars"]
        by_stage[st]["failed"] += 0 if e["http"] == 200 else 1
    fails = [e for e in Lg["entries"] if e["http"] != 200]
    # ---------------- 事實摘要（由數據計算）
    TS = json.loads((TONE / "summary.json").read_text("utf-8")) if (TONE / "summary.json").exists() else {}
    wi = TS.get("waveform_identity", {})
    v2c = [p["corr"] for k, v in wi.get("pairs", {}).items() if k.endswith("v2") for p in v.values() if p]
    v3c = [p["corr"] for k, v in wi.get("pairs", {}).items() if k.endswith("v3") for p in v.values() if p]
    det = wi.get("determinism_same_text") or {}
    facts = [f"- 聲線庫台灣華語 48 個＋描述提到台灣的 3 個，Starter「你好」實測 51／51 可用（含 free_users_allowed=false 的 17 個）。"]
    if v2c:
        facts.append(f"- eleven_multilingual_v2 固定 seed 時，「紙燈節。」「紙登結。」「紙等街。」以及整句原字／替身字的原始波形兩兩相關 {min(v2c)}–{max(v2c)}、長度逐樣本相同；"
                     f"同一句重複呼叫的相關 {det.get('v2', {}).get('corr')}。即換字（含聲調不同的「等」「街」）不改變 v2 的輸出。")
    if v3c:
        facts.append(f"- eleven_v3 同參數同 seed 重複呼叫同一句，波形相關只有 {det.get('v3', {}).get('corr')}（每次輸出不同）；不同寫法之間相關 {min(v3c)}–{max(v3c)}，無法區分是換字還是抽樣造成。")
    nt = [t for t in T if t["role"] in ("narrator", "zhezhe")]
    full_asr = [(t["role_zh"], t["voice"].split(" - ")[0].strip(), t["model"]) for t in nt if t.get("整句（替身字，正式管線）", {}).get("asr_both_ok")]
    facts.append("- 「紙燈節」整句（正式管線、替身字）兩個轉寫模型都沒有非同音差異的：" + ("、".join(f"{r} {v}（{m}）" for r, v, m in full_asr) or "無")
                 + "；F0 判定（燈不下降且高於紙、節終點高於最低點 8%）連 edge 基準也不通過，判定門檻對自然語流偏嚴，逐字數據見 4.3。")
    facts.append(f"- 計費：character-cost 標頭顯示中文約 0.4 點／字元（multilingual_v2 與 v3 相同）；本代理合計 {Lg['spent']} 點。")
    # ---------------- INDEX.md
    L = ["# ElevenLabs 台灣華語聲線庫選角｜驗收入口", "",
         f"- 日期：{time.strftime('%Y-%m-%d %H:%M')}｜製作：配音製作代理（EL 選角，成人角色為主）｜腳本：`tools/vo_el_library.py`",
         "- 範圍：旁白、阿樂叔叔（一般段＋受影響段）、葉護理師、林老師、陳伯伯、邀請者、執勤人員；庫裡年輕聲線另試折折、小晴、小宇、品安（聲線設計由另一位代理負責）。",
         "- **本文件只列候選與數據，不打分、不推薦。** 候選排序與 eleven_v3 前兩名都只依下方寫明的客觀條件。",
         "- **聽感一律未驗證**：Claude 聽不到聲音。台灣口音自然度、情緒、童聲像不像、成人角色年齡感，全部未驗證（第 6 節）。",
         f"- **點數**：本代理 ElevenLabs 計費合計 **{Lg['spent']}** 點（上限 3,000；依回應標頭 `character-cost` 逐筆累加），呼叫 {Lg['calls']} 次、失敗 {Lg['failed']} 次（第 7 節）。",
         "", "## 0. 量測事實摘要（只列事實，不含評分或推薦）", "",
         ] + facts + ["", "## 1. 聲線庫查詢與 Starter 實測", "",
         f"- `GET /v1/shared-voices`（page_size=100，每個查詢都翻到 has_more=false）：",
         ]
    for q in VV["queries"]:
        L.append(f"  - `{urllib.parse.urlencode(q['query'])}` → {q['count']} 個（{len(q['pages'])} 頁）")
    L += [f"- 聯集 {VV['total_unique']} 個；依欄位判定為台灣華語（locale＝cmn-TW 或 verified_languages 有 cmn-TW）{VV['tw_mandarin_count']} 個。"
          "任務指定的 `accent=taiwanese` 查到 0 個：聲線庫的口音值是 `taiwan mandarin`，已另用 `accent=taiwan mandarin` 查一次（48 個，與 locale 查詢相同）。",
          f"- 「你好」實測（eleven_multilingual_v2、mp3_44100_128、seed {SEED}）：{P['summary']['tested']} 個全部測過，"
          f"**{P['summary']['usable']} 個可用**，失敗 {sum(P['summary']['failed_by_http'].values())} 個；計費 {P['summary']['billed']} 點。"
          "沒有任何聲線需要先加入「我的聲線」（加入 0 個）。",
          "- `free_users_allowed=false` 的聲線（Chloe、Andrew、Angel、Ian - Radio Host 等 17 個）在 Starter 也全部回應 200；"
          "Liang 的計費倍率是 2.0（「你好」計 2 點），篩選時排除。",
          "- 每個聲線的名稱、voice_id、public_owner_id、性別、年齡、口音、用途、描述、free_users_allowed、category：`voices.json`；實測結果與錯誤原文：`probe.json`；"
          "聲線主人預覽檔的 F0／共振峰（免費下載、不計點，只作篩選）：`previews.json`。", "",
          "| 聲線 | voice_id | 性別 | 年齡 | 用途 | category | free_users_allowed | 倍率 | Starter | 預覽 F0 | 預覽 F1／F2 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in VV["voices"]:
        pr = P["voices"].get(v["voice_id"], {})
        pv = PV.get(v["voice_id"], {})
        L.append(f"| {v['name']}{'' if v['tw_mandarin'] else '（非台灣華語欄位）'} | `{v['voice_id']}` | {v.get('gender') or '—'} | {v.get('age')} | "
                 f"{v.get('use_case')} | {v.get('category')} | {v.get('free_users_allowed')} | {v.get('rate')} | "
                 f"{'可用' if pr.get('ok') else 'HTTP ' + str(pr.get('http'))} | {_fmt(pv.get('f0_median'))} | {pv.get('F1_median')}／{pv.get('F2_median')} |")
    L += ["", "## 2. 方法", "",
          "**篩選（不計點）**：" + C["_說明"], "",
          "**合成**：每個角色最多 3 個候選，各念 2–3 句該角色的劇本台詞（`vo_lib.load_lines()` 依台詞編號讀，一字不改；替身字照 `audio/vo/pronounce.json` 的全域表，"
          "與正式管線相同），另外補念所選台詞沒涵蓋的檢查詞片段（取自同一角色的台詞）。eleven_multilingual_v2；voice_settings：stability 0.5、similarity_boost 0.75、"
          f"style 0、use_speaker_boost true、speed 依角色（表內列出）；seed {SEED}；mp3_44100_128。eleven_v3：stability 0.5、similarity_boost 0.75、speed 同上、language_code zh。",
          "- 必要旁白一 a2_c004_02：依句號分三段合成、speed 0.85，段間插入 1,300 ms 靜音（沿用 vo_lib.split_breaks／vo_build.plan_segments 的分段方式；"
          "每段修到語音起訖前 10 ms、後 80 ms，10 ms 淡入／20 ms 淡出），量到的句間停頓與 edge 版（1.41 秒）比較。",
          "- eleven_v3 的 API 接受 speed 參數（沒有任何錯誤回應、沒有不帶 speed 重試）；是否生效沒有另外測，實測語速見比較表。",
          "- 執勤人員：與 edge 基準相同的 300–3400 Hz 電話音色（casting.json post.telephone）。ElevenLabs 候選不做句中停頓上限（max_pause_ms），保留合成器原本的停頓。",
          "- **edge 基準**：照 `audio/vo/casting.json` 目前參數（含 post：替身字、[[break]]、segment_rates、contour、max_pause_ms、sentence_gap_ms、telephone）走 "
          "`vo_build.render_line` 念同樣的句子（免費）；原始檔快取放在本資料夾 `raw_edge/`，不寫 `audio/vo/_raw/`。",
          "- **母帶**（同 G3，`vo_lib.master`）：去頭尾靜音後補頭 120 ms、尾 250 ms；−18 LUFS；真峰值 ≤ −1.5 dBTP；48 kHz／16-bit／單聲道（TPDF 抖動，固定亂數種子）。",
          "", "**量測**：" + json.loads(METRICS.read_text("utf-8"))["_說明"], "",
          "- **共振峰**：有聲格（自相關 F0 > 0、強度在最大值 25 dB 內）LPC（Praat Burg，5 個共振峰、上限 5,500 Hz、25 ms 窗）F1／F2 中位數；"
          "所有聲線用同一上限才可互相比較。兒童聲道短，F1／F2 一般高於成人；只是「像不像孩子」的代理指標。",
          "- **eleven_v3 前兩名**：" + RANK_RULE, "", "- **「紙燈節」聲調**：" + TONE_RULE, ""]
    # ---------------- 3. 比較表
    L += ["## 3. 比較表（每個角色：edge 基準＋候選；數值為所選劇本台詞合併）", "",
          "欄位：F0＝合併有聲格中位（p10–p90）；F1／F2＝共振峰中位；語速＝各句 毛／淨（字／秒）；停頓＝各句句中停頓（ms，−35 dB、≥150 ms）；"
          "LUFS、dBTP＝各句範圍；削波＝樣本數合計；原始頭／尾＝合成器原始檔頭尾靜音（ms，各句）；需複查＝兩個轉寫模型同處非同音差異的句數；"
          "檢查詞不一致＝兩個模型合計次數；PER＝各句兩模型取小的平均。", ""]
    for role, rows in table.items():
        plan = ROLE_PLAN[role]
        rc = C["roles"][role]
        L += [f"### 3.{list(table).index(role) + 1} {plan['zh']}", "",
              f"- F0 目標 {plan['f0_target']} Hz（{plan['f0_src']}）；語速目標 {plan['rate'][0]}–{plan['rate'][1]} 字／秒"
              + ("；" + "、".join(f"{k} {v[0]}–{v[1]}" for k, v in plan.get("rate_line", {}).items()) if plan.get("rate_line") else "")
              + f"；ElevenLabs speed {plan['speed']}" + ("（" + "、".join(f"{k} {v}" for k, v in plan.get("speed_line", {}).items()) + "）" if plan.get("speed_line") else ""),
              f"- 台詞：" + "、".join(f"{lid}「{R().LINES[lid]['text']}」" for lid in plan["lines"])
              + ("；檢查詞片段：" + "、".join(f"「{t}」（{w}）" for _, t, w in plan.get("frames", [])) if plan.get("frames") else ""),
              f"- 篩選通過 {len(rc['screen_passing'])} 個，取前 {len(rc['candidates'])} 個（預覽 F0 與目標差的半音數）："
              + "、".join(f"{c['name']}（{c['preview_f0']} Hz，{c['f0_dist_semitones']} 半音）" for c in rc["candidates"]),
              f"- eleven_v3 前兩名（依上列規則）：{'、'.join((rc.get('v3') or {}).get('top2', [])) or '—'}", "",
              "| 聲線 | 模型 | F0 中位（p10–p90） | 與目標差（半音） | F1／F2 | 語速 毛／淨 | 停頓 ms | LUFS | dBTP | 削波 | 原始頭／尾 ms | 需複查 | 檢查詞不一致 | PER 平均 | 紙燈節 F0／ASR |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            p = r["pooled"]
            ln = r["lines"]
            tone = r.get("tone") or {}
            tcell = "—"
            if tone:
                parts = []
                for lab, short in (("整句（替身字，正式管線）", "整句替身"), ("整句（原字）", "整句原字"),
                                   ("短框句 紙登結（替身字）", "框替身"), ("短框句 紙燈節（原字）", "框原字")):
                    if lab in tone:
                        t = tone[lab]
                        parts.append(f"{short} {'✓' if t['f0_pass'] else '✗'}" + (f"/{'✓' if t['asr_both_ok'] else '✗'}" if t.get("asr_both_ok") is not None else ""))
                tcell = "；".join(parts)
            if r["errors"]:
                L.append(f"| {r['voice']} | {r['model']} | 合成失敗：{json.dumps(r['errors'][0], ensure_ascii=False)[:120]} |" + " |" * 12)
                continue
            L.append(f"| {r['voice']} | {r['model']} | {_fmt(p.get('f0_median'))}（{_fmt(p.get('f0_p10'))}–{_fmt(p.get('f0_p90'))}） | "
                     f"{_fmt(r['f0_dist_semitones'], 2)} | {p.get('F1_median')}／{p.get('F2_median')} | "
                     + "；".join(f"{_fmt(x['rate_cps'], 2)}／{_fmt(x['rate_cps_net'], 2)}" for x in ln) + " | "
                     + "；".join(",".join(str(q) for q in x["pauses_ms"]) or "—" for x in ln) + " | "
                     f"{min(x['lufs'] for x in ln):.1f}～{max(x['lufs'] for x in ln):.1f} | {max(x['dbtp'] for x in ln):.1f} | "
                     f"{sum(x['clip'] or 0 for x in ln)} | " + "；".join(f"{x['raw_head']}/{x['raw_tail']}" if x["raw_head"] is not None else
                                                                   "分段" + ",".join(f"{a}/{b}" for a, b in (x['raw_segments'] or [])) for x in ln)
                     + f" | {r['lines_flagged_both_models']} | {r['checkword_fail_count']} | {_fmt(r['mean_per_min'], 3)} | {tcell} |")
        L.append("")
        # 逐句明細
        L += ["<details><summary>逐句明細（轉寫原文、CER／PER、檢查詞）</summary>", "",
              "| 聲線 | 模型 | 台詞 | 秒 | 毛／淨／淨r | 停頓 ms | F0 中位（p10–p90） | F1／F2 | CER small／turbo | PER small／turbo | 判讀 | small 轉寫 | turbo 轉寫 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            for x in r["lines"]:
                cer, per, hyp = x["cer"], x["per"], x["hyp"]
                extra = ""
                if x.get("yi_first_syllable"):
                    extra = f"（首字「咦」終點／起點 {x['yi_first_syllable'].get('end_over_start')}）"
                L.append(f"| {r['voice']} | {r['model']} | {x['line']}{extra} | {x['seconds']} | {_fmt(x['rate_cps'], 2)}／{_fmt(x['rate_cps_net'], 2)}／{_fmt(x['rate_cps_net_r'], 2)} | "
                         f"{','.join(str(q) for q in x['pauses_ms']) or '—'} | {_fmt(x['f0_median'])}（{_fmt(x['f0_p10'])}–{_fmt(x['f0_p90'])}） | "
                         f"{x['F1']}／{x['F2']} | {cer.get('small')}／{cer.get('large-v3-turbo')} | {per.get('small')}／{per.get('large-v3-turbo')} | "
                         f"{x['verdict']} | {hyp.get('small')} | {hyp.get('large-v3-turbo')} |")
        L += ["", "</details>", ""]
    # ---------------- 4. 必要旁白與阿樂 a2_c002_01
    L += ["## 4. 指定檢查", "", "### 4.1 必要旁白一 a2_c004_02（一字不改、慢、句間停頓）", "",
          "| 聲線 | 模型 | 毛／淨 字／秒 | 句中停頓 ms（≥150 ms） | 兩個模型轉寫 | 判讀 |", "|---|---|---|---|---|---|"]
    for r in table.get("narrator", []):
        for x in r["lines"]:
            if x["line"] == "a2_c004_02":
                L.append(f"| {r['voice']} | {r['model']} | {_fmt(x['rate_cps'], 2)}／{_fmt(x['rate_cps_net'], 2)} | {','.join(str(q) for q in x['pauses_ms'])} | "
                         f"small：{x['hyp'].get('small')}<br>turbo：{x['hyp'].get('large-v3-turbo')} | {x['verdict']} |")
    L += ["", "- edge 正式版（casting.json：−8%、句間 1,300 ms）在 G3 量到句間停頓 1.41 秒；本表 edge 列是同參數重跑。", "",
          "### 4.2 阿樂 a2_c002_01（咦？……受影響段）", "",
          "| 聲線 | 模型 | 毛／淨 字／秒 | 停頓 ms | 首字「咦」F0 起點→終點（終點／起點） | small | turbo |", "|---|---|---|---|---|---|---|"]
    for r in table.get("ale", []):
        for x in r["lines"]:
            if x["line"] == "a2_c002_01":
                y = x.get("yi_first_syllable") or {}
                L.append(f"| {r['voice']} | {r['model']} | {_fmt(x['rate_cps'], 2)}／{_fmt(x['rate_cps_net'], 2)} | {','.join(str(q) for q in x['pauses_ms']) or '—'} | "
                         f"{y.get('start_hz')}→{y.get('end_hz')}（{y.get('end_over_start')}） | {x['hyp'].get('small')} | {x['hyp'].get('large-v3-turbo')} |")
    L += ["", "- G3 的參考條件（review/G3/a2_c002_01_rms50.json）：「咦」之後停頓 ≤600 ms、「揮手……」之後 ≥500 ms、淨語速 ≤4.5；「咦」二聲上揚＝終點／起點 ≥1.15"
          "（edge 正式版是 PSOLA 改調後的值）。ElevenLabs 候選沒有改調、沒有剪停頓，是合成器原樣。", ""]
    # ---------------- 5. 紙燈節
    L += ["### 4.3 「紙燈節」聲調與轉寫（旁白、折折必測；林老師 a3_c008_01 附帶）", "", TONE_RULE, "",
          "| 角色 | 聲線 | 模型 | 寫法 | 燈 終點／起點 | 燈÷紙 平均 | 節 終點／最低點（最低點位置） | F0 判定 | 窗內有聲段 | 兩個模型 ASR | small／turbo 轉寫 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in T:
        for lab in ("整句（替身字，正式管線）", "整句（原字）", "短框句 紙登結（替身字）", "短框句 紙燈節（原字）"):
            if lab not in t:
                continue
            x = t[lab]
            hyp = x.get("hyp") or {}
            L.append(f"| {t['role_zh']} | {t['voice']} | {t['model']} | {lab} | {x['燈_end_over_start']} | {x['燈_over_紙_mean']} | {x['節_end_over_min']}（{x['節_min_pos']}） | "
                     f"{'通過' if x['f0_pass'] else ('不通過' if x['f0_pass'] is False else '無法定位：' + str(x.get('error')))} | {x['islands']} | "
                     f"{'通過' if x['asr_both_ok'] else ('不通過' if x['asr_both_ok'] is False else '—')} | {hyp.get('small', '—')}／{hyp.get('large-v3-turbo', '—')} |")
    L += ["", "- **判定門檻的校準**：edge 基準（G3 正式管線）在本判定也不通過（整句「燈」不比「紙」高 5%、「節」句末沒有上揚）。"
          "所以 F0 判定只是一致的客觀量尺，不代表聽起來一定念錯；轉寫結果另列，兩者都列給驗收代理判讀。",
          "- 短框句只有三個字，轉寫模型缺少上下文，常寫成不相關的詞（例如「咖喱洞解」），框句的轉寫只作參考。", "",
          "**原字／替身字／錯誤寫法的波形比較**（合成器原始檔解碼後；corr＝相關係數；residual＝差值能量相對原訊號）", "",
          "| 候選 | 模型 | 紙燈節 vs 紙登結 | 紙燈節 vs 紙等街 | 整句 原字 vs 替身字 |", "|---|---|---|---|---|"]
    for k, v in wi.get("pairs", {}).items():
        cand, mt = k.split("｜")
        cells = []
        for key in ("紙燈節 vs 紙登結", "紙燈節 vs 紙等街"):
            q = v.get(key)
            cells.append(f"{q['corr']}（{q['residual_db']} dB）" if q else "—")
        q = next((vv for kk, vv in v.items() if kk.endswith("原字 vs 替身字")), None)
        cells.append(f"{q['corr']}（{q['residual_db']} dB）" if q else "—")
        L.append(f"| {cand} | {mt} | " + " | ".join(cells) + " |")
    if det:
        L.append(f"| Door Chow 同一句重複呼叫（決定性對照） | v2／v3 | v2：{det['v2']['corr']}（{det['v2']['resid_db']} dB） | v3：{det['v3']['corr']}（{det['v3']['resid_db']} dB） | — |")
    L += ["", f"- 逐檔走勢（20 ms 一點）：`tone_checks/*.json`；摘要 `tone_checks/summary.json`；決定性對照 `tone_checks/determinism_door.json`。",
          f"- 讀音提案（不改 pronounce.json）：`proposed_pronounce_el.json`。{prop.get('proposal_text', '')}", ""]
    # ---------------- 6. 檔案
    n_wav = sum(1 for s in S.values() if not s.get("error"))
    L += ["## 5. 數據與檔案", "",
          f"- `samples/<角色>/<角色>__<聲線>_<模型>__<項目>.wav`：{n_wav} 檔（edge 基準檔名為 `__edge__`）。",
          "- `samples.json`：每檔的合成參數（voice_id、模型、speed、seed、合成用文字、分段、原始檔、母帶紀錄）。",
          "- `metrics.json`：每檔全部量測與兩個模型的轉寫比對。",
          "- `candidates.json`：每個角色的篩選條件、通過名單、候選、v2 排名、eleven_v3 前兩名與比較表數據。",
          "- `transcripts.md`：逐檔兩個模型的轉寫原文、差異與檢查詞。",
          "- `tone_checks/`：「紙燈節」F0 走勢；`proposed_pronounce_el.json`：讀音提案。",
          "- `voices.json`、`probe.json`、`previews.json`：聲線庫查詢、Starter 實測、預覽檔量測；`ledger.json`：本代理點數帳本。",
          "- `listen.html`：選擇性試聽頁（相對路徑，直接用瀏覽器開）。",
          "- `raw/`、`raw_edge/`、`previews/`：ElevenLabs／edge 原始檔與預覽檔。",
          "- 重跑：`tools/.venv/bin/python tools/vo_el_library.py <discover|previews|probe|shortlist|render|v3|measure|tone|report>`（有快取，不重複計點）。", ""]
    # ---------------- 7. 未驗證
    L += ["## 6. 未驗證項目", "",
          "- 聽感：自然度、台灣口音自然度、情緒（阿樂困惑但咬字清楚、林老師肯定溫暖、邀請者友善不陰沉、陳伯伯渾厚讓人安心）、角色年齡感。",
          "- 童聲像不像：只有 F0 與 F1／F2 代理指標；聲線庫都是成人聲線，ElevenLabs 沒有音高參數。",
          "- 「和」念 hé 或 hàn、「一」「不」變調：轉寫看不出，未驗證。",
          "- 邀請者「中性」：只用 F0 中性區（145–175 Hz）當條件，聽起來是否中性未驗證。",
          "- 實際投影現場的音量、清晰度與學校筆電播放：未驗證（第 3 天彩排）。",
          "- 授權條款：Starter 方案的商用／署名條件未在本輪查證（帳號方案條款由使用者確認）。", ""]
    # ---------------- 8. 點數
    L += ["## 7. 點數紀錄", "",
          f"- 本代理合計 **{Lg['spent']}** 點／上限 3,000；呼叫 {Lg['calls']} 次（失敗 {Lg['failed']} 次，失敗不計費）。逐筆：`ledger.json`；共用紀錄：`audio/vo/elevenlabs_usage.jsonl`（purpose 以「EL 選角」開頭）。",
          "- 計費依回應標頭 `character-cost`：中文台詞實際計費約為字元數的 0.3–0.4 倍（例如 23 字元計 8 點），以標頭為準。", "",
          "| 階段 | 呼叫 | 失敗 | 送出字元 | 計費（點） |", "|---|---|---|---|---|"]
    for st, v in by_stage.items():
        L.append(f"| {st} | {v['calls']} | {v['failed']} | {v['text_chars']} | {v['billed']} |")
    if fails:
        L += ["", "失敗的呼叫（錯誤原文）：", ""]
        for e in fails:
            L.append(f"- {e['time']}｜{e['purpose']}｜HTTP {e['http']}｜{json.dumps(e.get('detail'), ensure_ascii=False)[:300]}")
    stops = load_samples().get("stops", [])
    if stops:
        L += ["", "點數上限停止紀錄：", ""] + [f"- {s['time']}：{s['why']}" for s in stops]
    (OUT / "INDEX.md").write_text("\n".join(L) + "\n", "utf-8")
    print("報告完成", OUT / "INDEX.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--group", default="adult")
    ap.add_argument("--roles", default="")
    ap.add_argument("--no-transcribe", action="store_true")
    args = ap.parse_args()
    {"discover": cmd_discover, "previews": cmd_previews, "probe": cmd_probe, "shortlist": cmd_shortlist,
     "render": cmd_render, "measure": cmd_measure, "v3": cmd_v3, "tone": cmd_tone,
     "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
