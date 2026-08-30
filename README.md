# agents-guideline — 給 AI coding agent 的長期工作制度

一套裝進 `~/.claude/` 或 `~/.codex/` 就生效的工作系統：模型調度規則、判斷準則、驗收 rubric、驗收 agent、維護協議。目標：讓不同 coding agent 在這個環境都能穩定產出可驗證的工作品質。

設計背景：2026-07-06 由高階模型（Fable 5）一次性建立，供之後所有 session 長期沿用。結構借鏡自 `goad-dot-claude`；機器差異隔離在 `rules/05-hosts.md`（macOS 主力機＋Windows 桌機，新機器由 AI 探測建檔）。

寫作原則（2026-07-25 依 [Claude 5 世代的 context engineering 指南](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) 修正）：**寫這個環境的 gotcha 與授權邊界，不寫通用做事方法**。模型自己就會的判斷不寫成決策樹；自我文件化的介面（agent 定義）不附填空範例；同一條規則只留一個 canonical 位置；只有每次開工都需要的內容放進常駐的 `rules/`。原則是「規則越少代表模型越強」，不是「規則越多越安全」。

## 安裝 Claude Code（macOS／Linux，symlink 版，repo 即唯一事實來源）

> Windows 用 PowerShell 版，見下方「安裝（Windows／PowerShell）」。
> `REPO` 依機器而異，各機器的實際位置見 `rules/05-hosts.md`。

```bash
# 備份既有設定
cp -r ~/.claude ~/.claude.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline   # macOS 主力機；其他機器見 rules/05-hosts.md
mkdir -p ~/.claude/agents ~/.claude/skills
for pair in \
  "CLAUDE.md:$HOME/.claude/CLAUDE.md" \
  "rules:$HOME/.claude/rules" \
  "rubrics:$HOME/.claude/rubrics" \
  "skills/maintain-guideline:$HOME/.claude/skills/maintain-guideline" \
  "skills/create-pr:$HOME/.claude/skills/create-pr" \
  "skills/debug-environment-first:$HOME/.claude/skills/debug-environment-first"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done

for agent in verifier; do
  src="$REPO/agents/$agent.md"; dst="$HOME/.claude/agents/$agent.md"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done
```

指令可重跑（已存在就略過不覆蓋）。若「已存在」的是你自己的舊全域 CLAUDE.md，手動把本 repo 的路由表與鐵律段落合併進去，不要直接覆蓋。

symlink 的好處：session 依規則附加教訓、更新事實時直接改到 repo，git diff 一目了然，由使用者 review 後 commit。若遇到不跟隨 symlink 的工具，改用 `cp` 安裝並在每次改 repo 後重新複製。

⚠️ **`~/.claude/rules/` 是無條件常駐區**：Claude Code 會把該目錄下無 `paths` frontmatter 的 `*.md` 每 session 全文載入，付的是每個 session 的固定 context 成本。所以只有「每次開工都需要」的內容放 `rules/`；只在特定情境才用得到的長內容放 `skills/`（維護協議）、`rubrics/`（驗收判準）或 `docs/`（封存與情境化參考），這三個目錄不會自動載入。`~/.claude/rubrics` 雖然也是目錄 symlink，但 `rules/` 才是 Claude Code 的 memory 目錄，`rubrics/` 不會被自動載入。

## 安裝（Windows／PowerShell）

一次裝好 Claude Code 與 Codex 兩側。**前置條件：開啟 Developer Mode**（設定 → 系統 → 開發人員專用），否則建 symlink 需要 admin 權限。已開的話 `(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock').AllowDevelopmentWithoutDevLicense` 會回 1。實測 `FatJohn-PC` 上 Developer Mode 已開，非 admin 的 PowerShell 7 即可 `New-Item -ItemType SymbolicLink` 建立跨磁碟（C: → E:）的檔案與目錄連結。

