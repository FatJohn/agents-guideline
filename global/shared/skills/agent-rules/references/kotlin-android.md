# Kotlin／Android：啟用 lint 查法與散文規則對應表

讀者：跑 `agent-rules` 第 2 步「每條規則過分類」的 session，專案是 Android（Kotlin）或純 Kotlin。三個工具各管一塊：Android Lint 管平台正確性與資源，ktlint 管排版與基本慣用法，detekt 管複雜度、潛在 bug 與風格。專案不一定三個都裝，先看 `build.gradle.kts` 的 plugins 與 `libs.versions.toml`。

## 列出實際啟用的規則

### Android Lint

Android Lint 約 500 個 issue，39 個預設關閉，`lint --list` 看不出哪些；`lint --show`（不帶 id）的全文對預設關閉的 issue 多印一行 `NOTE: This issue is disabled by default!`。模組自己的開關在 `build.gradle.kts` 的 `android { lint { enable += …; disable += …; checkOnly += … } }` 與模組目錄的 `lint.xml`（`<issue id="X" severity="ignore|warning|error|fatal"/>`）。本 skill 的腳本把這三處合起來算：

```bash
python3 <SK>/scripts/active_lints_android.py --module <模組目錄>                    # 啟用清單；stderr 的 SUMMARY 有 disabled_here、enabled_here、default_off
python3 <SK>/scripts/active_lints_android.py --module <模組目錄> --has HardcodedText StopShip   # 逐條 enabled / disabled here / disabled by default / not an issue id
python3 <SK>/scripts/active_lints_android.py --module <模組目錄> --json
```

前提：cmdline-tools 裝了 `lint`（預設在 `$ANDROID_HOME/cmdline-tools/*/bin/lint` 找最新版，或 `--lint` 指定）。三個限制：

- 這是靜態讀設定，不是跑 Gradle：`lint {}` 區塊用變數組出來的清單、放在別處的 `lintConfig`，腳本看不到；`unknown_ids_in_config` 列出設定裡有但 `--show` 沒有的 id。
- `--show` 只含 SDK 內建檢查。函式庫隨附的 lint（Timber 的 `LogNotTimber`、Compose runtime 的 `ComposableNaming`、`UnrememberedMutableState`、slack compose-lints 的 `ComposeModifierMissing`）只在 Gradle 跑 `lint` 時出現；要查這類，看 `./gradlew :<模組>:lintDebug` 產生的 HTML 報告（`build/reports/lint-results-debug.html`），它有「Disabled Checks」章節，每條標 `Disabled By: Default` 或設定來源。
- `warningsAsErrors`、`abortOnError`、`checkAllWarnings`（含預設關閉的全開）影響的是嚴重度與是否擋 build，不影響啟用集合；分類時要連這三個一起看，`warningsAsErrors = false` 的 warning 不算擋。

### ktlint（直接用或透過 kotlinter／spotless）

ktlint 1.x 沒有列出規則的指令（依 1.8.0 的 CLI 文件，未實跑）。啟用集合＝standard ruleset 全部（1.8.0 文件列 99 條）減 `.editorconfig` 關掉的：

```bash
rg -n '^ktlint_' .editorconfig                      # ktlint_code_style、ktlint_standard_<rule> = disabled、ktlint_standard = disabled、ktlint_experimental = enabled
rg -n -i 'ktlintVersion|kotlinter|ktlint' build.gradle.kts */build.gradle.kts gradle/libs.versions.toml
```

要注意（以下依 ktlint 與 kotlinter 文件，本機未實跑 ktlint）：`ktlint_experimental` 預設不跑；`no-unused-imports` 從 1.7.0 起預設不跑，要 `ktlint_standard_no-unused-imports = enabled`；kotlinter 5.7.0 的 `libs.versions.toml` 寫 ktlint 1.8.0，`kotlinter { ktlintVersion }` 可覆寫，它沒有自己的關規則機制。standard 規則 id 清單在 https://ktlint.github.io/ktlint/latest/rules/standard/ （舊網址 `pinterest.github.io/ktlint` 已 404）。

### detekt

沒有列出有效啟用規則的指令。啟用集合＝`default-detekt-config.yml` 每條的 `active` 預設值，疊上專案 config（`buildUponDefaultConfig = true` 時）或整份取代（false 時）；`allRules = true` 全開。

```bash
./gradlew detektGenerateConfig          # 或 detekt --generate-config；產出預設設定，與專案 config 做 diff
rg -n 'active: (true|false)' config/detekt/detekt.yml | head   # 專案明寫的開關
rg -n 'buildUponDefaultConfig|allRules|config.setFrom' build.gradle.kts
```

規則文件 `https://detekt.dev/docs/rules/<組>`（style、complexity、potential-bugs、coroutines、naming、exceptions、empty-blocks、comments）現在是 2.0 alpha 的內容，分組與 1.23.x 有差；專案用哪版就以那版的 `default-detekt-config.yml` 為準（1.23.8：`https://raw.githubusercontent.com/detekt/detekt/v1.23.8/detekt-core/src/main/resources/default-detekt-config.yml`）。

