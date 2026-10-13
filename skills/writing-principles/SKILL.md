---
name: writing-principles
description: 寫或改長存文件時使用——README、接入指南（quickstart／integration）、架構或設計說明、開發與發版流程、參考頁、wiki 頁（如 ClickUp、Confluence），新寫、改寫、整理都算；驗收這類文件時 verifier 也用本 skill 的判定與檢查腳本。觸發詞：寫文件、改寫 README、整理 docs、文件太亂、接入指南、架構說明、"rewrite the docs"、"doc cleanup"。不用於程式註解、commit message、PR 描述、issue、ADR、CHANGELOG，以及本工作系統的 rules／agent 定義／skill（那些走 maintain-guideline）。
allowed-tools: Bash(python3:*), Bash(git:*), Read, Grep, Glob
---

# Writing Principles — 長存文件的寫作原則與檢查

12 條原則，每條有「判定」：能機械判的由 `scripts/check_docs.py` 判，需要人判的寫明 verifier 怎麼抽樣。寫的人與 verifier 跑同一支腳本、看同一份判定。原則來源是 Diátaxis、Google／GitLab／Microsoft 風格指南與 Write the Docs（短引在 `references/sources.md`），加上在實際專案改寫四個 repo 與 wiki 頁後驗證過的固定字樣。`<SK>` 指本 skill 的目錄（安裝後通常是 `~/.claude/skills/writing-principles` 或 `~/.agents/skills/writing-principles`）。

## 何時用／不用

- 用：新寫或改寫 README、接入指南、設計／架構說明、流程文件、參考頁、wiki 頁；驗收這類文件；專案要訂自己的文件規則時（先套本 skill，再在專案 AGENTS.md 加專案自訂值，見「專案自訂」）。
- 不用：程式註解、commit message、PR／issue 描述、ADR、CHANGELOG（它們就是放歷史與票號的地方，原則 10）；本工作系統自己的 rules／agents／skills（走 `maintain-guideline`）；一次性的分析報告或交付包。

## 流程（寫文件時）

1. 先定型別（原則 1），一份文件一型；檔頭寫 `讀者：`／`型別：`。
2. 寫完跑 `python3 <SK>/scripts/check_docs.py --repo <repo>`（範圍、設定見「檢查腳本」），機械項歸零；提示項（p4h、p6）逐條看，該改就改。
3. 交付時附 SUMMARY 行與 `--exclude` 清單（原則 10：預設排除以外的每一個排除都要在 PR 說明）。
4. 驗收由 fresh-context verifier 重跑同一指令並對 verifier 判定項抽樣（見「驗收怎麼用」）。

## 原則與判定

每條的判定標 `[腳本 pN]`（機械項，腳本印出命中行；`[腳本 --list]` 指掃描範圍由 `--list` 印出）或 `[verifier]`（人判項，抽樣或寫明可判定的條件）。

### 1. 文件分型，一份文件只做一件事
- **原則**：每份文件屬於 接入指南／參考／說明／流程／規則／入口 之一（專案可用設定 `TYPES` 增加型別），標題之下兩行依序宣告讀者與型別，內容不跨型。
- **判定**：
  1. `[腳本 p1]` 第一個 `# ` 標題之後（副本的 `> 本文件為副本…` 行跳過）前兩個非空行依序為 `讀者：…`、`型別：<型別>`；缺漏檔數 0。
  2. `[腳本 p1b]` 型別為接入指南的檔，H2 不含 `設計`、`架構`、`為什麼`、`決策`、`取捨`；型別為說明的檔，H2／H3 不含「步驟」。
  3. `[verifier]` 內容不跨型（說明文件裡沒有操作步驟、接入指南裡沒有設計理由）。
- **例外**：入口（README）可同時有簡介與快速開始，各為獨立 H2，快速開始不超過一個編號清單；設定 `NO_HEADER` 列的檔免檔頭（例如只含 `@AGENTS.md` 的 CLAUDE.md、PR template、框架範本自帶的 README）。

