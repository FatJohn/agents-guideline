# TypeScript／JavaScript：啟用 lint 查法與散文規則對應表

讀者：跑 `agent-rules` 第 2 步「每條規則過分類」的 session，專案是 TypeScript 或 JavaScript（Node、前端、React 類框架）。常見組合是 ESLint 管語意與慣用法（排版也可能交給它）、`tsc` 管型別，Prettier 或 Biome 視專案而定。

## 列出實際啟用的規則

### ESLint

```bash
pnpm exec eslint --print-config <某個原始碼檔>   # 該檔實際套用的合併設定（JSON）
```

輸出的 `rules` 是每條規則的最終值，嚴重度是第一個元素：`0`／`"off"` 關、`1`／`"warn"` 警告、`2`／`"error"` 錯誤；`plugins` 列出真的載入的 plugin。2026-11-20 在試跑 repo A（ESLint 10.14.0、flat config＋`@antfu/eslint-config`）實測：458 條規則裡 349 條 error、60 條 warn、49 條 off；`package.json` 有、`eslint.config.js` 沒直接 import 的三個 plugin（`@eslint-react/eslint-plugin`、`eslint-plugin-react-refresh`、`eslint-plugin-format`）都出現在 `plugins`，是共用設定載入的。

三個要另外看的地方：

- **依賴清單不等於載入**：plugin 在 `package.json` 只代表裝了。有沒有在跑以 `--print-config` 的 `plugins` 與 `rules` 為準；共用設定（`@antfu/eslint-config`、`eslint-config-*`）會替你載入，沒用共用設定又沒 import 的 plugin 才是「裝了沒跑」。
- **warn 不會讓 CI 失敗**：`eslint .` 只在有 error 時 exit 1。CI 指令要帶 `--max-warnings 0`，嚴重度 1 的規則才算擋；沒帶時，嚴重度 1 的規則歸「可擋未擋」。
- **檔案不同，設定不同**：flat config 依 glob 套不同規則（測試檔、設定檔常放寬），`--print-config` 要對規則想管的那類檔各跑一次。

### TypeScript（`tsc`）

```bash
pnpm exec tsc --showConfig        # 合併 extends 後的 compilerOptions，看 strict、noUncheckedIndexedAccess 等
pnpm exec tsc --noEmit            # 當 CI 閘門（專案若 noEmit 已寫在 tsconfig，直接 tsc）
```

`strict: true` 一次開 `strictNullChecks`、`noImplicitAny` 等一組旗標；個別旗標可以在後面被關掉，以 `--showConfig` 的結果為準。2026-11-20 在試跑 repo A（TypeScript 6.0.3）實測 `--showConfig` 回 `strict: true`。框架先產生型別再檢查的（React Router 的 `react-router typegen && tsc`），CI 要跑整條，只跑 `tsc` 會缺型別檔。

### 排版

- **Prettier**：CI 跑 `prettier --check .`；`prettier --write` 只改檔、不失敗（未實測）。
- **ESLint 管排版**：`@stylistic/eslint-plugin`、`eslint-plugin-format` 或共用設定的 stylistic 選項，排版規則就跟著 ESLint 的嚴重度走；`--print-config` 裡 `style/*`、`format/*` 開頭的規則就是它們。
- **Biome**：`biome ci` 或 `biome check` 一次跑排版與 lint；規則清單用 `biome explain <rule>` 逐條看（未實測）。

## 散文規則對應表

| 散文規則 | 對應的 lint 或檢查 | 備註 |
|---|---|---|
| 不准 `any` | `@typescript-eslint/no-explicit-any`；`tsc` 的 `noImplicitAny` | 前者擋寫出來的 `any`，後者擋推不出型別 |
| 不准 `console.log` 進 main | `no-console` | 常對 scripts 目錄放寬 |
| 不准未使用的 import／變數 | `unused-imports/no-unused-imports`、`@typescript-eslint/no-unused-vars`；整個檔或 export 沒人用交給 knip | |
| import 方向（UI 不准直接 import data 層） | `no-restricted-imports`、`import-x/no-restricted-paths`；整個依賴圖用 dependency-cruiser | 屬結構層，`layer-audit` 另外列 |
| 不准浮動 Promise | `@typescript-eslint/no-floating-promises` | 要 type-aware 設定（`parserOptions.project`） |
| React hook 規則 | `react-hooks/rules-of-hooks`、`react-hooks/exhaustive-deps` | 共用設定可能用別的前綴（`react/`、`@eslint-react/`），以 `--print-config` 的名字為準 |
| warning 不准進 main | `eslint --max-warnings 0` | 擋的是「有 warning」這個形狀 |
