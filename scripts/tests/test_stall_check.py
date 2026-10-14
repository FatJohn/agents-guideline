"""scripts/stall-check.py 的測試。執行：python3 -m unittest scripts/tests/test_stall_check.py"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "stall-check.py"
spec = importlib.util.spec_from_file_location("stall_check", SCRIPT)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def ts(minutes_ago):
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def assistant(minutes_ago, tool_uses=()):
    content = [{"type": "text", "text": "x"}] + [
        {"type": "tool_use", "id": i, "name": n} for i, n in tool_uses
    ]
    return {"type": "assistant", "timestamp": ts(minutes_ago), "message": {"content": content}}


def result(minutes_ago, *ids):
    return {"type": "user", "timestamp": ts(minutes_ago),
            "message": {"content": [{"type": "tool_result", "tool_use_id": i} for i in ids]}}


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
        f.write("not json\n")  # 壞行要被略過
        f.write(json.dumps({"type": "attachment", "timestamp": ts(0)}) + "\n")  # 非訊息列不算靜默終點


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_idle_when_every_tool_use_has_a_result(self):
        p = self.dir / "s.jsonl"
        write_jsonl(p, [assistant(10, [("t1", "Bash")]), result(9, "t1"), assistant(8)])
        last, outstanding, kind = sc.scan(p)
        self.assertEqual(outstanding, [])
        self.assertEqual(last, NOW - timedelta(minutes=8))
        self.assertEqual(kind, "assistant-end")

    def test_outstanding_tool_use_is_reported_with_name_and_send_time(self):
        p = self.dir / "s.jsonl"
        write_jsonl(p, [assistant(10, [("t1", "Bash")]), result(9, "t1"), assistant(7, [("t2", "Edit")])])
        last, outstanding, kind = sc.scan(p)
        self.assertEqual(kind, "assistant-tool")
        self.assertEqual([(i, n) for i, n, _ in outstanding], [("t2", "Edit")])
        self.assertEqual(outstanding[0][2], NOW - timedelta(minutes=7))


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = Path(self.tmp.name)
        self.cwd = "/Users/x/proj/.orca/workspaces/proj/issue-1"
        self.pdir = self.projects / "-Users-x-proj--orca-workspaces-proj-issue-1"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, procs, argv=()):
        out = io.StringIO()
        procs = [p if len(p) == 3 else (p[0], p[1], NOW - timedelta(hours=1)) for p in procs]
        with mock.patch.object(sc, "PROJECTS", self.projects), \
             mock.patch.object(sc, "SESSIONS", self.projects / "sessions"), \
             mock.patch.object(sc, "running_claude_processes", return_value=procs), \
             mock.patch.object(sc, "datetime", wraps=datetime) as dt, \
             mock.patch.object(sys, "argv", ["stall-check.py", *argv]), \
             redirect_stdout(out):
            dt.now.return_value = NOW
            sc.main()
        return out.getvalue()

    def test_idle_working_quiet_and_no_log_states(self):
        write_jsonl(self.pdir / "a.jsonl", [assistant(10, [("t1", "Bash")]), result(9, "t1"), assistant(3)])
        working = self.projects / "-Users-x-w"
        write_jsonl(working / "a.jsonl", [assistant(2, [("t1", "Bash")])])
        quiet = self.projects / "-Users-x-q"
        write_jsonl(quiet / "a.jsonl", [assistant(6, [("t1", "Bash")])])
        out = self.run_main([(1, self.cwd), (2, "/Users/x/w"), (3, "/Users/x/q"), (4, "/Users/x/none")], ["--json"])
        rows = {r["pid"]: r for r in json.loads(out)}
        self.assertEqual(rows[1]["state"], "idle")
        self.assertEqual(rows[1]["silent"], "  3m00s")
        self.assertEqual((rows[2]["state"], rows[2]["outstanding"]), ("working", "Bash"))
        self.assertEqual((rows[3]["state"], rows[3]["outstanding"]), ("quiet", "Bash"))
        self.assertEqual(rows[4]["state"], "no-log")

    def test_quiet_threshold_is_configurable(self):
        write_jsonl(self.pdir / "a.jsonl", [assistant(6, [("t1", "Bash")])])
        rows = json.loads(self.run_main([(1, self.cwd)], ["--json", "--quiet-min", "10"]))
        self.assertEqual(rows[0]["state"], "working")

    def test_log_pairing_by_start_time_with_mtime_fallback(self):
        old = self.pdir / "old.jsonl"
        new = self.pdir / "new.jsonl"
        write_jsonl(old, [assistant(30, [("t1", "Bash")])])
        write_jsonl(new, [assistant(1)])
        import os
        os.utime(old, (1, 1))
        # process 啟動時間比兩個檔都早：兩個都是候選（/clear 後的形狀），取最近有動靜的＝new，不黏在舊檔
        rows = json.loads(self.run_main([(1, self.cwd, NOW - timedelta(minutes=40))], ["--json"]))
        self.assertEqual(rows[0]["state"], "idle")
        # 啟動時間晚於 old 的第一筆：只剩 new 是候選
        rows = json.loads(self.run_main([(1, self.cwd, NOW - timedelta(minutes=20))], ["--json"]))
        self.assertEqual(rows[0]["state"], "idle")
        # 啟動時間晚於兩個檔（resume 的情形）：沒有候選，退回 mtime 最新的 new
        rows = json.loads(self.run_main([(1, self.cwd, NOW)], ["--json"]))
        self.assertEqual(rows[0]["state"], "idle")

    def test_background_subagents_make_main_sub_and_finished_ones_are_hidden(self):
        # 背景 Agent：主 session 已收到 "launched" 的 tool_result 並收尾，subagent 仍在跑
        main_log = self.pdir / "s1.jsonl"
        write_jsonl(main_log, [assistant(8, [("a1", "Agent")]), result(8, "a1"), assistant(8)])
        subs = self.pdir / "s1" / "subagents"
        write_jsonl(subs / "agent-live.jsonl", [assistant(7, [("t9", "Bash")]), result(6, "t9"), assistant(1, [("t10", "Read")])])
        write_jsonl(subs / "agent-thinking.jsonl", [assistant(7, [("t9", "Bash")]), result(2, "t9")])
        done = result(3, "hb")
        done["toolEndsTurn"] = True  # SubagentHandback 的 tool_result：已交回報告
        write_jsonl(subs / "agent-done.jsonl", [assistant(4, [("hb", "SubagentHandback")]), done])
        rows = json.loads(self.run_main([(1, self.cwd)], ["--json"]))
        self.assertEqual(rows[0]["state"], "sub")
        self.assertIsNone(rows[0]["outstanding"])
        self.assertEqual([(s["file"], s["silent"], s["outstanding"]) for s in rows[0]["subagents"]],
                         [("agent-live.jsonl", "  1m00s", "Read"), ("agent-thinking.jsonl", "  2m00s", "(model)")])
        table = self.run_main([(1, self.cwd)])
        self.assertIn("└ sub", table)
        self.assertNotIn("agent-done.jsonl", table)

    def test_model_turn_is_turn_not_idle_and_goes_quiet_past_threshold(self):
        # P1：最後一筆是 30 分鐘前的 tool_result（模型那一輪卡住）
        write_jsonl(self.pdir / "a.jsonl", [assistant(31, [("t1", "Bash")]), result(30, "t1")])
        # P2：最後一筆是剛送出的 user prompt
        prompt_dir = self.projects / "-Users-x-p"
        write_jsonl(prompt_dir / "a.jsonl", [assistant(9), {"type": "user", "timestamp": ts(1), "message": {"content": "再來"}}])
        rows = {r["pid"]: r for r in json.loads(self.run_main([(1, self.cwd), (2, "/Users/x/p")], ["--json"]))}
        self.assertEqual((rows[1]["state"], rows[1]["outstanding"], rows[1]["silent"]), ("quiet", "(model)", " 30m00s"))
        self.assertEqual((rows[2]["state"], rows[2]["outstanding"]), ("turn", "(model)"))

    def test_two_processes_in_one_cwd_get_their_own_log_by_start_time(self):
        # P4：舊 session 卡在 Bash 30 分，新 session 剛收尾
        old_log = self.pdir / "old.jsonl"
        new_log = self.pdir / "new.jsonl"
        write_jsonl(old_log, [assistant(60), assistant(30, [("t1", "Bash")])])
        write_jsonl(new_log, [assistant(10), assistant(1)])
        old_start = NOW - timedelta(minutes=61)
        new_start = NOW - timedelta(minutes=11)
        rows = {r["pid"]: r for r in json.loads(self.run_main([(1, self.cwd, old_start), (2, self.cwd, new_start)], ["--json"]))}
        self.assertEqual((rows[1]["state"], rows[1]["outstanding"]), ("quiet", "Bash"))
        self.assertEqual(rows[2]["state"], "idle")


    def test_harness_sessions_json_wins_over_start_time_heuristic(self):
        # 兩個 process：啟動順序與檔案順序相反（舊 process /clear 後開了新檔、新 process 接手舊檔的 resume 情形）
        log_a = self.pdir / "aaaa.jsonl"
        log_b = self.pdir / "bbbb.jsonl"
        write_jsonl(log_a, [assistant(50), assistant(30, [("t1", "Bash")])])
        write_jsonl(log_b, [assistant(20), assistant(1)])
        sessions = self.projects / "sessions"
        sessions.mkdir()
        (sessions / "1.json").write_text(json.dumps({"pid": 1, "sessionId": "bbbb", "status": "busy", "statusUpdatedAt": int((NOW - timedelta(minutes=2)).timestamp() * 1000)}))
        (sessions / "2.json").write_text(json.dumps({"pid": 2, "sessionId": "aaaa", "status": "idle"}))
        rows = {r["pid"]: r for r in json.loads(self.run_main([(1, self.cwd, NOW - timedelta(minutes=60)), (2, self.cwd, NOW - timedelta(minutes=25))], ["--json"]))}
        self.assertEqual((rows[1]["state"], rows[1]["harness"]), ("idle", "busy@2m00s"))
        self.assertEqual((rows[2]["state"], rows[2]["outstanding"], rows[2]["harness"]), ("quiet", "Bash", "idle"))
        (sessions / "1.json").write_text("{not json")
        rows = {r["pid"]: r for r in json.loads(self.run_main([(1, self.cwd, NOW - timedelta(minutes=60))], ["--json"]))}
        self.assertEqual((rows[1]["state"], rows[1]["harness"]), ("idle", None))  # 壞檔退回啟發式：最近有動靜的 bbbb

    def test_local_command_compact_summary_and_interrupt_count_as_idle(self):
        cases = {
            "cmd": {"type": "user", "timestamp": ts(30), "message": {"content": "<command-name>/clear</command-name>\n<command-message>clear</command-message>"}},
            "stdout": {"type": "user", "timestamp": ts(30), "message": {"content": [{"type": "text", "text": "<local-command-stdout>(no content)</local-command-stdout>"}]}},
            "compact": {"type": "user", "timestamp": ts(30), "isCompactSummary": True, "message": {"content": "This session is being continued…"}},
            "interrupt": {"type": "user", "timestamp": ts(30), "message": {"content": [{"type": "text", "text": "[Request interrupted by user]"}]}},
        }
        procs = []
        for i, (name, rec) in enumerate(cases.items(), start=1):
            write_jsonl(self.projects / f"-Users-x-{name}" / "a.jsonl", [assistant(40), rec])
            procs.append((i, f"/Users/x/{name}"))
        rows = json.loads(self.run_main(procs, ["--json"]))
        self.assertEqual([r["state"] for r in rows], ["idle"] * 4)
        # 對照組：一般 prompt 與 task-notification 仍是輪到模型
        write_jsonl(self.projects / "-Users-x-notify" / "a.jsonl", [assistant(40), {"type": "user", "timestamp": ts(30), "message": {"content": "<task-notification>\n<task-id>x</task-id>"}}])
        rows = json.loads(self.run_main([(9, "/Users/x/notify")], ["--json"]))
        self.assertEqual((rows[0]["state"], rows[0]["outstanding"]), ("quiet", "(model)"))

    def test_interrupted_subagent_is_not_listed_as_running(self):
        main_log = self.pdir / "s1.jsonl"
        write_jsonl(main_log, [assistant(8, [("a1", "Agent")]), result(8, "a1"), assistant(8)])
        subs = self.pdir / "s1" / "subagents"
        write_jsonl(subs / "agent-killed.jsonl", [assistant(7, [("t9", "Bash")]), {"type": "user", "timestamp": ts(6), "message": {"content": [{"type": "text", "text": "[Request interrupted by user]"}]}}])
        rows = json.loads(self.run_main([(1, self.cwd)], ["--json"]))
        self.assertEqual((rows[0]["state"], rows[0]["subagents"]), ("idle", []))


    def test_sessions_json_pointing_at_pre_clear_log_is_overridden_by_its_successor(self):
        # json 仍指向 /clear 前的檔 aaaa；bbbb 在 aaaa 最後一筆之後才開始且更近期有動靜 → 配 bbbb
        write_jsonl(self.pdir / "aaaa.jsonl", [assistant(50), assistant(30, [("t1", "Bash")])])
        write_jsonl(self.pdir / "bbbb.jsonl", [assistant(20), assistant(1)])
        sessions = self.projects / "sessions"
        sessions.mkdir()
        (sessions / "1.json").write_text(json.dumps({"pid": 1, "sessionId": "aaaa", "status": "idle"}))
        rows = json.loads(self.run_main([(1, self.cwd, NOW - timedelta(minutes=60))], ["--json"]))
        self.assertEqual(rows[0]["state"], "idle")
        # 反例：bbbb 開始於 aaaa 最後一筆之前（另一個 session 的檔），json 照用
        write_jsonl(self.pdir / "bbbb.jsonl", [assistant(40), assistant(1)])
        rows = json.loads(self.run_main([(1, self.cwd, NOW - timedelta(minutes=60))], ["--json"]))
        self.assertEqual((rows[0]["state"], rows[0]["outstanding"]), ("quiet", "Bash"))


class ProcessListTests(unittest.TestCase):
    def test_ps_parsing_skips_chrome_native_host_and_keeps_bare_claude(self):
        comm = " 9048 claude\n26829 claude\n  500 node\n"
        args = (" 9048 Wed Oct 14 21:00:00 2026 claude\n"
                "26829 Wed Oct 14 20:00:00 2026 claude --chrome-native-host\n"
                "  500 Wed Oct 14 19:00:00 2026 /usr/bin/node /x/claude-helper.js\n")

        def fake_run(cmd, **kw):
            out = comm if "pid=,comm=" in cmd[2] else args
            return mock.Mock(stdout=out)

        with mock.patch.object(sc.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(sc, "process_cwd", return_value="/Users/x"):
            procs = sc.running_claude_processes()
        self.assertEqual([(p, c) for p, c, _ in procs], [(9048, "/Users/x")])
        self.assertEqual(procs[0][2].strftime("%Y-%m-%d %H:%M:%S"), "2026-10-14 21:00:00")


if __name__ == "__main__":
    unittest.main()
