# Prompt audit 2026-11-07

讀者：決定要採用哪些 hunk 的本 repo 維護者。

本報告依 Claude Code `claude-api` skill 的 `prompt-audit` 流程產出，基準 commit 是 `fe16088`。

**採用狀態（2026-11-07）**：使用者同意後，H1–H3、M1、M2、M4–M9 已套用；M3 依建議等量測，暫不採用，下方 Part B 的第 53 行 hunk 未套。下方的行號與 diff 是稽核當時的內容。

## 假設

- **目標模型**：Claude 系檔案對 Sonnet 5.5（主對話）與 Opus 5.5（issue session、verifier）判定，這是請求指定的。
- **非 Anthropic 標記**：`global/codex/agents/*.toml` 釘在 `gpt-5.6-{terra,sol,luna}`。依流程，釘自己 model 的檔要對該 model 判定，所以 `global/codex/**` 只查 Group 2（事實與矛盾），不套 Claude 的行為判定，也不提議換 provider。
- **`global/shared/**`**：兩平台共用，以 Claude 目標判定；有 Codex 影響的另外註明。
- **未讀**：`global/claude/settings.snippets.json`（流程規定設定檔不讀）。
- **`.py`**：不算 prompt 面，只比對了 `check_docs.py` 的 regex 與 `pricing.json`。

### 涵蓋深度

| 深度 | 檔案 |
|---|---|
| 全文讀 | 兩個入口、`route-card.md`、`judgment.md`、`claude/agents/verifier.md`、`codex/agents/{verifier,explorer,scanner}.toml`、`dispatch`、`handoff`、`git-commit`、`worktree-session/SKILL.md`、`rubrics/{code-change,document-quality,research-analysis,review-findings}.md`、`maintain-guideline`、`controller-context.sh` |
| 讀主要段落加全檔 grep | `create-pr`（第 1–215 行）、`agent-rules/SKILL.md`（第 1–60 行）、`usage-review/SKILL.md`（第 1–20、70–90 行）、`codex/rules/dispatch.md`（開頭與 grep 命中行）、`codex/agents/{reviewer,sol_verifier}.toml`（`reviewer` 看到第 13 行前後） |
| 只有 grep 與引用檢查 | `writing-principles/**`、`agent-rules/references/**`、`usage-review/references/**`、`worktree-session/references/**`、`delegation-templates.md`、其餘 hooks、`global/shared/hosts/*` |

只有 grep 的檔可能還有文字型的過時內容沒被抓到，這是本次的已知缺口。

## 摘要

最值得先看的是三件事：

1. **dispatch 自己對 fresh `code-review` 的 brief 有矛盾**（H2）。第 23 行說不需驗收條件，第 58 行說缺驗收條件就是不合格的派工。
2. **「鐵律二／三」已經沒有定義**（H1）。v2 把入口改成「邊界」六條後，`global/` 還有 6 處在用這個詞，但沒有任何地方定義它，其中包含授權邊界的引用。
3. **fresh review 可能被 `review-findings.md` 的過濾句壓低 recall**（M3）。這是三項中證據最弱的一項：文件記載的是 Opus 4.7、4.8、5 與 Sonnet 5 會照字面遵守「只報高嚴重度」，Opus 5.5 與 Sonnet 5.5 沒有同樣的記載，這裡是外推，也沒有 recall eval。

本次沒有對 `judgment.md` 提任何修改：15 條都查得到訂條理由或環境 gotcha，沒有符合過時 pattern 的條目。

| Group | 有提案 | 只 flag | 結果 |
|---|---|---|---|
| 1 過時 prompt 文字 | 3（M1、M2、M8） | 7（L1–L6、L8） | 1b 的思考與格式 scaffold、1f 的回報上限，signal 皆零命中或屬格式約束 |
| 2 脆弱的 skill 與設定 | 8（H1–H3、M4–M7、M9） | 4（L9–L12） | 路徑引用檢查 237 處，唯一命中是佔位字（`container.md:37` 的 `ade-survey-<日期>`）；章節引用檢查 56 處無斷鏈 |
| 3 tool description | — | — | not applicable：repo 沒有 tool 定義 |
| 4 request 與架構 | 1（M3） | 1（L7） | 沒有 request code；roster 乾淨；已有 token accounting（`usage-review`）；`pricing.json` 的 Opus 5.5、Sonnet 5.5、Fable 5.1 單價與 skill 價目表一致 |

M3 同時屬於文件記載的 review 行為與 harness 設計，計在 Group 4。

## Findings：高信心

### H1　「鐵律二／三」沒有定義

- **Location**：`global/shared/skills/dispatch/SKILL.md:28`、`:80`；`global/shared/skills/worktree-session/SKILL.md:27`、`:63`；`global/shared/skills/create-pr/SKILL.md:199`；`global/codex/rules/dispatch.md:109`
- **Evidence**：「對外授權仍依鐵律二」「（鐵律二）」「## 6. 驗證語意（鐵律三）」
- **Pattern**：Group 2 Volatile specifics，指向已不存在的名稱。
- **Why obsolete**：`rg --hidden 鐵律 global .claude/skills` 的 6 處全是使用，沒有定義；入口現在叫「邊界」，`worktree-session/SKILL.md` 第 1 節已經寫「全域邊界 5」。讀者要自己猜鐵律二等於邊界 3。
- **Confidence**：High
- **Action**：`rewrite`，改成「全域邊界 3」；Codex 標題去掉括號（引用該節都用「驗證語意」，改了不斷鏈）。
- **權限**：`maintain-guideline` §5 把斷鏈修正列為不受判準修改觸發條件限制，dispatch 的兩處仍列在 Part B 由你決定。

### H2　fresh `code-review` 的 brief 要不要驗收條件

- **Location**：`global/shared/skills/dispatch/SKILL.md:23` 對 `:58`；`global/claude/route-card.md:15`
- **Evidence**：第 23 行「執行 `code-review` skill（從 diff 推 bug，不需驗收條件…）」；第 58 行「**brief 必含三段**…缺一段就是不合格的派工：目標與動機…；驗收條件…」。
- **Pattern**：Group 2 指示互相矛盾。
- **Why obsolete**：同一檔的兩條規則對同一種派工結論相反。第 23 行較具體，也符合 `code-review` skill 的實際輸入，所以以它為準。
- **Confidence**：High
- **Action**：`rewrite`，在第 58 行與路由卡加上例外。

