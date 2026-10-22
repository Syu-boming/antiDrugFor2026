"""G6 全劇驗收包彙整（由 tools/show_review_pack.mjs 呼叫；也可單獨重跑：python tools/show_review_pack.py <輸出資料夾> <九段驗收包根目錄>）。

讀 show_review_pack.mjs 的原始量測（show_timeline.json、live/live_raw.json、seams/seams_raw.json、ops/*）與九段驗收包
（<根目錄>/<段>/pack 的 durations、audio/loudness、flash_playback／flash_variants、subtitle_sync、safety_data、timeline），寫：
  packs/show_table.json、packs/loudness_show.json      (a) 全劇表、段落響度差、全劇時長＋教師時間
  live/perf.json、live/frametime_plot.png、live/memory_plot.png   (b) 效能；live/network.json (d) 離線
  seams/seams.json、seams/seam_<前>_<後>.jpg、seams/seams_all.jpg、seams/<前>_<後>/flash_playback.json   (c) 接縫
  ops/ops.json                                          (e) 操作
  attribution/attribution.json、attribution/attribution.jpg     (f) 署名卡
  quiz/quiz.json                                        (g) 八題
  summary.json、INDEX.md（只列數字與檔案）
方法與門檻：v1.3 第 8 節、v1.2 第 24 節（第 5 項效能：第 95 百分位 ≤ 34 ms、超過 100 ms 的卡頓 ≤ 2 次且不在對白或揭答中；第 7 項各段響度差 ±1 LU；
第 12 項時長 ≤ 38 分；第 11 項署名卡）。光敏通過判定沿用 act_review_pack.py（主線裁定 1：16×9 與 fine_32x18 的明暗、紅色每秒都 ≤ 3）。
G6 修正第 1 輪：(a) 與建置一致改比段落 sha1（packs/segment_hashes.json，去掉 checkpoint 欄）；光敏另加孤立單格全畫面亮度比 ≤ 1.2（舊包從播放錄製補算）；
(b) 播放中／停格用逐格狀態判定（cueTime ≥ cue 長度＝停格），停格中預先建景的長格另列；卡頓依「是否在 fade 黑格內（全畫面亮度 < 0.05）」分類。
"""
import bisect
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
FPS = 30
FADE_BLACK = 0.05
LIMIT_MIN = 38.0
SIGNATURE = "許博明老師製作"
ANSWERS = [2, 3, 1, 1, 3, 2, 3, 2]


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _np(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o).__name__)


def dump(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=_np), encoding="utf-8")


def rel(p, base):
    try:
        return str(Path(p).resolve().relative_to(Path(base).resolve())).replace("\\", "/")
    except ValueError:
        return str(p)


def mean_linear_luma(path):
    """圖檔全畫面平均線性亮度（128×72 縮圖、sRGB→線性、Rec.709；同 act_review_pack.py 的孤立單格亮度比）"""
    from PIL import Image
    x = np.asarray(Image.open(path).convert("RGB").resize((128, 72), Image.BOX), dtype=np.float32) / 255
    x = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return float((0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]).mean())


def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


def mmss(sec):
    return f"{int(sec // 60)}:{sec % 60:04.1f}"


def font(n):
    import capture_analyze as ca
    return ca.font(n)


# ====================================================================== (a) 九段驗收包彙整
def _estimate_v03():
    txt = (ROOT / "script/時長估算_v03.md").read_text(encoding="utf-8")
    tot = float(re.search(r"\*\*預設情境合計\*\*\s*\|\s*\*\*([\d.]+)\*\*", txt).group(1))
    rec = None
    for raw in txt.splitlines():
        if raw.startswith("| **合計**") and "秒（" in raw:
            nums = re.findall(r"\*\*([\d.]+) 秒（", raw)
            if nums:
                rec = float(nums[-1])
    comp = re.findall(r"^\| (八題作答[^|]*|教師引導與練習[^|]*|故事段換 cue[^|]*) \| ([\d.]+) \|", txt, re.M)
    return tot, rec, [{"item": a.strip(), "sec": float(b)} for a, b in comp]


def teacher_time():
    """教師時間（不含預錄播放）。優先用講稿產生器的 teacher/data/timing.json（tools/teacher_docs.mjs）：
    教師＋按鍵＋換景＝totalSec − playback.level0（含換景漸暗預捲）；沒有就用 script/時長估算_v03.md 第 4.1 節：預設情境合計 − 預錄合計（不含預捲）。"""
    tot, rec, comp = _estimate_v03()
    est = {"default_scenario_sec": tot, "recorded_sec": rec, "teacher_sec": round(tot - rec, 1), "components": comp}
    tj = ROOT / "teacher/data/timing.json"
    d = load(tj)
    if d and isinstance(d.get("totalSec"), (int, float)) and isinstance((d.get("playback") or {}).get("level0"), (int, float)):
        speak = sum(c.get("teacherSec") or 0 for c in d.get("cues", []) if isinstance(c, dict))
        return {"teacher_sec": round(d["totalSec"] - d["playback"]["level0"], 1), "includes_preroll": True, "source": rel(tj, ROOT),
                "script_total_sec": d["totalSec"], "script_playback_level0_sec": d["playback"]["level0"], "script_teacher_speaking_sec": speak,
                "script_press_and_scene_sec": round(d["totalSec"] - d["playback"]["level0"] - speak, 1), "script_generated": d.get("generatedAt"), "script_cue_hash": d.get("cueHash"),
                "estimate_v03": est, "note": "教師時間＝講稿 totalSec − 預錄播放 level0（教師講述＋按鍵反應＋換景漸暗）"}
    return {"teacher_sec": est["teacher_sec"], "includes_preroll": False, "source": "script/時長估算_v03.md 第 4.1 節（teacher/data/timing.json 不存在）", "estimate_v03": est,
            "note": "教師時間＝預設情境合計 − 預錄合計（八題教師 8×47 秒＋換 cue、教師引導與練習 360 秒、故事段換 cue 45 秒）；不含換景預捲，預捲另加"}


def flash_pass(fl, fv, iso=None):
    def ok(mc):
        return None if not mc else (mc.get("luma", 99) <= 3 and mc.get("red", 99) <= 3)
    p169 = ok((fl or {}).get("max_changes_per_sec"))
    fine = ((fv or {}).get("variants") or {}).get("fine_32x18") or {}
    pf = ok(fine.get("max_changes_per_sec"))
    # G6 修正：孤立單格全畫面亮度比 ≤ 1.2（act_review_pack.py isolated_cuts.json；舊包由本工具從播放錄製補算）
    pi = None if not iso else bool(iso.get("pass"))
    return {"grid16x9": (fl or {}).get("max_changes_per_sec"), "fine32x18": fine.get("max_changes_per_sec"), "pass16x9": p169, "passFine": pf,
            "isolated_max_ratio": (iso or {}).get("max_ratio"), "isolated_over_limit": [{k: c.get(k) for k in ("cue", "cue_t", "t", "ratio")} for c in (iso or {}).get("over_limit", [])],
            "isolated_source": (iso or {}).get("_source"), "passIsolated": pi,
            "pass": None if p169 is None or pf is None or pi is None else bool(p169 and pf and pi), "near_limit_total": (fl or {}).get("near_limit_total"),
            "frames": (fl or {}).get("frames_analyzed")}


def isolated_for_pack(out, pk, tl):
    """驗收包的孤立單格亮度比：包裡有 isolated_cuts.json 就用；沒有（舊包）就從包的播放錄製補算，存在 <out>/packs/isolated/<段>.json（不寫進別人的包）"""
    iso = load(pk / "isolated_cuts.json")
    if iso:
        iso["_source"] = "驗收包 isolated_cuts.json"
        return iso
    if not tl:
        return None
    mp4 = pk / f"{tl['act']}_playback.mp4"
    if not mp4.exists():
        return None
    cache = out / "packs" / "isolated" / f"{tl['act']}.json"
    if cache.exists() and cache.stat().st_mtime >= mp4.stat().st_mtime:
        return load(cache)
    import act_review_pack as ap
    iso = ap.isolated_report(mp4, ap.schedule_where(tl))
    iso["_source"] = f"show_review_pack 從 {rel(mp4, ROOT)} 補算（舊包沒有 isolated_cuts.json）"
    dump(cache, iso)
    return iso


