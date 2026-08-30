---
name: maintain-guideline
description: 修改本工作系統本身時使用——`<REPO>/rules/*`、全域 CLAUDE.md／AGENTS.md、`agents/*.md`、`codex/agents/*.toml`、`rubrics/*`、任何專案的 CLAUDE.md／AGENTS.md。內含權限分級（哪些可自行改、哪些要先問使用者）、標準修改流程、教訓寫回格式、瘦身與日落條款、路由完整性檢查。動這些檔案之前先讀。
---

# 系統維護協議

> 讀者：要維護本 repo、`~/.claude/`、`~/.codex/`、任何專案 CLAUDE.md 或 AGENTS.md 的 session。
> 本系統以 symlink 安裝：Claude Code 裝到 `~/.claude/`，Codex 裝到 `~/.codex/`，檔案連回本系統 repo，改動會直接反映在 repo，由使用者定期 review 後 commit。
> 下文以 `<REPO>` 代稱 repo 的本機絕對路徑——它依機器而異，canonical 清單在 `<REPO>/rules/05-hosts.md`。不確定時依當前平台讀全域入口的 symlink target：Claude 用 `readlink ~/.claude/CLAUDE.md`，Codex 用 `readlink ~/.codex/AGENTS.md`；PowerShell 分別用 `(Get-Item ~/.claude/CLAUDE.md).Target`、`(Get-Item ~/.codex/AGENTS.md).Target`。target 的目錄部分就是 `<REPO>`。
> 本檔在 `skills/` 底下而非 `rules/`，所以**不會每 session 自動載入**——這是刻意的：維護協議只在真的要動系統時才需要在 context 裡。

## 1. 檔案清單與權限分級

| 檔案 | 性質 | 可以自行改嗎 |
|------|------|-------------|
| `rules/00-environment.md` | 跨機器事實與風險 | ✅ 更新過時事實（附當場驗證與查證日期）；「三大結構性風險」框架不可移除 |
| `rules/05-hosts.md` | 各機器事實 | ✅ 新機器段落可自行加；過時事實可更新（附探測日） |
| `rules/10-dispatch.md`／`rules/20-judgment.md`／`codex/rules/10-dispatch-codex.md`／`codex/rules/30-delegation-templates-codex.md` | 系統核心 | ⚠️ 新增條目可以；**修改或刪除既有判準要先問使用者** |
| `skills/maintain-guideline/SKILL.md`（本檔） | 憲法 | ❌ 動之前先問使用者 |
| `rules/50-lessons.md` | 活躍教訓日誌 | ✅ 隨時可加；升級成判準後移到 `<REPO>/docs/lessons-archive.md` |
| `docs/lessons-archive.md` | 教訓封存 | ✅ 可加封存條目；**不改寫既有條目原文** |
| `rubrics/*.md` | 驗收判準（verifier 讀） | ⚠️ 新增條目可以；修改或刪除既有判準要先問使用者 |
| `agents/*.md`／`codex/agents/*.toml` | agent 定義（＝角色介面） | ✅ 新角色可加；改既有角色的職責先問 |
| 全域 CLAUDE.md | 路由 | ⚠️ 只能加/修路由行，不准把長內容塞回去 |
| 全域 AGENTS.md | Codex 路由 | ⚠️ 只能加/修路由行，不准把長內容塞回去 |
| 各專案的 CLAUDE.md／AGENTS.md | 專案規格，可能是團隊共用 | ❌ 內容修改先問使用者 |

「我覺得這條規則不合理」的情況：提出來問，不要默默繞過。

## 2. 標準修改流程

1. 確認回退路徑：`git status --short` 應為乾淨，或至少確認未提交變更是你自己的。**本 repo 有 git 版控，不要 `cp` 出 `.bak` 檔**——那是雜訊，回退用 `git checkout`／`git diff`。
2. 修改（優先「新增段落」而非動既有文字）。
3. 驗證：派 fresh-context verifier 做 read-back；一般驗收兩端都用 `verifier`，高風險或動到憲法／判準時 Claude 用同一個 `verifier` 但呼叫時指定 `model: fable`、Codex 用 `sol_verifier`。驗收條件至少包含「與其他 rules 檔無矛盾」「引用的路徑/指令實際存在」。
4. 提醒使用者 repo 有未 commit 的變更（不要自行 commit）。

