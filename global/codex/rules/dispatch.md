# Codex 模型調度守則

> 讀者：Codex 主對話（controller）。每次要派工、選模型或驗收之前照著做。
> 本檔是 `<REPO>/global/shared/skills/dispatch/SKILL.md` 的 Codex 版；Claude Code 專用的 Agent 工具參數不要套到這裡。
> 下文的 `<REPO>` 同 `~/.codex/AGENTS.md` 的 Bootstrap 段定義（依機器而異；該段有對照表，`readlink ~/.codex/AGENTS.md` 只在 symlink 安裝的機器上有效）。本檔位在 `<REPO>/global/codex/rules/`，寫成裸 `rules/…` 從這裡解析不到。

controller 在主對話自己做實作與文件；subagent 只剩三類：fresh-context 驗收（`verifier`／`sol_verifier`）、fresh review（`reviewer`）、旁支查詢（`scanner`／`explorer`）。實作型角色（worker、pro_worker、recovery_worker、escalation_worker）與規劃型角色（planner、escalation_planner）於 v4（2026-10-29）日落，理由與量測見 `<REPO>/docs/reviews/v4-2026-10.md`。平行開發與多 issue 走 `<REPO>/global/shared/skills/worktree-session/SKILL.md`：一 issue 一頂層 session，各在自己的 worktree，不派實作型 subagent。

## 0. Codex 角色與 runtime adapter（以當前 session 實際工具為準）

| 角色 | Agent／effort／權限 | 用途定位 |
|------|--------------------|----------|
| `scanner` | Luna／medium／read-only | 答案在檔案裡的查詢：精確清單、分類、格式檢查、資料抽取 |
| `explorer` | Terra／medium／read-only | 要歸納推理的查詢：repo 執行路徑、跨檔追查、長文件與外部文件研究、影響範圍 |
| `reviewer` | Terra／high／read-only | 程式碼 diff 的 fresh-context 對抗式 review |
| `verifier` | Terra／high／workspace-write（只寫 repo 外探針目錄） | 一般 read-back、文件與驗收審查 |
| `sol_verifier` | Sol／high／workspace-write（只寫 repo 外探針目錄） | 安全、不可逆、重大架構與正式高風險驗收 |

五個角色都不寫 repo：`scanner`、`explorer`、`reviewer` 是 read-only；`verifier`、`sol_verifier` 的 sandbox 是 workspace-write，合約只許寫 repo 外探針目錄（探針落檔用），repo 內一律不寫，controller 事後 read-back `git status`／`git stash list`。一般文件的驗收使用 `verifier/Terra high`；安全、不可逆、重大架構與正式高風險驗收使用 `sol_verifier/Sol high`（刻意分版，Claude 端用同一個 verifier 顯式帶 opus）。所有 verifier 只找碴與判定，不製作也不修正產物。**Codex 內建的 generic `default` child 不因 custom worker 刪除而消失**：本檔不授權用它當實作者，實作一律留在主對話。

**別名與主對話邊界**：Luna＝`gpt-5.6-luna`、Terra＝`gpt-5.6-terra`、Sol＝`gpt-5.6-sol`。主對話的靜態預設不在本檔寫死，設定預設讀 `~/.codex/config.toml`，當前 model／effort 以 runtime metadata 或 CLI header 為準。global instruction 不能在已啟動的主對話中自動切換主 agent，只能指導 delegated agent、direct CLI，或下一個 session 的選擇；不要把可能過期的 `~/.codex/models_cache.json` 當 runtime 證據。

角色名稱使用底線，因目前 `spawn_agent.task_name` 只接受小寫英數與底線。安裝 `~/.codex/agents/*.toml` 與 runtime 選中角色是兩件事：派工前先看當前 surface 是否明確提供 `agent_type` 與該角色的 model／effort metadata。可選中時，把 surface metadata 當作「工具宣告值」記進 adapter envelope；若回傳或 child metadata 另有實際 runtime model／effort，再一併 read-back。surface 沒有角色選擇入口、role 不符或 runtime 證據與宣告不一致時，不得假裝 custom role 已套用；依下方 adapter 改用 `default`，或標記「模型／effort 未驗證」後停止該 routing。

