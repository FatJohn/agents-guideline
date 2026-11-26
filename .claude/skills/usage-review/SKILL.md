---
name: usage-review
description: 量 Claude Code 本機 session jsonl 的用量與派工行為時使用：成本按 subagent 角色×model 拆帳、cache write 1h／5m 與過期重寫、主對話 context 膨脹、subagent 回報長度、派工平行度與 controller 自修次數、verifier 判定分布、每週規則效果（$/PR、首輪 OPEN、接手門檻模擬）。Use for usage or token-cost reviews by agent.這不是帳單，也算不出訂閱額度百分比。
allowed-tools: Bash(python3:*), Read, Grep, Glob
---

# Usage Review — 量多 agent 編排的成本與行為

把 `~/.claude/projects/<slug>/<sid>.jsonl`（主對話）與 `<slug>/<sid>/subagents/agent-*.jsonl`（subagent）正規化成單一 JSON，再用子命令出表。差異化只有一件事：**多 agent 編排制度花了多少、行為長怎樣**（誰花的、cache 有沒有過期重寫、context 多大、派工怎麼並行）。單純「花了多少」的總帳用既有的用量工具就好，本 skill 不重做。

兩層分工：`scripts/extract.py` 是**唯一**與 jsonl 內部格式耦合的地方；`scripts/report.py` 只讀 extract 的輸出，格式見 `references/schema.md`。純標準庫、不連網；只讀 jsonl 與 pricing.json，輸出只寫 `--out` 指定的檔。

## 何時用／不用

- 用：想知道一段期間的成本花在哪個角色、哪個 model、哪個專案、哪一天；懷疑 cache 過期重寫、context 膨脹、subagent 回報太長、派工沒有並行、主對話自己動手改檔；要比較制度改動前後（用 `--window` 切兩段）。
- 不用：要看帳單或剩餘額度（本機 jsonl 不是帳單，換算不出訂閱額度百分比）；要看其他裝置、claude.ai、手機的用量（不在本機）；要的是即時的當前 session 狀態（用官方 `/usage`）。

## 流程（兩步）

`<SK>` 指本 skill 的目錄（`<REPO>/.claude/skills/usage-review`，在本 repo 開工時由專案層載入，不裝進全域）。

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
- 共用旗標：`--data`（必填）、`--tz`、`--window NAME=ISO..ISO`（可重複，任一端可空、省略＝全部）、`--project SUBSTR`、`--exclude-project SUBSTR`（排除 slug 含 SUBSTR 的 session，例如測試 session）、`--exclude-session SID`、`--corrected`、`--format md|json`、`--top N`。
- `data.json` 內含 prompt 與報告前段、cwd、session 標題與專案目錄名，**分享前先檢查**；要分享報表時只貼 `report.py` 的輸出並自行去識別化。

## 子命令

| 子命令 | 量什麼 | 注意 |
|---|---|---|
| `cost` | 總額；角色×model family；model；專案目錄；每日（顯示時區日曆日）；cache read／write 1h／write 5m／input／output 占比；unpriced | `--corrected` 時 raw 與 est 並列 |
| `cache` | 連續 request 間隔分布；過期重寫次數與 cache write 費用；1h／5m 細分與 TTL 未知占比 | 過期重寫為啟發式 |
| `context` | 主對話 ctx 中位／P90／分桶／>400K 占比；subagent 首個 request 的 ctx（固定注入量代理）；compact 次數 | |
| `reports` | subagent 最終報告長度（依 type）與 handback 比率；Agent tool_result 長度 | tool_result 常只是啟動說明，以 `final_chars` 為準 |
| `dispatch` | Agent 呼叫的參數組合；錯誤數；notification status；平行度（連通的在途區間） | 在途區間是近似值 |
| `controller` | 主對話 Edit／Write 與 Bash 寫檔 vs 派工數（逐專案目錄）；worker 交回後到下一個 verifier 派出前的改檔次數（只有含 worker 派工的 session 才有值） | Bash 寫檔與「交回後」皆為啟發式 |
| `verifier` | verifier 判定分布與各自成本 | 判定由 `final_head` 的 regex 抓，為啟發式 |
| `agents` | 每種 subagent 的 request 數、工具數、牆鐘、成本（中位／P90）、通知 token 中位 | |
| `sessions` | 最貴前 N 個 session（含 subagent 成本）、ctx 中位、派工數、人類訊息數 | 人類訊息只算 `human`＋`ask_answer` |
| `weekly` | 每週規則效果：$/PR、PR/h、$/h、token／request／Agent 呼叫每 PR、主對話與 subagent 每 PR；主對話 ctx 對門檻（跨過的 session、這些 session 裡 ctx ≥ 門檻的 request 數中位、≥門檻占主對話成本）；verifier 判定、首輪 OPEN、機械結案後又派 delta；verifier 與 fresh review 按 model 的每次成本與每 session 輪數；接手門檻模擬 | 專屬旗標 `--prs`、`--ctx-threshold`、`--sim-threshold`；判定、首輪、review 分類、fork 歸屬是啟發式，模擬是粗估 |
| `escapes` | 漏網：窗口內 merge 的原 PR，有多少在 N 天內被引用它的 fix／revert PR 改到同一批檔；比率（全部與已滿 N 天的 mature 兩種）、依 merge 前 fresh 驗收涵蓋（verifier／code-review／none／unknown）分組、逐筆清單與留給人填的 `should_catch` 欄 | 專屬旗標 `--prs`（必填）、`--fix-days`、`--as-of`、`--author`；性質判定、引用、涵蓋都是啟發式，命中要人工判 |

