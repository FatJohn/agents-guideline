#!/usr/bin/env python3
"""一次列出某個 repo 每個 issue worktree 的狀態，給「盤點 session」取代反覆 `orca terminal read`。

用途：issue session 把交付包寫在 `<worktree>/.worktrees/result.md`（欄位見
`global/shared/skills/worktree-session/SKILL.md` §2「issue session result」）。這支腳本讀每個 worktree 的
result.md，再拿 git／gh 的事實對照，每個 worktree 輸出一行。它只是彙整 result.md 與 git／gh 事實，不是
完成證據：要宣稱完成、要 merge，仍要看 PR、CI 與 verifier 的回報本身。

完全唯讀：只跑 `git -C <path>`（rev-parse、status、worktree list、remote get-url；status 加
--no-optional-locks 不更新 index）、`gh -R <owner/repo> pr list`、可選的 `orca worktree list --json`；
不寫檔、不改 git 狀態、不碰 `orca terminal` 系列、不讀 TUI 或 process 狀態（TUI idle、process 結束都不對應
任何狀態）。orca 不在或失敗就略過，只少了 linkedIssue 欄。

worktree 列舉用 `git -C <repo> worktree list --porcelain`，涵蓋 Orca 建的 `<repo>/.orca/workspaces/...`
與 `claude -w` 建的，排除第一筆（main worktree）。預設也略過巢狀切片 worktree：路徑落在另一個 linked
worktree 的 `.worktrees/` 底下者（issue session 自己開給 worker 的切片，沒有 result.md）；main worktree
自己的 `<repo>/.worktrees/<x>` 不算巢狀，照列。--include-nested 恢復列出；文字輸出最後一行會寫略過幾個。

狀態規則：
  狀態只來自 result.md 的 Status 欄，合法值：working、blocked、awaiting verification、
  ready for authorization、merged、unknown。機械比對只能把它降成 unknown 並寫一句原因，不能推進成別的
  狀態（例：PR 已 merge 但 result.md 寫 working -> unknown「PR 已 merge，result.md 未更新」，不是 merged）。
  降成 unknown 的情形（每個都附原因與 result.md 的 mtime）：
    無 result.md；Status 缺或不是合法值；Status 自報 unknown；
    Candidate SHA 缺或不是 7-40 位 hex 也不是 uncommitted（無法比對），或與 HEAD 前綴不符
      （uncommitted 不比 SHA）；
    Dirty 缺或不是整數，或與 `git status --short` 行數不符；
    Status=merged 但 Merged 欄不是 7-40 位 hex；
    PR 查不到（gh 失敗、無 origin、detached HEAD）且 Status 是 ready for authorization 或 merged；
    Status=ready for authorization 但沒有 OPEN 的 PR；Status=merged 但沒有 MERGED 的 PR；
    PR 已 merge（且沒有 OPEN 的 PR）但 Status 不是 merged；
    --no-gh 且 Status 是 ready for authorization 或 merged（未查 PR）。
  git 讀不到（HEAD 或 status 失敗、目錄不存在）也是 unknown。

每行欄位：名稱（相對 repo 的路徑）、狀態、原因或 -、result 年齡（result.md 的 mtime 距今）、HEAD 短 SHA、
dirty 行數、PR 編號與狀態（gh error＝查詢失敗、not queried＝--no-gh）、Pending authorization、Blocker。
--json 輸出陣列，欄位更完整（含 result_mtime ISO 時間、reported_status＝result.md 原寫的狀態）。
exit code：成功 0；--repo 不是 git repo 時 2。
注意：Candidate SHA 要精確等於一個 hex SHA 才會被比對；寫成自由文字（例如「PR1 a2fddc0（已 merge）」）
會被判 unknown，請 issue session 依模板補成單一 SHA 或 uncommitted。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STATUSES = (
    "working",
    "blocked",
    "awaiting verification",
    "ready for authorization",
    "merged",
    "unknown",
)
FIELD_KEYS = (
    "Issue", "Status", "Worktree", "Branch", "Base SHA", "Candidate SHA", "Dirty",
    "Files changed", "Verification", "PR / CI", "Cross-issue risk",
    "Pending authorization", "Blocker", "Merged",
)
# key 出現在行首，或前面隔著兩個以上空白／tab（同一行多欄的分隔方式）
FIELD_RE = re.compile(
    r"(?:^|(?<=\s\s)|(?<=\t))(" + "|".join(re.escape(k) for k in FIELD_KEYS) + r"):[ \t]*",
    re.IGNORECASE,
)
CANON = {k.lower(): k for k in FIELD_KEYS}
HEX_RE = re.compile(r"[0-9a-fA-F]{7,40}")
GIT_TIMEOUT = 30
GH_TIMEOUT = 60


class GhError(Exception):
    pass


def run(cmd, timeout=GIT_TIMEOUT):
    """回 (returncode, stdout, stderr)；找不到指令回 127，逾時回 124。"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: command not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timeout"
    return p.returncode, p.stdout, p.stderr


