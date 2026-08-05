---
name: create-pr
description: Use when the user wants to create a Pull Request from the current branch. Triggers include Chinese phrases like 「建立 PR」「產生 PR」「開 PR」「幫我開一個 PR」「發 PR」「送 review」 and English equivalents like "create a PR", "open a pull request", "make a pull request". Also trigger on implicit ship-it cues like 「可以開了」「差不多可以送出」「ship it」 when the current branch is clearly diverged from its base branch.
allowed-tools: Bash(git:*), Bash(gh:*), Bash(mktemp), Bash(cat), Bash(rm:*), Read, Write
---

# Create PR

分析 branch 變更、生成描述、建立 Pull Request。適用任何 repo；先偵測該 repo 的 base branch 與 PR template 再生成，不假設特定 stack。**PR 標題與描述預設一律使用繁體中文台灣用語（技術名詞與程式碼識別字保留原文）；標題採一句摘要主題，不用 Conventional Commits 或任何 prefix。**

## 1. 核心原則

**描述的粒度是「功能概念」而非「class/method」**——reviewer 需要理解的是設計意圖和實作方向，細節應該自己看 code。

**每個描述條目回答「做了什麼 + 為什麼」**：

```
Bad -- 只有 what：
- 新增 DailyAnimationPhase enum

Good -- what + why：
- 引入 DailyAnimationPhase enum 以狀態機模式管理動畫流程，
  將原本難以追蹤的多階段動畫拆分為明確的 challenge/reward 兩個階段

Bad -- 逐一列出每個 class：
- ImageUploadJob: 提取 _createDio() 私有方法
- ImageUploadJob: 提取 _performUpload() 私有方法

Good -- 同一概念的變更聚合描述：
- 重構 ImageUploadJob 上傳邏輯，提取私有方法並優化重試機制，
  解決原本過長的 execute() 方法難以閱讀和測試的問題
```

**有明確主軸時，融合敘述而非分區**：

當 PR 圍繞單一主軸（例如「實作某功能」、「修某 bug」），實作過程中順手做的重構、bug 修復、附帶調整都是「為了完成主軸而做的」，應作為實作細節融入主敘述條目，**不要**獨立為 Refactoring / Bugfixes 區塊。獨立分區會讓 reviewer 誤以為那些是與主題無關的副作用，反而模糊了 PR 的整體意圖。

只有當變更彼此並列、沒有共同主軸（例如雜項修補 PR）時，才以分類區段（Features / Bugfixes / Refactoring / Breaking Changes）呈現。分類以「目的」為準：為了新功能 → Features；為了修 bug → Bugfixes；純品質改善、行為不變 → Refactoring；其他模組需要改 code 才能運作 → Breaking Changes。

**篇幅隨變更規模縮放**：小 PR（幾十行內）只需 Summary＋兩三個條目；大 PR 才展開完整段落。判準：拿掉某段不會讓 reviewer 變慢，就拿掉。

**明寫 trade-off 與刻意不做的事**：如果實作中做了取捨（「考慮過 X 但決定不做，因為 Y」）或刻意 deferred 某範圍，在 body 中明說，避免 reviewer 誤以為是遺漏。

**忽略不影響邏輯的變更**：生成檔案（lock files、`*.g.dart`／`*.freezed.dart` 等 codegen 產物、build 輸出）、純格式化、單純的 import 重排等，不寫進描述。

## 2. 流程

### 2.1 確認 PR 目的

檢查使用者是否有提供 PR 目的。有的話以目的為主軸串連所有變更；沒有的話從 diff 推斷。

建議使用者在開 PR 前先跑該 repo 的檢查慣例（lint / type-check / test，或專案自帶的 pre-commit skill）；本 skill 不主動代跑，避免重複工作。

### 2.2 偵測 repo 慣例

生成任何內容前，先偵測兩件事：

```bash
# (a) base branch：預設取 origin 的 HEAD；使用者指定則優先。
# --short 輸出 origin/main，再去掉 origin/ 前綴得到裸分支名；後續 2.3、2.7 都用這個 $BASE
BASE="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
[ -n "$BASE" ] || BASE="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"

# (b) PR template：找到就以它為 body 骨架
ls .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md \
   docs/pull_request_template.md PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null   # 多 template 目錄，有的話問使用者選哪個
```

title 風格與語言不必偵測、不跟隨 repo 近期慣例，一律照下列固定規則：

- **title 風格（固定）**：一句簡潔摘要主題，直接描述這個 PR 做了什麼，**不用 Conventional Commits（`feat:`／`fix(scope):` 等）、也不加 ticket 或任何 prefix**。
- **語言（固定）**：PR 標題與描述一律使用**繁體中文台灣用語**，技術名詞與程式碼識別字（class／method／API 名等）保留原文。唯一例外：使用者當下明確要求改用其他語言時才跟隨。

使用者指定 base branch 時，改設 `BASE="<使用者指定的名稱>"`，並先驗證名稱合法（白名單字元＋確認為實際存在的 ref），避免 shell injection：

```bash
case "$BASE" in
  *[!a-zA-Z0-9._/-]*) echo "invalid base branch name" >&2; exit 1 ;;
esac
git rev-parse --verify "origin/$BASE" >/dev/null || { echo "no such ref: origin/$BASE" >&2; exit 1; }
```

