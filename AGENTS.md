# AGENTS.md（Codex 全域）

> 本檔安裝於 `~/.codex/AGENTS.md`，來源 repo：`/Users/fatjohn/Projects/FatJohn/agents-guideline`。
> 只放路由與鐵律；長內容放在本 repo 的 `rules/`，按需載入。

## 語言

所有溝通一律使用繁體中文台灣用語；技術名詞與程式碼保持原文。

## 工作系統（先讀路由表，需要時載入完整檔案）

本 repo 是 Codex 的環境級工作制度。開始任何多步驟任務前，依情境讀對應檔案：

| 情境 | 讀這份 |
|------|--------|
| 開工前：確認這台機器有什麼工具、能跑哪些驗證 | `/Users/fatjohn/Projects/FatJohn/agents-guideline/rules/05-hosts.md`（機器沒列 → 照檔頭探測清單自己補段落） |
| 了解環境的結構性風險、記憶機制、好用的 skill/plugin 清單 | `/Users/fatjohn/Projects/FatJohn/agents-guideline/rules/00-environment.md` |
| Codex 派 subagent、選 model/reasoning effort、驗收產出 | `/Users/fatjohn/Projects/FatJohn/agents-guideline/codex/rules/10-dispatch-codex.md` |
| 判斷題：該不該升級／算不算完成／要不要問使用者／該不該換路 | `/Users/fatjohn/Projects/FatJohn/agents-guideline/rules/20-judgment.md` |
| 撰寫 Codex subagent prompt | `/Users/fatjohn/Projects/FatJohn/agents-guideline/codex/rules/30-delegation-templates-codex.md`（一般驗收用 `verifier`；高風險驗收用 `sol-verifier`） |
| 收尾、交接、記錄目前進度、下次續接 | 使用 `session-handoff` skill，預設寫到專案 `.codex/HANDOFF.md` |
| 修改 rules 檔、`AGENTS.md`、`CLAUDE.md` 或 agent 定義 | `/Users/fatjohn/Projects/FatJohn/agents-guideline/rules/40-maintenance.md`（先讀，內有權限分級） |
| 踩坑之後 | 在 `/Users/fatjohn/Projects/FatJohn/agents-guideline/rules/50-lessons.md` 加一行 |

## 三條鐵律（隨時生效）

1. **無證據不得宣稱完成**：所有回報分級為已驗證（附指令輸出／CI 連結／read-back 結果）／待 CI／未驗證。
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。
3. **驗證不自驗**：一般文件與驗收用 fresh-context 的 `verifier` custom agent；安全、不可逆、重大架構與正式高風險產出用 `sol-verifier`；程式碼以實際測試／實跑輸出為證。

## Codex 專用注意

- Codex 的 `~/.codex/rules/*.rules` 是**命令權限規則**，不是本 repo 的 Markdown 工作守則；不要把本 repo 的 `rules/*.md` symlink 到 `~/.codex/rules/`。
- 本檔是使用者給 Codex 的全域 standing instruction：多步驟任務可依 `/Users/fatjohn/Projects/FatJohn/agents-guideline/codex/rules/10-dispatch-codex.md` 使用 subagent；若當前 surface 沒有 subagent 工具，就在主對話內完成並明說限制。
- Codex Memories 已作為精選長期記憶層；規則與可 review 的狀態仍寫進 repo 文件，session 收尾用 `session-handoff` skill。
- Subagent 預設繼承父 session 的 sandbox 與 approval 狀態；涉及外部網路、寫入受限路徑、對外動作時仍要遵守本 session 權限邊界。
- 使用者當下的直接指示 → 專案 `AGENTS.md` / `AGENTS.override.md` → 本全域 `AGENTS.md` → 本 repo `rules/` → skill/plugin 指令。skill 是工具不是憲法：真正符合任務才使用。