### H3　對照組還寫「升降級」

- **Location**：`.claude/skills/maintain-guideline/SKILL.md:40`
- **Evidence**：「派工時機、升降級、驗證不自驗」
- **Pattern**：Group 2 Volatile specifics。
- **Why obsolete**：`global/` 與 `.claude/skills/` 只剩這一處寫「升降級」；dispatch 現在只有 §1–§6，沒有這一節，對應內容是 `dispatch/SKILL.md:26` 的升檔條件。
- **Confidence**：High
- **Action**：`rewrite` 成「升檔條件」。

## Findings：中信心

### M1　要求 brief 寫「指令批次化」

- **Location**：`global/claude/route-card.md:15`、`global/shared/skills/dispatch/SKILL.md:58`、`global/shared/skills/handoff/SKILL.md:22`
- **Evidence**：路由卡「附已讀素材並要求指令批次化」；dispatch「把已讀過的素材附進 prompt並要求指令批次化」；handoff「能一次串完的批次化」
- **Pattern**：Group 1d Tool-use discouragement（「minimize tool calls」的變體）。
- **Why obsolete**：文件記載 Sonnet 5.5 會照字面遵守減少工具呼叫的指示。本 repo 自己也量過：`docs/judgment-rationale.md:281` 記錄派工 prompt 有無重申這句沒有差別（工具呼叫中位 97.5 對 89 次）。不過那次量的是已移除的 worker，不是目前的角色。
- **保留的部分**：「附已讀素材」有獨立理由，不動；`verifier.md:26` 的批次化也不動，因為它綁 subagent 5 分鐘 cache 的成本理由（`docs/reviews/verification-policy-history.md:30-38`），不是 brief 重申。
- **Confidence**：Medium
- **Action**：`remove` brief 層的這句。
- **待決**：`global/codex/rules/dispatch.md:85` 有對應句，目標模型不同所以沒有提案；要不要對齊由你決定。

### M2　context 量測的固定時機

- **Location**：`global/shared/skills/dispatch/SKILL.md:94`
- **Evidence**：「每個實作 phase 開始前、打算一次讀入 ≥5 個未讀檔前各量一次。」
- **Pattern**：Group 1d Unenforced instructions，加上 1b 的固定節奏編排。
- **Why obsolete**：這條沒有任何機制檢查。粗略量測：2026-10-29 之後的 231 個主對話 jsonl，最多 23 個有符合這個 jq 量測形狀的 Bash 呼叫。這是上界，regex 也可能命中用量分析指令，而且分母含不需要量的小 session。本次稽核讀入遠超過 5 個未讀檔，也沒有照做。
- **保留的部分**：≥300K 的門檻有理由（`docs/judgment-rationale.md:315`），不動。
- **Confidence**：Medium
- **Action**：`rewrite` 成不含計數的時機。要真的落實應該改成 hook，但那要動 `settings.json`，不在本 diff。

### M3　review 的過濾句約束到 fresh review

- **Location**：`global/shared/rubrics/review-findings.md:10`、`:28`、`:43`；提案改 `global/shared/skills/dispatch/SKILL.md:53`
- **Evidence**：「缺一就不發」「讀不出型別就不提」「**LOW＝不發**」
- **Pattern**：文件記載的 severity filter（`model-migration.md` 第 795–801、1144、1288 行），歸在 Group 4 的 harness 設計。
- **Why obsolete**：文件記載 Opus 4.7、4.8、5 與 Sonnet 5 會查到問題後，因為低於門檻而不回報。**Opus 5.5 與 Sonnet 5.5 的章節沒有這項記載，把它套到目標模型是外推。** 這份 rubric 的門檻算具體（文件對單次自我過濾的建議正是要具體），來源是實測的 67 條 AI inline review（`review-findings.md:5`），第 18 行也允許寫成問句，所以對 PR 留言仍然合理。疑慮只在 fresh review 交給 controller 時，後面已有一層過濾，前面再過濾可能多丟資訊。
- **風險**：finding 變多可能重新放大驗收輪次，所以採用前要量 finding 數與輪數。來源的 67 條不是目標模型上的量測，目前也沒有 recall eval。
- **Codex 影響**：沒有。rubric 兩平台共用，Codex `reviewer.toml:11` 規定不提純風格意見，所以 hunk 不動 rubric，只改 Claude 端的 dispatch brief；兩平台在這點會刻意分版，要不要對齊由你決定。
- **Confidence**：Medium
- **Action**：`add` 一句到 Claude 的 brief 要求，把 rubric 的「不發」「不提」限定在要貼到 PR 的留言；純風格偏好仍不列。

### M4　路由卡引用的環境句

- **Location**：`global/claude/route-card.md:21`
- **Evidence**：「環境注入的「除非使用者要求，否則不要叫用 Agent」擋的是沒有制度依據的自主派工」
- **Pattern**：Group 2 Volatile specifics（沒有查核日期的 harness 引語）。
- **Why obsolete**：本 session（Claude Code 2.1.319）的 Agent 工具說明沒有這句，改成成本取捨的說法（例如「When in doubt, don't spawn」）。這只是單一 session 的觀察。這句要傳達的授權關係還有效，所以只拿掉引語。
- **Confidence**：Medium
- **Action**：`rewrite`。

### M5　skill description 的觸發詞清單

- **Location**：`.claude/skills/usage-review/SKILL.md:3`、`global/shared/skills/writing-principles/SKILL.md:3`、`global/shared/skills/agent-rules/SKILL.md:3`
- **Evidence**：「觸發詞：量用量、成本拆帳、subagent 成本、context 膨脹…」
- **Pattern**：Group 2 Trigger-case enumeration。
- **Why obsolete**：description 每個 request 都帶，清單多半重複同一段前面已寫的內容。`dispatch` 與 `handoff` 已經用意圖句的寫法。
- **Confidence**：Medium
- **注意**：`maintain-guideline:52` 指出 skill 容易 under-trigger，keep list 也允許路由文字保留強度，所以這裡只收斂列舉，不降低強度。依 `maintain-guideline` §2，改 description 要跑 `claude -p` 2＋2 句觸發測試，這一步還沒跑。「規則太多」這類詞刪掉後別處零命中，要靠測試確認沒有變差。
- **Action**：`rewrite` 成一句英文意圖。

