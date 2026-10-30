# 記憶機制（四層，各有分工）

> 這些分工只在**寫或讀記憶時**用得到，所以不放每個 session 都會讀到的全域入口。

- **自動事件史**：Claude 端由 remember plugin 寫（`now.md`／`recent.md`／`archive.md` 等），用途是續接工作時快速查「上次做到哪」。位置依 plugin 設定：預設在各專案根目錄 `.remember/`，external storage mode 時在 `~/.remember/config.json` 的 `data_dir` 指到的 store、一專案一個 slug 目錄，store 本身是 git repo 時 plugin 會自動 commit／push（本機採哪種見 `global/shared/hosts/<key>.md`）。Codex 端尚未安裝等價自動時間軸；若需要，第二階段用 Codex hooks 在 `Stop`／`PreCompact` 事件產生摘要。
- **精選持久記憶**：Claude 端是 `~/.claude/projects/<專案slug>/memory/`；Codex 端是 `~/.codex/memories/`（`~/.codex/config.toml` 的 `[features] memories = true`）。放使用者偏好、被糾正的教訓、進行中工作的穩定狀態。不要把必守規則只放記憶；規則要進 `AGENTS.md`／`CLAUDE.md` 或 repo 文件。
  - **Chronicle（可選的螢幕脈絡）**：opt-in research preview，是精選持久記憶的可選補充，用螢幕活動脈絡補充 Codex Memories，不新增或取代自動事件史、精選持久記憶、顯式交接檔、repo 文件這四層。它有 rate limit、可能擷取或處理含敏感資訊的畫面，以及畫面內 prompt injection 等風險，因此不預設開啟；啟用前先確認資料邊界與風險承受度。
- **顯式交接檔**：兩平台共用 `<REPO>/global/shared/skills/handoff/SKILL.md` §4「session 交接卡」定格式。載體：裝有 remember plugin 的平台交給它的 handoff 腳本（`remember.md`，下個 session 自動注入、隨 store 備份），其餘寫專案 `.agents/HANDOFF.md`。用途是讓下個 session 不靠自動記憶也能接上。
  - session 內優先使用平台提供的 plan／task 狀態，不強制在 repo 建 scratchpad；跨 session 續接才用 `handoff` skill 寫交接卡；Claude 端另有自動事件史與精選持久記憶（見上）承接。
- **repo 文件＝制度層**：跨裝置、可 review，git 是同步機制（本系統即是）。自動事件史與精選記憶多半只在本機；長期制度、判準與可審查流程寫進本 repo。
