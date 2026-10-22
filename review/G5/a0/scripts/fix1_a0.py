"""G5 修正第 1 輪：app/cues/show/a0.json（開場）。從 c2e8868 的版本（scratchpad 備份或 git show）重建，重跑結果相同。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/fix1_a0.py
寫入方式：先寫暫存檔、讀回驗證 JSON，再搬回（段落檔隨時保持合法）。
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DST = ROOT / "app/cues/show/a0.json"
src = subprocess.run(["git", "show", "c2e8868:app/cues/show/a0.json"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
d = json.loads(src)
C = {c["id"]: c for c in d["cues"]}


def A(name, start, target=None, duration=None, **params):
    a = {"name": name, "start": start}
    if target:
        a["target"] = target
    if duration is not None:
        a["duration"] = duration
    if params:
        a["params"] = params
    return a


# ───────── a0_c001 開幕（主線特別授權）：依裁定 2 拿掉角色立起（節拍表「無角色」）；劇名「紙燈節」紙條由景 workshop_a0 畫
c = C["a0_c001"]
c["set"] = "workshop_a0"
c["initialState"]["characters"] = {}
c["animation"] = [a for a in c["animation"] if a["name"] != "puppet.popup"]
c["teacherNote"] = ("一次按鍵完成：署名卡約 1 秒淡出、場燈漸暗、柔和追光慢慢掃過台口 → 摺層紙布幕約 2 秒打開（3.0 秒對上開幕曲落點）"
                    "→ 立體書景片依序立起（空的燈籠店，還沒有人）→ 劇名「紙燈節」紙條約 5.2 秒淡入、停約 3 秒後收起 → 鏡頭慢慢推到工作台中景（4.6 秒，光敏：放慢），停住等老師。"
                    "開幕曲一次播完、自然收尾。（全劇版：旁白 a0_c001_01 在 7.6 秒進來。）")

# ───────── a0_c002 折折登場：推近到工作台，燈籠紙佔畫面高約 30%，三下摺（各約 0.5 秒）看得清楚；回憶小窗淡入後才切到回憶鏡位
c = C["a0_c002"]
c["initialState"]["stage"]["camera"] = "a0_fold"
FOLD0, FOLD_DUR = 1.05, 4.0          # 三下摺各約 0.67 秒（細格光敏：3.0 秒時摺面翻轉每秒 4 次、3.4／3.8 秒時仍有 4 次）
anims = []
for a in c["animation"]:
    if a["name"] == "camera.move" and a["params"].get("to") == "a0_memory":
        anims.append(A("camera.cut", "a0_c002_02.end+1.30", duration=0, to="a0_memory"))   # 紙框淡入完成（end+0.9）後再停一下才硬切
        continue
    if a["name"] == "zhezhe.fold" and a["params"].get("form") == "idle":
        a = {**a, "start": FOLD0, "duration": FOLD_DUR}
    if a["name"] == "zhezhe.twitch" and a["start"] == 3.96:
        a = {**a, "start": round(FOLD0 + FOLD_DUR, 2)}
    if a["name"] == "puppet.popup":       # 回憶裡阿樂叔叔立起：延後到硬切之後、放慢到 1.6 秒（細格光敏）
        a = {**a, "start": "a0_c002_02.end+1.60", "duration": 1.6}
    if a["name"] == "puppet.chest":       # 摺紙手勢三下拉開到每 1.1–1.3 秒一下（細格光敏）
        to = a["params"]["to"]
        st = {1: None, 0.55: "a0_c002_02.end+4.20"}.get(to)
        if st is None:
            st = "a0_c002_02.end+3.10" if not any(x["name"] == "puppet.chest" for x in anims) else "a0_c002_02.end+5.30"
        a = {**a, "start": st, "duration": 0.8}
    anims.append(a)
c["animation"] = anims
c["sfx"] = [{"id": "sfx_fold", "at": round(FOLD0 + FOLD_DUR * 0.6 * k, 3), "gain": 0.7} for k in (0.28, 0.62, 0.96)] + \
           [{"id": "sfx_paper_rustle", "at": round(FOLD0 + FOLD_DUR - 0.05, 2), "gain": 0.35}]
c["voStart"] = 5.2
c["teacherNote"] = "播完停格（回憶小窗），等老師按下一步。"

# ───────── a0_c003 主燈骨架不見了
c = C["a0_c003"]
c["initialState"]["stage"]["camera"] = "a0_table2"
c["initialState"]["characters"]["ale"] = {"visible": True, "emotion": "worried", "x": -3.2, "z": -1.55, "facing": 1, "sit": 0}
c["animation"] = [
    A("zhezhe.emote", "a0_c003_01+0.20", "zhezhe", emotion="proud"),
    A("camera.cut", "a0_c003_01+2.10", duration=0, to="a0_design"),
    A("zhezhe.look", "a0_c003_01+2.20", "zhezhe", 0.6, yaw=-0.5),
    A("zhezhe.twitch", "a0_c003_01+3.30", "zhezhe", side="both"),
    # 「不見了！」：切到空底座（畫面中央），折折轉頭看它、走過去、耳朵垂下
    A("camera.cut", "a0_c003_02-0.20", duration=0, to="a0_base"),
    A("zhezhe.look", "a0_c003_02+0.10", "zhezhe", 0.6, yaw=-0.45),
    A("zhezhe.emote", "a0_c003_02+1.40", "zhezhe", emotion="worried"),
    # 阿樂叔叔從畫外（裡間，畫面左邊）走進來：底座近景時他從框外起步，上半身從左緣進框（腿被工作台擋住）；
    # 走到桌角時切到雙人中景（動作中切），整個人已在畫面裡，再走 1.3 單位停在工作台後。平移不加上下彈跳（細格光敏）
    {"name": "puppet.move", "target": "ale", "start": "a0_c003_02.end+0.60", "duration": 2.6, "params": {"dx": 2.58}},
    A("camera.cut", "a0_c003_02.end+1.90", duration=0, to="a0_ale"),
    A("zhezhe.look", "a0_c003_02.end+0.90", "zhezhe", 0.5, yaw=-0.45),
    # 疲倦：換擔心臉（阿樂叔叔沒有「疲倦」臉，用最接近的 worried）＋頭往下垂一點＋手放到胸口（正面紙偶沒有「手到頭邊」的姿勢，
    # puppet.wave 只在側面有效；抓頭交主線評估是否加 rig 姿勢）
    A("puppet.face", "a0_c003_02.end+2.85", "ale", emotion="worried"),
    A("puppet.tilt", "a0_c003_02.end+2.95", "ale", 0.7, to=0.09),
    A("puppet.chest", "a0_c003_02.end+2.95", "ale", 0.8, to=0.7),
    A("puppet.tilt", "a0_c003_03-0.35", "ale", 0.7, to=0.07),
    A("puppet.face", "a0_c003_03-0.30", "ale", emotion="confused"),
    A("puppet.lean", "a0_c003_03+1.20", "ale", 0.9, to=0.05),
    A("puppet.chest", "a0_c003_03+0.90", "ale", 0.8, to=1),
    A("puppet.chest", "a0_c003_04+1.00", "ale", 0.9, to=0),
    A("zhezhe.emote", "a0_c003_04-0.10", "zhezhe", emotion="sad"),
    A("zhezhe.look", "a0_c003_04+1.20", "zhezhe", 0.6, yaw=0.0),
    A("puppet.lean", "a0_c003_04+0.40", "ale", 0.9, to=0.0),
    A("puppet.face", "a0_c003_04+1.50", "ale", emotion="worried"),
]
for l in c["lines"]:
    if l["id"] == "a0_c003_03":
        l["start"] = "a0_c003_02.end+3.20"
c["sfx"] = [{"id": "sfx_footsteps", "at": "a0_c003_02.end+0.40", "gain": 0.3},
            {"id": "sfx_footsteps", "at": "a0_c003_02.end+1.50", "gain": 0.35}]
c["tail"] = 2.0

# ───────── a0_c004 小晴和小宇：走進門改用平移（不加走路上下彈跳，細格光敏）；折折先跳到台面前緣、鏡頭推近再摺帽子；
#           「小晴、小宇」兩人一起對嘴（timeline actorIds），拿掉圓嘴代替的寫法
c = C["a0_c004"]
ini = c["initialState"]["characters"]
# 進門在大全景裡演（人物小，腿的明暗不會觸發細格光敏），兩人錯開 1.4 秒；走到定點後切到孩子中景
c["initialState"]["stage"]["camera"] = "a0_shopwide"
ENTER = {"xiaoyu": (6.9, 0.35, 3.0, 3.1), "xiaoqing": (6.0, 1.75, 2.8, 4.6)}      # 起點偏移、開始、時長、換站姿
ini["xiaoyu"]["x"] = round(1.6 + ENTER["xiaoyu"][0], 2)
ini["xiaoqing"]["x"] = round(2.7 + ENTER["xiaoqing"][0], 2)
anims = []
for a in c["animation"]:
    if a["name"] == "puppet.enter":
        off, st, du, _ = ENTER[a["target"]]
        anims.append({"name": "puppet.move", "target": a["target"], "start": st, "duration": du, "params": {"dx": -off}})
        continue
    if a["name"] == "puppet.pose" and a["params"]["pose"] in ("standwatch", "stand") and isinstance(a["start"], (int, float)):
        a = {**a, "start": ENTER[a["target"]][3]}
    if a["name"] == "camera.move" and a["params"].get("to") == "a0_kids":
        anims.append(A("camera.cut", 5.2, duration=0, to="a0_kids"))
        continue
    if a["name"] == "puppet.face" and str(a["start"]).startswith("a0_c004_06"):
        continue      # 兩人一起說：不再用 surprised 圓嘴代替
    if a["name"] == "zhezhe.hopTo":
        anims.append(A("zhezhe.hopTo", "a0_c004_03.end+1.25", "zhezhe", 0.9, pos=[1.62, 1.99, 0.47], height=0.45))
        continue
    anims.append(a)
anims += [
    A("zhezhe.hopTo", "a0_c004_03-0.90", "zhezhe", 0.7, pos=[1.0, 1.4, -0.6], height=0.25),
    A("camera.move", "a0_c004_03-0.50", duration=3.0, to="a0_hat"),
]
c["animation"] = anims
for l in c["lines"]:
    if l["id"] == "a0_c004_03":
        l["start"] = "a0_c004_02.end+2.00"
c["tail"] = 1.8

# ───────── a0_c005 請大家一起找：孩子往右平移出門；折折跳到台口前緣後硬切大全景（大幅後拉改硬切，細格光敏）；
#           停格時阿樂叔叔換略疲倦的表情（延續 a0_c003 的伏筆）
c = C["a0_c005"]
c["initialState"]["stage"]["camera"] = "a0_hat"
anims = []
for a in c["animation"]:
    if a["name"] == "puppet.exit":
        anims.append({"name": "puppet.move", "target": a["target"], "start": a["start"], "duration": a["duration"], "params": {"dx": a["params"]["to"]}})
        continue
    if a["name"] == "camera.move":
        # 「台口上這八盞燈」：引擎的台口實景燈（裁定 3）只在 quiz 鏡位看得到 → 硬切到台口全景（和之後題卡模式同一個鏡位）
        anims.append(A("camera.cut", 0.3, duration=0, to="quiz"))
        continue
    if a["name"] == "zhezhe.fold" and a["params"].get("form") == "idle":
        a = {**a, "params": {"form": "idle", "scale": 1.6}}
    if a["name"] == "zhezhe.hopTo" and a["start"] == 0.35:     # 跳到台口前緣最左側（兩行字幕條很寬，折折要在它左邊才看得到）
        a = {**a, "params": {**a["params"], "pos": [-7.0, 0.0, 6.0]}}
    anims.append(a)
anims += [
    A("puppet.face", 4.6, "ale", emotion="worried"),
    A("puppet.tilt", 4.7, "ale", 0.8, to=0.05),
    A("puppet.chest", 5.0, "ale", 0.9, to=0.6),
]
c["animation"] = anims
c["tail"] = 2.4

txt = json.dumps(d, ensure_ascii=False, indent=1)
tmp = DST.with_suffix(".json.tmp")
tmp.write_text(txt + "\n")
json.loads(tmp.read_text())
os.replace(tmp, DST)
print("wrote", DST.relative_to(ROOT))
