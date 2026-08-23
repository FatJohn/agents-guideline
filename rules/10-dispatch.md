# 10 — 模型調度守則

> 讀者：主對話（指揮官）。每次要派工、選模型之前照著做。
> 本檔事實的查證日與時效規則統一記在 `00-environment.md` 開頭。

## 0. 可用模型與 subagent（查證過，不要憑印象改）

**Agent 工具的 `model` 參數**可逐次指定常用 alias，也可使用完整 model ID 或 `inherit`。alias 會隨平台改版重新指向新一代同層模型——要宣稱某次派工實際跑在哪個型號，以當場自報的 model ID 為準，不引用本表：

| 參數值 | 實際型號 | 用途定位 |
|--------|----------|----------|
| `haiku` | claude-haiku-4-5 | 平台可用模型；不列入本制度 active routing |
| `sonnet` | claude-sonnet-5 | 掃描、總結、批次機械車道主力；Pro 檔位的實作預設 |
| `opus` | claude-opus-5 | 難題升級、高風險判斷 |
| `fable` | claude-fable-5 | 最高階；高風險、最終升級與獨立驗收 |

agent frontmatter 的 effort 可設 `low`／`medium`／`high`／`xhigh`／`max`，也可由 session／workflow 控制；實際可用範圍受模型與組織設定限制（見 `../docs/harness-facts.md`）。

**入口檔位依訂閱事實**（`00-environment.md`）：主對話預設 Opus，**subagent 不指定 `model` 時繼承主對話的模型**，所以上表的 model 欄是「顯式 routing」指示——掃描、總結、抓網頁與批次套用已驗證 pattern 寫明 `sonnet`（即使在 Max 也保留這條車道：opus 在這類任務的品質增益趨近零，且 opus 配額耗盡時的被動降級不挑任務），實作與規劃 Max 檔位預設 `opus`、Pro 檔位降回 `sonnet`，`fable` 只在明確高風險或最終升級時指定；Haiku 不作為本制度的預設或 fallback。

### Active model routing

| 階段 | 預設 model／effort | 使用邊界 |
|------|--------------------|----------|
| 一般探索、文件研究、批次機械工作與已驗證 pattern 套用 | Sonnet／依任務設定 | 範圍清楚、可重現驗證、無重大風險 |
| 實作（Max 檔位）、困難規劃、跨檔推理與一般高難度 review | Opus／high 或以上 | 需要架構取捨、未決問題較多或 Sonnet 已失敗 |
| 高風險、不可逆、重大安全判斷與最終獨立驗收 | Fable／high（驗收）或 xhigh（升級規劃與實作） | 只在風險或升級條件成立時使用；角色上等同 Codex Sol |

升級順序：`Sonnet → Opus → Fable`。這是能力與風險的升級鏈，不代表每個任務都要經過三個階段。

**常用 subagent 類型**（`subagent_type`）：
- `Explore`——唯讀搜索，掃 repo、找檔案、答「哪裡有 X」。不能改檔。
- `Plan`——出實作計畫、架構取捨。
- `general-purpose`——多步驟執行、實作、批次改檔（全工具）。
- 本系統自帶 5 個角色：`verifier`／`fable-verifier`／`recovery-worker`／`escalation-planner`／`escalation-worker`。**進場門檻、model／effort、tools 與行為合約的 canonical 全在 `~/.claude/agents/<角色>.md` 的 frontmatter 與本文**，派工前讀該檔；哪個門檻成立後派給誰見 §4（2026-08-22 移除此處的 model／effort 抄本）。
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

這張表只列日常派工。升級要派給誰見 §4 指向的 `../docs/escalation-paths.md`，驗收要派給誰見 §5，整包委派給外部模型見 §0 的 `codex:codex-rescue`。

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

各自帶行為合約的角色（`verifier`／`fable-verifier`／`recovery-worker`／`escalation-worker`／`escalation-planner`）已把「需要哪些輸入、缺什麼就停」寫進 `~/.claude/agents/<角色>.md`——派工時只需提供該檔要求的素材，不必重述其職責。

## 3. 回報合約

**派工揭露（controller → 使用者，每次派 subagent 都要）**：派工當下講明四項——**派給誰／model／effort／依據**。依據要指得出制度出處（§1、§5 或 `20-judgment.md` §1 的哪一條），「範圍明確」這類自由心證不算。主對話自己做時，只有在**符合 §1 任一派工條件卻仍不派**時才要交代；例行讀檔、跑指令、對話不必。

