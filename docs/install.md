# 安裝 Claude Code／Codex

> 本檔是 `README.md` 安裝入口指向的完整安裝步驟：Claude Code（macOS／Linux）→ Codex（macOS／Linux）→ Windows（PowerShell，兩側一起裝）→ 實體檔同步版（不能提權的機器）。

## 安裝 Claude Code（macOS／Linux，symlink 版，repo 即唯一事實來源）

> Windows 用 PowerShell 版，見下方「安裝（Windows／PowerShell）」。
> `REPO` 依機器而異，各機器的實際位置見 `rules/05-hosts.md`。

```bash
# 備份既有設定
cp -r ~/.claude ~/.claude.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline   # macOS 主力機；其他機器見 rules/05-hosts.md
mkdir -p ~/.claude/agents ~/.claude/skills
# hosts/<key>.md 只裝本機那份（主力 Mac 是 macos.md；其他機器換成自己的 key），CLAUDE.md 用 @~/.claude/host-facts.md 匯入
for pair in \
  "CLAUDE.md:$HOME/.claude/CLAUDE.md" \
  "hosts/macos.md:$HOME/.claude/host-facts.md" \
  "rules:$HOME/.claude/rules" \
  "rubrics:$HOME/.claude/rubrics" \
  "skills/maintain-guideline:$HOME/.claude/skills/maintain-guideline" \
  "skills/create-pr:$HOME/.claude/skills/create-pr" \
  "skills/parallel-dispatch:$HOME/.claude/skills/parallel-dispatch"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done

for agent in worker verifier; do
  src="$REPO/agents/$agent.md"; dst="$HOME/.claude/agents/$agent.md"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done
```

指令可重跑（已存在就略過不覆蓋）。若「已存在」的是你自己的舊全域 CLAUDE.md，手動把本 repo 的路由表與鐵律段落合併進去，不要直接覆蓋。

2026-10-09 起移除 `worker-opus` 車道（`agents/worker-opus.md` 已刪，本檔的 symlink 與實體檔同步兩種流程都不再裝它）：舊安裝要手動刪 `~/.claude/agents/worker-opus.md`——實體檔複本安裝的那份不會被 `scripts/sync-profile.py --prune` 清掉，因為 `plan_prunes` 只清指向本 repo 的 symlink（見其 docstring 與 `_is_repo_link`）；symlink 安裝的該連結會變成斷鏈，同樣直接刪掉即可。

裝完驗證本機事實真的被匯入（`@import` 缺檔是**靜默略過**，不會報錯）：`claude -p --allowed-tools "" <<< '不准用工具，引用 context 裡「# 本機事實」那段的標題與 hostname'`——回不出標題就是 `~/.claude/host-facts.md` 沒連上，或 CLAUDE.md 少了 `@~/.claude/host-facts.md` 那行。

symlink 的好處：session 依規則附加教訓、更新事實時直接改到 repo，git diff 一目了然，由使用者 review 後 commit。若遇到不跟隨 symlink 的工具，改用 `cp` 安裝並在每次改 repo 後重新複製。

⚠️ **`~/.claude/rules/` 是無條件常駐區**：Claude Code 會把該目錄下無 `paths` frontmatter 的 `*.md` 每 session 全文載入，付的是每個 session 的固定 context 成本。所以只有「每次開工都需要」的內容放 `rules/`；只在特定情境才用得到的長內容放 `skills/`（維護協議）、`rubrics/`（驗收判準）或 `docs/`（封存與情境化參考），這三個目錄不會自動載入。`~/.claude/rubrics` 雖然裝法與 `rules/` 相同（symlink 或實體檔複本），但 `rules/` 才是 Claude Code 的 memory 目錄，`rubrics/` 不會被自動載入。

### Claude Code permissions 要和鐵律二對齊

`CLAUDE.md` 是 advisory context，不是 permission gate。`~/.claude/settings.json` 的全域 allowlist 不要放 `Bash(git push:*)`、`Bash(gh pr:*)` 或 `Bash(gh api:*)` 這類同時涵蓋唯讀與對外寫入的 wildcard；否則 push、merge 或任意 GitHub API 寫入可能不會出現逐次權限確認。只預先允許可明確判定為唯讀的子命令，例如 `git status`／`git diff`／`git log` 與 `gh pr view`／`gh pr checks`／`gh pr diff`。需要零例外硬擋時使用 `PreToolUse` hook 驗證 Bash command；不要把「規則文字通常會被遵守」當成 deterministic enforcement（見 [Anthropic 的 steering 指南](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)）。本 repo 不管理 `settings.json`，新機器安裝後要另行 audit。

