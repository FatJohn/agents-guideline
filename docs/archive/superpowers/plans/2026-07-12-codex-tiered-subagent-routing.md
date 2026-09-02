# Codex 分級 Subagent 調度與全域規則校正 Implementation Plan

> Status: Superseded. This is a historical implementation record, not an active execution plan.
>
> 歷史計畫：目前 routing 已由 2026-07-14 的 model-routing-policy 取代。下方 RED/GREEN 指令只記錄當時的建立流程；不要直接重跑整份計畫，尤其要沿用目前 canonical model IDs（`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna`）與現行 agent 清單。

> Archived execution record: the historical steps below retain their original checkbox and skill references for traceability; do not use them as current execution instructions.

**Goal:** 建立以角色為穩定介面、由 Luna／Terra／Sol 提供分級能力的 Codex subagent 系統，並同步修正 Claude/Codex 共用規則、並行寫入與驗證邊界。

**Architecture:** `scanner`、`explorer`、`worker`、`verifier` 定義工作責任，模型映射只存在 Codex agent TOML 與平台 dispatch 文件。共用 `rules/` 採平台中立能力層級；Claude 與 Codex 的工具參數留在各自文件。所有寫入、安裝與本機 config 變更分段驗證，最後由 Claude 與 Codex fresh-context verifier 各自 read-back。

**Tech Stack:** Markdown、TOML、zsh、git、Claude Code 2.1.207、Codex 0.144.1、custom agents、symlink

---

## File Map

新增：

- `codex/agents/scanner.toml`：Luna/medium/read-only 的精確掃描角色。
- `codex/agents/explorer.toml`：Terra/medium/read-only 的跨檔探索角色；覆寫 Codex 內建 `explorer`。

修改：

- `codex/agents/verifier.toml`：固定 Sol/high/read-only。
- `codex/rules/10-dispatch-codex.md`：Codex 角色映射、派工判斷、升降級、並行寫入與驗證政策。
- `codex/rules/30-delegation-templates-codex.md`：scanner/explorer/worker/verifier prompt 模板與 worktree 安全欄位。
- `rules/00-environment.md`：平台中立環境風險、Claude/Codex 路由、記憶與 Chronicle 邊界。
- `rules/05-hosts.md`：主力機穩定識別與目前工具事實。
- `rules/10-dispatch.md`：Claude 2.1.207 model/effort/background/worktree 現況與雙軸派工門檻。
- `rules/20-judgment.md`：平台中立能力層級、完成定義與統一授權邊界。
- `rules/40-maintenance.md`：並行寫入、安裝 config 與驗證流程。
- `rules/50-lessons.md`：把已升級教訓的「已套用到」欄位改成實際規則位置，不刪歷史。
- `AGENTS.md`、`CLAUDE.md`、`README.md`：統一路由、三鐵律、授權清單、安裝方式與檔案索引。
- `docs/superpowers/specs/2026-07-12-codex-tiered-subagent-routing-design.md`：維持已核准狀態，不再變更設計內容。
- `docs/superpowers/plans/2026-07-12-codex-tiered-subagent-routing.md`：本實作計畫。

本機狀態：

- `~/.codex/agents/scanner.toml`、`explorer.toml`：指向 repo agent 定義的 symlink。
- `~/.codex/config.toml`：加入或合併 `[agents] max_threads = 4, max_depth = 1`。

## Execution Rules

- 修改任何已存在檔案前，先完成 Task 1 備份。
- 同一 working tree 同時只允許一個寫入者；本計畫預設序列執行。
- 所有檔案修改使用 `apply_patch`；格式化或純驗證指令例外。
- 任何 `git commit` 步驟都需要使用者在執行 session 明確授權；未授權時跳過 commit，但保留相同驗證 checkpoint。
- 不 push、不 merge、不發佈。

### Task 1: 建立基準、備份與 RED 證據

**Files:**
- Read: `AGENTS.md`
- Read: `CLAUDE.md`
- Read: `rules/00-environment.md`
- Read: `rules/05-hosts.md`
- Read: `rules/10-dispatch.md`
- Read: `rules/20-judgment.md`
- Read: `rules/40-maintenance.md`
- Read: `codex/rules/10-dispatch-codex.md`
- Read: `codex/rules/30-delegation-templates-codex.md`
- Read: `codex/agents/verifier.toml`
- Backup: `~/.claude/backups/2026-07-12-tiered-subagents/`
- Backup: `~/.codex/backups/2026-07-12-tiered-subagents/`

- [ ] **Step 1: 確認工作樹只包含已核准的 spec/plan**

Run:

```bash
git status --short
for file in docs/superpowers/specs/2026-07-12-codex-tiered-subagent-routing-design.md docs/superpowers/plans/2026-07-12-codex-tiered-subagent-routing.md; do
  test -f "$file"
  sed -n '1,$p' "$file"
done
git diff -- . ':(exclude)docs/superpowers'
```

