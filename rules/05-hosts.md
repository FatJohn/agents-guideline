# 05 — 各機器事實（單機的事寫這裡，跨機器的結論寫 00）

> 多步驟任務開工前：`hostname` 認機器 → 找到對應段落沿用其事實；沒有段落就照 `../README.md`「新機器建檔（5 分鐘探測清單）」跑一輪，**自己把新段落補上**（本檔可直接寫入，不用問）。
> 事實看起來過時就抽查一兩項再用；工具「有沒有裝」永遠以 `command -v` 現查為準，清單只是加速。
> 各機器的**工具鏈與版本明細**（加速用快照）2026-09-06 搬到 `../docs/hosts-detail.md`，本檔只留身分、位置、驗證能力與陷阱。

## 主力 Mac（目前 hostname：`xushengzhedeMacBook-Pro.local`，arm64）

> 探測日：2026-07-14；2026-08-06 複查身分／版本／工具鏈

- hostname 只作當場參考，不作跨重開機或改名後的唯一識別。
- 專案位置：`~/Projects/`（公司與個人混放）、個人專案集中在 `~/Projects/FatJohn/`
- 本系統 repo：`~/Projects/FatJohn/agents-guideline`，Claude Code symlink 裝進 `~/.claude/`；Codex `AGENTS.md` symlink 裝進 `~/.codex/`，agent TOML 由同步器裝成 `~/.codex/agents/` 實體檔
- 驗證能力：Flutter／.NET／Node 皆可本地跑；個人專案部署走 Zeabur
- **port 5000 被 macOS ControlCenter（AirPlay 接收器）佔在 `*:5000`**（2026-08-06 實測）：自己的服務綁 `localhost:5000` 仍可共存，但 `lsof -ti tcp:5000` 回的是 ControlCenter 的 PID —— 照著 kill 會殺到系統進程、自己的服務還活著，重啟後拿舊進程的回應當新版本的驗證。停服務用 `pkill -f <專案名>`，並以 `ps aux | grep <專案名>` 確認真的消失。

## Windows 桌機（目前 hostname：`FatJohn-PC`，AMD64）

> 探測日：2026-08-05；2026-09-20 複查工具鏈與 symlink

- **`python3` 沒有別名，只有 `python`**——README 探測清單第 3 項的指令直接照抄會誤判 Python 未安裝
- 專案位置：個人專案放在 `E:\` 根層，不是 Mac 的 `~/Projects/FatJohn/`
- 本系統 repo：`E:\agents-guideline`。**目前全域設定是 `../scripts/sync-profile.py` 同步過去的實體檔複本**（2026-09-20 改的，`~/.claude`／`~/.codex`／`~/.agents` 三處；Codex agent TOML 另由 `sync-codex-agents.py` 管）。當時還不知道根因，所以繞過去；現在知道用 admin 裝 symlink 即可（見下），下次重建時改回去。
  - **改了 repo 不會自動生效**——symlink 版改完即時生效，複本版不會。動完 `rules/`、`rubrics/`、`skills/`、`agents/`、`CLAUDE.md`、`AGENTS.md` 要跑 `python scripts/sync-profile.py --apply --update`（加 `--prune` 清掉已 sunset 的舊項），否則你讀到的規則和跑起來的規則會不一樣。
  - **根因（2026-09-20 確認）：reparse point 的信任等級在「建立當下」由建立者的 token 決定**——非提權建的是 Level 1，啟用 RedirectionTrust 的行程一律拒絕走訪，回 `ERROR_UNTRUSTED_MOUNT_POINT`／os error 448；admin 建的是 Level 2，所有行程都讀得到。實測同一個目標檔：admin 建的連結非 admin 讀得到，自己建的同一條 448。
  - **所以正解是「用 admin 建連結」，不是改用複本。** 重裝或重建安裝時用 admin PowerShell 跑 README 的 symlink 版即可；複本版是不能提權時的備案。
  - `LinkType`／`Target`／`readlink` 查起來永遠全綠，只有真的開檔才會爆——**read-back 不能只驗連結存在，要實際讀內容**。
  - 同一個根因連帶：`node`／`npm`／`codex` 的 mise shim 全掛（要走 WinGet Links 的 `mise.exe`，那是 winget 非提權裝的 Level 1 連結）；Orca 把 `CODEX_HOME` 改指到自己的 runtime home，那裡的連結同樣是 Level 1，所以**從 Orca 啟動的 Codex 讀不到全域設定**（`~/.codex` 本身已修好）。
  - 複本安裝的副作用：`readlink ~/.claude/CLAUDE.md`／`~/.codex/AGENTS.md` 回空（已是實體檔）。要 `<REPO>` 看本段開頭那行。
- 驗證能力：.NET／Node／Flutter／Docker CLI 都在 PATH，但**本機尚未實跑過任何 build／test**；第一次要用來當完成證據前，先跑一次 `dotnet --info`／`flutter doctor` 確認 SDK 完整，不要憑 CLI 存在就宣稱可驗證。iOS build 不可（非 macOS）。
