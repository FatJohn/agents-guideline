# worker 換 Sonnet 5.5/xhigh 試用：前後期對照與量測紀錄（2026-09）（2026-10-05 已轉正式）

## 目的

2026-09-29 使用者決定把 Claude 端標準執行者 `worker` 從 Opus 5.5/medium **直接切換**為 Sonnet 5.5/xhigh（`claude-sonnet-5-5`，試用），不是 A/B 交替；Opus 5.5/medium 改為備用車道 `worker-opus`。本檔只做兩件事：留下切換前（窗口 A）的量化基線，以及訂出試用期怎麼量、何時回退。路由本身的規則在 `../rules/10-dispatch.md` §0 與 `../agents/worker.md`，本檔不重複。2026-09-29 規則改良（worker 突變自證、CI 設定排除小修例外、平行 fan-out 與切片相對尺寸、CI 等待做法）與 worker 切換同日生效，窗口 B 的量測起點以該批規則 commit 時間為準：`29be425`（2026-09-29 10:39:17 +0800）。原 SHA `958804a` 於 2026-09-29 11:01 因去除專案名改寫歷史後變為 `29be425`（author date 仍為 10:39:17 +0800；證據：`git log -1 --format='%ai %ci' 29be425` 輸出 `2026-09-29 10:39:17 +0800 2026-09-29 11:01:48 +0800`）。

- 決策日：2026-09-29。
- 窗口 A（基線）＝Opus 5.5/medium：2026-09-24 11:49～09-29 09:39，約 4.9 天。主報告各節（1–7）資料截至 09:36，advisor 補充段截至 09:39。
- 窗口 B（試用）＝Sonnet 5.5/xhigh：2026-09-29 09:41 起（worker 換型時間）；量測起點以規則 commit 為準，見「目的」段末句。
- runtime 證據：09-29 09:41 worker smoke test 的 subagent transcript，assistant `message.model` 為 `claude-sonnet-5-5`。另 controller 同日 `claude -p --model sonnet` 實測 `modelUsage` 為 `claude-sonnet-5-5`。
- 前次 A/B 對照文件（Sonnet/xhigh vs Opus 5.5/medium）已刪，歷史在 `git show 3ad8d8a:docs/worker-ab-2026-09.md`；本檔的「更早基線」欄引用的 09-21、09-25 數字存在主力 Mac 的 auto-memory，不在 repo 內。
- 成本背景與量測方法的上游文件：`dispatch-cost-review-2026-09-17.md`。

## 窗口 A 基線（Opus 5.5/medium）

資料：`~/.claude/projects/*/` 主對話 35 個 session、subagent 447 個（窗口內啟動 436 個，與主對話 Agent tool_use 436 次逐筆相符）。成本口徑：requestId 去重；API 牌價等價依 model 分別計，cache_write=2×in（沿用前次 1h TTL）；相對價 in 1／cw 1.25／cr 0.1／out 5。Opus 5.5 每 request output 補估 +680（jsonl 只記串流開頭），已含於所有 $ 與相對價（補估合計約 $220，占總額 14%）。

**窗口內沒有 Sonnet 5.5 worker 資料，本節只當 Opus 5.5 medium 基線。**

**全窗口混淆**：主對話同樣在 09-23 22:31 起改為 `claude-opus-5-5`，與 worker 換型同期，無法拆開；任務內容也與更早基線期不同。窗口 B 同理：任務內容會變，`sonnet` alias 自 09-29 09:36 起在 CLI 2.1.284 的 session 解析為 `claude-sonnet-5-5`（窗口 A 內的 sonnet 車道是 `claude-sonnet-5`，最近一次 09-29 00:52；2.1.283 的 session 在窗口 B 仍解析為 `claude-sonnet-5`，見「量法」節），所以 Explore／general-purpose 的 sonnet 車道在窗口 B 新舊型號混用。

### 1. worker（agentType `worker`）

| 群組 | n | 工具 中位／P75 | 牆鐘(分) 中位／P75 | 每 req 秒 | 每個 API 等價 $ 中位／總和 | 續用 |
|---|---|---|---|---|---|---|
| 全體 | 182 | 28／51.8 | 10.5／22.8 | 31.2 | 1.84／526 | 49/182（27%） |
| 未續用 | 133 | 25／47 | 8.8／16.3 | 23.2 | 1.50／340 | — |
| 續用（收到 SendMessage 或有第二個非空 user turn） | 49 | 39／66 | 20.0／34.4 | 46.1 | 2.63／186（占 Opus worker 成本 35%） | 49/49 |
| **project-a（主比較）** | 78 | **36.5**／63.5 | **13.5**／26.9 | 26.5 | **2.30**／287 | 10/78（13%） |
| project-a 未續用／續用 | 68／10 | 34.5／55.5 | 13.3／24.5 | 25.7／30.9 | 2.26／4.48 | — |
| project-b | 59 | 27／43.5 | 11.9／22.0 | 44.4 | 1.75／153 | 26/59 |
| project-c | 11 | 52／81.5 | 23.2／32.2 | 25.9 | 3.37／37 | 6/11 |

- project-a 依 prompt 含「finding／修正／delta／第 N 輪」分：fresh n=36 工具 58／23.2 分／$4.27；fix n=42 工具 27.5／10.1 分／$1.74（首次實作約為修正的 2.4 倍成本）。
- 對照更早基線（project-a Opus 09-25，n=84）：工具 37.5→36.5、牆鐘 13.6→13.5 分、$2.4→2.30、每 req 秒 25.3→26.5，與初期幾乎不變。窗口 A 內分段：09-26 中午前 n=56：36.5 次／13.4 分／$2.30；之後 n=22：47 次／17.0 分／$3.27（後半任務較重：#17 P5、#58 Refit）。
- 對照 09-21 Sonnet 5 全體（90 次／16.1 分）：Opus 全體 28 次／10.5 分。任務混合不同，只當上下界。
- 同專案 Sonnet 對照（n 很小，僅參考、不可當結論）：project-d 09-24 12:04–15:49 有 7 個 `worker` 被顯式帶 `model: sonnet`（`claude-sonnet-5`）：工具 55／6.7 分／10.4 秒每 req／$1.26；同專案 Opus n=6：21.5／4.9 分／16.1 秒／$1.42。
- 其他 lane（窗口 A）：`worker-sonnet` agentType 0 個；general-purpose/opus n=12（31 次／8.6 分／$2.57）、/sonnet n=17（33／7.2／$1.35）、/fable n=1（60 次／17.5 分／$8.98）；Explore/sonnet n=34（45／5.9／$0.92）；Plan/opus n=10（40／10.3／$2.56）；codex-rescue n=4（約 $1）。

### 2. verifier（n=168：167 Opus 5.5、1 Fable）

