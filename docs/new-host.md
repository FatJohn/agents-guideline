# 新機器建檔（5 分鐘探測清單）

> 這份清單只在裝新機器當下用得到，所以不放全域入口（每個 session 都會讀到）。
> 裝完照 `install.md` 走，含 SessionStart hook 登記（controller 路由卡靠它注入主對話）。

`global/shared/hosts/` 沒有這台機器的檔時，照這份跑一輪，然後**自己建檔**（下列檔都可直接寫入，不用問）——**探測結果分三處寫**：

- `global/shared/hosts/<key>.md`（常駐，但**每台機器只裝自己那份**）：標題以「# 本機事實：」開頭並寫 hostname；內容是機器身分、本系統 repo 位置、**驗證能力**、以及**陷阱**（不知道就會踩的那種，例如某 port 被系統佔用、`python3` 沒有別名）；專案路徑類事實不放這裡，由各專案自己的 `CLAUDE.md` 承接。然後照 `docs/install.md` 把它連／複製到 `~/.claude/host-facts.md`（`sync-profile.py` 要認得新 key 就在 `HOST_KEYS` 加一行）。
- `<REPO>/global/codex/AGENTS.md` 的 Bootstrap 段：`<REPO>` 對照加一行「hostname → repo 路徑 → `global/shared/hosts/<key>.md`」。Claude 入口不用加，它靠 `~/.claude/host-facts.md` 匯入與 readlink 取得 `<REPO>`。
- `docs/hosts-detail.md`（非常駐）：OS／shell／套件管理器版本、CLI 版本、工具盤點清單——這些是加速用快照，不佔每 session 的固定成本。

1. 身分：`hostname`＋OS（macOS 用 `sw_vers`；Windows 看 shell 環境是 PowerShell / Git Bash / WSL）
2. shell 與套件管理器（brew／winget／scoop）
3. 常用工具盤點：`for t in git gh node python3 flutter dotnet rg jq; do command -v $t; done`
   （PowerShell：`'git','gh','node','python','flutter','dotnet','rg','jq' | % { Get-Command $_ -EA SilentlyContinue }`；Windows 常無 `python3` 別名）
4. 這台機器能做哪些驗證：能不能跑 Flutter build？.NET build？（決定 `<REPO>/global/shared/rules/judgment.md` 第 1 條「完成的三個條件」在這台機器怎麼落地）
5. 記憶注意：內建持久記憶與 `.remember/` 都是本機的——機器綁定的事實要註明是哪台機器的

另外確認（不屬上面的探測清單）：全域 gitignore（`git config --global core.excludesFile` 指向的檔）含 `.worktrees/`（不帶開頭 `/`）、`**/.claude/worktrees/` 與 `.orca/` 三條；驗證 `git -C <任一 repo> check-ignore -v .worktrees/x`、`git -C <任一 repo> check-ignore -v .claude/worktrees/x` 與 `git -C <任一 repo> check-ignore -v .orca/x` 都要印出命中規則。理由見 `<REPO>/global/shared/skills/worktree-session/references/worktree.md`「所有權與路徑」。