def packs_table(out, packs, show):
    cur = {c["id"]: c for c in show["cues"]}
    hashes = (load(out / "packs" / "segment_hashes.json") or {}).get("segments", {})
    rows = []
    wavs = []
    for seg in show["segments"]:
        a = seg["id"]
        pk = packs / a / "pack"
        du, lo, fl, fv = load(pk / "durations.json"), load(pk / "audio/loudness.json"), load(pk / "flash_playback.json"), load(pk / "flash_variants.json")
        ss, sa, tl, tr = load(pk / "subtitle_sync.json"), load(pk / "safety_data.json"), load(pk / "timeline.json"), load(pk / "transcripts.json")
        cur_dur = sum(cur[i]["duration"] for i in seg["cueIds"] if i in cur)
        cur_pre = sum(cur[i]["preroll"] for i in seg["cueIds"] if i in cur)
        row = {"act": a, "title": seg["title"], "pack": rel(pk, ROOT), "exists": pk.exists(), "cues": len(seg["cueIds"]),
               "current_build": {"cue_total_sec": round(cur_dur, 2), "preroll_sec": round(cur_pre, 2), "lines": sum(len(cur[i]["lines"]) for i in seg["cueIds"] if i in cur)}}
        if not pk.exists():
            rows.append(row)
            continue
        idx = pk / "INDEX.md"
        row["pack_generated"] = datetime.fromtimestamp(idx.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if idx.exists() else None
        # 與建置一致（G6 修正）：驗收包記下的段落指紋（app/dist 合併後這一段的 sha1，去掉 checkpoint 欄）＝目前 app/dist 的指紋；
        # 舊版工具產生的包沒有指紋 → 不判一致（None），cue 長度比對只留作參考
        h = hashes.get(a)
        row["segment_hash"] = h
        row["matches_current_build"] = (h or {}).get("builtMatch")
        row["matches_by"] = "段落 sha1" if row["matches_current_build"] is not None else "沒有指紋（舊版工具產生的包，要重產）"
        row["timeline_match_fallback"] = (h or {}).get("timelineMatch")
        if tl:
            diffs = [{"cue": c["id"], "pack": c["duration"], "build": cur[c["id"]]["duration"]} for c in tl["cues"] if c["id"] in cur and abs(c["duration"] - cur[c["id"]]["duration"]) > 0.01]
            missing = [i for i in seg["cueIds"] if i not in {c["id"] for c in tl["cues"]}]
            row["cue_lengths_match"] = not diffs and not missing
            row["duration_diffs_vs_build"] = diffs
            row["cues_missing_in_pack"] = missing
        if du:
            row["durations"] = {k: du.get(k) for k in ("act_total_sec", "act_preroll_total_sec", "act_budget_recorded_sec", "diff_vs_budget_sec", "estimate_sum_sec", "playback_with_holds_sec")}
        if lo:
            ms = lo.get("music_sfx_only") or {}
            lines = lo.get("lines", [])
            mix_i = [l["mix_I_LUFS"] for l in lines if l.get("mix_I_LUFS") is not None]
            row["loudness"] = {"I_LUFS": (lo.get("full_playback") or {}).get("I_LUFS"), "LRA_LU": (lo.get("full_playback") or {}).get("LRA_LU"), "TP_dBTP": (lo.get("full_playback") or {}).get("TP_dBTP"),
                               "sample_peak_dBFS": lo.get("sample_peak_dBFS"), "clipped_samples": lo.get("clipped_samples"),
                               "dialog_median_mix_I_LUFS": round(float(np.median(mix_i)), 1) if mix_i else None, "line_mix_I_spread_LU": lo.get("line_mix_I_spread_LU"),
                               "momentary_max_LUFS": lo.get("momentary_max_LUFS"), "music_sfx_only_max_LUFS": ms.get("max_LUFS"),
                               "freeze_holds_pass": f"{sum(1 for h in lo.get('freeze_holds', []) if h.get('pass_le_-35'))}/{len(lo.get('freeze_holds', []))}"}
            w = pk / "audio" / f"{a}_mix.wav"
            if w.exists():
                wavs.append(w)
        row["flash"] = flash_pass(fl, fv, isolated_for_pack(out, pk, tl))
        if ss:
            r_ = ss.get("rows", [])
            row["subtitle_sync"] = {"pages": len(r_), "pass": sum(1 for x in r_ if x["pass"]), "all_pass": ss.get("all_pass"),
                                    "max_s": max((x["diff_s"] for x in r_), default=None), "min_s": min((x["diff_s"] for x in r_), default=None)}
        if sa:
            row["safety"] = {"anchors": sa.get("string_anchors_in_cues"), "anchors_only_allowed": sa.get("string_anchors_only_allowed"),
                             "min_dist_to_head_px": sa.get("string_path_min_dist_to_head_box_px"), "string_through_child_frames": sa.get("string_path_intersects_child_box_count"),
                             "required_narration": {k: {"cue_eq_script": v.get("cue_equals_script"), "script_eq_claude_md": v.get("script_equals_claude_md"), "speaker": v.get("speaker")}
                                                    for k, v in (sa.get("required_narration") or {}).items()},
                             "lines_total": sa.get("lines_total"), "lines_differ_from_script": len(sa.get("lines_differ_from_script_v03", [])),
                             "subtitle_max_chars_per_row": sa.get("subtitle_max_chars_per_row"), "subtitle_max_rows_per_page": sa.get("subtitle_max_rows_per_page"),
                             "getUserMedia": sa.get("app_js_getUserMedia_count"), "mediaDevices": sa.get("app_js_mediaDevices_count"),
                             "capture_external_requests": sa.get("capture_external_requests"), "capture_console_errors": sa.get("capture_console_errors")}
        if tr:
            rws = tr.get("rows", [])
            row["transcripts"] = {m: {"vo_exact": sum(1 for r in rws if (r["vo"].get(m) or {}).get("cer") == 0), "mix_exact": sum(1 for r in rws if (r["mix"].get(m) or {}).get("cer") == 0)}
                                  for m in ("small", "large-v3-turbo")}
            row["transcripts"]["lines"] = len(rws)
        rows.append(row)
    # 段落響度差（v1.2 第 24 節第 7 項：各段響度差 ±1 LU）：以九段整合響度的中位數為基準
    Is = [r["loudness"]["I_LUFS"] for r in rows if r.get("loudness") and r["loudness"]["I_LUFS"] is not None]
    med = float(np.median(Is)) if Is else None
    for r in rows:
        if r.get("loudness") and med is not None and r["loudness"]["I_LUFS"] is not None:
            r["loudness"]["dev_from_median_LU"] = round(r["loudness"]["I_LUFS"] - med, 1)
    Ds = [r["loudness"]["dialog_median_mix_I_LUFS"] for r in rows if r.get("loudness") and r["loudness"].get("dialog_median_mix_I_LUFS") is not None]
    dmed = float(np.median(Ds)) if Ds else None
    for r in rows:
        if r.get("loudness") and dmed is not None and r["loudness"].get("dialog_median_mix_I_LUFS") is not None:
            r["loudness"]["dialog_dev_from_median_LU"] = round(r["loudness"]["dialog_median_mix_I_LUFS"] - dmed, 1)
    show_I = None
    if wavs:
        cmd = ["ffmpeg", "-nostats", "-hide_banner"]
        for w in wavs:
            cmd += ["-i", str(w)]
        cmd += ["-filter_complex", "".join(f"[{i}:a]" for i in range(len(wavs))) + f"concat=n={len(wavs)}:v=0:a=1,ebur128=peak=true", "-f", "null", "-"]
        txt = subprocess.run(cmd, capture_output=True, text=True).stderr
        summ = txt[txt.rfind("Summary:"):]
        m = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
        tp = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+)", summ)
        show_I = {"I_LUFS": float(m.group(1)) if m else None, "TP_dBTP": float(tp.group(1)) if tp else None, "files": [rel(w, ROOT) for w in wavs]}
    devs = [abs(r["loudness"]["dev_from_median_LU"]) for r in rows if r.get("loudness") and r["loudness"].get("dev_from_median_LU") is not None]
    ddevs = [abs(r["loudness"]["dialog_dev_from_median_LU"]) for r in rows if r.get("loudness") and r["loudness"].get("dialog_dev_from_median_LU") is not None]
    loud = {"rule": "v1.2 第 24 節第 7 項：各段響度差 ±1 LU。基準＝九段整合響度（act_review_pack 播放錄製混音，含教師停格假設）的中位數；另列各段對白（混音中各句）響度中位數的差。",
            "median_I_LUFS": round(med, 1) if med is not None else None, "max_abs_dev_LU": max(devs) if devs else None, "spread_LU": round(max(Is) - min(Is), 1) if Is else None,
            "pass_pm1": (max(devs) <= 1.0) if devs else None, "segments_over_1LU": [r["act"] for r in rows if r.get("loudness") and abs(r["loudness"].get("dev_from_median_LU") or 0) > 1.0],
            "dialog_median_LUFS": round(dmed, 1) if dmed is not None else None, "dialog_max_abs_dev_LU": max(ddevs) if ddevs else None, "dialog_pass_pm1": (max(ddevs) <= 1.0) if ddevs else None,
            "show_concat": show_I}
    tt = teacher_time()
    cue_sum = round(sum(c["duration"] for c in show["cues"]), 1)
    pre_sum = round(sum(c["preroll"] for c in show["cues"]), 1)
    play_cur = round(cue_sum + pre_sum, 1)
    play_pack = round(sum((r.get("durations") or {}).get("act_total_sec") or 0 for r in rows) + sum((r.get("durations") or {}).get("act_preroll_total_sec") or 0 for r in rows), 1)
    total = cue_sum + (0 if tt["includes_preroll"] else pre_sum) + tt["teacher_sec"]
    dur = {"cue_sum_current_build_sec": cue_sum, "preroll_sum_sec": pre_sum, "playback_current_build_sec": play_cur, "playback_current_build_min": round(play_cur / 60, 2), "playback_from_packs_sec": play_pack,
           "estimate_recorded_sec": tt["estimate_v03"]["recorded_sec"], "teacher": tt, "total_sec": round(total, 1), "total_min": round(total / 60, 2), "limit_min": LIMIT_MIN,
           "pass_le_38min": total / 60 <= LIMIT_MIN, "margin_sec": round(LIMIT_MIN * 60 - total, 1),
           "rule": "v1.3 第 8 節：以講稿估計的教師時間＋播放時間 ≤ 38 分；合計＝目前建置全部 cue 長度＋換景漸暗預捲＋教師時間（講稿：教師講述＋按鍵反應）"}
    res = {"segments": rows, "loudness": loud, "duration": dur,
           "packs_matching_build": sum(1 for r in rows if r.get("matches_current_build")), "packs_total": len(rows),
           "packs_matching_rule": "驗收包記下的段落指紋（app/dist 合併後這一段的 sha1，去掉 checkpoint 欄）＝目前 app/dist；packs/segment_hashes.json",
           "packs_without_hash": [r["act"] for r in rows if r.get("exists") and r.get("matches_current_build") is None],
           "packs_hash_mismatch": [r["act"] for r in rows if r.get("matches_current_build") is False],
           "packs_cue_lengths_match": sum(1 for r in rows if r.get("cue_lengths_match")),
           "packs_without_hash_timeline_match": [r["act"] for r in rows if r.get("exists") and r.get("matches_current_build") is None and r.get("timeline_match_fallback")],
           "dist_not_built_from_source": [a for a, h in hashes.items() if not (h.get("current") or {}).get("builtFromSource")],
           "flash_all_pass": all((r.get("flash") or {}).get("pass") for r in rows if r.get("exists")),
           "subtitle_sync_all_pass": all((r.get("subtitle_sync") or {}).get("all_pass") for r in rows if r.get("exists"))}
    dump(out / "packs" / "show_table.json", res)
    dump(out / "packs" / "loudness_show.json", loud)
    return res