| 項目 | 窗口 A | 對照更早基線 |
|---|---|---|
| 首輪（prompt 無 delta 訊號）n=124 | OPEN 65（**52%**）、CONVERGED 38、PROSE-ONLY 19、INCONCLUSIVE 2（另 3 個沒回報，排除） | 首輪 OPEN 67%（09-21）／62–64%（09-25） |
| delta 輪 n=41 | CONVERGED 28、PROSE-ONLY 6、OPEN 7（**17%**） | delta OPEN 23.5%／25% |
| 時間分段 | 09-24~26 首輪 37/73=51%、delta 6/28=21%；09-27 起首輪 28/51=55%、delta 1/13=8% | — |
| 驗收鏈（啟發式掛接，可能掛錯）n=126 | 1 輪 92、2 輪 29、3 輪 4、4 輪 1；一輪定案 52/126＝41%；鏈終態 CONVERGED 60、PROSE-ONLY 24、OPEN 42（首輪 OPEN 後沒有 delta，屬機械結案或未追蹤）；首輪 OPEN／INCONCLUSIVE 的 68 條中有 delta 收斂者 27 條 | 報告未給 |
| 成本／時間 | $310（占窗口 API 等價 20%）；單一 verifier 工具中位 25 次、牆鐘中位 8.3 分 | 報告未給 |

- 上表「delta 輪 n=41」列附註（2026-10-05 更正：17% 是 regex 口徑（重跑近似 7/42）；B–D 門檻用的手動口徑下窗口 A 為 5/37＝13.5%，再排除非修正輪為 4/36。兩邊從未同口徑比較。）
- ≥3 輪的鏈 5 條：`5db74ff6-6275-4094-b5d1-ea25334fc622`（3 條）、`1738276b-6dc2-4b12-b848-af6399158ba3`（疑似掛錯）、`1a30eb86-0517-42db-af75-d6a883d9ea45`。
- 混淆：delta 以 regex 判，未標示者會漏判為首輪；worker 品質提升與 verifier 同為 Opus 5.5 都可能造成 OPEN 率下降，無法拆。窗口 B 的 verifier 仍是 `model: opus` alias（2026-09-29 `../agents/verifier.md` 未改；alias 現解析為 `claude-opus-5-5`，見 `harness-facts.md`），所以窗口 B 首輪 OPEN 率變化較能歸因到 worker 換型（推論），但任務內容不同的混淆仍在。另有兩項混淆：窗口 B 的 Explore／general-purpose sonnet 車道新舊型號混用（見「窗口 A 基線」節開頭的「全窗口混淆」），且 2026-09-29 同日規則改良（worker 突變自證、CI 設定排除小修例外、平行 fan-out 與切片尺寸檢查）也會影響首輪 OPEN。

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

- `claude-sonnet-5`：最近一次 09-29 00:52（Explore/sonnet）；`claude-sonnet-5-5`：09-29 09:36 起（限 CLI 2.1.284 的 session，見「量法」節）。
- `claude-fable-5-1`：實際 request n=25（general-purpose 17、verifier 8），09-26 09:36～23:26。jsonl 中另有大量 `advisorModel`／advisor attachment 的 fable-5-1 字串，是設定紀錄非 request。
- `opus` alias 自 09-23 22:31 起皆為 `claude-opus-5-5`。

### 窗口 A 分級

- 已驗證：subagent 總數 436/436 與 Agent tool_use 相符；worker 型號分佈與 meta 相符；requestId 去重；型號只讀 `type:"assistant"` 的 `message.model`。
- 未驗證／有限制：驗收鏈掛接、delta regex 漏判、整合時間代理值、牆鐘估計、advisor 用量、週額度百分比。

## 量法（下次量窗口 B 要照做）

- **去重**：以 requestId 去重，再算 request 數與成本。
- **續用判定**：先剝 `<system-reminder>` 再判是否有第二個非空 user turn 或 SendMessage；不剝會把注入誤判成續用。
- **verifier 輪次**：用 prompt regex（含「finding／修正／delta／第 N 輪」）分首輪與 delta；漏標的會被當首輪，結果只當上下界。regex 要同時認中文數字（「第二輪」「第三輪」），窗口 B 曾因此漏判 1 個；手動改判要在報告揭露並與 regex 口徑並列。**窗口 C 起門檻以手動口徑判定**：regex 含「修正／finding」會把首輪 brief（常寫「commit xxx（修正）」）誤判成 delta，窗口 C 腳本的 `common.manual_delta` 可重現窗口 B 的手動值（首輪 10/30、delta 3/9），regex 只當上下界。
- **主對話直接改檔不只 Edit/Write**：還有 Bash（python heredoc、`sed -i`、`cat >`）。門檻口徑只數 Edit/Write；Bash 直接改程式檔另列揭露（下限，不計入門檻）。
- **fresh vs fix**：同樣用 worker prompt 是否含「finding／修正／delta／第 N 輪」分。
- **output_tokens 補估**：Opus 5.5 的 jsonl 只記串流開頭，窗口 A 每 request 補 +680。Sonnet 5.5 不直接沿用 +680，核對結果見下條。
- **Sonnet 5.5 output_tokens 也少記（窗口 B 已核對）**：jsonl 中位 7 token 對可見 575 字元（Opus 5.5 為 121 對 458）；補估用 max(記錄值, 0.9×可見字元) 當上界，係數未校準；Sonnet 5.5 牌價沿用 sonnet 價為假設。**`sonnet` alias 解析綁 CLI 版本**：2.1.283 仍為 `claude-sonnet-5`、2.1.284 為 `claude-sonnet-5-5`，量 Explore／general-purpose sonnet 車道時逐 request 讀 `message.model`，不假設同一型號；worker 鎖完整 ID 不受影響。
- **型號判定**：只看 `type:"assistant"` 的 `message.model`；advisor attachment、`advisorModel` 設定字串不算 request。
- **advisor**：只有 `usage.iterations[]` 的 `advisor_message` 有 usage，subagent 多數沒記，只能報下限。
- **主比較口徑**：用同專案（project-a，或窗口 B 的主專案）worker 的中位數；全體只當上下界。任務較重的分段（如窗口 A 09-26 午後的 #17 P5、#58 Refit）要另分開看。
- **計價**：同窗口 A 口徑（cache_write=2×in、相對價 in 1／cw 1.25／cr 0.1／out 5），Sonnet 5.5 牌價現查再套，不沿用 Opus 價。額度 % 才是實際負擔的量尺，API 牌價只當相對權重。
- **腳本**：`parse.py`、`common.py`（價格、`OUTFIX=680`）、`an_worker.py`、`an_ver.py`＋`an_chain.py`、`an_wave.py`＋`an_agg.py`、`an_main.py`、`an_time.py`、`an_cost.py`、`an_advisor.py`、`an_slice.py`（從零切片牆鐘＝worker 牆鐘＋首輪 verifier 牆鐘；從零＝prompt 前 1500 字不含 finding／修正／delta／第 N 輪／OPEN／FAIL；掛接＝同 session、verifier 起點在 worker 起點到結束後 90 分內、路徑／PR 號／description 相似度最高，一對一貪婪配對）。腳本在 session scratchpad 暫存區，可能消失；消失時依本節口徑重寫，不必找原檔。窗口 C 的腳本：`extract.py`、`common.py`、`agents_lib.py`、`sec_agents.py`、`sec_edits.py`、`sec_design.py`、`s5_labels.py`、`run_all.sh`（同樣在 scratchpad 暫存，可能消失）。