歸屬規則：request 級表格（cost、cache、context）用 request 時間；agent 級表格（reports、agents、verifier）用 subagent 的開始時間並計入它全部的 request，不會被窗口切成兩半；dispatch、controller 用 Agent 呼叫、改檔的時間。`weekly` 各表分別照這三種：成本與 context 用 request 時間，verifier 輪次用 subagent 開始時間，review 每次成本用 Agent 呼叫時間。`escapes` 用原 PR 的 merge 時間。

## 每週規則效果（`weekly`）

```bash
gh search prs --author=@me --merged --merged-at ">=2026-11-02" --limit 1000 --json repository,number,closedAt > "$TMPDIR/prs.json"
python3 <SK>/scripts/report.py weekly --data "$TMPDIR/ur-data.json" --prs "$TMPDIR/prs.json" --tz +08:00 \
  --window before=2026-11-03T00:00..2026-11-10T00:00 --window after=2026-11-10T00:00..2026-11-18T13:20
```

- `--prs` 吃 JSON 物件陣列，每筆用 `mergedAt`，沒有時用 `closedAt`（`gh search prs --merged` 的 closedAt 就是 merge 時間）；不給時 PR 相關欄位為空。`--project` 等篩選不會套到 PR 清單上，篩專案時 PR 清單要自己給同範圍。活躍小時＝窗口內全部 request 的 10 分鐘 bucket 數 ÷ 6。
- 內建 `code-review` skill 通常會再 fork 沒有 Agent 呼叫的 general-purpose 子 agent（偶爾不只一個，description 是 `/code-review …` 或空白）；`weekly` 的 review 表把它併回 fork 當下還在跑的父呼叫（主對話直接打 `/code-review` 的 fork 沒有父呼叫，不併），`agents` 子命令仍算成獨立 agent（按 agent 數看 review 會變兩倍）。
- 接手門檻模擬是粗估：每個 session 只換手一次、不算新 session 重讀檔案，方向相反，不是嚴格上界。要用接手規則上線前的窗口：規則生效後跨過較高門檻的 session 被截斷，模擬出來接近 0。
- 300K 提醒的觸發、接手 session 的啟動、brief 前 600 字（`prompt_head`）之後的字串（例如宣稱對照）需要讀 raw jsonl，不在 extract 的輸出裡，`weekly` 不量。
- **報告格式**：週量測報告一律照 `references/report-format.md` 的骨架寫：開頭是計分卡（每個指標判 🟢 變好／🔴 變壞／⚪ 持平／🟡 待觀察）與規則表，接著每個 🔴 一列 finding（根因、證據、落點、下次的判定門檻），之後才是結論、窗口與量法、逐題數字。動筆前先讀那份檔。

## 漏網（`escapes`）

驗收與 review 放過了什麼：窗口內 merge 的原 PR，N 天內（`--fix-days`，預設 14）有沒有同 repo 的後續 PR 同時符合四件事：與原 PR 共用至少一個檔、標題或描述引用原 PR（`#N`、`owner/repo#N` 或 PR 網址）、性質判為 fix 或 revert、merge 在原 PR 之後。後續 PR 作者不限；原 PR 用 `--author` 限定成自己的。

