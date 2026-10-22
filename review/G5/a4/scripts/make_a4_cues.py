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
CHEN_BENCH = {"x": -0.3, "z": 0.62}        # G5 修正第 1 輪：往右 0.65（膝前線離他接鑰匙的手 ≥ 60 px）
CHEN_FAR = {"x": -3.3, "z": -3.0}           # a4_c001 大全景：遠方路口、背對阿樂叔叔舉導護旗（切到隔馬路中景時移出畫面）
ZZ_C008 = [3.05, 0, 2.6]
ZZ_QUIZ = [-4.7, 0, 4.15]                   # 題卡模式折折的位置（SHOW_INTERFACE.md 第 12 節建議 x −4.7、z 3.4；z 往前到台口內緣，第六題兩行題卡才不會擋住臉）

STRINGS = ["wrist", "elbow", "knee"]

# G5 修正第 2 輪：鏡頭各自的舞台燈（曝光），讓硬切前後的全畫面平均亮度相差 ≤ 約 15%（主線更正裁定：> 約 20% 不能一格硬切）
L_WIDE = 0.66       # a4_c001 放學大全景（燈 1 時亮度約 0.41；隔馬路看阿樂叔叔約 0.28）
L_WIN = 0.80        # a4_c001 孩子＋警衛室窗（G6 精修：校內景片蒙白後，燈 0.8 時孩子身後投影 ≥ 0.50）
L_WIN0 = 0.57       # a4_c001 切到警衛室窗那一格的燈（和隔馬路鏡頭亮度相差 ≤ 約 16%），鏡頭不動 0.7 秒慢慢升到 L_WIN（約 +14%）
L_WIDE2 = 0.90      # a4_c013 校門內外全景（燈 1 時約 0.39；之後切到車斗近景約 0.33）
L_SKY = 0.55        # a4_c002 天空（燈 1 時約 0.57、0.55 時約 0.41，從全暗淡入；之後硬切到俯視地圖約 0.36）
# 景的程式動作（gate.ts）：lift＝孩子身後的警衛室、校門柱、折疊門、校內圍牆提亮（兒童站位背景亮度 ≥ 0.50）；gateOpen＝放學時折疊門收起來；
# zzpatch＝蓋住引擎放在原點的折折接觸陰影（stage.ts 程式角色的接觸陰影用 root 位置＝永遠在 (0,0,0)；折折自己有影子）
# G6 精修：haze＝校內那一側的景片蒙一層暖白（輕微景深；兒童站位背景投影 ≥ 0.50）
GATE_BASE = [{"do": "lift", "start": 0, "duration": 0, "to": 1}, {"do": "gateOpen", "start": 0, "duration": 0, "to": 1},
             {"do": "haze", "start": 0, "duration": 0, "to": 1}]
GATE_ZZ = GATE_BASE + [{"do": "zzpatch", "start": 0, "duration": 0, "to": 1}]


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


FADE = 0.6          # fade.out／fade.in 長度（validate.ts MIN_SET_FADE；主線更正裁定：亮度差 > 約 20% 的切換不能一格硬切）
Q_VO = 1.45         # 出題台詞「第 N 題」開始（主線更正裁定 ≥ 1.4 秒；不壓在 sfx_quiet_fold 的前段）
Q_LIGHT = 0.55      # 題卡模式舞台燈


def dip(at, to_cam, light=None):
    """全暗換鏡：at 起 FADE 秒漸暗 → 全暗時切鏡頭（可順便把燈調到 light，0 秒）→ FADE 秒漸亮。回傳 (動畫, 漸亮結束時間)。
    at 是數字或 "<台詞>.end+x" 這類參照（同一句的參照才能相加）。"""
    def plus(ref, d):
        if isinstance(ref, (int, float)):
            return round(ref + d, 3)
        base, off = ref.rsplit("+", 1) if "+" in ref else (ref, "0")
        return f"{base}+{round(float(off) + d, 3)}"
    out = [an("fade.out", at, FADE), cam(to_cam, plus(at, FADE + 0.02), cut=True)]
    if light is not None:
        out.append(an("light.restore", plus(at, FADE + 0.02), 0) if light >= 1 else an("light.dim", plus(at, FADE + 0.02), 0, to=light))
    out.append(an("fade.in", plus(at, FADE + 0.05), FADE))
    return out, plus(at, 2 * FADE + 0.05)


