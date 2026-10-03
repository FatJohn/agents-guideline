#!/bin/bash
# PreToolUse hook: the MAIN conversation (controller) must not edit CI config.
#
# Rule (rules/10-dispatch.md, "Controller 工作迴圈"): CI/release config
# (.github/workflows, .github/actions) is not covered by the controller's
# small-fix exception; it goes through a worker. This hook enforces that
# mechanically.
#
# Decision table (stdin JSON from Claude Code PreToolUse):
#   - tool is Edit|Write|MultiEdit|NotebookEdit
#   - target path (file_path, or notebook_path) normalised to contain
#     /.github/workflows/ or /.github/actions/
#   - caller is the main conversation = stdin has NO agent_id
#     (subagent calls carry agent_id + agent_type; measured 2026-10-03,
#     see docs/install.md)
#   => exit 2 + message on stderr (tool call is blocked, message goes to model)
#   everything else => exit 0 (allow).
#
# Fail-open on purpose: if jq is missing or stdin is unparsable we exit 1
# (non-blocking error, visible in the transcript) and the tool call proceeds.
#
# Optional audit log: set CI_EDIT_GUARD_LOG=/path/to/file to append one line
# per decision (leave unset in normal use).
#
# Offline tests: tests/test-block-ci-edit.sh. Install and limits: docs/install.md.
#
# Needs: bash, jq, cat, tr. No python. Works in macOS bash 3.2 and Git Bash.

if ! command -v jq >/dev/null 2>&1; then
  echo "block-ci-edit: jq not found, CI edit guard is INACTIVE" >&2
  exit 1
fi

input=$(cat)

verdict=$(printf '%s' "$input" | jq -r '
  # lower-case, backslash -> slash, drop "" and "." segments, resolve ".."
  def norm:
    gsub("\\\\"; "/") | ascii_downcase | split("/")
    | reduce .[] as $s ([];
        if $s == "" or $s == "." then .
        elif $s == ".." then .[:-1]
        else . + [$s] end)
    | join("/");
  (.tool_name // "") as $t
  | (.tool_input.file_path // .tool_input.notebook_path // "") as $p
  | ((.agent_id // "") | if . == "" then "-" else . end) as $aid
  | ((.agent_type // "") | if . == "" then "-" else . end) as $atype
  | (("/" + ($p | norm) + "/") | test("/\\.github/(workflows|actions)/")) as $hit
  | (["Edit","Write","MultiEdit","NotebookEdit"] | index($t)) as $isedit
  | (if $isedit != null and $hit and $aid == "-" then "deny" else "allow" end)
    + "\t" + $aid + "\t" + $atype + "\t" + $t + "\t" + ($p | if . == "" then "-" else . end)
' 2>/dev/null | tr -d '\r')

if [ -z "$verdict" ]; then
  echo "block-ci-edit: could not parse hook input, CI edit guard did not run" >&2
  exit 1
fi

IFS=$'\t' read -r decision aid atype tool path <<EOF
$verdict
EOF

if [ -n "${CI_EDIT_GUARD_LOG-}" ]; then
  printf '%s decision=%s agent_id=%s agent_type=%s tool=%s path=%s\n' \
    "$(date +%T)" "$decision" "$aid" "$atype" "$tool" "$path" >> "$CI_EDIT_GUARD_LOG"
fi

if [ "$decision" = "deny" ]; then
  cat >&2 <<MSG
BLOCKED by hook block-ci-edit: 主對話（controller）不得直接修改 CI 設定（${path}）。
規則見 rules/10-dispatch.md「Controller 工作迴圈」：.github/workflows、.github/actions 不屬小修例外，必須走「核定 plan -> 派 worker 實作 -> controller read-back -> 一次 review/verifier」。
請改派 worker subagent 修改此檔；不要改用 Bash（sed、heredoc）繞過。
MSG
  exit 2
fi

exit 0
