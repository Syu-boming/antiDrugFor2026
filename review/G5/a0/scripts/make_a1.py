"""第一幕段落檔 app/cues/show/a1.json：依劇本 v03／節拍表 v03 排表演（景 square_a1）。
台詞編號、說話者、字幕文字、八題資料一律沿用現有段落檔（不改）；題卡三段只調時間（另把折折留在台上做收摺訊號，避免題卡前後折折突然消失）。
寫到暫存檔、用 node 驗證 JSON 後才搬回。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SEG = ROOT / "app/cues/show/a1.json"


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


def ref(line, off=0.0, end=False):
    r = f"{line}.end" if end else line
    if off:
        r += f"{off:+.2f}"
    return r


d = json.loads(SEG.read_text(encoding="utf8"))
cues = {c["id"]: c for c in d["cues"]}
d["set"] = "square_a1"

PINAN = {"x": -2.4, "z": 0.2}
LANTERN_TOP = [-2.34, 1.37, 0.42]      # 品安腿上竹燈籠的上緣（facing −1 鏡像後）
ZZ_BENCH = [-1.3, 0.92, 0.32]          # 品安旁邊的椅面
QG1, XY1, ZZ1 = {"x": -0.55, "z": 0.45}, {"x": 0.55, "z": 0.15}, [0.1, 0.0, 1.0]
# 第一幕後段（拒絕後往右走）的停位
QG4, XY4, ZZ4 = {"x": 1.2, "z": 0.45}, {"x": 2.35, "z": 0.15}, [1.75, 0.0, 1.05]
QG_MID, XY_MID = 0.3, 1.3      # 拒絕後第一段走到的位置（小晴回頭叫品安）


def char(vis=True, **kw):
    o = {"visible": vis}
    o.update(kw)
    return o


def start_state(camera, chars, light=1, quiz=False):
    st = {"curtain": "open", "camera": camera, "light": light}
    if quiz:
        st["quiz"] = True
    return {"stage": st, "characters": chars}


# ───────────────────────────── a1_c001 廣場上的品安（紙青蛙） ─────────────────────────────
c = cues["a1_c001"]
L1, L2, L3, L4, L5 = (f"a1_c001_0{i}" for i in range(1, 6))
c["initialState"] = start_state("a1_wide", {
    "pinan": char(emotion="smile", pose="sit_lantern", x=PINAN["x"], z=PINAN["z"], facing=-1),
    "xiaoqing": char(emotion="smile", pose="walk_l", x=QG1["x"], z=QG1["z"], facing=1),
    "xiaoyu": char(emotion="smile", pose="walk", x=XY1["x"], z=XY1["z"], facing=-1),
    "zhezhe": char(emotion="happy", x=8.8, y=0, z=ZZ1[2]),
})
FROG = ref(L4, -0.35, end=True)
c["animation"] = [
    # 廣場大全景 → 推到長椅；孩子從右邊走過來
    # 大全景交代廣場（只有長椅上的品安）→ 鏡頭推到長椅中景 → 孩子才從畫面右邊走進來（中景裡走的距離短，畫面不會一格一格閃）
    A("camera.move", 0.9, 2.8, None, to="a1_bench"),
    {"name": "puppet.enter", "target": "xiaoqing", "start": 3.5, "duration": 3.0, "ease": "out", "params": {"from": 9.5}},
    {"name": "puppet.enter", "target": "xiaoyu", "start": 4.7, "duration": 2.9, "ease": "out", "params": {"from": 9.0}},
    A("zhezhe.walkTo", 7.4, 2.8, "zhezhe", pos=ZZ1),
    A("puppet.pose", 6.35, 0.24, "xiaoqing", pose="stand"),
    A("puppet.pose", 7.45, 0.24, "xiaoyu", pose="standwatch"),
    A("puppet.face", ref(L1, 0.3), None, "pinan", emotion="smile"),
    A("puppet.tilt", ref(L2, 0.6), 0.6, "xiaoqing", to=0.04),
    A("puppet.face", ref(L3, -0.1), None, "xiaoyu", emotion="worried"),
    A("puppet.face", ref(L3, 0.2, end=True), None, "xiaoyu", emotion="smile"),
    # 折折：「看我摺一盞燈籠——」→ 一摺卻摺成紙青蛙（摺錯晃一下）→ 蹦一下跳進品安的竹燈籠，探出頭來
    A("zhezhe.emote", ref(L4, -0.1), None, "zhezhe", emotion="proud"),
    A("camera.move", ref(L4, 2.25, end=True), 2.2, None, to="a1_lantern"),
    A("zhezhe.fold", FROG, 1.3, "zhezhe", form="frog", scale=0.76, fumble=True),
    A("zhezhe.hopTo", ref(L4, 1.25, end=True), 0.95, "zhezhe", pos=LANTERN_TOP, height=0.75),
    A("puppet.face", ref(L4, 2.15, end=True), None, "pinan", emotion="surprised"),
    A("puppet.face", ref(L5, 0.05, end=True), None, "pinan", emotion="smile"),
    # 三個孩子笑出來
    A("puppet.face", ref(L5, 0.15, end=True), None, "xiaoqing", emotion="surprised"),
    A("puppet.face", ref(L5, 0.15, end=True), None, "xiaoyu", emotion="surprised"),
    A("puppet.tilt", ref(L5, 0.2, end=True), 0.6, "xiaoyu", to=0.06),
    A("puppet.tilt", ref(L5, 0.35, end=True), 0.6, "xiaoqing", to=0.05),
    A("puppet.face", ref(L5, 1.1, end=True), None, "xiaoqing", emotion="smile"),
    A("puppet.face", ref(L5, 1.0, end=True), None, "xiaoyu", emotion="smile"),
    A("puppet.tilt", ref(L5, 0.4, end=True), 0.6, "pinan", to=0.04),
    A("camera.move", ref(L5, 1.0, end=True), 2.4, None, to="a1_bench"),
    # 紙青蛙跳到品安旁邊的椅面上，摺回貓
    A("zhezhe.hopTo", ref(L5, 1.05, end=True), 0.85, "zhezhe", pos=ZZ_BENCH, height=0.35),
    A("zhezhe.fold", ref(L5, 1.95, end=True), 1.3, "zhezhe", form="idle"),
]
c["lines"][4]["start"] = ref(L4, 2.65, end=True)
c["audioId"] = "music_town"
c["music"] = []
c["sfx"] = [S("sfx_crowd_far", 0.3, 0.22), S("sfx_footsteps", 3.8, 0.35),
            S("sfx_fold", ref(L4, -0.22, end=True), 0.7), S("sfx_paper_rustle", ref(L4, 2.1, end=True), 0.35),
            S("sfx_fold", ref(L5, 2.08, end=True), 0.6)]
c["voStart"] = 6.6
c["tail"] = 3.1
c["fx"] = ["FX7", "FX13"]

# ───────────────────────────── a1_c002 閃亮的小盒子 ─────────────────────────────
c = cues["a1_c002"]
M1, M2, M3 = "a1_c002_01", "a1_c002_02", "a1_c002_03"
c["initialState"] = start_state("a1_bench", {
    "pinan": char(emotion="smile", pose="sit_lantern", x=PINAN["x"], z=PINAN["z"], facing=-1),
    "xiaoqing": char(emotion="smile", pose="stand", x=QG1["x"], z=QG1["z"], facing=1),
    "xiaoyu": char(emotion="smile", pose="standwatch", x=XY1["x"], z=XY1["z"], facing=-1),
    "zhezhe": char(emotion="happy", x=ZZ_BENCH[0], y=ZZ_BENCH[1], z=ZZ_BENCH[2]),
})
c["animation"] = [
    # 音樂轉輕；畫面左側柱子後面伸出一隻手（景 square_a1）→ 鏡頭往左帶出手
    A("camera.move", 0.9, 2.6, None, to="a1_hand"),
    A("zhezhe.look", 1.6, 0.6, "zhezhe", yaw=-0.45),
    A("zhezhe.emote", 1.7, None, "zhezhe", emotion="curious"),
    A("zhezhe.twitch", 1.9, None, "zhezhe", side="both"),
    A("puppet.face", 2.0, None, "xiaoqing", emotion="neutral"),
    A("puppet.face", ref(M2, 0.8), None, "xiaoyu", emotion="surprised"),
    # 小宇往前走一步，眼睛被吸引；品安也探頭看
    A("puppet.move", ref(M2, 0.3, end=True), 0.9, "xiaoyu", dx=-0.42),
    A("puppet.lean", ref(M2, 0.5, end=True), 0.9, "pinan", to=0.05),
    A("puppet.face", ref(M2, 0.6, end=True), None, "pinan", emotion="surprised"),
    A("puppet.face", ref(M3, 0.2), None, "xiaoqing", emotion="worried"),
]
c["audioId"] = None
c["music"] = [{"id": "music_shiny", "at": 0.3, "fade": 2.2}]
c["sfx"] = []
c["voStart"] = 2.7
c["tail"] = 2.2
c["fx"] = ["FX8"]

# ───────────────────────────── a1_c003 哪裡怪怪的？（找找看 1） ─────────────────────────────
c = cues["a1_c003"]
N1, N2, N3 = "a1_c003_01", "a1_c003_02", "a1_c003_03"
XYs = XY1["x"] - 0.42
c["initialState"] = start_state("a1_hand", {
    "pinan": char(emotion="surprised", pose="sit_lantern", x=PINAN["x"], z=PINAN["z"], facing=-1),
    "xiaoqing": char(emotion="worried", pose="stand", x=QG1["x"], z=QG1["z"], facing=1),
    "xiaoyu": char(emotion="surprised", pose="standwatch", x=XYs, z=XY1["z"], facing=-1),
    "zhezhe": char(emotion="curious", x=ZZ_BENCH[0], y=ZZ_BENCH[1], z=ZZ_BENCH[2]),
})
c["animation"] = [
    # 小宇停下來、推推眼鏡（歪頭）；鏡頭到兩個孩子的近景
    A("puppet.face", ref(N1, -0.2), None, "xiaoyu", emotion="neutral"),
    A("puppet.tilt", ref(N1, -0.1), 0.7, "xiaoyu", to=0.06),
    A("camera.move", 0.3, 2.4, None, to="a1_two"),
    A("puppet.tilt", ref(N1, 0.4, end=True), 0.7, "xiaoyu", to=0.0),
    # 小晴站在原地只用眼睛看；盒子特寫小窗（景 square_a1 疊層）
    A("puppet.face", ref(N2, 0.0), None, "xiaoqing", emotion="neutral"),
    A("puppet.tilt", ref(N2, 2.4), 0.7, "xiaoqing", to=0.04),
    # 折折問大家
    A("zhezhe.look", ref(N3, -0.3), 0.6, "zhezhe", yaw=0.0),
    A("zhezhe.emote", ref(N3, -0.2), None, "zhezhe", emotion="happy"),
    A("zhezhe.twitch", ref(N3, 1.5), None, "zhezhe", side="r"),
]
c["music"] = []          # 閃亮動機從上一段接著播；停格時引擎自動把配樂壓低（不切到全靜音，下一段開頭不會從無聲突然跳出對白）
c["voStart"] = 0.9
c["tail"] = 3.4
c["fx"] = ["FX7"]

# ───────────────────────────── a1_c004 不用，我們不要 ─────────────────────────────
c = cues["a1_c004"]
R1, R2, R3, R4, R5, R6 = (f"a1_c004_0{i}" for i in range(1, 7))
c["initialState"] = start_state("a1_two", {
    "pinan": char(emotion="surprised", pose="sit_lantern", x=PINAN["x"], z=PINAN["z"], facing=-1),
    "xiaoqing": char(emotion="neutral", pose="stand", x=QG1["x"], z=QG1["z"], facing=1),
    "xiaoyu": char(emotion="neutral", pose="standwatch", x=XYs, z=XY1["z"], facing=-1),
    "zhezhe": char(emotion="happy", x=ZZ_BENCH[0], y=ZZ_BENCH[1], z=ZZ_BENCH[2]),
})
c["animation"] = [
    A("camera.move", 0.7, 2.4, None, to="a1_hand"),
    A("zhezhe.emote", ref(R1, 1.0), None, "zhezhe", emotion="worried"),
    A("puppet.face", ref(R1, 1.2), None, "pinan", emotion="neutral"),
    # 小晴：「電子煙在臺灣是禁止的。」（掌心向前）
    A("puppet.pose", ref(R2, -0.3), 0.24, "xiaoqing", pose="palm"),
    A("puppet.face", ref(R2, -0.05), None, "xiaoqing", emotion="neutral"),
    A("puppet.pose", ref(R3, 0.3, end=True), 0.24, "xiaoqing", pose="stand"),
    # 小宇：「不用，我們不要。」（雙手交叉）
    A("puppet.pose", ref(R4, -0.3), 0.24, "xiaoyu", pose="cross"),
    A("puppet.face", ref(R4, -0.05), None, "xiaoyu", emotion="neutral"),
    # 轉身往右走開（手縮回柱子後面，景 square_a1）；鏡頭跟著兩人，品安留在左後方
    A("puppet.pose", ref(R4, 0.3, end=True), 0.24, "xiaoyu", pose="walk_r"),
    A("puppet.exit", ref(R4, 0.5, end=True), 2.3, "xiaoyu", to=round(XY_MID - XYs, 2)),
    A("puppet.pose", ref(R4, 0.75, end=True), 0.24, "xiaoqing", pose="walk"),
    A("puppet.exit", ref(R4, 0.95, end=True), 2.1, "xiaoqing", to=round(QG_MID - QG1["x"], 2)),
    A("zhezhe.hopTo", ref(R4, 0.5, end=True), 0.8, "zhezhe", pos=[-0.75, 0.0, 1.0], height=0.3),
    A("zhezhe.walkTo", ref(R4, 1.35, end=True), 1.6, "zhezhe", pos=[0.2, 0.0, 1.05]),
    A("camera.move", ref(R4, 1.1, end=True), 3.0, None, to="a1_follow"),
    # 小晴回頭叫品安
    A("puppet.pose", ref(R5, -0.5), 0.24, "xiaoqing", pose="stand"),
    A("puppet.face", ref(R5, -0.1), None, "xiaoqing", emotion="worried"),
    A("zhezhe.look", ref(R5, 0.0), 0.5, "zhezhe", yaw=-0.45),
    # 品安：「你們先走，我把燈籠收好就來。」→ 低頭收燈籠，偷偷回頭看了柱子一眼（翻面）
    A("puppet.face", ref(R6, -0.1), None, "pinan", emotion="smile"),
    A("puppet.pose", ref(R6, 0.55, end=True), 0.24, "pinan", pose="sit_lantern_back"),
    # 兩人繼續往右（鏡頭跟著，不再交代品安）
    A("puppet.pose", ref(R6, 0.2, end=True), 0.24, "xiaoqing", pose="walk"),
    A("puppet.exit", ref(R6, 0.45, end=True), 2.4, "xiaoyu", to=round(XY4["x"] - XY_MID, 2)),
    A("puppet.exit", ref(R6, 0.55, end=True), 2.4, "xiaoqing", to=round(QG4["x"] - QG_MID, 2)),
    A("zhezhe.walkTo", ref(R6, 0.5, end=True), 2.4, "zhezhe", pos=ZZ4),
    A("zhezhe.look", ref(R6, 0.5, end=True), 0.5, "zhezhe", yaw=0.0),
    A("camera.move", ref(R6, 0.5, end=True), 2.8, None, to="a1_follow2"),
]
c["lines"][4]["start"] = ref(R4, 3.3, end=True)
c["music"] = [{"id": "music_courage", "at": ref(R2, -0.2), "fade": 1.6}]
c["sfx"] = [S("sfx_footsteps", ref(R4, 0.7, end=True), 0.4), S("sfx_footsteps", ref(R6, 0.5, end=True), 0.35)]
c["voStart"] = 1.0
c["tail"] = 3.4
c["fx"] = []

# ───────────────────────────── 題卡三段：只調時間（另把孩子、品安、折折留在 a1_c004 結束的位置） ─────────────────────────────
end_chars = {
    "pinan": char(emotion="smile", pose="sit_lantern_back", x=PINAN["x"], z=PINAN["z"], facing=-1),
    "xiaoqing": char(emotion="worried", pose="walk", x=QG4["x"], z=QG4["z"], facing=1),
    "xiaoyu": char(emotion="neutral", pose="walk_r", x=XY4["x"], z=XY4["z"], facing=-1),
    "zhezhe": char(emotion="happy", x=ZZ4[0], y=0, z=ZZ4[2]),
}
c = cues["a1_c005"]
c["initialState"] = start_state("a1_follow2", end_chars)
c["animation"] = [
    A("zhezhe.hush", -0.55, 1.4, "zhezhe"),   # 收摺的瞬間（HUSH_BEATS.snap＝0.55 秒）對上 sfx_quiet_fold（0 秒）
    A("camera.move", 0, 3.2, None, to="quiz"),
    A("light.dim", 0, 1.2, None, to=0.55),
    A("quiz.show", 0.7, 0.6),
]
c = cues["a1_c006"]
c["initialState"] = start_state("quiz", end_chars, light=0.55, quiz=True)
c = cues["a1_c007"]
c["initialState"] = start_state("quiz", end_chars, light=0.55, quiz=True)
for a in c["animation"]:
    if a["name"] == "camera.move":
        a["params"]["to"] = "a1_follow2"
        a["duration"] = 3.4

# ───────────────────────────── a1_c008 一團線（懸念） ─────────────────────────────
c = cues["a1_c008"]
T1, T2, T3 = "a1_c008_01", "a1_c008_02", "a1_c008_03"
c["setFade"] = 0.8           # 題卡後回到故事：換到往燈籠店的街上（同一個廣場景，從暗漸亮）
ST_QG, ST_XY, ST_ZZ = -0.35, 0.6, [0.15, 0.0, 1.1]
STOP_QG, STOP_XY, STOP_ZZ = 1.0, 1.9, [1.85, 0.0, 1.2]
WIN_QG, WIN_XY, WIN_ZZ = 3.55, 4.45, [5.15, 0.0, 1.0]
c["initialState"] = start_state("a1_street", {
    "xiaoqing": char(emotion="smile", pose="walk", x=ST_QG, z=QG4["z"], facing=1),
    "xiaoyu": char(emotion="smile", pose="walk", x=ST_XY, z=XY4["z"], facing=1),
    "zhezhe": char(emotion="happy", x=ST_ZZ[0], y=0, z=ST_ZZ[2]),
})
c["animation"] = [
    # 往右走向燈籠店；風從左邊吹來一張撕破的包裝紙（景 square_a1），停在他們腳邊
    A("puppet.exit", 0.5, 2.3, "xiaoqing", to=round(STOP_QG - ST_QG, 2)),
    A("puppet.exit", 0.55, 2.3, "xiaoyu", to=round(STOP_XY - ST_XY, 2)),
    A("zhezhe.walkTo", 0.6, 2.2, "zhezhe", pos=STOP_ZZ),
    A("puppet.pose", 2.75, 0.24, "xiaoqing", pose="forehead"),
    A("puppet.pose", 2.85, 0.24, "xiaoyu", pose="standwatch"),
    A("puppet.face", 3.1, None, "xiaoqing", emotion="surprised"),
    A("puppet.face", 3.2, None, "xiaoyu", emotion="surprised"),
    A("zhezhe.look", 3.2, 0.5, "zhezhe", yaw=0.45),
    A("zhezhe.emote", 3.3, None, "zhezhe", emotion="curious"),
    # 鏡頭推近：撕開的紙邊裡，糾結著一團灰色的紙線（孩子不靠近、不撿）
    A("camera.cut", 3.6, 0, None, to="a1_wrapper0"),
    A("camera.move", 3.7, 4.0, None, to="a1_wrapper"),
    A("zhezhe.twitch", ref(T1, 0.2), None, "zhezhe", side="both"),
    A("zhezhe.emote", ref(T1, 1.8), None, "zhezhe", emotion="worried"),
    # 小晴：「不要碰。」（雙手交叉）→ 繞開包裝紙，跑到燈籠店窗前
    A("camera.cut", ref(T2, -0.3), 0, None, to="a1_street"),
    A("puppet.pose", ref(T2, -0.35), 0.24, "xiaoqing", pose="cross"),
    A("puppet.face", ref(T2, -0.1), None, "xiaoqing", emotion="neutral"),
    A("puppet.face", ref(T2, 0.3), None, "xiaoyu", emotion="worried"),
    A("puppet.pose", ref(T2, 0.2, end=True), 0.24, "xiaoyu", pose="walk"),
    A("puppet.exit", ref(T2, 1.0, end=True), 3.0, "xiaoyu", to=round(WIN_XY - STOP_XY, 2)),
    A("puppet.pose", ref(T2, 1.4, end=True), 0.24, "xiaoqing", pose="walk"),
    A("puppet.exit", ref(T2, 2.2, end=True), 3.0, "xiaoqing", to=round(WIN_QG - STOP_QG, 2)),
    A("zhezhe.hopTo", ref(T2, 0.5, end=True), 0.9, "zhezhe", pos=[2.5, 0.0, 0.55], height=0.45),
    A("zhezhe.hopTo", ref(T2, 5.25, end=True), 1.0, "zhezhe", pos=WIN_ZZ, height=0.4),
    A("camera.move", ref(T2, 0.9, end=True), 3.0, None, to="a1_window"),
    A("puppet.pose", ref(T2, 4.35, end=True), 0.24, "xiaoyu", pose="standwatch"),
    A("puppet.pose", ref(T2, 5.55, end=True), 0.24, "xiaoqing", pose="forehead"),
    # 窗裡的剪影想舉起竹篾，手卻往旁一歪，竹篾輕輕掉在地上（景 square_a1，_02 結束後 5.8 秒）
    A("puppet.face", ref(T2, 6.45, end=True), None, "xiaoyu", emotion="worried"),
    A("puppet.face", ref(T2, 6.6, end=True), None, "xiaoqing", emotion="worried"),
    A("zhezhe.emote", ref(T2, 6.4, end=True), None, "zhezhe", emotion="worried"),
    A("zhezhe.twitch", ref(T2, 6.2, end=True), None, "zhezhe", side="both"),
    A("zhezhe.look", ref(T2, 6.2, end=True), 0.5, "zhezhe", yaw=-0.2),
    # 燈光慢慢暗下，停在窗前
    A("light.dim", ref(T3, 0.4, end=True), 3.2, None, to=0.8),
]
c["lines"][2]["start"] = ref(T2, 7.2, end=True)
c["audioId"] = None
c["music"] = [{"id": "music_town", "at": 0, "fade": 1.0, "gain": 0.7}, {"id": "music_m4_light", "at": 3.3, "fade": 3.0, "gain": 0.42}]   # 包裝紙落地起，操偶線動機極輕出現（懸念）
c["sfx"] = [S("sfx_plane_whoosh", 0.9, 0.45), S("sfx_paper_rustle", 3.3, 0.3), S("sfx_footsteps", 0.55, 0.35), S("sfx_footsteps", ref(T2, 1.0, end=True), 0.35),
            S("sfx_bamboo_drop", ref(T2, 6.65, end=True), 0.4)]
c["voStart"] = 6.3
c["tail"] = 3.4
c["fx"] = ["FX12", "FX10", "FX4"]

d["cues"] = [cues[c["id"]] for c in d["cues"]]
tmp = SEG.with_suffix(".json.tmp_a1")
tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
r = subprocess.run(["node", "-e", f"JSON.parse(require('fs').readFileSync({json.dumps(str(tmp))},'utf8'));console.log('ok')"], capture_output=True, text=True)
if r.returncode != 0 or "ok" not in r.stdout:
    print(r.stderr)
    sys.exit(1)
os.replace(tmp, SEG)
print("wrote", SEG)
