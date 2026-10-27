# 安裝 Claude Code／Codex

讀者：要在機器上安裝、升級本工作系統的人與 agent。

型別：接入指南

> 本檔是 `README.md` 安裝入口指向的完整安裝步驟：Claude Code（macOS／Linux）→ Codex（macOS／Linux）→ Windows（PowerShell，兩側一起裝）→ 實體檔同步版（不能提權的機器）→ 從 v1 升級。
> 想先懂「哪些東西在什麼時刻生效、各裝在哪、少了會怎樣」再動手，讀 `docs/design/mechanism.md`「運作機制」。
> `REPO` 依機器而異：macOS 主力機是 `~/Projects/FatJohn/agents-guideline`，Windows 桌機是 `D:\Projects\FatJohn\agents-guideline`，兩者的對照在 `global/codex/AGENTS.md`「Bootstrap」；新機器先照 `docs/new-host.md` 建檔。

## 安裝對應

所有安裝來源都在 `<REPO>/global/` 底下；`.claude/skills/` 的 `maintain-guideline`、`usage-review` 是 repo-only，在本 repo 開工時由專案層自動可用，不安裝。

| 安裝位置 | 來源 | 形式 |
|---|---|---|
| `~/.claude/CLAUDE.md` | `global/claude/CLAUDE.md` | 檔 |
| `~/.claude/host-facts.md` | `global/shared/hosts/<key>.md`（每台只裝自己那份） | 檔 |
| `~/.claude/rules/` | `global/shared/rules/`（目前只有 `judgment.md`） | 目錄 |
| `~/.claude/route-card.md` | `global/claude/route-card.md`（SessionStart hook 注入主對話） | 檔 |
| `~/.claude/agents/{worker,verifier}.md` | `global/claude/agents/` | 檔 |
| `~/.claude/rubrics/` | `global/shared/rubrics/` | 目錄 |
| `~/.claude/hooks/` | `global/claude/hooks/` | 目錄 |
| `~/.claude/ripgreprc` | `global/claude/config/ripgreprc` | 檔 |
| `~/.claude/skills/<name>`、`~/.agents/skills/<name>` | `global/shared/skills/<name>`，name ∈ dispatch、handoff、git-commit、create-pr、parallel-dispatch、writing-principles | 目錄 |
| `~/.codex/AGENTS.md` | `global/codex/AGENTS.md` | 檔 |
| `~/.codex/agents/*.toml` | `global/codex/agents/*.toml` | 實體檔（`scripts/sync-codex-agents.py`） |

## 安裝 Claude Code

macOS／Linux，symlink 版：repo 即唯一事實來源，改 repo 即時生效。Windows 用下方「安裝（Windows／PowerShell）」。

```bash
# 備份既有設定
cp -r ~/.claude ~/.claude.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline   # macOS 主力機；其他機器見上方
G="$REPO/global"
link_one() {   # link_one <來源> <目的>；已存在就略過，不覆蓋
  if [ -e "$2" ] || [ -L "$2" ]; then echo "略過（已存在，需手動處理）：$2"; else ln -s "$1" "$2"; fi
}
mkdir -p ~/.claude/agents ~/.claude/skills

# host-facts 只裝本機那份（主力 Mac 是 macos.md；其他機器換成自己的 key），CLAUDE.md 用 @~/.claude/host-facts.md 匯入
link_one "$G/claude/CLAUDE.md"          ~/.claude/CLAUDE.md
link_one "$G/shared/hosts/macos.md"     ~/.claude/host-facts.md
link_one "$G/shared/rules"              ~/.claude/rules
link_one "$G/claude/route-card.md"      ~/.claude/route-card.md
link_one "$G/shared/rubrics"            ~/.claude/rubrics
link_one "$G/claude/hooks"              ~/.claude/hooks
link_one "$G/claude/config/ripgreprc"   ~/.claude/ripgreprc
for agent in worker verifier; do link_one "$G/claude/agents/$agent.md" ~/.claude/agents/$agent.md; done
for skill in dispatch handoff git-commit create-pr parallel-dispatch writing-principles; do
  link_one "$G/shared/skills/$skill" ~/.claude/skills/$skill
done
```

指令可重跑（已存在就略過不覆蓋）。若「已存在」的是你自己的舊全域 CLAUDE.md，手動把本 repo 的路由表與邊界段落合併進去，不要直接覆蓋。從 v1 升級的機器，舊連結一律先清掉，見下方「從 v1 升級」。

裝完驗證本機事實真的被匯入（`@import` 缺檔是**靜默略過**，不會報錯）：`claude -p --allowed-tools "" <<< '不准用工具，引用 context 裡「# 本機事實」那段的標題與 hostname'`——回不出標題就是 `~/.claude/host-facts.md` 沒連上，或 CLAUDE.md 少了 `@~/.claude/host-facts.md` 那行。

symlink 的好處：session 依規則更新事實、寫教訓時直接改到 repo，git diff 一目了然，由使用者 review 後 commit。若遇到不跟隨 symlink 的工具，改用 `cp` 安裝並在每次改 repo 後重新複製。

