"""scripts/worktree-clean-check.py 的測試。執行：python3 -m unittest scripts/tests/test_worktree_clean_check.py

用 tempfile 建真的 bare origin、repo 與 worktree；gh 以 patch `query_prs` 取代，閒置檢查的 process 形狀用
`idle_problems` 的純函式輸入，另有一組跑真的 lsof／ps。"""
import importlib.util
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "worktree-clean-check.py"
spec = importlib.util.spec_from_file_location("worktree_clean_check", SCRIPT)
wcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wcc)

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(os.path.realpath(self.tmp.name))
        env = mock.patch.dict(os.environ, GIT_ENV)
        env.start()
        self.addCleanup(env.stop)
        idle = mock.patch.object(wcc, "check_idle", return_value=[])
        idle.start()
        self.addCleanup(idle.stop)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.root / "o.git")], check=True)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "remote", "add", "origin", str(self.root / "o.git"))
        (self.repo / ".git" / "info" / "exclude").write_text(".worktrees/\n*.env\nnode_modules/\n")
        (self.repo / "a.txt").write_text("a\n")
        (self.repo / "old.txt").write_text("old\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "push", "-q", "origin", "main")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.wt = self.root / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "feat/x", str(self.wt), self.base)
        (self.wt / "new.txt").write_text("new\n")
        git(self.wt, "add", ".")
        git(self.wt, "commit", "-qm", "feat")
        self.head = git(self.wt, "rev-parse", "HEAD")

    def rebase_merge(self):
        """把交付內容以新 SHA 放上 origin/main，回 merge commit SHA。"""
        with mock.patch.dict(os.environ, {"GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z"}):  # 同一秒的 cherry-pick 會得到相同 SHA
            git(self.repo, "cherry-pick", self.head)
        git(self.repo, "push", "-q", "origin", "main")
        return git(self.repo, "rev-parse", "HEAD")

    def merge_commit(self):
        git(self.repo, "merge", "-q", "--no-ff", "-m", "m", "feat/x")
        git(self.repo, "push", "-q", "origin", "main")
        return git(self.repo, "rev-parse", "HEAD")

    def write(self, merged, **over):
        f = {"Status": "merged", "Pending": "無", "Blocker": "無", "Base": self.base, "Cand": self.head,
             "Dirty": "0", "Worktree": str(self.wt), "Branch": "feat/x", "extra": ""}
        f.update(over)
        d = self.wt / ".worktrees"
        d.mkdir(exist_ok=True)
        (d / "result.md").write_text(
            f"Issue: 1\nStatus: {f['Status']}\nWorktree: {f['Worktree']}    Branch: {f['Branch']}\n"
            f"Base SHA: {f['Base']}    Candidate SHA: {f['Cand']}    Dirty: {f['Dirty']}\n"
            f"Files changed: new.txt\nVerification: CONVERGED @x\nPR / CI: x\nCross-issue risk: 無\n"
            f"Pending authorization: {f['Pending']}\nBlocker: {f['Blocker']}\nMerged: {merged}\n" + f["extra"],
            encoding="utf-8")

    def check(self, merged, **pr_over):
        files = git(self.wt, "diff", "--name-only", self.base, self.head).splitlines()
        files = [f.strip('"') for f in files]
        pr = {"number": 1, "state": "MERGED", "headRefOid": self.head, "baseRefName": "main",
              "mergeCommit": {"oid": merged}, "url": "u", "files": [{"path": f} for f in files], "changedFiles": len(files)}
        pr.update(pr_over)
        with mock.patch.object(wcc, "query_prs", return_value=[pr]):
            return wcc.evaluate(str(self.repo), str(self.wt))[0]


class Delivery(Base):
    def test_rebase_merge_passes(self):
        m = self.rebase_merge()
        self.write(m)
        self.assertEqual(self.check(m), [])

    def test_merge_commit_passes(self):
        m = self.merge_commit()
        self.write(m)
        self.assertEqual(self.check(m), [])

    def test_merge_commit_then_revert_is_blocked(self):
        m = self.merge_commit()
        git(self.repo, "rm", "-q", "new.txt")
        git(self.repo, "commit", "-qm", "revert")
        git(self.repo, "push", "-q", "origin", "main")
        self.write(m)
        self.assertTrue(any("交付內容" in p for p in self.check(m)))

    def test_fast_forward_then_base_deletes_file_is_blocked(self):
        git(self.repo, "merge", "-q", "--ff-only", "feat/x")
        git(self.repo, "rm", "-q", "new.txt")
        git(self.repo, "commit", "-qm", "del")
        git(self.repo, "push", "-q", "origin", "main")
        self.write(self.head)
        self.assertTrue(any("交付內容" in p for p in self.check(self.head)))

    def test_base_advanced_over_same_file_is_blocked(self):
        m = self.rebase_merge()
        (self.repo / "new.txt").write_text("changed\n")
        git(self.repo, "commit", "-qam", "later")
        git(self.repo, "push", "-q", "origin", "main")
        self.write(m)
        self.assertTrue(any("交付內容" in p for p in self.check(m)))

    def test_base_advanced_elsewhere_passes(self):
        m = self.rebase_merge()
        (self.repo / "other.txt").write_text("o\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "later")
        git(self.repo, "push", "-q", "origin", "main")
        self.write(m)
        self.assertEqual(self.check(m), [])

    def test_rename_with_old_path_still_on_base_is_blocked(self):
        git(self.wt, "mv", "old.txt", "renamed.txt")
        git(self.wt, "commit", "-qm", "mv")
        self.head = git(self.wt, "rev-parse", "HEAD")
        git(self.repo, "cherry-pick", git(self.wt, "rev-parse", "HEAD~1"))
        (self.repo / "renamed.txt").write_text("old\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "partial")
        git(self.repo, "push", "-q", "origin", "main")
        m = git(self.repo, "rev-parse", "HEAD")
        self.write(m)
        self.assertTrue(any("old.txt" in p for p in self.check(m)))

    def test_pathspec_magic_filename_is_literal(self):
        (self.wt / ":weird").write_text("w\n")
        git(self.wt, "add", "--", ":(literal):weird")
        git(self.wt, "commit", "-qm", "w")
        self.head = git(self.wt, "rev-parse", "HEAD")
        self.write(self.base)  # 內容根本沒進 base
        m = self.base
        self.assertTrue(any("交付內容" in p for p in self.check(m)))

    def test_empty_pr_files_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        self.assertTrue(any("檔案清單" in p for p in self.check(m, files=[], changedFiles=0)))

    def test_truncated_pr_files_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        self.assertTrue(any("檔案清單" in p for p in self.check(m, changedFiles=101)))

    def test_self_reported_base_cannot_shrink_delivery(self):
        (self.wt / "second.txt").write_text("2\n")
        git(self.wt, "add", ".")
        git(self.wt, "commit", "-qm", "second")
        self.head = git(self.wt, "rev-parse", "HEAD")
        git(self.repo, "merge", "-q", "--ff-only", "feat/x")
        git(self.repo, "rm", "-q", "new.txt")  # 第一個 commit 的檔被 base 刪掉
        git(self.repo, "commit", "-qm", "del")
        git(self.repo, "push", "-q", "origin", "main")
        self.write(self.head, Base=git(self.wt, "rev-parse", "HEAD~1"))
        self.assertTrue(any("new.txt" in p for p in self.check(self.head)))

    def test_base_on_branch_only_is_blocked(self):
        (self.wt / "second.txt").write_text("2\n")
        git(self.wt, "add", ".")
        git(self.wt, "commit", "-qm", "second")
        branch_only = git(self.wt, "rev-parse", "HEAD~1")
        self.head = git(self.wt, "rev-parse", "HEAD")
        m = self.rebase_merge()
        self.write(m, Base=branch_only)
        self.assertTrue(any("不在 origin/main 上" in p for p in self.check(m)))

    def test_local_branch_named_origin_main_does_not_shadow(self):
        m = self.rebase_merge()
        git(self.repo, "rm", "-q", "new.txt")
        git(self.repo, "commit", "-qm", "revert")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "branch", "origin/main", m)
        self.write(m)
        self.assertTrue(any("new.txt" in p for p in self.check(m)))

    def test_narrow_refspec_still_sees_remote_revert(self):
        m = self.rebase_merge()
        git(self.repo, "config", "remote.origin.fetch", "+refs/heads/other:refs/remotes/origin/other")
        clone = self.root / "c"
        subprocess.run(["git", "clone", "-q", str(self.root / "o.git"), str(clone)], check=True)
        git(clone, "rm", "-q", "new.txt")
        git(clone, "commit", "-qm", "revert")
        git(clone, "push", "-q", "origin", "main")
        self.write(m)
        self.assertTrue(any("new.txt" in p for p in self.check(m)))

    def test_base_not_ancestor_is_blocked(self):
        m = self.rebase_merge()
        self.write(m, Base=m)
        self.assertTrue(any("不是 HEAD 的祖先" in p for p in self.check(m)))

    def test_base_field_revision_expression_is_blocked(self):
        m = self.rebase_merge()
        self.write(m, Base="HEAD~1")
        self.assertTrue(any("Base SHA" in p for p in self.check(m)))

    def test_base_field_not_sha_is_blocked(self):
        m = self.rebase_merge()
        self.write(m, Base="x")
        self.assertTrue(any("Base SHA" in p for p in self.check(m)))

    def test_pr_head_differs_from_worktree_head_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        self.assertTrue(self.check(m, headRefOid="f" * 40))

    def test_open_pr_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        self.assertTrue(self.check(m, state="OPEN"))

    def test_merged_pr_plus_open_pr_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        merged = {"number": 1, "state": "MERGED", "headRefOid": self.head, "baseRefName": "main",
                  "mergeCommit": {"oid": m}, "url": "u", "files": [{"path": "new.txt"}], "changedFiles": 1}
        with mock.patch.object(wcc, "query_prs", return_value=[{"number": 2, "state": "OPEN"}, merged]):
            self.assertTrue(any("OPEN" in p for p in wcc.evaluate(str(self.repo), str(self.wt))[0]))

    def test_pathspec_magic_filename_delivered_passes(self):
        (self.wt / ":weird").write_text("w\n")
        git(self.wt, "add", "--", ":(literal):weird")
        git(self.wt, "commit", "--amend", "-qm", "feat")
        self.head = git(self.wt, "rev-parse", "HEAD")
        m = self.rebase_merge()
        self.write(m)
        self.assertEqual(self.check(m), [])

    def test_glob_filename_does_not_match_other_files(self):
        (self.wt / "*.txt").write_text("g\n")
        git(self.wt, "add", "--", ":(literal)*.txt")
        git(self.wt, "commit", "--amend", "-qm", "feat")
        self.head = git(self.wt, "rev-parse", "HEAD")
        m = self.rebase_merge()
        (self.repo / "a.txt").write_text("later\n")  # 不在交付清單內；glob 展開才會比到
        git(self.repo, "commit", "-qam", "later")
        git(self.repo, "push", "-q", "origin", "main")
        self.write(m)
        self.assertEqual(self.check(m), [])

    def test_wrong_merged_sha_is_blocked(self):
        m = self.rebase_merge()
        self.write("deadbeef")
        self.assertTrue(any("Merged" in p for p in self.check(m)))

    def test_merge_commit_not_on_base_is_blocked(self):
        self.rebase_merge()
        self.write(self.head)
        self.assertTrue(any("不在 origin/main" in p for p in self.check(self.head)))

    def test_gh_failure_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        with mock.patch.object(wcc, "query_prs", return_value=None):
            self.assertTrue(any("PR 查不到" in p for p in wcc.evaluate(str(self.repo), str(self.wt))[0]))

    def test_fetch_failure_is_blocked(self):
        m = self.rebase_merge()
        self.write(m)
        git(self.repo, "remote", "set-url", "origin", str(self.root / "gone.git"))
        self.assertTrue(any("fetch" in p for p in self.check(m)))


class ResultFields(Base):
    def setUp(self):
        super().setUp()
        self.m = self.rebase_merge()

    def blocked(self, **over):
        self.write(self.m, **over)
        return self.check(self.m)

    def test_status_not_merged(self):
        self.assertTrue(self.blocked(Status="ready for authorization"))

    def test_pending_not_none(self):
        self.assertTrue(self.blocked(Pending="merge"))

    def test_blocker_not_none(self):
        self.assertTrue(self.blocked(Blocker="x"))

    def test_candidate_stale(self):
        self.assertTrue(self.blocked(Cand="1234567"))

    def test_dirty_field_nonzero(self):
        self.assertTrue(self.blocked(Dirty="1"))

    def test_worktree_field_is_prefix_path(self):
        self.assertTrue(self.blocked(Worktree=str(self.wt) + "-x"))

    def test_branch_field_differs(self):
        self.assertTrue(self.blocked(Branch="other"))

    def test_pending_continuation_line(self):
        self.write(self.m, Pending="無\nmerge PR #2")
        self.assertTrue(any("不是下一個欄位" in p for p in self.check(self.m)))

    def test_status_repeated(self):
        self.assertTrue(any("Status" in p for p in self.blocked(extra="Status: working\n")))

    def test_bullet_blocker_in_notes(self):
        self.assertTrue(any("Blocker" in p for p in self.blocked(extra="## 備註\n- Blocker: 等人\n")))

    def test_second_worktree_line(self):
        self.write(self.m, extra=f"Worktree: {self.root}/other\n")
        self.assertTrue(any("Worktree" in p for p in self.check(self.m)))

    def test_notes_without_field_names_pass(self):
        self.assertEqual(self.blocked(extra="\n## 備註\n一般說明。\n"), [])

    def edit(self, old, new):
        self.write(self.m)
        rp = self.wt / ".worktrees" / "result.md"
        text = rp.read_text(encoding="utf-8")
        self.assertIn(old, text)
        rp.write_text(text.replace(old, new), encoding="utf-8")
        return self.check(self.m)

    def test_issue_unknown_with_reason(self):
        for value in ("unknown 沒有票", "unknown（找不到票）", "UNKNOWN: 沒票"):
            self.assertTrue(any("Issue" in p for p in self.edit("Issue: 1", f"Issue: {value}")), value)

    def test_pending_hidden_inline_after_other_field(self):
        problems = self.edit("Cross-issue risk: 無\nPending authorization: 無",
                             "Cross-issue risk: 無    Pending authorization: 無\n  等使用者授權 merge")
        self.assertTrue(any("Pending" in p for p in problems))

    def test_status_hidden_inline_after_issue(self):
        problems = self.edit("Issue: 1\nStatus: merged", "Issue: 1    Status: merged\n  其實還在等")
        self.assertTrue(any("Status" in p for p in problems))

    def test_duplicate_pending_on_one_line(self):
        problems = self.edit("Pending authorization: 無", "Pending authorization: 無    Pending authorization: merge PR")
        self.assertTrue(any("Pending" in p for p in problems))

    def test_duplicate_status_on_one_line(self):
        problems = self.edit("Status: merged", "Status: merged    Status: working")
        self.assertTrue(any("Status" in p for p in problems))

    def test_template_inline_fields_parse(self):
        self.assertEqual(self.edit("Issue: 1", "Issue: 1"), [])

    def test_inline_fields_may_be_on_their_own_lines(self):
        self.write(self.m)
        rp = self.wt / ".worktrees" / "result.md"
        text = rp.read_text(encoding="utf-8").replace("    Branch:", "\nBranch:").replace("    Candidate SHA:", "\nCandidate SHA:").replace("    Dirty:", "\nDirty:")
        rp.write_text(text, encoding="utf-8")
        self.assertEqual(self.check(self.m), [])

    def test_merged_continuation_line(self):
        self.write(self.m, extra="其實還沒 merge\n")
        self.assertTrue(any("Merged" in p for p in self.check(self.m)))

    def test_issue_unknown(self):
        self.write(self.m)
        rp = self.wt / ".worktrees" / "result.md"
        rp.write_text(rp.read_text(encoding="utf-8").replace("Issue: 1", "Issue: unknown"), encoding="utf-8")
        self.assertTrue(any("Issue" in p for p in self.check(self.m)))

    def test_missing_issue_line(self):
        self.write(self.m)
        rp = self.wt / ".worktrees" / "result.md"
        rp.write_text(rp.read_text(encoding="utf-8").replace("Issue: 1\n", ""), encoding="utf-8")
        self.assertTrue(any("Issue" in p for p in self.check(self.m)))

    def variant(self, line):
        self.write(self.m)
        rp = self.wt / ".worktrees" / "result.md"
        rp.write_text(line + rp.read_text(encoding="utf-8"), encoding="utf-8")
        return self.check(self.m)

    def test_lowercase_status_line(self):
        self.assertTrue(any("Status" in p for p in self.variant("status: working\n")))

    def test_uppercase_status_line(self):
        self.assertTrue(any("Status" in p for p in self.variant("STATUS: working\n")))

    def test_bom_before_status_line(self):
        self.assertTrue(any("Status" in p for p in self.variant("\ufeffStatus: working\n")))

    def test_zero_width_in_key(self):
        self.assertTrue(any("Status" in p for p in self.variant("Status\u200b: working\n")))

    def test_blank_then_note_after_pending(self):
        self.write(self.m, Pending="無\n\n還要等 merge 授權")
        self.assertTrue(self.check(self.m))

    def test_indented_field_does_not_count(self):
        self.write(self.m)
        rp = self.wt / ".worktrees" / "result.md"
        rp.write_text(rp.read_text(encoding="utf-8").replace("Status: merged", "  Status: merged"), encoding="utf-8")
        self.assertTrue(self.check(self.m))

    def test_no_result_md(self):
        self.assertTrue(any("來源不明" in p for p in self.check(self.m)))


class Tree(Base):
    def setUp(self):
        super().setUp()
        self.m = self.rebase_merge()
        self.write(self.m)

    def test_tracked_change(self):
        (self.wt / "a.txt").write_text("z\n")
        self.assertTrue(any("不乾淨" in p for p in self.check(self.m)))

    def test_untracked_even_when_config_hides_it(self):
        git(self.wt, "config", "status.showUntrackedFiles", "no")
        (self.wt / "u.txt").write_text("u\n")
        self.assertTrue(any("不乾淨" in p for p in self.check(self.m)))

    def test_skip_worktree(self):
        git(self.wt, "update-index", "--skip-worktree", "a.txt")
        (self.wt / "a.txt").write_text("z\n")
        self.assertTrue(any("skip-worktree" in p for p in self.check(self.m)))

    def test_assume_unchanged(self):
        git(self.wt, "update-index", "--assume-unchanged", "a.txt")
        (self.wt / "a.txt").write_text("z\n")
        self.assertTrue(any("assume-unchanged" in p for p in self.check(self.m)))

    def test_ignored_env_is_blocked(self):
        (self.wt / "x.env").write_text("s\n")
        self.assertTrue(any("ignored" in p for p in self.check(self.m)))

    def ignored(self, *rel):
        for r in rel:
            p = self.wt / r
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x\n")
        return self.check(self.m)

    def test_ignored_secret_under_rebuildable_named_path_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("*.key\nbin/\nsecrets/obj\n")
        self.assertTrue(any("ignored" in p for p in self.ignored("src/bin/deploy.key")))

    def test_generic_named_ignored_dir_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("build/\n")
        self.assertTrue(any("ignored" in p for p in self.ignored("build/notes.md")))

    def test_ignored_file_named_like_rebuildable_dir_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("secrets/.gradle\n")
        self.assertTrue(any("ignored" in p for p in self.ignored("secrets/.gradle")))

    def test_generic_ignored_dir_inside_rebuildable_name_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("foo/\n")
        self.assertTrue(any("ignored" in p for p in self.ignored(".gradle/foo/s")))

    def test_ds_store_passes(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text(".DS_Store\n")
        self.assertEqual(self.ignored(".DS_Store"), [])

    def test_ignored_build_output_passes(self):
        (self.wt / "node_modules").mkdir()
        (self.wt / "node_modules" / "p.js").write_text("p\n")
        self.assertEqual(self.check(self.m), [])

    def self_ignoring(self, root, gitignore="*\n", *rel):
        """工具在自己的目錄放 `*` 的 .gitignore：status 會逐檔列出，不會回報成目錄（pytest、venv 都是這個形狀）。"""
        (self.wt / root).mkdir(parents=True, exist_ok=True)
        (self.wt / root / ".gitignore").write_text(gitignore)
        return self.ignored(*(rel or (f"{root}/README.md", f"{root}/v/cache/lastfailed")))

    def test_self_ignoring_cache_passes(self):
        self.assertEqual(self.self_ignoring(".pytest_cache", "# Created by pytest automatically.\n*\n"), [])

    def test_self_ignoring_venv_passes(self):
        self.assertEqual(self.self_ignoring(".venv", "# Created by venv\n*\n", ".venv/pyvenv.cfg"), [])

    def test_self_ignoring_dir_below_root_is_blocked(self):
        for root in ("pkg/.venv", "a\rb/.venv", "Äx/.pytest_cache"):
            with self.subTest(root=root):
                self.assertTrue(any("ignored" in p for p in self.self_ignoring(root, "*\n", f"{root}/a")))

    def test_root_venv_does_not_vouch_for_subdir_venv(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("*.key\n")
        self.self_ignoring(".venv", "*\n", ".venv/a")
        self.assertTrue(any("pkg/.venv/a.key" in p for p in self.ignored("pkg/.venv/a.key")))

    def test_similarly_named_tracked_dir_does_not_block(self):
        (self.wt / ".venv2").mkdir()
        (self.wt / ".venv2" / "t").write_text("t\n")
        git(self.wt, "add", ".venv2/t")
        git(self.wt, "commit", "-qm", "tracked")
        self.assertFalse(any("ignored" in p for p in self.self_ignoring(".venv", "*\n", ".venv/a")))

    def test_self_ignoring_generic_dir_is_blocked(self):
        self.assertTrue(any("ignored" in p for p in self.self_ignoring("build", "*\n", "build/deploy.key")))

    def test_rebuildable_name_without_star_gitignore_is_blocked(self):
        for content in ("*.key\n.gitignore\n", "# *\n*.key\n.gitignore\n", "/*\n", " *\n.gitignore\n*.key\n"):
            with self.subTest(content=content):
                self.assertTrue(any("ignored" in p for p in self.self_ignoring(".venv", content, ".venv/a.key")))

    def test_rebuildable_name_ignored_by_outside_rule_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("*.key\n.gitignore\n")
        self.assertTrue(any("ignored" in p for p in self.ignored(".venv/.gitignore", ".venv/a.key")))

    def test_negated_file_in_self_ignoring_dir_is_blocked(self):
        problems = self.self_ignoring(".venv", "*\n!keep.txt\n", ".venv/keep.txt", ".venv/a")
        self.assertTrue(any("不乾淨" in p for p in problems))

    def test_tracked_gitignore_in_self_ignoring_dir_is_blocked(self):
        (self.wt / ".venv").mkdir()
        (self.wt / ".venv" / ".gitignore").write_text("*\n")
        git(self.wt, "add", "-f", ".venv/.gitignore")
        git(self.wt, "commit", "-qm", "tracked")
        self.assertTrue(any("ignored" in p for p in self.ignored(".venv/a.key")))

    def test_tracked_file_in_self_ignoring_dir_is_blocked(self):
        (self.wt / ".venv").mkdir()
        (self.wt / ".venv" / "t.txt").write_text("t\n")
        git(self.wt, "add", ".venv/t.txt")
        git(self.wt, "commit", "-qm", "tracked")
        self.assertTrue(any("ignored" in p for p in self.self_ignoring(".venv", "*\n", ".venv/a.key")))

    def test_gitignore_directory_in_rebuildable_name_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("*.key\n.gitignore\n")
        self.assertTrue(any("ignored" in p for p in self.ignored(".venv/.gitignore/x", ".venv/a.key")))

    def test_symlinked_self_ignoring_dir_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text(".venv\n")
        (self.root / "secrets").mkdir()
        (self.root / "secrets" / ".gitignore").write_text("*\n")
        os.symlink(self.root / "secrets", self.wt / ".venv")
        self.assertTrue(any("ignored" in p for p in self.check(self.m)))

    def test_symlinked_gitignore_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text(".gitignore\n*.key\n")
        (self.root / "star").write_text("*\n")
        (self.wt / ".venv").mkdir()
        os.symlink(self.root / "star", self.wt / ".venv" / ".gitignore")
        self.assertTrue(any("ignored" in p for p in self.ignored(".venv/a.key")))

    def test_unreadable_gitignore_is_blocked(self):
        (self.wt / ".venv").mkdir()
        (self.wt / ".venv" / ".gitignore").write_text("*\n")
        (self.wt / ".venv" / "a").write_text("a\n")
        with mock.patch.object(Path, "read_bytes", side_effect=OSError):
            self.assertTrue(any("ignored" in p for p in self.check(self.m)))

    def test_ls_files_failure_is_blocked(self):
        real = wcc.git
        fail = lambda path, *a: (1, "") if "ls-files" in a else real(path, *a)
        with mock.patch.object(wcc, "git", side_effect=fail):
            self.assertTrue(any("ls-files" in p for p in self.check(self.m)))

    def test_special_gitignore_is_not_read(self):
        """symlink 指到 FIFO 或超大檔：不能掛住，也不能放行。"""
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text(".gitignore\n*.key\n")
        os.mkfifo(self.root / "pipe")
        (self.wt / ".venv").mkdir()
        os.symlink(self.root / "pipe", self.wt / ".venv" / ".gitignore")
        signal.signal(signal.SIGALRM, signal.default_int_handler)
        signal.alarm(20)
        self.addCleanup(signal.alarm, 0)
        self.assertTrue(any("ignored" in p for p in self.ignored(".venv/a.key")))

    def test_oversized_gitignore_is_blocked(self):
        self.assertTrue(self.star_rule_blocked(b"#" * wcc.MARKER_MAX_BYTES + b"\n*\n"))

    def test_tracked_file_with_literal_pathspecs_env_is_blocked(self):
        (self.wt / ".venv").mkdir()
        (self.wt / ".venv" / "t").write_text("t\n")
        git(self.wt, "add", "-f", ".venv/t")
        git(self.wt, "commit", "-qm", "tracked")
        with mock.patch.dict(os.environ, {"GIT_LITERAL_PATHSPECS": "1"}):
            self.assertTrue(any("ignored" in p for p in self.self_ignoring(".venv", "*\n", ".venv/a.key")))

    def star_rule_blocked(self, content):
        (self.wt / ".venv").mkdir(exist_ok=True)
        (self.wt / ".venv" / ".gitignore").write_bytes(content)
        return bool(self.ignored(".venv/a.key"))

    def test_line_separators_git_does_not_honor_are_blocked(self):
        """Python 的 splitlines 會切、git 不會切的字元：git 沒有 `*` 規則，a.key 是被 *.key 忽略的。"""
        for sep in (b"\f", b"\x0b", b"\x1c", b"\x1d", b"\x1e", b"\xc2\x85", b"\xe2\x80\xa8", b"\xe2\x80\xa9", b"\r"):
            with self.subTest(sep=sep):
                self.assertTrue(self.star_rule_blocked(b"*.key\n.gitignore\n#" + sep + b"*\n"))

    def test_lone_cr_file_is_blocked(self):
        self.assertTrue(self.star_rule_blocked(b"*.key\r.gitignore\r*\r"))

    def test_cr_inside_comment_hiding_star_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text("*.key\n.gitignore\n")
        self.assertTrue(self.star_rule_blocked(b"# note\r*\n"))

    def test_extra_rules_besides_star_are_blocked(self):
        for content in (b"*\n!sub/\nsub/*\n", b"*.key\n*\n", b"*\n*\n", b"\xff\n*\n"):
            with self.subTest(content=content):
                self.assertTrue(self.star_rule_blocked(content))

    def test_crlf_star_passes(self):
        self.assertFalse(self.star_rule_blocked(b"# Created by venv\r\n*\r\n"))

    def test_self_ignoring_other_rebuildable_name_is_blocked(self):
        for root in (".gradle", "__pycache__", "Pods"):
            with self.subTest(root=root):
                self.assertTrue(any("ignored" in p for p in self.self_ignoring(root, "*\n", f"{root}/a")))

    def test_tracked_file_with_different_case_is_blocked(self):
        (self.wt / ".VENV").mkdir()
        (self.wt / ".VENV" / "t").write_text("t\n")
        git(self.wt, "add", "-f", ".VENV/t")
        git(self.wt, "commit", "-qm", "tracked")
        if not (self.wt / ".venv").exists():
            self.skipTest("需要大小寫不敏感的檔案系統")
        os.rename(self.wt / ".VENV", self.wt / "tmpx")
        os.rename(self.wt / "tmpx", self.wt / ".venv")
        self.assertTrue(any("ignored" in p for p in self.self_ignoring(".venv", "*\n", ".venv/a.key")))

    def fresh_husky(self, root, marker="*", *names):
        """跑一個形狀後清掉，同一個 test 的下一個形狀不受前一個的檔案影響。"""
        try:
            return self.self_ignoring(root, marker, *(f"{root}/{n}" for n in (names or ("h", "pre-commit"))))
        finally:
            shutil.rmtree(self.wt / root.split("/")[0])

    def test_root_husky_passes(self):
        for marker in ("*", "*\n"):
            with self.subTest(marker=marker):
                self.assertEqual(self.fresh_husky(".husky/_", marker), [])

    def test_husky_below_root_is_blocked(self):
        for root in ("pkg/.husky/_", "a/b/.husky/_"):
            with self.subTest(root=root):
                self.assertTrue(any("ignored" in p for p in self.fresh_husky(root)))

    def test_husky_lookalike_paths_are_blocked(self):
        for root in (".husky/x", ".husky/_x", ".husky", "_", ".husky/_/sub"):
            with self.subTest(root=root):
                self.assertTrue(any("ignored" in p for p in self.fresh_husky(root)))

    def test_husky_marker_must_be_only_star(self):
        for marker in ("*\n!keep\n", "h\n"):
            with self.subTest(marker=marker):
                self.assertTrue(any("ignored" in p for p in self.fresh_husky(".husky/_", marker, "keep", "h")))

    def test_tracked_file_in_husky_is_blocked(self):
        (self.wt / ".husky" / "_").mkdir(parents=True)
        (self.wt / ".husky" / "_" / "t").write_text("t\n")
        git(self.wt, "add", ".husky/_/t")
        git(self.wt, "commit", "-qm", "t")
        self.assertTrue(any("ignored" in p for p in self.self_ignoring(".husky/_", "*", ".husky/_/h")))

    def test_symlinked_husky_marker_is_blocked(self):
        git(self.wt, "config", "core.excludesFile", str(self.root / "ex"))
        (self.root / "ex").write_text(".husky/_/h\n.husky/_/.gitignore\n")
        (self.root / "star").write_text("*")
        (self.wt / ".husky" / "_").mkdir(parents=True)
        os.symlink(self.root / "star", self.wt / ".husky" / "_" / ".gitignore")
        self.assertTrue(any("ignored" in p for p in self.ignored(".husky/_/h")))

    def test_nested_generic_dir_in_self_ignoring_root_passes(self):
        self.assertEqual(self.self_ignoring(".venv", "*\n", ".venv/lib/python/site.py", ".venv/build/x"), [])

    def test_other_file_in_dot_worktrees_is_blocked(self):
        (self.wt / ".worktrees" / "notes.md").write_text("n\n")
        self.assertTrue(any("notes.md" in p for p in self.check(self.m)))

    def test_nested_worktree_is_blocked(self):
        git(self.repo, "worktree", "add", "-q", "-b", "feat/n", str(self.wt / ".worktrees" / "n"), self.base)
        self.assertTrue(any("巢狀" in p for p in self.check(self.m)))


    def test_nested_worktree_in_rebuildable_dir_is_blocked(self):
        (self.wt / "node_modules").mkdir()
        git(self.repo, "worktree", "add", "-q", "-b", "feat/n", str(self.wt / "node_modules" / "n"), self.base)
        self.assertTrue(any("巢狀" in p for p in self.check(self.m)))


class Selection(Base):
    def test_locked_worktree(self):
        git(self.repo, "worktree", "lock", str(self.wt))
        self.addCleanup(git, self.repo, "worktree", "unlock", str(self.wt))
        self.assertTrue(any("lock" in p for p in wcc.evaluate(str(self.repo), str(self.wt))[0]))

    def test_main_worktree(self):
        self.assertIn("這是 main worktree", wcc.evaluate(str(self.repo), str(self.repo))[0])

    def test_unknown_path(self):
        self.assertTrue(any("不是該 repo" in p for p in wcc.evaluate(str(self.repo), str(self.root / "nope"))[0]))

    def test_detached_head(self):
        git(self.wt, "checkout", "-q", "--detach")
        self.assertTrue(any("detached" in p for p in wcc.evaluate(str(self.repo), str(self.wt))[0]))


class IdleShapes(unittest.TestCase):
    WT = "/w/t"
    SELF = 100

    def lsof(self, *rows):
        out = f"p{self.SELF}\ncpython\nn/elsewhere\n"
        for pid, comm, cwd in rows:
            out += f"p{pid}\nc{comm}\nn{cwd}\n"
        return out

    def ps(self, *rows):
        out = f"{self.SELF} 1 python x\n"
        for pid, ppid, args in rows:
            out += f"{pid} {ppid} {args}\n"
        return out

    def run_it(self, rows, lsof_rows, ps_rows):
        with mock.patch.object(wcc.os.path, "realpath", side_effect=lambda p: p):
            return wcc.idle_problems(self.WT, rows, self.lsof(*lsof_rows), self.ps(*ps_rows), self.SELF)

    def test_nothing_running(self):
        self.assertEqual(self.run_it([], [], []), [])

    def test_plain_shell_passes(self):
        self.assertEqual(self.run_it([], [(5, "zsh", self.WT)], [(5, 1, "-zsh")]), [])

    def test_idle_claude_passes_by_pid_not_name(self):
        rows = [{"pid": 6, "state": "idle", "cwd": self.WT}]
        self.assertEqual(self.run_it(rows, [(6, "2.1.319", self.WT)], [(6, 1, "claude")]), [])

    def test_login_shell_parent_of_idle_claude_passes(self):
        rows = [{"pid": 6, "state": "idle", "cwd": self.WT}]
        lsof = [(5, "zsh", self.WT), (6, "2.1.319", self.WT)]
        self.assertEqual(self.run_it(rows, lsof, [(5, 1, "-/bin/zsh -l"), (6, 5, "claude --x")]), [])

    def test_login_shell_parent_of_working_claude_blocked(self):
        rows = [{"pid": 6, "state": "working", "cwd": self.WT}]
        lsof = [(5, "zsh", self.WT), (6, "2.1.319", self.WT)]
        problems = self.run_it(rows, lsof, [(5, 1, "-/bin/zsh -l"), (6, 5, "claude --x")])
        self.assertTrue(any("5 zsh" in p for p in problems))

    def test_working_claude_blocked(self):
        for state in ("working", "turn", "sub", "quiet", "no-log"):
            rows = [{"pid": 6, "state": state, "cwd": self.WT}]
            self.assertTrue(self.run_it(rows, [(6, "2.1.319", self.WT)], [(6, 1, "claude")]), state)

    def test_foreground_command_blocked(self):
        self.assertTrue(self.run_it([], [(7, "sleep", self.WT + "/sub")], [(7, 1, "sleep 600")]))

    def test_codex_blocked(self):
        self.assertTrue(self.run_it([], [(8, "codex", self.WT)], [(8, 1, "codex")]))

    def test_shell_waiting_on_child_elsewhere_blocked(self):
        self.assertTrue(self.run_it([], [(9, "bash", self.WT)], [(9, 1, "bash"), (10, 9, "sleep 9")]))

    def test_shell_running_script_blocked(self):
        self.assertTrue(self.run_it([], [(9, "bash", self.WT)], [(9, 1, "bash s.sh")]))

    def test_shell_dash_c_blocked(self):
        self.assertTrue(self.run_it([], [(9, "zsh", self.WT)], [(9, 1, "zsh -c loop")]))

    def test_prefix_path_ignored(self):
        self.assertEqual(self.run_it([], [(7, "sleep", self.WT + "-x")], [(7, 1, "sleep 1")]), [])

    def test_lsof_without_self_blocked(self):
        with mock.patch.object(wcc.os.path, "realpath", side_effect=lambda p: p):
            self.assertTrue(wcc.idle_problems(self.WT, [], "p5\nczsh\nn/x\n", self.ps(), self.SELF))

    def test_ps_without_self_blocked(self):
        with mock.patch.object(wcc.os.path, "realpath", side_effect=lambda p: p):
            self.assertTrue(wcc.idle_problems(self.WT, [], self.lsof(), "5 1 zsh\n", self.SELF))


class IdleTools(unittest.TestCase):
    def fake_run(self, overrides):
        real = wcc.run
        def _run(cmd, cwd=None):
            key = cmd[0] if cmd[0] != wcc.sys.executable else "stall"
            if key in overrides:
                return overrides[key]
            return real(cmd, cwd)
        return mock.patch.object(wcc, "run", side_effect=_run)

    def test_lsof_missing_blocked(self):
        with self.fake_run({"lsof": (127, ""), "stall": (0, "[]")}):
            self.assertTrue(any("lsof" in p for p in wcc.check_idle("/nope")))

    def test_lsof_rc1_empty_blocked(self):
        with self.fake_run({"lsof": (1, ""), "stall": (0, "[]")}):
            self.assertTrue(any("lsof" in p for p in wcc.check_idle("/nope")))

    def test_ps_failure_blocked(self):
        with self.fake_run({"ps": (1, ""), "stall": (0, "[]")}):
            self.assertTrue(any("ps" in p for p in wcc.check_idle("/nope")))

    def test_stall_check_failure_blocked(self):
        with self.fake_run({"stall": (1, "")}):
            self.assertTrue(any("stall-check" in p for p in wcc.check_idle("/nope")))

    def test_stall_check_garbage_blocked(self):
        with self.fake_run({"stall": (0, "not json")}):
            self.assertTrue(any("讀不懂" in p for p in wcc.check_idle("/nope")))

    @unittest.skipUnless(os.path.exists("/usr/sbin/lsof"), "需要 lsof")
    def test_real_tools_see_a_real_process(self):
        with tempfile.TemporaryDirectory() as d:
            d = os.path.realpath(d)
            self.assertEqual(wcc.check_idle(d), [])
            p = subprocess.Popen(["sleep", "30"], cwd=d)
            try:
                time.sleep(0.3)
                self.assertTrue(any(str(p.pid) in x for x in wcc.check_idle(d)))
            finally:
                p.kill()
                p.wait()


if __name__ == "__main__":
    unittest.main()
