# 10C — Codex 模型調度守則

> 讀者：Codex 主對話（controller）。每次要派工、選模型或驗收之前照著做。
> 本檔是 `rules/10-dispatch.md` 的 Codex 版；Claude Code 專用的 Agent 工具參數不要套到這裡。

## 0. Codex 可用角色（以當前 session 實際工具為準）

| 角色 | Agent／effort／權限 | 用途定位 |
|------|--------------------|----------|
| `scanner` | Luna／medium／read-only | 精確清單、分類、格式檢查、資料抽取 |
| `explorer` | Terra／medium／read-only | repo 探索、跨檔追查、文件研究、影響範圍分析 |
| `worker` | 繼承父 session，通常 Sol／父 session 權限 | 實作、除錯、執行機械驗證 |
| `verifier` | Sol／high／read-only | read-back、文件與高風險產出審查、最終驗收 |

Luna 只做低風險、可機械驗證的唯讀工作；不得寫入、做架構或安全判斷、執行對外動作或最終驗收。`verifier` 只找碴與判定，不製作也不修正產物。

## 1. 雙軸派工判斷

派工同時看兩軸：**任務獨立性**（能否只靠完整 prompt 獨立完成）與**脈絡／輸出成本**（原始內容是否會淹沒主對話、後續是否需要全文）。角色選擇再依風險與可機械驗證程度決定。

優先派 subagent：

- 任務可獨立，且主對話只需要結論與證據。
- 輸出量大，後續決策不需要把全文帶回主對話。
- 有兩個以上互不依賴、可安全平行的子任務。
- 需要 fresh-context 或對抗式驗收。

留在主對話：

- 工作很小但與當下決策高度耦合。
- 需要頻繁讀寫共享可變狀態。
- 需要即時與使用者互動或取得授權。
- 平行寫入無法用獨立 worktree 隔離。

主對話負責與使用者溝通、整合證據、做決策，並 read-back 實際狀態；subagent 的摘要不能取代這些責任。

## 2. 工作目錄與執行安全

- 同一 working tree 同一時間只能有一個寫入者（single-writer）。
- 平行寫入必須各用獨立 worktree；只要共用 working tree，即使修改檔案不重疊也必須序列執行。
- blocking 任務不得只放在可能因休眠或背景 session 中斷而消失的背景執行；controller 必須保有可持續等待、重接或重跑的前景路徑。
- Subagent 回報不等於實際狀態。controller 必須 read-back `git status`、`git diff`、commit 狀態與驗證輸出，確認共享工作目錄的真實結果。
- 寫入型 prompt 必須指定 working tree 絕對路徑與寫入所有權；不同寫入者不得擁有重疊路徑。

## 3. 派工三件套

每個 subagent prompt 必含三段，缺一段就是不合格派工（模板見 `30-delegation-templates-codex.md`）：

1. **目標與動機**：要達成什麼、為什麼；subagent 看不到完整主對話，脈絡要自帶。
2. **驗收條件**：可機械判定的完成定義；判準是另一個 agent 能只憑這句話判定過或不過。
3. **回報格式**：規定回什麼、多長、哪些證據必要。

## 4. 回報與證據合約

- Subagent 只回結論與證據（檔案:行號、指令輸出關鍵行、URL），不得傾倒原始內容。
- 回報上限預設 30 行；長報告、大 diff、完整清單由父任務接手落檔，subagent 只回摘要與來源。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**。
- controller 整合回報後仍須 read-back 實際檔案與狀態；不把 agent 自述當作完成證據。

## 5. 升降級路徑

- Luna 有一次實質錯誤，或任務變成跨檔、不可機械驗證 → 升級 Terra。
- Terra 在同一子任務失敗兩次，或遇到架構、安全、資料遺失、不可逆、對外動作 → 升級 Sol。
- 升級 Sol 只處理能力需求，不取代使用者授權；對外或不可逆動作未在本 session 明確授權時，停止並交回 controller。
- Sol 卡住 → 換 fresh-context Sol、取得獨立第二意見，或重定義問題與驗收條件。
- 高能力角色解出可重複且可機械驗證的 pattern 後，可把 pattern 寫入 prompt，降級交給較輕角色套用。
- 同一件事最多重試兩輪；兩輪仍失敗就換方法或依 `20-judgment.md` 向使用者取得方向。

## 6. 驗證語意（鐵律三）

- 主觀判斷、文件與高風險產出不得由製作者自我背書；交給 fresh-context `verifier` read-back，逐條判 PASS/FAIL。
- 測試、build、lint、實跑與 schema 驗證可由製作者執行，但回報必須附指令與輸出證據。
- 高風險程式碼除機械驗證外，再做一次 fresh-context review。
- `verifier` 的任務是假設產物有問題並找碴；只驗收與指出缺口，不修正產物。
