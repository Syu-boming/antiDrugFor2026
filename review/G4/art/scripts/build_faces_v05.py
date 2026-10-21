"""G4 修正第 1 輪（美術，問題 16）：中性閉眼換片（取代向上拱的「笑眼」閉眼）。

- 小晴、小宇、阿樂的 eyes_closed 改成往下彎的中性閉眼線（眼皮蓋下來），其餘換片不變。
- 只輸出 assets/final/face/<角色>/chr-<角色>_eyes_closed_v02.png 與 face_v02.json（打包 id 仍是 face/<角色>/face，
  tools/pack.mjs 取最新版本）；v01 檔案不覆寫。
- 檢查圖 review/G4/art/face_sheet_v05.png。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_faces_v05.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_faces as BF  # noqa: E402

ROOT = BF.ROOT
NEUTRAL = {"closed_curve": 0.10, "closed_v": 0.52}


def main():
    BF.PIECE_VER = {"eyes_closed": "v02"}
    BF.WRITE = {"eyes_closed"}
    BF.FACE_JSON = "face_v02.json"
    BF.FACE_VERSION = "v02"
    BF.SHEET = ROOT / "review/G4/art/face_sheet_v05.png"
    crop = json.loads((ROOT / "review/G4/art/kids_crop.json").read_text())
    for name in ("xiaoqing", "xiaoyu"):
        BF.CHARS[name] = BF.shift_cfg(BF.CHARS[name], crop[BF.CHARS[name]["head"].name]["offset_from_source"])
    faces = {}
    for name, cfg in BF.CHARS.items():
        cfg.update(NEUTRAL)
        face, head = BF.build(name, cfg)
        face["change_log"] = "v02（G4 修正第 1 輪）：eyes_closed 改中性閉眼（往下彎的眼皮線），取代 v01 的笑眼弧線；其餘換片沿用 v01。"
        (BF.FACE_DIR / name / BF.FACE_JSON).write_text(json.dumps(face, ensure_ascii=False, indent=1))
        faces[name] = (face, head)
        if name in ("xiaoqing", "xiaoyu"):
            BF.rebase_to_head_layer(name, face)
        print(name, face["pieces"]["eyes_closed"]["file"], face["pieces"]["eyes_closed"]["changed_px"])
    BF.face_sheet(faces)


if __name__ == "__main__":
    main()
