---
name: worktree-session
description: 開工前把工作放進自己的 worktree（`git worktree` 或 `orca worktree`）、把互相獨立的多個 issue 各開成一個頂層 session、盤點 session 怎麼起 issue session 與收結果、worktree 怎麼清。要開工或建工作環境（「開工前建 worktree」「先把環境準備好」）、要同時處理幾個 issue（「這幾個 issue 一起處理」、"split this into sessions"）、要清 worktree 時使用。Use when starting work in a worktree, fanning independent issues out to their own sessions, or cleaning worktrees up.
allowed-tools: Bash(git:*), Bash(gh:*), Bash(orca:*), Read, Grep, Glob
---

# worktree-session — 一個 session 一個 worktree

平行開發的單位是**頂層 session**，不是 subagent：每個 session 在自己的 worktree 裡是完整的 controller（有完整的 CLAUDE.md、hook、記憶，自己實作、自己派 verifier、自己交付）。本 skill 只管三件事：開工時怎麼進 worktree、多個 issue 怎麼分 session、worktree 怎麼清。`<REPO>` 依全域 `CLAUDE.md`／`AGENTS.md` 的 Bootstrap 解出。驗收沿用 `~/.claude/skills/dispatch/SKILL.md` §1『驗證不自驗』與 §2『修正與驗收輪次』。

## 1. 開工預設在 worktree

會改檔的工作一律在自己的 worktree 做，main working tree 只留給盤點、讀碼與 merge；單一任務也一樣，不等到要平行才開。理由：同一 working tree 同一時間只能有一個寫入者（全域邊界 5），worktree 讓這條規則變成目錄邊界而不靠自律；verifier 跑測試時工作區不會被改動；開第二個 session 不必先問第一個做到哪。

- 建法與位置：`git -C <repo> worktree add <repo>/.worktrees/<名> -b <branch> <base-ref>`，或 Orca 的 `orca worktree create`（位置 `<repo>/.orca/workspaces/<repo-name>/<名>`）；Claude Code 內建 `isolation: worktree` 另放 `<repo>/.claude/worktrees/`。三個位置的忽略方式、搜尋副作用與 `check-ignore` 驗證見 `references/worktree.md`「所有權與路徑」。
- 建立後 `git worktree list` read-back，記下絕對路徑、branch、base SHA；之後所有 git／gh 指令逐條綁定（`git -C <path>`、`gh pr view <n> -R <owner/repo>`），不靠 cwd（`~/.claude/rules/judgment.md` 11）。
- 使用者已在某個 worktree 裡開 session（cwd 就是 worktree）時不再另開；`git -C . rev-parse --git-common-dir` 不等於 `.git` 就是在 worktree 裡。
- 已在 main working tree 做了未提交的改動才想起要開：先 `git stash` 或先 commit 到暫時 branch 再開，不把改動複製到 worktree（另一邊的 base 可能已前進，複製會覆蓋新 code）。
- subagent 不是寫入者：verifier 只寫 repo 外探針目錄，查詢型角色唯讀。要給 verifier 乾淨工作區時用 `isolation: worktree`，其餘情況不給 subagent 開 worktree。

## 2. 多個 issue：一 issue 一頂層 session

互相獨立的 issue（各自可單獨交付、不必一起整合）一個 issue 一個頂層 session，不由同一個 controller 平行扛、也不拆給 subagent。判不出是否獨立（共用 schema、lockfile、registry、CI 設定、migration 序號，或驗收要一起跑）就當成相依，序列做。理由與量測見 `<REPO>/docs/reviews/issue-session-trial-2026-10.md`。

**盤點 session**（通常是使用者正在用的那個）只做四件事：現查 tracker 與 open PR，列出可做／blocked 項目、優先序與共用觸點，有共用觸點的 issue 序列開、不同時開；每個 issue 寫一份 brief 到 `<repo>/.worktrees/briefs/<issue>.md`；逐一起 issue session（指令與 fallback 見 `references/cli.md`「盤點 session 與 issue session」）；收結果時只讀各 worktree 的 `.worktrees/result.md` 與 `gh pr view`。不逐票讀 source、不收完整回報、不追各 issue 的 CI；欄位不足或 `unknown` 就送回該 issue session 補，不自己重跑它的探索或驗收。一個 issue 交付後要換主題，開新 session，不在大 context 上接新主題。