**新增 skill／agent／rubric 檔時多一步**：在 repo 加檔**不等於**任何機器已安裝——加完當場重跑 README 的安裝段（可重跑，已存在會略過），再 read-back symlink 與當下的 skill／agent 清單確認叫得出名字。漏掉這步，規則會指向一個當下根本叫不出來的名字。

### 本機設定安全

- 修改 `~/.codex/config.toml` 前先備份（這個檔不在 git 裡），修改後驗證不存在重複的 TOML table。
- commit 前 read-back：`git status --short`、`git diff --cached`、`git stash list`；確認 staged scope 與 stash 狀態後才進行下一步。仍須遵守本節第 4 步：不要自行 commit。
- 平行寫入與 working-tree 所有權規則見對應平台 dispatch：Claude 為 `<REPO>/rules/10-dispatch.md`「工作目錄與背景任務安全」；Codex 為 `<REPO>/codex/rules/10-dispatch-codex.md` §2「工作目錄與執行安全」。

## 3. 教訓寫回（每次踩坑後）

寫進 `<REPO>/rules/50-lessons.md`，一行一條，格式：

```
- [YYYY-MM-DD][專案名或 global] 一句情境 → 一句教訓 → 已套用到：{檔名 或「尚未」}
```

- 「值得寫」的門檻：這個坑會讓下個 session 多花 10 分鐘以上，且從 repo/git log 看不出來。
- **情境壓在一行、上限 80 字**：活躍條目只留「觸發訊號 → 該怎麼做」，完整事故脈絡留在當時的 PR／commit 或封存檔。
  情境是專案專屬、且每個 session 都不需要的那部分，而它正是條目變長的主因。
  （80 是量現有條目後訂的可達值，不是理想值——訂一個沒人做得到的數字等於沒訂。）
- **同一個坑踩第二次＝該從教訓升級成正式判準**：走「先問使用者」流程提案修改 `<REPO>/rules/20-judgment.md`。
- **升級落地後把該條移到 `<REPO>/docs/lessons-archive.md`**（原文不改寫，只搬位置）。`<REPO>/rules/50-lessons.md` 常駐在每個 session 的 context 裡，只該留「尚未」有判準承接的教訓；已被判準吸收的條目留在那裡等於同一件事佔兩份 context。

## 4. 記憶寫入規則（制度存活的關鍵）

每個 session 結束前自查一次：
- **使用者糾正過你** → 寫進可用的持久記憶層（Claude：`~/.claude/projects/<專案slug>/memory/`；Codex：`~/.codex/memories/` 由內建 memories 產生／整合），type: feedback，含「為什麼」與「怎麼套用」；能進 repo 的長期制度仍優先進本 repo。
- **發現使用者的偏好／背景** → type: user。
- **跨 session 的進行中工作** → type: project，日期寫絕對日期；Codex 端另用 `session-handoff` skill 更新專案 `.codex/HANDOFF.md`。
- **不要存**：repo 本身就記錄的事（程式結構、git 歷史）、只對當次對話有意義的細節。
- 環境級（跨專案）的事實不進記憶，進 `<REPO>/rules/00-environment.md`。

## 5. 瘦身協議（防膨脹＋日落條款）

- 觸發：`<REPO>/rules/50-lessons.md` 的活躍教訓超過 **8** 條，或任一 `<REPO>/rules/` 檔超過 200 行，或 `<REPO>/rules/` 全目錄超過 40,000 bytes（該目錄每 session 全文載入，bytes 就是固定成本）。
- **活躍教訓是硬上限 8 條，不是軟建議**：滿 8 條時要記新教訓，**必須先升級或封存一條**，不准「先加了再說」。
  下修理由（2026-08-04）：原本的 15 條門檻從未被觸發過，而實測 14 條就吃掉 `rules/` 24% 的常駐預算；
  同期 14 條**全部**是「已套用到：尚未」——一個月零升級證明這個檔案的失敗模式是「只進不出」，
  所以真正有效的機制不是更大的容量，是逼人在加新條目時付出清舊條目的成本。
