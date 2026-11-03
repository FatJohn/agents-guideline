---
name: agent-rules
description: 建立或稽核某個專案 repo 的 AGENTS.md／CLAUDE.md 程式碼規則時使用：盤點常駐檔、詳細規則、AI reviewer 版本三層；把機械可驗的規則降級成 lint 或 CI 檢查而不留成散文；稽核常駐檔每條規則的標題能不能單獨判斷適用性；用單一來源加腳本產生索引並核對 reviewer 版本的 ID 與 severity。觸發詞：建 AGENTS.md、稽核 CLAUDE.md、整理專案規則、規則太多、哪些規則可以改 lint、"audit AGENTS.md"、"set up coding rules for agents"。不用於本工作系統自己的 rules／agents／skills（走 maintain-guideline），也不用於 README 等一般文件（走 writing-principles）。
allowed-tools: Bash(python3:*), Bash(rg:*), Bash(git:*), Bash(gh:*), Read, Grep, Glob
---

# agent-rules — 專案規則的三層、降級與標題稽核

> 讀者：要替一個專案 repo 建立或稽核 coding agent 規則的 session，語言不限。`<SK>` 指本 skill 的目錄（安裝後通常是 `~/.claude/skills/agent-rules` 或 `~/.agents/skills/agent-rules`）。寫法原則（context pointer、no-op 句、單一來源）引用 `writing-for-agents` skill（mattpocock-skills plugin），本檔不重述；裝了就讀它，沒裝不影響本檔流程。

## 前提：只有常駐檔會被讀到

常駐檔（`AGENTS.md`／`CLAUDE.md`）每個 session 全文載入；它連出去的規則文件只在 agent **已經判斷規則適用**之後才會被打開。所以常駐檔裡每條規則那一行是判斷「現在適不適用」的唯一依據，連結裡的本文只能放理由、取捨、範例、checklist，不能當觸發條件。

已知的平台差異有兩個：Claude Code 的 `CLAUDE.md` 支援 `@path` 自動匯入（匯入的內容也算常駐），Codex 的 `AGENTS.md` 沒有匯入機制；Codex 讀 `AGENTS.md` 有大小上限（設定鍵 `project_doc_max_bytes`，預設 32 KiB，超過的部分不載入；上限值讀自 Codex 0.164.0 的設定說明，截斷行為未實測），所以常駐檔的生成區塊要連同手寫段一起估 bytes。同一個 repo 兩種 agent 都用時以 `AGENTS.md` 為準、由腳本回寫區塊（§4），只有 Claude 的 repo 才可改用 `@docs/rules-index.md`。

## 流程

六步，每步有可判定的完成條件。稽核既有 repo 六步都做；從零建立跳過第 3 步（還沒有規則可稽核），第 2 步改成「把想寫的規則先過分類」。

### 1. 盤點三層

找出三層各在哪、怎麼被載入，列成表：

| 層 | 找法 | 載入方式 |
|---|---|---|
| 常駐檔 | `AGENTS.md`、`CLAUDE.md`、`.claude/CLAUDE.md`、`GEMINI.md`、`.cursorrules`、`.github/copilot-instructions.md` | 每 session 全文；Claude 另算 `@` 匯入 |
| 詳細規則 | 常駐檔連出去的 `docs/guideline_*.md`、`docs/code-review.md`、`CONTRIBUTING.md` 之類 | 只在 agent 主動開啟時 |
| AI reviewer 版本 | `.gemini/styleguide.md`、`.github/copilot-instructions.md`、`.coderabbit.yaml`、`.cursor/rules/` | 整份餵給 reviewer |

再找出已經存在的機械守門：lint 設定檔、架構測試（例如 import 方向的單元測試）、CI 裡的 grep 型檢查、產生索引的腳本。**完成條件**：三層每層都有「檔案路徑＋載入方式」或明寫「無」；機械守門列出指令與它守的是哪幾條規則。

### 2. 每條規則過分類，機械可驗的降級

把三層裡的每條規則列成一行，給它一個分類與證據。分類的對象是**規則**，不是程式碼：問的是「這條規則有沒有東西在機械地擋」，不是「程式碼哪裡違規」；既有違規多半是規則建立前寫的，命中數只當「開了這個 lint 會咬到多少」的附註，不列成 finding。

| 分類 | 定義 | 證據 | 動作 |
|---|---|---|---|
| A 已擋 | 啟用中的 lint／編譯器／既有測試已經會擋 | lint 名稱＋**啟用狀態的實跑輸出**（不是套件文件） | 從規則文件刪掉，常駐檔最多留一句「lint 走 X，排除項見設定檔」 |
| B 可擋未擋 | 有現成 lint 沒開、有 lint 套件但 plugin 沒跑、或一行 `rg`／一個單元測試就能擋 | lint 名稱與目前狀態，或 `rg` 指令＋命中數 | 開 lint 或加 CI 檢查，規則隨之刪掉；暫時開不了（版本相容、大量既有違規）才留規則並在規則旁註明阻礙 |
| C 判斷 | 需要讀上下文才能判（設計取捨、放哪一層、何時拆） | 寫出為什麼不能機械判 | 留在規則文件，進第 3 步 |

查啟用狀態的方法各語言不同，見 `references/<language>.md`；有頁的語言照頁上的指令跑，沒頁的語言先找「怎麼列出目前啟用的規則」那個指令，列在報告裡。兩個已實測會漏的形狀：規則文件說「要做 X」但 lint 設定把對應規則明確關掉（規則與設定互相矛盾，要麼開 lint 要麼刪規則，不能兩邊都留）；lint 套件在依賴清單裡但執行它的 plugin 停用，整包其實沒在跑。

**完成條件**：每條規則有分類與證據；A 與 B 的證據是指令輸出，不是「應該有」；B 類每條有對應的 lint 名稱或檢查指令。

