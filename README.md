# agents-guideline — 給 AI coding agent 的長期工作制度

一套裝進 `~/.claude/` 或 `~/.codex/` 就生效的工作系統：模型調度規則、判斷準則、驗收 rubric、驗收 agent、維護協議。目標：讓不同 coding agent 在這個環境都能穩定產出可驗證的工作品質。

設計背景：2026-07-06 由高階模型（Fable 5）一次性建立，供之後所有 session 長期沿用。結構借鏡自 `goad-dot-claude`；機器差異隔離在 `rules/05-hosts.md`（macOS 主力機＋Windows 桌機，新機器由 AI 探測建檔）。

寫作原則（2026-07-25 依 [Claude 5 世代的 context engineering 指南](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) 修正）：**寫這個環境的 gotcha 與授權邊界，不寫通用做事方法**。模型自己就會的判斷不寫成決策樹；自我文件化的介面（agent 定義）不附填空範例；同一條規則只留一個 canonical 位置；只有每次開工都需要的內容放進常駐的 `rules/`。原則是「規則越少代表模型越強」，不是「規則越多越安全」。

## 安裝 Claude Code（symlink 版，repo 即唯一事實來源）

```bash
# 備份既有設定
cp -r ~/.claude ~/.claude.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline
mkdir -p ~/.claude/agents ~/.claude/skills
for pair in \
  "CLAUDE.md:$HOME/.claude/CLAUDE.md" \
  "rules:$HOME/.claude/rules" \
  "rubrics:$HOME/.claude/rubrics" \
  "skills/maintain-guideline:$HOME/.claude/skills/maintain-guideline" \
  "skills/create-pr:$HOME/.claude/skills/create-pr"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done

for agent in verifier fable-verifier recovery-worker escalation-planner escalation-worker; do
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

⚠️ **`~/.claude/rules/` 是無條件常駐區**：Claude Code 會把該目錄下無 `paths` frontmatter 的 `*.md` 每 session 全文載入，付的是每個 session 的固定 context 成本。所以只有「每次開工都需要」的內容放 `rules/`；只在特定情境才用得到的長內容放 `skills/`（維護協議）、`rubrics/`（驗收判準）或 `docs/`（封存），這三個目錄不會自動載入。`~/.claude/rubrics` 雖然也是目錄 symlink，但 `rules/` 才是 Claude Code 的 memory 目錄，`rubrics/` 不會被自動載入。

## 安裝 Codex（symlink 版）

```bash
# 備份既有設定
cp -r ~/.codex ~/.codex.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline
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
  "skills/maintain-guideline:maintain-guideline"; do
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
model = "gpt-5.6-terra"
model_reasoning_effort = "high"