```powershell
$REPO = 'E:\agents-guideline'   # 本機 repo 位置；其他機器見 rules/05-hosts.md

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
Link-One "$REPO\rules"                     "$HOME\.claude\rules"
Link-One "$REPO\rubrics"                   "$HOME\.claude\rubrics"
Link-One "$REPO\skills\maintain-guideline"       "$HOME\.claude\skills\maintain-guideline"
Link-One "$REPO\skills\create-pr"                "$HOME\.claude\skills\create-pr"
Link-One "$REPO\skills\debug-environment-first"  "$HOME\.claude\skills\debug-environment-first"
foreach ($a in 'verifier') {
  Link-One "$REPO\agents\$a.md" "$HOME\.claude\agents\$a.md"
}

# Codex
Link-One "$REPO\AGENTS.md" "$HOME\.codex\AGENTS.md"
foreach ($a in 'scanner','explorer','planner','worker','pro_worker','recovery_worker','reviewer',
               'escalation_planner','escalation_worker','verifier','sol_verifier') {
  Link-One "$REPO\codex\agents\$a.toml" "$HOME\.codex\agents\$a.toml"
}
Link-One "$REPO\codex\skills\session-handoff"    "$HOME\.agents\skills\session-handoff"
Link-One "$REPO\skills\create-pr"                "$HOME\.agents\skills\create-pr"
Link-One "$REPO\skills\maintain-guideline"       "$HOME\.agents\skills\maintain-guideline"
Link-One "$REPO\skills\debug-environment-first"  "$HOME\.agents\skills\debug-environment-first"
```

指令可重跑：連結部分已存在就略過不覆蓋，備份部分已安裝過就整段跳過（見上方兩道保護）。read-back 驗證：

```powershell
Get-ChildItem "$HOME\.claude","$HOME\.claude\agents","$HOME\.claude\skills","$HOME\.codex","$HOME\.codex\agents","$HOME\.agents\skills" -Force |
  Where-Object LinkType | Select-Object FullName, LinkType, @{n='Target';e={$_.Target}}
```

Windows 專屬注意：

- **目錄可用 symlink 或 junction，檔案只能用 symlink**——`~/.claude/CLAUDE.md` 這種跨磁碟的檔案不能用 hardlink（hardlink 不可跨磁碟區）。
- **Windows 檔名不分大小寫**：既有的 `~/.claude/claude.md` 與本 repo 的 `CLAUDE.md` 是同一個檔，所以上面腳本一定會動到它。跑完務必打開 `.bak-<日期>` 檔看一次——舊的全域 CLAUDE.md 若有值得保留的個人偏好，照 macOS 安裝段落「指令可重跑」後的說明手動併進 repo 的 `CLAUDE.md`（腳本只負責搬開，不負責合併）。
- 底下 Codex 的 `~/.codex/config.toml` 合併說明（model／`[agents]`／`[features] memories`）**兩個平台都適用**，Windows 也要照做。

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

for agent in scanner explorer planner worker pro_worker recovery_worker reviewer escalation_planner escalation_worker verifier sol_verifier; do
  src="$REPO/codex/agents/$agent.toml"; dst="$HOME/.codex/agents/$agent.toml"
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
  "skills/debug-environment-first:debug-environment-first"; do
  src="$REPO/${pair%%:*}"; dst="$HOME/.agents/skills/${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done