### 選配：擋主對話改 CI 設定的 hook 與 ripgrep 預設設定

兩個檔，裝法跟 `agents/*.md` 一樣是單檔 symlink；裝完要另外改 `~/.claude/settings.json` 才會生效（本 repo 不管理 `settings.json`）。

- `hooks/block-ci-edit.sh`：Claude Code `PreToolUse` hook。**主對話**（hook 收到的 stdin 沒有 `agent_id`）用 Edit／Write／MultiEdit／NotebookEdit 改路徑含 `.github/workflows/` 或 `.github/actions/` 的檔會被擋（exit 2，訊息要求改派 worker）；subagent（有 `agent_id`）與其他路徑一律放行。把 `rules/10-dispatch.md`「Controller 工作迴圈」那條「CI／release 設定不屬小修例外」變成機械擋板。
- `config/ripgreprc`：讓 **Bash 裡的 `rg`** 預設 `--hidden` 並排除 `.git`，對應 `rules/20-judgment.md` §2 的殘留掃描。Claude Code 的 Grep 工具本來就搜隱藏目錄（不搜 `.git`），也不讀 `RIPGREP_CONFIG_PATH`，所以這份設定只影響 Bash 的 `rg`。

安裝檔案（macOS／Linux；可重跑，已存在就略過）：

```bash
REPO=~/Projects/FatJohn/agents-guideline   # 其他機器見 rules/05-hosts.md
mkdir -p ~/.claude/hooks
for pair in \
  "hooks/block-ci-edit.sh:$HOME/.claude/hooks/block-ci-edit.sh" \
  "config/ripgreprc:$HOME/.claude/ripgreprc"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done
```

Windows 的這兩個 symlink 已在下方「安裝（Windows／PowerShell）」的腳本裡（`Link-One` 兩行）；不能提權的機器改跑 `python scripts/sync-profile.py --apply --update`（同步器已含這兩個檔，改了 hook 要重跑）。

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

裝完驗證（在本 repo 根目錄；前兩行離線、不需要 claude，`python3 -m unittest discover -s tests` 也會一起跑到）：

```bash
bash tests/test-block-ci-edit.sh ~/.claude/hooks/block-ci-edit.sh   # 13 個斷言，需要 jq
bash tests/test-ripgreprc.sh ~/.claude/ripgreprc                    # 4 個斷言，需要 rg
# 端到端：主對話應被擋、檔案不變（<abs path> 換成任一 git 目錄下的 .github/workflows/x.yml）
# ripgreprc 端到端：在 Claude Code 的 Bash 裡（讀 settings.json 的 env）不帶 --hidden 也要搜到隱藏目錄；印出 PATH OK 才算生效
claude -p "Run exactly: mkdir -p /tmp/rgchk/.h && echo rgtoken > /tmp/rgchk/.h/f && rg -l rgtoken /tmp/rgchk && echo PATH OK"
claude -p --disallowedTools=Bash "Use the Edit tool yourself to change 'name: x' to 'name: y' in <abs path>/.github/workflows/x.yml; quote any tool error verbatim."
```

**已知限制**：

- **Bash 改檔不經 hook**：`sed -i`、heredoc、`tee`、`git apply` 改 `.github/workflows` 都不會被擋（實測 `sed -i` 改成功）。hook 只補 Edit／Write 這條路，`rules/10-dispatch.md` 那條規則仍然要靠 controller 自己守。路徑只做字串比對，不解析 symlink。
- **CLI adapter 的 worker 也會被擋**：`skills/parallel-dispatch/references/cli.md` 用 `claude -p` 起的 worker 是頂層 session，hook 的 stdin 沒有 `agent_id`，判斷方式與主對話相同，改 `.github/workflows`／`.github/actions` 會被擋。裝了這個 hook 的機器，這類切片改用 Agent 工具派 `worker`，不走 CLI adapter。
- **使用者要求主對話直接改 CI 也會被擋**：hook 不分專案、不分誰下的指示。使用者在編輯器自己改不受影響；真要主對話改，只能暫時移除 `settings.json` 裡那個 `PreToolUse` 元素。`claude --agent <name>` 啟動的主執行緒同樣沒有 `agent_id`，會被當主對話擋。
- **hook 會被略過**：`claude --bare`、`--setting-sources` 不含 user、`disableAllHooks`。`jq` 不在 PATH 或 stdin 不是 JSON 時 hook fail-open（exit 1，非阻擋錯誤，工具照跑；transcript 會顯示 `CI edit guard is INACTIVE`／`did not run`）——等於沒裝，不會誤擋。
- **沒測過**：agent teams／teammate、`isolation: worktree` 的 subagent（預期同樣帶 `agent_id`），以及與其他 `*` hook 並存。
- **`--hidden` 不蓋過 gitignore**：`.worktrees/` 或被專案 `.gitignore` 排除的隱藏目錄仍搜不到，要 `--no-ignore`（會連 `node_modules` 一起進）。沒裝 ripgreprc 的機器（包含 Codex）Bash 的 `rg` 要手動加 `--hidden`。

