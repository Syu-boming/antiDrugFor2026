"""第三幕（a3）Codex 角色姿勢提示詞：沿用 G5 共用美術的提示格式（review/G5/shared_art/raw/pose_*_v06.prompt.txt），只換姿勢與輸出路徑。
用法：/opt/anaconda3/bin/python3 review/G5/a3/scripts/make_prompts.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
SH = ROOT / "review/G5/shared_art/raw"
RAW = ROOT / "review/G5/a3/raw"
STYLE = ROOT / "review/G2a/S4.png"

def split_template(src):
    t = (SH / src).read_text()
    head, rest = t.split("POSE (very important):", 1)
    tail = rest[rest.index("The whole figure from the top"):]
    tail = tail[:tail.index("After the image is generated:")]
    return head, tail

AFTER = """After the image is generated:
1. The tool saves the PNG under ${{CODEX_HOME:-$HOME/.codex}}/generated_images/<session-id>/<call-id>.png. Other Codex sessions may be generating images in parallel into sibling folders, so copy YOUR OWN image (match your session id / image call id; do not just take the newest file across all folders).
2. Copy it unmodified (no crop, no resize, no re-encode) to review/G5/a3/raw/{id}.png inside the current workspace.
3. Print the copied file's pixel width and height (e.g. `sips -g pixelWidth -g pixelHeight -g hasAlpha review/G5/a3/raw/{id}.png`) and the absolute source path you copied from.
Do not create, edit or delete any other files. Do not regenerate unless the first generation failed. Final answer: source path, destination path, pixel width x height, whether it has alpha.
"""

JOBS = {
    "pose_xq_pointr_v07": ("pose_xq_cross_v06.prompt.txt", ROOT / "assets/generated/chr-xiaoqing_master_v04.png", """POSE (very important): the "leave first" gesture from a children's safety chant: pointing the way to the exit. The body faces the viewer in a gentle three-quarter view turned slightly toward the VIEWER'S RIGHT, standing upright, both soles flat on the floor, feet slightly apart. The arm on the RIGHT side of the picture (her left arm) is stretched out sideways toward the viewer's right, almost straight, at SHOULDER height, with the INDEX FINGER clearly POINTING horizontally to the viewer's right and the other fingers curled (one clear pointing hand, the finger points sideways, NOT up). The other arm hangs relaxed at her side. Her head is turned toward the pointing direction (viewer's right) so both eyes are still visible. The origami star hair clip stays on the SAME side of her head as in the second reference image (the viewer's right side of her head).
EXPRESSION: calm, confident, friendly: eyebrows level, eyes open looking toward the pointing direction, small closed smile. Not scared, not angry.
"""),
    "pose_xy_pointr_v07": ("pose_xy_palmno_v06.prompt.txt", ROOT / "assets/generated/chr-xiaoyu_master_v04.png", """POSE (very important): the "leave first" gesture from a children's safety chant: pointing the way to the exit. The body faces the viewer in a gentle three-quarter view turned slightly toward the VIEWER'S RIGHT, standing upright, both soles flat on the floor, feet slightly apart. The arm on the RIGHT side of the picture (his LEFT arm, the one wearing the smartwatch) is stretched out sideways toward the viewer's right, almost straight, at SHOULDER height, with the INDEX FINGER clearly POINTING horizontally to the viewer's right and the other fingers curled (one clear pointing hand, the finger points sideways, NOT up); the smartwatch on that wrist stays visible. The other arm hangs relaxed at his side. His head is turned toward the pointing direction (viewer's right) so both eyes and both glasses lenses are still visible.
EXPRESSION: calm, confident, friendly: eyebrows level, eyes open looking toward the pointing direction, small closed smile. Not scared, not angry.
"""),
    "pose_xy_glasses_v07": ("pose_xy_palmno_v06.prompt.txt", ROOT / "assets/generated/chr-xiaoyu_master_v04.png", """POSE (very important): stopping to think it over before answering. The whole body is in a gentle three-quarter view toward the VIEWER'S LEFT, standing still and upright, both soles flat on the floor. The hand on the LEFT side of the picture (his right hand) is raised to his face and the tip of its INDEX FINGER lightly pushes up the BRIDGE of his round glasses (the small bar between the two lenses); the fingertip touches only that bridge and does NOT cover either eye or either lens; the other fingers are curled loosely below, away from the eyes. The other arm (his LEFT arm, with the smartwatch visible on the wrist) hangs relaxed at his side. Head level, facing the viewer's left.
EXPRESSION: thoughtful and calm, as if saying "wait, let me think": eyebrows level, eyes open looking slightly down toward the viewer's left, mouth a small closed straight line. Not scared, not angry, not sad.
"""),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for jid, (src, master, pose) in JOBS.items():
        head, tail = split_template(src)
        txt = head + pose + "\n" + tail + AFTER.format(id=jid)
        (RAW / f"{jid}.prompt.txt").write_text(txt)
        (RAW / f"{jid}.refs").write_text(f"{STYLE}\n{master}\n")
        print(jid, len(txt))

if __name__ == "__main__":
    main()
