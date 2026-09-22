# Git worktree：隔離、integration tree 與清理

配合 [../SKILL.md](../SKILL.md) 使用。worktree 是 implementation detail：它讓多個 worker 同時寫入而不互踩，**不是** orchestration model——task 不等於 worktree，worktree 不等於 terminal 或 workspace。誰建 worktree、用什麼指令 launch 由各 adapter 決定；本檔只放所有 adapter 共用的機制與證據條件。

## 何時需要

≥2 個 worker 要同時寫入同一 repo 時必須各用獨立 worktree（single-writer：同一 working tree 同一時間只有一個寫入者；只要共用 tree，即使檔案不重疊也只能序列）。單一 worker、或 worker 之間嚴格序列，可直接在主 working tree 做，不必開 worktree。read-only 角色（verifier、探索）與寫入者共用 tree 時，唯讀結論仍可信，但**跑測試／build 得到的數字被污染**——要嘛等寫入者停手，要嘛給它自己的 worktree。

## 所有權與路徑

brief 的 ownership 以 repo 相對路徑寫；每個 worker 的實際寫入範圍 ＝ **它的 worktree 絕對路徑 × 允許的相對路徑**。不同 worktree 的同名相對路徑不是衝突；同一 worktree 永遠單一寫入者。controller 記錄每片的絕對路徑、branch、base SHA。

`git worktree add` 建立後務必 `git worktree list` read-back 記錄絕對路徑與 branch；worktree 目錄若放在 repo 內（如 `<repo>/.claude/worktrees/`），先確認已被 `.gitignore` 忽略，否則全目錄掃描工具與 `git add -A` 會掃進去。

## Ownership 稽核（SKILL §6 第 2 步）

只信實際 diff，不信 report 的 Files changed：

以下 HEAD-based 指令的前置條件是每片交付都已 materialize 成 commit；worker 合約若禁止 commit，先依該平台 adapter 由 controller 在 worker 停止後 read-back、只 stage ownership 內路徑並建立 checkpoint commit。HEAD 仍等於 base 且 working tree 有修改時不得執行本稽核，也不得把空結果當成零改動。

```bash
# 每片實際改動檔（含新增／刪除／更名）
git -C <wt-A> diff --name-only <base>...HEAD | sort > <log-dir>/A.files
git -C <wt-B> diff --name-only <base>...HEAD | sort > <log-dir>/B.files
# 對照 brief 允許路徑：不在允許清單內的路徑 → 該片退回
# 兩兩交集：任一對非空 → 停下先解 ownership（SKILL §8「overlapping changes」）
comm -12 <log-dir>/A.files <log-dir>/B.files
# 唯讀 conflict 預檢（git ≥ 2.38）；不要用 checkout＋merge --no-commit 這種會動 working tree 的試合
git -C <repo> merge-tree --write-tree <base> <slice-branch>
```

worktree 之間**不要用複製檔案**搬改動——另一邊的 base 可能已前進，複製會覆蓋新 code；一律透過 commit 與 git 合併。

## Integration tree（SKILL §6 第 7–9 步）

merge 前用一個暫存 worktree／branch 從當前 base 開出，依序合入候選片：

```bash
git -C <repo> worktree add <integration-path> -b integration/<batch> <base-ref>
git -C <integration-path> merge --no-ff <slice-branch>     # 逐片；conflict 依 SKILL §6 第 6 步
git -C <integration-path> rev-parse HEAD^{tree}           # 記 tree SHA
<完整測試 / lint / typecheck / build>
```

記錄：base SHA、每片 HEAD、integration tree SHA、測試指令與結果。逐 PR gate 是「當前 base ＋ 該候選片」的另一棵 tree，不是全批最終 tree。merge 後比對：`git -C <repo> rev-parse <merge-sha>^{tree}` 應等於該次候選 gate 的 tree SHA；squash／rebase merge 時比對的是內容 diff（`git diff <gate-tree> <merge-sha>^{tree}` 為空），不是 commit 數。

## 清理的證據條件（全部 AND，缺一不清）

1. 該 worktree `git status --short` 為空，且沒有仍在使用它的 agent／session（adapter 的 stop 已確認結束 ＋ `ps`／session 清單現查）。逾時的 worker 不等於已停止；確認不了就不清、也不重用該 worktree（SKILL §8「逾時或 stop 之後要重派」）。
2. 重新取得 `<target-base>` 的 SHA，**等於**最近一次完成整批交付驗收且通過 merge read-back 所記錄的 base SHA。
3. 目前切片 HEAD **等於**該整合記錄的 slice HEAD。
4. 交付內容已在目前 base 上：核對**完整交付 diff**（含新增、刪除與更名）都出現在 base；`git merge-base --is-ancestor <slice-head> <target-base>`（一般 merge）或 PR `MERGED` 狀態（squash／rebase）只證明「曾合併」，是來源證據，不能取代內容核對；也不得以整棵 base／slice tree 相等為條件，因為 base 還含其他切片。

base 或 slice HEAD 任一變動，先對目前 base 重新核對本批全部交付 diff 與必要驗收條件，取得綁定新 SHA 的新證據後才可清理。被 revert 或缺失的交付保持未完成並保留 worktree，除非使用者明確撤銷交付。

條件以 `&&`／`test`／`assert` 串起來強制，只印出結果不能阻擋下一步：

```bash
BASE_NOW=$(git -C <repo> rev-parse <target-base>) && test "$BASE_NOW" = "<recorded-base>" \
&& test "$(git -C <wt> rev-parse HEAD)" = "<recorded-slice-head>" \
&& test -z "$(git -C <wt> status --short)" \
&& git -C <repo> worktree remove <wt> && git -C <repo> branch -D <branch>
```

Pattern B 落選方案的 worktree 不經第 2–4 條（它們本來就不會進 base），只需第 1 條加使用者已看過比較結果。刪除**非本次自建**的 worktree／branch 仍需明確授權（鐵律二）。

## Harness 事實

各 adapter 的自動 worktree 行為（路徑、branch 命名、自動刪除條件、成本樣本）canonical 在 `<REPO>/docs/harness-facts.md`，adapter 檔只引用不重抄。
