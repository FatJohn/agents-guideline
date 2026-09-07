# 10 — 模型調度守則

> 讀者：主對話（指揮官）。每次要派工、選模型之前照著做。
> 本檔事實的查證日與時效規則統一記在 `00-environment.md` 開頭。

## 0. 可用模型與 subagent（查證過，不要憑印象改）

**Agent 工具的 `model` 參數**可逐次指定常用 alias（`haiku`／`sonnet`／`opus`／`fable`；harness 每 session 已注入同一份 enum，2026-08-30 由 Agent 工具 schema 現查確認），也可使用完整 model ID 或 `inherit`。alias→實際型號的對照 2026-08-30 搬到 `../docs/harness-facts.md`「Agent 工具 `model` 參數的 alias 對照」——alias 會隨平台改版重新指向新一代同層模型，要宣稱某次派工實際跑在哪個型號，以當場自報的 model ID 為準。

agent frontmatter 的 effort 可設 `low`／`medium`／`high`／`xhigh`／`max`，也可由 session／workflow 控制；實際可用範圍受模型與組織設定限制（見 `../docs/harness-facts.md`）。

**入口檔位依訂閱事實**：使用者的 Claude Code 訂閱為 Max；主對話 effort 由 `~/.claude/settings.json` 的 `effortLevel: xhigh` 設定，model 由 UI 選擇（2026-07-25 核對；當次實際型號以主對話自報的 model ID 為準）。主對話預設 Opus，**subagent 不指定 `model` 時繼承主對話的模型**，所以本檔各表寫出的 model 欄是「顯式 routing」指示——掃描、總結、抓網頁與批次套用已驗證 pattern 寫明 `sonnet`（即使在 Max 也保留這條車道：opus 在這類任務的品質增益趨近零，且 opus 配額耗盡時的被動降級不挑任務），實作與規劃 Max 檔位預設 `opus`、Pro 檔位降回 `sonnet`，`fable` 只在明確高風險的**實作／規劃**時指定（驗收不走這條，見 §5）；Haiku 不作為本制度的預設或 fallback。

升級順序：`Sonnet → Opus → Fable`（能力與風險的升級鏈，不代表每個任務都要經過三階段）。各層的使用邊界與 effort 預設：Sonnet／依任務設定＝範圍清楚、可重現驗證、無重大風險；Opus／high 或以上＝需要架構取捨、未決問題較多或 Sonnet 已失敗；Fable／high＝只在風險條件成立時，角色上等同 Codex Sol。**哪種工作派給誰、跑哪個 model 的 canonical 是 §1 那張表**，這裡不重複第二份。

**常用 subagent 類型**（`subagent_type`）：
- `Explore`——唯讀搜索，掃 repo、找檔案、答「哪裡有 X」。不能改檔。
- `Plan`——出實作計畫、架構取捨。
- `general-purpose`——多步驟執行、實作、批次改檔（全工具）。
- 本系統自帶 1 個角色：`verifier`（驗收）。**行為合約與找碴範圍的 canonical 在 `~/.claude/agents/verifier.md`**，派工前讀該檔；**不分風險等級一律顯式帶 `model: opus`**（與該檔 frontmatter 一致），升 `fable` 的訊號與授權要求見 §5，不另設角色。
- 簡化整理剛改過的程式碼——用內建 `simplify` skill，不是 subagent（`code-simplifier` plugin 2026-08-06 現查未安裝，寫成 `subagent_type` 會叫不出來）。
- `codex:codex-rescue`——外部模型（GPT 系，Codex 訂閱，不占 Claude 配額），第二意見或整包委派用。備用車道：2026-09-02 現查近 45 天派工 0 次，不再展開用法。
- `claude-code-guide`——回答 Claude Code / API 本身的問題。**不是每個 session 都有**：2026-08-06 實測 `claude -p` 起的 session 清單裡沒有它（主對話清單裡有），機制未查明。派工前先確認當下清單真的有這個名字。

## 1. 雙軸判斷：context 成本 × 任務耦合

