# 00 — 環境事實與結構性風險

> 本檔只放**跨機器皆真**的結論；單機事實（工具鏈、驗證能力）在 `05-hosts.md`，開工前先去認機器。
> 本檔是全系統唯一記查證日的地方：**2026-07-14**；距今超過 90 天，先當場核對再引用，核對後更新此日期。事實過時就更新本檔，不要另開新檔。

## 使用者背景（最低必要認知）

- 使用者：FatJohn（JohnShu），繁體中文台灣用語溝通。任職 TVBS（GitHub org：`tvbstw`），公司與個人專案並行。
- 公司專案（自己主導的代表作）：`flutter-slimgo`（Flutter App）、`web-starvision`／`web-starvision-cms`（網站）等。
- 個人 side project：財經類（macroeconomics-report 等，自己玩玩性質）等。完整清單用 `gh repo list`（個人）、`gh search repos --owner tvbstw`（公司）現查，不要依賴這裡的列舉。
- 技術背景：C#／.NET／WPF／UWP 熟、C++ 部分會；Flutter、TypeScript 可；JavaScript／Vue 一般、React 初學。**後端與雲端架構不熟**——個人專案部署以 Zeabur 為主；財經專案另碰過 CloudFront＋自有 domain、R2 storage。涉及雲端架構的建議要多給脈絡、少假設既有知識。
- LLM 資源：Claude Code 訂閱 Max；主對話的實際設定（`~/.claude/settings.json`，只查非敏感欄位）為 `opus[1m]`／effort `xhigh`。Codex 目前為 Plus，主對話預設 `gpt-5.6-terra`／effort `high`；若升級 Pro，主對話預設改為 `gpt-5.6-terra`／effort `xhigh`。Codex 可透過 codex plugin 派工，見 `10-dispatch.md`。
- Codex custom agent runtime 限制（主力 Mac，0.144.4，2026-07-14 實跑）：`~/.codex/agents/` 的 standalone TOML 可被 `--strict-config` 接受，但目前 collaboration v2 的 `spawn_agent` 只帶 `task_name`；fresh child metadata 仍可能是 `agent_role:null`，即使同名檔案與 `[agents.<name>] config_file` 都存在。只有 child metadata 的 `agent_role` 明確符合角色，才可宣稱 custom model／effort／contract 已套用；`null` 必須標記 runtime unavailable／模型未驗證，不得用 child 文案當載入證據。

## 三大結構性風險與修法（按嚴重度）

### 1. 主對話下場做粗活 → context 塞爆 → compaction 失憶

**症狀**：大量讀檔、掃 repo、抓網頁、批次改檔在主對話進行，context 膨脹；compaction 觸發後早期決定遺失，開始重做已完成的工作或偏離原目標。

**修法**：
- 判斷基準同時看 **context 成本**與**任務獨立性**：大量原始內容且可獨立驗收時優先派工；強依賴主線決策或需要即時整合時留在主對話並控制讀取範圍。Claude 派工見 `10-dispatch.md`；Codex 派工見 `../codex/rules/10-dispatch-codex.md`。
- session 內優先使用平台提供的 plan／task 狀態，不強制在 repo 建 scratchpad；跨 session 續接才使用 `session-handoff` skill 更新專案 `.codex/HANDOFF.md`。

### 2. 假完成：宣稱通過但沒有實際執行

**症狀**：說「測試通過」「已修好」但沒有跑過任何驗證，或驗證是自己看自己的產出。

**修法**：鐵律一（回報分級：已驗證／待 CI／未驗證）＋按產出風險分工驗證：文件、主觀品質與高風險產出派 fresh-context `verifier`；程式碼的測試、build、lint、實跑、schema 等機械驗證可由製作者執行，但必須附指令輸出或實跑證據，高風險程式碼另加 fresh review。完成的定義見 `20-judgment.md` §2。

### 3. 固定注入肥大：每個 session 開場漏掉數千 token

**症狀**：大量 plugin（superpowers、firecrawl 全家桶、chrome、computer-use…）每 session 注入工具清單與絕對化指令；其中 superpowers 要求「任何動作前先叫 skill」。