### M6　正文裡的歷史敘述

- **Location**：`global/shared/skills/worktree-session/SKILL.md:79`、`global/codex/rules/dispatch.md:7`、`global/codex/rules/delegation-templates.md:5`
- **Evidence**：「已於 2026-10 日落」「於 v4（2026-10-29）日落」「v4（2026-10-29）起只有六份模板」
- **Pattern**：Group 2 History narratives，以及 1d Migration-relative phrasing。
- **Why obsolete**：規則的效力來自它規定的行為。這些句子是對舊版的 diff，讀者看不到舊版，還多列了已不存在的角色名。
- **Confidence**：Medium
- **Action**：`rewrite` 成現況句，保留理由文件的連結；「divide-and-conquer」「agent race」在別處零命中，所以留在改寫後的句子裡。

### M7　`usage-review` 的 worker 指標

- **Location**：`.claude/skills/usage-review/SKILL.md:47`
- **Evidence**：「worker 交回後到下一個 verifier 派出前的改檔次數」
- **Pattern**：Group 2 Volatile specifics。
- **Why obsolete**：路由卡現在只有驗收、review、查詢三類 subagent，`scripts/report.py` 仍只認 `subagent_type` 含 `worker` 的派工（第 597 行）。新 session 的這一欄沒有資料，看起來卻像「交回後沒有改檔」。
- **Confidence**：Medium
- **Action**：`rewrite` 註明適用範圍。腳本本身不在提案內。

### M8　「不准「先加了再說」」

- **Location**：`.claude/skills/maintain-guideline/SKILL.md:74`、`:90`
- **Evidence**：「不准「先加了再說」」
- **Pattern**：Group 1a Pressure language。
- **Why obsolete**：同一句已經把順序規定清楚，這幾個字沒有增加可判定的內容，也沒有附理由。上限與「先合併或日落」的規定都保留。
- **Confidence**：Medium
- **Action**：`rewrite`。

### M9　verifier 合約的「最終升級」

- **Location**：`global/claude/agents/verifier.md:10`
- **Evidence**：「高風險驗收（文件／規則／架構決策／最終升級）」
- **Pattern**：Group 2 Volatile specifics。
- **Why obsolete**：目前的卡住流程只有換路（`dispatch/SKILL.md:70-74`），升檔則是另外問使用者（第 26 行），沒有「最終升級」這個階段。
- **Confidence**：Medium
- **Action**：`remove` 這個詞。

## Findings：低信心，只 flag

這些項目不進 diff。L1、L2 符合文件列的 pattern，但依 keep list 第 5 項（失敗仍實際發生）與你對日落條款的要求，不提刪除；L3 同樣先量再決定。

| ID | Location | Pattern | 判斷 |
|---|---|---|---|
| L1 | `global/claude/CLAUDE.md:12`、`dispatch/SKILL.md:12`、`route-card.md:8` | 1d 過度驗證 | 文件對 Opus 5 的建議正好相反（「Verification belongs in your main agent loop」），Opus 5.5 段要求重測。**建議保留**：這裡的目的是去除作者偏誤，理由有實際事故（`judgment-rationale.md:341-351`，測試全綠仍漏掉五條失敗路徑）。要動只能用量測決定 |
| L2 | `handoff/SKILL.md:31`、`judgment.md` 第 6 條 | 1d self-check | 文件的 Opus 5 段（`model-migration.md:1091`）說要求自我複查會增加工作量。**建議保留**：這條 2026-11-05 才根據 310 筆 finding 訂立，本機記憶記載約 11-12 要再量，先等結果 |
| L3 | `route-card.md:3`、`dispatch/SKILL.md:8`、`handoff/SKILL.md:29` | 1b plan before acting | 文件說這類指示會造成過度規劃。但這張卡的主要產物是給 verifier 的驗收條件，不只是規劃。可以量 `Phases` 欄是否被用到，再決定要不要留 |
| L4 | `dispatch/SKILL.md:58`、`handoff/SKILL.md:28` | 1c 防幻覺句 | 「查無來源就留空」。Opus 5.5 較少憑空寫內容，但查詢角色用 Haiku 與 Sonnet，文件也說這類刪除屬低信心 |
| L5 | `verifier.md:26` | 1b 輪詢編排 | 合約要求背景指令後前景輪詢；本 session 的 Bash 工具說明是背景結束會自動喚醒，不要輪詢。主對話這樣成立，**subagent 是否同樣會被喚醒未驗證**，所以不改。可用一次低成本 subagent 實跑確認 |
| L6 | `verifier.md:35`、`dispatch/SKILL.md` §1–§2 | 1d Patch accretion | 條件很多，各自對應事故。本機記憶記載機械結案後仍重派 delta 約 10 次（2026-11-05，本次未重量），表示這段的規則有不被遵守的跡象。這是結構問題，字句修改解決不了，`maintain-guideline` §5 也不允許順手重寫 |
| L7 | 主對話設定（未讀，依本機記憶） | 4 effort | Sonnet 5.5 的 effort 已重新校準，文件建議 agentic coding 從 `medium` 開始。本機記憶記載主對話用 `high` 是刻意選擇，所以只建議下次用量 review 時順便比較 |
| L8 | `maintain-guideline:73` | 1f 數字上限 | 「上限 80 字」管的是教訓日誌的格式，不是模型回覆。目前 5 條教訓第一個 `→` 之前的段落（含日期與標籤）為 61–99 字元，4 條超過 80，代表這條沒有被檢查 |
| L9 | `worktree-session/SKILL.md:4` 對 `:53` | 2 契約不符 | `allowed-tools` 沒有 `Bash(python3:*)`，正文卻要跑 `python3 …/worktree-clean-check.py`。這是放寬權限的改動，所以只 flag |
| L10 | `route-card.md:21` | 2 未定義名稱 | `deep-research` 在 repo 內只出現這一次，本 session 的 skill 清單也沒有。它可能是另外安裝的工具，不算被 repo 反駁 |
| L11 | `cli.md:8`、`container.md:7`、`require-issue-session-model.sh:8,106`、`hosts/macos.md:8` | 2 釘死 model | `claude-opus-5-5` 是精確指令，屬 keep list 第 3 項。下次換代時要一起改這幾處，因此列為清單 |
| L12 | `handoff/SKILL.md:15`、`dispatch/SKILL.md:54` | 2 角色名 | 兩處還提到 `Plan`，路由卡的 subagent 三類不含它。規則上不派，不會誤導行動 |

