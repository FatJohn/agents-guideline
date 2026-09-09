# 00 — 環境事實與結構性風險

> 本檔只放**跨機器皆真**的結論；單機事實（工具鏈、驗證能力）在 `05-hosts.md`，開工前先去認機器。
> **跨機器事實**的查證日以本檔檔頭為準：**2026-08-06**（單機事實的探測日各自記在 `05-hosts.md`；個別條目另帶戳記者，以其戳記為準）。距今超過 90 天，先當場核對再引用，核對後更新此日期。事實過時就更新本檔，不要另開新檔。

## 使用者背景（最低必要認知）

- 使用者：FatJohn（JohnShu），繁體中文台灣用語溝通。任職 TVBS（GitHub org：`tvbstw`），公司與個人專案並行。
- 專案清單一律現查：`gh repo list`（個人）、`gh search repos --owner tvbstw`（公司），本檔不列舉。
- 技術背景：C#／.NET／WPF／UWP 熟、C++ 部分會；Flutter、TypeScript 可；JavaScript／Vue 一般、React 初學。**後端與雲端架構不熟**——個人專案部署以 Zeabur 為主；財經專案另碰過 CloudFront＋自有 domain、R2 storage。涉及雲端架構的建議要多給脈絡、少假設既有知識。

## LLM 資源（先分流）

先辨識當前 runtime，只展開相符的一條；另一平台的 dispatch 檔留在 context 外：

- **Claude Code** → 只讀 `10-dispatch.md` §0「可用模型與 subagent」。
- **Codex** → 只讀 `../codex/rules/10-dispatch-codex.md` §0–1「角色與 runtime adapter／雙軸派工判斷」。

## 三大結構性風險與修法（按嚴重度）

### 1. 主對話下場做粗活 → context 塞爆 → compaction 失憶

**症狀**：大量讀檔、掃 repo、抓網頁、批次改檔在主對話進行，context 膨脹；compaction 觸發後早期決定遺失，開始重做已完成的工作或偏離原目標。

**修法**：
- 判斷基準（context 成本 × 任務獨立性）的 canonical 在 dispatch 文件：Claude `10-dispatch.md` §1「雙軸判斷：context 成本 × 任務耦合」；Codex `../codex/rules/10-dispatch-codex.md` §1「雙軸派工判斷」。
- session 內優先使用平台提供的 plan／task 狀態，不強制在 repo 建 scratchpad；跨 session 續接才使用 `session-handoff` skill 更新專案 `.codex/HANDOFF.md`——該 skill **只裝在 Codex 端**（`~/.agents/skills/`），Claude 端叫不到，Claude 的跨 session 續接靠 remember plugin 的 `.remember/` 與精選持久記憶。

### 2. 假完成：宣稱通過但沒有實際執行

**症狀**：說「測試通過」「已修好」但沒有跑過任何驗證，或驗證是自己看自己的產出。

**修法**：鐵律一（回報分級：已驗證／待 CI／未驗證）＋按產出風險分工驗證。完成的定義見 `20-judgment.md` §2；誰驗什麼、用哪份 rubric 見 `10-dispatch.md` §5。

### 3. 固定注入肥大：每個 session 開場漏掉數千 token

**症狀**：plugin 與 MCP server 每 session 注入工具清單、skill 描述與絕對化指令；skill 清單本身就是固定成本，跟用不用得到無關。（當下啟用了哪些 plugin 一律現查 `~/.claude/settings.json` 的 `enabledPlugins`，此處刻意不列舉——列了就會過時，而過時的清單比沒有清單更糟。）

**修法**：
- 抓住優先權排序（見全域 CLAUDE.md），不被注入音量牽著走。
- deferred MCP 工具只注入名稱——與任務無關的 schema 不要主動 ToolSearch。

## 非常駐內容索引（用到才讀）

動手前先想「這類問題有沒有現成 skill」，有就用，不要土炮重造。下面三份都不會自動載入：

| 什麼時候讀 | 讀哪份 |
|---|---|
| 要寫或讀記憶 | `../docs/memory-layers.md`——四層（自動事件史／精選持久記憶／顯式交接檔／repo 文件＝制度層）的分工與已知邊界 |
| 找這類任務有沒有現成 skill／plugin | `../docs/skill-catalog.md`——含 Figma 在 MCP 缺席時的 curl fallback；名稱一律以當前 session 公開的為準，不跨平台猜 |
| 派工前要引用 harness 事實 | `../docs/harness-facts.md`——`model`／`effort` 可填值、`isolation: worktree` 等（查證日 2026-08-06，版本更新後重新核對） |
