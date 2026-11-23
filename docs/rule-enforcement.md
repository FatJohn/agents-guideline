# 規則由什麼強制

讀者：在本 repo 維護全域制度的 session
型別：參考

本檔不安裝、不常駐；用法見 `.claude/skills/maintain-guideline/SKILL.md` §3「教訓寫回」與 §5「瘦身協議」。本檔只描述現況。改規則、hook 或腳本閘門的同一次修改一起改對應列；`tests/test_rule_enforcement.py` 在下列情況失敗：`judgment.md` 多一條而 Claude 段或 Codex 段沒有對應列、`global/claude/hooks/` 多一支 hook、`global/codex/AGENTS.md`「邊界」多一條、`global/codex/rules/` 多一份檔或 `global/codex/agents/` 多一個 TOML 而本表沒有對應列；也核對機械強制列的檔案與符號存在。

前半段是 Claude 端，「Codex 端」以下各段是 Codex 端。同一條規則兩端的強制方式不同時，看兩段的同名列。

## 「由什麼強制」的值

| 值 | 意思 |
|---|---|
| hook | Claude Code hook 在違反時擋下或注入，不靠模型記得 |
| 腳本 | 有人或流程呼叫時，腳本以 exit code 判過或不過 |
| 測試 | `tests/`、`scripts/tests/` 的測試在違反時變紅 |
| 設定 | 安裝的設定檔改了工具的預設行為，不照做也會得到正確結果；Codex 角色 TOML 的 model／effort 也算，但只在該角色真的被選中時生效。TOML 的 `sandbox_mode` 不算，理由見「Codex 端：角色」 |
| verifier 合約 | 派了 verifier 時由驗收角色的定義判定：Claude 是 `global/claude/agents/verifier.md`，Codex 是 `global/codex/agents/verifier.toml`／`sol_verifier.toml` 的 `developer_instructions`；不派就沒有東西會失敗 |
| 注入文字 | 由平台在 session 開頭放進 context，不必主動去讀，但跳過它沒有東西會失敗。Claude：入口、`judgment.md`、路由卡；Codex：本 repo 只有入口 `global/codex/AGENTS.md`（依據與限制見「Codex 端：載入方式」），另外派出的角色會讀到自己 TOML 的 `developer_instructions` |
| 按需文字 | 只寫在 skill、docs 或入口路由指向的檔裡，要讀了才知道 |

一條規則只有部分被機器擋住時，值寫整條規則在常見違反情境下的狀態，部分強制寫在備註。「強制點」欄：值是 hook、腳本、測試、設定或 verifier 合約時，第一個反引號是檔案路徑，其後每個反引號都是該檔內 `rg` 得到的符號或檢查名；其餘值寫「—」。

