#!/usr/bin/env python3
"""Synchronize repository Codex agent TOML files into a profile directory.

The repository files are the source of truth.  The destination contains
regular files so a Codex surface that does not load symlinked agent files can
still discover the same bytes.  The command previews by default and only
writes with ``--apply``.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / "codex" / "agents"
DEFAULT_DESTINATION = Path.home() / ".codex" / "agents"


class SyncError(ValueError):
    """A safe, user-actionable synchronization error."""


@dataclass(frozen=True)
class SourceRole:
    name: str
    source: Path
    content: bytes


@dataclass(frozen=True)
class Operation:
    role: SourceRole
    destination: Path
    action: str


def _path_text(path: Path) -> str:
    return str(path)


def load_roles(source: Path) -> list[SourceRole]:
    """Parse and validate every source TOML before touching the destination."""

    source = source.expanduser()
    if not source.exists():
        raise SyncError(f"source directory does not exist: {source}")
    if not source.is_dir():
        raise SyncError(f"source path is not a directory: {source}")

    files = sorted(source.glob("*.toml"))
    if not files:
        raise SyncError(f"no agent TOML files found in {source}")

    roles: list[SourceRole] = []
    for path in files:
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise SyncError(f"cannot read source TOML {_path_text(path)}: {exc}") from exc

        try:
            data = tomllib.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise SyncError(f"invalid source TOML {_path_text(path)}: {exc}") from exc

        missing = [
            field
            for field in ("name", "description", "developer_instructions")
            if not isinstance(data.get(field), str) or not data[field].strip()
        ]
        if missing:
            fields = ", ".join(missing)
            raise SyncError(f"{path}: missing required field(s): {fields}")

        name = data["name"]
        if name != path.stem:
            raise SyncError(
                f"{path}: name {name!r} must equal filename stem {path.stem!r}"
            )

        roles.append(SourceRole(name=name, source=path, content=content))

    return roles


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def validate_destination_root(source: Path, destination: Path) -> Path:
    """Validate the root without creating it or following it for writes."""

    source_resolved = _resolved(source)
    destination_resolved = _resolved(destination)
    if (
        destination_resolved == source_resolved
        or destination_resolved.is_relative_to(source_resolved)
        or source_resolved.is_relative_to(destination_resolved)
    ):
        raise SyncError(
            "destination must be outside the source directory and its ancestors: "
            f"source={source_resolved}, destination={destination_resolved}"
        )

    if destination.is_symlink():
        raise SyncError(f"destination directory must not be a symlink: {destination}")
    if destination.exists() and not destination.is_dir():
        raise SyncError(f"destination path is not a directory: {destination}")

    return destination


def _entry_kind(path: Path) -> str:
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISREG(mode):
        return "regular file"
    if stat.S_ISDIR(mode):
        return "directory"
    return "special file"


def plan_operations(
    roles: list[SourceRole],
    source: Path,
    destination: Path,
    *,
    apply: bool,
    update: bool,
) -> list[Operation]:
    """Inspect every destination entry before any operation can mutate it."""

    validate_destination_root(source, destination)
    operations: list[Operation] = []

    for role in roles:
        target = destination / f"{role.name}.toml"
        if not target.exists() and not target.is_symlink():
            operations.append(Operation(role, target, "install"))
            continue

        kind = _entry_kind(target)
        if kind == "symlink":
            try:
                target_source = target.resolve(strict=True)
            except OSError as exc:
                raise SyncError(f"cannot resolve destination symlink {target}: {exc}") from exc
            if target_source != role.source.resolve(strict=True):
                raise SyncError(
                    f"foreign symlink at {target} resolves to {target_source}; "
                    f"expected {_path_text(role.source.resolve(strict=True))}"
                )
            operations.append(Operation(role, target, "migrate-symlink"))
            continue

        if kind == "directory":
            raise SyncError(f"destination entry is a directory: {target}")
        if kind != "regular file":
            raise SyncError(f"unsupported destination entry at {target}: {kind}")

        try:
            existing = target.read_bytes()
        except OSError as exc:
            raise SyncError(f"cannot read destination file {target}: {exc}") from exc
        if existing == role.content:
            operations.append(Operation(role, target, "unchanged"))
        elif not apply or not update:
            operations.append(Operation(role, target, "update-required"))
        else:
            operations.append(Operation(role, target, "update"))

    blocked = [operation for operation in operations if operation.action == "update-required"]
    if blocked and apply:
        paths = ", ".join(_path_text(operation.destination) for operation in blocked)
        raise SyncError(
            f"differing regular file(s) require --apply --update: {paths}"
        )

    return operations


def _make_backup_root(destination: Path) -> Path:
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{destination.name}.backup-", dir=parent))


def _move_to_backup(operation: Operation, backup_root: Path) -> Path:
    backup = backup_root / operation.destination.name
    # Rename on the same volume preserves a symlink as a symlink and does not
    # require permission to create a new symlink (important on Windows).
    os.replace(operation.destination, backup)
    return backup


def _replace_with_bytes(destination: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def apply_operations(operations: list[Operation], destination: Path) -> tuple[Path | None, dict[str, Path]]:
    """Apply staged regular-file replacements and return backup evidence."""

    changes = [operation for operation in operations if operation.action in {"install", "migrate-symlink", "update"}]
    if not changes:
        return None, {}

    destination.mkdir(parents=True, exist_ok=True)
    backup_root: Path | None = None
    backups: dict[str, Path] = {}

    # Move all existing entries before replacing any destination path.  A
    # symlink is moved as a symlink, so backup never follows it.
    existing_changes = [operation for operation in changes if operation.destination.is_symlink() or operation.destination.exists()]
    if existing_changes:
        backup_root = _make_backup_root(destination)
        moved: list[Operation] = []
        try:
            for operation in existing_changes:
                backups[operation.role.name] = _move_to_backup(operation, backup_root)
                moved.append(operation)
        except OSError:
            for operation in reversed(moved):
                backup = backups[operation.role.name]
                if backup.exists() or backup.is_symlink():
                    os.replace(backup, operation.destination)
            raise

    try:
        for operation in changes:
            _replace_with_bytes(operation.destination, operation.role.content)
    except OSError:
        # Restore every original entry and remove files installed earlier in
        # this run if a later atomic replacement fails.
        for operation in reversed(changes):
            backup = backups.get(operation.role.name)
            if backup is not None:
                if operation.destination.exists() or operation.destination.is_symlink():
                    operation.destination.unlink()
                if backup.exists() or backup.is_symlink():
                    os.replace(backup, operation.destination)
            elif operation.destination.exists() or operation.destination.is_symlink():
                operation.destination.unlink()
        if backup_root is not None:
            try:
                backup_root.rmdir()
            except OSError:
                pass
        raise

    return backup_root, backups


def _counts(operations: list[Operation]) -> dict[str, int]:
    labels = {"install": "install", "migrate-symlink": "migrate", "update": "update", "unchanged": "unchanged", "update-required": "update-required"}
    counts = {label: 0 for label in labels.values()}
    for operation in operations:
        counts[labels[operation.action]] += 1
    return counts


def print_preview(operations: list[Operation], destination: Path, *, apply: bool) -> None:
    mode = "apply" if apply else "dry-run"
    print(f"mode: {mode}")
    print(f"destination: {destination}")
    for operation in operations:
        if operation.action == "install":
            verb = "install"
        elif operation.action == "migrate-symlink":
            verb = "migrate symlink to regular file"
        elif operation.action == "update":
            verb = "update regular file"
        elif operation.action == "update-required":
            verb = "would update (requires --apply --update)"
        else:
            verb = "unchanged"
        print(f"{verb}: {operation.destination}")

    counts = _counts(operations)
    print(
        "summary: "
        f"install={counts['install']} "
        f"migrate={counts['migrate']} "
        f"update={counts['update']} "
        f"unchanged={counts['unchanged']} "
        f"update-required={counts['update-required']}"
    )


def sync(source: Path, destination: Path, *, apply: bool = False, update: bool = False) -> list[Operation]:
    """Validate, preview, or apply a synchronization plan."""

    source = source.expanduser()
    destination = destination.expanduser()
    roles = load_roles(source)
    operations = plan_operations(roles, source, destination, apply=apply, update=update)
    if not apply:
        print_preview(operations, destination, apply=False)
        return operations

    backup_root, backups = apply_operations(operations, destination)
    print_preview(operations, destination, apply=True)
    for name, backup in backups.items():
        print(f"backup {name}: {backup}")
    if backup_root is not None:
        print(f"backup directory: {backup_root}")
    return operations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or install codex/agents/*.toml as regular files."
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
        help=f"profile agent directory (default: {DEFAULT_DESTINATION})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the validated plan; without this flag the command is dry-run",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="allow --apply to replace differing regular files after backing them up",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.update and not args.apply:
        parser.error("--update requires --apply")
    try:
        sync(DEFAULT_SOURCE, args.destination, apply=args.apply, update=args.update)
    except (OSError, SyncError) as exc:
        print(f"sync-codex-agents: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
