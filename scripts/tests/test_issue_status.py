"""scripts/issue-status.py 的測試。執行：python3 -m unittest scripts/tests/test_issue_status.py

用 tempfile 建真的 git repo＋`git worktree add`；gh 以 patch `query_prs` 取代，orca 以 patch `orca_info` 取代。"""
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "issue-status.py"
spec = importlib.util.spec_from_file_location("issue_status", SCRIPT)
iss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iss)
REAL_ORCA_INFO = iss.orca_info

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


def write_result(wt, status="working", cand=None, dirty="0", merged="—", pending="無", blocker="無", extra=""):
    """寫成與模板相同的版面：Worktree／Branch、Base／Candidate／Dirty 各自同一行。"""
    if cand is None:
        cand = git(wt, "rev-parse", "--short", "HEAD")
    d = Path(wt) / ".worktrees"
    d.mkdir(exist_ok=True)
    (d / "result.md").write_text(
        "Issue: https://github.com/acme/widgets/issues/1\n"
        f"Status: {status}\n"
        f"Worktree: {wt}    Branch: x\n"
        f"Base SHA: abc1234    Candidate SHA: {cand}    Dirty: {dirty}\n"
        "Files changed: a.txt\n"
        "Verification: 未驗收\n"
        "PR / CI: 無\n"
        "Cross-issue risk: 無\n"
        f"Pending authorization: {pending}\n"
        f"Blocker: {blocker}\n"
        f"Merged: {merged}\n" + extra,
        encoding="utf-8",
    )


def pr(number, state):
    return {"number": number, "state": state, "url": f"https://github.com/acme/widgets/pull/{number}",
            "mergedAt": "2026-10-17T00:00:00Z" if state == "MERGED" else None, "headRefOid": "f" * 40}


class IssueStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self.tmp.name))
        env = mock.patch.dict(os.environ, GIT_ENV)
        env.start()
        self.addCleanup(env.stop)
        orca = mock.patch.object(iss, "orca_info", return_value={})
        orca.start()
        self.addCleanup(orca.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "remote", "add", "origin", "git@github.com:acme/widgets.git")
        (self.repo / "a.txt").write_text("a\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init")
        (self.repo / ".git" / "info" / "exclude").write_text(".worktrees/\n.orca/\n")

    def tearDown(self):
        self.tmp.cleanup()

    def add_wt(self, name, branch=None, outside=False):
        """預設建在 <repo>/.orca/workspaces/<name>（Orca 的位置）；outside=True 建在 repo 外。"""
        path = (self.root / "outside" / name) if outside else (self.repo / ".orca" / "workspaces" / name)
        git(self.repo, "worktree", "add", "-q", "-b", branch or f"feat/{name}", str(path))
        return path

    def commit(self, wt, fname="b.txt"):
        (Path(wt) / fname).write_text("b\n")
        git(wt, "add", fname)
        git(wt, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "more")

    def run_main(self, *args, gh=None):
        """跑 main；gh 是 query_prs 的替身（None＝不該被呼叫）。回 (rc, stdout, stderr)。"""
        out, err = io.StringIO(), io.StringIO()
        if gh is None:
            gh = mock.Mock(side_effect=AssertionError("query_prs 不該被呼叫"))
        elif not callable(gh):
            gh = mock.Mock(return_value=gh)
        with mock.patch.object(iss, "query_prs", gh), redirect_stdout(out), redirect_stderr(err):
            rc = iss.main(["--repo", str(self.repo), *args])
        return rc, out.getvalue(), err.getvalue()

    def rows(self, *args, gh=None):
        rc, out, _ = self.run_main("--json", *args, gh=gh)
        self.assertEqual(rc, 0)
        return {r["name"]: r for r in json.loads(out)}

    def _rel(self, name):
        return os.path.join(".orca", "workspaces", name)

    # --- 解析 ---
    def test_parse_result_tolerates_multi_field_lines_and_missing_fields(self):
        text = ("Issue: #7\nStatus: working\nWorktree: /w/x    Branch: feat/x\n"
                "Base SHA: abc1234    Candidate SHA: PR1 abc1234（已 merge）；PR2 進行中    Dirty: 2\n"
                "Blocker: 等 CI\n")
        f = iss.parse_result(text)
        self.assertEqual((f["Worktree"], f["Branch"]), ("/w/x", "feat/x"))
        self.assertEqual((f["Base SHA"], f["Candidate SHA"], f["Dirty"]),
                         ("abc1234", "PR1 abc1234（已 merge）；PR2 進行中", "2"))
        self.assertEqual(f["Blocker"], "等 CI")
        self.assertNotIn("Merged", f)
        self.assertNotIn("Pending authorization", f)

    def test_parse_result_reads_fields_after_headings_but_first_occurrence_wins(self):
        # 實際的 result.md 會把 Blocker／Merged 寫在 `##` 備註段落之後；備註內的條列不蓋掉header 欄位
        text = ("Status: working\nPending authorization: 無\n\n## 備註\n- Status: merged（備註內的條列）\n"
                "- 另一行 Merged: 這不是欄位\nBlocker: 等答覆\nMerged: —\nStatus: merged\n")
        f = iss.parse_result(text)
        self.assertEqual(f["Status"], "working")
        self.assertEqual((f["Blocker"], f["Merged"]), ("等答覆", "—"))

    def test_parse_slug_ssh_and_https(self):
        for url in ("git@github.com:acme/widgets.git", "https://github.com/acme/widgets",
                    "https://github.com/acme/widgets.git", "ssh://git@github.com/acme/widgets.git",
                    "https://tok@github.com/acme/widgets.git"):
            self.assertEqual(iss.parse_slug(url), "acme/widgets", url)
        self.assertIsNone(iss.parse_slug("not a url"))

    # --- 機械比對 ---
    def test_no_result_md_is_unknown(self):
        self.add_wt("a")
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("無 result.md", r["reason"])
        self.assertIsNone(r["result_mtime"])

    def test_working_with_matching_sha_and_dirty_stays_working(self):
        wt = self.add_wt("a")
        write_result(wt)
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual((r["status"], r["reason"]), ("working", None))
        self.assertEqual(r["dirty"], 0)
        self.assertEqual(r["head"], git(wt, "rev-parse", "HEAD"))
        self.assertIsNotNone(r["result_mtime"])

    def test_stale_candidate_sha_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt)
        self.commit(wt)
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("Candidate SHA ≠ HEAD", r["reason"])
        self.assertEqual(r["reported_status"], "working")
        self.assertRegex(r["result_mtime"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_uncommitted_candidate_skips_sha_comparison(self):
        wt = self.add_wt("a")
        self.commit(wt)
        (wt / "scratch.txt").write_text("x\n")
        write_result(wt, cand="uncommitted", dirty="1")
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual((r["status"], r["reason"]), ("working", None))

    def test_candidate_sha_free_text_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, cand="PR1 abc1234（已 merge）")
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("Candidate SHA", r["reason"])

    def test_dirty_mismatch_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, dirty="0")
        (wt / "scratch.txt").write_text("x\n")
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("Dirty 不符", r["reason"])
        self.assertEqual(r["dirty"], 1)

    def test_merged_without_merge_sha_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, status="merged", merged="—")
        r = self.rows(gh=[pr(5, "MERGED")])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("Merged", r["reason"])

    def test_merged_with_sha_and_merged_pr_is_merged(self):
        wt = self.add_wt("a")
        write_result(wt, status="merged", merged="5f69d0a")
        r = self.rows(gh=[pr(5, "MERGED")])[self._rel("a")]
        self.assertEqual((r["status"], r["reason"]), ("merged", None))
        self.assertEqual(r["pr_text"], "#5 MERGED")

    def test_merged_but_pr_open_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, status="merged", merged="5f69d0a")
        r = self.rows(gh=[pr(5, "OPEN")])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("PR 不是 MERGED", r["reason"])

    def test_ready_for_authorization_without_open_pr_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, status="ready for authorization")
        for prs in ([], [pr(3, "CLOSED")]):
            r = self.rows(gh=prs)[self._rel("a")]
            self.assertEqual(r["status"], "unknown")
            self.assertIn("無 OPEN 的 PR", r["reason"])

    def test_ready_for_authorization_with_open_pr_passes(self):
        wt = self.add_wt("a")
        write_result(wt, status="ready for authorization", pending="merge PR #9")
        r = self.rows(gh=[pr(9, "OPEN")])[self._rel("a")]
        self.assertEqual((r["status"], r["reason"]), ("ready for authorization", None))
        self.assertEqual(r["pr_text"], "#9 OPEN")
        self.assertEqual(r["pending_authorization"], "merge PR #9")

    def test_pr_merged_but_result_says_working_is_unknown_not_merged(self):
        wt = self.add_wt("a")
        write_result(wt, status="working")
        r = self.rows(gh=[pr(7, "MERGED")])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertNotEqual(r["status"], "merged")
        self.assertIn("PR 已 merge，result.md 未更新", r["reason"])
        self.assertEqual(r["reported_status"], "working")

    def test_gh_failure_with_ready_for_authorization_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, status="ready for authorization")
        r = self.rows(gh=mock.Mock(side_effect=iss.GhError("boom")))[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("PR 狀態查不到", r["reason"])
        self.assertEqual(r["pr_text"], "gh error")

    def test_gh_failure_with_working_keeps_working_but_shows_gh_error(self):
        wt = self.add_wt("a")
        write_result(wt, status="working")
        rc, out, _ = self.run_main(gh=mock.Mock(side_effect=iss.GhError("boom")))
        self.assertEqual(rc, 0)
        self.assertIn("working", out)
        self.assertIn("pr=gh error", out)

    def test_invalid_status_value_is_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, status="done")
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")
        self.assertIn("Status 值不合法", r["reason"])

    def test_self_reported_unknown_stays_unknown(self):
        wt = self.add_wt("a")
        write_result(wt, status="unknown")
        r = self.rows(gh=[])[self._rel("a")]
        self.assertEqual(r["status"], "unknown")

    def test_no_gh_flag_never_queries_and_blocks_ready_and_merged(self):
        a, b, c = self.add_wt("a"), self.add_wt("b"), self.add_wt("c")
        write_result(a, status="ready for authorization")
        write_result(b, status="merged", merged="5f69d0a")
        write_result(c, status="blocked", blocker="等答覆")
        rows = self.rows("--no-gh")  # gh=None：query_prs 被呼叫會 AssertionError
        for n in ("a", "b"):
            self.assertEqual(rows[self._rel(n)]["status"], "unknown")
            self.assertIn("未查 PR", rows[self._rel(n)]["reason"])
        self.assertEqual(rows[self._rel("c")]["status"], "blocked")
        self.assertEqual(rows[self._rel("c")]["pr_text"], "not queried")

    # --- 列舉與輸出 ---
    def test_main_worktree_excluded_and_linked_all_listed(self):
        self.add_wt("a")
        self.add_wt("b")
        rows = self.rows(gh=[])
        self.assertEqual(sorted(rows), sorted([self._rel("a"), self._rel("b")]))
        self.assertNotIn(".", rows)
        self.assertNotIn("", rows)

    def test_worktree_outside_repo_is_named_by_absolute_path(self):
        wt = self.add_wt("a", outside=True)
        rows = self.rows(gh=[])
        self.assertEqual(list(rows), [str(wt)])

    def test_repo_can_be_a_linked_worktree_and_main_is_still_excluded(self):
        wt = self.add_wt("a")
        out = io.StringIO()
        with mock.patch.object(iss, "query_prs", return_value=[]), redirect_stdout(out):
            rc = iss.main(["--repo", str(wt), "--json"])
        self.assertEqual(rc, 0)
        paths = [r["path"] for r in json.loads(out.getvalue())]
        self.assertEqual(paths, [str(wt)])

    def test_gh_is_bound_to_owner_repo_and_branch(self):
        self.add_wt("a", branch="JohnShu/1")
        gh = mock.Mock(return_value=[])
        self.rows(gh=gh)
        gh.assert_called_once_with("acme/widgets", "JohnShu/1")

    def test_query_prs_command_uses_dash_R_and_head(self):
        with mock.patch.object(iss, "run", return_value=(0, "[]", "")) as run:
            iss.query_prs("acme/widgets", "feat/x")
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[:4], ["gh", "-R", "acme/widgets", "pr"])
        self.assertIn("--head", cmd)
        self.assertEqual(cmd[cmd.index("--head") + 1], "feat/x")
        self.assertEqual(cmd[cmd.index("--state") + 1], "all")
        with mock.patch.object(iss, "run", return_value=(1, "", "no auth")):
            with self.assertRaises(iss.GhError):
                iss.query_prs("acme/widgets", "feat/x")
        with self.assertRaises(iss.GhError):
            iss.query_prs(None, "feat/x")

    def test_json_output_parses_and_text_is_one_line_per_worktree(self):
        a, b = self.add_wt("a"), self.add_wt("b")
        write_result(a, blocker="等使用者決定")
        rc, out, _ = self.run_main("--json", gh=[])
        data = json.loads(out)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        for key in ("name", "path", "branch", "status", "reason", "result_mtime", "head", "dirty", "pr_text",
                    "pending_authorization", "blocker"):
            self.assertIn(key, data[0])
        rc, out, _ = self.run_main(gh=[])
        lines = out.splitlines()
        self.assertEqual(len(lines), 2)
        line_a = next(ln for ln in lines if ln.startswith(self._rel("a")))
        self.assertIn("working", line_a)
        self.assertIn("blocker=等使用者決定", line_a)
        line_b = next(ln for ln in lines if ln.startswith(self._rel("b")))
        self.assertIn("unknown", line_b)
        self.assertIn("無 result.md", line_b)

    def test_unknown_line_carries_reason_and_result_mtime(self):
        wt = self.add_wt("a")
        write_result(wt)
        self.commit(wt)
        rc, out, _ = self.run_main(gh=[])
        self.assertIn("Candidate SHA ≠ HEAD", out)
        self.assertRegex(out, r"result\.md mtime \d{4}-\d\d-\d\dT")

    def test_not_a_git_repo_exits_nonzero(self):
        plain = self.root / "plain"
        plain.mkdir()
        err = io.StringIO()
        with redirect_stderr(err):
            rc = iss.main(["--repo", str(plain)])
        self.assertEqual(rc, 2)
        self.assertIn("不是 git repo", err.getvalue())

    def test_read_only_nothing_changes_on_disk(self):
        wt = self.add_wt("a")
        write_result(wt)

        def snapshot():
            return {str(p): p.stat().st_mtime_ns for p in sorted(self.root.rglob("*")) if p.is_file()}

        before = snapshot()
        self.run_main(gh=[pr(1, "OPEN")])
        self.run_main("--json", gh=[])
        self.assertEqual(snapshot(), before)

    def test_orca_info_parses_and_failure_is_empty(self):
        payload = json.dumps({"ok": True, "result": {"worktrees": [
            {"path": "/p/1", "displayName": "392", "linkedIssue": 392, "isMainWorktree": False}]}})
        with mock.patch.object(iss, "run", return_value=(0, payload, "")):
            self.assertEqual(REAL_ORCA_INFO(), {"/p/1": {"displayName": "392", "linkedIssue": 392}})
        for bad in ((127, "", "nf"), (0, "not json", ""), (0, "{}", "")):
            with mock.patch.object(iss, "run", return_value=bad):
                self.assertEqual(REAL_ORCA_INFO(), {})


if __name__ == "__main__":
    unittest.main()
