#!/bin/bash
# Offline assertions for controller-context.sh (route card path via CLAUDE_ROUTE_CARD, no claude needed).
# usage: bash tests/test-controller-context.sh [path/to/controller-context.sh]
# default: ../global/claude/hooks/controller-context.sh relative to this file. Needs bash only.
set -u
HOOK=${1:-$(dirname "$0")/../global/claude/hooks/controller-context.sh}
fail=0
check(){ # name condition-exit-status(0=ok)
  if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; fail=$((fail+1)); fi
}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/controller-context.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT

# (a) card exists: prefix line naming the file, then the card body, exit 0
printf 'CARD-BODY-LINE1\nCARD-BODY-LINE2\n' > "$tmp/card.md"
out=$(CLAUDE_ROUTE_CARD="$tmp/card.md" bash "$HOOK"); rc=$?
check "card exists: exit 0" "$rc"
first=${out%%$'\n'*}
if [ "$first" = "# Contents of $tmp/card.md (controller route card; injected by SessionStart hook, not inherited by subagents)" ]; then ok=0; else ok=1; fi
check "card exists: first line is the prefix" "$ok"
case "$out" in *CARD-BODY-LINE1*CARD-BODY-LINE2*) ok=0;; *) ok=1;; esac
check "card exists: body content" "$ok"
pp=${out%%CARD-BODY-LINE1*}
case "$pp" in *"# Contents of "*) ok=0;; *) ok=1;; esac
check "card exists: prefix before body" "$ok"

# (b) card file does not exist: exit 0, no output
out=$(CLAUDE_ROUTE_CARD="$tmp/nope.md" bash "$HOOK"); rc=$?
check "missing card: exit 0" "$rc"
if [ -z "$out" ]; then ok=0; else ok=1; fi
check "missing card: empty output" "$ok"

# (c) the path is a directory, not a file: exit 0, no output
mkdir "$tmp/dir.md"
out=$(CLAUDE_ROUTE_CARD="$tmp/dir.md" bash "$HOOK"); rc=$?
check "path is a directory: exit 0" "$rc"
if [ -z "$out" ]; then ok=0; else ok=1; fi
check "path is a directory: empty output" "$ok"

# (d) default path: with HOME pointing at an empty dir and no override, nothing is injected
mkdir "$tmp/home"
out=$(env -u CLAUDE_ROUTE_CARD HOME="$tmp/home" bash "$HOOK"); rc=$?
check "default path missing: exit 0" "$rc"
if [ -z "$out" ]; then ok=0; else ok=1; fi
check "default path missing: empty output" "$ok"

# (e) default path: card at $HOME/.claude/route-card.md is found without the override
mkdir -p "$tmp/home/.claude"; printf 'HOME-CARD\n' > "$tmp/home/.claude/route-card.md"
out=$(env -u CLAUDE_ROUTE_CARD HOME="$tmp/home" bash "$HOOK"); rc=$?
check "default path present: exit 0" "$rc"
case "$out" in *"# Contents of $tmp/home/.claude/route-card.md (controller route card;"*HOME-CARD*) ok=0;; *) ok=1;; esac
check "default path present: prefix and body" "$ok"

echo "failures=$fail"; [ "$fail" = 0 ]