## 額度追蹤

週額度每週一 19:00（台北時間）重置。API 牌價等價只當相對權重（窗口 A 只有 $ 等價，沒有額度 %）；**Settings > Usage 的週 % 是判斷 Sonnet 5.5 是否較省額度的唯一量尺**。由使用者定期提供，不從 jsonl 推估。

| 日期時間 | Settings > Usage 週 % | 距上次重置時數 | 備註 |
|---|---|---|---|
| 2026-09-29 10:47 | 9% | 約 15.8h | 試用起點（上次重置 09-28 19:00；這段主要是 Opus 5.5 worker＋本次 review 的 Fable 5.1） |
| 2026-09-29 22:49 | 21% | 約 27.8h | 窗口 B 第一次量測點；10:47→22:49 共 12 個百分點，同期 API 等價 $297（不含 advisor）→ 1% ≈ $24.7 |
| 2026-10-01 09:07 | 43% | 約 62.1h | 窗口 C 量測點；09-29 22:49→10-01 09:07 共 22 個百分點，同期 API 等價 $737（raw，不含 advisor）→ 1% ≈ $33.5；本腳本重跑窗口 B 為 $31.4，與上列 $24.7 口徑不同 |
| 2026-10-03 00:00 | 70% | 約 101h（上次重置 09-28 19:00 起算） | 窗口 D 量測點；10-01 09:07→10-03 00:00 共 27 個百分點（扣 09:07–09:57 間隔後約 25.1–25.8），窗口 D（09:57 起）API 等價 $571.61（spec raw，不含 advisor）→ 1% ≈ $21.17（raw），比窗口 C 的 $33.50 低 37%；額度約有三分之一在本機 jsonl 找不到對應消耗（來源未量到，見「窗口 D 量測」） |

## 評估門檻（事先訂定，2026-09-29 使用者採用 Fable 建議）

速度與品質兩者都是衡量標準（2026-09-23 使用者確認）。累積 n≥30 個窗口 B 首輪 verifier 後判定；任一條成立就回報使用者決定是否回退，不自動回退：

- 首輪 verifier OPEN 率 >62%（窗口 A 52%）。
- delta OPEN 率 >25%（窗口 A 17%）。2026-10-05 更正：17% 是 regex 口徑（重跑近似 7/42）；B–D 門檻用的手動口徑下窗口 A 為 5/37＝13.5%，再排除非修正輪為 4/36。兩邊從未同口徑比較。
- project-a（或當期主專案）worker 工具數中位 >55（窗口 A project-a 36.5）。
- 每片牆鐘（worker＋首輪驗收）比窗口 A 多 30%。窗口 A：從零切片的 worker 牆鐘＋啟發式掛接的首輪 verifier 牆鐘，project-a n=27 中位 34.1 分（P75 48.8），全體 n=75 中位 26.9 分（P75 38.6）；兩段直接相加、不含中間主對話時間，屬下限；掛接失敗排除 27 個（project-a 9），未人工抽查（未驗證）。窗口 B 用同一定義量（腳本 `an_slice.py`）。
- 主對話直接 Edit/Write 程式／設定檔的速率達窗口 A 基線（12 次／4.9 天）的 2 倍。

週額度 % 只記錄不設門檻（見「額度追蹤」）。使用者決定回退時走「回退方式」；轉為正式預設同樣要使用者明確同意。2026-10-05 使用者確認轉為正式方案，門檻不再作為回退判定；理由與 delta OPEN 成因見「轉正式與 delta OPEN 成因（2026-10-05）」。

## 窗口 B 第一次量測（2026-09-29 10:39～22:51，約 12.2h）

- 樣本：主對話 11 session、subagent 105 個；worker（`claude-sonnet-5-5`）44 個：project-b 30、project-a 10、其他 4；`worker-opus` 1；verifier 39 全為 `claude-opus-5-5`。

| 門檻 | 窗口 B | 窗口 A | 觸發？ | 樣本 |
|---|---|---|---|---|
| 首輪 OPEN >62% | regex 口徑 11/31＝35%；手動改判後 10/30＝33% | 52%（n=124） | 否 | n≈30 剛達 |
| delta OPEN >25% | regex 口徑 2/8＝25%；手動改判後 3/9＝33% | 17%（n=41） | regex 口徑否（25% 未 >25%）；手動改判後觸發 | 不足（n=8–9） |
| project-a worker 工具中位 >55 | 31.5 | 36.5 | 否 | 不足（n=10）；參考 project-b 34.5（A 27，n=30 對 59） |
| 每片牆鐘 +30% | 全體中位 18.8 分（−30%，n=20）、project-b 19.1（−29%，n=16） | 全體 26.9／project-b 27.0 | 否 | project-a n=1 不足 |
| 主對話 Edit/Write 程式檔 2 倍 | 13 次／12.2h（約 10 倍） | 12 次／4.9 天 | **觸發** | 13 次、6 個叢集 |