### 3. 稽核常駐檔的每一行

對第 2 步留下的 C 類，逐條看常駐檔裡代表它的那一行（手寫摘要或產生的標題），三個問題：

1. **觸發範圍**：本文列的觸發點，標題都寫到了嗎？本文說 X 與 Y 都算、標題只寫 X，agent 遇到 Y 會判不適用。
2. **判準內容**：標題寫的是判準本身，還是「依某個判準決定」？「用 consumer-count 決定要不要升格」看了不能行動，要寫成「被 2 個以上 feature 用到就升格」。
3. **漂移**：只出現在手寫摘要、規則文件與 reviewer 版本都沒有的條目；或三處 severity、觸發條件不一致。

原則性條目（「遵循 SOLID」）本來就沒有更具體的觸發條件，不改；改的是標題，不是另外寫一份摘要（多一份來源就多一處漂移）。**完成條件**：每條有「通過」或「改寫成：…」；改寫後的標題一行就能讓另一個 agent 判出適不適用（`~/.claude/rules/judgment.md` 12『驗收條件要能被判定』的同一個測試）。

### 4. 單一來源與產生

規則文件是唯一來源，常駐檔的規則區塊與索引由腳本產生，reviewer 版本的 ID 與 severity 由同一支腳本核對：

- 規則標題格式 `### 標題（SEVERITY）`，有 reviewer 版本對應的加 `<!-- D-3 -->` 形式的 ID；severity 用 CRITICAL／HIGH／MEDIUM／LOW。
- 設定檔 `<repo>/.agent-rules.conf`：`SOURCES=<path>|<label>, …`（必填）、`SYNC_TARGETS`（預設 `AGENTS.md`）、`INDEX_OUTPUT`、`STYLEGUIDE`、`STYLEGUIDE_RE`（具名群組 `rid`、`severity`）、`TRACKED_PREFIXES`、`SEVERITIES`。
- 常駐檔放一組 `<!-- BEGIN GENERATED RULES -->`／`<!-- END GENERATED RULES -->` 標記，跑 `python3 <SK>/scripts/rules_index.py --repo <repo>` 產生；CI 跑 `--check`，不同步或 ID／severity 不一致就非 0。`--list` 印每條的 severity、ID、來源行與標題，第 3 步的逐條稽核用它當清單。
- 常駐檔的手寫摘要只留「lint 看不出來、最常踩、值得講兩次」的少數幾條，每條帶連結到規則本文的章節；其餘靠產生的標題清單。
- reviewer 版本（Gemini styleguide 等）的條文是另一種語言另一個讀者，腳本不比對本文，只綁 ID 與 severity；本文同步靠第 3 步的漂移檢查。

**完成條件**：`rules_index.py --check` 以 0 結束；CI 有這條；常駐檔的生成區塊在 git diff 裡與來源同步。

### 5. 審查 brief 要求對照規則

常駐檔連出去的規則不會自動被 reviewer 讀到。派 fresh code-review 或 verifier 時，brief 固定加一句：「逐條對照 `<規則文件路徑>` 的 `<章節>`，每個 finding 引用規則 ID 或標題，沒有對應規則標 AD-HOC」。留言品質照 `~/.claude/rubrics/review-findings.md`。**完成條件**：專案的 review 流程文件或常駐檔有這句，brief 模板照抄。

### 6. 交付與授權

產出一份稽核報告，照 `references/report-template.md` 的結構寫：結論在前、「建議修改」是獨立主章節且每條四行（改什麼、問題、改法、改完避免）、「不用動的」一節、步驟 1 到 3 的表格與跑過的指令進附錄 1–4 並各帶一句解釋、最後一段是可直接貼給 agent 的執行 prompt（建議編號、授權範圍、驗收條件）。報告的讀者是沒讀過本 skill 的人，章節不用步驟名，A／B／C、常駐檔、brief 這些詞第一次出現就解釋。報告先交，**改專案的 `AGENTS.md`／`CLAUDE.md` 與 lint 設定要另外取得當次授權**（這兩類檔可能是團隊共用；改 CI 設定依 dispatch skill §3 先給 diff）。驗收派 fresh-context verifier：重跑 `rules_index.py --check` 與第 2 步的 lint 狀態指令，對第 3 步的改寫抽樣 5 條判「一行能不能判定適用」。**完成條件**：報告通過範本「寫法檢查」段的每一條（以範本為準，不在本檔重抄）；三組建議與「不用動的」沒有內容就寫「無」；每個改檔動作都對得上使用者當次的授權句；verifier 判定已回且第一行是 CONVERGED 或 PROSE-ONLY，其餘狀態照 dispatch skill §2 處理後才算完成。

## 不做

- 不把規則文件整份搬進常駐檔（常駐成本倍增，重要規則被稀釋）。
- 不替規則文件另寫第二份摘要。
- 不只讀 lint 套件的規則清單就判 A 類；一律看啟用狀態的實跑輸出。
- 不碰本工作系統自己的 rules／skills（走 `maintain-guideline`）。

## 參考頁

- `references/report-template.md`：稽核報告的結構、每條建議的四行格式與交付前的寫法檢查。
- `references/dart-flutter.md`：Dart／Flutter 的啟用 lint 查法（`scripts/active_lints_dart.py`）、常見散文規則對應的 lint 名稱、grep 型閘門範例。
- 其他語言尚無參考頁：第 2 步照「先找列出啟用規則的指令」做，做完把查法補成新的一頁（ESLint `--print-config`、Ruff `ruff rule --all`／`ruff check --show-settings`、.NET `.editorconfig` 的 `dotnet_diagnostic.*` 與 `dotnet format --verify-no-changes` 是已知起點，未實測）。
