"""第五幕段落檔產生器：讀現有 app/cues/show/a5.json（台詞、題目、storyboard 不動），重排表演、鏡頭、聲音、景，
寫到暫存檔、驗證 JSON 後再搬回（同時開工時段落檔隨時保持合法）。

用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/make_a5_cues.py（修正第 1 輪前的版本：make_a5_cues_r0.py）
景：a5_gate（app/src/sets/a5_gate.ts＝gate 建構器＋第五幕程式景片）、a5_hospital（assets/final/sets/a5_hospital/layout.json）。
setTrack＝景的程式動作（格式見 a5_gate.ts、gate.ts 檔頭；引擎不讀）。
"""
import copy
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "app/cues/show/a5.json"
# 底稿（tools/build_show_skeleton.py 產生的原始段落檔；台詞、題目、storyboard 從這裡取）
SKEL = ROOT / "review/G5/a5/scripts/a5_skeleton.json"

src = json.loads(SKEL.read_text(encoding="utf-8"))
OLD = {c["id"]: c for c in src["cues"]}

# ------------------------------------------------------------------ 名冊（順序＝層序）
ROSTER = {
    "ale": {"name": "阿樂叔叔", "rig": "ale_v03", "x": -2.65, "z": 0.3, "facing": 1, "fallback": "adult"},
    "chen": {"name": "陳伯伯", "rig": "standee:chen", "x": -0.95, "z": 0.62, "facing": 1, "fallback": "adult"},
    "medic_a": {"name": "救護人員A", "rig": "standee:medic_a", "x": -7.0, "z": 1.0, "facing": 1, "fallback": "adult"},
    "medic_b": {"name": "救護人員B", "rig": "standee:medic_b", "x": -6.2, "z": 0.9, "facing": 1, "fallback": "adult"},
    "lin": {"name": "林老師", "rig": "standee:lin", "x": 7.4, "z": 1.35, "facing": -1, "fallback": "adult"},
    "xiaoyu": {"name": "小宇", "rig": "standee:xiaoyu", "x": 4.35, "z": 1.75, "facing": 1, "fallback": "child"},
    "xiaoqing": {"name": "小晴", "rig": "standee:xiaoqing", "x": 3.75, "z": 2.0, "facing": 1, "fallback": "child"},
    "ye": {"name": "葉護理師", "rig": "standee:ye", "x": 1.75, "z": 0.9, "facing": 1, "fallback": "adult"},
    "zhezhe": {"name": "折折", "rig": "zhezhe", "x": 3.2, "z": 2.55, "facing": 1, "fallback": "child"},
}

# 陳伯伯手上導護旗的握點（立牌身體座標）：stand／receive 畫面右手、standr 鏡射、shoutr 垂下握拳那隻手
FLAG = {
    "stand": {"at": [0.587, 1.329], "dir": 1},
    "receive": {"at": [0.587, 1.329], "dir": 1},
    "standr": {"at": [-0.587, 1.329], "dir": -1},
    "shoutr": {"at": [-0.585, 1.397], "dir": -1},
}

def A(name, start, duration=None, target=None, ease=None, **params):
    a = {"name": name, "start": start}
    if duration is not None:
        a["duration"] = duration
    if target:
        a["target"] = target
    if ease:
        a["ease"] = ease
    if params:
        a["params"] = params
    return a


def pose(target, start, p):
    return A("puppet.pose", start, 0.24, target, pose=p)


def chen_pose(start, p, track, flip_mid=True):
    """陳伯伯換姿勢＋導護旗在翻面中點換手"""
    track.append({"do": "chenFlag", "start": plus(start, 0.12), "to": 1, **FLAG[p]})
    return pose("chen", start, p)


def plus(ref, d):
    """時間參照加秒數（"a5_c001_01.end+0.3" + 0.2 → "a5_c001_01.end+0.5"）"""
    if isinstance(ref, (int, float)):
        return round(ref + d, 3)
    m = re.match(r"^([a-z0-9_]+(?:\.end|\.start)?)([+-]\d+(?:\.\d+)?)?$", ref)
    base, off = m.group(1), float(m.group(2) or 0)
    v = round(off + d, 3)
    return base if v == 0 else f"{base}{'+' if v > 0 else '-'}{abs(v)}"


def keep(c, keys):
    return {k: c[k] for k in keys if k in c}


def base_cue(cid):
    o = OLD[cid]
    c = {k: copy.deepcopy(o[k]) for k in ("id", "sceneId", "kind", "title") if k in o}
    return c


def finish(c, old_keys=("lines", "next", "prevStable", "skippable", "compression", "fx", "teacherNote", "checkpoint", "quiz", "lamp", "storyboard")):
    o = OLD[c["id"]]
    for k in old_keys:
        if k in o and k not in c:
            c[k] = copy.deepcopy(o[k])
    return c


