"""新舊配音對照表（G3 修正清單第 13 項：edge-tts → Azure 重建後用）。

用法（專案根目錄）：
  cp audio/vo/build_report.json audio/vo/build_report_edge.json          # 重建前先留一份
  tools/.venv/bin/python tools/vo_build.py --all --service azure --version v03
  /opt/anaconda3/bin/python3 tools/vo_compare.py --before audio/vo/build_report_edge.json --after audio/vo/build_report.json \
      --out review/G3/azure_vs_edge.md
比較每句：檔案、服務、長度、整合響度、真峰值、削波、F0 中位、語速（毛／淨）、兩個轉寫模型的 CER 與判讀、停頓突波。
對嘴與 timings.json 由 vo_build.py 重建時一併更新。聽感未驗證。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def row(r: dict | None) -> dict:
    if not r:
        return {}
    m = r["metrics"]
    t = r.get("transcript", {})
    cer = {k: v["cer"] for k, v in t.get("models", {}).items()}
    return {"file": r["file"], "service": r["synthesis"][0]["service"], "s": m["seconds"], "I": m["integrated_lufs"],
            "TP": m["true_peak_dbtp"], "clip": m["clipped_samples"], "f0": m["f0_median"], "cps": m["rate_cps"],
            "net": m.get("rate_cps_net"), "cer": cer, "verdict": t.get("verdict", "—"), "spk": m.get("pause_spikes")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", default=str(ROOT / "review/G3/azure_vs_edge.md"))
    a = ap.parse_args()
    b = json.loads(Path(a.before).read_text("utf-8"))
    n = json.loads(Path(a.after).read_text("utf-8"))
    md = ["# 新舊配音對照", "", f"- 舊：`{a.before}`；新：`{a.after}`（tools/vo_compare.py）。聽感未驗證。", "",
          "| 句子 | 版本 | 服務 | 檔案 | 長度 s | LUFS | dBTP | 削波 | F0 中位 | 毛／淨 字/秒 | CER small／turbo | 判讀 | 停頓突波 |",
          "|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|"]
    for lid in sorted(set(b) | set(n)):
        for tag, r in (("舊", row(b.get(lid))), ("新", row(n.get(lid)))):
            if not r:
                md.append(f"| {lid} | {tag} | — | — | | | | | | | | | |")
                continue
            cer = "／".join(f"{v:.3f}" for v in r["cer"].values()) or "—"
            md.append(f"| {lid} | {tag} | {r['service']} | `{r['file']}` | {r['s']} | {r['I']} | {r['TP']} | {r['clip']} | {r['f0']} | "
                      f"{r['cps']}／{r['net']} | {cer} | {r['verdict']} | {r['spk']} |")
    Path(a.out).write_text("\n".join(md) + "\n", "utf-8")
    print("ok →", a.out)


if __name__ == "__main__":
    main()
