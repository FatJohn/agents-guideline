# 驗收政策歷史背景

現行規則見 `<REPO>/global/shared/rules/judgment.md` 第 1 條「完成的三個條件」、第 7 條「驗收的停止端」及各平台 dispatch；本檔不作驗收指令，唯一例外是下方「fable 升檔訊號」清單（`<REPO>/global/shared/skills/dispatch/SKILL.md` §1「驗證不自驗」指向此處）。

2026-09-06 舊驗收規則記錄 project-d 八輪驗收，前五輪 fable 的成本為
601,747 tokens，第六輪額度不足，後三輪 opus 仍抓到修正引入的迴歸。此數字沿用當時紀錄，
未在本次重新核定計量口徑，不與包含 cache read 的 session usage 加總直接比較。

2026-09-07 調整聚焦修正後的分流及 delta 範圍：每輪找到問題不代表每輪都需要完整重驗。
保留 Claude opus 與 Codex Sol/high 的高風險檔位差異；沒有修改前後對照，尚不宣稱節省比例。

## fable 升檔訊號

訊號清單由舊驗收規則搬入（原文未改寫）。規則本文在 `<REPO>/global/shared/skills/dispatch/SKILL.md` §6「驗證不自驗」：改用 `model: fable` 前，說明訊號與證據並取得當次同意；使用者當次直接指定 fable 不必再問；無訊號仍可提議，但要明說沒有訊號及判斷理由。

訊號清單（原文）：
(a) 同一條件連續兩輪 UNSURE；(b) 與實跑或獨立結論矛盾且 controller 無法裁決；
(c) 後來實測抓到它漏掉的安全、授權或不可逆缺陷。

觸發紀錄：2026-09-29 窗口內 fable 兩次皆使用者直接指定（`worker-sonnet55-trial-2026-09.md`「死重（0 觸發）」）；2026-10-03 審查（2026-09-19 起 14 天）fable 派工 9 次，9 次之前使用者都先點名 fable，訊號 (a)(b)(c) 觸發 0 次。

## verifier 找碴範圍的由來

從 `global/claude/agents/verifier.md` 的「找碴範圍」搬入，原句未改寫。現行規則是 verifier 合約的「找碴範圍」與 `global/shared/rules/judgment.md` 7「驗收的停止端」。

訂這條範圍的理由（原文，僅更新指向）：

> 找碴 prompt **保證有輸出**。不限定範圍，每一輪都必然找得到措辭問題，而散文修正不會讓任何閘門變紅，所以下一輪還是找得到——那個迴圈沒有終點（實測：一次 40 輪驗收的 93 則發現有 87% 落在散文，`~/.claude/rules/judgment.md` 第 7 條「驗收的停止端」即為此而設）。

同批從 worker 與 verifier 合約刪掉的理由句（原文），當時寫在指令批次化規則內：

> 每次往返都是一輪推理，是驗收耗時的主因。
>
> 每次工具往返都是一輪模型推理，串行小步是 subagent 比主對話慢的主因之一。
>
> subagent 的 prompt cache 只保留 5 分鐘（主對話是 1 小時），一次等 10 分鐘，醒來就得把整段 context 重寫（量測見 `<REPO>/docs/harness-facts.md`「subagent 的 prompt cache 是 5 分鐘」）。

合約現在只留可執行的部分（批次化、`run_in_background`、輪詢迴圈上限、`timeout` 不超過 240000），cache 的數字與量測留在 `harness-facts.md`。