def set_line_starts(c, starts):
    for l in c["lines"]:
        if l["id"] in starts:
            l["start"] = starts[l["id"]]
        else:
            l.pop("start", None)


# ======================================================================================================
# 修正第 1 輪（G5 第二批驗收 b2_director／b2_safety／b2_art；主線補充裁定與 08:0x 更正裁定）
#  - 細格光敏：題卡進出、回故事用 fade.out → 暗中切鏡＋調燈 → fade.in（各 0.6 秒）；姿勢翻面離切鏡 ≥0.6 秒；
#    救護車在鏡頭靜止時倒車進場（正弦緩入緩出 4 秒），車身腰線與輪胎的明度差減半（景圖 v02）。
#  - 題卡模式折折統一 {x −4.7, y 0, z 4.15}；出題鏡頭 quiz；「第七題！」1.45 秒開始。
#  - 叫不醒：頭側傾＋身體一起約 31°、頭往下沉（景的 slump 軌）、閉眼、線鬆垂（張力 0.04），停 2 秒才讓孩子喊。
#  - 小宇的手錶在左腕：a5_c005 起小宇 facing −1（standwatch_m／dial 鏡射後＝錶在左腕）。
#  - 送醫：救護人員從車後出來、擔架（阿樂叔叔坐在擔架上，遠景）送進後車門、關門、慢慢往左開走；陳伯伯在車前、不在車後。
# ======================================================================================================
# 叫不醒的姿勢（頭往畫面右：腕、肘線在畫面左）：頭側傾 0.46＋身體 0.08 ≈ 31°
SLUMP_TILT, SLUMP_LEAN, SLACK = -0.46, 0.08, 0.04
FADE = 0.6
ZQ = [-4.7, 0, 4.15]                       # 題卡模式折折
ZS = [3.2, 0, 2.55]                        # 故事裡折折（孩子腳邊）


def slumped_ale(extra=None):
    c = {"visible": True, "sit": 1, "emotion": "neutral", "strings": ["wrist", "elbow", "knee"], "stringTension": SLACK,
         "x": -2.65, "z": 0.3, "facing": 1}
    if extra:
        c.update(extra)
    return c


def slump_anims():
    return [A("puppet.tilt", 0, 0, "ale", to=SLUMP_TILT), A("puppet.lean", 0, 0, "ale", to=SLUMP_LEAN)]


# 阿樂叔叔叫不醒之後各 cue 的景軌：閉眼、頭下沉、小朋友已離開、小貨車是第四幕那張（竹編貓頭骨架）
SLEEP_TRACK = [{"do": "sleep", "start": 0, "duration": 0, "to": 1}, {"do": "slump", "start": 0, "duration": 0, "to": 1},
               {"do": "catEar", "start": 0, "duration": 0, "to": 1}]

cues = []

