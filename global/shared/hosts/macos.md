# 本機事實：主力 Mac（hostname：`xushengzhedeMacBook-Pro.local`，arm64）

探測日：2026-08-06

- `<REPO>` 是 `~/Projects/FatJohn/agents-guideline`，symlink 安裝，改 repo 即時生效；只有 Codex agent TOML 是同步器裝的實體檔（`~/.codex/agents/`）。
- 驗證能力：Flutter、.NET、Node 皆可本地跑。
- **port 5000 被 macOS ControlCenter（AirPlay 接收器）佔在 `*:5000`**：自己的服務綁 `localhost:5000` 可共存，但 `lsof -ti tcp:5000` 回的是 ControlCenter 的 PID，照著 kill 殺到的是系統進程，自己的舊服務還活著，會拿舊進程的回應當新版驗證。停服務用 `pkill -f <專案名>`，再 `ps aux | grep <專案名>` 確認消失。
- Orca（CLI `orca`）已裝：`orca worktree create --agent claude` 可由主對話 Bash 執行、不被 auto mode 擋。tmux 未裝（`command -v tmux` 空）；`/Applications/iTerm.app` 存在，`claude --help` 說 `--tmux` 有 iTerm2 時用原生 pane，`claude -w --tmux` 未實跑。
