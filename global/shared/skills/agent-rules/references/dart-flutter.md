# Dart／Flutter：啟用 lint 查法與散文規則對應表

讀者：跑 `agent-rules` 第 2 步「每條規則過分類」的 session，專案是 Dart 或 Flutter。

## 列出實際啟用的 lint

`analysis_options.yaml` 的 `include:` 會串進套件（`package:very_good_analysis/...`、`package:flutter_lints/...`），本檔的 `linter: rules:` 再覆寫。只看專案檔看不到基底開了什麼，只看套件文件看不到專案關了什麼。用本 skill 的腳本解整條鏈：

```bash
python3 <SK>/scripts/active_lints_dart.py --package <repo>                 # 啟用清單；stderr 的 SUMMARY 有 disabled_here 與 plugins
python3 <SK>/scripts/active_lints_dart.py --package <repo> --has eol_at_end_of_file directives_ordering   # 逐條 enabled / disabled here / not enabled
python3 <SK>/scripts/active_lints_dart.py --package <repo> --json
```

前提：`dart pub get` 跑過（`package:` 透過 `.dart_tool/package_config.json` 解析）。多 package 的 workspace 每個 package 各跑一次。

三個要另外看的地方：

- **`disabled_here`**：基底開了、本專案關掉的規則。規則文件還在要求同一件事就是矛盾（例如規則寫「imports 按字母順序」、設定卻 `directives_ordering: false`），二選一。
- **`plugins`**：plugin 沒列出來，靠它執行的套件就算在 `pubspec.yaml` 裡也沒在跑，它們的規則全部算「B 可擋未擋」，不算 A。兩種寫法：舊式 `analyzer: plugins: [custom_lint]`（`dart_code_metrics` 與 riverpod_lint 2.x 走這條，要另跑 `dart run custom_lint`）；新式頂層 `plugins:`（Dart 3.10 起的 analysis_server_plugin，riverpod_lint 3.x 走這條，`riverpod_lint: {version: ^3.1.9}`），腳本兩種都認。新式還有一個陷阱：**`flutter analyze` 不跑 plugin，只有 `dart analyze` 會報**（2026-11-04 實測：同一個違規 `dart analyze` exit 2、`flutter analyze` No issues）；CI 只跑 `flutter analyze` 的專案，plugin 規則仍算 B，要接 `dart analyze` 才算 A。
- **formatter**：`dart format` 管的（縮排、trailing comma 在 `formatter: trailing_commas` 設定下）不是 lint，用 `dart format --output=none --set-exit-if-changed .` 當證據。

## 散文規則 → 機械守門對應表

已知的對應；左欄是常見寫法，實際規則措辭不同時照意思對。「守門」欄寫 lint 名稱、analyzer 診斷或可直接用的指令。

