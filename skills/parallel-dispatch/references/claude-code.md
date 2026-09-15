# Adapter：Claude Code 同 session subagent

配合 [../SKILL.md](../SKILL.md) §9 的 adapter 契約使用；只提供 launch、follow-up、query status、collect、stop、workspace 與角色分流，不改變 SKILL 任何一步。不適用於 Codex。

| 契約項目 | 本 adapter 的做法 |
|---|---|
| launch | 一個 controller session 在**同一則訊息**發多個 `Agent` 呼叫，每片一個；實作用 `worker`（`model: sonnet`），切片與整合驗收用 fresh `verifier`（`model: opus`）。subagent 在 controller session 內跑，沒有獨立 terminal |
| workspace | 每個寫入型 Agent 呼叫設 `isolation: worktree`；harness 自動建 worktree，行為事實見 `<REPO>/docs/harness-facts.md` |
| query status | subagent 完成時回報一次；期間狀態靠 `git worktree list`、`git -C <wt> status --short`、`git -C <wt> log -1 --format=%H` read-back |
| follow-up | 同一 agent 用 `SendMessage` 續派（保留其 context），或帶原 finding 與 diff 另派 fresh agent |
| collect | subagent 回傳的最後訊息就是 worker report（必含 Location 欄的 worktree 路徑、branch、HEAD）；長輸出由 worker 落檔到 brief 指定的 `<log-dir>` |
| stop | 背景 subagent 用當下工具清單裡的停止工具（現查有無 `TaskStop`）終止；同步呼叫的 subagent 無法中途停止，只能等回傳。停止後以 `git -C <wt> status --short`＋`rev-parse HEAD` 做兩次 read-back，**相隔至少 60 秒**且期間該 agent 未回傳任何訊息，兩次都無變化才算停；否則依 SKILL §8 換新 worktree 重派 |

## 派工與 worktree

- harness 不回報 worktree 路徑，worker prompt 必須要求回報 worktree 絕對路徑、branch、HEAD SHA（worker report 的 Location 欄）。
- **隔離 worktree 例外**（`<REPO>/agents/worker.md` 規則 5）：plan 明寫「本任務在隔離 worktree（`isolation: worktree`）」時，worker 可在該 worktree 自己的 branch commit，完成前 rebase 到最新 base 一次並自行解純文字 conflict，解完重跑機械驗證；push、開 PR、開 issue、merge 仍禁止，且仍是該 worktree 唯一寫入者。
- controller read-back：`git worktree list`、`git -C <wt> log -1 --format=%H`、`git -C <wt> status --short`、`git -C <wt> diff <base>...HEAD --stat`。同一 working tree 僅一寫入者；read-only agent 與寫入者共用 tree 時，其測試／build 量測無效（`worktree.md`「何時需要」）。
- worktree branch 為 `worktree-<name>` 時，controller 以 `git -C <wt> push origin worktree-<name>:refs/heads/<repo 慣例 branch>` 推出並走 `create-pr` skill；所有 push、PR、merge、tracker comment 都需當次授權並由 controller 做。
- `Workflow` 工具的 `agent()` 未確認支援 `isolation`，且需使用者當次明確要求，本流程不使用。

## 驗收角色分流

切片驗收與 SKILL §6 第 9 步的整合 verifier 都用 `verifier`（`model: opus`）；升 `model: fable` 的訊號與授權見 `<REPO>/rules/10-dispatch.md` §5「驗證不自驗」。整合 verifier 在 integration tree 的乾淨環境跑；範圍外發現依 `<REPO>/rules/10-dispatch.md` §5 登記，不擴修。

## 清理

採 `worktree.md`「清理的證據條件」；確認後 controller 在主 repo 執行 `git worktree remove <絕對路徑>` 與 `git branch -D worktree-<name>`。不可用 commit 數判定 squash 後是否落地。

## 已知成本

2026-09-12 的 3 片 S／M 實跑樣本（每片 2–4 輪、12 次 agent 呼叫、約 1.6M subagent token、約 100 分鐘）記在 `<REPO>/docs/harness-facts.md`；這是成本參考，不是加速宣稱。
