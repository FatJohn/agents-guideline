#!/usr/bin/env python3
"""量「主對話自己寫入」對「派 subagent」的使用率（日落審查用）。

資料來源：~/.claude/projects/**/*.jsonl 的 assistant tool_use 事件。
只數 tool_use 的 JSON 形狀，不做裸字串 grep——rules 全文會出現在每個 jsonl 的
system-reminder 裡，裸 grep 會被污染（見 memory `rules-review-2026-09-02`）。

用法：python3 scripts/dispatch-usage.py [--days 30] [--top 12]
輸出：全域計數、有寫入的 session 數對有派實作型 agent 的 session 數、逐專案表。
已知邊界：subagent 自己的 tool_use 不在主 jsonl（isSidechain 一律 false），所以
side_edits 欄目前恆為 0，只能看主對話端。
"""
import argparse, collections, glob, json, os, time

IMPL_AGENTS = {"general-purpose", "worker", "claude"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    a = ap.parse_args()
    cut = time.time() - a.days * 86400
    proj = collections.defaultdict(collections.Counter)
    tot = collections.Counter()
    edit_sessions, impl_sessions = set(), set()
    for f in glob.glob(os.path.join(a.root, "*", "*.jsonl")):
        if os.path.getmtime(f) < cut:
            continue
        p = os.path.basename(os.path.dirname(f))
        with open(f, errors="ignore") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "assistant":
                    continue
                side = d.get("isSidechain", False)
                for c in (d.get("message") or {}).get("content") or []:
                    if not isinstance(c, dict) or c.get("type") != "tool_use":
                        continue
                    n, inp = c.get("name"), c.get("input") or {}
                    if n in EDIT_TOOLS:
                        k = "edit_sidechain" if side else "edit_main"
                        proj[p][k] += 1; tot[k] += 1
                        if not side:
                            edit_sessions.add(f)
                    elif n == "Agent":
                        st = inp.get("subagent_type", "?")
                        proj[p]["agent:" + st] += 1; tot["agent:" + st] += 1
                        if st in IMPL_AGENTS:
                            impl_sessions.add(f)
    print(f"TOTAL ({a.days}d):", dict(sorted(tot.items())))
    print(f"sessions with main-session edits: {len(edit_sessions)} | "
          f"dispatching impl agents {sorted(IMPL_AGENTS)}: {len(impl_sessions)} | "
          f"both: {len(edit_sessions & impl_sessions)}")
    print()
    print(f"{'project':45s} {'main_edits':>10s} {'gp':>4s} {'worker':>6s} {'verifier':>8s} {'explore':>7s}")
    for p, c in sorted(proj.items(), key=lambda x: -x[1]["edit_main"])[: a.top]:
        print(f"{p[-45:]:45s} {c['edit_main']:10d} {c['agent:general-purpose']:4d} "
              f"{c['agent:worker']:6d} {c['agent:verifier']:8d} {c['agent:Explore']:7d}")


if __name__ == "__main__":
    main()
