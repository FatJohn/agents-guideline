# worker 換 Sonnet 5.5/xhigh 試用：前後期對照與量測紀錄（2026-09）

## 目的

2026-09-29 使用者決定把 Claude 端標準執行者 `worker` 從 Opus 5.5/medium **直接切換**為 Sonnet 5.5/xhigh（`claude-sonnet-5-5`，試用），不是 A/B 交替；Opus 5.5/medium 改為備用車道 `worker-opus`。本檔只做兩件事：留下切換前（窗口 A）的量化基線，以及訂出試用期怎麼量、何時回退。路由本身的規則在 `../rules/10-dispatch.md` §0 與 `../agents/worker.md`，本檔不重複。2026-09-29 規則改良（worker 突變自證、CI 設定排除小修例外、平行 fan-out 與切片相對尺寸、CI 等待做法）與 worker 切換同日生效，窗口 B 的量測起點以該批規則 commit 時間為準：`958804a`（2026-09-29 10:39:17 +0800）。

- 決策日：2026-09-29。
- 窗口 A（基線）＝Opus 5.5/medium：2026-09-24 11:49～09-29 09:39，約 4.9 天。主報告各節（1–7）資料截至 09:36，advisor 補充段截至 09:39。
- 窗口 B（試用）＝Sonnet 5.5/xhigh：2026-09-29 09:41 起（worker 換型時間）；量測起點以規則 commit 為準，見「目的」段末句。
- runtime 證據：09-29 09:41 worker smoke test 的 subagent transcript，assistant `message.model` 為 `claude-sonnet-5-5`。另 controller 同日 `claude -p --model sonnet` 實測 `modelUsage` 為 `claude-sonnet-5-5`。
- 前次 A/B 對照文件（Sonnet/xhigh vs Opus 5.5/medium）已刪，歷史在 `git show 3ad8d8a:docs/worker-ab-2026-09.md`；本檔的「更早基線」欄引用的 09-21、09-25 數字存在主力 Mac 的 auto-memory，不在 repo 內。
- 成本背景與量測方法的上游文件：`dispatch-cost-review-2026-09-17.md`。

## 窗口 A 基線（Opus 5.5/medium）

資料：`~/.claude/projects/*/` 主對話 35 個 session、subagent 447 個（窗口內啟動 436 個，與主對話 Agent tool_use 436 次逐筆相符）。成本口徑：requestId 去重；API 牌價等價依 model 分別計，cache_write=2×in（沿用前次 1h TTL）；相對價 in 1／cw 1.25／cr 0.1／out 5。Opus 5.5 每 request output 補估 +680（jsonl 只記串流開頭），已含於所有 $ 與相對價（補估合計約 $220，占總額 14%）。

**窗口內沒有 Sonnet 5.5 worker 資料，本節只當 Opus 5.5 medium 基線。**

**全窗口混淆**：主對話同樣在 09-23 22:31 起改為 `claude-opus-5-5`，與 worker 換型同期，無法拆開；任務內容也與更早基線期不同。窗口 B 同理：任務內容會變，`sonnet` alias 自 09-29 09:36 起解析為 `claude-sonnet-5-5`（窗口 A 內的 sonnet 車道是 `claude-sonnet-5`，最近一次 09-29 00:52），所以 Explore／general-purpose 的 sonnet 車道也同時換型。

### 1. worker（agentType `worker`）

| 群組 | n | 工具 中位／P75 | 牆鐘(分) 中位／P75 | 每 req 秒 | 每個 API 等價 $ 中位／總和 | 續用 |
|---|---|---|---|---|---|---|
| 全體 | 182 | 28／51.8 | 10.5／22.8 | 31.2 | 1.84／526 | 49/182（27%） |
| 未續用 | 133 | 25／47 | 8.8／16.3 | 23.2 | 1.50／340 | — |
| 續用（收到 SendMessage 或有第二個非空 user turn） | 49 | 39／66 | 20.0／34.4 | 46.1 | 2.63／186（占 Opus worker 成本 35%） | 49/49 |
| **project-a（主比較）** | 78 | **36.5**／63.5 | **13.5**／26.9 | 26.5 | **2.30**／287 | 10/78（13%） |
| project-a 未續用／續用 | 68／10 | 34.5／55.5 | 13.3／24.5 | 25.7／30.9 | 2.26／4.48 | — |
| flutter-app-template | 59 | 27／43.5 | 11.9／22.0 | 44.4 | 1.75／153 | 26/59 |
| flutter-slimgo | 11 | 52／81.5 | 23.2／32.2 | 25.9 | 3.37／37 | 6/11 |

