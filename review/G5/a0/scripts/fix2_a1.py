"""G5 修正第 2 輪：app/cues/show/a1.json（第一幕）。從修正第 1 輪的版本（a1_fix1_base.json）重建，重跑結果相同。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/fix2_a1.py
寫入方式：先寫暫存檔、讀回驗證 JSON，再搬回（段落檔隨時保持合法）。
依據：review/G5/qa/b1r2_recheck.md、b1r2_regress.md 的第一幕條目；REVIEW.md 主線更正裁定（切場亮度漸變、出題台詞 ≥1.4 秒、
題卡模式折折 {x −4.7, y 0, z 4.15}）。
  - 嚴重 S1：a1_c008 小宇轉身改成 0.7 秒的翻面（原 0.24 秒、3 格壓扁）；三人都往左站 0.24 單位（約 60 px），小宇不再疊在窗框的高對比邊上。
  - 進出題卡：一格硬切改成 fade.out 0.6 秒 → 全暗時換鏡位（燈光同時設好）→ fade.in 0.6 秒；鏡頭在題卡淡入淡出時不動。
  - a1_c004 結尾停在品安中景（她轉頭看柱子 0.9 秒再轉回），拿掉切回跟拍孩子那一刀（亮度差 25%）。
  - a1_c008 包裝紙特寫進出：切之前把街景燈光壓到 0.8（0.9 秒、鏡頭不動），切到特寫時燈光回到 1，切回街景時 0.86 再 1.0 秒漸回，
    兩邊全畫面亮度差 < 15%。
  - a1_c001 第一句提前到 3.7 秒（孩子邊走邊說）；a1_c002 小宇被吸引往左一步（0.4 單位＋前傾 0.07）。
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DST = ROOT / "app/cues/show/a1.json"
d = json.loads((ROOT / "review/G5/a0/scripts/a1_fix1_base.json").read_text())
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


QZ = {"x": -4.7, "y": 0, "z": 4.15}           # 題卡模式折折（主線補充裁定，全劇統一）
DIP = {"out": 0.6, "cut": 0.62, "in": 0.6}    # 進出題卡的漸暗→換鏡位→漸亮（引擎驗證：fade 至少 0.6 秒）


def quiz_entry(c, story_cam, zz_story, n_line, q_line):
    """出題 cue：從上一個 cue 的故事鏡位開始（接縫不跳），漸暗 0.6 秒 → 全暗時換到 quiz 鏡位、燈光 0.55、折折移到台口左前 → 漸亮 0.6 秒；
    折折先說「第 N 題」（1.4 秒起，不壓在摺紙音效上）→ 摺成題卡、DOM 題卡淡入 → 旁白唸題目。"""
    st = c["initialState"]
    st["stage"]["camera"] = story_cam
    st["stage"]["light"] = 1
    st["characters"]["zhezhe"] = {"visible": True, "emotion": "happy", **zz_story}
    c["voStart"] = 1.4
    line(c, q_line)["start"] = f"{n_line}.end+1.0"
    c["animation"] = [
        A("fade.out", 0, duration=DIP["out"], to=1),
        A("camera.cut", DIP["cut"], duration=0, to="quiz"),
        A("light.dim", DIP["cut"] - 0.02, duration=0.02, to=0.55),
        A("zhezhe.glideTo", DIP["cut"] - 0.03, "zhezhe", 0.02, pos=[QZ["x"], QZ["y"], QZ["z"]]),
        A("zhezhe.fold", DIP["cut"] - 0.02, "zhezhe", 0.02, form="idle"),
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
    c["initialState"]["characters"]["zhezhe"] = {"visible": True, "emotion": "happy", **QZ}
    drop(c, lambda a: a["name"] == "zhezhe.fold" and a["start"] == -1.2)


def lamp_exit(c, l_line, story_cam, light_story=1.0, zz_story=None):
    """點燈 cue 回故事：題卡淡出（鏡頭不動）→ 漸暗 0.6 秒 → 全暗時換鏡位、燈光回故事 → 漸亮 0.6 秒"""
    drop(c, lambda a: a["name"] in ("quiz.hide", "light.restore", "camera.cut", "camera.move"))
    t = f"{l_line}.end"
    c["animation"] += [
        A("quiz.hide", f"{t}+0.30", duration=0.6),
        A("fade.out", f"{t}+0.55", duration=DIP["out"], to=1),
        A("camera.cut", f"{t}+1.17", duration=0, to=story_cam),
        A("light.restore", f"{t}+1.15", duration=0.02) if light_story >= 1 else A("light.dim", f"{t}+1.15", duration=0.02, to=light_story),
        A("fade.in", f"{t}+1.19", duration=DIP["in"]),
    ]
    if zz_story:
        c["animation"].append(A("zhezhe.glideTo", f"{t}+1.14", "zhezhe", 0.02, pos=zz_story))


# ───────── a1_c001：第一句提前到 3.7 秒（孩子在大全景裡邊走邊說）；說完才切長椅中景
c = C["a1_c001"]
for a in c["animation"]:
    if a["name"] == "puppet.move" and a.get("target") == "xiaoqing":
        a["start"] = 0.2
    if a["name"] == "puppet.move" and a.get("target") == "xiaoyu":
        a["start"] = 0.55
    if a["name"] == "puppet.pose" and a.get("target") == "xiaoqing" and a["params"]["pose"] == "stand":
        a["start"] = 3.8
    if a["name"] == "puppet.pose" and a.get("target") == "xiaoyu" and a["params"]["pose"] == "standwatch":
        a["start"] = 4.3
    if a["name"] == "zhezhe.walkTo" and a["start"] == 2.0:
        a["start"] = 1.6
    if a["name"] == "camera.cut" and a["start"] == 5.05:
        a["start"] = "a1_c001_01.end+0.12"
c["voStart"] = 3.7
c["sfx"] = [{**s, "at": 0.6} if s["id"] == "sfx_footsteps" and s["at"] == 0.8 else s for s in c["sfx"]]

# ───────── a1_c002：小宇「哇……好亮」時被吸引往左一步（0.4 單位、1.0 秒）＋身體前傾 0.07
c = C["a1_c002"]
drop(c, lambda a: a.get("target") == "xiaoyu" and a["name"] in ("puppet.move", "puppet.lean"))
c["animation"] += [
    A("puppet.move", "a1_c002_03-0.35", "xiaoyu", 1.0, "inOut", dx=-0.4),
    A("puppet.lean", "a1_c002_03-0.30", "xiaoyu", 0.9, to=0.07),
]
# ───────── a1_c003：開頭退回原位（0.9 秒）
c = C["a1_c003"]
c["initialState"]["characters"]["xiaoyu"]["x"] = round(0.55 - 0.4, 2)
c["animation"].insert(0, A("puppet.lean", -0.6, "xiaoyu", 0.02, to=0.07))     # 接 a1_c002 結尾的前傾（起始狀態沒有 lean 欄位）
for a in c["animation"]:
    if a["name"] == "puppet.move" and a.get("target") == "xiaoyu":
        a["params"]["dx"] = 0.4
        a["duration"] = 0.9
        a["ease"] = "inOut"

# ───────── a1_c004：結尾停在品安中景：她說完「我把燈籠收好就來」→ 轉頭看左邊的柱子（翻面 0.5 秒）、停 0.9 秒 → 轉回燈籠（0.5 秒）
c = C["a1_c004"]
drop(c, lambda a: (a["name"] == "camera.cut" and a["params"].get("to") == "a1_follow2")
     or (a.get("target") == "pinan" and a["name"] in ("puppet.pose", "puppet.tilt")))
c["animation"] += [
    A("puppet.pose", "a1_c004_05-0.20", "pinan", 0.24, pose="sit_lantern_back"),   # 小晴叫她：轉向右邊的孩子
    # 切到品安中景（+0.15）之後 1 秒才轉頭（細格光敏：切換與翻面不擠在同一秒）
    A("puppet.pose", "a1_c004_06.end+1.20", "pinan", 0.5, pose="sit_lantern"),     # 轉頭看左邊的柱子
    A("puppet.tilt", "a1_c004_06.end+1.40", "pinan", 0.6, to=0.05),
    A("puppet.pose", "a1_c004_06.end+2.60", "pinan", 0.5, pose="sit_lantern_back"), # 停 0.9 秒後轉回來（燈籠）
    A("puppet.tilt", "a1_c004_06.end+2.65", "pinan", 0.5, to=0.0),
]

# ───────── a1_c005–c007 題卡 Q1
end4 = {"xiaoqing": 1.2, "xiaoyu": 2.35}
quiz_entry(C["a1_c005"], "a1_pinan", {"x": 1.75, "y": 0.0, "z": 1.05}, "a1_c005_01", "a1_c005_02")
for cid in ("a1_c005", "a1_c006", "a1_c007"):
    C[cid]["initialState"]["characters"]["pinan"]["pose"] = "sit_lantern_back"
quiz_mode(C["a1_c006"])
quiz_mode(C["a1_c007"])
lamp_exit(C["a1_c007"], "a1_c007_01", "a1_follow2", zz_story=[1.75, 0.0, 1.05])

# ───────── a1_c008：S1 小宇轉身；三人往左站 0.24；包裝紙特寫進出的亮度
c = C["a1_c008"]
SHIFT = 0.24
for a in c["animation"]:
    n, tg = a["name"], a.get("target")
    if n == "puppet.move" and a["start"] == "a1_c008_02.end+0.50" and tg in ("xiaoqing", "xiaoyu"):
        a["params"]["dx"] = round(2.2 - SHIFT, 2)
    if n == "zhezhe.glideTo" and a["start"] == "a1_c008_02.end+0.60":
        a["params"]["pos"] = [round(2.35 - SHIFT, 2), 0.0, 1.15]
    if n == "puppet.pose" and tg == "xiaoyu" and a["params"]["pose"] == "standwatch":
        a["start"] = "a1_c008_02.end+5.60"
        a["duration"] = 0.7
    if n == "camera.cut" and a["start"] == 4.6:
        a["start"] = 4.6
# 包裝紙特寫進出：街景先壓暗、特寫恢復 1；切回街景時從 0.86 慢慢回到 1（鏡頭不動時才變）
c["animation"] += [
    A("light.dim", 3.6, duration=0.9, to=0.8),
    A("light.restore", 4.58, duration=0.02),
    A("light.dim", "a1_c008_02-0.32", duration=0.02, to=0.86),
    A("light.restore", "a1_c008_02+0.40", duration=1.0),
]

txt = json.dumps(d, ensure_ascii=False, indent=1)
tmp = DST.with_suffix(".json.tmp")
tmp.write_text(txt + "\n")
json.loads(tmp.read_text())
os.replace(tmp, DST)
print("wrote", DST.relative_to(ROOT))
