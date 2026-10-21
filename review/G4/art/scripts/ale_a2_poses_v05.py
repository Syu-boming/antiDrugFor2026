"""G4 修正第 1 輪（美術）：阿樂 a2 六個姿勢 × 新紙繩／紙環／扣點 v05／前臂 v05 的檢查圖與數據。

輸出：
  review/G4/art/ale_a2_poses_v05.png   上排：六個姿勢以 g4_mid 中景的螢幕比例（1 母版 px ≈ 0.41 px）1:1 畫出，
                                       線寬 8 px、紙環直徑 19 px（與引擎建議值相同）；下排：腕／肘／膝扣點 4× 放大。
  review/G4/art/ale_attach_v05_check.json  每個姿勢每個扣點：紙環是否整個在角色剪影內（剪影邊距 px）、扣點座標。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/ale_a2_poses_v05.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
import rig_ale_v03 as R  # noqa: E402
import ale_a2_poses as A  # noqa: E402
import make_string_tex as T  # noqa: E402

RIG = ROOT / "assets/final/rig"
FIN = ROOT / "assets/final"
ART = ROOT / "review/G4/art"
PX_PER_UNIT_MID = 186.8          # g4_mid：距離 16.4、垂直視角 20°、1080p


def load_rig_v05():
    rig = R.Rig(head="worried")
    meta = json.loads((RIG / "ale_rig_v05.json").read_text())
    for n, p in meta["parts"].items():
        if n == "head":
            continue
        im = Image.open(RIG / p["file"]).convert("RGBA")
        key = "head" if n == "head_worried" else n
        rig.parts[key] = (im, tuple(p["origin_master"]))
    return rig, meta


def main():
    A.apply_ik()
    rig, meta = load_rig_v05()
    att = json.loads((RIG / "ale_attach_v05.json").read_text())
    ring_d_px = att["ring"]["diameter_master_px"]
    s_world = att["ring"]["diameter_world"] / ring_d_px            # 世界單位 / 母版 px
    sc = s_world * PX_PER_UNIT_MID                                  # 母版 px → 中景螢幕 px
    rope = np.array(Image.open(FIN / "tex-string-rope_v01.png").convert("RGB"))
    ring = np.array(Image.open(FIN / "tex-string-ring_v01.png").convert("RGBA"))
    wall = Image.open(FIN / "bg-workshop-back_v02.jpg").convert("RGB")
    check = {"ring_diameter_master_px": ring_d_px, "screen_scale_mid": round(sc, 4), "poses": {}}
    cols = []
    keys = (("wrist_back", -0.02), ("elbow_out", -0.02), ("knee_front", 0.19))
    for name in A.POSES:
        # (1) 母版尺度：剪影邊距
        img1, pt1, _, _ = rig.render(A.POSES[name], outline=False, scale=1.0)
        al = np.array(img1)[..., 3] > 127
        dt = ndimage.distance_transform_edt(al)
        rec = {}
        for k, _ in keys:
            q = pt1(att["points"][k]["part"], att["points"][k]["master_px"])
            yy, xx = np.mgrid[:al.shape[0], :al.shape[1]]
            circle = (xx - q[0]) ** 2 + (yy - q[1]) ** 2 <= (ring_d_px / 2) ** 2
            inside = bool(al[circle].all())
            rec[k] = {"canvas_px": [round(float(q[0]), 1), round(float(q[1]), 1)], "ring_inside_silhouette": inside,
                      "margin_px": round(float(dt[int(round(q[1])), int(round(q[0]))] - ring_d_px / 2), 1)}
        check["poses"][name] = rec
        # (2) 中景螢幕尺度 1:1
        img, pt, _, _ = rig.render(A.POSES[name], outline=True, scale=sc)
        bgw = wall.resize((int(wall.width * img.width / 900), int(wall.height * img.width / 900)))
        bg = Image.new("RGBA", img.size, (236, 226, 212, 255))
        bg.paste(bgw.crop((bgw.width // 2 - img.width // 2, bgw.height - img.height - 40, bgw.width // 2 + img.width // 2, bgw.height - 40)), (0, 0))
        bg.alpha_composite(A.table_layer(img.size, sc, R.OFFSET))   # 佔位工作台在阿樂前面？—— 照 v04 規劃圖，桌子畫在後面以便看手
        bg.alpha_composite(img)
        canvas = np.array(bg.convert("RGB"), np.float32)
        qs = {}
        for k, lean in keys:
            q = pt(att["points"][k]["part"], att["points"][k]["master_px"])
            qs[k] = q
            top = (q[0] + lean * q[1], -5)
            # 線的下端停在紙環上緣
            d = np.array(top) - np.array(q); d = d / np.hypot(*d)
            end = np.array(q) + d * ring_d_px * sc * 0.4
            canvas = T.draw_strip(canvas, rope, top, end, 8.0)
            canvas = T.draw_strip(canvas, rope, end, end, 0.0001, ring, ring_d=ring_d_px * sc) if False else canvas
            rd = int(round(ring_d_px * sc))
            rs = np.array(Image.fromarray(ring).resize((rd * 4, rd * 4), Image.LANCZOS).resize((rd, rd), Image.BOX), np.float32)
            cx, cy = int(round(q[0] - rd / 2)), int(round(q[1] - rd / 2))
            a = rs[..., 3:4] / 255
            canvas[cy:cy + rd, cx:cx + rd] = canvas[cy:cy + rd, cx:cx + rd] * (1 - a) + rs[..., :3] * a
        out = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
        body = out.crop((int((R.OFFSET[0] - 380) * sc), int(60 * sc), int((R.OFFSET[0] + 1100) * sc), int((R.OFFSET[1] + A.FLOOR + 20) * sc)))
        crops = []
        for k, _ in keys:
            q = qs[k]
            c = out.crop((int(q[0] - 30), int(q[1] - 45), int(q[0] + 30), int(q[1] + 15))).resize((240, 240), Image.NEAREST)
            crops.append((k, c))
        cols.append((name, body, crops))
    W = sum(max(b.width, 250) + 20 for _, b, _ in cols) + 20
    Hh = max(b.height for _, b, _ in cols)
    S = Image.new("RGB", (max(W, 1500), 90 + Hh + 3 * 260 + 20), (44, 42, 40))
    d = ImageDraw.Draw(S)
    from PIL import ImageFont
    f = lambda n: ImageFont.truetype(T.projsim.FONT[0], n)
    d.text((20, 10), "阿樂 a2 姿勢 × 操偶線 v05：上＝g4_mid 中景螢幕比例 1:1（線寬 8 px、紙環 19 px）；下＝腕背／肘外／膝前扣點 4× 放大（紙環整個在剪影內）",
           font=f(20), fill=(240, 240, 240))
    x = 20
    for name, body, crops in cols:
        ok = all(v["ring_inside_silhouette"] for v in check["poses"][name].values())
        d.text((x, 44), f"{name}（紙環在剪影內：{'是' if ok else '否'}）", font=f(18), fill=(240, 210, 120) if ok else (255, 90, 90))
        S.paste(body, (x, 80))
        for i, (k, c) in enumerate(crops):
            S.paste(c, (x, 90 + Hh + i * 260))
            d.text((x + 4, 92 + Hh + i * 260), k, font=f(14), fill=(20, 20, 20))
        x += max(body.width, 250) + 20
    S.save(ART / "ale_a2_poses_v05.png")
    (ART / "ale_attach_v05_check.json").write_text(json.dumps(check, ensure_ascii=False, indent=1))
    bad = [(n, k) for n, r in check["poses"].items() for k, v in r.items() if not v["ring_inside_silhouette"]]
    print("ring outside:", bad or "none")
    print(json.dumps({n: {k: v["margin_px"] for k, v in r.items()} for n, r in check["poses"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
