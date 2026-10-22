"""第三幕（a3）段落檔產生器：讀 app/cues/show/a3.json（保留台詞、題目、cue 編號、流程欄位與 storyboard），
改寫每個 cue 的景、起始狀態、動畫、配樂、音效、voStart、tail，寫到暫存檔、驗證 JSON 再搬回。

用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/make_a3_cues.py
"""
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SEG = ROOT / "app/cues/show/a3.json"


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


def pose(who, start, p):
    return A("puppet.pose", start, who, 0.24, pose=p)


def face(who, start, e):
    return A("puppet.face", start, who, emotion=e)


def ch(pose_=None, x=None, z=None, emotion="smile", facing=None, y=None):
    c = {"visible": True, "emotion": emotion}
    if pose_:
        c["pose"] = pose_
    if x is not None:
        c["x"] = x
    if y is not None:
        c["y"] = y
    if z is not None:
        c["z"] = z
    if facing is not None:
        c["facing"] = facing
    return c


def stage(cam, light=1, **kw):
    s = {"curtain": "open", "camera": cam, "light": light}
    s.update(kw)
    return s


HOOD = [-1.38, 1.62, 0.05]       # 小宇連帽（背在畫面右側；小宇 standwatch 臉朝左）
ZZ_Q = [-4.7, 0.0, 4.15]           # 題卡模式折折的全劇統一位置（主線補充裁定；台口左前）
KID_X, KID_Z = 3.45, 4.0           # a3_c004 練習卡兩側的示範位置（卡寬 6，左右緣 ±3）
PINAN_X0, PINAN_Z = 5.45, -1.1     # a3_c003 品安起點：站姿（較窄）整個藏在警衛室右半段實牆後面（窗洞 x ≤4.85 右邊、房子實際右緣 x 5.93 左邊），矮牆（z −1.25）前面
PINAN_DX, PINAN_T = 3.6, 3.75      # 往右走 3.6 單位、3.75 秒（約 0.96 單位／秒），最後一格整個人（含後腳）已在畫面右緣外
LIN_DX, LIN_T = 2.15, 3.2          # a3_c008 林老師往右走出 a3_cls_lin 畫面（約 0.67 單位／秒：白襯衫＋深色外套的邊掃過細格不超過每秒 3 次）