### 2. 正文只寫現況，歷史不進正文
- **原則**：正文只描述現在怎麼運作、怎麼用；過去怎樣、改過什麼交給 CHANGELOG、PR、ADR、票。
- **判定**：`[腳本 p2]` 命中 `原本|後來改成|後來改為|之前是|舊版|曾經|已改為|改版前|不再支援|取代了` 的行數 0（設定 `HISTORY_WORDS` 可覆寫詞表；比對前先剔除原則 3 所列的 `IGNORE_WORDS` 複合詞）。「某版本以下不支援」是現況，寫成「需要 vX.Y.Z 以上」。
- **例外**：原則 10 的 ADR 與 CHANGELOG。

### 3. 不用時間性與承諾性用語
- **原則**：不寫會隨時間失真的詞、不承諾未來；需要時間錨點寫版本號或日期（「自 vX.Y.Z 起」「需要 vX.Y.Z 以上」）；待辦放 issue 或票。
- **判定**：`[腳本 p3]` 命中 `目前|現在|最新|最近|即將|未來|之後會|將會|預計|規劃中|待實作|暫時|新增的|全新` 的行數 0（設定 `TIME_WORDS` 可覆寫）。中文沒有詞界，「出現在」含「現在」這類複合詞會誤報；專案可在設定檔用 `IGNORE_WORDS`（以 `|` 分隔的**字面詞**，不是 regex，例如 `出現在|呈現在`）列出比對前先剔除的複合詞，預設為空、不剔除；每項必須含詞表內的某個觸發詞且比它長，否則腳本 exit 2（擋住 `.`、`前`、`目前` 這類會讓檢查靜默歸零的值）。代價是已知漏抓：與剔除詞匹配範圍重疊的時間詞都不會命中（`IGNORE_WORDS=出現在` 下「指出現在的流程」不會命中），所以清單只收專案文件真的常用的複合詞，verifier 核對設定檔時逐條看（見「驗收怎麼用」）。
- **例外**：原則 7 的固定字樣含「尚未發版」，不在此詞表；引用外部原文（錯誤訊息、他人文件標題）的行在行尾加 `<!-- allow-time-word -->`，腳本另計 `p3-allow` 數，交付時逐檔列出給 verifier。

### 4. 正文不放票號與 commit SHA
- **原則**：說明不靠票號或 SHA 撐住；來源追溯交給 ADR、CHANGELOG、PR。
- **判定**：
  1. `[腳本 p4t]` 票號命中 0——設定 `TICKET_RE` 指定專案的票號樣式（例如 `PROJ-[0-9]+`）；未設定時用通用樣式 `[A-Z][A-Z0-9]{1,9}-[0-9]+`（前後不得緊接英數字）並排除 ISO／RFC／SHA／UTF／CVE 等常見非票號前綴，誤報多就設 `TICKET_RE`。
  2. `[腳本 p4c]` `commit/<hex>`、`blob/<hex>` 連結 0。
  3. `[腳本 p4h]` **提示**：7–40 位 hex 字串逐條看，只能是版本號、雜湊值範例或程式碼範例。
- **例外**：ADR、CHANGELOG；副本頁首的權威來源連結（原則 11，腳本不對該行檢查 p4）。

### 5. 接入指南從頭照做，不必開別份文件
- **原則**：接入指南的步驟區自足——前置條件、每一步、驗證方式都在同一份；補充資料放文末「參考」或「下一步」。
- **判定**（只對型別為接入指南的檔）：
  1. `[腳本 p5]` 第一個 H2 起、扣掉標題含 `參考|下一步|延伸閱讀|相關文件|Next` 的 H2 區段後，不得出現 `同上|如前述|請參考|見〈`，也不得有指向 repo 內 `.md` 或設定 `DOC_HOST_RE`（wiki 網域）的連結；命中 0。第一個 H2 之前的導言不受限（共用概念只留一句話加連結就放這裡，原則 11）。
  2. `[verifier]` 步驟用編號清單，每個編號項只做一個動作。
- **例外**：前置條件中的外部官方文件（平台開發者網站、主控台）可連，列在前置條件的清單內。

### 6. 每段第一句是結論，段落與表格格保持短
- **原則**：先講結論再講原因；段落短，細節用清單或表格承載。
- **判定**：
  1. `[腳本 p6]` **提示**：列出超過參考上限的位置——段落 5 句或 220 字、單句 80 字、表格單格 60 字——只作提示，不計 FAIL；verifier 只在超限段落**同時**符合下列任一形狀時判 FAIL：(a) 散文中以「、」或「；」並列 3 個以上同構項目（應改清單或表格，原則 12）；(b) 一段內含 2 個以上以「若」「如果」「當」開頭的獨立條件分支。
  2. `[verifier]` 每個 H2 的第一句抽樣 5 處，判是否為結論句（含動詞與對象，不是背景鋪陳）。
