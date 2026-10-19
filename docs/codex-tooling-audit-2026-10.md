# Codex tooling audit（2026-10-11）
> 本檔是歷史紀錄，引用的是重構前的檔案路徑；對照見 `docs/repo-layout.md`。

> 查證環境：macOS `xushengzhedeMacBook-Pro.local`；`codex-cli 0.162.1`。本文件把第一輪盤點的數字標成「調整前 baseline」；第二輪已批准的 config 調整、CLI read-back 與仍待刷新項目分開記錄。數字不可直接當成調整後的 CLI 或桌面 catalog。
> 本次文件只記現況、可追溯操作與未驗證項；不把 metadata bytes 當 token 或實際注入量，也不宣稱 token 節省。

## 調整前 baseline（已查證 facts）

### Surface 與技能載入

- `codex --version` 回報 `codex-cli 0.162.1`。
- 調整前執行 `codex plugin list --json` 列出 23 個 installed plugin，當時回報全部 `enabled=true`。
- 調整前 fresh CLI JSONRPC `skills/list` 使用 `forceReload` 發現 68 個 enabled skills，`errors=[]`；其中 14 個 SKILL frontmatter 設為 `disable-model-invocation=true`。
- 調整前 CLI skill metadata 的 `name`＋`description` UTF-8 bytes 為 21,144；這只是 metadata 代理量，不是 token 數，也不是注入量。
- 調整前本桌面 session 的 Available skills 有 72 筆、58 個不同名稱；14 個 Figma 名稱各出現兩次。文字段 UTF-8 bytes 為 21,033，也不是 token 數。
- 調整前 CLI 沒有帶入 `openai-curated-remote` skills，因此 CLI 68 筆不能作為桌面 session 的證據；CLI 的 68 筆也不等於每次都自動注入。
- 桌面 session catalog 統計來源為 session `01a12a44-9d73-7c50-a279-6115b6cb6b10`；文件只保留 ID 與統計，不引用整段 history。

### Plugins、Figma 與 MCP

- 調整前 23 個 installed plugin 的構成：`@openai-primary-runtime` 有 `documents`、`pdf`、`spreadsheets`、`presentations`、`template-creator`；`@openai-bundled` 有 `codex-app-tools`、`browser`、`unified-computer-use`、`chrome`、`computer-use`、`code-review`、`visualize`；`@claude-plugins-official` 有 `figma`、`firebase`、`frontend-design`、`playwright`、`sentry`；`@openai-curated-remote` 有 `clickup`、`figma`、`openai-templates`、`sites`、`plugin-management`、`work-pets`。
- 調整前 config 可見 17 個 local plugin `enabled=true`；另有 6 個 remote plugin 只在 `plugin list` 可見，不能只讀 config 推回完整安裝清單。
- local `figma@claude-plugins-official` 是 2.2.127，remote `figma@openai-curated-remote` 是 15.0.0；兩邊各有 14 個 skills，兩份 frontmatter 總 bytes 各為 6,904。
- 兩份 Figma skills 至少 `figma-generate-design` 正文不同；local 版本另有 HTML-to-Figma Exceptions，因此不能宣稱是同字檔。
- 桌面同時暴露 `mcp__figma` 與 `mcp__codex_apps__figma` 兩族工具；前者由 local plugin 提供 MCP，後者是 connected app。
- local Figma 與 connected-app Figma 仍是不同 surface；本輪只停用 local plugin 的預設啟用，不卸載 remote `figma` 或 connected app，停用後能力需以新 CLI／桌面 session read-back 為準。
- Sentry plugin root `plugin.json` 的 `mcpServers.sentry` 是 `https://mcp.sentry.dev/mcp?utm_source=plugin`；standalone config 的 `mcp_servers.sentry` 是 `npx -y mcp-remote@latest https://mcp.sentry.dev/mcp`。兩者 server ID／endpoint 相同但 query 不同；目前只看到 `mcp__sentry` 工具族，尚不證明 runtime 建立了重複連線或重複注入。

### Claude 對照與 local skills

