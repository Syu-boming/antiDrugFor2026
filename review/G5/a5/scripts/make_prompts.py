"""第五幕（a5）Codex image_gen 提示詞 → review/G5/a5/raw/<id>.prompt.txt、<id>.refs。

用法：/opt/anaconda3/bin/python3 review/G5/a5/scripts/make_prompts.py
角色姿勢沿用 G5 共用美術的提示格式（review/G5/shared_art/raw/*.prompt.txt）：風格參考 S4＋角色母版＋同劇角色（比例）。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "review/G5/a5/raw"
SHARED = ROOT / "review/G5/shared_art/raw"
S4 = str(ROOT / "review/G2a/S4.png")
GEN = ROOT / "assets/generated"

# 共用尾段（角色）：取自 shared_art 的 chr_lin_sit_v01（整體、臉、風格、無文字、存檔步驟），存檔路徑改成本幕
tail = (SHARED / "chr_lin_sit_v01.prompt.txt").read_text()
TAIL_CHAR = tail[tail.index("The whole figure"):]

XQ = """- 9-year-old girl, shoulder-length dark brown bob; on her LEFT side of the head (the right side of the hair as seen by the viewer in a front view) a small ORIGAMI STAR hair clip whose paper folds/creases are clearly visible; mustard-yellow short-sleeve top; deep lake-teal (dark blue-green) overalls with rolled cuffs; a small spiral-bound notebook peeking out of the overalls' bib pocket, its cover completely BLANK (no marks, no letters); white socks; mustard-yellow sneakers. Same exact colors as the second reference image (do NOT lighten or darken them; the overalls stay the same deep teal as the reference).
- Proportions exactly like the master: 4.45 heads tall (head including hair = about 22.5% of the full height), slim natural 9-year-old picture-book child, NOT chibi, NOT big-headed."""

XY = """- 9-year-old boy, short slightly curly dark brown hair; round thin black-framed glasses; deep vermilion (dark orange-red) zip-up hoodie with white drawstrings and the hood resting behind his neck; khaki shorts with rolled cuffs; white crew socks; navy-blue canvas sneakers with white soles and white laces; a small dark navy backpack with shoulder straps over both shoulders. Same exact colors as the second reference image (do NOT lighten or darken them; the hoodie stays the same deep vermilion as the reference).
- On his LEFT wrist a generic kids' smartwatch: dark gray strap and a plain round dark-gray face with nothing drawn on it (no numbers, no letters, no logo); it must be visible.
- Proportions exactly like the master: 4.3 heads tall (head including hair = about 23% of the full height), slim natural 9-year-old picture-book child, NOT chibi, NOT big-headed."""

CHEN = """- Grandpa Chen, the school gate guard: a man in his 60s, kind and steady, with a sturdy, solid build (broad shoulders, a little stocky; dignified, not comical).
- Short gray-white crew-cut hair, thick gray eyebrows, gentle smile lines at the corners of his eyes, clean-shaven.
- A light gray short-sleeve button-up shirt with two plain chest pockets and NOTHING on it: no badge, no patch, no emblem, no insignia, no name tag, no text. Over it a yellow-green (lime) crossing-guard safety vest with two matte off-white (cream) horizontal stripes; the stripes are plain flat cream paper, NOT glowing, NOT shiny. Dark charcoal-gray trousers; black shoes.
- It must NOT look like a real police or security-company uniform: no hat, no cap, no badge, no shoulder patches, no epaulettes, no duty belt, no radio, no baton, no whistle.
- Natural adult proportions exactly like the master: about 6.2 heads tall (head = about 16% of the full height), NOT chibi, NOT big-headed."""

HEAD_CHAR = """Use your built-in image generation tool (image_gen) to generate exactly ONE image: {what} of an existing character for a children's paper-cut puppet theater. PORTRAIT (vertical) orientation, request the tall 2:3 size (1024x1536), with a TRANSPARENT background (real alpha channel).

THREE reference images are attached. The FIRST is only the art-style reference (thick matte cardstock pop-up picture book). The SECOND is the FINAL approved character master. The THIRD is another approved character of the same show (for scale and style). Draw THE SAME CHARACTER as the second reference - identical face, identical design and identical colors - only the pose and expression change:
"""

JOBS = {}

JOBS["a5_chen_shout_v01"] = (
    HEAD_CHAR.format(what="a full-body standing POSE") + CHEN + """

POSE (very important): calling out loudly but kindly to a colleague who is far away on the right (off-picture). Standing upright, the whole body in a three-quarter view toward the VIEWER'S RIGHT, both soles flat on the floor, feet slightly apart. The hand on the RIGHT side of the image is raised to his face with the palm cupped beside his mouth (fingers together, like a little megaphone), the elbow out to the side; the hand does NOT cover his eyes or nose, the mouth stays visible next to the cupped palm. The other arm (on the LEFT side of the image) hangs down relaxed along his body, that hand loosely closed in a fist as if gripping a thin pole (draw NO pole, NO flag, nothing in the hand). The head turns toward the right, eyes looking right into the distance.
EXPRESSION: clear, calm and friendly calling: eyebrows slightly raised, mouth open in a medium "ah" shape (calling a name), not angry, not shouting in fear.

