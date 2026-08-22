# 00 — 環境事實與結構性風險

> 本檔只放**跨機器皆真**的結論；單機事實（工具鏈、驗證能力）在 `05-hosts.md`，開工前先去認機器。
> **跨機器事實**的查證日以本檔檔頭為準：**2026-08-06**（單機事實的探測日各自記在 `05-hosts.md`；個別條目另帶戳記者，以其戳記為準）。距今超過 90 天，先當場核對再引用，核對後更新此日期。事實過時就更新本檔，不要另開新檔。

## 使用者背景（最低必要認知）

- 使用者：FatJohn（JohnShu），繁體中文台灣用語溝通。任職 TVBS（GitHub org：`tvbstw`），公司與個人專案並行。
- 公司專案（自己主導的代表作）：`flutter-slimgo`（Flutter App）、`web-starvision`／`web-starvision-cms`（網站）等。
- 個人 side project：財經類（macroeconomics-report 等，自己玩玩性質）等。完整清單用 `gh repo list`（個人）、`gh search repos --owner tvbstw`（公司）現查，不要依賴這裡的列舉。
- 技術背景：C#／.NET／WPF／UWP 熟、C++ 部分會；Flutter、TypeScript 可；JavaScript／Vue 一般、React 初學。**後端與雲端架構不熟**——個人專案部署以 Zeabur 為主；財經專案另碰過 CloudFront＋自有 domain、R2 storage。涉及雲端架構的建議要多給脈絡、少假設既有知識。
- LLM 資源：Claude Code 訂閱 Max；主對話 effort 由 `~/.claude/settings.json` 的 `effortLevel: xhigh` 設定，**model 不在 settings.json 裡**（由 UI 選，2026-07-25 核對；當次實際型號以主對話自報的 model ID 為準，該日為 `claude-opus-5`）。Codex 的訂閱檔位、主對話預設與 5.6 世代型號分層已移到 `../codex/rules/10-dispatch-codex.md` §0（2026-08-22 瘦身：那是 Codex 派工時才用得到的東西，Claude session 每次載入它是純浪費）。Claude 透過 codex plugin 派 Codex 外部第二意見，見 `10-dispatch.md`；Codex 自身派工見 `../codex/rules/10-dispatch-codex.md`。

## 三大結構性風險與修法（按嚴重度）

### 1. 主對話下場做粗活 → context 塞爆 → compaction 失憶

**症狀**：大量讀檔、掃 repo、抓網頁、批次改檔在主對話進行，context 膨脹；compaction 觸發後早期決定遺失，開始重做已完成的工作或偏離原目標。

**修法**：
- 判斷基準同時看 **context 成本**與**任務獨立性**：大量原始內容且可獨立驗收時優先派工；強依賴主線決策或需要即時整合時留在主對話並控制讀取範圍。Claude 派工見 `10-dispatch.md`；Codex 派工見 `../codex/rules/10-dispatch-codex.md`。
- session 內優先使用平台提供的 plan／task 狀態，不強制在 repo 建 scratchpad；跨 session 續接才使用 `session-handoff` skill 更新專案 `.codex/HANDOFF.md`——該 skill **只裝在 Codex 端**（`~/.agents/skills/`），Claude 端叫不到，Claude 的跨 session 續接靠 remember plugin 的 `.remember/` 與精選持久記憶。

### 2. 假完成：宣稱通過但沒有實際執行

**症狀**：說「測試通過」「已修好」但沒有跑過任何驗證，或驗證是自己看自己的產出。

**修法**：鐵律一（回報分級：已驗證／待 CI／未驗證）＋按產出風險分工驗證。完成的定義見 `20-judgment.md` §2；誰驗什麼、用哪份 rubric 見 `10-dispatch.md` §5。

### 3. 固定注入肥大：每個 session 開場漏掉數千 token

**症狀**：plugin 與 MCP server 每 session 注入工具清單、skill 描述與絕對化指令；skill 清單本身就是固定成本，跟用不用得到無關。（2026-08-06 現查：曾是最大注入源的 superpowers 與 firecrawl 全家桶已移除，`~/.claude/settings.json` 的 `enabledPlugins` 現存 context7／codex／remember／document-skills／mattpocock-skills／andrej-karpathy-skills 六個；要引用當下清單一律現查該檔，不要照抄這一行。）

**修法**：
- 抓住優先權排序（見全域 CLAUDE.md），不被注入音量牽著走。
- deferred MCP 工具只注入名稱——與任務無關的 schema 不要主動 ToolSearch。
- ［需使用者動作］長期不用的 plugin 可停用：專案 `.claude/settings.json` 寫 `"enabledPlugins": { "<plugin>@<marketplace>": false }` 可逐專案覆寫全域設定。

## 記憶機制

四層（自動事件史／精選持久記憶／顯式交接檔／repo 文件＝制度層），各有分工與已知邊界。
**要寫或讀記憶時再讀 `../docs/memory-layers.md`**（2026-08-22 從本檔搬出，只在特定情境用得到）。

## 好用的 skill／plugin（實戰驗證的優先選項）

原則：動手前先想「這類問題有沒有現成 skill」，有就用，不要土炮重造；但真正符合任務才叫用（優先權排序依平台見全域 `CLAUDE.md`／`AGENTS.md`）。

具體清單（各類任務用哪個 skill、Figma 在 MCP 缺席時的 curl fallback）在 `../docs/skill-catalog.md`——那份不常駐，要用時再讀。清單內容一律以當前 session 公開的 skill／tool 名稱為準，不跨平台猜名稱。

## 查證過的 harness 事實

Agent 工具的 `model`／`effort` 可填值、`isolation: worktree` 等——**派工前要引用時再讀
`../docs/harness-facts.md`**（2026-08-22 從本檔搬出，查證日 2026-08-06，版本更新後要重新核對）。