def git(path, *args):
    return run(["git", "--no-optional-locks", "-C", str(path), *args])


def parse_result(text):
    """result.md -> {欄位名: 值}。一行可有多欄；同名欄取第一次出現；缺的欄位不在 dict 裡。
    不在標題處停下：實際的 result.md 會在 `##` 備註段落之後才出現 Blocker／Merged 欄；
    key 只認行首或兩個以上空白之後，所以備註裡的 `- Blocker: ...` 條列不會被誤抓。"""
    fields = {}
    for line in text.splitlines():
        ms = list(FIELD_RE.finditer(line))
        for i, m in enumerate(ms):
            end = ms[i + 1].start() if i + 1 < len(ms) else len(line)
            key = CANON[m.group(1).lower()]
            fields.setdefault(key, line[m.end():end].strip())
    return fields


def list_worktrees(repo):
    """回 (main_path, [linked worktree dict])；repo 不是 git repo 回 None。"""
    rc, out, _ = git(repo, "worktree", "list", "--porcelain")
    if rc != 0:
        return None
    blocks, cur = [], {}
    for line in out.splitlines():
        if not line.strip():
            if cur:
                blocks.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(" ")
        cur[key] = val
    if cur:
        blocks.append(cur)
    if not blocks:
        return None
    main = blocks[0]["worktree"]
    linked = []
    for b in blocks[1:]:
        ref = b.get("branch")
        linked.append({
            "path": b["worktree"],
            "head": b.get("HEAD"),
            "branch": ref[len("refs/heads/"):] if ref and ref.startswith("refs/heads/") else None,
        })
    return main, linked


def is_nested(path, others):
    """path 是否落在 others（其他 linked worktree 路徑）之中某一個的 `.worktrees/` 底下。"""
    return any(o != path and path.startswith(o.rstrip("/") + "/.worktrees/") for o in others)


