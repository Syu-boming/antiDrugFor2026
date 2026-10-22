"""G6 精修 a1（第一批放行時記錄的一般問題；REVIEW.md「G5 第一批：關卡決定」、qa/b1r3_failed.md、b1r3_regress.md）。

基準：review/G5/a0/scripts/polish_base_a1.json（精修前的 app/cues/show/a1.json）。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/polish_a1.py   （寫暫存 → 驗證 JSON → 搬回）

1. Q1 點燈後只暗亮一次（b1r3_regress a1 一般問題 1）：
   - a1_c005 進題卡的全暗那一刻（0.60–0.64）把孩子移到 a1_c008 開頭的站位（x −0.35／0.6、z 0.1／−0.25、都面向右），
     換成站姿（不再停在跨步）；a1_c005 開頭是品安近景 a1_pinan，孩子在畫面外，所以起始的 z 與面向可以直接改（小宇 walk_r＋facing −1
     ＝walk＋facing 1，同一張圖的鏡像）。a1_c006、a1_c007 起始狀態跟著改。
   - a1_c007 題卡淡出後在全暗中切到 a1_street2（＝a1_c008 開頭鏡位）、折折移到 a1_c008 開頭位置、品安退到畫面外，再淡入 → 停在穩定的故事畫面
     （節拍表：「鏡頭回到故事，停在穩定畫面」）。
   - a1_c008 拿掉 setFade（同一個景，不再換景預捲 0.6 秒＋漸亮），開頭孩子翻面成走路再往右走。
2. 翻面一律 ≥0.4 秒（最窄處換圖；b1r3_failed a1 一般問題 1、b1r3_regress 2）：a1_c008 的小晴、小宇換姿勢；和鏡頭硬切同一刻的換姿勢改成 0 秒（藏在切點）。
3. 切近景前一格亮 11%（b1r3_failed 2）：light.restore 與 camera.cut 同一刻（4.60，0 秒）；切回街景前的 light.dim 也和切點同一刻。
4. 品安回頭看柱子（b1r3_failed 3）：a1_c004 結尾翻成臉朝左上（sit_lantern_look1 → look2，眼珠往左上、頭抬起），停 1.0 秒再回到燈籠。
5. a1_c008 站定看窗縮短（b1r3_failed 4）：竹篾落下後 0.2 秒就說「阿樂叔叔？」（提前 0.3 秒），結尾燈光漸暗 3.2 → 2.6 秒；
   a1_c008 共短 1.0 秒（走路、轉身、剪影的時間不動：試過整段提早 0.2 秒，走路步伐和小宇紅外套的細格紅色變成每秒 4 次）。
"""
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "review/G5/a0/scripts/polish_base_a1.json"
DST = ROOT / "app/cues/show/a1.json"

d = json.loads(BASE.read_text(encoding="utf-8"))
cues = {c["id"]: c for c in d["cues"]}


def anims(cid, name=None, target=None):
    return [a for a in cues[cid]["animation"] if (name is None or a["name"] == name) and (target is None or a.get("target") == target)]


def find(cid, name, target=None, start=None):
    r = [a for a in anims(cid, name, target) if start is None or a["start"] == start]
    assert len(r) == 1, (cid, name, target, start, r)
    return r[0]


# ───────── 1. a1_c005–a1_c007：孩子站到 a1_c008 開頭的站位 ─────────
QX = {"x": -0.35, "z": 0.1, "facing": 1}
YX = {"x": 0.6, "z": -0.25, "facing": 1}
c5 = cues["a1_c005"]["initialState"]["characters"]
c5["xiaoqing"].update({"z": 0.1, "facing": 1, "pose": "walk"})
c5["xiaoyu"].update({"z": -0.25, "facing": 1, "pose": "walk"})        # walk_r＋facing −1 的同一張圖
dq = round(QX["x"] - c5["xiaoqing"]["x"], 4)
dy_ = round(YX["x"] - c5["xiaoyu"]["x"], 4)
cues["a1_c005"]["animation"] += [
    # 全暗（fade.out 0–0.60 到底、fade.in 0.64 才開始）的那一刻換站位與站姿
    {"name": "puppet.move", "start": 0.605, "target": "xiaoqing", "duration": 0.02, "params": {"dx": dq}},
    {"name": "puppet.move", "start": 0.605, "target": "xiaoyu", "duration": 0.02, "params": {"dx": dy_}},
    {"name": "puppet.pose", "start": 0.61, "target": "xiaoqing", "duration": 0, "params": {"pose": "stand"}},
    {"name": "puppet.pose", "start": 0.61, "target": "xiaoyu", "duration": 0, "params": {"pose": "stand"}},
]
for cid in ("a1_c006", "a1_c007"):
    ch = cues[cid]["initialState"]["characters"]
    ch["xiaoqing"].update(QX | {"pose": "stand"})
    ch["xiaoyu"].update(YX | {"pose": "stand"})

