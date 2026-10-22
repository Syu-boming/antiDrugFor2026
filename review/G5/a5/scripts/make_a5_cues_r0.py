"""第五幕段落檔產生器：讀現有 app/cues/show/a5.json（台詞、題目、storyboard 不動），重排表演、鏡頭、聲音、景，
寫到暫存檔、驗證 JSON 後再搬回（同時開工時段落檔隨時保持合法）。

用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/make_a5_cues.py
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
    "medic_a": {"name": "救護人員A", "rig": "standee:medic_a", "x": -4.3, "z": 0.45, "facing": 1, "fallback": "adult"},
    "medic_b": {"name": "救護人員B", "rig": "standee:medic_b", "x": -2.9, "z": 0.5, "facing": 1, "fallback": "adult"},
    "lin": {"name": "林老師", "rig": "standee:lin", "x": 2.95, "z": 1.2, "facing": -1, "fallback": "adult"},
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

# 頭往畫面右（膝前線那側的反方向是畫面左的腕、肘線；往右垂才不會碰到腕、肘線）
SLUMP_TILT, SLUMP_LEAN, SLACK = -0.32, 0.05, 0.04


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


def slumped_ale(extra=None):
    c = {"visible": True, "sit": 1, "emotion": "neutral", "strings": ["wrist", "elbow", "knee"], "stringTension": SLACK,
         "x": -2.65, "z": 0.3, "facing": 1}
    if extra:
        c.update(extra)
    return c


def slump_anims():
    """阿樂叔叔叫不醒的姿勢（起始狀態不能寫歪頭，用 0 秒動畫在 cue 開頭擺好）"""
    return [A("puppet.tilt", 0, 0, "ale", to=SLUMP_TILT), A("puppet.lean", 0, 0, "ale", to=SLUMP_LEAN)]


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


cues = []

# ================================================================== a5_c001 叫不醒
c = base_cue("a5_c001")
c["sceneId"] = "a5_gate"
c["set"] = "a5_gate"
c = finish(c)
L1, L2, L3, L4, L5, L6 = (f"a5_c001_0{i}" for i in range(1, 7))
track = [
    {"do": "student", "start": 0, "duration": 0, "to": 1},
    {"do": "chenFlag", "start": 0, "to": 1, **FLAG["stand"]},
    {"do": "studentWave", "start": f"{L1}.end-0.6", "duration": 4.6},
]
CUT_CORNER = f"{L1}.end+0.15"
anims = [
    A("puppet.face", 1.0, None, "xiaoqing", emotion="surprised"),
    A("zhezhe.emote", 1.2, None, "zhezhe", emotion="curious"),
    A("puppet.face", f"{L1}.end+0.2", None, "xiaoqing", emotion="neutral"),
    # 遠景轉角（硬切：大幅換景別）
    A("camera.cut", CUT_CORNER, 0, None, to="a5_corner"),
    # 陳伯伯看看轉角（stand 本來就朝左）→ 又看看校門（standr 朝右）→ 對阿樂叔叔說（receive，手朝他）
    chen_pose(f"{L1}.end+0.8", "standr", track),
    chen_pose(f"{L2}.start-0.15", "receive", track),
    # 阿樂叔叔還能點頭回話
    A("puppet.tilt", f"{L2}.start+2.0", 0.35, "ale", to=0.06),
    A("puppet.tilt", f"{L2}.start+2.4", 0.4, "ale", to=0.0),
    # 轉向右邊辦公室、手圍在嘴邊大聲交代（鏡頭先切到長椅中景，畫面右邊留給辦公室方向）
    A("camera.cut", f"{L2}.start+3.05", 0, None, to="a5_bench_chen"),
    chen_pose(f"{L2}.start+3.2", "shoutr", track),
    # 林老師畫外回答：陳伯伯朝右聽、點頭
    chen_pose(f"{L3}.start+0.15", "standr", track),
    A("puppet.lean", f"{L3}.end+0.05", 0.25, "chen", to=-0.05),
    A("puppet.lean", f"{L3}.end+0.32", 0.35, "chen", to=0.0),
    # 拍拍阿樂叔叔的肩膀
    chen_pose(f"{L3}.end+1.45", "receive", track),
    # 快步走向轉角（stand 朝左），轉過街角就看不見
    # （光敏：點頭、翻面、切鏡、起步各自錯開；等速走，每秒約 2.2 單位——預設的三次緩動中段會快到 3 倍）
    A("camera.cut", f"{L3}.end+2.3", 0, None, to="a5_corner"),
    chen_pose(f"{L3}.end+2.75", "stand", track),
    # 平移（puppet.move 沒有走路起伏；引擎的走路起伏每秒 3.2 下，在細格光敏會超標）
    A("puppet.move", f"{L3}.end+3.05", 4.0, "chen", "linear", dx=-5.4),
]
track += [
    {"do": "studentWave", "start": f"{L3}.end+2.95", "duration": 1.6},
    {"do": "studentGo", "start": f"{L3}.end+5.0", "duration": 2.4, "dx": -2.4},
]
# 停頓：陳伯伯走掉 → 長椅中景安靜 1.5 秒 → 頭慢慢垂下
GONE = f"{L3}.end+6.7"
DROOP = f"{L3}.end+8.1"
anims += [
    A("camera.cut", GONE, 0, None, to="a5_bench"),
    A("puppet.tilt", DROOP, 2.5, "ale", to=SLUMP_TILT),
    A("puppet.lean", DROOP, 2.5, "ale", to=SLUMP_LEAN),
    A("puppet.face", DROOP, None, "ale", emotion="neutral"),
    A("strings.tension", DROOP, 2.5, "ale", to=SLACK),
    A("fx.desat", DROOP, 3.2, None, to=0.35),
    # 孩子在門裡叫他（孩子前景右、長椅後景左：前後景深）
    A("camera.cut", f"{L4}.start-0.35", 0, None, to="a5_deep"),
    A("puppet.face", f"{L4}.start", None, "xiaoyu", emotion="worried"),
    A("puppet.face", f"{L4}.start+0.3", None, "xiaoqing", emotion="worried"),
    pose("xiaoqing", f"{L5}.start-0.45", "worried"),
    # 停格：兩個孩子＋折折（折折耳朵壓平，小聲把問題交給觀眾）
    # 停格鏡頭：硬切（光敏：大幅換鏡不用推移）
    A("camera.cut", f"{L5}.end+0.3", 0, None, to="a5_kids_z"),
    A("zhezhe.emote", f"{L5}.end+0.4", None, "zhezhe", emotion="worried"),
]
track += [{"do": "sleep", "start": plus(DROOP, 0.7), "duration": 0.7, "to": 1}]
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_ots", "light": 1, "set": 1, "desat": 0},
    "characters": {
        "ale": {"visible": True, "sit": 1, "emotion": "confused", "strings": ["wrist", "elbow", "knee"], "stringTension": 0.12,
                "x": -2.65, "z": 0.3, "facing": 1},
        "chen": {"visible": True, "x": -0.95, "z": 0.62, "pose": "stand", "emotion": "neutral", "facing": 1},
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "standwatch", "emotion": "neutral"},
        "xiaoqing": {"visible": True, "x": 3.75, "z": 2.0, "pose": "stand", "emotion": "neutral"},
        "zhezhe": {"visible": True, "x": 3.2, "z": 2.55, "emotion": "neutral"},
    },
}
c["animation"] = anims
c["audioId"] = "music_m4_light"
c["music"] = [{"id": "none", "at": f"{L3}.end+6.05", "fade": 2.6}]
c["sfx"] = [
    {"id": "sfx_footsteps", "at": f"{L3}.end+3.07", "gain": 0.45},
    # 音樂停住、只剩很輕的風：用 2.6 秒的陣風隔 4.3 秒排四次（30 秒的 sfx_wind 會一直響到教師停格裡，停格時配樂與音效要 3 秒內 ≤ −35 LUFS）
    {"id": "sfx_gust", "at": f"{L3}.end+5.75", "gain": 0.8},
    {"id": "sfx_gust", "at": f"{L3}.end+10.05", "gain": 0.7},
    {"id": "sfx_gust", "at": f"{L3}.end+14.35", "gain": 0.6},
    {"id": "sfx_gust", "at": f"{L3}.end+18.65", "gain": 0.5},
]
set_line_starts(c, {L1: 0.95, L2: plus(CUT_CORNER, 1.8), L3: f"{L2}.end+0.3", L4: plus(DROOP, 2.75), L5: f"{L4}.end+0.5", L6: f"{L5}.end+0.95"})
c["voStart"] = 0.95
c["tail"] = 1.25
c["setTrack"] = track
c["fx"] = ["FX8"]
cues.append(c)

# ================================================================== 題卡三段（只調時間；起始狀態＝a5_c001 停格）
END_C001 = {
    "ale": slumped_ale(),
    "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "standwatch", "emotion": "worried"},
    "xiaoqing": {"visible": True, "x": 3.75, "z": 2.0, "pose": "worried", "emotion": "worried"},
    "zhezhe": {"visible": True, "x": 3.2, "z": 2.55, "emotion": "worried"},
}
SLEEP_TRACK = [{"do": "sleep", "start": 0, "duration": 0, "to": 1}]
for cid in ("a5_c002", "a5_c003", "a5_c004"):
    o = OLD[cid]
    c = copy.deepcopy(o)
    c["sceneId"] = "a5_gate"
    c["set"] = "a5_gate"
    c["initialState"]["characters"] = copy.deepcopy(END_C001)
    c["initialState"]["stage"]["set"] = 1
    c["initialState"]["stage"]["desat"] = 0.35
    if cid == "a5_c002":
        # 從全景開始拉到台口（從近景直接拉遠，前段畫面縮得太快：光敏）；c001 停格是近景，進題卡時硬切一次
        c["initialState"]["stage"]["camera"] = "a5_wide"
    c["animation"] = slump_anims() + [a for a in o["animation"] if a.get("target") != "ale"]
    c["setTrack"] = copy.deepcopy(SLEEP_TRACK)
    # 只調時間（光敏：鏡頭推移拉長、和舞台燈明暗錯開；回到故事時在燈還暗的時候移動、移完才亮燈）
    for a in c["animation"]:
        if cid == "a5_c002" and a["name"] == "camera.move":
            a["start"] = 1.4
            a["duration"] = 3.4
        if cid == "a5_c002" and a["name"] == "light.dim":
            a["start"] = 2.2
        if cid == "a5_c004" and a["name"] == "camera.move":
            a["params"]["to"] = "a5_wide"
            a["start"] = "a5_c004_01.end+0.5"
            a["duration"] = 4.8
        if cid == "a5_c004" and a["name"] == "light.restore":
            a["start"] = "a5_c004_01.end+4.7"
            a["duration"] = 1.2
    cues.append(c)

# ================================================================== a5_c005 分頭求助
c = base_cue("a5_c005")
c["sceneId"] = "a5_gate"
c["set"] = "a5_gate"
c = finish(c)
M1, M2, M3 = "a5_c005_01", "a5_c005_02", "a5_c005_03"
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_pov_a", "light": 1, "set": 1, "desat": 0.35},
    "characters": {
        "ale": slumped_ale(),
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "standwatch", "emotion": "worried"},
        "xiaoqing": {"visible": True, "x": 3.75, "z": 2.0, "pose": "worried", "emotion": "worried"},
        "zhezhe": {"visible": True, "x": 3.2, "z": 2.55, "emotion": "worried"},
    },
}
c["animation"] = slump_anims() + [
    # 環顧（小宇的視線）：空空的接送區 → 慢慢搖到轉角，只露出導護旗一角
    # （光敏：連續搖鏡改成三個靜止的主觀鏡頭硬切：接送區 → 長椅 → 轉角）
    A("camera.cut", 1.35, 0, None, to="a5_pov_m"),
    A("camera.cut", 2.75, 0, None, to="a5_pov_b"),
    # 雙人：小晴決定去找林老師
    A("camera.cut", f"{M1}.end+1.0", 0, None, to="a5_kids"),
    pose("xiaoqing", f"{M2}.start-0.1", "stand"),
    A("puppet.face", f"{M2}.start", None, "xiaoqing", emotion="neutral"),
    # 小晴往右跑進校園：切到全景再走（人在畫面上小，細格光敏）
    A("camera.cut", f"{M2}.end+0.25", 0, None, to="a5_wide"),
    A("puppet.move", f"{M2}.end+0.5", 2.6, "xiaoqing", "linear", dx=4.2),
    # 小宇中景：確定沒有大人能馬上來，舉起兒童手錶
    A("camera.cut", f"{M2}.end+2.6", 0, None, to="a5_xy"),
    pose("xiaoyu", f"{M3}.start+3.25", "dial"),
    A("puppet.face", f"{M3}.start+3.5", None, "xiaoyu", emotion="neutral"),
]
c["setTrack"] = copy.deepcopy(SLEEP_TRACK) + [{"do": "flagPeek", "start": 0, "duration": 0, "to": 1}]
c["audioId"] = None
c["music"] = [{"id": "music_courage", "at": f"{M2}.start", "loop": True, "fade": 2.0, "gain": 0.8}]
c["sfx"] = [{"id": "sfx_gust", "at": 0.1, "gain": 0.8}, {"id": "sfx_gust", "at": 3.0, "gain": 0.7}, {"id": "sfx_footsteps", "at": f"{M2}.end+0.5", "gain": 0.4}]
set_line_starts(c, {M1: 3.35, M2: f"{M1}.end+1.3", M3: f"{M2}.end+2.85"})
c["voStart"] = 3.35
c["tail"] = 1.2
cues.append(c)

# ================================================================== a5_c006 撥 119
c = base_cue("a5_c006")
c["sceneId"] = "a5_gate"
c["set"] = "a5_gate"
c = finish(c)
N = [f"a5_c006_0{i}" for i in range(1, 6)]
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_xy_close", "light": 1, "set": 1, "desat": 0.35},
    "characters": {
        "ale": slumped_ale(),
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "dial", "emotion": "neutral"},
    },
}
c["animation"] = slump_anims() + [
    A("camera.cut", f"{N[1]}.start-0.2", 0, None, to="a5_xy_deep"),
    A("camera.cut", f"{N[2]}.start-0.2", 0, None, to="a5_xy_close"),
    A("camera.cut", f"{N[3]}.start-0.2", 0, None, to="a5_xy_inside"),
    A("camera.cut", f"{N[4]}.start-0.2", 0, None, to="a5_xy_close"),
    A("puppet.face", f"{N[4]}.end-0.6", None, "xiaoyu", emotion="smile"),
]
track = copy.deepcopy(SLEEP_TRACK) + [{"do": "phone", "start": 0.5, "duration": 0.6, "to": 1}]
for i in (0, 2, 4):
    track.append({"do": "phoneTalk", "start": f"{N[i]}.start", "until": f"{N[i]}.end"})
c["setTrack"] = track
c["audioId"] = None
c["musicLevel"] = 0.5
c["sfx"] = [{"id": "sfx_watch_dial", "at": 0.2, "gain": 1.0}, {"id": "sfx_phone_bed", "at": 1.45, "gain": 0.5}]
set_line_starts(c, {N[0]: 1.55, N[1]: f"{N[0]}.end+0.25", N[2]: f"{N[1]}.end+0.25", N[3]: f"{N[2]}.end+0.25", N[4]: f"{N[3]}.end+0.25"})
c["voStart"] = 1.55
c["tail"] = 1.1
cues.append(c)

# ================================================================== a5_c007 大人接手
c = base_cue("a5_c007")
c["sceneId"] = "a5_gate"
c["set"] = "a5_gate"
c = finish(c)
P1, P2 = "a5_c007_01", "a5_c007_02"
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "a5_wide", "light": 1, "set": 1, "desat": 0.35},
    "characters": {
        "ale": slumped_ale(),
        # 進場一律用 puppet.move 平移（起點在畫面外；沒有走路起伏，細格光敏）
        "chen": {"visible": True, "x": -6.6, "z": 0.62, "pose": "standr", "emotion": "worried", "facing": 1},
        "medic_a": {"visible": True, "x": -6.6, "z": 0.45, "emotion": "neutral"},
        "medic_b": {"visible": True, "x": -6.7, "z": 0.5, "emotion": "neutral"},
        "lin": {"visible": True, "x": 7.45, "z": 1.2, "pose": "standr", "emotion": "worried", "facing": -1},
        "xiaoyu": {"visible": True, "x": 4.35, "z": 1.75, "pose": "dial", "emotion": "neutral"},
        "xiaoqing": {"visible": True, "x": 8.45, "z": 2.05, "pose": "walk_l", "emotion": "worried"},
    },
}
track = copy.deepcopy(SLEEP_TRACK) + [
    {"do": "chenFlag", "start": 0, "to": 1, **FLAG["standr"]},
    # 救護車：聲音先到（7.4 起從遠處開近），切到遠景後才從街角後面出來；停的時間對引擎聲 8.0–9.0 的停車點
    {"do": "ambulance", "start": 8.9, "duration": 6.5, "from": -8.5},
    {"do": "gurney", "start": 15.5, "duration": 2.0, "x0": -6.4, "x1": -4.4, "to": 1},
]
anims = slump_anims() + [
    # 全景：林老師和小晴從右邊跑來、陳伯伯從轉角快步回來（同時，左右各一）
    A("puppet.move", 0.5, 3.4, "lin", "linear", dx=-4.5),
    A("puppet.move", 1.0, 3.2, "xiaoqing", "linear", dx=-3.0),
    A("puppet.move", 0.1, 3.4, "chen", "linear", dx=5.55),
    A("fx.desat", 0.5, 3.0, None, to=0.0),
    chen_pose(3.6, "receive", track),
    pose("lin", 3.95, "crouch"),
    pose("xiaoqing", 4.3, "worried"),
    # 林老師蹲到小宇旁、對著他舉起的手錶接手通話
    A("camera.cut", 4.45, 0, None, to="a5_lin_kids"),
    # 救護車遠景（不特寫擔架上的臉；擔架與救護人員在車後面）
    A("camera.cut", f"{P1}.end+0.3", 0, None, to="a5_amb"),
    # 救護車開近：陳伯伯往右退一步讓出位置（之後在駕駛艙後面、頭肩露出車頂）
    A("puppet.move", 12.3, 1.2, "chen", "sine", dx=0.85),
    A("puppet.move", 15.5, 2.6, "medic_a", "linear", dx=2.2),
    A("puppet.move", 15.7, 2.6, "medic_b", "linear", dx=3.7),
    # 林老師與孩子中景：林老師站起來稱讚
    A("camera.cut", 16.6, 0, None, to="a5_lin_kids2"),
    pose("lin", 16.8, "stand"),
    pose("xiaoqing", 16.95, "stand"),
    A("puppet.face", f"{P2}.end-0.8", None, "xiaoqing", emotion="smile"),
    A("puppet.face", f"{P2}.end-0.6", None, "xiaoyu", emotion="smile"),
    pose("xiaoyu", f"{P2}.start+0.6", "standwatch"),
]
# 救護人員在救護車到之前不在台上：用 puppet.enter 前的位置在畫面外（左外），enter 前看不到
c["animation"] = anims
c["setTrack"] = track
c["audioId"] = None
# M6 漸收：林老師稱讚時就開始淡出（救護車怠速聲還在，對白要清楚）
c["music"] = [{"id": "none", "at": f"{P2}.start+0.2", "fade": 3.5}]
c["sfx"] = [{"id": "sfx_footsteps", "at": 0.5, "gain": 0.45}, {"id": "sfx_ambulance_engine", "at": 7.4, "gain": 0.75}]
set_line_starts(c, {P1: 4.7, P2: 17.2})
c["voStart"] = 4.7
c["tail"] = 1.3
cues.append(c)

# ================================================================== a5_c008 醫院的走廊
c = base_cue("a5_c008")
c["sceneId"] = "a5_hospital"
c["set"] = "a5_hospital"
c = finish(c)
H = [f"a5_c008_0{i}" for i in range(1, 6)]
c["setFade"] = 1.6
c["initialState"] = {
    "stage": {"curtain": "open", "camera": "hosp_wide", "light": 1, "set": 1, "desat": 0},
    "characters": {
        "lin": {"visible": True, "x": -2.65, "z": -0.2, "pose": "sit", "emotion": "smile", "facing": 1},
        "xiaoyu": {"visible": True, "x": -1.55, "z": -0.15, "pose": "sitb", "emotion": "worried", "facing": 1},
        "xiaoqing": {"visible": True, "x": -0.45, "z": -0.12, "pose": "sitb", "emotion": "worried", "facing": 1},
        "ye": {"visible": True, "x": 1.75, "z": 0.9, "pose": "crouch", "emotion": "smile", "facing": 1},
    },
}
c["animation"] = [
    # 林老師坐姿：起始狀態寫 pose "sit" 會被引擎當成分件紙偶的預設姿勢（立牌不換圖），改用 0 秒換姿勢
    A("puppet.pose", 0, 0, "lin", pose="sit"),
    A("camera.move", 1.0, 3.2, None, to="hosp_mid"),
    A("camera.cut", f"{H[1]}.start-0.25", 0, None, to="hosp_kids"),
    A("puppet.face", f"{H[2]}.end+0.25", None, "xiaoqing", emotion="neutral"),
    A("camera.cut", f"{H[3]}.start-0.25", 0, None, to="hosp_mid"),
    A("puppet.face", f"{H[4]}.end-0.5", None, "xiaoyu", emotion="neutral"),
]
c["audioId"] = "music_recovery"
c["sfx"] = []
set_line_starts(c, {H[0]: 1.75, H[1]: f"{H[0]}.end+0.45", H[2]: f"{H[1]}.end+0.35", H[3]: f"{H[2]}.end+0.5", H[4]: f"{H[3]}.end+0.35"})
c["voStart"] = 1.75
c["tail"] = 1.8
cues.append(c)

# ------------------------------------------------------------------ 寫回（暫存檔 → 驗證 → 搬回）
out = {k: v for k, v in src.items() if k != "cues"}
out["set"] = "a5_gate"
out["characters"] = ROSTER
out["_note"] = ("第五幕（G5 第五幕代理排戲；review/G5/a5/scripts/make_a5_cues.py 產生）。景：a5_gate（校門口，app/src/sets/a5_gate.ts＝"
                "gate 建構器＋街角、轉角小朋友、救護車、擔架、電話圖示、阿樂叔叔閉眼）、a5_hospital（醫院走廊，layout.json）。"
                "cue 的 setTrack＝景的程式動作（引擎不讀，景的 update 讀；格式見 a5_gate.ts 與 gate.ts 檔頭）。storyboard 是劇本與節拍表的摘錄，引擎不讀。")
out["cues"] = cues
txt = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
json.loads(txt)
tmp = SRC.with_suffix(".json.tmp")
tmp.write_text(txt, encoding="utf-8")
os.replace(tmp, SRC)
print("寫回", SRC, len(cues), "個 cue")
