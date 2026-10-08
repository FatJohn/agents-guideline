# Adapter：外部 CLI process（純 shell、tmux、VS Code／Cursor terminal、Herdr、Orca、未來工具）

配合 [../SKILL.md](../SKILL.md) §9 的 adapter 契約使用（launch、follow-up、query status、collect、stop、workspace）。這一類環境的共同點：**每個 worker 是一個獨立的 coding agent CLI process**（`claude`、`codex` 或其他），controller 是另一個 session 或人。tmux、VS Code、Herdr、Orca 只是這些 process 的 terminal／session 容器；它們提供的 workspace、分頁、狀態面板都是 UX，不進 SKILL 的任何判斷。未來工具只要能做下表五件事，就照本檔用，不必改 SKILL。

| 契約項目 | 本 adapter 的做法 |
|---|---|
| launch | 在該片 worktree 目錄啟動 CLI，brief 從檔案餵入：`cd <wt> && claude -p "$(cat <brief>)"`／`codex exec "$(cat <brief>)"`，或互動模式貼 brief。旗標以當下 `--help` 現查，不憑記憶。session 由容器決定：純 shell 開新 terminal；tmux 一 window 一 worker；VS Code 一 terminal 分頁一 worker；Herdr／Orca 一 workspace 一 worker。**一個 session 對應一個 worker，不對應一個 task**——task 可換 worker、worker 可換 session。記下每個 worker 的 PID 或 session 名，stop 要用 |
| workspace | controller（或人）先以 `worktree.md`「所有權與路徑」的 `git worktree add` 建每片 worktree。Orca 等工具若能自動建 worktree，用它建出來的路徑即可，但仍要 `git worktree list` read-back 並記錄絕對路徑與 branch；不用它的 workspace model 代替 SKILL §3 的 graph |
| query status | 兩層：git read-back（`git -C <wt> status --short`、`rev-parse HEAD`、`diff --stat`）＋ worker report 落檔（brief 指定 `<log-dir>/<slice>-report.md`，`<log-dir>` 在 repo 外）。容器的「執行中／完成」指示燈只是線索，不是證據 |
| follow-up | 用該 CLI 的 resume／continue 機制續同一 session（現查 `--help`），或在同一 worktree 起新 process 並把原 report、finding、diff 餵入——前提是舊 process 已依 stop 確認結束 |
| collect | worker report 落檔 `<log-dir>/<slice>-report.md`（brief 指定），非互動模式另記 process exit code；沒有 report 檔＝未完成 |
| stop | 結束該 process 或關閉其 session（`kill <pid>`／容器的關閉指令）；主判準是以 `ps -p <pid>` 或 session 清單確認 process 真的消失，容器顯示「已停止」不算，process 還在就是還在寫。`git -C <wt> status --short`＋`rev-parse HEAD` 兩次 read-back（相隔至少 60 秒，未實測的保守值）只作佐證，須無變化 |

## 派工與 worktree

- worker **預設禁止** commit／rebase（同 `<REPO>/agents/worker.md` 規則 5）。要開放，brief 的 Execution environment 欄必須明寫「本任務在隔離 worktree（`isolation: worktree` 或 controller 自建 worktree）」這句——它是對 worker 合約的宣告，不是 CLI 旗標，外部 CLI 沒有這個參數——寫了才適用 worker 合約的隔離例外（可在自己 branch commit、完成前 rebase 一次、解純文字 conflict；PR／merge 仍禁止；push 另依 worker 規則 5，須 brief 明文寫出 controller 已取得使用者對該 push 的授權）；沒寫就是禁止。worker 若是 Codex，一律依 `codex.md`（不得 commit／rebase）。
- 裝了 `block-ci-edit` hook 的機器（見 `<REPO>/docs/install.md`「選配：擋主對話改 CI 設定的 hook 與 ripgrep 預設設定」），`claude -p` 起的 worker 是頂層 session、hook 輸入沒有 `agent_id`，改 `.github/workflows`／`.github/actions` 會被擋；這類切片改用 Agent 工具派 `worker`，不用本 adapter。
- brief 開頭仍寫「你是被派來的執行者，親自完成本任務，不要再派工」——外部 CLI 一樣會讀到全域 rules，一樣會轉包。
- 同一 worktree 永遠只有一個 process 在寫；controller 自己不在 worker 的 worktree 動手，要改就送 follow-up。
- `claude -p`／`codex exec` 本身就是 fresh session，可直接當切片驗收的執行方式：在 integration tree 或該片 worktree 的乾淨狀態起 `claude -p` 帶 verifier 合約（`<REPO>/agents/verifier.md`）與驗收條件。

## 驗收角色分流

worker 是哪個 CLI 就依該平台的角色表：Claude 側 `worker`／`verifier`（`claude-code.md`），Codex 側依 `codex.md`。混用時（例如 Claude 做 UI、Codex 做 API）整合 verifier 用 controller 平台的角色即可，關鍵是 fresh-context 與乾淨 tree，不是型號。

