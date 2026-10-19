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

## 首次量測（2026-10-09）

> 承接上節「試行與判定方法」，是「一個 issue 一個頂層 session」試行後的第一次量測，供之後評估有基線可比。標記：**已驗證**＝有數字；**推論**＝由數字推出、未單獨驗證。

### 窗口與口徑

- 已驗證：前＝2026-10-05 19:00～10-07 23:00（52.0h，同「改規則時的量測」基線，重算得 $1,638）；後＝10-07 23:00～10-09 07:51（32.9h）；穩態＝10-08 12:25 起（第一個盤點 session 開始，19.4h）。
- 金額口徑同「改規則時的量測」：API 牌價等價、usage 去重，不含 advisor。
- 使用者在對話中回報（非量測）：週額度 52%→70–80%，期間另有用 claude.ai／手機，本機 jsonl 量不到。

### 成本

- 已驗證（機制生效）：主對話 context 中位 255K→200K、P90 534K→296K；>400K request 占比 22.6%→0%；cache_read 占主對話費用 68%→62%。
- 已驗證（每活動小時）：$／活動小時 38.1→33.0（後全部），穩態 41.4。平均同時開的 session 3.7→4.0（穩態 4.7）；單一 session $／活動小時 10.5→8.5。後全部較低主要因 10-07 23:00～10-08 12:25 使用強度低（$18.4／活動小時）。
- 已驗證（每 merged PR）：$19.5（n=84）→$30.5（n=27），兩窗口 PR 組成差異大，只看方向。曾試過「只算 session 有 pr-link 的 PR」口徑（$32.8→$39.2），後查前窗口 34 個無 pr-link 的 PR 中 33 個在本機 session 有 `gh pr create` 輸出，是 pr-link 記錄不全，該口徑作廢。
- 已驗證（占比）：主對話占比 45.6%→45.7%；Opus 占比 82.4%→82.5%；worker-opus 占比 11.0%→14.6%。
- 已驗證（新模式特有成本）：3 個盤點 session 合計 $47.4（後窗口 6%）；issue session 開場第一個 request 約 70–80K context，第一次派工前主對話成本中位 $2.47；13 個 session 逐筆占該 session 成本中位 5.9%（範圍 1.5–35.5%），合計 7.2%。
- advisor（Fable）不在本機 usage 計算內；以 CLI cost-state 估兩窗口都約占 cost-state 總額 38%（約等於本機計算金額的 50%）。是否計入週額度：未驗證。

### 單一 issue 牆鐘

以主 PR 為單位；「淨」＝扣掉 session 閒置超過 10 分鐘；數字為中位／P75，單位小時。

- 已驗證（開工→開 PR 淨）：舊模式多 issue controller 0.9／1.9（n=55）→ issue session 1.0／2.0（n=13），p≈0.97；小／中／大三組各自也持平。
- 已驗證（開工→merge 牆鐘）：1.9／3.0 → 2.1／2.9。
- 已驗證（含排隊，T0 取第一次被提到，淨值）：開工→開 PR 中位 1.8→1.9、P75 3.8→2.8；整體分佈差異 p≈0.3–0.7，不顯著。開工→merge 的淨值不能跨模式比（issue session 開 PR 後閒置被扣掉），不列。
- 已驗證（排隊本身，牆鐘）：舊模式（第一次被提到→第一次派 worker 實作）中位 1.2h、P75 2.9h，其中約一半是等使用者；扣掉等使用者後，至少 54% 的時間 controller 在跑別題。新模式（盤點 session 提到→issue session 開工）牆鐘 0.5／2.4h（扣閒置後 0.3／1.0h）。
- 已驗證：後窗口另有 6 題未經盤點、直接單開一個 session，按改動大小分組後速度與 issue session 相近（未分組時開工→開 PR 淨中位 1.7h，樣本只有 6）。
- 推論：效果來自「一題一 session」，不是盤點 session（依上一點）。
- 推論：使用者體感變快來自排隊縮短，單題實作工時沒變（依開工→開 PR 淨時間持平）。

### 品質

- 已驗證：首輪 verifier OPEN 率 49%（36/74）→48%（14/29）；delta OPEN 率 19%（6/31）→42%（5/12），Fisher p≈0.24，不顯著；同一產出驗到第 3 輪 6 條→2 條（窗口長度 52h 對 33h，不能直接比）。
- 已驗證：後窗口發現的交付後缺陷 1 件，來自改規則前舊模式的交付。

### 限制

- 後窗口樣本小：13 個 issue session，集中在 10-08 下午到深夜。
- 兩窗口專案組成與難度不同，作息也不同。
- 本機 jsonl 量不到 claude.ai 與其他機器的用量。

### 判定

依「試行與判定方法」：

- 品質：沒有可判定的變差（樣本小）；delta OPEN 率待累積樣本再比。
- token：未證實節省。單 session 便宜，但同時 session 變多；每日總額持平、穩態每活動小時略升、每 PR 未降。
- 收益：排隊長尾方向縮短（含排隊開 PR 的 P75 3.8→2.8、排隊牆鐘 P75 2.9→2.4），但不顯著，待樣本累積；單題實作工時不變（推論，依淨時間 p≈0.97）。
- 結論：保留一題一 session（品質未見變差、排隊方向改善）。本檔開頭「節省」的假設目前不成立；「以 token 換等待時間」是待驗證的替代假設（開頭原文不改）。
- 下次評估：issue session 累積到 30 個以上再比 delta OPEN 率；查清 advisor 是否計入週額度。
