# Adapter：Codex 同 session subagent

配合 [../SKILL.md](../SKILL.md) §9 的 adapter 契約使用；只提供 launch、follow-up、query status、collect、stop、workspace 與角色分流，不改變 SKILL 任何一步。Claude worker 合約的隔離 worktree 例外（`<REPO>/agents/worker.md` 規則 5）不適用於 Codex worker（`<REPO>/codex/agents/worker.toml` 禁止 commit）。

| 契約項目 | 本 adapter 的做法 |
|---|---|
| launch | Codex controller 依 `<REPO>/codex/rules/10-dispatch-codex.md` §3 三件套，用當前 surface 的 `spawn_agent` 每片派一個 subagent；prompt 的工作目錄欄指定該片 worktree 絕對路徑與絕對寫入所有權。subagent 在 controller session 內跑，沒有獨立 terminal |
| workspace | **controller 先建**每片獨立 worktree 與 integration worktree（指令見 `worktree.md`「所有權與路徑」），Codex 沒有自動隔離機制 |
| query status | 用當前 surface 的 `list_agents` 看 thread 狀態，再以 `git worktree list`、`git -C <wt> status --short`、`git -C <wt> diff`、`git -C <wt> rev-parse HEAD`、`git -C <wt> branch --show-current` read-back；thread 狀態只是執行線索，git 才是產物證據 |
| follow-up | agent 還在跑時用 `send_message` steering；idle／completed 時用 `followup_task` 續同一 agent context。需要 fresh-context delta 時另派同角色，並帶原 finding、修正 diff、受影響驗收條件與既有證據 |
| collect | 用 `wait_agent` 等 mailbox／final-status 通知，從該 agent 的 final response 收 worker report（含路徑、HEAD 與驗證輸出關鍵行）；長輸出落檔到 brief 指定的 `<log-dir>` |
| stop | 用當前 surface 的 `interrupt_agent` 中止該 agent turn，再以 `list_agents` 確認不再 running；最後 read-back `git -C <wt> status --short` 與 `rev-parse HEAD`。工具不存在或狀態確認不了時，依 SKILL §8 視為仍可能在寫，不重用該 worktree |

## 派工與 worktree

- worker 只修改 approved plan 授權的產物（程式碼、設定、文件、測試與 fixture），執行機械驗證並回報路徑、HEAD 與輸出；**禁止** branch、stash、commit、rebase、push、merge、tracker 或其他對外動作。controller 負責 commit、rebase、PR 與 merge，均仍受 session 授權。
- worker 回報後，controller 先確認 agent 已停止，並以 `git status --short`、`git diff --name-only`、`git diff` 對照 report 與 ownership；只 stage 本片允許路徑、read-back staged diff，再在該 slice branch 建 **checkpoint commit**。記下新的 HEAD，之後 §5 驗收、§6 ownership audit 與 integration 都綁這個 SHA；follow-up 產生新修改時重做同一套 read-back 與新 checkpoint。checkpoint 是 Codex worker 禁 commit 合約下的 controller handoff，不得在 agent 仍 running 時執行。
- controller rebase／解 conflict 後重跑受影響測試；切片驗收在已停止 worker、乾淨且 HEAD 已 checkpoint 的 slice worktree 執行，整合驗收才在 integration worktree 執行。

## 驗收角色分流

切片驗收用 `verifier/Terra high`；安全、不可逆、重大架構或正式高風險切片用 `sol_verifier/Sol high`。SKILL §6 第 9 步的整合驗收同樣依此分流，僅該階段限於整合互動；切片驗收仍須核對該片全部驗收條件。兩者依 `<REPO>/codex/rules/10-dispatch-codex.md` §6「驗證語意」保持 fresh-context、read-only；修正收斂依 `<REPO>/rules/20-judgment.md` §2「停止端」。

## 清理

controller 依 session 授權管理 git，push／PR 走 `create-pr` skill；清理採 `worktree.md`「清理的證據條件」，確認後 `git -C <repo> worktree remove <絕對路徑>` 再刪已核對的 branch；非自己建立的 worktree／branch 仍需明確授權。
