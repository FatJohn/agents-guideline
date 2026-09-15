---
name: parallel-dispatch
description: 一個開發任務可能拆給 ≥2 個 coding agent 平行做（divide & conquer），或讓多個 agent 各解一版再選優（agent race）時使用；spec 尚未切分、要先判斷值不值得平行時也用。觸發句：「平行做」「同時派」「這幾個 issue 一起處理」「切成幾個 task 同時開發」「能不能切」「讓幾個 agent 各做一版比較」，及英文 "in parallel"、"split this into tasks"、"race two agents"。已有切好的 tracker 項目要直接平行派工與整合驗收時同樣觸發。
allowed-tools: Bash(git:*), Bash(gh:*), Read, Grep, Glob
---

# Parallel Dispatch — 平行開發的 orchestration

本 skill 只管 **orchestration strategy**：值不值得拆、怎麼拆、誰擁有什麼、怎麼驗、怎麼整合。它**不是** workspace／terminal／process manager。`<REPO>` 依全域 `CLAUDE.md`／`AGENTS.md` 的 bootstrap 解出；本檔承接 Claude `<REPO>/rules/10-dispatch.md` 與 Codex `<REPO>/codex/rules/10-dispatch-codex.md`，是切分、驗收與整合的唯一 canonical。

四個概念彼此獨立，不得互相等同：

```text
Task（一片工作，有 ownership 與驗收條件）
 ↓ 指派給
Worker / Agent（任一 coding agent；平台角色名在 adapter）
 ↓ 跑在
Execution Environment（同 session 的 subagent、獨立 CLI process，或任何能 launch／follow-up／query／collect／stop 一個 agent 的容器）
 ↓ 需要隔離寫入時才配
Optional Git Worktree
```

最低需求只有 **git、shell、任一 coding agent CLI 或 subagent 工具**。其他工具只能以 **execution adapter**（§9）進來改善 UX，不能改變本檔任何一步；換工具只加一份 adapter，不改本檔。執行環境與容器的工具名稱只出現在 adapter 檔；本檔只在承接關係與 reference 分工處點名平台，流程步驟本身不依賴任何一個。

**reference 分工**：`references/templates.md`（task graph、worker brief、worker report、integration record、status board 的格式，及 tracker 對應預設）；`references/worktree.md`（git 隔離、ownership 稽核、integration tree、清理的機制與證據條件）；adapter：`references/claude-code.md`（Claude Code 同 session subagent）、`references/codex.md`（Codex 同 session subagent）、`references/cli.md`（外部 CLI process 與其 terminal／workspace 容器，及沒有 controller 的人手多開）。

## 核心流程

```text
REQUEST → ANALYZE（§1）→ PARALLELIZE?（§2）
                             ├─ no  → 單一 worker，走一般 dispatch
                             └─ yes → TASK GRAPH（§3）→ WORKERS（§4）→ VALIDATION（§5）
                                      → INTEGRATION（§6）→ FINAL VALIDATION（§7）→ RESULT
任何一步出現新資訊 → 回 §3 re-plan（§8），不死守最初的 graph。
```

## §1 ANALYZE：任務分析

- **入口 A**：tracker 已有切好的項目 → 不重切，但每項仍要補齊下列欄位；tracker 上的數字與事實以現查為準，與使用者提供素材不一致時在 plan 並列，不靜默採用。
- **入口 B**：spec／grilling 結論尚未切 → 先切。只動一個模組且預估 ≤3 片由 controller 自切；跨模組或依賴不明時依平台 dispatch 派 read-only 規劃角色，controller 核定。

每個候選子任務必帶四項：**目標、獨立驗收條件、依賴的子任務、預估 ownership**（repo 相對路徑＋函式或行範圍，**含測試與 fixture**）。填不出獨立驗收條件的片不能平行；每片還要能**只憑自己的 brief 站住**——worker 對其他片零認知，需要邊做邊問別片在做什麼的就不是一片。

## §2 PARALLELIZE?：值不值得

```text
parallelize only when: parallel benefit > coordination + merge cost
```

**改派單一 worker**（任一成立）：改動範圍小或多數集中在同一檔；任一片沒有獨立驗收條件；只有一片無依賴（其餘都在等它）；每片都會碰同一函式或相鄰區段（預估行範圍相距 10 行內）；整份 spec 單一實作者即可完成，拆了不到一個 agent 的合理工作量；子任務定義不清楚；預期需要頻繁交換 context；merge 或整合成本高於省下的時間。相同檔但不同且不相鄰的函式不算 git 重疊，仍受 §3 語意風險檢查。

