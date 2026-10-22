"""G5 修正第 2 輪（第二幕）：手部近景（a2_c008 開頭）的手臂改用阿樂母版的 forearm／hand 分件放大處理（b1r2_regress a2 一般問題 5：
平塗橙色、像橡膠、和全劇剪紙工藝有落差）。不用 Codex 生圖，只處理母版分件：

  輸入：assets/final/rig/chr-ale_forearm-{r,l}_v05.png、chr-ale_hand-{r,l}_v04.png 與各自的 -outline 圖（白紙芯外框）
  輸出：assets/final/sets/a2_shop/insert-ale-forearm-{r,l}_v01.png、insert-ale-hand-{r,l}_v01.png、
        insert-ale-forearm-{r,l}-outline_v01.png、insert-ale-hand-{r,l}-outline_v01.png
  做法（2 倍解析度，座標＝母版座標 × 2）：
    - LANCZOS 放大 2 倍；乘上全劇共用的紙纖維紋理（paperdraw.paper_tex，對比加強 1.6 倍）
    - 紙片厚度：邊緣往內 6 px 漸暗 10%（同 Sheet.finish 的 edge_dark 做法）
    - 2 px 深色紙邊（#4E3E33，和角色立牌同色）沿著不透明區外緣
    - 白紙芯外框：同樣加紙纖維，外緣 1.5 px 淡灰邊
規則：不改形狀、不加文字；只在手部近景使用（紙偶本體不變）。
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

RIG = ROOT / "assets/final/rig"
OUT = ROOT / "assets/final/sets/a2_shop"
INK = np.array([78, 62, 51], np.float32)
S = 2


def process(src, dst, outline=False):
    im = Image.open(src).convert("RGBA")
    im = im.resize((im.width * S, im.height * S), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    tex = 1.0 + (P.paper_tex(w, h) - 1.0) * 1.6
    a[..., :3] *= tex[..., None]
    m = a[..., 3] > 128
    din = ndimage.distance_transform_edt(m)
    if not outline:
        k = np.clip(1 - din / 6.0, 0, 1) * 0.10
        a[..., :3] *= (1 - k[..., None])
    if outline:      # 白紙芯外緣：淡淡的 1.5 px 灰邊（和背景分開，不搶戲）
        edge = m & (din <= 1.5)
        a[edge, :3] = a[edge, :3] * 0.65 + INK * 0.35
    else:            # 部件外緣：2 px 深色紙邊（同角色立牌白邊內側那圈細線）
        edge = m & (din <= 2.0)
        a[edge, :3] = a[edge, :3] * 0.2 + INK * 0.8
    a = np.clip(a, 0, 255).astype(np.uint8)
    P.save(a, dst)
    return dst


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for side in ("r", "l"):
        process(RIG / f"chr-ale_forearm-{side}_v05.png", OUT / f"insert-ale-forearm-{side}_v01.png")
        process(RIG / f"chr-ale_hand-{side}_v04.png", OUT / f"insert-ale-hand-{side}_v01.png")
        process(RIG / f"chr-ale_forearm-{side}-outline_v05.png", OUT / f"insert-ale-forearm-{side}-outline_v01.png", outline=True)
        process(RIG / f"chr-ale_hand-{side}-outline_v04.png", OUT / f"insert-ale-hand-{side}-outline_v01.png", outline=True)
    print("wrote", sorted(p.name for p in OUT.glob("insert-*")))


if __name__ == "__main__":
    main()