## 刻意不標過時的項目

這些符合 grep signal，但查過來歷後保留：

| 項目 | 依據 |
|---|---|
| `judgment.md` 第 8–10 條 | 實測到的漏洞與誤判（`judgment-rationale.md:167-204`） |
| 「不要再呼叫 Agent 工具轉包」 | 曾發生 5 層以上遞迴派工（`lessons-archive.md:25`），句旁有理由 |
| verifier 的找碴範圍 | 一次 40 輪驗收，93 則發現有 87% 落在散文（`verification-policy-history.md:28`） |
| delta 不換新探測形狀 | 三輪各出新形狀的量測（`judgment-rationale.md:113`） |
| 本人在場時先問時段 | 約 6 小時與 10.9 小時的空轉（`judgment-rationale.md:219`） |
| `rg --hidden`、`gh -R` 單獨呼叫、`--delete-branch`、5 分鐘 cache | 環境 gotcha，日落條款明定保留 |
| 顯式 `model: opus` 與風險分流（皆多處） | 內容一致的重複，屬 keep list 第 8 項 |
| `create-pr` 的 Good／Bad 範例與段落骨架 | 格式敏感的輸出，且有多個對照例子 |
| 繁中「一律／不准／禁止」 | 各 skill 合計命中多，但多數附理由或屬安全邊界；不以密度判定，只列 M8 |

英文全大寫強調只命中 3 個檔共 4 行，其中 `review-findings.md` 的 2 行是嚴重度標籤。

## 範圍外的觀察

這些不在請求範圍內，所以沒有 hunk。其中 `install.md`、`mechanism.md`、`harness-facts.md:33` 依判準第 3 條的殘留掃描，已在採用時一併修正：

- `docs/judgment-rationale.md:9,15,21`：對照表還寫 dispatch §5「升降級」、§7、§8，現在分別不存在、是 §2、是 §5。`judgment.md:3` 把讀者導向這份檔。
- `docs/install.md:66`：標題「Claude Code permissions 要和鐵律二對齊」，是 H1 在範圍外的殘留；`docs/design/mechanism.md:47`、`:59`、`:97` 也命中「鐵律」，改標題時要一起查。
- `docs/harness-facts.md:33`：還寫「最終升級」，是 M9 在範圍外的殘留。
- `global/claude/config/ripgreprc:6`：註解還寫 `20-judgment.md section 2`。

## 補充稽核：`resolving-merge-conflicts`

稽核後另一個 session 在 `~/.claude/skills` 建了第三方 skill 的 symlink。這些 skill 本來就在 `~/.agents/skills`，只是對 Claude 端是新的。與先前清單相比，會自動觸發的新面孔只有這個（`grill-me` 也是新面孔，但只有一行轉呼叫 `/grilling` 且 `disable-model-invocation: true`，沒有 finding）。使用者沒有指名是哪個 skill，這是推斷。這些檔在 repo 外，依流程只 flag，不提 diff。

| ID | Location | Pattern | 判斷 |
|---|---|---|---|
| S1 | `~/.agents/skills/resolving-merge-conflicts/SKILL.md:10` | 1a 無條件禁止 | 「Always resolve; never `--abort`.」沒有附理由。若解不開或方向錯，這句會禁止最安全的退路。入口的優先權（使用者指示→專案規格→本系統→skill 自我宣稱）可蓋過它，但模型載入 skill 時不一定會比對 |
| S2 | 同檔:14 | 2 指示互相衝突 | 「Stage everything and commit.」可能把無關的 untracked 檔一起加入，也和環境「使用者要求才 commit」的規定不同；只有使用者已要求完成 merge／rebase 時才成立 |
| S3 | 同檔:6–14 | 1c 步驟編排 | 五步驟與「Understand deeply」偏指令式，但 merge 的順序確實重要，屬 keep list 第 3 項，不建議動 |

第 3 步「Do **not** invent new behaviour」與判準第 15 條方向一致。如果要改 S1、S2，建議自己維護一份而不是直接改第三方安裝檔，否則更新時會被蓋掉。

## 如何採用

每個 Part 都能單獨套用，`-U0` 的 hunk 要加 `--unidiff-zero`：

```bash
git apply --unidiff-zero <只含想要 hunk 的 patch>
```

`dispatch/SKILL.md:58` 同一行含 H2 與 M1，以及 `route-card.md:15` 同一行含 H2 與 M1，因為檔案是單行長段落，無法拆成兩個 hunk；只想取其一要手動改那一行。

**權限**：`maintain-guideline` §5 規定主動 review 產生的判準修改只算候選，要你對單項說「改」才算觸發，否則應開 `candidate:` issue。這次請求只要報告，所以我沒有開 issue。

### 已驗證

- 三個 Part 都對 `fe16088` 通過 `git apply --check --unidiff-zero`。
- 三個 Part 一起套到 scratch 匯出副本後，`tests/` 149 個、`scripts/tests/` 166 個 unittest 全過，`tests/*.sh` 5 支全過。本機 `python3` 沒有 pytest，所以用 `unittest discover` 跑；`tests` 與 `scripts/tests` 查無 pytest 專屬語法（`rg 'import pytest|^@pytest|pytest\.'` 零命中）。
- 套用後 `global/` 與 `.claude/skills/` 不再有「鐵律」。
- 套用後路由卡 2,952 bytes，低於 3,000 bytes 的 tripwire（現在是 2,994）。

