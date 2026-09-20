#!/usr/bin/env python3
"""Synchronize this repository into ~/.claude, ~/.codex and ~/.agents as regular files.

The repository is the source of truth.  ``README.md`` installs the same set as
symlinks, which is the preferred layout because a repo edit takes effect with no
further step.  This script exists for hosts where a symlinked profile silently
fails to load: ``hosts/windows.md`` records ``FatJohn-PC``, where opening any
path behind a reparse point returns ``ERROR_UNTRUSTED_MOUNT_POINT`` (os error
448) while ``LinkType``/``Target`` still read back green.

Because a symlinked entry can look installed and still be unreadable, ``--apply``
finishes by opening every destination file and comparing bytes.  A link-shaped
read-back is not evidence here.

The command previews by default and only writes with ``--apply``.
"""

from __future__ import annotations

import argparse
import os
import platform
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class SyncError(ValueError):
    """A safe, user-actionable synchronization error."""


# ``platform.system()`` -> the ``hosts/<key>.md`` that machine class installs as
# ``~/.claude/host-facts.md``.  Only the current machine's file is installed;
# the global CLAUDE.md imports it with ``@~/.claude/host-facts.md``.
HOST_KEYS = {"Darwin": "macos", "Windows": "windows"}


def detect_host_key() -> str:
    """Pick ``hosts/<key>.md`` for this platform, or explain what to pass."""

    system = platform.system()
    try:
        return HOST_KEYS[system]
    except KeyError:
        raise SyncError(
            f"no hosts/<key>.md mapping for platform {system!r}; pass --host-key "
            f"(known: {', '.join(sorted(HOST_KEYS.values()))})"
        ) from None


@dataclass(frozen=True)
class Mapping:
    """One repository path installed at one profile path."""

    source: Path
    destination: Path
    kind: str  # "file" or "tree"


@dataclass(frozen=True)
class SourceFile:
    source: Path
    destination: Path
    content: bytes


@dataclass(frozen=True)
class Operation:
    destination: Path
    action: str
    source: Path | None = None
    content: bytes | None = None


def default_mappings(
    *,
    repo: Path,
    claude_home: Path,
    codex_home: Path,
    agents_home: Path,
    host_key: str,
) -> list[Mapping]:
    """The same set README.md installs as symlinks, as regular files.

    ``hosts/<host_key>.md`` is the one per-machine file; the other machines'
    files stay in the repository and never reach the profile.
    ``codex/agents/*.toml`` is deliberately absent: ``sync-codex-agents.py``
    already owns that directory and validates the TOML before writing.
    """

    claude_skills = claude_home / "skills"
    agents_skills = agents_home / "skills"
    shared_skills = ("maintain-guideline", "create-pr", "parallel-dispatch")

    mappings = [
        Mapping(repo / "CLAUDE.md", claude_home / "CLAUDE.md", "file"),
        Mapping(repo / "hosts" / f"{host_key}.md", claude_home / "host-facts.md", "file"),
        Mapping(repo / "rules", claude_home / "rules", "tree"),
        Mapping(repo / "rubrics", claude_home / "rubrics", "tree"),
        Mapping(repo / "agents" / "worker.md", claude_home / "agents" / "worker.md", "file"),
        Mapping(repo / "agents" / "verifier.md", claude_home / "agents" / "verifier.md", "file"),
        Mapping(repo / "AGENTS.md", codex_home / "AGENTS.md", "file"),
        Mapping(
            repo / "codex" / "skills" / "session-handoff",
            agents_skills / "session-handoff",
            "tree",
        ),
    ]
    for name in shared_skills:
        mappings.append(Mapping(repo / "skills" / name, claude_skills / name, "tree"))
        mappings.append(Mapping(repo / "skills" / name, agents_skills / name, "tree"))
    return mappings


