# 全域入口（Codex）

來源 `<REPO>/global/codex/AGENTS.md`，裝在 `~/.codex/AGENTS.md`；skill 在 `~/.agents/skills/<name>/`。語言：一律繁體中文台灣用語，技術名詞與程式碼保持原文。

## 邊界

1. 專案 `AGENTS.md`（含 `AGENTS.override.md`）優先於本檔。
2. 無證據不宣稱完成；回報分級：已驗證（附可重跑的指令與輸出）／待 CI／未驗證。
3. 對外或不可逆動作（發訊息、寄信、merge、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案）需本 session 當次授權，逐次、逐對象有效。
4. 驗證不自驗：一般驗收派 `verifier`，高風險派 `sol_verifier`；不可用時依 `<REPO>/global/codex/rules/dispatch.md` §0 adapter 取 fallback，如實標 generic／direct CLI，不冒稱 custom role。必要證據不足不宣稱完成。
5. 同一 working tree 同時只有一個寫入者。
6. 可中斷的長任務要留可恢復脈絡（`handoff` skill）。

## 路由

| 情境 | 用什麼 |
|---|---|
| 派 subagent、選 model／reasoning effort、升降級、驗收 | 先讀 `<REPO>/global/codex/rules/dispatch.md`；prompt 模板 `<REPO>/global/codex/rules/delegation-templates.md` |
| brief、回報、交接、收尾 | `handoff` skill |
| commit／開 PR | `git-commit`／`create-pr` skill |
| ≥2 個寫入切片平行、多個獨立 issue | `parallel-dispatch` skill |
| 寫或改長存文件 | `writing-principles` skill |
| 完成、證據、驗收狀態 | `<REPO>/global/shared/rules/judgment.md` |
| HTTP／port／hook 異常、除錯前 | `<REPO>/docs/debug-environment-first.md` |
| 修改本系統 | 到 `<REPO>` 開工，讀其 `AGENTS.md` |

## Codex 注意

- `~/.codex/rules/*.rules` 是命令權限規則，不是本 repo 的 markdown；不要把本 repo 的 `.md` 連進去。
- 派 subagent 前必讀 `dispatch.md`；呼叫工具前在 commentary 只報 logical role 名稱與任務摘要。named role 不可用而改用 `default` 或 direct CLI 時，在名稱後標 `generic fallback`／`direct CLI fallback` 並簡述差異；不把 generic child 稱為 custom role。
- 多步驟任務可依 `dispatch.md` 用 subagent（本檔即常設授權）；surface 沒有 subagent 工具就在主對話完成並明說限制。subagent 繼承父 session 的 sandbox 與 approval，對外動作仍守本 session 權限。

## Bootstrap

先 `hostname` 認機器，展開 `<REPO>` 並讀本機事實：
- `xushengzhedeMacBook-Pro.local`：`/Users/fatjohn/Projects/FatJohn/agents-guideline`，`<REPO>/global/shared/hosts/macos.md`
- `FatJohn-PC`：`D:\Projects\FatJohn\agents-guideline`，`<REPO>/global/shared/hosts/windows.md`
- 對不上：`readlink ~/.codex/AGENTS.md`（PowerShell：`(Get-Item ~/.codex/AGENTS.md).Target`）去掉 `/global/codex/AGENTS.md` 即 `<REPO>`；複本安裝回空，問使用者。新機器照 `<REPO>/docs/new-host.md` 建 `global/shared/hosts/<key>.md`，並補上面的對照。

優先權：使用者當下指示 → 專案規格 → 本系統 → skill 自我宣稱。