c7 = cues["a1_c007"]
find("a1_c007", "camera.cut")["params"]["to"] = "a1_street2"
g = find("a1_c007", "zhezhe.glideTo", "zhezhe")
g["start"] = "a1_c007_01.end+1.155"
g["params"]["pos"] = [-1.9, 0.0, 1.2]
c7["animation"] += [
    {"name": "zhezhe.emote", "start": "a1_c007_01.end+0.30", "target": "zhezhe", "params": {"emotion": "happy"}},
    {"name": "puppet.exit", "start": "a1_c007_01.end+1.155", "target": "pinan", "duration": 0.02, "params": {"to": -6}},
    {"name": "puppet.face", "start": "a1_c007_01.end+1.16", "target": "xiaoqing", "params": {"emotion": "smile"}},
    {"name": "puppet.face", "start": "a1_c007_01.end+1.16", "target": "xiaoyu", "params": {"emotion": "smile"}},
]
c7["storyboard"]["directions"].append("（G6 精修：題卡淡出後在全暗中切到往燈籠店的街上，淡入停在孩子站在街上的穩定畫面；下一段不再換景預捲。）")

# ───────── a1_c008 ─────────
c8 = cues["a1_c008"]
c8.pop("setFade", None)
c8["initialState"]["characters"]["xiaoqing"]["pose"] = "stand"
c8["initialState"]["characters"]["xiaoyu"]["pose"] = "stand"
c8["animation"] = [
    {"name": "puppet.pose", "start": 0.05, "target": "xiaoqing", "duration": 0.45, "params": {"pose": "walk"}},
    {"name": "puppet.pose", "start": 0.15, "target": "xiaoyu", "duration": 0.45, "params": {"pose": "walk"}},
] + c8["animation"]
# 翻面完成後隔約 0.4 秒才起步（同一格不疊翻面＋走路，細格光敏）；包裝紙 2.0–4.0 秒才吹進來，起步晚一點不影響後面
p = find("a1_c008", "puppet.move", "xiaoqing", 0.3); p["start"] = 0.95; p["duration"] = 1.85
p = find("a1_c008", "puppet.move", "xiaoyu", 0.35); p["start"] = 1.0; p["duration"] = 1.85
for s_ in c8["sfx"]:
    if s_["id"] == "sfx_footsteps" and s_["at"] == 0.5:
        s_["at"] = 1.0
