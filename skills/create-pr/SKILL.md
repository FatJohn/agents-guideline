---
name: create-pr
description: Use when the user wants to create a Pull Request from the current branch. Triggers include Chinese phrases like 「建立 PR」「產生 PR」「開 PR」「幫我開一個 PR」「發 PR」「送 review」 and English equivalents like "create a PR", "open a pull request", "make a pull request". Also trigger on implicit ship-it cues like 「可以開了」「差不多可以送出」「ship it」 when the current branch is clearly diverged from its base branch.
allowed-tools: Bash(git:*), Bash(gh:*), Bash(find:*), Bash(ls:*), Bash(test:*), Bash(grep:*), Bash(sed:*), Bash(wc:*), Bash(cd:*), Bash(echo:*), Bash(mktemp:*), Bash(cat:*), Bash(rm:*), Read
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
# --short 輸出 origin/main，再去掉 origin/ 前綴得到裸分支名；後續 2.3、2.6、2.7 都用這個 $BASE
BASE="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
test -n "$BASE" || BASE="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"

# (b) PR template：GitHub 只認三個位置（repo 根、docs/、.github/），檔名大小寫不敏感，
# 所以用 -iname 一次找完，不要逐一 ls 固定字串（會漏掉 docs/ 與大小寫變體）
# 一律先切到 repo 根：從子目錄跑 find 會 0 筆命中，被誤判成「這個 repo 沒有 template」
cd "$(git rev-parse --show-toplevel)"
# .github／docs 不存在時 find 會回非 0 exit code（stderr 已導掉），那是正常的不是偵測失敗，一律以 stdout 有無輸出為準
find .github docs . -maxdepth 1 -iname 'pull_request_template*' 2>/dev/null
```

偵測結果的四種處置：

- **命中檔案** → 以它為 body 骨架（見 2.6）。
- **命中目錄** → 該 repo 有多份 template。多 template 目錄名不帶副檔名（`.github/PULL_REQUEST_TEMPLATE`），跟無副檔名的單一 template 檔長得一樣，用 `test -d` 確認後再 `ls` 出裡面的檔案請使用者選一份。
- **命中多筆**（例如 `docs/` 與 `.github/` 各有一份，或一個檔加一個目錄）→ 把清單列給使用者選一份，不要自己挑；命中含目錄時一併把目錄內的檔案展開進選單。GitHub 在多位置並存時採用哪一份未見官方明文，猜錯會套錯骨架。
- **什麼都沒命中** → 直接用 2.6 的內建骨架，不必問使用者，**也不要順手幫該 repo 新增 template 檔**——那是改動對方的協作慣例，超出「開一個 PR」的授權範圍。

title 風格與語言不必偵測、不跟隨 repo 近期慣例，一律照下列固定規則：

- **title 風格（固定）**：一句簡潔摘要主題，直接描述這個 PR 做了什麼，**不用 Conventional Commits（`feat:`／`fix(scope):` 等）、也不加 ticket 或任何 prefix**。
- **語言（固定）**：PR 標題與描述一律使用**繁體中文台灣用語**，技術名詞與程式碼識別字（class／method／API 名等）保留原文。唯一例外：使用者當下明確要求改用其他語言時才跟隨。

使用者指定 base branch 時，改設 `BASE="<使用者指定的名稱>"`，並先驗證名稱合法（白名單字元＋確認為實際存在的 ref），避免 shell injection：

```bash
# 兩道檢查任一失敗就停手，不要繼續往下走
echo "$BASE" | grep -qE '^[a-zA-Z0-9._/-]+$' || echo "invalid base branch name" >&2
git rev-parse --verify "origin/$BASE" >/dev/null 2>&1 || echo "no such ref: origin/$BASE" >&2
```

### 2.3 取得 diff

**`$BASE` 不會跨 Bash 呼叫保留**——2.2 設的 shell 變數在下一次呼叫就沒了。要嘛把 2.2 的偵測與後續用到 `$BASE` 的區塊併進同一次呼叫，要嘛在每個區塊開頭重新取一次。漏掉時 `origin/$BASE` 會展開成 `origin/`，git 會報 unknown revision（會噴錯，不是靜默失敗，但白跑一輪）。

以 remote 上的 base 為比較基準（本地同名 branch 可能過時或不存在）：

```bash
git diff "origin/$BASE"...HEAD
git diff --name-only "origin/$BASE"...HEAD
```

### 2.4 分析與分類

從 diff 中識別功能概念層級的變更。先判斷 PR 是否有明確主軸：

- **有單一主軸**：以主軸串連所有條目，實作過程的重構、修補、附帶調整融入條目敘述，不獨立分區。
- **多項並列、無共同主軸**：在 `## 主要變更` 之下分區（Features／Bugfixes／Refactoring／Breaking Changes），**只寫實際有內容的分區**——沒有 breaking change 就不要放那個標題，也不要寫「無破壞性變更」這種佔位句。

