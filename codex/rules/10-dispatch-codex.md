# 10C — Codex 模型調度守則

> 讀者：Codex 主對話（controller）。每次要派工、選模型或驗收之前照著做。
> 本檔是 `<REPO>/rules/10-dispatch.md` 的 Codex 版；Claude Code 專用的 Agent 工具參數不要套到這裡。
> 下文的 `<REPO>` 同 `~/.codex/AGENTS.md` 檔頭定義（依機器而異；不確定就取 `readlink ~/.codex/AGENTS.md` 的目錄部分）。本檔位在 `<REPO>/codex/rules/`，寫成裸 `rules/…` 從這裡解析不到。

## 0. Codex 角色與 runtime adapter（以當前 session 實際工具為準）

| 角色 | Agent／effort／權限 | 用途定位 |
|------|--------------------|----------|
| `scanner` | Luna／medium／read-only | 精確清單、分類、格式檢查、資料抽取 |
| `explorer` | Terra／medium／read-only | repo 探索、跨檔追查、文件研究、影響範圍分析 |
| `planner` | Terra／high／read-only | 非平凡任務的 scope、風險、invariants、執行計畫與完成條件 |
| `worker` | Luna／max／workspace-write | 所有訂閱檔位依 approved plan 實作、除錯、執行機械驗證 |
| `pro_worker` | Terra／high／workspace-write | 已有複雜度證據時，預先承接跨模組、large-context 或高 ambiguity 實作 |
| `recovery_worker` | Terra／high／workspace-write | Luna 顯示能力／脈絡理解不足，或兩次未明失敗後的 fresh-context recovery |
| `reviewer` | Terra／high／read-only | 一般實作的 fresh-context 對抗式 review |
| `verifier` | Terra／high／read-only | 一般 read-back、文件與驗收審查 |
| `escalation_planner` | Sol／medium／read-only | Terra 已確認模型能力或高 judgment 成為限制時的 root-cause 規劃升級 |
| `escalation_worker` | Sol／medium／workspace-write | Terra 已確認模型能力不足後的 root-cause 升級實作 |
| `sol_verifier` | Sol／high／read-only | 安全、不可逆、重大架構與正式高風險驗收 |

`scanner` 使用 Luna 做低風險、可機械驗證的唯讀工作；一般實作使用 `worker/Luna max`。若開工前已有多 subsystem、依賴關係密集、脈絡量大、需求高 ambiguity 或 architecture judgment 等證據，可直接使用 `pro_worker/Terra high`，不必先犧牲一次 Luna 嘗試；失敗後的 Terra 路徑則使用 `recovery_worker/Terra high`。`planner`、`explorer`、`reviewer`、`verifier`、`escalation_planner`、`sol_verifier` 都是 read-only。一般文件與一般驗收使用 `verifier/Terra high`；安全、不可逆、重大架構與正式高風險驗收使用 `sol_verifier/Sol high`。Sol 升級實作與規劃先從 medium 開始，只有 exceptional difficulty 才提高 effort；所有 verifier 只找碴與判定，不製作也不修正產物。

**別名與主對話邊界**：Luna＝`gpt-5.6-luna`、Terra＝`gpt-5.6-terra`、Sol＝`gpt-5.6-sol`。本機新 session 的靜態預設是 Luna/max，讓一般 coding 不先支付 Sol 成本；使用者仍可在 UI 或 CLI 為特定任務明確選擇其他 model／effort，目前這種刻意使用 Sol/high 的高 judgment session 就屬於 override。global instruction 不能在已啟動的主對話中自動切換主 agent，只能指導 delegated agent、direct CLI，或下一個 session 的選擇。當前 runtime 若已是較強主 agent，仍按本表把可獨立工作派給能可靠完成的最低 tier。型號與 effort 可用性以當前 surface 或 `codex debug models` 現查；不要把可能過期的 `~/.codex/models_cache.json` 當 runtime 證據。

