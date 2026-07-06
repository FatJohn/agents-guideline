# 10 — 模型調度守則

> 讀者：主對話（指揮官）。每次要派工、選模型之前照著做。
> 本檔事實的查證日與時效規則統一記在 `00-environment.md` 開頭。

## 0. 可用模型與 subagent（查證過，不要憑印象改）

**Agent 工具的 `model` 參數**只接受四個值：

| 參數值 | 實際型號 | 用途定位 |
|--------|----------|----------|
| `haiku` | claude-haiku-4-5 | 便宜、快，機械性批次工作 |
| `sonnet` | claude-sonnet-5 | 預設主力，八成派工用它 |
| `opus` | claude-opus-4-8 | 難題升級、高風險判斷 |
| `fable` | claude-fable-5 | 最高階；除非使用者明說，不要動用 |

effort 無法在 Agent 呼叫指定，要靠 agent 定義的 frontmatter（見 `00-environment.md` §查證過的事實）。

**Max 方案注意**：主對話預設 Opus，而 **subagent 不指定 `model` 時繼承主對話的模型**——等於預設全用 Opus。所以上表的 model 欄是「顯式降級」指示：機械性、批次性工作一定要寫明 `haiku`/`sonnet`，省的是配額（rate limit）與時間；判斷性工作則直接省略 model 讓它繼承 Opus 即可。

**常用 subagent 類型**（`subagent_type`）：
- `Explore`——唯讀搜索，掃 repo、找檔案、答「哪裡有 X」。不能改檔。
- `Plan`——出實作計畫、架構取捨。
- `general-purpose`——多步驟執行、實作、批次改檔（全工具）。
- `verifier`——fresh-context 驗收（本系統自帶，定義在 `~/.claude/agents/verifier.md`）。
- `code-simplifier:code-simplifier`——簡化整理剛改過的程式碼。
- `codex:codex-rescue`——外部模型（GPT 系，使用者有 Codex 訂閱）。兩種用法：(a) 卡死或高風險判斷時的第二意見；(b) 把獨立性高的完整實作／診斷任務整包委派出去，與 Claude subagent 平行運作。
- `claude-code-guide`——回答 Claude Code / API 本身的問題。

## 1. 指揮官不下場

以下工作**一律派 subagent**，主對話只收結論。判斷基準：會把超過一頁原始內容帶進主對話的動作，都不該自己做。

| 工作 | 派給 | model |
|------|------|-------|
| 掃 repo、找出「哪些檔案有 X」 | Explore | sonnet（簡單的用 haiku） |
| 讀多份長文件並總結 | general-purpose | sonnet |
| 查網頁、抓文件 | general-purpose（firecrawl skill 在 subagent 內用） | sonnet |
| 批次機械性改檔（同 pattern 套 N 個檔） | general-purpose | haiku |
| 實作一個功能 | general-purpose | sonnet |
| 設計實作方案 | Plan | 省略（繼承 Opus） |
| 獨立性高的完整實作、或需要換視角的診斷 | codex:codex-rescue | —（外部 GPT 系，不占 Claude 配額） |
| 驗收任何檔案產出 | verifier | （定義內建 sonnet + effort high） |

主對話**可以**自己做的：讀單一已知檔案的特定段落、改一兩個檔、跑一條指令、跟使用者對話、做決策。

## 2. 派工三件套

每個 subagent prompt 必含三段，缺一段就是不合格的派工（模板見 `30-delegation-templates.md`）：

1. **目標與動機**——要達成什麼、為什麼（subagent 看不到主對話，脈絡要自帶）。
2. **驗收條件**——可機械判定的完成定義；判準：另一個 agent 能只憑這句話判定過或不過。
3. **回報格式**——規定回什麼、多長。

## 3. 回報合約

- Subagent 只回**結論與證據**（檔案:行號、指令輸出關鍵行），不回原始內容傾倒。
- 長產物（報告、大 diff、清單）**落檔傳路徑**：臨時的放 scratchpad，要留的放 repo 內合適路徑。
- 回報上限預設 30 行；需要更多就落檔。
- 回報必須分級：**已驗證（附證據）／待 CI／未驗證**（鐵律一）。

## 4. 升降級路徑

- **haiku 錯一次** → 同任務直接升 sonnet，不重試 haiku。
- **sonnet 在同一個子任務連錯兩次** → 升 opus，且 prompt 必須附**完整失敗軌跡**（試了什麼、輸出什麼、為什麼判定失敗），不能只丟原題。
- **opus（含主對話本身）也卡住** → 升級的形式不是更大的 Claude，而是**換腦袋**：(a) 派 fresh-context 的 opus subagent 帶完整失敗軌跡重解（乾淨 context 常常就夠）；(b) codex-rescue 換外部視角；(c) 都不行走 `20-judgment.md` §3 問使用者。
- **降級**：難題被高階模型解出「模式」後（例如確認了正確的修法 pattern），把 pattern 寫進 prompt，降回 sonnet/haiku 批次套用到其餘案例。
- **重試上限**：同一件事最多重試兩輪。兩輪後還不行，代表方向錯了，換方法或問人，不要換個措辭再試第三次。

## 5. 驗證不自驗（鐵律三）

做的人不驗自己的成果。宣稱完成之前：

- **檔案產出** → 派 `verifier` 做 read-back：給它「產出檔案路徑＋驗收條件清單」，它逐條判 PASS/FAIL。
- **程式碼** → 跑測試或實跑，以指令輸出為證。沒有測試就先寫一個最小驗證腳本。「我看程式碼邏輯是對的」不算驗證。
- **高風險判斷**（對外文件、不可逆操作、架構決策）→ 加第二意見：codex-rescue，或派兩個 agent 各自獨立解再比對；不一致時把分歧點呈給使用者。
- 驗證 prompt 要求**找碴**而不是背書：「假設這份產出有問題，找出來」比「確認這份沒問題」有效。
