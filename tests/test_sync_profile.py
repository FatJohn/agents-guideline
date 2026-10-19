"""Tests for the physical profile synchronizer."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
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


SHARED_SKILLS = ("dispatch", "handoff", "git-commit", "create-pr", "parallel-dispatch", "writing-principles")


def build_repo(root: Path) -> Path:
    """A miniature repository with the same shape the mappings expect."""

    repo = root / "repo"
    claude = repo / "global" / "claude"
    shared = repo / "global" / "shared"
    for directory in (
        claude / "agents",
        claude / "hooks",
        claude / "config",
        repo / "global" / "codex",
        shared / "rules",
        shared / "rubrics",
        shared / "hosts",
    ):
        directory.mkdir(parents=True)
    for name in SHARED_SKILLS:
        (shared / "skills" / name).mkdir(parents=True)
        (shared / "skills" / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    # Repo-only skills: present in the repository, never installed.
    for name in ("maintain-guideline", "usage-review"):
        (repo / ".claude" / "skills" / name).mkdir(parents=True)
        (repo / ".claude" / "skills" / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")

    (repo / "CLAUDE.md").write_text("# repo CLAUDE\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# repo AGENTS\n", encoding="utf-8")
    (claude / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")
    (claude / "route-card.md").write_text("# route card\n", encoding="utf-8")
    (repo / "global" / "codex" / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (shared / "rules" / "judgment.md").write_text("# judgment\n", encoding="utf-8")
    (shared / "hosts" / "macos.md").write_text("# mac\n", encoding="utf-8")
    (shared / "hosts" / "windows.md").write_text("# win\n", encoding="utf-8")
    (shared / "rubrics" / "code-change.md").write_text("# code change\n", encoding="utf-8")
    (shared / "rubrics" / "document-quality.md").write_text("# document quality\n", encoding="utf-8")
    (claude / "agents" / "worker.md").write_text("# worker\n", encoding="utf-8")
    (claude / "agents" / "verifier.md").write_text("# verifier\n", encoding="utf-8")
    (claude / "hooks" / "block-ci-edit.sh").write_text("#!/bin/bash\n# hook\n", encoding="utf-8")
    (claude / "hooks" / "controller-context.sh").write_text("#!/bin/bash\n# context\n", encoding="utf-8")
    (claude / "config" / "ripgreprc").write_text("--hidden\n", encoding="utf-8")
    return repo


class SyncProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = build_repo(self.root)
        self.src_claude = self.repo / "global" / "claude"
        self.src_shared = self.repo / "global" / "shared"
        self.claude = self.root / "profile" / ".claude"
        self.codex = self.root / "profile" / ".codex"
        self.agents = self.root / "profile" / ".agents"

    def run_sync(self, **kwargs):
        # Pin the host key so the suite does not depend on the platform it runs on.
        kwargs.setdefault("host_key", "macos")
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

        installed = self.claude / "rules" / "judgment.md"
        self.assertTrue(installed.is_file())
        self.assertFalse(installed.is_symlink())
        self.assertEqual(installed.read_text(encoding="utf-8"), "# judgment\n")

        # The tree root must be a real directory, not a link.
        self.assertTrue((self.claude / "rules").is_dir())
        self.assertFalse((self.claude / "rules").is_symlink())

        # Both platforms get their own entry point (not the repo's project spec)
        # and the six shared skills.
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# CLAUDE\n")
        self.assertEqual((self.codex / "AGENTS.md").read_text(encoding="utf-8"), "# AGENTS\n")
        for name in SHARED_SKILLS:
            self.assertTrue((self.claude / "skills" / name / "SKILL.md").is_file())
            self.assertTrue((self.agents / "skills" / name / "SKILL.md").is_file())
        # The repo-only skills (.claude/skills) and the retired session-handoff
        # never reach either profile.
        for name in ("maintain-guideline", "usage-review", "session-handoff"):
            self.assertFalse((self.claude / "skills" / name).exists())
            self.assertFalse((self.agents / "skills" / name).exists())

        # worker.md is the entry docs/install.md's symlink install has been missing.
        self.assertEqual((self.claude / "agents" / "worker.md").read_text(encoding="utf-8"), "# worker\n")
        self.assertEqual((self.claude / "agents" / "verifier.md").read_text(encoding="utf-8"), "# verifier\n")
        self.assertEqual(
            (self.claude / "rubrics" / "code-change.md").read_text(encoding="utf-8"), "# code change\n"
        )

    def test_route_card_is_installed_as_a_single_file(self) -> None:
        self.run_sync(apply=True)

        card = self.claude / "route-card.md"
        self.assertTrue(card.is_file())
        self.assertFalse(card.is_symlink())
        self.assertEqual(card.read_text(encoding="utf-8"), "# route card\n")

        # The card is injected by the SessionStart hook, so it must stay out of
        # ~/.claude/rules (which every session, subagents included, loads), and the
        # v1 rules-controller directory must not come back.
        self.assertFalse((self.claude / "rules" / "route-card.md").exists())
        self.assertFalse((self.claude / "rules-controller").exists())
        self.assertEqual(sorted(path.name for path in (self.claude / "rules").iterdir()), ["judgment.md"])

    def test_hook_and_ripgreprc_are_installed_as_regular_files(self) -> None:
        self.run_sync(apply=True)

        hook = self.claude / "hooks" / "block-ci-edit.sh"
        self.assertTrue(hook.is_file())
        self.assertFalse(hook.is_symlink())
        self.assertEqual(hook.read_text(encoding="utf-8"), "#!/bin/bash\n# hook\n")
        self.assertFalse((self.claude / "hooks").is_symlink())

        ripgreprc = self.claude / "ripgreprc"
        self.assertTrue(ripgreprc.is_file())
        self.assertFalse(ripgreprc.is_symlink())
        self.assertEqual(ripgreprc.read_text(encoding="utf-8"), "--hidden\n")

    def test_missing_hook_source_is_refused_before_writing(self) -> None:
        shutil.rmtree(self.src_claude / "hooks")

        with self.assertRaises(sync_profile.SyncError):
            self.run_sync(apply=True)
        self.assertFalse(self.claude.exists())

    def test_missing_route_card_source_is_refused_before_writing(self) -> None:
        (self.src_claude / "route-card.md").unlink()

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("route-card.md", str(caught.exception))
        self.assertFalse(self.claude.exists())

    def test_host_facts_installs_only_this_machines_file(self) -> None:
        self.run_sync(apply=True, host_key="windows")

        facts = self.claude / "host-facts.md"
        self.assertTrue(facts.is_file())
        self.assertEqual(facts.read_text(encoding="utf-8"), "# win\n")
        # The other machine's file must not reach the profile in any shape.
        self.assertFalse((self.claude / "hosts").exists())
        self.assertFalse((self.claude / "rules" / "hosts").exists())
        self.assertNotIn("# mac", facts.read_text(encoding="utf-8"))

    def test_unknown_host_key_is_refused_before_writing(self) -> None:
        # "amiga" is a well-formed key; it is refused because
        # global/shared/hosts/amiga.md does not exist, which must read as a different error than a
        # malformed key (see test_invalid_host_key_format_is_refused...).
        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True, host_key="amiga")
        self.assertIn("missing", str(caught.exception))
        self.assertIn("global/shared/hosts/amiga.md", str(caught.exception))
        self.assertFalse(self.claude.exists())

    def test_invalid_host_key_format_is_refused_before_writing(self) -> None:
        invalid_keys = ["../CLAUDE", "../../x", "/etc/passwd", "a/b", "", "Macos"]
        for key in invalid_keys:
            with self.subTest(host_key=key):
                with self.assertRaises(sync_profile.SyncError) as caught:
                    self.run_sync(apply=True, host_key=key)
                self.assertIn("invalid --host-key", str(caught.exception))
                self.assertFalse(self.claude.exists())
                self.assertFalse(self.codex.exists())
                self.assertFalse(self.agents.exists())

    def test_custom_host_key_can_install(self) -> None:
        (self.src_shared / "hosts" / "linuxbox.md").write_text("# linux\n", encoding="utf-8")

        self.run_sync(apply=True, host_key="linuxbox")

        facts = self.claude / "host-facts.md"
        self.assertEqual(facts.read_text(encoding="utf-8"), "# linux\n")

    def test_detect_host_key_follows_platform(self) -> None:
        import platform

        system = platform.system()
        if system in sync_profile.HOST_KEYS:
            self.assertEqual(sync_profile.detect_host_key(), sync_profile.HOST_KEYS[system])
        else:
            with self.assertRaises(sync_profile.SyncError):
                sync_profile.detect_host_key()

    def test_rerun_reports_everything_unchanged(self) -> None:
        self.run_sync(apply=True)
        operations = self.run_sync(apply=True)

        self.assertTrue(operations)
        self.assertTrue(all(operation.action == "unchanged" for operation in operations))

    def test_directory_symlink_root_is_replaced_by_a_real_directory(self) -> None:
        self.require_symlinks()
        (self.claude).mkdir(parents=True)
        os.symlink(self.src_shared / "rules", self.claude / "rules", target_is_directory=True)
        self.assertTrue((self.claude / "rules").is_symlink())

        self.run_sync(apply=True, replace_symlinks=True)

        self.assertFalse((self.claude / "rules").is_symlink())
        self.assertTrue((self.claude / "rules").is_dir())
        self.assertEqual(
            (self.claude / "rules" / "judgment.md").read_text(encoding="utf-8"), "# judgment\n"
        )

    def test_owned_tree_link_migrates_every_child_without_following_old_root(self) -> None:
        self.require_symlinks()
        (self.claude).mkdir(parents=True)
        os.symlink(self.src_shared / "rubrics", self.claude / "rubrics", target_is_directory=True)

        operations = self.run_sync(apply=True, replace_symlinks=True)

        self.assertEqual(
            [operation.action for operation in operations if operation.destination.parent == self.claude / "rubrics"],
            ["install", "install"],
        )
        self.assertFalse((self.claude / "rubrics").is_symlink())
        self.assertEqual(
            (self.claude / "rubrics" / "document-quality.md").read_text(encoding="utf-8"),
            "# document quality\n",
        )

    def test_foreign_tree_redirect_is_refused_before_any_write(self) -> None:
        self.require_symlinks()
        elsewhere = self.root / "elsewhere-rules"
        elsewhere.mkdir()
        (elsewhere / "keep.md").write_text("keep\n", encoding="utf-8")
        self.claude.mkdir(parents=True)
        os.symlink(elsewhere, self.claude / "rules", target_is_directory=True)

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("foreign tree redirect", str(caught.exception))
        self.assertTrue((self.claude / "rules").is_symlink())
        self.assertFalse((self.claude / "CLAUDE.md").exists())
        self.assertEqual((elsewhere / "keep.md").read_text(encoding="utf-8"), "keep\n")

    def test_foreign_ancestor_redirect_is_refused_before_any_write(self) -> None:
        self.require_symlinks()
        elsewhere = self.root / "elsewhere-skills"
        elsewhere.mkdir()
        self.claude.mkdir(parents=True)
        os.symlink(elsewhere, self.claude / "skills", target_is_directory=True)

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("destination ancestor is a redirect", str(caught.exception))
        self.assertTrue((self.claude / "skills").is_symlink())
        self.assertFalse((elsewhere / "dispatch" / "SKILL.md").exists())

    def test_nested_tree_redirect_is_refused_before_any_write(self) -> None:
        self.require_symlinks()
        source = self.src_shared / "skills" / "create-pr" / "references"
        source.mkdir()
        (source / "guide.md").write_text("guide\n", encoding="utf-8")
        destination = self.claude / "skills" / "create-pr" / "references"
        destination.parent.mkdir(parents=True)
        elsewhere = self.root / "elsewhere-references"
        elsewhere.mkdir()
        os.symlink(elsewhere, destination, target_is_directory=True)

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("destination ancestor is a redirect", str(caught.exception))
        self.assertTrue(destination.is_symlink())
        self.assertFalse((elsewhere / "guide.md").exists())

    def test_repo_file_symlink_is_replaced_and_backed_up(self) -> None:
        self.require_symlinks()
        (self.claude).mkdir(parents=True)
        os.symlink(self.src_claude / "CLAUDE.md", self.claude / "CLAUDE.md")

        self.run_sync(apply=True, replace_symlinks=True)

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

    def test_foreign_source_alias_is_not_accepted_as_owned(self) -> None:
        self.require_symlinks()
        outside = self.root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        alias = self.root / "outside-alias.md"
        os.symlink(outside, alias)
        self.claude.mkdir(parents=True)
        os.symlink(alias, self.claude / "CLAUDE.md")

        with self.assertRaises(sync_profile.SyncError):
            self.run_sync(apply=True)
        self.assertTrue((self.claude / "CLAUDE.md").is_symlink())

    def test_mac_var_alias_accepts_the_exact_repo_source(self) -> None:
        self.require_symlinks()
        self.claude.mkdir(parents=True)
        # ``resolve`` is /private/var on macOS while this stored target retains
        # the /var spelling used by temporary test paths.
        os.symlink(self.src_claude / "CLAUDE.md", self.claude / "CLAUDE.md")

        self.run_sync(apply=True, replace_symlinks=True)

        self.assertFalse((self.claude / "CLAUDE.md").is_symlink())

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
        os.symlink(self.src_claude / "agents" / "retired.md", agents_dir / "retired.md")
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
        os.symlink(self.src_claude / "agents" / "retired.md", agents_dir / "retired.md")

        self.run_sync(apply=True)

        self.assertTrue((agents_dir / "retired.md").is_symlink())

    def test_missing_source_is_refused_before_writing(self) -> None:
        (self.src_shared / "rules" / "judgment.md").unlink()

        with self.assertRaises(sync_profile.SyncError):
            self.run_sync(apply=True)
        self.assertFalse(self.claude.exists())

    def _mixed_transaction_fixture(self) -> Path:
        self.require_symlinks()
        self.run_sync(apply=True)
        (self.claude / "CLAUDE.md").write_text("# personal\n", encoding="utf-8")
        rules = self.claude / "rules"
        for child in rules.iterdir():
            child.unlink()
        rules.rmdir()
        os.symlink(self.src_shared / "rules", rules, target_is_directory=True)
        retired = self.claude / "agents" / "retired.md"
        os.symlink(self.src_claude / "agents" / "retired.md", retired)
        return retired

    def _assert_mixed_transaction_restored(self, retired: Path) -> None:
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# personal\n")
        self.assertTrue((self.claude / "rules").is_symlink())
        self.assertEqual(os.readlink(self.claude / "rules"), str(self.src_shared / "rules"))
        self.assertTrue(retired.is_symlink())
        # No stray staging file from an interrupted write is left behind.
        self.assertEqual(list(self.claude.rglob(".*.tmp")), [])
        # A successful rollback must not leave an empty backup directory (F4).
        self.assertEqual(list(self.claude.parent.glob(f"{self.claude.name}.backup-*")), [])

    def test_rollback_restores_mixed_changes_after_later_write_failure(self) -> None:
        retired = self._mixed_transaction_fixture()
        original = sync_profile._replace_with_bytes
        calls = 0

        def fail_later(destination, content, created_directories):
            nonlocal calls
            calls += 1
            # Write 1 is the CLAUDE.md update, write 2 is rules/judgment.md.
            if calls == 2:
                raise OSError("injected write failure")
            return original(destination, content, created_directories)

        sync_profile._replace_with_bytes = fail_later
        try:
            with self.assertRaises(OSError):
                self.run_sync(apply=True, update=True, prune=True, replace_symlinks=True)
        finally:
            sync_profile._replace_with_bytes = original
        self._assert_mixed_transaction_restored(retired)

    def test_rollback_restores_mixed_changes_after_move_failure(self) -> None:
        retired = self._mixed_transaction_fixture()
        original = sync_profile._move_aside
        calls = 0

        def fail_second_move(path, backup_root, label):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected move failure")
            return original(path, backup_root, label)

        sync_profile._move_aside = fail_second_move
        try:
            with self.assertRaises(OSError):
                self.run_sync(apply=True, update=True, prune=True, replace_symlinks=True)
        finally:
            sync_profile._move_aside = original
        self._assert_mixed_transaction_restored(retired)

    def test_rollback_restores_mixed_changes_after_readback_failure(self) -> None:
        retired = self._mixed_transaction_fixture()
        original = sync_profile.verify
        sync_profile.verify = lambda operations: ["injected read-back failure"]
        try:
            with self.assertRaises(sync_profile.SyncError):
                self.run_sync(apply=True, update=True, prune=True, replace_symlinks=True)
        finally:
            sync_profile.verify = original
        self._assert_mixed_transaction_restored(retired)

    def test_rollback_failure_preserves_original_error(self) -> None:
        retired = self._mixed_transaction_fixture()

        original_replace = sync_profile._replace_with_bytes
        calls = 0

        def fail_and_occupy(destination, content, created_directories):
            nonlocal calls
            calls += 1
            if calls == 2:
                # Simulate something else occupying a path rollback will try
                # to restore, so rollback itself fails and the original
                # failure must not be lost behind "rollback failed".
                retired.write_text("occupied again\n", encoding="utf-8")
                raise OSError("injected write failure for rollback test")
            return original_replace(destination, content, created_directories)

        original_make_backup_root = sync_profile._make_backup_root
        backup_roots: list[Path] = []

        def capture_backup_root(anchor):
            root = original_make_backup_root(anchor)
            backup_roots.append(root)
            return root

        original_sync = sync_profile.sync

        def sync_with_test_repo(**kwargs):
            kwargs.setdefault("repo", self.repo)
            return original_sync(**kwargs)

        sync_profile._replace_with_bytes = fail_and_occupy
        sync_profile._make_backup_root = capture_backup_root
        sync_profile.sync = sync_with_test_repo
        argv = [
            "--claude-home", str(self.claude),
            "--codex-home", str(self.codex),
            "--agents-home", str(self.agents),
            "--host-key", "macos",
            "--apply", "--update", "--prune", "--replace-symlinks",
        ]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                code = sync_profile.main(argv)
        finally:
            sync_profile._replace_with_bytes = original_replace
            sync_profile._make_backup_root = original_make_backup_root
            sync_profile.sync = original_sync

        output = stderr.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("injected write failure for rollback test", output)
        self.assertIn("rollback failed", output)
        self.assertEqual(len(backup_roots), 1)
        self.assertIn(str(backup_roots[0]), output)

    def test_symlink_migration_without_flag_is_refused_before_any_write(self) -> None:
        self.require_symlinks()
        self.claude.mkdir(parents=True)
        os.symlink(self.src_claude / "CLAUDE.md", self.claude / "CLAUDE.md")

        with self.assertRaises(sync_profile.SyncError) as caught:
            self.run_sync(apply=True)
        self.assertIn("--replace-symlinks", str(caught.exception))
        self.assertTrue((self.claude / "CLAUDE.md").is_symlink())
        self.assertEqual(list(self.claude.parent.glob(f"{self.claude.name}.backup-*")), [])

    def test_symlink_migration_with_flag_matches_existing_behavior(self) -> None:
        self.require_symlinks()
        self.claude.mkdir(parents=True)
        os.symlink(self.src_claude / "CLAUDE.md", self.claude / "CLAUDE.md")

        self.run_sync(apply=True, replace_symlinks=True)

        self.assertFalse((self.claude / "CLAUDE.md").is_symlink())
        self.assertEqual((self.claude / "CLAUDE.md").read_text(encoding="utf-8"), "# CLAUDE\n")

    def test_dry_run_hints_replace_symlinks_when_migration_pending(self) -> None:
        self.require_symlinks()
        self.claude.mkdir(parents=True)
        os.symlink(self.src_claude / "CLAUDE.md", self.claude / "CLAUDE.md")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.run_sync()
        self.assertIn("--replace-symlinks", stdout.getvalue())

    def test_first_install_leaves_no_backup_directory(self) -> None:
        self.run_sync(apply=True)

        self.assertEqual(list(self.claude.parent.glob(f"{self.claude.name}.backup-*")), [])

    def test_update_backup_directory_retains_replaced_file(self) -> None:
        self.run_sync(apply=True)
        (self.claude / "CLAUDE.md").write_text("# edited by hand\n", encoding="utf-8")

        self.run_sync(apply=True, update=True)

        backups = list(self.claude.parent.glob(f"{self.claude.name}.backup-*"))
        self.assertEqual(len(backups), 1)
        backed_up_files = list(backups[0].iterdir())
        self.assertEqual(len(backed_up_files), 1)
        self.assertEqual(backed_up_files[0].read_text(encoding="utf-8"), "# edited by hand\n")

    def test_apply_prints_plan_before_writing_when_apply_fails(self) -> None:
        self.run_sync(apply=True)
        (self.claude / "CLAUDE.md").write_text("# edited by hand\n", encoding="utf-8")

        original = sync_profile._replace_with_bytes

        def fail_first(destination, content, created_directories):
            raise OSError("injected write failure")

        sync_profile._replace_with_bytes = fail_first
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                with self.assertRaises(OSError):
                    self.run_sync(apply=True, update=True)
        finally:
            sync_profile._replace_with_bytes = original

        output = stdout.getvalue()
        self.assertIn("mode: apply", output)
        self.assertIn(f"update regular file: {self.claude / 'CLAUDE.md'}", output)


    def run_sync_output(self, **kwargs) -> str:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.run_sync(**kwargs)
        return stdout.getvalue()

    def make_v1_leftovers(self) -> list[Path]:
        """What a v1 install left in the profile; returns the entries to be listed."""

        listed = [
            self.claude / "rules-controller",
            self.claude / "rules" / "00-environment.md",
            self.claude / "rules" / "05-hosts.md",
            self.claude / "rules" / "20-judgment.md",
            self.claude / "rules" / "50-lessons.md",
            self.claude / "skills" / "maintain-guideline",
            self.claude / "skills" / "usage-review",
            self.claude / "agents" / "worker-opus.md",
            self.agents / "skills" / "maintain-guideline",
            self.agents / "skills" / "session-handoff",
        ]
        for path in listed:
            if path.name.endswith(".md"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# v1\n", encoding="utf-8")
            else:
                path.mkdir(parents=True)
                (path / "SKILL.md").write_text("# v1\n", encoding="utf-8")
        return listed

    def test_dry_run_lists_v1_leftovers_and_removes_nothing(self) -> None:
        listed = self.make_v1_leftovers()

        output = self.run_sync_output()

        for path in listed:
            self.assertIn(f"legacy: {path}", output)
            self.assertTrue(path.exists())

    def test_apply_lists_v1_leftovers_and_removes_nothing(self) -> None:
        listed = self.make_v1_leftovers()

        output = self.run_sync_output(apply=True)

        for path in listed:
            self.assertIn(f"legacy: {path}", output)
            self.assertTrue(path.exists())
        # The new rules file is installed next to the stale one; the script does not choose between them.
        self.assertTrue((self.claude / "rules" / "judgment.md").is_file())
        self.assertTrue((self.claude / "rules" / "20-judgment.md").is_file())

    def test_clean_profile_prints_no_legacy_notice(self) -> None:
        self.assertNotIn("legacy", self.run_sync_output())
        self.assertNotIn("legacy", self.run_sync_output(apply=True))
        self.assertNotIn("legacy", self.run_sync_output(apply=True))

    def test_prune_removes_a_v1_link_and_does_not_list_it_twice(self) -> None:
        self.require_symlinks()
        self.claude.mkdir(parents=True)
        stale = self.claude / "rules-controller"
        os.symlink(self.repo / "rules-controller", stale, target_is_directory=True)

        preview = self.run_sync_output(prune=True)
        self.assertIn(f"remove stale link into this repo: {stale}", preview)
        self.assertNotIn(f"legacy: {stale}", preview)
        self.assertTrue(stale.is_symlink())

        applied = self.run_sync_output(apply=True, prune=True)
        self.assertFalse(stale.is_symlink())
        self.assertNotIn("legacy", applied)


if __name__ == "__main__":
    unittest.main()
