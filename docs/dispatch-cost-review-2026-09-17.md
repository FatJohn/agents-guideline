# 派工成本 audit（2026-09-17）

> 這是對 `a4b62aa` 所依據統計的更正與重算紀錄，不是遙測 framework，也不是節省或加速的證明。

## 輸入與範圍

- 原始 Claude session：`2ed816be-1381-4505-918c-c9868e3e3e84`。
- 當時的本機暫存（可能因清理消失）：
  `/private/tmp/claude-501/-Users-fatjohn-Projects-FatJohn-agents-guideline/2ed816be-1381-4505-918c-c9868e3e3e84/scratchpad/{sessions.json,vf.py,analyze4.py,analyze7.py}`。
- 原始 session／subagent transcript 與 metadata：`~/.claude/projects/**/<session>/subagents/agent-*.jsonl` 及對應 `.meta.json`；本 audit 不把這些資料複製進 repo。
- 2026-09-17 controller 重新計算原始分組；`single`／`multi` 是腳本分類，不等於真實修正輪。

## 重算結果（描述性，不作因果結論）

| 分組／項目 | 重算結果 |
|---|---|
| 原 `single` 分組 | 66 個；requests mean 58.12、median 48；tools median 51 |
| 原 `multi` 分組 | 71 個；統一權重 proxy cost 300.1749178M；對照 `single` 為 67.4412536M；multi 占兩者合計 81.7% |

這些數字只描述該批輸入與量法。29 個被歸為 `multi` 的後續文字全是 `system-reminder`，不是可確認的 `SendMessage` 修 finding；資料也混有 rate-limit 恢復，因此不能把 `single`／`multi` 解讀成兩種真實修正策略。

## 量法限制與更正

- **原分析啟發式估計**：verifier 初步輪次摘要曾記首輪 `OPEN` 64%；腳本分出的首輪／後續 proxy cost 約 78M／46M。這些是歷史更正，仍受同一類 heuristic 影響，不是真正可靠的重算，也不能作政策依據。
- `vf.py` 以 description regex 猜輪次；第三、第四輪的中文描述可被歸成 `r1`。早期摘要曾寫第二輪占 83%，作者後更正為 37%；兩者都不能作政策依據。
- agent 的 first–last 區間包含閒置時間；主對話的工具等待未與獨占 interval 取交集，不能當 critical path 的精確分帳。
- cost 是統一權重代理（input 1、cache write 1.25、cache read 0.1、output 5），不是實付價格或訂閱額度；output token 也不是交付成果。

## effort 證據

- controller read-back 顯示 repo 與已安裝的 Codex `worker.toml` 都是 `gpt-5.6-luna`／`max`。
- Claude worker 在 `1bcb5a2`（2026-09-09）由 `xhigh` 改為 `high`，同一變更也批次化工具呼叫；沒有前後隔離的 effort 對照，不能歸因於 effort。
- 2026-09-17 使用者決策：Claude `worker` default 改為 `Sonnet/xhigh`；Codex `worker` 的 `gpt-5.6-luna`／`max` 不變。這是路由設定決策，不是成本或 verifier 輪數的效益結論。
- 2026-09-24 使用者決策：Claude `worker` default 改為 Opus 5.5/medium（試用），Sonnet/xhigh 改為 `worker-sonnet` 備用；worker A/B 對照實驗移除。
- [Claude Code model configuration](https://code.claude.com/docs/en/model-config) 說明 effort 可用級別依 model 而異，不支援的級別會回落，較高級別通常增加 token spend，且設定／環境／組織 cap 會影響有效值。若要比較 `high`／`xhigh`，須固定同一 model、同類任務、verifier 與 fresh 策略，記錄 runtime 實值、總成本、時間與行為缺陷；現有資料沒有證明 effort 一定降低 verifier 輪數。

## 後續量測方法（需要時重算）

1. 以 `task/slice + artifact SHA + 驗收條件版本` 識別交付；每輪連到 finding ID。缺資料記 `unknown`，不從 description 或文字猜。
2. 將 finding 分為行為缺陷、證據缺口、非行為事實／引用問題、範圍外事項；停止端沿用 `../rules/20-judgment.md` §2，不以輪數自動重派。
3. 記錄實際 model／effort 與證據等級；input、cache write、cache read、output 分開。記錄每階段執行區間及人工／CI 等待，重疊區間先取 union；若無法消除閒置或等待，保留限制而不命名為 critical path。
4. 同類任務比較「到收斂／完成的總成本、時間、返工與逃逸缺陷」；output 數或 `OPEN` 單一指標不能支持因果。
5. fresh 策略與 60 次提醒是待評估假設；沒有序列 baseline 不稱加速。effort 對照須固定其他策略，runtime 未知的樣本不併組。

## 2026-09-18 更正（重算全部 09-07 起資料）

範圍：09-07 起 178 個 `worker`、270 個 `verifier`、44 個有 ≥3 subagent 的主對話 session；權重同上（in 1／cache write 1.25／cache read 0.1／output 5）；usage 以 requestId 去重。

- **上節「29 個 multi 全是 system-reminder」的成因**：Claude Code 從 2.1.272 起在每個 subagent 第一次 request **之前**注入一則 `SubagentHandback` system-reminder（2.1.270 已見 2 例；92 個 worker 全在首個 request 前，0 個在後），舊腳本把它算成第二個 user turn。剝掉 `<system-reminder>` 後：真的收到 `SendMessage` 的 worker 45/178，占 worker 成本 68%（不是 71/82%）；follow-up 93 則，其中 rate-limit 恢復 2 則。
- **續用 vs fresh**：這 45 個 worker 首輪 3,821 request／91M，後續輪 4,364 request／196M；每 request 成本首輪 23.9K、後續輪 44.9K。單一續用修正輪（n=87）中位 41 request／1,364K；prompt 帶 finding 的 fresh 修正 worker（n=47，regex 辨識、任務難度未受控）中位 48 request／816K。93 次 follow-up 有 48 次送出時 worker context 已 >200K；鏈長 1／2／3 以上分別 17／16／12 個 worker。
- **verifier**（輪次改由 prompt regex 判，不用 description）：09-15 前首輪 OPEN 69%（n=75）、delta 62%（n=101）；09-15 後首輪 55%（n=44）、delta 49%（n=35）。delta 占 verifier 145/270、成本 80/145M。09-15 後 17 個 delta OPEN 的 FAIL 以文件可證偽宣稱與「修一半」居多。
- **主對話**：8,397 request／383M，其中 cache read 74%、cache write 13%、output 13%；每 session request 中位 189、context 中位 320K；Bash 5,791 次，約 1,000 次首字是 `sed`／`cat`／`grep`／`rg`／`ls`（其中 `cat` 含 72 次 `cat >` 寫入；另有 1,129 次 `cd … &&` 開頭的複合指令未分類）、約 480 次是 inline `python3`／`node` 腳本。
- **`<usage>` 欄位**：`subagent_tokens` ≈ 交回當下 context 大小（逐筆核過），是 controller 現成的 fresh／continue 訊號；上節未提。
- **effort**：single-turn worker `high` n=99 中位 44 request／628K，`xhigh` n=34 中位 52 request／851K；時間窗與任務混合不同，仍不作政策依據。

限制不變：fresh 修正 worker 的辨識靠 prompt regex、任務難度未受控，倍率是方向證據；主對話「每次工具呼叫重讀 context」是機制事實，74% 是該批 session 的實測份額。
