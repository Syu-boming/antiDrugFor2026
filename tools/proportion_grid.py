"""比例格線對照圖（G2）：三位母版並排，畫出頭身格線，證明兒童 4–4.5 頭身、成人 6–6.5 頭身。

用法：/opt/anaconda3/bin/python3 tools/proportion_grid.py [--out review/G2/proportion_grid.png]
量測資料：review/G2/proportions.json
  每位角色：file（母版路徑，相對專案根目錄）、chin_y（下巴最低點的 y，人工以放大尺規圖量測）。
  頭頂與腳底由程式自動找：紙芯白邊內側第一個／最後一個「非白色不透明」像素列（深色內描線或頭髮）。
頭身＝（腳底 − 頭頂）÷（下巴 − 頭頂）。並排時依舞台合成的比例縮放（兒童身高＝成人 × child_ratio）。
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fix_proportion import inner_extent

ROOT = Path(__file__).resolve().parent.parent
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)
FONT_FALLBACK = ("/System/Library/Fonts/STHeiti Medium.ttc", 0)
TARGET = {True: (4.0, 4.5), False: (6.0, 6.5)}
NAMES = {"xiaoqing": "小晴", "xiaoyu": "小宇", "ale": "阿樂叔叔"}


def font(px):
    for p, i in (FONT, FONT_FALLBACK):
        try:
            return ImageFont.truetype(p, px, index=i)
        except OSError:
            pass
    return ImageFont.load_default()


def measure(path, chin_y):
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    opaque = a[..., 3] > 200
    top, bot = inner_extent(im)
    arows = np.nonzero(opaque.sum(1) > 0)[0]
    head = chin_y - top
    return dict(top=top, bottom=bot, chin=chin_y, head_px=head, height_px=bot - top,
                heads=(bot - top) / head, alpha_top=int(arows.min()), alpha_bottom=int(arows.max()),
                border_top_px=top - int(arows.min()), border_bottom_px=int(arows.max()) - bot), im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "review/G2/proportions.json"))
    ap.add_argument("--out", default=str(ROOT / "review/G2/proportion_grid.png"))
    args = ap.parse_args()
    data = json.loads(Path(args.data).read_text())
    ratio = data.get("child_ratio", 0.65)
    order = ["xiaoqing", "xiaoyu", "ale"]
    adult_h = 940
    margin_top, margin_bot = 130, 330
    cw, ch = 1980, adult_h + margin_top + margin_bot
    HW = 210  # 格線半寬
    canvas = Image.new("RGB", (cw, ch), (206, 202, 194))
    d = ImageDraw.Draw(canvas)
    f_big, f_mid, f_small = font(34), font(26), font(20)
    d.text((40, 30), "G2 母版比例格線（頭頂到下巴＝1 頭高；兒童身高＝成人 × %.2f）" % ratio, font=f_big, fill=(30, 30, 30))
    base_y = margin_top + adult_h
    results = {}
    col_w = cw // 3
    for i, key in enumerate(order):
        info = data["characters"][key]
        child = key != "ale"
        m, im = measure(ROOT / info["file"], info["chin_y"])
        target_h = adult_h * (ratio if child else 1.0)
        s = target_h / m["height_px"]
        crop = im.crop((0, m["top"], im.width, m["bottom"] + 1))
        a = np.array(crop.getchannel("A"))
        xs = np.nonzero(a.max(0) > 16)[0]
        crop = crop.crop((xs.min(), 0, xs.max() + 1, crop.height))
        crop = crop.resize((max(1, round(crop.width * s)), round(target_h)), Image.LANCZOS)
        cx = col_w * i + col_w // 2 - 20
        x0 = cx - crop.width // 2
        y0 = base_y - crop.height
        unit = m["head_px"] * s
        lo, hi = TARGET[child]
        # 目標範圍色帶（腳底應落在這裡）
        d.rectangle([cx - HW, round(y0 + unit * lo), cx + HW, round(y0 + unit * hi)], fill=(186, 214, 186))
        # 頭部色塊
        d.rectangle([cx - HW, y0, cx + HW, round(y0 + unit)], fill=(232, 214, 170))
        canvas.paste(crop, (x0, y0), crop)
        for k in range(int(np.floor(m["heads"])) + 1):
            y = round(y0 + unit * k)
            d.line([cx - HW, y, cx + HW, y], fill=(60, 60, 140), width=2)
            d.text((cx - HW - 30, y - 12), str(k), font=f_small, fill=(60, 60, 140))
        d.line([cx - HW, base_y, cx + HW, base_y], fill=(170, 30, 30), width=3)
        d.text((cx - HW - 74, base_y - 12), f"{m['heads']:.2f}", font=f_small, fill=(170, 30, 30))
        for v, lab in ((lo, f"{lo:g}"), (hi, f"{hi:g}")):
            y = round(y0 + unit * v)
            for xx in range(cx - HW, cx + HW, 16):
                d.line([xx, y, xx + 8, y], fill=(20, 120, 40), width=3)
            d.text((cx + HW + 6, y - 12), lab, font=f_small, fill=(20, 120, 40))
        ok = lo <= m["heads"] <= hi
        ty = base_y + 150
        d.text((cx - 200, ty), f"{NAMES[key]}：{m['heads']:.2f} 頭身", font=f_mid, fill=(20, 20, 20))
        d.text((cx - 200, ty + 36), f"目標 {lo:g}–{hi:g}：{'符合' if ok else '不符'}", font=f_mid,
               fill=(20, 110, 40) if ok else (170, 30, 30))
        d.text((cx - 200, ty + 72), f"頭高 {m['head_px']} px／身高 {m['height_px']} px（母版像素）", font=f_small, fill=(50, 50, 50))
        results[key] = dict(m, ok=bool(ok), target=[lo, hi], display_scale=round(s, 4))
    # 兒童頭高相對成人頭高（舞台比例）
    ah = results["ale"]["head_px"] * results["ale"]["display_scale"]
    for k in ("xiaoqing", "xiaoyu"):
        results[k]["head_vs_adult_head_on_stage"] = round(results[k]["head_px"] * results[k]["display_scale"] / ah, 3)
    d.text((40, ch - 40), "藍線＝每 1 頭高；紅線＝腳底（實測頭身）；綠色虛線＝目標頭身範圍上下限（腳底應落在綠色帶內）；黃色帶＝頭部（含頭髮）。",
           font=f_small, fill=(40, 40, 40))
    canvas.save(args.out)
    data["measured"] = results
    Path(args.data).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