def build(cues):
    by = {c["id"]: c for c in cues}

    # ───────────── a3_c001 又是那隻手（騎樓上學路，早上）─────────────
    c = by["a3_c001"]
    c["set"] = "a3_arcade"
    c["initialState"] = {"stage": stage("a3_follow0"), "characters": {
        "xiaoqing": ch("walk", -2.2, 0.45, "smile", 1),
        "xiaoyu": ch("walk", -3.3, 0.15, "smile", 1),
        "zhezhe": ch(None, -1.05, 1.15, "happy", y=0.0),
    }}
    c["animation"] = [
        # 跟拍：孩子往右走（學校在右），鏡頭同速正弦緩動；走到定點翻面站好（小宇戴手錶的站姿 standwatch，臉朝左＝看得到從左邊伸出的手）
        A("camera.move", 0.35, duration=3.2, ease="sine", to="a3_follow1"),
        A("puppet.exit", 0.3, "xiaoqing", 3.0, "sine", to=1.6),
        A("puppet.exit", 0.35, "xiaoyu", 3.0, "sine", to=1.6),
        pose("xiaoqing", 3.15, "stand"),
        pose("xiaoyu", 3.3, "standwatch"),
        # 折折摺成紙飛機想帶路：往右前方飛、繞一大圈回來，落進小宇的連帽（在小宇背後，身體擋住下半截），摺回小小的貓
        A("zhezhe.fold", 0.15, "zhezhe", 1.2, form="plane", scale=0.65),
        A("zhezhe.flyTo", 1.4, "zhezhe", 1.6, pos=[1.5, 2.45, 0.9], height=0.4),
        A("zhezhe.flyTo", 3.0, "zhezhe", 1.6, pos=HOOD, height=0.7),
        A("zhezhe.fold", 4.65, "zhezhe", 0.9, form="idle", scale=0.5),
        A("zhezhe.emote", "a3_c001_02", "zhezhe", emotion="proud"),
        face("xiaoyu", "a3_c001_01-0.3", "smile"),
        face("xiaoqing", "a3_c001_02+0.6", "smile"),
        # 手出現前先硬切到紅磚柱（硬切＝一次變化；橫移會讓騎樓燈籠串一格一格掃過，細格光敏超標）
        A("camera.cut", "a3_c001_02.end+0.25", duration=0, to="a3_hand"),
        A("zhezhe.twitch", "a3_c001_03-1.0", "zhezhe", side="both"),
        A("zhezhe.emote", "a3_c001_03-0.7", "zhezhe", emotion="worried"),
        face("xiaoyu", "a3_c001_03-0.9", "surprised"),
        face("xiaoqing", "a3_c001_03-0.6", "worried"),
        face("xiaoyu", "a3_c001_03+1.6", "neutral"),
    ]
    c["audioId"] = "music_zhezhe"
    c["music"] = [{"id": "music_shiny", "at": "a3_c001_03-1.6", "fade": 2.0}]
    c["sfx"] = [
        {"id": "sfx_fold", "at": 0.2, "gain": 0.55},
        {"id": "sfx_plane_whoosh", "at": 1.9, "gain": 0.8},
        {"id": "sfx_quiet_fold", "at": 4.7, "gain": 0.35},
    ]
    c["voStart"] = 4.9
    c["tail"] = 1.1
    lines = {l["id"]: l for l in c["lines"]}
    lines["a3_c001_03"]["start"] = "a3_c001_02.end+2.0"   # 修正第 1 輪：縮 0.3 秒（總長不增加）

    # ───────────── a3_c002 我想一想 ─────────────
    c = by["a3_c002"]
    c["set"] = "a3_arcade"
    c["initialState"] = {"stage": stage("a3_xy_close"), "characters": {
        "xiaoqing": ch("stand", -0.6, 0.45, "worried", 1),
        "xiaoyu": ch("standwatch", -1.7, 0.15, "neutral", 1),
        "zhezhe": ch(None, HOOD[0], HOOD[2], "worried", y=HOOD[1]),
    }}
    c["animation"] = [
        A("zhezhe.fold", -2.0, "zhezhe", 0.3, form="idle", scale=0.5),     # 承接上一段：在帽子裡的小貓（不在畫面上變形）
        # 腦中小畫面（回想小圓窗由景在 0.8 秒打開）；推推眼鏡、想一想
        pose("xiaoyu", 1.0, "glasses"),
        # 抬頭、掌心向外（朝畫面左的手），語氣平穩（翻面在「我想一想」字幕還在時，腳不在字幕開關的同一秒裡動）
        pose("xiaoyu", "a3_c002_01.end-0.25", "palmno"),
        face("xiaoyu", "a3_c002_01.end-0.1", "neutral"),
        A("zhezhe.emote", "a3_c002_02.end+0.1", "zhezhe", emotion="proud"),
        # 「不用，我不試。我先離開。」字幕還在時切到稍遠的中景（紅磚柱與手在左）
        A("camera.cut", "a3_c002_02.end-0.3", duration=0, to="a3_leave"),
        face("xiaoqing", "a3_c002_03-0.25", "neutral"),
        A("zhezhe.hopTo", "a3_c002_02.end+0.5", "zhezhe", 0.8, pos=[-1.0, 0.0, 1.15], height=0.4),
        A("zhezhe.emote", "a3_c002_02.end+1.4", "zhezhe", emotion="happy"),
        # 「我們走」：兩人轉身往右（安全方位）朝校門口走，沒有回頭爭辯（走得短而穩：細格光敏）
        pose("xiaoqing", "a3_c002_03.end+0.25", "walk"),
        pose("xiaoyu", "a3_c002_03.end+0.55", "walk"),
        A("puppet.exit", "a3_c002_03.end+0.4", "xiaoqing", 2.8, "sine", to=1.3),
        A("puppet.exit", "a3_c002_03.end+0.7", "xiaoyu", 2.8, "sine", to=1.3),
        face("xiaoyu", "a3_c002_03.end+0.7", "smile"),
        A("zhezhe.walkTo", "a3_c002_03.end+0.65", "zhezhe", 2.6, pos=[0.4, 0.0, 1.15]),
    ]
    c["audioId"] = None
    c["music"] = [{"id": "music_courage", "at": "a3_c002_01.end+0.3", "fade": 1.6}]
    c["sfx"] = [{"id": "sfx_footsteps", "at": "a3_c002_03.end+0.5", "gain": 0.3}]
    c["voStart"] = 1.9
    c["tail"] = 3.9   # 修正第 1 輪：手縮回柱子後面提早（景 a3.ts），縮 0.4 秒
    lines = {l["id"]: l for l in c["lines"]}
    lines["a3_c002_02"]["start"] = "a3_c002_01.end+0.95"

    # ───────────── a3_c003 告訴林老師（早上的校門口）─────────────
    c = by["a3_c003"]
    c["set"] = "a3_gate"
    c["initialState"] = {"stage": stage("a3_gate_in"), "characters": {
        "lin": ch("stand", 3.95, 0.3, "smile", 1),
        "xiaoqing": ch("walk", 2.55, 0.4, "smile", 1),
        "xiaoyu": ch("walk", 1.5, 0.12, "smile", 1),
        "zhezhe": ch(None, 0.85, 1.15, "happy", y=0.0),
        # 修正第 1 輪：品安在警衛室（z −0.95）和校內矮牆（z −1.25）之間的通道，起點整個藏在警衛室右半段後面
        "pinan": ch("stand", PINAN_X0, PINAN_Z, "neutral", 1),
    }}
    c["animation"] = [
        # 林老師在校門內迎接學生（臉朝校內）；兩人從左邊（校門外）走進來
        A("puppet.enter", 0.3, "xiaoqing", 2.4, "linear", **{"from": -1.2}),
        A("puppet.enter", 0.4, "xiaoyu", 2.4, "linear", **{"from": -1.2}),
        A("zhezhe.walkTo", 0.35, "zhezhe", 2.4, pos=[2.05, 0.0, 1.2]),
        pose("xiaoqing", 2.5, "stand"),
        pose("xiaoyu", 2.65, "standwatch"),
        face("xiaoqing", 2.7, "neutral"),
        face("xiaoyu", 2.85, "neutral"),
        # 小晴開口，林老師轉過來蹲下、和孩子一樣高（蹲姿臉朝左）
        pose("lin", "a3_c003_01+0.5", "crouch"),
        face("lin", "a3_c003_01+2.6", "neutral"),
        face("lin", "a3_c003_02", "smile"),
        face("lin", "a3_c003_02+2.0", "neutral"),
        face("lin", "a3_c003_03", "smile"),
        face("xiaoyu", "a3_c003_03+0.8", "smile"),
        face("xiaoqing", "a3_c003_03+1.0", "smile"),
        # 約 3 秒無台詞：品安低頭、雙手抓著背帶，從後面快步走過（不推近、不加音效、不交代原因）；折折的耳朵動了一下
        # 修正第 1 輪（導演 a3 第 1 項）：全身入鏡（在矮牆前面的通道，不再藏在牆後只露頭），從警衛室後面走出來、往右（校內）
        # 快步走出畫面右緣；等速、約 3 秒，大小約小晴的 0.9 倍
        pose("pinan", "a3_c003_03.end+0.15", "walk_straps"),       # 起步時才翻成走路姿勢（朝右；翻面在警衛室後面）
        A("puppet.exit", "a3_c003_03.end+0.25", "pinan", PINAN_T, "linear", to=PINAN_DX),
        A("zhezhe.twitch", "a3_c003_03.end+0.9", "zhezhe", side="r"),
        A("zhezhe.look", "a3_c003_03.end+1.0", "zhezhe", 0.6, yaw=0.35),
        A("zhezhe.look", "a3_c003_03.end+3.2", "zhezhe", 0.6, yaw=0.0),
    ]
    c["audioId"] = None
    c["sfx"] = [{"id": "sfx_gate_ambience", "at": 0, "gain": 0.7}]
    c["voStart"] = 2.9
    c["tail"] = 4.0

    # ───────────── a3_c004 換大家練習（台口前緣的練習卡）─────────────
    # 修正第 1 輪：鏡頭推近一級（a3_apron2），兩個示範的孩子站到練習卡左右兩邊、往前一步（z 4.0），比原來大約 1.3 倍；
    # 折折一開始就在題卡模式的統一位置（台口左前 ZZ_Q），下一段出題不必再移動（cue 接縫一致）
    c = by["a3_c004"]
    c["set"] = "a3_card"
    c["initialState"] = {"stage": stage("a3_apron2"), "characters": {
        "xiaoqing": ch("stand", -KID_X, KID_Z, "smile", 1),
        "xiaoyu": ch("standwatch", KID_X, KID_Z, "smile", 1),
        "zhezhe": ch(None, ZZ_Q[0], ZZ_Q[2], "happy", y=ZZ_Q[1]),
    }}
    W = "a3_c004_02"
    c["animation"] = [
        # 折折摺出小紙卡；大紙卡由景在 1.6 秒立起（攤開）；折折摺回貓（都在換景漸亮 0.8 秒之後）
        A("zhezhe.fold", 0.85, "zhezhe", 0.9, form="card", scale=0.55),
        A("zhezhe.fold", 2.3, "zhezhe", 0.8, form="idle"),
        A("zhezhe.emote", 3.1, "zhezhe", emotion="happy"),
        A("puppet.tilt", "a3_c004_01+1.5", "xiaoyu", 0.4, to=0.06),
        A("puppet.tilt", "a3_c004_01+2.6", "xiaoyu", 0.5, to=0.0),
        # 口訣四個動作（對折折念到的字；翻面在字的開頭前 0.12 秒）：不碰＝雙手胸前交叉、不試＝手掌往外、先離開＝手指向右（安全方向）、
        # 找大人＝手掌放額前張望（小晴 forehead_l 朝左、小宇 forehead 朝右，髮夾都在原來那一側）
        # 同一個角色兩次翻面至少隔 1 秒（細格光敏：翻面一次＝外框兩次明暗變化），所以兩人輪流，順序和練習卡小圖一樣
        pose("xiaoqing", f"{W}+1.63", "cross"),
        pose("xiaoyu", f"{W}+2.13", "palmno"),
        pose("xiaoqing", f"{W}+2.80", "pointr"),
        pose("xiaoyu", f"{W}+3.46", "forehead"),
        pose("xiaoqing", f"{W}.end+0.2", "forehead_l"),
        face("xiaoqing", f"{W}+1.75", "neutral"), face("xiaoyu", f"{W}+2.25", "neutral"),
        face("xiaoqing", f"{W}.end+0.9", "smile"), face("xiaoyu", f"{W}.end+0.6", "smile"),
    ]
    c["audioId"] = None
    c["sfx"] = [{"id": "sfx_fold", "at": 0.9, "gain": 0.6}, {"id": "sfx_paper_rustle", "at": 1.65, "gain": 0.6}]
    c["voStart"] = 3.0
    c["tail"] = 1.8

    END4 = {
        "xiaoqing": ch("forehead_l", -KID_X, KID_Z, "smile", 1),
        "xiaoyu": ch("forehead", KID_X, KID_Z, "smile", 1),
        "zhezhe": ch(None, ZZ_Q[0], ZZ_Q[2], "happy", y=ZZ_Q[1]),
    }
    # ───────────── a3_c005–a3_c007 Q4 題卡 ─────────────
    # 修正第 1 輪（主線補充裁定＋更正裁定）：
    #  - 折折在統一位置 {x −4.7, y 0, z 4.15}（a3_c004 起就站在這裡）；先說「第四題！」再 zhezhe.fold card、DOM 題卡跟著出現
    #  - 練習卡近景 → 題卡鏡位（quiz，看得到台口八盞燈）是大幅縮放、亮度差大：不用運鏡、也不一格硬切；
    #    fade.out 0.6 秒（同時舞台燈調到 0.55）→ 全暗時切鏡、練習卡收平 → fade.in 0.6 秒；題卡淡入時鏡頭不動
    #  - 「第四題！」1.4 秒才開始（不壓在 sfx_quiet_fold 上）
    c = by["a3_c005"]
    c["set"] = "a3_card"
    c["initialState"] = {"stage": stage("a3_apron2"), "characters": json.loads(json.dumps(END4))}
    Q1 = "a3_c005_01"
    c["animation"] = [
        A("fade.out", 0, duration=0.6, to=1),
        A("light.dim", 0, duration=0.6, to=0.55),
        A("camera.cut", 0.6, duration=0, to="quiz"),
        A("fade.in", 0.62, duration=0.6),
        A("zhezhe.hush", 0.0, "zhezhe", 1.4),            # 收聲訊號（對 sfx_quiet_fold at 0）
        A("zhezhe.emote", 1.2, "zhezhe", emotion="happy"),
        A("zhezhe.fold", f"{Q1}.end+0.05", "zhezhe", 1.2, form="card"),
        A("quiz.show", f"{Q1}.end+0.3", duration=0.55),
        A("zhezhe.fold", f"{Q1}.end+1.35", "zhezhe", 0.7, form="idle"),
    ]
    c["sfx"] = [{"id": "sfx_quiet_fold", "at": 0}, {"id": "sfx_card_in", "at": f"{Q1}.end+0.3", "gain": 0.8}]
    c["voStart"] = 1.4
    c["tail"] = 1.0
    lines = {l["id"]: l for l in c["lines"]}
    lines["a3_c005_02"]["start"] = f"{Q1}.end+0.85"

    c = by["a3_c006"]
    c["set"] = "a3_card"
    c["initialState"] = {"stage": {"curtain": "open", "camera": "quiz", "light": 0.55, "quiz": True},
                         "characters": json.loads(json.dumps(END4))}
    c["animation"] = [
        A("quiz.reveal", 0.3, duration=0.45),
        A("zhezhe.emote", 0.2, "zhezhe", emotion="curious"),
    ]
    c["sfx"] = [{"id": "sfx_stamp", "at": 0.3}]
    c["voStart"] = 1.0
    c["tail"] = 1.2

    c = by["a3_c007"]
    c["set"] = "a3_card"
    c["initialState"] = {"stage": {"curtain": "open", "camera": "quiz", "light": 0.55, "quiz": True},
                         "characters": json.loads(json.dumps(END4))}
    # 下一段 a3_c008 換景（引擎自動漸暗 0.6 秒）：鏡頭停在題卡鏡位（看得到台口上方第四盞燈亮了），不推回故事鏡位
    c["animation"] = [
        A("lamp.light", 0.3, duration=1.5, index=4),
        A("zhezhe.emote", 0.2, "zhezhe", emotion="happy"),
        A("quiz.hide", "a3_c007_01.end+0.3", duration=0.6),
        A("light.restore", "a3_c007_01.end+0.3", duration=1.2),
    ]
    c["sfx"] = [{"id": "sfx_lamp_on", "at": 0.3}]
    c["voStart"] = 1.9
    c["tail"] = 0.6

    # ───────────── a3_c008 放學以後（教室午後，懸念）─────────────
    c = by["a3_c008"]
    c["set"] = "a3_classroom"
    c["initialState"] = {"stage": stage("a3_cls_mid"), "characters": {
        "lin": ch("stand_m", 1.3, 0.2, "smile", 1),
        "xiaoqing": ch("stand", -1.15, 0.45, "smile", 1),
        "xiaoyu": ch("standwatch_m", -2.4, 0.1, "smile", 1),
        "zhezhe": ch(None, -1.8, 1.25, "happy", y=0.0),
    }}
    L2, L3, L4 = "a3_c008_02", "a3_c008_03", "a3_c008_04"
    c["animation"] = [
        # 修正第 1 輪（導演 a3 第 3 項）：兩人＋折折三人中景（頭到腳都在畫面裡）：聽到「阿樂叔叔」互看一眼、折折耳朵慢慢壓平
        #（取代原來的兩人近景＋只拍到腿的折折插鏡，少一次切鏡）
        A("camera.cut", f"{L2}+2.3", duration=0, to="a3_cls_trio"),
        face("xiaoqing", f"{L2}+4.4", "worried"),
        face("xiaoyu", f"{L2}+4.8", "worried"),
        A("puppet.tilt", f"{L2}+5.3", "xiaoyu", 0.5, to=0.07),
        A("puppet.tilt", f"{L2}+5.6", "xiaoqing", 0.5, to=-0.06),
        A("zhezhe.emote", f"{L2}.end+0.15", "zhezhe", emotion="worried"),
        A("puppet.tilt", f"{L2}.end+0.6", "xiaoyu", 0.6, to=0.0),
        # 林老師與小晴中景：小晴舉手、往前一步，當場告訴林老師（切鏡頭、舉手、放下手各隔 ≥0.5／1 秒）
        A("camera.cut", f"{L2}.end+1.0", duration=0, to="a3_cls_lin"),
        pose("xiaoqing", f"{L2}.end+1.5", "reach"),
        face("lin", f"{L2}.end+1.65", "neutral"),
        pose("xiaoqing", f"{L2}.end+2.75", "stand"),
        A("puppet.move", f"{L2}.end+2.8", "xiaoqing", 0.6, "sine", dx=0.5),
        A("puppet.tilt", f"{L2}.end+2.9", "xiaoqing", 0.4, to=0.0),
        face("lin", f"{L3}+1.6", "worried"),
        face("lin", L4, "smile"),
        face("lin", f"{L4}+2.3", "neutral"),
        face("xiaoqing", f"{L4}+6.0", "neutral"),
        # 修正第 1 輪（導演 a3 第 2 項、美術 a3 第 1 項）：林老師翻回朝右的站姿、手上拿著手機（景放在她手上），
        # 在這個中景裡往右走出畫面（約 2 秒，切鏡前已經完全出畫）去走廊打電話
        pose("lin", f"{L4}.end+0.15", "stand"),
        A("puppet.exit", f"{L4}.end+0.75", "lin", LIN_T, "linear", to=LIN_DX),
        # 兩個孩子轉頭看窗外（窗在他們左後方）：小晴、小宇先後翻成朝左
        pose("xiaoqing", f"{L4}.end+1.5", "stand_m"),
        face("xiaoqing", f"{L4}.end+1.75", "worried"),
        pose("xiaoyu", f"{L4}.end+2.3", "standwatch"),
        face("xiaoyu", f"{L4}.end+2.55", "worried"),
        # 最後一個鏡頭（林老師已經走出畫面）：窗外輕擺的燈籠串在上方、兩個孩子在右下望著它（懸念）
        A("camera.cut", f"{L4}.end+4.1", duration=0, to="a3_cls_end"),
        A("zhezhe.look", f"{L4}.end+4.35", "zhezhe", 0.8, yaw=-0.45),
    ]
    c["audioId"] = None
    c["music"] = [
        {"id": "none", "at": 0, "fade": 1.2},
        {"id": "music_m4_light", "at": f"{L2}.end+0.1", "fade": 2.5, "gain": 0.5},
    ]
    c["sfx"] = [{"id": "sfx_school_bell", "at": 0.1, "gain": 0.6}]
    c["voStart"] = 1.15
    c["tail"] = 5.45
    lines = {l["id"]: l for l in c["lines"]}
    lines[L2]["start"] = "a3_c008_01.end+0.3"
    lines[L3]["start"] = f"{L2}.end+2.95"
    return cues