- **例外**：程式碼區塊與 ADR 引文不計。

### 7. 未發版行為用固定字樣
- **原則**：任何只在主幹成立、已發佈版本沒有的行為，用專案自訂的一句固定字樣（設定 `UNRELEASED_PHRASE`）標示，一字不差，依範圍擇一放在三種位置：(a) 整節成立——H2／H3 標題下一行單行 blockquote `> <字樣>。`；(b) 單一表格列、清單項或單句——該列／項／句尾 `（<字樣>）`；(c) 程式碼區塊內註解 `// <字樣>`。已發版的功能不標，版本需求寫「需要 vX.Y.Z 以上」。
- **判定**：
  1. `[腳本 p7]` 命中 `尚未發版|尚未發佈|未發佈|未發版|僅 main|only on main|unreleased|未釋出`（英文不分大小寫）的每一行必須含 (a)(b)(c) 之一；不符 0。未設定 `UNRELEASED_PHRASE` 時所有命中都算不符（腳本會提示要設定）。
  2. `[腳本 p7a]` (a) 型必須緊接在 H2／H3 之後、中間只隔一個空行；不符的 (a) 型行逐行列出。
- **例外**：CHANGELOG 的 Unreleased 區段。

### 8. 證據等級用兩個固定值
- **原則**：凡宣稱「在某環境能跑／會失敗」，只用 `已實測（YYYY-MM-DD，環境）` 與 `未實測` 兩種標法，放在限制表的「驗證」欄；讀碼可確認的結構事實直接寫成事實，行為宣稱實跑過才標已實測，讀碼不算實跑；不寫「推論」「讀碼推論」「未驗」這類來源標示。
- **判定**：
  1. `[腳本 p8]` 排除標題行後，命中 `實測|驗證過|已測|測過|有測|未測|沒測|應該可以|理論上|預期可|未驗(?!簽)|推論` 的行，去掉合格寫法 `已實測（\d{4}-\d{2}-\d{2}，[^）]+）` 與 `未實測` 後仍含觸發詞者為不符；不符 0（「未驗簽」指 token 未驗簽章，不算）。
  2. `[verifier]` 已實測必有日期與環境（裝置或系統版本）；未實測的條目不得同時寫成肯定句，寫「X 的行為：未實測」；一句涵蓋多個平台時逐平台各自標。
- **例外**：ADR 的當時證據保留原貌。

### 9. 引用別份文件用章節名稱，連結文字要自己看得懂
- **原則**：交叉引用寫「〈文件名〉的〈章節名稱〉」，不寫 commit SHA、行號或「這裡」；連結文字描述目的地。
- **判定**：
  1. `[腳本 p9a]` `(請見|詳見|見)(這裡|此處|本文件|該文件)|點此|這份文件|click here`（英文不分大小寫）命中 0。
  2. `[腳本 p9b]` `#L[0-9]+` 行號錨點命中 0（commit／blob 連結歸 p4c）。
  3. `[腳本 p9c]` 指向 repo 內檔案的相對連結，目標檔必須存在；帶 `#anchor` 時目標（或本檔）必須有對應標題（GitHub slug：小寫、去標點、空格換 `-`，重複標題依序加 `-1`、`-2`）；不存在 0。含 `://` 的外部連結與行內程式碼（反引號內）不檢查。
  4. `[verifier]` 連結文字含目的地文件名或章節名。
- **例外**：外部 RFC 或官方文件，連結文字用文件標題即可。

### 10. ADR、CHANGELOG 的例外與掃描範圍
- **原則**：歷史、取捨、被否決的方案、票號與 commit 的歸處是 ADR、CHANGELOG（以及 PR、票）；正文談決策理由時一句結論加連到 ADR 章節名稱，不重述。
- **判定**：
  1. `[腳本 --list]` 腳本預設範圍是 `git ls-files '*.md'` 扣掉路徑含 `changelog`（不分大小寫）與 `docs/adr/` 的檔；其他排除用 `--exclude`（或設定 `EXCLUDE`），**每一個都要在 PR 逐條說明**；`[verifier]` 對照 `--list` 輸出與 PR 的排除說明，未說明的排除判 FAIL。
  2. `[verifier]` ADR 不改寫、CHANGELOG 只追加（diff 只允許新增檔、改狀態欄、修錯字連結）。
