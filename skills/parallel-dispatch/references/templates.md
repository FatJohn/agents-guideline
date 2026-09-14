# 格式模板

配合 [../SKILL.md](../SKILL.md) 使用。這些是 orchestration 層的資料格式，與執行環境無關；adapter 只補「落地位置」與「launch 方式」兩欄。

## Task graph（SKILL §3）

```text
<Feature 名>
├─ A: <一句目標>            ownership: <路徑…>        batch 1
├─ B: <一句目標>            ownership: <路徑…>        batch 1
├─ C: <一句目標>            depends on A              batch 2
└─ D: Integration            depends on A + B + C      §6
```

Pattern B 版本：

```text
<Problem>
├─ S1: <同一份 brief>        worker: <agent>   落地位置: <path>
├─ S2: <同一份 brief>        worker: <agent>   落地位置: <path>
└─ Compare: depends on S1 + S2
     準則: 同一組測試 / 正確性 / 可維護性 / 複雜度 / 與既有風格一致
     winner only → §6
```

graph 旁附重疊矩陣（片 × 預估路徑，含測試與 fixture）與語意風險清單。

## Worker brief（SKILL §3–§4；controller → worker）

```text
你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具或其他方式轉包。

Objective:
<要達成什麼、為什麼；使用者原話或 spec 節錄>

Scope / Ownership（允許修改，repo 相對路徑）:
- <dir>/**
- <file>:<function or line range>

Do not modify:
- <路徑或子系統>
- 其他片的 ownership（列出）

Dependencies:
- <依賴哪片、其介面或簽名已凍結為何>；無則寫「無」

Execution environment（由 adapter 填）:
- 落地位置: <絕對路徑；隔離時為 worktree>
- 你是此位置唯一寫入者
- 可否 commit / rebase: <adapter 決定>
- 禁止: push、開 PR、開 issue、merge、tracker、刪除非自建檔案

Expected output:
<程式碼 / 測試 / 文件…>

Validation commands:
<逐條可執行指令；含探針的還原指令與預期會紅的既有檢查>

Done when:
- <逐條可機械判定>

Report format: 依「Worker report」，上限 30 行；長輸出落檔 <log-dir>/<slice>-<name>.log
```

## Worker report（SKILL §4；worker → controller）

```text
Status: completed | blocked | failed
Summary: <做了什麼，三句內>
Files changed: <路徑清單；越出 ownership 的另標>
Validation: <跑了哪些 test / lint / build，關鍵輸出行>
Issues: <發現的問題、未完成項、建議升級或重切的理由>
Integration notes: <merge 時要注意的介面、順序、共用狀態>
Commit: <SHA；沒有 commit 寫「uncommitted」>
Location: <落地位置絕對路徑、branch、HEAD>
分級: 已驗證（附證據）| 待 CI | 未驗證
```

只回「Done」或缺任一欄 ＝ 未完成，controller 退回補齊。

## Integration record（SKILL §6–§7；controller 自留）

```text
Batch: <n>   Base SHA (start): <sha>
Slice A: HEAD <sha>  PR <#>  slice verification: CONVERGED @<sha>
Slice B: HEAD <sha>  PR <#>  slice verification: CONVERGED @<sha>
Integration tree: <tree/commit sha>  full tests: <結果與指令>
Semantic risk: <none | list>  integration verifier: <not needed | result>
Merge order & gates:
  1. A → gate on base <sha>: <結果>  merged <sha>  tree match: yes  CI: <狀態>
  2. B → gate on base <sha>: ...
Estimate vs actual paths: <落差>
Metrics: elapsed / wait-for-verification / rework count / tokens (if available) / defects found at integration
Cleanup: <worktree.md 條件逐項 yes/no，指令與輸出>
```

## Status board（SKILL §9；給使用者看）

```text
為什麼拆: <一句>            Pattern: A | B
片        worker   狀態                 驗收          整合
A         <agent>  running | blocked    —             —
B         <agent>  completed            CONVERGED     ready
C         <agent>  waiting on A         —             —
Blocked 原因: <一句，含需要使用者決定的事>
下一步: <一句>
```
