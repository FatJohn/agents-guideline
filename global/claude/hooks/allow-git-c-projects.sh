#!/bin/bash
# PreToolUse hook: auto-allow two narrow `git -C <path>` cleanup commands.
#
# Why: permission rules like `Bash(git -C * worktree remove *)` make Claude Code
# warn that a `*` before the subcommand also admits arbitrary options
# (`git -C -c core.pager=... `, `--exec-path`), and it warns even for
# `git -C $HOME/Projects/* ...`. This hook is the strict version of a
# "`-C` under the projects root" prefix rule: it only says allow for the exact shapes
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
#   - <path> must start with "<root>/" (absolute, no ~), have a remainder that
#     is not just "." and "/" segments (so <root>/ itself, <root>/. and
#     <root>/./ are out), contain no ".." segment, not start with "-", and
#     be an existing directory ([ -d ])                       -> else no opinion
#     <root> is "$HOME/Projects" unless GIT_C_ALLOW_ROOT is set (see below).
#   - at least one <arg>, and no <arg> may start with "-"     -> else no opinion
#     (so --force / -f never auto-allow; settings deny rules such as
#     `git worktree remove --force*` stay in charge. Per the docs, deny and ask
#     rules are still evaluated whatever a hook returns.)
#   everything matches -> stdout allow JSON, reason "allow-git-c-projects: <path>".
#
# GIT_C_ALLOW_ROOT (optional) replaces <root>; it does not add a second root.
#   - unset or empty -> <root> = "${HOME%/}/Projects" (the original behaviour).
#   - set -> trailing "/" are dropped, then it is used only if ALL hold:
#       * only chars from the command whitelist [A-Za-z0-9_./:@%+=,-]
#         (no space, backslash, ~ or $)
#       * absolute: starts with "/" or with "X:/" (X a drive letter), so a
#         Windows root is written "D:/Projects"; a backslash spelling is
#         rejected, while "/d/Projects" is a plain absolute path and is
#         accepted (then only commands spelled "/d/Projects/..." match)
#       * no ".." segment and no "." segment
#       * something remains after the leading "/" or "X:/" (so "/", "//",
#         "C:/" and "C:" are rejected)
#     Otherwise it falls back to the default root (it does not switch the hook
#     off). <path> is compared as a plain string, so a command that spells the
#     same directory differently (backslashes, "/d/Projects/...") is no opinion.
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
# decision (leave unset in normal use). The line ends with
# root=default|env|default-invalid-env, where <root> came from.
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

# root of the allowed tree: "$HOME/Projects" unless GIT_C_ALLOW_ROOT passes
# every check below, in which case the env value replaces it
root="${HOME%/}/Projects"
root_src="default"
if [ -n "${GIT_C_ALLOW_ROOT-}" ]; then
  root_src="default-invalid-env"
  env_root=$GIT_C_ALLOW_ROOT
  while :; do
    case "$env_root" in
      */) env_root=${env_root%/} ;;
      *) break ;;
    esac
  done
  env_rest=""
  env_ok=1
  case "$env_root" in
    *[!A-Za-z0-9_./:@%+=,-]*) env_ok=0 ;;
    /*) env_rest=${env_root#/} ;;
    [A-Za-z]:/*) env_rest=${env_root#?:/} ;;
    *) env_ok=0 ;;
  esac
  # "/", "//" and "C:/" would leave nothing here; the strip loop and the case
  # patterns above already reject them, this keeps the rule explicit
  [ -n "$env_rest" ] || env_ok=0
  case "/$env_root/" in
    */../*|*/./*) env_ok=0 ;;
  esac
  if [ "$env_ok" = 1 ]; then
    root=$env_root
    root_src="env"
  fi
fi

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
  prefix="$root/"
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
  printf '%s decision=%s reason=%s path=%s root=%s\n' \
    "$(date +%T)" "$decision" "$reason" "$path" "$root_src" >> "$GIT_C_ALLOW_LOG"
fi

if [ "$decision" = "allow" ]; then
  jq -nc --arg r "allow-git-c-projects: $path" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"allow",permissionDecisionReason:$r}}'
fi

exit 0
