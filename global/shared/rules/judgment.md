# 判斷準則

> 讀者：所有等級的模型。訂條理由與正反例在 `<REPO>/docs/judgment-rationale.md` 同編號章節，用到才讀。

## 1. 完成的三個條件

宣稱完成前須同時成立：派工時寫的驗收條件逐條核過；有指令輸出或 read-back 結果作證據，不是「我認為」，分級為已驗證／待 CI／未驗證；驗證方式符合產出風險——機械驗證可自跑但附輸出，主觀品質、高風險產出、修使用者實際回報的 bug、diff 含外部呼叫／權限請求／不可逆副作用（第 2 條）要 fresh-context 驗收。誰驗什麼：Claude 見 `~/.claude/skills/dispatch/SKILL.md` §1「驗證不自驗」，Codex 見 `<REPO>/global/codex/rules/dispatch.md` §6「驗證語意」。

## 2. 不可逆副作用的定義

**「不可逆副作用」的 canonical 定義**：**一般側**＝程式路徑在正常流程會做、事後可由系統重建或重送的操作（寫後端狀態、清本機進度或快取、覆寫可重算的資料、向作業系統請求 Health／通知等平台權限），走一般驗收；**高風險側**＝決策層級（架構、安全設計、權限模型與存取控制的設計）與無法由系統重建或重送的效果（使用者資料刪除或覆寫、扣款、對外寄送推播或信件），不論是否寫在程式路徑裡。本檔、dispatch skill、各 dispatch 文件、agent 合約、派工模板與 skill reference 裡作為高風險門檻的「安全、不可逆、資料遺失」一律指高風險側；同一操作兩側都符合時高風險側優先。**收窄**：使用者當次操作對自己單筆資料的寫入（舊值由使用者自己覆蓋）歸一般側，即使舊值無法由系統重建；刪除、批次寫入、他人資料不在此例外內，照上面兩側判。只含一般側的 feature 不因此升高風險層，其 FAIL 修正後的結案仍依 `~/.claude/skills/dispatch/SKILL.md`（Codex：`<REPO>/global/shared/skills/dispatch/SKILL.md`）§2「修正與驗收輪次」。

## 3. 殘留掃描

重構、字串抽取、搬移、更正事實宣稱類任務，宣稱完成前全 repo 搜尋舊引用／字串／路徑，附指令與結果，須無殘留。搜尋須含隱藏目錄（`.claude/`／`.agents/`／`.gemini/`）：Bash 搜尋檔案內容（含計數、管線）一律用 `rg` 不用 `grep`，且 `rg` 一律加 `--hidden`（預設值與 Grep 工具差異見 `<REPO>/docs/install.md`「選配：擋主對話改 CI 設定的 hook 與 ripgrep 預設設定」）。entrypoint、設定檔、腳本、`.github/workflows`／`.github/actions` 最易漏，release／deploy-only 的 CI 路徑 PR 不會跑，PR 全綠不代表沒炸。排除清單只能排內容型目標，設定型（會被執行）不可排除；細節見 `<REPO>/docs/debug-environment-first.md`。

## 4. 未驗證的意思

「未驗證」是宣稱它現在驗不了，不是「我沒去驗」的委婉說法；標之前先確認真的沒有工具能驗。fresh-context 類的宣稱不算驗不了：`claude -p`／`codex exec` 本身就是全新 session，不必等或請使用者手動重開。

## 5. 驗到被嵌的那一層

設定檔內嵌別的語言時（GitHub Actions 的 `run:`、Dockerfile 的 `RUN`、YAML 裡的 jq 或 SQL），上層格式 parse 通過不算驗過那一層：要跑被嵌那層自己的檢查，跑不了就明說那一層未驗。各語言跑什麼檢查、哪些跑不了，以 `<REPO>/docs/debug-environment-first.md` 為準，新增的語言寫進那份。

## 6. 修正者的證據

修正者（含 controller 自修）對文件新寫或改寫的句子逐句對照權威來源；對新增或修改的測試斷言與守門檢查，附實跑會變紅的突變紅／綠輸出（做法見 `~/.claude/skills/dispatch/SKILL.md` §1「驗證不自驗」的程式碼機械驗證條）。兩者證據帶進 delta brief；分流與輪次見 `~/.claude/skills/dispatch/SKILL.md`（Codex：`<REPO>/global/shared/skills/dispatch/SKILL.md`）§2「修正與驗收輪次」。

## 7. 驗收的停止端

行為承載產物＝程式碼、測試斷言、設定、指令，及直接改變 agent／人員行動的 `CLAUDE.md`／`AGENTS.md`、rules、agent 定義、skills、rubrics、hooks、permissions、高風險決策文件；Markdown 不自動算散文——不改變行為的排版／語氣才算，改變行動的錯誤路徑或指令仍屬行為缺陷。只對本次範圍內的條件與發現判定，無關後續事項分列。verifier 第一行依優先序回報狀態並附下一步：