**選 pattern**：
- **Pattern A — Divide and Conquer**：子任務彼此不同、可各自驗收、最後全部整合。重點是 ownership、dependency、integration order。這是預設。
- **Pattern B — Agent Race（competing solutions）**：問題單一但解法路徑不確定、正確性或可維護性難以事前判斷，且成果互斥（例如同一個演算法、同一個 API 設計的兩種取向）。N 個 worker 拿同一份 brief 各自做，最後比較、只整合一個 winner，**不 merge 全部方案**。race 的成本是 N 倍工作量換一次選擇權，只在選錯代價高於重做代價時用。

**Human checkpoint 1**：決定後向使用者說明為什麼拆或不拆、用哪個 pattern（一段話即可，不要求使用者處理任何 infra 細節）。

## §3 TASK GRAPH：依賴圖、所有權與批次

輸出一張 dependency graph（格式見 `references/templates.md`），每個節點對應一份 worker brief。

**兩種量法，不可互相取代**：
- **重疊矩陣**量 git 合併性：納入所有片的所有預估路徑（含測試、fixture、設定、CI 檔）；同函式或相鄰區段的片合併成一片或序列。
- **語意風險**量行為互動：merge conflict（含 git 可自動合但語意互踩）、同檔或同目錄、跨目錄 API／schema、共用狀態、build 產物、CI job 順序或產物依賴。這不阻擋平行，但決定 §6 要不要派整合 verifier。

**依賴**：有依賴的片序列做，只有互不依賴者同批。「先凍介面再平行」只在簽名可先固定、下游驗收只依賴簽名時成立；stub 由 controller 建。缺權限或外部依賴未落地的單片不入批，其餘可繼續。

**Foundation 先落地**：多片共用的地基（套件清單、共用型別／schema、router／DI／export 的 registry、測試設定、migration 序號）先由 controller 或一個序列片做完並 **commit 到 base**，graph 記下 foundation SHA，之後才 fan out；不得讓兩片各自補同一份地基——那是最常見、也最沒必要的 merge conflict 來源。

**批次上限**：預設一批 **3** 片，最多 4 片且要寫出理由（每片獨立且 review 量可承受）；不滾動補位；下一批須等本批整合完成（§7）。平行是有成本的資源：每多一個 worker 就多一份 context 複製、一個要 review 的 diff、一次整合風險；而驗收與整合本身是序列的，多開 worker 不會讓瓶頸變快。

**Ownership**（每份 brief 必填）：objective、scope、允許路徑、禁止路徑或子系統、依賴、預期輸出、驗證命令、完成定義。允許路徑以 repo 相對路徑寫，實際落地位置由 adapter 決定（`references/worktree.md`）。目標是**兩個 worker 不會同時改同一檔**，做不到就序列。三條硬規則：
- **共用觸點不得有兩個 owner**：lockfile、registry／index 檔、generated artifact、migration 序號、changelog 這類單檔熱點，要嘛指定唯一 owner，要嘛留給 integrator 在 §6 統一改，要嘛改成每片一個 fragment 由整合時合併。沒有 owner 的路徑任何片都不准改。
- **ownership 空白的片不派**：沒有允許路徑就沒有邊界可守，也沒有東西可稽核。
- **brief 只描述 WHAT**：branch 名、commit 訊息、push／PR 等 commit-time 事項只寫在 brief 的 Execution environment 欄（由 adapter 填），Objective 與 Expected output 不得提到，否則兩層指示互相打架而 worker 解衝突的方式不一致。

**Pattern B 的 graph**：N 個節點共用同一份 brief（只差 worker 標籤與落地位置），加一個「比較與選擇」節點依賴全部 N 個；比較準則（測試、正確性、可維護性、複雜度、與既有風格一致）在 graph 就寫死，不事後補。

**Human checkpoint 2**：切片清單（或 race 的 N 與比較準則）先給使用者看。tracker 由專案規格宣告：一批對應一個 tracker 項目、切片對應其子項目，各平台的預設對應見 `references/templates.md`「Tracker 對應」。使用者明確核可一次只授權該清單的 tracker 建立；清單外項目、下一批、阻擋片的 tracker comment 都要另取授權（鐵律二）。

## §4 WORKERS：派工

**Preflight（fan out 之前）**：記錄 base SHA；確認 base working tree 乾淨；在 base SHA 跑一次完整檢查並記錄結果（全綠，或逐項列出已知紅項）——沒有這份 baseline 就分不出 §8 的「屬 base 還是屬該片」。preflight 不過就不 fan out，先修 base。