def _lkind(path: Path) -> str | None:
    """Classify an entry without following it; None when it does not exist.

    ``Path.exists`` follows the link and raises on this repository's motivating
    host, so every check here goes through ``lstat``.
    """

    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        # An entry whose parent is itself an unreadable reparse point.
        return "unreadable"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISREG(mode):
        return "regular file"
    if stat.S_ISDIR(mode):
        return "directory"
    return "special file"


def _plain(path: Path) -> Path:
    """Drop the Windows extended-length prefix ``os.readlink`` adds.

    Without this, every target comes back as ``\\\\?\\C:\\...`` and compares
    unequal to the repository path, so no link is ever recognized as ours.
    """

    text = str(path)
    if text.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + text[len("\\\\?\\UNC\\"):])
    if text.startswith("\\\\?\\"):
        return Path(text[len("\\\\?\\"):])
    return path


def _link_target(path: Path) -> Path | None:
    """Read a link's stored target, even when the target is missing."""

    try:
        target = _plain(Path(os.readlink(path)))
    except OSError:
        return None
    if not target.is_absolute():
        # A relative target is stored relative to the link's own directory.
        target = path.parent / target
    return Path(os.path.normpath(target))


def _is_repo_link(path: Path, repo: Path) -> bool:
    """True when this entry is a link this repository's installer created."""

    if _lkind(path) != "symlink":
        return False
    target = _link_target(path)
    if target is None:
        return False
    try:
        return target == repo or target.is_relative_to(repo)
    except (OSError, ValueError):
        return False


def load_sources(mappings: list[Mapping]) -> list[SourceFile]:
    """Read and validate every source byte before any destination is touched."""

    files: list[SourceFile] = []
    seen: dict[Path, Path] = {}
    for mapping in mappings:
        source = mapping.source
        if not source.exists():
            raise SyncError(f"source does not exist: {source}")

        if mapping.kind == "file":
            if not source.is_file():
                raise SyncError(f"source is not a file: {source}")
            pairs = [(source, mapping.destination)]
        elif mapping.kind == "tree":
            if not source.is_dir():
                raise SyncError(f"source is not a directory: {source}")
            pairs = []
            for child in sorted(source.rglob("*")):
                if child.is_dir():
                    continue
                if not child.is_file():
                    raise SyncError(f"unsupported source entry: {child}")
                pairs.append((child, mapping.destination / child.relative_to(source)))
            if not pairs:
                raise SyncError(f"source tree is empty: {source}")
        else:
            raise SyncError(f"unknown mapping kind: {mapping.kind}")

        for child, destination in pairs:
            previous = seen.get(destination)
            if previous is not None and previous != child:
                raise SyncError(
                    f"two sources map to {destination}: {previous} and {child}"
                )
            seen[destination] = child
            try:
                content = child.read_bytes()
            except OSError as exc:
                raise SyncError(f"cannot read source {child}: {exc}") from exc
            files.append(SourceFile(source=child, destination=destination, content=content))

    return files


def _managed_roots(mappings: list[Mapping]) -> list[Path]:
    return [mapping.destination for mapping in mappings if mapping.kind == "tree"]


def plan_prunes(
    mappings: list[Mapping],
    planned: set[Path],
    repo: Path,
) -> list[Operation]:
    """Find leftover links this repository installed but no longer provides.

    Only entries that are symlinks pointing into the repository qualify, so a
    directory the user created and a junction into another tool's profile are
    both left alone.
    """

    prunes: list[Operation] = []
    candidates: list[Path] = []

    for mapping in mappings:
        if mapping.kind == "file" and mapping.destination not in planned:
            candidates.append(mapping.destination)
        parent = mapping.destination.parent
        if _lkind(parent) != "directory":
            continue
        try:
            siblings = sorted(parent.iterdir())
        except OSError:
            continue
        candidates.extend(siblings)

    for candidate in dict.fromkeys(candidates):
        if candidate in planned:
            continue
        if any(candidate == root for root in _managed_roots(mappings)):
            continue
        if _is_repo_link(candidate, repo):
            prunes.append(Operation(destination=candidate, action="prune"))

    return prunes


