# 驗收政策歷史背景

現行規則見 `../rules/20-judgment.md` §2 及各平台 dispatch；本檔不作驗收指令，唯一例外是下方「fable 升檔訊號」清單（`../rules/10-dispatch.md` §5 指向此處）。

2026-09-06 舊 `rules/10-dispatch.md` 記錄 web-member-login 八輪驗收，前五輪 fable 的成本為
601,747 tokens，第六輪額度不足，後三輪 opus 仍抓到修正引入的迴歸。此數字沿用當時紀錄，
未在本次重新核定計量口徑，不與包含 cache read 的 session usage 加總直接比較。

2026-09-07 調整聚焦修正後的分流及 delta 範圍：每輪找到問題不代表每輪都需要完整重驗。
保留 Claude opus 與 Codex Sol/high 的高風險檔位差異；沒有修改前後對照，尚不宣稱節省比例。

## fable 升檔訊號

2026-10-03 從 `rules/10-dispatch.md` §5 搬入（原文未改寫）。規則本文留在 §5：改用 `model: fable` 前，說明訊號與證據並取得當次同意；使用者當次直接指定 fable 不必再問；無訊號仍可提議，但要明說沒有訊號及判斷理由。

訊號清單（原文）：
(a) 同一條件連續兩輪 UNSURE；(b) 與實跑或獨立結論矛盾且 controller 無法裁決；
(c) 後來實測抓到它漏掉的安全、授權或不可逆缺陷。

觸發紀錄：2026-09-29 窗口內 fable 兩次皆使用者直接指定（`worker-sonnet55-trial-2026-09.md`「死重（0 觸發）」）；2026-10-03 審查（2026-09-19 起 14 天）fable 派工 9 次，9 次之前使用者都先點名 fable，訊號 (a)(b)(c) 觸發 0 次。
