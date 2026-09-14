---
name: parallel-dispatch
description: 準備讓 ≥2 個各需寫入的切片平行開發與驗收時使用；spec 或 grilling 結論尚未切分、要先判斷能不能切時也用。觸發句：「平行做」「同時派」「這幾個 issue 一起處理」「切成幾個 task 同時開發」「能不能切」，及英文 "in parallel"、"split this into tasks"。已有切好的 tracker 項目要直接平行派工與合併驗收時同樣觸發。
allowed-tools: Bash(git:*), Bash(gh:*), Read, Grep, Glob
---

# Parallel Dispatch

同時派多個 agent 開發與驗收的流程。`<REPO>` 依全域 `CLAUDE.md`／`AGENTS.md` 的 bootstrap 解出；本檔承接 Claude `<REPO>/rules/10-dispatch.md` 與 Codex `<REPO>/codex/rules/10-dispatch-codex.md`。先依 runtime 讀平台契約：Claude Code 讀 [references/claude.md](references/claude.md)，Codex 讀 [references/codex.md](references/codex.md)。本檔是切分、批次與整合證據的唯一共通核心；platform reference 只補 worktree、角色與權限差異。

## §0 入口、切分與重疊矩陣

- **入口 A**：tracker 已有切好的項目 → 跳過切分，仍逐片寫目標、獨立驗收條件、依賴、預估路徑與下列矩陣。tracker 的數字與事實以現查為準；與使用者提供素材不一致時在 plan 並列，不靜默採用。
- **入口 B**：grilling／spec 尚未切 → 先切分；只動一個模組且預估 ≤3 片由 controller 切，跨模組或依賴不明時依平台 dispatch 派 read-only 規劃角色，controller 核定。

改序列派一個實作者：任一切片不能有獨立驗收條件、只有一片無依賴、每片都會碰同一函式或相鄰區段（預估行範圍相距 10 行內），或整份 spec 單一實作者即可完成。相同檔但不同且不相鄰函式不算 git 重疊，仍受 §2 語意風險檢查。

每片必帶：目標、獨立驗收條件、依賴切片、預估檔案:函式或行範圍。每一工作者的寫入所有權另以**實際 worktree 的絕對路徑**加上檔案範圍表示；相對同路徑在不同 worktree 不是衝突。矩陣納入所有預估路徑，含測試與 fixture；同函式／相鄰區段的片合併或序列。矩陣量的是 git 合併性；§2 的檔案／目錄與跨目錄風險量的是行為互動，兩者不可互相取代。

有依賴的片序列做；只有互不依賴者同批。先凍介面再平行只在簽名可先固定、下游驗收只依賴簽名時成立；stub、tracker、分支與其他對外動作均由 controller 依當次授權處理。缺權限或外部依賴的單片不入批，其餘可繼續。

tracker 由專案規格宣告；未宣告預設 GitHub issue。ClickUp 時一個 task 是一批、sub task 是切片，GitHub 關聯寫 PR body，branch 沿用 repo 慣例不塞 ClickUp ID。controller 先把切片清單給使用者；明確核可一次只授權該清單的 tracker 建立，清單外項目與下一批要另取授權。阻擋片的 tracker comment 同樣是對外動作，要取得當次授權。

## §1 派工與切片驗收

一批上限 3 片，不滾動補位；下一批須等本批所有 PR merge 且整合驗收完成。platform reference 決定 worktree 建立者、worker 可否 commit／rebase、角色與 prompt 限制。無論平台，controller 必須提供每片的實際 worktree 絕對路徑、唯一寫入者、完整 approved plan 與驗收命令；worker 回報其路徑、HEAD 與機械驗證證據，controller read-back，不採信自述。暫時探針的 plan 必須寫還原指令、探針期間預期會紅的既有檢查，且不得為此順手修 fixture；長輸出落檔使用切片專屬前綴。

每片完成即可進行其獨立 fresh-context 驗收與必要 CI，不必等待同批其他片。切片級驗收要求驗收者使用 worker 未用過的探測形狀，並確認移除或固定該交付的輸出／訊息／綁定時有檢查失敗；修正後依對應平台的停止端處理。CI `skipping` 不算通過；endpoint／timeout 類錯誤僅在同一 SHA 重跑一次轉綠時可記為 flake，否則當真失敗。