```

不要把本 repo 的 `rules/*.md` symlink 到 `~/.codex/rules/`。Codex 的 `~/.codex/rules/*.rules` 是命令權限規則（Starlark），不是 Markdown 工作守則；Codex 入口 `AGENTS.md` 會直接指向本 repo 的 `rules/` 文件。

請將下列設定合併進 `~/.codex/config.toml`。主對話 default 依 `rules/00-environment.md` 的已查證訂閱事實選一組，不要同時保留兩組：

```toml
# Plus
model = "gpt-5.6-sol"
model_reasoning_effort = "medium"

# Pro（升級方案後用這組取代上面兩行；同型號拉高 effort）
# model = "gpt-5.6-sol"
# model_reasoning_effort = "xhigh"
```

若檔案已有 `[agents]`，只更新其中的 `max_threads` 與 `max_depth`，不可新增第二個 `[agents]` table；只有原本沒有 `[agents]` 時才新增整段。下面三個 `[agents.<name>]` 也採相同合併規則：table 已存在就只核對或更新其中的 `description` 與 `config_file`，不存在才新增，不可重複宣告。Codex CLI 0.149.1 若未自動接受 `~/.codex/agents/*.toml` 角色，可用對應的 `[agents.<name>]` 與 `config_file` 作相容性註冊；這只是 standalone TOML／註冊層，不等於 runtime 已選中 named role。

Codex subagent 並行與遞迴上限建議固定：

    [agents]
    max_threads = 4
    max_depth = 1

    [agents.reviewer]
    description = "Terra high 唯讀 reviewer。用 fresh context 做一般實作的對抗式 read-back review。"
    config_file = "agents/reviewer.toml"

    [agents.verifier]
    description = "Terra high fresh-context 一般驗收審查者。用於檔案產出的 read-back 驗證。"
    config_file = "agents/verifier.toml"

    [agents.sol_verifier]
    description = "Sol high 高風險 fresh-context 驗收者。只處理安全、不可逆、重大架構與正式高風險驗收。"
    config_file = "agents/sol_verifier.toml"

`max_depth = 1` 禁止 subagent 再往下遞迴派工；調高前需重新評估 token、延遲與 working-tree 風險。`codex exec --ephemeral --sandbox read-only` 是單體 fresh reviewer 的 direct CLI 路徑；它直接驗收，不在該 ephemeral process nested spawn。

合併後要在全新 CLI session 檢查當前 surface 實際提供的 named `agent_type`，並另以實際 `agent_type=default` 測試 adapter 需要的 model／effort mapping（例如 Luna/max、Terra/high、Sol/high）；不要求把三種 verifier 名稱當成可用入口。TOML parse 通過、檔案存在或 surface 顯示角色名稱都不等於 runtime 已接受該角色。若工具回覆 `agent type is currently not available`，依 `codex/rules/10-dispatch-codex.md` §0 的 named-first → `default` fallback 處理；generic child 不得冒充 custom role。

Codex 的三個層次要分開看：standalone `~/.codex/agents/*.toml` 只提供角色設定與註冊來源；named role runtime 只有在當前 surface 明確選中並取得證據時才算套用；named unavailable 時由 runtime adapter 選擇實際 `agent_type=default` 或 direct CLI，並加上 `codex/rules/30-delegation-templates-codex.md` 的 adapter envelope 與完整 logical-role contract，再明確傳入 mapping 的 model／effort。generic spawn 要 override model／effort 時，`fork_turns` 必須是 `none` 或正整數，不能用 full-history fork。permission 分成 logical contract 與 runtime evidence：寫入角色可在父 session 權限涵蓋 approved scope 時用 `default`；read-only 角色只有 runtime 已是 read-only 時可用 `default`，否則改走 `codex exec --sandbox read-only`。generic adapter 是可執行 fallback，不是 custom role；沒有 child metadata 就標記 runtime 未驗證。

Codex Memories 是精選長期記憶層，需在 `~/.codex/config.toml` 啟用：

```toml
[features]
memories = true
```

本 repo 另外提供四個 Codex 可用的 global skills：`session-handoff` 負責在收尾時產生可 review 的專案交接檔（預設 `.codex/HANDOFF.md`），`create-pr` 負責分析 branch 變更並準備 Pull Request，`maintain-guideline` 是修改本工作系統時要先讀的維護協議，`debug-environment-first` 負責除錯前確認環境事實與量測方法。這不是自動事件史；若未來需要像 Claude remember plugin 一樣的自動時間軸，再用 Codex hooks 補第二階段。

## 檔案結構

**每 session 自動載入**（固定 context 成本，只放每次都要的）：

| 檔案 | 用途 |
|------|------|
| `CLAUDE.md` | 路由表＋三鐵律＋優先權排序（裝在 `~/.claude/`） |
| `AGENTS.md` | Codex 路由表＋三鐵律＋Codex 專用注意（裝在 `~/.codex/`） |
| `rules/00-environment.md` | 跨機器事實、三大結構性風險與修法 |
| `rules/05-hosts.md` | 各機器事實（探測清單＋按機器分段；新機器由 AI 自行探測建檔） |
| `rules/10-dispatch.md` | Claude Code 調度：何時派 subagent、派工合約、回報合約、升降級路徑、驗證分工與 rubric 對應 |
| `rules/20-judgment.md` | 判斷準則：升級／完成／問使用者／換路／環境先驗，各附正反例 |
| `rules/50-lessons.md` | **還沒有正式判準承接的**活躍教訓＋交接欄 |

**用到才讀**（不在 `rules/`，故不自動載入）：

| 檔案 | 用途 |
|------|------|
| `skills/maintain-guideline/SKILL.md` | 系統維護協議：權限分級、修改流程、教訓寫回、瘦身與日落條款、路由完整性（原 `rules/40-maintenance.md`） |
| `skills/debug-environment-first/SKILL.md` | 除錯前的環境事實檢查清單＋量測方法自證陷阱（原 `rules/20-judgment.md` §6，2026-08-05 移出常駐區） |
| `rubrics/document-quality.md` | 文件類產出的逐條驗收判準（verifier 讀） |
| `rubrics/code-change.md` | 程式碼變更的逐條驗收判準（含殘留掃描與作假偵測） |
| `rubrics/research-analysis.md` | 研究／盤點類產出的逐條驗收判準 |
| `docs/lessons-archive.md` | 已升級成正式判準的歷史教訓（保留原文，作為判準來歷） |
| `docs/skill-catalog.md` | 各類任務用哪個 skill／plugin，含 Figma 在 MCP 缺席時的 curl fallback（原 `rules/00-environment.md` §好用的 skill／plugin，2026-08-12 移出常駐區） |
| `docs/harness-facts.md` | 查證過的 harness 事實（2026-08-22 從 00-environment 搬出，非常駐） |
| `docs/memory-layers.md` | 記憶機制四層的分工與邊界（2026-08-22 從 00-environment 搬出，非常駐） |
| `codex/rules/10-dispatch-codex.md` | Codex 調度：角色 mapping、named-first → `default` runtime adapter、reasoning effort、subagent 使用邊界、驗證不自驗 |
| `codex/rules/30-delegation-templates-codex.md` | Codex A–L 十二份 logical-role 派工模板與共用 adapter envelope（scanner 掃描；explorer repo 探索與外部研究；planner 規劃；worker 實作與重構；reviewer 一般 review；recovery_worker Terra recovery；escalation_planner 規劃升級；escalation_worker 升級實作；verifier 一般驗收；sol_verifier 高風險驗收） |
| `agents/verifier.md` | fresh-context 驗收 agent 定義（opus + effort high，對齊 Codex verifier/Terra high）。含「找碴範圍」與收斂標記；**高風險驗收用同一個角色、呼叫時指定 `model: fable`**，Claude 端不另設 agent 檔 |
| `codex/agents/scanner.toml` | Codex Luna/medium/read-only 精確掃描 agent |
| `codex/agents/explorer.toml` | Codex Terra/medium/read-only 探索 agent |
| `codex/agents/planner.toml` | Codex Terra/high/read-only 非平凡任務規劃 agent |
| `codex/agents/worker.toml` | Codex 所有訂閱檔位的 Luna/max/workspace-write 標準實作 agent；需完整 approved plan |
| `codex/agents/pro_worker.toml` | 相容性保留的 Terra/xhigh/workspace-write 實作 agent；只有使用者明確 override 時使用 |
| `codex/agents/recovery_worker.toml` | Codex Terra/xhigh/workspace-write 標準實作者失敗或揭露高風險後的 recovery 實作 agent |
| `codex/agents/reviewer.toml` | Codex Terra/high/read-only 一般實作 review agent |
| `codex/agents/escalation_planner.toml` | Codex Sol/xhigh/read-only root-cause 規劃升級 agent |
| `codex/agents/escalation_worker.toml` | Codex Sol/xhigh/workspace-write recovery 仍失敗或確認需要 Sol 後的 root-cause 升級實作 agent |
| `codex/agents/verifier.toml` | Codex Terra/high/read-only 一般 fresh-context 驗收 agent |
| `codex/agents/sol_verifier.toml` | Codex Sol/high/read-only 高風險 fresh-context 驗收 agent |
| `codex/skills/session-handoff/SKILL.md` | Codex 收尾／交接 skill，產生專案 `.codex/HANDOFF.md` |
| `skills/create-pr/SKILL.md` | Codex／Claude 共用的 Pull Request 建立 skill |

`agents/*.md` 與 `codex/agents/*.toml` 是 standalone role 定義／設定；它們的正文只在該 named role 被派工時進入 subagent context（name／description 會出現在每 session 的可用 agent 清單裡）。named unavailable 時，generic adapter 仍須在 prompt 帶入 `30-delegation-templates-codex.md` 的完整 logical-role contract；`pro_worker` 明確重用 D 的 worker contract，只替換 Terra/xhigh mapping 與 explicit-override 門檻。TOML 安裝或角色名稱不能取代 runtime evidence。

**為什麼 Claude 側沒有 `scanner`／`explorer`／`planner`／`worker` 的等價 custom agent**：內建 `Explore`／`Plan`／`general-purpose` 加上逐次指定 `model` 已經涵蓋，且本制度不把 haiku 列入 active routing。Claude 側自建 agent 只補一個缺口——**Agent 呼叫無法逐次指定 effort**，所以 recovery／escalation／驗收這些需要綁定 effort 與行為合約的角色才需要獨立定義檔。（原為 `rules/10-dispatch.md` §0 註，2026-08-05 移出常駐區。）

**為什麼 Claude 側沒有派工模板檔、Codex 側有**：Claude 側的模板（原 `rules/30-delegation-templates.md`）在 2026-07-25 移除，內容併入 `rules/10-dispatch.md` §2 的派工合約與各 `agents/*.md` 的角色合約——填空模板對 Claude 5 世代是重複投入，且範例會窄化探索。Codex 側維持 `codex/rules/30-delegation-templates-codex.md`：它把 approved plan、寫入所有權、驗證命令與回報格式做成可核對欄位，避免 controller 只靠角色名稱推定 child 已取得完整脈絡。

Codex 所有訂閱檔位的一般升級路徑都是 `planner/Terra high → controller 核定 approved plan → worker/Luna max → recovery_worker/Terra xhigh → escalation_worker/Sol xhigh`。`pro_worker/Terra xhigh` 只為相容性保留，需使用者本 session 明確 override 才能使用。`Sol max` 僅保留給 controller 在 `Sol xhigh` 仍無法收斂或明確遇到最困難單一路徑時使用，`Sol Ultra` 僅用於可獨立平行的大型工作流。

Codex custom role 名稱使用底線，以符合目前 `spawn_agent.task_name` 的格式限制。安裝 TOML 不等於 runtime 已選中角色：派工前先看當前 surface 是否明確提供 `agent_type` 與該角色的 model／effort metadata；named 可用時優先選 named，unavailable 時依 `codex/rules/10-dispatch-codex.md` §0 以實際 `agent_type=default` 套用 logical-role contract。這些值只能揭露為「工具宣告值」；若工具回傳或 child metadata 另有 runtime 值，再升級為「runtime 已驗證」。沒有 metadata 就標「runtime 未驗證」，不得把 generic child 稱為 custom role。

## 三條鐵律

1. **無證據不得宣稱完成**——回報分級：已驗證（附測試輸出／CI 連結）／待 CI／未驗證
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。
3. **驗證不自驗**——一般文件與驗收優先派 named `verifier/Terra high`；named unavailable 時使用 sandbox 強制 read-only 的 Terra/high direct CLI，只有 runtime 已是 read-only 時才可用 `agent_type=default` + 完整 logical `verifier` contract。安全、不可逆、重大架構與正式高風險產出優先派 named `sol_verifier/Sol high`；generic Sol review 只作補強，仍標記未取得 custom `sol_verifier` 驗收／未驗證。

## 已知退化模式與預防（維護者必讀）

1. **儀式死**：模板照抄但驗收條件寫成空話 → 判準：另一個 agent 能不能只憑那句話判定過或不過；verifier 見到模糊條件直接 FAIL
2. **膨脹死**：每個坑都塞進規則 → 教訓只進 `rules/50-lessons.md`；升級成正式判準要走 `maintain-guideline` skill 的流程；行數／bytes 門檻觸發瘦身；升級落地後把該條教訓移進 `docs/lessons-archive.md`，不要讓同一件事在常駐區佔兩份
6. **常駐區膨脹死**：把只在特定情境用得到的長內容放進 `rules/` → 每個 session 都付固定成本。判準：這份內容是不是「每次開工都需要」？不是就放 `skills/`／`rubrics/`／`docs/`
7. **過度規格化死**：為模型本來就會做的判斷寫死決策樹、為自我文件化的介面附填空範例 → 規則互相衝突、模型多耗推理。日落條款（`maintain-guideline` skill §5）就是解法：規則是不是在講「這個環境的 gotcha」還是「通用做事方法」？後者刪掉
3. **過時死**：模型名/工具參數換了文件沒跟上，整套失去公信力 → 事實帶查證日期、90 天過期重核、爛一條修一條
4. **斷鏈死**：檔案改名路由指向不存在的路徑 → 改名前 `rg` 掃引用；斷鏈是 P0
5. **繞過死**：「這個任務很簡單不用照守則」→ 簡單任務正是 context 塞爆的起點；覺得規則不合理走流程提出，不准默默繞過

## 誠實條款：這套系統補不了的

拆解、模板、fresh-context 驗收能拉高**執行品質**；**品味與模糊題**（長期架構取捨、文案語氣、功能該不該存在）補不了。遇到時依序：沿用 repo 既有慣例 → 用可用的最強模型 → 產出多個候選讓使用者選 → 明說「這超出系統能保證的範圍」。
