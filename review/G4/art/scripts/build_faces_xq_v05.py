"""G4 修正第 1 輪（美術，問題 16、25）：小晴三張新姿勢圖的臉部換片＋合併版 face_v03.json。

輸入：assets/final/chr-xiaoqing_pose-{watch,palm,worried}_v05.png；手量的眼、嘴位置 review/G4/art/xq_v05_face_cfg.json
     （座標＝assets/final 裁切後的姿勢圖像素；格式同 build_faces.CHARS）
輸出：
  assets/final/face/xiaoqing/chr-xiaoqing_<姿勢>-{mouth_*,eyes_*}_v01.png（每姿勢 8 片；閉眼一律中性閉眼）
  assets/final/face/xiaoqing/face-<姿勢>_v01.json（素材代理格式，每姿勢一份，給之後要逐姿勢載入的引擎用）
  assets/final/face/xiaoqing/face_v03.json（引擎原生 FaceConfig 格式，打包 id 仍是 face/xiaoqing/face）：
     - headLayer／poseImage：沿用 reach 姿勢的頭層（face_v02.json）
     - perPose.reach：reach 的換片（頭層座標，閉眼 v02）；perPose.watch／palm／worried：新姿勢的換片（姿勢圖座標）
     - 最上層 mouth／eyes 是「沒有圖」的空槽（shapes 指向不存在的 id），讓沒有換片的 stand 姿勢照舊用退路換片
       （app/src/stage/face.ts：perPose 沒有該姿勢時退回最上層槽；最上層找不到圖 → mode=fallback）
     - 不寫 restMouth：各姿勢原圖的嘴（watch 微笑、palm 圓嘴、worried 擔心）就是不說話時的樣子
  review/G4/art/face_sheet_xq_v05.png
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_faces_xq_v05.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_faces as BF  # noqa: E402

ROOT = BF.ROOT
FIN = ROOT / "assets/final"
FD = FIN / "face/xiaoqing"


def slot(face, kind, coord_key="anchor_px"):
    g = face["groups"][kind]
    ax, ay = g[coord_key]
    w, h = g["size"]
    shapes = {k.replace(f"{kind}_", ""): v["image_id"] for k, v in face["pieces"].items() if v["group"] == kind}
    return {"anchor": [ax + w / 2, ay + h / 2], "size": [w, h], "z": 2 if kind == "mouth" else 1, "shapes": shapes}


def main():
    cfgs = json.loads((ROOT / "review/G4/art/xq_v05_face_cfg.json").read_text())
    faces = {}
    BF.WRITE = None
    BF.PIECE_VER = {}
    BF.FACE_VERSION = "v01"
    for k, c in cfgs.items():
        f = FIN / f"chr-xiaoqing_pose-{k}_v05.png"
        if not f.exists():
            continue
        cfg = dict(c)
        cfg["head"] = f
        cfg["zh"] = "小晴"
        cfg["head_note"] = f"頭部圖＝整張姿勢圖 chr-xiaoqing_pose-{k}（沒有拆頭層；座標以 assets/final 裁切後的圖為準）"
        for key in ("mouth_c",):
            cfg[key] = tuple(cfg[key])
        for key in ("mouth_box", "eyes_box", "mouth_search"):
            if cfg.get(key):
                cfg[key] = tuple(cfg[key])
        cfg["eyes"] = [tuple(e) for e in cfg["eyes"]]
        cfg["eye_boxes"] = [tuple(e) for e in cfg["eye_boxes"]]
        if cfg.get("eye_ellipses"):
            cfg["eye_ellipses"] = [tuple(e) for e in cfg["eye_ellipses"]]
        cfg.setdefault("closed_curve", 0.10)
        cfg.setdefault("closed_v", 0.52)
        BF.PREFIX = f"{k}-"
        BF.FACE_JSON = f"face-{k}_v01.json"
        face, head = BF.build("xiaoqing", cfg)
        face["pose"] = k
        face["rest_mouth"] = c.get("rest_mouth_label", face.get("rest_mouth"))
        (FD / BF.FACE_JSON).write_text(json.dumps(face, ensure_ascii=False, indent=1))
        faces[k] = (face, head)
        BF.CHARS[f"xiaoqing-{k}"] = cfg
        print(k, {p: v["changed_px"] for p, v in face["pieces"].items()})
    BF.PREFIX = ""
    # 合併版（原生 FaceConfig）
    v2 = json.loads((FD / "face_v02.json").read_text())
    hi, pi = v2["head_image"], v2["pose_image"]
    none = lambda shapes: {s: f"none/xiaoqing-{s}" for s in shapes}  # noqa: E731
    native = {
        "character": "xiaoqing",
        "format_note": "引擎原生 FaceConfig（app/src/stage/face.ts）。perPose 依立牌姿勢名稱（cast.ts／g4_manifest characters.xiaoqing.poses）；"
                       "最上層 mouth／eyes 是空槽（stand 姿勢沒有正式換片，照舊用退路換片）。各姿勢的素材代理格式見 face-<姿勢>_v01.json、reach 見 face_v02.json。",
        "version": "v03",
        "headLayer": {"image": hi["image_id"], "offset": hi["offset_in_pose_image_px"], "pivot": hi["pivot_px"], "size": hi["size"]},
        "poseImage": pi["image_id"],
        "mouth": {"anchor": [0, 0], "size": [1, 1], "z": 2, "shapes": none(["closed", "half", "open", "round", "worried", "smile"])},
        "eyes": {"anchor": [0, 0], "size": [1, 1], "z": 1, "shapes": none(["open", "half", "closed"])},
        "perPose": {"reach": {"mouth": slot(v2, "mouth"), "eyes": slot(v2, "eyes")}},
        "lipsync_map": v2["lipsync_map"],
        "swap_rule": v2["swap_rule"],
    }
    for k, (face, _) in faces.items():
        native["perPose"][k] = {"mouth": slot(face, "mouth"), "eyes": slot(face, "eyes")}
    (FD / "face_v03.json").write_text(json.dumps(native, ensure_ascii=False, indent=1))
    BF.SHEET = ROOT / "review/G4/art/face_sheet_xq_v05.png"
    sheet_faces = {}
    for k, (face, head) in faces.items():
        sheet_faces[f"xiaoqing-{k}"] = (dict(face, zh=f"小晴 {k}"), head)
    BF.face_sheet(sheet_faces)
    print("face_v03 perPose:", list(native["perPose"]))


if __name__ == "__main__":
    main()
