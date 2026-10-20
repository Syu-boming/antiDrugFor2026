"""G4 驗收包：配音逐句 faster-whisper 逐字稿與劇本差異（由 tools/g4_review_pack.mjs 呼叫）。

用法：tools/.venv/bin/python tools/g4_transcripts.py <驗收包資料夾>
- 讀 <資料夾>/timeline.json 取得 G4 用到的台詞與配音檔；劇本原文取自 script/劇本_v03.md。
- 每句轉寫兩次來源：配音檔本身、最終混音中該句的時段（<資料夾>/_work/mixseg/<台詞>.wav，含配樂與音效）。
- 兩個模型（small、large-v3-turbo）；比對方法沿用 tools/vo_lib.py 的 compare（字錯率、含聲調拼音錯率、差異清單）。
輸出：transcripts.json、transcripts.md（只列轉寫與差異，不下結論）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vo_lib  # noqa: E402

out = Path(sys.argv[1]).resolve()
tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
script = vo_lib.load_lines()
report = json.loads((ROOT / "audio/vo/build_report.json").read_text(encoding="utf-8")) if (ROOT / "audio/vo/build_report.json").exists() else {}

items = []
for c in tl["cues"]:
    for l in c["lines"]:
        src = tl["audio"].get(l["audioId"], {}).get("source")
        if not src:
            continue
        ref = script.get(l["id"], {}).get("text", l["text"])
        syn = "".join(s.get("synth_text", "") for s in report.get(l["id"], {}).get("synthesis", [])) or ref
        items.append({"id": l["id"], "speaker": l["speaker"], "script": ref, "cue_text": l["text"], "synth_text": syn,
                      "vo": ROOT / src, "mix": out / "_work" / "mixseg" / f"{l['id']}.wav"})

rows = []
for it in items:
    rows.append({"id": it["id"], "speaker": it["speaker"], "script": it["script"], "cue_text_equals_script": it["cue_text"].replace("\n", "") == it["script"],
                 "vo_file": str(it["vo"].relative_to(ROOT)), "vo": {}, "mix": {}})
for mname in vo_lib.ASR_MODELS:
    for src in ("vo", "mix"):
        paths = [it[src] for it in items if it[src].exists()]
        tx = vo_lib.transcribe(paths, mname)
        for it, row in zip(items, rows):
            p = str(it[src])
            if p in tx:
                c = vo_lib.compare(it["script"], it["synth_text"], tx[p])
                row[src][mname] = {"hyp": c["hyp"], "hyp_trad": c["hyp_trad"], "cer": c["cer"], "per": c["per"], "diffs": c["diffs"], "checks": c["checks"]}
    print(f"[transcripts] {mname} 完成")

res = {
    "method": "faster-whisper（small、large-v3-turbo；CPU int8；language=zh；beam 5；initial_prompt「以下是繁體中文的台灣華語。」）逐句轉寫；"
              "比對沿用 tools/vo_lib.py compare：轉寫先轉繁體、去標點後與劇本逐字對齊，字不同的段落再比含聲調拼音（參考讀音取合成用文字）。"
              "來源「配音檔」＝audio/vo 的單句檔；「最終混音該句」＝audio/g4_mix.wav 中該句時段（前後各加 0.1 秒），含配樂與音效。",
    "rows": rows,
}
(out / "transcripts.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

L = ["# G4 配音逐字稿與劇本差異", "", f"- 方法：{res['method']}", "- 只列轉寫結果與差異，不含評語。聽感未驗證。", ""]
for r in rows:
    L.append(f"## {r['id']}｜{r['speaker']}")
    L.append("")
    L.append(f"- 劇本 v03：{r['script']}")
    L.append(f"- cue 檔文字與劇本相同：{r['cue_text_equals_script']}")
    L.append(f"- 配音檔：`{r['vo_file']}`")
    L.append("")
    L.append("| 來源 | 模型 | 轉寫（轉繁體） | CER | PER | 差異（劇本→轉寫） | 讀音檢查詞 |")
    L.append("|---|---|---|---|---|---|---|")
    for src, lab in (("vo", "配音檔"), ("mix", "最終混音該句")):
        for mname, m in r[src].items():
            diffs = "；".join(f"{d['ref'] or '∅'}→{d['hyp'] or '∅'}（{d['kind']}）" for d in m["diffs"]) or "無"
            checks = "；".join(f"{c['word']}：{c['status']}" for c in m["checks"]) or "—"
            L.append(f"| {lab} | {mname} | {m['hyp_trad']} | {m['cer']} | {m['per']} | {diffs} | {checks} |")
    L.append("")
(out / "transcripts.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"[transcripts] → {out / 'transcripts.md'}")