本節只決定 `## 主要變更` 的**內部**寫法；整份 body 有哪些段落一律以 2.6 為準。

無論哪種寫法，每條都聚焦「功能概念」與「為什麼這樣做」，不列檔案路徑（例外：配置檔案如 `pubspec.yaml`／`package.json`、整個模組的新增或移除可提及路徑）。

### 2.5 生成 Summary 與 Title

- **Summary**：2-3 句概述。有 PR 目的時以目的為主軸；重要功能移除必須在 Summary 說明。
- **Title**：一句簡潔摘要主題，直接描述這個 PR 做了什麼，不用 Conventional Commits（`feat:`／`fix:` 等）或 ticket prefix；語言用繁體中文台灣用語，技術名詞保留原文。

### 2.6 組裝 PR Body

- **repo 有 PR template**：以 template 為骨架，將 Summary、變更條目、測試建議填入對應段落；template 中不適用的段落保留標題、填「N/A」或簡短說明，不要整段刪除。
- **無 template**：用內建骨架。骨架分「固定三段」與「條件選配段」。

  固定三段永遠寫：

  ```markdown
  ## Summary
  （2-3 句概述）

  ## 主要變更
  （條列，每條 what + why）

  ## Verification
  （只列「實際執行過」的指令與關鍵輸出，例如「flutter test: 21/21 passed」
   「tsc --noEmit: clean」。沒跑過任何驗證就誠實寫「未執行自動驗證」，
   不得寫「測試通過」之類無憑據的空話。）
  ```

  `## 主要變更` 的內部結構依 2.4 決定：有單一主軸就是一組條列敘述；多項並列則在其下分 Features／Bugfixes／Refactoring／Breaking Changes 區段。

  其餘段落**符合觸發條件才加**：

  | 選配段 | 觸發條件 | 內容 |
  |--------|----------|------|
  | `## 畫面` | 任何 UI 可見的變更 | 截圖或錄影。有前後對照時用兩欄 table 並排 before／after |
  | `## 請重點看` | `git diff --name-only "origin/$BASE"...HEAD \| wc -l` 大於 10 | 一兩句指出希望 reviewer 花時間的地方，以及可略過的部分（codegen、格式化）。未達 10 檔但作者自己想指路時也可以加，那部分屬作者裁量、不列入機械判定 |
  | `## 怎麼驗` | 需要 reviewer 手動確認的行為（UI 流程、跨系統整合） | reviewer 自己重現的操作路徑。與 `## Verification` 的分工：那段是「我跑了什麼」，這段是「你要怎麼確認」 |
  | `## 設計決策` | 有 trade-off 或刻意 deferred 的範圍 | 「考慮過 X 但選 Y，因為 Z」 |
  | `## 注意事項` | 有 migration、feature flag、新環境變數，或需手動執行的部署步驟 | 用 alert 語法標示，讓它在 GitHub 上跳出來 |
  | `## Related` | 有關聯 issue、跨 repo 配套 PR，或 deploy preview | issue 寫 `Closes #123`——**僅在 base 是該 repo 的預設分支時生效**，base 是其他分支（stacked PR、release 分支）時 GitHub 會忽略這個關鍵字——不會建立 linked issue 關聯、merge 也不會自動關閉 issue（`#123` 本身仍會渲染成超連結，所以「看起來有效」，這正是容易漏掉的地方）；那種情況改寫成 `Ref #123`；跨 repo PR 附連結與建議合併順序 |

  選配段的取捨：沒觸發就整段不要出現，不要留空標題或填「N/A」——那是照 repo 現成 template 填寫時才需要的禮貌。**選配段上限三段**：觸發超過三段時，依上表由上到下取前三段，其餘資訊併進 `## 主要變更` 的條目敘述裡。段落一多，reviewer 反而找不到重點。

**GitHub 渲染慣例**（讓 body 好讀，不是裝飾）：

- alert 語法 `> [!NOTE]`／`> [!WARNING]`／`> [!CAUTION]` 會渲染成帶圖示的色塊，用來標 breaking change 或部署前必須做的事。一個 PR 最多用一兩次，濫用就失去對比。
- 長輸出（完整 test log、大量檔案清單）用 `<details><summary>完整測試輸出</summary>` 摺疊：證據留著，但不佔版面。
- 截圖並排用 markdown table（`| Before | After |`），不要上下堆疊——上下堆會逼 reviewer 捲動來回比對。
- **不要自己加 checklist**（`- [ ] 已加測試`、`- [ ] 已閱讀 CONTRIBUTING`）：會被無腦全勾，訊號量為零還撐長 body。repo 自己的 template 有 checklist 則照填，那是該 repo 的規矩。

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