Expected: `git status` 只有 `?? docs/`；兩份文件內容會由 `sed` read-back；排除 docs 後的 tracked diff 無輸出。

- [ ] **Step 2: 建立 Claude 與 Codex 備份**

Run:

```bash
mkdir -p ~/.claude/backups ~/.codex/backups
CLAUDE_BACKUP=$(mktemp -d ~/.claude/backups/2026-07-12-tiered-subagents.XXXXXX)
CODEX_BACKUP=$(mktemp -d ~/.codex/backups/2026-07-12-tiered-subagents.XXXXXX)
cp CLAUDE.md rules/00-environment.md rules/05-hosts.md rules/10-dispatch.md rules/20-judgment.md rules/40-maintenance.md rules/50-lessons.md "$CLAUDE_BACKUP/"
cp AGENTS.md codex/rules/10-dispatch-codex.md codex/rules/30-delegation-templates-codex.md codex/agents/verifier.toml "$CODEX_BACKUP/"
cp ~/.codex/config.toml "$CODEX_BACKUP/config.toml"
printf 'CLAUDE_BACKUP=%s\nCODEX_BACKUP=%s\n' "$CLAUDE_BACKUP" "$CODEX_BACKUP"
ls -la "$CLAUDE_BACKUP" "$CODEX_BACKUP"
```

Expected: `mktemp` 每次建立新的唯一目錄，三個 `cp` 都 exit 0，輸出實際 backup 路徑與檔案；重跑不覆蓋先前備份。

- [ ] **Step 3: 執行現況 RED contract checks**

Run:

```bash
test ! -e codex/agents/scanner.toml
test ! -e codex/agents/explorer.toml
! rg -q '^model = "gpt-5.6-sol"$' codex/agents/verifier.toml
rg -q 'max.*不能進 frontmatter' rules/00-environment.md
rg -q '見 `10-dispatch.md` §4' rules/20-judgment.md
```

Expected: command exit 0，證明新角色尚不存在、verifier 尚未固定 Sol、Claude effort 與共用 dispatch 路由仍是舊規則。

### Task 2: 建立 Codex 分級 custom agents

**Files:**
- Create: `codex/agents/scanner.toml`
- Create: `codex/agents/explorer.toml`
- Modify: `codex/agents/verifier.toml:1-15`

- [ ] **Step 1: 新增 `scanner`**

Use `apply_patch` to create:

```toml
name = "scanner"
description = "低風險唯讀掃描者。適用於精確清單、分類、格式檢查與結構化抽取；不得做跨系統判斷、寫入或最終驗收。"
model = "gpt-5.6-luna"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"

developer_instructions = """
你是唯讀掃描者。只完成明確、可機械驗證的搜尋、分類、格式檢查或結構化抽取。

規則：
1. 禁止修改檔案、branch、stash、commit、push 或任何對外動作。
2. 任務需要跨檔推理、架構判斷、安全判斷或無法機械驗證時，停止並回報應升級 explorer。
3. 每項結果附檔案:行號或可核對來源；找不到時列出查過的關鍵字。
4. 只回結論與證據，不貼大量原文；回報不超過 30 行。
5. 禁止再 spawn subagent。
"""
```

- [ ] **Step 2: 新增 `explorer`**

Use `apply_patch` to create:

```toml
name = "explorer"
description = "唯讀探索者。適用於 repo 探索、跨檔追蹤、文件研究、影響範圍與證據整理。"
model = "gpt-5.6-terra"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"

developer_instructions = """
你是唯讀探索者。追蹤真實執行路徑、跨檔關係與外部文件證據，但不實作修改。

規則：
1. 禁止修改檔案、branch、stash、commit、push 或任何對外動作。
2. 優先使用精確搜尋與目標段落讀取，回報檔案:行號、URL 與摘要。
3. 遇到架構取捨、安全高風險或連續兩次失敗時，停止並回報應升級 escalation-planner/Sol max。
4. 只回結論與證據；內容超過 30 行時回報「需要父任務接手落檔」與建議結構，自己仍禁止寫檔。
5. 禁止再 spawn subagent。
"""
```

- [ ] **Step 3: 固定 `verifier` 為 Sol/high/read-only**

Insert after `description` in `codex/agents/verifier.toml`:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
```

Remove the old duplicate `model_reasoning_effort = "high"` line.

Insert these exact rules at the start of the existing numbered rules inside `developer_instructions`，then renumber the original rules:

```text
1. 禁止修改任何檔案、branch、stash、commit、push 或對外狀態；只讀取、執行不產生變更的檢查並回報判定。
2. 即使父任務要求寫入，也要拒絕並回報「verifier 角色使用錯誤」；不得為了完成驗收自行修正問題。
```

- [ ] **Step 4: 執行 agent TOML GREEN checks**

Run:

```bash
for f in codex/agents/scanner.toml codex/agents/explorer.toml codex/agents/verifier.toml; do
  rg -q '^name = ' "$f"
  rg -q '^description = ' "$f"
  rg -q '^model = ' "$f"
  rg -q '^model_reasoning_effort = ' "$f"
  rg -q '^sandbox_mode = "read-only"$' "$f"
  rg -q '^developer_instructions = """$' "$f"