- 首輪／delta 的手動改判：21:47「Verify L38 round 2 plus weight」的 prompt 寫「第二輪」，regex 只認阿拉伯數字而漏判為首輪；改判為 delta 後得 10/30 與 3/9。門檻以「量法」節的 regex 口徑判定，手動改判值並列。
- 門檻只寫「任一成立就回報」，不因歸因排除；以下歸因只供使用者判斷：delta 的 3 個 OPEN 中 2 個（L38 round 2／3）驗的是升級 `worker-opus` 後的 Opus 產出，Sonnet 產出為 1/7。主對話 13 次 Edit/Write 依時間線（fresh verifier 對工具時間戳實查）：4 次是 16:00 一段未派 worker 的 hotfix；**6 次落在 worker 交回之後、首輪 verifier 派出之前**（controller 直接補 worker 產出，正是本門檻要抓的訊號）；3 次在驗收之後。**本條觸發，已回報使用者。**
- worker：project-b 工具中位 27→34.5（+28%）、牆鐘 11.9→9.1 分、$ 中位 1.75→1.51；續用 37%（A 44%）。全體 44：34 次／10.8 分／$1.57。
- verifier（手動改判口徑；regex 口徑並列於括號）：一輪定案 18/30＝60%（regex 18/31；A 41%）；≥3 輪鏈 1 條（L38，已升級 Opus＋第二意見；regex 口徑 0 條）。首輪 OPEN 全量 10 個分類（regex 口徑首輪 OPEN 11 個，多出的是 L38 round 2）：A1 1、A2 2、B 4、C 2、D 1、E 0；A1＋B＝5/10（A 15/26）；自述低嚴重 3/10，扣除後實質 OPEN 7/30＝23%。
- 新規則落地：回報「提及突變」38/44（86%），同一 regex 重跑窗口 A 為 102/182（56%）；嚴格分類「有突變證據」35/44（fresh 20/26），3 個是明說未做突變。窗口 B 的 regex 比窗口 A 的 STRONG regex 寬（多「變紅／反向驗證／sabotag」），嚴格口徑沒有窗口 A 同口徑值。
- parallel-dispatch：並行波次 5/8，並行度平均 2.38（A 1.93），最大 6；同批最長／中位 1.88×（P75 2.10，n=5），有 2 波超過 2× 線。帶 `isolation: worktree` 0/8，全為 controller 自建 worktree。
- 成本：10:47～22:49 API 等價 $297（Opus 5.5 $190、Sonnet $107；主對話 39%、worker 33%、verifier 20%、其他 8%），$24.6/h 高於 A 是活動量造成；每 worker 任務 $1.57 對 A $1.84（全體）。1% ≈ $24.7（raw 口徑 $20.1），與 Opus 期估計 $20–24 同量級，**分不出額度差異**；主對話 Opus 占 39%，worker 即使省 30%，總額最多降約 10%。advisor 72 次呼叫，已量到下限 $23.2。
- 量法新陷阱（已補進「量法」節）：Sonnet 5.5 jsonl `output_tokens` 少記約一個數量級（中位 7 token 對可見 575 字元，Opus 5.5 為 121 對 458），補估用 max(記錄值, 0.9×可見字元) 當上界，係數未校準；Sonnet 5.5 牌價沿用 sonnet 價為假設。`sonnet` alias 解析綁 CLI 版本：2.1.283 仍為 `claude-sonnet-5`、2.1.284 為 `claude-sonnet-5-5`，窗口 B 的 Explore／general-purpose sonnet 車道新舊混用；worker 鎖完整 ID 不受影響。
- 混淆：任務混合（B 多為 project-b CI／守門小片，A 為 project-a 大片）、規則改良同日生效、僅一個密集白天、尾端驗收鏈截尾、質性分類僅 10 個且單人判讀。
- 決定：2026-09-29 23:03 使用者回覆繼續試用、主觀感受比 Opus medium 快且品質 OK——當時 controller 回報的 Edit/Write 歸因是已撤回的「5 次 hotfix、其餘多為驗收後小修」；23:12 controller 以上方更正後的 4／6／3 時間線重新回報門檻觸發，**23:14 使用者確認仍繼續試用、多跑一些再評估**。下次在 project-a（或當期主專案）累積約 30 個 worker 後重判；（controller 建議）續盯主對話在 worker 交回後、驗收前的直接改檔，與 Sonnet 在難題（如 L38）是否需要升級。

## 窗口 C 量測（2026-09-29 22:51～10-01 09:07，約 34.3h）

- 樣本：窗口 C 34.27h，週額度 21%→43%（22 個百分點，無重置）；累積（B 起點 09-29 10:39～10-01 09:07）46.47h。主對話 10 session（project-c 3、project-a 2、project-d 2、project-b 1、project-e 1、project-f 1；累積 17 個）。subagent：worker（`claude-sonnet-5-5`）60、worker-opus（`claude-opus-5-5`）8、verifier 56（全 `claude-opus-5-5`）；Explore sonnet-5-5 13／sonnet-5 1、Plan opus-5-5 7／fable-5-1 1、codex-rescue 7（sonnet-5-5 外包殼）、general-purpose opus-5-5 6／sonnet-5-5 1。累積 worker 104、worker-opus 9（多的 1 個是 09-29 21:10 的 L38 round 2）、verifier 95。
- **專案代號沿用上文，但窗口 C 的 project-b session（ee3b79b6）實際操作 project-c 的 codebase，與窗口 A 的 project-b 不是同一 codebase**；窗口 A 表裡也有 project-c，是否同一專案未核對。窗口 B 節的 project-b 也含同一個 session（L38），其餘 project-b session 的 codebase 未核對。
- 口徑校準（本窗口的腳本重跑窗口 B）：首輪 OPEN 10/30、delta OPEN 3/9、主對話 Edit/Write 13、worker 44 與 B 節相同；每片牆鐘 18.1（n=21）對 B 節 18.8（n=20），接近；regex 口徑重現不出（重跑為首輪 2/17、delta 11/22，B 節為 11/31、2/8）。原因見「量法」節：regex 含「修正／finding」會把首輪 brief 判成 delta，所以窗口 C 起門檻以手動口徑判定，regex 並列當上下界。

| 門檻 | A | B | C | 累積（B＋C） | 觸發？ | 樣本 |
|---|---|---|---|---|---|---|
| 首輪 OPEN >62% | 52%（n=124） | 手動 10/30＝33% | 手動 19/41＝46%（regex 8/14） | 手動 29/71＝41%（OPEN＋INCONCLUSIVE 31/71＝44%；regex 10/31＝32%） | 否 | C n=41、累積 n=71（已超過 n≥30） |
| delta OPEN >25% | 17%（n=41） | 手動 3/9＝33% | 手動 7/15＝47%（regex 18/42＝43%） | 手動 10/24＝42%（regex 29/64＝45%） | **觸發**（手動、regex 兩個口徑都 >25%）；C 的 7 個 OPEN 有 4 個來自 L40 同一條 ≥3 輪鏈，扣除後 3/11＝27% | C n=15、累積 n=24 |
| 主專案 worker 工具中位 >55 | project-a 36.5 | project-a 31.5 | project-c 27（n=31）；project-a 38.5（n=14）；project-b 49（n=3） | project-a 37（n=24）；project-b 33；project-c 28 | 否 | project-a C n=14、累積 n=24；project-b 在 C 實際是 project-c 的 codebase（見上） |
| 每片牆鐘 +30%（門檻：全體 >35.0） | 全體 26.9 | 全體 18.8 | 全體 41.0（n=23）；去 3 個零相似錯配後 41.7（n=20）；只看 Sonnet 片 27.1（n=18）／去錯配 41.0（n=15） | 全體 20.7（n=44） | **C 全體觸發，Sonnet 子集邊界**（27.1 未達、去錯配後 41.0 超過）；累積否 | 配對受錯配影響大（見「混淆」）；定義同窗口 A 的從零切片，兩段直接相加屬下限 |
| 主對話 Edit/Write 速率 ≥2×A | 12 次／4.9 天 | 13 次／12.2h | 6 次／34.3h（本窗口門檻 6.99） | 19 次／46.5h（門檻 9.48） | C 否（差 1 次）；**累積觸發** | C 6 次（另 1 筆在 scratchpad 不計）、累積 19 次 |

