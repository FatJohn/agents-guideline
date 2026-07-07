# 05 — 各機器事實（單機的事寫這裡，跨機器的結論寫 00）

> 多步驟任務開工前：`hostname` 認機器 → 找到對應段落沿用其事實；沒有段落就照下面的探測清單跑一輪，**自己把新段落補上**（本檔可直接寫入，不用問）。
> 事實看起來過時就抽查一兩項再用；工具「有沒有裝」永遠以 `command -v` 現查為準，清單只是加速。

## 探測清單（新機器 5 分鐘建檔）

1. 身分：`hostname`＋OS（macOS 用 `sw_vers`；Windows 看 shell 環境是 PowerShell / Git Bash / WSL）
2. shell 與套件管理器（brew／winget／scoop）
3. 常用工具盤點：`for t in git gh node python3 flutter dotnet rg jq; do command -v $t; done`
4. 這台機器能做哪些驗證：能不能跑 Flutter build？.NET build？（決定 `20-judgment.md` §2 在這台機器怎麼落地）
5. 記憶注意：內建持久記憶與 `.remember/` 都是本機的——機器綁定的事實要註明是哪台機器的

## xushengzhedeMacBook-Pro（macOS，主力開發機）

> 探測日：2026-07-06

- macOS 26.5.2、zsh、brew ✓
- 工具：node ✓、python3 ✓、flutter ✓、dotnet ✓、gh ✓、rg ✓、jq ✓；fd ✗（找檔用 `rg --files` 或裝 fd）
- 專案位置：`~/Projects/`（公司與個人混放）、個人專案集中在 `~/Projects/FatJohn/`
- 本系統 repo：`~/Projects/FatJohn/agents-guideline`，Claude Code symlink 裝進 `~/.claude/`，Codex symlink 裝進 `~/.codex/`
- 驗證能力：Flutter／.NET／Node 皆可本地跑；個人專案部署走 Zeabur

## Windows 桌機（尚未建檔）

> 第一次在那台機器用 Claude Code 跑多步驟任務時，照探測清單補上這段。
> 已知：存在一台 Windows 桌機（使用者口述，2026-07-06）；C#/.NET/WPF/UWP 開發推測在此進行。注意 Windows 上 `~/.claude/`／`~/.codex/` 的 symlink 安裝方式可能不同（mklink 或改用 cp），建檔時一併驗證並記錄。
