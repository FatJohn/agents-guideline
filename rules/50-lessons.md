# 50 — 教訓日誌（只留未升級的活躍教訓）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與格式見 `maintain-guideline` skill §3；瘦身與封存規則見同 skill §5。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接，所以需要常駐提醒。
> 一旦升級成正式判準（改到 10／20 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事在 context 裡佔兩份位置。

- [2026-07-21][web-pulse-workspace] 只憑 Playwright a11y snapshot 判「新版 UI 與舊版一致」，漏掉純 CSS 寬度的進度條，上線才被抓到 → a11y snapshot **不含只有視覺、無文字的元素**（進度條、色塊、icon-only）；判視覺對齊要用截圖或 `browser_evaluate` 抓 computed style → 已套用到：尚未（再踩就提案入 `rubrics/code-change.md`）
- [2026-07-21][global] 把「加 import」與「加使用處」拆成兩次 Edit，per-file lint hook 在中間態報 `unused-imports` 假 error → 有 PostToolUse per-file lint hook 時，import 與其使用處併在同一次 Edit（或先改使用處再加 import）；真假存疑一律補跑 eslint 確認 → 已套用到：尚未
- [2026-07-25][flutter-slimgo] 見兩份同名 SKILL.md `diff -q` 顯示 differ 就當成漂移去問使用者，拿到授權後才發現一份是刻意為 Codex 寫的精簡版 → 拿「兩個檔案不一致」問人**之前**先看清不一致的**性質**（漂移事故 vs 刻意分版），否則拿到的是基於錯誤前提的授權；動手前再複查一次前提 → 已套用到：尚未（再踩就提案入 20-judgment §3）
- [2026-08-06][global] repo 新增 `debug-environment-first` skill，`20-judgment.md` §6 已指向它，但本機沒重跑安裝、skill 清單裡根本沒這個名字 → 在 repo 加 skill／agent 不等於任何機器已安裝；加完當場重跑 README 安裝段（可重跑，已存在會略過）並 read-back 連結，否則規則會指向一個叫不出來的名字 → 已套用到：尚未

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