# Pro（升級方案後用這組取代上面兩行）
# model = "gpt-5.6-terra"
# model_reasoning_effort = "xhigh"
```

若檔案已有 `[agents]`，只更新其中的 `max_threads` 與 `max_depth`，不可新增第二個 `[agents]` table；只有原本沒有 `[agents]` 時才新增整段。

Codex subagent 並行與遞迴上限建議固定：

    [agents]
    max_threads = 4
    max_depth = 1

`max_depth = 1` 禁止 subagent 再往下遞迴派工；調高前需重新評估 token、延遲與 working-tree 風險。

Codex Memories 是精選長期記憶層，需在 `~/.codex/config.toml` 啟用：

```toml
[features]
memories = true
```

本 repo 另外提供三個 Codex 可用的 global skills：`session-handoff` 負責在收尾時產生可 review 的專案交接檔（預設 `.codex/HANDOFF.md`），`create-pr` 負責分析 branch 變更並準備 Pull Request，`maintain-guideline` 是修改本工作系統時要先讀的維護協議。這不是自動事件史；若未來需要像 Claude remember plugin 一樣的自動時間軸，再用 Codex hooks 補第二階段。

## 檔案結構

**每 session 自動載入**（固定 context 成本，只放每次都要的）：

| 檔案 | 用途 |
|------|------|
| `CLAUDE.md` | 路由表＋三鐵律＋優先權排序（裝在 `~/.claude/`） |
| `AGENTS.md` | Codex 路由表＋三鐵律＋Codex 專用注意（裝在 `~/.codex/`） |
| `rules/00-environment.md` | 跨機器事實、三大結構性風險與修法、記憶機制、查證過的 harness 事實 |
| `rules/05-hosts.md` | 各機器事實（探測清單＋按機器分段；新機器由 AI 自行探測建檔） |
| `rules/10-dispatch.md` | Claude Code 調度：何時派 subagent、派工合約、回報合約、升降級路徑、驗證分工與 rubric 對應 |
| `rules/20-judgment.md` | 判斷準則：升級／完成／問使用者／換路／環境先驗，各附正反例 |
| `rules/50-lessons.md` | **還沒有正式判準承接的**活躍教訓＋交接欄 |

**用到才讀**（不在 `rules/`，故不自動載入）：

| 檔案 | 用途 |
|------|------|
| `skills/maintain-guideline/SKILL.md` | 系統維護協議：權限分級、修改流程、教訓寫回、瘦身與日落條款、路由完整性（原 `rules/40-maintenance.md`） |
| `rubrics/document-quality.md` | 文件類產出的逐條驗收判準（verifier 讀） |
| `rubrics/code-change.md` | 程式碼變更的逐條驗收判準（含殘留掃描與作假偵測） |
| `rubrics/research-analysis.md` | 研究／盤點類產出的逐條驗收判準 |
| `docs/lessons-archive.md` | 已升級成正式判準的歷史教訓（保留原文，作為判準來歷） |
| `codex/rules/10-dispatch-codex.md` | Codex 調度：角色、reasoning effort、subagent 使用邊界、驗證不自驗 |
| `codex/rules/30-delegation-templates-codex.md` | Codex A–L 十二份派工模板（scanner 掃描；explorer repo 探索與外部研究；planner 規劃；worker 實作與重構；reviewer 一般 review；recovery_worker Terra recovery；escalation_planner 規劃升級；escalation_worker 升級實作；verifier 一般驗收；sol_verifier 高風險驗收） |
| `agents/verifier.md` | fresh-context 驗收 agent 定義（opus + effort high，對齊 Codex verifier/Terra high） |
| `agents/fable-verifier.md` | Claude Fable/high-risk fresh-context 驗收 agent（read-only） |
| `agents/recovery-worker.md` | Claude Opus/xhigh recovery 實作 agent（標準層實作者同一子任務兩次失敗或揭露高風險後接手，先建 root cause；同階時價值在 fresh context） |
| `agents/escalation-planner.md` | Claude Fable/xhigh/read-only 規劃升級 agent（Plan 或探索路徑/opus 無法建立可靠方案時） |
| `agents/escalation-worker.md` | Claude Fable/xhigh 最終升級實作 agent（recovery-worker 再兩次失敗或確認需要 Fable 能力後接手；opus 進場的能力天花板型失敗可直升） |
| `codex/agents/scanner.toml` | Codex Luna/medium/read-only 精確掃描 agent |
| `codex/agents/explorer.toml` | Codex Terra/medium/read-only 探索 agent |
| `codex/agents/planner.toml` | Codex Terra/high/read-only 非平凡任務規劃 agent |
| `codex/agents/worker.toml` | Codex Plus 檔位 Luna/max/workspace-write 實作 agent |
| `codex/agents/pro_worker.toml` | Codex Pro 檔位 Terra/xhigh/workspace-write 實作 agent；依失敗型態選 fresh Terra recovery 或 Sol escalation |
| `codex/agents/recovery_worker.toml` | Codex Terra/xhigh/workspace-write 標準實作者失敗或揭露高風險後的 recovery 實作 agent |
| `codex/agents/reviewer.toml` | Codex Terra/high/read-only 一般實作 review agent |
| `codex/agents/escalation_planner.toml` | Codex Sol/xhigh/read-only root-cause 規劃升級 agent |
| `codex/agents/escalation_worker.toml` | Codex Sol/xhigh/workspace-write recovery 仍失敗、確認需要 Sol，或 Pro Terra 能力天花板型失敗後的 root-cause 升級實作 agent |
| `codex/agents/verifier.toml` | Codex Terra/high/read-only 一般 fresh-context 驗收 agent |
| `codex/agents/sol_verifier.toml` | Codex Sol/high/read-only 高風險 fresh-context 驗收 agent |
| `codex/skills/session-handoff/SKILL.md` | Codex 收尾／交接 skill，產生專案 `.codex/HANDOFF.md` |
| `skills/create-pr/SKILL.md` | Codex／Claude 共用的 Pull Request 建立 skill |

`agents/*.md` 與 `codex/agents/*.toml` 的**正文**只在該角色被派工時進入該 subagent 的 context（name／description 會出現在每 session 的可用 agent 清單裡）。這是刻意的：每個角色需要哪些輸入、缺什麼就停、回報格式，寫在角色定義裡而不是派工守則裡——角色定義就是它的介面。

**為什麼 Claude 側沒有派工模板檔、Codex 側有**：Claude 側的模板（原 `rules/30-delegation-templates.md`）在 2026-07-25 移除，內容併入 `rules/10-dispatch.md` §2 的派工合約與各 `agents/*.md` 的角色合約——填空模板對 Claude 5 世代是重複投入，且範例會窄化探索。Codex 側維持 `codex/rules/30-delegation-templates-codex.md`：那份不會進 Claude 的 context（成本為零），且 Codex 端的 custom role runtime 尚未穩定套用角色合約（見 `rules/00-environment.md` 的 `agent_role:null` 觀察），模板仍在補這個缺口。

Codex Plus 的一般升級路徑是 `worker/Luna max → recovery_worker/Terra xhigh → escalation_worker/Sol xhigh`。Codex Pro 由 `pro_worker/Terra xhigh` 進場：context 汙染型或型態難辨走同階 fresh `recovery_worker/Terra xhigh`，能力天花板型可直升 `escalation_worker/Sol xhigh`。`Sol max` 僅保留給 controller 在 `Sol xhigh` 仍無法收斂或明確遇到最困難單一路徑時使用，`Sol Ultra` 僅用於可獨立平行的大型工作流。

Codex custom role 名稱使用底線，以符合目前 `spawn_agent.task_name` 的格式限制。安裝 TOML 不等於 runtime 已選中角色：派工後必須 read-back child metadata，只有 `agent_role` 明確等於指定角色才能宣稱其固定 model／effort／contract 生效；`agent_role:null` 時必須視為 generic child，停止該 custom routing 並標記模型未驗證。主力 Mac 的 Codex 0.144.4 collaboration v2 目前已實跑觀察到此限制，詳見 `rules/00-environment.md`。

## 三條鐵律

1. **無證據不得宣稱完成**——回報分級：已驗證（附測試輸出／CI 連結）／待 CI／未驗證
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。
3. **驗證不自驗**——一般文件與驗收派 fresh-context 的 `verifier/Terra high`；安全、不可逆、重大架構與正式高風險產出派 `sol_verifier/Sol high`，不用繼承脈絡的 agent

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
