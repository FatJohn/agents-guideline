# 寫作原則的出處

開啟日期（全部來源）：2026-10-12，皆以 WebFetch 實際開啟。引文為原文短引，由 WebFetch 回傳內容摘出；個別引文經小模型摘要轉述的，下面以「（摘要）」標示，採用前建議在瀏覽器核對原文。

## 原則 → 出處

編號對應 `SKILL.md` 的 12 條原則。「自訂」指該條的具體做法（固定字樣、格式、判定 regex）是在實際專案改寫時訂出來的，外部來源只提供方向。

| 原則 | 出處 | 備註 |
|---|---|---|
| 1 文件分型 | A1 Diátaxis（how-to 不夾 explanation／reference）、A4 GitLab topic types | 檔頭兩行與型別清單為自訂 |
| 2 正文只寫現況 | A1 explanation（歷史原因屬於 explanation）、A2 timeless、A3 Dead docs、A4 移除過期歷史 | |
| 3 不用時間性與承諾性用語 | A2 timeless documentation、A4 "Do not promise to deliver features in a future release." | 詞表為自訂 |
| 4 正文不放票號與 commit SHA | 自訂；外部旁證 A3（文件與程式碼同步、避免失效資訊） | |
| 5 接入指南從頭照做 | A1 how-to（連結而非夾帶）、B1 Firebase、B2 Auth0（單頁線性步驟加 Next Steps）、B3 AppAuth（README 自足） | |
| 6 首句結論、段落短 | A5 Microsoft scannable content、A6 Write the Docs skimmable、A2 lists | 字數上限只作參考 |
| 7 未發版行為用固定字樣 | A2 timeless（時間詞加版本錨點）、A4 版本標示區塊的固定位置與格式、B3 AppAuth（"introduced in 0.8.0" 就地短句） | 三種位置形式為自訂，目的是讓 CI 可機械檢查 |
| 8 證據等級兩個固定值 | 自訂；外部旁證 A6 "incorrect documentation is worse than missing documentation"（摘要） | |
| 9 引用用章節名稱 | A2 link text、A4 link text、A3 "Link instead" | |
| 10 ADR、CHANGELOG 例外 | A1 explanation（設計決策與歷史原因有專屬位置）、A4 版本歷史是獨立區塊 | ADR 不改寫為常見慣例 |
| 11 共用說明單一權威 | A6 Unique／ARID、A4 "Do not duplicate entries on multiple pages"、B1 Firebase（共用概念放不分平台頁面）、B5 Sentry | 副本頁首格式為自訂 |
| 12 清單與表格 | A2 lists、A5 相似資訊用相同句型 | |

## A. 風格與方法論來源

### A1. Diátaxis
- 首頁 https://diataxis.fr/
  - 「Diátaxis identifies four distinct needs, and four corresponding forms of documentation」（四種：tutorials、how-to guides、technical reference、explanation）。
- How-to guides https://diataxis.fr/how-to-guides/
  - "A how-to guide helps the user get something done, correctly and safely; it guides the user's action."
  - "Typically, the temptations are to explain or to provide reference for completeness." 特徵含 "no digression, explanation, teaching"（摘要）。論點：操作文件不夾說明與完整參考，改用連結。
- Reference https://diataxis.fr/reference/
  - "One hardly reads reference material; one consults it."
  - "The only purpose of a reference guide is to describe, as succinctly as possible, and in an orderly way."
  - "the structure of the documentation should mirror the structure of the product."
- Explanation https://diataxis.fr/explanation/
  - "Explanation is a discursive treatment of a subject, that permits reflection."
  - "explain why things are so - design decisions, historical reasons, technical constraints."（歷史與「為什麼」屬於 explanation，不屬於操作或參考）

### A2. Google developer documentation style guide
- Timeless documentation https://developers.google.com/style/timeless-documentation
  - "Words like now, new, and currently can render such documentation inaccurate, outdated, or unmeaningful."
  - "If you must use words like new, give a reference point such as a date or version release number."
  - 未來功能：避免 "at present"、"eventually" 這類洩漏計畫的詞。