- `~/.agents/skills` 有 33 個 skills：14 個 manual、19 個 auto。14 個 manual 為 `ask-matt`、`grill-me`、`grill-with-docs`、`handoff`、`implement`、`improve-codebase-architecture`、`setup-matt-pocock-skills`、`teach`、`to-questionnaire`、`to-spec`、`to-tickets`、`triage`、`wait-what`、`wayfinder`。
- 本桌面 session 沒有注入上述 14 個 manual skills，因此不需要為了本次 catalog 再刪它們。
- `orchestration`、`orca-cli`、`computer-use` 屬 Orca 相關的按需候選；本輪以 `[[skills.config]]` 停用其預設注入，不修改第三方 SKILL frontmatter。
- Claude 此次 enabled plugins 為 `codex`、`context7`、`mattpocock-skills`、`remember`、`kotlin-lsp`、`swift-lsp`、`typescript-lsp`、`dart-lsp`；`document-skills` 為 false。Codex 不需為了名字完全相同而刪必要能力。
- `node_repl` 是目前 CUA 的支援，不能因看似額外而盲目關閉。standalone `computer-use` MCP 仍是 `enabled=false`；`browser`、`chrome`、`unified-computer-use` 仍保留為 runtime 組件。
- `code-review@openai-bundled` 沒有 SKILL，不等同 local `code-review` skill；不可判定為完全重複。

### LSP／語意工具現況