- 主對話直接改程式／設定檔（C）：Edit/Write 7 筆（1 筆 scratchpad 不計）＝驗收後小修 5、worker 交回後→首輪前 1（project-b 09-29 23:46，L38 v2 測試檔頭註解，39 秒後派首輪 verifier）、hotfix 0。**另有 Bash 直接改程式檔 16 次（下限，不計入門檻）**：驗收後小修 7、rebase／合併衝突 5、hotfix 2、worker 交回後→首輪前 2；探針（突變後還原）11 次與誤判 5 次已排除。其中 project-b 09-30 14:58 一次改的是 `.github/actions/...` 的註解——CI 設定依 `../rules/10-dispatch.md`「Controller 工作迴圈」不屬小修例外。Edit/Write＋Bash 合計約 22 次。
- 「worker 交回後→首輪前」：C 共 3 次（Edit/Write 1＋Bash 2），B 為 6 次（B 節 fresh verifier 實查，僅 Edit/Write；本窗口腳本分桶重算 B 為 4 次，兩者差異的原因未核對，只能當量級參考）。
- worker／worker-opus（工具與牆鐘取第一段；$ 為 API 牌價等價，raw＝jsonl 記錄值、cor＝補估 output_tokens 後；兩者任務難度不同，**不可直比**）：

| 群組 | n | 工具 中位／P75 | 牆鐘中位（分） | $ 中位 raw／cor | 續用 |
|---|---|---|---|---|---|
| C worker 全體 | 60 | 27／54.5 | 12.0 | 1.2／1.6 | 8/60 |
| C worker project-c | 31 | 27／68 | 12.0 | 1.3／1.6 | 3/31 |
| C worker project-a | 14 | 38.5／55.5 | 19.6 | 2.0／2.5 | 1/14 |
| C worker-opus | 8 | 64.5／75.8 | 29.4 | 8.6／10.0 | 5/8 |
| 累積 worker | 104 | 29／49.2 | 10.7 | 1.3／1.9 | 17/104 |
| 累積 worker-opus | 9 | 58 | — | 8.0 | — |

- 成本（C，API 牌價等價；advisor 不在內，量得到的下限 11 次 $19.65）：

| 角色 | req | $ raw | $ cor |
|---|---|---|---|
| 主對話（opus-5-5） | 1262 | 354.64 | 376.10 |
| worker（sonnet-5-5） | 2312 | 154.79 | 200.79 |
| verifier | 1365 | 104.89 | 128.09 |
| worker-opus | 624 | 73.91 | 84.52 |
| 其他 | 688 | 48.84 | 60.68 |
| 合計 | 6251 | 737.07 | 850.18 |

- 額度換算：22 個百分點，1% ≈ $33.50（raw）／$38.64（cor）；腳本另算的 doc 牌價口徑為 $18.98／$22.78，兩組口徑差異未展開。**本腳本重跑窗口 B 為 $31.4／$37.4，與 C 相近；B 節的 $24.7 是舊腳本口徑，重現不出。** 窗口 A 沒有額度 %，無法用同口徑重算 Opus 期，所以**額度每 % 換算看不出 Sonnet 期與 Opus 期差異**。主對話占 48%（raw 口徑 354.64／737.07），仍是最大宗。
- 設計審查（`../rules/10-dispatch.md`「Controller 工作迴圈」第 1 步的不變量前置、Plan＋codex 雙方案；09-30 10:03 起）：成對 6 組（5 題）。4 題是真案例（L41、L43／44／46、L41C 兩組〔第一組被使用者中斷〕、PR625），1 題擴大到 project-a 新功能設計（brief 有不變量，不算誤觸發）；批次機械改檔誤觸發 0。L41 系列的雙審查是使用者交接文明確要求，不是 controller 自行判斷觸發。
- worker-opus 派工原因（另一 agent 判讀 9 筆，累積）：Sonnet 失敗後換車 2（L38 round 2、L38 v2）、使用者提問 1（L40）、預判難題直接派 3（L42 F「需要推理的基礎工作」、L42 B「狀態流向最複雜」、T10「都需要判斷」）、無理由 3（L40 v2、PR625 兩筆）。**0 筆走 `../rules/10-dispatch.md` §4 的 general-purpose／opus，0 筆要求先建立 root cause。** 誘因文字三處：`../agents/worker.md` description「需要 Opus 時改派 `worker-opus`」、`../rules/10-dispatch.md` §0「Opus 備用車道」、本檔「回退方式」節「臨時單次改派」。`worker.md` effort 為 xhigh、`worker-opus.md` 為 medium，已核對。
- 首輪 OPEN 的 FAIL 類型（C，19 件；**人工判讀，未經 fresh 驗收**）：主類 A1 測試沒守住交付 6、A2 漏改／修一半／迴歸 8、B 可證偽宣稱失準 3、C 範圍／契約 2、D 環境／流程 0、E 其他 0；含次類計：A1 7、A2 8、B 8、C 3、D 1。A1 多為 verifier 突變存活；A2 集中在生命週期／時序類票。本段 A2、C 的定義是窗口 C 腳本的標籤，與「質性 review」節同名類別（A2 為對抗性形狀或守門檢查器有洞、C 為真 bug）不同，不可與窗口 A／B 的同名類別直比。
- ≥3 輪鏈：L38 4 輪（第 4 輪由 worker-opus v2 新設計後 CONVERGED）；L40 7 輪（第 3 輪後使用者同意續驗，輪數重計；第 7 輪 Plan（fable）＋Codex 重設計後 v2 首驗仍 OPEN）。
- 混淆：題目組成換成生命週期／時序硬題；每片牆鐘的配對受錯配影響大；delta OPEN 集中在 L40；主對話改檔有一大塊走 Bash（上方已揭露）；project-d（本 repo 的 meta 工作）混在樣本，扣除後首輪 17/37＝46%，比例不變；Sonnet output 少記、advisor 只有下限、Codex 本體成本不在 jsonl；C 有活動的時數約 21h／34.27h。
- 決定：2026-10-01 09:35 使用者看完窗口 C 決定繼續試用；同日 worker-opus 定位改為「設計已核定、但實作須同時推理多條執行路徑或時序時可直接用，不作為失敗升級路徑」（`../agents/worker.md`、`../agents/worker-opus.md` description 與 README）。

## 窗口 D 量測（2026-10-01 09:57～10-03 00:00，約 38h）

