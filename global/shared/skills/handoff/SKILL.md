---
name: handoff
description: 交接的四張固定卡，Claude 與 Codex 共用：派工 brief 卡、subagent 回報卡、verifier 判定卡、session 交接卡。寫派工 brief、收尾回報、寫驗收判定、使用者要收尾、離開、compact、交給另一個 agent、下次接續、要你開新 session 接手或另開 session 做別的事（「開新 session 繼續」「開新的 session 做 X」「開 orca session」）時使用。Use for wrap-up, handoff, resume later, open a new session, brief, report, verdict, save progress.
---

# handoff — 四張固定卡

交接格式固定，欄位不增不減，讓收的人不必重讀對話。誰在什麼時候用：§1 controller 派工、§2 subagent 回報、§3 verifier 回報、§4 session 收尾或交給另一個 agent。為什麼要這些欄位、缺欄怎麼處理，見 `<REPO>/docs/dispatch.md` §3『派工合約與回報』、§2『修正與驗收輪次』（Codex 對應：`<REPO>/global/codex/rules/dispatch.md`）。issue session 的 brief 與 result 欄位另見 `~/.claude/skills/worktree-session/SKILL.md` §2。

## 1. brief 卡

controller → subagent。缺任一欄就是不合格的派工：

```text
你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包。（只有 general-purpose 要寫；Explore／Plan／verifier 可省）
目標與動機：<要達成什麼、為什麼；使用者原話、已知限制>
Scope（只能改）：<絕對路徑清單>   不得改：<絕對路徑清單>
single-writer：本 working tree 目前只有你在寫；落地位置 <絕對路徑>
已附素材：<附了哪些 diff、行號、關鍵段落、指令輸出>   不要重讀：<檔案>   請自讀：<檔案:行號範圍>
Invariants：<修完後必須成立的條件>
Phases：<逐 phase；每 phase 跑哪些驗證>
Validation commands：<逐條可執行>
驗收條件：<逐條、可機械判定>
回報格式：依回報卡（§2）；長產物落檔 <絕對路徑>，檔名不以 report／summary／findings／analysis 開頭
```

- 路徑一律絕對路徑；已讀過的素材直接附，不叫 subagent 重讀。
- 要求補齊某個格式欄位時加一句「查無來源就留空」。
- subagent 不寫 repo（verifier 只寫 repo 外探針目錄），所以派 verifier 與查詢型 subagent 時省 single-writer、Invariants、Phases 三欄，Validation 改填「驗收用的探針與 repo 外落檔路徑」，其餘欄不省；fresh `code-review` 從 diff 推 bug，驗收條件也可省。這三欄是給 controller 自做用的：同一張卡就是開工前的 plan，目標、Scope、Invariants、Phases、Validation、驗收條件寫在第一次改檔前，之後的 verifier brief 逐字沿用。
- **派 fresh `code-review` 時**，「已附素材」列出 controller 已知、不必重報的項目，每項一句：待授權或等後續步驟的事（依賴還沒升版、tag 還沒發）、已決定不修的既有問題、已寫進 PR 內文或同時派出的驗收 brief 的風險；末尾加「認為理由不成立時才報」，沒有就寫「無」。「目標與動機」只寫 diff 做了什麼、新增或改動了哪些寫入入口與共享狀態，不列製作者自己擔心的「特別留意」檢查點：那份清單只涵蓋製作者想過的地方，reviewer 的篇幅會跟著收進去。
- **派 fresh 審查者套 `<REPO>/global/shared/rubrics/code-change.md` §7『失敗路徑與不可逆副作用』時**（diff 含外部呼叫、權限請求或不可逆副作用；誰來審見 Claude：`<REPO>/docs/dispatch.md` §1『驗證不自驗』；Codex：`<REPO>/global/codex/rules/dispatch.md` §6『驗證語意』）：驗收條件加一條「§7 每題逐一回答，查過沒問題的寫查了哪裡」，並在「已附素材」列出 diff 新增或改動的每個寫入入口與外部呼叫（函式名＋`檔案:行號`），以及會寫同一筆資料的既有入口。§7「重入」題要有這份清單才問得到「這兩個入口同時觸發會怎樣」。
- 新增或修改測試斷言與守門檢查者，在 Validation 列各自的突變指令、可暫時碰觸的路徑與還原指令。

## 2. 回報卡

subagent → controller。只寫 controller 下一步決策要用的：

```text
改動檔案：<絕對路徑；越出 scope 的另標>
完成狀態：<逐 phase 或逐條：完成｜部分｜未做＋一句原因>
驗證：<指令> → <關鍵輸出行>；突變：<斷言→突變→紅／綠，或 N/A＋原因>；現況宣稱對應的證據或缺口
未完成：<項目與原因；scope 外發現也列這裡；無則「無」>
分級：已驗證（附證據）｜待 CI｜未驗證（附原因）
長產物：<落檔絕對路徑>
```

缺欄＝未完成，controller 退回補齊。不貼完整指令輸出與全文 diff，落檔附路徑。不宣稱「已驗收」，驗收是 verifier 的事。controller 自做時不必填這張卡，但第 2 步的指令輸出與突變證據要留著給 verifier brief。

## 3. verifier 判定卡

verifier → controller。第一行固定：

