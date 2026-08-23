# 升降級路徑（Claude 端）

> 2026-08-23 從 `rules/10-dispatch.md` §4 整節搬出。理由：這是「門檻成立**之後**派給誰」的決策樹，
> 只在升級真的發生時才讀，而 `rules/` 是每個 session 全文載入的常駐區
> （`maintain-guideline` §5「只在特定情境才用得到的內容不該放 rules/」）。
> 升級**門檻**本身的 canonical 仍在 `../rules/20-judgment.md` §1；`../rules/10-dispatch.md` §4 已改為指向本檔。
> Codex 端的對應章節是 `../codex/rules/10-dispatch-codex.md` §5「升降級路徑」，未搬動。
>
> **內容原文未改寫**，唯一的改動是相對路徑：本檔在 `docs/`，原文的 `20-judgment.md`（2 處）
> 改寫為 `../rules/20-judgment.md`，否則從這裡解析不到。

升級**門檻**（幾次失敗、什麼算高風險）的 canonical 定義在 `../rules/20-judgment.md` §1；本節只講門檻成立後**派給誰**。

任何升級派工一律必附**對應門檻的證據**，不能只丟原題：失敗入口附完整失敗軌跡（改了什麼／跑了什麼指令／輸出關鍵行／為什麼判定失敗，每次嘗試各一段）；高風險入口附風險判定依據（發現了什麼、為何屬高風險）；「確認需要 Fable」入口附 recovery 的 root cause 報告與判定理由。缺對應證據時 agent 會直接回報「升級素材不足」。

- **實作側，門檻成立** → 派 fresh-context `recovery-worker`（opus／xhigh）。它先建立 root cause 再編輯；價值同時來自乾淨 context 與強制 root cause，所以即使失敗者已是 opus 也適用。
  - **例外可直升 `escalation-worker`（fable／xhigh）**：失敗者已是 opus／xhigh，且明顯是**能力天花板**——反覆撞同一面牆、看得出理解問題但解不動，而不是越修越糟、越疊 workaround。難以判定就走 recovery（便宜的那條）。
- **實作側，recovery-worker 也沒收斂**（再兩次失敗，或它自己判定 root cause 需要 Fable 能力）→ 升 `escalation-worker`（fable／xhigh）。Fable 與 Codex Sol 屬同一個最高風險角色層。
- **規劃側：Plan 或探索路徑（opus）無法建立可靠方案** → 先以 fresh-context Plan（opus）重述問題並附完整探索輸出重試一次；仍無法形成可靠方案才升 `escalation-planner`（fable／xhigh）。它唯讀出 plan，實作仍走上面的實作側路徑。
- **fable 回報 unsupported 或 unavailable** → 不得宣稱已使用 Fable；改用 fresh-context opus 或 `codex:codex-rescue`，並把 model mapping 標記為「未驗證」。
- **fable 仍卡住** → 改用 Codex Sol 作跨平台第二意見，或依 `../rules/20-judgment.md` §3 問使用者；不可只換措辭重試第三輪。
- **降級**：難題被 Opus／Fable 解出可重複且可機械驗證的 pattern 後，把 pattern 寫進 prompt，降回 sonnet 批次套用；不降到 haiku。
- **重試上限**：同一件事最多重試兩輪。兩輪後還不行，代表方向錯了，換方法或問人，不要換個措辭再試第三次。
