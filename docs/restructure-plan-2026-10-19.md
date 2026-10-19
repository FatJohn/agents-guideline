# 全域規則重構計畫（2026-10-19）

讀者：本 repo 維護者與執行重構的 agent。

型別：計畫（完成後封存到 `docs/archive/`）。

輸入：使用者自評 `2026-10-19-agents-guildeline-self-review.md`（主）、ownership review `global-policy-ownership-review-2026-10-19.md`（主）、token review `global-rules-token-review-2026-10-19.md`（輔）、`docs/judgment-rationale.md` 與 `docs/lessons-archive.md`（歷程）。

## 1. 目標與不變量

目標：全域層只剩「最小面積的路由＋不可越過的邊界」，其餘交給專案規格、agent 合約與按需 skill。用吸收後重建的方式在 orphan branch 產出新版，不逐條修補。

不變量（任何階段都不能失守；對應 ownership review 的 K-01～K-07）：

| ID | 內容 | 新 owner |
|---|---|---|
| K-01 | 對外、共享或不可逆動作要本 session 當次授權 | 全域入口一行＋`permissions`／hook 硬擋 |
| K-02 | 完成宣稱附可重跑證據，分級已驗證／待 CI／未驗證 | 全域入口一行 |
| K-03 | 同一 working tree 單一寫入者 | agent 合約＋dispatch skill |
| K-04 | 高風險變更由 fresh-context 驗收，製作者不自驗 | verifier 合約＋dispatch skill |
| K-05 | 回覆語言 | Claude：`settings.json` 的 `language`（已設）；Codex：`AGENTS.md` 留一行 |
| K-06 | 專案規格優先於個人流程 | 兩個入口各一行 |
| K-07 | 找到本 repo 與本機事實的最短 bootstrap | 入口一行＋`hosts/<key>.md` |

不做的事：不照抄 pstack（它的自主預設會違反 K-01，mandate 本身 49KB）；不因「模型更強」刪驗收語意；不在本輪縮 Codex A–L 模板（token review FIND-07：沒有 runtime 證據前不縮）。

## 2. 目標結構

```
agents-guideline/
  CLAUDE.md / AGENTS.md          # 本 repo 自己的專案規格（怎麼維護這個 repo），不是全域
  .claude/skills/                # repo-only skill：maintain-guideline、usage-review
  global/                        # 真正會裝到 ~/.claude、~/.codex 的東西
    claude/
      CLAUDE.md                  # 最小入口：邊界 7 行＋路由表＋bootstrap
      rules/judgment.md          # 單一常駐規則檔：編號條列，無「補充判準（）」、無日期
      route-card.md              # SessionStart hook 注入的 controller 路由卡（約 2–3KB）
      agents/worker.md、verifier.md
      hooks/controller-context.sh、block-ci-edit.sh
      settings.snippets.json     # permissions／hooks／modelSettings 片段（安裝時合併）
    codex/
      AGENTS.md                  # 同一組邊界與路由，Codex 措辭
      rules/dispatch.md、delegation-templates.md   # 內容本輪只搬不縮
      agents/*.toml
    shared/                      # 兩平台共用、靠複製或 symlink 同步
      skills/dispatch/           # 由 rules-controller 兩檔吸收：派工合約、回報合約、升降級、驗收輪次
      skills/handoff/            # 交接卡：brief 卡、回報卡、verifier 判定卡、session 交接卡
      skills/git-commit/         # Conventional Commits 與 squash -t；專案規格優先
      skills/create-pr/、parallel-dispatch/、writing-principles/
      rubrics/                   # 只由 verifier 合約引用
      hosts/<key>.md             # 單機事實，只留環境 gotcha（port、sandbox、CLI）
  docs/                          # 設計說明、理由、歷史、安裝
  docs/lessons.md                # 教訓日誌：留在 repo 當改善依據，不再裝進全域
  scripts/、tests/、hooks 測試
```