- **例外**：無。

### 11. 共用說明單一權威，副本逐字一致並連回
- **原則**：每個共用概念（流程總覽、錯誤碼對照、名詞）只有一個權威版本（位置由專案指定：wiki 頁或 repo 內某檔）；其他文件對同一概念不超過 3 行並連到權威版；需要在別的 repo 留副本時，副本頁首固定一行指向權威版，內文逐字相同。
- **判定**：
  1. `[腳本 p11]` 第一個 `# ` 標題後第一個非空行以 `> 本文件為副本` 開頭的檔，該行必須完全符合 `> 本文件為副本，權威版：[<標題>](<URL>)。副本同步日：YYYY-MM-DD。`；不符 0。
  2. `[verifier]` 副本去掉頁首區塊後與權威版正規化後 `diff` 為空——正規化腳本由專案提供（wiki 匯出格式各異），verifier 實跑；專案沒提供正規化腳本時直接對原文 `diff`，不為空即 FAIL，不判 UNSURE；副本之間兩兩 diff 也為空。
  3. `[verifier]` 非權威文件對同一概念的篇幅 ≤3 行且含連結；副本不含只在該 repo 成立的平台專屬段落。
- **例外**：無。

### 12. 清單與表格各有用途
- **原則**：有順序用編號清單，無順序的同構項目用項目符號，多屬性的同構項目用表格；單一項目不做清單；同一清單句型一致。
- **判定**：
  1. `[腳本 p12]` 只有一個項目的清單數 0（程式碼區塊內不計；巢狀項目、項目間空行、縮排在項目內的程式碼區塊都算同一份清單；`* * *` 這類分隔線不是清單；頂層清單換了種類——項目符號↔編號——算新的一份）。
  2. `[verifier]` 標題含「步驟」的區段下的清單是編號清單。
  3. `[verifier]` 3 個以上、每項 2 個以上屬性的項目不得以散文並列，抽樣 5 處。
  4. `[verifier]` 同一清單項目開頭詞性一致，抽樣判定。
- **例外**：無。

## 掃描範圍、例外與 allow marker

- 預設範圍與排除見原則 10；`--exclude` 必列 PR；明列 FILE 參數時只掃那些檔，不套預設排除。
- 唯一的行內 allow marker 是原則 3 的 `<!-- allow-time-word -->`；其他原則沒有 marker——命中就是改寫，不是標記。
- wiki 頁的讀回檔（頁名不在內文、沒有 `# ` 標題）用 `--headerless` 掃，檔頭取檔案最前兩個非空行。

## 專案自訂

- 設定檔 `<repo>/.writing-principles.conf`（腳本自動讀；`--config` 可指定別的路徑），一行一個 `KEY=VALUE`，`#` 開頭是註解，**不會被 source／eval**，未知的鍵會在 stderr 警告後忽略。鍵：`TYPES`（以 `|` 分隔的額外型別）、`NO_HEADER`（空白分隔的免檔頭路徑，可用 glob）、`TICKET_RE`、`UNRELEASED_PHRASE`、`DOC_HOST_RE`、`EXCLUDE`（空白分隔的 glob）、`HISTORY_WORDS`、`TIME_WORDS`（兩者覆寫預設 regex）、`IGNORE_WORDS`（比對 p2／p3 前先剔除的字面複合詞，`|` 分隔，每項須含觸發詞且比它長；預設空＝不剔除；已知漏抓形狀見原則 3）。旗標與設定檔並用時，單值鍵（`TICKET_RE`、`UNRELEASED_PHRASE`、`DOC_HOST_RE`）以旗標為準，清單型（`TYPES`、`NO_HEADER`、`EXCLUDE`）兩邊合併。
- 範例：

  ```
  # <repo>/.writing-principles.conf
  TYPES=教學
  NO_HEADER=CLAUDE.md .github/pull_request_template.md
  TICKET_RE=PROJ-[0-9]+
  UNRELEASED_PHRASE=僅在主幹，尚未發版
  DOC_HOST_RE=wiki\.example\.com
  EXCLUDE=vendor/*
  IGNORE_WORDS=出現在|呈現在
  ```

