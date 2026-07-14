# agents-guideline — 給 AI coding agent 的長期工作制度

一套裝進 `~/.claude/` 或 `~/.codex/` 就生效的工作系統：模型調度規則、判斷 rubric、派工模板、驗收 agent、維護協議。目標：讓不同 coding agent 在這個環境都能穩定產出可驗證的工作品質。

設計背景：2026-07-06 由高階模型（Fable 5）一次性建立，供之後所有 session 長期沿用。結構借鏡自 `goad-dot-claude`；機器差異隔離在 `rules/05-hosts.md`（macOS 主力機＋Windows 桌機，新機器由 AI 探測建檔）。寫作原則：「寫給最弱的執行者——具體、可執行、有判準、附正反例」。

## 安裝 Claude Code（symlink 版，repo 即唯一事實來源）

```bash
# 備份既有設定
cp -r ~/.claude ~/.claude.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline
mkdir -p ~/.claude/agents
for pair in "CLAUDE.md:$HOME/.claude/CLAUDE.md" "rules:$HOME/.claude/rules"; do
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

for agent in scanner explorer planner worker recovery-worker reviewer escalation-planner escalation-worker verifier sol-verifier; do
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
  "skills/create-pr:create-pr"; do
  src="$REPO/${pair%%:*}"; dst="$HOME/.agents/skills/${pair#*:}"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "略過（已存在，需手動處理）：$dst"
  else
    ln -s "$src" "$dst"
  fi
done
```

不要把本 repo 的 `rules/*.md` symlink 到 `~/.codex/rules/`。Codex 的 `~/.codex/rules/*.rules` 是命令權限規則（Starlark），不是 Markdown 工作守則；Codex 入口 `AGENTS.md` 會直接指向本 repo 的 `rules/` 文件。

請將下列設定合併進 `~/.codex/config.toml`。若檔案已有 `[agents]`，只更新其中的 `max_threads` 與 `max_depth`，不可新增第二個 `[agents]` table；只有原本沒有 `[agents]` 時才新增整段。

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

本 repo 另外提供兩個 Codex 可用的 global skills：`session-handoff` 負責在收尾時產生可 review 的專案交接檔（預設 `.codex/HANDOFF.md`），`create-pr` 負責分析 branch 變更並準備 Pull Request。這不是自動事件史；若未來需要像 Claude remember plugin 一樣的自動時間軸，再用 Codex hooks 補第二階段。

## 檔案結構

