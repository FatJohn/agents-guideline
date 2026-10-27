#!/bin/bash
# Offline assertions for require-issue-session-model.sh (synthetic PreToolUse stdin, no claude needed).
# usage: bash tests/test-require-issue-session-model.sh [path/to/require-issue-session-model.sh]
# default: ../global/claude/hooks/require-issue-session-model.sh relative to this file. Needs bash + jq.
HOOK=${1:-$(dirname "$0")/../global/claude/hooks/require-issue-session-model.sh}
fail=0
t(){ # name expected_exit json
  printf '%s' "$3" | bash "$HOOK" >/dev/null 2>&1; got=$?
  if [ "$got" = "$2" ]; then echo "PASS exit=$got  $1"; else echo "FAIL exit=$got (want $2)  $1"; fail=$((fail+1)); fi
}
j(){ jq -nc --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}'; }
FULL='orca worktree create --repo path:/r --name member-1 --no-parent --base-branch origin/main --agent claude --model claude-opus-5-5 --effort medium --prompt "$(cat /r/b.md)" --json'
t "worktree create, no flags -> deny"        2 "$(j 'orca worktree create --repo path:/r --name m --no-parent --agent claude --prompt "x" --json')"
t "worktree create, only --model -> deny"    2 "$(j 'orca worktree create --name m --agent claude --model claude-opus-5-5 --prompt "x"')"
t "worktree create, only --effort -> deny"   2 "$(j 'orca worktree create --name m --agent claude --effort medium --prompt "x"')"
t "agent launch, no flags -> deny"           2 "$(j 'orca agent launch --worktree m --agent claude --prompt "x"')"
t "--model with empty next flag -> deny"     2 "$(j 'orca worktree create --name m --agent claude --model --effort medium --prompt "x"')"
t "multi-line, launch line lacks flags -> deny" 2 "$(j $'W=/r\norca worktree create --repo path:$W --name m --agent claude --prompt "x"')"
t "chained &&, launch lacks flags -> deny"   2 "$(j 'git -C /r fetch -q origin && orca worktree create --repo path:/r --name m --agent claude --prompt "x"')"
t "quoted --agent \"claude\" no flags -> deny"  2 "$(j 'orca worktree create --name m --agent "claude" --prompt "x"')"
t "quoted --agent='"'"'claude'"'"' no flags -> deny" 2 "$(j "orca worktree create --name m --agent='claude' --prompt x")"
t "full documented command -> allow"         0 "$(j "$FULL")"
t "equals form -> allow"                     0 "$(j 'orca worktree create --name m --agent=claude --model=claude-opus-5-5 --effort=medium --prompt "x"')"
t "agent launch with flags -> allow"         0 "$(j 'orca agent launch --worktree m --agent claude --model claude-opus-5-5 --effort medium --prompt "x"')"
t "chained &&, launch has flags -> allow"    0 "$(j "git -C /r fetch -q origin && $FULL")"
t "prompt text containing && -> allow"       0 "$(j 'orca worktree create --name m --agent claude --model claude-opus-5-5 --effort medium --prompt "run a && b; then c" --json')"
t "codex agent without flags -> allow"       0 "$(j 'orca worktree create --name m --agent codex --prompt "x"')"
t "no --agent (plain worktree) -> allow"     0 "$(j 'orca worktree create --name m --no-parent --json')"
t "orca terminal create -> allow"            0 "$(j 'orca terminal create --worktree m --command "claude"')"
t "unrelated command -> allow"               0 "$(j 'git status')"
t "non-Bash tool -> allow"                   0 '{"tool_name":"Edit","tool_input":{"file_path":"/r/a.md"}}'
t "garbage stdin -> fail-open exit 1"        1 'not json'
echo "failures=$fail"; [ "$fail" = 0 ]
