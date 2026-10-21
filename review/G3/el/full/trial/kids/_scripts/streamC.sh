#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py zz_chloe_v3_p2 $S/cands/zz_chloe_v3_p2.json 5 2 a0_c003_01 a0_c002_02 a3_c004_02
$=PY $S/trial_kids.py xq_tiffy_v3_yan $S/cands/xq_tiffy_v3_yan.json 30 2 a1_c004_02
$=PY $S/trial_kids.py xy_yui_v3_m2_s1 $S/cands/xy_yui_v3_m2_s1.json 50 2 a0_c004_01 a5_c005_03
$=PY $S/trial_kids.py xy_vivian_v3_s1 $S/cands/xy_vivian_v3_s1.json 50 2 a0_c004_01 a5_c005_03
$=PY $S/trial_kids.py zz_chloe_v3_p2_s1 $S/cands/zz_chloe_v3_p2_s1.json 50 2 a3_c004_02 a0_c002_02
echo STREAM_C_DONE
