# 10 — 模型調度守則

> 讀者：主對話（指揮官）。每次要派工、選模型之前照著做。
> 本檔事實的查證日與時效規則統一記在 `00-environment.md` 開頭。

## 0. 可用模型與 subagent（查證過，不要憑印象改）

**Agent 工具的 `model` 參數**可逐次指定常用 alias（`haiku`／`sonnet`／`opus`／`fable`；harness 每 session 已注入同一份 enum，2026-08-30 由 Agent 工具 schema 現查確認），也可使用完整 model ID 或 `inherit`。alias→實際型號的對照 2026-08-30 搬到 `../docs/harness-facts.md`「Agent 工具 `model` 參數的 alias 對照」——alias 會隨平台改版重新指向新一代同層模型，要宣稱某次派工實際跑在哪個型號，以當場自報的 model ID 為準。

agent frontmatter 的 effort 可設 `low`／`medium`／`high`／`xhigh`／`max`，也可由 session／workflow 控制；實際可用範圍受模型與組織設定限制（見 `../docs/harness-facts.md`）。

**入口檔位依訂閱事實**（`00-environment.md`）：主對話預設 Opus，**subagent 不指定 `model` 時繼承主對話的模型**，所以本檔各表寫出的 model 欄是「顯式 routing」指示——掃描、總結、抓網頁與批次套用已驗證 pattern 寫明 `sonnet`（即使在 Max 也保留這條車道：opus 在這類任務的品質增益趨近零，且 opus 配額耗盡時的被動降級不挑任務），實作與規劃 Max 檔位預設 `opus`、Pro 檔位降回 `sonnet`，`fable` 只在明確高風險時指定；Haiku 不作為本制度的預設或 fallback。

### Active model routing

| 階段 | 預設 model／effort | 使用邊界 |
|------|--------------------|----------|
| 一般探索、文件研究、批次機械工作與已驗證 pattern 套用 | Sonnet／依任務設定 | 範圍清楚、可重現驗證、無重大風險 |
| 實作（Max 檔位）、困難規劃、跨檔推理與一般高難度 review | Opus／high 或以上 | 需要架構取捨、未決問題較多或 Sonnet 已失敗 |
| 高風險、不可逆、重大安全判斷與獨立驗收 | Fable／high | 只在風險條件成立時使用；角色上等同 Codex Sol |

升級順序：`Sonnet → Opus → Fable`。這是能力與風險的升級鏈，不代表每個任務都要經過三個階段。

**常用 subagent 類型**（`subagent_type`）：
- `Explore`——唯讀搜索，掃 repo、找檔案、答「哪裡有 X」。不能改檔。
- `Plan`——出實作計畫、架構取捨。
- `general-purpose`——多步驟執行、實作、批次改檔（全工具）。
- 本系統自帶 1 個角色：`verifier`（驗收）。**行為合約與找碴範圍的 canonical 在 `~/.claude/agents/verifier.md`**，派工前讀該檔；高風險驗收用同一個角色、呼叫時指定 `model: fable`，不另設角色。
- 簡化整理剛改過的程式碼——用內建 `simplify` skill，不是 subagent（`code-simplifier` plugin 2026-08-06 現查未安裝，寫成 `subagent_type` 會叫不出來）。
- `codex:codex-rescue`——外部模型（GPT 系，使用者有 Codex 訂閱，不占 Claude 配額）。兩種用法：(a) 卡死或高風險判斷時的第二意見；(b) 把獨立性高的完整實作／診斷任務整包委派出去（需要換視角的診斷同樣走這條），與 Claude subagent 平行運作。
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
| 實作一個功能 | general-purpose | opus（Max 檔位；Pro 檔位降回 sonnet） |
| 設計實作方案 | Plan | opus／high |

這張表只列日常派工。升級怎麼做見 §4，驗收要派給誰見 §5，整包委派給外部模型見 §0 的 `codex:codex-rescue`。

主對話**可以**自己做的：讀單一已知檔案的特定段落、改一兩個檔、跑一條指令、跟使用者對話、做決策。

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

**派工揭露（controller → 使用者，每次派 subagent 都要）**：派工當下講明**派了誰**（agent 名稱即可，例如「派 Explore 掃 repo」）。目的是讓使用者看得出派工規則有沒有被遵守，不是建稽核鏈——model／effort 與制度出處使用者問了才報；報制度出處要指得出是 §1、§5 或 `20-judgment.md` §1 的哪一條，「範圍明確」這類自由心證不算。主對話自己做時，只有在**符合 §1 任一派工條件卻仍不派**時才要交代；例行讀檔、跑指令、對話不必。