""" + TAIL_CHAR,
    [S4, str(GEN / "chr-chen_master_v01.png"), str(GEN / "chr-xiaoqing_master_v04.png")],
)

JOBS["a5_xq_sitb_v01"] = (
    HEAD_CHAR.format(what="a full-body SITTING pose") + XQ + """

POSE (very important): P-QG2: sitting on a hospital waiting bench that is NOT drawn (an invisible seat - draw NO bench, NO chair, NO seat of any kind; the bench is a separate stage piece added later). Three-quarter view toward the VIEWER'S RIGHT. She sits a little forward on the seat, thighs horizontal, knees bent, lower legs hanging down vertically, her small sneakers side by side and lifted slightly above the floor line (a child on an adult bench), both hands resting on her knees. Her head is lowered about 10 degrees (a little sad, listening), face still clearly visible with both eyes visible. Because she faces the viewer's right, the origami star clip on her LEFT side of the head is on the far side: only a small part of it peeks out at the right edge of her hair in the image. Draw her at the same scale as the standing reference (same head size).
EXPRESSION: quiet and a little worried / sad, eyebrows slightly raised in the middle, eyes open, mouth closed in a small soft line. Not crying, no tears.

""" + TAIL_CHAR,
    [S4, str(GEN / "chr-xiaoqing_master_v04.png"), str(GEN / "chr-lin_pose-sit_v01.png")],
)

JOBS["a5_xy_sitb_v01"] = (
    HEAD_CHAR.format(what="a full-body SITTING pose") + XY + """

POSE (very important): P-XY3: sitting on a hospital waiting bench that is NOT drawn (an invisible seat - draw NO bench, NO chair, NO seat of any kind; the bench is a separate stage piece added later). Three-quarter view toward the VIEWER'S RIGHT. He sits on the seat with thighs horizontal, knees bent, lower legs hanging down vertically, sneakers side by side and lifted slightly above the floor line (a child on an adult bench), both hands resting on his knees so the smartwatch on his left wrist is visible. The backpack stays on his back (only the straps and a small part of the bag are visible behind him). Head level, looking right, face clearly visible with both eyes visible behind the glasses. Draw him at the same scale as the standing reference (same head size).
EXPRESSION: quiet, a little worried but hopeful: eyebrows slightly raised in the middle, eyes open, mouth closed. Not crying, no tears.

""" + TAIL_CHAR,
    [S4, str(GEN / "chr-xiaoyu_master_v04.png"), str(GEN / "chr-lin_pose-sit_v01.png")],
)

MEDICS = """Use your built-in image generation tool (image_gen) to generate exactly ONE image: TWO NEW supporting adult characters (paramedics) for a children's paper-cut puppet theater, drawn as two SEPARATE standing cut-out figures side by side. LANDSCAPE orientation, request the wide 3:2 size (1536x1024), with a TRANSPARENT background (real alpha channel).

