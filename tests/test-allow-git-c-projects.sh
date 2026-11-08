#!/bin/bash
# Offline assertions for allow-git-c-projects.sh (synthetic PreToolUse stdin, no claude needed).
# usage: bash tests/test-allow-git-c-projects.sh [path/to/allow-git-c-projects.sh]
# default: ../global/claude/hooks/allow-git-c-projects.sh relative to this file. Needs bash + jq.
HOOK=${1:-$(dirname "$0")/../global/claude/hooks/allow-git-c-projects.sh}
# a Windows path (C:/... or C:\...) is absolute too; do not prefix $PWD to it
case "$HOOK" in /*|[A-Za-z]:[/\\]*) ;; *) HOOK="$PWD/$HOOK" ;; esac
# the existing cases run with the root override unset, whatever the caller exports
unset GIT_C_ALLOW_ROOT
TMPHOME=$(mktemp -d "${TMPDIR:-/tmp}/allowgitc.XXXXXX") || exit 1
trap 'rm -rf "$TMPHOME"' EXIT
mkdir -p "$TMPHOME/Projects/foo" "$TMPHOME/outside" "$TMPHOME/alt/foo"
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
# ce root name want command: like c with GIT_C_ALLOW_ROOT=root for the hook
ce(){ export GIT_C_ALLOW_ROOT="$1"; c "[ROOT=$1] $2" "$3" "$4"; unset GIT_C_ALLOW_ROOT; }
# lg root command: print the root= field of the audit log line the hook writes
lg(){
  rm -f "$TMPHOME/audit.log"
  if [ -n "$1" ]; then export GIT_C_ALLOW_ROOT="$1"; fi
  printf '%s' "$(cmdjson "$2")" | HOME="$H" GIT_C_ALLOW_LOG="$TMPHOME/audit.log" bash "$HOOK" >/dev/null 2>&1
  unset GIT_C_ALLOW_ROOT
  sed -n 's/.* root=//p' "$TMPHOME/audit.log"
}
check_log(){ # name want got
  if [ "$3" = "$2" ]; then echo "PASS log  $1 -> $2"; else echo "FAIL log got=$3 want=$2  $1"; fail=$((fail+1)); fi
}

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
c "other subcommand (pull) -> skip"     skip  "git -C $H/Projects/foo pull origin a"
c "branch -d lowercase -> skip"         skip  "git -C $H/Projects/foo branch -d a"
c "env prefix -> skip"                  skip  "GIT_DIR=/x git -C $H/Projects/foo branch -D a"
c "non-git command -> skip"             skip  "rm -rf $H/Projects/foo"
# --- push: git -C <path> push [-u|--set-upstream] [<remote> [<refspec>...]] ---
P="$H/Projects/foo"
c "push bare -> allow"                  allow "git -C $P push"
c "push remote -> allow"                allow "git -C $P push origin"
c "push remote branch -> allow"         allow "git -C $P push origin feature/x"
c "push -u remote branch -> allow"      allow "git -C $P push -u origin feature/x"
c "push --set-upstream -> allow"        allow "git -C $P push --set-upstream origin feature/x"
c "push -u alone -> allow"              allow "git -C $P push -u"
c "push src:dst refspec -> allow"       allow "git -C $P push origin HEAD:refs/heads/x"
c "push several refspecs -> allow"      allow "git -C $P push origin a b:c"
c "push + inside branch name -> allow"  allow "git -C $P push origin feature/a+b"
c "push under Projects/foo/. -> allow"  allow "git -C $P/. push origin a"
for bad in --force -f --force-with-lease --force-with-lease=a --force-if-includes --delete -d \
           --mirror --all --tags --prune "-o ci.skip" --push-option=x --receive-pack=x --exec=x \
           --no-verify --dry-run -n --atomic --follow-tags --repo=x -- - -uf -fu --set-upstream=origin --u -U; do
  c "push option $bad before remote -> skip" skip "git -C $P push $bad origin a"
  c "push option $bad after -u -> skip"      skip "git -C $P push -u $bad origin a"
  c "push option $bad after refspec -> skip" skip "git -C $P push origin a $bad"
done
c "push -u twice -> skip"               skip  "git -C $P push -u -u origin a"
c "push -u not first -> skip"           skip  "git -C $P push origin -u a"
c "push -u at end -> skip"              skip  "git -C $P push origin a -u"
c "push +refspec -> skip"               skip  "git -C $P push origin +a"
c "push +src:dst -> skip"               skip  "git -C $P push origin +a:b"
c "push -u +refspec -> skip"            skip  "git -C $P push -u origin +a"
c "push second refspec + -> skip"       skip  "git -C $P push origin a +b"
c "push :dst delete -> skip"            skip  "git -C $P push origin :a"
c "push -u :dst delete -> skip"         skip  "git -C $P push -u origin :a"
c "push second refspec : -> skip"       skip  "git -C $P push origin a :b"
c "push bare : (matching) -> skip"      skip  "git -C $P push origin :"
c "push bare + -> skip"                 skip  "git -C $P push origin +"
c "push remote starting + -> skip"      skip  "git -C $P push +origin a"
c "push remote starting : -> skip"      skip  "git -C $P push :origin a"
c "push -c before push -> skip"         skip  "git -C $P -c core.sshCommand=x push origin a"
c "push -c as -C path -> skip"          skip  "git -C -c core.sshCommand=x push origin a"
c "push -c before -C -> skip"           skip  "git -c core.sshCommand=x -C $P push origin a"
c "push env prefix -> skip"             skip  "GIT_SSH_COMMAND=x git -C $P push origin a"
c "push ; chaining -> skip"             skip  "git -C $P push origin a; id"
c "push && chaining -> skip"            skip  "git -C $P push origin a && id"
c "push \$(...) -> skip"               skip  "git -C $P push origin \$(id)"
c "push outside Projects -> skip"       skip  "git -C $H/outside push origin a"
c "push Projects/ itself -> skip"       skip  "git -C $H/Projects/ push origin a"
c "push path with .. -> skip"           skip  "git -C $P/../../outside push origin a"
c "push path missing -> skip"           skip  "git -C $H/Projects/nope push origin a"
c "push tilde path -> skip"             skip  "git -C ~/Projects/foo push origin a"
c "push -C glued -> skip"               skip  "git -C$P push origin a"
c "push-x subcommand -> skip"           skip  "git -C $P push-x origin a"
c "Push capitalised -> skip"            skip  "git -C $P Push origin a"
c "git -C <path> alone -> skip"         skip  "git -C $P"
# --- read-only and index subcommands: flags must be on the per-subcommand list ---
git init -q "$P" && git -C "$P" remote add origin /nonexistent || exit 1
for ok in "status" "status --short" "status -sb" "status --porcelain=v2 --branch -uall" "status -- src" \
          "diff" "diff --stat origin/main...HEAD" "diff --cached --name-only" "diff --name-only -z a HEAD -- x/y" "diff -U0 --no-color a b" "diff a...b" "diff a..b -- x/y" \
          "log" "log --oneline -5" "log --oneline -n 5 --all --graph" "log --format=%H -1 main" "log --max-count=3 --since=2026-01-01 --name-only" \
          "show" "show HEAD:a/b.txt" "show --stat --format=%s HEAD" "show -s --format=%H" \
          "rev-parse HEAD" "rev-parse --show-toplevel" "rev-parse --abbrev-ref HEAD" "rev-parse --short=7 HEAD" "rev-parse --git-common-dir" \
          "rev-list --count origin/main..HEAD" "rev-list --left-right --count a...b" \
          "merge-base a b" "merge-base --is-ancestor a b" "ls-files" "ls-files -z --cached --others --exclude-standard" "ls-files -v" \
          "fetch" "fetch origin" "fetch origin main" "fetch origin refs/heads/a" "fetch --prune origin" "fetch -q --all" \
          "add a b/c" "add ." "add -A" "add -u -- src" \
          "commit -m word" "commit -am word" "commit -a -m word" "commit -m word -- a" "commit -F /tmp/msg" "commit --file=/tmp/msg"; do
  c "$ok -> allow" allow "git -C $P $ok"
done
for bad in "diff --output=/tmp/x" "diff --outp=/tmp/x" "diff --ext-diff" "diff --no-index /etc/passwd /tmp/y" "diff -O/tmp/o" \
           "log --output=/tmp/x" "log --ext-diff -p" "log --exec=x" "log --outpu=/tmp/x" "show --output=/tmp/x" "show --ext-diff" \
           "status --output=/tmp/x" "status -c" "rev-parse --parseopt" "rev-parse --sq-quote a" "rev-list --stdin" "ls-files --format=x" \
           "merge-base --bogus a b" \
           "fetch --upload-pack=/tmp/x origin" "fetch --force origin" "fetch -f origin" "fetch origin +main:main" "fetch origin main:main" \
           "fetch origin +a" "fetch ext::sh" "fetch https://example.com/x.git" "fetch /tmp/x" "fetch ../x" "fetch ." \
           "fetch --recurse-submodules origin" "fetch -o x origin" "fetch --unshallow origin" \
           "add -f a" "add --force a" "add --chmod=+x a" "add --pathspec-from-file=/tmp/x" "add -p" \
           "commit --amend" "commit --amend -m word" "commit -m word --amend" "commit --no-verify -m word" "commit -n -m word" \
           "commit -c HEAD" "commit -C HEAD" "commit --fixup=HEAD" "commit --squash=HEAD" "commit --author=x -m word" "commit -F -" "commit -m --amend" \
           "diff /etc/hosts /tmp/y" "diff -- /etc/hosts /tmp/y" "diff ../../a ../../b" "diff x/../../a b" "diff .." \
           "fetch sub" "fetch bun" "fetch origin tag v1" "fetch nosuchremote main" \
           "commit" "commit -a" "commit -s" "commit --" "commit -- -m" "commit -- --file=x" "commit -a -- -m" "diff C:/a D:/b" \
           "reset --hard" "reset HEAD" "clean -fdx" "checkout main" "checkout -- a" "rebase main" "config user.name x" "config --get user.name" "stash"; do
  c "$bad -> skip" skip "git -C $P $bad"
done
for s in status diff log show rev-parse rev-list merge-base ls-files fetch add commit; do
  c "$s: -c after path -> skip"       skip "git -C $P -c core.pager=x $s"
  c "$s: --exec-path after path -> skip" skip "git -C $P --exec-path=/tmp/x $s"
  c "$s: --git-dir after path -> skip" skip "git -C $P --git-dir=/tmp/x $s"
  c "$s: -c before -C -> skip"        skip "git -c core.pager=x -C $P $s"
  c "$s: -c as -C path -> skip"       skip "git -C -c core.pager=x $s"
  c "$s: outside Projects -> skip"    skip "git -C $H/outside $s"
  c "$s: Projects root -> skip"       skip "git -C $H/Projects/ $s"
  c "$s: chaining -> skip"            skip "git -C $P $s; id"
  c "$s: capitalised -> skip"         skip "git -C $P $(printf '%s' "$s" | tr 'a-z' 'A-Z')"
done
c "quoted commit message -> skip"       skip "git -C $P commit -m \"two words\""
c "HEAD~1 -> skip"                      skip "git -C $P diff HEAD~1"
c "env prefix on diff -> skip"          skip "GIT_EXTERNAL_DIFF=x git -C $P diff"
c "redirect on log -> skip"             skip "git -C $P log > /tmp/x"
c "status-x subcommand -> skip"         skip "git -C $P status-x"
ce "$H/alt" "status under env root -> allow" allow "git -C $H/alt/foo status"
ce "$H/alt" "status env root replaces default -> skip" skip "git -C $P status"
ce "$H/alt" "push under env root -> allow" allow "git -C $H/alt/foo push -u origin a"
ce "$H/alt" "push env root replaces default -> skip" skip "git -C $P push origin a"
ce "$H/alt" "push env root, --force -> skip" skip "git -C $H/alt/foo push --force origin a"
tl "UTF-8 locale, e-acute arg -> skip"  skip  "$(cmdjson "git -C $H/Projects/foo branch -D é")"
tl "UTF-8 locale, fullwidth arg -> skip" skip "$(cmdjson "git -C $H/Projects/foo branch -D ａ")"
tl "UTF-8 locale, ascii arg -> allow"   allow "$(cmdjson "git -C $H/Projects/foo branch -D a")"
t "tool_name Edit -> skip"              skip  "$(jq -nc --arg c "git -C $H/Projects/foo branch -D a" '{tool_name:"Edit",tool_input:{command:$c}}')"
t "missing tool_input -> skip"          skip  '{"tool_name":"Bash"}'
t "garbage stdin -> fail-open exit 1"   exit1 'not json'
t "empty stdin -> fail-open exit 1"     exit1 ''

# --- GIT_C_ALLOW_ROOT: replaces $HOME/Projects (valid values), else falls back to it ---
A="$H/alt"
WT="worktree remove a"
ce "$A" "worktree remove under env root -> allow" allow "git -C $A/foo worktree remove $A/foo/.wt/a"
ce "$A" "branch -D under env root -> allow"       allow "git -C $A/foo branch -D feature/x"
ce "$A" "env root is replaced, not added -> skip" skip  "git -C $H/Projects/foo $WT"
ce "$A" "env root itself -> skip"                 skip  "git -C $A $WT"
ce "$A" "env root/ itself -> skip"                skip  "git -C $A/ $WT"
ce "$A" "env root/. -> skip"                      skip  "git -C $A/. branch -D a"
ce "$A" "env root/foo/../.. -> skip"              skip  "git -C $A/foo/../.. $WT"
ce "$A" "env root, nonexistent dir -> skip"       skip  "git -C $A/nope $WT"
ce "$A" "env root, --force arg -> skip"           skip  "git -C $A/foo worktree remove --force a"
ce "$A" "env root, outside dir -> skip"           skip  "git -C $H/outside $WT"
ce "$A/" "env root with trailing / = without -> allow" allow "git -C $A/foo branch -D a"
ce "$A/" "env root with trailing / still replaces -> skip" skip "git -C $H/Projects/foo branch -D a"
ce "$A//" "env root with trailing // -> allow"    allow "git -C $A/foo branch -D a"
# empty = unset
ce "" "empty env -> default root allow"           allow "git -C $H/Projects/foo branch -D a"
ce "" "empty env -> alt not allowed"              skip  "git -C $A/foo branch -D a"
# invalid values fall back to the default root (they do not disable the hook, nor widen it)
for bad in "/" "//" "relative/x" "$A/../alt" "$A/./alt" "$H/al t" "C:" "C:/" "C:\\x" "D:\\Projects" "~/alt" "$A/.." "$A/." "/." "$A\$x" "$H/alt;id" "-C"; do
  ce "$bad" "invalid env falls back: default root allow" allow "git -C $H/Projects/foo branch -D a"
  ce "$bad" "invalid env falls back: alt skip"           skip  "git -C $A/foo branch -D a"
done
# invalid root '/' must not turn the whole filesystem into an allowed root
ce "/" "env '/' does not allow /tmp-like dirs" skip "git -C $H/outside branch -D a"
# audit log records where the root came from
check_log "default root"      default             "$(lg "" "git -C $H/Projects/foo branch -D a")"
check_log "valid env root"    env                 "$(lg "$A" "git -C $A/foo branch -D a")"
check_log "invalid env root"  default-invalid-env "$(lg "$A/../alt" "git -C $H/Projects/foo branch -D a")"
# Windows-style root (C:/...): only where cygpath can spell the temp dir that way
if command -v cygpath >/dev/null 2>&1; then
  M=$(cygpath -m "$A")
  case "$M" in
    [A-Za-z]:/*)
      drive=$(printf '%s' "${M%%:*}" | tr 'A-Z' 'a-z')
      U="/$drive/${M#?:/}"
      ce "$M" "drive-letter root, same spelling -> allow"  allow "git -C $M/foo branch -D a"
      ce "$M" "drive-letter root, /c/ spelling -> skip"    skip  "git -C $U/foo branch -D a"
      ce "$U" "/c/ spelling root, /c/ spelling -> allow"   allow "git -C $U/foo branch -D a"
      ce "$U" "/c/ spelling root, C:/ spelling -> skip"    skip  "git -C $M/foo branch -D a"
      ce "$M" "drive-letter root, root itself -> skip"     skip  "git -C $M $WT"
      ce "$M" "drive-letter root, .. -> skip"              skip  "git -C $M/foo/../foo $WT"
      check_log "drive-letter env root" env "$(lg "$M" "git -C $M/foo branch -D a")"
      ;;
    *) echo "SKIP drive-letter root (cygpath -m gave $M)" ;;
  esac
else
  echo "SKIP drive-letter root (no cygpath)"
fi
echo "failures=$fail"; [ "$fail" = 0 ]
