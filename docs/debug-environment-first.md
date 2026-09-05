> 2026-09-02 從 `skills/debug-environment-first/SKILL.md` 降為文件：近 45 天以 Skill 工具叫用 1 次、直接 Read 約 50 次，它實際上被當參考文件用，skill 身分只多付每 session 的 description 注入。內容原文未改寫；下文提到「本 skill」「搬進 skills/」處為當時歷史。
> 何時讀：除錯或量測結果看起來不對時；報出任何量測數字或訂任何門檻之前；改完帶內嵌程式碼的設定檔之後（GitHub Actions 的 `run:`、Dockerfile、husky hook、YAML 裡的 jq）。

# 除錯前先驗證環境（訊號常在 shell，不在程式）

> `<REPO>/rules/20-judgment.md` §5「除錯前先驗證環境」只留判準與指向；細節在這裡，只在除錯時才需要讀。

**判準**：遇到 HTTP 錯誤、port 相關異常、或指令輸出與預期不符時，在提出任何「程式碼有 bug」的假設之前，先花 30 秒驗證環境事實並回報：

- `pwd` 與目標 repo 是否一致（多 clone／多 worktree 環境特別容易站錯目錄）。**但別靠 `cd` 修**
  ——見下方「指令自己綁定目標」，那是 `<REPO>/rules/20-judgment.md` §2 同名判準的細節 canonical。
- 目標 port 被誰佔用（`lsof -i :<port>`）；跑著的 server 是不是本 repo、本分支起的（看啟動時間或 build 產物）。
- `git status --short && git log --oneline -3` 用新指令重新確認分支與 merge 狀態——不從舊的 scrollback 推斷。
- **per-file lint hook 會在多步編輯的中間態報假 error**：有 PostToolUse per-file lint hook 時，把「加 import」與「加使用處」拆成兩次 Edit，中間那次必被判 `unused-imports`。兩者併在同一次 Edit（或先改使用處再加 import）；真假存疑一律補跑一次完整 lint 確認，不要照著假 error 改程式。
- 輸出像亂碼或被截斷時，先懷疑 shell quoting（zsh 會展開 `===`、吃掉 backtick），多行或含特殊字元的內容改用 quoted heredoc（`<<'EOF'`）重跑一次，再解讀結果。
- **量測方法要先自證，再拿它的結果下結論**——「壞了」與「我量錯了」長得一樣。
  這是 `<REPO>/rules/20-judgment.md` §2「補充判準（把可證偽宣稱寫下來之前）」的細節 canonical：
  常駐區只留判準，**新增的陷阱一律寫進這裡**，不要在兩邊各記一份。
  兩個場合都會踩，而**報數字時比除錯時貴**——除錯時錯的量測只是多繞一圈，報數字時錯的量測
  會被寫進 PR、判準與告警門檻，之後每個人都照著那個數字做決定。

  **除錯時：**
  - HTTP 檢查一律帶 `-L`，並看 `%{http_code}` ＋ `size_download`（不跟隨 302 會得到 `000`／0 bytes）。
  - 數 XML/JSON 元素用 `grep -o … | wc -l`，不要用 `grep -c`（它數的是**行**，單行文件恆為 1）。
  - **破壞性檢驗（竄改後確認測試會紅）必須先證明自己真的改到了東西**：`assert 搜尋字串 in 內容`，或改完 read-back diff。
    引號層一多，shell 與目標檔案對 backslash 的認知就會錯開，replace 靜默 no-op 時**輸出完全沒有異狀**，
    於是竄改沒發生、測試照樣綠，被讀成「守衛有效」——這是本節前一條的觸發條件（亂碼／截斷）涵蓋不到的失敗模式。

  **報出任何數字或訂任何門檻之前**（下面這些都在 2026-08-23 踩過；後續踩到的直接加進來，
不要在這裡記條數——那個數字每次新增都會腐爛一次）：
  - **管線之後的 `$?` 是最後一個指令的離開碼**，不是你在意的那個：`cmd | head` 拿到的是 `head` 的（恆為 0）。
    要單獨跑那個指令，或用 `${PIPESTATUS[0]}`（bash）／`$pipestatus[1]`（zsh）。
  - **拿歷史資料列去推「現行設定會怎麼跑」**：那批列反映的是**寫入當時**的設定。要先查現行設定，
    設定換過的來源必須實打一次現行的那條路徑才算數。
  - **沿用別處量出來的門檻而不重量**：窗、cap、firing rate 都與該 pipeline 的節奏綁死。
    抄一個數字過來等於抄了它背後那次量測的前提。
  - **報「N 處」時要寫出搜尋鍵，並用形狀不同的第二把鍵交叉驗證**：同一條不變式通常有多種
    寫法，拿其中一種當網子會漏掉其餘——用 `localStorage.clear()` 掃殘留漏掉 `removeItem` 那份、
    用 `new QueryClient` 掃 provider 疊法漏掉只有 `MemoryRouter` 的 10 個檔。**取樣鍵選錯會讓
    「我掃過了」變成假的全稱句**。它與本清單「工具預設跳過某些目標」那條的差別：那條是工具
    騙你，這條是你自己選錯了網子。
  - **宣稱「這條路不可行／成本太高」之前先跑一次**：可行性估計與數字一樣要自證，而它通常更便宜——
    看到某個 lint 開關報 36 項就下結論「打開要配 20 幾條 ignore」，實際再加一個選項只剩 9 項，
    整條路是通的。**沒跑過的估計不該用來關掉一個選項。**
  - **`rg <欄位名>` 命中的是賦值點，不是值的來源**：讀到 `foo: bar` 那一行不等於讀懂了 `bar`
    怎麼來——**決定 `bar` 的那一行通常不含你搜的欄位名，所以不會出現在命中裡**（實例：
    `hasOtherOption: otherOption !== undefined` 命中，而同一個函式裡把它閘掉的
    `const otherOption = liftsOther ? … : undefined` 沒有）。要宣稱「這條路徑會產生 X」，
    跑那條路徑比往上讀更快也更準。
  - **拿「預設會跳過某些目標」的工具當成「我搜過了」的證據**：`rg` 預設不掃隱藏目錄，
    `.github/` 要另外抓（`rg --hidden` 或直接指定路徑）。這與
    `<REPO>/rules/20-judgment.md` §2「補充判準（重構／字串抽取／搬移／更正事實宣稱類任務）」
    是同一件事的兩半：那條說要搜，這條說你的搜可能是假陰性。

