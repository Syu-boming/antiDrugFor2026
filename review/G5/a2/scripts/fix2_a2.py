"""G5 修正第 2 輪：app/cues/show/a2.json（第二幕）。從修正第 1 輪的版本（a2_fix1_base.json＝gen_a2.mjs 的輸出）重建，重跑結果相同。
用法：/opt/anaconda3/bin/python3 review/G5/a2/scripts/fix2_a2.py
寫入方式：先寫暫存檔、讀回驗證 JSON，再搬回（段落檔隨時保持合法）。
依據：review/G5/qa/b1r2_recheck.md、b1r2_regress.md 的第二幕條目；REVIEW.md 主線更正裁定（切場亮度漸變、出題台詞 ≥1.4 秒、
題卡模式折折 {x −4.7, y 0, z 4.15}）。
  - 進出題卡（a2_c005、a2_c007、a2_c009、a2_c011）：一格硬切改成 fade.out 0.6 秒 → 全暗時換鏡位（燈光、折折同時就位）→ fade.in 0.6 秒；
    題卡淡入淡出時鏡頭不動。折折先說「第 N 題」（1.4 秒起）再摺成題卡、DOM 題卡淡入，旁白接著唸題目。
    上一段（a2_c004、a2_c008）沒有折折：出題 cue 的折折一開始就在主線統一位置（g4_mid 鏡位裡剛好在畫面左緣外），漸亮後才看得到；
    點燈回故事時全暗中移到畫面外（下一段沒有折折）。
  - a2_c013 筆記本特寫進出：兩次硬切改成漸暗 0.6 秒 → 切 → 漸亮 0.6 秒（景 a2_window：筆畫在漸亮完成後才開始）；
    葉護理師說完時窗內阿樂叔叔點頭 2 次（幅度 1.6 倍，約 11°，2.2 秒），說話段的點頭幅度加大到 1.3 倍。
  - a2_c012 回到店裡的那一刀（求助站→店內，全畫面亮度 0.413→0.517）：求助站景提亮（assets/final/sets/a2_helpdesk/layout.json），
    不加第二次切黑（第 1 輪導演 6）。
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DST = ROOT / "app/cues/show/a2.json"
d = json.loads((ROOT / "review/G5/a2/scripts/a2_fix1_base.json").read_text())
C = {c["id"]: c for c in d["cues"]}


def A(name, start, target=None, duration=None, ease=None, **params):
    a = {"name": name, "start": start}
    if target:
        a["target"] = target
    if duration is not None:
        a["duration"] = duration
    if ease:
        a["ease"] = ease
    if params:
        a["params"] = params
    return a


def line(c, lid):
    return next(l for l in c["lines"] if l["id"] == lid)


def drop(c, pred):
    c["animation"] = [a for a in c["animation"] if not pred(a)]


QZ = [-4.7, 0, 4.15]           # 題卡模式折折（主線補充裁定，全劇統一）
OFF = [-13.0, 0, 4.15]         # 畫面外（g4_mid 鏡位在 z 4.15 的左緣約 x −5.8）
DIP = {"out": 0.6, "cut": 0.62, "in": 0.6}


def quiz_entry(c, n_line, q_line):
    """出題 cue：從上一段的故事鏡位開始（initialState 鏡位、燈光不動＝接縫不跳），漸暗 → 全暗時換 quiz 鏡位、燈光 0.55、折折就位 → 漸亮"""
    st = c["initialState"]
    st["characters"]["zhezhe"] = {"visible": True, "emotion": "happy", "x": QZ[0], "y": QZ[1], "z": QZ[2]}   # 主線統一位置（g4_mid 鏡位裡在畫面左緣外）
    c["voStart"] = 1.4
    line(c, q_line)["start"] = f"{n_line}.end+1.0"
    c["animation"] = [
        A("fade.out", 0, duration=DIP["out"], to=1),
        A("camera.cut", DIP["cut"], duration=0, to="quiz"),
        A("light.dim", DIP["cut"] - 0.02, duration=0.02, to=0.55),
        A("fade.in", DIP["cut"] + 0.02, duration=DIP["in"]),
        A("zhezhe.hush", DIP["cut"] + 0.08, "zhezhe", 1.4),
        A("zhezhe.emote", 1.0, "zhezhe", emotion="happy"),
        A("zhezhe.fold", f"{n_line}.end+0.05", "zhezhe", 1.2, form="card"),
        A("quiz.show", f"{n_line}.end+0.6", duration=0.6),
        A("zhezhe.fold", f"{n_line}.end+1.35", "zhezhe", 0.7, form="idle"),
    ]
    c["sfx"] = [{"id": "sfx_quiet_fold", "at": 0}, {"id": "sfx_card_in", "at": f"{n_line}.end+0.6", "gain": 0.8}]


def quiz_mode(c):
    """揭答、點燈：折折留在台口左前、idle（不做大動作）"""
    c["initialState"]["characters"]["zhezhe"] = {"visible": True, "emotion": "happy", "x": QZ[0], "y": QZ[1], "z": QZ[2]}
    drop(c, lambda a: a["name"] == "zhezhe.fold")


def lamp_exit(c, l_line, story_cam, story_light):
    """點燈回故事：題卡淡出（鏡頭不動）→ 漸暗 → 全暗時換鏡位、燈光回故事、折折回畫面外 → 漸亮"""
    drop(c, lambda a: a["name"] in ("quiz.hide", "light.restore", "camera.cut", "camera.move", "zhezhe.walkTo"))
    t = f"{l_line}.end"
    c["animation"] += [
        A("quiz.hide", f"{t}+0.30", duration=0.6),
        A("fade.out", f"{t}+0.55", duration=DIP["out"], to=1),
        A("camera.cut", f"{t}+1.17", duration=0, to=story_cam),
        A("light.restore", f"{t}+1.15", duration=0.02) if story_light >= 1 else A("light.dim", f"{t}+1.15", duration=0.02, to=story_light),
        A("zhezhe.glideTo", f"{t}+1.14", "zhezhe", 0.02, pos=OFF),
        A("fade.in", f"{t}+1.19", duration=DIP["in"]),
    ]


# ───────── 題卡 Q2（a2_c005–c007）、Q3（a2_c009–c011）
quiz_entry(C["a2_c005"], "a2_c005_01", "a2_c005_02")
quiz_mode(C["a2_c006"])
quiz_mode(C["a2_c007"])
lamp_exit(C["a2_c007"], "a2_c007_01", "g4_mid", 1.0)
quiz_entry(C["a2_c009"], "a2_c009_01", "a2_c009_02")
quiz_mode(C["a2_c010"])
quiz_mode(C["a2_c011"])
lamp_exit(C["a2_c011"], "a2_c011_01", "g4_mid", 1.0)

# ───────── a2_c013：筆記本特寫進出改漸暗漸亮；點頭看得見
c = C["a2_c013"]
drop(c, lambda a: a["name"] == "camera.cut" or (a["name"] == "puppet.nod" and a["start"] == "a2_c013_03.end-0.6")
     or (a["name"] in ("zhezhe.look", "zhezhe.emote") and str(a["start"]).startswith("a2_c013_03.end+3.")))
for a in c["animation"]:
    if a["name"] == "puppet.nod" and a["start"] == "a2_c013_01+0.2":
        a["params"]["depth"] = 1.3
        a["duration"] = 3.6
    if a["name"] == "puppet.nod" and a["start"] == "a2_c013_02+0.3":
        a["params"]["depth"] = 1.3
t3 = "a2_c013_03.end"
c["animation"] += [
    A("puppet.nod", "a2_c013_03.end-2.3", "ale", 2.2, count=2, depth=1.6),        # 葉護理師說完前，阿樂叔叔點頭兩下（答應不開車）
    A("fade.out", f"{t3}+0.25", duration=0.6, to=1),
    A("camera.cut", f"{t3}+0.87", duration=0, to="a2_win_note"),
    A("fade.in", f"{t3}+0.89", duration=0.6),
    A("fade.out", f"{t3}+3.05", duration=0.6, to=1),
    A("camera.cut", f"{t3}+3.67", duration=0, to="a2_win_kids"),
    A("fade.in", f"{t3}+3.69", duration=0.6),
    A("zhezhe.look", f"{t3}+4.3", "zhezhe", 0.9, yaw=-0.45),
    A("zhezhe.emote", f"{t3}+4.8", "zhezhe", emotion="sad"),
]

# ───────── 總長不得比修正第 1 輪長（進出題卡的漸暗漸亮、題卡在「第 N 題」之後才出現，多出約 1.7 秒）：拿掉空轉
line(C["a2_c001"], "a2_c001_03")["start"] = "a2_c001_02.end+1.2"     # 推近和 _03 重疊（原 +1.5）
line(C["a2_c013"], "a2_c013_04")["start"] = "a2_c013_03.end+4.45"    # 筆記本回到孩子之後（漸亮完成 +4.29；原 +4.7）
C["a2_c012"]["tail"] = 1.2                                             # 葉護理師點頭後停格（原 1.8）
C["a2_c008"]["tail"] = 1.4                                             # 必要旁白二說完後停格（原 1.8）

txt = json.dumps(d, ensure_ascii=False, indent=1)
tmp = DST.with_suffix(".json.tmp")
tmp.write_text(txt + "\n")
json.loads(tmp.read_text())
os.replace(tmp, DST)
print("wrote", DST.relative_to(ROOT))