對應使用者自評的決定：

- 全域與 repo 規則分層（`global/` 子目錄），`maintain-guideline`、`usage-review` 降為 repo skill。
- Claude／Codex 拆目錄；`shared/` 放可直接複製的；`maintain-guideline` 新增「哪些檔案是複製同步、哪些各平台獨立」矩陣。
- `00-environment.md` 作廢：使用者背景刪除；「主對話下場做粗活」併入 dispatch skill 與 route card 一句。
- `05-hosts.md` 作廢：`<REPO>` 對照與 bootstrap 縮成入口一行；`hosts/<key>.md` 只留環境 gotcha，專案路徑類事實改由各專案 CLAUDE.md 承接。
- `50-lessons.md` 搬 `docs/lessons.md`，不裝進全域；專案真名對照仍只留本機記憶（私有 repo 見 §5 決定 B）。
- `20-judgment.md` 改寫成編號單句規則：每條「觸發→做什麼→不算違規」，刪語言特定例子（`main.tsx` 等）與日期，細節指向 rubric／docs。
- `rules-controller/` 兩檔吸收進 `skills/dispatch/`；hook 只注入 route card（見 §5 決定 A）。
- 標題不再帶「（）」補充；規則檔不留日期 log。

## 3. 各角色與 skill 的調整

**verifier**：保留合約核心（找碴範圍、PASS／FAIL／UNSURE、四種收斂狀態、唯一可寫探針目錄）。刪歷史理由與數字（87% 散文那段進 docs）。回報改成固定「verifier 判定卡」。程式碼 diff 的 fresh review 優先走內建 `code-review` skill（由 controller 派 fresh subagent 執行），verifier 只收驗收條件與文件／規則類；rubrics 只從 verifier 合約引用。effort 依 §5 決定 C。

**worker**：合約保留（approved plan 前置、single-writer、突變紅綠、不自驗、不擴 scope、禁對外）。刪 model／effort 解釋段與 harness 數字（進 docs）。程式碼實作維持 Sonnet 5.5。

**Explore／掃描**：route card 把「掃 repo、找哪些檔有 X、整理清單」預設改派 `haiku`，列為實驗；以 verifier 首輪 OPEN 率與重派次數對照（量法沿用 `usage-review`）。

**dispatch skill**（新）：吸收 `rules-controller/10-dispatch.md` §1–§5 與 `20-judgment-controller.md` 全部。觸發：要派任何 subagent、要升降級、驗收後要決定修正路徑。body 分節，controller 用錨點讀節。

**handoff skill**（新，兩平台共用；取代 Codex-only `session-handoff`）：四張固定卡——
brief 卡（主題、目標與動機、scope 絕對路徑、single-writer、驗收條件、回報格式、已附素材）、
回報卡（改動清單、逐條完成狀態、驗證指令與關鍵輸出、未完成、分級）、
verifier 判定卡（第一行收斂標記＋下一步、逐條判定、開放題）、
session 交接卡（所在位置、已完成、待檢查、下一步、風險／待確認、為什麼這樣做；來自 hwdc 2026-10-14 脈絡卡）。全域規則只留一句「可中斷的長任務要留可恢復脈絡」。

**git-commit skill**（新）：`rules/20-judgment.md` §6 整段搬入；專案規格有自己的慣例時以專案為準。`create-pr` §2.8 指向它。

**writing-principles**：範例 `acme-login-web` 改中性名稱；其餘不動。

**parallel-dispatch**：路徑更新；定位改寫為「跨 agent 平台（Claude、Codex）與 Orca 多 session 的切分與整合」。Claude Desktop 的 nested sessions 不改變它的適用性（見 §6）。

**Codex 側**：`AGENTS.md` 改成與 Claude 入口同構的最小版（語言留一行）；dispatch 與模板只搬路徑、不縮內容；`session-handoff` 由共用 `handoff` 取代。