- project-a 依 prompt 含「finding／修正／delta／第 N 輪」分：fresh n=36 工具 58／23.2 分／$4.27；fix n=42 工具 27.5／10.1 分／$1.74（首次實作約為修正的 2.4 倍成本）。
- 對照更早基線（project-a Opus 09-25，n=84）：工具 37.5→36.5、牆鐘 13.6→13.5 分、$2.4→2.30、每 req 秒 25.3→26.5，與初期幾乎不變。窗口 A 內分段：09-26 中午前 n=56：36.5 次／13.4 分／$2.30；之後 n=22：47 次／17.0 分／$3.27（後半任務較重：#17 P5、#58 Refit）。
- 對照 09-21 Sonnet 5 全體（90 次／16.1 分）：Opus 全體 28 次／10.5 分。任務混合不同，只當上下界。
- 同專案 Sonnet 對照（n 很小，僅參考、不可當結論）：web-member-login 09-24 12:04–15:49 有 7 個 `worker` 被顯式帶 `model: sonnet`（`claude-sonnet-5`）：工具 55／6.7 分／10.4 秒每 req／$1.26；同專案 Opus n=6：21.5／4.9 分／16.1 秒／$1.42。
- 其他 lane（窗口 A）：`worker-sonnet` agentType 0 個；general-purpose/opus n=12（31 次／8.6 分／$2.57）、/sonnet n=17（33／7.2／$1.35）、/fable n=1（60 次／17.5 分／$8.98）；Explore/sonnet n=34（45／5.9／$0.92）；Plan/opus n=10（40／10.3／$2.56）；codex-rescue n=4（約 $1）。

### 2. verifier（n=168：167 Opus 5.5、1 Fable）

| 項目 | 窗口 A | 對照更早基線 |
|---|---|---|
| 首輪（prompt 無 delta 訊號）n=124 | OPEN 65（**52%**）、CONVERGED 38、PROSE-ONLY 19、INCONCLUSIVE 2（另 3 個沒回報，排除） | 首輪 OPEN 67%（09-21）／62–64%（09-25） |
| delta 輪 n=41 | CONVERGED 28、PROSE-ONLY 6、OPEN 7（**17%**） | delta OPEN 23.5%／25% |
| 時間分段 | 09-24~26 首輪 37/73=51%、delta 6/28=21%；09-27 起首輪 28/51=55%、delta 1/13=8% | — |
| 驗收鏈（啟發式掛接，可能掛錯）n=126 | 1 輪 92、2 輪 29、3 輪 4、4 輪 1；一輪定案 52/126＝41%；鏈終態 CONVERGED 60、PROSE-ONLY 24、OPEN 42（首輪 OPEN 後沒有 delta，屬機械結案或未追蹤）；首輪 OPEN／INCONCLUSIVE 的 68 條中有 delta 收斂者 27 條 | 報告未給 |
| 成本／時間 | $310（占窗口 API 等價 20%）；單一 verifier 工具中位 25 次、牆鐘中位 8.3 分 | 報告未給 |

- ≥3 輪的鏈 5 條：`5db74ff6-6275-4094-b5d1-ea25334fc622`（3 條）、`1738276b-6dc2-4b12-b848-af6399158ba3`（疑似掛錯）、`1a30eb86-0517-42db-af75-d6a883d9ea45`。
- 混淆：delta 以 regex 判，未標示者會漏判為首輪；worker 品質提升與 verifier 同為 Opus 5.5 都可能造成 OPEN 率下降，無法拆。窗口 B 的 verifier 仍是 `model: opus` alias（2026-09-29 `../agents/verifier.md` 未改；alias 現解析為 `claude-opus-5-5`，見 `harness-facts.md`），所以窗口 B 首輪 OPEN 率變化較能歸因到 worker 換型（推論），但任務內容不同的混淆仍在。另有兩項混淆：窗口 B 的 Explore／general-purpose sonnet 車道同時換型（見「窗口 A 基線」節開頭的「全窗口混淆」），且 2026-09-29 同日規則改良（worker 突變自證、CI 設定排除小修例外、平行 fan-out 與切片尺寸檢查）也會影響首輪 OPEN。

