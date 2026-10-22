#!/bin/bash
# Offline assertions for allow-git-c-projects.sh (synthetic PreToolUse stdin, no claude needed).
# usage: bash tests/test-allow-git-c-projects.sh [path/to/allow-git-c-projects.sh]
# default: ../global/claude/hooks/allow-git-c-projects.sh relative to this file. Needs bash + jq.
HOOK=${1:-$(dirname "$0")/../global/claude/hooks/allow-git-c-projects.sh}
case "$HOOK" in /*) ;; *) HOOK="$PWD/$HOOK" ;; esac
TMPHOME=$(mktemp -d "${TMPDIR:-/tmp}/allowgitc.XXXXXX") || exit 1
trap 'rm -rf "$TMPHOME"' EXIT
mkdir -p "$TMPHOME/Projects/foo" "$TMPHOME/outside"
H=$TMPHOME
fail=0
cmdjson(){ jq -nc --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}'; }
# t name want(allow|skip|exit1) stdin-json
t(){
  out=$(printf '%s' "$3" | HOME="$H" bash "$HOOK" 2>/dev/null); got_exit=$?
  if [ "$got_exit" = 1 ]; then got=exit1
  elif printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName == "PreToolUse" and .hookSpecificOutput.permissionDecision == "allow"' >/dev/null 2>&1; then got=allow
  elif [ "$got_exit" = 0 ] && [ -z "$out" ]; then got=skip
  else got="unexpected(exit=$got_exit out=$out)"; fi
  if [ "$got" = "$2" ]; then echo "PASS $got  $1"; else echo "FAIL got=$got want=$2  $1"; fail=$((fail+1)); fi
}
# tl: like t but with a UTF-8 locale in the hook's environment
tl(){
  out=$(printf '%s' "$3" | LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 HOME="$H" bash "$HOOK" 2>/dev/null); got_exit=$?
  if [ "$got_exit" = 0 ] && [ -z "$out" ]; then got=skip
  elif printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "allow"' >/dev/null 2>&1; then got=allow
  else got="unexpected(exit=$got_exit out=$out)"; fi
  if [ "$got" = "$2" ]; then echo "PASS $got  $1"; else echo "FAIL got=$got want=$2  $1"; fail=$((fail+1)); fi
}
# c name want command
c(){ t "$1" "$2" "$(cmdjson "$3")"; }

c "worktree remove -> allow"            allow "git -C $H/Projects/foo worktree remove $H/Projects/foo/.wt/a"
c "branch -D -> allow"                  allow "git -C $H/Projects/foo branch -D feature/x"
c "surrounding spaces + multi arg -> allow" allow "  git -C $H/Projects/foo branch -D a b  "
c "-c core.pager injection -> skip"     skip  "git -C -c core.pager=x worktree remove a"
c "-c after path -> skip"               skip  "git -C $H/Projects/foo -c core.pager=x worktree remove a"
c "--exec-path= injection -> skip"      skip  "git --exec-path=/tmp/x -C $H/Projects/foo worktree remove a"
c "--exec-path as -C path -> skip"      skip  "git -C --exec-path=/tmp/x worktree remove a"
c "path does not exist -> skip"         skip  "git -C $H/Projects/nope worktree remove a"
c "path outside Projects -> skip"       skip  "git -C $H/outside worktree remove a"
c "path with .. -> skip"                skip  "git -C $H/Projects/foo/../../outside worktree remove a"
c "path = Projects/ itself -> skip"     skip  "git -C $H/Projects/ worktree remove a"
c "path = Projects/. -> skip"           skip  "git -C $H/Projects/. branch -D a"
c "path = Projects/./ -> skip"          skip  "git -C $H/Projects/./ branch -D a"
c "path = Projects/./. -> skip"         skip  "git -C $H/Projects/./. branch -D a"
c "path = Projects/foo/. -> allow"      allow "git -C $H/Projects/foo/. branch -D a"
c "tilde path -> skip"                  skip  "git -C ~/Projects/foo worktree remove a"
c "&& chaining -> skip"                 skip  "git -C $H/Projects/foo worktree remove a && rm -rf /"
c "; chaining -> skip"                  skip  "git -C $H/Projects/foo branch -D a; id"
c "pipe -> skip"                        skip  "git -C $H/Projects/foo branch -D a | cat"
c "\$(...) -> skip"                     skip  "git -C $H/Projects/foo branch -D \$(id)"
# shellcheck disable=SC2016 # literal backtick on purpose
c "backtick -> skip"                    skip  'git -C '"$H"'/Projects/foo branch -D `id`'
c "redirect -> skip"                    skip  "git -C $H/Projects/foo branch -D a > /tmp/x"
c "quoted arg -> skip"                  skip  "git -C $H/Projects/foo branch -D 'a'"
c "newline second command -> skip"      skip  "$(printf 'git -C %s/Projects/foo branch -D a\nid' "$H")"
c "worktree remove --force -> skip"     skip  "git -C $H/Projects/foo worktree remove --force a"
c "worktree remove -f -> skip"          skip  "git -C $H/Projects/foo worktree remove -f a"
c "branch -D --force-ish arg -> skip"   skip  "git -C $H/Projects/foo branch -D a --track"
c "no args -> skip"                     skip  "git -C $H/Projects/foo worktree remove"
c "-C glued -> skip"                    skip  "git -C$H/Projects/foo worktree remove a"
c "--git-dir -> skip"                   skip  "git --git-dir=$H/Projects/foo/.git worktree remove a"
c "other subcommand (push) -> skip"     skip  "git -C $H/Projects/foo push origin a"
c "branch -d lowercase -> skip"         skip  "git -C $H/Projects/foo branch -d a"
c "env prefix -> skip"                  skip  "GIT_DIR=/x git -C $H/Projects/foo branch -D a"
c "non-git command -> skip"             skip  "rm -rf $H/Projects/foo"
tl "UTF-8 locale, e-acute arg -> skip"  skip  "$(cmdjson "git -C $H/Projects/foo branch -D é")"
tl "UTF-8 locale, fullwidth arg -> skip" skip "$(cmdjson "git -C $H/Projects/foo branch -D ａ")"
tl "UTF-8 locale, ascii arg -> allow"   allow "$(cmdjson "git -C $H/Projects/foo branch -D a")"
t "tool_name Edit -> skip"              skip  "$(jq -nc --arg c "git -C $H/Projects/foo branch -D a" '{tool_name:"Edit",tool_input:{command:$c}}')"
t "missing tool_input -> skip"          skip  '{"tool_name":"Bash"}'
t "garbage stdin -> fail-open exit 1"   exit1 'not json'
t "empty stdin -> fail-open exit 1"     exit1 ''
echo "failures=$fail"; [ "$fail" = 0 ]