### Runtime adapter（所有 logical role 共用）

上表是唯一的 logical-role、model／effort、權限 mapping；`delegation-templates.md` 的模板提供完整 contract，不在此複製第二張角色表。每次派工先分開記錄兩個身份：`logical role` 是要完成的角色（例如 `reviewer`），`actual agent_type` 是當前 runtime 實際接受的 agent type。

1. **Named-first**：先檢查當前 surface 是否明確提供 `agent_type=<logical role>`，且 metadata 的 model／effort／權限符合上表；符合才以 named role 派送。surface metadata 先標「工具宣告值」，只有工具回傳或 child metadata read-back 的實際值才可升級為「runtime 已驗證」。若角色看似已註冊但回覆 unavailable，可在不修改 local config 的前提下 read-only 核對 `[agents.<name>]`／`config_file` 並於 fresh session 重試一次。
2. **Default fallback**：surface 沒有 named selector、named call 回覆 `agent type is currently not available`、或 named metadata 不符合時，改以實際 `agent_type=default` 啟動；明確傳入選定的 model／effort，並在 prompt 寫入 permission contract 與 route evidence。override model／effort 時 `fork_turns` 必須用 `none` 或正整數，驗收與 fresh review 一律 `none`（fresh context 是它們的價值所在）；full-history fork 不接受 override。prompt 必須先放 `delegation-templates.md` 的 adapter envelope，再接完整 logical-role contract。generic `default` 不得稱為 custom role；`default` unavailable 或無法接受 mapping 時停止並標記「runtime 未驗證」。
3. **Evidence／permission gate**：envelope 必須分開記錄 logical role、actual `agent_type`、fork context、requested model／effort、logical permission contract、runtime permission evidence 與其他 runtime evidence。surface 固定值是「工具宣告值」；child metadata 是「runtime 已驗證」；兩者都取不到就是「runtime 未驗證」。TOML、檔案存在、角色名稱或 prompt 內容都不能冒充 runtime 證據。generic `default` 沒有 sandbox override 時繼承父 session：verifier 類（`verifier`／`sol_verifier`）只需父 session runtime 至少 workspace-write，其寫入範圍僅 repo 外探針目錄，由合約約束，父 runtime 為 read-only 時改走 direct CLI（`--sandbox workspace-write`）或停止；`reviewer`／`explorer`／`scanner` 等 read-only 角色只有父 session runtime 已是 read-only 時可派，否則強制改走下方 read-only direct CLI branch 或停止，不得靠 prompt 禁寫與事後 read-back 補救。指定 model／effort 無法明確傳入時，停止並回 controller。
4. **Role transitions**：換角色（如 `scanner` 超界交回後改派 `explorer`、`reviewer` 發現正式驗收需求改派 `verifier`）時，權限與授權不因 adapter 改變；每次轉派都重新套用 named-first → fallback 與同一個 logical-role contract。generic reviewer／verifier／`sol_verifier` 必須標記 generic 身份；若 direct CLI 或 generic child 已有指定 model／effort、sandbox 證據、完整同角色 contract 與可讀 runtime 證據，可作為有效獨立驗收（包含 Sol/high 高風險驗收），但不得冒稱 custom role。缺任一 model／effort／permission 證據就只能標「runtime 未驗證」，不能正式結案。

### Direct CLI review branch

`reviewer`、`verifier`、`sol_verifier`、`explorer`、`scanner` 若沒有可用 child surface，controller 可直接啟動 fresh process。`--sandbox` 依角色：唯讀角色用 `read-only`；`verifier`／`sol_verifier` 用 `workspace-write`（只為了寫 repo 外探針目錄，repo 內不寫由合約約束，controller 事後 read-back `git status`／`git stash list`）：

