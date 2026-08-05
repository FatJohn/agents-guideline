---
name: debug-environment-first
description: 除錯、追 bug、或量測結果看起來不對時使用。遇到 HTTP 錯誤、port 相關異常、指令輸出與預期不符、測試結果可疑、或準備提出「程式碼有 bug」的假設之前先讀。內含環境事實檢查清單，以及「量測方法要先自證」的具體陷阱（curl 未跟隨 302、grep -c 數行不數元素、破壞性檢驗靜默 no-op）。原本是 rules/20-judgment.md §6，2026-08-05 搬出常駐區。
---

# 除錯前先驗證環境（訊號常在 shell，不在程式）

> 這一節原本常駐在 `rules/20-judgment.md` §6。它只在除錯時用得到，不是每次開工都需要，故依 `maintain-guideline` §5 搬進 `skills/`（2026-08-05）。判準本身沒有改動。

**判準**：遇到 HTTP 錯誤、port 相關異常、或指令輸出與預期不符時，在提出任何「程式碼有 bug」的假設之前，先花 30 秒驗證環境事實並回報：

- `pwd` 與目標 repo 是否一致（多 clone／多 worktree 環境特別容易站錯目錄）。
- 目標 port 被誰佔用（`lsof -i :<port>`）；跑著的 server 是不是本 repo、本分支起的（看啟動時間或 build 產物）。
- `git status --short && git log --oneline -3` 用新指令重新確認分支與 merge 狀態——不從舊的 scrollback 推斷。
- 輸出像亂碼或被截斷時，先懷疑 shell quoting（zsh 會展開 `===`、吃掉 backtick），多行或含特殊字元的內容改用 quoted heredoc（`<<'EOF'`）重跑一次，再解讀結果。
- **量測方法要先自證，再拿它的結果下結論**——「壞了」與「我量錯了」長得一樣：
  - HTTP 檢查一律帶 `-L`，並看 `%{http_code}` ＋ `size_download`（不跟隨 302 會得到 `000`／0 bytes）。
  - 數 XML/JSON 元素用 `grep -o … | wc -l`，不要用 `grep -c`（它數的是**行**，單行文件恆為 1）。
  - **破壞性檢驗（竄改後確認測試會紅）必須先證明自己真的改到了東西**：`assert 搜尋字串 in 內容`，或改完 read-back diff。
    引號層一多，shell 與目標檔案對 backslash 的認知就會錯開，replace 靜默 no-op 時**輸出完全沒有異狀**，
    於是竄改沒發生、測試照樣綠，被讀成「守衛有效」——這是本節前一條的觸發條件（亂碼／截斷）涵蓋不到的失敗模式。

✅ **正例**：dev server 一直回 400/503 → 先 `lsof -i :8787`，發現是另一個 clone 殘留的 mock-server 佔著 port，殺掉即復原，程式碼一行不用改。
❌ **反例**：反覆修改 API 呼叫端程式碼想解 503，兩小時後才發現打到的根本不是自己起的 server。

## Windows 對照

`lsof` 在 Windows 沒有；改用 `Get-NetTCPConnection -LocalPort <port> | Select-Object OwningProcess` 再 `Get-Process -Id`。shell quoting 的坑同樣存在，只是主角換成 PowerShell 的 backtick 逸出與 `@'...'@` here-string（見 `rules/05-hosts.md`）。
