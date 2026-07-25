# 50 — 教訓日誌（只留未升級的活躍教訓）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與格式見 `maintain-guideline` skill §3；瘦身與封存規則見同 skill §5。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接，所以需要常駐提醒。
> 一旦升級成正式判準（改到 10／20 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事在 context 裡佔兩份位置。

- [2026-07-06][macroeconomics-report] 文件重組 sed 批次改連結、把「早已因改標題而死掉」的 anchor 原樣搬過去、verifier 抓到 3 條死鏈 → 改 markdown 標題（不只搬檔）也會斷下游 anchor、改完要 rg "檔名#" 全 repo 驗存活；手算 GitHub anchor 易錯、歷史文件用檔案層連結+章節名文字更穩 → 已套用到：尚未（再踩就提案入 maintain-guideline skill §6）
- [2026-07-08][macroeconomics-report] 逐源獨立 PR、第二刀 stacked 在第一刀 branch 上（共用檔避 merge 衝突）；merge 第一刀 PR 時用 `gh pr merge --delete-branch` 刪掉 base branch → GitHub 自動**關閉**（非 retarget）stacked 在其上的第二刀 PR、且 closed PR 無法 reopen/改 base → 教訓：merge「有其他 PR stack 在其上」的 branch 時**勿用 --delete-branch**；正解＝先 `gh pr edit <stacked#> --base main` retarget 再 merge base PR，或 merge 時不刪 branch。救援：stacked branch 本身未受影響（commits 完整）、直接用它開新 PR 到 main 即可（本例 #130 被誤關→開 #131 救回、兩刀順利進 main）→ 已套用到：尚未（再踩就提案入 20-judgment 或 dispatch 檔）
- [2026-07-08][global] figma plugin 已啟用但 session 內搜不到 `figma-dev-mode-mcp-server` 工具（MCP 未在 session 啟動時註冊）→ Figma 桌面 App 的 Dev Mode MCP server 若在 127.0.0.1:3845 有跑，可用 curl 手動走 JSON-RPC（initialize→tools/call get_design_context/get_screenshot/get_metadata）直接取設計稿，不必重開 session → 已套用到：尚未
- [2026-07-08][web-pulse-workspace] 背景 Explore agent 無聲消失（TaskList 查無、無完成通知）→ 需要結果才能往下走的掃描任務改 run_in_background:false 同步等 → 已套用到：尚未
- [2026-07-21][web-pulse-workspace] 判「新版 UI 與舊版一致」時只看 Playwright accessibility snapshot（只含文字），漏掉純 CSS 寬度的進度條，回報「回應數呈現一致」後上線才被使用者抓到少一條 bar → a11y snapshot 不含只有視覺、無文字的元素（進度條、色塊、icon-only）；判 UI 視覺對齊要用截圖或 `browser_evaluate` 抓 DOM/computed style，不能只憑 a11y 樹 → 已套用到：尚未（再踩就提案入 `rubrics/code-change.md`）
- [2026-07-21][global] 把「加 import」與「加使用處」拆成兩次 Edit，per-file lint hook 在中間態抓到 `unused-imports` 假 error → 有 PostToolUse per-file lint hook 時，import 與其使用處併在同一次 Edit（或先改使用處再加 import）避免中間態假告警；真假存疑一律補跑 eslint 確認 → 已套用到：尚未
- [2026-07-23][web-pulse-survey-sdk] tsup→tsdown 遷移（#110）改了 package.json build script 卻漏改 `.github/actions/deploy-widget` 裡的 `pnpm exec tsup`；PR CI 不跑部署路徑故全綠，直到發 0.20.0 時 release CI 的 deploy-staging 才炸（`Command "tsup" not found`）、連帶 prod 部署與 Slack 通知被 skip；重跑舊 run 又沿用含 bug 的 action，只能修 action 後另發 patch（0.20.1）讓部署帶新 action 重跑 → build-tool／依賴遷移後，`rg` 全 repo（含 `.github/workflows` 與 `.github/actions`）搜舊工具名；release/deploy-only 路徑 PR CI 測不到、發版才會爆，要另外查 → 已套用到：尚未（再踩提案入 20-judgment §2 補充判準）
- [2026-07-25][agents-guideline] 為去重把重複規則改成「見對應平台 dispatch 文件 §N」的單一指向，但 Claude 與 Codex 兩份 dispatch 的章節編號不同（升降級 Claude §4／Codex §5，驗證 Claude §5／Codex §6），Codex session 照 §N 會翻到回報合約——fable-verifier 抓到 → 跨平台共用的指向一律**逐平台各寫一組編號並附章節名**（「§5『升降級路徑』」），不要用一個 §N 指兩份結構不同的文件；章節名是編號漂移時的救命錨點 → 已套用到：尚未（再踩就提案入 maintain-guideline skill §6）

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
