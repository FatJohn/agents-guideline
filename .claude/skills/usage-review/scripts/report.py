#!/usr/bin/env python3
"""report.py - read the JSON written by extract.py and print cost / behaviour tables.

Eleven sub-commands (cost, cache, context, reports, dispatch, controller, verifier, agents,
sessions, weekly, escapes) share the same filters. Nothing here reads a jsonl file: the only input is the
extract output (schema: references/schema.md), so this file never has to know about Claude
Code's internal record format.

Pure standard library (Python >= 3.10 intended; kept 3.9-compatible). No machine facts, project
names or time windows live in this file: everything comes from arguments or from the data file.

Assignment rules (also printed in each report):
  * request level tables (cost, cache, context) use the request time `t`;
  * agent level tables (reports, agents, verifier) assign a subagent to the window of its
    `first` event and count all of its requests, so one subagent is never split across windows;
  * dispatch / controller use the time of the Agent call, the edit or the bash write.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import usagelib as ul  # noqa: E402

COMMANDS = ("cost", "cache", "context", "reports", "dispatch", "controller", "verifier", "agents", "sessions", "weekly", "escapes")
MAIN_TTL_S = 3600  # main conversation writes 1h cache
SUB_TTL_S = 300    # subagents are assumed to write 5m cache
REWRITE_CW_RATIO = 0.5
# (name, lower bound inclusive, upper bound exclusive) on ctx = inp + cw + cr
CTX_BUCKETS = (("lt100k", None, 100_000), ("100k_200k", 100_000, 200_000), ("200k_400k", 200_000, 400_001), ("gt400k", 400_001, None))
VERDICT_RE = re.compile(r"(?<![A-Za-z])(CONVERGED|PROSE-ONLY|INCONCLUSIVE|OPEN)(?![A-Za-z])")

# ---------------------------------------------------------------- small numeric helpers


def pct(xs, q):
    """Linear-interpolated quantile of a list of numbers; None for an empty list."""
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def median(xs):
    return pct(xs, 0.5)


def ri(x):
    """round to int, keeping None."""
    return None if x is None else int(round(x))


def ratio(a, b):
    return a / b if b else None


def ep(t: str) -> float:
    return ul.parse_ts(t).timestamp()


def norm_bool(v):
    """Agent-call flags arrive as true / "true" / false / null; show them uniformly."""
    if v is None:
        return None
    if isinstance(v, str):
        return "true" if v.strip().lower() == "true" else "false"
    return "true" if v else "false"


# ---------------------------------------------------------------- windows


class Window:
    def __init__(self, name, lo=None, hi=None):
        self.name, self.lo, self.hi = name, lo, hi  # lo/hi: UTC ISO strings (ms, Z) or None

    def has(self, t: str) -> bool:
        return (self.lo is None or t >= self.lo) and (self.hi is None or t < self.hi)

    def label(self):
        return {"name": self.name, "from": self.lo, "to": self.hi}


def parse_windows(specs, tz):
    """['NAME=ISO..ISO', ...] -> [Window]. Either bound may be empty (open). No specs -> one 'all' window."""
    if not specs:
        return [Window("all")]
    out, seen = [], set()
    for spec in specs:
        name, eq, rng = spec.partition("=")
        lo_s, sep, hi_s = rng.partition("..")
        if not eq or not name or not sep:
            raise ValueError(f"--window expects NAME=ISO..ISO, got {spec!r}")
        if name in seen:
            raise ValueError(f"duplicate window name {name!r}")
        seen.add(name)
        lo = ul.fmt_ts(ul.parse_cli_time(lo_s, tz)) if lo_s.strip() else None
        hi = ul.fmt_ts(ul.parse_cli_time(hi_s, tz)) if hi_s.strip() else None
        if lo and hi and lo >= hi:
            raise ValueError(f"window {name!r}: start must be earlier than end")
        out.append(Window(name, lo, hi))
    return out


# ---------------------------------------------------------------- context (filters, pricing, derived fields)


def _pricing_for(data):
    path = (data.get("args") or {}).get("pricing")
    if path and Path(path).is_file():
        try:
            return ul.load_pricing(path), None
        except (OSError, ValueError):
            pass
    note = None
    if path:
        note = f"資料檔記錄的 pricing 檔 {path} 讀不到，成本占比改用 skill 內附的 pricing.json（總額仍取資料檔裡存的 cost 欄位）。"
    return ul.load_pricing(None), note


class Ctx:
    """The data file after --project / --exclude-session filtering, with cost fields resolved."""

    def __init__(self, data, tz=None, projects=(), exclude=(), corrected=False, exclude_projects=()):
        self.data = data
        self.tz = ul.parse_tz(tz)
        self.corrected = bool(corrected)
        self.pricing, self.pricing_note = _pricing_for(data)
        self.mult = self.pricing["cache_write_multiplier"]
        self.sessions = {}
        for sid, s in data["sessions"].items():
            if any(sid.startswith(x) for x in exclude):
                continue
            if projects and not any(p in (s.get("slug") or "") for p in projects):
                continue
            if any(p in (s.get("slug") or "") for p in exclude_projects):
                continue
            self.sessions[sid] = s
        self.reqs = [r for r in data["reqs"] if r["sid"] in self.sessions]
        self.reqs.sort(key=lambda r: r["t"])
        for r in self.reqs:
            self._annotate(r)
        self.agents = {aid: a for aid, a in data["agents"].items() if a["sid"] in self.sessions}
        self.agent_cost = collections.defaultdict(float)
        self.agent_reqs = collections.defaultdict(list)
        self.main_reqs = collections.defaultdict(list)
        for r in self.reqs:
            if r["agent"]:
                self.agent_reqs[r["agent"]].append(r)
                if r["_usd"] is not None:
                    self.agent_cost[r["agent"]] += r["_usd"]
            else:
                self.main_reqs[r["sid"]].append(r)
        self.call_by_agent = {}
        for sid, s in self.sessions.items():
            for call in s["agent_calls"].values():
                if call.get("agent_id"):
                    self.call_by_agent[call["agent_id"]] = call

    # -- cost fields -------------------------------------------------------

    def _annotate(self, r):
        entry = ul.price_for(r.get("model"), self.pricing)
        r["_ep"] = ep(r["t"])
        r["_ctx"] = (r.get("inp") or 0) + (r.get("cw") or 0) + (r.get("cr") or 0)
        usd = None
        if r.get("cost_raw") is not None:  # null cost_raw == unpriced at extraction time
            if self.corrected:
                usd = r.get("cost_est")
                if usd is None:
                    usd = ul.cost(r, self.pricing, corrected=True)
            else:
                usd = r["cost_raw"]
        r["_usd"] = usd
        comp = None
        if entry is not None:
            if self.corrected:
                out = r.get("out_est")
                if out is None:
                    out = ul.estimate_output(r.get("model"), r.get("out_raw") or 0, r.get("vis") or 0, self.pricing)
            else:
                out = r.get("out_raw") or 0
            p_in = entry["input"]
            comp = {
                "cache_read": (r.get("cr") or 0) * entry["cache_read"] / 1e6,
                "cache_write_1h": (r.get("cw1h") or 0) * p_in * self.mult["1h"] / 1e6,
                "cache_write_5m": (r.get("cw5m") or 0) * p_in * self.mult["5m"] / 1e6,
                "input": (r.get("inp") or 0) * p_in / 1e6,
                "output": out * entry["output"] / 1e6,
            }
            r["_out"] = out
        r["_comp"] = comp
        r["_cwusd"] = (comp["cache_write_1h"] + comp["cache_write_5m"]) if comp else 0.0

    # -- window helpers ----------------------------------------------------

    def reqs_in(self, win):
        return [r for r in self.reqs if win.has(r["t"])]

    def agents_in(self, win):
        return [a for a in self.agents.values() if win.has(a["first"])]

    def calls_in(self, win):
        """[(sid, tool_use_id, call)] with the call time inside the window."""
        out = []
        for sid, s in self.sessions.items():
            for tid, call in s["agent_calls"].items():
                if win.has(call["t"]):
                    out.append((sid, tid, call))
        out.sort(key=lambda x: x[2]["t"])
        return out

    def day(self, t: str) -> str:
        return dt.datetime.fromtimestamp(ep(t), self.tz).strftime("%Y-%m-%d")

    def call_end(self, sid, call):
        """(end_epoch, unterminated). In flight from the Agent call until the first
        task-notification, else the tool_result; with neither, until the session's last event."""
        end_t = call.get("first_notification_t") or (call.get("result") or {}).get("t")
        if end_t is None:
            last = self.sessions[sid].get("last") or call["t"]
            return max(ep(last), ep(call["t"])), True
        return max(ep(end_t), ep(call["t"])), False

    def agent_type(self, a):
        return a.get("type") or "unknown"

    def agent_call(self, a):
        """The Agent call that started this subagent, or {}."""
        s = self.sessions.get(a["sid"])
        return (s["agent_calls"].get(a.get("tool_use_id")) if s else None) or self.call_by_agent.get(a["id"]) or {}

    def agent_note(self, a):
        """The notification of the Agent call that started this subagent, or None."""
        return self.agent_call(a).get("notification")