### 3. parallel-dispatch

波次定義：同 session 的 worker 忙碌段（req 間隔>5 分視為閒置）串起，相鄰 ≤15 分歸同波。

| 項目 | 窗口 A | 對照更早基線 |
|---|---|---|
| session／波次 | ≥1 worker 的 session 20 個、≥2 worker 的 session 17 個；波次 n=45 | — |
| 真並行比例 | ≥2 片 session 中曾有真並行（最大重疊≥2）16/17（94%）；波次層級 29/45（64%）並行、16/45 序列 | 報告未給 |
| 並行度 | 全體平均 1.93、並行波次 2.45、最大 5（09-29 00:50 跨三 repo 共 8 片）；分布 1:16、2:19、3:8、4:1、5:1 | 09-21 並行度 2 |
| 並行波次(n=29) vs 序列波次(n=16) | 平均切片 3.7 vs 2.7；牆鐘中位 98 vs 97 分（P75 130 vs 135）；worker 忙碌總和中位 40 vs 39 分；牆鐘／忙碌總和中位 1.77 vs 2.67；每片 verifier 1.06 vs 1.16 | 報告未給 |
| 隔離 | Agent 帶 `isolation: worktree` 的波次 11/45；prompt 提到 worktree 35/45（多數平行波次是 controller 自建 worktree） | — |
| 整合時間代理值 | 中位 121 分（並行 n=27）／91 分（序列 n=16），量不準（含等 CI 與跨波重疊） | — |

- 並行波次牆鐘中位沒有比序列短，是同樣牆鐘內多做約一片；牆鐘由驗收、整合、使用者往返主導。
- 混淆：以時間近似切波，會把「實作＋修正」序列 worker 當同一波。

### 4. 主對話（n=4,127 requests、34 session，全為 Opus 5.5）

| 項目 | 窗口 A | 對照更早基線 |
|---|---|---|
| cache_read 占比 | 相對價 71%；API 等價 51%（cache_write 24%、output 25%） | 相對價基線 69% |
| context 大小 | 中位 308K、P75 440K、P90 561K | 中位基線 274K |
| 按 model | 全為 `claude-opus-5-5`，API 等價 $533（占總額 35%） | — |
| 讀檔類 Bash | Bash 共 2,530 次；讀檔類（排除 heredoc 寫檔）670 次＝26%；git／gh 34%；Read 工具 77 次 | 基線 5.4%（口徑可能不同） |

- 限制：本節主對話成本不含 advisor（advisor 用量大多不在 jsonl 的一般 usage 內；能量到的下限見第 6 節）。

### 5. 牆鐘分解（≥3 subagent 的 session，n=20，總 175.9 小時）

| 類別 | 含離席 | 排除離席 |
|---|---|---|
| 等 subagent | 38% | 64% |
| 主對話自己工具 | 3% | 6% |
| 主對話模型生成 | 4% | 7% |
| AskUserQuestion | 3% | 5% |
| 閒置（≤30 分） | 11% | 18% |
| 離席 >30 分 | 40% | — |

- 對照 09-21 等 subagent 47%：口徑不同，只能說等 subagent 仍是最大宗、主對話自己工具極小。

### 6. 成本（API 牌價等價，含 Opus 5.5 補估；對照更早基線：報告未給）

| 日期 | 總計 | 主對話 | worker | verifier | 其他 sub |
|---|---|---|---|---|---|
| 09-24（自 11:49） | 276 | 84 | 109 | 71 | 12 |
| 09-25 | 310 | 101 | 114 | 57 | 38 |
| 09-26 | 366 | 129 | 99 | 68 | 69 |
| 09-27 | 337 | 119 | 129 | 65 | 23 |
| 09-28 | 212 | 83 | 84 | 38 | 7 |
| 09-29（至 09:36） | 40 | 18 | 11 | 10 | 1 |
| 合計 | 1,540 | 533 | 541 | 310 | 156 |

