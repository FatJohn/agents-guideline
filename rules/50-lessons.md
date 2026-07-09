# 50 — 教訓日誌（append-only）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與瘦身規則見 `40-maintenance.md`。

- [2026-07-06][global] 盤點發現持久記憶目錄全空，過去所有 session 學到的東西都蒸發了 → 每 session 結束前自查該寫的記憶，這比當日任何單一任務都值錢 → 已套用到：40-maintenance.md §4
- [2026-07-06][global] Agent 工具呼叫無法指定 effort；effort 只能設在 agent 定義的 frontmatter → 需要特定 effort 的角色先建 `~/.claude/agents/` 定義 → 已套用到：00-environment.md、agents/verifier.md
- [2026-07-06][document] 驗收 agent 查 `.remember/` 時跑去 `~/.claude` 下找，實際在專案根目錄，差點誤判環境異常 → 給 subagent 的路徑一律寫絕對路徑，文件裡的路徑要寫到能直接 `ls` 的精確度 → 已套用到：30-delegation-templates.md 通用規則
- [2026-07-06][document] 第一版守則把「教訓記錄」分散在各檔檔尾，與交接欄用途重疊、弱模型不知道寫哪邊 → 教訓集中單一檔案（本檔），升級成正式判準才進 rules → 已套用到：40-maintenance.md §3
- [2026-07-06][global] 使用者背景第一版只憑單一 repo 的文件推斷，寫得過窄（把 side project 當工作重心）→ 背景事實用 `gh` CLI 等來源現查，文件裡的列舉標明「不要依賴，現查為準」→ 已套用到：00-environment.md
- [2026-07-06][global] 每份 rules 檔頭都放查證日期，重複且像 changelog 浪費 context → 查證日全系統只記在 00-environment.md 一處，其他檔用指向 → 已套用到：00-environment.md、10-dispatch.md
- [2026-07-06][global] 開場看 `.remember/` 只有 logs 就判定 remember plugin 沒在運作，實際上記憶檔是 session 進行中才寫入、其他專案都有完整檔組 → 判定「某機制壞了/沒在用」前，多看幾個專案與時間點，單一時點快照會騙人 → 已套用到：00-environment.md §記憶機制
- [2026-07-06][macroeconomics-report] 文件重組 sed 批次改連結、把「早已因改標題而死掉」的 anchor 原樣搬過去、verifier 抓到 3 條死鏈 → 改 markdown 標題（不只搬檔）也會斷下游 anchor、改完要 rg "檔名#" 全 repo 驗存活；手算 GitHub anchor 易錯、歷史文件用檔案層連結+章節名文字更穩 → 已套用到：尚未（再踩就提案入 40-maintenance §6）
- [2026-07-07][agents-guideline] 派 subagent 做分析，subagent 繼承全域 CLAUDE.md 後把「指揮官不下場」套在自己身上、再往下轉包，形成 5 層以上遞迴鏈，每層 ~55k tokens 空燒且回報「已派工」即結束（假完成的新型態）→ 派工 prompt 開頭明寫「你是被派來的執行者，親自完成，禁止呼叫 Agent 工具」；收到「我已再派背景工作」的回報一律視為未完成，立即糾正 → 已套用到：30-delegation-templates.md 通用規則
- [2026-07-07][macroeconomics-report] 背景 subagent（Agent tool、run_in_background）在筆電休眠時被中斷（Connection closed mid-response、status failed），最後訊息停在「Both clean post-commit. Now write report」→ 教訓：background agent 遇機器休眠會死，但**若已 commit，work 原子性保留在 git**；agent 死掉的 partial 自我回報不可信，controller 一律用 `git log`/`git show`/獨立跑測試核實際落地，從最後 commit 續接而非重跑（本例 Task 5 已 commit、獨立驗證全綠後照常進 review→PR）→ 已套用到：尚未（可考慮：長任務優先前景跑，或 dispatch 後在 ledger 記「commit 才算數、agent 回報僅參考」）
- [2026-07-08][macroeconomics-report] 逐源獨立 PR、第二刀 stacked 在第一刀 branch 上（共用檔避 merge 衝突）；merge 第一刀 PR 時用 `gh pr merge --delete-branch` 刪掉 base branch → GitHub 自動**關閉**（非 retarget）stacked 在其上的第二刀 PR、且 closed PR 無法 reopen/改 base → 教訓：merge「有其他 PR stack 在其上」的 branch 時**勿用 --delete-branch**；正解＝先 `gh pr edit <stacked#> --base main` retarget 再 merge base PR，或 merge 時不刪 branch。救援：stacked branch 本身未受影響（commits 完整）、直接用它開新 PR 到 main 即可（本例 #130 被誤關→開 #131 救回、兩刀順利進 main）→ 已套用到：尚未（再踩就提案入 20-judgment 或 dispatch 檔）
- [2026-07-08][global] figma plugin 已啟用但 session 內搜不到 `figma-dev-mode-mcp-server` 工具（MCP 未在 session 啟動時註冊）→ Figma 桌面 App 的 Dev Mode MCP server 若在 127.0.0.1:3845 有跑，可用 curl 手動走 JSON-RPC（initialize→tools/call get_design_context/get_screenshot/get_metadata）直接取設計稿，不必重開 session → 已套用到：尚未
- [2026-07-08][web-pulse-workspace] 背景 Explore agent 無聲消失（TaskList 查無、無完成通知）→ 需要結果才能往下走的掃描任務改 run_in_background:false 同步等 → 已套用到：尚未
- [2026-07-08][web-pulse-workspace] spawn_task 背景 session 與主 session 在**同一個 git 工作目錄**動工（非隔離 worktree）：背景任務把主 session 未提交的變更 stash 走、換了分支，主 session 的 `git add -A` 把對方做到一半的檔案 commit＋push 上去 → 同 repo 有其他 session 在跑時，commit 前先 `git status`＋`git stash list` 核對內容物是不是自己的；要並行就自己開 `git worktree`，誤推立即 `push --delete` 撤下 → 已套用到：尚未
- [2026-07-09][global] /doctor 查出 `~/.claude/rules` 是**目錄 symlink → agents-guideline/rules**，Claude Code 會把整個資料夾**每 session 無條件全文載入**（官方 memory 功能：無 `paths` frontmatter 的 rule＝launch 時載入，與 CLAUDE.md 同級）；router 寫的「rules/ 按需載入」對 Claude 其實無效、9 檔約 ~10.3k tokens 常駐。純 Codex 檔（`10/30-*-codex.md`）先試加 `paths` frontmatter（可行，但依賴未確認的 user 層級 paths 支援），最後改**結構性分離**：`git mv` 到 `agents-guideline/codex/rules/`（Claude 的 symlink 看不到→保證不載入；Codex 靠 AGENTS.md 絕對路徑按需讀、不受影響），引用同步改 `AGENTS.md`／`README.md` → 教訓：要讓某檔在 Claude 不自動載入，**把它移出被 symlink 的 `rules/` 目錄**比加 frontmatter 穩；日後 Codex-only 或非 Claude 的守則一律放 `codex/rules/`、不放 `rules/`。router「按需載入」措辭對 rules 檔其實不成立，是否修正留給使用者 → 已套用到：AGENTS.md、README.md、檔案位置 codex/rules/
## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