# ================================================================== a5_c001 叫不醒
c = base_cue("a5_c001")
c["sceneId"] = "a5_gate"
c["set"] = "a5_gate"
c = finish(c)
L1, L2, L3, L4, L5, L6 = (f"a5_c001_0{i}" for i in range(1, 7))
CUT_CORNER = f"{L1}.end+0.15"
CUT2 = f"{L3}.end+1.8"                     # 陳伯伯要走了：切到遠景轉角
WALK = plus(CUT2, 1.4)                    # 起步（翻面在切鏡後 0.9 秒、起步再晚 0.5 秒：光敏錯開）
# 走路分兩段（等速）：經過長椅與阿樂叔叔前面（景物多）每秒 0.75 單位，之後每秒 0.95 單位
# （遠景每秒約 120／150 px：兩條褲管與鞋子掃過細格每秒 ≤3 次）
WALK_A, WALK_A_DX = 3.2, -2.4
WALK_B, WALK_B_DX = 2.9, -2.75
GONE = plus(WALK, 5.5)                    # 陳伯伯走到街角小店後面（長椅中景看不到他）→ 切長椅中景
DROOP = plus(GONE, 0.45)                  # 頭慢慢垂下 2.3 秒，停 2 秒才讓孩子喊
track = [
    {"do": "catEar", "start": 0, "duration": 0, "to": 1},
    {"do": "student", "start": 0, "duration": 0, "to": 1},
    {"do": "chenFlag", "start": 0, "to": 1, **FLAG["stand"]},
    {"do": "studentWave", "start": f"{L1}.end+0.4", "duration": 3.4},
    {"do": "studentWave", "start": plus(WALK, 0.4), "duration": 2.0},
    {"do": "studentGo", "start": plus(WALK, 4.0), "duration": 2.6, "dx": -2.6},
    {"do": "slump", "start": DROOP, "duration": 2.3, "to": 1},
    {"do": "sleep", "start": plus(DROOP, 0.7), "duration": 0.7, "to": 1},
]
anims = [
    A("puppet.face", 1.0, None, "xiaoqing", emotion="surprised"),
    A("zhezhe.emote", 1.2, None, "zhezhe", emotion="curious"),
    A("puppet.face", f"{L1}.end+0.2", None, "xiaoqing", emotion="neutral"),
    # 遠景轉角（亮度相近的硬切）：遠處轉角的低年級小朋友揮手；陳伯伯看看轉角、又看看校門、對阿樂叔叔交代
    A("camera.cut", CUT_CORNER, 0, None, to="a5_corner"),
    chen_pose(f"{L1}.end+0.6", "standr", track),
    chen_pose(f"{L2}.start+0.2", "receive", track),
    A("puppet.tilt", f"{L2}.start+2.0", 0.35, "ale", to=0.06),
    A("puppet.tilt", f"{L2}.start+2.4", 0.4, "ale", to=0.0),
    # 轉向右邊辦公室、手圍在嘴邊大聲交代
    A("camera.cut", f"{L2}.start+3.05", 0, None, to="a5_bench_chen"),
    chen_pose(f"{L2}.start+3.2", "shoutr", track),
    chen_pose(f"{L3}.start+0.15", "standr", track),
    A("puppet.lean", f"{L3}.end+0.05", 0.25, "chen", to=-0.05),
    A("puppet.lean", f"{L3}.end+0.32", 0.35, "chen", to=0.0),
    chen_pose(f"{L3}.end+0.9", "receive", track),          # 拍拍阿樂叔叔的肩膀
    # 快步走向轉角（等速平移、沒有走路起伏：光敏），轉過街角就看不見
    A("camera.cut", CUT2, 0, None, to="a5_corner"),
    chen_pose(plus(CUT2, 0.9), "stand", track),
    A("puppet.move", WALK, WALK_A, "chen", "linear", dx=WALK_A_DX),
    A("puppet.move", plus(WALK, WALK_A), WALK_B, "chen", "linear", dx=WALK_B_DX),
    # 長椅中景：陳伯伯走了，阿樂叔叔的頭慢慢垂下、身體歪向一邊、線鬆垂、閉眼
    A("camera.cut", GONE, 0, None, to="a5_bench"),
    A("puppet.tilt", DROOP, 2.3, "ale", to=SLUMP_TILT),
    A("puppet.lean", DROOP, 2.3, "ale", to=SLUMP_LEAN),
    A("puppet.face", DROOP, None, "ale", emotion="neutral"),
    A("strings.tension", DROOP, 2.3, "ale", to=SLACK),
    A("fx.desat", DROOP, 3.2, None, to=0.35),
    # 停 2 秒 → 孩子在門裡叫他（孩子前景右、長椅後景左：前後景深）
    A("camera.cut", plus(DROOP, 3.95), 0, None, to="a5_deep"),
    A("puppet.face", f"{L4}.start", None, "xiaoyu", emotion="worried"),
    A("puppet.face", f"{L4}.start+0.3", None, "xiaoqing", emotion="worried"),
    pose("xiaoqing", f"{L5}.start-0.45", "worried"),
    # 停格：兩個孩子＋折折（折折耳朵壓平，小聲把問題交給觀眾）
    A("camera.cut", f"{L5}.end+0.3", 0, None, to="a5_kids_z"),
    A("zhezhe.emote", f"{L5}.end+0.4", None, "zhezhe", emotion="worried"),
]
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_ots", "light": 1, "set": 1, "desat": 0},
    "characters": {
        "ale": {"visible": True, "sit": 1, "emotion": "confused", "strings": ["wrist", "elbow", "knee"], "stringTension": 0.12,
                "x": -2.65, "z": 0.3, "facing": 1},
        "chen": {"visible": True, "x": -1.2, "z": 0.62, "pose": "stand", "emotion": "neutral", "facing": 1},
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "standwatch", "emotion": "neutral"},
        "xiaoqing": {"visible": True, "x": 3.75, "z": 2.0, "pose": "stand", "emotion": "neutral"},
        "zhezhe": {"visible": True, "x": ZS[0], "z": ZS[2], "emotion": "neutral"},
    },
}
c["animation"] = anims
c["audioId"] = "music_m4_light"
c["music"] = [{"id": "none", "at": plus(CUT2, 4.0), "fade": 2.6}]
c["sfx"] = [
    {"id": "sfx_footsteps", "at": plus(WALK, 0.02), "gain": 0.45},
    # 音樂停住、只剩很輕的風：2.6 秒的陣風隔 4.3 秒排四次（停格時配樂與音效 3 秒內 ≤ −35 LUFS）
    {"id": "sfx_gust", "at": plus(CUT2, 3.3), "gain": 0.8},
    {"id": "sfx_gust", "at": plus(CUT2, 7.6), "gain": 0.7},
    {"id": "sfx_gust", "at": plus(CUT2, 11.9), "gain": 0.6},
    {"id": "sfx_gust", "at": plus(CUT2, 16.2), "gain": 0.5},
]
set_line_starts(c, {L1: 0.95, L2: plus(CUT_CORNER, 1.55), L3: f"{L2}.end+0.3", L4: plus(DROOP, 4.3), L5: f"{L4}.end+0.45",
                    L6: f"{L5}.end+0.5"})