### 採用時跑的 M5 觸發測試

`claude -p` 每個 skill 2＋2 句，用 `--setting-sources project` 的夾具（與真實全域環境不同）。6 句正向都載入被測 skill；6 句反向都沒有誤載被測 skill，其中 2 句載入其他相符的 skill（`writing-principles`、`claude-api`）。

### 未跑

以下不是驗不了，而是本次範圍只出報告：

- **行為探針**：這些刪改對模型行為的影響沒有前後比較，移除都只是假設。M1、M3 建議用 `usage-review` 比較採用前後的工具呼叫數、finding 數與驗收輪數。
- **兩平台同步**：採用 Part C 的 Codex hunk 不需跑 `sync-codex-agents.py`（沒有動 TOML）；複本安裝的機器要跑 `sync-profile.py --apply --update`。

## Proposed diff

### Part A：`maintain-guideline` §1 標 ✅ 的檔，加上 §1 未列的 `usage-review`

包含 H1（`worktree-session`、`create-pr`）、M5、M6（`worktree-session`）、M7。`usage-review` 是 repo-only skill，§1 的權限表沒有列它，請你確認歸類。

```diff
diff --git a/.claude/skills/usage-review/SKILL.md b/.claude/skills/usage-review/SKILL.md
index 89822c9..8c6b89d 100644
--- a/.claude/skills/usage-review/SKILL.md
+++ b/.claude/skills/usage-review/SKILL.md
@@ -3 +3 @@ name: usage-review
-description: 量 Claude Code 本機 session jsonl 的用量與派工行為時使用：成本按 subagent 角色×model 拆帳、cache write 1h／5m 與過期重寫、主對話 context 膨脹、subagent 回報長度、派工平行度與 controller 自修次數、verifier 判定分布。觸發詞：量用量、成本拆帳、subagent 成本、context 膨脹、cache 過期重寫、派工行為、"usage review"、"token cost by agent"、"cost breakdown by subagent"。這不是帳單，也算不出訂閱額度百分比。
+description: 量 Claude Code 本機 session jsonl 的用量與派工行為時使用：成本按 subagent 角色×model 拆帳、cache write 1h／5m 與過期重寫、主對話 context 膨脹、subagent 回報長度、派工平行度與 controller 自修次數、verifier 判定分布。Use for usage or token-cost reviews by agent.這不是帳單，也算不出訂閱額度百分比。
@@ -47 +47 @@ python3 <SK>/scripts/report.py dispatch --data "$TMPDIR/ur-data.json" \
-| `controller` | 主對話 Edit／Write 與 Bash 寫檔 vs 派工數（逐專案目錄）；worker 交回後到下一個 verifier 派出前的改檔次數 | Bash 寫檔與「交回後」皆為啟發式 |
+| `controller` | 主對話 Edit／Write 與 Bash 寫檔 vs 派工數（逐專案目錄）；worker 交回後到下一個 verifier 派出前的改檔次數（只有含 worker 派工的 session 才有值） | Bash 寫檔與「交回後」皆為啟發式 |
diff --git a/global/shared/skills/agent-rules/SKILL.md b/global/shared/skills/agent-rules/SKILL.md
index b4b8f1f..f4e8fa0 100644
--- a/global/shared/skills/agent-rules/SKILL.md
+++ b/global/shared/skills/agent-rules/SKILL.md
@@ -3 +3 @@ name: agent-rules
-description: 建立或稽核某個專案 repo 的 AGENTS.md／CLAUDE.md 程式碼規則時使用：盤點常駐檔、詳細規則、AI reviewer 版本三層；把機械可驗的規則降級成 lint 或 CI 檢查而不留成散文；稽核常駐檔每條規則的標題能不能單獨判斷適用性；用單一來源加腳本產生索引並核對 reviewer 版本的 ID 與 severity。觸發詞：建 AGENTS.md、稽核 CLAUDE.md、整理專案規則、規則太多、哪些規則可以改 lint、"audit AGENTS.md"、"set up coding rules for agents"。不用於本工作系統自己的 rules／agents／skills（走 maintain-guideline），也不用於 README 等一般文件（走 writing-principles）。
+description: 建立或稽核某個專案 repo 的 AGENTS.md／CLAUDE.md 程式碼規則時使用：盤點常駐檔、詳細規則、AI reviewer 版本三層；把機械可驗的規則降級成 lint 或 CI 檢查而不留成散文；稽核常駐檔每條規則的標題能不能單獨判斷適用性；用單一來源加腳本產生索引並核對 reviewer 版本的 ID 與 severity。Use for auditing or setting up a repo's agent coding rules.不用於本工作系統自己的 rules／agents／skills（走 maintain-guideline），也不用於 README 等一般文件（走 writing-principles）。
diff --git a/global/shared/skills/create-pr/SKILL.md b/global/shared/skills/create-pr/SKILL.md
index a8c84a6..8359b05 100644
--- a/global/shared/skills/create-pr/SKILL.md
+++ b/global/shared/skills/create-pr/SKILL.md
@@ -199 +199 @@ rm -f "$PR_BODY_FILE"
-   - 使用者的 merge 指令只限這個 PR，不延伸到其他 PR 或之後的 PR（鐵律二逐次逐對象）。
+   - 使用者的 merge 指令只限這個 PR，不延伸到其他 PR 或之後的 PR（全域邊界 3：逐次、逐對象）。
diff --git a/global/shared/skills/worktree-session/SKILL.md b/global/shared/skills/worktree-session/SKILL.md
index fefb397..f7c9bd1 100644
--- a/global/shared/skills/worktree-session/SKILL.md
+++ b/global/shared/skills/worktree-session/SKILL.md
@@ -27 +27 @@ allowed-tools: Bash(git:*), Bash(gh:*), Bash(orca:*), Read, Grep, Glob
-**brief**：目標與動機、tracker 連結、base ref、共用觸點與禁止碰的路徑、完成定義、授權、交付檔路徑，以及「需要使用者決策或授權時：寫進 `result.md` 的 Pending authorization／Blocker，繼續做不被該答案擋住的部分，不用等鍵盤回答的工具停住等」。**授權**以 session 為單位（鐵律二）：brief 只能逐字引用使用者在盤點 session 對**該 issue** 明說的動作與對象，以「使用者原話：」開頭並註明對象 issue，上限 push feature branch＋開 PR；沒說就寫「無」。issue session 只認這段，merge、對外訊息與 brief 沒列的動作一律等使用者在該 issue 的分頁親口授權。
+**brief**：目標與動機、tracker 連結、base ref、共用觸點與禁止碰的路徑、完成定義、授權、交付檔路徑，以及「需要使用者決策或授權時：寫進 `result.md` 的 Pending authorization／Blocker，繼續做不被該答案擋住的部分，不用等鍵盤回答的工具停住等」。**授權**以 session 為單位（全域邊界 3）：brief 只能逐字引用使用者在盤點 session 對**該 issue** 明說的動作與對象，以「使用者原話：」開頭並註明對象 issue，上限 push feature branch＋開 PR；沒說就寫「無」。issue session 只認這段，merge、對外訊息與 brief 沒列的動作一律等使用者在該 issue 的分頁親口授權。
@@ -63 +63 @@ Merged: <merge SHA；merge 後補；未 merge 寫「—」>
-**要先問**：任一條判不出來或不成立就保留 worktree，回報原因；來源不明的 worktree／branch 要使用者明確授權才能刪（鐵律二）。
+**要先問**：任一條判不出來或不成立就保留 worktree，回報原因；來源不明的 worktree／branch 要使用者明確授權才能刪（全域邊界 3）。
@@ -79 +79 @@ Merged: <merge SHA；merge 後補；未 merge 寫「—」>
-不做：把 issue 拆給 subagent 當實作者；在 worktree 之間用複製檔案代替 git 合併；為了用某個 workspace 工具（Orca、Herdr、tmux、VS Code 分頁）而改變上述任何一步，它們只是 session 的容器，只提供 `references/container.md` 列的五個動作；讓 issue session 取得 brief 沒逐字引用的授權；把 git 無 conflict 當語意安全。同一 issue 內切片給多個 agent 平行做的 divide-and-conquer 與 agent race 流程已於 2026-10 日落，舊設計與理由見 `<REPO>/docs/reviews/parallel-dispatch-design-2026-09.md`。
+不做：把 issue 拆給 subagent 當實作者；在 worktree 之間用複製檔案代替 git 合併；為了用某個 workspace 工具（Orca、Herdr、tmux、VS Code 分頁）而改變上述任何一步，它們只是 session 的容器，只提供 `references/container.md` 列的五個動作；讓 issue session 取得 brief 沒逐字引用的授權；把 git 無 conflict 當語意安全。同一 issue 內不切片給多個 agent 平行做（divide-and-conquer、agent race），理由見 `<REPO>/docs/reviews/parallel-dispatch-design-2026-09.md`。
diff --git a/global/shared/skills/writing-principles/SKILL.md b/global/shared/skills/writing-principles/SKILL.md
index 6dec1d1..ddd989b 100644
--- a/global/shared/skills/writing-principles/SKILL.md
+++ b/global/shared/skills/writing-principles/SKILL.md
@@ -3 +3 @@ name: writing-principles
-description: 寫或改長存文件時使用——README、接入指南（quickstart／integration）、架構或設計說明、開發與發版流程、參考頁、wiki 頁（如 ClickUp、Confluence），新寫、改寫、整理都算；驗收這類文件時 verifier 也用本 skill 的判定與檢查腳本。觸發詞：寫文件、改寫 README、整理 docs、文件太亂、接入指南、架構說明、"rewrite the docs"、"doc cleanup"。不用於程式註解、commit message、PR 描述、issue、ADR、CHANGELOG，以及本工作系統的 rules／agent 定義／skill（那些走 maintain-guideline）。
+description: 寫或改長存文件時使用——README、接入指南（quickstart／integration）、架構或設計說明、開發與發版流程、參考頁、wiki 頁（如 ClickUp、Confluence），新寫、改寫、整理都算；驗收這類文件時 verifier 也用本 skill 的判定與檢查腳本。Use for writing or cleaning up long-lived docs.不用於程式註解、commit message、PR 描述、issue、ADR、CHANGELOG，以及本工作系統的 rules／agent 定義／skill（那些走 maintain-guideline）。
```