⚠️ **`~/.claude/rules/` 是無條件常駐區**：Claude Code 會把該目錄下無 `paths` frontmatter 的 `*.md` 每 session 全文載入（subagent 也付），是每個 session 的固定 context 成本，所以只有「每次開工都需要」的內容放這裡，目前只有 `judgment.md`。只在特定情境才用的長內容放 skill、`rubrics/` 或 `docs/`，這幾處不會自動載入。`route-card.md` 刻意放在 `rules/` 外面，理由見下方「SessionStart hook」。

### Claude Code permissions 要和鐵律二對齊

`CLAUDE.md` 是 advisory context，不是 permission gate。`~/.claude/settings.json` 的全域 allowlist 不要放 `Bash(git push:*)`、`Bash(gh pr:*)` 或 `Bash(gh api:*)` 這類同時涵蓋唯讀與對外寫入的 wildcard；否則 push、merge 或任意 GitHub API 寫入可能不會出現逐次權限確認。只預先允許可明確判定為唯讀的子命令，例如 `git status`／`git diff`／`git log` 與 `gh pr view`／`gh pr checks`／`gh pr diff`。需要零例外硬擋時使用 `PreToolUse` hook 驗證 Bash command；不要把「規則文字通常會被遵守」當成 deterministic enforcement（見 [Anthropic 的 steering 指南](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)）。本 repo 不管理 `settings.json`，新機器安裝後要另行 audit。

### SessionStart hook：注入 controller 路由卡

**必裝。** `route-card.md`（何時必須派工、角色表、brief 必含欄位、指向 dispatch skill）只有主對話用得到，但放在 `rules/` 會原封注入每個 worker／verifier／general-purpose subagent。所以它不放 `~/.claude/rules/`，改由 `hooks/controller-context.sh` 以 SessionStart hook 的 stdout 只注入主對話（subagent 不跑 SessionStart、不繼承），省每個 subagent 的這份固定注入；分流實測見 `docs/harness-facts.md`「controller 專用規則分流」。

`route-card.md` 與 `hooks/` 的連結由上方主安裝一併建立；`settings.json` 要**手動追加**到 `hooks.SessionStart` 陣列（**追加元素，不要取代既有條目**；不設 matcher，官方文件寫 startup／resume／clear／compact 來源都會重跑；compaction 後重注入尚未實測，見 `docs/harness-facts.md`「controller 專用規則分流」）：

```json
{ "hooks": [ { "type": "command", "command": "bash \"$HOME/.claude/hooks/controller-context.sh\"" } ] }
```

- 驗證：新開 session 後 context 裡應有一行以 `# Contents of ` 開頭、含 `route-card.md` 的注入；沒有＝hook 未登記（hook 或卡片缺檔都靜默略過，與 `@import` 同一陷阱）。
- 腳本缺卡片檔時 exit 0、無輸出，不會讓 session 啟動失敗；`CLAUDE_ROUTE_CARD` 環境變數可改卡片路徑（測試用，`bash tests/test-controller-context.sh`）。
- Windows 與複本安裝：symlink 版用 `Link-One`（見下方 Windows 腳本），複本版由 `sync-profile.py` 一併複製 `route-card.md` 與 `hooks/`，`settings.json` 一樣要手動加。

### 選配：擋主對話改 CI 設定的 hook 與 ripgrep 預設設定

兩個檔（`hooks/block-ci-edit.sh`、`ripgreprc`）已由主安裝連好；要另外改 `~/.claude/settings.json` 才會生效（本 repo 不管理 `settings.json`）。三段合併用的片段（含上面的 SessionStart）收在 `<REPO>/global/claude/settings.snippets.json`，**逐段併入既有設定，不要整檔覆蓋**。片段另含頂層 `language`（`繁體中文台灣用語`）：Claude 端的回覆語言只由這個設定承接，入口不再寫語言段，新機器漏設就會掉回預設語言。

- `hooks/block-ci-edit.sh`：Claude Code `PreToolUse` hook。**主對話**（hook 收到的 stdin 沒有 `agent_id`）用 Edit／Write／MultiEdit／NotebookEdit 改路徑含 `.github/workflows/` 或 `.github/actions/` 的檔會被擋（exit 2，訊息要求改派 worker）；subagent（有 `agent_id`）與其他路徑一律放行。把 dispatch skill §1『何時派工』「controller 自做的邊界」那條「CI／release 設定不自做」變成機械擋板。
- `ripgreprc`：讓 **Bash 裡的 `rg`** 預設 `--hidden` 並排除 `.git`，對應 `global/shared/rules/judgment.md` 3『殘留掃描』。Claude Code 的 Grep 工具本來就搜隱藏目錄（不搜 `.git`），也不讀 `RIPGREP_CONFIG_PATH`，所以這份設定只影響 Bash 的 `rg`。

`~/.claude/settings.json` 要加兩段。頂層 `env`（已有 `env` 就只加這一個 key）；值必須是絕對路徑，settings 的 `env` 不經 shell 展開（`~` 是否展開沒測，不要依賴）；`<echo "$HOME/.claude/ripgreprc" 的輸出>` 整個換成該指令印出的完整路徑，路徑錯時 `rg` 每次在 stderr 報錯，且 `--hidden` 不生效：

```json
{
  "env": {
    "RIPGREP_CONFIG_PATH": "<echo \"$HOME/.claude/ripgreprc\" 的輸出>"
  }
}
```

