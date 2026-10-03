# agents-guideline — 給 AI coding agent 的長期工作制度

[English](README.md) | 繁體中文

## 核心概念

### 定位

一套裝進 `~/.claude/` 或 `~/.codex/` 就生效的工作系統：模型調度規則、判斷準則、驗收 rubric、驗收 agent、維護協議。目標：讓不同 coding agent 在這個環境都能穩定產出可驗證的工作品質。

### 設計背景與寫作原則

設計背景：2026-07-06 由高階模型（Fable 5）一次性建立，供之後所有 session 長期沿用。結構借鏡自 `goad-dot-claude`；機器差異隔離在 `hosts/<key>.md`（每台機器只裝自己那份；macOS 主力機＋Windows 桌機，新機器由 AI 探測建檔，`<REPO>` 對照表在 `rules/05-hosts.md`）。

寫作原則（2026-07-25 依 [Claude 5 世代的 context engineering 指南](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) 修正）：**寫這個環境的 gotcha 與授權邊界，不寫通用做事方法**。模型自己就會的判斷不寫成決策樹；自我文件化的介面（agent 定義）不附填空範例；同一條規則只留一個 canonical 位置；只有每次開工都需要的內容放進常駐的 `rules/`。原則是「規則越少代表模型越強」，不是「規則越多越安全」。

### 常駐區與「用到才讀」

⚠️ **`~/.claude/rules/` 是無條件常駐區**：Claude Code 每 session 全文載入其中無 `paths` frontmatter 的 `*.md`，付的是每個 session 的固定 context 成本。所以只有「每次開工都需要」的內容放 `rules/`；只在特定情境才用得到的長內容放 `skills/`（維護協議）、`rubrics/`（驗收判準）或 `docs/`（封存與情境化參考），這三個目錄**不會自動載入**。

### 三條鐵律

1. **無證據不得宣稱完成**（測試輸出／CI 連結／read-back 結果）。所有回報分級：已驗證（附證據）／待 CI／未驗證。
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。授權逐次、逐對象有效，不得推廣為常設政策。
3. **驗證不自驗**：驗收派 fresh-context 的驗收 agent，不用繼承脈絡的 agent 驗收。分工細節：Claude `rules/10-dispatch.md` §5「驗證不自驗」；Codex `codex/rules/10-dispatch-codex.md` §6「驗證語意」。

### 已知退化模式與預防（維護者必讀）

1. **儀式死**：模板照抄但驗收條件寫成空話 → 判準：另一個 agent 能不能只憑那句話判定過或不過；verifier 見到模糊條件直接 FAIL
2. **膨脹死**：每個坑都塞進規則 → 教訓只進 `rules/50-lessons.md`；升級成正式判準要走 `maintain-guideline` skill 的流程；行數／bytes 門檻觸發瘦身；升級落地後把該條教訓移進 `docs/lessons-archive.md`，不要讓同一件事在常駐區佔兩份
3. **常駐區膨脹死**：把只在特定情境用得到的長內容放進 `rules/` → 每個 session 都付固定成本。判準：這份內容是不是「每次開工都需要」？不是就放 `skills/`／`rubrics/`／`docs/`
4. **過度規格化死**：為模型本來就會做的判斷寫死決策樹、為自我文件化的介面附填空範例 → 規則互相衝突、模型多耗推理。日落條款（`maintain-guideline` skill §5）就是解法：規則是不是在講「這個環境的 gotcha」還是「通用做事方法」？後者刪掉
5. **過時死**：模型名/工具參數換了文件沒跟上，整套失去公信力 → 事實帶查證日期、90 天過期重核、爛一條修一條
6. **斷鏈死**：檔案改名路由指向不存在的路徑 → 改名前 `rg` 掃引用；斷鏈是 P0
7. **繞過死**：「這個任務很簡單不用照守則」→ 簡單任務正是 context 塞爆的起點；覺得規則不合理走流程提出，不准默默繞過

### 誠實條款：這套系統補不了的

拆解、模板、fresh-context 驗收能拉高**執行品質**；**品味與模糊題**（長期架構取捨、文案語氣、功能該不該存在）補不了。遇到時依序：沿用 repo 既有慣例 → 用可用的最強模型 → 產出多個候選讓使用者選 → 明說「這超出系統能保證的範圍」。

## 安裝

完整步驟（含裝完驗證與注意事項）在 [`docs/install.md`](docs/install.md)。依平台與權限擇一：

- **Claude Code，macOS／Linux**：macOS／Linux 上的 Claude Code；symlink 版，repo 即唯一事實來源，改 repo 即時生效。
- **Codex，macOS／Linux**：macOS／Linux 上的 Codex；`AGENTS.md` 與 skills 用 symlink，agent TOML 由同步器寫成實體檔。
- **Windows（PowerShell）**：Windows；要用系統管理員 PowerShell，一次裝好 Claude Code 與 Codex 兩側。
- **實體檔同步版**：不能提權的機器；用 `scripts/sync-profile.py` 寫成實體檔複本，改 repo 後要重跑同步器。

新機器（`hosts/` 沒有它的檔）照 [`docs/new-host.md`](docs/new-host.md)「新機器建檔」探測並建檔。`docs/install.md`、`docs/new-host.md`、`docs/repo-layout.md` 只有中文版，agent 與規則引用的就是它們。

## 目錄地圖

逐檔用途見 [`docs/repo-layout.md`](docs/repo-layout.md)「檔案結構」。

| 路徑 | 用途 |
|------|------|
| `CLAUDE.md`、`AGENTS.md` | 全域入口（Claude Code／Codex 各一份）：只放路由與鐵律 |
| `rules/` | **每 session 自動載入（常駐）**：只放每次開工都要的守則 |
| `hosts/` | 單機事實 `hosts/<key>.md`；經全域 `CLAUDE.md` 匯入、同為常駐，每台機器只裝自己那份 |
| `skills/`、`rubrics/`、`docs/` | **用到才讀，不自動載入**：維護協議與共用 skill、驗收判準、情境化參考 |
| `agents/` | Claude Code agent 定義：`worker`、`worker-opus`、`verifier` |
| `codex/` | Codex 專用：調度規則與派工模板、agent TOML、skill |
| `hooks/`、`config/` | 選配的 Claude Code hook（擋主對話改 CI 設定）與 ripgrep 設定（讓 Bash 的 `rg` 預設 `--hidden`）；安裝見 [`docs/install.md`](docs/install.md) |
| `scripts/`、`tests/` | 安裝同步器、日落審查量測腳本與測試 |
