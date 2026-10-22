"""G5 修正第 1 輪：app/cues/show/a1.json（第一幕）。從 c2e8868 的版本重建，重跑結果相同。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/fix1_a1.py
寫入方式：先寫暫存檔、讀回驗證 JSON，再搬回（段落檔隨時保持合法）。
細格光敏（fine_32x18 每秒 ≤3）的做法：
  - 中景裡走路的腿（腿－空隙－腿）掃過 60 px 的格子會連續 4 次明暗轉折 → 孩子走進／走出改成①在大全景裡走（人小）或②慢慢平移（≤0.45 單位／秒）
    或③鏡頭跟著平移（人在畫面上幾乎不動）；平移用 puppet.move（不加走路的上下彈跳，彈跳每秒 3.2 下）。
  - 大幅縮放（推近、後拉）改硬切：a1_c001 大全景→長椅、紙青蛙近景進出、題卡進出。
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DST = ROOT / "app/cues/show/a1.json"
src = subprocess.run(["git", "show", "c2e8868:app/cues/show/a1.json"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
d = json.loads(src)
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


# 題卡模式折折的站位：第 12 節建議 x≈−4.7、z≈3.4，但那裡被 DOM 題卡（1080p 下緣約 y 915）整個擋住；
# 依實際鏡位微調到台口前緣（z 8.6）：腳約 y 1037、頭頂約 y 925，整隻在題卡下方看得到，不擋題卡（題卡模式字幕條收起）
QZ = {"x": -4.7, "y": 0, "z": 9.2}
QZ_SCALE = 1.4      # 題卡模式折折放大 1.4 倍（約畫面高 15%，頭頂只碰到題卡下緣）

# ───────── a1_c001 廣場上的品安：孩子在大全景裡走進來（人小），到定點後硬切長椅中景；第一句提前到 4.2 秒；
#           紙青蛙近景進出改硬切（大幅縮放）
c = C["a1_c001"]
ini = c["initialState"]["characters"]
# 孩子一開場（漸亮）就在大全景裡，等速慢慢走向長椅（走路姿勢的腿－空隙－腿掃過格子要超過 1 秒，細格光敏），兩人走過同一段路錯開 ≥1 秒
WALK = {"xiaoqing": (2.05, 0.4, 3.6), "xiaoyu": (2.35, 0.9, 3.6)}      # 走的距離、開始、時長（等速）
ini["xiaoqing"]["x"] = round(-0.55 + WALK["xiaoqing"][0], 2)
ini["xiaoyu"]["x"] = round(0.55 + WALK["xiaoyu"][0], 2)
anims = []
for a in c["animation"]:
    n, st = a["name"], a["start"]
    if n == "camera.move" and a["params"]["to"] == "a1_bench" and st == 0.9:
        anims.append(A("camera.cut", 5.05, duration=0, to="a1_bench"))
        continue
    if n == "puppet.enter":
        dist, st2, du = WALK[a["target"]]
        anims.append(A("puppet.move", st2, a["target"], du, "linear", dx=-dist))
        continue
    if n == "puppet.pose" and a["params"]["pose"] == "stand" and a["target"] == "xiaoqing":
        a = {**a, "start": 4.0}
    if n == "puppet.pose" and a["params"]["pose"] == "standwatch" and a["target"] == "xiaoyu":
        a = {**a, "start": 4.55}
    if n == "zhezhe.walkTo" and st == 7.4:
        a = {**a, "start": 2.0, "duration": 2.4}
    if n == "camera.move" and a["params"]["to"] == "a1_lantern":
        anims.append(A("camera.cut", "a1_c001_04.end+2.25", duration=0, to="a1_lantern"))
        continue
    if n == "camera.move" and a["params"]["to"] == "a1_bench":
        anims.append(A("camera.cut", "a1_c001_05.end+0.95", duration=0, to="a1_bench"))
        continue
    anims.append(a)
c["animation"] = anims
c["voStart"] = 5.1
c["tail"] = 2.4
c["sfx"] = [{"id": "sfx_crowd_far", "at": 0.3, "gain": 0.22}, {"id": "sfx_footsteps", "at": 0.8, "gain": 0.35}] + \
           [s for s in c["sfx"] if s["id"] != "sfx_crowd_far" and not (s["id"] == "sfx_footsteps" and s["at"] == 3.8)]

# ───────── a1_c002 閃亮的小盒子：小宇說「哇……好亮」時往左一步、身體前傾、驚喜眼睛；品安探頭（背景冷色降彩由景做）
c = C["a1_c002"]
anims = []
for a in c["animation"]:
    if a["name"] == "puppet.move" and a["target"] == "xiaoyu":
        continue
    if a["name"] == "puppet.lean" and a["target"] == "pinan":
        continue
    anims.append(a)
anims += [
    A("puppet.face", "a1_c002_03-0.25", "xiaoyu", emotion="surprised"),
    A("puppet.move", "a1_c002_03-0.10", "xiaoyu", 0.8, dx=-0.25),
    A("puppet.lean", "a1_c002_03-0.10", "xiaoyu", 0.8, to=0.04),
    A("puppet.lean", "a1_c002_03+0.10", "pinan", 0.9, to=-0.03),
]
c["animation"] = anims

# ───────── a1_c003 找找看 1：「等一下，我想一想」退回原位、推眼鏡；特寫卡片放左上（景），不蓋住品安
c = C["a1_c003"]
ini = c["initialState"]["characters"]
ini["xiaoyu"]["x"] = 0.3
# 退回原位（開口前）→ 說話中推眼鏡（翻面）→ 說完後放下；鏡頭推近晚一點才開始（三個動作不擠在同一秒，細格光敏）
anims = [a for a in c["animation"] if not (a["name"] == "puppet.tilt" and a["target"] == "xiaoyu")
         and not (a["name"] == "camera.move")]
anims += [
    A("puppet.lean", 0.1, "xiaoyu", 0.7, to=0.0),
    A("puppet.move", 0.1, "xiaoyu", 0.8, dx=0.25),
    A("puppet.pose", "a1_c003_01+0.75", "xiaoyu", 0.24, pose="glasses"),
    A("puppet.pose", "a1_c003_01.end+0.60", "xiaoyu", 0.24, pose="standwatch"),
    A("camera.move", "a1_c003_01.end+0.10", duration=2.6, to="a1_two"),
]
c["animation"] = anims

# ───────── a1_c004 不用，我們不要：孩子離開改成慢慢平移（不加彈跳）；品安說完後鏡頭先停 1.6 秒在品安中景（左緣看得到紅磚柱子），
#           她回頭看柱子（a6 秘密的伏筆），再切到跟拍孩子
c = C["a1_c004"]
ini = c["initialState"]["characters"]
ini["xiaoyu"]["x"] = 0.55
anims = []
for a in c["animation"]:
    n = a["name"]
    if n == "puppet.exit":
        to = a["params"]["to"]
        if a["target"] == "xiaoyu" and to == 1.17:
            to = 0.75
        du = a["duration"] if a["target"] == "xiaoyu" else max(a["duration"], 2.4)
        anims.append(A("puppet.move", a["start"], a["target"], du, "linear", dx=to))
        continue
    if n == "camera.move" and a["params"]["to"] == "a1_follow":
        continue          # 鏡頭不跟拍（平移時背景與長椅掃過格子）：孩子在 a1_hand 畫面裡往右走，品安、柱子留在左邊
    if n == "puppet.move" or n == "puppet.exit":
        pass
    if n == "camera.move" and a["params"]["to"] == "a1_follow2":
        anims.append(A("camera.cut", "a1_c004_06.end+0.15", duration=0, to="a1_pinan"))
        anims.append(A("camera.cut", "a1_c004_06.end+2.70", duration=0, to="a1_follow2"))
        continue
    if n == "zhezhe.hopTo" and str(a["start"]).startswith("a1_c004_04.end"):
        # 等孩子走完第一段才從長椅跳下來，放慢、跳低一點（細格光敏：和孩子起步、換姿勢擠在同一秒）
        a = {**a, "start": "a1_c004_04.end+3.50", "duration": 1.4, "params": {**a["params"], "height": 0.2}}
    if n == "zhezhe.walkTo" and a["start"] == "a1_c004_04.end+1.35":
        anims.append(A("zhezhe.glideTo", "a1_c004_04.end+5.00", "zhezhe", 2.0, pos=a["params"]["pos"]))   # 平移，不跳步
        continue
    # 小晴第一段往右走用站姿平移（不翻成走路姿勢：翻面＋起步擠在同一秒，細格光敏），走完叫品安時也就不必再翻回站姿
    if n == "puppet.pose" and a["target"] == "xiaoqing" and a["start"] in ("a1_c004_04.end+0.75", "a1_c004_05-0.50"):
        continue
    anims.append(a)
for a in anims:
    if a["name"] == "puppet.pose" and a["target"] == "pinan":
        a["params"]["pose"] = "sit_lantern"           # 說完後轉回去：臉朝左邊的柱子（偷偷回頭看）
        a["start"] = "a1_c004_06.end+1.30"
anims += [
    A("puppet.pose", "a1_c004_05-0.20", "pinan", 0.24, pose="sit_lantern_back"),   # 小晴叫她：轉向右邊的孩子
    A("puppet.tilt", "a1_c004_06.end+1.85", "pinan", 0.6, to=0.05),
]
c["animation"] = anims
c["tail"] = 3.4

# ───────── a1_c005–c007 題卡 Q1：硬切到題卡鏡位（大幅後拉改硬切）；折折上台站在台口左前（第 12 節），出題時摺成題卡、
#           唸完選項摺回貓；揭答、點燈留在同一位置不做大動作；點燈後硬切回故事
c = C["a1_c005"]
c["initialState"]["stage"]["camera"] = "quiz"
c["initialState"]["characters"]["zhezhe"] = {"visible": True, "emotion": "happy", **QZ}
c["animation"] = [
    A("zhezhe.hush", -0.55, "zhezhe", 1.4),
    A("light.dim", 0, duration=1.2, to=0.55),
    A("zhezhe.fold", -1.2, "zhezhe", 0.3, form="idle", scale=QZ_SCALE),
    A("zhezhe.fold", 0.1, "zhezhe", 1.3, form="card", scale=QZ_SCALE),
    A("quiz.show", 0.7, duration=0.6),
    A("zhezhe.fold", "a1_c005_05.end+0.00", "zhezhe", 1.0, form="idle", scale=QZ_SCALE),
]
for cid in ("a1_c005", "a1_c006", "a1_c007"):
    C[cid]["initialState"]["characters"]["pinan"]["pose"] = "sit_lantern"      # 品安看著柱子那邊（a1_c004 結尾回頭看柱子）
for cid in ("a1_c006", "a1_c007"):
    C[cid]["initialState"]["characters"]["zhezhe"] = {"visible": True, "emotion": "happy", **QZ}
    C[cid]["animation"].insert(0, A("zhezhe.fold", -1.2, "zhezhe", 0.3, form="idle", scale=QZ_SCALE))   # 預捲：一開始就是放大的貓
c = C["a1_c007"]
anims = []
for a in c["animation"]:
    if a["name"] == "camera.move":
        anims.append(A("camera.cut", "a1_c007_01.end+0.45", duration=0, to="a1_follow2"))
        continue
    anims.append(a)
anims.append(A("zhezhe.emote", "a1_c007_01-0.10", "zhezhe", emotion="proud"))
c["animation"] = anims

# ───────── a1_c008 一團線（懸念）
c = C["a1_c008"]
c["initialState"]["stage"]["camera"] = "a1_street2"
c["initialState"]["characters"] = {
    "xiaoqing": {"visible": True, "emotion": "smile", "pose": "walk", "x": -0.35, "z": 0.1, "facing": 1},
    "xiaoyu": {"visible": True, "emotion": "smile", "pose": "walk", "x": 0.6, "z": -0.25, "facing": 1},
    "zhezhe": {"visible": True, "emotion": "happy", "x": -1.9, "y": 0, "z": 1.2},
}
c["animation"] = [
    # 往右走（慢慢平移）；包裝紙 1.6 秒起被風從左邊吹進來，3.6 秒停在他們身後左下方（景：x −0.5、z 1.4，離小晴一個身寬以上）
    A("puppet.move", 0.3, "xiaoqing", 1.9, dx=0.8),
    A("puppet.move", 0.35, "xiaoyu", 1.9, dx=0.8),
    A("zhezhe.walkTo", 0.4, "zhezhe", 1.8, pos=[-1.3, 0.0, 1.2]),
    A("puppet.pose", 3.8, "xiaoqing", 0.24, pose="forehead_l"),      # 包裝紙落地：回頭看身後的包裝紙（_l／_m＝朝左）
    A("puppet.pose", 4.0, "xiaoyu", 0.24, pose="standwatch_m"),
    A("puppet.face", 4.25, "xiaoqing", emotion="surprised"),
    A("puppet.face", 4.35, "xiaoyu", emotion="surprised"),
    A("zhezhe.look", 3.9, "zhezhe", 0.5, yaw=0.45),
    A("zhezhe.emote", 4.1, "zhezhe", emotion="curious"),
    # 包裝紙特寫：中心是紙邊裡那團灰色紙線，折折在左側三分之一
    A("camera.cut", 4.6, duration=0, to="a1_wrapper0"),
    A("camera.move", 4.7, duration=3.8, to="a1_wrapper"),
    A("zhezhe.twitch", "a1_c008_01+0.20", "zhezhe", side="both"),
    A("zhezhe.emote", "a1_c008_01+1.80", "zhezhe", emotion="worried"),
    # 「不要碰。」：切回街上；兩人各往後（遠離包裝紙＝往右）退半步
    A("camera.cut", "a1_c008_02-0.30", duration=0, to="a1_street2"),
    A("puppet.pose", "a1_c008_02-0.35", "xiaoqing", 0.24, pose="cross"),
    A("puppet.face", "a1_c008_02-0.10", "xiaoqing", emotion="neutral"),
    A("puppet.move", "a1_c008_02+0.60", "xiaoqing", 0.6, dx=0.15),
    A("puppet.move", "a1_c008_02+0.70", "xiaoyu", 0.6, dx=0.15),
    A("puppet.face", "a1_c008_02+0.30", "xiaoyu", emotion="worried"),
    # 離開包裝紙、走到燈籠店窗下：鏡頭跟著一起平移（人在畫面上幾乎不動），停在窗前中景，窗戶整個露出來
    A("puppet.pose", "a1_c008_02.end+0.20", "xiaoyu", 0.24, pose="walk"),
    A("puppet.pose", "a1_c008_02.end+0.30", "xiaoqing", 0.24, pose="walk"),
    A("puppet.move", "a1_c008_02.end+0.50", "xiaoqing", 4.4, dx=2.2),
    A("puppet.move", "a1_c008_02.end+0.50", "xiaoyu", 4.4, dx=2.2),
    A("camera.move", "a1_c008_02.end+0.50", duration=4.4, to="a1_window"),
    A("zhezhe.glideTo", "a1_c008_02.end+0.60", "zhezhe", 4.4, pos=[2.35, 0.0, 1.15]),     # 跟著平移（不跳步，細格光敏）
    A("zhezhe.look", "a1_c008_02.end+0.60", "zhezhe", 0.5, yaw=0.0),
    A("puppet.pose", "a1_c008_02.end+5.50", "xiaoyu", 0.24, pose="standwatch"),
    A("puppet.pose", "a1_c008_02.end+6.20", "xiaoqing", 0.24, pose="forehead"),
    # 窗內剪影（景 square_a1：窗光在走到窗下時 1.2 秒漸亮；02.end＋5.6 起 舉起 0.8 秒 → 被帶往左歪 0.5 秒 → 竹條落下 1 秒 → 窗光再亮一點）
    A("zhezhe.look", "a1_c008_02.end+6.50", "zhezhe", 0.5, yaw=0.35),
    A("zhezhe.twitch", "a1_c008_02.end+8.00", "zhezhe", side="both"),
    A("zhezhe.emote", "a1_c008_02.end+8.10", "zhezhe", emotion="worried"),
    A("puppet.face", "a1_c008_02.end+8.10", "xiaoyu", emotion="worried"),
    A("puppet.face", "a1_c008_02.end+8.25", "xiaoqing", emotion="worried"),
    A("light.dim", "a1_c008_03.end+0.40", duration=3.2, to=0.8),
]
line(c, "a1_c008_03")["start"] = "a1_c008_02.end+8.50"
c["voStart"] = 5.2
c["tail"] = 3.2
c["sfx"] = [
    {"id": "sfx_footsteps", "at": 0.5, "gain": 0.35},
    {"id": "sfx_plane_whoosh", "at": 2.0, "gain": 0.45},
    {"id": "sfx_paper_rustle", "at": 3.9, "gain": 0.3},
    {"id": "sfx_footsteps", "at": "a1_c008_02.end+0.60", "gain": 0.35},
    {"id": "sfx_bamboo_drop", "at": "a1_c008_02.end+7.95", "gain": 0.4},
]

txt = json.dumps(d, ensure_ascii=False, indent=1)
tmp = DST.with_suffix(".json.tmp")
tmp.write_text(txt + "\n")
json.loads(tmp.read_text())
os.replace(tmp, DST)
print("wrote", DST.relative_to(ROOT))
