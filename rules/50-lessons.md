# 50 — 教訓日誌（append-only）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與瘦身規則見 `40-maintenance.md`。

- [2026-07-06][global] 盤點發現持久記憶目錄全空，過去所有 session 學到的東西都蒸發了 → 每 session 結束前自查該寫的記憶，這比當日任何單一任務都值錢 → 已套用到：40-maintenance.md §4
- [2026-07-06][global] Agent 工具呼叫無法指定 effort；effort 只能設在 agent 定義的 frontmatter → 需要特定 effort 的角色先建 `~/.claude/agents/` 定義 → 已套用到：00-environment.md、agents/verifier.md
- [2026-07-06][document] 驗收 agent 查 `.remember/` 時跑去 `~/.claude` 下找，實際在專案根目錄，差點誤判環境異常 → 給 subagent 的路徑一律寫絕對路徑，文件裡的路徑要寫到能直接 `ls` 的精確度 → 已套用到：30-delegation-templates.md 通用規則
- [2026-07-06][document] 第一版守則把「教訓記錄」分散在各檔檔尾，與交接欄用途重疊、弱模型不知道寫哪邊 → 教訓集中單一檔案（本檔），升級成正式判準才進 rules → 已套用到：40-maintenance.md §3
- [2026-07-06][global] 使用者背景第一版只憑單一 repo 的文件推斷，寫得過窄（把 side project 當工作重心）→ 背景事實用 `gh` CLI 等來源現查，文件裡的列舉標明「不要依賴，現查為準」→ 已套用到：00-environment.md
- [2026-07-06][global] 每份 rules 檔頭都放查證日期，重複且像 changelog 浪費 context → 查證日全系統只記在 00-environment.md 一處，其他檔用指向 → 已套用到：00-environment.md、10-dispatch.md
- [2026-07-06][global] 開場看 `.remember/` 只有 logs 就判定 remember plugin 沒在運作，實際上記憶檔是 session 進行中才寫入、其他專案都有完整檔組 → 判定「某機制壞了/沒在用」前，多看幾個專案與時間點，單一時點快照會騙人 → 已套用到：00-environment.md §記憶機制
- [2026-07-06][macroeconomics-report] 文件重組 sed 批次改連結、把「早已因改標題而死掉」的 anchor 原樣搬過去、verifier 抓到 3 條死鏈 → 改 markdown 標題（不只搬檔）也會斷下游 anchor、改完要 rg "檔名#" 全 repo 驗存活；手算 GitHub anchor 易錯、歷史文件用檔案層連結+章節名文字更穩 → 已套用到：尚未（再踩就提案入 40-maintenance §6）

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