**brief**：目標與動機、tracker 連結、base ref、共用觸點與禁止碰的路徑、完成定義、授權、交付檔路徑，以及「需要使用者決策或授權時：寫進 `result.md` 的 Pending authorization／Blocker，繼續做不被該答案擋住的部分，不用等鍵盤回答的工具停住等」。**授權**以 session 為單位（鐵律二）：brief 只能逐字引用使用者在盤點 session 對**該 issue** 明說的動作與對象，以「使用者原話：」開頭並註明對象 issue，上限 push feature branch＋開 PR；沒說就寫「無」。issue session 只認這段，merge、對外訊息與 brief 沒列的動作一律等使用者在該 issue 的分頁親口授權。

**issue session result**（issue session → 盤點 session）：落地位置 `$(git rev-parse --show-toplevel)/.worktrees/result.md`（自己的 worktree 內）。填不出來的欄寫 `unknown`＋原因，不留空：

```text
Issue: <tracker 連結或編號>
Status: working | blocked | awaiting verification | ready for authorization | merged | unknown
Worktree: <絕對路徑>    Branch: <branch>
Base SHA: <sha>    Candidate SHA: <HEAD；未 commit 寫 uncommitted>    Dirty: <git status --short 行數；0＝乾淨>
Files changed: <已 commit：git diff --name-only <base>...HEAD；uncommitted：git status --short＋git diff --name-only，不能拿 HEAD diff 判零；碰到 brief 列的共用觸點或禁止路徑的另標>
Verification: <CONVERGED | PROSE-ONLY | OPEN | INCONCLUSIVE @<sha>；修正輪數 <n>；探針目錄路徑；未派寫「未驗收」>
PR / CI: <PR 連結；寫 result.md 當下 `gh pr checks` 一次讀到的 required CI 狀態與對應 SHA，不等它跑完；無 PR 寫「無」>
Cross-issue risk: <共用觸點、base 變動、與其他 issue 互踩；無則「無」>
Pending authorization: <待使用者在本 issue session 親口授權的動作；無則「無」>
Blocker: <一句；無則「無」>
Merged: <merge SHA；merge 後補；未 merge 寫「—」>
```

`awaiting verification`＝已派 verifier 未回；`ready for authorization`＝驗收收斂且 PR 已開，只差 Pending authorization 列的動作；`merged` 必須同時有 Merged 欄的 SHA。TUI 閒置、process 結束、分頁無回應都不對應任何狀態，盤點 session 查到這些只代表該去讀 result.md 或在那個分頁問，不得據此推進狀態。

**整合**：各 issue 各自走 PR 與 CI；merge 由使用者或盤點 session 依當次授權執行。被判獨立卻在 merge 時才發現互踩的，後 merge 的 issue session 在當前 base 重跑完整檢查，並回報盤點 session 修正下次的共用觸點判斷。某個 issue merge 後才發現壞：revert **該 issue** 的 merge，其餘不動。

## 3. 清理

清 worktree 與 branch 只在 `references/worktree.md`「清理的證據條件」全部成立後進行，且以 `&&`／`test` 串起來強制，不靠人眼看結果；刪除**非本次自建**的 worktree／branch 仍需明確授權（鐵律二）。先關 session 再清 worktree（避免清理時仍有 process 在寫），Orca 建的 worktree 的關法與 read-back 見 `references/cli.md`「清理」。

## 4. 邊界

不做：把 issue 拆給 subagent 當實作者；在 worktree 之間用複製檔案代替 git 合併；為了用某個 workspace 工具（Orca、tmux、VS Code 分頁）而改變上述任何一步，它們只是 session 的容器；讓 issue session 取得 brief 沒逐字引用的授權；把 git 無 conflict 當語意安全。同一 issue 內切片給多個 agent 平行做的 divide-and-conquer 與 agent race 流程已於 2026-10 日落，舊設計與理由見 `<REPO>/docs/reviews/parallel-dispatch-design-2026-09.md`。
