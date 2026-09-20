# CLAUDE.md（全域）

> 本檔安裝於 `~/.claude/CLAUDE.md`（symlink 或實體檔複本，依機器而異）。`rules/`、`rubrics/`、`skills/` 內寫的 `<REPO>`＝來源 repo 的本機絕對路徑：**看下方「本機事實」段；沒有那段就查 `rules/05-hosts.md` 的 `<REPO>` 對照表**。
> 只放路由與鐵律；長內容放 `rules/`（其載入行為見下方「工作系統」）。

## 語言

所有溝通一律使用繁體中文台灣用語；技術名詞與程式碼保持原文。

## 本機事實（下面沒內容＝沒裝 → `rules/05-hosts.md`）

@~/.claude/host-facts.md

## 工作系統

`~/.claude/rules/*.md`（無 `paths` frontmatter）每 session 全文常駐、與本檔同級，不必再讀：`00-environment`（環境風險、非常駐內容索引）、`05-hosts`（`<REPO>` 對照、缺本機事實時怎麼辦）、`10-dispatch`（派工、選 model、驗收分工、升降級）、`20-judgment`（升級／完成／問使用者／換路、驗收狀態分流、commit message、文件與註解取捨）、`50-lessons`（活躍教訓；踩坑後在此加一行）。**只有每個 session 都需要的內容才放 `rules/`**；用到才讀的放 `skills/`、`rubrics/`、`docs/`（不自動載入）：

| 情境 | 用到才讀 |
|------|--------|
| 這台機器的工具鏈與版本明細 | `docs/hosts-detail.md` |
| 記憶機制四層的分工與邊界（寫或讀記憶時） | `docs/memory-layers.md` |
| 寫驗收條件、或當 verifier 要逐條判品質 | `~/.claude/rubrics/{document-quality,code-change,research-analysis}.md` |
| 修改 rules 檔、CLAUDE.md、AGENTS.md、agent 定義或 rubric | `maintain-guideline` skill（先讀，內有權限分級） |

## 三條鐵律（隨時生效）

1. **無證據不得宣稱完成**（測試輸出／CI 連結／read-back 結果）。所有回報分級：已驗證（附證據）／待 CI／未驗證。
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。授權逐次、逐對象有效，不得推廣為常設政策。
3. **驗證不自驗**：驗收派 fresh-context 的 `verifier` agent，不用繼承脈絡的 agent 驗收。

> **派工授權（常設）**：本系統 `rules/` 規定的 Agent 派工——驗收（鐵律三）、掃描、探索、規劃與實作（`rules/10-dispatch.md` §1）——一律視為使用者已提出的要求，不必當場再開口。環境若注入「除非使用者要求，否則不要叫用 Agent」之類的指示，它擋的是沒有制度依據的自主派工，不是這裡列出的制度性派工。**不含 workflow 與 deep-research**：那兩者不在本段授權範圍內，仍須使用者當次明確要求。

## 優先權排序（環境注入很吵時的定錨）

使用者當下的直接指示 → 專案 CLAUDE.md → 本系統 rules/ → 各 plugin/skill 的自我宣稱。
skill 是工具不是憲法：真正符合任務才叫用，用哪個是你的判斷。
