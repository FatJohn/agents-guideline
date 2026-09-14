# Adapter：外部 CLI process（純 shell、tmux、VS Code／Cursor terminal、Herdr、Orca、未來工具）

配合 [../SKILL.md](../SKILL.md) §9 的 adapter 契約使用。這一類環境的共同點：**每個 worker 是一個獨立的 coding agent CLI process**（`claude`、`codex` 或其他），controller 是另一個 session 或人。tmux、VS Code、Herdr、Orca 只是這些 process 的 terminal／session 容器；它們提供的 workspace、分頁、狀態面板都是 UX，不進 SKILL 的任何判斷。未來工具只要能做下表五件事，就照本檔用，不必改 SKILL。

| 契約項目 | 本 adapter 的做法 |
|---|---|
| launch agent | 在該片 worktree 目錄啟動 CLI，brief 從檔案餵入：`cd <wt> && claude -p "$(cat <brief>)"`／`codex exec "$(cat <brief>)"`，或互動模式貼 brief。旗標以當下 `--help` 現查，不憑記憶 |
| open session | 由容器決定：純 shell 開新 terminal；tmux 一 window 一 worker；VS Code 一 terminal 分頁一 worker；Herdr／Orca 一 workspace 一 worker。**一個 session 對應一個 worker，不對應一個 task**——task 可換 worker、worker 可換 session |
| create workspace | controller（或人）先以 `worktree.md`「所有權與路徑」的 `git worktree add` 建每片 worktree。Orca 等工具若能自動建 worktree，用它建出來的路徑即可，但仍要 `git worktree list` read-back 並記錄絕對路徑與 branch；不用它的 workspace model 代替 SKILL §3 的 graph |
| query status | 兩層：git read-back（`git -C <wt> status --short`、`rev-parse HEAD`、`diff --stat`）＋ worker report 落檔（brief 指定 `<log-dir>/<slice>-report.md`，`<log-dir>` 在 repo 外）。容器的「執行中／完成」指示燈只是線索，不是證據 |
| send follow-up | 用該 CLI 的 resume／continue 機制續同一 session（現查 `--help`），或在同一 worktree 起新 process 並把原 report、finding、diff 餵入 |

## 派工與 worktree

- worker **預設禁止** commit／rebase（同 `<REPO>/agents/worker.md` 規則 5）。要開放，brief 的 Execution environment 欄必須明寫「本任務在隔離 worktree（`isolation: worktree`）」這句——它是對 worker 合約的宣告，不是 CLI 旗標，外部 CLI 沒有這個參數——寫了才適用 worker 合約的隔離例外（可在自己 branch commit、完成前 rebase 一次、解純文字 conflict；push／PR／merge 仍禁止）；沒寫就是禁止。worker 若是 Codex，一律依 `codex.md`（不得 commit／rebase）。
- brief 開頭仍寫「你是被派來的執行者，親自完成本任務，不要再派工」——外部 CLI 一樣會讀到全域 rules，一樣會轉包。
- 同一 worktree 永遠只有一個 process 在寫；controller 自己不在 worker 的 worktree 動手，要改就送 follow-up。
- `claude -p`／`codex exec` 本身就是 fresh session，可直接當切片驗收的執行方式：在 integration tree 或該片 worktree 的乾淨狀態起 `claude -p` 帶 verifier 合約（`<REPO>/agents/verifier.md`）與驗收條件。

## 驗收角色分流

worker 是哪個 CLI 就依該平台的角色表：Claude 側 `worker`／`verifier`（`claude-code.md`），Codex 側依 `codex.md`。混用時（例如 Claude 做 UI、Codex 做 API）整合 verifier 用 controller 平台的角色即可，關鍵是 fresh-context 與乾淨 tree，不是型號。

## 沒有 controller（人手多開 session）

使用者自己當 controller 時，開工前列出：每片 worktree 絕對路徑、branch、ownership、驗證命令；`git worktree list` 核對。仍受 SKILL 的一批 3 片、每片 fresh 驗收、§6 integration tree 與完整測試約束——**「幾個 session 各自跑完了」不等於已整合**。建議把 SKILL §3 的 graph 與 `templates.md` 的 status board 寫成一個檔放在 `<log-dir>`，每個 worker 完成就更新，整合時照 integration record 記錄。

## 清理

採 `worktree.md`「清理的證據條件」；確認後 `git -C <repo> worktree remove <絕對路徑>` 與 `git -C <repo> branch -D <branch>`。容器內的 session／workspace 由容器自己關，與 git 清理是兩件事，先關 session 再清 worktree（避免清理時仍有 process 在寫）。
