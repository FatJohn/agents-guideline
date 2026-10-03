# 50 — 教訓日誌（只留未升級的活躍教訓）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與格式見 `maintain-guideline` skill §3；瘦身與封存規則見同 skill §5。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接，所以需要常駐提醒。
> 一旦升級成正式判準（改到 10／20 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事在 context 裡佔兩份位置。

- [2026-09-23][project-a] 驗收跑突變讓 dotnet test 卡住，--blame-hang-timeout 每次寫約 7.4GB 傾印，累積 74GB 塞滿磁碟 → 跑突變或可能卡住的 `dotnet test` 一律加 `--blame-hang-dump-type none`（預設 full） → 已套用到：尚未

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
