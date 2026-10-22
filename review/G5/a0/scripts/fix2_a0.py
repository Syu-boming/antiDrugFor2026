"""G5 修正第 2 輪：app/cues/show/a0.json（開場）。從修正第 1 輪的版本（a0_fix1_base.json）重建，重跑結果相同。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/fix2_a0.py
寫入方式：先寫暫存檔、讀回驗證 JSON，再搬回（段落檔隨時保持合法）。
依據：review/G5/qa/b1r2_recheck.md a0 一般問題 1–4；REVIEW.md 主線更正裁定（切場亮度漸變）。
  1. a0_c005 停格：阿樂叔叔改成中性臉（X11 疲倦：困惑頭＋閉嘴），頭再低一點，延續 a0_c003 的伏筆。
  2. a0_c002 摺紙：燈籠紙放大 1.4 倍（最後一摺的小三角約佔畫面高 15–16%，摺成的貓仍是原尺寸）、摺紙放慢到 5.4 秒；鏡位 a0_fold2 略往下看，桌面在畫面高約 62%。\n     （試過推近 1.45 倍：貓耳抖動與回憶切換在細格 32×18 超標，所以改放大紙、不放大貓。）
  3. 吊燈下的灰色圓影：景 workshop_a0 讓上方吊燈籠不投影子（workshop_a0.ts）。
  4. 切到 a0_c005 題卡鏡位（看台口八盞燈）的一格硬切（全畫面亮度 0.518→0.366）：改成漸暗 0.6 秒 → 全暗時換鏡位 → 漸亮 0.6 秒；
     折折跳到台口、孩子離開、阿樂叔叔揮手都排在漸亮之後。
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DST = ROOT / "app/cues/show/a0.json"
d = json.loads((ROOT / "review/G5/a0/scripts/a0_fix1_base.json").read_text())
C = {c["id"]: c for c in d["cues"]}


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


# ───────── a0_c002：燈籠紙放大 1.4 倍（最後一摺的小三角約佔畫面高 15–16%；摺成的貓仍是原尺寸）、鏡頭略往下看（桌面在畫面高約 62%）；
#           摺紙放慢 4.0→5.4 秒（放大後摺邊的深色細線掃過同一格：每一摺間隔要 > 1 秒，細格光敏）；
#           回憶鏡位在紙框淡入完成時就切（+0.9），切進去時阿樂叔叔已經坐好（拿掉立起動作）
c = C["a0_c002"]
c["initialState"]["stage"]["camera"] = "a0_fold2"
FOLD = 5.4
k = FOLD / 4.0
for a in c["animation"]:
    n, st = a["name"], a["start"]
    if n == "zhezhe.fold" and st == -1.2 and a["params"].get("form") == "sheet":
        a["params"]["scale"] = 1.4
    if n == "zhezhe.fold" and st == 1.05:
        a["duration"] = FOLD
    if n == "zhezhe.twitch" and st == 5.05:
        a["start"] = round(1.05 + FOLD, 2)
    if n == "camera.cut" and st == "a0_c002_02.end+1.30":
        a["start"] = "a0_c002_02.end+0.90"
c["voStart"] = round(5.2 + (FOLD - 4.0), 2)
# 回憶裡阿樂叔叔不再「立起」（立起時白邊→深色輪廓→身體連續掃過同一格，加上切換就超過每秒 3 次）：切進回憶時他已經坐在工作台前
c["animation"] = [a for a in c["animation"] if a["name"] != "puppet.popup"]
c["initialState"]["characters"]["ale"]["popup"] = 1
c["sfx"] = [{**e, "at": round(1.05 + (e["at"] - 1.05) * k, 3)} if e["id"] == "sfx_fold" else
            ({**e, "at": round(5.0 + (FOLD - 4.0), 2)} if e["id"] == "sfx_paper_rustle" else e) for e in c["sfx"]]
# 總長不比第 1 輪長（摺紙多 1.4 秒）：各 cue 結尾停留縮短、a0_c003 阿樂叔叔走進來後的第一句提早 0.3 秒
c["tail"] = 2.0                                                                   # 原 2.4
C["a0_c003"]["tail"] = 1.6                                                        # 原 2.0
C["a0_c004"]["tail"] = 1.5                                                        # 原 1.8
next(l for l in C["a0_c003"]["lines"] if l["id"] == "a0_c003_03")["start"] = "a0_c003_02.end+2.90"   # 原 +3.20

# ───────── a0_c005：漸暗→換到題卡鏡位→漸亮；動作往後排；停格中性臉
c = C["a0_c005"]
SHIFT = {  # 原本在 0.3 秒硬切之後馬上開始的動作，移到漸亮（0.64–1.24 秒）之後
    ("zhezhe.hopTo", 0.35): 0.95, ("zhezhe.fold", 1.75): 2.3, ("puppet.pose", 1.0): 1.3, ("puppet.wave", 1.1): 1.35,
}
anims = []
for a in c["animation"]:
    n, st = a["name"], a["start"]
    if n == "camera.cut" and st == 0.3:
        continue
    if (n, st) in SHIFT:
        a = {**a, "start": SHIFT[(n, st)]}
    if n == "puppet.face" and a.get("target") == "ale" and st == 4.6:
        a = {**a, "params": {"emotion": "neutral"}}
    if n == "puppet.tilt" and a.get("target") == "ale" and st == 4.7:
        a = {**a, "params": {"to": 0.09}}
    anims.append(a)
anims += [
    A("fade.out", 0, duration=0.6, to=1),
    A("camera.cut", 0.62, duration=0, to="quiz"),
    A("fade.in", 0.64, duration=0.6),
]
c["animation"] = anims
SFX_AT = {("sfx_paper_rustle", 1.7): 2.3, ("sfx_fold", 1.88): 2.43}     # 跟著折折落地、摺回貓的新時間
c["sfx"] = [{**e, "at": SFX_AT.get((e["id"], e["at"]), e["at"])} for e in c["sfx"]]

c["tail"] = 1.9      # 總長不比修正第 1 輪長（原 2.4）

txt = json.dumps(d, ensure_ascii=False, indent=1)
tmp = DST.with_suffix(".json.tmp")
tmp.write_text(txt + "\n")
json.loads(tmp.read_text())
os.replace(tmp, DST)
print("wrote", DST.relative_to(ROOT))