def quiz_cues(C, ids, quiz_set_track, chars, lamp_index, exit_anims, lamp_tail):
    """題卡三段（SHOW_INTERFACE.md 第 12 節＋主線補充裁定；G5 修正第 2 輪重排）：
    出題：故事畫面 0.6 秒淡到全暗（鏡頭不動；sfx_quiet_fold 0 秒、折折收聲訊號）→ 全暗時切到 quiz、燈 0.55 → 0.6 秒淡入
         → 1.45 秒折折說「第 N 題」→ 摺成題卡（攤開 0.6 秒時 DOM 題卡 0.6 秒淡入）→ 變回貓 → 旁白念題目。
    揭答：不動鏡頭，蓋章。
    點燈：第 N 盞燈 1.5 秒漸亮 → 折折說話 → 題卡 0.6 秒淡出 → 停 ≥ 0.5 秒 → exit_anims（回故事；各段自己排）。
    折折在三段都留在台口左前 ZZ_QUIZ，揭答、點燈恢復 idle。"""
    q, r, l = ids
    for cid in ids:
        c = C[cid]
        c["initialState"]["characters"] = copy.deepcopy(chars)
        c["initialState"]["characters"]["zhezhe"] = {"visible": True, "x": ZZ_QUIZ[0], "z": ZZ_QUIZ[2], "emotion": "curious"}
        c["setTrack"] = copy.deepcopy(quiz_set_track)
    L1 = f"{q}_01"
    for line in C[q]["lines"]:
        if line["id"] == f"{q}_02":
            line["start"] = f"{L1}.end+1.3"     # 題卡攤開後旁白才念題目
    C[q]["voStart"] = Q_VO
    C[q]["tail"] = 1.0
    enter, _ = dip(0, "quiz", Q_LIGHT)
    C[q]["animation"] = enter + [
        an("quiz.show", f"{L1}.end+0.6", 0.6),
        an("zhezhe.hush", 0.0, 1.4, "zhezhe"),
        an("zhezhe.emote", 0.6, None, "zhezhe", emotion="happy"),
        an("zhezhe.fold", f"{L1}.end+0.05", 1.2, "zhezhe", form="card"),
        an("zhezhe.fold", f"{L1}.end+1.35", 0.7, "zhezhe", form="idle"),
    ]
    C[q]["sfx"] = [sfx("sfx_quiet_fold", 0), sfx("sfx_card_in", f"{L1}.end+0.6", 0.8)]
    C[r]["animation"] = [an("quiz.reveal", 0.3, 0.45), an("zhezhe.emote", 0.2, None, "zhezhe", emotion="curious")]
    C[r]["initialState"]["stage"] = stage("quiz", light=Q_LIGHT, quiz=True)
    C[l]["initialState"]["stage"] = stage("quiz", light=Q_LIGHT, quiz=True)
    LL = f"{l}_01"
    C[l]["animation"] = [
        an("lamp.light", 0.3, 1.5, index=lamp_index),
        an("zhezhe.emote", 0.2, None, "zhezhe", emotion="happy"),
        an("quiz.hide", f"{LL}.end+0.3", 0.6),
    ] + exit_anims(LL)
    C[l]["tail"] = lamp_tail