# ====================================================================== (b) 即時播放效能
def perf(out, show):
    raw = load(out / "live" / "live_raw.json")
    if not raw:
        return None
    cues = {c["id"]: c for c in show["cues"]}
    clist = show["cues"]
    ts = np.array(raw["ts"], dtype=np.float64)
    S = sorted(raw["samples"], key=lambda x: x[0])
    st = [s[0] for s in S]
    presses = raw.get("presses", [])
    fsr = raw.get("fs") or []
    t_first = presses[0]["t"] if presses else (st[0] if st else 0)
    t_last = max(st) if st else ts[-1]
    if fsr:
        t_last = max(t_last, fsr[-1][0])

    def at(t):
        i = bisect.bisect_right(st, t) - 1
        if i < 0:
            return None
        s = S[i]
        ct = s[3] + ((t - s[0]) / 1000.0 if s[9] == "playing" and not s[5] else 0.0)
        return {"cue": s[1], "phase": s[2], "cueTime": round(ct, 2), "voSounding": s[4], "paused": bool(s[5]), "mode": s[9]}

    def in_line(cue, t):
        c = cues.get(cue)
        return next((l["id"] for l in (c or {}).get("lines", []) if l["start"] - 0.1 <= t <= l["end"] + 0.1), None)
    seg_of = {c["id"]: c["segment"] for c in clist}
    # 卡頓前後畫面的全畫面亮度（stall_frames.json：擷取模式重畫；在 fade 黑格內＝前後兩格全畫面平均線性亮度都 < 0.05）
    sf = load(out / "live" / "stall_frames.json") or {}
    sf_by_k = {x["k"]: x for x in sf.get("list", [])}

    def shot_luma(x):
        f = (x or {}).get("file")
        return mean_linear_luma(out / "live" / f) if f and (out / "live" / f).exists() else None
    if fsr:
        # G6 修正：逐格狀態（每一格開頭記下引擎上一格做完後的狀態）。第 k−1 格到第 k 格的間隔：卡住時畫面＝第 k−1 格的狀態、卡完＝第 k 格。
        # 停格＝停住等老師，或播放中 cueTime ≥ cue 長度（播完停在最後一格）；前後兩格都是停格的間隔＝畫面靜止（預先建下一個景），另列、不算播放中。
        F = np.array([r[:7] for r in fsr], dtype=np.float64)
        tsf = F[:, 0]
        iv_all = np.diff(tsf)
        k_all = np.arange(1, len(F))
        sel = (tsf[1:] >= t_first) & (tsf[1:] <= t_last)
        ks, ivs, tms = k_all[sel], iv_all[sel], tsf[1:][sel]
        durs = np.array([c["duration"] for c in clist])
        ci = F[:, 1].astype(int).clip(0, len(clist) - 1)
        hold_f = (F[:, 3] == 2) | ((F[:, 3] == 1) & (F[:, 2] >= durs[ci] - 1e-3))
        paused_f = F[:, 6] > 0
        hb, ha = hold_f[ks - 1], hold_f[ks]
        anyplay = (F[ks - 1, 3] == 1) | (F[ks, 3] == 1)
        pz = paused_f[ks - 1] | paused_f[ks]
        playing = anyplay & ~(hb & ha) & ~pz
        holding = hb & ha & ~pz

        def state(k):
            r = F[k]
            c = clist[int(ci[k])]
            return {"cue": c["id"], "cueTime": round(float(r[2]), 3), "mode": {1: "playing", 2: "waiting"}.get(int(r[3]), "other"), "hold": bool(hold_f[k]), "dim": round(float(r[4]), 3),
                    "preroll": bool(r[5] > 0 and r[2] <= 1e-6 and int(r[3]) == 1), "paused": bool(paused_f[k])}
        info = [state(int(k)) for k in ks]
        stalls, hold_stalls = [], []
        for j in np.flatnonzero(ivs > 100):
            k = int(ks[j])
            b, a = state(k - 1), state(k)
            cue = a["cue"]
            line = (in_line(b["cue"], b["cueTime"]) or in_line(a["cue"], a["cueTime"])) if playing[j] else None
            x = sf_by_k.get(k) or {}
            lb, la = shot_luma(x.get("before")), shot_luma(x.get("after"))
            rec = {"t_sec": round((tms[j] - t_first) / 1000, 2), "interval_ms": round(float(ivs[j]), 1), "cue": cue, "segment": seg_of.get(cue), "cueTime": a["cueTime"],
                   "before": b, "after": a, "mode": "playing" if playing[j] else ("hold" if holding[j] else ("paused" if pz[j] else "other")),
                   "in_dialog": bool(line), "line": line, "in_reveal": (cues.get(cue) or {}).get("kind") == "reveal" and bool(playing[j]),
                   "luma_before": None if lb is None else round(lb, 4), "luma_after": None if la is None else round(la, 4),
                   "in_fade_black": None if lb is None or la is None else bool(max(lb, la) < FADE_BLACK),
                   "during_set_fade_in": (cues.get(cue) or {}).get("enterFade", 0) > 0 and bool(playing[j]) and a["cueTime"] <= (cues.get(cue) or {}).get("enterFade", 0) + 0.1}
            (stalls if playing[j] else hold_stalls).append(rec)
        stalls_play = stalls
        hold_long = [{"t_sec": round((tms[j] - t_first) / 1000, 2), "interval_ms": round(float(ivs[j]), 1), "cue": info[j]["cue"], "cueTime": info[j]["cueTime"]}
                     for j in np.flatnonzero(holding & (ivs > 50))]
        frame_method = "逐格狀態（live_raw.json fs）：前後兩格都是停格（停住等老師，或 cueTime ≥ cue 長度）＝停格，其餘（含預捲漸暗）＝播放中；暫停中的格不算"
    else:
        # 舊資料（沒有逐格狀態）：每 200 ms 取樣推測；cueTime 推到 ≥ cue 長度的算停格
        iv = np.diff(ts)
        tmid = ts[1:]
        sel = (tmid >= t_first) & (tmid <= t_last)
        ivs, tms = iv[sel], tmid[sel]
        info = [at(t) for t in tms]
        hold_s = np.array([bool(x and (x["mode"] == "waiting" or x["cueTime"] >= ((cues.get(x["cue"]) or {}).get("duration", 1e9) - 1e-3))) for x in info])
        playing = np.array([bool(x and x["mode"] == "playing" and not x["paused"]) for x in info]) & ~hold_s
        holding = hold_s
        stalls, hold_stalls = [], []
        for k in np.flatnonzero(ivs > 100):
            x = info[k] or {}
            cue = x.get("cue")
            line = in_line(cue, x.get("cueTime", -1)) if playing[k] else None
            rec = {"t_sec": round((tms[k] - t_first) / 1000, 2), "interval_ms": round(float(ivs[k]), 1), "cue": cue, "segment": seg_of.get(cue), "phase": x.get("phase"),
                   "cueTime": x.get("cueTime"), "mode": "playing" if playing[k] else "hold", "in_dialog": bool(line) or (x.get("voSounding") or 0) > 0, "line": line,
                   "in_reveal": (cues.get(cue) or {}).get("kind") == "reveal" and bool(playing[k]), "luma_before": None, "luma_after": None, "in_fade_black": None,
                   "during_set_fade_in": (cues.get(cue) or {}).get("enterFade", 0) > 0 and bool(playing[k]) and (x.get("cueTime") or 99) <= (cues.get(cue) or {}).get("enterFade", 0) + 0.1}
            (stalls if playing[k] else hold_stalls).append(rec)
        stalls_play = stalls
        hold_long = [{"t_sec": round((tms[j] - t_first) / 1000, 2), "interval_ms": round(float(ivs[j]), 1), "cue": (info[j] or {}).get("cue"), "cueTime": (info[j] or {}).get("cueTime")}
                     for j in np.flatnonzero(holding & (ivs > 50))]
        frame_method = "舊資料：每 200 ms 取樣推測（沒有逐格狀態）；推到 cueTime ≥ cue 長度或停住等老師＝停格"
    per_seg = {}
    per_cue = {}
    for k in np.flatnonzero(playing):
        cue = info[k]["cue"]
        per_cue.setdefault(cue, []).append(ivs[k])
        per_seg.setdefault(seg_of.get(cue), []).append(ivs[k])
    seg_stats = {s: {"frames": len(v), "p50_ms": pct(v, 50), "p95_ms": pct(v, 95), "max_ms": round(float(max(v)), 1), "over_50ms": int(sum(1 for x in v if x > 50))} for s, v in per_seg.items()}
    cue_stats = sorted(({"cue": c, "frames": len(v), "p95_ms": pct(v, 95), "max_ms": round(float(max(v)), 1)} for c, v in per_cue.items()), key=lambda r: -r["p95_ms"])
    loaf = [{"t_sec": round((l[0] - t_first) / 1000, 2), "dur_ms": round(l[1], 1), "blocking_ms": round(l[2], 1), **({k: v for k, v in (at(l[0]) or {}).items() if k in ('cue', 'phase', 'mode')})}
            for l in raw.get("loaf", []) if l[0] >= t_first]
    # 記憶體
    mem = raw.get("memory", [])
    play_mem = [m for m in mem if m["label"] == "播放"]

    def slope(xs):
        if len(xs) < 3:
            return None
        t = np.array([m["t"] for m in xs]) / 60000.0
        y = np.array([m["jsHeapUsedMB"] for m in xs])
        return round(float(np.polyfit(t, y, 1)[0]), 2)

    def rss_total(m):
        return round(sum((m.get("processRssMB") or {}).values()), 1) if m.get("processRssMB") else None
    first10 = [m for m in play_mem if m["t"] - play_mem[0]["t"] <= 600000] if play_mem else []
    last10 = [m for m in play_mem if play_mem[-1]["t"] - m["t"] <= 600000] if play_mem else []
    memory = {"samples": len(mem), "title_idle": next((m for m in mem if m["label"] == "片頭待機"), None), "end": mem[-1] if mem else None,
              "js_heap_used_MB": {"min": min((m["jsHeapUsedMB"] for m in mem), default=None), "max": max((m["jsHeapUsedMB"] for m in mem), default=None),
                                  "first_play": play_mem[0]["jsHeapUsedMB"] if play_mem else None, "last_play": play_mem[-1]["jsHeapUsedMB"] if play_mem else None,
                                  "slope_MB_per_min_playing": slope(play_mem),
                                  "first10min_mean": round(float(np.mean([m["jsHeapUsedMB"] for m in first10])), 1) if first10 else None,
                                  "last10min_mean": round(float(np.mean([m["jsHeapUsedMB"] for m in last10])), 1) if last10 else None},
              "process_rss_total_MB": {"min": min((rss_total(m) for m in mem if rss_total(m)), default=None), "max": max((rss_total(m) for m in mem if rss_total(m)), default=None),
                                       "first_play": rss_total(play_mem[0]) if play_mem else None, "last_play": rss_total(play_mem[-1]) if play_mem else None},
              "process_rss_by_type_end_MB": (mem[-1].get("processRssMB") if mem else None), "dom_nodes_max": max((m.get("nodes") or 0 for m in mem), default=None),
              "loadavg1": {"mean": round(float(np.mean([m["loadavg1"] for m in mem])), 2) if mem else None, "max": round(float(max(m["loadavg1"] for m in mem)), 2) if mem else None},
              "note": (raw.get("cdpNote") or "") + " macOS 的 RSS 會因記憶體壓縮、清除快取而突然下降，只當走勢參考；學校 Windows 筆電請以工作管理員實測（未驗證）。"}
    # 字幕與語音時間差（voiceSync，每秒一次，說話時）
    vs = [abs(r["diffMs"]) for v in raw.get("voiceSync", []) for r in v["rows"]]
    vs_bad = [{"cue": v["cue"], "t": v["t"], "rows": v["rows"]} for v in raw.get("voiceSync", []) if any(abs(r["diffMs"]) > 50 for r in v["rows"])]
    # 字幕內容：播放中、某句台詞進行中（頭尾各留 0.15 秒）、題卡不在畫面上 → 字幕必須是這一句的一部分
    plain = lambda t: re.sub(r"\s+", "", t or "")
    sub_checked, sub_bad = 0, []
    for s in S:
        if s[0] < t_first or s[9] != "playing" or s[5] or s[7]:
            continue
        c = cues.get(s[1])
        l = next((l for l in (c or {}).get("lines", []) if l["start"] + 0.15 <= s[3] <= l["end"] - 0.15), None)
        if not l:
            continue
        sub_checked += 1
        if not s[6] or plain(s[6]) not in plain(l["text"]):
            sub_bad.append({"cue": s[1], "t": round(s[3], 2), "line": l["id"], "subtitle": s[6]})
    # 嘴型：每句（≥ 1.5 秒、說話者有紙偶）說話期間取樣到的嘴型種類
    faces = raw.get("faces", [])
    mouth_rows = []
    for c in show["cues"]:
        for l in c["lines"]:
            if l["end"] - l["start"] < 1.5 or not l["actorIds"]:
                continue
            fs = [f for f in faces if f[1] == c["id"] and l["start"] + 0.1 <= f[2] <= l["end"] - 0.1]
            if not fs:
                continue
            states = {a: sorted({(f[3].get(a) or {}).get("mouth") for f in fs if f[3].get(a)}) for a in l["actorIds"]}
            has_face = {a: any(f[3].get(a) for f in fs) for a in l["actorIds"]}
            mouth_rows.append({"line": l["id"], "samples": len(fs), "states": states, "has_face": has_face, "moved": any(len(v) >= 2 for v in states.values())})
    mouth_face = [r for r in mouth_rows if any(r["has_face"].values())]
    # 流程
    order = [c["id"] for c in show["cues"]][1:]
    visited = [v["id"] for v in raw.get("visits", [])]
    ivp = ivs[playing]
    res = {
        "environment": {**raw.get("system", {}), "note": "開發機實測（Apple M4、macOS、Chrome 無頭模式＋GPU〔ANGLE Metal〕、--mute-audio）；學校筆電：未驗證（探針結果回來後換算）。"},
        "load": raw.get("load"),
        "frames": {"all_after_start": int(len(ivs)), "playing": int(playing.sum()),
                   "p50_ms_playing": pct(ivp, 50), "p95_ms_playing": pct(ivp, 95), "p99_ms_playing": pct(ivp, 99), "max_ms_playing": round(float(ivp.max()), 1) if len(ivp) else None,
                   "p95_ms_all": pct(ivs, 95), "mean_fps_playing": round(1000.0 / float(np.mean(ivp)), 1) if len(ivp) else None,
                   "over_34ms_playing": int((ivp > 34).sum()), "over_50ms_playing": int((ivp > 50).sum()),
                   "engine_fps_median": round(float(np.median([s[8] for s in S if s[9] == "playing" and s[8]])), 1) if any(s[9] == "playing" and s[8] for s in S) else None},
        "frame_classification": frame_method,
        "stalls_over_100ms": stalls, "stalls_over_100ms_count": len(stalls) + len(hold_stalls), "stalls_over_100ms_playing_count": len(stalls_play),
        "stalls_in_dialog_or_reveal": sum(1 for s in stalls_play if s["in_dialog"] or s["in_reveal"]),
        "stalls_in_fade_black": sum(1 for s in stalls_play if s.get("in_fade_black")),
        "stalls_not_in_fade_black": sum(1 for s in stalls_play if s.get("in_fade_black") is False),
        "stalls_luma_unmeasured": sum(1 for s in stalls_play if s.get("in_fade_black") is None),
        "fade_black_rule": f"卡住時與卡完的畫面（擷取模式重畫）全畫面平均線性亮度都 < {FADE_BLACK}＝在 fade 黑格內（live/stall_frames.json）",
        "stalls_during_set_fade_in": sum(1 for s in stalls_play if s["during_set_fade_in"]),
        "hold_stalls_over_100ms": hold_stalls, "hold_stalls_over_100ms_count": len(hold_stalls),
        "hold_long_frames_over_50ms": {"count": len(hold_long), "max_ms": max((h["interval_ms"] for h in hold_long), default=None), "list": hold_long[:40],
                                       "note": "停格中（前後兩格都是停格：畫面靜止）預先建下一個景的長格；不算播放中卡頓"},
        "criteria_v12_24_5": {"p95_le_34ms": (pct(ivp, 95) or 99) <= 34, "stalls_le_2": len(stalls_play) <= 2,
                              "no_stall_in_dialog_or_reveal": not any(s["in_dialog"] or s["in_reveal"] for s in stalls_play),
                              "heat_test_30min_idle_40min_show": "未驗證（本次只跑一次完整演出，沒有待機 30 分鐘）"},
        "per_segment": seg_stats, "worst_cues_p95": cue_stats[:12], "long_animation_frames": {"count": len(loaf), "over_100ms": sum(1 for l in loaf if l["dur_ms"] > 100), "top": sorted(loaf, key=lambda l: -l["dur_ms"])[:15]},
        "memory": memory,
        "voice_sync": {"samples": len(vs), "max_abs_ms": max(vs) if vs else None, "p95_abs_ms": pct(vs, 95), "over_50ms": len(vs_bad), "over_50ms_where": vs_bad[:20]},
        "subtitles": {"checked_samples": sub_checked, "mismatch": len(sub_bad), "mismatch_where": sub_bad[:20]},
        "mouth": {"lines_checked": len(mouth_face), "lines_moved": sum(1 for r in mouth_face if r["moved"]), "not_moved": [r for r in mouth_face if not r["moved"]][:20],
                  "lines_without_face_data": len(mouth_rows) - len(mouth_face)},
        "flow": {"visited": len(visited), "expected": len(order), "all_visited_in_order": visited == order, "missing": [c for c in order if c not in visited][:20],
                 "end": raw.get("end"), "wall_min": round((raw.get("end") or {}).get("wall_ms", 0) / 60000, 2), "presses": len(presses)},
        "page_errors": raw.get("errors", []),
    }
    dump(out / "live" / "perf.json", res)
    plot_perf(out, ts, t_first, t_last, raw, show, mem)
    return res


