# Codex 分級 Subagent 調度與全域規則校正設計

日期：2026-07-12
狀態：方案 B 已經使用者 review 核准並完成首版實作；2026-07-14 model tier revision 已核准，將一般驗證與高風險驗證分層。

## 目標

在保留現有「角色導向」工作制度的前提下，將 GPT-5.6 Sol、Terra、Luna 納入 Codex subagent 調度，並修正本次全域規則 review 發現的跨平台矛盾、過時事實、並行寫入風險與驗證語意問題。

成功條件：

1. Agent 的公開介面仍以 `scanner`、`explorer`、`planner`、`worker`、`recovery-worker`、`reviewer`、`verifier`、`sol-verifier` 等職責命名，不讓工作流程綁死在特定世代模型名稱。
2. 每個角色有清楚的模型、reasoning effort、權限與升級條件。
3. Luna 不負責高風險判斷、對外動作或最終驗收；一般 approved-plan 實作可由 `worker` 在明確授權的 workspace-write 範圍內完成。
4. Claude 與 Codex 共用規則使用平台中立語彙；平台特定模型映射留在各自的 dispatch 文件。
5. 同一 working tree 不允許多個 agent 同時寫入；平行寫入必須使用獨立 worktree，不重疊範圍只能序列寫入。
6. 所有完成宣稱都有可重現的指令輸出或 fresh-context read-back 證據。

## 非目標

- 不把 Claude 與 Codex 的工具參數或 agent 格式硬統一成同一份檔案。
- 不改變「對外動作需本 session 明確授權」的邊界。
- 不用 Chronicle 取代 Memories、handoff 或 repo 文件。
- 不讓 subagent 自動遞迴派工。
- 不把所有工作都強制派給 subagent；派工仍取決於任務獨立性與 context 成本。

## 架構原則

### 角色是穩定介面，模型是可替換實作

規則與 prompt 以角色描述工作責任；agent 定義才固定當代模型。未來模型名稱改變時，只需更新角色到模型的映射，不必重寫派工模板與判斷準則。

| 角色 | GPT-5.6 模型 | Effort | 權限 | 適用工作 |
|---|---|---|---|---|
| `scanner` | Luna | medium | read-only | 精確清單、分類、格式檢查、結構化抽取 |
| `explorer` | Terra | medium | read-only | repo 探索、跨檔追蹤、文件研究、影響範圍分析 |
| `planner` | Terra | high | read-only | 非平凡任務規劃、invariants、failure modes 與驗收條件 |
| `worker` | Luna | max | workspace-write | 依 approved plan 實作、除錯與機械驗證 |
| `recovery-worker` | Terra | xhigh | workspace-write | Luna worker 同一子任務兩次失敗或揭露高風險後的 root-cause recovery 實作 |
| `reviewer` | Terra | high | read-only | 一般實作 fresh-context review |
| `verifier` | Terra | high | read-only | 一般文件、read-back 與驗收 |
| `escalation-planner` | Sol | xhigh | read-only | Terra planner／explorer 無法建立可靠方案時的規劃升級 |
| `escalation-worker` | Sol | xhigh | workspace-write | Luna 兩次失敗後，Terra recovery 再兩次失敗或確認 root cause 需要 Sol 能力時的 final root-cause 實作 |
| `sol-verifier` | Sol | high | read-only | 安全、不可逆、重大架構與正式高風險驗收 |

以上 active role 都使用明確的 custom agent TOML。一般升級路徑為 `Luna max → Terra xhigh → Sol xhigh`；`Sol max` 不作為固定 agent，只能由 controller 在 `Sol xhigh` 仍無法收斂或明確遇到最困難單一路徑時顯式使用；`Sol Ultra` 僅限可獨立平行的大型工作流。一般文件與一般驗收使用 `verifier/Terra high`，安全、不可逆、重大架構與正式高風險驗收使用 `sol-verifier/Sol high`。

`read-only` 同時是角色行為合約與 custom agent 的 sandbox 偏好；父 session 的 live runtime permission override 可能優先於 agent TOML，因此不能只靠 sandbox。Agent instructions 必須拒絕寫入，controller 也必須用 git 狀態 read-back 驗證沒有變更。

## 派工與升降級

### 派工判斷

不再只用「原始內容超過一頁」作唯一門檻。符合下列任一情況才優先派工：

- 任務可獨立完成，主對話只需要結論與證據。
- 原始輸出量大，而且後續不需要主對話反覆引用全部內容。
- 有兩個以上互不依賴的子任務，可安全平行。
- 需要 fresh-context 第二意見或對抗式驗收。