符合任一條件時優先派 subagent：任務可獨立且主對話只需結論；原始輸出量大且後續不需反覆引用；有互不依賴子任務可安全平行；需要 fresh-context 驗收。

以下情況保留主對話：工作小但與決策高度耦合；需頻繁共享可變狀態；需要即時使用者互動；平行寫入無法隔離。

| 工作 | 派給 | model |
|------|------|-------|
| 掃 repo、找出「哪些檔案有 X」 | Explore | sonnet |
| 讀多份長文件並總結 | general-purpose | sonnet |
| 查網頁、抓文件 | general-purpose（`WebSearch`／`WebFetch` 在 subagent 內用；沒有 firecrawl，2026-08-06 已移除） | sonnet |
| 批次機械性改檔（同 pattern 套 N 個檔） | general-purpose | sonnet |
| 實作一個功能 | general-purpose | opus／high 或以上（Max 檔位；Pro 檔位降回 sonnet） |
| 設計實作方案 | Plan | opus／high |
| 跨檔推理、一般高難度 review | general-purpose | opus／high 或以上 |

這張表只列日常派工。升級怎麼做見 §4，驗收要派給誰見 §5。

## 工作目錄與背景任務安全

- 同一 working tree 同時只能有一個寫入者。
- 平行寫入的 subagent 必須設定 `isolation: worktree`；若仍共用 working tree，即使檔案不重疊也只能序列寫入。
- 需要其結果才能繼續的 blocking 任務不得只依賴可能因休眠中斷的背景執行。
- Subagent 回報不等於實際狀態；controller 必須 read-back `git status`、diff、commit 與驗證輸出。
- **唯讀角色也受影響**：verifier／Explore 與寫入者共用 working tree 時，它的**唯讀結論**
  （檔案內容、路徑與指令是否存在）仍可信，但**任何跑測試／build 取得的數字**都被污染——
  工作區在它量測期間被改動過。要嘛等它跑完再動手，要嘛給它 `isolation: worktree`。

## 2. 派工合約

每個 subagent prompt 必含三段，缺一段就是不合格的派工：

1. **目標與動機**——要達成什麼、為什麼（subagent 看不到主對話，脈絡要自帶：相關檔案、使用者原話、已知限制）。
2. **驗收條件**——可機械判定的完成定義；判準：另一個 agent 能只憑這句話判定過或不過。填不出驗收條件代表你還沒想清楚要什麼，先想再派。
3. **回報格式**——規定回什麼、多長（預設合約見 §3）。

兩個非顯然的必要條件（漏掉會出事，不是風格建議）：

- **路徑一律寫絕對路徑**——subagent 的工作目錄認知可能跟你不同，相對路徑會找錯地方。
- **prompt 開頭明寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」**——subagent 也會讀到全域 rules，不加這句會把「指揮官不下場」套在自己身上、逐層轉包（2026-07-07 實測發生過 5 層遞迴）。收到「我已再派背景工作」類回報＝未完成，立即糾正。

`verifier` 已把「需要哪些輸入、找碴範圍到哪、什麼時候標收斂」寫進 `~/.claude/agents/verifier.md`——派工時只需提供該檔要求的素材，不必重述其職責。

## 3. 回報合約

**派工揭露（controller → 使用者）**：派工當下只講**指定的 agent 名稱與任務摘要**（「派 Explore 掃 repo」）；實際派送不是指定的 named role 就在名稱後標 `fallback` 並簡述差異，建立失敗回報「`<agent>` 未建立」與 runtime 原因。model／effort 與制度出處平常不報，被問到、runtime 不一致、unsupported／unavailable 或稽核時才展開——怎麼答（報呼叫參數、註明 runtime 未驗證）見 `../docs/harness-facts.md`「被問到 model／effort 時怎麼答」；報制度出處要指得出是 §1、§5 或 `20-judgment.md` §1 的哪一條，「範圍明確」這類自由心證不算。主對話自己做時，只有**符合 §1 任一派工條件卻仍不派**才要交代。Codex 端 `../codex/rules/10-dispatch-codex.md` §3 用同一套揭露。

