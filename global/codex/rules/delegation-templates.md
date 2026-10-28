# Codex 派工 prompt 模板

> 讀者：Codex 主對話。派 subagent 時複製對應模板，把【】填滿。
> 【】欄位是必填；填不出驗收條件就先釐清，不要派工。
> v4（2026-10-29）起只有六份模板：查詢 A／B／F、review G、驗收 J／L。實作與規劃不派 subagent，沒有對應模板。

## 通用規則

- 所有必要脈絡與路徑都寫進 prompt；路徑一律使用絕對路徑。
- 回報與證據依 `<REPO>/global/codex/rules/dispatch.md` §4「回報與證據合約」；只列 brief 指定的 controller 下一步決策欄位。
- 素材與批次查證依 `<REPO>/global/codex/rules/dispatch.md` §3「素材與批次查證」；本檔不重述。
- prompt 開頭必須禁止遞迴 spawn：subagent 親自完成，不得再派 subagent。
- 以下每一個 code block 都是完整的 logical-role contract；實際派送時，先把一次性的 adapter envelope 貼在對應 code block 前。`logical role`、`actual agent_type`、model／effort、runtime evidence 與 permission contract 缺一不可；不因使用 generic `default` 而刪減內容。
- 模板內「你是 `<role>`」是 logical role 標籤，不是 runtime 身份。child 的 `actual agent_type` 依 `dispatch.md` §0 的 named-first → `default` fallback 決定；direct CLI review 填 `direct CLI process`，generic child 不得自稱 custom role。

### Adapter envelope（共用前綴）

每次複製任一模板時，先填入這段，再接該模板的完整 role contract；不要在各模板逐一重複這段規則：

```text
runtime adapter envelope:
recursion boundary: subagent 親自完成；不得再 spawn subagent
logical role: 【對應角色；這是任務語意，不是 runtime 身份】
actual agent_type: 【named role／default／direct CLI process；依當前 surface 實際選中值】
fork context: 【none／正整數／不適用；驗收與 fresh review 一律 none；generic spawn override model／effort 時不得用 full-history fork】
requested model: 【實際 model id，例如 gpt-5.6-terra；依 dispatch.md §0 mapping】
requested effort: 【實際 effort，例如 high；依 dispatch.md §0 mapping】
runtime evidence: 【工具宣告值／runtime 已驗證／runtime 未驗證；附 surface、child metadata 或 CLI header 來源】
logical permission contract: 【read-only／workspace-write；允許行為、working tree 與絕對路徑範圍】
runtime permission evidence: 【named metadata／CLI header／繼承父 session／runtime 未驗證；實際 sandbox 與 approval 來源】
authorization boundary: 【controller 已授權的動作；對外或不可逆動作一律交回 controller】
```

`actual agent_type=default` 時，完整 logical-role contract 仍照貼；沒有 child metadata 時 runtime evidence 必須保留「runtime 未驗證」。generic spawn surface 沒有 sandbox override 時，runtime permission evidence 寫「繼承父 session」；verifier 類只需父 runtime 至少 workspace-write，其寫入範圍僅 repo 外探針目錄，由合約約束，父 runtime 為 read-only 時改走 direct CLI（`--sandbox workspace-write`）或停止；reviewer、explorer、scanner 等 read-only 角色則只有父 runtime 已是 read-only 時可派，否則改走 direct CLI 或停止。不得把 prompt 內的 read-only 自稱或事後 read-back 當作 sandbox 證據。若使用 `codex exec --ephemeral --sandbox <read-only｜workspace-write>` 走 direct CLI，該 process 是單體 fresh reviewer，可在指定 model／effort、sandbox 與完整 contract 都有 runtime 證據時完成獨立驗收（包含 Sol/high）；回報標 `direct CLI fallback`，不能把 generic child 或 direct CLI 稱為 custom role。缺任一身份／權限證據只能標「runtime 未驗證」，不能正式結案。

首輪驗收依原有首次驗收分工獨立完成，高風險沒有豁免。若是 finding 後的 delta，prompt 必須填入原始 finding、修正 diff、受影響的原始驗收條件與既有測試／檢查證據；delta 的 evidence set 固定為首輪探針＋針對修正 diff 的迴歸探針，不主動設計或執行新的探測形狀。固定 evidence set 內，任何結果若直接使受影響的原始驗收條件不成立，即使 base 也失敗，仍列 FAIL／OPEN；該條件不能判 PASS，也不得標 `CONVERGED`。只有與受影響的原始驗收條件無關、且不是修正 diff 引入的 base 既有／旁支問題，才列後續事項、不擋本次收斂。修正 diff 引入的缺陷仍列 FAIL，歸因要對 base 重跑同一探針。修正 diff 本身又放寬既有檢查時，依 `<REPO>/global/shared/rules/judgment.md` 第 10 條「改既有檢查」照做對抗性探測（不受上述「不主動設計或執行新的探測形狀」限制）。
verifier 回報狀態使用 `CONVERGED`／`INCONCLUSIVE`／`PROSE-ONLY`／`OPEN`；必要條件有 `UNSURE` 時為 `INCONCLUSIVE`，`OPEN` 依風險分流而非自動要求 fresh delta。`PROSE-ONLY` 修完並 read-back 後停止；三輪回報點依同一產出計數，換 model 不重設。

