# Swift／iOS：啟用 lint 查法與散文規則對應表

讀者：跑 `agent-rules` 第 2 步「每條規則過分類」的 session，專案是 Swift（iOS／macOS App 或 Swift Package）。常見組合是 SwiftLint 管語意與慣用法、swift-format 管排版，兩邊各有自己的規則名；Xcode 的編譯設定是第三道守門。

## 列出實際啟用的規則

### SwiftLint

```bash
<swiftlint> rules --config .swiftlint.yml              # 全表：identifier、opt-in、correctable、enabled in your config、kind、analyzer
<swiftlint> rules --config .swiftlint.yml --enabled    # 只列啟用的
<swiftlint> rules --config .swiftlint.yml --disabled   # 只列關掉的
<swiftlint> rules <rule-id>                            # 單條：說明、設定值、觸發與不觸發範例
<swiftlint> rules --config .swiftlint.yml --config-only   # 印出合併後的 YAML
```

`<swiftlint>` 是專案固定版本的二進位（常見放 `.tools/swiftlint`，由 `scripts/install-swiftlint.sh` 之類下載）；沒有就 `brew install swiftlint`，但版本要與 CI 一致，規則集每版都在變。

三個要另外看的地方：

- **opt-in 欄**：`opt-in: yes` 的規則預設不跑，要在 `opt_in_rules:` 列出或寫 `opt_in_rules: [all]` 才算啟用；只看 `rules` 全表會把它們誤判成已擋。以「enabled in your config」欄為準。
- **analyzer 欄**：`analyzer: yes` 的規則（0.65.1 共 5 條：`capture_variable`、`explicit_self`、`typesafe_array_init`、`unused_declaration`、`unused_import`）只在 `swiftlint analyze --compiler-log-path <log>` 下跑，`swiftlint lint` 不會跑；CI 沒跑 `analyze` 就不算擋。
- **與 swift-format 的分工**：專案常把排版類規則（`indentation_width`、`sorted_imports`、`multiline_*`、`opening_brace` 變體）關掉交給 swift-format；關掉的規則要對照 swift-format 那邊有沒有對應規則，兩邊都沒有才是「可擋未擋」。

### swift-format

Xcode 16 起內建 `swift format` 子命令（Xcode 27.2 實測 6.4.4），獨立安裝的叫 `swift-format`。

```bash
cd <專案根> && swift format dump-configuration --effective   # 合併 .swift-format 後實際生效的設定，含 rules 的 true／false
swift format dump-configuration                              # 預設值，拿來比對專案關了什麼
swift format lint --strict --recursive Sources Tests         # 當 CI 閘門
```

`dump-configuration` 不帶 `--effective` 印的是預設值，不是專案的；實測 43 條規則預設 31 條開，專案開全部 43 條時只有 `--effective` 看得出來。

### Xcode 編譯設定

`SWIFT_TREAT_WARNINGS_AS_ERRORS = YES`、`SWIFT_STRICT_CONCURRENCY = complete`、`SWIFT_UPCOMING_FEATURE_*`、`GCC_TREAT_WARNINGS_AS_ERRORS`，寫在 `.xcconfig` 或 pbxproj 的 buildSettings；Swift Package 則是 `Package.swift` 的 `swiftSettings: [.unsafeFlags(["-warnings-as-errors"])]` 或 `.enableUpcomingFeature`。查法：`xcodebuild -showBuildSettings -scheme <s> | rg 'SWIFT_TREAT_WARNINGS_AS_ERRORS|SWIFT_STRICT_CONCURRENCY'`（未實測）。這一層擋的是「warning 不准進 main」與「並行安全」類規則。

## 散文規則 → 機械守門對應表

規則 id 皆在 SwiftLint 0.65.1 用 `rules <id>` 實查過；opt-in 欄標「opt-in」的要確認專案有開。swift-format 的規則名取自 `dump-configuration` 輸出。