以及下面這一個 hook 元素。**追加**到既有的 `hooks.PreToolUse` 陣列（別的元素，例如 matcher 為 `*` 的 hook，保留不動，不是取代）：

```json
{
  "matcher": "Edit|Write|MultiEdit|NotebookEdit",
  "hooks": [
    { "type": "command", "command": "bash \"$HOME/.claude/hooks/block-ci-edit.sh\"" }
  ]
}
```

command 用 `bash "<路徑>"`，不依賴執行權限位元。`$HOME` 在 command 裡的展開沒有單獨測（測試用的是絕對路徑）；若 hook 沒生效就改寫絕對路徑。

裝完驗證（在本 repo 根目錄；前三行離線、不需要 claude，`python3 -m pytest tests -q` 也會一起跑到）：

```bash
bash tests/test-block-ci-edit.sh ~/.claude/hooks/block-ci-edit.sh          # 需要 jq
bash tests/test-controller-context.sh ~/.claude/hooks/controller-context.sh
bash tests/test-ripgreprc.sh ~/.claude/ripgreprc                           # 需要 rg
# 端到端：主對話應被擋、檔案不變（<abs path> 換成任一 git 目錄下的 .github/workflows/x.yml）
# ripgreprc 端到端：在 Claude Code 的 Bash 裡（讀 settings.json 的 env）不帶 --hidden 也要搜到隱藏目錄；印出 PATH OK 才算生效
claude -p "Run exactly: mkdir -p /tmp/rgchk/.h && echo rgtoken > /tmp/rgchk/.h/f && rg -l rgtoken /tmp/rgchk && echo PATH OK"
claude -p --disallowedTools=Bash "Use the Edit tool yourself to change 'name: x' to 'name: y' in <abs path>/.github/workflows/x.yml; quote any tool error verbatim."
```

**已知限制**：

- **Bash 改檔不經 hook**：`sed -i`、heredoc、`tee`、`git apply` 改 `.github/workflows` 都不會被擋（實測 `sed -i` 改成功）。hook 只補 Edit／Write 這條路，dispatch skill 那條規則仍然要靠 controller 自己守。路徑只做字串比對，不解析 symlink。
- **CLI adapter 的 worker 也會被擋**：`global/shared/skills/parallel-dispatch/references/cli.md` 用 `claude -p` 起的 worker 是頂層 session，hook 的 stdin 沒有 `agent_id`，判斷方式與主對話相同，改 `.github/workflows`／`.github/actions` 會被擋。裝了這個 hook 的機器，這類切片改用 Agent 工具派 `worker`，不走 CLI adapter。
- **使用者要求主對話直接改 CI 也會被擋**：hook 不分專案、不分誰下的指示。使用者在編輯器自己改不受影響；真要主對話改，只能暫時移除 `settings.json` 裡那個 `PreToolUse` 元素。`claude --agent <name>` 啟動的主執行緒同樣沒有 `agent_id`，會被當主對話擋。
- **hook 會被略過**：`claude --bare`、`--setting-sources` 不含 user、`disableAllHooks`。`jq` 不在 PATH 或 stdin 不是 JSON 時 hook fail-open（exit 1，非阻擋錯誤，工具照跑；transcript 會顯示 `CI edit guard is INACTIVE`／`did not run`）——等於沒裝，不會誤擋。
- **沒測過**：agent teams／teammate、`isolation: worktree` 的 subagent（預期同樣帶 `agent_id`），以及與其他 `*` hook 並存。
- **`--hidden` 不蓋過 gitignore**：`.worktrees/` 或被專案 `.gitignore` 排除的隱藏目錄仍搜不到，要 `--no-ignore`（會連 `node_modules` 一起進）。沒裝 ripgreprc 的機器（包含 Codex）Bash 的 `rg` 要手動加 `--hidden`。

**Windows 上本段全部未驗證**：

- hook 在 Git Bash 執行，要用 `jq`。裝完先在 Git Bash 跑 `jq --version`；找不到就是 fail-open（印 `jq not found`），沒有保護。
- 行尾：`*.sh` 由 `.gitattributes` 固定成 LF；CRLF 的 `.sh` 會報 `$'\r': command not found`。ripgreprc 也要保持 LF。
- `RIPGREP_CONFIG_PATH` 寫 Windows 路徑，建議正斜線：`C:/Users/<user>/.claude/ripgreprc`（`rg` 是原生 exe，推測讀不懂 MSYS 的 `/c/Users/...`）。另外該機 `rg` 走 `WinGet\Links` symlink，Git Bash 開不了（見 `docs/hosts-detail.md`），ripgreprc 目前沒有東西可影響，hook 可先裝。
- 該機的 `settings.json` 要自己加同樣兩段。

### 選配：自動放行專案根目錄（預設 `$HOME/Projects/`）底下的 `git -C` 清理指令

`hooks/allow-git-c-projects.sh` 已由主安裝連好；要另外改 `~/.claude/settings.json` 才會生效。目的：permission 規則寫成 `Bash(git -C * worktree remove *)`、`Bash(git -C * branch -D *)` 時，Claude Code 啟動會警告子指令前的 `*` 也放行任意 option（例如 `git -C -c core.pager=...`、`--exec-path`），連 `git -C /Users/<user>/Projects/* ...` 也一樣報，逐 repo 寫確切路徑又太多條。這個 `PreToolUse` hook 是自己實作的嚴格版「專案根目錄前綴規則」（根目錄預設 `$HOME/Projects`，可用 `GIT_C_ALLOW_ROOT` 改，見下）：形狀全部符合才回 `permissionDecision: allow`，其餘一律不表態（exit 0、無輸出），交回正常 permission 流程。