角色名稱使用底線，因目前 `spawn_agent.task_name` 只接受小寫英數與底線。安裝 `~/.codex/agents/*.toml` 與 runtime 選中角色是兩件事：派工前先看當前 surface 是否明確提供 `agent_type` 與該角色的 model／effort metadata。可選中時，把 surface metadata 當作「工具宣告值」記進 adapter envelope；若回傳或 child metadata 另有實際 runtime model／effort，再一併 read-back。surface 沒有角色選擇入口、role 不符或 runtime 證據與宣告不一致時，不得假裝 custom role 已套用；依下方 adapter 改用 `default`，或標記「模型／effort 未驗證」後停止該 routing。

### Runtime adapter（所有 A–L logical role 共用）

上表是唯一的 logical-role、model／effort、權限 mapping；A–L 模板提供完整 contract，不在此複製第二張角色表。`pro_worker` 重用 D 的 worker contract，替換為 Terra/high，並附觸發它的複雜度證據。每次派工先分開記錄兩個身份：`logical role` 是要完成的角色（例如 `reviewer`），`actual agent_type` 是當前 runtime 實際接受的 agent type。

1. **Named-first**：先檢查當前 surface 是否明確提供 `agent_type=<logical role>`，且 metadata 的 model／effort／權限符合上表；符合才以 named role 派送。surface metadata 先標「工具宣告值」，只有工具回傳或 child metadata read-back 的實際值才可升級為「runtime 已驗證」。若角色看似已註冊但回覆 unavailable，可在不修改 local config 的前提下 read-only 核對 `[agents.<name>]`／`config_file` 並於 fresh session 重試一次。
2. **Default／effort fallback**：surface 沒有 named selector、named call 回覆 `agent type is currently not available`、named metadata 不符合，或 exceptional route 需要同一 logical contract 搭配不同 effort 時，改以實際 `agent_type=default` 啟動；明確傳入選定的 model／effort，並在 prompt 寫入 permission contract 與 route evidence。override model／effort 時，`fork_turns` 必須用 `none` 或正整數；full-history fork 不接受 override。prompt 必須先放 `30-delegation-templates-codex.md` 的 adapter envelope，再接完整 logical-role contract。generic `default` 不得稱為 custom role；`default` unavailable 或無法接受 mapping 時停止並標記「runtime 未驗證」。
3. **Evidence／permission gate**：envelope 必須分開記錄 logical role、actual `agent_type`、fork context、requested model／effort、logical permission contract、runtime permission evidence 與其他 runtime evidence。surface 固定值是「工具宣告值」；child metadata 是「runtime 已驗證」；兩者都取不到就是「runtime 未驗證」。TOML、檔案存在、角色名稱或 prompt 內容都不能冒充 runtime 證據。generic `default` 沒有 sandbox override 時繼承父 session：寫入角色只有在父 session runtime 權限已知且涵蓋 approved scope 時可派；read-only 角色只有父 session runtime 已是 read-only 時可派，否則強制改走下方 read-only direct CLI branch 或停止，不得靠 prompt 禁寫與事後 read-back 補救。指定 model／effort 無法明確傳入時，停止並回 controller。
4. **Role transitions**：升級原因分類、single-writer、approved plan、權限與授權不因 adapter 改變；每次轉派都重新套用 named-first → fallback 與同一個 logical-role contract。generic reviewer／verifier／`sol_verifier` 都只能回報 generic review；generic Sol/high 只能補強高風險證據，仍標記「未取得 custom `sol_verifier` 驗收／未驗證」。

### Direct CLI review branch

read-only 的 `reviewer`、`verifier`、`sol_verifier` 或其他唯讀 logical role 若沒有可用 child surface，controller 可直接啟動 fresh process：

```bash
codex exec --ephemeral --strict-config --sandbox read-only \
  -m <上表對應 model> -c 'model_reasoning_effort="<上表對應 effort>"' \
  "<adapter envelope + 對應 A–L 完整 contract + 原始需求與驗收條件>"
```

