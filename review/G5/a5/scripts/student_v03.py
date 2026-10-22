"""轉角的低年級小朋友 v03：Codex 生成的同畫風紙片小人（review/G5/a5/raw/a5_student_v03.png，codex_log 修正第 2 輪第 1 張）
切成「身體」與「舉高揮手的手臂」兩片（手臂在身體後面，以袖口為樞紐左右擺；放下時轉到身體後面）。

- 切線：袖口（原圖座標 (690,440)→(765,700) 的線段）；手臂＝切開後含手掌那一塊相連的不透明區域。
- 手臂片多留袖子內側 22 px（在身體後面，揮動時袖口不會露縫）。
- 輸出縮到人物高 440 px（舞台上約 1.55 世界單位、遠景約 150 px 高，2–3 倍取樣）。
回傳 meta：圖寬（世界單位）、樞紐位置（相對身體底邊中點，世界單位）。
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "review/G5/a5/raw/a5_student_v03.png"
FIG_H_WORLD = 1.55          # 人物（帽頂到鞋底）的世界高度
OUT_FIG_PX = 440
P0, P1 = np.array([690.0, 440.0]), np.array([765.0, 700.0])   # 袖口切線（原圖像素）
HAND = (900, 260)


def save(a, path):
    m = a[..., 3] > 0
    if m.any() and not m.all():
        _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
        a = a.copy()
        a[~m, :3] = a[iy[~m], ix[~m], :3]
    Image.fromarray(a, "RGBA").save(path, optimize=True)


def build(out_dir):
    src = np.array(Image.open(RAW).convert("RGBA"))
    H, W = src.shape[:2]
    op = src[..., 3] > 100
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = P1 - P0
    n = np.array([d[1], -d[0]]) / np.linalg.norm(d)          # 線的法向（指向右上＝手臂那一側）
    sd = (xx - P0[0]) * n[0] + (yy - P0[1]) * n[1]
    tpar = ((xx - P0[0]) * d[0] + (yy - P0[1]) * d[1]) / (d @ d)
    band = (np.abs(sd) < 2.5) & (tpar > -0.15) & (tpar < 1.15)
    lab, _ = ndimage.label(op & ~band)
    arm_id = lab[HAND[1], HAND[0]]
    assert arm_id > 0
    arm = lab == arm_id
    assert arm.sum() < op.sum() * 0.3, arm.sum()
    arm = ndimage.binary_dilation(arm, iterations=3) & op & (sd > -3)      # 切線上的那幾 px 也算手臂
    # 手臂片：手臂＋袖子內側 22 px（身體那一側，只取袖子範圍：切線附近、y 400–720）
    over = op & (sd <= 0) & (sd > -22) & (tpar > 0.0) & (tpar < 1.0)
    arm_piece = src.copy()
    arm_piece[..., 3] = np.where(arm | over, src[..., 3], 0)
    body = src.copy()
    body[..., 3] = np.where(arm & (sd > 1.5), 0, src[..., 3])
    # 人物外框（身體＋手臂合起來）→ 共同的裁切與縮放
    ys, xs = np.where(op)
    fy0, fy1 = ys.min(), ys.max()
    k = OUT_FIG_PX / (fy1 - fy0)
    ppw = (fy1 - fy0) / FIG_H_WORLD                          # 原圖每世界單位幾 px

    def crop_scale(a, mask):
        ys2, xs2 = np.where(mask)
        x0, x1, y0, y1 = xs2.min() - 6, xs2.max() + 7, ys2.min() - 6, ys2.max() + 7
        c = a[y0:y1, x0:x1].astype(np.float32)
        pm = c.copy(); pm[..., :3] *= c[..., 3:4] / 255.0
        w2, h2 = max(4, round((x1 - x0) * k)), max(4, round((y1 - y0) * k))
        r = np.asarray(Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), "RGBA").resize((w2, h2), Image.LANCZOS), np.float32)
        al = np.maximum(r[..., 3:4], 1e-3)
        r[..., :3] = np.where(r[..., 3:4] > 0.5, r[..., :3] * 255.0 / al, 0)
        return np.clip(r, 0, 255).astype(np.uint8), (x0, y0, x1, y1)

    bm = body[..., 3] > 100
    b_img, (bx0, by0, bx1, by1) = crop_scale(body, bm)
    am = arm_piece[..., 3] > 100
    a_img, (ax0, ay0, ax1, ay1) = crop_scale(arm_piece, am)
    out_dir = Path(out_dir)
    save(b_img, out_dir / "a5-student_v03.png")
    save(a_img, out_dir / "a5-student-arm_v03.png")
    # 世界座標：身體圖的原點＝底邊中點（imagePlane）；樞紐＝袖口中點
    piv = (P0 + P1) / 2 + np.array([-4.0, 0.0])
    bcx, bby = (bx0 + bx1) / 2, by1
    acx, aby = (ax0 + ax1) / 2, ay1
    meta = {
        "body_w": round((bx1 - bx0) / ppw, 4), "body_h": round((by1 - by0) / ppw, 4),
        "arm_w": round((ax1 - ax0) / ppw, 4), "arm_h": round((ay1 - ay0) / ppw, 4),
        # 樞紐相對身體底邊中點（世界單位，y 向上）
        "pivot_in_body": [round((piv[0] - bcx) / ppw, 4), round((bby - piv[1]) / ppw, 4)],
        # 手臂圖的底邊中點相對樞紐（世界單位）：把手臂幾何平移這麼多，樞紐就在原點
        "arm_origin_from_pivot": [round((acx - piv[0]) / ppw, 4), round((piv[1] - aby) / ppw, 4)],
        "fig_h_world": FIG_H_WORLD, "raw": str(RAW.relative_to(ROOT)),
        "body_px": list(b_img.shape[1::-1]), "arm_px": list(a_img.shape[1::-1]),
    }
    print("student v03", meta)
    return meta


if __name__ == "__main__":
    import os
    build(os.environ.get("A5_ART_OUT") or ROOT / "assets/final/sets/a5_gate")
