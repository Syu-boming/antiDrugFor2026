"""G3 修正第 1 輪：混音參數離線模擬（修正清單第 9、11、12 項的「聲音那一半」）。

用法：/opt/anaconda3/bin/python3 tools/vo_mixsim.py
讀：review/G4/pack/timeline.json（G4 擷取時的 cue 時間）、app/cues/g4.json（台詞與音效的相對時間）、audio/vo 最新版配音（v02）。
做：沿用 tools/g4_review_pack.py 的 mix()（同一套引擎混音規則），只替換
    1) 配音改用最新版本並依 cue 規則重排台詞時間（相對時間 "X.end+秒"、預設句間 0.45 s、cue 長度＝最後一句結束＋tail），
    2) 對白避讓常數（DUCK_LEVEL、DUCK_BRIDGE；其餘照 app/src/audio/ducking.ts），
    3) 教師停格（final_waiting）時配樂匯流排淡到 FREEZE_LEVEL×基準音量（時間常數 FREEZE_TC），
    場景 cue 的教師停格一律假設 6 秒（G4 擷取時只有 2 秒，量不到「3 秒內」）。
寫：review/G3/mix_r1.json（各方案的對白−背景差、必要旁白句間停頓的背景響度、停格第 3 秒的響度、各段整合響度與差距）、
    review/G3/mix_r1.png（建議方案的分軌與瞬間響度）。
這是給引擎的建議值；正式數字要等引擎改常數後由 tools/g4_review_pack.mjs 重出 review/G4/pack/audio/loudness.json。
"""
from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import g4_review_pack as P  # noqa: E402
import vo_lib as V  # noqa: E402

SR = P.SR
HOLD_SCENE = 6.0
LINE_GAP = 0.45
FREEZE_TC = 0.6
DK_SRC = (ROOT / "app/src/audio/ducking.ts").read_text(encoding="utf-8")
DK0 = {k: float(re.search(rf"export const {k} = ([\d.]+)", DK_SRC).group(1)) for k in
       ("DUCK_LEVEL", "DUCK_LEAD", "DUCK_TC_DOWN", "DUCK_RELEASE", "DUCK_TC_UP", "DUCK_BRIDGE")}

VARIANTS = {
    "現行（0.32／0.9，無停格淡出）": {"DUCK_LEVEL": DK0["DUCK_LEVEL"], "DUCK_BRIDGE": DK0["DUCK_BRIDGE"], "freeze": None},
    "0.50／0.9＋停格 0.10": {"DUCK_LEVEL": 0.50, "DUCK_BRIDGE": 0.9, "freeze": 0.10},
    "0.56／0.9＋停格 0.10": {"DUCK_LEVEL": 0.56, "DUCK_BRIDGE": 0.9, "freeze": 0.10},
    "0.63／0.9＋停格 0.10": {"DUCK_LEVEL": 0.63, "DUCK_BRIDGE": 0.9, "freeze": 0.10},
    "0.56／2.0＋停格 0.10": {"DUCK_LEVEL": 0.56, "DUCK_BRIDGE": 2.0, "freeze": 0.10},
    "0.56／0.9＋停格 0（靜音）": {"DUCK_LEVEL": 0.56, "DUCK_BRIDGE": 0.9, "freeze": 0.0},
}


def latest_vo(aid: str) -> Path | None:
    """配音、配樂、音效都取最新版本（同 tools/pack.mjs）。"""
    d = V.VO_DIR if aid.startswith("vo_") else ROOT / "audio" / ("music" if aid.startswith("music_") else "sfx")
    c = sorted(d.glob(f"{aid}_v*.wav"), key=lambda p: int(re.search(r"_v(\d+)\.wav$", p.name).group(1)))
    return c[-1] if c else None