以下情況保留在主對話：

- 工作很小但與目前決策高度耦合。
- 多步驟操作需要頻繁共享同一份可變狀態。
- 使用者正在做需要即時互動的品味或需求選擇。
- 平行寫入無法安全隔離。

### 升級路徑

1. 非平凡任務先用 `planner/Terra high → worker/Luna max → reviewer/Terra high`；小型、範圍清楚的修改留在主對話。
2. planner 或 explorer 若 high／medium 路徑仍無法形成可靠 plan，先 fresh rerun `planner/Terra xhigh`，再升 `escalation-planner/Sol xhigh`。
3. worker 同一子任務失敗兩次先升 `recovery-worker/Terra xhigh`；recovery 在同一子任務再失敗兩次，或 recovery 已確認 root cause 需要 Sol 能力時，再升 `escalation-worker/Sol xhigh`。
4. 一般文件／一般驗收用 `verifier/Terra high`；安全、不可逆、重大架構或正式高風險驗收用 `sol-verifier/Sol high`。
5. Sol xhigh 仍卡住時，換 fresh-context Sol、加入獨立第二意見或重新定義問題；只有 controller 顯式判定仍需最終能力時才使用 Sol max。
6. 高能力模型確認可重複 pattern 後，可降回 Terra 或 Luna 批次套用；輸出仍需機械驗證。

## 並行與工作目錄安全

同一 working tree 同時只能有一個寫入者。主 agent 要讓多個 agent 平行寫入時，每個寫入者都必須使用獨立 git worktree；只切割互不重疊的檔案不足以隔離共享 index、branch、stash 與 working-tree 狀態。

若無法建立獨立 worktree，可以明確指定互不重疊的檔案所有權，但寫入任務必須序列執行，且 subagent 禁止 branch、stash、commit、push 操作。

主 agent 在 commit 前必須重新執行並閱讀：

- `git status --short`
- `git diff --cached`
- `git stash list`

Subagent 的「已完成」回報不代表 worktree 實際狀態；controller 必須 read-back diff、commit 與驗證輸出。需要其結果才能繼續的 blocking 任務不得只依賴容易因休眠或背景 session 中斷而消失的背景執行。

Codex 全域設定建議固定：

```toml
[agents]
max_threads = 4
max_depth = 1
```

`max_depth = 1` 明確阻止遞迴派工；`max_threads = 4` 配合目前 surface 的並行上限，避免規則以為可同時啟動更多 agent。

## 驗證模型

「驗證不自驗」改成下列精確語意：

- 主觀判斷、一般文件與一般驗收不得由製作者自己背書，必須由 fresh-context `verifier/Terra high` 驗收；安全、不可逆、重大架構與正式高風險產出改由 `sol-verifier/Sol high` 或獨立第二意見驗收。
- 測試、build、lint、實跑、schema 驗證等可重現的機械驗證可以由製作者執行，但必須回報指令與結果。
- 高風險程式碼除機械驗證外，再加 fresh-context review。
- `verifier` 與 `sol-verifier` 僅 read-only，不參與製作，也不直接修正發現的問題。

## 共用規則校正

### 平台中立化

`rules/20-judgment.md` 改用「輕量層／標準層／高能力層」與「對應平台 dispatch 文件」；Claude 的 Haiku/Sonnet/Opus/Fable 與 Codex 的 Luna/Terra/Sol 映射分別留在平台專用文件。

`rules/00-environment.md` 同時指向 Claude 與 Codex dispatch 文件，不再讓 Codex 共用內容只引用 Claude 路徑。

### 授權邊界同步

`AGENTS.md`、`CLAUDE.md`、README 與 `rules/20-judgment.md` 使用同一份對外／不可逆動作清單：

- 發訊息與寄信
- merge PR
- push 共享分支
- 發佈
- 刪除或覆蓋非自己建立的檔案

使用者在本 session 已明確要求該動作時可直接執行，不重複詢問。

### Claude 事實更新

依本機 Claude Code 2.1.207 與當前官方文件更新：

- Subagent `effort` 可用 `low`、`medium`、`high`、`xhigh`、`max`，仍以實際模型支援為準。
- `model` 可使用 `haiku`、`sonnet`、`opus`、`fable`、完整 model ID 或 `inherit`。
- 記錄新版 background 預設與 `isolation: worktree` 能力，並將實際事故轉成 blocking 任務與寫入隔離規則。

### Session 狀態與記憶

