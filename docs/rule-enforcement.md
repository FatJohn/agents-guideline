# 規則由什麼強制

讀者：在本 repo 維護全域制度的 session
型別：參考

本檔不安裝、不常駐；用法見 `.claude/skills/maintain-guideline/SKILL.md` §3「教訓寫回」與 §5「瘦身協議」。本檔只描述現況。改規則、hook 或腳本閘門的同一次修改一起改對應列；`tests/test_rule_enforcement.py` 在 `judgment.md` 多一條或 `global/claude/hooks/` 多一支 hook 而本表沒有對應列時失敗，也核對機械強制列的檔案與符號存在。

## 「由什麼強制」的值

| 值 | 意思 |
|---|---|
| hook | Claude Code hook 在違反時擋下或注入，不靠模型記得 |
| 腳本 | 有人或流程呼叫時，腳本以 exit code 判過或不過 |
| 測試 | `tests/`、`scripts/tests/` 的測試在違反時變紅 |
| 設定 | 安裝的設定檔改了工具的預設行為，不照做也會得到正確結果 |
| verifier 合約 | 派了 verifier 時由 `global/claude/agents/verifier.md` 的規則判定；不派就沒有東西會失敗 |
| 注入文字 | 每個 session 都讀到（入口、`judgment.md`、路由卡），但跳過它沒有東西會失敗 |
| 按需文字 | 只寫在 skill 或 docs 內文，要載入才讀得到 |

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
| `global/claude/route-card.md`「寫入」 | 注入文字 | — | |
| `global/claude/route-card.md`「揭露與授權」：派工揭露與授權段 | 注入文字 | — | |
| `global/claude/route-card.md`「揭露與授權」：驗收後修正分流段 | verifier 合約 | `global/claude/agents/verifier.md` 的 `controller 不得自行降級` | verifier 第一行寫分流；code-review finding 沒有分流行，由 controller 自判，不受合約約束 |

## 入口邊界（`global/claude/CLAUDE.md`「邊界」）

| 規則 | 由什麼強制 | 強制點 | 備註 |
|---|---|---|---|
| `global/claude/CLAUDE.md`「邊界」1：專案 `CLAUDE.md` 優先 | 注入文字 | — | |
| `global/claude/CLAUDE.md`「邊界」2：無證據不宣稱完成 | 注入文字 | — | |
| `global/claude/CLAUDE.md`「邊界」3：對外或不可逆動作需當次授權 | 注入文字 | — | `~/.claude/settings.json` 的 permissions 與 auto mode 分類器擋一部分，那份設定不在本 repo；CI 設定的編輯由 `block-ci-edit.sh` 擋 |
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
| worktree-session §3「直接清」的條件 | 腳本 | `scripts/worktree-clean-check.py` 的 `check_delivery` `check_tree` | fail-closed；盤點 session 清 worktree 前跑 |
| writing-principles 可機械判定的原則 | 腳本 | `global/shared/skills/writing-principles/scripts/check_docs.py` 的 `check_header` `check_links` `check_heading_refs` | 寫文件與 verifier 驗文件時跑 |
| agent-rules：規則索引單一來源、reviewer 版本 ID 與 severity 對得上 | 腳本 | `global/shared/skills/agent-rules/scripts/rules_index.py` 的 `check_rules` | 用在別的專案 repo，不管本系統 |
| 本表涵蓋每條 judgment 與每支 hook，機械強制點存在 | 測試 | `tests/test_rule_enforcement.py` 的 `test_every_judgment_entry_has_a_row` `test_every_hook_has_a_row` `test_mechanical_rows_point_at_existing_symbols` | |