```bash
codex exec --ephemeral --strict-config --sandbox <read-only｜workspace-write> \
  -m <上表對應 model> -c 'model_reasoning_effort="<上表對應 effort>"' \
  "<adapter envelope + 對應模板完整 contract + 原始需求與驗收條件>"
```

若是程式碼 diff，可在同一組明確 model／effort 參數後使用 `review --uncommitted`。這個 `--ephemeral` process 本身就是單體 fresh reviewer，直接完成驗收，不在其中 nested spawn；CLI header 與命令列可驗證 model／effort／permission，但不能證明 custom role。named unavailable 時，這條 direct CLI 是有效的獨立 fallback，包含指定 Sol/high 的高風險驗收；回報仍標 `direct CLI fallback`／generic 身份。若 header、sandbox 或完整 logical-role contract 缺任一項，只能補強證據並標「runtime 未驗證」，不能正式結案。

## 1. 派工判斷

controller 自己做實作、修 bug、重構、文件與規劃；subagent 只派三類：驗收（§6）、fresh review（§6）、旁支查詢。「任務可獨立」「只需結論」「按工作類型分」都不是派工理由。

### Controller 工作迴圈

1. **開工前的 plan**（非平凡任務首次改檔前寫下，不派 planner）：目標與動機、affected files／寫入範圍（絕對路徑）、invariants、implementation phases、validation commands 與可判定的完成條件（`<REPO>/global/shared/rules/judgment.md` 第 12 條）；高風險補 failure modes 與 rollback；未決邊界先向使用者釐清，不邊做邊補。approved plan 由 controller 自己核定，不新增使用者批准程序。修正要對多個呼叫點、非同步交錯或多處讀寫同一狀態都成立時，先寫不變量，再依 §5 第 1 條取獨立方案比對。
2. **開工在自己的 worktree**（`<REPO>/global/shared/skills/worktree-session/SKILL.md` §1），逐 phase 實作並跑 validation commands，留指令輸出；新增或修改的測試斷言與守門檢查各附一次實跑會變紅的突變紅／綠（`<REPO>/global/shared/rules/judgment.md` 第 6 條）；失敗先查環境與根因（`<REPO>/docs/debug-environment-first.md`），每輪記一列逐輪嘗試表，無進展依 §5 換路。
3. **旁支查詢**只在原始內容後續不需逐行引用、經有界讀取（`rg`、`sed -n`）仍要帶入大量原文時派：答案在檔案裡（找哪些檔有 X、列清單、抓數字）派 `scanner`；要讀多份長文歸納、跨來源比對、結論帶推理派 `explorer`；只拿結論與檔案:行號，原文不帶回主對話。`scanner` 超界交回時由 controller 改派 `explorer`。短搜尋留在主對話。
4. **依 §6 選驗收與 fresh review**；修正一律 controller 自做，依 `<REPO>/global/shared/rules/judgment.md` 第 7 條「驗收的停止端」與 `<REPO>/global/shared/skills/dispatch/SKILL.md` §2「修正與驗收輪次」分流。自做不改變驗收：自己改的產出照 §6 派，不因自做降級。

**CI／release 設定**（`.github/workflows`、`.github/actions` 等會被執行的設定）不靜默自改：先把 diff 給使用者、取得本 session 當次授權，再套上並照 §6 派驗收。

**多個互相獨立的 issue**（各自可單獨交付、不必一起整合）一個 issue 一個頂層 session，依 `<REPO>/global/shared/skills/worktree-session/SKILL.md` §2，本 session 只做盤點、不兼任其中任何一個。**主對話 context 很大**（runtime 有可靠數字時 ≥300K；沒有時以內容量與漏掉既有決定、重讀無進展等退化證據判斷，「曾 compact」只觸發重新評估）且還有未做的 phase：寫 `<REPO>/global/shared/skills/handoff/SKILL.md` §4「session 交接卡」，剩下的 phase 開新 session 接手，不派 subagent。

