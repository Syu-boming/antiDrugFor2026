"""備援影片：混音、章節、封裝與檢查（由 tools/backup_video.mjs 呼叫）。

用法：
  /opt/anaconda3/bin/python3 tools/backup_video.py mux <工作資料夾> <輸出.mp4> <檢查報告.json> [--no-verify]
  /opt/anaconda3/bin/python3 tools/backup_video.py readme <影片資料夾> <檢查資料夾>
  /opt/anaconda3/bin/python3 tools/backup_video.py full <影片資料夾> <檢查資料夾>

mux：
  1. 混音：tools/g4_review_pack.py 的 mix()（與 act_review_pack.py 驗收包同一套引擎混音規則）。送進 mix() 之前，照引擎
     engine.ts scheduleAudio 的規則修正一件事：cue 的 audioId 和「目前正在播的配樂」相同時，引擎不會重新淡入（mixer.musicId 相同就跳過），
     mix() 卻會從頭重新起播；這裡把這種 audioId 拿掉（記在報告 music_semantics）。
  2. 章節：ffmpeg FFMETADATA，每個 cue 一章（起點＝老師按下一步的那一格，含換景漸暗預捲），標題「cue 標題（cue 編號）」。
  3. 封裝：無聲影片（H.264，ffmpeg 已編好）＋混音（32 位元浮點 WAV → AAC-LC）＋章節，+faststart。
  4. 檢查（--no-verify 略過）：ffprobe（編碼、解析度、格率、色彩標註、章節）；影格數與長度；聲畫對齊（每句配音檔與成品音軌
     在預定時間附近做互相關，時間差應為 0 ms 左右）；取樣格（擷取時存下的原始截圖）與成品同一格號的 PSNR，以及前後一格
     （確認沒有掉格、重複格或錯位）；成品音軌響度（EBU R128）。
readme：依 <檢查資料夾>/backup_*.json 寫 <影片資料夾>/README.txt（UTF-8 BOM，Windows 記事本可讀）。
full：把 backup_a0.mp4 … backup_a8.mp4 照順序接成 backup_full.mp4（九段原檔不動）。
  1. 畫面：concat 直接複製（不重新編碼，逐格和各段相同）；每段的接點用影格數／30 秒，不用容器長度。
  2. 聲音：各段解碼後接起來，重新編成 AAC 256 kbps（直接複製 AAC 會在每個接點多出編碼器前置樣本，聲音逐段延後）；
     各段從無聲開始，但 a0–a7 結尾的停格還有很小的配樂，接起來會突然斷掉，所以每段最後 FULL_FADE_SEC 秒淡出（a8 結尾本來就無聲）。
  3. 章節：各段的章節照起點平移，共 71 章；標題不變（含 cue 編號）。
  4. 檢查：逐格封包雜湊和九段依序相同；完整解碼 0 錯誤；每段起點那一格解碼後和該段第一格相同；每段聲音和原檔的時間差（互相關）
     與相似度；長度、章節數與標題。結果寫 <檢查資料夾>/backup_full.json，README.txt 會列出各段在完整版裡的時間。
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
FPS = 30
SR = 48000
ALIGN_TOL_DB = 1.0  # 逐格對齊：同格號 PSNR 不低於前後格最高值減這個量（G7 主線裁定：原本 0.05 dB 在靜止畫面誤判）
W, H = 1920, 1080
GENERIC_NOTE = "播完停格，等老師按下一步。"


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _np(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"{type(o).__name__} 不能寫成 JSON")


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1, default=_np)


def mmss(t):
    t = max(0.0, float(t))
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


# ====================================================================== 1. 混音（引擎配樂規則修正後交給 g4.mix）
def engine_music_semantics(tl):
    """照 engine.ts scheduleAudio：audioId 與 mixer.musicId（最近一次交叉淡入、還沒播完的配樂）相同時不重新淡入。
    回傳（修正後的時間軸副本, 拿掉的 audioId 清單）。一次播完的曲子（musicLoop false、music 事件 loop false）播完後 musicId 變回空。"""
    tl2 = json.loads(json.dumps(tl))
    audio = tl2["audio"]
    sched = {s["id"]: s for s in tl2["schedule"]}
    cur = None  # (id, 播完的全域秒數 或 inf)
    removed = []

    def alive(t):
        return cur if cur and t < cur[1] else None

    for c in tl2["cues"]:
        G = sched[c["id"]]["start"]
        now = alive(G)
        aid = c.get("audioId")
        if aid == "none":
            cur = None
        elif aid:
            if now and now[0] == aid:
                removed.append({"cue": c["id"], "audioId": aid, "reason": "同一首配樂已在播（引擎 mixer.musicId 相同，不重新淡入）"})
                c["audioId"] = None
            else:
                dur = (audio.get(aid) or {}).get("duration") or 0
                cur = (aid, float("inf") if c.get("musicLoop", True) else G + dur)
        for m in c.get("music", []):
            if m["id"] == "none":
                cur = None
            else:
                dur = (audio.get(m["id"]) or {}).get("duration") or 0
                cur = (m["id"], float("inf") if m.get("loop", True) else G + m["at"] + max(0.0, dur - m.get("offset", 0)))
    return tl2, removed


def write_chapters(path, tl, title):
    def esc(s):
        return re.sub(r"([=;#\\\n])", r"\\\1", s)
    total_ms = int(round(tl["totalFrames"] * 1000 / FPS))
    sch = tl["schedule"]
    L = [";FFMETADATA1", f"title={esc(title)}", "artist=許博明老師製作", f"comment={esc('反毒剪紙劇場 備援影片（tools/backup_video.mjs 逐格離線輸出）')}", ""]
    chapters = []
    for i, s in enumerate(sch):
        st = int(round(s["fPre0"] * 1000 / FPS))
        en = int(round(sch[i + 1]["fPre0"] * 1000 / FPS)) if i + 1 < len(sch) else total_ms
        name = f"{s['title']}（{s['id']}）"
        chapters.append({"id": s["id"], "title": name, "start_ms": st, "end_ms": en})
        L += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={st}", f"END={en}", f"title={esc(name)}", ""]
    Path(path).write_text("\n".join(L), encoding="utf-8")
    return chapters


# ====================================================================== 2. 檢查
def ffprobe(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_streams", "-show_format", "-show_chapters", "-of", "json", str(mp4)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def decode_audio(mp4):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2)


def xcorr_lag(sig, ref, max_lag):
    """sig 長度 = len(ref) + 2*max_lag；回傳（最佳延遲樣本數（正＝成品較晚）, 正規化相關係數）"""
    n = len(ref)
    L = 1 << int(np.ceil(np.log2(len(sig) + n)))
    S = np.fft.rfft(sig, L)
    R = np.fft.rfft(ref[::-1], L)
    full = np.fft.irfft(S * R, L)[n - 1:n - 1 + 2 * max_lag + 1]  # full[k] = sum sig[k+j] ref[j]
    c2 = np.concatenate([[0.0], np.cumsum(sig.astype(np.float64) ** 2)])
    energy = np.sqrt(np.maximum(c2[n:n + 2 * max_lag + 1] - c2[:2 * max_lag + 1], 1e-12) * float((ref.astype(np.float64) ** 2).sum()))
    norm = full / np.maximum(energy, 1e-12)
    k = int(np.argmax(norm))
    return k - max_lag, float(norm[k])


def av_sync(mp4_audio, spans, tl):
    import g4_review_pack as g4
    mono = mp4_audio.mean(axis=1)
    rows = []
    max_lag = int(0.2 * SR)
    for sp in spans:
        src = ROOT / tl["audio"][sp["audioId"]]["source"]
        vo = g4.load_wav(src)[:, 0]
        nz = np.flatnonzero(np.abs(vo) > 0.02)
        if not len(nz):
            continue
        a = max(0, nz[0] - int(0.05 * SR))  # 從語音起點前 50 ms 起取 1 秒當樣板（避開句首長靜音）
        ref = vo[a:a + SR]
        s0 = int(round(sp["start"] * SR)) + a
        lo, hi = s0 - max_lag, s0 + len(ref) + max_lag
        if lo < 0 or hi > len(mono):
            continue
        lag, corr = xcorr_lag(mono[lo:hi], ref, max_lag)
        rows.append({"line": sp["id"], "cue": sp["cue"], "expected_sec": round(sp["start"] + a / SR, 3), "lag_ms": round(lag * 1000 / SR, 2), "corr": round(corr, 3)})
    lags = [abs(r["lag_ms"]) for r in rows]
    return {"method": "成品 AAC 音軌（解碼成 48 kHz 單聲道）與該句配音檔（從語音起點前 50 ms 取 1 秒）在預定時間 ±200 ms 內做正規化互相關；lag_ms＝成品比預定晚多少毫秒",
            "lines": len(rows), "max_abs_lag_ms": round(max(lags), 2) if lags else None, "median_abs_lag_ms": round(float(np.median(lags)), 2) if lags else None,
            "min_corr": round(min(r["corr"] for r in rows), 3) if rows else None,
            "pass_le_1_frame": bool(rows) and max(lags) <= 1000 / FPS, "rows": rows}


def frame_check(mp4, work, samples):
    from PIL import Image
    if not samples:
        return {"samples": 0}
    want = sorted({k for s in samples for k in (s - 1, s, s + 1) if k >= 0})
    expr = "+".join(f"eq(n\\,{k})" for k in want)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"select='{expr}',scale=in_color_matrix=bt709:in_range=tv,format=rgb24", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    fr = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(fr) // (W * H * 3)
    frames = {want[i]: fr[i * W * H * 3:(i + 1) * W * H * 3].reshape(H, W, 3) for i in range(min(n, len(want)))}

    def psnr(a, b):
        mse = float(np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2))
        return 99.0 if mse < 1e-9 else round(10 * np.log10(255.0 ** 2 / mse), 2)
    rows = []
    for s in samples:
        p = next((q for q in (work / "samples").glob(f"{s:06d}.*")), None)
        if p is None or s not in frames:
            continue
        src = np.asarray(Image.open(p).convert("RGB"))
        row = {"frame": s, "time_sec": round(s / FPS, 3), "psnr_same_dB": psnr(src, frames[s])}
        for d, key in ((-1, "psnr_prev_dB"), (1, "psnr_next_dB")):
            if s + d in frames:
                row[key] = psnr(src, frames[s + d])
        row["aligned"] = row["psnr_same_dB"] >= max(row.get("psnr_prev_dB", 0), row.get("psnr_next_dB", 0)) - ALIGN_TOL_DB
        rows.append(row)
    ps = [r["psnr_same_dB"] for r in rows]
    return {"method": "擷取時存下的原始截圖 vs 成品解碼後同一格號（與前後各一格）的 PSNR；同格號最高＝沒有錯位（靜止畫面前後格幾乎相同、H.264 雜訊會讓鄰格高出零點幾 dB，差距在 ALIGN_TOL_DB 內視為對齊；真的錯一格時有動作的地方會差數 dB）",
            "samples": len(rows), "min_psnr_dB": min(ps) if ps else None, "mean_psnr_dB": round(float(np.mean(ps)), 2) if ps else None,
            "all_aligned": all(r["aligned"] for r in rows) if rows else None, "rows": rows}


# ====================================================================== mux
def mux(work: Path, mp4: Path, report: Path, verify=True):
    import g4_review_pack as g4
    t_start = time.time()
    tl = json.loads((work / "timeline.json").read_text(encoding="utf-8"))
    act = tl["act"]
    tl2, removed = engine_music_semantics(tl)
    print(f"[backup.py] {act} 混音（g4_review_pack.mix；引擎配樂規則修正 {len(removed)} 處）")
    mixed, stems, spans, elog, ts, lvl, dk = g4.mix(work, tl2)
    n_expect = tl["totalFrames"] * SR // FPS
    if len(mixed) < n_expect:
        mixed = np.concatenate([mixed, np.zeros((n_expect - len(mixed), 2), np.float32)])
    mixed = mixed[:n_expect]
    wav = work / f"mix_{act}.wav"
    g4.write_wav(wav, mixed, bits=32)
    peak = float(np.abs(mixed).max()) if len(mixed) else 0.0
    meta = work / "chapters.txt"
    title = f"反毒剪紙劇場 備援影片 {act} {tl['title']}（許博明老師製作）"
    chapters = write_chapters(meta, tl, title)
    mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = mp4.with_suffix(".tmp.mp4")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(work / "video_silent.mp4"), "-i", str(wav), "-i", str(meta),
                    "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "2", "-map_chapters", "2",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", tl["capture"]["encoder"]["abr"], "-ar", str(SR), "-ac", "2",
                    "-metadata:s:a:0", "language=chi", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(mp4)
    mux_sec = time.time() - t_start
    res = {
        "file": rel(mp4), "act": act, "title": tl["title"], "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "size_MB": round(mp4.stat().st_size / 1e6, 1), "frames_expected": tl["totalFrames"], "duration_expected_sec": round(tl["totalFrames"] / FPS, 3),
        "holds": tl["holds"], "previous_cue": tl.get("previousCue"),
        "chapters": [{**c, "start": mmss(c["start_ms"] / 1000)} for c in chapters],
        "cues": [{"id": s["id"], "kind": s["kind"], "title": s["title"], "chapter_start_sec": round(s["chapterStart"], 3), "cue_start_sec": round(s["start"], 3),
                  "duration_sec": round(s["duration"], 3), "pause_from_sec": round(s["start"] + s["duration"], 3), "hold_sec": s["hold"], "preroll_sec": s["preroll"],
                  "teacherNote": next((c.get("teacherNote", "") for c in tl["cues"] if c["id"] == s["id"]), ""),
                  "quiz": next((c.get("quiz") for c in tl["cues"] if c["id"] == s["id"]), None)} for s in tl["schedule"]],
        "mix": {"source": "tools/g4_review_pack.py mix()（act_review_pack.py 同一套）＋引擎配樂規則修正", "music_semantics": removed,
                "sample_peak_dBFS": round(20 * np.log10(max(peak, 1e-9)), 2), "clipped_samples": int((np.abs(mixed) >= 1.0).sum()),
                "missing_audio": [e for e in elog if "missing" in e]},
        "capture": {k: v for k, v in tl["capture"].items() if k != "external_requests"},
        "capture_external_requests": len(tl["capture"].get("external_requests", [])),
        "timing": {"img": tl["capture"]["img"], "load_sec": tl["capture"].get("load_sec"), "capture_ms_per_frame": tl["capture"]["capture_ms_per_frame"], "capture_sec": tl["capture"]["capture_sec"],
                   "mux_sec": round(mux_sec, 1), "mux_sec_per_video_sec": round(mux_sec / max(1.0, tl["totalFrames"] / FPS), 3)},
    }
    if verify:
        print(f"[backup.py] {act} 檢查（ffprobe、聲畫對齊、逐格比對、響度）")
        pr = ffprobe(mp4)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        a = next(s for s in pr["streams"] if s["codec_type"] == "audio")
        aud = decode_audio(mp4)
        sync = av_sync(aud, spans, tl)
        fc = frame_check(mp4, work, tl.get("samples", []))
        loud = g4.ebur(aud)
        ch = pr.get("chapters", [])
        res["verify"] = {
            "video": {k: v.get(k) for k in ("codec_name", "profile", "level", "width", "height", "pix_fmt", "r_frame_rate", "avg_frame_rate", "color_space", "color_primaries",
                                             "color_transfer", "color_range", "bit_rate", "nb_read_packets", "duration")},
            "audio": {k: a.get(k) for k in ("codec_name", "profile", "sample_rate", "channels", "bit_rate", "duration")},
            "format": {k: pr["format"].get(k) for k in ("format_name", "duration", "size", "bit_rate")},
            "frames_ok": int(v.get("nb_read_packets", -1)) == tl["totalFrames"],
            "duration_diff_av_sec": round(abs(float(v.get("duration", 0)) - float(a.get("duration", 0))), 4),
            "chapters_in_file": len(ch), "chapters_ok": len(ch) == len(tl["schedule"]) and all(c.get("tags", {}).get("title") == x["title"] for c, x in zip(ch, chapters)),
            "chapter_titles_in_file": [c.get("tags", {}).get("title") for c in ch],
            "av_sync": sync, "frame_check": fc,
            "loudness_final": loud, "decoded_audio_sec": round(len(aud) / SR, 3),
        }
        vv = res["verify"]
        vv["all_ok"] = bool(vv["frames_ok"] and vv["chapters_ok"] and vv["duration_diff_av_sec"] <= 1 / FPS + 0.03 and (sync["lines"] == 0 or sync["pass_le_1_frame"])
                            and fc.get("all_aligned") is not False and (fc.get("min_psnr_dB") or 99) >= 35 and v.get("width") == W and v.get("height") == H)
        print(f"[backup.py] {act}：影格 {v.get('nb_read_packets')}／{tl['totalFrames']}、章節 {len(ch)}、聲畫時間差最大 {sync['max_abs_lag_ms']} ms（{sync['lines']} 句）、"
              f"逐格 PSNR 最低 {fc.get('min_psnr_dB')} dB、對齊 {fc.get('all_aligned')}、響度 {loud.get('I_LUFS')} LUFS → 全部通過 {vv['all_ok']}")
        res["timing"]["verify_sec"] = round(time.time() - t_start - mux_sec, 1)
    res["timing"]["post_sec_per_video_sec"] = round((time.time() - t_start) / max(1.0, tl["totalFrames"] / FPS), 3)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(jdump(res), encoding="utf-8")


# ====================================================================== 完整版（九段接成一檔）
FULL_NAME = "backup_full.mp4"
FULL_FADE_SEC = 0.5


def show_segments():
    try:
        return [Path(s).stem for s in json.loads((ROOT / "app/cues/show/index.json").read_text(encoding="utf-8"))["segments"]]
    except OSError:
        return [f"a{i}" for i in range(9)]


def packet_md5(mp4):
    """每個畫面封包的 MD5（不解碼）"""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:v:0", "-c", "copy", "-f", "framemd5", "-"], capture_output=True, text=True, check=True)
    return [ln.rsplit(",", 1)[1].strip() for ln in r.stdout.splitlines() if ln and not ln.startswith("#")]


def gray_frame_at(mp4, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", str(mp4), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.uint8)[:W * H].astype(np.float32)


def full(out: Path, check: Path):
    t_start = time.time()
    segs = show_segments()
    files = [out / f"backup_{a}.mp4" for a in segs]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        sys.exit(f"[backup.py] 完整版需要九段都在，缺 {'、'.join(missing)}")
    parts = []
    for a, f in zip(segs, files):
        pr = ffprobe(f)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        n = int(v["nb_read_packets"])
        rep = check / f"backup_{a}.json"
        title = json.loads(rep.read_text(encoding="utf-8"))["title"] if rep.exists() else ""
        parts.append({"act": a, "file": f, "title": title, "frames": n, "chapters": pr.get("chapters", []),
                      "level": v.get("level"), "profile": v.get("profile"), "size": (v.get("width"), v.get("height"))})
    if len({(p["level"], p["profile"], p["size"]) for p in parts}) != 1:
        sys.exit("[backup.py] 九段的畫面編碼設定不同，不能直接複製接起來")
    off = 0
    for p in parts:
        p["offset_frames"] = off
        off += p["frames"]
    total_frames = off
    work = check / "_work_full"
    work.mkdir(parents=True, exist_ok=True)

    def q(s):
        return "'" + str(s).replace("'", "'\\''") + "'"
    (work / "list.ffconcat").write_text("ffconcat version 1.0\n" + "".join(f"file {q(p['file'])}\nduration {p['frames'] / FPS:.6f}\n" for p in parts), encoding="utf-8")

    def esc(s):
        return re.sub(r"([=;#\\\n])", r"\\\1", s)
    L = [";FFMETADATA1", f"title={esc('反毒剪紙劇場 備援影片 完整版 a0–a8（許博明老師製作）')}", "artist=許博明老師製作",
         f"comment={esc('反毒剪紙劇場 備援影片（tools/backup_video.mjs 逐格離線輸出的九段依序接成一檔）')}", ""]
    chapters = []
    for p in parts:
        base = p["offset_frames"] * 1000 / FPS
        for i, c in enumerate(p["chapters"]):
            st = int(round(base + float(c["start_time"]) * 1000))
            en = int(round(base + p["frames"] * 1000 / FPS)) if i + 1 == len(p["chapters"]) else int(round(base + float(p["chapters"][i + 1]["start_time"]) * 1000))
            name = c.get("tags", {}).get("title", "")
            chapters.append({"act": p["act"], "title": name, "start_ms": st, "end_ms": en})
            L += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={st}", f"END={en}", f"title={esc(name)}", ""]
    meta = work / "chapters.txt"
    meta.write_text("\n".join(L), encoding="utf-8")

    fades = []
    for i, p in enumerate(parts):
        d = p["frames"] / FPS
        fades.append(f"[{i + 1}:a:0]" + (f"afade=t=out:st={d - FULL_FADE_SEC:.6f}:d={FULL_FADE_SEC}" if i + 1 < len(parts) else "anull") + f"[a{i}]")
    graph = ";".join(fades) + ";" + "".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[aout]"
    mp4 = out / FULL_NAME
    tmp = mp4.with_suffix(".tmp.mp4")
    # auto_convert 0：不讓 concat 在每個關鍵格前面再塞一次 SPS/PPS（九段編碼設定相同，原封包直接接就能解）
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-auto_convert", "0", "-i", str(work / "list.ffconcat")]
    for p in parts:
        cmd += ["-i", str(p["file"])]
    cmd += ["-i", str(meta), "-filter_complex", graph, "-map", "0:v:0", "-map", "[aout]", "-map_metadata", str(len(parts) + 1), "-map_chapters", str(len(parts) + 1),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-ac", "2", "-metadata:s:a:0", "language=chi", "-movflags", "+faststart", str(tmp)]
    print(f"[backup.py] 完整版：接 {len(parts)} 段、{total_frames} 格（{mmss(total_frames / FPS)}）")
    subprocess.run(cmd, check=True)
    tmp.replace(mp4)
    mux_sec = time.time() - t_start

    print("[backup.py] 完整版檢查（逐格封包雜湊、完整解碼、接點畫面、聲音對齊）")
    pr = ffprobe(mp4)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next(s for s in pr["streams"] if s["codec_type"] == "audio")
    src_md5 = [h for p in parts for h in packet_md5(p["file"])]
    out_md5 = packet_md5(mp4)
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:v:0", "-f", "null", "-"], capture_output=True, text=True)
    joins = []
    for p in parts:
        t_full = p["offset_frames"] / FPS
        x, y = gray_frame_at(p["file"], 0.0), gray_frame_at(mp4, max(0.0, t_full - 0.002))  # 往前 2 ms：避免秒數進位跳到下一格
        joins.append({"act": p["act"], "full_start": mmss(t_full), "full_start_sec": round(t_full, 3), "first_frame_mean_abs_diff": round(float(np.abs(x - y).mean()), 3) if len(x) == len(y) else None})
    aud = decode_audio(mp4)
    asum = []
    for i, p in enumerate(parts):
        src = decode_audio(p["file"]).mean(axis=1)
        s0 = p["offset_frames"] * SR // FPS
        body = len(src) - (int(FULL_FADE_SEC * SR) if i + 1 < len(parts) else 0)
        seg = aud[s0:s0 + len(src)].mean(axis=1)
        e = np.convolve(src[:body] ** 2, np.ones(SR) / SR, mode="valid")
        c = int(np.argmax(e)) if len(e) else 0
        ref = src[c:c + SR]
        ml = SR // 20
        lag, corr = xcorr_lag(aud[max(0, s0 + c - ml):s0 + c + SR + ml].mean(axis=1), ref, ml) if s0 + c - ml >= 0 else xcorr_lag(np.concatenate([np.zeros(ml - (s0 + c)), aud[:s0 + c + SR + ml].mean(axis=1)]), ref, ml)
        n = min(body, len(seg))
        err = seg[:n] - src[:n]
        snr = 10 * np.log10(max(float((src[:n] ** 2).sum()), 1e-12) / max(float((err ** 2).sum()), 1e-12))
        asum.append({"act": p["act"], "lag_samples": lag, "lag_ms": round(lag * 1000 / SR, 2), "corr": round(corr, 4), "snr_vs_source_dB": round(snr, 1),
                     "window_sec": round(c / SR, 2)})
    ch = pr.get("chapters", [])
    res = {
        "file": rel(mp4), "generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "size_MB": round(mp4.stat().st_size / 1e6, 1),
        "segments": [{"act": p["act"], "title": p["title"], "file": p["file"].name, "frames": p["frames"], "full_start_sec": round(p["offset_frames"] / FPS, 3),
                      "full_start": mmss(p["offset_frames"] / FPS), "chapters": len(p["chapters"])} for p in parts],
        "frames_expected": total_frames, "duration_expected_sec": round(total_frames / FPS, 3), "fade_out_sec_at_joins": FULL_FADE_SEC,
        "chapters": [{**c, "start": mmss(c["start_ms"] / 1000)} for c in chapters],
        "verify": {
            "video": {k: v.get(k) for k in ("codec_name", "profile", "level", "width", "height", "pix_fmt", "r_frame_rate", "avg_frame_rate", "color_space", "color_primaries", "color_transfer", "nb_read_packets", "duration")},
            "audio": {k: a.get(k) for k in ("codec_name", "profile", "sample_rate", "channels", "bit_rate", "duration")},
            "frames_ok": int(v.get("nb_read_packets", -1)) == total_frames,
            "packets_identical_to_segments": out_md5 == src_md5, "packets_compared": len(src_md5),
            "decode_errors": len([ln for ln in dec.stderr.splitlines() if ln.strip()]),
            "join_first_frames": joins, "joins_ok": all(j["first_frame_mean_abs_diff"] == 0.0 for j in joins),
            "duration_diff_av_sec": round(abs(float(v.get("duration", 0)) - float(a.get("duration", 0))), 4),
            "decoded_audio_sec": round(len(aud) / SR, 3),
            "audio_vs_segments": asum, "audio_ok": all(x["lag_samples"] == 0 and x["corr"] >= 0.99 for x in asum),
            "chapters_in_file": len(ch), "chapters_ok": len(ch) == len(chapters) and all(c.get("tags", {}).get("title") == x["title"] for c, x in zip(ch, chapters)),
        },
        "timing": {"mux_sec": round(mux_sec, 1), "verify_sec": round(time.time() - t_start - mux_sec, 1)},
    }
    vv = res["verify"]
    vv["all_ok"] = bool(vv["frames_ok"] and vv["packets_identical_to_segments"] and vv["decode_errors"] == 0 and vv["joins_ok"] and vv["audio_ok"]
                        and vv["chapters_ok"] and vv["duration_diff_av_sec"] <= 1 / FPS + 0.03)
    (check / "backup_full.json").write_text(jdump(res), encoding="utf-8")
    for f in work.iterdir():
        f.unlink()
    work.rmdir()
    print(f"[backup.py] 完整版：影格 {v.get('nb_read_packets')}／{total_frames}、封包與九段相同 {vv['packets_identical_to_segments']}、解碼錯誤 {vv['decode_errors']}、"
          f"接點 {vv['joins_ok']}、聲音時間差最大 {max(abs(x['lag_ms']) for x in asum)} ms、章節 {len(ch)} → 全部通過 {vv['all_ok']}（{res['size_MB']} MB）")
    if not vv["all_ok"]:
        sys.exit(1)


# ====================================================================== README.txt
# 交付資料夾裡老師拿得到的文件（README 只指向這些，不寫開發文件）
TEACHER_PDF = "teacher_pdf\\"
# 要老師說話的停格 → 教師講稿.pdf 第五節的講法（和 teacher/src/script_doc.mjs 第五節同一組編號）
TALK = [
    (r"今天有八題", "規則說明＋全班試做一次捧燈手（約 75 秒）", "5.1"),
    (r"^找找看 ?1", "找找看 1（約 30 秒，不計獎）", "5.2"),
    (r"^找找看 ?2", "找找看 2（約 30 秒，不計獎）", "5.3"),
    (r"^找找看 ?3", "找找看 3（約 30 秒，不計獎）", "5.4"),
    (r"^練習", "全班練習拒絕句與口訣動作（約 90 秒，全場只練這一次）", "5.5"),
    (r"帶全場說口訣", "帶全場說口訣、做動作一次（約 30 秒）", "5.8"),
]


def main_lamp_info():
    """高潮主燈（全場一起捧燈手）的時間：teacher/data/check_report.json 的 mainLamp（tools/teacher_docs.mjs 依時間軸算的）。"""
    try:
        m = json.loads((ROOT / "teacher/data/check_report.json").read_text(encoding="utf-8")).get("mainLamp")
        return m if m and m.get("id") else None
    except (OSError, ValueError):
        return None


def pause_action(c, main=None):
    """老師在這個 cue 播完後要不要按暫停、要做什麼（回傳多行；空串列＝停 2 秒後影片自己往下播）。
    依 cue 種類與 teacherNote 關鍵字判斷，文字改寫成指向交付資料夾 teacher_pdf 的文件（不引用開發文件）。"""
    note = re.sub(r"`", "", (c.get("teacherNote") or "").replace("\n", " ")).strip()
    short = lambda s, n=46: s if len(s) <= n else s[:n] + "…"
    k = c["kind"]
    q = c.get("quiz") or {}
    zone = (re.search(r"([A-D]) 區", note) or [None, "?"])[1]
    if k == "quiz":
        if not q:
            return [f"按暫停：{short(note)}"]
        return [f"按暫停（題卡只停 3 秒）：說「想一想……3、2、1，一起比！」看 {zone} 區；全班比完再按播放。正解 {q.get('answer', '?')}"]
    if k == "reveal":
        if not q:
            return [f"按暫停：{short(note)}"]
        ans, n, qid = q.get("answer", "?"), q.get("number", "?"), q.get("qid", "")
        call = "最後一盞" if "最後一盞" in note else "大家一起"
        return [f"按暫停：正解 {ans}。回饋照 {TEACHER_PDF}題卡_教師版.pdf 第 {n} 題（或 教師講稿.pdf 第六節 {qid}）；",
                f"從 {zone} 區比 {ans} 的同學中點一位說理由，協助教師記錄區、排、座位；說「{call}，捧燈手——」後按播放"]
    if k == "lamp":
        return ["按暫停：燈亮後做安靜手勢，等全場安靜再按播放"]
    if k == "title" and c["cue_start_sec"] < 0.5:
        return ["開頭先暫停在署名卡；學生坐定後按播放"]
    if k == "title":
        return ["影片結束：停在署名卡（閉幕曲自然淡出）；接著教師結語（教師講稿.pdf 5.9）"]
    if main and c["id"] == main["id"]:
        t_call = c["cue_start_sec"] + float(main.get("callAt0", 0))
        t_lamp = c["cue_start_sec"] + float(main.get("at0", 0))
        return [f"不用暫停，全場一起捧燈手：約 {mmss(t_call)}（八盞燈都亮、鏡頭往後拉時）帶大家說",
                f"「最後的主燈，全場一起，捧燈手——」，主燈約 {mmss(t_lamp)} 亮起；燈亮後做安靜手勢（教師講稿.pdf 5.6）"]
    if not main and re.search(r"主燈", c.get("title") or ""):
        return ["不用暫停，全場一起捧燈手：看到八盞燈都亮、鏡頭往後拉時，帶大家說「最後的主燈，全場一起，捧燈手——」（教師講稿.pdf 5.6）"]
    for pat, label, sec in TALK:
        if re.search(pat, note):
            return [f"按暫停：{label}，講法見 {TEACHER_PDF}教師講稿.pdf {sec}"]
    return []


def readme(out: Path, check: Path):
    reps = {}
    for p in sorted(check.glob("backup_a*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        reps[r["act"]] = r
    try:
        show_idx = json.loads((ROOT / "app/cues/show/index.json").read_text(encoding="utf-8"))
        segs = [Path(s).stem for s in show_idx["segments"]]
    except OSError:
        segs = [f"a{i}" for i in range(9)]
    plan = json.loads((check / "plan.json").read_text(encoding="utf-8")) if (check / "plan.json").exists() else None
    titles = {r["act"]: r["title"] for r in (plan or {}).get("rows", [])}
    titles.update({a: r["title"] for a, r in reps.items()})
    main = main_lamp_info()
    full = json.loads((check / "backup_full.json").read_text(encoding="utf-8")) if (check / "backup_full.json").exists() else None
    full_ok = bool(full and (out / FULL_NAME).exists() and full["verify"].get("all_ok")
                   and [s["act"] for s in full["segments"]] == segs and all(a in reps and s["frames"] == reps[a]["frames_expected"] for a, s in zip(segs, full["segments"])))
    full_at = {s["act"]: s["full_start_sec"] for s in full["segments"]} if full_ok else {}
    L = ["反毒剪紙劇場｜備援影片使用說明（許博明老師製作）", "",
         f"本檔由 tools/backup_video.mjs 自動產生（{datetime.now().strftime('%Y-%m-%d %H:%M')}）。", "",
         "一、什麼時候用", "",
         "  ・演出包（AntidrugTheater.exe 或瀏覽器版）打不開、畫面黑掉、顯示卡中斷後重建失敗時，改用這組影片繼續上課。",
         "  ・影片是同一套劇場程式逐格輸出的，劇情、配音、字幕、題卡都和現場版一樣，但沒有互動：",
         "    答題、說明、發獎都要老師自己按暫停。每個段落播完會停 2 秒，八題的出題畫面停 3 秒，就在這時候按暫停。",
         f"  ・八題的正解、指定區與回饋：{TEACHER_PDF}題卡_教師版.pdf（第 n 題一頁）；規則、找找看、練習的講法：{TEACHER_PDF}教師講稿.pdf 第五節。",
         "    兩份都在交付資料夾的 teacher_pdf 裡，備援時請放在手邊。", "",
         "二、檔案（照順序播放：a0 → a1 → … → a8）", ""]
    for a in segs:
        r = reps.get(a)
        if r:
            L.append(f"  backup_{a}.mp4　{titles.get(a, '')}　長度 {mmss(r['duration_expected_sec'])}　章節 {len(r['chapters'])} 個　{r['size_MB']} MB")
        else:
            L.append(f"  backup_{a}.mp4　{titles.get(a, '')}　（尚未產生）")
    tot = sum(r["duration_expected_sec"] for r in reps.values())
    L += ["", f"  已產生 {len(reps)}／{len(segs)} 段，合計 {mmss(tot)}。"]
    if full_ok:
        L += ["", f"  {FULL_NAME}　完整版（上面九段照順序接成一檔，不用換檔）　長度 {mmss(full['duration_expected_sec'])}　章節 {len(full['chapters'])} 個　{full['size_MB']} MB",
              "    畫面和九段逐格相同；只在每段接點前的停格把很小的配樂淡出 0.5 秒，避免聲音突然斷掉。九段原檔都還在，兩種播法任選一種。"]
    elif (out / FULL_NAME).exists():
        L += ["", f"  ※ {FULL_NAME} 和目前的九段不一致（或沒有通過檢查），請不要用，改播九段；維護者請重接（第六節）。"]
    L += ["",
          "三、怎麼播放（Windows 內建播放器）", "",
          "  1. 整個資料夾用隨身碟複製到筆電本機硬碟再播放，不要直接從隨身碟或網路磁碟播。",
          "  2. 接好投影機，Win＋P 選「同步顯示」（影片只有一個畫面，同步最簡單）。",
          "  3. 在 backup_a0.mp4 上按右鍵 →「開啟檔案」→ 選「媒體播放器」（Windows 11）或「電影與電視」（Windows 10）。",
          "  4. 全螢幕：按播放器右下角的全螢幕鈕（多數版本也可以按 F11 或在畫面上按兩下）；離開全螢幕按 Esc。",
          "  5. 暫停／繼續：按筆電的空白鍵，或用滑鼠按播放器的暫停鈕。",
          "     羅技簡報筆的翻頁鍵在影片播放器裡不一定能暫停，備援時請改用筆電空白鍵。",
          "  6. 一段播完，開下一個檔案（a0 → a1 → … → a8）。最後一段停在「許博明老師製作」署名卡。",
          *([f"     或改播 {FULL_NAME}：一個檔案從開場播到片尾署名卡，不用換檔；暫停方法相同，時間看第四節表格的「完整版停格」那一欄。"] if full_ok else []),
          "  7. 跳到某個地方：檔案裡有每個 cue 一章的章節標記，但 Windows 內建播放器不一定顯示章節；",
          "     請照下面「哪裡要暫停」表格的時間拖曳進度列。",
          "  ※ 以上播放器操作還沒有在學校筆電實際試過（未驗證）。請課前先開一次 backup_a0.mp4，確認有畫面、有聲音、",
          "    空白鍵能暫停、能全螢幕。", "",
          "四、哪裡要暫停（時間＝影片內時間；「停格」是這段播完、畫面停住的時間"
          + (f"；「完整版停格」＝播 {FULL_NAME} 時要按暫停的時間，「（不停）」＝自動接下去；"
             f"要在完整版裡跳到某個 cue，用該段標題的「完整版從…開始」加上「開始」欄）" if full_ok else "）"), ""]
    for a in segs:
        r = reps.get(a)
        if not r:
            continue
        fa = full_at.get(a)
        L += [f"  【{a}】{r['title']}（{mmss(r['duration_expected_sec'])}" + (f"；完整版從 {mmss(fa)} 開始）" if fa is not None else "）"), "",
              "    " + ("完整版停格　" if fa is not None else "") + "開始　　停格　　cue　　　　內容／老師要做的事"]
        for c in r["cues"]:
            acts = pause_action(c, main)
            hold = f"{mmss(c['pause_from_sec'])}" if c["hold_sec"] > 0 else "（自動接下一段）"
            fcol = ((f"{mmss(fa + c['pause_from_sec'])}　　" if c["hold_sec"] > 0 else "（不停）　　") if fa is not None else "")
            L.append(f"    {fcol}{mmss(c['chapter_start_sec'])}　{hold}　{c['id']}　{c['title']}")
            for i, a_ in enumerate(acts):
                L.append(f"    {'　　　　　　' if fa is not None else ''}　　　　　　　　　　　　　{'→ ' if i == 0 else '　 '}{a_}")
        L.append("")
    L += ["五、畫質與聲音", "",
          "  ・1920×1080、每秒 30 格、H.264 高畫質（CRF 16）、AAC 立體聲 256 kbps。",
          "  ・影片壓縮可能讓紙紋與漸層出現色帶、顏色略偏；正式使用前請許老師目視確認。",
          "  ・聲音是用和演出包同一套混音規則離線混成；每段影片從無聲開始，上一段的配樂不會延續過來。",
          "  ・音量：先在播放器把音量開到 100%，再用投影機或喇叭調整，和演出包現場版大致相同。", "",
          "六、重新產生（給 Claude 或維護者；專案根目錄）", "",
          "  cd app && npm run build && cd ..",
          "  caffeinate -i node tools/backup_video.mjs --acts all --out 交付/backup_video",
          "  node tools/backup_video.mjs --acts all --plan        （只看每段格數與預估時間）",
          f"  node tools/backup_video.mjs --full-only              （只把現有九段重接成 {FULL_NAME}，再重寫本檔；九段都在時，產生影片後也會自動重接）",
          "  檢查報告：交付/backup_video/_check/backup_<段>.json（交付給學校時可以刪掉 _check 資料夾）。", ""]
    if plan:
        L.insert(L.index("六、重新產生（給 Claude 或維護者；專案根目錄）") + 2,
                 f"  預估：全劇 {plan['total_frames']} 格、影片約 {plan['total_video_min']} 分鐘，產生約 {plan['total_est_min']} 分鐘（{plan['rate_source']}）。")
    out.mkdir(parents=True, exist_ok=True)
    (out / "README.txt").write_text("﻿" + "\r\n".join(L) + "\r\n", encoding="utf-8")
    print(f"[backup.py] README.txt → {out / 'README.txt'}（{len(reps)} 段）")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "mux":
        mux(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve(), verify="--no-verify" not in sys.argv)
    elif cmd == "readme":
        readme(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
    elif cmd == "full":
        full(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
    else:
        sys.exit(f"未知指令 {cmd}")
