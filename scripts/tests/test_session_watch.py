"""scripts/session-watch.py 的測試。執行：python3 -m unittest scripts/tests/test_session_watch.py

測合併與分類（純函式），以及 `--under`／`--dispatched-by` 的範圍（替掉對外的兩個呼叫，jsonl 用暫存檔）；issue-status.py 與 stall-check.py 各有自己的測試。"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "session-watch.py"
spec = importlib.util.spec_from_file_location("session_watch", SCRIPT)
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)

WT = "/r/widgets/.worktrees/issue-1"


def row(**over):
    base = {"path": WT, "repo": "/r/widgets", "status": "working", "reported_status": "working", "reason": None,
            "result_mtime": "2026-01-01T00:00:00+00:00", "result_age": "1m", "pr_text": "-",
            "pending_authorization": "無", "blocker": "無", "issue": "#1"}
    return {**base, **over}


def sess(state="working", cwd=WT):
    return {"name": "s", "state": state, "silent": "  0m05s", "cwd": cwd}


class Classify(unittest.TestCase):
    def one(self, r, sessions):
        return sw.join([r], sessions)[0]

    def test_in_flight_with_working_session_needs_nothing(self):
        out = self.one(row(), [sess()])
        self.assertEqual((out["status"], out["attention"]), ("working", ""))
        self.assertEqual(out["name"], "widgets/issue-1")

    def test_in_flight_but_session_idle_is_waiting_for_input(self):
        self.assertEqual(self.one(row(), [sess("idle")])["attention"], "input")

    def test_in_flight_without_session(self):
        self.assertEqual(self.one(row(), [sess(cwd="/elsewhere")])["attention"], "nosession")

    def test_in_flight_with_pending_is_users_turn(self):
        self.assertEqual(self.one(row(pending_authorization="merge PR"), [sess()])["attention"], "you")

    def test_blocked_and_ready_are_users_turn_even_without_session(self):
        for st in ("blocked", "ready for authorization"):
            self.assertEqual(self.one(row(status=st, reported_status=st), [])["attention"], "you")

    def test_stale_in_flight_shows_reported_status_not_unknown(self):
        out = self.one(row(status="unknown", reason="result.md 過時：Dirty 不符"), [sess()])
        self.assertEqual((out["status"], out["attention"]), ("working", ""))

    def test_other_unknown_asks_for_a_check_with_the_reason(self):
        out = self.one(row(status="unknown", reason="Dirty 缺或不是整數"), [sess()])
        self.assertEqual((out["status"], out["attention"], out["note"]), ("unknown", "check", "Dirty 缺或不是整數"))

    def test_merged_is_done(self):
        self.assertEqual(self.one(row(status="merged", reported_status="merged"), [])["attention"], "done")


class Join(unittest.TestCase):
    def test_worktree_without_result_or_session_is_dropped(self):
        self.assertEqual(sw.join([row(result_mtime=None, status="unknown", reported_status=None)], []), [])

    def test_worktree_without_result_but_with_session_is_kept(self):
        out = sw.join([row(result_mtime=None, status="unknown", reported_status=None, reason="無 result.md")], [sess()])
        self.assertEqual(out[0]["attention"], "check")

    def test_session_in_subdirectory_matches_and_sibling_prefix_does_not(self):
        self.assertIsNotNone(sw.join([row()], [sess(cwd=WT + "/app")])[0]["session"])
        self.assertIsNone(sw.join([row()], [sess(cwd=WT + "-2")])[0]["session"])

    def test_session_in_nested_worktree_belongs_to_the_child(self):
        out = sw.join([row()], [sess("idle"), sess("working", cwd=WT + "/.worktrees/slice")])
        self.assertEqual((out[0]["session"]["state"], out[0]["attention"]), ("idle", "input"))

    def test_most_active_session_wins(self):
        out = sw.join([row()], [sess("idle"), sess("working")])
        self.assertEqual(out[0]["session"]["state"], "working")

    def test_rows_needing_attention_sort_first(self):
        a = row(path="/r/widgets/.worktrees/a")
        b = row(path="/r/widgets/.worktrees/b")
        out = sw.join([a, b], [sess(cwd=a["path"]), sess("idle", cwd=b["path"])])
        self.assertEqual([o["name"] for o in out], ["widgets/b", "widgets/a"])


class Under(unittest.TestCase):
    def repos_queried(self, under):
        sessions = [sess(cwd="/r/ws"), sess(cwd="/r/ws/api/.worktrees/issue-2"), sess(cwd="/r/ws-other"),
                    sess(cwd="/r/elsewhere/.worktrees/x")]
        checkout = {"/r/ws": "/r/ws", "/r/ws/api/.worktrees/issue-2": "/r/ws/api", "/r/ws-other": "/r/ws-other",
                    "/r/elsewhere/.worktrees/x": "/r/elsewhere", "/r/ws/.worktrees/coord": "/r/ws"}
        queried = []

        def fake_run_json(argv, timeout=25):
            if "--repo" not in argv:
                return sessions
            queried.append(argv[argv.index("--repo") + 1])
            return []
        real = sw.run_json, sw.main_checkout
        sw.run_json, sw.main_checkout = fake_run_json, checkout.get
        try:
            self.scope = sw.collect([], under)["scope"]
        finally:
            sw.run_json, sw.main_checkout = real
        return queried

    def test_without_under_every_session_repo_is_queried(self):
        self.assertEqual(self.repos_queried(None), ["/r/elsewhere", "/r/ws", "/r/ws-other", "/r/ws/api"])
        self.assertEqual(self.scope, "all")

    def test_under_keeps_the_repo_and_nested_repos_only(self):
        self.assertEqual(self.repos_queried("/r/ws"), ["/r/ws", "/r/ws/api"])

    def test_under_given_a_worktree_resolves_to_its_main_checkout(self):
        self.assertEqual(self.repos_queried("/r/ws/.worktrees/coord"), ["/r/ws", "/r/ws/api"])


def log_line(role, block):
    return json.dumps({"type": role, "message": {"role": role, "content": [block]}}, ensure_ascii=False)


class Dispatched(unittest.TestCase):
    A = "/r/api/.orca/workspaces/api/issue-1"
    B = "/r/web/.orca/workspaces/web/issue-1"
    C = "/r/web/.orca/workspaces/web/issue-2"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.projects = Path(self.tmp.name)
        (self.projects / "-r-ws").mkdir()
        launch = lambda i, cmd: log_line("assistant", {"type": "tool_use", "id": i, "name": "Bash", "input": {"command": cmd}})
        result = lambda i, text: log_line("user", {"type": "tool_result", "tool_use_id": i, "content": text})
        (self.projects / "-r-ws" / "sid.jsonl").write_text("\n".join([
            launch("t1", "W=/r/api; orca worktree create --repo path:$W --name issue-1 --agent claude"),
            result("t1", json.dumps({"ok": True, "path": self.A})),
            launch("t2", "orca worktree create --repo path:/r/web --name issue-1 --json"),
            log_line("user", {"type": "tool_result", "tool_use_id": "t2",
                              "content": [{"type": "text", "text": json.dumps({"result": {"worktree": {"path": self.B}}})}]}),
            launch("t4", "orca worktree create --repo path:/r/web --name issue-2 --json | jq -r .result.worktree.path"),
            result("t4", "True " + self.C + "\nbrief /r/ws/.worktrees/briefs/issue-2.md"),
            launch("t3", "ls /r/other"),
            result("t3", json.dumps({"path": "/r/other/not-a-launch"})),
            "not json",
        ]))

    def test_candidates_come_from_launch_results_only_even_when_filtered_to_bare_paths(self):
        self.assertEqual(sw.dispatched_paths("sid", self.projects),
                         {self.A, self.B, self.C, "/r/ws/.worktrees/briefs/issue-2.md"})

    def test_only_existing_non_main_worktrees_are_kept(self):
        with tempfile.TemporaryDirectory() as d:
            wt, main, gone = f"{d}/main/.worktrees/a", f"{d}/main", f"{d}/main/.worktrees/gone"
            sub = f"{main}/docs"  # 主 checkout 底下的一般子目錄：git 會回同一個主 checkout，但它不是 worktree
            Path(wt).mkdir(parents=True)
            Path(wt, ".git").write_text("gitdir: elsewhere\n")
            Path(sub).mkdir()
            Path(main, ".git").mkdir()
            Path(f"{d}/plain").mkdir()
            real = sw.main_checkout
            sw.main_checkout = {wt: main, main: main, sub: main}.get
            try:
                self.assertEqual(sw.worktrees_among({wt + "/", main, sub, gone, f"{d}/plain"}), {wt: main})
            finally:
                sw.main_checkout = real

    def test_unknown_session_has_no_paths(self):
        self.assertEqual(sw.dispatched_paths("other", self.projects), set())

    def add_log(self, project, session_id, lines=()):
        (self.projects / project).mkdir(exist_ok=True)
        (self.projects / project / f"{session_id}.jsonl").write_text("\n".join(lines))

    def launch_lines(self, tool_id, path):
        return [log_line("assistant", {"type": "tool_use", "id": tool_id, "name": "Bash",
                                       "input": {"command": "orca worktree create --name x --json"}}),
                log_line("user", {"type": "tool_result", "tool_use_id": tool_id, "content": json.dumps({"path": path})})]

    def test_takeover_session_in_the_same_checkout_inherits_earlier_launches(self):
        mine = "/r/api/.orca/workspaces/api/issue-9"
        self.add_log("-r-ws", "fresh")  # 剛接手、還沒派過任何東西
        self.add_log("-r-ws", "next", self.launch_lines("n1", mine))  # 接手後自己又派了一個
        inherited = {self.A, self.B, self.C, "/r/ws/.worktrees/briefs/issue-2.md"}
        self.assertEqual(sw.dispatched_paths("fresh", self.projects), inherited | {mine})
        self.assertEqual(sw.dispatched_paths("next", self.projects), inherited | {mine})

    def test_sessions_of_another_checkout_are_not_mixed_in(self):
        far = "/r/far/.orca/workspaces/far/issue-7"
        self.add_log("-r-far", "elsewhere", self.launch_lines("f1", far))
        self.add_log("-r-far", "idle")
        self.assertNotIn(far, sw.dispatched_paths("sid", self.projects))
        self.assertEqual(sw.dispatched_paths("idle", self.projects), {far})

    def test_result_after_unrelated_lines_is_still_matched_to_its_launch(self):
        launch, result = self.launch_lines("late", self.A)
        noise = log_line("user", {"type": "tool_result", "tool_use_id": "zzz", "content": "/r/noise/path"})
        self.add_log("-r-solo", "solo", [launch, noise, noise, result, noise])
        self.assertEqual(sw.dispatched_paths("solo", self.projects), {self.A})

    def test_unreadable_log_in_the_directory_is_skipped(self):
        (self.projects / "-r-ws" / "broken.jsonl").mkdir()  # open() 會丟 OSError
        self.assertIn(self.A, sw.dispatched_paths("sid", self.projects))

    def test_takeover_session_gets_the_dispatched_scope(self):
        self.add_log("-r-ws", "fresh")
        data, queried = self.collect("fresh")
        self.assertEqual((data["scope"], queried), ("dispatched", ["/r/api", "/r/web"]))
        self.assertEqual([r["path"] for r in data["rows"]], [self.A])

    def collect(self, session_id):
        api_rows = [row(path=self.A, repo="/r/api"), row(path="/r/api/.worktrees/someone-else", repo="/r/api")]
        queried = []

        def fake_run_json(argv, timeout=25):
            if "--repo" not in argv:
                return [sess(cwd="/r/ws"), sess(cwd="/r/ws/.worktrees/local")]
            queried.append(argv[argv.index("--repo") + 1])
            return {"/r/api": api_rows, "/r/ws": [row(path="/r/ws/.worktrees/local", repo="/r/ws")]}.get(queried[-1], [])
        checkout = {"/r/ws": "/r/ws", "/r/ws/.worktrees/local": "/r/ws"}
        among = lambda c: {p: m for p, m in {self.A: "/r/api", self.B: "/r/web"}.items() if p in c}
        real = sw.run_json, sw.main_checkout, sw.PROJECTS, sw.worktrees_among
        sw.run_json, sw.main_checkout, sw.PROJECTS, sw.worktrees_among = fake_run_json, checkout.get, self.projects, among
        try:
            return sw.collect([], "/r/ws", session_id), queried
        finally:
            sw.run_json, sw.main_checkout, sw.PROJECTS, sw.worktrees_among = real

    def test_dispatched_scope_lists_only_this_sessions_worktrees_across_repos(self):
        data, queried = self.collect("sid")
        self.assertEqual((data["scope"], queried), ("dispatched", ["/r/api", "/r/web"]))
        self.assertEqual([r["path"] for r in data["rows"]], [self.A])

    def test_session_that_dispatched_nothing_falls_back_to_under(self):
        data, queried = self.collect("other")
        self.assertEqual((data["scope"], queried), ("under", ["/r/ws"]))
        self.assertEqual([r["path"] for r in data["rows"]], ["/r/ws/.worktrees/local"])


if __name__ == "__main__":
    unittest.main()
