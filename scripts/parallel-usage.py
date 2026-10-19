#!/usr/bin/env python3
"""量平行寫入派工：同時在途 ≥2 個寫入型 agent 的群組、worktree 派工、parallel-dispatch 叫用次數。

資料來源：~/.claude/projects/**/*.jsonl 的 assistant tool_use 與 task-notification（不裸 grep，
理由同 dispatch-usage.py）。背景 agent 以 tool_result 的 agentId 對到 task-notification 的結束時間；
找不到結束通知的當作持續到 session 最後一個事件（重疊會高估）。重疊群組是時間上的連通分量，
串連的修正輪會併進同一群。「唯讀」只看 brief 前 600 字的關鍵字。

用法：python3 scripts/parallel-usage.py [--since 2026-09-08] [--out <repo 外路徑>/groups.md] [--classes <classes.json>]
--out 寫逐群明細（含專案名與 brief 摘錄，不要寫進本 repo）；--classes 是 {"群號": "A|A?|Ax|B|C"}
的人工分類，只對同一次輸出的群號有效。來由見 issue #9。
"""
import argparse, collections, glob, json, os, re, datetime as dt

WRITE = {"worker", "worker-opus", "general-purpose", "claude", None, ""}
NOTE_RE = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)

def P(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

CL = {}

def main():
    global CL
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-09-08")
    ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--out")
    ap.add_argument("--classes")
    a = ap.parse_args()
    if a.classes: CL = json.load(open(a.classes))
    since = P(a.since + "T00:00:00+00:00"); cut = since.timestamp()
    tot = collections.Counter(); proj = collections.defaultdict(collections.Counter)
    groups = []; strict = []; nsess = 0; unterminated = 0
    for f in sorted(glob.glob(os.path.join(a.root, "*", "*.jsonl"))):
        if os.path.getmtime(f) < cut: continue
        slug = os.path.basename(os.path.dirname(f)); sess = os.path.basename(f)
        agents = {}   # tool_use_id -> dict
        results = {}  # tool_use_id -> (ts, text)
        notes = {}    # key(task-id or tool-use-id) -> earliest ts
        last = None
        skill = wt = 0
        for line in open(f, errors="ignore"):
            try: d = json.loads(line)
            except ValueError: continue
            ts = d.get("timestamp")
            if not ts: continue
            t = P(ts)
            if t < since: continue
            last = t if (last is None or t > last) else last
            ty = d.get("type")
            if ty == "assistant":
                for c in (d.get("message") or {}).get("content") or []:
                    if not isinstance(c, dict) or c.get("type") != "tool_use": continue
                    inp = c.get("input") or {}
                    if c["name"] == "Skill" and "parallel-dispatch" in str(inp.get("skill", "")): skill += 1
                    if c["name"] == "Agent":
                        st = inp.get("subagent_type")
                        if inp.get("isolation") == "worktree":
                            wt += 1; proj[slug]["wt:" + str(st)] += 1; tot["wt:" + str(st)] += 1
                        agents[c["id"]] = dict(id=c["id"], t0=t, st=st, desc=inp.get("description", ""),
                                               prompt=(inp.get("prompt") or "")[:600], wt=inp.get("isolation")=="worktree", mid=(d.get("message") or {}).get("id") or d.get("uuid"),
                                               bg=bool(inp.get("run_in_background")))
            else:
                if ty == "user":
                    cont = (d.get("message") or {}).get("content")
                    if isinstance(cont, list):
                        for c in cont:
                            if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in agents or \
                               (isinstance(c, dict) and c.get("type") == "tool_result"):
                                txt = c.get("content")
                                if isinstance(txt, list): txt = " ".join(x.get("text", "") for x in txt if isinstance(x, dict))
                                results.setdefault(c.get("tool_use_id"), (t, str(txt)))
                # notifications can appear in user / queue-operation / attachment events
                if "<task-notification>" in line:
                    s = line.replace("\\n", "\n")
                    for m in NOTE_RE.finditer(s):
                        body = m.group(1)
                        tid = re.search(r"<task-id>(.*?)</task-id>", body); tu = re.search(r"<tool-use-id>(.*?)</tool-use-id>", body)
                        stt = re.search(r"<status>(.*?)</status>", body)
                        if stt and stt.group(1).strip() in ("completed", "failed", "killed"):
                            for k in (tid and tid.group(1), tu and tu.group(1)):
                                if k and k not in notes: notes[k] = t
        if not agents: continue
        nsess += 1
        tot["skill_pd"] += skill; proj[slug]["skill_pd"] += skill
        tot["agents"] += len(agents); proj[slug]["agents"] += len(agents)
        iv = []
        for aid, g in agents.items():
            r = results.get(aid)
            aidm = re.search(r"agentId:\s*([0-9a-f]+)", r[1]) if r else None
            if aidm:
                g["agent"] = aidm.group(1)
                end = notes.get(aidm.group(1)) or notes.get(aid)
                if end is None: end = last; g["unterminated"] = True; unterminated += 1
                g["async"] = True
            else:
                end = r[0] if r else g["t0"]; g["async"] = False
            g["t1"] = max(end, g["t0"])
            head = g["prompt"][:600].lower()
            g["ro"] = any(k in head for k in ("唯讀", "只讀", "read-only", "readonly", "不得修改", "不要修改", "不改任何", "不改檔", "do not modify", "不寫入", "不得寫", "嚴禁修改"))
            if g["st"] in WRITE: iv.append(g)
        def comps_of(lst):
            lst = sorted(lst, key=lambda g: g["t0"]); comps = []; cur = []; cend = None
            for g in lst:
                if cur and g["t0"] < cend:
                    cur.append(g); cend = max(cend, g["t1"])
                else:
                    if len(cur) >= 2: comps.append(cur)
                    cur = [g]; cend = g["t1"]
            if len(cur) >= 2: comps.append(cur)
            return comps
        for c in comps_of(iv): groups.append((slug, sess, c))
        for c in comps_of([g for g in iv if not g["ro"]]): strict.append((slug, sess, c, skill))
        tot["write_agents"] += len(iv)
    # output
    lines = []
    def out(s=""):
        lines.append(s)
    out(f"since {a.since}; sessions with Agent calls: {nsess}; Agent calls: {tot['agents']}; write-type agents: {tot['write_agents']}")
    out(f"Skill parallel-dispatch: {tot['skill_pd']}; async agents with no end notification (treated open to session end): {unterminated}")
    out("worktree Agent: " + str({k[3:]: v for k, v in tot.items() if k.startswith('wt:')}) + f" total={sum(v for k,v in tot.items() if k.startswith('wt:'))}")
    out(f"parallel-write groups (spec definition, all write-type roles): {len(groups)}")
    out(f"parallel-write groups STRICT (>=2 overlapping write-type agents whose brief head lacks read-only markers): {len(strict)}")
    out()
    out("project | sessions? | skill | wt | groups")
    gp = collections.Counter(g[0] for g in groups)
    for p in sorted(set(proj) | set(gp)):
        out(f"{p} | skill={proj[p]['skill_pd']} | wt={sum(v for k,v in proj[p].items() if k.startswith('wt:'))} | groups={gp[p]}")
    out(); out("=== MANUAL CLASS (judgement, classes.json) per project: A / A? (borderline) / Ax (same change across repos) / B / C ===")
    pc = collections.defaultdict(collections.Counter)
    for i, (slug, sess, c, sk) in enumerate(strict, 1): pc[slug][CL.get(str(i), "?")] += 1
    allc = collections.Counter()
    for p, cc in sorted(pc.items()):
        out(f"{p}: " + " ".join(f"{k}={cc[k]}" for k in ("A","A?","Ax","B","C","?") if cc[k])); allc.update(cc)
    out("TOTAL: " + " ".join(f"{k}={allc[k]}" for k in ("A","A?","Ax","B","C","?") if allc[k]))
    out(); out("=== STRICT GROUPS (detail) ===")
    for i, (slug, sess, c, sk) in enumerate(strict, 1):
        out(f"\n## G{i} [{CL.get(str(i), '?unclassified')}] wt={sum(g['wt'] for g in c)}/{len(c)} skill_in_session={sk} {slug} / {sess} / {c[0]['t0'].isoformat()} .. {max(g['t1'] for g in c).isoformat()}  n={len(c)}")
        for g in c:
            out(f"- [{g['st']}] {g['t0'].isoformat()}->{g['t1'].isoformat()} {'bg' if g['async'] else 'sync'}{' UNTERMINATED' if g.get('unterminated') else ''} | {g['desc']}")
            out("    " + g["prompt"].replace("\n", " ")[:600])
    if a.out: open(a.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(l for l in lines if not l.startswith(("- [", "    ")))[:6000])

if __name__ == "__main__": main()
