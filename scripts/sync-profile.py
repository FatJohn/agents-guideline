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
import re
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


_HOST_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _validate_host_key(host_key: str, repo: Path) -> None:
    """Reject a key that cannot safely become a ``hosts/<key>.md`` filename.

    ``host_key`` is interpolated into ``repo / "hosts" / f"{host_key}.md"`` and
    the result is installed as ``~/.claude/host-facts.md``.  Without this check
    a value like ``"../CLAUDE"`` or an absolute path is accepted unmodified and
    quietly resolves outside ``hosts/``, installing an arbitrary repo file (or
    nothing at all) as the machine's facts.
    """

    if not _HOST_KEY_PATTERN.match(host_key):
        raise SyncError(
            f"invalid --host-key {host_key!r}: must match "
            f"{_HOST_KEY_PATTERN.pattern!r} (lowercase letters, digits, '-', '_'; "
            "must start with a letter or digit)"
        )
    facts_file = repo / "hosts" / f"{host_key}.md"
    if not facts_file.is_file():
        raise SyncError(
            f"missing {facts_file}; create hosts/{host_key}.md or pass a "
            "different --host-key"
        )


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


@dataclass
class Transaction:
    """The entries this invocation may safely undo after a caught failure."""

    backup_root: Path
    backups: dict[Path, Path]
    written: list[Path]
    created_directories: list[Path]


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
        Mapping(repo / "agents" / "worker-sonnet.md", claude_home / "agents" / "worker-sonnet.md", "file"),
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
        entry_stat = path.lstat()
        mode = entry_stat.st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        # An entry whose parent is itself an unreadable reparse point.
        return "unreadable"
    if stat.S_ISLNK(mode):
        return "symlink"
    # On Windows, a junction is reported as a directory by ``stat``.  Treat
    # every reparse point as a redirect unless it was already identified as a
    # symlink; ownership cannot be established by following its target.
    attributes = getattr(entry_stat, "st_file_attributes", 0)
    if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        return "redirect"
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


def _comparison_path(path: Path) -> Path:
    """Normalize host aliases only while comparing known link endpoints.

    macOS exposes the same filesystem through ``/var`` and ``/private/var``.
    ``realpath`` makes those spellings compare equal; preflight separately
    rejects every redirect below a profile root, so this comparison never
    authorizes an external profile redirect.  Windows reparse points are not
    resolved: an untrusted junction may fail to open and must never become
    trusted merely because its eventual target looks right.
    """

    raw = os.path.normpath(os.path.abspath(str(_plain(path))))
    if platform.system() == "Darwin":
        raw = os.path.realpath(raw)
    return Path(os.path.normcase(raw))


def _same_path(left: Path, right: Path) -> bool:
    return _comparison_path(left) == _comparison_path(right)


def _lexical_path(path: Path) -> Path:
    """Normalize spelling without resolving profile redirects."""

    return Path(os.path.normcase(os.path.normpath(os.path.abspath(str(_plain(path))))))


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(_lexical_path(path)), str(_lexical_path(root)))) == str(
            _lexical_path(root)
        )
    except ValueError:
        return False


def _comparison_is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(_comparison_path(path)), str(_comparison_path(root)))) == str(
            _comparison_path(root)
        )
    except ValueError:
        return False


def _is_repo_link(path: Path, repo: Path) -> bool:
    """True when this entry is a link this repository's installer created."""

    if _lkind(path) != "symlink":
        return False
    target = _link_target(path)
    if target is None:
        return False
    # The target is only classified for pruning; comparison preserves a broken
    # repo-owned link and accepts /var versus /private/var source spellings.
    return _comparison_is_within(target, repo)


def _is_owned_link(path: Path, source: Path) -> bool:
    """Accept only the precise source mapping, including macOS's /var alias."""

    target = _link_target(path)
    return target is not None and _same_path(target, source)


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


