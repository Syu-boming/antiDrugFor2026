#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py xq_tiffy_v3_zi $S/cands/xq_tiffy_v3_zi.json 15 2 a1_c004_02
$=PY $S/trial_kids.py xq_tiffy_v3_comma $S/cands/xq_tiffy_v3_comma.json 15 2 a1_c004_02
$=PY $S/trial_kids.py zz_chloe_v3_p2_long $S/cands/zz_chloe_v3_p2_long.json 50 2 a0_c002_02 a6_c007_01 a1_c001_04
echo STREAM_F_DONE