THREE reference images are attached. The FIRST is only the art-style reference (thick matte cardstock pop-up picture book). The SECOND (Grandpa Chen) and THIRD (Nurse Ye) are approved adults of the same show. Draw the two new characters in EXACTLY the same rendering style, line weight, face style, flat colors, white paper-core border and natural adult proportions as the second and third references:
- Paramedic A: a man in his 30s, short black hair, calm and kind. Paramedic B: a woman in her 30s, black hair tied in a low ponytail, calm and kind.
- Both wear the SAME custom paramedic uniform: a dark charcoal-gray (#4A4F55-like) zip jacket and matching dark charcoal-gray trousers, black work shoes; TWO plain matte cream-white horizontal stripes around each lower sleeve and around the trouser legs (flat paper, NOT glowing, NOT shiny, NOT reflective-looking); on the upper LEFT arm a small round cream patch showing ONLY a simple icon of an open hand holding a heart (the heart in soft warm coral-orange, not saturated red). Nothing else on the uniform.
- Absolutely NO red cross, NO plus/cross symbol of any kind, NO star of life, NO text, NO letters, NO numbers, NO real agency colors or emblems, NO helmets, NO medical bags, NO stethoscope, NO gloves.
- Natural adult proportions exactly like the references: about 6.2 heads tall (head = about 16% of the full height), slim, NOT chibi, NOT big-headed. Both figures the same scale as the references (same head size), the man slightly taller than the woman.

POSE (very important): both stand upright and calm, side by side, each in a three-quarter view toward the VIEWER'S RIGHT, both soles flat on the floor, arms relaxed at the sides (hands relaxed and empty), heads turned slightly right, attentive. The two figures do NOT touch or overlap: leave a clear EMPTY transparent gap of at least 120 px between them (they will be cut apart into two separate stage pieces).
EXPRESSION: both calm, kind and professional, small gentle closed-mouth expressions.

Both whole figures from the top of the hair to the soles and the fingertips are visible with empty transparent margin all around (nothing cropped). Face style exactly like the approved characters: simple dark eyes with one small white highlight, small simple nose, small mouth, soft rosy cheeks, thin dark lines. Faces fully visible (three-quarter view, both eyes visible, the far eye slightly narrower), never a strict side profile.

""" + TAIL_CHAR[TAIL_CHAR.index("ART STYLE"):].replace("the figure", "each figure").replace("The figure", "Each figure")
JOBS["a5_medics_v01"] = (MEDICS, [S4, str(GEN / "chr-chen_master_v01.png"), str(GEN / "chr-ye_master_v01.png")])

HOSP = """Use your built-in image generation tool (image_gen) to generate exactly ONE image: a flat stage BACKDROP (the far wall of a quiet hospital corridor at early evening) for a children's paper-cut puppet theater. LANDSCAPE orientation, request the wide 3:2 size (1536x1024). Opaque image (no transparency needed).

TWO reference images are attached. The FIRST is the art-style reference ("3D pop-up picture book made of thick matte cardstock": paper fiber texture, layered cut-paper shapes, soft warm colors). The SECOND is an approved interior backdrop of the same show (match its paper texture, line weight and level of detail).

CONTENT (very important):
- A straight-on, frontal ELEVATION view of one long corridor wall (like a theater flat seen face-on): NO perspective vanishing lines, NO floor, NO ceiling, NO people, NO animals. The wall fills the whole picture; along the very bottom edge runs a simple wooden baseboard and just above it a horizontal light-wood handrail along the whole wall.
- Wall: soft warm cream / pale butter-yellow plaster in two tones (lower half slightly darker warm beige, upper half light cream), gentle.
- On the LEFT THIRD: two large tall windows with simple light-wood frames showing a calm early-evening sky (soft apricot and lavender gradient, one or two tiny cut-paper clouds, a far row of low rooftops as simple silhouettes, no lit windows, no stars, no moon).
- In the CENTER: plain wall with one small framed picture of a simple cut-paper landscape (green hills and a round sun shape, no text), hung at about 60% of the picture height.
- On the RIGHT THIRD: a closed light-wood clinic door with a narrow frosted vertical glass strip and a simple round door handle; next to it a small blank cream sign plate with NOTHING written on it (completely empty), and a small round wall clock with a plain face and NO numbers, only two hands.
- Two soft round ceiling-light glows on the upper wall (warm yellow, very soft, even, not bright, no rays, no lens flare).
- Gentle warm-yellow, soft, even evening light overall; calm and safe mood; NOT dark, NOT scary, NOT clinical blue.
- Absolutely NO red cross, NO plus/cross symbol of any kind, NO hospital logo, NO medical equipment, NO beds, NO wheelchairs, NO exit sign, NO running-man sign, NO arrows.
- Absolutely NO text of any kind: no letters, no Chinese characters, no numbers (not even on the clock or door), no logos, no brand marks, no symbols that look like writing, no watermark, no signature.
- Keep the lower 35% of the picture calm and low-contrast (plain wall, baseboard, handrail): characters and a bench will stand in front of it.

After the image is generated:
1. The tool saves the PNG under ${CODEX_HOME:-$HOME/.codex}/generated_images/<session-id>/<call-id>.png. Other Codex sessions are generating images in parallel into sibling folders, so copy YOUR OWN image (match your session id / image call id; do not just take the newest file across all folders).
2. Copy it unmodified (no crop, no resize, no re-encode) to review/G5/a5/raw/a5_hosp_wall_v01.png inside the current workspace.
3. Print the copied file's pixel width and height (e.g. `sips -g pixelWidth -g pixelHeight -g hasAlpha review/G5/a5/raw/a5_hosp_wall_v01.png`) and the absolute source path you copied from.
Do not create, edit or delete any other files. Do not regenerate unless the first generation failed. Final answer: source path, destination path, pixel width x height, whether it has alpha.
"""
JOBS["a5_hosp_wall_v01"] = (HOSP, [S4, str(GEN / "bg-workshop-back_v02.png")])


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for jid, (prompt, refs) in JOBS.items():
        p = prompt.replace("review/G5/shared_art/raw/chr_lin_sit_v01.png", f"review/G5/a5/raw/{jid}.png")
        assert "chr_lin_sit" not in p
        (RAW / f"{jid}.prompt.txt").write_text(p)
        (RAW / f"{jid}.refs").write_text("\n".join(refs) + "\n")
        for r in refs:
            assert Path(r).exists(), r
        print(jid, len(p))


if __name__ == "__main__":
    main()
