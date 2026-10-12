# 量 jsonl 的已知陷阱

每條格式：**現象 → 影響 → 本工具怎麼處理**。標「人工」的表示工具不處理，解讀報表時要自己留意。Claude Code 的 jsonl 沒有官方穩定性承諾，下列觀察綁定寫這份文件時的版本；新版本改格式時，先對照 `schema.md` 與 `scripts/extract.py` 的 record 解析。

## A. 用量數字

1. **一個 request 會寫成多行、同 message id 可能對到多個 requestId**
   現象：一則 assistant message 的每個 content block（text、每個 tool_use）各寫一行，每行都重複同一份 `usage`；舊 session 還看過同一個 `message.id` 帶不同 `requestId`（重送）。在寫這份文件時的一週樣本裡，約 77% 的 request 有兩行以上，同 id 多 requestId 的為 0 筆。
   影響：直接加總 usage 會把用量重複計入約一倍。另外各行的 usage 不一定相同：實測抽到的差異都出在含 advisor 呼叫的 request（有多個 executor iteration），較早的行只帶前面的 iteration，最後一行（output 最大）才是合計；取第一行會低估這類 request。
   處理：去重鍵是 `(message.id, requestId)`，全域（跨檔）唯一。同鍵多筆時 `output_tokens` 取最大值，其餘 usage 欄位取 output 最大那筆。重送（同 id 不同 requestId）會被當成兩個 request，因為它們確實各自打過 API。

2. **`output_tokens` 只記到串流開頭**
   現象：jsonl 記的是串流開始時的 usage，部分模型的 output 遠低於實際（作者機器的校準：Opus 5.5 約少記三分之二，Sonnet 5.5 約少一個數量級；Sonnet 的可見文字字元中位數有時為 0，連用字元數反推都補不到）。這是本機觀察，不是官方數字。
   影響：只看 `out_raw` 會低估成本，output 單價高的 model 尤其明顯。
   處理：預設只報原始值（`cost_raw`）。`--output-correction` 依 `pricing.json` 的 `output_correction` 規則另算 `out_est`／`cost_est`，是**啟發式**，兩個數字永遠並列報告，不覆蓋原始值。規則要重新校準時改 pricing.json，不改程式。

3. **`cache_creation` 的 1h／5m 細分可能缺**
   現象：有的記錄只有 `cache_creation_input_tokens` 總額，沒有 `cache_creation` 子物件。
   影響：1h 與 5m 的寫入單價差（2× vs 1.25× input）會讓成本不確定。
   處理：缺細分時整筆當 1h（成本上界），該 req 標 `cw_ttl_known: false`，extract 摘要會印出這類 req 的數量。
   出處：這個 fallback 沿用本 skill 之前多輪手寫量測腳本的計價做法（cw1h 缺值時整筆 cw 當 1h，取上界）。
   現況：本機一份樣本中（2026-10-05 起的資料，47,239 筆 request），`cw_ttl_known=false` 為 0 筆，細分小於總額的有 137 筆（0.29%）；這是單一機器、單一期間的觀察，不是通則。

4. **細分合計可能小於總額**
   現象：有 `cache_creation` 細分，但 `ephemeral_1h + ephemeral_5m` 小於 `cache_creation_input_tokens`（在一週樣本裡約 0.3% 的 request，差額原因不明）。
   影響：照細分計價時，差額那部分沒有被計價，成本略低估。
   處理：照細分計價（`cw` 仍存 API 給的總額），extract 摘要印出這類 req 的數量。要保守估計時可自行把差額當 1h。

5. **`<synthetic>` 佔位記錄**
   現象：少數 assistant 記錄的 model 是 `<synthetic>`，usage 全 0、沒有 requestId（harness 產生的訊息，不是 API request）。
   影響：算進 req 會多出沒有價格的 model、拉高 `unpriced`。
   處理：model 以 `<` 開頭的記錄不算 request。

