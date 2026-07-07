# agents-guideline — 給 AI coding agent 的長期工作制度

一套裝進 `~/.claude/` 或 `~/.codex/` 就生效的工作系統：模型調度規則、判斷 rubric、派工模板、驗收 agent、維護協議。目標：讓不同 coding agent 在這個環境都能穩定產出可驗證的工作品質。

設計背景：2026-07-06 由高階模型（Fable 5）一次性建立，供之後所有 session 長期沿用。結構借鏡自 `goad-dot-claude`；機器差異隔離在 `rules/05-hosts.md`（macOS 主力機＋Windows 桌機，新機器由 AI 探測建檔）。寫作原則：「寫給最弱的執行者——具體、可執行、有判準、附正反例」。

## 安裝 Claude Code（symlink 版，repo 即唯一事實來源）

```bash
# 備份既有設定
cp -r ~/.claude ~/.claude.backup-$(date +%F) 2>/dev/null

REPO=~/Projects/FatJohn/agents-guideline
mkdir -p ~/.claude/agents
for pair in "CLAUDE.md:$HOME/.claude/CLAUDE.md" "rules:$HOME/.claude/rules" "agents/verifier.md:$HOME/.claude/agents/verifier.md"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  [ -e "$dst" ] && echo "略過（已存在，需手動處理）：$dst" || ln -s "$src" "$dst"
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
for pair in "AGENTS.md:$HOME/.codex/AGENTS.md" "codex/agents/verifier.toml:$HOME/.codex/agents/verifier.toml"; do
  src="$REPO/${pair%%:*}"; dst="${pair#*:}"
  [ -e "$dst" ] && echo "略過（已存在，需手動處理）：$dst" || ln -s "$src" "$dst"
done

mkdir -p ~/.agents/skills
for skill in session-handoff; do
  src="$REPO/codex/skills/$skill"; dst="$HOME/.agents/skills/$skill"
  [ -e "$dst" ] && echo "略過（已存在，需手動處理）：$dst" || ln -s "$src" "$dst"
done
```

不要把本 repo 的 `rules/*.md` symlink 到 `~/.codex/rules/`。Codex 的 `~/.codex/rules/*.rules` 是命令權限規則（Starlark），不是 Markdown 工作守則；Codex 入口 `AGENTS.md` 會直接指向本 repo 的 `rules/` 文件。

Codex Memories 是精選長期記憶層，需在 `~/.codex/config.toml` 啟用：

```toml
[features]
memories = true
```

本 repo 另外提供 `session-handoff` skill，負責在收尾時產生可 review 的專案交接檔（預設 `.codex/HANDOFF.md`）。這不是自動事件史；若未來需要像 Claude remember plugin 一樣的自動時間軸，再用 Codex hooks 補第二階段。

## 檔案結構

| 檔案 | 用途 |
|------|------|
| `CLAUDE.md` | 路由表＋三鐵律＋優先權排序，每 session 自動載入（裝在 `~/.claude/`） |
| `AGENTS.md` | Codex 路由表＋三鐵律＋Codex 專用注意（裝在 `~/.codex/`） |
| `rules/00-environment.md` | 跨機器事實、三大結構性風險與修法、記憶機制、查證過的 harness 事實 |
| `rules/05-hosts.md` | 各機器事實（探測清單＋按機器分段；新機器由 AI 自行探測建檔） |
| `rules/10-dispatch.md` | Claude Code 調度：何時派 subagent、派工三件套、回報合約、升降級路徑、驗證不自驗 |
| `rules/10-dispatch-codex.md` | Codex 調度：角色、reasoning effort、subagent 使用邊界、驗證不自驗 |
| `rules/20-judgment.md` | 判斷 rubric：升級／完成／問使用者／換路／品質底線，各附正反例 |
| `rules/30-delegation-templates.md` | Claude Code 五份派工模板（搜尋／實作／重構／研究／驗收） |
| `rules/30-delegation-templates-codex.md` | Codex 五份派工模板（explorer／worker／verifier 語彙） |
| `rules/40-maintenance.md` | 權限分級、修改流程、教訓寫回、瘦身、路由完整性 |
| `rules/50-lessons.md` | 教訓日誌（append-only）＋交接欄 |
| `agents/verifier.md` | fresh-context 驗收 agent 定義（sonnet + effort high） |
| `codex/agents/verifier.toml` | Codex fresh-context 驗收 custom agent 定義（high reasoning effort） |
| `codex/skills/session-handoff/SKILL.md` | Codex 收尾／交接 skill，產生專案 `.codex/HANDOFF.md` |

## 三條鐵律

1. **無證據不得宣稱完成**——回報分級：已驗證（附測試輸出／CI 連結）／待 CI／未驗證
2. **對外動作需本 session 明確授權**——訊息、郵件、merge PR、push 共享分支
3. **驗證不自驗**——驗收派 fresh-context 的 verifier，不用繼承脈絡的 agent

## 已知退化模式與預防（維護者必讀）

1. **儀式死**：模板照抄但驗收條件寫成空話 → 判準：另一個 agent 能不能只憑那句話判定過或不過；verifier 見到模糊條件直接 FAIL
2. **膨脹死**：每個坑都塞進規則 → 教訓只進 `50-lessons.md`；升級成正式判準要走 `40-maintenance.md` 流程；行數門檻觸發瘦身
3. **過時死**：模型名/工具參數換了文件沒跟上，整套失去公信力 → 事實帶查證日期、90 天過期重核、爛一條修一條
4. **斷鏈死**：檔案改名路由指向不存在的路徑 → 改名前 `rg` 掃引用；斷鏈是 P0
5. **繞過死**：「這個任務很簡單不用照守則」→ 簡單任務正是 context 塞爆的起點；覺得規則不合理走流程提出，不准默默繞過

## 誠實條款：這套系統補不了的

拆解、模板、fresh-context 驗收能拉高**執行品質**；**品味與模糊題**（長期架構取捨、文案語氣、功能該不該存在）補不了。遇到時依序：沿用 repo 既有慣例 → 用可用的最強模型 → 產出多個候選讓使用者選 → 明說「這超出系統能保證的範圍」。
