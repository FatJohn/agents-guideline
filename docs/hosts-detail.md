# 各機器工具鏈與版本明細（探測快照）

> 2026-09-06 從 `rules/05-hosts.md` 搬出。理由：這些是**加速用的快照**——該檔自己規定「工具『有沒有裝』永遠以 `command -v` 現查為準，清單只是加速」，而 `rules/` 是每個 session 全文載入的常駐區（`skills/maintain-guideline/SKILL.md` §5「只在特定情境才用得到的內容不該放 rules/」）。內容原文未改寫。
> 常駐區（`rules/05-hosts.md`）留的是機器身分、專案位置、驗證能力與**陷阱**——陷阱是「不知道就會踩」，不能搬。
> 開工前要引用工具是否存在時讀這份；版本號一律現查，不要引用本檔的數字。

## 主力 Mac（hostname：`xushengzhedeMacBook-Pro.local`，arm64）

> 探測日：2026-07-14；2026-08-06 複查身分／版本／工具鏈

- macOS 26.5.2（Build 25F84）、zsh（`/bin/zsh`）、Homebrew ✓（`/opt/homebrew/bin/brew`）
- Claude Code 2.1.258；Codex 0.152.0（2026-09-02 現查；版本會隨自動更新跳動，一律現查）
- 工具：git ✓、gh ✓、node ✓、python3 ✓、flutter ✓、dotnet ✓、rg ✓、jq ✓；fd ✗（找檔用 `rg --files` 或安裝 fd）

## Windows 桌機（hostname：`FatJohn-PC`，AMD64）

> 探測日：2026-08-05

- Windows 11 專業版（Build 26200）、PowerShell 7.6.4（`pwsh`，主要 shell）；Git Bash 與 WSL 皆可用（`bash`／`wsl` 都在 PATH）
- 套件管理器：winget ✓、mise ✓（node／npm／python／codex 都走 mise shim）；scoop ✗、Homebrew ✗
- Claude Code 2.1.222；Codex CLI 0.146.0（走 mise shim 會自動更新，同一天內就跳過版——版本號一律現查）
- Codex 本機 config 的主對話為 `gpt-5.6-sol`／effort `medium`（2026-08-06 00:14 現查 `~/.codex/config.toml`；與 Plus 制度預設一致）
- 工具：git ✓、gh ✓、node ✓、npm ✓、python ✓、flutter ✓（`D:\flutter\bin\flutter.bat`）、dotnet ✓、rg ✓、jq ✓、docker ✓、uv ✓；fd ✗、yarn ✗
- **symlink／rules 載入探測**：跨磁碟 C: → E: 的檔案與目錄連結建立成功，Codex agent 現採實體同步；Windows named runtime 待實測，指令見 README「安裝（Windows／PowerShell）」。`~/.claude/rules` 目錄 symlink 實測回傳 00／05／10／20／50 五個標題；驗法見 `rules/20-judgment.md` §2 的 `claude -p --allowed-tools` 正例。
