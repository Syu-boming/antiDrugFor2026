"""配音波形接觸表：每檔一列（波形＋語音起訖線＋F0 曲線；G4 正式台詞另疊對嘴格）。

用法：tools/.venv/bin/python tools/vo_sheet.py   （需要 matplotlib：以 /opt/anaconda3/bin/python3 執行亦可）
輸出：review/G3/vo_waveforms_g3.png（G3 試音樣本）、review/G3/vo_waveforms_g4.png（G4 正式台詞＋對嘴）。
用途：讓驗收者看得到句頭 120 ms／句尾 250 ms 靜音、句尾是否被截斷、停頓位置、音高範圍與對嘴開合。
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
for fam in ("PingFang TC", "Heiti TC", "Arial Unicode MS", "Noto Sans CJK TC"):
    from matplotlib import font_manager
    if any(fam == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = fam
        break


def read(path: Path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    return sr, x


def f0(path: Path):
    try:
        import parselmouth
    except ImportError:
        return None, None
    p = parselmouth.Sound(str(path)).to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=700)
    fr = p.selected_array["frequency"]
    fr[fr == 0] = np.nan
    return p.xs(), fr


def sheet(items: list[dict], out: Path, title: str) -> None:
    n = len(items)
    fig, axes = plt.subplots(n, 1, figsize=(14, 1.15 * n + 0.8), squeeze=False)
    tmax = max(it["seconds"] for it in items)
    for ax, it in zip(axes[:, 0], items):
        sr, x = read(ROOT / it["file"])
        t = np.arange(len(x)) / sr
        ax.plot(t, x, lw=0.4, color="#335")
        ax.axvspan(0, 0.12, color="#9c9", alpha=0.25)
        ax.axvspan(len(x) / sr - 0.25, len(x) / sr, color="#9c9", alpha=0.25)
        if it.get("speech"):
            for v in it["speech"]:
                ax.axvline(v, color="#c33", lw=0.8)
        ax.set_xlim(0, tmax)
        ax.set_ylim(-1, 1)
        ax.set_yticks([])
        ax.tick_params(axis="x", labelsize=6)
        ax.text(0.002, 0.95, it["label"], transform=ax.transAxes, fontsize=7, va="top")
        ft, fv = f0(ROOT / it["file"])
        if ft is not None:
            ax2 = ax.twinx()
            ax2.plot(ft, fv, ".", ms=1.2, color="#d80")
            ax2.set_ylim(60, 500)
            ax2.tick_params(axis="y", labelsize=5)
        if it.get("lip"):
            lp = it["lip"]
            lt = np.arange(len(lp["frames"])) / lp["fps"]
            ax.step(lt, np.array(lp["frames"]) / 3 * 0.9 - 0.95, where="post", color="#09c", lw=0.8)
    fig.suptitle(title, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main():
    g3 = json.loads((ROOT / "review/G3/metrics.json").read_text("utf-8"))["samples"]
    items = []
    for n, r in g3.items():
        items.append({"file": r["file"], "seconds": r["seconds"],
                      "label": f"{n}｜{r['rate_cps']} 字/秒｜F0 中位 {r['f0_median']} Hz｜{r['integrated_lufs']} LUFS／{r['true_peak_dbtp']} dBTP"})
    sheet(items, ROOT / "review/G3/vo_waveforms_g3.png",
          "G3 試音樣本：藍＝波形、橘點＝F0（右軸 60–500 Hz）、綠底＝頭 120 ms／尾 250 ms 靜音區")
    rep = json.loads((ROOT / "audio/vo/build_report.json").read_text("utf-8"))
    items = []
    for lid, r in rep.items():
        lip = json.loads((ROOT / r["lipsync"]).read_text("utf-8"))
        m = r["metrics"]
        items.append({"file": r["file"], "seconds": r["seconds"], "speech": [r["speech_start"], r["speech_end"]], "lip": lip,
                      "label": f"{lid} {r['role']}：{r['text']}｜{m['rate_cps']} 字/秒｜F0 {m['f0_median']} Hz｜{m['integrated_lufs']} LUFS"})
    sheet(items, ROOT / "review/G3/vo_waveforms_g4.png",
          "G4 正式台詞：藍＝波形、紅線＝語音起訖、橘點＝F0、青色階梯＝對嘴格（0 閉、1 半開、2 大開、3 圓唇；每秒 12 格）")
    print("ok")


if __name__ == "__main__":
    main()
