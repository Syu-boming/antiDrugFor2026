#!/bin/zsh
# 把 app/dist（舞台、控制台、按鍵測試）與 teacher/（網頁、圖、PDF）發布到 gh-pages 分支（GitHub Pages）。
# 用法：先 cd app && npm run build，再在專案根目錄跑 zsh tools/deploy_pages.sh [--no-push]
# 推送後會等到線上的 version.txt 換成這次的網站指紋才結束（Pages 偶爾卡在 queued：10 分鐘後重新要求建置一次，30 分鐘仍沒換就 exit 1）。
# 不切換工作目錄、不動 main：用暫存索引直接寫 gh-pages 的 commit。
set -euo pipefail
ROOT=${0:A:h:h}
cd "$ROOT"
PUSH=1; [[ "${1:-}" == "--no-push" ]] && PUSH=0

[[ -f app/dist/index.html && -f app/dist/data/manifest.js ]] || { echo "[pages] 找不到 app/dist，先 npm run build"; exit 1 }

TMP=$(mktemp -d)
SITE=$TMP/site
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$SITE/show" "$SITE/teacher"
cp tools/pages/index.html "$SITE/index.html"
cp -R app/dist/. "$SITE/show/"
cp -R teacher/html teacher/img teacher/pdf teacher/fonts "$SITE/teacher/"
touch "$SITE/.nojekyll"
find "$SITE" -name .DS_Store -delete
SITEFP=$(cd "$SITE" && find . -type f -print0 | sort -z | xargs -0 shasum | shasum | cut -c1-12)
echo "$SITEFP" > "$SITE/version.txt"

# GitHub Pages：單檔 < 100 MB、整站 < 1 GB
BIG=$(find "$SITE" -type f -size +95M | wc -l | tr -d ' ')
SIZE_MB=$(du -sm "$SITE" | cut -f1)
[[ "$BIG" == 0 ]] || { echo "[pages] 有檔案超過 95 MB"; exit 1 }
(( SIZE_MB < 950 )) || { echo "[pages] 整站 ${SIZE_MB} MB 超過上限"; exit 1 }

# 金鑰檢查：.env 的值與 sk_／sk- 樣式都不能出現在網站檔案裡（只印命中數）
/opt/anaconda3/bin/python3 -I - "$ROOT/.env" "$SITE" <<'EOF'
import os, re, sys
env, site = sys.argv[1], sys.argv[2]
vals = []
if os.path.exists(env):
    for line in open(env, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            v = line.split('=', 1)[1].strip().strip('"').strip("'")
            if len(v) >= 12: vals.append(v.encode())
pat = re.compile(rb'sk[_-][A-Za-z0-9_\-]{20,}')
hits = 0
for d, _, fs in os.walk(site):
    for f in fs:
        b = open(os.path.join(d, f), 'rb').read()
        if any(v in b for v in vals) or pat.search(b): hits += 1; print('[pages] 金鑰命中：', os.path.relpath(os.path.join(d, f), site))
if hits: sys.exit(1)
print('[pages] 金鑰檢查 0 命中')
EOF

IDX=$TMP/index
(cd "$SITE" && GIT_DIR="$ROOT/.git" GIT_WORK_TREE="$SITE" GIT_INDEX_FILE="$IDX" git add -A .)
TREE=$(GIT_INDEX_FILE="$IDX" git write-tree)
PARENT=$(git rev-parse -q --verify refs/heads/gh-pages || true)
if [[ -n "$PARENT" && "$(git rev-parse "$PARENT^{tree}")" == "$TREE" ]]; then
  echo "[pages] 內容和上次相同，不另建 commit"
else
  MAIN=$(git rev-parse --short HEAD)
  DIST=$(shasum app/dist/data/manifest.js app/dist/app.js | shasum | cut -c1-10)
  MSG="Pages：發布 main ${MAIN}（dist 指紋 ${DIST}）的建置（舞台、控制台、教師資料）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013HpBRZnxMJ6dMY1xBFwjTq"
  PARENT_ARGS=(); [[ -n "$PARENT" ]] && PARENT_ARGS=(-p "$PARENT")
  COMMIT=$(git -c user.name=許博明 -c user.email=ulycessjp@gmail.com commit-tree "$TREE" "${PARENT_ARGS[@]}" -m "$MSG")
  git update-ref refs/heads/gh-pages "$COMMIT"
  echo "[pages] gh-pages → ${COMMIT:0:7}（${SIZE_MB} MB）"
fi
if (( PUSH )); then
  git push origin gh-pages
  URL="https://syu-boming.github.io/antiDrugFor2026/version.txt"
  for i in {1..60}; do
    GOT=$(curl -s "$URL?v=$RANDOM$i" | tr -d '[:space:]')
    [[ "$GOT" == "$SITEFP" ]] && break
    (( i == 20 )) && gh api -X POST repos/Syu-boming/antiDrugFor2026/pages/builds >/dev/null && echo "[pages] 10 分鐘還沒生效，重新要求建置一次"
    sleep 30
  done
  [[ "$GOT" == "$SITEFP" ]] || { echo "[pages] 30 分鐘後線上版仍不是這次的內容（線上 ${GOT:-無}、這次 $SITEFP）；查 gh api repos/Syu-boming/antiDrugFor2026/pages/builds/latest"; exit 1 }
  echo "[pages] 線上版已生效（網站指紋 $SITEFP）"
fi
echo "[pages] 完成"
