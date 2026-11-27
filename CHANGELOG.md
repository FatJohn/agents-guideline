# Changelog

讀者：裝了這套制度的人（含維護者自己在其他機器），pull 之後想知道制度改了什麼、要不要動手。

只記行為變更：規則、skill、agent 合約、rubric、hook、使用者會執行的腳本、安裝步驟或設定片段，以及需要使用者動手的事。純措辭、量測報告、內部重構不記。按日期分段，新的在上；本 repo 沒有版本號。2026-11-26 開始記錄，之前的變更看 `git log`。

複本安裝（Windows、不能提權的機器）的每一筆都隱含同一個動作：pull 後重跑 `python scripts/sync-profile.py --apply --update`，下面不再逐筆重複。

## 2026-11-27

- **日落三條零效果規則**（#PR 待開）：`docs/dispatch.md` §4 卡住換路不再派 Fable＋`codex:codex-rescue` 各出方案，換路訊號成立就停下回報使用者並重新定義問題（附不變量與失敗軌跡，與 §2 三輪回報點同一種回報，不等第三輪），Codex `rules/dispatch.md` §5 同步；高風險判斷不再加 codex 第二意見，路由卡移除「獨立第二意見」，`codex:codex-rescue` 只在使用者當次要求時用；文件首輪 verifier brief 不再附「宣稱對照」表（handoff §1、Codex 驗收模板 J／L、judgment 6），製作者自己的逐句對照照舊。量測對照起點＝本 PR 的 merge 時間；下次看文件首輪 OPEN 率是否變化（基線：有帶 49%、沒帶 28%，整體約 30%），以及同根因換層有沒有沒被回報接住、拖到第三輪以上的案例。symlink 安裝 pull 後即生效，不用動手。
- **盤點 session 的監看改用背景 Bash**（#85）：`issue-status.py` 新增 `--exit-on-event`（搭配 `--watch`，印出 `delivered`／`error:` 那一輪後就結束）；`worktree-session` 的 `references/cli.md` 改成用 Bash `run_in_background` 跑它，不再用 `Monitor`，盤點 session 不會每 30 分鐘被到期叫醒重掛。正在掛 Monitor 監看的盤點 session：`TaskStop` 停掉後照新指令重掛一次。Codex 端不變。
- **usage-review 週量測報告固定格式**（#84）：`weekly` 的報告開頭改成計分卡（🟢 變好／🔴 變壞／⚪ 持平／🟡 待觀察，±5% 門檻）與規則表，每個 🔴 要有一列 finding（根因、落點、下次的判定門檻），之後才是結論與數字；格式在 `.claude/skills/usage-review/references/report-format.md`。repo-only skill，pull 後即生效，不用動手。
- **fresh `code-review` 寫明 skill 等級參數**（#83）：`docs/dispatch.md` §3 與路由卡規定派 fresh review 時 prompt 寫 `/code-review medium <目標>`，Opus（`effort: high`）與 Fable（`effort: medium`）都用 `medium`，不跟著 agent `effort` 調。量測對照起點＝本 PR 的 merge 時間（`gh pr view 83 -R FatJohn/agents-guideline --json mergedAt`）；之前的 review 成本混入了 `high` 等級參數這個變因。symlink 安裝 pull 後即生效，不用另外設定。

## 2026-11-26

- **新增本檔與記錄規則**（#82）：之後 PR 改到規則、skill、agent 合約、rubric、hook、使用者會執行的腳本、安裝步驟或設定片段，或 merge 後要使用者動手時，同一個 PR 要在這裡補一筆（門檻與時點見 `.claude/skills/maintain-guideline/SKILL.md` §2）。維護者照做即可，不用另外設定。
- **commit 閘門擋專案真名**（#80）：本 repo 加了 `.githooks/pre-commit`、`commit-msg`，staged 檔案或 commit message 含 repo 外名單裡的名字就擋下。要 commit 本 repo 的維護者：照 `docs/install.md`「本 repo 的 commit 閘門：擋專案真名」設 `core.hooksPath` 與名單路徑；沒設定的 clone 只印一行提示、照常放行。
- **派出去的 session 帶固定名稱**（#81）：issue session、接手、旁支、盤點 session 啟動時命名為 `issue-<issue>`、`takeover-<主題>`、`side-<brief 名>`、`inventory-<MMDD>`（Codex 端只給建議名稱，由使用者自己命名）；`require-issue-session-model.sh` 的 fallback 提示同步改成 `-n issue-<issue>`。symlink 安裝 pull 後即生效；在主 checkout 用 `claude --resume` 找 issue worktree 的 session 要按 `Ctrl+W`。
- **刪除 `v1` tag**（無 PR）：遠端已刪除，舊歷史含非公開專案名稱；`v3` tag 不受影響。新 clone 拿不到 `v1`（`git fetch origin tag v1` 會失敗），但既有 clone 的本機 `v1` 不會因 pull／fetch 消失：在其他機器的 clone 跑 `git tag -d v1`，清掉之前不要跑 `git push --tags`，否則會推回公開 repo。
