# 05 — 機器事實（跨機器規則與 `<REPO>` 對照在本檔；單機事實在 `../hosts/<key>.md`，每台機器只裝自己那份）

> **Claude Code**：本機事實由全域 `CLAUDE.md` 的 `@~/.claude/host-facts.md` 匯入——context 裡應有一段標題以「# 本機事實：」開頭、hostname 與 `hostname` 現查相符的內容。**Codex**：直接讀 `<REPO>/hosts/<key>.md`。
> **沒有那段＝沒裝或沒建檔；hostname 對不上＝裝錯檔**：依下表讀 `<REPO>/hosts/` 對應檔；沒有對應檔就照 `../README.md`「新機器建檔」探測後**自己建 `hosts/<key>.md`**、補下表與 `AGENTS.md` 的對照、照 README 安裝段裝上（可直接寫入，不用問）。
> **`<REPO>` 對照**（canonical；新機器要加）：主力 Mac（`xushengzhedeMacBook-Pro.local`）`~/Projects/FatJohn/agents-guideline` → `hosts/macos.md`；Windows 桌機（`FatJohn-PC`）`D:\Projects\FatJohn\agents-guideline` → `hosts/windows.md`。
> 事實看起來過時就抽查再用；工具「有沒有裝」永遠以 `command -v` 現查為準，清單只是加速。工具鏈與版本明細在 `../docs/hosts-detail.md`，不常駐。
