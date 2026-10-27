# 全域 Claude／Codex 規則：載入與用量日落審查（2026-10-19）

## 結論先行

這份審查的建議不是「規則少了就會延後 Max weekly limit」。本機資料顯示，最大已知可控成本是主對話的長 context 與標準 `worker` 的大量 request；全域靜態規則是可量測、值得減少的固定輸入，但不是 weekly 配額的換算單位。Claude 官方也明確把模型、effort、訊息與對話長度、附件、tool usage 都列為用量因子，且 Max 的五小時與 weekly limit 跨 Claude／Claude Code 共用。[Usage limit best practices](https://support.claude.com/en/articles/9797557-usage-limit-best-practices) [Pro/Max plan and Claude Code](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)

優先順序如下；全都是**後續修改授權候選**，本報告沒有修改任何規則或設定。

新增的總原則是：**先審所有權與是否需要全域常駐，再談壓字句**。專案規格優先能解決衝突，但不會自動消除兩份 context；要逐項判斷是刪除、由 project 負責、skill 化、agent contract 承接，或保留全域最低邊界。

1. **P0，先量後改**：以相同類型工作、固定期間比較 main context、worker 在窗口可見的首 request、重複修正／escaped defect 與 Usage 畫面的 weekly 曲線；先做兩個低風險 A/B 實驗：語言段落、Codex named-role prompt。任一品質指標退步立即回退。
2. **P1，最小且最有把握的瘦身候選**：現有 user-level Claude `language` 設定已是「繁體中文台灣用語」，以可回退 A/B 驗證其是否足以取代 [`CLAUDE.md:6-8`](../../CLAUDE.md#L6) 的重複語言句。技術名詞／程式碼原文是另一個語義，不能因為 `language` key 存在便直接宣稱已涵蓋。
3. **P1，保留安全核心、審查 controller fan-out**：不是先砍 verifier。先檢驗 [`rules-controller/10-dispatch.md:43-46`](../rules-controller/10-dispatch.md#L43) 對素材探索、完整 plan、fresh repair 與驗收輪次的組合，是否把 routine 工作推成不成比例的 `Explore → worker → verifier` request 數。現行「一次 review／按風險做 delta」已是抑制機制，不能又提成新規則。
4. **P2，拆出少數真正在常駐區的細節**：把 `rules/20` 的工具／Git 細節、`rules/00` 的使用者背景、`rules/50` 的工具專屬教訓改為有觸發條件的資料；保留不可逆授權、環境 gotcha、產物／negative evidence 的可判定邊界。
5. **P2，Codex dispatch 僅做 named-role 實驗**：現行 adapter 與 A–L 模板總計很長，但不是 Codex session 的自動初始內容。先證明 named role 已有角色合約後，能否只傳 task-specific plan；generic fallback／direct CLI 仍傳完整 adapter 合約。未證實前不縮短。

## 範圍、證據與不作的推論

審查基準是 `51b04f29cbdf0d918a72d1081d8a2ffa4c7adf17`，目錄為本公開工作制度 repo。本報告只涵蓋其全域 Claude／Codex 入口、常駐 rules、controller hook、角色定義、Codex dispatch、parallel-dispatch skill，以及本機聚合 usage。usage extractor 在本機程式解析 local logs，但本輪未人工展開完整 transcript，也未將原文或私有專案內容納入報告；聚合輸出刻意不含 repo slug、session title、raw heads。

證據分三類：

| 分類 | 本報告採用方式 | 不可推出的結論 |
|---|---|---|
| 靜態檔案 bytes／行數 | `wc -lc`，可重算載入候選集合 | 不是 token，也不是帳單或 subscription quota |
| Claude／Codex 官方文件 | 載入時機、settings scope、skills／subagent 語義、用量因子 | 不是此機器實際 prompt 或 weekly 因果 |
| 近 7 日本機聚合 telemetry | context、role／model、request 與 API 表價等價組成 | 不含 claude.ai、其他機器；不是帳單、也不能把 API 價格等同 Max 配額 |

### 載入成本模型

令 `B` 為 UTF-8 bytes，`T` 為某次 request 實際 input／cache token，`Q` 為帳戶在某一 weekly window 的剩餘 allocation。只有 `B` 在這次檔案盤點中可直接相加；`T` 還受 system prompt、chat history、工具結果、plugin／MCP、動態 hook 與選中的 agent 影響；`Q` 的計量未由 Anthropic 公開為 `B` 或 `T` 的固定函數。既有校準也只是一個舊的中英混合檔樣本（2.07 bytes/token），不適用於本集合的通用換算。[`docs/harness-facts.md:81-84`](../harness-facts.md#L81)

因此只使用下列安全陳述：刪除**確實載入**的內容，會降低那個情境的靜態 bytes；是否降低 token、cache write/read、輸出、總 request、或延後 weekly limit，必須用相同工作類型的 before/after 量測確認。

## 已量測的載入集合

`wc -lc` 於上述基準、2026-10-19 執行。數字是檔案候選量，不表示可整塊刪除。

| Claude 載入情境 | 組成 | Bytes | 解讀 |
|---|---|---:|---|
| 全域 shared | `CLAUDE.md` 3,943 + `rules/*` 16,923 + 本機 host 1,428 | 22,294 | `CLAUDE.md` 明示 rules 每 session 常駐，並 `@` 匯入 host facts；custom worker／verifier 也繼承。[`CLAUDE.md:10-16`](../../CLAUDE.md#L10) [`docs/harness-facts.md:70-78`](../harness-facts.md#L70) |
| Claude controller | shared + `rules-controller/*` 25,016 | 47,310 | controller files 由 SessionStart 注入主對話、custom agent 不繼承。不是每個 subagent 固定成本。[`docs/harness-facts.md:77`](../harness-facts.md#L77) |
| Claude `worker` | shared + role file 6,775（含 frontmatter） | 29,069 | 不含 Claude 的內建 system prompt、專案檔、工具結果與 brief。[`agents/worker.md:1-13`](../agents/worker.md#L1) |
| Claude `verifier` | shared + role file 7,897（含 frontmatter） | 30,191 | 同上；不能將 fresh-context 驗收的價值當作可任意刪除的重複。[`agents/verifier.md:1-10`](../agents/verifier.md#L1) |
| Codex global entry | `AGENTS.md` | 6,495 | 入口要求按情境讀其他文件，不等同把所有後續檔案注入。[`AGENTS.md:17-36`](../../AGENTS.md#L17) |
| Codex dispatch materials | dispatch 28,438 + A–L templates 22,937 | 51,375 | 是 controller 派工／模板工作量；不是已證實的每-agent 初始注入。[`codex/rules/10-dispatch-codex.md:1-4`](../codex/rules/10-dispatch-codex.md#L1) [`codex/rules/30-delegation-templates-codex.md:1-35`](../codex/rules/30-delegation-templates-codex.md#L1) |
| 平行派工 Claude adapter | core 24,732 + Claude reference 5,599 | 30,331 | 只在並行切分觸發，不能誤列進一般 session 初始成本。[`skills/parallel-dispatch/SKILL.md:1-18`](../skills/parallel-dispatch/SKILL.md#L1) |

本 repo 自己當工作目錄時，global `AGENTS.md` 同時也是 project entry，當前表面可能重複呈現相同內容；這是維護本制度 repo 的局部成本，不應外推到每一個一般專案。

## 官方查證：可安全依賴的產品語義

### Claude Code

- `CLAUDE.md` 是每 session 的 persistent project/user/managed instruction；官方建議放每 session 都需要的事實，把多步程序或局部內容放 skill 或 path-scoped rules。文件也說明它會在每個 request 佔 context，即使 prompt caching 可降低後續計費。 [Memory](https://code.claude.com/docs/en/memory) [Models, usage, and limits](https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code)
- 官方的載入表區分：`CLAUDE.md` 全文 session-start／每 request、skill 初始僅 description 且 invocation 才全文、MCP schema on demand、subagent 是隔離 context；被 agent `skills:` 明列的 skill 則會預先全文載入。 [Extend Claude Code](https://code.claude.com/docs/en/features-overview)
- output style 是每 response 的 role/tone/format 指令；它可管回覆風格，但不保證動作，也不改變一般 subagent 的自有 system prompt。 [Output styles](https://code.claude.com/docs/en/output-styles)
- `~/.claude/settings.json` 是 user scope，適用本機所有專案；settings 有 precedence，應以 `/status` 確認文件來源是否載入。 [Settings](https://code.claude.com/docs/en/settings)
- 官方 settings schema 的 `language` 是 preferred response language key；其 description 說預設以該語言回覆，並影響 voice dictation 與 terminal tab title。它不是台灣詞彙／技術名詞政策的機械保證。 [Settings reference—language](https://code.claude.com/docs/en/settings-reference#language)
- 官方列 Max 的 five-hour 與 weekly limits，且 Claude／Claude Code 共用；`/status` 與 Settings > Usage 是可觀察使用量的入口。它沒有公布「檔案 bytes／tokens 對 weekly 配額」的轉換率。 [Pro/Max plan and Claude Code](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) [Usage limit best practices](https://support.claude.com/en/articles/9797557-usage-limit-best-practices)

### Codex

本輪也核對 OpenAI 官方文件：`AGENTS.md` 是 global/project chain，skill 初始載入是 catalog、selected skill 才全文，subagent 是額外 token／不同 model-effort 的決策單位。這些描述支持「不要把按需資料誤算成初始注入」，但沒有替本機 runtime 做過 prompt token probe；故 Codex finding 仍是實驗而非節省宣稱。[AGENTS.md configuration](https://learn.chatgpt.com/docs/agent-configuration/agents-md) [Build skills](https://learn.chatgpt.com/docs/build-skills) [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

## 本機近 7 日 usage：優先管哪裡

期間是 2026-10-12 00:00 至 2026-10-19 00:00（+08:00）。抽取命令為：

```sh
python3 skills/usage-review/scripts/extract.py \
  --since 2026-10-12T00:00 --until 2026-10-19T00:00 --tz +08:00 \
  --out /tmp/global-rules-review.GcfDVQ/data.json
```

結果：193 sessions、942 agents、47,281 requests；`unpriced=0`、`retyped=0`、`unknownTTL=0`，且 TTL 子項未超總額。實際最後 event 是 2026-10-18 21:41:16 +08:00，並已核對 47,281 個 unique `(mid,rid)`。其後只以不含 slug/session-title/raw-head 的 summary／role-family／component tables 聚合。

| 指標 | 數值 | 可得出的行動 |
|---|---:|---|
| main 模型占 raw API-equivalent | Opus 44.9999% + Fable 3.6323% + Sonnet 0.0359% + Haiku 0.0002% = **48.6683%** | 先控制 main context／長 session；非直接降 rules 即可解。 |
| `worker` / `verifier` | 33.4841% / 10.7522% | worker 是較大的次要槓桿；不要把 verifier 當首要浪費來源。 |
| general-purpose / Explore / Plan | 5.3996% / 1.0005% / 0.6054% | fan-out 是否有必要需 task-class 抽樣，比例本身不足以下刪。 |
| 主對話 context | median 184,954；P90 330,118；max 581,941；>400k 為 4.4% requests | 支持優先研究 task boundary、compact／clear 與回報落檔，而非只壓幾百 bytes。 |
| 窗口可見首 request context | worker median/P90 28,620/35,465；verifier 26,785/34,498；general-purpose 43,751/50,803；Explore 15,056；Plan 14,244 | 角色 static prompt 只是其中一部分；worker 數量與 task brief 值得比對。 |
| final report 字元 median | worker 4,642；verifier 4,379；general-purpose 1,095；Explore 12,298；Plan 13,694；codex-rescue 10,164 | 字元不是 token；但指出回報結構與主對話累積仍應被抽樣檢驗。 |
| component share | cache read 52.447%、1h write 18.4721%、5m write 17.2983%、output 11.7696%、input 0.013% | 可把「減少重讀／過期重寫」列為實驗主目標；不可拿 API 價格直接解釋 Max weekly。 |

raw API price snapshot（repo 於 2026-10-06 的表）算得 $3,131.02860047 等價值；它**不是**帳單、不是 subscription 額度、不是當日官方價格，且 `out_est_nonnull=0`、advisor 缺失、不含其他機器與 claude.ai。窗口可見首 request 也可能是 10-12 前已啟動／續用 agent 的首筆，而非冷啟動；不同專案、brief、tool 混雜。因此角色比例只用來排實驗優先，不能稱為精確真實支出結構，更不能預測節省多少週配額。

既有實測已證明 controller rules 分流能降低 custom agent 首 request；同時也證明 `omitClaudeMd` 會連 project spec 與語言設定一起消失，所以不是本輪可直接採用的省 token 手段。[`docs/harness-facts.md:89-98`](../harness-facts.md#L89) 現有 plugin 差約 3.8K tokens 的歷史 probe 也只量到整體 plugin／hook，互動額外約 28K 未拆因，不能把它全怪到 9 個 enabled plugins。[`docs/harness-facts.md:118-133`](../harness-facts.md#L118)

## 檔案逐項分類與 findings

分類定義：**保留**＝本輪未看到安全的縮減點；**搬移／合併候選**＝內容可能在錯的載入層，先比資訊量；**實驗**＝產品或 runtime 語義尚不足以安全改；**刪除候選**＝只在實驗／審查證據成立後才可日落。

| 主要檔案／集合 | 分類 | 結論 |
|---|---|---|
| `CLAUDE.md` | 實驗 + 保留路由 | 語言句候選外移到已存在的 setting；常駐載入說明、三鐵律與 routing 仍是 bootstrap。 |
| `rules/00-environment.md` | 搬移候選 | 使用者背景與 controller-only compact/handoff 不是所有 agent 都需要；真實環境風險仍保留。 |
| `rules/05-hosts.md` + `hosts/macos.md` | 保留 | host lookup／缺檔 sentinel 有已知 `@import` 靜默失敗風險，不能因模型進步刪除。 |
| `rules/20-judgment.md` | 保留核心 + 搬移候選 | 完成證據、風險與檢查放寬的 guardrail 保留；Git convention 與可觸發的工具細節候選下沉。 |
| `rules/50-lessons.md` | 保留機制 + 搬移候選 | 8 條硬上限和升級／封存機制保留；工具專屬教訓應確認是否能由 task trigger 發現。 |
| `rules-controller/10-dispatch.md` | 實驗 | 主對話專用分流已正確；檢驗 routine task 是否被強制 Explore/Plan 素材路徑放大。 |
| `rules-controller/20-judgment-controller.md` | 保留決策語義／controller owner + 搬移候選 | escalation 與 delta closing 的 owner／判定保留；詳細流程可移到按需 skill，不等於永遠全量常駐。 |
| `agents/worker.md` | 實驗 | xhigh 與完整 plan gate 可能是品質投資；依 task class 做 Sonnet effort 與 plan-detail A/B，不直接降級。 |
| `agents/verifier.md` | 保留核心 + 快速搬移 | fresh context、PASS/FAIL/UNSURE、fixed evidence set 屬驗收語義；可只移理由／歷史數字，不縮核心判定。 |
| `AGENTS.md` | 保留 | 它是 Codex routing bootstrap；目前本 repo 自己造成的重複呈現是局部問題。 |
| `codex/rules/10-dispatch-codex.md` + `30-delegation-templates-codex.md` | 實驗／合併候選 | 大量重複在 adapter、template、role prompt；先分 named vs fallback runtime，再決定 canonical / 省略內容。 |
| `parallel-dispatch` skill + references | 保留按需 | 大但非一般初始載入；不要為字節數破壞 worktree／ownership／integration gate。 |
| `rubrics/*`、`codex/agents/*.toml` | 保留按需／角色註冊 | 本輪未列為 Claude 初始載入；rubric 只在驗收、TOML 只在 Codex named-role 安裝／runtime 選路時考慮。 |
| `skills/maintain-guideline/SKILL.md`、`docs/harness-facts.md` | 保留按需 | 分別 20,189 bytes／長證據庫，但非每 agent 固定；是審查與實驗的依據，不是首波 token 目標。 |

### 可直接提案的文字搬移／去重清單（未授權，gross bytes 不可相加）

下列是「不改行為設計、先比較 canonical 是否完整」的高信心候選；每筆仍需使用者授權、路徑 read-back 與 fresh verifier，但不必把每一筆文字搬移升格成昂貴模型 A/B。bytes 有重疊，故只作每項上限提示、不可合計成預估收益。

| 候選 | Gross bytes | 建議與保留物 |
|---|---:|---|
| `agents/verifier.md:22` 的歷史理由 | 366 | 搬到 rationale/docs；保留 `:14-20` 的找碴邊界與可判定職責。 |
| `rules/00-environment.md:27` 的 compact/handoff 說明 | 703 | 移 controller-only context；global rules 留可發現的短 trigger。 |
| `agents/worker.md:3`、`agents/verifier.md:3` 的長 description | 474 / 400 | 壓為 task matching 所需的適用範圍；frontmatter model/effort、runtime 能力與 body 的責任邊界不刪。 |
| `agents/worker.md:31` 的 model/parameter 解釋 | 446 | 主要是 controller routing 資訊；先核對 controller/harness facts 已完整承接，再移到按需說明，保留 runtime evidence 的必要句。 |

### FIND-01 — 語言重複是最小可回退實驗

- **現況**：[`CLAUDE.md:6-8`](../../CLAUDE.md#L6) 有 194 bytes 的語言段；本機 user settings 已經以白名單讀回相同「繁體中文台灣用語」值。官方 schema 支持 `language` 做預設回覆語言，但不保證術語規則。
- **建議**：先只在隔離設定／新 Claude session 做低成本代表性抽樣：移除 global `CLAUDE.md` 的語言句，保留 user `language`，檢查回覆語言、台灣用語、程式碼、library/API/CLI 名稱。若有術語漂移，回退並測一行「程式碼與明確技術名詞保留原文」是否足夠；不要把完整語言段直接刪掉。
- **平台差異**：Claude 有 user language setting；Codex 本輪沒有同一個已查證設定 key，`AGENTS.md:13-15` 的語言段不可隨 Claude 一起移除。
- **風險／驗收**：抽樣需涵蓋繁中議題、英文 tool output、code review、對外文字；數量是執行者依可用任務決定的小樣本 early-warning，不是新硬門檻。任何指令誤解即 rollback；rollback 是還原單一段落。

### FIND-02 — controller 的成本是「讀到」與「派出」的組合，不是 bytes alone

- **現況**：controller 在 hook 中取得 25,016 bytes，但 custom worker／verifier 不繼承它；[`rules-controller/10-dispatch.md:39-48`](../rules-controller/10-dispatch.md#L39) 已避免預設多輪 review。第 43 行的 (a)/(b) 是「controller 自取素材」的窄例外，不是聲稱已知 scope 的有界少數檔案一律不能直接核定；跨時序／新 gate 才要求 Plan + 第二意見。
- **建議**：從近 7 日取可取得的小型分層樣本，標記被派出的角色、必要性、改動檔數、驗證結果、後續修正。只對「scope 已明、必要段落已在 brief、非跨時序／安全」的 routine cohort 試行擴大既有 direct-plan 例外；其餘維持現狀。樣本數是執行者依資料可用性選的 early-warning，不是採納門檻。
- **平台差異**：Claude 的 Explore／Plan 不繼承 shared rules，Codex logical role 則靠 adapter/contract；不能把一方的派工減法套到另一方。
- **風險／驗收**：比較首次完成率、測試／verifier finding、二次修正、context/request；若 direct-plan 增加任一高風險 omission 或 verifier `OPEN`，停止 cohort 擴大。這是「派工閘門」實驗，不是放棄 fresh-context 驗收。

### FIND-03 — worker 是較大的實驗槓桿；xhigh 不是自動過時

- **現況**：[`agents/worker.md:1-7`](../agents/worker.md#L1) 宣告 Sonnet 5.5/xhigh；近 7 日 worker 占 raw 等價 33.4841%、351 個窗口可見首筆 median 28,620 context、每 agent median 46 requests/49 tools。完整 plan gate 和一次明確 execution-mistake 補正見 [`agents/worker.md:11-28`](../agents/worker.md#L11)。
- **建議**：按 task class 做兩個分離的單變因試驗：先固定 approved plan 細節只比較 xhigh 與 medium/high；若不劣，再固定 effort 比較較短 plan brief。只在各自結果不劣且 input/output/request 有下降時，才考慮改預設。
- **平台差異**：Claude 的 frontmatter xhigh 和 Codex `worker/Luna max` 不是同一模型／effort 語義；兩端分開對照，不能用 Claude 結果改 Codex routing。
- **風險／驗收**：preserve approved-plan、不擴 scope、測試與 fresh verification；比 complete-first-pass、rework、escaped defect、agent requests、context／cache components。若 quality 降，保留 xhigh。

### FIND-04 — verifier 可移理由，不能以「模型更強」移除驗收語義

- **現況**：verifier 占 10.7522%，低於 worker；[`agents/verifier.md:14-37`](../agents/verifier.md#L14) 的職責包括區分行為承載產物、PASS/FAIL/UNSURE、固定 delta evidence set。`rules/20` 也要求放寬既有檢查時有 frozen baseline 與對抗探測。[`rules/20-judgment.md:43-50`](../rules/20-judgment.md#L43)
- **建議**：只先盤點 role description／body 裡的歷史理由、已被 canonical 規則完整承接的解釋；若搬移，保留可判定的命令、狀態與禁止範圍。不要按每份文件都強制高成本 runtime probe；依現有風險／產物類型規則分流。
- **平台差異**：Claude verifier 的 read-only tools/合約與 Codex verifier 的 workspace-write probe contract 不同，不能合併成單一模糊條文。
- **風險／驗收**：以少量歷史 OPEN/INCONCLUSIVE 與 CONVERGED 產物做 blind replay；數量是可調的 early-warning 樣本，不是新儀式。任何原有 FAIL 消失或越權寫入，即回退。

### FIND-05 — `rules/20` 有明確下沉候選，但核心判準不是「舊模型補丁」

- **現況**：全檔 10,206 bytes；`14-55` 的驗證細節約 5,955 bytes，`65-69` Git convention 約 818 bytes。核心完成／證據／高風險分界在 [`rules/20-judgment.md:7-12`](../rules/20-judgment.md#L7)；工具細節已有指向 docs 的設計。[`rules/20-judgment.md:18-23`](../rules/20-judgment.md#L18)
- **建議**：將「每 session 未必會 commit/PR」的 Git convention 移到 commit／create-PR 的觸發入口，或保留一條極短的常駐 commit trigger，使獨立 commit 也能發現；將可由特定變更類型觸發的命令細節收斂到 debug docs。保留一句 trigger、最低保證與 canonical link，不能只剩動詞與檔名。
- **平台差異**：shared judgment 是兩端的語義錨；Claude/Codex dispatch 編號、sandbox 與角色不同，只能各自引用同一 canonical 不能互抄。
- **風險／驗收**：用 mutation briefs 檢查「放寬既有檢查」「CI-only 路徑」「巢狀 repo」仍選到正確 guardrail；找不到 rule 的任務要自動被 skill／routing 發現。若只是文字搬移，不額外虛構 runtime 成本驗證。

### FIND-06 — 環境事實、授權與裝置 gotcha 不因模型改善而日落

- **現況**：`rules/05` 的 sentinel 對抗 `@import` 缺檔靜默略過；[`docs/harness-facts.md:77-83`](../harness-facts.md#L77) 已有此 failure mode。`rules/00` 的使用者背景約 749 bytes，compact/handoff 有 controller-only 成分；`rules/50:9-12` 的工具專屬活躍教訓約 789 bytes。
- **建議**：使用者背景搬入 profile/memory 或只在需要風格化輸出時載入；compact/handoff 搬到 controller context；工具專屬 lesson 轉為明確 task trigger，且要先證明觸發發現率不降。
- **保留理由**：host/port/CLI/sandbox/installation、對外與不可逆授權、artifact evidence、negative-test semantics 是模型無從推知的真實環境／責任邊界。它們不是「模型變強就會自然做到」的教學。
- **風險／驗收**：在 macOS 及另一安裝形狀重跑 `@import` sentinel、host lookup、受限命令與新機器 bootstrap；發現一個未引導的錯誤便回退。

### FIND-07 — Codex adapter/模板有高重複潛力，但 runtime 證據不足

- **現況**：Codex §0 規定每次派工記錄 adapter envelope，A–L 以完整 role contract 重複安全限制、plan 欄位、驗收／回報格式；worker template 例見 [`codex/rules/30-delegation-templates-codex.md:80-93`](../codex/rules/30-delegation-templates-codex.md#L80)，verifier 例見 [`:169-184`](../codex/rules/30-delegation-templates-codex.md#L169)。實際 spawn surface 的 `fork_turns` 預設是 `all`；本次 fresh analysis agent 才明確 `none`。
- **建議**：做三組 matched named worker/verifier task：(a) 目前完整 envelope+contract、(b) 保留 envelope 和 task-specific plan、(c) named role 最小 task-specific brief；generic/default/direct-CLI 一律仍完整。逐一 read-back actual role、model/effort、permission、scope escape、test/result、父 context tokens。
- **平台差異**：Claude named agent body 是角色 prompt；Codex named role 有 runtime metadata 與 adapter 不確定性，fallback 更不能省。禁止把 Claude agent 簡化結果直接移植。
- **風險／驗收**：任何 runtime identity 未證實、越權、漏跑驗證或回報缺欄，(b)/(c) 失敗；保留現行完整 prompt。這個實驗同時驗證 `fork_turns: none` 是否真的提供 fresh context，不只看參數。

### FIND-08 — controller 詳細規則可測「route card + on-demand」，不是直接取消 hook

- **現況**：controller 的 25,016 bytes 在每個主對話透過 SessionStart 注入；這個分流已把成本從 custom agent 移走，且 compact 後的 reinjection 是設計動機。[`docs/harness-facts.md:89-97`](../harness-facts.md#L89)
- **建議**：以 10 個不派工／單點小修與 10 個需派工的 matched sessions 為可調整起點（不是硬門檻），測試一張極短 route card（鐵律、何時讀 dispatch、驗收入口）加上要派工時才讀完整 controller files。不要改 hook 前就假定這一定較省，因為 on-demand read 與漏讀都可能反而增加 request。
- **平台差異**：本 repo 已採用的是 Claude SessionStart 注入方案；Codex 官方也支援 `SessionStart`／`SubagentStart`、stdout／`additionalContext` 注入與 compact 後重注入。本 repo 尚未採用等價的 Codex controller 分流方案，本機等價設定與繼承行為未實測，不能直接共用 patch；後續可另列比較候選。[Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- **風險／驗收**：小修不能誤派或越權；派工 task 必有完整 approved plan、正確 model/role、fresh verification。任一 controller 忘讀 detail 而違反 gate，即回退全量 injection。

### FIND-09 — skill／plugin catalog 應依可發現性與實際使用做減法

- **現況**：官方說可供模型呼叫的 skills 每 request 至少有 name/description；manual-only (`disable-model-invocation: true`) skill 在呼叫前不載入。現有 9 enabled plugins 的整體歷史差約 3.8K tokens，但沒有逐 plugin 歸因。 [Extend Claude Code](https://code.claude.com/docs/en/features-overview) [`docs/harness-facts.md:118-133`](../harness-facts.md#L118)
- **建議**：先以 30 日 invocation/工具呼叫率作為可調整起點（不是硬門檻），建立 plugin、skill 的「高頻必要／低頻但模型需自動發現／只由人手動叫」三欄清單；只將最後一欄在 isolated config 試設 manual-only，或停用確定無用的 plugin。不要因檔案大就移除 `parallel-dispatch` 等按需高風險工作流。
- **平台差異**：Claude 有 `disable-model-invocation`；Codex skill catalog/設定上限是另一 surface，僅有官方一般語義，需另外量測。
- **風險／驗收**：每個試驗 task 都要量 skill 被正確發現率、tool 成功率與初始 context；遺漏必需 skill 即回退。3.8K 是歷史觀察，非承諾收益。

### FIND-10 — 「零命中」是去重安全閘門，不應退化成每次改字的形式成本

- **現況**：維護協議要求刪重前確認每個關鍵詞仍有命中並比較語意方向，目的是避免 canonical 遺漏授權入口。[`skills/maintain-guideline/SKILL.md:96-98`](../skills/maintain-guideline/SKILL.md#L96)
- **建議**：把它限定於刪除／合併行為規則、授權、runtime facts 的 checklist；純語病、標題與不改語義的搬移只驗路徑／anchor。對真正去重改用「舊條目的 action、trigger、boundary、owner 是否仍可從 canonical 讀出」矩陣，不以 keyword 0/非 0 當完整語意判定。
- **平台差異**：同一語意守門在 Claude/Codex 都需要，但文件編號與 runtime facts 不同，矩陣要各列證據來源。
- **風險／驗收**：以少量既有高風險重複條目做 mutation：刪掉唯一的授權、fallback、或 exception 必須被矩陣抓到；純搬移不應增加 verifier/runtime probe。這是維護流程實驗，不是讓模型自行判定「大概涵蓋」。

### FIND-11 — Explore／Plan 的長回報是執行落差，先修 brief 而非加字數上限

- **現況**：窗口中 Explore/Plan 的 final report median 分別為 12,298/13,694 字元，高於 worker/verifier；但現有 controller 已要求回 controller 下一步需要的結論與證據、不要傾倒原文，並明說不靠固定字數上限。[`rules-controller/10-dispatch.md:81-86`](../rules-controller/10-dispatch.md#L81)
- **建議**：在 Explore/Plan brief 固定要求「affected paths、關鍵 invariant、必要片段定位（file:line range）與未決問題」，不抄原文或逐檔摘要；沒有新字數限制。抽樣比較 final chars、回到 main 的 input 與返工，先確認是 brief 執行落差而非角色工作本身必需。
- **平台差異**：Claude Explore/Plan 與 Codex explorer/planner 的檔案可寫性、注入 context 不同；各自測 brief compliance，不能共用中位字數門檻。
- **風險／驗收**：controller 若需要原文，應從指定位置 read 而不是靠摘要猜；若被壓縮的回報漏掉影響 scope 的 invariant，回退該 brief。

### FIND-12 — 突變證據可按獨立保護行為合併，不可整體取消

- **現況**：worker 對新增／修改 assertion 或 gate 要求紅／綠突變，[`agents/worker.md:21-23`](../agents/worker.md#L21)；judgment rule 也把修正者的 assertion/gate 證據寫入 delta brief。[`rules/20-judgment.md:23`](../rules/20-judgment.md#L23) 本輪沒有把每條 assertion 的實際成本與逃逸缺陷逐一對應。
- **建議**：先盤點同一個 mutation 是否同時證明多個 assertion／同一負向保證；可合併重複 probe、重用同一紅／綠證據。安全、負向或新的獨立保護行為仍各保留至少一個能失敗的證據；不要聲稱「新模型因此不需 mutation」。
- **平台差異**：Claude worker contract 的暫時變異／還原步驟和 Codex worker 的 validation contract 不同；共用的是「證據必能失敗」語義，不是命令模板。
- **風險／驗收**：以高風險與一般 gate 各抽一組，確認合併後每個原 assertion 仍有明確反例；若無法指向，分開保留。這是按風險的去重，不是所有測試一律加或砍。

### FIND-13 — 專案規格優先；全域保留能力與最低邊界，工作流程按需 skill 化

- **使用者方向（判斷）**：全域規則若與各專案的 `CLAUDE.md`／`AGENTS.md` 重複，不能先把兩份都當常駐。
  先問「誰是 owner、這件事是否每個 session 都需要」。
  本 repo 已明定 project 規格優先，但優先權只解決衝突，不代表同義內容會自動去重（[`CLAUDE.md:35-38`](../../CLAUDE.md#L35)；[`skills/maintain-guideline/SKILL.md:107-111`](../skills/maintain-guideline/SKILL.md#L107)）。
- **不可直接推出**：某 project 有自己的規則檔，不代表它已涵蓋全域 entry 的授權、環境事實、完成證據或 fallback。
  這份報告也沒有掃描其他私有專案的 `CLAUDE.md`／`AGENTS.md`，所以不宣稱跨 project 重複率。
- **責任分類（提案）**：逐項把候選標成 `delete candidate`、`project-owned`、`on-demand skill`、`agent contract` 或 `global minimum`。
  只有比對資訊量、觸發條件、責任 owner 與 fallback 後，才可把疑似重複列為刪除候選。
  「看起來已有一份」不能取代這個安全閘門。
- **Project-owned（本 repo 的具體候選）**：commit／PR naming conventions、code style、testing commands/framework、business specs 與 project playbooks 由 project owner 定義。
  `rules/20-judgment.md:65-69` 的 commit message convention 已是本報告列出的下沉候選；若它只服務某 project，應由 project 的 PR／create-PR 入口承接。
  不把本 repo 的候選誤寫成「已量到所有 project 都重複」。
- **On-demand skill（本 repo 的具體候選）**：通用 bug、refactor、planning、review、dispatch procedure 按意圖與 task trigger 發現。
  `parallel-dispatch` 已把 orchestration 放在非一般 session 的 skill 層；不因它有完整流程就把它整包搬進 global 常駐。
- **Agent contract（本 repo 的具體候選）**：agents 保留角色、工具、必要權限、single-writer／scope 邊界與輸出 contract。
  角色 interface 不等於把每個工作流程全文灌給每個 agent；需要的 procedure 仍由 brief 或 skill discovery 提供。
- **Global minimum（本 repo 的具體候選）**：授權、安全、真實環境入口、project precedence、最低完成／證據邊界與必要 fallback 留在最短 global。
  `rules/20` 的完成、證據與高風險判定保留；完整 mutation／判斷細節不必每個 session 常駐。
- **不要自動灌 fallback（提案）**：若 project 沒有明定某項，且使用者也沒有明確選用 skill，不應因此自動注入整套 global fallback。
  只補足必要的最低授權／安全／環境入口，或把缺口標成待決策。
  這是責任分類提案，不是已量得的跨 project 覆蓋率。
- **pstack 來源事實（固定 pin）**：本輪查讀 `v0.9.93`／`046341e3aaf2405083973a37f860d0d2ea98e18a`。
  root README 說 `poteto-mode` 依目標選 workflow；Claude、Codex、Copilot 安裝有 routing hook，而 skills-only 安裝沒有 hook，需點名 `poteto-mode` 或加 standing instruction（[README.md:5-7](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/README.md#L5-L7)、[README.md:52-70](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/README.md#L52-L70)）。
  這不是「完全不用 global entry」的證據。
- **pstack 的實際組成**：plugin README 將內容拆成 Markdown skills、agents、SessionStart routing hook 與 local scripts（[plugins/pstack/README.md:7-13](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/README.md#L7-L13)）。
  這支持「workflow 可按需 skill 化」，不支持「所有 global context 都可刪除」。
- **pstack 的 hook routing**：Claude/Codex hook JSON 都在 SessionStart 呼叫 runtime-specific `session-start.sh`（[hooks.json:1-15](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/hooks/hooks.json#L1-L15)、[codex-hooks.json:1-16](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/hooks/codex-hooks.json#L1-L16)）。
  `session-start.sh` 依 runtime 讀 sheet、允許關閉 hook，否則輸出 routing context（[session-start.sh:4-47](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/hooks/session-start.sh#L4-L47)）。
- **pstack 的觸發邊界**：hook context 要求符合條件時叫 `poteto-mode`，小修才直接做（[session-start-context.md:1-15](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/hooks/session-start-context.md#L1-L15)）。
  這是 global routing mandate 加 on-demand workflow 的組合，不是 zero-context 的 skills-only 模式。
- **可借的架構（判斷）**：可借「hook／小 router → 依意圖展開 skill → playbook／子流程與 roles」。
  `poteto-mode` 以 task trigger、playbook、project playbook 與 role defaults 把流程按需組合（[poteto-mode/SKILL.md:20-41](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/skills/poteto-mode/SKILL.md#L20-L41)、[poteto-mode/SKILL.md:128-169](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/skills/poteto-mode/SKILL.md#L128-L169)）。
  代表 workflow `figure-it-out` 也把工作拆成 framing、workflow design、verifiable loop、audit trail、real-artifact verification（[figure-it-out/SKILL.md:14-50](https://github.com/michael-denyer/pstack-claude/blob/046341e3aaf2405083973a37f860d0d2ea98e18a/plugins/pstack/skills/figure-it-out/SKILL.md#L14-L50)）。
- **與本 repo 已有能力比較（判斷）**：本 repo 已有 shared judgment、project precedence、platform adapters、isolation ownership 與驗收停止。
  `parallel-dispatch` 明確分離 task／agent／execution environment／optional worktree，並保留 ownership、integration 與 fresh validation；這些是應重用的結構，不需照 pstack 重新建立。
  技能化只能移動 workflow，不應取代本 repo 的 stop condition、single-writer 或 scope contract。
- **代價與不可照搬（判斷）**：hook／小 router 仍可能預載 skill catalog／routing mandate，並付 skill 展開、playbook、fan-out、agent role 與模型設定成本。
  不可把 pstack 的 workflow side effects、subagent defaults、autonomy／shipping 行為直接移植到本 repo。
  來源沒有提供本機 token、Max quota 或「移出 global 後一定省多少」的 ablation。

| 本機 seam | 目標層 | 必要 trigger／discovery／fallback |
|---|---|---|
| `CLAUDE.md:14-25,35-38` | global minimum／入口路由 | 每 session 只留 authority、優先權與可發現索引；依 task 讀 rule／skill；未選 skill 不自動全載 global。 |
| `rules/20-judgment.md:7-12,23-34,57-73` | global minimum + on-demand docs/rubric | completion、行為性文件或高風險變更觸發；細節由 docs／rubric 發現；缺 runtime evidence 就標未驗證並走 fresh verifier。 |
| `rules-controller/10-dispatch.md:39-48,63-75` | controller owner／agent contract | 要派工或 scope／ownership 不明時觸發；由 approved plan 發現 worker／skill；無法界定時走 Explore／Plan，不靜默複製全域內容。 |
| `skills/parallel-dispatch/SKILL.md:7-9,27-35,72-97` | on-demand skill | ≥2 coding agents、race 或需整合才觸發；description 是 discovery；不值得拆時 fallback 為單一 worker／一般 dispatch。 |
| `skills/maintain-guideline/SKILL.md:56,107-111` | global public／project ownership guard | 往公開 repo 或 project 規格寫入時觸發；由 skill discovery；受保護的 project rules 沒有明確授權仍停下，不以 generic fallback 代改。 |

- **最脆弱證據（未驗證）**：本輪尚未量測跨 project 的實際覆蓋率、同一任務的 global/project/skill 消融、routing／fan-out runtime 成本或品質差異。
  mapping 是可供下一輪執行者採用的設計建議，不是省 token、Max quota 或通用重複率結論。
  新增段落只補本輪研究，未改變初次 verifier 對原報告 12 findings 的證據。

## 可日落的舊模型補丁，與不可日落的邊界

可提出日落實驗的是：通用工作教學、已由 settings 承接的語言偏好、角色／模板中逐字重複的完整 approved-plan 欄位、以及「零命中即不能語意判斷」這類可能以文字匹配取代結構比對的流程規定。它們必須先以 matched task 證明新模型／新 runtime 仍會做對，並保有 rollback。

不可用「新模型應該懂」推翻的是：使用者授權與不可逆行為、實際 host/OS/CLI/sandbox/install 事實、模型看不到的 secrets/外部狀態、artifact/read-back/negative-test 證據、以及跨平台 permission/runtime 差異。這些是資訊不可得或責任分配，不是推理能力問題。

現有 maintenance protocol 已正確把 byte tripwire 定義為審查觸發而非最佳化目標，也要求資訊量／語意方向比對；後續 patch 不能為壓 bytes 而把安全邊界縮成引用。[`skills/maintain-guideline/SKILL.md:74-98`](../skills/maintain-guideline/SKILL.md#L74)

## 後續派工包（尚未授權修改）

### Wave 0 — 先做 ownership 分類，再重用既有 usage-review 固定基準

- **順序**：先把候選條目標成 `global minimum`、`project-owned`、`on-demand skill`、`agent contract` 或 `delete candidate`，逐項確認 project entry 的語義是否真的完整；project 檔存在本身不算覆蓋證據。之後才重用 usage-review 固定基準與決定量測 cohort。

- **所有權**：重用既有 `skills/usage-review` 的匿名 summary，不新建常駐 collector／儀表板，也不動 rules。
- **輸入**：本報告的 extraction window；必要時記錄 Usage Settings weekly percentage/timestamp；依 task class 做最少 outcome 標籤。
- **完成條件**：可重跑、無 slug/title/raw transcript、每個指標說清楚分母；公布 before/after 不是 API-equivalent→weekly 的換算。

### Wave 1 — 兩個可回退試驗

- **語言**：隔離 Claude config / fresh sessions，做 FIND-01 的代表性低成本抽樣；不變量是繁中台灣用語與 code/專有名詞正確性。
- **Codex named prompt**：隔離工作樹／相同 task，測 FIND-07 三組；不變量是 role/runtime evidence、approved-plan、write scope、驗證與回報完整。
- **停止**：任何 one-way action、品質下降或 runtime 未證實，立即回復目前內容並只交付實驗結果。

### Wave 2 — Claude dispatch cohort

- **所有權**：只在使用者核准後改 controller／role 相關檔；single writer，先做一項候選。
- **不變量**：高風險／跨時序路徑仍走現行 Plan/second-opinion；文件／驗收仍 fresh-context；不擴大權限。
- **驗收**：相同 task class 的 first-pass、OPEN/INCONCLUSIVE、修正輪數、worker/main context、request、cache component；新規則的路徑／引用檢查與 fresh verifier。

### Wave 3 — 採納／回退／日落

- 預先訂出保留或回退門檻後才改 default；只在 quality 非劣、效益跨多個 window 穩定時採納。
- 每次只改一個可歸因變因；將 retired rationale 封存到按需 docs，不留同義副本。
- 任何判準內容的修改／刪除、agent responsibility 或全域入口變動，都需使用者再授權與 fresh-context verifier，遵循現有 maintenance ownership。 [`skills/maintain-guideline/SKILL.md:13-30`](../skills/maintain-guideline/SKILL.md#L13)

## 最大未解風險與查證邊界

1. 近 7 日 telemetry 是事後關聯，未標示每一個 verifier finding 是否必要；它不足以裁定某角色「多餘」。
2. 沒有做 Claude Max weekly 的受控因果實驗，且官方未公開 bytes/token/weekly 函數；任何「能多用幾天」的說法都應拒絕。
3. Claude `language` schema 的語言覆蓋是文件／設定層證據，未在代表性台灣用語抽樣實跑；它不能單獨保證術語選擇。
4. Codex docs 描述一般載入機制，但本機 named role 最小 prompt、adapter 需要的最小資料、`fork_turns` fresh 行為尚未 runtime 測試。
5. 本輪未重新量測 9 plugins 的個別成本；既有 3.8K 整體差與互動額外 context 不能用於刪 plugin 決策。
6. 所有檔案分類是設計審查，不是修改完成或現場品質證明。
7. FIND-13 的跨 project 覆蓋、routing／fan-out cost、消融與品質比較尚未實跑；pstack 只作固定 pin 的來源比較，不是本機 runtime 或 Max quota 證據。

## 驗證記錄

- `git rev-parse HEAD` → `51b04f29cbdf0d918a72d1081d8a2ffa4c7adf17`。
- `wc -lc` 對本報告列出的入口／rules／roles／Codex dispatch／parallel files：數值見「已量測的載入集合」。
- `ls -l ~/.claude/{CLAUDE.md,rules,rules-controller,host-facts.md} ~/.codex/AGENTS.md`：本機 Claude/Codex 入口與 host facts 都指向此 repo；設定僅由本機程式解析後白名單讀回指定 keys，未輸出其他欄位。
- 官方網頁查證：Claude docs/settings/schema/help center 與 OpenAI docs，連結列於「官方查證」。
- 2026-10-19 fresh-context `verifier` 獨立核對 8 項條件：7 項 PASS，1 項 Codex Hooks 能力宣稱列 `PROSE-ONLY`；依官方來源修正後由 controller read-back 結案。此為研究／數值／引用審查，不代表提案的 runtime、節省或 weekly 影響已實測；本輪只新增報告。
- 2026-10-19 FIND-13 補充另經 fresh-context `verifier` 審查：6／6 PASS、`CONVERGED`；核對固定版本 pstack 來源、責任分類、原報告保留範圍與提案邊界。未執行 pstack scripts，未量測跨專案覆蓋率、token／Max 配額收益或品質消融。