6. **advisor 用量不在 req 的 token 欄位裡，而且是下限**
   現象：`advisor_tool` attachment 與每筆 assistant 的 `advisorModel` 欄位都含模型字串，但它們不是 request；advisor（如 Fable）的用量只出現在 `usage.iterations[]` 裡 `type: "advisor_message"` 的項目，且 subagent 檔裡多數沒有記。
   影響：若把含模型字串的行當 request 數，會算出不存在的 request；advisor 的花費不會出現在 `reqs`，總額偏低（在一週樣本裡，有 `advisor_message` 的記錄其頂層 usage 逐筆等於 `type:"message"` 各 iteration 的加總，確認不含 advisor）。
   處理：model 只看 `type:"assistant"` 的 `message.model`。本工具**不展開** `iterations`，所以 `reqs` 的成本不含 advisor；需要時另外讀 `usage.iterations[]`（人工），並把結果視為下限。

7. **1M context 倍增**
   現象：同一個 session 內 context 突然翻倍（改用 1M context 視窗的情形）。這條來自先前的人工分析註記，本工具沒有獨立驗證。
   影響：`context` 類統計（分桶、中位數）會在轉換點出現階梯，成為雜訊來源。
   處理：人工；看到階梯時回頭檢查該 session 的 model 與 request 序列。

8. **字元換算 token 的係數是估的**
   現象：舊分析用過「字元 ÷ 3.5」或「0.9～1 token／字元」等係數，不同語言差很多。
   影響：任何由字元數反推 token 的數字（`tool_result_chars`、`final_chars`、`prompt_chars` 換算 context 負擔）只能當上界或量級。
   處理：本工具只存字元數，不內建換算；報告引用換算結果時要註明係數。

## B. 角色與事件歸屬

9. **subagent 的 tool_use 不在主 jsonl**
   現象：主對話檔裡的記錄 `isSidechain` 是 false（或沒有這個欄位）；subagent 的對話在 `<sid>/subagents/agent-*.jsonl`（記錄的 `isSidechain` 為 true）。
   影響：只掃主對話檔會漏掉 subagent 的 request 與工具呼叫。
   處理：同時掃兩種檔；req 的 `agent` 欄位指出歸屬，`role` 是主對話 `main` 或 `agents[agent].type`。

10. **`.meta.json` 的 `agentType` 會被改寫**
    現象：agent 定義被刪除之後，仍在跑或之後續用的 subagent，meta 會被記成 `general-purpose`。
    影響：用 meta 分角色會把已刪除角色的成本算進 `general-purpose`。
    處理：角色以主對話 `Agent` tool_use 的 `subagent_type` 覆寫（經 meta 的 `toolUseId` 或 `agent_id` 連結），保留 `meta_type`，不同時 `retyped: true`。

11. **不是人類輸入的 user 記錄**
    現象：`type:"user"` 的記錄裡，有 `<agent-message>`／「Another Claude session sent a message」（其他 session 的訊息，以及 harness 轉交的 `[Subagent hand-back]`）、`<command-*>`／`<local-command*>`、續接摘要（"This session is being continued…"）、`<task-notification>`、`isMeta` 記錄，另有只剩 `<system-reminder>` 的文字。
    影響：把它們算成人類輸入會高估人工介入次數。
    處理：`humans[].kind` 分類（分類以文字前綴判斷，屬啟發式），只有 `human` 與 `ask_answer` 是真人。剝除 `<system-reminder>` 後為空的記錄直接不輸出。

12. **`AskUserQuestion`／`ExitPlanMode` 的回答是真人回覆**
    現象：這兩個工具的 tool_result 其實是使用者的回答，不是工具輸出。另外，背景 Bash 執行期間使用者插話，會在時間軸上被看成「等待結果」。
    影響：漏算這類回覆會低估人工介入；做 lead time 類分析時，插話會被誤判成等待。
    處理：extract 把前者記為 `ask_answer`。後者本工具不處理（人工）。

