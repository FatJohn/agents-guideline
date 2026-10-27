# 運作機制：哪些東西在什麼時刻生效、各裝在哪

讀者：要理解、排錯或重建這套系統的維護者與 agent。

型別：說明

> 本檔回答「Claude Code 跑起來時，本系統的哪些部分在哪個時刻進入 context 或攔截工具呼叫，它們分別由 repo 的檔案還是本機的 `settings.json` 承載，少了會長什麼樣」。安裝步驟在 `docs/install.md`，逐檔用途在 `docs/repo-layout.md`，量測數字在 `docs/harness-facts.md`，本檔只講機制與邊界。

## 兩半承載：repo 檔與 settings.json

系統由兩半組成，缺任一半都不會報錯，只會靜默退化。

| 承載 | 內容 | 誰管 | 改了怎麼生效 |
|---|---|---|---|
| repo 檔（symlink 進 `~/.claude`、`~/.agents`、`~/.codex`） | 入口、host facts、judgment、路由卡、agent 合約、rubrics、skills、hook **腳本**、ripgreprc | 本 repo，`git` 版控 | symlink 版改 repo 即時生效；複本版要重跑 `scripts/sync-profile.py --apply --update` |
| `~/.claude/settings.json` | hook **登記**（哪個事件跑哪支腳本）、`language`、`env.RIPGREP_CONFIG_PATH`、permissions、`model`／`effortLevel`、statusline、plugins | 本機手動；repo 只提供 `global/claude/settings.snippets.json` 片段與 `docs/install.md` 的追加說明 | 新開的 session 生效 |

hook 是最容易只裝一半的部分：腳本在 `~/.claude/hooks/` 連上了，但 `settings.json` 沒有對應的 hook 元素，腳本永遠不會被叫到；反過來，`settings.json` 登記了而腳本缺檔，Claude Code 只在 transcript 留一則 hook error、session 照常跑。

## 四個時刻

| 時刻 | 進入什麼 | 承載 | 失效形狀 |
|---|---|---|---|
| session 啟動 | `~/.claude/CLAUDE.md`（含 `@~/.claude/host-facts.md` 匯入）、`~/.claude/rules/judgment.md`、回覆語言 | repo 檔＋`settings.json` 的 `language` | `@import` 缺檔靜默略過；`language` 漏設回預設語言 |
| session 啟動（只有主對話） | controller 路由卡 `~/.claude/route-card.md`，由 `hooks/controller-context.sh` 以 SessionStart hook 的 stdout 注入 | 腳本在 repo、登記在 `settings.json` `hooks.SessionStart` | context 裡沒有以 `# Contents of ` 開頭、含 `route-card.md` 的注入；主對話照常跑但沒有派工路由 |
| 每次工具呼叫 | PreToolUse hook（下節三支）＋ `permissions` 規則 | 腳本在 repo、登記在 `settings.json` `hooks.PreToolUse` | 本該被擋的呼叫直接執行，沒有任何提示 |
| 派 subagent | `~/.claude/agents/{worker,verifier}.md` 合約進該 subagent 的 context；`general-purpose`／自訂 agent 繼承全域 `CLAUDE.md` 與 `rules/`，不繼承路由卡；`Explore`／`Plan` 兩者都不繼承 | repo 檔 | 可用 agent 清單裡沒有 `worker`／`verifier`，Agent 工具報 unknown agent type |
| skill 觸發 | `~/.claude/skills/<name>/SKILL.md`，description 與任務比對到才載入 | repo 檔 | skill 清單沒有該名字；或清單有、但 controller 沒載就照自己的印象做（issue session 旗標事故就是這個形狀，見下節） |

## hooks：四支，各補一條靠自律會漏的規則

| hook | 事件／matcher | 做什麼 | 補的是哪條規則 | 離線測試 |
|---|---|---|---|---|
| `controller-context.sh` | `SessionStart`（無 matcher） | 把路由卡印到 stdout，注入主對話 | 路由卡只給 controller，subagent 不付這份 context（`docs/harness-facts.md`「controller 專用規則分流」） | `tests/test-controller-context.sh` |
| `block-ci-edit.sh` | `PreToolUse`，`Edit\|Write\|MultiEdit\|NotebookEdit` | 主對話（stdin 沒有 `agent_id`）改 `.github/workflows`／`.github/actions` 時 exit 2 | dispatch skill §1「controller 自做的邊界」：CI／release 設定不自做 | `tests/test-block-ci-edit.sh` |
| `allow-git-c-projects.sh` | `PreToolUse`，`Bash` | 嚴格形狀的 `git -C <projects 下路徑> worktree remove`／`branch -D` 回 allow，其餘不表態 | 替代會觸發 Claude Code 警告的 `Bash(git -C * …)` wildcard 規則 | `tests/test-allow-git-c-projects.sh` |
| `require-issue-session-model.sh` | `PreToolUse`，`Bash` | `orca worktree create`／`orca agent launch` 帶 `--agent claude` 卻缺 `--model` 或 `--effort` 時 exit 2 | parallel-dispatch `references/cli.md`「盤點 session 與 issue session」：issue session 一律帶固定旗標，不隨主對話預設 | `tests/test-require-issue-session-model.sh` |

