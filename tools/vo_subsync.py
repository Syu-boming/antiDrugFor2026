"""字幕與語音的時間差表（G3 修正清單第 14 項）。

用法：/opt/anaconda3/bin/python3 tools/vo_subsync.py [--timeline review/G4/pack/timeline.json]
做法：讀 G4 擷取的 timeline.json（每句的字幕頁起訖），配音改用最新版本並依 cue 規則重排時間（同 tools/vo_mixsim.py 的 retime），
      用 ffmpeg silencedetect（noise=−45 dB、d=0.1 s）找每個配音檔的語音起點（第一個 silence_end；之後的 silence_end＝句中停頓後的起點）。
      第 1 頁的語音起點＝檔案的第一個起點；之後各頁取「頁起點前後最接近的停頓後起點」。
      差值＝字幕頁起點 −（句子起點＋該頁語音起點）；自動檢查 −0.8 s ≤ 差值 ≤ +0.1 s（字幕可以早出現最多 0.8 秒，不能晚於語音 0.1 秒以上）。
寫：review/G3/subtitle_sync.json、review/G3/subtitle_sync.md。
引擎改了字幕分頁或時間後，重新擷取 G4（timeline.json 會更新）再跑一次。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from vo_mixsim import retime  # noqa: E402

LO, HI = -0.8, 0.1


def onsets(path: Path) -> list[float]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "silencedetect=noise=-45dB:d=0.1",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    out = []
    if not starts or starts[0] > 0.01:
        out.append(0.0)
    out += ends
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=str(ROOT / "review/G4/pack/timeline.json"))
    a = ap.parse_args()
    tl = retime(json.loads(Path(a.timeline).read_text("utf-8")))
    rows = []
    for c in tl["cues"]:
        for l in c["lines"]:
            src = ROOT / tl["audio"][l["audioId"]]["source"]
            ons = onsets(src)
            for k, pg in enumerate(l.get("pages") or [{"start": l["start"], "end": l["end"], "rows": [l["text"]]}]):
                rel = pg["start"] - l["start"]
                if k == 0:
                    on = ons[0]
                else:
                    cand = [o for o in ons if o >= rel + LO]
                    on = min(cand, key=lambda o: abs(o - rel)) if cand else ons[-1]
                d = round(pg["start"] - (l["start"] + on), 3)
                rows.append({"cue": c["id"], "line": l["id"], "page": k + 1, "text": "／".join(pg.get("rows", [])),
                             "subtitle_start_s": round(pg["start"], 3), "line_start_s": round(l["start"], 3),
                             "voice_onset_in_file_s": round(on, 3), "voice_start_s": round(l["start"] + on, 3),
                             "diff_s": d, "pass": LO <= d <= HI, "audio": str(src.relative_to(ROOT))})
    res = {"_說明": __doc__.strip().splitlines()[0], "method": "ffmpeg silencedetect noise=-45dB d=0.1；差值＝字幕頁起點−語音起點",
           "range_s": [LO, HI], "timeline": str(Path(a.timeline).resolve().relative_to(ROOT)), "rows": rows,
           "all_pass": all(r["pass"] for r in rows)}
    (ROOT / "review/G3/subtitle_sync.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    md = ["# 字幕與語音的時間差（G3 修正第 14 項）", "",
          f"- 產生：`tools/vo_subsync.py`；字幕頁時間取自 `{res['timeline']}`，配音取最新版本並依 cue 規則重排（同 `tools/vo_mixsim.py`）。",
          "- 語音起點：ffmpeg silencedetect（−45 dB、0.1 s）。差值＝字幕頁起點 − 語音起點；通過範圍 −0.8 s ≤ 差值 ≤ +0.1 s。",
          "- 引擎目前依字數比例分配各頁時間（`app/src/cues/timeline.ts` paginate），不看實際停頓；第 2 頁以後對到「頁起點前後最接近的停頓後起點」。"
          "建議引擎改用 `audio/vo/timings.json` 的 `speech_segments`（每段語音起訖）對齊分頁，差值可以全部收斂到約 −0.13 s。", "",
          "| cue | 句子 | 頁 | 字幕 | 字幕起點 s | 語音起點 s | 差值 s | 通過 | 配音檔 |", "|---|---|---:|---|---:|---:|---:|---|---|"]
    for r in rows:
        md.append(f"| {r['cue']} | {r['line']} | {r['page']} | {r['text']} | {r['subtitle_start_s']} | {r['voice_start_s']} | "
                  f"{r['diff_s']:+.3f} | {'是' if r['pass'] else '**否**'} | `{r['audio']}` |")
    md += ["", f"全部通過：{'是' if res['all_pass'] else '否'}"]
    (ROOT / "review/G3/subtitle_sync.md").write_text("\n".join(md) + "\n", "utf-8")
    print("\n".join(md[-len(rows) - 2:]))


if __name__ == "__main__":
    main()
