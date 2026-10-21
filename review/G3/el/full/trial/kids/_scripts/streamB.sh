#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY=tools/.venv/bin/python
$PY $S/trial_kids.py zz_lulu_v3 $S/cands/zz_lulu_v3.json 70 2 a0_c003_01 a0_c002_02 a3_c004_02
$PY $S/trial_kids.py zz_chloe_v3 $S/cands/zz_chloe_v3.json 70 2 a0_c003_01 a0_c002_02 a3_c004_02
$PY $S/trial_kids.py ale_juin_v2 $S/cands/ale_juin_v2.json 70 2 a2_c002_01 a6_c009_03 a4_c008_01
$PY $S/trial_kids.py ale_kuoyu_v2 $S/cands/ale_kuoyu_v2.json 70 2 a2_c002_01 a6_c009_03 a4_c008_01
$PY $S/trial_kids.py ale_xuming_v2 $S/cands/ale_xuming_v2.json 70 2 a2_c002_01 a6_c009_03 a4_c008_01
$PY $S/trial_kids.py ale_kuoyu_v3 $S/cands/ale_kuoyu_v3.json 70 2 a2_c002_01 a6_c009_03 a4_c008_01
echo STREAM_B_DONE