各支的性質：

- 兩支擋板（`block-ci-edit.sh`、`require-issue-session-model.sh`）只擋，不改寫指令；exit 2 的 stderr 訊息會回到模型，裡面寫著規則出處與正確寫法。
- 三支 PreToolUse hook 都 fail-open：`jq` 不在 PATH 或 stdin 不是 JSON 時 exit 1、不擋也不放行，transcript 看得到 `INACTIVE`／`did not run`。裝完要跑一次離線測試，不能只看檔案存在。
- `require-issue-session-model.sh` 以整條 Bash 指令為單位：任一段命中就整條不放行，前面已經寫好的其他步驟也不會跑；補旗標後整條重送。它是字面比對，heredoc 或字串裡出現同形狀的文字也會被擋，寫文件時用 Write／Edit 工具落地，不經 Bash。
- `controller-context.sh` 不用 `jq`，卡片缺檔時靜默 exit 0、無輸出；唯一的判定訊號是 context 裡有沒有那行注入。
- `settings.json` 裡還有 Orca 自己登記的 matcher `*` hook（所有事件各一個，指向 `~/.orca/agent-hooks/`），不屬本 repo；追加本系統的 hook 元素時只加、不動它。

為什麼是 hook 不是規則：規則檔都是 advisory context，模型沒載到或沒照做時沒有任何訊號。`docs/install.md`「Claude Code permissions 要和鐵律二對齊」把這條寫成原則：零例外的事交給 hook。

`require-issue-session-model.sh` 的來歷是直接案例。`cli.md` 寫了旗標規定，但 controller 沒載 parallel-dispatch skill，照 host facts 一句沒帶旗標的範例起了四個 issue session，全部拿到 `settings.json` 當時的預設 model。hook 上線後，同形狀的指令在主對話 Bash 被擋：已實測（2026-10-27，主力 Mac）。文件裡每個可複製的 `--agent claude` 範例也都帶齊旗標。

## settings.json 裡本系統依賴的欄位

| 欄位 | 值 | 少了會怎樣 |
|---|---|---|
| `language` | `繁體中文台灣用語` | 回覆掉回預設語言；入口不寫語言段，只靠這裡 |
| `env.RIPGREP_CONFIG_PATH` | `~/.claude/ripgreprc` 的絕對路徑 | Bash 的 `rg` 不帶 `--hidden`，judgment §3 殘留掃描漏 `.claude/`、`.github/` |
| `hooks.SessionStart[]` | `controller-context.sh` 元素 | 主對話沒有路由卡 |
| `hooks.PreToolUse[]` | `block-ci-edit.sh`、`allow-git-c-projects.sh`、`require-issue-session-model.sh` 三個元素 | 對應擋板失效，見上表 |
| `permissions` | 本 repo 不管理；原則是 allow 只放可判定唯讀的子命令（`docs/install.md`「Claude Code permissions 要和鐵律二對齊」） | 對外或不可逆動作可能不再逐次確認 |
| `model`／`effortLevel` | 本 repo 不管理；是主對話與**任何沒帶 `--model` 的 `claude` 程序**的預設。可以刻意設便宜（例如 sonnet／high 給只做盤點、起 issue session 的主對話），單一任務要 Opus 時用 `/model` 當次切 | 沒帶旗標起的 session 跟著它變；issue session 由 `require-issue-session-model.sh` 保證帶旗標，不受影響 |

model 的優先序由低到高：全域 `settings.json`、專案層 `.claude/settings.local.json`、CLI 的 `--model`／`--effort` 旗標。旗標蓋過所有 settings 層：已實測（2026-10-27，主力 Mac），settings 設 sonnet／high、旗標給 opus／medium 時，init 訊息與 session jsonl 都是 opus／medium。

## 每個座位的 model 在哪設、怎麼選

每個座位的 model 各有一個設定點，互不影響；選法的原則是：便宜的預設給量大的座位，貴的能力只在單一任務需要時當次切。

| 座位 | model／effort | 設定點 | 選法 |
|---|---|---|---|
| 主對話（controller） | `settings.json` 的 `model`／`effortLevel`，可被專案 `.claude/settings.local.json` 與 `/model` 蓋過 | 本機 settings，使用者自選 | 工作型態是「盤點、起 issue session、驗收回報」時設便宜的（sonnet／high）；單一任務要重推理時 `/model opus` 當次切，不改 settings |
| issue session（獨立 controller） | `claude-opus-5-5`／medium | `orca worktree create` 的 `--model`／`--effort` 旗標，`require-issue-session-model.sh` 保證帶齊 | 固定值，寫在 parallel-dispatch `references/cli.md`；要換值改 cli.md，hook 只檢查有沒有帶 |
| `worker` | `claude-sonnet-5-5`／high | `global/claude/agents/worker.md` frontmatter | 派工不帶 `model`／`effort`；不收斂時依 dispatch skill §5 升級，不是調這裡 |
| `verifier` | opus／medium | `global/claude/agents/verifier.md` frontmatter | 派工顯式 `model: opus`、不帶 `effort`；升 fable 要使用者當次同意 |
| `Explore`／`Plan`／`general-purpose` | haiku／opus／sonnet 或 opus | Agent 工具的 `model` 參數，依路由卡 | 路由卡角色表定死，controller 不自選 |

