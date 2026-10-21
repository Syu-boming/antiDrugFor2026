#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py xq_tiffy_v3_hg $S/cands/xq_tiffy_v3_hg.json 20 2 a1_c004_02
$=PY $S/trial_kids.py xy_vivian_v3_s1_hg $S/cands/xy_vivian_v3_s1_hg.json 20 2 a0_c004_01
$=PY $S/trial_kids.py zz_chloe_v3_p2_zhe2 $S/cands/zz_chloe_v3_p2_zhe2.json 40 2 a0_c002_02 a6_c007_01
echo STREAM_G_DONE