```bash
# 1. extract 的起點要比窗口早（PR merge 前的驗收派工要在資料裡），窗口終點要早於現在 N 天
python3 <SK>/scripts/extract.py --since 2026-10-24T00:00 --tz +08:00 --out "$TMPDIR/ur-data.json"
# 2. 本機 session 連過的 repo，逐 repo 抓已 merge PR（從窗口起點的前一天抓到現在，免得時區差切掉窗口開頭）
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("\n".join(sorted({"/".join(u.split("/")[3:5]) for s in d["sessions"].values() for u in s["prs"]})))' "$TMPDIR/ur-data.json" > "$TMPDIR/repos.txt"
mkdir -p "$TMPDIR/esc-prs"
while read -r r; do gh pr list -R "$r" --state merged --search "merged:>=2026-10-26" --limit 1000 \
  --json number,title,body,mergedAt,url,headRefName,author,files > "$TMPDIR/esc-prs/${r//\//__}.json" \
  || { echo "FAIL $r"; rm -f "$TMPDIR/esc-prs/${r//\//__}.json"; }; done < "$TMPDIR/repos.txt"
python3 -c 'import json,sys; print(json.dumps([p for f in sys.argv[1:] for p in json.load(open(f))]))' "$TMPDIR"/esc-prs/*.json > "$TMPDIR/esc-prs.json"
# 3. 出表
python3 <SK>/scripts/report.py escapes --data "$TMPDIR/ur-data.json" --prs "$TMPDIR/esc-prs.json" --tz +08:00 \
  --author "$(gh api user -q .login)" --window w=2026-10-27T00:00..2026-11-07T00:00
```

- 用 `gh pr list -R`，不用 `gh search prs`：後者沒有 `files`、`headRefName`。不要加 `commits` 欄位，`--limit 1000` 時 GraphQL 會超過 500,000 節點上限被拒。某個 repo 回 `HTTP 502` 時，把 `merged:` 拆成幾段日期範圍（`merged:2026-10-27..2026-11-03`）分次抓再合併；重疊抓到的同一個 PR 只算一次。失敗的 repo 會印 `FAIL` 並刪掉空檔，合併前先補抓。某個 repo 剛好回 1,000 筆時可能被 `--limit` 截斷，同樣拆日期範圍。
- `files` 看起來每個 PR 最多回 100 個檔（2026-11-21 抓的 1,123 個 PR 裡最大值是 100，有 9 個剛好 100），超過的 PR 共用檔會漏算；`files` 是 null 的原 PR 算進 `no_file_list`（仍在分母），落在某個原 PR 期限內的這類後續候選算進 `followups_no_file_list`，兩者都不參與配對。
- `--as-of` 是 PR 清單的抓取時間（預設現在）；merge 後還沒滿 N 天的原 PR 標 `censored`，比率看 `mature_with_fix_share`。窗口內沒有原 PR、清單沒有 `body` 欄位、或沒有任何 PR 帶 `files` 時，`status` 寫「無法計算」，比率是空的，不印 0%。
- `by_coverage` 是對照組：沒被修的原 PR 也按驗收涵蓋分組，比較各組的 `with_fix_share`。涵蓋只從 session 的 `pr-link` 推，判法與限制見 `references/caveats.md`「E. 漏網指標」。
- 命中清單的 `should_catch` 留空給人填（該由 verifier、code-review、測試、CI 抓到，或事前抓不到）。

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

- **lead time、單一 PR 的成本**：要用 `gh` 把 session 與 PR 配對，本 skill 只存 `sessions[].prs`（`pr-link` 記錄）；窗口層級的 $/PR 由 `weekly --prs` 提供，merge 後被修的比率由 `escapes --prs` 提供。
- **品質人工改判**：verifier 判定、finding 是否成立需要人看原文，工具只給 regex 分布。
- **polling 浪費**（背景工作期間反覆輪詢）：判定規則與環境相關，未做成通用子命令。
- **advisor 用量展開**：`usage.iterations[]` 的 `advisor_message` 不展開，見 caveats。
- **`tool-results/*.txt`**：工具輸出快取，不是事件，一律不讀。

## 檔案

- `scripts/extract.py`、`scripts/usagelib.py`、`scripts/pricing.json`：正規化、共用函式、價格表。
- `scripts/report.py`：十一個子命令。
- `references/schema.md`：extract 輸出的欄位定義（canonical）。
- `references/caveats.md`：量 jsonl 的已知陷阱（現象 → 影響 → 處理）。
- `references/report-format.md`：週量測報告的固定骨架、判定規則與範例。