**Agent 選擇**：caller 可指定 preferred agent、available agents、agent capabilities；沒指定就用當前 adapter 角色表的預設 worker。可依任務性質建議（實作、refactor、research、測試、review 各有偏好），**不 hard-code 領域對 agent 的對應**（不是「frontend = 某家、backend = 另一家」）。

**每個 worker 都必須拿到**：完整 brief（`references/templates.md`）、唯一寫入者宣告、自己的落地位置（隔離時為 worktree 絕對路徑）、驗證命令、回報格式。brief 開頭明寫「你是被派來的執行者，親自完成，不要再派工」，並告知它不是 codebase 裡唯一在改的人——ownership 外看起來殘缺的東西不要順手修或回退。暫時探針的 plan 必須寫還原指令、探針期間預期會紅的既有檢查，且不得為此順手修 fixture；長輸出落檔使用切片專屬前綴。誰建 worktree、用什麼指令 launch 由 adapter 決定；**worker 可否 commit／rebase 由該 agent 的合約決定**（各平台的合約與宣告句見對應 adapter），adapter 只在 brief 的 Execution environment 欄如實填入，不做授權判斷。

**回報**：worker 完成後必須回 structured report（Status／Summary／Files changed／Validation／Issues／Integration notes／Commit／Location，格式在 `references/templates.md`）。只回「Done」＝未完成，退回補齊。controller **逐欄 read-back**，不採信自述：Commit 用 `git show` 核、Files changed 對 `git diff --name-only <base>...HEAD`（高報與低報都算不符）、Validation 由 §5 的驗收者在該落地位置重跑；實作類任務改動為零＝失敗，不是「沒事可做」。adapter 的 query status 只是線索，**不得憑摘要 merge**。

## §5 VALIDATION：切片驗收

每片完成即進行獨立 fresh-context 驗收與必要 CI，不等同批其他片。驗收者依平台 dispatch 的角色分流（adapter 寫明），首輪用 worker 沒用過的探測形狀（delta 輪依 `<REPO>/rules/20-judgment.md` §2「修正與驗收輪次」重跑原探針加修正 diff 的迴歸探針，不換形狀），並確認「移除或固定該交付的輸出／訊息／綁定時有檢查會紅」（`<REPO>/rubrics/code-change.md`「交付的價值要被測試守住」）。修正後依 `<REPO>/rules/20-judgment.md` §2「停止端」處理，三輪回報點照計。

- CI `skipping` 不算通過；endpoint／timeout 類錯誤僅在同一 SHA 重跑一次轉綠時記為 flake，否則當真失敗；CI 重跑次數與原因記在 PR。
- 改既有檢查、過濾或驗證規則的片，動手前依 `<REPO>/rules/20-judgment.md` §2「改既有檢查／過濾／驗證規則」凍結行為基線。
- controller 自己做 tamper／探針時，先以替換計數 `== 1` 或 `git diff --stat` 證明改動真的發生，再讀測試結果。

**Pattern B 在此比較**：在各自乾淨的落地位置跑**同一組**測試與檢查，依 §3 寫死的準則列表比較，結論給使用者（表格：方案 × 準則）。只有 winner 進 §6；落選方案的 worktree 依 `references/worktree.md` 清理（本次自建的可直接清，非自建的要授權）。選不出來就是準則寫得不夠，回 §3 補準則，不擲硬幣。

## §6 INTEGRATION：獨立階段

**worker 完成 ≠ 任務完成。** Integrator（預設由 controller 擔任，高風險可派獨立角色）逐步做：