def _parts_under(path: Path, root: Path) -> list[Path]:
    """Return lexical ancestors from ``root`` through ``path`` without links."""

    if not _is_within(path, root):
        raise SyncError(f"destination escapes its profile root: {path}")
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = _lexical_path(path).relative_to(_lexical_path(root))
        root = _lexical_path(root)
    result = [root]
    current = root
    for part in relative.parts:
        current = current / part
        result.append(current)
    return result


def preflight_destinations(
    mappings: list[Mapping],
    profile_roots: list[Path],
    files: list[SourceFile],
) -> set[Path]:
    """Reject redirects before planning can traverse or write through them.

    A tree root may be a link only when it is the exact repository mapping we
    are replacing.  Its children are then planned as fresh installs, without
    reading the old linked directory.  All other redirect ancestors are a
    foreign boundary, including Windows junctions and unreadable reparse
    points.
    """

    migrated: set[Path] = set()
    for home in profile_roots:
        kind = _lkind(home)
        if kind in {"symlink", "redirect", "unreadable"}:
            raise SyncError(f"profile root is a redirect or unreadable: {home} ({kind})")
        if kind in {"regular file", "special file"}:
            raise SyncError(f"profile root is not a directory: {home} ({kind})")

    for mapping in mappings:
        if mapping.kind != "tree":
            continue
        kind = _lkind(mapping.destination)
        if kind == "symlink":
            if not _is_owned_link(mapping.destination, mapping.source):
                raise SyncError(
                    f"foreign tree redirect at {mapping.destination} -> "
                    f"{_link_target(mapping.destination)}; move it aside by hand and re-run"
                )
            migrated.add(mapping.destination)
        elif kind in {"redirect", "unreadable"}:
            raise SyncError(f"destination tree root is a redirect: {mapping.destination} ({kind})")
        elif kind in {"regular file", "special file"}:
            raise SyncError(f"destination tree root is not a directory: {mapping.destination} ({kind})")

    def check_ancestors(destination: Path) -> None:
        home = next((root for root in profile_roots if _is_within(destination, root)), None)
        if home is None:
            raise SyncError(f"destination is outside the intended profiles: {destination}")
        # Stop at an owned tree link that this transaction will replace.  Its
        # old descendants must never be listed or trusted during planning.
        for ancestor in _parts_under(destination.parent, home):
            if ancestor in migrated:
                break
            kind = _lkind(ancestor)
            if kind in {"symlink", "redirect", "unreadable"}:
                raise SyncError(f"destination ancestor is a redirect: {ancestor} ({kind})")
            if kind in {"regular file", "special file"}:
                raise SyncError(f"destination ancestor is not a directory: {ancestor} ({kind})")

    for mapping in mappings:
        check_ancestors(mapping.destination)
    # Tree mappings expand to several SourceFiles.  Check each final parent,
    # not merely the tree root, so a nested skill or references redirect cannot
    # turn a later write into an external one.
    for entry in files:
        check_ancestors(entry.destination)
    return migrated


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
    migrated_roots: set[Path] | None = None,
) -> list[Operation]:
    """Inspect every destination entry before any operation can mutate it."""

    operations: list[Operation] = []

    migrated_roots = migrated_roots or set()
    for root in _managed_roots(mappings):
        kind = _lkind(root)
        if root in migrated_roots:
            operations.append(Operation(destination=root, action="migrate-tree"))
        elif kind in {"regular file", "special file", "redirect", "unreadable"}:
            raise SyncError(f"destination tree root is not a directory: {root} ({kind})")

    for entry in files:
        destination = entry.destination
        under_migrated_root = any(_is_within(destination, root) for root in migrated_roots)
        kind = None if under_migrated_root else _lkind(destination)
        if kind is None:
            action = "install"
        elif kind == "symlink":
            if not _is_owned_link(destination, entry.source):
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


