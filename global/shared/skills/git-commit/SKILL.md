---
name: git-commit
description: 寫 git commit message 或 squash merge 標題時使用：commit 全英文、Conventional Commits 格式。要 commit、amend、改 commit 訊息、squash merge 時觸發，中英措辭皆可（「提交」「commit」「squash」）。Use when writing a commit message or a squash-merge title.
---

# git-commit — commit message 的固定格式

專案 `CLAUDE.md`／`AGENTS.md` 有自己的 commit 慣例時以專案為準；沒有才用本格式。

commit message（subject 與 body）全英文，subject 符合 Conventional Commits：`type: 小寫祈使句`，scope 可省略（`type(scope):` 同樣合格），type 限 `build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test`。對話、PR title 與 body、程式註解、issue 仍是繁體中文。

例：`fix: reject empty token in refresh flow`、`feat(auth): add token rotation`。

## squash merge

PR title 依 `create-pr` skill 用中文不加 prefix，而 `gh pr merge --squash` 預設拿 PR title 當 commit 標題，所以 squash merge 一律用 `-t` 覆寫成本 skill 的格式；指令與後果見 `~/.claude/skills/create-pr/SKILL.md` §2.8。

**不算違規**：PR title 本身已符合本 skill 的格式（例如 release-please 開的 Release PR `chore(main): release x.y.z`），且 repo 文件規定 merge 時不覆寫標題，照 repo 文件不加 `-t`。