**本機設定**：主對話 effort 改 `medium`（使用者 2026-10-19 決定；2026-10-11 曾裁定不降，當時理由是 output 只占 17%、省幅 ≤2%——本次以使用者新決定為準，效果由下次 usage review 量）。

## 4. 執行步驟

| 步 | 內容 | 執行者 | 驗收 |
|---|---|---|---|
| 0 | 記基線：`claude -p` 空目錄首 request tokens（10-16 量得 34.2K）、互動 62.4K；rules 常駐 bytes 22,294、controller 25,016 | controller | 數字寫進本檔 §7 |
| 1 | 在 `.worktrees/v2` 建 orphan branch `v2`，建 §2 目錄骨架；`git mv` 等價搬移可直接沿用的檔（skills、rubrics、hosts、docs、scripts、tests、codex rules／agents） | controller | `tree` 與 §2 一致 |
| 2 | 寫 `global/claude/CLAUDE.md`、`global/codex/AGENTS.md`、`route-card.md`、本 repo 自己的 `CLAUDE.md`／`AGENTS.md` | worker | 入口 ≤2,500 bytes；K-01～K-07 每條可在入口或指向處讀出 |
| 3 | 把 `rules/20-judgment.md` 重寫成 `global/claude/rules/judgment.md` 編號規則；理由句搬 `docs/judgment-rationale.md` | worker | 無「補充判準（」、無日期、無語言特定檔名；每條另一 agent 可判過或不過 |
| 4 | 建 `skills/dispatch/`（吸收 rules-controller 兩檔）、`skills/handoff/`、`skills/git-commit/`；刪 `codex/skills/session-handoff` | worker | 原兩檔每個關鍵詞在新位置仍命中（`rg --hidden`）；四張卡欄位齊 |
| 5 | 改寫 `agents/worker.md`、`agents/verifier.md`；rubrics 引用只剩 verifier；writing-principles 範例改名 | worker | 刪掉的句子都在 docs 有落點；verifier 判定卡與 handoff 一致 |
| 6 | 安裝層：`scripts/install.sh`（symlink 版，從 `global/` 出發）、`sync-profile.py` 路徑、`settings.snippets.json`、`docs/install.md`、`docs/repo-layout.md`、README；`maintain-guideline` 搬 `.claude/skills/` 並加複製矩陣與新權限表 | worker | 測試全綠（`tests/`、hook 測試）；install 在暫時 `HOME` 下 dry-run 成功 |
| 7 | 路由完整性：`rg --hidden` 舊路徑零殘留（`rules-controller`、`00-environment`、`05-hosts`、`50-lessons`、`session-handoff`）；fresh verifier 逐條驗收 §4 全部條件 | verifier | CONVERGED 或 PROSE-ONLY 修完 read-back |
| 8 | 切本機安裝到 `v2`（symlink 指向 worktree），`claude -p` 重量首 request；Codex 開 fresh session 讀 AGENTS.md 走一次派工 | controller | 首 request tokens 與基線對照；兩平台都能找到 skill 與 agent |
| 9 | 試用 2–3 個真實 session 後，由使用者決定把 `v2` 取代 `main`（`main` 歷史保留為 `v1` tag） | 使用者 | — |

單一 worktree 內序列派工，一步一個 worker；步 2–5 互相獨立，若要平行就各開 worktree 再整合（照 `parallel-dispatch`）。

## 5. 需要使用者決定的項目

**A. route card 的形狀**（改變核心架構，且推翻 2026-10-16「dispatch 段不做 skill」的裁定）：
建議 hook 注入約 2–3KB 的 route card（鐵律三、何時必須派工、角色表、brief 必含欄位、指向 dispatch skill），完整派工與升降級細節在 dispatch skill 按需讀。時刻型觸發留在卡上，領域型細節才下沉，避免 10-03 稽核的自律型零觸發重演。

