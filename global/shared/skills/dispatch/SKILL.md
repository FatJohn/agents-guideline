---
name: dispatch
description: 驗收與派工的機制：驗證不自驗（先定深度再派 verifier 或 fresh code-review）、驗收後的修正與輪次、派 verifier 與旁支查詢的 brief 與回報合約、卡住時換路、何時問使用者、主對話 context 管理。要派 verifier、fresh review 或查詢型 subagent、問「接下來怎麼驗收」、驗收後選修正路徑、同一個問題修了兩次還沒好要換路、或使用者要 compact 時使用。Use when dispatching a verifier or research subagent, choosing a fix or verification path, escalating after repeated failure, or writing a compact handoff.
---

# dispatch — 驗收、派工與修正

controller 在主對話自己做實作與文件；subagent 只剩三類：fresh-context 驗收（`verifier`）、fresh `code-review`、旁支查詢。**開工前的 plan**：非平凡任務第一次改檔前，用 `~/.claude/skills/handoff/SKILL.md` §1『brief 卡』同一張卡寫下目標、Scope、Invariants、Phases、Validation 與可判定的驗收條件（`~/.claude/rules/judgment.md` 12），之後的 verifier brief 逐字沿用；高風險補 failure modes 與 rollback。本 skill 寫 Claude Code 端的角色與參數；Codex 見 `<REPO>/global/codex/rules/dispatch.md`，§1–§2 的判準兩平台共用。skill 路徑以 Claude 安裝位置 `~/.claude/skills/<name>` 書寫，Codex 對應 `~/.agents/skills/<name>`。按節讀：驗收 §1–§2、派工與回報 §3、卡住 §4、問使用者 §5、context 變大 §6。brief、回報與判定的固定格式在 `~/.claude/skills/handoff/SKILL.md`。平行開發與多 issue 走 `~/.claude/skills/worktree-session/SKILL.md`，不派實作型 subagent。

## 1. 驗證不自驗

製作者不驗自己的產出；「是 controller 自己改的」「只是順手改一下」都不構成降級或跳過驗收的理由。**先定深度再派**：

- **低風險小改**＝同時成立：文件只改數句（事實更正、連結、措辭）或程式碼只改單點素材／設定／字串／幾行邏輯；不含外部呼叫、權限請求或不可逆副作用（`~/.claude/rules/judgment.md` 2）；不屬 `~/.claude/rules/judgment.md` 1 的高風險產出（含並行、資料一致性、安全相關的邏輯，即使只有幾行）；不是使用者回報的 bug；製作者已附機械檢查輸出。走輕量路徑：**文件**派 `verifier` 做 read-back 級（逐句對照來源、跑 repo 的文件檢查腳本、查引用存在），brief 寫明不跑 repo 全套驗證；**程式碼**由製作者機械驗證＋派一個 fresh subagent 執行 `code-review` skill，不派 `verifier`。
- 其餘照下列首次驗收分工。
- **verifier 的重跑深度**（各級通用）：製作者已附全套測試／build／lint 輸出時，verifier 只重跑判定所需的受影響 spec、檢查腳本與自己的探針，全套交 CI；多引擎、多模式、多環境的探測只在驗收條件明列時做。brief 附全套輸出的路徑並列出受影響的 spec，verifier 據此決定重跑範圍。

首次驗收分工：

- **文件／主觀品質**：派 fresh-context `verifier`，給產出路徑及驗收條件，逐條 PASS／FAIL／UNSURE；不參與製作。
- **程式碼機械驗證**：製作者可跑測試、build、lint、實跑、schema，附輸出；讀碼不取代執行證據。新增或修改的測試斷言與守門檢查（lint、regex、檢查器、CI gate）各附一次實跑會變紅的突變：暫時改壞被守的行為、實跑看到失敗，還原後重跑轉綠，回報列「斷言→突變→紅／綠關鍵輸出」；還原只能反向編輯或從 scratchpad 快照複製回去，不用 `git checkout`／`git restore`／`git stash`。
- **含外部呼叫、權限請求或不可逆副作用的程式碼**：不論風險等級，機械驗證外一律派 fresh-context `verifier` 套 `~/.claude/rubrics/code-change.md` §7『失敗路徑與不可逆副作用』；製作者的測試與突變證據只證 happy path，不得據此結案。「不可逆副作用」的範圍依 `~/.claude/rules/judgment.md` 2『不可逆副作用的定義』；§7 FAIL 修正後的結案方式依本 skill §2。
- **高風險程式碼或使用者回報的 bug**：機械驗證外加 fresh review，必問「同一錯誤還有沒有第二個現場」。fresh review 派一個 fresh-context subagent 執行 `code-review` skill（從 diff 推 bug，不需驗收條件）；它不取代上一條的 §7 verifier 審查，有逐條驗收條件時仍派 `verifier`。
- **高風險判斷**（對外文件、不可逆、架構決策）：加獨立第二意見，用 `codex:codex-rescue` 或第二個獨立 agent，分歧交使用者。

