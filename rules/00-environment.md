# 00 — 環境事實與結構性風險

> 本檔只放**跨機器皆真**的結論；單機事實（工具鏈、驗證能力）在 `05-hosts.md`，開工前先去認機器。
> 本檔是全系統唯一記查證日的地方：**2026-07-06**；距今超過 90 天，先當場核對再引用，核對後更新此日期。事實過時就更新本檔，不要另開新檔。

## 使用者背景（最低必要認知）

- 使用者：FatJohn（JohnShu），繁體中文台灣用語溝通。任職 TVBS（GitHub org：`tvbstw`），公司與個人專案並行。
- 公司專案（自己主導的代表作）：`flutter-slimgo`（Flutter App）、`web-starvision`／`web-starvision-cms`（網站）等。
- 個人 side project：財經類（macroeconomics-report 等，自己玩玩性質）等。完整清單用 `gh repo list`（個人）、`gh search repos --owner tvbstw`（公司）現查，不要依賴這裡的列舉。
- 技術背景：C#／.NET／WPF／UWP 熟、C++ 部分會；Flutter、TypeScript 可；JavaScript／Vue 一般、React 初學。**後端與雲端架構不熟**——個人專案部署以 Zeabur 為主；財經專案另碰過 CloudFront＋自有 domain、R2 storage。涉及雲端架構的建議要多給脈絡、少假設既有知識。
- LLM 資源：Claude Code 訂閱 Max（主對話預設 Opus）；另訂閱 Codex（可透過 codex plugin 派工，見 `10-dispatch.md`）。

## 三大結構性風險與修法（按嚴重度）

### 1. 主對話下場做粗活 → context 塞爆 → compaction 失憶

**症狀**：大量讀檔、掃 repo、抓網頁、批次改檔在主對話進行，context 膨脹；compaction 觸發後早期決定遺失，開始重做已完成的工作或偏離原目標。

**修法**：
- 判斷基準：**會把超過一頁原始內容帶進主對話的動作，一律派 subagent**（規則見 `10-dispatch.md`）。
- 多步驟任務開始時，在 scratchpad 建任務狀態檔（目標／驗收條件／已完成／待辦），每步更新；compaction 後靠它恢復狀態。

### 2. 假完成：宣稱通過但沒有實際執行

**症狀**：說「測試通過」「已修好」但沒有跑過任何驗證，或驗證是自己看自己的產出。

**修法**：鐵律一（回報分級：已驗證／待 CI／未驗證）＋鐵律三（驗收派 `verifier`）。完成的定義見 `20-judgment.md` §2。

### 3. 固定注入肥大：每個 session 開場漏掉數千 token

**症狀**：大量 plugin（superpowers、firecrawl 全家桶、chrome、computer-use…）每 session 注入工具清單與絕對化指令；其中 superpowers 要求「任何動作前先叫 skill」。

**修法**：
- 抓住優先權排序（見全域 CLAUDE.md），不被注入音量牽著走。
- deferred MCP 工具只注入名稱——與任務無關的 schema 不要主動 ToolSearch。
- ［需使用者動作］長期不用的 plugin 可停用：專案 `.claude/settings.json` 寫 `"enabledPlugins": { "<plugin>@<marketplace>": false }` 可逐專案覆寫全域設定。

## 記憶機制（三層，各有分工）

- **remember plugin＝自動事件史**：hooks 自動把每個 session 做了什麼壓成時間軸，寫進各專案根目錄 `.remember/`：`now.md`（當前 buffer）→ `today-*.md`（當日）→ `recent.md`（近 7 天）→ `archive.md`（更舊），另有 `core-memories.md`（關鍵時刻）。不用維護、自動累積。**用途：續接工作時查「上次做到哪」——開工前看 `recent.md`＋`now.md` 最快**；session 收尾可用 `/remember` skill 做交接。注意檔案是 session 進行中才逐步寫入，別因開場看不到就判定它沒運作。
- **內建持久記憶＝精選事實**：`~/.claude/projects/<專案slug>/memory/`。放使用者偏好、被糾正的教訓、進行中工作的狀態。**不會自動寫**——2026-07-06 盤點時全空即為證據——每 session 結束前依 `40-maintenance.md` §4 自查。與上層的分工：remember 記「發生過什麼」，這裡記「該記住什麼」。
- **repo 文件＝制度層**：跨裝置、可 review，git 是同步機制（本系統即是）。`.remember/` 目前被 gitignore，前兩層都只在本機。本系統 repo（agents-guideline）即為此設計。

## 好用的 skill／plugin（實戰驗證的優先選項）

原則：動手前先想「這類問題有沒有現成 skill」，有就用，不要土炮重造；但真正符合任務才叫用（優先權排序見全域 CLAUDE.md）。

- **開發流程（使用者常用且信任）**：superpowers 系列——動工前 `brainstorming`、實作 `test-driven-development`、除錯 `systematic-debugging`、宣稱完成前 `verification-before-completion`。與本系統的分工：superpowers 管「執行者怎麼做好一件事」，本系統管「指揮官怎麼調度與驗收」，兩者疊加使用。
- **查網頁／爬資料**：firecrawl 系列（search／scrape／crawl）——在 subagent 內用，只把結論帶回主對話。
- **產出文件**：docx／pptx／xlsx／pdf 等 anthropic-skills。
- **外部第二意見／整包委派**：codex plugin（用法見 `10-dispatch.md`）。
- **找新工具**：遇到「感覺應該有現成工具」的問題，先搜 mcp-registry 的 connector 清單或問使用者，找不到再自己寫。

## 查證過的事實（2026-07-06；版本更新後重新核對）

- **Agent 工具呼叫沒有 `effort` 參數**；effort 只能設在 agent 定義的 frontmatter（`~/.claude/agents/*.md` 或 `.claude/agents/*.md`），值：`low`／`medium`／`high`／`xhigh`（`max` 不能進 frontmatter）。需要特定 effort 的角色，先建 agent 定義（本系統的 `agents/verifier.md` 即一例）。（來源：goad-dot-claude 對照官方 sub-agents 文件的查證，2026-07）
- agent 定義 frontmatter 的 `model` 可填：`haiku`／`sonnet`／`opus`／完整 model ID／`inherit`。
- Workflow 工具的 `agent()` 可逐呼叫指定 model 與 effort，但 Workflow 需使用者明確要求多 agent 編排（如說「ultracode」）才能用。
