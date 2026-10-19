---
name: usage-review
description: 量 Claude Code 本機 session jsonl 的用量與派工行為時使用：成本按 subagent 角色×model 拆帳、cache write 1h／5m 與過期重寫、主對話 context 膨脹、subagent 回報長度、派工平行度與 controller 自修次數、verifier 判定分布。觸發詞：量用量、成本拆帳、subagent 成本、context 膨脹、cache 過期重寫、派工行為、"usage review"、"token cost by agent"、"cost breakdown by subagent"。這不是帳單，也算不出訂閱額度百分比。
allowed-tools: Bash(python3:*), Read, Grep, Glob
---

# Usage Review — 量多 agent 編排的成本與行為

把 `~/.claude/projects/<slug>/<sid>.jsonl`（主對話）與 `<slug>/<sid>/subagents/agent-*.jsonl`（subagent）正規化成單一 JSON，再用子命令出表。差異化只有一件事：**多 agent 編排制度花了多少、行為長怎樣**（誰花的、cache 有沒有過期重寫、context 多大、派工怎麼並行）。單純「花了多少」的總帳用既有的用量工具就好，本 skill 不重做。

兩層分工：`scripts/extract.py` 是**唯一**與 jsonl 內部格式耦合的地方；`scripts/report.py` 只讀 extract 的輸出，格式見 `references/schema.md`。純標準庫、不連網；只讀 jsonl 與 pricing.json，輸出只寫 `--out` 指定的檔。

## 何時用／不用

- 用：想知道一段期間的成本花在哪個角色、哪個 model、哪個專案、哪一天；懷疑 cache 過期重寫、context 膨脹、subagent 回報太長、派工沒有並行、主對話自己動手改檔；要比較制度改動前後（用 `--window` 切兩段）。
- 不用：要看帳單或剩餘額度（本機 jsonl 不是帳單，換算不出訂閱額度百分比）；要看其他裝置、claude.ai、手機的用量（不在本機）；要的是即時的當前 session 狀態（用官方 `/usage`）。

## 流程（兩步）

`<SK>` 指本 skill 的目錄（安裝後通常是 `~/.claude/skills/usage-review`）。

```bash
# 1. 正規化（窗口以事件時間為界；--since 不帶 offset 時依 --tz 解讀，省略 --tz＝系統本地時區）
python3 <SK>/scripts/extract.py --since 2026-10-01T00:00 --tz +08:00 --out "$TMPDIR/ur-data.json"

# 2. 出表（預設 markdown 表印到 stdout；--format json 給機器）
python3 <SK>/scripts/report.py cost --data "$TMPDIR/ur-data.json"
python3 <SK>/scripts/report.py cache --data "$TMPDIR/ur-data.json" --project my-proj
python3 <SK>/scripts/report.py dispatch --data "$TMPDIR/ur-data.json" \
  --window before=2026-10-01T00:00..2026-10-08T00:00 --window after=2026-10-08T00:00..
```

- extract 結尾會印摘要：sessions／agents／reqs 數、時間範圍、**unpriced model**、retyped 數、`cw_ttl_known=false` 的 req 數。先看摘要再出表；unpriced 不為空代表 `pricing.json` 缺那個 model 的價格，總額偏低（缺的 model 成本是 `null`，不會當 0）。
- 價格表在 `scripts/pricing.json`（每條有 `verified` 日期，是本地快照）；換價格或加 model 用 `extract.py --pricing <path>` 重跑，不改程式。
- 共用旗標：`--data`（必填）、`--tz`、`--window NAME=ISO..ISO`（可重複，任一端可空、省略＝全部）、`--project SUBSTR`、`--exclude-session SID`、`--corrected`、`--format md|json`、`--top N`。
- `data.json` 內含 prompt 與報告前段、cwd、session 標題與專案目錄名，**分享前先檢查**；要分享報表時只貼 `report.py` 的輸出並自行去識別化。

## 子命令

| 子命令 | 量什麼 | 注意 |
|---|---|---|
| `cost` | 總額；角色×model family；model；專案目錄；每日（顯示時區日曆日）；cache read／write 1h／write 5m／input／output 占比；unpriced | `--corrected` 時 raw 與 est 並列 |
| `cache` | 連續 request 間隔分布；過期重寫次數與 cache write 費用；1h／5m 細分與 TTL 未知占比 | 過期重寫為啟發式 |
| `context` | 主對話 ctx 中位／P90／分桶／>400K 占比；subagent 首個 request 的 ctx（固定注入量代理）；compact 次數 | |
| `reports` | subagent 最終報告長度（依 type）與 handback 比率；Agent tool_result 長度 | tool_result 常只是啟動說明，以 `final_chars` 為準 |
| `dispatch` | Agent 呼叫的參數組合；錯誤數；notification status；平行度（連通的在途區間） | 在途區間是近似值 |
| `controller` | 主對話 Edit／Write 與 Bash 寫檔 vs 派工數（逐專案目錄）；worker 交回後到下一個 verifier 派出前的改檔次數 | Bash 寫檔與「交回後」皆為啟發式 |
| `verifier` | verifier 判定分布與各自成本 | 判定由 `final_head` 的 regex 抓，為啟發式 |
| `agents` | 每種 subagent 的 request 數、工具數、牆鐘、成本（中位／P90）、通知 token 中位 | |
| `sessions` | 最貴前 N 個 session（含 subagent 成本）、ctx 中位、派工數、人類訊息數 | 人類訊息只算 `human`＋`ask_answer` |

