# 檔案結構

讀者：想查某個檔案的用途、或某個角色設計理由的維護者與 agent。

型別：參考

> 完整檔案表與各角色的設計說明。`README.md`／`README.zh-TW.md` 的目錄地圖只列頂層目錄，逐檔用途看這裡。安裝對應（哪個檔裝到 `~/.claude`、`~/.codex`、`~/.agents` 的哪裡）在 `docs/install.md`「安裝對應」。

repo 根目錄的 `CLAUDE.md`／`AGENTS.md` 是本 repo 自己的專案規格（怎麼維護這個 repo），內容相同、改一邊同步另一邊，不是全域入口；全域入口在 `global/`。

## Claude 每 session 自動載入

固定 context 成本，只放每次都要的。

| 檔案 | 用途 |
|------|------|
| `global/claude/CLAUDE.md` | 全域入口：邊界六條、路由表、Bootstrap；以 `@~/.claude/host-facts.md` 匯入本機事實（裝在 `~/.claude/CLAUDE.md`） |
| `global/shared/hosts/<key>.md` | 單機事實（身分、驗證能力、環境陷阱），**每台機器只裝自己那份**到 `~/.claude/host-facts.md`；新機器由 AI 照 `docs/new-host.md`「新機器建檔」建檔 |
| `global/shared/rules/judgment.md` | 判斷準則：15 條編號規則（完成的條件、殘留掃描、驗收停止端、可證偽宣稱、放寬防線、除錯前驗環境等），裝在 `~/.claude/rules/`；訂條理由與正反例在 `docs/judgment-rationale.md` |
| `global/claude/route-card.md` | controller 路由卡（何時必須派工、角色表、brief 必含欄位、指向 dispatch skill）；由 SessionStart hook 只注入主對話，subagent 不繼承 |

## 按需

不自動載入，用到才讀。

| 檔案 | 用途 |
|------|------|
| `global/shared/skills/dispatch/SKILL.md` | 派工、驗收與升降級：何時派工、角色與模型、派工合約、回報合約、升降級、驗證不自驗、修正與驗收輪次、何時問使用者、工作目錄安全、主對話不做粗活 |
| `global/shared/skills/handoff/SKILL.md` | 四張固定卡：brief 卡、回報卡、verifier 判定卡、session 交接卡 |
| `global/shared/skills/git-commit/SKILL.md` | commit message 固定格式與 squash merge 標題；專案規格有自己的慣例時以專案為準 |
| `global/shared/skills/create-pr/SKILL.md` | 分析 branch 變更並準備 Pull Request |
| `global/shared/skills/parallel-dispatch/SKILL.md` | 多寫入切片的平行 orchestration（切分、派工、整合驗收）；`references/templates.md`（brief／report 格式）、`worktree.md`（隔離與清理）、execution adapter `claude-code.md`／`codex.md`／`cli.md`（純 shell、tmux、VS Code、Herdr、Orca 等外部 CLI process） |
| `global/shared/skills/writing-principles/SKILL.md` | 長存文件（README、接入指南、設計說明、流程、參考頁、wiki 頁）的 12 條寫作原則；`scripts/check_docs.py`（純標準庫）判機械項，其餘由 verifier 抽樣；`references/sources.md` 收出處短引、`references/examples.md` 收改寫前後片段 |
| `global/shared/rubrics/document-quality.md` | 文件類產出的逐條驗收判準（verifier 讀） |
| `global/shared/rubrics/code-change.md` | 程式碼變更的逐條驗收判準（含殘留掃描、作假偵測與失敗路徑） |
| `global/shared/rubrics/research-analysis.md` | 研究與盤點類產出的逐條驗收判準 |
| `global/claude/agents/worker.md` | 標準執行者：只在 controller 核定的完整 plan 下動手，涵蓋一般程式碼與一般文件；不做自己的正式驗收、不擴 scope、不執行對外或不可逆動作 |
| `global/claude/agents/verifier.md` | fresh-context 驗收者：含「找碴範圍」與收斂標記；高風險驗收用同一個角色，派工一律顯式 `model: opus`（升 `fable` 的條件見 dispatch skill §6『驗證不自驗』） |
| `global/claude/hooks/controller-context.sh` | SessionStart hook，把 `route-card.md` 注入主對話；卡片不存在就靜默略過 |
| `global/claude/hooks/block-ci-edit.sh` | PreToolUse hook，擋主對話用 Edit／Write 改 `.github/workflows` 與 `.github/actions`（選配） |
| `global/claude/hooks/allow-git-c-projects.sh` | PreToolUse hook，對 `$HOME/Projects/`（或 `GIT_C_ALLOW_ROOT` 指定的根目錄）底下嚴格形狀的 `git -C <path> worktree remove`／`branch -D` 回 allow，其餘不表態（選配） |
| `global/claude/config/ripgreprc` | 讓 Bash 的 `rg` 預設 `--hidden` 並排除 `.git`（選配） |
| `global/claude/settings.snippets.json` | 要手動併入 `~/.claude/settings.json` 的 hook 與 `env` 片段，不整檔覆蓋 |