放行條件（全部成立）：

- `tool_name` 是 `Bash`，command 去掉頭尾空白後只含 `A-Za-z0-9 _ . / : @ % + = ,` 與 `-`。
- 以空白切 token，恰為 `git -C <path> worktree remove <arg>…` 或 `git -C <path> branch -D <arg>…`，至少一個 `<arg>`，每個 `<arg>` 都不以 `-` 開頭。
- `<path>` 以 `<root>/` 開頭（絕對路徑；`<root>` 預設 `$HOME/Projects`）、其後的餘段不能只由 `.` 與 `/` 組成（`<root>/`、`<root>/.`、`<root>/./` 本身不放行）、沒有 `..` 段，且 `[ -d ]` 為真。

不放行（交回正常流程）的形狀：`;`、`&&`、`||`、`|`、反引號、`$`、`(`、換行、`>`、`<`、`#`、引號、反斜線、`~`、萬用字元；`-C<path>` 黏寫、`-c`、`--git-dir`、`--exec-path` 等任何其他 option 或前綴；路徑不存在、在 `<root>/` 外、就是 `<root>/` 本身（含 `.`、`./`）或含 `..`；`--force`、`-f` 等以 `-` 開頭的參數，所以 settings `deny` 裡的 `git worktree remove --force*` 不會被繞過（官方文件寫明 hook 回 allow 後 deny／ask 規則仍會評估，hook 輸出格式見腳本檔頭註解）。

**追加**到既有的 `hooks.PreToolUse` 陣列（不要取代 `block-ci-edit` 或其他元素；片段同樣收在 `<REPO>/global/claude/settings.snippets.json`）：

```json
{
  "matcher": "Bash",
  "hooks": [
    { "type": "command", "command": "bash \"$HOME/.claude/hooks/allow-git-c-projects.sh\"" }
  ]
}
```

裝完驗證（離線、需要 `jq`）：`bash tests/test-allow-git-c-projects.sh ~/.claude/hooks/allow-git-c-projects.sh`。設環境變數 `GIT_C_ALLOW_LOG=/path/to/file` 會逐筆 append 決定與原因（平常不設）；每行最後的 `root=default|env|default-invalid-env` 標示 `<root>` 來自預設、`GIT_C_ALLOW_ROOT`，或 `GIT_C_ALLOW_ROOT` 不合規而退回預設。

**改專案根目錄：`GIT_C_ALLOW_ROOT`**。專案不在 `$HOME/Projects`（例如 Windows 的 `D:/Projects`）時，在 `~/.claude/settings.json` 的 `env` 設這個變數；它**取代**預設根目錄（不是再加一個），所以設了之後 `$HOME/Projects/` 底下不再自動放行。

```json
{ "env": { "GIT_C_ALLOW_ROOT": "D:/Projects" } }
```

- 沒設或設成空字串：根目錄是 `${HOME%/}/Projects`，行為與沒有這個變數時完全相同（macOS 不必改任何東西）。
- 有設：先去掉結尾的 `/`，再全部成立才採用：只含 `A-Za-z0-9 _ . / : @ % + = ,` 與 `-`（不能有空白、反斜線、`~`、`$`）；是絕對路徑（以 `/` 開頭，或以 `X:/` 開頭，`X` 是磁碟機代號）；沒有 `..` 段也沒有 `.` 段；去掉開頭的 `/` 或 `X:/` 後還有內容（`/`、`//`、`C:/`、`C:` 都不行）。**任一不成立就退回預設根目錄**（不是關掉 hook，也不會放寬）。
- 路徑是純字串比對：`<path>` 要和 `GIT_C_ALLOW_ROOT` 用同一種寫法。Windows 上設 `D:/Projects` 時，指令裡寫 `git -C D:/Projects/foo ...` 才放行；`D:\Projects\foo`（反斜線）和 `/d/Projects/foo` 寫法一律不表態、會跳出確認，不會誤放行。`GIT_C_ALLOW_ROOT` 本身寫成 `D:\Projects`（反斜線）會退回預設根目錄；寫成 `/d/Projects` 則被當成一般 POSIX 絕對路徑採用，指令也要用 `/d/Projects/...` 才放行。
- 離線測試涵蓋：有效根目錄取代預設根目錄、根目錄本身／`.`／`..` 不放行、結尾 `/` 等同不帶、無效值（`/`、`//`、相對路徑、含 `..` 或 `.` 段、含空白、`C:`、`C:/`、反斜線）退回預設、`C:/...` 寫法與 `/c/...` 寫法的差別（機器上有 `cygpath` 時才跑，否則印 `SKIP`），以及 audit log 的 `root=` 欄位。

**已知限制**：

