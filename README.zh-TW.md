# agents-guideline — 給 AI coding agent 的長期工作制度

讀者：想採用、安裝或維護這套工作制度的人與 AI agent

型別：入口

[English](README.md) | 繁體中文

## 這是什麼

這是一套裝進 `~/.claude/` 或 `~/.codex/` 就生效的工作制度，給 AI coding agent 遵守。Claude Code 與 Codex 各有一個最小全域入口：六條邊界加一張路由表。其餘內容拆成 skill、agent 合約與 rubric，用到才載入。目標是讓不同的 coding agent 在這個環境穩定產出可驗證的工作。

## 設計概念

設計的主軸是常駐內容最小化、其餘按需載入，並把「誰能宣稱完成」交給獨立驗收。

### 分層與載入時機

常駐內容只放每次開工都需要的，其餘一律按需載入。

| 層 | 裝在哪 | 何時載入 | 誰讀 |
|---|---|---|---|
| 全域入口 | `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` | 常駐，每個 session | 該平台的 agent |
| `judgment.md` | `~/.claude/rules/` | Claude 常駐全文載入；Codex 經路由表指向才讀 | Claude 全部 agent（subagent 也付成本）；Codex 按需 |
| 本機事實 | `~/.claude/host-facts.md` | 常駐，每台機器只裝自己那份 | 該平台的 agent |
| controller 路由卡 | `~/.claude/route-card.md` | SessionStart hook 只注入主對話 | 主對話（controller） |
| skills | `~/.claude/skills/`、`~/.agents/skills/` | 依 description 比對才載入 | 命中描述的 agent |
| agent 合約 | `~/.claude/agents/`、`~/.codex/agents/` | 派工時進入 subagent context | 被派工的 subagent |
| rubrics | `~/.claude/rubrics/` | 不自動載入 | verifier 合約引用，Codex `reviewer` 亦用 |
| `docs/` | repo 內，不安裝 | 不自動載入 | 維護者與 agent，需要時讀 |

`~/.claude/rules/` 是無條件常駐區，每個 session 都全文載入其中的檔，所以只裝 `judgment.md` 一份。路由卡不放這個區，subagent 不繼承。

### 角色模型：controller 與 verifier

主對話是 controller，規劃、實作、核對與回報，全部自己做。subagent 只剩三種用途：fresh-context 驗收、fresh code review、旁支查詢。平行開發由多個頂層 session 各在自己的 worktree 進行，不用實作型 subagent（v4，2026-10-29；量測依據見 `docs/reviews/v4-2026-10.md`）。

- controller（主對話）：開工在自己的 worktree，自己實作、自己修；CI 與 release 設定先把 diff 給使用者、取得當次授權才改。
- `verifier`：fresh-context，只判定不製作。
- 互相獨立的 issue 一 issue 一頂層 session（`worktree-session` skill），本 session 只盤點。

派工對照（節錄自 `global/claude/route-card.md`）：

| 工作 | 派給 |
|---|---|
| 驗收 | `verifier`，`model: opus`；所有文件 merge／轉 ready 前一律派，程式碼依 dispatch skill §1 分流，專案規則只寫 code-review 時仍適用 |
| 程式碼 diff 的 fresh review | fresh subagent 跑內建 `code-review` skill，主對話不自跑；是 verifier 的加項不是替代，修 finding 後依 dispatch skill §2 再驗 |
| 旁支查詢 | 答案在檔案裡（找哪些檔有 X、列清單、抓數字）：`Explore`，`model: haiku`；要讀多份長文歸納、跨來源比對、結論帶推理：`general-purpose`，`model: sonnet`；第二意見：`codex:codex-rescue` |
| 實作、修 bug、文件、規劃 | 不派，controller 自己做 |

### 每個座位的 model

每個座位的 model 各有一個設定點：便宜的預設給量大的座位，貴的能力只在單一任務需要時當次切。主對話吃 `settings.json` 的 `model`／`effortLevel`——工作型態是盤點、起 issue session、收回報的 controller，設 sonnet／high 這類便宜值就夠，單一重任務用 `/model` 當次切、不改 settings。issue session 由 `--model`／`--effort` 旗標固定在 opus／medium，`require-issue-session-model.sh` hook 保證旗標帶齊。`verifier` 吃 frontmatter，`Explore`／`general-purpose` 吃路由卡。各設定點與少了會怎樣見 [`docs/design/mechanism.md`](docs/design/mechanism.md)「每個座位的 model 在哪設、怎麼選」。

### 六條邊界

兩個平台的入口共用同一組六條邊界。語意逐條對應 `global/claude/CLAUDE.md`「邊界」與 `global/codex/AGENTS.md`「邊界」。

1. 專案規格優先於全域入口。
2. 無證據不宣稱完成；回報分三級，分級定義見下一節。
3. 對外或不可逆動作（發訊息、寄信、merge、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案）需本 session 當次授權，逐次、逐對象有效。
4. 驗證不自驗：驗收派 fresh-context `verifier`；Codex 的高風險驗收派 `sol_verifier`。
5. 同一 working tree 同時只有一個寫入者。
6. 可中斷的長任務要留可恢復脈絡，格式見 `handoff` skill。