def _remove_backup_root_if_empty(backup_root: Path) -> None:
    """Best-effort cleanup: a run that moved nothing aside leaves no directory.

    A non-empty backup (the ordinary successful-replace case, or a rollback
    that itself failed) must never be removed; ``rmdir`` already refuses a
    non-empty directory, so any ``OSError`` here is simply left alone.
    """

    try:
        backup_root.rmdir()
    except OSError:
        pass


def _move_aside(path: Path, backup_root: Path, label: str) -> Path:
    backup = backup_root / label
    backup.parent.mkdir(parents=True, exist_ok=True)
    # Rename preserves a symlink as a symlink and never follows it, which also
    # avoids needing permission to create a new link on Windows.
    os.replace(path, backup)
    return backup


def _ensure_parent_directories(destination: Path, created_directories: list[Path]) -> None:
    missing: list[Path] = []
    current = destination.parent
    while _lkind(current) is None:
        missing.append(current)
        current = current.parent
    if _lkind(current) != "directory":
        raise SyncError(f"destination parent is not a directory: {current} ({_lkind(current)})")
    for directory in reversed(missing):
        directory.mkdir()
        created_directories.append(directory)


def _replace_with_bytes(
    destination: Path, content: bytes, created_directories: list[Path]
) -> None:
    _ensure_parent_directories(destination, created_directories)
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
    transaction: Transaction,
) -> None:
    """Move every replaced entry aside, then write the validated plan."""

    counter = 0

    # Tree roots first: a directory symlink must stop being a symlink before
    # any file underneath it can be written.
    for operation in operations:
        if operation.action != "migrate-tree":
            continue
        counter += 1
        transaction.backups[operation.destination] = _move_aside(
            operation.destination, transaction.backup_root, f"{counter:02d}-{operation.destination.name}"
        )
        operation.destination.mkdir(parents=True, exist_ok=True)
        transaction.created_directories.append(operation.destination)

    for operation in operations:
        if operation.action not in {"migrate-symlink", "update", "prune"}:
            continue
        if _lkind(operation.destination) is None:
            continue
        counter += 1
        transaction.backups[operation.destination] = _move_aside(
            operation.destination, transaction.backup_root, f"{counter:02d}-{operation.destination.name}"
        )

    for operation in operations:
        if operation.action in {"install", "migrate-symlink", "update"}:
            assert operation.content is not None
            _replace_with_bytes(
                operation.destination, operation.content, transaction.created_directories
            )
            transaction.written.append(operation.destination)



def rollback(transaction: Transaction) -> None:
    """Undo only paths created or moved by this invocation, in reverse order."""

    errors: list[str] = []
    for path in reversed(transaction.written):
        try:
            if _lkind(path) == "regular file":
                path.unlink()
            elif _lkind(path) is not None:
                raise SyncError(f"refusing to remove changed transaction path: {path}")
        except (OSError, SyncError) as exc:
            errors.append(f"cannot remove {path}: {exc}")
    for directory in reversed(transaction.created_directories):
        try:
            if _lkind(directory) == "directory":
                directory.rmdir()
            elif _lkind(directory) is not None:
                raise SyncError(f"refusing to remove changed transaction directory: {directory}")
        except (OSError, SyncError) as exc:
            errors.append(f"cannot remove directory {directory}: {exc}")
    for destination, backup in reversed(list(transaction.backups.items())):
        try:
            if _lkind(destination) is not None:
                raise SyncError(f"destination remains occupied: {destination}")
            os.replace(backup, destination)
        except (OSError, SyncError) as exc:
            errors.append(f"cannot restore {destination}: {exc}")
    if errors:
        detail = "; ".join(errors)
        raise SyncError(
            f"rollback failed ({detail}); recover originals from {transaction.backup_root}"
        )


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


