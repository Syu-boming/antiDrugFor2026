#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py xq_lulu_v3 $S/cands/xq_lulu_v3.json 30 2 a1_c004_02 a1_c008_02
$=PY $S/trial_kids.py xq_zmax_v3 $S/cands/xq_zmax_v3.json 30 2 a1_c004_02 a1_c008_02
$=PY $S/trial_kids.py xy_vivian_v3_s1_zz $S/cands/xy_vivian_v3_s1_zz.json 30 2 a0_c004_01 a3_c001_01
echo STREAM_H_DONE
