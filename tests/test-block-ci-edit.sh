#!/bin/bash
# Offline assertions for block-ci-edit.sh (synthetic PreToolUse stdin, no claude needed).
# usage: bash tests/test-block-ci-edit.sh [path/to/block-ci-edit.sh]
# default: ../hooks/block-ci-edit.sh relative to this file. Needs bash + jq.
HOOK=${1:-$(dirname "$0")/../hooks/block-ci-edit.sh}
fail=0
t(){ # name expected_exit json
  printf '%s' "$3" | bash "$HOOK" >/dev/null 2>&1; got=$?
  if [ "$got" = "$2" ]; then echo "PASS exit=$got  $1"; else echo "FAIL exit=$got (want $2)  $1"; fail=$((fail+1)); fi
}
t "main Edit abs workflows -> deny"        2 '{"tool_name":"Edit","tool_input":{"file_path":"/r/.github/workflows/x.yml"}}'
t "main Write relative workflows -> deny"  2 '{"tool_name":"Write","tool_input":{"file_path":".github/workflows/x.yml"}}'
t "main Edit actions -> deny"              2 '{"tool_name":"Edit","tool_input":{"file_path":"/r/.github/actions/a/action.yml"}}'
t "main NotebookEdit notebook_path -> deny" 2 '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"/r/.github/workflows/n.ipynb"}}'
t "main MultiEdit -> deny"                 2 '{"tool_name":"MultiEdit","tool_input":{"file_path":"/r/.github/workflows/x.yml"}}'
t "main Windows backslash -> deny"         2 '{"tool_name":"Edit","tool_input":{"file_path":"D:\\r\\.github\\workflows\\x.yml"}}'
t "main dotdot traversal -> deny"          2 '{"tool_name":"Edit","tool_input":{"file_path":"/r/.github/foo/../workflows/x.yml"}}'
t "main mixed case -> deny"                2 '{"tool_name":"Edit","tool_input":{"file_path":"/r/.GitHub/Workflows/x.yml"}}'
t "main other file -> allow"               0 '{"tool_name":"Edit","tool_input":{"file_path":"/r/README.md"}}'
t "main .github/ISSUE_TEMPLATE -> allow"   0 '{"tool_name":"Edit","tool_input":{"file_path":"/r/.github/ISSUE_TEMPLATE/a.md"}}'
t "main Read of workflow -> allow"         0 '{"tool_name":"Read","tool_input":{"file_path":"/r/.github/workflows/x.yml"}}'
t "subagent Edit workflow -> allow"        0 '{"tool_name":"Edit","agent_id":"a1","agent_type":"worker","tool_input":{"file_path":"/r/.github/workflows/x.yml"}}'
t "garbage stdin -> fail-open exit 1"      1 'not json'
echo "failures=$fail"; [ "$fail" = 0 ]
