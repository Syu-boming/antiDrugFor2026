"""投影模擬與可讀性檢查圖（v1.2 第 14.2 節）。

用法：/opt/anaconda3/bin/python3 tools/projsim.py 輸入圖 [輸出資料夾]
輸出：<名稱>_proj.png（投影模擬：壓縮對比、抬高黑位、降彩度）、
      <名稱>_gray.png（灰階）、<名稱>_deut.png（綠色弱模擬），
      以及三張並排的 <名稱>_sheet.png。透明圖會先鋪在中灰紙色背景上。
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

BG = (232, 226, 214)  # 舞台紙色背景


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


def projector(rgb):
    a = rgb.astype(np.float32) / 255.0
    gray = a.mean(axis=2, keepdims=True)
    a = gray + (a - gray) * 0.72          # 彩度降低約三成
    a = 0.14 + a * (0.90 - 0.14)          # 黑位抬高、白位略降（開燈的教室）
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


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


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent
    out.mkdir(parents=True, exist_ok=True)
    rgb = np.array(load_rgb(src))
    views = {"proj": projector(rgb), "gray": grayscale(rgb), "deut": deuteranopia(rgb)}
    for k, v in views.items():
        Image.fromarray(v).save(out / f"{src.stem}_{k}.png")
    w, h = rgb.shape[1], rgb.shape[0]
    scale = 640 / w
    tw, th = int(w * scale), int(h * scale)
    sheet = Image.new("RGB", (tw * 4 + 50, th + 40), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, (label, arr) in enumerate([("original", rgb)] + list(views.items())):
        sheet.paste(Image.fromarray(arr).resize((tw, th)), (10 + i * (tw + 10), 30))
        draw.text((10 + i * (tw + 10), 8), label, fill=(240, 240, 240))
    sheet.save(out / f"{src.stem}_sheet.png")
    print(out / f"{src.stem}_sheet.png")


if __name__ == "__main__":
    main()
