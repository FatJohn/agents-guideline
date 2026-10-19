#!/usr/bin/env bash
# SessionStart hook：把 controller 專用規則注入主對話。subagent 不跑 SessionStart，所以不會繼承。
# 登記方式見 docs/install.md「SessionStart hook：注入 controller 專用規則」。
dir="${CLAUDE_CONTROLLER_RULES_DIR:-$HOME/.claude/rules-controller}"
[ -d "$dir" ] || exit 0
for f in "$dir"/*.md; do
  [ -f "$f" ] || continue
  printf '# Contents of %s (controller-only rules; injected by SessionStart hook, not inherited by subagents)\n\n' "$f"
  cat "$f"
  printf '\n\n'
done
exit 0
