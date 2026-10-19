---
name: dispatch
description: 派工與驗收的完整機制：何時派 subagent、角色與 model、派工合約與回報合約、升降級、驗證不自驗、修正與驗收輪次、何時問使用者、worktree 與背景任務安全、compact 保留指示。要派任何 subagent、決定升降級、驗收後選修正路徑、或使用者要 compact 時使用。Use when delegating to subagents, escalating, choosing a fix or verification path, or writing a compact handoff.
---

# dispatch — 派工、驗收與升降級

本 skill 寫 Claude Code 端的角色與參數；Codex 的角色與派工見 `<REPO>/global/codex/rules/dispatch.md`，§5–§8 的判準兩平台共用。skill 路徑以 Claude 安裝位置 `~/.claude/skills/<name>` 書寫，Codex 對應 `~/.agents/skills/<name>`。按節讀：派工 §1–§4、失敗或升級 §5、驗收 §6–§7、問使用者 §8、worktree 與背景任務 §9、context 變大 §10。brief、回報與判定的固定格式在 `~/.claude/skills/handoff/SKILL.md`。

## 1. 何時派工

### 雙軸判斷

符合任一條件時優先派 subagent：任務可獨立且主對話只需結論；原始輸出量大且後續不需反覆引用；有互不依賴的子任務可安全平行；需要 fresh-context 驗收。探索與決策需即時互動時留在主對話；實際寫入僅適用「自行小修的例外」。無法隔離就序列派工，不改成多個寫入者。

### 一個 issue 一個 session

互相獨立的 issue（各自可單獨交付、不必一起整合）一個 issue 一個頂層 session，不由同一個 controller 平行扛：本 session 只做盤點，每個 issue 各開一個 session，依 `~/.claude/skills/parallel-dispatch/references/cli.md`「盤點 session 與 issue session」開出（理由與量測見 `<REPO>/docs/issue-session-trial-2026-10.md`）。issue session 的 brief 逐字引用使用者在盤點 session 對該 issue 的授權時，視同該 session 已授權，範圍以引文為限、上限 push feature branch＋開 PR，細節見 cli.md 該段「授權」條。一個 issue 交付後要換主題，開新 session，不在大 context 上接新主題。

同一 issue／功能內準備讓 ≥2 個各需寫入的切片平行（含 spec 尚未切分、要先判斷能不能切時），先讀 `~/.claude/skills/parallel-dispatch/SKILL.md`，它承載切分判準、派工、整合驗收流程（worktree 與 terminal 只是 adapter 層）。

### 日常派工表

| 工作 | 派給 | model |
|------|------|-------|
| 掃 repo、找出「哪些檔案有 X」、整理清單 | Explore | haiku（實驗中，對照 verifier 首輪 OPEN 率與重派次數，量法見 `usage-review` skill） |
| 讀多份長文件並總結 | general-purpose | sonnet |
| 查網頁、抓文件 | general-purpose（`WebSearch`／`WebFetch` 在 subagent 內用） | sonnet |
| 批次機械性改檔（同 pattern 套 N 個檔） | worker | frontmatter（不帶 model） |
| 實作一個功能、修 bug、重構 | worker | frontmatter（不帶 model；複雜度訊號成立才升級，見 §5） |
| 撰寫或修改一般文件／規則段落 | worker | frontmatter（不帶 model；僅驗收交 verifier，見 §6） |
| 設計實作方案、架構取捨 | Plan | opus |
| 跨檔推理、一般高難度 review | general-purpose | opus |

### Controller 工作迴圈

一般實作與一般文件的標準路徑，四步、不預設疊多輪 review：

