"""把 ElevenLabs 全劇版升為正式配音（使用者決定 D-G3-07：全部改用 ElevenLabs，不用 edge-tts）。

用法（專案根目錄）：
  tools/.venv/bin/python tools/vo_el_promote.py --check          # 只檢查：每句都有 EL 檔、對嘴、時間資料（不寫檔）
  tools/.venv/bin/python tools/vo_el_promote.py                  # 升級：v04＝EL；edge 舊檔移到 audio/_archive_edge/
  tools/.venv/bin/python tools/vo_el_promote.py --line <id> ...  # 只重升指定台詞（例如某句重算後）
  tools/.venv/bin/python tools/vo_el_promote.py --pick <id>=<檔案> --line <id>   # 指定採用某次合成（_attempts 的母帶 wav，
                                                                 # 或 vo_el_variants.py 的原始 mp3，會先依同規格做母帶）
做法：
  1. 第一次升級時把 audio/vo/vo_*_v01–v03.wav 與 audio/lipsync/*_v01–v03.json（都是 edge-tts）移到 audio/_archive_edge/，
     tools/pack.mjs 取最新版本號，移走後只會讀到 v04（ElevenLabs）。原檔不刪，只封存。
  2. audio/vo_el/vo_<id>_el01.wav → audio/vo/vo_<id>_v04.wav；audio/lipsync_el/<id>_el01.json → audio/lipsync/<id>_v04.json。
  3. audio/vo/timings.json 每句改指向 v04（秒數、語音起訖、句中段落取自 audio/vo_el/timings_el.json）。
  4. audio/vo/casting.json 加 official_engine（ElevenLabs、各角色聲線與設定檔）；defaults.version 改 v04。
  5. 寫 audio/vo/promoted_el.json：每句來源、sha1、自動檢查狀態、request_id。
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vo_lib as V  # noqa: E402

VO, LIP, ARC = ROOT / "audio/vo", ROOT / "audio/lipsync", ROOT / "audio/_archive_edge"
EL = ROOT / "audio/vo_el"
VER = "v04"


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def pick(lid: str, src: str) -> None:
    """把指定的一次合成寫成 audio/vo_el 的採用檔（含對嘴、時間資料），並記進 build_report_el.json 的 manual_pick。"""
    import subprocess
    import tempfile
    p = (ROOT / src).resolve()
    cast = json.loads((VO / "casting.json").read_text("utf-8"))["defaults"]
    if p.suffix == ".wav" and "_attempts" in p.parts:
        y, minfo = V.read_wav(p), {"method": "沿用 _attempts 母帶"}
    else:
        with tempfile.TemporaryDirectory() as td:
            w = Path(td) / "x.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ac", "1", "-ar", str(V.SR), str(w)], check=True)
            y, minfo = V.master(V.read_wav(w), target=cast["target_lufs"], tp_max=cast["true_peak_max"],
                                head_ms=cast["head_ms"], tail_ms=cast["tail_ms"])
    final = EL / f"vo_{lid}_el01.wav"
    V.write_wav(final, y)
    y = V.read_wav(final)
    lip = V.lipsync(y, fps=cast.get("lipsync_fps", 12))
    lp = ROOT / "audio/lipsync_el" / f"{lid}_el01.json"
    lp.write_text(json.dumps(lip, separators=(",", ":")), "utf-8")
    segs = V.speech_segments(y)
    rep_p, tel_p = EL / "build_report_el.json", EL / "timings_el.json"
    rep, tel = json.loads(rep_p.read_text("utf-8")), json.loads(tel_p.read_text("utf-8"))
    e = rep[lid]
    e["manual_pick"] = {"source": str(p.relative_to(ROOT)), "master": {k: v for k, v in minfo.items() if not isinstance(v, (list, dict))},
                        "time": time.strftime("%Y-%m-%d %H:%M:%S"), "note": "主線／使用者指定採用（自動檢查結果見 attempts 或 review/G3/el/full/fix_*）"}
    e.update({"file": str(final.relative_to(ROOT)), "lipsync": str(lp.relative_to(ROOT)), "seconds": round(len(y) / V.SR, 3),
              "speech_start": segs[0][0] if segs else 0.0, "speech_end": segs[-1][1] if segs else 0.0, "speech_segments": segs})
    tel[lid] = {k: e[k] for k in ("seconds", "speech_start", "speech_end", "speech_segments", "file", "lipsync", "role", "text")}
    rep_p.write_text(json.dumps(rep, ensure_ascii=False, indent=1), "utf-8")
    tel_p.write_text(json.dumps(tel, ensure_ascii=False, indent=1), "utf-8")
    print(f"{lid}：採用 {p.relative_to(ROOT)}（{e['seconds']} 秒）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--line", action="append")
    ap.add_argument("--pick", action="append", default=[], help="<台詞編號>=<檔案>：指定採用的合成")
    a = ap.parse_args()
    for spec in a.pick:
        pick(*spec.split("=", 1))
    lines = V.load_lines()
    rep = json.loads((EL / "build_report_el.json").read_text("utf-8"))
    tel = json.loads((EL / "timings_el.json").read_text("utf-8"))
    ids = a.line or [i for i in lines if lines[i].get("role")]
    missing, todo = [], []
    for i in ids:
        r = rep.get(i)
        wav = ROOT / r["file"] if r and r.get("file") else None
        lip = ROOT / r["lipsync"] if r and r.get("lipsync") else None
        if not (wav and wav.exists() and lip and lip.exists() and i in tel):
            missing.append(i)
        else:
            todo.append((i, r, wav, lip))
    print(f"台詞 {len(ids)} 句：可升級 {len(todo)}、缺檔 {len(missing)}")
    if missing:
        print("缺 EL 檔／對嘴／時間資料：", " ".join(missing))
    fails = [i for i, r, _, _ in todo if r.get("status") != "pass"]
    if fails:
        print(f"自動檢查未通過但仍升級（由驗收與使用者聽感判定）{len(fails)} 句：", " ".join(fails))
    if a.check or missing and not a.line:
        sys.exit(1 if missing else 0)

    # 1. 封存 edge 舊檔（只做一次；已封存的不重搬）
    moved = 0
    for src_dir, sub, pat in ((VO, "vo", "vo_*_v0[123].wav"), (LIP, "lipsync", "*_v0[123].json")):
        for p in sorted(src_dir.glob(pat)):
            dst = ARC / sub / p.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dst))
            moved += 1
    if moved:
        (ARC / "README.md").write_text(
            "# edge-tts 舊配音封存\n\n使用者 2026-10-21 決定全劇改用 ElevenLabs、不用 edge-tts（DECISIONS.md D-G3-07）。\n"
            "這裡是原本 audio/vo 與 audio/lipsync 的 v01–v03（edge-tts 7.3.1）檔案，只封存、不打包（tools/pack.mjs 不讀這個資料夾）。\n"
            "要刪除時由使用者決定。\n", "utf-8")
    # 2–3. 複製 v04、更新 timings
    tpath = VO / "timings.json"
    timings = json.loads(tpath.read_text("utf-8")) if tpath.exists() else {}
    prom_path = VO / "promoted_el.json"
    prom = json.loads(prom_path.read_text("utf-8")) if prom_path.exists() else {"_說明": "ElevenLabs 全劇版升為正式 v04 的紀錄（tools/vo_el_promote.py）", "lines": {}}
    for i, r, wav, lip in todo:
        dw, dl = VO / f"vo_{i}_{VER}.wav", LIP / f"{i}_{VER}.json"
        shutil.copy2(wav, dw)
        shutil.copy2(lip, dl)
        t = dict(tel[i])
        t["file"], t["lipsync"] = str(dw.relative_to(ROOT)), str(dl.relative_to(ROOT))
        t["engine"] = "elevenlabs"
        timings[i] = t
        prom["lines"][i] = {"role": r.get("role"), "source": r["file"], "lipsync_source": r["lipsync"], "file": t["file"],
                            "sha1": sha1(dw), "status": r.get("status"), "failed": r.get("failed"),
                            "request_ids": r.get("request_ids"), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    # timings 裡指向已封存 edge 檔的舊條目：移除（避免指到不存在的檔）
    for k in [k for k, v in timings.items() if isinstance(v, dict) and not (ROOT / v.get("file", "")).exists()]:
        timings.pop(k)
    tpath.write_text(json.dumps(timings, ensure_ascii=False, indent=1), "utf-8")
    prom_path.write_text(json.dumps(prom, ensure_ascii=False, indent=1), "utf-8")
    # 4. casting.json
    cpath = VO / "casting.json"
    cast = json.loads(cpath.read_text("utf-8"))
    roles = {}
    for f in sorted((EL / "casting").glob("*.json")):
        d = json.loads(f.read_text("utf-8"))
        roles[d["role"]] = {"code": d["code"], "voice_id": d["voice_id"], "voice_name": d["voice_name"], "model": d["model"],
                            "config": str(f.relative_to(ROOT))}
    cast["official_engine"] = {
        "service": "elevenlabs", "since": "2026-10-21", "decision": "DECISIONS.md D-G3-07（使用者：全部改用 ElevenLabs，不用 edge-tts）",
        "build": "tools/vo_el_prod.py（合成＋自動檢查）→ tools/vo_el_promote.py（升為 audio/vo 的 v04）",
        "license": "Starter 付費方案；兒童用途書面核准待 ElevenLabs 回覆（review/G3/el/license_evidence.md）",
        "roles": roles,
        "edge_archive": "audio/_archive_edge/（舊 edge-tts 檔，只封存）；下方 services／roles 的 edge 設定只留作紀錄，不再用於演出",
    }
    cast.setdefault("defaults", {})["version"] = VER
    cpath.write_text(json.dumps(cast, ensure_ascii=False, indent=1), "utf-8")
    print(f"已升級 {len(todo)} 句為 {VER}；封存 edge 舊檔 {moved} 個；timings.json {len(timings)} 筆")


if __name__ == "__main__":
    main()
