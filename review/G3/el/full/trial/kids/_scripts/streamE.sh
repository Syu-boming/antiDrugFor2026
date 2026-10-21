#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py xq_tiffy_v3_s1 $S/cands/xq_tiffy_v3_s1.json 30 2 a1_c004_02
$=PY $S/trial_kids.py zz_chloe_v3_p2_jue $S/cands/zz_chloe_v3_p2_jue.json 40 2 a3_c004_02 a7_c002_01
echo STREAM_E_DONE
