# 給 Claude：多 session 工作流與成本調整 brief
> 本檔是歷史紀錄，引用的是重構前的檔案路徑；對照見 `docs/repo-layout.md`。

日期：2026-10-12。這份文件是調整建議與執行 brief，並非已生效的制度，也不證明調整後會省 token。

## 目標與範圍

請對照本 repo 現況，調整「盤點 session → 獨立 issue session → 有界執行與獨立驗收 → 人工 merge → result.md 回收」工作流，降低重複探索、context 重讀、重複審查與無效修正的成本，保留品質與授權邊界。

優先補實際缺口、修正衝突與落實既有機制；已存在且足以約束行為的規則，以引用與執行方式改善處理。每項改動須指出它解決的具體重複工作，不因角色名稱或流程完整感而新增階段。

本 brief 的交付範圍是 repo 內可 review 的制度／skill／模板調整，以及驗證證據。外部工具安裝、全域設定與 plugin 啟停、push、PR、merge、發佈及對外訊息，另依當前 session 授權處理；本 brief 不授權這些動作。若修改既有判準需要額外核定，依 maintain-guideline 列出具體候選 diff 與理由，遵守其適用權限流程。

## 開工前讀取

先確認 hostname、repo 路徑、branch／HEAD 與 dirty state，保留使用者既有變更。依當前 AGENTS.md 的路由載入必要文件；修改工作制度前讀 maintain-guideline skill，撰寫 agent 文件時讀 writing-for-agents skill。

核心現況來源（相對於本 repo）：

- `skills/parallel-dispatch/SKILL.md`：獨立 issue 與相依切片分流、ownership、批次與整合。
- `skills/parallel-dispatch/references/cli.md`：盤點 session、Orca issue session、result.md 與授權。
- `skills/parallel-dispatch/references/templates.md`：現有 brief／report 模板。
- `rules/10-dispatch.md`、`codex/rules/10-dispatch-codex.md`：兩平台派工與驗收路由。
- `rules/20-judgment.md`：修正輪、delta 驗收與停止端。
- `docs/reviews/issue-session-trial-2026-10.md`：既有量測、限制與未證實節省的結論。
- `rubrics/document-quality.md`：文件驗收。

上述文件有分工，先找每個概念的 canonical 位置，再決定修改哪裡。Claude／Codex 同步共通語意，平台執行方式、權限與 runtime 證據仍依各自合約。

## 候選調整（依優先序）

### 1. 派工依需要觸發

一般有界 issue 採現有 controller → worker → 獨立驗收路線。探索廣度、規格不明、跨 subsystem、架構或安全風險需要時，才增加 explorer、planner、reviewer 或較高模型層級。

檢查規則與模板是否實際強迫每題都走 explorer＋planner＋worker＋reviewer＋verifier；若有，改成明確觸發條件。保留既有高風險 reviewer／verifier 分工、fresh-context 要求與 single-writer。issue session 可派有界 agent；收到有界任務的執行者親自完成，避免遞迴轉包。

### 2. 主 session 保持盤點與跨 issue 決策

主 session 負責優先序、依賴與共用觸點、brief、交付回收及跨 issue 決策。issue session 負責自己的 source 探索、實作、修正、驗收、CI 與交付準備。

主 session 讀 result.md 與必要外部事實，不預設重新跑各 issue 的完整探索或審查。證據不足、base 改變、共用觸點互踩或驗收不一致時，將問題送回原 issue owner；涉及跨 issue 的整合仍做必要 integration gate。摘要不能取代 git／PR／CI read-back。

result.md 使用固定且精簡的決策欄位：issue／status；worktree／branch／base SHA／candidate SHA；dirty state；changed-file ownership；驗證與 verifier 證據位置／結論／修正輪數；PR／CI；跨 issue 風險；待授權動作。merge 後補 merged commit 與交付狀態。詳細 log 留在原工作區，以路徑或連結引用。

### 3. 機械狀態由程式收集，例外由模型判斷

檢查現有 CLI 能否取得 process／terminal、worktree、branch／HEAD、PR、CI 與 merge 狀態。先使用既有工具；確認有重複手動工作才增加最小收集器，不預設導入新 orchestrator。

