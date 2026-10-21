"""全劇動態分鏡底稿產生器（v1.2 P6 動態分鏡；G5 開工前共用元件）。

依 script/劇本_v03.md、節拍表_v03.md、八題_v03.md、時長估算_v03.md 與 audio/vo/timings.json，產生
app/cues/show/index.json 與 a0.json（開場）、a1–a6.json（六幕）、a7.json（複習與收束）、a8.json（閉幕）。

- 每個劇本 cue 編號一個 cue：kind（故事／互動卡＝scene、題卡出題＝quiz、題卡揭答＝reveal、點燈＝lamp）、
  台詞（audioId vo_<台詞編號>、說話者、字幕原文一字不改）、教師欄文字（〔教師〕）放 teacherNote、壓縮級別、
  「落後 3 分鐘可略」的句子標 skippableWhenBehind、短版「只播 _NN」寫成 level2.lines、查核點（時長估算 4.3 節＋第 5 節門檻）。
- 時間：台詞依實際配音長度自動接續（引擎讀音檔長度；這裡只依劇本「動作」秒數訂 voStart 與 tail），題卡三段用固定模板。
- 八題：題目、選項與正解取自 八題_v03.md（答案 2、3、1、1、3、2、3、2）；揭答後的點燈 cue 用 lamp.light 點第 N 盞燈。
- G4 已完成的 cue（a0_c000、a0_c001、a2_c002、a2_c004、a8_c002、a8_c003）從 app/cues/g4.json 原樣搬進對應段落，
  只改全劇流程與授課時鐘需要的欄位（next、prevStable、checkpoint；a0_c001 補上台詞 a0_c001_01；a8_c002 的起始角色改成謝幕後、
  沒有操偶線的狀態），表演、鏡頭、配樂、音效、時間都不動。
- 還沒做景的 cue 用中性的牛皮紙舞台佔位景 kraft_stage；燈籠店的段落用 G4 的 workshop_g4。
- 每個 cue 附 storyboard（劇本舞台指示＋節拍表的節拍、角色、鏡頭、聲音），給各幕代理參考，引擎不讀。

用法（專案根目錄）：
  /opt/anaconda3/bin/python3 tools/build_show_skeleton.py            只寫還不存在的段落檔（各幕代理改過的檔不會被覆寫）
  /opt/anaconda3/bin/python3 tools/build_show_skeleton.py --force    全部重寫（會蓋掉各幕代理的修改，只有主線能用）
  /opt/anaconda3/bin/python3 tools/build_show_skeleton.py --check    不寫檔，只列每段預估長度與預算
"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "script"
OUT = ROOT / "app/cues/show"
ANSWERS = [2, 3, 1, 1, 3, 2, 3, 2]

# 角色：說話者名稱 → (角色 id, rig, 佔位紙偶)。邀請者（只出現手）、執勤人員（只有聲音）、旁白沒有紙偶
CHARS = {
    "阿樂叔叔": ("ale", "ale_v03", "adult"),
    "小晴": ("xiaoqing", "standee:xiaoqing", "child"),
    "小宇": ("xiaoyu", "standee:xiaoyu", "child"),
    "折折": ("zhezhe", "zhezhe", "child"),
    "品安": ("pinan", "standee:pinan", "child"),
    "葉護理師": ("ye", "standee:ye", "adult"),
    "林老師": ("lin", "standee:lin", "adult"),
    "陳伯伯": ("chen", "standee:chen", "adult"),
}
NAME_OF = {v[0]: k for k, v in CHARS.items()}
# 節拍表「角色」欄的簡稱
ALIASES = {"阿樂": "ale", "小晴": "xiaoqing", "小宇": "xiaoyu", "折折": "zhezhe", "品安": "pinan", "葉護理師": "ye", "林老師": "lin", "陳伯伯": "chen"}
# 預設站位（危險在左、安全與求助在右；ale、小晴、小宇＝G4 站位）
PLACE = {
    "ale": {"x": -2.6, "z": 0, "facing": 1},
    "chen": {"x": -0.9, "z": -0.4, "facing": 1},
    "zhezhe": {"x": 0.55, "z": 1.2, "facing": 1},
    "xiaoqing": {"x": 1.85, "z": 0.45, "facing": 1},
    "xiaoyu": {"x": 3.35, "z": -0.5, "facing": -1},
    "pinan": {"x": 4.5, "z": -0.1, "facing": -1},
    "lin": {"x": 5.3, "z": -0.6, "facing": -1},
    "ye": {"x": 6.2, "z": -0.3, "facing": -1},
}
# 段落：檔名、id、景、各 cue 換景（其餘用段落景）、名冊順序（G4 三人在前，renderOrder 與 G4 相同）
SEGMENTS = [
    {"id": "a0", "set": "workshop_g4", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe"]},
    {"id": "a1", "set": "kraft_stage", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe", "pinan"]},
    {"id": "a2", "set": "workshop_g4", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe", "ye"], "cueSets": {"a2_c013": "kraft_stage"},
     "place": {"ye": {"x": 0.95, "z": 0.95, "facing": -1}}},
    {"id": "a3", "set": "kraft_stage", "cast": ["xiaoqing", "xiaoyu", "zhezhe", "pinan", "lin"]},
    {"id": "a4", "set": "kraft_stage", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe", "lin", "chen"]},
    {"id": "a5", "set": "kraft_stage", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe", "lin", "chen", "ye"]},
    {"id": "a6", "set": "kraft_stage", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe", "pinan", "lin", "ye"], "cueSets": {"a6_c009": "workshop_g4"},
     "place": {}},
    {"id": "a7", "set": "kraft_stage", "cast": ["xiaoqing", "xiaoyu", "zhezhe", "pinan"]},
    {"id": "a8", "set": "workshop_g4", "cast": ["ale", "xiaoqing", "xiaoyu", "zhezhe", "pinan", "lin", "ye", "chen"],
     "place": {"chen": {"x": -4.4, "z": 0.4, "facing": 1}, "lin": {"x": -3.6, "z": 0.9, "facing": 1}, "pinan": {"x": 4.6, "z": 0.3, "facing": -1}, "ye": {"x": 5.6, "z": 0.2, "facing": -1}}},
]
G4_CUES = {"a0_c000": "a0", "a0_c001": "a0", "a2_c002": "a2", "a2_c004": "a2", "a8_c002": "a8", "a8_c003": "a8"}
# 段落配樂（底稿；各幕代理換成自己的配樂設計）：cue → audioId
MUSIC = {"a0_c002": "music_town", "a1_c001": "music_town", "a2_c001": "music_town", "a2_c012": "music_town", "a2_c013": "music_m4_light",
         "a3_c001": "music_town", "a4_c001": "music_m4_light", "a5_c001": "music_m4_light", "a5_c008": "music_town", "a6_c001": "music_town",
         "a7_c001": "music_town", "a8_c001": "music_town"}
KIND = {"故事": "scene", "互動卡": "scene", "題卡出題": "quiz", "題卡揭答": "reveal", "點燈": "lamp"}


def r1(x):
    return round(float(x) + 1e-9, 1)


# ---------------------------------------------------------------- 讀劇本
def parse_script():
    text = (SCRIPT / "劇本_v03.md").read_text(encoding="utf-8")
    acts, cues = {}, []
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = re.match(r"^## (a\d)｜(.+)$", line)
        if m:
            acts[m.group(1)] = m.group(2).strip()
            cur = None
            continue
        m = re.match(r"^### (a\d_c\d{3})｜(.+)$", line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2).strip(), "info": {}, "lines": [], "teacher": [], "directions": []}
            cues.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("- 類型："):
            for part in line[2:].split("｜"):
                if "：" in part:
                    k, v = part.split("：", 1)
                    cur["info"][k.strip()] = v.strip()
            continue
        m = re.match(r"^\[(a\d_c\d{3}_\d{2})\] ([^：]+)：(.+)$", line)
        if m:
            cur["lines"].append({"id": m.group(1), "speaker": m.group(2).strip(), "text": m.group(3).strip()})
            continue
        if line.startswith("〔教師〕"):
            cur["teacher"].append(line[len("〔教師〕"):].strip())
            continue
        if line.startswith("（") and line.endswith("）"):
            cur["directions"].append(line)
    return acts, cues


def parse_beats():
    rows = {}
    for raw in (SCRIPT / "節拍表_v03.md").read_text(encoding="utf-8").splitlines():
        if not raw.startswith("| a"):
            continue
        cols = [c.strip() for c in raw.strip().strip("|").split("|")]
        if len(cols) < 6:
            continue
        ids = re.findall(r"a\d_c\d{3}", cols[0])
        if not ids:
            continue
        if "–" in cols[0] and len(ids) == 2:
            a, b = ids
            act = a[:2]
            ids = [f"{act}_c{n:03d}" for n in range(int(a[4:]), int(b[4:]) + 1)]
        for i in ids[:1] if "–" not in cols[0] else ids:
            rows[i] = {"beat": cols[1], "cast": cols[2], "camera": cols[3], "fx": re.findall(r"FX\d+", cols[4]), "sound": cols[5]}
    return rows


def parse_quiz():
    text = (SCRIPT / "八題_v03.md").read_text(encoding="utf-8")
    qs = {}
    for blk in re.split(r"\n### ", text)[1:]:
        m = re.match(r"(Q\d)｜", blk)
        if not m:
            continue
        qid = m.group(1)
        cm = re.search(r"出題 (a\d_c\d{3})｜揭答 (a\d_c\d{3})｜點燈 (a\d_c\d{3})", blk)
        stem = re.search(r"- 題幹：(.+)", blk).group(1).strip()
        opts, ans = [], None
        for k in (1, 2, 3):
            om = re.search(rf"^- {k}　(.+?)\s*(\*\*〔正解〕\*\*)?\s*$", blk, re.M)
            opts.append(om.group(1).strip())
            if om.group(2):
                ans = k
        qs[qid] = {"qid": qid, "number": int(qid[1:]), "question": stem, "options": opts, "answer": ans,
                   "quiz": cm.group(1), "reveal": cm.group(2), "lamp": cm.group(3)}
    return qs


def parse_estimates():
    text = (SCRIPT / "時長估算_v03.md").read_text(encoding="utf-8")
    est = {}
    for raw in text.splitlines():
        m = re.match(r"^\| (a\d_c\d{3}) \|", raw)
        if m:
            cols = [c.strip() for c in raw.strip().strip("|").split("|")]
            try:
                est[m.group(1)] = float(cols[9])
            except (ValueError, IndexError):
                pass
    cps = {}
    for raw in text.splitlines():
        m = re.match(r"^\| (Q\d) 點燈收聲後（(a\d_c\d{3})） \| 約 (\d+):(\d+)", raw)
        if m:
            cps[m.group(2)] = (m.group(1), int(m.group(3)) + int(m.group(4)) / 60)
        m = re.match(r"^\| 停在署名卡（a8_c002 結束） \| 約 (\d+):(\d+)", raw)
        if m:
            cps["a8_c003"] = ("署名卡", int(m.group(1)) + int(m.group(2)) / 60)
    return est, cps


# ---------------------------------------------------------------- 角色與站位
def present(cue, beat):
    """這個 cue 在台上的角色：說話者（畫外、不入鏡的除外）＋節拍表「角色」欄提到、而且不是剪影／窗內／畫外的"""
    ids = []
    offscreen = set()
    for d in cue["directions"]:
        for name, (cid, _, _) in CHARS.items():
            if re.search(rf"{name}[^（）。，]*?(不入鏡|畫外)", d):
                offscreen.add(cid)
    for seg in (beat or {}).get("cast", "").split("；"):
        for alias, cid in ALIASES.items():
            if seg.startswith(alias) or seg.startswith(f"{alias}、") or re.match(rf"^[^：]*{alias}", seg.split("：")[0]):
                if re.search(r"剪影|窗內|畫外|不入鏡|圖示", seg):
                    if not any(l["speaker"] == NAME_OF.get(cid) for l in cue["lines"]):
                        offscreen.add(cid)
                    continue
                if cid not in ids:
                    ids.append(cid)
    for l in cue["lines"]:
        for name in re.split(r"、", l["speaker"]):
            if name in CHARS:
                cid = CHARS[name][0]
                if cid not in ids:
                    ids.append(cid)
    return [i for i in ids if i not in offscreen]


def char_state(cid, act, cue_id, set_name):
    st = {"visible": True, "emotion": "smile"}
    if cid == "ale":
        if set_name == "workshop_g4":
            if act == "a2" and cue_id >= "a2_c003":
                # 線落下來之後（G4 a2_c004 的停格姿勢）
                st.update({"pose": "pulled_half", "strings": ["wrist", "elbow", "knee"], "stringTension": 1, "emotion": "confused", "hand": "grab"})
            else:
                st.update({"pose": "sit"})
        elif act in ("a4", "a5"):
            # 操偶線鬆鬆垂著（不吊起身體）
            st.update({"strings": ["wrist", "elbow", "knee"], "stringTension": 0.15, "emotion": "confused"})
    return st


# ---------------------------------------------------------------- 產生
def story_timing(action):
    vo = min(4.0, max(0.5, r1(action * 0.25)))
    return vo, max(0.9, r1(action - vo))


def build():
    acts, cues = parse_script()
    beats = parse_beats()
    quiz = parse_quiz()
    est, cps = parse_estimates()
    timings = json.loads((ROOT / "audio/vo/timings.json").read_text(encoding="utf-8"))
    g4 = json.loads((ROOT / "app/cues/g4.json").read_text(encoding="utf-8"))
    g4cues = {c["id"]: c for c in g4["cues"]}
    assert [quiz[f"Q{n}"]["answer"] for n in range(1, 9)] == ANSWERS, "八題正解順序與固定需求不符"
    by_quiz_cue = {}
    for q in quiz.values():
        by_quiz_cue[q["quiz"]] = ("quiz", q)
        by_quiz_cue[q["reveal"]] = ("reveal", q)
        by_quiz_cue[q["lamp"]] = ("lamp", q)

    seg_of = {s["id"]: s for s in SEGMENTS}
    # 全劇 cue 順序：G4 片頭待機 → 劇本 a0_c001…a8_c002 → G4 片尾署名卡
    order = ["a0_c000"] + [c["id"] for c in cues] + ["a8_c003"]
    by_id = {c["id"]: c for c in cues}
    out_cues = {}
    last_story = None   # 上一個劇情 cue（題卡三段沿用它的畫面）
    for cid in order:
        act = cid[:2]
        seg = seg_of[act]
        set_name = seg.get("cueSets", {}).get(cid, seg["set"])
        sc = by_id.get(cid)
        if cid in G4_CUES:
            c = copy.deepcopy(g4cues[cid])
            if cid == "a0_c001":
                c["title"] = sc["title"]
                c["lines"] = [{"id": l["id"], "speaker": l["speaker"], "text": l["text"], "start": 7.6} for l in sc["lines"]]
                c["teacherNote"] = c["teacherNote"] + "（全劇版：開幕後旁白 a0_c001_01 在 7.6 秒進來。）"
            if sc:
                c["storyboard"] = storyboard(sc, beats.get(cid))
            if cid == "a2_c004":
                c["checkpoint"] = None
            if cid == "a8_c003" and "a8_c003" in cps:
                c["checkpoint"] = {"label": "停在署名卡（之後教師結語）", "atMinute": round(cps["a8_c003"][1], 2)}
            out_cues[cid] = c
            if c["kind"] in ("scene", "curtain") and cid != "a8_c002":
                last_story = c
            continue
        info = sc["info"]
        kind = KIND[info["類型"]]
        comp = int(re.match(r"\d", info.get("壓縮", "0")).group(0))
        action = float(re.match(r"[\d.]+", info.get("動作", "6")).group(0))
        skip_ids = {f"{cid}_{m}" for m in re.findall(r"_(\d{2})", info.get("落後 3 分鐘可略", ""))}
        lines = []
        for l in sc["lines"]:
            e = {"id": l["id"], "speaker": l["speaker"], "text": l["text"]}
            if l["id"] in skip_ids:
                e["skippableWhenBehind"] = True
            lines.append(e)
        beat = beats.get(cid)
        teacher = "\n".join(sc["teacher"]) or "播完停格，等老師按下一步。"
        c = {"id": cid, "sceneId": set_name, "kind": kind, "title": sc["title"], "initialState": {}, "animation": [], "audioId": MUSIC.get(cid),
             "lines": lines, "next": None, "prevStable": None, "skippable": False, "compression": comp, "fx": (beat or {}).get("fx", []),
             "teacherNote": teacher, "checkpoint": None}
        if set_name != seg["set"]:
            c["set"] = set_name
        if info.get("短版", "—") not in ("—", ""):
            c["shortVersion"] = info["短版"]
            keep = re.findall(r"只播 _(\d{2})", info["短版"])
            if comp == 2 and keep:
                c["level2"] = {"lines": [f"{cid}_{k}" for k in keep]}
        if cid in cps and cid != "a8_c003":
            q, mins = cps[cid]
            esc = {"Q3": {"behindSec": 90, "level": 1}, "Q6": {"behindSec": 120, "level": 1}, "Q8": {"behindSec": 150, "level": 2}}.get(q)
            c["checkpoint"] = {"label": f"{q} 點燈收聲後", "atMinute": round(mins, 2), **({"escalate": esc} if esc else {})}
        if kind == "scene":
            cast = present(sc, beat)
            if cid == "a8_c001":
                cast = ["chen", "lin", "ye", "ale", "pinan", "xiaoyu", "xiaoqing", "zhezhe"]
            chars = {i: char_state(i, act, cid, set_name) for i in cast if i in seg["cast"]}
            if cid == "a6_c009" and "ale" in chars:
                chars["ale"].update({"pose": "sit", "strings": ["wrist"], "stringTension": 0})
                c["animation"].append({"name": "strings.fade", "target": "ale", "start": 0, "duration": 0.01, "params": {"anchors": ["wrist"], "to": 0.35}})
            cam = "show_mid"
            if set_name == "workshop_g4" and set(chars) <= {"ale", "xiaoqing", "xiaoyu", "zhezhe"}:
                cam = "g4_mid"
            c["initialState"] = {"stage": {"curtain": "open", "camera": cam, "light": 1}, "characters": chars}
            vo, tail = story_timing(action)
            c["voStart"], c["tail"] = vo, tail
            last_story = c
        else:
            prev_chars = copy.deepcopy((last_story or {}).get("initialState", {}).get("characters", {}))
            prev_cam = story_camera(last_story)
            q = by_quiz_cue[cid][1]
            if kind == "quiz":
                c["initialState"] = {"stage": {"curtain": "open", "camera": prev_cam, "light": 1}, "characters": prev_chars}
                c["animation"] = [
                    {"name": "camera.move", "start": 0, "duration": 2.4, "params": {"to": "quiz"}},
                    {"name": "light.dim", "start": 0, "duration": 1.2, "params": {"to": 0.55}},
                    {"name": "quiz.show", "start": 0.7, "duration": 0.6},
                ]
                c["sfx"] = [{"id": "sfx_quiet_fold", "at": 0}, {"id": "sfx_card_in", "at": 0.7, "gain": 0.8}]
                c["quiz"] = {k: q[k] for k in ("qid", "number", "question", "options", "answer")}
                c["voStart"], c["tail"] = 1.4, 1.0
            elif kind == "reveal":
                c["initialState"] = {"stage": {"curtain": "open", "camera": "quiz", "light": 0.55, "quiz": True}, "characters": prev_chars}
                c["animation"] = [{"name": "quiz.reveal", "start": 0.3, "duration": 0.45}]
                c["sfx"] = [{"id": "sfx_stamp", "at": 0.3}]
                c["voStart"], c["tail"] = 1.0, 1.2
            else:  # lamp
                first = lines[0]["id"]
                c["initialState"] = {"stage": {"curtain": "open", "camera": "quiz", "light": 0.55, "quiz": True}, "characters": prev_chars}
                c["lamp"] = q["number"]
                c["animation"] = [
                    {"name": "lamp.light", "start": 0.3, "duration": 1.5, "params": {"index": q["number"]}},
                    {"name": "quiz.hide", "start": f"{first}.end+0.3", "duration": 0.6},
                    {"name": "light.restore", "start": f"{first}.end+0.3", "duration": 1.2},
                    {"name": "camera.move", "start": f"{first}.end+0.3", "duration": 2.5, "params": {"to": prev_cam}},
                ]
                c["sfx"] = [{"id": "sfx_lamp_on", "at": 0.3}]
                c["voStart"], c["tail"] = 1.9, 0.6
        c["storyboard"] = storyboard(sc, beat)
        out_cues[cid] = c

    # 全劇流程：next／prevStable（題目 → 揭答 → 等待 → 續演；自動接續的閉幕不算穩定節點）
    stable_prev = None
    for i, cid in enumerate(order):
        c = out_cues[cid]
        c["next"] = order[i + 1] if i + 1 < len(order) else None
        c["prevStable"] = stable_prev
        if not c.get("autoAdvance"):
            stable_prev = cid
    # a8_c003（片尾署名卡）的上一步跳過自動接續的閉幕
    out_cues["a8_c003"]["prevStable"] = "a8_c001"
    # a8_c002（G4 閉幕）：起始角色改成謝幕後的狀態（沒有操偶線），表演與時間不動
    out_cues["a8_c002"]["initialState"]["characters"] = copy.deepcopy(out_cues["a8_c001"]["initialState"]["characters"])
    out_cues["a8_c002"]["initialState"]["stage"] = {"curtain": "open", "camera": story_camera(out_cues["a8_c001"]), "light": 1, "desat": 0, "spot": 0}
    out_cues["a8_c002"]["teacherNote"] += "（全劇版：起始畫面是謝幕後全體角色、沒有操偶線；閉幕動作與 G4 相同。）"

    # 段落檔
    files = {}
    for seg in SEGMENTS:
        sid = seg["id"]
        ids = [cid for cid in order if cid[:2] == sid]
        roster = {}
        for ch in seg["cast"]:
            name = NAME_OF[ch]
            _, rig, fb = CHARS[name]
            p = {**PLACE[ch], **seg.get("place", {}).get(ch, {})}
            roster[ch] = {"name": name, "rig": rig, "x": p["x"], "z": p["z"], "facing": p["facing"], "fallback": fb}
        files[f"{sid}.json"] = {
            "format": "antidrug-cues/1", "id": sid, "title": acts.get(sid, sid),
            "set": seg["set"], "characters": roster,
            "_note": "動態分鏡底稿（tools/build_show_skeleton.py 產生）。本段落由該幕代理擁有；介面見 app/SHOW_INTERFACE.md。cue 的 storyboard 是劇本與節拍表的摘錄，引擎不讀。",
            "cues": [out_cues[i] for i in ids],
        }
    index = {"format": "antidrug-show/1", "id": "show", "title": "紙燈節（全劇）", "segments": [f"{s['id']}.json" for s in SEGMENTS]}
    return index, files, timings, est, cues


def story_camera(c):
    if not c:
        return "show_mid"
    cam = c.get("initialState", {}).get("stage", {}).get("camera", "show_mid")
    for a in c.get("animation", []):
        if a["name"] in ("camera.move", "camera.cut") and isinstance((a.get("params") or {}).get("to"), str):
            cam = a["params"]["to"]
    return cam


def storyboard(sc, beat):
    sb = {}
    if beat:
        sb.update({"beat": beat["beat"], "cast": beat["cast"], "camera": beat["camera"], "sound": beat["sound"]})
    if sc:
        if sc["directions"]:
            sb["directions"] = sc["directions"]
        m = re.match(r"[\d.]+", sc["info"].get("估計", ""))
        if m:
            sb["estimateSec"] = float(m.group(0))
        m = re.match(r"[\d.]+", sc["info"].get("動作", ""))
        if m:
            sb["actionSec"] = float(m.group(0))
    return sb


def estimate(files, timings):
    """依 timings.json 的句長粗估每段長度（引擎實際以音檔長度排）"""
    rows = []
    for f, d in files.items():
        tot = 0.0
        for c in d["cues"]:
            secs = [timings.get(l["id"], {}).get("seconds", 2.0) for l in c["lines"]]
            vo = c.get("voStart", 0.5)
            if c["lines"] and any("start" in l for l in c["lines"]):
                st = c["lines"][0].get("start", vo)
                end = st + sum(secs) + 0.45 * (len(secs) - 1)
            else:
                end = vo + sum(secs) + 0.45 * max(0, len(secs) - 1)
            dur = max(c.get("minDuration", 0), end + c.get("tail", 0.9) if secs else 0)
            if c["kind"] == "lamp":
                dur = max(dur, end + 0.3 + 2.5)
            tot += dur
        rows.append((f, len(d["cues"]), sum(len(c["lines"]) for c in d["cues"]), round(tot, 1)))
    return rows


def main():
    force = "--force" in sys.argv
    check = "--check" in sys.argv
    index, files, timings, est, script_cues = build()
    n_lines = sum(len(c["lines"]) for d in files.values() for c in d["cues"])
    print(f"[skeleton] {len(files)} 段、{sum(len(d['cues']) for d in files.values())} 個 cue、{n_lines} 句（劇本 {sum(len(c['lines']) for c in script_cues)} 句）")
    for f, nc, nl, sec in estimate(files, timings):
        print(f"  {f:8s} {nc:3d} cue {nl:3d} 句  約 {sec:6.1f} 秒（依 timings.json 粗估，不含教師時間與換景預捲）")
    if check:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    wrote, kept = [], []
    targets = [("index.json", index)] + list(files.items())
    for name, data in targets:
        p = OUT / name
        if p.exists() and not force:
            kept.append(name)
            continue
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        wrote.append(name)
    print(f"[skeleton] 寫入 {', '.join(wrote) or '無'}；已存在沒有覆寫 {', '.join(kept) or '無'}（要全部重寫加 --force，只有主線能用）")


if __name__ == "__main__":
    main()