# 2. 翻面 ≥0.4 秒；看到包裝紙的翻面提早，和切近景（4.60）隔開 0.7 秒以上
p = find("a1_c008", "puppet.pose", "xiaoqing", 3.8); p["start"] = 3.45; p["duration"] = 0.42
p = find("a1_c008", "puppet.pose", "xiaoyu", 4.0); p["start"] = 3.62; p["duration"] = 0.42
p = find("a1_c008", "puppet.pose", "xiaoqing", "a1_c008_02-0.35"); p["start"] = "a1_c008_02-0.30"; p["duration"] = 0   # 藏在切點
# 5. 站定看窗縮短：走到窗前、轉身、剪影舉竹篾都照原時間（走路步伐與細格光敏已驗過）；竹篾落下後 0.2 秒就說「阿樂叔叔？」
#    （提前 0.3 秒），結尾燈光漸暗 3.2 → 2.6 秒
p = find("a1_c008", "puppet.pose", "xiaoyu", "a1_c008_02.end+0.20"); p["start"] = "a1_c008_02.end+0.05"; p["duration"] = 0.42
p = find("a1_c008", "puppet.pose", "xiaoqing", "a1_c008_02.end+0.30"); p["start"] = "a1_c008_02.end+0.08"; p["duration"] = 0.42
# 小宇轉向窗戶慢翻 1.6 秒（中點 +6.15）：紅外套那一格的「壓窄→換圖→展開」拉開到 1 秒以上（細格紅色不到每秒 4 次）
p = find("a1_c008", "puppet.pose", "xiaoyu", "a1_c008_02.end+5.60"); p["start"] = "a1_c008_02.end+5.35"; p["duration"] = 1.6
p = find("a1_c008", "puppet.pose", "xiaoqing", "a1_c008_02.end+6.20"); p["start"] = "a1_c008_02.end+6.08"; p["duration"] = 0.5   # 翻面 ≥0.4 秒（中點不變）
find("a1_c008", "zhezhe.twitch", "zhezhe", "a1_c008_02.end+8.00")["start"] = "a1_c008_02.end+7.90"
find("a1_c008", "zhezhe.emote", "zhezhe", "a1_c008_02.end+8.10")["start"] = "a1_c008_02.end+8.00"
find("a1_c008", "puppet.face", "xiaoyu", "a1_c008_02.end+8.10")["start"] = "a1_c008_02.end+8.00"
find("a1_c008", "puppet.face", "xiaoqing", "a1_c008_02.end+8.25")["start"] = "a1_c008_02.end+8.10"
for l in c8["lines"]:
    if l["id"] == "a1_c008_03":
        assert l["start"] == "a1_c008_02.end+8.50"
        l["start"] = "a1_c008_02.end+8.20"
p = find("a1_c008", "light.dim", None, "a1_c008_03.end+0.40"); p["start"] = "a1_c008_03.end+0.30"; p["duration"] = 2.6
c8["tail"] = 2.6
# 3. 亮度：和切點同一刻
p = find("a1_c008", "light.restore", None, 4.58); p["start"] = 4.6; p["duration"] = 0
p = find("a1_c008", "light.dim", None, "a1_c008_02-0.32"); p["start"] = "a1_c008_02-0.30"; p["duration"] = 0

# ───────── 4. a1_c004 品安看柱子 ─────────
c4 = cues["a1_c004"]
drop = [find("a1_c004", "puppet.pose", "pinan", "a1_c004_06.end+1.20"), find("a1_c004", "puppet.tilt", "pinan", "a1_c004_06.end+1.40"),
        find("a1_c004", "puppet.pose", "pinan", "a1_c004_06.end+2.60"), find("a1_c004", "puppet.tilt", "pinan", "a1_c004_06.end+2.65")]
c4["animation"] = [a for a in c4["animation"] if not any(a is x for x in drop)]
c4["animation"] += [
    # 眼睛一瞟、頭抬起來（兩格換圖，同一個身體，只有頭和眼珠動）→ 停 1.0 秒 → 低頭回到燈籠
    {"name": "puppet.pose", "start": "a1_c004_06.end+1.15", "target": "pinan", "duration": 0, "params": {"pose": "sit_lantern_look1"}},
    {"name": "puppet.pose", "start": "a1_c004_06.end+1.25", "target": "pinan", "duration": 0, "params": {"pose": "sit_lantern_look2"}},
    {"name": "puppet.pose", "start": "a1_c004_06.end+2.30", "target": "pinan", "duration": 0, "params": {"pose": "sit_lantern_look1"}},
    {"name": "puppet.pose", "start": "a1_c004_06.end+2.40", "target": "pinan", "duration": 0, "params": {"pose": "sit_lantern_back"}},
]

# 寫回（暫存 → 驗證 → 搬）
fd, tmp = tempfile.mkstemp(dir=DST.parent, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
    f.write("\n")
json.loads(Path(tmp).read_text(encoding="utf-8"))
os.replace(tmp, DST)
print("a1.json 已更新")