**Windows（本段在 Windows 上全部未驗證）**：

- hook 在 Git Bash 執行，要用 `jq`。裝完先在 Git Bash 跑 `jq --version`；找不到就是 fail-open（印 `jq not found`），沒有保護。
- 行尾：`.gitattributes` 已把 `*.sh` 與 `config/ripgreprc` 固定成 LF；CRLF 的 `.sh` 會報 `$'\r': command not found`。
- `RIPGREP_CONFIG_PATH` 寫 Windows 路徑，建議正斜線：`C:/Users/<user>/.claude/ripgreprc`（`rg` 是原生 exe，推測讀不懂 MSYS 的 `/c/Users/...`）。另外該機 `rg` 走 `WinGet\Links` symlink，Git Bash 開不了（見 `docs/hosts-detail.md`），ripgreprc 目前沒有東西可影響，hook 可先裝。
- 該機的 `settings.json` 要自己加同樣兩段。

## 安裝 Codex（macOS／Linux，symlink 版）

```bash
# 備份既有設定
cp -r ~/.codex ~/.codex.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline   # macOS 主力機；其他機器見 rules/05-hosts.md
mkdir -p ~/.codex/agents
for pair in "AGENTS.md:$HOME/.codex/AGENTS.md"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done

mkdir -p ~/.agents/skills
for pair in \
  "codex/skills/session-handoff:session-handoff" \
  "skills/create-pr:create-pr" \
  "skills/maintain-guideline:maintain-guideline" \
  "skills/parallel-dispatch:parallel-dispatch"; do
  src="$REPO/${pair%%:*}"; dst="$HOME/.agents/skills/${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done

# Codex agent TOML：先預覽，再寫入實體 regular files
python3 "$REPO/scripts/sync-codex-agents.py" --destination "$HOME/.codex/agents"
python3 "$REPO/scripts/sync-codex-agents.py" --destination "$HOME/.codex/agents" --apply
```

不要把本 repo 的 `rules/*.md` symlink 到 `~/.codex/rules/`。Codex 的 `~/.codex/rules/*.rules` 是命令權限規則（Starlark），不是 Markdown 工作守則；Codex 入口 `AGENTS.md` 會直接指向本 repo 的 `rules/` 文件。

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

`max_depth = 1` 的用意是把 subagent 遞迴限制在一層；調高前需重新評估 token、延遲與 working-tree 風險。此 key 在 2026-08-31 以本機 Codex CLI 0.151.0 的 `--strict-config` 驗證可接受，但**本次沒有實跑 nested spawn 驗證其行為**，且目前公開 config reference 沒有列出，因此是本系統的實測相容設定，不是官方 canonical；新 CLI 若拒絕就移除，角色合約本身仍禁止 nested spawn。`codex exec --ephemeral --sandbox read-only` 是單體 fresh reviewer 的 direct CLI 路徑；它直接驗收，不在該 ephemeral process nested spawn。

安裝後實際測一次 named spawn；清單列出角色或 TOML parse 通過不代表能建立。physical TOML 讓目前桌面與 fresh CLI 的 explorer named path 可重跑；named 建立與 model／effort 的 child metadata 仍要以實際工具證據確認。沒有永久 config registration；證據、限制與用法見 `docs/codex-named-agent-registration.md`，不可用時仍依 runtime adapter 的 permission gate 選 fallback。