主對話負責與使用者溝通、整合證據、做決策，並 read-back 實際狀態；subagent 的摘要不能取代這些責任。read-back 用有界輸出（`git diff --stat`、`sed -n`、`rg -c`、`wc`）只讀判定所需的行，全文與大 diff 留給 verifier 或落檔。

## 2. 工作目錄與執行安全

- 同一 working tree 同一時間只能有一個寫入者（single-writer）；寫入者就是主對話（或各自 worktree 裡的頂層 session）。
- worktree 的位置、忽略方式與清理條件見 `<REPO>/global/shared/skills/worktree-session/references/worktree.md`。
- blocking 任務不得只放在可能因休眠或背景 session 中斷而消失的背景執行；controller 必須保有可持續等待、重接或重跑的前景路徑。
- Subagent 回報不等於實際狀態。controller 必須 read-back `git status`、`git diff`、commit 狀態與驗證輸出。
- **唯讀角色也受影響**：`verifier`／`explorer`／`reviewer` 等不寫 repo 的角色與寫入者共用 working tree 時，它的**唯讀結論**（檔案內容、路徑與指令是否存在）仍可信，但**任何跑測試／build 取得的數字**都被污染。驗收期間 controller 不動工作區；等不了就在 prompt 的工作目錄欄指定獨立 worktree 絕對路徑。

## 3. 派工三件套

**派工揭露（controller → 使用者，每次派 subagent 都要）**：在呼叫工具前，commentary 只報**指定的 logical role 名稱與任務摘要**，例如「派 `scanner` 掃描設定」。正常 named path 不例行回報 actual `agent_type`、model、effort、permission 或制度依據。named unavailable 而改走 `default` 時標成「`<logical role>`（generic fallback）」；direct CLI path 標成「`<logical role>`（direct CLI fallback）」；建立失敗則回報「`<logical role>` 未建立」與 runtime 原因。使用者詢問、runtime 不一致、unsupported／unavailable 或正式稽核時，才展開 adapter envelope 內的 actual `agent_type`、model／effort、permission 與證據層級。不得把 TOML、角色名稱或 generic child 冒充 custom runtime 身份。

Claude 端 `<REPO>/global/shared/skills/dispatch/SKILL.md` §3「派工合約與回報」使用同一套 user-facing 揭露：正常只報指定 role 名稱與任務摘要，fallback 才標差異。Codex 額外取得的 runtime metadata 留在 adapter envelope，不轉成每次 commentary；這是內部證據能力差異，不是使用者介面差異。

每個 subagent prompt 必含三段，缺一段就是不合格派工（模板見 `delegation-templates.md`）：

1. **目標與動機**：要達成什麼、為什麼；subagent 看不到完整主對話，脈絡要自帶。
2. **驗收條件**：可機械判定的完成定義；判準是另一個 agent 能只憑這句話判定過或不過。
3. **回報格式**：只列 brief 指定的 controller 下一步決策欄位，以及這些欄位所需的證據。

### 素材與批次查證

controller 應在 brief 附上仍有效的 diff、檔案行號／段落與測試結構；subagent 可用素材定位，不必重讀整檔。獨立 read／search 優先批次執行。verifier 可用素材定位，但機械事實要自行跑一次，不能把製作者輸出當證據。長任務保存 session id 與 output 路徑，只用當前 surface 支援的短段 wait／poll 維持進度，不假設 Claude cache TTL。

## 4. 回報與證據合約

- Subagent 只回結論與證據（檔案:行號、指令輸出關鍵行、URL），不得傾倒原始內容。
- 回報只列 brief 指定的 controller 下一步決策欄位；逐條驗收判定、根因證據與必要定位素材不得因篇幅省略。
- 大 diff、全文與完整清單由 controller 落檔；readonly role 不寫檔，verifier 僅依既有合約寫 repo 外 probe。readonly role 回「結論＋檔案:行號範圍」而非原文段落，controller 依範圍自讀。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**。
- controller 整合回報後仍須 read-back 實際檔案與狀態；不把 agent 自述當作完成證據。

