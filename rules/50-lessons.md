# 50 — 教訓日誌（只留未升級的活躍教訓）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與格式見 `maintain-guideline` skill §3；瘦身與封存規則見同 skill §5。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接，所以需要常駐提醒。
> 一旦升級成正式判準（改到 10／20 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事在 context 裡佔兩份位置。

- [2026-07-06][macroeconomics-report] 文件重組時改了 markdown 標題又批次搬連結，verifier 抓到 3 條死鏈 → 改標題（不只搬檔）會斷下游 anchor，改完要 `rg "檔名#"` 全 repo 驗存活；手算 GitHub anchor 易錯，歷史文件用「檔案層連結＋章節名文字」更穩 → 已套用到：尚未（再踩就提案入 maintain-guideline skill §6）
- [2026-07-08][macroeconomics-report] 用 `--delete-branch` 合併 base PR，GitHub 把 stacked 在其上的 PR 自動**關閉**、且無法 reopen → 有 PR stack 在其上的 branch，merge 時**勿用 --delete-branch**；正解是先 `gh pr edit <stacked#> --base main` retarget 再 merge。救援：stacked branch 的 commits 完整，直接用它開新 PR 到 main → 已套用到：尚未（再踩就提案入 20-judgment 或 dispatch 檔）
- [2026-07-08][web-pulse-workspace] 背景 Explore agent 無聲消失（TaskList 查無、無完成通知） → 需要結果才能往下走的掃描任務改 `run_in_background: false` 同步等 → 已套用到：尚未
- [2026-07-21][web-pulse-workspace] 只憑 Playwright a11y snapshot 判「新版 UI 與舊版一致」，漏掉純 CSS 寬度的進度條，上線才被抓到 → a11y snapshot **不含只有視覺、無文字的元素**（進度條、色塊、icon-only）；判視覺對齊要用截圖或 `browser_evaluate` 抓 computed style → 已套用到：尚未（再踩就提案入 `rubrics/code-change.md`）
- [2026-07-21][global] 把「加 import」與「加使用處」拆成兩次 Edit，per-file lint hook 在中間態報 `unused-imports` 假 error → 有 PostToolUse per-file lint hook 時，import 與其使用處併在同一次 Edit（或先改使用處再加 import）；真假存疑一律補跑 eslint 確認 → 已套用到：尚未
- [2026-07-23][web-pulse-survey-sdk] tsup→tsdown 遷移漏改 `.github/actions` 裡的舊指令，PR CI 不跑部署路徑故全綠，發版時 release CI 才炸 → build-tool／依賴遷移後 `rg` 全 repo（**含 `.github/workflows` 與 `.github/actions`**）搜舊工具名；release／deploy-only 路徑 PR CI 測不到、要另外查。**救援**：重跑舊 run 仍會沿用含 bug 的 action，必須先修 action、再發一個 patch 版本帶新 action 重跑 → 已套用到：尚未（再踩提案入 20-judgment §2 補充判準）
- [2026-07-25][agents-guideline] 把重複規則改成「見對應平台 dispatch 文件 §N」，但兩份 dispatch 的章節編號不同，Codex 照 §N 會翻到別節 → 跨平台共用的指向一律**逐平台各寫一組編號並附章節名**（「§5『升降級路徑』」）；章節名是編號漂移時的救命錨點 → 已套用到：尚未（再踩就提案入 maintain-guideline skill §6）
- [2026-07-25][flutter-slimgo] 見兩份同名 SKILL.md `diff -q` 顯示 differ 就當成漂移去問使用者，拿到授權後才發現一份是刻意為 Codex 寫的精簡版 → 拿「兩個檔案不一致」問人**之前**先看清不一致的**性質**（漂移事故 vs 刻意分版），否則拿到的是基於錯誤前提的授權；動手前再複查一次前提 → 已套用到：尚未（再踩就提案入 20-judgment §3）

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