Claude verifier 不因高風險自動升檔，一律顯式 `model: opus`：frontmatter 已寫 `model` 時不指定也不會繼承主對話，顯式寫是防 fallback 到沒有 frontmatter model 的 agent（如 `general-purpose`）時跟著主對話跑；真的 fallback 時另帶與 verifier frontmatter 相同的 `effort`，否則 effort 落到 session 設定。改用 `model: fable` 前，說明訊號與證據並取得當次同意（訊號清單見 `<REPO>/docs/reviews/verification-policy-history.md`「fable 升檔訊號」）；使用者當次直接指定 fable 不必再問。Codex 刻意維持 `sol_verifier/Sol high`，見 `<REPO>/global/codex/rules/dispatch.md` §6『驗證語意』。

**第二個現場**是取樣，不是本次必修清單；verifier 交回的 N 個實例清單同樣是取樣。逐個修完之前先問「是什麼產生它們」，再決定修哪一層。範圍內依 §2 修正分流；範圍外不擴修，登記該 repo issue 並附連結（對外授權仍依鐵律二，未授權先保留待登記項目）。連續兩輪發現都在範圍外就停手回報，不把下一批工作塞進本次。

**唯讀角色也受影響**：verifier 與寫入者共用 working tree 時，它的唯讀結論（檔案內容、路徑與指令是否存在）仍可信，但任何跑測試／build 取得的數字都被污染。驗收期間 controller 不動工作區；等不了就給 verifier 自己的 worktree（`isolation: worktree`）。

## 2. 修正與驗收輪次

verifier 第一行回報狀態與下一步（語意見 `~/.claude/rules/judgment.md` 7『驗收的停止端』），controller 照下一步走：`CONVERGED` 停止驗收；`PROSE-ONLY` 修完 read-back 後停止，不派 delta；`OPEN` 修正後依下方風險分流，不自動要求重派；`INCONCLUSIVE` 先補缺證，保留已知 FAIL，不自動重派或宣稱完成，也不以換 model 代替缺證。

**修正一律 controller 自做**（`~/.claude/rules/judgment.md` 6『修正者的證據』），沒有別的修正者。**驗收後的風險分流**：verifier 第一行已依判準寫明走哪一側，controller 照走；低風險且有確定性檢查能證明 finding 已修、無相關迴歸時，controller 自行檢查並以「finding→修正→證據」結案；安全、權限模型與存取控制的設計、不可逆、重大架構或缺乏可靠機械證據時，修完再派一次 fresh-context `verifier` 做 delta 驗收。

**驗收輪次按產物切開**：文件待實作與證據穩定後集中更新，不逐輪加未驗宣稱。可執行宣稱（測試、斷言）在實作當下寫並驗，散文最後一次寫完才驗；同一交付批次中證據已穩定、無個別交付依賴的散文可合併成一次驗收，不得為合批延後已可交付的 issue／PR 或阻塞後續工作，行為承載文件不因此降成散文。

**delta 派工**必帶：原 finding、修正 diff、受影響的原始驗收條件與既有證據（含修正者對新寫句子的逐句對照、對新斷言的突變紅／綠輸出）。evidence set 範圍、歸因與收斂判定的 canonical 在 verifier 合約（`~/.claude/agents/verifier.md`；Codex：`<REPO>/global/codex/agents/verifier.toml`）。首輪 brief 指定 repo 外的探針落檔路徑，delta brief 附該路徑；除「改既有檢查」的放寬探測外，delta brief 不另指定新探測形狀或開放式找漏洞。欄位見 handoff §1『brief 卡』。

