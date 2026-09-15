# Adapter：Codex 同 session subagent

配合 [../SKILL.md](../SKILL.md) §9 的 adapter 契約使用；只提供 launch、follow-up、query status、collect、stop、workspace 與角色分流，不改變 SKILL 任何一步。Claude worker 合約的隔離 worktree 例外（`<REPO>/agents/worker.md` 規則 5）不適用於 Codex worker（`<REPO>/codex/agents/worker.toml` 禁止 commit）。

| 契約項目 | 本 adapter 的做法 |
|---|---|
| launch | Codex controller 依 `<REPO>/codex/rules/10-dispatch-codex.md` §3 三件套派 subagent，每片一個；prompt 的工作目錄欄指定該片 worktree 絕對路徑與絕對寫入所有權。subagent 在 controller session 內跑，沒有獨立 terminal |
| workspace | **controller 先建**每片獨立 worktree 與 integration worktree（指令見 `worktree.md`「所有權與路徑」），Codex 沒有自動隔離機制 |
| query status | `git worktree list`、`git -C <wt> status --short`、`git -C <wt> diff`、`git -C <wt> rev-parse HEAD`、`git -C <wt> branch --show-current` read-back |
| follow-up | 帶原 finding、diff 與受影響驗收條件重派同角色；Codex subagent 不保留跨呼叫 context |
| collect | subagent 回傳的最後訊息就是 worker report（含路徑、HEAD 與驗證輸出關鍵行）；長輸出落檔到 brief 指定的 `<log-dir>` |
| stop | 同 session subagent 無法中途停止（以當下版本現查為準），只能等回傳；回傳前不得動它的 worktree。回傳後以 `git -C <wt> status --short` 確認無變化才算停 |

## 派工與 worktree

- worker 只修改 approved plan 授權的產物（程式碼、設定、文件、測試與 fixture），執行機械驗證並回報路徑、HEAD 與輸出；**禁止** branch、stash、commit、rebase、push、merge、tracker 或其他對外動作。controller 負責 commit、rebase、PR 與 merge，均仍受 session 授權。
- controller rebase／解 conflict 後重跑受影響測試；read-only 驗收的測試／build 必須在不被寫入污染的 integration worktree 執行。

## 驗收角色分流

切片驗收用 `verifier/Terra high`；安全、不可逆、重大架構或正式高風險切片用 `sol_verifier/Sol high`。SKILL §6 第 9 步的整合驗收同樣依此分流，僅該階段限於整合互動；切片驗收仍須核對該片全部驗收條件。兩者依 `<REPO>/codex/rules/10-dispatch-codex.md` §6「驗證語意」保持 fresh-context、read-only；修正收斂依 `<REPO>/rules/20-judgment.md` §2「停止端」。

## 清理

controller 依 session 授權管理 git，push／PR 走 `create-pr` skill；清理採 `worktree.md`「清理的證據條件」，確認後 `git -C <repo> worktree remove <絕對路徑>` 再刪已核對的 branch；非自己建立的 worktree／branch 仍需明確授權。
