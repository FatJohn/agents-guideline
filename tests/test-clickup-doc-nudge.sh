#!/bin/bash
# Offline assertions for clickup-doc-nudge.sh (synthetic stdin JSON, no claude needed).
# usage: bash tests/test-clickup-doc-nudge.sh [path/to/clickup-doc-nudge.sh]
# default: ../global/claude/hooks/clickup-doc-nudge.sh relative to this file. Needs bash and jq.
set -u
HOOK=${1:-$(dirname "$0")/../global/claude/hooks/clickup-doc-nudge.sh}
fail=0
check(){ # name condition-exit-status(0=ok)
  if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; fail=$((fail+1)); fi
}
P=mcp__claude_ai_ClickUp__clickup_
run(){ # tool_name [extra-json-fields]
  printf '{"hook_event_name":"PreToolUse","session_id":"s1","tool_name":"%s","tool_input":{}%s}' "$1" "${2:-}" | bash "$HOOK"
}
nudge_has(){ # output pattern
  printf '%s' "$1" | jq -e --arg p "$2" '.hookSpecificOutput.hookEventName=="PreToolUse" and (.hookSpecificOutput.additionalContext|test($p)) and (.hookSpecificOutput|has("permissionDecision")|not)' >/dev/null 2>&1
}

# (a) read tool: read-side reminder, exit 0, no permission decision (does not block or allow)
out=$(run "${P}get_document_pages"); rc=$?
check "get_document_pages: exit 0" "$rc"
nudge_has "$out" "不要重讀"; check "get_document_pages: read reminder" "$?"
nudge_has "$out" "不派 subagent 摘要"; check "get_document_pages: spec read in main" "$?"

# (b) write tool: write-side reminder
out=$(run "${P}update_document_page"); rc=$?
check "update_document_page: exit 0" "$rc"
nudge_has "$out" "不重送整頁"; check "update_document_page: send only the new part" "$?"
printf '%s' "$out" | jq -e '.hookSpecificOutput.additionalContext|test("subagent")|not' >/dev/null; check "update_document_page: no subagent hand-off" "$?"
nudge_has "$out" "不要再 get 整頁讀回"; check "update_document_page: no read-back" "$?"

# (c) other tools: silent exit 0 (incl. the neighbouring ClickUp list tool and a lookalike suffix)
for t in "${P}list_document_pages" "${P}get_task" "${P}get_document_pages_x" "x${P}get_document_pages" Bash Read mcp__other__get_document_pages; do
  out=$(run "$t"); rc=$?
  [ "$rc" = 0 ] && [ -z "$out" ]; check "other tool $t: silent" "$?"
done

# (d) subagent (agent_id present): silent even for the matched tools
for t in get_document_pages update_document_page; do
  out=$(run "${P}$t" ',"agent_id":"a1"'); rc=$?
  [ "$rc" = 0 ] && [ -z "$out" ]; check "subagent $t: silent" "$?"
done

# (e) CRLF from a native Windows jq is stripped
tmp=$(mktemp -d "${TMPDIR:-/tmp}/clickup-doc-nudge.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/bin"; real_jq=$(command -v jq)
printf '#!/bin/bash\n"%s" "$@" | sed "s/$/\\r/"\nexit "${PIPESTATUS[0]}"\n' "$real_jq" > "$tmp/bin/jq"; chmod +x "$tmp/bin/jq"
out=$(printf '{"tool_name":"%sget_document_pages"}' "$P" | PATH="$tmp/bin:$PATH" bash "$HOOK" | tr -d '\r')
nudge_has "$out" "不要重讀"; check "CRLF jq output: still nudges" "$?"

# (f) stdin is not JSON: exit 1 (hook did not run), no stdout
out=$(printf 'garbage' | bash "$HOOK" 2>/dev/null); rc=$?
[ "$rc" = 1 ]; check "non-JSON stdin: exit 1" "$?"
[ -z "$out" ]; check "non-JSON stdin: no stdout" "$?"

echo "failures=$fail"; [ "$fail" = 0 ]
