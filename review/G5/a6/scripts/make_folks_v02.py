"""第六幕修正第 1 輪：廣場鎮民改成「淺紙色小紙人」（主線補充裁定：沒有五官的灰色幾何人影 → 不透明、有紙纖維的淺紙色小紙人放遠景，
明度比背景暗 15–20%、2 px 紙邊）。

做法：沿用 build_a6_art2.py 的背影紙片人輪廓（不畫五官、中性設計），整張改成同一種淺牛皮紙色的深淺（頭髮／上衣／褲子只差一點明度），
外框線改成淡棕（不用深墨線），乘上 G2 同款紙纖維，外圈 12 px 白色紙芯邊（遠景顯示約 2 px）。
景（app/src/sets/a6_square_night layout.json）把他們放到主燈左後方、騎樓前的遠景（燈籠架角落的鏡頭看不到）。
輸出：assets/final/sets/a6_square_night/folk-{a,b,c,d}_v02.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paperdraw as PD  # noqa: E402
import build_a6_art2 as A2  # noqa: E402

FIN = ROOT / "assets/final/sets/a6_square_night"
LINE = (150, 124, 98, 255)
P = {"hair": (176, 150, 120, 255), "top": (214, 192, 160, 255), "pants": (188, 164, 134, 255),
     "shoe": (160, 136, 110, 255), "sheet": (244, 234, 214, 255)}


def main():
    PD.INK = LINE           # 外框線淡棕
    A2.INK = LINE
    specs = {
        "folk-a": (560, 980, dict(cx=210, foot=960, h=900, arms="reach")),
        "folk-b": (560, 980, dict(cx=210, foot=960, h=880, arms="reach")),
        "folk-c": (360, 760, dict(cx=180, foot=740, h=640, arms="up", child=True)),
        "folk-d": (420, 980, dict(cx=210, foot=960, h=900, arms="side")),
    }
    tone = {"folk-a": 1.0, "folk-b": 0.96, "folk-c": 1.02, "folk-d": 0.94}
    for name, (W, H, p) in specs.items():
        sh = PD.Sheet(W, H, ss=2)
        k = tone[name]
        col = {kk: tuple(int(min(255, v * k)) for v in c[:3]) + (255,) for kk, c in P.items()}
        A2.person_back(sh, hair=col["hair"], top=col["top"], pants=col["pants"], shoe=col["shoe"],
                       sheet=None if p["arms"] == "side" else col["sheet"], skin=(224, 204, 178, 255), **p)
        a = sh.finish(white_border=12)
        PD.save(a, FIN / f"{name}_v02.png")
        print("ok", name, np.asarray(a).shape)


if __name__ == "__main__":
    main()
