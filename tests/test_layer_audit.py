"""Assertions for global/shared/skills/layer-audit/scripts/layer_audit.py.

Fixture repos are built in a temp dir per test (not committed) so that no `.github/workflows`
file lands in this repo's tree.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "global" / "shared" / "skills" / "layer-audit" / "scripts" / "layer_audit.py"

sys.dont_write_bytecode = True  # keep __pycache__ out of the skill dir (sync-profile copies the tree)
spec = importlib.util.spec_from_file_location("layer_audit", SCRIPT)
la = importlib.util.module_from_spec(spec)
sys.modules["layer_audit"] = la
spec.loader.exec_module(la)

PACKAGE = {"name": "fx", "scripts": {"lint": "eslint . --max-warnings 0", "typecheck": "tsc"},
           "devDependencies": {"eslint": "9.0.0", "typescript": "5.0.0"}}
ESLINT_CONFIG = "export default [{ rules: { 'no-var': 'error' } }]\n"


def workflow(steps: str, on: str = "on:\n  pull_request:\n  push:\n    branches: [main]\n", job_extra: str = "") -> str:
    body = textwrap.indent(textwrap.dedent(steps).strip("\n"), " " * 6)
    return f"name: CI\n{on}jobs:\n  check:\n    runs-on: ubuntu-latest\n{job_extra}    steps:\n      - uses: actions/checkout@v4\n{body}\n"


class FixtureCase(unittest.TestCase):
    def make(self, files: dict[str, str]) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
        return root

    def ts_repo(self, wf: str | None, **extra) -> Path:
        files = {"package.json": PACKAGE, "tsconfig.json": "{}", "eslint.config.js": ESLINT_CONFIG, "src/a.ts": "export const a = 1\n"}
        if wf is not None:
            files[".github/workflows/ci.yml"] = wf
        files.update(extra)
        return self.make(files)

    def rows(self, root: Path) -> list[dict]:
        return la.audit(root)["rows"]

    def row(self, root: Path, check: str) -> dict:
        hits = [r for r in self.rows(root) if r["check"] == check]
        self.assertEqual(len(hits), 1, f"expected one row {check!r}, got {[r['check'] for r in self.rows(root)]}")
        return hits[0]


class FourRequiredCases(FixtureCase):
    def test_lint_configured_but_ci_never_calls_it_is_local_only(self):
        root = self.ts_repo(workflow("- run: pnpm typecheck\n"))
        eslint = self.row(root, "eslint（TypeScript）")
        self.assertEqual(eslint["status"], "local-only")
        self.assertIn("eslint.config.js", eslint["evidence"])
        self.assertEqual(self.row(root, "lint（TypeScript）")["status"], "local-only")

    def test_ci_calls_lint_but_failure_is_swallowed(self):
        variants = {
            "continue-on-error": "- run: pnpm lint\n  continue-on-error: true\n",
            "or-true": "- run: pnpm lint || true\n",
            "job-continue-on-error": None,
        }
        for name, steps in variants.items():
            with self.subTest(name):
                if steps is None:
                    wf = workflow("- run: pnpm lint\n", job_extra="    continue-on-error: true\n")
                else:
                    wf = workflow(steps)
                eslint = self.row(self.ts_repo(wf), "eslint（TypeScript）")
                self.assertEqual(eslint["status"], "non-blocking")
                self.assertRegex(eslint["note"], r"continue-on-error|\|\| true")

    def test_lint_enabled_and_ci_fails_is_blocking_with_call_chain(self):
        root = self.ts_repo(workflow("- run: pnpm lint\n- run: pnpm typecheck\n"))
        eslint = self.row(root, "eslint（TypeScript）")
        self.assertEqual(eslint["status"], "blocking")
        self.assertIn(".github/workflows/ci.yml:", eslint["evidence"])
        self.assertIn("eslint . --max-warnings 0", eslint["evidence"])
        base = self.row(root, "lint（TypeScript）")
        self.assertTrue(base["baseline"])
        self.assertEqual(base["status"], "blocking")

    def test_nothing_at_all_is_absent(self):
        root = self.make({"package.json": {"name": "bare"}, "src/a.ts": "export const a = 1\n"})
        for kind in ("格式化", "lint", "型別或靜態分析"):
            row = self.row(root, f"{kind}（TypeScript）")
            self.assertEqual(row["status"], "absent")
            self.assertTrue(row["baseline"])
        self.assertEqual(self.row(root, "CI 設定")["status"], "absent")


class OtherShapes(FixtureCase):
    def test_warn_rules_without_max_warnings_get_their_own_row(self):
        pkg = dict(PACKAGE, scripts={"lint": "eslint ."})
        root = self.ts_repo(workflow("- run: pnpm lint\n"), **{"package.json": pkg,
                                                              "eslint.config.js": "export default [{ rules: { 'no-var': 'warn' } }]\n"})
        self.assertEqual(self.row(root, "eslint（TypeScript）")["status"], "blocking")
        self.assertEqual(self.row(root, "eslint 的 warning 級規則（TypeScript）")["status"], "non-blocking")

    def test_push_only_workflow_does_not_gate_prs(self):
        wf = workflow("- run: pnpm lint\n", on="on:\n  push:\n    branches: [main]\n")
        eslint = self.row(self.ts_repo(wf), "eslint（TypeScript）")
        self.assertEqual(eslint["status"], "non-blocking")
        self.assertIn("PR 不跑", eslint["note"])

    def test_job_if_excluding_pull_requests(self):
        wf = workflow("- run: pnpm lint\n", job_extra="    if: github.event_name != 'pull_request'\n")
        self.assertEqual(self.row(self.ts_repo(wf), "eslint（TypeScript）")["status"], "non-blocking")

    def test_safe_step_if_still_blocks(self):
        wf = workflow("- if: ${{ !cancelled() }}\n  run: pnpm lint\n")
        self.assertEqual(self.row(self.ts_repo(wf), "eslint（TypeScript）")["status"], "blocking")

    def test_semicolon_in_package_script_swallows(self):
        pkg = dict(PACKAGE, scripts={"lint": "eslint . --max-warnings 0; echo done"})
        root = self.ts_repo(workflow("- run: pnpm lint\n"), **{"package.json": pkg})
        self.assertEqual(self.row(root, "eslint（TypeScript）")["status"], "non-blocking")

    def test_shell_script_indirection_and_pipe_without_pipefail(self):
        root = self.ts_repo(workflow("- run: bash scripts/lint.sh\n"),
                            **{"scripts/lint.sh": "#!/bin/bash\nset -e\nnpx eslint . --max-warnings 0 | tee lint.log\n"})
        eslint = self.row(root, "eslint（TypeScript）")
        self.assertEqual(eslint["status"], "non-blocking")
        self.assertIn("pipefail", eslint["note"])
        root = self.ts_repo(workflow("- run: bash scripts/lint.sh\n"),
                            **{"scripts/lint.sh": "#!/bin/bash\nset -euo pipefail\nnpx eslint . --max-warnings 0 | tee lint.log\n"})
        self.assertEqual(self.row(root, "eslint（TypeScript）")["status"], "blocking")

    def test_multiline_run_block_is_parsed(self):
        wf = workflow("- name: checks\n  run: |\n    echo start\n    pnpm lint\n")
        self.assertEqual(self.row(self.ts_repo(wf), "eslint（TypeScript）")["status"], "blocking")

    def test_reusable_workflow_inherits_pr_trigger(self):
        caller = "name: CI\non:\n  pull_request:\njobs:\n  call:\n    uses: ./.github/workflows/_lint.yml\n"
        callee = workflow("- run: pnpm lint\n", on="on:\n  workflow_call:\n")
        root = self.ts_repo(caller, **{".github/workflows/_lint.yml": callee})
        self.assertEqual(self.row(root, "eslint（TypeScript）")["status"], "blocking")

    def test_dart_format_without_exit_flag(self):
        root = self.make({"pubspec.yaml": "name: fx\n", "lib/a.dart": "void main() {}\n",
                          ".github/workflows/ci.yml": workflow("- run: dart format --output=none .\n")})
        self.assertEqual(self.row(root, "dart format（Dart）")["status"], "non-blocking")

    def test_dart_analyze_without_fatal_infos_leaves_lints_unblocked(self):
        root = self.make({"pubspec.yaml": "name: fx\n", "lib/a.dart": "void main() {}\n", "analysis_options.yaml": "linter:\n",
                          ".github/workflows/ci.yml": workflow("- run: dart analyze\n")})
        self.assertEqual(self.row(root, "dart/flutter analyze（Dart）")["status"], "blocking")
        self.assertEqual(self.row(root, "dart/flutter analyze 的 warning 級規則（Dart）")["status"], "non-blocking")

    def test_gradle_plugin_in_catalog_but_not_applied_is_inactive(self):
        root = self.make({
            "build.gradle.kts": "plugins {\n    alias(libs.plugins.kotlinter) apply false\n}\n",
            "app/build.gradle.kts": "plugins {\n    kotlin(\"jvm\")\n}\n",
            "app/src/main/kotlin/A.kt": "class A\n",
            "gradle/libs.versions.toml": "[plugins]\nkotlinter = { id = \"org.jmailen.kotlinter\", version = \"5.0.0\" }\n",
            ".github/workflows/ci.yml": workflow("- run: ./gradlew lintKotlin\n"),
        })
        self.assertEqual(self.row(root, "ktlint（Kotlin）")["status"], "inactive")

    def test_gradle_plugin_applied_by_alias_is_blocking(self):
        root = self.make({
            "app/build.gradle.kts": "plugins {\n    alias(libs.plugins.android.library)\n    alias(libs.plugins.kotlinter)\n}\n",
            "app/src/main/kotlin/A.kt": "class A\n",
            "gradle/libs.versions.toml": "[plugins]\nandroid-library = { id = \"com.android.library\", version = \"8.0.0\" }\n"
                                         "kotlinter = { id = \"org.jmailen.kotlinter\", version = \"5.0.0\" }\n",
            ".github/workflows/ci.yml": workflow("- run: ./gradlew lintKotlin lint\n"),
        })
        self.assertEqual(self.row(root, "ktlint（Kotlin）")["status"], "blocking")
        self.assertEqual(self.row(root, "Android Lint（Kotlin）")["status"], "blocking")
        self.assertEqual(self.row(root, "Android Lint 的 warning 級規則（Kotlin）")["status"], "non-blocking")

    def test_install_script_mentioning_tool_is_not_a_run(self):
        root = self.make({"Package.swift": "// swift-tools-version:5.9\n", "Sources/A/a.swift": "let a = 1\n",
                          ".swiftlint.yml": "disabled_rules: []\n",
                          "scripts/install-swiftlint.sh": "#!/bin/bash\nset -e\nunzip swiftlint.zip swiftlint -d .tools\n",
                          ".github/workflows/ci.yml": workflow("- run: bash scripts/install-swiftlint.sh\n")})
        self.assertEqual(self.row(root, "SwiftLint（Swift）")["status"], "local-only")


    def test_job_outside_required_checks_needs_chain_does_not_block(self):
        wf = ("name: CI\non:\n  pull_request:\njobs:\n  lint:\n    runs-on: x\n    steps:\n      - run: pnpm lint\n"
              "  extra:\n    runs-on: x\n    steps:\n      - run: pnpm typecheck\n"
              "  ci:\n    needs: [lint]\n    runs-on: x\n    steps:\n      - run: echo ok\n")
        root = self.ts_repo(wf)
        repo = la.Repo(root)
        invs, _, _ = la.github_invocations(repo)
        la.apply_required(invs, la.github_invocations.parsed, ["ci"])
        by_job = {i.job: i for i in invs if i.text.startswith("pnpm")}
        self.assertEqual(by_job["lint"].gate, [])
        self.assertIn("不在必要檢查", by_job["extra"].gate[0])
        invs2, _, _ = la.github_invocations(repo)
        la.apply_required(invs2, la.github_invocations.parsed, ["unrelated-context"])
        self.assertTrue(all(not i.gate for i in invs2), "no matching context means unknown, not a demotion")


class OutputContract(FixtureCase):
    def test_statuses_are_fixed_and_rows_have_all_columns(self):
        root = self.ts_repo(workflow("- run: pnpm lint\n"))
        for r in self.rows(root):
            self.assertIn(r["status"], la.STATUSES)
            self.assertIn(r["layer"], la.LAYERS)
            for key in ("check", "evidence"):
                self.assertTrue(r[key], r)

    def test_cli_json_and_markdown_and_read_only(self):
        root = self.ts_repo(workflow("- run: pnpm lint\n"))

        def digest():
            h = hashlib.sha256()
            for p in sorted(root.rglob("*")):
                h.update(str(p.relative_to(root)).encode())
                if p.is_file():
                    h.update(p.read_bytes())
            return h.hexdigest()

        before = digest()
        out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(root), "--format", "json"], capture_output=True, text=True, check=True)
        data = json.loads(out.stdout)
        self.assertIn("rows", data)
        md = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(root)], capture_output=True, text=True, check=True).stdout
        self.assertIn("| 層 | 檢查項 | 狀態 | 證據 | 備註 |", md)
        self.assertEqual(before, digest())

    def test_stdlib_only(self):
        import ast

        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        stdlib = set(sys.stdlib_module_names)
        self.assertEqual(sorted(m for m in mods if m not in stdlib and m != "__future__"), [])


if __name__ == "__main__":
    unittest.main()