1. **核定完整 plan**：目標、絕對 scope、single-writer、invariants、phases、validation、completion criteria，無未決問題。
   - 分流：本波有 ≥2 個互相獨立的 issue，依上一節改做盤點，本 session 不兼任其中任何一個。同一 issue 內有 ≥2 個 ownership 不相交的切片，先判斷能不能切，不預設序列。單一 issue 的 plan 預估要動 ≥2 個模組，或 phases 涵蓋整個功能一片到底時，同樣先評估 ownership 不相交、可獨立交付的切法，值不值得切依 `~/.claude/skills/parallel-dispatch/SKILL.md` §2「值不值得」；切不出來或不值得平行就維持單片，或依同檔「單片尺寸評估」比較冷啟動、context、重讀與交接成本後選序列交接，不以工具呼叫數或預估分鐘數強制切分。
   - 素材：核定前要有要動的檔案清單、關鍵段落（本輪已讀的附原文；未讀的附 `檔案:行號範圍` 讓執行者自讀）與既有測試結構，依 §3 附進 brief，不讓執行者從零探索；同時用這份清單估單片 context。素材預設派 `Explore` 拿；只有**兩項同時成立**才由 controller 自己拿：(a) 檔案清單與測試結構能從一次批次 `rg`／`ls` 的輸出直接得出，不必再讀檔內容去找；(b) 要附的關鍵段落全在本輪已讀進主對話 context 的檔裡。任一不成立就派 `Explore`，不讓主對話為了找素材讀檔（見 §10）。不算違規：改動範圍已知且手上就有素材（單檔修正且該檔本輪已讀、延續同一 session 剛讀過的檔），即 (a)(b) 同時成立，直接核定；下述不變量前置仍適用。
   - 不變量前置：修正要對所有執行路徑或時序都成立（同一條件要在多個呼叫點處理、非同步／並行交錯、多處讀寫同一份狀態），或以新增檢查閘門作為修補手段時，plan 先寫出不變量（修完後要由結構保證成立的條件），再派 `Plan`（opus）與 `codex:codex-rescue`（不可用時改派第二個獨立 agent）各自獨立出方案並互相比對；只靠事後檢查補洞的方案不核定。不算違規：只改單一路徑、結果不依賴其他路徑或執行順序的修正。
2. **派 `worker`（single-writer）** 依 plan 產出並執行機械驗證；有界的同一交付批次可用同一個 worker 跑完多個 phase，不必每個子步驟另開一個。
3. **controller read-back** 實際檔案與指令輸出，不採信 worker 自述。用有界輸出（`git diff --stat`、`sed -n a,bp`、`grep -c`、`wc`、`head -n`）只讀判定所需的行；全文與大 diff 留給 verifier 或落檔。
4. **依 §6 風險分流選一次 review 或 verifier**；修正後依 §7 機械結案（低風險）或 fresh delta（高風險），不自動再疊第二輪 review。一般修正交接預設帶 finding＋修正 diff 派 fresh `worker`；是否續用同一 worker 依 `~/.claude/skills/parallel-dispatch/SKILL.md` §6 第 10 步的可調判斷，該步是 canonical，不在此重複條件。這不是每次修正都強制套用 parallel-dispatch 全流程。

### 自行小修的例外

controller 自行小修**只限**單點、低風險、可機械驗證、scope 無歧義的修正（如打字錯誤、單一路徑修正）；涉及授權、安全、架構取捨或主觀品質的文件一律走上面四步，不得用「順手改一下」跳過。修 verifier finding 的自修同樣適用 `~/.claude/rules/judgment.md` 6『修正者的證據』。會被執行的 CI／release 設定（`.github/workflows`、`.github/actions` 等）不屬小修例外，一律走四步；已依 `<REPO>/docs/install.md`「選配：擋主對話改 CI 設定的 hook 與 ripgrep 預設設定」裝好 hook 的環境，主對話以 Edit／Write 改這兩個目錄會被擋（缺 jq 時 fail-open）；沒裝的環境與 Bash 改檔都不經 hook，仍靠本條。

## 2. 角色與模型

Agent 工具的 `model` 參數只接受 harness 每 session 注入的 alias enum（`haiku`／`sonnet`／`opus`／`fable`）；完整 model ID 與 `inherit` 只能寫在 agent frontmatter 的 `model` 欄。alias 對照見 `<REPO>/docs/harness-facts.md`「Agent 工具 `model` 參數的 alias 對照」。

- `worker`：一般實作與文件產出的預設執行者。不帶 `model`、`effort`，由 `~/.claude/agents/worker.md` frontmatter 決定。
- `verifier`：fresh-context 驗收。顯式 `model: opus`、不帶 `effort`；升 fable 見 §6。
- `general-purpose`（全工具）：worker 升級或需要 opus／fable 時改派，使用者當次指定 Opus 執行時也派這條；須顯式指定 model，用 opus 時帶 `effort: medium`（使用者當次指定別的 effort 時從其指定）。brief 要求照 worker 合約。
- `Explore`／`Plan`：唯讀掃描與規劃；職責與限制見 `<REPO>/docs/harness-facts.md`「常用 subagent 類型」。
- `codex:codex-rescue`：外部模型（GPT 系，Codex 訂閱，不占 Claude 配額）備用車道，第二意見或整包委派用。
- 簡化剛改過的程式碼用內建 `simplify` skill。