- Link text https://developers.google.com/style/link-text
  - "Write link text that makes sense without the surrounding text."
  - "Don't use phrases such as this document, this article, or click here."
- Lists https://developers.google.com/style/lists
  - 編號清單："A set of items where the sequence is significant, such as ordered steps, phases, or priorities."
  - "Tables and lists are both ways to present a set of similarly structured items."
  - "Use the same syntax/structure for all list items in a given list, if possible."

### A3. Google 工程文件最佳實務（Google Style Guides: Documentation best practices）
- https://google.github.io/styleguide/docguide/best_practices.html
  - "A small set of fresh and accurate docs is better than a large assembly of "documentation" in various states of disrepair."
  - "Dead docs are bad. They misinform, they slow down, they incite despair in engineers and laziness in team leads."
  - "Change your documentation in the same CL as the code change."
  - "Do not write your own guide to a common Google technology or process. Link to it instead."

### A4. GitLab documentation style guide
- Style guide https://docs.gitlab.com/development/documentation/styleguide/
  - 章節「Promising features in future versions」："Do not promise to deliver features in a future release."（要提計畫就連到 issue）
  - 連結文字："Use descriptive text for links, rather than words like `here` or `this page.`"
  - Topic types："Topic types help users digest information more quickly."
- Topic types https://docs.gitlab.com/development/documentation/topic_types/
  - "Each topic on a page should be one of the following topic types:"（concept／task／reference／troubleshooting；細則在各子頁，未開）
  - "Even if a page is short, the page usually starts with a concept and then includes a task or reference topic."
- Availability details（版本歷史）https://docs.gitlab.com/development/documentation/styleguide/availability_details/
  - "Ensure that history notes are listed after the details (if any), and immediately after the heading."
  - "Do not duplicate entries on multiple pages. Add the entry to the page that documents the feature that changed."
  - "Remove history items and inline text that refer to unsupported versions."
  - 論點：版本歷史是獨立、格式固定的區塊，連到 issue；過期的歷史會被移除。

### A5. Microsoft Writing Style Guide：Scannable content
- https://learn.microsoft.com/en-us/style-guide/scannable-content/
  - "Write short headings, short sentences, and short paragraphs that are easy to read".
  - "Three to seven lines is about the right length for a paragraph."
  - "Lead with what's most important. Place important keywords near the beginning of headings, table entries, and paragraphs so they're easy to spot."
  - "Apply the same sentence structures to similar information."

### A6. Write the Docs
- Docs principles https://www.writethedocs.org/guide/writing/docs-principles/
  - ARID："Accept (some) Repetition In Documentation."（摘要）
  - Skimmable："Save your readers' time by writing like a newspaper instead of a novel."
  - Unique："Eliminate content overlap between separate sources."（摘要）
  - "Consider incorrect documentation to be worse than missing documentation."（摘要）
- Docs as code https://www.writethedocs.org/guide/docs-as-code/
  - "writing documentation with the same tools as code."
  - "You can block merging of new features if they don't include documentation."

## B. 接入文件結構實例

### B1. Firebase Authentication
- URL：https://firebase.google.com/docs/auth 、Flutter 起步頁 https://firebase.google.com/docs/auth/flutter/start
- 切平台：一個平台一份。側欄每個平台（iOS+、Android、Flutter、Web、C++、Unity、Admin）各自有 `/docs/auth/<platform>/start`，其下再有各 provider 的平台專屬頁。
- 共用概念：放在不分平台的頁面（Introduction、Where do I start?、Users in Firebase Projects、Usage Limits、FAQ and troubleshooting）。
- 單頁結構（Flutter start）：Connect your app to Firebase（前置）→ Add Firebase Authentication to your app → Enable a sign-in provider → (Optional) Local Emulator Suite → Check current auth state → Persisting authentication state → Next Steps。選配步驟標「(Optional)」。
- 平台差異／限制：在同一頁內用散文與程式碼註解就地標，例如 "On native platforms such as Android & iOS, this behavior is not configurable."；沒有版本徽章。

