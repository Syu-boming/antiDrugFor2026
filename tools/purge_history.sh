#!/bin/zsh
# 清掉 GitHub 歷史裡的開發試音（許老師 2026-10-22 決定；由許老師自己執行，Claude 不執行）。
# 用法：在專案根目錄跑 zsh tools/purge_history.sh
# 做法：在暫存的 mirror 複本改寫 main 的歷史，移除 review/G3/samples、audio/_archive_edge、audio/_test、audio/vo/*_v01–v03.wav；
# 確認改寫後最新版本的內容和本機 main 完全相同、歷史裡不再有這些檔，才強制推送；最後把本機 main 指到改寫後的版本（檔案不動）。
set -euo pipefail
ROOT=${0:A:h:h}
cd "$ROOT"
[[ -z "$(git status --porcelain)" ]] || { echo "[purge] 還有未提交的改動，請先請 Claude commit"; exit 1 }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone -q --mirror "$ROOT" "$TMP/m.git"
cd "$TMP/m.git"
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --index-filter \
  'git rm -r -q --cached --ignore-unmatch review/G3/samples audio/_archive_edge audio/_test "audio/vo/*_v01.wav" "audio/vo/*_v02.wav" "audio/vo/*_v03.wav"' -- main

[[ "$(git -C "$ROOT" rev-parse 'main^{tree}')" == "$(git rev-parse 'main^{tree}')" ]] || { echo "[purge] 改寫後最新版本的內容和本機不同，停止（沒有推送）"; exit 1 }
LEFT=$(git log main --format= --name-only | grep -cE '^(review/G3/samples/|audio/_archive_edge/|audio/_test/|audio/vo/.*_v0[123]\.wav$)' || true)
[[ "$LEFT" == 0 ]] || { echo "[purge] 歷史裡還有 $LEFT 筆試音，停止（沒有推送）"; exit 1 }
NEW=$(git rev-parse main)
echo "[purge] 改寫完成，最新版本內容不變；強制推送 main → ${NEW:0:7}"
git push --force https://github.com/Syu-boming/antiDrugFor2026.git main

cd "$ROOT"
git fetch -q origin
[[ "$(git rev-parse origin/main)" == "$NEW" ]] || { echo "[purge] GitHub 上的 main 不是改寫後的版本，請把這段訊息給 Claude"; exit 1 }
git reset -q --soft "$NEW"
echo "[purge] 完成：GitHub main 與本機 main 都是 ${NEW:0:7}（工作中的檔案沒有變動）"
