# extract.py 輸出 schema（`schema_version: 1`）

`scripts/extract.py` 把 Claude Code 的 session jsonl 正規化成單一 JSON 檔，`report.py` 只讀這個檔。本檔是欄位的 canonical 說明；jsonl 內部格式沒有官方穩定性承諾，extract 壞掉時先對照本檔與 `extract.py` 的 record 解析，再看 `caveats.md`。

## 輸入與命令列

讀 `<root>/<slug>/<sid>.jsonl`（主對話）與 `<root>/<slug>/<sid>/subagents/agent-<id>.jsonl`（subagent，旁邊的 `agent-<id>.meta.json` 是 metadata）。不讀 `tool-results/*.txt`，也不掃 `subagents/` 底下更深的子目錄。

```
extract.py [--root ~/.claude/projects] --since ISO [--until ISO] [--tz +08:00]
           [--project SUBSTR ...] [--exclude-session SID ...]
           [--pricing path] [--output-correction] --out data.json [--quiet]
```

- 窗口：事件時間 `since <= t < until`（`--until` 省略＝無上界）。檔案的 mtime 早於 `--since` 直接跳過（舊 session 可能被續寫，所以不以 mtime 過濾 `--until`）。`--since`／`--until` 帶 offset 的 ISO 照字面解讀，不帶 offset 的依 `--tz`（`+08:00`、`UTC` 或 IANA 名稱；省略＝系統本地時區）。
- `--project`：目錄名（slug）含任一 SUBSTR 才讀。`--exclude-session`：session id 以 SID 開頭的整組（含其 subagent）跳過。
- 完全沒有窗口內事件的 session 與 agent 不輸出。
- stdout 最後印摘要：sessions／agents／reqs 數、時間範圍、unpriced model 與 req 數、retyped 數、`cw_ttl_known=false` 的 req 數、cache 細分小於總額的 req 數。`--quiet` 不印。

時間欄位一律是 ISO 8601 UTC，毫秒精度，結尾 `Z`（字串可直接字典序排序）。報表層才轉顯示時區。slug、cwd、title 等原樣輸出，不做代號對照。

## 頂層

```
{ "schema_version": 1, "generated_at": iso, "generator": "usage-review/extract.py",
  "args": {...}, "sessions": {sid: session}, "agents": {agent_id: agent},
  "reqs": [req...], "unpriced": {model: req_count} }
```

`args`：`root`（照傳入字串）、`since`／`until`（正規化後的 UTC，`until` 可為 null）、`tz`（解析後的 offset，如 `+08:00`）、`project`、`exclude_session`、`pricing`（實際用的 pricing.json 路徑）、`output_correction`。

`unpriced`：對不上 pricing.json 任何條目的 model 與其 req 數；這些 req 的 `cost_raw` 是 `null`，絕不當成 0。

## session

| 欄位 | 說明 |
|---|---|
| `sid`、`slug`、`cwd`、`version`、`entrypoint` | 窗口內主對話事件上讀到的第一個 cwd；最後一個 version／entrypoint |
| `title` | 最後一筆 `custom-title`，沒有則最後一筆 `ai-title`，都沒有為 null |
| `worktree` | 最後一筆 `worktree-state` 的 worktree 名稱 |
| `first`、`last` | 窗口內主對話與 subagent 檔事件的最早／最晚時間 |
| `prs` | `pr-link` 記錄的 URL（排序、去重；不受窗口限制） |
| `humans` | `[{t, chars, kind}]`，不存全文。`chars` 是剝除 `<system-reminder>` 後的字元數。`kind`：`human`（真人輸入）、`peer`（其他 Claude session 傳來的訊息）、`command`（`<command-*>`／`<local-command*>`）、`ask_answer`（`AskUserQuestion`／`ExitPlanMode` 的回答，是真人回覆）、`compact`（續接摘要）、`notification`（`<task-notification>`，以及 harness 轉交的 `[Subagent hand-back]` 訊息）、`meta`（`isMeta` 記錄）。剝除後為空字串的記錄不輸出 |
| `agent_calls` | `{tool_use_id: agent_call}` |
| `edits` | `[{t, tool, path}]`，主對話的 `Edit`／`Write`／`MultiEdit`／`NotebookEdit` |
| `bash_writes_heuristic` | `[{t, head}]`，**啟發式**：`Bash` 指令符合「可能寫檔」的 regex（`sed -i`、`cat >`、`tee`、`perl -pi`、`git apply`、重導向到常見程式／設定副檔名等）。會有誤判與漏判，回報時要標示；`head` 是指令前 200 字 |
| `sends` | `[{t, to, chars}]`，`SendMessage` |
| `compact_boundaries` | `[t...]`，`compact_boundary` system 記錄 |

## agent_call（主對話的一次 `Agent`／`Task` 呼叫）

