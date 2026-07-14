# 10 — 模型調度守則

> 讀者：主對話（指揮官）。每次要派工、選模型之前照著做。
> 本檔事實的查證日與時效規則統一記在 `00-environment.md` 開頭。

## 0. 可用模型與 subagent（查證過，不要憑印象改）

**Agent 工具的 `model` 參數**可逐次指定常用 alias，也可使用完整 model ID 或 `inherit`：

| 參數值 | 實際型號 | 用途定位 |
|--------|----------|----------|
| `haiku` | claude-haiku-4-5 | 平台可用模型；不列入本制度 active routing |
| `sonnet` | claude-sonnet-5 | 預設主力，八成派工用它 |
| `opus` | claude-opus-4-8 | 難題升級、高風險判斷 |
| `fable` | claude-fable-5 | 最高階；高風險、最終升級與獨立驗收 |

agent frontmatter 的 effort 可設 `low`／`medium`／`high`／`xhigh`／`max`，也可由 session／workflow 控制；實際可用範圍受模型與組織設定限制（見 `00-environment.md` §查證過的事實）。

**Max 方案注意**：主對話預設 Opus，而 **subagent 不指定 `model` 時繼承主對話的模型**——等於預設全用 Opus。所以上表的 model 欄是「顯式 routing」指示：一般工作寫明 `sonnet`，困難規劃與高難度實作使用 `opus`；`fable` 只在明確高風險或最終升級時指定。Haiku 雖可能可用，但不作為本制度的預設或 fallback。

### Active model routing

| 階段 | 預設 model／effort | 使用邊界 |
|------|--------------------|----------|
| 一般探索、文件研究、實作與機械驗證 | Sonnet／依任務設定 | 範圍清楚、可重現驗證、無重大風險 |
| 困難規劃、跨檔推理與一般高難度 review | Opus／high 或以上 | 需要架構取捨、未決問題較多或 Sonnet 已失敗 |
| 高風險、不可逆、重大安全判斷與最終獨立驗收 | Fable／high | 只在風險或升級條件成立時使用；角色上等同 Codex Sol |

升級順序：`Sonnet → Opus → Fable`。這是能力與風險的升級鏈，不代表每個任務都要經過三個階段。

**常用 subagent 類型**（`subagent_type`）：
- `Explore`——唯讀搜索，掃 repo、找檔案、答「哪裡有 X」。不能改檔。
- `Plan`——出實作計畫、架構取捨。
- `general-purpose`——多步驟執行、實作、批次改檔（全工具）。
- `verifier`——fresh-context 驗收（本系統自帶，定義在 `~/.claude/agents/verifier.md`）。
- `code-simplifier:code-simplifier`——簡化整理剛改過的程式碼。
- `codex:codex-rescue`——外部模型（GPT 系，使用者有 Codex 訂閱）。兩種用法：(a) 卡死或高風險判斷時的第二意見；(b) 把獨立性高的完整實作／診斷任務整包委派出去，與 Claude subagent 平行運作。
- `claude-code-guide`——回答 Claude Code / API 本身的問題。

## 1. 雙軸判斷：context 成本 × 任務耦合

符合任一條件時優先派 subagent：任務可獨立且主對話只需結論；原始輸出量大且後續不需反覆引用；有互不依賴子任務可安全平行；需要 fresh-context 驗收。

以下情況保留主對話：工作小但與決策高度耦合；需頻繁共享可變狀態；需要即時使用者互動；平行寫入無法隔離。

| 工作 | 派給 | model |
|------|------|-------|
| 掃 repo、找出「哪些檔案有 X」 | Explore | sonnet |
| 讀多份長文件並總結 | general-purpose | sonnet |
| 查網頁、抓文件 | general-purpose（firecrawl skill 在 subagent 內用） | sonnet |
| 批次機械性改檔（同 pattern 套 N 個檔） | general-purpose | sonnet |
| 實作一個功能 | general-purpose | sonnet |
| 設計實作方案 | Plan | opus／high |
| 獨立性高的完整實作、或需要換視角的診斷 | codex:codex-rescue | —（外部 GPT 系，不占 Claude 配額） |
| 一般文件／主觀品質 read-back | verifier | sonnet／high |
| 高風險文件、規則、架構決策與最終驗收 | fable-verifier | fable／high |