- 按 model 合計：opus-5-5 $1,445、sonnet $84、fable $11。
- 09-24 11:49～09-28 19:00（103 小時）$1,437（約 $334／天）；09-28 19:00 重置後至 09-29 09:36 累計 $103。
- 角色占比：主對話 35%、worker 35%、verifier 20%、其他 10%。
- advisor（補充段，窗口 09-24 11:49～09-29 09:39）：呼叫合計 205 次（主對話 27 次〔2 次 overloaded〕；subagent 178 次：worker 84、verifier 69、general-purpose/opus 13、Explore 8、general-purpose/sonnet 3、Plan 2），型號皆 `claude-fable-5-1`。usage 只有部分記在 `usage.iterations[]` 的 `advisor_message`：主對話 25 次 input 4,422,953／output 176,226，Fable 牌價約 $53.0；subagent 只有 5 次有記，約 $9.0（下限），另 173 次量不到。**可算下限合計約 $62，約占窗口 API 等價 $1,540 的 4%；上表各節成本不含 advisor。** subagent advisor 若與主對話同量級每次約 $2，可能再加 $300 以上——無記錄依據，不當數字引用。advisor input 無 cache_read，按全額 input 計價，實際帳單口徑未驗證。
- **量不到：週額度實際 %。** 這是判斷 Sonnet 是否較省額度的關鍵量尺，見下方「額度追蹤」。

### 7. alias 解析現況（2026-09-29）

- `claude-sonnet-5`：最近一次 09-29 00:52（Explore/sonnet）；`claude-sonnet-5-5`：09-29 09:36 起。
- `claude-fable-5-1`：實際 request n=25（general-purpose 17、verifier 8），09-26 09:36～23:26。jsonl 中另有大量 `advisorModel`／advisor attachment 的 fable-5-1 字串，是設定紀錄非 request。
- `opus` alias 自 09-23 22:31 起皆為 `claude-opus-5-5`。

### 窗口 A 分級

- 已驗證：subagent 總數 436/436 與 Agent tool_use 相符；worker 型號分佈與 meta 相符；requestId 去重；型號只讀 `type:"assistant"` 的 `message.model`。
- 未驗證／有限制：驗收鏈掛接、delta regex 漏判、整合時間代理值、牆鐘估計、advisor 用量、週額度百分比。

## 量法（下次量窗口 B 要照做）

- **去重**：以 requestId 去重，再算 request 數與成本。
- **續用判定**：先剝 `<system-reminder>` 再判是否有第二個非空 user turn 或 SendMessage；不剝會把注入誤判成續用。
- **verifier 輪次**：用 prompt regex（含「finding／修正／delta／第 N 輪」）分首輪與 delta；漏標的會被當首輪，結果只當上下界。
- **fresh vs fix**：同樣用 worker prompt 是否含「finding／修正／delta／第 N 輪」分。
- **output_tokens 補估**：Opus 5.5 的 jsonl 只記串流開頭，窗口 A 每 request 補 +680。**Sonnet 5.5 是否有同樣少記，窗口 B 先核對**：比每 request 可見輸出字元數與 `output_tokens`，兩者比例明顯偏離才套補估；沒核對前 Sonnet 成本標「output 可能低估」，不直接沿用 +680。
- **型號判定**：只看 `type:"assistant"` 的 `message.model`；advisor attachment、`advisorModel` 設定字串不算 request。
- **advisor**：只有 `usage.iterations[]` 的 `advisor_message` 有 usage，subagent 多數沒記，只能報下限。
- **主比較口徑**：用同專案（project-a，或窗口 B 的主專案）worker 的中位數；全體只當上下界。任務較重的分段（如窗口 A 09-26 午後的 #17 P5、#58 Refit）要另分開看。
- **計價**：同窗口 A 口徑（cache_write=2×in、相對價 in 1／cw 1.25／cr 0.1／out 5），Sonnet 5.5 牌價現查再套，不沿用 Opus 價。額度 % 才是實際負擔的量尺，API 牌價只當相對權重。
- **腳本**：`parse.py`、`common.py`（價格、`OUTFIX=680`）、`an_worker.py`、`an_ver.py`＋`an_chain.py`、`an_wave.py`＋`an_agg.py`、`an_main.py`、`an_time.py`、`an_cost.py`、`an_advisor.py`、`an_slice.py`（從零切片牆鐘＝worker 牆鐘＋首輪 verifier 牆鐘；從零＝prompt 前 1500 字不含 finding／修正／delta／第 N 輪／OPEN／FAIL；掛接＝同 session、verifier 起點在 worker 起點到結束後 90 分內、路徑／PR 號／description 相似度最高，一對一貪婪配對）。腳本在 session scratchpad 暫存區，可能消失；消失時依本節口徑重寫，不必找原檔。

