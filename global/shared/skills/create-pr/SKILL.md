---
name: create-pr
description: Use when the user wants to create a Pull Request from the current branch, in any wording or language that asks to open a PR or send the branch for review (e.g. 「開 PR」, "open a pull request"). Also trigger on implicit ship-it cues (e.g. 「可以開了」, "ship it") when the current branch is clearly diverged from its base branch.
allowed-tools: Bash(git:*), Bash(gh:*), Bash(find:*), Bash(ls:*), Bash(test:*), Bash(grep:*), Bash(sed:*), Bash(wc:*), Bash(cd:*), Bash(echo:*), Bash(mktemp:*), Bash(cat:*), Bash(rm:*), Read
---

# Create PR

先偵測 repo 的 base branch 與 PR template 再生成。**PR 標題與描述預設使用繁體中文台灣用語（技術名詞與程式碼識別字保留原文），標題採一句摘要主題、不用 Conventional Commits 或任何 prefix；repo 規定或既有慣例不同時以 repo 為準，判法見 2.2。**

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

**有明確主軸時，融合敘述而非分區**：PR 圍繞單一主軸（實作某功能、修某 bug）時，順手做的重構、修補、附帶調整作為實作細節融入主敘述條目，**不要**獨立為 Refactoring／Bugfixes 區塊，否則 reviewer 會誤以為那些是與主題無關的副作用。

只有變更彼此並列、沒有共同主軸（例如雜項修補 PR）時，才在 `## 主要變更` 之下以 `###` 分區（Features／Bugfixes／Refactoring／Breaking Changes），分類以目的為準：新功能 → Features；修 bug → Bugfixes；行為不變的品質改善 → Refactoring；其他模組要改 code 才能運作 → Breaking Changes。只寫有內容的分區，不寫「無破壞性變更」這種佔位句。

**篇幅隨變更規模縮放**：小 PR 只需 Summary＋少數條目；大 PR 才展開完整段落。判準：拿掉某段不會讓 reviewer 變慢，就拿掉。

**明寫 trade-off 與刻意不做的事**：如果實作中做了取捨（「考慮過 X 但決定不做，因為 Y」）或刻意 deferred 某範圍，在 body 中明說，避免 reviewer 誤以為是遺漏。重要功能移除要在 Summary 說明。

**忽略不影響邏輯的變更**：生成檔案（lock files、`*.g.dart`／`*.freezed.dart` 等 codegen 產物、build 輸出）、純格式化、單純的 import 重排等，不寫進描述。條目不列檔案路徑；設定檔（`pubspec.yaml`／`package.json`）與整個模組的新增或移除例外。

## 2. 流程

### 2.1 確認 PR 目的

使用者有給 PR 目的就以它為主軸串連所有變更；沒有就從 diff 推斷。

建議使用者在開 PR 前先跑該 repo 的檢查慣例（lint / type-check / test，或專案自帶的 pre-commit skill）；本 skill 不主動代跑。repo 文件把測試、lint 或 code review 通過列為開 PR 前置條件時例外：先確認那些閘門已通過並附證據（實跑輸出、review 紀錄或連結），未通過或拿不出證據就不開、回報缺哪一項。

### 2.2 偵測 repo 慣例

```bash
# (a) base branch：使用者指定則優先，否則取 origin 的 HEAD
BASE="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
test -n "$BASE" || BASE="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"

# (b) PR template：GitHub 只認 repo 根、docs/、.github/，檔名大小寫不敏感。
# 必須先切到 repo 根，從子目錄跑會 0 筆命中；目錄不存在時 find 回非 0，以 stdout 有無輸出為準
cd "$(git rev-parse --show-toplevel)"
find .github docs . -maxdepth 1 -iname 'pull_request_template*' 2>/dev/null
```

使用者指定 base 時，先確認名稱只含 `[a-zA-Z0-9._/-]` 且 `git rev-parse --verify "origin/$BASE"` 成功，任一失敗就停手。

template 偵測結果：

- **命中一個檔案** → 以它為 body 骨架（見 2.6）。
- **命中目錄**（多 template 目錄名不帶副檔名，跟無副檔名的單一 template 檔長得一樣，用 `test -d` 分辨）→ `ls` 出裡面的檔案請使用者選一份。
- **命中多筆** → 列清單（目錄內的檔案一併展開）請使用者選，不要自己挑。
- **沒命中** → 用 2.6 的內建骨架，不必問使用者。

**repo 規定與既有慣例**：標題／描述的語言與格式、是否一律先開 draft、開 PR 前要過的檢查、merge 與 review 流程，repo 有規定時以 repo 為準。依序判斷：

1. repo 文件（`AGENTS.md`／`CLAUDE.md`／`CONTRIBUTING.md`／PR template）有明文就照明文。
2. 只有標題／描述的語言與格式在沒明文時看既有慣例（其餘三件文件沒寫就用預設）：

   ```bash
   gh pr list --state merged -L 10 --json title,author -q '.[] | select(.author.is_bot | not) | .title'
   ```

   排除 bot 後過半是英文就用英文，其中過半是 Conventional Commits 就跟隨該格式，否則照多數的寫法；過半是中文就用中文；不足 3 筆或看不出多數視為無慣例。描述語言跟標題同語言，repo 文件另有規定時照文件。
3. 都沒有 → 照開頭的預設。
4. 使用者當下明確要求的語言或格式永遠最優先。

### 2.3 取得 diff

`$BASE` 不會跨 Bash 呼叫保留：把 2.2 的偵測與後續用到 `$BASE` 的指令併進同一次呼叫，或每次重新取。以 remote 上的 base 比較（本地同名 branch 可能過時或不存在）：

