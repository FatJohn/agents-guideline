---
name: maintain-guideline
description: 修改本工作系統本身時使用——`global/**`（入口、judgment、skills、agents、hooks、rubrics、hosts、Codex rules）、本 repo 的 `CLAUDE.md`／`AGENTS.md`、`docs/lessons.md`、任何專案的 CLAUDE.md／AGENTS.md。內含權限分級、兩平台同步矩陣、修改流程、教訓寫回、瘦身與日落條款、路由完整性。動這些檔案之前先讀。
---

# 系統維護協議

> 讀者：在本 repo 維護全域制度的 session。本檔是 repo-only skill（`<REPO>/.claude/skills/`），在本 repo 開工時由專案層載入，不裝進全域。
> `<REPO>` 是 repo 的本機絕對路徑：Claude 看 context 的「# 本機事實：」段，或 `readlink ~/.claude/CLAUDE.md` 去掉 `/global/claude/CLAUDE.md`；Codex 照 `global/codex/AGENTS.md` 的 Bootstrap。複本安裝的機器 readlink 回空，問使用者。
> 安裝形狀依機器而異：多數是 symlink（改 repo 即時生效）；不能提權的機器整套是實體檔複本；Codex agent TOML 一律是同步器寫的實體檔。步驟見 `<REPO>/docs/install.md`。

## 1. 檔案清單與權限分級

| 檔案 | 性質 | 可以自行改嗎 |
|------|------|-------------|
| `global/claude/CLAUDE.md`／`global/codex/AGENTS.md` | 全域入口 | ⚠️ 只能加或修路由行，不准把長內容塞回去；邊界六條兩邊同步 |
| `global/claude/route-card.md` | controller 路由卡（SessionStart 注入主對話） | ⚠️ 新增可以；改既有條目先問 |
| `global/shared/rules/judgment.md` | 判斷準則（每 session 常駐） | ⚠️ 新增條目可以；**修改或刪除既有判準要先問使用者** |
| `global/shared/skills/{dispatch,handoff,git-commit}/SKILL.md`、`global/shared/rubrics/*.md`、`global/codex/rules/{dispatch,delegation-templates}.md` | 系統核心與驗收判準 | ⚠️ 同上 |
| `global/claude/agents/*.md`、`global/codex/agents/*.toml` | agent 定義（角色介面） | ✅ 新角色可加；改既有角色的職責先問 |
| `global/shared/skills/{create-pr,parallel-dispatch,writing-principles}/` | 其餘共用 skill | ✅ 照 §2 改；改 `description` 要同步入口路由表 |
| `global/shared/hosts/<key>.md` | 單機事實（每台只裝自己那份） | ✅ 新機器可建檔，過時事實可更新；標題以「# 本機事實：」開頭並含 hostname |
| `docs/lessons.md`、`docs/lessons-archive.md` | 教訓日誌與封存 | ✅ 隨時可加；封存**不改寫既有條目原文**（唯一例外：專案真名換代號，見 §3） |
| 本 repo 的 `CLAUDE.md`／`AGENTS.md` | 本 repo 專案規格 | ⚠️ 兩份同內容，改一邊同步另一邊 |
| `.claude/skills/maintain-guideline/SKILL.md`（本檔） | 憲法 | ❌ 動之前先問使用者 |
| 各專案的 CLAUDE.md／AGENTS.md | 專案規格，可能是團隊共用 | ❌ 內容修改先問使用者 |

覺得某條規則不合理：提出來問，不要默默繞過。

### 兩平台同步矩陣

- **共用**（`global/shared/**`）：兩個平台裝的是同一個 repo 檔，複製或 symlink 都一樣，改一處兩邊同時生效（複本安裝要重跑 sync-profile）。正文不寫只對單一平台成立的工具名與路徑，平台差異寫進該平台自己的檔。
- **平台專屬**（`global/claude/**`、`global/codex/**`）：不互抄、不互相連結。但入口「邊界」六條與路由表的語意要對齊：改其中一邊時對照另一邊，差異只能是平台措辭與工具名，改完在回報列出對照結果。
- **對照組**：

