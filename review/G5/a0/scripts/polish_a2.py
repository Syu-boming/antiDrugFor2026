"""G6 精修 a2（REVIEW.md「G5 第一批：關卡決定」、qa/b1r3_failed.md、b1r3_regress.md 的 a2 條目）。

基準：review/G5/a0/scripts/polish_base_a2.json（精修前的 app/cues/show/a2.json）。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/polish_a2.py   （寫暫存 → 驗證 JSON → 搬回）

1. a2_c012 廣場求助鏡頭太短（b1r3_regress a2 一般問題 1：淡入完成後只看得到約 1.2 秒）：
   - 淡出提早 0.15 秒（1.00 → 0.85），淡入在 2.15 完成；切回工作室 3.47 → 4.15 → 廣場全亮約 2.0 秒。
   - 葉護理師在廣場的反應（皺眉、前傾、點頭）等畫面全亮後才開始。
   - 從同一個 cue 扣回：工作室裡葉護理師站著走近的那段（原 3.47–5.37）縮成 4.15–5.37（她直接站在阿樂旁邊，蹲下藏在切近景的切點），
     切近景 5.37 與第一句 5.72 不動 → cue 總長不變。
2. 手部近景（a2_c008）的接縫與手指：只換圖（assets/final/sets/a2_shop/insert-ale-hand-{r,l}_v02.png，build_polish_art.py hands），cue 不改。
3. a2_c002（G4 cue）膝線對比：引擎刻意不對 G4 cue 套用深灰邊與最小線寬（app/src/stage/stage.ts G4_CUE_IDS），交主線（不改引擎、不改 G4 表演）。
"""
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "review/G5/a0/scripts/polish_base_a2.json"
DST = ROOT / "app/cues/show/a2.json"

d = json.loads(BASE.read_text(encoding="utf-8"))
cues = {c["id"]: c for c in d["cues"]}
c = cues["a2_c012"]


def find(name, target=None, start=None):
    r = [a for a in c["animation"] if a["name"] == name and (target is None or a.get("target") == target)
         and (start is None or (isinstance(a["start"], (int, float)) and abs(a["start"] - start) < 1e-6) or a["start"] == start)]
    assert len(r) == 1, (name, target, start, r)
    return r[0]


# 淡出 → 廣場（提早 0.15 秒）
find("fade.out", None, 1.0)["start"] = 0.85
find("camera.cut", None, 1.62)["start"] = 1.47
find("fx.desat", None, 1.62)["start"] = 1.47
find("puppet.move", "xiaoqing", 1.62)["start"] = 1.47
find("puppet.move", "xiaoyu", 1.62)["start"] = 1.47
find("puppet.pose", "xiaoqing", 1.63)["start"] = 1.48
find("puppet.pose", "xiaoyu", 1.63)["start"] = 1.48
find("fade.in", None, 1.7)["start"] = 1.55          # 2.15 全亮
# 葉護理師在廣場：全亮後才反應
find("puppet.face", "ye", 2.12)["start"] = 2.25
find("puppet.lean", "ye", 2.32)["start"] = 2.5
find("puppet.nod", "ye", 2.62)["start"] = 2.9       # 0.8 秒，到 3.7
find("puppet.lean", "ye", 3.02)["start"] = 3.35
# 切回工作室（3.47 → 4.15）：廣場全亮 2.15–4.15
for nm, tg in (("camera.cut", None), ("fx.desat", None), ("puppet.move", "ye"), ("puppet.move", "xiaoqing"), ("puppet.move", "xiaoyu")):
    a = [x for x in c["animation"] if x["name"] == nm and (tg is None or x.get("target") == tg) and x["start"] == 3.47]
    assert len(a) == 1, (nm, tg, a)
    a[0]["start"] = 4.15
find("puppet.pose", "xiaoqing", 3.49)["start"] = 4.17
find("puppet.lean", "xiaoqing", 3.49)["start"] = 4.17
# 工作室這一段只剩 1.2 秒：葉護理師直接站在阿樂旁邊（原本走近 0.4 的那一步併進切點的瞬移），蹲下藏在切近景的切點（5.37，0 秒換姿勢）
#（試過 4.2 走近＋4.78 蹲下翻面＋5.37 切近景：她胸口那一格 1 秒內 4 次，驗收包細格不通過）
c["animation"].remove(find("puppet.move", "ye", 3.82))
mv = [x for x in c["animation"] if x["name"] == "puppet.move" and x.get("target") == "ye" and x["start"] == 4.15]
assert len(mv) == 1
mv[0]["params"]["dx"] = round(mv[0]["params"]["dx"] - 0.4, 4)
p = find("puppet.pose", "ye", 4.67); p["start"] = 5.37; p["duration"] = 0
find("fx.desat", None, 4.27)["start"] = 4.45
find("puppet.nod", "ale", 3.77)["start"] = 4.25
for s in c["sfx"]:
    if s["id"] == "sfx_crowd_short":
        s["at"] = 1.57
for m in c["music"]:
    if m["id"] == "music_town":
        m["at"] = 4.05

fd, tmp = tempfile.mkstemp(dir=DST.parent, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
    f.write("\n")
json.loads(Path(tmp).read_text(encoding="utf-8"))
os.replace(tmp, DST)
print("a2.json 已更新")
