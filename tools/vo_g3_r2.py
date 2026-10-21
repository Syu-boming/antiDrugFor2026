"""G3 修正第 2 輪：重驗 1 的聲音項目證據（第 2「品安」、第 3 葉護理師語速／音高、第 4「±1 LU」範圍、第 11 ElevenLabs 用量）。

用法（專案根目錄）：
  tools/.venv/bin/python tools/vo_g3_r2.py                       # 全部
  tools/.venv/bin/python tools/vo_g3_r2.py --only roles,pinan    # roles／ye／pinan／loudness／el（逗號分隔）

一律用正式管線（audio/vo/casting.json v03 → tools/vo_build.py render_line → vo_lib.master）。合成有快取；本輪全部 edge-tts，
ElevenLabs 計費 0 字元（本專案依主線裁決不再呼叫 ElevenLabs）。

輸出：
  review/G3/r2/*.wav                     各角色代表台詞與校準句（v03 參數）、「品安」對照檔（平安對照、修正前整句合成）
  review/G3/metrics.json → "round2"       角色 F0（代表台詞合併＋校準句）、同底聲兩兩檢查（重算）、葉護理師 8 句淨語速、
                                          葉護理師↔邀請者／阿樂、「品安」F0 走勢與轉寫、±1 LU 範圍兩案數字、ElevenLabs 用量
  review/G3/tone_check_pinan_r2.json/.png「品」對「平」的 F0 走勢對照（三句）
  review/G3/voice_matrix_r2.png          角色 F0（合併與校準句）× 語速分布圖
  review/G3/loudness_scope_r2.json        ±1 LU 範圍：對白句、主奏配樂段、劇情襯底段、整段 cue 的實測（讀 G4 驗收包混音）
  review/G3/transcripts.md               （由 vo_g3.write_transcripts 重寫，含第 2 輪）
聽感一律未驗證（Claude 聽不到聲音）。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402
import vo_build as B  # noqa: E402
import vo_g3_r1 as R1  # noqa: E402

G3 = V.ROOT / "review" / "G3"
OUT = G3 / "r2"
R1.OUT = OUT          # R1.render() 寫到 r2/
CAST = R1.CAST
LINES = R1.LINES
SR = V.SR
NAME_PROMPT = "以下是繁體中文的台灣華語。故事人物：小晴、小宇、品安、阿樂叔叔、折折。"
PINAN_LINES = ["a1_c001_01", "a1_c004_05", "a6_c006_01"]
YE_LINES = [lid for lid, ln in LINES.items() if ln["role"] == "葉護理師"]


def st(a: float, b: float) -> float:
    return round(12 * math.log2(b / a), 2)


def pct(a: float, b: float) -> float:
    return round(abs(a - b) / min(a, b) * 100, 1)


# ---------------------------------------------------------------- 角色（重驗 1 第 3 項）
def do_roles() -> dict:
    roles = R1.do_roles()
    for code, r in roles.items():
        m = V.measure(V.ROOT / r["calibration_file"], R1.CAL)
        r["calibration_f0_median"] = m["f0_median"]
        r["calibration_f0_p10"] = m["f0_p10"]
        r["calibration_f0_p90"] = m["f0_p90"]
    return roles


def pair_checks(r: dict) -> dict:
    """同底聲兩兩檢查（重算）。原規則（角色表第 3 節／修正第 1 輪）：校準句語速差 <5% → 代表台詞合併 F0 差須 ≥10%。
    另列重驗 1 第 3 項的較嚴規則（同一句校準句 F0 差 ≥10%，或語速差 ≥15%），全部配對都算，供參考。"""
    codes = [c for c in r if c != "narrator_required"] + ["narrator_required"]
    rows = []
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            if r[a]["spec"]["voice"] != r[b]["spec"]["voice"]:
                continue
            if {a, b} in ({"ale", "ale_affected"}, {"narrator", "narrator_required"}):
                continue
            ca, cb = r[a]["calibration_cps"], r[b]["calibration_cps"]
            fa, fb = r[a]["f0_median_pooled"], r[b]["f0_median_pooled"]
            ga, gb = r[a]["calibration_f0_median"], r[b]["calibration_f0_median"]
            rate_diff, f0_pooled, f0_cal = pct(ca, cb), pct(fa, fb), pct(ga, gb)
            rows.append({"a": R1.ROLE_ZH[a], "b": R1.ROLE_ZH[b], "voice": r[a]["spec"]["voice"],
                         "param": [r[a]["spec"], r[b]["spec"]], "calibration_cps": [ca, cb], "rate_diff_pct": rate_diff,
                         "f0_pooled": [fa, fb], "f0_pooled_diff_pct": f0_pooled, "semitones_pooled": abs(st(fa, fb)),
                         "f0_calibration": [ga, gb], "f0_calibration_diff_pct": f0_cal,
                         "rule": "語速差 <5% → F0 差須 ≥10%" if rate_diff < 5 else "語速差 ≥5%（F0 不設門檻）",
                         "pass": (f0_pooled >= 10) if rate_diff < 5 else True,
                         "strict_pass": f0_cal >= 10 or rate_diff >= 15})
    return {"rows": rows, "all_pass": all(x["pass"] for x in rows), "all_strict_pass": all(x["strict_pass"] for x in rows),
            "strict_failing": [f"{x['a']}↔{x['b']}" for x in rows if not x["strict_pass"]]}


def calibration_table(r: dict) -> list[dict]:
    return [{"role": R1.ROLE_ZH[c], "spec": v["spec"], "calibration_f0_median": v["calibration_f0_median"],
             "calibration_f0_p10": v["calibration_f0_p10"], "calibration_f0_p90": v["calibration_f0_p90"],
             "calibration_cps": v["calibration_cps"], "f0_median_pooled": v["f0_median_pooled"], "calibration_file": v["calibration_file"]}
            for c, v in r.items()]


def ye_checks(r: dict) -> dict:
    """葉護理師：校準句 ≤4.6 字／秒、全劇 8 句淨語速 ≤5.0（兩種算法）、和邀請者（F0 差 ≥10% 或語速差 ≥15%）、和阿樂。"""
    rep = json.loads((V.VO_DIR / "build_report.json").read_text("utf-8"))
    lines = []
    for lid in YE_LINES:
        e = rep.get(lid)
        if not e:
            lines.append({"line": lid, "missing": True})
            continue
        m = e["metrics"]
        lines.append({"line": lid, "text": e["text"], "file": e["file"], "rate": e["synthesis"][0].get("rate"),
                      "pitch": e["synthesis"][0].get("pitch"), "seconds": m["seconds"], "rate_cps": m["rate_cps"],
                      "rate_cps_net": m["rate_cps_net"], "rate_cps_net_r": m["rate_cps_net_r"], "f0_median": m["f0_median"],
                      "integrated_lufs": m["integrated_lufs"], "true_peak_dbtp": m["true_peak_dbtp"],
                      "pause_spikes": m["pause_spikes"], "verdict": e.get("transcript", {}).get("verdict")})
    ok_lines = [x for x in lines if not x.get("missing")]
    ye, inv, ale, alea = r["ye"], r["inviter"], r["ale"], r["ale_affected"]
    yi = {"ye_calibration_f0": ye["calibration_f0_median"], "inviter_calibration_f0": inv["calibration_f0_median"],
          "f0_calibration_diff_pct": pct(ye["calibration_f0_median"], inv["calibration_f0_median"]),
          "ye_calibration_cps": ye["calibration_cps"], "inviter_calibration_cps": inv["calibration_cps"],
          "rate_diff_pct": pct(ye["calibration_cps"], inv["calibration_cps"]),
          "f0_pooled": [ye["f0_median_pooled"], inv["f0_median_pooled"]],
          "f0_pooled_diff_pct": pct(ye["f0_median_pooled"], inv["f0_median_pooled"]),
          "rule": "同一句校準句 F0 差 ≥10%，或語速差 ≥15%（重驗 1 第 3 項）"}
    yi["pass"] = yi["f0_calibration_diff_pct"] >= 10 or yi["rate_diff_pct"] >= 15
    return {"spec": ye["spec"], "calibration_cps": ye["calibration_cps"], "calibration_le_4_6": ye["calibration_cps"] <= 4.6,
            "lines": lines, "max_rate_cps_net": max(x["rate_cps_net"] for x in ok_lines),
            "max_rate_cps_net_r": max(x["rate_cps_net_r"] for x in ok_lines),
            "all_lines_net_le_5_0": all(x["rate_cps_net"] <= 5.0 and x["rate_cps_net_r"] <= 5.0 for x in ok_lines),
            "gross_rate_mean": round(float(np.mean([x["rate_cps"] for x in ok_lines])), 2),
            "role_sheet_rate": "角色表 3.8–4.0 字／秒（溫柔、清楚、不急）",
            "vs_inviter": yi,
            "vs_ale": {"ye_f0_pooled": ye["f0_median_pooled"], "ale_f0_pooled": ale["f0_median_pooled"],
                       "ale_affected_f0_pooled": alea["f0_median_pooled"],
                       "semitones_vs_ale": abs(st(ale["f0_median_pooled"], ye["f0_median_pooled"])),
                       "semitones_vs_ale_affected": abs(st(alea["f0_median_pooled"], ye["f0_median_pooled"])),
                       "calibration_f0": [ye["calibration_f0_median"], ale["calibration_f0_median"], alea["calibration_f0_median"]],
                       "calibration_cps": [ye["calibration_cps"], ale["calibration_cps"], alea["calibration_cps"]],
                       "rate_diff_pct_vs_ale": pct(ye["calibration_cps"], ale["calibration_cps"]),
                       "rate_diff_pct_vs_ale_affected": pct(ye["calibration_cps"], alea["calibration_cps"])},
            "vs_lin_cross_voice": {"ye_f0_pooled": ye["f0_median_pooled"], "lin_f0_pooled": r["lin"]["f0_median_pooled"],
                                   "f0_pooled_diff_pct": pct(ye["f0_median_pooled"], r["lin"]["f0_median_pooled"]),
                                   "calibration_f0": [ye["calibration_f0_median"], r["lin"]["calibration_f0_median"]],
                                   "calibration_cps": [ye["calibration_cps"], r["lin"]["calibration_cps"]],
                                   "rate_diff_pct": pct(ye["calibration_cps"], r["lin"]["calibration_cps"]),
                                   "note": "不同底聲（YunJhe 男聲對 HsiaoChen 女聲；角色表第 3 節：常同場的林老師↔葉護理師用不同基礎聲音），"
                                           "同底聲門檻不適用。音高與語速現在幾乎相同（a6_c006 同場），區分只靠男女聲音色；聽感未驗證，列第 3 天彩排確認。"},
            "inviter_unchanged_note": "邀請者維持 YunJhe +0%／+45Hz（修正第 1 輪 D-G3-R1-04）。驗收建議的 HsiaoChen −30Hz 實測校準句 F0 157 Hz、"
                                      "4.66 字／秒，和新葉護理師（約 163 Hz、4.29 字／秒）F0 差約 4%、語速差約 9%，兩項都不到門檻，"
                                      "而且會和林老師（HsiaoChen −26Hz）同底聲又同高，不採用。"}


def plot_matrix(r: dict) -> None:
    """角色 F0 × 語速分布圖（同 vo_g3_r1.plot_matrix，改標題、多畫校準句 F0）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _font(plt)
    col = {"zh-TW-HsiaoChenNeural": "#c0392b", "zh-TW-HsiaoYuNeural": "#2e86c1", "zh-TW-YunJheNeural": "#27ae60"}
    fig, ax = plt.subplots(figsize=(10, 6))
    for code, v in r.items():
        c = col.get(v["spec"]["voice"], "#555")
        ax.errorbar(v["calibration_cps"], v["f0_median_pooled"], yerr=[[v["f0_median_pooled"] - v["f0_p10"]],
                    [v["f0_p90"] - v["f0_median_pooled"]]], fmt="o", color=c, alpha=0.8, capsize=3)
        ax.plot(v["calibration_cps"], v["calibration_f0_median"], "x", color=c, ms=6)
        ax.annotate(f"{v['role_zh']} {v['f0_median_pooled']:.0f}／{v['calibration_f0_median']:.0f}",
                    (v["calibration_cps"], v["f0_median_pooled"]), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_yscale("log")
    ax.set_yticks([80, 100, 125, 150, 175, 200, 250, 300, 400])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.axhspan(145, 175, color="#999", alpha=0.12)
    ax.set_xlabel("校準句語速（字／秒，同一句）")
    ax.set_ylabel("F0 中位（Hz，對數軸；圓點＝代表台詞合併、誤差棒 p10–p90；叉＝校準句）")
    ax.set_title("G3 修正第 2 輪：角色 F0 中位 × 語速（紅＝HsiaoChen、藍＝HsiaoYu、綠＝YunJhe；灰帶＝邀請者中性區 145–175 Hz）；"
                 "標籤＝合併／校準句 Hz", fontsize=8)
    fig.tight_layout()
    fig.savefig(G3 / "voice_matrix_r2.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 品安（重驗 1 第 2 項）
def render_variant(line_id: str, synth_text: str | None, contour: bool, name: str) -> Path:
    """小晴聲線：synth_text＝None 時用劇本原文整句合成（修正前做法）；contour＝False 時拿掉 post.contour。"""
    import copy
    c = copy.deepcopy(CAST)
    xq = c["roles"]["小晴"]
    xq["overrides"] = []
    if synth_text:
        post = {}
        if contour:
            ov = next(o for o in CAST["roles"]["小晴"]["overrides"] if re.fullmatch(o["match"], line_id))
            post = {"contour": ov["set"]["post"]["contour"]}
        xq["overrides"] = [{"match": line_id, "set": {"synth_text": synth_text, **({"post": post} if post else {})}}]
    ln = {"id": line_id, "cue": line_id[:7], "role": "小晴", "text": LINES[line_id]["text"]}
    x, _ = B.render_line(ln, c, R1.PRON, None, False, "G3 修正第 2 輪 品安對照")
    D = CAST["defaults"]
    y, _ = V.master(x, target=D["target_lufs"], tp_max=D["true_peak_max"], head_ms=D["head_ms"], tail_ms=D["tail_ms"],
                    short_s=D.get("short_line_s", 3.0))
    p = OUT / f"{name}.wav"
    V.write_wav(p, y)
    return p


def seg0_contour(path: Path) -> dict:
    """第一個語音段落（「品安」／「平安」）的 F0（10 ms）與走勢指標。"""
    import parselmouth
    x = V.read_wav(path)
    segs = V.speech_segments(x)
    a, b = segs[0]
    seg = x[int(a * SR):int(b * SR)]
    # 小晴（HsiaoChen +56Hz，F0 約 200–400 Hz）：下限 150 Hz，避免送氣「p」前的低頻雜訊被當成 105–108 Hz 的有聲格
    p = parselmouth.Sound(seg.astype(np.float64), sampling_frequency=SR).to_pitch_ac(time_step=0.01, pitch_floor=150,
                                                                                       pitch_ceiling=500)
    f, t = p.selected_array["frequency"], p.xs()
    v = np.nonzero(f > 0)[0]
    fv = f[v]
    n = len(fv)
    head = fv[:max(1, int(n * 0.55))]               # 第一個音節（品／平）約在有聲段前半
    tail = fv[int(n * 0.65):] if n > 4 else fv      # 第二個音節（安）
    onset = float(np.median(fv[:3]))
    k = int(np.argmin(head))
    fmin = float(head[k])
    low = int(np.sum(head <= fmin * 2 ** (1 / 12)))
    return {"file": str(path.relative_to(V.ROOT)) if path.is_relative_to(V.ROOT) else str(path), "segment_s": [a, b], "voiced_frames": n,
            "onset_hz": round(onset, 1), "min_hz_first55": round(fmin, 1), "min_at_s": round(float(t[v[k]]), 3),
            "fall_from_onset_st": st(onset, fmin), "low_within_1st_ms": low * 10,
            "second_syllable_median_hz": round(float(np.median(tail)), 1),
            "rise_min_to_second_st": st(fmin, float(np.median(tail))),
            "contour_t": [round(float(q), 3) for q in t[v]], "contour_hz": [round(float(q), 1) for q in fv]}


def transcribe_prompt(paths: list[Path], model: str, prompt: str) -> dict[str, str]:
    from faster_whisper import WhisperModel
    if model not in V._WHISPERS:
        V._WHISPERS[model] = WhisperModel(model, device="cpu", compute_type="int8")
    w = V._WHISPERS[model]
    out = {}
    for p in paths:
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             check=True, capture_output=True).stdout
        segs, _ = w.transcribe(np.frombuffer(pcm, dtype=np.float32), language="zh", beam_size=5, initial_prompt=prompt)
        out[str(p)] = V._to_trad("".join(s.text for s in segs).strip())
    return out


def name_of(h: str) -> str:
    h = re.sub(r"[\s，。、！？,.!?;；]", "", h)
    return h[:2]


def do_pinan(xq_cal_f0: float | None) -> dict:
    rep = json.loads((V.VO_DIR / "build_report.json").read_text("utf-8"))
    cases, files = {}, []
    for lid in PINAN_LINES:
        ov = next(o for o in CAST["roles"]["小晴"]["overrides"] if re.fullmatch(o["match"], lid))
        syn = ov["set"]["synth_text"]
        official = V.ROOT / rep[lid]["file"]
        ctrl = render_variant(lid, syn.replace("品安", "平安"), False, f"pinan_ctrl_ping_{lid}")   # 同管線、同分段、不加走勢
        before = render_variant(lid, None, False, f"pinan_before_{lid}")                          # 修正前：整句合成
        segonly = render_variant(lid, syn, False, f"pinan_segonly_{lid}")                         # 只分段、不加走勢
        cases[lid] = {"text": LINES[lid]["text"], "synth_text": syn, "official": seg0_contour(official),
                      "control_ping": seg0_contour(ctrl), "before_whole_sentence": seg0_contour(before),
                      "segment_only": seg0_contour(segonly)}
        files += [("official", lid, official), ("control_ping", lid, ctrl), ("before_whole_sentence", lid, before),
                  ("segment_only", lid, segonly)]
    # 轉寫：(1) 正式提示（與所有轉寫比對相同）；(2) 加人名提示（只用來檢查「品／平」在音檔裡分不分得出來：同時轉寫平安對照檔）
    tx = {}
    for mname in V.ASR_MODELS:
        std = transcribe_prompt([p for _, _, p in files], mname, "以下是繁體中文的台灣華語。")
        hint = transcribe_prompt([p for _, _, p in files], mname, NAME_PROMPT)
        for kind, lid, p in files:
            tx.setdefault(lid, {}).setdefault(kind, {})[mname] = {"standard_prompt": std[str(p)], "name_hint_prompt": hint[str(p)]}
    summary = {}
    for lid in PINAN_LINES:
        c = cases[lid]
        c["transcripts"] = tx[lid]
        o, k, bf = c["official"], c["control_ping"], c["before_whole_sentence"]
        d_st = st(k["min_hz_first55"], o["min_hz_first55"])
        rel = st(xq_cal_f0, o["min_hz_first55"]) if xq_cal_f0 else None
        crit = {"fall_from_onset_le_-4st": o["fall_from_onset_st"] <= -4,
                "min_le_-3st_vs_speaker_calibration_median": rel is not None and rel <= -3,
                "min_ge_2st_below_ping_control": d_st <= -2}
        std_ok = {m: name_of(tx[lid]["official"][m]["standard_prompt"]) == "品安" for m in V.ASR_MODELS}
        disc = {m: (name_of(tx[lid]["official"][m]["name_hint_prompt"]) == "品安"
                    and name_of(tx[lid]["control_ping"][m]["name_hint_prompt"]) == "平安") for m in V.ASR_MODELS}
        summary[lid] = {"official_min_hz": o["min_hz_first55"], "ping_control_min_hz": k["min_hz_first55"],
                        "before_min_hz": bf["min_hz_first55"], "pin_minus_ping_st": d_st,
                        "official_min_vs_speaker_median_st": rel, "official_fall_from_onset_st": o["fall_from_onset_st"],
                        "official_low_within_1st_ms": o["low_within_1st_ms"],
                        "official_rise_to_an_st": o["rise_min_to_second_st"],
                        "ping_control_rise_to_an_st": k["rise_min_to_second_st"],
                        "third_tone_criteria": crit, "third_tone_clear": all(crit.values()),
                        "standard_prompt_transcribed_pinan": std_ok,
                        "name_hint_discriminates_pin_vs_ping": disc}
    both_std = all(all(s["standard_prompt_transcribed_pinan"].values()) for s in summary.values())
    res = {"_說明": "重驗 1 第 2 項。edge-tts 7.3.1 不接受自訂 SSML（沒有 phoneme），先試合成用文字：注音「ㄆㄧㄣˇ安」、拼音「pin3安」、"
                    "空格「品 安」、間隔號「品‧安」都無效（轉寫成「特依恩底三聲安」「片山」「平安」等）。正式檔改為「品安」單獨一段合成，"
                    "再以 PSOLA 把該段 F0 改成半三聲（品低降、安高平）。本檔比較每句第一個語音段落（品安／平安）："
                    "official＝正式檔（audio/vo/*_v03.wav）；control_ping＝同管線、同分段，只把文字換成「平安」且不加走勢；"
                    "before_whole_sentence＝修正前的整句合成；segment_only＝只分段不加走勢。"
                    "F0 以 parselmouth 自相關法、10 ms、150–500 Hz 量測。指標：onset＝前 3 個有聲格中位數；min＝有聲段前 55%（品／平）最低點；low_within_1st＝離最低點 1 半音內的格數 ×10 ms；"
                    "rise＝最低點到後 35%（安）中位數的半音數。三聲判準（本輪自訂、可量測）：從起點降 ≥4 半音、最低點比小晴校準句 F0 中位"
                    "低 ≥3 半音、比平安對照的最低點低 ≥2 半音。轉寫：standard_prompt＝所有轉寫比對共用的提示；name_hint_prompt＝提示裡加"
                    "故事人物名單（只用來檢查音檔裡的品／平分不分得出來：同一提示也轉寫平安對照檔，對照檔仍轉成「平安」才算分得出）。"
                    "聽感未驗證（Claude 聽不到聲音）。",
           "speaker_calibration_f0": xq_cal_f0, "name_hint_prompt": NAME_PROMPT,
           "text_variants_tried": {"ㄆㄧㄣˇ安": "small「特依恩底三生安」／turbo「特意ND三聲鞍」", "pin3安": "small「片山」／turbo「騙三鞍」",
                                   "品 安": "兩個模型都是「平安」", "品‧安": "兩個模型都是「平安」",
                                   "PSOLA 加深（0.62–0.70 倍）不加提示": "small「挺安／平安」、turbo「平安」"},
           "cases": cases, "summary": summary,
           "pass_condition_a_both_models_transcribe_pinan": both_std,
           "pass_condition_b_third_tone_clear_all_lines": all(s["third_tone_clear"] for s in summary.values()),
           "conclusion": None}
    n_disc = sum(1 for s_ in summary.values() if s_["name_hint_discriminates_pin_vs_ping"].get("large-v3-turbo"))
    n_before = sum(1 for lid in PINAN_LINES
                   if name_of(tx[lid]["before_whole_sentence"]["large-v3-turbo"]["name_hint_prompt"]) == "品安")
    res["name_hint_turbo_official_pinan_and_control_ping"] = n_disc
    res["name_hint_turbo_before_pinan"] = n_before
    res["conclusion"] = ("兩個模型（正式提示）都轉成「品安」" if both_std else
                         "做不到通過條件 (a)：正式提示下兩個模型仍把三句的人名轉成常用詞「平安」（語言模型偏好；換寫法與加深走勢都無效）。"
                         "改用通過條件 (b)：附品／平 F0 走勢對照，"
                         + ("三句的「品」都符合三聲判準" if res["pass_condition_b_third_tone_clear_all_lines"] else "部分句子未符合三聲判準（見 summary）")
                         + f"；加人名提示時，large-v3-turbo 把 {n_disc}／{len(PINAN_LINES)} 句正式檔轉成「品安」、同時把平安對照檔轉成「平安」"
                         f"（修正前整句合成 {n_before}／{len(PINAN_LINES)} 句轉成「品安」）；small 加提示後連平安對照檔也寫成「品安」，分不出來。"
                         "聽感未驗證，寫入 DECISIONS.md D-G3-R2-01。")
    (G3 / "tone_check_pinan_r2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    plot_pinan(res)
    return {k: v for k, v in res.items() if k not in ("cases", "_說明", "text_variants_tried")}


def _font(plt):
    from matplotlib import font_manager
    for fam in ("PingFang TC", "Heiti TC", "Arial Unicode MS"):
        if any(fam == f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = fam
            return


def plot_pinan(res: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _font(plt)
    fig, axes = plt.subplots(len(PINAN_LINES), 1, figsize=(10, 3.0 * len(PINAN_LINES)), squeeze=False)
    for ax, lid in zip(axes[:, 0], PINAN_LINES):
        c = res["cases"][lid]
        for key, col, ls, lab in (("official", "#c0392b", "-", "正式檔 品安（分段＋PSOLA 半三聲）"),
                                  ("segment_only", "#e67e22", ":", "品安（只分段）"),
                                  ("before_whole_sentence", "#7f8c8d", "--", "修正前 品安（整句合成）"),
                                  ("control_ping", "#2e86c1", "-", "對照 平安（同管線）")):
            d = c[key]
            t = np.array(d["contour_t"])
            ax.plot(t - t[0], d["contour_hz"], ls, color=col, lw=1.6 if key in ("official", "control_ping") else 1.0, label=lab)
        if res.get("speaker_calibration_f0"):
            ax.axhline(res["speaker_calibration_f0"], color="#555", lw=0.6, ls="-.")
            ax.text(0.005, res["speaker_calibration_f0"] + 4, f"小晴校準句 F0 中位 {res['speaker_calibration_f0']} Hz", fontsize=7, color="#555")
        s = res["summary"][lid]
        ax.set_title(f"{lid}「{c['text']}」　品最低 {s['official_min_hz']} Hz／平最低 {s['ping_control_min_hz']} Hz"
                     f"（差 {s['pin_minus_ping_st']} 半音）；品從起點降 {s['official_fall_from_onset_st']} 半音", fontsize=8)
        ax.set_ylabel("F0（Hz）")
        ax.set_ylim(150, 420)
        ax.legend(fontsize=7, loc="upper right")
    axes[-1, 0].set_xlabel("秒（從第一個語音段落的第一個有聲格起算）")
    fig.suptitle("G3 修正第 2 輪：人名「品安」的「品」（三聲）對「平」（二聲）F0 走勢；聽感未驗證", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(G3 / "tone_check_pinan_r2.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- ±1 LU 的範圍（重驗 1 第 4 項；讀 G4 驗收包的離線混音）
def ebur_x(x: np.ndarray) -> float | None:
    import tempfile, os
    from scipy.io import wavfile
    fd, p = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wavfile.write(p, SR, x.astype(np.float32))
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", p, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    os.unlink(p)
    m = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", r[r.rfind("Summary:"):])
    return float(m.group(1)) if m and m.group(1) != "-inf" else None


def do_loudness() -> dict:
    from scipy.io import wavfile
    pack = V.ROOT / "review" / "G4" / "pack"
    mixp, lp, tp = pack / "audio" / "g4_mix.wav", pack / "audio" / "loudness.json", pack / "timeline.json"
    if not (mixp.exists() and lp.exists() and tp.exists()):
        return {"skipped": "找不到 G4 驗收包混音"}
    sr, x = wavfile.read(mixp)
    x = x.astype(np.float32) / 32768.0
    L, T = json.loads(lp.read_text("utf-8")), json.loads(tp.read_text("utf-8"))
    spans = [(l["start"], l["end"]) for l in L["lines"]]
    cues, featured, under = {}, {}, {}
    for s in T["schedule"]:
        if s["duration"] < 1:
            continue
        a, b = s["start"], s["start"] + s["duration"]
        seg = x[int(a * SR):int(b * SR)]
        mask = np.ones(len(seg), bool)
        for u, v in spans:
            i0, i1 = max(0, int((u - 0.3 - a) * SR)), min(len(mask), int((v + 0.5 - a) * SR))
            if i1 > i0:
                mask[i0:i1] = False
        mo = seg[mask]
        d_sec = round((len(seg) - len(mo)) / SR, 2)
        rec = {"kind": s["kind"], "from_s": a, "to_s": round(b, 3), "cue_I_LUFS": ebur_x(seg),
               "music_only_sec": round(len(mo) / SR, 2), "dialogue_window_sec": d_sec,
               "music_only_I_LUFS": ebur_x(mo) if len(mo) > SR else None}
        cues[s["id"]] = rec
        if rec["music_only_I_LUFS"] is not None:
            (under if s["kind"] == "scene" else featured)[s["id"]] = rec["music_only_I_LUFS"]
    dl = {l["id"]: l["mix_I_LUFS"] for l in L["lines"]}
    vf = {l["id"]: l["vo_file_I_LUFS"] for l in L["lines"]}

    def spread(d):
        v = [q for q in d.values() if q is not None]
        return round(max(v) - min(v), 1) if len(v) > 1 else 0.0
    # 如果裁成「有台詞的 cue 整段 ±1 LU」：a2_c002 的無台詞時段要多響（能量平均估算；只用來說明代價）
    est = None
    c2, c4 = cues.get("a2_c002"), cues.get("a2_c004")
    if c2 and c4 and c2["music_only_I_LUFS"] is not None:
        d_lvl = float(np.mean([dl[k] for k in dl if k.startswith("a2_c002")]))
        target = c4["cue_I_LUFS"] - 2.0
        tm, td = c2["music_only_sec"], c2["dialogue_window_sec"]
        e = (10 ** (target / 10) * (tm + td) - 10 ** (d_lvl / 10) * td) / tm
        need = 10 * math.log10(e) if e > 0 else None
        est = {"a2_c004_cue_I": c4["cue_I_LUFS"], "a2_c002_target_I": round(target, 1),
               "a2_c002_music_only_now": c2["music_only_I_LUFS"],
               "a2_c002_music_only_needed_est": round(need, 1) if need else None,
               "raise_needed_lu_est": round(need - c2["music_only_I_LUFS"], 1) if need else None,
               "dialogue_in_mix_LUFS": round(d_lvl, 1),
               "note": "能量平均估算（無台詞時段 15.6 秒、台詞時段含前後 0.3／0.5 秒）。襯底要升到約對白下 4 LU，"
                       "等於把劇情段的襯底配樂改成和開幕曲一樣的主奏音量；而且開幕、閉幕、署名卡（−20～−21.5）仍和 a2_c004（−15.2）差 >2 LU，"
                       "要讓「全部 cue」都在 ±1 LU 內，主奏配樂得和對白一樣響（約 −15），聲音代理不建議。"}
    res = {"_說明": "重驗 1 第 4 項（主線裁決用）。讀 G4 驗收包離線混音 review/G4/pack/audio/g4_mix.wav（由 tools/g4_review_pack.py 依引擎規則混出）"
                    "與 loudness.json、timeline.json；ffmpeg ebur128 整合響度（含閘門）。無台詞時段＝cue 內扣掉每句台詞前 0.3 秒到後 0.5 秒。",
           "source_mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mixp.stat().st_mtime)),
           "per_cue": cues,
           "dialogue_lines_in_mix_I": dl, "dialogue_lines_spread_lu": spread(dl),
           "vo_files_I": vf, "vo_files_spread_lu": spread(vf),
           "featured_music_passages_I": featured, "featured_music_spread_lu": spread(featured),
           "underscore_passages_I": under, "underscore_spread_lu": spread(under),
           "cue_level_option_estimate": est,
           "proposed_rule": {
               "text": "±1 LU（最大－最小 ≤2 LU）適用於三層：(1) 每個素材檔正規化：配音逐句檔 −18 LUFS、配樂檔與音效依各自目標（music_metrics.json，"
                       "偏離目標 ≤1 LU）；(2) 演出混音中每一句對白的整合響度（對白錨點，全部台詞最大－最小 ≤2 LU）；"
                       "(3) 同一類無台詞配樂段彼此比較：主奏段（開幕、閉幕、署名卡）一組、劇情襯底段（scene cue 內無台詞時段）一組，各自 ≤2 LU。"
                       "整段 cue 的整合響度只列參考，不設 ±1 LU（它取決於台詞佔比：以對白為主的 a2_c004 約 −15、以無台詞動作為主的 a2_c002 約 −20）。",
               "pass_now": None,
               "status": "聲音代理建議；裁決權在主線（REVIEW.md）。主線同意後，把 loudness_json_decision_draft 貼進 tools/g4_review_pack.py 的 "
                         "segment_spread_lu.decision，並加 loudness_json_fields_suggested 四個欄位（數字取本檔）。",
               "caveat": "劇情襯底組目前只有 a2_c002（15.6 秒）與 a2_c004（2.0 秒）兩段，a2_c004 樣本短；G5 各幕完成後要用全劇混音重算。",
               "loudness_json_decision_draft": "已定案（主線，依 review/G3/loudness_scope_r2.json）：±1 LU 適用於素材檔正規化、各句對白在混音中的整合響度、"
                                         "同類無台詞配樂段（主奏段一組、劇情襯底段一組）；整段 cue 只列參考。",
               "loudness_json_fields_suggested": ["dialogue_lines_lu", "featured_music_lu", "underscore_lu", "vo_files_lu"],
           }}
    res["proposed_rule"]["pass_now"] = {"vo_files": res["vo_files_spread_lu"] <= 2.0, "dialogue_lines": res["dialogue_lines_spread_lu"] <= 2.0,
                                        "featured_music": res["featured_music_spread_lu"] <= 2.0, "underscore": res["underscore_spread_lu"] <= 2.0}
    (G3 / "loudness_scope_r2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    return {k: res[k] for k in ("dialogue_lines_spread_lu", "vo_files_spread_lu", "featured_music_passages_I", "featured_music_spread_lu",
                                "underscore_passages_I", "underscore_spread_lu", "cue_level_option_estimate", "proposed_rule")}


# ---------------------------------------------------------------- ElevenLabs 用量（重驗 1 第 11 項）
def do_el() -> dict:
    tot, cats = 0, {}
    for line in (V.VO_DIR / "elevenlabs_usage.jsonl").read_text("utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        try:
            b = int(d.get("billed") or 0)
        except (TypeError, ValueError):
            b = 0
        if d.get("ok") is False:
            b = 0
        p = d.get("purpose", "")
        cat = ("G3 試音（免費方案，03:xx）" if p.startswith("G3") else
               "Starter 升級後探測（06:27）" if p.startswith("Starter") else
               "EL 選角（Starter，06–07 時；review/G3/el/library、design）" if p.startswith("EL 選角") else
               "EL 全劇版試作（Starter，08:27 起；tools/vo_el_prod.py，audio/vo_el/ledger.json）" if p.startswith("EL 全劇") else
               "其他")
        cats[cat] = cats.get(cat, 0) + b
        tot += b
    led = json.loads((V.ROOT / "audio" / "vo_el" / "ledger.json").read_text("utf-8"))
    return {"source": "audio/vo/elevenlabs_usage.jsonl（回應標頭 character-cost 逐筆累加；失敗呼叫不計費）",
            "snapshot": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "EL 全劇版試作由另一個工作流（tools/vo_el_prod.py）執行中，總數會繼續增加；以 audio/vo_el/ledger.json 與本檔為準。",
            "total_billed_chars": tot, "by_category": cats, "vo_el_ledger_total": led.get("total_billed"),
            "this_round_billed": 0,
            "license": "03:xx 的 G3 試音在免費方案下產生：只限非商業用途、公開時須標註 elevenlabs.io（review/G3/samples/A_*、B_*jessica*，不是正式素材）。"
                       "06:30 起為 Starter 付費方案（商用授權，Beta 服務除外）。另受 ElevenLabs 使用政策「Use by and for Minors」："
                       "給 18 歲以下對象的產品須經書面核准（review/G3/el/license_evidence.md）；未取得核准前，ElevenLabs 輸出一律不進演出。"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="roles,ye,pinan,loudness,el")
    args = ap.parse_args()
    only = set(args.only.split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = G3 / "metrics.json"
    metrics = json.loads(mpath.read_text("utf-8"))
    r2 = metrics.get("round2", {})
    r2["_說明"] = ("G3 修正第 2 輪（2026-10-21，tools/vo_g3_r2.py）。audio/vo/casting.json v03：葉護理師 −20%／+55Hz（3 句另設 −25%／−28%）、"
                  "小晴三句「品安」分段＋PSOLA 半三聲、pronounce.json 加「119」→「一一九」；其餘角色參數與第 1 輪相同。"
                  "F0 中位＝代表台詞合併（f0_median_pooled）與同一句校準句「" + R1.CAL + "」（calibration_f0_median）兩種；"
                  "語速比較用校準句。本節取代 round1 的 roles／same_voice_pairs（round1 保留作修正前紀錄）。聽感一律未驗證。ElevenLabs 本輪計費 0 字元。")
    if "roles" in only:
        roles = do_roles()
        r2["roles"] = roles
        r2["calibration_f0_table"] = calibration_table(roles)
        r2["same_voice_pairs"] = pair_checks(roles)
        r2["kids"] = R1.kid_matrix(roles)
        plot_matrix(roles)
        print("同底聲：", "全部通過" if r2["same_voice_pairs"]["all_pass"] else "有未通過",
              "；較嚴規則未通過：", r2["same_voice_pairs"]["strict_failing"])
    roles = r2.get("roles", {})
    if "ye" in only and roles:
        r2["ye"] = ye_checks(roles)
        print("葉護理師：", json.dumps({k: r2["ye"][k] for k in ("calibration_cps", "max_rate_cps_net", "max_rate_cps_net_r", "vs_inviter")},
                                     ensure_ascii=False))
    if "pinan" in only:
        r2["pinan"] = do_pinan(roles.get("xiaoqing", {}).get("calibration_f0_median"))
        print("品安：", json.dumps(r2["pinan"]["summary"], ensure_ascii=False)[:1500])
    if "loudness" in only:
        r2["loudness_scope"] = do_loudness()
        print("響度範圍：", json.dumps(r2["loudness_scope"], ensure_ascii=False)[:800])
    if "el" in only:
        r2["elevenlabs_usage"] = do_el()
        print("ElevenLabs：", r2["elevenlabs_usage"]["total_billed_chars"], r2["elevenlabs_usage"]["by_category"])
    metrics["round2"] = r2
    if "round1" in metrics:
        metrics["round1"]["_取代"] = "roles、same_voice_pairs、kids 已由 round2 重算取代（葉護理師參數改變）；本節保留作修正前紀錄。"
    mpath.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), "utf-8")
    from vo_g3 import write_transcripts
    write_transcripts(metrics)
    print("ok")


if __name__ == "__main__":
    main()
