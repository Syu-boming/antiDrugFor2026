#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py ale_kuoyu_v3_zhe $S/cands/ale_kuoyu_v3_zhe.json 60 2 a6_c009_03 a0_c002_03 a0_c003_03
$=PY $S/trial_kids.py zz_chloe_v3_p2_zhe $S/cands/zz_chloe_v3_p2_zhe.json 40 2 a0_c002_02 a6_c007_01
echo STREAM_D_DONE
