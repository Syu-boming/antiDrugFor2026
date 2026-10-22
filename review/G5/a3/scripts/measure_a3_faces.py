"""第三幕新姿勢的退路臉部範圍（FALLBACK_FACES 格式）＋兩眼同閉檢查：照 G5 共用美術 measure_faces.py（import 它的 measure、
g5lib.blink_check、zoom_face），紀錄寫在 review/G5/a3/（face_boxes.json、blink_check.json、faces/*.png），不寫共用資料夾。
xiaoqing:forehead_l＝forehead 的左右翻轉：眼框、嘴框依圖寬鏡射。
用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/measure_a3_faces.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import g5lib as L  # noqa: E402
import measure_faces as MF  # noqa: E402

OUT = ROOT / "review/G5/a3"
FACES = OUT / "faces"
POSE = {"pose-pointr": "pointr", "pose-glasses": "glasses"}
# 人工更正（看 faces/*.png 放大圖量的；自動量測只抓到黑眼珠、沒包到眼白，或被手指擋住少一隻眼）
MANUAL = {
    "xiaoqing:pointr": {"eyes": [[261, 214, 319, 274], [373, 203, 413, 263]], "mouth": [315, 293, 373, 313], "paintedMouth": "smile"},
    "xiaoyu:glasses": {"region": [150, 220, 340, 380], "eyes": [[180, 255, 203, 297], [273, 273, 301, 316]], "mouth": [226, 347, 254, 357],
                       "paintedMouth": "closed"},
}


def main():
    FACES.mkdir(parents=True, exist_ok=True)
    imp = json.loads((OUT / "import.json").read_text())
    boxes, bc = {}, {}
    for rid, rec in imp.items():
        if "final" not in rec:
            continue
        key = f"{rec['character']}:{POSE[rec['part']]}"
        a, fb, auto = MF.measure(key, rec, MANUAL)
        if len(fb["eyes"]) != 2 or not fb["mouth"]:
            print(key, "自動量測不完整", auto["candidates"][:8])
            boxes[key] = {"_incomplete": True, **fb}
            continue
        res = L.blink_check(a, fb)
        bc[key] = {"image": rec["final"], **res}
        boxes[key] = {**fb, "_image": rec["final"]}
        L.zoom_face(a, fb, label=key).save(FACES / f"{key.replace(':', '_')}.png")
        e = res["closed"]["eyes"]
        print(key, "眼", fb["eyes"], "嘴", fb["mouth"], fb.get("patchK"), "閉眼殘留", [x["residual_ratio"] for x in e],
              "線", [x["lid_line_px"] for x in e], "通過" if res["both_closed_ok"] else "不通過")
    # forehead_l（鏡射）
    sc = json.loads((ROOT / "assets/final/rig/show_characters.json").read_text())
    src = sc["fallbackFaces"]["xiaoqing:forehead"]
    im = Image.open(ROOT / "assets/final/chr-xiaoqing_pose-forehead-l_v01.png").convert("RGBA")
    a = np.array(im)
    W = a.shape[1]
    mir = lambda b: [W - b[2], b[1], W - b[0], b[3]]   # noqa: E731
    fb = {k: v for k, v in src.items() if not k.startswith("_")}
    fb["ref"] = L.alpha_ref(a)
    # 原圖的 ref 是不透明範圍左上角；翻轉後先換回絕對座標再鏡射
    r0 = src["ref"]
    a0 = np.array(Image.open(ROOT / "assets/final/chr-xiaoqing_pose-forehead_v06.png").convert("RGBA"))
    ref0 = L.alpha_ref(a0)
    dx, dy = ref0[0] - r0[0], ref0[1] - r0[1]
    fb["eyes"] = sorted([mir([e[0] + dx, e[1] + dy, e[2] + dx, e[3] + dy]) for e in src["eyes"]], key=lambda b: b[0])
    m = src["mouth"]
    fb["mouth"] = mir([m[0] + dx, m[1] + dy, m[2] + dx, m[3] + dy])
    fb["ref"] = ref0 if False else L.alpha_ref(a)
    # 翻轉後的座標是絕對座標，ref 也用翻轉圖的不透明左上角；引擎依 ref 平移（兩者同一張圖，所以位移 0）
    res = L.blink_check(a, fb)
    key = "xiaoqing:forehead_l"
    bc[key] = {"image": "assets/final/chr-xiaoqing_pose-forehead-l_v01.png", **res}
    boxes[key] = {**fb, "_image": "assets/final/chr-xiaoqing_pose-forehead-l_v01.png", "_note": "xiaoqing:forehead 的鏡射"}
    L.zoom_face(a, fb, label=key).save(FACES / "xiaoqing_forehead_l.png")
    e = res["closed"]["eyes"]
    print(key, "眼", fb["eyes"], "嘴", fb["mouth"], "閉眼殘留", [x["residual_ratio"] for x in e], "通過" if res["both_closed_ok"] else "不通過")
    (OUT / "face_boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=1, default=str))
    (OUT / "blink_check.json").write_text(json.dumps(bc, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
