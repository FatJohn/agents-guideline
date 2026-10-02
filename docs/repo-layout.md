# 檔案結構

> 完整檔案表與各角色的設計說明。`README.md`／`README.zh-TW.md` 的目錄地圖只列頂層目錄，逐檔用途看這裡。

**Claude Code 每 session 自動載入**（固定 context 成本，只放每次都要的）：

| 檔案 | 用途 |
|------|------|
| `CLAUDE.md` | 路由表＋三鐵律＋優先權排序（裝在 `~/.claude/`） |
| `rules/00-environment.md` | 跨機器事實、三大結構性風險與修法 |
| `hosts/<key>.md` | 單機事實（身分、repo 位置、驗證能力、陷阱）；經全域 `CLAUDE.md` 的 `@~/.claude/host-facts.md` 匯入，**每台機器只裝自己那份**；新機器由 AI 照 `docs/new-host.md`「新機器建檔」建檔 |
| `rules/05-hosts.md` | 跨機器規則、`<REPO>` 對照表、缺檔哨兵（context 裡沒有「# 本機事實」段時怎麼辦） |
| `rules/10-dispatch.md` | Claude Code 調度：何時派 subagent、派工合約、回報合約、升降級路徑、驗證分工與 rubric 對應 |
| `rules/20-judgment.md` | 判斷準則：升級／完成／問使用者／換路／環境先驗，各附正反例 |
| `rules/50-lessons.md` | **還沒有正式判準承接的**活躍教訓＋交接欄 |

Codex 只自動取得 `~/.codex/AGENTS.md` 的路由；它依其中條件按需讀本 repo 的 `rules/`、`codex/rules/`、`rubrics/` 與 skills，不能把 Claude Code 的 resident imports 當成 Codex 的常駐內容。

**用到才讀**（不在 `rules/`，故不自動載入）：

| 檔案 | 用途 |
|------|------|
| `skills/maintain-guideline/SKILL.md` | 系統維護協議：權限分級、修改流程、教訓寫回、瘦身與日落條款、路由完整性 |
| `docs/debug-environment-first.md` | 除錯前的環境事實檢查清單＋量測方法自證陷阱；`rules/20-judgment.md` §5 只留判準與指向 |
| `rubrics/document-quality.md` | 文件類產出的逐條驗收判準（verifier 讀） |
| `rubrics/code-change.md` | 程式碼變更的逐條驗收判準（含殘留掃描與作假偵測） |
| `rubrics/research-analysis.md` | 研究／盤點類產出的逐條驗收判準 |
| `docs/lessons-archive.md` | 已升級成正式判準的歷史教訓（保留原文，作為判準來歷） |
| `scripts/dispatch-usage.py` | 日落審查用：從 `~/.claude/projects/**/*.jsonl` 量主對話自寫 vs 派 subagent 的使用率（量法見 `maintain-guideline` §5） |
| `docs/hosts-detail.md` | 各機器工具鏈與版本明細（探測快照，非常駐） |
| `docs/skill-catalog.md` | 各類任務用哪個 skill／plugin，含 Figma 在 MCP 缺席時的 curl fallback |
| `docs/harness-facts.md` | 查證過的 harness 事實，非常駐 |
| `docs/codex-named-agent-registration.md` | Codex named agent 實體 TOML 同步、註冊實測差異與限制，非常駐 |
| `docs/memory-layers.md` | 記憶機制四層的分工與邊界，非常駐 |
| `README.md`／`README.zh-TW.md` | repo 概覽入口（英文／繁體中文，章節對應）：定位、核心概念、安裝入口、目錄地圖 |
| `docs/install.md` | 完整安裝步驟：Claude Code（macOS／Linux）、Codex（macOS／Linux）、Windows（PowerShell）、實體檔同步版；只有中文 |
| `docs/new-host.md` | 新機器建檔（5 分鐘探測清單）；只有中文 |
| `docs/archive/` | 無任何檔案引用的歷史文件（2026-07 的 Codex 分層路由 spec／plan、2026-08-29 的驗收輪次盤點）；只作事故考古用 |
| `codex/rules/10-dispatch-codex.md` | Codex 調度：角色 mapping、named-first → `default` runtime adapter、reasoning effort、subagent 使用邊界、驗證不自驗 |
| `codex/rules/30-delegation-templates-codex.md` | Codex A–L 十二份 logical-role 派工模板與共用 adapter envelope（scanner 掃描；explorer repo 探索與外部研究；planner 規劃；worker 實作與重構；reviewer 一般 review；recovery_worker Terra recovery；escalation_planner 規劃升級；escalation_worker 升級實作；verifier 一般驗收；sol_verifier 高風險驗收） |
| `agents/worker.md` | 標準執行者 agent 定義（Sonnet 5.5 完整 model ID `claude-sonnet-5-5` + effort xhigh，試用中，派工不帶 `model`；升級依 `rules/10-dispatch.md` §4）。只在 controller 核定的完整 plan 下動手，涵蓋一般程式碼與一般文件；不做自己的正式驗收、不擴 scope、不執行對外或不可逆動作 |
| `agents/worker-opus.md` | 備用車道，Opus 5.5/medium，合約同 `worker`；預設路由仍是 worker；設計已核定、但實作須同時推理多條執行路徑或時序時，或使用者指定時才用，不作為失敗升級路徑；派工不帶 `model` |
| `agents/verifier.md` | fresh-context 驗收 agent 定義（opus + effort high，對齊 Codex verifier/Terra high）。含「找碴範圍」與收斂標記；**高風險驗收用同一個角色、檔位不變**（派工一律顯式 `model: opus`；升 `model: fable` 的條件與例外見 `rules/10-dispatch.md` §5「驗證不自驗」） |
| `codex/agents/scanner.toml` | Codex Luna/medium/read-only 精確掃描 agent |
| `codex/agents/explorer.toml` | Codex Terra/medium/read-only 探索 agent |
| `codex/agents/planner.toml` | Codex Terra/high/read-only 非平凡任務規劃 agent |
| `codex/agents/worker.toml` | Codex 所有訂閱檔位的 Luna/max/workspace-write 標準實作 agent；需完整 approved plan |
| `codex/agents/pro_worker.toml` | Codex Terra/high/workspace-write higher-complexity 實作 agent；有 complexity signals 時可預先使用 |
| `codex/agents/recovery_worker.toml` | Codex Terra/high/workspace-write Luna 能力／脈絡理解不足或兩次未明失敗後的 recovery agent |
| `codex/agents/reviewer.toml` | Codex Terra/high/read-only 一般實作 review agent |
| `codex/agents/escalation_planner.toml` | Codex Sol/medium/read-only root-cause 規劃升級 agent |
| `codex/agents/escalation_worker.toml` | Codex Sol/medium/workspace-write Terra 已確認能力不足後的 root-cause 升級實作 agent |
| `codex/agents/verifier.toml` | Codex Terra/high/read-only 一般 fresh-context 驗收 agent |
| `codex/agents/sol_verifier.toml` | Codex Sol/high/read-only 高風險 fresh-context 驗收 agent |
| `codex/skills/session-handoff/SKILL.md` | Codex 收尾／交接 skill，產生專案 `.codex/HANDOFF.md` |
| `skills/create-pr/SKILL.md` | Codex／Claude 共用的 Pull Request 建立 skill |
| `skills/parallel-dispatch/SKILL.md` | Claude／Codex 共用的平行開發 orchestration：ANALYZE → PARALLELIZE? → TASK GRAPH → WORKERS → VALIDATION → INTEGRATION → FINAL VALIDATION，含 divide-and-conquer 與 agent-race 兩種 pattern；`references/templates.md`（brief／report 格式）、`references/worktree.md`（隔離與清理機制）、execution adapter `references/claude-code.md`／`codex.md`／`cli.md`（純 shell、tmux、VS Code、Herdr、Orca 等外部 CLI process） |

