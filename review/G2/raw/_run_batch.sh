#!/bin/zsh
# 用法：_run_batch.sh <id> [<id> ...]；每個 id 讀 <id>.prompt.txt，背景平行呼叫 codex exec，最後 wait。
# 第二張參考圖：若存在 <id>.ref2 檔，內容為第二張 -i 圖的路徑。
P="/Users/boming/Documents/AI tool/反毒小劇場"
R="$P/review/G2/raw"
for id in "$@"; do
  imgs=(-i "$P/review/G2a/S4.png")
  if [[ -f "$R/$id.ref2" ]]; then imgs+=(-i "$(cat "$R/$id.ref2")"); fi
  caffeinate -i codex exec --skip-git-repo-check -s workspace-write -C "$P" "${imgs[@]}" \
    -o "$R/$id.txt" "$(cat "$R/$id.prompt.txt")" < /dev/null > "$R/$id.log" 2>&1 &
  echo "started $id pid $!"
done
wait
for id in "$@"; do echo "== $id"; cat "$R/$id.txt" 2>/dev/null || echo "(no output)"; ls -la "$R/$id.png" 2>/dev/null; done