以 blocked、驗收失敗、CI 失敗、ownership 衝突、base 變更或待授權作為需介入的事件。正常等待避免讓主 session 反覆讀 terminal 全文。這些事件是候選設計，不代表目前已有可靠 hook。

若實作收集器：只讀取狀態與產出狀態資料，區分 working、blocked、awaiting verification、ready for authorization、merged、unknown；TUI idle 與 process exit 不直接等於完成。資料缺失或過時標 unknown／時間戳，避免推進完成狀態。另核對資料欄位、權限、錯誤處理與實際工具支援。

### 4. 修正輪遵守 delta 驗收

首輪獨立驗收依原需求與產物查證；修正輪帶原 finding、修正 diff、受影響原始驗收條件、既有證據與探針位置，重跑原探針及必要迴歸。

依既有停止與升級判準收斂。先檢查派工模板是否漏帶上述材料，或每輪重新開放無界找漏洞；保留既有對修改檢查／放寬條件的例外。此項不是降低品質門檻，也不新增任意固定輪數。

### 5. 常駐 context 與成本量測

先盤點實際載入的 rules、skill／plugin 描述、MCP tool definitions 與重複回報。按需內容放回適當 reference；共通約束保留 canonical 與精確路由。避免只依檔案字數宣稱 runtime context 已下降。

將候選精簡與實際載入證據分開。全域設定與 plugin 變更列為獨立候選，不混入本次文件修改，也不為省 token 移除安全或權限約束。

沿用既有 matched-trial 思路：相近 repo／scope／風險的成功交付，比較 input、cache creation、cache read、output，及模型、修正輪數、品質缺陷、等待與完成時間；納入盤點、issue session、subagent、驗收、整合與可取得的外部 advisor 成本。counter 缺失標 unknown；API 牌價等價、帳單與訂閱額度分開。一次試行只改一類主要變因，效果未量測前不承諾節省率。

## 外部借鏡與限制

- [Agent Orchestrator](https://github.com/OrchestratorInc/agent-orchestrator)：每 task 一個 agent／workspace／feedback loop，以 PR／CI／review 狀態呈現看板。可借鏡狀態收集，不照搬其 commit／PR 權限；README 是功能自述，不是效益量測。
- [Cursor 多 agent 實驗](https://cursor.com/blog/scaling-agents)：planner／worker／judge 分工；平等自行協調曾遇到鎖與責任問題，額外 integrator 也可能造成瓶頸。是大規模實驗經驗，不是本地最優架構的證明。
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams)：獨立 context 與任務協調；相依多、同檔及順序工作宜採較簡單路線，team 會增加 token。工具狀態與限制實作前重查。
- [Anthropic 多 agent 研究系統](https://www.anthropic.com/engineering/multi-agent-research-system)：明確委派邊界、依複雜度分配 effort、成果落檔後只回傳引用。其約 15× chat token 是研究系統觀察，不能套成 coding 倍率。
- [Cursor token efficiency](https://cursor.com/blog/improved-token-efficiency)：精簡常駐 instructions、按需載入 tool definitions、改善 cache reuse。其節省數字不能直接外推到本 repo。

## 交付與驗收

先列「已具備／實際缺口／候選修改／暫不修改」對照，再依權限流程完成已授權改動。一般文件做 fresh-context verifier；高風險改動依現行角色路由。修正者與驗收者分離。

驗收條件：

1. 每項改動有具體缺口與 canonical 位置；已存在的機制沒有再寫第二套。
2. 獨立 issue／相依切片、controller／執行者的邊界清楚；沒有增加無界遞迴派工。
3. 一般與高風險路由均可由文件判斷；獨立驗收、single-writer、授權與必要 integration gate 保留。
4. result.md 足以支援下一步決策；狀態來源可查，idle／摘要不冒充完成。
5. delta 驗收與既有停止判準一致，不改成每輪無界重驗或任意新輪數。
6. 引用路徑／章節、模板、平台差異與可執行片段實查；新增收集器時，驗證缺資料與失敗不會被判完成。
7. 文件改動、runtime 載入驗證、工具行為與成本效益分級回報；未量測部分明確保留未驗證。

最後回報：修改檔案與理由、驗收結論／證據、尚未驗證項目、下次試行方法、需使用者核定的具體動作。
