"""G4 修正第 1 輪（美術，問題 21）：後牆 v03——踢腳板提亮（開幕景片立起時，兒童軀幹帶落在踢腳板＋地板上，投影 v2 亮度只有 0.42）。

輸入 assets/final/bg-workshop-back_v02.jpg（不改原檔）→ 輸出 assets/final/bg-workshop-back_v03.jpg（尺寸、錨點、世界大小都不變）。
做法：只動最下方的踢腳板帶（和灰泥牆顏色明顯不同的連續橫帶）：保留紙紋與木紋高頻，平均色從 #DFB683 一帶（偏橘）
      改成淺木色 #F0DEC0，上緣留 2 px 較深的切口線（厚卡紙層次）。灰泥牆、柱子、層架、門洞完全不動。
預估：用 a0_c001 5.30 s 的 probe_bg 影格，把踢腳板像素依「貼圖→畫面」的實測色比換成新色，重算小晴量測區的投影 v2 亮度。
      正式數據要等引擎重擷取（capture/probe_report.json）。地板（畫面上約 0.34–0.38）不在本檔處理，見 notes。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/make_back_v03.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import capture_probe as C  # noqa: E402

FIN = ROOT / "assets/final"
ART = ROOT / "review/G4/art"
TARGET = np.array([240, 222, 192], np.float32)


def main():
    a = np.array(Image.open(FIN / "bg-workshop-back_v02.jpg").convert("RGB")).astype(np.float32)
    H, W = a.shape[:2]
    # 踢腳板：底部連續橫帶，B 明顯低於灰泥（R−B > 60）
    warm = (a[..., 0] - a[..., 2]) > 60
    rows = warm.mean(1)
    y0 = H - 1
    while y0 > H - 160 and rows[y0 - 1] > 0.6:
        y0 -= 1
    band = np.zeros((H, W), bool)
    band[y0:] = True
    band &= ndimage.binary_dilation(warm, iterations=2) | (np.arange(H)[:, None] >= y0 + 2)
    sub = a[band]
    mean0 = sub.mean(0)
    hp = a - ndimage.gaussian_filter(a, (2.0, 2.0, 0))
    out = a.copy()
    lowf = ndimage.gaussian_filter(a, (2.0, 2.0, 0))
    # 新色＝目標平均＋原本低頻偏差×0.5（保留木紋明暗起伏）＋高頻紙紋×0.8
    newc = TARGET + (lowf - mean0) * 0.5 + hp * 0.8
    out[band] = newc[band]
    # 上緣切口線
    edge = np.zeros((H, W), bool)
    edge[y0:y0 + 2] = True
    out[edge] = out[edge] * 0.86
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(FIN / "bg-workshop-back_v03.jpg", quality=92, subsampling=0)

    # 預估：probe_bg 影格的小晴量測區
    pb = np.array(Image.open(ROOT / "review/G4/pack/capture/probe_bg/a0_c001_005.30_mid.png").convert("RGB")).astype(np.float32)
    box = [1105, 807, 1194, 874]
    reg = pb[box[1]:box[3], box[0]:box[2]]
    warm_r = ((reg[..., 0] - reg[..., 2]) > 85) & (reg[..., 1] > 170)   # 畫面上的踢腳板（地板較暗，G < 170）
    ratio = reg[warm_r].mean(0) / mean0                                    # 貼圖 → 畫面 色比（燈光）
    sim = reg.copy()
    sim[warm_r] = np.clip(TARGET * ratio, 0, 255)

    def stat(x):
        lum = C.luminance(C.projector(x.astype(np.uint8)))
        return round(float(np.median(lum)), 3), round(float(np.percentile(lum, 10)), 3)

    rec = {
        "file": "assets/final/bg-workshop-back_v03.jpg", "source": "assets/final/bg-workshop-back_v02.jpg",
        "baseboard_rows_px": [int(y0), H], "baseboard_world_height": round((H - y0) * 0.007422, 3),
        "baseboard_mean_srgb_before": mean0.round(1).tolist(), "baseboard_mean_srgb_after": out[band].reshape(-1, 3).mean(0).round(1).tolist(),
        "a0_c001_5.30_xiaoqing_box": box,
        "projv2_median_p10_before": stat(reg), "projv2_median_p10_after_estimate": stat(sim),
        "baseboard_px_in_box": int(warm_r.sum()), "box_px": int(warm_r.size),
        "note": "預估值（色比換算），正式數據以引擎重擷取的 probe_report.json 為準；量測區下緣仍含約 20% 地板（投影 v2 約 0.34–0.38），p10 由地板決定。",
    }
    (ART / "wall_v03.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    # 對照圖
    c0 = Image.fromarray(a.astype(np.uint8)).crop((0, H - 260, W, H)).resize((W // 2, 130))
    c1 = Image.fromarray(out).crop((0, H - 260, W, H)).resize((W // 2, 130))
    S = Image.new("RGB", (W // 2, 270), (44, 42, 40))
    S.paste(c0, (0, 0)); S.paste(c1, (0, 140))
    S.save(ART / "wall_v03_compare.png")


if __name__ == "__main__":
    main()
