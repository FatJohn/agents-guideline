# 全域入口（Claude Code）

來源 `<REPO>/global/claude/CLAUDE.md`，symlink 裝在 `~/.claude/CLAUDE.md`；skill 在 `~/.claude/skills/<name>/`。回覆語言由 `settings.json` 的 `language` 承接（值在 `<REPO>/global/claude/settings.snippets.json`）；技術名詞與程式碼保持原文。

@~/.claude/host-facts.md

## 邊界

1. 專案 `CLAUDE.md` 優先於本檔。
2. 無證據不宣稱完成；回報分級：已驗證（附可重跑的指令與輸出）／待 CI／未驗證。
3. 對外或不可逆動作（發訊息、寄信、merge、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案、改 `~/.claude/settings.json`／`~/.codex/config.toml` 的任何欄位）需本 session 當次授權，逐次、逐對象有效；改這兩個設定檔一律先列出 diff、問過才動。
4. 驗證不自驗：驗收派 fresh-context `verifier`（`~/.claude/skills/dispatch/SKILL.md` §6）。
5. 同一 working tree 同時只有一個寫入者。
6. 可中斷的長任務要留可恢復脈絡（`handoff` skill）。

## 路由

| 情境 | 用什麼 |
|---|---|
| 首次改檔前（含自做）、派 subagent、選模型、升降級、驗收後修正 | `dispatch` skill；改檔前先讀 §1 |
| brief、回報、交接、收尾 | `handoff` skill |
| commit／開 PR | `git-commit`／`create-pr` skill |
| ≥2 個寫入切片平行、多個獨立 issue | `parallel-dispatch` skill |
| 寫或改長存文件 | `writing-principles` skill |
| 完成、證據、驗收狀態 | `~/.claude/rules/judgment.md` |
| HTTP／port／hook 異常、除錯前 | `<REPO>/docs/debug-environment-first.md` |
| 修改本系統 | 到 `<REPO>` 開工，讀其 `CLAUDE.md` |

## Bootstrap

context 沒有「# 本機事實：」開頭的段落，或其 hostname 與 `hostname` 不符＝未裝或裝錯：`readlink ~/.claude/CLAUDE.md` 去掉 `/global/claude/CLAUDE.md` 即 `<REPO>`，照 `<REPO>/docs/new-host.md` 建 `global/shared/hosts/<key>.md`。

優先權：使用者當下指示 → 專案規格 → 本系統 → skill 自我宣稱。
