# Adapter：Claude Code 同 session subagent

配合 [../SKILL.md](../SKILL.md) §9 的 adapter 契約使用；只提供 launch、follow-up、query status、collect、stop、workspace 與角色分流，不改變 SKILL 任何一步。不適用於 Codex。

| 契約項目 | 本 adapter 的做法 |
|---|---|
| launch | 一個 controller session 在**同一則訊息**發多個 `Agent` 呼叫，每片一個；實作用 `worker`（`model: sonnet`；A/B 對照片改派 `worker-opus`，不帶 `model`，見 `~/.claude/rules/10-dispatch.md` §0），切片與整合驗收用 fresh `verifier`（`model: opus`）。subagent 在 controller session 內跑，沒有獨立 terminal |
| workspace | 平行寫入型 Agent 呼叫設 `isolation: worktree`；fresh／continue 的同 worktree 序列交接是明確例外，fresh prompt 必須綁定 slice worktree 絕對路徑，不自動建立空 worktree；若另開 worktree，controller 先從已核對的 candidate checkpoint 建立並 read-back。harness 行為事實見 `<REPO>/docs/harness-facts.md` |
| query status | subagent 完成時回報一次；期間狀態靠 `git worktree list`、`git -C <wt> status --short`、`git -C <wt> log -1 --format=%H` read-back |
| counter | 完成通知 `<usage>` 帶三個欄位：`subagent_tokens`（≈ 該 agent 交回當下的 context 大小；2026-09-18 逐筆對 subagent jsonl 的 usage 核過）、`tool_uses`（該輪工具呼叫數，不等於模型 request）、`duration_ms`。fresh／continue 看 `subagent_tokens`；續用時它只會再長。通知缺欄位就標 `unknown`，不可猜，也不阻擋派工。 |
| follow-up | 依 [../SKILL.md](../SKILL.md) §6 第 10 步與 `<REPO>/rules/20-judgment.md`「停止端」判斷；預設帶原 brief、finding、diff、受影響條件與既有證據派 fresh agent。同 worktree 序列接手時明確不設自動 isolation，prompt 綁定絕對路徑；`SendMessage`／續派只能沿用該步的可調判斷，不以文字猜 counter。若另開 worktree，controller 先 materialize candidate checkpoint 並 read-back。 |
| collect | subagent 回傳的最後訊息就是 worker report（必含 Location 欄的 worktree 路徑、branch、HEAD）；長輸出由 worker 落檔到 brief 指定的 `<log-dir>` |
| stop | 背景 subagent 用當下工具清單裡的停止工具（現查有無 `TaskStop`）終止；同步呼叫的 subagent 無法中途停止，只能等回傳。主判準是 adapter 已確認 process／turn 結束（`TaskStop` 回報，或同步呼叫已回傳）——2026-09-22 實測 `TaskStop` 連 subagent 正在跑的 Bash 子 process 一起結束、檔案在回報當秒停止增長（見 `<REPO>/docs/harness-facts.md`「TaskStop」條）；`git -C <wt> status --short`＋`rev-parse HEAD` 兩次 read-back 只作佐證，相隔幾秒即可，期間該 agent 未回傳任何訊息且兩次都無變化才算停；否則依 SKILL §8 換新 worktree 重派 |

## 派工與 worktree

- harness 不回報 worktree 路徑，worker prompt 必須要求回報 worktree 絕對路徑、branch、HEAD SHA（worker report 的 Location 欄）。
- **隔離 worktree 例外**（`<REPO>/agents/worker.md` 規則 5）：plan 明寫「本任務在隔離 worktree（`isolation: worktree`）」時，worker 可在該 worktree 自己的 branch commit，完成前 rebase 到最新 base 一次並自行解純文字 conflict，解完重跑機械驗證；push、開 PR、開 issue、merge 仍禁止，且仍是該 worktree 唯一寫入者。這個 commit／rebase 權限來自 worker 合約，不因 fresh 或 follow-up 靜默延伸到非 isolation 的同 worktree；後者由 controller 建 checkpoint。
- controller read-back：`git worktree list`、`git -C <wt> log -1 --format=%H`、`git -C <wt> status --short`、`git -C <wt> diff <base>...HEAD --stat`。同一 working tree 僅一寫入者；read-only agent 與寫入者共用 tree 時，其測試／build 量測無效（`worktree.md`「何時需要」）。
- worktree branch 為 `worktree-<name>` 時，controller 以 `git -C <wt> push origin worktree-<name>:refs/heads/<repo 慣例 branch>` 推出並走 `create-pr` skill；所有 push、PR、merge、tracker comment 都需當次授權並由 controller 做。
- `Workflow` 工具的 `agent()` 未確認支援 `isolation`，且需使用者當次明確要求，本流程不使用。

## 驗收角色分流

切片驗收與 SKILL §6 第 9 步的整合 verifier 都用 `verifier`（`model: opus`）；升 `model: fable` 的訊號與授權見 `<REPO>/rules/10-dispatch.md` §5「驗證不自驗」。整合 verifier 在 integration tree 的乾淨環境跑；範圍外發現依 `<REPO>/rules/10-dispatch.md` §5 登記，不擴修。

## 清理

採 `worktree.md`「清理的證據條件」；確認後 controller 在主 repo 執行 `git worktree remove <絕對路徑>` 與 `git branch -D worktree-<name>`。不可用 commit 數判定 squash 後是否落地。