C008_CHARS = {
    "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1, hand="grab"),
    "xiaoqing": kid(QG0, emotion="worried"), "xiaoyu": kid(XY0, emotion="worried"),
}
C008_TRACK = GATE_ZZ + [tr("key", hold="ale.A"), tr("farUp", to=1), tr("catEar", to=0.5), tr("wind", to=0.3)]


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
    cut2 = f"{L1}.start+9.8"         # 「林老師的電話也還沒打通」：孩子在接送線後、警衛室窗裡的小背影（G6 精修：早 0.2 秒，燈升完才到 cue 中點）
    cut3 = f"{L1}.end+0.15"          # 阿樂叔叔叫孩子（G6 精修：切到 a4_deep——孩子在前景、阿樂叔叔在對街，和 a4_c008 開頭同一個鏡位）
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 1.4, "tail": 3.0,
        # G5 修正第 2 輪（主線更正裁定：亮度差 > 約 20% 的硬切不行）：每個鏡頭各自的舞台燈（曝光），
        # 讓三次切換前後的全畫面平均亮度相差 ≤ 約 15%：大全景、警衛室窗＝較亮的畫面 → 燈 L_WIDE／L_WIN；隔馬路看阿樂叔叔＝燈 1。
        # 燈只在切鏡頭那一格改（0 秒），畫面上不會看到燈在變。
        "initialState": {"stage": stage("a4_gate_wide", light=L_WIDE), "characters": {
            "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1),
            "chen": {"visible": True, "x": CHEN_FAR["x"], "z": CHEN_FAR["z"], "emotion": "neutral", "facing": -1},
            "xiaoqing": kid(QG0), "xiaoyu": kid(XY0),
        }},
        "animation": [
            # 阿樂叔叔剛下車（在大全景裡還在車上：切鏡頭那一格才出現）
            an("puppet.popup", f"{L1}.start+5.29", 0.005, "ale"),
            an("puppet.grab", f"{L1}.start+5.29", 0.005, "ale", at=DOOR),
            an("puppet.kneeTug", f"{L1}.start+7.0", 3.2, "ale", at=DOOR),
            an("strings.loosen", f"{L1}.start+10.6", 1.4, "ale", anchors=["knee"], to=0.22),
            # 「上車吧」：X11（勉強、眉尾下垂＝困惑頭配說話嘴型），不用 X2 開心笑臉
            an("puppet.waveTry", f"{L2}.start+0.9", 3.4, "ale", greet="confused", emotion="confused"),
            an("strings.loosen", f"{L2}.end+0.25", 1.4, "ale", anchors=["wrist", "elbow"], to=0.3),
            an("puppet.blink", f"{L2}.end+0.3", None, "ale"),
            # G5 修正第 2 輪：招手後手扶回車門（站不穩、扶著車；和 a4_c008 同一個姿勢）。
            # 手臂垂下的站姿在這個斜看的鏡位，紙環（在手臂前 0.24）會偏到前臂剪影外 15–20 px；扶車門時紙環落在前臂上
            an("puppet.grab", f"{L2}.end+0.5", 1.0, "ale", at=DOOR),
            # 陳伯伯只在大全景（遠方路口）；切到隔馬路中景那一格移出畫面（之後 a4_c012 才從路口走過來）
            an("puppet.move", cut1, 0.01, "chen", dx=-30),
            cam("a4_across", cut1, cut=True), an("light.restore", cut1, 0),
            cam("a4_across_push", f"{L1}.start+5.4", 4.4),
            # G6 精修：孩子＋警衛室窗比隔馬路鏡頭亮（孩子身後投影要 ≥ 0.50）→ 切過去那一格燈 L_WIN0（亮度相近），
            # 鏡頭不動 0.7 秒升到 L_WIN（單向）。阿樂叔叔叫孩子時切到 a4_deep（孩子在前景、阿樂叔叔在對街；亮度和窗景相近），
            # 不再切回隔馬路近景（以前窗景 → 近景一格暗 1.4 倍，要先降燈，會「亮一下又暗」）
            cam("a4_window", cut2, cut=True), an("light.dim", cut2, 0, to=L_WIN0),
            an("light.dim", f"{L1}.start+9.82", 0.7, to=L_WIN),
            cam("a4_deep", cut3, cut=True), an("light.restore", cut3, 0),
        ],
        "audioId": "music_town",
        "music": [music("music_m4_light", f"{L1}.start+4.6", fade=3.0)],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.7), sfx("sfx_truck_arrive", f"{L1}.start+0.9", 0.6),
                sfx("sfx_string_taut", f"{L2}.start+2.7", 0.7)],
        "setTrack": GATE_BASE + [
            tr("lin", to=1), tr("flag", to=1), tr("key", hold="ale.A"), tr("catEar", to=0.5),
            # 遠景家長牽孩子（淺紙色背影小紙人）：往左後方的對街人行道走遠；第一格就在，大全景切走那一格才消失（不在畫面中冒出來、消失）
            tr("walkers", 0, 6.68, kind="a", x0=1.2, x1=-2.3, z=-2.7, z1=-3.25),
            tr("walkers", 0, 6.68, kind="b", x0=-0.3, x1=-3.9, z=-2.8, z1=-3.3),
            tr("truck", f"{L1}.start+1.0", 4.6, **{"from": -9.5}),
            tr("wind", to=0.25),
            # 隔馬路看阿樂叔叔的兩段推鏡掃過紅磚立面（細格紅色光敏）：切過去那一格起紅磚降彩 0.3（切鏡頭那一格改，看不到變化）
            tr("brick", cut1, 0, to=0.3),
            # G6 精修：對街中景也蒙一點白（隔馬路看阿樂叔叔 ↔ 孩子＋警衛室窗的硬切亮度相近；孩子身後投影 ≥ 0.50）
            tr("hazeStreet", to=1),
        ],
    })

    # ============================================================ a4_c002 不對勁 → 街道摺平成地圖
    c = C["a4_c002"]
    L1, L2, L3 = "a4_c002_01", "a4_c002_02", "a4_c002_03"
    for l in c["lines"]:
        if l["id"] == L3:
            l["start"] = f"{L2}.end+1.1"
    f0 = f"{L3}.end+0.1"             # 摺成紙飛機
    f0s = f"{L3}.end+0.6"             # 摺紙聲（摺痕）
    # G5 修正第 2 輪：孩子近景（亮度約 0.34）→ 天空（約 0.57）差 1.7 倍，不能硬切 → 0.6 秒淡到全暗、全暗時切到天空、0.6 秒淡入；
    # 天空這個鏡頭燈 L_SKY（亮度約 0.42），之後切到俯視地圖（約 0.36–0.40）時燈回 1，亮度相差 ≤ 約 15%，可以硬切
    sky_dip, _ = dip(f"{L3}.end+0.1", "a4_up", L_SKY)
    # G6 精修（第一批放行一般問題）：以前天空停 3.3 秒、再硬切到俯視，校門口景片的正上方俯視與左下深紅布幕露出 1.4 秒才換景。
    # 改成：紙飛機一淡入就起飛（天空約 1.7 秒，含淡入淡出）→ 飛出畫面後 0.6 秒淡到全暗 → 全暗那一格同時換景（a4_roadmap）、
    # 切俯視地圖、小屋收平、燈回 1 → 0.6 秒淡入地圖 → 停 0.25 秒 → 小屋立起 2 秒（立體書）。觀眾不會看到校門口景的俯視。
    M_OUT = f"{L3}.end+2.45"
    M_SW = f"{L3}.end+3.07"
    c.update({
        # G5 修正第 2 輪：a4_c001 停在隔馬路的阿樂叔叔（亮度約 0.32），這裡開在孩子近景（門房提亮後約 0.41），差 1.3 倍
        # → setFade：引擎先把上一格漸暗 0.6 秒（預捲），本 cue 從全暗 0.6 秒漸亮（SHOW_INTERFACE.md 第 4 節）
        "setFade": FADE,
        "set": "gate", "sceneId": "gate", "voStart": 0.8, "tail": 0.35,
        "initialState": {"stage": stage("a4_kids_qg"), "characters": {
            "xiaoqing": kid(QG0, pose="worried", emotion="worried"),
            "xiaoyu": kid(XY0, emotion="worried"),
            "zhezhe": {"visible": True, "x": 2.5, "z": 1.6, "emotion": "curious"},
        }},
        "animation": [
            an("puppet.tilt", f"{L1}.start+0.2", 0.6, "xiaoyu", to=0.03),
            # 鏡頭不推不搖（細格光敏：小宇的紅外套）：小晴近景 → 小宇開口時切到兩人＋折折
            cam("a4_kids_z2", f"{L2}.start-0.25", cut=True),
            # 折折從小晴的筆記本後面探出頭、走到兩人中間前面（不跳：落地彈跳在細格光敏會超標）
            an("zhezhe.walkTo", f"{L2}.end+0.15", 1.0, "zhezhe", pos=[2.75, 0, 2.6]),
            an("zhezhe.emote", f"{L2}.end+0.9", None, "zhezhe", emotion="worried"),
            an("zhezhe.emote", f"{L3}.start+0.9", None, "zhezhe", emotion="curious"),
            # 折折開始摺紙飛機時畫面淡到全暗 → 天空淡入，紙飛機飛過天空、飛出畫面
            # → 直接切到俯視（不俯衝斑馬線；景片不在畫面上翻摺）→ 街道淡成牛皮紙地圖 → 換景、小屋立起
            an("zhezhe.fold", f0, 1.5, "zhezhe", form="plane"),
        ] + sky_dip + [
            an("zhezhe.flyTo", f"{L3}.end+1.0", 2.0, "zhezhe", pos=[-0.5, 9.8, -1.2], height=1.0),
            an("fade.out", M_OUT, FADE),
            an("set.swap", M_SW, 0, set="a4_roadmap"),
            an("set.fold", M_SW, 0),
            cam("a4_map", M_SW, cut=True), an("light.restore", M_SW, 0),
            an("fade.in", f"{L3}.end+3.1", FADE),
            an("set.popup", f"{L3}.end+3.95", 2.0),
        ],
        "audioId": None,
        "music": [music("music_road", f"{L3}.end+1.6", fade=2.5, gain=0.9)],
        "sfx": [sfx("sfx_fold", f0s, 0.9), sfx("sfx_plane_whoosh", f"{L3}.end+1.3", 0.8),
                sfx("sfx_paper_rustle", f"{L3}.end+3.15", 0.7), sfx("sfx_paper_rustle", f"{L3}.end+4.0", 0.8)],
        "setTrack": GATE_ZZ + [tr("farUp", to=1), tr("key", hold="ale.A"), tr("catEar", to=0.5),
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
        # G5 修正第 2 輪：俯視地圖（亮度約 0.37）→ 還暗著的剪影幕（約 0.13）差 2.8 倍，不能硬切 → 0.6 秒淡到全暗、切鏡、0.6 秒淡入
        "animation": dip(0, "a4_sil")[0] + [
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

    # ============================================================ a4_c005–a4_c007 Q5（題卡三段；點燈後直接淡到 a4_c008 的街景）
    for cid in ("a4_c005", "a4_c006", "a4_c007"):
        C[cid]["set"] = "a4_roadmap"
        C[cid]["sceneId"] = "a4_roadmap"
    C["a4_c005"]["initialState"]["stage"] = stage("a4_sil", light=0.36)

    def q5_exit(LL):
        """點燈回故事（G5 修正第 2 輪；重驗嚴重問題 S2）：題卡 0.6 秒淡出 → 停 0.55 秒（畫面不動）→ 0.6 秒淡到全暗
        （台口、折折一起慢慢暗下；折折不跳、不換姿勢）→ 全暗時換回校門口、切到 a4_deep、燈回 1、角色站好、折折移到孩子旁邊
        → 0.8 秒淡入 a4_c008 的街景。拿掉以前「硬切回亮剪影 1.3 秒再摺回地圖」那一段。"""
        sw = f"{LL}.end+2.1"
        k = f"{LL}.end+2.11"
        return [
            an("fade.out", f"{LL}.end+1.45", FADE),
            an("set.swap", sw, 0, set="gate"),
            cam("a4_deep", sw, cut=True),
            an("light.restore", sw, 0),
            an("puppet.popup", k, 0.005, "ale"),
            an("puppet.grab", k, 0.005, "ale", at=DOOR),
            an("puppet.popup", k, 0.005, "xiaoqing"),
            an("puppet.popup", k, 0.005, "xiaoyu"),
            an("zhezhe.glideTo", k, 0.01, "zhezhe", pos=ZZ_C008),
            an("zhezhe.emote", k, None, "zhezhe", emotion="worried"),
            an("fade.in", f"{LL}.end+2.15", 0.8),
        ]

    quiz_cues(C, ("a4_c005", "a4_c006", "a4_c007"), SIL_STATE, {}, 5, q5_exit, 3.4)
    # a4_c007 換回校門口之後才出現的角色與景（有 puppet.popup 的角色在立起之前看不到；景的程式動作只有 gate 讀）
    C["a4_c007"]["initialState"]["characters"].update(copy.deepcopy(C008_CHARS))
    C["a4_c007"]["setTrack"] += copy.deepcopy(C008_TRACK)

    # ============================================================ a4_c008 回到校門口（會動的節拍）
    c = C["a4_c008"]
    L1, L2 = "a4_c008_01", "a4_c008_02"
    V8 = 1.3                          # 街景已經在 a4_c007 結尾淡入：老師按下一步後停 1.3 秒，阿樂叔叔開口
    for l in c["lines"]:
        if l["id"] == L1:
            l["start"] = V8
        if l["id"] == L2:
            l["start"] = f"{L1}.end+3.3"
    c.update({
        "voStart": V8, "tail": 2.2, "set": "gate", "sceneId": "gate",
        "initialState": {"stage": stage("a4_deep"), "characters": {
            **copy.deepcopy(C008_CHARS),
            "zhezhe": {"visible": True, "x": ZZ_C008[0], "z": ZZ_C008[2], "emotion": "worried"},
        }},
        "animation": [
            an("puppet.grab", -0.01, 0.005, "ale", at=DOOR),   # G6 精修：−0.01，第 0 格就扶著車門（同 a4_c007 結尾）
            # 阿樂叔叔舉鑰匙招手 → 線繃直、手被拉偏（鑰匙晃兩下）→ 線鬆一點、手落回來
            an("puppet.waveTry", f"{L1}.start+1.15", 3.4, "ale", greet="confused", emotion="confused"),
            an("strings.loosen", f"{L1}.start+4.75", 1.3, "ale", anchors=["wrist", "elbow"], to=0.3),
            # 兩個孩子在接送線後各退半步、互看，不往車子走
            an("puppet.pose", f"{L1}.end+0.1", 0.24, "xiaoyu", pose="stepback"),
            an("puppet.move", f"{L1}.end+0.25", 0.7, "xiaoqing", dx=STEP),
            an("puppet.move", f"{L1}.end+0.4", 0.7, "xiaoyu", dx=STEP),
            an("puppet.lean", f"{L1}.end+1.0", 0.6, "xiaoqing", to=0.035),
            an("puppet.tilt", f"{L1}.end+1.0", 0.6, "xiaoyu", to=0.035),
            an("puppet.face", f"{L1}.end+1.1", None, "xiaoqing", emotion="worried"),
            # 不從大全景推過紅磚立面（細格紅色光敏）：孩子退完半步後直接切到雙人近景（亮度相近）
            cam("a4_kids_z", f"{L1}.end+1.6", cut=True),
            an("zhezhe.emote", f"{L2}.start-0.3", None, "zhezhe", emotion="curious"),
            an("zhezhe.look", f"{L2}.start+1.4", 0.6, "zhezhe", yaw=0),
            # 折折把問題交給觀眾後，跳出畫面左邊（去台口左前主持題卡）
            an("zhezhe.hopTo", f"{L2}.end+0.45", 0.9, "zhezhe", pos=[-1.3, 0, 3.0], height=0.5),
        ],
        "audioId": None,
        "music": [music("none", 0, fade=1.0)],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.4), sfx("sfx_wind", 0.4, 0.2), sfx("sfx_string_taut", f"{L1}.start+2.95", 0.7)],
        "setTrack": copy.deepcopy(C008_TRACK) + [tr("wind", 0.6, 2.0, to=1)],
    })

    # ============================================================ a4_c009–a4_c011 Q6（題卡三段）
    for cid in ("a4_c009", "a4_c010", "a4_c011"):
        C[cid]["set"] = "gate"
        C[cid]["sceneId"] = "gate"
    q6_chars = {
        "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1, hand="grab", stringTension=0.3),
        "xiaoqing": kid(QG1, emotion="worried"), "xiaoyu": kid(XY1, pose="stepback", emotion="worried"),
    }

    def q6_exit(LL):
        """點燈回故事：題卡 0.6 秒淡出 → 停 0.55 秒 → 0.6 秒淡到全暗 → 全暗時切回孩子近景、燈回 1（孩子站直）→ 0.6 秒淡入
        （quiz 全景約 0.28、門房提亮後的孩子近景約 0.38，差 1.4 倍，不能硬切；a4_c012 從孩子近景接）。"""
        sw = f"{LL}.end+2.1"
        return [
            an("fade.out", f"{LL}.end+1.45", FADE),
            cam("a4_kids", sw, cut=True),
            an("light.restore", sw, 0),
            an("puppet.lean", sw, 0.001, "xiaoqing", to=0),
            an("puppet.tilt", sw, 0.001, "xiaoyu", to=0),
            an("puppet.pose", sw, 0.001, "xiaoyu", pose="stand"),
            an("fade.in", f"{LL}.end+2.15", FADE),
        ]

    quiz_cues(C, ("a4_c009", "a4_c010", "a4_c011"), GATE_ZZ + [tr("key", hold="ale.A"), tr("wind", to=0.6), tr("catEar", to=0.5)],
              q6_chars, 6, q6_exit, 3.1)
    C["a4_c009"]["initialState"]["stage"] = stage("a4_kids_z")
    # a4_c008 結尾孩子微微前傾（lean／tilt 0.035）：initialState 沒有前傾欄位，用極短動畫接上（題卡三段都一樣）。
    # G6 精修：開始時間 −0.01（以前是 0：紙偶動畫在 t=0 進度是 0，第一格孩子會站直一格再前傾——
    # 校內景片蒙白後頭髮和背景的對比變大，a4_c009 第 0 格這一下在細格光敏算 2 次，加上進題卡的淡出淡入＝每秒 4 次）
    for cid in ("a4_c009", "a4_c010", "a4_c011"):
        C[cid]["animation"][0:0] = [an("puppet.lean", -0.01, 0.001, "xiaoqing", to=0.035), an("puppet.tilt", -0.01, 0.001, "xiaoyu", to=0.035)]

    # ============================================================ a4_c012 先不上車
    # G5 修正第 1 輪：細格 32×18 光敏對「畫面上橫向移動快的紙偶」很敏感（白邊、反光背心一條條掃過格子）。
    # 走位都放在放學大全景（每單位約 125–135 px）裡、螢幕上每秒 ≤ 約 200 px；說話時才切回近景、中景（推拉一律硬切）。
    c = C["a4_c012"]
    L1, L2, L3, L4, L5 = (f"a4_c012_0{k}" for k in range(1, 6))
    for l in c["lines"]:
        if l["id"] == L3:
            l["start"] = f"{L2}.end+4.6"
    e = lambda d: f"{L2}.end+{d}"
    CHEN_FROM = -2.2                   # 陳伯伯從路口走過來的起點（大全景裡看得到他起步）
    LIN_FROM = round(LIN2["x"] + 3.15, 3)   # 林老師從大全景右緣外走進來（警衛室那一側）
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 1.0, "tail": 2.4,
        "initialState": {"stage": stage("a4_kids"), "characters": {
            "ale": ale(x=ALE_TRUCK["x"], z=ALE_TRUCK["z"], facing=1, hand="grab", stringTension=0.3),
            "xiaoqing": kid({"x": round(QG2["x"] - WALK - QG_STEP12, 3), "z": QG2["z"]}, emotion="worried"),
            "xiaoyu": kid({"x": round(XY2["x"] - WALK, 3), "z": XY2["z"]}, emotion="worried"),
            "lin": {"visible": True, "x": LIN_FROM, "z": LIN2["z"], "emotion": "neutral", "facing": 1},
            "chen": {"visible": True, "x": CHEN_FROM, "z": 0.35, "emotion": "neutral", "facing": -1},
        }},
        "animation": [
            # 阿樂叔叔還在車門邊（大全景裡看得到）
            an("puppet.grab", 0, 0.005, "ale", at=DOOR),
            # 小晴往後退一步（掌心向外，聲音不大但清楚）
            an("puppet.pose", 0.35, 0.24, "xiaoqing", pose="palmno"),
            an("puppet.move", 0.45, 0.6, "xiaoqing", dx=QG_STEP12),
            # 切到放學大全景：兩人轉身往右走回校門裡、警衛室門口（紙偶在軌道上滑步；不用 enter 的上下彈跳）
            cam("a4_gate_wide", e(0.1), cut=True),
            an("puppet.pose", e(0.25), 0.24, "xiaoqing", pose="walk"),
            an("puppet.pose", e(0.4), 0.24, "xiaoyu", pose="walk"),
            an("puppet.move", e(0.3), 3.0, "xiaoqing", dx=WALK),
            an("puppet.move", e(0.45), 3.0, "xiaoyu", dx=WALK),
            an("puppet.pose", e(3.3), 0.24, "xiaoqing", pose="stand"),
            an("puppet.pose", e(3.45), 0.24, "xiaoyu", pose="stand"),
            an("puppet.face", e(3.7), None, "xiaoqing", emotion="neutral"),
            # 林老師拿著手機從警衛室那一側快步出來；陳伯伯從路口走過來
            an("puppet.move", e(0.8), 3.6, "lin", dx=round(LIN2["x"] - LIN_FROM, 3)),
            # 陳伯伯在小宇說話時就起步（還在近景畫面外），慢慢走 6 秒（深色褲腳掃過淺色門柱：細格光敏）
            an("puppet.move", f"{L2}.start+0.4", 6.0, "chen", dx=round(CHEN_X["c012"] - CHEN_FROM, 3)),
            # 四人到齊、小宇報告前切到警衛室門口四人中景
            cam("a4_guard", f"{L3}.start-0.3", cut=True),
            an("puppet.face", f"{L4}.start", None, "lin", emotion="smile"),
            an("puppet.pose", f"{L4}.start+0.05", 0.24, "lin", pose="crouch"),
            an("puppet.pose", f"{L4}.end+0.15", 0.24, "lin", pose="stand"),
            cam("a4_guard_lin", f"{L4}.start-0.2", cut=True),
            cam("a4_guard", f"{L5}.start-0.4", cut=True),
            an("puppet.face", f"{L5}.start", None, "chen", emotion="smile"),
        ],
        "audioId": "music_courage",
        "music": [],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.4), sfx("sfx_footsteps", e(0.3), 0.5)],
        "setTrack": GATE_BASE + [tr("flag", to=1), tr("wind", to=0.5), tr("phone", to=1), tr("catEar", to=1), tr("key", hold="ale.A"),
                     tr("phone", f"{L4}.start+0.17", 0, to=0), tr("phone", f"{L4}.end+0.27", 0, to=1)],
    })

    # ============================================================ a4_c013 那是什麼？（找找看 3）
    c = C["a4_c013"]
    L1, L2, L3 = "a4_c013_01", "a4_c013_02", "a4_c013_03"
    for l in c["lines"]:
        if l["id"] == L1:
            l["start"] = 3.6
        if l["id"] == L2:
            l["start"] = f"{L1}.end+0.9"
        if l["id"] == L3:
            l["start"] = f"{L2}.end+3.5"
    chen_palm = [round(CHEN_BENCH["x"] - 0.971, 3), 1.568]
    c.update({
        "set": "gate", "sceneId": "gate", "voStart": 3.6, "tail": 1.9,
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
            # 陳伯伯先在中景伸手（紙片翻面），過 1 秒才切到收鑰匙近景（翻面和切鏡不擠在同一秒：細格光敏）
            an("puppet.pose", 1.2, 0.24, "chen", pose="receive"),
            an("puppet.grab", 2.35, 0.9, "ale", at=chen_palm),
            an("puppet.grab", 3.5, 0.9, "ale", to=0),
            an("puppet.pose", f"{L1}.start+1.75", 0.24, "chen", pose="stand"),
            # 推拉都改硬切（細格光敏：紅磚立面）：中景 → 收鑰匙近景 → 中景 → 校門內外全景
            cam("a4_keyclose", 2.3, cut=True),
            cam("a4_bench", f"{L1}.start+1.9", cut=True),
            cam("a4_gate_wide2", f"{L1}.end+0.1", cut=True), an("light.dim", f"{L1}.end+0.1", 0, to=L_WIDE2),
            an("puppet.pose", f"{L2}.end+0.2", 0.24, "lin", pose="standr"),
            an("puppet.exit", f"{L2}.end+0.5", 2.2, "lin", to=4.0),
            an("puppet.face", f"{L2}.end+0.6", None, "xiaoqing", emotion="smile"),
            an("puppet.face", f"{L2}.end+0.8", None, "xiaoyu", emotion="smile"),
            an("zhezhe.emote", f"{L2}.end+1.0", None, "zhezhe", emotion="happy"),
            # 不從長椅搖過去（會切到阿樂叔叔半張臉、掃過紅磚立面）：孩子鬆一口氣後直接切到車斗（畫面裡只有車），再慢慢推到貓耳
            cam("a4_truck_close", f"{L2}.end+2.3", cut=True), an("light.restore", f"{L2}.end+2.3", 0),
            cam("a4_ears", f"{L2}.end+2.5", 5.4),
            an("zhezhe.emote", f"{L3}.start", None, "zhezhe", emotion="curious"),
        ],
        "audioId": None,
        "music": [music("music_town", f"{L2}.end+1.5", fade=2.5, gain=0.8)],
        "sfx": [sfx("sfx_gate_ambience", 0, 0.5)],
        "setTrack": GATE_ZZ + [
            tr("key", hold="ale.B"), tr("key", 3.25, 0.3, hold="chen.receive"), tr("key", f"{L1}.start+1.75", 0.24, hold="chen.stand"),
            tr("flag", to=1), tr("wind", to=0.4), tr("phone", to=1), tr("phone", f"{L2}.end+0.32", 0, to=0), tr("catEar", to=1),
            # 推鏡時紅磚降彩約 30%（細格紅色光敏），停格時留 12%（骨架是畫面裡對比最高的東西）
            tr("brick", f"{L2}.end+2.25", 0.05, to=0.3), tr("brick", f"{L2}.end+8.0", 0.8, to=0.12),
            tr("focus", f"{L2}.end+6.0", 2.0, to=1),
        ],
    })
    return cues


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]).resolve() if "--out" in sys.argv else SRC
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
    # 先寫到同一個資料夾的暫存檔再改名（其他代理同時在 build，不會讀到寫一半的檔）
    part = out.with_suffix(".json.part")
    part.write_text(text, encoding="utf-8")
    os.replace(part, out)
    tmp.unlink()
    print("已寫入", out)


if __name__ == "__main__":
    main()
