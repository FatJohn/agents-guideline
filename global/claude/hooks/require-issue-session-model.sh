#!/bin/bash
# PreToolUse hook: a Claude issue session launch (Orca, or the container-neutral `claude -w`)
# must carry --model and --effort.
#
# Rule (worktree-session skill, references/cli.md "盤點 session 與 issue session"):
# an issue session is a controller and must not inherit the main conversation's
# default model, so `orca worktree create ... --agent claude` and
# `orca agent launch ... --agent claude` always pass
# `--model claude-opus-5-5 --effort medium`. Without flags the new `claude`
# process takes whatever ~/.claude/settings.json "model" is at that moment
# (2026-10-27: four issue sessions came up as Sonnet/high and Fable because the
# controller copied an example without the flags). This hook makes the rule
# mechanical; the VALUES stay policy in cli.md, only presence is checked here.
#
# Decision table (stdin JSON from Claude Code PreToolUse):
#   - tool_name is not Bash                                        -> allow
#   - command split into segments on newline ; && || |
#   - a segment is a "claude launch" when it contains
#       `orca worktree create` or `orca agent launch`
#     AND the token `--agent claude` (or `--agent=claude`, or the value in
#     double/single quotes);
#     OR when `claude` is the command word (segment start, or the quoted
#     value of `--command`, as in `--command "claude ..."`) and it carries
#     `-w` / `--worktree` (the container-neutral `claude -w` fallback in cli.md).
#     `claude -p`, `claude mcp ...`, `rg -w claude` etc. are not launches.
#   - every claude-launch segment must contain both a `--model <v>` and an
#     `--effort <v>` token (`--model=<v>` / `--effort=<v>` also count)
#   - any claude-launch segment missing one                        -> exit 2
#     (tool call blocked, message on stderr goes to the model)
#   everything else                                                -> exit 0
#   A segment split inside a quoted --prompt text is harmless as long as the
#   flags come before --prompt (the documented order).
#   Other agents (`--agent codex`) are not checked: their model flags are theirs.
#
# Fail-open on purpose: if jq is missing or stdin is unparsable we exit 1
# (non-blocking error, visible in the transcript) and the tool call proceeds.
#
# Optional audit log: set ISSUE_SESSION_MODEL_LOG=/path/to/file to append one
# line per decision (leave unset in normal use).
#
# Offline tests: tests/test-require-issue-session-model.sh. Install: docs/install.md.
#
# Needs: bash, jq, cat, tr. No python. Works in macOS bash 3.2 and Git Bash.

export LC_ALL=C

if ! command -v jq >/dev/null 2>&1; then
  echo "require-issue-session-model: jq not found, issue-session model guard is INACTIVE" >&2
  exit 1
fi

input=$(cat)

