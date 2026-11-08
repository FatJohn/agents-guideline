# 容器契約：盤點 session 對 ADE／terminal 容器只要五個動作

配合 [../SKILL.md](../SKILL.md) §2「多個 issue：一 issue 一頂層 session」與 [cli.md](cli.md) 使用。本頁是「不綁死在某個 ADE」的那一層：定義容器要提供什麼、什麼東西不隨容器變、換容器時要動哪幾個檔。Orca、Herdr、tmux、iTerm 分頁、VS Code 分頁都是容器；判斷永遠只讀 git、gh、`result.md` 與本 repo 的腳本，容器的面板、狀態燈、看板、mod 都只是線索。

## 不隨容器變的東西

- **單位**：issue session 是一個獨立的 coding agent CLI process（`claude` 或 `codex`），在自己的 worktree 裡當該 issue 的 controller。容器負責把固定的 argv 起起來並把 brief 送進 session（Claude：`claude --model claude-opus-5-5 --effort medium`，值的政策在 cli.md「盤點 session 與 issue session」；brief 可以在 argv 尾端，也可以在 session 起來後送進 terminal，送到沒有以 cli.md「launch」的 read-back 判定），其餘不管。
- **交接檔**：brief 在 `<repo>/.worktrees/briefs/<issue>.md`，result 在 `<wt>/.worktrees/result.md`，欄位依 SKILL §2；兩者都是純檔案，任何容器、任何 agent 都讀得到。
- **worktree 由 git 管**：容器建的 worktree 必須出現在 `git -C <repo> worktree list --porcelain`，位置與忽略方式依 `worktree.md`「所有權與路徑」；清理條件依 `worktree.md`「清理的證據條件」，直接清的閘門是 `<REPO>/scripts/worktree-clean-check.py`。
- **三支腳本只讀 git、gh、process 與 session jsonl**：`issue-status.py`（進度板）、`stall-check.py`（Claude session 在做什麼）、`worktree-clean-check.py`（能不能清）。容器資訊只能當可選加值（`issue-status.py` 讀 `orca worktree list` 補 linkedIssue，orca 不在就略過），不能是判定輸入。
- **狀態推進只靠 `result.md` 與 `gh pr view`**：容器回報的 idle／done／blocked、pane 顏色、看板欄位都不對應 SKILL §2 的任何 `Status`。

## 五個動作與各容器對照

| 動作 | 要求 | Orca（已實跑，指令在 cli.md） | 純 shell／分頁（cli.md「Fallback」） | Herdr desktop app（候選，未實跑；依 2026-11-07 官方 CLI 文件，見 `<REPO>/docs/reviews/ade-survey-2026-11-07.md`） |
|---|---|---|---|---|
| **launch** | 在指定 repo、指定 base ref 建 worktree，以固定 argv 起 agent 並送達 brief，回 worktree 絕對路徑與 branch | `orca worktree create --repo path:<repo> --base-branch <ref> --agent claude --model … --effort … --prompt …` | `claude -w <issue> -n <issue> --model … --effort … "<brief>"` | `herdr worktree create --cwd <repo> --branch <b> --base <ref>` → `herdr pane split`／root pane → `herdr agent start <issue> --kind claude --pane <id> -- --model … --effort …` → `herdr agent prompt <issue> "<brief>"` |
| **locate** | 由 issue 名找 worktree 絕對路徑與 branch | `orca worktree list --json`（`path`／`branch`／`displayName`） | `git -C <repo> worktree list --porcelain` | `herdr worktree list --cwd <repo>` 或 git |
| **overview** | 一眼看全部 session 在跑、等人、還是靜默，只當線索 | `orca worktree ps --json --agent-wait` 經 jq 壓成一行一 worktree | `python3 <REPO>/scripts/stall-check.py` | `herdr agent list`（working／blocked／done／idle）、`herdr agent wait <n> --until blocked` |
| **stop** | 關該 worktree 的 session 與 terminal，read-back 該 worktree 內無 agent process | `orca terminal close --worktree path:<wt> --all --json` ＋ cli.md「stop」的 pgrep／lsof 迴圈 | 使用者在分頁 `/exit`；`pgrep -fl -- '-n <issue>( |$)'` 回空 | `herdr workspace close <id> --group` ＋ 同一個 pgrep／lsof 迴圈 |
| **rm** | 刪 worktree 與 branch，git 判定在先 | `orca worktree rm --worktree path:<wt> --delete-branch --json` | `git -C <repo> worktree remove <wt>`＋`git -C <repo> branch -D <b>` | `herdr worktree remove --workspace <id>`（文件說不刪 branch，branch 另用 git） |

不在表內的都不是契約的一部分：Orca 的 `--parent-worktree` 分組、看板欄位、Agents feed、Herdr 的 mod 與 pane 狀態燈，用了可以更好看，沒有也不影響任何判定。

## 換容器要動的檔（清單）

1. `cli.md`：加一節新容器的 launch／locate／overview／stop／rm 實跑指令，表格裡的「未實跑」改成實跑日期與輸出摘要；舊容器那節保留直到該機器不再裝它。
2. `<REPO>/global/claude/hooks/require-issue-session-model.sh` 與 `<REPO>/tests/test-require-issue-session-model.sh`：hook 比對的是 launch 指令樣式（目前 `orca worktree create`／`orca agent launch` 帶 `--agent claude`），新容器的 launch 指令要加進比對並補測試，否則缺 `--model`／`--effort` 的啟動不會被擋。
3. `worktree.md`「所有權與路徑」：新容器建的 worktree 位置與全域 gitignore 條目（Orca 是 `.orca/`），`check-ignore -v` 驗一次。
4. `<REPO>/global/shared/hosts/<key>.md`：該機器裝了什麼、哪些指令實跑過、auto mode 會不會擋。
5. 可選：`issue-status.py` 的容器加值欄位。

不用動：SKILL.md 的流程、brief／result 格式、三支腳本的判定邏輯、judgment、dispatch、route card。搬完的判定：對同一批 issue worktree，換容器前後各跑一次 `issue-status.py`，每個 issue 的 `Status` 欄相同（名稱後的 `(#N)` 是 Orca 加值欄、worktree 路徑隨容器的位置變，兩者本來就會不同，不比）；對一個已交付的 worktree 各跑一次 `worktree-clean-check.py`，exit code 與列出的原因相同。

## 評估新容器時看什麼

依序問：能不能用一條指令在指定 repo／base ref 建 worktree 並以指定 argv 起 agent；建出來的 worktree 在不在 `git worktree list`；能不能從 CLI 關 session 並 read-back；清理會不會動 branch；以及它的狀態面板要不要我們寫入（要寫入就是多一個同步點，不寫入就只是看）。候選的調查結果與結論寫 `<REPO>/docs/reviews/ade-survey-<日期>.md`，不寫進本頁。