c["voStart"] = 0.95
c["tail"] = 0.8
c["setTrack"] = track
c["fx"] = ["FX8"]
cues.append(c)

# ================================================================== 題卡三段
END_C001 = {
    "ale": slumped_ale(),
    "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "standwatch", "emotion": "worried"},
    "xiaoqing": {"visible": True, "x": 3.75, "z": 2.0, "pose": "worried", "emotion": "worried"},
}
QUIZ_TRACK = copy.deepcopy(SLEEP_TRACK)

# ---- a5_c002 出題：起始＝a5_c001 停格 → 漸暗 → 暗中切到 quiz、燈 0.55、折折到台口左前 → 漸亮 →「第七題！」→ 摺題卡
o = OLD["a5_c002"]
c = copy.deepcopy(o)
c["sceneId"] = c["set"] = "a5_gate"
c["initialState"] = {"stage": {"curtain": "open", "camera": "a5_kids_z", "light": 1, "set": 1, "desat": 0.35},
                     "characters": {**copy.deepcopy(END_C001), "zhezhe": {"visible": True, "x": ZS[0], "z": ZS[2], "emotion": "worried"}}}
Q1 = "a5_c002_01"
c["animation"] = slump_anims() + [
    A("zhezhe.hush", 0.0, 1.4, "zhezhe"),
    A("fade.out", 0.0, FADE),
    A("camera.cut", 0.62, 0, None, to="quiz"),
    A("light.dim", 0.62, 0.06, None, to=0.55),
    A("zhezhe.glideTo", 0.62, 0.05, "zhezhe", pos=ZQ),
    A("zhezhe.emote", 0.64, None, "zhezhe", emotion="curious"),
    A("fade.in", 0.72, FADE),
    A("zhezhe.emote", 1.35, None, "zhezhe", emotion="happy"),
    A("zhezhe.fold", f"{Q1}.end+0.05", 1.2, "zhezhe", form="card"),
    A("quiz.show", f"{Q1}.end+0.6", 0.6),
    A("zhezhe.fold", f"{Q1}.end+1.35", 0.7, "zhezhe", form="idle"),
]
c["sfx"] = [{"id": "sfx_quiet_fold", "at": 0}, {"id": "sfx_card_in", "at": f"{Q1}.end+0.6", "gain": 0.8}]
for l in c["lines"]:
    l.pop("start", None)
    if l["id"] == "a5_c002_02":
        l["start"] = f"{Q1}.end+1.3"
c["voStart"] = 1.45
c["tail"] = 0.7
c["setTrack"] = copy.deepcopy(QUIZ_TRACK)
cues.append(c)

QZ = {"visible": True, "x": ZQ[0], "y": ZQ[1], "z": ZQ[2], "emotion": "curious"}
# ---- a5_c003 揭答（折折留在台口左前、idle）
o = OLD["a5_c003"]
c = copy.deepcopy(o)
c["sceneId"] = c["set"] = "a5_gate"
c["initialState"] = {"stage": {"curtain": "open", "camera": "quiz", "light": 0.55, "quiz": True, "set": 1, "desat": 0.35},
                     "characters": {**copy.deepcopy(END_C001), "zhezhe": dict(QZ)}}
c["animation"] = slump_anims() + [A("quiz.reveal", 0.3, 0.45), A("zhezhe.emote", 0.2, None, "zhezhe", emotion="curious")]
c["tail"] = 1.0
c["setTrack"] = copy.deepcopy(QUIZ_TRACK)
cues.append(c)

