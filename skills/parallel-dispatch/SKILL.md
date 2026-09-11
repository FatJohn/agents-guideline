---
name: parallel-dispatch
description: 準備讓 ≥2 個各需寫入的切片平行開發與驗收時使用；spec 或 grilling 結論尚未切分、要先判斷能不能切時也用。觸發句：「平行做」「同時派」「這幾個 issue 一起處理」「切成幾個 task 同時開發」「能不能切」，及英文 "in parallel"、"split this into tasks"。已有切好的 tracker 項目（GitHub issue／ClickUp sub task）要直接平行派工與合併驗收時同樣觸發。
allowed-tools: Bash(git:*), Bash(gh:*), Read, Grep, Glob
---

# Parallel Dispatch

一個 feature／task 切分後，同時派多個 agent 開發與驗收的完整流程：怎麼切、怎麼平行派工、怎麼合併與整合驗收。（下文 `<REPO>` 指本工作系統 repo 的本機路徑，取法見 `~/.claude/CLAUDE.md` 檔頭。）承接 `~/.claude/rules/10-dispatch.md` 的既有合約（單一 worktree 單一寫入者、派工三段合約、驗證不自驗）；本檔只補「平行」這個維度特有的判準，兩者衝突時以 `10-dispatch.md` 為準。

## §0 兩個入口與「不值得切」判準

- **入口 A**：tracker 已有切好的項目（GitHub issue／ClickUp sub task）→ 跳過 §1，直接進 §2。
- **入口 B**：grilling／spec 產出，尚未切 → 先走 §1。

**不值得切、改序列派一個 `worker`**：以下任一成立就不切：

1. 切出的片無法各自寫出獨立驗收條件。
2. 切完只有 1 片無依賴（切了也不會平行）。
3. 每片預估路徑都含同一個檔案（切了也只能序列）。
4. 整份 spec 派一個 `worker`、走一次 `~/.claude/rules/10-dispatch.md`「Controller 工作迴圈」就能做完（沒有平行收益）。

## §1 切分段（入口 B）

**誰切**：spec 只動一個模組且預估 ≤3 片 → controller 主對話直接切；跨模組，或 controller 自己看不清依賴 → 派 `Plan`（`model: opus`）出切分方案，controller 核定。

**每片必帶四項**：目標、獨立驗收條件、依賴的其他切片、預估會動的路徑。路徑只用來「合併重疊的兩片」或「標依賴」，**不是**正式的檔案所有權宣告——不必為此另花 token 事前分析既有 issue 的所有權邊界。

**依賴處理**：有依賴關係的片序列做；只有互不依賴的片進同一批。例外——「先凍介面、commit stub、再平行」，兩個條件都成立才用：(1) 上游對外的型別／函式簽名能在切分階段就寫成可 commit 的 stub；(2) 下游片的驗收條件只依賴那個簽名、不依賴上游的實作行為。stub 由 controller 在 base branch 上 commit，再開這一批的 worktree。

**落地到該專案的 tracker**：由專案 `CLAUDE.md` 宣告（例如 `tracker: clickup list <id>`），未宣告一律預設 GitHub issue。ClickUp 情境：一個 task＝一批切分，sub task＝切片，與 GitHub 的關聯寫在 PR body 裡；branch 名沿用該 repo 既有慣例，不塞 ClickUp ID。**建立 tracker 項目由 controller 做，不派 worker**（`~/.claude/agents/worker.md` 第 5 條把開 issue 列為 worker 禁止動作）。做法：切分方案先列成清單給使用者看，使用者對這份清單明確同意（「可以」「建」之類的核可；有保留意見就先改清單再問）一次，即視為對清單內每一項的當次授權；清單以外的項目與下一批仍要另取授權，不推廣為常設政策。

## §2 派工段

- 一個 controller session，一次發出多個 Agent 呼叫；每個都設 `isolation: worktree`。執行者依 `~/.claude/rules/10-dispatch.md` §1 表選角色，一般實作是 `worker`（`model: sonnet`）。
- **一批上限 3 片**；一批全部 merge 完成（含 §3 整合驗收）後才開下一批——不滾動補位，因為整合驗收需要明確的批次邊界，滾動會讓「這批測過了嗎」變成無法回答的問題。

**worker prompt 在 `~/.claude/agents/worker.md` 合約之外必加四項**（平行情境特有；其中第 1、2 項依 `~/.claude/agents/worker.md` 第 5 條的「隔離 worktree 例外」才合法，plan 必須明寫「本任務在隔離 worktree，依該例外可 commit 與 rebase」）：

