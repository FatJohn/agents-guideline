"""Tests for .claude/skills/usage-review/scripts/extract.py (jsonl -> normalised JSON).

All fixtures are invented: fictional slug, session ids, dates (2031) and models.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".claude" / "skills" / "usage-review" / "scripts"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(SCRIPTS))
usagelib = _load("usagelib", "usagelib.py")
extract = _load("usage_review_extract", "extract.py")

SLUG = "-home-user-proj-alpha"
SID = "sess-main"
SINCE = "2031-01-02T00:00:00Z"
DUP_A, DUP_B = "uuid-dup-a", "uuid-dup-b"
_uuid = itertools.count(1)


def ts(hms: str) -> str:
    return f"2031-01-02T{hms}.000Z"


def usage(inp=0, cw1h=0, cw5m=0, cr=0, out=0, total_only=None):
    if total_only is not None:
        return {"input_tokens": inp, "cache_creation_input_tokens": total_only,
                "cache_read_input_tokens": cr, "output_tokens": out}
    return {"input_tokens": inp, "cache_creation_input_tokens": cw1h + cw5m,
            "cache_creation": {"ephemeral_1h_input_tokens": cw1h, "ephemeral_5m_input_tokens": cw5m},
            "cache_read_input_tokens": cr, "output_tokens": out}


def assistant(t, mid, rid, use, content, model="claude-opus-5-5", sid=SID, uuid=None):
    return {"type": "assistant", "timestamp": t, "uuid": uuid or f"u{next(_uuid)}", "sessionId": sid,
            "requestId": rid, "message": {"id": mid, "model": model, "role": "assistant",
                                           "content": content, "usage": use}}


def user(t, content, sid=SID, **extra):
    return {"type": "user", "timestamp": t, "uuid": f"u{next(_uuid)}", "sessionId": sid,
            "message": {"role": "user", "content": content}, **extra}


def text(s):
    return {"type": "text", "text": s}


def tool_use(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def tool_result(tid, body, is_error=False):
    return {"type": "tool_result", "tool_use_id": tid, "content": body, "is_error": is_error}


def notification(tool_use_id, task_id, status="completed", tokens=123, tools=4, ms=5000):
    return (f"<task-notification>\n<task-id>{task_id}</task-id>\n<tool-use-id>{tool_use_id}</tool-use-id>\n"
            f"<status>{status}</status>\n<summary>done</summary>\n"
            f"<usage><subagent_tokens>{tokens}</subagent_tokens><tool_uses>{tools}</tool_uses>"
            f"<duration_ms>{ms}</duration_ms></usage>\n</task-notification>")


def write_jsonl(path: Path, records, mtime: str | None = "2031-01-03T00:00:00+00:00"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    if mtime:
        stamp = usagelib.parse_ts(mtime).timestamp()
        os.utime(path, (stamp, stamp))


def main_records():
    rules = "<system-reminder>\nrules: always write tests\n</system-reminder>"
    return [
        {"type": "custom-title", "customTitle": "alpha task", "sessionId": SID},
        {"type": "worktree-state", "worktreeSession": {"worktreeName": "wt-alpha"}, "sessionId": SID},
        {"type": "pr-link", "prUrl": "https://example.test/o/r/pull/7", "sessionId": SID, "timestamp": ts("03:00:00")},
        user(ts("03:00:00"), "hello there", cwd="/work/alpha", version="9.9.9", entrypoint="cli"),
        user(ts("03:00:01"), rules),
        user(ts("03:00:02"), "Another Claude session sent a message:\n<agent-message from=\"peer1\">ping</agent-message>"),
        user(ts("03:00:03"), "<command-name>/foo</command-name>"),
        user(ts("03:00:04"), [text(rules + "\nsecond question")]),
        user(ts("03:00:04"), "injected skill text", isMeta=True),
        assistant(ts("03:00:05"), "msg_call", "req_call", usage(inp=5, cr=50, out=7),
                  [tool_use("toolu_A1", "Agent", subagent_type="worker", model="opus", effort="high",
                            isolation="worktree", run_in_background=True, description="do it",
                            prompt="p" * 700)]),
        user(ts("03:00:06"), [tool_result("toolu_A1", "Async agent launched successfully.\nagentId: agentx1 (internal)")],
             toolUseResult={"isAsync": True, "status": "async_launched", "agentId": "agentx1",
                            "resolvedModel": "claude-opus-5-5"}),
        # two more launches whose agent id is only known from the tool_result (no subagent file, no meta)
        assistant(ts("03:00:06"), "msg_calls2", "req_calls2", usage(inp=1, out=1),
                  [tool_use("toolu_A2", "Agent", subagent_type="verifier", description="check", prompt="q"),
                   tool_use("toolu_A3", "Agent", subagent_type="Explore", description="scan", prompt="r")]),
        user(ts("03:00:06"), [tool_result("toolu_A2", "launched")], toolUseResult={"agentId": "agenty2"}),
        user(ts("03:00:06"), [tool_result("toolu_A3", "Async agent launched successfully.\nagentId: agentz3 (internal)")]),
        {"type": "queue-operation", "operation": "enqueue", "timestamp": ts("03:00:30"), "sessionId": SID,
         "content": "<task-notification>\n<task-id>agentz3</task-id>\n<status>completed</status>\n"
                    "<usage><subagent_tokens>7</subagent_tokens><tool_uses>1</tool_uses>"
                    "<duration_ms>9</duration_ms></usage>\n</task-notification>"},
        assistant(ts("03:00:06"), "synthetic-1", None, usage(), [text("No response requested.")], model="<synthetic>"),
        # one request written as two rows (one per content block): output 300 then 900
        assistant(ts("03:00:07"), "msg_dup", "req_dup", usage(inp=1, cr=111, out=300), [text("abc")], uuid=DUP_A),
        assistant(ts("03:00:08"), "msg_dup", "req_dup", usage(inp=1, cr=222, out=900), [text("defg")], uuid=DUP_B),
        # a resend: same message.id under two different requestIds are two requests, not one
        assistant(ts("03:00:08"), "msg_resend", "req_resend_a", usage(inp=2, cr=20, out=40), [text("r1")]),
        assistant(ts("03:00:08"), "msg_resend", "req_resend_b", usage(inp=3, cr=30, out=50), [text("r2")]),
        assistant(ts("03:00:09"), "msg_price", "req_price", usage(inp=1000, cw1h=2000, cw5m=1000, cr=1000, out=1000),
                  [text("x")]),
        assistant(ts("03:00:10"), "msg_unk", "req_unk", usage(inp=10, out=10), [text("y")], model="claude-unknown-9"),
        assistant(ts("03:00:11"), "msg_total", "req_total", usage(inp=1, cr=2, out=3, total_only=500), [text("z")]),
        assistant(ts("03:00:12"), "msg_son", "req_son", usage(inp=1, out=10), [text("s" * 100)],
                  model="claude-sonnet-5-5"),
        assistant(ts("03:00:13"), "msg_edit", "req_edit", usage(inp=1, out=1),
                  [tool_use("toolu_E1", "Edit", file_path="/work/alpha/a.py"),
                   tool_use("toolu_B1", "Bash", command="echo hi > notes.md"),
                   tool_use("toolu_B2", "Bash", command="ls -la"),
                   tool_use("toolu_M1", "SendMessage", to="agentx1", message="hello")]),
        assistant(ts("03:00:14"), "msg_ask", "req_ask", usage(inp=1, out=1),
                  [tool_use("toolu_Q1", "AskUserQuestion", question="which?")]),
        user(ts("03:00:15"), [tool_result("toolu_Q1", "option two")]),
        {"type": "system", "subtype": "compact_boundary", "timestamp": ts("03:00:16"), "sessionId": SID},
        {"type": "queue-operation", "operation": "enqueue", "timestamp": ts("03:10:00"), "sessionId": SID,
         "content": notification("toolu_A1", "agentx1")},
        {"type": "attachment", "timestamp": ts("03:10:00"), "sessionId": SID, "uuid": f"u{next(_uuid)}",
         "attachment": {"type": "queued_command", "prompt": notification("toolu_A1", "agentx1")}},
        user(ts("03:10:01"), notification("toolu_A1", "agentx1")),
        # the rules text mentions task-notification; inside a system-reminder it must not count
        user(ts("03:10:02"), "<system-reminder>a <task-notification> may arrive</system-reminder>\nthanks"),
    ]


def sub_records():
    return [
        user(ts("03:00:20"), "do the thing", sid=SID),
        assistant(ts("03:00:21"), "msg_sub1", "req_s1", usage(inp=10, cw1h=100, cr=1000, out=20),
                  [tool_use("toolu_R1", "Read", file_path="/work/alpha/a.py")], model="claude-sonnet-5-5"),
        user(ts("03:00:22"), [tool_result("toolu_R1", "12345")]),
        assistant(ts("03:00:23"), "msg_sub2", "req_s2", usage(inp=10, cw1h=100, cr=1000, out=30),
                  [tool_use("toolu_H1", "SubagentHandback", message="final report text")],
                  model="claude-sonnet-5-5"),
    ]


def build_root(tmp: str) -> str:
    root = Path(tmp) / "projects"
    proj = root / SLUG
    write_jsonl(proj / f"{SID}.jsonl", main_records())
    write_jsonl(proj / SID / "subagents" / "agent-agentx1.jsonl", sub_records())
    # the harness lists the subagent as general-purpose even though the call asked for a worker
    (proj / SID / "subagents" / "agent-agentx1.meta.json").write_text(
        json.dumps({"agentType": "general-purpose", "toolUseId": "toolu_A1", "description": "sub desc"}))
    # decoys that must never be read
    decoy = assistant(ts("03:30:00"), "msg_decoy", "req_decoy", usage(inp=999999, out=1), [text("d")])
    (proj / SID / "tool-results").mkdir(parents=True)
    (proj / SID / "tool-results" / "x.txt").write_text(json.dumps(decoy) + "\n")
    write_jsonl(proj / SID / "tool-results" / "agent-decoy.jsonl", [decoy])
    # the same request row copied into another session file (fork / resume): must not be counted twice
    write_jsonl(proj / "sess-zcopy.jsonl",
                [assistant(ts("03:00:08"), "msg_dup", "req_dup", usage(inp=1, cr=222, out=900), [text("defg")],
                           sid="sess-zcopy", uuid=DUP_B)])
    # an old session file (mtime before --since) and a fresh file whose events are before --since
    write_jsonl(proj / "sess-old.jsonl", [assistant(ts("03:00:00"), "msg_old", "req_old", usage(inp=1, out=1),
                                                    [text("o")], sid="sess-old")], mtime="2030-01-01T00:00:00+00:00")
    write_jsonl(proj / "sess-early.jsonl", [assistant("2030-12-31T23:00:00.000Z", "msg_early", "req_early",
                                                      usage(inp=1, out=1), [text("e")], sid="sess-early")])
    return str(root)


def run_extract(root: str, *extra: str) -> dict:
    out = os.path.join(os.path.dirname(root), "data.json")
    args = extract.build_parser().parse_args(["--root", root, "--since", SINCE, "--out", out, "--quiet", *extra])
    return extract.run(args)


class ExtractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = build_root(cls._tmp.name)
        cls.data = run_extract(cls.root)
        cls.est = run_extract(cls.root, "--output-correction")
        cls.by_mid = {r["mid"]: r for r in cls.data["reqs"]}
        cls.est_by_mid = {r["mid"]: r for r in cls.est["reqs"]}
        cls.sess = cls.data["sessions"][SID]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # -- dedup ----------------------------------------------------------------

    def test_duplicate_rows_of_one_request_collapse_to_the_largest_output(self):
        dup = [r for r in self.data["reqs"] if r["mid"] == "msg_dup" and r["rid"] == "req_dup"]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["out_raw"], 900)
        self.assertEqual(dup[0]["cr"], 222)  # the other usage fields come from the row with the largest output
        # a copy of the same record (same uuid) in another session file must not add its text twice
        self.assertEqual(dup[0]["vis"], len("abc") + len("defg"))

    def test_same_message_id_under_different_request_ids_stays_two_requests(self):
        resend = sorted((r for r in self.data["reqs"] if r["mid"] == "msg_resend"), key=lambda r: r["rid"])
        self.assertEqual(len(resend), 2)
        self.assertEqual([r["rid"] for r in resend], ["req_resend_a", "req_resend_b"])
        self.assertEqual([(r["inp"], r["cr"], r["out_raw"]) for r in resend], [(2, 20, 40), (3, 30, 50)])

    def test_tool_results_directory_is_never_read(self):
        self.assertNotIn("msg_decoy", self.by_mid)
        self.assertEqual(sum(r["inp"] for r in self.data["reqs"] if r["inp"] >= 999999), 0)

    # -- roles ----------------------------------------------------------------

    def test_agent_call_type_overrides_the_rewritten_meta_type(self):
        agent = self.data["agents"]["agentx1"]
        self.assertEqual(agent["type"], "worker")
        self.assertEqual(agent["meta_type"], "general-purpose")
        self.assertTrue(agent["retyped"])
        self.assertEqual(agent["tool_use_id"], "toolu_A1")
        self.assertEqual(self.by_mid["msg_sub1"]["role"], "worker")
        self.assertEqual(self.by_mid["msg_dup"]["role"], "main")
        self.assertIsNone(self.by_mid["msg_dup"]["agent"])

    # -- human messages -------------------------------------------------------

    def test_human_message_kinds(self):
        kinds = [h["kind"] for h in self.sess["humans"]]
        # reminder-only text is dropped; the reminder wrapped around "second question" is stripped
        self.assertEqual(kinds.count("human"), 3)  # hello there, second question, thanks
        self.assertEqual(kinds.count("peer"), 1)
        self.assertEqual(kinds.count("command"), 1)
        self.assertEqual(kinds.count("ask_answer"), 1)
        self.assertEqual(kinds.count("notification"), 1)
        self.assertEqual(kinds.count("meta"), 1)  # isMeta record
        self.assertEqual(len(kinds), 8)
        hello = self.sess["humans"][0]
        self.assertEqual((hello["kind"], hello["chars"]), ("human", len("hello there")))

    def test_classify_human_directly(self):
        c = usagelib.classify_human
        self.assertEqual(c("<system-reminder>only rules</system-reminder>"), "meta")
        self.assertEqual(c("Another Claude session sent a message:\nhi"), "peer")
        self.assertEqual(c('<agent-message from="a1">\n[Subagent hand-back] report</agent-message>'), "notification")
        self.assertEqual(c("<command-name>/x</command-name>"), "command")
        self.assertEqual(c("This session is being continued from a previous conversation"), "compact")
        self.assertEqual(c("[ASK-ANSWER] yes"), "ask_answer")
        self.assertEqual(c("plain words", is_meta=True), "meta")
        self.assertEqual(c("plain words"), "human")

    # -- task-notification ----------------------------------------------------

    def test_task_notification_numbers_land_on_the_agent_call(self):
        call = self.sess["agent_calls"]["toolu_A1"]
        self.assertEqual(call["agent_id"], "agentx1")
        n = call["notification"]
        self.assertEqual((n["subagent_tokens"], n["tool_uses"], n["duration_ms"]), (123, 4, 5000))
        self.assertEqual(n["status"], "completed")
        # the same notification appears as queue-operation, attachment and user record: counted once
        self.assertEqual(call["notification_count"], 1)

    def test_agent_id_comes_from_tool_result_and_notification_matches_by_task_id(self):
        calls = self.sess["agent_calls"]
        self.assertEqual(calls["toolu_A2"]["agent_id"], "agenty2")  # toolUseResult.agentId
        self.assertIsNone(calls["toolu_A2"]["notification"])
        self.assertEqual(calls["toolu_A3"]["agent_id"], "agentz3")  # "agentId: ..." in the result text
        n = calls["toolu_A3"]["notification"]  # the notification carries no tool-use-id
        self.assertEqual((n["subagent_tokens"], n["tool_uses"], n["duration_ms"]), (7, 1, 9))

    def test_synthetic_placeholders_are_not_requests(self):
        self.assertNotIn("synthetic-1", self.by_mid)
        self.assertNotIn("<synthetic>", self.data["unpriced"])
        self.assertFalse([r for r in self.data["reqs"] if r["model"] == "<synthetic>"])

    def test_parse_task_notification_directly(self):
        n = usagelib.parse_task_notification(notification("toolu_X", "task9", status="killed", tokens=1, tools=2, ms=3))
        self.assertEqual(n, {"task_id": "task9", "tool_use_id": "toolu_X", "status": "killed",
                             "subagent_tokens": 1, "tool_uses": 2, "duration_ms": 3})
        self.assertIsNone(usagelib.parse_task_notification("no notification here"))
        self.assertIsNone(usagelib.parse_task_notification(
            "<system-reminder>a <task-notification>x</task-notification></system-reminder>"))

    # -- pricing --------------------------------------------------------------

    def test_cost_of_a_priced_request_splits_cache_write_by_ttl(self):
        r = self.by_mid["msg_price"]
        # cw1h != cw5m on purpose: with equal counts a swapped 1h/5m multiplier would price the same
        expected = (1000 * 4 + 1000 * 4 * 1.25 + 2000 * 4 * 2 + 1000 * 0.20 + 1000 * 20) / 1e6
        self.assertAlmostEqual(r["cost_raw"], expected, places=12)
        self.assertEqual((r["cw"], r["cw1h"], r["cw5m"], r["cw_ttl_known"]), (3000, 2000, 1000, True))
        self.assertIsNone(r["cost_est"])
        self.assertIsNone(r["out_est"])

    def test_unknown_model_is_unpriced_not_zero(self):
        r = self.by_mid["msg_unk"]
        self.assertIsNone(r["cost_raw"])
        self.assertEqual(self.data["unpriced"], {"claude-unknown-9": 1})

    def test_cache_creation_without_breakdown_is_priced_as_1h(self):
        r = self.by_mid["msg_total"]
        self.assertEqual((r["cw"], r["cw1h"], r["cw5m"]), (500, 500, 0))
        self.assertFalse(r["cw_ttl_known"])
        self.assertAlmostEqual(r["cost_raw"], (1 * 4 + 500 * 4 * 2 + 2 * 0.20 + 3 * 20) / 1e6, places=12)

    def test_output_correction_estimates_per_family(self):
        self.assertEqual(self.est_by_mid["msg_price"]["out_est"], 1000 + 680)
        self.assertEqual(self.est_by_mid["msg_son"]["out_est"], max(10, int(0.9 * 100)))
        self.assertEqual(self.est_by_mid["msg_price"]["out_raw"], 1000)  # the raw figure is kept
        expected_est = (1000 * 4 + 1000 * 4 * 1.25 + 2000 * 4 * 2 + 1000 * 0.20 + 1680 * 20) / 1e6
        self.assertAlmostEqual(self.est_by_mid["msg_price"]["cost_est"], expected_est, places=12)
        self.assertAlmostEqual(self.est_by_mid["msg_price"]["cost_raw"], self.by_mid["msg_price"]["cost_raw"], places=12)
        self.assertIsNone(self.est_by_mid["msg_unk"]["cost_est"])

    # -- time window ----------------------------------------------------------

    def test_files_older_than_since_and_events_before_it_are_skipped(self):
        self.assertNotIn("sess-old", self.data["sessions"])
        self.assertNotIn("msg_old", self.by_mid)
        self.assertNotIn("sess-early", self.data["sessions"])
        self.assertNotIn("msg_early", self.by_mid)

    def test_until_is_exclusive_and_since_is_inclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "projects"
            recs = [assistant(ts(f"0{h}:00:00"), f"msg_h{h}", f"req_h{h}", usage(inp=h, out=1), [text("t")],
                              sid="sess-edge") for h in (4, 5, 6)]
            write_jsonl(root / SLUG / "sess-edge.jsonl", recs)
            data = run_extract(str(root), "--since", "2031-01-02T05:00:00Z", "--until", "2031-01-02T06:00:00Z")
        self.assertEqual([r["mid"] for r in data["reqs"]], ["msg_h5"])

    def test_cli_time_uses_tz_only_for_naive_values(self):
        p = usagelib.parse_cli_time
        self.assertEqual(p("2031-01-02T08:00", "+08:00").isoformat(), "2031-01-02T00:00:00+00:00")
        self.assertEqual(p("2031-01-02T08:00:00+00:00", "+08:00").isoformat(), "2031-01-02T08:00:00+00:00")
        self.assertEqual(p("2031-01-02T08:00:00Z", "+08:00").isoformat(), "2031-01-02T08:00:00+00:00")

    def test_timestamp_and_zone_parsing(self):
        for raw, expected in (("2031-01-02T03:00:00.1Z", "2031-01-02T03:00:00.100Z"),
                              ("2031-01-02T03:00:00.123456789Z", "2031-01-02T03:00:00.123Z"),
                              ("2031-01-02T03:00:00+08:00", "2031-01-01T19:00:00.000Z")):
            parsed = usagelib.parse_ts(raw)
            self.assertEqual(parsed.utcoffset().total_seconds(), 0)
            self.assertEqual(usagelib.fmt_ts(parsed), expected)
        self.assertEqual(usagelib.parse_tz("-0330").utcoffset(None).total_seconds(), -3.5 * 3600)
        self.assertEqual(usagelib.parse_tz("+08:00").utcoffset(None).total_seconds(), 8 * 3600)
        self.assertEqual(usagelib.parse_tz("UTC").utcoffset(None).total_seconds(), 0)

    def test_since_given_in_tz_is_normalised_to_utc_in_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = extract.build_parser().parse_args(
                ["--root", tmp, "--since", "2031-01-02T08:00", "--tz", "+08:00", "--out", os.path.join(tmp, "o.json")])
            data = extract.run(args)
        self.assertEqual(data["args"]["since"], "2031-01-02T00:00:00.000Z")
        self.assertEqual(data["args"]["tz"], "+08:00")

    # -- filters --------------------------------------------------------------

    def test_project_and_exclude_session_filters(self):
        self.assertEqual(run_extract(self.root, "--project", "no-such-project")["reqs"], [])
        self.assertTrue(run_extract(self.root, "--project", "proj-alpha")["reqs"])
        excluded = run_extract(self.root, "--exclude-session", "sess-ma")  # prefix match, subagents go too
        self.assertNotIn(SID, excluded["sessions"])
        self.assertEqual(excluded["agents"], {})

    # -- other fields ---------------------------------------------------------

    def test_session_and_agent_call_fields(self):
        s = self.sess
        self.assertEqual((s["slug"], s["cwd"], s["version"], s["entrypoint"]), (SLUG, "/work/alpha", "9.9.9", "cli"))
        self.assertEqual((s["title"], s["worktree"], s["prs"]), ("alpha task", "wt-alpha", ["https://example.test/o/r/pull/7"]))
        self.assertEqual(len(s["compact_boundaries"]), 1)
        call = s["agent_calls"]["toolu_A1"]
        self.assertEqual((call["subagent_type"], call["model"], call["effort"], call["isolation"], call["background"]),
                         ("worker", "opus", "high", "worktree", True))
        self.assertEqual((call["prompt_chars"], len(call["prompt_head"])), (700, 600))
        self.assertEqual(call["resolved_model"], "claude-opus-5-5")
        self.assertEqual(call["result"]["chars"], len("Async agent launched successfully.\nagentId: agentx1 (internal)"))

    def test_edits_bash_writes_and_sends(self):
        s = self.sess
        self.assertEqual([(e["tool"], e["path"]) for e in s["edits"]], [("Edit", "/work/alpha/a.py")])
        self.assertEqual([b["head"] for b in s["bash_writes_heuristic"]], ["echo hi > notes.md"])
        self.assertEqual([(m["to"], m["chars"]) for m in s["sends"]], [("agentx1", 5)])

    def test_agent_record_and_per_request_tool_fields(self):
        agent = self.data["agents"]["agentx1"]
        self.assertEqual((agent["requests"], agent["prompt_chars"], agent["handback"]), (2, len("do the thing"), True))
        self.assertEqual(agent["tools"], {"Read": 1, "SubagentHandback": 1})
        self.assertEqual((agent["final_chars"], agent["final_head"]), (len("final report text"), "final report text"))
        self.assertEqual(agent["description"], "sub desc")
        self.assertEqual(self.by_mid["msg_sub1"]["tools"], ["Read"])
        self.assertEqual(self.by_mid["msg_sub1"]["tool_result_chars"], 5)

    def test_summary_reports_unpriced_and_unknown_ttl(self):
        text_out = extract.summary(self.data)
        self.assertIn("claude-unknown-9=1 reqs", text_out)
        self.assertIn("cw_ttl_known=false: 1 reqs", text_out)
        self.assertIn("retyped agents: 1", text_out)

    def test_load_data_rejects_other_schema_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / "good.json", Path(tmp) / "bad.json"
            good.write_text(json.dumps({"schema_version": 1}))
            bad.write_text(json.dumps({"schema_version": 2}))
            self.assertEqual(usagelib.load_data(good), {"schema_version": 1})
            with self.assertRaises(ValueError):
                usagelib.load_data(bad)


if __name__ == "__main__":
    unittest.main()