Codex 的三個層次要分開看：standalone `~/.codex/agents/*.toml` 只提供角色設定與註冊來源；named role runtime 只有在當前 surface 明確選中並取得證據時才算套用；named unavailable 時由 runtime adapter 選擇實際 `agent_type=default` 或 direct CLI，並加上 `codex/rules/30-delegation-templates-codex.md` 的 adapter envelope 與完整 logical-role contract，再明確傳入 mapping 的 model／effort。generic spawn 要 override model／effort 時，`fork_turns` 必須是 `none` 或正整數，不能用 full-history fork。permission 分成 logical contract 與 runtime evidence：寫入角色可在父 session 權限涵蓋 approved scope 時用 `default`；read-only 角色只有 runtime 已是 read-only 時可用 `default`，否則改走 `codex exec --sandbox read-only`。generic／direct CLI 是可執行 fallback，不是 custom role；若 model／effort／permission 證據完整，可作獨立驗收，缺證據則標 runtime 未驗證、不能正式結案。

Codex Memories 是精選長期記憶層，需在 `~/.codex/config.toml` 啟用：

```toml
[features]
memories = true
```

本 repo 另外提供四個 Codex 可用的 global skills：`session-handoff` 負責在收尾時產生可 review 的專案交接檔（預設 `.codex/HANDOFF.md`），`create-pr` 負責分析 branch 變更並準備 Pull Request，`maintain-guideline` 是修改本工作系統時要先讀的維護協議，`parallel-dispatch` 處理多寫入切片的切分、派工與整合驗收（worktree 與 terminal 只是 adapter 層）。除錯前的環境檢查清單是文件不是 skill：`docs/debug-environment-first.md`（2026-09-02 降級，理由見該檔檔頭）。這不是自動事件史；若未來需要像 Claude remember plugin 一樣的自動時間軸，再用 Codex hooks 補第二階段。

## 安裝（Windows／PowerShell）

> ⚠️ **這一段要用系統管理員的 PowerShell 跑。**
> Windows 在**建立** reparse point 的當下就依建立者的 token 蓋信任等級：非提權建的是 Level 1，啟用 RedirectionTrust 的行程一律拒絕走訪，回 `ERROR_UNTRUSTED_MOUNT_POINT`（os error 448）；admin 建的是 Level 2，誰都讀得到。非提權裝的話連結會全部建得起來、`LinkType`／`Target` read-back 也全綠，但 Claude Code 與 Codex 讀不到任何全域設定——「安裝全綠＋完全失效」。
> 2026-09-20 在 `FatJohn-PC` 上實測確認（同一個目標檔，admin 建的讀得到、非 admin 建的 448）。Developer Mode 只決定「能不能建」，不決定「建出來能不能用」。
> **裝完一定要實際讀一個檔驗證**（`Get-Content "$HOME\.claude\CLAUDE.md" -TotalCount 1`），不要只查 `LinkType`。不能提權的機器改用下一節的實體檔同步。

一次裝好 Claude Code 與 Codex 兩側。**用系統管理員的 PowerShell 跑**（理由見上方警告）。Developer Mode 只是讓非提權也「建得起來」，建出來的是不受信任的 Level 1 連結，所以開不開 Developer Mode 都不影響這裡——提權才是關鍵。