def plot_perf(out, ts, t_first, t_last, raw, show, mem):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for fp in ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc"):
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
            break
    iv = np.diff(ts)
    tm = (ts[1:] - t_first) / 60000.0
    sel = (ts[1:] >= t_first) & (ts[1:] <= t_last)
    fig, ax = plt.subplots(1, 1, figsize=(18, 5))
    ax.plot(tm[sel], np.minimum(iv[sel], 200), lw=0.4, color="#3b6ea8")
    for y, c, lab in ((34, "#c0392b", "34 ms"), (100, "#7f1d1d", "100 ms")):
        ax.axhline(y, color=c, lw=0.8, ls="--")
        ax.text(0.2, y + 2, lab, color=c, fontsize=9)
    seg_first = {}
    for v in raw.get("visits", []):
        seg = next((c["segment"] for c in show["cues"] if c["id"] == v["id"]), None)
        if seg not in seg_first:
            seg_first[seg] = (v["at"] - t_first) / 60000.0
    for s, x in seg_first.items():
        ax.axvline(x, color="#999", lw=0.6)
        ax.text(x + 0.05, 190, s, fontsize=9)
    ax.set_ylim(0, 205)
    ax.set_xlabel("開演後（分鐘）")
    ax.set_ylabel("影格時間 ms（>200 畫在 200）")
    ax.set_title("即時播放影格時間（requestAnimationFrame 間隔）")
    fig.tight_layout()
    fig.savefig(out / "live" / "frametime_plot.png", dpi=80)
    plt.close(fig)
    if mem:
        fig, ax = plt.subplots(1, 1, figsize=(18, 4.5))
        t = [m["t"] / 60000.0 for m in mem]
        ax.plot(t, [m["jsHeapUsedMB"] for m in mem], label="JS heap used（MB）", color="#3b6ea8")
        rs = [sum((m.get("processRssMB") or {}).values()) or None for m in mem]
        ax.plot(t, rs, label="Chrome 各程序 RSS 合計（MB）", color="#a8643b")
        for typ, col in (("renderer", "#5a8a4a"), ("GPU", "#7a4a8a")):
            ys = [(m.get("processRssMB") or {}).get(typ) for m in mem]
            if any(ys):
                ax.plot(t, ys, label=f"{typ} RSS（MB）", color=col, lw=0.8)
        ax.set_xlabel("開頁後（分鐘）")
        ax.legend(loc="upper left", fontsize=9)
        ax.set_title("記憶體走勢")
        fig.tight_layout()
        fig.savefig(out / "live" / "memory_plot.png", dpi=80)
        plt.close(fig)


