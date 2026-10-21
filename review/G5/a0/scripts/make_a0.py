"""開場段落檔 app/cues/show/a0.json：a0_c000、a0_c001（G4）原樣保留，a0_c002–a0_c005 依劇本 v03／節拍表 v03 排表演。
台詞編號、說話者、字幕文字一律從現有段落檔讀出（不改）；只改 initialState、animation、鏡頭、配樂音效、時間參數與 set。
寫到暫存檔、用 node 驗證 JSON 後才搬回（其他代理同時在 build）。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SEG = ROOT / "app/cues/show/a0.json"
d = json.loads(SEG.read_text(encoding="utf8"))
cues = {c["id"]: c for c in d["cues"]}

SET = "workshop_a0"
TABLE = [0.85, 1.4, -0.6]          # 折折在工作台右段
ALE_BACK = {"x": -0.62, "z": -1.55}  # 阿樂叔叔站在工作台後面（空底座後方）
XY = {"x": 1.6, "z": 0.35}          # 小宇（和工作台後的阿樂叔叔、桌上的折折組成一群）
XQ = {"x": 2.7, "z": 0.15}          # 小晴
HAT = [XY["x"] + 0.02, 1.99, XY["z"] + 0.12]   # 紙帽子落在小宇頭上（帽簷在頭頂下一點）
APRON = [0.35, 0.0, 3.35]          # 台口前緣


def A(name, start, dur=None, tgt=None, **params):
    a = {"name": name, "start": start}
    if tgt:
        a["target"] = tgt
    if dur is not None:
        a["duration"] = dur
    if params:
        a["params"] = params
    return a


def S(id_, at, gain=None):
    s = {"id": id_, "at": at}
    if gain is not None:
        s["gain"] = gain
    return s


def fold_sfx(start, dur, from_sheet=False, gain=0.7, line=None, end=False):
    """摺紙聲 S2 對 FOLD_BEATS.crease（zhezhe.ts）；line 給了就錨在台詞上（start＝位移秒數）"""
    beats = [0.6 * 0.28, 0.6 * 0.62, 0.6 * 0.96] if from_sheet else [0.1]
    out = []
    for b in beats:
        off = round(start + dur * b, 3)
        out.append(S("sfx_fold", ref(line, off, end=end) if line else off, gain))
    return out


def ref(line, off=0.0, end=False):
    r = f"{line}.end" if end else line
    if off:
        r += f"{off:+.2f}"
    return r


# ───────────────────────────── a0_c002 折折登場（回憶小窗） ─────────────────────────────
c = cues["a0_c002"]
c["set"] = SET
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a0_table", "light": 1},
    "characters": {
        "zhezhe": {"visible": True, "emotion": "neutral", "x": TABLE[0], "y": TABLE[1], "z": TABLE[2]},
        "ale": {"visible": True, "pose": "sit", "emotion": "smile", "x": -2.6, "z": 0, "facing": 1, "popup": 0},
    },
}
FOLD0 = 1.05
c["animation"] = [
    # 燈籠紙（cue 開始前就摺成方形紙；漸亮時已站在桌上）→ 摺、摺、摺 → 貓，耳朵啪地立起
    A("zhezhe.fold", -1.2, 0.3, "zhezhe", form="sheet"),
    A("zhezhe.fold", FOLD0, 3.0, "zhezhe", form="idle"),
    A("zhezhe.twitch", round(FOLD0 + 3.0 * 0.97, 3), None, "zhezhe", side="both"),
    A("zhezhe.emote", ref("a0_c002_01", -0.1), None, "zhezhe", emotion="happy"),
    A("zhezhe.emote", ref("a0_c002_01", 0.95), None, "zhezhe", emotion="neutral"),
    A("zhezhe.emote", ref("a0_c002_01", 1.75), None, "zhezhe", emotion="proud"),
    A("zhezhe.emote", ref("a0_c002_02", -0.15), None, "zhezhe", emotion="neutral"),
    A("zhezhe.look", ref("a0_c002_02", 2.0), 0.6, "zhezhe", yaw=-0.42),
    A("zhezhe.twitch", ref("a0_c002_02", 2.2), None, "zhezhe", side="l"),
    A("zhezhe.emote", ref("a0_c002_02", 3.2), None, "zhezhe", emotion="happy"),
    # 回憶小窗（景 workshop_a0 的疊層在 _02 結束前 0.5 秒收進來）→ 鏡頭往左帶到工作台前的阿樂叔叔；他像立體書一樣立起
    A("camera.move", ref("a0_c002_02", 0.55, end=True), 2.8, None, to="a0_memory"),
    A("puppet.popup", ref("a0_c002_02", 1.25, end=True), 1.0, "ale"),
    A("puppet.chest", ref("a0_c002_02", 2.05, end=True), 0.7, "ale", to=1),
    A("puppet.chest", ref("a0_c002_02", 2.85, end=True), 0.6, "ale", to=0.55),
    A("puppet.chest", ref("a0_c002_02", 3.5, end=True), 0.6, "ale", to=1),
    # 抬頭對折折笑
    A("puppet.face", ref("a0_c002_03", -0.45), None, "ale", emotion="greet"),
    A("puppet.tilt", ref("a0_c002_03", -0.4), 0.7, "ale", to=0.05),
    A("zhezhe.look", ref("a0_c002_03", -0.6), 0.5, "zhezhe", yaw=-0.5),
    A("puppet.face", ref("a0_c002_03", 0.6, end=True), None, "ale", emotion="smile"),
    A("zhezhe.emote", ref("a0_c002_03", 0.3, end=True), None, "zhezhe", emotion="proud"),
]
c["audioId"] = "music_zhezhe"
c["music"] = [{"id": "music_town", "at": ref("a0_c002_02", -0.6, end=True), "fade": 2.5}]
c["sfx"] = fold_sfx(FOLD0, 3.0, from_sheet=True) + [S("sfx_paper_rustle", round(FOLD0 + 2.9, 2), 0.35)]
c["lines"][2]["start"] = ref("a0_c002_02", 3.0, end=True)
c["voStart"] = 4.55
c["tail"] = 2.4
c["fx"] = ["FX13", "FX8"]
c["teacherNote"] = "播完停格（回憶小窗），等老師按下一步。"

# ───────────────────────────── a0_c003 主燈骨架不見了 ─────────────────────────────
c = cues["a0_c003"]
c["set"] = SET
c["setFade"] = 0.8            # 回憶 → 回到現在：從暗漸亮
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a0_table", "light": 1},
    "characters": {
        "zhezhe": {"visible": True, "emotion": "happy", "x": TABLE[0], "y": TABLE[1], "z": TABLE[2]},
        "ale": {"visible": True, "emotion": "worried", "x": ALE_BACK["x"], "z": ALE_BACK["z"], "facing": 1, "sit": 0},
    },
}
L1, L2, L3, L4 = "a0_c003_01", "a0_c003_02", "a0_c003_03", "a0_c003_04"
c["animation"] = [
    # 「今年的主燈，是照著我的樣子做的！」→ 鏡頭帶到牆上的設計圖，折折回頭看
    A("zhezhe.emote", ref(L1, 0.2), None, "zhezhe", emotion="proud"),
    A("camera.cut", ref(L1, 2.1), 0, None, to="a0_design"),
    A("zhezhe.look", ref(L1, 2.2), 0.6, "zhezhe", yaw=-0.5),
    A("zhezhe.twitch", ref(L1, 3.3), None, "zhezhe", side="both"),
    # 「可是……骨架不見了！」→ 鏡頭落回空著的底座，折折走到底座旁、耳朵垂下
    A("camera.cut", ref(L2, -0.2), 0, None, to="a0_base"),
    A("zhezhe.look", ref(L2, 0.1), 0.6, "zhezhe", yaw=-0.25),
    A("zhezhe.walkTo", ref(L2, 0.4), 1.2, "zhezhe", pos=[0.62, TABLE[1], TABLE[2]]),
    A("zhezhe.emote", ref(L2, 1.4), None, "zhezhe", emotion="worried"),
    # 音樂停半拍；阿樂叔叔從裡間（左邊）走到工作台後，抓抓頭
    # 從畫面外（左）慢慢走進來（等速、每秒約 0.7 單位，像有點累；說「不見了」時已經在畫面外起步）
    {"name": "puppet.enter", "target": "ale", "start": ref(L2, 0.0), "duration": 5.6, "ease": "linear", "params": {"from": -4.0}},
    A("camera.move", ref(L2, 2.0, end=True), 2.6, None, to="a0_ale"),
    A("zhezhe.look", ref(L2, 0.9, end=True), 0.5, "zhezhe", yaw=-0.45),
    A("puppet.tilt", ref(L3, -0.35), 0.7, "ale", to=0.07),
    A("puppet.face", ref(L3, -0.3), None, "ale", emotion="confused"),
    A("puppet.lean", ref(L3, 1.2), 0.9, "ale", to=0.05),
    A("puppet.chest", ref(L3, 0.9), 0.8, "ale", to=1),
    A("puppet.chest", ref(L4, 1.0), 0.9, "ale", to=0),
    A("zhezhe.emote", ref(L4, -0.1), None, "zhezhe", emotion="sad"),
    A("zhezhe.look", ref(L4, 1.2), 0.6, "zhezhe", yaw=0.0),
    A("puppet.lean", ref(L4, 0.4), 0.9, "ale", to=0.0),
    A("puppet.face", ref(L4, 1.5), None, "ale", emotion="worried"),
]
c["lines"][1]["start"] = ref(L1, 0.6, end=True)
c["lines"][2]["start"] = ref(L2, 2.9, end=True)
c["music"] = [
    {"id": "none", "at": ref(L2, -0.1, end=True), "fade": 0.35},
    {"id": "music_town", "at": ref(L3, -0.2), "fade": 1.4},
]
c["sfx"] = [S("sfx_footsteps", ref(L2, -0.2, end=True), 0.35), S("sfx_footsteps", ref(L2, 1.6, end=True), 0.35)]
c["voStart"] = 1.15
c["tail"] = 2.2
c["fx"] = []

# ───────────────────────────── a0_c004 小晴和小宇（紙帽子） ─────────────────────────────
c = cues["a0_c004"]
c["set"] = SET
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a0_shop", "light": 1},
    "characters": {
        "ale": {"visible": True, "emotion": "worried", "x": ALE_BACK["x"], "z": ALE_BACK["z"], "facing": 1, "sit": 0},
        "zhezhe": {"visible": True, "emotion": "worried", "x": 0.62, "y": TABLE[1], "z": TABLE[2]},
        "xiaoyu": {"visible": True, "emotion": "smile", "x": XY["x"], "z": XY["z"], "facing": -1, "pose": "walk"},
        "xiaoqing": {"visible": True, "emotion": "smile", "x": XQ["x"], "z": XQ["z"], "facing": 1, "pose": "walk_l"},
    },
}
W1, W2, W3, W4, W5, W6 = (f"a0_c004_0{i}" for i in range(1, 7))
c["animation"] = [
    # 門口風鈴（景片輕擺）→ 兩個孩子背著書包從右側走進來
    A("puppet.enter", 0.35, 2.6, "xiaoyu", **{"from": 5.4}),
    A("puppet.enter", 1.45, 2.6, "xiaoqing", **{"from": 5.0}),
    A("puppet.pose", 2.72, 0.24, "xiaoyu", pose="standwatch"),
    A("puppet.pose", 3.82, 0.24, "xiaoqing", pose="stand"),
    A("puppet.face", 2.0, None, "ale", emotion="smile"),
    A("zhezhe.emote", 2.2, None, "zhezhe", emotion="happy"),
    A("zhezhe.look", 2.3, 0.5, "zhezhe", yaw=0.4),
    # 小晴「我記下來」：筆記本特寫小窗（景 workshop_a0 疊層，筆畫逐筆畫上）；鏡頭往右留出小窗的位置
    A("camera.move", ref(W2, -0.4), 2.4, None, to="a0_kids"),
    A("puppet.tilt", ref(W2, 0.2), 0.6, "xiaoqing", to=0.04),
    # 折折：「交給我！我摺成放大鏡」→ 一摺卻摺成紙帽子（摺錯晃一下）→ 輕輕跳到小宇頭上
    A("zhezhe.emote", ref(W3, -0.1), None, "zhezhe", emotion="proud"),
    A("zhezhe.fold", ref(W3, -0.25, end=True), 1.3, "zhezhe", form="hat", fumble=True),
    A("zhezhe.hopTo", ref(W3, 1.25, end=True), 1.05, "zhezhe", pos=HAT, height=0.55),
    A("puppet.face", ref(W3, 2.25, end=True), None, "xiaoyu", emotion="surprised"),
    A("puppet.tilt", ref(W4, 0.3), 0.6, "xiaoyu", to=0.05),
    A("puppet.face", ref(W4, 1.6), None, "xiaoyu", emotion="smile"),
    A("puppet.face", ref(W3, 2.35, end=True), None, "xiaoqing", emotion="surprised"),
    A("puppet.face", ref(W4, 1.0), None, "xiaoqing", emotion="smile"),
    # 阿樂叔叔請他們先上學；「好！」兩人一起
    A("puppet.lean", ref(W5, 0.2), 0.8, "ale", to=-0.03),
    A("puppet.lean", ref(W5, 0.3, end=True), 0.8, "ale", to=0.0),
    A("puppet.face", ref(W6, -0.05), None, "xiaoyu", emotion="surprised"),
    A("puppet.face", ref(W6, -0.05), None, "xiaoqing", emotion="surprised"),
    A("puppet.face", ref(W6, 0.05, end=True), None, "xiaoyu", emotion="smile"),
    A("puppet.face", ref(W6, 0.05, end=True), None, "xiaoqing", emotion="smile"),
]
c["lines"][2]["start"] = ref(W2, 2.4, end=True)
c["music"] = [
    {"id": "music_zhezhe", "at": ref(W3, -0.3), "fade": 0.9},
    {"id": "music_town", "at": ref(W5, -0.6), "fade": 1.6},
]
c["sfx"] = [S("sfx_windchime", 0.15, 0.7), S("sfx_footsteps", 0.45, 0.4)] + fold_sfx(-0.25, 1.3, line=W3, end=True) + [S("sfx_paper_rustle", ref(W3, 2.25, end=True), 0.35)]
c["voStart"] = 3.35
c["tail"] = 2.0
c["fx"] = ["FX13"]

# ───────────────────────────── a0_c005 請大家一起找 ─────────────────────────────
c = cues["a0_c005"]
c["set"] = SET
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a0_kids", "light": 1},
    "characters": {
        "ale": {"visible": True, "emotion": "smile", "x": ALE_BACK["x"], "z": ALE_BACK["z"], "facing": 1, "sit": 0},
        "zhezhe": {"visible": True, "emotion": "happy", "x": HAT[0], "y": HAT[1], "z": HAT[2]},
        "xiaoyu": {"visible": True, "emotion": "smile", "x": XY["x"], "z": XY["z"], "facing": -1, "pose": "standwatch"},
        "xiaoqing": {"visible": True, "emotion": "smile", "x": XQ["x"], "z": XQ["z"], "facing": 1, "pose": "stand"},
    },
}
F1, F2, F3 = "a0_c005_01", "a0_c005_02", "a0_c005_03"
c["animation"] = [
    A("zhezhe.fold", -1.2, 0.3, "zhezhe", form="hat"),
    # 紙帽子從小宇頭上跳到台口前緣，落地摺回自己（變大一點，對全場說話）
    A("zhezhe.hopTo", 0.35, 1.35, "zhezhe", pos=APRON, height=1.1),
    A("zhezhe.fold", 1.75, 1.3, "zhezhe", form="idle", scale=1.3),
    # 孩子轉身往右跑出門；阿樂叔叔揮手
    A("puppet.pose", 1.0, 0.24, "xiaoyu", pose="walk_r"),
    A("puppet.exit", 1.9, 2.6, "xiaoyu", to=9.2),
    A("puppet.pose", 2.5, 0.24, "xiaoqing", pose="walk"),
    A("puppet.exit", 3.35, 2.4, "xiaoqing", to=8.6),
    A("puppet.wave", 1.1, 2.6, "ale"),
    # 鏡頭後拉：台口前緣的折折＋台口上方一串八盞還沒亮的燈
    A("camera.move", 3.0, 3.6, None, to="a0_apron"),
    A("fx.spot", 3.6, 2.0, None, to=0.6, target="zhezhe"),
    A("zhezhe.emote", ref(F1, -0.2), None, "zhezhe", emotion="happy"),
    A("zhezhe.look", ref(F2, 0.2), 0.6, "zhezhe", yaw=0.35),
    A("zhezhe.look", ref(F2, 2.6), 0.6, "zhezhe", yaw=-0.3),
    A("zhezhe.look", ref(F3, -0.2), 0.6, "zhezhe", yaw=0.0),
    A("zhezhe.emote", ref(F3, 0.3), None, "zhezhe", emotion="proud"),
    A("zhezhe.twitch", ref(F3, 0.25, end=True), None, "zhezhe", side="both"),
]
c["music"] = []
c["sfx"] = [S("sfx_paper_rustle", 1.7, 0.3)] + fold_sfx(1.75, 1.3) + [S("sfx_footsteps", 1.95, 0.4), S("sfx_footsteps", 3.4, 0.35)]
c["voStart"] = 5.3
c["tail"] = 2.6
c["fx"] = ["FX4", "FX13"]

for k in ("a0_c002", "a0_c003", "a0_c004", "a0_c005"):
    cues[k].pop("minDuration", None)

d["cues"] = [cues[c["id"]] for c in d["cues"]]
tmp = SEG.with_suffix(".json.tmp_a0")
tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
r = subprocess.run(["node", "-e", f"JSON.parse(require('fs').readFileSync({json.dumps(str(tmp))},'utf8'));console.log('ok')"], capture_output=True, text=True)
if r.returncode != 0 or "ok" not in r.stdout:
    print(r.stderr)
    sys.exit(1)
os.replace(tmp, SEG)
print("wrote", SEG)