| Claude | Codex | 對齊什麼 |
|---|---|---|
| `global/claude/CLAUDE.md` | `global/codex/AGENTS.md` | 邊界六條、路由表、Bootstrap |
| `global/claude/agents/worker.md` | `global/codex/agents/worker.toml` | 合約核心：approved plan 前置、single-writer、突變紅綠、不自驗、不擴 scope、禁對外 |
| `global/claude/agents/verifier.md` | `global/codex/agents/{verifier,sol_verifier}.toml` | 找碴範圍、逐條判定、收斂狀態；Codex 高風險派 `sol_verifier` 是刻意分版 |
| `global/claude/route-card.md`＋`global/shared/skills/dispatch/SKILL.md` | `global/codex/rules/dispatch.md` | 派工時機、升降級、驗證不自驗 |

沒有對照的檔是刻意的（`global/claude/{hooks,config}`、Codex 的 `delegation-templates.md` 與其餘角色 TOML），理由見 `<REPO>/docs/repo-layout.md`。

## 2. 標準修改流程

1. 確認回退路徑：`git status --short` 應為乾淨，或至少未提交變更是你自己的。**本 repo 有 git 版控，不要 `cp` 出 `.bak` 檔**，回退用 `git diff`。
2. 修改（優先新增段落，少動既有文字）。
3. 驗證：派 fresh-context `verifier` 做 read-back。Claude 端不因高風險升檔，一律顯式帶 `model: opus`（升 `model: fable` 見 `<REPO>/global/shared/skills/dispatch/SKILL.md` §6『驗證不自驗』）；Codex 端高風險仍派 `sol_verifier`。驗收條件至少含「與其他 global 檔無矛盾」「引用的路徑與指令存在」「兩平台對照組語意對齊」。
4. 提醒使用者 repo 有未 commit 的變更（不要自行 commit）。

**新增或修改 skill／agent／rubric 檔時多一步**：在 repo 加檔不等於任何機器已安裝。新 skill 要補進 `<REPO>/docs/install.md` 的安裝清單與 `<REPO>/scripts/sync-profile.py` 的 `SHARED_SKILLS`；Codex agent TOML 跑 `sync-codex-agents.py --apply`（既有差異加 `--update`），read-back 實體檔 bytes。漏掉這步，規則會指向一個叫不出來的名字。
**新增或修改 skill 的 `description` 時再多一步**：用 `claude -p` 各跑 2 句該觸發、2 句近似但不該觸發的任務描述，以 `--output-format stream-json` 的輸出有無 `Skill` 工具呼叫判定載入，不憑回覆內容猜（Claude Code 容易 under-trigger，該用沒用比誤觸發常見）；只改說明正文不改 description 的不必跑。
**複本安裝的機器還要多一步**：平常改完即時生效的檔也要跑 `python <REPO>/scripts/sync-profile.py --apply --update`；否則 repo 改了、跑起來的還是舊的，兩邊都不報錯，`git status` 也乾淨。

### 本機設定安全

- 改 `~/.codex/config.toml` 前先備份（不在 git 裡），改後驗證沒有重複的 TOML table。
- commit 前 read-back：`git status --short`、`git diff --cached`、`git stash list`。
- 平行寫入：Claude 見 `<REPO>/global/shared/skills/dispatch/SKILL.md` §9『工作目錄與背景任務安全』；Codex 見 `<REPO>/global/codex/rules/dispatch.md` §2『工作目錄與執行安全』。

## 3. 教訓寫回（每次踩坑後）

寫進 `<REPO>/docs/lessons.md`，一行一條：

```
- [YYYY-MM-DD][標籤] 一句情境 → 一句教訓 → 已套用到：{檔名 或「尚未」}
```

教訓日誌留在 repo 當改善依據，**不裝進全域**、不常駐 context。