def plan_operations(
    files: list[SourceFile],
    mappings: list[Mapping],
    repo: Path,
    *,
    apply: bool,
    update: bool,
    prune: bool,
) -> list[Operation]:
    """Inspect every destination entry before any operation can mutate it."""

    operations: list[Operation] = []

    for root in _managed_roots(mappings):
        kind = _lkind(root)
        if kind == "symlink":
            operations.append(Operation(destination=root, action="migrate-tree"))
        elif kind in {"regular file", "special file"}:
            raise SyncError(f"destination tree root is not a directory: {root} ({kind})")

    for entry in files:
        destination = entry.destination
        kind = _lkind(destination)
        if kind is None:
            action = "install"
        elif kind == "symlink":
            if not _is_repo_link(destination, repo):
                raise SyncError(
                    f"foreign symlink at {destination} -> {_link_target(destination)}; "
                    "move it aside by hand and re-run"
                )
            action = "migrate-symlink"
        elif kind == "regular file":
            try:
                existing = destination.read_bytes()
            except OSError:
                # Readable-shaped but unopenable: treat as needing replacement.
                existing = None
            if existing == entry.content:
                action = "unchanged"
            elif not update:
                action = "update-required"
            else:
                action = "update"
        elif kind == "unreadable":
            # Its parent is a reparse point that will be migrated first.
            action = "install"
        else:
            raise SyncError(f"unsupported destination entry at {destination}: {kind}")

        operations.append(
            Operation(
                destination=destination,
                action=action,
                source=entry.source,
                content=entry.content,
            )
        )

    planned = {entry.destination for entry in files}
    if prune:
        operations.extend(plan_prunes(mappings, planned, repo))

    blocked = [operation for operation in operations if operation.action == "update-required"]
    if blocked and apply:
        paths = ", ".join(str(operation.destination) for operation in blocked)
        raise SyncError(f"differing regular file(s) require --apply --update: {paths}")

    return operations


def _make_backup_root(anchor: Path) -> Path:
    parent = anchor.parent
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{anchor.name}.backup-", dir=parent))


def _move_aside(path: Path, backup_root: Path, label: str) -> Path:
    backup = backup_root / label
    backup.parent.mkdir(parents=True, exist_ok=True)
    # Rename preserves a symlink as a symlink and never follows it, which also
    # avoids needing permission to create a new link on Windows.
    os.replace(path, backup)
    return backup