def parse_slug(url):
    """git remote URL（ssh 或 https）-> `owner/repo`（非 github.com 則 `host/owner/repo`），解析不了回 None。"""
    m = re.match(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://)?(?:[^@/]+@)?([^/:]+)[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    if not m:
        return None
    host, owner, repo = m.groups()
    return f"{owner}/{repo}" if host == "github.com" else f"{host}/{owner}/{repo}"


def repo_slug(main_path):
    rc, out, _ = git(main_path, "remote", "get-url", "origin")
    return parse_slug(out) if rc == 0 else None


def query_prs(slug, branch):
    """查某個 head branch 的 PR（最多 5 筆，新的在前）。失敗丟 GhError。測試時 patch 這個函式。"""
    if not slug:
        raise GhError("無法解析 origin remote")
    rc, out, err = run(
        ["gh", "-R", slug, "pr", "list", "--head", branch, "--state", "all",
         "--json", "number,state,url,mergedAt,headRefOid", "--limit", "5"],
        timeout=GH_TIMEOUT,
    )
    if rc != 0:
        raise GhError((err or out).strip()[:200] or f"gh exit {rc}")
    try:
        data = json.loads(out)
    except ValueError:
        raise GhError("gh 輸出不是 JSON")
    if not isinstance(data, list):
        raise GhError("gh 輸出不是陣列")
    return data


def orca_info():
    """可選加值：{worktree 路徑: {displayName, linkedIssue}}。orca 不在或失敗回 {}，不影響結果。"""
    rc, out, _ = run(["orca", "worktree", "list", "--json", "--limit", "500"], timeout=20)
    if rc != 0:
        return {}
    try:
        items = json.loads(out)["result"]["worktrees"]
        return {w["path"]: {"displayName": w.get("displayName"), "linkedIssue": w.get("linkedIssue")}
                for w in items if isinstance(w, dict) and w.get("path")}
    except (ValueError, KeyError, TypeError):
        return {}


def fmt_age(seconds):
    s = max(0, int(seconds))
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def short(value, n=70):
    value = (value or "").strip()
    if not value:
        return "-"
    return value if len(value) <= n else value[: n - 1] + "…"


def inspect_worktree(wt, base, slug, use_gh, orca):
    """對單一 worktree 產出一列。status 只可能是 result.md 的 Status 或被降成 unknown。"""
    path = wt["path"]
    try:
        name = os.path.relpath(path, base)
        if name.startswith(".."):
            name = path
    except ValueError:
        name = path
    row = {
        "name": name, "path": path, "branch": wt["branch"], "status": "unknown", "reported_status": None,
        "reason": None, "result_mtime": None, "result_age": None, "head": None, "dirty": None,
        "pr": None, "pr_text": "-", "pr_error": None, "pending_authorization": None, "blocker": None,
        "issue": None, "orca_issue": (orca.get(path) or {}).get("linkedIssue"),
        "orca_display": (orca.get(path) or {}).get("displayName"),
    }
    result_path = Path(path) / ".worktrees" / "result.md"
    fields = {}
    if result_path.is_file():
        try:
            st = result_path.stat()
            row["result_mtime"] = datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")
            row["result_age"] = fmt_age(time.time() - st.st_mtime)
            fields = parse_result(result_path.read_text(encoding="utf-8", errors="replace"))
        except OSError as e:
            row["reason"] = f"result.md 讀取失敗：{e.strerror or e}"
    else:
        row["reason"] = "無 result.md"
    row["pending_authorization"] = fields.get("Pending authorization")
    row["blocker"] = fields.get("Blocker")
    row["issue"] = fields.get("Issue")

    # git 事實（即使 result.md 有問題也列出 HEAD／dirty，供人對照）
    if not os.path.isdir(path):
        git_ok = False
        git_err = "worktree 目錄不存在"
    else:
        rc_h, out_h, err_h = git(path, "rev-parse", "HEAD")
        rc_s, out_s, err_s = git(path, "status", "--short")
        git_ok = rc_h == 0 and rc_s == 0
        git_err = None if git_ok else f"git 讀取失敗：{(err_h or err_s).strip()[:80]}"
        if rc_h == 0:
            row["head"] = out_h.strip()
        if rc_s == 0:
            row["dirty"] = len([ln for ln in out_s.splitlines() if ln.strip()])

    # PR 事實（有 branch 才查；每個 worktree 都查，PR 欄對人有用）
    if not use_gh:
        row["pr_text"] = "not queried"
    elif not wt["branch"]:
        row["pr_error"] = "detached HEAD，無 branch 可查"
    else:
        try:
            prs = query_prs(slug, wt["branch"])
        except GhError as e:
            row["pr_text"] = "gh error"
            row["pr_error"] = str(e)
            prs = None
        if prs is not None:
            open_pr = next((p for p in prs if p.get("state") == "OPEN"), None)
            merged_pr = next((p for p in prs if p.get("state") == "MERGED"), None)
            shown = open_pr or merged_pr or (prs[0] if prs else None)
            if shown:
                row["pr"] = {k: shown.get(k) for k in ("number", "state", "url", "mergedAt", "headRefOid")}
                row["pr_text"] = f"#{shown.get('number')} {shown.get('state')}"
            row["_open_pr"] = open_pr is not None
            row["_merged_pr"] = merged_pr is not None
    pr_known = "_open_pr" in row

    reason = row["reason"]
    status = None
    if reason is None:
        raw = (fields.get("Status") or "").strip()
        row["reported_status"] = raw or None
        if not raw:
            reason = "result.md 缺 Status 欄"
        elif raw.lower() not in STATUSES:
            reason = f"Status 值不合法：{short(raw, 40)}"
        else:
            status = raw.lower()
            row["reported_status"] = status
    if reason is None and status == "unknown":
        reason = "result.md 自報 unknown"
    if reason is None and not git_ok:
        reason = git_err
    if reason is None:
        cand = (fields.get("Candidate SHA") or "").strip()
        if cand.lower() == "uncommitted":
            pass
        elif HEX_RE.fullmatch(cand):
            if not row["head"].lower().startswith(cand.lower()):
                reason = "result.md 過時：Candidate SHA ≠ HEAD"
        else:
            reason = "Candidate SHA 缺或格式不明（需單一 SHA 或 uncommitted），無法比對 HEAD"
    if reason is None:
        dirty = (fields.get("Dirty") or "").strip()
        if not re.fullmatch(r"\d+", dirty):
            reason = "Dirty 缺或不是整數，無法比對"
        elif int(dirty) != row["dirty"]:
            reason = "result.md 過時：Dirty 不符"
    if reason is None and status == "merged" and not HEX_RE.fullmatch((fields.get("Merged") or "").strip()):
        reason = "Status=merged 但 Merged 欄不是 SHA"
    if reason is None and status in ("ready for authorization", "merged"):
        if not use_gh:
            reason = "未查 PR"
        elif not pr_known:
            reason = "PR 狀態查不到" + ("（detached HEAD）" if not wt["branch"] else "")
        elif status == "ready for authorization" and not row["_open_pr"]:
            reason = "Status=ready for authorization 但無 OPEN 的 PR"
        elif status == "merged" and not row["_merged_pr"]:
            reason = "Status=merged 但 PR 不是 MERGED"
    if reason is None and pr_known and status != "merged" and row["_merged_pr"] and not row["_open_pr"]:
        reason = "PR 已 merge，result.md 未更新"

    row.pop("_open_pr", None)
    row.pop("_merged_pr", None)
    row["status"] = "unknown" if reason else status
    row["reason"] = reason
    return row


def render_text(rows):
    if not rows:
        return ""
    names = [r["name"] + (f" (#{r['orca_issue']})" if r["orca_issue"] else "") for r in rows]
    nw = max(len(n) for n in names)
    sw = max(len(r["status"]) for r in rows)
    lines = []
    for r, name in zip(rows, names):
        reason = "-"
        if r["reason"]:
            reason = r["reason"]
            extra = []
            if r["reported_status"] and r["reported_status"] != "unknown":
                extra.append(f"result 自報 {r['reported_status']}")
            if r["result_mtime"]:
                extra.append(f"result.md mtime {r['result_mtime']}")
            if extra:
                reason += f"（{'；'.join(extra)}）"
        head = r["head"][:7] if r["head"] else "-"
        dirty = "-" if r["dirty"] is None else str(r["dirty"])
        lines.append(" | ".join([
            name.ljust(nw), r["status"].ljust(sw), reason, f"age={r['result_age'] or '-'}",
            f"head={head}", f"dirty={dirty}", f"pr={r['pr_text']}",
            f"pending={short(r['pending_authorization'])}", f"blocker={short(r['blocker'])}",
        ]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="repo 路徑（main worktree 或任一 linked worktree 皆可）")
    ap.add_argument("--json", action="store_true", help="輸出 JSON 陣列而非每個 worktree 一行")
    ap.add_argument("--include-nested", action="store_true",
                    help="也列出巢狀切片 worktree（路徑在另一個 linked worktree 的 .worktrees/ 底下者，預設略過）")
    ap.add_argument("--no-gh", action="store_true",
                    help="跳過 PR 查詢；此時 ready for authorization／merged 一律 unknown「未查 PR」")
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    listing = list_worktrees(repo) if os.path.isdir(repo) else None
    if listing is None:
        print(f"issue-status: {args.repo} 不是 git repo", file=sys.stderr)
        return 2
    main_path, linked = listing
    slug = None if args.no_gh else repo_slug(main_path)
    orca = orca_info()
    paths = [wt["path"] for wt in linked]
    shown = linked if args.include_nested else [wt for wt in linked if not is_nested(wt["path"], paths)]
    skipped = len(linked) - len(shown)
    rows = [inspect_worktree(wt, main_path, slug, not args.no_gh, orca) for wt in shown]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        text = render_text(rows)
        if text:
            print(text)
        elif not skipped:
            print("issue-status: 沒有 linked worktree", file=sys.stderr)
        if skipped:
            print(f"略過 {skipped} 個巢狀切片 worktree（--include-nested 顯示）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
