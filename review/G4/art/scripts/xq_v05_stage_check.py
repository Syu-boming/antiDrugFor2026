"""G4 修正第 1 輪（美術）：小晴新姿勢放進 G4 實際畫面的檢查圖（換掉 a2_c002 11.41 s 關鍵影格裡的小晴）。
- 小晴原本的位置用同一格的 probe_bg（隱藏角色後的背景）補回，再把新姿勢以相同腳底位置、相同身高（頭頂→腳底）疊上。
- 輸出 review/G4/art/xq_v05_stage_check.png（上＝原圖、下＝投影 v2）與數據 xq_v05_stage_check.json（吊帶褲對背景對比）。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/xq_v05_stage_check.py
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import projsim  # noqa: E402
import capture_probe as C  # noqa: E402
KF = ROOT / "review/G4/pack/capture"
FIN = ROOT / "assets/final"


def main():
    fr = Image.open(KF / "keyframes/a2_c002_011.41_mid.png").convert("RGBA")
    bg = Image.open(KF / "probe_bg/a2_c002_011.41_mid.png").convert("RGBA")
    box = (1290, 470, 1492, 975)
    base = fr.copy()
    base.paste(bg.crop(box), box[:2])
    feet = (1392, 962)
    H = 965 - 483
    rows, tiles = {}, []
    for k in ("watch", "palm", "worried"):
        im = Image.open(FIN / f"chr-xiaoqing_pose-{k}_v05.png").convert("RGBA")
        a = np.array(im)[..., 3] > 128
        ys = np.nonzero(a.any(1))[0]
        top, bot = ys.min(), ys.max()
        low = a[bot - 6:bot + 1].any(0); lx = np.nonzero(low)[0]
        fx = (lx.min() + lx.max()) / 2
        s = H / (bot - top)
        sm = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        out = base.copy()
        out.alpha_composite(sm, (int(feet[0] - fx * s), int(feet[1] - bot * s)))
        rgb = np.array(out.convert("RGB"))
        # 吊帶褲對兩側背景（投影 v2）
        m = np.array(sm)[..., :3].astype(np.float32)
        h_, s_, v_ = [x for x in __import__("recolor_garment").hsv(m)]
        ov = (h_ > 160) & (h_ < 205) & (s_ > 0.25) & (np.array(sm)[..., 3] > 200)
        ox, oy = int(feet[0] - fx * s), int(feet[1] - bot * s)
        yy, xx = np.nonzero(ov)
        pj = projsim.projector(rgb)
        lum = C.luminance(pj)
        cl = float(np.median(lum[yy + oy, xx + ox]))
        bgl = float(np.median(C.luminance(projsim.projector(np.array(bg.convert("RGB"))))[box[1]:box[3], box[0]:box[2]]))
        rows[k] = {"overalls_projv2_lum": round(cl, 3), "bg_projv2_lum_median": round(bgl, 3), "contrast": round((bgl + 0.05) / (cl + 0.05), 2)}
        tiles.append((k, out.convert("RGB").crop((900, 300, 1920, 1080)), Image.fromarray(pj).crop((900, 300, 1920, 1080))))
    W = 3 * 520 + 40
    S = Image.new("RGB", (W, 60 + 2 * 400), (44, 42, 40))
    d = ImageDraw.Draw(S)
    f = ImageFont.truetype(projsim.FONT[0], 18)
    d.text((16, 14), "小晴新姿勢放進 a2_c002 11.41 s 實際畫面（相同腳底、相同身高）：上＝原圖、下＝投影 v2", font=f, fill=(240, 240, 240))
    x = 16
    for k, o, p in tiles:
        o = o.resize((510, 390)); p = p.resize((510, 390))
        S.paste(o, (x, 50)); S.paste(p, (x, 450))
        d.text((x + 6, 54), f"{k}（吊帶褲對比 {rows[k]['contrast']}:1）", font=f, fill=(20, 20, 20))
        x += 520
    S.save(ROOT / "review/G4/art/xq_v05_stage_check.png")
    (ROOT / "review/G4/art/xq_v05_stage_check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
