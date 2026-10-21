"""G3 修正第 1 輪：試音補量與證據（修正清單第 1、2、3、5、6、7、8、10 項）。

用法（專案根目錄）：
  tools/.venv/bin/python tools/vo_g3_r1.py                 # 全部
  tools/.venv/bin/python tools/vo_g3_r1.py --only roles     # 只做角色量測（roles／checklist／tone／spikes／rms，可逗號分隔）
  選項：--no-transcribe（讀音檢查表句子不轉寫）

一律用正式管線：audio/vo/casting.json（v02 參數）→ tools/vo_build.py 的 render_line → vo_lib.master（頭 120 ms、尾 250 ms、
−18 LUFS、真峰值 ≤ −1.5 dBTP、16-bit）。合成有快取；本輪全部 edge-tts，ElevenLabs 計費 0 字元。

輸出：
  review/G3/r1/*.wav                     角色代表台詞、校準句、讀音檢查表句子、聲調對照
  review/G3/metrics.json  → "round1"      角色 F0 中位／語速、同底聲兩兩檢查、四個孩子半音矩陣、旁白↔小宇、葉護理師↔阿樂、
                                          讀音檢查表轉寫（small＋large-v3-turbo）、a2_c002_01 停頓與淨語速、停頓突波
  review/G3/transcripts.md               （由 vo_g3.write_transcripts 重寫，含第 1 輪讀音檢查表）
  review/G3/tone_check_yi_r1.json        「咦？」各種寫法首字 F0 走勢＋正式檔（v01 對 v02）
  review/G3/tone_check_ting.json         必要旁白一「不聽」：一聲「聽」對二聲「停」的 F0 走勢
  review/G3/tone_check_lese.json         「垃圾」：lè sè（樂色）對 lā jī（拉機）的 F0 走勢
  review/G3/pause_spikes.json            所有台詞檔停頓核心的 1 ms 峰值與突波數（門檻 −60 dBFS）
  review/G3/a2_c002_01_rms50.json/.png   a2_c002_01 v01 對 v02 每 50 ms RMS 剖面
  review/G3/voice_matrix_r1.png          角色 F0 中位與語速分布圖
聽感一律未驗證（Claude 聽不到聲音）。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402
import vo_build as B  # noqa: E402

G3 = V.ROOT / "review" / "G3"
OUT = G3 / "r1"
CAST = json.loads((V.VO_DIR / "casting.json").read_text("utf-8"))
PRON = V.load_pronounce()
LINES = V.load_lines()
D = CAST["defaults"]

CAL = "今天放學以後，我們一起去廣場看燈籠。"   # 校準句：所有角色同一句，比較語速（字／秒）
# 角色 → (casting 角色名, 代表台詞, 校準句用的台詞編號：決定套用哪一組 override)
ROLES = {
    "narrator": ("旁白", ["a2_c004_01", "a2_c004_02", "a0_c001_01", "a2_c003_02"], "cal_narrator"),
    "narrator_required": ("旁白", ["a2_c004_02"], "a2_c004_02"),
    "zhezhe": ("折折", ["a2_c001_03", "a0_c003_01", "a0_c002_01", "a3_c004_02"], "cal_zhezhe"),
    "xiaoqing": ("小晴", ["a2_c002_02", "a1_c004_03", "a1_c001_01", "a6_c006_01"], "cal_xiaoqing"),
    "xiaoyu": ("小宇", ["a2_c001_01", "a3_c002_02", "a2_c013_04", "a0_c004_01"], "cal_xiaoyu"),
    "pinan": ("品安", ["a1_c001_02", "a1_c004_06", "a6_c002_03", "a7_c003_01"], "cal_pinan"),
    "ale": ("阿樂叔叔", ["a0_c002_03", "a0_c003_03", "a0_c004_05", "a6_c009_03"], "cal_ale"),
    "ale_affected": ("阿樂叔叔", ["a2_c001_02", "a2_c002_01", "a2_c008_01", "a2_c012_02"], "a2_c001_99"),
    "ye": ("葉護理師", ["a2_c012_01", "a5_c008_05", "a2_c013_03", "a5_c008_03"], "cal_ye"),
    "lin": ("林老師", ["a3_c003_02", "a3_c008_02", "a5_c007_02", "a6_c006_04"], "cal_lin"),
    "chen": ("陳伯伯", ["a4_c012_05", "a4_c013_01", "a5_c001_02"], "cal_chen"),
    "inviter": ("邀請者", ["a1_c002_01", "a1_c002_02", "a1_c004_01", "a3_c001_03"], "cal_inviter"),
    "dispatcher": ("執勤人員", ["a5_c006_01", "a5_c006_03", "a5_c006_05"], "cal_dispatcher"),
}
ROLE_ZH = {"narrator": "旁白", "narrator_required": "旁白（必要旁白）", "zhezhe": "折折", "xiaoqing": "小晴", "xiaoyu": "小宇",
           "pinan": "品安", "ale": "阿樂叔叔（一般段）", "ale_affected": "阿樂叔叔（受影響段）", "ye": "葉護理師", "lin": "林老師",
           "chen": "陳伯伯", "inviter": "邀請者", "dispatcher": "執勤人員"}
KIDS = ["xiaoyu", "xiaoqing", "zhezhe", "pinan"]

# 讀音檢查表（修正清單第 1 項）：劇本句＋一句「垃圾」測試句（劇本沒有含「垃圾」的台詞）
CHECKLIST = [
    ("a0_c001_01", None, "紙燈節"),
    ("a0_c003_01", None, "紙燈節"),
    ("a0_c003_04", None, "紙燈節"),
    ("a0_c002_01", None, "折折"),
    ("a2_c003_02", None, "喪屍煙彈"),
    ("a1_c004_06", None, "燈籠"),
    ("a0_c002_02", None, "燈籠"),
    ("t_lese_01", ("旁白", "折折把地上的垃圾撿起來，丟進垃圾桶。"), "垃圾"),
    ("a3_c004_02", None, "不碰、不試"),
    ("a3_c002_02", None, "不試"),
    ("a6_c003_04", None, "一起"),
]
# 附帶列出（不算在第 1 項的必要句）：含人名「品安」的「一起」句，兩個模型都把「品安」轉成「平安」→ 另做聲調對照
EXTRA = [("a6_c006_01", None, "一起（附帶：人名品安）")]


def render(line_id: str, role: str, text: str, name: str) -> tuple[Path, dict, dict]:
    ln = {"id": line_id, "cue": line_id[:7], "role": role, "text": text}
    x, notes = B.render_line(ln, CAST, PRON, None, False, "G3 修正第 1 輪")
    y, minfo = V.master(x, target=D["target_lufs"], tp_max=D["true_peak_max"], head_ms=D["head_ms"], tail_ms=D["tail_ms"],
                        short_s=D.get("short_line_s", 3.0))
    p = OUT / f"{name}.wav"
    V.write_wav(p, y)
    return p, notes, minfo


def f0_frames(path: Path) -> np.ndarray:
    import parselmouth
    p = parselmouth.Sound(str(path)).to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
    f = p.selected_array["frequency"]
    return f[f > 0]


def st(a: float, b: float) -> float:
    return round(12 * math.log2(b / a), 2)


def spec_of(role: str, line_id: str) -> dict:
    s = B.resolve_spec(CAST, role, line_id, None)
    return {k: s.get(k) for k in ("voice", "rate", "pitch", "segment_rates") if s.get(k) is not None} | (
        {"telephone": True} if s.get("post", {}).get("telephone") else {})


def do_roles() -> dict:
    res = {}
    for code, (role, ids, cal_id) in ROLES.items():
        frames, per = [], []
        for lid in ids:
            p, notes, _ = render(lid, role, LINES[lid]["text"], f"{code}_{lid}")
            m = V.measure(p, LINES[lid]["text"])
            f = f0_frames(p)
            frames.append(f)
            per.append({"line": lid, "text": LINES[lid]["text"], "file": m["file"], "f0_median": m["f0_median"],
                        "rate_cps": m["rate_cps"], "rate_cps_net": m["rate_cps_net"], "rate_cps_net_r": m["rate_cps_net_r"],
                        "pause_spikes": m["pause_spikes"], "integrated_lufs": m["integrated_lufs"],
                        "true_peak_dbtp": m["true_peak_dbtp"], "clipped_samples": m["clipped_samples"]})
        pc, _, _ = render(cal_id, role, CAL, f"{code}_calibration")
        mc = V.measure(pc, CAL)
        allf = np.concatenate(frames)
        res[code] = {"role_zh": ROLE_ZH[code], "spec": spec_of(role, ids[0] if code != "narrator_required" else "a2_c004_02"),
                     "f0_median_pooled": round(float(np.median(allf)), 1),
                     "f0_p10": round(float(np.percentile(allf, 10)), 1), "f0_p90": round(float(np.percentile(allf, 90)), 1),
                     "rate_cps_mean": round(float(np.mean([q["rate_cps"] for q in per])), 2),
                     "calibration_cps": mc["rate_cps"], "calibration_file": mc["file"], "lines": per}
        print(f"{code:18s} F0 {res[code]['f0_median_pooled']:6.1f}  校準句 {mc['rate_cps']} 字/秒  {res[code]['spec']}")
    return res


def pair_checks(r: dict) -> dict:
    """同底聲兩兩檢查（修正清單第 2 項）：語速差＝校準句字／秒相對差；語速差 <5% 的兩個角色，F0 中位差須 ≥10%。"""
    codes = [c for c in r if c != "narrator_required"] + ["narrator_required"]
    rows = []
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            if r[a]["spec"]["voice"] != r[b]["spec"]["voice"]:
                continue
            if {a, b} in ({"ale", "ale_affected"}, {"narrator", "narrator_required"}):
                continue
            fa, fb = r[a]["f0_median_pooled"], r[b]["f0_median_pooled"]
            ca, cb = r[a]["calibration_cps"], r[b]["calibration_cps"]
            rate_diff = abs(ca - cb) / min(ca, cb) * 100
            f0_diff = abs(fa - fb) / min(fa, fb) * 100
            need_f0 = rate_diff < 5
            rows.append({"a": ROLE_ZH[a], "b": ROLE_ZH[b], "voice": r[a]["spec"]["voice"],
                         "rate_param": [r[a]["spec"].get("rate"), r[b]["spec"].get("rate")],
                         "calibration_cps": [ca, cb], "rate_diff_pct": round(rate_diff, 1),
                         "f0": [fa, fb], "f0_diff_pct": round(f0_diff, 1), "semitones": abs(st(fa, fb)),
                         "rule": "語速差 <5% → F0 差須 ≥10%" if need_f0 else "語速差 ≥5%（F0 不設門檻）",
                         "pass": (f0_diff >= 10) if need_f0 else True})
    return {"rows": rows, "all_pass": all(x["pass"] for x in rows),
            "inviter_f0": r["inviter"]["f0_median_pooled"],
            "inviter_in_neutral_145_175": 145 <= r["inviter"]["f0_median_pooled"] <= 175}


def kid_matrix(r: dict) -> dict:
    m = {}
    for a in KIDS:
        for b in KIDS:
            if a < b:
                m[f"{ROLE_ZH[a]}↔{ROLE_ZH[b]}"] = abs(st(r[a]["f0_median_pooled"], r[b]["f0_median_pooled"]))
    vs_xy = {ROLE_ZH[b]: abs(st(r["xiaoyu"]["f0_median_pooled"], r[b]["f0_median_pooled"])) for b in KIDS if b != "xiaoyu"}
    return {"f0": {ROLE_ZH[k]: r[k]["f0_median_pooled"] for k in KIDS}, "pairwise_semitones": m,
            "xiaoyu_vs_others_semitones": vs_xy, "xiaoyu_vs_each_ge3": all(v >= 3 for v in vs_xy.values()),
            "all_pairs_ge3": all(v >= 3 for v in m.values()),
            "note": "小宇和其他三個孩子都差 ≥3 半音。小晴↔折折約 1 半音：edge-tts HsiaoYu 的音高在 +90Hz 以上不再升高（折折上限約 294 Hz），"
                    "小晴又要比小宇高 3 半音（≥271 Hz），兩者無法再拉開；改靠不同底聲（HsiaoChen 對 HsiaoYu）與語速（+0% 對 +22%）區分，"
                    "聽感留到第 3 天彩排。"}


def do_checklist(transcribe: bool) -> dict:
    items, rows = [], []
    for lid, alt, word in CHECKLIST + EXTRA:
        role, text = alt if alt else (LINES[lid]["role"], LINES[lid]["text"])
        p, notes, _ = render(lid if not alt else "t_lese_01", role, text, f"check_{lid}")
        syn = V.strip_breaks(notes["specs"][0]["synth_text"])
        items.append((p, text, syn))
        rows.append({"line": lid, "role": role, "text": text, "synth_text": syn, "check_word": word,
                     "spec": spec_of(role, lid), "file": str(p.relative_to(V.ROOT)),
                     "in_script": alt is None, "required": (lid, alt, word) in CHECKLIST})
    if transcribe:
        tc = V.transcribe_compare(items)
        for row, (p, _, _) in zip(rows, items):
            t = tc[str(p)]
            row["transcript"] = t
            strict = []
            for mname, m in t["models"].items():
                bad = [d for d in m["diffs"] if d["kind"] != "同音字（讀音一致）"]
                badw = [c for c in m["checks"] if c["status"].startswith("不一致")]
                strict.append(not bad and not badw)
            row["pass_strict"] = all(strict)     # 兩個模型都沒有任何非同音差異、檢查詞都一致或同音
            row["check_words_ok"] = all(not c["status"].startswith("不一致") for m in t["models"].values() for c in m["checks"])
            print(f"  {row['line']} " + "｜".join(f"{k}：{v['hyp_trad']}" for k, v in t["models"].items()) + f"｜嚴格通過 {row['pass_strict']}")
    req = [r for r in rows if r["required"]]
    return {"rows": rows,
            "required_check_words_ok_both_models": all(r.get("check_words_ok") for r in req) if transcribe else None,
            "required_all_pass_strict": all(r.get("pass_strict") for r in req) if transcribe else None,
            "required_failing_strict": [r["line"] for r in req if transcribe and not r.get("pass_strict")]}


# ---------------------------------------------------------------- 聲調對照
def islands(x: np.ndarray, floor: float = 60, ceil: float = 500, min_ms: int = 40) -> list[dict]:
    import parselmouth
    p = parselmouth.Sound(x.astype(np.float64), sampling_frequency=V.SR).to_pitch_ac(time_step=0.01, pitch_floor=floor,
                                                                                       pitch_ceiling=ceil)
    f, ts = p.selected_array["frequency"], p.xs()
    out, i = [], 0
    while i < len(f):
        if f[i] > 0:
            j = i
            while j + 1 < len(f) and f[j + 1] > 0:
                j += 1
            if (j - i + 1) * 10 >= min_ms:
                seg = f[i:j + 1]
                n = max(1, len(seg) // 5)
                a, b = float(np.median(seg[:n])), float(np.median(seg[-n:]))
                out.append({"t0": round(float(ts[i]), 3), "t1": round(float(ts[j]), 3), "mean_hz": round(float(seg.mean()), 1),
                            "start_hz": round(a, 1),
                            "end_hz": round(b, 1), "end_over_start": round(b / a, 3),
                            "contour_hz_20ms": [round(float(q)) for q in seg[::2]]})
            i = j + 1
        else:
            i += 1
    return out


def synth_plain(spec: dict, text: str) -> np.ndarray:
    raw, _ = V.synth_raw({k: v for k, v in spec.items() if k in ("service", "voice", "rate", "pitch")}, text,
                         purpose="G3 修正第 1 輪 聲調對照")
    x, _ = V.declick(V.decode(raw))
    return x


def do_tone() -> dict:
    out = {}
    # 1)「咦？」：阿樂 a2_c002_01 第一段的聲線參數（YunJhe −8%），各種寫法單獨合成，比較首字走勢
    ale = B.resolve_spec(CAST, "阿樂叔叔", "a2_c002_01", None)
    s_ale = {"service": "edge", "voice": ale["voice"], "rate": ale["segment_rates"][0], "pitch": ale.get("pitch", "+0Hz")}
    var = {}
    for t in ["咦？", "咦——？", "咦？？", "咦…？", "疑？", "移？", "姨？", "欸？", "咦，怎麼了？"]:
        var[t] = V.first_syllable_rise(synth_plain(s_ale, t))
    files = {}
    for v in ("v01", "v02"):
        p = V.VO_DIR / f"vo_a2_c002_01_{v}.wav"
        if p.exists():
            files[v] = V.first_syllable_rise(V.read_wav(p))
    yi = {"_說明": "修正清單第 10 項。同一聲線（YunJhe，a2_c002_01 第一段語速 −8%）把「咦？」換成各種寫法單獨合成，量第一個有聲段 F0 "
                   "（前 20% 中位數＝起點、後 20% 中位數＝終點）。所有寫法終點／起點都 ≤1.13（換寫法無效），所以正式檔改用「拆句＋加升調」："
                   "「咦？」單獨一段合成，再以 Praat PSOLA 把該段 F0 改成二聲走勢（起點 → 35% 處 0.97 倍 → 終點 1.28 倍），不改長度、不變速。"
                   "通過條件：正式檔首字終點比起點高 ≥15%。聽感未驗證（第 3 天彩排確認）。",
          "voice_spec": s_ale, "variants": var, "official_files": files,
          "pass": bool(files.get("v02") and files["v02"]["end_over_start"] >= 1.15)}
    (G3 / "tone_check_yi_r1.json").write_text(json.dumps(yi, ensure_ascii=False, indent=1), "utf-8")
    out["yi"] = {"v02_end_over_start": files.get("v02", {}).get("end_over_start"),
                 "v01_end_over_start": files.get("v01", {}).get("end_over_start"), "pass": yi["pass"]}
    # 2)「不聽」：必要旁白的聲線參數；整句（第二句）與短框句，「聽」（一聲）對「停」（二聲）
    nar = B.resolve_spec(CAST, "旁白", "a2_c004_02", None)
    s_nar = {"service": "edge", "voice": nar["voice"], "rate": nar["rate"], "pitch": nar.get("pitch", "+0Hz")}
    sent = "毒品可能讓人的頭腦和身體受到影響，{}使喚。"
    ting = {"_說明": "修正清單第 6 項（方法同 tone_check_yi.json）：必要旁白一的第二句，small 模型把「不聽」轉成「不停」。"
                     "用正式必要旁白參數，把「聽」（tīng 一聲）換成「停」（tíng 二聲）各合成一次，量目標音節的 F0 走勢："
                     "短框句「不聽使喚。」取第 2 個有聲段（不｜聽｜使｜喚，送氣 t、sh、h 把有聲段隔開）；整句取倒數第 3 個有聲段。"
                     "一聲＝高平（終點／起點約 0.95–1.05），二聲＝上升（> 1.10）。聽感未驗證，第 3 天彩排確認。",
            "voice_spec": s_nar, "cases": {}}
    for key, ch in (("聽（一聲）", "不聽"), ("停（二聲）", "不停")):
        xs = synth_plain(s_nar, f"{ch}使喚。")
        isl = islands(xs)
        xl = synth_plain(s_nar, sent.format(ch))
        isl_l = islands(xl)
        ting["cases"][key] = {"short_frame": f"{ch}使喚。", "short_target": isl[1] if len(isl) > 1 else None,
                              "short_islands": len(isl),
                              "sentence": sent.format(ch), "sentence_target": isl_l[-3] if len(isl_l) >= 3 else None,
                              "sentence_islands": len(isl_l)}
    p = V.VO_DIR / "vo_a2_c004_02_v02.wav"
    if p.exists():
        # 正式檔：第二句在兩個 1.3 秒停頓之間；取第二段語音的倒數第 3 個有聲段
        x = V.read_wav(p)
        cores = V.pause_cores(x)
        if len(cores) >= 2:
            seg = x[cores[0][1]:cores[-1][0]]
            isl = islands(seg)
            ting["official_v02_target"] = isl[-3] if len(isl) >= 3 else None
    a = ting["cases"]["聽（一聲）"]
    b = ting["cases"]["停（二聲）"]
    ting["summary"] = {k: {"聽_end_over_start": (a[k] or {}).get("end_over_start"), "停_end_over_start": (b[k] or {}).get("end_over_start"),
                           "聽_mean_hz": (a[k] or {}).get("mean_hz"), "停_mean_hz": (b[k] or {}).get("mean_hz"),
                           "聽_over_停_mean": round((a[k] or {}).get("mean_hz", 0) / max(1e-6, (b[k] or {}).get("mean_hz", 1)), 3)}
                       for k in ("short_target", "sentence_target")}
    ting["結論"] = ("合成器把「聽」讀成高平調（一聲）：短框句與整句裡，「聽」的走勢平（終點／起點約 0.97–1.00），而且平均 F0 比同位置的「停」"
                  "高約 15–20%；「停」起點較低、先降再回升（台灣華語二聲常見的低升形）。兩者在音高上可清楚分開，所以 small 的「不停」"
                  "判讀為轉寫誤差（large-v3-turbo 轉寫為「不聽」）。聽感未驗證，第 3 天彩排確認。")
    ting["summary"]["official_v02"] = (ting.get("official_v02_target") or {}).get("end_over_start")
    (G3 / "tone_check_ting.json").write_text(json.dumps(ting, ensure_ascii=False, indent=1), "utf-8")
    out["ting"] = ting["summary"]
    # 3)「垃圾」：台灣常用 lè sè（四聲＋四聲）對 lā jī（一聲＋一聲）
    lese = {"_說明": "讀音檢查表：「垃圾」台灣常用 lè sè。轉寫兩種讀音都會寫成「垃圾」，看不出來；改用 F0 走勢對照："
                     "同一聲線（旁白）單獨合成「垃圾。」「樂色。」（lè sè，兩個四聲＝下降）「拉機。」（lā jī，兩個一聲＝高平），"
                     "比較兩個有聲段的終點／起點。聽感未驗證。", "voice_spec": {k: v for k, v in s_nar.items()}, "cases": {}}
    for t in ("垃圾。", "樂色。", "拉機。"):
        lese["cases"][t] = islands(synth_plain(s_nar, t))[:2]
    (G3 / "tone_check_lese.json").write_text(json.dumps(lese, ensure_ascii=False, indent=1), "utf-8")
    out["lese"] = {t: [i["end_over_start"] for i in v] for t, v in lese["cases"].items()}
    # 4) 人名「品安」：兩個轉寫模型都寫成「平安」（附帶發現，G5 用）。小晴聲線合成「品安，」「平安，」，比較第一個有聲段
    #    （in＋an 連在一起）前 40% 的走勢：品＝三聲（接一聲時為半三聲，低而略降），平＝二聲（上升）
    xq = B.resolve_spec(CAST, "小晴", "a6_c006_01", None)
    s_xq = {"service": "edge", "voice": xq["voice"], "rate": xq["rate"], "pitch": xq.get("pitch", "+0Hz")}
    pa = {"_說明": "附帶發現：a6_c006_01「品安，我在乎你」兩個轉寫模型都把人名「品安」寫成常用詞「平安」。用小晴正式參數合成"
                   "「品安，我在乎你。」與「平安，我在乎你。」，比較第一個有聲段（品／平＋安）前 40% 的 F0：三聲（半三聲）低而平或略降，"
                   "二聲明顯上升。聽感未驗證；G5 量產時若仍需要，轉寫比對可加人名提示詞。", "voice_spec": s_xq, "cases": {}}
    for t in ("品安，我在乎你。", "平安，我在乎你。"):
        isl = islands(synth_plain(s_xq, t))
        if isl:
            c = isl[0]["contour_hz_20ms"]
            k = max(2, int(len(c) * 0.4))
            pa["cases"][t] = {"island": isl[0], "first40pct_end_over_start": round(c[k - 1] / c[0], 3) if c[0] else None}
    (G3 / "tone_check_pinan.json").write_text(json.dumps(pa, ensure_ascii=False, indent=1), "utf-8")
    out["pinan"] = {t: v["first40pct_end_over_start"] for t, v in pa["cases"].items()}
    print("聲調：", json.dumps(out, ensure_ascii=False))
    return out


def do_spikes() -> dict:
    rows = {}
    for p in sorted(V.VO_DIR.glob("vo_*.wav")) + sorted(OUT.glob("*.wav")):
        r = V.pause_spikes(V.read_wav(p))
        rows[str(p.relative_to(V.ROOT))] = {k: r[k] for k in ("pauses_checked", "spikes", "max_core_peak_dbfs")} | {
            "detail": r["detail"]}
    cur = {k: v for k, v in rows.items() if "_v01" not in k}
    res = {"_說明": "修正清單第 5 項：停頓核心＝句中停頓（10 ms RMS 低於最大值 −35 dB、≥150 ms）裡，前一個字衰減到 −66 dBFS 以下"
                    "（10 ms 滑動最大值連續 20 ms）之後、下一個字起音之前的範圍；前後各留 10 ms。突波＝核心內 1 ms 峰值 > −60 dBFS "
                    "且比核心中位數高 ≥15 dB。v01 為修正前（對照），其餘為修正後（v02 正式檔與 r1 試音）。",
           "files": rows,
           "v01_spikes_total": sum(v["spikes"] for k, v in rows.items() if "_v01" in k),
           "current_spikes_total": sum(v["spikes"] for v in cur.values()),
           "current_max_core_peak_dbfs": max((v["max_core_peak_dbfs"] for v in cur.values() if v["max_core_peak_dbfs"] is not None),
                                             default=None),
           "pass": all(v["spikes"] == 0 for v in cur.values())}
    (G3 / "pause_spikes.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    print(f"停頓突波：修正前 {res['v01_spikes_total']}、修正後 {res['current_spikes_total']}（核心最大峰值 {res['current_max_core_peak_dbfs']} dBFS）")
    return {k: res[k] for k in ("v01_spikes_total", "current_spikes_total", "current_max_core_peak_dbfs", "pass")}


def do_rms() -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for fam in ("PingFang TC", "Heiti TC", "Arial Unicode MS"):
        if any(fam == f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = fam
            break
    text = LINES["a2_c002_01"]["text"]
    res = {"_說明": "修正清單第 4 項：a2_c002_01 每 50 ms 的 RMS（dBFS，50 ms 窗、不重疊）。停頓＝語音區間內 10 ms RMS 低於最大值 −35 dB、"
                    "≥150 ms（vo_lib.measure）；驗收者算法＝−40 dB、≥200 ms（rate_cps_net_r）。通過條件：「咦」之後的停頓 ≤600 ms、"
                    "「揮手……」之後的停頓 ≥500 ms、淨語速 ≤4.5 字／秒。", "files": {}}
    fig, axes = plt.subplots(2, 1, figsize=(12, 5), sharex=True)
    for ax, v in zip(axes, ("v01", "v02")):
        p = V.VO_DIR / f"vo_a2_c002_01_{v}.wav"
        if not p.exists():
            continue
        x = V.read_wav(p)
        n = len(x) // 2400
        rms = 20 * np.log10(np.sqrt((x[:n * 2400].reshape(n, 2400) ** 2).mean(1)) + 1e-9)
        m = V.measure(p, text)
        res["files"][v] = {"file": m["file"], "seconds": m["seconds"], "rms_50ms_dbfs": [round(float(q), 1) for q in rms],
                           "pauses_ms": m["pauses_ms"], "pauses_ms_r": m["pauses_ms_r"], "rate_cps": m["rate_cps"],
                           "rate_cps_net": m["rate_cps_net"], "rate_cps_net_r": m["rate_cps_net_r"],
                           "pause_spikes": m["pause_spikes"]}
        ax.step(np.arange(n) * 0.05, rms, where="post", color="#335")
        ax.axhline(-60, color="#c33", lw=0.6, ls="--")
        for a, b in V.pause_cores(x):
            ax.axvspan(a / V.SR, b / V.SR, color="#9c9", alpha=0.3)
        ax.set_ylim(-100, 0)
        ax.set_ylabel(f"{v}\nRMS dBFS", rotation=0, ha="right", va="center")
        ax.text(0.01, 0.92, f"{v}：停頓 {m['pauses_ms']} ms（驗收者算法 {m['pauses_ms_r']}）｜毛 {m['rate_cps']}／淨 {m['rate_cps_net']}"
                            f"（驗收者算法 {m['rate_cps_net_r']}）字/秒｜停頓突波 {m['pause_spikes']}", transform=ax.transAxes, fontsize=8)
    axes[-1].set_xlabel("秒（綠底＝停頓核心；紅虛線＝−60 dBFS）")
    fig.suptitle("a2_c002_01「咦？我想揮手……手怎麼跑到旁邊去了？」每 50 ms RMS：v01（修正前）對 v02", fontsize=9)
    fig.tight_layout()
    fig.savefig(G3 / "a2_c002_01_rms50.png", dpi=110)
    plt.close(fig)
    v2 = res["files"].get("v02")
    if v2:
        p_after_yi = v2["pauses_ms"][0] if v2["pauses_ms"] else None
        p_after_wave = v2["pauses_ms"][1] if len(v2["pauses_ms"]) > 1 else None
        res["check"] = {"pause_after_yi_ms": p_after_yi, "pause_after_huishou_ms": p_after_wave,
                        "pause_after_yi_ms_r": v2["pauses_ms_r"][0] if v2["pauses_ms_r"] else None,
                        "pause_after_huishou_ms_r": v2["pauses_ms_r"][1] if len(v2["pauses_ms_r"]) > 1 else None,
                        "rate_cps_net": v2["rate_cps_net"], "rate_cps_net_r": v2["rate_cps_net_r"],
                        "pass": bool(p_after_yi and p_after_yi <= 600 and p_after_wave and p_after_wave >= 500
                                     and v2["rate_cps_net"] <= 4.5 and v2["rate_cps_net_r"] <= 4.5)}
    (G3 / "a2_c002_01_rms50.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    print("a2_c002_01：", json.dumps(res.get("check"), ensure_ascii=False))
    return res.get("check", {})


def plot_matrix(r: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for fam in ("PingFang TC", "Heiti TC", "Arial Unicode MS"):
        if any(fam == f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = fam
            break
    col = {"zh-TW-HsiaoChenNeural": "#c0392b", "zh-TW-HsiaoYuNeural": "#2e86c1", "zh-TW-YunJheNeural": "#27ae60"}
    fig, ax = plt.subplots(figsize=(10, 6))
    for code, v in r.items():
        c = col.get(v["spec"]["voice"], "#555")
        ax.errorbar(v["calibration_cps"], v["f0_median_pooled"], yerr=[[v["f0_median_pooled"] - v["f0_p10"]],
                    [v["f0_p90"] - v["f0_median_pooled"]]], fmt="o", color=c, alpha=0.8, capsize=3)
        ax.annotate(f"{v['role_zh']} {v['f0_median_pooled']:.0f}", (v["calibration_cps"], v["f0_median_pooled"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_yscale("log")
    ax.set_yticks([80, 100, 125, 150, 175, 200, 250, 300, 400])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.axhspan(145, 175, color="#999", alpha=0.12)
    ax.set_xlabel("校準句語速（字／秒，同一句）")
    ax.set_ylabel("F0 中位（Hz，對數軸；誤差棒 p10–p90）")
    ax.set_title("G3 修正第 1 輪：角色 F0 中位 × 語速（紅＝HsiaoChen、藍＝HsiaoYu、綠＝YunJhe；灰帶＝邀請者中性區 145–175 Hz）",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(G3 / "voice_matrix_r1.png", dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="roles,checklist,tone,spikes,rms")
    ap.add_argument("--no-transcribe", action="store_true")
    args = ap.parse_args()
    only = set(args.only.split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = G3 / "metrics.json"
    metrics = json.loads(mpath.read_text("utf-8"))
    r1 = metrics.get("round1", {})
    r1["_說明"] = ("G3 修正第 1 輪（2026-10-21，tools/vo_g3_r1.py）。全部用 audio/vo/casting.json v02 參數走正式管線；"
                  "F0 中位＝該角色代表台詞（3–4 句）全部有聲格合併取中位數（parselmouth，75–700 Hz）；語速比較用同一句校準句"
                  f"「{CAL}」。半音＝12·log2(F0 比)。聽感一律未驗證。ElevenLabs 本輪計費 0 字元。")
    if "roles" in only:
        roles = do_roles()
        r1["roles"] = roles
        r1["same_voice_pairs"] = pair_checks(roles)
        r1["kids"] = kid_matrix(roles)
        r1["narrator_vs_xiaoyu"] = {"narrator": roles["narrator"]["f0_median_pooled"],
                                    "xiaoyu": roles["xiaoyu"]["f0_median_pooled"],
                                    "diff_pct": round((roles["xiaoyu"]["f0_median_pooled"] / roles["narrator"]["f0_median_pooled"] - 1) * 100, 1),
                                    "narrator_required": roles["narrator_required"]["f0_median_pooled"],
                                    "pass_ge12pct": roles["xiaoyu"]["f0_median_pooled"] >= 1.12 * max(
                                        roles["narrator"]["f0_median_pooled"], roles["narrator_required"]["f0_median_pooled"])}
        r1["ye_vs_ale"] = {"ye": roles["ye"]["f0_median_pooled"], "ale": roles["ale"]["f0_median_pooled"],
                           "ale_affected": roles["ale_affected"]["f0_median_pooled"],
                           "semitones_vs_ale": abs(st(roles["ale"]["f0_median_pooled"], roles["ye"]["f0_median_pooled"])),
                           "semitones_vs_ale_affected": abs(st(roles["ale_affected"]["f0_median_pooled"], roles["ye"]["f0_median_pooled"])),
                           "calibration_cps": {"ye": roles["ye"]["calibration_cps"], "ale": roles["ale"]["calibration_cps"],
                                               "ale_affected": roles["ale_affected"]["calibration_cps"]}}
        r1["ye_vs_ale"]["pass_ge4_semitones"] = min(r1["ye_vs_ale"]["semitones_vs_ale"], r1["ye_vs_ale"]["semitones_vs_ale_affected"]) >= 4
        r1["ye_vs_ale"]["rate_diff_cps_min"] = round(min(abs(roles["ye"]["calibration_cps"] - roles["ale"]["calibration_cps"]),
                                                         abs(roles["ye"]["calibration_cps"] - roles["ale_affected"]["calibration_cps"])), 2)
        plot_matrix(roles)
        print(json.dumps({k: r1[k] for k in ("kids", "narrator_vs_xiaoyu", "ye_vs_ale")}, ensure_ascii=False))
        print("同底聲：", "全部通過" if r1["same_voice_pairs"]["all_pass"] else "有未通過")
    if "checklist" in only:
        r1["checklist"] = do_checklist(not args.no_transcribe)
    if "tone" in only:
        r1["tone"] = do_tone()
    if "spikes" in only:
        r1["pause_spikes"] = do_spikes()
    if "rms" in only:
        r1["a2_c002_01"] = do_rms()
    metrics["round1"] = r1
    mpath.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), "utf-8")
    from vo_g3 import write_transcripts
    write_transcripts(metrics)
    print("ok")


if __name__ == "__main__":
    main()
