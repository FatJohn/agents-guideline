#!/usr/bin/env python3
"""把 issue-status.py（result.md 與 git／gh 事實）和 stall-check.py（claude session 的 TUI 狀態）
併成一張表，給人看的監看畫面用（`mods/session-watch` 的 pane 每分鐘跑一次）。

這張表只給人看，不是判定依據：盤點 session 推進狀態仍只讀 result.md 與 `gh pr view`
（`global/shared/skills/worktree-session/SKILL.md` §2）。session 的 TUI 狀態在這裡只用來提示
「該去哪個分頁看」。

看哪些 worktree（輸出的 `scope` 欄說明這次用的是哪一種）：
  repos       給了 `--repo`（可重複）：只看這些 repo
  dispatched  給了 `--dispatched-by <session id>`，且那個 session 或同一個 checkout 的其他 session（例如前後任的
              盤點 session）的 jsonl 裡 `orca worktree create` 的回傳有還在的 worktree 路徑：只列這些，
              跨 repo 也算。查不到就落到下一種
  under       給了 `--under <目錄>`：反查範圍縮到該目錄所屬 repo 的主 checkout 底下（含巢狀子 repo）
  all         都沒給：從正在跑的 claude session 的 cwd 反查它們所屬的所有 repo
完全唯讀。

每列的 attention：
  you        Status 是 blocked／ready for authorization，或還在做但 Pending authorization 不是「無」
  input      result.md 自報還在做，session 卻停在等人打字
  nosession  result.md 自報還在做，但 worktree 裡沒有活著的 claude session
  check      unknown（result.md 缺欄、互相矛盾；自報還在做而只是過時的不算）
  done       merged
  （空字串）  正常進行中
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = Path.home() / ".claude" / "projects"
LAUNCH = "orca worktree create"
ABS_PATH = re.compile(r'/[^\s"\'\\,;:)\]}>]+')
IN_FLIGHT = ("working", "awaiting verification")
NONE_VALUES = (None, "", "-", "無", "—")
ORDER = {"input": 0, "you": 1, "nosession": 2, "check": 3, "": 4, "done": 5}
ACTIVE = {"working": 0, "turn": 0, "sub": 1, "quiet": 2, "idle": 3, "no-log": 4}


def run_json(argv, timeout=25):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip().splitlines()[-1] if (p.stderr or p.stdout).strip()
                           else f"exit {p.returncode}")
    return json.loads(p.stdout)


def main_checkout(cwd):
    """cwd 所屬 repo 的主 checkout 路徑；不是 git repo 回 None。"""
    try:
        p = subprocess.run(["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    common = p.stdout.strip()
    if p.returncode != 0 or not common.endswith("/.git"):
        return None
    return common[: -len("/.git")]


def session_for(path, sessions):
    """cwd 在這個 worktree 內的 session 裡挑最活躍的一個。巢狀 worktree（`<path>/.worktrees/<子>`）裡的
    session 屬於子 worktree，不算進來，否則父 session 停著等人時會被子 session 的 working 蓋掉。"""
    inside = [s for s in sessions
              if s.get("cwd") == path or ((s.get("cwd") or "").startswith(path + "/")
                                          and not (s.get("cwd") or "").startswith(path + "/.worktrees/"))]
    return min(inside, key=lambda s: ACTIVE.get(s.get("state"), 9)) if inside else None


def classify(row, session):
    status, reported = row["status"], row.get("reported_status")
    stale = status == "unknown" and reported in IN_FLIGHT and (row.get("reason") or "").startswith("result.md 過時")
    shown = reported if stale else status
    pending = row.get("pending_authorization")
    if shown in ("blocked", "ready for authorization"):
        return shown, "you", "輪到你"
    if shown in IN_FLIGHT:
        if session is None:
            return shown, "nosession", "沒有活著的 session"
        if session.get("state") == "idle":
            return shown, "input", "session 停在等你輸入"
        if pending not in NONE_VALUES:
            return shown, "you", "還在做，但有事等你"
        return shown, "", ""
    if shown == "merged":
        return shown, "done", ""
    return shown, "check", row.get("reason") or "result.md 要補"


def join(issue_rows, sessions):
    out = []
    for r in issue_rows:
        s = session_for(r["path"], sessions)
        if s is None and not r.get("result_mtime"):
            continue  # 沒有 result.md 也沒有 session：不是 issue session 的 worktree，不列
        shown, attention, note = classify(r, s)
        out.append({
            "name": f"{Path(r['repo']).name}/{Path(r['path']).name}",
            "path": r["path"],
            "issue": r.get("issue"),
            "status": shown,
            "attention": attention,
            "note": note,
            "session": {"name": s.get("name"), "state": s.get("state"), "silent": (s.get("silent") or "").strip()}
                       if s else None,
            "pr": r.get("pr_text") or "-",
            "pending": r.get("pending_authorization"),
            "blocker": r.get("blocker"),
            "result_age": r.get("result_age"),
        })
    out.sort(key=lambda x: (ORDER.get(x["attention"], 9), x["name"]))
    return out


def dispatched_paths(session_id, projects=None):
    """那個 session 與同一個專案目錄的其他 session 用 `orca worktree create` 建出來的 worktree 的候選路徑。
    同一個專案目錄＝在同一個 checkout 開的 session：盤點 session 換手（context 到門檻開新 session 接手、
    `/clear`）之後 session id 會換，只讀自己的 jsonl 會看不到前一任派出去、還在跑的 worktree。
    讀每份 jsonl，取該 Bash 呼叫回傳裡出現的每個絕對路徑。指令本身常用 shell 變數組路徑，所以看回傳不看
    指令；回傳常被 jq／python 濾成只剩路徑本身，所以不認 JSON 欄位名。候選裡會混進 brief 檔、主 checkout、
    已經清掉的舊 worktree 這類路徑，由 collect 篩掉。找不到那個 session 的 jsonl 回空集合。"""
    paths = set()
    for own in (projects or PROJECTS).glob(f"*/{session_id}.jsonl"):
        for log in own.parent.glob("*.jsonl"):
            pending = set()  # 已送出、還沒看到回傳的 launch；只解析提到 launch 或這些 id 的行，其餘整行跳過
            try:
                f = open(log, encoding="utf-8", errors="replace")
            except OSError:  # 別的 session 的檔可能剛被清掉或讀不到，少一份不該讓整輪失敗
                continue
            with f:
                for line in f:
                    if LAUNCH not in line and not any(i in line for i in pending):
                        continue
                    try:
                        content = (json.loads(line).get("message") or {}).get("content")
                    except ValueError:
                        continue
                    for block in content if isinstance(content, list) else []:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "tool_use" and LAUNCH in str((block.get("input") or {}).get("command")):
                            if isinstance(block.get("id"), str):
                                pending.add(block["id"])
                        elif block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                            pending.discard(block["tool_use_id"])
                            paths.update(ABS_PATH.findall(json.dumps(block.get("content"), ensure_ascii=False)))
    return paths


def worktrees_among(candidates):
    """候選路徑裡還在、且不是主 checkout 的 git worktree → 它的主 checkout。只收 worktree 的根目錄
    （linked worktree 的 `.git` 是檔案）：回傳文字裡常夾著主 checkout 底下的一般子目錄，收進來會讓範圍
    變成 dispatched 卻一列都對不上。"""
    out = {}
    for p in candidates:
        p = p.rstrip("/")
        if (Path(p) / ".git").is_file():
            main = main_checkout(p)
            if main and main != p:
                out[p] = main
    return out


def under_root(cwd, root):
    return cwd == root or cwd.startswith(root + "/")


def collect(repos, under=None, dispatched_by=None):
    errors = []
    try:
        sessions = run_json([sys.executable, str(HERE / "stall-check.py"), "--json"])
    except Exception as e:  # session 狀態拿不到時照樣列 result.md，只是少一欄
        sessions, _ = [], errors.append(f"stall-check: {e}")
    scope, only = "repos", None
    if not repos:
        only = worktrees_among(dispatched_paths(dispatched_by)) if dispatched_by else {}
        if only:
            scope = "dispatched"
            found = set(only.values())
        else:
            only = None
            scope = "under" if under else "all"
            root = (main_checkout(under) or under.rstrip("/")) if under else None
            found = {main_checkout(s["cwd"]) for s in sessions
                     if s.get("cwd") and (root is None or under_root(s["cwd"], root))}
        repos = sorted(r for r in found if r)
    rows = []
    for repo in repos:
        try:
            rows += run_json([sys.executable, str(HERE / "issue-status.py"), "--repo", repo, "--json"])
        except Exception as e:
            errors.append(f"{Path(repo).name}: {e}")
    if only is not None:
        rows = [r for r in rows if r["path"] in only]
    return {"generated_at": datetime.now().strftime("%H:%M"), "scope": scope, "rows": join(rows, sessions),
            "errors": errors}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", action="append", default=[], help="repo 主 checkout 路徑；可重複。不給就從在跑的 session 反查")
    ap.add_argument("--dispatched-by", help="沒給 --repo 時，只列這個 session id 與同一個 checkout 的其他 session 用 orca worktree create 建出來的 worktree")
    ap.add_argument("--under", help="沒給 --repo、也查不到派出紀錄時，只反查這個目錄所屬 repo 底下的 session")
    ap.add_argument("--json", action="store_true", help="輸出 JSON（給 mod 用）")
    args = ap.parse_args()
    data = collect([str(Path(r).expanduser()) for r in args.repo],
                   str(Path(args.under).expanduser()) if args.under else None, args.dispatched_by)
    if args.json:
        json.dump(data, sys.stdout, ensure_ascii=False)
        return
    for r in data["rows"]:
        s = r["session"]
        print(" | ".join([r["attention"] or "-", r["name"], r["status"],
                          f"{s['state']} {s['silent']}" if s else "no session", f"pr={r['pr']}", r["note"] or "-"]))
    for e in data["errors"]:
        print(f"error: {e}")


if __name__ == "__main__":
    main()
