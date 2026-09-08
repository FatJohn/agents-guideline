# Codex named agent：0.153.4 本機診斷

以下是 2026-09-08 的本機觀察，描述目前 desktop／CLI surface 的結果，不是上游根因或永久相容性保證。

| 實測 | 結果 |
|---|---|
| 目前 desktop 對話以 repo symlink 載入 `explorer` | `agent type is currently not available` |
| 同一角色改用 physical TOML（曾量到 exact 1003 bytes） | named 建立成功 |
| fresh CLI 讀取 physical TOML | named 建立成功 |
| 11 個角色安裝到 `~/.codex/agents/` | destination 與 repo source bytes identical |
| 早期單次 `-c` 註冊 | 可行；當時 `config_file` 指向 physical source file |

目前採用 `scripts/sync-codex-agents.py`：預設只 dry-run，`--apply` 將 `codex/agents/*.toml` 安裝成 destination 的 regular files；repo 更新後用 `--apply --update`，差異檔案或已知 source symlink 會先備份到 `agents` 目錄外的唯一資料夾。foreign symlink、directory、invalid source 與未加 `--update` 的差異 regular file 都在寫入前失敗。這個同步器只處理 Codex agent TOML；`AGENTS.md`、skills 與 Claude 安裝路徑的 symlink 維持原方式。

```bash
python3 scripts/sync-codex-agents.py --destination "$HOME/.codex/agents"
python3 scripts/sync-codex-agents.py --destination "$HOME/.codex/agents" --apply
python3 scripts/sync-codex-agents.py --destination "$HOME/.codex/agents" --apply --update
```

Windows PowerShell 將 `python3` 改成 `python`。不需要永久新增 `[agents.<name>]` 註冊，也不應為了 workaround 改角色 `name`、model 或自然語言指示。

controller 從本機 runtime state `state_5.sqlite` 的 threads 唯讀讀回 child metadata（證據快照：`/private/tmp/codex-physical-agent-runtime-evidence.json`）：physical `worker` 回報 `agent_role=worker`、`model=gpt-5.6-luna`、`reasoning_effort=max`；physical `explorer` 回報 `agent_role=explorer`、`model=gpt-5.6-terra`、`reasoning_effort=medium`。兩次 child 的 live `sandbox_policy` 都繼承父 session 的 `workspace-write`；`explorer.toml` 的 `read-only` 沒有覆蓋 live parent 權限。因此 named 建立與 model／effort 已有證據，不等於 readonly 隔離已驗證；需要唯讀驗收時仍依 adapter 改用強制 `read-only` 的 direct CLI。角色 metadata 必須來自實際 runtime state 或 child metadata，不能用 TOML 或 child 自述代替。