# ---- a5_c004 點燈 → 題卡淡出（鏡頭不動）→ 漸暗 → 暗中切回故事（a5_c005 的主觀鏡頭）、燈恢復、折折回孩子腳邊 → 漸亮
o = OLD["a5_c004"]
c = copy.deepcopy(o)
c["sceneId"] = c["set"] = "a5_gate"
c["initialState"] = {"stage": {"curtain": "open", "camera": "quiz", "light": 0.55, "quiz": True, "set": 1, "desat": 0.35},
                     "characters": {**copy.deepcopy(END_C001), "zhezhe": dict(QZ)}}
K1 = "a5_c004_01"
c["animation"] = slump_anims() + [
    A("lamp.light", 0.3, 1.5, None, index=7),
    A("zhezhe.emote", 0.2, None, "zhezhe", emotion="happy"),
    A("quiz.hide", f"{K1}.end+0.3", 0.6),
    A("fade.out", f"{K1}.end+0.95", FADE),
    A("camera.cut", f"{K1}.end+1.58", 0, None, to="a5_pov_a"),
    A("light.restore", f"{K1}.end+1.58", 0.06),
    A("zhezhe.glideTo", f"{K1}.end+1.58", 0.05, "zhezhe", pos=ZS),
    A("fade.in", f"{K1}.end+1.68", FADE),
]
c["sfx"] = [{"id": "sfx_lamp_on", "at": 0.3}]
c["voStart"] = 1.9
c["tail"] = 0.6
c["setTrack"] = copy.deepcopy(QUIZ_TRACK)
cues.append(c)

# ================================================================== a5_c005 分頭求助
c = base_cue("a5_c005")
c["sceneId"] = c["set"] = "a5_gate"
c = finish(c)
M1, M2, M3 = "a5_c005_01", "a5_c005_02", "a5_c005_03"
PAN0, PAN = 1.15, 2.7
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_pov_a", "light": 1, "set": 1, "desat": 0.35},
    "characters": {
        "ale": slumped_ale(),
        # 鏡射（facing −1）：standwatch_m／dial 鏡射後手錶在左腕（a0_c004 起一致）；standwatch_m 鏡射＝standwatch 原圖
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "standwatch_m", "emotion": "worried", "facing": -1},
        "xiaoqing": {"visible": True, "x": 3.75, "z": 2.0, "pose": "worried", "emotion": "worried"},
        "zhezhe": {"visible": True, "x": ZS[0], "z": ZS[2], "emotion": "worried"},
    },
}
c["animation"] = slump_anims() + [
    # 環顧（小宇的視線）：空空的接送區（靜止）→ 亮度相近的硬切到遠處街角 → 慢慢推近（2.6 秒、正弦緩入緩出、移動小）
    # 到街角後面只露出的陳伯伯導護旗一角（他背對這邊）。整段從接送區一路慢搖到街角在細格光敏會超標（景物多、距離長），改成切＋短推
    A("camera.cut", PAN0, 0, None, to="a5_pov_b0"),
    A("camera.move", PAN0 + 0.3, PAN - 0.3, None, to="a5_pov_b"),
    # 喊完停在旗子上 1 秒，旗子不動（沒有回應）
    A("camera.cut", f"{M1}.end+1.05", 0, None, to="a5_kids"),
    pose("xiaoqing", f"{M2}.start+0.7", "stand"),
    A("puppet.face", f"{M2}.start+0.75", None, "xiaoqing", emotion="neutral"),
    # 小晴往右跑進校園（全景、人在畫面上小）
    A("camera.cut", f"{M2}.end+0.25", 0, None, to="a5_wide"),
    A("puppet.move", f"{M2}.end+0.3", 2.3, "xiaoqing", "linear", dx=4.2),
    # 小宇中景：確定沒有大人能馬上來，舉起兒童手錶（左腕）
    A("camera.cut", f"{M2}.end+2.4", 0, None, to="a5_xy"),
    pose("xiaoyu", f"{M3}.start+3.25", "dial"),
    A("puppet.face", f"{M3}.start+3.5", None, "xiaoyu", emotion="neutral"),
]
c["setTrack"] = copy.deepcopy(SLEEP_TRACK) + [
    {"do": "flagPeek", "start": 0, "duration": 0, "to": 1},
    # 搖鏡時對街紅磚騎樓降彩（細格紅色光敏），停住後慢慢回來
    {"do": "brick", "start": PAN0 - 0.6, "duration": 0.5, "to": 0.3},
    {"do": "brick", "start": PAN0 + PAN + 0.4, "duration": 1.2, "to": 0.0},
]
c["audioId"] = None
c["music"] = [{"id": "music_courage", "at": f"{M2}.start", "loop": True, "fade": 2.0, "gain": 0.8}]
c["sfx"] = [{"id": "sfx_gust", "at": 0.1, "gain": 0.8}, {"id": "sfx_gust", "at": 3.0, "gain": 0.7}, {"id": "sfx_footsteps", "at": f"{M2}.end+0.3", "gain": 0.4}]
set_line_starts(c, {M1: PAN0 + PAN + 0.15, M2: f"{M1}.end+1.3", M3: f"{M2}.end+2.65"})
c["voStart"] = PAN0 + PAN + 0.15
c["tail"] = 1.0
cues.append(c)