**三輪回報點**：同一產出第 3 次 fresh 驗收後仍需重派（`OPEN`／`INCONCLUSIVE`），回報輪數、FAIL／UNSURE 性質、修正與剩餘項目交使用者決定，不自動開第 4 次；delta 計次，換 model 不重設。例外：本 session 已明確要求驗到收斂；或回報後使用者明確同意續驗，此時從零重計下一段三輪。

## 3. 派工合約與回報

**三類 subagent 與參數**。Agent 工具的 `model` 參數只接受 harness 注入的 alias（`haiku`／`sonnet`／`opus`／`fable`），完整 model ID 只能寫在 agent frontmatter；對照見 `<REPO>/docs/harness-facts.md`「Agent 工具 `model` 參數的 alias 對照」。

- `verifier`：顯式 `model: opus`、不帶 `effort`（帶了會蓋過 frontmatter）；派前讀 `~/.claude/agents/verifier.md`，只提供該檔要求的素材，不重述其職責。
- fresh `code-review`：派 `general-purpose` 執行內建 `code-review` skill，`model: opus`、`effort: medium`（與路由卡一致）。
- 旁支查詢：答案在檔案裡的用 `Explore`（`model: haiku`）；要讀多份長文歸納、跨來源比對、結論帶推理的用 `general-purpose`（`model: sonnet`）；要落檔原文也派 `general-purpose`（Explore／Plan 的角色指示禁止寫檔，見 `<REPO>/docs/harness-facts.md`「常用 subagent 類型」）。第二意見用 `codex:codex-rescue`（外部模型，不占 Claude 配額）。簡化剛改過的程式碼用內建 `simplify` skill。

**CI／release 設定**（`.github/workflows`、`.github/actions` 等會被執行的設定）不派也不靜默自改：先把 diff 給使用者、取得當次授權，再套上並照 §1 派 verifier。裝了 `block-ci-edit` hook 的環境，主對話以 Edit／Write 改這兩個目錄會被擋（缺 jq 時 fail-open），訊息要求先取授權；授權後以 `git apply` 套上給使用者看過的 patch，未授權不得改用 Bash 繞過。

**brief 必含三段**（欄位模板見 `~/.claude/skills/handoff/SKILL.md` §1『brief 卡』），缺一段就是不合格的派工：目標與動機（subagent 看不到主對話，脈絡要自帶）；驗收條件（可機械判定，自我檢查見 `~/.claude/rules/judgment.md` 12）；回報格式。三個非顯然的必要條件：**把已讀過的素材附進 prompt並要求指令批次化**（subagent 是冷啟動，每個它自己去讀的檔都是一輪完整推理）；**路徑一律絕對路徑**；派 `general-purpose` 時 **prompt 開頭明寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」**（它會讀到全域 `CLAUDE.md` 與 `~/.claude/rules/`，不加這句會把自己當 controller 逐層轉包；`Explore`／`verifier` 沒有 Agent 工具，可省）。要求 subagent 補齊某個格式欄位時同時規定「查無來源就留空」，否則原檔沒有的內容會被當場發明。

**派工揭露（controller → 使用者）**：派工當下只講 agent 名稱與任務摘要；實際派送不是指定的 named role 就在名稱後標 `fallback` 並簡述差異，建立失敗回報「`<agent>` 未建立」與 runtime 原因。model／effort 平常不報，被問到、runtime 不一致或稽核時才展開（`<REPO>/docs/harness-facts.md`「被問到 model／effort 時怎麼答」）。Codex 端 `<REPO>/global/codex/rules/dispatch.md` §3 用同一套揭露。