| 欄位 | 說明 |
|---|---|
| `t`、`subagent_type`、`model`、`effort`、`isolation`、`background`、`description` | 呼叫參數原樣（`background` 來自 `run_in_background`；沒帶為 null） |
| `prompt_chars`、`prompt_head` | prompt 長度與前 600 字 |
| `agent_id` | 啟動後的 agent id：優先 tool_result 旁的 `toolUseResult.agentId`，其次 result 文字裡的 `agentId: …`；仍沒有時由 `.meta.json` 的 `toolUseId` 或 notification 的 task-id 補 |
| `resolved_model` | `toolUseResult.resolvedModel`（harness 實際解析的 model；沒有為 null）。**延伸欄位** |
| `result` | `{t, is_error, chars, head}`（head＝前 300 字）或 null。非同步啟動時內容只是「已啟動」訊息，不是 agent 的報告 |
| `notification` | `{t, status, subagent_tokens, tool_uses, duration_ms}` 或 null。取該呼叫**最後一筆** task-notification（agent 被續用時它帶最新數字）；沒有 `<usage>` 的通知（例如 `killed`）三個數字是 null |
| `notification_count`、`first_notification_t` | 該呼叫收過幾筆不同的通知、第一筆的時間（算「在途」區間用最早完成時間）。**延伸欄位** |

同一則通知會同時出現在 `queue-operation`、`attachment`（`queued_command`）與 `user` 記錄，extract 依內容去重、取最早時間，不會算多筆。通知先以 `<tool-use-id>` 對到呼叫，沒有 tool-use-id 時用 `<task-id>`＝`agent_id` 對。

## agent（一個 subagent 檔）

| 欄位 | 說明 |
|---|---|
| `id`、`sid`、`slug` | `sid` 是父 session |
| `type` | 角色。判定順序：主對話 `Agent` 呼叫的 `subagent_type`（經 `meta.json.toolUseId` 或 `agent_id` 連結）→ `meta.json.agentType` → `"unknown"` |
| `meta_type`、`retyped` | `meta.json` 記的 `agentType`；`retyped` 為 true＝有 `meta_type` 且與 `type` 不同（agent 定義被刪後 meta 會被改記成 `general-purpose`） |
| `model_meta`、`description`、`tool_use_id` | `meta.json` 的 `model`、`description`（缺則取呼叫的）、`toolUseId`（缺則由 `agent_id` 反查） |
| `first`、`last`、`requests` | 窗口內事件最早／最晚時間；歸屬於它的 req 數 |
| `prompt_chars` | 第一則 user 訊息（派工 prompt）長度 |
| `final_chars`、`final_head` | 最終報告的長度與前 400 字：有 `SubagentHandback` 呼叫時取其 `message`，否則取最後一段非空 assistant 文字 |
| `handback` | 是否呼叫過 `SubagentHandback` |
| `tools` | `{工具名: 次數}`，依 tool_use id 去重；含 `SubagentHandback` 本身 |
| `tool_errors` | `is_error` 的 tool_result 數 |

## req（去重後的一次 API request）

| 欄位 | 說明 |
|---|---|
| `t`、`sid`、`agent`（agent id 或 null）、`role` | `role`：主對話為 `"main"`，subagent 為 `agents[agent].type` |
| `model`、`mid`、`rid` | `message.model`、`message.id`、`requestId` |
| `inp`、`cw`、`cr` | `input_tokens`、`cache_creation_input_tokens`（總額）、`cache_read_input_tokens` |
| `cw1h`、`cw5m`、`cw_ttl_known` | cache write 依 TTL 細分。有 `cache_creation` 細分時照實填且 `cw_ttl_known: true`；只有總額時整筆當 1h（`cw1h == cw`、`cw5m == 0`，是成本上界）且 `cw_ttl_known: false` |
| `out_raw`、`out_est` | jsonl 記的 `output_tokens`；`out_est` 只有 `--output-correction` 時才有（**啟發式**，規則在 pricing.json 的 `output_correction`），否則 null |
| `vis` | 該 message 可見 text 的字元數（Sonnet 補估用） |
| `cost_raw`、`cost_est` | USD。`cost_raw` 用 `out_raw`；`cost_est` 用 `out_est`（未開補估為 null）。model 對不上 pricing 時兩者都是 null |
| `tools` | 該 request 發出的 tool_use 名稱（依 id 去重） |
| `tool_result_chars` | 這些 tool_use 對應的 tool_result 文字字元總和（以 `tool_use_id` 配對，在後續 user 記錄裡） |

去重鍵 `(mid, rid)` 全域唯一（跨檔也是）。同鍵多筆時：`out_raw` 取最大值，其餘 usage 欄位取 `output_tokens` 最大那筆；`vis` 累加不同 uuid 的 text（同一筆記錄被複製進別的檔不重複加）。model 只看 `type:"assistant"` 的 `message.model`；`<synthetic>` 這類 harness 佔位記錄（usage 全 0）不算 request。

成本公式（每百萬 token 美元，數字在 `scripts/pricing.json`）：
`inp×input + cw5m×input×1.25 + cw1h×input×2 + cr×cache_read + out×output`。

## 啟發式欄位

下列欄位是啟發式，引用時要標示：`bash_writes_heuristic`、`out_est`／`cost_est`、`humans[].kind`（以文字前綴判斷）。之後由 `report.py` 以 regex 產生的分類（例如 verifier 判定）也要在欄位名帶 `_heuristic` 後綴。
