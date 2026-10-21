"""G4 修正第 1 輪（美術，問題 17）：阿樂「X2 想打招呼」換頭 head_greet（微笑＋眉毛上抬）。

來源：assets/final/rig/chr-ale_head_v04.png（母版的一般頭，本來就是微笑），不重新生成，避免變臉。
做法：兩道眉毛（深色連通塊）整塊往上移 9 px、外端再多抬 2 px（友善的「眉抬」），原位置用調和填補＋同強度紙紋補成皮膚。
      其餘像素（臉型、膚色、髮型、眼、嘴、鬍渣）完全不動；尺寸與原點和 head 相同（母版原點 378,18；頸部樞紐 530,330）。
輸出：assets/final/rig/chr-ale_head-greet_v05.png、chr-ale_head-greet-outline_v05.png；
      ale_rig_v05.json 加一個替換部件 head_greet（與 head、head_worried 同樞紐）；檢查圖 review/G4/art/ale_head_greet_v05.png。
臉部換片：眼、嘴位置和 head 完全相同 → 引擎可直接沿用 FALLBACK_FACES['ale:head']（一般頭的退路換片：眨眼、對嘴）。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/make_ale_greet_head.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import build_faces as BF  # noqa: E402
import build_ale_rig as B  # noqa: E402

RIG = ROOT / "assets/final/rig"
ART = ROOT / "review/G4/art"
LIFT = 9
OUTER_EXTRA = 2


def main():
    src = RIG / "chr-ale_head_v04.png"
    a = np.array(Image.open(src).convert("RGBA"))
    L = BF.lum(a[..., :3].astype(np.float32))
    dark = (L < 95) & (a[..., 3] > 128)
    lab, n = ndimage.label(dark)
    brows = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        comp = lab == i + 1
        sz = int(comp.sum())
        cy = (sl[0].start + sl[0].stop) / 2
        cx = (sl[1].start + sl[1].stop) / 2
        if 200 < sz < 800 and 115 < cy < 150 and 100 < cx < 230:
            brows.append((comp, sl))
    assert len(brows) == 2, f"眉毛找到 {len(brows)} 塊"
    H, W = L.shape
    brow_m = np.zeros((H, W), bool)
    for comp, _ in brows:
        brow_m |= comp
    # 含抗鋸齒邊（較淺的深色）
    soft = ndimage.binary_dilation(brow_m, iterations=2) & (L < 175) & (a[..., 3] > 128)
    full_m = brow_m | soft
    fill = ndimage.binary_dilation(full_m, iterations=1)
    protect = (L < 125) & (a[..., 3] > 128) & ~fill
    box = (100, 100, 240, 200)
    skin, skin_box = BF.skin_stats(a, box, fill | protect)
    skin_full = np.zeros((H, W), bool)
    skin_full[box[1]:box[3], box[0]:box[2]] = skin_box
    clean = BF.harmonic_fill(a, fill, skin, protect)
    clean = BF.paper_grain(clean, fill, skin_full & ~fill, seed=517)
    # 眉毛整塊上移（外端多抬一點）：眉毛層（顏色＝原圖、覆蓋度＝深淺）以仿射變換（雙三次）搬到新位置再疊回，邊緣保持抗鋸齒
    import math
    out_img = Image.fromarray(clean.copy(), "RGBA")
    face_cx = 170
    for comp, sl in brows:
        m = ndimage.binary_dilation(comp, iterations=2) & full_m
        ys, xs = np.nonzero(m)
        x0, x1 = xs.min(), xs.max()
        outer_left = (x0 + x1) / 2 < face_cx
        layer = np.zeros_like(a)
        layer[..., :3] = a[..., :3]
        cov = np.clip((200 - L) / (200 - 70), 0, 1) * m
        layer[..., 3] = (cov * 255).astype(np.uint8)
        # 以眉毛內端為支點，外端往上轉 OUTER_EXTRA px
        ang = math.atan2(OUTER_EXTRA, max(1, x1 - x0)) * (1 if outer_left else -1)   # 影像座標：左眉外端在左 → 逆時針
        px_, py_ = (x1 if outer_left else x0), float(ys.mean())
        ca, sa = math.cos(ang), math.sin(ang)
        # 正向：p' = R(p - pivot) + pivot + (0, -LIFT)；PIL 要反向矩陣
        # 反向：p = R^-1 (p' - pivot - t) + pivot
        tx, ty = 0.0, -LIFT
        ia, ib = ca, sa
        ic, id_ = -sa, ca
        cx0 = px_ + tx; cy0 = py_ + ty
        A_ = (ia, ib, px_ - ia * cx0 - ib * cy0, ic, id_, py_ - ic * cx0 - id_ * cy0)
        moved = Image.fromarray(layer, "RGBA").transform((W, H), Image.AFFINE, data=A_, resample=Image.BICUBIC)
        out_img.alpha_composite(moved)
    out = np.array(out_img)
    out[..., 3] = a[..., 3]
    changed = int((np.abs(out[..., :3].astype(int) - a[..., :3].astype(int)).max(-1) > 12).sum())
    Image.fromarray(B.bleed(out), "RGBA").save(RIG / "chr-ale_head-greet_v05.png", optimize=True)
    Image.fromarray(B.bleed(B.outline_of(out[..., 3])), "RGBA").save(RIG / "chr-ale_head-greet-outline_v05.png", optimize=True)
    # rig v05 加替換部件
    rp = RIG / "ale_rig_v05.json"
    rig = json.loads(rp.read_text())
    h = dict(rig["parts"]["head"])
    h.update({"zh": "打招呼頭 X2（一般頭的微笑＋眉毛上抬；換頭用，與 head 同樞紐）", "file": "chr-ale_head-greet_v05.png",
              "image_id": "rig/chr-ale_head-greet", "outline_file": "chr-ale_head-greet-outline_v05.png",
              "outline_image_id": "rig/chr-ale_head-greet-outline"})
    rig["parts"]["head_greet"] = h
    rig.setdefault("fix_log", {})["head_greet_v05"] = {"source": "chr-ale_head_v04.png", "brow_lift_px": LIFT, "outer_extra_px": OUTER_EXTRA,
                                                       "changed_px": changed, "face_swaps": "沿用 FALLBACK_FACES['ale:head']（眼、嘴位置與 head 相同）"}
    rp.write_text(json.dumps(rig, ensure_ascii=False, indent=1))
    # 檢查圖：head（原）｜head_greet｜head_worried；原寸 2× 與中景尺寸（×0.41）
    imgs = [("head（v04，原）", a), ("head_greet（v05，X2）", out), ("head_worried（v04，困惑）", np.array(Image.open(RIG / "chr-ale_head-worried_v04.png").convert("RGBA")))]
    from PIL import ImageFont
    font = ImageFont.truetype(BF.FONT, 18, index=10)
    S = Image.new("RGB", (3 * 300 * 2 // 2 * 2 + 80, 470 + 220), (44, 42, 40))
    d = ImageDraw.Draw(S)
    x = 20
    for lab_, im in imgs:
        t = Image.new("RGBA", (im.shape[1], im.shape[0]), (214, 206, 190, 255))
        t.alpha_composite(Image.fromarray(im))
        c = t.crop((60, 60, im.shape[1] - 10, 260)).resize(((im.shape[1] - 70) * 2 // 2 * 2 // 2 * 2 // 2, 400 // 2 * 2 // 2), Image.LANCZOS)
        c = t.crop((60, 60, 260, 260)).resize((400, 400), Image.LANCZOS)
        d.text((x, 10), lab_, font=font, fill=(240, 210, 120))
        S.paste(c.convert("RGB"), (x, 40))
        sm = t.resize((int(t.width * 0.41), int(t.height * 0.41)), Image.LANCZOS)
        S.paste(sm.convert("RGB"), (x, 470))
        x += 420
    S.save(ART / "ale_head_greet_v05.png")
    print("brows", len(brows), "changed px", changed)


if __name__ == "__main__":
    main()