- 只比對字串：不解析 symlink，`<root>/` 底下指向別處的 symlink 目錄仍會放行；放行的是「對該目錄跑這兩個指令」，不是「該目錄是 git repo」。`<arg>` 只檢查不以 `-` 開頭，不檢查它指向哪裡。
- 路徑含空白、非 ASCII 或上述字元集以外的字元，一律不表態（會跳 prompt），不會誤放行。
- 會被略過：`claude --bare`、`--setting-sources` 不含 user、`disableAllHooks`；略過時等於沒裝，指令回到正常 permission 流程。
- fail-open 語意：`jq` 不在 PATH 或 stdin 不是 JSON 時 exit 1（非阻擋錯誤，stderr 顯示 `auto-allow is INACTIVE`／`did not run`），不給 allow，工具照正常 permission 流程；不會因此多放行。
- 不和 `permissions.allow` 互斥：已有的 allow 規則照常生效，這個 hook 只多一條放行路徑。

### 選配：擋沒帶 `--model`／`--effort` 的 Claude issue session 啟動

`hooks/require-issue-session-model.sh` 已由主安裝連好；要另外改 `~/.claude/settings.json` 才會生效。目的：`global/shared/skills/parallel-dispatch/references/cli.md`「盤點 session 與 issue session」規定 issue session 一律 `--model claude-opus-5-5 --effort medium`，但這條只寫在 reference 裡，controller 沒載 skill 就看不到；沒帶旗標的 `claude` 吃的是啟動當下 `~/.claude/settings.json` 的 `model`（2026-10-27 四個 issue session 因此開成 Sonnet high 與 Fable）。這個 `PreToolUse` hook 把它變成機械擋板：Bash command 以換行、`;`、`&&`、`||`、`|` 切段，任一段含 `orca worktree create` 或 `orca agent launch` 且含 token `--agent claude`（或 `--agent=claude`、值加引號的寫法），就必須同段含 `--model <值>` 與 `--effort <值>`（`=` 寫法亦可），缺一即 exit 2、stderr 訊息指回 cli.md 與完整旗標；只檢查有沒有帶，值的政策留在 cli.md。`--agent codex`、沒有 `--agent` 的純 worktree、`orca terminal create`、其他指令與非 Bash 工具一律放行；`--prompt` 內文含 `&&` 不影響（旗標依文件順序寫在 `--prompt` 之前）。fail-open：`jq` 不在或 stdin 不是 JSON 時 exit 1、不擋。

**追加**到既有的 `hooks.PreToolUse` 陣列（不要取代其他元素；片段同樣收在 `<REPO>/global/claude/settings.snippets.json`）：

```json
{
  "matcher": "Bash",
  "hooks": [
    { "type": "command", "command": "bash \"$HOME/.claude/hooks/require-issue-session-model.sh\"" }
  ]
}
```

裝完驗證（離線、需要 `jq`）：`bash tests/test-require-issue-session-model.sh ~/.claude/hooks/require-issue-session-model.sh`。設 `ISSUE_SESSION_MODEL_LOG=/path/to/file` 會逐筆 append 決定與原因（平常不設）。

## 安裝 Codex

macOS／Linux，symlink 版。

```bash
# 備份既有設定
cp -r ~/.codex ~/.codex.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline   # macOS 主力機；其他機器見上方
link_one() {   # link_one <來源> <目的>；已存在就略過，不覆蓋
  if [ -e "$2" ] || [ -L "$2" ]; then echo "略過（已存在，需手動處理）：$2"; else ln -s "$1" "$2"; fi
}
mkdir -p ~/.codex/agents ~/.agents/skills
link_one "$REPO/global/codex/AGENTS.md" ~/.codex/AGENTS.md
for skill in dispatch handoff git-commit create-pr parallel-dispatch writing-principles; do
  link_one "$REPO/global/shared/skills/$skill" ~/.agents/skills/$skill
done

# Codex agent TOML：先預覽，再寫入實體 regular files
python3 "$REPO/scripts/sync-codex-agents.py" --destination "$HOME/.codex/agents"
python3 "$REPO/scripts/sync-codex-agents.py" --destination "$HOME/.codex/agents" --apply
```

不要把本 repo 的 `.md` symlink 到 `~/.codex/rules/`。Codex 的 `~/.codex/rules/*.rules` 是命令權限規則（Starlark），不是 Markdown 工作守則；Codex 入口 `AGENTS.md` 會直接指向本 repo 的 `global/codex/rules/` 與 `global/shared/rules/` 文件。

若要採用本制度推薦的低成本一般 coding 預設，可將下列設定合併進 `~/.codex/config.toml`；這是建議值，不是
runtime 證據。設定檔只反映預設；當前主 session 的 model／effort 以 runtime metadata 或 CLI header 為準：

```toml
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
```

特定困難任務可在 UI 或 CLI 當次明確選擇 Terra／Sol 與相應 effort；這不代表要改掉一般預設。global instruction 無法在已啟動的主對話中自動切換主 agent，實際可控點是 delegated agent、direct CLI 與下一個 session。

