# 50 — 教訓日誌（只留未升級的活躍教訓）

> 格式：`- [YYYY-MM-DD][專案名或 global] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`
> 寫入門檻與格式見 `maintain-guideline` skill §3；瘦身與封存規則見同 skill §5。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接，所以需要常駐提醒。
> 一旦升級成正式判準（改到 10／20 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事在 context 裡佔兩份位置。

- [2026-09-23][project-a] 驗收跑突變讓 dotnet test 卡住，--blame-hang-timeout 每次寫約 7.4GB 傾印，累積 74GB 塞滿磁碟 → 跑突變或可能卡住的 `dotnet test` 一律加 `--blame-hang-dump-type none`（預設 full） → 已套用到：尚未
- [2026-10-09][sdk-member-auth-flutter] 用桌面 JDK／Robolectric 當「Android 會拒絕 X」的證據，host 底線、IPv6 zone 判定與裝置 libcore 不同 → Android 解析行為要在裝置上實跑（自起 read-only AVD），或讀 `~/Library/Android/sdk/sources/android-*/` 的 libcore 原始碼，並注意不同 API 版本可能不一致 → 已套用到：尚未
- [2026-10-10][sdk-member-auth-flutter] macOS 上 probe 目錄名只差大小寫會互相覆蓋（APFS 不分大小寫） → 產生後核對目錄數＝預期數，命名不靠大小寫區分 → 已套用到：尚未
- [2026-10-10][member-auth-workspace] LSP findReferences 冷啟動（Kotlin／Swift／TS）或 cwd 在專案上層目錄時，只回宣告本身、空結果或報錯 → 不算無引用證據，用 Grep 交叉確認 → 已套用到：尚未

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