done
rg -q '^model = "gpt-5.6-luna"$' codex/agents/scanner.toml
rg -q '^model = "gpt-5.6-terra"$' codex/agents/explorer.toml
rg -q '^model = "gpt-5.6-sol"$' codex/agents/verifier.toml
rg -q '禁止修改任何檔案、branch、stash、commit、push' codex/agents/verifier.toml
rg -q 'verifier 角色使用錯誤' codex/agents/verifier.toml
```

Expected: exit 0；三個角色的 model、effort、sandbox 與必填欄位都存在。

- [ ] **Step 5: 可選 checkpoint commit**

Only if explicitly authorized:

```bash
git add codex/agents/scanner.toml codex/agents/explorer.toml codex/agents/verifier.toml
git status --short
git diff --cached --stat
git diff --cached
git stash list
git commit -m "feat(codex): add tiered subagent roles"
```

Expected before commit: staged diff 只包含三個 agent TOML，沒有未知 stash；否則停止，不 commit。

### Task 3: 更新 Codex dispatch 與派工模板

**Files:**
- Modify: `codex/rules/10-dispatch-codex.md:1-64`
- Modify: `codex/rules/30-delegation-templates-codex.md:1-75`

- [ ] **Step 1: 將角色表改成 scanner/explorer/worker/verifier 分級表**

Replace §0 with a table containing these exact mappings:

```markdown
| 角色 | 模型與 effort | 權限 | 用途 |
|------|---------------|------|------|
| `scanner` | Luna / medium | read-only | 精確清單、分類、格式檢查、結構化抽取 |
| `explorer` | Terra / medium | read-only | repo 探索、跨檔追蹤、文件研究、影響範圍 |
| `worker` | 繼承父 session，通常為 Sol | 父 session | 實作、除錯、執行驗證 |
| `verifier` | Sol / high | read-only | 文件 read-back、高風險與最終驗收 |
```

Add this exact paragraph after the table:

```markdown
Luna 只處理低風險且可機械驗證的唯讀任務，不得寫入、做架構／安全判斷、執行對外動作或最終驗收。`verifier` 不參與製作，也不直接修正驗收發現的問題。
```

- [ ] **Step 2: 將派工門檻改成 context 成本＋任務獨立性雙軸**

Replace the single “超過一頁” rule with this exact block:

```markdown
符合任一條件時優先派 subagent：

- 任務可獨立完成，主對話只需要結論與證據。
- 原始輸出量大，而且後續不需要主對話反覆引用全部內容。
- 有兩個以上互不依賴的子任務，可安全平行。
- 需要 fresh-context 第二意見或對抗式驗收。

以下情況保留在主對話：

- 工作很小但與目前決策高度耦合。
- 多步驟操作需要頻繁共享同一份可變狀態。
- 使用者正在做需要即時互動的品味或需求選擇。
- 平行寫入無法安全隔離。
```

Keep this final sentence: `主對話負責跟使用者對話、整合證據、做決策與 read-back 實際工作狀態。`

- [ ] **Step 3: 加入 working-tree 不變量與升降級**

Add these requirements:

```markdown
- 同一 working tree 同時只能有一個寫入者。
- 平行寫入必須使用獨立 worktree；不重疊檔案若共用 working tree 也只能序列寫入。
- 需要其結果才能繼續的 blocking 任務不得只放在可能因休眠或背景 session 中斷而消失的背景執行。
- Subagent 回報不等於實際狀態；controller 必須 read-back `git status`、diff、commit 與驗證輸出。
- Luna 一次實質錯誤、跨檔推理或不可機械驗證 → Terra。
- Terra 同一子任務失敗兩次，或涉及架構、安全、資料遺失、不可逆／對外動作 → Sol。
- Sol 仍卡住 → fresh-context Sol、獨立第二意見或重新定義問題。
```

- [ ] **Step 4: 更新 Codex prompt templates**

Add these complete read-only templates before the writing template:

```text
## A. 精確掃描（角色：scanner）

你是被派來的執行者，親自完成本任務；禁止再 spawn subagent。
目標：【精確清單、分類、格式檢查或結構化抽取】。
範圍：【絕對路徑與排除範圍】。
限制：禁止寫檔、branch、stash、commit、push 與對外動作。需要跨檔推理、架構／安全判斷或無法機械驗證時，停止並回報應升級 explorer。
驗收條件：每筆附檔案:行號或可核對來源；找不到時列出查過的關鍵字。
回報格式：不超過 30 行；內容更長時回報「需要父任務接手落檔」與建議結構。

## B. 探索／研究（角色：explorer）