揭露不帶證據就只是宣告，稽核不到。所以：

- **派工 prompt 一律要求 subagent 自報實際 model ID 與該資訊的來源**，原樣轉給使用者。這是稽核鏈上唯一的外部證據，但仍是自述，非鐵證。
- 分清**「我派了什麼」**（Agent 呼叫參數，你自述即可）與**「它實際跑在什麼」**（以自報 model ID 為準，見 §0）。兩者不符時**明確標出不一致**並說明處置，不得原樣轉述當沒事。
- **自己忘了在 prompt 裡要求＝重派一次**，不得標「未驗證」了事——agent 結束後補問不到，那是自造的證據缺口（`20-judgment.md` §2）。agent 有回但沒照做，才寫「未取得自報，model 未驗證」。
- **effort 無法逐次指定**（Agent 工具無 effort 參數，見 §0）**，也無法 runtime 自報**：有 `agents/<角色>.md` 的自帶角色引其 frontmatter 並標「宣告值」；外部模型（`codex:codex-rescue`）model／effort 都寫「不適用」；其餘一律寫「未指定，繼承主對話」（內建 type 與 plugin／平台提供的 agent 如 `claude-code-guide` 都在此類）。

**Subagent 回報：**

- Subagent 只回**結論與證據**（檔案:行號、指令輸出關鍵行），不回原始內容傾倒。
- 需留存的長產物（報告、大 diff、清單）放 repo 內合適路徑；session 內進度使用平台 plan／task，跨 session 續接才寫 `.codex/HANDOFF.md`。
- 回報上限預設 30 行；需要更多就落檔。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**（鐵律一）。

## 4. 升降級路徑

升級**門檻**（幾次失敗、什麼算高風險）的 canonical 在 `20-judgment.md` §1；門檻成立後**派給誰**、以及升級 prompt 必附哪些證據，2026-08-23 整節搬到 `../docs/escalation-paths.md`（不常駐，升級真的發生時才讀）。本節編號保留不動，下游引用的「§4『升降級路徑』」仍指得到這裡。

Codex 端的對應章節是 `../codex/rules/10-dispatch-codex.md` §5「升降級路徑」，未搬動。

## 5. 驗證不自驗（鐵律三）

> 本節是「誰驗什麼」的 canonical 位置；「什麼叫完成」在 `20-judgment.md` §2。

主觀判斷、文件品質與高風險產出不得由製作者自己背書。測試、build、lint、實跑與 schema 驗證等可重現的機械驗證可由製作者執行，但必須附指令與輸出；高風險程式碼、以及修使用者實際回報的 bug，另加 fresh-context review。

驗收條件不必每次重寫——按產出類型直接引用 rubric（產出類型 → rubric 檔的對照表在 `20-judgment.md` §5「品質底線怎麼驗」，canonical 只有那一份），再補該次任務特有的條件。

- **文件／主觀品質** → 派 fresh-context `verifier` 做 read-back：給它「產出檔案路徑＋驗收條件清單」，逐條判 PASS/FAIL；verifier 不參與製作。
- **高風險文件／規則／架構決策／最終驗收** → 使用 `fable-verifier`；它與 Codex `sol_verifier/Sol high` 對應（Codex role 名一律底線，見 README「檔案結構」），只讀取、找碴與判定，不修正產物。
- **程式碼機械驗證** → 測試、build、lint、實跑、schema 可由製作者執行，但必須附指令與輸出；「我看程式碼邏輯是對的」不算驗證。
- **高風險程式碼，或修使用者實際回報的 bug** → 除機械驗證外再加 fresh-context review。「高風險」要當場判斷，「使用者回報的 bug」不用——只要這件事成立就派，不必先判定風險等級或改動大小。這類驗收一定要問「**同一個錯誤還有沒有第二個現場**」：那是製作者最不適合回答的問題（他的心智模型正是漏掉那一處的原因），也是機械驗證最驗不到的——測試只覆蓋你改的那條路，改對的那條會全綠。
- **高風險判斷**（對外文件、不可逆操作、架構決策）→ 加第二意見：codex-rescue，或派兩個 agent 各自獨立解再比對；不一致時把分歧點呈給使用者。
- 驗證 prompt 要求**找碴**而不是背書：「假設這份產出有問題，找出來」比「確認這份沒問題」有效。

模型升級只提高解題能力，不取代對外授權；發訊息、merge、push 共享分支、發佈或不可逆動作仍以共用 `20-judgment.md` 與全域 `CLAUDE.md` 的授權邊界為準。
