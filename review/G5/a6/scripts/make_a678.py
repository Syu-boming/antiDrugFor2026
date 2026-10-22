"""第六幕＋複習＋閉幕段落檔 app/cues/show/a6.json、a7.json、a8.json 的排戲（G5 第六幕代理）。

從底稿備份（review/G5/a6/a{6,7,8}_skeleton_backup.json）讀台詞（編號、說話者、字幕）、題卡資料、查核點、流程欄位、storyboard，
一律保留原樣（只加 line.start 時間錨點），重寫景、名冊站位、起始狀態、動畫、鏡頭、配樂、音效。
a8_c002、a8_c003 是 G4 cue：整個 cue 原樣保留（表演不動）。
寫到暫存檔 → validate_a678.mjs 驗證 → 通過才搬回（其他代理同時在 build）。
用法：/opt/anaconda3/bin/python3 review/G5/a6/scripts/make_a678.py [a6 a7 a8]
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BK = ROOT / "review/G5/a6"
OUT = ROOT / "app/cues/show"


# ───────────────────────────── 小工具 ─────────────────────────────
def an(name, start, duration=None, target=None, ease=None, **params):
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


def ref(line, which="end", off=0.0):
    s = f"{line}.{which}"
    if off:
        s += f"{off:+.2f}"
    return s


def cam(to, start, duration=2.5, ease="sine"):
    return an("camera.move", start, duration, ease=ease, to=to)


def cut(to, start):
    return an("camera.cut", start, 0.01, to=to)


def pose(target, start, p):
    return an("puppet.pose", start, 0.24, target=target, pose=p)


def face(target, start, emotion):
    return an("puppet.face", start, target=target, emotion=emotion)


def sfx(id_, at, gain=1.0):
    return {"id": id_, "at": at, "gain": gain}


def music(id_, at, fade=1.5, gain=1.0, loop=True):
    return {"id": id_, "at": at, "loop": loop, "fade": fade, "gain": gain}


def ch(x, z, facing=1, pose_=None, emotion="smile", **kw):
    d = {"visible": True, "x": x, "z": z, "facing": facing, "emotion": emotion}
    if pose_:
        d["pose"] = pose_
    d.update(kw)
    return d


def stage(camera, **kw):
    d = {"curtain": "open", "camera": camera, "light": 1}
    d.update(kw)
    return d


def set_line_start(cue, line_id, start):
    for l in cue["lines"]:
        if l["id"] == line_id:
            l["start"] = start
            return
    raise KeyError(line_id)


STR3 = ["wrist", "elbow", "knee"]
OFF = 40.0     # 台外（cue 裡之後才上台的角色先放在畫面外，暗場時移進來）


# ───────────────────────────── 第六幕 ─────────────────────────────
A6_ROSTER = {
    "ale": {"name": "阿樂叔叔", "rig": "ale_v03", "x": -2.6, "z": 0, "facing": 1, "fallback": "adult"},
    "xiaoqing": {"name": "小晴", "rig": "standee:xiaoqing", "x": -1.5, "z": 0.85, "facing": 1, "fallback": "child"},
    "xiaoyu": {"name": "小宇", "rig": "standee:xiaoyu", "x": -0.75, "z": 0.55, "facing": 1, "fallback": "child"},
    "zhezhe": {"name": "折折", "rig": "zhezhe", "x": -2.1, "z": 1.55, "facing": 1, "fallback": "child"},
    "pinan": {"name": "品安", "rig": "standee:pinan", "x": 0.45, "z": 0.4, "facing": 1, "fallback": "child"},
    "lin": {"name": "林老師", "rig": "standee:lin", "x": 5.3, "z": 0.15, "facing": -1, "fallback": "adult"},
    "ye": {"name": "葉護理師", "rig": "standee:ye", "x": 6.55, "z": -0.05, "facing": -1, "fallback": "adult"},
    "chen": {"name": "陳伯伯", "rig": "standee:chen", "x": -5.1, "z": 0.45, "facing": -1, "fallback": "adult"},
    "aqin": {"name": "阿琴阿姨", "rig": "standee:aqin", "x": -2.75, "z": 0.5, "facing": 1, "fallback": "adult"},
}
# 燈籠架後的角落（a6_c002–a6_c006 開頭）
SEC = {"xiaoqing": (1.0, 0.45), "xiaoyu": (1.85, 0.05), "pinan": (2.7, 0.3), "zhezhe": (2.3, 1.05)}
# 求助站（a6_c006 走到之後；帳篷景片 x 5.55，林老師、葉護理師站在帳篷前）
TENT = {"xiaoqing": 3.85, "xiaoyu": 4.45, "pinan": 5.05, "zz": [3.65, 0, 1.45], "lin": 5.75, "ye": 6.5}
# 題卡模式折折全劇統一位置（主線補充裁定，G5 第二批修正第 1 輪）
ZQ = {"visible": True, "x": -4.7, "y": 0, "z": 4.15}
ZQ_POS = [-4.7, 0, 4.15]


def secret_chars(xy_pose="standwatch_m", emo_kids="neutral", pinan_emo="worried", zz=None, zz_emo="curious", plaza=True):
    """燈籠架後的角落：小晴（左，朝右）、小宇（中，朝右）、品安（右，朝左看著兩人）"""
    d = {
        "pinan": ch(*SEC["pinan"], 1, "stand", pinan_emo),
        "xiaoyu": ch(*SEC["xiaoyu"], 1, xy_pose, emo_kids),
        "xiaoqing": ch(*SEC["xiaoqing"], 1, "stand", emo_kids),
        "zhezhe": dict(zz, emotion=zz_emo) if zz else {"visible": True, "x": SEC["zhezhe"][0], "z": SEC["zhezhe"][1], "emotion": zz_emo},
    }
    if plaza:   # 廣場上糊紙的大人（在燈籠架角落的鏡頭外；題卡大全景看得到）
        d["chen"] = ch(-5.1, 0.45, -1, "receive", "smile")
        d["aqin"] = ch(-2.75, 0.5, 1, None, "smile")
    return d


def quiz_in(line1, sfx_list):
    """進題卡（主線更正裁定 08:0x）：全畫面亮度差大，不硬切 → 0.6 秒漸暗、全暗時切到 quiz 鏡位並把舞台燈設成 0.55、0.6 秒漸亮；
    鏡頭不動之後折折收聲、說「最後一題」（≥1.4 秒），說完才摺開題卡、DOM 題卡 0.7 秒淡入（不和亮度變化疊在同一秒）"""
    anims = [
        an("fade.out", 0.0, 0.6),
        an("light.dim", 0.61, 0.03, to=0.55),
        cut("quiz", 0.65),
        an("fade.in", 0.68, 0.6),
        an("zhezhe.hush", 0.0, 1.4, "zhezhe"),          # 收聲（對 sfx_quiet_fold at 0；音效 2.8 秒，出題句 1.7 秒才開始）
        an("zhezhe.emote", 1.45, target="zhezhe", emotion="happy"),
        an("zhezhe.fold", ref(line1, "end", 0.05), 1.2, "zhezhe", form="card"),
        an("quiz.show", ref(line1, "end", 0.6), 0.7),
        an("zhezhe.fold", ref(line1, "end", 1.35), 0.7, "zhezhe", form="idle"),
    ]
    sfx_list[:] = [sfx("sfx_quiet_fold", 0.0, 0.8), sfx("sfx_card_in", ref(line1, "end", 0.6), 0.8)]
    return anims


def a6(cues):
    C = {c["id"]: c for c in cues}

    # a6_c001 燈節的晚上：大全景（鎮民一起糊紙、主燈一片一片糊上）→ 硬切孩子說話 → 硬切品安近景（抓著背帶不說話）
    c = C["a6_c001"]
    c["set"] = c["sceneId"] = "a6_square_night"
    c["initialState"] = {"stage": stage("a6_wide"), "characters": {
        "chen": ch(-5.1, 0.45, -1, "receive"),
        "aqin": ch(-2.75, 0.5, 1),
        "xiaoqing": ch(-1.85, 0.85, 1, "stand_m"),
        "xiaoyu": ch(-1.15, 0.55, 1, "standwatch"),
        "pinan": ch(0.75, 0.4, 1, "stand", "worried"),
        "zhezhe": {"visible": True, "x": -2.1, "z": 1.55, "emotion": "smile"},
    }}
    c["animation"] = [
        an("zhezhe.look", 0.9, 0.6, "zhezhe", yaw=-0.4),
        cam("a6_kids", 0.15, 3.0),          # 大全景 → 孩子：全畫面亮度差約 27%，不硬切（3 秒緩入緩出慢推）
        an("zhezhe.look", ref("a6_c001_01", "start", 0.3), 0.5, "zhezhe", yaw=0.3),
        an("zhezhe.emote", ref("a6_c001_02", "end", 0.1), target="zhezhe", emotion="happy"),
        cut("a6_pinan", ref("a6_c001_02", "end", 0.5)),
        an("puppet.blink", ref("a6_c001_02", "end", 4.2), target="pinan"),
    ]
    c["audioId"] = "music_town_night"
    c["musicLevel"] = 0.5          # 教師停格時配樂 3 秒後 ≤ −35 LUFS（停格＝本值 × HOLD_MUSIC_RATIO）
    c["sfx"] = [sfx("sfx_crowd_far", 0, 0.55)]
    c["voStart"], c["tail"] = 2.4, 5.0

    # a6_c002 品安的秘密：品安拉著小晴、小宇走進燈籠架後的角落（燈籠架框住三人）→ 小聲說秘密
    c = C["a6_c002"]
    c["set"] = c["sceneId"] = "a6_square_night"
    st0 = {"pinan": 1.7, "xiaoyu": 0.8, "xiaoqing": -0.1}       # 起點（品安在前、兩人跟在後面，從畫面左側走進燈籠架角落；走短距離、慢：光敏）
    chars = secret_chars(xy_pose="standwatch_m", plaza=False)
    for k, x in st0.items():
        chars[k]["x"] = x
    c["initialState"] = {"stage": stage("a6_secret"), "characters": chars}
    set_line_start(c, "a6_c002_01", 3.0)
    set_line_start(c, "a6_c002_04", ref("a6_c002_03", "end", 2.6))
    c["animation"] = [
        # 走進來：平移（不加走路起伏）、前後錯開，一次只過一個人
        an("puppet.move", 0.05, 3.6, "pinan", ease="inOut", dx=round(SEC["pinan"][0] - st0["pinan"], 3)),
        an("puppet.move", 0.35, 3.6, "xiaoyu", ease="inOut", dx=round(SEC["xiaoyu"][0] - st0["xiaoyu"], 3)),
        an("puppet.move", 0.65, 3.6, "xiaoqing", ease="inOut", dx=round(SEC["xiaoqing"][0] - st0["xiaoqing"], 3)),
        an("zhezhe.look", 0.6, 0.6, "zhezhe", yaw=-0.3),
        an("zhezhe.look", 2.6, 0.6, "zhezhe", yaw=0.2),
        cam("a6_secret_close", ref("a6_c002_01", "start"), 4.0),
        face("xiaoqing", ref("a6_c002_02", "start", 3.2), "worried"),
        face("xiaoyu", ref("a6_c002_02", "start", 3.45), "worried"),
        cut("a6_secret_pinan", ref("a6_c002_02", "start", 6.6)),
        cut("a6_secret", ref("a6_c002_03", "end", 0.2)),
        pose("xiaoyu", ref("a6_c002_03", "end", 1.0), "standwatch"),      # 小晴、小宇互看（和切鏡錯開：紅外套不在同一秒變三次）
        an("puppet.blink", ref("a6_c002_03", "end", 1.2), target="xiaoqing"),
        an("zhezhe.emote", ref("a6_c002_03", "end", 0.6), target="zhezhe", emotion="worried"),   # 尾巴慢慢收起
        pose("xiaoyu", ref("a6_c002_03", "end", 2.2), "glasses"),          # 推推眼鏡
        an("zhezhe.look", ref("a6_c002_04", "start", -0.4), 0.5, "zhezhe", yaw=0.0),
        # 問完觀眾：折折從左邊出畫（去台口出題；畫面外再滑到題卡位置）
        an("zhezhe.walkTo", ref("a6_c002_04", "end", 0.3), 1.5, "zhezhe", pos=[-3.0, 0, 1.05]),
        an("zhezhe.glideTo", ref("a6_c002_04", "end", 1.9), 0.02, "zhezhe", pos=ZQ_POS),
    ]
    c["audioId"] = "music_town_night"
    c["music"] = [music("none", ref("a6_c002_01", "start", -0.2), 3.0)]
    c["sfx"] = [sfx("sfx_crowd_far", 0, 0.32), sfx("sfx_footsteps", 0.3, 0.3)]
    c["voStart"], c["tail"] = 3.0, 2.0

    # a6_c003–a6_c005 題卡三段：題卡模式折折在統一位置（ZQ）；進出題卡用全暗切換（不硬切、不大幅運鏡）
    for cid in ("a6_c003", "a6_c004", "a6_c005"):
        c = C[cid]
        c["set"] = c["sceneId"] = "a6_square_night"
        st = c["initialState"]["stage"]
        st["camera"] = "a6_secret" if cid == "a6_c003" else "quiz"
        c["initialState"]["characters"] = secret_chars(xy_pose="glasses", emo_kids="worried" if cid == "a6_c003" else "neutral", zz=ZQ)
    c = C["a6_c003"]
    sx = []
    set_line_start(c, "a6_c003_01", 1.7)
    set_line_start(c, "a6_c003_02", ref("a6_c003_01", "end", 1.3))
    c["animation"] = quiz_in("a6_c003_01", sx) + [face("xiaoqing", 0.5, "neutral"), face("xiaoyu", 0.5, "neutral")]
    c["sfx"] = sx
    c["voStart"], c["tail"] = 1.7, 1.0

    c = C["a6_c004"]
    c["animation"] = [an("quiz.reveal", 0.3, 0.45), an("zhezhe.emote", 0.2, target="zhezhe", emotion="curious")]

    c = C["a6_c005"]
    L = "a6_c005_01"
    c["animation"] = [
        an("lamp.light", 0.3, 1.5, index=8),
        an("zhezhe.emote", 0.2, target="zhezhe", emotion="happy"),
        an("quiz.hide", ref(L, "end", 0.3), 0.7),
        # 回故事：題卡收完 → 0.6 秒漸暗 → 全暗時切回燈籠架角落、舞台燈恢復、折折回到孩子腳邊 → 0.6 秒漸亮
        an("fade.out", ref(L, "end", 1.1), 0.6),
        an("light.restore", ref(L, "end", 1.71), 0.03),
        cut("a6_secret_c6", ref(L, "end", 1.75)),     # 比 a6_secret 往左一點：帳篷前的林老師在畫面外
        an("zhezhe.glideTo", ref(L, "end", 1.75), 0.02, "zhezhe", pos=[SEC["zhezhe"][0], 0, SEC["zhezhe"][1]]),
        an("zhezhe.emote", ref(L, "end", 1.76), target="zhezhe", emotion="neutral"),
        face("xiaoqing", ref(L, "end", 1.76), "smile"),
        face("xiaoyu", ref(L, "end", 1.76), "smile"),
        an("fade.in", ref(L, "end", 1.8), 0.6),
    ]
    c["voStart"], c["tail"] = 1.9, 2.5

    # a6_c006 我在乎你：燈籠架角落 → 三人往右走、鏡頭跟拍（2.8 秒緩入緩出）→ 帳篷入鏡停住 → 說出來
    c = C["a6_c006"]
    c["set"] = c["sceneId"] = "a6_square_night"
    chars = secret_chars(xy_pose="glasses", emo_kids="smile", zz_emo="neutral", plaza=False)
    chars["lin"] = ch(TENT["lin"], 0.15, -1, "standr", "smile")      # 帳篷前；孩子走到時像立體書一樣立起來（跟拍時不在畫面裡掃過：人頭高對比）
    chars["ye"] = ch(TENT["ye"], -0.05, -1, None, "smile")
    c["initialState"] = {"stage": stage("a6_secret_c6"), "characters": chars}

    def w(off):
        return ref("a6_c006_02", "end", 0.35 + off)
    set_line_start(c, "a6_c006_03", w(5.6))
    set_line_start(c, "a6_c006_06", ref("a6_c006_05", "end", 2.5))
    WALK = 4.7
    c["animation"] = [
        pose("xiaoyu", 0.3, "standwatch_m"),
        an("puppet.move", ref("a6_c006_01", "start", 0.2), 0.8, "xiaoqing", dx=0.25),
        face("pinan", ref("a6_c006_02", "end", 0.05), "neutral"),
        an("zhezhe.emote", ref("a6_c006_02", "end"), target="zhezhe", emotion="happy"),
        # 往右走到求助站（往右＝安全方位）：平移、緩入緩出；鏡頭同時跟拍（人在畫面上幾乎不動、背景慢慢帶過）
        an("puppet.move", w(0.0), WALK, "pinan", ease="inOut", dx=round(TENT["pinan"] - SEC["pinan"][0], 3)),
        an("puppet.move", w(0.1), WALK, "xiaoyu", ease="inOut", dx=round(TENT["xiaoyu"] - SEC["xiaoyu"][0], 3)),
        an("puppet.move", w(0.2), WALK, "xiaoqing", ease="inOut", dx=round(TENT["xiaoqing"] - SEC["xiaoqing"][0] - 0.25, 3)),
        an("zhezhe.walkTo", w(0.1), WALK, "zhezhe", pos=TENT["zz"]),
        cam("a6_follow", w(0.0), WALK + 0.3),              # 跟拍（5 秒緩入緩出、移 2.8 單位：光敏）→ 帳篷入鏡停住
        an("puppet.popup", w(WALK - 0.1), 1.4, "lin"),     # 林老師、葉護理師在帳篷前立起來迎接
        an("puppet.popup", w(WALK + 0.6), 1.4, "ye"),
        # 說出來
        face("pinan", ref("a6_c006_03", "start"), "worried"),
        pose("lin", ref("a6_c006_04", "start", -0.15), "crouch"),
        cam("a6_tent_close", ref("a6_c006_04", "start", 0.2), 3.0),
        # 約 2 秒無台詞：品安抬頭看林老師、回頭看看兩位朋友、肩膀放鬆、輕輕點頭
        face("pinan", ref("a6_c006_05", "end", 0.25), "smile"),
        pose("pinan", ref("a6_c006_05", "end", 0.55), "stand_m"),
        face("xiaoqing", ref("a6_c006_05", "end", 0.8), "smile"),
        face("xiaoyu", ref("a6_c006_05", "end", 0.85), "smile"),
        pose("pinan", ref("a6_c006_05", "end", 1.6), "stand"),
        an("puppet.nod", ref("a6_c006_05", "end", 1.95), 1.0, "pinan"),
        an("puppet.lean", ref("a6_c006_06", "start"), 0.8, "ye", to=0.02),
        # 下一個 cue（a6_c007 廣場中景）比帳篷近景暗約 20%：結尾先把舞台燈慢慢降一點，接縫的硬切亮度相近
        an("light.dim", ref("a6_c006_06", "end", 0.2), 1.0, to=0.84),
    ]
    c["audioId"] = "music_courage"
    c["music"] = []
    c["sfx"] = [sfx("sfx_footsteps", w(0.2), 0.45), sfx("sfx_crowd_far", 0, 0.3)]
    c["voStart"], c["tail"] = 0.8, 1.0

    # a6_c007 八盞燈與主燈：折折在主燈底座上摺成小燈籠 → 漸暗切到台口＋廣場大全景（八盞燈都亮）→ 光流進廣場、主燈柔和亮起、騎樓燈籠一盞接一盞
    #（林老師、葉護理師站在燈籠架前面：架上的燈籠在他們身後，不擋臉）
    c = C["a6_c007"]
    c["set"] = c["sceneId"] = "a6_square_night"
    c["initialState"] = {"stage": stage("a6_plaza"), "characters": {
        "chen": ch(-5.1, 0.45, -1),
        "aqin": ch(-2.75, 0.5, 1),
        "xiaoqing": ch(-1.6, 0.95, 1, "stand_m"),
        "xiaoyu": ch(-0.85, 0.75, 1, "standwatch"),
        "pinan": ch(0.0, 1.0, 1, "stand"),
        "lin": ch(1.05, 1.75, -1, "standr"),
        "ye": ch(2.05, 1.6, -1),
        "zhezhe": {"visible": True, "x": -3.9, "y": 0.78, "z": -0.45, "emotion": "happy"},
    }}
    set_line_start(c, "a6_c007_02", ref("a6_c007_01", "end", 6.6))
    c["animation"] = [
        an("zhezhe.hopTo", 0.45, 0.7, "zhezhe", pos=[-3.9, 0.78, -0.45], height=0.45),
        an("zhezhe.fold", 0.7, 1.4, "zhezhe", form="lantern"),
        an("zhezhe.glow", 2.0, 1.5, "zhezhe", to=1),
        # 後拉到台口全景：全畫面亮度差大 → 0.6 秒漸暗、全暗時切、0.6 秒漸亮（不硬切、不大幅運鏡）
        an("fade.out", ref("a6_c007_01", "end", 0.2), 0.6),
        cut("a6_full", ref("a6_c007_01", "end", 0.82)),
        an("fade.in", ref("a6_c007_01", "end", 0.86), 0.6),
    ]
    c["audioId"] = None
    c["music"] = [music("music_town", ref("a6_c007_01", "end"), 4.0, 1.0)]
    c["sfx"] = [sfx("sfx_fold", 0.75, 0.6), sfx("sfx_crowd_far", 0, 0.4), sfx("sfx_lamp_on", ref("a6_c007_02", "start", -2.8), 0.7)]
    c["voStart"], c["tail"] = 2.0, 1.2

    # a6_c008 四季：固定窗框，不經過黑場（窗外 4.6／9.4／14.2 秒交叉淡換 1.2 秒；新來陪伴的人像立體書一樣立起來）
    #   秋（葉護理師陪回診說話）→ 冬（＋阿琴阿姨陪散步）→ 春（＋孩子們帶折折來）→ 夏：陪伴的人一季一季多起來
    #   操偶線：先鬆垂（張力 0）→ 慢慢變淡到看不見（≥2 秒）→ 看不見之後才脫離（脫離動作本身看不到；不往上抽、不經過頭部）
    c = C["a6_c008"]
    c["set"] = c["sceneId"] = "a6_window"
    K8 = {"xiaoqing": 2.25, "xiaoyu": 3.0, "pinan": 3.75}
    K8IN = 5.65            # 孩子們走進來的起點（窗框鏡頭右緣外一點點）
    c["initialState"] = {"stage": stage("a6_win"), "characters": {
        "ale": {"visible": True, "x": -0.65, "z": 0.25, "facing": 1, "sit": 0, "strings": STR3, "stringTension": 0.3, "emotion": "neutral"},
        "ye": ch(1.2, 0.4, -1),
        "aqin": ch(-2.65, 0.45, 1),      # 離操偶線遠一點（線鬆時往左弓）
        "xiaoqing": ch(K8["xiaoqing"], 0.6, -1, "stand"),
        "xiaoyu": ch(K8["xiaoyu"], 0.35, -1, "standwatch_m"),
        "pinan": ch(K8["pinan"], 0.2, -1, "stand_m"),
        "zhezhe": {"visible": True, "x": 6.0, "z": 1.3, "emotion": "happy"},
    }}
    c["animation"] = [
        # 秋：回診、說話（線一天一天變鬆）
        an("puppet.lean", 0.6, 1.0, "ye", to=0.025),
        an("strings.loosen", 1.0, 3.0, "ale", anchors=STR3, to=0.0),
        face("ale", 3.0, "smile"),
        # 走進、走出一律平移（不加走路起伏：起伏每秒 3 次以上，近景會超過光敏門檻）、緩入緩出、從畫面邊緣外一點點開始
        # 陪伴一季一季累積（秋：葉護理師 → 冬：＋阿琴阿姨 → 春：＋孩子們和折折），沒有人走出畫面
        #（走出畫面＝兩條腿在同一列格子一秒內進出 4 次，超過光敏門檻）
        an("puppet.lean", 3.6, 1.0, "ye", to=0.0),
        # 冬：阿琴阿姨像立體書一樣在他身邊立起來（窗外 4.6–5.8 秒交叉淡換成冬天）；膝前線變淡到看不見才脫離
        an("puppet.popup", 5.3, 1.6, "aqin"),
        an("strings.fade", 5.6, 2.2, "ale", anchors=["knee"], to=0.0),
        an("strings.fade", 5.6, 2.2, "ale", anchors=["wrist", "elbow"], to=0.55),
        an("strings.detach", 8.0, 0.6, "ale", anchors=["knee"]),
        an("puppet.move", 8.3, 2.0, "ale", ease="inOut", dx=0.6),           # 一起散步幾步
        an("puppet.move", 8.3, 2.0, "aqin", ease="inOut", dx=0.6),
        # 阿琴阿姨留在窗前（家人一直陪著）；窗外 9.4–10.6 秒換成春天
        # 春到夏：孩子們像立體書一樣一個一個立起來（時間跳接；三個人同時走過同一區會超過光敏門檻），折折從右邊跳進來；
        # 肘線變淡到看不見才脫離，手腕的線很淡很鬆
        an("puppet.popup", 10.6, 1.5, "pinan"),
        an("puppet.popup", 11.7, 1.5, "xiaoyu"),
        an("puppet.popup", 12.6, 1.5, "xiaoqing"),
        an("zhezhe.hopTo", 13.0, 1.4, "zhezhe", pos=[1.75, 0, 1.3], height=0.4),
        an("strings.fade", 12.0, 2.2, "ale", anchors=["elbow"], to=0.0),
        an("strings.fade", 12.0, 3.0, "ale", anchors=["wrist"], to=0.35),
        an("strings.detach", 14.4, 0.6, "ale", anchors=["elbow"]),
        an("zhezhe.hopTo", 14.7, 0.8, "zhezhe", pos=[1.45, 0, 1.35], height=0.35),
        an("puppet.chest", 15.6, 1.0, "ale", to=1),
        an("zhezhe.look", 15.8, 0.6, "zhezhe", yaw=-0.35),
    ]
    hide = [an("puppet.move", 0, 0.02, k, dx=OFF) for k in ("ye", "aqin", "xiaoqing", "xiaoyu", "pinan")]
    c["level2"] = {
        "lines": ["a6_c008_03"],
        "voStart": 1.4, "tail": 6.0,
        "animation": hide + [
            an("strings.loosen", 0.3, 1.6, "ale", anchors=STR3, to=0.0),
            an("strings.fade", 1.8, 2.0, "ale", anchors=["knee"], to=0.0),
            an("strings.fade", 1.8, 2.0, "ale", anchors=["wrist", "elbow"], to=0.55),
            an("strings.detach", 3.9, 0.6, "ale", anchors=["knee"]),
            face("ale", 4.0, "smile"),
            an("strings.fade", 4.6, 2.0, "ale", anchors=["elbow"], to=0.0),
            an("strings.fade", 4.6, 2.4, "ale", anchors=["wrist"], to=0.35),
            an("strings.detach", 6.7, 0.6, "ale", anchors=["elbow"]),
        ],
    }
    c["audioId"] = "music_recovery"
    c["music"] = []
    c["sfx"] = []
    c["voStart"], c["tail"] = 3.5, 5.0

    # a6_c009 又到了紙燈節：一年後的燈籠店。阿樂叔叔一摺、一摺摺小折折燈（三個手部循環＝燈籠紙摺三次），
    # 孩子們站在工作台後面圍著看；燈亮時切到手與小燈近景，手腕上最後那根淡線鬆垂、淡到看不見才脫離
    c = C["a6_c009"]
    c["set"] = c["sceneId"] = "a6_shop"
    c["initialState"] = {"stage": stage("a6_shop_mid"), "characters": {
        "ale": {"visible": True, "x": -2.6, "z": 0, "facing": 1, "pose": "sit", "strings": ["wrist"], "stringTension": 0.05, "emotion": "smile", "hand": "grab"},
        "xiaoqing": ch(-1.45, -1.55, -1, "stand", "neutral"),
        "pinan": ch(-0.7, -1.7, -1, "stand_m", "neutral"),
        "xiaoyu": ch(0.05, -1.55, -1, "standwatch_m", "neutral"),
        "zhezhe": {"visible": True, "x": 0.95, "z": 0.75, "emotion": "happy"},
    }}
    L2 = "a6_c009_02"
    fold_t = [ref(L2, "start", 0.9), ref(L2, "start", 3.5), ref("a6_c009_03", "start", 0.9)]
    anim = [
        an("strings.fade", 0, 0.01, "ale", anchors=["wrist"], to=0.35),
        an("zhezhe.look", ref("a6_c009_01", "end", 0.3), 0.6, "zhezhe", yaw=-0.4),
        an("puppet.grab", 0.0, 0.01, "ale", at=[-2.02, 1.47]),
        face("xiaoqing", ref(L2, "end"), "smile"),
        face("pinan", ref("a6_c009_03", "start", 1.0), "smile"),
    ]
    for t0 in fold_t:     # 一個手部循環：手抬起離開紙（0.55 秒）→ 低頭看 → 按下去摺一摺（0.6 秒）
        anim += [
            an("puppet.grab", t0, 0.55, "ale", to=0.62),
            an("puppet.nod", t0, 1.4, "ale", depth=0.8),
            an("puppet.grab", _addref(t0, 0.7), 0.6, "ale", to=1.0),
        ]
    anim += [
        face("xiaoyu", ref("a6_c009_04", "end", 0.2), "smile"),
        an("zhezhe.emote", ref("a6_c009_04", "end", 0.2), target="zhezhe", emotion="happy"),
        # 小折折燈亮起（景：a6_c009_04 結束 +0.35 秒、2 秒漸亮）→ 切手與小燈近景
        cut("a6_shop_hands", ref("a6_c009_04", "end", 0.3)),
        an("strings.loosen", ref("a6_c009_04", "end", 0.6), 1.2, "ale", anchors=["wrist"], to=0.0),
        an("strings.fade", ref("a6_c009_04", "end", 0.8), 2.2, "ale", anchors=["wrist"], to=0.0),
        an("strings.detach", ref("a6_c009_04", "end", 3.1), 0.5, "ale", anchors=["wrist"]),
    ]
    c["animation"] = anim
    c["audioId"] = "music_recovery"
    c["music"] = [music("music_town", ref("a6_c009_04", "start", -0.5), 3.0, 0.85)]
    c["sfx"] = [sfx("sfx_fold", _addref(t, 0.75), 0.4) for t in fold_t] + [sfx("sfx_lamp_on", ref("a6_c009_04", "end", 0.35), 0.6)]
    c["voStart"], c["tail"] = 1.6, 3.5


def _addref(r, off):
    """時間參照加秒數（"a6_c009_02.start+0.9" + 0.7 → "a6_c009_02.start+1.60"）"""
    if isinstance(r, (int, float)):
        return round(r + off, 3)
    import re
    m = re.match(r"^(.*?\.(?:start|end))([+-]\d+(?:\.\d+)?)?$", r)
    base, o = m.group(1), float(m.group(2) or 0)
    return f"{base}{o + off:+.2f}"


# ───────────────────────────── 複習與收束 ─────────────────────────────
# 修正第 1 輪：回到舞台全景（台口＋上方八盞燈入鏡，鏡位 a7_stage）；折折在台口前緣攤卡；三張大卡念到時放大到中央（景 a6_shop.ts 依句子時間算）；
# 口訣卡時鏡頭推近一級（a7_mid），小晴、小宇從兩側台外走進來；最後品安在中間像立體書一樣立起（比兩人前面半步），鏡頭拉回舞台全景、八盞燈入鏡。
A7_ROSTER = {
    "xiaoqing": {"name": "小晴", "rig": "standee:xiaoqing", "x": -9.0, "z": 3.0, "facing": 1, "fallback": "child"},
    "xiaoyu": {"name": "小宇", "rig": "standee:xiaoyu", "x": 9.0, "z": 3.0, "facing": 1, "fallback": "child"},
    "zhezhe": {"name": "折折", "rig": "zhezhe", "x": -2.4, "z": 3.7, "facing": 1, "fallback": "child"},
    "pinan": {"name": "品安", "rig": "standee:pinan", "x": 0.0, "z": 3.4, "facing": 1, "fallback": "child"},
}
ZZ7 = {"start": [-2.4, 0, 3.7], "card2": [-0.75, 0, 2.7], "side": [-5.3, 0, 3.5], "final": [-2.6, 0, 3.75]}
K7 = {"xiaoqing": -4.55, "xiaoyu": 4.6, "wing": 9.0, "q3": -1.15, "y3": 1.15}


def a7(cues):
    C = {c["id"]: c for c in cues}
    c = C["a7_c001"]
    c["set"] = c["sceneId"] = "a6_shop"
    c["setFade"] = 0.8
    c["initialState"] = {"stage": stage("a7_stage"), "characters": {"zhezhe": {"visible": True, "x": ZZ7["start"][0], "z": ZZ7["start"][2], "emotion": "happy"}}}
    set_line_start(c, "a7_c001_01", 2.2)
    set_line_start(c, "a7_c001_02", ref("a7_c001_01", "end", 4.3))
    e1 = "a7_c001_01"
    c["animation"] = [
        an("zhezhe.look", 0.4, 0.6, "zhezhe", yaw=0.4),
        an("zhezhe.look", ref(e1, "start", -0.2), 0.5, "zhezhe", yaw=0.0),
        # 第二張卡倒了（景：e1+1.3 起上下顛倒立起）→ 折折跳過去碰一下（卡片輕跳、顛倒的那面淡出）→ 跳回台口
        an("zhezhe.emote", ref(e1, "end", 1.6), target="zhezhe", emotion="curious"),
        an("zhezhe.hopTo", ref(e1, "end", 1.7), 1.1, "zhezhe", pos=ZZ7["card2"], height=0.4),
        an("zhezhe.emote", ref(e1, "end", 3.0), target="zhezhe", emotion="happy"),
        an("zhezhe.hopTo", ref(e1, "end", 3.0), 1.1, "zhezhe", pos=ZZ7["start"], height=0.4),
        an("zhezhe.look", ref("a7_c001_02", "end", 0.2), 0.6, "zhezhe", yaw=0.3),
    ]
    c["level2"] = {
        "lines": ["a7_c001_03"], "voStart": 1.8, "tail": 2.4,
        "animation": [an("zhezhe.look", 0.4, 0.6, "zhezhe", yaw=0.3), an("zhezhe.emote", 0.5, target="zhezhe", emotion="happy")],
    }
    c["audioId"] = "music_zhezhe"
    c["music"] = [music("music_town", ref("a7_c001_03", "start"), 3.0, 0.75)]
    c["sfx"] = [sfx("sfx_fold", 0.5, 0.5), sfx("sfx_fold", ref(e1, "end", 1.3), 0.5), sfx("sfx_paper_rustle", ref(e1, "end", 2.65), 0.5),
                sfx("sfx_fold", ref("a7_c001_02", "end", 1.0), 0.5)]
    c["voStart"], c["tail"] = 2.2, 1.6

    c = C["a7_c002"]
    c["set"] = c["sceneId"] = "a6_shop"
    c["initialState"] = {"stage": stage("a7_stage"), "characters": {
        "zhezhe": {"visible": True, "x": ZZ7["start"][0], "z": ZZ7["start"][2], "emotion": "happy"},
        "xiaoqing": ch(-K7["wing"], 3.0, 1, "stand"),
        "xiaoyu": ch(K7["wing"], 3.0, 1, "standwatch"),
    }}
    # 一次只動一件事（光敏）：三張卡淡出（景 0.1–1.5 秒）→ 漸暗切到推近一級的鏡位（1.55–2.85 秒）→ 口訣卡立起（景 4.3 秒起）、
    # 兩個孩子從兩側台外走到卡片兩邊（平移、緩入緩出）
    set_line_start(c, "a7_c002_01", 4.0)
    c["animation"] = [
        # 推近一級：全畫面亮度差大（台口外框）→ 0.6 秒漸暗、全暗時切到 a7_mid、0.6 秒漸亮（大幅縮放不運鏡：八盞燈與層架燈籠掃過格子）
        an("fade.out", 1.55, 0.6),
        cut("a7_mid", 2.2),
        an("zhezhe.glideTo", 2.2, 0.02, "zhezhe", pos=ZZ7["side"]),
        an("fade.in", 2.25, 0.6),
        an("puppet.move", 4.4, 3.0, "xiaoqing", ease="inOut", dx=round(K7["xiaoqing"] + K7["wing"], 3)),
        an("puppet.move", 4.6, 3.0, "xiaoyu", ease="inOut", dx=round(K7["xiaoyu"] - K7["wing"], 3)),
    ]
    c["audioId"] = None
    c["music"] = [music("music_courage", 0, 1.5, 0.6)]
    c["sfx"] = [sfx("sfx_paper_rustle", 0.1, 0.4), sfx("sfx_card_in", 4.3, 0.6), sfx("sfx_footsteps", 4.6, 0.3)]
    c["voStart"], c["tail"] = 4.0, 1.4

    c = C["a7_c003"]
    c["set"] = c["sceneId"] = "a6_shop"
    c["initialState"] = {"stage": stage("a7_mid"), "characters": {
        "zhezhe": {"visible": True, "x": ZZ7["side"][0], "z": ZZ7["side"][2], "emotion": "happy"},
        "xiaoqing": ch(K7["xiaoqing"], 3.0, 1, "stand"),
        "xiaoyu": ch(K7["xiaoyu"], 3.0, 1, "standwatch"),
        "pinan": ch(0.0, 3.4, 1, "stand", "smile"),
    }}
    # 收聲 → 口訣卡淡出 → 小晴、小宇往中間走 → 品安在兩人中間、前面半步立起來 → 說完鏡頭拉回舞台全景（八盞燈入鏡）→ 折折謝謝大家
    set_line_start(c, "a7_c003_01", 4.3)
    set_line_start(c, "a7_c003_02", ref("a7_c003_01", "end", 0.9))
    c["animation"] = [
        an("zhezhe.hush", 0.0, target="zhezhe"),
        an("puppet.move", 0.8, 3.9, "xiaoqing", ease="inOut", dx=round(K7["q3"] - K7["xiaoqing"], 3)),
        an("puppet.move", 1.0, 3.9, "xiaoyu", ease="inOut", dx=round(K7["y3"] - K7["xiaoyu"], 3)),
        an("zhezhe.walkTo", 1.5, 2.6, "zhezhe", pos=ZZ7["final"]),
        an("puppet.popup", 2.7, 1.5, "pinan"),
        # 拉回舞台全景（八盞燈入鏡）：亮度差大 → 漸暗、全暗時切、漸亮（不大幅運鏡）
        an("fade.out", ref("a7_c003_01", "end", 0.05), 0.6),
        cut("a7_stage", ref("a7_c003_01", "end", 0.7)),
        an("fade.in", ref("a7_c003_01", "end", 0.75), 0.6),
        an("zhezhe.look", ref("a7_c003_02", "start", -0.3), 0.5, "zhezhe", yaw=0.0),
    ]
    c["audioId"] = None
    c["music"] = [music("none", 0, 0.8), music("music_town", ref("a7_c003_02", "start"), 3.0, 0.75)]
    c["sfx"] = [sfx("sfx_quiet_fold", 0.55)]
    c["voStart"], c["tail"] = 4.3, 0.5


# ───────────────────────────── 閉幕 ─────────────────────────────
# 謝幕站位＝a8_c002（G4 閉幕）的起始站位（名冊）；阿樂叔叔最後坐回工作台前（a8_c002 起始 pose:sit）
A8_ROSTER = {
    "ale": {"name": "阿樂叔叔", "rig": "ale_v03", "x": -2.6, "z": 0, "facing": 1, "fallback": "adult"},
    "xiaoqing": {"name": "小晴", "rig": "standee:xiaoqing", "x": 3.1, "z": 0.65, "facing": -1, "fallback": "child"},
    "xiaoyu": {"name": "小宇", "rig": "standee:xiaoyu", "x": 2.0, "z": 0.35, "facing": 1, "fallback": "child"},
    "zhezhe": {"name": "折折", "rig": "zhezhe", "x": -0.6, "z": 1.6, "facing": 1, "fallback": "child"},
    "pinan": {"name": "品安", "rig": "standee:pinan", "x": 0.9, "z": 0.6, "facing": 1, "fallback": "child"},
    "lin": {"name": "林老師", "rig": "standee:lin", "x": -4.3, "z": 0.8, "facing": -1, "fallback": "adult"},
    "ye": {"name": "葉護理師", "rig": "standee:ye", "x": 4.6, "z": 0.3, "facing": -1, "fallback": "adult"},
    "chen": {"name": "陳伯伯", "rig": "standee:chen", "x": -5.3, "z": 0.5, "facing": -1, "fallback": "adult"},
}
# 鞠躬（分件紙偶不換圖：puppet.nod 加大幅度＝以腳底為支點前傾約 14°、上身微縮；同一張圖、同一比例）
BOW_DEPTH, BOW_DUR = 5.0, 1.7
#   陳伯伯和林老師（從左邊台外走進來）→ 葉護理師（從右邊走進來）→ 阿樂叔叔（站起來、捧著小折折燈）→ 品安、小宇、小晴（像立體書一樣一個一個立起來）
#   → 折折（跳到前面鞠躬、說再見）→ 全體一起鞠躬（music_bows 最後和弦 15 秒）
BOW = {"chen": 3.6, "lin": 3.7, "ye": 5.2, "pinan": 9.0, "xiaoyu": 10.0, "xiaoqing": 11.0}
WALK_IN = {"chen": (-2.4, 0.05), "lin": (-2.4, 0.2), "ye": (3.6, 1.6)}   # (dx 起點偏移, 開始時間)
POP = {"pinan": 7.6, "xiaoyu": 8.6, "xiaoqing": 9.6}
#   鏡頭固定在謝幕中景（show_mid＝a8_c002 起點）。台口八盞燈：a7_c003 結尾的舞台全景（換景漸暗前）入鏡；
#   a8_c002 是 G4 cue（表演不改，鏡位 g4_stage 看不到燈），布幕合上前的八盞燈要主線決定是否改 a8_c002 的鏡位
REST = {"chen": "stand", "lin": "stand", "ye": "stand", "pinan": "stand", "xiaoyu": "stand", "xiaoqing": "stand"}
ALE = {"stand": 5.5, "bow": 7.2, "sit": 16.75}


def a8(cues):
    C = {c["id"]: c for c in cues}
    c = C["a8_c001"]
    c["set"] = c["sceneId"] = "a6_shop"
    c["setFade"] = 1.0
    chars = {}
    for cid in ("chen", "lin", "ye", "pinan", "xiaoyu", "xiaoqing"):
        r = A8_ROSTER[cid]
        x = r["x"] + (WALK_IN[cid][0] if cid in WALK_IN else 0)
        chars[cid] = ch(x, r["z"], r["facing"], REST[cid])
    chars["ale"] = {"visible": True, "x": -2.6, "z": 0, "facing": 1, "pose": "sit", "emotion": "smile"}
    chars["zhezhe"] = {"visible": True, "x": A8_ROSTER["zhezhe"]["x"], "z": A8_ROSTER["zhezhe"]["z"], "emotion": "happy"}
    c["initialState"] = {"stage": stage("show_mid"), "characters": chars}
    anim = []
    for cid, (dx, t0) in WALK_IN.items():      # 從台外走進來（平移、緩入緩出：不加走路起伏）
        anim.append(an("puppet.move", t0, 3.2, cid, ease="inOut", dx=-dx))
    for cid, t0 in POP.items():
        anim.append(an("puppet.popup", t0, 1.3, cid))
    for cid, t in BOW.items():
        anim.append(an("puppet.nod", t, BOW_DUR, cid, depth=BOW_DEPTH))
    zz_front = [A8_ROSTER["zhezhe"]["x"], 0, 2.5]
    anim += [
        # 阿樂叔叔：站起來 → 拿起小折折燈捧在胸前（景 a6_shop.ts 依這幾個時間把燈移到手上）→ 點頭鞠躬 → 全體鞠躬 → 放回桌上、坐回去
        face("ale", ALE["stand"] - 0.2, "greet"),
        an("puppet.sit", ALE["stand"], 1.0, "ale", to=0.0),
        an("puppet.chest", ALE["stand"] + 0.8, 0.8, "ale", to=1.0),     # 拿起小折折燈捧在胸前
        an("puppet.nod", ALE["bow"], BOW_DUR, "ale", depth=2.2),
        face("ale", ALE["bow"] + 1.8, "smile"),
        an("zhezhe.emote", 3.6, target="zhezhe", emotion="happy"),
        an("zhezhe.hopTo", 12.6, 0.8, "zhezhe", pos=zz_front, height=0.4),
        an("zhezhe.hush", 13.0, target="zhezhe"),                 # 折折的鞠躬（耳朵壓低、身體縮一下）
        an("zhezhe.emote", 13.9, target="zhezhe", emotion="proud"),
    ]
    for cid in BOW:
        anim.append(an("puppet.nod", 15.0, BOW_DUR, cid, depth=BOW_DEPTH))
    anim += [
        an("puppet.nod", 15.0, BOW_DUR, "ale", depth=2.2),
        an("zhezhe.hush", 15.0, target="zhezhe"),
        an("puppet.chest", ALE["sit"] - 0.6, 0.6, "ale", to=0.0),
        an("puppet.sit", ALE["sit"], 1.0, "ale", to=1.0),
        an("zhezhe.hopTo", 16.9, 0.8, "zhezhe", pos=[A8_ROSTER["zhezhe"]["x"], 0, A8_ROSTER["zhezhe"]["z"]], height=0.3),
        an("zhezhe.emote", 16.9, target="zhezhe", emotion="happy"),      # 和 a8_c002 起始（smile＝happy）一致
    ]
    c["animation"] = anim
    # 2 級短版（約 8 秒）：全體一起鞠躬一次（大家已經在台上；阿樂叔叔坐著點頭）
    lvl2 = [an("puppet.move", 0, 0.01, cid, dx=-dx) for cid, (dx, _) in WALK_IN.items()]
    for cid in BOW:
        lvl2.append(an("puppet.nod", 4.6, BOW_DUR, cid, depth=BOW_DEPTH))
    lvl2 += [an("puppet.nod", 4.6, BOW_DUR, "ale", depth=2.2), an("zhezhe.hush", 4.6, target="zhezhe")]
    c["level2"] = {"voStart": 1.0, "tail": 3.95, "minDuration": 8.0, "animation": lvl2}
    c["audioId"] = "music_bows"
    c["musicLoop"] = False
    c["music"] = []
    c["sfx"] = []
    c["voStart"], c["tail"] = 13.4, 1.55


# ───────────────────────────── 寫檔 ─────────────────────────────
LOCK = ("kind", "next", "prevStable", "teacherNote", "checkpoint", "quiz", "lamp", "compression", "skippable")


def finish(seg, data, roster, file_set, note):
    before = json.loads((BK / f"{seg}_skeleton_backup.json").read_text())
    B = {c["id"]: c for c in before["cues"]}
    data["characters"] = roster
    data["set"] = file_set
    data["_note"] = note
    for c in data["cues"]:
        b = B[c["id"]]
        for k in LOCK:
            assert json.dumps(c.get(k), ensure_ascii=False) == json.dumps(b.get(k), ensure_ascii=False), f"{c['id']} 鎖定欄位 {k} 被改了"
        strip = lambda ls: [{k: v for k, v in l.items() if k != "start"} for l in ls]   # noqa: E731
        assert strip(c["lines"]) == strip(b["lines"]), f"{c['id']} 台詞被改了"
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    tmp = Path(name)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    tmp.write_text(text, encoding="utf-8")
    r = subprocess.run(["node", str(HERE / "validate_a678.mjs"), seg, str(tmp)], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        print(f"驗證失敗，{seg}.json 不動；暫存檔：", tmp)
        return False
    (OUT / f"{seg}.json").write_text(text, encoding="utf-8")
    tmp.unlink()
    print("已寫入", OUT / f"{seg}.json")
    return True


NOTE = ("G5 第六幕代理排戲（review/G5/a6/scripts/make_a678.py 產生；台詞、題卡、流程欄位、storyboard 照底稿）。景："
        "a6_square_night（紙燈節晚上的廣場，app/src/sets/a6_square_night.ts）、a6_window（四季窗景）、a6_shop（一年後的燈籠店、複習紙卡、謝幕；"
        "G4 燈籠店＋程式景片）。storyboard 是劇本與節拍表的摘錄，引擎不讀。")


def main():
    segs = sys.argv[1:] or ["a6", "a7", "a8"]
    ok = True
    if "a6" in segs:
        d = json.loads((BK / "a6_skeleton_backup.json").read_text())
        a6(d["cues"])
        ok &= finish("a6", d, A6_ROSTER, "a6_square_night", NOTE)
    if "a7" in segs:
        d = json.loads((BK / "a7_skeleton_backup.json").read_text())
        a7(d["cues"])
        ok &= finish("a7", d, A7_ROSTER, "a6_shop", NOTE)
    if "a8" in segs:
        d = json.loads((BK / "a8_skeleton_backup.json").read_text())
        a8(d["cues"])
        ok &= finish("a8", d, A8_ROSTER, "a6_shop", NOTE + " a8_c002、a8_c003 是 G4 cue，原樣保留（a8_c002 的景＝本段的 a6_shop，畫面＝G4 燈籠店）。")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
