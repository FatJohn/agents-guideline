#!/bin/bash
# Offline assertions for context-size-nudge.sh (synthetic transcript + stdin JSON, no claude needed).
# usage: bash tests/test-context-size-nudge.sh [path/to/context-size-nudge.sh]
# default: ../global/claude/hooks/context-size-nudge.sh relative to this file. Needs bash and jq.
set -u
HOOK=${1:-$(dirname "$0")/../global/claude/hooks/context-size-nudge.sh}
fail=0
check(){ # name condition-exit-status(0=ok)
  if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; fail=$((fail+1)); fi
}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/context-size-nudge.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT
T="$tmp/t.jsonl"
usage(){ # input cache_read cache_creation -> one assistant line
  printf '{"type":"assistant","message":{"usage":{"input_tokens":%s,"cache_read_input_tokens":%s,"cache_creation_input_tokens":%s}}}\n' "$1" "$2" "$3"
}
run(){ # extra-json-fields ; uses $T, state in $tmp/state
  printf '{"session_id":"sid-1","transcript_path":"%s"%s}' "$T" "${1:-}" |
    CLAUDE_CTX_NUDGE_STATE="$tmp/state" bash "$HOOK"
}
has_nudge(){ printf '%s' "$1" | jq -e '.hookSpecificOutput.hookEventName=="PostToolUse" and (.hookSpecificOutput.additionalContext|test("handoff skill §4"))' >/dev/null 2>&1; }

# (a) below threshold: silent, exit 0
usage 10 200000 5000 > "$T"
out=$(run); rc=$?
check "below threshold: exit 0" "$rc"
[ -z "$out" ]; check "below threshold: no output" "$?"

# (b) crossing 300K: one nudge carrying the measured size (sum of the three usage fields)
usage 10 290000 15000 >> "$T"
out=$(run); rc=$?
check "crossing: exit 0" "$rc"
has_nudge "$out"; check "crossing: additionalContext JSON" "$?"
case "$out" in *"約 305K"*) ok=0;; *) ok=1;; esac
check "crossing: size is input+cache_read+cache_creation" "$ok"

# (c) same band again: silent
usage 10 300000 20000 >> "$T"
out=$(run)
[ -z "$out" ]; check "same band: no repeat" "$?"

# (d) next 100K band: nudges again
usage 10 400000 20000 >> "$T"
out=$(run)
has_nudge "$out"; check "next band: nudge again" "$?"

# (e) drop below threshold (compact) resets; crossing again nudges
usage 10 90000 0 >> "$T"
out=$(run)
[ -z "$out" ]; check "after compact: silent" "$?"
usage 10 310000 0 >> "$T"
out=$(run)
has_nudge "$out"; check "after compact: crossing nudges again" "$?"

# (f) subagent (agent_id present): silent even far above threshold, state untouched
rm -rf "$tmp/state"; usage 10 900000 0 > "$T"
out=$(run ',"agent_id":"a1"'); rc=$?
check "subagent: exit 0" "$rc"
[ -z "$out" ]; check "subagent: no output" "$?"
[ ! -e "$tmp/state/sid-1" ]; check "subagent: no state written" "$?"

# (g) the last assistant usage wins; trailing non-assistant and broken lines are skipped
{ usage 10 900000 0; usage 10 100000 0; printf '{"type":"user"}\nnot json\n'; } > "$T"
out=$(run)
[ -z "$out" ]; check "last usage wins: small last value stays silent" "$?"
# a broken line before the last usage must not hide it
rm -rf "$tmp/state"; { usage 10 100000 0; printf '{"type":"assistant","message":{"usa\n'; usage 10 350000 0; } > "$T"
out=$(run)
has_nudge "$out"; check "broken line before the last usage: still nudges" "$?"

# (g2) parallel tool calls crossing the same band: exactly one nudge
# The race is probabilistic without the atomic claim, so repeat: every round must give exactly one.
usage 10 350000 0 > "$T"; bad=0
for round in 1 2 3 4 5 6 7 8; do
  rm -rf "$tmp/state"
  for i in 1 2 3 4 5 6 7 8; do run > "$tmp/par.$i" & done; wait
  n=$(cat "$tmp"/par.* | grep -c hookEventName)
  [ "$n" = 1 ] || bad=$((bad+1))
done
[ "$bad" = 0 ]; check "parallel calls: one nudge per band in all 8 rounds (bad rounds: $bad)" "$?"

# (g3) CRLF from a native Windows jq is stripped (jq wrapper that appends CR to every line)
mkdir "$tmp/bin"; real_jq=$(command -v jq)
printf '#!/bin/bash\n"%s" "$@" | sed "s/$/\\r/"\nexit "${PIPESTATUS[0]}"\n' "$real_jq" > "$tmp/bin/jq"; chmod +x "$tmp/bin/jq"
rm -rf "$tmp/state"; usage 10 350000 0 > "$T"
out=$(printf '{"session_id":"sid-1","transcript_path":"%s"}' "$T" | PATH="$tmp/bin:$PATH" CLAUDE_CTX_NUDGE_STATE="$tmp/state" bash "$HOOK" | tr -d '\r')
has_nudge "$out"; check "CRLF jq output: still nudges" "$?"

# (h) missing transcript, unsafe session id: silent exit 0
out=$(printf '{"session_id":"sid-1","transcript_path":"%s/nope.jsonl"}' "$tmp" | CLAUDE_CTX_NUDGE_STATE="$tmp/state" bash "$HOOK"); rc=$?
check "missing transcript: exit 0" "$rc"
[ -z "$out" ]; check "missing transcript: no output" "$?"
usage 10 900000 0 > "$T"
out=$(printf '{"session_id":"../x","transcript_path":"%s"}' "$T" | CLAUDE_CTX_NUDGE_STATE="$tmp/state" bash "$HOOK"); rc=$?
check "unsafe session id: exit 0" "$rc"
[ -z "$out" ]; check "unsafe session id: no output" "$?"
[ ! -e "$tmp/x" ]; check "unsafe session id: nothing written outside state dir" "$?"

# (i) stdin is not JSON: exit 1 (hook did not run), no stdout
out=$(printf 'garbage' | CLAUDE_CTX_NUDGE_STATE="$tmp/state" bash "$HOOK" 2>/dev/null); rc=$?
[ "$rc" = 1 ]; check "non-JSON stdin: exit 1" "$?"
[ -z "$out" ]; check "non-JSON stdin: no stdout" "$?"

# (j) threshold override
rm -rf "$tmp/state"; usage 10 50000 0 > "$T"
out=$(printf '{"session_id":"sid-1","transcript_path":"%s"}' "$T" | CLAUDE_CTX_NUDGE_THRESHOLD=40000 CLAUDE_CTX_NUDGE_STATE="$tmp/state" bash "$HOOK")
has_nudge "$out"; check "threshold override: nudges at the lower threshold" "$?"

echo "failures=$fail"; [ "$fail" = 0 ]