- 專案 AGENTS.md／CLAUDE.md 該寫什麼：指向本 skill；列設定檔的值與理由；專案額外規則（例如「一個平台一份接入指南」、共用說明的權威位置、哪些檔只能改排版不能改規則）寫在專案文件，**不改本 skill**；專案規則與本 skill 衝突時專案規則優先（優先權排序見全域 CLAUDE.md「優先權排序」節；Codex 端見全域 AGENTS.md「Codex 專用注意」末條）。

## 檢查腳本

- 用法：`python3 <SK>/scripts/check_docs.py [--repo DIR] [--config FILE] [--exclude GLOB]… [--ticket-re RE] [--unreleased-phrase TEXT] [--types A|B] [--no-header PATHS] [--headerless] [--doc-host-re RE] [--list] [FILE…]`；`--repo` 預設 cwd，`--list` 只印掃描範圍。
- 輸出：第一行 `掃描檔：N 個（…）`、第二行 `設定檔：…；詞表覆寫：…`；每個有命中的原則一段 `== pN …`，內容為 `path:line: 內容`；`== 提示（不計入 FAIL）` 段放 p4h、p6；最後 `SUMMARY …` 與 `RESULT PASS|FAIL`。exit code：0 無 FAIL 項、1 有、2 用法或環境錯（含掃描範圍為空）。
- 純 Python 3 標準庫，不需 rg；專案不是 git repo、或 git 沒有任何已追蹤的 md 時改走目錄遍歷（跳過 `.git/`、`node_modules/`）。
- 紅綠證據：`cd <REPO> && python3 -m unittest tests.test_writing_principles_check -v`；樣本在 `<REPO>/tests/fixtures/writing-principles/{pass,fail}`，`fail/` 每個原則一檔，直接跑 `python3 <SK>/scripts/check_docs.py --repo <REPO>/tests/fixtures/writing-principles/fail` 可看到每個原則的命中長什麼樣。

## 驗收怎麼用（給 verifier）

`rubrics/document-quality.md` §6 指到這裡。verifier 自己重跑腳本（派工者附的輸出只當線索），SUMMARY 貼回報；機械項以腳本為準；`[verifier]` 項各抽樣 5 處；派工者附的 `--exclude` 清單與 `p3-allow` 逐檔清單要逐條有說明，沒有說明的判 FAIL。 腳本輸出第二行印出用了哪個設定檔與覆寫了哪些詞表；有覆寫 `TIME_WORDS`、`HISTORY_WORDS`、`IGNORE_WORDS` 時 verifier 逐條核對覆寫值：拿掉原詞表的詞、`IGNORE_WORDS` 的某項不是該專案文件實際出現的複合詞、或拿掉該項就等於放行一個時間詞（如 `目前的`），沒有逐條理由就判 FAIL（設定檔是專案可改的，腳本只擋得住不含觸發詞的項目）。

## 改寫前後

完整的三組片段（README 首段、名詞節、表格拆分）在 `references/examples.md`。最短的例子——檔頭與首段：

```markdown
<!-- 改寫前 -->
# api-login-web

目前登入頁已接上社群登入，Apple 按鈕暫時維持 disabled（細節見[這裡](docs/flow.md)）。

<!-- 改寫後 -->
# api-login-web

讀者：開發者、SRE
型別：入口

登入頁接上 Google、Facebook、LINE 的社群登入；Apple 按鈕為 disabled，需要 api v2.1.0 以上才有 Apple 的 start 端點。流程見 [docs/flow.md 的〈登入流程〉](docs/flow.md#登入流程)。
```

對應原則：1（加檔頭）、3（「目前」「暫時」換成版本錨點）、9（連結文字寫目的地）。

## 檔案

- `scripts/check_docs.py`：機械檢查，純標準庫。
- `references/sources.md`：各原則的出處短引與開啟日期。
- `references/examples.md`：改寫前後對照片段（已去識別化）。
- `<REPO>/tests/fixtures/writing-principles/`：`pass/` 與 `fail/` 樣本。
- `<REPO>/tests/test_writing_principles_check.py`：腳本的斷言。