### 證據與驗收收斂

完成宣稱要附可重跑的證據，驗收何時停止由 verifier 的四種狀態決定。

回報分三級：已驗證、待 CI、驗不了。已驗證要附可重跑的指令與輸出；標「驗不了」之前，先確認真的沒有工具能驗（`global/shared/rules/judgment.md`「完成的三個條件」）。

verifier 第一行依優先序回報狀態，由高到低：

| 狀態 | 意義 |
|---|---|
| `INCONCLUSIVE` | 有 UNSURE 或必要條件未判定；先補證據，不宣稱完成 |
| `OPEN` | 無缺證，但行為承載產物有 FAIL；修正後依風險分流 |
| `PROSE-ONLY` | FAIL 全是不影響行為的事實或引用問題；修完 read-back 即停 |
| `CONVERGED` | 必要條件全 PASS，無 FAIL 與 UNSURE；停止驗收 |

狀態語意出自 `global/shared/rules/judgment.md`「驗收的停止端」。不可逆副作用分兩側，決定驗收走一般還是高風險路徑（`judgment.md`「不可逆副作用的定義」）：

- 一般側：正常流程會做、事後可由系統重建或重送的操作，例如寫後端狀態、清本機快取、請求通知權限；走一般驗收。
- 高風險側：決策層級（架構、安全設計、權限模型）與無法重建或重送的效果，例如刪除或覆寫使用者資料、扣款、對外寄信；兩側都符合時以高風險側為準。

### 交接四張卡

交接用四張固定欄位的卡，收的人不必重讀對話；欄位定義在 `global/shared/skills/handoff/SKILL.md`。

| 卡 | 方向 | 用途 |
|---|---|---|
| brief 卡 | controller → subagent | 派工：目標、scope、驗收條件、回報格式 |
| 回報卡 | subagent → controller | 改動、完成狀態、驗證指令與輸出、分級 |
| verifier 判定卡 | verifier → controller | 第一行收斂標記，逐條 PASS／FAIL／UNSURE |
| session 交接卡 | session → 接手的 session 或 agent | 所在位置、已完成、待檢查、下一步、風險 |

### 寫規則的原則

規則只寫這個環境的 gotcha 與授權邊界，不寫通用做事方法。

- 模型本來就會的判斷不寫成決策樹，自我文件化的介面（agent 定義）不附填空範例。
- 同一條規則只有一個 canonical 位置。
- 只有每次開工都需要的內容才常駐。
- 教訓先進 `docs/lessons.md`，經 `maintain-guideline` 流程才升格為正式判準。

原則是「規則越少代表模型越強」，不是「規則越多越安全」。

### 兩平台同構

Claude 與 Codex 的入口是同一組邊界與路由表，只有平台措辭不同。

- `global/shared/`：共用的 skill、rubric、rules、hosts；改一處，兩邊同時生效。
- `global/claude/`、`global/codex/`：平台獨有的內容；Claude 側有 hook 與路由卡，Codex 側有調度規則與派工模板，兩邊各有 agent 定義。
- 角色刻意分版時各寫各的：Claude 的 `verifier` 涵蓋高風險驗收，Codex 的高風險驗收派 `sol_verifier`。
- 對照矩陣在 `.claude/skills/maintain-guideline/SKILL.md`「兩平台同步矩陣」。

## Skills

共用 skill 來自 `global/shared/skills/`，裝進 `~/.claude/skills/` 與 `~/.agents/skills/`。另有兩個 repo-only skill，只在本 repo 開工時載入。

| 名稱 | 何時觸發 | 裝在哪 |
|---|---|---|
| `dispatch` | 驗收、fresh review、旁支查詢、驗收後選修正路徑、卡住換路、要 compact 時 | 兩平台共用 |
| `handoff` | 寫 brief、回報、驗收判定，或收尾、離開、compact、交接時 | 兩平台共用 |
| `git-commit` | 寫 commit message 或 squash merge 標題時 | 兩平台共用 |
| `create-pr` | 要從 branch 開 Pull Request 時（含「可以開了」這類暗示） | 兩平台共用 |
| `worktree-session` | 開工建 worktree、多個獨立 issue 各開 session、清 worktree 時 | 兩平台共用 |
| `writing-principles` | 寫、改或驗收 README、接入指南、設計說明等長存文件時 | 兩平台共用 |
| `maintain-guideline` | 修改本系統本身（`global/**`、入口、`docs/lessons.md`）時 | repo-only |
| `usage-review` | 量 Claude Code session 的用量與派工行為時（成本拆帳、context 膨脹） | repo-only |

## Agents

Claude 側只自建 `verifier`，Codex 側維持自己的角色集；model 與 effort 鎖在各自的定義檔。

### Claude Code

`Explore`、`Plan`、`general-purpose` 是 Claude Code 內建的 subagent，用途由路由卡指定。

| 名稱 | 職責 | model | effort | tools |
|---|---|---|---|---|
| `verifier` | fresh-context 驗收：逐條判 PASS／FAIL／UNSURE，不參與製作 | `opus` | `medium` | Read, Bash, Glob, Grep, LSP |