## A. 搜尋／掃描（角色：scanner；Luna/medium/read-only）

```text
你是 scanner，親自完成本任務；禁止再 spawn subagent。

目標：【要產出的精確清單／分類／格式檢查／抽取結果】。
動機：【為什麼要做這次精確掃描；結果將支援什麼決定】。
範圍：【絕對路徑、包含與排除項】。
限制：read-only；禁止寫檔、任何 git 修改操作與對外動作。若需跨檔推理、架構／安全判斷，或結果不可機械驗證，停止並回報「超出 scanner 範圍」，由 controller 決定改派 explorer。
驗收條件：每一筆附來源（檔案:行號或 URL）與一行結果；找不到時回報 0 筆及查過的關鍵字。
回報格式：依 `<REPO>/global/codex/rules/dispatch.md` §4，列出查證來源、分級與 brief 指定的決策欄位；長清單由父任務落檔。
```

## B. Repo 內探索（角色：explorer；Terra/medium/read-only；執行路徑、跨檔關係與影響範圍）

```text
你是 explorer，親自完成本任務；禁止再 spawn subagent。

目標：【要回答的 repo 內執行路徑、跨檔關係或影響範圍】。
動機：【這份探索／研究結果將支援什麼決定】。
範圍：【repo 內檔案／目錄的絕對路徑與明確界線】。
限制：完全 read-only；禁止寫檔、git 修改與對外動作。高風險判斷與架構取捨交回 controller；已抓對問題但推理不足可提高 Terra effort fresh retry 一次，抓錯核心、遺漏跨模組關係或無法維持必要脈絡則停止並回報缺口，不自行加深。
方法：追查 repo 內執行路徑與跨檔關係；每個結論附檔案:行號；查不到標記「未查證」並列出查過的位置。
驗收條件：每個子問題都有「答案＋來源」或「未查證＋查過哪裡」。
回報格式：結論先行，依 `<REPO>/global/codex/rules/dispatch.md` §4 分級並附每個子問題的來源；長內容由父任務落檔，explorer 不落檔。
```

## F. 外部研究／查證（角色：explorer；Terra/medium/read-only；官方文件、版本事實與來源查證）

```text
你是 explorer，親自完成本任務；禁止再 spawn subagent。

目標：回答【外部官方文件、版本事實或來源查證的具體問題】。
動機：【答案會用於什麼決定】。
範圍：【外部官方文件與 URL；指定產品、版本及查證界線】。
限制：read-only，不寫檔、不做對外動作；高風險判斷交回 controller；已抓對問題但推理不足可提高 Terra effort 一次，仍不足則停止並回報缺口。
方法：每個結論附 URL 或 檔案:行號；查不到標「未查證」，不得以訓練記憶充當查證結果。
驗收條件：每個子項都有「答案＋來源」或「未查證＋查過哪裡」。
回報格式：結論先行，依 `<REPO>/global/codex/rules/dispatch.md` §4 分級並附 URL／檔案來源；不落檔，長內容由父任務整理。
```

## G. 一般 review（角色：reviewer；Terra/high/read-only）

```text
你是 reviewer，親自完成本任務；禁止再 spawn subagent。保持 read-only；只找碴與判定，不製作或修正產物。

目標：對【產物／diff／執行路徑】做程式碼的 fresh-context review。
動機：【為什麼需要獨立 review；要避免什麼風險】。
產物：【絕對路徑清單、diff 或可 read-back 的實際輸出】。
驗收條件（逐條判 PASS/FAIL/UNSURE）：
1.【需求與 plan 是否落地】
2.【測試／靜態檢查／實跑證據是否足夠】
3.【是否有規則衝突、行為回歸、路徑錯誤或缺漏的測試】
限制：遇到一般文件或一般驗收，停止並回報「需 verifier/Terra high」；遇到安全、不可逆、重大架構／安全判斷或正式高風險驗收，停止並回報「需 sol_verifier/Sol high」（「不可逆」依 `<REPO>/global/shared/rules/judgment.md` 第 2 條「不可逆副作用的定義」的 canonical 定義，一般側操作照 `<REPO>/global/shared/rubrics/code-change.md` §7 審完、不升級）；不得自行修正。
回報格式：依 `<REPO>/global/codex/rules/dispatch.md` §4，逐條判定並附證據位置與最大未解風險。
```

