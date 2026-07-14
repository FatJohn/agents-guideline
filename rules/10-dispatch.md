# 10 — 模型調度守則

> 讀者：主對話（指揮官）。每次要派工、選模型之前照著做。
> 本檔事實的查證日與時效規則統一記在 `00-environment.md` 開頭。

## 0. 可用模型與 subagent（查證過，不要憑印象改）

**Agent 工具的 `model` 參數**可逐次指定常用 alias，也可使用完整 model ID 或 `inherit`：

| 參數值 | 實際型號 | 用途定位 |
|--------|----------|----------|
| `haiku` | claude-haiku-4-5 | 平台可用模型；不列入本制度 active routing |
| `sonnet` | claude-sonnet-5 | 掃描、總結、批次機械車道主力；Pro 檔位的實作預設 |
| `opus` | claude-opus-4-8 | 難題升級、高風險判斷 |
| `fable` | claude-fable-5 | 最高階；高風險、最終升級與獨立驗收 |

agent frontmatter 的 effort 可設 `low`／`medium`／`high`／`xhigh`／`max`，也可由 session／workflow 控制；實際可用範圍受模型與組織設定限制（見 `00-environment.md` §查證過的事實）。

**入口檔位依訂閱事實**（`00-environment.md`）：主對話預設 Opus，而 **subagent 不指定 `model` 時繼承主對話的模型**。所以上表的 model 欄是「顯式 routing」指示：掃描、總結、抓網頁與批次套用已驗證 pattern 寫明 `sonnet`（這條車道即使在 Max 也保留——opus 在這類任務品質增益趨近零，且 opus 配額耗盡時的被動降級不挑任務）；實作與規劃在 **Max 檔位預設 `opus`**，Pro 檔位降回 `sonnet`；`fable` 只在明確高風險或最終升級時指定。Haiku 雖可能可用，但不作為本制度的預設或 fallback。

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
- `verifier`——fresh-context 驗收（本系統自帶，定義在 `~/.claude/agents/verifier.md`）。
- `recovery-worker`——標準層實作者（sonnet 或 opus 進場）同一子任務兩次失敗或揭露高風險後的 fresh-context recovery 實作（opus／xhigh，先建 root cause 再動手；與失敗者同階時，價值在乾淨 context 與強制 root cause；本系統自帶）。
- `escalation-planner`——Plan 或探索路徑（opus）無法建立可靠方案時的規劃升級（fable／xhigh，唯讀；本系統自帶）。
- `escalation-worker`——recovery-worker 再兩次失敗或確認 root cause 需要 Fable 能力時的最終升級實作；opus 進場者的能力天花板型失敗可直升（fable／xhigh；本系統自帶）。
- `code-simplifier:code-simplifier`——簡化整理剛改過的程式碼。
- `codex:codex-rescue`——外部模型（GPT 系，使用者有 Codex 訂閱）。兩種用法：(a) 卡死或高風險判斷時的第二意見；(b) 把獨立性高的完整實作／診斷任務整包委派出去，與 Claude subagent 平行運作。
- `claude-code-guide`——回答 Claude Code / API 本身的問題。

註：Claude 端不設 Codex `scanner`／`explorer`／`planner`／`worker` 的等價 custom agent——內建 `Explore`／`Plan`／`general-purpose` 加逐次指定 `model` 已涵蓋，且本制度不把 haiku 列入 active routing。自建 agent 只補「Agent 呼叫無法逐次指定 effort」的缺口（recovery／escalation／驗收角色需要綁定 effort 與行為合約）。另注意 Claude agent 沒有 sandbox 欄位：唯讀角色（escalation-planner、verifier、fable-verifier）靠 tools 清單與指令合約約束，controller 驗收時仍須 read-back `git status` 確認無意外寫入。

## 1. 雙軸判斷：context 成本 × 任務耦合

符合任一條件時優先派 subagent：任務可獨立且主對話只需結論；原始輸出量大且後續不需反覆引用；有互不依賴子任務可安全平行；需要 fresh-context 驗收。

以下情況保留主對話：工作小但與決策高度耦合；需頻繁共享可變狀態；需要即時使用者互動；平行寫入無法隔離。

| 工作 | 派給 | model |
|------|------|-------|
| 掃 repo、找出「哪些檔案有 X」 | Explore | sonnet |
| 讀多份長文件並總結 | general-purpose | sonnet |
| 查網頁、抓文件 | general-purpose（firecrawl skill 在 subagent 內用） | sonnet |
| 批次機械性改檔（同 pattern 套 N 個檔） | general-purpose | sonnet |
| 實作一個功能 | general-purpose | opus（Max 檔位；Pro 檔位降回 sonnet） |
| 設計實作方案 | Plan | opus／high |
| 同一子任務兩次失敗後的 root-cause recovery 實作 | recovery-worker | opus／xhigh |
| Plan 或探索路徑無法形成可靠方案時的規劃升級（先 fresh Plan 重試一次，見 §4） | escalation-planner | fable／xhigh |
| recovery 再失敗後的最終升級實作 | escalation-worker | fable／xhigh |
| 獨立性高的完整實作、或需要換視角的診斷 | codex:codex-rescue | —（外部 GPT 系，不占 Claude 配額） |
| 一般文件／主觀品質 read-back | verifier | opus／high |
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

