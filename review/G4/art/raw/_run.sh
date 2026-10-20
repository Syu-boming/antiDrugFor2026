#!/bin/zsh
# G4 美術：codex exec 平行生成。用法：_run.sh <id> [<id> ...]；讀 <id>.prompt.txt；參考圖 S4＋G2 stage_composite_v04（或 <id>.refs 指定）
P="/Users/boming/Documents/AI tool/反毒小劇場"
R="$P/review/G4/art/raw"
for id in "$@"; do
  if [[ -f "$R/$id.refs" ]]; then imgs=(); while read -r f; do imgs+=(-i "$f"); done < "$R/$id.refs";
  else imgs=(-i "$P/review/G2a/S4.png" -i "$P/review/G2/stage_composite_v04.png"); fi
  caffeinate -i codex exec --skip-git-repo-check -s workspace-write -C "$P" "${imgs[@]}" \
    -o "$R/$id.txt" "$(cat "$R/$id.prompt.txt")" < /dev/null > "$R/$id.log" 2>&1 &
  echo "started $id pid $!"
done
wait
for id in "$@"; do echo "== $id"; cat "$R/$id.txt" 2>/dev/null || echo "(no output)"; ls -la "$R/$id.png" 2>/dev/null; done