若是程式碼 diff，可在同一組明確 model／effort 參數後使用 `review --uncommitted`。這個 `--ephemeral --sandbox read-only` process 本身就是單體 fresh reviewer，直接完成驗收，不在其中 nested spawn；CLI header 可驗證 model／effort，但不能證明 custom role。generic Sol review 仍只作補強，不能改寫高風險「未取得 custom `sol_verifier` 驗收／未驗證」的分級。

## 1. 雙軸派工判斷

派工同時看兩軸：**任務獨立性**（能否只靠完整 prompt 獨立完成）與**脈絡／輸出成本**（原始內容是否會淹沒主對話、後續是否需要全文）。角色選擇再依風險與可機械驗證程度決定。

### 預設 workflow 與最低模型原則

使用「能可靠完成該階段的最低 model tier」，優化 **total cost to success**：reasoning tokens、重讀 repo、tool calls、錯誤修改、retry 與人工修正都算成本。只在任務開始、scope 明顯改變或一次嘗試失敗後重判路由，不在每個步驟反覆做模型分析。model tier 與 reasoning effort 分開判斷；高 tier 不自動配高 effort，小模型也不自動配 max。

快速看六個 complexity signals：scope／檔案與模組廣度、subsystem 數量、dependency 與既有 code 理解量、ambiguity／debug search space、architecture／correctness／security judgment、既有失敗證據。任務名稱只提供背景，不決定 tier。

- **Simple／mechanical**：可明確描述且可機械驗證，使用 Luna low／medium（如 `scanner`）或留在主對話。
- **Normal development**：需求清楚、scope 有界的一般 feature、bug fix、refactor、test、UI／API 修改，使用 `worker/Luna max`；controller 可自行核定完整 plan，不強制先派 Terra planner。
- **Higher complexity／large-context reasoning**：上述 signals 有一項很強或多項同時成立，使用 Terra；探索可 medium，規劃、實作 recovery 與重要 review 用 high。已有充分證據時可預先派 `pro_worker/Terra high`。
- **Very difficult／high judgment**：Terra 已確認模型能力不足，或任務本身是高影響且需要跨 subsystem judgment，使用 Sol medium。
- **Exceptional difficulty**：Sol medium 仍顯示能力不足、或錯誤代價極高且可說明 high 的邊際價值，才使用 Sol high。xhigh／max 不設固定 route，僅在 high 仍無法收斂且 controller 有證據時顯式使用；Ultra 不是一般 coding route。

Reasoning effort 只回答「同一模型需要思考多深」：問題已理解但推理鏈不夠完整，可提高一級 effort 並 fresh retry 一次；若 root cause、跨模組關係或需求模型本身理解錯誤，應升 model tier，而不是持續加 effort。

- 小型、範圍明確、驗收條件清楚的修改留在主對話；不強制經過額外規劃或 review 階段。
- 一般實作由 controller 核定 approved plan 後派 `worker/Luna max`；只有 complexity signals 支持時才加入 `planner/Terra high`、`pro_worker/Terra high` 或 `reviewer/Terra high`。
- `planner` 只檢查 repo、列出未決問題與提出 plan；controller 負責和使用者釐清 scope、取得授權、做最後決策。
- controller 只有在 plan 已列出 affected files、寫入所有權、invariants、implementation phases、validation commands 與 completion criteria，且未決問題均已解決或明確交由 worker 不得碰觸時，才可標為 approved plan 並派 `worker`。缺任一項就留在規劃階段，不得用高 effort 取代清楚 plan。
- `worker` 依 approved plan 分階段實作、執行測試／靜態檢查並修復一般失敗；不得自行擴大範圍或執行對外動作。
- `reviewer` 做一般實作的 fresh-context review；一般文件與一般驗收改派 `verifier/Terra high`，安全、不可逆、重大架構與正式高風險驗收才改派 `sol_verifier/Sol high`。
- 若 planner 的 Terra high 已抓對問題但推理仍不足，可 fresh-context 提高 Terra effort 一次；若它誤判核心、遺漏跨模組關係或無法承載必要脈絡，直接進入 `escalation_planner/Sol medium`。
- retry／escalation 依 §5 的失敗原因處理；兩次失敗是未能判明原因時的硬上限，不是每條路都必須先浪費兩次。

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
- **唯讀角色也受影響**：`verifier`／`explorer`／`reviewer` 等 read-only 角色與寫入者共用 working tree 時，它的**唯讀結論**（檔案內容、路徑與指令是否存在）仍可信，但**任何跑測試／build 取得的數字**都被污染——工作區在它量測期間被改動過。要嘛等它跑完再動手，要嘛在 prompt 的工作目錄欄指定獨立 worktree 絕對路徑。
- 寫入型 prompt 必須指定 working tree 絕對路徑與寫入所有權；不同寫入者不得擁有重疊路徑。

