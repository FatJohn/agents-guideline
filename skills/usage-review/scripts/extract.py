#!/usr/bin/env python3
"""Normalise Claude Code session jsonl files into one JSON file for report.py.

This is the only place that knows the jsonl record shapes. The format has no stability
promise from Anthropic, so when a new Claude Code version breaks something, fix it here
(see references/schema.md for the output and references/caveats.md for known traps).

    extract.py [--root ~/.claude/projects] --since ISO [--until ISO] [--tz +08:00]
               [--project SUBSTR ...] [--exclude-session SID ...]
               [--pricing path] [--output-correction] --out data.json [--quiet]

Reads <root>/<slug>/<sid>.jsonl and <root>/<slug>/<sid>/subagents/agent-*.jsonl (plus the
sibling .meta.json). Never reads tool-results/*.txt. Pure standard library.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import usagelib as U  # noqa: E402

GENERATOR = "usage-review/extract.py"
AGENT_TOOLS = ("Agent", "Task")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
ASK_TOOLS = ("AskUserQuestion", "ExitPlanMode")

# Heuristic: a Bash command that probably writes a file. Output field is *_heuristic.
BASH_WRITE_RE = re.compile(
    r"sed -i|\bcat\s*>>?|\btee\b|perl -pi|git apply|python3? - <<|python3? <<"
    r"|>>?\s*[\w./~-]+\.(?:dart|kt|swift|ts|tsx|js|py|cs|md|ya?ml|json|gradle|kts)\b"
)
# Where the agent id of a launched agent can be read from an Agent tool_result.
AGENT_ID_RES = (re.compile(r"agentId:\s*([0-9A-Za-z]+)"), re.compile(r'message from "([0-9A-Za-z]+)"'))


# ---------------------------------------------------------------- small helpers


def text_of(content) -> str:
    """Joined text blocks of a message content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(parts)


