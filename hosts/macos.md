# 本機事實：主力 Mac（目前 hostname：`xushengzhedeMacBook-Pro.local`，arm64）

> 探測日：2026-07-14；2026-08-06 複查身分／版本／工具鏈。跨機器規則與 `<REPO>` 對照在 `../rules/05-hosts.md`，工具鏈明細在 `../docs/hosts-detail.md`。

- hostname 只作當場參考，不作跨重開機或改名後的唯一識別。
- 專案位置：`~/Projects/`（公司與個人混放）、個人專案集中在 `~/Projects/FatJohn/`
- 本系統 repo：`~/Projects/FatJohn/agents-guideline`，Claude Code symlink 裝進 `~/.claude/`；Codex `AGENTS.md` symlink 裝進 `~/.codex/`，agent TOML 由同步器裝成 `~/.codex/agents/` 實體檔
- 驗證能力：Flutter／.NET／Node 皆可本地跑；個人專案部署走 Zeabur
- **port 5000 被 macOS ControlCenter（AirPlay 接收器）佔在 `*:5000`**（2026-08-06 實測）：自己的服務綁 `localhost:5000` 仍可共存，但 `lsof -ti tcp:5000` 回的是 ControlCenter 的 PID —— 照著 kill 會殺到系統進程、自己的服務還活著，重啟後拿舊進程的回應當新版本的驗證。停服務用 `pkill -f <專案名>`，並以 `ps aux | grep <專案名>` 確認真的消失。