# ---------------------------------------------------------------- tables


def cap_rows(rows, top, label, sum_cols, share_of=None):
    """Keep the first `top` rows and fold the rest into one '(其餘 N 個)' row summing `sum_cols` (column indexes)."""
    if top is None or top < 1 or len(rows) <= top:
        return rows
    rest = rows[top:]
    folded = [None] * len(rows[0])
    folded[0] = f"({label} {len(rest)} 個)"
    for i in sum_cols:
        folded[i] = sum(r[i] for r in rest)
    if share_of:
        idx, total_idx, denom = share_of
        folded[idx] = ratio(folded[total_idx], denom)
    return rows[:top] + [folded]


def table(tid, title, columns, rows, note=None):
    return {"id": tid, "title": title, "columns": list(columns), "rows": [list(r) for r in rows], "note": note}


def basis(ctx):
    return "est（補估後 output）" if ctx.corrected else "raw（jsonl 記的 output）"


def fmt_cell(col, v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if col.endswith("_usd"):
        return f"${v:,.2f}" if abs(v) >= 1 or v == 0 else f"${v:,.3f}"
    if col.endswith("_share"):
        return f"{v * 100:.1f}%"
    if col.endswith(("_per_pr", "_per_hour")) and isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:,.1f}"
    return str(v).replace("|", "\\|").replace("\n", " ")


def render_table_md(t):
    lines = [f"### {t['title']}", ""]
    if t["note"]:
        lines += [f"> {t['note']}", ""]
    if not t["rows"]:
        lines += ["（無資料）", ""]
        return lines
    lines.append("| " + " | ".join(t["columns"]) + " |")
    lines.append("|" + "|".join("---" for _ in t["columns"]) + "|")
    for row in t["rows"]:
        lines.append("| " + " | ".join(fmt_cell(c, v) for c, v in zip(t["columns"], row)) + " |")
    lines.append("")
    return lines


def _rounded(v):
    return round(v, 6) if isinstance(v, float) else v


def render_md(rep):
    lines = [f"# usage-review: {rep['command']}", ""]
    for k, v in rep["header"].items():
        lines.append(f"- {k}：{v}")
    lines.append("")
    for n in rep["notes"]:
        lines.append(f"- 註：{n}")
    if rep["notes"]:
        lines.append("")
    for w in rep["windows"]:
        span = f"{w['from'] or '(開頭)'} .. {w['to'] or '(結尾)'}"
        lines += [f"## 窗口 {w['name']}（UTC {span}）", ""]
        for t in w["tables"]:
            lines += render_table_md(t)
    return "\n".join(lines).rstrip() + "\n"


