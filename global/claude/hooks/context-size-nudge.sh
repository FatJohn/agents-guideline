#!/usr/bin/env bash
# PostToolUse hook：主對話 context 跨過門檻時，注入一次交接提醒（dispatch skill §6「主對話 context 管理」）。
# 讀 stdin 的 transcript_path，取最後一筆 assistant usage 的 input＋cache_read＋cache_creation 當 context 大小。
# 每個 session 每跨一個 100K 級距只提醒一次；掉回門檻以下（compact 之後）重新計。subagent（stdin 有 agent_id）不提醒。
# 沒有 jq 或 stdin 不是 JSON 時 exit 1（不擋工具，transcript 看得到 hook 沒跑）。
# 登記方式見 docs/install.md「選配：主對話 context 跨門檻提醒」。測試：tests/test-context-size-nudge.sh。
command -v jq >/dev/null 2>&1 || { echo "context-size-nudge: INACTIVE, jq not found" >&2; exit 1; }
input=$(cat)
# 分隔用 US（0x1f）：tab 是空白類 IFS，開頭的空欄位（主對話沒有 agent_id）會被吃掉、後面的欄位整個錯位。
fields=$(printf '%s' "$input" | jq -r '[.agent_id // "", .session_id // "", .transcript_path // ""] | join("\u001f")' 2>/dev/null) || {
  echo "context-size-nudge: did not run, stdin is not JSON" >&2; exit 1; }
fields=${fields//$'\r'/}  # Windows 原生 jq 的輸出行尾是 CRLF；不接 tr 是為了保留上一行 jq 的 exit code
IFS=$'\037' read -r agent_id sid transcript <<EOF
$fields
EOF
[ -z "$agent_id" ] || exit 0
case "$sid" in ''|*[!A-Za-z0-9_-]*) exit 0;; esac
[ -f "$transcript" ] || exit 0

threshold=${CLAUDE_CTX_NUDGE_THRESHOLD:-300000}
step=100000
ctx=$(tail -n 80 "$transcript" | jq -R -r 'fromjson? | select(.type=="assistant" and .message.usage!=null) | .message.usage | ((.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0))' 2>/dev/null | tr -d '\r' | tail -n 1)
case "$ctx" in ''|*[!0-9]*) exit 0;; esac

state_dir=${CLAUDE_CTX_NUDGE_STATE:-${TMPDIR:-/tmp}/claude-ctx-nudge}
state="$state_dir/$sid"
prev=0
[ -f "$state" ] && prev=$(cat "$state" 2>/dev/null)
case "$prev" in ''|*[!0-9]*) prev=0;; esac

if [ "$ctx" -lt "$threshold" ]; then
  if [ "$prev" != 0 ]; then echo 0 > "$state"; rmdir "$state".b* 2>/dev/null; fi
  exit 0
fi
band=$((ctx / step))
[ "$band" -ge 1 ] || band=1
[ "$band" -gt "$prev" ] || exit 0
mkdir -p "$state_dir" 2>/dev/null || exit 0
# mkdir 是原子的：同一則訊息的平行工具呼叫會同時跑到這裡，只有搶到這個級距目錄的那一個提醒。
mkdir "$state.b$band" 2>/dev/null || exit 0
echo "$band" > "$state" || exit 0

msg="主對話 context 約 $((ctx / 1000))K（門檻 $((threshold / 1000))K）。還有未做的 phase 時：做到目前段落結束，寫 session 交接卡（handoff skill §4），告訴使用者剩下的 phase 開新 session 接手；不派 subagent 代做。沒有未做的 phase 就照常收尾。依據：dispatch skill §6。"
jq -n --arg m "$msg" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $m}}'
exit 0