主對話設便宜不影響其他座位：issue session 由 hook 保證帶旗標，subagent 由 frontmatter 與路由卡決定。改 `settings.json` 的 `model` 只會動到主對話與其他沒帶旗標的 `claude` 程序。

## 重建一台機器：兩半各要補齊什麼

| 元件 | repo 來源 | 本機位置 | 已裝的判定訊號 |
|---|---|---|---|
| 入口與 host facts | `global/claude/CLAUDE.md`、`global/shared/hosts/<key>.md` | `~/.claude/CLAUDE.md`、`~/.claude/host-facts.md` | `claude -p` 不准用工具時能引出「# 本機事實：」標題與 hostname（`docs/install.md`「安裝 Claude Code」） |
| judgment | `global/shared/rules/` | `~/.claude/rules/` | `ls ~/.claude/rules/` 只有 `judgment.md`（多一個檔就是 v1 殘留） |
| 路由卡＋SessionStart hook | `global/claude/route-card.md`、`global/claude/hooks/controller-context.sh` | `~/.claude/route-card.md`、`~/.claude/hooks/`＋`settings.json` 元素 | 新 session context 有 `# Contents of …route-card.md` |
| PreToolUse hooks | `global/claude/hooks/*.sh` | `~/.claude/hooks/`＋`settings.json` 三個元素 | 三支離線測試 `failures=0`；主對話 Bash 下 `false && orca worktree create --name probe --agent claude --prompt x` 被 hook 擋下（hook 沒裝時 `false` 讓後段不執行，不會真的開 worktree） |
| agents、rubrics、skills | `global/claude/agents/`、`global/shared/rubrics/`、`global/shared/skills/` | `~/.claude/agents/`、`~/.claude/rubrics/`、`~/.claude/skills/`、`~/.agents/skills/` | 可用 agent 清單有 `worker`／`verifier`；skill 清單有六個共用 skill |
| ripgreprc | `global/claude/config/ripgreprc` | `~/.claude/ripgreprc`＋`settings.json` `env` | `tests/test-ripgreprc.sh`；Claude Code 的 Bash 裡 `rg` 不帶 `--hidden` 也搜到隱藏目錄 |
| language | `global/claude/settings.snippets.json` | `settings.json` 頂層 | 回覆是繁體中文 |
| Codex 端 | `global/codex/AGENTS.md`、`global/shared/skills/`、`global/codex/agents/*.toml` | `~/.codex/AGENTS.md`、`~/.agents/skills/`、`~/.codex/agents/`（實體檔，`scripts/sync-codex-agents.py`） | TOML 檔 bytes 與 repo 一致；named spawn 實際起得來 |

「本機位置」欄的檔案與目錄由 `docs/install.md` 的主安裝一次連好。標「＋`settings.json`」的部分全部要手動追加，片段在 `global/claude/settings.snippets.json`；`tests/test_settings_snippets.py` 保證片段、hook 腳本與 `docs/install.md` 的 JSON 區塊三者一致。

## 不在 repo 管轄、但會影響觀感的東西

- **plugins**（`enabledPlugins`）：各自帶 skill 與 hook，與本系統無關；盤點與瘦身見 `docs/reviews/codex-tooling-audit-2026-10.md`。
- **statusline**（ccstatusline）：`model` 欄讀 Claude Code 餵的 status JSON，反映該 session 實際 model；`thinking-effort` 欄沒拿到 status JSON 的 `effort.level`、該 session 又沒跑過 `/effort` 或 `/model` 時，退回顯示 `settings.json` 的 `effortLevel`，不反映 `--effort` 旗標。要確認某個 session 的 effort，看它 jsonl 的 `"effort"` 欄位。
- **Orca**：`settings.json` 的 matcher `*` hooks 與 `~/.orca/` 由 Orca 安裝；`orca worktree create --agent claude` 翻成 `claude --model … --effort … <prompt>` 起頂層 session，旗標語意見 `global/shared/skills/parallel-dispatch/references/cli.md`。
- **`settings.json` 的 permissions**：安裝後另行 audit，原則見 `docs/install.md`「Claude Code permissions 要和鐵律二對齊」。

## Codex 端的對照

Codex 沒有 SessionStart／PreToolUse 的等價機制。`global/codex/rules/` 不分流，subagent 與主對話讀同一份；四支 hook 補的規則在 Codex 端只有文字版（dispatch 規則與 `cli.md`），沒有機械擋板。這是刻意分版，理由見 `docs/repo-layout.md`「Codex」。
