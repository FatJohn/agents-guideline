# 查證過的 harness 事實

> 2026-08-22 從 `rules/00-environment.md` 搬出。理由：這些是**派工當下**才用得到的 Agent 工具事實，
> 而 `rules/` 是每個 session 全文載入的常駐區（`maintain-guideline` §5「只在特定情境才用得到的
> 內容不該放 rules/」）。`rules/10-dispatch.md` §0 已經指向這裡。內容原文未改寫。
>
> **查證日：2026-08-06。版本更新後重新核對**——這些值會隨 Claude Code 改版漂移，
> 要宣稱某個參數存在時以當場現查的工具 schema 為準，不引用本檔。

- Agent 呼叫可逐次指定 model；effort 仍由 agent 定義 frontmatter 或 session/workflow 設定控制。
- 主對話（controller）的 model 由 UI 選擇，effort 由 `~/.claude/settings.json` 的 `effortLevel` 設定（2026-07-25 核對為 `xhigh`；2026-09-07 複查仍為 `xhigh`，另有 `modelSettings.claude-fable-5-1.effortLevel: high` 的逐型號覆寫）。**subagent 不指定 `model` 時繼承主對話的模型**，所以 `../rules/10-dispatch.md` 各表的 model 欄是顯式 routing 指示，派 `worker`／`verifier` 一律要寫 `model:`。（2026-09-07 從 `rules/10-dispatch.md` §0 搬入；原「Max 檔位實作預設 opus、Pro 檔位降回 sonnet」的分檔位規則已由 `worker/Sonnet high` 不分檔位取代，刻意放棄。）
- Agent frontmatter 的 `effort` 可填 `low`／`medium`／`high`／`xhigh`／`max`，實際可用值仍受模型與組織限制。
- Agent frontmatter 的 `model` 可填 `haiku`／`sonnet`／`opus`／`fable`／完整 model ID／`inherit`。
- Claude Code 2.1.222 的 subagent 可使用 `isolation: worktree`（2026-08-06 由 Agent 工具 schema 現查確認該參數仍存在）；需要 blocking 結果時不得只依賴可能因休眠中斷的背景執行。
- `isolation: worktree` 的實際行為（2026-09-12 在 Claude Code 2.1.267 實測＋官方 worktrees 文件）：worktree 建在 `<repo>/.claude/worktrees/<name>/`、branch 名 `worktree-<name>`、從 controller 當下 HEAD 開出；subagent 結束時有改動（commit 或 uncommitted）就保留，無改動則 worktree 與 branch 一起自動刪除；harness 不把路徑回報給 controller，要靠 subagent 自己回報或 `git worktree list`。官方不提供多 worktree 的合併方式。`.claude/worktrees/` 不會自動進 `.gitignore`，全目錄掃描工具會掃進去。Workflow 工具的 `agent()` 查不到 isolation 參數（未確認支援）。成本量級（2026-09-12，3 片 S／M 平行）：每片 2–4 輪修正＋驗收、共 12 次 agent 呼叫、約 1.6M subagent token、約 100 分鐘。使用流程見 `../skills/parallel-dispatch/SKILL.md`。
- Claude agent **沒有 sandbox 欄位**——唯讀角色（`verifier`）只靠 tools 清單與指令合約約束，可寫角色（`worker`）更只剩合約（禁 branch／stash／覆蓋非自建檔案）在擋，controller 驗收時仍須 read-back `git status` 與 `git stash list` 確認無意外寫入。（為什麼 Claude 端只自建 `worker`／`verifier`、不設 Codex `scanner`／`explorer`／`planner` 等價 agent，見 README「檔案結構」。）（2026-08-23 從 `rules/10-dispatch.md` §0 搬入；原文僅去掉句首的「註：」。）

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