def result_text(block: dict) -> str:
    """Text of one tool_result block (content is a str or a list of text blocks)."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(y.get("text") or "" for y in content if isinstance(y, dict))
    return ""


def has_tool_result(content) -> bool:
    return isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content)


# ---------------------------------------------------------------- the extractor


class Extractor:
    def __init__(self, since: dt.datetime, until: dt.datetime | None, pricing: dict, output_correction: bool):
        self.since, self.until = since, until
        self.pricing = pricing
        self.output_correction = output_correction
        self.reqs: dict[tuple, dict] = {}
        self.req_int: dict[tuple, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.sess_int: dict[str, dict] = {}
        self.agents: dict[str, dict] = {}
        self.agent_int: dict[str, dict] = {}

    # -- bookkeeping ---------------------------------------------------------

    def in_window(self, t: dt.datetime) -> bool:
        return t >= self.since and (self.until is None or t < self.until)

    def session(self, sid: str, slug: str) -> tuple[dict, dict]:
        if sid not in self.sessions:
            self.sessions[sid] = {
                "sid": sid, "slug": slug, "cwd": None, "version": None, "title": None,
                "entrypoint": None, "worktree": None, "first": None, "last": None,
                "prs": [], "humans": [], "agent_calls": {}, "edits": [],
                "bash_writes_heuristic": [], "sends": [], "compact_boundaries": [],
            }
            self.sess_int[sid] = {
                "active": False, "first": None, "last": None, "custom_title": None, "ai_title": None,
                "prs": set(), "seen_tu": set(), "ask_ids": set(), "notifs": {},
            }
        return self.sessions[sid], self.sess_int[sid]

    # -- file scanning -------------------------------------------------------

    def scan(self, path: str, sid: str, slug: str, sub: dict | None) -> None:
        s, si = self.session(sid, slug)
        ai = self.agent_int[sub["id"]] if sub is not None else None
        tu_req: dict[str, tuple] = {}
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(d, dict):
                    continue
                ty = d.get("type")
                if sub is None:  # session-level metadata records carry no timestamp
                    if ty == "custom-title":
                        si["custom_title"] = d.get("customTitle") or si["custom_title"]
                        continue
                    if ty == "ai-title":
                        si["ai_title"] = d.get("aiTitle") or si["ai_title"]
                        continue
                    if ty == "pr-link":
                        url = d.get("prUrl") or (
                            f"https://github.com/{d['prRepository']}/pull/{d['prNumber']}"
                            if d.get("prRepository") and d.get("prNumber") else None)
                        if url:
                            si["prs"].add(url)
                        continue
                    if ty == "worktree-state":
                        name = (d.get("worktreeSession") or {}).get("worktreeName")
                        if name:
                            s["worktree"] = name
                        continue
                ts = d.get("timestamp")
                if not ts:
                    continue
                try:
                    t = U.parse_ts(ts)
                except ValueError:
                    continue
                if not self.in_window(t):
                    continue
                si["active"] = True
                si["first"] = t if si["first"] is None or t < si["first"] else si["first"]
                si["last"] = t if si["last"] is None or t > si["last"] else si["last"]
                if sub is not None:
                    sub["first"] = t if sub["first"] is None or t < sub["first"] else sub["first"]
                    sub["last"] = t if sub["last"] is None or t > sub["last"] else sub["last"]
                else:
                    if s["cwd"] is None and d.get("cwd"):
                        s["cwd"] = d["cwd"]
                    s["version"] = d.get("version") or s["version"]
                    s["entrypoint"] = d.get("entrypoint") or s["entrypoint"]
                if ty == "assistant":
                    self._assistant(d, t, s, si, sub, ai, tu_req)
                elif ty == "user":
                    self._user(d, t, s, si, sub, ai, tu_req)
                elif sub is None:
                    self._main_other(d, ty, t, s, si)

    def _main_other(self, d: dict, ty: str, t: dt.datetime, s: dict, si: dict) -> None:
        if ty == "system" and d.get("subtype") == "compact_boundary":
            s["compact_boundaries"].append(U.fmt_ts(t))
        elif ty == "queue-operation" and d.get("operation") == "enqueue" and isinstance(d.get("content"), str):
            self._notifications(d["content"], t, si)
        elif ty == "attachment":
            att = d.get("attachment") or {}
            if att.get("type") == "queued_command" and isinstance(att.get("prompt"), str):
                self._notifications(att["prompt"], t, si)

    def _notifications(self, text: str, t: dt.datetime, si: dict) -> None:
        """Collect task-notifications; the same one shows up in several record types, so
        de-duplicate on its content and keep the earliest time."""
        if "<task-notification>" not in text:
            return
        for n in U.parse_task_notifications(text):
            key = (n["task_id"], n["tool_use_id"], n["status"], n["subagent_tokens"], n["tool_uses"], n["duration_ms"])
            old = si["notifs"].get(key)
            if old is None or t < old[0]:
                si["notifs"][key] = (t, n)

    # -- assistant records ---------------------------------------------------

    def _assistant(self, d, t, s, si, sub, ai, tu_req) -> None:
        msg = d.get("message") or {}
        content = msg.get("content")
        blocks = content if isinstance(content, list) else []
        model = msg.get("model")
        usage = msg.get("usage") or {}
        mid, rid = msg.get("id"), d.get("requestId")
        vis = len(content) if isinstance(content, str) else sum(
            len(b.get("text") or "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
        key = None
        # '<synthetic>' records are harness-made placeholders (all-zero usage), not requests.
        if usage and mid and not (isinstance(model, str) and model.startswith("<")):
            key = (mid, rid)
            self._upsert_req(key, d, t, usage, model, vis, sid=s["sid"], agent=sub["id"] if sub else None)
        for b in blocks:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp, tid = b.get("name"), b.get("input") or {}, b.get("id")
            if not isinstance(inp, dict):
                inp = {}
            if key is not None and tid:
                tu_req[tid] = key
                self.req_int[key]["tools"].setdefault(tid, name)
            if sub is not None:
                if tid and tid not in ai["tool_ids"]:
                    ai["tool_ids"].add(tid)
                    sub["tools"][name] = sub["tools"].get(name, 0) + 1
                if name == "SubagentHandback":
                    sub["handback"] = True
                    ai["handback_text"] = inp.get("message") if isinstance(inp.get("message"), str) else ""
                continue
            if tid and tid in si["seen_tu"]:
                continue
            if tid:
                si["seen_tu"].add(tid)
            ts = U.fmt_ts(t)
            if name in AGENT_TOOLS and tid:
                prompt = inp.get("prompt")
                prompt = prompt if isinstance(prompt, str) else ""
                s["agent_calls"][tid] = {
                    "t": ts, "subagent_type": inp.get("subagent_type"), "model": inp.get("model"),
                    "effort": inp.get("effort"), "isolation": inp.get("isolation"),
                    "background": inp.get("run_in_background"), "description": inp.get("description"),
                    "prompt_chars": len(prompt), "prompt_head": prompt[:600],
                    "agent_id": None, "resolved_model": None, "result": None,
                    "notification": None, "notification_count": 0, "first_notification_t": None,
                }
            elif name in EDIT_TOOLS:
                s["edits"].append({"t": ts, "tool": name, "path": inp.get("file_path") or inp.get("notebook_path")})
            elif name == "Bash":
                cmd = inp.get("command")
                if isinstance(cmd, str) and BASH_WRITE_RE.search(cmd):
                    s["bash_writes_heuristic"].append({"t": ts, "head": cmd[:200]})
            elif name == "SendMessage":
                body = inp.get("message") if inp.get("message") is not None else inp.get("content")
                body = body if isinstance(body, str) else json.dumps(body or inp, ensure_ascii=False)
                s["sends"].append({"t": ts, "to": inp.get("to") or inp.get("recipient") or inp.get("agent_id"),
                                   "chars": len(body)})
            elif name in ASK_TOOLS:
                si["ask_ids"].add(tid)
        if sub is not None:
            text = text_of(content)
            if text.strip():
                ai["last_text"] = text

    def _upsert_req(self, key, d, t, usage, model, vis, sid, agent) -> None:
        cc = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
        v1, v5 = cc.get("ephemeral_1h_input_tokens"), cc.get("ephemeral_5m_input_tokens")
        cw = usage.get("cache_creation_input_tokens") or 0
        known = v1 is not None or v5 is not None
        fields = {
            "inp": usage.get("input_tokens") or 0, "cw": cw,
            "cw1h": (v1 or 0) if known else cw, "cw5m": (v5 or 0) if known else 0,
            "cw_ttl_known": known, "cr": usage.get("cache_read_input_tokens") or 0,
            "out_raw": usage.get("output_tokens") or 0,
        }
        row = self.reqs.get(key)
        uid = d.get("uuid")
        if row is None:
            self.reqs[key] = {
                "t": t, "sid": sid, "agent": agent, "role": None, "model": model,
                "mid": key[0], "rid": key[1], **fields, "out_est": None, "vis": vis,
                "cost_raw": None, "cost_est": None, "tools": [], "tool_result_chars": 0,
            }
            self.req_int[key] = {"uuids": {uid} if uid else set(), "tools": {}, "tr": {}}
            return
        ri = self.req_int[key]
        if uid and uid in ri["uuids"]:  # the same record seen again (copied into another file)
            return
        if uid:
            ri["uuids"].add(uid)
        row["vis"] += vis
        if t < row["t"]:
            row["t"] = t
        if fields["out_raw"] > row["out_raw"]:  # keep the usage of the row with the largest output
            row.update(fields)

    # -- user records --------------------------------------------------------

    def _user(self, d, t, s, si, sub, ai, tu_req) -> None:
        content = (d.get("message") or {}).get("content")
        if isinstance(content, list):
            for c in content:
                if not isinstance(c, dict) or c.get("type") != "tool_result":
                    continue
                tid = c.get("tool_use_id")
                txt = result_text(c)
                key = tu_req.get(tid)
                if key is not None:
                    self.req_int[key]["tr"][tid] = len(txt)
                if sub is not None:
                    if c.get("is_error") and tid not in ai["err_ids"]:
                        ai["err_ids"].add(tid)
                        sub["tool_errors"] += 1
                    continue
                call = s["agent_calls"].get(tid)
                if call is not None and call["result"] is None:
                    call["result"] = {"t": U.fmt_ts(t), "is_error": bool(c.get("is_error")),
                                      "chars": len(txt), "head": txt[:300]}
                    tur = d.get("toolUseResult") if isinstance(d.get("toolUseResult"), dict) else {}
                    call["agent_id"] = tur.get("agentId") or self._agent_id_from_text(txt)
                    call["resolved_model"] = tur.get("resolvedModel")
                if tid in si["ask_ids"]:
                    s["humans"].append({"t": U.fmt_ts(t), "chars": len(txt), "kind": "ask_answer"})
        if has_tool_result(content):
            return
        if sub is not None:
            if ai["prompt_chars"] is None:
                ai["prompt_chars"] = len(text_of(content))
            return
        if d.get("isSidechain"):
            return
        raw = text_of(content)
        clean = U.strip_system_reminders(raw).strip()
        if not clean:  # nothing but injected system-reminder text: not a human message
            return
        kind = U.classify_human(raw, is_meta=bool(d.get("isMeta")))
        if kind == "notification":
            self._notifications(raw, t, si)
        s["humans"].append({"t": U.fmt_ts(t), "chars": len(clean), "kind": kind})

    @staticmethod
    def _agent_id_from_text(txt: str):
        for rx in AGENT_ID_RES:
            m = rx.search(txt)
            if m:
                return m.group(1)
        return None

    # -- finalisation --------------------------------------------------------

    def finalize(self) -> dict:
        pricing = self.pricing
        calls_by_tid, tid_of, calls_by_agent = {}, {}, {}
        for s in self.sessions.values():
            for tid, call in s["agent_calls"].items():
                calls_by_tid[tid] = call
                tid_of[id(call)] = tid
                if call["agent_id"]:
                    calls_by_agent[call["agent_id"]] = call

        # agents: drop those without an in-window event, link to the Agent call, resolve the type
        agent_type = {}
        for aid in list(self.agents):
            a, ai = self.agents[aid], self.agent_int[aid]
            if a["first"] is None:
                del self.agents[aid]
                continue
            call = calls_by_tid.get(a["tool_use_id"]) if a["tool_use_id"] else None
            if call is None:
                call = calls_by_agent.get(aid)
                if call is not None:
                    a["tool_use_id"] = tid_of[id(call)]
            if call is not None and not call["agent_id"]:
                call["agent_id"] = aid
                calls_by_agent[aid] = call
            call_type = call.get("subagent_type") if call else None
            a["type"] = call_type or a["meta_type"] or "unknown"
            a["retyped"] = a["meta_type"] is not None and a["type"] != a["meta_type"]
            if not a["description"] and call:
                a["description"] = call.get("description")
            text = ai["handback_text"] if a["handback"] and ai["handback_text"] else (ai["last_text"] or "")
            a["final_chars"], a["final_head"] = len(text), text[:400]
            a["prompt_chars"] = ai["prompt_chars"] or 0
            agent_type[aid] = a["type"]

        # notifications -> agent_calls (by tool-use-id, else by task-id == agent id); the last
        # one carries the cumulative numbers of a resumed agent, the first one its first completion
        for sid, si in self.sess_int.items():
            s = self.sessions[sid]
            by_agent = {c["agent_id"]: c for c in s["agent_calls"].values() if c["agent_id"]}
            per_call: dict[int, list] = collections.defaultdict(list)
            for t, n in si["notifs"].values():
                call = s["agent_calls"].get(n["tool_use_id"]) or by_agent.get(n["task_id"])
                if call is not None:
                    per_call[id(call)].append((t, n, call))
            for items in per_call.values():
                items.sort(key=lambda x: (x[0], x[1]["duration_ms"] or 0))
                t_last, n_last, call = items[-1]
                call["notification"] = {"t": U.fmt_ts(t_last), "status": n_last["status"],
                                        "subagent_tokens": n_last["subagent_tokens"],
                                        "tool_uses": n_last["tool_uses"], "duration_ms": n_last["duration_ms"]}
                call["notification_count"] = len(items)
                call["first_notification_t"] = U.fmt_ts(items[0][0])
                if not call["agent_id"] and n_last["task_id"]:
                    call["agent_id"] = n_last["task_id"]

        # requests
        unpriced: collections.Counter = collections.Counter()
        per_agent_reqs: collections.Counter = collections.Counter()
        out_reqs = []
        for key, r in self.reqs.items():
            ri = self.req_int[key]
            r["role"] = "main" if r["agent"] is None else agent_type.get(r["agent"], "unknown")
            r["tools"] = list(ri["tools"].values())
            r["tool_result_chars"] = sum(ri["tr"].values())
            if self.output_correction:
                r["out_est"] = U.estimate_output(r["model"], r["out_raw"], r["vis"], pricing)
            r["cost_raw"] = U.cost(r, pricing, corrected=False)
            r["cost_est"] = U.cost(r, pricing, corrected=True) if self.output_correction else None
            if r["cost_raw"] is None:
                unpriced[r["model"] or "null"] += 1
            if r["agent"]:
                per_agent_reqs[r["agent"]] += 1
            r["t"] = U.fmt_ts(r["t"])
            out_reqs.append(r)
        out_reqs.sort(key=lambda r: (r["t"], r["mid"], r["rid"] or ""))
        for aid, a in self.agents.items():
            a["requests"] = per_agent_reqs.get(aid, 0)
            a["first"], a["last"] = U.fmt_ts(a["first"]), U.fmt_ts(a["last"])

        # sessions
        out_sessions = {}
        for sid in sorted(self.sessions):
            si, s = self.sess_int[sid], self.sessions[sid]
            if not si["active"]:
                continue
            s["title"] = si["custom_title"] or si["ai_title"]
            s["prs"] = sorted(si["prs"])
            s["first"], s["last"] = U.fmt_ts(si["first"]), U.fmt_ts(si["last"])
            out_sessions[sid] = s
        return {"sessions": out_sessions, "agents": dict(sorted(self.agents.items())),
                "reqs": out_reqs, "unpriced": dict(unpriced)}

    def new_agent(self, aid: str, sid: str, slug: str, meta: dict) -> dict:
        a = {"id": aid, "sid": sid, "slug": slug, "type": None, "meta_type": meta.get("agentType"),
             "retyped": False, "model_meta": meta.get("model"), "description": meta.get("description"),
             "tool_use_id": meta.get("toolUseId"), "first": None, "last": None, "requests": 0,
             "prompt_chars": 0, "final_chars": 0, "final_head": "", "handback": False,
             "tools": {}, "tool_errors": 0}
        self.agents[aid] = a
        self.agent_int[aid] = {"tool_ids": set(), "err_ids": set(), "prompt_chars": None,
                               "handback_text": "", "last_text": ""}
        return a


# ---------------------------------------------------------------- driver


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="extract.py",
        description="Normalise Claude Code session jsonl files into one JSON file (schema: references/schema.md).")
    p.add_argument("--root", default="~/.claude/projects", help="projects directory (default: %(default)s)")
    p.add_argument("--since", required=True, help="window start, ISO 8601; naive values are read in --tz")
    p.add_argument("--until", help="window end (exclusive), ISO 8601; default: no upper bound")
    p.add_argument("--tz", help="zone for naive --since/--until: +08:00, UTC or an IANA name (default: system local)")
    p.add_argument("--project", action="append", default=[], metavar="SUBSTR",
                   help="only project directories whose name contains SUBSTR (repeatable)")
    p.add_argument("--exclude-session", action="append", default=[], metavar="SID",
                   help="skip sessions whose id starts with SID, subagents included (repeatable)")
    p.add_argument("--pricing", help="pricing.json to use instead of the one next to this script")
    p.add_argument("--output-correction", action="store_true",
                   help="also estimate output tokens (heuristic, see pricing.json); keeps out_raw and cost_raw")
    p.add_argument("--out", required=True, help="output JSON file")
    p.add_argument("--quiet", action="store_true", help="print nothing on success")
    return p


def run(args: argparse.Namespace) -> dict:
    """Scan, normalise and return the data dict (main() writes it to --out)."""
    tz = U.parse_tz(args.tz)
    since = U.parse_cli_time(args.since, tz)
    until = U.parse_cli_time(args.until, tz) if args.until else None
    if until is not None and until <= since:
        raise SystemExit("--until must be later than --since")
    pricing = U.load_pricing(args.pricing)
    root = os.path.expanduser(args.root)
    ex = Extractor(since, until, pricing, bool(args.output_correction))
    since_ts = since.timestamp()

    def wanted(slug: str, sid: str) -> bool:
        if args.project and not any(p in slug for p in args.project):
            return False
        return not any(sid.startswith(x) for x in args.exclude_session)

    for f in sorted(glob.glob(os.path.join(root, "*", "*.jsonl"))):
        parts = f.split(os.sep)
        slug, sid = parts[-2], parts[-1][:-len(".jsonl")]
        if os.path.getmtime(f) < since_ts or not wanted(slug, sid):
            continue
        ex.scan(f, sid, slug, None)
    for f in sorted(glob.glob(os.path.join(root, "*", "*", "subagents", "agent-*.jsonl"))):
        parts = f.split(os.sep)
        slug, sid = parts[-4], parts[-3]
        if os.path.getmtime(f) < since_ts or not wanted(slug, sid):
            continue
        aid = parts[-1][len("agent-"):-len(".jsonl")]
        meta = {}
        try:
            with open(f[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                loaded = json.load(fh)
            meta = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError):
            pass
        ex.scan(f, sid, slug, ex.new_agent(aid, sid, slug, meta))

    body = ex.finalize()
    return {
        "schema_version": U.SCHEMA_VERSION,
        "generated_at": U.fmt_ts(dt.datetime.now(U.UTC)),
        "generator": GENERATOR,
        "args": {
            "root": args.root, "since": U.fmt_ts(since), "until": U.fmt_ts(until) if until else None,
            "tz": U.fmt_offset(tz, since), "project": list(args.project),
            "exclude_session": list(args.exclude_session), "pricing": pricing["_path"],
            "output_correction": bool(args.output_correction),
        },
        **body,
    }


def summary(data: dict) -> str:
    reqs = data["reqs"]
    lines = [f"sessions={len(data['sessions'])} agents={len(data['agents'])} reqs={len(reqs)}"]
    if reqs:
        lines.append(f"time range: {reqs[0]['t']} .. {reqs[-1]['t']} (UTC)")
    if data["unpriced"]:
        lines.append("unpriced models: " + ", ".join(f"{m}={n} reqs" for m, n in sorted(data["unpriced"].items())))
    else:
        lines.append("unpriced models: none")
    lines.append(f"retyped agents: {sum(1 for a in data['agents'].values() if a['retyped'])}")
    unknown_ttl = sum(1 for r in reqs if not r["cw_ttl_known"])
    lines.append(f"cw_ttl_known=false: {unknown_ttl} reqs (whole cache write priced as 1h, an upper bound)")
    short = sum(1 for r in reqs if r["cw_ttl_known"] and r["cw1h"] + r["cw5m"] < r["cw"])
    lines.append(f"cw breakdown smaller than total (remainder not priced): {short} reqs")
    return "\n".join(lines)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    data = run(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    if not args.quiet:
        print(summary(data))
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
