"""投影模擬與可讀性檢查圖（v1.2 第 14.2 節）。

用法：/opt/anaconda3/bin/python3 tools/projsim.py 輸入圖 [輸出資料夾] [--profile v2|v1]
輸出：
  <名稱>_proj.png   投影模擬（壓縮對比、抬高黑位、降彩度）——預設 v2（G2 第 2 輪起；第 1 輪意見第 23 條要求加強）
  <名稱>_gray.png   灰階（WCAG 相對亮度）
  <名稱>_deut.png   綠色弱模擬（Machado 2009, severity 1.0）
  <名稱>_sheet.png  四聯圖：原圖／投影模擬／灰階／色盲
  <名稱>_lowc.png   低對比模擬（近似 Chrome DevTools「Reduced contrast」：CSS contrast(50%)，在原圖上套用）
  <名稱>_stress_sheet.png  壓力對照：原圖／投影 v1（第 1 輪）／投影 v2／低對比
透明圖會先鋪在中灰紙色背景上。

投影模擬參數：
  v1（第 1 輪）：彩度 ×0.72、黑位 0.14、白位 0.90 → 黑位相對亮度 0.0174、最亮 0.787（範圍 12.4:1）
  v2（第 2 輪）：彩度 ×0.65、黑位 0.18、白位 0.87 → 黑位相對亮度 0.0272、最亮 0.729（範圍 10.1:1）
  v2 模擬的是開燈教室裡的一般投影機；場地實拍（14.2 場地實測）仍須另外安排，這裡無法取代。
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = (232, 226, 214)  # 舞台紙色背景
PROFILES = {"v1": (0.72, 0.14, 0.90), "v2": (0.65, 0.18, 0.87)}
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)


def load_rgb(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    return Image.alpha_composite(bg, im).convert("RGB")


def to_linear(a):
    a = a / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def to_srgb(a):
    a = np.clip(a, 0, 1)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055) * 255


def projector(rgb, profile="v2"):
    sat, lo, hi = PROFILES[profile]
    a = rgb.astype(np.float32) / 255.0
    gray = a.mean(axis=-1, keepdims=True)
    a = gray + (a - gray) * sat           # 降彩度
    a = lo + a * (hi - lo)                # 黑位抬高、白位降低（開燈的教室）
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def projector_v1(rgb):
    return projector(rgb, "v1")


def low_contrast(rgb, k=0.5):
    """CSS contrast(k)：以 0.5 為中心壓縮（sRGB 值域）。"""
    a = rgb.astype(np.float32) / 255.0
    return (np.clip((a - 0.5) * k + 0.5, 0, 1) * 255).astype(np.uint8)


def grayscale(rgb):
    lin = to_linear(rgb.astype(np.float32))
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    g = to_srgb(y)
    return np.repeat(g[..., None], 3, axis=2).astype(np.uint8)


def deuteranopia(rgb):
    m = np.array([[0.367, 0.861, -0.228],
                  [0.280, 0.673, 0.047],
                  [-0.012, 0.043, 0.969]])  # Machado 2009, severity 1.0
    lin = to_linear(rgb.astype(np.float32))
    return to_srgb(lin @ m.T).astype(np.uint8)


def _sheet(views, w, h, path, title=None):
    scale = 640 / w
    tw, th = int(w * scale), int(h * scale)
    top = 30 if title is None else 58
    sheet = Image.new("RGB", (tw * len(views) + 10 * (len(views) + 1), th + top + 10), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(FONT[0], 18, index=FONT[1])
    except OSError:
        f = ImageFont.load_default()
    if title:
        draw.text((10, 6), title, font=f, fill=(240, 240, 240))
    for i, (label, arr) in enumerate(views):
        sheet.paste(Image.fromarray(arr).resize((tw, th), Image.LANCZOS), (10 + i * (tw + 10), top))
        draw.text((10 + i * (tw + 10), top - 24), label, font=f, fill=(240, 240, 240))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out", nargs="?", default=None)
    ap.add_argument("--profile", default="v2", choices=sorted(PROFILES))
    args = ap.parse_args()
    src = Path(args.src)
    out = Path(args.out) if args.out else src.parent
    out.mkdir(parents=True, exist_ok=True)
    rgb = np.array(load_rgb(src))
    views = {"proj": projector(rgb, args.profile), "gray": grayscale(rgb), "deut": deuteranopia(rgb)}
    for k, v in views.items():
        Image.fromarray(v).save(out / f"{src.stem}_{k}.png")
    lowc = low_contrast(rgb)
    Image.fromarray(lowc).save(out / f"{src.stem}_lowc.png")
    w, h = rgb.shape[1], rgb.shape[0]
    sat, lo, hi = PROFILES[args.profile]
    _sheet([("original 原圖", rgb), (f"proj 投影模擬 {args.profile}", views["proj"]), ("gray 灰階", views["gray"]),
            ("deut 綠色弱", views["deut"])], w, h, out / f"{src.stem}_sheet.png",
           title=f"{src.name}｜投影模擬 {args.profile}：彩度×{sat}、黑位 {lo}、白位 {hi}")
    _sheet([("original 原圖", rgb), ("proj v1（第 1 輪）", projector(rgb, "v1")), ("proj v2（第 2 輪）", projector(rgb, "v2")),
            ("低對比 contrast(50%)", lowc)], w, h, out / f"{src.stem}_stress_sheet.png",
           title=f"{src.name}｜壓力對照：投影 v1／v2 與低對比模擬")
    print(out / f"{src.stem}_sheet.png")


if __name__ == "__main__":
    main()