| 散文規則 | 守門 | 分類備註 |
|---|---|---|
| 提交前跑 format 與 analyze | CI 跑 `dart format --output=none --set-exit-if-changed .`、`flutter analyze --fatal-infos` | CI 有就是 A |
| 檔案結尾留 trailing newline | `eol_at_end_of_file` | |
| 檔名 snake_case | `file_names` | 「資料夾用單數」沒有 lint，留 C 或寫 `find` 檢查 |
| 命名遵循 Effective Dart | `camel_case_types`、`non_constant_identifier_names`、`constant_identifier_names` | |
| 控制流一律用大括號 | `curly_braces_in_flow_control_structures` | |
| Widget 加 `const` | `prefer_const_constructors`、`prefer_const_literals_to_create_immutables`、`prefer_const_declarations` | |
| imports 排序 | `directives_ordering` | very_good_analysis 開、專案常關 |
| 建構子放前面、成員順序 | `sort_constructors_first`、`sort_unnamed_constructors_first`；更細的順序要 `dart_code_metrics` 的 `member-ordering` | |
| 不要吞掉 Future | `unawaited_futures`、`discarded_futures` | |
| 不用 `print` | `avoid_print` | |
| `StatelessWidget` 不放可變欄位 | analyzer 診斷 `must_be_immutable`（`@immutable` 帶出） | |
| Freezed 類別宣告為 `abstract`／`sealed` | freezed 3 起非 abstract／sealed 的 class 產生碼無法通過 analyze（未實測，以專案 `flutter analyze` 輸出為準） | 能證明就是 A |
| 不寫死 hex 顏色 | `rg -n 'Color\(0x' lib --glob '!**/*.g.dart' \| rg -v '<顏色常數檔名>'` | 命中數 0 當 CI 閘門 |
| 不要 `_build…()` 方法回傳 Widget | `rg -n 'Widget _build\w*\(' lib`；或 `dart_code_metrics` 的 `avoid-returning-widgets` | |
| 不在 `dispose()` 後碰 `ref` | `riverpod_lint` 的 `avoid_ref_inside_state_dispose` | 要 plugin 在跑且 CI 用 `dart analyze`（見上面 `plugins`） |
| Notifier 的 `build()` 必須存在、不要 public 欄位 | `riverpod_lint` 的 `notifier_build`、`avoid_public_notifier_properties` | 同上 |
| keep-alive 的用法 | `riverpod_lint` 的 `only_use_keep_alive_inside_keep_alive` | 同上 |
| 依賴方向（feature 不得 import 另一個 feature） | 單元測試掃 import（既有專案的 `test/unit/architecture/*_test.dart` 是範本） | 有測試就是 A，測試只守既有白名單的要在證據寫明 |
| 跨 `await` 後不要用 `ref`／`context` | 沒有現成 lint；`use_build_context_synchronously` 只管 `BuildContext` | `ref` 那半留 C，`context` 那半是 A |
| 巢狀不超過兩層、early return | 沒有官方 lint；`dart_code_metrics` 的 `maximum-nesting-level`、`avoid-nested-conditional-expressions` | 沒裝就是 C |

`riverpod_lint` 3.1.9 全部規則（`lib/src/lints/`）：`async_value_nullable_pattern`、`avoid_build_context_in_providers`、`avoid_public_notifier_properties`、`avoid_ref_inside_state_dispose`、`functional_ref`、`missing_provider_scope`、`notifier_build`、`notifier_extends`、`only_use_keep_alive_inside_keep_alive`、`protected_notifier_properties`、`provider_dependencies`、`provider_parameters`、`riverpod_syntax_error`、`scoped_providers_should_specify_dependencies`、`unsupported_provider_value`。不在這張清單裡的 Riverpod 規則就是 C。

## grep 型閘門怎麼寫進 CI

一行 `rg` 能判的規則，放進既有的 CI job 或一支 `scripts/check_rules.sh`，每條一段：

```bash
hits=$(rg -n 'Color\(0x' lib --glob '!**/*.g.dart' | rg -v 'app_colors' || true)
if [ -n "$hits" ]; then printf '%s\n' "寫死 hex 顏色（規則 D-7）：" "$hits"; exit 1; fi
```

既有違規太多一次清不完時，先把目前命中數寫成基線（`expected=7`），CI 只擋「變多」，規則文件旁註明基線與清零的 issue；清零後把閘門改成 0。

## 實測紀錄

2026-11-03，一個 Flutter 專案（very_good_analysis 11.0.0，custom_lint 因 analyzer 版本停用）：81 條規則裡至少 8 條已被啟用中的 lint 或編譯期檢查擋住、2 條與專案關掉的 lint 互相矛盾、`riverpod_lint` 整包沒在跑、2 條用一行 `rg` 各抓到 7 與 15 處。這些都是規則文件本身看不出來的。

2026-11-04，同一專案套用建議：riverpod_lint 3.1.9 改走頂層 `plugins:`，不再需要 custom_lint（custom_lint 0.8.1 仍只支援 analyzer ^8）；開啟當下 `dart analyze` 報 52 處（`avoid_public_notifier_properties` 50、`missing_provider_scope` 2 處誤報，後者以 `diagnostics:` 關掉）。15 條 riverpod_lint 規則沒有一條完整覆蓋該專案的 9 條 Riverpod 散文規則，所以散文一條都沒刪。
