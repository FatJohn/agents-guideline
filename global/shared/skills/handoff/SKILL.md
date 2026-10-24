---
name: handoff
description: 交接的四張固定卡，Claude 與 Codex 共用：派工 brief 卡、subagent 回報卡、verifier 判定卡、session 交接卡。寫派工 brief、收尾回報、寫驗收判定、使用者要收尾、離開、compact、交給另一個 agent、下次接續時使用。Use for wrap-up, handoff, resume later, brief, report, verdict, save progress.
---

# handoff — 四張固定卡

交接格式固定，欄位不增不減，讓收的人不必重讀對話。誰在什麼時候用：§1 controller 派工、§2 subagent 回報、§3 verifier 回報、§4 session 收尾或交給另一個 agent。為什麼要這些欄位、缺欄怎麼處理，見 `~/.claude/skills/dispatch/SKILL.md` §3『派工合約』、§4『回報合約』、§7『修正與驗收輪次』（Codex 對應：`<REPO>/global/codex/rules/dispatch.md`）。平行切片專用欄位另見 `~/.claude/skills/parallel-dispatch/references/templates.md`。

## 1. brief 卡

controller → subagent。缺任一欄就是不合格的派工：

```text
你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包。（Explore／Plan 可省）
目標與動機：<要達成什麼、為什麼；使用者原話、已知限制>
Scope（只能改）：<絕對路徑清單>   不得改：<絕對路徑清單>
single-writer：本 working tree 目前只有你在寫；落地位置 <絕對路徑>
已附素材：<附了哪些 diff、行號、關鍵段落、指令輸出>   不要重讀：<檔案>   請自讀：<檔案:行號範圍>
Invariants：<修完後必須成立的條件>
Phases：<逐 phase；每 phase 跑哪些驗證>
Validation commands：<逐條可執行；能一次串完的批次化>
驗收條件：<逐條、可機械判定>
回報格式：依回報卡（§2）；長產物落檔 <絕對路徑>，檔名不以 report／summary／findings／analysis 開頭
```

- 路徑一律絕對路徑；已讀過的素材直接附，不叫 subagent 重讀。
- 要求補齊某個格式欄位時加一句「查無來源就留空」。
- Invariants、Phases、Validation 是派 `worker` 的 approved plan 必備，且未決問題必須已解決或明列為禁止範圍（缺項 worker 會退回）；唯讀探索或規劃可省這三欄，其餘欄不省。
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

缺欄＝未完成，controller 退回補齊。不貼完整指令輸出與全文 diff，落檔附路徑。不宣稱「已驗收」，驗收是 verifier 的事。

## 3. verifier 判定卡

verifier → controller。第一行固定：

```text
<CONVERGED｜PROSE-ONLY｜OPEN｜INCONCLUSIVE>：<下一步>
1. PASS
2. FAIL — <檔案:行號> — <一行理由>
3. UNSURE — <檔案:行號> — <缺什麼證據>
最大風險：<開放題「這份產出最大的風險是什麼？」的回答>
探針目錄：<repo 外絕對路徑>
```

- 下一步：`CONVERGED`→停止驗收；`PROSE-ONLY`→controller 修完 read-back 結案，不再派 verifier；`OPEN`→寫明低風險機械結案或高風險 fresh delta；`INCONCLUSIVE`→列缺少的證據，補證後依風險分流。風險分流由verifier判、寫在第一行：低風險＝不屬下列高風險項，且有確定性檢查能證明 finding 已修且無相關迴歸，controller 自行檢查並以「finding→修正→證據」結案；高風險＝FAIL 涉及安全、權限模型與存取控制的設計、不可逆副作用（`~/.claude/rules/judgment.md` 2 高風險側）、重大架構，或缺乏可靠機械證據，須 fresh-context delta。controller 不得自行降級。狀態語意見 `~/.claude/rules/judgment.md` 7『驗收的停止端』。
- PASS 每條一行（條號＋一句證據或指令關鍵行）；FAIL 與 UNSURE 才展開 `檔案:行號` 與一行理由。完整指令輸出寫進探針目錄，不貼全文。

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

- **何時寫**：收尾、要離開、要 compact、交給另一個 agent、長任務每個 phase 結束（可恢復脈絡的要求見 `~/.claude/rules/judgment.md` 15『可中斷的長任務要留可恢復脈絡』）。
- **寫到哪**：使用者給路徑優先；否則專案根 `.agents/HANDOFF.md`；不能寫就把卡回在對話並明說沒寫檔。更新既有檔時保留仍有效的內容，移除已過時的完成項。
- **內容**：只寫耐久狀態，不重述對話；事實與猜測分開；完成項附驗證分級，沒驗就寫未驗證；不寫 secrets、token、憑證與原始 log，必要時只引關鍵一行；短到一分鐘內掃得完。
- **compact 保留指示**就是這張卡的精簡版：目標、授權、未完成項目、在途 subagent（名稱、任務、worktree／分支）、產物證據位置；規則見 dispatch §10『主對話 context 管理』。