Agent 工具有逐次 `effort` 參數，但派 `worker`／`verifier` 不帶（帶了會蓋過 frontmatter）；沒有 frontmatter effort 的車道（`general-purpose` 等）只在本 skill 或使用者要求固定 effort 時才帶，不帶時依 session 設定（不可當常數），見 `<REPO>/docs/harness-facts.md`「沒有 frontmatter effort 的 subagent」。模型升級鏈為 Sonnet → Opus → Fable，不代表必須依次嘗試；Haiku 只用於 Explore 掃描實驗，不作實作或 fallback。派 `worker`／`verifier` 前讀 `~/.claude/agents/<角色>.md` 合約；派 verifier 時只需提供該檔要求的素材，不必重述其職責。

## 3. 派工合約

欄位模板見 `~/.claude/skills/handoff/SKILL.md` §1『brief 卡』。每個 subagent prompt 必含三段，缺一段就是不合格的派工：

1. **目標與動機**：要達成什麼、為什麼。subagent 看不到主對話，脈絡要自帶：相關檔案、使用者原話、已知限制。
2. **驗收條件**：可機械判定的完成定義，自我檢查見 `~/.claude/rules/judgment.md` 12『驗收條件要能被判定』，正反例見 `<REPO>/docs/judgment-rationale.md`。填不出驗收條件代表你還沒想清楚要什麼，先想再派。
3. **回報格式**：規定回哪些欄位，預設合約見 §4。

三個非顯然的必要條件（漏掉會出事，不是風格建議）：

- **把已讀過的素材附進 prompt，並要求指令批次化**：diff、行號、關鍵段落、你已跑過的指令輸出直接貼進去並明寫「不要重讀 X」。subagent 是冷啟動，每個它自己去讀的檔與每次串行的小步工具呼叫都是一輪完整推理，會把牆鐘拉長。
- **路徑一律寫絕對路徑**：subagent 的工作目錄認知可能跟你不同，相對路徑會找錯地方。
- **prompt 開頭明寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」**：`general-purpose`／`worker` 會讀到全域 `CLAUDE.md`（含路由表）與 `~/.claude/rules/`，不加這句會把自己當 controller、逐層轉包，可遞迴多層；`Explore`／`Plan` 讀不到這些也沒有 Agent 工具，可省（見 `<REPO>/docs/harness-facts.md`「常駐內容對 subagent 的可見性」）。收到「我已再派背景工作」類回報＝未完成，立即糾正。

要求 subagent **補齊某個格式欄位**（例如每條規則的「不算違規」邊界）時，同時規定「查無來源就留空」：強制欄位一定會被填滿，原檔沒有的邊界會被當場發明。

## 4. 回報合約

**派工揭露（controller → 使用者）**：派工當下只講**指定的 agent 名稱與任務摘要**（「派 Explore 掃 repo」）；實際派送不是指定的 named role 就在名稱後標 `fallback` 並簡述差異，建立失敗回報「`<agent>` 未建立」與 runtime 原因。model／effort 與制度出處平常不報，被問到、runtime 不一致、unsupported／unavailable 或稽核時才展開，怎麼答見 `<REPO>/docs/harness-facts.md`「被問到 model／effort 時怎麼答」。主對話自己做時，只有**符合 §1 任一派工條件卻仍不派**才要交代。Codex 端 `<REPO>/global/codex/rules/dispatch.md` §3 用同一套揭露。

**Subagent 回報**，固定格式見 `~/.claude/skills/handoff/SKILL.md` §2『回報卡』與 §3『verifier 判定卡』：