13. **`task-notification` 的重複與數字**
    現象：同一則通知會同時出現在 `queue-operation`、`attachment`（`queued_command`）與 `user` 記錄；有些通知沒有 `<tool-use-id>`，只有 `<task-id>`（＝agent id）；被續用的 agent 會收到多筆通知，且 `<usage>` 的數字不一定是累計值（有些通知的 `tool_uses` 小於 agent 檔實際的工具數）；`killed` 之類的通知沒有 `<usage>`。
    影響：不去重會多算；用通知的數字當 agent 總用量可能偏低。
    處理：依內容去重、取最早時間；先用 tool-use-id、再用 task-id 對呼叫；`agent_call.notification` 取最後一筆（無 `<usage>` 時三個數字為 null），並附 `notification_count`。agent 的總用量以 `agents[].requests`、`tools` 與 req 的 token 為準，通知數字只當參考。

## C. 解析與覆蓋範圍

14. **不裸 grep**
    現象：規則全文會出現在每個 jsonl 的 `<system-reminder>` 裡（以及工具輸出裡）。
    影響：任何「某字串出現幾次」的 grep 都會被污染。
    處理：只認 JSON 結構；文字要比對時先剝除 `<system-reminder>…</system-reminder>`；角色與工具判定只用 `type:"assistant"` 的 `message.content[]` 中 `tool_use` 的 `name`／`input`。

15. **`tool-results/*.txt` 不是事件**
    現象：`<sid>/tool-results/` 放的是工具輸出快取。
    影響：把它當事件讀會混入不屬於任何 request 的內容。
    處理：不讀；掃描只匹配 `<slug>/*.jsonl` 與 `<slug>/*/subagents/agent-*.jsonl`。順帶：`subagents/` 底下更深的子目錄（例如 workflow 產生的）與其中的檔也不掃，那類 agent 的用量不在報表內（人工）。

16. **時間戳是 UTC，本地日曆日要轉時區**
    現象：jsonl 的 `timestamp` 是 UTC。
    影響：以 UTC 日期分「每日」會與你的本地日曆日錯位。
    處理：extract 存 UTC；`--since`／`--until` 不帶 offset 時依 `--tz`（預設系統本地時區）解讀；報表層轉顯示時區再分日。

17. **窗口邊界與在途 subagent**
    現象：事件依時間戳過濾，窗口終點附近還在跑的 subagent 只有一半落在窗口內；舊 session 也可能被續寫，所以檔案預篩只看 mtime 是否早於 `--since`。
    影響：切在 subagent 執行中間，會把它的成本拆成兩半或漏掉通知／結果。
    處理：窗口以事件時間為界；選窗口終點時避開在途 subagent，或接受邊界誤差並註明。

18. **本機資料不等於全部用量**
    現象：本機只保留設定的天數內的 jsonl（設定項 `cleanupPeriodDays`；實際保留期以自己機器為準，可用 `ls -t` 看最舊檔案的日期）。其他裝置、claude.ai 與手機上的 session 不在本機。
    影響：本機總額不是帳單，也換算不出訂閱額度的百分比；窗口早於保留期的部分根本沒有資料。
    處理：人工；報告開頭註明資料範圍。

## D. 量測解讀

19. **共用工作樹時牆鐘與 token 會互相污染**
    現象：唯讀 verifier／Explore 與寫入者共用同一個 working tree 時，工作區在量測期間被改動。
    影響：同時間跑測試或 build 取得的耗時與 token 數會被交錯污染，單看一個 agent 的牆鐘會失真。
    處理：人工；比較牆鐘（`agents` 的 first/last）時，注意同時間有哪些 agent 在跑。
    出處：`rules/10-dispatch.md`「工作目錄與背景任務安全」一節（唯讀角色也受影響）。

20. **啟發式分類要標示**
    現象：verifier 判定 regex、`bash_writes_heuristic`、`out_est`、`humans[].kind` 都是依文字樣式猜的。
    影響：會有誤判與漏判；regex 誤判在舊分析中常需要人工改判。
    處理：這類欄位名帶 `_heuristic` 或在 `schema.md` 標明啟發式；回報時要註明，重要結論回頭抽樣核對原文。
