# 05 — 各機器事實（單機的事寫這裡，跨機器的結論寫 00）

> 多步驟任務開工前：`hostname` 認機器 → 找到對應段落沿用其事實；沒有段落就照 `../README.md`「新機器建檔（5 分鐘探測清單）」跑一輪，**自己把新段落補上**（本檔可直接寫入，不用問）。
> 事實看起來過時就抽查一兩項再用；工具「有沒有裝」永遠以 `command -v` 現查為準，清單只是加速。

## 主力 Mac（目前 hostname：`xushengzhedeMacBook-Pro.local`，arm64）

> 探測日：2026-07-14；2026-08-06 複查身分／版本／工具鏈

- macOS 26.5.2（Build 25F84）、zsh（`/bin/zsh`）、Homebrew ✓（`/opt/homebrew/bin/brew`）
- Claude Code 2.1.258；Codex 0.152.0（2026-09-02 現查；版本會隨自動更新跳動，一律現查）
- 工具：git ✓、gh ✓、node ✓、python3 ✓、flutter ✓、dotnet ✓、rg ✓、jq ✓；fd ✗（找檔用 `rg --files` 或安裝 fd）
- hostname 只作當場參考，不作跨重開機或改名後的唯一識別。
- 專案位置：`~/Projects/`（公司與個人混放）、個人專案集中在 `~/Projects/FatJohn/`
- 本系統 repo：`~/Projects/FatJohn/agents-guideline`，Claude Code symlink 裝進 `~/.claude/`，Codex symlink 裝進 `~/.codex/`
- 驗證能力：Flutter／.NET／Node 皆可本地跑；個人專案部署走 Zeabur
- **port 5000 被 macOS ControlCenter（AirPlay 接收器）佔在 `*:5000`**（2026-08-06 實測）：自己的服務綁 `localhost:5000` 仍可共存，但 `lsof -ti tcp:5000` 回的是 ControlCenter 的 PID —— 照著 kill 會殺到系統進程、自己的服務還活著，重啟後拿舊進程的回應當新版本的驗證。停服務用 `pkill -f <專案名>`，並以 `ps aux | grep <專案名>` 確認真的消失。

## Windows 桌機（目前 hostname：`FatJohn-PC`，AMD64）

> 探測日：2026-08-05

- Windows 11 專業版（Build 26200）、PowerShell 7.6.4（`pwsh`，主要 shell）；Git Bash 與 WSL 皆可用（`bash`／`wsl` 都在 PATH）
- 套件管理器：winget ✓、mise ✓（node／npm／python／codex 都走 mise shim）；scoop ✗、Homebrew ✗
- Claude Code 2.1.222；Codex CLI 0.146.0（走 mise shim 會自動更新，同一天內就跳過版——版本號一律現查）
- Codex 本機 config 的主對話為 `gpt-5.6-sol`／effort `medium`（2026-08-06 00:14 現查 `~/.codex/config.toml`；與 Plus 制度預設一致）
- 工具：git ✓、gh ✓、node ✓、npm ✓、python ✓、flutter ✓（`D:\flutter\bin\flutter.bat`）、dotnet ✓、rg ✓、jq ✓、docker ✓、uv ✓；fd ✗、yarn ✗
- **`python3` 沒有別名，只有 `python`**——README 探測清單第 3 項的指令直接照抄會誤判 Python 未安裝
- 專案位置：個人專案放在 `E:\` 根層，不是 Mac 的 `~/Projects/FatJohn/`
- 本系統 repo：`E:\agents-guideline`（與 Mac 同一個 `git@github.com:FatJohn/agents-guideline.git`），Claude Code symlink 裝進 `~/.claude/`，Codex symlink 裝進 `~/.codex/`
- **symlink 安裝可行，不需要改用 `cp`**（2026-08-05 實測：跨磁碟 C: → E: 的檔案與目錄 symlink 都成功）；Developer Mode、registry key、junction 與 hardlink 的差異及安裝指令見 README「安裝（Windows／PowerShell）」。
  - **`~/.claude/rules` 用目錄 symlink，Claude Code 在 Windows 確實會自動全文載入**（2026-08-05 實測回傳 00／05／10／20／50 五個標題；驗法見 `20-judgment.md` §2 的 `claude -p --allowed-tools` 正例）。
- 驗證能力：.NET／Node／Flutter／Docker CLI 都在 PATH，但**本機尚未實跑過任何 build／test**（2026-08-05）；第一次要用來當完成證據前，先跑一次 `dotnet --info`／`flutter doctor` 確認 SDK 完整，不要憑 CLI 存在就宣稱可驗證。iOS build 不可（非 macOS）。