| 散文規則 | 守門 | 分類備註 |
|---|---|---|
| 不用 `!` 強制解包 | SwiftLint `force_unwrapping`（opt-in）；swift-format `NeverForceUnwrap` | 兩邊都有，專案通常只開一邊 |
| 不用 `try!`／`as!` | SwiftLint `force_try`、`force_cast`（預設開）；swift-format `NeverUseForceTry` | |
| 不用隱式解包 `!` 型別 | SwiftLint `implicitly_unwrapped_optional`（opt-in）；swift-format `NeverUseImplicitlyUnwrappedOptionals` | |
| delegate 用 `weak` | SwiftLint `weak_delegate`（opt-in） | |
| closure 捕獲避免 retain cycle | SwiftLint `unowned_variable_capture`（opt-in）；`capture_variable`（analyzer，要 `analyze`） | 「一律 `[weak self]`」沒有現成規則，留 C 或 `custom_rules` |
| 檔案／型別／函式長度上限 | SwiftLint `file_length`、`type_body_length`、`function_body_length`、`closure_body_length`（opt-in） | 門檻寫進設定，規則文字只留數字來源 |
| 巢狀深度、複雜度 | SwiftLint `nesting`、`cyclomatic_complexity` | |
| 行寬 | SwiftLint `line_length`；swift-format 設定鍵 `lineLength`（不是 rule） | 二選一，另一邊關掉 |
| 命名（lowerCamelCase、型別大寫） | SwiftLint `identifier_name`、`type_name`；swift-format `AlwaysUseLowerCamelCase`、`TypeNamesShouldBeCapitalized` | |
| `IBOutlet`／`IBAction` 用 `private`、outlet 用 `weak` | SwiftLint `private_outlet`、`private_action`、`strong_iboutlet`（皆 opt-in） | |
| `fatalError` 要帶訊息 | SwiftLint `fatal_error_message`（opt-in） | |
| 不用 `Bool?` | SwiftLint `discouraged_optional_boolean`（opt-in） | |
| 明寫存取層級、公開 API 要文件 | SwiftLint `explicit_acl`、`missing_docs`（opt-in）；swift-format `AllPublicDeclarationsHaveDocumentation`、`FileScopedDeclarationPrivacy` | |
| 不寫魔術數字 | SwiftLint `no_magic_numbers`（opt-in） | |
| 靜態成員用 `Self` | SwiftLint `prefer_self_in_static_references`（opt-in） | |
| 不留空 block | SwiftLint `no_empty_block`（opt-in，可排除 initializer） | |
| 未使用的宣告／import | SwiftLint `unused_declaration`、`unused_import`（analyzer）；或 Periphery（未實測） | CI 沒跑 `swiftlint analyze` 就是 B |
| import 排序、不重複 import | swift-format `OrderedImports`；SwiftLint `sorted_imports`（opt-in）、`duplicate_imports` | |
| `count == 0` 改 `isEmpty`、`first(where:)` | SwiftLint `empty_count`、`first_where`、`contains_over_first_not_nil`（opt-in） | |
| tuple 不超過 N 個元素 | SwiftLint `large_tuple` | |
| 不用 `NSString`／`NSArray` 等 legacy 型別 | SwiftLint `legacy_objc_type`（opt-in） | |
| 型別可推論就不標註 | SwiftLint `redundant_type_annotation`（opt-in） | 與「一律標型別」的 `explicit_type_interface` 互斥 |
| `catch` 不要吞掉 error 型別 | SwiftLint `untyped_error_in_catch`（opt-in） | |
| 不用 `print`、不用 `debugPrint` | 沒有內建規則；`custom_rules` 一條 regex，或 `rg -n '^\s*(debugPrint|print)\(' Sources` | B |
| `TODO`／`FIXME` 要帶票號 | SwiftLint `todo` 只擋存在；帶票號要 `custom_rules` | |
| 早退（guard）優先 | swift-format `UseEarlyExits` | |
| 不用分號、不用區塊註解 | swift-format `DoNotUseSemicolons`、`NoBlockComments` | |
| warning 不准進 main | Xcode `SWIFT_TREAT_WARNINGS_AS_ERRORS`／SwiftPM `-warnings-as-errors`；SwiftLint `--strict` | 擋的是「有 warning」這個形狀 |
| 並行安全（Sendable、actor 隔離） | `SWIFT_STRICT_CONCURRENCY = complete` 讓編譯器報錯 | 規則文字只留「開到 complete」，細節交給編譯器 |

## grep 型閘門怎麼寫

SwiftLint 的 `custom_rules` 比外部 `rg` 好：同一份報告、同一個 severity、同樣進 CI。

```yaml
custom_rules:
  no_print:
    name: "No print"
    regex: '^\s*(debugPrint|print)\('
    match_kinds: [identifier]
    message: "用 Logger（規則 L-3）"
    severity: error
```

需要跨檔或非 Swift 檔的才用 `rg`，寫法同 `dart-flutter.md`「grep 型閘門怎麼寫進 CI」。

## 實測紀錄

2026-11-03，一個 iOS SDK 專案（Swift Package，SwiftLint 0.65.1 固定在 `.tools/`，`opt_in_rules: [all]` 加 `disabled_rules` 26 條，swift-format 43 條全開）。

| 計數 | 值 | 怎麼數 |
|---|---|---|
| `rules --enabled` | 225 | 表格資料列數，不含表框與表頭 |
| `rules --disabled` | 31 | 同上；26 條來自 `disabled_rules`，5 條是 analyzer 規則（`lint` 階段本來就不跑） |
| 候選 id 不存在 | 3 | `print_usage`、`no_print`、`main_actor_in_defer`，已改寫成 `custom_rules` |
