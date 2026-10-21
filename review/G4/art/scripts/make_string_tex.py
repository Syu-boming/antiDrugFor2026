"""G4 修正第 1 輪（美術）：操偶線紙繩貼圖＋紙環貼圖（G4 問題 22、23、34；v1.2 第 15.2 節「灰色扭紋紙繩」）。

輸出（都在 assets/final/，打包 id 去掉 _vNN）：
  tex-string-rope_v01.png  64×256 不透明。u（橫向）＝跨線寬，左＝受光邊；v（縱向）＝沿線長，上下四方連續，
                           一個貼圖週期＝4 個線寬長（與 strings.ts 的 vRepeat = len /(width·4) 相同）。
                           由左到右：深灰邊 12 px｜淡色受光邊 7 px｜淡灰紙繩身（sRGB≈172，斜向扭紋＋紙纖維）｜背光漸暗｜深灰邊 12 px。
                           畫成 8 px 寬時：兩側深灰邊各約 1.5 px、受光邊約 1 px。
  tex-string-ring_v01.png  128×128 透明。紙環（圓環）：外側深灰細線＋白色紙芯邊＋淡灰紙環身＋內側深灰細線，中間透明（看得到肢體）。
                           不是矩形帶、鉚釘或扁板。建議畫成直徑 ≈2.4×線寬（中景約 19 px）。
另外輸出檢查圖與數據：
  review/G4/art/string_preview_v01.png  在 G4 實際關鍵影格上模擬 8 px 線＋紙環（1:1 與 4× 放大、投影 v2）
  review/G4/art/string_tex_v01.json     顏色、ΔL*（對牆、皮膚、工作褲、袖子；原圖與投影 v2）
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/make_string_tex.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import projsim  # noqa: E402

FIN = ROOT / "assets/final"
ART = ROOT / "review/G4/art"

BODY = np.array([188, 186, 180], np.float32)    # 淡灰紙繩身（sRGB 170–200 的較深端，保留對淺牆的明度差）
EDGE = np.array([64, 61, 58], np.float32)       # 深灰邊
LIT = np.array([226, 223, 215], np.float32)     # 淡色受光邊
CREASE = np.array([116, 113, 108], np.float32)  # 扭紋摺痕（暗）
FOLD = np.array([216, 213, 206], np.float32)    # 摺痕旁的亮面
RING_WHITE = np.array([250, 246, 236], np.float32)
RING_BODY = np.array([214, 210, 200], np.float32)

W, H = 64, 256
SS = 4  # 超取樣


def srgb_to_lstar(rgb):
    a = np.asarray(rgb, np.float32) / 255.0
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return np.where(y > 216 / 24389, 116 * np.cbrt(y) - 16, (24389 / 27) * y)


def rope_texture():
    h, w = H * SS, W * SS
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    u = (xx + 0.5) / w            # 0..1 跨寬
    v = (yy + 0.5) / h            # 0..1 沿長（一個週期＝4 線寬）
    img = np.ones((h, w, 3), np.float32) * BODY
    # 1) 斜向扭紋：每個週期 3 道（線寬 8 px 時約每 10.7 px 一道），角度約 35°，摺痕帶一點不規則起伏
    n_tw = 3
    slope = 0.70 * (W / H) * 4    # 在 (u, v) 空間：跨一個線寬，v 前進 0.70 個線寬
    rng = np.random.default_rng(15)
    wob = np.zeros_like(u)
    for k in (1, 2):
        wob += rng.uniform(0.004, 0.009) * np.sin(2 * np.pi * (k * u * 1.0 + rng.uniform(0, 1)))
    phase = (v * n_tw - u * slope * n_tw / 4 + wob * n_tw) % 1.0
    d_crease = np.minimum(phase, 1 - phase)                         # 0 在摺痕中心
    crease = np.clip(1 - d_crease / 0.10, 0, 1) ** 1.2             # 暗摺痕
    fold = np.clip(1 - np.abs(phase - 0.2) / 0.1, 0, 1) ** 1.4    # 摺痕下方亮面
    img = img * (1 - 0.9 * crease[..., None]) + CREASE * (0.9 * crease[..., None])
    img = img * (1 - 0.65 * fold[..., None]) + FOLD * (0.65 * fold[..., None])
    # 2) 紙纖維：沿長方向的細短纖維（四方連續）
    fib = np.zeros((h, w), np.float32)
    r = np.random.default_rng(913)
    for _ in range(420):
        x, y = r.uniform(0, w), r.uniform(0, h)
        L = r.uniform(10, 44) * SS / 2
        ang = np.pi / 2 + r.normal(0, 0.35)
        sgn = 1 if r.random() < 0.5 else -1
        for t in np.linspace(0, L, int(L)):
            xi, yi = int(x + np.cos(ang) * t) % w, int(y + np.sin(ang) * t) % h
            fib[yi, xi] += sgn
    fib = ndimage.gaussian_filter(fib, 1.2, mode="wrap")
    fib = fib / (np.abs(fib).max() + 1e-6)
    img += fib[..., None] * 22
    # 3) 粗紙紋（低頻）
    n = ndimage.gaussian_filter(np.random.default_rng(7).standard_normal((h, w)), 6 * SS / 2, mode="wrap")
    img += (n / (n.std() + 1e-6))[..., None] * 3.0
    # 4) 背光：右側 30% 漸暗（圓柱感，但仍是平面紙繩）
    shade = np.clip((u - 0.55) / 0.27, 0, 1) ** 1.3
    img *= (1 - 0.16 * shade)[..., None]
    # 5) 邊：左深灰 12 px、受光 7 px；右深灰 12 px（邊緣用紙纖維輕微不規則）
    edge_jit = ndimage.gaussian_filter(np.random.default_rng(3).standard_normal(h), 8 * SS, mode="wrap")
    edge_jit = edge_jit / (np.abs(edge_jit).max() + 1e-6) * 0.6 * SS
    px = xx / SS
    left_e = px < 12 + edge_jit[:, None] / SS
    lit = (px >= 12 + edge_jit[:, None] / SS) & (px < 19)
    right_e = px >= W - 12 - edge_jit[::-1, None] / SS
    img[lit] = img[lit] * 0.25 + LIT * 0.75
    img[left_e] = EDGE
    img[right_e] = EDGE
    out = img.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))
    return np.clip(out, 0, 255).astype(np.uint8)


def ring_texture(S=128):
    s = S * SS
    yy, xx = np.mgrid[:s, :s].astype(np.float32)
    c = (s - 1) / 2
    r = np.hypot(xx - c, yy - c) / (s / 2)       # 0 中心 → 1 外緣（貼圖半徑 64 px）
    rgba = np.zeros((s, s, 4), np.float32)
    # 半徑分區（以 64 px 為 1）：外深灰 1.00–0.86｜白紙芯 0.86–0.74｜紙環身 0.74–0.56｜內深灰 0.56–0.47｜中間透明
    R_OUT, R_WHITE, R_BODY, R_IN, R_HOLE = 0.98, 0.85, 0.73, 0.56, 0.46
    a = (r <= R_OUT) & (r >= R_HOLE)
    rgba[a, :3] = EDGE
    m = (r < R_WHITE) & (r >= R_BODY)
    rgba[m, :3] = RING_WHITE
    m2 = (r < R_BODY) & (r >= R_IN)
    # 紙環身：淡灰紙＋纖維（沿圓周方向），上半略亮、下半略暗（紙帶繞到肢體下緣）
    ang = np.arctan2(yy - c, xx - c)
    fib = ndimage.gaussian_filter(np.random.default_rng(21).standard_normal((s, s)), 1.5, mode="wrap")
    body = RING_BODY + (fib / (fib.std() + 1e-6))[..., None] * 5
    body *= (1 - 0.06 * np.sin(ang))[..., None]
    rgba[m2, :3] = body[m2]
    # 白紙芯邊上的一道摺痕（紙環接口），在左下方
    seam = m & (np.abs(((ang + np.pi) - 2.3) % (2 * np.pi)) < 0.05)
    rgba[seam, :3] = RING_WHITE * 0.82
    rgba[a, 3] = 255
    out = rgba.reshape(S, SS, S, SS, 4).mean(axis=(1, 3))
    # 透明處顏色外擴（避免縮圖白邊／黑邊）
    al = out[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~al, return_indices=True)
    out[~al, :3] = out[iy[~al], ix[~al], :3]
    return np.clip(out, 0, 255).astype(np.uint8)


def draw_strip(canvas, tex, p0, p1, width, ring=None, ring_d=None):
    """用貼圖在 canvas（float RGB）上畫一條直線紙繩（反向取樣，超取樣 4×4）。p1＝扣點（紙環中心）。"""
    h, w = canvas.shape[:2]
    p0 = np.array(p0, np.float32); p1 = np.array(p1, np.float32)
    d = p1 - p0; L = float(np.hypot(*d)); t_hat = d / L
    n_hat = np.array([-t_hat[1], t_hat[0]], np.float32)
    if n_hat[0] > 0:
        n_hat = -n_hat                         # u=0 在畫面左側（受光邊在左）
    x0, x1 = int(max(0, min(p0[0], p1[0]) - width - 2)), int(min(w, max(p0[0], p1[0]) + width + 2))
    y0, y1 = int(max(0, min(p0[1], p1[1]) - width - 2)), int(min(h, max(p0[1], p1[1]) + width + 2))
    k = 4
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    acc = np.zeros((y1 - y0, x1 - x0, 3), np.float32); cov = np.zeros((y1 - y0, x1 - x0), np.float32)
    th, tw = tex.shape[:2]
    # 縮小取樣：先把貼圖降到接近螢幕尺寸（模擬 mipmap）
    scale = width / tw
    small_w = max(4, int(round(tw * scale * 4)))
    small_h = max(4, int(round(th * scale * 4)))
    texs = np.array(Image.fromarray(tex).resize((small_w, small_h), Image.BOX), np.float32)
    for i in range(k):
        for j in range(k):
            px = xs + (j + 0.5) / k; py = ys + (i + 0.5) / k
            rel = np.stack([px - p0[0], py - p0[1]], -1)
            along = rel @ t_hat; across = rel @ n_hat
            inside = (along >= 0) & (along <= L) & (np.abs(across) <= width / 2)
            uu = ((-across / width) + 0.5)       # n_hat 指向左 → across>0 在左
            uu = 1 - uu
            vv = (along / (width * 4)) % 1.0
            ui = np.clip((uu * small_w).astype(int), 0, small_w - 1)
            vi = np.clip((vv * small_h).astype(int), 0, small_h - 1)
            col = texs[vi, ui]
            acc += col * inside[..., None]; cov += inside
    cov /= k * k
    acc /= (k * k)
    reg = canvas[y0:y1, x0:x1]
    canvas[y0:y1, x0:x1] = reg * (1 - cov[..., None]) + acc
    if ring is not None:
        rd = int(round(ring_d))
        rs = Image.fromarray(ring).resize((rd * 4, rd * 4), Image.LANCZOS).resize((rd, rd), Image.BOX)
        ra = np.array(rs, np.float32)
        cx, cy = int(round(p1[0] - rd / 2)), int(round(p1[1] - rd / 2))
        sub = canvas[cy:cy + rd, cx:cx + rd]
        al = ra[..., 3:4] / 255
        canvas[cy:cy + rd, cx:cx + rd] = sub * (1 - al) + ra[..., :3] * al
    return canvas


def main():
    rope = rope_texture()
    ring = ring_texture()
    Image.fromarray(rope, "RGB").save(FIN / "tex-string-rope_v01.png", optimize=True)
    Image.fromarray(ring, "RGBA").save(FIN / "tex-string-ring_v01.png", optimize=True)

    # 顏色量測（貼圖上的分區平均）
    body_cols = rope[:, 22:46].reshape(-1, 3).astype(np.float32)
    stats = {
        "rope_body_srgb_mean": body_cols.mean(0).round(1).tolist(),
        "rope_body_srgb_p10_p90_gray": [float(np.percentile(body_cols.mean(1), 10).round(1)), float(np.percentile(body_cols.mean(1), 90).round(1))],
        "rope_edge_srgb": rope[:, 2:10].reshape(-1, 3).mean(0).round(1).tolist(),
        "rope_lit_srgb": rope[:, 13:18].reshape(-1, 3).mean(0).round(1).tolist(),
        "rope_layout_px_of_64": {"深灰邊（左）": "0–11", "受光邊": "12–18", "繩身": "19–51（右側 30% 漸暗）", "深灰邊（右）": "52–63"},
        "at_8px_screen": {"深灰邊": "各約 1.5 px", "受光邊": "約 0.9 px", "扭紋間距": "約 10.7 px（每 4 線寬 3 道）"},
        "seamless_v_maxdiff": int(np.abs(rope[0].astype(int) - rope[-1].astype(int)).max()),
    }
    # ΔL*：繩身／深灰邊 對 G4 實際背景（原圖與投影 v2）
    bgs = {"後牆": (237, 226, 213), "阿樂皮膚": (252, 167, 95), "工作褲（膝前線）": (119, 89, 53), "白襯衫袖": (240, 226, 204)}
    body = np.array(stats["rope_body_srgb_mean"], np.float32)
    edge = np.array(stats["rope_edge_srgb"], np.float32)
    rows = {}
    for k, c in bgs.items():
        c = np.array(c, np.float32)
        pj = lambda x: projsim.projector(x[None, None, :].astype(np.uint8))[0, 0].astype(np.float32)
        rows[k] = {
            "繩身ΔL*": round(float(abs(srgb_to_lstar(body) - srgb_to_lstar(c))), 1),
            "繩身ΔL*_投影v2": round(float(abs(srgb_to_lstar(pj(body)) - srgb_to_lstar(pj(c)))), 1),
            "深灰邊ΔL*": round(float(abs(srgb_to_lstar(edge) - srgb_to_lstar(c))), 1),
            "深灰邊ΔL*_投影v2": round(float(abs(srgb_to_lstar(pj(edge)) - srgb_to_lstar(pj(c)))), 1),
        }
    stats["deltaL_vs_g4_backgrounds"] = rows
    stats["note"] = ("繩身改成淡灰（art/ale_a2_poses_fixed.png 的紙繩畫法），對淺牆的明度差主要由兩側深灰邊提供；"
                     "對工作褲（膝前線）的繩身 ΔL* 由舊版約 10 提高到約 30。tools/capture_probe.py 目前只取線中心像素，"
                     "建議改成「繩身或深灰邊對背景的較大者」或同時列出兩者。")

    # 預覽（不疊在舊畫面上）：線寬 6／8／10.5 px 畫在後牆、皮膚、工作褲、白襯衫四種底色上＋紙環；1:1 與 4× 放大、投影 v2
    from PIL import ImageFont
    font = ImageFont.truetype(projsim.FONT[0], 18)
    wall = np.array(Image.open(FIN / "bg-workshop-back_v02.jpg").convert("RGB").resize((1482, 708)), np.float32)
    swatch = np.zeros((240, 560, 3), np.float32)
    names = list(bgs)
    for i, k in enumerate(names):
        swatch[:, i * 140:(i + 1) * 140] = bgs[k]
    swatch[:, 0:140] = wall[300:540, 600:740]
    for wpx, x0 in ((6, 20), (8, 60), (10.5, 100)):
        for i in range(4):
            xx = i * 140 + x0
            swatch = draw_strip(swatch, rope, (xx - 8, -2), (xx + 6, 200), wpx)
            rd = int(round(wpx * 2.4))
            rs = np.array(Image.fromarray(ring).resize((rd * 4, rd * 4), Image.LANCZOS).resize((rd, rd), Image.BOX), np.float32)
            cx, cy = int(round(xx + 6 - rd / 2)), int(round(200 + wpx - rd / 2))
            al = rs[..., 3:4] / 255
            swatch[cy:cy + rd, cx:cx + rd] = swatch[cy:cy + rd, cx:cx + rd] * (1 - al) + rs[..., :3] * al
    sw = Image.fromarray(np.clip(swatch, 0, 255).astype(np.uint8))
    sw4 = sw.crop((40, 120, 180, 240)).resize((560, 480), Image.NEAREST)
    swp = Image.fromarray(projsim.projector(np.array(sw)))
    tex4 = Image.fromarray(rope).resize((256, 1024), Image.NEAREST).crop((0, 0, 256, 480))
    ring4 = Image.fromarray(ring).resize((256, 256), Image.NEAREST)
    S = Image.new("RGB", (1760, 820), (44, 42, 40))
    d = ImageDraw.Draw(S)
    d.text((16, 10), "操偶線紙繩 v01／紙環 v01：左上＝1:1（每格三條：6／8／10.5 px；底色：後牆、皮膚、工作褲、白襯衫）；左下＝同圖投影 v2", fill=(240, 240, 240), font=font)
    S.paste(sw, (16, 50)); S.paste(swp, (16, 320))
    d.text((600, 30), "4× 放大（後牆＋皮膚，8／10.5 px）", fill=(240, 210, 120), font=font)
    S.paste(sw4, (600, 56))
    d.text((1190, 30), "貼圖 4×（局部）", fill=(240, 210, 120), font=font)
    S.paste(tex4, (1190, 56))
    bgc = Image.new("RGBA", (256, 256), (120, 89, 53, 255)); bgc.alpha_composite(ring4)
    d.text((1470, 30), "紙環貼圖（工作褲底）", fill=(240, 210, 120), font=font)
    S.paste(bgc.convert("RGB"), (1470, 56))
    S.save(ART / "string_preview_v01.png")
    (ART / "string_tex_v01.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