# ====================================================================== (c) 段落接縫
def seams(out):
    from PIL import Image, ImageDraw
    import capture_analyze as ca
    import g4_review_pack as g4
    raw = load(out / "seams" / "seams_raw.json")
    if not raw:
        return None
    prev = load(out / "seams" / "seams.json")
    if not all(Path(s["prevLast"]).exists() for s in raw["seams"]):
        # 擷取格做完就刪（--skip-seams 時沿用上次的分析結果）
        if prev and all("error" not in r for r in prev.get("seams", [])):
            return prev
        return {"seams": [{"seam": f"{s['from']}_{s['to']}", "error": "擷取格已刪除，請拿掉 --skip-seams 重跑"} for s in raw["seams"]], "all_flash_pass": None, "hard_cuts": [],
                "max_abs_first_shown_delta": None, "external_requests": len(raw.get("externalRequests", [])), "page_errors": raw.get("errors", [])}
    rows, tiles = [], []
    tw, th = 640, 360
    for s in raw["seams"]:
        name = f"{s['from']}_{s['to']}"
        d = out / "seams" / name
        d.mkdir(parents=True, exist_ok=True)
        if not Path(s["prevLast"]).exists():
            rows.append({"seam": name, "error": "擷取格已刪除（請拿掉 --skip-seams 重跑）"})
            continue
        st = {k: ca.frame_stats(s[k]) for k in ("prevLast", "nextFirstShown", "nextFirstLit")}
        L = {k: round(v[2], 4) for k, v in st.items()}
        dshown = float(np.abs(st["nextFirstShown"][0] - st["prevLast"][0]).max())
        dlit = float(np.abs(st["nextFirstLit"][0] - st["prevLast"][0]).max())
        seq = [(t, Path(p), cue, ct) for t, p, cue, ct in s["seq"]]
        fl = g4.flash_playback(d, seq)
        fv = g4.flash_variants(d, seq)
        fine = fv["variants"]["fine_32x18"]["max_changes_per_sec"]
        row = {"seam": name, "from": s["from"], "to": s["to"], "prevCue": s["prevCue"], "nextCue": s["nextCue"], "setFrom": s["setFrom"], "setTo": s["setTo"],
               "preroll_sec": s["preroll"], "enterFade_sec": s["enterFade"],
               "mean_luma": L, "first_shown_minus_last": round(L["nextFirstShown"] - L["prevLast"], 4), "first_lit_minus_last": round(L["nextFirstLit"] - L["prevLast"], 4),
               "max_region_luma_delta_first_shown": round(dshown, 4), "max_region_luma_delta_first_lit": round(dlit, 4),
               "hard_cut": dshown > 0.1 and s["preroll"] == 0,
               "flash": {"grid16x9": fl["max_changes_per_sec"], "fine32x18": fine, "pass": fl["max_changes_per_sec"]["luma"] <= 3 and fl["max_changes_per_sec"]["red"] <= 3 and fine["luma"] <= 3 and fine["red"] <= 3,
                         "frames": fl["frames_analyzed"], "file": rel(d / "flash_playback.json", out)},
               "image": f"seams/seam_{name}.jpg"}
        rows.append(row)
        sheet = Image.new("RGB", (3 * tw + 40, th + 92), (24, 22, 20))
        dr = ImageDraw.Draw(sheet)
        dr.text((10, 8), f"{s['from']}→{s['to']}｜{s['prevCue']}（{s['setFrom']}）→ {s['nextCue']}（{s['setTo']}）｜預捲 {s['preroll']} 秒、漸亮 {s['enterFade']} 秒", font=font(18), fill=(240, 236, 228))
        labels = (("prevLast", "前段最後一格"), ("nextFirstShown", "後段第一格（按下一步後）"), ("nextFirstLit", "後段第一個全亮格"))
        for i, (k, lab) in enumerate(labels):
            x = 10 + i * (tw + 10)
            sheet.paste(Image.open(s[k]).convert("RGB").resize((tw, th), Image.LANCZOS), (x, 36))
            extra = "" if k == "prevLast" else f"；Δ平均 {L[k] - L['prevLast']:+.3f}、區域最大 Δ {(dshown if k == 'nextFirstShown' else dlit):.3f}"
            dr.text((x, 36 + th + 8), f"{lab}：平均亮度 {L[k]:.3f}{extra}", font=font(15), fill=(220, 214, 204))
        dr.text((10, 36 + th + 32), f"接縫 30 格／秒光敏（{fl['frames_analyzed']} 格）：16×9 明暗 {fl['max_changes_per_sec']['luma']}、紅 {fl['max_changes_per_sec']['red']}；32×18 明暗 {fine['luma']}、紅 {fine['red']}（每秒）",
                font=font(15), fill=(220, 214, 204))
        p = out / "seams" / f"seam_{name}.jpg"
        sheet.save(p, quality=90)
        tiles.append(p)
    if tiles:
        ims = [Image.open(p) for p in tiles]
        w, h = ims[0].size
        scale = 0.5
        allim = Image.new("RGB", (int(w * scale), int(h * scale) * len(ims)), (24, 22, 20))
        for i, im in enumerate(ims):
            allim.paste(im.resize((int(w * scale), int(h * scale)), Image.LANCZOS), (0, i * int(h * scale)))
        allim.save(out / "seams" / "seams_all.jpg", quality=88)
    res = {"method": "擷取模式（?capture=1，固定步長 30 格／秒）：前段最後一個 cue 的最後 1 秒＋停住 1 秒 → 後段第一個 cue 的換景漸暗預捲＋前 3 秒；平均亮度＝線性亮度（capture_analyze.frame_stats），區域＝16×9；"
                     "光敏用 g4_review_pack.flash_playback／flash_variants（同各段驗收包）。後段第一格＝老師按下一步後畫出的第一格（有預捲時是漸暗的第一格）。",
           "seams": rows, "all_flash_pass": all(r.get("flash", {}).get("pass") for r in rows), "hard_cuts": [r["seam"] for r in rows if r.get("hard_cut")],
           "max_abs_first_shown_delta": max((abs(r["first_shown_minus_last"]) for r in rows if "first_shown_minus_last" in r), default=None),
           "external_requests": len(raw.get("externalRequests", [])), "page_errors": raw.get("errors", [])}
    dump(out / "seams" / "seams.json", res)
    return res


# ====================================================================== (e) 操作
OPS_MAP = [("連按", r"連按"), ("長按", r"長按|key repeat"), ("上一步", r"上一步"), ("暫停／繼續", r"暫停|句點鍵|空白鍵"), ("重播（R）", r"重播|按 R"),
           ("頁面隱藏後恢復", r"頁面隱藏|頁面恢復|失焦"), ("休眠／系統停音訊／凍結", r"AudioContext|系統|休眠|凍結|畫面更新中斷"), ("GPU 中斷重建", r"GPU 中斷|重建"),
           ("字幕與語音時間差／嘴型", r"時間差|嘴型|對嘴")]


def ops(out):
    logf = out / "ops" / "engine_test.log"
    et = []
    summary = None
    if logf.exists():
        for line in logf.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(  通過|✗ 失敗)  (.+?)(?:  （(.*)）)?$", line)
            if m:
                et.append({"ok": m.group(1).strip() == "通過", "name": m.group(2), "detail": m.group(3) or ""})
            m2 = re.search(r"\[engine-test\] (\d+)／(\d+) 項通過", line)
            if m2:
                summary = {"passed": int(m2.group(1)), "total": int(m2.group(2))}
    sh = load(out / "ops" / "ops_show.json") or {}
    shr = sh.get("results", [])
    cats = []
    for cat, rx in OPS_MAP:
        a = [r for r in et if re.search(rx, r["name"])]
        b = [r for r in shr if re.search(rx, r["name"])]
        cats.append({"category": cat, "engine_test": {"checks": len(a), "passed": sum(r["ok"] for r in a), "names": [r["name"] for r in a]},
                     "show_supplement": {"checks": len(b), "passed": sum(r["ok"] for r in b), "names": [r["name"] for r in b]}})
    res = {"engine_test": {"log": rel(logf, out) if logf.exists() else None, "summary": summary, "checks": len(et), "passed": sum(r["ok"] for r in et), "failed": [r for r in et if not r["ok"]]},
           "show_supplement": {"file": "ops/ops_show.json", "checks": len(shr), "passed": sum(r["ok"] for r in shr), "failed": [r for r in shr if not r["ok"]], "results": shr},
           "categories": cats,
           "note": "engine-test 的操作測試多在示範／G4 cue 集（第一、七段）；全劇補測在 ?cues=show、正式配音、即時 AudioContext 時鐘下重做連按、長按、題卡、上一步、暫停、重播、頁面隱藏、分頁凍結、休眠偵測。實機休眠（闔上筆電）：未驗證。"}
    dump(out / "ops" / "ops.json", res)
    return res


# ====================================================================== (f) 署名卡、(g) 八題
def attribution(out):
    from PIL import Image, ImageDraw
    raw = load(out / "live" / "live_raw.json")
    if not raw:
        return None
    a = raw.get("attribution", {})
    rows = {}
    for k in ("start", "end"):
        x = a.get(k) or {}
        rows[k] = {**x, "text_ok": x.get("text") == SIGNATURE, "visible": x.get("hidden") is False and float(x.get("opacity") or 0) > 0.99}
    ims = [out / "attribution" / f"title_{k}.png" for k in ("start", "end")]
    if all(p.exists() for p in ims):
        tw, th = 800, 450
        sheet = Image.new("RGB", (2 * tw + 30, th + 70), (24, 22, 20))
        dr = ImageDraw.Draw(sheet)
        for i, (p, lab) in enumerate(zip(ims, ("片頭（按「準備播放」後，片頭待機）", "片尾（a8_c003 結束後）"))):
            sheet.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (10 + i * (tw + 10), 40))
            x = rows["start" if i == 0 else "end"]
            dr.text((10 + i * (tw + 10), 8), f"{lab}｜DOM 文字「{x.get('text')}」", font=font(18), fill=(240, 236, 228))
        sheet.save(out / "attribution" / "attribution.jpg", quality=90)
    res = {"expected": SIGNATURE, "start": rows["start"], "end": rows["end"], "pass": rows["start"]["text_ok"] and rows["end"]["text_ok"] and rows["start"]["visible"] and rows["end"]["visible"],
           "files": ["attribution/title_start.png", "attribution/title_end.png", "attribution/attribution.jpg"],
           "method": "即時播放時讀 #title-card .sig-text 的 DOM 文字、#title-card 是否顯示（hidden／opacity）並全頁截圖；署名卡由程式排字（engine-test 第四段另驗）。"}
    dump(out / "attribution" / "attribution.json", res)
    return res


def quiz(out, show):
    raw = load(out / "live" / "live_raw.json")
    if not raw:
        return None
    q8 = (ROOT / "script/八題_v03.md").read_text(encoding="utf-8")

    def doc(qid):
        blk = next((b for b in q8.split("\n### ") if b.startswith(f"{qid}｜")), "")
        stem = re.search(r"- 題幹：(.+)", blk)
        opts = [re.search(rf"^- {k}　(.+?)\s*(\*\*〔正解〕\*\*)?\s*$", blk, re.M) for k in (1, 2, 3)]
        correct = next((i + 1 for i, m in enumerate(opts) if m and m.group(2)), None)
        return {"question": stem.group(1).strip() if stem else None, "options": [m.group(1).strip() if m else None for m in opts], "correct": correct}
    rows = []
    for q in raw.get("quiz", []):
        d = doc(q["qid"])
        shown = q.get("shown") or {}
        dom_opts = [re.sub(r"^\s*[123]\s*", "", (o.get("text") or "")).strip() for o in shown.get("options", [])]
        rv = q.get("revealed") or {}
        stamp = [c for c in rv.get("correct", [])]
        n = q.get("number")
        ok_text = shown.get("question") == d["question"] and all((d["options"][i] or "") in (dom_opts[i] if i < len(dom_opts) else "") for i in range(3))
        row = {"qid": q["qid"], "number": n, "cue": q["cue"], "answer_expected": ANSWERS[n - 1] if n else None, "answer_cue_data": q.get("answerData"), "answer_doc": d["correct"],
               "question_dom": shown.get("question"), "question_doc": d["question"], "options_dom": dom_opts, "options_doc": d["options"], "text_matches_doc": ok_text,
               "no_auto_reveal_after_sec": q.get("waitedSec") if q.get("noAutoReveal") else None, "no_auto_reveal": bool(q.get("noAutoReveal")),
               "reveal_phase_after_press": q.get("revealPhase"), "stamp_classes": stamp,
               "stamp_on_answer": len(stamp) == 1 and f"opt-{ANSWERS[n - 1]}" in stamp[0].split() if n else False,
               "lamp_lit_after": (q.get("lamp") or {}).get("lampsLit"), "lamp_ok": n in ((q.get("lamp") or {}).get("lampsLit") or []) and n not in (rv.get("lampsLit") or []),
               "continued_to": q.get("next"), "continued_ok": bool(q.get("next")) and (q["next"].get("kind") in ("scene", "curtain"))}
        row["pass"] = bool(row["answer_expected"] == row["answer_cue_data"] == row["answer_doc"] and ok_text and row["no_auto_reveal"] and row["reveal_phase_after_press"] == "reveal_playing"
                           and row["stamp_on_answer"] and row["lamp_ok"] and row["continued_ok"])
        rows.append(row)
    res = {"expected_answers": ANSWERS, "observed_answers_stamp": [next((int(c.split("opt-")[1][0]) for c in r["stamp_classes"] if "opt-" in c), None) for r in rows],
           "quizzes": len(rows), "passed": sum(1 for r in rows if r["pass"]), "rows": rows, "end_lamps": (raw.get("end") or {}).get("lampsLit"),
           "method": "即時播放（實體 PageDown）：出題畫面停住 → 讀 DOM 題卡（題幹、選項、有無印章）→ 等 --quiz-wait 秒確認沒有自動揭答 → 按下一步 → 揭答播完讀印章位置 → 點燈後讀 lampsLit → 按下一步確認續演；題卡文字與 script/八題_v03.md 比對（同 engine-test 的解析）。"}
    dump(out / "quiz" / "quiz.json", res)
    return res


