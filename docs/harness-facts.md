# 查證過的 harness 事實

> 2026-08-22 從 `rules/00-environment.md` 搬出。理由：這些是**派工當下**才用得到的 Agent 工具事實，
> 而 `rules/` 是每個 session 全文載入的常駐區（`maintain-guideline` §5「只在特定情境才用得到的
> 內容不該放 rules/」）。`rules/10-dispatch.md` §0 已經指向這裡。內容原文未改寫。
>
> **查證日：2026-08-06。版本更新後重新核對**——這些值會隨 Claude Code／Codex 改版漂移，
> 要宣稱某個參數存在時以當場現查的工具 schema 為準，不引用本檔。

- Agent 呼叫可逐次指定 model；effort 仍由 agent 定義 frontmatter 或 session/workflow 設定控制。
- 主對話（controller）的 model 由 UI 選擇，effort 由 `~/.claude/settings.json` 的 `effortLevel` 設定（2026-07-25 核對為 `xhigh`；2026-09-07 複查仍為 `xhigh`，另有 `modelSettings.claude-fable-5-1.effortLevel: high` 的逐型號覆寫）。**subagent 不指定 `model` 時繼承主對話的模型**，所以 `../rules/10-dispatch.md` 各表的 model 欄是顯式 routing 指示，派 `worker`／`verifier` 一律要寫 `model:`。（2026-09-07 從 `rules/10-dispatch.md` §0 搬入；原「Max 檔位實作預設 opus、Pro 檔位降回 sonnet」的分檔位規則已由 `worker/Sonnet xhigh` 不分檔位取代，刻意放棄。）
- Agent frontmatter 的 `effort` 可填 `low`／`medium`／`high`／`xhigh`／`max`，實際可用值仍受模型與組織限制。
- Agent frontmatter 的 `model` 可填 `haiku`／`sonnet`／`opus`／`fable`／完整 model ID／`inherit`。
- Claude Code 2.1.222 的 subagent 可使用 `isolation: worktree`（2026-08-06 由 Agent 工具 schema 現查確認該參數仍存在）；需要 blocking 結果時不得只依賴可能因休眠中斷的背景執行。
- `isolation: worktree` 的實際行為（2026-09-12 在 Claude Code 2.1.267 實測＋官方 worktrees 文件）：worktree 建在 `<repo>/.claude/worktrees/<name>/`、branch 名 `worktree-<name>`、從 controller 當下 HEAD 開出；subagent 結束時有改動（commit 或 uncommitted）就保留，無改動則 worktree 與 branch 一起自動刪除；harness 不把路徑回報給 controller，要靠 subagent 自己回報或 `git worktree list`。官方不提供多 worktree 的合併方式。`.claude/worktrees/` 不會自動進 `.gitignore`，全目錄掃描工具會掃進去。Workflow 工具的 `agent()` 查不到 isolation 參數（未確認支援）。成本量級（2026-09-12，3 片 S／M 平行）：每片 2–4 輪修正＋驗收、共 12 次 agent 呼叫、約 1.6M subagent token、約 100 分鐘。使用流程見 `../skills/parallel-dispatch/SKILL.md`。
- subagent 完成通知的 `<usage>` 帶 `subagent_tokens`／`tool_uses`／`duration_ms`（2026-09-18 在 2.1.270–2.1.274 的 session jsonl 現查）；`subagent_tokens` 逐筆對該 agent jsonl 的 `input+cache_creation+cache_read` 核對，等於交回當下的 context 大小（同一 agent 多次交回時逐次遞增），`tool_uses` 是該輪工具呼叫數。
- 2026-09-17 的成本／輪次統計已更正：不再把原 bullet 中的 64%／37%／337K／67% 當政策依據；重算結果、限制與後續量測方法見 [`dispatch-cost-review-2026-09-17.md`](dispatch-cost-review-2026-09-17.md)。
- Claude agent **沒有 sandbox 欄位**——唯讀角色（`verifier`）只靠 tools 清單與指令合約約束，可寫角色（`worker`）更只剩合約（禁 branch／stash／覆蓋非自建檔案）在擋，controller 驗收時仍須 read-back `git status` 與 `git stash list` 確認無意外寫入。（為什麼 Claude 端只自建 `worker`／`verifier`、不設 Codex `scanner`／`explorer`／`planner` 等價 agent，見 README「檔案結構」。）（2026-08-23 從 `rules/10-dispatch.md` §0 搬入；原文僅去掉句首的「註：」。）
- Codex CLI 0.154.0 的本 session collaboration surface（2026-09-15 現查）提供 `spawn_agent`、`send_message`、`followup_task`、`list_agents`、`wait_agent`、`interrupt_agent`；`spawn_agent` 沒有 worktree isolation 參數，controller 仍須自己建每片 worktree。官方 [Subagents](https://developers.openai.com/codex/multi-agent) 文件也載明目前 Codex 可 steer、stop 與 close agent threads。工具名稱與可用性會隨 surface 改變，派工時仍現查；使用流程見 `../skills/parallel-dispatch/references/codex.md`。

## Agent 工具 `model` 參數的 alias 對照

> 2026-08-30 從 `rules/10-dispatch.md` §0 搬入。理由：harness 每 session 已注入同一份 model enum，常駐區再放一次是重複；但 alias→實際型號的對照全 repo 僅此一處，依 `maintain-guideline` §5 零命中規則不可刪、只能搬。內容原文未改寫。

| 參數值 | 實際型號 | 用途定位 |
|--------|----------|----------|
| `haiku` | claude-haiku-4-5 | 平台可用模型；不列入本制度 active routing |
| `sonnet` | claude-sonnet-5 | 掃描、總結、批次機械車道主力；`worker` 一般實作與文件產出的預設，不分訂閱檔位 |
| `opus` | claude-opus-5 | 難題升級、高風險判斷 |
| `fable` | claude-fable-5 | 最高階；高風險實作／規劃與最終升級（驗收不自動走這條，見 `../rules/10-dispatch.md` §5） |

alias 會隨平台改版重新指向新一代同層模型——要宣稱某次派工實際跑在哪個型號，以當場自報的 model ID 為準，不引用本表。

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
