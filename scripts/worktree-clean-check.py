#!/usr/bin/env python3
"""判定盤點 session 能不能不問使用者就清掉一個 issue worktree（worktree-session SKILL §3「直接清」）。

規則是 fail-closed：任何檢查失敗、工具不在、輸出讀不懂、欄位不符，一律回 exit 1，由盤點 session 保留
worktree 並回報。全部檢查都會跑完，一次列出所有原因。exit 0 只代表「可以開始關 session」，不代表已清。

只讀：`git fetch` 只更新遠端 ref，其餘是 git／gh／lsof／ps 的查詢與 `stall-check.py --json`，不關 session、
不刪任何東西。

已知判不到的形狀（都是用 cwd 與 git 狀態判定的固有限制）：
  - cwd 在別處、但開著 worktree 內檔案寫入的 process；
  - 只留在 worktree reflog 或 `refs/worktree/*` 的 commit（`git reset` 丟掉的）；進行中的 merge；
  - 手寫的 result.md：來源與 `Base SHA` 都是交付檔的自報（交付清單另外併入 PR 的 files，自報只會多比不會少比
    PR 內的檔）；result.md 模板之外的備註不判讀語意，只擋白名單外的字元、HTML entity 與第二個近似 `Keep ignored` 的字串；
  - 工具專屬產物目錄（REBUILDABLE 等舊白名單）的內容不逐檔檢查；其他 ignored 目錄逐檔比對檔名，只認得
    CREDENTIAL_PATTERNS 列的憑證形狀與巢狀 `.git`，內容不判讀：憑證改了名字、使用者手寫的筆記、本地設定，
    都要靠 issue session 在 `Keep ignored` 欄宣告；
  - 根目錄 `.venv`、`.pytest_cache`、`.husky/_` 內「沒有 tracked 檔」的比對（fold_path）只在 APFS 窮舉過：HFS+ 會忽略零寬字元，
    commit 路徑 `.ve<U+200C>nv/t` 比對不到；ext4 casefold、ZFS、NTFS 未驗；
  - result.md 備註或其他欄裡用白名單內字元寫成的第二份 Keep 宣告：數字或 CJK 同形字代字母（`Keep ign0red`、
    `ign〇red`）、沒有分號的 HTML entity（`Keep&nbspignored`）；腳本只採用行首嚴格的 `Keep ignored:` 那一行
    （2026-11-11 使用者決定接受這個殘留，不再列舉）；
  - 讀不到的目錄：git status 只在 stderr 警告、不列出它（ignored 目錄底下讀不到的子目錄另會擋）；
  - 互動 shell 只跑 builtin 迴圈、沒有子程序時，看起來和閒置相同；
  - session 在等使用者回答時，stall-check 的狀態也是 idle；
  - stacked PR：內容核對的對象是該 PR 的 base branch，不一定是 main。
exit code：可清 0；不可清 1；參數錯 2。"""
import argparse
import fnmatch
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path

STALL_CHECK = Path(__file__).resolve().parent / "stall-check.py"
TIMEOUT = 60
SHELLS = {"zsh", "bash", "sh", "fish", "dash"}  # 只有 idle 的 claude 當子程序時也算閒置：Orca 的分頁是 `-zsh -l` → `claude`
# 舊白名單：工具專屬、重建得回來的 ignored 目錄，整包放行、不逐檔看。build、bin、out 這類泛用名不列：常是一般目錄，
# 裡面可能放密鑰或本地 commit，所以走下面 CREDENTIAL_PATTERNS 的逐檔比對。比對 status 回報為目錄（尾 `/`）的最後一段，
# 或 self_ignoring_root 認得的自我忽略目錄。
REBUILDABLE = {"node_modules", "DerivedData", "Pods", ".dart_tool", ".gradle", ".next", ".venv", "__pycache__", ".pytest_cache"}
REBUILDABLE_NAMES = {".DS_Store"}
# husky 在 .husky/_ 產生的檔名（實測本機 husky 目錄）；這裡以外的東西可能是使用者放的，不放行
HUSKY_GENERATED = {".gitignore", "h", "husky.sh", "applypatch-msg", "commit-msg", "post-applypatch", "post-checkout", "post-commit",
                   "post-merge", "post-rewrite", "pre-applypatch", "pre-auto-gc", "pre-commit", "pre-merge-commit", "pre-push",
                   "pre-rebase", "prepare-commit-msg"}