```bash
git diff "origin/$BASE"...HEAD
git diff --name-only "origin/$BASE"...HEAD
```

### 2.4 分析與分類

從 diff 識別功能概念層級的變更，依 §1 判斷有無主軸。

### 2.5 生成 Summary 與 Title

Summary 幾句話讓 reviewer 知道做了什麼、為什麼；Title 照 2.2。

### 2.6 組裝 PR Body

- **repo 有 PR template**：以 template 為骨架填入；不適用的段落保留標題、填「N/A」或簡短說明，不要整段刪除。
- **無 template**：固定三段永遠寫：

  ```markdown
  ## Summary
  （幾句話：做了什麼、為什麼）

  ## 主要變更
  （條列，每條 what + why；並列無主軸時在此段下用 ### 分區，見 §1）

  ## Verification
  （只列實際執行過的指令與關鍵輸出，例如「flutter test: 21/21 passed」「tsc --noEmit: clean」。
   沒跑過任何驗證就誠實寫「未執行自動驗證」，不得寫無憑據的「測試通過」。）
  ```

  其餘段落**符合觸發條件才加**：

  | 選配段 | 觸發條件 | 內容 |
  |--------|----------|------|
  | `## 畫面` | 任何 UI 可見的變更 | 截圖或錄影；前後對照用兩欄 table 並排 before／after |
  | `## 請重點看` | `git diff --name-only "origin/$BASE"...HEAD \| wc -l` 大於 10（未達時作者想指路也可加） | 希望 reviewer 花時間的地方，以及可略過的部分 |
  | `## 怎麼驗` | 需要 reviewer 手動確認的行為（UI 流程、跨系統整合） | reviewer 重現的操作路徑（`## Verification` 是「我跑了什麼」，這段是「你要怎麼確認」） |
  | `## 設計決策` | 有 trade-off 或刻意 deferred 的範圍 | 「考慮過 X 但選 Y，因為 Z」 |
  | `## 注意事項` | 有 migration、feature flag、新環境變數，或需手動執行的部署步驟 | 用 `> [!WARNING]` 等 alert 語法標示 |
  | `## Related` | 有關聯 issue、跨 repo 配套 PR，或 deploy preview | `Closes #123` 只在 base 是該 repo 預設分支時生效（其他 base 時 GitHub 忽略關鍵字，但 `#123` 仍渲染成連結，看起來像有效），那時改寫 `Ref #123`；跨 repo PR 附連結與建議合併順序 |

  沒觸發的選配段整段不出現，不留空標題或「N/A」。觸發很多時只保留 reviewer 必須單獨看到的段落（`## 注意事項` 一律保留），其餘併進 `## 主要變更`。

- alert 語法只用在 reviewer 絕不能錯過的事；長輸出用 `<details>` 摺疊。
- **不要自己加 checklist**（`- [ ] 已加測試`）：會被無腦全勾。repo template 自帶的 checklist 照填。

### 2.7 確認並建立 PR

1. 展示 Title、Base Branch、PR Body 完整預覽。
2. 取得使用者明確同意後才執行。repo 規定一律先開 draft 時加 `--draft`；沒規定時預設 ready。

```bash
git push -u origin HEAD

# body 走暫存檔，避免多行字串轉義問題
PR_BODY_FILE="$(mktemp)"
cat > "$PR_BODY_FILE" << 'PR_BODY_EOF'
（實際的 PR body 內容）
PR_BODY_EOF
gh pr create --title "（實際的 PR title）" --base "$BASE" --body-file "$PR_BODY_FILE"
rm -f "$PR_BODY_FILE"
```

3. 輸出 PR URL 後停下回報，**預設不等 CI、不等 bot review、不問「CI 全綠後是否直接 merge」**。使用者說「merge」就照 2.8 merge；明說「綠了再 merge」「等 review 處理完」才等。repo 規定 review 流程（例如 draft → bot review → ready）時照規定開，回報指出下一步，但不自動掛著等。merge 指令只限這個 PR（全域邊界 3）。

### 2.8 merge 時的標題覆寫

`gh pr merge --squash` 預設拿 PR title 當 commit 標題，與 `~/.claude/skills/git-commit/SKILL.md` 的英文 Conventional Commits 衝突，所以 squash merge 一律用 `-t` 覆寫：

```bash
gh pr merge <n> -R <owner/repo> --squash -t "type(scope): 英文描述 (#<n>)"
```

漏掉的後果：合併後的歷史第一行從此是中文、無 type prefix，事後只能重寫共享歷史。

不加 `-t` 的例外（PR title 已合格且 repo 文件規定不覆寫，如 release-please 的 Release PR；或 PR title 已照 2.2 跟隨英文 Conventional Commits 慣例）見 git-commit「squash merge」段的「不算違規」。

不加 `--delete-branch`：stacked 在其上的 PR 會被自動關閉且無法 reopen（`<REPO>/docs/lessons-archive.md` 2026-07-08）；遠端分支留給 repo 的自動清理或使用者自己刪。merge 指令單獨一個 Bash 呼叫、`-R` 放子命令之後（`<REPO>/docs/debug-environment-first.md`「gh 指令的 permission 形狀」）。

merge 時不等 CI：branch protection 擋下就回報 `gh` 錯誤原文，不自行等綠重試；merge 後 `gh pr view <n> -R <owner/repo> --json state,mergeCommit` read-back 一次即結束，不等 main 上的 run。只有使用者明說「綠了再 merge」才用 CI 閘門：先確認 check 已註冊再 `gh pr checks --watch`（或 `gh run watch <run-id> --exit-status`），不接 `| tail`（`<REPO>/docs/debug-environment-first.md`「管線之後的 `$?`」）。

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
