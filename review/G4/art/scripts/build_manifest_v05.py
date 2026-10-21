"""G4 修正第 1 輪（美術）：更新 assets/final/g4_manifest.json（就地更新；git 有紀錄）。

- version v01 → v05；新增 round1_art 區塊（這一輪的素材與引擎介面變更）
- assets[]：bg-workshop-back 改指 v03；rig/ale_rig 改指 v05（前臂 v05＋head_greet）；新增 tex-string-rope、tex-string-ring、
  ui/ui-speaker_*、小晴三張新姿勢圖（若 assets/final 已有）
- string_render：線寬、紙環直徑、貼圖 id、線下端規則
- characters.xiaoqing：只在三張新姿勢圖與 face_v03.json 都存在時才寫（cast.ts 會用它覆寫 BUILTIN_RIGS['standee:xiaoqing']）
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_manifest_v05.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
FIN = ROOT / "assets/final"
MAN = FIN / "g4_manifest.json"


def img_entry(id_, file, layer, engine_layer, notes, cues, **kw):
    im = Image.open(ROOT / file)
    e = {"id": id_, "file": file, "layer": layer, "engine_layer": engine_layer, "z": kw.pop("z", None), "size_px": list(im.size)}
    e.update(kw)
    e["notes"] = notes
    e["cues"] = cues
    return e


def main():
    m = json.loads(MAN.read_text())
    m["version"] = "v05"
    m["date"] = "2026-10-21"
    assets = {a["id"]: a for a in m["assets"]}
    # 後牆 v03
    b = assets["bg-workshop-back"]
    b["file"] = "assets/final/bg-workshop-back_v03.jpg"
    b["notes"] += " v03（G4 修正第 1 輪）：最下方踢腳板由偏橘 #DFB683 一帶提亮成淺木色 #F0DEC0（review/G4/art/wall_v03.json），開幕景片立起時兒童軀幹帶的背景亮度預估 0.42→0.55；尺寸、錨點不變。"
    # rig v05
    r = assets["rig/ale_rig"]
    r["file"] = "assets/final/rig/ale_rig_v05.json"
    for side in ("l", "r"):
        r["parts"][f"forearm_{side}"]["file"] = f"assets/final/rig/chr-ale_forearm-{side}_v05.png"
    r["parts"]["head_greet"] = {"id": "rig/chr-ale_head-greet", "file": "assets/final/rig/chr-ale_head-greet_v05.png", "outline_id": "rig/chr-ale_head-greet-outline",
                                "note": "替換頭 X2「想打招呼」（微笑＋眉毛上抬），與 head 同樞紐；臉部換片用 FALLBACK_FACES['ale:head']"}
    r["attach"] = "assets/final/rig/ale_attach_v05.json"
    # 新素材
    new = [
        img_entry("tex-string-rope", "assets/final/tex-string-rope_v01.png", "角色", "strings（order 390）",
                  "操偶線紙繩貼圖：u 跨線寬（u=0 畫面左＝受光邊）、v 沿線長四方連續，一週期＝4 線寬。淡灰紙繩身 sRGB≈178＋斜向扭紋＋紙纖維，兩側深灰邊各 12/64。RepeatWrapping＋mipmap。",
                  ["a2_c002", "a2_c004", "a8_c002"]),
        img_entry("tex-string-ring", "assets/final/tex-string-ring_v01.png", "角色", "strings（order 391）",
                  "紙環貼圖（圓環，中間透明）：外深灰細線＋白紙芯邊＋淡灰紙環身＋內深灰細線。正方形平面、直徑 0.103 世界單位、不隨肢體旋轉。",
                  ["a2_c002", "a2_c004", "a8_c002"]),
    ]
    for k, zh in (("narrator", "旁白（未點亮的和紙燈籠徽章）"), ("ale", "阿樂叔叔"), ("xiaoqing", "小晴"), ("xiaoyu", "小宇")):
        new.append(img_entry(f"ui/ui-speaker_{k}", f"assets/final/ui/ui-speaker_{k}_v01.png", "介面", "overlay（字幕說話者小頭像）",
                             f"字幕說話者小頭像：{zh}。128×128 透明圓形徽章（淡色圓盤＋白紙芯邊＋深色細線），顯示約 52–56 px；圖中無字，名牌文字由程式排字。說話者 id 同 app/src/ui/characters.ts。是否採用由主線決定（共用字幕樣式）。",
                             ["全劇字幕"]))
    xq = {}
    imp = ROOT / "review/G4/art/xq_v05_import.json"
    impj = json.loads(imp.read_text()) if imp.exists() else {}
    zh = {"watch": ("注視阿樂（a2_c002 開場；取代正面立正母版）：3/4 側身朝畫面左、放鬆、微笑", ["a2_c002（開場到第一根線落下後）"]),
          "palm": ("「叔叔，小心！」伸出手掌示意：掌心向外、手指併攏、手在胸口高度，不指人；擔心、叫喚的圓嘴；≤1.5 秒後換回 worried", ["a2_c002（a2_c002_02 句）"]),
          "worried": ("擔心站姿：雙手輕握在胸前、3/4 側身朝畫面左；a2_c004 全段用（不指人）", ["a2_c002（喊完之後）", "a2_c004"])}
    for k in ("watch", "palm", "worried"):
        f = FIN / f"chr-xiaoqing_pose-{k}_v05.png"
        if not f.exists():
            continue
        rec = impj.get(k, {})
        e = img_entry(f"chr-xiaoqing_pose-{k}", f"assets/final/chr-xiaoqing_pose-{k}_v05.png", "角色", "actors", zh[k][0], zh[k][1], z=0.4,
                      anchor={"px": rec.get("feet_bottom_px"), "meaning": "腳底中點（最低 6 列範圍中點）", "world": [0.95, 0.0, 0.4]},
                      face_pieces=f"assets/final/face/xiaoqing/face-{k}_v01.json（各姿勢各一份；合併版 face_v03.json 的 perPose.{k}）")
        new.append(e)
        xq[k] = e
    for e in new:
        assets[e["id"]] = e
    # 舊姿勢圖標示
    if "chr-xiaoqing_pose-reach-worried" in assets and xq:
        assets["chr-xiaoqing_pose-reach-worried"]["notes"] = (assets["chr-xiaoqing_pose-reach-worried"].get("notes", "") +
                                                               " G4 修正第 1 輪：導演要求 a2_c004 全段不指人、「叔叔，小心！」改伸手掌 → 這張（伸食指）改由 palm／worried 取代，保留不刪。").strip()
    m["assets"] = list(assets.values())
    m["string_render"] = {
        "rope_texture": "tex-string-rope", "ring_texture": "tex-string-ring",
        "string_width_world": 0.043, "ring_diameter_world": 0.103,
        "px_at_1080p": {"g4_mid": {"線寬": 8.0, "紙環": 19.2}, "錨點近景 dist 12.5": {"線寬": 10.5, "紙環": 25.2}},
        "rope_end": "線的下端停在紙環上緣（扣點往線的方向退 0.4×直徑）；紙環畫在部件與線上面、正對鏡頭、不隨肢體旋轉",
        "attach": "rig/ale_attach（v05）：三個扣點離肢體外形 ≥ 26.5 母版 px，整個紙環在剪影內（review/G4/art/ale_attach_v05_check.json）",
        "preview": ["review/G4/art/string_preview_v01.png", "review/G4/art/ale_a2_poses_v05.png"],
        "contrast": "review/G4/art/string_tex_v01.json（線身對淺牆 ΔL*≈18；深灰邊對牆 ΔL*≈64；線身對工作褲 ΔL*≈32）",
    }
    if xq and (FIN / "face/xiaoqing/face_v03.json").exists():
        m["characters"] = m.get("characters") or {}
        m["characters"]["xiaoqing"] = {
            "rig": "standee", "height": 2.5, "defaultPose": "stand", "face": "face/xiaoqing/face",
            "poses": {"stand": {"image": "chr-xiaoqing_master"}, "reach": {"image": "chr-xiaoqing_pose-reach-worried"},
                      **{k: {"image": f"chr-xiaoqing_pose-{k}"} for k in xq}},
        }
    m["round1_art"] = {
        "date": "2026-10-21",
        "items": {
            "22/34 操偶線紙繩": "tex-string-rope v01＋string_render（引擎換貼圖、STRING_WIDTH 0.066→0.043）",
            "23 紙環": "tex-string-ring v01＋rig/ale_attach v05（扣點內移，紙環整個在剪影內）",
            "27 前臂": "rig/chr-ale_forearm-{l,r} v05（補線稿、紙紋，移除袖口碎片）；id 不變，打包自動換用",
            "17 X2 打招呼臉": "rig/chr-ale_head-greet v05（rig v05 的 head_greet 替換部件）",
            "16 閉眼": "face/<角色>/chr-<角色>_eyes_closed v02（中性閉眼）＋face_v02.json",
            "16/25 小晴姿勢": "chr-xiaoqing_pose-{watch,palm,worried} v05＋face/xiaoqing/face_v03.json（perPose）＋characters.xiaoqing",
            "21 開幕背景亮度": "bg-workshop-back v03（踢腳板提亮）",
            "33 說話者圖示": "ui/ui-speaker_{narrator,ale,xiaoqing,xiaoyu} v01（主線決定是否採用）",
        },
    }
    MAN.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print("manifest", m["version"], "assets", len(m["assets"]), "characters", list((m.get("characters") or {}).keys()))


if __name__ == "__main__":
    main()