- **實作側：標準層實作者在同一個子任務連錯兩次（無論錯誤相同與否）或揭露高風險** → 依入口與失敗型態選路，prompt 一律必附**對應門檻的證據**——失敗入口附完整失敗軌跡（試了什麼、輸出什麼、為什麼判定失敗）；高風險入口附風險判定依據（發現了什麼、為何屬高風險）——不能只丟原題：
  - 失敗者是 **sonnet** → 一律改派 fresh-context `recovery-worker`（opus／xhigh，跳階＋fresh），它必須先建立 root cause 再編輯。
  - 失敗者是 **opus／xhigh（Max 檔位進場）**、失敗型態是 **context 汙染型**（錯誤有在演變、越修越糟、開始疊 workaround）→ 仍派 `recovery-worker`：同階 fresh 重啟，價值在乾淨 context 與強制 root cause，這型失敗換更大的模型沒用。
  - 失敗者是 **opus／xhigh**、失敗型態是 **能力天花板型**（反覆撞同一面牆、模型明顯理解問題但解不動）→ 直升 `escalation-worker`（fable／xhigh），不浪費一輪同階 recovery。型態難辨時先走同階 recovery（便宜的那條）。
- **實作側：recovery-worker 在同一子任務再失敗兩次，或確認 root cause 需要 Fable 能力** → 升 `escalation-worker`（fable／xhigh），prompt 附對應門檻證據（再失敗兩次＝兩層失敗軌跡；確認需要 Fable＝recovery 的 root cause 報告與判定理由）；重大架構／安全／資料遺失／不可逆決策也須先確認需要 Fable 能力才符合此門檻。Fable 與 Codex Sol 屬同一個最高風險角色層。
- **規劃側：Plan 或探索路徑（opus）無法建立可靠方案** → 先以 fresh-context Plan（opus）重述問題並附完整探索輸出重試一次；仍無法形成可靠方案才升 `escalation-planner`（fable／xhigh），同樣附完整軌跡。它唯讀出 plan，實作仍走上面的實作側路徑。
- **fable 回報 unsupported 或 unavailable** → 不得宣稱已使用 Fable；改用 fresh-context opus 或 `codex:codex-rescue`，並把 model mapping 標記為「未驗證」。
- **fable 仍卡住** → 改用 Codex Sol 作跨平台第二意見，或依 `20-judgment.md` §3 問使用者；不可只換措辭重試第三輪。
- **降級**：難題被 Opus／Fable 解出可重複且可機械驗證的 pattern 後，把 pattern 寫進 prompt，降回 sonnet 批次套用；不降到 haiku。
- **重試上限**：同一件事最多重試兩輪。兩輪後還不行，代表方向錯了，換方法或問人，不要換個措辭再試第三次。

## 5. 驗證不自驗（鐵律三）

主觀判斷、文件品質與高風險產出不得由製作者自己背書。測試、build、lint、實跑與 schema 驗證等可重現的機械驗證可由製作者執行，但必須附指令與輸出；高風險程式碼另加 fresh-context review。

- **文件／主觀品質** → 派 fresh-context `verifier` 做 read-back：給它「產出檔案路徑＋驗收條件清單」，逐條判 PASS/FAIL；verifier 不參與製作。
- **高風險文件／規則／架構決策／最終驗收** → 使用 `fable-verifier`；它與 Codex `sol-verifier/Sol high` 對應，只讀取、找碴與判定，不修正產物。
- **程式碼機械驗證** → 測試、build、lint、實跑、schema 可由製作者執行，但必須附指令與輸出；「我看程式碼邏輯是對的」不算驗證。
- **高風險程式碼** → 除機械驗證外再加 fresh-context review。
- **高風險判斷**（對外文件、不可逆操作、架構決策）→ 加第二意見：codex-rescue，或派兩個 agent 各自獨立解再比對；不一致時把分歧點呈給使用者。
- 驗證 prompt 要求**找碴**而不是背書：「假設這份產出有問題，找出來」比「確認這份沒問題」有效。

模型升級只提高解題能力，不取代對外授權；發訊息、merge、push 共享分支、發佈或不可逆動作仍以共用 `20-judgment.md` 與全域 `CLAUDE.md` 的授權邊界為準。