- 範圍：窗口 D＝`1e6ccd8`（compact 提醒、非驗收回報約 2,000 字、read-back 併批）生效後；牆鐘 38.05h，週額度 43%→70%（27 個百分點，D 內無重置：`cal` 顯示 9/28、10/5 為週一）。43% 是 09:07 的讀數，09:07–09:57 的間隔本機 $39.23（project-d $18.41），以 C 單價換算約 1.2 pp、以 D 單價換算約 1.9 pp，所以 D 實際約 25.1–25.8 pp。C 與 D 用同一份程式碼、同一套計價重跑；專案代號沿用上文，另加 project-g（D 最大宗，$228：SDK 骨架、跨平台文件、ClickUp 文件），project-f 含其 worktree 目錄；量測用的 session（efcc5f53）已排除。腳本（`extract.py`、`sec_agents.py`、`sec_edits.py`、`norm.py`、`replen.py`、`replen_cap.py`、`compact_ev.py`、`compact_compliance.py`；主對話：`scan.py`、`analyze.py`、`analyze2.py`）在 session scratchpad 暫存，可能消失。
- 校準（C 用新腳本重跑）：總成本 spec raw／cor 737.07／850.18、主對話 1262 req／$354.64、worker／worker-opus 60／8、首輪 OPEN 19/41、delta OPEN 7/15、每片牆鐘 41.03（n=23）、主對話 Edit/Write 6、1% ≈ 33.50／38.64、context 中位／P90 343,973／769,904、連續唯讀 request 占比 23.8%（$84.45）、主對話收到的 handback 字數中位 5,227，全部與窗口 C 期的原始量測報告相同（其中 context 分布、連續唯讀占比、handback 中位不在本文件 C 節，原值見 `harness-facts.md`「主對話 context 大小怎麼量、cache 何時過期」）；兩版 `analyze`／`analyze2` 輸出 `diff` 為空，腳本未漂移。**唯一重現不出的是 C 節的「約 21h」**：沒有任何腳本算這個數；新定義（任兩 request 間隔 ≤15 分合併，任何角色）下 C 為 14.84h，`norm.py` 其他定義得 14.3–17.1h。C 節原文不改，D 與 C 的比較一律用新定義。
- 樣本：主對話 request 1821（C 1262）、session 42（≥20 req 者 21；C 為 10／8）；worker＋worker-opus 派工 63（C 68）；general-purpose sonnet 由 1 個增為 22 個。
- **結論：「比較省」部分成立。** 兩個正規化分母只降了一個：每活動小時耗的額度降了，每個 worker 任務耗的額度反而升了。本機 API 等價 $ 在兩個分母上都降了，但每 1% 額度對應的本機 $ 從 $33.50 掉到 $21.17（−37%），代表 D 的額度約有三分之一在本機 jsonl 找不到對應消耗（來源未量到，見「混淆」）。

| 指標 | C | D | 變化 |
|---|---|---|---|
| 牆鐘時數 | 34.27h | 38.05h | |
| 週額度 pp | 22（21→43） | 27（43→70）；扣間隔後約 25.1–25.8 | |
| 有活動時數（≤15 分合併） | 14.84h | 20.43h | +38% |
| 　敏感度 ≤10 分／≤30 分 | 14.84／15.53 | 19.65／22.82 | |
| **pp／活動小時** | **1.483** | **1.322**（扣間隔 1.23–1.26） | −11%（扣間隔 −15～−17%） |
| worker＋worker-opus 派工數 | 68 | 63 | |
| **pp／worker 任務** | **0.324** | **0.429**（扣間隔 0.40–0.41） | +32%（扣間隔 +23～+26%） |
| 敏感度：pp／首輪驗收片數（手動） | 0.537（41） | 0.574（47） | +7% |
| 敏感度：pp／(worker＋worker-opus＋general-purpose) | 0.293（75） | 0.284（95） | −3% |
| 本機 $ raw／活動小時 | 49.68 | 27.98 | −44% |
| 本機 $ raw／worker 任務 | 10.84 | 9.07 | −16% |
| 窗口總 $ spec raw／cor | 737.07／850.18 | 571.61／670.68 | |
| **1% ≈ spec raw／cor** | **33.50／38.64** | **21.17／24.84** | −37% |
| 1% ≈ doc 牌價 raw／cor | 18.98／22.78 | 12.20／14.94 | |
| advisor 下限（次數／$） | 11／19.65 | 22／37.85 | 加進去後 1% ≈ 34.40 對 22.57 |
| 扣除 project-d 後 $ raw | 713.55 | 559.65 | project-d 只占 3.2%／2.1%，不影響結論 |

- 成本角色占比（spec raw）：主對話 C 48.1%→D 55.5%（含 headless 探針 $4.27）；worker 21.0%→15.7%；verifier 14.2%→12.7%；worker-opus 10.0%→3.8%；其他（general-purpose、Plan、Explore、codex）6.6%→12.2%。
- 另有 3 個 D session 在 D 起點前開啟（$42.24，主要是 project-a 的 6476709b），它們在 11:15／13:39 compact 之前跑的是舊規則。

**規則一：compact 提醒（`compact_ev.py`、`compact_compliance.py`、主對話 `analyze*.py`）——0 次主動提醒。**

- D 主對話 assistant 文字含 `/compact` 0 次；全文搜 `compact|壓縮|300K`，D 只有 6476709b 10-01 13:39 一處，是使用者先要求 compact 並索取接續 prompt 之後才寫的。AskUserQuestion 輸入含 compact：C、D 都是 0。
- D 有 11 次 `gh pr merge` 發生在 context ≥300K（d343e48e 7 次，該 session 10:26 開、已載入新規則；4215bd99 3 次；35e418fc 1 次），30 分內都沒有 compact 提醒。使用者離開 >60 分且 context ≥300K：D 有 2 次（6476709b 10-01 16:13，376K／284 分；35e418fc 10-02 13:33，301K／78 分），離開前都沒有提醒。
- D 主對話沒有任何 Bash 量自己的 context（搜 `cache_read_input_tokens` 或讀自己的 jsonl：只有 project-d 的 1 筆，與量 context 無關）。不量就觸發不了這條規則。
- 實際 compact 事件（`compact_boundary`）4 次，全是使用者手動 `/compact`、沒帶保留指示：

| 時間 | session | 專案 | compact 前 context | 誘因 |
|---|---|---|---|---|
| 10-01 11:15 | 6476709b | project-a | 219K | 使用者先要求 compact 並索取新 prompt |
| 10-01 13:39 | 6476709b | project-a | 224K | 使用者先要求 compact 並索取接續 prompt |
| 10-02 01:36 | 4215bd99 | project-f | 399K | 使用者直接打，前面沒有提醒 |
| 10-02 09:30 | 4215bd99 | project-f | 172K | 使用者直接打，前面沒有提醒 |

C 有 2 次（09-30 12:29 project-a 494K；10-01 09:06 project-c 844K，這次 controller 有附保留指示）。

| context 指標 | C | D |
|---|---|---|
| 主對話 request 數 | 1262 | 1821 |
| 中位 | 344K | 201K |
| P75／P90 | 571K／770K | 304K／385K |
| 最大 | 916K | 497K |
| >400K request 占比 | 42.3%（534/1262） | 7.1%（130/1821） |
| 間隔 >60 分後的 cache 寫入（次數／$） | 9／40.68 | 4／9.12 |
| 完整重寫（cr<20% ctx、ctx>50K）次數／$ | 11／45.53 | 7／12.11 |
| 主對話 session 數（≥20 req） | 10（8） | 42（21） |

- 歸因：context 下降來自 session 數從 10（8 個 ≥20 req）變成 42（21 個 ≥20 req），加上 4 次使用者自己打的 compact；不是規則觸發。`analyze2.py` 的模擬：D 若在 300K 時 compact 到 40K，還能再省 17.5%（$55）；C 同條件是 38.3%。ctx 取最後一次 model pass；advisor request 的 raw usage 會把兩次 pass 加總，所以 c0b108d6 的 raw 最大值是 763K。

**規則二：回報長度（`replen.py`、`replen_cap.py`、`analyze.py`）——有執行，沒效。**