- 動作：已升級成判準的教訓搬到 `<REPO>/docs/lessons-archive.md`；只在特定情境才需要的長內容搬出 `<REPO>/rules/`（進 `<REPO>/skills/`、`<REPO>/rubrics/` 或 `<REPO>/docs/`）；合併重複；同一條規則只留一個 canonical 位置，其餘改為指向。
- **驗證方法類判準：判準留常駐、細節進 skill**——「怎麼驗才算驗到」這類判準（各工具的檢查指令、觸發詞清單、失敗現場）一律寫進 `<REPO>/skills/debug-environment-first/SKILL.md`，`<REPO>/rules/20-judgment.md` §2 只留一句判準、一組正反例與指向。
  訂這條的理由（2026-08-23）：同一天升級的兩條判準，一條照這個模式落地、另一條整段含例塞進常駐區，§2 因此一次長了 32 行——膨脹主因是落地模式不一致，不是判準太多。
- **只在特定情境才用得到的內容不該放 `rules/`**：`rules/` 是無條件常駐區，付的是每個 session 的固定成本。維護協議、驗收 rubric、封存教訓、派工範例都屬於「用到才讀」，放 `skills/`／`rubrics/`／`docs/`。
- **日落條款**：本系統多數規則是在補償當代模型的弱點（context 上限、自驗偏誤、記憶斷裂）。當發現某條規則「不寫模型也自然做得到」時，提案刪除它——制度的理想終點是只剩事實（00／05）與授權邊界，規則越少代表模型越強，不是制度失敗。判斷訊號：這條規則在講**風格偏好或通用做事方法**（模型自己會）還是在講**這個環境的具體 gotcha**（模型不可能知道）？前者日落，後者保留。
- **判定「這段是重複副本」而要刪掉它之前，逐項比對兩邊的資訊量**：「看起來更完整」不等於涵蓋——留下的 canonical 很可能少了幾個只寫在被刪那份裡的機制事實。用 `rg` 確認被刪的每個關鍵詞在別處仍有命中才動手。**零命中就是未涵蓋，沒有「語意已被別處涵蓋」這個自行判斷的例外**——要嘛把該事實併回留下的 canonical，要嘛明說這個入口是刻意放棄的。併回時還要落在**語意同一邊**：把「整包委派出去」的入口併進「請它給第二意見」那一類，等於靜默收窄，`rg` 會顯示命中但入口已經換了一個。判定方法：併回之後，原條目授權的那個動作還能不能從新位置讀出來？讀不出來就是換邊了。
- 瘦身是「搬移與合併」不是「重寫」——整檔重寫需使用者同意；刪併清單先列給使用者確認。

## 6. 路由完整性（防斷鏈）

- 搬移或改名任何被引用的檔案時，同一次修改先用 `rg -l '<舊檔名>' ~/.claude/ ~/.codex/ <REPO>/` 找出所有引用一起改；專案 CLAUDE.md／AGENTS.md 裡的引用照 §1 權限先問再改。
- **改 markdown 標題也會斷鏈，不是只有搬檔會**：標題一改，下游所有 anchor 連結（`檔名#章節`）就死。改完用 `rg '檔名#'` 全 repo 驗存活。手算 GitHub anchor 容易錯，歷史文件寧可用「檔案層連結＋章節名文字」而不是 anchor。
- **跨平台共用的章節指向，一律逐平台各寫一組編號並附章節名**（「Claude：`<REPO>/rules/10-dispatch.md` §5『驗證不自驗』；Codex：`<REPO>/codex/rules/10-dispatch-codex.md` §6『驗證語意』」）。兩份 dispatch 的章節編號本來就不同，只寫 §N 會讓另一個平台翻到別節；章節名是編號漂移時唯一的救命錨點。連例子裡的檔名也要寫成可解析的路徑——本檔在 `skills/` 底下，裸檔名從這裡解析不到。
- 定期（或使用者要求時）健檢：派 verifier 對每個 rules 檔引用的路徑與指令做存在性檢查。

## 7. 跨專案應用

- 本系統是**環境級**（管「怎麼工作」）；各專案的 CLAUDE.md／AGENTS.md 是**專案規格**（管「寫出什麼樣的東西」）。衝突時專案規格優先。
- 到新專案開工時，先確認該 repo 的可驗證性（能不能本地 build/test？這決定 `<REPO>/rules/20-judgment.md` §2「何時算真的完成」與 `<REPO>/rubrics/code-change.md` 怎麼落地）。
- 值得留下的專案事實寫進該專案的記憶目錄，不要寫進全域 rules。
