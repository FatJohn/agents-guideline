#!/usr/bin/env python3
"""列出這台機器上每個在跑的 claude session 靜默多久、卡在哪裡。

用途：盤點 session 或使用者在 Orca 分頁外一眼看出哪個 issue session 是「在跑工具」、「等人
打字」、「等背景 subagent」還是「送出後靜默太久」。做法借自 oat-agents 的 liveness 報告：從
session jsonl 算最後一筆訊息距今多久，以及有沒有送出工具呼叫但還沒收到結果（outstanding）。
它只是線索，不是狀態：靜默 20 分的 Bash 可能是在跑 build；判定仍要去那個分頁看。

每行欄位：PID、狀態、靜默時間、outstanding、harness（sessions json 的 status@多久前更新）、cwd。狀態定義（依 jsonl 最後一筆訊息判）：
  idle     最後一筆是 assistant 收尾（沒有工具呼叫）且沒有還在跑的 subagent＝在等人打字
  sub      同上，但 session 底下有還沒收尾的 subagent transcript（背景 Agent）；逐個列在下一行
  turn     最後一筆是 user（prompt 或 tool_result）＝輪到模型、還沒有下一筆；outstanding 顯示 (model)
  working  有送出工具呼叫但還沒收到 tool_result；outstanding 顯示工具名
  quiet    turn 或 working 的靜默超過 --quiet-min（預設 5 分；subagent cache 也是 5 分）
  no-log   找不到對應的 session jsonl（剛啟動、或 cwd 與 projects 目錄對不上）
process 配哪個 jsonl：先用 harness 寫的 `~/.claude/sessions/<pid>.json` 的 sessionId（2026-10-15 以 pty 開
session 送 `/clear` 實測：json 的 sessionId 會換成新檔；若同目錄仍有在該檔最後一筆之後才開始的檔，
當作 json 過期、改配那個新檔）；
沒有 json 就取第一筆訊息不早於 process 啟動（`ps lstart`）−2 分、且最近有動靜的候選檔；再沒有就退回
該目錄 mtime 最新的未取走檔。`harness` 欄是 sessions json 的 status 與其更新時間，獨立於 jsonl 判定。
下列 user 訊息不算「輪到模型」而算收尾：local command（`<command-name>`／`<local-command-stdout>`）、
compact summary（isCompactSummary）、`[Request interrupted by user]`、subagent 交回報告的 tool_result
（toolEndsTurn）。跟 chrome 擴充溝通的 `claude --chrome-native-host` 不是 session，不列。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
SESSIONS = Path.home() / ".claude" / "sessions"
START_SLACK = timedelta(minutes=2)  # process 啟動到第一筆 jsonl 之間允許的落差


def running_claude_processes():
    """回 [(pid, cwd, started_at)]。用 ps 列全部 process 再自己比對，不用 pgrep：macOS 的 BSD pgrep
    預設排除自己的祖先 process（man pgrep 的 -a），從 claude session 裡跑會漏掉那個 session 自己。
    cwd 在 macOS 用 lsof、Linux 用 /proc。"""
    try:
        comm_out = subprocess.run(["ps", "-axo", "pid=,comm="], capture_output=True, text=True).stdout
        args_out = subprocess.run(["ps", "-axo", "pid=,lstart=,args="], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return []
    comm_by_pid = {}
    for line in comm_out.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            comm_by_pid[parts[0]] = parts[1]
    procs = []
    for line in args_out.splitlines():
        parts = line.split(None, 6)  # pid + lstart 五段 + args
        if len(parts) < 6:
            continue
        pid, lstart = parts[0], " ".join(parts[1:6])
        args = parts[6] if len(parts) > 6 else ""
        comm = comm_by_pid.get(pid, "")
        if os.path.basename(comm) != "claude" and not re.match(r"(^|.*/)claude( |$)", args):
            continue
        if "--chrome-native-host" in args:
            continue
        try:
            started = datetime.strptime(lstart, "%a %b %d %H:%M:%S %Y").astimezone()
        except ValueError:
            started = None
        cwd = process_cwd(pid)
        if cwd:
            procs.append((int(pid), cwd, started))
    return procs


def process_cwd(pid):
    proc_cwd = Path(f"/proc/{pid}/cwd")
    if proc_cwd.exists():
        try:
            return os.readlink(proc_cwd)
        except OSError:
            return None
    res = subprocess.run(["lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn"], capture_output=True, text=True).stdout
    for line in res.splitlines():
        if line.startswith("n"):
            return line[1:]
    return None


def project_dir_for(cwd):
    return PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", cwd)


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def first_ts(jsonl):
    with open(jsonl, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("timestamp"):
                return parse_ts(rec["timestamp"])
    return None


def scan(jsonl):
    """回 (last_ts, outstanding, last_kind)。outstanding 是 [(tool_use_id, name, ts)]；last_kind 是
    最後一筆訊息的種類：'assistant-end'（assistant 沒有 tool_use，或 user tool_result 帶 toolEndsTurn＝
    subagent 交回報告的收尾）、'assistant-tool'、'user'、None。"""
    last_ts = None
    last_kind = None
    pending = {}
    with open(jsonl, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("type")
            if t not in ("assistant", "user"):
                continue
            ts = rec.get("timestamp")
            if ts:
                last_ts = parse_ts(ts)
            content = (rec.get("message") or {}).get("content")
            has_tool_use = False
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if t == "assistant" and part.get("type") == "tool_use":
                        has_tool_use = True
                        pending[part.get("id")] = (part.get("name"), last_ts)
                    elif t == "user" and part.get("type") == "tool_result":
                        pending.pop(part.get("tool_use_id"), None)
            if t == "user":
                last_kind = "assistant-end" if user_record_ends_turn(rec, content) else "user"
            else:
                last_kind = "assistant-tool" if has_tool_use else "assistant-end"
    outstanding = [(k, v[0], v[1]) for k, v in pending.items()]
    return last_ts, outstanding, last_kind


END_MARKERS = ("<command-name>", "<local-command-stdout>", "[Request interrupted by user]")


def user_record_ends_turn(rec, content):
    """user 訊息裡不會讓模型接著跑的那幾種：subagent 交回報告的 tool_result（toolEndsTurn）、
    compact summary、local command 的回顯、使用者中斷。"""
    if rec.get("toolEndsTurn") is True or rec.get("isCompactSummary") is True:
        return True
    texts = [content] if isinstance(content, str) else [
        part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
    ] if isinstance(content, list) else []
    return any(t.lstrip().startswith(END_MARKERS) for t in texts)


def harness_session(pid):
    """`~/.claude/sessions/<pid>.json`：harness 自己記的 sessionId／status；沒有或壞掉回 None。"""
    f = SESSIONS / f"{pid}.json"
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pair_logs(procs, pdir):
    """同一 cwd 的 process 與 jsonl 配對。順序：harness 的 sessions json 指到的檔；否則第一筆訊息不早於
    啟動−START_SLACK 的候選檔中最近有動靜（最後一筆訊息最新）的那個——`/clear` 會開新檔，取最早的會
    黏在舊檔上；再否則退回 mtime 最新的未取走檔。回 {pid: (log 或 None, harness json 或 None)}。"""
    logs = [p for p in pdir.glob("*.jsonl") if p.is_file()] if pdir.is_dir() else []
    firsts = {p: first_ts(p) for p in logs}
    lasts = {}
    claimed = set()
    result = {}
    infos = {pid: harness_session(pid) for pid, _cwd, _started in procs}
    for pid, _cwd, _started in procs:  # 先把 harness 指到的檔配走，別被啟動時間較早的 process 搶
        info = infos[pid]
        sid = info.get("sessionId") if isinstance(info, dict) else None
        if sid:
            f = pdir / f"{sid}.jsonl"
            if f in logs and f not in claimed:
                # /clear 後 json 會換 sessionId（2026-10-15 實測）；這段是 json 過期時的備援：若有別的檔在
                # f 最後一筆之後才開始，那是後來開出的新檔（動靜必然比 f 新），改配其中最近有動靜的
                f_last = scan(f)[0] or firsts[f]
                successors = [g for g in logs if g not in claimed and g != f and firsts[g] and f_last and firsts[g] >= f_last]
                if successors:
                    for g in successors:
                        lasts[g] = scan(g)[0] or firsts[g]
                    f = max(successors, key=lambda x: lasts[x])
                claimed.add(f)
                result[pid] = (f, info)
    # 最新啟動的 process 先配：它的候選只有自己啟動後的檔，不會搶走舊 process 的；反過來配舊 process 會把新檔搶走
    for pid, _cwd, started in sorted(procs, key=lambda x: (x[2] is None, x[2]), reverse=True):
        if pid in result:
            continue
        pick = None
        if started is not None:
            candidates = [p for p in logs if p not in claimed and firsts[p] and started - START_SLACK <= firsts[p]]
            if candidates:
                for p in candidates:
                    if p not in lasts:
                        lasts[p] = scan(p)[0] or firsts[p]
                pick = max(candidates, key=lambda p: lasts[p])
        if pick is None:
            rest = [p for p in logs if p not in claimed]
            if rest:
                pick = max(rest, key=lambda p: p.stat().st_mtime)
        if pick is not None:
            claimed.add(pick)
        result[pid] = (pick, infos[pid])
    return result


def active_subagents(pdir, main_log, now):
    """session 底下還沒收尾的 subagent transcript（最後一筆不是 assistant 收尾）。"""
    rows = []
    subdir = pdir / main_log.stem / "subagents"
    for sub in subdir.glob("agent-*.jsonl"):
        s_last, s_out, s_kind = scan(sub)
        if not s_last or s_kind == "assistant-end":
            continue
        rows.append((s_last, {
            "file": sub.name,
            "silent": fmt_silent(now - s_last),
            "outstanding": ",".join(n for _, n, _ in s_out) or "(model)",
        }))
    rows.sort(key=lambda r: r[0], reverse=True)  # 最近有動靜的在前
    return [r for _, r in rows]


def fmt_silent(delta):
    s = int(delta.total_seconds())
    return f"{s // 60:3d}m{s % 60:02d}s"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet-min", type=float, default=5.0, help="turn／working 靜默超過這個分鐘數就標 quiet（預設 5）")
    ap.add_argument("--json", action="store_true", help="輸出 JSON 而非表格")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    procs = running_claude_processes()
    by_cwd = {}
    for p in procs:
        by_cwd.setdefault(p[1], []).append(p)
    rows = []
    for cwd, group in by_cwd.items():
        pdir = project_dir_for(cwd)
        logs = pair_logs(group, pdir)
        for pid, _cwd, _started in group:
            row = {"pid": pid, "cwd": cwd, "state": "no-log", "silent": None, "outstanding": None, "subagents": [], "harness": None}
            main_log, info = logs.get(pid, (None, None))
            if isinstance(info, dict) and info.get("status"):
                age = None
                if isinstance(info.get("statusUpdatedAt"), (int, float)):
                    age = fmt_silent(now - datetime.fromtimestamp(info["statusUpdatedAt"] / 1000, tz=timezone.utc)).strip()
                row["harness"] = f"{info['status']}@{age}" if age else info["status"]
            if main_log:
                last_ts, outstanding, last_kind = scan(main_log)
                if last_ts:
                    silent = now - last_ts
                    row["silent"] = fmt_silent(silent)
                    over = silent.total_seconds() > args.quiet_min * 60
                    if outstanding:
                        row["state"] = "quiet" if over else "working"
                        row["outstanding"] = ",".join(n for _, n, _ in outstanding)
                    elif last_kind == "user":
                        row["state"] = "quiet" if over else "turn"
                        row["outstanding"] = "(model)"
                    else:
                        row["state"] = "idle"
                    row["subagents"] = active_subagents(pdir, main_log, now)
                    if row["state"] == "idle" and row["subagents"]:
                        row["state"] = "sub"
            rows.append(row)
    rows.sort(key=lambda r: r["cwd"])
    if args.json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return
    if not rows:
        print("沒有在跑的 claude process")
        return
    for r in rows:
        print(f"{r['pid']:>6}  {r['state']:<8} {r['silent'] or '   —   ':>8}  {r['outstanding'] or '-':<14} {r['harness'] or '-':<14} {r['cwd']}")
        for s in r["subagents"]:
            print(f"{'':>6}  {'└ sub':<8} {s['silent']:>8}  {s['outstanding'] or '-':<14} {'':<14} {s['file']}")


if __name__ == "__main__":
    main()