### Codex

Codex 用 Luna、Terra、Sol 三個由低到高的層級。五個角色都是唯讀或只寫探針；實作與規劃留在主對話（實作型與規劃型角色於 v4，2026-10-29 日落）。

| 名稱 | 職責 | model | reasoning effort |
|---|---|---|---|
| `scanner` | 答案在檔案裡的旁支查詢：精確清單、分類、格式檢查、結構化抽取 | `gpt-5.6-luna` | `medium` |
| `explorer` | 要歸納推理的旁支查詢：跨檔追蹤、長文件與外部文件研究、影響範圍 | `gpt-5.6-terra` | `medium` |
| `reviewer` | 程式碼 diff 的 fresh-context 對抗式 review | `gpt-5.6-terra` | `high` |
| `verifier` | 一般驗收：fresh-context read-back，只判定不製作 | `gpt-5.6-terra` | `high` |
| `sol_verifier` | 高風險驗收：安全、不可逆、重大架構的 fresh-context 驗收 | `gpt-5.6-sol` | `high` |

## 安裝

完整步驟在 [`docs/install.md`](docs/install.md)，其「安裝對應」表列出每個檔裝到哪裡。依平台與權限擇一：

- **Claude Code，macOS／Linux**：symlink 版，repo 即唯一事實來源，改 repo 即時生效。
- **Codex，macOS／Linux**：`AGENTS.md` 與 skills 用 symlink，agent TOML 由同步器寫成實體檔。
- **Windows（PowerShell）**：用系統管理員 PowerShell，一次裝好 Claude Code 與 Codex 兩側。
- **實體檔同步版**：給不能提權的機器；用 `scripts/sync-profile.py` 寫成複本，改 repo 後要重跑。

新機器（`global/shared/hosts/` 沒有它的檔）照 [`docs/new-host.md`](docs/new-host.md)「新機器建檔（5 分鐘探測清單）」探測並建檔。裝好的東西在執行時怎麼運作（什麼時刻載入什麼、每支 hook 補哪條規則、`settings.json` 依賴哪些欄位、重建時兩半各要補什麼）見 [`docs/design/mechanism.md`](docs/design/mechanism.md)「運作機制」。`docs/install.md`、`docs/new-host.md`、`docs/design/mechanism.md`、`docs/repo-layout.md` 只有中文版。

## 目錄地圖

逐檔用途見 [`docs/repo-layout.md`](docs/repo-layout.md)「檔案結構」。

| 路徑 | 用途 |
|---|---|
| `CLAUDE.md`、`AGENTS.md` | 本 repo 自己的專案規格，不是全域入口 |
| `global/` | 會裝進 `~/.claude`、`~/.codex`、`~/.agents` 的全部內容 |
| `global/claude/` | Claude Code 專用：入口、路由卡、hook、agent 定義 |
| `global/codex/` | Codex 專用：入口、調度規則、派工模板、agent 定義 |
| `global/shared/` | 兩平台共用：judgment、skill、rubric、hosts |
| `.claude/skills/` | repo-only skill，不裝進全域 |
| `docs/` | 設計說明、理由、安裝指南與教訓日誌；不自動載入 |
| `scripts/`、`tests/` | 安裝同步器、用量量測腳本與測試 |

## 已知退化模式與預防（維護者必讀）

1. **儀式死**：模板照抄，驗收條件卻是空話 → 驗收條件要讓另一個 agent 只憑那句話判定過或不過，verifier 見到模糊條件直接判 FAIL。
2. **膨脹死**：每個坑都塞進規則 → 教訓先進 `docs/lessons.md`（活躍上限 8 條），升格落地後移進 `docs/lessons-archive.md`；規則檔碰到 tripwire 就排日落審查。
3. **常駐區膨脹死**：只在特定情境用的長內容放進常駐區，每個 session 都付固定成本 → 先問「每次開工都需要嗎」，不是就放 skill、rubric 或 `docs/`。
4. **過度規格化死**：為模型本來就會的判斷寫決策樹 → 套日落條款，規則只留這個環境的 gotcha，通用做事方法刪掉（`maintain-guideline`「瘦身協議」）。
5. **過時死**：模型名或工具參數換了，文件沒跟上 → 事實標探測日或查證日，引用前現查，過時就當場修。
6. **斷鏈死**：改檔名或標題後，路由指向不存在的位置 → 改名前 `rg --hidden` 掃全部引用，同一次修改一起改（`maintain-guideline`「路由完整性（防斷鏈）」）。
7. **繞過死**：「這個任務很簡單，不用照守則」 → 覺得規則不合理就走流程提出，不默默繞過。

## 誠實條款：這套系統補不了的

拆解、模板與 fresh-context 驗收能拉高**執行品質**，補不了**品味與模糊題**，例如長期架構取捨、文案語氣、功能該不該存在。遇到時依序：沿用 repo 既有慣例 → 用可用的最強模型 → 產出多個候選讓使用者選。仍然不夠就明說「這超出系統能保證的範圍」。