**B. 私有 repo**：教訓日誌、專案代號對照、hosts 明細放一個私有 repo（如 `agents-guideline-private`），公開 repo 只放制度。建立 GitHub repo 是對外動作，需當次授權；不建則 `docs/lessons.md` 留公開 repo 並維持代號制。

**C. verifier effort**：使用者提議 `medium`。建議改 `medium` 並以首輪 OPEN 率對照（reversible，frontmatter 一行）；worker 維持 `xhigh`。

## 6. 對使用者問題的回答

**Claude Desktop 的 nested sessions 對我們有沒有用？** 官方 2026 w24 更新說 subagent 可再開 subagent（最多五層），Desktop 的「nested sessions」是這套機制的介面：一個主視窗當 coordinator、每個子任務開一個子 session、逐個指定 model／effort。CLI 的 Agent 工具早就有逐次 `model`／`effort`，本系統的 worker／verifier 就是這樣跑的。差別只在可視化。我們 10-07 已經因為主對話 context 膨脹改成「一 issue 一頂層 session＋Orca 分頁」，Desktop 等於回到單一 coordinator 模式，對獨立 issue 沒有比較好；對同 issue 內的相依切片，CLI 與 Desktop 能力相同。結論：不需要為 Desktop 改制度；`parallel-dispatch` 的價值在跨 agent 平台（Codex）與 Orca 多 session，照舊保留。

**要不要直接用 pstack？** 不整包用。它的 autonomy 預設（team chat、ticket 更新不問就做）違反 K-01；mandate 49KB 與我們的瘦身方向相反；它的 playbooks 多數和本系統「指揮官怎麼調度與驗收」不是同一層。借三樣：SessionStart 短路由文字的形式、「教訓編成 lint／script 而不是更多文字」、effort 分級 agent 的想法（我們以 frontmatter 達成）。

**記憶機制有沒有更好的選擇？** 四層不變（事件史、精選記憶、交接檔、repo 文件）。可改善的是交接檔統一成 handoff skill 的 session 卡（兩平台同一格式），以及決定 B 的私有 repo 承接「不能公開但要跨機器」的那層。

## 7. 基線與量測

| 量測 | v1（main @ 51b04f2） | v2（@ 本檔 commit） | 差 |
|---|---:|---:|---:|
| `claude -p --model sonnet` 空目錄首 request 總輸入 tokens（含 SessionStart hook 注入，transcript 內可見注入標記） | 36,886（write 25,674＋read 11,210） | 31,782（write 20,570＋read 11,210） | −5,104（−14%） |
| Claude 常駐 bytes：入口＋rules＋host | 22,294 | 11,628（CLAUDE 1,869＋judgment 8,744＋host 1,015） | −48% |
| hook 注入 bytes | 25,016（rules-controller 兩檔） | 2,440（route-card） | −90% |
| 按需載入（派工時才付） | 0 | dispatch skill 25,361 | 新增 |
| Codex `codex exec` 讀新 `AGENTS.md`（Luna low） | — | 11,264 tokens，三題答對 | 可用 |

- 量法：`env -u CLAUDE* claude -p "reply with the single word ok" --model sonnet`，讀該 session jsonl 第一筆 assistant 的 `usage`。兩次都在空目錄，無專案 CLAUDE.md。
- 待兩週後用 `usage-review` 量：主對話首 request 中位、subagent 首 request 中位、verifier 首輪 OPEN 率（verifier effort medium 與 Explore haiku 兩個實驗）、dispatch skill 在多少比例的 session 被載入。
- 步 6 的 `scripts/install.sh` 未另建：`docs/install.md` 的 bash 區塊即安裝器，已在暫時 HOME 與本機實跑。
- 已知未決：Codex 端 `~/.agents/skills/handoff` 已有同名的第三方 skill（`disable-model-invocation: true`），本 repo 的 `handoff` 在 Codex 端未安裝，Claude 端正常。
