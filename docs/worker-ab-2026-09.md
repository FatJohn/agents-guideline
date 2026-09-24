# worker A/B 對照：Sonnet xhigh vs Opus 5.5 medium（2026-09）

## 目的

評估是否把 Claude 端標準執行者從 `worker`（Sonnet/xhigh）換成 Opus 5.5/medium。
先不改預設，新增實驗車道 `../agents/worker-opus.md`（合約與 `worker` 相同，只換 model／effort），
用 A/B 對照累積數據，數據支持再由使用者決定是否改預設或直接刪除實驗車道。

## 背景數據（來源：2026-09-21 session review，存在主力 Mac 的 auto-memory `~/.claude/projects/-Users-fatjohn-Projects-FatJohn-agents-guideline/memory/session-review-2026-09-21.md`，不在 repo 內）

- `worker`（Sonnet/xhigh）中位 90 次工具呼叫、16.1 分鐘。
- 每 request 秒數：worker/sonnet 14.1 秒，verifier/opus 21.6 秒（general-purpose/opus 20.5 秒）。
- Opus 實作 agent（非本車道，既有樣本）n=7，69 次工具呼叫、22.9 分鐘——**有選樣偏差**，
  這批任務不是刻意配對的 A/B 樣本。
- 初步判讀：慢的主因是步數 × 冷啟動，不是單步本身變慢；因此本次對照的重點量測放在
  「總工具呼叫數」與「總牆鐘時間」，不是單步秒數。

## 分派方式

- 同一波規模相近的切片交替派 `worker` 與 `worker-opus`，不要把明顯較難或較模糊的切片
  刻意分給 `worker-opus`（否則污染對照）。
- 不強制每波都要對照——沒有規模相近的可比切片時，正常派 `worker`，不要為了湊樣本硬切。
- 不和 workflow 試跑放同一波（workflow 本身的變異會混進車道差異）。

## 量測四項

| 項目 | 說明 | 資料來源 |
|---|---|---|
| `tool_uses` | 該次派工的工具呼叫總數 | 完成通知 `<usage>` 或對應 session jsonl |
| `duration_ms` | 該次派工的牆鐘時間 | 完成通知 `<usage>` 或對應 session jsonl |
| verifier 首輪 OPEN 率 | 該產出交 fresh verifier 後首輪判定是否為 OPEN（非 CONVERGED） | verifier 回報 |
| `subagent_tokens` | 該次派工消耗的 token 數，作 fresh 訊號輔助判讀 | 完成通知 `<usage>` 或對應 session jsonl |

兩車道可用 agent 類型名（`worker` vs `worker-opus`）在 session jsonl 或完成通知中區分。

## 樣本標記

每筆紀錄要標「起點」：
- **從零**：worker 收到任務時是全新 plan，沒有人先做過一部分。
- **接續**：worker 接手一個已經做到一半的任務（例如前一輪修正的 delta）。

兩類不可混算平均——接續的任務通常步數與時間都比較短，會低估真正的冷啟動成本。

## 切換門檻（2026-09-23：使用者確認速度與品質兩者都是衡量標準；樣本數 N 待定）

同時滿足才考慮把預設從 `worker` 換成 Opus 5.5/medium：
1. `worker-opus` 車道的牆鐘中位時間**不高於** `worker` 車道；
2. `worker-opus` 車道的 verifier 首輪 OPEN 率**明顯低於** `worker` 車道；
3. 兩車道樣本數各至少 N 個（N 待定——目前無法給出統計上有意義的下限，待累積初步數據後由使用者拍板）。

任一項不滿足就維持現狀（`worker` 為預設），`worker-opus` 繼續累積樣本或由使用者決定收斂。

## 結束後的處理

實驗結束（達門檻或使用者判斷數據已足夠下結論）後兩種結果：
- 維持現狀：刪除 `../agents/worker-opus.md` 與本檔（或標記歸檔）。
- 改預設：把 `worker.md` 的 model／effort 改成 Opus 5.5/medium，`../rules/10-dispatch.md` §0
  與「執行者預設」段同步更新，再刪除 `worker-opus.md`。

這屬於修改既有判準（`rules/10-dispatch.md` 的預設路由），**要使用者明確同意**才能動手，
worker／worker-opus 執行者本身不得自行決定切換預設。

## 紀錄表格

> 2026-09-23：prompt audit 同一個 commit 同步修改 `worker.md`／`worker-opus.md` 的合約（刪「不要再呼叫 Agent 工具轉包」、回報上限改為以 controller 下一步所需為準），兩車道合約仍只差 model／effort；此前無樣本。

| 日期 | 專案 | 切片 | 車道 | 起點（從零/接續） | tool_uses | duration | subagent_tokens | 首輪 verifier 狀態 | 備註 |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-24 | KKBOX-Slim | #26-39 補測試（2 個新測試檔，生產碼 0） | worker-opus | 從零 | 45 | 472556 | 127487 | PROSE-ONLY | 規模較 110／74 小（純測試），可比性有限；第 2 輪同 worker 續用：29 次／256083 ms／149366 |
| 2026-09-24 | KKBOX-Slim | #26-110 lint-check.sh 兩個死角＋接縫 | worker | 從零 | 74 | 1241690 | 181179 | PROSE-ONLY | 基線凍結順序違規（先改後凍結，verifier 重建基線）；第 2 輪 fresh worker：24 次／309s／79190 |
| 2026-09-24 | KKBOX-Slim | #26-74 淘汰 pin 競態（2 個 src＋測試＋docs） | worker | 從零 | 98 | 1595210 | 282914 | OPEN | 3 個測試破口；第 2 輪 fresh worker：35 次／385823 ms／134293 |
| 2026-09-24 | KKBOX-Slim | #26-118 saver rename Windows 重試（1 個 src＋新測試檔＋docs） | worker | 從零 | 69 | 841274 | 202093 | OPEN | 2 個測試破口＋1 句註解失準；第 2 輪 fresh worker（同 worktree 接手）：33 次／341837 ms／106140；controller 另自修 3 處 Task.Run 與錯字 |
| 2026-09-24 | KKBOX-Slim | #26-119 11 個測試檔 Task.Run→專屬執行緒（生產碼 0） | worker-opus | 從零 | 52 | 1023622 | 123918 | CONVERGED | 機械改寫，較 118 簡單，可比性有限；duration 含 base／修正版各 10 輪全套重現對照（約 9 分鐘） |