1. 在自己 worktree 的 branch 上 commit，**不 push**——push 交回 controller 走 `create-pr` skill。
2. 完成前 rebase 到最新 base branch 一次；有 conflict 自己解，解完重跑一次機械驗證。
3. 回報必含三項：worktree 絕對路徑、branch 名、HEAD sha——harness 不會替 controller 回報 worktree 路徑，controller 要靠這三項做 read-back。
4. 明白提醒它仍是自己 worktree 的**唯一寫入者**；同批其他片在別的 worktree，不共用。

**controller read-back**（不採信 worker 自述，逐一實查）：

```
git worktree list
git -C <worktree路徑> log -1 --format=%H
git -C <worktree路徑> status --short
```

**語意衝突判斷**：git 能自動合但兩片行為互踩（例如一片改了函式簽名的語意、另一片仍照舊語意呼叫），或兩片同時改同一函式的邏輯——這類升 controller 親自判斷；controller 判不了才問使用者。純文字 conflict 由 worker 自己在 rebase 時解掉，不升級。

## §3 合併與驗收

- 一切片一 PR，沿用 repo 現有 branch 慣例；push 與開 PR 由 controller 走 `create-pr` skill（鐵律二：對外動作，當次授權）。
- **切片級驗收** ＝ `verifier`（`model: opus`）＋ PR 上的 CI，這比 `10-dispatch.md` §5 對一般程式碼的要求（製作者機械驗證即可）多一層——平行情境下每片都要在合併前有 fresh-context 判定，是本 skill 刻意加的。
- **merge 順序 ＝ 完成順序**（先做完先 merge，不強求切分時的順序）。

**整合驗收觸發條件（任一成立就觸發）**：

1. merge 過程中發生 conflict。
2. `gh -R <owner/repo> pr diff <n> --name-only` 兩兩比對，有同檔或同目錄重疊。

觸發時：全部 merge 進 base branch 後，派一個 **fresh** `verifier`（`model: opus`）只驗「跨切片互動」，並跑一次完整測試——這個 verifier 不重驗每片已過的切片級驗收條件，只找片與片之間新產生的問題。零重疊時整合驗收退化成「全部 merge 後跑一次完整測試」，不必另派 verifier。

**為什麼只看 conflict 不夠**：A 改了一個函式的介面（例如回傳型別或參數語意），B 依照舊介面寫呼叫端——兩個檔案完全不重疊，git 不會回報 conflict，但合併後行為是錯的。所以觸發條件除了 conflict，還要看檔案清單的重疊；同目錄重疊納入，是因為介面與呼叫端多半在同一個模組目錄下。

## §4 人手多開 session（附段，非主線）

使用者自己開多個 Claude session、各自用 worktree 平行做事時的慣例（沒有 controller 角色，靠使用者自律）：

- worktree 統一放 `<專案repo>/.claude/worktrees/<name>/`，branch 命名依 repo 既有慣例。
- 每個 session 開工前先 `git worktree list`，確認沒有撞到別人正在用的 worktree。
- 沒有 controller 就沒有 §3 的整合驗收——merge 前自己跑一次完整測試，跨切片互動問題靠自己肉眼複查。

## §5 harness 事實（2026-09-12 查證，Claude Code 2.1.267；canonical 在 `<REPO>/docs/harness-facts.md`，版本更新後改那份）

- subagent 的 `isolation: worktree` 建在 `<專案repo>/.claude/worktrees/<name>/`，branch 名為 `worktree-<name>`，從 controller 當下的 HEAD 開出；有改動（commit 或 uncommitted）就保留、無改動則連 branch 一起自動刪除（「無改動→刪除」為 2026-09-12 空手 subagent 實測；「有改動→保留」依官方 worktrees 文件，未另實測——controller 仍要即時 read-back，不假設 commit 必然存活）。harness 不會把路徑回報給 controller，所以 §2 要求 worker 自己回報。
- 官方不提供多個 worktree 之間的合併方式；合併全部交給 controller 走 §3。
- Workflow 工具的 `agent()` 查不到 `isolation` 參數（未確認支援），且依全域 `CLAUDE.md` 授權規則，Workflow 需要使用者當次明確要求才能用——本 skill 不使用它。

## §6 刻意不做

- Workflow 工具（理由見 §5）。
- 既有 issue 的事前檔案所有權分析（§1 已說明路徑只用來合併重疊或標依賴）。
- 滾動補位（§2 已說明整合驗收需要明確批次邊界）。
- 每次 merge 通知全員 rebase（worker 自己在完成前 rebase 一次，見 §2）。
- 把「切分」獨立成另一個 skill（§1 已在本檔內完整涵蓋）。
- superpowers `subagent-driven-development` 式的每 task 雙判 review：本系統的 `verifier` 合約與 `~/.claude/rules/20-judgment.md` §2「停止端」已等價；且該 skill 明文禁止平行、沒有合併步驟，解的不是本 skill 要解的問題。