### 2.3 取得 diff

以 remote 上的 base 為比較基準（本地同名 branch 可能過時或不存在）：

```bash
git diff "origin/$BASE"...HEAD
git diff --name-only "origin/$BASE"...HEAD
```

### 2.4 分析與分類

從 diff 中識別功能概念層級的變更。先判斷 PR 是否有明確主軸：

- **有單一主軸**：以主軸串連所有條目，實作過程的重構、修補、附帶調整融入條目敘述，不獨立分區。Body 結構就是「Summary」＋一組條列敘述。
- **多項並列、無共同主軸**：以分類區段（Features / Bugfixes / Refactoring / Breaking Changes）呈現；沒有 Breaking Changes 則標示「無破壞性變更」。

無論哪種寫法，每條都聚焦「功能概念」與「為什麼這樣做」，不列檔案路徑（例外：配置檔案如 `pubspec.yaml`／`package.json`、整個模組的新增或移除可提及路徑）。

### 2.5 生成 Summary 與 Title

- **Summary**：2-3 句概述。有 PR 目的時以目的為主軸；重要功能移除必須在 Summary 說明。
- **Title**：一句簡潔摘要主題，直接描述這個 PR 做了什麼，不用 Conventional Commits（`feat:`／`fix:` 等）或 ticket prefix；語言用繁體中文台灣用語，技術名詞保留原文。

### 2.6 組裝 PR Body

- **repo 有 PR template**：以 template 為骨架，將 Summary、變更條目、測試建議填入對應段落；template 中不適用的段落保留標題、填「N/A」或簡短說明，不要整段刪除。
- **無 template**：使用內建骨架——

  ```markdown
  ## Summary
  （2-3 句概述）

  ## 主要變更
  （條列，每條 what + why）

  ## 設計決策            <!-- 選配：有 trade-off 或刻意不做的事才寫 -->

  ## Verification
  （只列「實際執行過」的指令與關鍵輸出，例如「flutter test: 21/21 passed」
   「tsc --noEmit: clean」。沒跑過任何驗證就誠實寫「未執行自動驗證」，
   不得寫「測試通過」之類無憑據的空話。）
  ```

- **選配 `## Related PRs`**：跨 repo 協同變更（如 monorepo 外的配套 PR）時，列出相關 PR 連結與建議合併順序。

### 2.7 確認並建立 PR

1. 展示建議的 Title、Base Branch、PR Body 完整預覽。
2. 取得使用者明確同意後才執行（建立 PR 是對外動作；使用者猶豫時可建議 `--draft`）：

```bash
# 推送 branch（第一次推送加 -u 建立 tracking）
git push -u origin HEAD

# PR body 走暫存檔傳入，避免 shell 多行字串轉義問題。
# mktemp 不帶 template 參數，跨平台（BSD/GNU）行為最穩
PR_BODY_FILE="$(mktemp)"
cat > "$PR_BODY_FILE" << 'PR_BODY_EOF'
（實際的 PR body 內容）
PR_BODY_EOF

gh pr create --title "（實際的 PR title）" --base "$BASE" --body-file "$PR_BODY_FILE"

rm -f "$PR_BODY_FILE"
```

3. 輸出 PR URL。

## 3. 完整輸出範例

### 範例 A：有單一主軸（融合敘述）

**Title**: `實作 Wishlist 投票功能`

**Summary**: 實作 Wishlist 投票功能：使用者可在 Settings 頁面看到正在進行的投票 banner 並開啟投票 dialog；同時在 AI Chat 完成食物分析後主動詢問使用者參與投票（每個 voteId 只通知一次）。

**主要變更**（不分區，以條列敘述涵蓋所有實作細節）：
- 新增 `ApiWishlist` 與 `VoteDetail` model，提供取得投票、送出投票、送出文字 feedback 三個 endpoint；同時統一強化 API 層初始化的錯誤邊界，避免 API client 建立失敗時整個 caller 流程崩潰
- Settings 頁面新增 wishlist banner，由 settings 專用的 `WishlistBannerNotifier` 持有 banner detail（page-scoped autoDispose），點擊 banner 直接以快取 detail 開啟 `WishlistDialog`
- AI Chat 完成食物分析後自動詢問使用者投票，並用 prefs 記錄已通知的 voteId 確保只通知一次。此處改用 `wishlistProvider` 上不寫 state 的 `fetchWishlist` 進行一次性查詢，避免「banner state」與「一次性查詢」這兩種無關職責共用同一個 autoDispose Notifier 而引發 `UnmountedRefException`

### 範例 B：多項並列（分類區段）

**Title**: `更新登入流程與相關 bug 修復`

**Summary**: 本次變更實作社交媒體登入功能，支援 Google 和 LINE 登入。同時順帶修正了與本次功能無關的 email 格式驗證 bug。

**Features**:
- 新增 Google 和 LINE 社交登入，整合 Firebase Auth token 交換與後端 session 同步，讓使用者有更多登入選擇

**Bugfixes**:
- 修正 email 格式驗證過於嚴格的問題，原本正規表達式會誤判含加號的有效 email，改用 RFC 5322 相容的驗證方式

**Breaking Changes**:
無破壞性變更
