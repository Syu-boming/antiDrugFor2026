#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY=tools/.venv/bin/python
$PY $S/trial_kids.py xq_tiffy_v3 $S/cands/xq_tiffy_v3.json 70 2 a1_c004_02 a1_c003_02 a5_c005_02
$PY $S/trial_kids.py xy_vivian_v3 $S/cands/xy_vivian_v3.json 70 2 a0_c004_01 a5_c005_03 a5_c006_02
$PY $S/trial_kids.py xy_yui_v3_m2 $S/cands/xy_yui_v3_m2.json 70 2 a0_c004_01 a5_c005_03 a5_c006_02
$PY $S/trial_kids.py pa_yui_v3_m3 $S/cands/pa_yui_v3_m3.json 70 2 a1_c004_06 a6_c002_02 a7_c003_01
$PY $S/trial_kids.py pa_vivian_v3_m1 $S/cands/pa_vivian_v3_m1.json 70 2 a1_c004_06 a6_c002_02 a7_c003_01
echo STREAM_A_DONE