**修法**：
- 抓住優先權排序（見全域 CLAUDE.md），不被注入音量牽著走。
- deferred MCP 工具只注入名稱——與任務無關的 schema 不要主動 ToolSearch。
- ［需使用者動作］長期不用的 plugin 可停用：專案 `.claude/settings.json` 寫 `"enabledPlugins": { "<plugin>@<marketplace>": false }` 可逐專案覆寫全域設定。

## 記憶機制（四層，各有分工）

- **自動事件史**：Claude 端由 remember plugin 寫進各專案根目錄 `.remember/`（`now.md`／`recent.md`／`archive.md` 等），用途是續接工作時快速查「上次做到哪」。Codex 端尚未安裝等價自動時間軸；若需要，第二階段用 Codex hooks 在 `Stop`／`PreCompact` 事件產生摘要。
- **精選持久記憶**：Claude 端是 `~/.claude/projects/<專案slug>/memory/`；Codex 端是 `~/.codex/memories/`（`~/.codex/config.toml` 的 `[features] memories = true`）。放使用者偏好、被糾正的教訓、進行中工作的穩定狀態。不要把必守規則只放記憶；規則要進 `AGENTS.md`／`CLAUDE.md` 或 repo 文件。
  - **Chronicle（可選的螢幕脈絡）**：opt-in research preview，是精選持久記憶的可選補充，用螢幕活動脈絡補充 Codex Memories，不新增或取代自動事件史、精選持久記憶、顯式交接檔、repo 文件這四層。它有 rate limit、可能擷取或處理含敏感資訊的畫面，以及畫面內 prompt injection 等風險，因此不預設開啟；啟用前先確認資料邊界與風險承受度。
- **顯式交接檔**：Codex 收尾用 `session-handoff` skill，預設寫專案 `.codex/HANDOFF.md`。用途是讓下個 session 不靠自動記憶也能接上；若需要 Claude/remember 相容，使用者明說時再同步 `.remember/now.md`。
- **repo 文件＝制度層**：跨裝置、可 review，git 是同步機制（本系統即是）。自動事件史與精選記憶多半只在本機；長期制度、判準與可審查流程寫進本 repo。

## 好用的 skill／plugin（實戰驗證的優先選項）

原則：動手前先想「這類問題有沒有現成 skill」，有就用，不要土炮重造；但真正符合任務才叫用（優先權排序見全域 CLAUDE.md）。

- **開發流程（使用者常用且信任）**：superpowers 系列——動工前 `brainstorming`、實作 `test-driven-development`、除錯 `systematic-debugging`、宣稱完成前 `verification-before-completion`。與本系統的分工：superpowers 管「執行者怎麼做好一件事」，本系統管「指揮官怎麼調度與驗收」，兩者疊加使用。
- **Claude 派工**：見 `10-dispatch.md`。
- **Codex 派工**：見 `../codex/rules/10-dispatch-codex.md`。
- **工具分工**：Memories、handoff、hooks、Chronicle 各自獨立，不合併成單一機制；Chronicle 只作為精選持久記憶的可選補充，不新增或取代 remember／自動事件史、Memories／精選持久記憶、handoff／顯式交接檔、repo 文件／制度層的四層定義。
- **查網頁／爬資料**：firecrawl 系列（search／scrape／crawl）——在 subagent 內用，只把結論帶回主對話。
- **產出文件**：docx／pptx／xlsx／pdf 等 anthropic-skills。
- **外部第二意見／整包委派**：codex plugin（用法見 `10-dispatch.md`）。
- **Codex 收尾交接**：`session-handoff` skill——使用者說「收尾」「記一下」「下次續接」「handoff」時，整理目標／已完成／驗證／下一步到 `.codex/HANDOFF.md`。
- **找新工具**：遇到「感覺應該有現成工具」的問題，先搜 mcp-registry 的 connector 清單或問使用者，找不到再自己寫。

## 查證過的事實（2026-07-13；版本更新後重新核對）

- Agent 呼叫可逐次指定 model；effort 仍由 agent 定義 frontmatter 或 session/workflow 設定控制。
- Agent frontmatter 的 `effort` 可填 `low`／`medium`／`high`／`xhigh`／`max`，實際可用值仍受模型與組織限制。
- Agent frontmatter 的 `model` 可填 `haiku`／`sonnet`／`opus`／`fable`／完整 model ID／`inherit`。
- Claude Code 2.1.207 的 subagent 可使用 `isolation: worktree`；需要 blocking 結果時不得只依賴可能因休眠中斷的背景執行。