你是被派來的執行者，親自完成本任務；禁止再 spawn subagent。
目標：【要追蹤的執行路徑、跨檔關係、文件問題或影響範圍】。
範圍：【絕對路徑、URL 與排除範圍】。
限制：禁止寫檔、branch、stash、commit、push 與對外動作。涉及高風險判斷或同一子任務失敗兩次時，停止並回報應升級 escalation-planner/Sol max。
驗收條件：每個結論附檔案:行號或 URL；查不到標示未查證並列出查過的位置。
回報格式：結論先行，不超過 30 行；內容更長時回報「需要父任務接手落檔」與建議結構。
```

Renumber implementation/refactor/research/verification sections. Every writing template must include:

```text
工作目錄：使用【目前 working tree／獨立 worktree 絕對路徑】。
寫入所有權：【絕對路徑清單】；禁止修改清單外檔案。
禁止 branch、stash、commit、push；由父任務統一整合。
```

Read-only templates must say “禁止寫檔；若需要長產物，回報父任務接手落檔”。

- [ ] **Step 5: 執行 Codex rules contract checks**

Run:

```bash
rg -q '`scanner`.*Luna / medium' codex/rules/10-dispatch-codex.md
rg -q '`explorer`.*Terra / medium' codex/rules/10-dispatch-codex.md
rg -q '`verifier`.*Sol / high' codex/rules/10-dispatch-codex.md
rg -q '同一 working tree 同時只能有一個寫入者' codex/rules/10-dispatch-codex.md
rg -q '任務獨立性' codex/rules/10-dispatch-codex.md
rg -q 'blocking 任務不得只' codex/rules/10-dispatch-codex.md
rg -q 'controller 必須 read-back' codex/rules/10-dispatch-codex.md
rg -q '工作目錄：使用' codex/rules/30-delegation-templates-codex.md
rg -q '寫入所有權：' codex/rules/30-delegation-templates-codex.md
```

Expected: exit 0。

- [ ] **Step 6: 可選 checkpoint commit**

Only if explicitly authorized:

```bash
git add codex/rules/10-dispatch-codex.md codex/rules/30-delegation-templates-codex.md
git status --short
git diff --cached --stat
git diff --cached
git stash list
git commit -m "docs(codex): define tiered dispatch policy"
```

Expected before commit: staged diff 只包含兩份 Codex rules，沒有未知 stash；否則停止，不 commit。

### Task 4: 平台中立化共用判斷與驗證規則

**Files:**
- Modify: `rules/20-judgment.md:1-57`
- Modify: `rules/00-environment.md:14-55`
- Modify: `rules/40-maintenance.md:22-65`

- [ ] **Step 1: 將 `20-judgment.md` 改成能力層級語彙**

Use these definitions at §1 start:

```markdown
- **輕量層**：低風險、範圍明確、可機械驗證的任務。
- **標準層**：跨檔探索、一般實作與需要中等推理的任務。
- **高能力層**：架構、安全、資料遺失、不可逆／對外動作或高風險驗收。

模型映射依目前平台 dispatch 文件：Claude 見 `10-dispatch.md`，Codex 見 `../codex/rules/10-dispatch-codex.md`。
```

Use these exact examples:

```markdown
✅ **正例**：標準層 agent 修一個測試失敗，兩種不同修法都沒有讓驗收條件增加 → 附完整失敗軌跡，升高能力層。
❌ **反例**：輕量層 agent 在機械清單漏一筆，但補查同一範圍即可確認 → 這是執行疏漏，補做並驗證，不因單次疏漏直接升級。
```

Replace the Claude-only Opus note with:

```markdown
若已在目前平台的高能力層，下一步是換 fresh context、獨立第二意見或重新定義問題，不是只換措辭重試。模型對應見各平台 dispatch 文件。
```

- [ ] **Step 2: 精確化完成與驗證定義**

Replace the ambiguous self-verification rule with:

```markdown
- 主觀判斷、文件品質與高風險產出不得由製作者自己背書。
- 測試、build、lint、實跑與 schema 驗證等可重現的機械驗證可由製作者執行，但必須附指令與輸出。
- 高風險程式碼除機械驗證外，再加 fresh-context review。
```

Update every reference from only `10-dispatch.md` to this exact wording: `對應平台 dispatch 文件（Claude：\`10-dispatch.md\`；Codex：\`../codex/rules/10-dispatch-codex.md\`）`。

- [ ] **Step 3: 統一授權清單**

Set `20-judgment.md` §3 to this exact list:

```markdown
- 發訊息或寄信
- merge PR
- push 共享分支
- 發佈
- 刪除或覆蓋非自己建立的檔案
```

Add this exact sentence after the list: `使用者已在本 session 明確授權該動作時，直接執行，不重複詢問。`

- [ ] **Step 4: 修正 environment 的跨平台路由與 scratchpad**

In `rules/00-environment.md`, replace the context-risk remedy with:

```markdown
**修法**：
- 派工同時評估 context 成本與任務獨立性；Claude 見 `10-dispatch.md`，Codex 見 `../codex/rules/10-dispatch-codex.md`。
- Session 內狀態優先使用平台 plan/task 機制，不強制在 repo 建立 scratchpad 檔案。
- 只有需要跨 session 接續時，才用 `session-handoff` skill 更新 `.codex/HANDOFF.md`。
```

Keep the existing four memory layers, then add after the Codex Memories bullet:

```markdown
- **Chronicle（Codex 可選）**：opt-in research preview，利用螢幕脈絡補強 Memories；不取代 handoff 或 repo 文件。它會增加 rate-limit 消耗、敏感畫面外洩與 prompt injection 風險，因此不列為預設啟用項目。
```

Replace platform-ambiguous routing text with these exact bullets:

```markdown
- **Claude 派工**：角色、模型與 effort 見 `10-dispatch.md`。
- **Codex 派工**：角色、模型與 reasoning effort 見 `../codex/rules/10-dispatch-codex.md`。
- Memories、handoff、hooks 與 Chronicle 各自保留既定分工，不合併成單一機制。
```

- [ ] **Step 5: 把寫入隔離與 config 備份加入 maintenance**

In `rules/40-maintenance.md` add this exact subsection after standard modification workflow:

```markdown
### 並行與本機設定安全

- 同一 working tree 同時只能有一個寫入者；平行寫入使用獨立 worktree。
- 只切割不重疊檔案時，若仍共用 working tree，寫入必須序列執行。
- 修改 `~/.codex/config.toml` 前必須備份並驗證沒有重複 TOML table。
- commit 前 read-back `git status --short`、`git diff --cached`、`git stash list`。
```

Keep existing permission tiers and “不要自行 commit” rule unchanged.

- [ ] **Step 6: 執行共用規則 GREEN checks**

Run:

```bash
! rg -q '見 `10-dispatch.md` §4' rules/20-judgment.md
! rg -q '^✅.*sonnet|^❌.*haiku' rules/20-judgment.md
rg -q '輕量層' rules/20-judgment.md
rg -q '高能力層' rules/20-judgment.md
rg -q '不得由製作者自己背書' rules/20-judgment.md
rg -q '明確授權.*不.*重複' rules/20-judgment.md
rg -q 'Chronicle' rules/00-environment.md
rg -q '同一 working tree 同時只能有一個寫入者' rules/40-maintenance.md
```

Expected: exit 0。

### Task 5: 更新 Claude dispatch 與主機事實

**Files:**
- Modify: `rules/10-dispatch.md:1-77`
- Modify: `rules/00-environment.md:57-61`
- Modify: `rules/05-hosts.md:1-27`

- [ ] **Step 1: 更新 Claude 2.1.207 事實**

In `rules/00-environment.md` replace the stale fact block with:

```markdown
- Agent 呼叫可逐次指定 model；effort 仍由 agent 定義 frontmatter 或 session/workflow 設定控制。
- Agent frontmatter 的 `effort` 可填 `low`／`medium`／`high`／`xhigh`／`max`，實際可用值仍受模型與組織限制。
- Agent frontmatter 的 `model` 可填 `haiku`／`sonnet`／`opus`／`fable`／完整 model ID／`inherit`。
- Claude Code 2.1.207 的 subagent 可使用 `isolation: worktree`；需要 blocking 結果時不得只依賴可能因休眠中斷的背景執行。
```

- [ ] **Step 2: 更新 Claude 派工門檻與工作目錄安全**

In `rules/10-dispatch.md`, preserve the current model table including the Fable opt-in restriction, then replace the single dispatch threshold with:

```markdown
符合任一條件時優先派 subagent：任務可獨立且主對話只需結論；原始輸出量大且後續不需反覆引用；有互不依賴子任務可安全平行；需要 fresh-context 驗收。

以下情況保留主對話：工作小但與決策高度耦合；需頻繁共享可變狀態；需要即時使用者互動；平行寫入無法隔離。
```

Add this exact safety block before the reporting contract:

```markdown
## 工作目錄與背景任務安全

- 同一 working tree 同時只能有一個寫入者。
- 平行寫入的 subagent 必須設定 `isolation: worktree`；若仍共用 working tree，即使檔案不重疊也只能序列寫入。
- 需要其結果才能繼續的 blocking 任務不得只依賴可能因休眠中斷的背景執行。
- Subagent 回報不等於實際狀態；controller 必須 read-back `git status`、diff、commit 與驗證輸出。
```

Replace §5 opening with:

```markdown
主觀判斷、文件品質與高風險產出不得由製作者自己背書。測試、build、lint、實跑與 schema 驗證等可重現的機械驗證可由製作者執行，但必須附指令與輸出；高風險程式碼另加 fresh-context review。
```

- [ ] **Step 3: 更新主機識別**

In `rules/05-hosts.md` set the main heading and facts to include:

```markdown
## 主力 Mac（目前 hostname：`Mac`，arm64）

> 探測日：2026-07-12

- macOS 26.5.2、zsh、Homebrew。
- Claude Code 2.1.207；Codex 0.144.1。
- `git`、`gh`、`node`、`python3`、`flutter`、`dotnet`、`rg`、`jq` 可用；`fd` 未安裝。
```