def network(out):
    n = load(out / "live" / "network.json") or {}
    s = load(out / "seams" / "seams_raw.json") or {}
    o = load(out / "ops" / "ops_show.json") or {}
    ext = len(n.get("external", [])) + len(s.get("externalRequests", [])) + len(o.get("externalRequests", []))
    return {"live_requests": n.get("requests"), "live_external": len(n.get("external", [])), "live_failed": len(n.get("failed", [])), "live_failed_list": n.get("failed", [])[:20],
            "seams_requests": s.get("requests"), "seams_external": len(s.get("externalRequests", [])), "ops_requests": o.get("requests"), "ops_external": len(o.get("externalRequests", [])),
            "external_total": ext, "pass_zero_external": ext == 0, "byType": n.get("byType"),
            "method": "Playwright 記錄頁面的每個請求（file:、data:、blob: 以外都算外部）；本機 file:// 開啟，沒有啟動伺服器。斷網啟動（學校實機）：未驗證。"}


# ====================================================================== INDEX.md
def fmt(x, nd=1):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "是" if x else "否"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


# ====================================================================== 建置指紋（G7 修正第 1 輪，技術 QA G2）
SECTION_NAME = {"live": "即時播放（live/live_raw.json）", "seams": "段落接縫（seams/seams_raw.json）", "ops": "全劇操作補測（ops/ops_show.json）", "engine_test": "engine-test（ops/engine_test.log）"}


def _when(iso):
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso


def build_notes(BC, keys):
    """該節開頭的建置說明：本次量測／沿用同一建置／沿用舊建置的數據（列出兩邊 sha1）。BC＝build_check.json"""
    if not BC:
        return ["- 建置：沒有 build_check.json（舊版工具），無法確認這一節的數據是不是用目前建置量的。"]
    cur = BC.get("current") or {}
    ca, cc, cf = cur.get("appJsSha1"), cur.get("cuesShowSha1"), cur.get("cuesShowFile") or "cues_show.js"
    out = []
    for k in keys:
        r = (BC.get("sections") or {}).get(k)
        if not r or r.get("status") == "missing":
            continue
        name = SECTION_NAME.get(k, k)
        rec = r.get("recorded") or {}
        st = r.get("status")
        if st == "fresh":
            out.append(f"- 建置：{name}本次以目前建置量測（app.js `{ca}`、{cf} `{cc}`）。")
        elif st == "reused_same_build":
            out.append(f"- 建置：{name}沿用 {_when(rec.get('measuredAt') or r.get('dataMtime'))} 的數據（{r.get('option')}），記錄的建置與目前 app/dist 相同（app.js `{ca}`、{cf} `{cc}`）。")
        elif st == "reused_other_build":
            if rec.get("appJsSha1"):
                diff = "、".join(x for x, ok in (("app.js", r.get("appJsMatch")), (cf, r.get("cuesShowMatch"))) if not ok)
                out.append(f"- **沿用舊建置的數據**：{name}是 {_when(rec.get('measuredAt') or r.get('dataMtime'))} 量的（{r.get('option')}），"
                           f"當時建置 app.js `{rec.get('appJsSha1')}`、{rec.get('cuesShowFile') or cf} `{rec.get('cuesShowSha1')}`；"
                           f"目前 app/dist app.js `{ca}`、{cf} `{cc}`（{diff} 不同）。這一節的數字不是用目前建置量的；要用目前建置請{r.get('rerun') or '重跑'}（約 {r.get('rerunMin')} 分鐘）。")
            else:
                cited = f"引用 {rec.get('cited')}、" if rec.get("cited") else ""
                out.append(f"- **沿用舊建置的數據**：{name}（{cited}資料時間 {_when(r.get('comparedTime') or r.get('dataMtime'))}）早於目前建置 app.js（{_when(cur.get('appJsMtime'))}），"
                           f"而且舊資料沒有記錄建置 sha1（當時建置：未記錄）；目前 app/dist app.js `{ca}`、{cf} `{cc}`。這一節的數字不是用目前建置量的；要用目前建置請{r.get('rerun') or '重跑'}（約 {r.get('rerunMin')} 分鐘）。")
        else:
            cited = f"引用 {rec.get('cited')}、" if rec.get("cited") else ""
            out.append(f"- 建置：{name}沿用舊資料（{cited}資料時間 {_when(r.get('comparedTime') or r.get('dataMtime'))}，晚於目前 app.js），但沒有記錄建置 sha1，無法確認是同一建置；目前 app/dist app.js `{ca}`、{cf} `{cc}`。")
    return out