- **本 repo 是公開 repo，不寫非公開專案的真名**：外部專案標技術領域（`[flutter]`、`[android]`、`[ci]`）或代號（`project-a`、`project-b`…，新專案依序給下一個；代號對照只留本機記憶，不進 repo）；本 repo 自身工作標 `[agents-guideline]`；跨專案通用標 `[global]`。同一規則適用 docs、hosts 紀錄、commit message 與 issue，範例 repo 用 `acme/widgets`。來源追溯依教訓日期回查 `~/.claude/projects/<專案目錄>/*.jsonl`（受 `cleanupPeriodDays` 限制）。
- 值得寫的門檻：會讓下個 session 多花 10 分鐘以上，且從 repo／git log 看不出來。
- **情境壓在一行、上限 80 字**：只留「觸發訊號 → 該怎麼做」，事故脈絡留在當時的 PR／commit。
- **活躍教訓硬上限 8 條**：滿 8 條要記新教訓，必須先升級或封存一條，不准「先加了再說」。
- **同一個坑踩第二次＝升級成正式判準**：先問使用者，提案修改 `<REPO>/global/shared/rules/judgment.md`。
- **升級落地後把該條移到 `<REPO>/docs/lessons-archive.md`**，原文全保留、只搬位置；`docs/lessons.md` 只留「尚未」有判準承接的條目。

## 4. 記憶寫入規則

每個 session 結束前自查一次：
- **使用者糾正過你** → 寫進持久記憶層（Claude：`~/.claude/projects/<專案slug>/memory/`；Codex：`~/.codex/memories/`），type: feedback，含「為什麼」與「怎麼套用」；能進 repo 的制度優先進本 repo。
- **發現使用者的偏好或背景** → type: user。
- **跨 session 的進行中工作** → type: project，日期寫絕對日期；兩平台另用 `handoff` skill 的 session 交接卡。
- **不要存**：repo 已記錄的事、只對當次對話有意義的細節。
- 環境級（跨專案）的事實不進記憶，進 `<REPO>/global/shared/hosts/<key>.md`（環境 gotcha）或 `<REPO>/docs/`。

## 5. 瘦身協議

- **tripwire**（觸發審查，不是優化目標）：`global/claude/CLAUDE.md` 超過 2,500 bytes、`global/claude/route-card.md` 超過 3,000 bytes、`global/shared/rules/judgment.md` 超過 15 條。碰到就排一次日落審查，不是砍到剛好低於門檻（門檻被當目標時，最先被砍的是『不算違規』邊界句）；沒碰到也可以瘦身。bytes 是常駐 context 的代理量，不等於 token。使用率用 `python3 <REPO>/scripts/dispatch-usage.py --days 45` 量。
- **硬上限**：judgment 15 條、活躍教訓 8 條（見 §3）。加一條要先合併或日落一條，不准「先加了再說」；合併後總數 ≤15、或整條搬走且不留只剩動詞與檔名的骨架，才算空出名額。每條判準目標 ≤450 bytes：觸發情境、要做什麼、不算違規、指向。機制事實、指令、數字與『不算違規』邊界砍不動而超標**不算違規**，回報實際 bytes；砍到邊界句才是違規。
- **正反例進 rationale**：✅／❌、訂條理由、事故脈絡與鄰條分工說明一律寫在 `<REPO>/docs/judgment-rationale.md` 同編號章節（原句搬入），常駐正文只留判準；判準仍要讓另一個 agent 只憑這句判得了過或不過。要省空間就整條日落或搬走。
- **驗證方法細節進 `<REPO>/docs/debug-environment-first.md`**：各工具的檢查指令、觸發詞、失敗現場寫那裡，judgment 只留一句判準與指向。
- **只在特定情境用到的內容不放常駐**：常駐＝入口、`host-facts`、`rules/judgment.md`（每 session 全文載入，subagent 也付）與 route card（只注入主對話）。維護協議、rubric、封存教訓、派工範例放 skill、rubric 或 docs。
- **單機事實放 `<REPO>/global/shared/hosts/<key>.md`**，由入口 `@~/.claude/host-facts.md` 匯入。匯入缺檔**靜默略過**，所以入口的 Bootstrap 句不能拿掉，它是唯一偵測。
- **新增、改寫或刪除 `global/shared/rules/judgment.md`、`global/shared/skills/dispatch/SKILL.md`、`global/claude/route-card.md` 的判準內容，觸發條件只有兩種**：(1) 使用者直接要求**修改判準**——只要求 review 不算，使用者對其中某項說「改」才算該項觸發；(2) `docs/lessons.md` 出現新條目，且寫明情境發生在**本 repo 以外的專案 session**（本 repo 自身工作的教訓標 `[agents-guideline]`，依 §3 踩第二次才算觸發）。主動 review 或瘦身掃描這類沒有事故在前的「可以更好」登記為候選：標題前綴 `candidate:` 開 GitHub issue，開之前先 `gh issue list -R FatJohn/agents-guideline --search 'candidate:'` 查重，已有就補在該 issue 下，不進 judgment。
  **不受本條限制**：(a) 已觸發修改的驗收輪次中 verifier 的發現，照 `<REPO>/global/shared/rules/judgment.md` 7『驗收的停止端』處理；(b) 搬移或改名後的路徑更新與斷鏈修正（§6）；(c) `hosts` 的事實更新。本條只管要不要開一輪修改，不管已開的那一輪怎麼收。
