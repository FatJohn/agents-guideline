# parallel-dispatch 設計說明

> 非常駐內容：架構說明與刻意不做的理由，用到才讀。判準與邊界仍在 `<REPO>/skills/parallel-dispatch/SKILL.md`。

## Adapter 契約

原位置：`SKILL.md` §9「Human-in-the-loop 與 execution adapter」。

一份 adapter 只回答五件事——
- **launch**：用什麼指令或呼叫啟動一個 worker、brief 怎麼餵進去；
- **follow-up**：怎麼把追加指示送給同一個 worker，或帶原 report／finding／diff 重派；
- **query status**：怎麼看它還在不在跑。git read-back 永遠是真相，容器的指示燈只是線索；
- **collect**：report 從哪裡拿（回傳值或落檔路徑）；
- **stop**：怎麼終止它、怎麼確認真的停了。確認不了就依 `SKILL.md` §8 當作仍可能在寫。

外加 workspace 建法（誰建 worktree、路徑與 branch 命名）與本平台 worker／verifier 的**角色名稱與 model 對應表**（名稱映射，不是 policy）。**不能**做 task decomposition、merge strategy、integration policy、授權判斷，也不能把「同一 session 的 subagent」「一個 terminal window」「一個 workspace」偷換成 task 的定義。adapter 內的機制事實（路徑、branch 命名、旗標）以各自檔案為 canonical；harness 實測數據集中在 `<REPO>/docs/harness-facts.md`。沒有 controller 的人手多開 session 走 `references/cli.md`「沒有 controller」一節，仍受 `SKILL.md` §3 批次上限與 `SKILL.md` §6 integration tree 的約束，不得把「不同 session 各自完成」當成已整合。

## 刻意不做（屬 framework 層，不進本 skill）

原位置：`SKILL.md` §10「邊界」。

持久化的 task state machine 或 event log、背景 daemon 監督 worker、自動 retry／escalation 引擎、dashboard、跨 run 的 metrics 自我調整、runtime／capability registry、獨立 arbiter agent 常設角色。這些各有價值，但需要一個能保證原子寫入與排程的 runtime；用 markdown 手刻只會得到沒人維護的帳。狀態就是 git（SHA、branch、worktree）加 status board 與 integration record。adapter 特有的機制事實只存在各自 reference，不可跨 adapter 套用；commit／rebase 權限的來源永遠是 worker 合約，不是 adapter。
