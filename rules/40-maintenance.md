# 40 — 系統維護協議

> 讀者：未來要維護本 repo、`~/.claude/`、`~/.codex/`、任何專案 CLAUDE.md 或 AGENTS.md 的 session。
> 本系統以 symlink 安裝：Claude Code 裝到 `~/.claude/`，Codex 裝到 `~/.codex/`，檔案連回 `~/Projects/FatJohn/agents-guideline`，改動會直接反映在 repo，由使用者定期 review 後 commit。

## 1. 檔案清單與權限分級

| 檔案 | 性質 | 可以自行改嗎 |
|------|------|-------------|
| `00-environment.md` | 跨機器事實與風險 | ✅ 更新過時事實（附當場驗證與查證日期）；「三大結構性風險」框架不可移除 |
| `05-hosts.md` | 各機器事實 | ✅ 新機器段落可自行加；過時事實可更新（附探測日） |
| `rules/10-dispatch.md`／`codex/rules/10-dispatch-codex.md`／`rules/20-judgment.md`／`rules/30-delegation-templates.md`／`codex/rules/30-delegation-templates-codex.md` | 系統核心 | ⚠️ 新增條目可以；**修改或刪除既有判準要先問使用者** |
| `40-maintenance.md`（本檔） | 憲法 | ❌ 動之前先問使用者 |
| `50-lessons.md` | 教訓日誌 | ✅ 隨時可加（append-only） |
| `agents/*.md`／`codex/agents/*.toml` | agent 定義 | ✅ 新角色可加；改既有角色的職責先問 |
| 全域 CLAUDE.md | 路由 | ⚠️ 只能加/修路由行，不准把長內容塞回去 |
| 全域 AGENTS.md | Codex 路由 | ⚠️ 只能加/修路由行，不准把長內容塞回去 |
| 各專案的 CLAUDE.md／AGENTS.md | 專案規格，可能是團隊共用 | ❌ 內容修改先問使用者 |

「我覺得這條規則不合理」的情況：提出來問，不要默默繞過。

## 2. 標準修改流程

1. 備份：依目標工具放到 `~/.claude/backups/` 或 `~/.codex/backups/`，檔名帶日期（backups 目錄不存在就建）。
2. 修改（優先「新增段落」而非動既有文字）。
3. 驗證：派 `verifier` read-back，驗收條件至少包含「與其他 rules 檔無矛盾」「引用的路徑/指令實際存在」。
4. 提醒使用者 repo 有未 commit 的變更（不要自行 commit）。

### 並行與本機設定安全

- 同一 working tree 同時只能有一個寫入者；需要平行寫入時，必須使用彼此獨立的 worktree。
- 即使工作切成不重疊檔案，只要共用同一 working tree，寫入仍必須序列執行。
- 修改 `~/.codex/config.toml` 前先備份，修改後驗證不存在重複的 TOML table。
- commit 前 read-back：`git status --short`、`git diff --cached`、`git stash list`；確認 staged scope 與 stash 狀態後才進行下一步。仍須遵守本節第 4 步：不要自行 commit。

## 3. 教訓寫回（每次踩坑後）

寫進 `50-lessons.md`，一行一條，格式：

```
- [YYYY-MM-DD][專案名或 global] 一句情境 → 一句教訓 → 已套用到：{檔名 或「尚未」}
```

- 「值得寫」的門檻：這個坑會讓下個 session 多花 10 分鐘以上，且從 repo/git log 看不出來。
- **同一個坑踩第二次＝該從教訓升級成正式判準**：走「先問使用者」流程提案修改 `20-judgment.md`。

## 4. 記憶寫入規則（制度存活的關鍵）

每個 session 結束前自查一次：
- **使用者糾正過你** → 寫進可用的持久記憶層（Claude：`~/.claude/projects/<專案slug>/memory/`；Codex：`~/.codex/memories/` 由內建 memories 產生／整合），type: feedback，含「為什麼」與「怎麼套用」；能進 repo 的長期制度仍優先進本 repo。
- **發現使用者的偏好／背景** → type: user。
- **跨 session 的進行中工作** → type: project，日期寫絕對日期；Codex 端另用 `session-handoff` skill 更新專案 `.codex/HANDOFF.md`。
- **不要存**：repo 本身就記錄的事（程式結構、git 歷史）、只對當次對話有意義的細節。
- 環境級（跨專案）的事實不進記憶，進 `00-environment.md`。

## 5. 瘦身協議（防膨脹＋日落條款）

- 觸發：`50-lessons.md` 超過 40 條，或任一 rules 檔超過 300 行。
- 動作：刪除已升級成正式判準的教訓；過時事實歸檔到 `~/.claude/backups/`；合併重複。
- **日落條款**：本系統多數規則是在補償當代模型的弱點（context 上限、自驗偏誤、記憶斷裂）。當發現某條規則「不寫模型也自然做得到」時，提案刪除它——制度的理想終點是只剩事實（00）與授權邊界，規則越少代表模型越強，不是制度失敗。
- 瘦身是「搬移與合併」不是「重寫」——整檔重寫需使用者同意；刪併清單先列給使用者確認。

## 6. 路由完整性（防斷鏈）

- 搬移或改名任何被引用的檔案時，同一次修改先用 `rg -l '<舊檔名>' ~/.claude/ ~/.codex/ ~/Projects/FatJohn/agents-guideline/` 找出所有引用一起改；專案 CLAUDE.md／AGENTS.md 裡的引用照 §1 權限先問再改。
- 定期（或使用者要求時）健檢：派 verifier 對每個 rules 檔引用的路徑與指令做存在性檢查。

## 7. 跨專案應用

- 本系統是**環境級**（管「怎麼工作」）；各專案的 CLAUDE.md／AGENTS.md 是**專案規格**（管「寫出什麼樣的東西」）。衝突時專案規格優先。
- 到新專案開工時，先確認該 repo 的可驗證性（能不能本地 build/test？這決定 `20-judgment.md` §2、§5 怎麼落地）。
- 值得留下的專案事實寫進該專案的記憶目錄，不要寫進全域 rules。
