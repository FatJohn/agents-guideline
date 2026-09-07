# 驗收政策歷史背景

現行規則見 `../rules/20-judgment.md` §2 及各平台 dispatch；本檔不作驗收指令。

2026-09-06 舊 `rules/10-dispatch.md` 記錄 web-member-login 八輪驗收，前五輪 fable 的成本為
601,747 tokens，第六輪額度不足，後三輪 opus 仍抓到修正引入的迴歸。此數字沿用當時紀錄，
未在本次重新核定計量口徑，不與包含 cache read 的 session usage 加總直接比較。

2026-09-07 調整聚焦修正後的分流及 delta 範圍：每輪找到問題不代表每輪都需要完整重驗。
保留 Claude opus 與 Codex Sol/high 的高風險檔位差異；沒有修改前後對照，尚不宣稱節省比例。
