---
name: layer-audit
description: 唯讀稽核一個 repo 有沒有把防線層建起來（結構、機器擋、跑起來驗、文字規則、獨立審查），每層查有沒有啟用、CI 有沒有跑、違規會不會讓 CI 失敗，輸出狀態與證據，不打分數。只由使用者觸發：Claude Code 打 /layer-audit，Codex 打 $layer-audit。
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(git:*), Bash(gh api:*), Bash(rg:*), Read, Grep, Glob
---

# layer-audit — 各層防線有沒有在擋

> 讀者：被使用者叫來稽核某個 repo 的 session，語言不限。`<SK>` 指本 skill 的目錄（安裝後是 `~/.claude/skills/layer-audit` 或 `~/.agents/skills/layer-audit`）。

一個錯誤的去處由強到弱是：結構讓它寫不出來、機器擋下、跑起來驗到、文字規則、人看。本 skill 從「層」出發，回答每一層有沒有、有的話是不是真的在擋。`agent-rules` 從「規則」出發；本 skill 找到「文字規則沒有機器擋」這類缺口時，交給它逐條分類。

## 跑法

```bash
python3 <SK>/scripts/layer_audit.py --repo <路徑>                  # Markdown 表
python3 <SK>/scripts/layer_audit.py --repo <路徑> --format json    # 機器可讀
python3 <SK>/scripts/layer_audit.py --repo <路徑> --github         # 另用 gh api 唯讀查分支保護與 ruleset
```

腳本只讀、只用 Python 標準庫，不安裝依賴也不執行目標 repo 的任何指令。輸出每列是「層、檢查項、狀態、證據、備註」；狀態值的定義印在輸出開頭。「有設定但沒有在擋」（`local-only`、`non-blocking`、`inactive`）與「有在擋」（`blocking`）一定是不同的值。

腳本判斷「有沒有在擋」的依據：

- **CI 會不會跑到**：從 workflow 的 `run:` 往下展開 package.json scripts、Makefile target 與被呼叫的 shell 腳本，看工具最後有沒有被執行。只寫在設定檔、CI 沒呼叫的是 `local-only`。
- **失敗會不會傳出來**：job／step 的 `continue-on-error`、`|| true`、`set +e` 後沒檢查 `$?`（管線後只認 `PIPESTATUS`）、管線沒有 pipefail（package script 與 Makefile recipe 用 `sh -c`，一律當沒有）、package script 用 `;` 串接、指令放在 `if`／`while` 條件裡而失敗分支沒有非 0 的 `exit`，都判 `non-blocking`。
- **一般 PR 會不會跑**：workflow 沒有 `pull_request` 觸發、job／step 的 `if:` 排除 PR 或只在前面失敗時跑（`failure()`、`cancelled()`）、reusable workflow 的呼叫端 job 都排除 PR，判 `non-blocking`，因為 merge 前擋不到。
- **只到 warning**：lint 預設只在 error 失敗，warning 級規則另列一列（ESLint 沒帶 `--max-warnings 0`、SwiftLint 沒帶 `--strict`、`dart analyze` 沒帶 `--fatal-infos`、Android Lint 沒開 `warningsAsErrors`）。ESLint 設定沒有字面 `warn` 時：沒載入共用設定就不列，載入了共用設定（import 名稱含 `eslint-config`）則列 `unknown`，要用 `eslint --print-config` 看有沒有嚴重度 1 的規則。
- **裝了但沒跑**：Gradle plugin 寫在版本目錄卻沒有 build 檔套用、Dart analyzer plugin 只有 `dart analyze` 會跑而 CI 只跑 `flutter analyze`、ESLint plugin 在依賴裡但設定沒引用，判 `inactive`；有共用設定可能代為載入時判 `unknown`。

## 基本盤

每個 repo 都該有的只有一項：格式化、lint、型別或靜態分析進 CI 且會失敗。腳本對每個有 manifest 的語言各列三列，檢查項前綴「【基本盤】」，表尾列出沒達到 `blocking` 的。其他層只列現況，缺了不代表要補，要不要補由使用者決定。

## 跑完之後

1. **`unknown` 列逐一看**：備註寫了為什麼判不出來。「測試是不是只測 mock」與「一件事是不是只有一種寫法」一定是 `unknown`，讀測試與程式碼判斷；mock import 的檔數只是線索。
2. **至少一項機器擋用實跑佐證**：在 `git clone --local --no-hardlinks <repo> <暫存目錄>` 的副本裡故意加一個違規，跑 CI 用的同一條指令，看到它失敗。不在使用者的 checkout 裡跑，因為安裝依賴與 lint 會產生檔案。
3. **列出啟用中的規則**用 `agent-rules` 的語言頁與腳本，本 skill 不重寫：`agent-rules/references/typescript-eslint.md`、`dart-flutter.md`、`swift-ios.md`、`kotlin-android.md`（路徑相對 `agent-rules` 的安裝目錄）。
4. **文字規則有沒有機器擋**交給 `agent-rules` 第 2 步。
5. **回報**：照層分組，先寫基本盤沒達到的，再寫其他層的現況；每項附腳本的證據欄，自己看過的 `unknown` 寫結論與讀了哪些檔。

## 已知限制

- 只解析 GitHub Actions；GitLab CI 有解析但未實測；Bitrise、Codemagic、Jenkins、CircleCI 等只列出檔案、狀態 `unknown`，裡面的指令沒有列入，相關列可能誤判成 `local-only` 或 `absent`。
- 哪些 job 是 branch protection 的必要檢查，本機檔案看不到；要 `--github`，而 branch protection 需要 admin 權限才讀得到。有 `--github` 時沿必要檢查的 `needs:` 往上算：彙總 job 要帶 `if: always()` 或 `!cancelled()` 才算，因為沒帶時上游失敗會讓彙總 job 被略過，而略過的必要檢查算通過。彙總 job 自己 shell 裡的邏輯（例如允許略過的名單）不判讀。
- Go、Python、.NET 的偵測規則沒有在真實 repo 跑過，輸出備註會標「未實測」。
- 工具認不出的自訂閘門（grep 檢查、索引檢查）只要檔名是 `check-*`、`lint-*`、`verify-*`、`guard-*`、`scan-*` 且由 CI 直接呼叫，會列成「自訂檢查」；它守什麼要讀腳本。
- 判斷「CI 會跑到」靠指令字串比對；動態組出來的指令（變數展開、矩陣值）可能判不出來。

## 不做

- 不打分數、不分等級、不排名。
- 不改目標 repo 的任何檔案，不自動修補；要補哪一層由使用者決定後另外動手。