1. 收齊所有 worker report，任一片 blocked／failed 先進 §8。
2. **ownership 稽核**（機械）：每片 `git diff --name-only <base>...<head>` 對照 brief 的允許路徑，越界的片退回；再對每一對片取實際改動檔的交集（`comm -12`，指令見 `references/worktree.md`「ownership 稽核」），任一對非空就停下先解 ownership，不往下走。
3. 對照原始需求：合起來有沒有涵蓋全部、有沒有多做。計畫裡點名的符號、路徑、訊息逐項 `git grep`，零命中＝被默默丟掉；grep 只證存在不證正確，正確性靠 §5 與第 7 步。
4. 檢查片與片的介面一致（簽名、schema、事件名、錯誤格式）。
5. 決定 merge 順序：**通過當前 base gate 的完成順序**，不強求切分時的順序。
6. 處理 conflict：預檢用唯讀的 `git merge-tree`，不用會動 working tree 的試合。純文字 conflict 由 integrator 在 integration tree 解，或以 follow-up 要 worker 在自己的落地位置 rebase 後重跑驗證——**不在 worker 的落地位置由第三者動手**。git 能自動合但語意互踩的由 controller 判斷，判不出才問使用者，**不以「無 conflict」跳過語意風險判定**。
7. 建暫存 integration tree／branch（`references/worktree.md`），跑完整測試／lint／typecheck／build；記錄 base SHA、每片 HEAD、integration tree／commit 與結果。任何 base、切片 HEAD 或 integration 內容變動都使受影響證據失效，必須重驗。
8. 逐片 merge（PR 或直接 merge 依專案流程）前，以**當前 base 加該候選片**建 integration gate 跑受影響的完整檢查；base 有 auto deploy 時這個中間狀態不可只由全批最終 tree 代替。不要拿全批最終 tree 比較第一片 merge，否則會把後續合法切片誤判為失效。
9. §3 語意風險任一成立才派一名 fresh verifier，只驗片與片的互動及合併後的執行環境（fresh checkout、CI job 順序、產物依賴），不重驗已通過的切片條件；驗收者在 integration tree 的乾淨環境執行。無風險時最終證據只需 integration tree 的完整測試。驗收 prompt 裡的測試數、新增條數由 controller 現查（如 `git grep -c`），不抄 worker 自報。
10. 必要時要求 worker follow-up（帶原 finding、diff、受影響驗收條件），修正後依停止端分流機械結案或 fresh delta。

**收斂即整合，不等整批**：§3 語意風險判定為無的片，一收斂（`CONVERGED`，或 `PROSE-ONLY` 修完 read-back）就單獨走第 7–8 步 merge 或開 PR，不等同批其他片；只有判定有語意風險的片才等它互動的對象一起做第 9 步。早 merge 前第 2 步的交集稽核改用**其他片 brief 的允許路徑**對本片實際改動檔取交集（非空就停）；其餘片完成後，再以實際改動檔補跑一次完整交集。§7 的全批最終驗證照做。（2026-09-14 實測：兩片批次中先收斂的一片等另一片三輪驗收，白等 55 分鐘，占整批 wall time 一半。）

merge／push 一律由 controller 依當次 session 授權執行；本 skill 不授權任何對外或不可逆動作。每次 merge 後比對實際 merge 結果的 tree 與該次候選 integration tree，記錄 merge SHA 並確認 required CI；不一致就停下一次 merge，先查明並重驗。某片 merge 後才發現壞：revert **該片**的 merge（或其 squash commit），其餘片不動，不整批回退；受影響證據依第 7 步作廢重驗。

## §7 FINAL VALIDATION 與 RESULT

全批 merge 後，在目標 base 跑完整測試與 required CI；以 `git diff --name-only <base>...<merge>`（或 PR 的檔案清單）比對實際改動與 §3 預估路徑，落差寫進整合記錄，作為下次切分的校正。清理 worktree 與 branch 只在 `references/worktree.md` 的證據條件全部成立後進行，且以 `&&`／`assert` 強制，不靠人眼看結果。

**已整合才算完成**：accepted 的改動要在目標 base 上看得到（`git log <base-start>..<base-now>` 有它）。併不回去時不得暗示完成——status board 列出每片所在的 branch 與 HEAD、確切 blocker、已跑的驗證與缺口、下一步要跑的指令，交給使用者決定。

最後回報 status board 終版（`references/templates.md`）：拆了什麼、各片狀態、整合證據、量測（elapsed、等待驗收時間、重工次數、可取得時的 tokens、整合或驗收發現的缺陷）。**沒有序列 baseline 不宣稱加速。**

## §8 失敗處理與 re-plan

```text
plan → execute → new information → re-plan（回 §3）→ execute
```