MARKER_MAX_BYTES = 4096
SELF_IGNORING = {".pytest_cache", ".venv", ".husky/_"}  # 實測過會在目錄內放 `*` 的 .gitignore 的工具（相對 worktree 根目錄）；其他路徑沒有這個形狀，不放行
# 上面的舊白名單之外，ignored 檔預設可清（2026-11-11 使用者決定）：issue session 要保留的寫在 result.md 的
# `Keep ignored` 欄，非「無」就擋；欄位缺就擋。下列憑證形狀（比對路徑每一段，NFKC＋去掉格式字元＋casefold＋
# 去尾端空白與點，所以 `.ENV`、`Foo.PEM`、`.e<U+200B>nv` 都算）照擋，除非逐條列在 `Disposable secrets` 欄。
CREDENTIAL_PATTERNS = (
    ".env*", "*.env", "*.env[.~]*",  # dotenv，含 .env.local、.envrc、prod.env.local
    # 私鑰與憑證包（p8 是 Apple APNs／App Store Connect API key），含 `.bak`、`.old`、`~` 這類備份或改名後綴
    "*.pem", "*.key", "*.p12", "*.pfx", "*.p8", "*.ppk", "*.pem[.~]*", "*.key[.~]*", "*.p12[.~]*", "*.pfx[.~]*",
    "*.keystore", "*.jks", "*.keystore[.~]*", "*.jks[.~]*", "key.properties", "keystore.properties",  # Android／Java 簽章
    "*credential*", "client_secret*", "*service-account*", "*service_account*", "*serviceaccount*",  # 雲端與 OAuth 憑證
    "secret.*", "secrets.*", "*.secret", "*.secrets", "token.json",  # 慣用的密鑰設定檔名
    "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*",  # 沒有副檔名的 SSH 私鑰
    ".npmrc", ".netrc", ".pypirc", ".pgpass", ".htpasswd", "*kubeconfig*", "*.ovpn", "*.kdbx",  # token、密碼、連線設定
    "*.tfstate*", "*.tfvars",  # Terraform state 與變數檔常含明文密鑰
)
KEYS = ("Issue", "Status", "Worktree", "Branch", "Base SHA", "Candidate SHA", "Dirty", "Files changed", "Keep ignored",
        "Verification", "PR / CI", "Cross-issue risk", "Pending authorization", "Blocker", "Merged")
OPTIONAL = ("Disposable secrets",)  # 可省略；出現就只能一行
# 模板裡只有這兩行是同一行多欄；其他欄的值就是整行剩下的內容，判定欄不能藏在別的欄後面。
INLINE = {"Worktree": ("Branch",), "Base SHA": ("Candidate SHA", "Dirty")}
LINE_START_RE = re.compile(r"^(?:" + "|".join(re.escape(k) for k in KEYS + OPTIONAL) + r"):")
INVISIBLE_RE = re.compile("[\ufeff\u200b-\u200f\u2060]")
LOCKED = object()
HEX_RE = re.compile(r"[0-9a-fA-F]{7,40}")
KEEP_LOOSE_RE = re.compile("[\\W_]*".join("keep") + "[\\W_]*" + "[\\W_]*".join("ignored"))  # 字母之間可夾任何非字母
# result.md 的字元白名單（2026-11-11 使用者決定）：同形字、組合字元、HTML entity 列舉不完，白名單外一律擋。
# ASCII、§·×、一般標點（U+2010–2027：破折號、引號、刪節號）、箭頭、CJK 標點與假名、注音、CJK 漢字、全形字與半形片假名
# （NFKC 後再比）；半形韓文 U+FFA0–FFDC 不收。
ALLOWED_RANGES = ((0x20, 0x7E), (0xA7, 0xA7), (0xB7, 0xB7), (0xD7, 0xD7), (0x2010, 0x2027), (0x2190, 0x21FF),
                  (0x3000, 0x30FF), (0x3100, 0x312F), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xFF01, 0xFF9F), (0xFFE0, 0xFFEF))
