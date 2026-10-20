"""G4 驗收包分析（由 tools/g4_review_pack.mjs 呼叫）。

用法：
  /opt/anaconda3/bin/python3 tools/g4_review_pack.py analyze <驗收包資料夾>
  /opt/anaconda3/bin/python3 tools/g4_review_pack.py index   <驗收包資料夾>

analyze：
  1. 關鍵影格（16:9 與 4:3）的投影模擬 v2（tools/projsim.py 的函式）與接觸表
  2. a2_c002 每秒 8 格逐格條帶
  3. 依 timeline.json 的 cue 時間，照引擎的混音規則（app/src/audio/mixer.ts、ducking.ts、engine.ts scheduleAudio）
     把配音、配樂、音效混成一軌，量整合響度、真峰值、各句響度
  4. 連續播放逐格（30 格／秒）的光敏分析（tools/capture_analyze.py 的同一套方法）
  5. 組成 g4_playback.mp4（固定步長逐格＋混音）
  6. 長度與安全界線相關量測（只列數字）
index：彙整成 INDEX.md（只列檔案與量測數字，不寫評語）。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import capture_analyze as ca  # noqa: E402
import projsim  # noqa: E402

SR = 48000
FPS = 30
font = ca.font


def rel(p, base):
    return os.path.relpath(p, base).replace(os.sep, "/")


# ====================================================================== 1. 投影模擬
def proj_keyframes(out: Path):
    cap = out / "capture"
    meta = json.loads((cap / "capture.json").read_text(encoding="utf-8"))
    pdir = out / "proj"
    (pdir / "16x9").mkdir(parents=True, exist_ok=True)
    keys = sorted({f["file"] for f in meta["frames"] if f.get("key")})
    made = []
    for k in keys:
        src = cap / k
        rgb = np.array(projsim.load_rgb(src))
        pv = projsim.projector(rgb, "v2")
        stem = Path(k).stem
        Image.fromarray(pv).save(pdir / "16x9" / f"{stem}_proj.png")
        projsim._sheet([("original 原圖", rgb), ("proj 投影模擬 v2", pv), ("gray 灰階", projsim.grayscale(rgb)),
                        ("deut 綠色弱", projsim.deuteranopia(rgb))], rgb.shape[1], rgb.shape[0],
                       pdir / "16x9" / f"{stem}_sheet.png", title=f"{Path(k).name}｜投影模擬 v2：彩度×0.65、黑位 0.18、白位 0.87")
        made.append({"src": f"capture/{k}", "proj": f"proj/16x9/{stem}_proj.png", "sheet": f"proj/16x9/{stem}_sheet.png"})
    grid_sheet([(m["src"], m["proj"]) for m in made], out, pdir / "contact_proj_16x9.png", "關鍵影格 原圖｜投影模擬 v2（16:9 1920×1080）")
    res = {"16x9": made}
    k43 = out / "keyframes_4x3"
    for d in sorted(k43.glob("*x*")) if k43.exists() else []:
        (pdir / d.name).mkdir(parents=True, exist_ok=True)
        lst = []
        for f in sorted(d.glob("*.png")):
            rgb = np.array(projsim.load_rgb(f))
            Image.fromarray(projsim.projector(rgb, "v2")).save(pdir / d.name / f"{f.stem}_proj.png")
            lst.append((rel(f, out), f"proj/{d.name}/{f.stem}_proj.png"))
        grid_sheet(lst, out, pdir / f"contact_4x3_{d.name}.png", f"4:3 關鍵影格 原圖｜投影模擬 v2（{d.name.replace('x', '×')}）")
        res[d.name] = [{"src": a, "proj": b} for a, b in lst]
    return res


def grid_sheet(pairs, out: Path, path: Path, title: str, tw=360):
    """每列一個 cue（前／中／後），每格左原圖右投影模擬"""
    rows = {}
    for a, b in pairs:
        name = Path(a).name
        cue = name[:7]
        rows.setdefault(cue, []).append((a, b, name))
    if not rows:
        return
    im0 = Image.open(out / pairs[0][0])
    th = int(tw * im0.height / im0.width)
    cols = max(len(v) for v in rows.values())
    cw = tw * 2 + 6
    W = 150 + cols * (cw + 14)
    H = 46 + len(rows) * (th + 34)
    sheet = Image.new("RGB", (W, H), (24, 22, 20))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), title, font=font(22), fill=(240, 236, 228))
    y = 46
    for cue, items in rows.items():
        d.text((10, y + 4), cue, font=font(20), fill=(232, 200, 140))
        for i, (a, b, name) in enumerate(items):
            x = 150 + i * (cw + 14)
            sheet.paste(Image.open(out / a).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
            sheet.paste(Image.open(out / b).convert("RGB").resize((tw, th), Image.LANCZOS), (x + tw + 6, y))
            lab = name[8:].replace(".png", "").replace("_", " ")
            d.text((x, y + th + 4), f"{lab}　｜原圖　投影 v2", font=font(15), fill=(200, 196, 188))
        y += th + 34
    sheet.save(path)


# ====================================================================== 2. 條帶
def strip(out: Path, meta: dict):
    sd = out / "strip_a2_c002"
    files = sorted((sd / "frames").glob("*.jpg"))
    if not files:
        return []
    cols, tw = 8, 300
    th = int(tw * 9 / 16)
    per_page = cols * 6
    pages = []
    for p in range(0, len(files), per_page):
        chunk = files[p:p + per_page]
        rows = (len(chunk) + cols - 1) // cols
        W = 10 + cols * (tw + 8)
        H = 50 + rows * (th + 30)
        sheet = Image.new("RGB", (W, H), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        s = meta.get("strip") or {}
        d.text((10, 10), f"a2_c002 逐格條帶：每秒 {s.get('fps', 8)} 格，從 strings.drop 起點 {s.get('from')} 秒到停格（第 {p // per_page + 1} 頁）",
               font=font(22), fill=(240, 236, 228))
        for i, f in enumerate(chunk):
            x, y = 10 + (i % cols) * (tw + 8), 50 + (i // cols) * (th + 30)
            sheet.paste(Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
            t = float(f.stem.split("_")[-1])
            d.text((x, y + th + 3), f"t={t:.3f}s" + ("（停格）" if f is files[-1] else ""), font=font(16), fill=(200, 196, 188))
        path = sd / f"strip_a2_c002_8fps_p{len(pages) + 1:02d}.png"
        sheet.save(path)
        pages.append(rel(path, out))
    return pages



# ====================================================================== 2b. 與 G2 退路試作並排
def compare_g2(out: Path):
    """固定規則：G2 退路試作合成圖（review/G2/stage_composite*_v04.png）對 G4 劇場截圖 a2_c002「後」（停格）與「中」；上排原圖、下排投影模擬 v2"""
    cap = out / "capture" / "keyframes"
    g4_after = sorted(cap.glob("a2_c002_*_after.png"))
    g4_mid = sorted(cap.glob("a2_c002_*_mid.png"))
    pairs = [("16x9", ROOT / "review/G2/stage_composite_v04.png", g4_mid + g4_after)]
    k43 = out / "keyframes_4x3"
    for size, g2name in (("1440x1080", "stage_composite_43_v04.png"), ("1024x768", "stage_composite_1024x768_v04.png")):
        g = sorted((k43 / size).glob("a2_c002_*_after.png")) if (k43 / size).exists() else []
        pairs.append((size, ROOT / "review/G2" / g2name, g))
    made = []
    for tag, g2, g4s in pairs:
        if not g2.exists() or not g4s:
            continue
        cols = [("G2 退路試作 " + g2.name, g2)] + [("G4 劇場截圖 " + f.name, f) for f in g4s]
        im0 = Image.open(g2)
        tw = 560
        th = int(tw * im0.height / im0.width)
        W = 20 + len(cols) * (tw + 14)
        H = 50 + 2 * (th + 34)
        sheet = Image.new("RGB", (W, H), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        d.text((10, 10), f"G2 退路試作（review/G2）｜G4 劇場截圖 並排（{tag}）：上排原圖、下排投影模擬 v2", font=font(22), fill=(240, 236, 228))
        for i, (lab, f) in enumerate(cols):
            rgb = np.array(projsim.load_rgb(f))
            x = 10 + i * (tw + 14)
            a = Image.fromarray(rgb).resize((tw, int(tw * rgb.shape[0] / rgb.shape[1])), Image.LANCZOS)
            b = Image.fromarray(projsim.projector(rgb, "v2")).resize(a.size, Image.LANCZOS)
            sheet.paste(a, (x, 50)); sheet.paste(b, (x, 50 + th + 34))
            d.text((x, 50 + th + 4), lab, font=font(15), fill=(200, 196, 188))
            d.text((x, 50 + 2 * th + 38), "投影模擬 v2", font=font(15), fill=(200, 196, 188))
        path = out / f"compare_g2v04_g4_{tag}.png"
        sheet.save(path)
        made.append(rel(path, out))
    return made

# ====================================================================== 3. 混音（照引擎規則）
class Param:
    """Web Audio AudioParam 的簡化版：setValueAtTime、linearRampToValueAtTime、setTargetAtTime、cancelScheduledValues"""

    def __init__(self, v0):
        self.v0 = v0
        self.ev = []  # (time, kind, value, tc)

    def cancel(self, t):
        self.ev = [e for e in self.ev if e[0] < t - 1e-12]

    def set(self, v, t):
        self.ev.append((t, "set", v, 0)); self.ev.sort(key=lambda e: e[0])

    def linear(self, v, t):
        self.ev.append((t, "lin", v, 0)); self.ev.sort(key=lambda e: e[0])

    def target(self, v, t, tc):
        self.ev.append((t, "tgt", v, tc)); self.ev.sort(key=lambda e: e[0])

    def at(self, t):
        return float(self.render(np.array([float(t)]))[0])

    def render(self, ts):
        ev = sorted(self.ev, key=lambda e: e[0])
        out = np.full(ts.shape, self.v0, dtype=np.float64)
        st = {"t": -np.inf, "v": self.v0, "mode": "hold", "tgt": 0.0, "tc": 1.0}

        def val(t):
            if st["mode"] == "tgt":
                return st["tgt"] + (st["v"] - st["tgt"]) * np.exp(-(t - st["t"]) / st["tc"])
            return st["v"] + 0.0 * t

        for T, kind, V, TC in ev:
            m = (ts >= st["t"]) & (ts < T)
            if kind == "lin":
                t1 = st["t"] if np.isfinite(st["t"]) else T
                v1 = st["v"]
                if m.any():
                    out[m] = v1 + (V - v1) * (ts[m] - t1) / max(1e-9, T - t1)
                st.update(t=T, v=V, mode="hold")
            else:
                if m.any():
                    out[m] = val(ts[m])
                vT = float(val(np.array(T))) if np.isfinite(st["t"]) or st["mode"] == "hold" else st["v"]
                if kind == "set":
                    st.update(t=T, v=V, mode="hold")
                else:
                    st.update(t=T, v=vT, mode="tgt", tgt=V, tc=max(1e-6, TC))
        m = ts >= st["t"]
        out[m] = val(ts[m])
        return out


def load_wav(path: Path):
    sr, x = wavfile.read(path)
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768.0
    elif x.dtype == np.int32:
        x = x.astype(np.float32) / 2147483648.0
    x = x.astype(np.float32)
    if sr != SR:
        from scipy.signal import resample_poly
        g = np.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g, axis=0).astype(np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)  # 單聲道 → 左右同值（Web Audio speakers 上混）
    return x


def duck_plan(intervals):
    """app/src/audio/ducking.ts 的 duckingPlan（同參數）"""
    src = (ROOT / "app/src/audio/ducking.ts").read_text(encoding="utf-8")
    c = {k: float(re.search(rf"export const {k} = ([\d.]+)", src).group(1)) for k in
         ("DUCK_LEVEL", "DUCK_LEAD", "DUCK_TC_DOWN", "DUCK_RELEASE", "DUCK_TC_UP", "DUCK_BRIDGE")}
    out = []
    s = sorted(intervals)
    for i, (a, b) in enumerate(s):
        out.append((a - c["DUCK_LEAD"], c["DUCK_LEVEL"], c["DUCK_TC_DOWN"]))
        nxt = s[i + 1][0] if i + 1 < len(s) else None
        if nxt is None or nxt - b > c["DUCK_BRIDGE"]:
            out.append((b + c["DUCK_RELEASE"], 1.0, c["DUCK_TC_UP"]))
    return out, c


def mix(out: Path, tl: dict):
    work = out / "_work"
    total = tl["totalPlaybackSec"]
    N = int(np.ceil(total * SR)) + SR
    ts = np.arange(N) / SR
    audio = tl["audio"]
    cache = {}

    def buf(aid):
        if aid not in cache:
            cache[aid] = load_wav(ROOT / audio[aid]["source"])
        return cache[aid]

    voices = []  # dict(bus, id, start, offset, loop, gain: Param, stop)
    bus_level = Param(0.0)
    duck = Param(1.0)
    music_now = []
    events_log = []
    cues = {c["id"]: c for c in tl["cues"]}
    sched = tl["schedule"]

    def stop_bus(bus, t, fade=0.03):
        """Mixer.stop(bus)：還在播的 30 ms 淡出；排在之後還沒開始的直接取消"""
        for v in voices:
            if v["bus"] != bus or v["stop"] <= t:
                continue
            if v["start"] >= t:
                v["stop"] = v["start"]
                continue
            g = v["gain"]
            cur = g.at(t)
            g.cancel(t); g.set(cur, t); g.linear(0.0, t + fade)
            v["stop"] = min(v["stop"], t + fade + 0.01)

    def crossfade(mid, t, loop=True, fade=1.5, gain=1.0, offset=0.0):
        fade = max(0.05, fade)
        for v in voices:
            if v["bus"] != "music" or v["stop"] <= t:
                continue
            g = v["gain"]
            cur = g.at(t)
            g.cancel(t); g.set(cur, t); g.linear(0.0, t + fade)
            v["stop"] = min(v["stop"], t + fade + 0.05)
        if mid == "none":
            return
        if mid not in audio:
            events_log.append({"t": round(t, 3), "missing": mid})
            return
        b = buf(mid)
        dur = len(b) / SR
        g = Param(0.0)
        g.set(0.0, t); g.linear(gain, t + fade)
        voices.append({"bus": "music", "id": mid, "start": t, "offset": offset % max(0.01, dur), "loop": loop, "gain": g,
                       "stop": np.inf if loop else t + dur - offset % max(0.01, dur)})
        events_log.append({"t": round(t, 3), "music": mid, "loop": loop, "fade": fade, "gain": gain, "offset": offset})

    line_spans = []
    current_music = None
    for s in sched:
        c = cues[s["id"]]
        G = s["start"]
        # playCue：先停掉台詞與音效
        stop_bus("vo", G)
        stop_bus("sfx", G)
        intervals = []
        for l in c["lines"]:
            if l["audioId"] not in audio:
                continue
            b = buf(l["audioId"])
            st = G + l["start"]
            g = Param(1.0)
            voices.append({"bus": "vo", "id": l["audioId"], "start": st, "offset": 0.0, "loop": False, "gain": g, "stop": st + len(b) / SR})
            intervals.append((st, G + l["end"]))
            line_spans.append({"id": l["id"], "cue": c["id"], "speaker": l["speaker"], "start": st, "end": G + l["end"], "audioId": l["audioId"]})
        for x in c["sfx"]:
            if x["id"] not in audio:
                events_log.append({"t": round(G + x["at"], 3), "missing": x["id"]})
                continue
            b = buf(x["id"])
            st = G + x["at"]
            voices.append({"bus": "sfx", "id": x["id"], "start": st, "offset": 0.0, "loop": False, "gain": Param(x.get("gain", 1.0)), "stop": st + len(b) / SR})
        if c["audioId"] == "none":
            crossfade("none", G, fade=1.0)
        elif c["audioId"] and current_music != c["audioId"]:
            crossfade(c["audioId"], G, loop=c["musicLoop"], fade=1.0)
        for m in c["music"]:
            crossfade(m["id"], G + m["at"], loop=m["loop"], fade=m["fade"], gain=m["gain"], offset=m["offset"])
        cur_level = bus_level.at(G)
        bus_level.cancel(G); bus_level.target(c["musicLevel"], G, 0.35)
        cur_d = duck.at(G)
        duck.cancel(G); duck.set(cur_d, G)
        plan, dk = duck_plan(intervals)
        for at, val, tc in plan:
            duck.target(val, max(G, at), tc)
    # 渲染
    stems = {b: np.zeros((N, 2), np.float32) for b in ("vo", "music", "sfx")}
    for v in voices:
        b = buf(v["id"])
        L = len(b)
        s0 = int(round(v["start"] * SR))
        s1 = min(N, int(round(min(v["stop"], total + 1) * SR)))
        if s1 <= s0:
            continue
        n = s1 - s0
        off = int(round(v["offset"] * SR))
        if v["loop"]:
            idx = (off + np.arange(n)) % L
            seg = b[idx]
        else:
            seg = b[off:off + n]
            n = len(seg)
            s1 = s0 + n
        g = v["gain"].render(ts[s0:s1]).astype(np.float32)
        stems[v["bus"]][s0:s1] += seg * g[:, None]
    lvl = (bus_level.render(ts) * duck.render(ts)).astype(np.float32)
    stems["music"] *= lvl[:, None]
    N2 = int(round(total * SR))
    for k in stems:
        stems[k] = stems[k][:N2]
    total_mix = stems["vo"] + stems["music"] + stems["sfx"]
    return total_mix, stems, line_spans, events_log, ts[:N2], lvl[:N2], dk


def write_wav(path, x, bits=16):
    x = np.clip(x, -1.0, 1.0)
    if bits == 16:
        wavfile.write(path, SR, (x * 32767.0).round().astype(np.int16))
    else:
        wavfile.write(path, SR, x.astype(np.float32))


def ebur(x, framelog=False):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        p = fh.name
    write_wav(p, x, bits=32)
    args = ["ffmpeg", "-nostats", "-hide_banner", "-i", p, "-filter_complex", "ebur128=peak=true" + (":framelog=verbose" if framelog else ""), "-f", "null", "-"]
    r = subprocess.run(args, capture_output=True, text=True)
    os.unlink(p)
    txt = r.stderr
    summ = txt[txt.rfind("Summary:"):]

    def grab(pat):
        m = re.search(pat, summ)
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None
    res = {"I_LUFS": grab(r"I:\s+(-?[\d.]+|-inf) LUFS"), "LRA_LU": grab(r"LRA:\s+(-?[\d.]+) LU"),
           "TP_dBTP": grab(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS")}
    if framelog:
        mom = []
        for m in re.finditer(r"t:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+|-inf)\s+S:\s*(-?[\d.]+|-inf)", txt):
            t, M, S = m.groups()
            mom.append((float(t), float(M) if M != "-inf" else -120.0, float(S) if S != "-inf" else -120.0))
        res["momentary"] = mom
    return res


def momentary(x):
    """ITU-R BS.1770 K 加權瞬間響度（400 ms 窗、每 100 ms），回傳 [(窗結束秒, LUFS, 0)]"""
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x.astype(np.float64), axis=0), axis=0)
    ms = (y ** 2).sum(axis=1)
    c = np.concatenate([[0.0], np.cumsum(ms)])
    win, hop = int(0.4 * SR), int(0.1 * SR)
    out = []
    for end in range(win, len(ms) + 1, hop):
        z = (c[end] - c[end - win]) / win
        out.append((end / SR, -0.691 + 10 * np.log10(z) if z > 1e-12 else -120.0, 0.0))
    return out


def audio_analysis(out: Path, tl: dict):
    adir = out / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    work = out / "_work"
    mixed, stems, spans, elog, ts, lvl, dk = mix(out, tl)
    peak = float(np.abs(mixed).max())
    clipped = int((np.abs(mixed) >= 1.0).sum())
    write_wav(adir / "g4_mix.wav", mixed, 16)
    (work / "stems").mkdir(parents=True, exist_ok=True)
    for k, v in stems.items():
        write_wav(work / "stems" / f"{k}.wav", v, 32)
    full = ebur(mixed)
    mom = momentary(mixed)
    sched = {s["id"]: s for s in tl["schedule"]}
    a = sched["a2_c002"]["start"]
    b = sched["a2_c004"]["start"] + sched["a2_c004"]["duration"]
    seg = ebur(mixed[int(a * SR):int(b * SR)])
    per_cue = {}
    for s in tl["schedule"]:
        if s["duration"] >= 1.0:
            x = mixed[int(s["start"] * SR):int((s["start"] + s["duration"]) * SR)]
            per_cue[s["id"]] = ebur(x)
    lines = []
    bg = stems["music"] + stems["sfx"]
    (work / "mixseg").mkdir(parents=True, exist_ok=True)
    for sp in spans:
        i0, i1 = int(sp["start"] * SR), int(sp["end"] * SR)
        vo_file = ROOT / tl["audio"][sp["audioId"]]["source"]
        f = ebur(load_wav(vo_file)[:, 0])
        in_mix = ebur(mixed[i0:i1])
        vo_in = ebur(stems["vo"][i0:i1])
        bgm = ebur(bg[i0:i1])
        write_wav(work / "mixseg" / f"{sp['id']}.wav", mixed[max(0, i0 - int(0.1 * SR)):i1 + int(0.1 * SR)], 16)
        lines.append({"id": sp["id"], "cue": sp["cue"], "speaker": sp["speaker"], "start": round(sp["start"], 3), "end": round(sp["end"], 3),
                      "vo_file": rel(vo_file, ROOT), "vo_file_I_LUFS": f["I_LUFS"], "vo_file_TP_dBTP": f["TP_dBTP"],
                      "mix_I_LUFS": in_mix["I_LUFS"], "vo_in_mix_I_LUFS": vo_in["I_LUFS"], "background_I_LUFS": bgm["I_LUFS"],
                      "vo_minus_background_LU": None if (vo_in["I_LUFS"] is None or bgm["I_LUFS"] is None) else round(vo_in["I_LUFS"] - bgm["I_LUFS"], 1)})
    vals = [l["vo_file_I_LUFS"] for l in lines if l["vo_file_I_LUFS"] is not None]
    mvals = [l["mix_I_LUFS"] for l in lines if l["mix_I_LUFS"] is not None]
    # 瞬間響度（400 ms，每 100 ms）：最大值與 1 秒內最大上升
    M = np.array([m[1] for m in mom]) if mom else np.array([])
    T = np.array([m[0] for m in mom]) if mom else np.array([])
    rise1 = rise01 = None
    if len(M) > 10:
        Mc = np.maximum(M, -70.0)
        rise1 = max(float(Mc[i] - Mc[max(0, i - 10):i].min()) for i in range(1, len(Mc)))
        rise01 = float(np.max(Mc[1:] - Mc[:-1]))
        imax = int(np.argmax(M))
    music_stem_full = ebur(stems["music"])

    def rises(mm):
        Mv = np.maximum(np.array([m[1] for m in mm]), -70.0)
        Tv = np.array([m[0] for m in mm])
        r1 = [float(Mv[i] - Mv[max(0, i - 10):i].min()) for i in range(1, len(Mv))]
        i1 = int(np.argmax(r1)) + 1
        r01 = Mv[1:] - Mv[:-1]
        i01 = int(np.argmax(r01)) + 1
        return {"max_LUFS": round(float(Mv.max()), 1), "max_at_sec": round(float(Tv[int(np.argmax(Mv))]), 1),
                "max_rise_within_1s_LU": round(r1[i1 - 1], 1), "max_rise_within_1s_at_sec": round(float(Tv[i1]), 1),
                "max_rise_per_100ms_LU": round(float(r01[i01 - 1]), 1), "max_rise_per_100ms_at_sec": round(float(Tv[i01]), 1)}
    mom_bg = rises(momentary(bg))
    mom_full = rises(mom) if len(mom) > 10 else None
    res = {
        "note": "依 timeline.json 的 cue 時間與教師按鍵間隔假設，照引擎混音規則（三條匯流排、配樂基準音量 setTargetAtTime 0.35 s、對白避讓 duckingPlan、交叉淡入淡出、換 cue 停台詞與音效 30 ms 淡出）以 48 kHz 離線混音；總音量 1.0。",
        "file": "audio/g4_mix.wav",
        "duration_sec": round(len(mixed) / SR, 3),
        "sample_peak_dBFS": round(20 * np.log10(max(peak, 1e-9)), 2),
        "clipped_samples": clipped,
        "full_playback": full,
        "a2_c002_to_a2_c004": {**seg, "from_sec": a, "to_sec": round(b, 3)},
        "per_cue": per_cue,
        "music_stem_full": music_stem_full,
        "lines": lines,
        "line_vo_file_I_spread_LU": round(max(vals) - min(vals), 2) if vals else None,
        "line_mix_I_spread_LU": round(max(mvals) - min(mvals), 2) if mvals else None,
        "momentary_max_LUFS": round(float(M.max()), 1) if len(M) else None,
        "momentary_max_at_sec": round(float(T[imax]), 1) if len(M) else None,
        "momentary_max_rise_within_1s_LU": round(rise1, 1) if rise1 is not None else None,
        "momentary_max_rise_per_100ms_LU": round(rise01, 1) if rise01 is not None else None,
        "momentary_full_mix": mom_full,
        "momentary_music_sfx_only": mom_bg,
        "momentary_note": "瞬間響度（BS.1770 K 加權，400 ms 窗，每 100 ms）；上升量以 −70 LUFS 為下限計算；music_sfx_only＝不含配音的配樂＋音效分軌（含基準音量與避讓）。",
        "ducking_constants": dk,
        "events": elog,
    }
    (adir / "loudness.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    plot_audio(adir / "g4_mix_plot.png", mixed, stems, lvl, ts, T, M, tl, spans)
    return res


def plot_audio(path, mixed, stems, lvl, ts, T, M, tl, spans):
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
    tt = ts[::step]
    for i, (k, lab) in enumerate((("vo", "配音"), ("music", "配樂（含基準音量與避讓）"), ("sfx", "音效"))):
        x = stems[k][:, 0]
        n = len(x) // step * step
        env = np.abs(x[:n]).reshape(-1, step).max(axis=1)
        ax[i].fill_between(tt[:len(env)], -env, env, lw=0, color=("#3b6ea8", "#a8643b", "#5a8a4a")[i])
        ax[i].set_ylabel(lab, rotation=0, ha="right", va="center")
        ax[i].set_ylim(-1, 1)
    ax[1].plot(ts[::step], lvl[::step], color="k", lw=0.8, label="配樂增益（基準×避讓）")
    ax[1].legend(loc="upper right", fontsize=9)
    if len(M):
        ax[3].plot(T, np.maximum(M, -60), lw=0.8, color="#333")
    ax[3].set_ylabel("總混音瞬間響度\nLUFS（400 ms）", rotation=0, ha="right", va="center")
    ax[3].set_ylim(-60, -5)
    for s in tl["schedule"]:
        for a in ax:
            a.axvline(s["start"], color="#999", lw=0.6, ls="--")
        ax[0].text(s["start"] + 0.2, 0.75, s["id"], fontsize=9)
    for sp in spans:
        ax[0].axvspan(sp["start"], sp["end"], color="#3b6ea8", alpha=0.08)
    ax[3].set_xlabel("播放時間（秒，含教師按鍵間隔假設）")
    fig.suptitle("G4 最終混音：分軌波形與瞬間響度")
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


# ====================================================================== 4. 連續播放光敏分析
def playback_sequence(out: Path, tl: dict):
    """回傳播放錄製的逐格清單 [(全域時間, 檔案, cue, cue 內時間)]（停住格重複同一張）"""
    work = out / "_work" / "video"
    seq = []
    for s in tl["schedule"]:
        G, D, hold = s["start"], s["duration"], s["hold"]
        f0 = int(round(G * FPS))
        f_end = int(round((G + D) * FPS))
        f_hold = int(round((G + D + hold) * FPS))
        for k in range(f_end - f0):
            p = work / s["id"] / f"{k:05d}.jpg"
            if not p.exists():
                p = work / s["id"] / "after.jpg"
            seq.append((round((f0 + k) / FPS, 4), p, s["id"], round(k / FPS, 4)))
        for k in range(f_end, f_hold):
            seq.append((round(k / FPS, 4), work / s["id"] / "after.jpg", s["id"], round(D + (k - f_end) / FPS, 4)))
    return seq


def flash_playback(out: Path, seq):
    times, luma, red, regL, regR = [], [], [], [], []
    cache = {}
    for t, p, cue, ct in seq:
        k = str(p)
        if k not in cache:
            cache = {k: ca.frame_stats(p)}  # 停住格連續重複，只留最近一張
        rl, rr, ml, rratio = cache[k]
        times.append(t); luma.append(ml); red.append(rratio); regL.append(rl); regR.append(rr)
    regL, regR = np.array(regL), np.array(regR)
    flagged, near, worst = [], [], {"luma": 0, "red": 0}
    where = {round(t, 4): (cue, ct) for t, p, cue, ct in seq}
    wc, wat = ca.max_per_second(ca.transitions(times, luma, ca.LUMA_TH, ca.LUMA_DARK))
    worst["luma"] = wc
    if wc > ca.LIMIT_PER_SEC:
        flagged.append({"type": "luma", "region": "全畫面", "count_per_sec": wc, "window_start": wat})
    W0, H0 = 1920, 1080
    for gy in range(ca.GRID_H):
        for gx in range(ca.GRID_W):
            for kind, arr, th, dark in (("luma", regL, ca.LUMA_TH, ca.LUMA_DARK), ("red", regR, ca.RED_TH, None)):
                ev = ca.transitions(times, list(arr[:, gy, gx]), th, dark)
                c, at = ca.max_per_second(ev)
                worst[kind] = max(worst[kind], c)
                rec = {"type": kind, "region": f"x{gx}_y{gy}", "px": [gx * W0 // ca.GRID_W, gy * H0 // ca.GRID_H, (gx + 1) * W0 // ca.GRID_W, (gy + 1) * H0 // ca.GRID_H],
                       "count_per_sec": c, "window_start": at}
                if at is not None:
                    cue, ct = where.get(round(at, 4), (None, None))
                    rec.update({"cue": cue, "cue_t": ct})
                if c > ca.LIMIT_PER_SEC:
                    flagged.append(rec)
                elif c >= 2:
                    near.append(rec)
    # 換 cue 的接縫：前一格與後一格的全畫面亮度差
    seams = []
    for i in range(1, len(seq)):
        if seq[i][2] != seq[i - 1][2]:
            seams.append({"from": seq[i - 1][2], "to": seq[i][2], "t": seq[i][0], "mean_luma_before": round(luma[i - 1], 4), "mean_luma_after": round(luma[i], 4),
                          "max_region_luma_delta": round(float(np.abs(regL[i] - regL[i - 1]).max()), 4)})
    rep = {
        "ok": len(flagged) == 0,
        "rule": "任一區域明暗或飽和紅色每秒變化 ≤ 3 次（不採面積豁免）",
        "method": f"播放錄製的連續逐格（{FPS} 格／秒，含 cue 之間的接縫與停住格）；{ca.GRID_W}×{ca.GRID_H} 區域＋全畫面；亮度門檻 {ca.LUMA_TH}（較暗端 < {ca.LUMA_DARK}）；紅色門檻 {ca.RED_TH}（R/(R+G+B) ≥ 0.8）",
        "frames_analyzed": len(seq),
        "duration_sec": round(len(seq) / FPS, 3),
        "max_changes_per_sec": worst,
        "flagged": flagged,
        "near_limit": sorted(near, key=lambda x: (-x["count_per_sec"], x["window_start"] or 0)),
        "near_limit_total": len(near),
        "cue_seams": seams,
        "mean_luma_range": [round(min(luma), 4), round(max(luma), 4)],
        "max_sat_red_ratio": round(max(red), 5),
    }
    (out / "flash_playback.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    plot_luma(out / "flash_playback_plot.png", times, luma, red, regL, near, rep)
    return rep


def plot_luma(path, times, luma, red, regL, near, rep):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for fp in ("/System/Library/Fonts/STHeiti Medium.ttc",):
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
    fig, ax = plt.subplots(3, 1, figsize=(18, 8), sharex=True)
    ax[0].plot(times, luma, lw=0.8)
    ax[0].set_ylabel("全畫面平均\n線性亮度", rotation=0, ha="right", va="center")
    ax[1].plot(times, regL.reshape(len(times), -1).max(axis=1), lw=0.6, label="最亮區域")
    ax[1].plot(times, regL.reshape(len(times), -1).min(axis=1), lw=0.6, label="最暗區域")
    ax[1].legend(loc="upper right", fontsize=9)
    ax[1].set_ylabel("16×9 區域\n線性亮度", rotation=0, ha="right", va="center")
    ax[2].plot(times, red, lw=0.8, color="#b03030")
    ax[2].set_ylabel("飽和紅色\n像素比例", rotation=0, ha="right", va="center")
    for n in near:
        if n.get("window_start") is not None:
            ax[0].axvspan(n["window_start"], n["window_start"] + 1, color="orange", alpha=0.04)
    ax[2].set_xlabel("播放時間（秒）")
    fig.suptitle(f"播放錄製逐格亮度／飽和紅色（每秒最多變化：明暗 {rep['max_changes_per_sec']['luma']}、紅色 {rep['max_changes_per_sec']['red']}；橘色＝接近上限的 1 秒窗）")
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


# ====================================================================== 5. 影片
def make_video(out: Path, seq):
    sdir = out / "_work" / "seq"
    if sdir.exists():
        for f in sdir.iterdir():
            f.unlink()
    sdir.mkdir(parents=True, exist_ok=True)
    for i, (t, p, cue, ct) in enumerate(seq):
        os.symlink(p, sdir / f"{i:06d}.jpg")
    mp4 = out / "g4_playback.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(sdir / "%06d.jpg"), "-i", str(out / "audio" / "g4_mix.wav"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-movflags", "+faststart", "-shortest", str(mp4)]
    subprocess.run(cmd, check=True)
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames",
                                    "-of", "json", str(mp4)], capture_output=True, text=True).stdout)
    return {"file": "g4_playback.mp4", "frames": len(seq), "ffprobe": pr}


# ====================================================================== 6. 長度與安全界線量測
def seg_box_dist(p, q, box):
    """線段 pq 到矩形的最短距離（相交＝0）"""
    x0, y0, x1, y1 = box
    def inside(pt):
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1
    if inside(p) or inside(q):
        return 0.0
    best = np.inf
    for t in np.linspace(0, 1, 41):
        pt = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        if inside(pt):
            return 0.0
        dx = max(x0 - pt[0], 0, pt[0] - x1)
        dy = max(y0 - pt[1], 0, pt[1] - y1)
        best = min(best, float(np.hypot(dx, dy)))
    return best


def safety_data(out: Path, tl: dict):
    cue_file = json.loads((ROOT / "app/cues/g4.json").read_text(encoding="utf-8"))
    anchors = set()
    for c in cue_file["cues"]:
        for ch in (c.get("initialState", {}).get("characters") or {}).values():
            anchors.update(ch.get("strings") or [])
        for a in c.get("animation", []):
            if a["name"].startswith("strings."):
                anchors.update((a.get("params") or {}).get("anchors") or [])
    attach = json.loads((ROOT / "assets/final/rig/ale_attach.json").read_text(encoding="utf-8"))
    probe = json.loads((out / "capture" / "probe.json").read_text(encoding="utf-8"))["probes"]
    probe_src = "capture/probe.json（關鍵影格與每秒一格）"
    if (out / "probe_dense.json").exists():
        probe = probe + json.loads((out / "probe_dense.json").read_text(encoding="utf-8"))["probes"]
        probe_src += "＋probe_dense.json（播放錄製每秒 10 次）"
    head_d, kid_hits, frames_with_strings = [], [], 0
    per_anchor = {}
    for pr in probe:
        acts = {a["id"]: a for a in pr["actors"]}
        hb = acts.get("ale", {}).get("headBox")
        vis = [s for s in pr["strings"] if s.get("visible") and s.get("path")]
        if not vis:
            continue
        frames_with_strings += 1
        for s in vis:
            path = s["path"]
            if hb:
                d = min(seg_box_dist(path[i], path[i + 1], hb) for i in range(len(path) - 1))
                head_d.append(d)
                pa = per_anchor.setdefault(s["anchor"], {"min_dist_to_head_box_px": np.inf, "frames": 0, "at": None})
                if d < pa["min_dist_to_head_box_px"]:
                    pa["min_dist_to_head_box_px"], pa["at"] = d, f"{pr['cueId']} t={pr['t']}"
                pa["frames"] += 1
            for kid in ("xiaoqing", "xiaoyu"):
                kb = acts.get(kid, {}).get("box")
                if kb and acts[kid].get("visible"):
                    d = min(seg_box_dist(path[i], path[i + 1], kb) for i in range(len(path) - 1))
                    if d == 0.0:
                        kid_hits.append({"cue": pr["cueId"], "t": pr["t"], "anchor": s["anchor"], "kid": kid})
    for v in per_anchor.values():
        v["min_dist_to_head_box_px"] = round(float(v["min_dist_to_head_box_px"]), 1)
    # 必要旁白一：CLAUDE.md、劇本、cue 檔三方逐字比對
    req = re.findall(r"「(這些線是故事的比喻。[^」]*)」", (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    script_line = None
    for raw in (ROOT / "script/劇本_v03.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[a2_c004_02\]\s*[^：]+：(.+?)\s*$", raw.strip())
        if m:
            script_line = m.group(1)
    cue_line = next(l["text"] for c in tl["cues"] for l in c["lines"] if l["id"] == "a2_c004_02")
    plain = re.sub(r"\s*\n\s*", "", cue_line)
    # 字幕排版
    sub = []
    for c in tl["cues"]:
        for l in c["lines"]:
            rows = [r for p in l["pages"] for r in p["rows"]]
            sub.append({"id": l["id"], "pages": len(l["pages"]), "max_rows_per_page": max(len(p["rows"]) for p in l["pages"]),
                        "max_chars_per_row": max(len(r) for r in rows), "rows": [p["rows"] for p in l["pages"]]})
    # 隱私：程式碼裡的攝影機、麥克風 API；擷取時的外部網路請求
    app_js = (ROOT / "app/dist/app.js").read_text(encoding="utf-8")
    cap = json.loads((out / "capture" / "capture.json").read_text(encoding="utf-8"))
    res = {
        "string_anchors_in_cues": sorted(anchors),
        "attach_points_primary": {k: {"part": v.get("part"), "local_px": v.get("local_px") or v.get("part_px")} for k, v in (attach.get("points") or {}).items() if v.get("primary", True)},
        "probe_frames_with_strings": frames_with_strings,
        "string_path_min_dist_to_ale_head_box_px": round(float(min(head_d)), 1) if head_d else None,
        "per_anchor": per_anchor,
        "string_path_intersects_child_box": kid_hits,
        "string_path_intersects_child_box_count": len(kid_hits),
        "probe_method": probe_src + "；線路徑＝引擎同一條二次貝茲曲線投影成 13 點；頭部框＝阿樂叔叔顯示中的 head／head_worried 部件圖外框（含透明邊，比可見的頭大）；兒童框＝整個立牌外框（含透明邊）。",
        "required_narration_1": {
            "claude_md": req[0] if req else None,
            "script_v03": script_line,
            "cue_text_plain": plain,
            "script_equals_claude_md": bool(req) and script_line == req[0],
            "cue_equals_script": plain == script_line,
        },
        "subtitles": sub,
        "subtitle_max_chars_per_row": max(s["max_chars_per_row"] for s in sub),
        "subtitle_max_rows_per_page": max(s["max_rows_per_page"] for s in sub),
        "app_js_getUserMedia_count": app_js.count("getUserMedia"),
        "app_js_mediaDevices_count": app_js.count("mediaDevices"),
        "capture_external_requests": len(cap.get("externalRequests", [])),
        "capture_console_errors": len(cap.get("consoleErrors", [])),
    }
    (out / "safety_data.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def durations(out: Path, tl: dict, video: dict | None):
    d = {c["id"]: c["duration"] for c in tl["cues"]}
    vdur = None
    if video:
        try:
            vdur = float(video["ffprobe"]["format"]["duration"])
        except (KeyError, TypeError, ValueError):
            vdur = None
    res = {
        "cues": d,
        "a2_c002_plus_a2_c004_sec": round(d["a2_c002"] + d["a2_c004"], 3),
        "target_sec": [30, 45],
        "all_cues_sum_sec": round(sum(d.values()), 3),
        "opening_a0_c001_sec": d.get("a0_c001"),
        "closing_a8_c002_plus_a8_c003_sec": round(d.get("a8_c002", 0) + d.get("a8_c003", 0), 3),
        "playback_with_holds_sec": tl["totalPlaybackSec"],
        "holds_assumed_sec": {s["id"]: s["hold"] for s in tl["schedule"]},
        "video_duration_sec": vdur,
        "vo_seconds_in_a2_c002_a2_c004": round(sum(l["duration"] for c in tl["cues"] if c["id"] in ("a2_c002", "a2_c004") for l in c["lines"]), 3),
    }
    (out / "durations.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def analyze(out: Path):
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    meta = json.loads((out / "_work" / "frames_meta.json").read_text(encoding="utf-8")) if (out / "_work" / "frames_meta.json").exists() else {}
    res = {}
    print("[g4pack.py] 投影模擬")
    res["proj"] = proj_keyframes(out)
    print("[g4pack.py] 條帶")
    res["strip_pages"] = strip(out, meta)
    res["compare_g2"] = compare_g2(out)
    print("[g4pack.py] 混音與響度")
    res["audio"] = {k: v for k, v in audio_analysis(out, tl).items() if k not in ("lines", "events", "per_cue")}
    seq = playback_sequence(out, tl)
    print(f"[g4pack.py] 播放逐格光敏分析（{len(seq)} 格）")
    fl = flash_playback(out, seq)
    res["flash_playback"] = {k: fl[k] for k in ("ok", "max_changes_per_sec", "near_limit_total", "frames_analyzed")}
    print("[g4pack.py] 影片")
    video = make_video(out, seq)
    res["video"] = video
    res["durations"] = durations(out, tl, video)
    res["safety"] = safety_data(out, tl)
    res["frames_meta"] = {k: v for k, v in meta.items() if k in ("strip", "engineDurations", "errors")}
    (out / "analysis.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("[g4pack.py] 分析完成")


# ====================================================================== INDEX.md
def fmt(x, nd=1):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def index(out: Path):
    J = lambda p: json.loads((out / p).read_text(encoding="utf-8")) if (out / p).exists() else None
    tl, an = J("timeline.json"), J("analysis.json")
    cap = J("capture/capture.json")
    fr, pr = J("capture/flash_report.json"), J("capture/probe_report.json")
    fp, au, perf = J("flash_playback.json"), J("audio/loudness.json"), J("perf.json")
    du, sa, tx = J("durations.json"), J("safety_data.json"), J("transcripts.json")
    L = []
    w = L.append
    w("# G4 代表鏡頭驗收包")
    w("")
    w(f"- 產生：`tools/g4_review_pack.mjs`（呼叫 `tools/capture.mjs`、`tools/g4_review_pack.py`、`tools/g4_transcripts.py`、`tools/projsim.py` 的函式）；產生時間 {cap['createdAt'] if cap else '—'}")
    w(f"- cue 檔：`app/cues/g4.json`；渲染：{cap['width']}×{cap['height']}、畫質 {cap['quality']}；GPU：{cap['gpu']}" if cap else "")
    w("- 取樣規則固定：每個 cue 前（t=0）、中（t=長度/2）、後（播完停住）各 1 格；每秒 2 格接觸表；a2_c002 從 `strings.drop` 起點到停格每秒 8 格；光敏分析每秒 30 格。")
    w("- 重現：`cd app && npm run build && cd .. && caffeinate -i node tools/g4_review_pack.mjs`")
    w("")
    w("## 1. 長度")
    w("")
    w("| 項目 | 秒數 |")
    w("|---|---|")
    for k, v in du["cues"].items():
        w(f"| {k} | {fmt(v, 3)} |")
    w(f"| a2_c002＋a2_c004 | {fmt(du['a2_c002_plus_a2_c004_sec'], 3)}（目標 30–45） |")
    w(f"| 整段 cue 合計（署名卡待機→開幕→a2_c002→a2_c004→閉幕→署名卡） | {fmt(du['all_cues_sum_sec'], 3)} |")
    w(f"| 開幕 a0_c001 | {fmt(du['opening_a0_c001_sec'], 3)} |")
    w(f"| 閉幕 a8_c002＋a8_c003 | {fmt(du['closing_a8_c002_plus_a8_c003_sec'], 3)} |")
    w(f"| a2_c002＋a2_c004 內配音合計 | {fmt(du['vo_seconds_in_a2_c002_a2_c004'], 3)} |")
    w(f"| 播放錄製（含教師按鍵間隔假設） | {fmt(du['playback_with_holds_sec'], 3)} |")
    w(f"| g4_playback.mp4 實際長度（ffprobe） | {fmt(du['video_duration_sec'], 3)} |")
    w("")
    w("教師按鍵間隔假設（cue 播完後停住幾秒才按下一步）：" + "、".join(f"{k} {v} 秒" for k, v in du["holds_assumed_sec"].items()) + "（a8_c002 自動接 a8_c003）。")
    eng = (an or {}).get("frames_meta", {}).get("engineDurations") or {}
    if eng:
        diff = max(abs(eng.get(k, v) - v) for k, v in du["cues"].items())
        w(f"引擎 getCues() 回報的 cue 長度與 timeline.json 最大差 {diff:.3f} 秒。")
    w("")
    w("## 2. 畫面")
    w("")
    w("| 檔案 | 內容 |")
    w("|---|---|")
    w("| `capture/contact_keyframes.png` | 每個 cue 前／中／後關鍵影格接觸表（1920×1080） |")
    w("| `capture/keyframes/*.png` | 關鍵影格原尺寸 PNG（%d 張） |" % len(list((out / "capture/keyframes").glob("*.png"))))
    w("| `capture/contact_timeline_*.png` | 每秒 2 格接觸表（%d 頁） |" % len(list((out / "capture").glob("contact_timeline_*.png"))))
    w("| `capture/frames/*.jpg` | 每秒 2 格原尺寸（%d 張） |" % len(list((out / "capture/frames").glob("*.jpg"))))
    for p in (an or {}).get("strip_pages", []):
        w(f"| `{p}` | a2_c002 逐格條帶（每秒 8 格） |")
    sm = (an or {}).get("frames_meta", {}).get("strip") or {}
    w(f"| `strip_a2_c002/frames/*.jpg` | 條帶原尺寸（{sm.get('count', '—')} 格，{sm.get('from', '—')}–{sm.get('to', '—')} 秒＋停格） |")
    w("| `proj/contact_proj_16x9.png` | 關鍵影格：原圖｜投影模擬 v2 |")
    w("| `proj/16x9/*_proj.png`、`*_sheet.png` | 每張關鍵影格的投影模擬 v2、四聯圖（原圖／投影／灰階／綠色弱） |")
    for d in sorted((out / "keyframes_4x3").glob("*x*")) if (out / "keyframes_4x3").exists() else []:
        w(f"| `keyframes_4x3/{d.name}/*.png` | 4:3 關鍵影格（視窗 {d.name.replace('x', '×')}，{len(list(d.glob('*.png')))} 張） |")
        w(f"| `proj/contact_4x3_{d.name}.png`、`proj/{d.name}/*_proj.png` | 4:3 關鍵影格：原圖｜投影模擬 v2 |")
    for p in (an or {}).get("compare_g2", []):
        w(f"| `{p}` | G2 退路試作合成圖（review/G2/*_v04）與 G4 劇場截圖 a2_c002 關鍵影格並排（上原圖、下投影模擬 v2） |")
    w("| `capture/probe_bg/*.png` | 同一格隱藏角色後的背景（量兒童站位背景亮度用） |")
    w("| `g4_playback.mp4` | 播放錄製：固定步長 30 格／秒逐格＋最終混音，1920×1080，H.264＋AAC |")
    w("")
    if pr:
        w("### 操偶線與背景量測（`capture/probe_report.json`）")
        w("")
        s = pr.get("summary") or {}
        rows = pr.get("strings") or []
        if rows:
            w("| cue | t | 扣點 | 線寬 px | ΔL* | ΔL*（投影 v2） |")
            w("|---|---|---|---|---|---|")
            for r in rows:
                w(f"| {r['cue']} | {fmt(r['t'], 2)} | {r['anchor']} | {fmt(r.get('widthPx'), 1)} | {fmt(r.get('deltaL'), 1)} | {fmt(r.get('deltaL_proj'), 1)} |")
            w("")
        kids = pr.get("child_background") or []
        if kids:
            w("兒童站位背景（同一格隱藏角色重畫，取兒童軀幹高度兩側背景，投影模擬 v2 後的相對亮度）：")
            w("")
            w("| cue | t | 關鍵影格 | 角色 | 量測區 px | 背景亮度中位 | p10 |")
            w("|---|---|---|---|---|---|---|")
            for r in kids:
                w(f"| {r.get('cue')} | {fmt(r.get('t'), 2)} | {r.get('key')} | {r.get('actor')} | {r.get('region')} | {fmt(r.get('proj_lum_median'), 3)} | {fmt(r.get('proj_lum_p10'), 3)} |")
            w("")
        if s:
            w("摘要：" + "；".join(f"{k} {v}" for k, v in s.items()))
            w("")
    w("## 3. 光敏")
    w("")
    w("| 報告 | 方法 | 每秒最多變化（明暗／紅色） | 超標區域 | 接近上限（每秒 2–3 次）區域 |")
    w("|---|---|---|---|---|")
    if fr:
        w(f"| `capture/flash_report.json`、`capture/luma_plot.png`、`capture/luma_series.csv` | 逐 cue，{fr['method']} | {fr['max_changes_per_sec']['luma']}／{fr['max_changes_per_sec']['red']} | {fr['flagged_total']} | {fr['near_limit_total']} |")
    if fp:
        w(f"| `flash_playback.json`、`flash_playback_plot.png` | {fp['method']} | {fp['max_changes_per_sec']['luma']}／{fp['max_changes_per_sec']['red']} | {len(fp['flagged'])} | {fp['near_limit_total']} |")
    w("")
    if fp:
        w(f"播放錄製：分析 {fp['frames_analyzed']} 格；全畫面平均線性亮度 {fp['mean_luma_range'][0]}–{fp['mean_luma_range'][1]}；飽和紅色像素比例最大 {fp['max_sat_red_ratio']}。")
        w("")
        w("cue 接縫（前一格→後一格）：")
        w("")
        w("| 接縫 | 時間 s | 平均亮度 前→後 | 區域亮度最大差 |")
        w("|---|---|---|---|")
        for s in fp["cue_seams"]:
            w(f"| {s['from']}→{s['to']} | {s['t']} | {s['mean_luma_before']}→{s['mean_luma_after']} | {s['max_region_luma_delta']} |")
        w("")
        w("接近上限的區域（播放錄製，前 30 筆；px＝1920×1080 上的範圍）：")
        w("")
        w("| 種類 | 區域 | px | 每秒次數 | 1 秒窗起點 s | cue | cue 內秒數 |")
        w("|---|---|---|---|---|---|---|")
        for n in fp["near_limit"][:30]:
            w(f"| {n['type']} | {n['region']} | {n['px']} | {n['count_per_sec']} | {n['window_start']} | {n.get('cue')} | {n.get('cue_t')} |")
        w("")
    w("## 4. 效能（`perf.json`）")
    w("")
    if perf:
        w(f"- {perf['note']}")
        w(f"- 方法：{perf['method']}")
        m = perf["machine"]
        w(f"- 機器：{m['cpu']}，{m['cores']} 核，{m['memGB']} GB，{m['os']}；GPU：{perf['runs'][0]['gpu']}")
        w("")
        w("| 畫質 | 播放中影格數 | 影格時間 中位 ms | p95 ms | p99 ms | 最長 ms | >33.4 ms 格數 | >50 ms 格數 | rAF 回呼 中位 ms | p95 ms | 最長 ms |")
        w("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in perf["runs"]:
            f, c = r["frameIntervalMs"] or {}, r["rafCallbackMs"] or {}
            w(f"| {r['quality']} | {r['playingFrames']} | {fmt(f.get('median'), 2)} | {fmt(f.get('p95'), 2)} | {fmt(f.get('p99'), 2)} | {fmt(f.get('max'), 1)} | {r['over33ms']} | {r['over50ms']} | {fmt(c.get('median'), 2)} | {fmt(c.get('p95'), 2)} | {fmt(c.get('max'), 1)} |")
        w("")
        w("逐 cue（畫質 A）：")
        w("")
        w("| cue | 播放 ms | 影格時間 中位 | p95 | 最長 | >33.4 ms |")
        w("|---|---|---|---|---|---|")
        for k, v in perf["runs"][0]["perCue"].items():
            f = v["frameIntervalMs"] or {}
            w(f"| {k} | {fmt(v['playMs'], 0)} | {fmt(f.get('median'), 2)} | {fmt(f.get('p95'), 2)} | {fmt(f.get('max'), 1)} | {v['over33ms']} |")
        w("")
    w("## 5. 聲音")
    w("")
    if au:
        w(f"- 最終混音 `audio/g4_mix.wav`（48 kHz、立體聲、16-bit，{au['duration_sec']} 秒）；分軌波形與瞬間響度 `audio/g4_mix_plot.png`；數據 `audio/loudness.json`。")
        w(f"- 混音方法：{au['note']}")
        w("")
        w("| 範圍 | 整合響度 LUFS | 真峰值 dBTP | LRA LU |")
        w("|---|---|---|---|")
        f = au["full_playback"]
        w(f"| 整段播放錄製 | {fmt(f['I_LUFS'])} | {fmt(f['TP_dBTP'])} | {fmt(f['LRA_LU'])} |")
        s = au["a2_c002_to_a2_c004"]
        w(f"| a2_c002＋a2_c004（{s['from_sec']}–{s['to_sec']} s） | {fmt(s['I_LUFS'])} | {fmt(s['TP_dBTP'])} | {fmt(s['LRA_LU'])} |")
        for k, v in au["per_cue"].items():
            w(f"| {k} | {fmt(v['I_LUFS'])} | {fmt(v['TP_dBTP'])} | {fmt(v['LRA_LU'])} |")
        w("")
        w(f"樣本峰值 {au['sample_peak_dBFS']} dBFS；削波樣本 {au['clipped_samples']}。")
        w("")
        w(au.get("momentary_note", "") + "上升量的時間＝該 400 ms 窗結束的播放秒數。")
        w("")
        w("| 分軌 | 最大 LUFS（時間 s） | 1 秒內最大上升 LU（時間 s） | 100 ms 最大上升 LU（時間 s） |")
        w("|---|---|---|---|")
        for lab, key in (("總混音", "momentary_full_mix"), ("配樂＋音效（不含配音）", "momentary_music_sfx_only")):
            m = au.get(key)
            if m:
                w(f"| {lab} | {m['max_LUFS']}（{m['max_at_sec']}） | {m['max_rise_within_1s_LU']}（{m['max_rise_within_1s_at_sec']}） | {m['max_rise_per_100ms_LU']}（{m['max_rise_per_100ms_at_sec']}） |")
        w("")
        w("逐句響度：")
        w("")
        w("| 台詞 | 說話者 | 播放時間 s | 配音檔 LUFS | 配音檔真峰值 dBTP | 混音中該句 LUFS | 混音中配音 LUFS | 同時段配樂＋音效 LUFS | 配音−背景 LU |")
        w("|---|---|---|---|---|---|---|---|---|")
        for l in au["lines"]:
            w(f"| {l['id']} | {l['speaker']} | {l['start']}–{l['end']} | {fmt(l['vo_file_I_LUFS'])} | {fmt(l['vo_file_TP_dBTP'])} | {fmt(l['mix_I_LUFS'])} | {fmt(l['vo_in_mix_I_LUFS'])} | {fmt(l['background_I_LUFS'])} | {fmt(l['vo_minus_background_LU'])} |")
        w("")
        w(f"各句配音檔響度差（最大−最小）{au['line_vo_file_I_spread_LU']} LU；混音中各句響度差 {au['line_mix_I_spread_LU']} LU。")
        miss = [e for e in au.get("events", []) if "missing" in e]
        w(f"混音時缺檔：{len(miss)} 個" + ("（" + "、".join(e["missing"] for e in miss) + "）" if miss else "") + "。")
        w("")
    if tx:
        w("### 配音逐字稿差異（`transcripts.md`、`transcripts.json`）")
        w("")
        w(f"- {tx['method']}")
        if (ROOT / "review/G3/tone_check_yi.json").exists():
            w("- 相關量測檔：`review/G3/tone_check_yi.json`（G3 配音代理對 a2_c002_01「咦」的 F0 走勢量測）。")
        w("")
        w("| 台詞 | 來源 | 模型 | 字錯率 CER | 拼音錯率 PER（含聲調） | 差異（劇本→轉寫） |")
        w("|---|---|---|---|---|---|")
        for r in tx["rows"]:
            for src in ("vo", "mix"):
                for mname, m in (r.get(src) or {}).items():
                    diffs = "；".join(f"{d['ref'] or '∅'}→{d['hyp'] or '∅'}（{d['kind']}）" for d in m["diffs"]) or "無"
                    w(f"| {r['id']} | {'配音檔' if src == 'vo' else '最終混音該句'} | {mname} | {m['cer']} | {m['per']} | {diffs} |")
        w("")
    w("## 6. 安全界線相關量測（`safety_data.json`）")
    w("")
    if sa:
        w(f"- cue 檔使用的操偶線扣點：{'、'.join(sa['string_anchors_in_cues'])}")
        w(f"- 扣點定義（`assets/final/rig/ale_attach.json`，primary）：" + "；".join(f"{k}＝{v['part']} {v['local_px']}" for k, v in sa["attach_points_primary"].items()))
        w(f"- 有線的量測格數 {sa['probe_frames_with_strings']}；線路徑到阿樂叔叔頭部框的最短距離 {sa['string_path_min_dist_to_ale_head_box_px']} px（逐扣點：" + "；".join(f"{k} {v['min_dist_to_head_box_px']} px（{v.get('at')}）／{v['frames']} 格" for k, v in sa["per_anchor"].items()) + "）")
        w(f"- 線路徑與兒童立牌外框相交：{sa['string_path_intersects_child_box_count']} 次" + ("（" + "；".join(f"{h['cue']} {h['t']}s {h['anchor']}→{h['kid']}" for h in sa['string_path_intersects_child_box'][:10]) + "）" if sa['string_path_intersects_child_box'] else ""))
        w(f"- 量測方法：{sa['probe_method']}")
        n = sa["required_narration_1"]
        w(f"- 必要旁白一：CLAUDE.md「{n['claude_md']}」；劇本 v03 與 CLAUDE.md 相同＝{n['script_equals_claude_md']}；cue 檔（去掉手動換行）與劇本相同＝{n['cue_equals_script']}")
        w(f"- 字幕：每行最多 {sa['subtitle_max_chars_per_row']} 字、每頁最多 {sa['subtitle_max_rows_per_page']} 行")
        w("")
        w("| 台詞 | 頁數 | 字幕分頁 |")
        w("|---|---|---|")
        for s in sa["subtitles"]:
            w(f"| {s['id']} | {s['pages']} | " + " ‖ ".join(" / ".join(p) for p in s["rows"]) + " |")
        w("")
        w(f"- `app/dist/app.js` 內 getUserMedia 出現 {sa['app_js_getUserMedia_count']} 次、mediaDevices {sa['app_js_mediaDevices_count']} 次；擷取時外部網路請求 {sa['capture_external_requests']} 個；主控台錯誤／警告 {sa['capture_console_errors']} 則。")
        w("")
    w("## 7. 其他檔案")
    w("")
    w("| 檔案 | 內容 |")
    w("|---|---|")
    w("| `timeline.json` | 解析後的 cue 時間軸（台詞起訖、字幕分頁、動畫、音效、配樂）與播放排程 |")
    w("| `capture/capture.json` | 擷取參數、逐格清單、主控台錯誤、外部請求、最終狀態 |")
    w("| `capture/probe.json` | 每個關鍵影格與每秒一格的操偶線螢幕路徑、線寬、角色外框、頭部框 |")
    w("| `probe_dense.json` | 播放錄製每秒 10 次的操偶線螢幕路徑、角色外框、頭部框 |")
    w("| `analysis.json` | 本頁數字的彙整來源 |")
    w("")
    w("未驗證（代理無法量測）：聽感、實際投影機與教室燈光、學校 Windows 筆電效能。")
    (out / "INDEX.md").write_text("\n".join(x for x in L if x is not None) + "\n", encoding="utf-8")
    print(f"[g4pack.py] INDEX.md → {out / 'INDEX.md'}")


if __name__ == "__main__":
    cmd, out = sys.argv[1], Path(sys.argv[2]).resolve()
    if cmd == "analyze":
        analyze(out)
    elif cmd == "index":
        index(out)
    else:
        raise SystemExit(f"未知指令 {cmd}")