## 額度追蹤

週額度每週一 19:00（台北時間）重置。API 牌價等價只當相對權重（窗口 A 只有 $ 等價，沒有額度 %）；**Settings > Usage 的週 % 是判斷 Sonnet 5.5 是否較省額度的唯一量尺**。由使用者定期提供，不從 jsonl 推估。

| 日期時間 | Settings > Usage 週 % | 距上次重置時數 | 備註 |
|---|---|---|---|
| 2026-09-29 10:47 | 9% | 約 15.8h | 試用起點（上次重置 09-28 19:00；這段主要是 Opus 5.5 worker＋本次 review 的 Fable 5.1） |

## 評估門檻（事先訂定，2026-09-29 使用者採用 Fable 建議）

速度與品質兩者都是衡量標準（2026-09-23 使用者確認）。累積 n≥30 個窗口 B 首輪 verifier 後判定；任一條成立就回報使用者決定是否回退，不自動回退：

- 首輪 verifier OPEN 率 >62%（窗口 A 52%）。
- delta OPEN 率 >25%（窗口 A 17%）。
- project-a（或當期主專案）worker 工具數中位 >55（窗口 A project-a 36.5）。
- 每片牆鐘（worker＋首輪驗收）比窗口 A 多 30%。窗口 A：從零切片的 worker 牆鐘＋啟發式掛接的首輪 verifier 牆鐘，project-a n=27 中位 34.1 分（P75 48.8），全體 n=75 中位 26.9 分（P75 38.6）；兩段直接相加、不含中間主對話時間，屬下限；掛接失敗排除 27 個（project-a 9），未人工抽查（未驗證）。窗口 B 用同一定義量（腳本 `an_slice.py`）。
- 主對話直接 Edit/Write 程式／設定檔的速率達窗口 A 基線（12 次／4.9 天）的 2 倍。

週額度 % 只記錄不設門檻（見「額度追蹤」）。使用者決定回退時走「回退方式」；轉為正式預設同樣要使用者明確同意。

## 回退方式

- **臨時單次改派**：派 `worker-opus`（不帶 `model`，model 與 effort 由其 frontmatter 決定）。適用於某個任務明顯需要較強推理，不必動制度檔。
- **整體回退**：要改 `../agents/worker.md` frontmatter 與 `../rules/10-dispatch.md` §0。這屬於修改既有判準，**要使用者明確同意**才能動手，worker 與 controller 都不得自行決定。

## 質性 review（Fable 5.1）

> 2026-09-29 由 general-purpose（`model: fable`，Fable 5.1）依窗口 A 資料做的質性 review，本節為精簡版。方法：取 verifier 回報全文並抽樣 26 個首輪 OPEN（7 專案分層）；波次以主對話工具呼叫與 subagent 起訖重建 4 條時間線。數字口徑同上方各節，但分母 /189 與 /126 等沿用原 review，與第 1 節 worker n=182 不同，原文未說明差異。標記「已驗證／推論」沿用原 review；id 格式為 `session:agent`，每類只列代表。

