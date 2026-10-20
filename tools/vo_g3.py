"""G3 試音包：三個版本 × 主要角色的代表台詞 → 樣本、量測、逐字稿差異。

用法：tools/.venv/bin/python tools/vo_g3.py [--only A|B|C] [--no-transcribe]
輸出：review/G3/samples/*.wav（與正式管線相同的母帶處理：頭 120 ms／尾 250 ms、−18 LUFS、真峰值 ≤ −1.5 dBTP、16-bit）、
      review/G3/metrics.json、review/G3/transcripts.md。
ElevenLabs 計費字數記在 audio/vo/elevenlabs_usage.jsonl（合成有快取，重跑不重複計費）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402
from vo_build import SENT_RE  # noqa: E402

G3 = V.ROOT / "review" / "G3"
SAMPLES = G3 / "samples"
EL_BUDGET = 1500   # G3 ElevenLabs 上限：免費方案 10,000 字元 × 15%（帳號金鑰無 user_read 權限，查不到剩餘字數，取最保守值）

EL_DEFAULT = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True, "speed": 1.0}
EL_V3 = {"stability": 0.5, "similarity_boost": 0.75}
VOICES = {  # ElevenLabs 免費方案可經 API 使用的預設聲線（中文驗證口音皆為 standard／cmn-CN）
    "sarah": "EXAVITQu4vr4xnSDxMaL", "lily": "pFZP5JQG7iQjIQuC4Bku", "brian": "nPczCjzI2devNBz1zQrb",
    "bill": "pqHfZKP75CvOlQylNhV4", "will": "bIHbv24MWmeRgasZH58o", "jessica": "cgSgspJ2msm6clMCkdW9",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
}


def el(voice: str, model: str = "eleven_multilingual_v2", speed: float = 1.0) -> dict:
    s = dict(EL_DEFAULT, speed=speed) if model != "eleven_v3" else dict(EL_V3)
    spec = {"service": "elevenlabs", "voice_id": VOICES[voice], "voice_name": voice, "model": model,
            "settings": s, "seed": 20261021, "output_format": "mp3_44100_128"}
    if model == "eleven_v3":
        spec["language_code"] = "zh"
    return spec


def edge(voice: str, rate: str, pitch: str, **post) -> dict:
    return {"service": "edge", "voice": f"zh-TW-{voice}Neural", "rate": rate, "pitch": pitch, "post": post}


# 代表台詞：旁白 a2_c004_02（必要旁白一）、阿樂 a2_c002_01、小晴 a2_c002_02＋a1_c004_03、小宇 a3_c002_02（第三幕拒絕句）、
# 折折 a2_c001_03、葉護理師 a2_c012_01（另一位成人；C 版加林老師 a3_c003_02）
PLAN = [
    # ---- A：ElevenLabs（免費方案只能用預設聲線；台灣共享聲線與聲線設計 API 都要付費方案）
    ("A", "narrator", "a2_c004_02", "sarah-v2", el("sarah")),
    ("A", "narrator", "a2_c004_02", "sarah-v3", el("sarah", "eleven_v3")),
    ("A", "narrator", "a2_c004_02", "lily-v2", el("lily")),
    ("A", "ale", "a2_c002_01", "brian-v2-s0.90", el("brian", speed=0.9)),
    ("A", "ale", "a2_c002_01", "bill-v2-s0.90", el("bill", speed=0.9)),
    ("A", "ye", "a2_c012_01", "will-v2", el("will")),
    ("A", "xiaoqing", "a2_c002_02", "jessica-v2", el("jessica")),
    ("A", "xiaoqing", "a1_c004_03", "jessica-v2", el("jessica")),
    ("A", "xiaoyu", "a3_c002_02", "laura-v2", el("laura")),
    ("A", "zhezhe", "a2_c001_03", "laura-v3", el("laura", "eleven_v3")),
    # ---- B：童聲方案（聲線設計 API 被拒 → 年輕成人女聲＋語速／音高調整；ElevenLabs 沒有音高參數，所以用 zh-TW 女聲）
    ("B", "xiaoqing", "a2_c002_02", "hsiaochen+40Hz", edge("HsiaoChen", "+0%", "+40Hz")),
    ("B", "xiaoqing", "a1_c004_03", "hsiaochen+40Hz", edge("HsiaoChen", "+0%", "+40Hz")),
    ("B", "xiaoyu", "a3_c002_02", "hsiaoyu+20Hz", edge("HsiaoYu", "+5%", "+20Hz")),
    ("B", "zhezhe", "a2_c001_03", "hsiaoyu+55Hz", edge("HsiaoYu", "+12%", "+55Hz")),
    ("B", "zhezhe", "a2_c001_03", "jessica-v2-s1.10", el("jessica", speed=1.1)),
    # ---- C：edge-tts 基準（角色表 v03 第 3 節起始值）
    ("C", "narrator", "a2_c004_02", "hsiaochen-5%", edge("HsiaoChen", "-5%", "+0Hz")),
    ("C", "narrator", "a2_c004_02", "hsiaochen-10%-gap1300", edge("HsiaoChen", "-10%", "+0Hz", sentence_gap_ms=1300)),
    ("C", "ale", "a2_c002_01", "yunjhe-15%", edge("YunJhe", "-15%", "+0Hz")),
    ("C", "ye", "a2_c012_01", "yunjhe-3%+12Hz", edge("YunJhe", "-3%", "+12Hz")),
    ("C", "lin", "a3_c003_02", "hsiaochen-20Hz", edge("HsiaoChen", "+0%", "-20Hz")),
    ("C", "xiaoqing", "a2_c002_02", "hsiaochen+25Hz", edge("HsiaoChen", "+0%", "+25Hz")),
    ("C", "xiaoqing", "a1_c004_03", "hsiaochen+25Hz", edge("HsiaoChen", "+0%", "+25Hz")),
    ("C", "xiaoyu", "a3_c002_02", "hsiaoyu+5%-10Hz", edge("HsiaoYu", "+5%", "-10Hz")),
    ("C", "zhezhe", "a2_c001_03", "hsiaoyu+10%+35Hz", edge("HsiaoYu", "+10%", "+35Hz")),
    # ---- P：提案參數（依 A／B／C 量測整理；與 audio/vo/casting.json 相同），同一句代表台詞重跑
    ("P", "narrator", "a2_c004_02", "hsiaochen-8%-gap1300", edge("HsiaoChen", "-8%", "+0Hz", sentence_gap_ms=1300)),
    ("P", "ale", "a2_c002_01", "yunjhe-6%-cap900", edge("YunJhe", "-6%", "+0Hz", max_pause_ms=900)),
    ("P", "ye", "a2_c012_01", "yunjhe+5%+12Hz-cap650", edge("YunJhe", "+5%", "+12Hz", max_pause_ms=650)),
    ("P", "lin", "a3_c003_02", "hsiaochen-5%-20Hz-cap650", edge("HsiaoChen", "-5%", "-20Hz", max_pause_ms=650)),
    ("P", "xiaoqing", "a2_c002_02", "hsiaochen+40Hz-cap550", edge("HsiaoChen", "+0%", "+40Hz", max_pause_ms=550)),
    ("P", "xiaoqing", "a1_c004_03", "hsiaochen+40Hz-cap550", edge("HsiaoChen", "+0%", "+40Hz", max_pause_ms=550)),
    ("P", "xiaoyu", "a3_c002_02", "hsiaoyu+12%+20Hz-cap550", edge("HsiaoYu", "+12%", "+20Hz", max_pause_ms=550)),
    ("P", "zhezhe", "a2_c001_03", "hsiaoyu+22%+60Hz-cap550", edge("HsiaoYu", "+22%", "+60Hz", max_pause_ms=550)),
]

ROLE_ZH = {v: k for k, v in V.ROLE_CODES.items()}


def render(spec: dict, text: str, line_id: str) -> tuple[np.ndarray, int, str]:
    pron = V.load_pronounce()
    synth = V.apply_pronounce(text, pron, spec["service"], line_id)
    post = spec.get("post", {})
    gap = post.get("sentence_gap_ms")
    parts = [p for p in SENT_RE.split(synth) if p.strip()] if gap else [synth]
    s = {k: v for k, v in spec.items() if k != "post"}
    chunks, billed = [], 0
    for i, p in enumerate(parts):
        raw, info = V.synth_raw(s, p, purpose=f"G3 試音 {line_id}")
        billed += info.get("billed") or (info["chars"] if s["service"] == "elevenlabs" else 0)
        x = V.decode(raw)
        if len(parts) > 1:
            a, b = V.speech_bounds(x)
            x = x[max(0, a - 480):min(len(x), b + int(0.08 * V.SR))]
            if i < len(parts) - 1:
                x = np.concatenate([x, np.zeros(int(gap / 1000 * V.SR), dtype=np.float32)])
        chunks.append(x)
    x = np.concatenate(chunks)
    if post.get("max_pause_ms"):
        x, _ = V.cap_pauses(x, post["max_pause_ms"])
    return x, billed, synth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--no-transcribe", action="store_true")
    args = ap.parse_args()
    lines = V.load_lines()
    SAMPLES.mkdir(parents=True, exist_ok=True)
    plan = [p for p in PLAN if not args.only or p[0] == args.only]
    need = 0
    for ver, role, lid, label, spec in plan:
        if spec["service"] == "elevenlabs":
            t = V.apply_pronounce(lines[lid]["text"], V.load_pronounce(), "elevenlabs", lid)
            if not V._cache_path({k: v for k, v in spec.items() if k != "post"}, t, "mp3").exists():
                need += len(t)
    used_before = 0
    if V.USAGE_LOG.exists():
        for l in V.USAGE_LOG.read_text("utf-8").splitlines():
            e = json.loads(l)
            if e.get("ok") and str(e.get("purpose", "")).startswith("G3"):
                used_before += int(e.get("billed") or e.get("text_chars") or 0)
    print(f"G3 ElevenLabs：已用 {used_before}、本次預估 {need}、上限 {EL_BUDGET}")
    if used_before + need > EL_BUDGET:
        raise SystemExit("超過 G3 ElevenLabs 字數上限")
    mpath = G3 / "metrics.json"
    metrics = json.loads(mpath.read_text("utf-8")) if mpath.exists() else {"samples": {}}
    done = []
    for ver, role, lid, label, spec in plan:
        name = f"{ver}_{role}_{lid}_{label}.wav"
        out = SAMPLES / name
        x, billed, synth = render(spec, lines[lid]["text"], lid)
        y, minfo = V.master(x)
        V.write_wav(out, y)
        m = V.measure(out, lines[lid]["text"])
        rec = {"version": ver, "role": role, "role_zh": ROLE_ZH.get(role, role), "line": lid,
               "text": lines[lid]["text"], "synth_text": synth, "label": label,
               "spec": {k: v for k, v in spec.items()}, "el_chars_billed": billed,
               "raw_head_silence_ms": minfo["raw_head_silence_ms"], "raw_tail_silence_ms": minfo["raw_tail_silence_ms"],
               "master": {k: minfo.get(k) for k in ("method", "gain_db", "normalization_type", "limited")},
               **m}
        metrics["samples"][name] = rec
        done.append(name)
        print(f"{name}: {m['seconds']}s {m['rate_cps']}字/秒 F0 {m['f0_median']} I {m['integrated_lufs']} TP {m['true_peak_dbtp']}")
    if not args.no_transcribe:
        tc = V.transcribe_compare([(SAMPLES / n, metrics["samples"][n]["text"], metrics["samples"][n]["synth_text"])
                                   for n in done])
        for n in done:
            metrics["samples"][n]["transcript"] = tc[str(SAMPLES / n)]
    used = 0
    for l in V.USAGE_LOG.read_text("utf-8").splitlines() if V.USAGE_LOG.exists() else []:
        e = json.loads(l)
        if e.get("ok") and str(e.get("purpose", "")).startswith("G3"):
            used += int(e.get("billed") or e.get("text_chars") or 0)
    metrics["elevenlabs"] = {"plan_detected": "免費方案（API 回應：pcm_44100 需 Pro、mp3_44100_192 需 Creator、共享聲線與聲線設計需付費方案）",
                             "subscription_readable": False,
                             "budget_rule": "G3 ≤ 剩餘字數 15%；金鑰沒有 user_read 權限查不到剩餘字數，取免費方案 10,000 × 15% = 1,500 為上限",
                             "g3_chars_billed": used}
    metrics["samples"] = dict(sorted(metrics["samples"].items()))
    mpath.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), "utf-8")
    write_transcripts(metrics)
    print(f"G3 ElevenLabs 實際計費合計 {used} 字元")


def write_transcripts(metrics: dict) -> None:
    rows = ["# G3 逐句轉寫差異表", "",
            "- 產生：`tools/vo_g3.py`。轉寫用兩個本機模型交叉比對：faster-whisper **small** 與 **large-v3-turbo**（皆 int8、beam 5、提示「繁體中文的台灣華語」），結果以 OpenCC s2tw 轉繁體後與劇本逐字比對（去標點）。",
            "- **CER**：字錯率（編輯距離÷劇本字數）。**PER**：拼音（含聲調）錯率——字相同的位置不算錯；字不同的段落比拼音，參考讀音取「合成用文字」（已套替身字，代表要的讀音）。CER 高而 PER 低＝轉寫用了同音字，讀音其實一致。",
            "- 差異類型：同音字（讀音一致）／聲調不同（疑讀錯，或轉寫偏好）／字不同／漏字／多字。**判讀**：兩個模型在同一處都出現非同音差異，才列為「需複查」；只有一個模型出現，多半是轉寫誤差。",
            "- 轉寫看不出的聲調變調（「一」「不」）一律標「未驗證」。聽感一律未驗證（Claude 聽不到聲音）。", ""]
    by_line: dict[str, list] = {}
    for n, r in metrics["samples"].items():
        by_line.setdefault(r["line"], []).append((n, r))
    for lid, items in by_line.items():
        rows += [f"## {lid}｜{items[0][1]['role_zh']}", "", f"劇本：{items[0][1]['text']}", "",
                 "| 樣本 | 模型 | 轉寫（繁體） | CER | PER | 差異 | 讀音檢查詞 |", "|---|---|---|---:|---:|---|---|"]
        for n, r in items:
            t = r.get("transcript")
            if not t:
                rows.append(f"| `{n}` | — | （未轉寫） | | | | |")
                continue
            for mname, m in t["models"].items():
                diffs = "；".join(f"「{d['ref']}」→「{d['hyp']}」{d['kind']}" for d in m["diffs"]) or "無"
                checks = "；".join(f"{c['word']}：{c['status']}" for c in m["checks"]) or "—"
                rows.append(f"| `{n}` | {mname} | {m['hyp_trad']} | {m['cer']:.3f} | {m['per']:.3f} | {diffs} | {checks} |")
            rows.append(f"| `{n}` | **判讀** | {t['verdict']} | {t['cer_min']:.3f} | {t['per_min']:.3f} | | |")
        rows.append("")
    (G3 / "transcripts.md").write_text("\n".join(rows), "utf-8")


if __name__ == "__main__":
    main()
