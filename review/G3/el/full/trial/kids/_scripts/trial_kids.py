"""兒童與阿樂組：試聲線包裝（呼叫 tools/vo_el_prod.py 的同一套合成＋檢查，但輸出改到試聽資料夾，不碰正式輸出）。

用法：tools/.venv/bin/python trial_kids.py <tag> <candidate.json> <max_credits> <max_attempts> <line> [<line> ...]
  candidate.json＝一個角色設定（同 audio/vo_el/casting/<code>.json 格式）。
輸出：review/G3/el/full/trial/kids/<tag>/（build_report_trial.json、_attempts/、out/、casting/）。
原始 mp3 快取共用 audio/vo_el/_raw/（同聲線、同文字、同 seed、同設定才會沿用，不重複計費）。
點數記入 audio/vo_el/ledger.json 與 audio/vo/elevenlabs_usage.jsonl（purpose「EL 全劇 試聲線（孩子與阿樂組）」）。
"""
import json
import shutil
import sys
import types
from pathlib import Path

ROOT = Path("/Users/boming/Documents/AI tool/反毒小劇場")
sys.path.insert(0, str(ROOT / "tools"))
import vo_el_prod as P  # noqa: E402

tag, cand, maxc, maxa, *ids = sys.argv[1:]
T = P.FULL / "trial" / "kids" / tag
(T / "casting").mkdir(parents=True, exist_ok=True)
c = json.loads(Path(cand).read_text("utf-8"))
(T / "casting" / f"{c['code']}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), "utf-8")
P.CAST_DIR = T / "casting"
P.REPORT = T / "build_report_trial.json"
P.TIMINGS = T / "timings_trial.json"
P.OUT = T / "out"
P.ATT = T / "_attempts"
P.LIP = T / "lipsync"
P.PURPOSE = "EL 全劇 試聲線（孩子與阿樂組）"
P.OUT.mkdir(parents=True, exist_ok=True)
args = types.SimpleNamespace(max_attempts=int(maxa), max_credits=int(maxc), dry_run=False, force=False,
                             include_draft=True)
P.run_el(ids, args)