Keep project paths and deployment facts; add this exact sentence: `hostname 只作當場參考，不作跨重開機或改名後的唯一識別。`

- [ ] **Step 4: 執行 Claude/host GREEN checks**

Run:

```bash
! rg -q 'max.*不能進 frontmatter' rules/00-environment.md
rg -q 'fable.*完整 model ID.*inherit' rules/00-environment.md
rg -q 'isolation: worktree' rules/00-environment.md rules/10-dispatch.md
rg -q '主力 Mac（目前 hostname：`Mac`，arm64）' rules/05-hosts.md
rg -q 'Claude Code 2.1.207；Codex 0.144.1' rules/05-hosts.md
```

Expected: exit 0。

### Task 6: 同步入口、README 與 lessons

**Files:**
- Modify: `AGENTS.md:25-37`
- Modify: `CLAUDE.md:24-33`
- Modify: `README.md:25-91`
- Modify: `rules/50-lessons.md:14-20`

- [ ] **Step 1: 同步三鐵律授權清單**

Use the same wording in `AGENTS.md`, `CLAUDE.md`, and README:

```markdown
**對外或不可逆動作需本 session 明確授權**：發訊息、寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案。已在本 session 明確授權時直接執行，不重複詢問。
```

- [ ] **Step 2: 更新 Codex 安裝腳本與檔案索引**

Change README Codex agent loop to symlink all three repo agents:

```bash
for agent in scanner explorer verifier; do
  src="$REPO/codex/agents/$agent.toml"; dst="$HOME/.codex/agents/$agent.toml"
  [ -e "$dst" ] && echo "略過（已存在，需手動處理）：$dst" || ln -s "$src" "$dst"
done
```

Add these exact rows to the README file table:

```markdown
| `codex/agents/scanner.toml` | Codex Luna/medium/read-only 精確掃描 agent |
| `codex/agents/explorer.toml` | Codex Terra/medium/read-only 探索 agent |
| `codex/agents/verifier.toml` | Codex Sol/high/read-only fresh-context 驗收 agent |
```

Add this exact text and TOML block immediately before the Memories configuration:

```markdown
Codex subagent 並行與遞迴上限建議固定：

    [agents]
    max_threads = 4
    max_depth = 1

`max_depth = 1` 禁止 subagent 再往下遞迴派工；調高前需重新評估 token、延遲與 working-tree 風險。
```

- [ ] **Step 3: 更新 lessons 的套用位置**

Do not rewrite historical incident text. Replace only each line’s final `已套用到` segment with these exact values:

```text
已套用到：rules/30-delegation-templates.md、codex/rules/30-delegation-templates-codex.md、README.md 的 max_depth = 1 設定
已套用到：rules/10-dispatch.md、codex/rules/10-dispatch-codex.md 的 blocking 任務規則
已套用到：rules/10-dispatch.md、codex/rules/10-dispatch-codex.md、rules/40-maintenance.md 的 single-writer/worktree 規則
```

Apply them respectively to the recursive delegation, background interruption, and shared-working-tree incident lines.

- [ ] **Step 4: 執行入口同步 checks**

Run:

```bash
for f in AGENTS.md CLAUDE.md README.md; do
  rg -q '刪除或覆蓋非自己建立的檔案' "$f"
  rg -q '不重複詢問' "$f"
done
rg -q 'for agent in scanner explorer verifier' README.md
rg -q 'max_threads = 4' README.md
rg -q 'max_depth = 1' README.md
rg -q '已套用到：.*40-maintenance.md' rules/50-lessons.md
```

Expected: exit 0。

- [ ] **Step 5: 可選 checkpoint commit**

Only if explicitly authorized:

```bash
git add AGENTS.md CLAUDE.md README.md rules codex/rules docs/superpowers
git status --short
git diff --cached --stat
git diff --cached
git stash list
git commit -m "docs(rules): align tiered agent guidance"
```

Expected before commit: staged diff 只包含 Task 3–6 與已核准 docs，沒有 agent TOML 或未知 stash；否則停止，不 commit。

### Task 7: 安裝 agents 並合併本機 Codex config

**Files:**
- Create symlink: `~/.codex/agents/scanner.toml`
- Create symlink: `~/.codex/agents/explorer.toml`
- Verify symlink: `~/.codex/agents/verifier.toml`
- Modify: `~/.codex/config.toml`

- [ ] **Step 1: 確認 agent 目的地沒有非本次建立的衝突檔案**

Run:

```bash
for agent in scanner explorer verifier; do
  dst="$HOME/.codex/agents/$agent.toml"
  if [ -e "$dst" ] || [ -L "$dst" ]; then ls -ld "$dst"; else echo "missing $dst"; fi
done
test "$(readlink ~/.codex/agents/verifier.toml)" = "/Users/fatjohn/Projects/FatJohn/agents-guideline/codex/agents/verifier.toml"
```