## judgment.md

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/shared/rules/judgment.md` 1「完成的三個條件」 | 注入文字 | — | 派了 verifier 時逐條判定由 verifier 合約承接；不派沒有東西會失敗 |
| `global/shared/rules/judgment.md` 2「不可逆副作用的定義」 | 注入文字 | — | 定義條，verifier 第一行的風險分流引用它 |
| `global/shared/rules/judgment.md` 3「殘留掃描」 | 注入文字 | — | 「`rg` 加 `--hidden`」那部分由下方 ripgreprc 列承接 |
| `global/shared/rules/judgment.md` 3「殘留掃描」：搜尋含隱藏目錄 | 設定 | `global/claude/config/ripgreprc` 的 `--hidden` | 只在 `RIPGREP_CONFIG_PATH` 指到這份檔時生效；Grep 工具與 `grep` 不受影響 |
| `global/shared/rules/judgment.md` 4「未驗證的意思」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 5「驗到被嵌的那一層」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 6「修正者的證據」 | verifier 合約 | `global/claude/agents/verifier.md` 的 `修正者的證據` | verifier 規則 4 要求判定前必讀；製作者不附證據時，要派了 verifier 才會被抓 |
| `global/shared/rules/judgment.md` 7「驗收的停止端」 | verifier 合約 | `global/claude/agents/verifier.md` 的 `INCONCLUSIVE` `CONVERGED` | verifier 第一行狀態與下一步 |
| `global/shared/rules/judgment.md` 8「可證偽宣稱」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 9「放寬防線要實跑證據」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 10「改既有檢查」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 11「指令自己綁定目標」 | 注入文字 | — | `allow-git-c-projects.sh` 讓 `git -C` 少問權限，不會擋沒綁目標的指令 |
| `global/shared/rules/judgment.md` 12「驗收條件要能被判定」 | verifier 合約 | `global/claude/agents/verifier.md` 的 `模糊到無法機械判定` | verifier 規則 1：模糊條件直接判 FAIL |
| `global/shared/rules/judgment.md` 13「除錯前先驗環境」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 14「現況證據與規格權威」 | 注入文字 | — | |
| `global/shared/rules/judgment.md` 15「改動要最小且可追溯」 | 注入文字 | — | |

## 路由卡（`global/claude/route-card.md`）

整張卡由 `controller-context.sh` 注入主對話（見下方 hook 段）；下列是卡內各條目本身的強制狀態。

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/claude/route-card.md` 開頭段：controller 自己做、預設在 worktree、動手前寫驗收條件 | 注入文字 | — | |
| `global/claude/route-card.md`「subagent 只有三類」：驗收列 | 注入文字 | — | verifier 的 model 由其 frontmatter 固定；何時派、派幾輪沒有東西會失敗 |
| `global/claude/route-card.md`「subagent 只有三類」：程式碼 diff 的 fresh review 列 | 注入文字 | — | |
| `global/claude/route-card.md`「subagent 只有三類」：旁支查詢列 | 注入文字 | — | |
| `global/claude/route-card.md`「subagent 只有三類」：使用者說開新 session 段 | 注入文字 | — | 開出來的 issue session 帶不帶 model／effort 由 `require-issue-session-model.sh` 擋；開不開、開成什麼形狀不擋 |
| `global/claude/route-card.md`「subagent 只有三類」：≥2 個獨立 issue 一 issue 一 session 段 | 注入文字 | — | |
| `global/claude/route-card.md`「Brief」 | 注入文字 | — | |
| `global/claude/route-card.md`「寫入」 | verifier 合約 | `global/claude/agents/verifier.md` 的 `受驗狀態` `工作區在驗收期間被改動` | verifier 規則 8 開始與判定前各取一次 HEAD＋tracked 改動指紋，不同就判 `INCONCLUSIVE`：只事後發現、不阻止寫入；未追蹤檔不在指紋內，驗收期間新增的未追蹤檔抓不到；不派 verifier 沒有東西會失敗 |
| `global/claude/route-card.md`「揭露與授權」：派工揭露與授權段 | 注入文字 | — | |
| `global/claude/route-card.md`「揭露與授權」：驗收後修正分流段 | 注入文字 | — | verifier 合約只管第一行寫出分流；controller 拿到後照不照做（機械結案後不重派、不自行降級、第三輪停下）沒有東西會失敗 |

