# 記憶機制（四層，各有分工）

> 2026-08-22 從 `rules/00-environment.md` 搬出。理由：它只在**寫或讀記憶時**用得到，而
> `rules/` 是每個 session 全文載入的常駐區、付的是固定成本（`maintain-guideline` §5
> 「只在特定情境才用得到的內容不該放 rules/」）。內容原文未改寫。

- **自動事件史**：Claude 端由 remember plugin 寫進各專案根目錄 `.remember/`（`now.md`／`recent.md`／`archive.md` 等），用途是續接工作時快速查「上次做到哪」。Codex 端尚未安裝等價自動時間軸；若需要，第二階段用 Codex hooks 在 `Stop`／`PreCompact` 事件產生摘要。
- **精選持久記憶**：Claude 端是 `~/.claude/projects/<專案slug>/memory/`；Codex 端是 `~/.codex/memories/`（`~/.codex/config.toml` 的 `[features] memories = true`）。放使用者偏好、被糾正的教訓、進行中工作的穩定狀態。不要把必守規則只放記憶；規則要進 `AGENTS.md`／`CLAUDE.md` 或 repo 文件。
  - **Chronicle（可選的螢幕脈絡）**：opt-in research preview，是精選持久記憶的可選補充，用螢幕活動脈絡補充 Codex Memories，不新增或取代自動事件史、精選持久記憶、顯式交接檔、repo 文件這四層。它有 rate limit、可能擷取或處理含敏感資訊的畫面，以及畫面內 prompt injection 等風險，因此不預設開啟；啟用前先確認資料邊界與風險承受度。
- **顯式交接檔**：Codex 收尾用 `session-handoff` skill，預設寫專案 `.codex/HANDOFF.md`。用途是讓下個 session 不靠自動記憶也能接上；若需要 Claude/remember 相容，使用者明說時再同步 `.remember/now.md`。
- **repo 文件＝制度層**：跨裝置、可 review，git 是同步機制（本系統即是）。自動事件史與精選記憶多半只在本機；長期制度、判準與可審查流程寫進本 repo。