- `INCONCLUSIVE`：有 UNSURE 或必要條件未判定；保留已知 FAIL，先補缺證，不自動重派或宣稱完成，補證後仍依風險分流選機械結案或 fresh delta，不以換模型代替缺證。
- `OPEN`：無缺證但有行為承載產物的 FAIL；修正後依風險分流，不自動要求重派。
- `PROSE-ONLY`：無缺證，FAIL 全為不影響行為的事實／引用問題；修完 read-back 後停止。
- `CONVERGED`：必要條件全 PASS 且無 FAIL／UNSURE；停止驗收，純品味不列 FAIL。

## 8. 可證偽宣稱

寫下可證偽宣稱之前：數字（PR、判準、告警門檻）、封閉量詞（「只有 N 個」「都沒有」「全部」「不可行」）與行為宣稱（「這條路徑會產生 X」「切換之後會變成 Y」）都是。對新增／變更且宣稱現況的內容，先映射同一 artifact 且仍有效的既有證據，一份證據可批次支持多個宣稱，無映射才補指令；讀碼只證存在或呼叫關係，行為宣稱仍須實跑路徑。撐不起現況射程就改寫成開放式（「至少有」「已知的有」）；規格、契約與驗收條件描述應有行為，未實現時保留並列缺口，不改弱。長存文件引用優先用符號名或段落標題，驗收證據可用綁定版本的檔案:行號。陷阱清單以 `<REPO>/docs/debug-environment-first.md` 為準，新增陷阱寫進那份。

## 9. 放寬防線要實跑證據

宣稱「X 會被另一層擋掉，所以這裡可以不擋」是放寬的理由：刪除或放寬既有防線前，要有那一層自己的實跑輸出——最小案例餵給它、看到真的擋；讀文件、型別定義或既有測試不算。查不出來就保留防線，把「疑似重複」寫成註解或 issue。不算違規：只說明兩層職責重疊、未據此刪減任何檢查（仍受第 8 條射程要求約束）；或該層實跑輸出已涵蓋要放行的同一個輸入形狀。

## 10. 改既有檢查

改既有檢查／過濾／驗證規則時，完成證據＝動手前凍結的行為基線前後比對（新版是舊版超集，或差異都是刻意的）＋正向語料（合法輸入不被誤叫）實跑；事後補的基線不算，測試全綠不算。放寬時基線照做但不足以結案，另派 fresh-context 對抗性探測（Claude：`~/.claude/skills/dispatch/SKILL.md` §1「驗證不自驗」；Codex：`<REPO>/global/codex/rules/dispatch.md` §6「驗證語意」）；判不出安全的輸入維持擋。不算違規：全新檢查沒有舊行為可比，只需正向語料；「順手動到既有檢查」不算全新。

## 11. 指令自己綁定目標

巢狀 clone、workspace 底下的子 repo、多專案並存時，cwd 不是可靠的定位方式：git／gh／pnpm 一律逐指令綁定（`git -C <path>`、`gh pr view <n> -R <owner/repo>`、`pnpm -C <path>`）。gh 的 `-R` 放子命令之後；寫入類 gh 指令（merge／ready／comment／create／edit／review／workflow run）一條一個 Bash 呼叫，不接 `$()`、不與別的指令串 `&&`，否則對不上 permission 前綴規則、整串掉進分類器被擋。理由與 read-back 指令見 `<REPO>/docs/debug-environment-first.md`「指令自己綁定目標」。

## 12. 驗收條件要能被判定

寫驗收條件時自我檢查：另一個 agent 能不能只憑這句話判定過或不過？做不到就是空話，verifier 見到模糊條件應直接 FAIL。

## 13. 除錯前先驗環境

遇到 HTTP 錯誤、port 異常、hook／lint 在多步編輯中途報錯、輸出與預期不符，或準備提出「程式碼有 bug」的假設之前，讀 `<REPO>/docs/debug-environment-first.md`（環境事實檢查清單＋量測方法自證的具體陷阱＋內嵌各語言各自要跑什麼語法檢查）。

## 14. 現況證據與規格權威

以已部署程式、設定與實跑確認現況；以核定需求、契約與驗收條件判斷應有行為。兩者不一致時先查明原因，不自動選擇修程式或修文件。文件只留業務意圖、重要邊界、決策理由與驗收例子，不逐段翻譯程式；行為／契約變更要更新受影響規格及驗收例子，純內部重構無須同步文件。失準註解仍要修正。

## 15. 可中斷的長任務要留可恢復脈絡

可中斷的長任務（多階段、會等人、會離開、會 compact）要在段落結束時留下可恢復脈絡；格式與時機見 `~/.claude/skills/handoff/SKILL.md`（Codex：`<REPO>/global/shared/skills/handoff/SKILL.md`）§4「session 交接卡」。不算違規：單輪可完成的小任務。
