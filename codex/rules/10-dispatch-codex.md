# 10C — Codex 模型調度守則

> 讀者：Codex 主對話（controller）。每次要派工、選模型或驗收之前照著做。
> 本檔是 `rules/10-dispatch.md` 的 Codex 版；Claude Code 專用的 Agent 工具參數不要套到這裡。

## 0. Codex 可用角色（以當前 session 實際工具為準）

| 角色 | Agent／effort／權限 | 用途定位 |
|------|--------------------|----------|
| `scanner` | Luna／medium／read-only | 精確清單、分類、格式檢查、資料抽取 |
| `explorer` | Terra／medium／read-only | repo 探索、跨檔追查、文件研究、影響範圍分析 |
| `planner` | Terra／high／read-only | 非平凡任務的 scope、風險、invariants、執行計畫與完成條件 |
| `worker` | Luna／max／workspace-write | Plus 檔位依 plan 實作、除錯、執行機械驗證 |
| `pro_worker` | Terra／xhigh／workspace-write | Pro 檔位依 plan 實作；依失敗型態選 fresh Terra recovery 或 Sol escalation |
| `recovery_worker` | Terra／xhigh／workspace-write | Plus Luna 或 Pro Terra 實作者失敗／揭露高風險後的 fresh-context root-cause recovery 實作 |
| `reviewer` | Terra／high／read-only | 一般實作的 fresh-context 對抗式 review |
| `verifier` | Terra／high／read-only | 一般 read-back、文件與驗收審查 |
| `escalation_planner` | Sol／xhigh／read-only | Terra planner／explorer 無法建立可靠方案時的 root-cause 規劃升級 |
| `escalation_worker` | Sol／xhigh／workspace-write | recovery 再失敗、確認需要 Sol，或 Pro Terra 能力天花板型失敗時的 final root-cause 實作 |
| `sol_verifier` | Sol／high／read-only | 安全、不可逆、重大架構與正式高風險驗收 |

`scanner` 使用 Luna 做低風險、可機械驗證的唯讀工作；Plus 使用 `worker/Luna max`，Pro 使用 `pro_worker/Terra xhigh`，兩者都只可寫入父任務明確授權的 working tree 與範圍。`recovery_worker` 以 Terra xhigh 接手任一標準實作者失敗或揭露高風險的情況，並先建立 root cause；與 Pro 失敗者同階時，價值在 fresh context 與強制 root-cause 合約。`planner`、`explorer`、`reviewer`、`verifier`、`escalation_planner`、`sol_verifier` 都是 read-only。`reviewer` 處理一般實作 review；一般文件與一般驗收使用 `verifier/Terra high`；安全、不可逆、重大架構與正式高風險驗收才升級 `sol_verifier/Sol high`。`escalation_planner` 只處理規劃／探索升級；`escalation_worker` 處理 recovery 仍不足或 Pro Terra 能力天花板型失敗；所有 verifier 只找碴與判定，不製作也不修正產物。

角色名稱使用底線，因目前 `spawn_agent.task_name` 只接受小寫英數與底線。主力 Mac 的 Codex 0.144.4 collaboration v2 已實跑觀察到 custom role 可能未被傳入 child；每次派 custom agent 都必須 read-back child session metadata：只有 `agent_role` 明確等於指定角色，才能宣稱該 TOML 的 model、effort、sandbox 與 developer contract 已套用。若 `agent_role:null`、role 不符或 surface 沒有 agent-type 選擇入口，該 custom role 視為 **runtime unavailable**；不得把同名 generic child 當作成功載入，也不得依它的回答反推 contract。此時留在 controller、改用當前 surface 已明確提供的角色，或標記「模型未驗證」後停止該 routing。

## 1. 雙軸派工判斷

派工同時看兩軸：**任務獨立性**（能否只靠完整 prompt 獨立完成）與**脈絡／輸出成本**（原始內容是否會淹沒主對話、後續是否需要全文）。角色選擇再依風險與可機械驗證程度決定。

### 預設 workflow 與最低模型原則

使用「能可靠完成該階段的最低 model tier」，並把 model tier 與 reasoning effort 分開判斷；不要只因任務困難就直接使用 Sol Ultra。

**入口檔位依訂閱事實**（`rules/00-environment.md`）：Plus 主對話預設 Terra/high，標準實作用 `worker/Luna max`；Pro 主對話預設 Terra/xhigh，標準實作用 `pro_worker/Terra xhigh`。方案未知或環境事實未查證時不得猜測，先回 controller 查明。掃描、探索、一般規劃／review／驗收與 Sol 高風險角色不因 Pro 全面升級；Pro 的額外額度優先用在非機械實作入口。