歸屬規則：request 級表格（cost、cache、context）用 request 時間；agent 級表格（reports、agents、verifier）用 subagent 的開始時間並計入它全部的 request，不會被窗口切成兩半；dispatch、controller 用 Agent 呼叫、改檔的時間。

## 窗口怎麼切

- 窗口以事件時間為界。窗口終點附近還在跑的 subagent 只有一半在窗口內；比較前後兩段時，切點選在**沒有在途 subagent** 的時間，或接受邊界誤差並在報告註明。
- 比較制度改動前後，用同一份 data 的兩個 `--window`，不要分兩次 extract（兩次之間 jsonl 可能又被寫入，口徑會不一致）。
- 本機 jsonl 預設只留 30 天（`cleanupPeriodDays`，官方預設值）；窗口早於保留期的部分沒有資料。

## 解讀邊界（回報時必須帶）

完整陷阱清單在 `references/caveats.md`，下面幾條會直接改變結論，回報時要寫進去：

1. **口徑**：預設只報 raw（jsonl 記的 output）。jsonl 只記串流開頭的 usage，部分 model 的 output 被少記；`--corrected` 是本機校準的**啟發式**（`pricing.json` 的 `output_correction`），**一定要和 raw 並列**，不能單獨當事實。
2. **啟發式欄位要標示**：`bash_writes_heuristic`、`edits_after_worker_heuristic`、`verdict_heuristic`、`out_est`／`cost_est`、`humans[].kind`、過期重寫與平行度。回報這些數字時註明是啟發式，重要結論抽樣回頭核對原文。
3. **本機 ≠ 全部**：其他裝置、claude.ai、手機的 session 不在本機；本機總額不是帳單，advisor 的用量不在 request 的 token 欄位裡（總額是下限）。
4. **cache write 的 TTL**：沒有 1h／5m 細分的 request 整筆當 1h（成本上界），`cw_ttl_unknown_reqs` 不為 0 時總額偏高。
5. **角色以主對話 `Agent` 呼叫的 `subagent_type` 為準**（agent 定義被刪後 meta 會被改寫，`retyped` 欄位標出）。型別來源都對不上的 subagent 角色是 `unknown`。
6. **量到的是這段期間這台機器**：用量絕對值不能跨機器、跨期間直接比，比相對占比與前後變化。

jsonl 是 Claude Code 的內部紀錄檔。官方 sessions 文件明寫：「The entry format is internal to Claude Code and changes between versions, so scripts that parse these files directly can break on any release」（記錄格式屬 Claude Code 內部、隨版本改變，直接解析的腳本任何版本都可能壞掉），並建議改用 `/export` 或 script interfaces；本 skill 仍直接解析 jsonl，所以視為**沒有穩定性保證**，並把這份耦合限制在 `extract.py` 一處。extract 在新版本壞掉或數字突然對不上時：先對照 `references/schema.md` 與 `scripts/extract.py` 的 record 解析（user／assistant／attachment 各種記錄的欄位名），再看 `references/caveats.md`；report 層不需要改，因為它只認 schema。

## 與官方機制的關係

依 code.claude.com 的 costs、monitoring-usage、claude-directory 文件（2026-10-12 讀取，版本更新後重新核對）：

- 官方 `/usage`（別名 `/cost`、`/stats`）看當前 session 的 token 用量與以定價估算的金額；訂閱方案另顯示近期用量的歸因百分比（skills、subagents、plugins、MCP 各占幾 %）。文件描述的是當前 session 區塊與近期歸因（CLI 的 `/usage` 按 `d`／`w` 在最近 24 小時與 7 天之間切換；VS Code 的 Account & usage 對話框有 Day／Week 切換，沒有 Loops 列），沒有描述任意窗口或 request 明細。本 skill 補的是跨 session 的任意窗口、subagent 角色×model 的**金額**拆帳、cache 1h／5m 與過期重寫、context 分布、派工平行度與 controller 行為。
- OpenTelemetry 的 cost counter 與 `api_request` 事件帶 `agent.name`（發出 request 的 subagent 類型），可以**往後**取代 extract 的角色拆帳；`query_source` 屬性在兩處的值不同：cost／token counter 上是粗分類 `main`／`subagent`／`auxiliary`，`api_request` 事件上是 `repl_main_thread`、`compact` 或 subagent 名；限制：從開啟遙測之後才有資料、不回溯；自訂 agent 名預設會被改成 `custom`，要設 `OTEL_LOG_TOOL_DETAILS=1` 才帶真名；文件列出的 token 欄位是 `cache_read_tokens`／`cache_creation_tokens`，沒有 1h／5m 細分。
- 官方 `cleanupPeriodDays` 決定本機 jsonl 留多久（預設 30 天），超過會被刪。

## 未納入（需要時另做）

- **lead time、每 PR 成本**：要用 `gh` 把 session 與 PR 配對，本 skill 只存 `sessions[].prs`（`pr-link` 記錄）。
- **品質人工改判**：verifier 判定、finding 是否成立需要人看原文，工具只給 regex 分布。
- **polling 浪費**（背景工作期間反覆輪詢）：判定規則與環境相關，未做成通用子命令。
- **advisor 用量展開**：`usage.iterations[]` 的 `advisor_message` 不展開，見 caveats。
- **`tool-results/*.txt`**：工具輸出快取，不是事件，一律不讀。

## 檔案

- `scripts/extract.py`、`scripts/usagelib.py`、`scripts/pricing.json`：正規化、共用函式、價格表。
- `scripts/report.py`：九個子命令。
- `references/schema.md`：extract 輸出的欄位定義（canonical）。
- `references/caveats.md`：量 jsonl 的已知陷阱（現象 → 影響 → 處理）。
