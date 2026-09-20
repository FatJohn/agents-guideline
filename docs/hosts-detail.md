# 各機器工具鏈與版本明細（探測快照）

> 2026-09-06 從 `rules/05-hosts.md` 搬出。理由：這些是**加速用的快照**——該檔自己規定「工具『有沒有裝』永遠以 `command -v` 現查為準，清單只是加速」，而 `rules/` 是每個 session 全文載入的常駐區（`skills/maintain-guideline/SKILL.md` §5「只在特定情境才用得到的內容不該放 rules/」）。內容原文未改寫。
> 常駐區（`rules/05-hosts.md`）留的是機器身分、專案位置、驗證能力與**陷阱**——陷阱是「不知道就會踩」，不能搬。
> 開工前要引用工具是否存在時讀這份；版本號一律現查，不要引用本檔的數字。

## 主力 Mac（hostname：`xushengzhedeMacBook-Pro.local`，arm64）

> 探測日：2026-07-14；2026-08-06 複查身分／版本／工具鏈

- macOS 26.5.2（Build 25F84）、zsh（`/bin/zsh`）、Homebrew ✓（`/opt/homebrew/bin/brew`）
- Claude Code 2.1.258；Codex 0.152.0（2026-09-02 現查；版本會隨自動更新跳動，一律現查）
- 工具：git ✓、gh ✓、node ✓、python3 ✓、flutter ✓、dotnet ✓、rg ✓、jq ✓；fd ✗（找檔用 `rg --files` 或安裝 fd）
- **安裝來源原則（2026-09-20 現查）：只有 node／npm 走 mise**（`~/.config/mise/config.toml` 只列 `node`，全域預設 26；已開 `idiomatic_version_file_enable_tools = ["node"]`，專案的 `.nvmrc`／`.node-version` 會自動生效——不開的話 mise 會靜默忽略這些檔、一律用全域版本），其餘一律官方安裝——go（`/usr/local/go/bin/go`，官方 pkg）、python3（python.org framework，`/Library/Frameworks/Python.framework`）、bun（`~/.bun/bin`）、pnpm（standalone，`~/Library/pnpm/bin`）、dotnet、flutter。Homebrew 不裝語言 runtime；uv／corepack 未安裝。要新增語言工具時照此原則，不要順手 `mise use` 或 `brew install`。

## Windows 桌機（hostname：`FatJohn-PC`，AMD64）

> 探測日：2026-08-05；2026-09-20 複查工具鏈、安裝來源與 symlink

