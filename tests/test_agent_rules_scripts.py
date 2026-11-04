"""Assertions for global/shared/skills/agent-rules/scripts/{rules_index,active_lints_dart}.py.

Fixtures under tests/fixtures/agent-rules: ``repo/`` is a minimal project whose outputs are
in sync (``--check`` must pass); each mutation test copies it and breaks one thing, so the
red side of every check is exercised.  Needs only python3.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "global" / "shared" / "skills" / "agent-rules" / "scripts"
INDEX = SCRIPTS / "rules_index.py"
LINTS = SCRIPTS / "active_lints_dart.py"
ANDROID = SCRIPTS / "active_lints_android.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agent-rules" / "repo"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )


class IndexFixtureInSync(unittest.TestCase):
    def test_check_passes_on_fixture(self) -> None:
        r = run(INDEX, "--repo", str(FIXTURE), "--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("3 條規則", r.stdout)

    def test_list_prints_every_rule(self) -> None:
        r = run(INDEX, "--repo", str(FIXTURE), "--list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SUMMARY rules=3 with_id=2 problems=0", r.stdout)
        self.assertIn("HIGH\tD-1\tdocs/guideline_style.md:", r.stdout)


class IndexMutations(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        shutil.copytree(FIXTURE, self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _edit(self, rel: str, old: str, new: str) -> None:
        p = self.repo / rel
        text = p.read_text(encoding="utf-8")
        assert old in text, (rel, old)
        p.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_stale_target_fails_check_and_generate_fixes_it(self) -> None:
        self._edit("docs/guideline_style.md", "### 檔名用 snake_case（MEDIUM）", "### 檔名用 snake_case，資料夾單數（MEDIUM）")
        r = run(INDEX, "--repo", str(self.repo), "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("AGENTS.md", r.stderr)
        self.assertIn("docs/rules-index.md", r.stderr)
        r = run(INDEX, "--repo", str(self.repo))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("資料夾單數（MEDIUM）", (self.repo / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(run(INDEX, "--repo", str(self.repo), "--check").returncode, 0)

    def test_duplicate_title_is_a_problem(self) -> None:
        self._edit("docs/guideline_widget.md", "### 提取 widget 用 class（MEDIUM）", "### 檔名用 snake_case（MEDIUM）")
        r = run(INDEX, "--repo", str(self.repo), "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("出現 2 次", r.stderr)

    def test_severity_mismatch_with_styleguide(self) -> None:
        self._edit(".gemini/styleguide.md", "*(HIGH)*", "*(LOW)*")
        r = run(INDEX, "--repo", str(self.repo), "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("D-1 的 severity 不一致", r.stderr)

    def test_id_only_in_styleguide(self) -> None:
        self._edit("docs/guideline_widget.md", " <!-- W-1 -->", "")
        r = run(INDEX, "--repo", str(self.repo), "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("W-1 在 .gemini/styleguide.md 有", r.stderr)

    def test_untracked_prefix_is_ignored(self) -> None:
        self._edit(".gemini/styleguide.md", "**W-1 — ", "**CI-9 — Quote every expansion** *(HIGH)*\n\n**W-1 — ")
        self.assertEqual(run(INDEX, "--repo", str(self.repo), "--check").returncode, 0)

    def test_malformed_heading_is_reported(self) -> None:
        self._edit("docs/guideline_style.md", "### 檔名用 snake_case（MEDIUM）", "### 檔名用 snake_case")
        r = run(INDEX, "--repo", str(self.repo), "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("不符格式", r.stderr)

    def test_two_marker_blocks_abort(self) -> None:
        p = self.repo / "AGENTS.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- BEGIN GENERATED RULES -->\n<!-- END GENERATED RULES -->\n", encoding="utf-8")
        r = run(INDEX, "--repo", str(self.repo), "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("恰好各一組", r.stderr)

    def test_missing_config_names_sources(self) -> None:
        (self.repo / ".agent-rules.conf").unlink()
        self.assertEqual(run(INDEX, "--repo", str(self.repo), "--check").returncode, 1)
        self.assertIn("SOURCES", run(INDEX, "--repo", str(self.repo), "--check").stderr)


class DartLints(unittest.TestCase):
    PKG = FIXTURE / "dart_pkg"

    def test_resolves_include_chain(self) -> None:
        r = run(LINTS, "--package", str(self.PKG), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["enabled"], ["eol_at_end_of_file", "file_names", "unawaited_futures"])
        self.assertEqual(report["disabled_here"], ["directives_ordering"])
        self.assertEqual(report["plugins"], [])
        self.assertEqual(len(report["chain"]), 2)

    def test_has_reports_each_state(self) -> None:
        r = run(LINTS, "--package", str(self.PKG), "--has", "file_names", "directives_ordering", "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("file_names\tenabled", r.stdout)
        self.assertIn("directives_ordering\tdisabled here", r.stdout)
        self.assertIn("nope\tnot enabled", r.stdout)
        self.assertEqual(run(LINTS, "--package", str(self.PKG), "--has", "file_names").returncode, 0)

    def test_plugin_detected(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(self.PKG, tmp / "pkg")
            p = tmp / "pkg" / "analysis_options.yaml"
            p.write_text(p.read_text(encoding="utf-8") + "\nanalyzer:\n  plugins:\n    - custom_lint\n", encoding="utf-8")
            report = json.loads(run(LINTS, "--package", str(tmp / "pkg"), "--json").stdout)
            self.assertEqual(report["plugins"], ["custom_lint"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_top_level_plugins_map_detected(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(self.PKG, tmp / "pkg")
            p = tmp / "pkg" / "analysis_options.yaml"
            p.write_text(
                p.read_text(encoding="utf-8")
                + "\nplugins:\n  riverpod_lint:\n    version: ^3.1.9\n    diagnostics:\n      missing_provider_scope: false\n  - dart_code_metrics\n",
                encoding="utf-8",
            )
            report = json.loads(run(LINTS, "--package", str(tmp / "pkg"), "--json").stdout)
            self.assertEqual(report["plugins"], ["riverpod_lint", "dart_code_metrics"])
            self.assertEqual(report["disabled_here"], ["directives_ordering"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AndroidLints(unittest.TestCase):
    MOD = FIXTURE.parent / "android_module"
    DUMP = MOD / "lint-show.txt"

    def _report(self) -> dict:
        r = run(ANDROID, "--module", str(self.MOD), "--dump", str(self.DUMP), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_default_off_plus_gradle_enable_and_lint_xml(self) -> None:
        report = self._report()
        # StopShip: off by default, enabled by gradle `enable +=`; UnusedIds: off by default, lint.xml severity=warning
        self.assertEqual(report["enabled"], ["StopShip", "UnusedIds"])
        # GradleDependency: gradle `disable +=`; HardcodedText: lint.xml severity=ignore
        self.assertEqual(report["disabled_here"], ["GradleDependency", "HardcodedText"])
        self.assertEqual(report["enabled_here"], ["StopShip"])
        self.assertEqual(report["unknown_ids_in_config"], ["NewerVersionAvailable"])
        self.assertEqual(report["total"], 4)

    def test_has_reports_each_state(self) -> None:
        r = run(ANDROID, "--module", str(self.MOD), "--dump", str(self.DUMP), "--has", "StopShip", "GradleDependency", "Nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("StopShip\tenabled", r.stdout)
        self.assertIn("GradleDependency\tdisabled here", r.stdout)
        self.assertIn("Nope\tnot an issue id", r.stdout)

    def test_mutation_removing_disable_line_enables_issue(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(self.MOD, tmp / "m")
            g = tmp / "m" / "build.gradle.kts"
            g.write_text(g.read_text(encoding="utf-8").replace('disable += setOf("GradleDependency", "NewerVersionAvailable")', ""), encoding="utf-8")
            report = json.loads(run(ANDROID, "--module", str(tmp / "m"), "--dump", str(self.DUMP), "--json").stdout)
            self.assertIn("GradleDependency", report["enabled"])
            self.assertEqual(report["unknown_ids_in_config"], [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_unparseable_dump_exits_1(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "dump.txt").write_text("nothing here\n", encoding="utf-8")
            r = run(ANDROID, "--module", str(self.MOD), "--dump", str(tmp / "dump.txt"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("解析不到", r.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
