#!/usr/bin/env bash
# PreToolUse hook：主對話呼叫 ClickUp 讀頁／寫頁工具時，以 additionalContext 注入一句省 context 的做法，不擋呼叫。
# 只認 tool_name 是下面兩個 ClickUp 工具；其他工具、subagent（stdin 有 agent_id）一律無輸出 exit 0。
# 沒有 jq 或 stdin 不是 JSON 時 exit 1（不擋工具，transcript 看得到 hook 沒跑）。
# 登記方式見 docs/install.md「選配：ClickUp 文件頁讀寫提醒」。測試：tests/test-clickup-doc-nudge.sh。
command -v jq >/dev/null 2>&1 || { echo "clickup-doc-nudge: INACTIVE, jq not found" >&2; exit 1; }
input=$(cat)
fields=$(printf '%s' "$input" | jq -r '[.agent_id // "", .tool_name // ""] | join("\u001f")' 2>/dev/null) || {
  echo "clickup-doc-nudge: did not run, stdin is not JSON" >&2; exit 1; }
fields=${fields//$'\r'/}
IFS=$'\037' read -r agent_id tool <<EOF
$fields
EOF
# 提醒只為省主對話的 context；subagent 的 context 是分開的，不提醒。
[ -z "$agent_id" ] || exit 0

case "$tool" in
  mcp__claude_ai_ClickUp__clickup_get_document_pages)
    msg="ClickUp 文件頁常是單頁就數萬字元，整頁進主對話 context。這一頁已經在 context 裡就不要重讀；剛 update 完不要整頁讀回核對（成功回應就夠）。要照著實作的規格（驗收條件、欄位名、流程邊界）主對話自己讀原文，不派 subagent 摘要。" ;;
  mcp__claude_ai_ClickUp__clickup_update_document_page)
    msg="ClickUp 寫頁的內容會整段留在主對話 context。只新增段落時用 append 只送新增的部分，不重送整頁 replace；寫完不要再 get 整頁讀回核對（成功回應就夠）。" ;;
  *) exit 0 ;;
esac
jq -n --arg m "$msg" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
exit 0
