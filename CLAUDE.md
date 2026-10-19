# agents-guideline

本檔是 Claude Code 讀的專案規格；Codex 讀同內容的 `AGENTS.md`，改一邊要同步另一邊。

這是公開 repo：Claude Code 與 Codex 的全域工作制度（入口、規則、agent 合約、skill、rubric）。`global/` 底下的檔案經 symlink（Windows 為同步複本）裝進 `~/.claude`、`~/.codex`、`~/.agents`。

## 目錄

- `global/claude`、`global/codex`：各平台獨立的入口、agent、規則、hook
- `global/shared`：兩平台共用的 skill、rubric、rules、hosts
- `.claude/skills`：repo-only skill（不裝進全域）
- `docs`：設計說明、理由、安裝；`scripts`、`tests`

逐檔用途見 `docs/repo-layout.md`。

## 規則

- 動 `global/**` 前先讀 `.claude/skills/maintain-guideline/SKILL.md`（權限分級與同步矩陣）。
- 公開 repo，不寫非公開專案真名。
- commit 照 `global/shared/skills/git-commit/SKILL.md` 格式。
- 教訓寫在 `docs/lessons.md`。

## 測試

```
python3 -m pytest tests scripts/tests -q
for t in tests/*.sh; do bash "$t"; done
```
