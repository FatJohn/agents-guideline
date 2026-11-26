# Changelog

讀者：裝了這套制度的人（含維護者自己在其他機器），pull 之後想知道制度改了什麼、要不要動手。

只記行為變更：規則、skill、agent 合約、rubric、hook、使用者會執行的腳本、安裝步驟或設定片段，以及需要使用者動手的事。純措辭、量測報告、內部重構不記。按日期分段，新的在上；本 repo 沒有版本號。2026-11-26 開始記錄，之前的變更看 `git log`。

複本安裝（Windows、不能提權的機器）的每一筆都隱含同一個動作：pull 後重跑 `python scripts/sync-profile.py --apply --update`，下面不再逐筆重複。

## 2026-11-26

- **新增本檔與記錄規則**（#82）：之後 PR 改到規則、skill、agent 合約、rubric、hook、使用者會執行的腳本、安裝步驟或設定片段，或 merge 後要使用者動手時，同一個 PR 要在這裡補一筆（門檻與時點見 `.claude/skills/maintain-guideline/SKILL.md` §2）。維護者照做即可，不用另外設定。
- **commit 閘門擋專案真名**（#80）：本 repo 加了 `.githooks/pre-commit`、`commit-msg`，staged 檔案或 commit message 含 repo 外名單裡的名字就擋下。要 commit 本 repo 的維護者：照 `docs/install.md`「本 repo 的 commit 閘門：擋專案真名」設 `core.hooksPath` 與名單路徑；沒設定的 clone 只印一行提示、照常放行。
- **派出去的 session 帶固定名稱**（#81）：issue session、接手、旁支、盤點 session 啟動時命名為 `issue-<issue>`、`takeover-<主題>`、`side-<brief 名>`、`inventory-<MMDD>`（Codex 端只給建議名稱，由使用者自己命名）；`require-issue-session-model.sh` 的 fallback 提示同步改成 `-n issue-<issue>`。symlink 安裝 pull 後即生效；在主 checkout 用 `claude --resume` 找 issue worktree 的 session 要按 `Ctrl+W`。
- **刪除 `v1` tag**（無 PR）：遠端已刪除，舊歷史含非公開專案名稱；`v3` tag 不受影響。新 clone 拿不到 `v1`（`git fetch origin tag v1` 會失敗），但既有 clone 的本機 `v1` 不會因 pull／fetch 消失：在其他機器的 clone 跑 `git tag -d v1`，清掉之前不要跑 `git push --tags`，否則會推回公開 repo。
