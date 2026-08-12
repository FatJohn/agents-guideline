# skill／plugin 選用指引（用到才讀）

> 2026-08-12 由 `rules/00-environment.md` §好用的 skill／plugin 整節搬入（瘦身：該節每 session 常駐但內容本身要求「一律現查」，常駐價值低）。
> 事實查證日沿用搬出前的 **2026-08-06**；本檔不常駐，引用前先當場核對。
> 常駐區只留原則與指向，見 `rules/00-environment.md` §好用的 skill／plugin。

原則：動手前先想「這類問題有沒有現成 skill」，有就用，不要土炮重造；但真正符合任務才叫用（優先權排序依平台見全域 `CLAUDE.md`／`AGENTS.md`）。

- **開發流程**：兩端共用本 repo 的 `debug-environment-first`；其他 skill 必須以當前 session 公開的清單為準，不跨平台猜名稱。若 Claude 當前有公開 `mattpocock-skills:` 或 `andrej-karpathy-skills:`，可依任務叫用；Codex 只有在自己的清單也公開對應 skill 時才能叫用，否則依當前可用 skill 或主流程完成。這些 skill 管「執行者怎麼做好一件事」，本系統管「指揮官怎麼調度與驗收」；宣稱完成前由 `rules/20-judgment.md` §2 與 verifier 把關。
- **查網頁／爬資料**：Claude 使用當前 session 公開的 web search／fetch 或已註冊的文件 MCP；Codex 使用自己當前 session 公開的 web／browser 工具。這份跨機器檔不固定暫時的 tool 名稱；每次現查，不把另一平台的名稱直接套用。適合派工時只把結論帶回主對話。
- **產出文件**：兩端都只使用當前 session 公開的文件產出 skill；Claude／Codex 的實際名稱可能不同，以各自當前清單為準，不跨平台猜名稱。
- **找新工具**：遇到「感覺應該有現成工具」的問題，先查當前平台公開的 skill／plugin／connector 清單；需要安裝或沒有可用入口時再問使用者，找不到才自己寫。
- **Figma 設計稿**：session 內搜不到 `figma-dev-mode-mcp-server` 工具時（plugin 未啟用，或 MCP 未在 session 啟動時註冊；2026-08-06 現查主力 Mac 的 `enabledPlugins` 已無 figma），
  只要 Figma 桌面 App 的 Dev Mode MCP server 在 `127.0.0.1:3845` 有跑，就能用 `curl` 手動走 JSON-RPC
  （initialize → tools/call `get_design_context`／`get_screenshot`／`get_metadata`）直接取設計稿，不必重開 session。

## 搬移時一併刪除的重複條目（2026-08-12）

原節另有 4 條在別處已有 canonical，未搬入本檔，直接刪除：

- 「工具分工」（Memories／handoff／hooks／Chronicle 四層不合併）→ canonical 在 `rules/00-environment.md` §記憶機制（四層，各有分工）。
- 「Codex 收尾交接」（`session-handoff` 寫 `.codex/HANDOFF.md`）→ canonical 在 `rules/00-environment.md` §記憶機制的「顯式交接檔」條。
- 「Claude 派工」「Codex 派工」「外部第二意見／整包委派」→ 純指標，canonical 在 `rules/10-dispatch.md` 與 `codex/rules/10-dispatch-codex.md`，全域 `CLAUDE.md`／`AGENTS.md` 的索引表也已有路由。