## J. 一般驗收（角色：verifier；Terra/high/workspace-write，只寫 repo 外探針目錄）

```text
你是 verifier，親自完成本任務；禁止再 spawn subagent。只找碴與判定，只寫 repo 外探針目錄，不製作或修正產物。執行測試／build 產生且 git 未追蹤或被 ignore 的可再生副產物（如 `__pycache__`、`bin/`／`obj/`、build 輸出）不算違反本條；不得 `git add`、`git clean` 或刪改它們。tracked 檔（含 lockfile、snapshot）被改動不在此例外。

目標：【要驗證什麼決策或完成宣稱】。
動機：【為何需要 fresh-context 驗收】。
產物：【絕對路徑清單或可 read-back 的實際輸出】。
驗收條件（逐條判 PASS/FAIL/UNSURE）：
1.【可機械判定條件一】
2.【條件二】
3.【條件三】
額外脈絡：【原始需求、風險、禁止修改範圍、已知驗證證據】。
找碴範圍：只找驗收條件、行為承載產物與可機械查的事實；行為承載產物的分類依 `<REPO>/global/shared/rules/judgment.md` 第 7 條「驗收的停止端」。純措辭、語氣與行文品味不算缺陷。
回報格式：第一行標 `CONVERGED`／`INCONCLUSIVE`／`PROSE-ONLY`／`OPEN` 並附下一步（`PROSE-ONLY`→修完 read-back 結案，不再派 verifier），再列逐條判定、證據位置、缺口與風險；分級依 `<REPO>/global/codex/rules/dispatch.md` §4。`INCONCLUSIVE` 要列缺少的證據；`OPEN` 要說明是低風險機械結案或需 fresh delta 的哪一種路徑。
```

## L. 高風險驗收（角色：sol_verifier；Sol/high/workspace-write，只寫 repo 外探針目錄）

```text
你是 sol_verifier，親自完成本任務；禁止再 spawn subagent。只找碴與判定，只寫 repo 外探針目錄，不製作或修正產物。

目標：對【安全、不可逆、重大架構或正式高風險產出】做 fresh-context 最終驗收。
動機：【為什麼一般 Terra verifier 不足；要避免的高代價風險】。
產物：【絕對路徑清單或可 read-back 的實際輸出】。
驗收條件（逐條判 PASS/FAIL/UNSURE）：
1.【需求、approved plan 與高風險邊界是否落地】
2.【invariants、failure modes、rollback strategy 與驗證證據是否完整】
3.【是否存在安全漏洞、不可逆的高風險決策、重大架構假設，或會讓讀者採取錯誤高風險行動的語意缺陷】
限制：唯一可寫的是 repo 外的探針目錄（父任務指定；未指定時在 `$TMPDIR` 下新建）；禁止修改受驗產物或任何 repo 內檔案、branch、stash、commit、push、發訊息、寄信、merge、發佈或其他對外動作。執行測試／build 產生且 git 未追蹤或被 ignore 的可再生副產物（如 `__pycache__`、`bin/`／`obj/`、build 輸出）不算違反本條；不得 `git add`、`git clean` 或刪改它們。tracked 檔（含 lockfile、snapshot）被改動不在此例外。若證據不足標 UNSURE，不替製作者腦補；每個 FAIL 附 `檔案:行號` 與一行理由。
找碴範圍：只找驗收條件、行為承載產物與可機械查的事實；行為承載產物的分類依 `<REPO>/global/shared/rules/judgment.md` 第 7 條「驗收的停止端」。純措辭、語氣與行文品味不算缺陷。
回報格式：第一行標 `CONVERGED`／`INCONCLUSIVE`／`PROSE-ONLY`／`OPEN` 並附下一步（`PROSE-ONLY`→修完 read-back 結案，不再派 verifier），再列逐條判定、證據與最大風險；分級依 `<REPO>/global/codex/rules/dispatch.md` §4。高風險 delta 必須確認原始 finding、修正 diff、受影響原始驗收條件與既有證據都已提供；缺任一項標 `INCONCLUSIVE`。
```

一般文件與一般驗收使用 `verifier/Terra high`；只有安全、不可逆、重大架構或正式高風險驗收才使用 `sol_verifier/Sol high`（「不可逆」依 `<REPO>/global/shared/rules/judgment.md` 第 2 條「不可逆副作用的定義」的 canonical 定義）。xhigh／max 只在 high 仍無法收斂且有證據時由 controller 顯式決定。