def _symlink_migration_message(migrating: list[Operation], limit: int = 5) -> str:
    """Explain what ``--apply`` would silently convert to regular file copies."""

    paths = [str(operation.destination) for operation in migrating]
    shown = ", ".join(paths[:limit])
    if len(paths) > limit:
        shown += f", and {len(paths) - limit} more"
    return (
        "this profile is currently installed as symlinks; --apply would replace "
        f"{len(paths)} symlink(s) with regular file copies: {shown}; "
        "re-run with --replace-symlinks to continue"
    )


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
    replace_symlinks: bool = False,
    host_key: str | None = None,
) -> list[Operation]:
    """Validate, preview, or apply a synchronization plan."""

    repo = _plain(repo.expanduser().resolve())
    if host_key is None:
        host_key = detect_host_key()
    _validate_host_key(host_key, repo)
    claude_home = claude_home.expanduser()
    codex_home = codex_home.expanduser()
    agents_home = agents_home.expanduser()
    mappings = default_mappings(
        repo=repo,
        claude_home=claude_home,
        codex_home=codex_home,
        agents_home=agents_home,
        host_key=host_key,
    )
    files = load_sources(mappings)
    migrated_roots = preflight_destinations(
        mappings, [claude_home, codex_home, agents_home], files
    )
    operations = plan_operations(
        files,
        mappings,
        repo,
        apply=apply,
        update=update,
        prune=prune,
        migrated_roots=migrated_roots,
    )

    migrating = [
        operation for operation in operations if operation.action in {"migrate-symlink", "migrate-tree"}
    ]

    if not apply:
        print_preview(operations, apply=False)
        if migrating:
            print("note: --apply of this plan requires --replace-symlinks")
        return operations

    if migrating and not replace_symlinks:
        raise SyncError(_symlink_migration_message(migrating))

    # Print the plan before any write, so a mid-apply failure still leaves a
    # record of what was intended, not just what got interrupted.
    print_preview(operations, apply=True)

    changes = [
        operation
        for operation in operations
        if operation.action in {"install", "migrate-symlink", "migrate-tree", "update", "prune"}
    ]
    transaction: Transaction | None = None
    if changes:
        backup_root = _make_backup_root(claude_home)
        transaction = Transaction(backup_root, {}, [], [])
        try:
            apply_operations(operations, transaction=transaction)
            failures = verify(operations)
            if failures:
                for failure in failures:
                    print(f"read-back FAILED: {failure}", file=sys.stderr)
                raise SyncError(f"{len(failures)} destination file(s) failed read-back")
        except Exception as exc:
            try:
                rollback(transaction)
            except SyncError as rollback_error:
                raise SyncError(f"apply failed: {exc}; {rollback_error}") from exc
            # Rollback succeeded: every backed-up entry moved back out, so an
            # anchor-only backup directory is now empty and safe to remove.
            _remove_backup_root_if_empty(transaction.backup_root)
            raise
        else:
            _remove_backup_root_if_empty(transaction.backup_root)
    else:
        failures = verify(operations)
        if failures:
            for failure in failures:
                print(f"read-back FAILED: {failure}", file=sys.stderr)
            raise SyncError(f"{len(failures)} destination file(s) failed read-back")

    if transaction and transaction.backups:
        print(f"backup directory: {transaction.backup_root}")
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
    parser.add_argument(
        "--replace-symlinks",
        action="store_true",
        help=(
            "required together with --apply when the plan would replace this "
            "profile's existing symlink install with regular file copies"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.update and not args.apply:
        parser.error("--update requires --apply")
    if args.replace_symlinks and not args.apply:
        parser.error("--replace-symlinks requires --apply")
    try:
        sync(
            claude_home=args.claude_home,
            codex_home=args.codex_home,
            agents_home=args.agents_home,
            apply=args.apply,
            update=args.update,
            prune=args.prune,
            replace_symlinks=args.replace_symlinks,
            host_key=args.host_key,
        )
    except (OSError, SyncError) as exc:
        print(f"sync-profile: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