Session 內狀態優先使用平台 plan/task 機制，不強制在 repo 建立未定義的 scratchpad。只有跨 session 需要接續時，才依 `session-handoff` skill 寫 `.codex/HANDOFF.md`。

Chronicle 僅記錄為可選的螢幕脈絡來源：不取代 Memories、handoff 或 repo 制度；因其隱私、rate limit 與 prompt injection 風險，不列為預設啟用項目。

### 主機識別

`rules/05-hosts.md` 的主力機段落增加目前可驗證的穩定特徵：macOS 26.5.2、arm64、repo 路徑與工具狀態；hostname `Mac` 只作參考，不作唯一識別。

## 2026-07-14 model tier revision 實際變更範圍

本次 revision 實際調整以下既有檔案：

- `AGENTS.md`
- `README.md`
- `rules/10-dispatch.md`
- `codex/agents/escalation-planner.toml`
- `codex/agents/escalation-worker.toml`
- `codex/agents/explorer.toml`
- `codex/agents/planner.toml`
- `codex/agents/reviewer.toml`
- `codex/agents/verifier.toml`
- `codex/agents/worker.toml`
- `codex/rules/10-dispatch-codex.md`
- `codex/rules/30-delegation-templates-codex.md`
- `docs/superpowers/specs/2026-07-12-codex-tiered-subagent-routing-design.md`

本次新增以下 agent 定義：

- `codex/agents/recovery-worker.toml`
- `codex/agents/sol-verifier.toml`

## 首版方案的預計檔案變更（歷史對照）

> 以下清單保留 2026-07-12 初始方案的預計範圍，不代表本次 2026-07-14 revision 的完整變更清單。

新增：

- `codex/agents/scanner.toml`
- `codex/agents/explorer.toml`

修改：

- `codex/agents/verifier.toml`
- `codex/rules/10-dispatch-codex.md`
- `codex/rules/30-delegation-templates-codex.md`
- `rules/00-environment.md`
- `rules/05-hosts.md`
- `rules/10-dispatch.md`
- `rules/20-judgment.md`
- `rules/40-maintenance.md`
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`

本機安裝更新：

- 將新增 Codex agent TOML symlink 至 `~/.codex/agents/`。
- 備份後在 `~/.codex/config.toml` 加入或合併 `[agents]` 設定。

`rules/50-lessons.md` 保留歷史原文；已升級的教訓在正式規則落地後標註套用位置，不刪除歷史證據。

## 驗證計畫

1. `git diff --check`：確認格式與空白錯誤。
2. 檢查所有 Markdown 引用路徑與安裝 symlink 實際存在。
3. 驗證 custom agent TOML 必填欄位、model、effort 與 sandbox 設定。
4. 在新 Codex session 實際 spawn 全部 active custom agents，從 subagent activity 或執行資訊確認載入的角色與模型符合定義。
5. 對 `scanner`、`explorer`、`planner`、`reviewer`、`escalation-planner`、`verifier`、`sol-verifier` 執行受控寫入要求；預期角色自行拒絕或 read-only sandbox 拒絕，且 repo 內容與 git 狀態不變。若父 session runtime override 使 sandbox 未強制 read-only，必須明確記錄，不能宣稱 sandbox 已驗證。
6. 對 `worker`、`recovery-worker`、`escalation-worker` 驗證只能寫入父 prompt 明確授權的 workspace 與範圍，且禁止 branch、stash、commit、push 與對外／不可逆動作。
7. 確認 `~/.codex/config.toml` 合併後沒有重複 `[agents]` table，且原設定未遺失。
8. 使用 Claude fresh-context verifier 驗收共用與 Claude 規則。
9. 使用 Codex fresh-context `verifier/Terra high` 驗收一般共用與 Codex 規則；高風險範圍使用 `sol-verifier/Sol high`。
10. 逐條比對三鐵律、授權清單、升級路徑、角色映射與 README，確認沒有跨檔矛盾。
11. 最後確認 `git status --short` 只包含本次核准範圍內的變更。

## 失敗處理

- 若 Luna 在本機 Codex custom agent 路徑不可用，`scanner` 暫時改用 Terra/low；不得靜默繼承父 session。
- 若 custom agent 未出現在可用角色中，先檢查 symlink、TOML schema 與新 session 載入，再判斷是否回退成 prompt-only routing。
- 若本機 config 與官方 schema 衝突，保留備份、回復 config 變更，repo 文件標註該項未啟用。
- 若 Claude 與 Codex verifier 對共用規則有不同判定，將分歧呈給使用者，不自行選擇較寬鬆的一邊。
