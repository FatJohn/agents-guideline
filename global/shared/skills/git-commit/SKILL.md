---
name: git-commit
description: 寫 git commit message 或 squash merge 標題時使用：commit 全英文、Conventional Commits 格式。要 commit、amend、改 commit 訊息、squash merge 時觸發，中英措辭皆可（「提交」「commit」「squash」）。Use when writing a commit message or a squash-merge title.
---

# git-commit — commit message 的固定格式

專案 `CLAUDE.md`／`AGENTS.md`／`CONTRIBUTING.md` 有自己的 commit 或註解慣例時以專案為準；沒有明文時看既有慣例（見下）；都沒有才用本格式。

commit message（subject 與 body）全英文，subject 符合 Conventional Commits：`type: 小寫祈使句`，scope 可省略（`type(scope):` 同樣合格），type 限 `build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test`。對話與 issue 仍是繁體中文；PR title 與 body 依 `create-pr` skill 2.2「repo 規定與既有慣例」；程式註解預設繁體中文，但 repo 既有註解以英文為主時跟隨英文。

例：`fix: reject empty token in refresh flow`、`feat(auth): add token rotation`。

## 既有慣例怎麼判

專案沒有明文規定時，用指令看既有慣例：

```bash
# commit 標題慣例：最近 20 個非 merge commit 的標題
git log --no-merges -n 20 --format=%s
# 註解語言：含 CJK 的註解行數 vs 全部註解行數（以 Go 的 // 為例，其他語言換註解符號）
git grep -cP '^\s*//.*[\x{4e00}-\x{9fff}]' -- '*.go' | awk -F: '{s+=$2} END{print s+0}'
git grep -c '^\s*//' -- '*.go' | awk -F: '{s+=$2} END{print s+0}'
```

判準：過半是哪一種就跟隨哪一種；樣本不足（commit < 5、註解 < 20 行）或看不出多數，視為無慣例，用本 skill 預設。

## squash merge

PR title 依 `create-pr` skill 預設用中文不加 prefix，而 `gh pr merge --squash` 預設拿 PR title 當 commit 標題，所以 squash merge 一律用 `-t` 覆寫成本 skill 的格式；指令與後果見 `~/.claude/skills/create-pr/SKILL.md` §2.8。

**不算違規**：PR title 本身已符合本 skill 的格式（例如 release-please 開的 Release PR `chore(main): release x.y.z`），且 repo 文件規定 merge 時不覆寫標題，照 repo 文件不加 `-t`。PR title 已照 repo 慣例是英文 Conventional Commits 時同屬此例外。
