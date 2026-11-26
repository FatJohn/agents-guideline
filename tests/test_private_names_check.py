"""End-to-end tests for .githooks/{pre-commit,commit-msg} and scripts/private-names-check.py.

Each test builds a throwaway repo with the hooks installed through core.hooksPath
and runs real `git commit`. Names in the list are made up.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAMES = ["acme-secret", "Zebra Widget", "第七號專案"]


class PrivateNamesHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        (self.repo / "scripts").mkdir(parents=True)
        shutil.copytree(REPO_ROOT / ".githooks", self.repo / ".githooks")
        shutil.copy2(REPO_ROOT / "scripts" / "private-names-check.py", self.repo / "scripts")
        self.names = self.tmp / "names.txt"
        self.names.write_text("# comment line, ignored\n\n" + "\n".join(NAMES) + "\n", encoding="utf-8")
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "core.hooksPath", ".githooks")
        self.git("config", "privateNames.file", str(self.names))
        self.git("add", ".")
        self.assertEqual(self.commit("chore: init").returncode, 0)

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def commit(self, message: str) -> subprocess.CompletedProcess[str]:
        return self.git("commit", "-q", "-m", message)

    def stage(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.git("add", "--", rel)

    def assert_blocked(self, result: subprocess.CompletedProcess[str], *expected: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("commit blocked", result.stderr)
        for text in expected:
            self.assertIn(text, result.stderr)
        for name in NAMES:
            self.assertNotIn(name.casefold(), result.stderr.casefold())

    def head_count(self) -> int:
        return int(self.git("rev-list", "--count", "HEAD").stdout)

    def test_staged_content_is_blocked_case_insensitively(self) -> None:
        self.stage("docs/a.md", "line one\nmentions ACME-Secret here\n")
        self.assert_blocked(self.commit("docs: add a"), "docs/a.md:2", "list entry line 3")
        self.assertEqual(self.head_count(), 1)

    def test_non_ascii_entry_and_entry_with_space(self) -> None:
        self.stage("a.md", "zebra widget\n")
        self.stage("b.md", "x\ny\n第七號專案的紀錄\n")
        self.assert_blocked(self.commit("docs: add"), "a.md:1 (list entry line 4)", "b.md:3 (list entry line 5)")

    def test_staged_path_is_blocked(self) -> None:
        self.stage("notes/acme-secret-plan.md", "clean\n")
        result = self.commit("docs: add plan")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("file path (list entry line 3)", result.stderr)

    def test_commit_message_is_blocked(self) -> None:
        self.stage("a.md", "clean\n")
        self.assert_blocked(self.commit("docs: notes\n\nfrom the zebra WIDGET repo"), "commit message line 3")
        self.assertEqual(self.head_count(), 1)

    def test_verbose_diff_below_scissors_is_ignored(self) -> None:
        message = self.tmp / "msg"
        message.write_text(
            "docs: clean\n\n# ------------------------ >8 ------------------------\n-acme-secret\n", encoding="utf-8"
        )
        result = subprocess.run(
            ["python3", "scripts/private-names-check.py", "message", str(message)],
            cwd=self.repo, env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clean_commit_passes(self) -> None:
        self.stage("a.md", "nothing private\n")
        result = self.commit("docs: clean")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.head_count(), 2)

    def test_deleting_a_file_with_a_name_passes(self) -> None:
        self.git("config", "--unset", "core.hooksPath")
        self.stage("old.md", "acme-secret\n")
        self.assertEqual(self.commit("seed").returncode, 0)
        self.git("config", "core.hooksPath", ".githooks")
        self.git("rm", "-q", "old.md")
        self.assertEqual(self.commit("docs: remove old").returncode, 0)

    def test_unset_list_path_passes_with_notice(self) -> None:
        self.git("config", "--unset", "privateNames.file")
        self.stage("a.md", "acme-secret\n")
        result = self.commit("docs: acme-secret")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("privateNames.file is not set", result.stderr)

    def test_missing_list_file_passes_with_notice(self) -> None:
        self.names.unlink()
        self.stage("a.md", "acme-secret\n")
        result = self.commit("docs: acme-secret")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("list file not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
