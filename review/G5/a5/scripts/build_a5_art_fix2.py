"""第五幕修正第 2 輪：素材（b2r2_failed／b2r2_regress 的 a5 美術條目）。

- 導護旗 a5-flag_v01（正面）、a5-flag-back_v01（背面：轉角後面只露出一角、陳伯伯背對這邊）：
  同第四幕旗子的畫布比例與旗桿位置（程式的握點不變），2 倍解析度；旗面兩道摺痕、紙纖維、白色紙芯邊＋深色細線、旗桿木紋。
- 校門口景片（第四幕 gate 的 school-building、school-wall、folding-gate、guard-house、pillar）：
  paperize（放大、紙片浮雕、深色線投影、紙纖維、紙邊）後存成 sets/a5_gate/set-gate_*（只有第五幕的 a5_gate 會讀到：
  imageSet 先找 sets/<景名>/<id>；第四幕 gate 景、gate.ts、第四幕的圖都不動）。
- 救護車 v03、後車門 v02、擔架 v03、街角小店 v02：同一套 paperize（比例不變，程式裡的寬度常數不用改）。
- 轉角的低年級小朋友 v03：Codex 生成的同畫風紙片小人（review/G5/a5/raw/a5_student_v03.png）切成身體＋揮手手臂（見 student_v03）。

用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/build_a5_art_fix2.py [--only flag,gate,props,student]
輸出：assets/final/sets/a5_gate/…；review/G5/a5/art_meta.json 的 fix2 鍵。
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paperdraw as P  # noqa: E402
from paperize import paperize, add_white_border  # noqa: E402

FINAL = ROOT / "assets/final/sets"
SRC = FINAL / "a5_gate"
OUT = Path(os.environ.get("A5_ART_OUT") or SRC)   # 預覽時可改寫到 scratch
META = ROOT / "review/G5/a5/art_meta.json"

LIME = (214, 224, 86, 255)
LIME_D = (190, 202, 70, 255)
LIME_L = (228, 236, 120, 255)
STRIPE = (242, 238, 212, 255)
POLE = (178, 140, 92, 255)
POLE_D = (150, 114, 72, 255)


def flag(back=False):
    """畫布 672×1088（= 第四幕旗子 336×544 的 2 倍；旗桿 x 96–132、y 32–1062）"""
    wb = 14
    pad = wb + 6
    W, H = 672 - 2 * pad, 1088 - 2 * pad
    s = P.Sheet(W, H, ss=2)
    o = lambda pts: [(x - pad, y - pad) for x, y in pts]
    # 旗面（輕微波浪的上下緣；背面：同一張紙的背面，顏色暗一點、白條只透出一點）
    top = [(132 + i * 26, 52 + 30 * np.sin(i / 19 * np.pi) * 0.5 + i * 2.3) for i in range(20)]
    right = [(636, 100), (624, 230), (604, 372)]
    bot = [(132 + (19 - i) * 24.6, 372 + (i - 19) * -4.6 + 12 * np.sin(i / 19 * np.pi)) for i in range(20)]
    bot = [(x, 372 + (604 - x) / 472 * 92 + 10 * np.sin((x - 132) / 472 * np.pi)) for x, _ in bot]
    cloth = o(top + right + bot)
    base = tuple(int(c * (0.93 if back else 1.0)) for c in LIME[:3]) + (255,)
    s.poly(cloth, base, line=2.2)
    # 白條（背面只透出一點）
    if back:
        sc = tuple(int(base[i] * 0.72 + STRIPE[i] * 0.28) for i in range(3)) + (255,)
    else:
        sc = STRIPE
    s.poly(o([(150, 226), (600, 240), (600, 254), (150, 242)]), sc, line=0)
    # 旗桿（木紋細線）＋頂端圓頭
    s.rect(96 - pad, 40 - pad, 132 - pad, 1062 - pad, POLE, line=2.2, r=6)
    for yy in range(120, 1040, 140):
        s.line(o([(106, yy), (108, yy + 60)]), w=1.2, color=POLE_D)
    s.ellipse(92 - pad, 26 - pad, 136 - pad, 66 - pad, POLE, line=2.2)
    a = s.finish(white_border=wb, edge_dark=0.0, seed=31 if back else 30)
    assert a.shape[:2] == (1088, 672), a.shape
    # 旗面輕微起伏（紙旗被風吹出的兩道柔和波紋：斜的明暗帶，±4%）；背面波紋方向相反
    from PIL import ImageDraw
    m = Image.new("L", (672, 1088), 0)
    ImageDraw.Draw(m).polygon([(x, y) for x, y in (top + right + bot)], fill=255)
    m = ndimage.gaussian_filter(np.asarray(m, np.float32) / 255.0, 2.0)
    yy, xx = np.mgrid[0:1088, 0:672].astype(np.float32)
    u = (xx - 132) / 472.0
    v = (yy - 60) / 400.0
    sgn = -1.0 if back else 1.0
    rip = 1.0 + 0.045 * np.sin(2 * np.pi * (u * 1.7 + sgn * v * 0.35) + 0.6)
    f = a.astype(np.float32)
    f[..., :3] *= (1.0 + (rip - 1.0) * m)[..., None]
    a = np.clip(f, 0, 255).astype(np.uint8)
    a = paperize(Image.fromarray(a), scale=1.0, seed=32 if back else 33, relief=1.2, shadow=1.0, rim=0.6)
    return a


GATE_PIECES = {   # id → 放大倍數
    "set-gate_school-building": 1.35,
    "set-gate_school-wall": 2.0,
    "set-gate_folding-gate": 2.0,
    "set-gate_guard-house": 2.0,
    "set-gate_pillar": 2.0,
}


def latest(dirp, stem):
    c = sorted(dirp.glob(f"{stem}_v*.png"), key=lambda p: int(p.stem.rsplit("_v", 1)[1]))
    return c[-1]


def gate_pieces(meta):
    for i, (gid, sc) in enumerate(GATE_PIECES.items()):
        src = latest(FINAL / "gate", gid)
        a = paperize(Image.open(src), scale=sc, seed=50 + i)
        dst = OUT / f"{gid}_v01.png"
        P.save(a, dst)
        meta[gid] = {"src": str(src.relative_to(ROOT)), "scale": sc, "size": [a.shape[1], a.shape[0]]}
        print(dst.name, a.shape)


def props(meta):
    jobs = [("a5-ambulance", "a5-ambulance_v03.png", 1.5, 61), ("a5-ambulance-door", "a5-ambulance-door_v02.png", 1.5, 62),
            ("a5-gurney", "a5-gurney_v03.png", 1.5, 63), ("a5-corner", "a5-corner_v02.png", 2.5, 64)]
    for stem, out, sc, seed in jobs:
        srcs = sorted(SRC.glob(f"{stem}_v*.png"), key=lambda p: int(p.stem.rsplit("_v", 1)[1]))
        src = [p for p in srcs if p.name != out][-1]
        a = paperize(Image.open(src), scale=sc, seed=seed)
        P.save(a, OUT / out)
        meta[stem] = {"src": src.name, "out": out, "scale": sc, "size": [a.shape[1], a.shape[0]]}
        print(out, a.shape)


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    meta_all = json.loads(META.read_text()) if META.exists() else {}
    meta = meta_all.setdefault("fix2", {})
    if not only or "flag" in only:
        P.save(flag(False), OUT / "a5-flag_v01.png")
        P.save(flag(True), OUT / "a5-flag-back_v01.png")
        meta["flag"] = {"canvas": [672, 1088], "note": "同第四幕旗子（336×544）的 2 倍；旗桿 x 96–132"}
        print("flag")
    if not only or "gate" in only:
        gate_pieces(meta)
    if not only or "props" in only:
        props(meta)
    if not only or "student" in only:
        import student_v03
        meta["student"] = student_v03.build(OUT)
    if OUT == SRC:
        META.write_text(json.dumps(meta_all, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