**Subagent 回報：**

- Subagent 只回**結論與證據**（檔案:行號、指令輸出關鍵行），不回原始內容傾倒。
- 需留存的長產物（報告、大 diff、清單）放 repo 內合適路徑；session 內進度使用平台 plan／task，跨 session 續接才寫 `.codex/HANDOFF.md`。
- 回報上限預設 30 行；需要更多就落檔。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**（鐵律一）。

## 4. 升降級路徑

升級**門檻**（幾次失敗、什麼算高風險）的 canonical 在 `20-judgment.md` §1。門檻成立後怎麼做，只有三條路，一律附上完整失敗軌跡（改了什麼／跑了什麼指令／輸出關鍵行／為什麼判定失敗，每次嘗試各一段）：

1. **換 fresh context 重做**——派新的 general-purpose（`model: opus`，高風險用 `fable`），把失敗軌跡當輸入，要求它先建立 root cause 再動手，不要沿用失敗者的假設。
2. **換平台取第二意見**——`codex:codex-rescue`，或派兩個 agent 各自獨立解再比對。
3. **重新定義問題**——見 `20-judgment.md` §1「換路的質性訊號」；訊號出現時，加能力層不會有用。

**降級**：難題解出可重複、可機械驗證的 pattern 後，把 pattern 寫進 prompt 降回 sonnet 批次套用；不降到 haiku。
**重試上限**：同一件事最多兩輪（指同一個問題的修法重試，不含驗收輪次——驗收狀態與回報點見
`20-judgment.md` §2「停止端」）。兩輪後還不行代表方向錯了，換方法或問人，不要換個措辭再試第三次。

Codex 端的 `../codex/rules/10-dispatch-codex.md` §5「升降級路徑」是另一平台的 canonical；驗收分流
則依兩端共用的 `20-judgment.md` §2「停止端」落地。

## 5. 驗證不自驗（鐵律三）

首次驗收分工：
- **文件／主觀品質**：派 fresh-context `verifier`，給產出路徑及驗收條件，逐條 PASS／FAIL／UNSURE；不參與製作。
- **程式碼機械驗證**：製作者可跑測試、build、lint、實跑、schema，附輸出；讀碼不取代執行證據。
- **高風險程式碼或使用者回報的 bug**：機械驗證外加 fresh review，必問「同一錯誤還有沒有第二個現場」。
- **高風險判斷**（對外文件、不可逆、架構決策）：加獨立第二意見，可用 codex-rescue 或兩個 agent，分歧交使用者。

Claude verifier 不因高風險自動升檔，一律顯式 `model: opus`；不指定會繼承主對話。
改用 `model: fable` 前，說明訊號與證據並取得當次同意：
(a) 同一條件連續兩輪 UNSURE；(b) 與實跑或獨立結論矛盾且 controller 無法裁決；
(c) 後來實測抓到它漏掉的安全、授權或不可逆缺陷。使用者當次直接指定 fable 不必再問；
無上述訊號仍可提議，但要明說沒有訊號及判斷理由。Codex 刻意維持 `sol_verifier/Sol high`，
見 `../codex/rules/10-dispatch-codex.md` §6「驗證語意」。歷史理由見 `<REPO>/docs/verification-policy-history.md`。

「第二個現場」是取樣，不是本次必修清單：範圍內依 `20-judgment.md` §2「停止端」修正分流；
範圍外不擴修，登記該 repo issue 並附連結（對外授權仍依鐵律二，未授權先保留待登記項目）。
連續兩輪發現都在範圍外就停手回報，不把下一批工作塞進本次。

✅ **正例**：三種漏擋只修本次涵蓋的一種，另兩種需 allowlist 決策，列 issue 後續處理。
❌ **反例**：原驗收條件已過，仍連續十輪補下一種寫法及其新迴歸。

修正的風險分流、delta 範圍、四種狀態與三輪回報點統一依 `20-judgment.md` §2「停止端」。
模型升級不取代對外授權；發訊息、merge、push、發佈或不可逆動作仍依鐵律二。