```powershell
$REPO = 'D:\Projects\FatJohn\agents-guideline'   # 本機 repo 位置；其他機器見 rules/05-hosts.md

# 備份會被取代的既有設定（只備份實際衝突的檔案，不整包複製 ~/.claude——裡面有大量 cache/sessions）
# 兩道保護缺一不可，否則同日重跑會用 symlink 蓋掉第一次跑時保存的那份真備份（$stamp 同一天相同），
# 使用者的原始設定永久消失，而事後 read-back 只查 LinkType，25 條連結照樣全綠、看不出來。
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
Link-One "$REPO\CLAUDE.md"                 "$HOME\.claude\CLAUDE.md"
Link-One "$REPO\hosts\windows.md"          "$HOME\.claude\host-facts.md"   # 本機那份；其他機器換 hosts\<key>.md
Link-One "$REPO\rules"                     "$HOME\.claude\rules"
Link-One "$REPO\rubrics"                   "$HOME\.claude\rubrics"
Link-One "$REPO\skills\maintain-guideline"       "$HOME\.claude\skills\maintain-guideline"
Link-One "$REPO\skills\create-pr"                "$HOME\.claude\skills\create-pr"
Link-One "$REPO\skills\parallel-dispatch"        "$HOME\.claude\skills\parallel-dispatch"
foreach ($a in 'worker','verifier') {
  Link-One "$REPO\agents\$a.md" "$HOME\.claude\agents\$a.md"
}
# 選配的 hook 與 ripgreprc（只連結檔案，settings.json 另外加，見上方「選配」段）
Link-One "$REPO\hooks\block-ci-edit.sh" "$HOME\.claude\hooks\block-ci-edit.sh"
Link-One "$REPO\config\ripgreprc"       "$HOME\.claude\ripgreprc"

# Codex
Link-One "$REPO\AGENTS.md" "$HOME\.codex\AGENTS.md"
Link-One "$REPO\codex\skills\session-handoff"    "$HOME\.agents\skills\session-handoff"
Link-One "$REPO\skills\create-pr"                "$HOME\.agents\skills\create-pr"
Link-One "$REPO\skills\maintain-guideline"       "$HOME\.agents\skills\maintain-guideline"
Link-One "$REPO\skills\parallel-dispatch"        "$HOME\.agents\skills\parallel-dispatch"

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
- **Windows 檔名不分大小寫**：既有的 `~/.claude/claude.md` 與本 repo 的 `CLAUDE.md` 是同一個檔，所以上面腳本一定會動到它。跑完務必打開 `.bak-<日期>` 檔看一次——舊的全域 CLAUDE.md 若有值得保留的個人偏好，照 macOS 安裝段落「指令可重跑」後的說明手動併進 repo 的 `CLAUDE.md`（腳本只負責搬開，不負責合併）。
- 上方 Codex 的 `~/.codex/config.toml` 合併說明（model／`[agents]`／`[features] memories`）**兩個平台都適用**，Windows 也要照做。

## 安裝（實體檔同步版——不能提權的機器用這個）

**不能提權的機器**用這個。連結建得起來卻讀不到（Level 1／os error 448，見上方警告、`hosts/windows.md` 與 `docs/hosts-detail.md`）而又拿不到 admin 時，改用同步器把 repo 寫成**實體檔複本**，裝的是跟 symlink 版同一份清單（`CLAUDE.md`、`hosts/<key>.md`→`~/.claude/host-facts.md`（依平台自動選 `macos`／`windows`，`--host-key` 可覆寫）、`rules/`、`rubrics/`、`agents/worker.md`＋`verifier.md`、三個共用 skill、`AGENTS.md`、`session-handoff`，以及上方「選配」段的 `hooks/` 與 `config/ripgreprc`；後兩者只寫檔，`settings.json` 仍要手動加）：

```bash
python scripts/sync-profile.py --prune                                  # 先預覽
python scripts/sync-profile.py --prune --apply --replace-symlinks       # 首次遷移：寫入
python scripts/sync-codex-agents.py --apply                             # Codex agent TOML 另一支
```

`--apply` 結束前會**逐檔開起來比對 bytes** 才算成功——在這類機器上「連結存在」不是證據，只有真的讀得到才是。既有檔案被取代前會先搬進同步器輸出的 `~/.claude.backup-*`；內容被手改過要覆蓋得再加 `--update`；`--prune` 只清掉「指向本 repo 但清單裡已經沒有」的舊連結，別人的連結與你自己建的檔不動。同步器遇到本次可捕捉的 move、write 或 read-back 失敗時會回復已搬開的項目與本次新建的檔案；若回復本身失敗，錯誤會保留可復原的 backup 目錄路徑。它不保證處理程序遭強制中止時的復原。

`--replace-symlinks` 是防呆閘門：只要計畫要把既有 symlink（或整棵 symlink 目錄）換成實體檔複本，`--apply` 沒帶這個旗標就會被 `SyncError` 擋下、不寫入任何東西——避免在其實是 symlink 安裝的機器（例如主力 Mac）上誤跑這支腳本，把整套 symlink 靜默換成複本。日常重跑（計畫裡已經沒有 migrate 動作）用 `python scripts/sync-profile.py --apply --update` 即可，不必再帶它。

⚠️ **代價：改了 repo 不會自動生效**。symlink 版改完即時生效，複本版要重跑 `python scripts/sync-profile.py --apply --update`。這條寫在 `hosts/windows.md`。
