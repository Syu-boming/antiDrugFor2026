import json
from pathlib import Path

OUT = Path(__file__).parent / "cands"
OUT.mkdir(exist_ok=True)
DOC = json.loads(Path("/Users/boming/Documents/AI tool/反毒小劇場/audio/vo_el/casting/ye.json").read_text("utf-8"))["_說明"]
DOC += ("（兒童組加）post.pitch_shift_st＝PSOLA 整段改調半音；post.stretch＝固定長度倍數；post.auto_stretch＝{target, tolerance, min, "
        "max, default}：母帶前淨語速超出角色表語速 ±tolerance 時，用 PSOLA 把長度乘 淨語速÷target（夾在 min–max）；eleven_v3 不理會 speed，只能這樣放慢。")

V = {
    "Tiffy": ("1AKkSX7KMPHIWuz76m0n", "Tiffy - Taiwanese Bilingual Narrator"),
    "Vivian": ("xrDmUzhnE51Df8z38r1M", "Vivian - Taiwanese Social Media"),
    "Yui": ("kGjJqO6wdwRN9iJsoeIC", "Yui - Delicate, Graceful and Soothing"),
    "Lulu": ("BT0SH7Hb8NRPpT5xbCgg", "Lulu - Cute Little Witch"),
    "Chloe": ("cXGZGSG0udxZ0hTfyBnC", "Chloe - Gentle, Delicate, Reassuring"),
    "Juin": ("7Sk22fdUzAroSHJkVoXB", "Juin - Taiwanese Male Adult"),
    "KuoYu": ("Z9RJEkFYQw307BCQULDR", "Kuo Yu - Taiwan"),
    "XuMing": ("A3T1GnLHdn0WL5w4TMtq", "Xu Ming"),
}
ROLE = {"xiaoqing": "小晴", "xiaoyu": "小宇", "pinan": "品安", "zhezhe": "折折", "ale": "阿樂叔叔"}
ALE_AFF = ["a2_c001_02", "a2_c002_01", "a2_c008_01", "a2_c008_02", "a2_c012_02", "a4_c001_02", "a4_c008_01"]


def v3(code, voice, gap=450, shift=0.0, stretch_max=1.3, lines=None):
    vid, name = V[voice]
    post = {"auto_stretch": {"tolerance": 0.2, "min": 1.0, "max": stretch_max, "default": 1.0}}
    if shift:
        post["pitch_shift_st"] = shift
    return {"_說明": DOC, "role": ROLE[code], "code": code, "status": "active", "voice_id": vid, "voice_name": name,
            "model": "eleven_v3", "language_code": "zh",
            "settings": {"stability": 0.5, "similarity_boost": 0.75, "style": None, "speed": None, "use_speaker_boost": None},
            "seed_base": 20261021, "sentence_gap_ms": gap, "segment_mode": "post",
            "tail_guard": {"mode": "always", "suffix": "……嗯。", "min_pause_ms": 300},
            "text_mode": "pronounce", "text_subs": {"119": "一一九"}, "post": post,
            "adaptive_speed": {"enabled": False, "note": "eleven_v3 不理會 speed；改用 post.auto_stretch"},
            "lines": lines or {}}


def v2(code, voice, speed=0.88, gap=450, shift=0.0, stretch_max=1.25, lines=None):
    vid, name = V[voice]
    post = {"auto_stretch": {"tolerance": 0.2, "min": 1.0, "max": stretch_max, "default": 1.0}}
    if shift:
        post["pitch_shift_st"] = shift
    return {"_說明": DOC, "role": ROLE[code], "code": code, "status": "active", "voice_id": vid, "voice_name": name,
            "model": "eleven_multilingual_v2", "language_code": None,
            "settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "speed": speed, "use_speaker_boost": True},
            "seed_base": 20261021, "sentence_gap_ms": gap, "segment_mode": "post",
            "tail_guard": {"mode": "on_fail", "suffix": "……嗯。", "min_pause_ms": 300},
            "text_mode": "pronounce", "text_subs": {"119": "一一九"}, "post": post,
            "adaptive_speed": {"enabled": True, "step": 0.04, "min": 0.7, "max": 1.0},
            "lines": lines or {}}


ale_lines_v2 = {lid: {"settings": {"speed": 0.8}} for lid in ALE_AFF}
yi = {"synth_text": "咦？我想揮手……[[break:550]]手怎麼跑到旁邊去了？", "sentence_gap_ms": 350}
ale_lines_v2["a2_c002_01"] = dict(ale_lines_v2["a2_c002_01"], **yi)
ale_lines_v3 = {"a2_c002_01": dict(yi)}

C = {
    "xq_tiffy_v3": v3("xiaoqing", "Tiffy"),
    "xy_vivian_v3": v3("xiaoyu", "Vivian"),
    "xy_yui_v3_m2": v3("xiaoyu", "Yui", shift=-2.0),
    "pa_yui_v3_m3": v3("pinan", "Yui", shift=-3.0, stretch_max=1.4),
    "pa_vivian_v3_m1": v3("pinan", "Vivian", shift=-1.0, stretch_max=1.4),
    "zz_lulu_v3": v3("zhezhe", "Lulu"),
    "zz_chloe_v3": v3("zhezhe", "Chloe"),
    "ale_juin_v2": v2("ale", "Juin", lines=ale_lines_v2),
    "ale_kuoyu_v2": v2("ale", "KuoYu", lines=ale_lines_v2),
    "ale_xuming_v2": v2("ale", "XuMing", lines=ale_lines_v2),
    "ale_kuoyu_v3": v3("ale", "KuoYu", gap=500, stretch_max=1.45, lines=ale_lines_v3),
}
for k, c in C.items():
    (OUT / f"{k}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), "utf-8")
print(list(C))
