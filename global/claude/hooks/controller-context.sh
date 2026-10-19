#!/usr/bin/env bash
# SessionStart hook：把 controller 路由卡注入主對話。subagent 不跑 SessionStart，所以不會繼承。
# 登記方式見 docs/install.md「SessionStart hook：注入 controller 路由卡」。
card="${CLAUDE_ROUTE_CARD:-$HOME/.claude/route-card.md}"
[ -f "$card" ] || exit 0
printf '# Contents of %s (controller route card; injected by SessionStart hook, not inherited by subagents)\n\n' "$card"
cat "$card"
printf '\n'
exit 0
