"""產生 review/G3/el/deng/listen.html（本機試聽頁；音檔用相對路徑直接播 audio/vo 與 audio/vo_el/_attempts，不複製）。
用法：/opt/anaconda3/bin/python3 review/G3/el/deng/make_listen.py
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
UP = "../../../../"
T4 = json.loads((HERE / "tracks_v04.json").read_text("utf-8"))
T5 = json.loads((HERE / "tracks_v05.json").read_text("utf-8"))
TA = json.loads((HERE / "tracks_attempts.json").read_text("utf-8"))
REP = json.loads((ROOT / "audio/vo_el/build_report_el.json").read_text("utf-8"))
TIM = json.loads((ROOT / "audio/vo/timings.json").read_text("utf-8"))
OLD_SEC = {"a0_c002_03": 2.62, "a6_c009_03": 8.08, "a6_c001_02": 2.01, "a2_c013_05": 2.79}
CUE_DIFF = {"a0_c002_03": ("a0_c002", 22.30, 22.27), "a6_c009_03": ("a6_c009", 25.81, 25.78),
            "a6_c001_02": ("a6_c001", 13.68, 13.68)}
TARGETS = [k for k in T4 if k in ("a0_c001_01 a0_c002_03 a0_c003_01 a0_c003_02 a0_c003_04 a0_c005_02 a0_c005_03 "
                                   "a1_c001_03 a1_c001_05 a1_c007_01 a2_c011_01 a2_c013_05 a4_c007_01 a5_c001_01 "
                                   "a5_c004_01 a5_c006_02 a5_c007_01 a6_c001_01 a6_c001_02 a6_c007_02 a6_c007_03 "
                                   "a6_c009_03 a7_c003_02 a8_c001_01").split()]
REFS = [k for k in T4 if k not in TARGETS]
REDO = {"a0_c002_03", "a6_c009_03", "a6_c001_02", "a2_c013_05"}
ADOPT = {"a0_c002_03": "r2_a2", "a6_c009_03": "r2_a3", "a6_c001_02": "r4_a2"}
CANDS = {"a2_c013_05": ["r3_a3", "r4_a1"]}

e = html.escape


def sent_of(lid: str) -> str:
    r = REP.get(lid, {})
    ch = [a for a in r.get("attempts", []) if a["k"] == r.get("chosen")]
    if lid == "a2_c013_05":   # 維持 v04：取原採用（第 2 輪第 1 次）
        return "嗯。主灯骨架，到底在哪裡？……嗯。（送出時句首「嗯。」、句尾「……嗯。」會切掉）"
    return " / ".join(s["sent"] for s in ch[0]["segments"]) if ch else ""


def v04_sent(lid: str) -> str:
    from_backup = {"a0_c002_03": "慢慢折，燈才會亮。……嗯。", "a6_c009_03": "我現在還是會定期回去看醫生。慢慢折，燈才會亮。……嗯。",
                   "a6_c001_02": "慢慢折，灯才會亮。……嗯。"}
    return from_backup.get(lid) or sent_of(lid)


def hl(text: str) -> str:
    return e(text).replace("燈", '<mark>燈</mark>').replace("登", '<mark class="d">登</mark>').replace("灯", '<mark class="d">灯</mark>')


def verdict_block(r: dict) -> str:
    out = []
    for c in r["chars"]:
        if c["i"] in r["targets"]:
            v = c.get("verdict", "")
            cls = {"第一聲": "ok", "疑似第四聲": "bad", "疑似第三聲": "bad"}.get(v, "warn")
            vs = c.get("vs_tone1") or {}
            vs_t = f"；比同句一聲字 {vs['diff_st']:+.1f} 半音（{vs['n']} 字）" if vs.get("diff_st") is not None else ""
            out.append(f'<div class="v"><span class="tag {cls}">{e(v)}</span> 第 {c["i"] + 1} 字（前字{e(c.get("prev") or "")}）'
                       f'<div class="why">{e(c.get("why", ""))}{e(vs_t)}；F0 {c.get("f0_start_hz")}→{c.get("f0_end_hz")} Hz，'
                       f'{c.get("t0")}–{c.get("t1")} 秒</div></div>')
    return "".join(out)


def audio(path: str, label: str) -> str:
    return f'<div class="au"><span>{e(label)}</span><audio controls preload="none" src="{UP}{e(path)}"></audio></div>'


def plot(path: Path, label: str) -> str:
    if not path.exists():
        return ""
    rel = path.relative_to(HERE)
    return f'<a class="pl" href="{e(str(rel))}" target="_blank">{e(label)}</a>'


rows = []
for lid in TARGETS:
    r4 = T4[lid]
    v4c = [c for c in r4["chars"] if c["i"] in r4["targets"]]
    worst = "第一聲" if all(c.get("verdict") == "第一聲" for c in v4c) else next(c["verdict"] for c in v4c if c.get("verdict") != "第一聲")
    status = ""
    new = ""
    if lid in ADOPT:
        r5 = T5[lid]
        sec = TIM[lid]["seconds"]
        cue, a, b = CUE_DIFF[lid]
        new = (audio(f"audio/vo/vo_{lid}_v05.wav", "新版 v05") + verdict_block(r5)
               + f'<div class="meta">送出：{hl(sent_of(lid))}<br>長度 {OLD_SEC[lid]} → {sec} 秒（{sec - OLD_SEC[lid]:+.2f}）；'
               f'cue {cue} 總長 {a} → {b} 秒</div>' + plot(HERE / "plots_v05" / f"{lid}.png", "F0 圖（v05）"))
        status = '<span class="tag ok">已升 v05</span>'
    elif lid in CANDS:
        parts = []
        for k in CANDS[lid]:
            key = f"{lid}_{k}"
            if key in TA:
                parts.append(audio(f"audio/vo_el/_attempts/{lid}/{k}.wav", f"候選 {k}（未採用）") + verdict_block(TA[key])
                             + plot(HERE / "plots_attempts" / f"{key}.png", f"F0 圖（{k}）"))
        new = ("".join(parts) + '<div class="meta">送「登」重做 4 次（seed 20261021–24），通過自動檢查的兩次「燈」仍是接在「主」後面一路往上升'
               '（三種寫法「燈／灯／登」、不同 seed 都一樣，看起來是這個聲線的連讀習慣），r3_a3 的逗號停頓也幾乎消失。'
               '量測沒有確認的改善，<b>維持 v04</b>。若許老師聽了覺得候選比較好，可用 '
               '<code>tools/vo_el_promote.py --pick a2_c013_05=audio/vo_el/_attempts/a2_c013_05/r3_a3.wav --line a2_c013_05 --ver v05</code> 換上。</div>')
        status = '<span class="tag warn">重做未採用（維持 v04）</span>'
    else:
        status = '<span class="tag mute">不需重做</span>'
    rows.append(f'''<section class="row{' redo' if lid in REDO else ''}" id="{lid}">
<header><b>{lid}</b> <span class="cue">cue {lid[:7]}</span> <span class="spk">{e(r4["role"])}</span> {status}</header>
<p class="txt">{hl(r4["text"])}</p>
<div class="cols"><div class="col"><h4>舊版 v04</h4>{audio(f"audio/vo/vo_{lid}_v04.wav", "舊版 v04")}{verdict_block(r4)}
<div class="meta">送出：{hl(v04_sent(lid))}</div>{plot(HERE / "plots_v04" / f"{lid}.png", "F0 圖（v04）")}</div>
<div class="col"><h4>新版</h4>{new or '<p class="muted">v04 量測為第一聲，未重做。</p>'}</div></div>
</section>''')

refs = []
for lid in REFS:
    r = T4[lid]
    refs.append(f'<section class="row ref"><header><b>{lid}</b> <span class="spk">{e(r["role"])}</span> <span class="tag mute">參考</span></header>'
                f'<p class="txt">{hl(r["text"])}</p>{audio(f"audio/vo/vo_{lid}_v04.wav", "v04")}{verdict_block(r)}'
                f'<div class="meta">送出：{hl(sent_of(lid))}</div>'
                f'{plot(HERE / "plots_v04" / f"{lid}.png", "F0 圖")}</section>')

page = f'''<!doctype html>
<html lang="zh-Hant-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>「燈」讀音試聽</title>
<style>
:root{{--bg:#faf8f4;--fg:#222;--muted:#6b6b6b;--card:#fff;--line:#e4dfd6;--ok:#2e7d32;--bad:#b3261e;--warn:#9a6700;--mark:#ffe7a3;--markd:#d7ecff}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1c1b19;--fg:#ece8e1;--muted:#a49f97;--card:#262421;--line:#3a3733;--ok:#7bc47f;--bad:#f2867d;--warn:#e0b44c;--mark:#5c4a12;--markd:#1f3c58}}}}
:root[data-theme="dark"]{{--bg:#1c1b19;--fg:#ece8e1;--muted:#a49f97;--card:#262421;--line:#3a3733;--ok:#7bc47f;--bad:#f2867d;--warn:#e0b44c;--mark:#5c4a12;--markd:#1f3c58}}
body{{background:var(--bg);color:var(--fg);font:15px/1.6 "PingFang TC","Heiti TC","Noto Sans TC",sans-serif;margin:0;padding:16px;max-width:1100px;margin-inline:auto}}
h1{{font-size:22px;margin:8px 0}} h2{{font-size:18px;margin:28px 0 8px}} h4{{margin:0 0 6px;font-size:14px;color:var(--muted)}}
.sum{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px}}
.sum li{{margin:3px 0}}
.row{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}}
.row.redo{{border-left:4px solid var(--warn)}}
.row header{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.cue,.spk{{color:var(--muted);font-size:13px}}
.txt{{font-size:18px;margin:6px 0 8px}}
mark{{background:var(--mark);color:inherit;padding:0 2px;border-radius:3px}} mark.d{{background:var(--markd)}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media (max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.au{{display:flex;align-items:center;gap:8px;margin:4px 0;flex-wrap:wrap}} .au span{{font-size:13px;color:var(--muted);min-width:7em}}
audio{{height:34px;max-width:100%}}
.v{{margin:6px 0;font-size:14px}} .why{{color:var(--muted);font-size:12.5px}}
.tag{{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid currentColor}}
.tag.ok{{color:var(--ok)}} .tag.bad{{color:var(--bad)}} .tag.warn{{color:var(--warn)}} .tag.mute{{color:var(--muted)}}
.meta{{font-size:12.5px;color:var(--muted);margin-top:4px}} .muted{{color:var(--muted)}}
.pl{{font-size:12.5px;margin-right:10px}} code{{font-size:12px;word-break:break-all}}
</style></head><body>
<h1>「燈」讀音試聽（v04 → v05）</h1>
<div class="sum"><ul>
<li>起因：許老師聽到開場 a0_c002_03 阿樂叔叔「慢慢摺，燈才會亮。」的「燈」念成「鄧」（第四聲）。</li>
<li>量測：large-v3-turbo 字級時間戳＋parselmouth F0，取每個「燈」的有聲音節核心，看起點、終點、最高點後的下降、相對該句音域的高低（工具 <code>tools/vo_tone_check.py</code>、<code>review/G3/el/deng/measure.py</code>）。
已知第四聲的 a0_c002_03 量到「最高點後降 4.5 半音、起點在音域上段」，判為疑似第四聲（方法驗證通過）；使用者認可的「紙登結」（a0_c001_01、a0_c003_01）的「登」是平或小幅上升。</li>
<li>v04 結果（24 句）：疑似第四聲 2 句（a0_c002_03、a6_c009_03，都是阿樂叔叔，都是直接送繁體「燈」）；無法判定 1 句（a2_c013_05，一路上升沒有平段）；其餘 21 句第一聲。</li>
<li>重做：pronounce.json 單句覆寫「燈→登」（全域表不動）；口頭禪三句（a0_c002_03、a6_c001_02、a6_c009_03）一起重做。同聲線、同設定；第 1 次沿用 v04 採用的 seed。
升 v05：a0_c002_03、a6_c009_03、a6_c001_02，新版「登」都量成第一聲。a2_c013_05 重做沒有改善，維持 v04（候選放在該列）。</li>
<li>字幕文字不變（仍是「燈」）；ElevenLabs 這次共計費 106 點（16 次呼叫，記在 audio/vo_el/ledger.json）。</li>
<li><b>聽感一律未驗證</b>：Claude 聽不到聲音，這裡只有聲學量測。請許老師用耳朵比對「舊版／新版」。</li>
</ul></div>
<h2>需要重做的句子</h2>
{''.join(r for r, lid in zip(rows, TARGETS) if lid in REDO)}
<h2>其他含「燈」的句子（v04 量測為第一聲，未重做）</h2>
{''.join(r for r, lid in zip(rows, TARGETS) if lid not in REDO)}
<h2>參考：「紙燈節」「燈籠」的句子（全域替身字或角色替身字已處理，送出文字見各列）</h2>
{''.join(refs)}
</body></html>
'''
(HERE / "listen.html").write_text(page, "utf-8")
print("寫出", HERE / "listen.html", len(page))
