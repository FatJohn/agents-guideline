"""Run the shell-level assertions for hooks/block-ci-edit.sh and config/ripgreprc.

The two scripts under tests/ build synthetic input (hook stdin JSON, a throwaway
fixture tree) and need no Claude Code or network.  They are wrapped here so
``python3 -m unittest discover -s tests`` covers them with the rest.  A missing
tool (bash, jq, rg, git) skips instead of failing: the hook is fail-open without
jq, and rg may be unusable on a host (see docs/hosts-detail.md, Windows).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS = REPO_ROOT / "tests"


def run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(TESTS / script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def count_lines(output: str, prefix: str) -> int:
    return sum(1 for line in output.splitlines() if line.startswith(prefix))


class BlockCiEditHookTests(unittest.TestCase):
    def test_hook_assertions_pass(self) -> None:
        for tool in ("bash", "jq"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} is not on PATH")

        result = run_script("test-block-ci-edit.sh")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(count_lines(result.stdout, "FAIL"), 0, result.stdout)
        # A script that prints nothing and exits 0 must not pass.
        self.assertGreaterEqual(count_lines(result.stdout, "PASS"), 13, result.stdout)
        self.assertIn("failures=0", result.stdout)


class RipgreprcTests(unittest.TestCase):
    def test_ripgreprc_assertions_pass(self) -> None:
        for tool in ("bash", "rg", "git"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} is not on PATH")

        with tempfile.TemporaryDirectory() as fixture:
            result = run_script(
                "test-ripgreprc.sh", str(REPO_ROOT / "config" / "ripgreprc"), fixture
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(count_lines(result.stdout, "FAIL"), 0, result.stdout)
        self.assertGreaterEqual(count_lines(result.stdout, "PASS"), 4, result.stdout)
        self.assertIn("failures=0", result.stdout)


if __name__ == "__main__":
    unittest.main()