# ================================================================== a5_c006 撥 119
c = base_cue("a5_c006")
c["sceneId"] = c["set"] = "a5_gate"
c = finish(c)
N = [f"a5_c006_0{i}" for i in range(1, 6)]
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_xy_close", "light": 1, "set": 1, "desat": 0.35},
    "characters": {
        "ale": slumped_ale(),
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "dial", "emotion": "neutral", "facing": -1},
    },
}
c["animation"] = slump_anims() + [
    # 說地點：抬頭看長椅那邊（小宇在前景、長椅在後）
    A("camera.cut", f"{N[1]}.start-0.2", 0, None, to="a5_xy_deep"),
    pose("xiaoyu", f"{N[1]}.start+1.0", "standwatch_m"),
    pose("xiaoyu", f"{N[1]}.end-0.3", "dial"),             # 說完低頭看錶（還在中景；近景裡不翻面：光敏）
    A("camera.cut", f"{N[2]}.start-0.2", 0, None, to="a5_xy_close"),
    # 「我在校門裡面」：門內外分界的全景（門柱、長椅在門外、小宇在門內）
    A("camera.cut", f"{N[3]}.start-0.2", 0, None, to="a5_gate_full"),
    pose("xiaoyu", f"{N[3]}.start+0.9", "standwatch_m"),
    pose("xiaoyu", f"{N[3]}.end-0.3", "dial"),
    A("camera.cut", f"{N[4]}.start-0.2", 0, None, to="a5_xy_close"),
    A("puppet.face", f"{N[4]}.end-0.6", None, "xiaoyu", emotion="smile"),
]
track = copy.deepcopy(SLEEP_TRACK) + [{"do": "flagPeek", "start": 0, "duration": 0, "to": 1},   # 陳伯伯還在街角後面（同 a5_c005）
                                     {"do": "phone", "start": 0.5, "duration": 0.6, "to": 1}]
for i in (0, 2, 4):
    track.append({"do": "phoneTalk", "start": f"{N[i]}.start", "until": f"{N[i]}.end"})
c["setTrack"] = track
c["audioId"] = None
c["musicLevel"] = 0.5
c["sfx"] = [{"id": "sfx_watch_dial", "at": 0.15, "gain": 1.0}, {"id": "sfx_phone_bed", "at": 1.3, "gain": 0.5}]
set_line_starts(c, {N[0]: 1.4, N[1]: f"{N[0]}.end+0.25", N[2]: f"{N[1]}.end+0.25", N[3]: f"{N[2]}.end+0.25", N[4]: f"{N[3]}.end+0.25"})
c["voStart"] = 1.4
c["tail"] = 0.85
cues.append(c)