| 口徑（字元數，中英混排，路徑與程式碼也算） | C | D |
|---|---|---|
| 主對話收到的 handback 字數中位（與 C 基線 5.2K 同口徑） | 5,227（n=175） | 4,958（n=194） |
| 每段最終回報，全體 中位／P90 | 3,928／8,644 | 3,694／7,032 |
| 非豁免角色 中位／P90／>2000 占比 | 3,198／6,222／72% | 3,266／6,038／86% |
| worker 中位／P90 | 3,462／6,027 | 3,489／5,584 |
| worker-opus 中位／P90 | 2,515／4,207 | 4,882／5,387 |
| general-purpose 中位／P90 | 2,847／3,862（n=7） | 2,793／6,815（n=33） |
| codex:codex-rescue 中位 | 8,433（n=7） | 3,972（n=6） |
| verifier（豁免）中位 | 4,146 | 3,690 |
| Explore（豁免）中位 | 12,588 | 8,286 |
| Plan（豁免）中位 | 10,045 | 7,919 |

- D 非豁免派工 103 份，brief 寫了 2,000 字上限的有 23 份（C 0 份；C 有 3 筆 regex 命中，但都是「約 2000 行」之類的誤判）。這 23 份的回報中位 5,113 字，**全部超過 2,000**（96% 超過 3,000）；沒寫上限的 80 份中位 3,188。會寫上限的多是大任務、回報格式欄位列得很長，兩組不能直接比；但能確定的是，寫了上限的回報沒有一份守住。

**規則三：read-back 併批（`analyze2.py`）——沒有改善。** 連續唯讀工具 request（Bash／Read／Grep／Glob、<300 字）在每段連續序列中第一筆之後的占比：C 23.8%（369 req，$84.45）→ D 25.5%（571 req，$80.84）。

**試用門檻指標（`sec_agents.py`、`sec_edits.py`）：**

| 門檻 | C | D | 觸發？ |
|---|---|---|---|
| 首輪 OPEN >62%（手動） | 19/41＝46% | 19/47＝40% | 否 |
| 首輪 OPEN＋INCONCLUSIVE | 19/41＝46% | 24/47＝51%（INC 5；C 為 0） | 否 |
| 首輪 OPEN（regex 口徑） | 8/14 | 13/31 | 參考 |
| delta OPEN >25%（手動） | 7/15＝47% | 7/9＝78% | **觸發**；n=9，7 個裡有 4 個來自兩條文件草稿鏈（513342a4 任務一 ×2、4e3c00d5 草稿 ×2）；regex 口徑 13/25＝52% |
| 每片牆鐘（全體 >35.0） | 41.0（n=23） | 18.2（n=27）；只看 worker 15.7（n=21） | 否；組成不同：C 多 project-b 生命週期硬片＋worker-opus，D 多文件／SDK 骨架片，project-g 23.5（n=11） |
| 主對話 Edit/Write（門檻 C 6.99／D 7.77） | 6 | 規則口徑 18；扣掉 6 個 10 秒權限探針 session 的 9 筆 `probe-ok/deny.txt` 後 9 | **觸發**（兩種算法都超過） |
| 其中「worker 交回後→首輪前」 | 1 | 3–4（4215bd99 23:47／23:48 controller 自己 red/green；9ac7875a 09:55；9ac7875a 10:19 在 PROSE-ONLY 驗收和外部 review 留言之後，較像驗收後修正） | |
| Bash 直接改程式檔 | 32 候選→人工 16 | 37 候選（規則口徑，未逐條核對）；其中至少 9 筆明顯是 md 內容或 scratchpad 誤判；規則分桶：驗收後 16、hotfix 9、交回後→首輪前 9、其他 3 | 未判 |
| CI 設定被主對話直接改 | 1 | 1（`.github/actions/...`，PROSE-ONLY 後） | 違反 `../rules/10-dispatch.md` 小修例外 |
| worker 工具中位／牆鐘中位／$ 中位 raw | 27／12.0 分／1.2 | 27／10.0 分／1.2 | |
| worker-opus 派工 | 8 | 7 | |

- D 至少兩處是主對話直接實作而沒有派 worker：4215bd99 10-01 23:47–10-02 01:43（在 worktree 裡自己 red/green，後面有「實作完成，測試全綠 966/966」）、9a9f7650 10-01 23:27–23:35（Bash 改 app 與測試檔，之後才派 worker-opus 做第二段）。
- worker-opus 派工原因（`out_wopus_D.txt`）：

| 分類 | C（9，累積） | D（7） |
|---|---|---|
| Sonnet 失敗後換車 | 2 | 0 |
| 使用者要求 | 1 | 0 |
| 預判硬題（明寫理由） | 3 | 2（9a9f7650 23:42、4e3c00d5 20:10，理由都是實作要同時推理多條時序路徑；都符合新規則） |
| 沒寫理由 | 3 | 5（其中 L51、L53、#229 緊接在 Plan＋Codex 雙設計核定之後，brief 內容是時序題，形狀符合新規則，只是沒寫理由） |

worker-opus 成本占比 10.0%→3.8%，牆鐘中位 29.4→11.5 分，$ 中位 8.6→3.1。

**混淆因素與未量到：**

1. **本機以外的額度消耗（未量到）**：1% 對應的本機 $ 掉了 37%。可能的來源：另一台機器（Windows 桌機）、claude.ai 網頁對話、advisor 的實際用量（jsonl 只有下限，D 是 C 的兩倍：22 次、$37.85）。哪一個占多少本機資料判斷不了，不估；使用者 2026-10-03 確認窗口 D 期間有在 Windows 桌機使用，Windows 用同一帳號時其用量同樣計入週額度，所以本窗口的 pp 比值與 1% ≈ $ 都混入本機量不到的用量，「比較省」的結論只能當方向參考。
2. 專案組成換了：D 最大宗是新的 project-g，C 是 project-b／c 的生命週期硬題；D 的切片偏文件與骨架，牆鐘、首輪 OPEN 不能直接跟 C 比。
3. 使用習慣變了：session 數 10→42，所以 context 下降的主因是開新 session，不是規則。
4. 任務分母不穩定：general-purpose 7→32，加上主對話自己實作的段落，worker 數不是穩定的工作量分母；所以另列 pp／首輪驗收片數（+7%）和含 general-purpose 的版本（−3%）當敏感度。
5. 活動時數 D 多 5.6h，而且晚間時段比較長。
6. 3 個 D session 在 D 起點前開啟（$42.24）；D 有 headless `claude -p` 探針 $4.27（C 沒有）；project-d 兩窗都很小。
7. Sonnet output 少記、advisor 只有下限、Codex 本體成本不在 jsonl（兩窗相同）。

**分級：**

