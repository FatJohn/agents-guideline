#!/bin/bash
# Offline assertions for config/ripgreprc. Builds its own fixture.
# usage: bash tests/test-ripgreprc.sh [path/to/ripgreprc] [fixture-dir]
# defaults: ../config/ripgreprc relative to this file; a fresh mktemp -d fixture
# that is removed on exit (a fixture dir passed in by the caller is never deleted).
# Needs: bash, rg, git.
RC=${1:-$(dirname "$0")/../config/ripgreprc}
D=${2:-}
if [ -z "$D" ]; then
  D=$(mktemp -d) || exit 2
  trap 'rm -rf "$D"' EXIT
fi
mkdir -p "$D/.claude/sub" "$D/.git" "$D/.github/workflows" "$D/src" || exit 2
[ -d "$D/.git/objects" ] || git -C "$D" init -q
echo "TOKEN_A_HIDDEN"   > "$D/.claude/sub/f.txt"
echo "TOKEN_B_GITDIR"   > "$D/.git/probe.txt"
echo "TOKEN_G_WORKFLOW" > "$D/.github/workflows/x.yml"
echo "TOKEN_V_VISIBLE"  > "$D/src/visible.txt"
RC=$(cd "$(dirname "$RC")" && pwd)/$(basename "$RC")
cd "$D" || exit 2
fail=0
chk(){ # name want(hit|none) pattern
  out=$(RIPGREP_CONFIG_PATH=$RC rg -n "$3" . </dev/null 2>&1)
  if [ -n "$out" ]; then got=hit; else got=none; fi
  if [ "$got" = "$2" ]; then echo "PASS $got  $1"; else echo "FAIL $got (want $2)  $1"; fail=$((fail+1)); fi
}
chk "hidden dir .claude is searched"  hit  TOKEN_A_HIDDEN
chk ".git internals are not searched" none TOKEN_B_GITDIR
chk ".github/workflows is searched"   hit  TOKEN_G_WORKFLOW
chk "visible file still searched"     hit  TOKEN_V_VISIBLE
echo "failures=$fail"; [ "$fail" = 0 ]