被問到 model／effort 時報**呼叫時指定的參數**，並註明 runtime 未驗證，不要改口說已驗證。為什麼不稽核 runtime model、各類角色的 effort 各自怎麼標，見 `../docs/harness-facts.md`「被問到 model／effort 時怎麼答」（2026-08-30 搬出）。

Codex 端 `../codex/rules/10-dispatch-codex.md` §3 要求的是四項揭露＋證據層級，**兩邊詳略不同是刻意分版、不是漂移**：Codex surface 拿得到 runtime model 的 read-back，Claude 的 Agent 工具沒有。不要修齊。

**Subagent 回報：**

- Subagent 只回**結論與證據**（檔案:行號、指令輸出關鍵行），不回原始內容傾倒。
- 需留存的長產物（報告、大 diff、清單）放 repo 內合適路徑；session 內進度使用平台 plan／task，跨 session 續接才寫 `.codex/HANDOFF.md`。
- 回報上限預設 30 行；需要更多就落檔。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**（鐵律一）。

## 4. 升降級路徑

升級**門檻**（幾次失敗、什麼算高風險）的 canonical 在 `20-judgment.md` §1。門檻成立後怎麼做，只有三條路，一律附上完整失敗軌跡（改了什麼／跑了什麼指令／輸出關鍵行／為什麼判定失敗，每次嘗試各一段）：

1. **換 fresh context 重做**——派新的 general-purpose（`model: opus`，高風險用 `fable`），把失敗軌跡當輸入，要求它先建立 root cause 再動手，不要沿用失敗者的假設。
2. **換平台取第二意見**——`codex:codex-rescue`，或派兩個 agent 各自獨立解再比對。
3. **重新定義問題**——見 `20-judgment.md` §4；換路的訊號出現時，加能力層不會有用。

**降級**：難題解出可重複、可機械驗證的 pattern 後，把 pattern 寫進 prompt 降回 sonnet 批次套用；不降到 haiku。
**重試上限**：同一件事最多兩輪。兩輪後還不行代表方向錯了，換方法或問人，不要換個措辭再試第三次。

Codex 端的 `../codex/rules/10-dispatch-codex.md` §5「升降級路徑」未動，兩邊刻意分版。

## 5. 驗證不自驗（鐵律三）

> 本節是「誰驗什麼」的 canonical 位置；「什麼叫完成」在 `20-judgment.md` §2。

主觀判斷、文件品質與高風險產出不得由製作者自己背書。測試、build、lint、實跑與 schema 驗證等可重現的機械驗證可由製作者執行，但必須附指令與輸出；高風險程式碼、以及修使用者實際回報的 bug，另加 fresh-context review。

驗收條件不必每次重寫——按產出類型直接引用 rubric（產出類型 → rubric 檔的對照表在 `20-judgment.md` §5「品質底線怎麼驗」，canonical 只有那一份），再補該次任務特有的條件。

- **文件／主觀品質** → 派 fresh-context `verifier` 做 read-back：給它「產出檔案路徑＋驗收條件清單」，逐條判 PASS/FAIL；verifier 不參與製作。
- **高風險文件／規則／架構決策** → 同樣派 `verifier`，呼叫時指定 `model: fable`（Codex 端對應 `sol_verifier`／Sol high，role 名一律底線，見 README「檔案結構」）。
- **程式碼機械驗證** → 測試、build、lint、實跑、schema 可由製作者執行，但必須附指令與輸出；「我看程式碼邏輯是對的」不算驗證。
- **高風險程式碼，或修使用者實際回報的 bug** → 除機械驗證外再加 fresh-context review。「高風險」要當場判斷，「使用者回報的 bug」不用——只要這件事成立就派，不必先判定風險等級或改動大小。這類驗收一定要問「**同一個錯誤還有沒有第二個現場**」：那是製作者最不適合回答的問題（他的心智模型正是漏掉那一處的原因），也是機械驗證最驗不到的——測試只覆蓋你改的那條路，改對的那條會全綠。
- **高風險判斷**（對外文件、不可逆操作、架構決策）→ 加第二意見：codex-rescue，或派兩個 agent 各自獨立解再比對；不一致時把分歧點呈給使用者。
- 驗證 prompt 要求**找碴**而不是背書：「假設這份產出有問題，找出來」比「確認這份沒問題」有效。

模型升級只提高解題能力，不取代對外授權；發訊息、merge、push 共享分支、發佈或不可逆動作仍以共用 `20-judgment.md` 與全域 `CLAUDE.md` 的授權邊界為準。