def retime(tl: dict) -> dict:
    tl = copy.deepcopy(tl)
    cj = {c["id"]: c for c in json.loads((ROOT / "app/cues/g4.json").read_text("utf-8"))["cues"]}
    for aid, a in tl["audio"].items():
        p = latest_vo(aid)
        if p and str(p.relative_to(ROOT)) != a["source"]:
            a["source"] = str(p.relative_to(ROOT))
            a["duration"] = round(V.read_wav(p).shape[0] / V.SR, 3)
    for c in tl["cues"]:
        src = cj.get(c["id"], {})
        if not c["lines"]:
            continue
        old_last = max(l["end"] for l in c["lines"])
        ends, prev = {}, None
        for l, lj in zip(c["lines"], src.get("lines", [])):
            dur = tl["audio"][l["audioId"]]["duration"]
            s = lj.get("start")
            if isinstance(s, (int, float)):
                st = float(s)
            elif isinstance(s, str):
                m = re.match(r"(\w+)\.end\+([\d.]+)", s)
                st = ends[m.group(1)] + float(m.group(2))
            else:
                st = prev + LINE_GAP if prev is not None else float(src.get("voStart", 0.0))
            o_s, o_e = l["start"], l["end"]
            l["start"], l["end"], l["duration"] = round(st, 3), round(st + dur, 3), dur
            # 字幕分頁：引擎依字數比例分配（app/src/cues/timeline.ts paginate），比例不變、按新長度縮放
            for pg in l.get("pages", []):
                a0 = (pg["start"] - o_s) / max(1e-6, o_e - o_s)
                a1 = (pg["end"] - o_s) / max(1e-6, o_e - o_s)
                pg["start"], pg["end"] = round(st + a0 * dur, 3), round(st + a1 * dur, 3)
            ends[l["id"]] = l["end"]
            prev = l["end"]
        for x, xj in zip(c["sfx"], src.get("sfx", [])):
            if isinstance(xj.get("at"), str):
                m = re.match(r"(\w+)\.end\+([\d.]+)", xj["at"])
                x["at"] = round(ends[m.group(1)] + float(m.group(2)), 3)
        new_last = max(l["end"] for l in c["lines"])
        c["duration"] = round(c["duration"] + (new_last - old_last), 3)
    t = 0.0
    dur = {c["id"]: c["duration"] for c in tl["cues"]}
    for s in tl["schedule"]:
        s["start"] = round(t, 3)
        s["duration"] = dur[s["id"]]
        if s["kind"] == "scene":
            s["hold"] = HOLD_SCENE
        t += s["duration"] + s["hold"]
    tl["totalPlaybackSec"] = round(t, 3)
    return tl


