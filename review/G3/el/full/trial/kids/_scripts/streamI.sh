#!/bin/zsh
cd "/Users/boming/Documents/AI tool/反毒小劇場"
S=/private/tmp/claude-501/-Users-boming-Documents-AI-tool------/05ec9c64-b2bb-4668-8277-069722cf5dfb/scratchpad
PY="tools/.venv/bin/python -u"
$=PY $S/trial_kids.py xq_tiffy_v3_dz $S/cands/xq_tiffy_v3_dz.json 15 2 a1_c004_02
$=PY $S/trial_kids.py xq_tiffy_v2 $S/cands/xq_tiffy_v2.json 15 2 a1_c004_02
echo STREAM_I_DONE