# @tsv keeps the command on one line (newline -> \n, tab -> \t) so a multi-line
# command survives the read below; segments are split on the literal "\n" too.
verdict=$(printf '%s' "$input" | jq -r '
  [(.tool_name // "" | tostring), (.tool_input.command // "" | tostring)] | @tsv
' 2>/dev/null | tr -d '\r')

if [ -z "$verdict" ]; then
  echo "require-issue-session-model: could not parse hook input, guard did not run" >&2
  exit 1
fi

tool=${verdict%%$'\t'*}
cmd=${verdict#*$'\t'}
[ "$verdict" = "$tool" ] && cmd=""

decision="allow"
reason="not-bash"
missing=""

if [ "$tool" = "Bash" ] && [ -n "$cmd" ]; then
  reason="no-claude-launch"
  # segment separators -> newline; the \n escape from @tsv is a separator too
  segs=$(printf '%s' "$cmd" | sed -e 's/\\n/\n/g' -e 's/&&/\n/g' -e 's/||/\n/g' -e 's/[;|]/\n/g')
  while IFS= read -r seg; do
    launch=0
    case "$seg" in
      *"orca worktree create"*|*"orca agent launch"*)
        # "--agent claude" as whole tokens (also --agent=claude)
        case " $seg " in
          *" --agent claude "*|*" --agent=claude "*|*" --agent \"claude\" "*|*" --agent 'claude' "*|*" --agent=\"claude\" "*|*" --agent='claude' "*) launch=1 ;;
        esac ;;
    esac
    # container-neutral fallback: `claude` as the command word (first word of the segment
    # after env assignments / env / command / nohup / exec / "(", bare or as a path), or the
    # quoted value of --command (`orca terminal create --command "claude ..."`), carrying
    # -w/--worktree. Quoted strings are replaced by a placeholder before matching, so a
    # quoted value (`-w "$ISSUE"`, `--model "m"`) still counts while flag-like text inside
    # the prompt does not.
    chk="$seg"
    if [ $launch = 0 ]; then
      w=${seg//\\t/ }   # @tsv turns a tab into the two characters \t
      while :; do
        case "$w" in
          [[:space:]]*|'('*) w=${w#?} ;;
          'env '*|'command '*|'nohup '*|'exec '*) w=${w#* } ;;
          *)
            first=${w%% *}
            case "$first" in
              [A-Za-z_]*=*) case "${first%%=*}" in *[!A-Za-z0-9_]*) break ;; esac; w=${w#"$first"} ;;
              *) break ;;
            esac ;;
        esac
      done
      cw=""
      first=${w%% *}
      case "$first" in
        claude|*/claude) [ "$w" != "$first" ] && cw=${w#* } ;;
      esac
      if [ -z "$cw" ]; then
        case "$seg" in
          *'--command "claude '*|*'--command="claude '*) cw=${seg#*--command*\"claude }; cw=${cw%%\"*} ;;
          *"--command 'claude "*|*"--command='claude "*) cw=${seg#*--command*\'claude }; cw=${cw%%\'*} ;;
        esac
      fi
      cw=" $(printf '%s' "$cw" | sed -e 's/"[^"]*"/Q/g' -e "s/'[^']*'/Q/g") "
      cw=${cw//\\t/ }
      case "$cw" in
        *" -w "*|*" --worktree "*|*" --worktree="*) launch=1; chk="$cw" ;;
      esac
    fi
    [ $launch = 1 ] || continue
    reason="claude-launch"
    has_model=0; has_effort=0
    case " $chk " in *" --model "[!-]*|*" --model="[!-]*) has_model=1 ;; esac
    case " $chk " in *" --effort "[!-]*|*" --effort="[!-]*) has_effort=1 ;; esac
    if [ $has_model = 0 ] || [ $has_effort = 0 ]; then
      decision="deny"
      [ $has_model = 0 ] && missing="$missing --model"
      [ $has_effort = 0 ] && missing="$missing --effort"
      reason="missing:${missing# }"
      break
    fi
  done <<EOF
$segs
EOF
fi

if [ -n "${ISSUE_SESSION_MODEL_LOG-}" ]; then
  printf '%s decision=%s reason=%s\n' "$(date +%T)" "$decision" "$reason" >> "$ISSUE_SESSION_MODEL_LOG"
fi

if [ "$decision" = "deny" ]; then
  cat >&2 <<MSG
BLOCKED by hook require-issue-session-model: 起 Claude issue session 的指令缺${missing}。
issue session 是 controller，不隨主對話的預設 model；沒帶旗標的 \`claude\` 會吃啟動當下 ~/.claude/settings.json 的 model。
規則見 ~/.claude/skills/worktree-session/references/cli.md「盤點 session 與 issue session」：\`orca worktree create ... --agent claude --model claude-opus-5-5 --effort medium --prompt ...\`（\`orca agent launch\` 同；fallback 為 \`claude -w <issue> -n issue-<issue> --model claude-opus-5-5 --effort medium ... "<brief>"\`，旗標寫在 prompt 之前）。
請補上旗標後重送；不要改用 \`orca terminal create\` 或其他方式繞過。
MSG
  exit 2
fi

exit 0
