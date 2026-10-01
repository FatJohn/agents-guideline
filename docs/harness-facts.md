# 查證過的 harness 事實

> 2026-08-22 從 `rules/00-environment.md` 搬出。理由：這些是**派工當下**才用得到的 Agent 工具事實，
> 而 `rules/` 是每個 session 全文載入的常駐區（`maintain-guideline` §5「只在特定情境才用得到的
> 內容不該放 rules/」）。`rules/10-dispatch.md` §0 已經指向這裡。搬入時原文未改寫，之後的更正見各條內文。
>
> **查證日：2026-08-06。版本更新後重新核對**——這些值會隨 Claude Code／Codex 改版漂移，
> 要宣稱某個參數存在時以當場現查的工具 schema 為準，不引用本檔。

- Agent 呼叫可逐次指定 model；effort 仍由 agent 定義 frontmatter 或 session/workflow 設定控制。
- 主對話（controller）的 model 由 UI 選擇，effort 由 `~/.claude/settings.json` 的 `effortLevel` 設定（2026-07-25 核對為 `xhigh`；2026-09-07 複查仍為 `xhigh`，另有 `modelSettings.claude-fable-5-1.effortLevel: high` 的逐型號覆寫）。**subagent 不指定 `model`、且 agent 定義 frontmatter 也沒寫 `model` 時，繼承主對話的模型**，所以 `../rules/10-dispatch.md` 各表的 model 欄是顯式 routing 指示，派 `worker`／`verifier` 一律要寫 `model:`（worker 已改，見本條末句）。**更正（2026-09-23 實測）**：agent 定義 frontmatter 有寫 `model` 時，不帶參數用的是 frontmatter 的型號、不繼承主對話——`claude -p --model sonnet` 主對話（claude-sonnet-5）不帶 `model` 派 `worker-opus`，subagent transcript 記錄 `claude-opus-5-5`；「繼承主對話」只適用於 frontmatter 沒寫 `model` 的 agent。派 `verifier` 仍照舊顯式寫 `model:`；`worker`（型號與 effort 由其 frontmatter 決定）與 `worker-opus` 見 `../rules/10-dispatch.md` §0。（2026-09-07 從 `rules/10-dispatch.md` §0 搬入；原「Max 檔位實作預設 opus、Pro 檔位降回 sonnet」的分檔位規則已由不分檔位的 `worker`（型號由其 frontmatter 決定）取代，刻意放棄。）
- Agent frontmatter 的 `effort` 可填 `low`／`medium`／`high`／`xhigh`／`max`，也可由 session／workflow 控制；實際可用值仍受模型與組織限制。（2026-09-30 併入原 `rules/10-dispatch.md` §0 的「也可由 session／workflow 控制」；原文未改寫。）
- `claude-code-guide`——回答 Claude Code / API 本身的問題。不是每個 session 都有（`claude -p` 起的 session 曾缺它，機制未查明），以當下 Agent 工具列出的類型為準。（2026-09-30 從 `rules/10-dispatch.md` §0 搬入；原文未改寫。）
- 新增 `~/.claude/agents/*.md` 後，已在執行中的 session 不必重開：新增當輪派該名字會回 `Agent type ... not found`，下一個使用者輪次 harness 注入「New agent types are now available」後即可派（2026-09-23 實測，`worker-opus`，n=1）。
- `Monitor` 工具（2026-09-29 在 Claude Code 2.1.284 由工具 schema 現查）：預設是 deferred tool，要先 `ToolSearch` 載入 schema 才能呼叫；背景跑一支 script，**stdout 每一行是一則通知**，script 結束即停止；`timeout_ms` 預設 5 分鐘，上限依 session 而異（同日互動 session 的 schema 寫 cap 1800000ms＝30 分，`claude -p` session 的 schema 寫 cap 600000ms＝10 分，JSON `maximum` 皆為 3600000），以當場 schema 為準；到期要重新掛。只需要一次通知（「CI 跑完告訴我」）時，schema 建議改用 Bash `run_in_background` 加會自己結束的 `until` 迴圈；過濾條件要涵蓋失敗與所有終止狀態，否則當掉和還在跑一樣安靜。用在 CI 等待的做法見 `../skills/parallel-dispatch/references/claude-code.md`「CI 等待與 PR」。
- Agent frontmatter 的 `model` 可填 `haiku`／`sonnet`／`opus`／`fable`／完整 model ID／`inherit`。
- Claude Code 2.1.222 的 subagent 可使用 `isolation: worktree`（2026-08-06 由 Agent 工具 schema 現查確認該參數仍存在）；需要 blocking 結果時不得只依賴可能因休眠中斷的背景執行。
- `isolation: worktree` 的實際行為（2026-09-12 在 Claude Code 2.1.267 實測＋官方 worktrees 文件）：worktree 建在 `<repo>/.claude/worktrees/<name>/`、branch 名 `worktree-<name>`、從 controller 當下 HEAD 開出；subagent 結束時有改動（commit 或 uncommitted）就保留，無改動則 worktree 與 branch 一起自動刪除；harness 不把路徑回報給 controller，要靠 subagent 自己回報或 `git worktree list`。官方不提供多 worktree 的合併方式。`.claude/worktrees/` 不會自動進 `.gitignore`，全目錄掃描工具會掃進去；本系統以使用者全域 gitignore 的 `**/.claude/worktrees/` 排除內建 isolation 的位置；controller 自建 worktree 另依 `../skills/parallel-dispatch/references/worktree.md`「所有權與路徑」放 `<repo>/.worktrees/`（2026-09-27 起）。Workflow 工具的 `agent()` 查不到 isolation 參數（未確認支援）。成本量級（2026-09-12，3 片 S／M 平行）：每片 2–4 輪修正＋驗收、共 12 次 agent 呼叫、約 1.6M subagent token、約 100 分鐘。使用流程見 `../skills/parallel-dispatch/SKILL.md`。
- `TaskStop` 對背景 subagent 的效果（2026-09-22 在 Claude Code 2.1.278 實測，n=1）：subagent 正在執行一個每秒 append 檔案、跑 240 秒的 Bash 呼叫時 `TaskStop`，回報 stopped 當秒檔案停止增長（最後一筆 10:43:51、stop 回報 10:43:52），之後 5 秒與 15 秒 read-back 行數不變，`pgrep` 查無殘留 process——子 process 隨 agent 一起結束，不是只停模型迴圈。未測：`isolation: worktree` 的 subagent、Write／Edit 工具寫到一半。
- subagent 完成通知的 `<usage>` 帶 `subagent_tokens`／`tool_uses`／`duration_ms`（2026-09-18 在 2.1.270–2.1.274 的 session jsonl 現查）；`subagent_tokens` 逐筆對該 agent jsonl 的 `input+cache_creation+cache_read` 核對，等於交回當下的 context 大小（同一 agent 多次交回時逐次遞增），`tool_uses` 是該輪工具呼叫數。
- 2026-09-17 的成本／輪次統計已更正：不再把原 bullet 中的 64%／37%／337K／67% 當政策依據；重算結果、限制與後續量測方法見 [`dispatch-cost-review-2026-09-17.md`](dispatch-cost-review-2026-09-17.md)。
- Claude agent **沒有 sandbox 欄位**——唯讀角色（`verifier`）只靠 tools 清單與指令合約約束，可寫角色（`worker`）更只剩合約（禁 branch／stash／覆蓋非自建檔案）在擋，controller 驗收時仍須 read-back `git status` 與 `git stash list` 確認無意外寫入。（為什麼 Claude 端只自建 `worker`／`verifier`、不設 Codex `scanner`／`explorer`／`planner` 等價 agent，見 README「檔案結構」。）（2026-08-23 從 `rules/10-dispatch.md` §0 搬入；原文僅去掉句首的「註：」。）
- Codex CLI 0.154.0 的本 session collaboration surface（2026-09-15 現查）提供 `spawn_agent`、`send_message`、`followup_task`、`list_agents`、`wait_agent`、`interrupt_agent`；`spawn_agent` 沒有 worktree isolation 參數，controller 仍須自己建每片 worktree。官方 [Subagents](https://developers.openai.com/codex/multi-agent) 文件也載明目前 Codex 可 steer、stop 與 close agent threads。工具名稱與可用性會隨 surface 改變，派工時仍現查；使用流程見 `../skills/parallel-dispatch/references/codex.md`。

## Agent 工具 `model` 參數的 alias 對照

> 2026-08-30 從 `rules/10-dispatch.md` §0 搬入。理由：harness 每 session 已注入同一份 model enum，常駐區再放一次是重複；但 alias→實際型號的對照全 repo 僅此一處，依 `maintain-guideline` §5 零命中規則不可刪、只能搬。搬入時原文未改寫；用途定位欄之後隨路由決策更新。

| 參數值 | 實際型號 | 用途定位 |
|--------|----------|----------|
| `haiku` | claude-haiku-4-5 | 平台可用模型；不列入本制度 active routing |
| `sonnet` | claude-sonnet-5-5（2026-09-29 由 `claude -p --model sonnet --output-format json` 的 `modelUsage` 現查；原為 claude-sonnet-5） | 掃描、總結、查網頁的讀取車道主力；`worker` 標準實作車道（frontmatter 鎖完整 ID） |
| `opus` | claude-opus-5-5（2026-09-23 由 verifier transcript 的 `"model":"claude-opus-5-5"` 現查；2026-08-30 原為 claude-opus-5） | 難題升級、高風險判斷 |
| `fable` | claude-fable-5-1（2026-09-29 由 09-26 subagent transcript 的 assistant message.model 現查，n=25 request；原為 claude-fable-5） | 最高階；高風險實作／規劃與最終升級（驗收不自動走這條，見 `../rules/10-dispatch.md` §5） |

alias 會隨平台改版重新指向新一代同層模型——要宣稱某次派工實際跑在哪個型號，以當場自報的 model ID 為準，不引用本表。

## 主對話 context 大小怎麼量、cache 何時過期（2026-10-01 實測）

> 窗口 C（2026-09-29 22:51～10-01 09:07）主對話 Opus 5.5 的 session jsonl 量測：1,262 request、$354.64（API 等價）。用途：`../rules/00-environment.md` §1「修法」的 compact 時機，與 `../rules/10-dispatch.md` §3「Subagent 回報」的字數預設。

- **量主對話自己的 context**（2026-10-01 實測可跑，回 175154）：session-id 取 system prompt 裡 scratchpad 路徑倒數第二段的 UUID（末段是 `scratchpad`），再跑下列指令；三項相加與本檔前段 `subagent_tokens` 那條同一算法，取最後一筆 assistant usage。macOS 沒有 `tac`，用 `tail -r`。

  ```
  tail -r ~/.claude/projects/*/<session-id>.jsonl | jq -c 'select(.type=="assistant" and .message.usage!=null) | .message.usage | (.input_tokens+.cache_read_input_tokens+.cache_creation_input_tokens)' | head -1
  ```
- **prompt cache 為 1h TTL**：窗口 C 的 cache_write 全為 1h、5m 為 0。request 間隔 5–60 分的 137 次全部未過期；間隔 >60 分（71–501 分）的 9 次全部整段重寫，cache_write $40.68（含 cache_read 的 request 總額約 $41）。cache 完整重寫合計 11 次、$45.53；ToolSearch 載入 deferred tool 會改 prefix 而觸發重寫，2 次、$4.52（$45.53 與 $4.52 都是 request 總額口徑）。
- **主對話成本拆解**：69% 是 cache_read；context 中位 344K、P90 770K，>400K 的 request 占 62% 成本；最貴 3 個 session 占 82%；前兩名 context 中位 571K／674K、窗口內未 compact，第三名中位 293K、最大 494K、compact 1 次。連續唯讀工具 request（每段第一個以外）369 個、$84.45＝23.8%。subagent 回報中位 5.2K 字，全文留在主對話 context、每輪重讀，占位估 $72.19（20.4%，估算值）。
- **compact 模擬**：「context 超過 T 就 compact 到約 90K」，T=200K 上界省 37%、T=300K 上界省 34%（上界：未計 compact 後重建 context 的成本與在途工作風險）。
- **未驗證**：compact 時有在途背景 subagent，其回報是否仍正常送達主對話。
- **subagent 寫報告檔會被擋**（2026-10-01，n=2，general-purpose）：用 Write 把報告寫到 scratchpad 時 harness 回「Subagents should return findings as text, not write report files」。觸發條件（[anthropics/claude-code#44657](https://github.com/anthropics/claude-code/issues/44657)，2026-10-01 查證、本機 2.1.286）：Agent 工具派出的 subagent 寫 `.md` 且檔名以 `report`／`summary`／`findings`／`analysis` 開頭（不分大小寫），與路徑、agent 類型無關；server 端開關，無 settings／環境變數可關。worker 改 repo 內其他檔名不受影響。要長產物落檔時，檔名改用不以這四字開頭的名稱（如 `out-<主題>.md`；2026-10-01 使用者同意此做法），或由 controller 從回報文字存檔。

## 被問到 model／effort 時怎麼答

> 2026-08-30 從 `rules/10-dispatch.md` §3 搬入。理由：這段服務的是「使用者問起時怎麼答」這個罕見場景，不是每個 session 都要的；§3 的判準（報呼叫參數、註明 runtime 未驗證）留在常駐區，本節只是細節。內容原文未改寫。

被問到 model／effort 時報**呼叫時指定的參數**——那是你自述得出的。**本制度不稽核 subagent 實際跑在哪個 model**：runtime model ID 只能在派工 prompt 裡事前要求 subagent 自報，事後補問不到，而每次派工都加那段話的成本高過它的價值。所以被問時答「呼叫參數是 X，runtime 未驗證」，不要改口說已驗證。effort 另有硬限制：Agent 工具沒有 effort 參數、也無法 runtime 自報，有 `agents/<角色>.md` 的角色引其 frontmatter 標「宣告值」，其餘寫「未指定，繼承主對話」；外部模型（`codex:codex-rescue`）model／effort 都寫「不適用」。報制度出處要指得出是 §1、§5 或 `20-judgment.md` §1 的哪一條，「範圍明確」這類自由心證不算。

## 常駐內容對 subagent 的可見性、`paths` frontmatter、hook 注入（2026-09-20 實測）

> 實測環境：Claude Code 2.1.278、Windows `FatJohn-PC`，在 scratchpad 臨時專案跑 `claude -p --output-format json`，用帶編號的哨兵字串問模型「context 裡有沒有」。用途：拆 `rules/05-hosts.md` 成 `hosts/<key>.md` 的依據（`skills/maintain-guideline/SKILL.md` §5「單機專屬事實不進 rules/」）。Mac 端只補測了匯入與 token 校準（見下方「Mac 補測」），其餘未在 Mac 實測。

| 內容 | 主對話 | `general-purpose`／`worker`（`~/.claude/agents/` 自訂 agent） | `Explore`／`Plan` |
|---|---|---|---|
| 全域 `CLAUDE.md`、`~/.claude/rules/*.md`、專案 `CLAUDE.md`、專案 `.claude/rules/*.md` | ✅ | ✅（同一個 `<system-reminder>` 區塊；**每派一個就再付一次**） | ❌ 完全沒有（連三條鐵律都沒有） |
| `CLAUDE.md` 的 `@./x.md`、`@~/…/x.md` 匯入 | ✅ launch 時展開 | ✅ | ❌ |
| SessionStart hook 的 stdout／JSON `additionalContext` | ✅（獨立 system 訊息，排在 rules 那批之後、第一則 user message 之前） | ❌ | ❌ |
| SubagentStart hook 的 JSON `additionalContext` | — | ✅ | ✅（文件未列此事件支援 `additionalContext`，實測可用） |

- `@import` **缺檔靜默略過**，沒有任何錯誤或提示——靠匯入撐的內容要配哨兵句（`rules/05-hosts.md` 那段就是）。`@~/` 家目錄路徑在 Windows 也能展開。
- `.claude/rules/*.md` 的 `paths` frontmatter：glob 只相對專案根目錄比對（`paths: ["C:/Users/**"]` 在 Read 了 `C:\Users\…\src\a.ts` 之後仍不載入）；觸發時機是 **Read 工具讀到符合檔之後**（以「Contents of …\cond.md」訊息附在 Read 結果後），不是 session 開頭，Bash `cat` 不算；`paths: ["**"]` 反而 launch 就載入（等同無條件，原因未查）。**做不了機器分流。**
- `claude -p` 會跑 SessionStart hook；Windows 上 shell-form hook 用 Git Bash 執行（hook 內 `uname -s` 回 `MINGW64_NT`）。
- token 校準：`rules/05-hosts.md`（拆之前）4,317 bytes 實測 2,083 tokens，**2.07 bytes/token**（中英混排；`claude -p` 預設模型 claude-opus-5）。這台機器空目錄 session 的固定 prompt 是 54,359 tokens，同一批內重跑數字相同。
- 拆分前後的實測（`CLAUDE_CONFIG_DIR` 指到兩個只含 CLAUDE.md＋rules 的隔離設定目錄，背靠背跑）：舊形狀 61,198 → 新形狀 60,895，**Windows 端每 session 省 303 tokens**（丟掉 Mac 段、加回哨兵與對照表後的淨值）；Mac 端丟的是 Windows 段（≈1,265 tokens），估計淨省 ≈870，**未在 Mac 實測**。同一設定隔幾分鐘重跑會漂 7–8k tokens（fresh config dir 自己長出 plugins 目錄），跨時段的絕對數字不能拿來比，只能比背靠背那組。
- **Mac 補測（2026-09-20，`xushengzhedeMacBook-Pro.local`，`claude -p --model sonnet --output-format json`，scratchpad 空目錄背靠背）**：`@~/.claude/host-facts.md` 匯入在 Mac 成立——symlink 建立前問「有沒有『# 本機事實：』標題」回「無」、建立後引出標題；prompt 56,284 → 56,894，`hosts/macos.md` 1,185 bytes＝610 tokens（**1.94 bytes/token**）。拆分那個 commit 合進來時 Mac 端沒有裝 `host-facts.md`，當天 14:17 之後的 Mac session 都沒有本機事實，是事後 review 才發現的——**改安裝清單的 commit，另一台機器要等人去裝才生效**。
- 同日常駐 bytes 帳（`CLAUDE.md`＋`rules/00`＋`rules/05`＋host-facts；`git show <rev>:<file> | wc -c`）：當天第一個 commit 之前 11,631 → 拆分前 13,982（同日 `1673f4d` 把 05-hosts 從 2,615 加到 4,317）→ 拆分後 Mac 12,324／Windows 13,389 → 同日再精簡 CLAUDE.md（刪掉與 `hosts/windows.md` 重複的 Windows 專屬 ⚠️ 段、縮檔頭與段標題，4,792 → 3,959）後 Mac 11,491／Windows 12,599 → 第二輪（CLAUDE.md 常駐檔索引列併成一句、只留「用到才讀」表，3,959 → 3,104；`hosts/macos.md` 1,185 → 1,106）後 Mac 10,557／Windows 11,744。**上面「省 303／≈870 tokens」是對拆分前那個當天才長大的基準算的**；對當天開頭算，Mac −1,074 bytes、Windows +113 bytes（Windows 多的是新增的 448／複本安裝事實）。
- `claude -p --allowed-tools "" '<prompt>'` 會把 prompt 吃進 `--allowed-tools`（可變長參數）而報 `Input must be provided`；prompt 用 stdin（`echo … | claude -p …`）或 `<<<`，或把 `--allowed-tools ""` 放在 prompt 之後。
- 附帶：`rules/10-dispatch.md` §2「subagent 也會讀到全域 rules」只對 general-purpose／worker 成立，Explore／Plan 不成立——登記為候選（`FatJohn/agents-guideline` issue #3），未動判準。