**首輪 OPEN 52% 的原因結構**（26 抽樣已驗證；全 65 個的 regex 計數為推論）
- A1 交付價值沒被測試守住（worker 可避免）：新斷言拿掉或換成固定值仍全綠；26 中 8 個（例 `43debcfb:ab472be1`、`a554a3c4:a5bdc31e`）；全 65 提到突變／假綠／存活者 42（推論）。
- A2 對抗性形狀或守門檢查器本身有洞（verifier 該抓、worker 難預見）：26 中 6 個（例 `59c3d18f:a8851eb3`）；屬 `parallel-dispatch` SKILL.md §5 首輪探針設計的結果，原 review 認為不該改。
- B 可證偽宣稱失準（worker 可避免；`20-judgment.md` §2 已有判準但 worker 沒實跑）：26 中 7 個（例 `0b7b1923:aa705754`、`5db74ff6:a3272adb`）；全 65 含「不成立／寫錯／漏列」27（推論）。
- C 真 bug 3 個（例 `a554a3c4:ac888b7f`）；D brief／controller 造成 3 個（例 `43debcfb:ad482dcc` 驗收條件互相衝突），D 作為模式屬推論。C、D 原文只寫「3 個」，未標是否出自 26 抽樣。
- E verifier 嚴格度：全 65 中 21 個自述「低嚴重／可機械結案」（regex 推論）；OPEN 定義使約 1/3 首輪 OPEN 只有一個低風險項。原 review 不建議改定義，但試用期分開計。
- Sonnet 5.5 最可能惡化 A1 與 B（推論）：兩者都是「多做一步自證」的紀律；A2／E 與 worker 模型無關（verifier 仍是 Opus）。

**平行開發牆鐘花在哪**（4 條時間線已驗證）
- 前提：波次牆鐘把 worker 之後 +90 分內的 verifier、+120 分內的 merge 都算進去，所以第 3 節的「牆鐘中位 98 vs 97 分」是啟發式，不是純 worker 工時（例 `43debcfb` L4 波 98 分實為 worker 5 分＋PR/CI/merge 20 分，其餘是下一波驗收）。
- (1) OPEN→修→delta 迴圈：首輪 OPEN 到最後一輪驗收結束中位 +17 分（P75 22，n=26 鏈）；`1738276b` 16:04 三片並行 3/3 首輪 OPEN，全部續用同 worker 再 delta，76 分波次中約 25–30 分在此。worker 合約只要求跑 plan 的 validation，沒被要求自證紅→綠。
- (2) 依賴階段序列化＋逐 PR 等 CI：`43debcfb` L6 四個階段，每階段 PR 各等 CI 3–6 分；主對話 139 個 sleep／pr checks 迴圈（104 已背景化，但每次讀輸出仍是一次 308K 重讀）。對應 SKILL.md §3「Foundation 先落地」與 §6 逐片 integration gate；實務上從 foundation SHA 開 integration branch 就 fan-out。
- (3) 切片不均：並行波次內最長片／中位片 1.71×（P75 2.27×）；例 `59c3d18f` 04:57 波 T8-A 64 分 169 工具，另有 9 分的片。SKILL.md §3「單片尺寸評估」沒有同批相對尺寸檢查。
- (4) 等使用者：`1738276b` 兩段離席共 43 分。另觀察小片成本幾乎全是 PR/CI 流程（`43debcfb` L4 三片 5 分完工、20 分全 merge）。

**主對話成本來源**（587 筆分類＋40 抽樣已驗證；第 4 節計讀檔類 670 次，與 587 的差異原文未說明）
- 讀檔類 Bash 26% 中，≥3 檔多檔閱讀只有 89/587（15%），規則針對的行為大致遵守；大宗是規則沒涵蓋的型態：讀背景任務輸出（CI／測試輪詢）127（22%）、讀暫存區內自己寫的 plan／worker log 122（21%）、1–2 檔定點 read-back 131（22%，規則允許）、重讀 rules/skills 60（10%）。
- 主對話 2,530 Bash 中 gh pr checks/run 290、pr create 145、pr merge 139、worktree add/remove 169、git commit 200，全在 308K context 跑；worker 合約禁 push/PR/merge，這塊結構上落在主對話。