### B2. Auth0 Flutter quickstart
- URL：https://auth0.com/docs/quickstart/native/flutter
- 切平台：以「SDK」為單位，一份涵蓋 Android／iOS／macOS；Flutter Web、Windows 另有獨立 quickstart，用 callout 連出去。
- 頁內平台差異：步驟 3、4 用 Android／iOS／macOS 分頁籤（tabs）。
- 結構：前置條件（含最低版本）→ 七個編號步驟（建專案、裝 SDK、設定 Auth0 app、設定應用、實作登入登出、顯示 profile、執行）→ Checkpoint → Troubleshooting & Advanced Usage → Next Steps。
- 版本／限制：寫在前置條件，如 "Universal Links require iOS 17.4+ or macOS 14.4+. Older versions fall back to custom URL schemes."（摘要）

### B3. AppAuth-Android／AppAuth-iOS（OpenID 官方，同協定 SDK，與 OAuth／OIDC SDK 文件最相近）
- URL：https://github.com/openid/AppAuth-Android 、https://github.com/openid/AppAuth-iOS
- 切平台：兩個 repo 兩份 README，彼此不互相提及；各自完整自足。
- Android README 順序：Download → Requirements → Demo app → Conceptual overview → Implementing the authorization code flow（子節：設定、取 code、換 token、用 token、登出、狀態持久化）→ Advanced configuration → Dynamic client registration → Utilizing client secrets (DANGEROUS) → Contributing。
- iOS README 順序：Specification（含 iOS／macOS／tvOS 的 Supported Versions 與 Authorization Server Requirements）→ Try → Setup → Auth Flow → API Documentation → Included Samples。API 參考以產生的 API 文件網站承擔，README 只放連結。
- 版本／限制：最低版本寫在 Requirements／Supported Versions；限制就地一句話標示，如 "`UIWebView` and `WKWebView` are explicitly _not_ supported."、"ID Token validation was introduced in `0.8.0`"。

### B4. Stripe：Accept a payment
- URL：https://docs.stripe.com/payments/accept-a-payment?platform=ios
- 切平台：同一篇文章，多個變體；以 URL 參數（`payment-ui`、`platform=ios|android|react-native`）切換，每個變體是獨立的線性內容（頁首 Index 列出所有變體）。
- 備註：只抓到索引區塊，未取得單一變體內的步驟與限制標法，不據以下結論。

### B5. Sentry 平台文件
- URL：https://docs.sentry.io/platforms/
- 切平台：每個平台一個區塊，框架歸在所屬平台之下；跨平台內容放獨立的 Documentation 區（Get Started、Concepts & Reference、API Reference）。
- 備註：頁面未顯示共用概念是否在各平台頁重複，不據以下結論。

## C. 結論

1. 各家主流是「一個平台（或一個 SDK）一份接入指南」加「不分平台的共用概念／限制頁」。Firebase、Sentry、AppAuth 都這樣切；Auth0 在同一 SDK 內用 tabs 處理子平台差異；Stripe 用同一篇文章的變體。沒有人把 Web 與 App 的接入塞在同一份線性文件。
2. 版本需求寫在文件開頭的前置條件／Requirements；功能引入版本與限制就地一句話標示，不開歷史章節。
3. 歷史與決策理由屬於 explanation（Diátaxis）或獨立的版本歷史區塊（GitLab），不在操作與參考文件的正文裡。
4. 大家都避免時間性用語與未來承諾（Google、GitLab）。

## D. 打不開或不足的項目

- 全部列出的 URL 都已成功開啟。
- Diátaxis 首頁本身沒有四種形式的定義與「不要混用」的論述，已改引子頁。
- GitLab topic types 頁只列出類型、各類型定義在子頁，沒再往下開。
- Stripe、Sentry 只取得結構索引（見 B4、B5）。
- Microsoft 繁體中文風格指南、Sentry／Stripe 的版本標示寫法未查到，不引用。
