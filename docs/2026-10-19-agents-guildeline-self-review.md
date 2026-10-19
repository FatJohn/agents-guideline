## 全局
- agents 的角色我覺得可以留著，目前分工我沒有特別意見，但 agents 裡面寫的內容可以再細看是否合適
  - verifier : 很棒
- 同意 `global-policy-ownership-review-2026-10-19.md` 裡面說的應該只要有個最小面積，用 route 的概念導向各個地方，各個專案的規則為主
- git commit 的規則等等的應該直接寫成 skill 會更省
- 記憶的機制是否有更好的選擇？除了 skill 外，是否可以開一個專們的 private rpeo 來同步記憶
- main session 的 effort 我想調整為 medium
- 整體規則不需要用修補的方式思考，可以用吸收然後重新構思的角度去思考建立，是可以用一個 orphan branch 整理出一份新的
  - 是不是直接把 claude, codex 拆成兩個資料夾，雖然有些東西會是重複的，但應該用維護的 skill 說說哪些東西是可以直接用複製的，哪些就不要互相動
- 每個規則的標題不需要右邊多一個`（）`的區段補充
- 規則中不要保留有日期類型的 log 只需要保留最終事實，有 git 可以追溯
- 是不是引入 https://github.com/michael-denyer/pstack-claude 來做事情就好，有把 skill 細化
- `~/Downloads/Claude Desktop improve.jpeg` 現在 claude 官方的 claude desktop app 似乎有支援一樣的東西，還有一個 nested session 的概念，不確定 cli 能不能用，這個在 claude code cli 可以用嗎？或者說對我們用 orca 有用嗎？還是我直接用 claude desktop 會更單純？
  - 這個跟 dispatch.md 和 parallel-skill 有關係

## 規則
### CLAUDE.md
- 標題的 `(全域)` 多餘
- `語言` 區段多餘
- 目前的 `工作系統` 區段
  - 非條列式，似乎多餘的贅字多
- 應該會調整為最小的 route 所以`工作系統`區段應該要換掉
  - `情境` 應該變成某種規則轉導向不同的 skill or agent ?
- 鐵律有兩條似乎應該收在 verifier 中

### 00-environment.md
- 這個檔案感覺可以作廢，在沒有全域規則之前應該也可以滿好的運作
  - 使用者背景的東西感覺沒有意義


### 05-hosts.md
- 轉導向 `/hotsts/` 下的平台檔案，但那些路徑真的必要嗎？真的有意義的比較像 pythone 沒也別名那種，其他真的有關係的路徑可能應該寫在各個 repo 的 agents.md or claude.md 中就好
- 例如全域規則中提到的全域規則是怎麼套用到到電腦的方式
- 我覺得我們是不是應該拆分 2 層，第一層應該也是這個 repo 的規則，全域規則則是放到子資料夾中，例如： `/global/` 下面才是真的擺放要放在全域的東西，然後看一律都是用複製蓋掉的方式還是要用 symlink 就看怎麼做，突然覺得放在一層以這個 repo 來說，就 repo rule 和 global rule 打架
  - maintain-skill 的這個應該也是變成 repo skill not global skill

### 20-judgement.md
- 想到我們每一個步驟交給下一個的步驟，例如 agent, subagent 應該有個規範的格式，例如主題、目標、驗收條件等等，像交接也要有一個交接的格式，避免無謂的變化格式增加負擔
- 裡面太多不補充判准的方式描述，應該直接變成一調一條的規則
- 並且有些是針對特定語言的，例如出現 `main.tsx` 這種，我覺得這個應該不是全域規則該有的寫法？


### 50-lessons
- 如果要記錄 project 的真實名稱的話，也許可以考慮把這個東西拆出去另外一個 repo
- 並且這個東西也許可以不用擺在全域規則裡面，但可以擺在這個 repo 中作為改善依據，意思就是不需要用 symlink or 複製到全域中

### 10-dispatch.md
- 在 claude 這邊的派工可以考慮由 haiku 起跳，實驗過後可以看 verifier 判斷迴圈的品質，因為 haiku 也出 5.5 了
- 驗證不自厭的地方好像跟前面其他的規則重複
- 基本上規則都還滿認同，只是擺放的角色的地方，也許是未來 route 的核心規則

### 20-judgment-controller.md
- 這個感覺應該變成某個 agent 的內容而不是規則

## rubrics
這些感覺應該放在 verifier agent 下面的子參考文件，因為主要是用來判斷品質

## agents
- codex 下面的 agetns 的規則寫的比較簡潔欸！

### verifier
- 可以利用官方的 code-review skill 為優先作為 verifier 的模型，或者各自的 code review skill (codex, claude) 優先，但給予的只是可以用這邊的
- claude 的 efferot 是不是改成 medium 就好？
- 一樣驗收的結果是不是可以定義一個固定的格式？

### worker
- 如果是實做程式碼可以沿用既有的 model 
- 不過查一些東西根據上面說的 claude desktop 裡面的，可以用 haiku 

## skills
### parallel-dispatch
- 依照上面的一些原則判斷之後，看看這個 skill 的適用姓，因為如果要用 ORca 來開發，應該還是有幫助，但如果用 claude desktop 來開發可能就用不到，換個角度想如果針對的是跨不同的 ai agent 的話，這個應該野獸有幫助的（例如 codex, agy ）

### maintain-guideline
- 這個應該放在全域規則的 repo only 的 skill 而不是全域的

### usage-review
- 這個應該也是放在 repo 中的 skill 非全域

### writing-principles
- 這個是可以放在全域
- 裡面的範例 `acme-login-web` 要換掉名稱


### session-handoff
- 竟然只有在 codex 下？
- 這個是不是可以使用 ~/Projects/FatJohn/document/public-notes/conference/hwdc-2026-10-14 的 02-dynamic-focus.md 的交接卡的概念，上面我也有提到是不是每個步驟都可以訂格式往後交付