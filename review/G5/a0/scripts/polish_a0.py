"""G6 精修 a0（REVIEW.md「G5 第一批：關卡決定」、qa/b1r3_failed.md a0 條目）。

基準：review/G5/a0/scripts/polish_base_a0.json（精修前的 app/cues/show/a0.json）。
用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/polish_a0.py   （寫暫存 → 驗證 JSON → 搬回）

1. a0_c004「摺成放大鏡」時折折被小宇擋住一半（b1r3_failed a0 一般問題 2）：折折在工作台上的小跳落點往左 0.22（x 1.00 → 0.78），
   推近到 a0_hat 後折折和小宇的頭隔開；小跳提早 0.5 秒（和推近鏡頭錯開）；之後跳到小宇頭上當帽子的終點不變。
2. 上半部空牆（一般問題 3）、門邊風鈴的模糊灰影（一般問題 4）：只改景 workshop_a0.ts（牆上一排吊燈籠 hanglamps、風鈴不投影子），cue 不改。
3. 摺紙最後縮成小點（一般問題 1）：縮成紙包的大小寫死在折折程式（app/src/stage/zhezhe.ts 摺紙變形 MIN＝0.34），不是本段的檔，交主線（handoff）。
"""
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "review/G5/a0/scripts/polish_base_a0.json"
DST = ROOT / "app/cues/show/a0.json"

d = json.loads(BASE.read_text(encoding="utf-8"))
cues = {c["id"]: c for c in d["cues"]}
hop = [a for a in cues["a0_c004"]["animation"] if a["name"] == "zhezhe.hopTo" and a["params"].get("pos") == [1, 1.4, -0.6]]
assert len(hop) == 1, hop
hop[0]["params"]["pos"] = [0.78, 1.4, -0.6]
# 跳得短了，跳上去的身體留在同一格裡：提早 0.5 秒跳、0.6 秒落地，和推近鏡頭（「交給我」前 0.5 秒起）錯開（細格光敏）
hop[0]["start"] = "a0_c004_03-1.40"
hop[0]["duration"] = 0.6

# 3. 摺紙縮成小點：先寫好 minScale（目前的折折程式不認得這個參數，不影響畫面）；主線套用
#    review/G5/a0/handoff_zhezhe_minScale.patch 後生效：紙包只縮到 0.8（三角直接換成大紙包、展開成貓），私人建置細格 3／1 通過
fold = [a for a in cues["a0_c002"]["animation"] if a["name"] == "zhezhe.fold" and a["params"].get("form") == "idle"]
assert len(fold) == 1, fold
fold[0]["params"]["minScale"] = 0.8

fd, tmp = tempfile.mkstemp(dir=DST.parent, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
    f.write("\n")
json.loads(Path(tmp).read_text(encoding="utf-8"))
os.replace(tmp, DST)
print("a0.json 已更新")