## 入口邊界（`global/claude/CLAUDE.md`「邊界」）

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/claude/CLAUDE.md`「邊界」1：專案 `CLAUDE.md` 優先 | 注入文字 | — | |
| `global/claude/CLAUDE.md`「邊界」2：無證據不宣稱完成 | 注入文字 | — | |
| `global/claude/CLAUDE.md`「邊界」3：對外或不可逆動作需當次授權 | 注入文字 | — | `~/.claude/settings.json` 的 permissions 與 auto mode 分類器擋一部分，那份設定不在本 repo；主對話用 Edit／Write 類工具改 CI 設定由 `block-ci-edit.sh` 擋 |
| `global/claude/CLAUDE.md`「邊界」4：驗證不自驗 | 注入文字 | — | 不派 verifier 沒有東西會失敗 |
| `global/claude/CLAUDE.md`「邊界」5：同一 working tree 一個寫入者 | 注入文字 | — | |
| `global/claude/CLAUDE.md`「邊界」6：長任務留可恢復脈絡 | 注入文字 | — | `context-size-nudge.sh` 只在 context 跨門檻時提醒交接，不檢查有沒有留 |

## hook（`global/claude/hooks/`）

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| 路由卡只注入主對話 | hook | `global/claude/hooks/controller-context.sh` 的 `CLAUDE_ROUTE_CARD` | SessionStart；subagent 不跑 SessionStart |
| `docs/dispatch.md` §3「派工合約與回報」：主對話不默改 CI 設定 | hook | `global/claude/hooks/block-ci-edit.sh` 的 `.github/(workflows` | 只擋 Edit／Write 類工具；用 Bash 改不擋 |
| `docs/dispatch.md` §6「主對話 context 管理」：跨門檻要交接 | hook | `global/claude/hooks/context-size-nudge.sh` 的 `CLAUDE_CTX_NUDGE_THRESHOLD` | PostToolUse 注入提醒，不阻擋 |
| 窄形狀的 `git -C <path>` 不問權限 | hook | `global/claude/hooks/allow-git-c-projects.sh` 的 `flag_allowed` | 放行型，不擋任何指令；其餘交給一般權限流程 |
| worktree-session `references/cli.md`：issue session 啟動要帶 model 與 effort | hook | `global/claude/hooks/require-issue-session-model.sh` 的 `--effort` | 只查有沒有帶，值是 cli.md 的政策 |

## 腳本閘門與測試

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| worktree-session §3「直接清」的條件 | 腳本 | `scripts/worktree-clean-check.py` 的 `check_delivery` `check_tree` | fail-closed；盤點 session 清 worktree 前跑；使用者說做完或授權清時帶 `--user-authorized`，不看 `result.md` 自報欄位與 `Keep ignored` |
| writing-principles 可機械判定的原則 | 腳本 | `global/shared/skills/writing-principles/scripts/check_docs.py` 的 `check_header` `check_links` `check_heading_refs` | 寫文件與 verifier 驗文件時跑 |
| agent-rules：規則索引單一來源、reviewer 版本 ID 與 severity 對得上 | 腳本 | `global/shared/skills/agent-rules/scripts/rules_index.py` 的 `check_rules` | 用在別的專案 repo，不管本系統 |
| 本表涵蓋每條 judgment 與每支 hook，機械強制點存在 | 測試 | `tests/test_rule_enforcement.py` 的 `test_every_judgment_entry_has_a_row` `test_every_hook_has_a_row` `test_mechanical_rows_point_at_existing_symbols` | |

## Codex 端：載入方式

Codex 端的強制方式跟 Claude 端有三處不同，下面各段的值都由此而來：

- 本 repo 裝進 Codex 的全域規則只有入口：Codex 在 session 開頭把全域 `~/.codex/AGENTS.md`（來源 `global/codex/AGENTS.md`）當「AGENTS.md instructions」注入，專案自己的 `AGENTS.md` 另外注入；`judgment.md` 不注入，只在入口「路由」表的「寫或改程式碼的範圍、完成、證據、驗收狀態」列指過去。依據：`scripts/sync-profile.py` 的 `default_mappings` 只把 `global/codex/AGENTS.md` 裝進 Codex 目錄；查過的一筆 session jsonl 有入口全文、沒有 `judgment.md` 的內文，已實測（2026-11-20，codex-cli 0.169.0），只查一筆，不代表每種啟動方式都一樣。所以 `judgment.md` 在 Codex 端是按需文字。
- 沒有路由卡，`global/codex/rules/` 也不注入：`dispatch.md` 與 `delegation-templates.md` 要照入口路由表去讀，主對話與 subagent 讀的是同一份。
- 本 repo 不提供、不安裝 Codex hook：`global/codex/` 只有 `AGENTS.md`、`rules/`、`agents/`，同步腳本不碰 `~/.codex/hooks.json`。Codex CLI 本身有 hook 機制，`codex features list` 列 `hooks` 為 stable，已實測（2026-11-20，codex-cli 0.169.0），只是本系統沒用。Claude 端五支 hook 補的規則，在 Codex 端最多是文字。

## Codex 端：judgment.md

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/shared/rules/judgment.md` 1「完成的三個條件」 | 按需文字 | — | Claude 端是注入文字。派了驗收角色時逐條判定由 `verifier.toml`／`sol_verifier.toml` 承接 |
| `global/shared/rules/judgment.md` 2「不可逆副作用的定義」 | 按需文字 | — | Claude 端是注入文字。`reviewer.toml` 規則 3、`sol_verifier.toml` 規則 3 與兩份 verifier TOML 的第一行分流引用它 |
| `global/shared/rules/judgment.md` 3「殘留掃描」 | 按需文字 | — | Claude 端是注入文字，加上 ripgreprc 設定承接 `--hidden`。本 repo 只教在 `~/.claude/settings.json` 設 `RIPGREP_CONFIG_PATH`（`docs/install.md`），Codex 端沒有對應設定；Codex 的 Bash 拿不拿得到這個變數：未實測 |
| `global/shared/rules/judgment.md` 4「未驗證的意思」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 5「驗到被嵌的那一層」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 6「修正者的證據」 | verifier 合約 | `global/codex/agents/verifier.toml` 的 `修正者的證據` | 與 Claude 端相同。`sol_verifier.toml` 規則 6 同樣要求判定前必讀；製作者不附證據時，要派了驗收角色才會被抓 |
| `global/shared/rules/judgment.md` 7「驗收的停止端」 | verifier 合約 | `global/codex/agents/verifier.toml` 的 `INCONCLUSIVE` `CONVERGED` | 與 Claude 端相同。`sol_verifier.toml` 規則 6、9 同樣寫第一行狀態與下一步 |
| `global/shared/rules/judgment.md` 8「可證偽宣稱」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 9「放寬防線要實跑證據」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 10「改既有檢查」 | 按需文字 | — | Claude 端是注入文字。兩份 verifier TOML 的 delta 規則要求修正放寬既有檢查時照它做對抗性探測 |
| `global/shared/rules/judgment.md` 11「指令自己綁定目標」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 12「驗收條件要能被判定」 | 按需文字 | — | Claude 端是 verifier 合約；Codex 的 verifier TOML 沒有「模糊條件直接判 FAIL」這條。派工方的判準寫在 `dispatch.md` §3「派工三件套」第 2 項與共用 `handoff` skill §1「brief 卡」 |
| `global/shared/rules/judgment.md` 13「除錯前先驗環境」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 14「現況證據與規格權威」 | 按需文字 | — | Claude 端是注入文字 |
| `global/shared/rules/judgment.md` 15「改動要最小且可追溯」 | 按需文字 | — | Claude 端是注入文字 |

## Codex 端：入口（`global/codex/AGENTS.md`）

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/codex/AGENTS.md`「邊界」1：專案 `AGENTS.md` 優先 | 注入文字 | — | 與 Claude 端相同 |
| `global/codex/AGENTS.md`「邊界」2：無證據不宣稱完成 | 注入文字 | — | 與 Claude 端相同 |
| `global/codex/AGENTS.md`「邊界」3：對外或不可逆動作需當次授權 | 注入文字 | — | Claude 端同為注入文字，但另有 permissions、auto mode 分類器與 `block-ci-edit.sh` 擋一部分；Codex 端能擋的是本機 `~/.codex/config.toml` 的 sandbox／approval 與 `~/.codex/rules/*.rules` 命令規則，都不在本 repo |
| `global/codex/AGENTS.md`「邊界」4：驗證不自驗 | 注入文字 | — | 與 Claude 端相同：不派驗收角色沒有東西會失敗。fallback 的身份標記規則在 `dispatch.md` §0 |
| `global/codex/AGENTS.md`「邊界」5：同一 working tree 一個寫入者 | 注入文字 | — | 與 Claude 端相同 |
| `global/codex/AGENTS.md`「邊界」6：長任務留可恢復脈絡 | 注入文字 | — | Claude 端另有 `context-size-nudge.sh` 跨門檻提醒；Codex 端只有文字：本條、`handoff` skill §4「session 交接卡」的何時寫，以及 `dispatch.md` §1 的 300K 分流 |
| `global/codex/AGENTS.md`「路由」：各情境先讀哪份檔 | 注入文字 | — | 路由表本身隨入口注入；指過去的檔是按需文字 |
| `global/codex/AGENTS.md`「Codex 注意」1：不把本 repo 的 `.md` 連進 `~/.codex/rules/` | 注入文字 | — | `docs/install.md` 與 `scripts/sync-profile.py` 都不寫 `~/.codex/rules/`，照安裝步驟不會做錯；手動連結不擋 |
| `global/codex/AGENTS.md`「Codex 注意」2：派工揭露與 fallback 標記 | 注入文字 | — | 細則在 `dispatch.md` §3「派工三件套」 |
| `global/codex/AGENTS.md`「Codex 注意」3：實作留在主對話，subagent 只派三類 | 注入文字 | — | Claude 端是路由卡注入文字；兩端都沒有東西擋實作型派工 |
| `global/codex/AGENTS.md`「Bootstrap」：認機器、展開 `<REPO>` | 注入文字 | — | |

## Codex 端：規則檔（`global/codex/rules/`）

兩份都是入口路由指過去的按需文字；下列是各段本身的強制狀態。

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/codex/rules/dispatch.md` §0「Codex 角色與 runtime adapter」：角色表與 model／effort | 設定 | `global/codex/agents/verifier.toml` 的 `model = "gpt-5.6-terra"` `model_reasoning_effort = "high"` | 選中 named role 時 model／effort 由各角色 TOML 固定，child metadata 對得上 TOML，已實測（2026-09-08，codex-cli 0.153.4；`docs/reviews/codex-named-agent-registration.md`）；走 `default` 或 direct CLI 時要 controller 自己傳，只有文字 |
| `global/codex/rules/dispatch.md` §0：adapter 證據、fallback 身份標記、不冒稱 custom role | 按需文字 | — | Claude 端 `docs/dispatch.md` §3「派工合約與回報」也要求標 fallback，同為按需文字；adapter envelope 的證據分層是 Codex 專有 |
| `global/codex/rules/dispatch.md` §1「派工判斷」：controller 工作迴圈 | 按需文字 | — | Claude 端對應 `docs/dispatch.md`，也是按需文字 |
| `global/codex/rules/dispatch.md` §1：CI／release 設定不靜默自改 | 按需文字 | — | Claude 端由 `block-ci-edit.sh` 擋 Edit／Write 類工具 |
| `global/codex/rules/dispatch.md` §1：多 issue 分 session、主對話 context 很大且還有未做的 phase 時開新 session | 按需文字 | — | 「很大」在 runtime 有可靠數字時是 ≥300K，沒有時看退化證據。Claude 端 300K 由 `context-size-nudge.sh` 提醒；開 issue session 帶 model／effort 由 `require-issue-session-model.sh` 擋，該 hook 對 `--agent codex` 放行 |
| `global/codex/rules/dispatch.md` §2「工作目錄與執行安全」 | 按需文字 | — | |
| `global/codex/rules/dispatch.md` §3「派工三件套」 | 按需文字 | — | |
| `global/codex/rules/dispatch.md` §4「回報與證據合約」 | 按需文字 | — | 五個角色 TOML 都寫「依 §4 回報」，派了角色時由各 TOML 帶著，但沒有檢查 |
| `global/codex/rules/dispatch.md` §5「卡住時」 | 按需文字 | — | |
| `global/codex/rules/dispatch.md` §6「驗證語意」 | 按需文字 | — | 派了驗收角色後的判定由 verifier 合約承接；派不派、派哪個沒有東西會失敗 |
| `global/codex/rules/delegation-templates.md`：六份派工模板與 adapter envelope | 按需文字 | — | Claude 端沒有對應檔，brief 格式在 `handoff` skill §1 |

## Codex 端：角色（`global/codex/agents/`）

TOML 由 `scripts/sync-codex-agents.py` 複製成 `~/.codex/agents/` 的實體檔，該腳本核對 `name`／`description`／`developer_instructions` 存在且 `name` 等於檔名。

TOML 的 `sandbox_mode` 不當成機器擋：選中 named `explorer` 時 model／effort 對得上 TOML，live `sandbox_policy` 卻繼承父 session 的 `workspace-write`，已實測（2026-09-08，codex-cli 0.153.4；`docs/reviews/codex-named-agent-registration.md`）；0.169.0 未實測。`dispatch.md` §0「Runtime adapter」要求 controller 選一條權限唯讀的路徑：named role 的權限 metadata 要符合角色表（第 1 項；surface metadata 只算工具宣告值，child metadata 讀回才算 runtime 已驗證），generic `default` 只在父 session 已是 read-only 時可派，否則走 `--sandbox read-only` 的 direct CLI 或停止（第 3 項）。只有 effective sandbox 確認是 read-only 的那次派送，唯讀才由 runtime 擋；選哪條路徑、有沒有讀回確認都只有文字，named role 在權限不符時照樣派得出去，所以唯讀角色列記為注入文字。

「不再 spawn subagent」五份 TOML 都寫在合約裡；`docs/install.md` 建議的 `[agents] max_depth = 1` 用意是限制遞迴，但沒有實跑 nested spawn 驗證，本表不把它算成機器擋。

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/codex/agents/scanner.toml`：唯讀掃描、不寫 repo | 注入文字 | — | 派出的 scanner 讀到自己的合約；「不寫 repo」「超界交回」都沒有東西擋 |
| `global/codex/agents/explorer.toml`：唯讀探索、不寫 repo | 注入文字 | — | 同 scanner |
| `global/codex/agents/reviewer.toml`：唯讀 fresh review | 注入文字 | — | finding 自查照 `review-findings.md` 也是合約文字。Claude 端的 fresh review 是 `general-purpose` 跑內建 `code-review`，不寫 repo 同樣只靠 brief |
| `global/codex/agents/verifier.toml`：一般驗收逐條判定、只寫 repo 外探針目錄 | verifier 合約 | `global/codex/agents/verifier.toml` 的 `verifier 角色使用錯誤` `INCONCLUSIVE` `受驗狀態` | repo 內不寫只靠合約與 controller 事後 read-back，合約規則 1 自述 sandbox 不擋 repo 內。Claude 端 `verifier.md` 的 `tools` 不含 Edit／Write。規則 13 兩次取受驗狀態，驗收期間工作區被改動判 `INCONCLUSIVE`，同 Claude 端「寫入」列 |
| `global/codex/agents/sol_verifier.toml`：高風險驗收 | verifier 合約 | `global/codex/agents/sol_verifier.toml` 的 `verifier 角色使用錯誤` `INCONCLUSIVE` `受驗狀態` | 寫入限制同 `verifier.toml`；受驗狀態比對在規則 10。Claude 端沒有獨立高風險角色，同一個 verifier 處理 |