**Subagent 回報**（固定格式見 handoff §2『回報卡』與 §3『verifier 判定卡』）：只回結論與證據（檔案:行號、指令輸出關鍵行），不回原始內容傾倒；長產物落檔，`.md` 檔名不以 `report`／`summary`／`findings`／`analysis` 開頭（harness 會擋 subagent 寫入，見 `<REPO>/docs/harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」）；回報必須分級**已驗證（附證據）／待 CI／未驗證**；brief 的回報格式只列下一步決策要用的欄位。回報全文會留在主對話每輪重讀，要縮時先砍原始內容與重複敘述，不砍決策所需證據。

## 4. 卡住時

同一件事最多**兩輪無進展**重試（指同一個問題的修法重試，不含驗收輪次）。無進展的判定：失敗原因不明且同一子任務兩次沒推進；有機械指標（失敗測試數、錯誤數、benchmark 值）時該輪未優於歷來最佳值就算一次無進展，錯誤訊息換了也一樣。每次錯誤都不同且驗收條件持續增加屬正常收斂，不計。execution mistake（syntax、漏改、指令拼錯）修法明確時直接補正；缺證據先補證據，不猜。

**換路訊號**（任一成立就換路，不等兩輪）：修法越疊越多層 workaround；同一錯誤訊息在兩種不同修法後原樣出現；新 FAIL 與前一輪同根因只是換層或換形；diff 越改越大但驗收達成數不增；想先關掉檢查「之後再回來」。每輪「照 plan 做了嗎」都 PASS 卻持續冒同根因的新症狀＝**plan 缺陷**，重新定義問題，不換更強的模型。

換路只有三條，一律附完整失敗軌跡（逐輪嘗試表：改了什麼｜跑了什麼指令｜輸出關鍵行｜改動仍在或已回退｜為什麼判定失敗）：

1. **重新定義問題**：先寫出不變量（修完後要由結構保證成立的條件、不靠事後檢查），附全部失敗紀錄與其共同形狀，派 `general-purpose`（`model: opus`，brief 寫明唯讀、只出方案不改檔）與 `codex:codex-rescue` 各自獨立出方案並互相比對，只靠事後檢查補洞的方案不採；分歧交使用者。修正要對多個呼叫點、非同步交錯或多處讀寫同一狀態都成立時，動手前就先做這一步。
2. **第二意見**：`codex:codex-rescue`，或派第二個獨立 `general-purpose`（`model: opus`）帶失敗軌跡從 root cause 重看，不沿用自己的假設。
3. **問人**：見 §5。兩輪無進展代表方向錯了，不要換個措辭再試第三次。

## 5. 何時問使用者

符合任一條就停，其餘情況自主前進不要問：

- 動作屬於**發訊息或寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案、改 CI／release 設定**，且本 session 尚未明確授權（鐵律二）。未授權就停止；已在本 session 明確授權時直接執行，不重複詢問。
- 發現必須擴大**功能、契約、權限或外部影響**，而非只是在已授權 scope 內補齊必要實作檔與 dependency。前者停下確認；後者自主完成並在回報說明。
- 是品味／模糊題且第二意見後仍無收斂（例如文案語氣、提案方向）。
- 驗證或動作需要使用者**本人在場**（live 登入、實機操作、手動觸發）且會阻塞後續工作：先問可用時段，其餘已授權且不依賴使用者的工作照常繼續。

停下來問之前，先確認要問的**前提**成立。「兩個檔案不一致」「某機制壞了」這類判定，先看清不一致的**性質**（漂移事故 vs 刻意分版）再開口。拿到授權後動手前再複查一次前提。

## 6. 主對話 context 管理

**症狀**：大量讀檔、掃 repo、抓網頁、批次改檔在主對話進行，context 膨脹；compaction 觸發後早期決定遺失，開始重做已完成的工作或偏離原目標。

**修法**：

- 原始內容後續不需逐行引用、經搜尋與節錄仍要帶入大量原文時，派旁支查詢（§3）只拿結論；能用有界讀取（`rg`、`sed -n a,bp`、`head`）處理的短內容留在主對話。檔案數、網頁、完整 log 本身不是派出理由，看的是帶回來的量與之後引用的方式。
- controller 看不到 statusline，要自己量：用 `<REPO>/docs/harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」的 jq 指令取最後一筆 usage 的三項和。每個實作 phase 開始前、打算一次讀入 ≥5 個未讀檔前各量一次。**≥300K 且還有未做的 phase**：寫 `~/.claude/skills/handoff/SKILL.md` §4『session 交接卡』，剩下的 phase 開新 session 接手，不派 subagent（subagent 不繼承 context，等於重新開始，還少了完整的 CLAUDE.md、hook 與記憶）。
- 何時 compact 由使用者決定，controller 不主動提醒，也不能自己 compact。使用者說要 compact、要離開 >1h（prompt cache 1h 過期，回來整段重寫）或要「新 prompt」時，給一段可直接貼在 `/compact` 後面的**保留指示**，內容是交接卡的精簡版：目標、授權、未完成項目、在途 subagent（名稱、任務）、產物證據位置。有在途 subagent 時先告知，建議等回報後再 compact。