- Windows 11 專業版（Build 26200）、PowerShell 7.6.6（`pwsh`，主要 shell）；Git Bash 與 WSL 皆可用（`bash`／`wsl` 都在 PATH）
- 套件管理器：winget ✓、mise ✓（2026-09-20 `mise ls` 現查**只有 node 一項**）；scoop ✗、Homebrew ✗
- **安裝來源原則與 Mac 相同**（2026-09-20 現查確認）：只有 node／npm 走 mise（`~/.config/mise/config.toml` 列 `node = "26"`，實裝 26.9.0；2026-09-20 已補上 `idiomatic_version_file_enable_tools = ["node"]`，與 Mac 一致），其餘官方安裝——python（`~\AppData\Local\Programs\Python\Python314`）、go（`C:\Program Files\Go`）、dotnet、flutter（`D:\flutter`）、bun（`~\.bun\bin`）、pnpm、uv（`~\.local\bin`）、codex（pnpm 全域）。2026-08-05 那筆「python／codex 也走 mise shim」的快照已不成立。
- Claude Code 2.1.278（`~\.local\bin\claude.exe`，原生執行檔）；Codex CLI 有三份，**版本與路徑不要憑印象配對**——pnpm 全域 `codex.ps1`（走 node，目前因下方 symlink 問題無法啟動）、`~\AppData\Local\OpenAI\Codex\bin\codex.exe` 是 **0.130.0-alpha.5**、真正較新的 0.142.5 在巢狀 hash 目錄 `~\AppData\Local\OpenAI\Codex\bin\ea1c60319a1dcb19\codex.exe`。版本號一律現查。
- Codex 本機 config 的主對話為 `gpt-5.6-sol`／effort `medium`（2026-08-06 00:14 現查 `~/.codex/config.toml`；與 Plus 制度預設一致）。**注意**：桌面版自帶的 0.142.5 會拒絕這個 model（`requires a newer version of Codex`），要用 CLI 得先修好 node。
- 工具：git ✓、gh ✓、node ✓、npm ✓、python ✓、go ✓、pnpm ✓、bun ✓、flutter ✓（`D:\flutter\bin\flutter.bat`）、dotnet ✓、rg ✓、jq ✓、docker ✓、uv ✓；fd ✗、yarn ✗、`python3` ✗（只有 `python`）
- **symlink／rules 載入探測（2026-09-20 重驗，結論與 2026-08-05 相反）**：本機**開啟非提權建立的** reparse point 背後的檔案一律失敗，錯誤是 `ERROR_UNTRUSTED_MOUNT_POINT`（os error 448）。**「非提權建立的」這個限定詞很重要**——下面的矩陣是在知道根因之前跑的，當時機器上所有連結剛好都是非提權建的，所以看起來像全面失效；admin 建的連結不受影響（見下方決定性實驗）。
  - 實測矩陣（目錄 symlink 與 junction、C:→C: 與 C:→E:、新建與 2026-08-05 舊建，**全部都是非提權建立**）：**開檔一律失敗**。唯一的例外是 **Git Bash（MSYS）自行解析 reparse data**——它既讀得到檔案 symlink（`head -1 ~/.claude/CLAUDE.md` 成功），也列得出目錄 symlink 的內容（`ls ~/.claude/rules` 回五個檔名），但 `cat ~/.claude/rules/00-environment.md` 仍然 Permission denied。
  - **Node、Claude Code 自己的 Read 工具、PowerShell 7、Rust 寫的 Codex 全部開不了檔案 symlink**：`Read("C:\Users\FatJohn\.claude\CLAUDE.md")` → `EUNKNOWN`；實體 `node.exe` 對同一路徑 `open` → `UNKNOWN -4094`（只有 `lstat`／`readlink` 過得去，所以 `LinkType`／`Target` 查起來全綠）。**連全域 `~/.claude/CLAUDE.md` 都沒有載入**——cwd 在本 repo 時 context 裡那份 `CLAUDE.md` 是以「專案 CLAUDE.md」身分進來的，很容易被誤判成全域那份生效了。
  - 當時的後果（**已由下方 2026-09-20 修復解除，保留為證據**）：`~/.claude/rules`／`rubrics`／`skills/*` 與 `~/.agents/skills/*` 對 Claude Code 等同不存在——fresh `claude -p --allowed-tools ""` 問 context 裡有哪些 rules 檔，回「一個都沒有」；repo 提供的 `maintain-guideline`／`create-pr` 也不在 skill 清單裡，而實體目錄的 `fatjohn-writing-style` 有出現，正好是對照組。Codex 則是 `failed to read global AGENTS.md ... (os error 448)`。
  - **仍然成立的**：`node`／`npm`／`codex` 的 mise shim 全掛，因為 shim 要經 `~\AppData\Local\Microsoft\WinGet\Links\mise.exe` 這個 symlink 找 mise；codex plugin 的 `session-lifecycle-hook.mjs` 走 node，因此每個 session 結束都會看到 mise-shim 失敗訊息（**不是** remember plugin，它的 SessionEnd 是純 bash、實跑 rc=0）。
  - **當時 `worker`／`verifier` 都派不出來，原因不同**（兩者皆已修復，現在可正常派工）：`~/.claude/agents/` **根本沒有 `worker.md`**（從未安裝），另有 4 條指向已 sunset 檔案的 stale symlink（`escalation-planner`／`escalation-worker`／`fable-verifier`／`recovery-worker`，repo 在 commit `4465de6` 已刪）；`verifier.md` 有裝但是 symlink，開不了。前者與 reparse point 無關，補裝實體檔即可。
  - **根因（2026-09-20 實測確認，不是推測）**：reparse point 建立時，系統以建立者的 token 算出信任等級並蓋在上面（`nt!IoComputeRedirectionTrustLevel`）——medium integrity 的一般使用者是 **Level 1（不受信任）**，admin／SYSTEM／kernel 是 Level 2。啟用 `ProcessRedirectionTrustPolicy` 的行程走訪 Level 1 就回 448。
    - **決定性實驗**：請使用者用 admin PowerShell 建一條指向 `~/.claude/rules/00-environment.md` 的檔案 symlink，再由**非 admin** 的行程讀。結果：admin 建的那條，PowerShell 與 Claude Code 的 Read 工具都讀得到全文；同一時間自己（非 admin）建的、指向同一個目標的對照組則是 448。等級由建立者決定，與讀取者無關。
    - 先前排除掉的（都不是原因）：`fsutil behavior query SymlinkEvaluation` 的 L2L／L2R 都啟用；E: 是一般 NTFS 固定磁碟（`fsutil devdrv query E:` 回 not a developer volume）；跨磁碟與否無關（C:→C: 一樣失敗）；也不是 Claude Code 行程樹的問題（用 WMI 生一個父行程是 `WmiPrvSE.exe` 的 pwsh，結果相同）。時間上最接近的變動是 2026-09-14～18 安裝的 KB5124007／KB5126052／KB5129195，推測是那批把 enforcement 從 audit 打開。
  - **修復方向（已更新）**：正解是**用 admin 建立連結**，symlink 安裝即可照常運作，repo 改完也即時生效。實體檔同步是**不能提權時的備案**——真實目錄 `.claude/rules/` 裡放實體檔會被載入、放檔案 symlink 不會（兩者都用 `claude -p` 驗過），而檔案 symlink 不被載入已由開檔失敗解釋，不需要另外假設載入器會略過 symlink。
  - **2026-09-20 已修復（改實體檔複本，OS 層的 448 仍在）**：`scripts/sync-profile.py --prune --apply` 把 `CLAUDE.md`／`rules/`／`rubrics/`／`agents/`／三個共用 skill 與 `AGENTS.md`／`session-handoff` 寫成實體檔（26 install、3 檔案 symlink 轉檔、7 目錄 symlink 轉實體目錄、6 條 stale link 清除，read-back 29 檔逐 byte 相符），`sync-codex-agents.py --apply` 把 11 個 agent TOML 轉成實體檔。從 repo 以外的目錄跑 fresh `claude -p` 驗證：五份 `rules/` 標題、全域 CLAUDE.md 的三條鐵律、`worker`／`verifier` 可派工，全部回來了。
    - **代價一：改 repo 不再即時生效**，要重跑 `--apply --update`。這條寫在 `rules/05-hosts.md`。
    - **代價二：`readlink ~/.claude/CLAUDE.md`／`~/.codex/AGENTS.md` 回空**（exit 1），因為它們已是實體檔。本系統原本用這個當取得 `<REPO>` 的 canonical 做法，共四處（`CLAUDE.md`、`AGENTS.md`、`codex/rules/10-dispatch-codex.md`、`skills/maintain-guideline/SKILL.md`）；已改成「先查 `rules/05-hosts.md` 的機器段落，readlink 只當 symlink 機器的 fallback」。**這是驗收抓到的，不是同步時想到的**——改安裝形狀會連帶打斷所有依賴該形狀的指令。
    - 同一輪順手修掉 `sync-codex-agents.py` 的 `resolve(strict=True)`——它會開啟 symlink 目標，在本機直接爆，所以那支腳本原本**根本跑不動**（既有的 `tests/test_sync_codex_agents.py` 在本機本來就是紅的）。兩支腳本現在都用 `os.readlink` 比對，不走訪。`os.readlink` 在 Windows 回的是 `\\?\` 擴充長度前綴，不剝掉就沒有任何連結會被認出是自己裝的（測試抓到的）。
    - **仍未修**：`node`／`npm`／`codex` 的 mise shim；以及 Orca 把 `CODEX_HOME` 改指到 `~\AppData\Roaming\orca\codex-runtime-home\home`，那裡的 `AGENTS.md` 是指回 `~/.codex` 的 symlink、`skills`／`plugins`／`prompts` 是指回 `~/.codex` 的 junction，所以從 Orca 啟動的 Codex 仍是 448。直接用 `CODEX_HOME=~/.codex` 啟動則不再出現該 warning。那是 Orca 自己的目錄，沒有動它。
  - 驗法見 `rules/20-judgment.md` §2 的 `claude -p --allowed-tools` 正例；**在本機要驗「裝好了沒」一律實際讀檔，不能只查 `LinkType`**。Windows named runtime 仍待實測，指令見 README「安裝（Windows／PowerShell）」。
