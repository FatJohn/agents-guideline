# ADE 容器調查 2026-11-07：Orca 近況、Herdr 評估、搬移成本

> 讀者：要決定 issue session 的容器要不要換、或要把新容器接進 worktree-session skill 的人。契約本身在 `global/shared/skills/worktree-session/references/container.md`，本頁只放調查結果與決定。

## 起因

使用者對 Orca 的兩個不滿：workspace 沒辦法分群觀看；盤點 session 看不到派出去的 issue session 在做什麼。另外看到 Herdr 有 pane 與 mod 生態，問值不值得換。

## Orca 現況（本機 1.4.251，官方 changelog 到 1.4.252）

| 版本（日期） | 與本系統有關的項目 |
|---|---|
| 1.4.252（11-07） | folder workspace 底下可巢狀其他 workspace（含跨機器）；聊天可從任一回應 fork；`/plan` 進 Plan mode；需 macOS 13.4+ |
| 1.4.251（11-06） | 巢狀 worker 預設開（深度 4），停 worker 連帶停 helper；全部 project 一鍵收合；右鍵建 child worktree；terminal 在 daemon 重連後自動重接 |
| 1.4.248（11-04） | commit message／PR 描述／branch 名各自可選 model 與 effort；可設更新延遲天數；Orchestration panel 以 experimental opt-in 回歸 |
| 1.4.245（10-30） | plugin 系統（需同意）；worker 可訂 `agent.status.changed`（working／blocked／waiting／done 含 outcome）與 `workspace.created/removed`，可畫 sidebar panel 與 status bar item |
| 1.4.242（10-27） | shared skills 安裝／更新；Claude subagent 顯示在 sidebar |
| 1.4.226（10-15） | folder workspace 進 ⌘J palette |

本機實跑（2026-11-07）：

- `orca worktree create --repo path:<repo> --name <n> --base-branch origin/main --parent-worktree path:<repo> --json` 回 `parentWorktreeId` 等於主 checkout 的 worktree id，sidebar 會縮在「N children」chip 下；只影響 sidebar，git 不變。
- `orca worktree ps --json --agent-wait --limit 10`：每個 worktree 一筆，含 `workspaceStatus`、`unread`、`liveTerminalCount`、`terminalVerdict`，每個 agent 有 `state`、`agentType`、`programStatus.message`（agent 自報的一句）與完整 `lastAssistantMessage`；`agentWait` 這次全為 null。原始 JSON 很大，要經 jq 壓成一行一 worktree 再讀。
- `orca worktree set --worktree path:<wt> --workspace-status in-review --unread --json` 回 `workspaceStatus: in-review`、`isUnread: true`；改回 `in-progress --read` 亦可。

結論：兩個不滿都有現成解法。分群用 `--parent-worktree`（issue session 縮在 repo 主 workspace 下）或 1.4.252 的 folder workspace 巢狀；觀測用 `worktree ps --json` 加 Agents feed／Agent Dashboard。細節已寫進 cli.md。

## Herdr（desktop app 與 TUI）

- 兩個產品：TUI（brew `herdr` 0.9.5）與 desktop app（`herdr-app`，跑在 `herdr-core` 上，關窗 agent 不死，但重開機或停 core 就沒了，不 resume）。Apache 2.0，免費；macOS Apple silicon、Linux、Windows；SSH 遠端機器進同一個 sidebar。
- **主動起 session**：可以，但要兩步以上。`herdr workspace create --cwd` 拿 root pane，`herdr pane split`，`herdr agent start <name> --kind claude --pane <id>`（等到 agent ready 才回，30 秒預設逾時），`herdr agent prompt <name> "<text>" --wait --until blocked`，`herdr agent read`。對照 Orca 一條 `worktree create --agent`。
- **worktree 與分群**：`herdr worktree create --branch --base` 建 checkout、開成 workspace 並群組在來源 workspace 下；11 月 changelog 補了 sidebar 拖曳排序與 group 修正。沒有 Orca 的 project→worktree→child 三層與看板。
- **觀測**：agent sidebar 跨 space 收集所有 agent（含別的 agent 開的 worker），狀態靠 OSC 7501 協定；`herdr agent list`／`wait --until`。已知 issue #488：Claude Code pane 曾顯示成普通 terminal，更新 Claude Code 後才好。
- **mod**：`~/.config/herdr-app/mods/` 的 JavaScript，trusted 不沙箱，照它的 AGENTS.md 讓 agent 寫；內建的啟動會被覆蓋，改之前先複製。gallery 裡對「整體觀測」有用的：Mission Control（agents／sessions／spaces／tabs 加 GitHub／Jira／GitLab 面板）、Quests（每個 finished turn 自動摘要「要求了什麼、做了什麼、機器驗了什麼、還要人確認什麼」成可勾選看板，靠 omp extension 跑，每 session 五分鐘一次、1200 token 上限）、Kanban、Agent folders、Auto tabs、Prompt Queue、Agent Quota。遊戲角色類（Herdr Zoo、Pokémon Workers、Maid Café ADV）只是狀態的另一種呈現。
- **沒有的**：Jira／Linear 內建、手機 app、automations、per-workspace 環境 recipe、coordinator mailbox／decision gate。

## 決定

不換。理由：兩個不滿在 Orca 現版已可解；本系統綁 Orca 的只有 cli.md 的指令段、`require-issue-session-model.sh` 的指令比對、`worktree.md` 的 `.orca/` 忽略條目與 hosts 事實，三支腳本與 SKILL 流程都不綁。為了讓下次換容器只動那幾個檔，把「五個動作」寫成 `references/container.md` 的契約，並把 Herdr 的對應指令先列在表裡（標未實跑）。

Quests 那種「每輪結束的待確認看板」如果之後想要，Orca plugin 訂 `agent.status.changed` 就能做，不必換平台；`result.md` 的 `Pending authorization` 欄已經是它的資料來源。

## 來源

Orca changelog（onorca.dev/changelog）、stablyai/orca GitHub releases、Orca docs（worktrees、activity、agents-sessions）、herdr.dev 首頁與 TUI CLI reference、herdrdev/herdr-app README 與 issue #488、herdrdev/herdr CHANGELOG、herdr.dev/mods gallery、AlanWanco/herdr-app-mod-quests。