## 5. 卡住時

同一件事最多**兩輪無進展**重試（指同一個問題的修法重試，不含驗收輪次）。無進展的判定：失敗原因不明且同一子任務兩次沒推進；有機械指標（失敗測試數、錯誤數、benchmark 值）時該輪未優於歷來最佳值就算一次無進展，錯誤訊息換了也一樣；每次錯誤都不同且驗收條件持續增加屬正常收斂，不計。先分類：**execution mistake**（syntax、漏改、指令拼錯）修法明確時直接補正；**insufficient evidence／environment understanding**（缺 repo 事實、log、重現步驗或環境量測錯誤）先補查證或依 `<REPO>/docs/debug-environment-first.md` 校正量法，換更強模型不會補出不存在的證據。

**換路訊號**（任一成立就換路，不等兩輪）：修法越疊越多層 workaround；同一錯誤訊息在兩種不同修法後原樣出現；新 FAIL 與前一輪同根因只是換層或換形；diff 越改越大但驗收達成數不增；想先關掉檢查「之後再回來」。每輪「照 plan 做了嗎」都 PASS 卻持續冒同根因的新症狀＝**plan 缺陷**，重新定義問題，不換更強的模型。

換路只有三條，一律附完整失敗軌跡（逐輪嘗試表：改了什麼｜跑了什麼指令｜輸出關鍵行或指標值｜改動仍在工作樹或已回退｜為什麼判定失敗）：

1. **重新定義問題**：先寫出不變量（修完後要由結構保證成立的條件、不靠事後檢查），附全部失敗紀錄與其共同形狀，派 `explorer`（依 §0，read-only，brief 寫明只出方案）與一個 direct CLI 的 Sol/medium fresh process 各自獨立出方案並互相比對，只靠事後檢查補洞的方案不採；分歧交使用者。
2. **第二意見**：direct CLI 起一個 fresh process（Terra high；高風險或 Terra 已顯示能力不足時 Sol medium）帶失敗軌跡從 root cause 重看，不沿用自己的假設；主對話 model 本身要換時，由使用者在 UI 或 CLI 為下一個 session 選擇，global instruction 不能在已啟動的主對話中切換。
3. **問人**：依 `<REPO>/global/shared/skills/dispatch/SKILL.md` §5「何時問使用者」。兩輪無進展代表方向錯了，不要換個措辭再試第三次。

任一指定 model 回報 unsupported 或 unavailable → 停止宣稱該 model mapping 已驗證，改用已核准的 fallback 並標記「模型未驗證」；不得靜默繼承另一個 model。`Sol high` 卡住 → 先換 fresh-context Sol、取得獨立第二意見或重定義問題與驗收條件；只有仍有明確邊際價值時，controller 才可顯式使用 xhigh／max。Ultra 不是一般 coding route。

## 6. 驗證語意（鐵律三）

