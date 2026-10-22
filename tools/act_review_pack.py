"""G5 各幕驗收包分析（由 tools/act_review_pack.mjs 呼叫）。

用法：
  /opt/anaconda3/bin/python3 tools/act_review_pack.py analyze <驗收包資料夾>
  tools/.venv/bin/python     tools/act_review_pack.py transcripts <驗收包資料夾>
  /opt/anaconda3/bin/python3 tools/act_review_pack.py index <驗收包資料夾>

analyze 沿用 tools/g4_review_pack.py 的函式（投影模擬、混音、光敏、字幕時間差），只把 G4 專用的部分換成通用版：
  1. 關鍵影格投影模擬 v2（proj/）
  2. 與 G4 代表鏡頭同尺寸並排的對照格（compare_g4/）
  3. 依 timeline.json 照引擎規則混音：整段、各 cue、各句對白響度、瞬間響度、教師停格配樂（audio/）
  4. 播放錄製（含換景漸暗預捲）30 格／秒光敏分析（flash_playback.json、flash_variants.json）
  5. 影片 <段>_playback.mp4、字幕與語音時間差（subtitle_sync.json）
  6. 長度對照 時長估算_v03.md 預算（durations.json）、安全量測（safety_data.json）
transcripts：配音（v04）逐句 faster-whisper 逐字稿與劇本差異（方法同 tools/g4_transcripts.py，用 tools/vo_lib.py）。
index：INDEX.md（只列數字與檔案，不寫評語）。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
FPS = 30
G4_REFS = ["a2_c002_012.59_mid", "a2_c004_010.96_mid", "a0_c001_011.60_after", "a2_c002_025.18_after"]
CHILDREN = ("xiaoqing", "xiaoyu", "pinan")
FRAME_W, FRAME_H = 1920, 1080


def rel(p, base):
    return os.path.relpath(p, base).replace(os.sep, "/")


def load(out, name):
    p = out / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ====================================================================== 播放錄製逐格清單（含預捲）
def playback_sequence(out: Path, tl: dict):
    """[(全域秒, 檔案, cue, cue 內秒)]：預捲格（cue 內秒為負）→ cue 逐格 → 停住格（重複 after.jpg）"""
    work = out / "_work" / "video"
    seq = []
    for s in tl["schedule"]:
        G, D, hold, pre = s["start"], s["duration"], s["hold"], s.get("preroll", 0)
        d = work / s["id"]
        f_pre0 = int(round((G - pre) * FPS))
        f0 = int(round(G * FPS))
        for k in range(f0 - f_pre0):
            p = d / f"pre_{k:05d}.jpg"
            if p.exists():
                seq.append((round((f_pre0 + k) / FPS, 4), p, s["id"], round(-pre + k / FPS, 4)))
        f_end = int(round((G + D) * FPS))
        f_hold = int(round((G + D + hold) * FPS))
        for k in range(f_end - f0):
            p = d / f"{k:05d}.jpg"
            if not p.exists():
                p = d / "after.jpg"
            seq.append((round((f0 + k) / FPS, 4), p, s["id"], round(k / FPS, 4)))
        for k in range(f_end, f_hold):
            seq.append((round(k / FPS, 4), d / "after.jpg", s["id"], round(D + (k - f_end) / FPS, 4)))
    return seq


# ====================================================================== 與 G4 並排
def compare_g4(out: Path):
    from PIL import Image, ImageDraw
    import capture_analyze as ca
    cap = out / "capture"
    meta = json.loads((cap / "capture.json").read_text(encoding="utf-8"))
    g4dir = ROOT / "review/G4/pack/capture/keyframes"
    refs = [g4dir / f"{r}.png" for r in G4_REFS if (g4dir / f"{r}.png").exists()]
    keys = [f for f in meta["frames"] if f.get("key") and ("mid" in f["key"] or "after" in f["key"])]
    rows = {}
    for f in keys:
        rows.setdefault(f["cueId"], []).append(f)
    tw, th = 640, 360
    pdir = out / "compare_g4"
    pdir.mkdir(parents=True, exist_ok=True)
    made = []
    items = list(rows.items())
    per_sheet = 6
    for si in range(0, len(items), per_sheet):
        chunk = items[si:si + per_sheet]
        Wd = 170 + 3 * (tw + 12)
        Hd = 50 + len(chunk) * (th + 30)
        sheet = Image.new("RGB", (Wd, Hd), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        d.text((10, 10), f"本段關鍵影格（中／後）｜G4 代表鏡頭基準（同尺寸 {tw}×{th}，來源 review/G4/pack/capture/keyframes）", font=ca.font(20), fill=(240, 236, 228))
        y = 50
        for ri, (cue, fs) in enumerate(chunk):
            d.text((10, y + 4), cue, font=ca.font(20), fill=(232, 200, 140))
            cells = [(cap / f["file"], f"{f['key']} {f['t']:.2f}s") for f in fs[:2]]
            ref = refs[(si + ri) % len(refs)] if refs else None
            if ref:
                cells.append((ref, f"G4 {ref.stem}"))
            for ci, (p, lab) in enumerate(cells):
                x = 170 + ci * (tw + 12)
                sheet.paste(Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
                d.text((x, y + th + 4), lab, font=ca.font(15), fill=(200, 196, 188))
            y += th + 30
        path = pdir / f"compare_g4_{si // per_sheet + 1:02d}.png"
        sheet.save(path)
        made.append(rel(path, out))
    return {"sheets": made, "g4_refs": [rel(r, ROOT) for r in refs], "size": [tw, th]}


# ====================================================================== 字幕與語音時間差（G5 修正第 1 輪：靜音偵測 −40 dB、最短 0.05 秒）
SYNC_NOISE_DB, SYNC_MIN_SIL = -40, 0.05


def voice_onsets_g5(path: Path):
    """配音檔的語音起點：ffmpeg silencedetect noise=−40 dB、d=0.05 s（G4 是 −45 dB、0.1 s，抓不到句中短停頓，b1 驗收兩處誤判）"""
    import re
    import subprocess
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", f"silencedetect=noise={SYNC_NOISE_DB}dB:d={SYNC_MIN_SIL}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    out = []
    if not starts or starts[0] > 0.01:
        out.append(0.0)
    return out + ends


def subtitle_sync_g5(out: Path, tl: dict):
    """字幕頁起點 − 該頁語音起點；方法同 g4_review_pack.subtitle_sync，只把靜音偵測改成 −40 dB、0.05 秒"""
    LO, HI = -0.8, 0.1
    rows = []
    for c in tl["cues"]:
        for l in c["lines"]:
            if l["audioId"] not in tl["audio"]:
                continue
            src = ROOT / tl["audio"][l["audioId"]]["source"]
            ons = voice_onsets_g5(src)
            for k, pg in enumerate(l["pages"]):
                relt = pg["start"] - l["start"]
                if k == 0:
                    on = ons[0]
                else:
                    cand = [o for o in ons if o >= relt + LO]
                    on = min(cand, key=lambda o: abs(o - relt)) if cand else ons[-1]
                d = round(pg["start"] - (l["start"] + on), 3)
                rows.append({"cue": c["id"], "line": l["id"], "page": k + 1, "text": "／".join(pg["rows"]), "subtitle_start_s": pg["start"],
                             "voice_start_s": round(l["start"] + on, 3), "diff_s": d, "pass": LO <= d <= HI, "audio": rel(src, ROOT)})
    res = {"method": f"ffmpeg silencedetect noise={SYNC_NOISE_DB} dB、d={SYNC_MIN_SIL} s 找配音檔的語音起點（G5 修正第 1 輪：G4 的 −45 dB、0.1 s 抓不到句中短停頓，"
                     "b1 驗收 a2_c003_02、a4_c001_01 兩頁誤判）；第 1 頁＝第一個起點，之後各頁＝頁起點前後最接近的停頓後起點；差值＝字幕頁起點 − 語音起點",
           "silencedetect": {"noise_dB": SYNC_NOISE_DB, "min_silence_s": SYNC_MIN_SIL},
           "range_s": [LO, HI], "rows": rows, "all_pass": all(r["pass"] for r in rows)}
    (out / "subtitle_sync.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


# ====================================================================== 混音與響度（通用版）
def audio_analysis(out: Path, tl: dict):
    import numpy as np
    import g4_review_pack as g4
    SR = g4.SR
    adir = out / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    work = out / "_work"
    act = tl["act"]
    mixed, stems, spans, elog, ts, lvl, dk = g4.mix(out, tl)
    peak = float(np.abs(mixed).max()) if len(mixed) else 0.0
    g4.write_wav(adir / f"{act}_mix.wav", mixed, 16)
    full = g4.ebur(mixed)
    mom = g4.momentary(mixed)
    per_cue = {}
    for s in tl["schedule"]:
        if s["duration"] >= 1.0:
            x = mixed[int(s["start"] * SR):int((s["start"] + s["duration"]) * SR)]
            per_cue[s["id"]] = g4.ebur(x)
    bg = stems["music"] + stems["sfx"]
    (work / "mixseg").mkdir(parents=True, exist_ok=True)
    lines = []
    for sp in spans:
        i0, i1 = int(sp["start"] * SR), int(sp["end"] * SR)
        vo_file = ROOT / tl["audio"][sp["audioId"]]["source"]
        f = g4.ebur(g4.load_wav(vo_file)[:, 0])
        in_mix = g4.ebur(mixed[i0:i1])
        vo_in = g4.ebur(stems["vo"][i0:i1])
        bgm = g4.ebur(bg[i0:i1])
        g4.write_wav(work / "mixseg" / f"{sp['id']}.wav", mixed[max(0, i0 - int(0.1 * SR)):i1 + int(0.1 * SR)], 16)
        lines.append({"id": sp["id"], "cue": sp["cue"], "speaker": sp["speaker"], "start": round(sp["start"], 3), "end": round(sp["end"], 3),
                      "vo_file": rel(vo_file, ROOT), "vo_file_I_LUFS": f["I_LUFS"], "vo_file_TP_dBTP": f["TP_dBTP"],
                      "mix_I_LUFS": in_mix["I_LUFS"], "vo_in_mix_I_LUFS": vo_in["I_LUFS"], "background_I_LUFS": bgm["I_LUFS"],
                      "vo_minus_background_LU": None if (vo_in["I_LUFS"] is None or bgm["I_LUFS"] is None) else round(vo_in["I_LUFS"] - bgm["I_LUFS"], 1)})
    vals = [l["vo_file_I_LUFS"] for l in lines if l["vo_file_I_LUFS"] is not None]
    mvals = [l["mix_I_LUFS"] for l in lines if l["mix_I_LUFS"] is not None]
    M = np.array([m[1] for m in mom]) if mom else np.array([])
    T = np.array([m[0] for m in mom]) if mom else np.array([])
    rise1 = rise01 = None
    if len(M) > 10:
        Mc = np.maximum(M, -70.0)
        rise1 = max(float(Mc[i] - Mc[max(0, i - 10):i].min()) for i in range(1, len(Mc)))
        rise01 = float(np.max(Mc[1:] - Mc[:-1]))
    # 只有配樂與音效（不含配音）的分軌（G5 修正第 1 輪；G4 驗收包的 momentary_music_sfx_only 同算法）：
    # 瞬間響度最大、100 ms 最大上升、1 秒內最大上升、峰值——讓驗收能用數字排除「音效或配樂的突發巨響」（語音起音不算）
    bg_stats = music_sfx_only_stats(bg, mom_times=None, tl=tl)
    holds = []
    for s_ in tl["schedule"]:
        if s_["kind"] != "scene" or s_["hold"] < 3.2:
            continue
        h0 = s_["start"] + s_["duration"]
        after = [m[1] for m in mom if h0 + 3.0 - 1e-6 <= m[0] <= h0 + s_["hold"] + 1e-6]
        holds.append({"cue": s_["id"], "hold_from_sec": round(h0, 3), "hold_sec": s_["hold"],
                      "momentary_max_after_3s_LUFS": round(float(max(after)), 1) if after else None,
                      "pass_le_-35": bool(max(after) <= -35.0) if after else None})
    res = {
        "note": "依 timeline.json 的 cue 時間與教師按鍵間隔假設（含換景漸暗預捲），照引擎混音規則（tools/g4_review_pack.py mix()：三條匯流排、配樂基準音量、對白避讓、教師停格降配樂、交叉淡入淡出、換 cue 停台詞與音效）以 48 kHz 離線混音；總音量 1.0；開頭靜音 0 ms。",
        "file": f"audio/{act}_mix.wav",
        "duration_sec": round(len(mixed) / SR, 3),
        "sample_peak_dBFS": round(20 * np.log10(max(peak, 1e-9)), 2),
        "clipped_samples": int((np.abs(mixed) >= 1.0).sum()),
        "full_playback": full,
        "per_cue": per_cue,
        "lines": lines,
        "line_vo_file_I_spread_LU": round(max(vals) - min(vals), 2) if vals else None,
        "line_mix_I_spread_LU": round(max(mvals) - min(mvals), 2) if mvals else None,
        "momentary_max_LUFS": round(float(M.max()), 1) if len(M) else None,
        "momentary_max_rise_within_1s_LU": round(rise1, 1) if rise1 is not None else None,
        "momentary_max_rise_per_100ms_LU": round(rise01, 1) if rise01 is not None else None,
        "momentary_note": "瞬間響度（BS.1770 K 加權，400 ms 窗，每 100 ms）；上升量以 −70 LUFS 為下限計算。momentary_* 是總混音（含配音：句首起音會被算成上升）；music_sfx_only 是不含配音的配樂＋音效分軌（含配樂基準音量、對白避讓、教師停格降配樂）。",
        "music_sfx_only": bg_stats,
        "freeze_holds": holds,
        "freeze_rule": "教師停格（劇情段落播完、等老師按鍵）：配樂在停住後 3 秒內降到 ≤ −35 LUFS（瞬間響度，400 ms 窗）",
        "ducking_constants": dk,
        "events": elog,
    }
    (adir / "loudness.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    plot_audio(adir / f"{act}_mix_plot.png", stems, lvl, ts, T, M, tl, spans, act)
    return res


def plot_audio(path, stems, lvl, ts, T, M, tl, spans, act):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for fp in ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc"):
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
            break
    fig, ax = plt.subplots(4, 1, figsize=(18, 10), sharex=True)
    step = 240
    for i, (k, lab) in enumerate((("vo", "配音"), ("music", "配樂（含基準音量與避讓）"), ("sfx", "音效"))):
        x = stems[k][:, 0]
        n = len(x) // step * step
        env = np.abs(x[:n]).reshape(-1, step).max(axis=1)
        ax[i].fill_between(ts[::step][:len(env)], -env, env, lw=0, color=("#3b6ea8", "#a8643b", "#5a8a4a")[i])
        ax[i].set_ylabel(lab, rotation=0, ha="right", va="center")
        ax[i].set_ylim(-1, 1)
    ax[1].plot(ts[::step], lvl[::step], color="k", lw=0.8)
    if len(M):
        ax[3].plot(T, np.maximum(M, -60), lw=0.8, color="#333")
    ax[3].set_ylabel("總混音瞬間響度\nLUFS（400 ms）", rotation=0, ha="right", va="center")
    ax[3].set_ylim(-60, -5)
    for s in tl["schedule"]:
        for a in ax:
            a.axvline(s["start"], color="#999", lw=0.6, ls="--")
        ax[0].text(s["start"] + 0.2, 0.75, s["id"], fontsize=8)
    for sp in spans:
        ax[0].axvspan(sp["start"], sp["end"], color="#3b6ea8", alpha=0.08)
    ax[3].set_xlabel("播放時間（秒，含換景預捲與教師按鍵間隔假設）")
    fig.suptitle(f"{act} 混音：分軌波形與瞬間響度")
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


# ====================================================================== 影片
def make_video(out: Path, seq, act: str):
    sdir = out / "_work" / "seq"
    if sdir.exists():
        for f in sdir.iterdir():
            f.unlink()
    sdir.mkdir(parents=True, exist_ok=True)
    for i, (t, p, cue, ct) in enumerate(seq):
        os.symlink(p, sdir / f"{i:06d}.jpg")
    mp4 = out / f"{act}_playback.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(sdir / "%06d.jpg"), "-i", str(out / "audio" / f"{act}_mix.wav"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(mp4)]
    subprocess.run(cmd, check=True)
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames",
                                    "-of", "json", str(mp4)], capture_output=True, text=True).stdout)
    return {"file": mp4.name, "frames": len(seq), "ffprobe": pr}


# ====================================================================== 長度對照預算
def durations(out: Path, tl: dict):
    text = (ROOT / "script/時長估算_v03.md").read_text(encoding="utf-8")
    est = {}
    for raw in text.splitlines():
        m = re.match(r"^\| (a\d_c\d{3}) \|", raw)
        if m:
            cols = [c.strip() for c in raw.strip().strip("|").split("|")]
            try:
                est[m.group(1)] = float(cols[9])
            except (ValueError, IndexError):
                pass
    budget = None
    for raw in text.splitlines():
        m = re.match(rf"^\| {tl['act']} [^|]*\|(.+)$", raw)
        if m:
            cols = [c.strip() for c in raw.strip().strip("|").split("|")]
            mm = re.match(r"([\d.]+) 秒", cols[-1])
            if mm:
                budget = float(mm.group(1))
    rows = []
    for c in tl["cues"]:
        s = next(x for x in tl["schedule"] if x["id"] == c["id"])
        rows.append({"cue": c["id"], "kind": c["kind"], "duration_sec": c["duration"], "preroll_sec": s.get("preroll", 0),
                     "estimate_sec": est.get(c["id"]), "diff_sec": round(c["duration"] - est[c["id"]], 1) if c["id"] in est else None,
                     "vo_sec": round(sum(l["duration"] for l in c["lines"]), 2), "lines": len(c["lines"])})
    tot = round(sum(r["duration_sec"] for r in rows), 1)
    pre = round(sum(r["preroll_sec"] for r in rows), 1)
    est_sum = round(sum(r["estimate_sec"] or 0 for r in rows), 1)
    res = {"source": "script/時長估算_v03.md 第 2 節逐 cue「估計」與第 3 節「預錄合計」；本段長度＝引擎時間軸（實際配音長度）",
           "cues": rows, "act_total_sec": tot, "act_preroll_total_sec": pre, "estimate_sum_sec": est_sum,
           "act_budget_recorded_sec": budget, "diff_vs_budget_sec": round(tot + pre - budget, 1) if budget else None,
           "playback_with_holds_sec": tl["totalPlaybackSec"], "holds_assumed_sec": {s["id"]: s["hold"] for s in tl["schedule"]}}
    (out / "durations.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


# ====================================================================== 安全量測
def safety_data(out: Path, tl: dict):
    import numpy as np
    import g4_review_pack as g4
    anchors, string_actors = set(), set()
    for c in tl["cues"]:
        for aid, lst in (c.get("strings") or {}).items():
            anchors.update(lst)
            string_actors.add(aid)
        for a in c.get("stringAnims", []):
            anchors.update(a.get("anchors") or [])
            if a.get("target"):
                string_actors.add(a["target"])
    probe = []
    src = []
    for name in ("capture/probe.json", "probe_dense.json"):
        d = load(out, name)
        if d:
            probe += d["probes"]
            src.append(name)
    head_d, kid_hits, frames = [], [], 0
    head_offscreen = 0
    per_anchor = {}
    # G5 修正第 2 輪（主線授權）：線到頭部框只算頭部框在 1920×1080 畫面內（至少一部分）的格；
    # 角色在鏡頭外時（例如 a2_c008 手部近景，阿樂紙偶 x≈26600）頭部框和線都看不到，不算（以前會量到 0.0 px）。
    in_frame = lambda b: b[2] > 0 and b[0] < FRAME_W and b[3] > 0 and b[1] < FRAME_H
    for pr in probe:
        acts = {a["id"]: a for a in pr["actors"]}
        vis = [s for s in pr["strings"] if s.get("visible") and s.get("path")]
        if not vis:
            continue
        frames += 1
        for s in vis:
            path = s["path"]
            hb = acts.get(s["actor"], {}).get("headBox")
            if hb and not in_frame(hb):
                head_offscreen += 1
            elif hb:
                dd = min(g4.seg_box_dist(path[i], path[i + 1], hb) for i in range(len(path) - 1))
                head_d.append(dd)
                pa = per_anchor.setdefault(f"{s['actor']}.{s['anchor']}", {"min_dist_to_head_box_px": np.inf, "frames": 0, "at": None})
                if dd < pa["min_dist_to_head_box_px"]:
                    pa["min_dist_to_head_box_px"], pa["at"] = dd, f"{pr['cueId']} t={pr['t']}"
                pa["frames"] += 1
            for kid in CHILDREN:
                kb = acts.get(kid, {}).get("box")
                if kb and acts[kid].get("visible"):
                    dd = min(g4.seg_box_dist(path[i], path[i + 1], kb) for i in range(len(path) - 1))
                    if dd == 0.0:
                        kid_hits.append({"cue": pr["cueId"], "t": pr["t"], "anchor": f"{s['actor']}.{s['anchor']}", "kid": kid})
    for v in per_anchor.values():
        v["min_dist_to_head_box_px"] = round(float(v["min_dist_to_head_box_px"]), 1)
    # 必要旁白（CLAUDE.md、劇本 v03、cue 檔三方逐字比對；只列本段有的句子）
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    req = {"a2_c004_02": re.search(r"「(這些線是故事的比喻。[^」]*)」", claude), "a2_c008_05": re.search(r"「(不過，看見一個人站不穩[^」]*)」", claude)}
    script = {}
    for raw in (ROOT / "script/劇本_v03.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[(a\d_c\d{3}_\d{2})\]\s*([^：]+)：(.+?)\s*$", raw.strip())
        if m:
            script[m.group(1)] = (m.group(2), m.group(3))
    narr = {}
    lines_all = {l["id"]: l for c in tl["cues"] for l in c["lines"]}
    for lid, m in req.items():
        if lid not in lines_all:
            continue
        plain = re.sub(r"\s*\n\s*", "", lines_all[lid]["text"])
        narr[lid] = {"claude_md": m.group(1) if m else None, "script_v03": script.get(lid, (None, None))[1], "cue_text_plain": plain,
                     "speaker": lines_all[lid]["speaker"], "script_equals_claude_md": bool(m) and script.get(lid, (None, None))[1] == m.group(1),
                     "cue_equals_script": plain == script.get(lid, (None, None))[1]}
    # 全部台詞與劇本逐字比對
    text_diff = [lid for lid, l in lines_all.items() if script.get(lid) != (l["speaker"], re.sub(r"\s*\n\s*", "", l["text"]))]
    sub = []
    for c in tl["cues"]:
        for l in c["lines"]:
            rows = [r for p in l["pages"] for r in p["rows"]]
            sub.append({"id": l["id"], "pages": len(l["pages"]), "max_rows_per_page": max(len(p["rows"]) for p in l["pages"]), "max_chars_per_row": max(len(r) for r in rows)})
    app_js = (ROOT / "app/dist/app.js").read_text(encoding="utf-8")
    cap = load(out, "capture/capture.json") or {}
    res = {
        "string_anchors_in_cues": sorted(anchors),
        "string_anchors_allowed": ["elbow", "knee", "wrist"],
        "string_anchors_only_allowed": anchors <= {"wrist", "elbow", "knee"},
        "actors_with_strings": sorted(string_actors),
        "probe_frames_with_strings": frames,
        "string_path_min_dist_to_head_box_px": round(float(min(head_d)), 1) if head_d else None,
        "head_box_rule": f"只算頭部框（至少一部分）在 {FRAME_W}×{FRAME_H} 畫面內的格；頭部框整個在畫面外的線不算",
        "string_head_offscreen_skipped": head_offscreen,
        "per_anchor": per_anchor,
        "string_path_intersects_child_box": kid_hits[:50],
        "string_path_intersects_child_box_count": len(kid_hits),
        "probe_sources": src,
        "probe_method": "線路徑＝引擎實際畫的中心線投影到螢幕；頭部框＝分件紙偶 head* 部件圖外框（含透明邊）；兒童框＝立牌外框（含透明邊）。",
        "required_narration": narr,
        "lines_total": len(lines_all),
        "lines_differ_from_script_v03": text_diff,
        "subtitle_max_chars_per_row": max((s["max_chars_per_row"] for s in sub), default=None),
        "subtitle_max_rows_per_page": max((s["max_rows_per_page"] for s in sub), default=None),
        "subtitles": sub,
        "app_js_getUserMedia_count": app_js.count("getUserMedia"),
        "app_js_mediaDevices_count": app_js.count("mediaDevices"),
        "capture_external_requests": len(cap.get("externalRequests", [])),
        "capture_console_errors": len(cap.get("consoleErrors", [])),
    }
    (out / "safety_data.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def music_sfx_only_stats(bg, mom_times=None, tl=None):
    """配樂＋音效分軌（不含配音）：瞬間響度最大、100 ms 最大上升、1 秒內最大上升、取樣峰值、真峰值；各附發生的秒數與 cue。
    參考：G4 驗收包 momentary_music_sfx_only（review/G4/pack/audio/loudness.json）。"""
    import numpy as np
    import g4_review_pack as g4
    SR = g4.SR
    mm = g4.momentary(bg)
    if len(mm) < 11:
        return None
    Mv = np.maximum(np.array([m[1] for m in mm]), -70.0)
    Tv = np.array([m[0] for m in mm])
    r1 = [float(Mv[i] - Mv[max(0, i - 10):i].min()) for i in range(1, len(Mv))]
    i1 = int(np.argmax(r1)) + 1
    r01 = Mv[1:] - Mv[:-1]
    i01 = int(np.argmax(r01)) + 1
    imax = int(np.argmax(Mv))
    mono = bg.mean(axis=1) if bg.ndim == 2 else bg
    ipk = int(np.argmax(np.abs(mono))) if len(mono) else 0
    eb = g4.ebur(bg)

    def cue_at(t):
        if not tl:
            return None
        for s_ in tl["schedule"]:
            if s_["start"] - s_.get("preroll", 0) <= t < s_["start"] + s_["duration"] + s_["hold"]:
                return {"cue": s_["id"], "cue_t": round(t - s_["start"], 2)}
        return None
    ref = None
    try:
        g4l = json.loads((ROOT / "review/G4/pack/audio/loudness.json").read_text(encoding="utf-8")).get("momentary_music_sfx_only")
        ref = {k: g4l.get(k) for k in ("max_LUFS", "max_rise_within_1s_LU", "max_rise_per_100ms_LU")} if g4l else None
    except OSError:
        ref = None
    peak = float(np.abs(bg).max()) if len(bg) else 0.0
    res = {"max_LUFS": round(float(Mv.max()), 1), "max_at_sec": round(float(Tv[imax]), 1), "max_at": cue_at(float(Tv[imax])),
           "max_rise_per_100ms_LU": round(float(r01[i01 - 1]), 1), "max_rise_per_100ms_at_sec": round(float(Tv[i01]), 1), "max_rise_per_100ms_at": cue_at(float(Tv[i01])),
           "max_rise_within_1s_LU": round(r1[i1 - 1], 1), "max_rise_within_1s_at_sec": round(float(Tv[i1]), 1),
           "sample_peak_dBFS": round(20 * np.log10(max(peak, 1e-9)), 2), "sample_peak_at_sec": round(ipk / SR, 2), "sample_peak_at": cue_at(ipk / SR),
           "true_peak_dBTP": eb.get("TP_dBTP"), "I_LUFS": eb.get("I_LUFS"),
           "g4_reference": ref,
           "within_g4_max_LUFS": (float(Mv.max()) <= ref["max_LUFS"] + 1e-6) if ref and ref.get("max_LUFS") is not None else None,
           "note": "不含配音的配樂＋音效分軌；上升量以 −70 LUFS 為下限（從靜音起音會算成大上升，要看發生的 cue 與聲音是否本來就是輕的起音）；聽感未驗證。"}
    return res


def analyze(out: Path):
    import g4_review_pack as g4
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    act = tl["act"]
    res = {"act": act}
    # G5 修正第 2 輪：capture.mjs 呼叫 capture_probe.py 時這次的 timeline.json 還沒寫好；這裡用新的時間軸重跑，題卡格才排除得正確
    if (out / "capture/probe.json").exists():
        print("[actpack.py] 操偶線量測（依時間軸排除題卡格）")
        r = subprocess.run([sys.executable, str(ROOT / "tools/capture_probe.py"), str(out / "capture"), "--timeline", str(out / "timeline.json")])
        res["capture_probe_rerun"] = r.returncode == 0
    print("[actpack.py] 投影模擬")
    res["proj"] = {k: len(v) for k, v in g4.proj_keyframes(out).items()}
    print("[actpack.py] 與 G4 並排")
    res["compare_g4"] = compare_g4(out)
    print("[actpack.py] 混音與響度")
    res["audio"] = {k: v for k, v in audio_analysis(out, tl).items() if k not in ("lines", "events", "per_cue")}
    seq = playback_sequence(out, tl)
    print(f"[actpack.py] 播放逐格光敏分析（{len(seq)} 格）")
    fl = g4.flash_playback(out, seq)
    res["flash_playback"] = {k: fl[k] for k in ("ok", "max_changes_per_sec", "near_limit_total", "frames_analyzed")}
    fv = g4.flash_variants(out, seq)
    res["flash_variants"] = {k: {kk: v[kk] for kk in ("max_changes_per_sec", "near_limit_3_total")} for k, v in fv["variants"].items()}
    res["subtitle_sync"] = {k: v for k, v in subtitle_sync_g5(out, tl).items() if k != "rows"}
    print("[actpack.py] 影片")
    res["video"] = make_video(out, seq, act)
    res["durations"] = durations(out, tl)
    res["safety"] = {k: v for k, v in safety_data(out, tl).items() if k not in ("subtitles",)}
    meta = load(out, "_work/frames_meta.json") or {}
    res["frames_meta"] = {k: meta.get(k) for k in ("preroll", "engineDurations", "errors", "sets")}
    (out / "analysis.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("[actpack.py] 分析完成")


# ====================================================================== 逐字稿（tools/.venv）
def transcripts(out: Path):
    import vo_lib  # noqa: E402  （faster-whisper；方法同 tools/g4_transcripts.py）
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    script = vo_lib.load_lines()
    report = json.loads((ROOT / "audio/vo/build_report.json").read_text(encoding="utf-8")) if (ROOT / "audio/vo/build_report.json").exists() else {}
    items = []
    for c in tl["cues"]:
        for l in c["lines"]:
            src = tl["audio"].get(l["audioId"], {}).get("source")
            if not src:
                continue
            ref = script.get(l["id"], {}).get("text", l["text"])
            syn = "".join(s.get("synth_text", "") for s in report.get(l["id"], {}).get("synthesis", [])) or ref
            items.append({"id": l["id"], "speaker": l["speaker"], "script": ref, "cue_text": l["text"], "synth_text": syn, "vo": ROOT / src,
                          "mix": out / "_work" / "mixseg" / f"{l['id']}.wav"})
    rows = [{"id": it["id"], "speaker": it["speaker"], "script": it["script"], "cue_text_equals_script": it["cue_text"].replace("\n", "") == it["script"],
             "vo_file": str(it["vo"].relative_to(ROOT)), "vo_version_v04": it["vo"].name.endswith("_v04.wav"), "vo": {}, "mix": {}} for it in items]
    for mname in vo_lib.ASR_MODELS:
        for src in ("vo", "mix"):
            paths = [it[src] for it in items if it[src].exists()]
            tx = vo_lib.transcribe(paths, mname)
            for it, row in zip(items, rows):
                p = str(it[src])
                if p in tx:
                    c = vo_lib.compare(it["script"], it["synth_text"], tx[p])
                    row[src][mname] = {"hyp": c["hyp"], "hyp_trad": c["hyp_trad"], "cer": c["cer"], "per": c["per"], "diffs": c["diffs"], "checks": c["checks"]}
        print(f"[transcripts] {mname} 完成")
    res = {"method": "faster-whisper（tools/vo_lib.py 的模型與設定）逐句轉寫；比對沿用 vo_lib.compare（轉繁體、去標點後與劇本逐字對齊，字不同的段落再比含聲調拼音）。"
                     f"來源「配音檔」＝audio/vo 的單句檔（v04）；「混音中該句」＝audio/{tl['act']}_mix.wav 中該句時段（前後各加 0.1 秒），含配樂與音效。",
           "rows": rows}
    (out / "transcripts.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    L = [f"# {tl['act']} 配音逐字稿與劇本差異", "", f"- 方法：{res['method']}", "- 只列轉寫結果與差異。", ""]
    for r in rows:
        L += [f"## {r['id']}｜{r['speaker']}", "", f"- 劇本 v03：{r['script']}", f"- cue 檔文字與劇本相同：{r['cue_text_equals_script']}", f"- 配音檔：`{r['vo_file']}`", "",
              "| 來源 | 模型 | 轉寫（轉繁體） | CER | PER | 差異（劇本→轉寫） |", "|---|---|---|---|---|---|"]
        for src, lab in (("vo", "配音檔"), ("mix", "混音中該句")):
            for mname, m in r[src].items():
                diffs = "；".join(f"{d['ref'] or '∅'}→{d['hyp'] or '∅'}（{d['kind']}）" for d in m["diffs"]) or "無"
                L.append(f"| {lab} | {mname} | {m['hyp_trad']} | {m['cer']} | {m['per']} | {diffs} |")
        L.append("")
    (out / "transcripts.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ====================================================================== INDEX.md
def fmt(x, nd=1):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def index(out: Path):
    from datetime import datetime, timezone
    a = load(out, "analysis.json") or {}
    tl = load(out, "timeline.json") or {}
    loud = load(out, "audio/loudness.json") or {}
    fl = load(out, "flash_playback.json") or {}
    fv = load(out, "flash_variants.json") or {}
    ss = load(out, "subtitle_sync.json") or {}
    du = load(out, "durations.json") or {}
    sa = load(out, "safety_data.json") or {}
    tr = load(out, "transcripts.json")
    cap = load(out, "capture/capture.json") or {}
    cflash = load(out, "capture/flash_report.json") or {}
    pr = load(out, "capture/probe_report.json")
    act = tl.get("act", "?")
    L = [f"# {act} 驗收包（{tl.get('title', '')}）", "",
         f"- 產生：tools/act_review_pack.mjs（{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}）；段落檔 `{tl.get('segmentFile')}`；本檔只列數字與檔案。",
         "- 聽感、實際投影、學校硬體：未驗證。", ""]
    L += ["## 檔案", "",
          "| 項目 | 檔案 |", "|---|---|",
          "| 關鍵影格（每個 cue 前／中／後，1920×1080） | capture/keyframes/、capture/contact_keyframes.png |",
          "| 每秒接觸表 | capture/contact_timeline_*.png、capture/frames/ |",
          "| 投影模擬 v2 | proj/16x9/、proj/contact_proj_16x9.png |",
          f"| 與 G4 同尺寸並排 | {'、'.join((a.get('compare_g4') or {}).get('sheets', [])) or '—'} |",
          f"| 播放錄製（30 格／秒＋混音） | {act}_playback.mp4 |",
          f"| 混音與響度 | audio/{act}_mix.wav、audio/loudness.json、audio/{act}_mix_plot.png |",
          "| 光敏 | flash_playback.json、flash_playback_plot.png、flash_variants.json、capture/flash_report.json |",
          "| 字幕與語音時間差 | subtitle_sync.json |",
          "| 逐字稿 | transcripts.md、transcripts.json |",
          "| 長度對照預算 | durations.json |",
          "| 安全量測 | safety_data.json、probe_dense.json、capture/probe.json、capture/probe_report.json |",
          "| 時間軸與排程 | timeline.json |", ""]
    L += ["## 長度", "",
          f"- 本段 cue 總長 {fmt(du.get('act_total_sec'))} 秒＋換景漸暗預捲 {fmt(du.get('act_preroll_total_sec'))} 秒；時長估算_v03.md 預錄合計 {fmt(du.get('act_budget_recorded_sec'))} 秒；差 {fmt(du.get('diff_vs_budget_sec'))} 秒；逐 cue 估計合計 {fmt(du.get('estimate_sum_sec'))} 秒。",
          f"- 播放錄製（含教師按鍵間隔假設）{fmt(tl.get('totalPlaybackSec'))} 秒。", "",
          "| cue | 種類 | 長度 | 預捲 | 估計 | 差 | 台詞秒 | 句數 |", "|---|---|---|---|---|---|---|---|"]
    for r in du.get("cues", []):
        L.append(f"| {r['cue']} | {r['kind']} | {fmt(r['duration_sec'])} | {fmt(r['preroll_sec'])} | {fmt(r['estimate_sec'])} | {fmt(r['diff_sec'])} | {fmt(r['vo_sec'], 2)} | {r['lines']} |")
    L += ["", "## 光敏（任一區域明暗或飽和紅色每秒變化 ≤ 3 次）", "",
          f"- 播放錄製 30 格／秒（16×9 區域＋全畫面，含換景預捲與停住格）：每秒最多 明暗 {fmt((fl.get('max_changes_per_sec') or {}).get('luma'))}、紅色 {fmt((fl.get('max_changes_per_sec') or {}).get('red'))}；超標 {len(fl.get('flagged', []))}；接近上限（2–3 次）{fl.get('near_limit_total', '—')}；分析 {fl.get('frames_analyzed', '—')} 格。"]
    for k, v in (fv.get("variants") or {}).items():
        L.append(f"- {k}：每秒最多 明暗 {v['max_changes_per_sec']['luma']}、紅色 {v['max_changes_per_sec']['red']}；超標 {len(v['flagged'])}；3 次 {v['near_limit_3_total']}。")
    # 通過條件（主線裁定 1，G5 修正第 1 輪起）：16×9 與 fine_32x18 的明暗、紅色每秒都 ≤ 3（不採面積豁免；64×36 不要求）
    def _pass(mc):
        return None if not mc else (mc.get("luma", 99) <= 3 and mc.get("red", 99) <= 3)
    p169 = _pass(fl.get("max_changes_per_sec"))
    fine = (fv.get("variants") or {}).get("fine_32x18") or {}
    pfine = _pass(fine.get("max_changes_per_sec"))
    word = lambda b: "—" if b is None else ("通過" if b else "不通過")
    L.append(f"- **通過判定**（主線裁定 1：16×9 與 fine_32x18 的明暗、紅色每秒都 ≤ 3）：16×9 {word(p169)}；fine_32x18 {word(pfine)}"
             + (f"（明暗 {fine['max_changes_per_sec']['luma']}、紅色 {fine['max_changes_per_sec']['red']}；超標格 {len(fine.get('flagged', []))}"
                + (f"，最早 {fine['flagged'][0].get('cue')} {fine['flagged'][0].get('cue_t')} 秒" if fine.get('flagged') else "") + "）" if fine else "") + "；整段 " + word(None if p169 is None or pfine is None else (p169 and pfine)) + "。")
    L.append(f"- capture.mjs 逐 cue（{cap.get('analysisFps', '—')} 格／秒）：{json.dumps({k: cflash.get(k) for k in ('ok', 'max_changes_per_sec')}, ensure_ascii=False) if cflash else '—'}")
    seams = fl.get("cue_seams", [])
    if seams:
        L.append(f"- cue 接縫全畫面亮度差最大 {fmt(max(abs(s['mean_luma_after'] - s['mean_luma_before']) for s in seams), 3)}；區域亮度差最大 {fmt(max(s['max_region_luma_delta'] for s in seams), 3)}。")
    L += ["", "## 聲音", "",
          f"- 整段：{fmt((loud.get('full_playback') or {}).get('I_LUFS'))} LUFS、真峰值 {fmt((loud.get('full_playback') or {}).get('TP_dBTP'))} dBTP、取樣峰值 {fmt(loud.get('sample_peak_dBFS'), 2)} dBFS、削波 {loud.get('clipped_samples', '—')} 個。",
          f"- 各句對白：配音檔響度差 {fmt(loud.get('line_vo_file_I_spread_LU'), 2)} LU、混音中響度差 {fmt(loud.get('line_mix_I_spread_LU'), 2)} LU。",
          f"- 瞬間響度最大 {fmt(loud.get('momentary_max_LUFS'))} LUFS；1 秒內最大上升 {fmt(loud.get('momentary_max_rise_within_1s_LU'))} LU；100 ms 最大上升 {fmt(loud.get('momentary_max_rise_per_100ms_LU'))} LU。",
          f"- 教師停格 3 秒後配樂 ≤ −35 LUFS：{sum(1 for h in loud.get('freeze_holds', []) if h.get('pass_le_-35'))}／{len(loud.get('freeze_holds', []))} 段通過。"]
    ms = loud.get("music_sfx_only") or {}
    if ms:
        g4r = ms.get("g4_reference") or {}
        at = lambda k: (f"（{ms[k]['cue']} {ms[k]['cue_t']} 秒）" if ms.get(k) else "")
        L.append(f"- 只有配樂與音效（不含配音）：瞬間響度最大 {fmt(ms.get('max_LUFS'))} LUFS{at('max_at')}；100 ms 最大上升 {fmt(ms.get('max_rise_per_100ms_LU'))} LU{at('max_rise_per_100ms_at')}；"
                 f"1 秒內最大上升 {fmt(ms.get('max_rise_within_1s_LU'))} LU；取樣峰值 {fmt(ms.get('sample_peak_dBFS'), 2)} dBFS{at('sample_peak_at')}、真峰值 {fmt(ms.get('true_peak_dBTP'))} dBTP"
                 f"（G4 基準：瞬間最大 {fmt(g4r.get('max_LUFS'))} LUFS、100 ms 上升 {fmt(g4r.get('max_rise_per_100ms_LU'))} LU；不高於 G4 最大值：{ms.get('within_g4_max_LUFS')}）。")
    L += ["",
          "| 台詞 | 說話者 | 配音檔 LUFS | 混音中 LUFS | 對白−背景 LU |", "|---|---|---|---|---|"]
    for l in loud.get("lines", []):
        L.append(f"| {l['id']} | {l['speaker']} | {fmt(l['vo_file_I_LUFS'])} | {fmt(l['mix_I_LUFS'])} | {fmt(l['vo_minus_background_LU'])} |")
    rows = ss.get("rows", [])
    sd = ss.get("silencedetect") or {}
    L += ["", "## 字幕與語音時間差（字幕頁起點 − 語音起點，範圍 −0.8～+0.1 秒）", "",
          f"- {sum(1 for r in rows if r['pass'])}／{len(rows)} 頁在範圍內；最大 {fmt(max((r['diff_s'] for r in rows), default=None), 3)} 秒、最小 {fmt(min((r['diff_s'] for r in rows), default=None), 3)} 秒。",
          f"- 語音起點偵測：ffmpeg silencedetect {sd.get('noise_dB', -45)} dB、最短靜音 {sd.get('min_silence_s', 0.1)} 秒"
          + ("（G5 修正第 1 輪起；G4 是 −45 dB、0.1 秒，抓不到句中短停頓）。" if sd else "（G4 方法）。")]
    L += ["", "## 逐字稿（v04 配音）", ""]
    if tr:
        rws = tr["rows"]
        for m in ("small", "large-v3-turbo"):
            vo0 = sum(1 for r in rws if (r["vo"].get(m) or {}).get("cer") == 0)
            mx0 = sum(1 for r in rws if (r["mix"].get(m) or {}).get("cer") == 0)
            L.append(f"- {m}：配音檔逐字正確 {vo0}／{len(rws)} 句、混音中 {mx0}／{len(rws)} 句。")
        L.append(f"- 配音檔都是 v04：{all(r.get('vo_version_v04') for r in rws)}；cue 文字與劇本相同：{sum(1 for r in rws if r['cue_text_equals_script'])}／{len(rws)}。")
    else:
        L.append("- 未產生（--skip-asr）。")
    L += ["", "## 安全量測", "",
          f"- 操偶線扣點：{'、'.join(sa.get('string_anchors_in_cues', [])) or '本段沒有操偶線'}（只限 wrist／elbow／knee：{sa.get('string_anchors_only_allowed')}）；有操偶線的角色：{'、'.join(sa.get('actors_with_strings', [])) or '無'}。",
          f"- 有操偶線的量測格 {sa.get('probe_frames_with_strings', 0)}；線到頭部框最短 {fmt(sa.get('string_path_min_dist_to_head_box_px'))} px（只算頭部框在畫面內的格；畫面外略過 {sa.get('string_head_offscreen_skipped', 0)} 條）；線經過兒童立牌外框 {sa.get('string_path_intersects_child_box_count', 0)} 格。",
          f"- 必要旁白：{json.dumps({k: {'cue＝劇本': v['cue_equals_script'], '劇本＝CLAUDE.md': v['script_equals_claude_md'], '說話者': v['speaker']} for k, v in (sa.get('required_narration') or {}).items()}, ensure_ascii=False) if sa.get('required_narration') else '本段沒有必要旁白'}。",
          f"- 台詞與劇本 v03 逐字不同：{len(sa.get('lines_differ_from_script_v03', []))} 句（共 {sa.get('lines_total', '—')} 句）。",
          f"- 字幕：每行最多 {sa.get('subtitle_max_chars_per_row', '—')} 字、每頁最多 {sa.get('subtitle_max_rows_per_page', '—')} 行。",
          f"- 隱私：app.js getUserMedia {sa.get('app_js_getUserMedia_count', '—')} 次、mediaDevices {sa.get('app_js_mediaDevices_count', '—')} 次；擷取時外部網路請求 {sa.get('capture_external_requests', '—')} 個、主控台錯誤 {sa.get('capture_console_errors', '—')} 則。"]
    if pr:
        L.append(f"- capture_probe.py 量測：{rel(out / 'capture/probe_report.json', out)}（操偶線 ΔL*、紙環是否在剪影內、兒童站位背景亮度）。")
    fm = a.get("frames_meta") or {}
    L += ["", "## 其他", "",
          f"- 換景漸暗預捲：{json.dumps({k: v for k, v in (fm.get('preroll') or {}).items() if v}, ensure_ascii=False)}；景：{'、'.join(sorted({s.get('set') for s in tl.get('schedule', [])}))}；景的建立／釋放 {json.dumps(fm.get('sets'), ensure_ascii=False)}。",
          f"- 逐格擷取時的頁面錯誤 {len(fm.get('errors') or [])} 則。"]
    (out / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[actpack.py] → {out / 'INDEX.md'}")


if __name__ == "__main__":
    cmd, out = sys.argv[1], Path(sys.argv[2]).resolve()
    {"analyze": analyze, "transcripts": transcripts, "index": index}[cmd](out)
