# 本機事實：Windows 桌機（目前 hostname：`FatJohn-PC`，AMD64）

> 探測日：2026-08-05；2026-09-20 複查工具鏈與 symlink。跨機器規則與 `<REPO>` 對照在 `../rules/05-hosts.md`，工具鏈明細與 os error 448 的根因、實驗、修法在 `../docs/hosts-detail.md`。

- **`python3` 沒有別名，只有 `python`**——README 探測清單第 3 項的指令直接照抄會誤判 Python 未安裝
- 專案位置：個人專案放在 `E:\` 根層，不是 Mac 的 `~/Projects/FatJohn/`
- 本系統 repo：`E:\agents-guideline`。**全域設定是 `../scripts/sync-profile.py` 同步過去的實體檔複本**（2026-09-20 起，`~/.claude`／`~/.codex`／`~/.agents` 三處；Codex agent TOML 另由 `sync-codex-agents.py` 管）；正解是用 admin 建 symlink，下次重建時改回去。
  - **改了 repo 不會自動生效**——動完 `rules/`、`hosts/`、`rubrics/`、`skills/`、`agents/`、`CLAUDE.md`、`AGENTS.md` 要跑 `python scripts/sync-profile.py --apply --update`（加 `--prune` 清掉已 sunset 的舊項），否則你讀到的規則和跑起來的規則會不一樣。
  - 副作用：`readlink ~/.claude/CLAUDE.md`／`~/.codex/AGENTS.md` 回空（已是實體檔）；`<REPO>` 就是本條開頭那個路徑。
- **非提權建立的 symlink 在本機開檔一律 os error 448**，而 `LinkType`／`Target`／`readlink` 查起來全綠——**read-back 要實際讀內容**。連帶：`rg`（WinGet Links）與 `node`／`npm`／`codex`（mise shim）目前都掛，用前先 `--version`，`rg` 改用 `grep` 或 Claude 的 Grep 工具；從 Orca 啟動的 Codex 讀不到全域設定。
- **Claude Code 的 Bash 工具會先把指令字串裡的 `\\` 收成 `\`（單引號與 heredoc 內都一樣，2026-09-20 實測 `printf '%s' 'x\\y'` 印出 `x\y`；Mac 未測）**：含反斜線的 regex／python 片段用 Write 寫成檔再執行，或用 Edit 工具取代 sed。
- 驗證能力：.NET／Node／Flutter／Docker CLI 都在 PATH，但**本機尚未實跑過任何 build／test**；第一次要用來當完成證據前，先跑一次 `dotnet --info`／`flutter doctor` 確認 SDK 完整，不要憑 CLI 存在就宣稱可驗證。iOS build 不可（非 macOS）。