- **先定深度再派**：低風險小改＝同時成立：文件只改數句（事實更正、連結、措辭）或程式碼只改單點素材／設定／字串／幾行邏輯；不含外部呼叫、權限請求或不可逆副作用（`<REPO>/global/shared/rules/judgment.md` 第 2 條）；不屬 judgment 第 1 條的高風險產出（含並行、資料一致性、安全相關的邏輯，即使只有幾行）；不是使用者回報的 bug；製作者已附機械檢查輸出。走輕量路徑：文件派 `verifier` 做 read-back 級（逐句對照來源、跑 repo 的文件檢查腳本、查引用存在，brief 寫明不跑 repo 全套驗證）；程式碼由製作者機械驗證＋一次 fresh-context `reviewer`，不派 `verifier`。各級通用：製作者已附全套測試／build／lint 輸出時，verifier 只重跑判定所需的受影響 spec、檢查腳本與自己的探針，全套交 CI；多引擎、多模式、多環境的探測只在驗收條件明列時做；brief 附全套輸出的路徑並列出受影響的 spec，verifier 據此決定重跑範圍。判準與 Claude 端同步：`<REPO>/global/shared/skills/dispatch/SKILL.md` §1「驗證不自驗」。
- 主觀判斷、一般文件與一般驗收依原有首次驗收分工交給獨立 fresh-context `verifier/Terra high` read-back，逐條判 PASS/FAIL/UNSURE；安全、不可逆、重大架構與正式高風險產出改用獨立 fresh-context `sol_verifier/Sol high`。named role unavailable 時依 §0 direct CLI review branch，指定 model／effort、強制對應 sandbox 並貼完整同角色 contract；證據完整即可作有效獨立驗收，身份仍標 generic／direct CLI，不冒稱 custom。
- 一般程式碼 review 由 fresh-context `reviewer` 執行；它發現一般文件問題或正式驗收需求時停止回報，由 controller 改派 `verifier`，發現高風險或正式高風險驗收需求時改派 `sol_verifier`；reviewer 不自行修正。
- 測試、build、lint、實跑與 schema 驗證由製作者（controller）執行，回報附指令與輸出證據；讀碼不取代執行證據。
- 含外部呼叫、權限請求或不可逆副作用的程式碼，不論風險等級，機械驗證外一律加 fresh-context `reviewer` review，套 `<REPO>/global/shared/rubrics/code-change.md` §7「失敗路徑與不可逆副作用」；製作者的測試與突變證據只證 happy path，不得據此結案。「不可逆副作用」與本檔所有分流句、各 agent 合約及 `delegation-templates.md` 裡「安全、不可逆」的範圍，一律依 `<REPO>/global/shared/rules/judgment.md` 第 2 條「不可逆副作用的定義」的 canonical 定義。reviewer 不因 diff 含一般側操作就升級 `sol_verifier`；controller 也不因 reviewer 依 §7 回報一般側操作的 FAIL 而改派 `sol_verifier`；修正後結案依 `<REPO>/global/shared/skills/dispatch/SKILL.md` §2「修正與驗收輪次」（高風險 FAIL 由 controller 自修後再派一次 fresh delta）。
- 高風險程式碼除機械驗證外，再做一次 fresh-context `reviewer` 與 `sol_verifier` review；若 named role unavailable，兩者依同一 direct CLI fallback 取得獨立證據，不能因 TOML 或角色名稱存在就視為已選中。
- **修使用者實際回報的 bug 一律加 fresh-context `reviewer` review**，不必先判定風險等級或改動大小——「高風險」要當場判斷，「使用者回報的 bug」不用。該次驗收一定要問「同一個錯誤還有沒有第二個現場」——那是製作者最不適合回答的問題（他的心智模型正是漏掉那一處的原因），也是機械驗證最驗不到的：測試只覆蓋你改的那條路，改對的那條會全綠。答案是取樣不是本次必修清單；先判斷共同成因，再決定修哪一層。範圍內依 `<REPO>/global/shared/rules/judgment.md` 第 7 條「驗收的停止端」分流；範圍外不擴修，由 controller 登記該 repo issue 並附連結，未取得對外授權則保留待登記項目。連續兩輪發現都在範圍外就停止回報，不把下一批工作塞進本次。
- `verifier` 與 `sol_verifier` 的任務是假設產物有問題並找碴；只驗收與指出缺口，不修正產物。找碴範圍與「行為承載產物」分類的 canonical 在 `<REPO>/global/shared/rules/judgment.md` 第 7 條「驗收的停止端」；不因檔案是 Markdown 就把會改變 agent／人員行動的語意降成散文。
- 驗收判定前必讀 `<REPO>/global/shared/rules/judgment.md` 第 6 條「修正者的證據」及第 7 條「驗收的停止端」：四種狀態與補證只在該處定義，修正風險分流、delta brief 必帶項與三輪回報點在 `<REPO>/global/shared/skills/dispatch/SKILL.md` §2「修正與驗收輪次」；不可把 OPEN 當成必派或把 UNSURE 當成通過。
