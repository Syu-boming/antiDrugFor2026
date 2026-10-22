"""把 tracks_<ver>.json 畫成逐句 F0 圖（半音，相對該檔中位數）＋字窗＋「燈」音節核心。
用法：/opt/anaconda3/bin/python3 review/G3/el/deng/plot.py --ver v04 [--ids ...]  → plots_<ver>/<id>.png
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

matplotlib.rcParams["font.family"] = ["Heiti TC"]
HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", default="v04")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--tracks")
    a = ap.parse_args()
    R = json.loads((Path(a.tracks) if a.tracks else HERE / f"tracks_{a.ver}.json").read_text("utf-8"))
    od = HERE / f"plots_{a.ver}"
    od.mkdir(exist_ok=True)
    for lid in a.ids or R:
        r = R[lid]
        t, f, db = np.array(r["track"]["t"]), np.array(r["track"]["f0"]), np.array(r["track"]["db"])
        med = r["f0_median"]
        st = np.where(f > 0, 12 * np.log2(np.maximum(f, 1) / med), np.nan)
        fig, ax = plt.subplots(figsize=(max(6, t[-1] * 2.2), 3.2), dpi=90)
        ax.plot(t, st, ".", ms=2.5, color="#1f5fa8")
        ax.axhline(12 * np.log2(r["f0_p10"] / med), color="#aaa", lw=0.6, ls="--")
        ax.axhline(12 * np.log2(r["f0_p90"] / med), color="#aaa", lw=0.6, ls="--")
        ax.axhline(0, color="#ccc", lw=0.6)
        ax2 = ax.twinx()
        ax2.plot(0.01 * (np.arange(len(db)) + 1), db, color="#d9a441", lw=0.6)
        ax2.set_yticks([])
        for c in r["chars"]:
            if "s" not in c:
                continue
            tg = c["i"] in r["targets"]
            ax.axvspan(c["s"], c["e"], color="#f4c7c3" if tg else ("#eeeeee" if c["i"] % 2 else "#ffffff"), alpha=0.6, lw=0)
            ax.text((c["s"] + c["e"]) / 2, 9.5, f"{c['ch']}{c['tone']}", ha="center", fontsize=9,
                    color="#b3261e" if tg else "#333")
            if "t0" in c:
                ax.plot([c["t0"], c["t1"]], [c["start_st"], c["end_st"]], "-", color="#b3261e" if tg else "#2e7d32", lw=2)
        ax.set_ylim(-12, 11)
        ax.set_xlim(0, t[-1])
        ax.set_title(f"{lid} {r['role']} {r['ver']}｜{r['text']}｜中位數 {med} Hz", fontsize=9)
        ax.set_ylabel("半音（相對中位數）")
        fig.tight_layout()
        fig.savefig(od / f"{lid}.png")
        plt.close(fig)


if __name__ == "__main__":
    main()