def index(out, packs, show, A, P, C, E, F, G, N):
    BC = load(out / "build_check.json")
    cur = (BC or {}).get("current") or {}
    stale = [SECTION_NAME.get(k, k) for k, r in ((BC or {}).get("sections") or {}).items() if r.get("status") == "reused_other_build"]
    L = [f"# G6 全劇驗收包", "",
         f"- 產生：tools/show_review_pack.mjs（{datetime.now().strftime('%Y-%m-%d %H:%M')}）；建置 `app/dist`（{len(show['cues'])} 個 cue、{len(show['segments'])} 段）；九段驗收包 `{rel(packs, ROOT)}/<段>/pack`。本檔只列數字與檔案。",
         f"- 建置指紋（build_check.json）：app.js `{cur.get('appJsSha1', '—')}`、{cur.get('cuesShowFile') or 'cues_show.js'} `{cur.get('cuesShowSha1', '—')}`（資料包 builtAt {cur.get('distBuiltAt', '—')}）。"
         + (f"**沿用舊建置的數據：{'、'.join(stale)}**（見各節開頭）。" if stale else "各節數據都是目前建置（或沿用、但 sha1 相同）。" if BC else "沒有 build_check.json（舊版工具）。"),
         "- 未驗證：學校筆電效能（待探針換算）、實際投影、聽感、實機休眠與斷網、待機 30 分鐘＋演出 40 分鐘耐熱測試。", ""]
    L += ["## 檔案", "", "| 項目 | 檔案 |", "|---|---|",
          "| 目前建置時間軸 | show_timeline.json |",
          "| 建置指紋（各節數據量測時的 app.js、cues_show.js sha1） | build_check.json、live/build.json、seams/build.json、ops/build.json、ops/engine_test.build.json |",
          "| (a) 九段彙整、響度、時長 | packs/show_table.json、packs/loudness_show.json、packs/segment_hashes.json（段落指紋）、packs/isolated/（舊包補算的孤立單格亮度比） |",
          "| (b) 即時播放效能 | live/perf.json、live/frametime_plot.png、live/memory_plot.png、live/live_raw.json、live/stall_frames.json、live/stall_frames/ |",
          "| (c) 段落接縫 | seams/seams.json、seams/seams_all.jpg、seams/seam_<前>_<後>.jpg、seams/<前>_<後>/flash_playback.json |",
          "| (d) 離線 | live/network.json |",
          "| (e) 操作 | ops/ops.json、ops/ops_show.json、ops/engine_test.log |",
          "| (f) 署名卡 | attribution/attribution.json、attribution/attribution.jpg、attribution/title_start.png、attribution/title_end.png |",
          "| (g) 八題 | quiz/quiz.json |",
          "| (h) 交付包 | delivery/delivery_smoke.json、delivery/delivery_smoke.md（tools/delivery_smoke.mjs 產生；沒有跑就不列） |",
          "| 摘要（機器可讀） | summary.json |", ""]
    if A:
        d = A["duration"]
        lo = A["loudness"]
        L += ["## (a) 九段驗收包彙整", "",
              f"- 驗收包與目前建置一致（段落 sha1，去掉 checkpoint 欄；packs/segment_hashes.json）：{A['packs_matching_build']}／{A['packs_total']} 段"
              f"；指紋不同：{'、'.join(A.get('packs_hash_mismatch') or []) or '無'}；舊包沒有指紋（要重產）：{'、'.join(A.get('packs_without_hash') or []) or '無'}"
              f"；app/dist 不是用目前段落檔建的：{'、'.join(A.get('dist_not_built_from_source') or []) or '無'}。"
              f"（參考：沒有指紋的包裡，解析後時間軸〔timeline.json cues，不含 initialState 站位與鏡位〕與目前建置相同：{'、'.join(A.get('packs_without_hash_timeline_match') or []) or '無'}；cue 長度一致 {A.get('packs_cue_lengths_match', '—')}／{A['packs_total']} 段）",
              f"- 光敏（16×9 與 fine_32x18 的明暗、紅色每秒 ≤ 3；孤立單格全畫面亮度比 ≤ 1.2）全部通過：{fmt(A['flash_all_pass'])}；字幕時間差全部在範圍內：{fmt(A['subtitle_sync_all_pass'])}。",
              f"- 段落響度：中位數 {fmt(lo['median_I_LUFS'])} LUFS、最大偏差 {fmt(lo['max_abs_dev_LU'])} LU、最大−最小 {fmt(lo['spread_LU'])} LU；±1 LU：{fmt(lo['pass_pm1'])}（超過：{'、'.join(lo['segments_over_1LU']) or '無'}）。"
              f"對白響度中位數 {fmt(lo['dialog_median_LUFS'])} LUFS、最大偏差 {fmt(lo['dialog_max_abs_dev_LU'])} LU。九段接起來 {fmt((lo.get('show_concat') or {}).get('I_LUFS'))} LUFS、真峰值 {fmt((lo.get('show_concat') or {}).get('TP_dBTP'))} dBTP。",
              f"- 時長：目前建置 cue 長度合計 {fmt(d['cue_sum_current_build_sec'])} 秒＋換景預捲 {fmt(d['preroll_sum_sec'])} 秒＝播放 {fmt(d['playback_current_build_sec'])} 秒（{mmss(d['playback_current_build_sec'])}）；驗收包合計 {fmt(d['playback_from_packs_sec'])} 秒；時長估算 v03 預錄 {fmt(d['estimate_recorded_sec'])} 秒。"
              f"教師時間 {fmt(d['teacher']['teacher_sec'])} 秒（{d['teacher']['source']}"
              + (f"；講稿自己的總長 {fmt(d['teacher'].get('script_total_sec'))} 秒、預錄 {fmt(d['teacher'].get('script_playback_level0_sec'))} 秒、教師講述 {fmt(d['teacher'].get('script_teacher_speaking_sec'))} 秒、按鍵與換景 {fmt(d['teacher'].get('script_press_and_scene_sec'))} 秒" if d['teacher'].get('script_total_sec') else "")
              + f"）。合計 {fmt(d['total_sec'])} 秒＝{fmt(d['total_min'], 2)} 分；≤ 38 分：{fmt(d['pass_le_38min'])}（餘 {fmt(d['margin_sec'])} 秒）。", "",
              "| 段 | 驗收包時間 | 與建置一致（sha1） | cue 長度（包） | 建置 | 預算差 | I LUFS | 偏差 LU | 對白 LUFS | 真峰值 | 削波 | 光敏 16×9 | 光敏 32×18 | 孤立亮度比 | 光敏判定 | 字幕時間差 | 線到頭部 px | 線經過兒童 | 台詞≠劇本 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in A["segments"]:
            if not r.get("exists"):
                L.append(f"| {r['act']} | 沒有驗收包 | — | — | {fmt(r['current_build']['cue_total_sec'])} | — | — | — | — | — | — | — | — | — | — | — | — | — | — |")
                continue
            lo_, fl_, ss_, sa_, du_ = r.get("loudness") or {}, r.get("flash") or {}, r.get("subtitle_sync") or {}, r.get("safety") or {}, r.get("durations") or {}
            g = lambda m: f"{m.get('luma')}／{m.get('red')}" if m else "—"
            hm = r.get("matches_current_build")
            tlm = r.get("timeline_match_fallback")
            L.append(f"| {r['act']} | {r.get('pack_generated')} | {('沒有指紋' + ('（時間軸相同）' if tlm else '（時間軸不同）' if tlm is False else '')) if hm is None else fmt(hm)} | {fmt(du_.get('act_total_sec'))} | {fmt(r['current_build']['cue_total_sec'])} | {fmt(du_.get('diff_vs_budget_sec'))} | "
                     f"{fmt(lo_.get('I_LUFS'))} | {fmt(lo_.get('dev_from_median_LU'))} | {fmt(lo_.get('dialog_median_mix_I_LUFS'))} | {fmt(lo_.get('TP_dBTP'))} | {lo_.get('clipped_samples', '—')} | "
                     f"{g(fl_.get('grid16x9'))} | {g(fl_.get('fine32x18'))} | {fmt(fl_.get('isolated_max_ratio'), 3)} | {'通過' if fl_.get('pass') else ('不通過' if fl_.get('pass') is False else '—')} | "
                     f"{ss_.get('pass', '—')}／{ss_.get('pages', '—')} | {fmt(sa_.get('min_dist_to_head_px'))} | {sa_.get('string_through_child_frames', '—')} | {sa_.get('lines_differ_from_script', '—')} |")
        iso_bad = [(r["act"], (r.get("flash") or {}).get("isolated_over_limit")) for r in A["segments"] if (r.get("flash") or {}).get("isolated_over_limit")]
        if iso_bad:
            L.append("")
            for a, cs in iso_bad:
                L.append(f"- {a} 孤立單格亮度比 > 1.2：" + "、".join(f"{c.get('cue')} {c.get('cue_t')} 秒 ×{c.get('ratio')}" for c in cs[:8]))
        srcs = sorted({(r.get("flash") or {}).get("isolated_source") or "" for r in A["segments"] if r.get("exists")} - {""})
        if any("補算" in x for x in srcs):
            L.append("")
            L.append("- 孤立單格亮度比來源：" + "；".join(f"{r['act']} {(r.get('flash') or {}).get('isolated_source')}" for r in A["segments"] if "補算" in ((r.get("flash") or {}).get("isolated_source") or "")) + "（packs/isolated/）。")
        diffs = [(r["act"], r["duration_diffs_vs_build"]) for r in A["segments"] if r.get("duration_diffs_vs_build")]
        if diffs:
            L.append("")
            for a, ds in diffs:
                L.append(f"- {a} 驗收包與目前建置不同的 cue：" + "、".join(f"{x['cue']} {x['pack']}→{x['build']} 秒" for x in ds[:8]))
        L.append("")
    if P:
        f_, ld = P["frames"], P["load"] or {}
        cr = P["criteria_v12_24_5"]
        L += ["## (b) 即時播放效能（開發機實測；學校筆電未驗證）", ""] + build_notes(BC, ["live"]) + [
              f"- 環境：{P['environment'].get('gpu')}；時鐘 {P['environment'].get('clock')}；無頭 {fmt(P['environment'].get('headless'))}；畫質 {P['environment'].get('quality')}；鎖 30 fps {fmt(P['environment'].get('lock30'))}；1920×1080；"
              f"按鍵間隔 {P['environment'].get('gapSec')} 秒、出題等 {P['environment'].get('quizWaitSec')} 秒；系統負載（1 分鐘平均）平均 {fmt(P['memory']['loadavg1']['mean'], 2)}、最高 {fmt(P['memory']['loadavg1']['max'], 2)}。",
              f"- 載入：開頁到「準備播放」可按 {ld.get('ready_button_ms')} ms；按「準備播放」到片頭待機 {ld.get('ready_click_to_title_ms')} ms（預熱 {fmt(ld.get('warm_ms'), 0)} ms）；開頁到片頭待機合計 {ld.get('open_to_title_idle_ms')} ms。",
              f"- 影格時間（播放中 {f_['playing']} 格）：p50 {fmt(f_['p50_ms_playing'], 2)} ms、p95 {fmt(f_['p95_ms_playing'], 2)} ms、p99 {fmt(f_['p99_ms_playing'], 2)} ms、最大 {fmt(f_['max_ms_playing'])} ms；平均 {fmt(f_['mean_fps_playing'])} fps；"
              f"> 34 ms {f_['over_34ms_playing']} 格、> 50 ms {f_['over_50ms_playing']} 格；開演後全部格 p95 {fmt(f_['p95_ms_all'], 2)} ms。",
              f"- 播放中／停格的分法：{P.get('frame_classification', '—')}。",
              f"- > 100 ms 卡頓：開演後 {P['stalls_over_100ms_count']} 次（播放中 {P['stalls_over_100ms_playing_count']} 次、停格中 {P.get('hold_stalls_over_100ms_count', '—')} 次）；"
              f"播放中的卡頓：在 fade 黑格內（卡住與卡完的畫面全畫面亮度都 < {FADE_BLACK}）{P.get('stalls_in_fade_black', '—')} 次、不在黑格內 {P.get('stalls_not_in_fade_black', '—')} 次、沒量到 {P.get('stalls_luma_unmeasured', '—')} 次；"
              f"在對白或揭答中 {P['stalls_in_dialog_or_reveal']} 次。"
              + ("發生在：" + "、".join(f"{s['cue']} {s['cueTime']} 秒（{s['interval_ms']} ms；亮度 {fmt(s.get('luma_before'), 3)}→{fmt(s.get('luma_after'), 3)}"
                                         f"{'，黑格內' if s.get('in_fade_black') else ('，不在黑格內' if s.get('in_fade_black') is False else '')}{'，對白' if s['in_dialog'] else ''}{'，揭答' if s['in_reveal'] else ''}）"
                                         for s in P["stalls_over_100ms"][:12]) if P["stalls_over_100ms"] else ""),
              f"- 停格中（畫面靜止，預先建下一個景）的長格：> 50 ms {(P.get('hold_long_frames_over_50ms') or {}).get('count', '—')} 格、最長 {fmt((P.get('hold_long_frames_over_50ms') or {}).get('max_ms'))} ms"
              + ("（" + "、".join(f"{h['cue']} {h['interval_ms']} ms" for h in (P.get('hold_long_frames_over_50ms') or {}).get('list', [])[:10]) + "）" if (P.get('hold_long_frames_over_50ms') or {}).get('list') else "")
              + "；不算播放中卡頓。",
              f"- v1.2 第 24 節第 5 項：p95 ≤ 34 ms {fmt(cr['p95_le_34ms'])}；卡頓 ≤ 2 次 {fmt(cr['stalls_le_2'])}；不在對白或揭答中 {fmt(cr['no_stall_in_dialog_or_reveal'])}；耐熱測試 {cr['heat_test_30min_idle_40min_show']}。",
              f"- 長動畫格（LoAF ≥ 50 ms）：{P['long_animation_frames']['count']} 個，> 100 ms {P['long_animation_frames']['over_100ms']} 個。",
              f"- 記憶體：JS heap {fmt(P['memory']['js_heap_used_MB']['min'])}–{fmt(P['memory']['js_heap_used_MB']['max'])} MB（開演第一次 {fmt(P['memory']['js_heap_used_MB']['first_play'])}、最後 {fmt(P['memory']['js_heap_used_MB']['last_play'])}；"
              f"播放中斜率 {fmt(P['memory']['js_heap_used_MB']['slope_MB_per_min_playing'], 2)} MB／分；前 10 分平均 {fmt(P['memory']['js_heap_used_MB']['first10min_mean'])}、後 10 分 {fmt(P['memory']['js_heap_used_MB']['last10min_mean'])}）；"
              f"Chrome 各程序 RSS 合計 {fmt(P['memory']['process_rss_total_MB']['min'])}–{fmt(P['memory']['process_rss_total_MB']['max'])} MB（macOS RSS，只當參考）；DOM 節點最多 {P['memory']['dom_nodes_max']}。",
              f"- 字幕與語音時間差（voiceSync，說話時每秒一次 {P['voice_sync']['samples']} 筆）：最大 {fmt(P['voice_sync']['max_abs_ms'], 0)} ms、p95 {fmt(P['voice_sync']['p95_abs_ms'], 0)} ms、> 50 ms {P['voice_sync']['over_50ms']} 次。",
              f"- 字幕內容（每 0.2 秒、台詞進行中、無題卡）：{P['subtitles']['checked_samples']} 筆，不符 {P['subtitles']['mismatch']} 筆。",
              f"- 嘴型（≥ 1.5 秒、說話者有臉部資料的句子）：{P['mouth']['lines_moved']}／{P['mouth']['lines_checked']} 句說話時嘴型換片 ≥ 2 種。",
              f"- 流程：依序經過 {P['flow']['visited']}／{P['flow']['expected']} 個 cue（順序一致 {fmt(P['flow']['all_visited_in_order'])}）；最後 {(P['flow']['end'] or {}).get('cueId')} {(P['flow']['end'] or {}).get('phase')}、八盞燈 {(P['flow']['end'] or {}).get('lampsLit')}；"
              f"開演到片尾 {fmt(P['flow']['wall_min'], 2)} 分（含按鍵間隔）；頁面錯誤 {len(P['page_errors'])} 則。", "",
              "| 段 | 播放中格數 | p50 ms | p95 ms | 最大 ms | > 50 ms |", "|---|---|---|---|---|---|"]
        for s, v in sorted(P["per_segment"].items(), key=lambda kv: str(kv[0])):
            L.append(f"| {s} | {v['frames']} | {fmt(v['p50_ms'], 2)} | {fmt(v['p95_ms'], 2)} | {fmt(v['max_ms'])} | {v['over_50ms']} |")
        L += ["", "p95 最高的 cue：" + "、".join(f"{c['cue']} {fmt(c['p95_ms'], 1)} ms" for c in P["worst_cues_p95"][:8]), ""]
    if C:
        L += ["## (c) 段落接縫", ""] + build_notes(BC, ["seams"]) + [
              f"- 8 個接縫光敏全部通過：{fmt(C['all_flash_pass'])}；一格硬切（沒有預捲、區域亮度差 > 0.1）：{'、'.join(C['hard_cuts']) or '無'}；按下一步後第一格與前段最後一格的平均亮度差最大 {fmt(C['max_abs_first_shown_delta'], 4)}。", "",
              "| 接縫 | cue | 景 | 預捲／漸亮 秒 | 前段最後 | 後段第一格 | 第一個全亮格 | Δ第一格（區域最大） | Δ全亮（區域最大） | 光敏 16×9 | 32×18 | 圖 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in C["seams"]:
            if "error" in r:
                L.append(f"| {r['seam']} | {r['error']} |||||||||||")
                continue
            ml = r["mean_luma"]
            L.append(f"| {r['from']}→{r['to']} | {r['prevCue']}→{r['nextCue']} | {r['setFrom']}→{r['setTo']} | {r['preroll_sec']}／{r['enterFade_sec']} | {ml['prevLast']:.3f} | {ml['nextFirstShown']:.3f} | {ml['nextFirstLit']:.3f} | "
                     f"{r['first_shown_minus_last']:+.3f}（{r['max_region_luma_delta_first_shown']:.3f}） | {r['first_lit_minus_last']:+.3f}（{r['max_region_luma_delta_first_lit']:.3f}） | "
                     f"{r['flash']['grid16x9']['luma']}／{r['flash']['grid16x9']['red']} | {r['flash']['fine32x18']['luma']}／{r['flash']['fine32x18']['red']} | {r['image']} |")
        L.append("")
    if N:
        L += ["## (d) 離線", ""] + build_notes(BC, ["live", "seams", "ops"]) + [
              f"- 外部請求合計 {N['external_total']}（即時播放 {N['live_external']}／{N['live_requests']} 個請求、接縫擷取 {N['seams_external']}／{N['seams_requests']}、操作補測 {N['ops_external']}／{N['ops_requests']}）；零外部請求：{fmt(N['pass_zero_external'])}；"
              f"失敗的本機請求 {N['live_failed']} 個。", ""]
    if E:
        et = E["engine_test"]
        L += ["## (e) 操作", ""] + build_notes(BC, ["engine_test", "ops"]) + [
              f"- engine-test：{(et['summary'] or {}).get('passed', et['passed'])}／{(et['summary'] or {}).get('total', et['checks'])} 項通過（{et['log']}）；失敗 {len(et['failed'])} 項。",
              f"- 全劇模式補測：{E['show_supplement']['passed']}／{E['show_supplement']['checks']} 項通過（ops/ops_show.json）。", "",
              "| 操作 | engine-test 項數（通過） | 全劇補測項數（通過） |", "|---|---|---|"]
        for c in E["categories"]:
            L.append(f"| {c['category']} | {c['engine_test']['checks']}（{c['engine_test']['passed']}） | {c['show_supplement']['checks']}（{c['show_supplement']['passed']}） |")
        fails = E["engine_test"]["failed"] + E["show_supplement"]["failed"]
        if fails:
            L += ["", "失敗：" + "；".join(f"{f['name']}（{f.get('detail', '')}）" for f in fails[:10])]
        L.append("")
    if F:
        L += ["## (f) 署名卡", ""] + build_notes(BC, ["live"]) + [
              f"- 片頭：DOM「{F['start'].get('text')}」、顯示 {fmt(F['start']['visible'])}（{F['start'].get('cueId')} {F['start'].get('phase')}）；片尾：DOM「{F['end'].get('text')}」、顯示 {fmt(F['end']['visible'])}（{F['end'].get('cueId')} {F['end'].get('phase')}）；"
              f"都是「{SIGNATURE}」：{fmt(F['pass'])}。圖：attribution/attribution.jpg。", ""]
    if G:
        L += ["## (g) 八題", ""] + build_notes(BC, ["live"]) + [
              f"- {G['passed']}／{G['quizzes']} 題通過（出題 → 不自動揭答 → 揭答印章在正解 → 點燈 → 續演，題卡文字＝八題_v03.md）；印章位置依序 {G['observed_answers_stamp']}（應為 {G['expected_answers']}）；演完八盞燈 {G['end_lamps']}。", "",
              "| 題 | cue | 正解（應／cue／題卡檔） | 印章 | 題卡文字一致 | 不自動揭答 | 點燈後 | 續演 | 通過 |", "|---|---|---|---|---|---|---|---|---|"]
        for r in G["rows"]:
            L.append(f"| {r['qid']} | {r['cue']} | {r['answer_expected']}／{r['answer_cue_data']}／{r['answer_doc']} | {' '.join(r['stamp_classes'])} | {fmt(r['text_matches_doc'])} | {fmt(r['no_auto_reveal'])}（等 {r['no_auto_reveal_after_sec']} 秒） | "
                     f"{r['lamp_lit_after']} | {(r['continued_to'] or {}).get('cue')} | {fmt(r['pass'])} |")
        L.append("")
    # (h) 交付包（tools/delivery_smoke.mjs 的結果；主線把 app/dist 複製進交付資料夾後跑，寫在 <out>/delivery/）
    D = load(out / "delivery" / "delivery_smoke.json")
    if D:
        L += ["## (h) 交付包與建置一致（tools/delivery_smoke.mjs）", "",
              f"- 測試時間 {D.get('generated')}；對照建置 `{D.get('ref')}`；整體 {'通過' if D.get('pass') else '不通過'}（delivery/delivery_smoke.md）。", "",
              "| 交付資料夾 | 逐檔相同（diff 0） | 不加參數載入全劇 | 配音齊全 | 署名卡兩端 | 八題 | 實鍵走一題 | 啟動說明 | 外部請求 0 | 頁面錯誤 0 |", "|---|---|---|---|---|---|---|---|---|---|"]
        w = lambda c: "—" if not c else ("通過" if c.get("ok") else "不通過")
        for t in D.get("targets", []):
            c = t.get("checks", {})
            diff = t.get("diff") or {}
            L.append(f"| {t['target']} | {w(c.get('identical_to_build'))}（不同 {len(diff.get('different', []))}、缺 {len(diff.get('missing', []))}、多 {len(diff.get('extra', []))}） | {w(c.get('loads_show_without_params'))} | "
                     f"{w(c.get('audio_complete'))} | {w(c.get('attribution_both_ends'))} | {w(c.get('quiz_order_answers'))} | {w(c.get('quiz_real_keys'))} | {w(c.get('startup_note'))} | "
                     f"{w(c.get('zero_external_requests'))} | {w(c.get('no_page_errors'))} |")
        try:
            gen = datetime.fromisoformat(D["generated"].replace("Z", "+00:00")).timestamp()
            js = ROOT / "app/dist/app.js"
            if js.exists() and js.stat().st_mtime > gen:
                L.append("")
                L.append("- 注意：app/dist 在這次交付冒煙測試之後又重建過，請重新複製交付包並重跑 tools/delivery_smoke.mjs。")
        except (KeyError, ValueError):
            pass
        L.append("")
    (out / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main(out, packs):
    show = load(out / "show_timeline.json")
    A = packs_table(out, packs, show)
    print("[g6pack.py] (a) 九段彙整完成")
    P = perf(out, show)
    print("[g6pack.py] (b) 效能" + ("完成" if P else "：沒有 live/live_raw.json"))
    C = seams(out)
    print("[g6pack.py] (c) 接縫" + ("完成" if C else "：沒有 seams/seams_raw.json"))
    E = ops(out)
    F = attribution(out)
    G = quiz(out, show)
    N = network(out)
    summary = {"generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "a_packs": {k: A[k] for k in ("packs_matching_build", "packs_total", "flash_all_pass", "subtitle_sync_all_pass")} | {"loudness": {k: A["loudness"][k] for k in ("median_I_LUFS", "max_abs_dev_LU", "pass_pm1", "dialog_max_abs_dev_LU")}, "duration": {k: A["duration"][k] for k in ("playback_current_build_sec", "total_min", "pass_le_38min", "margin_sec")}},
               "b_perf": ({"p95_ms_playing": P["frames"]["p95_ms_playing"], "stalls_over_100ms_playing": P["stalls_over_100ms_playing_count"], "stalls_in_dialog_or_reveal": P["stalls_in_dialog_or_reveal"], "criteria": P["criteria_v12_24_5"],
                           "load_open_to_title_ms": (P["load"] or {}).get("open_to_title_idle_ms"), "js_heap_max_MB": P["memory"]["js_heap_used_MB"]["max"], "voice_sync_max_ms": P["voice_sync"]["max_abs_ms"],
                           "subtitle_mismatch": P["subtitles"]["mismatch"], "flow_all_visited": P["flow"]["all_visited_in_order"]} if P else None),
               "c_seams": ({"all_flash_pass": C["all_flash_pass"], "hard_cuts": C["hard_cuts"]} if C else None),
               "d_offline": {"external_total": N["external_total"], "pass": N["pass_zero_external"]},
               "e_ops": {"engine_test": E["engine_test"]["summary"], "show_supplement": f"{E['show_supplement']['passed']}/{E['show_supplement']['checks']}"},
               "f_attribution": F["pass"] if F else None, "g_quiz": f"{G['passed']}/{G['quizzes']}" if G else None,
               "build": (lambda bc: {"current": bc.get("current"), "sections": {k: v.get("status") for k, v in (bc.get("sections") or {}).items()}} if bc else None)(load(out / "build_check.json"))}
    dump(out / "summary.json", summary)
    index(out, packs, show, A, P, C, E, F, G, N)
    print(f"[g6pack.py] → {out / 'INDEX.md'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / "review/G5")
