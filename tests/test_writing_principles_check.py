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
    "p8", "p8-source", "p9a", "p9b", "p9c", "p9d", "p11", "p12",
)
# Listed for the verifier but never counted as FAIL.
LIST_ONLY_KEYS = ("p3-allow", "p7-section", "p8-source")

EXPECTED_FAIL_COUNTS = {
    "p1": 1, "p1b": 1, "p2": 2, "p3": 2, "p3-allow": 0, "p4t": 1, "p4c": 1, "p5": 2,
    "p7": 2, "p7a": 1, "p7-section": 1, "p8": 13, "p8-source": 2, "p9a": 1, "p9b": 1, "p9c": 3,
    "p9d": 6, "p11": 1, "p12": 5,
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


def block_of(output: str, title: str) -> str:
    """The body of the ``== <title>…`` block (up to the next ``== `` heading or SUMMARY)."""
    match = re.search(rf"(?ms)^== {re.escape(title)}.*?(?=^== |^SUMMARY )", output)
    assert match is not None, f"{title}\n{output}"
    return match.group(0)


class PassFixtureTests(unittest.TestCase):
    def test_pass_fixture_is_clean(self) -> None:
        result = run_check("--repo", str(PASS_DIR))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT PASS", result.stdout)
        summary = parse_summary(result.stdout)
        for key in HARD_KEYS:
            if key not in LIST_ONLY_KEYS:
                self.assertEqual(summary[key], 0, f"{key}\n{result.stdout}")
        self.assertEqual(summary["p3-allow"], 1, result.stdout)
        self.assertEqual(summary["p7-section"], 1, result.stdout)
        self.assertEqual(summary["p8-source"], 1, result.stdout)
        self.assertEqual(summary["p9d"], 0, result.stdout)
        self.assertGreaterEqual(summary["p4h"], 1, result.stdout)
        self.assertRegex(result.stdout, r"(?m)^設定檔：.*；標題引用：docs/guide\.md、docs/overview\.md$")
        self.assertIn("AuthServer.kt", block_of(result.stdout, "p8-source"))

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

    def test_p9d_skips_binary_files_and_changelog(self) -> None:
        # blob.bin (a NUL byte, otherwise valid UTF-8), latin1.txt (invalid UTF-8) and CHANGELOG.md all quote
        # a title that does not exist; none of them may be reported.
        for name in ("blob.bin", "latin1.txt"):
            self.assertTrue((PASS_DIR / "assets" / name).is_file(), name)
        result = run_check("--repo", str(PASS_DIR))

        self.assertEqual(parse_summary(result.stdout)["p9d"], 0, result.stdout)
        self.assertNotIn("已改名的舊標題", result.stdout)
        self.assertNotIn("assets/", result.stdout)


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
        # p8: a bare （讀碼） is not a source marker; （讀碼：<檔名>） is (listed in p8-source, never in p8).
        self.assertRegex(out, r"(?m)^p8-evidence\.md:\d+: .*（讀碼）。$")
        self.assertNotIn("Resolver.kt", block_of(out, "p8 "))
        self.assertIn("Resolver.kt", block_of(out, "p8-source"))
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

    def test_p8_source_marker_and_placeholder_rules(self) -> None:
        result = run_check("--repo", str(FAIL_DIR))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        out = result.stdout
        # Not reported: backtick-quoted placeholders, the verb phrase 用來讀碼, a （讀碼：…） format example.
        for lookalike in ("只用來讀碼", "格式說明：", "驗證欄只用兩種標法"):
            self.assertNotIn(lookalike, out)
        # Every other use of 「讀碼」 is reported: only the verb phrase is let through.
        p8 = block_of(out, "p8 ")
        self.assertRegex(p8, r"(?m)^p8-evidence\.md:\d+: 從讀碼來看會成功。$")
        self.assertRegex(p8, r"(?m)^p8-evidence\.md:\d+: \(讀碼:看起來是這樣\)。$")
        self.assertRegex(p8, r"(?m)^p8-evidence\.md:\d+: 只靠讀碼判斷結果。$")
        # The verb phrase is let through only when it ends at punctuation, a space, 「的」 or the end of the line.
        self.assertRegex(p8, r"(?m)^p8-evidence\.md:\d+: 這段用來讀碼確認結果會成功。$")
        self.assertRegex(p8, r"(?m)^p8-evidence\.md:\d+: 用來讀碼表明會成功。$")
        # Reported: an unquoted placeholder in a table cell, and a marker whose content is not a source.
        self.assertRegex(out, r"(?m)^p8-evidence\.md:\d+: \| Android 15 \| 已實測（日期，環境） \|$")
        self.assertRegex(out, r"(?m)^p8-evidence\.md:\d+: .*隨便寫什麼都可以）。  （出處標示不是檔名、符號或章節）$")
        # Listed, not failed: a marker without an evidence level goes to p8-source for the verifier.
        listed = block_of(out, "p8-source")
        self.assertIn("app/entry.client.tsx", listed)
        self.assertIn("Resolver.kt", listed)
        self.assertNotIn("app/entry.client.tsx", block_of(out, "p8 "))

    def test_p9d_reports_missing_titles_and_section_numbers(self) -> None:
        result = run_check("--repo", str(FAIL_DIR))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("標題引用：p9d-headings.md", result.stdout)
        block = block_of(result.stdout, "p9d ")
        self.assertRegex(block, r"(?m)^p9d-refs\.kt:1: 〈不存在的標題〉（p9d-headings\.md 沒有這個標題）$")
        self.assertRegex(block, r"(?m)^p9d-refs\.kt:2: 〈1\.2〉（p9d-headings\.md 沒有這個標題）$")
        self.assertRegex(block, r"(?m)^p9d-refs\.kt:5: 節號 1\.3（p9d-headings\.md 沒有這個節號）$")
        # A parenthesised suffix may be left out, but not invented.
        self.assertRegex(block, r"(?m)^p9d-refs\.kt:7: 〈1\.1 子節（不存在的後綴）〉（p9d-headings\.md 沒有這個標題）$")
        # A bare number at the end of a sentence is a section number.
        self.assertRegex(block, r"(?m)^p9d-refs\.kt:8: 節號 7（p9d-headings\.md 沒有這個節號）$")
        # A non-Markdown file and a Markdown file are both scanned.
        self.assertRegex(block, r"(?m)^p9-links\.md:\d+: 〈消失的章節〉（p9d-headings\.md 沒有這個標題）$")
        # Bare title, number-only and number+title forms resolve; so does a bare section number.
        for fine in ("〈第一節〉", "〈1.1〉", "〈1.1 子節〉", "節號 1（"):
            self.assertNotIn(fine, block)
        self.assertEqual(len(re.findall(r"(?m)^\S+:\d+: ", block)), 6, block)

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


@unittest.skipIf(shutil.which("git") is None, "git is not on PATH")
class HeadingRefTests(unittest.TestCase):
    """p9d end to end in a throw-away git repo: rename a heading and the stale reference is caught."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True, capture_output=True)
        (self.root / "docs").mkdir()
        (self.root / "src").mkdir()
        self.write_design("## 2. 流程")
        (self.root / "src" / "a.kt").write_text("// design.md〈流程〉\n", encoding="utf-8")
        (self.root / ".writing-principles.conf").write_text("HEADING_REF=docs/design.md\n", encoding="utf-8")
        self.stage()

    def stage(self) -> None:
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True, capture_output=True)

    def write_design(self, heading: str) -> None:
        (self.root / "docs" / "design.md").write_text(
            f"# 設計\n\n讀者：維護者\n型別：參考\n\n{heading}\n\n流程只有一句。\n", encoding="utf-8"
        )

    def test_renamed_heading_turns_red_and_restoring_it_turns_green(self) -> None:
        green = run_check("--repo", str(self.root))
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)
        self.assertEqual(parse_summary(green.stdout)["p9d"], 0, green.stdout)
        self.assertIn("標題引用：docs/design.md", green.stdout)

        self.write_design("## 2. 處理流程")
        red = run_check("--repo", str(self.root))
        self.assertEqual(red.returncode, 1, red.stdout + red.stderr)
        self.assertEqual(parse_summary(red.stdout)["p9d"], 1, red.stdout)
        self.assertRegex(red.stdout, r"(?m)^src/a\.kt:1: 〈流程〉（docs/design\.md 沒有這個標題）$")

        self.write_design("## 2. 流程")
        restored = run_check("--repo", str(self.root))
        self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
        self.assertEqual(parse_summary(restored.stdout)["p9d"], 0, restored.stdout)

    def test_disabled_without_heading_ref(self) -> None:
        (self.root / ".writing-principles.conf").write_text("TICKET_RE=PROJ-[0-9]+\n", encoding="utf-8")
        self.write_design("## 2. 處理流程")

        result = run_check("--repo", str(self.root))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(parse_summary(result.stdout)["p9d"], 0, result.stdout)
        self.assertIn("標題引用：未設定", result.stdout)

    def test_missing_target_document_is_a_usage_error(self) -> None:
        (self.root / ".writing-principles.conf").write_text("HEADING_REF=docs/nope.md\n", encoding="utf-8")

        result = run_check("--repo", str(self.root))

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HEADING_REF", result.stderr)

    def test_invalid_prefix_regex_is_a_usage_error(self) -> None:
        result = run_check("--repo", str(self.root), "--heading-ref", "docs/design.md (unclosed")

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HEADING_REF", result.stderr)

    def test_prefix_regex_matching_the_empty_string_is_a_usage_error(self) -> None:
        (self.root / ".writing-principles.conf").write_text("HEADING_REF=docs/design.md .*\n", encoding="utf-8")

        result = run_check("--repo", str(self.root))

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("空字串", result.stderr)
        self.assertIn("HEADING_REF", result.stderr)

    def test_parenthesised_suffix_of_a_title_may_be_left_out(self) -> None:
        self.write_design("## 2. 流程（概要）")
        (self.root / "src" / "c.kt").write_text(
            "// design.md〈2. 流程〉\n// design.md〈流程（別的）〉\n// design.md〈2. 流程（概要）〉、〈流程（概要）〉\n",
            encoding="utf-8",
        )
        self.stage()

        result = run_check("--repo", str(self.root))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(parse_summary(result.stdout)["p9d"], 1, result.stdout)
        self.assertRegex(result.stdout, r"(?m)^src/c\.kt:2: 〈流程（別的）〉（docs/design\.md 沒有這個標題）$")
        self.assertNotIn("src/a.kt:", result.stdout)

    def test_a_plain_number_is_a_section_number_only_before_a_boundary(self) -> None:
        self.write_design("## 1. 第一節")
        (self.root / "src" / "a.kt").write_text("// ok\n", encoding="utf-8")
        (self.root / "src" / "e.kt").write_text(
            "// design.md 2 份\n// design.md 2026 年版\n// design.md 2）\n// design.md 2.5 份\n",
            encoding="utf-8",
        )
        self.stage()

        result = run_check("--repo", str(self.root))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(parse_summary(result.stdout)["p9d"], 2, result.stdout)
        self.assertRegex(result.stdout, r"(?m)^src/e\.kt:3: 節號 2（docs/design\.md 沒有這個節號）$")
        self.assertRegex(result.stdout, r"(?m)^src/e\.kt:4: 節號 2\.5（docs/design\.md 沒有這個節號）$")
        self.assertNotIn("src/e.kt:1:", result.stdout)
        self.assertNotIn("src/e.kt:2:", result.stdout)

    def test_references_inside_inline_code_are_examples(self) -> None:
        (self.root / "src" / "d.kt").write_text(
            "// 範例：`design.md〈不存在〉` 與 `design.md 9 節`\n"
            "// 檔名在反引號內、〈〉在外面：`docs/design.md`〈不存在〉\n"
            "// 同一行兩個：`design.md〈甲〉` 和 design.md〈乙〉\n",
            encoding="utf-8",
        )
        self.stage()

        result = run_check("--repo", str(self.root))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(parse_summary(result.stdout)["p9d"], 2, result.stdout)
        self.assertNotIn("src/d.kt:1:", result.stdout)
        self.assertRegex(result.stdout, r"(?m)^src/d\.kt:2: 〈不存在〉（docs/design\.md 沒有這個標題）$")
        self.assertRegex(result.stdout, r"(?m)^src/d\.kt:3: 〈乙〉（docs/design\.md 沒有這個標題）$")
        self.assertNotIn("〈甲〉", result.stdout)

    def test_flag_adds_a_document_and_a_custom_prefix(self) -> None:
        (self.root / "src" / "b.kt").write_text(
            "// 設計文件〈流程〉\n// 設計文件〈不存在〉\n", encoding="utf-8"
        )
        self.stage()

        result = run_check("--repo", str(self.root), "--heading-ref", "docs/design.md design\\.md|設計文件")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(parse_summary(result.stdout)["p9d"], 1, result.stdout)
        self.assertRegex(result.stdout, r"(?m)^src/b\.kt:2: 〈不存在〉（docs/design\.md 沒有這個標題）$")
        self.assertNotIn("src/b.kt:1:", result.stdout)

    def test_explicit_files_limit_the_p9d_scan(self) -> None:
        (self.root / "src" / "stale.kt").write_text("// design.md〈已不存在〉\n", encoding="utf-8")
        self.stage()

        everything = run_check("--repo", str(self.root))
        only_a = run_check("--repo", str(self.root), str(self.root / "src" / "a.kt"))

        self.assertEqual(parse_summary(everything.stdout)["p9d"], 1, everything.stdout)
        self.assertEqual(parse_summary(only_a.stdout)["p9d"], 0, only_a.stdout)


if __name__ == "__main__":
    unittest.main()