- **日落條款**：多數規則在補償當代模型的弱點（context 上限、自驗偏誤、記憶斷裂）。發現某條「不寫模型也自然做得到」就提案刪除：講風格偏好或通用做事方法的日落，講這個環境具體 gotcha 的保留。
- **判定「這段是重複副本」而要刪掉它之前，逐項比對兩邊的資訊量**：用 `rg` 確認被刪的每個關鍵詞在別處仍有命中才動手。**零命中就是未涵蓋**，沒有「語意已被別處涵蓋」這個自行判斷的例外——要嘛併回 canonical，要嘛明說這個入口是刻意放棄的。併回要落在**語意同一邊**：把「整包委派出去」的入口併進「請它給第二意見」是靜默收窄；判定方法是併回後原條目授權的動作還讀不讀得出來。
- 瘦身是「搬移與合併」不是「重寫」；整檔重寫需使用者同意，刪併清單先列給使用者確認。

## 6. 路由完整性（防斷鏈）

- 搬移或改名被引用的檔案時，同一次修改先用 `rg --hidden -l '<舊檔名>' ~/.claude/ ~/.codex/ ~/.agents/ <REPO>/` 找出所有引用一起改；專案 CLAUDE.md／AGENTS.md 裡的引用照 §1 權限先問再改。
- **改 markdown 標題也會斷鏈**：標題一改，下游的 anchor 連結和「§編號『章節名』」引用就死。改完用 `rg --hidden '檔名#'` 與章節名全 repo 驗存活；寧可用「檔案路徑＋章節名」，不手算 GitHub anchor。
- **跨平台共用的章節指向，逐平台各寫一組編號並附章節名**（「Claude：`<REPO>/global/shared/skills/dispatch/SKILL.md` §6『驗證不自驗』；Codex：`<REPO>/global/codex/rules/dispatch.md` §6『驗證語意』」）。兩份編號本來就不同，只寫 §N 會讓另一個平台翻到別節；路徑寫完整，裸檔名從本檔解析不到。
- 定期（或使用者要求時）健檢：派 verifier 對入口與 skill 引用的路徑與指令做存在性檢查。

## 7. 跨專案應用

- 本系統是**環境級**（管「怎麼工作」）；各專案的 CLAUDE.md／AGENTS.md 是**專案規格**（管「寫出什麼樣的東西」）。衝突時專案規格優先。
- 到新專案開工時，先確認該 repo 的可驗證性（能不能本地 build／test？這決定 `<REPO>/global/shared/rules/judgment.md` 1『完成的三個條件』怎麼落地）。
- 專案事實寫進該專案的記憶目錄，不寫進全域。
