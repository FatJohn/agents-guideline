"""Tests for .claude/skills/usage-review/scripts/report.py (normalised JSON -> cost / behaviour tables).

The fixture is a hand-written data dict in the schema_version 1 shape (see
.claude/skills/usage-review/references/schema.md). Everything in it is invented: fictional slugs, ids,
dates (2031) and models; every cost_raw is a hand-computed literal, checked against the pricing
formula once in test_fixture_costs_match_pricing_formula so a typo cannot hide behind the report.

Request timeline of the fixture (all 2031-01-02 UTC unless noted):
  alpha session   main (opus 5.5)  m1 00:00:00  m2 00:01:00  m3 02:00:00  m4 02:30:00  m5 20:00:00
                  worker ag1 (sonnet 5.5) s1 00:10:00  s2 00:20:00  s3 00:20:30
                  verifiers ag2 00:12:00 / ag3 00:50:00 / ag4 01:00:00 / ag5 00:55:00 (one request each)
  beta session    main  b1 00:02:00 (unknown model, unpriced)  b2 00:03:00 (sonnet 5.5)
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".claude" / "skills" / "usage-review" / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(SCRIPTS))
usagelib = _load("usagelib", SCRIPTS / "usagelib.py")
report = _load("usage_review_report", SCRIPTS / "report.py")

SLUG_A, SLUG_B = "-home-user-proj-alpha", "-home-user-proj-beta"
SID_A, SID_B = "sess-aaaaaaaa-0001", "sess-bbbbbbbb-0002"
OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"

# hand-computed from pricing.json (opus 4/20/0.2, sonnet 2/10/0.2 per M; cache write 1.25x / 2x input)
TOTAL_RAW = 0.93039      # sum of every cost_raw literal in the fixture
TOTAL_EST = 1.05279      # TOTAL_RAW + 9 opus requests x 680 extra output tokens x $20/M


def ts(hms: str, day: str = "02") -> str:
    return f"2031-01-{day}T{hms}.000Z"


_serial = [0]


def req(t, sid, agent, role, model, cost, inp=0, cw1h=0, cw5m=0, cr=0, out=0, cw=None, known=True, vis=0):
    _serial[0] += 1
    return {"t": ts(t) if len(t) == 8 else t, "sid": sid, "agent": agent, "role": role, "model": model,
            "mid": f"msg_{_serial[0]}", "rid": f"req_{_serial[0]}", "inp": inp,
            "cw": cw1h + cw5m if cw is None else cw, "cw1h": cw1h, "cw5m": cw5m, "cw_ttl_known": known,
            "cr": cr, "out_raw": out, "out_est": None, "vis": vis, "cost_raw": cost, "cost_est": None,
            "tools": [], "tool_result_chars": 0}


def call(t, stype, agent_id=None, result=None, note=None, background=None):
    """result/note are (time, ...) tuples: result=(t, is_error, chars), note=(t, status, tokens)."""
    res = None if result is None else {"t": ts(result[0]), "is_error": result[1], "chars": result[2], "head": ""}
    nt = None if note is None else {"t": ts(note[0]), "status": note[1], "subagent_tokens": note[2],
                                    "tool_uses": 4, "duration_ms": 1000}
    return {"t": ts(t), "subagent_type": stype, "model": None, "effort": None, "isolation": None,
            "background": background, "description": "d", "prompt_chars": 100, "prompt_head": "",
            "agent_id": agent_id, "resolved_model": None, "result": res, "notification": nt,
            "notification_count": 1 if nt else 0, "first_notification_t": nt["t"] if nt else None}


def agent(aid, atype, first, last, requests, tool_use_id, final_chars, final_head, handback=True, tools=None):
    return {"id": aid, "sid": SID_A, "slug": SLUG_A, "type": atype, "meta_type": atype, "retyped": False,
            "model_meta": None, "description": "d", "tool_use_id": tool_use_id, "first": ts(first), "last": ts(last),
            "requests": requests, "prompt_chars": 100, "final_chars": final_chars, "final_head": final_head,
            "handback": handback, "tools": tools or {}, "tool_errors": 0}


def make_data():
    reqs = [
        # alpha main: m3 follows a 1h59m gap with 90% cache write (expired rewrite); m5 follows a long gap but only reads
        req("00:00:00", SID_A, None, "main", OPUS, 0.0372, inp=1000, cw1h=1000, cw5m=1000, cr=1000, out=1000),
        req("00:01:00", SID_A, None, "main", OPUS, 0.0104, cr=2000, out=500),
        req("02:00:00", SID_A, None, "main", OPUS, 0.742, cw1h=90000, cr=10000, out=1000),
        req("02:30:00", SID_A, None, "main", OPUS, 0.022, cr=100000, out=100),
        req("20:00:00", SID_A, None, "main", OPUS, 0.1, cr=500000),
        # alpha worker ag1: s2 follows a 10 minute gap with a mostly-write request; s3 has no 1h/5m breakdown
        req("00:10:00", SID_A, "ag1", "worker", SONNET, 0.00195, inp=100, cw5m=500, out=50),
        req("00:20:00", SID_A, "ag1", "worker", SONNET, 0.00202, cw5m=800, cr=100),
        req("00:20:30", SID_A, "ag1", "worker", SONNET, 0.00142, cw=300, cw1h=300, known=False, cr=600, out=10),
        # alpha verifiers
        req("00:12:00", SID_A, "ag2", "verifier", OPUS, 0.0026, inp=100, cr=1000, out=100),
        req("00:50:00", SID_A, "ag3", "verifier", OPUS, 0.0026, inp=100, cr=1000, out=100),
        req("01:00:00", SID_A, "ag4", "verifier", OPUS, 0.0026, inp=100, cr=1000, out=100),
        req("00:55:00", SID_A, "ag5", "verifier", OPUS, 0.0026, inp=100, cr=1000, out=100),
        # beta: one request whose model matches no pricing entry, one sonnet request
        req("00:02:00", SID_B, None, "main", "claude-unknown-9", None, inp=10, out=10),
        req("00:03:00", SID_B, None, "main", SONNET, 0.003, inp=1000, out=100),
    ]
    reqs.sort(key=lambda r: r["t"])
    calls = {
        "tu1": call("00:05:00", "worker", "ag1", result=("00:05:01", False, 1100), note=("00:30:00", "completed", 5000), background="true"),
        "tu2": call("00:10:00", "verifier", "ag2", result=("00:10:01", False, 1100), note=("00:40:00", "completed", 7000)),
        "tu3": call("00:35:00", "Explore", "ag6", result=("00:35:01", False, 1100), note=("00:36:00", "killed", None)),
        "tu4": call("05:00:00", "verifier", None, result=("05:01:00", True, 200)),
        "tu5": call("06:00:00", "worker"),
        "tu6": call("05:01:00", "worker", None, result=("05:02:00", False, 300), background=False),
        "tu7": call("08:00:00", "Plan", None, result=("08:01:00", False, 400)),
        "tu8": call("07:00:00", "verifier", None, result=("07:01:00", False, 500)),
    }
    session_a = {
        "sid": SID_A, "slug": SLUG_A, "cwd": "/work/alpha", "version": "9.9.9", "title": "alpha work",
        "entrypoint": "cli", "worktree": None, "first": ts("00:00:00"), "last": ts("20:00:00"), "prs": [],
        "humans": [{"t": ts("00:00:00"), "chars": 10, "kind": "human"}, {"t": ts("00:00:01"), "chars": 5, "kind": "meta"},
                   {"t": ts("00:00:02"), "chars": 5, "kind": "ask_answer"}, {"t": ts("00:00:03"), "chars": 5, "kind": "notification"}],
        "agent_calls": calls,
        "edits": [{"t": ts(x), "tool": "Edit", "path": "/work/alpha/a.py"}
                  for x in ("00:20:00", "01:00:00", "04:59:00", "05:00:30", "05:30:00", "08:30:00")],
        "bash_writes_heuristic": [{"t": ts(x), "head": "echo a > b.md"} for x in ("00:01:00", "02:00:00", "05:00:40")],
        "sends": [], "compact_boundaries": [ts("03:00:00")],
    }
    session_b = {
        "sid": SID_B, "slug": SLUG_B, "cwd": "/work/beta", "version": "9.9.9", "title": None, "entrypoint": "cli",
        "worktree": None, "first": ts("00:02:00"), "last": ts("00:03:00"), "prs": [], "humans": [],
        "agent_calls": {}, "edits": [], "bash_writes_heuristic": [], "sends": [], "compact_boundaries": [],
    }
    agents = {
        "ag1": agent("ag1", "worker", "00:10:00", "00:20:30", 3, "tu1", 1200, "Done.", tools={"Read": 4, "SubagentHandback": 1}),
        "ag2": agent("ag2", "verifier", "00:12:00", "00:12:00", 1, "tu2", 400, "CONVERGED\n\nall checks pass"),
        "ag3": agent("ag3", "verifier", "00:50:00", "00:50:00", 1, "tuX3", 600, "PROSE-ONLY\n\nthe OPEN list is empty"),
        "ag4": agent("ag4", "verifier", "01:00:00", "01:00:00", 1, "tuX4", 800, "The REOPENED item is back", handback=False),
        "ag5": agent("ag5", "verifier", "00:55:00", "00:55:00", 1, "tuX5", 500, "**OPEN**\n\nitems remain"),
    }
    return {
        "schema_version": 1, "generated_at": "2031-01-05T00:00:00.000Z", "generator": "usage-review/extract.py",
        "args": {"pricing": str(usagelib.DEFAULT_PRICING_PATH), "output_correction": False},
        "sessions": {SID_A: session_a, SID_B: session_b}, "agents": agents, "reqs": reqs,
        "unpriced": {"claude-unknown-9": 1},
    }


def tables(rep, window=0):
    return {t["id"]: t for t in rep["windows"][window]["tables"]}


def rows(rep, tid, window=0):
    t = tables(rep, window)[tid]
    return [dict(zip(t["columns"], r)) for r in t["rows"]]


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = make_data()

    def rep(self, command, **kw):
        kw.setdefault("tz", "+08:00")
        return report.make_report(copy.deepcopy(self.data), command, **kw)

    # -- fixture sanity ---------------------------------------------------------

    def test_fixture_costs_match_pricing_formula(self):
        pricing = usagelib.load_pricing(None)
        for r in self.data["reqs"]:
            if r["cost_raw"] is None:
                self.assertIsNone(usagelib.price_for(r["model"], pricing))
            else:
                self.assertAlmostEqual(usagelib.cost(r, pricing), r["cost_raw"], places=9, msg=r["mid"])
        self.assertAlmostEqual(sum(r["cost_raw"] for r in self.data["reqs"] if r["cost_raw"] is not None), TOTAL_RAW, places=9)

    # -- cost -------------------------------------------------------------------

    def test_cost_total_and_breakdowns(self):
        rep = self.rep("cost")
        s = rows(rep, "summary")[0]
        self.assertEqual((s["reqs"], s["priced_reqs"], s["unpriced_reqs"]), (14, 13, 1))
        self.assertAlmostEqual(s["cost_usd"], TOTAL_RAW, places=9)
        by_model = {r["model"]: r for r in rows(rep, "by_model")}
        self.assertAlmostEqual(by_model[OPUS]["cost_usd"], 0.9116 + 4 * 0.0026, places=9)
        self.assertAlmostEqual(by_model[SONNET]["cost_usd"], 0.00539 + 0.003, places=9)
        by_role = {(r["role"], r["family"]): r["cost_usd"] for r in rows(rep, "by_role_family")}
        self.assertAlmostEqual(by_role[("worker", "sonnet")], 0.00539, places=9)
        self.assertAlmostEqual(by_role[("verifier", "opus")], 4 * 0.0026, places=9)
        by_slug = {r["slug"]: r for r in rows(rep, "by_slug")}
        self.assertAlmostEqual(by_slug[SLUG_B]["cost_usd"], 0.003, places=9)
        self.assertEqual(by_slug[SLUG_B]["sessions"], 1)

    def test_top_folds_the_remaining_slugs_into_one_row(self):
        slugs = rows(self.rep("cost", top=1), "by_slug")
        self.assertEqual([r["slug"] for r in slugs], [SLUG_A, "(其餘 1 個)"])
        rest = slugs[1]
        self.assertEqual((rest["sessions"], rest["reqs"]), (1, 1))   # the unpriced request is not in the by-slug tables
        self.assertAlmostEqual(rest["cost_usd"], 0.003, places=9)
        self.assertAlmostEqual(slugs[0]["cost_share"] + rest["cost_share"], 1.0, places=9)
        self.assertEqual(len(rows(self.rep("cost", top=2), "by_slug")), 2)   # nothing to fold

    def test_unknown_model_is_listed_unpriced_and_never_counted_as_zero(self):
        rep = self.rep("cost")
        self.assertEqual(rows(rep, "unpriced"), [{"model": "claude-unknown-9", "reqs": 1}])
        s = rows(rep, "summary")[0]
        self.assertEqual(s["priced_reqs"], 13)
        self.assertNotIn("claude-unknown-9", [r["model"] for r in rows(rep, "by_model")])

    def test_cost_components_use_the_pricing_table(self):
        rep = self.rep("cost", windows=["first=2031-01-02T00:00:00Z..2031-01-02T00:00:30Z"])
        comp = {r["component"]: r for r in rows(rep, "components")}
        self.assertEqual(comp["cache_read"]["tokens"], 1000)
        self.assertAlmostEqual(comp["cache_read"]["cost_usd"], 0.0002, places=9)
        self.assertAlmostEqual(comp["cache_write_1h"]["cost_usd"], 0.008, places=9)   # 1000 x 4 x 2.0
        self.assertAlmostEqual(comp["cache_write_5m"]["cost_usd"], 0.005, places=9)   # 1000 x 4 x 1.25
        self.assertAlmostEqual(comp["input"]["cost_usd"], 0.004, places=9)
        self.assertAlmostEqual(comp["output"]["cost_usd"], 0.02, places=9)
        self.assertAlmostEqual(sum(r["cost_share"] for r in comp.values()), 1.0, places=9)
        self.assertAlmostEqual(rows(rep, "summary")[0]["cost_usd"], 0.0372, places=9)

    def test_by_day_uses_the_display_timezone(self):
        local = {r["day"]: r for r in rows(self.rep("cost", tz="+08:00"), "by_day")}
        self.assertEqual(sorted(local), ["2031-01-02", "2031-01-03"])   # m5 at 20:00Z is 04:00 the next day in +08:00
        self.assertAlmostEqual(local["2031-01-03"]["cost_usd"], 0.1, places=9)
        self.assertAlmostEqual(local["2031-01-03"]["main_usd"], 0.1, places=9)
        self.assertAlmostEqual(local["2031-01-02"]["main_usd"], 0.0372 + 0.0104 + 0.742 + 0.022 + 0.003, places=9)
        self.assertAlmostEqual(local["2031-01-02"]["subagent_usd"], 0.00539 + 4 * 0.0026, places=9)
        utc = rows(self.rep("cost", tz="UTC"), "by_day")
        self.assertEqual([r["day"] for r in utc], ["2031-01-02"])

    def test_corrected_flag_prices_estimated_output_next_to_raw(self):
        rep = self.rep("cost", corrected=True)
        s = rows(rep, "summary")[0]
        self.assertAlmostEqual(s["cost_usd"], TOTAL_EST, places=9)
        self.assertAlmostEqual(s["cost_raw_usd"], TOTAL_RAW, places=9)
        out = {r["component"]: r for r in rows(rep, "components")}["output"]
        self.assertEqual(out["tokens"], 3160 + 9 * 680)   # raw output of the 13 priced requests + 680 on each of 9 opus requests

    def test_without_the_flag_there_is_no_estimate_column(self):
        self.assertNotIn("cost_raw_usd", tables(self.rep("cost"))["summary"]["columns"])

    # -- filters and windows ----------------------------------------------------

    def test_project_and_exclude_session_filters(self):
        only_b = rows(self.rep("cost", projects=["beta"]), "summary")[0]
        self.assertEqual(only_b["reqs"], 2)
        self.assertAlmostEqual(only_b["cost_usd"], 0.003, places=9)
        no_a = rows(self.rep("cost", exclude=["sess-aaaa"]), "summary")[0]
        self.assertEqual(no_a["reqs"], 2)
        self.assertAlmostEqual(no_a["cost_usd"], 0.003, places=9)

    def test_windows_split_the_totals_and_end_is_exclusive(self):
        rep = self.rep("cost", windows=["a=..2031-01-02T02:00:00Z", "b=2031-01-02T02:00:00Z.."])
        self.assertEqual([w["name"] for w in rep["windows"]], ["a", "b"])
        a, b = rows(rep, "summary", 0)[0], rows(rep, "summary", 1)[0]
        self.assertEqual((a["reqs"], b["reqs"]), (11, 3))   # m3 sits exactly on the boundary and belongs to b only
        self.assertAlmostEqual(a["cost_usd"] + b["cost_usd"], TOTAL_RAW, places=9)
        self.assertAlmostEqual(b["cost_usd"], 0.742 + 0.022 + 0.1, places=9)

    def test_window_bounds_are_read_in_the_given_timezone(self):
        tz = usagelib.parse_tz("+08:00")
        win = report.parse_windows(["x=2031-01-02T08:00..2031-01-02T09:00+00:00"], tz)[0]
        self.assertEqual(win.lo, "2031-01-02T00:00:00.000Z")   # naive bound read as +08:00
        self.assertEqual(win.hi, "2031-01-02T09:00:00.000Z")   # explicit offset wins
        self.assertEqual([w.name for w in report.parse_windows([], tz)], ["all"])

    def test_bad_window_specs_are_rejected(self):
        tz = usagelib.parse_tz("UTC")
        for bad in ("2031-01-01..2031-01-02", "w=2031-01-01", "=2031-01-01..2031-01-02"):
            with self.assertRaises(ValueError, msg=bad):
                report.parse_windows([bad], tz)
        with self.assertRaises(ValueError):
            report.parse_windows(["w=2031-01-01..2031-01-02", "w=2031-01-03.."], tz)
        with self.assertRaises(ValueError):
            report.parse_windows(["w=2031-01-02..2031-01-01"], tz)

    # -- cache ------------------------------------------------------------------

    def test_cache_gap_buckets_and_expired_rewrites(self):
        rep = self.rep("cache", projects=["alpha"])
        gaps = {r["scope"]: r for r in rows(rep, "gaps")}
        self.assertEqual((gaps["main"]["intervals"], gaps["main"]["le5m"], gaps["main"]["m5_60"], gaps["main"]["gt60m"]), (4, 1, 1, 2))
        self.assertAlmostEqual(gaps["main"]["gt60m_share"], 0.5)
        self.assertEqual((gaps["subagent"]["intervals"], gaps["subagent"]["le5m"], gaps["subagent"]["m5_60"], gaps["subagent"]["gt60m"]), (2, 1, 1, 0))
        rw = {r["scope"]: r for r in rows(rep, "rewrites")}
        # main: m3 and m5 follow a gap > 60m, only m3 is mostly cache write (90000 of 100000)
        self.assertEqual((rw["main"]["reqs_after_gap"], rw["main"]["rewrite_reqs"]), (2, 1))
        self.assertAlmostEqual(rw["main"]["rewrite_cw_usd"], 0.72, places=9)
        # subagent: s2 follows a 10 minute gap and is 800 of 900 cache write
        self.assertEqual((rw["subagent"]["reqs_after_gap"], rw["subagent"]["rewrite_reqs"]), (1, 1))
        self.assertAlmostEqual(rw["subagent"]["rewrite_cw_usd"], 0.002, places=9)

    def test_cache_gap_belongs_to_the_window_of_the_later_request(self):
        rep = self.rep("cache", projects=["alpha"], windows=["late=2031-01-02T01:00:00Z.."])
        main = {r["scope"]: r for r in rows(rep, "gaps")}["main"]
        # m3 is the first main request in the window but still has its 1h59m gap from m2; m1 -> m2 is outside
        self.assertEqual((main["intervals"], main["le5m"], main["m5_60"], main["gt60m"]), (3, 0, 1, 2))

    def test_cache_write_ttl_table_counts_unknown_breakdowns(self):
        ttl = {r["scope"]: r for r in rows(self.rep("cache", projects=["alpha"]), "cw_ttl")}
        self.assertEqual((ttl["main"]["cw_reqs"], ttl["main"]["ttl_unknown_reqs"]), (2, 0))
        self.assertEqual((ttl["main"]["cw1h_tokens"], ttl["main"]["cw5m_tokens"]), (91000, 1000))
        self.assertEqual((ttl["subagent"]["cw_reqs"], ttl["subagent"]["ttl_unknown_reqs"]), (3, 1))
        self.assertAlmostEqual(ttl["subagent"]["ttl_unknown_share"], 1 / 3)
        self.assertEqual((ttl["subagent"]["cw1h_tokens"], ttl["subagent"]["cw5m_tokens"]), (0, 1300))
        self.assertEqual(rows(self.rep("cost"), "summary")[0]["cw_ttl_unknown_reqs"], 1)

    # -- context ----------------------------------------------------------------

    def test_context_percentiles_buckets_and_first_request(self):
        rep = self.rep("context", projects=["alpha"])
        main = rows(rep, "main_ctx")[0]
        self.assertEqual((main["reqs"], main["median"], main["p90"], main["max"]), (5, 100000, 340000, 500000))
        self.assertAlmostEqual(main["gt400k_share"], 0.2)
        buckets = {r["bucket"]: r["reqs"] for r in rows(rep, "buckets")}
        self.assertEqual(buckets, {"lt100k": 2, "100k_200k": 2, "200k_400k": 0, "gt400k": 1})   # 100,000 is in 100k_200k
        first = {r["type"]: r for r in rows(rep, "sub_first_ctx")}
        self.assertEqual((first["worker"]["agents"], first["worker"]["median"]), (1, 600))
        self.assertEqual((first["verifier"]["agents"], first["verifier"]["median"]), (4, 1100))
        self.assertEqual(rows(rep, "compact"), [{"compact_boundaries": 1, "sessions_with_compact": 1}])

    # -- reports / agents -------------------------------------------------------

    def test_report_lengths_and_agent_tool_result_lengths(self):
        rep = self.rep("reports")
        by = {r["type"]: r for r in rows(rep, "final_chars")}
        self.assertEqual((by["worker"]["median"], by["worker"]["max"]), (1200, 1200))
        self.assertEqual((by["verifier"]["agents"], by["verifier"]["median"], by["verifier"]["max"]), (4, 550, 800))
        self.assertAlmostEqual(by["verifier"]["handback_share"], 0.75)
        self.assertEqual(by["ALL"]["agents"], 5)
        res = {(r["subagent_type"], r["mode"]): r for r in rows(rep, "result_chars")}
        self.assertEqual(res[("worker", "async")]["median"], 1100)
        self.assertEqual(res[("worker", "sync")]["median"], 300)
        self.assertEqual((res[("verifier", "sync")]["calls"], res[("verifier", "sync")]["median"]), (1, 500))   # tu8; tu4 is an is_error result

    def test_agent_sizes_come_from_requests_and_notifications(self):
        rows_ = {r["type"]: r for r in rows(self.rep("agents"), "agents")}
        w = rows_["worker"]
        self.assertEqual((w["agents"], w["reqs_median"], w["tools_median"]), (1, 3, 5))
        self.assertAlmostEqual(w["wall_min_median"], 10.5)          # 00:10:00 -> 00:20:30
        self.assertAlmostEqual(w["cost_usd"], 0.00539, places=9)
        self.assertEqual(w["notif_tokens_median"], 5000)
        v = rows_["verifier"]
        self.assertEqual(v["agents"], 4)
        self.assertEqual(v["notif_tokens_median"], 7000)            # only ag2 has a matching Agent call

    # -- dispatch ---------------------------------------------------------------

    def test_dispatch_parallelism_groups_overlapping_calls(self):
        rep = self.rep("dispatch")
        p = rows(rep, "parallelism")[0]
        # tu1 [00:05, 00:30], tu2 [00:10, 00:40], tu3 [00:35, 00:36] chain into one group with two in flight at most;
        # tu4 ends exactly when tu6 starts (no overlap); tu5 never got a notification or result, so it runs to the
        # session's last event (20:00) and chains tu8 [07:00, 07:01] and tu7 [08:00, 08:01] into a second group
        self.assertEqual((p["calls"], p["parallel_groups"], p["calls_in_groups"], p["max_concurrency"]), (8, 2, 6, 2))
        self.assertEqual(p["unterminated_calls"], 1)
        top = rows(rep, "top_groups")
        self.assertEqual((len(top), sum(r["calls"] for r in top), top[0]["calls"], top[0]["sid"]), (2, 6, 3, SID_A[:8]))

    def test_dispatch_counts_parameters_errors_and_notification_status(self):
        rep = self.rep("dispatch")
        combos = {(r["subagent_type"], r["background"]): r["calls"] for r in rows(rep, "combos")}
        self.assertEqual(combos[("worker", "true")], 1)    # tu1
        self.assertEqual(combos[("worker", "false")], 1)   # tu6
        self.assertEqual(combos[("worker", None)], 1)      # tu5
        calls = rows(rep, "calls")[0]
        self.assertEqual((calls["calls"], calls["result_is_error"], calls["no_result"], calls["with_notification"]), (8, 1, 1, 3))
        status = {r["status"]: r["calls"] for r in rows(rep, "notification_status")}
        self.assertEqual(status, {"completed": 2, "killed": 1, "(none)": 5})

    # -- controller -------------------------------------------------------------

    def test_controller_counts_edits_between_worker_return_and_next_verifier(self):
        row = rows(self.rep("controller"), "controller")[0]
        self.assertEqual(row["slug"], SLUG_A)
        self.assertEqual((row["agent_calls"], row["main_edits"], row["bash_writes_heuristic"]), (8, 6, 3))
        self.assertAlmostEqual(row["direct_per_call"], 9 / 8)
        # worker tu1 returns 00:30 and the next verifier goes out 05:00: edits at 01:00 and 04:59 count; worker tu6 returns
        # 05:02 and the next verifier (tu8) goes out 07:00: the edit at 05:30 counts. Not counted: 00:20 (before any worker
        # returned), 05:00:30 (between a verifier dispatch and the next worker return) and 08:30 (after tu8; the Plan call
        # tu7 returning at 08:01 is not a worker)
        self.assertEqual(row["edits_after_worker_heuristic"], 3)
        self.assertEqual(row["bash_writes_after_worker_heuristic"], 1)   # 02:00 only; 00:01 is early, 05:00:40 follows a verifier dispatch
        all_row = rows(self.rep("controller"), "controller")[-1]
        self.assertEqual((all_row["slug"], all_row["main_edits"], all_row["sessions"]), ("ALL", 6, 1))

    # -- verifier ---------------------------------------------------------------

    def test_verifier_verdict_regex(self):
        v = {r["verdict_heuristic"]: r for r in rows(self.rep("verifier"), "verdicts")}
        self.assertEqual(v["CONVERGED"]["agents"], 1)
        self.assertEqual(v["PROSE-ONLY"]["agents"], 1)       # leftmost verdict wins over the OPEN later in the text
        self.assertEqual(v["OPEN"]["agents"], 1)             # bold **OPEN**
        self.assertEqual(v["(unclassified)"]["agents"], 1)   # REOPENED is not OPEN
        self.assertEqual(v["ALL"]["agents"], 4)
        self.assertAlmostEqual(v["CONVERGED"]["cost_usd"], 0.0026, places=9)
        self.assertAlmostEqual(v["ALL"]["cost_usd"], 4 * 0.0026, places=9)
        self.assertIn("verdict_heuristic", tables(self.rep("verifier"))["verdicts"]["columns"])
        early = {r["verdict_heuristic"]: r for r in rows(self.rep("verifier", windows=["early=..2031-01-02T00:40:00Z"]), "verdicts")}
        self.assertEqual(sorted(early), ["ALL", "CONVERGED"])   # only ag2 starts before 00:40; a subagent belongs to the window it starts in

    def test_verdict_of_directly(self):
        for head, expected in (("INCONCLUSIVE\n\nno log", "INCONCLUSIVE"), ("OPEN", "OPEN"), ("nothing here", "(unclassified)"),
                               ("x CONVERGED y OPEN", "CONVERGED"), ("OPENED the file", "(unclassified)"), ("", "(unclassified)")):
            self.assertEqual(report.verdict_of({"final_head": head}), expected, head)

    # -- sessions ---------------------------------------------------------------

    def test_sessions_are_ranked_by_cost(self):
        rep = self.rep("sessions", top=1)
        out = rows(rep, "sessions")
        self.assertEqual(len(out), 1)
        s = out[0]
        self.assertEqual((s["sid"], s["slug"], s["title"]), (SID_A[:8], SLUG_A, "alpha work"))
        self.assertAlmostEqual(s["cost_usd"], TOTAL_RAW - 0.003, places=9)   # main + subagents of alpha
        self.assertEqual((s["reqs"], s["agent_calls"], s["human_msgs"]), (12, 8, 2))   # human + ask_answer only
        both = rows(self.rep("sessions", top=5), "sessions")
        self.assertEqual([r["sid"] for r in both], [SID_A[:8], SID_B[:8]])

    # -- output formats and the command line ------------------------------------

    def run_cli(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = report.main(argv)
        return code, out.getvalue()

    def test_cli_json_and_markdown_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps(self.data), encoding="utf-8")
            code, text = self.run_cli(["cost", "--data", str(path), "--format", "json", "--tz", "UTC", "--window", "w=2031-01-02T00:00:00Z.."])
            self.assertEqual(code, 0)
            rep = json.loads(text)
            self.assertEqual((rep["command"], rep["windows"][0]["name"]), ("cost", "w"))
            summary = next(t for t in rep["windows"][0]["tables"] if t["id"] == "summary")
            self.assertAlmostEqual(summary["rows"][0]["cost_usd"], TOTAL_RAW, places=6)
            code, text = self.run_cli(["verifier", "--data", str(path)])
            self.assertEqual(code, 0)
            self.assertTrue(text.startswith("# usage-review: verifier"))
            self.assertIn("| verdict_heuristic |", text)
            self.assertIn("| CONVERGED | 1 |", text)

    def test_cli_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text(json.dumps(self.data), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    report.main(["cost", "--data", str(path), "--window", "nonsense"])
                self.assertEqual(cm.exception.code, 2)
                old = dict(self.data, schema_version=99)
                bad = Path(tmp) / "old.json"
                bad.write_text(json.dumps(old), encoding="utf-8")
                self.assertEqual(report.main(["cost", "--data", str(bad)]), 1)
                self.assertEqual(report.main(["cost", "--data", str(Path(tmp) / "missing.json")]), 1)

    def test_markdown_escapes_pipes_and_marks_empty_tables(self):
        self.assertEqual(report.fmt_cell("title", "a|b\nc"), "a\\|b c")
        self.assertEqual(report.fmt_cell("cost_usd", 1234.5), "$1,234.50")
        self.assertEqual(report.fmt_cell("cost_usd", 0.0026), "$0.003")
        self.assertEqual(report.fmt_cell("x_share", 0.25), "25.0%")
        self.assertEqual(report.fmt_cell("n", None), "-")
        empty = report.render_table_md(report.table("t", "Title", ["a"], []))
        self.assertIn("（無資料）", empty)

    # -- contract with extract.py ------------------------------------------------

    def test_every_command_runs_on_real_extract_output(self):
        spec = importlib.util.spec_from_file_location("usage_review_extract_tests", REPO_ROOT / "tests" / "test_usage_review_extract.py")
        assert spec and spec.loader
        helpers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helpers)
        with tempfile.TemporaryDirectory() as tmp:
            data = helpers.run_extract(helpers.build_root(tmp))
        self.assertGreater(len(data["reqs"]), 0)
        for command in report.COMMANDS:
            rep = report.make_report(data, command, tz="UTC")
            json.loads(report.to_json(rep))
            self.assertIn("usage-review", report.render_md(rep))
        total = rows(report.make_report(data, "cost", tz="UTC"), "summary")[0]["cost_usd"]
        self.assertAlmostEqual(total, sum(r["cost_raw"] for r in data["reqs"] if r["cost_raw"] is not None), places=9)
        calls = rows(report.make_report(data, "dispatch", tz="UTC"), "calls")[0]
        self.assertEqual((calls["calls"], calls["with_notification"], calls["no_result"]), (3, 2, 0))
        self.assertEqual(len(rows(report.make_report(data, "agents", tz="UTC"), "agents")), 1)


if __name__ == "__main__":
    unittest.main()
