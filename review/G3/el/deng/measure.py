"""「燈」聲調量測：對指定版本（v04／v05）逐句做字級時間戳＋F0，寫 tracks_<ver>.json（給 plot.py 與判定）。

用法（專案根目錄）：tools/.venv/bin/python review/G3/el/deng/measure.py --ver v04 [--ids a0_c002_03 ...] [--refs]
--refs：連同劇本裡已替換成「登」的參考句（紙登結、登籠）一起量（目標字改成「燈」，即原文的燈＝送出的登）。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
import vo_lib as V  # noqa: E402
import vo_tone_check as T  # noqa: E402

HERE = Path(__file__).resolve().parent
TARGETS = ("a0_c001_01 a0_c002_03 a0_c003_01 a0_c003_02 a0_c003_04 a0_c005_02 a0_c005_03 a1_c001_03 a1_c001_05 "
           "a1_c007_01 a2_c011_01 a2_c013_05 a4_c007_01 a5_c001_01 a5_c004_01 a5_c006_02 a5_c007_01 a6_c001_01 "
           "a6_c001_02 a6_c007_02 a6_c007_03 a6_c009_03 a7_c003_02 a8_c001_01").split()
REFS = "a0_c002_02 a1_c001_01 a1_c001_04 a1_c004_06 a2_c013_04 a6_c007_01 a6_c009_01 a3_c008_01".split()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", default="v04")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--refs", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--files", nargs="*", help="<鍵>=<台詞編號>:<wav 路徑>（量指定檔，例如 _attempts 的嘗試檔）")
    ap.add_argument("--reuse", action="store_true", help="沿用 tracks 檔裡的字窗（不重新轉寫），只重算 F0 特徵與判定")
    a = ap.parse_args()
    L = V.load_lines()
    P = V.load_pronounce()
    ids = a.ids or (TARGETS + (REFS if a.refs else []))
    out_p = Path(a.out) if a.out else HERE / f"tracks_{a.ver}.json"
    res = json.loads(out_p.read_text("utf-8")) if out_p.exists() else {}
    jobs = [(lid, lid, ROOT / "audio/vo" / f"vo_{lid}_{a.ver}.wav") for lid in ids]
    if a.files:
        jobs = []
        for spec in a.files:
            key, rest = spec.split("=", 1)
            lid, path = rest.split(":", 1)
            jobs.append((key, lid, ROOT / path))
    for key, lid, wav in jobs:
        if not wav.exists():
            print(lid, "沒有", wav.name)
            continue
        text = L[lid]["text"]
        win = None
        if a.reuse and key in res:
            o = res[key]
            win = (o["asr"], [[c["s"], c["e"], c.get("asr")] if "s" in c else None for c in o["chars"]])
        r = T.measure_file(wav, text, "燈", win)
        sent = V.apply_pronounce(text, P, "elevenlabs", lid)
        ref_sent = V.PUNCT_RE.sub("", sent)
        # 每個「燈」實際送出的字（燈／登）
        for c in r["chars"]:
            c["sent"] = ref_sent[c["i"]] if c["i"] < len(ref_sent) and len(ref_sent) == len(r["chars"]) else None
        x = V.read_wav(wav)
        t, f = T.pitch_track(x)
        db = V.frame_db(x)
        r.update(id=lid, key=key, role=L[lid]["role"], ver=a.ver, synth_text=sent, wav=str(wav.relative_to(ROOT)),
                 track={"t": [round(float(v), 3) for v in t], "f0": [round(float(v), 1) for v in f],
                        "db": [round(float(v), 1) for v in db]})
        tg = [c for c in r["chars"] if c["i"] in r["targets"]]
        for c in tg:
            c["verdict"], c["why"] = T.classify(c)
            c["vs_tone1"] = T.vs_tone1(r["chars"], c["i"])
            prev = r["chars"][c["i"] - 1] if c["i"] > 0 else None
            c["prev"] = f"{prev['ch']}（{prev['tone']} 聲）" if prev else None
        res[key] = r
        print(key, r["role"], "ASR", r["asr"], "|", "；".join(
            f"#{c['i']} 送出{c['sent']} {c.get('t0')}-{c.get('t1')} {c['verdict']}｜{c['why']}｜比同句一聲字 {c['vs_tone1']}｜前字 {c['prev']}"
            for c in tg))
        out_p.write_text(json.dumps(res, ensure_ascii=False, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)),
                         "utf-8")


if __name__ == "__main__":
    main()