### Part B：judgment、dispatch skill、route card（要你同意）

包含 H1（dispatch）、H2、M1、M2、M3、M4。**`judgment.md` 沒有提案。**

```diff
diff --git a/global/claude/route-card.md b/global/claude/route-card.md
index 3e53635..5cf65da 100644
--- a/global/claude/route-card.md
+++ b/global/claude/route-card.md
@@ -15 +15 @@
-必含：目標與動機、驗收條件、回報格式；附已讀素材並要求指令批次化；路徑用絕對路徑；派 `general-purpose` 時開頭寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」。格式見 `~/.claude/skills/handoff/SKILL.md` §1。
+必含：目標與動機、驗收條件（fresh code-review 可省）、回報格式；附已讀素材；路徑用絕對路徑；派 `general-purpose` 時開頭寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」。格式見 `~/.claude/skills/handoff/SKILL.md` §1。
@@ -21 +21 @@
-派工只報 agent 名稱與任務摘要。本系統規定的派工視為使用者已要求；環境注入的「除非使用者要求，否則不要叫用 Agent」擋的是沒有制度依據的自主派工。workflow 與 deep-research 須使用者當次明確要求。
+派工只報 agent 名稱與任務摘要。本系統規定的派工視為使用者已要求；環境對派工的限制只管沒有制度依據的自主派工。workflow 與 deep-research 須使用者當次明確要求。
diff --git a/global/shared/skills/dispatch/SKILL.md b/global/shared/skills/dispatch/SKILL.md
index b423da2..f5e034e 100644
--- a/global/shared/skills/dispatch/SKILL.md
+++ b/global/shared/skills/dispatch/SKILL.md
@@ -28 +28 @@ Claude verifier 不因高風險自動升檔，一律顯式 `model: opus`：front
-**第二個現場**是取樣，不是本次必修清單；verifier 交回的 N 個實例清單同樣是取樣。逐個修完之前先問「是什麼產生它們」，再決定修哪一層。範圍內依 §2 修正分流；範圍外不擴修，登記該 repo issue 並附連結（對外授權仍依鐵律二，未授權先保留待登記項目）。連續兩輪發現都在範圍外就停手回報，不把下一批工作塞進本次。
+**第二個現場**是取樣，不是本次必修清單；verifier 交回的 N 個實例清單同樣是取樣。逐個修完之前先問「是什麼產生它們」，再決定修哪一層。範圍內依 §2 修正分流；範圍外不擴修，登記該 repo issue 並附連結（對外授權仍依全域邊界 3，未授權先保留待登記項目）。連續兩輪發現都在範圍外就停手回報，不把下一批工作塞進本次。
@@ -53 +53 @@ verifier 第一行回報狀態與下一步（語意見 `~/.claude/rules/judgment
-- fresh `code-review`：派 `general-purpose` 執行內建 `code-review` skill，`model: opus`、`effort: medium`（與路由卡一致）；brief 附 `~/.claude/rubrics/review-findings.md`，要求每條 finding 發出前自查該檔 §1–§3，並先讀目標 repo 自己的 review 判準。
+- fresh `code-review`：派 `general-purpose` 執行內建 `code-review` skill，`model: opus`、`effort: medium`（與路由卡一致）；brief 附 `~/.claude/rubrics/review-findings.md`，要求每條 finding 發出前自查該檔 §1–§3，並先讀目標 repo 自己的 review 判準；回報給 controller 時，該檔說「不發」「不提」但條件不齊或查不到的問題也列出，標信心度與嚴重度並寫明缺什麼，由 controller 過濾，純風格偏好仍不列。
@@ -58 +58 @@ verifier 第一行回報狀態與下一步（語意見 `~/.claude/rules/judgment
-**brief 必含三段**（欄位模板見 `~/.claude/skills/handoff/SKILL.md` §1『brief 卡』），缺一段就是不合格的派工：目標與動機（subagent 看不到主對話，脈絡要自帶）；驗收條件（可機械判定，自我檢查見 `~/.claude/rules/judgment.md` 12）；回報格式。三個非顯然的必要條件：**把已讀過的素材附進 prompt並要求指令批次化**（subagent 是冷啟動，每個它自己去讀的檔都是一輪完整推理）；**路徑一律絕對路徑**；派 `general-purpose` 時 **prompt 開頭明寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」**（它會讀到全域 `CLAUDE.md` 與 `~/.claude/rules/`，不加這句會把自己當 controller 逐層轉包；`Explore`／`verifier` 沒有 Agent 工具，可省）。要求 subagent 補齊某個格式欄位時同時規定「查無來源就留空」，否則原檔沒有的內容會被當場發明。
+**brief 必含三段**（欄位模板見 `~/.claude/skills/handoff/SKILL.md` §1『brief 卡』），缺一段就是不合格的派工（fresh `code-review` 從 diff 推 bug，驗收條件可省，見 §1）：目標與動機（subagent 看不到主對話，脈絡要自帶）；驗收條件（可機械判定，自我檢查見 `~/.claude/rules/judgment.md` 12）；回報格式。三個非顯然的必要條件：**把已讀過的素材附進 prompt**（subagent 是冷啟動，每個它自己去讀的檔都是一輪完整推理）；**路徑一律絕對路徑**；派 `general-purpose` 時 **prompt 開頭明寫「你是被派來的執行者，親自完成本任務，不要再呼叫 Agent 工具轉包」**（它會讀到全域 `CLAUDE.md` 與 `~/.claude/rules/`，不加這句會把自己當 controller 逐層轉包；`Explore`／`verifier` 沒有 Agent 工具，可省）。要求 subagent 補齊某個格式欄位時同時規定「查無來源就留空」，否則原檔沒有的內容會被當場發明。
@@ -80 +80 @@ verifier 第一行回報狀態與下一步（語意見 `~/.claude/rules/judgment
-- 動作屬於**發訊息或寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案（符合 worktree-session §3「直接清」的 issue worktree 與其 branch 除外）、改 CI／release 設定**，且本 session 尚未明確授權（鐵律二）。未授權就停止；已在本 session 明確授權時直接執行，不重複詢問。
+- 動作屬於**發訊息或寄信、merge PR、push 共享分支、發佈、刪除或覆蓋非自己建立的檔案（符合 worktree-session §3「直接清」的 issue worktree 與其 branch 除外）、改 CI／release 設定**，且本 session 尚未明確授權（全域邊界 3）。未授權就停止；已在本 session 明確授權時直接執行，不重複詢問。
@@ -94 +94 @@ verifier 第一行回報狀態與下一步（語意見 `~/.claude/rules/judgment
-- controller 看不到 statusline，要自己量：用 `<REPO>/docs/harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」的 jq 指令取最後一筆 usage 的三項和。每個實作 phase 開始前、打算一次讀入 ≥5 個未讀檔前各量一次。**≥300K 且還有未做的 phase**：寫 `~/.claude/skills/handoff/SKILL.md` §4『session 交接卡』，剩下的 phase 開新 session 接手，不派 subagent（subagent 不繼承 context，等於重新開始，還少了完整的 CLAUDE.md、hook 與記憶）。
+- controller 看不到 statusline，要自己量：用 `<REPO>/docs/harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」的 jq 指令取最後一筆 usage 的三項和。phase 交界與大量讀檔之後量。**≥300K 且還有未做的 phase**：寫 `~/.claude/skills/handoff/SKILL.md` §4『session 交接卡』，剩下的 phase 開新 session 接手，不派 subagent（subagent 不繼承 context，等於重新開始，還少了完整的 CLAUDE.md、hook 與記憶）。
```

