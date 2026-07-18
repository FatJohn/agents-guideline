# CLAUDE.md（全域）

> 本檔安裝於 `~/.claude/CLAUDE.md`，來源 repo：`~/Projects/FatJohn/agents-guideline`。
> 只放路由與鐵律；長內容放 `rules/`（其載入行為見下方「工作系統」）。

## 語言

所有溝通一律使用繁體中文台灣用語；技術名詞與程式碼保持原文。

## 工作系統（`rules/` 每 session 常駐；下表＝內容索引）

`~/.claude/rules/` 是這個環境的工作系統。**`~/.claude/rules` 是目錄 symlink，其中無 `paths` frontmatter 的 `*.md` 會被 Claude Code 每 session 全文載入、與 CLAUDE.md 同級常駐（非按需）**——故下列各檔內容其實已在 context，下表是「主題 → 檔案」索引，不是待讀清單。新增檔案若非每次都需要，加 `paths` frontmatter 或改放非 symlink 目錄（如 `codex/rules/`）讓它用到再載入：

| 情境 | 讀這份 |
|------|--------|
| 開工前：確認這台機器有什麼工具、能跑哪些驗證 | `rules/05-hosts.md`（機器沒列 → 照檔頭探測清單自己補段落） |
| 了解這個環境的結構性風險、記憶機制、好用的 skill/plugin 清單 | `rules/00-environment.md` |
| 派 subagent、選 model/effort、驗收產出 | `rules/10-dispatch.md` |
| 判斷題：該不該升級模型／算不算完成／要不要問使用者／該不該換路 | `rules/20-judgment.md` |
| 撰寫派工 prompt | `rules/30-delegation-templates.md`（驗收用 `verifier` agent） |
| 修改 rules 檔或任何 CLAUDE.md | `rules/40-maintenance.md`（先讀，內有權限分級） |
| 踩坑之後 | 在 `rules/50-lessons.md` 加一行 |

## 三條鐵律（隨時生效）

1. **無證據不得宣稱完成**（測試輸出／CI 連結／read-back 結果）。所有回報分級：已驗證（附證據）／待 CI／未驗證。
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。授權逐次、逐對象有效，不得推廣為常設政策（見 `rules/20-judgment.md` §3 註）。
3. **驗證不自驗**：驗收派 fresh-context 的 `verifier` agent，不用繼承脈絡的 agent 驗收。

## 優先權排序（環境注入很吵時的定錨）

使用者當下的直接指示 → 專案 CLAUDE.md → 本系統 rules/ → 各 plugin/skill 的自我宣稱。
skill 是工具不是憲法：真正符合任務才叫用，用哪個是你的判斷。