### 2.8 merge 時的標題覆寫

`gh pr merge --squash` 預設拿 **PR title** 當合併後的 commit 標題，而本 skill 規定 PR title 用中文且不加 prefix——與 `<REPO>/rules/20-judgment.md` §6「commit message 的固定格式」要求的英文 Conventional Commits 直接衝突。所以 squash merge 一律要用 `-t` 覆寫標題：

```bash
gh pr merge <n> --squash -t "type(scope): 英文描述 (#<n>)" --delete-branch
```

漏掉的後果：合併後的歷史第一行從此是中文、無 type prefix，事後只能重寫共享歷史（flutter-app-template 2026-08-12 為此重寫 36 個 commit）。

## 3. 完整輸出範例

> 下面為了排版，段落名用粗體、分區名用斜體。實際 PR body 裡**段落**寫成 `## 標題`，`## 主要變更` 底下的**分區**寫成 `### 標題`——低一階才會落在該段之下，寫成 `##` 會變成與 `## 主要變更` 平行。兩個範例都遵守 2.6 的固定三段。

### 範例 A：有單一主軸（融合敘述）

**Title**: `實作 Wishlist 投票功能`

**Summary**: 實作 Wishlist 投票功能：使用者可在 Settings 頁面看到正在進行的投票 banner 並開啟投票 dialog；同時在 AI Chat 完成食物分析後主動詢問使用者參與投票（每個 voteId 只通知一次）。

**主要變更**（不分區，以條列敘述涵蓋所有實作細節）：
- 新增 `ApiWishlist` 與 `VoteDetail` model，提供取得投票、送出投票、送出文字 feedback 三個 endpoint；同時統一強化 API 層初始化的錯誤邊界，避免 API client 建立失敗時整個 caller 流程崩潰
- Settings 頁面新增 wishlist banner，由 settings 專用的 `WishlistBannerNotifier` 持有 banner detail（page-scoped autoDispose），點擊 banner 直接以快取 detail 開啟 `WishlistDialog`
- AI Chat 完成食物分析後自動詢問使用者投票，並用 prefs 記錄已通知的 voteId 確保只通知一次。此處改用 `wishlistProvider` 上不寫 state 的 `fetchWishlist` 進行一次性查詢，避免「banner state」與「一次性查詢」這兩種無關職責共用同一個 autoDispose Notifier 而引發 `UnmountedRefException`

**畫面**（選配段，觸發條件：UI 可見變更；前後對照用兩欄 table 並排）：

| Before | After |
|--------|-------|
| Settings 頁面頂部無 banner | 頂部出現 wishlist banner，點擊開啟投票 dialog |

**怎麼驗**（選配段，觸發條件：需要 reviewer 手動確認 UI 流程）：
1. Settings 頁面應出現 wishlist banner，點擊開啟投票 dialog、送出後 banner 消失
2. 在 AI Chat 完成一次食物分析，應跳出投票詢問；重跑第二次分析不應再跳（同一個 voteId 只通知一次）

**Verification**: `flutter test`: 34/34 passed；`flutter analyze`: no issues。上述兩條路徑已在 iOS simulator 實際點過。

### 範例 B：多項並列（分類區段）

**Title**: `修正 email 驗證與補上 API 逾時重試`

**Summary**: 三件互不相關的後端修補，沒有共同主軸：API client 補上逾時重試、修正 email 格式驗證的誤判、把散在三處的日期格式化收斂成單一 util。

**主要變更**（多項並列，在此段之下分區；沒有 breaking change 就不放那個分區，也不寫「無破壞性變更」）：

*Features*
- API client 補上逾時重試（指數退避、上限 3 次），讓後端偶發的 504 不再直接冒到呼叫端；重試行為以 fake timer 單元測試覆蓋

*Bugfixes*
- 修正後端 email 格式驗證過於嚴格的問題，原本正規表達式會誤判含加號的有效 email，改用 RFC 5322 相容的驗證方式

*Refactoring*
- 三個模組各自實作的日期格式化收斂成單一 `formatDate` util，行為不變

**Verification**: `npm test`: 88/88 passed；`tsc --noEmit`: clean。

（本例逐條比對 2.6 的觸發條件後**一段選配段都沒觸發**：純後端邏輯、無 UI 可見變更；diff 5 個檔未達 10；三項都有單元測試覆蓋，reviewer 不需手動重現；沒有 migration、feature flag 或新環境變數；也沒有關聯 issue。所以就只有固定三段。選配段不是「有主軸的 PR 才用」，而是每次都照表逐條比對——範例 A 那種 UI 功能就會觸發到兩段。）
