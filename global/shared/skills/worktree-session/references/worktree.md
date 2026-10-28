# Git worktree：位置、忽略與清理

配合 [../SKILL.md](../SKILL.md) 使用。worktree 是 implementation detail：它讓多個 session 同時寫入同一 repo 而不互踩（single-writer：同一 working tree 同一時間只有一個寫入者；只要共用 tree，即使檔案不重疊也只能序列）。不寫 repo 的角色（verifier、查詢型 subagent）與寫入者共用 tree 時，唯讀結論仍可信，但**跑測試／build 得到的數字被污染**——要嘛等寫入者停手，要嘛給它自己的 worktree。

## 所有權與路徑

每個 session 的實際寫入範圍 ＝ **它的 worktree 絕對路徑**；不同 worktree 的同名相對路徑不是衝突；同一 worktree 永遠單一寫入者。記錄每個 worktree 的絕對路徑、branch、base SHA。

自建的 worktree 預設放 `<repo>/.worktrees/<名>`。為什麼是 `.worktrees/`：規則由 Claude、Codex 與其他 agent 共用，不綁 Claude 專屬的 `.claude/`；用 `.` 開頭是因為多數工具（analyzer、`tsc`、測試搜尋、lint、watcher 等）預設跳過 dot 目錄，卻會掃一般目錄、且多半不讀 gitignore。Claude Code 內建 `isolation: worktree` 另放在 `<repo>/.claude/worktrees/<name>/`，位置改不了（見 `<REPO>/docs/harness-facts.md`），所以三個位置並存：`.worktrees/`、`.claude/worktrees/`、Orca 的 `.orca/workspaces/`。不放 session scratchpad 或系統暫存目錄：路徑冗長、session 結束後難找，且 Windows `%TEMP%` 可能被儲存空間感知／磁碟清理清掉。不放 repo 旁的固定目錄：曾整個被外部工具清掉，量測做到一半得重建。忽略靠使用者全域 gitignore（`git config --global core.excludesFile` 指向的檔）的三條：`.worktrees/`（刻意不帶開頭 `/`：ripgrep（含 Claude 的 Grep 工具）把全域 excludesFile 中帶開頭 `/` 的規則錨定在自己的 cwd，從 repo 根以外的位置搜尋時就失效，以 `rg` 實測）、給內建 isolation 的 `**/.claude/worktrees/`，與給 Orca `orca worktree create` 建的 worktree 的 `.orca/`（位置 `<repo>/.orca/workspaces/<repo-name>/<name>`），**不在各 repo 的 `.gitignore` 加這三條**（`git check-ignore -v` 的驗證法見 `<REPO>/docs/new-host.md`；其他機器同步後自行驗證）。

建立指令範本：`git -C <repo> worktree add <repo>/.worktrees/<名> -b <branch> <base-ref>`。建立後務必 `git worktree list` read-back 記錄絕對路徑與 branch，並跑 `git -C <repo> check-ignore -v .worktrees/<名>`：必須 rc=0 且印出命中規則；不命中代表該機器的全域 gitignore 未更新——停下回報，不要自行改該 repo 的 `.gitignore`。`git status --short` 只當線索、不當判定依據（判定以 `check-ignore` 為準）；列出 `.worktrees/` 本身是 worktree 沒被忽略的直接訊號。已知副作用：從 repo 根目錄 `grep -r` 或其他不讀 gitignore 的掃描工具會掃到 worktree 裡的整份副本；搜尋用 `git grep`、Claude 的 Grep 工具或 `rg`，三者都照 gitignore 排除三個位置（實測 Grep 與 `rg --hidden` 對 `.worktrees/` 與 `.claude/worktrees/`（Windows 桌機）皆排除，對 `.orca/`（主力 Mac）也排除、加 `--no-ignore` 才命中；`rg` 不可用的機器見該機器的 host facts）；`grep -r` 等不讀 gitignore 的工具加 `--exclude-dir=.worktrees --exclude-dir=worktrees --exclude-dir=.orca`（`worktrees` 涵蓋 `.claude/worktrees`，`.orca` 涵蓋 Orca 的 `.orca/workspaces`）。

worktree 之間**不要用複製檔案**搬改動——另一邊的 base 可能已前進，複製會覆蓋新 code；一律透過 commit 與 git 合併。merge 前的 conflict 預檢用唯讀的 `git -C <repo> merge-tree --write-tree <base> <branch>`（git ≥ 2.38），不用會動 working tree 的試合。

## 清理的證據條件（全部 AND，缺一不清）

1. 該 worktree `git status --short` 為空，且沒有仍在使用它的 session（`cli.md`「stop」的 process 檢查回空）。逾時或無回應的 session 不等於已停止；確認不了就不清、也不重用該 worktree。
2. 交付內容已在目標 base 上：核對**完整交付 diff**（含新增、刪除與更名）都出現在 base；`git merge-base --is-ancestor <head> <target-base>`（一般 merge）或 PR `MERGED` 狀態（squash／rebase）只證明「曾合併」，是來源證據，不能取代內容核對。被 revert 或缺失的交付保持未完成並保留 worktree，除非使用者明確撤銷交付。

條件以 `&&`／`test` 串起來強制，只印出結果不能阻擋下一步：

```bash
test -z "$(git -C <wt> status --short)" \
&& git -C <repo> merge-base --is-ancestor "$(git -C <wt> rev-parse HEAD)" <target-base> \
&& git -C <repo> worktree remove <wt> && git -C <repo> branch -D <branch>
```

squash／rebase merge 的 branch 不是 base 的祖先，第二個 `test` 改成確認 `gh pr view <n> -R <owner/repo> --json state` 為 `MERGED` 且 `git diff <target-base> <wt-head> -- <交付路徑>` 為空。刪除**非本次自建**的 worktree／branch 仍需明確授權（鐵律二）。

## Harness 事實

各工具的自動 worktree 行為（路徑、branch 命名、自動刪除條件、成本樣本）canonical 在 `<REPO>/docs/harness-facts.md`，本檔只引用不重抄。
