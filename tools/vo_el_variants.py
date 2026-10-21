"""單句發音修正實驗：同一句用幾種模型／設定／寫法各合成幾次，兩個轉寫模型比對，產生試聽清單給使用者挑。

用法（專案根目錄）：
  tools/.venv/bin/python tools/vo_el_variants.py <台詞編號> <輸出資料夾> <variants.json>
variants.json：[{"name", "voice_id", "model", "text", "settings": {...}, "seeds": [..], "language_code"?}]
輸出：<輸出資料夾>/<name>_s<seed>.mp3／.wav、results.json（轉寫、計費、request_id）。
每次呼叫都記進 audio/vo/elevenlabs_usage.jsonl（purpose「EL 發音修正」）。已存在的檔不重叫。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vo_lib as V  # noqa: E402

FMT = "mp3_44100_128"


def main():
    lid, out_dir, vfile = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = V.load_lines()
    ref = lines[lid]["text"]
    reading = V.strip_breaks(V.apply_pronounce(ref, V.load_pronounce(), "global", lid))
    res_path = out_dir / "results.json"
    results = json.loads(res_path.read_text("utf-8")) if res_path.exists() else {}
    spent = 0
    for v in json.loads(vfile.read_text("utf-8")):
        for seed in v["seeds"]:
            key = f"{v['name']}_s{seed}"
            mp3, wav = out_dir / f"{key}.mp3", out_dir / f"{key}.wav"
            if not mp3.exists():
                body = {"text": v["text"], "model_id": v["model"], "seed": int(seed)}
                if v.get("settings"):
                    body["voice_settings"] = {k: x for k, x in v["settings"].items() if x is not None}
                if v.get("language_code"):
                    body["language_code"] = v["language_code"]
                code, payload, hdr = V.el_request("POST", f"/v1/text-to-speech/{v['voice_id']}?output_format={FMT}", body)
                if code != 200:
                    V.log_usage({"purpose": f"EL 發音修正 {lid} {key}", "voice_id": v["voice_id"], "model": v["model"],
                                 "ok": False, "http": code, "text_chars": len(v["text"]), "seed": seed})
                    results[key] = {"error": code, "detail": payload[:300].decode("utf-8", "replace")}
                    continue
                mp3.write_bytes(payload)
                cost = hdr.get("character-cost")
                billed = int(cost) if cost and str(cost).strip().isdigit() else None
                spent += billed or 0
                V.log_usage({"purpose": f"EL 發音修正 {lid} {key}", "voice_id": v["voice_id"], "model": v["model"],
                             "ok": True, "http": 200, "text_chars": len(v["text"]), "billed": billed,
                             "billed_source": "character-cost", "request_id": hdr.get("request-id"), "seed": seed,
                             "raw": str(mp3.relative_to(ROOT))})
                results[key] = {"variant": v, "seed": seed, "billed": billed, "request_id": hdr.get("request-id")}
            if not wav.exists():
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", "48000", str(wav)], check=True)
            r = results.setdefault(key, {"variant": v, "seed": seed})
            if "asr" not in r:
                r["asr"] = {}
                for m in V.ASR_MODELS:
                    hyp = V.transcribe([wav], m)[str(wav)]
                    c = V.compare(ref, reading, hyp)
                    r["asr"][m] = {"hyp_trad": c["hyp_trad"], "cer": c["cer"], "diffs": c["diffs"]}
            res_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
            print(key, "|", " ｜ ".join(f"{m}: {r['asr'][m]['hyp_trad']}" for m in r["asr"]))
    print("本次計費", spent)


if __name__ == "__main__":
    main()