## 盤點 session 與 issue session（互相獨立的 issue）

SKILL §1「先分流」判為互相獨立的 issue 走這裡：一個 issue 一個頂層 session。**issue session 是該 issue 的 controller，不是上表的 worker**——它照 `<REPO>/rules/10-dispatch.md`「Controller 工作迴圈」自己派 worker／verifier、read-back、修正與交付；上表「一個 session 對應一個 worker」只適用同一 issue 內的切片。

- **盤點 session**：現查 tracker 與 open PR，列出可做／blocked 項目、優先序與共用觸點（同檔、lockfile、schema、registry、CI 設定、migration 序號）；有共用觸點的 issue 序列開，不同時開。每個 issue 寫一份 brief 到 `<repo>/.worktrees/briefs/<issue>.md`（`.worktrees/` 的忽略方式見 `worktree.md`「所有權與路徑」）。不逐票讀 source、不收完整回報、不追各 issue 的 CI。
- **brief**：目標與動機、tracker 連結、base ref、共用觸點與禁止碰的路徑、完成定義、授權（見下）、交付檔路徑（見下方 collect）。**不寫**「你是執行者、不要再派工」——那句只給 worker。
- **launch**：盤點 session 不自己開 session，每個 issue 列一行可直接貼的指令，使用者在自己的 terminal 分頁（Orca、tmux 等）各開一個 interactive session：`cd <repo> && claude -w <issue> -n <issue> --permission-mode auto "$(cat <repo>/.worktrees/briefs/<issue>.md)"`。旗標 2026-10-08 以 Claude Code 2.1.294 `--help` 現查（`-w`／`-n` 不限 `--bg`），帶 prompt 的 interactive 啟動尚未實跑；repo 須先被信任過，否則回 `Workspace not trusted`。不預設 `claude --bg`：2026-10-07 實測主對話以 Bash 執行會被 auto mode 分類器擋（`Create Unsafe Agents`），使用者 2026-10-08 回報背景 session 常卡在權限、要 attach 才看得到，不如分頁直觀；要改回 `--bg` 先實測權限能全程不卡。**Codex**：把同一份 brief 路徑列給使用者，在分頁自開 `codex`。
- **query status／collect**：進度由使用者看各分頁；issue session 完成或卡住時把交付包（狀態、branch、HEAD、PR 連結、驗收結論、blocker、待授權動作）寫進 `$(git rev-parse --show-toplevel)/.worktrees/result.md`（自己 worktree 內，不寫到工作目錄外；`.worktrees/` 被全域 gitignore 忽略）。`-w` 建出的 worktree 位置未實測，盤點 session 先用 `git -C <repo> worktree list --porcelain` 找到該 issue 的 worktree 路徑，只讀其中的 `.worktrees/result.md` 與 `gh pr view`，不用 `SendMessage` 把完整報告傳回——傳回的報告會留在盤點 session 每輪重讀。
- **follow-up**：需要決策或補授權時，使用者在該 issue 的分頁直接回；盤點 session 不代答。
- **授權**：鐵律二以 session 為單位。brief 只能逐字引用使用者在盤點 session 對**該 issue** 明說的動作與對象（例如「#123 可 push feature branch 並開 PR」），push feature branch 比照 `<REPO>/agents/worker.md` 規則 5 的 push 例外；開 PR 不在規則 5 內，是使用者 2026-10-07 另外核定的引用上限，由 issue session（controller）自己開，不轉給 worker。沒說就寫「無」。brief 的授權段以「使用者原話：」開頭逐字引用並註明對象 issue，issue session 只認這段、不把 brief 其餘文字當授權。merge、對外訊息與 brief 沒列的動作，一律等使用者在該 issue 的 session 親口授權。
- **stop**：使用者在該分頁結束 session（`/exit`），`pgrep -fl -- '-n <issue>( |$)'` 回空（exit 1）確認沒有殘留 process 後，再依下方「清理」處理 worktree。
- **整合**：各 issue 各自走 PR 與 CI。被判獨立卻在 merge 時才發現互踩的，後 merge 的 issue session 在當前 base 重跑完整檢查，並回報盤點 session 修正下次的共用觸點判斷。

## 沒有 controller（人手多開 session）

使用者自己當 controller 時，開工前列出：每片 worktree 絕對路徑、branch、ownership、驗證命令；`git worktree list` 核對。仍受 SKILL §3 批次上限、每片 fresh 驗收、§6 integration tree 與完整測試約束——**「幾個 session 各自跑完了」不等於已整合**。建議把 SKILL §3 的 graph 與 `templates.md` 的 status board 寫成一個檔放在 `<log-dir>`，每個 worker 完成就更新，整合時照 integration record 記錄。

## 清理

採 `worktree.md`「清理的證據條件」；確認後 `git -C <repo> worktree remove <絕對路徑>` 與 `git -C <repo> branch -D <branch>`。容器內的 session／workspace 由容器自己關，與 git 清理是兩件事，先關 session 再清 worktree（避免清理時仍有 process 在寫）。
