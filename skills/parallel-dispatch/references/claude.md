# Claude Code 平台契約

本 reference 配合 [../SKILL.md](../SKILL.md) 使用，保留 Claude Code 的既有隔離例外與 harness 事實；不適用於 Codex。

## 派工與 worktree

- 一個 controller session 一次派多個 Agent 呼叫，每片設 `isolation: worktree`；一般實作是 `worker`（`model: sonnet`），切片驗收是 fresh `verifier`（`model: opus`）。
- worker prompt 明寫隔離 worktree 例外：可在自己的 branch commit、完成前 rebase 到最新 base 一次並自行解純文字 conflict，解完重跑機械驗證，但不得 push；回報 worktree 絕對路徑、branch、HEAD SHA，且仍是該 worktree 唯一寫入者。
- controller read-back：`git worktree list`、`git -C <worktree> log -1 --format=%H`、`git -C <worktree> status --short`。同一 working tree 僅一寫入者；read-only agent 與寫入者共用 tree 時，其測試／build 量測無效。
- worktree branch 為 `worktree-<name>` 時，controller 以 `git -C <worktree> push origin worktree-<name>:refs/heads/<repo 慣例 branch>` 建 PR，並走 `create-pr` skill；所有 push、PR、merge、tracker comment 都需當次授權並由 controller 做。

## 整合驗收與清理

共通 SKILL §2 的 fresh verifier 使用 `verifier`（`model: opus`）；在 integration tree 驗跨切片互動、全新 checkout 與 CI job／產物依賴。範圍外發現依 `~/.claude/rules/10-dispatch.md` §5 登記，不能擴修。

清理採共通 SKILL §2 的證據條件；確認後 controller 在主 repo 執行 `git worktree remove <絕對路徑>` 與 `git branch -D worktree-<name>`。不可用 commit 數判定 squash 後是否落地。

## Harness 事實與手動 session

Claude Code 2.1.267（2026-09-12 查證）的 `isolation: worktree` 建於 `<repo>/.claude/worktrees/<name>/`，從 controller 當下 HEAD 開出、branch 為 `worktree-<name>`；無改動會連 branch 移除為當日空手實測，有改動會保留僅見官方文件、未另實測。harness 不回報路徑，故 worker 必須回報。官方未提供多 worktree 合併方式；`.claude/worktrees/` 也不會自動進 `.gitignore`，首次使用先確認忽略。

同日 3 片 S／M 實跑樣本：每片 2–4 輪修正加驗收（含機械結案輪），共 12 次 agent 呼叫、約 1.6M subagent token、派工到開 PR 約 100 分鐘；這是成本參考，不是加速宣稱。fresh 驗收仍受 `<REPO>/rules/20-judgment.md` §2「修正與驗收輪次」三輪回報點約束。

人手多 session 時 worktree 放 `<repo>/.claude/worktrees/<name>/`，但仍由使用者手動建立 integration tree、跑完整測試。Workflow 工具的 `agent()` 未確認支援 `isolation`，且需使用者當次明確要求，本流程不使用。