| 情境 | 處理 |
|---|---|
| worker 卡住／回報 blocked | 缺權限或外部依賴 → 該片退出本批，其餘繼續；缺脈絡 → 補 brief 一次，仍卡就換 fresh context 重做 |
| worker 停滯（還在跑，但落地位置的 `git status --short`／`diff --stat` 兩次 read-back 無變化，兩次相隔至少 10 分鐘或該片預估工時的一半，取小者） | 進度以 git 可見改動為準，不以 log 或輸出活動為準；stop 該 worker，補脈絡一次或換 fresh context |
| agent failure（崩潰、逾時、回報不成形） | 以 read-back 判斷落地位置的實際狀態；有可用進度就從該 HEAD 續派，否則重派；不採信中斷前的自述 |
| 逾時或 stop 之後要重派 | timeout 只是記帳：除非 adapter 的 stop 已確認 process 結束，視為它仍可能在寫。**同一落地位置／ownership 不得出現第二個寫入者**——確認不了就換新 worktree 重派，舊位置的晚到輸出一律忽略 |
| 已 merge 的片事後發現壞 | revert 該片（§6），其餘片不動；依賴它的下游片證據失效重驗 |
| 測試失敗 | 屬該片 → 退回 worker 修（重試上限兩輪，依平台 dispatch：Claude `<REPO>/rules/10-dispatch.md` §4、Codex `<REPO>/codex/rules/10-dispatch-codex.md` §5）；屬 base 或其他片 → 回 §3 判斷依賴是否變了 |
| 依賴改變（上游片改了簽名） | 下游片凍結，重發 brief；已通過的下游證據失效 |
| overlapping changes（實際 diff 越界或兩片改同區） | 兩片都停；判斷是 brief 錯還是 worker 越界；前者重切、後者退回 |
| merge conflict | 純文字依 adapter；語意衝突依 §6 第 6 步；同一衝突兩輪未解就重切 |
| worker 發現 decomposition 不合理 | 視為新資訊，回 §3 重切；已通過的片保留證據，只重驗受影響範圍 |

**re-plan 規則**：切片清單、ownership 或比較準則有變就重過 checkpoint 2；ownership 與 brief 未變、且已綁定 SHA 的片保留證據；brief 被改的片證據作廢；foundation 或 base 變動＝全批依 §6 第 7 步重驗。re-plan 只重驗受影響的片，不因 re-plan 本身讓其他證據失效。同一件事的重試上限沿用平台 dispatch（Claude `<REPO>/rules/10-dispatch.md` §4、Codex `<REPO>/codex/rules/10-dispatch-codex.md` §5），兩輪後換方法或問人。

## §9 Human-in-the-loop 與 execution adapter

**使用者要看得懂的節點**：為什麼拆（§2）、拆成哪些片（§3）、哪些在跑／blocked／完成（§4–§5，用 status board）、哪些成果準備整合（§6 第 1 步）、整合結果與量測（§7）。使用者不必處理 terminal、worktree、process 的細節，那是 adapter 的事。

**Adapter 契約**：一份 adapter 只回答五件事——
- **launch**：用什麼指令或呼叫啟動一個 worker、brief 怎麼餵進去；
- **follow-up**：怎麼把追加指示送給同一個 worker，或帶原 report／finding／diff 重派；
- **query status**：怎麼看它還在不在跑。git read-back 永遠是真相，容器的指示燈只是線索；
- **collect**：report 從哪裡拿（回傳值或落檔路徑）；
- **stop**：怎麼終止它、怎麼確認真的停了。確認不了就依 §8 當作仍可能在寫。

外加 workspace 建法（誰建 worktree、路徑與 branch 命名）與本平台 worker／verifier 的**角色名稱與 model 對應表**（名稱映射，不是 policy）。**不能**做 task decomposition、merge strategy、integration policy、授權判斷，也不能把「同一 session 的 subagent」「一個 terminal window」「一個 workspace」偷換成 task 的定義。adapter 內的機制事實（路徑、branch 命名、旗標）以各自檔案為 canonical；harness 實測數據集中在 `<REPO>/docs/harness-facts.md`。沒有 controller 的人手多開 session 走 `references/cli.md`「沒有 controller」一節，仍受一批 3 片與 §6 integration tree 的約束，不得把「不同 session 各自完成」當成已整合。

## §10 邊界

不做：跳過重疊矩陣或 ownership 分析；滾動補位；每次 merge 通知所有 worker rebase；把切分拆成另一個 skill；讓 worker 取得 tracker／push／merge 的隱含授權；把 git 無 conflict 當語意安全；Pattern B 合併多個方案；為了用某個 workspace 工具而改變上述任何一步；在 worktree 之間用複製檔案代替 git 合併。也不用其他 skill 內建、沒有整合步驟的多輪 review 流程取代 §5–§7——既有 fresh verifier 合約與 `<REPO>/rules/20-judgment.md` §2「停止端」已承接其驗收目的。

**刻意不做（屬 framework 層，不進本 skill）**：持久化的 task state machine 或 event log、背景 daemon 監督 worker、自動 retry／escalation 引擎、dashboard、跨 run 的 metrics 自我調整、runtime／capability registry、獨立 arbiter agent 常設角色。這些各有價值，但需要一個能保證原子寫入與排程的 runtime；用 markdown 手刻只會得到沒人維護的帳。狀態就是 git（SHA、branch、worktree）加 status board 與 integration record。adapter 特有的機制事實只存在各自 reference，不可跨 adapter 套用；commit／rebase 權限的來源永遠是 worker 合約，不是 adapter。
