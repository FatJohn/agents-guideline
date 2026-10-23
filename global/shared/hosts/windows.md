# 本機事實：Windows 桌機（hostname：`FatJohn-PC`，AMD64）

探測日：2026-09-20

- 個人專案放在 `D:\Projects\FatJohn\`（2026-09-23 起；原本在 `E:\` 根層，E: 槽已不存在）。
- `<REPO>` 是 `D:\Projects\FatJohn\agents-guideline`。**全域設定是 `<REPO>/scripts/sync-profile.py` 同步過去的實體檔複本**（`~/.claude`、`~/.codex`、`~/.agents` 三處；Codex agent TOML 另由 `sync-codex-agents.py` 管）；正解是用 admin 建 symlink，下次重建時改回去。
  - **改了 repo 不會自動生效**：動完 `global/` 底下任何檔，要跑 `python "D:/Projects/FatJohn/agents-guideline/scripts/sync-profile.py" --apply --update`（加 `--prune` 清掉已 sunset 的舊項），否則讀到的規則和跑起來的規則不一樣。
  - 副作用：`readlink ~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 回空（已是實體檔）。
- 驗證能力：.NET、Node、Flutter、Docker CLI 都在 PATH。**.NET 已實跑**（`dotnet build`＋`dotnet test` 全套可跑）；**Node、Flutter、Docker 尚未實跑過 build／test**，第一次要當完成證據前先跑 `flutter doctor` 等確認工具鏈完整，不要憑 CLI 存在就宣稱可驗證。iOS build 不可（非 macOS）。
- **`python3` 沒有別名，只有 `python`**：`<REPO>/docs/new-host.md` 探測清單第 3 項的指令照抄會誤判 Python 未安裝。
- **非提權建立的 symlink 在本機開檔一律 os error 448**，而 `LinkType`、`Target`、`readlink` 查起來全綠，所以 read-back 要實際讀內容（根因與修法見 `<REPO>/docs/hosts-detail.md`）。連帶：`node`、`npm`、`codex`（mise shim）都掛，用前先 `--version`，Node 驗證也受影響；`rg` 可用但仍先 `--version`。
- 搜尋用 `rg`、`git grep` 或 Claude 的 Grep 工具（皆照 gitignore 排除 `.worktrees` 與 `.claude/worktrees`）；非用 `grep -r` 不可時加 `--exclude-dir=.worktrees --exclude-dir=worktrees` 或限定子目錄。從 Orca 啟動的 Codex 讀不到全域設定。
- **Claude Code 的 Bash 工具會先把指令字串裡的 `\\` 收成 `\`**（單引號與 heredoc 內都一樣；`printf '%s' 'x\\y'` 印出 `x\y`，Mac 無此現象）：含反斜線的 regex 或 python 片段用 Write 寫成檔再執行，或用 Edit 工具取代 sed。
