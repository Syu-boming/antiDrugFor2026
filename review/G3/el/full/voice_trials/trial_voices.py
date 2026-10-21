"""成人組試聲線：同一角色多個候選聲線（或參數）各念 2–3 句代表句，用 tools/vo_el_prod.py 的同一套合成與 (a)–(f) 檢查。

  tools/.venv/bin/python review/G3/el/full/voice_trials/trial_voices.py <trial.json> --max-credits N

trial.json：{"code": 角色代碼, "lines": [...], "attempts": 次數, "variants": {名稱: 角色設定（同 audio/vo_el/casting/*.json）}}
輸出：本資料夾 <code>/<名稱>/<台詞>_a<k>.wav、<code>/results.json。不寫 build_report_el.json／timings_el.json。
ElevenLabs 呼叫經 vo_el_prod.el_call（記入 audio/vo/elevenlabs_usage.jsonl 與 audio/vo_el/ledger.json；原始檔快取在
audio/vo_el/_raw/<台詞>/，檔名含角色代碼、嘗試序號與請求內容雜湊——正式製作用同一份設定時直接沿用、不重複計費）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import vo_el_prod as P  # noqa: E402

V = P.V


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("trial")
    ap.add_argument("--max-credits", type=int, default=100)
    args = ap.parse_args()
    T = json.loads(Path(args.trial).read_text("utf-8"))
    code = T["code"]
    out_dir = HERE / code
    res_p = out_dir / "results.json"
    results = P.jload(res_p, {})
    run = {"spent": 0, "calls": 0, "failed": 0, "max_credits": args.max_credits}
    P.ledger_run({"start": P.now(), "lines": T["lines"], "max_credits": args.max_credits,
                  "note": f"試聲線 {code}：{'、'.join(T['variants'])}（review/G3/el/full/voice_trials/）"}, start=True)
    stop = None
    try:
        for vname, cfg in T["variants"].items():
            cfg = dict(cfg, code=code, role=P.CODE2ROLE[code])
            for lid in cfg.get("trial_lines") or T["lines"]:
                ln = P.LINES[lid]
                key = f"{vname}|{lid}"
                prev = results.get(key, {}).get("attempts", [])
                if any(not a["failed"] for a in prev):
                    continue
                base = P.jload(P.EDGE_METRICS, {}).get(lid)
                if not base or base.get("signature") != P.edge_signature(lid):
                    base = P.baseline_line(lid)
                targets = P.line_targets(code, lid, cfg)
                loud = float(cfg.get("lines", {}).get(lid, {}).get("loudness_offset_db", 0.0))
                for k in range(len(prev), int(cfg.get("trial_attempts") or T.get("attempts", 1))):
                    x, segrecs, settings_by, seeds, gaps, bnd = P.render_attempt(lid, ln, [cfg], k, prev, run)
                    y, minfo = V.master(x, target=P.D["target_lufs"], tp_max=P.D["true_peak_max"], head_ms=P.D["head_ms"],
                                        tail_ms=P.D["tail_ms"], short_s=P.D.get("short_line_s", 3.0))
                    if loud:
                        y = (y * 10 ** (loud / 20)).astype("float32")
                    wav = out_dir / vname / f"{lid}_a{k + 1}.wav"
                    V.write_wav(wav, y)
                    pb = P.boundary_pauses(y, x, gaps) if gaps is not None else None
                    n_sent = (len(gaps) + 1) if gaps is not None else P.n_sentences(ln["text"])
                    asr = P.asr_eval(wav, ln["text"], P.reading_of(ln["text"], lid))
                    ch, summ = P.evaluate(wav, ln, targets, [s["tail"] for s in segrecs], pb, n_sent, asr,
                                          base.get("asr") if base else None, True, loud, bnd)
                    failed, n, det = P.score(ch)
                    prev.append({"k": k + 1, "seeds": seeds, "settings": settings_by, "segments": segrecs, "wav": P.rel(wav),
                                 "metrics": summ, "asr": {m: v["hyp_trad"] for m, v in asr.items()}, "checks": ch,
                                 "failed": failed, "detail_score": det, "fail_detail": P.fail_detail(ch),
                                 "billed": sum(s["billed"] or 0 for s in segrecs)})
                    results[key] = {"variant": vname, "line": lid, "voice": cfg["voice_name"], "model": cfg["model"],
                                    "attempts": prev}
                    P.jsave(res_p, results)
                    print(f"{vname} {lid} 嘗試{k + 1}：未通過 {','.join(failed) or '無'}  淨語速 {ch['d']['value']}  "
                          f"F0 {summ['f0_median']}  {P.fail_detail(ch)}  ｜" + "｜".join(asr[m]['hyp_trad'] for m in asr))
                    if not failed:
                        break
    except (P.BudgetStop, P.ApiStop) as ex:
        stop = str(ex)
        print("停止：", stop)
    P.ledger_run({"end": P.now(), "spent": run["spent"], "calls": run["calls"], "failed_calls": run["failed"], "stopped": stop})
    print(f"本次計費 {run['spent']} 點（呼叫 {run['calls']} 次、失敗 {run['failed']} 次）")


if __name__ == "__main__":
    main()