def to_json(rep):
    out = {k: v for k, v in rep.items() if k != "windows"}
    out["windows"] = []
    for w in rep["windows"]:
        tables = []
        for t in w["tables"]:
            rows = [{c: _rounded(v) for c, v in zip(t["columns"], row)} for row in t["rows"]]
            tables.append({"id": t["id"], "title": t["title"], "note": t["note"], "columns": t["columns"], "rows": rows})
        out["windows"].append({**{k: v for k, v in w.items() if k != "tables"}, "tables": tables})
    return json.dumps(out, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- cost


def cmd_cost(ctx, win, args):
    reqs = ctx.reqs_in(win)
    priced = [r for r in reqs if r["_usd"] is not None]
    total = sum(r["_usd"] for r in priced)
    unpriced = collections.Counter(r["model"] for r in reqs if r["_usd"] is None)
    ttl_unknown = sum(1 for r in reqs if (r.get("cw") or 0) > 0 and not r.get("cw_ttl_known", True))
    summary_cols = ["reqs", "priced_reqs", "unpriced_reqs", "cost_usd"]
    summary_row = [len(reqs), len(priced), len(reqs) - len(priced), total]
    if ctx.corrected:
        summary_cols.append("cost_raw_usd")
        summary_row.append(sum(r["cost_raw"] for r in priced if r.get("cost_raw") is not None))
    summary_cols.append("cw_ttl_unknown_reqs")
    summary_row.append(ttl_unknown)
    tables = [table("summary", f"總額（成本口徑 {basis(ctx)}）", summary_cols, [summary_row],
                    "cost_usd 是上面口徑；開 --corrected 時同時列 cost_raw_usd 供並列。cw_ttl_unknown_reqs 的 cache write 整筆以 1h 計價（上界）。")]

    def group(keyf):
        agg = collections.defaultdict(lambda: [0, 0.0])
        for r in priced:
            a = agg[keyf(r)]
            a[0] += 1
            a[1] += r["_usd"]
        return sorted(agg.items(), key=lambda kv: (-kv[1][1], str(kv[0])))

    rows = [[k[0], k[1], v[0], v[1], ratio(v[1], total)] for k, v in group(lambda r: (r["role"], ul.family(r["model"])))]
    tables.append(table("by_role_family", "依角色 x model family", ["role", "family", "reqs", "cost_usd", "cost_share"], rows))
    rows = [[k, v[0], v[1], ratio(v[1], total)] for k, v in group(lambda r: r["model"])]
    tables.append(table("by_model", "依 model", ["model", "reqs", "cost_usd", "cost_share"], rows))
    slug_sessions = collections.defaultdict(set)
    for r in priced:
        slug_sessions[ctx.sessions[r["sid"]].get("slug")].add(r["sid"])
    slug_rows = [[k, len(slug_sessions[k]), v[0], v[1], ratio(v[1], total)] for k, v in group(lambda r: ctx.sessions[r["sid"]].get("slug"))]
    rows = cap_rows(slug_rows, args.top, "其餘", (1, 2, 3), share_of=(4, 3, total))
    tables.append(table("by_slug", f"依專案目錄（slug 原樣，前 {args.top}）", ["slug", "sessions", "reqs", "cost_usd", "cost_share"], rows,
                        "「其餘」列的 sessions 是各 slug 的 session 數相加；一個 session 只屬於一個 slug，所以不會重複。"))
    days = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for r in priced:
        d = days[ctx.day(r["t"])]
        d[0] += 1
        d[1 if r["agent"] is None else 2] += r["_usd"]
    rows = [[k, v[0], v[1] + v[2], v[1], v[2]] for k, v in sorted(days.items())]
    off = ul.fmt_offset(ctx.tz)
    tables.append(table("by_day", f"每日（顯示時區 {off} 的日曆日）", ["day", "reqs", "cost_usd", "main_usd", "subagent_usd"], rows))
    comp_tokens = {"cache_read": "cr", "cache_write_1h": "cw1h", "cache_write_5m": "cw5m", "input": "inp"}
    sums = collections.defaultdict(float)
    toks = collections.defaultdict(int)
    for r in priced:
        if r["_comp"] is None:
            continue
        for k, v in r["_comp"].items():
            sums[k] += v
        for k, f in comp_tokens.items():
            toks[k] += r.get(f) or 0
        toks["output"] += r["_out"]
    comp_total = sum(sums.values())
    rows = [[k, toks[k], sums[k], ratio(sums[k], comp_total)] for k in ("cache_read", "cache_write_1h", "cache_write_5m", "input", "output")]
    tables.append(table("components", "成本組成", ["component", "tokens", "cost_usd", "cost_share"], rows,
                        "以 pricing.json 重算各組成；cw_ttl_known=false 的 cache write 已整筆算在 cache_write_1h。"))
    rows = [[m, n] for m, n in sorted(unpriced.items(), key=lambda kv: (-kv[1], kv[0]))]
    tables.append(table("unpriced", "未計價的 model（成本為 null，不計入總額）", ["model", "reqs"], rows))
    return tables


# ---------------------------------------------------------------- cache


def _gap_scan(groups, ttl_s, win):
    """Consecutive-request gaps inside each group, attributed to the later request's window."""
    buckets = {"le5m": 0, "m5_60": 0, "gt60m": 0}
    over = rewrite = 0
    rewrite_usd = 0.0
    for lst in groups:
        prev = None
        for r in lst:
            if prev is not None and win.has(r["t"]):
                gap = r["_ep"] - prev["_ep"]
                if gap <= 300:
                    buckets["le5m"] += 1
                elif gap <= 3600:
                    buckets["m5_60"] += 1
                else:
                    buckets["gt60m"] += 1
                if gap > ttl_s:
                    over += 1
                    if r["_ctx"] > 0 and (r.get("cw") or 0) / r["_ctx"] >= REWRITE_CW_RATIO:
                        rewrite += 1
                        rewrite_usd += r["_cwusd"]
            prev = r
    return buckets, over, rewrite, rewrite_usd


def cmd_cache(ctx, win, args):
    scopes = (
        ("main", list(ctx.main_reqs.values()), MAIN_TTL_S, ">60m"),
        ("subagent", list(ctx.agent_reqs.values()), SUB_TTL_S, ">5m"),
    )
    gap_rows, rewrite_rows, ttl_rows = [], [], []
    reqs = ctx.reqs_in(win)
    for name, groups, ttl_s, label in scopes:
        b, over, rewrite, usd = _gap_scan(groups, ttl_s, win)
        n = sum(b.values())
        gap_rows.append([name, n, b["le5m"], b["m5_60"], b["gt60m"], ratio(b["gt60m"], n)])
        rewrite_rows.append([name, label, over, rewrite, ratio(rewrite, over), usd])
        sub = [r for r in reqs if (r["agent"] is not None) == (name == "subagent") and (r.get("cw") or 0) > 0]
        unknown = [r for r in sub if not r.get("cw_ttl_known", True)]
        t1h = sum(r.get("cw1h") or 0 for r in sub if r.get("cw_ttl_known", True))
        t5m = sum(r.get("cw5m") or 0 for r in sub if r.get("cw_ttl_known", True))
        ttl_rows.append([name, len(sub), len(unknown), ratio(len(unknown), len(sub)), t1h, t5m, ratio(t5m, t1h + t5m)])
    return [
        table("gaps", "連續 request 間隔分布", ["scope", "intervals", "le5m", "m5_60", "gt60m", "gt60m_share"], gap_rows,
              "main＝每個 session 的主對話 request 序列；subagent＝每個 agent 自己的序列。第一個 request（冷啟動）沒有間隔，不計。間隔歸屬於後一個 request 的窗口。"),
        table("rewrites", "過期重寫（啟發式）", ["scope", "gap_over", "reqs_after_gap", "rewrite_reqs", "rewrite_share", "rewrite_cw_usd"],
              rewrite_rows,
              f"過期重寫＝間隔超過 TTL（main >60m、subagent >5m）且該 request 的 cache write 占 ctx（inp+cw+cr）≥{int(REWRITE_CW_RATIO * 100)}%。"
              "rewrite_cw_usd 是這些 request 付的 cache write 費用（不是可省下的差額）。subagent 的 5m 是假設，實際 TTL 見下表。"),
        table("cw_ttl", "cache write 的 TTL 細分", ["scope", "cw_reqs", "ttl_unknown_reqs", "ttl_unknown_share", "cw1h_tokens", "cw5m_tokens", "cw5m_share"],
              ttl_rows, "ttl_unknown 的 request 沒有 1h／5m 細分，整筆當 1h；cw1h／cw5m tokens 只算有細分的。"),
    ]


# ---------------------------------------------------------------- context


def cmd_context(ctx, win, args):
    main = [r for r in ctx.reqs_in(win) if r["agent"] is None]
    ctxs = [r["_ctx"] for r in main]
    over = sum(1 for c in ctxs if c > 400_000)
    tables = [table("main_ctx", "主對話 ctx（inp+cw+cr）", ["reqs", "median", "p90", "max", "gt400k_share"],
                    [[len(main), ri(median(ctxs)), ri(pct(ctxs, 0.9)), max(ctxs) if ctxs else None, ratio(over, len(main))]])]
    rows = []
    for name, lower, upper in CTX_BUCKETS:
        chosen = [r for r in main if (lower is None or r["_ctx"] >= lower) and (upper is None or r["_ctx"] < upper)]
        rows.append([name, len(chosen), ratio(len(chosen), len(main)), sum(r["_usd"] or 0 for r in chosen)])
    tables.append(table("buckets", "主對話 ctx 分桶（<100K／100–200K／200–400K／>400K）", ["bucket", "reqs", "reqs_share", "cost_usd"], rows,
                        "分桶界線：lt100k＜100,000；100k_200k＜200,000；200k_400k ≤400,000；gt400k ＞400,000。1M context 倍增會造成階梯（caveats）。"))
    firsts = collections.defaultdict(list)
    for aid, lst in ctx.agent_reqs.items():
        if lst and win.has(lst[0]["t"]):
            firsts[ctx.agent_type(ctx.agents[aid]) if aid in ctx.agents else "unknown"].append(lst[0]["_ctx"])
    rows = [[k, len(v), ri(median(v)), ri(pct(v, 0.9))] for k, v in sorted(firsts.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    everything = [c for v in firsts.values() for c in v]
    rows.append(["ALL", len(everything), ri(median(everything)), ri(pct(everything, 0.9))])
    tables.append(table("sub_first_ctx", "subagent 首個 request 的 ctx（固定注入量的代理值）", ["type", "agents", "median", "p90"], rows))
    boundaries = [(sid, t) for sid, s in ctx.sessions.items() for t in s.get("compact_boundaries", []) if win.has(t)]
    tables.append(table("compact", "compact 次數", ["compact_boundaries", "sessions_with_compact"],
                        [[len(boundaries), len({sid for sid, _ in boundaries})]]))
    return tables


# ---------------------------------------------------------------- reports


def cmd_reports(ctx, win, args):
    by_type = collections.defaultdict(list)
    for a in ctx.agents_in(win):
        by_type[ctx.agent_type(a)].append(a)
    rows = []
    for k, lst in sorted(by_type.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ch = [a["final_chars"] for a in lst]
        rows.append([k, len(lst), ri(median(ch)), ri(pct(ch, 0.9)), max(ch), ratio(sum(1 for a in lst if a.get("handback")), len(lst))])
    allc = [a["final_chars"] for lst in by_type.values() for a in lst]
    n_all = sum(len(v) for v in by_type.values())
    rows.append(["ALL", n_all, ri(median(allc)), ri(pct(allc, 0.9)), max(allc) if allc else None,
                 ratio(sum(1 for v in by_type.values() for a in v if a.get("handback")), n_all)])
    tables = [table("final_chars", "subagent 最終報告長度（字元）", ["type", "agents", "median", "p90", "max", "handback_share"], rows,
                    "final_chars 取 SubagentHandback 的 message，沒有則取最後一段 assistant 文字。依 subagent 開始時間歸窗口。")]
    groups = collections.defaultdict(list)
    for sid, tid, call in ctx.calls_in(win):
        res = call.get("result")
        if res and not res.get("is_error"):
            mode = "async" if call.get("first_notification_t") or norm_bool(call.get("background")) == "true" else "sync"
            groups[(call.get("subagent_type") or "-", mode)].append(res["chars"])
    rows = [[k[0], k[1], len(v), ri(median(v)), ri(pct(v, 0.9)), max(v)] for k, v in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    tables.append(table("result_chars", "Agent tool_result 長度（字元，不含 is_error）", ["subagent_type", "mode", "calls", "median", "p90", "max"], rows,
                        "mode=async＝該呼叫收過 task-notification（或帶 run_in_background），其餘為 sync。"
                        "若各列長度都接近固定值（只有數百到一千多字），代表 tool_result 只是啟動／轉交說明、報告本體另行送回，此時以上表 final_chars 當回報長度的代理值。"))
    return tables


# ---------------------------------------------------------------- dispatch


def overlap_groups(ivs):
    """Connected components (>= 2 members) of [start, end) intervals; item = (start, end, tag)."""
    out, cur, cend = [], [], None
    for iv in sorted(ivs, key=lambda x: (x[0], x[1])):
        if cur and iv[0] < cend:
            cur.append(iv)
            cend = max(cend, iv[1])
        else:
            if len(cur) >= 2:
                out.append(cur)
            cur, cend = [iv], iv[1]
    if len(cur) >= 2:
        out.append(cur)
    return out


def max_concurrency(group):
    events = []
    for iv in group:
        events.append((iv[0], 1))
        events.append((iv[1], -1))
    events.sort(key=lambda e: (e[0], e[1]))  # an end sorts before a start at the same instant
    cur = best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best


def cmd_dispatch(ctx, win, args):
    calls = ctx.calls_in(win)
    combos = collections.Counter()
    for sid, tid, c in calls:
        combos[(c.get("subagent_type"), c.get("model"), c.get("effort"), c.get("isolation"), norm_bool(c.get("background")))] += 1
    rows = [list(k) + [n] for k, n in sorted(combos.items(), key=lambda kv: (-kv[1], str(kv[0])))]
    tables = [table("combos", "Agent 呼叫參數組合", ["subagent_type", "model", "effort", "isolation", "background", "calls"], rows,
                    "model／effort／isolation／background 為空（-）＝呼叫沒帶該參數。")]
    errors = sum(1 for _, _, c in calls if (c.get("result") or {}).get("is_error"))
    no_result = sum(1 for _, _, c in calls if not c.get("result"))
    tables.append(table("calls", "呼叫總數與錯誤", ["calls", "result_is_error", "no_result", "with_notification"],
                        [[len(calls), errors, no_result, sum(1 for _, _, c in calls if c.get("notification"))]]))
    status = collections.Counter((c.get("notification") or {}).get("status") or "(none)" for _, _, c in calls)
    tables.append(table("notification_status", "最後一筆 task-notification 的 status", ["status", "calls"],
                        [[k, n] for k, n in sorted(status.items(), key=lambda kv: (-kv[1], kv[0]))]))
    per_sid = collections.defaultdict(list)
    unterminated = 0
    for sid, tid, c in calls:
        end, unterm = ctx.call_end(sid, c)
        unterminated += unterm
        per_sid[sid].append((ep(c["t"]), end, c.get("subagent_type") or "-"))
    groups = []
    for sid, ivs in per_sid.items():
        for g in overlap_groups(ivs):
            groups.append((sid, g, max_concurrency(g)))
    tables.append(table("parallelism", "平行度（同 session 的在途區間 [Agent 呼叫, 第一筆 notification／tool_result) 重疊）",
                        ["sessions_with_calls", "calls", "parallel_groups", "calls_in_groups", "max_concurrency", "unterminated_calls"],
                        [[len(per_sid), len(calls), len(groups), sum(len(g) for _, g, _ in groups),
                          max((m for _, _, m in groups), default=0), unterminated]],
                        "parallel_groups＝≥2 個呼叫在途區間連通的群組數（含串連的修正輪）。沒收到 notification／tool_result 的呼叫算到 session 最後一個事件，會高估重疊。不分唯讀或寫入型。"))
    rows = []
    for sid, g, m in sorted(groups, key=lambda x: (-x[2], -len(x[1]), x[0]))[: args.top]:
        start = dt.datetime.fromtimestamp(min(iv[0] for iv in g), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        types = collections.Counter(iv[2] for iv in g)
        rows.append([sid[:8], ctx.sessions[sid].get("slug"), start, len(g), m,
                     ", ".join(f"{k}x{n}" for k, n in sorted(types.items(), key=lambda kv: (-kv[1], kv[0])))])
    tables.append(table("top_groups", f"最大的平行群組（前 {args.top}）", ["sid", "slug", "start_utc", "calls", "max_concurrency", "types"], rows))
    return tables


# ---------------------------------------------------------------- controller


def worker_windows(ctx, sid):
    """[(worker_return_epoch, next_verifier_dispatch_epoch|inf)] for one session (heuristic)."""
    calls = list(ctx.sessions[sid]["agent_calls"].values())
    verifier_ts = sorted(ep(c["t"]) for c in calls if "verifier" in (c.get("subagent_type") or ""))
    out = []
    for c in calls:
        if "worker" not in (c.get("subagent_type") or ""):
            continue
        end, _ = ctx.call_end(sid, c)   # a worker with no notification or result "returns" at the session's last event: nothing follows
        nxt = next((v for v in verifier_ts if v > end), float("inf"))
        out.append((end, nxt))
    return out


def cmd_controller(ctx, win, args):
    per = collections.defaultdict(lambda: collections.Counter())
    sessions_seen = collections.defaultdict(set)
    for sid, s in ctx.sessions.items():
        slug = s.get("slug")
        wins = worker_windows(ctx, sid)
        calls = [c for c in s["agent_calls"].values() if win.has(c["t"])]
        edits = [e for e in s["edits"] if win.has(e["t"])]
        bashes = [b for b in s["bash_writes_heuristic"] if win.has(b["t"])]
        if not (calls or edits or bashes):
            continue
        sessions_seen[slug].add(sid)
        per[slug]["calls"] += len(calls)
        per[slug]["edits"] += len(edits)
        per[slug]["bash"] += len(bashes)
        per[slug]["edits_after_worker"] += sum(1 for e in edits if any(a < ep(e["t"]) < b for a, b in wins))
        per[slug]["bash_after_worker"] += sum(1 for b in bashes if any(a < ep(b["t"]) < c for a, c in wins))
    rows = []
    total = collections.Counter()
    for slug, c in sorted(per.items(), key=lambda kv: (-(kv[1]["edits"] + kv[1]["bash"]), str(kv[0]))):
        rows.append([slug, len(sessions_seen[slug]), c["calls"], c["edits"], c["bash"], None,
                     c["edits_after_worker"], c["bash_after_worker"]])
        total.update(c)
    rows = cap_rows(rows, args.top, "其餘", (1, 2, 3, 4, 6, 7))
    for row in rows:
        row[5] = ratio(row[3] + row[4], row[2])
    seen = sum(len(v) for v in sessions_seen.values())
    rows.append(["ALL", seen, total["calls"], total["edits"], total["bash"], ratio(total["edits"] + total["bash"], total["calls"]),
                 total["edits_after_worker"], total["bash_after_worker"]])
    cols = ["slug", "sessions", "agent_calls", "main_edits", "bash_writes_heuristic", "direct_per_call",
            "edits_after_worker_heuristic", "bash_writes_after_worker_heuristic"]
    return [table("controller", f"主對話直接改檔 vs 派工（逐專案目錄，前 {args.top}）", cols, rows,
                  "main_edits＝主對話的 Edit／Write／MultiEdit／NotebookEdit。bash_writes_heuristic 是 regex 啟發式（會有誤判與漏判）。"
                  "after_worker_heuristic＝發生在某個 worker 類（type 含 worker）subagent 交回之後、下一個 verifier 類派出之前（沒有後續 verifier 則到 session 結尾）的次數，同一筆只算一次。"
                  "direct_per_call＝(main_edits+bash_writes)/agent_calls。")]


# ---------------------------------------------------------------- verifier


def verdict_of(a):
    m = VERDICT_RE.search((a.get("final_head") or "")[:400])
    return m.group(1) if m else "(unclassified)"


def cmd_verifier(ctx, win, args):
    groups = collections.defaultdict(list)
    for a in ctx.agents_in(win):
        if "verifier" in ctx.agent_type(a):
            groups[verdict_of(a)].append(ctx.agent_cost.get(a["id"], 0.0))
    n_all = sum(len(v) for v in groups.values())
    total = sum(sum(v) for v in groups.values())
    order = ("CONVERGED", "PROSE-ONLY", "OPEN", "INCONCLUSIVE", "(unclassified)")
    rows = [[k, len(groups[k]), ratio(len(groups[k]), n_all), sum(groups[k]), median(groups[k])] for k in order if k in groups]
    rows.append(["ALL", n_all, ratio(n_all, n_all), total, median([c for v in groups.values() for c in v])])
    return [table("verdicts", "verifier 判定分布（啟發式）", ["verdict_heuristic", "agents", "agents_share", "cost_usd", "median_cost_usd"], rows,
                  "啟發式：type 含 verifier 的 subagent，取 final_head 前 400 字第一個符合 CONVERGED／PROSE-ONLY／INCONCLUSIVE／OPEN 的詞；"
                  "找不到為 (unclassified)。成本是該 subagent 全部 request，依開始時間歸窗口。")]


# ---------------------------------------------------------------- agents


def cmd_agents(ctx, win, args):
    by_type = collections.defaultdict(list)
    for a in ctx.agents_in(win):
        by_type[ctx.agent_type(a)].append(a)
    rows = []
    for k, lst in sorted(by_type.items(), key=lambda kv: (-sum(ctx.agent_cost.get(a["id"], 0.0) for a in kv[1]), kv[0])):
        reqs = [a["requests"] for a in lst]
        tools = [sum(a.get("tools", {}).values()) for a in lst]
        wall = [(ep(a["last"]) - ep(a["first"])) / 60 for a in lst]
        usd = [ctx.agent_cost.get(a["id"], 0.0) for a in lst]
        tok = [n["subagent_tokens"] for n in (ctx.agent_note(a) for a in lst) if n and n.get("subagent_tokens") is not None]
        rows.append([k, len(lst), ri(median(reqs)), ri(pct(reqs, 0.9)), ri(median(tools)), ri(pct(tools, 0.9)),
                     median(wall), pct(wall, 0.9), sum(usd), median(usd), pct(usd, 0.9), ri(median(tok))])
    cols = ["type", "agents", "reqs_median", "reqs_p90", "tools_median", "tools_p90", "wall_min_median", "wall_min_p90",
            "cost_usd", "cost_median_usd", "cost_p90_usd", "notif_tokens_median"]
    return [table("agents", "每種 subagent 的規模（依總成本排序）", cols, rows,
                  "依 subagent 開始時間歸窗口；wall＝last−first（被續用的 agent 含等待時間）。tools＝工具呼叫總數（含 SubagentHandback）。"
                  "notif_tokens_median＝task-notification 的 subagent_tokens 中位數（killed 或沒有 usage 的不算）。")]


# ---------------------------------------------------------------- sessions


def cmd_sessions(ctx, win, args):
    agg = collections.defaultdict(lambda: [0, 0.0])
    for r in ctx.reqs_in(win):
        a = agg[r["sid"]]
        a[0] += 1
        a[1] += r["_usd"] or 0.0
    rows = []
    for sid, (n, usd) in sorted(agg.items(), key=lambda kv: (-kv[1][1], kv[0]))[: args.top]:
        s = ctx.sessions[sid]
        main_ctx = [r["_ctx"] for r in ctx.main_reqs.get(sid, []) if win.has(r["t"])]
        calls = sum(1 for c in s["agent_calls"].values() if win.has(c["t"]))
        humans = sum(1 for h in s["humans"] if h["kind"] in ("human", "ask_answer") and win.has(h["t"]))
        rows.append([sid[:8], s.get("slug"), (s.get("title") or "")[:40] or None, usd, n, ri(median(main_ctx)), calls, humans])
    return [table("sessions", f"成本最高的 session（前 {args.top}）",
                  ["sid", "slug", "title", "cost_usd", "reqs", "main_ctx_median", "agent_calls", "human_msgs"], rows,
                  "cost_usd 含該 session 的 subagent。human_msgs 只算 kind 為 human 與 ask_answer（meta、command、peer、notification 不是人類輸入）。")]


# ---------------------------------------------------------------- weekly (rules-effect review)

REVIEW_RE = re.compile(r"\bcode-review\b|\breview\b|審查|\bfresh\b", re.I)
DELTA_RE = re.compile(r"delta", re.I)
MECH_CLOSE = "機械結案"
CLAUSE_SPLIT_RE = re.compile(r"[。；;\n]")
MECH_NEGATED_RE = re.compile(r"(?:不是|不屬於?|並非|非|不能|不可|無法)" + MECH_CLOSE)
CONDITIONAL_RE = re.compile(r"如果|若|的話")
PRIOR_ROUND_RE = re.compile(r"(?:上一?輪|前一輪|第\s*\d+\s*輪)[^。；\n]{0,60}?(?:OPEN|FAIL|INCONCLUSIVE)")
HANDOFF_CARD_TOKENS = 5000  # assumed size of a handoff card read by the takeover session


def is_fork(ctx, a):
    """A code-review fork: a general-purpose subagent with no Agent call in the main thread whose description is
    '/code-review ...' (or empty)."""
    desc = (a.get("description") or "").strip()
    return (a["id"] not in ctx.call_by_agent and ctx.agent_type(a) == "general-purpose"
            and (not desc or desc.startswith("/code-review")))


def fork_parents(ctx):
    """{fork agent id: parent agent id}. The built-in code-review skill usually forks a general-purpose subagent that has
    no Agent call in the main thread. A fork is folded into a general-purpose Agent call of the same session that was in
    flight when the fork started (call time .. first notification); among several, the earliest one without a fork yet,
    else the latest started. A fork with no call in flight (e.g. /code-review typed in the main thread) stays unfolded."""
    calls = collections.defaultdict(list)  # sid -> [(start_ep, end_ep, agent_id)]
    for sid, s in ctx.sessions.items():
        for c in s["agent_calls"].values():
            aid = c.get("agent_id")
            if aid and aid in ctx.agents and ctx.agent_type(ctx.agents[aid]) == "general-purpose":
                calls[sid].append((ep(c["t"]), ctx.call_end(sid, c)[0], aid))
    for lst in calls.values():
        lst.sort()
    out, has_fork = {}, set()
    for a in sorted((a for a in ctx.agents.values() if is_fork(ctx, a)), key=lambda a: a["first"]):
        t = ep(a["first"])
        live = [aid for st, en, aid in calls.get(a["sid"], []) if st <= t <= en]
        if not live:
            continue
        fresh = [aid for aid in live if aid not in has_fork]
        parent = fresh[0] if fresh else live[-1]
        out[a["id"]] = parent
        has_fork.add(parent)
    return out


def says_mech_close(head):
    """True when some clause of a verifier's final head offers 機械結案 outright: a negated clause ('不是機械結案') or a
    conditional one ('如果只改 X，可機械結案') does not count."""
    return any(MECH_CLOSE in c and not MECH_NEGATED_RE.search(c) and not CONDITIONAL_RE.search(c)
               for c in CLAUSE_SPLIT_RE.split(head or ""))


def rechecks_prior_round(prompt):
    """True when a delta brief points back at the previous round's verdict ('上一輪 OPEN 的唯一 FAIL'), i.e. it re-verifies
    the same findings rather than the session's next change. Descriptions are too short to tell the two apart."""
    return bool(PRIOR_ROUND_RE.search(prompt or ""))


def agent_family(ctx, aid):
    fams = collections.Counter(ul.family(r.get("model")) for r in ctx.agent_reqs.get(aid, []))
    return fams.most_common(1)[0][0] if fams else "unknown"


def prs_in(prs, win):
    if prs is None:
        return None
    n = 0
    for p in prs:
        t = p.get("mergedAt") or p.get("closedAt") if isinstance(p, dict) else None
        if t and win.has(ul.fmt_ts(ul.parse_ts(t))):
            n += 1
    return n


def cmd_weekly(ctx, win, args):
    reqs = ctx.reqs_in(win)
    usd = sum(r["_usd"] or 0.0 for r in reqs)
    hours = len({int(r["_ep"] // 600) for r in reqs}) / 6
    npr = prs_in(args.prs, win)
    tokens = sum(r["_ctx"] + ((r.get("out_est") if ctx.corrected and r.get("out_est") is not None else r.get("out_raw")) or 0) for r in reqs)
    calls = ctx.calls_in(win)
    main = [r for r in reqs if r["agent"] is None]
    main_usd = sum(r["_usd"] or 0.0 for r in main)

    def per_pr(x):
        return ratio(x, npr) if npr else None

    tables = [table("summary", "成本與產出", ["cost_usd", "active_hours", "merged_prs", "per_hour_usd", "prs_per_hour", "per_pr_usd",
                                         "tokens_per_pr", "reqs_per_pr", "agent_calls_per_pr", "main_per_pr_usd", "subagent_per_pr_usd"],
                    [[usd, hours, npr, ratio(usd, hours), ratio(npr, hours) if npr is not None else None, per_pr(usd),
                      ri(per_pr(tokens)), per_pr(len(reqs)), per_pr(len(calls)), per_pr(main_usd), per_pr(usd - main_usd)]],
                    "active_hours＝窗口內全部 request 落在幾個 10 分鐘 bucket ÷ 6。merged_prs 來自 --prs（gh search prs 的 JSON，"
                    "按 mergedAt，沒有時用 closedAt）；沒給 --prs 時 PR 相關欄位為空，--project 等篩選不會套到 PR 上，PR 清單要自己給同範圍。"
                    "tokens＝inp+cw+cr+output（未定價 model 也算）。")]

    thr = args.ctx_threshold
    ctxs = [r["_ctx"] for r in main]
    by_sid = collections.defaultdict(list)
    for r in main:
        by_sid[r["sid"]].append(r)
    crossed = [n for n in (sum(1 for r in lst if r["_ctx"] >= thr) for lst in by_sid.values()) if n]
    above_usd = sum(r["_usd"] or 0.0 for r in main if r["_ctx"] >= thr)
    tables.append(table("main_ctx", f"主對話 context（門檻 {thr:,}）",
                        ["reqs", "median", "p90", "gt400k_share", "max", "sessions_crossed", "reqs_at_or_above_median", "at_or_above_cost_share"],
                        [[len(main), ri(median(ctxs)), ri(pct(ctxs, 0.9)), ratio(sum(1 for c in ctxs if c > 400_000), len(ctxs)),
                          max(ctxs) if ctxs else None, len(crossed), median(crossed), ratio(above_usd, main_usd)]],
                        "ctx＝inp+cw+cr。sessions_crossed＝至少一個主對話 request 的 ctx ≥ 門檻的 session；"
                        "reqs_at_or_above_median＝這些 session 裡 ctx ≥ 門檻的 request 數中位。"))

    vers = sorted((a for a in ctx.agents_in(win) if "verifier" in ctx.agent_type(a)), key=lambda a: a["first"])
    first = [a for a in vers if not DELTA_RE.search(a.get("description") or "")]
    by_s = collections.defaultdict(list)
    for a in vers:
        by_s[a["sid"]].append(a)
    mech = sum(1 for lst in by_s.values() for p, q in zip(lst, lst[1:])
               if says_mech_close(p.get("final_head")) and DELTA_RE.search(q.get("description") or "")
               and rechecks_prior_round(ctx.agent_call(q).get("prompt_head")))
    dist = collections.Counter(verdict_of(a) for a in vers)
    first_open = sum(1 for a in first if verdict_of(a) == "OPEN")
    tables.append(table("verifier_rounds", "verifier 判定與輪次（啟發式）",
                        ["agents", "converged_share", "prose_only_share", "open_share", "inconclusive_share",
                         "first_round", "first_round_open", "first_round_open_share", "mech_close_then_delta"],
                        [[len(vers), ratio(dist["CONVERGED"], len(vers)), ratio(dist["PROSE-ONLY"], len(vers)), ratio(dist["OPEN"], len(vers)),
                          ratio(dist["INCONCLUSIVE"], len(vers)), len(first), first_open, ratio(first_open, len(first)), mech]],
                        "啟發式：判定同 verifier 子命令的 regex；first_round＝description 不含 delta；mech_close_then_delta＝同 session "
                        "相鄰兩次 verifier，前一次 final_head 有一句直接說可「機械結案」（否定句與「如果／若／的話」條件句不算）、"
                        "下一次 description 含 delta，且其 brief 前 600 字在「上一輪／前一輪／第 N 輪」後 60 字內提到 OPEN／FAIL／INCONCLUSIVE。"))

    forks = fork_parents(ctx)
    fork_usd = collections.defaultdict(float)
    for f, p in forks.items():
        fork_usd[p] += ctx.agent_cost.get(f, 0.0)
    groups = collections.defaultdict(list)  # (kind, family) -> [(sid, usd)]
    for sid, _tid, c in calls:
        aid = c.get("agent_id")
        if not aid or aid not in ctx.agents:
            continue
        stype = ctx.agent_type(ctx.agents[aid])
        if "verifier" in stype:
            kind = "verifier"
        elif stype == "general-purpose" and REVIEW_RE.search((c.get("description") or "") + " " + (c.get("prompt_head") or "")):
            kind = "review"
        else:
            continue
        groups[(kind, agent_family(ctx, aid))].append((sid, ctx.agent_cost.get(aid, 0.0) + fork_usd[aid]))
    rows = []
    for (kind, fam), lst in sorted(groups.items()):
        costs = [u for _, u in lst]
        per_s = list(collections.Counter(s for s, _ in lst).values())
        rows.append([kind, fam, len(lst), per_pr(len(lst)), sum(costs), per_pr(sum(costs)), median(costs), ratio(sum(costs), len(costs)),
                     median(per_s), sum(1 for n in per_s if n >= 3), len(per_s)])
    tables.append(table("reviews", "verifier 與 fresh review 每次成本（fork 子 agent 併回父呼叫）",
                        ["kind", "family", "calls", "calls_per_pr", "cost_usd", "per_pr_usd", "median_usd", "mean_usd",
                         "calls_per_session_median", "sessions_ge3", "sessions"], rows,
                        "依主對話 Agent 呼叫時間歸窗口。review＝general-purpose 且 description／prompt 前段含 code-review、review、審查或 fresh（啟發式）。"
                        "內建 code-review skill 通常會再 fork 沒有 Agent 呼叫的 general-purpose 子 agent，它們的成本併進父呼叫；"
                        "agents 子命令仍把它算成獨立 agent。family＝該 agent 最多 request 的 model family。"))

    starts = [lst[0]["_ctx"] for sid, lst in by_sid.items() if win.has(ctx.sessions[sid].get("first") or "")]
    base = (median(starts or [lst[0]["_ctx"] for lst in by_sid.values()]) or 0) + HANDOFF_CARD_TOKENS
    rows = []
    for t in args.sim_thresholds:
        save = hand = 0.0
        n, after = 0, []
        for lst in by_sid.values():
            i = next((k for k, r in enumerate(lst) if r["_ctx"] >= t), None)
            if i is None:
                continue
            n += 1
            after.append(len(lst) - i)
            c0 = lst[i]["_ctx"]
            p0 = ul.price_for(lst[i].get("model"), ctx.pricing)
            if p0:
                hand += base * p0["input"] * ctx.mult["1h"] / 1e6
            for r in lst[i + 1:]:
                pr = ul.price_for(r.get("model"), ctx.pricing)
                if pr:
                    save += max(min(c0, r["_ctx"]) - base, 0) * pr["cache_read"] / 1e6
        rows.append([t, n, median(after), save, hand, save - hand, ratio(save - hand, main_usd)])
    tables.append(table("handoff_sim", f"接手門檻模擬（base＝窗口內開始的 session 首個主對話 request ctx 中位＋{HANDOFF_CARD_TOKENS:,}＝{ri(base):,}）",
                        ["threshold", "sessions", "reqs_after_median", "gross_usd", "handoff_usd", "net_usd", "net_main_share"], rows,
                        "粗估模型：在第一個 ctx ≥ 門檻的 request 換新 session，之後每個 request 的 ctx 少掉（跨過時的 ctx − base），"
                        "省下的部分照 cache read 計價，扣掉一次 base 的 1h cache write。每個 session 只換手一次（低估）、"
                        "沒算新 session 重讀檔案的成本（高估），兩者方向相反，不是嚴格上界；"
                        "已經有接手規則的窗口裡，跨過該門檻的 session 會被截斷，模擬要用規則上線前的窗口。"))
    return tables


# ---------------------------------------------------------------- escapes (merged PRs later fixed or reverted)

PR_URL_RE = re.compile(r"github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)", re.I)
GH_REVERT_RE = re.compile(r'^\s*Revert\s+"', re.I)                     # GitHub's "Revert" button
TICKET_TAG_RE = re.compile(r"^\s*(\[[^\]]*\]\s*)+")                     # leading [ABC-1][ABC-2] tags
CC_TYPE_RE = re.compile(r"^\s*([A-Za-z]+)(\([^)]*\))?!?\s*:")           # conventional-commit type
BRANCH_TYPE_RE = re.compile(r"^(?:[^/]+/)?(fix|hotfix|bugfix|revert|feat|feature|chore|docs|ci|build|test|refactor|perf|content|release)/", re.I)
GH_REVERT_BRANCH_RE = re.compile(r"^revert-\d+-")                       # branch GitHub creates for a revert
REVERT_WORD_RE = re.compile(r"撤回|退回|還原|回退|撤銷|復原|\brevert(s|ed)?\b|\broll\s*back\b|\brollback\b", re.I)
FIX_WORD_RE = re.compile(r"修正|修復|修掉|修補|修好|更正|\bhot\s*fix\b|\bbug\s*fix\b|\bfix(es|ed)?\b", re.I)
FIX_TYPES, REVERT_TYPES = {"fix", "hotfix", "bugfix"}, {"revert"}
CC_TYPES = FIX_TYPES | REVERT_TYPES | {"feat", "feature", "chore", "docs", "ci", "build", "test", "tests", "refactor", "perf", "style",
                                      "release", "deps"}  # 'iOS: fix crash' is an area prefix, not a type
FRESH_COVERAGE = ("verifier+code-review", "verifier", "code-review", "none", "unknown")


def pr_key(p):
    """'owner/repo#N' (lower-case) from the PR url, else from repository + number; None when neither is there."""
    m = PR_URL_RE.search(p.get("url") or "")
    if m:
        return f"{m.group(1).lower()}#{int(m.group(2))}"
    repo = p.get("repository")
    if isinstance(repo, dict):
        repo = repo.get("nameWithOwner")
    if repo and p.get("number") is not None:
        return f"{str(repo).lower()}#{int(p['number'])}"
    return None


def pr_nature(title, branch):
    """('revert'|'fix'|'other'|'unknown', basis). Order: GitHub revert title, conventional type in the title (after
    leading [TICKET] tags), branch type prefix, then fix / revert words in the title (any language listed in the
    regexes). A PR with none of these signals is 'unknown' and is never counted as a fix."""
    title, branch = title or "", branch or ""
    if GH_REVERT_RE.match(title):
        return "revert", "title:github-revert"
    m = CC_TYPE_RE.match(TICKET_TAG_RE.sub("", title))
    if m and m.group(1).lower() in CC_TYPES:
        t = m.group(1).lower()
        return ("revert" if t in REVERT_TYPES else "fix" if t in FIX_TYPES else "other"), f"title:{t}"
    if GH_REVERT_BRANCH_RE.match(branch):
        return "revert", "branch:revert-N"
    m = BRANCH_TYPE_RE.match(branch)
    if m:
        t = m.group(1).lower()
        return ("revert" if t in REVERT_TYPES else "fix" if t in FIX_TYPES else "other"), f"branch:{t}"
    if re.match(r"^\s*(Merge|Release)\b", title, re.I):
        return "other", "title:merge-or-release"
    if REVERT_WORD_RE.search(title):
        return "revert", "title:word"
    if FIX_WORD_RE.search(title):
        return "fix", "title:word"
    return "unknown", "-"


def cites(text, key):
    """True when text names the PR `key` ('owner/repo#N'): a bare '#N' (not part of '#N0' or 'other/repo#N'),
    'owner/repo#N' (GitHub's 'Reverts owner/repo#N' body) or its pull URL."""
    repo, n = key.split("#")
    return bool(re.search(rf"(?<![A-Za-z0-9_/])#{n}(?!\d)", text)   # '修正#5' cites #5 (Python's \w includes Han)
                or re.search(rf"(?<![\w.-]){re.escape(repo)}(?:#|/pull/){n}(?!\d)", text, re.I))


def norm_prs(raw):
    """Merged PRs from gh JSON -> {key: pr}. Duplicates (overlapping fetches) keep the first copy."""
    out = {}
    for p in raw:
        key = pr_key(p)
        t = p.get("mergedAt") or p.get("closedAt")
        if not key or not t:
            continue
        files = p.get("files")
        paths = None if files is None else {f.get("path") if isinstance(f, dict) else f for f in files} - {None}
        author = p.get("author")
        out.setdefault(key, {
            "key": key, "repo": key.split("#")[0], "merged": ul.fmt_ts(ul.parse_ts(t)), "title": p.get("title") or "",
            "branch": p.get("headRefName") or "", "author": author.get("login") if isinstance(author, dict) else author,
            "files": paths, "nature": pr_nature(p.get("title"), p.get("headRefName")),
            "text": (p.get("title") or "") + "\n" + (p.get("body") or ""), "has_body": "body" in p,
        })
    return out


def fresh_coverage(ctx, key, merged, links):
    """Fresh acceptance a PR got before its merge, from the sessions whose pr-link points at it. Only sessions that
    link this PR alone can attribute a call to it; a verifier / review call in a session that links several PRs might
    be for any of them, so that case is 'unknown'. 'none' means no verifier or review call at all before the merge in
    any linking session."""
    sids = links.get(key) or []
    if not sids:
        return "unknown"
    kinds_by_sid = {}
    for sid in sids:
        kinds = set()
        for c in ctx.sessions[sid]["agent_calls"].values():
            if c["t"] > merged:
                continue
            aid = c.get("agent_id")
            stype = ctx.agent_type(ctx.agents[aid]) if aid in ctx.agents else (c.get("subagent_type") or "")
            if "verifier" in stype:
                kinds.add("verifier")
            elif stype == "general-purpose" and REVIEW_RE.search((c.get("description") or "") + " " + (c.get("prompt_head") or "")):
                kinds.add("code-review")
        for a in ctx.agents.values():
            if a["sid"] == sid and a["first"] <= merged and is_fork(ctx, a):
                kinds.add("code-review")  # a code-review fork, folded into any in-flight call or typed in the main thread
        kinds_by_sid[sid] = kinds
    dedicated = [sid for sid in sids if len(ctx.sessions[sid].get("prs") or []) == 1]
    found = set().union(*(kinds_by_sid[s] for s in dedicated)) if dedicated else set()
    if not found and any(kinds_by_sid[s] for s in sids if s not in dedicated):
        return "unknown"
    if not found:
        return "none"
    return "+".join(k for k in ("verifier", "code-review") if k in found)


def cmd_escapes(ctx, win, args):
    prs = norm_prs(args.prs or [])
    days = args.fix_days
    span = dt.timedelta(days=days)
    as_of = args.as_of
    links = collections.defaultdict(list)
    for sid, s in ctx.sessions.items():
        for u in s.get("prs") or []:
            k = pr_key({"url": u})
            if k:
                links[k].append(sid)
    origs = sorted((p for p in prs.values() if win.has(p["merged"]) and (not args.author or p["author"] in args.author)),
                   key=lambda p: (p["merged"], p["key"]))
    by_repo = collections.defaultdict(list)
    for p in prs.values():
        by_repo[p["repo"]].append(p)
    pairs, unknown_pairs, overlap_only, cov_of = [], [], 0, {}
    followups_no_files = set()
    for o in origs:
        end = ul.fmt_ts(ul.parse_ts(o["merged"]) + span)
        o["censored"] = end > as_of
        cov_of[o["key"]] = fresh_coverage(ctx, o["key"], o["merged"], links)
        if not o["files"]:
            continue
        for f in by_repo[o["repo"]]:
            if f["key"] == o["key"] or not (o["merged"] < f["merged"] <= end):
                continue
            if not f["files"]:
                followups_no_files.add(f["key"])
                continue
            shared = sorted(o["files"] & f["files"])
            if not shared:
                continue
            if not cites(f["text"], o["key"]):
                overlap_only += f["nature"][0] in ("fix", "revert")
                continue
            row = (o, f, shared, (ul.parse_ts(f["merged"]) - ul.parse_ts(o["merged"])).total_seconds() / 86400)
            if f["nature"][0] in ("fix", "revert"):
                pairs.append(row)
            elif f["nature"][0] == "unknown":
                unknown_pairs.append(row)
    hit = {o["key"] for o, *_ in pairs}
    mature = [o for o in origs if not o["censored"]]
    hit_mature = [o for o in mature if o["key"] in hit]
    no_files = sum(1 for o in origs if not o["files"])
    if not origs:
        status = "無法計算：窗口內沒有原 PR"
    elif not any(p["has_body"] for p in prs.values()):
        status = "無法計算：--prs 沒有 body 欄位，判不出後續 PR 有沒有引用原 PR"
    elif not any(p["files"] for p in prs.values()):
        status = "無法計算：--prs 沒有 files，判不出共用檔"
    elif not mature:
        status = f"成熟比率無法計算：每個原 PR 都還沒滿 {days} 天"
    else:
        status = "ok"
    share = ratio(len(hit), len(origs)) if status == "ok" or status.startswith("成熟") else None
    mature_share = ratio(len(hit_mature), len(mature)) if status == "ok" else None
    tables = [table("summary", f"漏網：merge 後 {days} 天內被引用它的 fix／revert PR 改到同一批檔的原 PR",
                    ["status", "original_prs", "with_fix", "with_fix_share", "mature_prs", "mature_with_fix", "mature_with_fix_share",
                     "censored_prs", "no_file_list", "followups_no_file_list", "overlap_only_pairs", "unknown_nature_pairs"],
                    [[status, len(origs), len(hit), share, len(mature), len(hit_mature), mature_share,
                      len(origs) - len(mature), no_files, len(followups_no_files), overlap_only, len(unknown_pairs)]],
                    f"原 PR＝--prs 裡 merge 時間在窗口內的 PR（有 --author 時只算該作者）。後續修正＝同 repo、merge 在原 PR 之後 {days} 天內、"
                    "與原 PR 至少共用一個檔、標題或描述引用原 PR（#N、owner/repo#N 或 PR 網址）、性質判為 fix 或 revert 的 PR（作者不限）。"
                    f"mature＝merge 後已滿 {days} 天（以 --as-of {as_of} 為準）；censored 的原 PR 觀察期不滿，with_fix_share 會偏低，看比率以 mature 為準。"
                    "no_file_list＝沒有檔案清單的原 PR（仍在分母、配不到後續 PR）；followups_no_file_list＝落在某個原 PR 期限內、"
                    "但沒有檔案清單而無法配對的後續候選 PR。overlap_only_pairs＝共用檔且是 fix／revert、但沒有引用原 PR 的配對數，不計入（只靠共用檔時多半是同一批檔被別的缺陷修到）。"
                    "unknown_nature_pairs＝共用檔又引用原 PR、但性質判不出的配對數，不計入，列在最後一張表給人看。引用也可能只是順帶提到，命中要人工判。")]
    cov_rows = []
    for c in FRESH_COVERAGE:
        os_ = [o for o in mature if cov_of[o["key"]] == c]
        h = sum(1 for o in os_ if o["key"] in hit)
        cov_rows.append([c, len(os_), h, ratio(h, len(os_))])
    tables.append(table("by_coverage", "成熟原 PR 依 merge 前的 fresh 驗收涵蓋分組（沒被修的原 PR 就是對照組）",
                        ["fresh_coverage", "mature_prs", "with_fix", "with_fix_share"], cov_rows,
                        "涵蓋由 session 的 pr-link 與 merge 前的 Agent 呼叫推：只連這一個 PR 的 session 裡有 verifier／review 呼叫才算；"
                        "只有連多個 PR 的 session 有呼叫時判不出是驗哪個 PR，寫 unknown；沒有 session 連到這個 PR 也是 unknown；"
                        "所有連到它的 session 在 merge 前都沒有 verifier／review 呼叫才寫 none。review 的判定同 weekly（啟發式）。"))
    rows = [[o["key"], ctx.day(o["merged"]), o["censored"], cov_of[o["key"]], o["title"][:60], f["key"], f["nature"][0],
             f["nature"][1], f["title"][:60], len(shared), gap, ""] for o, f, shared, gap in pairs]
    tables.append(table("escapes", "命中清單（一個原 PR 可能對到多個後續 PR）",
                        ["original", "original_merged", "censored", "fresh_coverage", "original_title", "followup", "nature",
                         "nature_basis", "followup_title", "shared_files", "gap_days", "should_catch"], rows,
                        "should_catch 留給人填（verifier／code-review／測試／CI／無法事前抓），腳本不判。censored＝原 PR 還沒滿觀察期。"
                        "nature_basis：title:github-revert／title:<type>／branch:<type>／branch:revert-N／title:word。"))
    urows = [[o["key"], f["key"], f["title"][:60], f["branch"][:40], len(shared), gap] for o, f, shared, gap in unknown_pairs]
    tables.append(table("unknown_nature", "判不出性質的候選（不計入比率）",
                        ["original", "followup", "followup_title", "followup_branch", "shared_files", "gap_days"], urows,
                        "標題沒有 conventional type、分支沒有類型前綴、標題也沒有修正／撤回類字眼。要算進來就人工改判。"))
    return tables


# ---------------------------------------------------------------- driver

CMD_FUNCS = {
    "cost": cmd_cost, "cache": cmd_cache, "context": cmd_context, "reports": cmd_reports, "dispatch": cmd_dispatch,
    "controller": cmd_controller, "verifier": cmd_verifier, "agents": cmd_agents, "sessions": cmd_sessions,
    "weekly": cmd_weekly, "escapes": cmd_escapes,
}

CMD_NOTES = {
    "cache": ["過期重寫與 TTL 假設是啟發式；沒有細分的 cache write 一律當 1h。"],
    "controller": ["bash 寫檔與『worker 交回後』都是啟發式，引用時要標示。"],
    "verifier": ["verifier 判定由 final_head 的 regex 抓出，是啟發式，不等於 verifier 實際結論欄位。"],
    "dispatch": ["平行度由 Agent 呼叫到第一筆通知（或 tool_result）的區間推得；在途判定是近似值。"],
    "weekly": ["verifier 判定、首輪、機械結案後 delta、review 分類與 fork 歸屬都是啟發式；接手門檻模擬是粗估。"],
    "escapes": ["fix／revert 判定、共用檔即相關、驗收涵蓋與 review 分類都是啟發式；命中要人工判是否真的在修原 PR 的缺陷。"],
}


def make_report(data, command, *, tz=None, windows=None, projects=(), exclude=(), corrected=False, top=10, data_path=None,
                exclude_projects=(), prs=None, ctx_threshold=300_000, sim_thresholds=(200_000, 300_000, 400_000, 500_000),
                fix_days=14, as_of=None, author=()):
    """Build the report dict for one sub-command (render_md / to_json turn it into text)."""
    if command not in CMD_FUNCS:
        raise ValueError(f"unknown command {command!r}")
    ctx = Ctx(data, tz=tz, projects=projects, exclude=exclude, corrected=corrected, exclude_projects=exclude_projects)
    wins = parse_windows(windows or [], ctx.tz)
    if command == "escapes" and prs is None:
        raise ValueError("escapes needs --prs")
    as_of_s = ul.fmt_ts(ul.parse_cli_time(as_of, ctx.tz) if as_of else dt.datetime.now(dt.timezone.utc))
    ns = argparse.Namespace(top=top, prs=prs, ctx_threshold=ctx_threshold, sim_thresholds=list(sim_thresholds),
                            fix_days=fix_days, as_of=as_of_s, author=list(author))
    header = {
        "資料檔": f"{data_path or '(in memory)'}（generated_at {data.get('generated_at')}，schema_version {data.get('schema_version')}）",
        "顯示時區": ul.fmt_offset(ctx.tz),
        "成本口徑": basis(ctx),
        "篩選": f"project={list(projects) or '-'}，exclude-project={list(exclude_projects) or '-'}，exclude-session={list(exclude) or '-'}，sessions={len(ctx.sessions)}，reqs={len(ctx.reqs)}",
    }
    notes = list(CMD_NOTES.get(command, []))
    if ctx.pricing_note:
        notes.append(ctx.pricing_note)
    if corrected:
        notes.append("--corrected 的 output 補估是本機校準的啟發式（pricing.json 的 output_correction），必須與 raw 並列看。")
    rep = {"command": command, "header": header, "notes": notes, "windows": []}
    for w in wins:
        rep["windows"].append({**w.label(), "tables": CMD_FUNCS[command](ctx, w, ns)})
    return rep


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data", required=True, help="data.json written by extract.py")
    common.add_argument("--tz", help="display zone: +08:00, UTC or an IANA name (default: system local)")
    common.add_argument("--window", action="append", default=[], metavar="NAME=ISO..ISO",
                        help="time window (repeatable; either bound may be empty; naive times are read in --tz). Default: everything")
    common.add_argument("--project", action="append", default=[], metavar="SUBSTR",
                        help="only slugs containing SUBSTR (repeatable)")
    common.add_argument("--exclude-project", action="append", default=[], metavar="SUBSTR",
                        help="drop sessions whose slug contains SUBSTR (repeatable), e.g. test sessions")
    common.add_argument("--exclude-session", action="append", default=[], metavar="SID",
                        help="drop sessions whose id starts with SID, subagents included (repeatable)")
    common.add_argument("--corrected", action="store_true",
                        help="use the estimated output (cost_est / out_est); a heuristic, read it next to the raw numbers")
    common.add_argument("--format", choices=("md", "json"), default="md")
    common.add_argument("--top", type=int, default=10, help="rows for the 'sessions' list and the largest parallel groups")
    p = argparse.ArgumentParser(prog="report.py", description="Cost and dispatch-behaviour tables from an extract.py data file.")
    sub = p.add_subparsers(dest="command", required=True)
    helps = {
        "cost": "total, role x family, model, slug, day, cost components, unpriced models",
        "cache": "request gaps, expired cache rewrites, 1h/5m write split",
        "context": "main ctx percentiles and buckets, subagent first-request ctx, compact count",
        "reports": "subagent final report length and Agent tool_result length",
        "dispatch": "Agent call parameters, errors, notification status, parallelism",
        "controller": "main-thread edits vs Agent calls, edits between a worker's return and the next verifier",
        "verifier": "verifier verdict distribution (regex heuristic) and cost",
        "agents": "per subagent type: requests, tools, wall clock, cost",
        "sessions": "most expensive sessions",
        "weekly": "rules-effect review: $/PR, PR/h, main ctx vs threshold, verifier rounds, review cost per call, handoff simulation",
        "escapes": "merged PRs later touched by a fix / revert PR on a shared file, with the fresh acceptance each one got",
    }
    subs = {name: sub.add_parser(name, parents=[common], help=helps[name], description=helps[name]) for name in COMMANDS}
    w = subs["weekly"]
    w.add_argument("--prs", metavar="PATH", help="JSON list of merged PRs (gh search prs --json closedAt,... or gh pr list --json mergedAt)")
    w.add_argument("--ctx-threshold", type=int, default=300_000, help="main ctx threshold for the crossed-session columns (default 300000)")
    w.add_argument("--sim-threshold", type=int, action="append", metavar="N",
                   help="handoff simulation threshold (repeatable; default 200000 300000 400000 500000)")
    e = subs["escapes"]
    e.add_argument("--prs", metavar="PATH", required=True,
                   help="JSON list of merged PRs with url, title, body, mergedAt, headRefName, author, files (gh pr list --json ...)")
    e.add_argument("--fix-days", type=int, default=14, help="follow-up window after the original merge, in days (default 14)")
    e.add_argument("--as-of", metavar="ISO", help="when the PR list was fetched; originals younger than --fix-days are marked censored (default: now)")
    e.add_argument("--author", action="append", default=[], metavar="LOGIN", help="only PRs by LOGIN count as originals (repeatable)")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = ul.load_data(args.data)
    except (OSError, ValueError) as exc:
        print(f"report.py: {exc}", file=sys.stderr)
        return 1
    extra = {}
    if args.command in ("weekly", "escapes"):
        if args.prs:
            try:
                extra["prs"] = json.loads(Path(args.prs).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"report.py: --prs: {exc}", file=sys.stderr)
                return 1
            if not isinstance(extra["prs"], list) or not all(isinstance(x, dict) for x in extra["prs"]):
                parser.error("--prs must be a JSON list of objects")
    if args.command == "weekly":
        extra["ctx_threshold"] = args.ctx_threshold
        if args.sim_threshold:
            extra["sim_thresholds"] = args.sim_threshold
    if args.command == "escapes":
        if args.fix_days < 1:
            parser.error("--fix-days must be >= 1")
        extra.update(fix_days=args.fix_days, as_of=args.as_of, author=args.author)
    try:
        rep = make_report(data, args.command, tz=args.tz, windows=args.window, projects=args.project,
                          exclude=args.exclude_session, corrected=args.corrected, top=args.top, data_path=args.data,
                          exclude_projects=args.exclude_project, **extra)
    except (ValueError, KeyError) as exc:  # bad --window / --tz (an unknown IANA zone raises KeyError)
        parser.error(str(exc))
    sys.stdout.write(render_md(rep) if args.format == "md" else to_json(rep) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
