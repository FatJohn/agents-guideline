# AGENTS.md（Codex 全域）

> 本檔以 symlink 安裝於 `~/.codex/AGENTS.md`。
> 只放路由與鐵律；長內容放在本 repo 的 `rules/`，按需載入。
>
> **下表的 `<REPO>` 是本系統 repo 的絕對路徑，依機器而異——讀檔前先認機器再展開**：
> - macOS（hostname `xushengzhedeMacBook-Pro.local`，2026-08-06 現查；hostname 會隨設定改名而變，對不上就走下面第三條的 `readlink`）：`/Users/fatjohn/Projects/FatJohn/agents-guideline`
> - Windows（hostname `FatJohn-PC`）：`E:\agents-guideline`
> - 不確定或新機器：`readlink ~/.codex/AGENTS.md`（PowerShell：`(Get-Item ~/.codex/AGENTS.md).Target`）的目錄部分就是 `<REPO>`；機器事實照 `<REPO>/README.md`「新機器建檔」的探測清單自己建檔，補進 `<REPO>/rules/05-hosts.md`。
>
> （這份對照表的 canonical 位置是 `<REPO>/rules/05-hosts.md`。這裡刻意重複一份是 bootstrap 需要——Codex 得先解出 `<REPO>` 才讀得到 05-hosts，不是可以合併掉的冗餘。新增機器時兩處都要加。）

## 語言

所有溝通一律使用繁體中文台灣用語；技術名詞與程式碼保持原文。

## 工作系統（先讀路由表，需要時載入完整檔案）

本 repo 是 Codex 的環境級工作制度。開始任何多步驟任務前，依情境讀對應檔案：

| 情境 | 讀這份 |
|------|--------|
| 開工前：確認這台機器有什麼工具、能跑哪些驗證 | `<REPO>/rules/05-hosts.md`（機器沒列 → 照 `<REPO>/README.md`「新機器建檔」的探測清單自己補段落） |
| 了解環境的結構性風險、好用的 skill/plugin 清單 | `<REPO>/rules/00-environment.md` |
| 記憶機制四層的分工與邊界（寫或讀記憶時） | `<REPO>/docs/memory-layers.md` |
| Codex 派 subagent、依 complexity signals 選 model/reasoning effort、判斷 retry／escalation、驗收產出 | `<REPO>/codex/rules/10-dispatch-codex.md` |
| 判斷題：該不該升級／算不算完成／要不要問使用者／該不該換路 | `<REPO>/rules/20-judgment.md` |
| 撰寫 Codex subagent prompt | `<REPO>/codex/rules/30-delegation-templates-codex.md`（A–L logical-role contract 與共用 runtime adapter envelope） |
| 收尾、交接、記錄目前進度、下次續接 | 使用 `session-handoff` skill，預設寫到專案 `.codex/HANDOFF.md` |
| 寫驗收條件、或驗收者要逐條判品質 | `<REPO>/rubrics/` 底下對應產出類型的 `document-quality.md`／`code-change.md`／`research-analysis.md` |
| 修改 rules 檔、`AGENTS.md`、`CLAUDE.md`、agent 定義或 rubric | `maintain-guideline` skill（或直接讀 `<REPO>/skills/maintain-guideline/SKILL.md`；先讀，內有權限分級） |
| 踩坑之後 | 在 `<REPO>/rules/50-lessons.md` 加一行（已升級成判準的歷史條目在 `<REPO>/docs/lessons-archive.md`） |

## 三條鐵律（隨時生效）

1. **無證據不得宣稱完成**：所有回報分級為已驗證（附指令輸出／CI 連結／read-back 結果）／待 CI／未驗證。
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。
3. **驗證不自驗**：一般文件與驗收優先派 fresh-context 的 named `verifier`；若 named role unavailable，依 Codex runtime adapter 使用 sandbox 強制 read-only 的 Terra/high direct CLI，只有 runtime 已是 read-only 時才可用實際 `agent_type=default` 與完整 logical `verifier` contract 做 generic read-back。安全、不可逆、重大架構與正式高風險產出優先派 named `sol_verifier`；generic Sol/high 只作補強，仍標記「未取得 custom `sol_verifier` 驗收／未驗證」。只有當前 surface 明確提供並選中指定 `agent_type`，或 child metadata 證實指定 role 時，才可視為 custom verifier；禁止把同名 generic child 冒充 custom role。程式碼以實際測試／實跑輸出為證；高風險驗收若兩種證據都沒有，必須標記「未驗證」，不得宣稱完成。

## Codex 專用注意

- Codex 的 `~/.codex/rules/*.rules` 是**命令權限規則**，不是本 repo 的 Markdown 工作守則；不要把本 repo 的 `rules/*.md` symlink 到 `~/.codex/rules/`。
- 每次派 subagent 前，必讀 `<REPO>/codex/rules/10-dispatch-codex.md`；呼叫工具前在 commentary 只報指定的 logical role 名稱與任務摘要。正常 named path 不例行回報 model／effort／permission／制度依據；named unavailable 而改用 `default` 或 direct CLI 時，在 role 名稱後標 `generic fallback`／`direct CLI fallback` 並簡述差異。完整 runtime 證據仍記在 adapter envelope，只有使用者詢問、runtime 不一致、unsupported／unavailable 或正式稽核時才展開；不得把 generic child 稱為 custom role。
- 本檔是使用者給 Codex 的全域 standing instruction：多步驟任務可依 `<REPO>/codex/rules/10-dispatch-codex.md` 使用 subagent；若當前 surface 沒有 subagent 工具，就在主對話內完成並明說限制。
- Codex Memories 已作為精選長期記憶層；規則與可 review 的狀態仍寫進 repo 文件，session 收尾用 `session-handoff` skill。
- Subagent 預設繼承父 session 的 sandbox 與 approval 狀態；涉及外部網路、寫入受限路徑、對外動作時仍要遵守本 session 權限邊界。
- 使用者當下的直接指示 → 專案 `AGENTS.md` / `AGENTS.override.md` → 本全域 `AGENTS.md` → 本 repo `rules/` → skill/plugin 指令。skill 是工具不是憲法：真正符合任務才使用。
