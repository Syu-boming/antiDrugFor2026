"""第六幕代理：小晴站姿左右翻轉（程式）＋退路臉部範圍鏡射。

用法：/opt/anaconda3/bin/python3 review/G5/a6/scripts/add_xq_stand_m.py
- assets/final/chr-xiaoqing_master_v04.png → assets/final/chr-xiaoqing_pose-stand-m_v01.png（PIL ImageOps.mirror）
- show_characters.json：characters.xiaoqing.poses 新增 stand_m；fallbackFaces 新增 xiaoqing:stand_m（由 face.ts 的 xiaoqing:stand 鏡射）
  只新增鍵，不改別人的鍵。
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "assets/final"
src = Image.open(FIN / "chr-xiaoqing_master_v04.png").convert("RGBA")
W = src.width
mir = ImageOps.mirror(src)
mir.save(FIN / "chr-xiaoqing_pose-stand-m_v01.png", optimize=True)

def tl(im):
    a = np.array(im)[..., 3] >= 128
    ys, xs = np.nonzero(a)
    return int(xs.min()), int(ys.min()), int(xs.max())

FB = {"ref": [262, 48], "eyes": [[393, 240, 427, 289], [494, 251, 538, 301]], "mouth": [433, 328, 481, 339]}
ax, ay, axr = tl(src)
dx, dy = ax - FB["ref"][0], ay - FB["ref"][1]
cur = lambda b: [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]   # noqa: E731
mx = lambda b: [W - b[2], b[1], W - b[0], b[3]]                  # noqa: E731
mx0, my0, _ = tl(mir)
face = {
    "ref": [mx0, my0],
    "eyes": [mx(cur(FB["eyes"][1])), mx(cur(FB["eyes"][0]))],
    "mouth": mx(cur(FB["mouth"])),
    "paintedMouth": "smile",
    "_note": "第六幕代理新增：小晴站姿左右翻轉（xiaoqing:stand 鏡射）；a6 小晴轉身朝左用（紙片翻面）",
}
p = FIN / "rig/show_characters.json"
d = json.loads(p.read_text())
d["characters"]["xiaoqing"]["poses"].setdefault("stand_m", {"image": "chr-xiaoqing_pose-stand-m", "face": "xiaoqing:stand_m"})
d["fallbackFaces"].setdefault("xiaoqing:stand_m", face)
p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print(face)
