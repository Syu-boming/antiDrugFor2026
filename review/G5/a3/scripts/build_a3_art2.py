"""G5 第三幕（a3）補充美術（接續 build_a3_art.py；程式繪製，不生成）。

輸出：
  assets/final/sets/a3_classroom/students_v02.png  教室後排同學（背面：頭髮蓋住整個後腦、看不到臉；不透明紙片小人、
                                                    衣服低彩度、有的背書包）——取代 v01 的灰色無五官人形（主線裁定第 6 條）
  assets/final/chr-lin_pose-stand-m_v01.png        林老師站姿左右翻轉（a3_c008：站在孩子右邊、臉朝畫面左跟全班說話；
                                                    走出教室時翻回原圖朝右）
用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/build_a3_art2.py
"""
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

FINAL = ROOT / "assets/final"
PPU = 100


def students():
    """6 個同學的背影（寬 7.0、高 2.4 世界單位）。頭＝髮色圓頂（背面，沒有五官），身體＝圓角上衣＋短褲／長褲＋鞋。"""
    W, H = 7.0, 2.4
    w, h = int(W * PPU), int(H * PPU)
    s = P.Sheet(w, h)
    rng = random.Random(23)
    hair = [(70, 52, 42, 255), (52, 40, 34, 255), (92, 66, 48, 255), (60, 46, 40, 255), (84, 60, 44, 255), (48, 38, 32, 255)]
    shirt = [(176, 196, 170, 255), (172, 186, 206, 255), (222, 196, 140, 255), (214, 176, 166, 255), (238, 228, 206, 255), (190, 176, 204, 255)]
    pants = [(120, 112, 104, 255), (150, 130, 104, 255), (96, 104, 120, 255)]
    skin = (238, 204, 172, 255)
    bag = [(120, 140, 120, 255), (150, 110, 90, 255), (110, 120, 150, 255)]
    xs = [55, 165, 285, 410, 525, 635]
    for k, x in enumerate(xs):
        hh = rng.uniform(1.95, 2.2) * PPU          # 身高（像素）
        top = h - hh
        hr = hh * 0.12                              # 頭半徑
        cx = x
        bw = hr * 1.35                              # 半身寬
        y_sh = top + hr * 2.05                      # 肩
        y_hip = h - hh * 0.40
        # 腿＋鞋
        pc = pants[k % 3]
        for side in (-1, 1):
            lx0 = cx + side * hr * 0.12 if side > 0 else cx - hr * 0.95
            lx1 = lx0 + hr * 0.83
            s.rect(lx0, y_hip - 4, lx1, h - 12, pc if k % 2 == 0 else skin, line=1.2, r=4)
            if k % 2:   # 短褲
                s.rect(lx0 - 2, y_hip - 4, lx1 + 2, y_hip + hh * 0.13, pc, line=1.2, r=4)
            s.rect(lx0 - 3, h - 16, lx1 + 4, h - 2, (238, 234, 226, 255), line=1.2, r=5)
        # 手臂（垂下）
        aw = hr * 0.44
        for side in (-1, 1):
            a0 = cx - bw - aw + 3 if side < 0 else cx + bw - 3
            s.ellipse(a0 + 1, y_hip + hr * 0.15, a0 + aw - 1, y_hip + hr * 0.75, skin, line=1.0)
            s.rect(a0, y_sh + 6, a0 + aw, y_hip + hr * 0.35, shirt[k], line=1.2, r=8)
        # 上衣
        s.rect(cx - bw, y_sh, cx + bw, y_hip + 6, shirt[k], line=1.4, r=14)
        # 後頸＋頭（背面：整個是頭髮）
        s.rect(cx - hr * 0.35, y_sh - hr * 0.35, cx + hr * 0.35, y_sh + 4, skin, line=1.0)
        s.ellipse(cx - hr, top, cx + hr, top + hr * 2.1, hair[k], line=1.4)
        if k in (1, 4):   # 綁馬尾
            s.ellipse(cx - hr * 0.28, top + hr * 1.6, cx + hr * 0.28, top + hr * 2.5, hair[k], line=1.2)
        # 耳朵（頭的兩側一點點）
        for side in (-1, 1):
            ex = cx + side * hr * 0.97
            s.ellipse(ex - hr * 0.16, top + hr * 0.95, ex + hr * 0.16, top + hr * 1.35, skin, line=1.0)
        s.ellipse(cx - hr, top, cx + hr, top + hr * 2.1, hair[k], line=1.4)
        # 書包（背在背上）
        if k % 3 != 2:
            bc = bag[k % 3]
            s.rect(cx - bw * 0.78, y_sh + hr * 0.25, cx + bw * 0.78, y_hip - hr * 0.1, bc, line=1.4, r=12)
            s.rect(cx - bw * 0.5, y_sh + hr * 1.0, cx + bw * 0.5, y_sh + hr * 1.7, tuple(int(c * 1.12) if i < 3 else c for i, c in enumerate(bc)), line=1.2, r=6)
    return s.finish()


def lin_stand_m():
    src = FINAL / "chr-lin_master_v01.png"
    im = ImageOps.mirror(Image.open(src).convert("RGBA"))
    out = FINAL / "chr-lin_pose-stand-m_v01.png"
    if out.exists():
        print("exists", out.relative_to(ROOT))
        return
    im.save(out)
    print("wrote", out.relative_to(ROOT), im.size)


if __name__ == "__main__":
    a = students()
    p = FINAL / "sets/a3_classroom/students_v02.png"
    P.save(a, p)
    print("wrote", p.relative_to(ROOT), a.shape[1], a.shape[0])
    lin_stand_m()
