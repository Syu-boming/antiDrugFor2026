"""第四幕段落檔 app/cues/show/a4.json 的排戲（G5 第四幕代理）。

讀現有 a4.json，台詞（編號、說話者、字幕）、題卡資料、查核點、流程欄位、storyboard 一律保留原樣，
只重寫景、名冊站位、起始狀態、動畫、鏡頭、配樂、音效與 setTrack（景的程式動作，見 app/src/sets/gate.ts、a4_roadmap.ts 檔頭）。
寫到暫存檔 → 用 validate.ts 驗證 → 通過才搬回（其他代理同時在 build）。
用法：/opt/anaconda3/bin/python3 review/G5/a4/scripts/make_a4_cues.py
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "app/cues/show/a4.json"

# ---------------------------------------------------------------- 站位（世界座標；gate 景：x 向右、z 朝觀眾；接送線 x +1.6）
ALE_TRUCK = {"x": -6.3, "z": -1.95}          # 小貨車駕駛座門前（扶著車門）
DOOR = [-5.6, 1.42]                            # 車門前緣（B 側手扶的位置）
QG0, XY0 = {"x": 2.35, "z": 2.0}, {"x": 3.1, "z": 1.75}     # 孩子：接送線後
STEP = 0.25                                     # a4_c008 各退半步
QG1, XY1 = {"x": QG0["x"] + STEP, "z": QG0["z"]}, {"x": XY0["x"] + STEP, "z": XY0["z"]}
WALK = 1.0                                      # a4_c012 走到警衛室門口
QG_STEP12 = 0.15
QG2 = {"x": QG1["x"] + QG_STEP12 + WALK, "z": QG0["z"]}
XY2 = {"x": XY1["x"] + WALK, "z": XY0["z"]}
LIN2 = {"x": 5.45, "z": -0.25}
CHEN_X = {"c001": -1.4, "c012": 2.0}
BENCH_ALE = {"x": -2.65, "z": 0.3}
CHEN_BENCH = {"x": -0.95, "z": 0.62}
ZZ_C008 = [3.05, 0, 2.6]

STRINGS = ["wrist", "elbow", "knee"]


def ale(**kw):
    d = {"visible": True, "emotion": "confused", "strings": STRINGS, "stringTension": 0.18, "sit": 0}
    d.update(kw)
    return d


def kid(pos, pose="stand", emotion="neutral", **kw):
    d = {"visible": True, "x": pos["x"], "z": pos["z"], "pose": pose, "emotion": emotion}
    d.update(kw)
    return d


def an(name, start, duration=None, target=None, **params):
    a = {"name": name, "start": start}
    if duration is not None:
        a["duration"] = duration
    if target:
        a["target"] = target
    if params:
        a["params"] = params
    return a


def cam(to, start, duration=2.5, cut=False):
    return an("camera.cut" if cut else "camera.move", start, 0 if cut else duration, to=to)


def tr(do, start=0, duration=0, **kw):
    d = {"do": do, "start": start, "duration": duration}
    d.update(kw)
    return d


def sfx(id_, at, gain=1.0):
    return {"id": id_, "at": at, "gain": gain}


def music(id_, at, fade=1.5, gain=1.0, loop=True):
    return {"id": id_, "at": at, "loop": loop, "fade": fade, "gain": gain}


# 小車：路線點序號（app/src/sets/a4_roadmap.ts ACTUAL）
CAR_FROZEN = 11
MAP_STATE = [tr("plan", to=1), tr("car", keys=[[0, CAR_FROZEN]])]
SIL_STATE = MAP_STATE + [tr("screen", to=1), tr("glow", to=1), tr("spot", target="all", to=0.8)]


def stage(camera, light=1, **kw):
    d = {"curtain": "open", "camera": camera, "light": light, "set": 1}
    d.update(kw)
    return d


def build(cues):
    C = {c["id"]: c for c in cues}

    # ============================================================ a4_c001 校門口
    c = C["a4_c001"]
    L1, L2 = "a4_c001_01", "a4_c001_02"
    cut1 = f"{L1}.start+5.3"         # 「叔叔的頭腦受到影響」：切到隔著馬路的阿樂叔叔（他剛下車）
    cut2 = f"{L1}.start+10.0"        # 「林老師的電話也還沒打通」：孩子在接送線後、警衛室窗裡的小背影
    cut3 = f"{L1}.end+0.15"          # 阿樂叔叔叫孩子
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 1.4, "tail": 3.0,
        "initialState": {"stage": stage("a4_gate_wide"), "characters": {
            "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1),
            "chen": {"visible": True, "x": CHEN_X["c001"], "z": 0.15, "emotion": "neutral"},
            "xiaoqing": kid(QG0), "xiaoyu": kid(XY0),
        }},
        "animation": [
            # 阿樂叔叔剛下車（在大全景裡還在車上：切鏡頭那一格才出現）
            an("puppet.popup", f"{L1}.start+5.29", 0.005, "ale"),
            an("puppet.grab", f"{L1}.start+5.29", 0.005, "ale", at=DOOR),
            an("puppet.kneeTug", f"{L1}.start+7.0", 3.2, "ale", at=DOOR),
            an("strings.loosen", f"{L1}.start+10.6", 1.4, "ale", anchors=["knee"], to=0.22),
            an("puppet.waveTry", f"{L2}.start+0.9", 3.4, "ale", greet="greet", emotion="confused"),
            an("strings.loosen", f"{L2}.end+0.25", 1.4, "ale", anchors=["wrist", "elbow"], to=0.3),
            an("puppet.blink", f"{L2}.end+0.3", None, "ale"),
            cam("a4_across", cut1, cut=True),
            cam("a4_across_push", f"{L1}.start+5.4", 4.4),
            cam("a4_window", cut2, cut=True),
            cam("a4_across", cut3, cut=True),
            cam("a4_across_push", f"{L2}.start+0.2", 4.5),
        ],
        "audioId": "music_town",
        "music": [music("music_m4_light", f"{L1}.start+4.6", fade=3.0)],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.7), sfx("sfx_ambulance_engine", f"{L1}.start+0.9", 0.28),
                sfx("sfx_string_taut", f"{L2}.start+2.7", 0.7)],
        "setTrack": [
            tr("lin", to=1), tr("flag", to=1), tr("key", hold="ale.A"),
            tr("walkers", 0, 7.0, kind="a", x0=-1.0, x1=14.0, z=-2.85),
            tr("walkers", 1.0, 8.0, kind="b", x0=-3.6, x1=13.0, z=-2.95),
            tr("truck", f"{L1}.start+1.0", 4.6, **{"from": -9.5}),
            tr("wind", to=0.25),
        ],
    })

    # ============================================================ a4_c002 不對勁 → 街道摺平成地圖
    c = C["a4_c002"]
    L1, L2, L3 = "a4_c002_01", "a4_c002_02", "a4_c002_03"
    for l in c["lines"]:
        if l["id"] == L3:
            l["start"] = f"{L2}.end+1.1"
    f0 = f"{L3}.end+0.15"            # 摺成紙飛機
    f0s = f"{L3}.end+0.75"            # 摺紙聲（摺痕）
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 0.8, "tail": 0.9,
        "initialState": {"stage": stage("a4_kids"), "characters": {
            "xiaoqing": kid(QG0, pose="worried", emotion="worried"),
            "xiaoyu": kid(XY0, emotion="worried"),
            "zhezhe": {"visible": True, "x": 2.5, "z": 1.6, "emotion": "curious"},
        }},
        "animation": [
            an("puppet.tilt", f"{L1}.start+0.2", 0.6, "xiaoyu", to=0.03),
            cam("a4_kids_qg", f"{L1}.start-0.2", 2.2),
            cam("a4_kids_xy", f"{L2}.start-0.3", 1.9),
            cam("a4_kids_z2", f"{L2}.end+0.05", 1.7),
            # 折折從小晴的筆記本後面探出頭（跳到兩人中間前面）
            an("zhezhe.hopTo", f"{L2}.end+0.15", 0.75, "zhezhe", pos=[2.75, 0, 2.6], height=0.55),
            an("zhezhe.emote", f"{L2}.end+0.9", None, "zhezhe", emotion="worried"),
            an("zhezhe.emote", f"{L3}.start+0.9", None, "zhezhe", emotion="curious"),
            an("zhezhe.fold", f0, 2.4, "zhezhe", form="plane"),
            # 紙飛機飛出畫面上緣 → 切到天空（鏡頭不掃過整條街：光敏）→ 切到高處看街道摺平
            an("zhezhe.flyTo", f"{L3}.end+2.45", 2.6, "zhezhe", pos=[-0.5, 9.8, -1.2], height=1.0),
            cam("a4_up", f"{L3}.end+3.6", cut=True),
            cam("a4_fold_high", f"{L3}.end+5.1", cut=True),
            an("set.fold", f"{L3}.end+5.2", 2.2),
            cam("a4_map_top", f"{L3}.end+7.5", 2.0),
            an("set.swap", f"{L3}.end+9.7", 0, set="a4_roadmap"),
            an("set.popup", f"{L3}.end+9.8", 2.3),
            cam("a4_map", f"{L3}.end+9.95", 2.6),
        ],
        "audioId": None,
        "music": [music("music_road", f"{L3}.end+3.2", fade=2.5, gain=0.9)],
        "sfx": [sfx("sfx_fold", f0s, 0.9), sfx("sfx_plane_whoosh", f"{L3}.end+2.55", 0.8),
                sfx("sfx_paper_rustle", f"{L3}.end+5.2", 0.8), sfx("sfx_paper_rustle", f"{L3}.end+6.3", 0.7),
                sfx("sfx_paper_rustle", f"{L3}.end+9.85", 0.8)],
        "setTrack": [tr("map", f"{L3}.end+8.0", 1.6, to=1), tr("key", hold="ale.A"),
                     tr("plan", to=0), tr("car", keys=[[0, 0]])],
    })

    # ============================================================ a4_c003 紙上的路
    c = C["a4_c003"]
    L1, L2 = "a4_c003_01", "a4_c003_02"
    c.update({
        "set": "a4_roadmap", "sceneId": "a4_roadmap", "voStart": 1.6, "tail": 2.6,
        "initialState": {"stage": stage("a4_map"), "characters": {}},
        "animation": [
            cam("a4_map_cross", f"{L2}.start+0.9", 3.6),
            an("light.dim", f"{L2}.start+5.3", 1.2, to=0.82),
        ],
        "audioId": None,
        "music": [music("none", f"{L2}.start+5.2", fade=0.7)],
        "sfx": [],
        "setTrack": [
            tr("plan", 0.3, 1.7, to=1, ease="linear"),
            tr("car", keys=[[0, 0], [f"{L1}.start+0.9", 0], [f"{L1}.start+2.8", 1.0], [f"{L1}.start+4.6", 2.0], [f"{L2}.start-0.3", 3.3],
                            [f"{L2}.start+0.35", 4.0], [f"{L2}.start+1.5", 5.5], [f"{L2}.start+2.6", 7.0], [f"{L2}.start+3.6", 8.4],
                            [f"{L2}.start+4.35", 9.5], [f"{L2}.start+4.85", 10.3], [f"{L2}.start+5.25", CAR_FROZEN]]),
        ],
    })

    # ============================================================ a4_c004 同一條路上的人（背光剪影）
    c = C["a4_c004"]
    L1, L2 = "a4_c004_01", "a4_c004_02"
    c.update({
        "set": "a4_roadmap", "sceneId": "a4_roadmap", "voStart": 4.5, "tail": 2.4,
        "initialState": {"stage": stage("a4_map_cross", light=0.82), "characters": {}},
        "animation": [
            cam("a4_sil", 0.3, cut=True),
            an("light.dim", 3.0, 1.8, to=0.36),
        ],
        "audioId": None,
        "music": [music("music_road", 0.8, fade=2.5, gain=0.7)],
        "sfx": [sfx("sfx_paper_rustle", 0.95, 0.7)],
        "setTrack": MAP_STATE + [
            tr("screen", 0.9, 3.5, to=1),
            tr("glow", 3.1, 1.6, to=1),
            tr("spot", f"{L2}.start+0.0", 1.0, target="driver", to=1),
            tr("spot", f"{L2}.start+2.15", 1.0, target="driver", to=0.3),
            tr("spot", f"{L2}.start+2.15", 1.0, target="passenger", to=1),
            tr("spot", f"{L2}.start+3.45", 1.0, target="passenger", to=0.3),
            tr("spot", f"{L2}.start+3.45", 1.0, target="walker", to=1),
            tr("spot", f"{L2}.end+0.3", 1.2, target="driver", to=0.8),
            tr("spot", f"{L2}.end+0.3", 1.2, target="passenger", to=0.8),
            tr("spot", f"{L2}.end+0.3", 1.2, target="walker", to=0.8),
        ],
    })

    # ============================================================ a4_c005–a4_c007 Q5（題卡三段只調時間；回到剪影畫面）
    for cid in ("a4_c005", "a4_c006", "a4_c007"):
        c = C[cid]
        c["set"] = "a4_roadmap"
        c["sceneId"] = "a4_roadmap"
        c["setTrack"] = copy.deepcopy(SIL_STATE)
        c["initialState"]["characters"] = {}
    C["a4_c005"]["initialState"]["stage"] = stage("a4_sil", light=0.36)
    for cid in ("a4_c006", "a4_c007"):
        C[cid]["initialState"]["stage"].update({"set": 1})
    for a in C["a4_c007"]["animation"]:
        if a["name"] == "camera.move":
            a["params"]["to"] = "a4_sil"

    # ============================================================ a4_c008 回到校門口（會動的節拍）
    c = C["a4_c008"]
    L1, L2 = "a4_c008_01", "a4_c008_02"
    for l in c["lines"]:
        if l["id"] == L1:
            l["start"] = 7.0
        if l["id"] == L2:
            l["start"] = f"{L1}.end+3.3"
    sw = 3.32                         # 全暗時換景
    c.update({
        "voStart": 7.0, "tail": 2.2, "set": "a4_roadmap", "sceneId": "a4_roadmap",
        "initialState": {"stage": stage("a4_sil", light=1), "characters": {
            "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1, hand="grab"),
            "xiaoqing": kid(QG0, emotion="worried"), "xiaoyu": kid(XY0, emotion="worried"),
            "zhezhe": {"visible": True, "x": 14.0, "z": 1.05, "emotion": "worried"},
        }},
        "animation": [
            # 剪影翻回紙地圖：聚光、背光先收 → 剪影幕往下摺回地圖、地圖上的小屋收平（鏡頭不動）
            an("set.fold", 1.5, 1.0),
            an("fade.out", 2.6, 0.7),
            an("set.swap", sw, 0, set="gate"),
            cam("a4_deep", sw, cut=True),
            # 角色跟著街景一起回來（全暗那一格就站好，不在畫面上被線拉起來）
            an("puppet.popup", sw + 0.01, 0.005, "ale"),
            an("puppet.grab", sw + 0.01, 0.005, "ale", at=DOOR),
            an("puppet.popup", sw + 0.01, 0.005, "xiaoqing"),
            an("puppet.popup", sw + 0.01, 0.005, "xiaoyu"),
            an("zhezhe.glideTo", sw + 0.01, 0.01, "zhezhe", pos=ZZ_C008),
            an("fade.in", sw + 0.08, 0.8),
            # 地圖再立起來，變回校門口的街景（遠景已站好；近處的車、校門、警衛室、長椅依序立起；鏡頭不動）
            an("set.popup", sw + 1.0, 3.6),
            # 阿樂叔叔舉鑰匙招手 → 線繃直、手被拉偏（鑰匙晃兩下）→ 線鬆一點、手落回來
            an("puppet.waveTry", f"{L1}.start+1.15", 3.4, "ale", greet="greet", emotion="confused"),
            an("strings.loosen", f"{L1}.start+4.75", 1.3, "ale", anchors=["wrist", "elbow"], to=0.3),
            # 兩個孩子在接送線後各退半步、互看，不往車子走
            an("puppet.pose", f"{L1}.end+0.1", 0.24, "xiaoyu", pose="stepback"),
            an("puppet.move", f"{L1}.end+0.25", 0.7, "xiaoqing", dx=STEP),
            an("puppet.move", f"{L1}.end+0.4", 0.7, "xiaoyu", dx=STEP),
            an("puppet.lean", f"{L1}.end+1.0", 0.6, "xiaoqing", to=0.035),
            an("puppet.tilt", f"{L1}.end+1.0", 0.6, "xiaoyu", to=0.035),
            an("puppet.face", f"{L1}.end+1.1", None, "xiaoqing", emotion="worried"),
            cam("a4_kids_z", f"{L1}.end+1.7", 3.3),
            an("zhezhe.emote", f"{L2}.start-0.3", None, "zhezhe", emotion="curious"),
            an("zhezhe.look", f"{L2}.start+1.4", 0.6, "zhezhe", yaw=0),
        ],
        "audioId": None,
        "music": [music("none", 2.2, fade=1.0)],
        "sfx": [sfx("sfx_paper_rustle", 1.0, 0.8), sfx("sfx_paper_rustle", 1.6, 0.6), sfx("sfx_gate_ambience", sw + 0.1, 0.4),
                sfx("sfx_paper_rustle", sw + 1.05, 0.8), sfx("sfx_wind", sw + 0.6, 0.2), sfx("sfx_string_taut", f"{L1}.start+2.95", 0.7)],
        "setTrack": SIL_STATE[:2] + [
            tr("screen", to=1), tr("glow", to=1), tr("spot", target="all", to=0.8),
            tr("spot", 0.05, 0.8, target="all", to=0), tr("glow", 0.2, 1.0, to=0), tr("screen", 1.0, 1.4, to=0),
            tr("key", hold="ale.A"), tr("farUp", to=1), tr("wind", sw + 0.5, 2.0, to=1),
            tr("walkers", sw + 0.2, 7.5, kind="b", x0=-1.5, x1=13.0, z=-2.95),
        ],
    })

    # ============================================================ a4_c009–a4_c011 Q6（題卡三段只調時間）
    for cid in ("a4_c009", "a4_c010", "a4_c011"):
        c = C[cid]
        c["set"] = "gate"
        c["sceneId"] = "gate"
        c["initialState"]["characters"] = {
            "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1, hand="grab", stringTension=0.3),
            "xiaoqing": kid(QG1, emotion="worried", lean=0.035), "xiaoyu": kid(XY1, pose="stepback", emotion="worried"),
            "zhezhe": {"visible": True, "x": ZZ_C008[0], "z": ZZ_C008[2], "emotion": "curious"},
        }
        c["setTrack"] = [tr("key", hold="ale.A"), tr("wind", to=0.6)]
    C["a4_c009"]["initialState"]["stage"] = stage("a4_kids_z")
    for cid in ("a4_c010", "a4_c011"):
        C[cid]["initialState"]["stage"].update({"set": 1})
    for a in C["a4_c011"]["animation"]:
        if a["name"] == "camera.move":
            a["params"]["to"] = "a4_kids"
            a["start"] = "a4_c011_01.end+0.9"
            a["duration"] = 4.4
        if a["name"] == "light.restore":
            a["duration"] = 1.6
    for cid in ("a4_c009", "a4_c010", "a4_c011"):
        for a in C[cid]["initialState"]["characters"].values():
            a.pop("lean", None)

    # ============================================================ a4_c012 先不上車
    c = C["a4_c012"]
    L1, L2, L3, L4, L5 = (f"a4_c012_0{k}" for k in range(1, 6))
    for l in c["lines"]:
        if l["id"] == L3:
            l["start"] = f"{L2}.end+2.2"
    W0 = 0.15                          # 轉身往右走回校門裡（L2 結束後幾秒）
    w0 = f"{L2}.end+{W0}"
    w = lambda d: f"{L2}.end+{round(W0 + d, 3)}"
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 1.0, "tail": 2.4,
        "initialState": {"stage": stage("a4_kids"), "characters": {
            "xiaoqing": kid({"x": QG2["x"], "z": QG2["z"]}, emotion="worried"),
            "xiaoyu": kid({"x": XY2["x"], "z": XY2["z"]}, emotion="worried"),
            "lin": {"visible": True, "x": LIN2["x"], "z": LIN2["z"], "emotion": "neutral", "facing": 1},
            "chen": {"visible": True, "x": CHEN_X["c012"], "z": 0.35, "emotion": "neutral", "facing": -1},
        }},
        "animation": [
            # 小晴往後退一步（掌心向外，聲音不大但清楚）；兩人起始位置＝走之前（enter 的 from 把他們放在左邊）
            an("puppet.pose", 0.35, 0.24, "xiaoqing", pose="palmno"),
            an("puppet.move", 0.45, 0.6, "xiaoqing", dx=QG_STEP12),
            an("puppet.enter", w0, 1.6, "xiaoqing", **{"from": -(WALK + QG_STEP12)}),
            an("puppet.enter", w(0.15), 1.6, "xiaoyu", **{"from": -WALK}),
            an("puppet.pose", w0, 0.24, "xiaoqing", pose="walk"),
            an("puppet.pose", w(0.15), 0.24, "xiaoyu", pose="walk"),
            an("puppet.pose", w(1.65), 0.24, "xiaoqing", pose="stand"),
            an("puppet.pose", w(1.8), 0.24, "xiaoyu", pose="stand"),
            an("puppet.face", w(2.1), None, "xiaoqing", emotion="neutral"),
            # 林老師拿著手機從警衛室快步出來；陳伯伯從路口走過來
            an("puppet.enter", f"{L2}.end+0.5", 1.3, "lin", **{"from": 3.2}),
            an("puppet.enter", f"{L2}.start-0.2", 2.8, "chen", **{"from": -4.2}),
            cam("a4_guard", f"{L2}.start+0.1", 2.8),
            an("puppet.face", f"{L4}.start", None, "lin", emotion="smile"),
            an("puppet.pose", f"{L4}.start+0.05", 0.24, "lin", pose="crouch"),
            an("puppet.pose", f"{L4}.end+0.15", 0.24, "lin", pose="stand"),
            cam("a4_guard_lin", f"{L4}.start-0.2", 2.0),
            cam("a4_guard", f"{L5}.start-0.4", 1.9),
            an("puppet.face", f"{L5}.start", None, "chen", emotion="smile"),
        ],
        "audioId": "music_courage",
        "music": [],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.4), sfx("sfx_footsteps", w0, 0.5)],
        "setTrack": [tr("flag", to=1), tr("wind", to=0.5), tr("phone", to=1),
                     tr("phone", f"{L4}.start+0.17", 0, to=0), tr("phone", f"{L4}.end+0.27", 0, to=1)],
    })
    # 起始 x 要扣掉 enter 的位移（enter 開始前停在 x＋from）
    c["initialState"]["characters"]["xiaoqing"]["x"] = QG2["x"]
    c["initialState"]["characters"]["xiaoyu"]["x"] = XY2["x"]

    # ============================================================ a4_c013 那是什麼？（找找看 3）
    c = C["a4_c013"]
    L1, L2, L3 = "a4_c013_01", "a4_c013_02", "a4_c013_03"
    for l in c["lines"]:
        if l["id"] == L1:
            l["start"] = 3.6
        if l["id"] == L2:
            l["start"] = f"{L1}.end+0.9"
        if l["id"] == L3:
            l["start"] = f"{L2}.end+6.4"
    chen_palm = [round(CHEN_BENCH["x"] - 0.971, 3), 1.568]
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 3.6, "tail": 2.6,
        "initialState": {"stage": stage("a4_bench"), "characters": {
            "ale": ale(x=BENCH_ALE["x"], z=BENCH_ALE["z"], facing=1, stringTension=0.12),
            "chen": {"visible": True, "x": CHEN_BENCH["x"], "z": CHEN_BENCH["z"], "emotion": "neutral", "facing": 1},
            "xiaoqing": kid({"x": QG2["x"], "z": QG2["z"]}, emotion="neutral"),
            "xiaoyu": kid({"x": XY2["x"], "z": XY2["z"]}, emotion="neutral"),
            "lin": {"visible": True, "x": LIN2["x"], "z": LIN2["z"], "emotion": "neutral", "facing": 1},
            "zhezhe": {"visible": True, "x": 3.2, "z": 2.55, "emotion": "neutral"},
        }},
        "animation": [
            an("puppet.sit", 0.4, 1.4, "ale", to=1),
            an("puppet.pose", 1.9, 0.24, "chen", pose="receive"),
            an("puppet.grab", 2.2, 0.9, "ale", at=chen_palm),
            an("puppet.grab", 3.35, 0.9, "ale", to=0),
            an("puppet.pose", f"{L1}.start+1.75", 0.24, "chen", pose="stand"),
            cam("a4_keyclose", 1.2, 1.9),
            cam("a4_bench", f"{L1}.start+1.9", 1.9),
            cam("a4_gate_wide2", f"{L1}.end+0.05", 2.2),
            an("puppet.pose", f"{L2}.end+0.2", 0.24, "lin", pose="standr"),
            an("puppet.exit", f"{L2}.end+0.5", 2.2, "lin", to=4.0),
            an("puppet.face", f"{L2}.end+0.6", None, "xiaoqing", emotion="smile"),
            an("puppet.face", f"{L2}.end+0.8", None, "xiaoyu", emotion="smile"),
            an("zhezhe.emote", f"{L2}.end+1.0", None, "zhezhe", emotion="happy"),
            cam("a4_truck_mid", f"{L2}.end+1.0", 4.2),
            cam("a4_truck_window", f"{L2}.end+5.2", 5.6),
            an("zhezhe.emote", f"{L3}.start", None, "zhezhe", emotion="curious"),
        ],
        "audioId": None,
        "music": [music("music_town", f"{L2}.end+1.5", fade=2.5, gain=0.8)],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.5)],
        "setTrack": [
            tr("key", hold="ale.B"), tr("key", 3.1, 0.3, hold="chen.receive"), tr("key", f"{L1}.start+1.75", 0.24, hold="chen.stand"),
            tr("flag", to=1), tr("wind", to=0.4), tr("phone", to=1), tr("phone", f"{L2}.end+0.32", 0, to=0),
            tr("focus", f"{L2}.end+7.4", 2.4, to=1),
        ],
    })
    return cues


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    before = {c["id"]: (json.dumps(c["lines"], ensure_ascii=False), json.dumps(c.get("quiz"), ensure_ascii=False), json.dumps(c.get("checkpoint"), ensure_ascii=False),
                        c["next"], c["prevStable"], c["kind"], c.get("lamp"), c["teacherNote"]) for c in data["cues"]}
    data["set"] = "gate"
    data["characters"] = {
        "ale": {"name": "阿樂叔叔", "rig": "ale_v03", "x": ALE_TRUCK["x"], "z": ALE_TRUCK["z"], "facing": 1, "fallback": "adult"},
        "xiaoqing": {"name": "小晴", "rig": "standee:xiaoqing", "x": QG0["x"], "z": QG0["z"], "facing": 1, "fallback": "child"},
        "xiaoyu": {"name": "小宇", "rig": "standee:xiaoyu", "x": XY0["x"], "z": XY0["z"], "facing": 1, "fallback": "child"},
        "zhezhe": {"name": "折折", "rig": "zhezhe", "x": 2.95, "z": 1.0, "facing": 1, "fallback": "child"},
        "lin": {"name": "林老師", "rig": "standee:lin", "x": LIN2["x"], "z": LIN2["z"], "facing": 1, "fallback": "adult"},
        "chen": {"name": "陳伯伯", "rig": "standee:chen", "x": CHEN_X["c001"], "z": 0.55, "facing": 1, "fallback": "adult"},
    }
    data["_note"] = ("第四幕（G5 第四幕代理排戲；review/G5/a4/scripts/make_a4_cues.py 產生）。景：gate（校門口，app/src/sets/gate.ts）、"
                     "a4_roadmap（紙上的路，app/src/sets/a4_roadmap.ts）。cue 的 setTrack＝景的程式動作（引擎不讀，景的 update 讀；格式見兩個景的檔頭）。"
                     "storyboard 是劇本與節拍表的摘錄，引擎不讀。")
    build(data["cues"])
    for c in data["cues"]:
        b = before[c["id"]]
        now = (json.dumps([{k: v for k, v in l.items() if k != "start"} for l in c["lines"]], ensure_ascii=False), json.dumps(c.get("quiz"), ensure_ascii=False),
               json.dumps(c.get("checkpoint"), ensure_ascii=False), c["next"], c["prevStable"], c["kind"], c.get("lamp"), c["teacherNote"])
        lines0 = json.dumps([{k: v for k, v in l.items() if k != "start"} for l in json.loads(b[0])], ensure_ascii=False)
        assert (lines0,) + b[1:] == now, f"{c['id']} 鎖定欄位被改了"
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    tmp = Path(name)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    tmp.write_text(text, encoding="utf-8")
    r = subprocess.run(["node", str(Path(__file__).with_name("validate_a4.mjs")), str(tmp)], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        print("驗證失敗，a4.json 不動；暫存檔：", tmp)
        sys.exit(1)
    SRC.write_text(text, encoding="utf-8")
    tmp.unlink()
    print("已寫入", SRC)


if __name__ == "__main__":
    main()