✅ **正例**：dev server 一直回 400/503 → 先 `lsof -i :8787`，發現是另一個 clone 殘留的 mock-server 佔著 port，殺掉即復原，程式碼一行不用改。
❌ **反例**：反覆修改 API 呼叫端程式碼想解 503，兩小時後才發現打到的根本不是自己起的 server。

## 指令自己綁定目標（cwd 會漂）

`<REPO>/rules/20-judgment.md` §2「補充判準（指令要自己綁定目標，不要靠 cwd）」的細節；判準留
在常駐區，**新踩到的工具寫進這裡**。

| 工具 | 綁定方式 | read-back |
|---|---|---|
| git | `git -C <絕對路徑> …` | `git -C <path> rev-parse --show-toplevel` |
| gh | `gh -R <owner/repo> …`（`pr`／`issue`／`run` 都吃） | 回應裡的 repo 欄位，或 `gh repo view <owner/repo> --json nameWithOwner`（**`repo view` 不吃 `-R`**，倉庫名走位置引數） |
| pnpm | `pnpm -C <路徑> …`（workspace 內另可 `--filter <pkg>`） | `pnpm -C <path> exec pwd` |
| rg／find | 路徑當引數傳，不要靠 cwd | 命中路徑本身 |

- **`cd X && a && b` 只保護到這一串**：換一行、換一個 Bash 呼叫、丟背景執行，都回到漂移狀態。
- **背景指令與跨 turn 的呼叫最容易中**：它們不繼承你上一個呼叫的 `cd`。
- **失敗長得像別的東西**：`gh` 在錯的 repo 下回「找不到 PR」，`exit 1` 會被讀成 CI 紅；
  `git status` 在錯的 repo 下回乾淨，會被讀成「改動已推上去」。兩者都不會有任何錯誤訊息說
  「你站錯地方了」。
- 對外或破壞性指令（push／merge／commit --amend／reset）做完一律 read-back 上表右欄那條，
  確認打到的是預期的 repo 與 commit，再回報。

## 內嵌程式碼要驗到被嵌的那一層

判準常駐在 `<REPO>/rules/20-judgment.md` §2「補充判準（驗證要驗到被嵌的那一層）」；這裡是
細節 canonical，**新增的語言與檢查方式一律寫進這裡**（2026-08-23 從常駐區搬入）。

設定檔內嵌別的語言時——GitHub Actions 的 `run:`、Dockerfile 的 `RUN`、husky hook、YAML 裡的
jq 或 SQL——上層格式 parse 通過**不算**驗過被嵌的那一層。

- **shell**（Actions `run:`、Dockerfile `RUN`、husky hook）：把每個區塊抽出來跑 `bash -n`。
  純語法檢查，不會執行任何指令，可以放心對正式檔案跑。
- **jq**：沒有純語法模式。`jq -n '<program>'` 會**執行**程式，而且缺 `--arg` 時以 exit 3 假紅——
  與真的語法錯同一個離開碼，分不出來。所以 jq 這層跑不了語法檢查，要明說未驗。
- 其他跑不了的：明說那一層未驗，不要用「上層 parse 過了」含混帶過。

失敗現場（2026-08-23）：YAML parse 過、測試全綠、CI 也綠，而那個 workflow 每天 cron 都是
bash syntax error，六條告警全滅。macroeconomics-report 的 workflows bash 區塊已加常設守衛，
缺口剩 Dockerfile／husky／jq 與其他 repo。

## Bash 覆蓋沒有保護（Write 工具有）

`cat > file`、`>` 重導向與整檔重寫都是覆蓋。Write 工具會擋「沒讀過就覆蓋」；**Bash 不會，
目標存在與否不會有任何提示**，寫之前先 `test -e`／`ls` 確認目標不存在。事後靠 `git status`
顯示 `M` 才發現，代表已經賭過一次。（harness 已內建「覆蓋或刪除前先看目標」，
常駐區不再重複，只剩這個 Bash 專屬缺口值得記。）

失敗現場：`cat > x.test.ts` 蓋掉既有 9 條測試，總數從 131 變 133 讓它看起來像「多了兩條」。

## Windows 對照

`lsof` 在 Windows 沒有；改用 `Get-NetTCPConnection -LocalPort <port> | Select-Object OwningProcess` 再 `Get-Process -Id`。shell quoting 的坑同樣存在，只是主角換成 PowerShell 的 backtick 逸出與 `@'...'@` here-string（見 `<REPO>/rules/05-hosts.md`）。