- 只回**結論與證據**（檔案:行號、指令輸出關鍵行），不回原始內容傾倒。
- 需留存的長產物（報告、大 diff、清單）放 repo 內合適路徑；session 內進度使用平台 plan／task，跨 session 續接用 handoff §4『session 交接卡』，記憶分層見 `<REPO>/docs/memory-layers.md`。
- 回報長度以 controller 下一步決策需要的資訊為準。大 diff、完整清單、全文等長產物落檔，`.md` 檔名不以 `report`／`summary`／`findings`／`analysis` 開頭（否則 harness 擋 subagent 寫入，見 `<REPO>/docs/harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」），回報附路徑與摘要；驗收的逐條判定屬決策資訊，留在回報內。brief 的回報格式只列下一步決策要用的欄位，欄位以外一律落檔附路徑。要縮時先砍原始內容傾倒與重複敘述，不砍決策所需證據。
- 唯讀角色（Explore／Plan）的角色指示禁止寫檔（含 heredoc，見 `<REPO>/docs/harness-facts.md`「常用 subagent 類型」），長度只能靠 brief 控：要它回「結論＋檔案:行號範圍」，不要回原文段落；worker brief 寫「讀 X 第 a–b 行」由執行者自讀；真要原文落檔改派 general-purpose（sonnet）寫到指定路徑。附進 brief 的素材本身不計長度。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**。

## 5. 升降級

### 先選能力層

- **輕量層**：低風險、範圍明確、可機械驗證。
- **標準層**：跨檔探索、一般實作、中等推理。
- **高能力層**：架構、安全、資料遺失、不可逆或對外動作。「不可逆」「資料遺失」依 `~/.claude/rules/judgment.md` 2『不可逆副作用的定義』，只含一般側操作不算。高風險驗收見 §6。

### 升級判準

符合任一條就升級：

- 一次失敗已顯示是**模型能力或脈絡理解不足**：抓錯核心、反覆遺漏跨檔／跨系統關係，或無法維持必要脈絡。直接 fresh＋升級，不等第二次。
- 失敗原因不明，且同一子任務已兩次無進展；每次錯誤都不同且驗收條件持續增加屬正常收斂，不計無進展。有機械指標（失敗測試數、錯誤數、benchmark 值）時改以數字判定：該輪未優於歷來最佳值（含改動前基線；沒跑到量測不算變好）就算一次無進展，錯誤訊息換了也一樣。
- 任務需要跨多個檔案／系統同時推理，而你發現自己開始遺漏前面看過的細節。
- 任務需要高影響的架構、安全或不可逆取捨（高風險側，同上），不只是照明確步驟執行。

execution mistake（syntax、漏改、指令拼錯）正確修法明確時可同層補正一次；缺證據先補證據，不靠升級模型猜。

### 換路的質性訊號

任一成立就換路，不等門檻次數滿：修法越疊越多層 workaround；同一錯誤訊息在兩種不同修法後原樣出現；新 FAIL 與前一輪同根因只是換層或換形出現；diff 越改越大但驗收達成數不增；想先關掉檢查「之後再回來」。錯誤根因每次不同且在收斂的不算，看根因，不看訊息字面。每輪「照 plan 做了嗎」都 PASS 卻持續冒同根因的新症狀＝**plan 缺陷**，走下面第 3 條重新定義問題，不換更強的執行者模型。

### 三條路

門檻成立後怎麼做，只有三條路，一律附上完整失敗軌跡：**逐輪嘗試表**，執行者每輪當下記一列、不事後重建；欄位為改了什麼｜跑了什麼指令｜輸出關鍵行或指標值｜改動仍在工作樹或已回退｜為什麼判定失敗。

1. **換 fresh context 重做**：`worker` 失敗時改派新的 `general-purpose`（`model: opus`，高風險用 `model: fable`），把失敗軌跡當輸入，要求它先建立 root cause 再動手，不要沿用失敗者的假設。適用能力或脈絡理解不足；execution mistake 依上節同層補正；plan 缺陷走第 3 條，換模型無效。
2. **換平台取第二意見**：`codex:codex-rescue`，或派兩個 agent 各自獨立解再比對。
3. **重新定義問題**：換路訊號出現時，加能力層不會有用。設計審查 brief 必含：開頭寫不變量並要求由結構保證、不靠事後檢查；附全部失敗紀錄與其共同形狀並明寫「不要列補丁」；每個候選方案逐一對照已知失敗形狀，判「結構上不可能／仍需檢查」。派 `Plan`（opus）與 `codex:codex-rescue` 各自獨立判斷，分歧交使用者。累計輪數沿用原任務，換 model／role 不重設（見 §7）。

### 重試上限

同一件事最多**兩輪無進展**重試（指同一個問題的修法重試，不含驗收輪次，驗收狀態與回報點見 §7）。有進展的輪次不計，無進展的判定見上方「升級判準」。兩輪無進展代表方向錯了，換方法或問人，不要換個措辭再試第三次。Codex 端同一口徑，見 `<REPO>/global/codex/rules/dispatch.md` §5『升降級路徑』。

## 6. 驗證不自驗

製作者不驗自己的產出。首次驗收分工：

- **文件／主觀品質**：派 fresh-context `verifier`，給產出路徑及驗收條件，逐條 PASS／FAIL／UNSURE；不參與製作。
- **程式碼機械驗證**：製作者可跑測試、build、lint、實跑、schema，附輸出；讀碼不取代執行證據。
- **含外部呼叫、權限請求或不可逆副作用的程式碼**：不論風險等級，機械驗證外一律派 fresh-context `verifier` 套 `~/.claude/rubrics/code-change.md` §7『失敗路徑與不可逆副作用』；製作者的測試與突變證據只證 happy path，不得據此結案。「不可逆副作用」的範圍依 `~/.claude/rules/judgment.md` 2『不可逆副作用的定義』；§7 FAIL 修正後的結案方式依本 skill §7。
- **高風險程式碼或使用者回報的 bug**：機械驗證外加 fresh review，必問「同一錯誤還有沒有第二個現場」。fresh review 可派一個 fresh-context subagent 執行 `code-review` skill（從 diff 推 bug，不需驗收條件）；它不取代上一條的 §7 verifier 審查，有逐條驗收條件時仍派 `verifier`。
- **高風險判斷**（對外文件、不可逆、架構決策）：加獨立第二意見，可用 `codex:codex-rescue` 或兩個 agent，分歧交使用者。

Claude verifier 不因高風險自動升檔，一律顯式 `model: opus`：frontmatter 已寫 `model` 時不指定也不會繼承主對話，顯式寫是防 fallback 到沒有 frontmatter model 的 agent（如 `general-purpose`）時跟著主對話跑；真的 fallback 時另帶與 verifier frontmatter 相同的 `effort`，否則 effort 落到 session 設定。

改用 `model: fable` 前，說明訊號與證據並取得當次同意（訊號清單與歷史理由見 `<REPO>/docs/verification-policy-history.md`「fable 升檔訊號」）。使用者當次直接指定 fable 不必再問；無訊號仍可提議，但要明說沒有訊號及判斷理由。Codex 刻意維持 `sol_verifier/Sol high`，見 `<REPO>/global/codex/rules/dispatch.md` §6『驗證語意』。

**第二個現場**是取樣，不是本次必修清單；verifier 交回的 N 個實例清單同樣是取樣。逐個修完之前先問「是什麼產生它們」，再決定修哪一層。範圍內依 §7 修正分流；範圍外不擴修，登記該 repo issue 並附連結（對外授權仍依鐵律二，未授權先保留待登記項目）。連續兩輪發現都在範圍外就停手回報，不把下一批工作塞進本次。

## 7. 修正與驗收輪次

首次驗收依 §6 分工，不另派小型機械工作。verifier 第一行回報狀態與下一步（語意見 `~/.claude/rules/judgment.md` 7『驗收的停止端』），controller 照下一步走：`CONVERGED` 停止驗收；`PROSE-ONLY` 修完 read-back 後停止，不派 delta；`OPEN` 修正後依下方風險分流，不自動要求重派；`INCONCLUSIVE` 先補缺證，保留已知 FAIL，不自動重派或宣稱完成，也不以換 model 代替缺證。

**驗收後修正的風險分流**：低風險且有確定性檢查能證明 finding 已修、無相關迴歸時，controller 可自行檢查並以「finding→修正→證據」結案；安全、權限模型與存取控制的設計、不可逆、重大架構或缺乏可靠機械證據時，仍須 fresh-context delta 驗收。

**驗收輪次按產物切開**：文件待實作與證據穩定後集中更新，不逐輪加未驗宣稱。可執行宣稱（測試、斷言）在實作當下寫並驗，散文最後一次寫完才驗；同一交付批次中證據已穩定、無個別交付依賴的散文可合併成一次驗收，不得為合批延後已可交付的 issue／PR 或阻塞後續工作，行為承載文件不因此降成散文。平行批次的切片依 `~/.claude/skills/parallel-dispatch/SKILL.md` §5『VALIDATION：切片驗收』各自驗收、收斂即整合，不受此限。

**delta 派工**必帶：原 finding、修正 diff、受影響的原始驗收條件與既有證據（含修正者對新寫句子的逐句對照、對新斷言的突變紅／綠輸出）。evidence set 範圍、歸因與收斂判定的 canonical 在 verifier 合約（`~/.claude/agents/verifier.md`；Codex：`<REPO>/global/codex/agents/verifier.toml`）。首輪 brief 指定 repo 外的探針落檔路徑，delta brief 附該路徑；除「改既有檢查」的放寬探測外，delta brief 不另指定新探測形狀或開放式找漏洞。欄位見 handoff §1『brief 卡』。

**三輪回報點**：同一產出第 3 次 fresh 驗收後仍需重派（`OPEN`／`INCONCLUSIVE`），回報輪數、FAIL／UNSURE 性質、修正與剩餘項目交使用者決定，不自動開第 4 次；delta 計次，換 model／role 不重設。例外：本 session 已明確要求驗到收斂；或回報後使用者明確同意續驗，此時從零重計下一段三輪。

## 8. 何時問使用者

符合任一條就停，其餘情況自主前進不要問：

- 動作屬於**發訊息或寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案**，且本 session 尚未明確授權（鐵律二）。未授權就停止；已在本 session 明確授權時直接執行，不重複詢問。
- 發現必須擴大**功能、契約、權限或外部影響**，而非只是在已授權 scope 內補齊必要實作檔與 dependency。前者停下確認；後者自主完成並在回報說明。
- 是品味／模糊題且第二意見後仍無收斂（例如文案語氣、提案方向）。
- 驗證或動作需要使用者**本人在場**（live 登入、實機操作、手動觸發）且會阻塞後續工作：先問可用時段再派，不要先派出去等；其餘已授權且不依賴使用者的工作照常繼續。

停下來問之前，先確認要問的**前提**成立。「兩個檔案不一致」「某機制壞了」這類判定，先看清不一致的**性質**（漂移事故 vs 刻意分版）再開口。拿到授權後動手前再複查一次前提。

## 9. 工作目錄與背景任務安全

- 同一 working tree 同時只能有一個寫入者。
- 平行寫入的 subagent 必須設定 `isolation: worktree`；若仍共用 working tree，即使檔案不重疊也只能序列寫入。
- controller 自建的 worktree 預設放 `<repo>/.worktrees/<片名>`；位置、忽略方式與例外見 `~/.claude/skills/parallel-dispatch/references/worktree.md`「所有權與路徑」。
- 需要其結果才能繼續的 blocking 任務不得只依賴可能因休眠中斷的背景執行（Agent 與 Bash 的 `run_in_background` 都一樣）。預期超過 4 分鐘的指令，起跑與輪詢寫法見 worker／verifier 合約的「指令批次化」規則。
- Subagent 回報不等於實際狀態；controller 必須 read-back `git status`、`git stash list`、diff、commit 與驗證輸出。
- **唯讀角色也受影響**：verifier／Explore 與寫入者共用 working tree 時，它的唯讀結論（檔案內容、路徑與指令是否存在）仍可信，但任何跑測試／build 取得的數字都被污染，因為工作區在它量測期間被改動過。要嘛等它跑完再動手，要嘛給它 `isolation: worktree`。

## 10. 主對話不做粗活

**症狀**：大量讀檔、掃 repo、抓網頁、批次改檔在主對話進行，context 膨脹；compaction 觸發後早期決定遺失，開始重做已完成的工作或偏離原目標。

**修法**：

- 判斷基準是 §1 雙軸判斷；找素材也適用（§1 工作迴圈的素材 (a)(b) 條件）。
- 何時 compact 由使用者看 statusline 的 context 用量決定，controller 不量測、不主動提醒。controller 不能自己 compact（`/compact` 只有使用者能打）。
- 使用者說要 compact、要離開 >1h（prompt cache 1h 過期，回來整段重寫），或要「新 prompt」時，給一段可直接貼在 `/compact` 後面的**保留指示**，內容是 `~/.claude/skills/handoff/SKILL.md` §4『session 交接卡』的精簡版：目標、授權、未完成項目、**在途 subagent（名稱、任務、worktree／分支）**、產物證據位置。有在途 subagent 時先告知，建議等回報後再 compact；等不了就把在途清單寫進保留指示。量測依據見 `<REPO>/docs/harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」。
