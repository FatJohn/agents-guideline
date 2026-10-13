"""Assertions for skills/writing-principles/scripts/check_docs.py.

The fixtures under tests/fixtures/writing-principles are the red/green evidence for
every machine-checked principle: ``pass/`` must stay clean, ``fail/`` has one file per
principle with a fixed expected count.  Needs only python3 (and git for one test).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "skills" / "writing-principles" / "scripts" / "check_docs.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "writing-principles"
PASS_DIR = FIXTURES / "pass"
FAIL_DIR = FIXTURES / "fail"

HARD_KEYS = (
    "p1", "p1b", "p2", "p3", "p3-allow", "p4t", "p4c", "p5", "p7", "p7a", "p7-section",
    "p8", "p9a", "p9b", "p9c", "p11", "p12",
)

EXPECTED_FAIL_COUNTS = {
    "p1": 1, "p1b": 1, "p2": 2, "p3": 2, "p3-allow": 0, "p4t": 1, "p4c": 1, "p5": 2,
    "p7": 2, "p7a": 1, "p7-section": 1, "p8": 6, "p9a": 1, "p9b": 1, "p9c": 3, "p11": 1, "p12": 5,
}


def run_check(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def parse_summary(output: str) -> dict[str, int]:
    lines = [line for line in output.splitlines() if line.startswith("SUMMARY ")]
    assert len(lines) == 1, output
    return {key: int(value) for key, value in re.findall(r"([\w-]+)=(\d+)", lines[0])}


class PassFixtureTests(unittest.TestCase):
    def test_pass_fixture_is_clean(self) -> None:
        result = run_check("--repo", str(PASS_DIR))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT PASS", result.stdout)
        summary = parse_summary(result.stdout)
        for key in HARD_KEYS:
            if key not in ("p3-allow", "p7-section"):
                self.assertEqual(summary[key], 0, f"{key}\n{result.stdout}")
        self.assertEqual(summary["p3-allow"], 1, result.stdout)
        self.assertEqual(summary["p7-section"], 1, result.stdout)
        self.assertGreaterEqual(summary["p4h"], 1, result.stdout)

    def test_default_scope_excludes_adr_and_changelog(self) -> None:
        result = run_check("--repo", str(PASS_DIR), "--list")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        listed = result.stdout.splitlines()
        self.assertIn("README.md", listed)
        self.assertIn("docs/guide.md", listed)
        self.assertFalse([p for p in listed if p.startswith("docs/adr/")], listed)
        self.assertNotIn("CHANGELOG.md", listed)
        # The excluded files really contain trigger words: scanning them explicitly must fail.
        explicit = run_check(
            "--repo", str(PASS_DIR), str(PASS_DIR / "docs" / "adr" / "0001-example.md")
        )
        self.assertEqual(explicit.returncode, 1, explicit.stdout)


class FailFixtureTests(unittest.TestCase):
    def test_fail_fixture_counts(self) -> None:
        result = run_check("--repo", str(FAIL_DIR))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("RESULT FAIL", result.stdout)
        summary = parse_summary(result.stdout)
        self.assertEqual({k: summary[k] for k in HARD_KEYS}, EXPECTED_FAIL_COUNTS, result.stdout)
        # Look-alikes that must not be reported: a token-signature phrase and a list inside a code block.
        self.assertNotIn("未驗簽", result.stdout)
        self.assertNotIn("fence-only-item", result.stdout)

    def test_template_checkbox_and_source_marker_lookalikes(self) -> None:
        result = run_check("--repo", str(FAIL_DIR))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        out = result.stdout
        # p12: a lone checkbox is reported in a normal file, allowed in a PR template; a lone plain item stays reported there.
        self.assertRegex(out, r"(?m)^p12-single-item\.md:\d+: - \[ \] 唯一的勾選項$")
        self.assertRegex(out, r"(?m)^\.github/pull_request_template\.md:\d+: - 單一普通項目$")
        self.assertNotRegex(out, r"(?m)^\.github/pull_request_template\.md:\d+: - \[ \] 單一勾選項")
        # p8: a bare （讀碼） is not a source marker; （讀碼：<檔名>） is.
        self.assertRegex(out, r"(?m)^p8-evidence\.md:\d+: .*（讀碼）。$")
        self.assertNotIn("Resolver.kt", out)
        # p8: a trigger word hidden inside the marker is still reported; the same-named file under a
        # subdirectory is not a PR template, so its lone checkbox stays reported.
        self.assertRegex(out, r"(?m)^p8-evidence\.md:\d+: 登入會成功（讀碼：推論）。$")
        self.assertRegex(out, r"(?m)^nested/\.github/pull_request_template\.md:\d+: - \[ \] 子目錄的單一勾選項$")
        # p7: a quoted section name that carries no trigger word is still a violation.
        section = re.search(r"(?ms)^== p7-section：.*?(?=^== |^SUMMARY )", out)
        self.assertIsNotNone(section, out)
        self.assertIn("`## 未發佈` 區段", section.group(0))
        self.assertRegex(out, r"(?m)^p7-unreleased\.md:\d+: 離線模式 unreleased，細節見「狀態」節。$")
        self.assertNotIn("「狀態」節", section.group(0))

    def test_exclude_flag_and_config(self) -> None:
        excluded = run_check("--repo", str(FAIL_DIR), "--exclude", "p2-*.md")
        self.assertEqual(excluded.returncode, 1, excluded.stdout)
        self.assertEqual(parse_summary(excluded.stdout)["p2"], 0, excluded.stdout)
        self.assertEqual(parse_summary(excluded.stdout)["p3"], 2, excluded.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "alt.conf"
            conf.write_text(
                "# overrides the ticket pattern\nTICKET_RE=ZZZ-[0-9]+\n"
                "UNRELEASED_PHRASE=僅在主幹，尚未發版\n",
                encoding="utf-8",
            )
            overridden = run_check("--repo", str(FAIL_DIR), "--config", str(conf))
        summary = parse_summary(overridden.stdout)
        self.assertEqual(summary["p4t"], 0, overridden.stdout)
        self.assertEqual(summary["p4c"], 1, overridden.stdout)

    def test_ignore_words_must_be_compounds_with_a_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for bad in (".", "前|在", "前景", "目前"):
                conf = Path(tmp) / "bad.conf"
                conf.write_text(f"IGNORE_WORDS={bad}\n", encoding="utf-8")
                result = run_check("--repo", str(FAIL_DIR), "--config", str(conf))
                self.assertEqual(result.returncode, 2, (bad, result.stderr))
                self.assertIn("IGNORE_WORDS", result.stderr)
            conf = Path(tmp) / "ok.conf"
            conf.write_text("IGNORE_WORDS=出現在\n", encoding="utf-8")
            result = run_check("--repo", str(PASS_DIR), "--config", str(conf))
            self.assertIn("詞表覆寫：IGNORE_WORDS", result.stdout)

    def test_missing_config_and_empty_scope_are_usage_errors(self) -> None:
        missing = run_check("--repo", str(FAIL_DIR), "--config", str(FAIL_DIR / "nope.conf"))
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            empty = run_check("--repo", tmp)
        self.assertEqual(empty.returncode, 2, empty.stdout + empty.stderr)


class ModeTests(unittest.TestCase):
    def test_headerless_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.md"
            page.write_text("讀者：維護者\n型別：說明\n\n正文只有一段。\n", encoding="utf-8")

            headerless = run_check("--repo", tmp, "--headerless", str(page))
            normal = run_check("--repo", tmp, str(page))

        self.assertEqual(parse_summary(headerless.stdout)["p1"], 0, headerless.stdout)
        self.assertEqual(headerless.returncode, 0, headerless.stdout)
        self.assertEqual(parse_summary(normal.stdout)["p1"], 1, normal.stdout)
        self.assertEqual(normal.returncode, 1, normal.stdout)

    @unittest.skipIf(shutil.which("git") is None, "git is not on PATH")
    def test_git_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True, capture_output=True)
            (root / "tracked.md").write_text("# a\n", encoding="utf-8")
            (root / "untracked.md").write_text("# b\n", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "add", "tracked.md"], check=True, capture_output=True)

            result = run_check("--repo", tmp, "--list")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.split(), ["tracked.md"])


if __name__ == "__main__":
    unittest.main()