- 當前 session tool catalog 沒有 LSP、reference、definition 等語意導航工具；Codex config 也查不到 LSP 設定。這只代表本次 surface 未暴露，不能推成所有 Codex 永遠不支援。
- `command -v dart` 為 `/Users/fatjohn/development/flutter/bin/dart`，`dart --version` 為 Dart 3.13.5 stable。
- Flutter 官方 [Dart and Flutter MCP server](https://docs.flutter.dev/ai/tools) 說明 stdio、analysis diagnostics、symbol resolution（definitions／signatures／docs）與 runtime 能力；官方 [Codex get started](https://docs.flutter.dev/ai/get-started) 提供 `marketplace add flutter/agent-plugins` 與 `plugin add dart-flutter@dart-flutter`。
- `dart mcp-server --disable all --enable lsp --enable roots` 在隔離 CLI process initialize 與 `tools/list` 成功，serverInfo 為 `dart and flutter tooling` 1.2.0，只暴露 `roots`、`lsp` 兩個工具。
- lsp schema 的 `command` enum 只有 `hover`、`signatureHelp`、`resolveWorkspaceSymbol`，沒有 `reference`／`rename`；這是能力邊界，不能把 MCP 宣稱成完整 LSP。
- 臨時 `dart-fixture` 的 `AuditSymbol` probe 中，`roots add` 成功；`hover` 回傳 class `AuditSymbol` 與 `probe.dart`，`resolveWorkspaceSymbol` 回傳 kind 5 及 `probe.dart` file URI／line 0。
- `/tmp/codex-dart-appserver-probe-20261011.json` 的 controller probe 已在隔離 `dart-fixture` 以 Codex app-server thread 驗證 Dart MCP 接入：`dartStatus.runtimeStatus=connected`，serverInfo `dart and flutter tooling` 1.2.0，實際列出 `lsp`／`roots`；`roots add` 回傳 `Success`，`lsp hover` 回傳 `AuditSymbol`，`resolveWorkspaceSymbol` 回傳 `probe.dart`。這只證明隔離 fixture＋app-server thread 的接入，沒有把 Dart／Flutter MCP 安裝成 Codex 全域常駐設定。
- analyzer（`dart analyze`、`flutter analyze`、`tsc --noEmit`）是專案診斷工具；採用 MCP 前仍需分開驗真實專案的 source mapping、cold start 與 permission。

## 已套用配置（2026-10-11）

來源是 `/Users/fatjohn/.codex/config.toml`；本輪以 controller 提供的 `/Users/fatjohn/.codex/backups/config-before-tooling-20261011-174345.toml` 作 before 結構比較。config parse、approved diff 與 path existence 已驗證，其他 model／effort／features／hooks／agents limits／approval／sandbox 等值保持不變。

- 10 個 local plugin 已設 `enabled=false`：`documents@openai-primary-runtime`、`pdf@openai-primary-runtime`、`spreadsheets@openai-primary-runtime`、`presentations@openai-primary-runtime`、`template-creator@openai-primary-runtime`、`figma@claude-plugins-official`、`frontend-design@claude-plugins-official`、`playwright@claude-plugins-official`、`sentry@claude-plugins-official`、`firebase@claude-plugins-official`。plugin cache 未刪除，其他 7 個 local plugin 的值未改。
- standalone `[mcp_servers.sentry]` 已設 `enabled=false`；Sentry 按次啟用走 local Sentry plugin，避免 standalone 與 plugin 同時作為預設來源。
- 3 個 local Orca skill 已加入 `[[skills.config]]` 並設 `enabled=false`：`/Users/fatjohn/.agents/skills/orca-cli/SKILL.md`、`/Users/fatjohn/.agents/skills/orchestration/SKILL.md`、`/Users/fatjohn/.agents/skills/computer-use/SKILL.md`。
- 已嘗試以相同 per-skill 機制停用 4 個 remote auto skill：`/Users/fatjohn/.codex/plugins/cache/openai-curated-remote/sites/1.0.1/skills/sites/SKILL.md`、`/Users/fatjohn/.codex/plugins/cache/openai-curated-remote/work-pets/0.1.6/skills/create-pet/SKILL.md`、`/Users/fatjohn/.codex/plugins/cache/openai-curated-remote/work-pets/0.1.6/skills/pets/SKILL.md`、`/Users/fatjohn/.codex/plugins/cache/openai-curated-remote/work-pets/0.1.6/skills/update-pet/SKILL.md`。4 個 path 均存在且無 duplicate；`/tmp/codex-remote-skill-roots-probe-20261011.json` 的隔離 app-server 以 `skills/extraRoots/set` 註冊兩個 exact skill roots，再 `skills/list forceReload`，四個 targets 實際均為 `enabled=false`，`configUnchanged=true`。這已驗證核心 loader 掃描 exact path 時尊重 disabled；hosting／remote workspace surface 重新載入仍待驗。
- `browser`、`chrome`、`computer-use`、`unified-computer-use`、`codex-app-tools`、`code-review`、`visualize` 仍維持 `enabled=true`；`node_repl` 的既有 command／env 未改；standalone `computer-use` MCP 仍維持 `enabled=false`。remote plugin／connected app 仍安裝，沒有卸載或刪 cache。

驗證分層如下：本輪已驗證的是 config TOML parse、before／after approved diff、7 個 skill path existence／uniqueness、核心 browser／CUA 值、standalone Sentry false，以及 fresh CLI `skills/list` 的 `discovered=39`、`enabled=36`、`errors=[]`、`name+description UTF-8 bytes=8,110`；active breakdown 為 `user=30`、`system=5`、`visualize@openai-bundled=1`，3 個 Orca entries 均出現在 catalog 且 `enabled=false`。CLI `plugin list --json` after read-back 為 23 個 installed、13 個 enabled、10 個 disabled；enabled 組成為 7 個 bundled＋6 個 remote，10 個 local target flags 為 false，remote `figma`／`clickup` 保留 enabled。`/tmp/codex-remote-skill-roots-probe-20261011.json` 已驗證核心 loader exact path 掃描的四個 remote targets 均 disabled 且 config 未變；這只證明核心 loader 行為，不等於 hosting surface 已重新載入。桌面 Available skills 與 hosting surface reload 仍待 controller／fresh verifier read-back。調整前的 `23／68／72` 只能作 baseline，不能當作 after count。

## 按次啟用入口

`codex -c 'plugins."figma@claude-plugins-official".enabled=true'` 的 fresh `skills/list` 與 `codex plugin list --json` probe 沒有改變 local Figma 的 `enabled=false`；`documents` 與 `sentry` 的 launch overrides 也沒有讓其 skills 在 fresh `skills/list` 重現。這些 probe 不涵蓋其餘 plugin，因此本文件不使用 plugin launch override 作恢復入口。需要 local plugin 時，將對應的 `/Users/fatjohn/.codex/config.toml` table 暫設為 `enabled=true`、開新 session，完成後改回 `false`；只修改目標 table，沿用既有 backup／parse／read-back 流程。remote plugin／connected app state 不由此控制。

已查證可用的是 MCP 的 invocation override，plugin loader 與 MCP server 語意分開：

```bash
# 從 Flutter project root 執行；只為這次 Codex process 指定 Dart MCP
cd /path/to/flutter-project
codex -C "$PWD" \
  -c 'mcp_servers.dart.command="/Users/fatjohn/development/flutter/bin/dart"' \
  -c 'mcp_servers.dart.args=["mcp-server","--disable","all","--enable","lsp","--enable","roots"]'
```

上述 Dart command／args 已在隔離 fixture 的 Codex app-server probe 驗證 `roots`／`lsp`；本版本 lsp schema 明確不支持 `reference`／`rename`，它們不是待驗功能。真實 Flutter project 的 source mapping、cold start 與 permission 仍待 controller 驗證；全域沒有常駐 Dart MCP。

### Orca skill 按次恢復

`skills.config` 是 array；`-c 'skills.config=[{...}]'` 會整體覆蓋 array，且本輪尚未證明 loader 會以這種 override 恢復單一 path。因此按次恢復採用和 local plugin 相同的精確 table 編輯：只把對應 path 的 `enabled=false` 暫改成 `enabled=true`、開新 session，完成後改回 `false`；不改第三方 SKILL frontmatter。其他 6 個停用 entry 必須保留。

### Local plugin 按次恢復

`documents`、`pdf`、`spreadsheets`、`presentations`、`template-creator`、`figma`、`frontend-design`、`playwright`、`sentry`、`firebase` 均依相同 table toggle 方式暫時恢復；例如編輯對應 table：

```toml
[plugins."figma@claude-plugins-official"]
enabled = true
```

Sentry plugin 暫時啟用時，`[mcp_servers.sentry].enabled` 維持 `false`；完成後把 plugin table 改回 `enabled=false`。官方 [plugin 文件](https://developers.openai.com/plugins/build/plugins) 的 local `enabled=false` 是停用而非卸載；remote `figma`／`clickup` 等 workspace-managed state 不由這個 local table 控制。

官方 [skills 說明](https://learn.chatgpt.com/docs/build-skills) 表示先載入 name／description，再按需載入 SKILL，`enabled=false` 停用需重啟。Codex MCP 設定參考以官方 [MCP 文件](https://developers.openai.com/codex/mcp) 為準；不直接搬 Claude 的 `.lsp.json`、agent、rules 或 `CODEX.md` 寫法。

## 未驗證與刷新入口

- Sentry standalone source 已在 config 層設為 false；plugin／MCP 是否只建立單一來源仍需 controller 以 fresh runtime read-back 確認。
- local／remote Figma 在不同 surface 的實際啟用、工具衝突與停用後能力，需各自 fresh session read-back；remote Figma 與 connected app 沒有卸載。
- 核心 loader 對 remote `sites`／`work-pets` 四個 exact path 的 `enabled=false` 已由隔離 roots probe 驗證；hosting／remote workspace surface 是否重新載入仍待驗證。若 SDK 不支持該 hosting path，不改 remote plugin state、不猜替代 key。
- `/tmp/codex-remote-skill-roots-probe-20261011.json` 是補充 evidence：`skills/extraRoots/set` 後 `skills/list forceReload` 的四個 targets 為 `('sites:sites', false)`、`('work-pets:create-pet', false)`、`('work-pets:pets', false)`、`('work-pets:update-pet', false)`，且 `configUnchanged=true`。這不證明 remote workspace／hosting surface 已刷新。
- `/tmp/codex-fresh-verifier-catalog-20261011.json` 的 named fresh verifier 仍讀到初始 developer catalog `72 entries／58 unique／14 duplicate Figma names`，local disabled skills 與 remote4 仍出現；child 沿用父 surface snapshot，不能把它當成新的 hosting surface read-back。
- `/tmp/codex-default-mcp-status-20261011.json` 的 default app-server `mcpServerStatus/list` 觀察到 Figma／Dart 的 `data=[]`；standalone Sentry 只列 config entry，`runtimeStatus=null`、`tools={}`、`serverInfo=null`。這只能表示該 probe 未發現對應 runtime inventory，不作 plugin source、connected 或 trace proof。
- Dart MCP 已在隔離 `dart-fixture` 的 Codex app-server thread 驗證 `lsp`／`roots`、`roots add`、`hover` 與 `resolveWorkspaceSymbol`；本版本 schema 不支持 `reference`／`rename`，未驗證項只剩真實 Flutter project 的 source mapping、cold start 與 permission。
- `skills.max_context_tokens` 官方 config reference 的預設是 window 的 2%、上限 10,000；這是目錄預算，不是 token 測量，來源為 [config reference](https://learn.chatgpt.com/docs/config-file/config-reference)。
- 調整前 CLI 證據摘要可在 `/var/folders/_7/sl615x616fq3z0gyqk39v82r0000gn/T/codex-tooling-audit-wre9zfif/plugins-before.json` 與 `skills-before.json` 讀回；長期文件不以 temporary path 作唯一證據。
- controller 的 Dart app-server probe 可在 `/tmp/codex-dart-appserver-probe-20261011.json` 讀回；它只證明隔離 fixture＋app-server thread，不證明真實 Flutter project 已接入。
- 後續刷新應重跑 `codex --version`、`codex plugin list --json`、fresh JSONRPC `skills/list`（`forceReload`），再以新桌面 session 重新計數 Available skills；不要沿用本次 bytes 當永久基線。

第一輪盤點未修改 `~/.codex/config.toml`、plugin state、skills cache 或 memory；第二輪依批准 scope 已只修改 `~/.codex/config.toml` 的上述 local plugin／standalone Sentry／per-skill entries，未卸載 remote plugin、未刪 cache、未改 memory。完成後仍以 controller 的 fresh CLI／桌面 read-back 作 runtime 判定。