## 3. 派工三件套

**派工揭露（controller → 使用者，每次派 subagent 都要）**：在呼叫工具前，commentary 只報**指定的 logical role 名稱與任務摘要**，例如「派 `scanner` 掃描設定」。正常 named path 不例行回報 actual `agent_type`、model、effort、permission 或制度依據。named unavailable 而改走 `default` 時標成「`<logical role>`（generic fallback）」；direct CLI path 標成「`<logical role>`（direct CLI fallback）」；建立失敗則回報「`<logical role>` 未建立」與 runtime 原因。使用者詢問、runtime 不一致、unsupported／unavailable 或正式稽核時，才展開 adapter envelope 內的 actual `agent_type`、model／effort、permission 與證據層級。不得把 TOML、角色名稱或 generic child 冒充 custom runtime 身份。

主對話自己做時，只有在符合 §1 任一派工條件卻仍不派時才要交代；例行讀檔、跑指令與對話不必。這段簡短揭露是給使用者看的派工狀態，不放進 subagent prompt 取代下面三件套；詳細稽核資料留在 adapter envelope。

Claude 端 `<REPO>/rules/10-dispatch.md` §3 使用同一套 user-facing 揭露：正常只報指定 role 名稱與任務摘要，fallback 才標差異。Codex 額外取得的 runtime metadata 留在 adapter envelope，不轉成每次 commentary；這是內部證據能力差異，不是使用者介面差異。

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
- **execution mistake**：syntax、漏改一處、指令拼錯或 fixture 小錯，且正確修法已明確 → 同 model 修正一次；若再失敗就重新分類，不把同一路線包裝成重試。
- **insufficient reasoning**：root cause 與相關脈絡已抓對，但推理鏈、比較或驗證深度不足 → 同 tier 提高一級 effort、換 fresh context 重試一次；不得連續加 effort。
- **insufficient model capability／context understanding**：抓錯問題核心、反覆遺漏跨模組關係、無法維持必要脈絡，或 architecture judgment 明顯不足 → 立即換 fresh context 並升一個 model tier，不必等第二次失敗。Luna 升 Terra/high；Terra 升 Sol/medium。
- **insufficient evidence／environment understanding**：缺 repo 事實、log、重現步驟或環境量測錯誤 → 先補查證或依 `<REPO>/docs/debug-environment-first.md` 校正量法；換更強模型不會補出不存在的證據。
- 失敗原因仍不明時，同一子任務最多兩次未收斂嘗試；達上限就升 tier 或換方法。若每次錯誤都不同且驗收條件持續增加，視為正常收斂，不計作無效重試。
- 開工前已有 higher-complexity signals，可直接使用 `pro_worker/Terra high`；Luna 失敗後若已符合 capability／context 訊號，使用 `recovery_worker/Terra high`。Terra 已確認自身能力不足時，升級 `escalation_worker/Sol medium`；Sol medium 仍顯示能力不足或高代價風險支持更深推理時，才由 controller 顯式改用 Sol high。
- 風險與實作難度分開判斷：安全／資料遺失／不可逆風險會提高規劃與驗收強度，但不自動證明實作一定需要 Sol；先看 root cause 與 complexity signals。
- 所有升級 prompt 都必須附原始需求、approved plan、相關 diff 與**對應門檻的證據**：失敗入口附完整失敗輸出與已嘗試 hypotheses；能力／脈絡入口附誤判或遺漏證據；高風險入口附風險判定依據。升級實作者必須先建立 root cause 再編輯。若 approved plan 不完整或需要擴大 scope，先停止並交回 controller 走 planner 路徑。若任務需要對外或不可逆動作，worker／pro_worker／recovery_worker／escalation_worker 直接停止並交回 controller；任何 subagent 都不得代替 controller 執行。
- `reviewer` 發現一般文件或一般驗收缺口 → 改派 `verifier/Terra high`；發現安全、不可逆、重大架構問題或正式高風險驗收需求 → 改派 `sol_verifier/Sol high`，不讓 reviewer 自行修正。
- 任一指定 model 回報 unsupported 或 unavailable → 停止宣稱該 model mapping 已驗證，改用已核准的 fallback 並標記「模型未驗證」；不得靜默繼承另一個 model。
- 升級角色（`recovery_worker`、`escalation_planner`、`escalation_worker`、`verifier`、`sol_verifier`）只處理能力需求，不取代使用者授權；對外或不可逆動作未在本 session 明確授權時，停止並交回 controller。
- `Sol high` 卡住 → 先換 fresh-context Sol、取得獨立第二意見或重定義問題與驗收條件；只有仍有明確邊際價值時，controller 才可顯式使用 xhigh／max。Ultra 只在當前 runtime 明確支援且工作可安全拆成獨立大型工作流時考慮。
- 高能力角色解出可重複且可機械驗證的 pattern 後，可把 pattern 寫入 prompt，降級交給較輕角色套用。
- 同一件事最多兩輪**無進展**重試；兩輪仍失敗就換方法、升級或依 `<REPO>/rules/20-judgment.md` §3「何時該停下來問使用者」取得方向。

