"""G4 關卡決定後、G5 開工前（主線，共用元件）：操偶線改成平面紙繩貼圖 tex-string-rope_v02。

G4 美術總監（G2 帶進 2、紙感與工藝）：v01 每隔約 10 px 一道規則斜向扭絞刻紋，像鋼索，不是 v1.2 第 15.2 節／REVIEW.md
要的「平面淡灰紙繩（纖維、深灰邊、受光邊），不用扭絞鋼索紋」。
這一版：沿用 v01 的版面（64×256、四方連續、左深灰邊 12 px｜受光邊 7 px｜繩身｜右深灰邊 12 px）與顏色，
拿掉扭紋，改成不規則的短纖維點紋（長 2–9 px、方向隨機），背光漸暗減半（平面紙，不做圓柱感）。
檢查：沿線（v 方向）繩身亮度剖面的自相關，週期 8–14 px（畫成 8 px 寬時）不得有明顯峰值；結果寫進
review/G4/art/string_tex_v02.json。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/make_string_tex_v02.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_string_tex as M  # noqa: E402

W, H, SS = M.W, M.H, M.SS


def rope_texture_v02():
    h, w = H * SS, W * SS
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    u = (xx + 0.5) / w
    img = np.ones((h, w, 3), np.float32) * M.BODY
    # 1) 不規則短纖維點紋（四方連續、方向隨機，避免任何規則斜紋）
    fib = np.zeros((h, w), np.float32)
    r = np.random.default_rng(2026)
    for _ in range(900):
        x, y = r.uniform(0, w), r.uniform(0, h)
        L = r.uniform(2, 9) * SS * 2          # 貼圖 px（畫成 8 px 寬時約 0.25–1.1 px 長）
        ang = r.uniform(0, np.pi)
        sgn = 1 if r.random() < 0.55 else -1
        for t in np.linspace(0, L, max(2, int(L))):
            xi, yi = int(x + np.cos(ang) * t) % w, int(y + np.sin(ang) * t) % h
            fib[yi, xi] += sgn
    fib = ndimage.gaussian_filter(fib, 1.0, mode="wrap")
    fib = fib / (np.abs(fib).max() + 1e-6)
    img += fib[..., None] * 26
    # 2) 粗紙紋（低頻，同 v01）
    n = ndimage.gaussian_filter(np.random.default_rng(7).standard_normal((h, w)), 6 * SS / 2, mode="wrap")
    img += (n / (n.std() + 1e-6))[..., None] * 3.0
    # 3) 背光：右側輕微漸暗（v01 的一半，平面紙繩）
    shade = np.clip((u - 0.55) / 0.27, 0, 1) ** 1.3
    img *= (1 - 0.08 * shade)[..., None]
    # 4) 邊（同 v01）：左深灰 12 px、受光 7 px；右深灰 12 px，邊緣輕微不規則
    edge_jit = ndimage.gaussian_filter(np.random.default_rng(3).standard_normal(h), 8 * SS, mode="wrap")
    edge_jit = edge_jit / (np.abs(edge_jit).max() + 1e-6) * 0.6 * SS
    px = xx / SS
    left_e = px < 12 + edge_jit[:, None] / SS
    lit = (px >= 12 + edge_jit[:, None] / SS) & (px < 19)
    right_e = px >= W - 12 - edge_jit[::-1, None] / SS
    img[lit] = img[lit] * 0.25 + M.LIT * 0.75
    img[left_e] = M.EDGE
    img[right_e] = M.EDGE
    out = img.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))
    return np.clip(out, 0, 255).astype(np.uint8)


def periodicity(tex):
    """沿線亮度剖面（繩身欄）的自相關：回傳畫成 8 px 寬時 8–14 px 週期範圍內的最大自相關。"""
    body = tex[:, 22:46].astype(np.float32).mean(axis=(1, 2))
    body = body - body.mean()
    ac = np.correlate(np.tile(body, 2), body, mode="valid")[:H]
    ac = ac / (ac[0] + 1e-6)
    tex_per_px = W / 8.0                      # 畫成 8 px 寬：1 螢幕 px＝8 貼圖 px（沿長方向同比例）
    lo, hi = int(8 * tex_per_px), int(14 * tex_per_px)
    return float(ac[lo:hi + 1].max()), float(np.abs(ac[1:]).max())


def main():
    v1 = np.array(Image.open(M.FIN / "tex-string-rope_v01.png").convert("RGB"))
    v2 = rope_texture_v02()
    Image.fromarray(v2, "RGB").save(M.FIN / "tex-string-rope_v02.png", optimize=True)
    p1, p2 = periodicity(v1), periodicity(v2)
    body2 = v2[:, 22:46].reshape(-1, 3).astype(np.float32)
    stats = {
        "rule": "沿線繩身亮度剖面的自相關；畫成 8 px 寬時週期 8–14 px 範圍內的最大值。規則斜紋會出現明顯峰值（v01），不規則纖維應接近 0。",
        "v01_ac_8_14px_max": round(p1[0], 3), "v02_ac_8_14px_max": round(p2[0], 3),
        "v02_body_srgb_mean": body2.mean(0).round(1).tolist(),
        "v02_body_lstar_mean": round(float(M.srgb_to_lstar(body2.mean(0))), 1),
        "v02_edge_srgb": v2[:, 2:10].reshape(-1, 3).mean(0).round(1).tolist(),
        "v02_lit_srgb": v2[:, 13:18].reshape(-1, 3).mean(0).round(1).tolist(),
        "seamless_v_maxdiff": int(np.abs(v2[0].astype(int) - v2[-1].astype(int)).max()),
    }
    (M.ART / "string_tex_v02.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    prev = Image.new("RGB", (2 * 256 + 24, 480), "white")
    prev.paste(Image.fromarray(v1).resize((256, 1024), Image.NEAREST).crop((0, 0, 256, 480)), (0, 0))
    prev.paste(Image.fromarray(v2).resize((256, 1024), Image.NEAREST).crop((0, 0, 256, 480)), (280, 0))
    prev.save(M.ART / "string_tex_v01_v02_4x.png")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