`worker.md`／`verifier.md` 的 name 與 description 會出現在每 session 的可用 agent 清單裡，正文只在該角色被派工時進入 subagent context。

## Codex

Codex 只自動取得 `~/.codex/AGENTS.md` 的路由，依其中條件按需讀下列檔與共用 skill；共用的 `global/shared/**` 與 Claude 側是同一份。

| 檔案 | 用途 |
|------|------|
| `global/codex/AGENTS.md` | Codex 全域入口：與 Claude 入口同組的邊界六條、路由表、Codex 注意事項、Bootstrap |
| `global/codex/rules/dispatch.md` | Codex 調度：角色 mapping、named-first → `default` runtime adapter、reasoning effort、subagent 使用邊界、驗證不自驗 |
| `global/codex/rules/delegation-templates.md` | A–L 十二份 logical-role 派工模板與共用 adapter envelope |
| `global/codex/agents/scanner.toml` | Luna／medium／read-only，精確掃描 |
| `global/codex/agents/explorer.toml` | Terra／medium／read-only，repo 探索與外部研究 |
| `global/codex/agents/planner.toml` | Terra／high／read-only，非平凡任務規劃 |
| `global/codex/agents/worker.toml` | Luna／max／workspace-write，標準實作；需完整 approved plan |
| `global/codex/agents/pro_worker.toml` | Terra／high／workspace-write，有 complexity signals 時預先使用的實作 |
| `global/codex/agents/recovery_worker.toml` | Terra／high／workspace-write，Luna 能力或脈絡理解不足、或兩次未明失敗後的 recovery |
| `global/codex/agents/reviewer.toml` | Terra／high／read-only，一般實作 review |
| `global/codex/agents/escalation_planner.toml` | Sol／medium／read-only，root-cause 規劃升級 |
| `global/codex/agents/escalation_worker.toml` | Sol／medium／workspace-write，Terra 已確認能力不足後的升級實作 |
| `global/codex/agents/verifier.toml` | Terra／high／workspace-write（只寫 repo 外探針目錄），一般 fresh-context 驗收 |
| `global/codex/agents/sol_verifier.toml` | Sol／high／workspace-write（只寫 repo 外探針目錄），高風險 fresh-context 驗收 |

Codex 的角色選擇、升降級與 runtime adapter 規則是 `global/codex/rules/dispatch.md` §0–§1 與 §5 的內容，這裡不重述。TOML 安裝或角色名稱不能取代 runtime evidence；Codex custom role 名稱使用底線，以符合 `spawn_agent.task_name` 的格式限制。

## repo-only

只在本 repo 開工時由專案層載入，不安裝到任何全域位置。

| 檔案 | 用途 |
|------|------|
| `.claude/skills/maintain-guideline/SKILL.md` | 系統維護協議：權限分級、兩平台同步矩陣、修改流程、教訓寫回、瘦身與日落條款、路由完整性 |
| `.claude/skills/usage-review/SKILL.md` | 量 Claude Code 本機 session jsonl 的用量與派工行為（只解析 Claude Code）：`scripts/extract.py` 把 jsonl 正規化成單一 JSON（`references/schema.md` 定義欄位）、`scripts/report.py` 九個子命令只讀該 JSON，`scripts/pricing.json` 是外置價格表，`references/caveats.md` 收攏已知陷阱 |

## docs、scripts、tests

