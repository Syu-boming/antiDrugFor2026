"""第三幕修正第 1 輪：邀請者的手＋貼紙盒（第三幕專用副本）。

驗收（b2_safety a3 第 1 項；b2_art a3 第 3 項）：
  - 盒子右上角的灰色短棒＋白色翹角可能被看成吸嘴（安全界線第 3 條）→ 拿掉灰色短棒、翹起的白色圓錐紙角，
    紙邊（白色貼紙外框）與盒子黑色上緣補成直線，盒面用周圍顏色補平（skimage 雙調和補圖＋原圖紙纖維雜訊）。
  - 手和盒子搶焦點 → 整張彩度降 15%（亮度不變）。
來源：assets/final/chr-inviter_hand-box_v01.png（第一幕也用；本檔不改它，只寫第三幕副本）。
輸出：assets/final/sets/a3_arcade/handbox_v01.png（圖像 id sets/a3_arcade/handbox）、review/G5/a3/art/handbox_fix1_check.png（前後放大對照）。
用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/build_a3_fix1_art.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from skimage.morphology import binary_dilation, disk

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "assets/final/chr-inviter_hand-box_v01.png"
OUT = ROOT / "assets/final/sets/a3_arcade/handbox_v01.png"
CHECK = ROOT / "review/G5/a3/art/handbox_fix1_check.png"


def main():
    src = Image.open(SRC).convert("RGBA")
    a = np.asarray(src).astype(np.float64)
    out = a.copy()

    # 1) 白色紙邊與黑色上緣：x 696–747 每一欄用 x=690 那一欄的縱向剖面（透明→白紙邊→黑線→盒面）平移補上
    ref_x = 690
    slope = 0.109                     # 紙邊上緣 y：690→32、745→38
    for x in range(696, 748):
        off = int(round((x - ref_x) * slope))
        for y in range(14, 47 + off):
            yy = y - off
            out[y, x] = a[yy, ref_x]
    # 2) 盒面上的灰色短棒（到黑色上緣以下的殘段、紙角上的小洞）與整個白色圓錐紙角：幾何遮罩（不靠顏色，免得漏掉陰影邊）→ 補成周圍盒面
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    edge_y = 45 + (xx - 690) * 0.1                      # 黑色上緣下面（盒面從這裡開始）
    # 短棒：線段 (701,57)→(731,29)，半寬 5 px
    p0, p1 = np.array([701.0, 57.0]), np.array([731.0, 29.0])
    d = p1 - p0
    tpar = np.clip(((xx - p0[0]) * d[0] + (yy - p0[1]) * d[1]) / (d @ d), 0, 1)
    dist = np.hypot(xx - (p0[0] + tpar * d[0]), yy - (p0[1] + tpar * d[1]))
    stick = (dist <= 5.0) & (yy >= edge_y)
    # 圓錐紙角（含上緣的小洞）：多邊形（8 倍放大圖量的頂點）
    poly = [(679, 55), (685, 50), (697, 49), (710, 53), (712, 62), (706, 73), (700, 85), (698, 97), (692, 91), (684, 76), (679, 64)]
    from PIL import ImageDraw as _D
    mimg = Image.new("L", (W, H), 0)
    _D.Draw(mimg).polygon(poly, fill=255)
    cone = np.asarray(mimg) > 0
    mask = binary_dilation(stick | cone, disk(2)) & (yy >= edge_y - 0.5)
    # 補色只取周圍「有彩度的盒面」像素（正規化高斯模糊）：不讓黑色轉折線、白色紙邊的顏色滲進補塊；補完再把盒子的轉折線畫回去
    rgb = a[..., :3] / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    keep_dark = (mx < 0.22) & ~binary_dilation(stick | cone, disk(1))     # 盒子的轉折線（在補塊外）
    valid = (~binary_dilation(mask, disk(1))) & (sat > 0.30) & (mx > 0.35) & (a[..., 3] > 250)
    from scipy.ndimage import gaussian_filter
    img3 = out[..., :3] / 255.0
    fill = np.zeros_like(img3)
    got = np.zeros(mask.shape, bool)
    for sig in (3.0, 5.0, 8.0, 12.0):
        wsum = gaussian_filter(valid.astype(float), sig)
        est = np.stack([gaussian_filter(img3[..., k] * valid, sig) for k in range(3)], -1) / np.maximum(wsum, 1e-6)[..., None]
        new_px = mask & ~got & (wsum > 0.08)
        fill[new_px] = est[new_px]
        got |= new_px
    # 紙纖維：補上的地方加細雜訊（和周圍的紙面顆粒相近）
    rng = np.random.default_rng(7)
    noise = gaussian_filter(rng.normal(0, 0.05, size=mask.shape), 0.7)[..., None]
    fill = np.clip(fill + noise, 0, 1)
    filled = out.copy()
    filled[..., :3] = np.where(mask[..., None], fill * 255.0, out[..., :3])
    filled[..., :3] = np.where((keep_dark & binary_dilation(mask, disk(3)))[..., None], a[..., :3], filled[..., :3])
    filled[..., 3] = np.where(mask, 255.0, out[..., 3])
    out = filled

    # 3) 整張彩度降 15%（以 Rec.709 亮度為軸，亮度不變）
    rgb = out[..., :3]
    lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
    out[..., :3] = np.clip(lum + (rgb - lum) * 0.85, 0, 255)

    res = Image.fromarray(out.round().astype(np.uint8), "RGBA")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.save(OUT, optimize=True)

    # 對照圖：前後各放大 6 倍（盒子右上角）＋整張縮圖
    CHECK.parent.mkdir(parents=True, exist_ok=True)
    box = (640, 0, 800, 130)
    S = 5
    def zoom(im):
        c = im.crop(box).resize(((box[2] - box[0]) * S, (box[3] - box[1]) * S), Image.NEAREST)
        bg = Image.new("RGBA", c.size, (96, 128, 96, 255)); bg.alpha_composite(c)
        return bg.convert("RGB")
    z0, z1 = zoom(src), zoom(res)
    th0 = Image.new("RGBA", src.size, (96, 128, 96, 255)); th0.alpha_composite(src)
    th1 = Image.new("RGBA", res.size, (96, 128, 96, 255)); th1.alpha_composite(res)
    tw = z0.width
    th0 = th0.convert("RGB").resize((tw, int(src.height * tw / src.width)))
    th1 = th1.convert("RGB").resize((tw, int(res.height * tw / res.width)))
    cv = Image.new("RGB", (tw * 2 + 10, z0.height + th0.height + 30), (30, 30, 30))
    cv.paste(z0, (0, 24)); cv.paste(z1, (tw + 10, 24))
    cv.paste(th0, (0, z0.height + 30)); cv.paste(th1, (tw + 10, z0.height + 30))
    d = ImageDraw.Draw(cv)
    d.text((4, 4), "before chr-inviter_hand-box_v01", fill=(255, 255, 0))
    d.text((tw + 14, 4), "after sets/a3_arcade/handbox_v01 (no stick / no cone corner, sat x0.85)", fill=(255, 255, 0))
    cv.save(CHECK)
    print("wrote", OUT.relative_to(ROOT), "mask px", int(mask.sum()), "check", CHECK.relative_to(ROOT))


if __name__ == "__main__":
    main()
