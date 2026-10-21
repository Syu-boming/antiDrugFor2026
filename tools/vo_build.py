"""配音一鍵重建（逐句一檔＋對嘴＋長度表）。

用法（在專案根目錄）：
  tools/.venv/bin/python tools/vo_build.py --set g4               # G4 代表鏡頭（a2_c001、a2_c002、a2_c004）
  tools/.venv/bin/python tools/vo_build.py --cue a2_c002          # 只重跑一個 cue
  tools/.venv/bin/python tools/vo_build.py --line a2_c002_01      # 只重跑一句
  tools/.venv/bin/python tools/vo_build.py --all                  # 全劇
  選項：--service edge（全部改用某服務的備用聲線，例如之後改 Azure）、--force（忽略合成快取重新呼叫）、
        --no-transcribe（略過轉寫比對）、--dry-run（只列出要做的句子與 ElevenLabs 預估字數）、
        --max-el-chars N（本次 ElevenLabs 新呼叫字數上限，預設 600，超過就中止）。

讀：audio/vo/casting.json（角色 → 服務、聲線、模型、參數、後處理）、audio/vo/pronounce.json（替身字）、
    script/劇本_v03.md（[台詞編號] 角色：台詞）。
寫：audio/vo/vo_<台詞編號>_<版本>.wav（48 kHz／單聲道／16-bit；頭 120 ms、尾 250 ms；−18 LUFS；真峰值 ≤ −1.5 dBTP）、
    audio/lipsync/<台詞編號>_<版本>.json（{"fps":12,"frames":[0–3]}，含義同 app/src/stage/perform.ts mouthOpen()）、
    audio/vo/timings.json（每句長度秒數等）、audio/vo/build_report.json（逐句量測與轉寫比對）。
金鑰：ElevenLabs 只從環境變數 ELEVENLABS_API_KEY 讀（或 .env），不印出、不寫入任何檔案。
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vo_lib as V  # noqa: E402

CASTING = V.VO_DIR / "casting.json"
SETS = {"g4": ["a2_c001", "a2_c002", "a2_c004"]}


def deep_merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def resolve_spec(casting: dict, role: str, line_id: str, service: str | None) -> dict:
    r = casting["roles"][role]
    spec = copy.deepcopy(r["spec"])
    if service and service != spec["service"]:
        if service in r.get("alt", {}):
            spec = copy.deepcopy(r["alt"][service])
        elif service == "azure" and spec["service"] == "edge":
            spec["service"] = "azure"          # Azure 與 edge-tts 同名聲線、同樣的 rate／pitch
        elif service == "azure" and r.get("alt", {}).get("edge"):
            spec = dict(copy.deepcopy(r["alt"]["edge"]), service="azure")
        else:
            raise SystemExit(f"{role} 沒有 {service} 備用聲線")
    spec.setdefault("post", r.get("post", {}))
    for ov in r.get("overrides", []):
        ov_svc = ov.get("service", spec["service"])
        if re.fullmatch(ov["match"], line_id) and (ov_svc == spec["service"] or {ov_svc, spec["service"]} == {"edge", "azure"}):
            spec = deep_merge(spec, ov["set"])
    return spec


SENT_RE = re.compile(r"(?<=[。！？])")


def plan_segments(synth_text: str, gap_ms: int | None) -> list[tuple[str, int | None]]:
    """合成用文字 → [(段落文字, 之後停頓毫秒)]：先依 [[break:N]] 分段，再依 post.sentence_gap_ms 依句號分句。"""
    out: list[tuple[str, int | None]] = []
    for text, brk in V.split_breaks(synth_text):
        parts = [p for p in SENT_RE.split(text) if p.strip()] if gap_ms else [text]
        for i, p in enumerate(parts):
            out.append((p, gap_ms if i < len(parts) - 1 else brk))
    return out


def render_line(line: dict, casting: dict, pron: dict, service: str | None, force: bool, purpose: str) -> tuple[np.ndarray, dict]:
    """合成一句（含多人同聲、分段加停頓、後處理），回傳母帶前的 48 kHz float 與紀錄。

    G3 修正第 1 輪：spec.synth_text（可含 [[break:N]]）優先於劇本原文；分段時每段去爆音、修到語音起訖（前 10 ms、後 80 ms），
    再做 10 ms 淡入／20 ms 淡出（升餘弦）後才接 N ms 靜音，不直接把全零樣本接在語音上；post.contour＝{"segment": i, "points": [...]}
    把第 i 段的 F0 改成指定走勢（例如「咦？」二聲上揚）。
    """
    roles = [r.strip() for r in line["role"].split("、")]
    mixes, notes = [], {"specs": [], "el_chars": 0}
    for role in roles:
        spec = resolve_spec(casting, role, line["id"], service)
        synth_text = V.apply_pronounce(spec.get("synth_text") or line["text"], pron, spec["service"], line["id"])
        post = spec.get("post", {})
        segs = plan_segments(synth_text, post.get("sentence_gap_ms"))
        contour = post.get("contour") or {}
        chunks, seg_log = [], []
        for i, (part, gap) in enumerate(segs):
            s = {k: v for k, v in spec.items() if k not in ("post", "synth_text", "note")}
            if s.get("segment_rates") and i < len(s["segment_rates"]):
                s["rate"] = s["segment_rates"][i]
            s.pop("segment_rates", None)
            raw, info = V.synth_raw(s, part, purpose=f"{purpose} {line['id']}", force=force)
            notes["el_chars"] += info.get("billed") or (info["chars"] if s["service"] == "elevenlabs" else 0)
            x = V.decode(raw)
            x, clicks = V.declick(x)
            rec = {"text": part, "rate": s.get("rate"), "gap_after_ms": gap, "declicked": clicks}
            if len(segs) > 1:
                a, b = V.speech_bounds(x)
                x = V.fade_edges(x[max(0, a - 480):min(len(x), b + int(0.08 * V.SR))], fin_ms=10, fout_ms=20)
            if contour and contour.get("segment") == i:
                x, cinfo = V.apply_contour(x, contour["points"])
                rec["contour"] = cinfo
                rec["rise_after"] = V.first_syllable_rise(x)
            if gap and i < len(segs) - 1:
                x = np.concatenate([x, np.zeros(int(gap / 1000 * V.SR), dtype=np.float32)])
            chunks.append(x)
            seg_log.append(rec)
        x = np.concatenate(chunks)
        notes.setdefault("segments", {})[role] = seg_log
        if post.get("max_pause_ms"):
            x, cut = V.cap_pauses(x, post["max_pause_ms"])
            if cut:
                notes.setdefault("pause_caps", []).extend(cut)
        if post.get("telephone"):
            from scipy.signal import butter, sosfiltfilt
            sos = butter(4, [300, 3400], btype="band", fs=V.SR, output="sos")
            x = sosfiltfilt(sos, x).astype(np.float32)
        mixes.append(x)
        notes["specs"].append({"role": role, "service": spec["service"],
                               **{k: spec.get(k) for k in ("voice", "voice_id", "voice_name", "model", "rate", "pitch",
                                                           "segment_rates", "settings", "seed", "language_code")
                                  if spec.get(k) is not None},
                               "post": post, "synth_text": synth_text})
    if len(mixes) > 1:
        n = max(len(m) for m in mixes)
        x = sum(np.pad(m, (0, n - len(m))) for m in mixes) * (1 / len(mixes)) ** 0.5
    else:
        x = mixes[0]
    return x.astype(np.float32), notes


def build(ids: list[str], args) -> list[dict]:
    casting = json.loads(CASTING.read_text(encoding="utf-8"))
    pron = V.load_pronounce()
    lines = V.load_lines()
    d = casting["defaults"]
    ver = args.version or d.get("version", "v01")
    # 預估 ElevenLabs 新呼叫字數
    est = 0
    for lid in ids:
        ln = lines[lid]
        for role in ln["role"].split("、"):
            spec = resolve_spec(casting, role.strip(), lid, args.service)
            if spec["service"] == "elevenlabs":
                t = V.apply_pronounce(ln["text"], pron, "elevenlabs", lid)
                s = {k: v for k, v in spec.items() if k != "post"}
                if args.force or not V._cache_path(s, t, "mp3").exists():
                    est += len(t)
    print(f"共 {len(ids)} 句；ElevenLabs 預估新呼叫 {est} 字元（上限 {args.max_el_chars}）")
    if args.dry_run:
        for lid in ids:
            print(" ", lid, lines[lid]["role"], lines[lid]["text"])
        return []
    if est > args.max_el_chars:
        raise SystemExit("超過本次 ElevenLabs 字數上限，中止（用 --max-el-chars 調整）")
    results = []
    for lid in ids:
        ln = lines[lid]
        x, notes = render_line(ln, casting, pron, args.service, args.force, "正式配音")
        y, minfo = V.master(x, target=d["target_lufs"], tp_max=d["true_peak_max"], head_ms=d["head_ms"],
                            tail_ms=d["tail_ms"], short_s=d.get("short_line_s", 3.0))
        off = 0.0
        for role in ln["role"].split("、"):
            off = casting["roles"][role.strip()].get("loudness_offset_db", {}).get(lid, off)
        if off:
            y = (y * 10 ** (off / 20)).astype(np.float32)
            minfo["loudness_offset_db"] = off
        wav = V.VO_DIR / f"vo_{lid}_{ver}.wav"
        V.write_wav(wav, y)
        lip = V.lipsync(y, fps=d.get("lipsync_fps", 12))
        V.LIP_DIR.mkdir(parents=True, exist_ok=True)
        (V.LIP_DIR / f"{lid}_{ver}.json").write_text(json.dumps(lip, separators=(",", ":")), "utf-8")
        m = V.measure(wav, ln["text"])
        rec = {"id": lid, "role": ln["role"], "text": ln["text"], "file": m["file"],
               "lipsync": str((V.LIP_DIR / f"{lid}_{ver}.json").relative_to(V.ROOT)),
               "seconds": m["seconds"], "speech_start": minfo["speech_start"], "speech_end": minfo["speech_end"],
               "master": minfo, "metrics": m, "synthesis": notes["specs"], "el_chars_billed": notes["el_chars"],
               "pause_caps_ms": notes.get("pause_caps", []), "segments": notes.get("segments", {}),
               "speech_segments": V.speech_segments(y)}
        results.append(rec)
        print(f"{lid} {ln['role']} {m['seconds']:.2f}s I={m['integrated_lufs']} TP={m['true_peak_dbtp']} "
              f"{m['rate_cps']}字/秒 F0={m['f0_median']} 削波={m['clipped_samples']}")
    if not args.no_transcribe and results:
        tc = V.transcribe_compare([(V.ROOT / r["file"], r["text"], V.strip_breaks(r["synthesis"][0]["synth_text"]))
                                   for r in results])
        for r in results:
            r["transcript"] = tc[str(V.ROOT / r["file"])]
            ms = r["transcript"]["models"]
            print(f"  {r['id']} " + "｜".join(f"{k}：{v['hyp_trad']}（PER {v['per']}）" for k, v in ms.items())
                  + f"｜{r['transcript']['verdict']}")
    # 合併寫回 timings.json 與 build_report.json
    tpath = V.VO_DIR / "timings.json"
    timings = json.loads(tpath.read_text("utf-8")) if tpath.exists() else {}
    rpath = V.VO_DIR / "build_report.json"
    report = json.loads(rpath.read_text("utf-8")) if rpath.exists() else {}
    for r in results:
        timings[r["id"]] = {"seconds": r["seconds"], "speech_start": r["speech_start"], "speech_end": r["speech_end"],
                            "speech_segments": r["speech_segments"],
                            "file": r["file"], "lipsync": r["lipsync"], "role": r["role"], "text": r["text"]}
        report[r["id"]] = r
    timings = dict(sorted(timings.items()))
    tpath.write_text(json.dumps(timings, ensure_ascii=False, indent=1), "utf-8")
    rpath.write_text(json.dumps(dict(sorted(report.items())), ensure_ascii=False, indent=1), "utf-8")
    billed = sum(r["el_chars_billed"] for r in results)
    print(f"完成 {len(results)} 句；本次 ElevenLabs 實際計費 {billed} 字元")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cue", action="append", default=[])
    ap.add_argument("--line", action="append", default=[])
    ap.add_argument("--set", choices=sorted(SETS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--service")
    ap.add_argument("--version")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-transcribe", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-el-chars", type=int, default=600)
    args = ap.parse_args()
    lines = V.load_lines()
    cues = list(args.cue) + (SETS[args.set] if args.set else [])
    ids = [l for l in lines if args.all or l in args.line or lines[l]["cue"] in cues]
    if not ids:
        raise SystemExit("沒有符合的台詞（用 --cue／--line／--set／--all）")
    build(ids, args)


if __name__ == "__main__":
    main()
