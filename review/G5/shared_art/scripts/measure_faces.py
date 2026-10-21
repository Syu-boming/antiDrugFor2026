"""G5 共用美術：每張立牌姿勢的退路臉部範圍（FALLBACK_FACES 格式）＋兩眼同閉檢查。

用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/measure_faces.py [key ...]
- 量測：頭部範圍內「膚色區的洞」裡的深色連通區（L* < 55）＝眼珠、眉毛、嘴線（g5lib.detect_face）。
  眼＝兩個最大、高寬比 ≥0.75 的連通區（外擴 1 px）；嘴＝兩眼下方、介於兩眼之間的最大連通區。
  自動結果寫在 face_boxes.json，人工更正寫在 face_boxes_manual.json（同 key 覆寫欄位），每張都要看放大圖確認。
- ref＝alpha ≥128 不透明範圍左上角（app/src/stage/face.ts shiftFallback 用）。
- 戴眼鏡（小宇）：glasses=true，patchK＝眼睛補片不超出鏡片的最大倍數（上限 1.32，下限 1.08）。
- 兩眼同閉檢查（g5lib.blink_check，模擬 face.ts drawFallback）：每隻眼原本的深色像素在閉眼換片上殘留 ≤3%、
  高光殘留 ≤2 px、眼皮線 ≥15 px；任一隻眼不通過＝不通過。結果 blink_check.json；放大圖 faces/<key>.png。
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
OUT = ROOT / "review/G5/shared_art"
FACES = OUT / "faces"
FIN = ROOT / "assets/final"

POSE_NAME = {"master": "stand", "pose-cross": "cross", "pose-palmno": "palmno", "pose-forehead": "forehead", "pose-walk": "walk",
             "pose-watch-dial": "dial", "pose-sit-lantern": "sit_lantern", "pose-walk-straps": "walk_straps", "pose-crouch": "crouch",
             "pose-sit": "sit"}
GLASSES = {"xiaoyu"}


def pick(cands, glasses):
    big = [c for c in cands if c[4] >= 40]
    eyes = [c for c in big if (c[3] - c[1]) / max(1, c[2] - c[0]) >= 0.75 and (c[3] - c[1]) <= 90]
    eyes = sorted(eyes, key=lambda c: -c[4])[:2]
    eyes.sort(key=lambda c: c[0])
    mouth = None
    if len(eyes) == 2:
        ey1 = max(e[3] for e in eyes)
        exl, exr = eyes[0][0] - 30, eyes[1][2] + 30
        ms = [c for c in big if c[1] > ey1 + 5 and c[0] > exl and c[2] < exr and c not in eyes]
        if ms:
            mouth = sorted(ms, key=lambda c: c[1])[0]
    return eyes, mouth


def lens_k(a, eye):
    """眼鏡：眼睛補片（橢圓 rx·k, ry·k 的實色區 0.82）不碰到鏡框深色線的最大 k。"""
    x0, y0, x1, y1 = eye
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    Lc = L.lab_of(a[..., :3])[..., 0]
    H, W = Lc.shape
    yy, xx = np.mgrid[:H, :W]
    eye_dark = np.zeros((H, W), bool)
    eye_dark[int(y0):int(math.ceil(y1)), int(x0):int(math.ceil(x1))] = True
    frame = (Lc < 40) & ~ndimage.binary_dilation(eye_dark, iterations=2)
    best = 1.08
    for k in np.arange(1.08, 1.5, 0.02):
        R = max(rx, ry) * k
        d = np.hypot((xx - cx) / (rx * k / R), (yy - cy) / (ry * k / R)) / R
        if (frame & (d <= 0.82)).any():
            break
        best = round(float(k), 2)
    return best


def measure(key, rec, manual):
    a = np.array(Image.open(ROOT / rec["final"]).convert("RGBA"))
    cid = rec["character"]
    glasses = cid in GLASSES
    m = manual.get(key, {})
    cands, region = L.detect_face(a, region=m.get("region"))
    eyes, mouth = pick(cands, glasses)
    fb = {"ref": L.alpha_ref(a), "eyes": [[e[0] - 1, e[1] - 1, e[2] + 1, e[3] + 1] for e in eyes],
          "mouth": [mouth[0], mouth[1], mouth[2], mouth[3]] if mouth else None, "paintedMouth": "smile"}
    if glasses:
        fb["glasses"] = True
    for k in ("eyes", "mouth", "paintedMouth", "patchK", "glasses"):
        if k in m:
            fb[k] = m[k]
    if glasses and "patchK" not in m and len(fb["eyes"]) == 2:
        fb["patchK"] = min(1.32, min(lens_k(a, e) for e in fb["eyes"]))
    if not glasses and "patchK" not in m and len(fb["eyes"]) == 2 and fb["mouth"]:
        # 沒戴眼鏡：從預設 1.3 往下找，取「兩眼殘留 ≤3% 且補片不溢出到頭髮／臉緣／背景」的最大倍數
        for k in (1.3, 1.25, 1.2, 1.15, 1.1, 1.05):
            t = dict(fb, patchK=k)
            r = L.blink_check(a, t)
            if r["both_closed_ok"] and r["half"]["ok"]:
                if k != 1.3:
                    fb["patchK"] = k
                break
    auto = {"candidates": cands[:10], "region": region}
    return a, fb, auto


def main():
    imp = json.loads((OUT / "import.json").read_text())
    manual_p = OUT / "face_boxes_manual.json"
    manual = json.loads(manual_p.read_text()) if manual_p.exists() else {}
    out_p = OUT / "face_boxes.json"
    boxes = json.loads(out_p.read_text()) if out_p.exists() else {}
    bc_p = OUT / "blink_check.json"
    bc = json.loads(bc_p.read_text()) if bc_p.exists() else {}
    FACES.mkdir(parents=True, exist_ok=True)
    want = sys.argv[1:]
    for rid, rec in imp.items():
        if rid.startswith("_") or "final" not in rec:
            continue
        key = f"{rec['character']}:{POSE_NAME[rec['part']]}"
        if want and key not in want:
            continue
        a, fb, auto = measure(key, rec, manual)
        if len(fb["eyes"]) != 2 or not fb["mouth"]:
            print(key, "自動量測不完整", auto["candidates"][:8])
            boxes[key] = {"_incomplete": True, **fb, "_auto": auto}
            continue
        res = L.blink_check(a, fb)
        bc[key] = {"image": rec["final"], **res}
        boxes[key] = {**fb, "_image": rec["final"], "_auto": auto}
        L.zoom_face(a, fb, label=key).save(FACES / f"{key.replace(':', '_')}.png")
        e = res["closed"]["eyes"]
        print(key, "眼", fb["eyes"], "嘴", fb["mouth"], fb.get("patchK"), "閉眼殘留", [x["residual_ratio"] for x in e],
              "線", [x["lid_line_px"] for x in e], "通過" if res["both_closed_ok"] else "不通過")
    out_p.write_text(json.dumps(boxes, ensure_ascii=False, indent=1))
    bc_p.write_text(json.dumps(bc, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