`agents/*.md` 與 `codex/agents/*.toml` 是 standalone role 定義／設定；它們的正文只在該 named role 被派工時進入 subagent context（name／description 會出現在每 session 的可用 agent 清單裡）。named unavailable 時，generic adapter 仍須在 prompt 帶入 `30-delegation-templates-codex.md` 的完整 logical-role contract；`pro_worker` 明確重用 D 的 worker contract，只替換 Terra/high mapping，並附 higher-complexity route 證據。TOML 安裝或角色名稱不能取代 runtime evidence。

**為什麼 Claude 側只自建 `worker`／`verifier`，沒有 `scanner`／`explorer`／`planner` 的等價 custom agent**：內建 `Explore`／`Plan`／`general-purpose` 加上逐次指定 `model` 已經涵蓋唯讀掃描與規劃，且本制度不把 haiku 列入 active routing。`worker` 與 `verifier` 需要獨立定義檔的理由相同——**Agent 呼叫無法逐次指定 effort**，一般實作與文件撰寫要固定綁 `sonnet 5.5／xhigh`、驗收要固定綁 `opus／high`，只有寫成 standalone agent 才能把 model 與 effort 一起鎖進角色合約，不必每次呼叫都手動重複。備用車道 `worker-opus`（Opus 5.5/medium，合約同 `worker`）不改變這裡的角色分工。

**為什麼 Claude 側沒有派工模板檔、Codex 側有**：Claude 側的派工合約併在 `rules/10-dispatch.md` §2 與各 `agents/*.md` 的角色合約，沒有獨立模板檔——填空模板對 Claude 5 世代是重複投入，且範例會窄化探索。Codex 側維持 `codex/rules/30-delegation-templates-codex.md`：它把 approved plan、寫入所有權、驗證命令與回報格式做成可核對欄位，避免 controller 只靠角色名稱推定 child 已取得完整脈絡。

Codex routing 依 complexity signals，而不是 task 名稱：simple／mechanical 用 Luna low／medium；normal development 用 `worker/Luna max`；higher complexity 可預先用 `planner`／`pro_worker` 的 Terra high，Luna 失敗後才由 `recovery_worker/Terra high` 接手；high-impact judgment 可直接用 `escalation_planner`／`escalation_worker` 的 Sol medium，其他路徑則等 Terra 已確認能力不足才升 Sol medium；exceptional difficulty 才用 Sol high。xhigh／max 沒有固定 route。失敗時先分 execution mistake、reasoning 不足、model／context 理解不足與 evidence／environment 不足，再決定補正、加 effort、升 tier 或補證據。

Codex custom role 名稱使用底線，以符合目前 `spawn_agent.task_name` 的格式限制。安裝 TOML 不等於 runtime 已選中角色：派工前先看當前 surface 是否明確提供 `agent_type` 與該角色的 model／effort metadata；named 可用時優先選 named，unavailable 時依 `codex/rules/10-dispatch-codex.md` §0 permission gate 選擇 `default` 或 direct CLI 套用 logical-role contract。這些值只進 adapter envelope：surface metadata 記「工具宣告值」，工具回傳或 child metadata 另有 runtime 值才升級為「runtime 已驗證」，沒有 metadata 就記「runtime 未驗證」。user-facing commentary 正常只報指定 role 名稱與任務摘要；generic／direct CLI fallback 必須標示，避免把 generic child 冒充 custom role。
