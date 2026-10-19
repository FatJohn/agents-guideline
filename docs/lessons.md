# 教訓日誌

> 格式：`- [YYYY-MM-DD][標籤] 情境 → 教訓 → 已套用到：{檔名 或「尚未」}`；本 repo 公開，標籤用技術領域、代號、`agents-guideline` 或 `global`，不寫專案真名。
> 本檔留在 repo 作改善依據，不裝進全域；格式與 8 條上限由 `.claude/skills/maintain-guideline/SKILL.md` §3 規定。
> **本檔只留「已套用到：尚未」的教訓**——它們還沒有正式判準承接。一旦升級成正式判準（改到 `global/shared/rules/judgment.md`、skill 或 agent 定義），把該條移到 `docs/lessons-archive.md`，別讓同一件事佔兩份位置。

- [2026-09-23][project-a] 驗收跑突變讓 dotnet test 卡住，--blame-hang-timeout 每次寫約 7.4GB 傾印，累積 74GB 塞滿磁碟 → 跑突變或可能卡住的 `dotnet test` 一律加 `--blame-hang-dump-type none`（預設 full） → 已套用到：尚未
- [2026-10-09][android] 用桌面 JDK／Robolectric 當「Android 會拒絕 X」的證據，host 底線、IPv6 zone 判定與裝置 libcore 不同 → Android 解析行為要在裝置上實跑（自起 read-only AVD），或讀 `~/Library/Android/sdk/sources/android-*/` 的 libcore 原始碼，並注意不同 API 版本可能不一致 → 已套用到：尚未
- [2026-10-10][macos] macOS 上 probe 目錄名只差大小寫會互相覆蓋（APFS 不分大小寫） → 產生後核對目錄數＝預期數，命名不靠大小寫區分 → 已套用到：尚未
- [2026-10-10][lsp] LSP findReferences 冷啟動（Kotlin／Swift／TS）或 cwd 在專案上層目錄時，只回宣告本身、空結果或報錯 → 不算無引用證據，用 Grep 交叉確認 → 已套用到：尚未
- [2026-10-19][agents-guideline] README 把 rubric 讀者、常駐範圍、分級標籤抄成固定句，來源改了 check_docs 不會紅，英文版是精簡翻譯更易落後 → 改 judgment／agent 合約／安裝對應時順手 grep 兩份 README 同一事實並同步，中英一起改 → 已套用到：尚未

## 交接欄

> 只放「因 session 中斷而未完成的任務」；教訓寫上面，不要兩邊重複。

（目前無）
