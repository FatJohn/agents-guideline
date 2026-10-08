# 獨立 issue 分 session 試行（2026-10）

> 承接 `rules/10-dispatch.md` §1「互相獨立的 issue 一個 issue 一個頂層 session」與 `skills/parallel-dispatch/SKILL.md` §1「先分流」。本檔記錄改規則當時的量測與試行方法；結論是**待試行的假設**，不是已證實的節省。

## 改規則時的量測（2026-10-07）

窗口：2026-10-05 19:00～10-07 約 23:00（台北），本機 `~/.claude/projects/**/*.jsonl`，usage 以 `(message.id, requestId)` 去重；金額為 API 牌價等價（量測腳本假設的單價，未對官方價目現查：Opus in $5／Sonnet in $3，cache write 1h 2×、5m 1.25×、read 0.1×，output 5×），不是帳單或額度。使用者回報同窗口週額度 52%。

- 合計約 $1,634：主對話 46%、verifier 17.5%、worker（Sonnet）14.6%、worker-opus 10.7%、general-purpose 7.8%；以 model 分 Opus 82%。
- 主對話每次請求的 context 中位 255K、P90 534K；主對話費用 68% 是 cache read（重讀既有 context）。
- 最貴 5 個主對話 session，以字元數拆 context 來源：subagent 交回報告（`Another Claude session sent a message` 包裝的 hand-back）占 25–37%，派工 brief（Agent 工具輸入）占 8–17%，Bash 輸入＋輸出約 33–40%。抽查其中一個 session：54 則交回報告，中位 8.4K 字、最大 22K 字。
- 這 5 個 session 都沒有用 Skill 工具叫用 parallel-dispatch；多 issue 同時派工的行為推斷來自 `rules/10-dispatch.md` §1 與「Controller 工作迴圈」第 1 步的平行入口。

另一份同期報告（外部模型產出，全部 project 一個月、token 計數不加權）顯示 subagent 占 cache creation 約七到八成；那是 token 數；本窗口換成金額後主對話（Opus、大 context）仍是最大的單一角色，兩者口徑不同、不矛盾。

## 機制假設

一個 controller 同時扛 N 個 issue 時，每輪請求都重讀所有在途 issue 的 brief 與回報，成本約隨「在途 issue 數 × 輪數」成長；拆成一個 issue 一個 session 後，每個 session 只重讀自己的往返。抵銷項：每個新 session 的冷啟動（常駐規則、repo 探索）、issue session 自己仍要派 worker／verifier、盤點 session 的成本。

## 試行與判定方法

1. 下一批互相獨立的 issue 走「盤點 session＋issue session」；model／effort 與 worker／verifier 路線不同時改動，避免分不出差異來源。
2. 每個 issue 記：session ID（盤點、issue、其下 subagent）、四種 usage counter、主對話 context 中位與 P90、修正輪數、驗收結論、是否有 ownership 衝突或重複探索。
3. 與範圍與難度相近的歷史交付比（同 repo、相近改動量），不拿整週加總比。盤點 session 與整合成本一起算。
4. 品質沒守住（escaped defect、驗收 OPEN 率上升）就不因 token 少判成功。
5. 評估額度體感前先問使用者該期間是否用了其他機器或 claude.ai（本機 jsonl 量不到）。
