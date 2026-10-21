"""G5 共用美術：產生 codex image_gen 提示（review/G5/shared_art/raw/<id>.prompt.txt＋<id>.refs）。

用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/make_prompts.py [id ...]
（不給 id＝全部重寫；已經有 <id>.png 的不影響）
風格段落沿用 G4 美術代理的提示（review/G4/art/raw/pose_xq_*_v05.prompt.txt），只換角色、姿勢與輸出路徑。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "review/G5/shared_art/raw"
S4 = ROOT / "review/G2a/S4.png"
XQ = ROOT / "assets/generated/chr-xiaoqing_master_v04.png"
XY = ROOT / "assets/generated/chr-xiaoyu_master_v04.png"
ALE = ROOT / "assets/generated/chr-ale_master_v02.png"
SQ = ROOT / "review/G2/stage_composite_v04.png"
GEN = ROOT / "assets/generated"

STYLE = """ART STYLE (match the FIRST attached reference image's "3D pop-up picture book made of thick matte cardstock" style and the approved character references, but apply ALL of these corrections):
- The figure is a single flat cut-out piece of thick matte cardstock with a subtle paper-fiber texture and crisp knife-cut outline.
- Exactly ONE fixed-width white paper-core border runs around the entire OUTER silhouette of the figure (same width everywhere, roughly 10-12 px at this canvas size). Directly inside that white border there is a thin dark warm-gray outline (2-3 px) separating the white border from the colored figure. Interior details (clothing seams, fingers, facial features) use only thin dark lines, never extra white borders.
- Completely FLAT, EVEN, SHADOWLESS lighting: no directional light, no rim light, no warm lantern glow, no orange cast, no glossy highlights, no baked-in shading gradients, no cast shadow, no drop shadow, no ground shadow, no floor, no reflection. Only flat color areas plus very light paper texture. (Stage lighting will be added later by software.)
- TRANSPARENT background (real alpha channel). Nothing else in the image: no ground, no props unless listed above, no scenery, no frame, no card behind the figure, no checkerboard pattern drawn in.
- Absolutely NO text of any kind: no letters, no Chinese characters, no numbers, no logos, no brand marks, no symbols that look like writing, no watermark, no signature.
- Child-friendly, warm, gentle storybook character design."""

FACE_STYLE = """Face style exactly like the approved characters: simple dark eyes with one small white highlight, small simple nose, small mouth, soft rosy cheeks, thin dark lines. Her/his face must be fully visible (three-quarter view, both eyes visible, the far eye slightly narrower), never a strict side profile."""

XQ_DESC = """- 9-year-old girl, shoulder-length dark brown bob; on one side of her hair a small ORIGAMI STAR hair clip whose paper folds/creases are clearly visible; mustard-yellow short-sleeve top; deep lake-teal (dark blue-green) overalls with rolled cuffs; a small spiral-bound notebook peeking out of the overalls' bib pocket, its cover completely BLANK (no marks, no letters); white socks; mustard-yellow sneakers. Same exact colors as the second reference image (do NOT lighten or darken them; the overalls stay the same deep teal as the reference).
- Proportions exactly like the master: 4.45 heads tall (head including hair = about 22.5% of the full height), slim natural 9-year-old picture-book child, NOT chibi, NOT big-headed."""

XY_DESC = """- 9-year-old boy, short slightly curly dark brown hair; round thin black-framed glasses; deep vermilion (dark orange-red) zip-up hoodie with white drawstrings and the hood resting behind his neck; khaki shorts with rolled cuffs; white crew socks; navy-blue canvas sneakers with white soles and white laces; a small dark navy backpack with shoulder straps over both shoulders. Same exact colors as the second reference image (do NOT lighten or darken them; the hoodie stays the same deep vermilion as the reference).
- On his LEFT wrist a generic kids' smartwatch: dark gray strap and a plain round dark-gray face with nothing drawn on it (no numbers, no letters, no logo); it must be visible.
- Proportions exactly like the master: 4.3 heads tall (head including hair = about 23% of the full height), slim natural 9-year-old picture-book child, NOT chibi, NOT big-headed."""

PINAN_DESC = """- Pinan, a 9-year-old girl (a classmate of the girl in the second reference); quiet, gentle and a little shy. Long straight BLACK hair tied into ONE low ponytail at the nape of the neck with a small woven-bamboo hair tie (tiny visible bamboo weave); straight blunt bangs across the forehead.
- Eggplant-purple (deep aubergine purple, NOT pink, NOT lilac) long-sleeve top; over it an off-white (warm cream) knitted sweater vest with a subtle knit texture; dark charcoal-gray long pants; white canvas shoes with white soles.
- Proportions exactly like the girl in the second reference: 4.4 heads tall (head including hair = about 22.5% of the full height), slim natural 9-year-old picture-book child, NOT chibi, NOT big-headed."""
PINAN_BAG = "- An olive-green canvas school backpack with wide shoulder straps over both shoulders (the bag partly visible behind her back), no marks, no text, no logo."

LIN_DESC = """- Ms. Lin, the children's homeroom teacher: a woman in her 30s, reliable and warm. Black medium-length hair gathered into a neat LOW BUN at the back of her head, a few soft strands at the temples.
- Deep wine-red (burgundy, #7B2638-like; NOT pink, NOT bright red) open-front knitted cardigan; plain off-white (cream) top underneath; dark charcoal-gray straight long pants; dark brown flat shoes.
- A plain dark-gray lanyard around her neck holding a small ID card whose face is completely BLANK plain cream (no text, no photo, no logo, no symbols).
- Natural adult proportions exactly like the man in the third reference: about 6.3 heads tall (head = about 16% of the full height), slim, natural, NOT chibi, NOT big-headed."""

CHEN_DESC = """- Grandpa Chen, the school gate guard: a man in his 60s, kind and steady, with a sturdy, solid build (broad shoulders, a little stocky; dignified, not comical).
- Short gray-white crew-cut hair, thick gray eyebrows, gentle smile lines at the corners of his eyes, clean-shaven.
- A light gray short-sleeve button-up shirt with two plain chest pockets and NOTHING on it: no badge, no patch, no emblem, no insignia, no name tag, no text. Over it a yellow-green (lime) crossing-guard safety vest with two matte off-white (cream) horizontal stripes; the stripes are plain flat cream paper, NOT glowing, NOT shiny. Dark charcoal-gray trousers; black shoes.
- It must NOT look like a real police or security-company uniform: no hat, no cap, no badge, no shoulder patches, no epaulettes, no duty belt, no radio, no baton, no whistle.
- Natural adult proportions exactly like the man in the third reference: about 6.2 heads tall (head = about 16% of the full height), NOT chibi, NOT big-headed."""

YE_DESC = """- Nurse Ye: a male nurse in his 30s, calm and gentle. Short black hair with a neat side part; gentle eyes; clean-shaven face.
- Sage-green (soft gray-green, #8EA48A-like) short-sleeve V-neck nurse scrub top; dark charcoal-gray long pants; white nurse shoes.
- Clipped on his chest a small cream ID badge showing ONLY a simple icon of an open hand holding a heart (the heart in soft warm orange-coral), no text; a pen clipped in his chest pocket; a simple wristwatch with a plain round face (no numbers).
- Absolutely NO red cross, NO plus/cross symbol of any kind, NO hospital logo, NO stethoscope.
- Natural adult proportions exactly like the man in the third reference: about 6.3 heads tall (head = about 16% of the full height), slim, NOT chibi, NOT big-headed."""


def char_prompt(out_id, who_line, refs_line, desc, pose, expr, extra="", size="PORTRAIT (vertical) orientation, request the tall 2:3 size (1024x1536)"):
    return f"""Use your built-in image generation tool (image_gen) to generate exactly ONE image: {who_line} for a children's paper-cut puppet theater. {size}, with a TRANSPARENT background (real alpha channel).

{refs_line}
{desc}

POSE (very important): {pose}
EXPRESSION: {expr}
{extra}
The whole figure from the top of the hair to the soles and the fingertips is visible with empty transparent margin all around (nothing cropped). {FACE_STYLE}

{STYLE}

After the image is generated:
1. The tool saves the PNG under ${{CODEX_HOME:-$HOME/.codex}}/generated_images/<session-id>/<call-id>.png. Other Codex sessions are generating images in parallel into sibling folders, so copy YOUR OWN image (match your session id / image call id; do not just take the newest file across all folders).
2. Copy it unmodified (no crop, no resize, no re-encode) to review/G5/shared_art/raw/{out_id}.png inside the current workspace.
3. Print the copied file's pixel width and height (e.g. `sips -g pixelWidth -g pixelHeight -g hasAlpha review/G5/shared_art/raw/{out_id}.png`) and the absolute source path you copied from.
Do not create, edit or delete any other files. Do not regenerate unless the first generation failed. Final answer: source path, destination path, pixel width x height, whether it has alpha.
"""


def set_prompt(out_id, what, body, size, transparent=True):
    bg = "with a TRANSPARENT background (real alpha channel)" if transparent else "fully opaque (no transparency)"
    return f"""Use your built-in image generation tool (image_gen) to generate exactly ONE image: {what} for a children's paper-cut puppet theater (2.5D pop-up stage). {size}, {bg}.

The FIRST attached reference is the art-style reference (thick matte cardstock pop-up picture book). The SECOND attached reference is an approved stage composite of the same show: match its scenery style exactly (flat cut cardstock pieces, soft daylight colors, light paper fiber texture, crisp knife-cut edges, thin dark warm-gray lines, warm cream paper-core edges).

{body}

GLOBAL RULES:
- Flat, even, SHADOWLESS lighting: no directional light, no baked cast shadows, no drop shadows, no glow, no glossy highlights, no vignette. Soft flat daylight colors. (Stage lighting is added later by software.)
- Absolutely NO text of any kind anywhere: no letters, no Chinese characters, no numbers, no signs with writing, no logos, no school emblem, no brand marks, no license plate characters, no watermark, no signature.
- No red cross symbols. No real company colors or logos (no delivery/logistics company look). No people unless stated.
- Calm, friendly, child-safe daytime scenery.

After the image is generated:
1. The tool saves the PNG under ${{CODEX_HOME:-$HOME/.codex}}/generated_images/<session-id>/<call-id>.png. Other Codex sessions are generating images in parallel into sibling folders, so copy YOUR OWN image (match your session id / image call id; do not just take the newest file across all folders).
2. Copy it unmodified (no crop, no resize, no re-encode) to review/G5/shared_art/raw/{out_id}.png inside the current workspace.
3. Print the copied file's pixel width and height (e.g. `sips -g pixelWidth -g pixelHeight -g hasAlpha review/G5/shared_art/raw/{out_id}.png`) and the absolute source path you copied from.
Do not create, edit or delete any other files. Do not regenerate unless the first generation failed. Final answer: source path, destination path, pixel width x height, whether it has alpha.
"""


KID_REF = "TWO reference images are attached. The FIRST is only the art-style reference (thick matte cardstock pop-up picture book). The SECOND is the FINAL approved character master. Draw THE SAME CHILD - identical face, identical design and identical colors - only the pose and expression change:"
NEW_KID_REF = "THREE reference images are attached. The FIRST is only the art-style reference (thick matte cardstock pop-up picture book). The SECOND and THIRD are approved main characters of the same show (two 9-year-old children). Draw a NEW child in EXACTLY the same rendering style, line weight, face style, flat colors, white paper-core border and proportions as those approved children:"
NEW_ADULT_REF = "THREE reference images are attached. The FIRST is only the art-style reference (thick matte cardstock pop-up picture book). The SECOND is an approved 9-year-old child of the same show and the THIRD is the approved adult man (Uncle Ale) of the same show. Draw a NEW adult character in EXACTLY the same rendering style, line weight, face style, flat colors, white paper-core border and natural adult proportions as Uncle Ale:"
SAME_NEW_REF = "THREE reference images are attached. The FIRST is only the art-style reference. The SECOND is the FINAL approved standing master of THIS character. The THIRD is another approved character of the same show (for scale and style). Draw THE SAME CHARACTER as the second reference - identical face, hair, clothes and colors - only the pose and expression change:"

CROSS_POSE = "the \"don't touch\" gesture from a children's safety chant. The child faces the viewer (front view, turned only very slightly toward the viewer's left), standing straight with both soles flat on the floor, feet slightly apart. Both forearms are crossed in front of the chest forming one clear big X (the wrists cross at the middle of the chest), both hands open with fingers together, elbows out to the sides. The X is in front of the chest below the chin: the hands do NOT cover the face, the mouth or the neck."
CROSS_EXPR = "friendly but firm and confident: eyebrows slightly lowered and straight, eyes open looking at the viewer, mouth closed in a small firm line. Not angry, not scared."
PALM_POSE = "calmly and firmly saying \"No, thank you.\" The whole body is in a three-quarter view toward the VIEWER'S LEFT, standing upright (not leaning forward), both soles flat on the floor. The arm on the LEFT side of the picture is extended forward toward the left at CHEST height (elbow slightly bent, the hand stays below the child's own chin height), with the hand OPEN and the PALM FACING OUTWARD toward the left, fingers together pointing up: a calm \"no\" sign. NOT pointing, no index finger pointing. The other arm hangs relaxed at the side. The head faces left, eyes looking left at an adult's chest height."
PALM_EXPR = "calm, steady and brave: eyebrows level and slightly lowered, eyes open, mouth slightly open as if calmly saying \"no\". Not angry, not scared, not shouting."
FORE_POSE = "\"look for a grown-up\". The whole body is in a three-quarter view toward the VIEWER'S RIGHT, standing, both soles flat on the floor. The hand of the arm on the RIGHT side of the picture is held flat against the forehead just above the eyebrows, PALM FACING DOWN, fingers together (like shading the eyes to look far away); the hand does not cover the eyes. The other arm hangs relaxed at the side. The head faces right, eyes looking into the distance to the right."
FORE_EXPR = "attentive and alert, calmly searching: eyebrows natural, eyes open looking far to the right, mouth closed."
WALK_POSE = "walking briskly toward the VIEWER'S RIGHT, in a three-quarter side view (body turned toward the right; the face still in three-quarter view with both eyes visible, NOT a strict profile). Mid-stride: the front foot (on the right side of the picture) steps forward with the heel touching down, the back foot pushes off on its toes; the arms swing naturally and gently (opposite arm to leg), hands relaxed. Upright, purposeful posture."
WALK_EXPR = "calm and purposeful, small closed mouth."

PROMPTS = {}
REFS = {}


def kid(out_id, desc, ref_img, pose, expr, extra=""):
    PROMPTS[out_id] = char_prompt(out_id, "a full-body POSE sheet of an existing character", KID_REF, desc, pose, expr, extra)
    REFS[out_id] = [S4, ref_img]


kid("pose_xq_cross_v06", XQ_DESC, XQ, CROSS_POSE, CROSS_EXPR)
kid("pose_xq_palmno_v06", XQ_DESC, XQ, PALM_POSE, PALM_EXPR)
kid("pose_xq_forehead_v06", XQ_DESC, XQ, FORE_POSE, FORE_EXPR)
kid("pose_xq_walk_v06", XQ_DESC, XQ, WALK_POSE, WALK_EXPR)
kid("pose_xy_cross_v06", XY_DESC, XY, CROSS_POSE, CROSS_EXPR)
kid("pose_xy_palmno_v06", XY_DESC, XY, PALM_POSE, PALM_EXPR)
kid("pose_xy_forehead_v06", XY_DESC, XY, FORE_POSE, FORE_EXPR)
kid("pose_xy_walk_v06", XY_DESC, XY, WALK_POSE, WALK_EXPR)
kid("pose_xy_watch_v06", XY_DESC, XY,
    "making an emergency phone call on his kids' smartwatch. The whole body is in a three-quarter view toward the VIEWER'S LEFT, standing, both soles flat on the floor. His LEFT forearm (the one with the smartwatch) is raised horizontally in front of his chest with the watch face turned up toward his own face; the index finger of his RIGHT hand presses the watch face, the other fingers of the right hand loosely curled. His head is tilted down a little, looking at the watch, face still clearly visible (both eyes visible behind the glasses). The round watch screen shows ONLY one small simple white telephone-handset icon on dark gray: no numbers, no letters, no other symbols. The watch is generic (round face, dark gray strap), not any real product.",
    "focused, serious and brave: eyebrows slightly lowered, mouth closed. Not scared, not crying.")

# 新角色站姿（母版）
PROMPTS["chr_pinan_stand_v01"] = char_prompt(
    "chr_pinan_stand_v01", "a full-body standing MASTER of a new supporting character", NEW_KID_REF, PINAN_DESC + "\n" + PINAN_BAG,
    "standing; the whole body in a three-quarter view toward the VIEWER'S LEFT, both soles flat on the floor, feet slightly apart; arms relaxed down at her sides, hands relaxed with fingers slightly curled. Her head turns toward the left, eyes looking left at eye level.",
    "calm, gentle, a little shy: a small closed-mouth smile, eyebrows natural.")
REFS["chr_pinan_stand_v01"] = [S4, XQ, XY]
for cid, desc in (("lin", LIN_DESC), ("chen", CHEN_DESC), ("ye", YE_DESC)):
    oid = f"chr_{cid}_stand_v01"
    PROMPTS[oid] = char_prompt(
        oid, "a full-body standing MASTER of a new supporting adult character", NEW_ADULT_REF, desc,
        "standing relaxed and upright; the whole body in a three-quarter view toward the VIEWER'S LEFT, both soles flat on the floor, feet slightly apart; arms relaxed at the sides, hands gently relaxed. The head turns toward the left, eyes looking left and slightly downward (as if looking at children).",
        "warm, kind, gentle closed-mouth smile.")
    REFS[oid] = [S4, XQ, ALE]

# 邀請者：只有手＋盒子（左側入畫）＋盒子單獨特寫
PROMPTS["prop_inviter_v01"] = f"""Use your built-in image generation tool (image_gen) to generate exactly ONE image for a children's paper-cut puppet theater. LANDSCAPE orientation, request the wide 3:2 size (1536x1024), with a TRANSPARENT background (real alpha channel).

TWO reference images are attached: the FIRST is the art-style reference (thick matte cardstock pop-up picture book); the SECOND is the approved adult character of the same show (match his hand drawing style, skin rendering, line weight and white paper-core border).

The image contains exactly TWO separate cut-out pieces with plenty of empty transparent space between them:

PIECE A (left 60% of the canvas): an adult's forearm and hand reaching in from the LEFT EDGE of the canvas - the sleeve is cut off by the left edge of the picture on purpose, as if the arm comes out from behind a pillar off-screen. Plain charcoal-gray long sleeve with a simple cuff. The hand is relaxed and casual, palm facing UP, with a small box resting on the open palm, like casually handing something over to someone. Neutral medium skin tone. No jewelry, no watch, no rings, no tattoos, no nail polish, no scars, no hair on the hand. An ordinary friendly hand: NOT claw-like, NOT dark, NOT menacing. No face, no body, no shadow.

THE SMALL BOX: a plain small rectangular box about the size of a palm (a simple cuboid; NOT shaped like any real product - not like an e-cigarette, vape pen, lighter, phone, cigarette pack or candy) completely covered with layer upon layer of gaudy, tacky stickers: shiny-looking stickers in clashing hot pink, lime green, lemon yellow and turquoise with abstract shapes only (stars, dots, zigzags, swirls), stickers overlapping each other, several sticker corners peeling up; from under one peeled corner a short little gray paper thread pokes out. The shine is only a few fixed tiny white sparkle marks. NO text, NO letters, NO numbers, NO logos, NO brand, NO cartoon characters, NO faces, NO smoke, NO vapor, NO scent lines.

PIECE B (right 40% of the canvas): the SAME sticker-covered box alone, drawn about twice as large, at a slight three-quarter angle showing its front and top faces, with the same peeled sticker corners and the little gray thread.

ART STYLE: each piece is a flat cut-out of thick matte cardstock with subtle paper-fiber texture and a crisp knife-cut outline; exactly ONE fixed-width white paper-core border (about 10-12 px) around each piece's outer silhouette (except where piece A is cut by the canvas edge), with a thin dark warm-gray line inside it. Completely FLAT, EVEN, SHADOWLESS lighting: no directional light, no glow, no cast or drop shadows. TRANSPARENT background, nothing else in the image. Absolutely NO text of any kind, no watermark, no signature.

After the image is generated:
1. The tool saves the PNG under ${{CODEX_HOME:-$HOME/.codex}}/generated_images/<session-id>/<call-id>.png. Other Codex sessions are generating images in parallel into sibling folders, so copy YOUR OWN image (match your session id / image call id; do not just take the newest file across all folders).
2. Copy it unmodified (no crop, no resize, no re-encode) to review/G5/shared_art/raw/prop_inviter_v01.png inside the current workspace.
3. Print the copied file's pixel width and height (e.g. `sips -g pixelWidth -g pixelHeight -g hasAlpha review/G5/shared_art/raw/prop_inviter_v01.png`) and the absolute source path you copied from.
Do not create, edit or delete any other files. Do not regenerate unless the first generation failed. Final answer: source path, destination path, pixel width x height, whether it has alpha.
"""
REFS["prop_inviter_v01"] = [S4, ALE]


def phase2():
    """第二階段：以第一階段採用的新角色母版為參考。"""
    pin = GEN / "chr-pinan_master_v01.png"
    lin = GEN / "chr-lin_master_v01.png"
    ye = GEN / "chr-ye_master_v01.png"
    PROMPTS["chr_pinan_sit_v01"] = char_prompt(
        "chr_pinan_sit_v01", "a full-body SITTING pose of an existing character", SAME_NEW_REF, PINAN_DESC + "\n- No backpack in this pose.",
        "P-PA1: sitting on a bench that is NOT drawn (an invisible seat - draw NO bench, NO chair, NO stool, NO seat of any kind; the bench is a separate stage piece added later). Three-quarter view toward the VIEWER'S LEFT. Her thighs are horizontal (as if on a seat), knees bent, lower legs hanging straight down, feet together, soles about to touch the floor. On her lap she holds a small round woven-bamboo lantern (a little bamboo-strip frame lantern, pale cream lantern paper on part of it, about the size of her head) with both hands, tying a short thin string on its top. She looks down at the lantern. Draw her at the same scale as the standing reference (same head size).",
        "content and gentle: a small closed-mouth smile, eyes looking down at the lantern.")
    REFS["chr_pinan_sit_v01"] = [S4, pin, XQ]
    PROMPTS["chr_pinan_walk_v01"] = char_prompt(
        "chr_pinan_walk_v01", "a full-body WALKING pose of an existing character", SAME_NEW_REF, PINAN_DESC + "\n" + PINAN_BAG,
        "walking quickly toward the VIEWER'S RIGHT in a three-quarter side view (face still in three-quarter view, both eyes visible, not a strict profile). Mid-stride, front foot (right side of the picture) stepping forward, back foot on its toes. BOTH hands tightly hold the two backpack shoulder straps in front of her shoulders (elbows bent). Her head is lowered a little, eyes looking down and away, shoulders slightly hunched - shy and avoiding eye contact, but not crying.",
        "worried and shy: eyebrows slightly raised in the middle, mouth closed in a small worried line, eyes lowered.")
    REFS["chr_pinan_walk_v01"] = [S4, pin, XQ]
    PROMPTS["chr_lin_crouch_v01"] = char_prompt(
        "chr_lin_crouch_v01", "a full-body CROUCHING pose of an existing character", SAME_NEW_REF, LIN_DESC,
        "P-LIN1: she squats down low next to a child (the child is NOT drawn) so that her face is at a 9-year-old child's chest height. Three-quarter view toward the VIEWER'S LEFT. Both knees bent deeply, one knee lower than the other, heels slightly raised, balanced and stable. Her upper body leans slightly forward toward the left; one hand rests lightly on her raised knee, the other hand hangs relaxed. She is speaking calmly toward a point just in front of her face on the left (a smartwatch held up by the child, not drawn). Draw her at the same scale as the standing reference (same head size).",
        "calm, focused and reassuring, mouth slightly open as if speaking clearly.")
    REFS["chr_lin_crouch_v01"] = [S4, lin, XY]
    PROMPTS["chr_lin_sit_v01"] = char_prompt(
        "chr_lin_sit_v01", "a full-body SITTING pose of an existing character", SAME_NEW_REF, LIN_DESC,
        "P-LIN2: sitting upright on a bench that is NOT drawn (an invisible seat - draw NO bench, NO chair, NO seat of any kind; the bench is a separate stage piece added later). Three-quarter view toward the VIEWER'S LEFT. Thighs horizontal, knees bent at a right angle, lower legs vertical, both soles flat on the floor, knees together; both hands resting gently on her knees. Draw her at the same scale as the standing reference (same head size).",
        "calm and gentle, a small soft closed-mouth smile.")
    REFS["chr_lin_sit_v01"] = [S4, lin, XQ]
    PROMPTS["chr_ye_crouch_v01"] = char_prompt(
        "chr_ye_crouch_v01", "a full-body CROUCHING pose of an existing character", SAME_NEW_REF, YE_DESC,
        "P-YE1: he crouches down to be at eye level with a seated person or a child (not drawn). Three-quarter view toward the VIEWER'S LEFT. One knee down near the floor and the other knee raised (a low, stable kneel-squat), back upright, head level. One forearm rests on the raised knee; the other hand is held out low and open with the PALM FACING UP (a gentle \"I'm here with you\" gesture), fingers relaxed. He looks left at eye level. Draw him at the same scale as the standing reference (same head size).",
        "warm, calm and reassuring, a soft gentle smile, mouth closed.")
    REFS["chr_ye_crouch_v01"] = [S4, ye, XQ]


def sets():
    PROMPTS["set_gate_back_v01"] = set_prompt(
        "set_gate_back_v01", "the far BACKDROP layer of a small-town Taiwanese elementary school gate scene",
        """CONTENT (one wide backdrop sheet that fills the whole canvas, no transparency):
- Upper part: soft pale blue sky with a few flat cut-paper clouds (like the second reference), pale near the horizon.
- Low distant green mountains as two flat layered cardstock ridges along the horizon (muted, desaturated).
- RIGHT 55%: a friendly, light-colored 3-story Taiwanese elementary school building seen from the front, far away: cream / pale yellow walls with long open corridors (balconies with simple railings) on each floor, rows of windows, a few potted plants on the corridor railings, a flat roof; NO emblem, NO clock with numbers, NO signboard, NO flags with symbols.
- LEFT 45%: a row of low town houses across the street: 2-3 story shophouses with an arcade (騎樓) at street level, red-brick and cream walls, simple windows, a few street trees in front; no signboards, no shop signs, no text.
- The bottom 15% of the image is a plain flat light gray-beige sidewalk/ground band (no details) - the stage floor is added separately.
- Overall light, airy daytime colors; keep the area behind the characters (the lower middle and right) LIGHT so that dark-clothed characters stand out.""",
        "LANDSCAPE orientation, request the wide 3:2 size (1536x1024)", transparent=False)
    REFS["set_gate_back_v01"] = [S4, SQ]
    PROMPTS["set_gate_mid_v01"] = set_prompt(
        "set_gate_mid_v01", "a KIT SHEET of separate standing set pieces (middle layer) for a school gate scene",
        """CONTENT: separate flat cardstock cut-out set pieces arranged on ONE sheet with clear empty transparent space between every piece (they will be cut apart and placed individually). Front (elevation) view, like stage flats. Pieces:
1. (left) A short section of the school's low perimeter wall: cream plaster with a light terracotta-tile coping on top and a low green hedge strip in front at its base; plain, no text, about 3 times wider than tall.
2. (center) The SCHOOL GATE: two sturdy square gate pillars in cream/light-gray washed-stone texture with simple caps, and between them an open gateway; a folded expandable (accordion) metal sliding gate in soft gray pushed open against the RIGHT pillar. The pillars carry NO plaque, NO emblem, NO lettering (plain surfaces only). The opening between the pillars is EMPTY TRANSPARENT (see-through).
3. (right) A small GUARD HOUSE booth: light gray-green walls, a flat roof with a small overhang, one door, and one big front window whose glass area is EMPTY TRANSPARENT (a see-through hole with a cream window frame and a simple sill) so a person can be shown inside behind it later. No sign, no text, no emblem on it.
4. (bottom row, small) two potted plants in simple terracotta pots and one low shrub.
Each piece has a thin warm kraft-brown cardstock thickness edge and a fine dark outline; the outer silhouettes are crisp knife-cut.""",
        "LANDSCAPE orientation, request the wide 3:2 size (1536x1024)")
    REFS["set_gate_mid_v01"] = [S4, SQ]
    PROMPTS["set_gate_fore_v01"] = set_prompt(
        "set_gate_fore_v01", "a KIT SHEET of separate FOREGROUND props and the FLOOR for a school-gate pick-up zone",
        """CONTENT: separate flat cardstock cut-out pieces on ONE sheet with clear empty transparent space between every piece. Pieces:
1. (top, full width) A long horizontal FLOOR STRIP seen slightly from above (like a stage floor flat), about 6 times wider than tall: on the left half a light gray asphalt road with white zebra-crossing stripes running across it; then a curb and a light beige sidewalk; on the right half the light concrete ground inside the school gate with one painted soft yellow straight line (the pick-up waiting line) parallel to the gate. Flat colors, light paper texture, no text, no arrows, no numbers.
2. A parked small scooter in plain cream and soft teal paper, side view facing right, NO brand, NO logo, NO license plate characters (plate area blank or none).
3. A slim street-lamp post (dark gray-green) with a simple lamp head, unlit.
4. A low planter box with leafy green shrubs and a few small cream flowers (like the planters in the second reference).
5. Two orange traffic cones with matte cream bands (no reflective glow).
Each piece has a thin warm kraft-brown cardstock thickness edge and fine dark outline.""",
        "LANDSCAPE orientation, request the wide 3:2 size (1536x1024)")
    REFS["set_gate_fore_v01"] = [S4, SQ]
    PROMPTS["prop_truck_v01"] = set_prompt(
        "prop_truck_v01", "a single SIDE-VIEW cut-out of a small pickup truck (prop)",
        """CONTENT: ONE small Taiwanese-style mini pickup truck (a small cab-over light truck with a cargo bed), exact side view, the FRONT of the truck facing the VIEWER'S RIGHT. Body color: soft pale cream / lantern-paper beige (NOT white, NOT any delivery-company color), with warm gray bumpers and dark gray tires with cream hubcaps. The cab has a side window and a small REAR window (the window at the back of the cab). The cargo bed is covered with a muted olive-khaki canvas tarp tied down with a few cords. Near the rear window of the cab, ONE small pointed tip of a woven bamboo-strip frame pokes out from under the tarp - it looks like the tip of a cat's ear made of bamboo strips (just a small triangular bamboo-lattice corner, not obvious). Generic friendly rounded design, NOT any real brand or model: NO logo, NO emblem, NO text, NO numbers, NO license plate characters (no plate), NO stripes or company livery. Headlights and tail lights unlit, flat. Driver's door closed. Nobody inside, no driver.
The whole truck is visible with transparent margin all around. One flat cardstock piece with a crisp knife-cut outline, exactly ONE white paper-core border around the outer silhouette, a thin dark warm-gray line inside it, and a fine kraft-brown cardstock thickness edge.""",
        "LANDSCAPE orientation, request the wide 3:2 size (1536x1024)")
    REFS["prop_truck_v01"] = [S4, SQ]
    PROMPTS["prop_bench_v01"] = set_prompt(
        "prop_bench_v01", "a single cut-out of a simple wooden park bench (prop)",
        """CONTENT: ONE simple slatted wooden bench, front view (seen straight from the front, very slightly from above so the top of the seat shows as a thin strip): warm honey-brown wooden slats for the seat and the backrest, simple dark gray-green metal side frames/legs, no armrests in the middle. Long enough for three people to sit side by side (about 4 times wider than its seat height). Plain, no plaque, no text, no logo, no carved marks. The whole bench visible with transparent margin all around; one flat cardstock piece with a crisp knife-cut outline, exactly ONE white paper-core border around the outer silhouette, a thin dark line inside it, and a fine kraft-brown cardstock thickness edge.""",
        "LANDSCAPE orientation, request the wide 3:2 size (1536x1024)")
    REFS["prop_bench_v01"] = [S4, SQ]


def main():
    if "--phase2" in sys.argv:
        phase2()
    if "--sets" in sys.argv:
        sets()
    ids = [a for a in sys.argv[1:] if not a.startswith("--")] or list(PROMPTS)
    for i in ids:
        (RAW / f"{i}.prompt.txt").write_text(PROMPTS[i])
        (RAW / f"{i}.refs").write_text("\n".join(str(p) for p in REFS[i]) + "\n")
        print("wrote", i)


if __name__ == "__main__":
    main()
