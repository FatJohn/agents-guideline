# Codex 平台契約

本 reference 配合 [../SKILL.md](../SKILL.md) 使用；Codex controller 建立並管理所有獨立 worktree 與 integration worktree，不能套用 Claude 的 worker commit／rebase 隔離例外。

## 派工與 worktree

- controller 先建立每片獨立 worktree，並在 prompt 指定該 worktree 的絕對路徑與絕對寫入所有權。不同 worktree 的同名相對路徑不衝突；同一 worktree 永遠單一寫入者。
- worker 只修改 approved plan 授權的產物（例如程式碼、設定、文件、測試與 fixture），執行機械驗證並回報路徑、HEAD 與輸出；禁止 branch、stash、commit、rebase、push、merge、tracker 或其他對外動作。controller 負責提交、rebase、PR 與 merge，均仍受 session 授權。
- controller 以 `git worktree list`、`git -C <worktree> status --short`、`git -C <worktree> diff`、`git -C <worktree> rev-parse HEAD` 與 `git -C <worktree> branch --show-current` read-back。controller rebase／解 conflict 後重跑受影響測試；read-only 驗收的測試／build 必須在不被寫入污染的 integration worktree 執行。

## 整合驗收與清理

每片的 fresh slice 驗收使用 `verifier/Terra high`；安全、不可逆、重大架構或正式高風險切片使用 `sol_verifier/Sol high`。共通 SKILL §2 的互動驗收同樣依此風險分流，僅該階段限於整合互動；切片驗收仍須核對該片全部驗收條件。兩者均依 `<REPO>/codex/rules/10-dispatch-codex.md` §6「驗證語意」保持 fresh-context、read-only；修正收斂依 `<REPO>/rules/20-judgment.md` §2「停止端」。

controller 依 session 授權管理 git，push／PR 走 `create-pr` skill；清理採共通 SKILL §2 的證據條件。確認後以 `git -C <repo> worktree remove <絕對路徑>` 移除乾淨 worktree，再刪除其已核對的 branch；非自己建立的 worktree／branch 仍需明確授權。
