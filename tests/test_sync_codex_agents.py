"""Tests for the physical Codex agent TOML synchronizer."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync-codex-agents.py"
SPEC = importlib.util.spec_from_file_location("sync_codex_agents", SCRIPT_PATH)
assert SPEC and SPEC.loader
sync_codex_agents = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync_codex_agents
SPEC.loader.exec_module(sync_codex_agents)


def write_role(directory: Path, name: str, *, description: str = "role") -> Path:
    path = directory / f"{name}.toml"
    path.write_text(
        f'name = "{name}"\n'
        f'description = "{description}"\n'
        'developer_instructions = "Do the task"\n'
        'model = "gpt-5.6-luna"\n',
        encoding="utf-8",
    )
    return path


class SyncTests(unittest.TestCase):
    def make_dirs(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        return temporary, root / "source", root / "profile" / "agents"

    def test_first_install_uses_regular_files_and_leaves_unrelated_names(self) -> None:
        temporary, source, destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            write_role(source, "worker")
            destination.mkdir(parents=True)
            unrelated = destination / "unrelated.toml"
            unrelated.write_bytes(b"keep me")

            operations = sync_codex_agents.sync(source, destination, apply=True)

            installed = destination / "worker.toml"
            self.assertTrue(installed.is_file())
            self.assertFalse(installed.is_symlink())
            self.assertEqual(installed.read_bytes(), (source / "worker.toml").read_bytes())
            self.assertEqual(unrelated.read_bytes(), b"keep me")
            self.assertEqual([operation.action for operation in operations], ["install"])

    def test_idempotence_identical_regular_file_is_noop(self) -> None:
        temporary, source, destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            source_file = write_role(source, "worker")
            destination.mkdir(parents=True)
            installed = destination / "worker.toml"
            installed.write_bytes(source_file.read_bytes())
            before = installed.stat().st_mtime_ns

            operations = sync_codex_agents.sync(source, destination, apply=True)

            self.assertEqual([operation.action for operation in operations], ["unchanged"])
            self.assertEqual(installed.read_bytes(), source_file.read_bytes())
            self.assertEqual(installed.stat().st_mtime_ns, before)

    def test_same_content_symlink_is_migrated_and_backed_up_as_symlink(self) -> None:
        temporary, source, destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            source_file = write_role(source, "worker")
            destination.mkdir(parents=True)
            installed = destination / "worker.toml"
            installed.symlink_to(source_file)

            operations = sync_codex_agents.sync(source, destination, apply=True)

            self.assertEqual([operation.action for operation in operations], ["migrate-symlink"])
            self.assertTrue(installed.is_file())
            self.assertFalse(installed.is_symlink())
            self.assertEqual(installed.read_bytes(), source_file.read_bytes())
            backups = list(destination.parent.glob("agents.backup-*/worker.toml"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())
            self.assertEqual(backups[0].resolve(), source_file.resolve())

    def test_differing_regular_requires_update_then_is_backed_up(self) -> None:
        temporary, source, destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            source_file = write_role(source, "worker", description="new")
            destination.mkdir(parents=True)
            installed = destination / "worker.toml"
            old = b'name = "worker"\ndescription = "old"\ndeveloper_instructions = "old"\n'
            installed.write_bytes(old)

            with self.assertRaises(sync_codex_agents.SyncError) as raised:
                sync_codex_agents.sync(source, destination, apply=True)
            self.assertIn("--apply --update", str(raised.exception))
            self.assertEqual(installed.read_bytes(), old)

            operations = sync_codex_agents.sync(source, destination, apply=True, update=True)

            self.assertEqual([operation.action for operation in operations], ["update"])
            self.assertEqual(installed.read_bytes(), source_file.read_bytes())
            backups = list(destination.parent.glob("agents.backup-*/worker.toml"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), old)

    def test_foreign_symlink_fails_before_changes(self) -> None:
        temporary, source, destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            source_file = write_role(source, "worker")
            other = Path(temporary.name) / "foreign.toml"
            other.write_bytes(b"foreign")
            destination.mkdir(parents=True)
            installed = destination / "worker.toml"
            installed.symlink_to(other)

            with self.assertRaises(sync_codex_agents.SyncError) as raised:
                sync_codex_agents.sync(source, destination, apply=True)

            self.assertIn("foreign symlink", str(raised.exception))
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), other.resolve())
            self.assertEqual(source_file.read_bytes(), (source / "worker.toml").read_bytes())
            self.assertEqual(list(destination.parent.glob("agents.backup-*")), [])

    def test_invalid_source_preflight_preserves_destination(self) -> None:
        temporary, source, destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            write_role(source, "worker")
            (source / "verifier.toml").write_text(
                'name = "wrong"\ndescription = "x"\ndeveloper_instructions = "x"\n',
                encoding="utf-8",
            )
            destination.mkdir(parents=True)
            existing = destination / "existing.toml"
            existing.write_bytes(b"preserve")

            with self.assertRaises(sync_codex_agents.SyncError) as raised:
                sync_codex_agents.sync(source, destination, apply=True)

            self.assertIn("must equal filename stem", str(raised.exception))
            self.assertEqual(existing.read_bytes(), b"preserve")
            self.assertFalse((destination / "worker.toml").exists())

    def test_destination_inside_source_is_rejected(self) -> None:
        temporary, source, _destination = self.make_dirs()
        with temporary:
            source.mkdir(parents=True)
            write_role(source, "worker")
            with self.assertRaises(sync_codex_agents.SyncError):
                sync_codex_agents.sync(source, source / "installed", apply=True)
            self.assertFalse((source / "installed").exists())


if __name__ == "__main__":
    unittest.main()