def run(tl: dict, v: dict) -> dict:
    c = dict(DK0, DUCK_LEVEL=v["DUCK_LEVEL"], DUCK_BRIDGE=v["DUCK_BRIDGE"])

    def duck_plan(intervals):
        out, s = [], sorted(intervals)
        for i, (a, b) in enumerate(s):
            out.append((a - c["DUCK_LEAD"], c["DUCK_LEVEL"], c["DUCK_TC_DOWN"]))
            nxt = s[i + 1][0] if i + 1 < len(s) else None
            if nxt is None or nxt - b > c["DUCK_BRIDGE"]:
                out.append((b + c["DUCK_RELEASE"], 1.0, c["DUCK_TC_UP"]))
        return out, c
    P.duck_plan = duck_plan
    with tempfile.TemporaryDirectory() as td:
        mixed, stems, spans, elog, ts, lvl, dk = P.mix(Path(td), tl)
    freeze_env = np.ones(len(ts), dtype=np.float64)
    holds = []
    sched = tl["schedule"]
    for i, s in enumerate(sched):
        if s["kind"] != "scene" or s["hold"] <= 0:
            continue
        t0 = s["start"] + s["duration"]
        t1 = t0 + s["hold"]
        holds.append((s["id"], t0, t1))
        if v["freeze"] is None:
            continue
        f = v["freeze"]
        m = (ts >= t0) & (ts < t1)
        freeze_env[m] = f + (1 - f) * np.exp(-(ts[m] - t0) / FREEZE_TC)
        g_end = f + (1 - f) * np.exp(-(t1 - t0) / FREEZE_TC)
        m2 = (ts >= t1) & (ts < t1 + 3.0)
        freeze_env[m2] = 1 - (1 - g_end) * np.exp(-(ts[m2] - t1) / 0.35)
    stems["music"] = stems["music"] * freeze_env[:, None].astype(np.float32)
    lvl = lvl * freeze_env
    mixed = stems["vo"] + stems["music"] + stems["sfx"]
    bg = stems["music"] + stems["sfx"]
    lines = []
    for sp in spans:
        i0, i1 = int(sp["start"] * SR), int(sp["end"] * SR)
        vo_in = P.ebur(stems["vo"][i0:i1])["I_LUFS"]
        bgi = P.ebur(bg[i0:i1])["I_LUFS"]
        lines.append({"id": sp["id"], "start": round(sp["start"], 2), "end": round(sp["end"], 2), "vo_in_mix_I": vo_in,
                      "background_I": bgi, "vo_minus_background_LU": round(vo_in - bgi, 1) if vo_in and bgi else None,
                      "mix_I": P.ebur(mixed[i0:i1])["I_LUFS"]})
    # 必要旁白一（a2_c004_02）句間停頓：背景（配樂＋音效）每 100 ms 的 400 ms 瞬間響度，取停頓核心內的平均與最小
    mom_bg = P.momentary(bg)
    Tm = np.array([m[0] for m in mom_bg])
    Mm = np.array([m[1] for m in mom_bg])
    nar = next(sp for sp in spans if sp["id"] == "a2_c004_02")
    vo_path = ROOT / tl["audio"][nar["audioId"]]["source"]
    cores = V.pause_cores(V.read_wav(vo_path))
    pauses = []
    for a, b in cores:
        t0, t1 = nar["start"] + a / V.SR, nar["start"] + b / V.SR
        sel = (Tm >= t0 + 0.4) & (Tm <= t1)
        if sel.any():
            pauses.append({"from": round(t0, 2), "to": round(t1, 2), "bg_momentary_mean_LUFS": round(float(Mm[sel].mean()), 1),
                           "bg_momentary_min_LUFS": round(float(Mm[sel].min()), 1)})
    # 停格：進入停格第 3 秒的總混音瞬間響度（400 ms 窗結束在 t0+3.0 s）與 3 秒後到停格結束的最大值
    mom = P.momentary(mixed)
    T = np.array([m[0] for m in mom])
    M = np.array([m[1] for m in mom])
    fr = []
    for cid, t0, t1 in holds:
        k = int(np.argmin(np.abs(T - (t0 + 3.0))))
        sel = (T >= t0 + 3.0) & (T <= t1)
        fr.append({"cue": cid, "hold_from": round(t0, 2), "hold_to": round(t1, 2),
                   "momentary_at_3s_LUFS": round(float(M[k]), 1),
                   "momentary_max_after_3s_LUFS": round(float(M[sel].max()), 1) if sel.any() else None,
                   "pass_le_-35": bool(sel.any() and M[sel].max() <= -35.0)})
    per_cue = {}
    for s in sched:
        if s["duration"] >= 1.0:
            per_cue[s["id"]] = P.ebur(mixed[int(s["start"] * SR):int((s["start"] + s["duration"]) * SR)])["I_LUFS"]
    dlg = [s["id"] for s in sched if any(c["id"] == s["id"] and c["lines"] for c in tl["cues"])]
    vals = [v2 for v2 in per_cue.values() if v2 is not None]
    dvals = [per_cue[k] for k in dlg if per_cue.get(k) is not None]
    lm = [l["mix_I"] for l in lines if l["mix_I"] is not None]
    diffs = [l["vo_minus_background_LU"] for l in lines if l["vo_minus_background_LU"] is not None]
    return {"constants": {"DUCK_LEVEL": c["DUCK_LEVEL"], "DUCK_BRIDGE": c["DUCK_BRIDGE"], "FREEZE_LEVEL": v["freeze"],
                          "FREEZE_TC": FREEZE_TC if v["freeze"] is not None else None},
            "lines": lines, "vo_minus_background_LU_range": [min(diffs), max(diffs)],
            "lines_in_15_18": all(15 <= d <= 18 for d in diffs),
            "narration_pauses_background": pauses, "freeze": fr, "per_cue_I": per_cue,
            "segment_spread_lu_all_cues": round(max(vals) - min(vals), 1),
            "segment_spread_lu_dialogue_cues": round(max(dvals) - min(dvals), 1) if dvals else None,
            "dialogue_line_mix_spread_lu": round(max(lm) - min(lm), 1),
            "_mixed": mixed, "_stems": stems, "_lvl": lvl, "_ts": ts, "_spans": spans, "_T": T, "_M": M}