def main():
    d = json.loads(SEG.read_text(encoding="utf-8"))
    d["set"] = "a3_arcade"
    d["characters"] = {
        "xiaoqing": {"name": "小晴", "rig": "standee:xiaoqing", "x": -0.6, "z": 0.45, "facing": 1, "fallback": "child"},
        "xiaoyu": {"name": "小宇", "rig": "standee:xiaoyu", "x": -1.7, "z": 0.15, "facing": 1, "fallback": "child"},
        "zhezhe": {"name": "折折", "rig": "zhezhe", "x": -1.0, "z": 1.1, "facing": 1, "fallback": "child"},
        "pinan": {"name": "品安", "rig": "standee:pinan", "x": -2.9, "z": -0.55, "facing": 1, "fallback": "child"},
        "lin": {"name": "林老師", "rig": "standee:lin", "x": 3.95, "z": 0.3, "facing": 1, "fallback": "adult"},
    }
    d["_note"] = ("第三幕代理（G5 第二批）。景：a3_arcade（騎樓上學路）、a3_gate（早上的校門口）、a3_card（台口前緣練習卡）、"
                  "a3_classroom（教室午後），程式在 app/src/sets/a3.ts。本檔由 review/G5/a3/scripts/make_a3_cues.py 產生。")
    d["cues"] = build(d["cues"])
    txt = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    json.loads(txt)
    fd, tmp = tempfile.mkstemp(prefix="a3_", suffix=".json", dir=str(SEG.parent.parent.parent.parent / "review/G5/a3"))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(txt)
    json.loads(Path(tmp).read_text(encoding="utf-8"))
    os.replace(tmp, SEG)
    print("wrote", SEG.relative_to(ROOT), len(d["cues"]), "cues")


if __name__ == "__main__":
    main()
