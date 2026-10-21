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
  7. G4 修正第 1 輪新增：條帶節拍標示、呼吸起伏、字幕底板與阿樂膝線／腳的重疊、換姿勢放大條帶、前臂裁切、
     光敏細格（32×18）與投影 v2 分析、教師停格配樂響度、段落響度差、字幕與語音時間差、a2_c004 兒童是否在安全框內
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
def strip(out: Path, meta: dict, tl: dict | None = None):
    """a2_c002 每秒 8 格條帶；揮手與扯膝的節拍（app/src/stage/beats.ts）標在「該拍之後的第一格」：紅框＋標籤"""
    sd = out / "strip_a2_c002"
    files = sorted((sd / "frames").glob("*.jpg"))
    if not files:
        return []
    beats = []
    if tl:
        c = next((c for c in tl["cues"] if c["id"] == "a2_c002"), None)
        beats = (c or {}).get("beats", [])
    times = [float(f.stem.split("_")[-1]) for f in files]
    marks = {}
    for i, bt in enumerate(sorted(beats, key=lambda x: x["t"])):
        k = next((j for j, t in enumerate(times) if t >= bt["t"] - 1e-6), None)
        if k is not None:
            marks.setdefault(k, []).append(f"{i + 1}. {bt['label']}（{bt['t']:.2f}s）")
    cols, tw = 8, 300
    th = int(tw * 9 / 16)
    per_page = cols * 6
    pages = []
    for p in range(0, len(files), per_page):
        chunk = files[p:p + per_page]
        rows = (len(chunk) + cols - 1) // cols
        W = 10 + cols * (tw + 8)
        H = 50 + rows * (th + 48)
        sheet = Image.new("RGB", (W, H), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        s_ = meta.get("strip") or {}
        d.text((10, 10), f"a2_c002 逐格條帶：每秒 {s_.get('fps', 8)} 格，從 strings.drop 起點 {s_.get('from')} 秒到停格（第 {p // per_page + 1} 頁）；紅框＝節拍時間點之後的第一格",
               font=font(22), fill=(240, 236, 228))
        for i, f in enumerate(chunk):
            gi = p + i
            x, y = 10 + (i % cols) * (tw + 8), 50 + (i // cols) * (th + 48)
            sheet.paste(Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
            t = times[gi]
            d.text((x, y + th + 3), f"t={t:.3f}s" + ("（停格）" if f is files[-1] else ""), font=font(16), fill=(200, 196, 188))
            if gi in marks:
                d.rectangle([x - 2, y - 2, x + tw + 1, y + th + 1], outline=(230, 40, 40), width=4)
                d.text((x, y + th + 22), "／".join(marks[gi]), font=font(13), fill=(255, 120, 110))
        path = sd / f"strip_a2_c002_8fps_p{len(pages) + 1:02d}.png"
        sheet.save(path)
        pages.append(rel(path, out))
    return pages


def beat_report(out: Path, tl: dict):
    """節拍時間點（依序遞增）與條帶上對應的格（G4 修正第 17、18 項）"""
    c = next((c for c in tl["cues"] if c["id"] == "a2_c002"), None)
    if not c:
        return None
    sd = out / "strip_a2_c002" / "frames"
    times = sorted(float(f.stem.split("_")[-1]) for f in sd.glob("*.jpg")) if sd.exists() else []
    res = {}
    for anim in ("puppet.waveTry", "puppet.kneeTug"):
        bs = [b for b in c.get("beats", []) if b["anim"] == anim]
        rows = []
        for b in bs:
            k = next((t for t in times if t >= b["t"] - 1e-6), None)
            rows.append({"label": b["label"], "t": b["t"], "strip_frame_t": k})
        ts = [r["t"] for r in rows]
        res[anim] = {"beats": rows, "increasing": all(ts[i] < ts[i + 1] for i in range(len(ts) - 1)),
                     "strip_frames_increasing": all((rows[i]["strip_frame_t"] or 0) <= (rows[i + 1]["strip_frame_t"] or 0) for i in range(len(rows) - 1))}
    tb = tl.get("beatTables", {})
    w, k = tb.get("waveTry", {}), tb.get("kneeTug", {})
    if w:
        res["checks"] = {
            "wave_duration_s": round(w["waveEnd"] - w["waveStart"], 3), "wave_ge_0_6s": w["waveEnd"] - w["waveStart"] >= 0.6,
            "wave_cycles": round((w["waveEnd"] - w["waveStart"]) * w["waveHz"], 2),
            "confused_after_pull_s": round(w["confused"] - w["pullStart"], 3), "confused_after_pull_ge_0_15s": w["confused"] - w["pullStart"] >= 0.15,
            "taut_after_wave": w["tautStart"] >= w["waveEnd"],
        }
    if k:
        res.setdefault("checks", {}).update({
            "half_stand_hold_s": round(k["tautStart"] - k["riseEnd"], 3), "half_stand_ge_0_5s": k["tautStart"] - k["riseEnd"] >= 0.5,
            "lift_after_taut": k["liftStart"] >= k["tautEnd"], "grab_after_sway_peak": k["grabStart"] >= k["swayPeak"],
        })
    return res


def strip_measures(out: Path, tl: dict):
    """條帶每一格的量測：小晴呼吸起伏（第 25 項）、字幕底板與阿樂膝前線／被提起的腳重疊（第 26 項）"""
    sp = out / "strip_a2_c002" / "strip_probe.json"
    if not sp.exists():
        return None
    frames = json.loads(sp.read_text(encoding="utf-8"))["frames"]
    c = next((c for c in tl["cues"] if c["id"] == "a2_c002"), None)
    # 呼吸：鏡頭與姿勢都不變的時段（第一句台詞期間），小晴外框高度的峰對峰值
    l1 = c["lines"][0]
    win = [f for f in frames if l1["start"] + 0.3 <= f["t"] <= l1["end"] - 0.3]
    hs = [a["box"][3] - a["box"][1] for f in win for a in f["actors"] if a["id"] == "xiaoqing" and a.get("visible")]
    breath = {"window_s": [round(l1["start"] + 0.3, 2), round(l1["end"] - 0.3, 2)], "frames": len(hs),
              "box_height_px_min": round(min(hs), 1) if hs else None, "box_height_px_max": round(max(hs), 1) if hs else None,
              "peak_to_peak_px": round(max(hs) - min(hs), 1) if hs else None,
              "amplitude_px": round((max(hs) - min(hs)) / 2, 1) if hs else None,
              "note": "外框高度＝立牌腳底到頭頂（含透明邊）；呼吸是以腳底為支點的伸縮，頭頂的上下起伏＝高度變化"}
    # 重疊：從第一句開始到停格，每一格有字幕時
    rows, hits = [], 0
    t_from = l1["start"]
    for f in frames:
        if f["t"] < t_from - 1e-6 or not f.get("sub"):
            continue
        x0, y0, x1, y1 = f["sub"]
        ale = next((a for a in f["actors"] if a["id"] == "ale"), None)
        knee = next((st for st in f["strings"] if st.get("anchor") == "knee" and st.get("visible")), None)
        ov_path = 0
        if knee and knee.get("path"):
            ov_path = sum(1 for (px, py) in knee["path"] if x0 <= px <= x1 and py >= y0)
        ring_ov = False
        if knee and knee.get("ringPx"):
            rx, ry = knee["ringPx"]
            r = knee.get("ringRadiusPx") or 0
            ring_ov = (x0 - r <= rx <= x1 + r) and (ry + r >= y0)
        part_ov = {}
        for pn in ("shin_l", "thigh_l"):
            bb = ((ale or {}).get("parts") or {}).get(pn)
            if bb:
                ox = min(bb[2], x1) - max(bb[0], x0)
                oy = min(bb[3], y1) - max(bb[1], y0)
                part_ov[pn] = round(oy, 1) if ox > 0 and oy > 0 else 0
        bad = ov_path > 0 or ring_ov or any(v > 0 for v in part_ov.values())
        hits += bad
        rows.append({"t": f["t"], "sub": [round(v) for v in f["sub"]], "knee_path_pts_in_sub": ov_path, "knee_ring_overlap": ring_ov,
                     "leg_box_overlap_px": part_ov, "overlap": bad})
    over = {"rule": "第一句台詞起到停格，有字幕的每一格：字幕底板（DOM 外框）不和膝前線路徑（引擎實際畫的中心線 37 點）、膝前紙環、被提起那條腿（thigh_l、shin_l 部件外框，含透明邊）重疊",
            "frames_with_subtitle": len(rows), "frames_overlapping": hits, "rows": rows}
    res = {"breathing_xiaoqing": breath, "subtitle_vs_knee": over}
    (out / "strip_a2_c002" / "strip_measures.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def flip_sheets(out: Path):
    """換姿勢（紙片翻面）前後每秒 30 格放大條帶；寬度比＝該格外框寬 ÷ 翻面前的寬度（第 19、27 項：不能只剩細縫）"""
    fd = out / "strip_a2_c002" / "flip"
    fj = fd / "flips.json"
    if not fj.exists():
        return []
    flips = json.loads(fj.read_text(encoding="utf-8"))
    made = []
    for fl in flips:
        frs = [f for f in fl["frames"] if f.get("box")]
        if not frs:
            continue
        x0 = max(0, int(min(f["box"][0] for f in frs)) - 30)
        y0 = max(0, int(min(f["box"][1] for f in frs)) - 30)
        x1 = min(1920, int(max(f["box"][2] for f in frs)) + 30)
        y1 = min(1080, int(max(f["box"][3] for f in frs)) + 30)
        w0 = frs[0]["box"][2] - frs[0]["box"][0]
        cw = 160
        ch = int(cw * (y1 - y0) / max(1, x1 - x0))
        sheet = Image.new("RGB", (len(frs) * (cw + 6) + 10, ch + 88), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        d.text((8, 6), f"{fl['target']} 換姿勢 → {fl['pose']}（{fl['start']:.2f}–{fl['end']:.2f} s，翻面前 0.2 秒到結束後 0.4 秒，每秒 30 格；數字＝寬度比；眼＝眼睛換片狀態）", font=font(18), fill=(240, 236, 228))
        ratios = []
        for i, f in enumerate(frs):
            im = Image.open(fd / f["file"]).convert("RGB").crop((x0, y0, x1, y1)).resize((cw, ch), Image.LANCZOS)
            x = 10 + i * (cw + 6)
            sheet.paste(im, (x, 34))
            r = (f["box"][2] - f["box"][0]) / max(1, w0)
            ratios.append(r)
            d.text((x, ch + 38), f"{f['t']:.3f}s ×{r:.2f}", font=font(14), fill=(200, 196, 188))
            if f.get("eyes"):
                tag = "（翻面中）" if fl["start"] <= f["t"] <= fl["end"] else ("（結束後≤0.3s）" if fl["end"] < f["t"] <= fl["end"] + 0.3 + 1e-6 else "")
                d.text((x, ch + 58), f"眼：{EYE_ZH.get(f['eyes'], f['eyes'])}{tag}", font=font(13), fill=(255, 200, 150) if f["eyes"] != "open" else (170, 200, 170))
        path = fd / f"flip_{fl['target']}_{fl['start']:06.2f}.png"
        sheet.save(path)
        eyes_after = [f.get("eyes") for f in frs if fl["start"] - 0.2 - 1e-6 <= f["t"] <= fl["end"] + 0.3 + 1e-6]
        made.append({"target": fl["target"], "pose": fl["pose"], "start": fl["start"], "end": fl["end"], "sheet": rel(path, out),
                     "min_width_ratio": round(min(ratios), 3), "frames": len(frs),
                     "eyes_open_from_start-0.2_to_end+0.3": all(e == "open" for e in eyes_after if e is not None) if eyes_after else None})
    return made


def forearm_crops(out: Path):
    """阿樂叔叔前臂件裁切（第 27 項：補線稿與紙紋、修掉肘部袖口零碎紙邊）：a2_c002 中／後、a2_c004 前／中關鍵影格"""
    pj = out / "capture" / "probe.json"
    if not pj.exists():
        return None
    probes = json.loads(pj.read_text(encoding="utf-8"))["probes"]
    tiles = []
    for pr in probes:
        if pr["cueId"] not in ("a2_c002", "a2_c004") or not pr.get("frame") or pr.get("key") not in ("mid", "after", "before"):
            continue
        ale = next((a for a in pr["actors"] if a["id"] == "ale"), None)
        if not ale or not ale.get("parts"):
            continue
        im = Image.open(out / "capture" / pr["frame"]).convert("RGB")
        for pn in ("forearm_r", "forearm_l"):
            bb = ale["parts"].get(pn)
            if not bb:
                continue
            box = (max(0, int(bb[0]) - 20), max(0, int(bb[1]) - 20), min(1920, int(bb[2]) + 20), min(1080, int(bb[3]) + 20))
            tiles.append((im.crop(box), f"{pr['cueId']} {pr['t']:.2f}s {pn}"))
    if not tiles:
        return None
    th = 300
    widths = [int(t.width * th / t.height) for t, _ in tiles]
    sheet = Image.new("RGB", (sum(widths) + 12 * len(tiles) + 10, th + 40), (24, 22, 20))
    d = ImageDraw.Draw(sheet)
    x = 10
    for (t, lab), w in zip(tiles, widths):
        sheet.paste(t.resize((w, th), Image.LANCZOS), (x, 8))
        d.text((x, th + 12), lab, font=font(14), fill=(200, 196, 188))
        x += w + 12
    path = out / "capture" / "forearm_crops.png"
    sheet.save(path)
    return rel(path, out)


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
    """app/src/audio/ducking.ts 的 duckingPlan（同參數）；另讀教師停格的 HOLD_MUSIC_RATIO、HOLD_TC"""
    src = (ROOT / "app/src/audio/ducking.ts").read_text(encoding="utf-8")
    c = {k: float(re.search(rf"export const {k} = ([\d.]+)", src).group(1)) for k in
         ("DUCK_LEVEL", "DUCK_LEAD", "DUCK_TC_DOWN", "DUCK_RELEASE", "DUCK_TC_UP", "DUCK_BRIDGE", "HOLD_MUSIC_RATIO", "HOLD_TC")}
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
        plan, dk = duck_plan(intervals)
        # 教師停格（engine.ts scheduleAudio）：劇情段落播完、停住等老師時，配樂降到基準音量 × HOLD_MUSIC_RATIO
        if c["kind"] == "scene" and not c.get("autoAdvance"):
            bus_level.target(c["musicLevel"] * dk["HOLD_MUSIC_RATIO"], G + c["duration"], dk["HOLD_TC"])
        cur_d = duck.at(G)
        duck.cancel(G); duck.set(cur_d, G)
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
    mom_bg_list = momentary(bg)
    mom_bg = rises(mom_bg_list)
    mom_full = rises(mom) if len(mom) > 10 else None
    # 教師停格（G3 修正第 11 項）：停住後第 3 秒的瞬間響度 ≤ −35 LUFS
    holds = []
    for s_ in tl["schedule"]:
        if s_["kind"] != "scene" or s_["hold"] < 3.2:
            continue
        h0 = s_["start"] + s_["duration"]
        def mat(series, t):
            v = [m[1] for m in series if abs(m[0] - t) < 0.051]
            return round(v[0], 1) if v else None
        after = [m[1] for m in mom if h0 + 3.0 - 1e-6 <= m[0] <= h0 + s_["hold"] + 1e-6]
        holds.append({"cue": s_["id"], "hold_from_sec": round(h0, 3), "hold_sec": s_["hold"], "momentary_at_hold_start_LUFS": mat(mom, round(h0 + 0.4, 1)),
                      "momentary_at_3s_LUFS": mat(mom, round(h0 + 3.0, 1)), "momentary_max_after_3s_LUFS": round(float(max(after)), 1) if after else None,
                      "pass_le_-35": bool(max(after) <= -35.0) if after else None})
    # 段落響度差（G3 修正第 12 項）：全部段落、有台詞的段落、各句台詞在混音中的整合響度
    cue_lines = {c["id"]: c["lines"] for c in tl["cues"]}
    i_all = {k: v["I_LUFS"] for k, v in per_cue.items() if v.get("I_LUFS") is not None}
    i_dlg = {k: v for k, v in i_all.items() if cue_lines.get(k)}
    # 聲音代理建議的分層（review/G3/loudness_scope_r2.json proposed_rule）：素材檔、各句對白、主奏段（無台詞 cue）、劇情襯底段（有台詞 cue 扣掉每句前 0.3 秒到後 0.5 秒）
    feat, under = {}, {}
    for s_ in tl["schedule"]:
        if s_["duration"] < 1.0:
            continue
        x0 = int(s_["start"] * SR)
        seg_ = mixed[x0:x0 + int(s_["duration"] * SR)]
        ls = cue_lines.get(s_["id"]) or []
        if not ls:
            v = ebur(seg_)["I_LUFS"]
            if v is not None:
                feat[s_["id"]] = v
        else:
            keep = np.ones(len(seg_), dtype=bool)
            for l_ in ls:
                keep[max(0, int((l_["start"] - 0.3) * SR)):max(0, int((l_["end"] + 0.5) * SR))] = False
            if keep.sum() > SR:
                v = ebur(seg_[keep])["I_LUFS"]
                if v is not None:
                    under[s_["id"]] = v
    rng = lambda d_: round(max(d_.values()) - min(d_.values()), 1) if len(d_) > 1 else None
    dec_file = ROOT / "review" / "G3" / "loudness_decision.json"
    decided = json.loads(dec_file.read_text(encoding="utf-8")) if dec_file.exists() else None
    spread = {
        "vo_files_lu": round(max(vals) - min(vals), 1) if vals else None,
        "featured_music_lu": rng(feat), "featured_music_I_LUFS": feat,
        "underscore_lu": rng(under), "underscore_I_LUFS": under,
        "layers_note": "分層依 review/G3/loudness_scope_r2.json proposed_rule：素材檔（配音逐句檔）、各句對白在混音中、主奏段（沒有台詞的 cue 整段）、劇情襯底段（有台詞的 cue 扣掉每句台詞前 0.3 秒到後 0.5 秒）；各自最大−最小 ≤ 2 LU。",
        "all_cues_lu": round(max(i_all.values()) - min(i_all.values()), 1) if i_all else None,
        "dialogue_cues_lu": round(max(i_dlg.values()) - min(i_dlg.values()), 1) if len(i_dlg) > 1 else None,
        "dialogue_lines_lu": round(max(mvals) - min(mvals), 1) if mvals else None,
        "per_cue_I_LUFS": i_all,
        "rule": "各段落整合響度最大−最小 ≤ 2 LU（±1 LU）",
        "pass_all_cues": (max(i_all.values()) - min(i_all.values()) <= 2.0) if i_all else None,
        "pass_dialogue_lines": (max(mvals) - min(mvals) <= 2.0) if mvals else None,
        "decision": (decided or {}).get("decision") or "待主線裁決（REVIEW.md）：聲音代理建議的規則見 review/G3/loudness_scope_r2.json proposed_rule（素材檔、各句對白、主奏段、劇情襯底段四層各 ≤ 2 LU，整段 cue 只列參考）；主線定案後寫 review/G3/loudness_decision.json，再跑 `g4_review_pack.py decision <驗收包>` 更新本欄與 INDEX.md",
        "decision_source": rel(dec_file, ROOT) if decided else None,
    }
    spread["pass_layers"] = {k: (spread[k] is not None and spread[k] <= 2.0) for k in ("vo_files_lu", "dialogue_lines_lu", "featured_music_lu", "underscore_lu")}
    res = {
        "note": "依 timeline.json 的 cue 時間與教師按鍵間隔假設，照引擎混音規則（三條匯流排、配樂基準音量 setTargetAtTime 0.35 s、對白避讓 duckingPlan、教師停格時配樂降到基準 ×HOLD_MUSIC_RATIO、交叉淡入淡出、換 cue 停台詞與音效 30 ms 淡出）以 48 kHz 離線混音；總音量 1.0；開頭靜音 0 ms。",
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
        "freeze_holds": holds,
        "freeze_rule": "教師停格（劇情段落播完、等老師按鍵）：配樂在停住後 3 秒內降到 ≤ −35 LUFS（瞬間響度，400 ms 窗）",
        "segment_spread_lu": spread,
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


# ====================================================================== 5b. 字幕與語音時間差、光敏細格與投影、兒童安全框
def voice_onsets(path: Path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "silencedetect=noise=-45dB:d=0.1", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    out = []
    if not starts or starts[0] > 0.01:
        out.append(0.0)
    return out + ends


def subtitle_sync(out: Path, tl: dict):
    """字幕頁起點 − 該頁語音起點（G3 修正第 14 項；同 tools/vo_subsync.py 的方法，但直接用本驗收包的 timeline.json）"""
    LO, HI = -0.8, 0.1
    rows = []
    for c in tl["cues"]:
        for l in c["lines"]:
            if l["audioId"] not in tl["audio"]:
                continue
            src = ROOT / tl["audio"][l["audioId"]]["source"]
            ons = voice_onsets(src)
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
    res = {"method": "ffmpeg silencedetect noise=−45 dB、d=0.1 s 找配音檔的語音起點（第 1 頁＝第一個起點；之後各頁＝頁起點前後最接近的停頓後起點）；差值＝字幕頁起點 − 語音起點",
           "range_s": [LO, HI], "rows": rows, "all_pass": all(r["pass"] for r in rows)}
    (out / "subtitle_sync.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def _region_stats(rgb_small, gw, gh):
    a = ca.to_linear(rgb_small.astype(np.float32) / 255.0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    ssum = r + g + b
    sat = (r / np.maximum(ssum, 1e-6) >= 0.8) & (r > 0.05)
    redv = np.where(sat, np.maximum(0.0, r - g - b) * 320.0, 0.0)
    H, W = lum.shape
    bh, bw = H // gh, W // gw
    reg = lambda x: x[: bh * gh, : bw * gw].reshape(gh, bh, gw, bw).mean(axis=(1, 3))
    return reg(lum), reg(redv), float(lum.mean())


def flash_variants(out: Path, seq):
    """光敏補充分析（G4 修正第 30 項）：細格 32×18（每區約占畫面 0.17%）、投影 v2 模擬後 16×9 與 32×18；方法同 capture_analyze.py"""
    variants = {"fine_32x18": (32, 18, False), "proj_16x9": (16, 9, True), "proj_32x18": (32, 18, True)}
    data = {k: {"L": [], "R": [], "M": []} for k in variants}
    times = []
    where = {round(t, 4): (cue, ct) for t, p, cue, ct in seq}
    cache_key, cache_val = None, None
    for t, p, cue, ct in seq:
        if str(p) != cache_key:
            im = np.asarray(Image.open(p).convert("RGB").resize((640, 360), Image.BOX))
            pv = projsim.projector(im, "v2")
            cache_val = {k: _region_stats(pv if proj else im, gw, gh) for k, (gw, gh, proj) in variants.items()}
            cache_key = str(p)
        times.append(t)
        for k in variants:
            L, R, M = cache_val[k]
            data[k]["L"].append(L); data[k]["R"].append(R); data[k]["M"].append(M)
    res = {}
    for k, (gw, gh, proj) in variants.items():
        L, R = np.array(data[k]["L"]), np.array(data[k]["R"])
        worst = {"luma": 0, "red": 0}
        flagged, near = [], []
        for gy in range(gh):
            for gx in range(gw):
                for kind, arr, th, dark in (("luma", L, ca.LUMA_TH, ca.LUMA_DARK), ("red", R, ca.RED_TH, None)):
                    ev = ca.transitions(times, list(arr[:, gy, gx]), th, dark)
                    c, at = ca.max_per_second(ev)
                    worst[kind] = max(worst[kind], c)
                    if c >= 2:
                        cue, ct = where.get(round(at, 4), (None, None)) if at is not None else (None, None)
                        rec = {"type": kind, "region": f"x{gx}_y{gy}", "px": [gx * 1920 // gw, gy * 1080 // gh, (gx + 1) * 1920 // gw, (gy + 1) * 1080 // gh],
                               "count_per_sec": c, "window_start": at, "cue": cue, "cue_t": ct}
                        (flagged if c > ca.LIMIT_PER_SEC else near).append(rec)
        wc, _ = ca.max_per_second(ca.transitions(times, data[k]["M"], ca.LUMA_TH, ca.LUMA_DARK))
        res[k] = {"grid": [gw, gh], "projector_v2": proj, "max_changes_per_sec": worst, "full_frame_luma_max_per_sec": wc,
                  "flagged": flagged, "near_limit_3": [n for n in near if n["count_per_sec"] == 3],
                  "near_limit_total": len(near), "near_limit_3_total": sum(1 for n in near if n["count_per_sec"] == 3)}
    rep_ = {"method": "縮成 640×360 後分析；投影 v2＝projsim.py projector(v2) 套在縮圖上；門檻同 capture_analyze.py",
            "variants": res}
    (out / "flash_variants.json").write_text(json.dumps(rep_, ensure_ascii=False, indent=1), encoding="utf-8")
    return rep_


def kids_in_frame(out: Path):
    """a2_c004 每一格（播放錄製每秒 10 次的 probe）兩個孩子的頭與上半身是否在 90% 安全框內（G4 修正第 24、32 項）"""
    pd = out / "probe_dense.json"
    if not pd.exists():
        return None
    probes = json.loads(pd.read_text(encoding="utf-8"))["probes"]
    SX0, SY0, SX1, SY1 = 96, 54, 1824, 1026
    res = {"rule": "頭（外框上 30%）與上半身（外框上 55%）完整落在 90% 安全框 [96, 54, 1824, 1026] 內；外框含立牌透明邊與卡紙側邊（比可見的人略大）",
           "cues": {}}
    for cue in ("a2_c002", "a2_c004"):
        rows = [p for p in probes if p["cueId"] == cue]
        bad = []
        for p in rows:
            for kid in ("xiaoqing", "xiaoyu"):
                a = next((x for x in p["actors"] if x["id"] == kid), None)
                if not a or not a.get("visible"):
                    bad.append({"t": p["t"], "kid": kid, "why": "不在畫面"})
                    continue
                x0, y0, x1, y1 = a["box"]
                ub = y0 + (y1 - y0) * 0.55
                if not (x0 >= SX0 and x1 <= SX1 and y0 >= SY0 and ub <= SY1):
                    bad.append({"t": p["t"], "kid": kid, "box": [round(v) for v in a["box"]]})
        res["cues"][cue] = {"probes": len(rows), "frames_outside": len(bad), "examples": bad[:10]}
    (out / "kids_in_frame.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


# ====================================================================== 5c. G4 修正第 2 輪：眨眼、操偶線鬆垂弧、站起與扶桌、a2_c004 小動作
KIDS = ("xiaoqing", "xiaoyu")
EYE_ZH = {"open": "睜", "half": "半閉", "closed": "閉", None: "—"}


def kid_face_crop(img, box, h_out=200, eyes=None):
    """有眼睛換片範圍（probe eyesBox）時：以兩眼為中心放大（左右各加 35%、上下各加 60%）；沒有時用兒童立牌外框的上 34%（頭部）"""
    if eyes:
        ex0, ey0, ex1, ey1 = eyes
        w_, h_ = ex1 - ex0, ey1 - ey0
        box_ = (ex0 - 0.35 * w_, ey0 - 0.6 * h_, ex1 + 0.35 * w_, ey1 + 0.6 * h_)
        c = img.crop(tuple(int(round(v)) for v in (max(0, box_[0]), max(0, box_[1]), min(img.width, box_[2]), min(img.height, box_[3]))))
        if c.width >= 2 and c.height >= 2:
            return c.resize((max(1, int(c.width * h_out / c.height)), h_out), Image.LANCZOS)
    x0, y0, x1, y1 = box
    hh = y1 - y0
    c = img.crop((int(max(0, x0)), int(max(0, y0)), int(min(img.width, x1)), int(min(img.height, y0 + 0.34 * hh))))
    if c.width < 2 or c.height < 2:
        return Image.new("RGB", (h_out, h_out), (40, 36, 32))
    return c.resize((max(1, int(c.width * h_out / c.height)), h_out), Image.LANCZOS)


def _flip_windows(tl):
    out = []
    for c in tl["cues"]:
        for a in c["anims"]:
            if a["name"] == "puppet.pose":
                out.append({"cue": c["id"], "target": a["target"], "pose": a["params"].get("pose"), "start": a["start"], "end": a["end"]})
    return out


def blink_check(out: Path, tl: dict):
    """第 1、5、9、10 項：眨眼與翻面錯開、兩眼同時閉。
    - 翻面窗：每段 puppet.pose 起點前 0.2 秒到結束後 0.3 秒，播放錄製每一格該角色 eyes 都要是 open
    - 37.9–38.1 秒（驗收意見指定）：從 g4_playback.mp4 每 1/30 秒抽格，放大兩個孩子的頭並標出換片狀態
    - 全片所有孩子眨眼格（eyes≠open）放大：眼睛換片是一張圖同時蓋兩眼（素材驗證見 review/G4/art/blink_check_r2.json）"""
    fj = out / "faces_playback.json"
    if not fj.exists():
        return None
    data = json.loads(fj.read_text(encoding="utf-8"))
    frames = data["frames"]
    res = {"rule": "翻面窗＝puppet.pose 起點前 0.2 秒到結束後 0.3 秒，該角色 eyes 一律 open（G4 修正第 2 輪第 10 項）；眼睛換片一張圖同時蓋兩眼，所以只會兩眼同時半閉／閉",
           "flips": [], "blinks": [], "window_37_9_38_1": None}
    by_cue = {}
    for f in frames:
        by_cue.setdefault(f["cueId"], []).append(f)
    for w in _flip_windows(tl):
        rows = [f for f in by_cue.get(w["cue"], []) if w["start"] - 0.2 - 1e-6 <= f["t"] <= w["end"] + 0.3 + 1e-6]
        bad = [{"t": f["t"], "eyes": (f["faces"].get(w["target"]) or {}).get("eyes")} for f in rows if (f["faces"].get(w["target"]) or {}).get("eyes") != "open"]
        after = [f for f in rows if w["end"] < f["t"] <= w["end"] + 0.3 + 1e-6]
        nxt = next((f["t"] for f in by_cue.get(w["cue"], []) if f["t"] > w["end"] and (f["faces"].get(w["target"]) or {}).get("eyes") != "open"), None)
        res["flips"].append({**w, "frames_checked": len(rows), "frames_after_end_0_3s": len(after), "not_open": bad, "all_open": not bad,
                             "first_blink_after_end_s": round(nxt - w["end"], 3) if nxt is not None else None})
    # 眨眼段（孩子）
    runs = {}
    for f in frames:
        for kid in KIDS:
            e = (f["faces"].get(kid) or {}).get("eyes")
            key = (f["cueId"], kid)
            if e and e != "open":
                r = runs.get(key)
                if r and r[-1]["k1"] == f["k"] - 1:
                    r[-1]["k1"] = f["k"]; r[-1]["t1"] = f["t"]; r[-1]["states"].append(e)
                else:
                    runs.setdefault(key, []).append({"cue": f["cueId"], "kid": kid, "k0": f["k"], "k1": f["k"], "t0": f["t"], "t1": f["t"], "playT0": f["playT"], "states": [e]})
    allruns = sorted([r for v in runs.values() for r in v], key=lambda r: r["playT0"])
    res["blinks"] = [{k: r[k] for k in ("cue", "kid", "t0", "t1", "playT0", "states")} for r in allruns]
    # 全片孩子眨眼格放大（工作資料夾的逐格原圖）
    vdir = out / "_work" / "video"
    tiles = []
    fidx = {(f["cueId"], f["k"]): f for f in frames}
    for r in allruns:
        for k in range(r["k0"], r["k1"] + 1):
            f = fidx.get((r["cue"], k))
            p = vdir / r["cue"] / f"{k:05d}.jpg"
            if not f or not p.exists() or r["kid"] not in f["boxes"]:
                continue
            im = Image.open(p).convert("RGB")
            tiles.append((kid_face_crop(im, f["boxes"][r["kid"]], 120, (f.get("eyes") or {}).get(r["kid"])), f"{f['playT']:.3f}s {r['cue']} {r['kid']} {EYE_ZH.get((f['faces'].get(r['kid']) or {}).get('eyes'))}"))
    if tiles:
        cols, cw, ch = 8, 230, 120
        rows_n = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (cw + 8) + 10, rows_n * (ch + 26) + 44), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        d.text((10, 8), f"全片孩子眨眼格（播放錄製每秒 30 格中 eyes≠open 的每一格，{len(tiles)} 格）：以眼睛換片範圍為中心放大，標 g4_playback.mp4 秒數與換片狀態", font=font(20), fill=(240, 236, 228))
        for i, (im, lab) in enumerate(tiles):
            x, y = 10 + (i % cols) * (cw + 8), 40 + (i // cols) * (ch + 26)
            sheet.paste(im.crop((0, 0, min(cw, im.width), ch)), (x + max(0, (cw - im.width) // 2), y))
            d.text((x, y + ch + 3), lab, font=font(13), fill=(200, 196, 188))
        path = out / "blink" / "kids_blink_frames.png"
        path.parent.mkdir(exist_ok=True)
        sheet.save(path)
        res["blink_frames_sheet"] = rel(path, out)
        res["blink_frames"] = len(tiles)
    # 37.9–38.1 秒：從 mp4 抽格
    mp4 = out / "g4_playback.mp4"
    if mp4.exists():
        k0, k1 = int(round(37.9 * FPS)), int(round(38.1 * FPS))
        tdir = out / "blink" / "mp4_37.9-38.1"
        tdir.mkdir(parents=True, exist_ok=True)
        for f in tdir.glob("*.png"):
            f.unlink()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", f"select=between(n\\,{k0}\\,{k1})", "-fps_mode", "passthrough", "-start_number", str(k0), str(tdir / "f_%05d.png")], check=True)
        play = {round(f["playT"] * FPS): f for f in frames}
        rows, tiles = [], []
        for k in range(k0, k1 + 1):
            p = tdir / f"f_{k:05d}.png"
            f = play.get(k)
            if not p.exists() or not f:
                continue
            im = Image.open(p).convert("RGB")
            row = {"frame": k, "playT": round(k / FPS, 3), "cue": f["cueId"], "cue_t": f["t"]}
            pair = []
            for kid in KIDS:
                e = (f["faces"].get(kid) or {}).get("eyes")
                row[kid] = e
                if kid in f["boxes"]:
                    pair.append((kid_face_crop(im, f["boxes"][kid], 150, (f.get("eyes") or {}).get(kid)), f"{kid} {EYE_ZH.get(e)}"))
            rows.append(row)
            tiles.append((row, pair))
        if tiles:
            cw = 300
            sheet = Image.new("RGB", (10 + len(tiles) * (2 * cw + 20), 230), (24, 22, 20))
            d = ImageDraw.Draw(sheet)
            d.text((10, 8), "g4_playback.mp4 37.9–38.1 秒每 1/30 秒抽格（ffmpeg 從 mp4 解碼）：兩個孩子的眼睛放大＋換片狀態", font=font(20), fill=(240, 236, 228))
            for i, (row, pair) in enumerate(tiles):
                x = 10 + i * (2 * cw + 20)
                for j, (im, lab) in enumerate(pair):
                    sheet.paste(im.crop((0, 0, min(cw - 6, im.width), 150)), (x + j * cw, 40))
                    d.text((x + j * cw, 194), lab, font=font(14), fill=(200, 196, 188))
                d.text((x, 210), f"{row['playT']:.3f}s（{row['cue']} {row['cue_t']:.3f}s）", font=font(13), fill=(255, 200, 150))
            path = out / "blink" / "mp4_37.9-38.1.png"
            sheet.save(path)
            res["window_37_9_38_1"] = {"sheet": rel(path, out), "frames": rows,
                                       "non_open_frames": sum(1 for r in rows for kid in KIDS if r.get(kid) not in ("open", None))}
    (out / "blink" ).mkdir(exist_ok=True)
    (out / "blink" / "blink_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"flips": [{k: f[k] for k in ("cue", "target", "pose", "start", "end", "frames_checked", "frames_after_end_0_3s", "all_open", "first_blink_after_end_s")} for f in res["flips"]],
            "blink_runs": len(res["blinks"]), "blink_frames_sheet": res.get("blink_frames_sheet"), "blink_frames": res.get("blink_frames"),
            "window_37_9_38_1": {k: v for k, v in (res["window_37_9_38_1"] or {}).items() if k != "frames"} or None}


def kids_zoom_strip(out: Path, t0=18.75, t1=22.6):
    """第 5 項：a2_c002 18.75–22.6 秒每秒 8 格的孩子頭部放大條帶（標出每格的眼睛換片狀態）"""
    sp = out / "strip_a2_c002" / "strip_probe.json"
    if not sp.exists():
        return None
    frames = [f for f in json.loads(sp.read_text(encoding="utf-8"))["frames"] if t0 - 1e-6 <= f["t"] <= t1 + 1e-6]
    fdir = out / "strip_a2_c002" / "frames"
    tiles, rows = [], []
    for f in frames:
        p = fdir / f"a2_c002_{f['t']:07.3f}.jpg"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        pair, row = [], {"t": f["t"]}
        for kid in KIDS:
            a = next((x for x in f["actors"] if x["id"] == kid and x.get("visible")), None)
            e = (f.get("faces", {}).get(kid) or {}).get("eyes")
            row[kid] = e
            if a:
                pair.append((kid_face_crop(im, a["box"], 140, a.get("eyesBox")), f"{kid} {EYE_ZH.get(e)}"))
        rows.append(row)
        tiles.append((f["t"], pair))
    if not tiles:
        return None
    cols, cw = 4, 2 * 240 + 16
    nrow = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (10 + cols * (cw + 10), 44 + nrow * 190), (24, 22, 20))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), f"a2_c002 {t0}–{t1} 秒孩子眼睛放大（每秒 8 格；以眼睛換片範圍為中心；標出眼睛換片：睜／半閉／閉；一張換片同時蓋兩眼）", font=font(20), fill=(240, 236, 228))
    for i, (t, pair) in enumerate(tiles):
        x, y = 10 + (i % cols) * (cw + 10), 40 + (i // cols) * 190
        for j, (im, lab) in enumerate(pair):
            sheet.paste(im.crop((0, 0, min(240, im.width), 140)), (x + j * 248, y))
            d.text((x + j * 248, y + 143), lab, font=font(13), fill=(200, 196, 188))
        d.text((x, y + 161), f"t={t:.3f}s", font=font(14), fill=(255, 200, 150))
    path = out / "strip_a2_c002" / f"kids_{t0}-{t1}.png"
    sheet.save(path)
    return {"sheet": rel(path, out), "frames": len(rows), "eyes": rows,
            "non_open_frames": [r for r in rows if any(r.get(k) not in ("open", None) for k in KIDS)]}


def _visible_poly(path, H=1080):
    pts = [tuple(p) for p in path]
    out_ = []
    for i, p in enumerate(pts):
        if p[1] >= 0:
            if i > 0 and pts[i - 1][1] < 0 and not out_:
                a, b = pts[i - 1], p
                u = (0 - a[1]) / (b[1] - a[1])
                out_.append((a[0] + (b[0] - a[0]) * u, 0.0))
            out_.append(p)
    return out_


def string_sag_px(path):
    """畫面裡那一段線（畫面上緣交點 → 線的下端＝紙環上緣）：弧長中點到兩端連線的距離（px）與最大偏離"""
    poly = _visible_poly(path)
    if len(poly) < 3:
        return None
    L = [0.0]
    for a, b in zip(poly, poly[1:]):
        L.append(L[-1] + float(np.hypot(b[0] - a[0], b[1] - a[1])))
    half = L[-1] / 2
    m = poly[-1]
    for i in range(1, len(L)):
        if L[i] >= half:
            u = (half - L[i - 1]) / max(1e-9, L[i] - L[i - 1])
            m = (poly[i - 1][0] + (poly[i][0] - poly[i - 1][0]) * u, poly[i - 1][1] + (poly[i][1] - poly[i - 1][1]) * u)
            break
    a, b = poly[0], poly[-1]
    cl = float(np.hypot(b[0] - a[0], b[1] - a[1])) or 1.0
    dev = lambda p: abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / cl
    return {"mid_offset_px": round(dev(m), 1), "max_offset_px": round(max(dev(p) for p in poly), 1), "visible_len_px": round(L[-1], 1), "mid_px": [round(m[0], 1), round(m[1], 1)], "ends_px": [[round(v, 1) for v in a], [round(v, 1) for v in b]]}


def string_sag(out: Path, tl: dict):
    """第 6 項：線還鬆時是下垂弧線、繃直節拍後是直線。條帶（每秒 8 格）每格量畫面裡那段線的中點偏移。
    規則：想揮手 9.75–12.25 秒三條線 ≥ 15 px；12.5 秒之後腕背、肘外 ≤ 3 px；膝前線在膝前線繃緊節拍前 ≥ 15 px、繃緊結束後 ≤ 3 px"""
    sp = out / "strip_a2_c002" / "strip_probe.json"
    if not sp.exists():
        return None
    frames = json.loads(sp.read_text(encoding="utf-8"))["frames"]
    c = next((c for c in tl["cues"] if c["id"] == "a2_c002"), None)
    tb = tl.get("beatTables", {})
    wave = next((a for a in c["anims"] if a["name"] == "puppet.waveTry"), None)
    knee = next((a for a in c["anims"] if a["name"] == "puppet.kneeTug"), None)
    kt0 = knee["start"] + tb["kneeTug"]["tautStart"] if knee else None
    kt1 = knee["start"] + tb["kneeTug"]["tautEnd"] if knee else None
    rows = []
    for f in frames:
        r = {"t": f["t"]}
        for s in f["strings"]:
            if s.get("visible") and s.get("path"):
                m = string_sag_px(s["path"])
                if m:
                    r[s["anchor"]] = m["mid_offset_px"]
        rows.append(r)
    def pick(t0, t1, anchors):
        vals = [r[a] for r in rows if t0 - 1e-6 <= r["t"] <= t1 + 1e-6 for a in anchors if a in r]
        return (min(vals) if vals else None, max(vals) if vals else None, len(vals))
    loose = pick(9.75, 12.25, ("wrist", "elbow", "knee"))
    taut = pick(12.5, c["duration"] + 0.01, ("wrist", "elbow"))
    k_loose = pick(9.75, kt0 - 0.01, ("knee",)) if kt0 else (None, None, 0)
    k_taut = pick(kt1 + 0.01, c["duration"] + 0.01, ("knee",)) if kt1 else (None, None, 0)
    res = {"rule": "畫面裡那一段線（畫面上緣到紙環上緣，引擎實際畫的中心線 path）的弧長中點，到兩端連線的距離（px）",
           "wave_taut_beat_s": round(wave["start"] + tb["waveTry"]["tautStart"], 3) if wave else None,
           "wave_taut_end_s": round(wave["start"] + tb["waveTry"]["tautEnd"], 3) if wave else None,
           "knee_taut_beat_s": round(kt0, 3) if kt0 else None, "knee_taut_end_s": round(kt1, 3) if kt1 else None,
           "loose_9_75_12_25": {"min_px": loose[0], "max_px": loose[1], "samples": loose[2], "pass_ge_15": loose[0] is not None and loose[0] >= 15},
           "taut_after_12_5_wrist_elbow": {"min_px": taut[0], "max_px": taut[1], "samples": taut[2], "pass_le_3": taut[1] is not None and taut[1] <= 3},
           "knee_loose_before_taut": {"min_px": k_loose[0], "max_px": k_loose[1], "samples": k_loose[2], "pass_ge_15": k_loose[0] is not None and k_loose[0] >= 15},
           "knee_after_taut": {"min_px": k_taut[0], "max_px": k_taut[1], "samples": k_taut[2], "pass_le_3": k_taut[1] is not None and k_taut[1] <= 3},
           "rows": rows}
    (out / "strip_a2_c002" / "string_sag.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    # 圖：中點偏移對時間
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 4.2))
    for a, col in (("wrist", "#c0392b"), ("elbow", "#2471a3"), ("knee", "#7d6608")):
        ts = [r["t"] for r in rows if a in r]
        ax.plot(ts, [r[a] for r in rows if a in r], "-o", ms=2.5, color=col, label=a)
    ax.axhline(15, color="#555", ls="--", lw=0.8)
    ax.axhline(3, color="#555", ls=":", lw=0.8)
    ax.axvspan(9.75, 12.25, color="#f5cba7", alpha=0.35)
    for x in (res["wave_taut_beat_s"], res["knee_taut_beat_s"]):
        if x:
            ax.axvline(x, color="#922b21", lw=0.8)
    ax.set_xlabel("a2_c002 s")
    ax.set_ylabel("mid offset px")
    ax.set_title("string sag (visible segment midpoint offset from chord); dashed 15 px, dotted 3 px; shaded 9.75-12.25 s; red = taut beats")
    ax.legend(loc="upper right")
    fig.tight_layout()
    pth = out / "strip_a2_c002" / "string_sag_plot.png"
    fig.savefig(pth, dpi=80)
    plt.close(fig)
    # 兩格對照：鬆（11.0）與繃直後（12.625）
    tiles = []
    for tt in (11.0, 12.625):
        f = min(frames, key=lambda x: abs(x["t"] - tt))
        p = out / "strip_a2_c002" / "frames" / f"a2_c002_{f['t']:07.3f}.jpg"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        labs = []
        for s in f["strings"]:
            if s.get("visible") and s.get("path"):
                m = string_sag_px(s["path"])
                if not m:
                    continue
                (ax0, ay0), (bx0, by0) = m["ends_px"]
                d.line([(ax0, ay0), (bx0, by0)], fill=(0, 160, 255), width=2)
                mx, my = m["mid_px"]
                d.ellipse([mx - 5, my - 5, mx + 5, my + 5], outline=(255, 0, 0), width=2)
                labs.append(f"{s['anchor']} {m['mid_offset_px']} px")
        crop = im.crop((60, 0, 1060, 760)).resize((700, 532), Image.LANCZOS)
        tiles.append((crop, f"t={f['t']:.3f}s：" + "、".join(labs) + "（藍線＝兩端連線、紅圈＝弧長中點）"))
    if tiles:
        sheet = Image.new("RGB", (len(tiles) * 710 + 10, 600), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        for i, (im, lab) in enumerate(tiles):
            sheet.paste(im, (10 + i * 710, 10))
            d.text((10 + i * 710, 552), lab, font=font(15), fill=(230, 226, 218))
        p2 = out / "strip_a2_c002" / "string_sag_frames.png"
        sheet.save(p2)
        res["frames_sheet"] = rel(p2, out)
    res["plot"] = rel(pth, out)
    return {k: v for k, v in res.items() if k != "rows"}


def stand_measure(out: Path, tl: dict, t0=18.5, t1=21.5):
    """第 7 項：站起拍。條帶（每秒 8 格）18.5–21.5 秒：臀部（骨盆樞紐）相對凳面上緣的上移量、扶桌時近側手（hand_l 不透明範圍）與桌面上緣的相交量"""
    sp = out / "strip_a2_c002" / "strip_probe.json"
    if not sp.exists():
        return None
    frames = json.loads(sp.read_text(encoding="utf-8"))["frames"]
    c = next((c for c in tl["cues"] if c["id"] == "a2_c002"), None)
    knee = next((a for a in c["anims"] if a["name"] == "puppet.kneeTug"), None)
    kb = tl.get("beatTables", {}).get("kneeTug", {})
    if not knee:
        return None
    grab_end = knee["start"] + kb.get("grabEnd", 2.6)
    rows = []
    base = None
    for f in frames:
        ale = next((a for a in f["actors"] if a["id"] == "ale"), None)
        lm = f.get("landmarks") or {}
        if not ale or not ale.get("joints") or "stoolTop" not in lm:
            continue
        hip_y = ale["joints"]["hip"][1]
        stool_y = (lm["stoolTop"][0][1] + lm["stoolTop"][1][1]) / 2
        above = stool_y - hip_y
        if f["t"] <= knee["start"] + 1e-6:
            base = above
        r = {"t": f["t"], "hip_px": ale["joints"]["hip"], "stool_top_y": round(stool_y, 1), "hip_above_stool_px": round(above, 1)}
        hand = (ale.get("opaque") or {}).get("hand_l")
        if hand and "tableTop" in lm:
            ty = (lm["tableTop"][0][1] + lm["tableTop"][1][1]) / 2
            tx0, tx1 = lm["tableTop"][0][0], lm["tableTop"][1][0]
            r.update({"table_top_y": round(ty, 1), "hand_opaque": hand,
                      "hand_straddle_px": round(min(ty - hand[1], hand[3] - ty), 1),
                      "hand_x_overlap_px": round(min(hand[2], tx1) - max(hand[0], tx0), 1)})
        rows.append(r)
    for r in rows:
        r["rise_px"] = round(r["hip_above_stool_px"] - (base or 0), 1)
    win = [r for r in rows if t0 - 1e-6 <= r["t"] <= t1 + 1e-6]
    # 臀部上移 ≥ 25 px 的最長連續時間（條帶每秒 8 格）
    best, cur, start = 0.0, None, None
    for r in [r for r in rows if r["t"] >= knee["start"] - 1e-6]:
        if r["rise_px"] >= 25:
            if cur is None:
                start = r["t"]
            cur = r["t"]
            best = max(best, cur - start + 1 / 8)
        else:
            cur = None
    after = [r for r in rows if r["t"] >= grab_end - 1e-6 and "hand_straddle_px" in r]
    res = {"rule": "臀部上移＝（凳面上緣 y − 骨盆樞紐 y）減去起身前（kneeTug 起點）的同一量（同一格內相對凳面，抵銷鏡頭推近）；"
                   "扶桌相交＝近側手 hand_l 貼圖不透明範圍（alpha ≥ 128，不含白色紙芯描邊）跨過桌面上緣的量：上下各離桌面上緣的較小者（hand_straddle_px），左右與桌面範圍重疊（hand_x_overlap_px）",
           "kneeTug_start_s": knee["start"], "grab_end_s": round(grab_end, 3), "seated_hip_above_stool_px": base,
           "max_rise_px": max((r["rise_px"] for r in win), default=None),
           "longest_rise_ge_25px_s": round(best, 3), "pass_rise": best >= 0.5 and max((r["rise_px"] for r in win), default=0) >= 25,
           "hand_after_grab_end": {"frames": len(after), "min_straddle_px": min((r["hand_straddle_px"] for r in after), default=None),
                                   "min_x_overlap_px": min((r["hand_x_overlap_px"] for r in after), default=None)},
           "rows": win}
    res["pass_hand"] = bool(after) and res["hand_after_grab_end"]["min_straddle_px"] >= 10 and res["hand_after_grab_end"]["min_x_overlap_px"] >= 10
    # 條帶圖：阿樂叔叔周圍放大＋量測線
    fdir = out / "strip_a2_c002" / "frames"
    tiles = []
    fmap = {f["t"]: f for f in frames}
    for r in win:
        p = fdir / f"a2_c002_{r['t']:07.3f}.jpg"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        f = fmap[r["t"]]
        lm = f["landmarks"]
        d.line([tuple(lm["stoolTop"][0]), tuple(lm["stoolTop"][1])], fill=(40, 120, 255), width=3)
        hx, hy = r["hip_px"]
        d.line([(hx - 40, hy), (hx + 40, hy)], fill=(255, 170, 0), width=3)
        if "table_top_y" in r:
            d.line([tuple(lm["tableTop"][0]), tuple(lm["tableTop"][1])], fill=(230, 30, 30), width=2)
            d.rectangle(r["hand_opaque"], outline=(0, 200, 80), width=2)
        ale = next(a for a in f["actors"] if a["id"] == "ale")
        bx0, by0, bx1, by1 = ale["box"]
        crop = im.crop((int(max(0, bx0 - 60)), int(max(0, by0 - 20)), int(min(1920, bx1 + 260)), int(min(1080, by1 + 20))))
        crop = crop.resize((int(crop.width * 300 / crop.height), 300), Image.LANCZOS)
        grab0 = knee["start"] + kb.get("grabStart", 1.95)
        lab = f"t={r['t']:.3f}s 臀部上移 {r['rise_px']:.0f}px" + (f"／手跨桌緣 {r['hand_straddle_px']:.0f}px" if "hand_straddle_px" in r and r["t"] >= grab0 - 1e-6 else "")
        tiles.append((crop, lab))
    if tiles:
        cols = 8
        cw = max(t.width for t, _ in tiles)
        nrow = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (10 + cols * (cw + 8), 44 + nrow * 330), (24, 22, 20))
        d = ImageDraw.Draw(sheet)
        d.text((10, 8), f"a2_c002 站起拍 {t0}–{t1} 秒（每秒 8 格）：藍＝凳面上緣、橘＝骨盆樞紐、紅＝桌面上緣、綠框＝近側手不透明範圍", font=font(20), fill=(240, 236, 228))
        for i, (im, lab) in enumerate(tiles):
            x, y = 10 + (i % cols) * (cw + 8), 40 + (i // cols) * 330
            sheet.paste(im, (x, y))
            d.text((x, y + 303), lab, font=font(13), fill=(200, 196, 188))
        path = out / "strip_a2_c002" / f"stand_{t0}-{t1}.png"
        sheet.save(path)
        res["sheet"] = rel(path, out)
    (out / "strip_a2_c002" / "stand_measures.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return {k: v for k, v in res.items() if k != "rows"}


def c004_variation(out: Path, tl: dict):
    """第 12 項：a2_c004 每 6 秒內至少一格構圖或姿勢不同。每秒 2 格接觸表的原尺寸格（capture/frames），相鄰兩格縮成 320×180 灰階，
    排除下方 22%（字幕帶）後的平均絕對差 > 1.0（0–255）＝這半秒內畫面有變化（鏡頭或角色）"""
    fr = sorted((out / "capture" / "frames").glob("a2_c004_*.jpg"))
    if len(fr) < 3:
        return None
    ts = [float(p.stem.split("_")[-1]) for p in fr]
    arr = []
    for p in fr:
        g = np.asarray(Image.open(p).convert("L").resize((320, 180), Image.BILINEAR), dtype=np.float32)
        arr.append(g[: int(180 * 0.78)])
    diffs = [{"t0": ts[i - 1], "t1": ts[i], "mean_abs_diff": round(float(np.abs(arr[i] - arr[i - 1]).mean()), 2)} for i in range(1, len(arr))]
    for d_ in diffs:
        d_["changed"] = d_["mean_abs_diff"] > 1.0
    c = next((c for c in tl["cues"] if c["id"] == "a2_c004"), None)
    D = c["duration"] if c else ts[-1]
    wins = []
    w0 = 0.0
    while w0 + 6 <= D + 1e-6:
        n = sum(1 for d_ in diffs if d_["changed"] and d_["t1"] > w0 + 1e-6 and d_["t0"] < w0 + 6 - 1e-6)
        wins.append({"from": round(w0, 2), "to": round(w0 + 6, 2), "changed_pairs": n})
        w0 += 0.5
    actions = [{"name": a["name"], "target": a["target"], "start": a["start"], "end": a["end"]} for a in (c or {}).get("anims", []) if a["name"].startswith("puppet.") or a["name"] == "camera.move"]
    res = {"rule": "相鄰兩格（每秒 2 格）灰階平均絕對差 > 1.0 算一次變化（排除下方 22% 字幕帶）；每個 6 秒窗（每 0.5 秒滑動）至少 1 次",
           "min_changed_pairs_per_6s": min((w["changed_pairs"] for w in wins), default=None), "windows": len(wins),
           "windows_without_change": [w for w in wins if w["changed_pairs"] == 0], "diffs": diffs, "animations": actions}
    (out / "c004_variation.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return {k: v for k, v in res.items() if k not in ("diffs",)}


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
    def _ver(pth):
        m = re.search(r"_v(\d+)$", pth.stem)
        return int(m.group(1)) if m else 0
    attach_path = max((ROOT / "assets/final/rig").glob("ale_attach*.json"), key=_ver)
    attach = json.loads(attach_path.read_text(encoding="utf-8"))
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
        "attach_file": rel(attach_path, ROOT),
        "attach_points_primary": {k: {"part": v.get("part"), "local_px": v.get("local_px") or v.get("part_px")} for k, v in (attach.get("points") or {}).items() if v.get("primary", True)},
        "probe_frames_with_strings": frames_with_strings,
        "string_path_min_dist_to_ale_head_box_px": round(float(min(head_d)), 1) if head_d else None,
        "per_anchor": per_anchor,
        "string_path_intersects_child_box": kid_hits,
        "string_path_intersects_child_box_count": len(kid_hits),
        "probe_method": probe_src + "；線路徑＝引擎實際畫的中心線（strings.ts，37 點，下段細分）投影到螢幕；頭部框＝阿樂叔叔顯示中的 head／head_worried 部件圖外框（含透明邊，比可見的頭大）；兒童框＝整個立牌外框（含透明邊）。",
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
    print("[g4pack.py] 條帶（含節拍標示）、呼吸、字幕重疊、換姿勢放大、前臂裁切")
    res["strip_pages"] = strip(out, meta, tl)
    res["beats"] = beat_report(out, tl)
    res["strip_measures"] = strip_measures(out, tl)
    res["flips"] = flip_sheets(out)
    res["forearm_crops"] = forearm_crops(out)
    res["compare_g2"] = compare_g2(out)
    print("[g4pack.py] 混音與響度")
    res["audio"] = {k: v for k, v in audio_analysis(out, tl).items() if k not in ("lines", "events", "per_cue")}
    seq = playback_sequence(out, tl)
    print(f"[g4pack.py] 播放逐格光敏分析（{len(seq)} 格）")
    fl = flash_playback(out, seq)
    res["flash_playback"] = {k: fl[k] for k in ("ok", "max_changes_per_sec", "near_limit_total", "frames_analyzed")}
    print("[g4pack.py] 光敏細格與投影 v2")
    fv = flash_variants(out, seq)
    res["flash_variants"] = {k: {kk: v[kk] for kk in ("max_changes_per_sec", "near_limit_3_total")} for k, v in fv["variants"].items()}
    res["subtitle_sync"] = {k: v for k, v in subtitle_sync(out, tl).items() if k != "rows"}
    res["kids_in_frame"] = kids_in_frame(out)
    print("[g4pack.py] 影片")
    video = make_video(out, seq)
    res["video"] = video
    res["durations"] = durations(out, tl, video)
    res["safety"] = safety_data(out, tl)
    print("[g4pack.py] G4 修正第 2 輪量測：眨眼與翻面、孩子頭部條帶、線的鬆垂弧、站起與扶桌、a2_c004 小動作")
    res["blink_check"] = blink_check(out, tl)
    res["kids_zoom"] = kids_zoom_strip(out)
    res["string_sag"] = string_sag(out, tl)
    res["stand"] = stand_measure(out, tl)
    res["c004_variation"] = c004_variation(out, tl)
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
    fv, ss, kf = J("flash_variants.json"), J("subtitle_sync.json"), J("kids_in_frame.json")
    smeas = J("strip_a2_c002/strip_measures.json")
    L = []
    w = L.append
    w("# G4 代表鏡頭驗收包")
    w("")
    w(f"- 產生：`tools/g4_review_pack.mjs`（呼叫 `tools/capture.mjs`、`tools/g4_review_pack.py`、`tools/g4_transcripts.py`、`tools/projsim.py` 的函式）；產生時間 {cap['createdAt'] if cap else '—'}")
    w(f"- cue 檔：`app/cues/g4.json`；渲染：{cap['width']}×{cap['height']}、畫質 {cap['quality']}；GPU：{cap['gpu']}" if cap else "")
    w("- 取樣規則固定：每個 cue 前（t=0）、中（t=長度/2）、後（播完停住）各 1 格；每秒 2 格接觸表；a2_c002 從 `strings.drop` 起點到停格每秒 8 格；光敏分析每秒 30 格。")
    w("- 另外固定量測：開幕兒童立起過程每 0.2 秒、驗收意見指定的 a2_c002 11.41／22.83 秒與 a2_c004 9.75 秒（`capture/probe_frames/`）；a2_c002 每個換姿勢前 0.2 秒到結束後 0.4 秒每秒 30 格；播放錄製每一格的臉部換片狀態（`faces_playback.json`）。")
    w("- G4 修正第 2 輪新增的量測在「2. 畫面」的「G4 修正第 2 輪量測」一節（眨眼與翻面、37.9–38.1 秒 mp4 抽格、孩子眼睛放大、操偶線鬆垂弧、站起與扶桌、a2_c004 畫面變化），紙環環身顏色在操偶線量測表。")
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
        w(f"| `{p}` | a2_c002 逐格條帶（每秒 8 格；紅框＝揮手、扯膝節拍時間點之後的第一格） |")
    for f in (an or {}).get("flips") or []:
        w(f"| `{f['sheet']}` | {f['target']} 換姿勢 → {f['pose']}（{f['start']:.2f} s）前後每秒 30 格放大，標出寬度比 |")
    if (an or {}).get("forearm_crops"):
        w(f"| `{an['forearm_crops']}` | 阿樂叔叔前臂件裁切（a2_c002、a2_c004 關鍵影格） |")
    if pr and (pr.get("ring_crops") or {}).get("sheet"):
        w("| `capture/ring_crops.png`、`capture/ring_crops/*.png` | 紙環 1:1 放大（×3，關鍵影格與指定時間） |")
    if (out / "capture/rope_crop_4x.png").exists():
        w("| `capture/rope_crop_4x.png` | 一段紙繩 1:1 放大 ×4（a2_c002 停格腕背紙環上方，看扭紋與纖維） |")
    w("| `strip_a2_c002/strip_probe.json`、`strip_measures.json` | 條帶每格的量測（外框、紙環、字幕底板）與呼吸、字幕重疊結果 |")
    sm = (an or {}).get("frames_meta", {}).get("strip") or {}
    w(f"| `strip_a2_c002/frames/*.jpg` | 條帶原尺寸（{sm.get('count', '—')} 格，{sm.get('from', '—')}–{sm.get('to', '—')} 秒＋停格） |")
    w("| `proj/contact_proj_16x9.png` | 關鍵影格：原圖｜投影模擬 v2 |")
    w("| `proj/16x9/*_proj.png`、`*_sheet.png` | 每張關鍵影格的投影模擬 v2、四聯圖（原圖／投影／灰階／綠色弱） |")
    for d in sorted((out / "keyframes_4x3").glob("*x*")) if (out / "keyframes_4x3").exists() else []:
        w(f"| `keyframes_4x3/{d.name}/*.png` | 4:3 關鍵影格（視窗 {d.name.replace('x', '×')}，{len(list(d.glob('*.png')))} 張） |")
        w(f"| `proj/contact_4x3_{d.name}.png`、`proj/{d.name}/*_proj.png` | 4:3 關鍵影格：原圖｜投影模擬 v2 |")
    for p in (an or {}).get("compare_g2", []):
        w(f"| `{p}` | G2 退路試作合成圖（review/G2/*_v04）與 G4 劇場截圖 a2_c002 關鍵影格並排（上原圖、下投影模擬 v2） |")
    r2 = an or {}
    if (r2.get("blink_check") or {}).get("blink_frames_sheet"):
        w(f"| `{r2['blink_check']['blink_frames_sheet']}` | 全片孩子眨眼格（播放錄製每秒 30 格中眼睛不是睜開的每一格）頭部放大 |")
    if ((r2.get("blink_check") or {}).get("window_37_9_38_1") or {}).get("sheet"):
        w(f"| `{r2['blink_check']['window_37_9_38_1']['sheet']}`、`blink/mp4_37.9-38.1/*.png` | g4_playback.mp4 37.9–38.1 秒每 1/30 秒抽格（ffmpeg 從 mp4 解碼）的孩子頭部放大 |")
    w("| `blink/blink_check.json`、`faces_playback.json` | 翻面窗內的眼睛狀態檢查、全片眨眼段；播放錄製每一格的臉部換片狀態與兒童外框 |")
    if (r2.get("kids_zoom") or {}).get("sheet"):
        w(f"| `{r2['kids_zoom']['sheet']}` | a2_c002 18.75–22.6 秒孩子頭部放大條帶（每秒 8 格，標眼睛換片狀態） |")
    if (r2.get("string_sag") or {}).get("plot"):
        w(f"| `{r2['string_sag']['plot']}`、`{r2['string_sag'].get('frames_sheet', '')}`、`strip_a2_c002/string_sag.json` | 操偶線鬆垂弧：條帶每格畫面裡那段線的中點偏移（px）對時間；鬆（11.0 s）與繃直後（12.625 s）對照 |")
    if (r2.get("stand") or {}).get("sheet"):
        w(f"| `{r2['stand']['sheet']}`、`strip_a2_c002/stand_measures.json` | 站起拍 18.5–21.5 秒每秒 8 格放大：臀部相對凳面上移、近側手與桌面上緣相交（附量測值） |")
    if r2.get("c004_variation"):
        w("| `c004_variation.json` | a2_c004 每 6 秒窗的畫面變化次數（構圖或姿勢） |")
    w("| `capture/probe_bg/*.png` | 同一格隱藏角色後的背景（量兒童站位背景亮度用） |")
    w("| `g4_playback.mp4` | 播放錄製：固定步長 30 格／秒逐格＋最終混音，1920×1080，H.264＋AAC |")
    w("")
    if pr:
        w("### 操偶線與背景量測（`capture/probe_report.json`）")
        w("")
        s = pr.get("summary") or {}
        rows = pr.get("strings") or []
        if rows:
            w("ΔL*＝每一側取「繩身或該側深灰邊對該側背景」的較大者，再取兩側較小者（繩身改淡灰後，對淺牆的可讀性由兩側深灰邊提供；判定方式待主線確認，繩身、深灰邊也分開列出：各自是兩側較小者）。")
            w("")
            w("| cue | t | 扣點 | 線寬 px | ΔL* | 繩身 | 深灰邊 | ΔL*（投影 v2） | 繩身（投影） | 深灰邊（投影） |")
            w("|---|---|---|---|---|---|---|---|---|---|")
            for r in rows:
                w(f"| {r['cue']} | {fmt(r['t'], 2)} | {r['anchor']} | {fmt(r.get('widthPx'), 1)} | {fmt(r.get('deltaL'), 1)} | {fmt(r.get('deltaL_body'), 1)} | {fmt(r.get('deltaL_edge'), 1)} | {fmt(r.get('deltaL_proj'), 1)} | {fmt(r.get('deltaL_proj_body'), 1)} | {fmt(r.get('deltaL_proj_edge'), 1)} |")
            w("")
        rings = pr.get("rings") or []
        if rings:
            w("紙環中心是否落在角色剪影內（紙環中間透明；中心 5×5 與同一格隱藏角色的背景比對，最大通道差中位數 > 18＝看到的是肢體）：")
            w("")
            w("環身顏色（G4 修正第 2 輪第 8 項）：" + (pr.get("ring_body_rule") or ""))
            w("")
            w("| cue | t | 扣點 | 紙環中心 px | 半徑 px | 與背景差 | 在剪影內 | 環身平均 sRGB | 環身亮度 luma | 最小通道 | 色相° | 彩度 |")
            w("|---|---|---|---|---|---|---|---|---|---|---|---|")
            for r in rings:
                b = r.get("body") or {}
                w(f"| {r['cue']} | {fmt(r['t'], 2)} | {r['anchor']} | {r['ring_px']} | {r['ring_radius_px']} | {r['center_diff_vs_bg']} | {'是' if r['center_inside_silhouette'] else '**否**'} | {b.get('mean_srgb', '—')} | {fmt(b.get('luma'), 1)} | {fmt(b.get('min_channel_mean'), 1)} | {fmt(b.get('hue_deg'), 1)} | {fmt(b.get('saturation'), 3)} |")
            w("")
        kids = pr.get("child_background") or []
        if kids:
            w("兒童站位背景（同一格隱藏角色重畫，取兒童軀幹高度兩側背景，投影模擬 v2 後的相對亮度）：")
            w("")
            w("| cue | t | 影格 | 角色 | 立起程度 | 量測區 px | 背景亮度中位 | p10 |")
            w("|---|---|---|---|---|---|---|---|")
            for r in kids:
                w(f"| {r.get('cue')} | {fmt(r.get('t'), 2)} | {r.get('key')} | {r.get('actor')} | {fmt(r.get('upright'), 2)} | {r.get('region')} | {fmt(r.get('proj_lum_median'), 3)} | {fmt(r.get('proj_lum_p10'), 3)} |")
            w("")
        if s:
            w("摘要：" + "；".join(f"{k} {v}" for k, v in s.items()))
            w("")
    bt = (an or {}).get("beats")
    if bt:
        w("### 節拍（`analysis.json` beats；資料來源 `app/src/stage/beats.ts`，條帶紅框）")
        w("")
        w("| 動作 | # | 節拍 | cue 內秒數 | 條帶上的格 |")
        w("|---|---|---|---|---|")
        for anim, lab in (("puppet.waveTry", "想揮手"), ("puppet.kneeTug", "想站起")):
            for i, b in enumerate((bt.get(anim) or {}).get("beats", [])):
                w(f"| {lab} | {i + 1} | {b['label']} | {fmt(b['t'], 2)} | {fmt(b['strip_frame_t'], 3)} |")
        ch = bt.get("checks") or {}
        w("")
        w(f"依序遞增：想揮手 {(bt.get('puppet.waveTry') or {}).get('increasing')}、想站起 {(bt.get('puppet.kneeTug') or {}).get('increasing')}。"
          f"揮手 {ch.get('wave_duration_s')} 秒（約 {ch.get('wave_cycles')} 下）；手開始被拉偏到換困惑臉 {ch.get('confused_after_pull_s')} 秒；"
          f"線繃直在揮完之後＝{ch.get('taut_after_wave')}；停在半站 {ch.get('half_stand_hold_s')} 秒；膝蓋在線繃緊之後才被提起＝{ch.get('lift_after_taut')}。")
        w("")
    if smeas:
        b, o = smeas["breathing_xiaoqing"], smeas["subtitle_vs_knee"]
        w("### 小晴呼吸與字幕底板（`strip_a2_c002/strip_measures.json`）")
        w("")
        w(f"- 小晴呼吸（{b['window_s'][0]}–{b['window_s'][1]} 秒，鏡頭與姿勢不變，{b['frames']} 格）：外框高度 {b['box_height_px_min']}–{b['box_height_px_max']} px，峰對峰 {b['peak_to_peak_px']} px（振幅 {b['amplitude_px']} px）。")
        w(f"- 字幕底板與阿樂膝前線、膝前紙環、被提起那條腿：有字幕的 {o['frames_with_subtitle']} 格中重疊 {o['frames_overlapping']} 格（規則：{o['rule']}）。")
        w("")
    fl = (an or {}).get("flips") or []
    if fl:
        w("### 換姿勢（紙片翻面：寬度壓到約 55% 就在動作中段硬切換圖）")
        w("")
        w("| 角色 | 換成 | 時間 s | 最窄寬度比 | 翻面前 0.2 秒到結束後 0.3 秒眼睛都是睜開 | 放大條帶 |")
        w("|---|---|---|---|---|---|")
        for f in fl:
            w(f"| {f['target']} | {f['pose']} | {f['start']:.2f}–{f['end']:.2f} | {f['min_width_ratio']} | {f.get('eyes_open_from_start-0.2_to_end+0.3')} | `{f['sheet']}` |")
        w("")
    r2 = an or {}
    bc, kz, sg, stn, cv = r2.get("blink_check"), r2.get("kids_zoom"), r2.get("string_sag"), r2.get("stand"), r2.get("c004_variation")
    if bc or kz or sg or stn or cv:
        w("### G4 修正第 2 輪量測（只列數字；判定由驗收者做）")
        w("")
    if bc:
        w("**眨眼與翻面、兩眼同閉**（`blink/blink_check.json`；資料來源：播放錄製每一格的 `window.__engine.debug.faces()`）")
        w("")
        w("- 眼睛換片：一張換片圖同時蓋兩眼（半閉／閉兩眼同時），所以引擎只會兩眼同時閉、同時開；換片圖本身兩眼是否都閉，見素材檢查 `review/G4/art/blink_check_r2.json` 與上面的放大圖。")
        w("")
        w("| cue | 角色 | 換成 | 翻面 s | 檢查格數（起點前 0.2 秒到結束後 0.3 秒） | 其中結束後 0.3 秒內 | 全部睜開 | 翻面結束後第一次眨眼（秒） |")
        w("|---|---|---|---|---|---|---|---|")
        for f in bc["flips"]:
            w(f"| {f['cue']} | {f['target']} | {f['pose']} | {f['start']:.2f}–{f['end']:.2f} | {f['frames_checked']} | {f['frames_after_end_0_3s']} | {f['all_open']} | {fmt(f['first_blink_after_end_s'], 3)} |")
        w("")
        win = bc.get("window_37_9_38_1") or {}
        if win:
            w(f"- g4_playback.mp4 37.9–38.1 秒：`{win.get('sheet')}`；眼睛不是睜開的格數 {win.get('non_open_frames')}。")
        w(f"- 全片孩子眨眼 {bc.get('blink_runs')} 次、{bc.get('blink_frames')} 格（`{bc.get('blink_frames_sheet')}`）。")
        w("")
    if kz:
        w(f"**a2_c002 18.75–22.6 秒孩子眼睛放大條帶**（`{kz['sheet']}`）：{kz['frames']} 格。有孩子在眨眼的格（括號內是兩個孩子各自的眼睛換片狀態；兩個孩子各自眨眼，同一個孩子的兩眼共用一張換片）：" + ("、".join(f"{r['t']:.3f}s（小晴 {EYE_ZH.get(r.get('xiaoqing'))}、小宇 {EYE_ZH.get(r.get('xiaoyu'))}）" for r in kz["non_open_frames"]) or "無"))
        w("")
    if sg:
        w(f"**操偶線鬆垂弧**（`strip_a2_c002/string_sag.json`、`{sg.get('plot')}`、`{sg.get('frames_sheet')}`）：{sg['rule']}。")
        w(f"想揮手繃直節拍 {sg['wave_taut_beat_s']} 秒（{sg['wave_taut_end_s']} 秒拉直）；膝前線繃緊節拍 {sg['knee_taut_beat_s']} 秒（{sg['knee_taut_end_s']} 秒拉直）。")
        w("")
        w("| 時段 | 線 | 中點偏移最小 px | 最大 px | 取樣 |")
        w("|---|---|---|---|---|")
        for key, lab, an_ in (("loose_9_75_12_25", "9.75–12.25 秒（還鬆）", "腕背、肘外、膝前"), ("taut_after_12_5_wrist_elbow", "12.5 秒之後（繃直後）", "腕背、肘外"),
                              ("knee_loose_before_taut", "9.75 秒到膝前線繃緊前", "膝前"), ("knee_after_taut", "膝前線拉直之後", "膝前")):
            v = sg.get(key) or {}
            w(f"| {lab} | {an_} | {fmt(v.get('min_px'), 1)} | {fmt(v.get('max_px'), 1)} | {v.get('samples')} |")
        w("")
    if stn:
        h = stn.get("hand_after_grab_end") or {}
        w(f"**站起拍與扶桌**（`strip_a2_c002/stand_measures.json`、`{stn.get('sheet')}`）：{stn['rule']}。")
        w(f"- 起身前臀部（骨盆樞紐）在凳面上緣上方 {fmt(stn.get('seated_hip_above_stool_px'), 1)} px；18.5–21.5 秒最大上移 {fmt(stn.get('max_rise_px'), 1)} px；上移 ≥ 25 px 最長連續 {stn.get('longest_rise_ge_25px_s')} 秒（條帶每秒 8 格）。")
        w(f"- 扶住桌邊之後（{stn.get('grab_end_s')} 秒起，{h.get('frames')} 格）：近側手不透明範圍跨過桌面上緣最少 {fmt(h.get('min_straddle_px'), 1)} px、左右與桌面重疊最少 {fmt(h.get('min_x_overlap_px'), 1)} px。")
        w("")
    if cv:
        w(f"**a2_c004 小動作與構圖變化**（`c004_variation.json`）：{cv['rule']}。6 秒窗 {cv['windows']} 個，每窗變化次數最少 {cv['min_changed_pairs_per_6s']}；沒有變化的窗 {len(cv['windows_without_change'])} 個。")
        w("- cue 內的角色動作與鏡頭移動：" + "、".join(f"{a['name']}（{a['target'] or '鏡頭'}，{a['start']:.2f}–{a['end']:.2f} s）" for a in cv.get("animations", [])))
        w("")
    if kf:
        w("### 兒童是否在 90% 安全框內（`kids_in_frame.json`，播放錄製每秒 10 次）")
        w("")
        w(f"- 規則：{kf['rule']}")
        for cue, v in kf["cues"].items():
            w(f"- {cue}：量測 {v['probes']} 格，有孩子的頭或上半身在安全框外 {v['frames_outside']} 次" + (f"（例：{v['examples'][:3]}）" if v["examples"] else ""))
        w("")
    w("- 字幕說話者小頭像：`assets/final/ui/ui-speaker_<說話者>`（旁白、阿樂叔叔、小晴、小宇）；沒有素材的說話者不顯示方塊、只留名牌文字。")
    w("")
    w("## 3. 光敏")
    w("")
    w("| 報告 | 方法 | 每秒最多變化（明暗／紅色） | 超標區域 | 接近上限（每秒 2–3 次）區域 |")
    w("|---|---|---|---|---|")
    if fr:
        w(f"| `capture/flash_report.json`、`capture/luma_plot.png`、`capture/luma_series.csv` | 逐 cue，{fr['method']} | {fr['max_changes_per_sec']['luma']}／{fr['max_changes_per_sec']['red']} | {fr['flagged_total']} | {fr['near_limit_total']} |")
    if fp:
        w(f"| `flash_playback.json`、`flash_playback_plot.png` | {fp['method']} | {fp['max_changes_per_sec']['luma']}／{fp['max_changes_per_sec']['red']} | {len(fp['flagged'])} | {fp['near_limit_total']} |")
    if fv:
        for k, v in fv["variants"].items():
            lab = {"fine_32x18": "細格 32×18", "proj_16x9": "投影 v2 後 16×9", "proj_32x18": "投影 v2 後 32×18"}.get(k, k)
            w(f"| `flash_variants.json` {k} | 播放錄製，{lab}（{fv['method']}） | {v['max_changes_per_sec']['luma']}／{v['max_changes_per_sec']['red']} | {len(v['flagged'])} | {v['near_limit_total']}（其中每秒 3 次 {v['near_limit_3_total']}） |")
    w("")
    if fv:
        three = [(k, n) for k, v in fv["variants"].items() for n in v["near_limit_3"]]
        if fp:
            three = [("16x9", n) for n in fp["near_limit"] if n["count_per_sec"] == 3] + three
        w(f"每秒 3 次（＝上限）的區域：{len(three)} 筆" + ("：" if three else "。"))
        if three:
            w("")
            w("| 分析 | 種類 | 區域 | px | 1 秒窗起點 s | cue | cue 內秒數 |")
            w("|---|---|---|---|---|---|---|")
            for k, n in three[:40]:
                w(f"| {k} | {n['type']} | {n['region']} | {n['px']} | {n['window_start']} | {n.get('cue')} | {n.get('cue_t')} |")
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
    prev = sorted(out.glob("perf_attempt*.json"))
    if prev:
        w("")
        w("同一版程式較早的效能量測（保留原始數據，沒有刪除；本節表格是最後一次 `perf.json`）：")
        for pf in prev:
            pj = json.loads(pf.read_text(encoding="utf-8"))
            acc = pj.get("acceptance") or {}
            slow = [dict(run=f"{r['quality']}{r['run']}", **x) for r in pj.get("runs", []) for x in r.get("slowFrames", [])]
            w(f"- `{pf.name}`：台詞時段內 > 100 ms {acc.get('over100msDuringLines')} 格、全部 > 100 ms {acc.get('over100ms')} 格；每格 > 50 ms：" + ("、".join(f"{x['run']} {x['cue']} {x['cueTime']} 秒 {x['frameMs']} ms（{x['duringLine'] or '非台詞'}）" for x in slow) or "無"))
    w("")
    if perf:
        w(f"- {perf['note']}")
        w(f"- 方法：{perf['method']}")
        m = perf["machine"]
        w(f"- 機器：{m['cpu']}，{m['cores']} 核，{m['memGB']} GB，{m['os']}；GPU：{perf['runs'][0]['gpu']}")
        w("")
        acc = perf.get("acceptance") or {}
        if acc:
            w(f"- 驗收條件：{acc.get('rule')}；台詞時段內 > 100 ms：{acc.get('over100msDuringLines')} 格；全部 > 100 ms：{acc.get('over100ms')} 格；每次都用 AudioContext 時鐘＝{acc.get('allClocksAudio')}。")
        sc = perf.get("school") or {}
        if sc:
            w(f"- 學校 Windows 筆電：**{sc.get('status')}**。{sc.get('todo')}")
        w("")
        w("| 畫質 | 第幾次 | 時鐘 | 預熱 ms | 播放中影格數 | 影格時間 中位 ms | p95 ms | p99 ms | 最長 ms | >33.4 ms | >50 ms | >100 ms | 台詞內 >100 ms | rAF 回呼 中位 ms | p95 ms | 最長 ms |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in perf["runs"]:
            f, c = r["frameIntervalMs"] or {}, r["rafCallbackMs"] or {}
            w(f"| {r['quality']} | {r.get('run', 1)} | {r.get('clock')} | {fmt(r.get('warmUpMs'), 0)} | {r['playingFrames']} | {fmt(f.get('median'), 2)} | {fmt(f.get('p95'), 2)} | {fmt(f.get('p99'), 2)} | {fmt(f.get('max'), 1)} | {r['over33ms']} | {r['over50ms']} | {r.get('over100ms', '—')} | {r.get('over100msDuringLines', '—')} | {fmt(c.get('median'), 2)} | {fmt(c.get('p95'), 2)} | {fmt(c.get('max'), 1)} |")
        w("")
        slow = [(r["quality"], r.get("run", 1), x) for r in perf["runs"] for x in r.get("slowFrames", [])]
        w(f"每格 > 50 ms 的時間點（全部 {len(slow)} 格）" + ("：" if slow else "。"))
        if slow:
            w("")
            w("| 畫質 | 第幾次 | cue | 距 cue 開始 ms | cue 內秒數 | 影格 ms | 台詞時段 |")
            w("|---|---|---|---|---|---|---|")
            for q, i, x in slow[:40]:
                w(f"| {q} | {i} | {x['cue']} | {x['msSinceCueStart']} | {x['cueTime']} | {x['frameMs']} | {x['duringLine'] or '—'} |")
        w("")
        w("逐 cue（畫質 A 第 1 次）：")
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
        dk = au.get("ducking_constants") or {}
        w(f"對白避讓 DUCK_LEVEL {dk.get('DUCK_LEVEL')}、DUCK_BRIDGE {dk.get('DUCK_BRIDGE')} 秒；教師停格 HOLD_MUSIC_RATIO {dk.get('HOLD_MUSIC_RATIO')}、時間常數 {dk.get('HOLD_TC')} 秒（`app/src/audio/ducking.ts`）。")
        w("")
        if au.get("freeze_holds"):
            w(f"{au.get('freeze_rule')}：")
            w("")
            w("| cue | 停住起點 s | 停住秒數 | 停住 0.4 秒時 LUFS | 第 3 秒 LUFS | 第 3 秒後最大 LUFS | ≤ −35 |")
            w("|---|---|---|---|---|---|---|")
            for h in au["freeze_holds"]:
                w(f"| {h['cue']} | {h['hold_from_sec']} | {h['hold_sec']} | {fmt(h['momentary_at_hold_start_LUFS'])} | {fmt(h['momentary_at_3s_LUFS'])} | {fmt(h['momentary_max_after_3s_LUFS'])} | {h['pass_le_-35']} |")
            w("")
        sp = au.get("segment_spread_lu")
        if sp:
            w(f"段落響度差 segment_spread_lu（{sp['rule']}）：全部段落 {sp['all_cues_lu']} LU、有台詞的段落 {sp['dialogue_cues_lu']} LU、各句台詞（混音中）{sp['dialogue_lines_lu']} LU。")
            if sp.get("layers_note"):
                w(f"分層數字：配音檔 {sp.get('vo_files_lu')} LU、各句對白（混音中）{sp.get('dialogue_lines_lu')} LU、主奏段 {sp.get('featured_music_lu')} LU（{sp.get('featured_music_I_LUFS')}）、劇情襯底段 {sp.get('underscore_lu')} LU（{sp.get('underscore_I_LUFS')}）。{sp['layers_note']}")
            w(f"裁決：{sp['decision']}。")
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
    if ss:
        w("### 字幕與語音的時間差（`subtitle_sync.json`）")
        w("")
        w(f"- {ss['method']}；通過範圍 {ss['range_s'][0]} s ≤ 差值 ≤ +{ss['range_s'][1]} s；全部通過＝{ss['all_pass']}")
        w("")
        w("| cue | 句子 | 頁 | 字幕 | 字幕起點 s | 語音起點 s | 差值 s | 通過 |")
        w("|---|---|---|---|---|---|---|---|")
        for r in ss["rows"]:
            w(f"| {r['cue']} | {r['line']} | {r['page']} | {r['text']} | {r['subtitle_start_s']} | {r['voice_start_s']} | {r['diff_s']:+.3f} | {'是' if r['pass'] else '**否**'} |")
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
        w(f"- 扣點定義（`{sa.get('attach_file', 'assets/final/rig/ale_attach.json')}`，primary）：" + "；".join(f"{k}＝{v['part']} {v['local_px']}" for k, v in sa["attach_points_primary"].items()))
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
    w("| `flash_variants.json` | 光敏細格 32×18、投影 v2 後 16×9 與 32×18 的分析 |")
    w("| `subtitle_sync.json` | 字幕頁起點與語音起點的差 |")
    w("| `kids_in_frame.json` | a2_c002、a2_c004 兒童頭與上半身是否在 90% 安全框內 |")
    w("")
    w("未驗證（代理無法量測）：聽感、實際投影機與教室燈光、學校 Windows 筆電效能（perf.json 的 school 欄）、HDMI 是否吞掉第一個音節（教師選單「開頭靜音」0／200／400 ms 要在學校實機試）。")
    (out / "INDEX.md").write_text("\n".join(x for x in L if x is not None) + "\n", encoding="utf-8")
    print(f"[g4pack.py] INDEX.md → {out / 'INDEX.md'}")


if __name__ == "__main__":
    cmd, out = sys.argv[1], Path(sys.argv[2]).resolve()
    if cmd == "analyze":
        analyze(out)
    elif cmd == "index":
        index(out)
    elif cmd == "decision":
        # 主線裁決 ±1 LU 範圍後：讀 review/G3/loudness_decision.json（{"decision": "...", "scope": "layers|dialogue_cues|all_cues"}），只更新 loudness.json 的裁決欄與 INDEX.md
        lj = out / "audio" / "loudness.json"
        dec = json.loads((ROOT / "review" / "G3" / "loudness_decision.json").read_text(encoding="utf-8"))
        au = json.loads(lj.read_text(encoding="utf-8"))
        au["segment_spread_lu"]["decision"] = dec["decision"]
        au["segment_spread_lu"]["decision_source"] = "review/G3/loudness_decision.json"
        lj.write_text(json.dumps(au, ensure_ascii=False, indent=1), encoding="utf-8")
        index(out)
    else:
        raise SystemExit(f"未知指令 {cmd}")
