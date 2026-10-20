"""ElevenLabs 聲線設計（G3 B 版：童聲方案）。

用法：
  tools/.venv/bin/python tools/vo_design.py preview <角色代號>      # 依 audio/vo/design_specs.json 產生 3 個試聽
  tools/.venv/bin/python tools/vo_design.py save <角色代號> <generated_voice_id> <聲線名稱>

試聽檔存 review/G3/design/<角色>_<序號>.mp3，結果寫入 review/G3/design/<角色>_previews.json；
每次呼叫的字數記錄在 audio/vo/elevenlabs_usage.jsonl。金鑰只從環境變數讀，不印出。
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import vo_lib as V

DESIGN_DIR = V.ROOT / "review" / "G3" / "design"
SPECS = V.VO_DIR / "design_specs.json"


def preview(role: str) -> None:
    specs = json.loads(SPECS.read_text(encoding="utf-8"))
    sp = specs[role]
    desc = sp["description"]
    if len(desc) < 100:
        raise SystemExit("描述文字少於 100 字元")
    lines = V.load_lines()
    pron = V.load_pronounce()
    text = "".join(V.apply_pronounce(lines[l]["text"], pron, "elevenlabs", l) for l in sp["preview_lines"])
    if len(text) < 100:
        raise SystemExit(f"試聽文字 {len(text)} 字元，少於 100")
    body = {"voice_description": desc, "model_id": sp.get("model", "eleven_ttv_v3"), "text": text,
            "auto_generate_text": False, "loudness": 0.5, "guidance_scale": sp.get("guidance_scale", 5),
            "seed": sp.get("seed", 20261021), "should_enhance": False}
    code, payload, hdr = V.el_request("POST", "/v1/text-to-voice/design?output_format=mp3_44100_128", body, timeout=300)
    entry = {"purpose": f"G3 聲線設計 {role}", "endpoint": "text-to-voice/design", "model": body["model_id"],
             "text_chars": len(text), "description_chars": len(desc), "ok": code == 200, "http": code,
             "billed": hdr.get("character-cost"), "request_id": hdr.get("request-id")}
    DESIGN_DIR.mkdir(parents=True, exist_ok=True)
    if code != 200:
        try:
            entry["detail"] = json.loads(payload).get("detail")
        except Exception:
            entry["detail"] = payload[:300].decode(errors="replace")
        V.log_usage(entry)
        (DESIGN_DIR / f"{role}_previews.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2), "utf-8")
        print(json.dumps(entry, ensure_ascii=False))
        return
    d = json.loads(payload)
    V.log_usage(entry)
    out = {"role": role, "description": desc, "model": body["model_id"], "text": text, "previews": []}
    for i, p in enumerate(d.get("previews", []), 1):
        f = DESIGN_DIR / f"{role}_{i}.mp3"
        f.write_bytes(base64.b64decode(p["audio_base_64"]))
        out["previews"].append({"n": i, "file": str(f.relative_to(V.ROOT)), "generated_voice_id": p["generated_voice_id"],
                                "duration_secs": p.get("duration_secs"), "language": p.get("language")})
    (DESIGN_DIR / f"{role}_previews.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "description"}, ensure_ascii=False, indent=1))


def save(role: str, gid: str, name: str) -> None:
    specs = json.loads(SPECS.read_text(encoding="utf-8"))
    desc = specs[role]["description"]
    body = {"voice_name": name, "voice_description": desc[:1000], "generated_voice_id": gid,
            "labels": {"project": "antidrug-theater", "role": role}}
    code, payload, hdr = V.el_request("POST", "/v1/text-to-voice", body)
    if code != 200:
        # 舊端點
        code, payload, hdr = V.el_request("POST", "/v1/text-to-voice/create-voice-from-preview", body)
    try:
        d = json.loads(payload)
    except Exception:
        d = {"raw": payload[:300].decode(errors="replace")}
    res = {"role": role, "http": code, "voice_id": d.get("voice_id"), "name": name,
           "detail": d.get("detail") if code != 200 else None}
    V.log_usage({"purpose": f"G3 儲存設計聲線 {role}", "endpoint": "text-to-voice", "ok": code == 200, "http": code,
                 "text_chars": 0, "detail": res["detail"]})
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview(sys.argv[2])
    elif sys.argv[1] == "save":
        save(sys.argv[2], sys.argv[3], sys.argv[4])