改既有檢查、過濾或驗證規則的片，動手前依 `<REPO>/rules/20-judgment.md` §2「改既有檢查／過濾／驗證規則」凍結行為基線。controller 自己做 tamper／探針時，先以替換計數 `== 1` 或 `git diff --stat` 證明改動真的發生，再讀測試結果；CI 重跑次數與原因記在 PR。

## §2 暫存整合、驗收與合併

controller 在 merge 前以暫存 integration worktree／branch 組合各切片，跑完整測試；記錄 base SHA、每片 HEAD SHA、integration tree／commit 與結果。任何 base、切片 HEAD 或 integration 內容變動，都使受影響證據失效，必須重驗受影響範圍。

逐 PR merge 時，controller 先以當前 base 加該候選切片建立 integration gate 並跑受影響的完整檢查；若 base 有 auto deploy，這個中間狀態不可只由批次最終 tree 代替。不要拿全批最終 tree 比較第一片 merge，否則會把後續合法切片誤判為失效。每批固定保留最終 interaction 證據集合（integration tree、完整測試、風險判定）；它不是無條件再派 verifier。

下列任一語意風險才觸發一名 fresh verifier，只驗片與片的互動，不重驗已通過的切片條件：merge conflict、同檔或同目錄、跨目錄 API／schema、共用狀態、build 產物、CI job 順序或產物依賴。角色風險分流依 platform reference；驗收者在 integration tree／branch 的乾淨環境執行。無上述風險時，最終 interaction 證據只需 integration tree 的完整測試，不另派 verifier。

純文字 conflict 依平台契約處理；git 可自動合但互踩的語意 conflict 由 controller 判斷，判不出才問使用者，不以「無 conflict」跳過上述風險判定。驗收 prompt 的測試數或新增條數由 controller 現查（如 `git grep -c`），不抄切片自報；merge 順序是通過當前 base gate 的完成順序，不強求切分時順序。

確認後才由 controller 依 session 授權 merge／push；本 skill 不授權任何對外或不可逆動作。每次合併後 controller 比對實際 merge 結果的 tree 與該次候選 integration tree，記錄 merge SHA 並確認 required CI；不一致時先查明差異並重驗，停止下一次 merge。

清理前逐一確認 worktree 乾淨且沒有仍在使用它的 agent，重新取得 `<target-base>` SHA，並以 `&&`／`assert` 強制確認它等於最近完成整批交付驗收且通過 merge readback 所記錄的 base SHA，且目前切片 HEAD 等於該整合記錄的 slice HEAD；這兩項是必要 AND 條件。base 或 slice HEAD 任一變動，就先對目前 base 重新核對本批全部交付 diff 與必要驗收條件，取得綁定新 SHA 的新證據後才可清理；被 revert 或缺失的交付保持未完成並保留 worktree，除非使用者明確撤銷交付並依新核定 scope 處理。一般 merge 的 `git merge-base --is-ancestor <slice-head> <target-base>`、squash／rebase 的 PR `MERGED` 狀態與合併時 head 只證明曾合併、作為來源證據，不能取代目前內容核對；核對要包含完整交付 diff（含新增、刪除與更名），不得以整棵 base／slice tree 相等為必要條件，因為 base 還含其他切片。只印出結果不能阻擋下一步；各平台的清理指令在 reference，刪除非自己建立的資源仍需明確授權。

## §3 人手多開 session

沒有 controller 時，使用者應先列出各 worktree 絕對路徑與寫入範圍，開工前查 `git worktree list`，仍以一批 3 片與 §2 的 integration tree／完整測試為界；不得把「不同 session」當成已完成整合驗收。

## §4 邊界與量測

不做：跳過重疊矩陣、既有 issue 的事前檔案所有權分析、滾動補位、每次 merge 通知所有 worker rebase、把切分拆成另一個 skill、讓 worker 取得 tracker／push／merge 的隱含授權，或把 git 無 conflict 當語意安全。也不套用沒有整合步驟、明文禁止平行的 `subagent-driven-development` 雙判流程；既有 fresh verifier 合約與 `<REPO>/rules/20-judgment.md` §2「停止端」已承接其驗收目的。platform 特有隔離例外只存在各自 reference，不可跨平台套用。

每批可記 elapsed、等待驗收時間、重工次數、可取得時的 tokens、與整合或驗收發現的缺陷；沒有序列 baseline 不宣稱加速。