```text
<CONVERGED｜PROSE-ONLY｜OPEN｜INCONCLUSIVE>：<下一步>
1. PASS
2. FAIL — <檔案:行號> — <一行理由>
3. UNSURE — <檔案:行號> — <缺什麼證據>
最大風險：<開放題「這份產出最大的風險是什麼？」的回答>
探針目錄：<repo 外絕對路徑>
受驗狀態：<HEAD 完整 SHA；tracked 檔有未提交改動時接 +<指紋 12 碼>；不在 git 工作區寫「非 git」>
```

- 下一步怎麼寫（四個狀態各自的下一步、低風險與高風險兩側的判準、controller 不得自行降級）以 verifier 合約為準，本卡不另抄：Claude 見 `~/.claude/agents/verifier.md` 規則 6 的「第一行」；Codex 見 `<REPO>/global/codex/agents/verifier.toml` 規則 12 與 `<REPO>/global/codex/agents/sol_verifier.toml` 規則 9 的「第一行」。controller 收到後怎麼走見 `<REPO>/docs/dispatch.md` §2『修正與驗收輪次』（Codex：`<REPO>/global/codex/rules/dispatch.md` §6『驗證語意』）。狀態語意見 `~/.claude/rules/judgment.md` 7『驗收的停止端』。
- PASS 每條一行（條號＋一句證據或指令關鍵行）；FAIL 與 UNSURE 才展開 `檔案:行號` 與一行理由。完整指令輸出寫進探針目錄，不貼全文。
- 受驗狀態是 verifier 開始前與判定前各取一次、兩次相同的值，取法與兩次不同時判 `INCONCLUSIVE` 的規定在 verifier 合約（Claude 規則 8；Codex `verifier.toml` 規則 13、`sol_verifier.toml` 規則 10）。controller 把它照抄到 issue session result 的 `Verification` 欄（`<REPO>/global/shared/skills/worktree-session/SKILL.md` §2）與 PR 的驗收戳記（`<REPO>/global/shared/skills/create-pr/SKILL.md` 2.6）。

## 4. session 交接卡

session → 未來的 session 或另一個 agent，兩平台同一格式：

```markdown
# Handoff
更新：<時間與時區>   專案：<絕對路徑>

**所在位置**：<branch、HEAD、worktree 絕對路徑、dirty 狀態>
**已完成**：<耐久的完成項，附檔案路徑與驗證分級>
**待檢查**：<還沒驗的宣稱、待 read-back、待 CI>
**下一步**：<依序的下一步動作>
**風險／待確認**：<阻塞、不確定處、等使用者授權的動作>
**為什麼這樣做**：<關鍵決定、被排除的方案、接手者必須保留的限制>
```

- **何時寫**：收尾、要離開、要 compact、要等人、交給另一個 agent、多階段長任務每個 phase 結束（全域邊界 6）。單輪可完成的小任務不必寫。
- **寫到哪**：使用者給路徑優先。否則，平台裝有 remember plugin 時（Claude：`remember:remember` skill 存在）把寫好的卡交給該 skill 存檔——內容用本節格式取代它自己的三段格式，路徑由它的腳本決定、不要自己猜或解析，下個 session 開頭會自動注入，store 由 plugin 自己備份；它回 `REFUSED` 就照下一句處理。沒有 plugin 或被拒時寫專案根 `.agents/HANDOFF.md`；不能寫就把卡回在對話並明說沒寫檔。更新 `.agents/HANDOFF.md` 時保留仍有效的內容，移除已過時的完成項；走 plugin 時是整份取代，上一份已在 session 開頭注入過，把其中仍有效的項目寫進新卡。
- **使用者要開新 session 接手**（「開新 session 繼續」「可以開新的主 session 繼續」「開新 main session 做」；「可以開…」這種句型也是要求，不是在告知可以收尾）：這是要你把新 session 啟動起來，不是要一段 prompt 或交接筆記。存好卡後照 `~/.claude/skills/worktree-session/references/cli.md`「接手 session」（Codex：`<REPO>/global/shared/skills/worktree-session/references/cli.md`）啟動並 read-back 提示已送達，再告訴使用者到哪個分頁繼續。主對話 context 到門檻、還有未做的 phase 時的交接同樣由你啟動，不等使用者開口。使用者明說「給我 prompt」，或該節的啟動方式在這台機器不可用時，才改給可直接貼的指令，並明說沒有啟動。使用者要另開 session 做旁支調查或別的事（「開新 session 幫我查 X」，不是接手同一件工作）時不寫交接卡，照同一節的「旁支 session」寫 brief 再啟動。兩種都要開成使用者看得到的互動 session，不用 `claude -p`、`claude --bg` 或背景執行代替，除非使用者明說要 headless 或背景執行。
- **內容**：只寫耐久狀態，不重述對話；事實與猜測分開；完成項附驗證分級，沒驗就寫未驗證；不寫 secrets、token、憑證與原始 log，必要時只引關鍵一行；短到一分鐘內掃得完。
- **compact 保留指示**就是這張卡的精簡版：目標、授權、未完成項目、在途 subagent（名稱、任務、worktree／分支）、產物證據位置；規則見 `<REPO>/docs/dispatch.md` §6『主對話 context 管理』。