Expected: `scanner`、`explorer` missing；`verifier` 是指向本 repo 的既有 symlink，最後的 `test` exit 0。若任一目的地已存在但不是本 repo 的對應 symlink，停止並詢問使用者，不覆蓋、不刪除、不改名。

- [ ] **Step 2: 建立 scanner/explorer symlink**

Run:

```bash
ln -s /Users/fatjohn/Projects/FatJohn/agents-guideline/codex/agents/scanner.toml ~/.codex/agents/scanner.toml
ln -s /Users/fatjohn/Projects/FatJohn/agents-guideline/codex/agents/explorer.toml ~/.codex/agents/explorer.toml
```

Expected: exit 0，`readlink` 回傳 repo 內的絕對路徑。

- [ ] **Step 3: 合併 `[agents]` 設定**

Create a dedicated non-overwriting config backup and inspect table count before edit:

```bash
CONFIG_BACKUP=~/.codex/backups/config.toml.before-tiered-agents-20260712
test ! -e "$CONFIG_BACKUP"
cp ~/.codex/config.toml "$CONFIG_BACKUP"
AGENTS_TABLE_COUNT=$(rg -c '^\[agents\]$' ~/.codex/config.toml || true)
test "$AGENTS_TABLE_COUNT" -le 1
rg -n '^\[agents\]|^max_threads\s*=|^max_depth\s*=' ~/.codex/config.toml || true
printf 'CONFIG_BACKUP=%s\nAGENTS_TABLE_COUNT=%s\n' "$CONFIG_BACKUP" "$AGENTS_TABLE_COUNT"
```

Expected: backup path did not exist and is now an exact copy；`AGENTS_TABLE_COUNT` is `0` or `1`。If it is greater than `1`, stop without editing and report the pre-existing invalid state；do not “fix” unrelated duplicate tables automatically.

If no `[agents]` table exists, use `apply_patch` to insert before `[features]`:

```toml
[agents]
max_threads = 4
max_depth = 1

```

If a table exists, use `apply_patch` to update only those two keys and preserve all unrelated settings.

- [ ] **Step 4: 驗證安裝與 config 唯一性**

Run:

```bash
for agent in scanner explorer verifier; do
  test -L "$HOME/.codex/agents/$agent.toml"
  test -f "$HOME/.codex/agents/$agent.toml"
done
test "$(rg -c '^\[agents\]$' ~/.codex/config.toml)" = "1"
test "$(rg -c '^max_threads = 4$' ~/.codex/config.toml)" = "1"
test "$(rg -c '^max_depth = 1$' ~/.codex/config.toml)" = "1"
```

Expected: exit 0。

If any config uniqueness/value check fails:

1. Run `diff -u ~/.codex/backups/config.toml.before-tiered-agents-20260712 ~/.codex/config.toml` and read the exact change.
2. Use `apply_patch` to restore `~/.codex/config.toml` to the backup content；do not use a broad overwrite command.
3. Run `cmp -s ~/.codex/backups/config.toml.before-tiered-agents-20260712 ~/.codex/config.toml` and require exit 0.
4. Verify scanner/explorer symlinks still point to files created by this task；remove only those two self-created symlinks with `unlink`, then stop and report config installation as rolled back.

- [ ] **Step 5: 驗證 Codex 啟動接受 config schema**

Start one new Codex CLI/app session and inspect startup output before spawning roles.

Expected: no warning or parse error for `[agents]`、`max_threads`、`max_depth`。If Codex reports an unsupported key, invalid table or config parse error:

1. Run `diff -u ~/.codex/backups/config.toml.before-tiered-agents-20260712 ~/.codex/config.toml` and read the change.
2. Use `apply_patch` to restore the backup content exactly.
3. Require `cmp -s ~/.codex/backups/config.toml.before-tiered-agents-20260712 ~/.codex/config.toml` to exit 0.
4. Verify and `unlink` only the self-created scanner/explorer symlinks.
5. Stop and report local installation as rolled back；do not continue to Task 8 and do not keep an unsupported `[agents]` config.

### Task 8: 靜態驗證、runtime 驗證與雙 verifier 驗收

**Files:**
- Verify: all changed repo files
- Verify: `~/.codex/agents/*.toml`
- Verify: `~/.codex/config.toml`

- [ ] **Step 1: 執行完整靜態驗證**

Run:

```bash
git diff --check
for p in \
  rules/00-environment.md rules/05-hosts.md rules/10-dispatch.md rules/20-judgment.md rules/40-maintenance.md rules/50-lessons.md \
  codex/rules/10-dispatch-codex.md codex/rules/30-delegation-templates-codex.md \
  codex/agents/scanner.toml codex/agents/explorer.toml codex/agents/verifier.toml; do
  test -f "$p"
done
! rg -n 'T[B]D|T[O]DO|待[定]|之後再決[定]' AGENTS.md CLAUDE.md README.md rules codex docs/superpowers
```