- 小型、範圍明確、驗收條件清楚的修改留在主對話；不強制經過昂貴的規劃階段。
- 非平凡實作依訂閱使用 `planner/Terra high → worker/Luna max（Plus）或 pro_worker/Terra xhigh（Pro）→ reviewer/Terra high`。
- `planner` 只檢查 repo、列出未決問題與提出 plan；controller 負責和使用者釐清 scope、取得授權、做最後決策。
- `worker`／`pro_worker` 依 plan 分階段實作、執行測試／靜態檢查並修復一般失敗；不得自行擴大範圍或執行對外動作。
- `reviewer` 做一般實作的 fresh-context review；一般文件與一般驗收改派 `verifier/Terra high`，安全、不可逆、重大架構與正式高風險驗收才改派 `sol_verifier/Sol high`。
- 若 planner 的 Terra high plan 仍卡在高難度推理，controller 可先以 fresh-context `planner/Terra xhigh` 重試，再進入 `escalation_planner/Sol xhigh`。
- 若 Plus worker/Luna max 在同一子任務失敗兩次，或任一標準實作者揭露架構／安全／資料遺失風險，先進入 `recovery_worker/Terra xhigh`。若 Pro pro_worker/Terra xhigh 失敗兩次，context 汙染型或型態難辨走同階 fresh recovery；能力天花板型可直升 `escalation_worker/Sol xhigh`。recovery_worker 再失敗兩次或確認 root cause 需要 Sol 能力時，才升 Sol。
- `Sol max` 不作為固定 agent route；只有 `Sol xhigh` 仍無法收斂、或 controller 明確判定是最困難的單一路徑任務時才顯式使用。若需要可獨立平行的大型工作流，且當前 runtime 明確支援 Sol Ultra，才可使用。

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

- `scanner` 出現一次實質錯誤，或任務變成跨檔推理、不可機械驗證 → 升級 `explorer` 或 `planner`。
- `planner` 或 `explorer` 無法提出 affected files、invariants、failure modes、rollback strategy、validation commands 與 completion criteria → 先以 fresh-context `planner/Terra xhigh` 重試；仍無法建立可靠方案才升級 `escalation_planner/Sol xhigh`。prompt 必須附原始需求、目前 plan、完整探索／失敗輸出與已嘗試 hypotheses，且 Sol 必須先建立 root cause 與可靠策略。
- Plus `worker/Luna max` 在同一子任務失敗兩次（無論錯誤相同與否）→ 升級 `recovery_worker/Terra xhigh`（跳階＋fresh）。
- Pro `pro_worker/Terra xhigh` 在同一子任務失敗兩次 → context 汙染型（錯誤仍在演變、越修越糟、開始疊 workaround）改派同階 fresh `recovery_worker/Terra xhigh`；能力天花板型（反覆撞同一面牆、理解正確但解不動）可直升 `escalation_worker/Sol xhigh`；型態難辨時先走 fresh Terra recovery。
- 任一標準實作者揭露架構／安全／資料遺失風險 → 先升級 `recovery_worker/Terra xhigh` 建立 root cause；不得只因風險標籤直接跳 Sol。recovery_worker 若在同一子任務再失敗兩次，或確認 root cause 需要 Sol 能力，才升級 `escalation_worker/Sol xhigh`。
- 所有升級 prompt 都必須附訂閱入口、原始需求、approved plan、相關 diff 與**對應門檻的證據**：失敗入口附完整失敗輸出與已嘗試 hypotheses；高風險入口附風險判定依據；「確認需要 Sol 能力」入口附 recovery 的 root cause 報告與判定理由；「Pro Terra 能力天花板直升」入口附 pro_worker 的兩次失敗軌跡與能力天花板判定理由。升級實作者必須先建立 root cause 再編輯。若 approved plan 不完整或需要擴大 scope，先停止並交回 controller 走 planner 路徑，不得把沒有 approved plan 的工作直接交給 recovery_worker。若任務本身需要對外或不可逆動作，worker／pro_worker／recovery_worker／escalation_worker 直接停止並交回 controller，由 controller 決定授權與後續路徑；任何 subagent 都不得代替 controller 執行外部或不可逆動作。
- `reviewer` 發現一般文件或一般驗收缺口 → 改派 `verifier/Terra high`；發現安全、不可逆、重大架構問題或正式高風險驗收需求 → 改派 `sol_verifier/Sol high`，不讓 reviewer 自行修正。
- 任一指定 model 回報 unsupported 或 unavailable → 停止宣稱該 model mapping 已驗證，改用已核准的 fallback 並標記「模型未驗證」；不得靜默繼承另一個 model。
- 升級角色（`recovery_worker`、`escalation_planner`、`escalation_worker`、`verifier`、`sol_verifier`）只處理能力需求，不取代使用者授權；對外或不可逆動作未在本 session 明確授權時，停止並交回 controller。
- `Sol xhigh` 卡住 → 先換 fresh-context Sol、取得獨立第二意見或重定義問題與驗收條件；只有仍需最終能力時，controller 才可顯式使用 `Sol max`。`Sol Ultra` 僅限可獨立平行的大型工作流。
- 高能力角色解出可重複且可機械驗證的 pattern 後，可把 pattern 寫入 prompt，降級交給較輕角色套用。
- 同一件事最多重試兩輪；兩輪仍失敗就換方法或依 `20-judgment.md` 向使用者取得方向。

## 6. 驗證語意（鐵律三）

- 主觀判斷、一般文件與一般驗收不得由製作者自我背書；交給 fresh-context `verifier/Terra high` read-back，逐條判 PASS/FAIL。安全、不可逆、重大架構與正式高風險產出改用 fresh-context `sol_verifier/Sol high`。
- 一般程式碼 review 可由 fresh-context `reviewer` 執行；它發現一般文件問題升級 `verifier`，發現高風險或正式驗收問題升級 `sol_verifier`。
- 測試、build、lint、實跑與 schema 驗證可由製作者執行，但回報必須附指令與輸出證據。
- 高風險程式碼除機械驗證外，再做一次 fresh-context `reviewer` 與 `sol_verifier` review。
- `verifier` 與 `sol_verifier` 的任務是假設產物有問題並找碴；只驗收與指出缺口，不修正產物。