### Part C：其他要先問的檔

包含 H1（Codex）、H3、M1（handoff）、M6（Codex）、M8、M9。這些檔在 `maintain-guideline` §1 同樣標為要先問；`maintain-guideline` 本身標 ❌。

```diff
diff --git a/.claude/skills/maintain-guideline/SKILL.md b/.claude/skills/maintain-guideline/SKILL.md
index 1cca64d..d0f4579 100644
--- a/.claude/skills/maintain-guideline/SKILL.md
+++ b/.claude/skills/maintain-guideline/SKILL.md
@@ -40 +40 @@ description: 修改本工作系統本身時使用——`global/**`（入口、ju
-| `global/claude/route-card.md`＋`global/shared/skills/dispatch/SKILL.md` | `global/codex/rules/dispatch.md` | 派工時機、升降級、驗證不自驗 |
+| `global/claude/route-card.md`＋`global/shared/skills/dispatch/SKILL.md` | `global/codex/rules/dispatch.md` | 派工時機、升檔條件、驗證不自驗 |
@@ -74 +74 @@ description: 修改本工作系統本身時使用——`global/**`（入口、ju
-- **活躍教訓硬上限 8 條**：滿 8 條要記新教訓，必須先升級或封存一條，不准「先加了再說」。
+- **活躍教訓硬上限 8 條**：滿 8 條時，先升級或封存一條再記新教訓。
@@ -90 +90 @@ description: 修改本工作系統本身時使用——`global/**`（入口、ju
-- **硬上限**：judgment 15 條、活躍教訓 8 條（見 §3）。加一條要先合併或日落一條，不准「先加了再說」；合併後總數 ≤15、或整條搬走且不留只剩動詞與檔名的骨架，才算空出名額。每條判準目標 ≤450 bytes：觸發情境、要做什麼、不算違規、指向。機制事實、指令、數字與『不算違規』邊界砍不動而超標**不算違規**，回報實際 bytes；砍到邊界句才是違規。
+- **硬上限**：judgment 15 條、活躍教訓 8 條（見 §3）。加一條要先合併或日落一條；合併後總數 ≤15、或整條搬走且不留只剩動詞與檔名的骨架，才算空出名額。每條判準目標 ≤450 bytes：觸發情境、要做什麼、不算違規、指向。機制事實、指令、數字與『不算違規』邊界砍不動而超標**不算違規**，回報實際 bytes；砍到邊界句才是違規。
diff --git a/global/claude/agents/verifier.md b/global/claude/agents/verifier.md
index 9722ea6..f1fcd19 100644
--- a/global/claude/agents/verifier.md
+++ b/global/claude/agents/verifier.md
@@ -10 +10 @@ effort: medium
-高風險驗收（文件／規則／架構決策／最終升級）與一般驗收用同一份合約與同一 model：派工者顯式帶 `model: opus`（與本檔 frontmatter 一致；顯式寫是防 fallback 到沒有 frontmatter model 的 agent 時繼承主對話）。改用 `model: fable` 的條件與例外以 `~/.claude/skills/dispatch/SKILL.md` §1「驗證不自驗」為準，訊號清單見 `<REPO>/docs/reviews/verification-policy-history.md`「fable 升檔訊號」。
+高風險驗收（文件／規則／架構決策）與一般驗收用同一份合約與同一 model：派工者顯式帶 `model: opus`（與本檔 frontmatter 一致；顯式寫是防 fallback 到沒有 frontmatter model 的 agent 時繼承主對話）。改用 `model: fable` 的條件與例外以 `~/.claude/skills/dispatch/SKILL.md` §1「驗證不自驗」為準，訊號清單見 `<REPO>/docs/reviews/verification-policy-history.md`「fable 升檔訊號」。
diff --git a/global/codex/rules/delegation-templates.md b/global/codex/rules/delegation-templates.md
index c325cb5..c0d018f 100644
--- a/global/codex/rules/delegation-templates.md
+++ b/global/codex/rules/delegation-templates.md
@@ -5 +5 @@
-> v4（2026-10-29）起只有六份模板：查詢 A／B／F、review G、驗收 J／L。實作與規劃不派 subagent，沒有對應模板。
+> 模板共六份：查詢 A／B／F、review G、驗收 J／L。實作與規劃不派 subagent，沒有對應模板。
diff --git a/global/codex/rules/dispatch.md b/global/codex/rules/dispatch.md
index da5d87a..7997a70 100644
--- a/global/codex/rules/dispatch.md
+++ b/global/codex/rules/dispatch.md
@@ -7 +7 @@
-controller 在主對話自己做實作與文件；subagent 只剩三類：fresh-context 驗收（`verifier`／`sol_verifier`）、fresh review（`reviewer`）、旁支查詢（`scanner`／`explorer`）。實作型角色（worker、pro_worker、recovery_worker、escalation_worker）與規劃型角色（planner、escalation_planner）於 v4（2026-10-29）日落，理由與量測見 `<REPO>/docs/reviews/v4-2026-10.md`。平行開發與多 issue 走 `<REPO>/global/shared/skills/worktree-session/SKILL.md`：一 issue 一頂層 session，各在自己的 worktree，不派實作型 subagent。
+controller 在主對話自己做實作與文件；subagent 只剩三類：fresh-context 驗收（`verifier`／`sol_verifier`）、fresh review（`reviewer`）、旁支查詢（`scanner`／`explorer`）。實作與規劃不派 subagent，理由與量測見 `<REPO>/docs/reviews/v4-2026-10.md`。平行開發與多 issue 走 `<REPO>/global/shared/skills/worktree-session/SKILL.md`：一 issue 一頂層 session，各在自己的 worktree，不派實作型 subagent。
@@ -109 +109 @@ controller 應在 brief 附上仍有效的 diff、檔案行號／段落與測試
-## 6. 驗證語意（鐵律三）
+## 6. 驗證語意
diff --git a/global/shared/skills/handoff/SKILL.md b/global/shared/skills/handoff/SKILL.md
index a7679f4..3cc97ca 100644
--- a/global/shared/skills/handoff/SKILL.md
+++ b/global/shared/skills/handoff/SKILL.md
@@ -22 +22 @@ Phases：<逐 phase；每 phase 跑哪些驗證>
-Validation commands：<逐條可執行；能一次串完的批次化>
+Validation commands：<逐條可執行>
```