def _replace_with_bytes(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
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


def apply_operations(
    operations: list[Operation],
    *,
    backup_root: Path,
) -> dict[Path, Path]:
    """Move every replaced entry aside, then write the validated plan."""

    backups: dict[Path, Path] = {}
    counter = 0

    # Tree roots first: a directory symlink must stop being a symlink before
    # any file underneath it can be written.
    for operation in operations:
        if operation.action != "migrate-tree":
            continue
        counter += 1
        backups[operation.destination] = _move_aside(
            operation.destination, backup_root, f"{counter:02d}-{operation.destination.name}"
        )
        operation.destination.mkdir(parents=True, exist_ok=True)

    for operation in operations:
        if operation.action not in {"migrate-symlink", "update", "prune"}:
            continue
        if _lkind(operation.destination) is None:
            continue
        counter += 1
        backups[operation.destination] = _move_aside(
            operation.destination, backup_root, f"{counter:02d}-{operation.destination.name}"
        )

    for operation in operations:
        if operation.action in {"install", "migrate-symlink", "update"}:
            assert operation.content is not None
            _replace_with_bytes(operation.destination, operation.content)

    return backups


def verify(operations: list[Operation]) -> list[str]:
    """Open every destination file and compare bytes.

    The failure this script exists for is invisible to a link-shaped check, so
    completion is claimed only against real reads.
    """

    failures: list[str] = []
    for operation in operations:
        if operation.action in {"migrate-tree", "prune"}:
            continue
        assert operation.content is not None
        destination = operation.destination
        kind = _lkind(destination)
        if kind != "regular file":
            failures.append(f"{destination}: expected a regular file, found {kind}")
            continue
        try:
            actual = destination.read_bytes()
        except OSError as exc:
            failures.append(f"{destination}: cannot open after install: {exc}")
            continue
        if actual != operation.content:
            failures.append(f"{destination}: content differs from source")
    return failures


_VERBS = {
    "install": "install",
    "migrate-symlink": "replace symlink with regular file",
    "migrate-tree": "replace directory symlink with real directory",
    "update": "update regular file",
    "update-required": "would update (requires --apply --update)",
    "unchanged": "unchanged",
    "prune": "remove stale link into this repo",
}


def print_preview(operations: list[Operation], *, apply: bool) -> None:
    print(f"mode: {'apply' if apply else 'dry-run'}")
    for operation in operations:
        if operation.action == "unchanged":
            continue
        print(f"{_VERBS[operation.action]}: {operation.destination}")

    counts: dict[str, int] = {}
    for operation in operations:
        counts[operation.action] = counts.get(operation.action, 0) + 1
    summary = " ".join(f"{action}={count}" for action, count in sorted(counts.items()))
    print(f"summary: {summary or 'nothing to do'}")


def sync(
    *,
    repo: Path = REPO_ROOT,
    claude_home: Path,
    codex_home: Path,
    agents_home: Path,
    apply: bool = False,
    update: bool = False,
    prune: bool = False,
    host_key: str | None = None,
) -> list[Operation]:
    """Validate, preview, or apply a synchronization plan."""

    repo = _plain(repo.expanduser().resolve())
    if host_key is None:
        host_key = detect_host_key()
    mappings = default_mappings(
        repo=repo,
        claude_home=claude_home.expanduser(),
        codex_home=codex_home.expanduser(),
        agents_home=agents_home.expanduser(),
        host_key=host_key,
    )
    files = load_sources(mappings)
    operations = plan_operations(
        files, mappings, repo, apply=apply, update=update, prune=prune
    )

    if not apply:
        print_preview(operations, apply=False)
        return operations

    changes = [
        operation
        for operation in operations
        if operation.action in {"install", "migrate-symlink", "migrate-tree", "update", "prune"}
    ]
    backups: dict[Path, Path] = {}
    if changes:
        backup_root = _make_backup_root(claude_home.expanduser())
        backups = apply_operations(operations, backup_root=backup_root)

    print_preview(operations, apply=True)
    if backups:
        print(f"backup directory: {next(iter(backups.values())).parent}")

    failures = verify(operations)
    if failures:
        for failure in failures:
            print(f"read-back FAILED: {failure}", file=sys.stderr)
        raise SyncError(f"{len(failures)} destination file(s) failed read-back")
    print(f"read-back: {len([o for o in operations if o.action != 'prune' and o.action != 'migrate-tree'])} file(s) opened and byte-identical")
    return operations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or install this repo into ~/.claude, ~/.codex and ~/.agents as regular files."
    )
    parser.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--agents-home", type=Path, default=Path.home() / ".agents")
    parser.add_argument(
        "--host-key",
        help=(
            "which hosts/<key>.md to install as ~/.claude/host-facts.md; "
            "default: detected from the platform (Darwin=macos, Windows=windows)"
        ),
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
    parser.add_argument(
        "--prune",
        action="store_true",
        help="also remove stale links into this repo that the plan no longer installs",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.update and not args.apply:
        parser.error("--update requires --apply")
    try:
        sync(
            claude_home=args.claude_home,
            codex_home=args.codex_home,
            agents_home=args.agents_home,
            apply=args.apply,
            update=args.update,
            prune=args.prune,
            host_key=args.host_key,
        )
    except (OSError, SyncError) as exc:
        print(f"sync-profile: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