## 6. 驗證語意（鐵律三）

- 主觀判斷、一般文件與一般驗收不得由製作者自我背書；交給 fresh-context `verifier/Terra high` read-back，逐條判 PASS/FAIL。安全、不可逆、重大架構與正式高風險產出改用 fresh-context `sol_verifier/Sol high`。
- 一般程式碼 review 可由 fresh-context `reviewer` 執行；它發現一般文件問題升級 `verifier`，發現高風險或正式驗收問題升級 `sol_verifier`。
- 測試、build、lint、實跑與 schema 驗證可由製作者執行，但回報必須附指令與輸出證據。
- 高風險程式碼除機械驗證外，再做一次 fresh-context `reviewer` 與 `sol_verifier` review。
- **修使用者實際回報的 bug 一律加 fresh-context `reviewer` review**，不必先判定風險等級或改動大小——「高風險」要當場判斷，「使用者回報的 bug」不用。該次驗收一定要問「同一個錯誤還有沒有第二個現場」——那是製作者最不適合回答的問題（他的心智模型正是漏掉那一處的原因），也是機械驗證最驗不到的：測試只覆蓋你改的那條路，改對的那條會全綠。答案是取樣不是清單：範圍內的修並重驗 delta，範圍外的一律開成 repo issue 並回報附連結；連續兩輪 FAIL 都落在範圍外就停下來回報（canonical 見 `<REPO>/rules/10-dispatch.md` §5）。
- `verifier` 與 `sol_verifier` 的任務是假設產物有問題並找碴；只驗收與指出缺口，不修正產物。找碴範圍與「行為承載產物」分類的 canonical 在 `<REPO>/rules/20-judgment.md` §2「停止端」；不因檔案是 Markdown 就把會改變 agent／人員行動的語意降成散文。
- 兩種 verifier 回報第一行都標 `CONVERGED`／`PROSE-ONLY`／`OPEN`。controller 收到前兩者就修完、read-back 引用後停止；收到 `OPEN` 才依 `<REPO>/rules/20-judgment.md` §2 對修正 delta 再做 fresh-context 驗收。
