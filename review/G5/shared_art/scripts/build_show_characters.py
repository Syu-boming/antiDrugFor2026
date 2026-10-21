"""G5 共用美術：assets/final/rig/show_characters.json（多幕共用角色的立牌設定）＋比例檢查。

格式：characters[角色 id] ＝ app/src/stage/cast.ts 的 StandeeCharConfig（rig:'standee'、height、defaultPose、poses{名稱:{image, feet?, headTop?, face?}}、face?）；
fallbackFaces ＝ app/src/stage/face.ts FALLBACK_FACES 同格式（key＝「角色:姿勢」，ref＝alpha≥128 不透明範圍左上角）。

比例：引擎以「腳底到頭頂」換算每張姿勢圖的縮放（standee.ts：s = height / (feet.y − headTop)）。
  站著的姿勢讓引擎自動偵測（G4 做法：翻面前後身高一致）；行走＝自動偵測 ÷0.96（跨步變矮 4%）；
  坐、蹲用「頭頂到嘴巴中心的距離」和同角色站姿母版比，算出等效站姿身高，寫成虛擬 headTop（＝feet.y − 等效身高）。
  （頭頂到嘴巴的指標在小宇身上不可靠：捲髮蓬度與低頭會讓它偏大，所以站姿不用它；scale_report.json 仍列出供參考。）
坐姿：feet 改寫成「座面高度」對齊長椅座面 BENCH_SEAT（世界單位；prop-bench 的座面高）：feet.y ＝ 座面像素 y ＋ BENCH_SEAT ÷ 每像素世界長度。
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/build_show_characters.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402
from measure_faces import POSE_NAME  # noqa: E402

ROOT = L.ROOT
OUT = ROOT / "review/G5/shared_art"
FIN = ROOT / "assets/final"
BENCH_SEAT = 0.92   # 長椅座面高（世界單位）；阿樂叔叔 G4 圓凳 0.98

HEIGHT = {"xiaoqing": 2.5, "xiaoyu": 2.42, "pinan": 2.45, "lin": 3.42, "chen": 3.45, "ye": 3.58}
MASTER = {"xiaoqing": "chr-xiaoqing_master_v04.png", "xiaoyu": "chr-xiaoyu_master_v04.png"}
# 坐姿座面（姿勢圖像素 y；看 _tmp 格線量：大腿下緣含白邊）
SEAT_Y = {"pinan:sit_lantern": 990, "lin:sit": 1013}
EXPLICIT = {"sit_lantern", "sit", "crouch"}
# 既有姿勢（G4）照抄 cast.ts BUILTIN_RIGS 與 g4_manifest，方便各幕一次拿到完整名冊
G4_POSES = {
    "xiaoqing": {"stand": "chr-xiaoqing_master", "reach": "chr-xiaoqing_pose-reach-worried", "watch": "chr-xiaoqing_pose-watch",
                 "palm": "chr-xiaoqing_pose-palm", "worried": "chr-xiaoqing_pose-worried"},
    "xiaoyu": {"stand": "chr-xiaoyu_master", "stepback": "chr-xiaoyu_pose-stepback-surprised"},
}
FACE = {"xiaoqing": "face/xiaoqing/face", "xiaoyu": "face/xiaoyu/face", "pinan": "face/pinan/face", "lin": "face/lin/face",
        "chen": "face/chen/face", "ye": "face/ye/face"}
NOTES = {
    "pinan": "周品安（9 歲，小晴同班）。sit_lantern＝P-PA1 坐長椅綁竹燈籠（長椅另外放 props/prop-bench，座面世界高 0.92）；walk_straps＝a3_c003 雙手抓書包背帶低頭快步走（往畫面右）。身上永遠沒有操偶線。",
    "lin": "林雅雯老師。crouch＝P-LIN1 蹲在小宇旁對著手錶說話（a5_c007）；sit＝P-LIN2 坐醫院長椅（a5_c008，長椅用 props/prop-bench）。背面（a4_c001 警衛室窗內）還沒有圖。",
    "chen": "陳伯伯（警衛，導護背心，無任何徽章字樣）。只有站姿；P-CH1 扶阿樂（可選）沒做。導護旗沒做。",
    "ye": "葉護理師（鼠尾草綠護理服，識別證只有手捧愛心圖示）。crouch＝P-YE1 蹲下平視、掌心朝上（a2_c012、a5_c008）。",
    "xiaoqing": "小晴。G5 新增 cross（P-QG1 口訣「不碰」雙手胸前交叉，正面）、palmno（掌心向外說「不要／不試」，朝畫面左）、forehead（手放額前張望，口訣「找大人」，朝畫面右）、walk（行走，往畫面右）。",
    "xiaoyu": "小宇。G5 新增 cross（P-XY1）、palmno（a3_c002 掌心向外拒絕，朝畫面左）、forehead（找大人，朝畫面右）、walk（往畫面右）、dial（P-XY2 舉手錶撥號，朝畫面左；錶面只有電話圖示）。",
}


def engine_feet(a):
    m = a[..., 3] >= 128
    ys, xs = np.nonzero(m)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    low = m[max(0, y1 - 40):y1]
    lx = np.nonzero(low.any(0))[0]
    return [float((lx.min() + lx.max()) / 2), float(y1 - 4)], (x0, y0, x1, y1)


def engine_top(a):
    """standee.ts 的頭頂偵測：高度 12–22% 的不透明欄位加權中心 ±6% 寬，取最高點。"""
    m = a[..., 3] >= 128
    _, (x0, y0, x1, y1) = engine_feet(a)
    H = y1 - y0
    band = m[int(round(y0 + 0.12 * H)):int(round(y0 + 0.22 * H))]
    ys, xs = np.nonzero(band)
    hx = xs.mean() if len(xs) else a.shape[1] / 2
    half = int(round((x1 - x0 + 36) * 0.06))
    best = None
    for x in range(max(0, int(round(hx - half))), min(a.shape[1], int(round(hx + half)))):
        col = np.nonzero(m[:, x])[0]
        if len(col) and (best is None or col[0] < best):
            best = col[0]
    return float(best if best is not None else y0)


def head_metric(a, fb):
    """頭頂到嘴巴中心的垂直距離（頭部大小指標；頭頂＝兩眼中點欄位 ±40 px 內最高的不透明點）。"""
    m = a[..., 3] >= 128
    ex = np.mean([(e[0] + e[2]) / 2 for e in fb["eyes"]])
    my = (fb["mouth"][1] + fb["mouth"][3]) / 2
    top = None
    for x in range(int(ex - 40), int(ex + 40)):
        col = np.nonzero(m[:, x])[0]
        if len(col) and (top is None or col[0] < top):
            top = col[0]
    return float(my - top), float(top)


def main():
    imp = json.loads((OUT / "import.json").read_text())
    boxes = json.loads((OUT / "face_boxes.json").read_text())
    pieces = json.loads((OUT / "blink_check_pieces.json").read_text())
    report = {}
    chars = {}
    fallback = {}
    # 母版
    masters = {}
    for cid in HEIGHT:
        if cid in MASTER:
            path = FIN / MASTER[cid]
            fbm = None
        else:
            rid = next(k for k, v in imp.items() if not k.startswith("_") and v.get("character") == cid and v.get("part") == "master")
            path = ROOT / imp[rid]["final"]
        a = np.array(Image.open(path).convert("RGBA"))
        feet, _ = engine_feet(a)
        top = engine_top(a)
        key = f"{cid}:stand"
        if cid in MASTER:
            # 兒童站姿的退路臉部範圍在 face.ts（主線實量）；這裡只要頭部指標 → 用 G4 FALLBACK_FACES 換算
            ref = L.alpha_ref(a)
            fbm = {"xiaoqing": {"ref": [262, 48], "eyes": [[393, 240, 427, 289], [494, 251, 538, 301]], "mouth": [433, 328, 481, 339]},
                   "xiaoyu": {"ref": [17, 16], "eyes": [[177, 212, 199, 249], [270, 225, 295, 263]], "mouth": [196, 285, 250, 299]}}[cid]
            dx, dy = ref[0] - fbm["ref"][0], ref[1] - fbm["ref"][1]
            fbm = {"eyes": [[b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy] for b in fbm["eyes"]],
                   "mouth": [fbm["mouth"][0] + dx, fbm["mouth"][1] + dy, fbm["mouth"][2] + dx, fbm["mouth"][3] + dy]}
        else:
            fbm = boxes[key]
        hm, _ = head_metric(a, fbm)
        masters[cid] = {"file": str(path.relative_to(ROOT)), "feet": feet, "top": top, "H": feet[1] - top, "head": hm,
                        "units_per_px": HEIGHT[cid] / (feet[1] - top)}
    report["masters"] = masters
    for cid in HEIGHT:
        poses = {}
        for name, img in G4_POSES.get(cid, {}).items():
            poses[name] = {"image": img}
        for rid, rec in imp.items():
            if rid.startswith("_") or rec.get("character") != cid:
                continue
            pose = POSE_NAME[rec["part"]]
            key = f"{cid}:{pose}"
            a = np.array(Image.open(ROOT / rec["final"]).convert("RGBA"))
            img_id = Path(rec["final"]).stem.rsplit("_v", 1)[0]
            feet, _ = engine_feet(a)
            top = engine_top(a)
            hm, htop = head_metric(a, boxes[key])
            M = masters[cid]
            r = hm / M["head"]
            H_eq = M["H"] * r
            H_auto = feet[1] - top
            dev = H_auto / H_eq - 1
            pc = {"image": img_id}
            if pose != "stand":
                pc["face"] = key
            entry = {"image": rec["final"], "head_metric_px": round(hm, 1), "head_ratio_vs_master": round(r, 3), "H_auto_px": round(H_auto, 1),
                     "H_equiv_px": round(H_eq, 1), "auto_vs_equiv": round(dev, 3)}
            if pose.startswith("walk") and pose not in EXPLICIT:
                # 行走：跨步讓腳底到頭頂變短；自動偵測會把整個角色放大。改成「比站姿矮 4%」的等效身高
                H_eq = H_auto / 0.96
                entry["H_equiv_px"] = round(H_eq, 1)
                entry["rule"] = "walk：等效身高＝自動偵測 ÷ 0.96（跨步）"
            if pose != "stand" and (pose in EXPLICIT or pose.startswith("walk")):
                upp = HEIGHT[cid] / H_eq
                if key in SEAT_Y:
                    fy = SEAT_Y[key] + BENCH_SEAT / upp
                    pc["feet"] = [round(feet[0], 1), round(fy, 1)]
                    entry["seat_px"] = SEAT_Y[key]
                    entry["feet_below_soles_world"] = round((fy - feet[1]) * upp, 3)
                else:
                    fy = feet[1]
                pc["headTop"] = round(fy - H_eq, 1)
                entry["explicit"] = True
            else:
                entry["explicit"] = False
            entry["units_per_px"] = round(HEIGHT[cid] / (H_eq if entry["explicit"] else H_auto), 6)
            poses[pose] = pc
            report[key] = entry
            fb = {k: v for k, v in boxes[key].items() if not k.startswith("_")}
            fallback[key] = fb
        cfg = {"rig": "standee", "height": HEIGHT[cid], "defaultPose": "stand", "poses": dict(sorted(poses.items(), key=lambda kv: kv[0] != "stand")),
               "face": FACE[cid], "_note": NOTES[cid]}
        chars[cid] = cfg
    # 新角色站姿的退路臉部 key 用引擎預設「角色:stand」；兒童站姿沿用 face.ts 內建
    out = {
        "format": "antidrug-g5-show-characters/1",
        "version": "v01",
        "date": "2026-10-21",
        "made_by": "review/G5/shared_art/scripts/build_show_characters.py（G5 共用美術代理）",
        "format_note": ("characters[角色 id]＝app/src/stage/cast.ts StandeeCharConfig（poses[名稱].image＝圖像 id，id 規則同 tools/pack.mjs：相對 assets/final 的路徑去掉副檔名與 _vNN）。"
                        "poses[名稱].face＝fallbackFaces 的 key（standee.ts 預設也是「角色:姿勢」）。feet／headTop 只在坐、蹲與自動偵測不準的姿勢才寫（像素，該姿勢圖座標）。"
                        "fallbackFaces＝app/src/stage/face.ts FALLBACK_FACES 同格式（ref＝alpha≥128 不透明範圍左上角），引擎要把它併進 FALLBACK_FACES。"
                        "face＝face JSON 的素材 id：小晴、小宇沿用 G4；品安、林老師、陳伯伯、葉護理師是 G5 新做的原生 FaceConfig（perPose 正式換片，眼睛兩眼同閉、補片不蓋到頭髮與臉緣）。"),
        "world": {"bench_seat_y": BENCH_SEAT, "child_height": "小晴 2.5、小宇 2.42、品安 2.45", "adult_height": "阿樂 3.55（分件）、林老師 3.42、陳伯伯 3.45、葉護理師 3.58",
                  "facing": "姿勢圖的朝向寫在各角色 _note；cue 的 facing:-1 會左右翻面"},
        "characters": chars,
        "fallbackFaces": fallback,
    }
    (FIN / "rig").mkdir(exist_ok=True)
    (FIN / "rig/show_characters.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (OUT / "scale_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    for k, v in report.items():
        if k == "masters":
            for c, m in v.items():
                print("母版", c, "H", round(m["H"], 1), "head", round(m["head"], 1))
            continue
        print(k, "head比", v["head_ratio_vs_master"], "自動/等效", v["auto_vs_equiv"], "明寫" if v["explicit"] else "", v.get("feet_below_soles_world", ""))


if __name__ == "__main__":
    main()