Expected: exit 0；`git diff --check` 無輸出，placeholder scan 無結果。

- [ ] **Step 2: 在新 Codex session 驗證角色與模型載入**

Start a new Codex CLI/app session in this repo. Spawn one trivial read-only task per role:

```text
使用 scanner 回報 AGENTS.md 的一級標題與行號，不得寫檔。
使用 explorer 說明 AGENTS.md 如何路由到 Codex dispatch 文件，不得寫檔。
使用 verifier 判定 AGENTS.md 是否包含三條鐵律，不得寫檔。
```

Classify each role independently:

- **模型已驗證**：Subagent activity 或執行資訊明確顯示 `scanner`=Luna、`explorer`=Terra、`verifier`=Sol。
- **模型未驗證**：角色成功啟動，但目前 surface 不顯示實際 model；保留角色輸出證據，不猜測 model。
- **不支援**：`gpt-5.6-luna` 或其他 model 回傳 unsupported/unavailable。依 spec 將 `scanner` 暫時改成 `model = "gpt-5.6-terra"`、`model_reasoning_effort = "low"`，同步更新 Codex dispatch 與 README mapping，再重跑靜態與 runtime 驗證。
- **FAIL**：activity 顯示的 model 與 TOML 不同，且不是明確的 unavailable fallback；停止完成宣稱並保留輸出。

All three roles must return the requested file evidence and leave `git status --short` unchanged. Do not report the model mapping as fully verified unless every role reaches “模型已驗證”.

If `scanner`、`explorer` or `verifier` does not appear as an available role:

1. Run `ls -ld ~/.codex/agents/<role>.toml` and `readlink ~/.codex/agents/<role>.toml`，requiring the target to equal this repo’s `codex/agents/<role>.toml`.
2. Run the Task 2 TOML GREEN checks against the installed target.
3. Close the test session completely and start one new session，then retry the same role once.
4. If it is still absent，mark custom-agent runtime as **blocked**；do not silently claim prompt-only routing is equivalent。Keep repo definitions and config backup intact，present the evidence to the user，and ask whether to investigate the current Codex surface or adopt the spec’s prompt-only fallback.

- [ ] **Step 3: 受控驗證 read-only sandbox**

In the same new session, ask each role to create `read-only-probe.tmp` while explicitly stating this is a sandbox test.

Expected: each role refuses before tool use or its sandbox rejects the write；`test ! -e read-only-probe.tmp` succeeds；`git status --short` does not gain the probe file。若父 session 的 live runtime override 使 per-agent sandbox 無法強制 read-only，回報「角色行為已驗證、sandbox enforcement 未驗證」，不得宣稱 sandbox 已通過。若任何角色實際寫入，runtime verification 為 FAIL，停止完成宣稱。

- [ ] **Step 4: Claude fresh-context verifier**

Give Claude verifier these inputs:

```text
產出檔案：AGENTS.md、CLAUDE.md、README.md、rules/*.md、codex/rules/*.md、agents/verifier.md、codex/agents/*.toml。
驗收條件：
1. Claude model/effort/background/worktree 事實與本機 2.1.207 相符。
2. 共用 rules 不綁死單一平台模型名稱或 dispatch 路徑。
3. 授權、驗證與 single-writer 規則跨檔一致。
4. 所有引用路徑存在。
```

Expected: every item PASS；FAIL 必須先修正再重跑。

- [ ] **Step 5: Codex fresh-context verifier**

Give Codex verifier these inputs:

```text
產出檔案：AGENTS.md、README.md、rules/*.md、codex/rules/*.md、codex/agents/*.toml。
驗收條件：
1. scanner/explorer/worker/verifier 角色、模型、effort、權限與升降級一致。
2. Luna 不可寫入、不可做高風險或最終驗收。
3. single-writer、worktree、blocking background 與 controller read-back 規則可執行。
4. config/安裝/README 指示與實際 symlink 一致。
```

Expected: every item PASS；FAIL 必須先修正再重跑。

- [ ] **Step 6: 最終 read-back 與狀態分級**

Run:

```bash
git status --short
git diff --stat
git diff -- AGENTS.md CLAUDE.md README.md rules codex docs/superpowers
git stash list
```

Expected: 只包含核准範圍；沒有未知 stash。回報分成：已驗證、待新 session runtime 驗證、未驗證，不把未跑的 runtime checks 宣稱為通過。

- [ ] **Step 7: 可選最終 commit**

Only if explicitly authorized and all required verification is PASS:

```bash
git add AGENTS.md CLAUDE.md README.md rules codex docs/superpowers
git status --short
git diff --cached --stat
git diff --cached
git stash list
git commit -m "feat(rules): add tiered Codex subagent routing"
```

Expected before commit: staged diff 只包含本計畫核准範圍，所有 verifier/runtime 狀態已在回報中分級，沒有未知 stash；否則停止，不 commit。

Do not push unless the user separately authorizes push in the current session.