目前 Codex release 會從 `~/.codex/agents/*.toml` 探索 custom agents；這些檔案要用上方同步器安裝成實體 regular files，只有 `AGENTS.md` 與 skills 維持 symlink。repo 更新後先 dry-run，再執行 `python3 scripts/sync-codex-agents.py --apply`（Windows 用 `python`）；既有檔案內容不同時加上 `--update`，同步器會先把檔案或 symlink 備份到 `agents` 目錄外的唯一資料夾。不要預先替少數角色另寫 `[agents.<name>]`；若檔案已有 `[agents]`，只更新其中的並行設定，不可新增第二個 `[agents]` table；只有原本沒有時才新增整段。官方現行 key 是 `max_concurrent_threads_per_session`；`max_threads` 仍可讀取，但只是 legacy alias（見 [Codex subagents 設定](https://learn.chatgpt.com/docs/agent-configuration/subagents)）。

Codex subagent 並行與遞迴上限建議固定：

    [agents]
    max_concurrent_threads_per_session = 4
    max_depth = 1

`max_depth = 1` 的用意是把 subagent 遞迴限制在一層；調高前需重新評估 token、延遲與 working-tree 風險。此 key 以 Codex CLI 0.151.0 的 `--strict-config` 驗證可接受，但**沒有實跑 nested spawn 驗證其行為**，且公開 config reference 沒有列出，因此是本系統的實測相容設定，不是官方 canonical；新 CLI 若拒絕就移除，角色合約本身仍禁止 nested spawn。`codex exec --ephemeral --sandbox read-only` 是單體 fresh reviewer 的 direct CLI 路徑；它直接驗收，不在該 ephemeral process nested spawn。

安裝後實際測一次 named spawn；清單列出角色或 TOML parse 通過不代表能建立。physical TOML 讓目前桌面與 fresh CLI 的 explorer named path 可重跑；named 建立與 model／effort 的 child metadata 仍要以實際工具證據確認。沒有永久 config registration；證據、限制與用法見 `docs/reviews/codex-named-agent-registration.md`，不可用時仍依 runtime adapter 的 permission gate 選 fallback。

Codex 的三個層次要分開看：standalone `~/.codex/agents/*.toml` 只提供角色設定與註冊來源；named role runtime 只有在當前 surface 明確選中並取得證據時才算套用；named unavailable 時由 runtime adapter 選擇實際 `agent_type=default` 或 direct CLI，並加上 `global/codex/rules/delegation-templates.md` 的 adapter envelope 與完整 logical-role contract，再明確傳入 mapping 的 model／effort。generic spawn 要 override model／effort 時，`fork_turns` 必須是 `none` 或正整數，不能用 full-history fork。permission 分成 logical contract 與 runtime evidence：寫入角色可在父 session 權限涵蓋 approved scope 時用 `default`；read-only 角色只有 runtime 已是 read-only 時可用 `default`，否則改走 `codex exec --sandbox read-only`。generic／direct CLI 是可執行 fallback，不是 custom role；若 model／effort／permission 證據完整，可作獨立驗收，缺證據則標 runtime 未驗證、不能正式結案。

Codex Memories 是精選長期記憶層，需在 `~/.codex/config.toml` 啟用：

```toml
[features]
memories = true
```

兩個平台共用的六個 global skills：`dispatch` 負責派工、回報、升降級與驗收後修正，`handoff` 提供 brief、回報、verifier 判定、session 交接四張固定卡（session 卡預設寫專案根 `.agents/HANDOFF.md`），`git-commit` 定 commit message 格式與 squash merge 標題，`create-pr` 負責分析 branch 變更並準備 Pull Request，`parallel-dispatch` 處理多寫入切片的切分、派工與整合驗收（worktree 與 terminal 只是 adapter 層），`writing-principles` 提供長存文件（README、接入指南、設計說明、流程、參考頁、wiki 頁）的 12 條寫作原則、判定與純標準庫檢查腳本（`scripts/check_docs.py`），寫的人與 verifier 跑同一支。`maintain-guideline` 與 `usage-review` 是 repo-only：Claude 在本 repo 開工時自動可用，Codex 維護本 repo 時直接讀 `.claude/skills/maintain-guideline/SKILL.md`；`usage-review` 只解析 Claude Code 本機 session jsonl（`~/.claude/projects`），不裝到 Codex。除錯前的環境檢查清單是文件不是 skill：`docs/debug-environment-first.md`。這不是自動事件史；若未來需要像 Claude remember plugin 一樣的自動時間軸，再用 Codex hooks 補第二階段。

Codex 的 LSP／語意工具、plugin／skill context 盤點與瘦身，按需讀 `<REPO>/docs/reviews/codex-tooling-audit-2026-10.md`。

## 安裝（Windows／PowerShell）

> ⚠️ **這一段要用系統管理員的 PowerShell 跑。**
> Windows 在**建立** reparse point 的當下就依建立者的 token 蓋信任等級：非提權建的是 Level 1，啟用 RedirectionTrust 的行程一律拒絕走訪，回 `ERROR_UNTRUSTED_MOUNT_POINT`（os error 448）；admin 建的是 Level 2，誰都讀得到。非提權裝的話連結會全部建得起來、`LinkType`／`Target` read-back 也全綠，但 Claude Code 與 Codex 讀不到任何全域設定——「安裝全綠＋完全失效」。
> 在 `FatJohn-PC` 上實測確認（同一個目標檔，admin 建的讀得到、非 admin 建的 448）。Developer Mode 只決定「能不能建」，不決定「建出來能不能用」。
> **裝完一定要實際讀一個檔驗證**（`Get-Content "$HOME\.claude\CLAUDE.md" -TotalCount 1`），不要只查 `LinkType`。不能提權的機器改用下一節的實體檔同步。

一次裝好 Claude Code 與 Codex 兩側。**用系統管理員的 PowerShell 跑**（理由見上方警告）。Developer Mode 只是讓非提權也「建得起來」，建出來的是不受信任的 Level 1 連結，所以開不開 Developer Mode 都不影響這裡——提權才是關鍵。

```powershell
$REPO = 'D:\Projects\FatJohn\agents-guideline'   # 本機 repo 位置；其他機器見上方
$G = "$REPO\global"

# 備份會被取代的既有設定（只備份實際衝突的檔案，不整包複製 ~/.claude——裡面有大量 cache/sessions）
# 兩道保護缺一不可，否則同日重跑會用 symlink 蓋掉第一次跑時保存的那份真備份（$stamp 同一天相同），
# 使用者的原始設定永久消失，而事後 read-back 只查 LinkType，連結照樣全綠、看不出來。
$stamp = Get-Date -Format 'yyyy-MM-dd'
foreach ($f in "$HOME\.claude\CLAUDE.md", "$HOME\.codex\AGENTS.md") {
  $i = Get-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
  if (-not $i) { "無需備份（不存在）：$f"; continue }
  if ($i.LinkType -eq 'SymbolicLink') { "已是 symlink，不重複備份：$f"; continue }   # 保護一：已安裝過就不動
  $bak = "$f.bak-$stamp"
  if (Get-Item -LiteralPath $bak -Force -EA SilentlyContinue) { "備份已存在，停手請自行處理：$bak"; continue }  # 保護二：不覆蓋既有備份
  Move-Item -LiteralPath $f $bak      # 刻意不加 -Force
  "已備份：$f -> $bak"
}

function Link-One($src, $dst) {
  # 用 Get-Item -Force 而非 Test-Path：斷掉的 symlink 在 Test-Path 會回 False，會誤判成「不存在」而覆蓋失敗
  if (Get-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue) { "略過（已存在，需手動處理）：$dst"; return }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
  New-Item -ItemType SymbolicLink -Path $dst -Target $src | Out-Null
  "已連結：$dst -> $src"
}

# Claude Code
Link-One "$G\claude\CLAUDE.md"          "$HOME\.claude\CLAUDE.md"
Link-One "$G\shared\hosts\windows.md"   "$HOME\.claude\host-facts.md"   # 本機那份；其他機器換 hosts\<key>.md
Link-One "$G\shared\rules"              "$HOME\.claude\rules"
Link-One "$G\claude\route-card.md"      "$HOME\.claude\route-card.md"
Link-One "$G\shared\rubrics"            "$HOME\.claude\rubrics"
foreach ($a in 'worker','verifier') {
  Link-One "$G\claude\agents\$a.md" "$HOME\.claude\agents\$a.md"
}
# hook 與 ripgreprc（只連結檔案，settings.json 另外加，見上方「SessionStart hook」與「選配」段）
Link-One "$G\claude\hooks"              "$HOME\.claude\hooks"
Link-One "$G\claude\config\ripgreprc"   "$HOME\.claude\ripgreprc"
$skills = 'dispatch','handoff','git-commit','create-pr','parallel-dispatch','writing-principles'
foreach ($s in $skills) { Link-One "$G\shared\skills\$s" "$HOME\.claude\skills\$s" }

# Codex
Link-One "$G\codex\AGENTS.md" "$HOME\.codex\AGENTS.md"
foreach ($s in $skills) { Link-One "$G\shared\skills\$s" "$HOME\.agents\skills\$s" }

# Codex agent TOML：先預覽，再寫入實體 regular files
python "$REPO\scripts\sync-codex-agents.py" --destination "$HOME\.codex\agents"
python "$REPO\scripts\sync-codex-agents.py" --destination "$HOME\.codex\agents" --apply
```

指令可重跑：連結部分已存在就略過不覆蓋，備份部分已安裝過就整段跳過（見上方兩道保護）。Codex agent TOML 由同步器寫成實體 regular files；read-back 驗證時只確認 Claude／AGENTS／skills 的連結，agent TOML 另看同步器輸出與檔案 bytes：

```powershell
Get-ChildItem "$HOME\.claude","$HOME\.claude\agents","$HOME\.claude\skills","$HOME\.codex","$HOME\.codex\agents","$HOME\.agents\skills" -Force |
  Where-Object LinkType | Select-Object FullName, LinkType, @{n='Target';e={$_.Target}}
```

Windows 專屬注意：

- **目錄可用 symlink 或 junction，檔案只能用 symlink**——`~/.claude/CLAUDE.md` 這種跨磁碟的檔案不能用 hardlink（hardlink 不可跨磁碟區）。
- **Windows 檔名不分大小寫**：既有的 `~/.claude/claude.md` 與本 repo 的 `CLAUDE.md` 是同一個檔，所以上面腳本一定會動到它。跑完務必打開 `.bak-<日期>` 檔看一次——舊的全域 CLAUDE.md 若有值得保留的個人偏好，照 macOS 安裝段落「指令可重跑」後的說明手動併進 repo 的 `global/claude/CLAUDE.md`（腳本只負責搬開，不負責合併）。
- 上方 Codex 的 `~/.codex/config.toml` 合併說明（model／`[agents]`／`[features] memories`）**兩個平台都適用**，Windows 也要照做。

## 安裝實體檔同步版

**不能提權的機器**用這個。連結建得起來卻讀不到（Level 1／os error 448，見上方警告、`global/shared/hosts/windows.md` 與 `docs/hosts-detail.md`）而又拿不到 admin 時，改用同步器把 repo 寫成**實體檔複本**，裝的是跟 symlink 版同一份清單（上方「安裝對應」的所有列，除了 `~/.codex/agents/*.toml` 由另一支 `sync-codex-agents.py` 負責）：`global/shared/hosts/<key>.md`→`~/.claude/host-facts.md` 依平台自動選 `macos`／`windows`，`--host-key` 可覆寫；`hooks/` 與 `ripgreprc` 只寫檔，`settings.json` 仍要手動加（見上方「SessionStart hook」與「選配」）。

```bash
python scripts/sync-profile.py --prune                                  # 先預覽
python scripts/sync-profile.py --prune --apply --replace-symlinks       # 首次遷移：寫入
python scripts/sync-codex-agents.py --apply                             # Codex agent TOML 另一支
```

`--apply` 結束前會**逐檔開起來比對 bytes** 才算成功——在這類機器上「連結存在」不是證據，只有真的讀得到才是。既有檔案被取代前會先搬進同步器輸出的 `~/.claude.backup-*`；內容被手改過要覆蓋得再加 `--update`；`--prune` 只清掉「指向本 repo 但清單裡已經沒有」的舊連結，別人的連結與你自己建的檔不動。同步器遇到本次可捕捉的 move、write 或 read-back 失敗時會回復已搬開的項目與本次新建的檔案；若回復本身失敗，錯誤會保留可復原的 backup 目錄路徑。它不保證處理程序遭強制中止時的復原。

`--replace-symlinks` 是防呆閘門：只要計畫要把既有 symlink（或整棵 symlink 目錄）換成實體檔複本，`--apply` 沒帶這個旗標就會被 `SyncError` 擋下、不寫入任何東西——避免在其實是 symlink 安裝的機器（例如主力 Mac）上誤跑這支腳本，把整套 symlink 靜默換成複本。日常重跑（計畫裡已經沒有 migrate 動作）用 `python scripts/sync-profile.py --apply --update` 即可，不必再帶它。

⚠️ **代價：改了 repo 不會自動生效**。symlink 版改完即時生效，複本版要重跑 `python scripts/sync-profile.py --apply --update`。這條寫在 `global/shared/hosts/windows.md`。

## 從 v1 升級

v1 是舊目錄結構（repo 根目錄的 `rules/`、`rules-controller/`、`skills/`、`hosts/` 等）。切到本結構的機器要清掉舊安裝，否則 `~/.claude/rules/` 會同時載入舊的 `20-judgment.md` 與新的 `judgment.md`，主安裝迴圈也會因為「已存在」而略過全部舊連結。

| 舊安裝 | 處理 |
|---|---|
| `~/.claude/rules-controller` | 移除（內容已併入 dispatch skill 與 `route-card.md`） |
| `~/.claude/rules/{00-environment,05-hosts,10-dispatch,20-judgment,50-lessons}.md` | 移除 |
| `~/.claude/skills/{maintain-guideline,usage-review}` | 移除（改為 repo-only） |
| `~/.agents/skills/{maintain-guideline,session-handoff}` | 移除（`session-handoff` 由 `handoff` skill 取代） |
| `~/.claude/agents/worker-opus.md` | 移除（`worker-opus` 車道已刪） |

symlink 安裝：先列出所有指向 repo 的連結，確認清單後再刪（`echo` 換成 `rm`），然後重跑上方主安裝。`rm` 一條連結不會動到 repo。

```bash
REPO=~/Projects/FatJohn/agents-guideline
for l in ~/.claude/* ~/.claude/agents/* ~/.claude/skills/* ~/.codex/AGENTS.md ~/.agents/skills/*; do
  [ -L "$l" ] || continue
  case "$(readlink "$l")" in "$REPO"/*) echo "$l";; esac   # 確認清單後，把 echo 換成 rm
done
```

PowerShell（symlink）：同樣先只列出指向 repo 的連結，確認後再接 `Remove-Item`：`Get-ChildItem "$HOME\.claude","$HOME\.claude\agents","$HOME\.claude\skills","$HOME\.codex","$HOME\.agents\skills" -Force | Where-Object { $_.LinkType -and "$($_.Target)" -like "$REPO*" } | Select-Object FullName, Target`（`$REPO` 見上方 Windows 腳本）。

實體檔複本安裝：`python scripts/sync-profile.py` 預覽時會在最後列出 `legacy:` 開頭的舊項目（`--apply` 後再列一次）。同步器**只列出、不刪**這些複本；`--prune` 只會清掉指向本 repo 的舊 symlink。清單裡的項目用 `rm -r`（PowerShell 用 `Remove-Item -Recurse`）逐項刪掉，再 `--apply --update`。舊的 `~/.claude/rules` 若還是指向舊 repo 位置的 symlink，同步器會以 `foreign tree redirect` 擋下，先把該連結移走再重跑。
