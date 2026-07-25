# 教訓封存（已升級成正式判準的歷史條目）

> 這些教訓的內容已經被正式判準或 agent 定義承接，故從常駐的 `rules/50-lessons.md` 移出，避免同一件事在每個 session 的 context 裡佔兩份位置。**原文保留不改寫**，作為判準的來歷證據。
> 本檔不在 `~/.claude/rules/` 底下，不會自動載入；要查某條判準為什麼存在時再讀。
> 封存日：2026-07-25。
>
> 注意：條目內的路徑是**寫入當時**的位置。之後發生過的搬移：
> - `rules/30-delegation-templates.md` → 已刪除，內容併入 `rules/10-dispatch.md` §2 與各 `agents/*.md` 角色合約（2026-07-25）
> - `rules/40-maintenance.md` → `skills/maintain-guideline/SKILL.md`（2026-07-25）
> - `codex/rules/10-dispatch-codex.md`、`codex/rules/30-delegation-templates-codex.md` 原本在 `rules/`（2026-07-09 移出）

- [2026-07-06][global] 盤點發現持久記憶目錄全空，過去所有 session 學到的東西都蒸發了 → 每 session 結束前自查該寫的記憶，這比當日任何單一任務都值錢 → 已套用到：40-maintenance.md §4
- [2026-07-06][global] Agent 工具呼叫無法指定 effort；effort 只能設在 agent 定義的 frontmatter → 需要特定 effort 的角色先建 `~/.claude/agents/` 定義 → 已套用到：00-environment.md、agents/verifier.md
- [2026-07-06][document] 驗收 agent 查 `.remember/` 時跑去 `~/.claude` 下找，實際在專案根目錄，差點誤判環境異常 → 給 subagent 的路徑一律寫絕對路徑，文件裡的路徑要寫到能直接 `ls` 的精確度 → 已套用到：30-delegation-templates.md 通用規則
- [2026-07-06][document] 第一版守則把「教訓記錄」分散在各檔檔尾，與交接欄用途重疊、弱模型不知道寫哪邊 → 教訓集中單一檔案（本檔），升級成正式判準才進 rules → 已套用到：40-maintenance.md §3
- [2026-07-06][global] 使用者背景第一版只憑單一 repo 的文件推斷，寫得過窄（把 side project 當工作重心）→ 背景事實用 `gh` CLI 等來源現查，文件裡的列舉標明「不要依賴，現查為準」→ 已套用到：00-environment.md
- [2026-07-06][global] 每份 rules 檔頭都放查證日期，重複且像 changelog 浪費 context → 查證日全系統只記在 00-environment.md 一處，其他檔用指向 → 已套用到：00-environment.md、10-dispatch.md
- [2026-07-06][global] 開場看 `.remember/` 只有 logs 就判定 remember plugin 沒在運作，實際上記憶檔是 session 進行中才寫入、其他專案都有完整檔組 → 判定「某機制壞了/沒在用」前，多看幾個專案與時間點，單一時點快照會騙人 → 已套用到：00-environment.md §記憶機制
- [2026-07-07][agents-guideline] 派 subagent 做分析，subagent 繼承全域 CLAUDE.md 後把「指揮官不下場」套在自己身上、再往下轉包，形成 5 層以上遞迴鏈，每層 ~55k tokens 空燒且回報「已派工」即結束（假完成的新型態）→ 派工 prompt 開頭明寫「你是被派來的執行者，親自完成，禁止呼叫 Agent 工具」；收到「我已再派背景工作」的回報一律視為未完成，立即糾正 → 已套用到：rules/30-delegation-templates.md、codex/rules/30-delegation-templates-codex.md、README.md 的 max_depth = 1 設定
- [2026-07-07][macroeconomics-report] 背景 subagent（Agent tool、run_in_background）在筆電休眠時被中斷（Connection closed mid-response、status failed），最後訊息停在「Both clean post-commit. Now write report」→ 教訓：background agent 遇機器休眠會死，但**若已 commit，work 原子性保留在 git**；agent 死掉的 partial 自我回報不可信，controller 一律用 `git log`/`git show`/獨立跑測試核實際落地，從最後 commit 續接而非重跑（本例 Task 5 已 commit、獨立驗證全綠後照常進 review→PR）→ 已套用到：rules/10-dispatch.md、codex/rules/10-dispatch-codex.md 的 blocking 任務規則
- [2026-07-08][web-pulse-workspace] spawn_task 背景 session 與主 session 在**同一個 git 工作目錄**動工（非隔離 worktree）：背景任務把主 session 未提交的變更 stash 走、換了分支，主 session 的 `git add -A` 把對方做到一半的檔案 commit＋push 上去 → 同 repo 有其他 session 在跑時，commit 前先 `git status`＋`git stash list` 核對內容物是不是自己的；要並行就自己開 `git worktree`，誤推立即 `push --delete` 撤下 → 已套用到：rules/10-dispatch.md、codex/rules/10-dispatch-codex.md、rules/40-maintenance.md 的 single-writer/worktree 規則
- [2026-07-09][global] /doctor 查出 `~/.claude/rules` 是**目錄 symlink → agents-guideline/rules**，Claude Code 會把整個資料夾**每 session 無條件全文載入**（官方 memory 功能：無 `paths` frontmatter 的 rule＝launch 時載入，與 CLAUDE.md 同級）；router 寫的「rules/ 按需載入」對 Claude 其實無效、9 檔約 ~10.3k tokens 常駐。純 Codex 檔（`10/30-*-codex.md`）先試加 `paths` frontmatter（可行，但依賴未確認的 user 層級 paths 支援），最後改**結構性分離**：`git mv` 到 `agents-guideline/codex/rules/`（Claude 的 symlink 看不到→保證不載入；Codex 靠 AGENTS.md 絕對路徑按需讀、不受影響），引用同步改 `AGENTS.md`／`README.md` → 教訓：要讓某檔在 Claude 不自動載入，**把它移出被 symlink 的 `rules/` 目錄**比加 frontmatter 穩；日後 Codex-only 或非 Claude 的守則一律放 `codex/rules/`、不放 `rules/`。router「按需載入」措辭對 rules 檔其實不成立，是否修正留給使用者 → 已套用到：AGENTS.md、README.md、檔案位置 codex/rules/
- [2026-07-18][global] insights 報告盤點 128 sessions：最長的幾次除錯繞路全是環境問題（stale mock-server 佔 port 8787、cwd 站錯、zsh quoting 弄壞輸出）被當成程式 bug 追 → 除錯前先驗環境（pwd、port 佔用者、git 狀態 read-back）再提程式假設 → 已套用到：20-judgment.md §6
- [2026-07-18][web-pulse-workspace] i18n 字串抽取宣稱完成後，main.tsx 的殘留字串靠後續全 repo 掃描才發現 → 重構／抽取類任務完成前必跑全 repo `rg` 驗無殘留並附輸出 → 已套用到：20-judgment.md §2 補充判準
- [2026-07-18][global] 一次性的「merge on green」指示被解讀為常設政策，導致 PR 被提前 merge → 對外／不可逆動作的授權一律逐次、逐對象，不得推廣為常設規則 → 已套用到：20-judgment.md §3 註
- [2026-07-18][global] zsh 展開 `===`、gh comment 的 backtick 被 shell 吃掉，指令重跑且輸出誤導判斷 → 多行或含特殊字元內容一律用 quoted heredoc（`<<'EOF'`）；git 操作後用新指令 read-back，不信 scrollback → 已套用到：20-judgment.md §6（heredoc 與 read-back 併入該節）