**死重與缺口**
- 教訓重演（已驗證）：`50-lessons.md` 2026-09-23 CI workflow 條仍是「尚未」，`1fd0fa6d` 09-25 12:09 controller 直接 Write PureFlac `.github/workflows/release.yml`、commit、PR，12:13 merge，無 worker 無 verifier。
- 缺口：worker 自證（A1）——`worker.md` 規則 2／10 與 `parallel-dispatch/references/templates.md` Validation 欄都沒要求新斷言／守門附會變紅的突變；另使用者核准的提案文字仍要實查（n=1，`137115b9:ad72f56a`）。
- 死重（0 觸發）：`10-dispatch.md` §5 fable 升檔訊號 (a)(b)(c)（窗口內 fable 兩次皆使用者直接指定）；`20-judgment.md` §4「把 rubric 路徑給 verifier」只 74/168 照做，而 `verifier.md` 規則 3 本來就自選；`50-lessons.md` filter-branch 條視為 0 觸發。
- 文字漂移：`worker.md` 規則 5 把 commit 權綁在 `isolation: worktree` 字面，實際 93/121 有 commit 的 worker 在 controller 自建 worktree（isolation 未設）——行為對、文字不對。
- 小修例外被拉寬（watch）：主對話直接 Edit/Write 程式／設定檔 12 次＋200 次 git commit；`1738276b` 17:07 在 worker worktree 內改 dart 與測試。
- 有作用：git -C／gh -R 綁定幾乎全面採用；worker 回報分級 182/189；scope 外回報 13/189；`parallel-dispatch` SKILL.md 在 12/16 並行 session 被讀。

**試用期要盯的訊號**
- 首輪 OPEN 拆兩層：「OPEN 且 verifier 未自述低嚴重」與「FAIL 屬 A1/B 類」占比；基線 52%（含約 1/3 低嚴重）。
- 續用修正迴圈：帶 finding 的 SendMessage 39/189、首輪 OPEN→收斂 +17 分、≥3 輪鏈 5/126、delta OPEN 17%。
- worker 工具數尾巴（P75／P90）、plan 不完整退回（基線 2/189）、scope 外回報率（13/189）、worker 回報規則 10（宣稱→證據）是否還在寫；controller 代修：主對話對程式檔 Edit/Write（基線 12／4.9 天）與 git commit 數。
- 回退門檻（n≥30 首輪 verifier 後判）已於 2026-09-29 由使用者採用，正式版見「評估門檻」一節；Fable 原建議另有「成本改看每片 $ 不高於 Opus 的 2.30」一項，未採入。

**建議優先序 Top 5**（提案；2026-09-29 經使用者逐項同意（maintain-guideline §5）後，已改 1、2、3、4 的 CI 等待段、5 的 verifier 路徑與 worker 規則 5；未改 4 的 integrator worker 評估與 5 的刪 fable 訊號 (a)(b)(c)）
1. `worker.md` 規則 2＋`templates.md` Validation 欄加「每個新斷言／守門附一個實跑會紅的突變並列在回報」——打 A1（8/26），原 review 預期首輪 OPEN 降 10–15 點、每片省約 17 分迴圈（預期值為推估）｜證據強。
2. `10-dispatch.md`「Controller 工作迴圈」小修例外明列排除 `.github/workflows`／CI 設定，`50-lessons.md` 該條升級封存｜證據強（1 次重演）。
3. SKILL.md §3「Foundation 先落地」改為 foundation SHA（base 或 integration branch）即可 fan-out、不等 CI／merge；「單片尺寸評估」加同批相對尺寸檢查（最長片 >2× 中位就重切）｜證據中。
4. `references/claude-code.md` 加「CI 等待與 PR 流程」段：同批多 PR 一次背景 watch、Monitor 收斂後才讀一次；評估在 session 授權下把 push／PR 交給 integrator worker｜證據中（結構性，效果未量）。
5. 刪 `10-dispatch.md` §5 fable 訊號 (a)(b)(c)、`20-judgment.md` §4「把路徑給 verifier」改指向 `verifier.md` 規則 3、`worker.md` 規則 5 改寫為「plan 明寫隔離 worktree（含 controller 自建）」｜證據強（0 觸發／74/168／93/121）。