| 檔案 | 用途 |
|------|------|
| `CLAUDE.md` | 路由表＋三鐵律＋優先權排序，每 session 自動載入（裝在 `~/.claude/`） |
| `AGENTS.md` | Codex 路由表＋三鐵律＋Codex 專用注意（裝在 `~/.codex/`） |
| `rules/00-environment.md` | 跨機器事實、三大結構性風險與修法、記憶機制、查證過的 harness 事實 |
| `rules/05-hosts.md` | 各機器事實（探測清單＋按機器分段；新機器由 AI 自行探測建檔） |
| `rules/10-dispatch.md` | Claude Code 調度：何時派 subagent、派工三件套、回報合約、升降級路徑、驗證不自驗 |
| `codex/rules/10-dispatch-codex.md` | Codex 調度：角色、reasoning effort、subagent 使用邊界、驗證不自驗 |
| `rules/20-judgment.md` | 判斷 rubric：升級／完成／問使用者／換路／品質底線，各附正反例 |
| `rules/30-delegation-templates.md` | Claude Code 五份派工模板（搜尋／實作／重構／研究／驗收） |
| `codex/rules/30-delegation-templates-codex.md` | Codex A–L 十二份派工模板（scanner 掃描；explorer repo 探索與外部研究；planner 規劃；worker 實作與重構；reviewer 一般 review；recovery-worker Terra recovery；escalation-planner 規劃升級；escalation-worker 升級實作；verifier 一般驗收；sol-verifier 高風險驗收） |
| `rules/40-maintenance.md` | 權限分級、修改流程、教訓寫回、瘦身、路由完整性 |
| `rules/50-lessons.md` | 教訓日誌（append-only）＋交接欄 |
| `agents/verifier.md` | fresh-context 驗收 agent 定義（opus + effort high，對齊 Codex verifier/Terra high） |
| `agents/fable-verifier.md` | Claude Fable/high-risk fresh-context 驗收 agent（read-only） |
| `agents/recovery-worker.md` | Claude Opus/xhigh recovery 實作 agent（標準層實作者同一子任務兩次失敗或揭露高風險後接手，先建 root cause；同階時價值在 fresh context） |
| `agents/escalation-planner.md` | Claude Fable/xhigh/read-only 規劃升級 agent（Plan 或探索路徑/opus 無法建立可靠方案時） |
| `agents/escalation-worker.md` | Claude Fable/xhigh 最終升級實作 agent（recovery-worker 再兩次失敗或確認需要 Fable 能力後接手；opus 進場的能力天花板型失敗可直升） |
| `codex/agents/scanner.toml` | Codex Luna/medium/read-only 精確掃描 agent |
| `codex/agents/explorer.toml` | Codex Terra/medium/read-only 探索 agent |
| `codex/agents/planner.toml` | Codex Terra/high/read-only 非平凡任務規劃 agent |
| `codex/agents/worker.toml` | Codex Luna/max/workspace-write 實作 agent |
| `codex/agents/recovery-worker.toml` | Codex Terra/xhigh/workspace-write Luna 同一子任務兩次失敗或揭露高風險後的 recovery 實作 agent |
| `codex/agents/reviewer.toml` | Codex Terra/high/read-only 一般實作 review agent |
| `codex/agents/escalation-planner.toml` | Codex Sol/xhigh/read-only root-cause 規劃升級 agent |
| `codex/agents/escalation-worker.toml` | Codex Sol/xhigh/workspace-write Luna 兩次失敗且 Terra recovery 再兩次失敗或確認 root cause 需要 Sol 能力後的 root-cause 升級實作 agent |
| `codex/agents/verifier.toml` | Codex Terra/high/read-only 一般 fresh-context 驗收 agent |
| `codex/agents/sol-verifier.toml` | Codex Sol/high/read-only 高風險 fresh-context 驗收 agent |
| `codex/skills/session-handoff/SKILL.md` | Codex 收尾／交接 skill，產生專案 `.codex/HANDOFF.md` |
| `skills/create-pr/SKILL.md` | Codex／Claude 共用的 Pull Request 建立 skill |

Codex 的一般升級路徑是 `Luna max → Terra xhigh → Sol xhigh`；`Sol max` 僅保留給 controller 在 `Sol xhigh` 仍無法收斂或明確遇到最困難單一路徑時使用，`Sol Ultra` 僅用於可獨立平行的大型工作流。

## 三條鐵律

1. **無證據不得宣稱完成**——回報分級：已驗證（附測試輸出／CI 連結）／待 CI／未驗證
2. **對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。
3. **驗證不自驗**——一般文件與驗收派 fresh-context 的 `verifier/Terra high`；安全、不可逆、重大架構與正式高風險產出派 `sol-verifier/Sol high`，不用繼承脈絡的 agent

## 已知退化模式與預防（維護者必讀）

1. **儀式死**：模板照抄但驗收條件寫成空話 → 判準：另一個 agent 能不能只憑那句話判定過或不過；verifier 見到模糊條件直接 FAIL
2. **膨脹死**：每個坑都塞進規則 → 教訓只進 `50-lessons.md`；升級成正式判準要走 `40-maintenance.md` 流程；行數門檻觸發瘦身
3. **過時死**：模型名/工具參數換了文件沒跟上，整套失去公信力 → 事實帶查證日期、90 天過期重核、爛一條修一條
4. **斷鏈死**：檔案改名路由指向不存在的路徑 → 改名前 `rg` 掃引用；斷鏈是 P0
5. **繞過死**：「這個任務很簡單不用照守則」→ 簡單任務正是 context 塞爆的起點；覺得規則不合理走流程提出，不准默默繞過

## 誠實條款：這套系統補不了的

拆解、模板、fresh-context 驗收能拉高**執行品質**；**品味與模糊題**（長期架構取捨、文案語氣、功能該不該存在）補不了。遇到時依序：沿用 repo 既有慣例 → 用可用的最強模型 → 產出多個候選讓使用者選 → 明說「這超出系統能保證的範圍」。
