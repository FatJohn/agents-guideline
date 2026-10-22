#!/bin/bash
# PreToolUse hook: auto-allow two narrow `git -C <path>` cleanup commands.
#
# Why: permission rules like `Bash(git -C * worktree remove *)` make Claude Code
# warn that a `*` before the subcommand also admits arbitrary options
# (`git -C -c core.pager=... `, `--exec-path`), and it warns even for
# `git -C $HOME/Projects/* ...`. This hook is the strict version of a
# "`-C` under ~/Projects" prefix rule: it only says allow for the exact shapes
#   git -C <path> worktree remove <arg>...
#   git -C <path> branch -D <arg>...
# and says nothing (prints nothing, exit 0) for everything else, so the normal
# permission flow (allow/ask/deny rules, prompts) decides.
#
# Decision table (stdin JSON from Claude Code PreToolUse):
#   - tool_name is not Bash                                   -> no opinion
#   - trimmed command has any char outside [A-Za-z0-9 _./:@%+=,-]
#     (covers ; & | ` $ ( ) < > # quotes backslash newline tab glob chars ~)
#                                                             -> no opinion
#   - tokens (split on spaces) are not exactly one of the two shapes above
#     (-C<path> glued, --git-dir, -c, extra options before -C ...) -> no opinion
#   - <path> must start with "$HOME/Projects/" (absolute, no ~), have a
#     remainder that is not just "." and "/" segments (so Projects/ itself,
#     Projects/. and Projects/./ are out), contain no ".." segment, not start with "-", and
#     be an existing directory ([ -d ])                       -> else no opinion
#   - at least one <arg>, and no <arg> may start with "-"     -> else no opinion
#     (so --force / -f never auto-allow; settings deny rules such as
#     `git worktree remove --force*` stay in charge. Per the docs, deny and ask
#     rules are still evaluated whatever a hook returns.)
#   everything matches -> stdout allow JSON, reason "allow-git-c-projects: <path>".
#
# Output format and stdin fields (official docs, Hooks reference, PreToolUse):
#   https://code.claude.com/docs/en/hooks  (formerly docs.claude.com/en/docs/claude-code/hooks)
#   stdin:  {"tool_name":"Bash","tool_input":{"command":"..."}, ...}
#   stdout: {"hookSpecificOutput":{"hookEventName":"PreToolUse",
#            "permissionDecision":"allow","permissionDecisionReason":"..."}}
#   "allow" skips the permission prompt; for "allow" the reason goes to the
#   debug log only. Exit code must be 0 for the JSON to be read.
#
# Fail-open on purpose: if jq is missing or stdin is unparsable we exit 1
# (non-blocking error, visible in the transcript) and the tool call goes through
# the normal permission flow (no allow is given).
#
# Optional audit log: set GIT_C_ALLOW_LOG=/path/to/file to append one line per
# decision (leave unset in normal use).
#
# Offline tests: tests/test-allow-git-c-projects.sh. Install and limits: docs/install.md.
#
# Needs: bash, jq, tr. No python. Works in macOS bash 3.2 and Git Bash.

# byte-wise character ranges in the whitelist below, whatever the user locale
export LC_ALL=C

if ! command -v jq >/dev/null 2>&1; then
  echo "allow-git-c-projects: jq not found, auto-allow is INACTIVE" >&2
  exit 1
fi

input=$(cat)

# @tsv escapes newline/tab/backslash/CR in the command as \n \t \\ \r, so a
# multi-line command can never look like a single clean line here.
verdict=$(printf '%s' "$input" | jq -r '
  [(.tool_name // "" | tostring), (.tool_input.command // "" | tostring)] | @tsv
' 2>/dev/null | tr -d '\r')

if [ -z "$verdict" ]; then
  echo "allow-git-c-projects: could not parse hook input, auto-allow did not run" >&2
  exit 1
fi

tool=${verdict%%$'\t'*}
cmd=${verdict#*$'\t'}
[ "$verdict" = "$tool" ] && cmd=""

decision="skip"
reason="-"
path="-"

check() {
  [ "$tool" = "Bash" ] || { reason="not-bash"; return; }

  # trim leading/trailing spaces
  cmd=${cmd#"${cmd%%[! ]*}"}
  cmd=${cmd%"${cmd##*[! ]}"}
  [ -n "$cmd" ] || { reason="empty"; return; }

  # whitelist of characters; anything else (control chars, quotes, $, ;, &, |,
  # redirects, globs, ~, backslash, newline, tab ...) is no opinion
  case "$cmd" in
    *[!A-Za-z0-9\ _./:@%+=,-]*) reason="unsafe-chars"; return ;;
  esac

  set -f
  # shellcheck disable=SC2086 # intentional word splitting, globbing is off
  set -- $cmd
  set +f

  [ $# -ge 6 ] || { reason="too-few-tokens"; return; }
  [ "$1" = "git" ] && [ "$2" = "-C" ] || { reason="not-git-C"; return; }
  p=$3
  case "$4 $5" in
    "worktree remove"|"branch -D") ;;
    *) reason="other-subcommand"; return ;;
  esac

  # path checks
  prefix="${HOME%/}/Projects/"
  case "$p" in
    "$prefix"?*) ;;
    *) reason="path-outside-projects"; return ;;
  esac
  case "/$p/" in
    */../*) reason="path-dotdot"; return ;;
  esac
  # remainder after the prefix made only of "." and "/" is Projects/ itself
  case "${p#"$prefix"}" in
    *[!./]*) ;;
    *) reason="path-is-projects-root"; return ;;
  esac
  [ -d "$p" ] || { reason="path-not-dir"; return; }

  # args after the subcommand: none may start with "-"
  shift 5
  for a in "$@"; do
    case "$a" in
      -*) reason="arg-starts-with-dash"; return ;;
    esac
  done

  decision="allow"
  path=$p
  reason="match"
}
check

if [ -n "${GIT_C_ALLOW_LOG-}" ]; then
  printf '%s decision=%s reason=%s path=%s\n' \
    "$(date +%T)" "$decision" "$reason" "$path" >> "$GIT_C_ALLOW_LOG"
fi

if [ "$decision" = "allow" ]; then
  jq -nc --arg r "allow-git-c-projects: $path" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"allow",permissionDecisionReason:$r}}'
fi

exit 0