主對話**可以**自己做的：讀單一已知檔案的特定段落、改一兩個檔、跑一條指令、跟使用者對話、做決策。

## 工作目錄與背景任務安全

- 同一 working tree 同時只能有一個寫入者。
- 平行寫入的 subagent 必須設定 `isolation: worktree`；若仍共用 working tree，即使檔案不重疊也只能序列寫入。
- 需要其結果才能繼續的 blocking 任務不得只依賴可能因休眠中斷的背景執行。
- Subagent 回報不等於實際狀態；controller 必須 read-back `git status`、diff、commit 與驗證輸出。

## 2. 派工三件套

每個 subagent prompt 必含三段，缺一段就是不合格的派工（模板見 `30-delegation-templates.md`）：

1. **目標與動機**——要達成什麼、為什麼（subagent 看不到主對話，脈絡要自帶）。
2. **驗收條件**——可機械判定的完成定義；判準：另一個 agent 能只憑這句話判定過或不過。
3. **回報格式**——規定回什麼、多長。

## 3. 回報合約

- Subagent 只回**結論與證據**（檔案:行號、指令輸出關鍵行），不回原始內容傾倒。
- 需留存的長產物（報告、大 diff、清單）放 repo 內合適路徑；session 內進度使用平台 plan／task，跨 session 續接才寫 `.codex/HANDOFF.md`。
- 回報上限預設 30 行；需要更多就落檔。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**（鐵律一）。

## 4. 升降級路徑

- **sonnet 在同一個子任務連錯兩次** → 升 opus，且 prompt 必須附**完整失敗軌跡**（試了什麼、輸出什麼、為什麼判定失敗），不能只丟原題。
- **opus 遇到重大架構／安全／資料遺失／不可逆問題，或帶完整失敗軌跡仍無法建立可靠方案** → 升 fable；Fable 與 Codex Sol 屬同一個最高風險角色層。
- **fable 回報 unsupported 或 unavailable** → 不得宣稱已使用 Fable；改用 fresh-context opus 或 `codex:codex-rescue`，並把 model mapping 標記為「未驗證」。
- **fable 仍卡住** → 改用 Codex Sol 作跨平台第二意見，或依 `20-judgment.md` §3 問使用者；不可只換措辭重試第三輪。
- **降級**：難題被 Opus／Fable 解出可重複且可機械驗證的 pattern 後，把 pattern 寫進 prompt，降回 sonnet 批次套用；不降到 haiku。
- **重試上限**：同一件事最多重試兩輪。兩輪後還不行，代表方向錯了，換方法或問人，不要換個措辭再試第三次。

## 5. 驗證不自驗（鐵律三）

主觀判斷、文件品質與高風險產出不得由製作者自己背書。測試、build、lint、實跑與 schema 驗證等可重現的機械驗證可由製作者執行，但必須附指令與輸出；高風險程式碼另加 fresh-context review。

- **文件／主觀品質** → 派 fresh-context `verifier` 做 read-back：給它「產出檔案路徑＋驗收條件清單」，逐條判 PASS/FAIL；verifier 不參與製作。
- **高風險文件／規則／架構決策／最終驗收** → 使用 `fable-verifier`；它與 Codex `verifier/Sol` 對應，只讀取、找碴與判定，不修正產物。
- **程式碼機械驗證** → 測試、build、lint、實跑、schema 可由製作者執行，但必須附指令與輸出；「我看程式碼邏輯是對的」不算驗證。
- **高風險程式碼** → 除機械驗證外再加 fresh-context review。
- **高風險判斷**（對外文件、不可逆操作、架構決策）→ 加第二意見：codex-rescue，或派兩個 agent 各自獨立解再比對；不一致時把分歧點呈給使用者。
- 驗證 prompt 要求**找碴**而不是背書：「假設這份產出有問題，找出來」比「確認這份沒問題」有效。

模型升級只提高解題能力，不取代對外授權；發訊息、merge、push 共享分支、發佈或不可逆動作仍以共用 `20-judgment.md` 與全域 `CLAUDE.md` 的授權邊界為準。