## 散文規則 → 機械守門對應表

「預設」欄：Android Lint 以 `lint --show` 實測（9.4.0-rc01），detekt 以 1.23.8 的預設 config，ktlint 以 1.8.0 文件；detekt／ktlint 的 id 由文件核對，未在本機實跑。

| 散文規則 | 守門 | 分類備註 |
|---|---|---|
| 不用 `!!` | detekt `UnsafeCallOnNullableType`（預設開） | 沒裝 detekt 時 `rg -n -g '*.kt' '[\w)\]]!!'`，字串內的 `!!` 會誤命中 |
| 不寫魔術數字 | detekt `MagicNumber`（預設開） | |
| 巢狀深度、函式長度、類別太大 | detekt `NestedBlockDepth`（4）、`LongMethod`（60）、`TooManyFunctions`（11）、`LargeClass`、`ComplexCondition`（4） | 門檻寫在 config，規則文字只留來源 |
| 不用 wildcard import | ktlint `standard:no-wildcard-imports`、detekt `WildcardImport` | 兩者都預設開 |
| 不留未用 import | ktlint `no-unused-imports`（1.7.0 起預設關）、detekt `UnusedImports`（預設關） | 常見「以為有擋」的形狀 |
| 行寬 | ktlint `standard:max-line-length`、detekt `MaxLineLength` | 二選一 |
| 命名 | ktlint `standard:function-naming`、detekt `FunctionNaming`／`ClassNaming` | Composable 要設 `ktlint_function_naming_ignore_when_annotated_with=Composable` |
| 不用 `GlobalScope` | detekt `GlobalCoroutineUsage`（**預設關**） | 或 `rg -n -g '*.kt' '\bGlobalScope\b'` |
| 不用 `runBlocking`、`print`／`println` | detekt `ForbiddenMethodCall`（預設關；預設 methods 已含 `kotlin.io.print`／`println`，`runBlocking` 要自己加，未實跑） | |
| 不吞例外 | detekt `SwallowedException`、`TooGenericExceptionCaught`、`EmptyCatchBlock`、`PrintStackTrace`（預設開） | |
| 少用 `lateinit` | detekt `LateinitUsage`（**預設關**） | |
| `TODO`／`FIXME` 要帶票號 | detekt `ForbiddenComment`（預設 `FIXME:`、`STOPSHIP:`、`TODO:`）；Android Lint `StopShip`（預設關） | |
| UI 字串不寫死 | Android Lint `HardcodedText`、`SetTextI18n` | |
| 用 Timber 不用 `Log` | Timber 隨附 `LogNotTimber`（不在 `--show`）；Android Lint `LogConditional`（預設關） | 或 `rg -n -g '*.kt' 'Log\.(d|v|i|w|e|wtf)\('`，`Timber.d(` 不命中 |
| Cursor／資源要釋放 | Android Lint `Recycle` | |
| 清未用資源、過時 SDK_INT 判斷 | Android Lint `UnusedResources`、`ObsoleteSdkInt` | |
| 權限要先檢查 | Android Lint `MissingPermission` | |
| Parcelable 要有 CREATOR | Android Lint `ParcelCreator` | |
| Composable 要有 `Modifier` 參數、`remember` 狀態、命名 | compose-rules：detekt `ModifierMissing`、`RememberMissing`、`ComposableNaming`；ktlint `compose:modifier-missing-check`、`compose:remember-missing-check`；Compose runtime lint `UnrememberedMutableState`、`ComposableNaming`；slack compose-lints `ComposeModifierMissing` | 全是第三方，要看專案裝了哪套；`compose:` 前綴的 id 由文件推得，未實跑 |
| 依賴方向、模組邊界 | 無現成 lint；Gradle 的 `api`／`implementation` 可見性加 ArchUnit 或 Konsist 測試 | C，除非專案已有架構測試 |
| warning 不准進 main | Android Lint `warningsAsErrors = true`；Kotlin `allWarningsAsErrors = true`（`kotlin { compilerOptions }`） | 擋的是「有 warning」這個形狀 |

## grep 型閘門怎麼寫

detekt 的 `ForbiddenMethodCall`／`ForbiddenComment`／`ForbiddenImport` 與 Android Lint 的自訂 issue 比外部 `rg` 好：同一份報告、同樣進 `check`。只有沒裝 detekt、或要掃非 Kotlin 檔時才用 `rg`，寫法同 `dart-flutter.md`「grep 型閘門怎麼寫進 CI」，用 `-g '*.kt'` 限定副檔名、排除 `build/`。

## 實測紀錄

2026-11-03，一個 Android SDK 專案（AGP lint、kotlinter 5.7.0、無 detekt）：`active_lints_android.py --module sdk` 回 total=512、enabled=470、disabled_here=3（與 `build.gradle.kts` 的 `disable += setOf(...)` 三條一致）、default_off=39；`--has HardcodedText GradleDependency StopShip` 分別回 enabled、disabled here、disabled by default。ktlint 的啟用集合只能從 `.editorconfig` 反推（該專案只設 `ktlint_code_style = ktlint_official`，即 standard 全開、experimental 關）。