# ================================================================== a5_c007 大人接手
c = base_cue("a5_c007")
c["sceneId"] = c["set"] = "a5_gate"
c = finish(c)
P1, P2 = "a5_c007_01", "a5_c007_02"
AMB_IN, AMB_DUR = f"{P1}.start+1.9", 4.5          # 救護車遠景（鏡頭不動）：倒車進來（林老師的話接著是畫外音）
PARK = plus(AMB_IN, AMB_DUR)
OUT, OUT_DUR = plus(PARK, 0.8), 3.4                # 救護人員推擔架從車後出來，到長椅前（每秒約 1 單位）
G0, G1 = -6.1, -2.65                               # 擔架中心：車後 → 長椅前（阿樂叔叔的位置）
DX = G1 - G0
NOD = plus(OUT, OUT_DUR + 0.1)
DOOR_OPEN = plus(OUT, OUT_DUR + 0.25)
IN, IN_DUR = plus(OUT, OUT_DUR + 1.15), 3.0        # 阿樂叔叔坐在擔架上，推進後車門
DOOR_CLOSE = plus(IN, IN_DUR + 0.1)
GO, GO_DUR, GO_DX = plus(IN, IN_DUR + 0.75), 5.0, -8.0
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_wide", "light": 1, "set": 1, "desat": 0.35},
    "characters": {
        "ale": slumped_ale(),
        # 陳伯伯從街角後面（a5_c001 走到的位置）快步回來，守在長椅右邊（救護車停在長椅左邊，他不在車後）
        "chen": {"visible": True, "x": -4.6, "z": 0.62, "pose": "standr", "emotion": "worried", "facing": 1},
        # 救護人員一開始平躺在街角小店後面（popup 0：看不到），救護車停好後在車後面立起來
        "medic_a": {"visible": True, "x": -7.0, "z": 1.0, "emotion": "neutral", "popup": 0},
        "medic_b": {"visible": True, "x": -6.2, "z": 0.9, "emotion": "neutral", "popup": 0},
        # 林老師、小晴從右邊跑來：林老師蹲在小宇右邊（小宇鏡射、錶在左腕、面向她）
        "lin": {"visible": True, "x": 7.4, "z": 1.35, "pose": "standr", "emotion": "worried", "facing": -1},
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "dial", "emotion": "neutral", "facing": -1},
        "xiaoqing": {"visible": True, "x": 8.2, "z": 1.0, "pose": "walk_l", "emotion": "worried"},
    },
}
track = copy.deepcopy(SLEEP_TRACK) + [
    {"do": "chenFlag", "start": 0, "to": 1, **FLAG["standr"]},
    {"do": "ambulance", "start": AMB_IN, "duration": AMB_DUR, "from": -4.4},
    # 推擔架時對街紅磚騎樓降彩（操偶線跟著阿樂叔叔掃過紅磚：細格紅色光敏）
    {"do": "brick", "start": plus(PARK, 0.1), "duration": 0.6, "to": 0.35},
    {"do": "gurney", "start": PARK, "duration": 0, "x0": G0, "x1": G0, "to": 1},
    {"do": "gurney", "start": OUT, "duration": OUT_DUR, "x0": G0, "x1": G1, "to": 1, "ease": "linear"},
    {"do": "ambDoor", "start": DOOR_OPEN, "duration": 0.7, "to": 1},
    {"do": "gurney", "start": IN, "duration": IN_DUR, "x0": G1, "x1": G0, "to": 1, "ease": "linear"},
    {"do": "ambDoor", "start": DOOR_CLOSE, "duration": 0.8, "to": 0},
    {"do": "gurney", "start": GO, "duration": 0, "x0": G0, "x1": G0, "to": 0},
    {"do": "ambulanceGo", "start": GO, "duration": GO_DUR, "dx": GO_DX},
]
anims = slump_anims() + [
    # 全景：陳伯伯從左邊街角快步回來；林老師、小晴從右邊跑來（短距離、等速；翻面在停下後 ≥0.5 秒、彼此錯開）
    # 陳伯伯：從街角快步回來（全景裡每秒約 1 單位）；救護車進來時再往右讓開（遠景、鏡頭不動）
    A("puppet.move", 0.1, 3.75, "chen", "linear", dx=3.75),
    A("puppet.move", plus(AMB_IN, 0.4), 1.3, "chen", "linear", dx=1.15),
    A("puppet.move", 0.4, 1.9, "lin", "linear", dx=-2.4),
    A("puppet.move", 0.9, 2.0, "xiaoqing", "linear", dx=-2.5),
    A("fx.desat", 0.5, 3.0, None, to=0.0),
    pose("lin", 2.6, "crouch"),
    pose("xiaoqing", 3.25, "worried"),
    # 林老師蹲在小宇右邊、對著他舉起的手錶接手通話
    A("camera.cut", 3.85, 0, None, to="a5_lin_kids"),
    # 救護車遠景（鏡頭不動；不拍擔架上的臉）
    A("camera.cut", AMB_IN, 0, None, to="a5_amb"),
    chen_pose(plus(AMB_IN, 2.0), "receive", track),
    # 救護人員在車後面立起來、站到擔架兩端（都被車身擋住）
    A("puppet.popup", plus(PARK, 0.05), 0.35, "medic_a"),
    A("puppet.popup", plus(PARK, 0.05), 0.35, "medic_b"),
    A("puppet.move", plus(PARK, 0.42), 0.3, "medic_a", "linear", dx=-0.65),
    A("puppet.move", plus(PARK, 0.42), 0.3, "medic_b", "linear", dx=1.65),
    # 推擔架出來 → 長椅前（阿樂叔叔坐上擔架）→ 推進後車門 → 隨車離開
    A("puppet.move", OUT, OUT_DUR, "medic_a", "linear", dx=DX),
    A("puppet.move", OUT, OUT_DUR, "medic_b", "linear", dx=DX),
    A("puppet.nod", NOD, 0.9, "medic_a", count=1),
    A("puppet.nod", plus(NOD, 0.15), 0.9, "medic_b", count=1),
    A("puppet.move", IN, IN_DUR, "medic_a", "linear", dx=-DX),
    A("puppet.move", IN, IN_DUR, "medic_b", "linear", dx=-DX),
    A("puppet.move", IN, IN_DUR, "ale", "linear", dx=-DX),
    A("puppet.move", GO, GO_DUR, "medic_a", "in", dx=GO_DX),
    A("puppet.move", GO, GO_DUR, "medic_b", "in", dx=GO_DX),
    A("puppet.move", GO, GO_DUR, "ale", "in", dx=GO_DX),
    # 林老師與孩子中景：林老師站起來稱讚
    A("camera.cut", plus(GO, 1.35), 0, None, to="a5_lin_kids2"),
    pose("lin", plus(GO, 2.0), "stand"),
    pose("xiaoqing", plus(GO, 2.6), "stand"),
    pose("xiaoyu", plus(GO, 3.3), "standwatch_m"),
    A("puppet.face", f"{P2}.end-0.8", None, "xiaoqing", emotion="smile"),
    A("puppet.face", f"{P2}.end-0.6", None, "xiaoyu", emotion="smile"),
]
c["animation"] = anims
c["setTrack"] = track
c["audioId"] = None
c["music"] = [{"id": "none", "at": f"{P2}.start+0.2", "fade": 3.5}]
c["sfx"] = [{"id": "sfx_footsteps", "at": 0.4, "gain": 0.45}, {"id": "sfx_ambulance_engine", "at": plus(AMB_IN, -1.6), "gain": 0.75}]
set_line_starts(c, {P1: 4.15, P2: plus(GO, 0.65)})
c["voStart"] = 4.15
c["tail"] = 1.0
cues.append(c)

