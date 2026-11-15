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
t "claude -w no flags -> deny"               2 "$(j 'claude -w 12 -n 12 "x"')"
t "cd && claude -w no flags -> deny"         2 "$(j 'cd /r && claude -w x "y"')"
t "claude --worktree only --model -> deny"   2 "$(j 'claude --worktree x --model m "y"')"
t "claude --worktree= only --effort -> deny" 2 "$(j 'claude --worktree=x --effort e "y"')"
t "indented claude -w -> deny"               2 "$(j '   claude -w x "y"')"
t "terminal create --command claude -w -> deny" 2 "$(j 'orca terminal create --worktree m --command "claude -w x"')"
t "terminal create --command single-quoted -> deny" 2 "$(j "orca terminal create --worktree m --command 'claude --worktree x'")"
t "documented claude -w fallback -> allow"   0 "$(j 'cd /r && claude -w 12 -n 12 --model claude-opus-5-5 --effort medium --permission-mode auto "$(cat /r/b.md)"')"
t "claude -w equals flags -> allow"          0 "$(j 'claude -w x --model=m --effort=e "y"')"
t "terminal create claude -w with flags -> allow" 0 "$(j 'orca terminal create --worktree m --command "claude -w x --model m --effort e"')"
t "claude -p -> allow"                       0 "$(j 'claude -p --model sonnet "hi" </dev/null')"
t "claude mcp list -> allow"                 0 "$(j 'claude mcp list')"
t "rg -w claude -> allow"                    0 "$(j 'rg -w claude file.txt')"
t "echo claude -w -> allow"                  0 "$(j 'echo claude -w')"
t "commit message mentioning claude -w -> allow" 0 "$(j 'git commit -m "claude -w support"')"
t "grep pattern \"claude -w\" -> allow"      0 "$(j 'grep -rn "claude -w" docs')"
t "env assignment before claude -w -> deny"  2 "$(j 'FOO=1 claude -w x "y"')"
t "env/command/nohup wrapper claude -w -> deny" 2 "$(j 'env FOO=1 nohup claude -w x "y"')"
t "absolute path claude -w -> deny"          2 "$(j '/usr/local/bin/claude -w x "y"')"
t "subshell (claude -w) -> deny"             2 "$(j '(claude -w y)')"
t "tab-indented claude -w -> deny"           2 "$(j $'\tclaude -w x')"
t "tab-separated claude<TAB>-w -> deny"      2 "$(j $'claude\t-w x')"
t "flags only inside prompt text -> deny"    2 "$(j 'claude -w x "do --model m --effort e"')"
t "claude -p prompt mentioning -w -> allow"  0 "$(j 'claude -p "explain the -w flag"')"
t "orca --worktree after --command -> allow" 0 "$(j 'orca terminal create --command "claude --permission-mode auto" --worktree path:/x')"
t "env assignment claude -w with flags -> allow" 0 "$(j 'FOO=1 claude -w x --model=m --effort=e "y"')"
t "env assignment before rg -w claude -> allow" 0 "$(j 'FOO=bar rg -w claude')"
t "garbage stdin -> fail-open exit 1"        1 'not json'
echo "failures=$fail"; [ "$fail" = 0 ]