def main():
    tl0 = json.loads((ROOT / "review/G4/pack/timeline.json").read_text("utf-8"))
    tl = retime(tl0)
    res = {"_說明": __doc__.strip().splitlines()[0] + " 方法見 tools/vo_mixsim.py 檔頭。聽感未驗證。",
           "ducking_ts_current": DK0, "hold_scene_assumed_s": HOLD_SCENE,
           "retimed": {c["id"]: [(l["id"], l["start"], l["end"]) for l in c["lines"]] for c in tl["cues"] if c["lines"]},
           "audio_sources": {k: v["source"] for k, v in tl["audio"].items()}, "variants": {}}
    keep = {}
    for name, v in VARIANTS.items():
        r = run(tl, v)
        keep[name] = r
        res["variants"][name] = {k: val for k, val in r.items() if not k.startswith("_")}
        print(f"{name}: 對白−背景 {r['vo_minus_background_LU_range']}｜句間停頓背景 "
              f"{[p['bg_momentary_mean_LUFS'] for p in r['narration_pauses_background']]}｜停格第3秒 "
              f"{[f['momentary_at_3s_LUFS'] for f in r['freeze']]}｜各段差 {r['segment_spread_lu_all_cues']}（對白段 "
              f"{r['segment_spread_lu_dialogue_cues']}、對白句 {r['dialogue_line_mix_spread_lu']}）")
    rec = "0.56／0.9＋停格 0.10"
    res["recommended"] = rec
    rv = res["variants"][rec]
    res["recommendation"] = {
        "app/src/audio/ducking.ts": {"DUCK_LEVEL": 0.56, "DUCK_BRIDGE": 0.9},
        "music": "audio/music/music_m4_light_v02.wav（−24 LUFS，v01 為 −27；tools/pack.mjs 自動取最新版）。v01 時 a2_c004 背景太低，"
                 "同一個 DUCK_LEVEL 無法讓 a2_c002 與 a2_c004 都落在 15–18 LU。",
        "final_waiting": {"music_bus_target": "musicLevel × 0.10（約 −20 dB）", "time_constant_s": FREEZE_TC,
                          "rule": "場景 cue 進入 final_waiting 時對配樂匯流排 setTargetAtTime(musicLevel×0.10, t, 0.6)；老師按下一步、"
                                  "下一個 cue 的 musicLevel 照常以 0.35 s 回升。片尾署名卡（a8_c003）不套用：閉幕曲照設計自然收尾。"},
        "why": f"對白比背景高 {rv['vo_minus_background_LU_range'][0]}–{rv['vo_minus_background_LU_range'][1]} LU（目標 15–18）；"
               f"必要旁白句間停頓的背景約 {[p['bg_momentary_mean_LUFS'] for p in rv['narration_pauses_background']]} LUFS（目標約 −30，不掉到 −40）；"
               f"停格第 3 秒總混音 {[f['momentary_at_3s_LUFS'] for f in rv['freeze']]} LUFS（目標 ≤ −35）。"
               "DUCK_BRIDGE 不必改：必要旁白一是單一音檔，句間停頓本來就在同一段避讓裡，背景高低由 DUCK_LEVEL 決定；"
               "改成 2.0 只會讓 a2_c002 兩句之間（1.85 s）不回升，沒有改善。",
        "segment_spread_note": f"各段（cue）整合響度差 {rv['segment_spread_lu_all_cues']} LU：純配樂段（開幕、閉幕、署名卡）約 −19 到 −21 LUFS，"
                               f"以對白為主的 a2_c004 約 −15 LUFS；台詞時段（對白句）之間只差 {rv['dialogue_line_mix_spread_lu']} LU"
                               f"（含台詞的 cue 整段量是 {rv['segment_spread_lu_dialogue_cues']} LU，因為 a2_c002 有 13 秒純配樂）。要讓所有段落都在 ±1 LU 內，純配樂段必須提高到和對白幾乎一樣響，"
                               "對白時又要再壓 14 dB 以上（換句時配樂起伏很大），不建議。建議主線依修正清單第 12 項的但書，把「各段 ±1 LU」"
                               "定義為對白段（以及每個素材檔各自正規化：配音 −18±0.2 LUFS、配樂 −20／−24／−27 LUFS 分級），並寫進 REVIEW.md。",
    }
    (ROOT / "review/G3/mix_r1.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    r = keep[rec]
    P.plot_audio(ROOT / "review/G3/mix_r1.png", r["_mixed"], r["_stems"], r["_lvl"].astype(np.float32), r["_ts"], r["_T"], r["_M"],
                 tl, r["_spans"])
    print("ok →", "review/G3/mix_r1.json")


if __name__ == "__main__":
    main()