# ================================================================== a5_c008 醫院的走廊
c = base_cue("a5_c008")
c["sceneId"] = c["set"] = "a5_hospital"
c = finish(c)
H = [f"a5_c008_0{i}" for i in range(1, 6)]
c["setFade"] = 1.2
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "hosp_wide", "light": 1, "set": 1, "desat": 0},
    "characters": {
        # 林老師往左坐一點：孩子與葉護理師的中景（hosp_kids）裡不會只露出半個身體
        "lin": {"visible": True, "x": -2.95, "z": -0.2, "pose": "sit", "emotion": "smile", "facing": 1},
        "xiaoyu": {"visible": True, "x": -1.55, "z": -0.15, "pose": "sitb", "emotion": "worried", "facing": 1},
        "xiaoqing": {"visible": True, "x": -0.45, "z": -0.12, "pose": "sitb", "emotion": "worried", "facing": 1},
        "ye": {"visible": True, "x": 1.75, "z": 0.9, "pose": "crouch", "emotion": "smile", "facing": 1},
    },
}
c["animation"] = [
    A("puppet.pose", 0, 0, "lin", pose="sit"),
    A("camera.move", 1.1, 3.2, None, to="hosp_mid"),
    A("camera.cut", f"{H[1]}.start-0.25", 0, None, to="hosp_kids"),
    A("puppet.face", f"{H[2]}.end+0.25", None, "xiaoqing", emotion="neutral"),
    A("camera.cut", f"{H[3]}.start-0.25", 0, None, to="hosp_mid"),
    A("puppet.face", f"{H[4]}.end-0.5", None, "xiaoyu", emotion="neutral"),
]
c["audioId"] = "music_recovery"
c["sfx"] = []
set_line_starts(c, {H[0]: 1.3, H[1]: f"{H[0]}.end+0.45", H[2]: f"{H[1]}.end+0.35", H[3]: f"{H[2]}.end+0.5", H[4]: f"{H[3]}.end+0.35"})
c["voStart"] = 1.3
c["tail"] = 1.3
cues.append(c)

# ------------------------------------------------------------------ 寫回（暫存檔 → 驗證 → 搬回）
out = {k: v for k, v in src.items() if k != "cues"}
out["set"] = "a5_gate"
out["characters"] = ROSTER
out["_note"] = ("第五幕（G5 第五幕代理排戲；review/G5/a5/scripts/make_a5_cues.py 產生；修正第 1 輪）。景：a5_gate（校門口，app/src/sets/a5_gate.ts＝"
                "gate 建構器＋街角、轉角小朋友、救護車與後車門、擔架、電話圖示、阿樂叔叔閉眼與頭下沉）、a5_hospital（醫院走廊，layout.json）。"
                "cue 的 setTrack＝景的程式動作（引擎不讀，景的 update 讀；格式見 a5_gate.ts 與 gate.ts 檔頭）。storyboard 是劇本與節拍表的摘錄，引擎不讀。")
out["cues"] = cues
txt = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
json.loads(txt)
tmp = SRC.with_suffix(".json.tmp")
tmp.write_text(txt, encoding="utf-8")
os.replace(tmp, SRC)
print("寫回", SRC, len(cues), "個 cue")