- 已驗證（腳本實跑輸出）：上列校準；所有本機 $、pp 比值、活動時數（依本次定義）；compact 事件、提醒次數、merge／離開時點、context 分布；回報長度與 brief 上限計數；唯讀占比；首輪／delta OPEN（手動與 regex 口徑）、牆鐘、Edit/Write 規則口徑、worker-opus 派工清單。
- 人工判讀、未經 fresh 驗收：Edit/Write 扣探針後 9、交回後→首輪前 3–4；worker-opus 原因分類；「主對話自己實作」兩處；delta OPEN 集中在文件鏈。
- 未量到：D 額度裡本機以外的部分（來源與占比）；C 節「約 21h」活動時數的來源；D 的 Bash 改檔人工總數（只有規則口徑）。

## 轉正式與 delta OPEN 成因（2026-10-05）

專案一律用代號；原始逐筆分析（含 transcript 路徑）不放進本 repo。L38、L40 沿用上方各窗口的代號。

1. **決定**：2026-10-05 使用者確認 `worker`（Sonnet 5.5/xhigh）與 `worker-opus`（Opus 5.5/medium）轉為正式方案。依據是本節的成因分析，不是「評估門檻」的數字；delta OPEN 門檻在 B–D 的計數都超過 25%（見下一點），但成因分析指向選題與核對缺口，沒有支持「Sonnet 型號造成」的證據（見下方結論）。
2. **計數**（手動口徑，以窗口 D 腳本 `manual_delta` 重跑，與前文計數相同）：B 3/9、C 7/15、D 7/9，B–D 合計 17 個 OPEN／33 個 delta。非修正輪被算成 delta 的（使用者新需求的新變更，不是修正複驗）排除後，D 為 6/8。窗口 A 的口徑更正見「窗口 A 基線」節與「評估門檻」節附註。
3. **主類**：每個 OPEN 只取一個主類，按序套用：非修正輪歸 F6；與前幾輪 finding 同根因、只是換層或換形狀重現歸 F4；純文件或規格草稿的事實／引用／措辭問題歸 F5；修正後行為正確但 verifier 自設突變存活（測試缺口）歸 F6；其餘依機制歸 F1／F2／F3。

   | 窗口 | F1 修正未完成 | F2 修正引入迴歸 | F3 verifier 抓到既有新問題 | F4 設計缺陷換層重現 | F5 文件／散文 | F6 其他 | 合計 |
   |---|---|---|---|---|---|---|---|
   | A（手動口徑） | 1 | 2 | 1 | 0 | 0 | 1（非修正輪） | 5 |
   | B | 0 | 0 | 0 | 3 | 0 | 0 | 3 |
   | C | 0 | 0 | 0 | 4 | 1 | 2（測試缺口：修正後行為對，但 verifier 自設突變存活） | 7 |
   | D | 1 | 0 | 0 | 0 | 4 | 2（測試缺口 1、非修正輪 1） | 7 |

   F4 全在 L38／L40 兩條鏈。L40 的歸類屬判讀：若改以各輪自己的機制計，C 會變成 F2 3、F3 1、F5 1、F6 2；B 的 L40 那一筆也會變 F2。
4. **修正者**（B–D 全部 33 個 delta，修正者依「verifier 派出前最近完成的 worker／worker-opus；中間只有主對話改檔則記 controller」判定）：

   | 修正者 | OPEN／delta | 備註 |
   |---|---|---|
   | `worker`（Sonnet 5.5） | 8／20 | 扣 L40 鏈 2 筆為 6／18 |
   | `worker-opus`（Opus 5.5） | 5／6 | 5 筆 OPEN 全在 L38／L40 鏈 |
   | controller 自修（主對話 Opus 5.5） | 4／6 | 4 個 OPEN 中 1 個是非修正輪 |
   | 混合（worker＋controller） | 0／1 | 另計 |

   窗口 A（`worker`＝Opus 5.5/medium）修正 35 個、OPEN 4（修正者為啟發式判定，只有 A 的 5 個 OPEN 逐筆核對過）。**窗口 A 的 `worker` 與 B–D 的 `worker-opus` 同為 Opus 5.5/medium，controller 是主對話的 Opus 5.5；所以 Opus 在 B–D 的較高 OPEN 率反映的是選題（`worker-opus` 只接已核定設計的時序硬片，L38／L40 是設計缺陷），不是型號或 effort 的結論，不得當成「Opus 修得比較差」引用。**
5. **結論**：
   - F4 換模型無效：L38／L40 換 Sonnet、Opus 都以換層形式重現，走設計審查（`../rules/20-judgment.md` §1「換路的質性訊號」），不加能力層。
   - Sonnet 修的 OPEN 扣 L40 後 6 筆：文件新句未對源 3、自設突變存活 2、「已被測試鎖住」不實宣稱 1。性質是沒有核對，不是理解錯誤。
   - 17 個 FAIL 中 10 個來自 delta brief 新指定的探測（對抗性探測、自設突變、開放式找漏洞；其中 L40 的放寬探測屬 `../rules/20-judgment.md` §2「改既有檢查」的規定，不是 brief 失誤），另 6 個來自針對修正 diff 的迴歸探針或文字核對，1 個不適用。L38 的 brief 還要求 verifier 探針跑完刪除，L40 第 2 輪的 verifier 自述上次探針沒有留存、依描述重建，所以規則要求的固定 evidence set 實際上無法逐輪重用。
6. **據此修改的規則**（2026-10-05，同批次）：
   - `../rules/20-judgment.md` §2「補充判準（修正與驗收輪次）」：delta brief 附探針落檔路徑；不另指定新探測形狀（放寬除外）；修正者（含 controller 自修）對文件新句逐句對源、對測試斷言與守門檢查附突變紅／綠，證據帶進 delta brief。
   - `../agents/verifier.md` 規則 4 與 `../codex/agents/verifier.toml` 規則 9：首輪與迴歸探針落檔到指定的 repo 外路徑、不刪，delta 輪重跑附上的探針檔。
   - `../rules/10-dispatch.md`「Controller 工作迴圈」小修例外段：修 verifier finding 的自修同樣適用 §2「修正與驗收輪次」對修正者的要求。
   - `../rules/10-dispatch.md` §0「執行者預設」、`../docs/repo-layout.md`、`dispatch-cost-review-2026-09-17.md`：移除「試用」標示並記錄使用者決策。
7. **分級**：已驗證：B／C／D 計數與修正者 model（腳本重跑、`message.model` 讀取）。人工判讀、未經 fresh 驗收：F 分類（單人判讀）；n=17，且 L38／L40 兩條鏈與文件草稿佔大半，樣本不足以支撐型號層級的結論。

## 回退方式

- **臨時單次改派**：派 `worker-opus`（不帶 `model`，model 與 effort 由其 frontmatter 決定）。適用條件依 `../agents/worker-opus.md` description（2026-10-01 起：設計已核定、但實作須同時推理多條執行路徑或時序時，或使用者指定）；失敗後升級不走這條，依 `../rules/10-dispatch.md` §4。不必動制度檔。
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
- 教訓重演（已驗證）：`50-lessons.md` 2026-09-23 CI workflow 條仍是「尚未」，`1fd0fa6d` 09-25 12:09 controller 直接 Write 某音訊專案的 `.github/workflows/release.yml`、commit、PR，12:13 merge，無 worker 無 verifier。
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
