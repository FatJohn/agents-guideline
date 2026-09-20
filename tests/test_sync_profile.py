"""Tests for the physical profile synchronizer."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync-profile.py"
SPEC = importlib.util.spec_from_file_location("sync_profile", SCRIPT_PATH)
assert SPEC and SPEC.loader
sync_profile = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync_profile
SPEC.loader.exec_module(sync_profile)


def can_symlink(directory: Path) -> bool:
    """Windows needs Developer Mode or elevation to create a link."""

    probe = directory / ".symlink-probe"
    try:
        os.symlink(directory, probe, target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    os.remove(probe)
    return True


def build_repo(root: Path) -> Path:
    """A miniature repository with the same shape the mappings expect."""

    repo = root / "repo"
    (repo / "rules").mkdir(parents=True)
    (repo / "rubrics").mkdir(parents=True)
    (repo / "agents").mkdir(parents=True)
    (repo / "codex" / "skills" / "session-handoff").mkdir(parents=True)
    for name in ("maintain-guideline", "create-pr", "parallel-dispatch"):
        (repo / "skills" / name).mkdir(parents=True)
        (repo / "skills" / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")

    (repo / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (repo / "rules" / "00-environment.md").write_text("# env\n", encoding="utf-8")
    (repo / "rules" / "05-hosts.md").write_text("# hosts\n", encoding="utf-8")
    (repo / "rubrics" / "code-change.md").write_text("# code change\n", encoding="utf-8")
    (repo / "agents" / "worker.md").write_text("# worker\n", encoding="utf-8")
    (repo / "agents" / "verifier.md").write_text("# verifier\n", encoding="utf-8")
    (repo / "codex" / "skills" / "session-handoff" / "SKILL.md").write_text(
        "# handoff\n", encoding="utf-8"
    )
    return repo


class SyncProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = build_repo(self.root)
        self.claude = self.root / "profile" / ".claude"
        self.codex = self.root / "profile" / ".codex"
        self.agents = self.root / "profile" / ".agents"

    def run_sync(self, **kwargs):
        return sync_profile.sync(
            repo=self.repo,
            claude_home=self.claude,
            codex_home=self.codex,
            agents_home=self.agents,
            **kwargs,
        )

    def require_symlinks(self) -> None:
        if not can_symlink(self.root):
            self.skipTest("this host cannot create symlinks")

    def test_dry_run_writes_nothing(self) -> None:
        operations = self.run_sync()

        self.assertTrue(operations)
        self.assertFalse(self.claude.exists())
        self.assertFalse(self.codex.exists())
        self.assertFalse(self.agents.exists())

    def test_first_install_writes_regular_files(self) -> None:
        self.run_sync(apply=True)

        installed = self.claude / "rules" / "00-environment.md"
        self.assertTrue(installed.is_file())
        self.assertFalse(installed.is_symlink())
        self.assertEqual(installed.read_text(encoding="utf-8"), "# env\n")

        # The tree root must be a real directory, not a link.
        self.assertTrue((self.claude / "rules").is_dir())
        self.assertFalse((self.claude / "rules").is_symlink())

        # Both platforms get their entry point and the shared skills.
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# CLAUDE\n")
        self.assertEqual((self.codex / "AGENTS.md").read_text(encoding="utf-8"), "# AGENTS\n")
        self.assertTrue((self.agents / "skills" / "session-handoff" / "SKILL.md").is_file())
        for name in ("maintain-guideline", "create-pr", "parallel-dispatch"):
            self.assertTrue((self.claude / "skills" / name / "SKILL.md").is_file())
            self.assertTrue((self.agents / "skills" / name / "SKILL.md").is_file())

        # worker.md is the entry README's symlink install has been missing.
        self.assertEqual((self.claude / "agents" / "worker.md").read_text(encoding="utf-8"), "# worker\n")

    def test_rerun_reports_everything_unchanged(self) -> None:
        self.run_sync(apply=True)
        operations = self.run_sync(apply=True)

        self.assertTrue(operations)
        self.assertTrue(all(operation.action == "unchanged" for operation in operations))

    def test_directory_symlink_root_is_replaced_by_a_real_directory(self) -> None:
        self.require_symlinks()
        (self.claude).mkdir(parents=True)
        os.symlink(self.repo / "rules", self.claude / "rules", target_is_directory=True)
        self.assertTrue((self.claude / "rules").is_symlink())

        self.run_sync(apply=True)

        self.assertFalse((self.claude / "rules").is_symlink())
        self.assertTrue((self.claude / "rules").is_dir())
        self.assertEqual(
            (self.claude / "rules" / "00-environment.md").read_text(encoding="utf-8"), "# env\n"
        )

    def test_repo_file_symlink_is_replaced_and_backed_up(self) -> None:
        self.require_symlinks()
        (self.claude).mkdir(parents=True)
        os.symlink(self.repo / "CLAUDE.md", self.claude / "CLAUDE.md")

        self.run_sync(apply=True)

        self.assertFalse((self.claude / "CLAUDE.md").is_symlink())
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# CLAUDE\n")
        backups = list(self.claude.parent.glob(".claude.backup-*"))
        self.assertEqual(len(backups), 1)

    def test_foreign_symlink_is_refused(self) -> None:
        self.require_symlinks()
        elsewhere = self.root / "elsewhere.md"
        elsewhere.write_text("not ours\n", encoding="utf-8")
        (self.claude).mkdir(parents=True)
        os.symlink(elsewhere, self.claude / "CLAUDE.md")

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("foreign symlink", str(caught.exception))
        # Nothing was touched.
        self.assertTrue((self.claude / "CLAUDE.md").is_symlink())

    def test_differing_regular_file_requires_update(self) -> None:
        self.run_sync(apply=True)
        (self.claude / "CLAUDE.md").write_text("# edited by hand\n", encoding="utf-8")

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("--apply --update", str(caught.exception))
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# edited by hand\n")

        self.run_sync(apply=True, update=True)
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# CLAUDE\n")

    def test_prune_removes_stale_repo_links_only(self) -> None:
        self.require_symlinks()
        agents_dir = self.claude / "agents"
        agents_dir.mkdir(parents=True)
        # A link this repo's installer created, for a role since sunset.
        os.symlink(self.repo / "agents" / "retired.md", agents_dir / "retired.md")
        # Someone else's link, and a real file of the user's own.
        outside = self.root / "outside.md"
        outside.write_text("theirs\n", encoding="utf-8")
        os.symlink(outside, agents_dir / "theirs.md")
        (agents_dir / "mine.md").write_text("mine\n", encoding="utf-8")

        self.run_sync(apply=True, prune=True)

        self.assertFalse((agents_dir / "retired.md").is_symlink())
        self.assertFalse((agents_dir / "retired.md").exists())
        self.assertTrue((agents_dir / "theirs.md").is_symlink())
        self.assertEqual((agents_dir / "mine.md").read_text(encoding="utf-8"), "mine\n")

    def test_without_prune_stale_links_are_left_alone(self) -> None:
        self.require_symlinks()
        agents_dir = self.claude / "agents"
        agents_dir.mkdir(parents=True)
        os.symlink(self.repo / "agents" / "retired.md", agents_dir / "retired.md")

        self.run_sync(apply=True)

        self.assertTrue((agents_dir / "retired.md").is_symlink())

    def test_missing_source_is_refused_before_writing(self) -> None:
        (self.repo / "rules" / "00-environment.md").unlink()
        (self.repo / "rules" / "05-hosts.md").unlink()

        with self.assertRaises(sync_profile.SyncError):
            self.run_sync(apply=True)
        self.assertFalse(self.claude.exists())


if __name__ == "__main__":
    unittest.main()