ENTITY_RE = re.compile(r"&#?\w+;")


def run(cmd, cwd=None):
    """回 (returncode, stdout)；找不到指令回 127，逾時回 124。"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd, errors="replace")
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:  # 例如路徑太多超過 ARG_MAX
        return 126, ""
    return p.returncode, p.stdout


def git(path, *args):
    return run(["git", "--no-optional-locks", "-C", str(path), *args])


def parse_result(text):
    """回 (fields, problems)。先去掉不可見字元；欄位只認行首，同一行多欄只限 INLINE。模板每欄要恰好出現一次（大小寫、
    條列、粗體、全形冒號的變形都算同一欄），判定用的值後面不能接延續行。白名單外的字元與 HTML entity 一律擋。"""
    problems = []
    bad = sorted({c for c in text.removeprefix("\ufeff") if not allowed_char(c)})
    if bad:
        problems.append(f"result.md 有白名單外的字元，判不出寫法：{[f'U+{ord(c):04X}' for c in bad][:10]}")
    if ENTITY_RE.search(text):
        problems.append("result.md 有 HTML entity（&…;），判不出寫法")
    text = INVISIBLE_RE.sub("", text)
    lines = text.splitlines()
    fields = {}
    for line in lines:
        if not LINE_START_RE.match(line):
            continue
        first, rest = line.split(":", 1)
        allowed = INLINE.get(first, ())
        pieces = re.split(r"(?:\s{2,}|\t+)(" + "|".join(map(re.escape, allowed)) + r"):", rest) if allowed else [rest]
        fields.setdefault(first, pieces[0].strip())
        for key, value in zip(pieces[1::2], pieces[2::2]):
            fields.setdefault(key, value.strip())
    for key in KEYS + OPTIONAL:
        loose = re.compile(r"(?:^\s*(?:[-*>#\d.]+\s*)?(?:\*\*)?|\s\s|\t)" + re.escape(key) + r"(?:\*\*)?\s*[:：]", re.IGNORECASE)
        hits = sum(1 for ln in lines if loose.search(ln))
        if key in OPTIONAL and hits > 1:
            problems.append(f"result.md 的 {key} 欄最多一行，實際 {hits} 行")
        elif key not in OPTIONAL and hits != 1:
            problems.append(f"result.md 的 {key} 欄應恰好一行，實際 {hits} 行")
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if re.match(r"(?:Status|Pending authorization|Blocker|Keep ignored):", ln) and not LINE_START_RE.match(nxt):
            problems.append(f"result.md 的 {ln.split(':')[0]} 欄後面不是下一個欄位")
        if re.match(r"(?:Merged|Disposable secrets):", ln) and nxt.strip() and not LINE_START_RE.match(nxt) \
                and not nxt.startswith("#"):
            problems.append(f"result.md 的 {ln.split(':')[0]} 欄後面有延續行")
    # Keep ignored 決定刪不刪：正規化後任何近似寫法（`Keep-ignored`、`KeepIgnored`、全形）在任何位置再出現一次就判不出，擋
    if len(KEEP_LOOSE_RE.findall(norm_name(text))) > 1:
        problems.append("result.md 的 Keep ignored 出現不只一次")
    return fields, problems


def allowed_char(c):
    if c in "\t\n\r":
        return True
    if unicodedata.category(c) in ("Mn", "Me", "Cf", "Cc", "Co", "Cn", "Cs"):  # 範圍內的組合字元（如假名濁點）也擋
        return False
    return any(lo <= ord(c) <= hi for lo, hi in ALLOWED_RANGES)


def worktree_entries(repo):
    """回 [(path, branch)]，第一筆是 main worktree；讀不到回 None。"""
    rc, out = git(repo, "worktree", "list", "--porcelain")
    if rc != 0:
        return None
    entries, path, branch = [], None, None
    for line in out.splitlines() + [""]:
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/"):
            branch = line[len("branch refs/heads/"):]
        elif line == "locked" or line.startswith("locked "):
            branch = LOCKED
        elif not line.strip() and path:
            entries.append((os.path.realpath(path), branch))
            path, branch = None, None
    return entries or None


def parse_slug(url):
    m = re.match(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://)?(?:[^@/]+@)?([^/:]+)[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    if not m:
        return None
    host, owner, repo = m.groups()
    return f"{owner}/{repo}" if host == "github.com" else f"{host}/{owner}/{repo}"


def query_prs(repo, branch):
    """該 head branch 的 PR 陣列；查不到回 None。測試時 patch 這個函式。"""
    rc, url = git(repo, "remote", "get-url", "origin")
    slug = parse_slug(url) if rc == 0 else None
    if not slug:
        return None
    rc, out = run(["gh", "-R", slug, "pr", "list", "--head", branch, "--state", "all", "--limit", "5",
                   "--json", "number,state,headRefOid,baseRefName,mergeCommit,url,files,changedFiles"])
    if rc != 0:
        return None
    try:
        data = json.loads(out)
    except ValueError:
        return None
    return data if isinstance(data, list) else None


def check_delivery(repo, wt, fields, branch, head, fetch=True):
    """第 2、4 條：result.md 的完成欄位、PR read-back、完整交付 diff 都在 PR 的 base 上。"""
    problems = []
    if not fields.get("Issue") or fields["Issue"].lower().startswith("unknown"):  # §2 規定填不出來時寫「unknown＋原因」
        problems.append("result.md 的 Issue 欄是空的或 unknown")
    if fields.get("Status") != "merged":
        problems.append(f"Status 是 {fields.get('Status')!r}，不是 merged")
    if fields.get("Pending authorization") != "無":
        problems.append("Pending authorization 不是「無」")
    if fields.get("Blocker") != "無":
        problems.append("Blocker 不是「無」")
    if fields.get("Dirty") != "0":
        problems.append("result.md 的 Dirty 不是 0")
    cand = fields.get("Candidate SHA", "")
    if not (HEX_RE.fullmatch(cand) and head.lower().startswith(cand.lower())):
        problems.append("result.md 的 Candidate SHA 與 HEAD 不符")
    prs = query_prs(repo, branch)
    if prs is None:
        return problems + ["PR 查不到（gh 失敗或 origin 解析不了）"]
    if any(p.get("state") == "OPEN" for p in prs):
        problems.append("這個 branch 還有 OPEN 的 PR")
    merged = [p for p in prs if p.get("state") == "MERGED" and p.get("headRefOid") == head]
    if len(merged) != 1:
        return problems + ["沒有恰好一個 MERGED 且 head 等於 worktree HEAD 的 PR"]
    pr = merged[0]
    merge_oid = ((pr.get("mergeCommit") or {}).get("oid") or "").lower()
    sha = fields.get("Merged", "").lower()
    if not (HEX_RE.fullmatch(sha) and merge_oid.startswith(sha)):
        problems.append("result.md 的 Merged 欄與 PR 的 merge commit 不符")
    base_ref = pr.get("baseRefName")
    if not base_ref:
        return problems + ["PR 沒有 baseRefName"]
    target = f"refs/remotes/origin/{base_ref}"  # 完整 ref：本機同名 branch／tag 蓋不掉；fetch 明寫 refspec：窄 refspec 的 clone 也會更新
    if fetch and git(repo, "fetch", "-q", "origin", f"+refs/heads/{base_ref}:{target}")[0] != 0:
        return problems + [f"git fetch origin {base_ref} 失敗"]
    if merge_oid and git(repo, "merge-base", "--is-ancestor", merge_oid, target)[0] != 0:
        problems.append(f"merge commit 不在 origin/{base_ref} 上（可能被改寫歷史）")
    pr_files = [f.get("path") for f in (pr.get("files") or []) if f.get("path")]
    if not pr_files or len(pr_files) != pr.get("changedFiles"):
        return problems + ["PR 的檔案清單是空的或不完整，算不出交付清單"]
    base = fields.get("Base SHA", "")
    if not HEX_RE.fullmatch(base):
        return problems + ["result.md 的 Base SHA 不是單一 SHA，算不出交付清單"]
    if git(wt, "merge-base", "--is-ancestor", base, "HEAD")[0] != 0:
        return problems + ["Base SHA 不是 HEAD 的祖先，算不出交付清單"]
    if git(repo, "merge-base", "--is-ancestor", base, target)[0] != 0:
        return problems + [f"Base SHA 不在 origin/{base_ref} 上，算不出交付清單"]
    rc, out = git(wt, "diff", "--name-only", "--no-renames", "-z", base, "HEAD")
    if rc != 0:
        return problems + ["讀不到交付清單"]
    # 併入 PR 的 files：Base SHA 是自報，改成較新的 commit 不能把清單縮小；git diff 補上更名前的舊路徑。
    paths = sorted(set(pr_files) | {p for p in out.split("\0") if p})
    rc, out = run(["git", "--no-optional-locks", "--literal-pathspecs", "-C", str(wt), "diff", "--name-only",
                   "--no-renames", target, "HEAD", "--", *paths])
    if rc != 0:
        problems.append(f"無法比對 origin/{base_ref} 與 HEAD")
    elif out.strip():
        problems.append(f"交付內容與 origin/{base_ref} 不同：{', '.join(out.split())[:200]}")
    return problems


def fold_path(path):
    """比對 index 與磁碟的寫法：大小寫不敏感的 FS 上，index 可能記成 `.VENV/t`。"""
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", path).casefold())


def husky_generated_file(wt, parts):
    """`.husky/_` 不像 .venv 整包可重建：只收 husky 產生的扁平一般檔，子目錄、巢狀 repo、其他檔名都維持判不出。"""
    if len(parts) != 3 or parts[2] not in HUSKY_GENERATED:
        return False
    try:
        return stat.S_ISREG(os.lstat(Path(wt, *parts)).st_mode)
    except OSError:
        return False


def self_ignoring_root(wt, parts, tracked, cache):
    """工具把 `*` 寫進自己目錄的 .gitignore 時（pytest、venv、husky），status 逐檔列出、不回報成目錄。
    只認 worktree 根目錄：路徑是固定的 ASCII 名稱，不必重做 FS 與 git 對父目錄名的語意（2026-11-06 三輪驗收都在這裡找到新形狀）。
    只認一般檔（不是 symlink、FIFO）、除了註解只有 `*` 這條規則的 .gitignore，且目錄內沒有 tracked 檔；其他形狀維持判不出。
    照 git 的語意解析：只以 \\n 分行，行尾容許一個 \\r，所以用 bytes 讀，不用 splitlines（`#\\f*` 對 git 是註解）。
    tracked 由呼叫端列出全部路徑後比對，不用 pathspec：pathspec 比對不到時回空，和「沒有 tracked 檔」分不開。
    .gitignore 若 untracked 又沒被忽略，status 已回報工作區不乾淨。"""
    root = next((r for r in SELF_IGNORING if parts[:r.count("/") + 1] == r.split("/")), None)
    if root is None or len(parts) <= root.count("/") + 1:  # 段數沒有多於 root：是 symlink 或檔案本身，不是目錄內容
        return False
    if root == ".husky/_" and not husky_generated_file(wt, parts):
        return False
    if root not in cache:
        marker = Path(wt) / root / ".gitignore"
        try:
            info = os.lstat(marker)
            ok = stat.S_ISREG(info.st_mode) and info.st_size <= MARKER_MAX_BYTES
            if ok:
                lines = [ln.removesuffix(b"\r") for ln in marker.read_bytes().split(b"\n")]
                ok = [ln for ln in lines if ln and not ln.startswith(b"#")] == [b"*"]
        except OSError:
            ok = False
        if ok:
            prefix = fold_path(root) + "/"
            ok = not any(path.startswith(prefix) for path in tracked)
        cache[root] = ok
    return cache[root]


def norm_name(name):
    """大小寫不敏感的 FS 上 `.ENV` 就是 `.env`、`.GIT` 就是 `.git`；零寬字元與全形字也不能繞過。"""
    norm = "".join(c for c in unicodedata.normalize("NFKC", name) if unicodedata.category(c) != "Cf")
    return norm.casefold().rstrip(" \t.")


def credential_name(name):
    """路徑的一段是否像憑證檔。"""
    norm = norm_name(name)
    return any(fnmatch.fnmatchcase(norm, pat) for pat in CREDENTIAL_PATTERNS)


def bare_repo(path):
    """沒有 `.git` 的 bare repo（例如 `mirror.git/`）：有 HEAD 檔、objects 與 refs 目錄。"""
    return os.path.isfile(path / "HEAD") and os.path.isdir(path / "objects") and os.path.isdir(path / "refs")


def scan_ignored(wt, rel):
    """回 (路徑, 原因) 清單：檔案的路徑任一段命中憑證形狀就列出那個檔（目錄名像憑證時列出它底下每個檔，
    `Disposable secrets` 只寫目錄蓋不到）；巢狀 `.git`（不分大小寫）與 bare repo 另列。
    不跟 symlink：刪 worktree 只刪連結本身。讀不到的目錄回報出來，由呼叫端擋下。"""
    hits = []
    parts = rel.rstrip("/").split("/")
    if any(norm_name(p) == ".git" for p in parts):
        hits.append((rel.rstrip("/"), "git"))
    elif not rel.endswith("/") and any(credential_name(p) for p in parts):
        hits.append((rel, "credential"))
    top = Path(wt, *parts)
    # status 不列 `.git`（含 gitfile），巢狀 repo 的內容會逐項列成 ignored：往上找到 worktree 根目錄為止
    for i in range(1, len(parts)):
        anc = Path(wt, *parts[:i])
        if os.path.lexists(anc / ".git") or bare_repo(anc):
            hits.append(("/".join(parts[:i]), "git"))
            break
    if not rel.endswith("/") or top.is_symlink():
        return hits
    errors = []
    for dirpath, dirnames, filenames in os.walk(top, onerror=errors.append, followlinks=False):
        if bare_repo(Path(dirpath)):
            hits.append((Path(dirpath).relative_to(wt).as_posix(), "git"))
        for name in dirnames + filenames:
            path = Path(dirpath, name).relative_to(wt).as_posix()
            if norm_name(name) == ".git":
                hits.append((path, "git"))
            elif name in filenames and any(credential_name(p) for p in path.split("/")):
                hits.append((path, "credential"))
    if errors:
        hits.append((rel.rstrip("/"), "unreadable"))
    return hits


def split_paths(value):
    if not value or value == "無":
        return set()
    return {p.strip() for p in re.split(r"[,，、]", value) if p.strip()}


def check_tree(wt, fields):
    """工作區乾淨，且沒有清掉就回不來的 ignored 檔。不受 status.showUntrackedFiles 等設定影響。"""
    rc, out = git(wt, "status", "--porcelain", "-z", "--untracked-files=all", "--ignored=matching",
                  "--ignore-submodules=none")
    if rc != 0:
        return ["git status 失敗"]
    problems, ignored = [], []
    for entry in out.split("\0"):
        if not entry:
            continue
        if entry.startswith("!! "):
            ignored.append(entry[3:])
        else:
            problems.append(f"工作區不乾淨：{entry[:80]}")
    rc, out = git(wt, "ls-files", "-v", "-z")
    tracked = set()
    if rc != 0:
        problems.append("git ls-files 失敗")
    else:
        entries = [ln for ln in out.split("\0") if ln]
        tracked = {fold_path(ln[2:]) for ln in entries}
        hidden = [ln[2:] for ln in entries if ln[0] == "S" or ln[0].islower()]
        if hidden:
            problems.append(f"有 skip-worktree／assume-unchanged 的檔：{hidden[:3]}")
    if fields.get("Keep ignored") != "無":  # 不給預設值：寫法變形時 fields 沒有這欄，也要擋
        problems.append(f"result.md 的 Keep ignored 不是「無」（{fields.get('Keep ignored')!r}），有 issue session 要保留的 ignored 檔")
    disposable = split_paths(fields.get("Disposable secrets"))
    secrets, repos, unreadable, roots = [], [], [], {}
    for rel in ignored:
        parts = rel.rstrip("/").split("/")
        if parts[0] == ".worktrees":
            continue
        if rel.endswith("/") and parts[-1] in REBUILDABLE:
            continue
        if not rel.endswith("/") and parts[-1] in REBUILDABLE_NAMES:
            continue
        if self_ignoring_root(wt, parts, tracked, roots):
            continue
        for path, kind in scan_ignored(wt, rel):
            if kind == "git":
                repos.append(path)
            elif kind == "unreadable":
                unreadable.append(path)
            elif path not in disposable:
                secrets.append(path)
    if secrets:
        problems.append(f"有憑證形狀的 ignored 檔，未列在 Disposable secrets（{len(secrets)} 個）：{sorted(secrets)}")
    if repos:
        problems.append(f"ignored 項目內有巢狀 git repo（可能有沒推的 commit）：{sorted(set(repos))}")
    if unreadable:
        problems.append(f"讀不完的 ignored 目錄，判不出裡面有沒有憑證：{unreadable[:5]}")
    extra = []
    root = Path(wt) / ".worktrees"
    if root.is_dir():
        for p in root.rglob("*"):
            rel = p.relative_to(root).as_posix()
            if rel != "result.md":
                extra.append(rel)
    if extra:
        problems.append(f".worktrees/ 內除了 result.md 還有別的（可能是巢狀 worktree）：{sorted(extra)[:5]}")
    return problems


def under(path, wt):
    return path == wt or path.startswith(wt + "/")


def idle_problems(wt, rows, lsof_out, ps_out, self_pid):
    """第 3 條。純函式：所有輸入都已取得。self_pid 必須出現在 lsof 輸出，證明 lsof 真的列得到 process。"""
    problems, idle = [], set()
    for r in rows:
        if under(os.path.realpath(r.get("cwd") or ""), wt):
            if r.get("state") == "idle":
                idle.add(int(r["pid"]))
            else:
                problems.append(f"claude session {r.get('pid')} 狀態是 {r.get('state')}")
    procs, pid, comm = {}, None, None
    seen_self = False
    for line in lsof_out.splitlines():
        tag, val = line[:1], line[1:]
        if tag == "p":
            pid = int(val)
            seen_self = seen_self or pid == self_pid
        elif tag == "c":
            comm = val
        elif tag == "n" and under(os.path.realpath(val), wt):
            procs[pid] = comm
    if not seen_self:
        return problems + ["lsof 沒有列出自己，process 清單不可信"]
    children, args = {}, {}
    for line in ps_out.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            args[int(parts[0])] = parts[2] if len(parts) == 3 else ""
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    if self_pid not in args:
        return problems + ["ps 沒有列出自己，process 清單不可信"]
    for pid, comm in sorted(procs.items()):
        if pid in idle:
            continue
        name = (comm or "").lstrip("-")
        tokens = args.get(pid, "").split()
        plain = bool(tokens) and all(t.startswith("-") for t in tokens[1:])
        if name in SHELLS and plain and not set(children.get(pid, [])) - idle:
            continue
        problems.append(f"worktree 內有還在跑的 process：{pid} {comm}")
    return problems


def check_idle(wt):
    rc, out = run([sys.executable, str(STALL_CHECK), "--json"])
    if rc != 0:
        return ["stall-check.py 失敗，判不出 session 狀態"]
    try:
        rows = json.loads(out)
        assert isinstance(rows, list)
    except (ValueError, AssertionError):
        return ["stall-check.py 輸出讀不懂"]
    _, lsof_out = run(["lsof", "-d", "cwd", "-Fpcn"])  # 只有部分 process 讀不到時 rc 也是 1，改由「列得出自己」判定可信
    _, ps_out = run(["ps", "-axo", "pid=,ppid=,args="])
    try:
        return idle_problems(wt, rows, lsof_out, ps_out, os.getpid())
    except (ValueError, KeyError, TypeError) as e:
        return [f"process 清單讀不懂：{e}"]


def evaluate(repo, wt, fetch=True):
    repo, wt = os.path.realpath(repo), os.path.realpath(wt)
    entries = worktree_entries(repo)
    if entries is None:
        return ["--repo 不是 git repo"], {}
    if entries[0][0] == wt:
        return ["這是 main worktree"], {}
    branch = dict(entries).get(wt)
    if wt not in dict(entries):
        return ["這個路徑不是該 repo 的 worktree"], {}
    if branch is LOCKED:
        return ["worktree 被 lock 了"], {}
    if not branch:
        return ["worktree 沒有 branch（detached HEAD）"], {}
    if any(p != wt and p.startswith(wt + "/") for p, _ in entries):
        return ["這個 worktree 底下還有巢狀 worktree"], {}
    result = Path(wt) / ".worktrees" / "result.md"
    if not result.is_file():
        return ["沒有 .worktrees/result.md，來源不明"], {}
    fields, problems = parse_result(result.read_text(encoding="utf-8", errors="replace"))
    if fields.get("Worktree") != wt:
        problems.append("result.md 的 Worktree 欄不等於這個 worktree")
    if fields.get("Branch") != branch:
        problems.append("result.md 的 Branch 欄不等於實際 branch")
    rc, head = git(wt, "rev-parse", "HEAD")
    if rc != 0:
        return problems + ["讀不到 HEAD"], fields
    head = head.strip()
    problems += check_delivery(repo, wt, fields, branch, head, fetch)
    problems += check_tree(wt, fields)
    problems += check_idle(wt)
    return problems, {**fields, "head": head, "branch": branch}


def main():
    ap = argparse.ArgumentParser(description="判定 issue worktree 能不能不問使用者就清（fail-closed，唯讀）。")
    ap.add_argument("--repo", required=True, help="該 worktree 所屬 repo 的路徑")
    ap.add_argument("--worktree", required=True, help="要判定的 worktree 絕對路徑")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    problems, info = evaluate(a.repo, a.worktree)
    if a.json:
        print(json.dumps({"clean": not problems, "problems": problems, "head": info.get("head"),
                          "branch": info.get("branch")}, ensure_ascii=False))
    elif problems:
        print("保留，不要直接清：")
        for p in problems:
            print(f"- {p}")
    else:
        print(f"可以直接清：{info['branch']}@{info['head']}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
