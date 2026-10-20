"""題卡樣張的四欄模擬（投影 v2／低對比／灰階／綠色弱）＋逐元素對比量測（G2 第 3 輪，投影可讀性意見 20）。

用法：/opt/anaconda3/bin/python3 tools/quizcard_sims.py [--dir review/G2]
讀 quizcard_q1_v03.json（tools/quizcard_sample.mjs 產生）與三張狀態截圖，輸出：
  quizcard_q1_sims_v03.png   每個狀態一列：原圖＋四欄模擬
  quizcard_q1_v03.json       補上 contrast（每列數字、手指圖示、形狀標記、選項文字 對 題卡紙底；原圖／投影 v2／低對比／灰階）
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from projsim import projector, low_contrast, grayscale, deuteranopia, FONT  # noqa: E402


def rel_lum(rgb):
    a = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def cr(a, b):
    hi, lo = max(a, b), min(a, b)
    return round((hi + 0.05) / (lo + 0.05), 2)


def font(px):
    try:
        return ImageFont.truetype(FONT[0], px, index=FONT[1])
    except OSError:
        return ImageFont.load_default()


def element_contrast(img, box, paper):
    """元素（文字或圖示）墨色＝框內最暗 15% 像素中位數（形狀標記取框中心 30% 的中位數），對紙底。"""
    x, y, w, h = box
    reg = img[y:y + h, x:x + w].reshape(-1, 3)
    lum = rel_lum(reg)
    ink = reg[lum <= np.percentile(lum, 15)]
    return np.median(ink, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "review/G2"))
    a = ap.parse_args()
    d = Path(a.dir)
    rep = json.loads((d / "quizcard_q1_v03.json").read_text())
    views = [("原圖", lambda x: x), ("投影 v2", lambda x: projector(x, "v2")), ("低對比 contrast(50%)", low_contrast),
             ("灰階", grayscale), ("綠色弱（Machado 1.0）", deuteranopia)]
    tw, th = 560, 315
    states = ["question", "reveal", "lamp"]
    zh = {"question": "出題（思考時靜止，無倒數）", "reveal": "揭答（紙印章＋勾號＋外框，其他變淡）", "lamp": "點燈（第 1 盞紙燈漸亮）"}
    sheet = Image.new("RGB", (len(views) * (tw + 12) + 12, len(states) * (th + 46) + 70), (36, 36, 38))
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 12), "題卡樣張 Q1（劇場程式實際樣式，1920×1080 擷取）：原圖＋投影 v2、低對比、灰階、綠色弱四欄模擬", font=font(22), fill=(240, 240, 240))
    for r, st in enumerate(states):
        img = np.array(Image.open(ROOT / rep["states"][st]["file"]).convert("RGB"))
        y = 60 + r * (th + 46)
        dr.text((12, y), zh[st], font=font(19), fill=(255, 220, 120))
        res = {}
        card = rep["states"][st]["card"]
        for c, (name, f) in enumerate(views):
            v = f(img)
            sheet.paste(Image.fromarray(v).resize((tw, th), Image.LANCZOS), (12 + c * (tw + 12), y + 28))
            if r == 0:
                dr.text((12 + c * (tw + 12), 40), name, font=font(17), fill=(220, 220, 220))
            if name.startswith("綠"):
                continue
            # 紙底：題卡範圍內，避開文字列的區域（卡片右下角內側）
            cx, cy, cw, ch = card
            paper = np.median(v[cy + ch - 40:cy + ch - 20, cx + 30:cx + 200].reshape(-1, 3), 0)
            lp = float(rel_lum(paper))
            rows = []
            for i, row in enumerate(rep["states"][st]["rows"]):
                e = {}
                for k in ("num", "hand", "shape", "text"):
                    ink = element_contrast(v, row[k], paper)
                    e[k] = cr(float(rel_lum(ink)), lp)
                e["row_opacity"] = row["opacity"]
                rows.append(e)
            res[name] = dict(paper_hex="#%02X%02X%02X" % tuple(paper.round().astype(int)), rows=rows)
        rep["states"][st]["contrast"] = res
    sheet.save(d / "quizcard_q1_sims_v03.png")
    rep["note"] = ("選項字身 80 px@1080（app/src/ui/theater.css：var(--H)×0.0741），題目 68 px；每列＝大號數字＋手指圖示（伸出 1/2/3 根）＋形狀標記"
                   "（1 圓、2 三角、3 方），不只靠顏色。contrast＝元素最暗 15% 像素對題卡紙底的 WCAG 比；揭答後非正解列刻意變淡（不透明度 0.36）。")
    (d / "quizcard_q1_v03.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    for st in states:
        c = rep["states"][st]["contrast"]
        print(st, {k: [r["text"] for r in v["rows"]] for k, v in c.items()})


if __name__ == "__main__":
    main()
