#!/bin/bash
# Offline assertions for controller-context.sh (fixture directories via CLAUDE_CONTROLLER_RULES_DIR, no claude needed).
# usage: bash tests/test-controller-context.sh [path/to/controller-context.sh]
# default: ../hooks/controller-context.sh relative to this file. Needs bash only.
set -u
HOOK=${1:-$(dirname "$0")/../hooks/controller-context.sh}
fail=0
check(){ # name condition-exit-status(0=ok)
  if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; fail=$((fail+1)); fi
}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/controller-context.XXXXXX") || exit 1
trap 'rm -rf "$tmp"' EXIT

# (a) two .md files: both headers and both bodies, a before b
mkdir "$tmp/two"
printf 'ALPHA-BODY\n' > "$tmp/two/a.md"
printf 'BETA-BODY\n' > "$tmp/two/b.md"
out=$(CLAUDE_CONTROLLER_RULES_DIR="$tmp/two" bash "$HOOK"); rc=$?
check "two files: exit 0" "$rc"
case "$out" in *"# Contents of $tmp/two/a.md (controller-only rules;"*) ok=0;; *) ok=1;; esac
check "two files: header for a.md" "$ok"
case "$out" in *"# Contents of $tmp/two/b.md (controller-only rules;"*) ok=0;; *) ok=1;; esac
check "two files: header for b.md" "$ok"
case "$out" in *ALPHA-BODY*) ok=0;; *) ok=1;; esac
check "two files: a.md content" "$ok"
case "$out" in *BETA-BODY*) ok=0;; *) ok=1;; esac
check "two files: b.md content" "$ok"
pa=${out%%ALPHA-BODY*}; pb=${out%%BETA-BODY*}
if [ ${#pa} -lt ${#pb} ]; then ok=0; else ok=1; fi
check "two files: a before b" "$ok"

# (b) directory does not exist: exit 0, no output
out=$(CLAUDE_CONTROLLER_RULES_DIR="$tmp/nope" bash "$HOOK"); rc=$?
check "missing dir: exit 0" "$rc"
if [ -z "$out" ]; then ok=0; else ok=1; fi
check "missing dir: empty output" "$ok"

# (c) directory exists but has no .md: exit 0, no output
mkdir "$tmp/empty"; printf 'not markdown\n' > "$tmp/empty/note.txt"
out=$(CLAUDE_CONTROLLER_RULES_DIR="$tmp/empty" bash "$HOOK"); rc=$?
check "no .md files: exit 0" "$rc"
if [ -z "$out" ]; then ok=0; else ok=1; fi
check "no .md files: empty output" "$ok"

echo "failures=$fail"; [ "$fail" = 0 ]
