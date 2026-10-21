import json
import sys
from pathlib import Path

ROOT = Path("/Users/boming/Documents/AI tool/反毒小劇場")
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
import vo_lib as V  # noqa: E402

T = ROOT / "review/G3/el/full/trial/kids"
tags = sys.argv[1:] or sorted(p.name for p in T.iterdir() if p.is_dir())
for tag in tags:
    p = T / tag / "build_report_trial.json"
    if not p.exists():
        continue
    R = json.loads(p.read_text("utf-8"))
    f0s = []
    print(f"=== {tag}")
    for lid, e in R.items():
        for a in e["attempts"]:
            m = a["metrics"]
            ps = [s.get("psola") for s in a["segments"] if s.get("psola")]
            st = ps[0]["stretch"] if ps else 1.0
            rb = ps[0]["rate_before"] if ps else None
            f0s.append(m["f0_median"])
            extra = ""
            if lid in ("a2_c002_01", "a1_c008_01", "a4_c013_03"):
                y = V.read_wav(ROOT / a["wav"])
                r = V.first_syllable_rise(y)
                extra = f" 咦={r.get('end_over_start')}"
            asr = " | ".join(v["hyp_trad"] for v in a["asr"].values())
            print(f" {lid} a{a['k']} fail={','.join(a['failed']) or '-'} rate={a['checks']['d']['value']} pre={rb} x{st} "
                  f"F0={m['f0_median']} pauses={a['checks']['e']['pauses_ms']} tail={[s['tail']['last60ms_rel_dB'] for s in a['segments']]}"
                  f" spd={list(a['settings'].values())[0].get('speed')}{extra} :: {asr}")
    f0s = [f for f in f0s if f]
    if f0s:
        print(f" F0 median of medians {np.median(f0s):.1f}")
