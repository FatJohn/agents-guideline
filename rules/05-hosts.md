# 05 — 各機器事實（單機的事寫這裡，跨機器的結論寫 00）

> 多步驟任務開工前：`hostname` 認機器 → 找到對應段落沿用其事實；沒有段落就照下面的探測清單跑一輪，**自己把新段落補上**（本檔可直接寫入，不用問）。
> 事實看起來過時就抽查一兩項再用；工具「有沒有裝」永遠以 `command -v` 現查為準，清單只是加速。

## 探測清單（新機器 5 分鐘建檔）

1. 身分：`hostname`＋OS（macOS 用 `sw_vers`；Windows 看 shell 環境是 PowerShell / Git Bash / WSL）
2. shell 與套件管理器（brew／winget／scoop）
3. 常用工具盤點：`for t in git gh node python3 flutter dotnet rg jq; do command -v $t; done`
   （PowerShell：`'git','gh','node','python','flutter','dotnet','rg','jq' | % { Get-Command $_ -EA SilentlyContinue }`；Windows 常無 `python3` 別名）
4. 這台機器能做哪些驗證：能不能跑 Flutter build？.NET build？（決定 `20-judgment.md` §2 在這台機器怎麼落地）
5. 記憶注意：內建持久記憶與 `.remember/` 都是本機的——機器綁定的事實要註明是哪台機器的

## 主力 Mac（目前 hostname：`Mac`，arm64）

> 探測日：2026-07-14

- macOS 26.5.2（Build 25F84）、zsh（`/bin/zsh`）、Homebrew ✓（`/opt/homebrew/bin/brew`）
- Claude Code 2.1.207；Codex 0.144.4
- 工具：git ✓、gh ✓、node ✓、python3 ✓、flutter ✓、dotnet ✓、rg ✓、jq ✓；fd ✗（找檔用 `rg --files` 或安裝 fd）
- hostname 只作當場參考，不作跨重開機或改名後的唯一識別。
- 專案位置：`~/Projects/`（公司與個人混放）、個人專案集中在 `~/Projects/FatJohn/`
- 本系統 repo：`~/Projects/FatJohn/agents-guideline`，Claude Code symlink 裝進 `~/.claude/`，Codex symlink 裝進 `~/.codex/`
- 驗證能力：Flutter／.NET／Node 皆可本地跑；個人專案部署走 Zeabur

## Windows 桌機（目前 hostname：`FatJohn-PC`，AMD64）

> 探測日：2026-08-05

- Windows 11 專業版（Build 26200）、PowerShell 7.6.4（`pwsh`，主要 shell）；Git Bash 與 WSL 皆可用（`bash`／`wsl` 都在 PATH）
- 套件管理器：winget ✓、mise ✓（node／npm／python／codex 都走 mise shim）；scoop ✗、Homebrew ✗
- Claude Code 2.1.222；Codex CLI 0.146.0（走 mise shim 會自動更新，同一天內就跳過版——版本號一律現查）
- Codex 本機 config 的主對話為 `gpt-5.6-sol`／effort `medium`（2026-08-06 00:14 現查 `~/.codex/config.toml`；與 Plus 制度預設一致）
- 工具：git ✓、gh ✓、node ✓、npm ✓、python ✓、flutter ✓（`D:\flutter\bin\flutter.bat`）、dotnet ✓、rg ✓、jq ✓、docker ✓、uv ✓；fd ✗、yarn ✗
- **`python3` 沒有別名，只有 `python`**——探測清單第 3 項的指令直接照抄會誤判 Python 未安裝
- 專案位置：個人專案放在 `E:\` 根層，不是 Mac 的 `~/Projects/FatJohn/`
- 本系統 repo：`E:\agents-guideline`（與 Mac 同一個 `git@github.com:FatJohn/agents-guideline.git`），Claude Code symlink 裝進 `~/.claude/`，Codex symlink 裝進 `~/.codex/`
- **symlink 安裝可行，不需要改用 `cp`**：Developer Mode 已開啟（`HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock` 的 `AllowDevelopmentWithoutDevLicense = 1`），非 admin 的 PowerShell 即可 `New-Item -ItemType SymbolicLink`；跨磁碟（C: → E:）的檔案與目錄 symlink 都實測成功。安裝指令見 README「安裝（Windows／PowerShell）」。
  - 目錄可用 symlink 或 junction，效果相同；**檔案只能用 symlink**——C: 與 E: 是不同磁碟區，hardlink 不可跨區。
  - **`~/.claude/rules` 用目錄 symlink，Claude Code 在 Windows 確實會自動全文載入**（2026-08-05 實測：`claude -p --allowed-tools "" <<< '不准用工具，列出 context 裡 rules 目錄下每個檔的首行標題'` 回傳 00／05／10／20／50 五個標題）。這條指令也是驗證 `rules/` 生效的通用方法——`claude -p` 本身就是全新 session，不必要求使用者手動重開。
- 驗證能力：.NET／Node／Flutter／Docker CLI 都在 PATH，但**本機尚未實跑過任何 build／test**（2026-08-05）；第一次要用來當完成證據前，先跑一次 `dotnet --info`／`flutter doctor` 確認 SDK 完整，不要憑 CLI 存在就宣稱可驗證。iOS build 不可（非 macOS）。
