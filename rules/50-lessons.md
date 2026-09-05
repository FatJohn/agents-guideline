# 50 — 教訓日誌（只留未升級的活躍教訓）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與格式見 `maintain-guideline` skill §3；瘦身與封存規則見同 skill §5。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接，所以需要常駐提醒。
> 一旦升級成正式判準（改到 10／20 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事在 context 裡佔兩份位置。

- [2026-08-23][global] verifier 交回 N 個實例的清單，我逐個修完就當處理完 → 先當作症狀取樣，問「是什麼產生它們的」再決定修哪一層 → 已套用到：尚未
- [2026-08-26][global] 派工規定「每條規則都要寫出什麼情況不算違規」，原檔沒邊界的條目被 agent 當場發明例外 → 格式欄位是強制的，內容就會被填滿；要求補欄位時同時規定「查無來源就留空」 → 已套用到：尚未
- [2026-09-04][macroeconomics-report] push 後立刻 `gh pr checks --watch` 回「no checks reported」且 exit 0，merge 在 CI 跑完前就按了 → 先等 check 註冊、或改用 `gh run watch <run-id> --exit-status`；閘門指令不要接 `| tail`（`set -e` 不管 pipeline 中段） → 已套用到：尚未
- [2026-09-05][macroeconomics-report] 改名殘留掃描為保護記憶快照排除整個 `.claude/`，連帶蓋住同目錄會被執行的 `launch.json`（指向已刪 workspace） → 排除清單要分「內容型（快照，排除）」與「設定型（會被執行，不可排除）」；設定型用 `git ls-files <dir> | grep -E '\.(json|sh|toml|ya?ml)$'` 列出 → 已套用到：尚未
- [2026-09-05][web-member-login] 收緊安全檢查器改了 10 輪，每輪 verifier 都用 code-change §6 找到新誤叫 → 動既有檢查規則前先備妥行為基線與合法程式碼語料；該 rubric 只長在驗收端 → 已套用到：rules/10-dispatch.md §5（僅分流判準；「先備基線與語料」尚未）

（2026-08-23 另有兩條已升級為 `rules/20-judgment.md` §2 的補充判準並封存至 `docs/lessons-archive.md`；同日另加的兩條判準是直接從事故寫成的，未經本檔，封存檔查不到對應條目。）

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
