#!/bin/zsh
# 第三幕（a3）：codex exec 內建 image_gen（ChatGPT 額度；不切換 API 模式）。用法：_run.sh <id> [<id> ...]
P="/Users/boming/Documents/AI tool/反毒小劇場"
R="$P/review/G5/a3/raw"
for id in "$@"; do
  imgs=(); while read -r f; do [[ -n "$f" ]] && imgs+=(-i "$f"); done < "$R/$id.refs"
  caffeinate -i codex exec --skip-git-repo-check -s workspace-write -C "$P" "${imgs[@]}" \
    -o "$R/$id.txt" "$(cat "$R/$id.prompt.txt")" < /dev/null > "$R/$id.log" 2>&1 &
  echo "started $id pid $!"
done
wait
for id in "$@"; do echo "== $id"; tail -5 "$R/$id.txt" 2>/dev/null || echo "(no output)"; ls -la "$R/$id.png" 2>/dev/null; done