| 檔案 | 用途 |
|------|------|
| `README.md`／`README.zh-TW.md` | repo 概覽入口（英文／繁體中文，章節對應）：定位、核心概念、安裝入口、目錄地圖 |
| `docs/install.md` | 完整安裝步驟：Claude Code、Codex、Windows（PowerShell）、實體檔同步版、從 v1 升級；只有中文 |
| `docs/new-host.md` | 新機器建檔（5 分鐘探測清單）；只有中文 |
| `docs/repo-layout.md` | 本檔 |
| `docs/lessons.md` | 活躍教訓日誌：只留還沒有判準承接的條目，不裝進全域 |
| `docs/lessons-archive.md` | 已升級成正式判準的歷史教訓（保留原文，作為判準來歷） |
| `docs/judgment-rationale.md` | `judgment.md` 各條的來歷、理由與正反例 |
| `docs/debug-environment-first.md` | 除錯前的環境事實檢查清單與量測方法自證陷阱；`judgment.md` 13 只留判準與指向 |
| `docs/harness-facts.md` | 查證過的 harness 事實（model／effort 可填值、`isolation: worktree`、hook 注入等） |
| `docs/hosts-detail.md` | 各機器工具鏈與版本明細（探測快照） |
| `docs/skill-catalog.md` | 各類任務用哪個 skill／plugin，含 Figma 在 MCP 缺席時的 curl fallback |
| `docs/memory-layers.md` | 記憶機制四層的分工與邊界 |
| `docs/codex-named-agent-registration.md` | Codex named agent 實體 TOML 同步、註冊實測差異與限制 |
| `docs/codex-tooling-audit-*.md` | Codex 的 LSP／語意工具、plugin／skill context 盤點與瘦身 |
| `docs/parallel-dispatch-design.md` | parallel-dispatch 的架構說明與刻意不做的理由 |
| `docs/verification-policy-history.md` | 驗收政策的歷史背景與 `fable` 升檔訊號清單 |
| `docs/dispatch-cost-review-*.md`、`worker-sonnet55-trial-*.md`、`issue-session-trial-*.md`、`workflow-cost-improvement-brief-*.md` | 派工成本 audit、worker 換型號的量測、issue 分 session 試行與成本調整 brief；歷史紀錄，不是現行規則 |
| `docs/restructure-plan-*.md`、`global-policy-ownership-review-*.md`、`global-rules-token-review-*.md`、`*-agents-guildeline-self-review.md` | 全域規則重構的計畫與其輸入審查 |
| `docs/archive/` | 無任何檔案引用的歷史文件；只作考古用 |
| `scripts/sync-profile.py` | 把 `global/` 寫成 `~/.claude`、`~/.codex`、`~/.agents` 的實體檔複本（不能提權的機器用），偵測並列出 v1 舊安裝殘留 |
| `scripts/sync-codex-agents.py` | 把 `global/codex/agents/*.toml` 寫成 `~/.codex/agents` 的實體檔 |
| `scripts/dispatch-usage.py` | 日落審查用：量主對話自寫與派 subagent 的使用率（量法見 `maintain-guideline` §5） |
| `scripts/parallel-usage.py` | 量平行寫入派工的群組與 worktree 派工次數 |
| `scripts/stall-check.py` | 列出本機每個 claude session 的靜默時間與卡住的位置（盤點 session 用） |
| `scripts/issue-status.py` | 一次列出某 repo 每個 issue worktree 的狀態（盤點 session 用，唯讀） |
| `scripts/tests/` | `issue-status.py`、`stall-check.py` 的單元測試 |
| `tests/test_*.py` | sync 腳本、usage-review 腳本、writing-principles 檢查腳本與 shell 守門腳本的單元測試；樣本在 `tests/fixtures/writing-principles/` |
| `tests/test-*.sh` | hook 與 ripgreprc 的離線斷言（`block-ci-edit.sh`、`allow-git-c-projects.sh`、`controller-context.sh`、`ripgreprc`），也由 `tests/test_shell_guards.py` 包進 pytest |

## 為什麼 Claude 側只自建 worker 與 verifier

Claude 側沒有 `scanner`／`explorer`／`planner` 的等價 custom agent：內建 `Explore`／`Plan`／`general-purpose` 加上逐次指定 `model` 已經涵蓋唯讀掃描與規劃。`worker` 與 `verifier` 需要獨立定義檔：一般實作與文件撰寫要固定綁 Sonnet 5.5，驗收要固定綁 `opus`，寫成 standalone agent 才能把 model、effort 與角色合約一起鎖成預設，不靠每次呼叫都記得帶參數。Agent 工具本身可以逐次帶 `effort`（見 `docs/harness-facts.md`「沒有 frontmatter effort 的 subagent」），所以獨立定義檔的價值是鎖預設，不是補足做不到的事。

## 為什麼 Claude 側沒有派工模板檔

Claude 側的派工合約併在 `global/shared/skills/dispatch/SKILL.md` §3『派工合約』與 `handoff` skill §1『brief 卡』，沒有獨立模板檔：填空模板對 Claude 5 世代是重複投入，且範例會窄化探索。Codex 側維持 `global/codex/rules/delegation-templates.md`：它把 approved plan、寫入所有權、驗證命令與回報格式做成可核對欄位，避免 controller 只靠角色名稱推定 child 已取得完整脈絡。
